from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

DIALOG_WIDTH = 360
DIALOG_HEIGHT = 420


class ChatDialog(QWidget):
    """对话框：由右键菜单「开始对话」唤起，关闭即清空会话记忆。

    AI 尚未接入：先提供多轮输入骨架，历史仅存于本次会话（_history）。
    关闭方式：标题栏 X、Esc、点外部（窗口失活即关）。
    """

    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("对话")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.setMinimumSize(320, 320)

        self._history: list[dict[str, str]] = []

        self._log = QPlainTextEdit(self)
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("AI 对话尚未接入，可先输入测试。")

        self._input = QLineEdit(self)
        self._input.setPlaceholderText("输入消息，Enter 发送")

        self._send_button = QPushButton("发送", self)

        row = QHBoxLayout()
        row.addWidget(self._input, 1)
        row.addWidget(self._send_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._log, 1)
        layout.addLayout(row)

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

    def closeEvent(self, event) -> None:
        self._history.clear()  # 关闭即清空全部会话记忆
        self.closed.emit()
        super().closeEvent(event)
