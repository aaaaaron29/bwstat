import os

from dotenv import load_dotenv

load_dotenv()


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
