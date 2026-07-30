from __future__ import annotations

from dataclasses import dataclass


class NoBedwarsStatsError(Exception):
    """Raised when a Hypixel player exists but has no recorded Bedwars stats."""


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else float(numerator)


@dataclass(frozen=True)
class ModeStats:
    label: str
    kills: int
    deaths: int
    final_kills: int
    final_deaths: int
    wins: int
    losses: int
    beds_broken: int
    beds_lost: int = 0  # defaulted: older history.json entries predate this field

    @property
    def kdr(self) -> float:
        return _ratio(self.kills, self.deaths)

    @property
    def fkdr(self) -> float:
        return _ratio(self.final_kills, self.final_deaths)

    @property
    def wlr(self) -> float:
        return _ratio(self.wins, self.losses)

    @property
    def bblr(self) -> float:
        return _ratio(self.beds_broken, self.beds_lost)


_MODE_PREFIXES = {
    "Solo": "eight_one",
    "Doubles": "eight_two",
    "3v3v3v3": "four_three",
    "4v4v4v4": "four_four",
    "4v4": "two_four",
}


def _mode_from_json(stats: dict, label: str, prefix: str | None) -> ModeStats:
    p = f"{prefix}_" if prefix else ""
    return ModeStats(
        label=label,
        kills=stats.get(f"{p}kills_bedwars", 0),
        deaths=stats.get(f"{p}deaths_bedwars", 0),
        final_kills=stats.get(f"{p}final_kills_bedwars", 0),
        final_deaths=stats.get(f"{p}final_deaths_bedwars", 0),
        wins=stats.get(f"{p}wins_bedwars", 0),
        losses=stats.get(f"{p}losses_bedwars", 0),
        beds_broken=stats.get(f"{p}beds_broken_bedwars", 0),
        beds_lost=stats.get(f"{p}beds_lost_bedwars", 0),
    )


@dataclass(frozen=True)
class BedwarsStats:
    username: str
    level: int
    winstreak: int | None
    coins: int
    overall: ModeStats
    modes: list[ModeStats]

    @classmethod
    def from_api_json(cls, player: dict, username: str) -> "BedwarsStats":
        stats = player.get("stats", {}).get("Bedwars")
        if not stats:
            raise NoBedwarsStatsError(f"{username} has no Bedwars stats")

        modes = [
            _mode_from_json(stats, label, prefix)
            for label, prefix in _MODE_PREFIXES.items()
        ]

        return cls(
            username=username,
            level=player.get("achievements", {}).get("bedwars_level", 0),
            winstreak=stats.get("winstreak"),
            coins=stats.get("coins", 0),
            overall=_mode_from_json(stats, "Overall", None),
            modes=modes,
        )
