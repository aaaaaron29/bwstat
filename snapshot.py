import logging
from pathlib import Path

from api.hypixel_client import get_player
from api.mojang_client import get_uuid
from config import TRACKED_USERNAMES, get_api_key
from models.bedwars_stats import BedwarsStats
from storage import history

LOG_PATH = Path(__file__).resolve().parent / "snapshot.log"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def snapshot_all() -> None:
    api_key = get_api_key()
    for username in TRACKED_USERNAMES:
        try:
            uuid = get_uuid(username)
            player = get_player(uuid, api_key)
            stats = BedwarsStats.from_api_json(player, username)
            history.add_entry(stats)
            logging.info("Snapshotted %s (level %d)", username, stats.level)
        except Exception:
            logging.exception("Failed to snapshot %s", username)


if __name__ == "__main__":
    snapshot_all()
