import json
import logging
import time
from pathlib import Path

from pipeline.terminology_builder import TerminologyDB
from pipeline.ocr_cleaner import OCRCleaner
from pipeline.few_shot_builder import FewShotLibrary

logger = logging.getLogger("gametrans.pipeline.translator")

SYSTEM_PROMPT_TEMPLATE = """你是守望先锋（Overwatch）游戏聊天翻译专家。将玩家的游戏内聊天内容翻译成自然、地道的中文。

要求：
- 使用游戏玩家常用的口语化表达，不要书面翻译
- 保留玩家的情绪和语气（嘲讽、兴奋、愤怒等）
- 专有名词（英雄名、技能名、地图名）使用中国玩家社区通用译名
- 翻译要简洁，符合游戏内快速交流的特点
- <TERM_N> 格式的占位符保持原样不翻译

当前源语言：{source_lang}"""


class EnhancedTranslator:
    def __init__(self):
        from config.settings import get_settings
        settings = get_settings()
        cfg = settings.get("translate_enhanced", default={})
        api_cfg = cfg.get("api", {})

        self._base_url = api_cfg.get("base_url", "https://api.openai.com/v1")
        self._api_key = api_cfg.get("api_key", "")
        self._model = api_cfg.get("model", "gpt-4o-mini")
        self._timeout = api_cfg.get("timeout", 10)
        self._max_retries = api_cfg.get("max_retries", 2)
        self._few_shot_count = cfg.get("few_shot_count", 3)
        self._ocr_cleaning = cfg.get("ocr_cleaning", True)

        self._db = TerminologyDB()
        self._cleaner = OCRCleaner(self._db)
        self._few_shot = FewShotLibrary()

        self._client = None
        self._log_path = Path(__file__).parent.parent / "logs" / "translations.jsonl"

        logger.info("EnhancedTranslator initialized: model=%s, terms=%d",
                     self._model, len(self._db.entries()))

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
                timeout=self._timeout,
            )
        return self._client

    def translate(self, text: str, source_lang: str = "en") -> str | None:
        """
        3-tier translation pipeline:
        Tier 1: Exact terminology match (< 1ms)
        Tier 2: Fuzzy phrase match (< 5ms)
        Tier 3: LLM API (500ms-2s)
        """
        if not text or not text.strip():
            return None

        t0 = time.perf_counter()

        # Step 0: OCR correction only (no placeholder protection) for Tier 1/2
        corrected = self._cleaner.apply_corrections(text, source_lang)

        # Step 1: Tier 1 — exact match on full corrected text
        exact = self._db.lookup(corrected.strip(), source_lang)
        if exact:
            t1 = time.perf_counter()
            logger.info("Tier 1 hit: '%s' -> '%s' (%.1fms)",
                        text[:30], exact["target_zh"], (t1 - t0) * 1000)
            self._log_translation(text, corrected, exact["target_zh"], source_lang, "tier1")
            return exact["target_zh"]

        # Step 2: Tier 2 — phrase/term fuzzy match
        matches = self._db.match_phrases(corrected, source_lang)
        if matches:
            total_chars = len(corrected.strip())
            matched_chars = sum(end - start for start, end, _, _ in matches)
            coverage = matched_chars / total_chars if total_chars > 0 else 0

            if coverage >= 0.7:
                result = self._assemble_from_matches(corrected, matches)
                t2 = time.perf_counter()
                logger.info("Tier 2 hit (%.0f%% coverage): '%s' -> '%s' (%.1fms)",
                            coverage * 100, text[:30], result, (t2 - t0) * 1000)
                self._log_translation(text, corrected, result, source_lang, "tier2")
                return result

        # Step 3: Tier 3 — full clean with placeholder protection + LLM
        if self._ocr_cleaning:
            cleaned, placeholder_map, zh_map = self._cleaner.clean_ocr(text, source_lang)
        else:
            cleaned, placeholder_map, zh_map = text, {}, {}

        result = self._translate_llm(cleaned, source_lang, placeholder_map, zh_map)
        t3 = time.perf_counter()
        logger.info("Tier 3: '%s' -> '%s' (%.1fms)",
                    text[:30], (result or "None")[:30], (t3 - t0) * 1000)
        self._log_translation(text, cleaned, result, source_lang, "tier3")
        return result

    def _assemble_from_matches(self, text: str, matches: list[tuple]) -> str:
        """Build translated text by replacing matched spans with Chinese translations."""
        result = []
        last_end = 0
        for start, end, matched_term, target_zh in matches:
            # Add unmatched text before this match
            if start > last_end:
                gap = text[last_end:start].strip()
                if gap:
                    result.append(gap)
            result.append(target_zh)
            last_end = end
        # Add remaining text after last match
        if last_end < len(text):
            remaining = text[last_end:].strip()
            if remaining:
                result.append(remaining)
        return " ".join(result)

    def _translate_llm(self, text: str, source_lang: str,
                       placeholder_map: dict[str, str],
                       placeholder_zh_map: dict[str, str] | None = None) -> str | None:
        """Call LLM API with few-shot prompting."""
        # Retrieve few-shot samples
        samples = self._few_shot.retrieve(text, source_lang, top_k=self._few_shot_count)

        # Build messages
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(source_lang=source_lang)
        messages = [{"role": "system", "content": system_prompt}]

        for sample in samples:
            messages.append({"role": "user", "content": sample["source"]})
            messages.append({"role": "assistant", "content": sample["target_zh"]})

        messages.append({"role": "user", "content": text})

        # Call API with retry
        for attempt in range(self._max_retries + 1):
            try:
                client = self._get_client()
                response = client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=200,
                    temperature=0.3,
                )
                result = response.choices[0].message.content.strip()

                # Restore placeholders
                if placeholder_map:
                    result = self._cleaner.restore_placeholders(result, placeholder_map, placeholder_zh_map)

                return result

            except Exception as e:
                logger.warning("LLM API attempt %d/%d failed: %s",
                               attempt + 1, self._max_retries + 1, e)
                if attempt < self._max_retries:
                    time.sleep(0.5)

        return None

    def _log_translation(self, original: str, cleaned: str,
                         result: str | None, source_lang: str, tier: str):
        """Append translation log entry for quality review."""
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source_lang": source_lang,
                "tier": tier,
                "original": original,
                "cleaned": cleaned,
                "translated": result,
            }
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug("Failed to log translation: %s", e)
