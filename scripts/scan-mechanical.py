"""机械规则确定性扫描器：确定命中与语境复核候选。

定位：生成候选命中清单，供 LLM 复核语境后决定是否改写。
脚本只报触发标记，不做自动改写——语境判断（如 B4 提示语是否承接上文、
B11 是否法规条目）仍由模型或人完成。依据 references/rules-full.md
成文清理边界"逐句对照实际改动"的要求，本脚本把"实搜"固化下来。

覆盖规则分两级：
  FIX 级（高精度，命中基本即可改）：
  B4  冒号滥用：提示语引出（一句话总结：/核心是：/直接给答案：……）
  B6  序数词通篇编号小标题（连续 ≥3 个才报）
  B10 起手式：说白了 / 说穿了 / 先说结论 / 说到底 / 归根结底（句首位置）
  REVIEW 级（只报候选，必须复核语境）：
  B12 空降宏观开场：在当今 / 在……时代（背景、环境）下 / 在……的今天 /
      随着……不断发展 / 众所周知（句首锚定；是否含具体背景信息须语义
      判断，故不授权自动改写）
  B11 顿号罗列过密：一个分句内 ≥2 个顿号串 ≥3 项并列（法规条目、配置项、
      技术操作枚举须保留，语义判断在模型——降级 REVIEW 防误授权）
  B1  翻案腔：只报四类有基准断言或零人类误报的形态
      ——“不是A，而是B”、“不是A，纯粹是B”、
      “不仅仅是A，更是B”、“没有A，只有/只是B”。
      “不在于A而在于B”、“表面/藉伿A实则B”、
      “与其说A不如说B”、“谈不上A更多是B”、
      “哪儿是A分明是B”是人类论述文常态，
      机械层不设候选，交人工判断（实测依据见
      rules-full.md B1 条）。fiction 模式下省“而”且
      B 侧落在屏“是/只是/只有”、B 侧能拍成画面
      时按事实清点放行；B 侧抽象则撤销免责
  B3  段首零回指评论：非首段以评论语开头且整句无"这/那/其/此/上面"
  B4b 空转句以冒号结尾引列表：冒号前是空转（"如下："）还是承载真指令
      （"强制写："）须读语义，与 B4a 不同级，发 REVIEW 防误授权
  B5  叙述中的破折号：逐处核对是否只是解释、列举、因果或同位补充
  B9  装饰性喻体：明喻标记＋"一＋量词"引出的铺陈喻体
  B16  fiction 中的"很久……久到……"等空泛回环候选
  B17  花式对白标签、句首代词连珠（段内 ≥3 句同一代词起头）、
        句内主语复现（同句相邻分句同一代词起头："她知道，她也明白"）、
        问答乒乓（连续 ≥5 行独行对白且行间无叙述）
  gen 模式追加 REVIEW 候选（D/C 层机械候选，改写判断在模型）：
  C2  结尾拔高、C4 hedging 叠加、C5 空泛气氛总结
  D2  服务腔开场（句首）与客服收尾（句尾）、总结套话开场（综上所述/由此可见）
  D3  免责包装、D4 万能收尾（含整句式"因人而异"）、D5 元话语空预告、D6 模糊归因
  无机械层的规则（判断类，交付前人工自查，依据见 rules-full.md 各条）：
  B2 概括盖住已有具体、B7 相邻句结构同款、B8 翻译腔（只认五种）

白名单（绝对原则，完全豁免）：围栏代码块、行内代码、YAML frontmatter、
表格行、引用块（> 起首）、URL、Markdown 列表内部（B11）。

输出附注：全文只有一段时 B3 段首判定无从执行，打印一行提示，不改退出码。
文件解码按 utf-8-sig（兼容 BOM）→ gbk 依序尝试，均失败打印跳过说明并继续。

用法：
  python scripts/scan-mechanical.py <文件> [文件...] [--mode prose|fiction|gen]
  python scripts/scan-mechanical.py -          # 读 stdin
退出码：0 无命中，1 有命中，2 用法错误。
自测：python scripts/test-scan-mechanical.py

模式（对应 rules-full.md 清理 / fiction 清理 / 生成自查三种流程）：
  prose（默认）  清理全量规则：FIX B4/B6/B10，REVIEW B1/B3/B5/B9/B11/B12
                  （B2/B7/B8 为判断类规则，机械层不设候选，见各条）
  fiction        报 fiction 清理带入集内的 B6(FIX)、B1/B5/B9/B13/B14/B15/
                  B16/B17/B18(REVIEW)；B3/B4/B11 的倍率来自非虚构论述
                  文体对照，fiction 不带入，一律不报（对小说照报即越界误伤）
  gen            生成期自查：FIX 同 prose（B 层生成清理共用）；
                  REVIEW 增 B13–B18 叙事候选与 C2/C4/C5/D2–D6
                  （D/C 层机械候选），全部只报候选，复核后决定改留
"""
import argparse
import re
import sys
from pathlib import Path
import _loader

_loader.ensure_utf8()

# ---------- 触发标记 ----------

# B10：句首起手式（词表与 SKILL.md / rules-full.md 的 B10 条目一致，verify_repo.py 做一致性核验）
B10_WORDS = ("说白了", "说穿了", "简单来说", "简单说", "先说结论",
              "说到底", "归根结底")
# B10 构词负向断言："归根结底的原因""说到底的方案"是名词性用法，不是起手式
B10_HEAD = re.compile(r"^(?:" + "|".join(B10_WORDS) + r")(?!的)")
# B12：句首空降宏观开场（prose / gen 同报 B12）。
# 覆盖 rules-full B12 文档形态：在当今 / 在……的今天 / 在……时代（背景、环境）下 /
# 随着……不断（发展、演变、进步）/ 众所周知。
# "随着"必须带"不断"：具体事件句（"随着供应商切换完成"）是合法叙述，不报；
# 句内是否含具体背景信息由人核对（REVIEW 口径）。
_MACRO_OPENER = re.compile(
    r"在当今|众所周知|在[^，。；！？\n]{2,24}的今天|"
    r"在[^，。；！？\n]{0,16}(?:时代|背景|环境)下|"
    r"随着[^，。；！？\n]{2,24}的?不断(?:发展|演变|进步|前进)")

# B4a：提示语＋冒号（见 references/rules-full.md 的 B4）
B4A_PROMPTS = ("一句话总结", "核心是", "关键在于", "原因如下", "本质上", "直接给答案")

# B1（REVIEW 级）：翻案腔候选词
B1_WORDS = ("而是", "其实", "恰恰")

# 翻案对举的肯定面标记。“其实/恰恰”与否定词同句外还须有对举证据
# 才报：本词表共现，或自身充当 B 侧引导词（_b1_self_contrast）。
_B1_CONTRAST = ("更是", "只是", "纯粹是", "装作是",
               "屏是", "不在于", "而在于")
