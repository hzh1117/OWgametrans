import json
import logging
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger("gametrans.pipeline.few_shot")

# === Seed few-shot samples (EN -> ZH) ===
SEED_FEW_SHOT_EN: list[dict] = [
    {"id": "en_001", "source_lang": "en", "source": "tracer diff go next",
     "target_zh": "猎空差距 下一把", "terms": ["Tracer", "diff"], "tags": ["slang", "post-match"], "quality": "curated"},
    {"id": "en_002", "source_lang": "en", "source": "tank diff gg",
     "target_zh": "坦克差距 gg", "terms": ["tank", "diff", "gg"], "tags": ["slang", "post-match"], "quality": "curated"},
    {"id": "en_003", "source_lang": "en", "source": "switch to rein we need shield",
     "target_zh": "换莱因哈特 我们需要盾", "terms": ["Reinhardt", "shield"], "tags": ["strategy"], "quality": "curated"},
    {"id": "en_004", "source_lang": "en", "source": "nano me nano me",
     "target_zh": "给我激素 给我激素", "terms": ["Nanoboost"], "tags": ["ability"], "quality": "curated"},
    {"id": "en_005", "source_lang": "en", "source": "nice shot",
     "target_zh": "好枪", "terms": [], "tags": ["reaction"], "quality": "curated"},
    {"id": "en_006", "source_lang": "en", "source": "group up stop feeding",
     "target_zh": "集合 别送了", "terms": ["feed"], "tags": ["strategy", "slang"], "quality": "curated"},
    {"id": "en_007", "source_lang": "en", "source": "heal me heal me",
     "target_zh": "奶我 奶我", "terms": [], "tags": ["phrase"], "quality": "curated"},
    {"id": "en_008", "source_lang": "en", "source": "widow is carrying",
     "target_zh": "黑百合在带飞", "terms": ["Widowmaker", "carry"], "tags": ["hero", "slang"], "quality": "curated"},
    {"id": "en_009", "source_lang": "en", "source": "push now go go go",
     "target_zh": "现在冲 冲冲冲", "terms": ["push"], "tags": ["strategy"], "quality": "curated"},
    {"id": "en_010", "source_lang": "en", "source": "graves combo with blade",
     "target_zh": "引力配合龙刃", "terms": ["Graviton Surge", "Dragonblade"], "tags": ["ability", "strategy"], "quality": "curated"},
    {"id": "en_011", "source_lang": "en", "source": "ez",
     "target_zh": "轻松", "terms": ["ez"], "tags": ["slang", "post-match"], "quality": "curated"},
    {"id": "en_012", "source_lang": "en", "source": "uninstall please",
     "target_zh": "求你卸载吧", "terms": ["uninstall"], "tags": ["slang", "toxic"], "quality": "curated"},
    {"id": "en_013", "source_lang": "en", "source": "genji is flanking",
     "target_zh": "源氏在绕后", "terms": ["Genji", "flanking"], "tags": ["hero", "callout"], "quality": "curated"},
    {"id": "en_014", "source_lang": "en", "source": "they have ult",
     "target_zh": "他们有大", "terms": [], "tags": ["callout"], "quality": "curated"},
    {"id": "en_015", "source_lang": "en", "source": "focus the mercy",
     "target_zh": "集火天使", "terms": ["Mercy", "focus"], "tags": ["hero", "strategy"], "quality": "curated"},
    {"id": "en_016", "source_lang": "en", "source": "one one one",
     "target_zh": "就一个就一个", "terms": ["one"], "tags": ["callout"], "quality": "curated"},
    {"id": "en_017", "source_lang": "en", "source": "lamp down push",
     "target_zh": "灯倒了 冲", "terms": ["lamp down", "push"], "tags": ["ability", "strategy"], "quality": "curated"},
    {"id": "en_018", "source_lang": "en", "source": "dps diff gg",
     "target_zh": "输出差距 gg", "terms": ["dps diff", "gg"], "tags": ["slang", "post-match"], "quality": "curated"},
    {"id": "en_019", "source_lang": "en", "source": "high ground take high ground",
     "target_zh": "高台 抢高台", "terms": ["high ground"], "tags": ["strategy"], "quality": "curated"},
    {"id": "en_020", "source_lang": "en", "source": "play safe wait for team",
     "target_zh": "稳一点 等队友", "terms": ["play safe"], "tags": ["strategy"], "quality": "curated"},
    {"id": "en_021", "source_lang": "en", "source": "dont peek widow",
     "target_zh": "别露头 有黑百合", "terms": ["dont peek", "Widowmaker"], "tags": ["callout"], "quality": "curated"},
    {"id": "en_022", "source_lang": "en", "source": "mercy low go kill her",
     "target_zh": "天使残血 去杀她", "terms": ["Mercy", "low"], "tags": ["callout"], "quality": "curated"},
    {"id": "en_023", "source_lang": "en", "source": "slept the genji",
     "target_zh": "睡了源氏", "terms": ["slept", "Genji"], "tags": ["ability"], "quality": "curated"},
    {"id": "en_024", "source_lang": "en", "source": "regroup dont stagger",
     "target_zh": "重新集合 别送", "terms": ["regroup"], "tags": ["strategy"], "quality": "curated"},
    {"id": "en_025", "source_lang": "en", "source": "cracked aim",
     "target_zh": "枪太准了", "terms": ["cracked"], "tags": ["slang"], "quality": "curated"},
    {"id": "en_026", "source_lang": "en", "source": "fall back fall back",
     "target_zh": "后撤 后撤", "terms": ["fall back"], "tags": ["strategy"], "quality": "curated"},
    {"id": "en_027", "source_lang": "en", "source": "zarya has grav",
     "target_zh": "查莉娅有引力", "terms": ["Zarya", "grav"], "tags": ["callout", "ability"], "quality": "curated"},
    {"id": "en_028", "source_lang": "en", "source": "im tilted",
     "target_zh": "我上头了", "terms": ["tilted"], "tags": ["slang"], "quality": "curated"},
    {"id": "en_029", "source_lang": "en", "source": "nice clutch",
     "target_zh": "漂亮 翻盘了", "terms": ["clutch"], "tags": ["slang", "reaction"], "quality": "curated"},
    {"id": "en_030", "source_lang": "en", "source": "peel for me peel",
     "target_zh": "帮我拆一下 帮我", "terms": ["peel"], "tags": ["phrase"], "quality": "curated"},
    {"id": "en_031", "source_lang": "en", "source": "boosted player",
     "target_zh": "被带上来的", "terms": ["boosted"], "tags": ["slang", "toxic"], "quality": "curated"},
    {"id": "en_032", "source_lang": "en", "source": "widow sightline dont go there",
     "target_zh": "黑百合视线 别过去", "terms": ["widow sightline"], "tags": ["callout"], "quality": "curated"},
    {"id": "en_033", "source_lang": "en", "source": "c9 omg",
     "target_zh": "C9了 我的天", "terms": ["c9"], "tags": ["slang", "reaction"], "quality": "curated"},
    {"id": "en_034", "source_lang": "en", "source": "point A take it",
     "target_zh": "A点 占", "terms": ["point A"], "tags": ["strategy"], "quality": "curated"},
    {"id": "en_035", "source_lang": "en", "source": "hardstuck diamond",
     "target_zh": "卡钻石了", "terms": ["hardstuck"], "tags": ["slang"], "quality": "curated"},
    {"id": "en_036", "source_lang": "en", "source": "ana anti them",
     "target_zh": "安娜禁疗他们", "terms": ["Ana", "anti"], "tags": ["hero", "ability"], "quality": "curated"},
    {"id": "en_037", "source_lang": "en", "source": "go in go in",
     "target_zh": "冲 冲", "terms": ["go in"], "tags": ["strategy"], "quality": "curated"},
    {"id": "en_038", "source_lang": "en", "source": "lucio beat incoming",
     "target_zh": "卢西奥要开音障了", "terms": ["Lucio", "beat"], "tags": ["hero", "ability"], "quality": "curated"},
    {"id": "en_039", "source_lang": "en", "source": "smurf on the other team",
     "target_zh": "对面有炸鱼的", "terms": ["smurf"], "tags": ["slang"], "quality": "curated"},
    {"id": "en_040", "source_lang": "en", "source": "nice grav nice grav",
     "target_zh": "好引力 好引力", "terms": ["grav"], "tags": ["ability", "reaction"], "quality": "curated"},
    {"id": "en_041", "source_lang": "en", "source": "backcap backcap",
     "target_zh": "偷点 偷点", "terms": ["backcap"], "tags": ["mode"], "quality": "curated"},
    {"id": "en_042", "source_lang": "en", "source": "flanking behind us",
     "target_zh": "有人绕后", "terms": ["flanking"], "tags": ["callout"], "quality": "curated"},
    {"id": "en_043", "source_lang": "en", "source": "swap off genji",
     "target_zh": "换掉源氏", "terms": ["swap", "Genji"], "tags": ["hero", "strategy"], "quality": "curated"},
    {"id": "en_044", "source_lang": "en", "source": "no ult no ult",
     "target_zh": "没有大 没有大", "terms": ["no ult"], "tags": ["callout"], "quality": "curated"},
    {"id": "en_045", "source_lang": "en", "source": "combo ult combo",
     "target_zh": "大招配合 配合", "terms": ["combo ult"], "tags": ["strategy"], "quality": "curated"},
    {"id": "en_046", "source_lang": "en", "source": "im pocketing you",
     "target_zh": "我跟定你了", "terms": ["pocketing"], "tags": ["slang"], "quality": "curated"},
    {"id": "en_047", "source_lang": "en", "source": "deranking gg",
     "target_zh": "掉分了 gg", "terms": ["derank", "gg"], "tags": ["slang", "post-match"], "quality": "curated"},
    {"id": "en_048", "source_lang": "en", "source": "behind behind",
     "target_zh": "后面 后面", "terms": ["behind"], "tags": ["callout"], "quality": "curated"},
    {"id": "en_049", "source_lang": "en", "source": "on me on me",
     "target_zh": "在我这 在我这", "terms": ["on me"], "tags": ["callout"], "quality": "curated"},
    {"id": "en_050", "source_lang": "en", "source": "gg close game",
     "target_zh": "gg 好局", "terms": ["gg"], "tags": ["post-match"], "quality": "curated"},
]

