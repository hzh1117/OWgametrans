import json
import pytest
from config.settings import Settings


class TestSettings:
    def _make_settings(self, monkeypatch, tmp_path, default_data=None, user_data=None):
        import config.settings as cs
        default_path = tmp_path / "default.json"
        user_path = tmp_path / "user.json"

        if default_data is not None:
            default_path.write_text(json.dumps(default_data), encoding="utf-8")
        if user_data is not None:
            user_path.write_text(json.dumps(user_data), encoding="utf-8")

        monkeypatch.setattr(cs, "DEFAULT_CONFIG", default_path)
        monkeypatch.setattr(cs, "USER_CONFIG", user_path)

        settings = Settings.__new__(Settings)
        settings._data = {}
        settings._last_mtime = 0.0
        settings._callbacks = []
        return settings

    def test_load_default_config(self, tmp_path, monkeypatch):
        settings = self._make_settings(monkeypatch, tmp_path, {"ocr": {"language": "en"}})
        settings.load()
        assert settings.get("ocr", "language") == "en"

    def test_user_config_override(self, tmp_path, monkeypatch):
        settings = self._make_settings(
            monkeypatch, tmp_path,
            {"ocr": {"language": "en", "threshold": 180}},
            {"ocr": {"language": "zh-Hans-CN"}},
        )
        settings.load()
        assert settings.get("ocr", "language") == "zh-Hans-CN"
        assert settings.get("ocr", "threshold") == 180

    def test_corrupted_default_config(self, tmp_path, monkeypatch):
        import config.settings as cs
        config_path = tmp_path / "default.json"
        config_path.write_text("not valid json{{{", encoding="utf-8")
        user_path = tmp_path / "user.json"

        monkeypatch.setattr(cs, "DEFAULT_CONFIG", config_path)
        monkeypatch.setattr(cs, "USER_CONFIG", user_path)

        settings = Settings.__new__(Settings)
        settings._data = {}
        settings._last_mtime = 0.0
        settings._callbacks = []
        settings.load()
        assert settings.data == {}

    def test_missing_default_config(self, tmp_path, monkeypatch):
        settings = self._make_settings(monkeypatch, tmp_path)
        settings.load()
        assert settings.data == {}

    def test_get_nested(self):
        settings = Settings.__new__(Settings)
        settings._data = {"a": {"b": {"c": 42}}}
        assert settings.get("a", "b", "c") == 42
        assert settings.get("a", "b", "d", default=99) == 99
        assert settings.get("x", "y", default="fallback") == "fallback"

    def test_set_nested(self):
        settings = Settings.__new__(Settings)
        settings._data = {}
        settings.set("a", "b", 42)
        assert settings.get("a", "b") == 42

    def test_set_many(self, tmp_path, monkeypatch):
        settings = self._make_settings(monkeypatch, tmp_path)
        settings.set_many([
            (("a", "b"), 1),
            (("c", "d"), 2),
        ])
        assert settings.get("a", "b") == 1
        assert settings.get("c", "d") == 2
