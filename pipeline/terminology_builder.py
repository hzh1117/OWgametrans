import json
import logging
import re
import time
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger("gametrans.pipeline.terminology")

# === SEED TERMS: 200+ Overwatch entries ===

SEED_TERMS: list[dict] = [
    # ── Hero names (EN) ──
    {"term": "Tracer", "source_lang": "en", "target_zh": "猎空", "category": "hero", "confidence": 1.0},
    {"term": "Reinhardt", "source_lang": "en", "target_zh": "莱因哈特", "category": "hero", "confidence": 1.0},
    {"term": "rein", "source_lang": "en", "target_zh": "莱因哈特", "category": "hero", "confidence": 1.0},
    {"term": "Winston", "source_lang": "en", "target_zh": "温斯顿", "category": "hero", "confidence": 1.0},
    {"term": "winston", "source_lang": "en", "target_zh": "温斯顿", "category": "hero", "confidence": 1.0},
    {"term": "D.Va", "source_lang": "en", "target_zh": "D.Va", "category": "hero", "confidence": 1.0},
    {"term": "dva", "source_lang": "en", "target_zh": "D.Va", "category": "hero", "confidence": 1.0},
    {"term": "Wrecking Ball", "source_lang": "en", "target_zh": "破坏球", "category": "hero", "confidence": 1.0},
    {"term": "ball", "source_lang": "en", "target_zh": "破坏球", "category": "hero", "confidence": 0.7},
    {"term": "Orisa", "source_lang": "en", "target_zh": "奥丽莎", "category": "hero", "confidence": 1.0},
    {"term": "Sigma", "source_lang": "en", "target_zh": "西格玛", "category": "hero", "confidence": 1.0},
    {"term": "Roadhog", "source_lang": "en", "target_zh": "路霸", "category": "hero", "confidence": 1.0},
    {"term": "hog", "source_lang": "en", "target_zh": "路霸", "category": "hero", "confidence": 0.7},
    {"term": "Zarya", "source_lang": "en", "target_zh": "查莉娅", "category": "hero", "confidence": 1.0},
    {"term": "zarya", "source_lang": "en", "target_zh": "查莉娅", "category": "hero", "confidence": 1.0},
    {"term": "Ramattra", "source_lang": "en", "target_zh": "拉玛刹", "category": "hero", "confidence": 1.0},
    {"term": "Mauga", "source_lang": "en", "target_zh": "毛加", "category": "hero", "confidence": 1.0},
    {"term": "Junker Queen", "source_lang": "en", "target_zh": "渣客女王", "category": "hero", "confidence": 1.0},
    {"term": "queen", "source_lang": "en", "target_zh": "渣客女王", "category": "hero", "confidence": 0.6},
    {"term": "Doomfist", "source_lang": "en", "target_zh": "末日铁拳", "category": "hero", "confidence": 1.0},
    {"term": "doom", "source_lang": "en", "target_zh": "末日铁拳", "category": "hero", "confidence": 0.7},
    {"term": "Soldier: 76", "source_lang": "en", "target_zh": "士兵76", "category": "hero", "confidence": 1.0},
    {"term": "soldier", "source_lang": "en", "target_zh": "士兵76", "category": "hero", "confidence": 0.8},
    {"term": "Cassidy", "source_lang": "en", "target_zh": "卡西迪", "category": "hero", "confidence": 1.0},
    {"term": "cass", "source_lang": "en", "target_zh": "卡西迪", "category": "hero", "confidence": 0.7},
    {"term": "Sojourn", "source_lang": "en", "target_zh": "索杰恩", "category": "hero", "confidence": 1.0},
    {"term": "Ashe", "source_lang": "en", "target_zh": "艾什", "category": "hero", "confidence": 1.0},
    {"term": "Bastion", "source_lang": "en", "target_zh": "堡垒", "category": "hero", "confidence": 1.0},
    {"term": "Hanzo", "source_lang": "en", "target_zh": "半藏", "category": "hero", "confidence": 1.0},
    {"term": "Junkrat", "source_lang": "en", "target_zh": "狂鼠", "category": "hero", "confidence": 1.0},
    {"term": "Mei", "source_lang": "en", "target_zh": "美", "category": "hero", "confidence": 1.0},
    {"term": "Pharah", "source_lang": "en", "target_zh": "法老之鹰", "category": "hero", "confidence": 1.0},
    {"term": "pharah", "source_lang": "en", "target_zh": "法老之鹰", "category": "hero", "confidence": 1.0},
    {"term": "Reaper", "source_lang": "en", "target_zh": "死神", "category": "hero", "confidence": 1.0},
    {"term": "reaper", "source_lang": "en", "target_zh": "死神", "category": "hero", "confidence": 1.0},
    {"term": "Symmetra", "source_lang": "en", "target_zh": "秩序之光", "category": "hero", "confidence": 1.0},
    {"term": "sym", "source_lang": "en", "target_zh": "秩序之光", "category": "hero", "confidence": 0.7},
    {"term": "Torbjorn", "source_lang": "en", "target_zh": "托比昂", "category": "hero", "confidence": 1.0},
    {"term": "torb", "source_lang": "en", "target_zh": "托比昂", "category": "hero", "confidence": 0.7},
    {"term": "Widowmaker", "source_lang": "en", "target_zh": "黑百合", "category": "hero", "confidence": 1.0},
    {"term": "widow", "source_lang": "en", "target_zh": "黑百合", "category": "hero", "confidence": 0.8},
    {"term": "Genji", "source_lang": "en", "target_zh": "源氏", "category": "hero", "confidence": 1.0},
    {"term": "genji", "source_lang": "en", "target_zh": "源氏", "category": "hero", "confidence": 1.0},
    {"term": "gen", "source_lang": "en", "target_zh": "源氏", "category": "hero", "confidence": 0.6},
    {"term": "Sombra", "source_lang": "en", "target_zh": "黑影", "category": "hero", "confidence": 1.0},
    {"term": "Echo", "source_lang": "en", "target_zh": "回声", "category": "hero", "confidence": 1.0},
    {"term": "Venture", "source_lang": "en", "target_zh": "探奇", "category": "hero", "confidence": 1.0},
    {"term": "Freja", "source_lang": "en", "target_zh": "芙蕾雅", "category": "hero", "confidence": 1.0},
    {"term": "Mercy", "source_lang": "en", "target_zh": "天使", "category": "hero", "confidence": 1.0},
    {"term": "mercy", "source_lang": "en", "target_zh": "天使", "category": "hero", "confidence": 1.0},
    {"term": "Ana", "source_lang": "en", "target_zh": "安娜", "category": "hero", "confidence": 1.0},
    {"term": "ana", "source_lang": "en", "target_zh": "安娜", "category": "hero", "confidence": 1.0},
    {"term": "Lucio", "source_lang": "en", "target_zh": "卢西奥", "category": "hero", "confidence": 1.0},
    {"term": "lucio", "source_lang": "en", "target_zh": "卢西奥", "category": "hero", "confidence": 1.0},
    {"term": "Moira", "source_lang": "en", "target_zh": "莫伊拉", "category": "hero", "confidence": 1.0},
    {"term": "moira", "source_lang": "en", "target_zh": "莫伊拉", "category": "hero", "confidence": 1.0},
    {"term": "Brigitte", "source_lang": "en", "target_zh": "布丽吉塔", "category": "hero", "confidence": 1.0},
    {"term": "brig", "source_lang": "en", "target_zh": "布丽吉塔", "category": "hero", "confidence": 0.8},
    {"term": "Baptiste", "source_lang": "en", "target_zh": "巴蒂斯特", "category": "hero", "confidence": 1.0},
    {"term": "bap", "source_lang": "en", "target_zh": "巴蒂斯特", "category": "hero", "confidence": 0.7},
    {"term": "Zenyatta", "source_lang": "en", "target_zh": "禅雅塔", "category": "hero", "confidence": 1.0},
    {"term": "zen", "source_lang": "en", "target_zh": "禅雅塔", "category": "hero", "confidence": 0.7},
    {"term": "Kiriko", "source_lang": "en", "target_zh": "雾子", "category": "hero", "confidence": 1.0},
    {"term": "kiriko", "source_lang": "en", "target_zh": "雾子", "category": "hero", "confidence": 1.0},
    {"term": "Lifeweaver", "source_lang": "en", "target_zh": "生命之梭", "category": "hero", "confidence": 1.0},
    {"term": "Illari", "source_lang": "en", "target_zh": "伊拉锐", "category": "hero", "confidence": 1.0},
    {"term": "Juno", "source_lang": "en", "target_zh": "朱诺", "category": "hero", "confidence": 1.0},

    # ── Ability names ──
    {"term": "Graviton Surge", "source_lang": "en", "target_zh": "引力乱流", "category": "ability", "confidence": 1.0},
    {"term": "grav", "source_lang": "en", "target_zh": "引力乱流", "category": "ability", "confidence": 0.9},
    {"term": "Dragonblade", "source_lang": "en", "target_zh": "龙刃", "category": "ability", "confidence": 1.0},
    {"term": "blade", "source_lang": "en", "target_zh": "龙刃", "category": "ability", "confidence": 0.6},
    {"term": "Nanoboost", "source_lang": "en", "target_zh": "纳米激素", "category": "ability", "confidence": 1.0},
    {"term": "nano", "source_lang": "en", "target_zh": "纳米激素", "category": "ability", "confidence": 0.9},
    {"term": "Tactical Visor", "source_lang": "en", "target_zh": "战术目镜", "category": "ability", "confidence": 1.0},
    {"term": "visors", "source_lang": "en", "target_zh": "战术目镜", "category": "ability", "confidence": 0.7},
    {"term": "Rally", "source_lang": "en", "target_zh": "集结号令", "category": "ability", "confidence": 1.0},
    {"term": "Primal Rage", "source_lang": "en", "target_zh": "原始暴怒", "category": "ability", "confidence": 1.0},
    {"term": "primal", "source_lang": "en", "target_zh": "原始暴怒", "category": "ability", "confidence": 0.8},
    {"term": "Self-Destruct", "source_lang": "en", "target_zh": "自毁", "category": "ability", "confidence": 1.0},
    {"term": "Barrage", "source_lang": "en", "target_zh": "火箭弹幕", "category": "ability", "confidence": 1.0},
    {"term": "RIP-Tire", "source_lang": "en", "target_zh": "轮胎炸弹", "category": "ability", "confidence": 1.0},
    {"term": "Deadeye", "source_lang": "en", "target_zh": "神射手", "category": "ability", "confidence": 1.0},
    {"term": "High Noon", "source_lang": "en", "target_zh": "午时已到", "category": "ability", "confidence": 1.0},
    {"term": "Earthshatter", "source_lang": "en", "target_zh": "裂地猛击", "category": "ability", "confidence": 1.0},
    {"term": "shatter", "source_lang": "en", "target_zh": "裂地猛击", "category": "ability", "confidence": 0.8},
    {"term": "Sound Barrier", "source_lang": "en", "target_zh": "音障", "category": "ability", "confidence": 1.0},
    {"term": "beat", "source_lang": "en", "target_zh": "音障", "category": "ability", "confidence": 0.7},
    {"term": "Transcendence", "source_lang": "en", "target_zh": "圣", "category": "ability", "confidence": 1.0},
    {"term": "trans", "source_lang": "en", "target_zh": "圣", "category": "ability", "confidence": 0.7},
    {"term": "EMP", "source_lang": "en", "target_zh": "电磁脉冲", "category": "ability", "confidence": 1.0},
    {"term": "Coalescence", "source_lang": "en", "target_zh": "聚合射线", "category": "ability", "confidence": 1.0},
    {"term": "Window", "source_lang": "en", "target_zh": "增幅矩阵", "category": "ability", "confidence": 0.7},
    {"term": "Tree", "source_lang": "en", "target_zh": "生命之树", "category": "ability", "confidence": 0.7},
    {"term": "Kitsune Rush", "source_lang": "en", "target_zh": "狐神冲刺", "category": "ability", "confidence": 1.0},
    {"term": "flux", "source_lang": "en", "target_zh": "引力流", "category": "ability", "confidence": 0.8},

    # ── Map names ──
    {"term": "King's Row", "source_lang": "en", "target_zh": "国王大道", "category": "map", "confidence": 1.0},
    {"term": "Dorado", "source_lang": "en", "target_zh": "多拉多", "category": "map", "confidence": 1.0},
    {"term": "Havana", "source_lang": "en", "target_zh": "哈瓦那", "category": "map", "confidence": 1.0},
    {"term": "Numbani", "source_lang": "en", "target_zh": "努巴尼", "category": "map", "confidence": 1.0},
    {"term": "Eichenwalde", "source_lang": "en", "target_zh": "艾兴瓦尔德", "category": "map", "confidence": 1.0},
    {"term": "Hollywood", "source_lang": "en", "target_zh": "好莱坞", "category": "map", "confidence": 1.0},
    {"term": "Watchpoint: Gibraltar", "source_lang": "en", "target_zh": "监测站:直布罗陀", "category": "map", "confidence": 1.0},
    {"term": "Gibraltar", "source_lang": "en", "target_zh": "直布罗陀", "category": "map", "confidence": 0.8},
    {"term": "Rialto", "source_lang": "en", "target_zh": "里阿尔托", "category": "map", "confidence": 1.0},
    {"term": "Circuit Royal", "source_lang": "en", "target_zh": "皇家赛道", "category": "map", "confidence": 1.0},
    {"term": "Ilios", "source_lang": "en", "target_zh": "伊利奥斯", "category": "map", "confidence": 1.0},
    {"term": "Lijiang Tower", "source_lang": "en", "target_zh": "漓江塔", "category": "map", "confidence": 1.0},
    {"term": "Nepal", "source_lang": "en", "target_zh": "尼泊尔", "category": "map", "confidence": 1.0},
    {"term": "Oasis", "source_lang": "en", "target_zh": "绿洲城", "category": "map", "confidence": 1.0},
    {"term": "Busan", "source_lang": "en", "target_zh": "釜山", "category": "map", "confidence": 1.0},
    {"term": "Paraiso", "source_lang": "en", "target_zh": "天堂", "category": "map", "confidence": 1.0},
    {"term": "Colosseo", "source_lang": "en", "target_zh": "斗兽场", "category": "map", "confidence": 1.0},
    {"term": "Midtown", "source_lang": "en", "target_zh": "中城", "category": "map", "confidence": 1.0},
    {"term": "New Queen Street", "source_lang": "en", "target_zh": "新皇后街", "category": "map", "confidence": 1.0},
    {"term": "Shambali", "source_lang": "en", "target_zh": "香巴里", "category": "map", "confidence": 1.0},
    {"term": "Suravasa", "source_lang": "en", "target_zh": "苏拉瓦萨", "category": "map", "confidence": 1.0},

    # ── Mode / abbreviation ──
    {"term": "payload", "source_lang": "en", "target_zh": "运载目标", "category": "mode", "confidence": 1.0},
    {"term": "cart", "source_lang": "en", "target_zh": "车", "category": "mode", "confidence": 0.8},
    {"term": "point", "source_lang": "en", "target_zh": "点", "category": "mode", "confidence": 0.7},
    {"term": "control point", "source_lang": "en", "target_zh": "控制点", "category": "mode", "confidence": 1.0},
    {"term": "KOTH", "source_lang": "en", "target_zh": "占点", "category": "mode", "confidence": 1.0},
    {"term": "push", "source_lang": "en", "target_zh": "推进", "category": "mode", "confidence": 0.8},
    {"term": "flashpoint", "source_lang": "en", "target_zh": "闪点", "category": "mode", "confidence": 1.0},
    {"term": "clash", "source_lang": "en", "target_zh": "冲突", "category": "mode", "confidence": 1.0},
    {"term": "overtime", "source_lang": "en", "target_zh": "加时", "category": "mode", "confidence": 1.0},
    {"term": "OT", "source_lang": "en", "target_zh": "加时", "category": "mode", "confidence": 0.8},
    {"term": "stall", "source_lang": "en", "target_zh": "拖时间", "category": "mode", "confidence": 1.0},
    {"term": "cap", "source_lang": "en", "target_zh": "占点", "category": "mode", "confidence": 0.8},
    {"term": "c9", "source_lang": "en", "target_zh": "C9（忘了占点）", "category": "mode", "confidence": 1.0},
    {"term": "backcap", "source_lang": "en", "target_zh": "偷点", "category": "mode", "confidence": 1.0},

    # ── Role ──
    {"term": "tank", "source_lang": "en", "target_zh": "坦克", "category": "role", "confidence": 1.0},
    {"term": "dps", "source_lang": "en", "target_zh": "输出", "category": "role", "confidence": 1.0},
    {"term": "support", "source_lang": "en", "target_zh": "辅助", "category": "role", "confidence": 1.0},
    {"term": "healer", "source_lang": "en", "target_zh": "奶妈", "category": "role", "confidence": 1.0},
    {"term": "main tank", "source_lang": "en", "target_zh": "主坦", "category": "role", "confidence": 1.0},
    {"term": "off tank", "source_lang": "en", "target_zh": "副坦", "category": "role", "confidence": 1.0},
    {"term": "main support", "source_lang": "en", "target_zh": "主辅", "category": "role", "confidence": 1.0},
    {"term": "flex", "source_lang": "en", "target_zh": "自由人", "category": "role", "confidence": 0.8},

    # ── Player slang (single words) ──
    {"term": "diff", "source_lang": "en", "target_zh": "差距", "category": "slang", "confidence": 1.0},
    {"term": "gg", "source_lang": "en", "target_zh": "gg", "category": "slang", "confidence": 1.0},
    {"term": "throw", "source_lang": "en", "target_zh": "送", "category": "slang", "confidence": 0.9},
    {"term": "throwing", "source_lang": "en", "target_zh": "在送", "category": "slang", "confidence": 1.0},
    {"term": "carry", "source_lang": "en", "target_zh": "带飞", "category": "slang", "confidence": 1.0},
    {"term": "clutch", "source_lang": "en", "target_zh": "翻盘", "category": "slang", "confidence": 0.9},
    {"term": "feed", "source_lang": "en", "target_zh": "送人头", "category": "slang", "confidence": 1.0},
    {"term": "feeding", "source_lang": "en", "target_zh": "在送人头", "category": "slang", "confidence": 1.0},
    {"term": "tilt", "source_lang": "en", "target_zh": "上头", "category": "slang", "confidence": 1.0},
    {"term": "tilted", "source_lang": "en", "target_zh": "上头了", "category": "slang", "confidence": 1.0},
    {"term": "peel", "source_lang": "en", "target_zh": "帮拆", "category": "slang", "confidence": 1.0},
    {"term": "gap", "source_lang": "en", "target_zh": "差距", "category": "slang", "confidence": 0.8},
    {"term": "ez", "source_lang": "en", "target_zh": "轻松", "category": "slang", "confidence": 1.0},
    {"term": "diffed", "source_lang": "en", "target_zh": "被碾压了", "category": "slang", "confidence": 1.0},
    {"term": "swap", "source_lang": "en", "target_zh": "换", "category": "slang", "confidence": 0.8},
    {"term": "switch", "source_lang": "en", "target_zh": "换", "category": "slang", "confidence": 0.8},
    {"term": "cracked", "source_lang": "en", "target_zh": "太猛了", "category": "slang", "confidence": 1.0},
    {"term": "one", "source_lang": "en", "target_zh": "就一个了", "category": "slang", "confidence": 0.6},
    {"term": "low", "source_lang": "en", "target_zh": "残血", "category": "slang", "confidence": 0.7},
    {"term": "anti", "source_lang": "en", "target_zh": "禁疗", "category": "slang", "confidence": 0.9},
    {"term": "purple", "source_lang": "en", "target_zh": "禁疗", "category": "slang", "confidence": 0.8},
    {"term": "sleep", "source_lang": "en", "target_zh": "睡了", "category": "slang", "confidence": 0.8},
    {"term": "slept", "source_lang": "en", "target_zh": "被睡了", "category": "slang", "confidence": 0.9},
    {"term": "boop", "source_lang": "en", "target_zh": "推了一下", "category": "slang", "confidence": 0.8},
    {"term": "pick", "source_lang": "en", "target_zh": "击杀", "category": "slang", "confidence": 0.7},
    {"term": "picks", "source_lang": "en", "target_zh": "击杀数", "category": "slang", "confidence": 0.7},
    {"term": "pocket", "source_lang": "en", "target_zh": "跟", "category": "slang", "confidence": 0.8},
    {"term": "pocketed", "source_lang": "en", "target_zh": "被跟了", "category": "slang", "confidence": 0.9},
    {"term": "smurf", "source_lang": "en", "target_zh": "炸鱼", "category": "slang", "confidence": 1.0},
    {"term": "win trading", "source_lang": "en", "target_zh": "演员", "category": "slang", "confidence": 1.0},
    {"term": "boosted", "source_lang": "en", "target_zh": "被带上来的", "category": "slang", "confidence": 1.0},
    {"term": "hardstuck", "source_lang": "en", "target_zh": "卡段位", "category": "slang", "confidence": 1.0},
    {"term": "derank", "source_lang": "en", "target_zh": "掉分", "category": "slang", "confidence": 1.0},
    {"term": "sr", "source_lang": "en", "target_zh": "分数", "category": "slang", "confidence": 0.7},

    # ── Player slang (phrases) ──
    {"term": "heal me", "source_lang": "en", "target_zh": "奶我", "category": "phrase", "confidence": 1.0},
    {"term": "need heals", "source_lang": "en", "target_zh": "需要治疗", "category": "phrase", "confidence": 1.0},
    {"term": "group up", "source_lang": "en", "target_zh": "集合", "category": "phrase", "confidence": 1.0},
    {"term": "regroup", "source_lang": "en", "target_zh": "重新集合", "category": "phrase", "confidence": 1.0},
    {"term": "push now", "source_lang": "en", "target_zh": "现在冲", "category": "phrase", "confidence": 1.0},
    {"term": "go in", "source_lang": "en", "target_zh": "冲", "category": "phrase", "confidence": 0.8},
    {"term": "fall back", "source_lang": "en", "target_zh": "后撤", "category": "phrase", "confidence": 1.0},
    {"term": "nice shot", "source_lang": "en", "target_zh": "好枪", "category": "phrase", "confidence": 1.0},
    {"term": "nice", "source_lang": "en", "target_zh": "漂亮", "category": "phrase", "confidence": 0.8},
    {"term": "go next", "source_lang": "en", "target_zh": "下一把", "category": "phrase", "confidence": 1.0},
    {"term": "uninstall", "source_lang": "en", "target_zh": "卸载吧", "category": "phrase", "confidence": 1.0},
    {"term": "switch to rein", "source_lang": "en", "target_zh": "换莱因哈特", "category": "phrase", "confidence": 1.0},
    {"term": "tank diff", "source_lang": "en", "target_zh": "坦克差距", "category": "phrase", "confidence": 1.0},
    {"term": "dps diff", "source_lang": "en", "target_zh": "输出差距", "category": "phrase", "confidence": 1.0},
    {"term": "support diff", "source_lang": "en", "target_zh": "辅助差距", "category": "phrase", "confidence": 1.0},
    {"term": "heal diff", "source_lang": "en", "target_zh": "奶量差距", "category": "phrase", "confidence": 1.0},
    {"term": "nano me", "source_lang": "en", "target_zh": "给我激素", "category": "phrase", "confidence": 1.0},
    {"term": "grav combo", "source_lang": "en", "target_zh": "引力配合", "category": "phrase", "confidence": 1.0},
    {"term": "lamp down", "source_lang": "en", "target_zh": "灯倒了", "category": "phrase", "confidence": 1.0},
    {"term": "high ground", "source_lang": "en", "target_zh": "高台", "category": "phrase", "confidence": 1.0},
    {"term": "low ground", "source_lang": "en", "target_zh": "低地", "category": "phrase", "confidence": 1.0},
    {"term": "point A", "source_lang": "en", "target_zh": "A点", "category": "phrase", "confidence": 1.0},
    {"term": "point B", "source_lang": "en", "target_zh": "B点", "category": "phrase", "confidence": 1.0},
    {"term": "peel for me", "source_lang": "en", "target_zh": "帮我拆一下", "category": "phrase", "confidence": 1.0},
    {"term": "focus", "source_lang": "en", "target_zh": "集火", "category": "phrase", "confidence": 0.8},
    {"term": "focus him", "source_lang": "en", "target_zh": "集火他", "category": "phrase", "confidence": 1.0},
    {"term": "on me", "source_lang": "en", "target_zh": "在我这", "category": "phrase", "confidence": 0.8},
    {"term": "behind", "source_lang": "en", "target_zh": "后面", "category": "phrase", "confidence": 0.7},
    {"term": "flanking", "source_lang": "en", "target_zh": "绕后", "category": "phrase", "confidence": 1.0},
    {"term": "they have ult", "source_lang": "en", "target_zh": "他们有大", "category": "phrase", "confidence": 1.0},
    {"term": "no ult", "source_lang": "en", "target_zh": "没有大", "category": "phrase", "confidence": 0.8},
    {"term": "combo ult", "source_lang": "en", "target_zh": "大招配合", "category": "phrase", "confidence": 1.0},
    {"term": "play safe", "source_lang": "en", "target_zh": "稳一点", "category": "phrase", "confidence": 1.0},
    {"term": "dont peek", "source_lang": "en", "target_zh": "别露头", "category": "phrase", "confidence": 1.0},
    {"term": "widow sightline", "source_lang": "en", "target_zh": "黑百合视线", "category": "phrase", "confidence": 1.0},
    {"term": "focus the mercy", "source_lang": "en", "target_zh": "集火天使", "category": "phrase", "confidence": 1.0},
    {"term": "widow is carrying", "source_lang": "en", "target_zh": "黑百合在带飞", "category": "phrase", "confidence": 1.0},
    {"term": "tracer diff", "source_lang": "en", "target_zh": "猎空差距", "category": "phrase", "confidence": 1.0},
    {"term": "genji is flanking", "source_lang": "en", "target_zh": "源氏在绕后", "category": "phrase", "confidence": 1.0},
    {"term": "mercy low", "source_lang": "en", "target_zh": "天使残血", "category": "phrase", "confidence": 1.0},
    {"term": "ana anti", "source_lang": "en", "target_zh": "安娜禁疗", "category": "phrase", "confidence": 1.0},
    {"term": "zarya has grav", "source_lang": "en", "target_zh": "查莉娅有引力", "category": "phrase", "confidence": 1.0},
    {"term": "lucio beat", "source_lang": "en", "target_zh": "卢西奥音障", "category": "phrase", "confidence": 1.0},
    {"term": "dps diff", "source_lang": "en", "target_zh": "输出差距", "category": "phrase", "confidence": 1.0},
    {"term": "support diff", "source_lang": "en", "target_zh": "辅助差距", "category": "phrase", "confidence": 1.0},
    {"term": "heal diff", "source_lang": "en", "target_zh": "奶量差距", "category": "phrase", "confidence": 1.0},

    # ── Hero names (Korean) ──
    {"term": "트레이서", "source_lang": "ko", "target_zh": "猎空", "category": "hero", "confidence": 1.0},
    {"term": "라인하르트", "source_lang": "ko", "target_zh": "莱因哈特", "category": "hero", "confidence": 1.0},
    {"term": "윈스턴", "source_lang": "ko", "target_zh": "温斯顿", "category": "hero", "confidence": 1.0},
    {"term": "디바", "source_lang": "ko", "target_zh": "D.Va", "category": "hero", "confidence": 1.0},
    {"term": "시그마", "source_lang": "ko", "target_zh": "西格玛", "category": "hero", "confidence": 1.0},
    {"term": "자리아", "source_lang": "ko", "target_zh": "查莉娅", "category": "hero", "confidence": 1.0},
    {"term": "리퍼", "source_lang": "ko", "target_zh": "死神", "category": "hero", "confidence": 1.0},
    {"term": "겐지", "source_lang": "ko", "target_zh": "源氏", "category": "hero", "confidence": 1.0},
    {"term": "한조", "source_lang": "ko", "target_zh": "半藏", "category": "hero", "confidence": 1.0},
    {"term": "솔저", "source_lang": "ko", "target_zh": "士兵76", "category": "hero", "confidence": 1.0},
    {"term": "캐서디", "source_lang": "ko", "target_zh": "卡西迪", "category": "hero", "confidence": 1.0},
    {"term": "위도우메이커", "source_lang": "ko", "target_zh": "黑百合", "category": "hero", "confidence": 1.0},
    {"term": "위도우", "source_lang": "ko", "target_zh": "黑百合", "category": "hero", "confidence": 0.9},
    {"term": "메르시", "source_lang": "ko", "target_zh": "天使", "category": "hero", "confidence": 1.0},
    {"term": "아나", "source_lang": "ko", "target_zh": "安娜", "category": "hero", "confidence": 1.0},
    {"term": "루시우", "source_lang": "ko", "target_zh": "卢西奥", "category": "hero", "confidence": 1.0},
    {"term": "모이라", "source_lang": "ko", "target_zh": "莫伊拉", "category": "hero", "confidence": 1.0},
    {"term": "키리코", "source_lang": "ko", "target_zh": "雾子", "category": "hero", "confidence": 1.0},
    {"term": "둠피스트", "source_lang": "ko", "target_zh": "末日铁拳", "category": "hero", "confidence": 1.0},
    {"term": "파라", "source_lang": "ko", "target_zh": "法老之鹰", "category": "hero", "confidence": 1.0},
    {"term": "정크랫", "source_lang": "ko", "target_zh": "狂鼠", "category": "hero", "confidence": 1.0},
    {"term": "토르비른", "source_lang": "ko", "target_zh": "托比昂", "category": "hero", "confidence": 1.0},

    # ── Hero names (Japanese) ──
    {"term": "トレーサー", "source_lang": "ja", "target_zh": "猎空", "category": "hero", "confidence": 1.0},
    {"term": "ラインハルト", "source_lang": "ja", "target_zh": "莱因哈特", "category": "hero", "confidence": 1.0},
    {"term": "ウィンストン", "source_lang": "ja", "target_zh": "温斯顿", "category": "hero", "confidence": 1.0},
    {"term": "D.Va", "source_lang": "ja", "target_zh": "D.Va", "category": "hero", "confidence": 1.0},
    {"term": "シグマ", "source_lang": "ja", "target_zh": "西格玛", "category": "hero", "confidence": 1.0},
    {"term": "リーパー", "source_lang": "ja", "target_zh": "死神", "category": "hero", "confidence": 1.0},
    {"term": "ゲンジ", "source_lang": "ja", "target_zh": "源氏", "category": "hero", "confidence": 1.0},
    {"term": "ハンゾー", "source_lang": "ja", "target_zh": "半藏", "category": "hero", "confidence": 1.0},
    {"term": "ソルジャー76", "source_lang": "ja", "target_zh": "士兵76", "category": "hero", "confidence": 1.0},
    {"term": "キャスディ", "source_lang": "ja", "target_zh": "卡西迪", "category": "hero", "confidence": 1.0},
    {"term": "ウィドウメイカー", "source_lang": "ja", "target_zh": "黑百合", "category": "hero", "confidence": 1.0},
    {"term": "ウィドウ", "source_lang": "ja", "target_zh": "黑百合", "category": "hero", "confidence": 0.9},
    {"term": "マーシー", "source_lang": "ja", "target_zh": "天使", "category": "hero", "confidence": 1.0},
    {"term": "アナ", "source_lang": "ja", "target_zh": "安娜", "category": "hero", "confidence": 1.0},
    {"term": "ルシオ", "source_lang": "ja", "target_zh": "卢西奥", "category": "hero", "confidence": 1.0},
    {"term": "モイラ", "source_lang": "ja", "target_zh": "莫伊拉", "category": "hero", "confidence": 1.0},
    {"term": "キリコ", "source_lang": "ja", "target_zh": "雾子", "category": "hero", "confidence": 1.0},
    {"term": "Doomfist", "source_lang": "ja", "target_zh": "末日铁拳", "category": "hero", "confidence": 1.0},

    # ── Korean slang / phrases ──
    {"term": "힐줘", "source_lang": "ko", "target_zh": "奶我", "category": "phrase", "confidence": 1.0},
    {"term": "모여", "source_lang": "ko", "target_zh": "集合", "category": "phrase", "confidence": 1.0},
    {"term": "밀어", "source_lang": "ko", "target_zh": "推", "category": "phrase", "confidence": 0.8},
    {"term": "뒤로", "source_lang": "ko", "target_zh": "后撤", "category": "phrase", "confidence": 0.8},
    {"term": "교체", "source_lang": "ko", "target_zh": "换", "category": "phrase", "confidence": 0.8},
    {"term": "차이", "source_lang": "ko", "target_zh": "差距", "category": "slang", "confidence": 0.8},

    # ── Japanese slang / phrases ──
    {"term": "ヒーラー", "source_lang": "ja", "target_zh": "奶妈", "category": "role", "confidence": 1.0},
    {"term": "タンク", "source_lang": "ja", "target_zh": "坦克", "category": "role", "confidence": 1.0},
    {"term": "DPS", "source_lang": "ja", "target_zh": "输出", "category": "role", "confidence": 1.0},
    {"term": "集合", "source_lang": "ja", "target_zh": "集合", "category": "phrase", "confidence": 0.8},

    # ── UI / system ──
    {"term": "Play of the Game", "source_lang": "en", "target_zh": "最佳表现", "category": "ui", "confidence": 1.0},
    {"term": "POTG", "source_lang": "en", "target_zh": "最佳表现", "category": "ui", "confidence": 1.0},
    {"term": "Victory", "source_lang": "en", "target_zh": "胜利", "category": "ui", "confidence": 1.0},
    {"term": "Defeat", "source_lang": "en", "target_zh": "失败", "category": "ui", "confidence": 1.0},
]