# 与"其实/恰恰"同句出现时才算翻案对举的否定词
_B1_NEGATION = ("不是", "没有", "并非", "不全是", "不在于")
# B1 变体：省略"而"的隐性对举——"不是A，只是B""那不是A，是B""不只是A，更是B"
# 与破折号分隔形态（"不是A——是B"，单双破折号与句号分隔同禁："不是A。是B"）。
# 同类扩展：没有A，只有/只是B（虚实对举；事实清点交模型复核）、不在于A而在于B、
# 表面/看似A实则B、"不算A，是B"（否定的另一种说法，同一个对举壳）。
# 裸"，是"口语中也常见（"不是不想去，是没时间"），故只作
# REVIEW 候选；"，而是"交由 B1_WORDS，避免同线双报。(?<!是) 排除"是不是"
# 疑问形被误判为对举（"她问这是不是真的，是真的…"）。
# B1 变体：省略"而"的隐性对举。
# 收窄依据（人类语料实测）：下列分支在人类论述文里是正常修辞，基准用例也不
# 断言它们，故不进机械层——不在于A而在于B（"差距不在于资源，而在于决心"）、
# 与其说A不如说B、谈不上A更多是B、哪儿是A分明是B、表面/看似A实则B。
# 鲁迅《拿来主义》664 字里 1 处误报正是"而不是'拿来'的缘故"（前文主张过的
# 合法否证）；这些形态是否病灶取决于"被否定的观点有没有人主张过"，须读上下文。
# 保留的三类都有基准断言或零人类误报：不是A，(只/纯)是B/更是B（SF-05）、
# 没有A，只有/只是B（事实清点另按 doc 判据放行）。分隔符含 ；（"这不是
# 结束；是开始"）与 、（"这不是结束、是开始"）——抽象 B 侧的对比对举
# 不因分隔符变形漏报；破折号与句号形 doc 明列为病灶，不设抽象豁免。
# B1 事实清点的反面：B 侧落在情绪/性质/概念类名词上时不是清点，是抽象对举
# （rules-full B1 与 fiction.md 二.1：A、B 均为情绪、性质、概念类名词才禁；
# 放行判据是"A、B 能拍成画面"）。机械层用概念词表近似——只认具体侧，
# B 侧抽象即撤销 fiction 的省"而"豁免。REVIEW 级候选不求全，词表取 doc
# 点名形态与实测 archetype。"这不是结束，是开始""那不是终点，是新的起点"
# "这不是妥协，是智慧"此前靠裸"是"尾全部溜过 fiction 豁免。
_B1_CONCEPT = re.compile(
    r"结束|终[点结]|起点|开[端始]|序章|妥协|智慧|勇气|勇敢|怯懦|英雄|幸存者|失败|失误|"
    r"必然|偶然|缺点|特点|学费|依赖|惩罚|保护|请求|命令|逃避|战场|坚持|放弃|态度|"
    r"选择|命运|宿命|轮回|循环|答案|真相|谎言|借口|理由|本质|核心|关键|意义|价值|"
    r"自由|孤独|绝望|希望|恐惧|愤怒|悲伤|喜悦|冷漠|热情|清醒|沉沦|救赎|审判|屈服|"
    r"反抗|顺从|成熟|天真|善良|恶意|赌博|调试|设计|问题|转身|时间|钱|表演|姿态|"
    r"立场|代价|回报|结果|过程|手段|目的|动机|逻辑|秩序|规则|底线|原则|门槛|镜像|"
    r"影子|外壳|假象|表象|实质|写法|形式|方式|表现|驯[服养化]|毁灭|牺牲|交易|"
    r"较量|博弈|让步|进步|退步|成功|胜利|征服|逃逸|放逐|执行|落实|推进")
# B 侧"能拍成画面"的具体标记：数量词、动作完成体、常规动作与生活实物。
# 数量词排除"另一"后接（(?<!另)）："另一个"的"一"是构词成分不是计数，
# "这是另一个开始"的 B 侧是抽象对举，不能被"一个"误判成具体。
_B1_CONCRETE = re.compile(
    r"(?<!另)[一二两三四五七八九十几半几多][个只条张片块支朵叶枚堵串头座辆台本册页句字"
    r"步声下拍息滴盏轮股颗缕丝道面抹汪弯茬顿袭派粒茎根幢把阵种味床束尊]|"
    r"[了着过](?![的])|走过来|跑过来|爬起来|蹲下来|站起来|开门|关门|点头|摇头|"
    r"皱眉|微笑|说话|出声|呼吸|抬手|啤酒|可乐|猫|狗|狼|雪|盐|钥匙|碗|书")
# 剥掉 B 侧的动词/修饰前缀再判概念词："在表演勇敢" → "勇敢"
_B1_STRIP = re.compile(
    r"^(?:在|被|选择|决定|装作|摆出|表演|精心|刻意|进一步|更|最|真正|唯一|最好|最后|"
    r"新的?|另一种?|某种|一种|更深的?|自己|他们|我们|你们|的)+")
_B1_NEXT_PUNCT = re.compile(r"[，。；！？、\n…]")


def _b1_b_side(masked, m):
    """取 B 标记右侧到下一个句读的文本（对举的 B 侧）。"""
    tail = masked[m.end():]
    nxt = _B1_NEXT_PUNCT.search(tail)
    return (tail[:nxt.start()] if nxt else tail).strip()


def _b1_abstract_b(side):
    """B 侧是抽象概念（不能拍成画面）→ 不是事实清点。"""
    if not side or len(side) > 12 or _B1_CONCRETE.search(side):
        return False
    core = _B1_STRIP.sub("", side)
    core = re.sub(r"^[^，。；！？\n]{1,4}的(?=.)", "", core)
    return bool(_B1_CONCEPT.search(core))


def _b1_self_contrast(w, sent):
    """“其实/恰恰”自身充当 B 侧引导词：不要求 _B1_CONTRAST 共现。

    紧跟逗号即落在 B 侧位置（“她不是不去，其实是不屑”）；“恰恰”紧贴否定词
    也是（“他恰恰不是主角”——恰恰只作对举副词，贴否定词即翻案；“其实”贴
    否定词是普通陈述）。朱自清“其实我那年已二十岁…”行首出现、王小波
    “男孩子其实没有犯癔症”均不具这些形态，据此静默。
    """
    if re.search(r"[\uff0c,]\s*" + w, sent):
        return True
    return w == "恰恰" and re.search(
        w + "(?:" + "|".join(_B1_NEGATION) + ")", sent) is not None


_B1_VARIANT = re.compile(
    r"(?:(?<!是)(?:不只是|不仅是|不仅仅是|并非是?|并未|不是|不算|算不上)[^，。；！？\n]{0,20}"
    r"(?:[，,。；、]\s*|——|—)(?:更是|只是|纯粹是|反倒是|反而是|倒像是|倒似是|"
    r"活像是|(?:(?:我们|你们|他们|她们|它们|我|你|他|她|它|这|那))?是(?!而))"
    r"|(?:不在)[^，。；！？\n]{1,20}(?:[，,。；！、]\s*)在"
    r"|(?:没有(?:什么)?)[^，。；！？\n]{0,20}(?:[，,。]\s*|——|—)"
    r"(?:只有|只是|唯有))")

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
# 引文整段豁免，含 ASCII 引号（技术写作常用 ASCII 引号作术语强调/转述）；
# 授权口径写入 rules-full.md 第五节"成文清理边界"的"引文整段免责"条
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
# B16 程度回环候选：程度词同形复现（"很久，久到"族）。
# "轻"为实测补充：fiction 清理中模型常规删除"你的呼吸轻得……轻得我数不到"
# 式程度回环，旧词表无此形态致删除无归属；
_B16_LOOP = re.compile(
    r"(?:很久[，,、；;。.!！？?…\s]{0,4}久到|"
    r"(?P<quiet>安静|寂静)[，,、；;。.!！？?…\s]{0,4}(?:(?P=quiet)|静)[到得]|"
    r"沉默[，,、；;。.!！？?…\s]{0,4}沉默到|"
    r"(?P<degree>冷|黑|痛|累|远|慢|快|轻|深|重|高|低|厚|久)"
    r"[得，,、；;。.!！？?…\s]{0,4}(?P=degree)[到得])")
# B16 生硬点题："所谓X不过是Y"是 rules-full B16 与 fiction.md 二.7 明示禁用的
# 形态，原正则无覆盖。
_B16_SUOWEI = re.compile(r"所谓(?:的)?[^，。；！？\n]{1,12}[，,]?不过是")
_TEXT_SUFFIXES = {".md", ".markdown", ".txt"}

# ---------- gen 模式触发标记（既有规则的机械候选，全部 REVIEW 级） ----------

# B9 装饰性喻体：明喻标记＋"一＋量词"引出的铺陈喻体（乐团/导师/灯塔/明月…），
# 以及"像X一般/一样"常规明喻形态（实测：fiction 清理中 6/7 模型删除
# "像是被雷击中一般""月光像水一样"，旧词表覆盖不到致删除无归属；
# 人类语料 10.7 万字该形态 0.24/万字，REVIEW 级候选不授权自动改写）。
# "一个"不报：解释性比喻的常规量词（缓存就像一个仓库）。
# 喻标记补 俨然/恍若/好似/似的；量词补 朵叶枚堵泓串注线圈顶副柱川撇捺头。
# 喻体与"一般/一样"之间至少留 1 字：鲁迅"画像一般都是披着长发"里的"一般"
# 是副词（＝通常），不是明喻收尾；"像羲皇时候一般太平"喻体非空，照报。
_B9_SIMILE = re.compile(
    r"(?:就像|如同|宛如|仿佛|犹如|恰似|俨然|恍若|好似|像|像是|相当于)"
    r"[^，。；！？]{1,8}(?:一般|一样|似的)|"
    r"(?:就像|如同|宛如|仿佛|犹如|恰似|俨然|恍若|好似|像|相当于)"
    r"[^，。；！？]{0,6}一[位支场座轮缕双只股颗盏片条面抹丝道汪弯茬顿袭派粒滴茎根台幢把阵种声味床束尊"
    r"朵朵叶枚堵泓串注线圈顶副柱川撇捺头]")

