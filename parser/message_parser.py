import re
import logging
from dataclasses import dataclass

logger = logging.getLogger("gametrans.parser")


def detect_source_language(text: str) -> str:
    """Detect source language using Unicode block heuristics.

    Returns 'ko', 'ja', 'zh', or 'en' (default).
    """
    if not text:
        return "en"

    hangul = 0
    cjk = 0
    hiragana_katakana = 0
    latin = 0
    total = 0

    for ch in text:
        if ch.isspace() or ch in ".,;:!?-()[]{}\"'":
            continue
        total += 1
        cp = ord(ch)
        if 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF or 0x3130 <= cp <= 0x318F:
            hangul += 1
        elif 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
            hiragana_katakana += 1
        elif 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            cjk += 1
        elif 0x0041 <= cp <= 0x007A or 0x00C0 <= cp <= 0x024F:
            latin += 1

    if total == 0:
        return "en"

    if hangul / total > 0.3:
        return "ko"
    if hiragana_katakana / total > 0.1:
        return "ja"
    if cjk / total > 0.3:
        return "zh"
    return "en"

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
