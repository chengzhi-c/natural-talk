# -*- coding: utf-8 -*-
"""natural-talk 规则自校验器。

用法：在仓库根目录运行  python scripts/check.py

检查内容：
1. tests/cases.json 全部用例：正例须零违规、反例须至少一条违规、
   边缘用例按期望判定（自证要求：反例不命中或正例误报，都是 checker 的 bug，先修 checker）
2. 注入产物格式自检：SKILL.md 与 templates/*.txt 无 emoji、无加粗标记

规则表与 docs/full-guide.md 保持一致，scripts/check-sync.py 负责防漂移。
计数口径：破折号/感叹号/路标词为密度项，按 300 字基准随篇幅折算；
协作痕迹/讲义腔为近绝对项，固定上限 1 次；步骤语义豁免 Tier 2，
身份询问豁免 Tier 1 身份词（身份披露例外）。
"""
import json
import math
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

# ---------- 规则表（与 docs/full-guide.md 同步，check-sync.py 防漂移） ----------

TIER1_IDENTITY = [
    "作为AI", "作为人工智能", "根据我的训练", "基于我的训练数据", "训练数据截至",
    "截至我的知识", "基于我所掌握的信息", "语言模型",
    "as an ai", "based on my training", "i'm an ai",
]

TIER1_COURTESY = [
    "好问题", "很好的问题", "有深度的问题", "这个问题问得好", "感谢提问",
    "感谢你的提问", "感谢你的咨询", "你说得完全对", "如果还有问题",
    "如果还有疑问", "随时告诉我", "欢迎继续交流", "欢迎随时",
    "great question", "you're absolutely right", "i hope this helps",
    "of course", "certainly", "let me know if",
]

HOPE_PATTERN = re.compile(r"希望.{0,12}(帮助|有用|解决|对你)")

NEXT_PATTERN = re.compile(r"接下来\s*[，,]?\s*(?:我|我们)")

TIER2 = [
    "让我来", "让我为你", "下面我们", "综上所述", "由此可见",
    "拆一拆", "盘一盘", "划重点", "敲黑板", "捋一捋", "首先", "其次", "让我们",
    "let me break this down", "let's dive in", "in conclusion",
    "without further ado", "here's what you need to know",
]

SIGNPOSTS = [
    "值得注意的是", "需要强调的是", "更关键的是", "事实上", "实际上",
    "换句话说", "说白了", "本质上", "归根结底", "与此同时",
    "at the end of the day", "actually", "additionally", "furthermore",
    "the truth is", "here's the thing",
]

TIER3_PATTERNS = [
    re.compile(r"不是.{0,30}(而是|而是说)"),
    re.compile(r"不是.{0,40}而是要"),
    re.compile(r"不仅仅.{0,30}(而是|更是)"),
    re.compile(r"不在于.{0,30}而在于"),
    re.compile(r"与其.{0,16}不如"),
    re.compile(r"it's not about", re.I),
    re.compile(r"真正的问题是"),
    re.compile(r"the real question is", re.I),
    re.compile(r"揭开面纱|遮羞布|戳穿真相|背后的真相"),
    re.compile(r"深层原因|the heart of the matter", re.I),
]

TIER4 = [
    "我完全理解", "我懂你的", "你不是敏感", "你问到了", "你有很强的",
    "你的观察力很敏锐", "你比大多数", "这个角度很新颖", "这个问题问得好",
    "这是顶刊作者的素养", "让我们一起", "我们可以共同", "你已经看穿了",
]

TIER5_WORDS = [
    "数据告诉我们", "问题变成了", "决策浮现了", "体现了", "体现在", "反映了", "彰显了",
    "深刻揭示", "至关重要", "不可或缺", "充满活力", "错综复杂",
    "赋能", "抓手", "闭环", "底层逻辑", "打法", "颗粒度",
    "serves as", "stands as", "crucial", "pivotal", "landscape", "delve",
    "underscore", "showcase", "testament", "tapestry", "vibrant", "profound",
    "groundbreaking", "leverage", "synergy", "paradigm shift", "game-changer",
]

TIER5_PATTERNS = [
    re.compile(r"可能.{0,8}(或许|大概|大致)"),
    re.compile(r"(通常来说|一般来说|通常情况下|很大程度上).{0,24}(可能|或许|大概|大致|也许|应该)"),
]

INLINE_TITLE = re.compile(r"^\s*(?:\d+[.、）]\s*)?(?:[-*]\s*)?\*\*.{1,16}\*\*\s*[:：]")

EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\uFE0F]")


