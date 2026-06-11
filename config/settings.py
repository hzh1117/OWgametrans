import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("gametrans.config")

CONFIG_DIR = Path(__file__).parent
DEFAULT_CONFIG = CONFIG_DIR / "default_config.json"
USER_CONFIG = CONFIG_DIR / "user_config.json"


class Settings:
    def __init__(self):
        self._data = {}
        self._last_mtime = 0.0
        self._callbacks = []
        self.load()

    def load(self):
        try:
            with open(DEFAULT_CONFIG, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Failed to load default config: %s, using empty config", e)
            self._data = {}

        if USER_CONFIG.exists():
            try:
                with open(USER_CONFIG, "r", encoding="utf-8") as f:
                    user = json.load(f)
                self._deep_merge(self._data, user)
            except (json.JSONDecodeError, PermissionError, OSError) as e:
                logger.warning("Failed to load user config: %s, using defaults only", e)

        # Record mtime so check_reload() doesn't re-trigger on the next poll
        try:
            if USER_CONFIG.exists():
                self._last_mtime = USER_CONFIG.stat().st_mtime
        except OSError:
            pass

    def save(self):
        try:
            with open(USER_CONFIG, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except (PermissionError, OSError) as e:
            logger.warning("Failed to save user config: %s", e)

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
        items: list of (keys_tuple, value) or (*keys, value) tuples.
        """
        for item in items:
            if len(item) == 2 and isinstance(item[0], tuple):
                keys, value = item
                self.set(*keys, value)
            else:
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

    def on_change(self, callback):
        self._callbacks.append(callback)

    def check_reload(self):
        if not USER_CONFIG.exists():
            return
        try:
            mtime = USER_CONFIG.stat().st_mtime
            if mtime > self._last_mtime:
                self._last_mtime = mtime
                old_data = json.dumps(self._data, sort_keys=True)
                self.load()
                new_data = json.dumps(self._data, sort_keys=True)
                if old_data != new_data:
                    logger.info("User config reloaded")
                    for cb in self._callbacks:
                        try:
                            cb(self._data)
                        except Exception as e:
                            logger.warning("Config change callback error: %s", e)
        except OSError:
            pass


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
