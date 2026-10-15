from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ---------- 视觉参数（集中定义，便于调整） ----------
BACKGROUND_COLOR = "#FFFFFF"  # 内层背景
BORDER_COLOR = "#8A2BE2"  # 紫边
BORDER_WIDTH = 2  # 整数，避免高 DPI 下发虚
BORDER_RADIUS = 12
SHADOW_BLUR_RADIUS = 24.0
SHADOW_OFFSET = QPointF(0.0, 4.0)
SHADOW_COLOR = QColor(0, 0, 0, 60)
OUTER_MARGIN = 20  # 外层留白：给阴影绘制空间
INNER_MARGIN = 12  # 内层布局留白：≥ 圆角半径，避免子控件盖住圆角
CLOSE_CHAR = "×"
CLOSE_COLOR = BORDER_COLOR
CLOSE_HOVER_COLOR = "#5C1DB8"
CLOSE_BUTTON_SIZE = 24

DIALOG_WIDTH = 360
DIALOG_HEIGHT = 210  # 默认高度减半（原 420）；最小高度须 ≤ 默认值，否则 resize 会被最小尺寸顶回
DEFAULT_INPUT_PLACEHOLDER = "输入消息，Enter 发送"  # 配置缺失/留空时的回退文案


class ChatDialog(QWidget):
    """对话框：由右键菜单「开始对话」唤起，关闭即清空会话记忆。

    AI 尚未接入：先提供多轮输入骨架，历史仅存于本次会话（_history）。
    关闭方式：右上角小叉、Esc、点外部（窗口失活即关）。
    外观：无系统装饰（Frameless + 透明），外层（对话框本身）留白给阴影，
    内层白底紫边圆角 + 阴影；顶部行（标题区）可按住拖动窗口。
    """

    closed = Signal()
    drag_moved = Signal(QPoint)  # 标题区拖动的请求位移；落位（屏内钳制/翻面）由桌宠窗口统一裁决

    def __init__(self, input_placeholder: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("对话")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.setMinimumSize(320, 160)

        self._history: list[dict[str, str]] = []
        self._drag_offset: QPoint | None = None

        # 外层 = 对话框本身（透明），margin 留出阴影空间
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN)

        # 内层：白底、紫边、圆角、阴影
        self._inner = QWidget(self)
        self._inner.setObjectName("inner")
        self._inner.setStyleSheet(
            f"QWidget#inner {{"
            f"  background-color: {BACKGROUND_COLOR};"
            f"  border: {BORDER_WIDTH}px solid {BORDER_COLOR};"
            f"  border-radius: {BORDER_RADIUS}px;"
            f"}}"
        )
        shadow = QGraphicsDropShadowEffect(self._inner)
        shadow.setBlurRadius(SHADOW_BLUR_RADIUS)
        shadow.setOffset(SHADOW_OFFSET)
        shadow.setColor(SHADOW_COLOR)
        self._inner.setGraphicsEffect(shadow)

        inner_layout = QVBoxLayout(self._inner)
        inner_layout.setContentsMargins(INNER_MARGIN, INNER_MARGIN, INNER_MARGIN, INNER_MARGIN)
        inner_layout.setSpacing(8)

        # 顶部行：只放右上角小叉，整条兼作窗口拖动区（无标题文字）
        self._header = QWidget(self._inner)
        self._header.setMinimumHeight(CLOSE_BUTTON_SIZE)
        self._header.installEventFilter(self)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self._close_button = QPushButton(CLOSE_CHAR, self._inner)
        self._close_button.setObjectName("closeButton")
        self._close_button.setFixedSize(CLOSE_BUTTON_SIZE, CLOSE_BUTTON_SIZE)
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_button.setStyleSheet(
            f"QPushButton {{"
            f"  border: none;"
            f"  background: transparent;"
            f"  color: {CLOSE_COLOR};"
            f"  font-size: 16px;"
            f"  font-weight: bold;"
            f"}}"
            f"QPushButton:hover {{"
            f"  color: {CLOSE_HOVER_COLOR};"
            f"  background-color: rgba(138, 43, 226, 40);"
            f"  border-radius: {CLOSE_BUTTON_SIZE // 2}px;"
            f"}}"
        )
        self._close_button.clicked.connect(self.close)

        header_layout.addStretch(1)
        header_layout.addWidget(self._close_button)

        # 只读日志：无边框、无阴影，内容直接写在紫白对话框内部（与白底一体，不另起一层“框”）
        self._log = QPlainTextEdit(self._inner)
        self._log.setReadOnly(True)
        self._log.setFrameShape(QFrame.Shape.NoFrame)
        self._log.setStyleSheet("QPlainTextEdit { background: transparent; border: none; }")
        self._log.setPlaceholderText("AI 对话尚未接入，可先输入测试。")

        # 输入行（提示文案可由配置 chat_dialog.input_placeholder 个性化）
        self._input = QLineEdit(self._inner)
        self._input.setPlaceholderText(input_placeholder or DEFAULT_INPUT_PLACEHOLDER)
        self._send_button = QPushButton("发送", self._inner)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self._input, 1)
        input_layout.addWidget(self._send_button)

        inner_layout.addWidget(self._header)
        inner_layout.addWidget(self._log, 1)
        inner_layout.addLayout(input_layout)

        outer_layout.addWidget(self._inner)

        self._send_button.clicked.connect(self._send)
        self._input.returnPressed.connect(self._send)

        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self.close)

    # ---------- 行为 ----------

    @property
    def history(self) -> list[dict[str, str]]:
        return self._history

    def focus_input(self) -> None:
        self._input.setFocus()

    def _send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._history.append({"role": "user", "content": text})
        self._log.appendPlainText(f"你：{text}")

    def event(self, ev) -> bool:
        if ev.type() == QEvent.Type.WindowDeactivate:
            self.close()  # 点外部即视为关闭并清空
        return super().event(ev)

    def eventFilter(self, watched, event) -> bool:
        # 顶部行拖动窗口：只绑定在标题区，避免输入框选字时窗口乱跑
        if watched is self._header:
            etype = event.type()
            if etype == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if (
                etype == QEvent.Type.MouseMove
                and self._drag_offset is not None
                and (event.buttons() & Qt.MouseButton.LeftButton)
            ):
                new_pos = event.globalPosition().toPoint() - self._drag_offset
                delta = new_pos - self.pos()
                self.drag_moved.emit(delta)  # 只上报请求位移，是否移动、移到哪由桌宠窗口决定
                if self.frameGeometry().topLeft() != new_pos:
                    #落位被桌宠窗口改写（贴屏边钳制/翻面）：按当前位置重算抓取偏移，
                    #否则下一次 move 仍按旧偏移把窗口拽回原处，翻面会来回抖
                    self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if etype == QEvent.Type.MouseButtonRelease and self._drag_offset is not None:
                self._drag_offset = None
                return True
        return super().eventFilter(watched, event)

    def closeEvent(self, event) -> None:
        self._history.clear()  # 关闭即清空全部会话记忆
        self.closed.emit()
        super().closeEvent(event)
