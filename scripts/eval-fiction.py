# -*- coding: utf-8 -*-
"""Fiction 模式评测：注入 system-prompt-fiction.txt 生成，人工判 AI 味。

用法：
  python scripts/eval-fiction.py                # with-skill vs baseline 对照
  python scripts/eval-fiction.py --no-baseline  # 只跑 with-skill
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _llm import chat_stream, model_name  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEUTRAL = "You are a helpful assistant."

PROMPTS = [
    "写一段：女儿要去外地上大学，父亲送她到火车站，两个人一路话很少。",
    "写一段：一个人深夜加完班走回家，他今天刚被公司辞退，不想回家。",
    "写一段：母亲去菜市场买菜，在外地工作的儿子今晚回来，她买得格外仔细。",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-baseline", action="store_true", help="只跑 with-skill，不跑对照")
    ap.add_argument("--list", action="store_true", help="只列题目，不联网")
    args = ap.parse_args()

    if args.list:
        for i, p in enumerate(PROMPTS, 1):
            print(f"{i}. {p}")
        return 0

    model = model_name()
    fiction = (ROOT / "templates" / "system-prompt-fiction.txt").read_text(encoding="utf-8")
    variants = [("with_fiction", fiction)]
    if not args.no_baseline:
        variants.append(("baseline", NEUTRAL))

    rows = []
    for prompt in PROMPTS:
        row = {"prompt": prompt}
        print("=" * 70)
        print("PROMPT:", prompt)
        for tag, system in variants:
            print("-" * 30, tag)
            try:
                row[tag] = chat_stream(system, prompt, echo=True)
            except Exception as exc:
                row[tag] = f"<ERR {exc}>"
                print(row[tag])
            time.sleep(0.3)
        rows.append(row)

    out = ROOT / "benchmarks" / f"fiction-{model}-{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"model": model, "date": datetime.now().isoformat(), "rows": rows},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("[存档]", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