# B9 句末明喻：分句以"，像X"收尾的整句（"她被光镀了一层霜，像雨前的天。"）。
# 单处是人类常态，不报；只在全文成规律时整体报一次——判据是"至少五处
# 且占全文句数 ≥8%"（见 rules-full B9）：短文本里一处明喻就占 10%+，
# 只看比例会把单处好写法判成节拍器（沈从文"象夏夜的一只微绿的小眼睛"
# 即此形态且是好写法）。实测长文创作中该形态可达 15%/句（人写语料 0/10 篇）。
_B9_TAIL = re.compile(
    r"[，,；]\s*(?:像|象|仿佛|宛如|犹如|好似|如同|恰似)"
    r"[^，。；！？\n]{1,24}[。！？]\s*$")
_B9_TAIL_MIN = 5          # 全文句末明喻至少这么多处
_B9_TAIL_RATIO = 0.08     # 且占全文句数 ≥8% 才报（实测分界）

# B9 陈词套式：doc 明列"单处即判，与密度无关"，与 _B9_TAIL 的密度口径分开。
# 判据是"换个场景还能原样用"——这些成套比喻在别处见过成百上千次。
_B9_CLICHE = re.compile(
    r"(?:像|象|仿佛|宛如|犹如|好似|如同|恰似)(?:被)?"
    r"(?:两口?枯井|一潭死水|抽走了?力气|抽干了?力气|从水里捞出来"
    r"|一床湿透的棉被|一道晴空霹雳|被雷劈中|被泼了一盆冷水)")

# C2 结尾拔高：模板化升华与乐观收尾
_C2_GRAND = re.compile(
    r"真正重要的是|从更大的角度看|未来可期|"
    r"迈出了?(?:重要|关键)的一步|开启了?(?:全新|新的?)篇章|"
    r"这不仅[^。]{0,20}更(?:是|关乎|能)")

# C4 hedging 叠加：两个不确定标记之间无句读
_C4_HEDGE = re.compile(
    r"(?:可能|或许|也许|大概|在一定程度上|在某种程度上)[^，。；]{0,10}"
    r"(?:可能|或许|也许|大概|在一定程度上|在某种程度上)")

# C5 空泛气氛总结
_C5_ATMOS = re.compile(
    r"(?:声音|寂静|沉默)[^。]{0,8}(?:填满|充满|弥漫)|"
    r"静[得有][^。]{0,6}重量|世界退回[^。]{0,4}壳")

# D2 服务腔开场（句首匹配）。过宽的"希望这/希望对你/希望对您"已换成完整客套形态：
# 原三词会把"希望这个世界更温柔""希望这周能上线"判成套话；收尾套话由 _D2_TAIL 覆盖。
# 构词负向断言：后接"的/地/得/性/之"是名词性用法（"希望对你有帮助的方式""好问题的定义"）。
_D2_OPENERS = ("好问题", "问得好", "这是个好问题", "这真是个好问题",
               "感谢提问", "感谢你的提问",
               "希望对你有帮助", "希望对您有帮助", "希望对您有所帮助",
               "希望对你有启发", "希望这些建议对你有帮助",
               "如有疑问", "如有任何问题", "欢迎随时提问", "欢迎随时向我提问")
_D2_HEAD = re.compile(
    r"^(?:" + "|".join(re.escape(w) for w in _D2_OPENERS) + r")(?![的地得性之])")

# D2 句首总结套话（仅书面空转词，不含口语的"综上/总之"——实测那是日常常态）
_D2_SUMMARY_OPENERS = ("综上所述", "由此可见")
# 构词负向断言："综上所述的问题""由此可见性"是名词性用法
_D2_SUMMARY_HEAD = re.compile(
    r"^(?:" + "|".join(_D2_SUMMARY_OPENERS) + r")(?![的性所言])")

# D2 客服收尾（句尾匹配，整句尾部为短语才算）
# 收尾标点/语气符在匹配前剔除（主体词表与 astrbot 插件侧 DEFAULT_ENDINGS 对齐；
# "随时问我"不收——那是自然口语不是客服腔，误伤面实测最大）
_TRAILING_PUNCT = "。．.!！?？~～…‥、,，;；)）」』】 \t\r\n"
_D2_TAIL = re.compile(
    r"(?:希望能帮到你|希望这能帮到你|希望对你有帮助|希望对您有帮助|希望对您有所帮助"
    r"|希望这对你有帮助|希望这些建议对你有帮助|希望对你有启发|希望有所帮助"
    r"|随时联系我|有问题随时找我|有问题可以随时找我"
    r"|欢迎继续交流|欢迎随时交流)\s*$")
# "以上，供参考"独立成句时才是空转收尾；"这部分供你参考"是正常信息句式
_D2_TAIL_STANDALONE = re.compile(r"^以上[，,]\s*供参考\s*$")

# D3 免责包装
_D3_DISCLAIM = re.compile(
    r"作为一?[个名]?语言模型|根据我的训练数据|我的知识截止|训练数据截止")

# D4 万能收尾
_D4_BALANCE = re.compile(
    r"关键在于找到平衡|要结合实际情况|没有绝对的对错")
# D4 整句式万能收尾（"因人而异。"式独立成句才报，句中"因人而异的问题"不报）
_D4_TAIL = re.compile(
    r"^(?:(?:因|视)?人而异|视情况而定|看具体情况|没有标准答案|没有绝对的对错)\s*$")

