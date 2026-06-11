import logging
import re

from pipeline.terminology_builder import TerminologyDB

logger = logging.getLogger("gametrans.pipeline.ocr_cleaner")


class OCRCleaner:
    def __init__(self, terminology_db: TerminologyDB):
        self._db = terminology_db
        self._en_rules = self._build_en_rules()
        self._ko_rules = self._build_ko_rules()

    @staticmethod
    def _build_en_rules() -> list[tuple[re.Pattern, str]]:
        return [
            # 0 -> O when followed by uppercase letter (e.g. "0RB" -> "ORB")
            (re.compile(r'(?<![A-Za-z0-9])0(?=[A-Z])'), 'O'),
            # 0 -> o when inside a word context (e.g. "overwatch" typed as "0verwatch")
            (re.compile(r'(?<![A-Za-z0-9])0(?=[a-z])'), 'o'),
            # l -> 1 when preceded by digit context (e.g. "playerl" unlikely, but "l33t" -> keep)
            (re.compile(r'(?<=\d)l(?=\d)'), '1'),
            # 1 -> l when in all-alpha word (e.g. "lucio" typed with leading 1 - context dependent)
            (re.compile(r'(?<=[a-z])1(?=[a-z])'), 'l'),
            # Common double-space cleanup
            (re.compile(r'  +'), ' '),
        ]

    @staticmethod
    def _build_ko_rules() -> list[tuple[re.Pattern, str]]:
        return [
            # Korean jamo that got stuck together: split common patterns
            # e.g. "힐줘" should stay as-is (it's valid Korean)
            # But OCR might merge separate words: "모여밀어" -> "모여 밀어"
            # We handle this via terminology matching rather than regex
            (re.compile(r'  +'), ' '),
        ]

    def apply_corrections(self, text: str, source_lang: str) -> str:
        """Apply OCR correction rules only (no placeholder protection). Used by Tier 1/2."""
        text = self._apply_ocr_rules(text, source_lang)
        if source_lang == "ko":
            text = self._split_korean_stuck(text)
        return text

    def _apply_ocr_rules(self, text: str, source_lang: str) -> str:
        rules = []
        if source_lang == "en":
            rules = self._en_rules
        elif source_lang == "ko":
            rules = self._ko_rules
        elif source_lang == "ja":
            rules = []  # Japanese OCR corrections TBD
        else:
            rules = self._en_rules  # Default to EN rules

        for pattern, replacement in rules:
            text = pattern.sub(replacement, text)

        # Apply hero name case normalization for EN
        if source_lang == "en":
            text = self._normalize_hero_names(text)

        return text

    def _normalize_hero_names(self, text: str) -> str:
        """Fix common OCR case errors for known hero names."""
        hero_corrections = {
            "lucio": "Lucio", "genji": "Genji", "tracer": "Tracer",
            "mercy": "Mercy", "moira": "Moira", "ana": "Ana",
            "kiriko": "Kiriko", "rein": "Rein", "reaper": "Reaper",
            "pharah": "Pharah", "hanzo": "Hanzo", "widow": "Widow",
            "soldier": "Soldier", "doom": "Doom", "brig": "Brig",
            "bap": "Bap", "zen": "Zen", "sym": "Sym", "torb": "Torb",
            "cass": "Cass", "hog": "Hog", "dva": "D.Va", "ball": "Ball",
            "queen": "Queen",
        }
        words = text.split()
        corrected = []
        for w in words:
            lower = w.lower()
            if lower in hero_corrections:
                corrected.append(hero_corrections[lower])
            else:
                corrected.append(w)
        return " ".join(corrected)

    def _split_korean_stuck(self, text: str) -> str:
        """Try to split stuck-together Korean words using terminology DB."""
        # Collect all matches first, then apply replacements in reverse order
        # to avoid index invalidation from string mutation
        ko_pattern = re.compile(r'[가-힯]+')
        replacements = []
        for match in ko_pattern.finditer(text):
            chunk = match.group()
            if len(chunk) <= 2:
                continue
            best_split = self._try_split_korean(chunk)
            if best_split and best_split != chunk:
                replacements.append((match.start(), match.end(), best_split))
        # Apply in reverse to preserve indices
        for start, end, replacement in reversed(replacements):
            text = text[:start] + replacement + text[end:]
        return text

    def _try_split_korean(self, chunk: str) -> str | None:
        """Try to split a Korean chunk into known terms."""
        # Simple greedy matching from left to right
        remaining = chunk
        parts = []
        while remaining:
            found = False
            for length in range(min(6, len(remaining)), 0, -1):
                candidate = remaining[:length]
                match = self._db.lookup(candidate, "ko")
                if match:
                    parts.append(candidate)
                    remaining = remaining[length:]
                    found = True
                    break
            if not found:
                # Can't split further
                return None
        return " ".join(parts) if len(parts) > 1 else None

    def clean_ocr(self, text: str, source_lang: str) -> tuple[str, dict[str, str], dict[str, str]]:
        """
        Clean OCR text and protect terminology with placeholders.
        Returns (cleaned_text, placeholder_map, placeholder_zh_map).
        placeholder_map: {"<TERM_0>": original_term, ...}
        placeholder_zh_map: {"<TERM_0>": Chinese translation, ...}
        """
        # Step 1: Apply OCR correction rules
        text = self._apply_ocr_rules(text, source_lang)

        # Step 2: Korean stuck-together splitting
        if source_lang == "ko":
            text = self._split_korean_stuck(text)

        # Step 3: Match known terminology and replace with placeholders
        matches = self._db.match_phrases(text, source_lang)

        if not matches:
            return text, {}, {}

        # Build placeholder map and replace in text (reverse order to preserve indices)
        placeholder_map = {}
        placeholder_zh_map = {}  # placeholder -> Chinese translation
        result = text
        for i, (start, end, matched_term, target_zh) in enumerate(reversed(matches)):
            placeholder = f"<TERM_{len(matches) - 1 - i}>"
            placeholder_map[placeholder] = matched_term
            placeholder_zh_map[placeholder] = target_zh
            result = result[:start] + placeholder + result[end:]

        logger.debug("OCR clean: '%s' -> '%s', %d placeholders", text, result, len(placeholder_map))
        return result, placeholder_map, placeholder_zh_map

    def restore_placeholders(self, text: str, placeholder_map: dict[str, str],
                             placeholder_zh_map: dict[str, str] | None = None) -> str:
        """Restore placeholders in translated text back to original terms."""
        if not placeholder_map:
            return text

        zh_map = placeholder_zh_map or {}
        for placeholder, original_term in placeholder_map.items():
            if placeholder in text:
                # Placeholder was preserved - replace with Chinese term
                zh_term = zh_map.get(placeholder, original_term)
                text = text.replace(placeholder, zh_term)

        return text
