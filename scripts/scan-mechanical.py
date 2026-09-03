"""机械规则确定性扫描器：确定命中与语境复核候选。

定位：生成候选命中清单，供 LLM 复核语境后决定是否改写。
脚本只报触发标记，不做自动改写——语境判断（如 B4 提示语是否承接上文、
B11 是否法规条目）仍由模型或人完成。依据 SKILL.md 执行要求
"低成本检查一律实搜不凭印象"，本脚本把"实搜"固化下来。

覆盖规则分两级：
  FIX 级（高精度，命中基本即可改）：
  B4  冒号滥用：提示语引出（一句话总结：/核心是：……）＋空转句引列表
  B6  序数词通篇编号小标题（连续 ≥3 个才报）
  B10 起手式：说白了 / 说穿了 / 先说结论（句首位置）
  B12 空降宏观开场：在当今 / 众所周知（句首位置；是否含具体背景信息语义判断）
  REVIEW 级（只报候选，必须复核语境）：
  B11 顿号罗列过密：一个分句内 ≥2 个顿号串 ≥3 项并列（法规条目、配置项、
      技术操作枚举须保留，语义判断在模型——降级 REVIEW 防误授权）
  B1  翻案腔：句中含"而是/其实/恰恰"——被否定的观点是否存在须读上下文
  B3  段首零回指评论：非首段以评论语开头且整句无"这/那/其/此/上面"
  B5  叙述中的破折号：逐处核对是否只是解释、列举、因果或同位补充
  F7  fiction 中的"很久……久到……"等空泛回环候选
  gen 模式追加 REVIEW 候选（既有规则补机械触发，改写判断在模型）：
  B9  装饰性喻体：明喻标记＋"一＋量词"引出的铺陈喻体
  C2  结尾拔高、C4 hedging 叠加、C5 宏观开场、C6 空泛气氛总结
  D2  服务腔开场收尾（句首）、D3 免责包装、D4 万能收尾、
  D5  元话语空预告、D6 模糊归因

白名单（绝对原则，完全豁免）：围栏代码块、行内代码、YAML frontmatter、
表格行、引用块（> 起首）、URL、Markdown 列表内部（B11）。

输出附注：全文无空行分段时 B3 无从执行，打印一行提示，不改退出码。
文件解码按 utf-8-sig（兼容 BOM）→ gbk 依序尝试，均失败打印跳过说明并继续。

用法：
  python scripts/scan-mechanical.py <文件> [文件...] [--mode prose|fiction|gen]
  python scripts/scan-mechanical.py -          # 读 stdin
退出码：0 无命中，1 有命中，2 用法错误。
自测：python scripts/test-scan-mechanical.py

模式（对应 SKILL.md 清理 / fiction 清理 / 生成自查三种流程）：
  prose（默认）  清理全量规则
  fiction        报 fiction 清理带入集内的 B6(FIX)、B1/B5/F7(REVIEW)；
                 B3/B4/B10/B11 的倍率来自非虚构论述文体对照，fiction 不带入，
                 一律不报（对小说照报即越界误伤）
  gen            生成期自查：FIX 同 prose（B 层生成清理共用）；
                 REVIEW 增 B1/B3/B5/B9/C2/C4/C5/C6/D2–D6（D/C 层机械候选），
                 全部只报候选，复核后决定改留
"""
import argparse
import re
import sys
from pathlib import Path

# ---------- 触发标记 ----------

# B10：句首起手式
B10_WORDS = ("说白了", "说穿了", "先说结论")
# B12：句首空降宏观开场（"随着"类不进机械层，误伤具体事件句）
B12_WORDS = ("在当今", "众所周知")

# B4a：提示语＋冒号（每个词必须出现在 references/rules-text.md 的 B4 触发行，见自测断言）
B4A_PROMPTS = ("一句话总结", "核心是", "关键在于", "原因如下", "本质上")

# B1（REVIEW 级）：翻案腔候选词
B1_WORDS = ("而是", "其实", "恰恰")

# B3（REVIEW 级）：段首评论语与回指词
B3_OPENERS = ("听起来", "看起来", "值得注意的是", "更重要的是",
              "关键在于", "问题在于", "说白了")
