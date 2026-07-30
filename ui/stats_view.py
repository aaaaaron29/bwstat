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

from models.bedwars_stats import BedwarsStats, ModeStats

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


class ModeTable(QTableWidget):
    """Renders a Solo/Doubles/3v3v3v3/4v4v4v4/4v4/Overall breakdown table.

    Used both for lifetime totals (Search tab) and for period gains
    (Tracked tab) — both are ModeStats-shaped, so the same rendering works.
    """

    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)
        self.setColumnCount(len(COLUMNS))
        self.setHorizontalHeaderLabels(COLUMNS)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setMinimumHeight(260)

    def set_rows(self, modes: list[ModeStats], overall: ModeStats) -> None:
        rows = list(modes) + [overall]
        self.setRowCount(len(rows))

        for r, mode in enumerate(rows):
            is_overall = mode is overall
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

                self.setItem(r, c, item)


class StatsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.header_layout = QHBoxLayout()
        layout.addLayout(self.header_layout)

        self.table = ModeTable()
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

        self.table.set_rows(stats.modes, stats.overall)

    def clear(self) -> None:
        self._clear_header()
        self.table.setRowCount(0)
