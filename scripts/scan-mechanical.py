"""机械规则确定性扫描器：确定命中与语境复核候选。

定位：生成候选命中清单，供 LLM 复核语境后决定是否改写。
脚本只报触发标记，不做自动改写——语境判断（如 B4 提示语是否承接上文、
B11 是否法规条目）仍由模型或人完成。依据 references/rules-full.md
成文清理边界"逐句对照实际改动"的要求，本脚本把"实搜"固化下来。

覆盖规则分两级：
  FIX 级（高精度，命中基本即可改）：
  B4  冒号滥用：提示语引出（一句话总结：/核心是：……）＋空转句引列表
  B6  序数词通篇编号小标题（连续 ≥3 个才报）
  B10 起手式：说白了 / 说穿了 / 先说结论（句首位置）
  B12 空降宏观开场：在当今 / 众所周知（句首位置；是否含具体背景信息语义判断）
  REVIEW 级（只报候选，必须复核语境）：
  B11 顿号罗列过密：一个分句内 ≥2 个顿号串 ≥3 项并列（法规条目、配置项、
      技术操作枚举须保留，语义判断在模型——降级 REVIEW 防误授权）
  B1  翻案腔：句中含"而是/其实/恰恰"，或省"而"变体"不是A，(只/纯)是B"
      （含"那不是……是……""不只是A，更是B""不是A——是B"，句号与单破折号
      分隔同禁），或"与其说A，不如说B""谈不上A，更多是B""没有A，只有/只是B"
      （事实清点交复核）"不在于A，而在于B""表面/看似A，实则B"——
      被否定的观点是否存在须读上下文
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

模式（对应 rules-full.md 清理 / fiction 清理 / 生成自查三种流程）：
  prose（默认）  清理全量规则
  fiction        报 fiction 清理带入集内的 B6(FIX)、B1/B5/F7/B13/B15/B17/B18
                 (REVIEW)；B3/B4/B10/B11 的倍率来自非虚构论述文体对照，
                 fiction 不带入，一律不报（对小说照报即越界误伤）
  gen            生成期自查：FIX 同 prose（B 层生成清理共用）；
                 REVIEW 增 B1/B3/B5/B9/B13/B15/B16/B17/B18 与
                 C2/C4/C5/C6/D2–D6（D/C 层机械候选），
                 全部只报候选，复核后决定改留
"""
import argparse
import re
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------- 触发标记 ----------

# B10：句首起手式
B10_WORDS = ("说白了", "说穿了", "先说结论")
# B12：句首空降宏观开场（"随着"类不进机械层，误伤具体事件句）
B12_WORDS = ("在当今", "众所周知")

# B4a：提示语＋冒号（见 references/rules-full.md 的 B4）
B4A_PROMPTS = ("一句话总结", "核心是", "关键在于", "原因如下", "本质上")

# B1（REVIEW 级）：翻案腔候选词
B1_WORDS = ("而是", "其实", "恰恰")
# B1 变体：省略"而"的隐性对举——"不是A，只是B""那不是A，是B""不只是A，更是B"
# 与破折号分隔形态（"不是A——是B"，单双破折号与句号分隔同禁："不是A。是B"）。
# 同类扩展：没有A，只有/只是B（虚实对举；事实清点交模型复核）、不在于A而在于B、
# 表面/看似A实则B。裸"，是"口语中也常见（"不是不想去，是没时间"），故只作
# REVIEW 候选；"，而是"交由 B1_WORDS，避免同线双报。(?<!是) 排除"是不是"
# 疑问形被误判为对举（"她问这是不是真的，是真的…"）。
_B1_VARIANT = re.compile(
    r"(?:(?<!是)(?:不只是|不仅是|并非是?|并未|不是)[^，。；！？\n]{0,20}"
    r"(?:[，,。]\s*|——|—)(?:更是|只是|纯粹是|反倒是|反而是|是(?!而))"
    r"|(?:与其说)[^，。；！？\n]{1,25}[，,]?\s*不如说"
    r"|(?:谈不上)[^，。；！？\n]{1,25}[，,]?\s*更多(?:的)?是"
    r"|(?:没有(?:什么)?)[^，。；！？\n]{0,20}(?:[，,。]\s*|——|—)"
    r"(?:只有|只是|唯有)"
    r"|(?:不在于)[^，。；！？\n]{1,25}[，,]?\s*而在于"
    r"|(?:表面(?:上|看似)?|看似)[^，。；！？\n]{1,25}[，,]?\s*"
    r"(?:实则|实际上|背后却|骨子里|暗地里))")

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

# ---------- fiction 词表（B13/B15/B16/B17/B18，gen 与 fiction 模式 REVIEW 候选） ----------

