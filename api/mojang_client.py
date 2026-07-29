import requests

MOJANG_PROFILE_URL = "https://api.mojang.com/users/profiles/minecraft/{username}"


class PlayerNotFoundError(Exception):
    """Raised when a username doesn't correspond to a Minecraft account."""


def get_uuid(username: str) -> str:
    response = requests.get(MOJANG_PROFILE_URL.format(username=username), timeout=10)

    if response.status_code in (400, 404):
        raise PlayerNotFoundError(f"No Minecraft account named '{username}'")
    response.raise_for_status()

    return response.json()["id"]
