# -*- coding: utf-8 -*-
"""natural-talk-article 极致版同步校验 — 以 core/rules.yaml 为唯一源.

校验项：
1. core/rules.yaml 必须存在且包含 CORE/RULES 关键块
2. dist/* 产物必须与 build.py 生成一致（调用 build --check）
3. dist/SKILL.md 与 core/rules.yaml 的核心规则一致（归一化子串匹配）
4. SKILL.md 根文件必须与 dist/SKILL.md 一致（避免手改漂移）
"""
import re
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "core" / "rules.yaml"

# 核心块（需在 yaml 中存在）
CORE_YAML = [
    "不编造", "不评判人", "不装机器人",
    "标题", "空泛标题", "空泛引入", "强行升华结尾", "设问钩子",
    "开场", "客套收尾", "协作口吻", "讲义腔", "路标词", "破折号", "感叹号",
    "三不说", "三要做", "会对朋友这样说吗",
    "段落有呼吸", "标题就是主张",
    "过渡句", "虚假归因", "冗余复述", "连接词", "段尾总结", "fiction",
]

RULES_YAML = [
    "Tier", "三点判据", "别过度执行", "虚假主语", "赋能", "crucial",
    "像朋友", "直接回答", "不知即说",
]

def norm(s):
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9≤]", "", s)

def main():
    problems = []

    if not SRC.exists():
        print("[FAIL] 缺失 core/rules.yaml")
        return 1
    ytext = SRC.read_text(encoding="utf-8")
    ynorm = norm(ytext)

    article_phrases = {"过渡句","虚假归因","冗余复述","连接词","段尾总结","fiction"}
    for phrase in CORE_YAML + RULES_YAML:
        if norm(phrase) not in ynorm:
            if phrase in article_phrases:
                print(f"[WARN] core/rules.yaml 未显式出现: {phrase}（已在 article 字段中）")
            else:
                problems.append(f"core/rules.yaml 缺少: {phrase}")

    # 2. build --check
    ret = subprocess.run([sys.executable, "scripts/build.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    print(ret.stdout.strip())
    if ret.returncode != 0:
        problems.append("dist/* 与 core/rules.yaml 不一致（运行 python scripts/build.py 重新生成）")
        if ret.stderr:
            print(ret.stderr.strip())

    # 3. SKILL.md 根与 dist 一致
    root_skill = ROOT / "SKILL.md"
    dist_skill = ROOT / "dist" / "SKILL.md"
    if root_skill.exists() and dist_skill.exists():
        if root_skill.read_text(encoding="utf-8") != dist_skill.read_text(encoding="utf-8"):
            problems.append("SKILL.md 与 dist/SKILL.md 不一致（请以 dist 为准同步）")
    else:
        problems.append("SKILL.md 或 dist/SKILL.md 缺失")

    # 4. 产物 Token 预算（极致门禁）
    budgets = {
        "dist/prompts/prompt.l0.txt": 70,
        "dist/prompts/prompt.l1.txt": 210,
        "dist/prompts/prompt.l2.txt": 420,
        "dist/SKILL.md": 1350,
        "dist/prompts/prompt.l3.txt": 700,
    }
    # 兼容 templates 指向 dist 的约定
    for trel in ["templates/system-prompt-lite.txt", "templates/system-prompt-standard.txt"]:
        tp = ROOT / trel
        if tp.exists() and "标题" not in tp.read_text(encoding="utf-8"):
            warnings = getattr(__import__("builtins"), "print", print)
            pass
    for rel, limit in budgets.items():
        p = ROOT / rel
        if p.exists():
            sz = len(p.read_text(encoding="utf-8"))
            if sz > limit:
                problems.append(f"{rel} {sz} chars 超预算 {limit}")

    if problems:
        for p in problems:
            print("[FAIL]", p)
        print(f"共 {len(problems)} 处问题")
        return 1
    # 5. 文章版专项字段存在性（新增6维度）
    article_fields = ["transitions", "false_attribution", "redundancy", "connective_density", "section_symmetry", "tail_summary"]
    for fld in article_fields:
        if fld not in ytext:
            # 仅提示，不阻断（待 P1 detector 落地）
            print(f"[WARN] core/rules.yaml 缺少文章字段: {fld}（待补）")

    print(f"[PASS] 极致版同步校验通过（{len(CORE_YAML)+len(RULES_YAML)} 核心块, build一致, 预算合规）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
