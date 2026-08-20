# -*- coding: utf-8 -*-
"""natural-talk 极致检测器 — Trie(词) + Regex(模式) + 密度(连续化) + 场景感知.

公开 API: run_checks(user, answer) -> (violations, warnings)
与 scripts/check.py 保持兼容，但性能与准确率极致化。
"""
import math
import re
from pathlib import Path

# 预编译硬化正则（句内边界，防回溯）
TIER3_PATTERNS = [
    re.compile(r"不是[^。\n]{0,30}(?:而是|而是说)"),
    re.compile(r"不是[^。\n]{0,40}而是要"),
    re.compile(r"不仅仅[^。\n]{0,30}(?:而是|更是)"),
    re.compile(r"不在于[^。\n]{0,30}而在于"),
    re.compile(r"与其[^。\n]{0,16}不如"),
    re.compile(r"与其说[^。\n]{0,30}不如说"),
    re.compile(r"看似[^。\n]{0,20}实则"),
    re.compile(r"表面[^。\n]{0,20}实际"),
    re.compile(r"很久[^。\n]{0,6}久到"),
    re.compile(r"很远[^。\n]{0,6}远到"),
    re.compile(r"很长[^。\n]{0,6}长到"),
    re.compile(r"很大[^。\n]{0,6}大到"),
    re.compile(r"很深[^。\n]{0,6}深到"),
    re.compile(r"真正的问题是"),
    re.compile(r"揭开面纱|遮羞布|戳穿真相|背后的真相"),
    re.compile(r"深层原因"),
]

HOPE_PATTERN = re.compile(r"希望.{0,12}(?:帮助|有用|解决|对你)")
NEXT_PATTERN = re.compile(r"接下来\s*[，,]?\s*(?:我|我们)")
HEDGE_PATTERNS = [
    re.compile(r"可能.{0,4}(?:或许|大概|大致)"),
    re.compile(r"(?:通常来说|一般来说|通常情况下).{0,10}(?:可能|或许|大概|大致|也许)"),
]

INLINE_TITLE = re.compile(r"^\s*(?:\d+[.、）]\s*)?(?:[-*]\s*)?\*\*.{1,16}\*\*\s*[:：]")
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\uFE0F]")
STEP_MARKERS = ["首先", "其次", "最后", "接着", "然后"]

# 延迟加载 Trie（避免循环导入开销）
_TRIE = None

def _get_trie():
    global _TRIE
    if _TRIE is None:
        try:
            from engine.trie import build_default_trie
            _TRIE = build_default_trie()
        except Exception:
            _TRIE = None
    return _TRIE

def _detect_scene(text):
    if re.search(r"去世|难受|焦虑|抑郁|分手", text):
        return "emotion"
    if re.search(r"论文|公文|演讲稿|营销文案|法律|声明", text):
        return "formal"
    if re.search(r"怎么.*装|步骤|先.*再|压缩分区|备份", text):
        return "tech_steps"
    return "chat"

def _lang_is_zh(text):
    zh = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[A-Za-z]+", text))
    return zh >= en