B3_REFERENTS = ("这", "那", "其", "此", "上面")

# B6：编号小标题（一、二、三 / 第一、第二）
_HEADING_MD = re.compile(r"^(#{1,6})\s+(.+)$")
_HEADING_BOLD = re.compile(r"^\*\*(.+)\*\*\s*$")
_NUM_PREFIX = re.compile(r"^(?:[一二三四五六七八九十]+、|第[一二三四五六七八九十0-9]+[、，,\s])")

# 列表行（B4b 判定下文是否列表；B11 对列表内部豁免）
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.、)）])\s")
_LIST_CONTINUATION = re.compile(r"^(?:\t| {2,})\S")

# 分句切分（B11 按分句判顿号密度；B10 按句判句首）
_CLAUSE_SPLIT = re.compile(r"[，。；：！？\n]")
_SENT_SPLIT = re.compile(r"[。！？；\n]")

_URL = re.compile(r"https?://\S+|www\.\S+")
_INLINE_CODE = re.compile(r"(?P<fence>`+).*?(?P=fence)")
_INLINE_QUOTES = (
    re.compile(r"“[^”]*”"),
    re.compile(r"‘[^’]*’"),
    re.compile(r"「[^」]*」"),
    re.compile(r"『[^』]*』"),
    re.compile(r'"[^"\n]*"'),
)
_TABLE_SEPARATOR = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_FENCE_OPEN = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_FENCE_CLOSE = re.compile(r"^\s{0,3}(`+|~+)\s*$")
_F7_LOOP = re.compile(
    r"(?:很久[，,、；;。.!！？?…\s]{0,4}久到|"
    r"安静[，,、；;。.!！？?…\s]{0,4}静[到得]|"
    r"寂静[，,、；;。.!！？?…\s]{0,4}静[到得]|"
    r"沉默[，,、；;。.!！？?…\s]{0,4}沉默到|"
    r"(?P<degree>冷|黑|痛|累|远|慢|快)"
    r"[，,、；;。.!！？?…\s]{0,4}(?P=degree)[到得])")
_TEXT_SUFFIXES = {".md", ".markdown", ".txt"}

# ---------- gen 模式触发标记（既有规则的机械候选，全部 REVIEW 级） ----------

# B9 装饰性喻体：明喻标记＋"一＋量词"引出的铺陈喻体（乐团/导师/灯塔/明月…）。
# "一个"不报：解释性比喻的常规量词（缓存就像一个仓库）。
_B9_SIMILE = re.compile(
    r"(?:就像|如同|宛如|仿佛|犹如|恰似|像)[^，。；！？]{0,6}一"
    r"[位支场座轮缕双只股颗盏片]")

# C2 结尾拔高：模板化升华与乐观收尾
_C2_GRAND = re.compile(
    r"真正重要的是|从更大的角度看|未来可期|"
    r"迈出了?(?:重要|关键)的一步|开启了?(?:全新|新的?)篇章|"
    r"这不仅[^。]{0,20}更(?:是|关乎|能)")

# C4 hedging 叠加：两个不确定标记之间无句读
_C4_HEDGE = re.compile(
    r"(?:可能|或许|也许|大概|在一定程度上|在某种程度上)[^，。；]{0,10}"
    r"(?:可能|或许|也许|大概|在一定程度上|在某种程度上)")

# C5 空降宏观开场
_C5_MACRO = re.compile(
    r"在(?:当今|当前)[^，。]{0,16}(?:时代|背景|环境)下?|"
    r"随着[^，。]{0,16}不断(?:发展|演变|进步)")

# C6 空泛气氛总结
_C6_ATMOS = re.compile(
    r"(?:声音|寂静|沉默)[^。]{0,8}(?:填满|充满|弥漫)|"
    r"静[得有][^。]{0,6}重量|世界退回[^。]{0,4}壳")

# D2 服务腔开场收尾（句首匹配）
_D2_OPENERS = ("好问题", "问得好", "这是个好问题", "这真是个好问题",
               "感谢提问", "感谢你的提问", "希望这", "希望对你", "希望对您",
               "如有疑问", "如有任何问题", "欢迎随时")