# B13 动作修饰副词候选（复核区分动作修饰与光/声/温度的客观状态描述）；
# "微弱"多用于状态陈述（微弱的光/回响），机械层无法区分，不收
_B13_ADVERBS = re.compile(r"微微|极轻|极慢|极细|轻轻|缓缓")

# B15 舞台剧抽搐候选（含 scan_slop 合并：下颌紧绷/喉结滚动一类/倒吸气/
# 指节泛白/睫毛颤/漏跳一拍——P1 族全量，成熟正则平移）
_B15_SPASM = re.compile(
    r"猛地|骤然|猝然|死死|整个人震了一下|身子猛然一僵|"
    r"喉结滚动|咬碎牙关|指甲掐进|"
    r"瞳孔(?:微|骤|猛地?|剧烈)?(?:缩|收缩)(?![小短])|"
    r"(?:下颌|下颌线|下巴)(?:紧绷|咬得死紧|咬得死死的|收紧)|"
    r"喉结(?:微|上下|艰难地?)?滚(?:动)?|喉头(?:微|剧烈|上下)?(?:滚|动|滚动)|"
    r"指甲(?:深深)?掐[进入]|"
    r"倒[吸抽](?:了)?[一口]*(?:凉|冷)气|"
    r"(?:手指|指|骨)?(?:关节|节|骨节)(?:发|泛|捏得|捏得发)白|"
    r"呼吸(?:猛地|不由得|微微)?一?(?:滞|窒)|"
    r"(?:睫毛|眼睫)(?:微|轻轻一?)?颤(?:动)?|"
    r"心(?:跳|脏)(?:仿佛|猛地|瞬间)?(?:漏|漏跳)了一拍|"
    r"(?:后背|脊背)(?:猛地?一僵|渗出冷汗|冒出冷汗|渗出一层冷汗|一僵)")

# B17 花式对白动词标签（说道/命令道/沉声道一类，台词内合法的中断除外）；
# 问道/答道属旧白话语域（鲁迅设问自答、评书体均常见），精度不足不收
_B17_FANCY_TAGS = re.compile(r"说道|命令道|吩咐道|沉声道|轻声道|"
                             r"低声道|冷声道|感叹道|开口道|沉声说|轻声说")

# B18 计数癖候选：拍子枚举、第N拍、顿了一拍
_B18_COUNTING = re.compile(
    r"[一二两三四五六七八九十\d]+[下息拍声滴]，[一二两三四五六七八九十\d]+[下息拍声滴]"
    r"|数到第?[一二两三四五六七八九十\d]+[下滴声息]"
    r"|第[一二三四五六七八九十\d]+[下拍滴]"
    r"|顿了[一半][拍下]")

# B17 句首代词连珠：段内 ≥3 句连续以同一代词起头
_B17_PRONOUN_HEAD = re.compile(r"^[她他你]")

# ---------- scan_slop 合并词条（P3–P8 同类，gen 模式 REVIEW 候选） ----------

# P3 套路修辞与凝固感 → C6 扩展（空气凝固/眼底闪过/填满/鬼魅）
_C6_ATMOS_EXT = re.compile(
    r"(?:眼(?:中|底|眸|眸深处|眸底)|眸(?:中|底|深处))(?:深处)?(?:闪过|掠过)一[丝抹道]|"
    r"空气(?:仿佛|骤然|在这一瞬间|像)*(?:凝固|静止)(?:了一般|了一样|了)?|"
    r"宛如鬼魅(?:一般)?|"
    r"寂静(?:仿佛)?有了重量|"
    r"(?:声音|尖叫声|警报声|轰鸣声|哭声)?填满(?:了整个|了整个?的?|了)?"
    r"[^，。；！？\n]{0,10}(?:空间|房间|屋子|走廊|大厅|室内|车厢)|"
    r"时间仿佛停止了流动")

# P4 虚假升华 → C2 扩展（这一刻明白真谛一类 + 何尝不是）
_C2_GRAND_EXT = re.compile(
    r"(?:(?:在?这一(?:刻|瞬间|刹那)|此时此刻)[，,]?"
    r"(?:他|她|他们|她们|所有人)?[^，。；！？\n]{0,8}"
    r"(?:终于|仿佛|才)?(?:彻底|深刻|深深地?)?(?:明白|领悟|读懂)了?"
    r"|领悟到了?|这何尝不是)"
    r"[^。；！？\n]{0,25}"
    r"(?:人生|命运|时代|灵魂|人性|真谛|意义|救赎|较量|宿命|生命的重量)")

# P6 装深沉时间感 → B16 扩展（许多年后才明白/世纪/失去意义）
_B16_TIME_EXT = re.compile(
    r"(?:(?:许多|很多|数|多|很久)年以?后[，,]?"
    r"(?:他|她|他们|她们|所有人)?才会?明白|"
    r"不知道?过了多(?:久|长时间)|"
    r"(?:仿佛|像是|好像|宛如)过了(?:一个世纪|很久)|"
    r"时间在?(?:这一刻|此刻|此时)(?:彻底)?失去了意义)")

