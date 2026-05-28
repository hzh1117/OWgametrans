import logging
import keyboard

logger = logging.getLogger("gametrans.hotkey")


class HotkeyManager:
    def __init__(self):
        self._callbacks = {}

    def register(self, hotkey: str, callback):
        self._callbacks[hotkey] = callback
        keyboard.add_hotkey(hotkey, callback, suppress=False)
        logger.info("Registered hotkey: %s", hotkey)

    def unregister_all(self):
        try:
            keyboard.unhook_all()
            logger.info("All hotkeys unregistered")
        except Exception as e:
            logger.warning("Error unregistering hotkeys: %s", e)