# D5 元话语空预告（含具体动作的真步骤不在此 pattern 内，复核区分）
_D5_META = re.compile(
    r"(?:下面|下面我|我先|首先由我)(?:我|让我)?(?:将|会|就|先|来)[^，。]{0,16}(?:展开|介绍|说明|分析)|"
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
# 指节泛白/睫毛颤/漏跳一拍——P1 族全量，成熟正则平移）。
# “狂跳”为实测补充：fiction 清理中模型常规删除“心脏狂跳不止”（生理模板），旧词表无此形态致删除无归属；人类语料 10.7 万字零出现。
# 喉结补"动了动/动"形态；瞳孔补间隔形态（"瞳孔在暗处缩紧"，实测漏网），
# 间隔内排除"射/光"防医学表述（瞳孔反射与对光收缩）误报；
# "缩小/缩短"是生理事实描述，负向断言排除；
# "低吼"为用户判定禁用的发声反应套板（"低吼一声/低吼着/几声低吼"），
# 与倒吸气同类；人类语料 17 万字零出现。裸"低吼"不命中——引擎、风、
# 兽群的客观声源是环境描写，放行。
_B15_SPASM = re.compile(
    r"猛地|骤然|猝然|死死|咬碎牙关|狂跳不止|心脏狂跳|整个人震了一下|身子猛然一僵|"
    r"喉结(?:微|上下|艰难地?)?(?:滚(?:动)?|动(?:了)?动)|"
    r"瞳孔[^，。；！？\n射光]{0,6}(?:缩|收缩)(?![小短])|"
    r"(?:下颌|下颌线|下巴)(?:紧绷|咬得死紧|咬得死死的|收紧)|"
    r"喉头(?:微|剧烈|上下)?(?:滚|动|滚动)|"
    r"指甲(?:深深)?掐[进入]|"
    r"倒[吸抽](?:了)?[一口]*(?:凉|冷)气|"
    r"低吼(?:一[声句]|了[一两三几\d]*[声句]|着|起来)|[一两三几\d]+[声句]低吼|"
    r"(?:手指|指|骨)?(?:关节|节|骨节)[^，。；！？\n]{0,6}(?:发|泛)白|"
    r"眼前(?:一阵|一黑|顿时)?发[白黑]|"
    r"呼吸(?:猛地|不由得|微微)?一?(?:滞|窒)|"
    r"(?:睫毛|眼睫)(?:微|轻轻一?)?颤(?:动)?|"
    r"心(?:跳|脏)(?:仿佛|猛地|瞬间)?(?:漏|漏跳)了一拍|"
    r"(?:后背|脊背)(?:猛地?一僵|渗出冷汗|冒出冷汗|渗出一层冷汗|一僵)")

# B15 客观声源：引擎、风、兽群、机器一类的低吼是环境描写，fiction.md 明言放行；
# 发声反应套板的主语只能是人。
_B15_OBJECTIVE_SOURCE = re.compile(
    r"(?:引擎|发动机|风机|排气管|音箱|喇叭|冰箱|空调|机器|锅炉|江水|海浪|狂风|风|"
    r"兽|狼|狗|狮子|老虎|牲口|人群|屋外|窗外|远处|山谷|丛林中?)\s*$")

# B17 花式对白动词标签（说道/命令道/沉声道一类，台词内合法的中断除外）；
# 问道/答道属旧白话语域（鲁迅设问自答、评书体均常见），精度不足不收；
# "说道"同理属旧白话常规标签，机械层分不清作者文域，一并排除（鲁迅语料实测：
# 《呐喊》6 万字 18 处"说道"，全属合法旧白话，doc 与词表原不一致）
_B17_FANCY_TAGS = re.compile(r"命令道|吩咐道|沉声道|轻声道|低声说|"
                             r"低吼道|低声道|冷声道|感叹道|开口道|沉声说|轻声说")

# B18 计数癖候选：拍子枚举、第N拍、顿了一拍（"顿了一下"是人类常规停顿表述，排除）
# "隔三息/隔两拍"同属给体感装仪表，fiction.md 二.9 的示范形态即此
_B18_COUNTING = re.compile(
    r"[一二两三四五六七八九十\d]+[下息拍声滴]，[一二两三四五六七八九十\d]+[下息拍声滴]"
    r"|数到第?[一二两三四五六七八九十\d]+[下滴声息]"
    r"|第[一二三四五六七八九十\d]+[下拍滴]"
    r"|顿了[一半]拍"
    r"|隔[一二两三四五六七八九十\d]+[息拍下滴声]")

# B18 角色在数：人物主语 + 数着/数到/数罢 是角色行为，fiction.md 二.9 明言放行
# （"孩子数水滴入睡、哨兵数更声，数这个动作塑造角色"）。作者数拍子没有这个主语。
_B18_CHARACTER_COUNTING = re.compile(
    r"[\u4e00-\u9fff]{0,4}(?:孩子|孩儿|儿子|女儿|老人|哨兵|母亲|父亲|奶奶|爷爷|他|她|我|你)"
    r"[^，。；！？\n]{0,6}数[着了到罢]")

# B17 句首代词连珠：段内 ≥3 句连续以同一代词起头
_B17_PRONOUN_HEAD = re.compile(r"^[她他你它]")
# 句首代词连珠只认"微型断句"（fiction.md 二.8）：连续以代词起头的长句是正常
# 叙述（"他仔细一想……他记得……他坐起身"），切碎成短句才是节拍器。
_B17_MICRO_SENT_MAX = 12
# B17 句内主语复现：同一句内相邻分句以同一代词起头（"她知道，她也明白"）。
# 主语切换（"她爱他，他也爱她"）不命中，第二分句代词与第一分句不同。
# 代词后接"的/们"时主语是后面的名词（"他的母亲/他的老婆"），不是同一主语复现。
_B17_INTRA_HEAD = re.compile(r"^[她他你它]")
_B17_POSSESSIVE = re.compile(r"^[她他你它][的们]")
# 否定-对比豁免（fiction.md 二.8：有意的对比复用放行，不机械清零）：
# 后一分句以"代词+是/在"起头、前一分句含该谓语的否定形（"不是A，是B"/
# "不在A，在B"族）时，相邻同代词分句是对举不是口吃式同向复说。同向复说
# （"她知道，她也明白"）后句不带"是/在"谓头，不受影响。
_B17_CONTRAST_NEG = re.compile(r"不是|不在|并非|不算|不过是|不仅仅是")
_B17_CONTRAST_TAIL = re.compile(r"^[她他你它][是在]")
# 汉字计数：断句长短与引语字数按汉字算，标点不计
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
# 本行是否含直接引语：行首引号、行内引号对、或"说/问/道＋冒号＋引号"。
# 内联引语与剧本体（角色：台词）都靠后两条认出来。
_HAS_QUOTED_SPEECH = re.compile(
    r"^[“\"『「]|[“\"『「][^”\"'』」]{1,400}[”\"'』」]|"
    r"[说问讲喊叫答应][：:]\s*[“\"『「]")

# B17 对白标签计数：口径同 fiction.md 一.5 对白标签纪律自查（数全篇"X说/X道"），
# 含"他说道/她道/他低声说"这类带修饰的形态；代词后必须紧跟说/道，
# 所以"他知道""难道"不会计入。主语是专名时不计数——机械层分不清
# "张三说"与"小说家言"，靠代词标签已能捕获"他说……她说……"转述链。
_B17_TAG = re.compile(
    r"[她他我你](?:低声|轻声|沉声|高声|大声|冷冷地|淡淡地|笑着|"
    r"便会|忙着|忙|又|才|便|就|也|这才)?(?:说道|说|道)(?=[，。：、！？…\s“])")
# B17 问答乒乓：对白行 = 以引号开头、且引号外叙述不超过 _B17_TAG_MAX 汉字的行。
# 整行一句引语算；"“我知道。”你顿了顿，“我是说……”"这类带短标签的也算——
# 标签只有四个字以内，叙述没真正介入，整场戏仍是问答在推进。反之
# "“走。”她把碗放下。"引号外已是一整个动作，叙述真正介入，打断连发。
# 阈值取 4 而非 6："她低声说。"（5 字含修饰）仍算标签，但"她把碗放下。"
# 是动作不是标签，算对白行会把叙述戏误判成乒乓（实测 4 与 6 的差异 <5%）。
_B17_DIALOGUE_HEAD = re.compile(r"^[“\"『「]")
# 行首说话人前缀：称谓（人名/角色/代词）＋可选冒号，长度 ≤6 汉字，
# 且前缀内无句读（否则是叙述句里的引语，不是独行对白）。
_B17_SPEAKER_HEAD = re.compile(
    r"^[\u4e00-\u9fff]{1,6}(?:说|问|答|喊|叫道|说道)?[：:]?(?=[“\"『「])")
_B17_QUOTED = re.compile(r"“[^”]*”|\"[^\"\n]*\"|『[^』]*』|「[^」]*」")
_B17_TAG_MAX = 4
# 叙述+说类标签+引语：引号外只有短标签时该行仍是对白行（B17 密度分母）。
# 整行 `他站起来。他说：“……”` 引号外有叙述，_is_dialogue_line 不认，
# 12 个说类标签 / 0 行对白 → 密度检查被 n_dialogue>=4 直接跳过。
_B17_TAG_QUOTE = re.compile(
    r"[她他我你](?:低声|轻声|沉声|高声|大声|冷冷地|淡淡地|笑着|又|才|便|就|也|这才)?"
    r"(?:说道|说|道)[：:，,]\s*[“\"『」]")
# B5 叙述破折号：排除数字之间的范围连接号
# B5 破折号：U+2014（——）为主，另收全角双连字符 －－（U+FF0D众所周知2）与
# 单字符 –（U+2013）、―（U+2015）。显式不收 ASCII `--`：语料 2360 处
# 全是表格分隔线、CLI 参数与代码，叙述层 0 处，收了只增技术文档误伤；
# 不收单 `－`（"气温－5 度""北京－上海"是连接号）；不收 `─`（U+2500
# 是制表符，语料 84 处全是目录树）。数字区间由 (?<!\d)…(?!\d) 挡下。
_DASH_NOT_RANGE = re.compile(
    r"(?:(?<=\S)(?<!\d)(?:\uff0d{2}|[\u2013\u2015])(?!\d)"
    r"|(?<!\d)\u2014(?!\d))")
# B5 右侧"没有实质内容"的判定：行末只剩空白与收尾标点时视为未完句。
# 含 ASCII 直引号，故用 chr() 拼，避免字面量被截断。
# 含 — 本身：中文破折号是两个 U+2014，判"右侧有无内容"时必须把它
# 从尾巴里去掉，否则"话没说完——"的第一个 — 右侧是第二个 —，判成有内容。
_B5_TAIL_PUNCT = (" \t" + chr(0x2014) + chr(0xFF0C) + chr(0x3002) + chr(0xFF01)
                  + chr(0xFF1F) + chr(0xFF1B) + chr(0xFF1A) + chr(0x3001)
                  + chr(0x2026) + chr(0x201D) + chr(0x2019) + chr(34)
                  + chr(0x3009) + chr(0x300B) + chr(0x300F) + chr(0xFF09))
# 问答乒乓阈值：连续 ≥5 行对白行且行间无叙述即报（fiction.md：四行以内放行，
# 交锋型反问短打是人类高频写法）。整场戏全由问答推进，
# 叙述被挤掉，动作、空间与停顿都没了。
_B17_PINGPONG_MIN = 5

# 剧本体行首「说话人＋冒号＋台词」，台词不带引号（`店员：……饭团。`）。
# _B17_SPEAKER_HEAD 要求冒号后紧跟引号，认不出无引号剧本体；B17 的省略号
# 怯场检查要覆盖这种格式。说话人名限 6 字，冒号后必须立刻有内容。
# 行首散文先行词（"结论：/注意：/前提："）是散文的小标题式行，不是对白：
# 算进分母会虚增省略号怯场占比（实测 6 行先行词＋2 行真对白误报 2/8、
# 6 行"结论一：……"误报 6/6）。负向前查做进模式而非判定处——本模式同时
# 供对白行判定与说话人剥离两处使用，写在模式里两边才不会走样。
_B17_PROSE_HEAD = ("结论", "注意", "前提", "假设", "范围", "背景", "说明",
                   "备注", "提示", "例如", "原因", "结果", "步骤", "重点", "要求")
_B17_SCRIPT_HEAD = re.compile(
    r"^(?!(?:" + "|".join(_B17_PROSE_HEAD) + r"))[\u4e00-\u9fff]{1,6}[：:](?=\S)")


def _is_dialogue_line(line):
    """对白行：整行一句引语；引号外只挂短标签；或行首是「说话人＋冒号＋
    引语」。引号外叙述成句则打断连发。

    说话人前缀也认：`店员："欢迎光临。"` 与 `"欢迎光临。"他说` 一样没有
    叙述介入，漏掉它等于放整个格式过关（实测无 skill 基线有 156 行纯对白墙
    用的正是这个格式，旧检测器 0 命中）。
    """
    m = _B17_SPEAKER_HEAD.match(line)
    if m:
        line = line[m.end():]
    elif not _B17_DIALOGUE_HEAD.match(line):
        return False
    rest = _B17_QUOTED.sub("", line)
    return len(_CJK.findall(rest)) <= _B17_TAG_MAX

# ---------- scan_slop 合并词条（P3–P8 同类，gen 模式 REVIEW 候选） ----------

# P3 套路修辞与凝固感 → C5 扩展（空气凝固/眼底闪过/填满/鬼魅）
_C5_ATMOS_EXT = re.compile(
    r"(?:眼(?:中|底|眸|眸深处|眸底)|眸(?:中|底|深处))(?:深处)?(?:闪过|掠过)一[丝抹道]|"
    r"空气(?:仿佛|骤然|在这一瞬间|像)*(?:凝固|静止)(?:了一般|了一样|了)?|"
    r"宛如鬼魅(?:一般)?|"
    r"寂静(?:仿佛)?有了重量|"
    r"(?:声音|尖叫声|警报声|轰鸣声|哭声)?填满(?:了整个|了整个?的?|了)?"
    r"[^，。；！？\n]{0,10}(?:空间|房间|屋子|走廊|大厅|室内|车厢)|"
     # 补 仿佛（fiction.md 二.5 明列"时间静止"，原正则只认"停止"）与
     # 凝固/静止两个动词、"连/也/都/终于/彻底"前缀；句读边界补 、――” 与空白。
     r"(?:连)?时间(?:也|都|终于|彻底)?"
     r"(?:仿佛|似乎|好像|稍怔|在这一刻|在这一瞬间)?"
     r"(?:停止|凝固|静止)了?(?:流动)?"
     r"(?=[。！？；，…，、——―\s”]|$)")

# P4 虚假升华 → C2 扩展（这一刻明白真谛一类 + 何尝不是）
_C2_GRAND_EXT = re.compile(
    r"(?:(?:在?这一(?:刻|瞬间|刹那)|此时此刻)[，,]?"
    r"(?:他|她|他们|她们|所有人)?[^，。；！？\n]{0,8}"
    r"(?:终于|仿佛|才)?(?:彻底|深刻|深深地?)?(?:明白|领悟|读懂)了?"
    r"|领悟到了?|这何尝不是)"
    r"[^。；！？\n]{0,25}"
    r"(?:人生|命运|时代|灵魂|人性|真谛|真理|意义|救赎|较量|宿命|生命的重量)")

# P6 装深沉时间感 → B16 扩展（许多年后才明白/世纪/失去意义）
_B16_TIME_EXT = re.compile(
    r"(?:(?:许多|很多|数|多|很久)年[以之]?后[，,]?"
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
    r"这是一个(?:非常|很|特别)?(?:好|棒|绝佳)的?问题|"
    r"希望(?:这个回答|这些建议|以上内容|以上解答|上述分析)?"
    r"对(?:您|你)(?:有所|有)?(?:帮助|启发)|"
    r"如(?:您|你)所(?:愿|见)|"
    r"当然可以[，。！]|"
    r"很高兴为(?:您|你)(?:解答|服务)?|"
    r"如果(?:您|你)还有(?:其他)?(?:问题|疑问)[，,]欢迎|"
    r"欢迎随时(?:向我)?提问")

# 各模式的报告集（见模块 docstring"模式"节；B11 需语义判断，prose/gen 均 REVIEW）
# gen 是生成期自查：覆盖全部文体，故含 B13–B18 叙事候选（REVIEW 级，须读上下文复核而非即改）。
FIX_RULES = {"prose": ("B4", "B6", "B10"), "fiction": ("B6", "B10"),
             "gen": ("B4", "B6", "B10")}
REVIEW_RULES = {
    "prose": ("B1", "B3", "B5", "B9", "B11", "B12"),
    "fiction": ("B1", "B5", "B9", "B16", "B13", "B15", "B17", "B18", "B14"),
    "gen": ("B1", "B3", "B5", "B9", "B11", "B13", "B14", "B15", "B16",
            "B17", "B18", "B12", "C2", "C4", "C5", "D2", "D3", "D4", "D5",
            "D6"),
}
# 逐行模板类规则：一行里命中多个模板只是同一句被重复覆盖，只报一条
_ONE_PER_LINE = ("C5", "D2", "D4")


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


def _mask_dialogue(line, in_quote):
    """把中文引号内的台词置换为等长空白，跨行延续。

    台词里的破折号、省略号属于角色声口，不参与叙述层判据（rules-full B5
    「台词中断与未完不改」）。按行配对会漏掉跨行引语：上一行开引号、下一行
    才收尾时，后一行整段被当成叙述，台词内的破折号就会误报。空行复位，
    避免个别未闭合的引号吃掉后文。
    """
    if not line.strip():
        return line, False
    out = []
    for ch in line:
        if ch == "“":
            in_quote = True
            out.append(" ")
        elif ch == "”":
            in_quote = False
            out.append(" ")
        else:
            out.append(" " if in_quote else ch)
    return "".join(out), in_quote


def _unclosed_note(text):
    """frontmatter 或代码围栏未闭合时返回告警文案，否则 None。

    状态机与 _iter_scannable_lines 逐行一致：不闭合时其后全文被跳过，
    扫描结果为空但退出码仍是 0——用户以为扫过了，实际整表作废。
    只在扫完打印提示，不产生命中、不改退出码。
    """
    fence_char = None
    fence_len = 0
    in_yaml = False
    for idx, raw in enumerate(text.splitlines(), 1):
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
    if in_yaml:
        return "frontmatter 未闭合（缺收尾 ---），其后全文未扫描"
    if fence_char is not None:
        return "代码围栏未闭合，围栏之后的正文未扫描"
    return None


def _iter_scannable_lines(text):
    """逐行产出 (行号, 原文, 屏蔽后文本)，跳过白名单区。"""
    fence_char = None
    fence_len = 0
    in_yaml = False
    in_quote = False
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
        body, in_quote = _mask_dialogue(raw, in_quote)
        yield idx, raw, _mask_line(body)


def _paragraph_heads(scannable):
    """产出每个段首 (行号, 段首文本)。

    空行、被白名单跳过的区块边界（围栏/表格/引用块/frontmatter）与整行被
    引语掩码都算分段——口径与 B3 的段首判定一致，CLI 的"未检出分段"提示
    也走这里：只数空行时，引用块前无空行的文本会出现"B3 已命中"与
    "B3 未执行"同轮并存的自相矛盾提示。
    """
    prev_blank = True
    prev_idx = None
    for idx, _raw, masked in scannable:
        stripped = masked.strip()
        if not stripped:
            prev_blank = True
            prev_idx = idx
            continue
        if prev_blank or (prev_idx is not None and idx != prev_idx + 1):
            yield idx, stripped
        prev_blank = False
        prev_idx = idx


def _paragraphs(scannable):
    """把可扫描行按段落聚合，产出 (段首行号, 段落文本)。

    软换行只是排版：同一段里三个以句号收尾的短句（推开门、放下包、坐下了）仍是
    段内连续三句。空行（或跳过的区块）断开成新段。
    """
    para, first = [], None
    prev = None
    for idx, _raw, masked in scannable:
        body = masked.strip()
        if not body:
            if para:
                yield first, "".join(para)
                para, first = [], None
            prev = idx
            continue
        if para and idx != prev + 1:
            yield first, "".join(para)
            para, first = [], None
        if not para:
            first = idx
        para.append(body)
        prev = idx
    if para:
        yield first, "".join(para)


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

    _raw_lines = text.splitlines()

    # _table_lines 预算一次。当前每次调用_same_paragraph_next 都重算全文，
    # 行末破折号稿件实测 O(n²)（16000 行 55s）。
    _table_line_set = set(_table_lines(_raw_lines))

    def _same_paragraph_next(line_no):
        """行号下一行是否为同段续行（软换行）。空行、EOF、或被白名单
        跳过的块边界（围栏、表格、引用块、frontmatter）都算段末，返回 None；
        否则返回该行的内容。"""
        k = line_no  # idx 是 1 基，_raw_lines 是 0 基
        if k >= len(_raw_lines):
            return None
        nxt = _raw_lines[k]
        if not nxt.strip():
            return None
        stripped = nxt.strip()
        if stripped.startswith(">"):  # 引用块
            return None
        opened = _FENCE_OPEN.match(nxt)  # 围栏起始
        if opened:
            return None
        if k in _table_line_set or stripped.startswith("|"):  # 表格行
            return None
        return nxt

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
        # 空行、或被白名单跳过的区块（围栅/表格/frontmatter）都断开成新段。
        # 只看 prev_blank 会漏掉"围栅前无空行"：那时下一段被并入上段，
        # 段首空评论不报。口径与 _paragraph_heads() 一致。
        for para_no, (idx, first_line) in enumerate(_paragraph_heads(scannable)):
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
                m10 = B10_HEAD.match(s)
                if m10:
                    hits.append(dict(line=idx, rule="B10", tier="FIX", snippet=m10.group(0),
                                     note="句首起手式，删后直接给判断"))

        # ---- B12（REVIEW）：句首空降宏观开场 ----
        if "B12" in review_on and not heading:
            for sent in _SENT_SPLIT.split(masked):
                s = sent.strip().lstrip(">*#- ")
                m = _MACRO_OPENER.match(s)
                if m:
                    hits.append(dict(line=idx, rule="B12", tier="REVIEW",
                                     snippet=m.group(0),
                                     note="句首宏观开场候选：核对句内是否含具体背景信息"))
                    break

        # ---- B1（REVIEW）：翻案腔候选词与隐性对举变体 ----
        if "B1" in review_on and not heading:
            # 变体匹配行级执行：句号分隔形态（"不是A。是B"）跨句界，
            # 按分句循环会漏报；台词引号已在 masked 中豁免。
            # 先跑变体；命中行不再跑 B1_WORDS——否则"其实不是A，只是B"
            # 会被两条路径重复报出（同规则同句双报）。
            variant_hit = False
            for m in _B1_VARIANT.finditer(masked):
                # 省"而"的"不是A，是B / 没有A，只有B"在小说里几乎全是事实清点
                # （"那不是拦，是量好了尺寸的堵""冰箱里没有可乐，只有啤酒"）：
                # 实测 48 份小说里 B1 的 6 处命中全部是这一形态，全是误报。
                # doc 的事实清点判据（A、B 能否拍成画面）须读语义，机械层不设
                # 候选；有"而"的"不是A，而是B"才是真翻案腔，两种模式都报。
                # 只豁免落在裸"是/只是/只有"上、且前面是逗号或空白的匹配。
                # 破折号与句号分隔形（"不是A——是B""不是A。是B"）doc 明列为病灶，
                # 不豁免。"纯粹是/更像是"承载抽象判断，任何模式下都是病灶。
                # 豁免尾必须跟上新增的"主语+是"形：B 标记可选代词后，
                # "他不是我的老板，他是我的客户"这类事实清点在 fiction 被误报
                # （裸"是"尾正则不认"他是"）。分隔符类只补 ；！、―，保持句号与
                # —— 形仍报（"那不是终点。是新的起点"是 doc 点名病灶）。
                # B 侧抽象（_b1_abstract_b）时撤销豁免——"这不是结束，是开始"
                # 不是清点。"不在A，在B"只在 B 侧抽象时报（"他不在家，在公司"
                # 是清点，放行）——豁免尾含"在"，否则该形态一律漏放。
                if (mode == "fiction" and "\u800c" not in m.group(0)
                        and re.search(
                            r"[\uff0c,\s\uff01\uff1b\u3001\u2015]"
                            r"(?:\u6211\u4eec|\u4f60\u4eec|\u4ed6\u4eec|\u5979\u4eec|"
                            r"\u5b83\u4eec|\u6211|\u4f60|\u4ed6|\u5979|\u5b83|"
                            r"\u8fd9|\u90a3)?"
                            r"(?:\u53ea\u6709|\u53ea\u662f|\u662f|\u5728)$",
                            m.group(0))):
                    if not _b1_abstract_b(_b1_b_side(masked, m)):
                        continue
                variant_hit = True
                hits.append(dict(line=idx, rule="B1", tier="REVIEW",
                                 snippet=m.group(0),
                                 note="隐性对举变体（不是A，(只/纯)是B/更是B/"
                                      "没有A只有B/看似A实则B——省“而”与句号、"
                                      "破折号分隔形态）：核对被否定的观点是否"
                                      "真实存在，不存在删否定留肯定；事实清点"
                                      "（冰箱里没有可乐，只有啤酒）与台词内不改"))
            if not variant_hit:
                for sent in _SENT_SPLIT.split(masked):
                    for w in B1_WORDS:
                        if w in sent:
                            # "其实/恰恰"单独出现是正常口语（"其实我早就知道了"），
                            # 只有同句带否定词时才构成翻案对举，否则无从"删否定留肯定"。
                            # 无否定结构不报——报了也没有可改的动作，纯噪声。
                            if not any(n in sent for n in _B1_NEGATION):
                                break
                            # "其实/恰恰"自身充当 B 侧引导词时不要求对举标记共现
                            # （判定见 _b1_self_contrast）；人类语料实测两处误报
                            # （朱自清"其实我那年已二十岁…"、王小波"男孩子其实
                            # 没有犯癔症"）都不具这些形态，仍静默。
                            # "而是"本身就是对举标记，不查此项——它正是主路径
                            # _B1_VARIANT 用 (?!而) 排除后交给本路径覆盖的形态。
                            if (w != "\u800c\u662f"
                                    and not any(mk in sent for mk in _B1_CONTRAST)
                                    and not _b1_self_contrast(w, sent)):
                                break
                            hits.append(dict(
                                line=idx, rule="B1", tier="REVIEW",
                                snippet=sent.strip()[:40],
                                note=f"含“{w}”且与否定词同句：核对被否定的观点"
                                     f"是否真实存在，不存在删否定留肯定；"
                                     f"角色台词内不改"))
                            break

        # ---- B5（REVIEW）：叙述破折号逐处复核用途 ----
        # 数字之间的连接号（1864—1928、第 3—5 章）是范围标记，不是叙述破折号；
        # 台词内的破折号已在 _mask_dialogue 中整体屏蔽。
        # 只对 Markdown 标题行（# 起首）免责：整行 **粗体** 在正文里是强调
        # 不是小标题，`**他说——不，他什么都没说**` 整行跳过等于放病灶过关。
        if "B5" in review_on and not _HEADING_MD.match(masked.strip()):
            # 行末破折号（话没说完——）是未完与中断的形态，正是本条豁免的对象；
            # 右侧没有内容时无从改用完整句，报了只会逼人把合法的未完句改掉。
            # 只判行内最后一个破折号：前面的破折号若右侧有内容，那个内容必然
            # 落在最后一个破折号之前或之后，取最后一个即可覆盖，且避免每个
            # 破折号都切片到行尾（50k 破折号单行会退化成 O(n²)，实测 26 秒）。
            # 台词内的破折号已由 _mask_dialogue 屏蔽。
            _last_dash = None
            for dm in _DASH_NOT_RANGE.finditer(masked):
                _last_dash = dm
            if _last_dash is not None:
                _tail = masked[_last_dash.end():].strip(_B5_TAIL_PUNCT)
                if not _tail:
                    # 本行右侧为空。软换行时右侧在同一段的下一行，那种情况
                    # 不是未完句，照报；段末（空行或 EOF）才是未完。
                    # 但硬换行的纯文本小说稿里，未完句在行末、下一行是同一句
                    # 的延续（"她话说到一半——\n突然停下。"），跨软换行取右侧
                    # 会把合法的未完句全判成病灶。破折号后紧跟 ！？。… 的是
                    # 被打断/截断的收束（鲁迅"啪，吧——！"），同样不跨行取右侧。
                    if re.search(r"[\uff01\uff1f\u3002\u2026]" + chr(0x2014) + r"*$",
                                 masked.rstrip()):
                        _tail = ""
                    else:
                        _nxt = _same_paragraph_next(idx)
                        if _nxt is not None:
                            _tail = _nxt.strip(_B5_TAIL_PUNCT)
                if _tail:
                    hits.append(dict(
                        line=idx, rule="B5", tier="REVIEW",
                        snippet=stripped[:40],
                        note="叙述破折号：若右侧只是解释、列举、同位、原因、结果或补充，"
                             "保留内容并改用完整句或常规标点；台词中断与未完不改"))

        # ---- gen 层（REVIEW）：既有规则的机械候选，逐处报出 ----
        if "B9" in review_on:
            for m in _B9_SIMILE.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B9", tier="REVIEW", snippet=m.group(0),
                    note="喻体候选：喻体与本体共享具体属性、删后解释力不减即为装饰，"
                         "删掉或直说；承载解释的保留"))
            # 陈词套式单处即判，与密度口径分开（doc：套式"单处即判，与密度无关"）
            for m in _B9_CLICHE.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B9", tier="REVIEW", snippet=m.group(0),
                    note="陈词套式候选：换个场景还能原样用的成套比喻，零增量；"
                         "换成这个场景独有的具体属性"))
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
            m = _C5_ATMOS.search(masked)
            if m:
                hits.append(dict(
                    line=idx, rule="C5", tier="REVIEW", snippet=m.group(0),
                    note="空泛气氛总结候选：没有新增感知、动作或结果就删，"
                         "或换成下一件可感知的事"))
            for m in _C5_ATMOS_EXT.finditer(masked):
                hits.append(dict(
                    line=idx, rule="C5", tier="REVIEW", snippet=m.group(0),
                    note="套路修辞候选（空气凝固/眼底闪过/声音填满一类）："
                         "删套路词，写具体光影、声音或动作"))
        if "D2" in review_on:
            for sent in _SENT_SPLIT.split(masked):
                s = sent.strip().lstrip(">*#- ")
                m_open = _D2_HEAD.match(s)
                if m_open:
                    hits.append(dict(
                        line=idx, rule="D2", tier="REVIEW", snippet=s[:20],
                        note="服务腔开场：首句直接给结论，从事实或判断起句"))
                m_sum = _D2_SUMMARY_HEAD.match(s)
                if m_sum:
                    hits.append(dict(
                        line=idx, rule="D2", tier="REVIEW", snippet=m_sum.group(0),
                        note="总结套话开场：'综上所述/由此可见'是空转过渡，"
                             "删掉让结论直接起句"))
            # 收尾：整句尾部为客服客套或万能废话才报（句中形态不报）
            tail_probe = re.sub(r"[ \t\r\n]+$", "", stripped).rstrip(_TRAILING_PUNCT)
            m_tail = _D2_TAIL.search(tail_probe)
            if m_tail:
                hits.append(dict(
                    line=idx, rule="D2", tier="REVIEW", snippet=m_tail.group(0),
                    note="客服收尾套话：末句停在事实、明确建议或行动边界"))
            if _D2_TAIL_STANDALONE.match(tail_probe):
                hits.append(dict(
                    line=idx, rule="D2", tier="REVIEW", snippet=tail_probe,
                    note="'以上，供参考'式空转收尾：删掉，停在实质内容"))
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
            tail_probe = re.sub(r"[ \t\r\n]+$", "", stripped).rstrip(_TRAILING_PUNCT)
            if _D4_TAIL.match(tail_probe):
                hits.append(dict(
                    line=idx, rule="D4", tier="REVIEW", snippet=tail_probe,
                    note="整句式万能收尾：'因人而异'一类消解信息的独立结尾，"
                         "写清判断条件与权衡基准"))
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
                # 客观声源的低吼（引擎、风、兽群、机器）是环境描写，
                # fiction.md 明言放行。发声反应套板的主语只能是人。
                _pre = masked[max(0, m.start() - 8):m.start()]
                if _B15_OBJECTIVE_SOURCE.search(_pre):
                    continue
                hits.append(dict(
                    line=idx, rule="B15", tier="REVIEW", snippet=m.group(0),
                    note="舞台剧抽搐候选：改成定住与动作停顿；"
                         "对抗场景用精准动量受力动词"))
        if "B16" in review_on:
            match = _B16_LOOP.search(masked)
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
            for m in _B16_SUOWEI.finditer(masked):
                hits.append(dict(
                    line=idx, rule="B16", tier="REVIEW", snippet=m.group(0),
                    note="生硬点题候选（所谓X不过是Y）：直接陈述事实，"
                         "不用'所谓'绕一圈再下定义"))
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
                # fiction.md 二.9：角色在数是情节（孩子数水滴入睡、哨兵数更声），
                # 与作者给动作数拍子是两件事。同句里有人物在做"数"这个动作时，
                # 计数是角色行为，放行。
                _pre = masked[max(0, m.start() - 12):m.start()]
                if _B18_CHARACTER_COUNTING.search(_pre + m.group(0)):
                    continue
                hits.append(dict(
                    line=idx, rule="B18", tier="REVIEW", snippet=m.group(0),
                    note="计数癖候选：作者数拍子改体感或物件变化；"
                         "角色在数是情节、数量变化是发现，保留"))

        # ---- B4a：提示语＋冒号 ----
        # 只对句首命中发 FIX。句中命中
        # （"这个方案的核心是：三个模块。"）
        # 按 note 教的"不带信息则删"会删出病句，
        # 与 rules-full B4"总说分说不改"矛盾，降为 REVIEW
        # 交人判。
        if "B4" in fix_on and not heading:
            for p in B4A_PROMPTS:
                for m in re.finditer(re.escape(p) + r"\s*[:：]", masked):
                    at_head = not masked[:m.start()].strip()
                    hits.append(dict(
                        line=idx, rule="B4",
                        tier="FIX" if at_head else "REVIEW",
                        snippet=m.group(0),
                        note=("提示语引出：不带信息则删，"
                              "承接上文换标点" if at_head else
                              "提示语落在句中：判断冒号前"
                              "是否为空转，总说分说不改")))
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
    # 连珠按"段内连续句"判，不按行判：软换行只是排版，同一段里的三个短句
    # 仍是三句。空行（或跳过区）断开成新段。
    if "B17" in review_on:
        for idx, para in _paragraphs(scannable):
            sents = [s.strip() for s in _SENT_SPLIT.split(para) if s.strip()]
            run = best_run = 0
            cur = None
            for s in sents:
                head = s[:1]
                short = len(_CJK.findall(s)) <= _B17_MICRO_SENT_MAX
                if _B17_PRONOUN_HEAD.match(head) and short:
                    run = run + 1 if head == cur else 1
                    cur = head
                else:
                    run, cur = 0, None
                best_run = max(best_run, run)
            if best_run >= 3:
                hits.append(dict(
                    line=idx, rule="B17", tier="REVIEW", snippet=para[:40],
                    note=f"句首代词连珠（段内连续 {best_run} 句）：一主串多动，"
                         "主语带出一次靠动词链顺承"))
            # 句内主语复现：同句相邻分句同一代词起头（“她知道，她也明白”）
            for sent in sents:
                clauses = [c.strip() for c in _CLAUSE_SPLIT.split(sent) if c.strip()]
                intra_run = []
                cur = None
                prev = None
                for c in clauses:
                    # 否定-对比分句（“不是A，他是B”）是对举不是口吃，不进复现串
                    if (prev is not None and _B17_CONTRAST_TAIL.match(c)
                            and _B17_CONTRAST_NEG.search(prev)):
                        prev = c
                        continue
                    head = (c[:1]
                            if _B17_INTRA_HEAD.match(c)
                            and not _B17_POSSESSIVE.match(c) else None)
                    if head and head == cur:
                        intra_run.append(c)
                    else:
                        if len(intra_run) >= 2:
                            break
                        intra_run = [c] if head else []
                        cur = head
                    prev = c
                if len(intra_run) >= 2:
                    hits.append(dict(
                        line=idx, rule="B17", tier="REVIEW",
                        snippet="，".join(c[:20] for c in intra_run),
                        note="句内主语复现（同句相邻分句同一代词起头）："
                             "承前省删后一个主语或合并动词链；有意的强调、"
                             "对比、递进复用放行"))
        # 标签密度的分母按 fiction.md 一.5 的"对白行"定义：整行一句引语、
        # 引语外只挂短标签、或行首是"说话人＋冒号＋引语"。内联引语行
        # （叙述中夹"他说：'……'"）不是独行对白，计入分母会把"每句独行对白
        # 都挂标签"这种真病灶稀释成合格（实测 6 标签 / 6 独行 + 10 内联行
        # → 分母 16，违规消失）。
        # 分母补"叙述+说+引语"行（口径同 _is_dialogue_line：引号外是短标签
        # 才算，动作行"她把碗放下。"照旧打断连发）
        n_dialogue = sum(1 for _, raw, _ in scannable
                         if _is_dialogue_line(raw.strip())
                         or _B17_TAG_QUOTE.search(raw.strip()))
        # "全篇转述体"要看的是有没有直接引语，与分母口径不同，单独数：
        # 全文只有内联引语时 n_dialogue 为 0，会被误判成"没有一句直接引语"。
        n_quoted = sum(1 for _, raw, _ in scannable
                       if _HAS_QUOTED_SPEECH.search(raw))
        n_tags = sum(len(_B17_TAG.findall(masked)) for _, _, masked in scannable)
        if n_dialogue >= 4 and n_tags > n_dialogue * 0.5:
            first_tag_line = next(
                (idx for idx, _, masked in scannable
                 if _B17_TAG.search(masked)), 1)
            hits.append(dict(
                line=first_tag_line, rule="B17", tier="REVIEW",
                snippet=f"{n_tags} 个说类标签 / {n_dialogue} 行独行对白",
                note="对白标签密度超标：语境可判的独行对白直接呈现；"
                     "力度用动作替标签干活"))
        # 全篇转述体：直接引语一行没有，全靠"他说……她说……"转述。
        # 这是把③间接转述当主调，节奏比引语连发更平（fiction.md 一.5）。
        # 阈值按实测取：病灶稿 33 个标签 / 904 字；语料里其余 97 篇未命中。
        if n_quoted == 0 and n_tags >= 8:
            first_tag_line = next(
                (idx for idx, _, masked in scannable
                 if _B17_TAG.search(masked)), 1)
            hits.append(dict(
                line=first_tag_line, rule="B17", tier="REVIEW",
                snippet=f"{n_tags} 个说类标签 / 0 行直接引语",
                note="全篇转述体：整场对白都写成'他说……她说……'，"
                     "没有一句直接引语。间接转述只用来压程序性拉锯那几轮，"
                     "交锋、告白与转折拍要给回直接引语"))
        # 问答乒乓：连续 ≥5 行对白行且行间无叙述，即整场戏只由问答构成
        ping_run = []

        # 省略号怯场：对白行统一以"……"开头。判据是一致性而非密度——
        # 鲁迅 228 行对白里只有 1 行以省略号开头（0.4%），省略号总量反而
        # 3.84/千字高于生成稿；实测最差一篇 106 行里 99 行（93%）以省略号
        # 开头，是把省略号当统一怯场标记。剧本体（"护士：……"）不含引号，
        # _HAS_QUOTED_SPEECH 认不出，故对白行另按"行首说话人＋冒号"数。
        _dlg_lines, _ell_lead = 0, []
        for _idx, _raw, _masked in scannable:
            _s = _raw.strip()
            if not _s:
                continue
            if not (_is_dialogue_line(_s) or _B17_SPEAKER_HEAD.match(_s)
                    or _B17_SCRIPT_HEAD.match(_s)):
                continue
            _dlg_lines += 1
            _body = _B17_SPEAKER_HEAD.sub("", _s)
            _body = _B17_SCRIPT_HEAD.sub("", _body)
            if _body.lstrip(chr(0x201C)).startswith(chr(0x2026) + chr(0x2026)):
                _ell_lead.append((_idx, _s))
        if _dlg_lines >= 6 and len(_ell_lead) * 100 >= _dlg_lines * 15:
            hits.append(dict(
                line=_ell_lead[0][0], rule="B17", tier="REVIEW",
                snippet=f"{len(_ell_lead)}/{_dlg_lines} 行对白以省略号开头",
                note="省略号怯场：整场戏把'……'当统一怯场标记。没说完的话"
                     "换着写——话头断在半句由动作接走、破折号中断、或让叙述"
                     "交代中断（'后面半句他没说'）；省略号留给最疼的那一两处"))

        def _flush_pingpong():
            if len(ping_run) >= _B17_PINGPONG_MIN:
                hits.append(dict(
                    line=ping_run[0][0], rule="B17", tier="REVIEW",
                    snippet=ping_run[0][1][:30],
                    note=f"问答乒乓（连续 {len(ping_run)} 行对白、行间无叙述）："
                         "确认型、递进型回合降级为嵌入叙述或间接转述，"
                         "只留每句都推进信息的独行"))

        for idx, raw, masked in scannable:
            line = raw.strip()
            if not line:
                continue  # 空行是小说常规分段，不打断对白连发
            if _is_dialogue_line(line):
                ping_run.append((idx, line))
            else:
                _flush_pingpong()
                ping_run = []
        _flush_pingpong()

    # ---- B9 句末明喻：全文密度超标才报一次（单处不报，避免误伤人写） ----
    if "B9" in review_on:
        # 句子列表必须走 masked：白名单（引用块、代码、表格、URL、frontmatter）
        # 是 docstring 声明的绝对豁免，吃 raw text 等于把引用块里的比喻也算进密度。
        _scan_text = "\n".join(m for _, _, m in scannable)
        # 不能写 re.findall(r"[^。！？\n]+[。！？]")：没有句读的长行会让
        # 它逐字符回溯，O(n²)（50k 破折号单行实测 15.7 秒全耗在这里）。
        # 按终止符迭代切片是 O(n)，且句末终止符保留在片段里（_B9_TAIL 需要）。
        _sents = []
        _start = 0
        for _m in re.finditer(r"[。！？\n]", _scan_text):
            _seg = _scan_text[_start:_m.end()].strip()
            if len(_seg) >= 4:
                _sents.append(_seg)
            _start = _m.end()
        _tails = [s for s in _sents if _B9_TAIL.search(s)]
        if _sents and len(_tails) >= _B9_TAIL_MIN \
                and len(_tails) / len(_sents) >= _B9_TAIL_RATIO:
            hits.append(dict(
                line=1, rule="B9", tier="REVIEW",
                snippet=_tails[0][:40],
                note=f"句末明喻过密（全文 {len(_tails)} 处 / "
                     f"{len(_sents)} 句 = {100 * len(_tails) / len(_sents):.0f}%）："
                     "整篇每段都用‘，像X’收句是节拍器；留几处最有效的，"
                     "其余改直述或让实体动作承接"))

    # 同规则同行只报一条：D2 的开场与收尾、D4 的万能收尾、C5 的气氛与
    # 修辞模板都是逐行模板匹配，一行里同时命中只是同一句被两个模板覆盖
    # （"希望对你有帮助。"既是收尾套话又像服务腔），报两条等于虚增计数
    seen = set()
    kept = []
    for h in hits:
        key = (h["rule"], h["line"])
        if h["rule"] in _ONE_PER_LINE:
            if key in seen:
                continue
            seen.add(key)
        kept.append(h)
    hits = kept

    # 同点双报抑制：仅当 B4 的提示语本身就是 B3 的触发语时（词表重叠：
    # "关键在于："），删掉提示语后 B3 的触发对象才确实不复存在。B4/B10
    # 命中在行内其他位置时（如"原因如下："），B3 的触发语删后照旧存在，
    # 必须照报，否则同行的 B3 病灶被吞
    if "B3" in review_on:
        drop_lines = {h["line"] for h in hits
                      if h["rule"] in ("B4", "B10")
                      and any(w in h["snippet"] for w in B3_OPENERS)}
        hits = [h for h in hits
                if not (h["rule"] == "B3" and h["line"] in drop_lines)]

    return hits


