from datetime import datetime, timezone

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import config
from api.hypixel_client import HypixelApiError, InvalidApiKeyError, RateLimitedError, get_player
from api.mojang_client import PlayerNotFoundError, get_uuid
from log_watcher import LobbyLogParser
from models.bedwars_stats import BedwarsStats, NoBedwarsStatsError
from storage import tracked_accounts

SOURCE_LABELS = {"who": "/who", "party": "/party list", "speaker": "pregame chat"}

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

COLUMNS = ["Player", "Level", "FKDR", "WLR", "Wins", "Final Kills"]
POLL_INTERVAL_MS = 500
FKDR_COLUMN = 2

# <1 muted, 1-4.9 green, 5-9.9 gold, 10-24.9 red, 25+ purple
FKDR_TIERS = [
    (1, "#9aa0ac"),
    (5, "#4ade80"),
    (10, "#fbbf24"),
    (25, "#f87171"),
]
FKDR_TOP_COLOR = "#a855f7"


def _fkdr_color(fkdr: float) -> str:
    for threshold, color in FKDR_TIERS:
        if fkdr < threshold:
            return color
    return FKDR_TOP_COLOR


class LogTailWorker(QThread):
    detected = Signal(str, list)

    def run(self) -> None:
        parser = LobbyLogParser(tracked_accounts.load())
        path = config.get_log_path()

        try:
            # Minecraft/Lunar write logs as Windows-1252, not UTF-8 — using
            # utf-8 here silently mangles every §-color-code byte.
            f = open(path, "r", encoding="cp1252", errors="replace")
        except OSError:
            return

        with f:
            f.seek(0, 2)  # start at end-of-file; only react to new activity
            position = f.tell()

            while not self.isInterruptionRequested():
                line = f.readline()
                if line and line.endswith("\n"):
                    position = f.tell()
                    result = parser.feed(line)
                    if result:
                        self.detected.emit(result[0], result[1])
                    continue

                # no complete line yet — check for truncation (new session) then wait
                f.seek(0, 2)
                size = f.tell()
                if size < position:
                    position = 0
                f.seek(position)
                self.msleep(POLL_INTERVAL_MS)


class LobbyLookupWorker(QThread):
    finished_with = Signal(list)

    def __init__(self, usernames: list[str]):
        super().__init__()
        self._usernames = usernames

    def run(self) -> None:
        api_key = config.get_api_key()
        results: list[tuple[str, BedwarsStats | None]] = []

        for username in self._usernames:
            try:
                uuid = get_uuid(username)
                player = get_player(uuid, api_key)
                stats = BedwarsStats.from_api_json(player, username)
            except (
                PlayerNotFoundError,
                NoBedwarsStatsError,
                InvalidApiKeyError,
                RateLimitedError,
                HypixelApiError,
                Exception,
            ):
                results.append((username, None))
            else:
                results.append((username, stats))

        self.finished_with.emit(results)


class LeaderboardTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)
        self.setColumnCount(len(COLUMNS))
        self.setHorizontalHeaderLabels(COLUMNS)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setSortingEnabled(True)

    def set_rows(self, results: list[tuple[str, BedwarsStats | None]]) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(len(results))

        for r, (username, stats) in enumerate(results):
            if stats is None:
                values = [username, "—", "—", "—", "—", "—"]
            else:
                values = [
                    username,
                    stats.level,
                    round(stats.overall.fkdr, 2),
                    round(stats.overall.wlr, 2),
                    stats.overall.wins,
                    stats.overall.final_kills,
                ]

            for c, value in enumerate(values):
                item = QTableWidgetItem()
                item.setData(Qt.DisplayRole, value)
                if c == FKDR_COLUMN and stats is not None:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setForeground(QColor(_fkdr_color(stats.overall.fkdr)))
                self.setItem(r, c, item)

        self.setSortingEnabled(True)
        self.sortItems(2, Qt.DescendingOrder)  # FKDR, highest first


class LobbyView(QWidget):
    def __init__(self):
        super().__init__()
        self._tail_worker: LogTailWorker | None = None
        self._lookup_workers: list[LobbyLookupWorker] = []
        # Accumulated for the current lobby — everyone seen via /who, /pl,
        # or pregame chat, merged rather than replaced. Cleared on "reset"
        # (one of your tracked accounts joining a fresh match).
        self._known: dict[str, tuple[str, BedwarsStats | None]] = {}
        self._pending: set[str] = set()

        layout = QVBoxLayout(self)

        self.status_label = QLabel(
            "Watching Lunar Client log for /who, /party list, or pregame chat..."
        )
        self.status_label.setStyleSheet("color: #9aa0ac; font-size: 12px;")
        layout.addWidget(self.status_label)

        self.table = LeaderboardTable()
        layout.addWidget(self.table)

        self._start_watching()

    def _start_watching(self) -> None:
        self._tail_worker = LogTailWorker()
        self._tail_worker.detected.connect(self._on_detected)
        self._tail_worker.start()

    def _on_detected(self, source: str, usernames: list[str]) -> None:
        if source == "reset":
            self._known.clear()
            self._pending.clear()
            self.table.set_rows([])
            self.status_label.setStyleSheet("color: #9aa0ac; font-size: 12px;")
            self.status_label.setText("New lobby detected — watching chat until the game starts...")
            return

        new_usernames = [
            u for u in usernames if u.lower() not in self._known and u.lower() not in self._pending
        ]
        if not new_usernames:
            return
        self._pending.update(u.lower() for u in new_usernames)

        self.status_label.setStyleSheet("color: #9aa0ac; font-size: 12px;")
        self.status_label.setText(
            f"Looking up {len(new_usernames)} player(s) from {SOURCE_LABELS[source]}..."
        )

        worker = LobbyLookupWorker(new_usernames)
        worker.finished_with.connect(lambda results: self._on_lookup_done(source, worker, results))
        self._lookup_workers.append(worker)
        worker.start()

    def _on_lookup_done(
        self,
        source: str,
        worker: "LobbyLookupWorker",
        results: list[tuple[str, BedwarsStats | None]],
    ) -> None:
        if worker in self._lookup_workers:
            self._lookup_workers.remove(worker)

        for username, stats in results:
            self._pending.discard(username.lower())
            self._known[username.lower()] = (username, stats)

        self.table.set_rows(list(self._known.values()))

        now = datetime.now(timezone.utc).astimezone().strftime("%H:%M")
        self.status_label.setStyleSheet("color: #4ade80; font-size: 12px;")
        self.status_label.setText(
            f"{len(self._known)} player(s) tracked — last update via "
            f"{SOURCE_LABELS[source]} at {now}"
        )

    def shutdown(self) -> None:
        if self._tail_worker is not None:
            self._tail_worker.requestInterruption()
            self._tail_worker.wait(2000)
