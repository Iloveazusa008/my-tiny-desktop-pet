from __future__ import annotations

from PySide6.QtCore import QThread, Signal

# 运行中的线程强引用池：对话框销毁（abort 后线程可能还差几帧才退出）时
# 由本模块代持引用，避免 QThread 被 GC「Destroyed while thread is still running」
_live_workers: set["ChatStreamWorker"] = set()


class ChatStreamWorker(QThread):
    """后台流式请求线程：迭代 OpenAI 兼容接口的 stream，逐字发 delta。

    delta(str)      流式增量文本
    completed(str)  完整回复文本（未中断时才发）
    failed(str)     错误说明（未中断时才发）
    中断：abort() 置标志并关闭底层流，循环随即退出，中断后不再发任何信号。
    """

    delta = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, api: dict, messages: list[dict], parent=None) -> None:
        super().__init__(parent)
        self._api = api or {}
        self._messages = messages
        self._aborted = False
        self._stream = None
        _live_workers.add(self)
        self.finished.connect(self._release)

    def _release(self) -> None:
        _live_workers.discard(self)
        self.deleteLater()

    def abort(self) -> None:
        self._aborted = True
        stream = self._stream
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass

    def run(self) -> None:
        try:
            from openai import OpenAI

            model = (self._api.get("model") or "").strip()
            if not model:
                self.failed.emit("config.yaml 中 api.model 未配置")
                return
            client = OpenAI(
                base_url=(self._api.get("base_url") or None),
                api_key=(self._api.get("api_key") or "").strip(),
                timeout=float(self._api.get("timeout_s", 60) or 60),
            )
            self._stream = client.chat.completions.create(
                model=model,
                messages=self._messages,
                stream=True,
            )
            parts: list[str] = []
            for chunk in self._stream:
                if self._aborted:
                    return
                if not chunk.choices:
                    continue
                text = chunk.choices[0].delta.content
                if not text:
                    continue
                parts.append(text)
                self.delta.emit(text)
            if self._aborted:
                return
            self.completed.emit("".join(parts))
        except Exception as exc:
            if self._aborted:
                return
            self.failed.emit(str(exc) or exc.__class__.__name__)