# P7 情绪贴标签 → B14 候选（情绪诊断书：涌上心头/大手攥住/无力感）
_B14_EMOTION = re.compile(
    r"(?:一股|一种|一阵)(?:莫名|强烈|无法言喻|前所未有|难以名状|难以抑制)"
    r"的?[^，。；！？\n]{0,8}(?:涌上|袭来|蔓延|攥住|包裹|苦涩)|"
    r"心(?:脏)?像被(?:一只(?:无形|冰冷)?的?大手)?(?:狠狠)?[拧攥揪]|"
    r"(?:感到|涌起|心底泛起)(?:一阵)?深深的无力(?:感)?")

# P8 客服套话 → D2 扩展（非常好问题/希望有所帮助/如您所见一类）
_D2_SERVICE_EXT = re.compile(
    r"这是一个(?:非常|很)?(?:好|棒|绝佳)的问题|"
    r"希望(?:这个回答|这些建议|以上内容|以上解答|上述分析)?"
    r"对(?:您|你)(?:有所)?(?:帮助|启发)|"
    r"如(?:您|你)所(?:愿|见)|"
    r"当然可以[，。！]|"
    r"很高兴为(?:您|你)(?:解答|服务)?|"
    r"如果(?:您|你)还有(?:其他)?(?:问题|疑问)[，,]欢迎|"
    r"欢迎随时(?:向我)?提问")

# 各模式的报告集（见模块 docstring"模式"节；B11 需语义判断，prose/gen 均 REVIEW）
FIX_RULES = {"prose": ("B4", "B6", "B10"), "fiction": ("B6",),
             "gen": ("B4", "B6", "B10")}
