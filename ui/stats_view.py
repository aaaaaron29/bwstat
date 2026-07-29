from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.bedwars_stats import BedwarsStats

ACCENT = "#3b82f6"
OVERALL_ROW_BG = "#20232b"

TILE_STYLE = """
QFrame#tile {
    background-color: #23262e;
    border-radius: 8px;
}
QLabel#tileValue {
    color: #f2f3f5;
    font-size: 18px;
    font-weight: 600;
}
QLabel#tileCaption {
    color: #9aa0ac;
    font-size: 11px;
    font-weight: 500;
}
"""

TABLE_STYLE = """
QTableWidget {
    background-color: #1c1f26;
    color: #d7dae0;
    gridline-color: #2c303a;
    border: 1px solid #2c303a;
    border-radius: 8px;
    font-size: 12px;
}
QHeaderView::section {
    background-color: #23262e;
    color: #9aa0ac;
    padding: 6px;
    border: none;
    font-weight: 600;
    font-size: 11px;
}
"""

COLUMNS = [
    "Type",
    "Kills",
    "Deaths",
    "K/D",
    "Final Kills",
    "Final Deaths",
    "FKDR",
    "Wins",
    "Losses",
    "WLR",
    "Beds Broken",
]

# The stats the user asked to foreground; everything else stays present but muted.
EMPHASIZED_COLUMNS = {"Final Kills", "FKDR", "Wins", "WLR"}


class StatTile(QFrame):
    def __init__(self, caption: str, value: str):
        super().__init__()
        self.setObjectName("tile")
        self.setStyleSheet(TILE_STYLE)

        value_label = QLabel(value)
        value_label.setObjectName("tileValue")
        value_label.setAlignment(Qt.AlignCenter)

        caption_label = QLabel(caption.upper())
        caption_label.setObjectName("tileCaption")
        caption_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(value_label)
        layout.addWidget(caption_label)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)


def _fmt(value: int) -> str:
    return f"{value:,}"


def _ratio(value: float) -> str:
    return f"{value:.2f}"


class StatsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.header_layout = QHBoxLayout()
        layout.addLayout(self.header_layout)

        self.table = QTableWidget()
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(260)
        layout.addWidget(self.table)

    def _clear_header(self) -> None:
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_stats(self, stats: BedwarsStats) -> None:
        self._clear_header()
        self.header_layout.addWidget(StatTile("Player", stats.username))
        self.header_layout.addWidget(StatTile("Level", str(stats.level)))
        self.header_layout.addWidget(
            StatTile(
                "Winstreak",
                str(stats.winstreak) if stats.winstreak is not None else "Hidden",
            )
        )
        self.header_layout.addWidget(StatTile("Tokens", _fmt(stats.coins)))

        rows = list(stats.modes) + [stats.overall]
        self.table.setRowCount(len(rows))

        for r, mode in enumerate(rows):
            is_overall = mode is stats.overall
            values = [
                mode.label if not is_overall else "Overall",
                _fmt(mode.kills),
                _fmt(mode.deaths),
                _ratio(mode.kdr),
                _fmt(mode.final_kills),
                _fmt(mode.final_deaths),
                _ratio(mode.fkdr),
                _fmt(mode.wins),
                _fmt(mode.losses),
                _ratio(mode.wlr),
                _fmt(mode.beds_broken),
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)

                col_name = COLUMNS[c]
                emphasize = col_name in EMPHASIZED_COLUMNS or c == 0
                if emphasize:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                if col_name in EMPHASIZED_COLUMNS:
                    item.setForeground(QColor(ACCENT))
                if is_overall:
                    item.setBackground(QColor(OVERALL_ROW_BG))

                self.table.setItem(r, c, item)

    def clear(self) -> None:
        self._clear_header()
        self.table.setRowCount(0)