def main():
    parser = argparse.ArgumentParser(
        description="机械规则扫描器（FIX：B4/B6/B10；REVIEW：B1/B3/B5/B9/B11/B12 与 fiction 的 B13–B18、gen 的 C/D 层）")
    parser.add_argument("files", nargs="*", help="待扫描文件或目录（目录递归）；单独的 - 读 stdin")
    parser.add_argument("--mode", choices=("prose", "fiction", "gen"), default="prose",
                        help="prose=论述清理（B1/B3/B4/B5/B6/B9/B10/B11/B12）；"
                             "fiction=fiction 清理（B1/B5/B6/B9/B13–B18）；"
                             "gen=生成期自查（prose 集加 B13–B18 与 C/D 层）")
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
                if len(_lines) > 1:
                    # 分段口径与 B3 判定一致（空行或引用/代码/表格边界都算分段）：
                    # 只数空行时，引用块前无空行的文本 B3 已命中，提示却仍说"未执行"
                    _n_para = sum(1 for _ in _paragraph_heads(
                        _iter_scannable_lines(text)))
                    if _n_para < 2:
                        print(f"# 提示：{name} 未检出分段（空行或引用/代码/表格边界），"
                              f"B3 段首判定不执行")
            _note = _unclosed_note(text)
            if _note:
                print(f"# 提示：{name} {_note}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