REVIEW_RULES = {
    "prose": ("B1", "B3", "B5", "B11", "B12"),
    "fiction": ("B1", "B5", "F7", "B13", "B15", "B17", "B18"),
    "gen": ("B1", "B3", "B5", "B9", "B11", "B13", "B14", "B15", "B16",
            "B17", "B18", "C2", "C4", "C5", "C6", "D2", "D3", "D4", "D5",
            "D6"),
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

        # ---- B1（REVIEW）：翻案腔候选词与隐性对举变体 ----
        if "B1" in review_on and not heading:
            for sent in _SENT_SPLIT.split(masked):
                for w in B1_WORDS:
                    if w in sent:
                        hits.append(dict(line=idx, rule="B1", tier="REVIEW",
                                         snippet=sent.strip()[:40],
                                         note=f"含“{w}”：核对被否定的观点是否真实存在，"
                                              f"不存在删否定留肯定；角色台词内不改"))
                        break
            # 变体匹配行级执行：句号分隔形态（"不是A。是B"）跨句界，
            # 按分句循环会漏报；台词引号已在 masked 中豁免
            for m in _B1_VARIANT.finditer(masked):
                hits.append(dict(line=idx, rule="B1", tier="REVIEW",
                                 snippet=m.group(0),
                                 note="隐性对举变体（不是A，(只/纯)是B/更是B/"
                                      "没有A只有B/看似A实则B——省“而”与句号、"
                                      "破折号分隔形态）：核对被否定的观点是否"
                                      "真实存在，不存在删否定留肯定；事实清点"
                                      "（冰箱里没有可乐，只有啤酒）与台词内不改"))

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
            for m in _C2_GRAND_EXT.finditer(masked):
                hits.append(dict(
                    line=idx, rule="C2", tier="REVIEW", snippet=m.group(0),
                    note="模板感悟句候选（这一刻明白真谛族）：脱离情节的"
                         "感悟金句删掉，停在人物最后的动作或物理余韵"))
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
            for m in _C6_ATMOS_EXT.finditer(masked):
                hits.append(dict(
                    line=idx, rule="C6", tier="REVIEW", snippet=m.group(0),
                    note="套路修辞候选（空气凝固/眼底闪过/声音填满一类）："
                         "删套路词，写具体光影、声音或动作"))
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
            for m in _D2_SERVICE_EXT.finditer(masked):
                hits.append(dict(
                    line=idx, rule="D2", tier="REVIEW", snippet=m.group(0),
                    note="客服套话候选（好问题/希望有所帮助/如您所见一类）："
                         "删掉，第一句直奔主题，说完即停"))
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

        # ---- fiction 词表（REVIEW）：B13/B15/B16/B17花式/B18，逐处报出 ----
        if "B13" in review_on:
            for m in _B13_ADVERBS.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B13", tier="REVIEW", snippet=m.group(0),
                    note="动作修饰副词候选：修饰动作则删（动词自带分量）；"
                         "光/声/温度的客观状态描述保留"))
        if "B15" in review_on:
            for m in _B15_SPASM.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B15", tier="REVIEW", snippet=m.group(0),
                    note="舞台剧抽搐候选：改成定住与动作停顿；"
                         "对抗场景用精准动量受力动词"))
        if "B16" in review_on:
            match = _F7_LOOP.search(masked)
            if match:
                hits.append(dict(
                    line=idx, rule="B16", tier="REVIEW", snippet=match.group(0),
                    note="同词回环候选：改掉‘很久，久到’表层句式；"
                         "后半有新信息保留事实改直述，无信息增量删后半"))
            for m in _B16_TIME_EXT.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B16", tier="REVIEW", snippet=m.group(0),
                    note="装深沉时间感候选（许多年后才明白/仿佛一世纪一类）："
                         "交代具体时间点或推进客观动作，不硬造时间重量"))
        if "B14" in review_on:
            for m in _B14_EMOTION.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B14", tier="REVIEW", snippet=m.group(0),
                    note="情绪贴标签候选（涌上心头/大手攥住/无力感一类）："
                         "用动作阻碍与视线停留呈现，不直接下情绪诊断"))
        if "B17" in review_on:
            for m in _B17_FANCY_TAGS.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B17", tier="REVIEW", snippet=m.group(0),
                    note="花式对白标签：改‘说’或改动作（她把碗放下。“吃。”）"))
        if "B18" in review_on:
            for m in _B18_COUNTING.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B18", tier="REVIEW", snippet=m.group(0),
                    note="计数癖候选：作者数拍子改体感或物件变化；"
                         "角色在数是情节、数量变化是发现，保留"))

        # ---- B4a：提示语＋冒号 ----
        if "B4" in fix_on and not heading:
            for p in B4A_PROMPTS:
                for m in re.finditer(re.escape(p) + r"\s*[:：]", masked):
                    hits.append(dict(line=idx, rule="B4", tier="FIX",
                                     snippet=m.group(0),
                                     note="提示语引出：不带信息则删，承接上文换标点"))
                    break

        # ---- B4b：冒号结尾引列表（REVIEW：冒号前是否承载真实指令/约束
        # 是语义判断——"PR 描述里强制写："是真指令，"如下："是空转；
        # 实测 qa 生成 FIX 误伤，降级复核）
        if "B4" in fix_on and stripped.endswith(("：", ":")) and not heading:
            for _, _, nxt in scannable[pos + 1:]:
                if not nxt.strip():
                    continue
                if _LIST_ITEM.match(nxt):
                    hits.append(dict(line=idx, rule="B4", tier="REVIEW",
                                     snippet=stripped,
                                     note="冒号引列表候选：冒号前是空转"
                                          "（如'如下：'）才删改；承载真实"
                                          "指令/约束（'强制写：'）保留"))
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

    # ---- B17：句首代词连珠（段内 ≥3 句连续同一代词起头）与标签密度 ----
    if "B17" in review_on:
        _plain_tag = re.compile(r"[她他你我](?:说|开口|应|问)[，。：、！？]")
        for idx, raw, masked in scannable:
            stripped_m = masked.strip()
            if not stripped_m:
                continue
            sents = [s.strip() for s in _SENT_SPLIT.split(stripped_m) if s.strip()]
            run = best_run = 0
            cur = None
            for s in sents:
                head = s[:1]
                if _B17_PRONOUN_HEAD.match(head):
                    run = run + 1 if head == cur else 1
                    cur = head
                else:
                    run, cur = 0, None
                best_run = max(best_run, run)
            if best_run >= 3:
                hits.append(dict(
                    line=idx, rule="B17", tier="REVIEW", snippet=stripped_m[:40],
                    note=f"句首代词连珠（连续 {best_run} 句）：一主串多动，"
                         "主语带出一次靠动词链顺承"))
        n_dialogue = sum(1 for _, raw, _ in scannable
                         if re.match(r"^[“\"『「]", raw.strip()))
        n_tags = sum(len(_plain_tag.findall(masked)) for _, _, masked in scannable)
        if n_dialogue >= 4 and n_tags > n_dialogue * 0.5:
            first_tag_line = next(
                (idx for idx, _, masked in scannable
                 if _plain_tag.search(masked)), 1)
            hits.append(dict(
                line=first_tag_line, rule="B17", tier="REVIEW",
                snippet=f"{n_tags} 个说类标签 / {n_dialogue} 行独行对白",
                note="对白标签密度超标：语境可判的独行对白直接呈现；"
                     "力度用动作替标签干活"))

    # 同点双报抑制：B4/B10 的改法是删掉段首提示语/起手式，删后 B3 的触发
    # 对象不复存在，同线命中时 B3 不报（优先级见 SKILL.md B3）
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
