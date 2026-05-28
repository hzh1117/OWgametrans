import re
import logging
from parser.message_parser import ChatMessage

logger = logging.getLogger("gametrans.parser")

SYSTEM_KEYWORDS_EN = [
    "switched to", "joined the match", "left the match",
    "joined the game", "left the game", "has been eliminated",
    "was eliminated", "Welcome to", "Match ends in",
    "Overtime", "Round ", "Victory", "Defeat", "Draw",
    "You are now", "Assembling heroes", "Prepare your defenses",
    "Attack begins in", "Defense begins in",
    "Play of the Game", "Eliminated", "Assisted",
]

SYSTEM_KEYWORDS_ZH = [
    "已切换为", "加入了比赛", "离开了比赛",
    "加入了游戏", "离开了游戏", "已被消灭",
    "被消灭", "欢迎来到", "比赛结束于",
    "加时赛", "回合", "胜利", "失败", "平局",
    "你已", "集结英雄", "准备防守",
    "进攻开始于", "防守开始于",
    "最佳表现", "已消灭", "助攻",
]

SYSTEM_KEYWORDS_JA = [
    "に変更", "マッチに参加", "マッチから退出",
    "ゲームに参加", "ゲームから退出", "が排除されました",
    "排除されました", "ようこそ", "マッチ終了",
    "オーバータイム", "ラウンド", "勝利", "敗北", "引き分け",
    "ヒーロー集结", "防衛準備",
]

SYSTEM_KEYWORDS_KO = [
    "전환했습니다", "매치에 참가", "매치에서 나감",
    "게임에 참가", "게임에서 나감", "처치되었습니다",
    "환영합니다", "매치 종료",
    "오버타임", "라운드", "승리", "패배", "무승부",
]

ALL_KEYWORDS = (
    SYSTEM_KEYWORDS_EN + SYSTEM_KEYWORDS_ZH
    + SYSTEM_KEYWORDS_JA + SYSTEM_KEYWORDS_KO
)

SYSTEM_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in ALL_KEYWORDS),
    re.IGNORECASE,
)

# Interference patterns
SCOREBOARD_PATTERN = re.compile(
    r"^[A-Za-z0-9_]+\s+\d+\s+\d+\s+\d+"
    r"|^\d+\s+(K|D|A|elims?|deaths?|assists?)"
    r"|^(RTT|FPS|ping|latency)\s*[:=]\s*\d+",
    re.IGNORECASE,
)

ULTIMATE_PATTERN = re.compile(
    r"(终极技能|ultimate|ult)\s*\d+%"
    r"|^[A-Z]\s+(终极技能|ultimate)"
    r"|充能\s*\d+%",
    re.IGNORECASE,
)

DEATH_REPLAY_PATTERN = re.compile(
    r"^(你被|Eliminated by|killed by)\s+"
    r"|^(你击杀了|You eliminated)\s+"
    r"|^(击杀了|Eliminated)\s+\S+$",
    re.IGNORECASE,
)

NUMERIC_HEAVY_PATTERN = re.compile(
    r"^[\d\s\.\,\:\%\+\-\*\/\=\(\)]+$",
)

NETWORK_STATS_PATTERN = re.compile(
    r"(RTT|ping|latency|jitter|pkt|loss|bandwidth)\s*[:=]",
    re.IGNORECASE,
)

JUNK_PATTERNS = [
    SCOREBOARD_PATTERN, ULTIMATE_PATTERN,
    DEATH_REPLAY_PATTERN, NUMERIC_HEAVY_PATTERN,
    NETWORK_STATS_PATTERN,
]


def is_system_message(msg: ChatMessage) -> bool:
    return bool(SYSTEM_PATTERN.search(msg.message))


def is_interference(msg: ChatMessage) -> bool:
    text = msg.message.strip()
    if len(text) < 2:
        return True
    if NUMERIC_HEAVY_PATTERN.match(text):
        return True
    for pattern in JUNK_PATTERNS:
        if pattern.search(text):
            return True
    digit_count = sum(1 for c in text if c.isdigit())
    if len(text) > 3 and digit_count / len(text) > 0.5:
        return True
    if text.isupper() and len(text) < 15 and text.isascii():
        return True
    return False


def filter_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    return [m for m in messages if not is_system_message(m) and not is_interference(m)]
