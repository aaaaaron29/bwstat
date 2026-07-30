from dataclasses import dataclass
from datetime import datetime, timedelta

from storage import history


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else float(numerator)


@dataclass(frozen=True)
class Delta:
    username: str
    days: int
    current_level: int
    baseline_date: datetime
    current_date: datetime
    wins_gained: int
    losses_gained: int
    final_kills_gained: int
    final_deaths_gained: int

    @property
    def wlr_period(self) -> float:
        return _ratio(self.wins_gained, self.losses_gained)

    @property
    def fkdr_period(self) -> float:
        return _ratio(self.final_kills_gained, self.final_deaths_gained)


def compute_delta(username: str, days: int) -> Delta | None:
    current_entry = history.latest_entry(username)
    if current_entry is None:
        return None
    current_date, current_stats = current_entry

    cutoff = current_date - timedelta(days=days)
    baseline_entry = history.snapshot_before(username, cutoff)
    if baseline_entry is None:
        return None
    baseline_date, baseline_stats = baseline_entry

    if baseline_date == current_date:
        return None

    return Delta(
        username=username,
        days=days,
        current_level=current_stats.level,
        baseline_date=baseline_date,
        current_date=current_date,
        wins_gained=current_stats.overall.wins - baseline_stats.overall.wins,
        losses_gained=current_stats.overall.losses - baseline_stats.overall.losses,
        final_kills_gained=current_stats.overall.final_kills - baseline_stats.overall.final_kills,
        final_deaths_gained=current_stats.overall.final_deaths - baseline_stats.overall.final_deaths,
    )
