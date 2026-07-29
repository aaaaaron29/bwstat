import requests

PLAYER_URL = "https://api.hypixel.net/v2/player"


class InvalidApiKeyError(Exception):
    """Raised when Hypixel rejects the configured API key."""


class RateLimitedError(Exception):
    """Raised when Hypixel's rate limit has been exceeded."""


class HypixelApiError(Exception):
    """Raised for any other non-success response from Hypixel."""


def get_player(uuid: str, api_key: str) -> dict:
    response = requests.get(
        PLAYER_URL,
        params={"uuid": uuid},
        headers={"API-Key": api_key},
        timeout=10,
    )

    if response.status_code == 403:
        raise InvalidApiKeyError("Hypixel rejected the configured API key")
    if response.status_code == 429:
        raise RateLimitedError("Hypixel API rate limit exceeded, try again shortly")

    response.raise_for_status()
    payload = response.json()

    if not payload.get("success", False):
        raise HypixelApiError(payload.get("cause", "Unknown Hypixel API error"))

    player = payload.get("player")
    if player is None:
        raise HypixelApiError("Player has never logged into Hypixel")

    return player
