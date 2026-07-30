import logging
from pathlib import Path

from api.hypixel_client import get_player
from api.mojang_client import get_uuid
from config import get_api_key
from models.bedwars_stats import BedwarsStats
from storage import history, tracked_accounts

LOG_PATH = Path(__file__).resolve().parent / "snapshot.log"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def snapshot_one(username: str) -> None:
    api_key = get_api_key()
    uuid = get_uuid(username)
    player = get_player(uuid, api_key)
    stats = BedwarsStats.from_api_json(player, username)
    history.add_entry(stats)


def snapshot_all() -> None:
    for username in tracked_accounts.load():
        try:
            snapshot_one(username)
            logging.info("Snapshotted %s", username)
        except Exception:
            logging.exception("Failed to snapshot %s", username)


if __name__ == "__main__":
    snapshot_all()
