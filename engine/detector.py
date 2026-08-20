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
    re.compile(r"(?:通常来说|一般来说|通常情况下|很大程度上).{0,10}(?:可能|或许|大概|大致|也许|应该)"),
]

INLINE_TITLE = re.compile(r"^\s*(?:\d+[.、）]\s*)?(?:[-*]\s*)?\*\*.{1,16}\*\*\s*[:：]")
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\uFE0F]")
STEP_MARKERS = ["首先", "其次", "最后", "接着", "然后"]

import re as _re_core
from pathlib import Path as _Path_core
_CORE_RULES_CACHE = None
def _load_article_thresholds():
    global _CORE_RULES_CACHE
    if _CORE_RULES_CACHE is not None:
        return _CORE_RULES_CACHE
    try:
        t = (_Path_core(__file__).resolve().parent.parent / "core" / "rules.yaml").read_text(encoding="utf-8")
        dens = float(_re_core.search(r"density_threshold:\s*([0-9.]+)", t).group(1)) if _re_core.search(r"density_threshold:\s*([0-9.]+)", t) else 0.15
        cv = float(_re_core.search(r"cv_threshold:\s*([0-9.]+)", t).group(1)) if _re_core.search(r"cv_threshold:\s*([0-9.]+)", t) else 0.25
    except Exception:
        dens, cv = 0.15, 0.25
    _CORE_RULES_CACHE = (dens, cv)
    return _CORE_RULES_CACHE

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
    if re.search(r"论文|公文|演讲稿|营销文案", text):
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
            # 角色语句除外：命中在引号内则降为提示
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
    if EMOJI_RE.search(answer):
        violations.append(("Tier6 表情符号", "包含 emoji"))

    # 三点并列提示（非违规）
    numbered = [l for l in answer.splitlines() if re.match(r"^\s*\d+[.、）]\s", l)]
    if len(numbered) == 3:
        warnings.append("三点并列：请人工确认是内容所需（删编号仍完整则保留）")

    return violations, warnings

# ---------- article 扩展（标题语义/开头密度/段落指纹） ----------

ARTICLE_VAGUE_PHRASES = ["的那些事","那些事","深度好文","完全指南","科普一下","必须知道","everything you need to know","comprehensive guide","things you should know"]
ARTICLE_VAGUE_RE = __import__('re').compile(r"(三|四|五|六|七)(?:个|大)?(?:核心|主要|关键|重要)?(?:维度|趋势|要点|方面|层次|角度)")
ARTICLE_VERBS = ["是","有","做","提","改","修","查","跑","崩","涨","用","写","追","发现","解决","优化","压","选","装","启动","排查","建","别","少","变","从","到","起","崩了","分析","告诉","建议","用"]
ARTICLE_OPENING_BANNED = [__import__('re').compile(p) for p in [r"在当今", r"随着", r"的背景下", r"众所周知", r"你有没有想过", r"你是否曾", r"为什么.*总是"]]
ARTICLE_CLOSE_PATS = [__import__('re').compile(p) for p in [r"让我们", r"共同探索|共同努力|共同成长", r"一起成长", r"携手|并肩", r"未来可期", r"展望未来", r"关于这个问题.*我想说的"]]
ARTICLE_HOOKS = [__import__('re').compile(p) for p in [r"你有没有想过", r"你知道吗", r"为什么.*(?:总是|就|偏)?\s*.*\?"]]

def _title_is_vague(title: str):
    # 纯英文标题仅靠短语/模式判，不走中文语义
    import re as _re2
    if _re2.search(r"[A-Za-z]{3,}", title) and not _re2.search(r"[\u4e00-\u9fff]", title):
        low2=title.lower()
        for w in ARTICLE_VAGUE_PHRASES:
            if w.lower() in low2:
                return True, w
        if ARTICLE_VAGUE_RE.search(title):
            return True, ARTICLE_VAGUE_RE.search(title).group(0)
        return False, None
    low=title.lower()
    for w in ARTICLE_VAGUE_PHRASES:
        if w.lower() in low:
            return True, w
    if ARTICLE_VAGUE_RE.search(title):
        return True, ARTICLE_VAGUE_RE.search(title).group(0)
    has_verb = any(v in title for v in ARTICLE_VERBS)
    has_scene = bool(__import__('re').search(r"\d|月|天|秒|我|你|项目|线上|容器|查询", title))
    if not has_verb and not has_scene:
        if len(title.strip())>4:
            return True, "无动词无场景"
    return False, None

