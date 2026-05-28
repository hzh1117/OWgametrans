import pytest
from parser.message_parser import parse_messages, OVERWATCH_CHAT_PATTERN


class TestOverwatchChatPattern:
    @pytest.mark.parametrize("text,expected", [
        ("[12:34] [综合] GenjiMain: 你好世界",
         {"timestamp": "12:34", "channel": "综合", "player": "GenjiMain", "message": "你好世界"}),
        ("[综合] GenjiMain: 你好世界",
         {"timestamp": None, "channel": "综合", "player": "GenjiMain", "message": "你好世界"}),
        ("[12:34] GenjiMain: gg",
         {"timestamp": "12:34", "channel": None, "player": "GenjiMain", "message": "gg"}),
        ("GenjiMain: gg",
         {"timestamp": None, "channel": None, "player": "GenjiMain", "message": "gg"}),
        ("[9:05] [私聊] TracerFan: 加油！",
         {"timestamp": "9:05", "channel": "私聊", "player": "TracerFan", "message": "加油！"}),
        ("[12:34] [システム] Player1: こんにちは",
         {"timestamp": "12:34", "channel": "システム", "player": "Player1", "message": "こんにちは"}),
        ("[12:34] [팀] Player1: 안녕하세요",
         {"timestamp": "12:34", "channel": "팀", "player": "Player1", "message": "안녕하세요"}),
    ])
    def test_chat_pattern_match(self, text, expected):
        m = OVERWATCH_CHAT_PATTERN.match(text)
        assert m is not None, f"Failed to match: {text}"
        assert m.group("timestamp") == expected["timestamp"]
        assert m.group("channel") == expected["channel"]
        assert m.group("player") == expected["player"]
        assert m.group("message") == expected["message"]

    def test_empty_line_skipped(self):
        result = parse_messages("")
        assert result == []

    def test_system_message_no_match(self):
        result = parse_messages("比赛即将开始")
        assert result == []

    def test_multiline_merge(self):
        text = "[12:34] [综合] GenjiMain: 这是一条很长的消息\n需要换行显示"
        result = parse_messages(text)
        assert len(result) == 1
        assert "需要换行显示" in result[0].message

    def test_multiple_messages(self):
        text = "[12:34] [综合] Player1: hello\n[12:34] [队伍] Player2: world"
        result = parse_messages(text)
        assert len(result) == 2
        assert result[0].player == "Player1"
        assert result[1].player == "Player2"

    def test_timestamp_preserved(self):
        text = "[12:34] [综合] Player1: test"
        result = parse_messages(text)
        assert len(result) == 1
        assert result[0].timestamp == "12:34"

    def test_channel_preserved(self):
        text = "[队伍] Player1: test"
        result = parse_messages(text)
        assert len(result) == 1
        assert result[0].channel == "队伍"
