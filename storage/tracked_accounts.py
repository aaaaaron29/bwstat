import json
from pathlib import Path

from config import TRACKED_USERNAMES

TRACKED_PATH = Path(__file__).resolve().parent.parent / "tracked_accounts.json"


def load() -> list[str]:
    if not TRACKED_PATH.exists():
        return list(TRACKED_USERNAMES)
    with TRACKED_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(usernames: list[str]) -> None:
    with TRACKED_PATH.open("w", encoding="utf-8") as f:
        json.dump(usernames, f, indent=2)


def add(username: str) -> None:
    usernames = load()
    if username.lower() not in (u.lower() for u in usernames):
        usernames.append(username)
        _save(usernames)


def remove(username: str) -> None:
    usernames = [u for u in load() if u.lower() != username.lower()]
    _save(usernames)
