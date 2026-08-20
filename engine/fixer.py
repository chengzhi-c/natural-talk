# -*- coding: utf-8 -*-
"""自动修复 — 对 Tier1-6 的确定性改写，无需 LLM.

公开 API: fix(text) -> (fixed_text, edits)
"""
import re

EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\uFE0F]")

REPLACEMENTS = [
    (re.compile(r"作为AI[^。\n]*[，。]?"), ""),
    (re.compile(r"希望[^。\n]{0,12}(?:帮助|有用)[^。\n]*[。！]?"), ""),
    (re.compile(r"好问题[！!]?\s*"), ""),
    (re.compile(r"让我来[^。\n]*[，。]?"), ""),
    (re.compile(r"值得注意的是[，,]?\s*"), ""),
    (re.compile(r"综上所述[，,]?\s*"), ""),
    (re.compile(r"我完全理解[^。\n]*[。]?"), "听起来"),
    # 铁律：不是…而是 → 直接留Y（删否定部分）；与其…不如… 同理
    (re.compile(r"不是[^。\n]{0,30}而是\s*"), ""),
    (re.compile(r"与其[^。\n]{0,16}不如\s*(?:说\s*)?"), ""),
    (re.compile(r"很久[^。\n]{0,6}久到[^。\n]*[，。]?"), "很久"),
]

def fix(text):
    edits = []
    out = text
    for pat, repl in REPLACEMENTS:
        new, n = pat.subn(repl, out)
        if n:
            edits.append((pat.pattern[:24], n))
            out = new
    # 破折号 -> 逗号
    if "—" in out or "–" in out:
        cnt = out.count("—") + out.count("–")
        out = out.replace("—", "，").replace("–", "，")
        edits.append(("dash->，", cnt))
    # 粗体滥用：每段超过1处则去加粗
    parts = re.split(r"(\n\s*\n)", out)
    for i, p in enumerate(parts):
        if p.count("**") > 2:
            parts[i] = p.replace("**", "")
            edits.append(("bold", 1))
    out = "".join(parts)
    # emoji：仅当原文含 emoji 时移除（保留用户显式要求的）
    # 默认不自动删，由检测提示
    return out, edits

if __name__ == "__main__":
    s = "作为AI，我很乐意帮助你。值得注意的是，这个方案——至关重要。"
    print(fix(s))
