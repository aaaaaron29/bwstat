import os
from pathlib import Path

from dotenv import load_dotenv, set_key

ENV_PATH = Path(__file__).resolve().parent / ".env"

load_dotenv(ENV_PATH)

TRACKED_USERNAMES = ["wns", "wukegh"]

DEFAULT_LOG_PATH = r"C:\Users\aaron\.lunarclient\profiles\1.8\logs\latest.log"


class MissingApiKeyError(Exception):
    pass


def get_api_key() -> str:
    api_key = os.getenv("HYPIXEL_API_KEY")
    if not api_key:
        raise MissingApiKeyError(
            "HYPIXEL_API_KEY is not set. Copy .env.example to .env and add your key "
            "from developer.hypixel.net."
        )
    return api_key


def set_api_key(new_key: str) -> None:
    if not ENV_PATH.exists():
        ENV_PATH.touch()
    set_key(ENV_PATH, "HYPIXEL_API_KEY", new_key)
    os.environ["HYPIXEL_API_KEY"] = new_key


def get_log_path() -> str:
    return os.getenv("LUNAR_LOG_PATH", DEFAULT_LOG_PATH)


def set_log_path(new_path: str) -> None:
    if not ENV_PATH.exists():
        ENV_PATH.touch()
    set_key(ENV_PATH, "LUNAR_LOG_PATH", new_path)
    os.environ["LUNAR_LOG_PATH"] = new_path
