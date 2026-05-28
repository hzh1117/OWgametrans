import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

logger = logging.getLogger("gametrans.translate.volcengine")

SERVICE = "translate"
REGION = "cn-north-1"
HOST = "open.volcengineapi.com"
PATH = "/"
QUERY_PARAMS = {"Action": "TranslateText", "Version": "2020-06-01"}

_HEADER_KEY_MAP = {
    "content-type": "Content-Type",
    "host": "Host",
    "x-date": "X-Date",
    "x-content-sha256": "X-Content-Sha256",
}


class VolcengineTranslator:
    def __init__(self, app_id: str, app_key: str):
        self.app_id = app_id
        self.app_key = app_key

    def translate(self, text: str, source: str = "auto", target: str = "zh") -> str | None:
        if not self.app_id or not self.app_key:
            return None

        try:
            body = {
                "SourceLanguage": source,
                "TargetLanguage": target,
                "TextList": [text],
            }
            body_bytes = json.dumps(body).encode("utf-8")
            body_hash = hashlib.sha256(body_bytes).hexdigest()

            now = datetime.now(timezone.utc)
            date_str = now.strftime("%Y%m%dT%H%M%SZ")
            date_short = now.strftime("%Y%m%d")

            headers = {
                "Content-Type": "application/json",
                "Host": HOST,
                "X-Date": date_str,
                "X-Content-Sha256": body_hash,
            }

            credential = f"{self.app_id}/{date_short}/{REGION}/{SERVICE}/request"
            signed_header_names = ["content-type", "host", "x-date", "x-content-sha256"]

            canonical_headers = ""
            for name in signed_header_names:
                canonical_headers += f"{name}:{headers[_HEADER_KEY_MAP[name]]}\n"

            sorted_query = urlencode(sorted(QUERY_PARAMS.items()))
            canonical_request = (
                f"POST\n{PATH}\n{sorted_query}\n"
                f"{canonical_headers}\n"
                f"{';'.join(signed_header_names)}\n"
                f"{body_hash}"
            )
            canonical_request_hash = hashlib.sha256(canonical_request.encode()).hexdigest()

            scope = f"{date_short}/{REGION}/{SERVICE}/request"
            string_to_sign = f"HMAC-SHA256\n{date_str}\n{scope}\n{canonical_request_hash}"

            signing_key = self._derive_signing_key(date_short)
            signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

            auth = (
                f"HMAC-SHA256 Credential={credential}, "
                f"SignedHeaders={';'.join(signed_header_names)}, "
                f"Signature={signature}"
            )
            headers["Authorization"] = auth

            url = f"https://{HOST}{PATH}?{sorted_query}"
            resp = requests.post(url, headers=headers, data=body_bytes, timeout=5)
            resp.raise_for_status()

            result = resp.json()
            translation_list = result.get("TranslationList", [])
            if translation_list:
                return translation_list[0].get("Translation", "")
            return None

        except Exception as e:
            logger.warning("Volcengine translate failed: %s", e)
            return None

    def _derive_signing_key(self, date_short: str) -> bytes:
        k_date = hmac.new(self.app_key.encode(), date_short.encode(), hashlib.sha256).digest()
        k_region = hmac.new(k_date, REGION.encode(), hashlib.sha256).digest()
        k_service = hmac.new(k_region, SERVICE.encode(), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b"request", hashlib.sha256).digest()
        return k_signing