# Remove duplicate with typo ("test" key)
SEED_TERMS = [t for t in SEED_TERMS if "test" not in t]


class TerminologyDB:
    def __init__(self, data_path: Path | None = None):
        if data_path is None:
            data_path = Path(__file__).parent / "data" / "terminology.json"
        self._path = data_path
        self._entries: list[dict] = []
        self._index: dict[str, dict[str, dict]] = {}  # lang -> term_lower -> entry
        self._trigram_index: dict[str, dict[str, set[str]]] = {}  # lang -> trigram -> set[term_lower]
        self._load()

    def _load(self):
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                self._entries = json.load(f)
        else:
            self._entries = []
        self._rebuild_index()

    @staticmethod
    def _trigrams(text: str) -> set[str]:
        """Extract character trigrams for fuzzy pre-filtering."""
        if len(text) < 3:
            return {text}
        return {text[i:i+3] for i in range(len(text) - 2)}

    def _rebuild_index(self):
        self._index.clear()
        self._trigram_index.clear()
        for entry in self._entries:
            lang = entry["source_lang"]
            term_lower = entry["term"].lower()
            if lang not in self._index:
                self._index[lang] = {}
                self._trigram_index[lang] = {}
            # Keep highest confidence entry for duplicates
            existing = self._index[lang].get(term_lower)
            if existing is None or entry.get("confidence", 0) > existing.get("confidence", 0):
                self._index[lang][term_lower] = entry
            # Build trigram index for single-word terms
            if " " not in term_lower:
                for tri in self._trigrams(term_lower):
                    self._trigram_index[lang].setdefault(tri, set()).add(term_lower)

    def lookup(self, term: str, source_lang: str) -> dict | None:
        lang_index = self._index.get(source_lang, {})
        return lang_index.get(term.lower())

    def fuzzy_match(self, term: str, source_lang: str, threshold: float = 0.8) -> dict | None:
        lang_index = self._index.get(source_lang, {})
        if not lang_index:
            return None
        term_lower = term.lower()
        # Pre-filter using trigram index
        tri_index = self._trigram_index.get(source_lang, {})
        candidates = set()
        for tri in self._trigrams(term_lower):
            candidates.update(tri_index.get(tri, set()))
        if not candidates:
            return None
        best_entry = None
        best_ratio = 0.0
        for candidate in candidates:
            ratio = SequenceMatcher(None, term_lower, candidate).ratio()
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_entry = lang_index.get(candidate)
        return best_entry

    def match_phrases(self, text: str, source_lang: str, threshold: float = 0.8) -> list[tuple[int, int, str, str]]:
        """Find all matching terms/phrases in text. Returns [(start, end, matched_term, target_zh)]."""
        lang_index = self._index.get(source_lang, {})
        if not lang_index:
            return []

        text_lower = text.lower()
        matches = []

        # Sort by term length descending to match longer phrases first
        sorted_entries = sorted(lang_index.values(), key=lambda e: len(e["term"]), reverse=True)

        matched_ranges = []
        for entry in sorted_entries:
            term_lower = entry["term"].lower()
            # Find ALL occurrences of this term in the text
            found_exact = False
            start_pos = 0
            while True:
                idx = text_lower.find(term_lower, start_pos)
                if idx < 0:
                    break
                end = idx + len(term_lower)
                # Check not already covered by a longer match
                overlap = False
                for ms, me in matched_ranges:
                    if idx < me and end > ms:
                        overlap = True
                        break
                if not overlap:
                    matches.append((idx, end, entry["term"], entry["target_zh"]))
                    matched_ranges.append((idx, end))
                    found_exact = True
                start_pos = idx + 1  # advance past this occurrence

            # Fuzzy match per word/token for single-word terms (only if no exact match found)
            if " " not in term_lower and not found_exact:
                tri_index = self._trigram_index.get(source_lang, {})
                for m in re.finditer(r'\b\w+\b', text_lower):
                    word = m.group()
                    # Pre-filter: only compare against terms sharing a trigram
                    word_tris = self._trigrams(word)
                    candidates = set()
                    for tri in word_tris:
                        candidates.update(tri_index.get(tri, set()))
                    if not candidates:
                        continue
                    for candidate in candidates:
                        ratio = SequenceMatcher(None, word, candidate).ratio()
                        if ratio >= threshold:
                            start, end = m.start(), m.end()
                            overlap = False
                            for ms, me in matched_ranges:
                                if start < me and end > ms:
                                    overlap = True
                                    break
                            if not overlap:
                                entry_for_candidate = lang_index.get(candidate)
                                if entry_for_candidate:
                                    matches.append((start, end, entry_for_candidate["term"], entry_for_candidate["target_zh"]))
                                    matched_ranges.append((start, end))
                            break  # one match per word is enough

        matches.sort(key=lambda x: x[0])
        return matches

    def entries(self) -> list[dict]:
        return self._entries

    def add_entry(self, term: str, source_lang: str, target_zh: str,
                  category: str, confidence: float = 0.8):
        entry = {
            "term": term,
            "source_lang": source_lang,
            "target_zh": target_zh,
            "category": category,
            "confidence": confidence,
        }
        self._entries.append(entry)
        lang = source_lang
        term_lower = term.lower()
        if lang not in self._index:
            self._index[lang] = {}
        existing = self._index[lang].get(term_lower)
        if existing is None or confidence > existing.get("confidence", 0):
            self._index[lang][term_lower] = entry

    def save(self, path: Path | None = None):
        target = path or self._path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=2)
        logger.info("Saved %d terminology entries to %s", len(self._entries), target)


def build_terminology_db(api_base_url: str | None = None,
                         api_key: str | None = None,
                         model: str | None = None):
    """Build terminology.json from SEED_TERMS + optional API translation for gaps."""
    db_path = Path(__file__).parent / "data" / "terminology.json"
    db = TerminologyDB(db_path)

    # Merge seed terms
    existing_keys = {(e["term"].lower(), e["source_lang"]) for e in db.entries()}
    new_count = 0
    for seed in SEED_TERMS:
        key = (seed["term"].lower(), seed["source_lang"])
        if key not in existing_keys:
            db.add_entry(
                term=seed["term"],
                source_lang=seed["source_lang"],
                target_zh=seed["target_zh"],
                category=seed["category"],
                confidence=seed["confidence"],
            )
            new_count += 1

    db.save()
    logger.info("Terminology DB built: %d total entries, %d new", len(db.entries()), new_count)
    return db


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_terminology_db()
    print(f"Built terminology.json with {len(SEED_TERMS)} seed entries")
