from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from models.bedwars_stats import ModeStats
from storage import history

PERIOD_LABELS = {
    "today": "Today",
    "week": "This Week",
    "month": "This Month",
    "year": "This Year",
}


def _period_start(period: str, local_now: datetime) -> datetime:
    midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        return midnight
    if period == "week":
        return midnight - timedelta(days=local_now.weekday())
    if period == "month":
        return midnight.replace(day=1)
    if period == "year":
        return midnight.replace(month=1, day=1)
    raise ValueError(f"Unknown period: {period}")


def _gained_mode(current: ModeStats, baseline: ModeStats) -> ModeStats:
    return ModeStats(
        label=current.label,
        kills=current.kills - baseline.kills,
        deaths=current.deaths - baseline.deaths,
        final_kills=current.final_kills - baseline.final_kills,
        final_deaths=current.final_deaths - baseline.final_deaths,
        wins=current.wins - baseline.wins,
        losses=current.losses - baseline.losses,
        beds_broken=current.beds_broken - baseline.beds_broken,
        beds_lost=current.beds_lost - baseline.beds_lost,
    )


@dataclass(frozen=True)
class PeriodStats:
    username: str
    period: str
    baseline_date: datetime
    current_date: datetime
    partial: bool
    current_level: int
    level_gained: int
    overall: ModeStats
    modes: list[ModeStats]

    @property
    def label(self) -> str:
        return PERIOD_LABELS[self.period]


def compute_period(username: str, period: str) -> PeriodStats | None:
    current_entry = history.latest_entry(username)
    if current_entry is None:
        return None
    current_date, current_stats = current_entry

    local_now = current_date.astimezone()
    start_local = _period_start(period, local_now)
    start_utc = start_local.astimezone(timezone.utc)

    baseline_entry = history.snapshot_before(username, start_utc)
    partial = False
    if baseline_entry is None:
        baseline_entry = history.earliest_entry(username)
        partial = True

    if baseline_entry is None:
        return None
    baseline_date, baseline_stats = baseline_entry

    if baseline_date == current_date:
        return None

    return PeriodStats(
        username=username,
        period=period,
        baseline_date=baseline_date,
        current_date=current_date,
        partial=partial,
        current_level=current_stats.level,
        level_gained=current_stats.level - baseline_stats.level,
        overall=_gained_mode(current_stats.overall, baseline_stats.overall),
        modes=[
            _gained_mode(c, b)
            for c, b in zip(current_stats.modes, baseline_stats.modes)
        ],
    )