def _opening_density(head: str):
    if not head:
        return 0.0
    import re as _re
    # 去领域化：数字 + 动词 + 实体名词（扩至通用技术实体）
    hits = len(_re.findall(r"\d+", head)) + len(_re.findall(r"是|有|做|提|改|查|跑|崩|涨|用|写|追|发现|解决|优化|压|选|装", head)) + len(_re.findall(r"项目|线上|配置|查询|索引|服务|接口|模型|数据|容器|权限|端口|镜像|查询", head))
    return hits / max(1, len(head))

def article_check(title: str, body: str, fiction: bool = False):
    violations, warnings = run_checks(title + " " + body, body)
    # fiction 触发：仅 fiction=True 时才做感官化等额外提示（默认关闭，避免污染主链）
    if fiction:
        # 精确数字感官化提示（仅提示，不计违规；主链不进）
        import re as _re_fic
        m_precise = _re_fic.search(r"\d+\s*(分钟|小时|天|米|厘米|度|个|公里)", body)
        if m_precise:
            warnings.append(f"fiction提示：精确数字可感官化（例：{m_precise.group(0)}→过了一会儿/一臂之遥）；技术文请忽略")
    vague, why = _title_is_vague(title)
    if vague:
        if why == "无动词无场景":
            warnings.append(f"标题建议：加一个动词或具体场景（例：关于X的那些事→我用3月把X提了10倍）：{title}")
        else:
            violations.append(("标题空泛", f"命中：{why}"))
    head = body[:100]
    hit_open = None
    for pat in ARTICLE_OPENING_BANNED:
        if pat.search(head):
            hit_open = pat.pattern[:16]
            break
    if hit_open:
        DENS_THR,_ = _load_article_thresholds()
        dens = _opening_density(head)
        if dens < DENS_THR:
            violations.append(("空泛引入", f"开头命中：{hit_open} 密度{dens:.2f}<{DENS_THR:.2f}"))
        else:
            warnings.append(f"开头命中 {hit_open} 但密度{dens:.2f}已含信息，豁免(阈值{DENS_THR:.2f})")
    hooks = [m.group(0) for pat in ARTICLE_HOOKS for m in pat.finditer(body)]
    if len(hooks) > 1:
        violations.append(("设问钩子", f"{len(hooks)}处（上限1）：{hooks[:3]}"))
    tail = body[-150:]
    for pat in ARTICLE_CLOSE_PATS:
        if pat.search(tail):
            violations.append(("强行升华结尾", f"命中：{pat.pattern[:16]}"))
            break
    paras = [p.strip() for p in __import__('re').split(r"\n\s*\n", body) if p.strip()]
    if len(paras) >= 4:
        heads = []
        for p in paras:
            first = p.split("。")[0].split("，")[0]
            heads.append(first[:4])
        for i in range(len(heads)-2):
            if heads[i]==heads[i+1]==heads[i+2]:
                warnings.append(f"段落同构：连续3段首句均为“{heads[i]}”")
                break
        lens = [len(p) for p in paras]
        mean = sum(lens)/len(lens)
        import math
        var = sum((x-mean)**2 for x in lens)/len(lens)
        std = math.sqrt(var)
        cv = std/mean if mean else 1
        _, CV_THR = _load_article_thresholds()
        if cv < CV_THR:
            warnings.append(f"段落模板化：CV={cv:.2f}<{CV_THR:.2f} 提示打破均匀")
    import re as _re
    m = ARTICLE_VAGUE_RE.search(body)
    if m:
        numbered = [l for l in body.splitlines() if _re.match(r"^\s*\d+[.、）]\s", l)]
        if len(numbered) >= 3:
            lens = [len(l) for l in numbered[:3]]
            mean = sum(lens)/len(lens)
            var = sum((x-mean)**2 for x in lens)/len(lens)
            struct = [bool(_re.search(r"\*\*[^*]+\*\*\s*[:：]", l) or _re.search(r"[^：:]+[:：]\s*\S", l)) for l in numbered[:3]]
            # 方差<400 + 结构一致：从违规降为提示，保护文笔（疑似凑结构）
            if var < 400 and all(struct):
                warnings.append(f"三点并列疑似凑结构：{m.group(0)} 方差{var:.0f} 结构一致 → 试试删编号读一遍，删后仍完整则保留")
            else:
                warnings.append("三点并列：请人工确认是内容所需（删编号仍完整则保留）")
    # ---------- 新增文章维度（方案 1.2 A1-A6，低成本正则） ----------
    # A1 过渡句模板
    trans_pats = [r"说到.{1,10}(?:就不得不|不得不|自然要|就要)", r"提到.{1,10}(?:自然|就不得不|不能不)", r"谈到.{1,10}(?:我们|就需要|还需要)", r"那么.{0,20}(?:到底|究竟).{0,10}(?:呢|？)", r"接下来.{0,6}(?:让我们|我们来)", r"having said that", r"with that in mind", r"speaking of which"]
    trans_hits = []
    for pat in trans_pats:
        trans_hits.extend(re.findall(pat, body, flags=re.I))
    if trans_hits:
        violations.append(("过渡句模板", f"命中：{trans_hits[0][:24]} — 人类很少用'说到X就不得不提Y'套路"))

    # A4 虚假归因（有归因无来源）
    false_pats = [r"研究(?:表明|显示|指出|发现)", r"据.{0,6}(?:专家|学者|业内人士).{0,6}(?:介绍|表示|指出)", r"根据(?:最新|相关|一项)?(?:数据|统计|调查|报告)"]
    fa_hits = []
    for pat in false_pats:
        for m in re.finditer(pat, body):
            after = body[m.end(): m.end()+50]
            has_src = bool(re.search(r"\d{4}|大学|研究院|公司|论文|报告|调查|Stack Overflow|\d+%|\d+\.\d+%", after))
            if not has_src:
                fa_hits.append(m.group(0))
    if fa_hits:
        violations.append(("虚假归因", f"命中：{fa_hits[0]} — 无具体来源，请给论文/机构/年份或删归因"))

    # A2 段尾总结句（>2 处提示）
    tail_pats = [r"由此可见.{0,20}[。！]?$", r"因此.{0,6}(?:我们|在).{0,20}(?:需要|应该|必须)", r"这也是为什么.{0,30}[。！]?$", r"总之.{0,30}[。！]?$"]
    tail_cnt = 0
    paras_tail = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    for para in paras_tail:
        last = para.split("\n")[-1].strip().split("。")[-1]
        # 检查段尾行是否命中
        seg = para.strip().split("\n")[-1]
        for pat in tail_pats:
            if re.search(pat, seg):
                tail_cnt += 1
                break
    if tail_cnt > 2:
        warnings.append(f"段尾总结句堆砌：全文{tail_cnt}处（上限2处）— 人类不会每段都收一句结论")

    # A3 冗余复述
    redun_triggers = ["换句话说","也就是说","简单来说","换言之","说白了就是","通俗地讲","in other words","put simply"]
    for t in redun_triggers:
        if t.lower() in body.lower():
            warnings.append(f"冗余复述：命中'{t}' — 若后句重复前句意思，删复述句")
            break

    # A5 连接词密度（每500字≤4）
    connectives = ["然而","因此","不过","但是","同时","此外","另外","与此同时","尽管如此","除此之外","however","therefore","moreover","furthermore"]
    cnt_conn = sum(body.count(c) for c in connectives)
    limit_conn = max(4, int(len(body)/500*4))
    if cnt_conn > limit_conn:
        warnings.append(f"连接词密度：全文{cnt_conn}个（{len(body)}字，上限约{limit_conn}个）— 靠语义连接，不靠堆词")

    # A6 节间对称（按 ## 分节，CV<0.20）
    sections = re.split(r"\n##\s", body)
    if len(sections) >= 3:
        lens_sec = [len(s.strip()) for s in sections if len(s.strip())>50]
        if len(lens_sec) >= 3:
            mean_sec = sum(lens_sec)/len(lens_sec)
            var_sec = sum((x-mean_sec)**2 for x in lens_sec)/len(lens_sec)
            cv_sec = (var_sec**0.5)/mean_sec if mean_sec else 1
            if cv_sec < 0.20:
                warnings.append(f"节间对称：CV={cv_sec:.2f}<0.20 各节长度{lens_sec} — 人类有详有略")

        # 句长节奏：长短交替提示（仅提示，不计违规）
    try:
        import re as _re_s
        sents = [s for s in _re_s.split(r"[。！？\n]+", body) if s.strip()]
        if len(sents) >= 6:
            lens_s = [len(s) for s in sents]
            mean_s = sum(lens_s) / len(lens_s)
            var_s = sum((x - mean_s) ** 2 for x in lens_s) / len(lens_s)
            std_s = var_s ** 0.5
            cv_s = std_s / mean_s if mean_s else 1
            if cv_s < 0.30:
                warnings.append(f"节奏提示：句长较均匀 CV={cv_s:.2f}<0.30，可尝试长短交替，打破匀速")
    except Exception:
        pass
    return violations, warnings