# D3 免责包装
_D3_DISCLAIM = re.compile(
    r"作为一?[个名]?语言模型|根据我的训练数据|我的知识截止|训练数据截止")

# D4 万能收尾
_D4_BALANCE = re.compile(
    r"关键在于找到平衡|要结合实际情况|没有绝对的对错")

# D5 元话语空预告（含具体动作的真步骤不在此 pattern 内，复核区分）
_D5_META = re.compile(
    r"下面我(?:将|会|就)[^，。]{0,16}(?:展开|介绍|说明|分析)|"
    r"让我们(?:先|一起|来)?[^，。]{0,12}"
    r"(?:理解|看看|回顾|进入|梳理|探讨|认识|了解|明白)")

# D6 模糊归因（有可指认来源的不报，复核区分）
_D6_ATTRIB = re.compile(
    r"(?:有|相关|多项|大量)研究[^，。；]{0,4}(?:表明|显示|指出)|"
    r"(?:业内|行业|专家|观察者)[^，。；]{0,4}(?:普遍)?(?:认为|指出|表示)|"
    r"(?:不少|很多|部分)(?:用户|人)[^，。；]{0,4}(?:反馈|认为|表示)")

# 各模式的报告集（见模块 docstring"模式"节；B11 需语义判断，prose/gen 均 REVIEW）
FIX_RULES = {"prose": ("B4", "B6", "B10"), "fiction": ("B6",),
             "gen": ("B4", "B6", "B10")}
REVIEW_RULES = {
    "prose": ("B1", "B3", "B5", "B11", "B12"),
    "fiction": ("B1", "B5", "F7"),
    "gen": ("B1", "B3", "B5", "B9", "B11", "C2", "C4", "C5", "C6",
            "D2", "D3", "D4", "D5", "D6"),
}


def _mask_line(line):
    """行内代码、URL 与行内引文替换为等长占位。"""
    def _blank(m):
        return " " * len(m.group(0))
    line = _INLINE_CODE.sub(_blank, line)
    line = _URL.sub(_blank, line)
    for pattern in _INLINE_QUOTES:
        line = pattern.sub(_blank, line)
    return line


def _table_lines(lines):
    """返回 Markdown 表格占用的零基行号，兼容无前导竖线写法。"""
    result = set()
    for idx, raw in enumerate(lines):
        if not _TABLE_SEPARATOR.match(raw):
            continue
        result.add(idx)
        if idx and "|" in lines[idx - 1]:
            result.add(idx - 1)
        pos = idx + 1
        while pos < len(lines) and lines[pos].strip() and "|" in lines[pos]:
            result.add(pos)
            pos += 1
    return result


def _list_content_lines(lines):
    """返回 Markdown 列表项及其缩进续行的零基行号。"""
    result = set()
    in_item = False
    for idx, raw in enumerate(lines):
        if _LIST_ITEM.match(raw):
            result.add(idx)
            in_item = True
            continue
        if not raw.strip():
            continue
        if in_item and _LIST_CONTINUATION.match(raw):
            result.add(idx)
            continue
        in_item = False
    return result


