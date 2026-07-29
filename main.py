import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from config import MissingApiKeyError, get_api_key
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)

    try:
        api_key = get_api_key()
    except MissingApiKeyError as e:
        QMessageBox.critical(None, "Missing API Key", str(e))
        sys.exit(1)

    window = MainWindow(api_key)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
