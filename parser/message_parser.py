import re
import logging
from dataclasses import dataclass

logger = logging.getLogger("gametrans.parser")

PATTERN = re.compile(
    r"(?:\[(?P<channel>\w+)\]\s*)?(?P<player>\S+):\s*(?P<message>.+)",
    re.IGNORECASE,
)


@dataclass
class ChatMessage:
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
        m = PATTERN.match(line)
        if m:
            messages.append(ChatMessage(
                channel=m.group("channel"),
                player=m.group("player"),
                message=m.group("message").strip(),
                raw=line,
            ))
    return messages
