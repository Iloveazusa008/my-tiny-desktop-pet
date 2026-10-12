import sys

from PySide6.QtWidgets import QApplication

from src.config import load_config
from src.pet_window import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    config = load_config()
    pet = PetWindow(config)
    pet.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
