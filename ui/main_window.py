from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from api.hypixel_client import HypixelApiError, InvalidApiKeyError, RateLimitedError, get_player
from api.mojang_client import PlayerNotFoundError, get_uuid
from models.bedwars_stats import BedwarsStats, NoBedwarsStatsError
from storage import history
from ui.lobby_view import LobbyView
from ui.settings_view import SettingsView
from ui.stats_view import StatsView
from ui.tracked_view import TrackedView

WINDOW_STYLE = """
QMainWindow, QWidget {
    background-color: #14161b;
}
QLineEdit {
    background-color: #1c1f26;
    color: #f2f3f5;
    border: 1px solid #2c303a;
    border-radius: 6px;
    padding: 8px;
    font-size: 13px;
}
QPushButton {
    background-color: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #2563eb;
}
QListWidget {
    background-color: #1c1f26;
    color: #d7dae0;
    border: 1px solid #2c303a;
    border-radius: 6px;
}
QLabel#status {
    color: #f87171;
    font-size: 12px;
}
QTabWidget::pane {
    border: 1px solid #2c303a;
    border-radius: 6px;
}
QTabBar::tab {
    background-color: #1c1f26;
    color: #9aa0ac;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background-color: #23262e;
    color: #f2f3f5;
    font-weight: 600;
}
"""


class SearchWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, username: str, api_key: str):
        super().__init__()
        self._username = username
        self._api_key = api_key

    def run(self) -> None:
        try:
            uuid = get_uuid(self._username)
            player = get_player(uuid, self._api_key)
            stats = BedwarsStats.from_api_json(player, self._username)
        except PlayerNotFoundError:
            self.failed.emit(f"No Minecraft account named '{self._username}'.")
        except NoBedwarsStatsError:
            self.failed.emit(f"'{self._username}' has no Bedwars stats yet.")
        except InvalidApiKeyError:
            self.failed.emit(
                "Hypixel rejected the API key. Check your key at "
                "developer.hypixel.net and update your .env file."
            )
        except RateLimitedError:
            self.failed.emit("Rate limited by Hypixel. Try again in a moment.")
        except HypixelApiError as e:
            self.failed.emit(str(e))
        except Exception as e:  # network errors, timeouts, etc.
            self.failed.emit(f"Unexpected error: {e}")
        else:
            self.succeeded.emit(stats)


class MainWindow(QMainWindow):
    def __init__(self, api_key: str):
        super().__init__()
        self._api_key = api_key
        self._worker: SearchWorker | None = None

        self.setWindowTitle("Bedwars Stat Tracker")
        self.resize(820, 560)
        self.setStyleSheet(WINDOW_STYLE)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Enter a Minecraft username...")
        self.search_box.returnPressed.connect(self._on_search)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._on_search)

        self.paste_button = QPushButton("Paste")
        self.paste_button.clicked.connect(self._on_paste)

        search_row = QHBoxLayout()
        search_row.addWidget(self.search_box)
        search_row.addWidget(self.search_button)
        search_row.addWidget(self.paste_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")

        self.stats_view = StatsView()

        content_layout = QVBoxLayout()
        content_layout.addLayout(search_row)
        content_layout.addWidget(self.status_label)
        content_layout.addWidget(self.stats_view)
        content_layout.addStretch()

        self.history_list = QListWidget()
        self.history_list.setFixedWidth(180)
        self.history_list.itemClicked.connect(self._on_history_clicked)
        self._refresh_history_list()

        root_layout = QHBoxLayout()
        root_layout.addWidget(self.history_list)
        root_layout.addLayout(content_layout, stretch=1)

        search_tab = QWidget()
        search_tab.setLayout(root_layout)

        settings_view = SettingsView()
        settings_view.key_updated.connect(self._on_key_updated)

        self.lobby_view = LobbyView()

        tabs = QTabWidget()
        tabs.addTab(search_tab, "Search")
        tabs.addTab(TrackedView(), "Tracked")
        tabs.addTab(self.lobby_view, "Lobby")
        tabs.addTab(settings_view, "Settings")
        self.setCentralWidget(tabs)

    def _on_key_updated(self, new_key: str) -> None:
        self._api_key = new_key

    def closeEvent(self, event) -> None:
        self.lobby_view.shutdown()
        super().closeEvent(event)

    def _refresh_history_list(self) -> None:
        self.history_list.clear()
        self.history_list.addItems(history.recent_usernames())

    def _on_history_clicked(self, item) -> None:
        cached = history.latest_for(item.text())
        if cached:
            self.status_label.setText("")
            self.stats_view.show_stats(cached)

    def _on_paste(self) -> None:
        clipboard_text = QGuiApplication.clipboard().text().strip()
        if clipboard_text:
            self.search_box.setText(clipboard_text)

    def _on_search(self) -> None:
        username = self.search_box.text().strip()
        if not username:
            return

        self.status_label.setText("Searching...")
        self.search_button.setEnabled(False)

        self._worker = SearchWorker(username, self._api_key)
        self._worker.succeeded.connect(self._on_search_succeeded)
        self._worker.failed.connect(self._on_search_failed)
        self._worker.finished.connect(lambda: self.search_button.setEnabled(True))
        self._worker.start()

    def _on_search_succeeded(self, stats: BedwarsStats) -> None:
        self.status_label.setText("")
        self.stats_view.show_stats(stats)
        history.add_entry(stats)
        self._refresh_history_list()

    def _on_search_failed(self, message: str) -> None:
        self.status_label.setText(message)
        self.stats_view.clear()