def _read_text(path):
    """utf-8-sig 兼容 BOM；GBK 回退；均失败返回 None。"""
    for enc in ("utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return None


def _expand_target(target):
    """把单文件或目录展开为稳定排序的文本文件列表。"""
    path = Path(target)
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(
            (item for item in path.rglob("*")
             if item.is_file() and item.suffix.lower() in _TEXT_SUFFIXES),
            key=lambda item: str(item).lower(),
        )
    return None


def _iter_scannable_lines(text):
    """逐行产出 (行号, 原文, 屏蔽后文本)，跳过白名单区。"""
    fence_char = None
    fence_len = 0
    in_yaml = False
    lines = text.splitlines()
    table_lines = _table_lines(lines)
    for idx, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if idx == 1 and stripped == "---":
            in_yaml = True
            continue
        if in_yaml:
            if stripped == "---":
                in_yaml = False
            continue
        if fence_char is not None:
            close = _FENCE_CLOSE.match(raw)
            if (close and close.group(1)[0] == fence_char
                    and len(close.group(1)) >= fence_len):
                fence_char = None
                fence_len = 0
            continue
        opened = _FENCE_OPEN.match(raw)
        if opened:
            fence = opened.group(1)
            fence_char = fence[0]
            fence_len = len(fence)
            continue
        if idx - 1 in table_lines or stripped.startswith("|"):  # 表格行豁免
            continue
        if stripped.startswith(">"):  # 引用块与引文豁免：引的是他人原文
            continue
        yield idx, raw, _mask_line(raw)


def _heading_info(masked):
    """返回 (层级, 小标题文字)，非小标题返回 None。"""
    m = _HEADING_MD.match(masked.strip())
    if m:
        return len(m.group(1)), m.group(2).strip()
    m = _HEADING_BOLD.match(masked.strip())
    if m:
        return 0, m.group(1).strip()
    return None


def _is_heading(masked):
    info = _heading_info(masked)
    return info[1] if info else None


def scan(text, mode="prose"):
    """返回命中列表：dict(line, rule, tier, snippet, note)。

    tier=FIX 高精度可据以改写；tier=REVIEW 只是候选，须读上下文复核。
    mode 按清理流程限定报告集，见模块 docstring。
    """
    hits = []
    fix_on = set(FIX_RULES[mode])
    review_on = set(REVIEW_RULES[mode])
    scannable = list(_iter_scannable_lines(text))
    list_lines = _list_content_lines(text.splitlines())

    # ---- B6：连续编号小标题，普通标题会打断编号序列 ----
    heading_stream = []
    for idx, raw, masked in scannable:
        info = _heading_info(masked)
        if info:
            level, title = info
            heading_stream.append((idx, level, title, bool(_NUM_PREFIX.match(title))))
    numbered_runs = []
    run = []
    run_level = None
    for idx, level, title, is_numbered in heading_stream:
        if is_numbered:
            if run and level != run_level:
                if len(run) >= 3:
                    numbered_runs.append(run)
                run = []
            run.append((idx, title))
            run_level = level
        else:
            if len(run) >= 3:
                numbered_runs.append(run)
            run = []
            run_level = None
    if len(run) >= 3:
        numbered_runs.append(run)
    if "B6" in fix_on:
        for numbered in numbered_runs:
            for idx, title in numbered:
                hits.append(dict(line=idx, rule="B6", tier="FIX", snippet=title,
                                 note=f"连续编号小标题共 {len(numbered)} 个（≥3 触发）"))

    # ---- B3（REVIEW）：非首段段首零回指评论 ----
    if "B3" in review_on:
        para_no = -1
        prev_blank = True
        for idx, raw, masked in scannable:
            stripped = masked.strip()
            if not stripped:
                prev_blank = True
                continue
            if prev_blank:
                para_no += 1
                first_line = stripped
                if para_no >= 1:
                    content = first_line.lstrip(">*# ")
                    for op in B3_OPENERS:
                        if content.startswith(op):
                            sentence = _SENT_SPLIT.split(content)[0]
                            if not any(r in sentence for r in B3_REFERENTS):
                                hits.append(dict(
                                    line=idx, rule="B3", tier="REVIEW",
                                    snippet=sentence[:40],
                                    note="段首评论无明确承接：恢复具体对象，或删掉空评论；"
                                         "不得机械补一个‘这’字"))
                            break
            prev_blank = False

    for pos, (idx, raw, masked) in enumerate(scannable):
        stripped = masked.strip()
        if not stripped:
            continue
        is_list_line = idx - 1 in list_lines
        heading = _is_heading(masked)

        # ---- B10：句首起手式 ----
        if "B10" in fix_on:
            for sent in _SENT_SPLIT.split(masked):
                s = sent.strip().lstrip(">*#- ")
                for w in B10_WORDS:
                    if s.startswith(w):
                        hits.append(dict(line=idx, rule="B10", tier="FIX", snippet=w,
                                         note="句首起手式，删后直接给判断"))
                        break

        # ---- B12（REVIEW）：句首空降宏观开场 ----
        if "B12" in review_on and not heading:
            for sent in _SENT_SPLIT.split(masked):
                s = sent.strip().lstrip(">*#- ")
                for w in B12_WORDS:
                    if s.startswith(w):
                        hits.append(dict(line=idx, rule="B12", tier="REVIEW", snippet=w,
                                         note="句首宏观开场候选：核对句内是否含具体背景信息"))
                        break

        # ---- B1（REVIEW）：翻案腔候选 ----
        if "B1" in review_on and not heading:
            for sent in _SENT_SPLIT.split(masked):
                for w in B1_WORDS:
                    if w in sent:
                        hits.append(dict(line=idx, rule="B1", tier="REVIEW",
                                         snippet=sent.strip()[:40],
                                         note=f"含“{w}”：核对被否定的观点是否真实存在，"
                                              f"不存在删否定留肯定；角色台词内不改"))
                        break

        # ---- B5（REVIEW）：叙述破折号逐处复核用途 ----
        if "B5" in review_on and "—" in masked:
            hits.append(dict(
                line=idx, rule="B5", tier="REVIEW", snippet=stripped[:40],
                note="叙述破折号：若右侧只是解释、列举、同位、原因、结果或补充，"
                     "保留内容并改用完整句或常规标点；台词中断与未完不改"))

        # ---- F7（REVIEW）：fiction 空泛程度回环 ----
        if "F7" in review_on:
            match = _F7_LOOP.search(masked)
            if match:
                hits.append(dict(
                    line=idx, rule="F7", tier="REVIEW", snippet=match.group(0),
                    note="程度回环候选：改掉‘很久，久到’等表层句式；"
                         "保留具体结果并改为直述，没有信息增量则删后半"))

        # ---- gen 层（REVIEW）：既有规则的机械候选，逐处报出 ----
        if "B9" in review_on:
            for m in _B9_SIMILE.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B9", tier="REVIEW", snippet=m.group(0),
                    note="喻体候选：喻体与本体共享具体属性、删后解释力不减即为装饰，"
                         "删掉或直说；承载解释的保留"))
        if "C2" in review_on:
            for m in _C2_GRAND.finditer(masked):
                hits.append(dict(
                    line=idx, rule="C2", tier="REVIEW", snippet=m.group(0),
                    note="拔高/乐观收尾候选：删后信息不减则删，"
                         "收尾停在具体事实或下一步"))
        if "C4" in review_on:
            m = _C4_HEDGE.search(masked)
            if m:
                hits.append(dict(
                    line=idx, rule="C4", tier="REVIEW", snippet=m.group(0),
                    note="hedging 叠加：留一个限定词或直说不知道；"
                         "单个‘可能’是诚实，不删"))
        if "C5" in review_on:
            m = _C5_MACRO.search(masked)
            if m:
                hits.append(dict(
                    line=idx, rule="C5", tier="REVIEW", snippet=m.group(0),
                    note="宏观开场候选：与论点无关的背景删掉，第一句即实质"))
        if "C6" in review_on:
            m = _C6_ATMOS.search(masked)
            if m:
                hits.append(dict(
                    line=idx, rule="C6", tier="REVIEW", snippet=m.group(0),
                    note="空泛气氛总结候选：没有新增感知、动作或结果就删，"
                         "或换成下一件可感知的事"))
        if "D2" in review_on:
            for sent in _SENT_SPLIT.split(masked):
                s = sent.strip().lstrip(">*#- ")
                for w in _D2_OPENERS:
                    if s.startswith(w):
                        hits.append(dict(
                            line=idx, rule="D2", tier="REVIEW", snippet=s[:20],
                            note="服务腔开场/收尾：首句直接给结论，"
                                 "末句停在事实、建议或边界"))
                        break
        if "D3" in review_on:
            m = _D3_DISCLAIM.search(masked)
            if m:
                hits.append(dict(
                    line=idx, rule="D3", tier="REVIEW", snippet=m.group(0),
                    note="免责包装：直接答；不确定就说不确定，不用铺垫句式"))
        if "D4" in review_on:
            for m in _D4_BALANCE.finditer(masked):
                hits.append(dict(
                    line=idx, rule="D4", tier="REVIEW", snippet=m.group(0),
                    note="万能收尾候选：问什么答什么给出倾向；"
                         "真两难写清判断条件"))
        if "D5" in review_on:
            for m in _D5_META.finditer(masked):
                hits.append(dict(
                    line=idx, rule="D5", tier="REVIEW", snippet=m.group(0),
                    note="元话语候选：空预告删；后接实际内容或真步骤的保留"))
        if "D6" in review_on:
            for m in _D6_ATTRIB.finditer(masked):
                hits.append(dict(
                    line=idx, rule="D6", tier="REVIEW", snippet=m.group(0),
                    note="模糊归因候选：有来源写来源，没来源删归因直接陈述；"
                         "不得补造来源"))

        # ---- B4a：提示语＋冒号 ----
        if "B4" in fix_on and not heading:
            for p in B4A_PROMPTS:
                for m in re.finditer(re.escape(p) + r"\s*[:：]", masked):
                    hits.append(dict(line=idx, rule="B4", tier="FIX",
                                     snippet=m.group(0),
                                     note="提示语引出：不带信息则删，承接上文换标点"))
                    break

        # ---- B4b：空转句以冒号结尾、下接列表 ----
        if "B4" in fix_on and stripped.endswith(("：", ":")) and not heading:
            for _, _, nxt in scannable[pos + 1:]:
                if not nxt.strip():
                    continue
                if _LIST_ITEM.match(nxt):
                    hits.append(dict(line=idx, rule="B4", tier="FIX",
                                     snippet=stripped,
                                     note="空转句引列表：删后信息不减则改写或删除"))
                break

        # ---- B11：分句内 ≥2 顿号（REVIEW：语义判断在模型；列表内部豁免） ----
        if "B11" in review_on and not is_list_line and not heading:
            for clause in _CLAUSE_SPLIT.split(masked):
                if clause.count("、") >= 2:
                    hits.append(dict(line=idx, rule="B11", tier="REVIEW",
                                     snippet=clause.strip(),
                                     note="分句内 ≥2 顿号串 ≥3 项：能概括就概括，"
                                          "法规条目/配置项/操作枚举保留"))
                    break

    # 同点双报抑制：B4/B10 的改法是删掉段首提示语/起手式，删后 B3 的触发
    # 对象不复存在，同线命中时 B3 不报（优先级见 references/rules-text.md B3）
    if "B3" in review_on:
        drop = {h["line"] for h in hits if h["rule"] in ("B4", "B10")}
        hits = [h for h in hits if not (h["rule"] == "B3" and h["line"] in drop)]

    return hits