def run_checks(user, answer):
    """返回 (violations, warnings)。violations 为 [(规则名, 说明)]，warnings 为提示字符串。"""
    violations = []
    warnings = []

    text_len = len(answer)
    scale = max(1, math.ceil(text_len / 300))

    identity_q = re.search(r"(你是|你是什么|你是啥)\s*?(AI|ai|人工智能|机器人|语言模型)|你是谁", user, re.I)
    steps_q = re.search(r"(怎么|如何|步骤|安装|配置|排查|修复|报错|流程|部署)", user)

    # Tier 1 协作痕迹（固定上限 1；身份询问豁免身份词）
    hits = []
    if not identity_q:
        hits += [w for w in TIER1_IDENTITY if w.lower() in answer.lower()]
    hits += [w for w in TIER1_COURTESY if w.lower() in answer.lower()]
    hits += HOPE_PATTERN.findall(answer)
    if len(hits) > 1:
        violations.append(("Tier1 协作痕迹", "{} 处（上限 1）：{}".format(len(hits), hits[:5])))

    # Tier 2 讲义腔（固定上限 1；步骤语义豁免）
    if not steps_q:
        t2 = [w for w in TIER2 if w.lower() in answer.lower()]
        t2 += NEXT_PATTERN.findall(answer)
        if len(t2) > 1:
            violations.append(("Tier2 讲义腔", "{} 处（上限 1）：{}".format(len(t2), t2[:5])))

    # 路标词（密度折算）
    sp = [w for w in SIGNPOSTS if w.lower() in answer.lower()]
    if len(sp) > scale * 2:
        violations.append(("路标词", "{} 处（上限 {}）：{}".format(len(sp), scale * 2, sp[:5])))

    # 破折号 / 感叹号（密度折算）
    dash = sum(1 for ch in answer if ch in "—–")
    if dash > scale * 2:
        violations.append(("破折号", "{} 个（上限 {}）".format(dash, scale * 2)))
    excl = sum(1 for ch in answer if ch in "！!")
    if excl > scale * 3:
        violations.append(("感叹号", "{} 个（上限 {}）".format(excl, scale * 3)))

    # Tier 3 结构性表演（命中即违规）
    for pat in TIER3_PATTERNS:
        m = pat.search(answer)
        if m:
            violations.append(("Tier3 结构性表演", "命中：{}".format(m.group(0)[:24])))
            break

    # Tier 4 评判越界（命中即违规）
    t4 = [w for w in TIER4 if w in answer]
    if t4:
        violations.append(("Tier4 评判越界", "命中：{}".format(t4[:3])))

    # Tier 5 语言痕迹（命中即违规）
    t5 = [w for w in TIER5_WORDS if w.lower() in answer.lower()]
    t5 += [m.group(0) for p in TIER5_PATTERNS for m in p.finditer(answer)]
    if t5:
        violations.append(("Tier5 语言痕迹", "命中：{}".format(t5[:3])))

    # Tier 6 视觉标记
    for para in re.split(r"\n\s*\n", answer):
        if para.count("**") > 2:  # 每段最多 1 处加粗 = 2 个星号
            violations.append(("Tier6 粗体滥用", "单段超过 1 处加粗"))
            break
    for line in answer.splitlines():
        if INLINE_TITLE.search(line):
            violations.append(("Tier6 内联标题列表", line.strip()[:24]))
            break
    if EMOJI_RE.search(answer):
        violations.append(("Tier6 表情符号", "包含 emoji"))

    # 三点并列提示（非违规，需按三点判据人工确认）
    numbered = [l for l in answer.splitlines() if re.match(r"^\s*\d+[.、）]\s", l)]
    if len(numbered) == 3:
        warnings.append("三点并列：请人工确认是内容所需（判据见 full-guide Tier 3）")

    return violations, warnings


def format_self_check():
    errors = []
    for rel in ["SKILL.md", "templates/system-prompt-standard.txt", "templates/system-prompt-lite.txt"]:
        p = ROOT / rel
        text = p.read_text(encoding="utf-8")
        if EMOJI_RE.search(text):
            errors.append("{} 含 emoji".format(rel))
        if "**" in text:
            errors.append("{} 含加粗标记".format(rel))
    return errors


def main():
    cases_file = ROOT / "tests" / "cases.json"
    data = json.loads(cases_file.read_text(encoding="utf-8"))
    failures = 0
    print("共 {} 条用例".format(len(data["cases"])))
    print()
    for c in data["cases"]:
        v, w = run_checks(c["user"], c["answer"])
        ok = (not v) if c["expect"] == "pass" else bool(v)
        if not ok:
            failures += 1
        print("[{}] {}（期望 {}）".format("PASS" if ok else "FAIL", c["id"], c["expect"]))
        for name, msg in v:
            print("      违规 {}: {}".format(name, msg))
        for msg in w:
            print("      提示 {}".format(msg))
    print()
    fmt = format_self_check()
    if fmt:
        failures += len(fmt)
        for e in fmt:
            print("[FAIL] 格式自检 {}".format(e))
    else:
        print("[PASS] 格式自检（SKILL.md 与 templates 无 emoji/加粗）")
    print()
    print("全绿" if failures == 0 else "{} 项失败".format(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
