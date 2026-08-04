from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from api.hypixel_client import HypixelApiError, InvalidApiKeyError, RateLimitedError
from api.mojang_client import PlayerNotFoundError
from models.bedwars_stats import NoBedwarsStatsError
from storage import history, tracked_accounts
from tracking import PERIOD_LABELS, PeriodStats, compute_period
from ui.stats_view import ModeTable
from ui.summary_card import SummaryCard

CARD_STYLE = """
QFrame#card {
    background-color: #1c1f26;
    border: 1px solid #2c303a;
    border-radius: 8px;
}
QLabel#cardMeta {
    color: #6b7280;
    font-size: 11px;
}
QLabel#periodLabel {
    color: #9aa0ac;
    font-size: 12px;
    font-weight: 600;
}
QLabel#placeholder {
    color: #6b7280;
    font-size: 12px;
    font-style: italic;
}
QComboBox {
    background-color: #23262e;
    color: #f2f3f5;
    border: 1px solid #2c303a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
    font-weight: 700;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #9aa0ac;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #23262e;
    color: #f2f3f5;
    border: 1px solid #2c303a;
    outline: none;
    selection-background-color: #3b82f6;
    selection-color: white;
}
QPushButton#refresh, QPushButton#addButton {
    background-color: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#refresh:hover, QPushButton#addButton:hover {
    background-color: #2563eb;
}
QPushButton#removeButton {
    background-color: #3a1f22;
    color: #f87171;
    border: 1px solid #5c2b2f;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton#removeButton:hover {
    background-color: #4a2529;
}
"""

PERIODS = ["today", "week", "month", "year"]


def _clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


def _period_section(period: PeriodStats) -> QVBoxLayout:
    section = QVBoxLayout()

    label_text = period.label.upper()
    if period.partial:
        label_text += f" (since {period.baseline_date.astimezone().strftime('%b %d')} — tracking just started)"
    label = QLabel(label_text)
    label.setObjectName("periodLabel")
    section.addWidget(label)

    section.addWidget(SummaryCard(period.overall, period.level_gained))

    table = ModeTable()
    table.set_rows(period.modes, period.overall)
    section.addWidget(table)
    return section


class TrackedCard(QFrame):
    remove_requested = Signal(str)

    def __init__(self, username: str, all_usernames: list[str]):
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet(CARD_STYLE)

        outer = QVBoxLayout(self)

        header_row = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.addItems(all_usernames)
        self.combo.setCurrentText(username)
        self.combo.currentTextChanged.connect(self._load_username)
        header_row.addWidget(self.combo)

        remove_button = QPushButton("Remove")
        remove_button.setObjectName("removeButton")
        remove_button.clicked.connect(
            lambda: self.remove_requested.emit(self.combo.currentText())
        )
        header_row.addWidget(remove_button)
        header_row.addStretch()
        outer.addLayout(header_row)

        self.meta_label = QLabel()
        self.meta_label.setObjectName("cardMeta")
        outer.addWidget(self.meta_label)

        self.body_layout = QVBoxLayout()
        outer.addLayout(self.body_layout)

        self._load_username(username)

    def _load_username(self, username: str) -> None:
        _clear_layout(self.body_layout)

        latest = history.latest_entry(username)
        if latest is None:
            self.meta_label.setText("")
            placeholder = QLabel("No data yet. Click Refresh Now to take the first snapshot.")
            placeholder.setObjectName("placeholder")
            self.body_layout.addWidget(placeholder)
            return

        last_updated, stats = latest
        self.meta_label.setText(
            f"Level {stats.level} · Last updated "
            f"{last_updated.astimezone().strftime('%Y-%m-%d %H:%M')}"
        )

        for period_key in PERIODS:
            period = compute_period(username, period_key)
            if period is None:
                label = QLabel(PERIOD_LABELS[period_key].upper())
                label.setObjectName("periodLabel")
                self.body_layout.addWidget(label)

                placeholder = QLabel("Not enough history yet.")
                placeholder.setObjectName("placeholder")
                self.body_layout.addWidget(placeholder)
            else:
                self.body_layout.addLayout(_period_section(period))


