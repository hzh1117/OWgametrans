import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
DEFAULT_CONFIG = CONFIG_DIR / "default_config.json"
USER_CONFIG = CONFIG_DIR / "user_config.json"


class Settings:
    def __init__(self):
        self._data = {}
        self.load()

    def load(self):
        with open(DEFAULT_CONFIG, "r", encoding="utf-8") as f:
            self._data = json.load(f)
        if USER_CONFIG.exists():
            with open(USER_CONFIG, "r", encoding="utf-8") as f:
                user = json.load(f)
            self._deep_merge(self._data, user)

    def save(self):
        with open(USER_CONFIG, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, *keys, default=None):
        obj = self._data
        for k in keys:
            if isinstance(obj, dict) and k in obj:
                obj = obj[k]
            else:
                return default
        return obj

    def set(self, *keys_and_value):
        if len(keys_and_value) < 2:
            raise ValueError("set() requires at least one key and a value")
        *keys, value = keys_and_value
        obj = self._data
        for k in keys[:-1]:
            if k not in obj or not isinstance(obj[k], dict):
                obj[k] = {}
            obj = obj[k]
        obj[keys[-1]] = value

    def set_and_save(self, *keys_and_value):
        self.set(*keys_and_value)
        self.save()

    def set_many(self, items: list[tuple]):
        """Batch set multiple key-value pairs and save once.
        items: list of tuples, each being (*keys, value)
        """
        for item in items:
            self.set(*item)
        self.save()

    def _deep_merge(self, base, override):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    @property
    def data(self):
        return self._data


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
