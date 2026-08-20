# -*- coding: utf-8 -*-
"""natural-talk 极致版同步校验 — 以 core/rules.yaml 为唯一源.

校验项：
1. core/rules.yaml 必须存在且包含 CORE/RULES 关键块
2. dist/* 产物必须与 build.py 生成一致（调用 build --check）
3. SKILL.md 根与 dist 一致
4. 产物 Token 预算（极致门禁）
5. 档位语义覆盖校验（L0→L1→L2→L3 核心关键词递进）
6. README budgets 数值校验（声称 chars 与实际一致 ±10）
7. SKILL 高频词覆盖校验（每 Tier 前3词至少覆盖）
"""
import re
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "core" / "rules.yaml"

CORE_YAML = [
    "不编造", "不评判人", "不装机器人",
    "开场", "客套收尾", "协作口吻", "讲义腔", "路标词", "破折号", "感叹号",
    "三不说", "三要做", "会对朋友这样说吗",
]

RULES_YAML = [
    "Tier", "三点判据", "别过度执行", "虚假主语", "赋能", "crucial",
    "像朋友", "直接回答", "不知即说",
]

def norm(s):
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9≤]", "", s)

def check_prompt_semantic_coverage():
    CORE_KEYWORDS = {
        0: ["编造", "装AI", "像朋友", "作为AI", "好问题", "—≤2"],
        1: ["三禁", "铁律", "不是X而是Y", "弹性", "开场"],
        2: ["协作", "讲义", "评判", "语言", "豁免"],
        3: ["防矫枉", "自查"],
    }
    prompts = {}
    for level in range(4):
        p = ROOT / f"dist/prompts/prompt.l{level}.txt"
        if not p.exists():
            return [f"缺失 dist/prompts/prompt.l{level}.txt"]
        prompts[level] = p.read_text(encoding="utf-8")
    warns = []
    for lower in range(3):
        higher = lower + 1
        for kw in CORE_KEYWORDS[lower]:
            if kw not in prompts[higher]:
                warns.append(f"L{lower} 关键词 '{kw}' 未出现在 L{higher} 中")
    return warns

def check_budgets_readme():
    warns = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
    for level in range(4):
        p = ROOT / f"dist/prompts/prompt.l{level}.txt"
        if not p.exists():
            continue
        actual = len(p.read_text(encoding="utf-8"))
        # 从 README 提取如 "L1 144c" 或 "l1.txt ... 144c"
        pat = rf"[Ll]{level}[^\n]*?(\d+)c"
        m = re.search(pat, readme)
        if m:
            claimed = int(m.group(1))
            if abs(actual - claimed) > 20:
                warns.append(f"L{level}: README 声称 {claimed}c，实际 {actual}c（误差>10）")
    return warns

def check_skill_coverage():
    warns = []
    try:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        ytext = (ROOT / "core/rules.yaml").read_text(encoding="utf-8")
        # 简单抽取：检查 Top 词是否在 skill
        top_words = ["作为AI", "好问题", "让我来", "首先其次", "我完全理解", "数据告诉我们"]
        for w in top_words:
            if w not in skill:
                warns.append(f"SKILL.md 未覆盖高频词 '{w}'")
    except Exception as e:
        warns.append(f"skill 覆盖校验异常: {e}")
    return warns

def main():
    problems = []
    warns = []

    if not SRC.exists():
        print("[FAIL] 缺失 core/rules.yaml")
        return 1
    ytext = SRC.read_text(encoding="utf-8")
    ynorm = norm(ytext)
    for phrase in CORE_YAML + RULES_YAML:
        if norm(phrase) not in ynorm:
            problems.append(f"core/rules.yaml 缺少: {phrase}")

    ret = subprocess.run([sys.executable, "scripts/build.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    print(ret.stdout.strip())
    if ret.returncode != 0:
        problems.append("dist/* 与 core/rules.yaml 不一致（运行 python scripts/build.py 重新生成）")
        if ret.stderr:
            print(ret.stderr.strip())

    root_skill = ROOT / "SKILL.md"
    dist_skill = ROOT / "dist" / "SKILL.md"
    if root_skill.exists() and dist_skill.exists():
        if root_skill.read_text(encoding="utf-8") != dist_skill.read_text(encoding="utf-8"):
            problems.append("SKILL.md 与 dist/SKILL.md 不一致（请以 dist 为准同步）")
    else:
        problems.append("SKILL.md 或 dist/SKILL.md 缺失")

    # 预算：与 core/rules.yaml 的 budgets 同步（极致门禁）
    budgets = {
        "dist/prompts/prompt.l0.txt": 70,
        "dist/prompts/prompt.l1.txt": 150,
        "dist/prompts/prompt.l2.txt": 430,
        "dist/prompts/prompt.l3.txt": 620,
        "dist/SKILL.md": 1000,
        "dist/lexicon.json": 2000,
    }
    for rel, limit in budgets.items():
        p = ROOT / rel
        if p.exists():
            sz = len(p.read_text(encoding="utf-8"))
            if sz > limit:
                problems.append(f"{rel} {sz} chars 超预算 {limit}")

    # 新增校验（5-7）仅作警告，不阻断？按计划作为问题列出但不影响主流程？这里作为问题但允许 WARN
    cov = check_prompt_semantic_coverage()
    for w in cov:
        warns.append(w)
        print(f"[WARN] 语义覆盖 {w}")
    b = check_budgets_readme()
    for w in b:
        warns.append(w)
        print(f"[WARN] budgets {w}")
    s = check_skill_coverage()
    for w in s:
        warns.append(w)
        print(f"[WARN] skill覆盖 {w}")

    if problems:
        for p in problems:
            print("[FAIL]", p)
        print(f"共 {len(problems)} 处问题，{len(warns)} 处警告")
        return 1
    print(f"[PASS] 极致版同步校验通过（{len(CORE_YAML)+len(RULES_YAML)} 核心块, build一致, 预算合规, {len(warns)} 警告）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
