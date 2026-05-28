import re
import logging
from parser.message_parser import ChatMessage

logger = logging.getLogger("gametrans.parser")

SYSTEM_KEYWORDS = [
    "switched to",
    "joined the match",
    "left the match",
    "joined the game",
    "left the game",
    "has been eliminated",
    "was eliminated",
    "Welcome to",
    "Match ends in",
    "Overtime",
    "Round ",
    "Victory",
    "Defeat",
    "Draw",
    "You are now",
    "Assembling heroes",
    "Prepare your defenses",
    "Attack begins in",
    "Defense begins in",
]

SYSTEM_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in SYSTEM_KEYWORDS),
    re.IGNORECASE,
)


def is_system_message(msg: ChatMessage) -> bool:
    return bool(SYSTEM_PATTERN.search(msg.message))


def filter_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    return [m for m in messages if not is_system_message(m)]
