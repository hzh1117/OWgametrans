"""
CLI entry point for the Translation Enhancement Pipeline.

Usage:
    python run.py --build-db          Build/rebuild terminology database
    python run.py --translate "text" --lang ko   Translate a single text
    python run.py --test              Run batch test with sample texts
    python run.py --gen-few-shot      Generate few-shot samples
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.logging_config import setup_logging


TEST_CASES = [
    # Tier 1: exact matches
    {"source": "gg", "lang": "en", "expected": "gg", "tier": "1"},
    {"source": "ez", "lang": "en", "expected": "轻松", "tier": "1"},
    # Tier 2: phrase matches
    {"source": "tracer diff", "lang": "en", "expected": "差距", "tier": "2"},
    {"source": "heal me", "lang": "en", "expected": "奶我", "tier": "2"},
    {"source": "group up", "lang": "en", "expected": "集合", "tier": "2"},
    {"source": "nice shot", "lang": "en", "expected": "好枪", "tier": "2"},
    {"source": "switch to rein", "lang": "en", "expected": "换", "tier": "2"},
    {"source": "tank diff", "lang": "en", "expected": "差距", "tier": "2"},
    {"source": "go next", "lang": "en", "expected": "下一把", "tier": "2"},
    {"source": "fall back", "lang": "en", "expected": "后撤", "tier": "2"},
    {"source": "focus the mercy", "lang": "en", "expected": "天使", "tier": "2"},
    {"source": "widow is carrying", "lang": "en", "expected": "带飞", "tier": "2"},
    # Tier 3: LLM required
    {"source": "can someone switch to a shield tank please", "lang": "en", "expected": None, "tier": "3"},
    {"source": "i think we should run dive comp", "lang": "en", "expected": None, "tier": "3"},
]


def cmd_build_db(args):
    from pipeline.terminology_builder import build_terminology_db, TerminologyDB
    build_terminology_db()
    db = TerminologyDB()
    print(f"Terminology database built: {len(db.entries())} entries")


def cmd_translate(args):
    from pipeline.translator import EnhancedTranslator
    translator = EnhancedTranslator()
    t0 = time.perf_counter()
    result = translator.translate(args.text, source_lang=args.lang)
    t1 = time.perf_counter()
    if result:
        print(f"Translation: {result}")
        print(f"Time: {(t1 - t0) * 1000:.1f}ms")
    else:
        print("Translation failed", file=sys.stderr)
        sys.exit(1)


def cmd_test(args):
    from pipeline.translator import EnhancedTranslator
    translator = EnhancedTranslator()

    passed = 0
    tier_stats = {"1": [], "2": [], "3": []}

    for i, case in enumerate(TEST_CASES):
        t0 = time.perf_counter()
        result = translator.translate(case["source"], source_lang=case["lang"])
        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000

        # Check if result contains expected keyword
        if case["expected"]:
            ok = result is not None and case["expected"] in (result or "")
        else:
            ok = result is not None  # Tier 3 just needs to not fail

        if ok:
            passed += 1

        tier = case["tier"]
        tier_stats[tier].append(elapsed_ms)

        status = "PASS" if ok else "FAIL"
        print(f"[{i+1:2d}] {status} T{tier} {elapsed_ms:7.1f}ms | {case['source'][:40]:<40} -> {result or 'None'}")

    print(f"\nResults: {passed}/{len(TEST_CASES)} passed")
    for tier, times in tier_stats.items():
        if times:
            avg = sum(times) / len(times)
            print(f"  Tier {tier}: {len(times)} tests, avg {avg:.1f}ms")


def cmd_gen_few_shot(args):
    from pipeline.few_shot_builder import generate_few_shot_samples
    for lang in ("en", "ko", "ja"):
        generate_few_shot_samples(lang)
    print("Few-shot samples generated for all languages")


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="OW Translation Enhancement Pipeline")
    parser.add_argument("--build-db", action="store_true", help="Build terminology database")
    parser.add_argument("--translate", type=str, help="Translate a single text")
    parser.add_argument("--lang", type=str, default="en", help="Source language (en/ko/ja)")
    parser.add_argument("--test", action="store_true", help="Run batch translation test")
    parser.add_argument("--gen-few-shot", action="store_true", help="Generate few-shot samples")
    args = parser.parse_args()

    if args.build_db:
        cmd_build_db(args)
    elif args.translate:
        cmd_translate(args)
    elif args.test:
        cmd_test(args)
    elif args.gen_few_shot:
        cmd_gen_few_shot(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
