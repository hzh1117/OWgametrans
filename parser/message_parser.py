import re
import logging
from dataclasses import dataclass

logger = logging.getLogger("gametrans.parser")

OVERWATCH_CHAT_PATTERN = re.compile(
    r"^\s*"
    r"(?:\[(?P<timestamp>\d{1,2}:\d{2})\]\s*)?"
    r"(?:\[(?P<channel>[^\]]+)\]\s*)?"
    r"(?P<player>[^\s:\[\]]+)"
    r"\s*:\s*"
    r"(?P<message>.+)",
    re.DOTALL,
)


@dataclass
class ChatMessage:
    timestamp: str | None
    channel: str | None
    player: str
    message: str
    raw: str


def parse_messages(text: str) -> list[ChatMessage]:
    messages = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        m = OVERWATCH_CHAT_PATTERN.match(line)
        if m:
            messages.append(ChatMessage(
                timestamp=m.group("timestamp"),
                channel=m.group("channel"),
                player=m.group("player"),
                message=m.group("message").strip(),
                raw=line,
            ))
        else:
            # Continuation line: no timestamp/channel/player, append to previous message
            if messages and not re.search(r"\[.*?\].*?:", line):
                messages[-1].message += " " + line
                messages[-1].raw += "\n" + line
            else:
                logger.debug("Unmatched line: %s", line[:80])

    return messages
