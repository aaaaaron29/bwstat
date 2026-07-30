from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config import TRACKED_USERNAMES
from storage import history
from tracking import Delta, compute_delta
from ui.stats_view import StatTile

CARD_STYLE = """
QFrame#card {
    background-color: #1c1f26;
    border: 1px solid #2c303a;
    border-radius: 8px;
}
QLabel#cardHeader {
    color: #f2f3f5;
    font-size: 15px;
    font-weight: 700;
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
QPushButton#refresh {
    background-color: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#refresh:hover {
    background-color: #2563eb;
}
"""

def _delta_tiles(delta: Delta) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(StatTile("Wins", f"+{delta.wins_gained:,}"))
    row.addWidget(StatTile("Final Kills", f"+{delta.final_kills_gained:,}"))
    row.addWidget(StatTile("WLR", f"{delta.wlr_period:.2f}"))
    row.addWidget(StatTile("FKDR", f"{delta.fkdr_period:.2f}"))
    return row


class RefreshWorker(QThread):
    finished_ok = Signal()

    def run(self) -> None:
        from snapshot import snapshot_all

        snapshot_all()
        self.finished_ok.emit()


class TrackedView(QWidget):
    def __init__(self):
        super().__init__()
        self._worker: RefreshWorker | None = None

        outer_layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Now")
        self.refresh_button.setObjectName("refresh")
        self.refresh_button.clicked.connect(self._on_refresh)
        top_row.addWidget(self.refresh_button)
        top_row.addStretch()
        outer_layout.addLayout(top_row)

        self.cards_layout = QVBoxLayout()
        cards_container = QWidget()
        cards_container.setLayout(self.cards_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(cards_container)
        outer_layout.addWidget(scroll)

        self.refresh_view()

    def _clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def refresh_view(self) -> None:
        self._clear_cards()
        for username in TRACKED_USERNAMES:
            self.cards_layout.addWidget(self._build_card(username))
        self.cards_layout.addStretch()

    def _build_card(self, username: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(CARD_STYLE)
        layout = QVBoxLayout(card)

        latest = history.latest_entry(username)
        if latest is None:
            header = QLabel(username)
            header.setObjectName("cardHeader")
            layout.addWidget(header)
            placeholder = QLabel("No data yet. Click Refresh Now to take the first snapshot.")
            placeholder.setObjectName("placeholder")
            layout.addWidget(placeholder)
            return card

        last_updated, stats = latest
        header = QLabel(f"{username} — Level {stats.level}")
        header.setObjectName("cardHeader")
        layout.addWidget(header)

        meta = QLabel(f"Last updated: {last_updated.strftime('%Y-%m-%d %H:%M UTC')}")
        meta.setObjectName("cardMeta")
        layout.addWidget(meta)

        for label, days in (("This Week", 7), ("This Month", 30)):
            period_label = QLabel(label.upper())
            period_label.setObjectName("periodLabel")
            layout.addWidget(period_label)

            delta = compute_delta(username, days)
            if delta is None:
                placeholder = QLabel(
                    f"Not enough history yet — need at least {days} days of daily snapshots."
                )
                placeholder.setObjectName("placeholder")
                layout.addWidget(placeholder)
            else:
                layout.addLayout(_delta_tiles(delta))

        return card

    def _on_refresh(self) -> None:
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Refreshing...")

        self._worker = RefreshWorker()
        self._worker.finished_ok.connect(self._on_refresh_done)
        self._worker.start()

    def _on_refresh_done(self) -> None:
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh Now")
        self.refresh_view()
