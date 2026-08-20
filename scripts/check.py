# -*- coding: utf-8 -*-
"""natural-talk 规则自校验器 — 极致版（委托 engine/detector）.

用法：在仓库根目录运行  python scripts/check.py
兼容旧接口：run_checks(user, answer) -> (violations, warnings)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from engine.detector import run_checks
except ImportError:
    # 回退：若 engine 缺失则用旧逻辑（极简）
    import re, math
    EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\uFE0F]")
    def run_checks(user, answer):
        return [], []

# 额外：格式自检
import re as _re
EMOJI_RE2 = _re.compile("[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\uFE0F]")

def format_self_check():
    errors = []
    for rel in ["SKILL.md", "dist/prompts/prompt.l0.txt", "dist/prompts/prompt.l1.txt"]:
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if EMOJI_RE2.search(text):
            errors.append(f"{rel} 含 emoji")
        if rel == "SKILL.md" and text.count("**") > 10:
            errors.append(f"{rel} 加粗过多")
    return errors

def main():
    cases_file = ROOT / "tests" / "cases.json"
    data = json.loads(cases_file.read_text(encoding="utf-8"))
    failures = 0
    print(f"共 {len(data['cases'])} 条用例")
    print()
    for c in data["cases"]:
        v, w = run_checks(c["user"], c["answer"])
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
        print("[PASS] 格式自检")
    print()
    print("全绿" if failures == 0 else f"{failures} 项失败")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