class RefreshWorker(QThread):
    finished_ok = Signal()

    def run(self) -> None:
        from snapshot import snapshot_all

        snapshot_all()
        self.finished_ok.emit()


class AddPlayerWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, username: str):
        super().__init__()
        self._username = username

    def run(self) -> None:
        from snapshot import snapshot_one

        try:
            snapshot_one(self._username)
        except PlayerNotFoundError:
            self.failed.emit(f"No Minecraft account named '{self._username}'.")
        except NoBedwarsStatsError:
            self.failed.emit(f"'{self._username}' has no Bedwars stats yet.")
        except InvalidApiKeyError:
            self.failed.emit("Hypixel rejected the API key.")
        except RateLimitedError:
            self.failed.emit("Rate limited by Hypixel. Try again in a moment.")
        except HypixelApiError as e:
            self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(f"Unexpected error: {e}")
        else:
            tracked_accounts.add(self._username)
            self.succeeded.emit(self._username)


class TrackedView(QWidget):
    def __init__(self):
        super().__init__()
        self._refresh_worker: RefreshWorker | None = None
        self._add_worker: AddPlayerWorker | None = None
        self._current_username: str | None = None

        outer_layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Now")
        self.refresh_button.setObjectName("refresh")
        self.refresh_button.clicked.connect(self._on_refresh)
        top_row.addWidget(self.refresh_button)

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("Add a Minecraft username...")
        self.add_input.returnPressed.connect(self._on_add)
        top_row.addWidget(self.add_input)

        self.add_button = QPushButton("Add Player")
        self.add_button.setObjectName("addButton")
        self.add_button.clicked.connect(self._on_add)
        top_row.addWidget(self.add_button)

        top_row.addStretch()
        outer_layout.addLayout(top_row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #9aa0ac; font-size: 12px;")
        outer_layout.addWidget(self.status_label)

        self.cards_layout = QVBoxLayout()
        cards_container = QWidget()
        cards_container.setLayout(self.cards_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(cards_container)
        outer_layout.addWidget(scroll)

        self.refresh_view()

    def refresh_view(self) -> None:
        _clear_layout(self.cards_layout)
        usernames = tracked_accounts.load()

        if not usernames:
            self._current_username = None
            placeholder = QLabel("No tracked accounts yet. Add one above.")
            placeholder.setStyleSheet("color: #6b7280; font-size: 12px; font-style: italic;")
            self.cards_layout.addWidget(placeholder)
            self.cards_layout.addStretch()
            return

        if self._current_username not in usernames:
            self._current_username = usernames[0]

        card = TrackedCard(self._current_username, usernames)
        card.combo.currentTextChanged.connect(self._on_selection_changed)
        card.remove_requested.connect(self._on_remove)
        self.cards_layout.addWidget(card)
        self.cards_layout.addStretch()

    def _on_selection_changed(self, username: str) -> None:
        self._current_username = username

    def _on_remove(self, username: str) -> None:
        tracked_accounts.remove(username)
        if self._current_username == username:
            self._current_username = None
        self.refresh_view()

    def _on_refresh(self) -> None:
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Refreshing...")

        self._refresh_worker = RefreshWorker()
        self._refresh_worker.finished_ok.connect(self._on_refresh_done)
        self._refresh_worker.start()

    def _on_refresh_done(self) -> None:
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh Now")
        self.refresh_view()

    def _on_add(self) -> None:
        username = self.add_input.text().strip()
        if not username:
            return

        self.add_button.setEnabled(False)
        self.status_label.setStyleSheet("color: #9aa0ac; font-size: 12px;")
        self.status_label.setText(f"Adding {username}...")

        self._add_worker = AddPlayerWorker(username)
        self._add_worker.succeeded.connect(self._on_add_succeeded)
        self._add_worker.failed.connect(self._on_add_failed)
        self._add_worker.finished.connect(lambda: self.add_button.setEnabled(True))
        self._add_worker.start()

    def _on_add_succeeded(self, username: str) -> None:
        self.status_label.setText("")
        self.add_input.clear()
        self._current_username = username
        self.refresh_view()

    def _on_add_failed(self, message: str) -> None:
        self.status_label.setStyleSheet("color: #f87171; font-size: 12px;")
        self.status_label.setText(message)
