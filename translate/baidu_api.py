import hashlib
import logging
import random
import string
import time

import requests

logger = logging.getLogger("gametrans.translate.baidu")

ENDPOINT = "https://fanyi-api.baidu.com/api/trans/vip/translate"
MIN_INTERVAL = 0.1


class BaiduTranslator:
    def __init__(self, app_id: str, app_key: str):
        self.app_id = app_id
        self.app_key = app_key
        self._last_call = 0.0

    def translate(self, text: str, source: str = "auto", target: str = "zh") -> str | None:
        if not self.app_id or not self.app_key:
            return None

        elapsed = time.monotonic() - self._last_call
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

        try:
            salt = "".join(random.choices(string.digits, k=10))
            sign_str = f"{self.app_id}{text}{salt}{self.app_key}"
            sign = hashlib.md5(sign_str.encode("utf-8"), usedforsecurity=False).hexdigest()

            data = {
                "q": text,
                "from": source,
                "to": target,
                "appid": self.app_id,
                "salt": salt,
                "sign": sign,
            }

            resp = requests.post(ENDPOINT, data=data, timeout=5)
            self._last_call = time.monotonic()
            resp.raise_for_status()
            result = resp.json()

            if "error_code" in result:
                logger.warning("Baidu translate error: %s - %s",
                               result["error_code"], result.get("error_msg", ""))
                return None

            trans_result = result.get("trans_result", [])
            if trans_result:
                return trans_result[0].get("dst", "")
            return None

        except Exception as e:
            logger.warning("Baidu translate failed: %s", e)
            return None
