import sys

from PySide6.QtWidgets import QApplication

from src.config import load_config
from src.pet_window import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    # 桌宠窗口是 Qt.Tool，不计入「最后一个可见窗口」；对话框是唯一普通窗口，
    # 关掉它会触发 QApplication 默认的 quitOnLastWindowClosed 而整个程序退出。
    app.setQuitOnLastWindowClosed(False)
    config = load_config()
    pet = PetWindow(config)
    pet.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
