import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from models.bedwars_stats import BedwarsStats, ModeStats

HISTORY_PATH = Path(__file__).resolve().parent.parent / "history.json"


def _load() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    with HISTORY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(entries: list[dict]) -> None:
    with HISTORY_PATH.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def add_entry(stats: BedwarsStats) -> None:
    entries = _load()
    entries.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": asdict(stats),
        }
    )
    _save(entries)


def recent_usernames(limit: int = 20) -> list[str]:
    seen: list[str] = []
    for entry in reversed(_load()):
        username = entry["stats"]["username"]
        if username not in seen:
            seen.append(username)
        if len(seen) >= limit:
            break
    return seen


def _stats_from_dict(data: dict) -> BedwarsStats:
    return BedwarsStats(
        username=data["username"],
        level=data["level"],
        winstreak=data["winstreak"],
        coins=data["coins"],
        overall=ModeStats(**data["overall"]),
        modes=[ModeStats(**m) for m in data["modes"]],
    )


def latest_for(username: str) -> BedwarsStats | None:
    for entry in reversed(_load()):
        if entry["stats"]["username"].lower() == username.lower():
            return _stats_from_dict(entry["stats"])
    return None