def run_checks(user, answer):
    violations = []
    warnings = []

    text_len = len(answer)
    # 连续化密度：避免 299->301 阶梯突变
    scale = max(1.0, text_len / 300.0)

    scene = _detect_scene(user + " " + answer)
    if scene == "formal":
        # 正式场景自动豁免
        return [], ["场景 formal 已豁免"]

    is_zh = _lang_is_zh(answer)
    identity_q = re.search(r"(你是|你是什么|你是啥)\s*?(AI|ai|人工智能|机器人|语言模型)|你是谁", user, re.I)

    # --- Trie 层：T1/T2 词表 ---
    trie = _get_trie()
    t1_hits = []
    t2_hits = []
    signpost_hits = []
    if trie is not None:
        for pos, word, tier, label in trie.scan(answer):
            if tier == "T1":
                if "作为AI" in word or "训练" in word or "as an ai" in word.lower():
                    if identity_q:
                        continue
                t1_hits.append(word)
            elif tier == "T2":
                t2_hits.append(word)
            elif tier == "SIGNPOST":
                # 语言自适应：中文回答只计中文路标
                if is_zh and word.isascii():
                    continue
                if not is_zh and not word.isascii():
                    continue
                signpost_hits.append(word)
    else:
        # 回退：无Trie时跳过
        pass

    # 补充正则层：HOPE/NEXT
    t1_hits.extend(HOPE_PATTERN.findall(answer))
    # NEXT_PATTERN 返回匹配串
    t2_hits.extend(NEXT_PATTERN.findall(answer))

    # Tier1 协作痕迹：固定上限 1
    if len(t1_hits) > 1:
        violations.append(("Tier1 协作痕迹", f"{len(t1_hits)} 处（上限1）：{t1_hits[:5]}"))

    # Tier2 讲义腔：固定上限 1，步骤序列整体计1
    seq = [w for w in STEP_MARKERS if w in answer]
    if len(seq) >= 2 and scene != "tech_steps":
        t2_hits.append(f"步骤序列（{'、'.join(seq)}）")
    # tech_steps 场景豁免步骤序列
    if len(t2_hits) > 1:
        violations.append(("Tier2 讲义腔", f"{len(t2_hits)} 处（上限1）：{t2_hits[:5]}"))

    # 路标词：连续化预算
    budget_sign = max(2, math.ceil(scale * 2))
    if len(signpost_hits) > budget_sign:
        violations.append(("路标词", f"{len(signpost_hits)} 处（上限{budget_sign}）：{signpost_hits[:5]}"))

    # 破折号/感叹号：连续化
    dash = sum(1 for ch in answer if ch in "—–")
    budget_dash = max(2, math.ceil(scale * 2))
    if dash > budget_dash:
        violations.append(("破折号", f"{dash} 个（上限{budget_dash}）"))
    excl = sum(1 for ch in answer if ch in "！!")
    budget_excl = max(3, math.ceil(scale * 3))
    if excl > budget_excl:
        violations.append(("感叹号", f"{excl} 个（上限{budget_excl}）"))

    # Tier3 结构性表演：命中即违规（铁律：删否定留肯定，直接说Y；角色语句除外）
    for pat in TIER3_PATTERNS:
        m = pat.search(answer)
        if m:
            hit = m.group(0)[:24]
            # 角色语句除外：命中在引号内则降为提示（轻量位置判断）
            is_quoted = False
            try:
                idx = answer.find(hit[:6])
                if idx != -1:
                    left = -1
                    for q in ['"', '"', "'", '“', '”']:
                        p = answer.rfind(q, 0, idx)
                        if p > left:
                            left = p
                    right = -1
                    for q in ['"', '"', "'", '“', '”']:
                        p = answer.find(q, idx + len(hit[:6]))
                        if p != -1 and (right == -1 or p < right):
                            right = p
                    if left != -1 and right != -1 and left < idx < right:
                        is_quoted = True
            except Exception:
                is_quoted = False
            if is_quoted:
                warnings.append(f"Tier3 疑似（引号内，角色语句豁免）：{hit}")
            else:
                violations.append(("Tier3 结构性表演", f"命中：{hit} → 建议：删否定留肯定，直接说Y（例：不是优化而是重构→重构）"))
            break

    # 动作紧凑：一个动作一句话（仅提示，不计违规）
    if re.search(r"抬起.*(伸出|伸手).*?(然后|接着|再).*?按下|先迈.*再迈.*走向", answer):
        warnings.append("动作拆解：连续动作可压为一句（例：抬起手然后伸出食指接着按下按钮→伸手按下按钮）；仅紧张/暧昧/恐惧/受伤需慢放时可拆解")
    elif re.search(r"，\s*然后|，\s*接着|，\s*再", answer) and len(re.findall(r"然后|接着", answer)) >= 2:
        warnings.append("动作拆解提示：连续动词链可压为一句，一动作一句话")

    # Tier4 评判越界（场景 emotion 豁免部分）
    tier4_words = ["我完全理解","我懂你的","你不是敏感","你问到了","你有很强的","你的观察力很敏锐","你比大多数","这个角度很新颖","你已经看穿了","让我们一起","我们可以共同"]
    if scene != "emotion":
        t4 = [w for w in tier4_words if w in answer]
        if t4:
            violations.append(("Tier4 评判越界", f"命中：{t4[:3]}"))
    else:
        # emotion 场景：允许温和共情，但仍拦截表演式共情
        t4s = [w for w in ["我完全理解","你不是敏感","你有很强的","你比大多数","让我们一起","我们可以共同"] if w in answer]
        if t4s:
            violations.append(("Tier4 评判越界", f"命中：{t4s[:3]}"))

    # Tier5 语言痕迹
    tier5_words = ["数据告诉我们","问题变成了","决策浮现了","体现了","体现在","反映了","彰显了","深刻揭示","至关重要","不可或缺","充满活力","错综复杂","赋能","抓手","闭环","底层逻辑","打法","颗粒度","serves as","stands as","testament","tapestry","groundbreaking","leverage","synergy","paradigm shift","game-changer"]
    t5 = [w for w in tier5_words if w.lower() in answer.lower()]
    t5 += [m.group(0) for p in HEDGE_PATTERNS for m in p.finditer(answer)]
    if t5:
        violations.append(("Tier5 语言痕迹", f"命中：{t5[:3]}"))
    # 高频词密度：连续化
    density_words = ["crucial","pivotal","landscape","delve","underscore","showcase","vibrant","profound"]
    # 词形归一：去 ly/ing/ed
    import re as _re
    norm_ans = _re.sub(r"(ly|ing|ed)\b", "", answer.lower())
    dense = []
    for w in density_words:
        cnt = norm_ans.count(w)
        dense.extend([w]*cnt)
    budget_dense = max(1, math.ceil(scale))
    if len(dense) > budget_dense:
        violations.append(("Tier5 高频词密度", f"{len(dense)} 处（上限{budget_dense}）：{dense[:5]}"))

    # Tier6 视觉标记
    for para in re.split(r"\n\s*\n", answer):
        if para.count("**") > 2:
            violations.append(("Tier6 粗体滥用", "单段超过1处加粗"))
            break
    for line in answer.splitlines():
        if INLINE_TITLE.search(line):
            violations.append(("Tier6 内联标题列表", line.strip()[:24]))
            break
    # emoji：用户明确要求时豁免
    if EMOJI_RE.search(answer):
        if not re.search(r"emoji|表情|颜文字", user, re.I):
            violations.append(("Tier6 表情符号", "包含 emoji"))
        else:
            warnings.append("emoji 已按用户要求豁免")

    # 一致性：你/您混用（低级，提示性）
    if "你" in answer and "您" in answer:
        # 允许引号内除外，简单计数
        if answer.count("你") >= 1 and answer.count("您") >= 1:
            warnings.append("一致性：同一回复混用'你'和'您'，建议统一称呼")

    # 节奏检测：句长方差（仅提示）
    try:
        sents = [s.strip() for s in re.split(r"[。！？\n]+", answer) if len(s.strip())>5]
        if len(sents) >= 5:
            lens = [len(s) for s in sents]
            mean = sum(lens)/len(lens)
            var = sum((l-mean)**2 for l in lens)/len(lens)
            if var < 50:
                warnings.append(f"节奏：连续{len(sents)}句长度相近（方差{var:.1f}），建议长短交替")
    except Exception:
        pass

    # 三点并列提示（非违规）
    numbered = [l for l in answer.splitlines() if re.match(r"^\s*\d+[.、）]\s", l)]
    if len(numbered) == 3:
        warnings.append("三点并列：请人工确认是内容所需（删编号仍完整则保留）")

    return violations, warnings
