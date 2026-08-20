# -*- coding: utf-8 -*-
"""natural-talk-article 规则自校验器 — 极致版（委托 engine/detector.article_check）。

用法：
  python scripts/check.py                          # 跑 tests/cases.json（title+body）
  python scripts/check.py --article "标题" 正文.md  # linter：对单篇扫标题/开头/结尾/段落
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from engine.detector import article_check as run_article
    from engine.detector import run_checks
except ImportError:
    import re as _re
    def run_article(title, body):
        return [], []
    def run_checks(user, answer):
        return [], []

import re as _re2
EMOJI_RE = _re2.compile("[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\uFE0F]")

def format_self_check():
    errors = []
    for rel in ["SKILL.md", "dist/prompts/prompt.l0.txt", "dist/prompts/prompt.l1.txt", "dist/prompts/prompt.l2.txt"]:
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if EMOJI_RE.search(text):
            errors.append(f"{rel} 含 emoji")
        if rel == "SKILL.md" and text.count("**") > 12:
            errors.append(f"{rel} 加粗过多")
    return errors

def main():
    # --article 模式：linter 优先，Token 0
    if "--article" in sys.argv:
        idx = sys.argv.index("--article")
        title = sys.argv[idx+1] if len(sys.argv) > idx+1 else "文章"
        body = ""
        if len(sys.argv) > idx+2:
            p = Path(sys.argv[idx+2])
            if p.exists():
                body = p.read_text(encoding="utf-8")
            else:
                body = " ".join(sys.argv[idx+2:])
        else:
            # 从 stdin 读
            import sys as _sys
            body = _sys.stdin.read() if not _sys.stdin.isatty() else ""
        v, w = run_article(title, body)
        for name, msg in v:
            print(f"违规 {name}: {msg}")
        for msg in w:
            print(f"提示 {msg}")
        print(f"\n共 {len(v)} 违规 {len(w)} 提示 — {'全绿' if not v else '需改'}")
        return 1 if v else 0
    cases_file = ROOT / "tests" / "cases.json"
    data = json.loads(cases_file.read_text(encoding="utf-8"))
    failures = 0
    print(f"共 {len(data['cases'])} 条用例")
    print()
    for c in data["cases"]:
        # 兼容两种结构：title/body（文章版）或 user/answer（旧）
        title = c.get("title", c.get("user", ""))
        body = c.get("body", c.get("answer", ""))
        v, w = run_article(title, body)
        ok = (not v) if c["expect"] == "pass" else bool(v)
        if not ok:
            failures += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {c['id']}（期望 {c['expect']}）")
        for name, msg in v:
            print(f"      违规 {name}: {msg}")
        for msg in w:
            print(f"      提示 {msg}")
    print()
    fmt = format_self_check()
    if fmt:
        failures += len(fmt)
        for e in fmt:
            print(f"[FAIL] 格式自检 {e}")
    else:
        print("[PASS] 格式自检（SKILL 与 prompts 无 emoji/加粗）")
    print()
    print("全绿" if failures == 0 else f"{failures} 项失败")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