# === Seed few-shot samples (KO -> ZH) ===
SEED_FEW_SHOT_KO: list[dict] = [
    {"id": "ko_001", "source_lang": "ko", "source": "힐줘 힐줘",
     "target_zh": "奶我 奶我", "terms": ["힐줘"], "tags": ["phrase"], "quality": "curated"},
    {"id": "ko_002", "source_lang": "ko", "source": "모여 모여",
     "target_zh": "集合 集合", "terms": ["모여"], "tags": ["strategy"], "quality": "curated"},
    {"id": "ko_003", "source_lang": "ko", "source": "밀어 밀어",
     "target_zh": "推 推", "terms": ["밀어"], "tags": ["strategy"], "quality": "curated"},
    {"id": "ko_004", "source_lang": "ko", "source": "트레이서 교체해",
     "target_zh": "换猎空", "terms": ["트레이서", "교체"], "tags": ["hero", "strategy"], "quality": "curated"},
    {"id": "ko_005", "source_lang": "ko", "source": "겐지 뒤에서",
     "target_zh": "源氏在后面", "terms": ["겐지"], "tags": ["callout"], "quality": "curated"},
    {"id": "ko_006", "source_lang": "ko", "source": "메르시 잡아",
     "target_zh": "杀天使", "terms": ["메르시"], "tags": ["callout"], "quality": "curated"},
    {"id": "ko_007", "source_lang": "ko", "source": "아나 안티 맞았다",
     "target_zh": "被安娜禁疗了", "terms": ["아나"], "tags": ["callout"], "quality": "curated"},
    {"id": "ko_008", "source_lang": "ko", "source": "디바 봄",
     "target_zh": "D.Va炸弹", "terms": ["디바"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_009", "source_lang": "ko", "source": "루시우 비트",
     "target_zh": "卢西奥音障", "terms": ["루시우"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_010", "source_lang": "ko", "source": "라인하르트 쉴드 없어",
     "target_zh": "莱因哈特没盾了", "terms": ["라인하르트"], "tags": ["callout"], "quality": "curated"},
    {"id": "ko_011", "source_lang": "ko", "source": "뒤로 빠져",
     "target_zh": "后撤", "terms": ["뒤로"], "tags": ["strategy"], "quality": "curated"},
    {"id": "ko_012", "source_lang": "ko", "source": "윈스턴 점프",
     "target_zh": "温斯顿跳了", "terms": ["윈스턴"], "tags": ["callout"], "quality": "curated"},
    {"id": "ko_013", "source_lang": "ko", "source": " 자리아 그라브",
     "target_zh": "查莉娅引力", "terms": ["자리아"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_014", "source_lang": "ko", "source": "위도우 조심",
     "target_zh": "小心黑百合", "terms": ["위도우"], "tags": ["callout"], "quality": "curated"},
    {"id": "ko_015", "source_lang": "ko", "source": "리퍼 뒤에",
     "target_zh": "死神在后面", "terms": ["리퍼"], "tags": ["callout"], "quality": "curated"},
    {"id": "ko_016", "source_lang": "ko", "source": "캐서디 하이눈",
     "target_zh": "卡西迪午时已到", "terms": ["캐서디"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_017", "source_lang": "ko", "source": "솔저 태크",
     "target_zh": "士兵76目镜", "terms": ["솔저"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_018", "source_lang": "ko", "source": "모이라 코알",
     "target_zh": "莫伊拉聚合射线", "terms": ["모이라"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_019", "source_lang": "ko", "source": "키리코 키츠네",
     "target_zh": "雾子狐神", "terms": ["키리코"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_020", "source_lang": "ko", "source": "둠피스트 메테",
     "target_zh": "末日铁拳流星锤", "terms": ["둠피스트"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_021", "source_lang": "ko", "source": "파라 포화",
     "target_zh": "法老之鹰弹幕", "terms": ["파라"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_022", "source_lang": "ko", "source": "정크랫 타이어",
     "target_zh": "狂鼠轮胎", "terms": ["정크랫"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_023", "source_lang": "ko", "source": "토르비른 몰트코어",
     "target_zh": "托比昂熔火核心", "terms": ["토르비른"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_024", "source_lang": "ko", "source": "시그마 플럭스",
     "target_zh": "西格玛引力流", "terms": ["시그마"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_025", "source_lang": "ko", "source": "한조 용",
     "target_zh": "半藏龙", "terms": ["한조"], "tags": ["ability"], "quality": "curated"},
    {"id": "ko_026", "source_lang": "ko", "source": "차이 차이",
     "target_zh": "差距 差距", "terms": ["차이"], "tags": ["slang"], "quality": "curated"},
    {"id": "ko_027", "source_lang": "ko", "source": "힐줘 제발",
     "target_zh": "奶我 求你了", "terms": ["힐줘"], "tags": ["phrase"], "quality": "curated"},
]

# === Seed few-shot samples (JA -> ZH) ===
SEED_FEW_SHOT_JA: list[dict] = [
    {"id": "ja_001", "source_lang": "ja", "source": "ヒーラー助けて",
     "target_zh": "奶妈救命", "terms": ["ヒーラー"], "tags": ["phrase"], "quality": "curated"},
    {"id": "ja_002", "source_lang": "ja", "source": "集合して",
     "target_zh": "集合", "terms": ["集合"], "tags": ["strategy"], "quality": "curated"},
    {"id": "ja_003", "source_lang": "ja", "source": "トレーサー交代して",
     "target_zh": "换猎空", "terms": ["トレーサー"], "tags": ["hero", "strategy"], "quality": "curated"},
    {"id": "ja_004", "source_lang": "ja", "source": "ゲンジ後ろ",
     "target_zh": "源氏在后面", "terms": ["ゲンジ"], "tags": ["callout"], "quality": "curated"},
    {"id": "ja_005", "source_lang": "ja", "source": "マーシー落とせ",
     "target_zh": "杀天使", "terms": ["マーシー"], "tags": ["callout"], "quality": "curated"},
    {"id": "ja_006", "source_lang": "ja", "source": "アナの禁療ついた",
     "target_zh": "被安娜禁疗了", "terms": ["アナ"], "tags": ["callout"], "quality": "curated"},
    {"id": "ja_007", "source_lang": "ja", "source": "D.Vaの自爆",
     "target_zh": "D.Va炸弹", "terms": ["D.Va"], "tags": ["ability"], "quality": "curated"},
    {"id": "ja_008", "source_lang": "ja", "source": "ルシオのバリア",
     "target_zh": "卢西奥音障", "terms": ["ルシオ"], "tags": ["ability"], "quality": "curated"},
    {"id": "ja_009", "source_lang": "ja", "source": "ラインハルトの盾ない",
     "target_zh": "莱因哈特没盾了", "terms": ["ラインハルト"], "tags": ["callout"], "quality": "curated"},
    {"id": "ja_010", "source_lang": "ja", "source": "後ろに下がって",
     "target_zh": "后撤", "terms": [], "tags": ["strategy"], "quality": "curated"},
    {"id": "ja_011", "source_lang": "ja", "source": "ウィンストン飛んだ",
     "target_zh": "温斯顿跳了", "terms": ["ウィンストン"], "tags": ["callout"], "quality": "curated"},
    {"id": "ja_012", "source_lang": "ja", "source": "シグマのグラビトン",
     "target_zh": "西格玛引力", "terms": ["シグマ"], "tags": ["ability"], "quality": "curated"},
    {"id": "ja_013", "source_lang": "ja", "source": "ウィドウ気をつけて",
     "target_zh": "小心黑百合", "terms": ["ウィドウ"], "tags": ["callout"], "quality": "curated"},
    {"id": "ja_014", "source_lang": "ja", "source": "リーパー後ろに",
     "target_zh": "死神在后面", "terms": ["リーパー"], "tags": ["callout"], "quality": "curated"},
    {"id": "ja_015", "source_lang": "ja", "source": "キャスディのデッドアイ",
     "target_zh": "卡西迪午时已到", "terms": ["キャスディ"], "tags": ["ability"], "quality": "curated"},
    {"id": "ja_016", "source_lang": "ja", "source": "ソルジャーのタクティカルバイザー",
     "target_zh": "士兵76目镜", "terms": ["ソルジャー76"], "tags": ["ability"], "quality": "curated"},
    {"id": "ja_017", "source_lang": "ja", "source": "モイラのCoalescence",
     "target_zh": "莫伊拉聚合射线", "terms": ["モイラ"], "tags": ["ability"], "quality": "curated"},
    {"id": "ja_018", "source_lang": "ja", "source": "キリコの狐",
     "target_zh": "雾子狐神", "terms": ["キリコ"], "tags": ["ability"], "quality": "curated"},
    {"id": "ja_019", "source_lang": "ja", "source": "ハンゾーの龍",
     "target_zh": "半藏龙", "terms": ["ハンゾー"], "tags": ["ability"], "quality": "curated"},
    {"id": "ja_020", "source_lang": "ja", "source": "タンクの差",
     "target_zh": "坦克差距", "terms": ["タンク"], "tags": ["slang"], "quality": "curated"},
    {"id": "ja_021", "source_lang": "ja", "source": "アナのスリープ",
     "target_zh": "安娜睡了", "terms": ["アナ"], "tags": ["ability"], "quality": "curated"},
    {"id": "ja_022", "source_lang": "ja", "source": "フォーカスして",
     "target_zh": "集火", "terms": [], "tags": ["strategy"], "quality": "curated"},
    {"id": "ja_023", "source_lang": "ja", "source": "フレイカー出てる",
     "target_zh": "有人绕后", "terms": [], "tags": ["callout"], "quality": "curated"},
    {"id": "ja_024", "source_lang": "ja", "source": "アルティメットない",
     "target_zh": "没有大", "terms": [], "tags": ["callout"], "quality": "curated"},
    {"id": "ja_025", "source_lang": "ja", "source": "後ろ気をつけて",
     "target_zh": "小心后面", "terms": [], "tags": ["callout"], "quality": "curated"},
]


class FewShotLibrary:
    def __init__(self, data_dir: Path | None = None):
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        self._data_dir = data_dir
        self._samples: dict[str, list[dict]] = {}
        self._load()

    def _load(self):
        for lang in ("en", "ko", "ja"):
            path = self._data_dir / f"few_shot_{lang}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._samples[lang] = json.load(f)
            else:
                self._samples[lang] = []

    def get_samples(self, source_lang: str) -> list[dict]:
        return self._samples.get(source_lang, [])

    def retrieve(self, text: str, source_lang: str, top_k: int = 3) -> list[dict]:
        """Retrieve the top_k most relevant samples using keyword overlap + length similarity."""
        samples = self.get_samples(source_lang)
        if not samples:
            return []

        text_tokens = set(text.lower().split())
        text_len = len(text)

        scored = []
        for sample in samples:
            sample_tokens = set(sample["source"].lower().split())
            # Jaccard overlap
            intersection = text_tokens & sample_tokens
            union = text_tokens | sample_tokens
            jaccard = len(intersection) / len(union) if union else 0.0

            # Length similarity (prefer similar char count)
            len_ratio = min(text_len, len(sample["source"])) / max(text_len, len(sample["source"])) if max(text_len, len(sample["source"])) > 0 else 0.0

            # Tag bonus: if sample shares tags with detected context
            tag_bonus = 0.0
            if any(t in sample.get("tags", []) for t in ["slang", "phrase"]):
                tag_bonus = 0.05

            score = jaccard * 0.6 + len_ratio * 0.3 + tag_bonus

            # Boost curated samples
            if sample.get("quality") == "curated":
                score += 0.05

            scored.append((score, sample))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_k]]


def generate_few_shot_samples(lang: str = "en", output_dir: Path | None = None):
    """Generate few-shot samples from seed data and save to JSON."""
    if output_dir is None:
        output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    seed_map = {
        "en": SEED_FEW_SHOT_EN,
        "ko": SEED_FEW_SHOT_KO,
        "ja": SEED_FEW_SHOT_JA,
    }

    seeds = seed_map.get(lang, [])
    if not seeds:
        logger.warning("No seed data for language: %s", lang)
        return

    output_path = output_dir / f"few_shot_{lang}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(seeds, f, ensure_ascii=False, indent=2)
    logger.info("Generated %d few-shot samples for %s -> %s", len(seeds), lang, output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for lang in ("en", "ko", "ja"):
        generate_few_shot_samples(lang)
    print("Few-shot samples generated for all languages")
