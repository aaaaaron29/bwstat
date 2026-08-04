from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config
from api.hypixel_client import InvalidApiKeyError, RateLimitedError, get_player
from api.mojang_client import get_uuid

# A long-lived, always-real account — used only to check whether the key
# itself is accepted by Hypixel, regardless of whether this account has
# Bedwars stats.
TEST_USERNAME = "Hypixel"

STYLE = """
QLabel#heading {
    color: #f2f3f5;
    font-size: 14px;
    font-weight: 700;
}
QLabel#hint {
    color: #6b7280;
    font-size: 11px;
}
"""


class KeyTestWorker(QThread):
    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, api_key: str):
        super().__init__()
        self._api_key = api_key

    def run(self) -> None:
        try:
            uuid = get_uuid(TEST_USERNAME)
            get_player(uuid, self._api_key)
        except InvalidApiKeyError:
            self.failed.emit("That key was rejected by Hypixel. Double-check it and try again.")
        except RateLimitedError:
            self.failed.emit("Rate limited while testing — try Save again in a moment.")
        except Exception as e:
            self.failed.emit(f"Couldn't verify the key: {e}")
        else:
            self.succeeded.emit()


class SettingsView(QWidget):
    key_updated = Signal(str)

    def __init__(self):
        super().__init__()
        self.setStyleSheet(STYLE)
        self._worker: KeyTestWorker | None = None
        self._pending_key: str | None = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        heading = QLabel("Hypixel API Key")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        hint = QLabel("Get one at developer.hypixel.net. Saving tests it against Hypixel first.")
        hint.setObjectName("hint")
        layout.addWidget(hint)

        row = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        try:
            self.key_input.setText(config.get_api_key())
        except config.MissingApiKeyError:
            pass
        row.addWidget(self.key_input)

        self.show_checkbox = QCheckBox("Show")
        self.show_checkbox.toggled.connect(self._on_toggle_show)
        row.addWidget(self.show_checkbox)
        layout.addLayout(row)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_save)
        layout.addWidget(self.save_button)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #9aa0ac; font-size: 12px;")
        layout.addWidget(self.status_label)

    def _on_toggle_show(self, checked: bool) -> None:
        self.key_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def _on_save(self) -> None:
        new_key = self.key_input.text().strip()
        if not new_key:
            return

        self._pending_key = new_key
        self.save_button.setEnabled(False)
        self.status_label.setStyleSheet("color: #9aa0ac; font-size: 12px;")
        self.status_label.setText("Testing key against Hypixel...")

        self._worker = KeyTestWorker(new_key)
        self._worker.succeeded.connect(self._on_test_succeeded)
        self._worker.failed.connect(self._on_test_failed)
        self._worker.finished.connect(lambda: self.save_button.setEnabled(True))
        self._worker.start()

    def _on_test_succeeded(self) -> None:
        config.set_api_key(self._pending_key)
        self.status_label.setStyleSheet("color: #4ade80; font-size: 12px;")
        self.status_label.setText("Saved — key verified and updated.")
        self.key_updated.emit(self._pending_key)

    def _on_test_failed(self, message: str) -> None:
        self.status_label.setStyleSheet("color: #f87171; font-size: 12px;")
        self.status_label.setText(message)