def main():
    parser = argparse.ArgumentParser(
        description="机械规则扫描器（确定命中 B4/B6/B10；复核候选 B1/B3/B5/B11/F7）")
    parser.add_argument("files", nargs="*", help="待扫描文件或目录（目录递归）；单独的 - 读 stdin")
    parser.add_argument("--mode", choices=("prose", "fiction", "gen"), default="prose",
                        help="prose=论述清理；fiction=fiction 清理（B6/B1/B5/F7）；"
                             "gen=生成期自查（FIX 同 prose，REVIEW 增 D/C 层候选）")
    args = parser.parse_args()
    if not args.files:
        parser.print_help(file=sys.stderr)
        sys.exit(2)
    total = 0
    for target in args.files:
        if target == "-":
            expanded = [("<stdin>", sys.stdin.read())]
        else:
            paths = _expand_target(target)
            if paths is None:
                print(f"找不到文件或目录：{target}", file=sys.stderr)
                sys.exit(2)
            expanded = []
            for path in paths:
                text = _read_text(path)
                if text is None:
                    print(f"{path}: 无法解码（非 UTF-8/GBK），跳过", file=sys.stderr)
                    continue
                expanded.append((str(path), text))
        for name, text in expanded:
            hits = scan(text, mode=args.mode)
            for h in hits:
                print(f"{name}:{h['line']}\t{h['rule']}\t{h['tier']}\t{h['snippet']}\t{h['note']}")
            total += len(hits)
            if "B3" in REVIEW_RULES[args.mode]:
                _lines = [line for line in text.splitlines() if line.strip()]
                _chunks = [chunk for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
                if len(_lines) > 1 and len(_chunks) < 2:
                    print(f"# 提示：{name} 未检出空行分段，B3 未执行")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
