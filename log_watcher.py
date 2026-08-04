import re

CHAT_PREFIX_RE = re.compile(r"^\[\d{2}:\d{2}:\d{2}\] \[[^\]]*\]: \[CHAT\] (.*)$")
COLOR_CODE_RE = re.compile(r"§.")
WHO_RE = re.compile(r"^ONLINE:\s*(.*)$")
PARTY_LABEL_RE = re.compile(r"^Party (?:Leader|Moderators|Members):\s*(.*)$")
BRACKET_RE = re.compile(r"\[[^\]]*\]")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,16}$")
SEPARATOR_RE = re.compile(r"^-{5,}$")
HAS_JOINED_RE = re.compile(r"^([A-Za-z0-9_]{1,16}) has joined \(\d+/\d+\)!$")
CHANNEL_PREFIX_RE = re.compile(r"^(?:Party|Guild|Officer) > ")
CHAT_MESSAGE_RE = re.compile(r"^([A-Za-z0-9_]{1,16}): (.+)$")
WHITESPACE_RE = re.compile(r"\s+")

# The exact banner line Hypixel sends the instant a Bedwars match begins.
GAME_START_TEXT = "Protect your bed and destroy the enemy beds."


def _extract_usernames(text: str) -> list[str]:
    stripped = BRACKET_RE.sub(" ", text)
    return [token for token in stripped.split() if USERNAME_RE.match(token)]


def _extract_speaker(plain_text: str) -> str | None:
    """Pulls the sender out of a chat/party/guild message line, anchored to
    avoid false positives like "You'll be partying with: ..." or
    "Guild: Message Of The Day" (neither of which is a real username)."""
    stripped = CHANNEL_PREFIX_RE.sub("", plain_text)
    stripped = BRACKET_RE.sub(" ", stripped)
    stripped = WHITESPACE_RE.sub(" ", stripped).strip()
    match = CHAT_MESSAGE_RE.match(stripped)
    return match.group(1) if match else None


class LobbyLogParser:
    """Consumes raw log lines and reports /who, /party list, and — while a
    tracked account's own match is in its pregame lobby — individual chat
    speakers, so the app can look each one up as they talk."""

    def __init__(self, own_usernames: list[str]):
        self._own_usernames_lower = {u.lower() for u in own_usernames}
        self._party_buffer: list[str] = []
        self._in_party_block = False
        self._pregame_active = False

    def feed(self, raw_line: str) -> tuple[str, list[str]] | None:
        match = CHAT_PREFIX_RE.match(raw_line.rstrip("\n").rstrip("\r"))
        if not match:
            return None
        plain = COLOR_CODE_RE.sub("", match.group(1))

        who_match = WHO_RE.match(plain)
        if who_match:
            names = [name.strip() for name in who_match.group(1).split(",") if name.strip()]
            return ("who", names) if names else None

        party_match = PARTY_LABEL_RE.match(plain)
        if party_match:
            self._in_party_block = True
            self._party_buffer.extend(_extract_usernames(party_match.group(1)))
            return None

        if self._in_party_block and SEPARATOR_RE.match(plain.strip()):
            names = self._party_buffer
            self._party_buffer = []
            self._in_party_block = False
            return ("party", names) if names else None

        joined_match = HAS_JOINED_RE.match(plain.strip())
        if joined_match and joined_match.group(1).lower() in self._own_usernames_lower:
            self._pregame_active = True
            return ("reset", [])

        if self._pregame_active and plain.strip() == GAME_START_TEXT:
            self._pregame_active = False
            return None

        if self._pregame_active:
            speaker = _extract_speaker(plain)
            if speaker:
                return ("speaker", [speaker])

        return None
