from __future__ import annotations

import math
import random
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QMovie, QPainter
from PySide6.QtWidgets import QApplication, QLabel, QWidget

IDLE = "idle"
WALK = "walk"
CLICK = "click"
DRAG = "drag"
LOST = "lost"
RANDOM = "random"

ONE_SHOT_STATES = (CLICK, LOST)  # 播完一次后自动回待机的状态
ONE_LOOP_STATES = (*ONE_SHOT_STATES, RANDOM)  # 需从首帧完整播完一遍（末帧检测）的状态

DRAG_THRESHOLD = 6  # 位移超过该像素数视为拖动，否则视为单击


class PetWindow(QWidget):
    """桌宠窗口：无边框、透明、置顶；负责 idle/walk/random/click/drag/lost 状态机。"""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.behavior = config.get("behavior") or {}

        self._state = IDLE
        self._movies: dict[str, QMovie] = {}
        self._random_action_keys = self._register_random_actions()
        self._random_key: str | None = None
        self._walk_vx = 1.0
        self._walk_vy = 0.0
        self._walk_fx = 0.0
        self._walk_fy = 0.0
        self._walking = False
        self._dragging = False
        self._press_pos: QPoint | None = None
        self._drag_offset: QPoint | None = None

        self._click_cap_timer = QTimer(self)
        self._click_cap_timer.setSingleShot(True)
        self._click_cap_timer.timeout.connect(self._on_one_shot_finished)

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._label = QLabel(self)
        self._label.setFixedSize(config["window"]["width"], config["window"]["height"])
        self.resize(self._label.size())

        self._walk_timer = QTimer(self)
        self._walk_timer.timeout.connect(self._walk_step)

        self._episode_timer = QTimer(self)
        self._episode_timer.setSingleShot(True)
        self._episode_timer.timeout.connect(self._end_walk)

        self._idle_timer = QTimer(self)  # 待机计时：到点后做一次行为决策
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._decide_action)

        self._set_state(IDLE)
        self._place(config["window"].get("start", "bottom_right"))
        self._schedule_next_behavior()

    # ---------- 状态与动画 ----------

    def _register_random_actions(self) -> list[str]:
        """把 random_actions 列表里的 GIF 注册为 random_action_0/1/... 动画键，返回可用键列表。"""
        anim = self.config.setdefault("animation", {})
        keys: list[str] = []
        for i, path in enumerate(anim.get("random_actions") or []):
            if path and Path(path).is_file():
                key = f"random_action_{i}"
                anim[key] = path
                keys.append(key)
        return keys

    @property
    def walk_enabled(self) -> bool:
        return bool(self.behavior.get("walk_enabled", True))

    @property
    def state(self) -> str:
        return self._state

    def _anim_key(self, state: str) -> str:
        if state == WALK:
            return "walk_left" if self._walk_vx < 0 else "walk_right"
        if state == RANDOM:
            return self._random_key or "idle"  # _random_key 由 _begin_random_action 指定
        return state  # idle/click/drag/lost 直接用状态名作动画键

    def _movie_for(self, key: str) -> QMovie:
        movie = self._movies.get(key)
        if movie is None:
            movie = QMovie(self.config["animation"][key])
            movie.setCacheMode(QMovie.CacheMode.CacheAll)
            if key in ONE_LOOP_STATES or key in self._random_action_keys:
                movie.frameChanged.connect(self._on_one_shot_frame)
            if key in ONE_SHOT_STATES:
                movie.finished.connect(self._on_one_shot_finished)
            self._movies[key] = movie
        return movie

    def _on_one_shot_frame(self, frame: int) -> None:
        if self._state not in ONE_LOOP_STATES or self._label.movie() is not self.sender():
            return
        movie: QMovie = self.sender()
        total = movie.frameCount()
        if total > 0 and frame >= total - 1:
            QTimer.singleShot(0, self._on_one_shot_finished)

    def _set_state(self, state: str) -> None:
        key = self._anim_key(state)
        movie = self._movie_for(key)
        self._state = state

        for other in self._movies.values():
            if other is not movie and other.state() == QMovie.MovieState.Running:
                other.setPaused(True)

        if self._label.movie() is not movie:
            self._label.setMovie(movie)
        if state in ONE_LOOP_STATES:  # 一次性/完整播一遍的状态：一律从首帧起播
            movie.jumpToFrame(0)
            if movie.state() != QMovie.MovieState.Running:
                movie.start()
        elif movie.state() != QMovie.MovieState.Running:
            movie.jumpToFrame(0)
            movie.start()

        # 切换状态时停掉与该状态无关的计时器：用户操作（click/drag）借此打断当前动作
        if state != IDLE:
            self._idle_timer.stop()
        if state != WALK:
            self._stop_walking()

        if state in ONE_LOOP_STATES:
            cap = int(self.behavior.get(f"{state}_max_ms", 0) or 0)
            if cap > 0:
                self._click_cap_timer.start(cap)
            else:
                self._click_cap_timer.stop()
        else:
            self._click_cap_timer.stop()

    def _rand_ms(self, lo_key: str, hi_key: str, lo_default: float, hi_default: float) -> int:
        lo = float(self.behavior.get(lo_key, lo_default))
        hi = float(self.behavior.get(hi_key, hi_default))
        if hi < lo:
            hi = lo
        return int(random.uniform(lo, hi) * 1000)

    # ---------- 自主行为循环：待机计时 → 概率决策 → 执行动作 → 回待机 ----------

    def _schedule_next_behavior(self) -> None:
        """随机待机一段时长（idle_duration_min~idle_duration_max 秒）后做一次行为决策。"""
        self._idle_timer.start(
            self._rand_ms("idle_duration_min", "idle_duration_max", 10, 60)
        )

    def _enter_idle(self) -> None:
        """动作执行完毕回到待机（播 stand.gif）并重新随机计时。"""
        self._set_state(IDLE)
        self._schedule_next_behavior()

    def _weight(self, key: str, default: float) -> float:
        """行为决策权重（即概率）：负数按 0 处理；三项按和归一化，和为 1 时即精确概率。"""
        return max(0.0, float(self.behavior.get(key, default)))

    def _decide_action(self) -> None:
        """待机到点：按三项概率在 走动 / 随机动画 / 继续待机 之间加权随机并执行。"""
        if self._state != IDLE:
            return
        choices = (
            (WALK, self._weight("walk_chance", 0.5) if self.walk_enabled else 0.0),
            (RANDOM, self._weight("random_chance", 0.3) if self._random_action_keys else 0.0),
            (IDLE, self._weight("continue_idle_chance", 0.2)),
        )
        total = sum(weight for _, weight in choices)
        if total <= 0.0:  # 三项权重全为 0：一直待机
            self._schedule_next_behavior()
            return
        roll = random.random() * total
        action = IDLE
        cumulative = 0.0
        for name, weight in choices:
            cumulative += weight
            if roll < cumulative:
                action = name
                break
        if action == WALK:
            self._begin_walk()
        elif action == RANDOM:
            self._begin_random_action()
        else:  # 继续待机：保持 stand.gif，重新计时
            self._schedule_next_behavior()

    # ---------- 随机动作 ----------

    def _begin_random_action(self) -> None:
        """随机动作：原地从首帧完整播一个 random_actions GIF（不位移），末帧检测回待机。"""
        if not self._random_action_keys:  # 没有随机动画素材：退回继续待机
            self._schedule_next_behavior()
            return
        self._random_key = random.choice(self._random_action_keys)
        self._set_state(RANDOM)  # 播完由 _on_one_shot_frame 末帧检测触发回待机

    # ---------- 走动 ----------

    def _begin_walk(self) -> None:
        if not self.walk_enabled or self._state != IDLE:
            return
        angle = random.uniform(0.0, 2.0 * math.pi)
        self._walk_vx = math.cos(angle)
        self._walk_vy = math.sin(angle)
        self._walk_fx = 0.0
        self._walk_fy = 0.0
        self._walking = True
        self._set_state(WALK)
        self._walk_timer.start(max(10, int(self.behavior.get("walk_tick_ms", 30))))
        self._episode_timer.start(
            self._rand_ms("walk_duration_min", "walk_duration_max", 3, 8)
        )

    def _end_walk(self) -> None:
        self._stop_walking()
        if self._state != WALK:
            return  # 走动已被用户操作打断，由打断流程负责回待机
        if self._should_play_lost():
            self._set_state(LOST)  # 播完“走丢了”由 _on_one_shot_finished 回待机并重新计时
            return
        self._enter_idle()

    def _should_play_lost(self) -> bool:
        chance = float(self.behavior.get("lost_chance", 0.3))
        chance = min(1.0, max(0.0, chance))
        if chance <= 0.0 or random.random() >= chance:
            return False
        path = self.config["animation"].get("lost")
        return bool(path) and Path(path).is_file()

    def _stop_walking(self) -> None:
        self._walking = False
        self._walk_timer.stop()
        self._episode_timer.stop()

    def _walk_step(self) -> None:
        speed = max(1, int(self.behavior.get("walk_speed", 3)))
        screen = QApplication.primaryScreen().availableGeometry()
        self._walk_fx += self._walk_vx * speed
        self._walk_fy += self._walk_vy * speed
        dx = int(self._walk_fx)
        dy = int(self._walk_fy)
        self._walk_fx -= dx
        self._walk_fy -= dy

        x = self.x() + dx
        y = self.y() + dy

        if x < screen.x():
            x = screen.x()
            self._walk_vx = abs(self._walk_vx)
        elif x + self.width() > screen.x() + screen.width():
            x = screen.x() + screen.width() - self.width()
            self._walk_vx = -abs(self._walk_vx)

        if y < screen.y():
            y = screen.y()
            self._walk_vy = abs(self._walk_vy)
        elif y + self.height() > screen.y() + screen.height():
            y = screen.y() + screen.height() - self.height()
            self._walk_vy = -abs(self._walk_vy)

        if (x, y) != (self.x(), self.y()):
            self.move(x, y)
        self._refresh_walk_movie()

    def _refresh_walk_movie(self) -> None:
        if self._state != WALK:
            return
        movie = self._movie_for(self._anim_key(WALK))
        if self._label.movie() is not movie:
            self._set_state(WALK)

    def set_walk_enabled(self, enabled: bool) -> None:
        """走动开关（供右键菜单调用）。关闭后行为决策只在 随机动画 / 继续待机 之间选。"""
        self.behavior["walk_enabled"] = bool(enabled)
        if not enabled:
            self._stop_walking()
            if self._state == WALK:
                self._enter_idle()
                return
        if self._state == IDLE and not self._idle_timer.isActive():
            self._schedule_next_behavior()

    # ---------- 单击 / 拖动 ----------

    def _on_interaction_done(self) -> None:
        """任意用户操作（点击/拖动）或一次性动画（点击/走丢）结束后：回到待机，并重新随机计时。"""
        if self._state in (*ONE_SHOT_STATES, DRAG):
            self._set_state(IDLE)
        self._schedule_next_behavior()

    def _on_one_shot_finished(self) -> None:
        if self._state == RANDOM:
            self._enter_idle()  # 随机动画完整播完一遍 → 回待机重新计时
            return
        if self._state not in ONE_SHOT_STATES:
            return
        self._on_interaction_done()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press_pos = event.globalPosition().toPoint()
        self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
        self._dragging = False

        self._set_state(CLICK)  # 内部会停掉待机/走动计时并打断当前动作（含随机动画）
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._press_pos is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not self._dragging:
            delta = event.globalPosition().toPoint() - self._press_pos
            if abs(delta.x()) < DRAG_THRESHOLD and abs(delta.y()) < DRAG_THRESHOLD:
                return
            self._dragging = True
            self._set_state(DRAG)

        self.move(event.globalPosition().toPoint() - self._drag_offset)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        was_dragging = self._dragging
        self._dragging = False
        self._press_pos = None
        self._drag_offset = None

        if was_dragging:
            self._on_interaction_done()
        elif self._state != CLICK:
            self._on_interaction_done()
        event.accept()

    # ---------- 窗口 ----------

    def _place(self, where: str) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        if where == "center":
            x = screen.x() + (screen.width() - self.width()) // 2
            y = screen.y() + (screen.height() - self.height()) // 2
        else:  # bottom_right
            x = screen.x() + screen.width() - self.width() - 20
            y = screen.y() + screen.height() - self.height() - 60
        self.move(x, y)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()
