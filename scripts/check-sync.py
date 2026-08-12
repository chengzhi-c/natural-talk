# -*- coding: utf-8 -*-
"""natural-talk 多文件规则同步防漂移。

用法：在仓库根目录运行  python scripts/check-sync.py

唯一源：docs/full-guide.md。
- CORE：核心规则块，须存在于全部 5 个文件（含 README）
- RULES：完整规则块，须存在于 4 个规则文件（不含 README）

比对方式：去除非文字字符（空格、标点、markdown 标记）后做子串匹配，
对格式差异不敏感，对内容漂移敏感。改规则时只改 full-guide.md，
其余文件同步，本脚本做最后防线。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CORE = [
    "不编造", "不评判人", "不装机器人", "身份披露例外",
    "开场白≤1句", "客套收尾≤1次", "协作口吻≤1次", "讲义腔≤1次",
    "路标词≤2次", "破折号≤2次", "感叹号≤3次",
    "直奔主题", "不说作为AI", "会对朋友这样说吗",
]

RULES = [
    "像朋友聊天", "不夸张", "不替对方做心理判断", "句子有长有短",
    "直接回答零开场", "不知道就直说", "主动语态真实主语",
    "具体表达删除空泛词", "承认不确定有边界", "自然节奏打破对称",
    "保持主题不过度平衡",
    "Tier1", "Tier2", "Tier3", "Tier4", "Tier5", "Tier6",
    "三点判据", "别过度执行", "虚假主语", "赋能", "crucial",
]

CORE_TARGETS = [
    "docs/full-guide.md",
    "SKILL.md",
    "README.md",
    "docs/quick-reference.md",
    "templates/system-prompt-standard.txt",
]

RULES_TARGETS = [
    "docs/full-guide.md",
    "SKILL.md",
    "docs/quick-reference.md",
    "templates/system-prompt-standard.txt",
]


def norm(s):
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9≤]", "", s)


def main():
    texts = {}
    for rel in CORE_TARGETS:
        p = ROOT / rel
        if not p.exists():
            print("[FAIL] 文件不存在：{}".format(rel))
            return 1
        texts[rel] = norm(p.read_text(encoding="utf-8"))

    problems = []
    for phrase in CORE + RULES:
        if norm(phrase) not in texts["docs/full-guide.md"]:
            problems.append("唯一源 docs/full-guide.md 缺少规则块：{}".format(phrase))
    for rel in CORE_TARGETS:
        for phrase in CORE:
            if norm(phrase) not in texts[rel]:
                problems.append("{} 缺少核心规则块：{}".format(rel, phrase))
    for rel in RULES_TARGETS:
        for phrase in RULES:
            if norm(phrase) not in texts[rel]:
                problems.append("{} 缺少规则块：{}".format(rel, phrase))

    if problems:
        for p in problems:
            print("[FAIL]", p)
        print("共 {} 处漂移".format(len(problems)))
        return 1
    print("[PASS] 全部规则块同步一致（唯一源 + {} 个文件）".format(len(CORE_TARGETS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
