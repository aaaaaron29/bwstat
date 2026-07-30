from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from models.bedwars_stats import ModeStats

GREEN = "#4ade80"
RED = "#f87171"
GOLD = "#fbbf24"
BORDER = "#f5b942"

CARD_STYLE = f"""
QFrame#summaryCard {{
    background-color: #1c1f26;
    border: 2px solid {BORDER};
    border-radius: 10px;
}}
QLabel#summaryCaption {{
    color: #9aa0ac;
    font-size: 12px;
}}
QLabel#summaryLevels {{
    color: {GOLD};
    font-size: 13px;
    font-weight: 700;
}}
"""


def _fmt(value: int) -> str:
    return f"{value:,}"


class SummaryCard(QFrame):
    """Color-coded Wins/Losses/WLR-style overview card.

    Takes any ModeStats — either a lifetime total (Search tab) or a
    period gain (Tracked tab) — since both are shaped the same way.
    """

    def __init__(self, overall: ModeStats, level_gained: int | None = None):
        super().__init__()
        self.setObjectName("summaryCard")
        self.setStyleSheet(CARD_STYLE)

        left = [
            ("Wins", _fmt(overall.wins), GREEN),
            ("Losses", _fmt(overall.losses), RED),
            ("WLR", f"{overall.wlr:.2f}", GOLD),
            ("Beds Broken", _fmt(overall.beds_broken), GREEN),
            ("Beds Lost", _fmt(overall.beds_lost), RED),
            ("BBLR", f"{overall.bblr:.2f}", GOLD),
        ]
        right = [
            ("Final Kills", _fmt(overall.final_kills), GREEN),
            ("Final Deaths", _fmt(overall.final_deaths), RED),
            ("FKDR", f"{overall.fkdr:.2f}", GOLD),
            ("Kills", _fmt(overall.kills), GREEN),
            ("Deaths", _fmt(overall.deaths), RED),
            ("KDR", f"{overall.kdr:.2f}", GOLD),
        ]

        grid = QGridLayout()
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(4)
        for row, (caption, value, color) in enumerate(left):
            grid.addWidget(self._pair(caption, value, color), row, 0)
        for row, (caption, value, color) in enumerate(right):
            grid.addWidget(self._pair(caption, value, color), row, 1)

        outer = QVBoxLayout(self)
        outer.addLayout(grid)

        if level_gained is not None:
            levels_label = QLabel(f"Levels Gained: +{level_gained}")
            levels_label.setObjectName("summaryLevels")
            levels_label.setAlignment(Qt.AlignCenter)
            outer.addWidget(levels_label)

    @staticmethod
    def _pair(caption: str, value: str, color: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        caption_label = QLabel(f"{caption}:")
        caption_label.setObjectName("summaryCaption")

        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 13px;")

        layout.addWidget(caption_label)
        layout.addWidget(value_label)
        layout.addStretch()
        return row
