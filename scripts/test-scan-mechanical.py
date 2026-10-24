"""scan-mechanical.py 自测：回归集红灯测试。

设计原则：先证明脚本能捕获已知缺陷（红灯真红），再采信"零命中"结论。
- 人类组（A1–A5、C1）：FIX 级必须 0 命中；
  A4 的叙述破折号报 B5 候选（候选不授权自动改写）。"其实"单独出现是正常
  口语（rules-full B1：与否定词同句且与对举标记共现才算对举），不报候选。
- AI 腔组 AI-1：必须命中 B10(FIX)＋B1/B9(REVIEW)——测不出即脚本失效。
  AI-1 为单段文本，B3 按规则定义（非首段）不触发。
- AI 腔组 AI-2：病灶是 B2（非机械规则），必须 0 命中——误命中即误伤。
- 种植病灶组：B1/B3/B4/B5/B6/B11/B12/B16 各一处，缺一即脚本漏检。
- 边界组：引用与行内引文豁免、行内代码、表格、B4 触发词、BOM、GBK、B3 分段。

运行：python scripts/test-scan-mechanical.py
"""
import importlib.util
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import _loader

_loader.ensure_utf8()

_spec = importlib.util.spec_from_file_location(
    "scan_mechanical", Path(__file__).resolve().parent / "scan-mechanical.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
scan = _mod.scan
FIX_RULES = _mod.FIX_RULES
REVIEW_RULES = _mod.REVIEW_RULES

# ---------- 回归集：人类组 ----------
A1 = "部署完成后先看日志。Kafka 消费延迟超过两秒，基本是消费者组 rebalance 没结束，等一会儿就好；持续上涨则是处理逻辑卡住了，多半出在数据库连接池。我们上个月踩过这个坑，把连接池从 20 调到 50，延迟就平了。"
A2 = "我妈总说冰箱第二层的酸奶别动，那是给猫拌药用的。猫今年十四岁，肾功能不太好，每天要吃半片药，碾碎了拌在酸奶里它才肯吃。上回我半夜偷喝了一罐，第二天她数了数罐数，什么也没说，把新买的一排全放进了带锁的保鲜盒。"
A3 = "换刹车片先做三件事。首先松掉手刹，用楔子固定住后轮；其次拆下卡钳螺栓，把卡钳整个挂到悬挂上，别让它吊着刹车油管；最后压回活塞，换上新片。装回去的顺序反过来就行。"
A4 = "这个方案被质疑得最多的一点是扩展性，但真正难办的其实是权限模型。数据库的分表方案像切蛋糕，切得再均匀，刀数多了哪个客人都不满意——三张表以内随便玩，上了十张表就得认真考虑分布式事务的代价。"
A5 = "上线当晚没有一个人回家。这听起来夸张，但监控大屏上的曲线确实在爬。值班室里泡面味道散不掉，谁也没提要走的事。"
C1 = "为什么大家都用消息队列？因为削峰填谷是刚需。提升吞吐，平滑峰值，解耦服务，这三件事它全占了。"

# ---------- 回归集：AI 腔组 ----------
AI_1 = "说白了，这个系统的核心不是技术，而是人。首先，让我们理解背景。值得注意的是，配置管理往往被忽视。它就像一位永不疲倦的管家，不仅守护数据，更守护信任。"
AI_2 = "新版本带来了显著的性能提升。压测数据显示 P99 延迟从 800ms 降到了 120ms。这意味着团队的努力得到了回报。"

# ---------- 种植病灶（红灯组：必须全部捕获） ----------
PLANTED_B4A = "一句话总结：这个方案成本太高。"
PLANTED_B4B = "我见过的几种典型场景：\n\n- 场景一\n- 场景二"
PLANTED_B6 = "## 一、先找出模糊在哪里\n\n正文。\n\n## 二、把需求写成模块\n\n正文。\n\n## 三、合成第一版 prompt"
PLANTED_B11 = "系统负责采集、存储、展示。"
PLANTED_B12 = "在当今快速发展的时代，效率成为核心竞争力。"
PLANTED_B12_BACKGROUND = "随着供应商切换完成，本月起账单走新渠道。"
PLANTED_B12_TODAY = "在这个行业野蛮生长的今天，效率成了唯一信仰。"
PLANTED_B1 = "真正的瓶颈不是技术，而是耐心。"
PLANTED_B3 = "第一段说完了。\n\n值得注意的是，配置管理往往被忽视。"
PLANTED_B5 = "答案已经很清楚——继续等。"
PLANTED_B5_SINGLE = "答案已经很清楚—继续等。"
PLANTED_F7 = "里面沉默了很久，久到他以为不会有回应。"
PLANTED_F7_PERIOD = "里面沉默了很久。久到他以为不会有回应。"
PLANTED_F7_SEMICOLON = "里面沉默了很久；久到他以为不会有回应。"

# ---------- 白名单豁免组（FIX 级预期 0 命中） ----------
WHITELIST = """---
title: 说白了，这是 frontmatter
---

```python
# 说白了，注释里随便写
items = ["采集、存储、展示"]
```

| 列 | 说白了 |
|---|---|

`说白了` 是行内代码。

https://example.com/说白了、说穿了、先看这里

- 采集、存储、展示（列表内部豁免 B11）

## 一、只有

## 二、两个编号（不足 3 个，B6 不触发）
"""

failures = []


def check(name, text, expect_fix, expect_review=(), expect_counts=None):
    hits = scan(text)
    got_fix = sorted({h["rule"] for h in hits if h["tier"] == "FIX"})
    got_review = sorted({h["rule"] for h in hits if h["tier"] == "REVIEW"})
    if got_fix != sorted(expect_fix) or got_review != sorted(expect_review):
        failures.append(
            f"{name}: 预期 FIX {sorted(expect_fix) or '无'} REVIEW {sorted(expect_review) or '无'}，"
            f"实际 FIX {got_fix or '无'} REVIEW {got_review or '无'}\n"
            + "\n".join(f"  行{h['line']} {h['rule']} {h['tier']} {h['snippet']}"
                        for h in hits))
    if expect_counts is not None:
        got_counts = Counter(h["rule"] for h in hits)
        if got_counts != Counter(expect_counts):
            failures.append(
                f"{name}: 预期命中数 {dict(expect_counts)}，实际 {dict(got_counts)}")


# 人类组：FIX 零命中是绿灯，但须先由红灯组证明脚本没瞎
for name, t in [("A1", A1), ("A2", A2), ("A3", A3), ("A5", A5), ("C1", C1)]:
    check(name, t, [])
check("A4", A4, [], ["B5"])

# AI 腔组
check("AI-1", AI_1, ["B10"], ["B1", "B9"])
check("AI-2", AI_2, [])

# 种植病灶：漏一个都是红灯
check("种植-B1", PLANTED_B1, [], ["B1"])
check("种植-B3", PLANTED_B3, [], ["B3"])
check("种植-B4a", PLANTED_B4A, ["B4"])
check("种植-B4b", PLANTED_B4B, [], ["B4"])
check("种植-B5", PLANTED_B5, [], ["B5"], {"B5": 1})
check("种植-B5-单破折号", PLANTED_B5_SINGLE, [], ["B5"], {"B5": 1})
check("种植-B6", PLANTED_B6, ["B6"], [], {"B6": 3})
check("种植-B11", PLANTED_B11, [], ["B11"], {"B11": 1})
check("种植-B12", PLANTED_B12, [], ["B12"], {"B12": 1})
check("种植-B12-带背景", PLANTED_B12_BACKGROUND, [])  # 随着句带具体事件，零命中
check("种植-B12-在今天", PLANTED_B12_TODAY, [], ["B12"], {"B12": 1})
# "时代/背景/环境 + 下"这条分支：没有这一正一反，把"下"改回可选完全不转红
check("种植-B12-时代广场不报", "在时代广场见面，然后去了中央公园。", [], [])
check("种植-B12-背景下报", "在那个时代背景下，效率成了唯一信仰。", [], ["B12"], {"B12": 1})
check("种植-B12-环境里不报", "在环境里走动，鞋底带了沙。", [], [])

# ---------- B1 隐性对举变体（生成文本实测漏网形态：省“而”翻案腔） ----------
check("种植-B1只是变体", "他不是不在意，只是习惯了把在意藏起来。", [], ["B1"], {"B1": 1})
check("种植-B1那不是是", "那不是裙子，是她妈妈的旧窗帘。", [], ["B1"], {"B1": 1})
check("种植-B1更是变体", "这不仅是一次升级，更是一次反思。", [], ["B1"], {"B1": 1})
check("种植-B1纯粹是变体", "她要的不是道歉，纯粹是一句实话。", [], ["B1"], {"B1": 1})
check("种植-B1破折号形态", "那不是道歉——是宣战。", [], ["B1", "B5"])
# 豁免：转折枚举不是对举；台词在引文掩码内；口语“不是A，是B”只作 REVIEW 候选
check("B1变体-转折豁免", "他不是本地人，但城里的每条胡同他都熟。", [])
check("B1变体-枚举豁免", "拿走文件的不是他就是他哥，办公室里再没别人。", [])
check("B1变体-台词豁免", "老张敲了敲桌子：“这不是钱的问题，是规矩问题。”", [])
check("B1变体-而是不双报", "真正的瓶颈不是技术，而是耐心。", [], ["B1"], {"B1": 1})
check("种植-B1与其说不如说-移交人工", "这与其说是理性抉择，不如说是骨子里的恐惧。", [], [], {})
# 叙事层的"不是A，只是B"（省"而"变体）：生理动作被写成对举即报
check("种植-B1音节只是呼吸", "她发出一声不是话语的音节，只是呼吸卡在喉间。",
      [], ["B1"], {"B1": 1})
check("B1音节-改后不报", "那声呼吸卡在喉间。", [], [])
check("种植-B1谈不上更多是-移交人工", "他谈不上喜欢画画，更多是为了打发时间。", [], [], {})
check("B1变体-单纯不如说不报", "与其抱怨规则，不如先把这局打完。", [])

# ---------- B1 变体扩展（句号/单破折号分隔 + 没有/看似/不在于同类 + 是不是误报回归） ----------
check("B1变体-句号形态", "那不是雨。是有人在楼上晾衣服。", [], ["B1"], {"B1": 1})
check("B1变体-句号形态-没有只有", "世上没有奇迹。只有不肯认输的人。", [], ["B1"], {"B1": 1})
check("B1变体-单破折号形态", "那不是道歉—是宣战。", [], ["B1", "B5"], {"B1": 1, "B5": 1})
check("B1变体-没有只有", "没有永远的朋友，只有永远的利益。", [], ["B1"], {"B1": 1})
check("B1变体-没有什么只是", "没有什么岁月静好，只是有人替你负重前行。", [], ["B1"], {"B1": 1})
check("B1变体-不在于而在于-移交人工", "真正的胜负不在于招式有多华丽，而在于能否一击毙命。", [], [], {})
check("B1变体-表面看似实则-移交人工", "表面看似风平浪静，实则各方势力早已磨刀霍霍。", [], [], {})
check("B1变体-看似骨子里-移交人工", "他表面看似玩世不恭，骨子里却极有原则。", [], [], {})
check("B1变体-反倒是", "这非但不是妥协，反倒是宣战。", [], ["B1"], {"B1": 1})
# 是不是疑问形不得误判为对举（句号形与逗号形各一，后者为历史误报回归锁）
check("B1变体-是不是疑问-句号", "他不确定那是不是猫。是他看错了。", [])
check("B1变体-是不是疑问-逗号", "她问这是不是真的，是真的她又该怎么办。", [])
# "其实"单独出现是正常口语，不报（rules-full B1）；与否定词同句、且与对举标记共现才构成对举候选
check("B1-其实单独不报", "这个方案被质疑得最多的一点是扩展性，但真正难办的其实是权限模型。", [])
# A4："其实/恰恰"与否定词同句还不够，还需与对举标记共现。
# 人类语料实测两处误报（朱自清、王小波）都是普通否定句。
check("B1-其实无对举不报", "其实没有你说的那么复杂，先跑一遍压测就知道。", [], [])
check("B1-其实带更是候选", "其实他不是不想帮，更是不能帮。", [], ["B1"], {"B1": 1})
check("B1-恰恰无对举不报", "男孩子其实没有犯癔症，就是太累了。", [], [])
# 没有……只有……的事实清点：同形不可机械区分，报 REVIEW 候选交复核（note 教判据）
# ——候选不授权自动改写
check("B1变体-事实清点候选", "冰箱里没有可乐，只有啤酒。", [], ["B1"], {"B1": 1})
# 动作否定（趋近-收回结构）：合法描写，与抽象对举同形，机器报 REVIEW 候选交人判（B1 小说形判据）
check("B1变体-动作否定候选", "她没有握上去，只是把手收回了掌心。", [], ["B1"], {"B1": 1})
# 抽象对举（两侧都是抽象词）：真病灶，必须报
check("B1变体-抽象对举", "没有安慰，只有沉默。", [], ["B1"], {"B1": 1})
# 跨句无对举关系不误报：没有 A。是 B（follow 受限，只有/只是/唯一直连才报）
check("B1变体-没有是-B不报", "冰箱里没有可乐。是我上次喝完了。", [])

# 白名单（frontmatter 里的"其实"等不在豁免列，此处只验 FIX 级零误伤）
check("白名单豁免", WHITELIST, [])

# ---------- 引用块与引文豁免（引的是他人原文，清理模式不得改动） ----------
QUOTE_FIRST = "> 值得注意的是，这段引自他人文章。采集、存储、展示、分析。\n"
QUOTE_MID = "正文一句交代背景。\n\n> 值得注意的是，配置管理往往被忽视。\n"
check("引用块-首", QUOTE_FIRST, [])
check("引用块-段中", QUOTE_MID, [])

INLINE_QUOTE = "他说：“一句话总结：采集、存储、展示——不是归档，而是上线。”"
DOUBLE_BACKTICK = "``采集、存储、展示`` 是配置原文。"
TABLE_NO_LEADING_PIPE = "名称 | 说明\n--- | ---\n采集、存储、展示 | 说白了，这是原始表格内容\n"
check("行内引文", INLINE_QUOTE, [])
check("双反引号代码", DOUBLE_BACKTICK, [])
check("无前导竖线表格", TABLE_NO_LEADING_PIPE, [])

FOUR_BACKTICK_FENCE = """````markdown
```
说白了，采集、存储、展示。
````
"""
MIXED_FENCE = """```text
~~~
说白了，采集、存储、展示。
```
"""
check("四反引号围栏", FOUR_BACKTICK_FENCE, [])
check("混合围栏字符", MIXED_FENCE, [])

LIST_CONTINUATION = """- 本项包括：
  采集、存储、展示。
"""
check("列表续行", LIST_CONTINUATION, [])

# ---------- B4 触发词不越规则文本（脚本不得扩权） ----------
check("B4-换句话说", "留存率涨到了72%。换句话说：产品找到了PMF。\n", [])
check("B4-结论如下", "结论如下：这个方案不行。\n", [])
check("B3-未授权开头", "第一段交代背景。\n\n意味着，配置仍需人工维护。\n", [])

# B6 要求连续编号小标题；普通小标题打断后，散落的三个编号不得合并计数。
SCATTERED_B6 = """## 一、第一部分

正文。

## 普通标题

正文。

## 二、第二部分

正文。

## 另一个标题

## 三、第三部分
"""
check("B6-分散编号", SCATTERED_B6, [])

MIXED_LEVEL_B6 = """## 一、一级

### 二、二级

## 三、又回一级
"""
check("B6-混合标题层级", MIXED_LEVEL_B6, [])

# 触发词一致性：B4A_PROMPTS 必须在全量规范 rules-full.md 的 B4 定义中
_RULES_FULL = (Path(__file__).resolve().parent.parent / "references" / "rules-full.md").read_text(encoding="utf-8")
for _w in ("一句话总结", "核心是"):
    if _w not in _RULES_FULL:
        failures.append(f"触发词缺失：核心提示词「{_w}」不在 rules-full.md 的 B4 定义中")

# ---------- 模式感知 ----------
# fixture 取自公版语料（呼蘭河傳）真实段落：含多处顿号串，是人类小说的正常写法。
# fiction.md 规定 fiction 清理不带入 B2/B3/B4/B11，扫描器 --mode fiction 必须抑制；
# B6/B1 在带入集内，末尾种植的编号小标题与"而是"句必须照报。
FICTION_FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "fiction-sample.txt"
                   ).read_text(encoding="utf-8")


def check_mode(name, text, mode, expect_fix, expect_review=(),
               expect_counts=None):
    hits = scan(text, mode=mode)
    got_fix = sorted({h["rule"] for h in hits if h["tier"] == "FIX"})
    got_review = sorted({h["rule"] for h in hits if h["tier"] == "REVIEW"})
    if got_fix != sorted(expect_fix) or got_review != sorted(expect_review):
        failures.append(
            f"{name}（mode={mode}）: 预期 FIX {sorted(expect_fix) or '无'} "
            f"REVIEW {sorted(expect_review) or '无'}，实际 FIX {got_fix or '无'} "
            f"REVIEW {got_review or '无'}\n"
            + "\n".join(f"  行{h['line']} {h['rule']} {h['tier']} {h['snippet']}"
                        for h in hits))
    if expect_counts is not None:
        got_counts = Counter(h["rule"] for h in hits)
        if got_counts != Counter(expect_counts):
            failures.append(
                f"{name}（mode={mode}）: 预期命中数 {dict(expect_counts)}，"
                f"实际 {dict(got_counts)}\n"
                + "\n".join(f"  行{h['line']} {h['rule']} {h['snippet']}"
                            for h in hits))


check_mode("fixture-fiction", FICTION_FIXTURE, "fiction", ["B6"], ["B1"])
check_mode("fixture-prose", FICTION_FIXTURE, "prose", ["B6"], ["B1", "B11"])
check_mode("fiction-叙述破折号", PLANTED_B5, "fiction", [], ["B5"])
check_mode("fiction-久到回环", PLANTED_F7, "fiction", [], ["B16"])
check_mode("fiction-句号久到回环", PLANTED_F7_PERIOD, "fiction", [], ["B16"])
check_mode("fiction-分号久到回环", PLANTED_F7_SEMICOLON, "fiction", [], ["B16"])

# ---------- gen 模式：生成期自查候选（既有规则补机械触发，全部 REVIEW 级） ----------
PLANTED_GEN_B9 = "微服务架构就像一支交响乐团，每个服务是一件乐器，共同奏响数字化的乐章。"
PLANTED_GEN_B9_ROLE = "它就像一位智慧的导师，不仅传授结论，更传授信任。"
PLANTED_GEN_C2 = "尽管面临诸多挑战，团队未来可期。"
PLANTED_GEN_C2_SUB = "这不仅是工具的升级，更关乎工作方式的变革。"
PLANTED_GEN_C4 = "这项政策可能在一定程度上或许会影响结果。"
PLANTED_GEN_MACRO = "在当今快速发展的时代下，AI 正在改变一切。"
PLANTED_GEN_MACRO_TODAY = "在这个行业野蛮生长的今天，AI 正在改变一切。"
PLANTED_GEN_C5 = "欢呼声过后，声音填满了整个空间。"
PLANTED_GEN_D2 = "好问题！\n\n希望这能帮到你。"
PLANTED_GEN_D2_ONE = "希望对你有帮助。"
PLANTED_GEN_D3 = "作为一个语言模型，我无法预测股价。"
PLANTED_GEN_D4 = "关键在于找到平衡，要结合实际情况。"
PLANTED_GEN_D4_ONE = "没有绝对的对错。"
PLANTED_GEN_D5 = "让我们先来理解背景。"
PLANTED_GEN_D6 = "有研究表明，这种方法可以提高效率。"

check_mode("gen-B9-乐团", PLANTED_GEN_B9, "gen", [], ["B9"])
check_mode("gen-B9-拟人", PLANTED_GEN_B9_ROLE, "gen", [], ["B9"])
check_mode("gen-B9-相当于", "这套架构相当于一座精密的钟表，每个齿轮都要咬合。",
           "gen", [], ["B9"])
# prose 带入集为 B1–B12（含 B9），铺陈喻体在论述文同样照报
check_mode("prose-B9-铺陈喻体", PLANTED_GEN_B9, "prose", [], ["B9"])
check_mode("prose-B9-拟人模板", PLANTED_GEN_B9_ROLE, "prose", [], ["B9"])
check_mode("gen-C2-未来可期", PLANTED_GEN_C2, "gen", [], ["C2"])
check_mode("gen-C2-不仅是更", PLANTED_GEN_C2_SUB, "gen", [], ["C2"])
check_mode("gen-C2-在这一刻明白真理", "在这一刻他明白了真理。", "gen", [], ["C2"])
check_mode("gen-C5-世界退回壳里", "世界退回壳里。", "gen", [], ["C5"])
check_mode("gen-C5-声音填满空间", "声音填满了整个房间。", "gen", [], ["C5"])
check_mode("gen-C4-叠加", PLANTED_GEN_C4, "gen", [], ["C4"])
check_mode("gen-B12-宏观", PLANTED_GEN_MACRO, "gen", [], ["B12"])
check_mode("gen-B12-在今天", PLANTED_GEN_MACRO_TODAY, "gen", [], ["B12"])
check_mode("gen-C5-气氛", PLANTED_GEN_C5, "gen", [], ["C5"], {"C5": 1})
check_mode("gen-D2-服务腔", PLANTED_GEN_D2, "gen", [], ["D2"], {"D2": 2})
# 同一句被开场与收尾两个模板同时覆盖时只报一条：报两条等于虚增计数
check_mode("gen-D2-单句不双报", PLANTED_GEN_D2_ONE, "gen", [], ["D2"],
           {"D2": 1})
check_mode("gen-D3-免责", PLANTED_GEN_D3, "gen", [], ["D3"])
check_mode("gen-D4-万能收尾", PLANTED_GEN_D4, "gen", [], ["D4"])
check_mode("gen-D4-单句不双报", PLANTED_GEN_D4_ONE, "gen", [], ["D4"],
           {"D4": 1})
check_mode("gen-D5-空预告", PLANTED_GEN_D5, "gen", [], ["D5"])
check_mode("gen-D6-模糊归因", PLANTED_GEN_D6, "gen", [], ["D6"])
# C5 同句被"气氛总结"与"套路修辞"两个模板覆盖时只报一条
PLANTED_GEN_C5_TWICE = "欢呼声过后，声音填满了整个房间，随后空气凝固了。"
check_mode("gen-C5-同句不双报", PLANTED_GEN_C5_TWICE, "gen", [], ["C5"],
           {"C5": 1})

# ---------- fiction 词表（B13/B15/B16/B17/B18）：红灯捕获 + 人写豁免 ----------
PLANTED_FICTION_B13 = "她微微点头，指尖极轻地按在杯沿上，又轻轻拍了拍。"
PLANTED_FICTION_B13_STATE = "远处传来微弱的回响，水面浮着一层极淡的柔光。"
PLANTED_FICTION_B15 = "她猛地一僵，整个人震了一下，指甲掐进了掌心。"
PLANTED_FICTION_B16 = "他们沉默了很久，久到炭火都凉透了。"
PLANTED_FICTION_B17_FANCY = "“坐。”她命令道。"
PLANTED_FICTION_B17_CHAIN = "他端着盆。他蹲下。他撕开布。"
# 连珠按"段内连续句"判：软换行只是排版，同一段的三句仍算连珠；
# 空行断开成新段，每段一句不报
PLANTED_FICTION_B17_CHAIN_SOFT = "他端着盆。\n他蹲下。\n他撕开布。"
B17_CHAIN_PARAGRAPHS = "他端着盆。\n\n他蹲下。\n\n他撕开布。"
PLANTED_FICTION_B17_DENSITY = (
    "“吃。”她说。\n\n“不吃。”她说。\n\n“为什么。”她问。\n\n"
    "“不饿。”她说。\n\n“那就放着。”她说。"
)
PLANTED_FICTION_B18 = "他拍了一下，两下，第三下拍到一半停住了。"
FICTION_HUMAN_CLEAN = "水声听久了就懒得分了。茶水凉透了，她把碗收进竹筐，起身去看院里的雨。壶盖一下一下地跳，也没人去管。"

check_mode("fiction-B13-动作副词", PLANTED_FICTION_B13, "gen", [], ["B13"])
check_mode("fiction-B13-状态豁免", PLANTED_FICTION_B13_STATE, "gen", [], [])
check_mode("fiction-B15-抽搐", PLANTED_FICTION_B15, "gen", [], ["B15"])
check_mode("fiction-B16-回环", PLANTED_FICTION_B16, "gen", [], ["B16"], {"B16": 1})
check_mode("fiction-B17-花式标签", PLANTED_FICTION_B17_FANCY, "gen", [], ["B17"])
# 回归：行首「说话人＋冒号＋引语」曾不算对白行，整个格式可骗过扫描器。
# 依据：不挂 skill 时，模型在“全程靠对白推进”这类题上会产出
# 整面纯对白墙（实测最长 156 行，格式为“店员：……”），而旧检测器
# 只认行首引号，整个格式 0 命中。
# 用的正是「店员："……"」，旧检测器 0 命中。
PP_SPEAKER_ROLE = ("店员：“欢迎光临。”\n顾客：“有热的吗？”\n"
                   "店员：“关东煮还热。”\n顾客：“一个玉米包。”\n店员：“好。”")
PP_SPEAKER_NAME = ("陈默：“姓名。”\n审讯员：“哪个默？”\n"
                   "陈默：“沉默的默。”\n审讯员：“年龄。”\n陈默：“三十二。”")
PP_SPEAKER_6 = ("值夜班店员：“欢迎光临。”\n裹紧围巾护士：“有热的吗？”\n"
                "值夜班店员：“关东煮还热。”\n裹紧围巾护士：“一个玉米包。”\n"
                "值夜班店员：“好。”")
# 反例：前缀超 6 字 / 前缀内含句读 / 引号外叙述成句，都不算对白行
PP_SPEAKER_LONG = ("那个穿灰外套的护士：“欢迎光临。”\n"
                   "那个值夜班的高个店员：“有热的吗？”\n"
                   "那个把围巾裹紧的护士：“关东煮还热。”\n"
                   "那个蹲着理货的店员：“一个玉米包。”\n"
                   "那个护士愣了一下：“好。”")
PP_SPEAKER_PUNCT = ("他站起身，说：“走吧。”\n她坐着没动，说：“我不走。”\n"
                    "门外有人喊她的名字。\n“走吧。”\n“我不走。”")

# 回归：B5 曾把行末破折号（话没说完——）报成病灶，而规则自己的豁免说明
# 就写着"台词中断与未完不改"，豁免没实现。中文破折号是两个 U+2014，
# 判"右侧有无内容"必须把 — 本身从尾巴里去掉。
B5_TRAILING = [
    ("B5-行末未完-长句", "他想了很久，最后说——", False),
    ("B5-行末未完-短句", "她话没说完——", False),
    ("B5-段末仅剩破折号", "话到这里——", False),
    ("B5-破折号后仅空白", "她停下来——   ", False),
    ("B5-破折号后仅省略号", "话没说完——……", False),
    ("B5-右侧是解释-应报", "答案其实很简单——专注。", True),
    ("B5-右侧是同位-应报", "他找到了一条路——一条别人都没注意的路。", True),
    ("B5-句中揭晓-应报", "领口别着枚旧胸针——地摊上淘的。", True),
    ("B5-右侧是引语-应报", "他只说了一句——走吧。", True),
    ("B5-三个破折号-应报", "他说了三件事——一件——两件——第三件最重要。", True),
    ("B5-数字范围-应豁免", "1864—1928 年间的事。", False),
    ("B5-对白内中断-应豁免", "“我等一下——不，你先走。”", False),
]
for _name, _text, _want in B5_TRAILING:
    check_mode(_name, _text, "gen", [], ["B5"] if _want else [])

# 回归：B9 句末明喻密度的句子列表曾吃 raw text，引用块/代码块里的比喻也
# 算进密度，违反 docstring 声明的"绝对豁免"。也回归量词表（原表只有
# 支/位/座 等 12 个，"像一条毒蛇/一面镜子/一抹斜阳"全漏）。
# 主语各不相同，免得被 B17 代词连珠正确抓住而干扰本组断言。
# 也不用"一＋量词"喻体：那会命中 _B9_SIMILE，密度断言就不干净了。
_B9_SIMS = ["他站在那儿，像截枯木。", "她坐在床边，像尊泥塑。",
            "风从窗缝进来，像声叹息。", "杯子裂了道纹，像张着的嘴。",
            "他把手举到灯下，像截枯枝。", "天色压低，像扣下来的锅盖。",
            "孩子睡着，像只搁浅的鱼。", "路牌歪着，像问路的姿势。"]
_B9_PLAIN = "第%d句话在这里说着内容。"


def _b9_text(n_sim, n_plain, prefix=""):
    return "\n".join([prefix + _B9_SIMS[k % len(_B9_SIMS)]
                       for k in range(n_sim)]
                      + [prefix + _B9_PLAIN % k for k in range(n_plain)])


B9_DENSITY = [
    ("B9-密度-四句不报", _b9_text(4, 16), False),
    ("B9-密度-五句必报", _b9_text(5, 15), True),
    ("B9-密度-八句必报", _b9_text(8, 12), True),
    ("B9-密度-引用块全豁免", _b9_text(8, 12, "> "), False),
    ("B9-密度-代码块全豁免", "```\n" + _b9_text(8, 12) + "\n```", False),
    ("B9-密度-引用块不计入分母", _b9_text(3, 12) + "\n"
     + "\n".join(["> " + _B9_SIMS[k % 8] for k in range(5)]), False),
    ("B9-密度-正文越线仍报", _b9_text(5, 10) + "\n"
     + "\n".join(["> " + _B9_SIMS[k % 8] for k in range(5)]), True),
]
for _name, _text, _want in B9_DENSITY:
    check_mode(_name, _text, "gen", [], ["B9"] if _want else [])

# 量词表回归：每个常用喻体量词都要能触发。
# 预期清单独立维护在本文件、不从实现读；反向再核实现字符类与清单一致——
# 原清单 29 字而实现已 37 字，多出的把/阵/种/声/味/床/束/尊 8 个字删掉也全绿
# （实测：删「把」verify_repo 11/11 仍绿，删在册的「座」才转红）。
_B9_QUANTIFIERS = ("位支场座轮缕双只股颗盏片条面抹丝道汪弯茬顿袭派粒滴茎根台幢"
                   "把阵种声味床束尊朵朵叶枚堵泓串注线圈顶副柱川撇捺头")
for _q in _B9_QUANTIFIERS:
    check_mode(f"B9-量词-{_q}", f"危险像一{_q}毒蛇。", "gen", [], ["B9"])
_b9_class = re.search(r"一\[([^]]+)\]", _mod._B9_SIMILE.pattern).group(1)
if _b9_class != _B9_QUANTIFIERS:
    failures.append(f"B9 量词表与实现不同步：实现「{_b9_class}」vs "
                    f"测试清单「{_B9_QUANTIFIERS}」——实现新增量词须同步清单，"
                    f"否则删改该字无用例守")

# ---- 回归：文档明说放行、代码却照打的误报 ----
# B5 软换行与段末形态（其余未完/应报形态见上方 B5_TRAILING 组）
for _n, _tx, _w in [
        ("B5-段末未完-后接空行", "她话没说完——\n\n下一段另起。", False),
        ("B5-软换行右侧续行-应报", "领口别着枚旧胸针——\n地摊上淘的，边缘磨得发亮。", True)]:
    check_mode(_n, _tx, "gen", [], ["B5"] if _w else [])

# B15 客观声源的低吼是环境描写（fiction.md 明言放行），发声套板主语只能是人
for _n, _tx, _w in [
        ("B15-引擎低吼着-放行", "引擎低吼着，车冲了出去。", False),
        ("B15-屋外风低吼-放行", "风在屋外低吼着。", False),
        ("B15-兽群低吼-放行", "丛林中兽群低吼。", False),
        ("B15-他低吼一声-应报", "他低吼一声，眼底发红。", True),
        ("B15-她低吼着-应报", "她低吼着扑上来。", True)]:
    check_mode(_n, _tx, "gen", [], ["B15"] if _w else [])

# B18 角色在数是情节（fiction.md 二.9 的放行例），作者数拍子才是病灶
for _n, _tx, _w in [
        ("B18-孩子数水滴入睡-放行", "孩子数着水滴入睡，数到第十一滴。", False),
        ("B18-哨兵数更声-放行", "哨兵数着更声，数到第三声。", False),
        ("B18-他数台阶-放行", "他数着台阶，数到第一百三十级。", False),
        ("B18-作者数拍子-应报", "他拍了拍，一下，两下，三下。", True),
        ("B18-第三下拍到一半-应报", "第三下拍到一半，他停了。", True),
        ("B18-隔三息-应报", "隔三息，又一滴。", True),
        ("B18-顿了一拍-应报", "他顿了一拍，没说话。", True)]:
    check_mode(_n, _tx, "gen", [], ["B18"] if _w else [])

# D2 只管末句纯客套；社交邀请（欢迎随时来玩）不是服务腔
for _n, _tx, _w in [
        ("D2-欢迎随时来玩-放行", "欢迎随时来玩。", False),
        ("D2-欢迎常来坐-放行", "欢迎常来坐。", False),
        ("D2-欢迎随时提问-应报", "欢迎随时提问。", True),
        ("D2-希望对你有帮助-应报", "希望对你有帮助。", True),
        ("D2-有问题随时找我-应报", "有问题随时找我。", True)]:
    check_mode(_n, _tx, "gen", [], ["D2"] if _w else [])

# B17 乒乓阈值与 fiction.md 一致：四行以内放行，≥5 行才报
for _n, _tx, _w in [
        ("B17-乒乓五行交锋-应报", "“你走吧。”\n“我不走。”\n“为什么？”\n“留下。”\n“确定？”", True)]:
    check_mode(_n, _tx, "gen", [], ["B17"] if _w else [])

# 省略号怯场（B17 第四子项）：对白行 ≥6 且省略号开头占比 ≥15% 才报。
# 判据是一致性而非密度——鲁迅 89 行对白里 1 行以省略号开头（1.1%），
# 省略号总量 3.84/千字反而高于生成稿，故"总量多"不报、"统一开头"才报。
ELL = chr(0x2026) + chr(0x2026)
LQ, RQ = chr(0x201C), chr(0x201D)
_ELL_SCRIPT = "\n".join(f"护士：{ELL}饭团。" for _ in range(8)) \
    + "\n护士：不用了。\n店员：慢走。"
_ELL_QUOTED = "\n".join(f"{LQ}{ELL}来一碗关东煮。{RQ}" for _ in range(9)) \
    + "\n门外有人敲门。"
_ELL_SPARSE = "\n".join(
    f"{LQ}第{_}句。{RQ}\n外面有响动。" for _ in range(10)) \
    + f"\n{LQ}{ELL}好吧。{RQ}"
_ELL_FEW_LINES = "\n".join(f"店员：{ELL}第{_}句。" for _ in range(4))
check_mode("fiction-B17-省略号怯场-剧本体", _ELL_SCRIPT, "gen", [], ["B17"])
check_mode("fiction-B17-省略号怯场-带引号对白", _ELL_QUOTED, "gen", [], ["B17"])
check_mode("fiction-B17-省略号怯场-占比低不报", _ELL_SPARSE, "gen", [], [])
check_mode("fiction-B17-省略号怯场-对白行不足不报", _ELL_FEW_LINES, "gen", [], [])
check_mode("prose-B17-省略号怯场不适用", _ELL_SCRIPT, "prose", [], [])

# ---------- 词表守卫：规则页不枚举、实现又是正则片段的词表 ----------
# _WORD_TABLES（verify_repo 第 6 层）按子串守纯词表；B15 抽搐套板、B16 回环
# 程度词、B18 计数形、B9 明喻标记是正则片段，删掉整条分支后词表子串仍在，
# 11/11 全绿而行为已退化（实测：删"死死"、删程度词"痛"、删"隔N息"分支、
# 删"宛如/犹如"标记、删两个构词负向断言，全部穿得过全套体检）。
# 此处逐形给独立用例；清单独立维护在本文件，不从实现读。
WORD_GUARD = [
    # B15 舞台剧抽搐：每条分支一个代表形
    ("B15-死死", "她死死盯着门口。"),
    ("B15-咬碎牙关", "他咬碎牙关，没出声。"),
    ("B15-身子猛然一僵", "他身子猛然一僵。"),
    ("B15-整个人震了一下", "他整个人震了一下。"),
    ("B15-喉头滚动", "她喉头滚动了一下。"),
    ("B15-倒吸了一口凉气", "他倒吸了一口凉气。"),
    ("B15-呼吸一滞", "他的呼吸不由得一滞。"),
    ("B15-漏跳了一拍", "她的心跳漏跳了一拍。"),
    ("B15-脊背渗出冷汗", "他的脊背渗出冷汗。"),
    # B16 同词回环：程度词逐字 + 安静/寂静/沉默三条分支。
    # 模板只放"词＋分隔＋同词＋到"：中间夹实词会超出正则的 4 字符分隔窗
    ("B16-冷", "他冷，冷到说不出口。"),
    ("B16-黑", "夜黑，黑到看不见路。"),
    ("B16-痛", "他痛，痛到见骨。"),
    ("B16-累", "他累，累到说不出话。"),
    ("B16-远", "路远，远到看不见头。"),
    ("B16-慢", "他慢，慢到让人着急。"),
    ("B16-快", "他快，快到看不清。"),
    ("B16-轻", "声音轻，轻到听不清。"),
    ("B16-低", "天平低，低到贴了地。"),
    ("B16-厚", "雪厚，厚到没了小腿。"),
    ("B16-久", "他久，久到成了习惯。"),
    ("B16-寂静", "陵园里寂静，寂静到能听见心跳。"),
    ("B16-沉默到", "两个人沉默，沉默到炭火都凉透。"),
    # B18 计数形：角色在数放行分支之外的"数到第N下"。用"声"收尾——
    # "第三下"同时命中"第N下"分支，删掉"数到第"分支照样红不了
    ("B18-数到第N声", "秒表数到第三声，他停了。"),
    # B9 明喻标记：删除任一标记后喻体句静默漏检。"一般/一样"形与"一+量词"形
    # 是正则里的两条分支，删第一条分支里的标记只有一般形用例会红
    ("B9-就像", "危险就像一条毒蛇。"),
    ("B9-如同", "危险如同一条毒蛇。"),
    ("B9-宛如", "危险宛如一条毒蛇。"),
    ("B9-仿佛", "危险仿佛一条毒蛇。"),
    ("B9-犹如", "危险犹如一条毒蛇。"),
    ("B9-恰似", "危险恰似一条毒蛇。"),
    ("B9-相当于", "危险相当于一条毒蛇。"),
    ("B9-像", "危险像一条毒蛇。"),
    ("B9-就像-一般形", "他就像山一般矗立。"),
    ("B9-如同-一般形", "他如同山一般矗立。"),
    ("B9-宛如-一般形", "他宛如山一般矗立。"),
    ("B9-仿佛-一般形", "他仿佛山一般矗立。"),
    ("B9-犹如-一般形", "他犹如山一般矗立。"),
    ("B9-恰似-一般形", "他恰似山一般矗立。"),
    ("B9-相当于-一般形", "他相当于山一般矗立。"),
    ("B9-像-一般形", "他像山一般矗立。"),
    # 构词负向断言：名词性用法不报（删掉断言后"说到底的方案"被误报成 FIX）
    ("B10-名词性用法不报", "说到底的方案他早就想好了。"),
    ("D2-总结套话名词性不报", "综上所述的问题他已经想过了。"),
]
for _n, _tx in WORD_GUARD:
    _rule = _n.split("-")[0]
    check_mode(_n, _tx, "gen", [], [] if _n.endswith("不报") else [_rule])

# ---- 回归：实测发现的漏报与误报 ----
# B3 段首判定改用行号不连续：围栏/表格前无空行时下一段被并入上段，
# 段首空评论漏报（与 _paragraphs() 的 docstring 口径矛盾）。
for _n, _tx, _w in [
        ("B3-围栏前无空行-应报",
         "第一段说完了。\n```\n代码\n```\n听起来，事情比预想的复杂。\n\n第三段。", True),
        ("B3-表格后无空行-应报",
         "第一段。\n| 列 | 值 |\n| --- | --- |\n听起来，事情比预想的复杂。", True),
        ("B3-围栏前后有空行-应报", "第一段。\n\n```\n代码\n```\n\n听起来，事情比预想的复杂。", True),
        ("B3-普通空行分段-应报", "第一段。\n\n听起来，事情比预想的复杂。", True),
        ("B3-首段-不报", "听起来，事情比预想的复杂。", False),
        ("B3-非B3词-不报", "第一段。\n\n```\n代码\n```\n意味着，配置仍需人工维护。", False),
        ("B3-有承接成分-不报", "第一段。\n\n```\n代码\n```\n听起来，这件事情比预想的复杂。", False)]:
    check_mode(_n, _tx, "gen", [], ["B3"] if _w else [])

# B17 连珠加"它"（_B17_INTRA_HEAD 早已含它，两个词表不同步）
for _n, _tx, _w in [
        ("B17-它连珠三短句-应报", "它停下。它转头。它走了。", True),
        ("B17-它连珠长句-应报", "它停在楼梯口一动不动。它转头看向窗外。它又走了了回去。", True),
        ("B17-他连珠-应报", "他停下。他转头。他走了。", True),
        ("B17-主语切换-不报", "她不信他，他也不信自己。", False),
        ("B17-风与她的动作-不报", "风把门吹开，她起身去闩上。", False)]:
    check_mode(_n, _tx, "gen", [], ["B17"] if _w else [])

# B5 破折号变体：收 －－(U+FF0D×2)/–(U+2013)/―(U+2015)，显式不收 ASCII --
# （语料 2360 处全是表格分隔线、CLI 参数与代码，叙述层 0 处）
for _n, _tx, _w in [
        ("B5-全角双连字符-应报", "领口别着枚旧胸针－－地摊上淘的，边缘磨得发亮。", True),
        ("B5-U+2013-应报", "领口别着枚旧胸针–地摊上淘的，边缘磨得发亮。", True),
        ("B5-U+2015-应报", "领口别着枚旧胸针―地摊上淘的，边缘磨得发亮。", True),
        ("B5-变体软换行-应报", "领口别着枚旧胸针－－\n地摊上淘的，边缘磨得发亮。", True),
        ("B5-SQL注释-不报", "SELECT * FROM users -- 只取用户表", False),
        ("B5-行首注释-不报", "-- 只取用户表的注释", False),
        ("B5-CLI参数-不报", "python build.py --force", False),
        ("B5-help-不报", "--help", False),
        ("B5-分隔线-不报", "----------", False),
        ("B5-表格分隔线-不报", "| --- | --- |", False),
        ("B5-代码块内注释-不报", "```\n-- 注释\n```", False),
        ("B5-行内代码-不报", "行内 `--force` 参数", False),
        ("B5-数字区间U+2013-不报", "960–1440", False),
        ("B5-数字区间U+2014-不报", "1864—1928", False),
        ("B5-日期-不报", "2024-10-23", False),
        ("B5-行首bullet-不报", "– 第一项", False),
        ("B5-URL连字符-不报", "URL foo--bar", False),
        ("B5-章节区间-不报", "3–5 章", False),
        ("B5-气温负号-不报", "气温－5 度", False),
        ("B5-京沪连接号-不报", "北京－上海高铁", False),
        ("B5-目录树-不报", "├── 目录树", False)]:
    check_mode(_n, _tx, "gen", [], ["B5"] if _w else [])

# B16 回环补形：doc 原文示例（"伤得很深，深到……"）与明令禁用的
# "所谓X不过是Y" 原正则零覆盖
for _n, _tx, _w in [
        ("B16-伤得很深-应报", "他伤得很深，深到见骨。", True),
        ("B16-担子很重-应报", "担子很重，重到压弯了肩。", True),
        ("B16-安静安静得-应报", "房间安静，安静得能听见灰尘落下来。", True),
        ("B16-站得很高-应报", "他站得很高，高到能看见屋顶。", True),
        ("B16-数年之后-应报", "数年之后，他才明白过来。", True),
        ("B16-所谓X不过是Y-应报", "所谓陪伴，不过是习惯。", True),
        ("B16-很久久到-应报", "很久，久到忘了怎么开口。", True),
        ("B16-伤口很深-不报", "伤口很深，能看见骨头。", False),
        ("B16-楼层很高-不报", "楼层很高，电梯停了。", False),
        ("B16-所谓的理由-不报", "所谓的理由，他一条也说不出来。", False),
        ("B16-他说不过是-不报", "他说不过是例行检查。", False),
        ("B16-单处安静得-不报", "房间里安静得能听见灰尘落下来。", False),
        ("B16-茶水凉透-不报", "雨声渐歇，茶水凉透了。", False),
        ("B16-数年之后搬走-不报", "数年之后，她搬去了南方。", False),
        ("B16-对白内所谓-不报", "“所谓陪伴，不过是习惯。”他说。", False)]:
    check_mode(_n, _tx, "gen", [], ["B16"] if _w else [])

# B15 词表缺口回归：眼前发白/发黑 与 指节插入词形原为零覆盖
for _n, _tx in [
        ("B15-眼前一阵发白", "眼前一阵发白。"),
        ("B15-眼前发黑", "他眼前发黑。"),
        ("B15-指节因用力泛白", "指节因为用力而泛白。"),
        ("B15-关节泛白", "关节泛白。")]:
    check_mode(_n, _tx, "gen", [], ["B15"])
for _n, _tx in [
        ("B15-眼前雪地-不报", "眼前一片雪地。"),
        ("B15-白发苍苍-不报", "白发苍苍的老人。"),
        ("B15-白天-不报", "白天。"),
        ("B15-黑洞-不报", "黑洞。"),
        ("B15-按在膝头-不报", "他把信纸按在膝头。"),
        ("B15-发展-不报", "发展。"),
        ("B15-黑白电视-不报", "黑白电视机。")]:
    check_mode(_n, _tx, "gen", [], [])

# 跳行引语是 _mask_dialogue 的独有路径：行内引文掩码（_INLINE_QUOTES）
# 按行配对，跳行引号对它不可见。单关任一个全绿、同时关才红——
# 这一条让 _mask_dialogue 单独失效也转红
check_mode("免责-B5-跳行对白内中断", "“等我一下——\n不，你先走。”", "gen", [], [])

# B17 标签密度分母按 fiction.md 一.5 的"对白行"定义：整行一句引语、引语外只挂短标签、
# 或行首说话人+冒号+引语。内联引语行（叙述中夹"他说：……"后还有叙述）不算对白行，
# 计入分母会把"每句独行对白都挂标签"这种真病炙稀释成合格。
_B17_SUBJ = ["他", "她", "老板", "店员", "客人",
             "女人", "男人", "孩子", "老人", "司机"]
_B17_INLINE = "\n".join(
    f"{_B17_SUBJ[k % 10]}说：“第{k}句话。”然后车间里安静下来。"
    for k in range(10))
_B17_DLG6 = ("“你走吧。”他说。\n“我不走。”他说。\n"
             "“为什么？”他说。\n“留下。”他说。\n"
             "“确定？”他说。\n“走吧。”他说。")
for _n, _tx, _w in [
        ("B17-密度分母-独行6标签应报", _B17_DLG6, True),
        ("B17-密度分母-内联不池释应报", _B17_DLG6 + "\n" + _B17_INLINE, True),
        ("B17-密度分母-两行不报",
         "“你走吧。”他说。\n“我不走。”他说。", False),
      ("B17-全篇内联不误报转述体", _B17_INLINE, False),
        # 密度边界：4 标签 / 6 对白行 = 0.67，>0.5 必须报。把阈值从 0.5 抬到
        # 0.9 后这条是唯一会转红的用例（6/6 全标签在两个阈值下都报）。
        # 对白行之间夹的叙述行不能以代词起头（否则句首代词连珠先红），
        # 也不能连发（否则问答乒乓先红）
        ("B17-密度边界-六七成标签应报",
         "“你走吧。”他说。\n门外有脚步声。\n“我不走。”他说。\n灯亮着。\n"
         "“为什么？”\n风把门吹开。\n“留下。”他说。\n茶还热着。\n"
         "“确定？”\n雨下大了。\n“走吧。”他说。\n天亮了。", True)]:
    check_mode(_n, _tx, "gen", [], ["B17"] if _w else [])

# 跨行引语掩码：_mask_dialogue 的独有能力是跨行延续（上行开引号、下行才收尾），
check_mode("fiction-B17-乒乓-角色称谓前缀", PP_SPEAKER_ROLE, "gen", [], ["B17"])
check_mode("fiction-B17-乒乓-人名前缀", PP_SPEAKER_NAME, "gen", [], ["B17"])
check_mode("fiction-B17-乒乓-前缀六字", PP_SPEAKER_6, "gen", [], ["B17"])
check_mode("fiction-B17-乒乓-前缀超限不报", PP_SPEAKER_LONG, "gen", [], [])
check_mode("fiction-B17-乒乓-前缀带句读不报", PP_SPEAKER_PUNCT, "gen", [], [])
check_mode("fiction-B17-代词连珠", PLANTED_FICTION_B17_CHAIN, "gen", [], ["B17"])
check_mode("fiction-B17-代词连珠软换行", PLANTED_FICTION_B17_CHAIN_SOFT,
           "gen", [], ["B17"])
check_mode("fiction-B17-空行分段不报", B17_CHAIN_PARAGRAPHS, "gen", [], [])
check_mode("fiction-B17-标签密度", PLANTED_FICTION_B17_DENSITY, "gen", [], ["B17"])
# 标签计数含"说道/道/低声说"：纯"X道"标签也要能撑出密度，否则把"道"分支
# 从正则里删掉，上面的用例一条都不会转红
PLANTED_FICTION_B17_DAO = (
    "“吃。”他道。\n\n“不吃。”她道。\n\n“为什么。”他低声说。\n\n"
    "“不饿。”她道。\n\n“那就放着。”他道。")
check_mode("fiction-B17-道类标签密度", PLANTED_FICTION_B17_DAO, "gen", [],
           ["B17"])
# 句内主语复现（口吃式主语过量，"她知道，她也明白"）与主语切换豁免
PLANTED_FICTION_B17_INTRA = "她知道这件事，她也明白为什么。屋里的灯没点，她坐着，她等着。"
B17_INTRA_SUBJECT_SWAP = "她不信他，他也不信自己。"
B17_INTRA_HUMAN = "风把门吹开，她起身去闩，顺手把灯芯剪短了一截。"
check_mode("fiction-B17-句内主语复现", PLANTED_FICTION_B17_INTRA, "gen", [], ["B17"])
check_mode("fiction-B17-主语切换不报", B17_INTRA_SUBJECT_SWAP, "gen", [], [])
check_mode("fiction-B17-句内人写不报", B17_INTRA_HUMAN, "gen", [], [])
# 问答乒乓：连续 ≥5 行独行对白无叙述即报（fiction.md：四行交锋短打放行）。
PLANTED_FICTION_B17_PINGPONG = (
    "“你走吧。”\n\n“我不走。”\n\n“为什么？”\n\n“不为什么。”\n\n"
    "“告诉我。”\n\n“没有什么好说的。”"
)
PLANTED_FICTION_B17_FIVE = ("“你走吧。”\n“我不走。”\n“为什么？”\n“留下。”\n“确定？”")
PLANTED_FICTION_B17_FOUR = (
    "“空气凝固了？”\n\n“没有啊，挺凉快的。”\n\n“那你为什么不说话？”\n\n“我在想事情。”"
)
check_mode("fiction-B17-问答乒乓", PLANTED_FICTION_B17_PINGPONG, "gen", [], ["B17"])
# fiction.md：交锋型反问短打四行以内放行，阈值是 ≥5 行。
check_mode("fiction-B17-四行乒乓不报", PLANTED_FICTION_B17_FOUR, "gen", [], [])
check_mode("fiction-B17-五行乒乓必报", PLANTED_FICTION_B17_FIVE, "gen", [], ["B17"])
# 带短标签的行算对白行：标签只有四个字以内，叙述没有真正介入，
# 不能靠给每句挂个"你说"绕开判定。
PLANTED_FICTION_B17_TAGGED = (
    "“我知道。”你顿了顿，“我是说，你一直这么坐着？”\n\n"
    "“嗯。”\n\n“你过来。”你说。\n\n“我在这里。”\n\n"
    "“那就好。”你说。"
)
check_mode("fiction-B17-带标签算对白行", PLANTED_FICTION_B17_TAGGED, "gen", [], ["B17"])
# 阈值边界："她说。"（3 字）是标签，该行仍算对白行；引号外是一整个动作时
# （"她把碗放下，碗沿磕在桌面上。"）叙述真正介入，该行打断连发——把动作行
# 也算对白行，正常叙述戏会被误判成乒乓
FICTION_HUMAN_TAGGED_ACTION = (
    "“走。”她说。\n\n“嗯。”\n\n她把碗放下，碗沿磕在桌面上。\n\n“走吧。”"
)
check_mode("fiction-B17-动作标签不算对白行", FICTION_HUMAN_TAGGED_ACTION,
           "gen", [], [])
# 引号外叙述成句的行打断连发：动作、空间回到正文里了。
FICTION_HUMAN_NARRATION_BREAK = (
    "“走。”她低头看那块干草，像是在权衡什么，然后慢慢侧过身。\n\n"
    "“我不困。”\n\n"
    "他把柴推了推，火苗歪了一下，又立起来，照亮半个洞壁。\n\n"
    "“躺下。”"
)
check_mode("fiction-B17-叙述行打断", FICTION_HUMAN_NARRATION_BREAK, "gen", [], [])
# 边界：三行独行对白是常见过场，不报
FICTION_HUMAN_THREE_LINES = (
    "“空气凝固了？”\n\n“没有啊，挺凉快的。”\n\n“那你为什么不说话？”"
)
check_mode("fiction-B17-三行不报", FICTION_HUMAN_THREE_LINES, "gen", [], [])
# 行间有叙述介入即断链，不报
FICTION_HUMAN_WITH_NARRATION = (
    "“你走吧。”\n\n她没动，手指在桌沿上敲了两下。\n\n“我不走。”\n\n"
    "窗外有人在喊孩子回家吃饭。\n\n“为什么？”\n\n他把碗搁在灶台上。"
)
check_mode("fiction-B17-叙述介入不报", FICTION_HUMAN_WITH_NARRATION, "gen", [], [])
# 全篇转述体：零直接引语、全靠"他说……她说……"。阈值 8 个标签：病灶稿 33 个标签 / 904 字
PLANTED_FICTION_B17_REPORTED = (
    "他撑着膝盖站起来，拿过饭团扫条码，问，要不要加热。她说，加热吧。\n\n"
    "她说，外面下雨了？他说，下了，不大。她说，你鞋边上都是水。"
    "他说，刚踩了个水洼。她说，我下夜班。他说，这个点不是刚下班就是刚上班。"
    "她说，也对。他说，那你坐会儿。"
)
check_mode("fiction-B17-全篇转述", PLANTED_FICTION_B17_REPORTED, "gen", [], ["B17"])
# 直接引语不只长在行首：内联引语与剧本体（角色：台词）通篇没有一行以引号
# 开头，只数行首会把它们误判成"没有一句直接引语"
FICTION_INLINE_QUOTE = (
    "他说：“走吧。”她问：“去哪？”他说：“回家。”她点头：“好。”\n\n"
    "他笑：“走吧。”她说：“嗯。”他伸手：“伞拿着。”她接了：“谢了。”"
)
check_mode("fiction-B17-内联引语不报", FICTION_INLINE_QUOTE, "gen", [], [])
FICTION_SCRIPT_FORM = (
    "老马：知道了。\n小厮：是。\n老马：备车。\n小厮：去哪儿？\n"
    "老马：城东。\n小厮：这就去。\n老马：快些。\n小厮：好。"
)
check_mode("fiction-B17-剧本体不报", FICTION_SCRIPT_FORM, "gen", [], [])
# 有直接引语的混写不报：转述只压程序性拉锯，交锋仍是直接引语
FICTION_HUMAN_MIXED_FORM = (
    "他问要不要加热，她说要。\n\n"
    "她把饭团放在台面上，看了他一眼。\n\n"
    "“几点了。”\n\n"
    "“四点。”他把微波炉的门按上。\n\n"
    "“还有两个小时。”\n\n"
    "“够你吃完。”\n\n"
    "他转身去拆那箱火腿肠，纸箱口划开的声音很脆。"
)
check_mode("fiction-B17-混写不报", FICTION_HUMAN_MIXED_FORM, "gen", [], [])
# B15 实测漏网变体：喉结"动了动"、瞳孔间隔"在暗处缩紧"；医学事实不误报
PLANTED_FICTION_B15_ADAM = "她喉结动了动，没说话。"
PLANTED_FICTION_B15_PUPIL = "你看见她的瞳孔在暗处缩紧，紫得发黑。"
FICTION_HUMAN_PUPIL_MEDICAL = "医生用手电筒照射患者的眼部，观察瞳孔反射与对光收缩情况。"
check_mode("fiction-B15-喉结动", PLANTED_FICTION_B15_ADAM, "gen", [], ["B15"])
check_mode("fiction-B15-瞳孔间隔", PLANTED_FICTION_B15_PUPIL, "gen", [], ["B15"])
check_mode("fiction-B15-瞳孔医学不报", FICTION_HUMAN_PUPIL_MEDICAL, "gen", [], [])
# B15 狂跳（实测补充：fiction 清理中"心脏狂跳不止"被常规删除但旧词表无归属）
PLANTED_FICTION_B15_POUND = "他愣在原地，心脏狂跳不止。"
check_mode("fiction-B15-狂跳", PLANTED_FICTION_B15_POUND, "gen", [], ["B15"])
# B15 低吼（用户判定禁用的发声反应套板）：模板形态全捕获；
# 裸"低吼"是引擎/风/兽群的客观声源，不报
PLANTED_FICTION_B15_GROWL = "他低吼一声，眼底发红。"
PLANTED_FICTION_B15_GROWL_N = "她从喉头里滚出几声低吼。"
PLANTED_FICTION_B15_GROWL_Z = "他低吼着掐住她的手腕。"
PLANTED_FICTION_B15_GROWL_S = "他低吼了一句，甩上门走了。"
FICTION_HUMAN_GROWL_ENGINE = "隧道尽头，引擎在低吼，盖住了他的脚步声。"
# 客观声源带"声"也不报："低吼声"是名词性声源，只有"低吼＋数量/着"才是发声反应
FICTION_HUMAN_GROWL_NOUN = "隧道尽头传来低吼声，回声滚了很久。"
check_mode("fiction-B15-低吼一声", PLANTED_FICTION_B15_GROWL, "gen", [], ["B15"])
check_mode("fiction-B15-几声低吼", PLANTED_FICTION_B15_GROWL_N, "gen", [], ["B15"])
check_mode("fiction-B15-低吼着", PLANTED_FICTION_B15_GROWL_Z, "gen", [], ["B15"])
check_mode("fiction-B15-低吼了一句", PLANTED_FICTION_B15_GROWL_S, "gen", [], ["B15"])
check_mode("fiction-B15-引擎低吼不报", FICTION_HUMAN_GROWL_ENGINE, "gen", [], [])
check_mode("fiction-B15-低吼声不报", FICTION_HUMAN_GROWL_NOUN, "gen", [], [])
# B17 低吼道 标签（"低声道"的姊妹形态）
PLANTED_FICTION_B17_GROWL_TAG = "“放开。”他低吼道。"
check_mode("fiction-B17-低吼道标签", PLANTED_FICTION_B17_GROWL_TAG, "gen", [], ["B17"])
# B14 情绪贴标签（扫描器 emit 但此前无测试覆盖：情绪诊断书报，直陈无力不报）
PLANTED_FICTION_B14_EMOTION = "一股强烈的苦涩涌上心头，他站在原地。"
FICTION_HUMAN_B14_PLAIN = "他确实感到无力，腿上的伤口还在渗血。"
check_mode("fiction-B14-情绪贴标签", PLANTED_FICTION_B14_EMOTION, "gen", [], ["B14"])
check_mode("fiction-B14-直陈无力不报", FICTION_HUMAN_B14_PLAIN, "gen", [], [])
# B14 在 fiction 清理带入集（B13–B18）内，fiction 模式照报
check_mode("fiction-B14-情绪贴标签-fiction模式", PLANTED_FICTION_B14_EMOTION,
           "fiction", [], ["B14"])
# B13–B18 是叙事工法，prose 清理不带入：同文本 prose 模式必须不报
check_mode("prose-B14-叙事工法不带入", PLANTED_FICTION_B14_EMOTION,
           "prose", [], [])
# B9 常规明喻形态（实测补充：fiction 清理中"像是被雷击中一般"被常规删除但旧词表无归属）
PLANTED_FICTION_B9_GENERAL = "他愣在原地，像是被雷击中一般。月光像水一样洒进来。"
FICTION_HUMAN_B9_EXPLAIN = "缓存就像一个仓库，把常用数据放在离 CPU 更近的位置。"
check_mode("fiction-B9-一般形态", PLANTED_FICTION_B9_GENERAL, "gen", [], ["B9"])
check_mode("fiction-B9-解释比喻不报", FICTION_HUMAN_B9_EXPLAIN, "gen", [], [])
# B9 句末明喻按全文密度报：单处不报，密集成篇才报
PLANTED_FICTION_B9_TAIL_DENSE = (
    "她推门进来，肩上落了一层雪，像披了半件旧蓑衣。\n\n"
    "炉子上的水刚开，白汽往上顶，像有人在屋里叹气。\n\n"
    "她把围巾解下来搭在椅背上，动作很慢，像在拆一件织错的东西。\n\n"
    "我递过去一只碗，她接了，指尖是凉的，像刚从井里提上来的。\n\n"
    "窗外那盏路灯一直闪，像谁在楼下反复按开关。\n\n"
    "她喝了一口，眉头松开一点，像紧绷的线被人放了半寸。\n")
FICTION_HUMAN_B9_TAIL_ONE = (
    "水声听久了就懒得分了，像是耳朵自己关掉一半。\n\n"
    "他把碗放进水池，出来时顺手把灯关了。\n\n"
    "屋里黑得干净，只有窗外的雨还在下，像有人在远处说话。\n")
# 判据是"至少五处 且 占全文句数 ≥8%"：短文本三处占比虽高但不成规律，不报
FICTION_B9_TAIL_SHORT_DENSE = (
    "她推门进来，肩上落了一层雪，像披了半件旧蓑衣。\n\n"
    "炉子上的水刚开，白汽往上顶，像有人在屋里叹气。\n\n"
    "她解下围巾搭在椅背上，动作很慢，像在拆一件织错的东西。\n")
check_mode("fiction-B9-句末尾巴过密", PLANTED_FICTION_B9_TAIL_DENSE,
           "fiction", [], ["B9"])
check_mode("fiction-B9-句末尾巴单处不报", FICTION_HUMAN_B9_TAIL_ONE,
           "fiction", [], [])
check_mode("fiction-B9-短文本三处不报", FICTION_B9_TAIL_SHORT_DENSE,
           "fiction", [], [])
check_mode("fiction-B18-计数", PLANTED_FICTION_B18, "gen", [], ["B18"])
check_mode("fiction-人写-洁净段", FICTION_HUMAN_CLEAN, "gen", [], [])
check_mode("fiction-人写-洁净段-fiction模式", FICTION_HUMAN_CLEAN, "fiction", [], [])

# 人写组：gen 模式 FIX 必须零命中；REVIEW 命中须为"复核后保留"型
GEN_HUMAN_METAPHOR = "缓存就像一个仓库，把常用数据放在离 CPU 更近的位置，读得快，写回慢。"
GEN_HUMAN_SOURCE = "2025 年 3 月接口升级后，旧版客户端无法继续登录。"
GEN_HUMAN_HEDGE = "这项政策可能影响结果。"
GEN_HUMAN_LETUS = "让我们看看结果：42% 的请求在 50ms 内返回。"
GEN_INDUSTRY_WORDS = "这套方案可以赋能开发团队，形成业务闭环，沉淀底层逻辑。"

check_mode("gen-人写-解释性比喻", GEN_HUMAN_METAPHOR, "gen", [], [])
check_mode("gen-人写-带来源数字", GEN_HUMAN_SOURCE, "gen", [], [])
check_mode("gen-人写-单个限定词", GEN_HUMAN_HEDGE, "gen", [], [])
check_mode("gen-人写-让我们看结果", GEN_HUMAN_LETUS, "gen", [], ["D5"])
check_mode("gen-N11-行业大词", GEN_INDUSTRY_WORDS, "gen", [], [])
check_mode("gen-人写-A1", A1, "gen", [], [])
check_mode("gen-AI-1", AI_1, "gen", ["B10"], ["B1", "B9", "D5"])

# 回归：方案文档中的 9 句 AI 腔文本，gen 模式须 ≥7 处命中，且"赋能"不得被当作问题
GEN_REGRESSION = (
    "在当今快速发展的时代下，AI 正在改变一切。\n\n"
    "值得注意的是，配置管理往往被忽视。这套方案可以赋能开发团队。"
    "它就像一位智慧的导师，不仅传授结论，更传授看待世界的多元视角。"
    "这不是一次简单的升级，而是一次跨越。\n\n"
    "首先，我们需要理解背景。其次，让我们深入探讨。真正重要的是，"
    "我们理解了工具的边界。尽管面临诸多挑战，团队未来可期。"
)
check_mode("gen-回归文本", GEN_REGRESSION, "gen", [],
           ["B1", "B3", "B9", "B12", "C2", "D5"])
_reg_hits = scan(GEN_REGRESSION, mode="gen")
if len(_reg_hits) < 7:
    failures.append(f"gen 回归：预期 ≥7 处命中，实际 {len(_reg_hits)} 处\n"
                    + "\n".join(f"  {h['rule']} {h['tier']} {h['snippet']}"
                                for h in _reg_hits))
if any("赋能" in h["note"] for h in _reg_hits):
    failures.append("gen 回归：赋能被当作问题写入命中说明（违反 N11 立场）")

# ---------- CLI：stdin 模式与 --mode 透传 ----------
_SCRIPT = Path(__file__).resolve().parent / "scan-mechanical.py"


def _cli(*argv, stdin=""):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, str(_SCRIPT), *argv], input=stdin,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="strict", env=env)

_r = _cli("-", stdin=PLANTED_B11)
if _r.returncode != 1 or "B11" not in _r.stdout:
    failures.append(f"CLI stdin: 预期 exit 1 且报 B11，实际 exit {_r.returncode}")
_r = _cli("--mode", "fiction", "-", stdin=PLANTED_B11)
if _r.returncode != 0:
    failures.append(f"CLI stdin fiction: 预期 exit 0（B11 不带入），实际 exit {_r.returncode}")
_r = _cli("--mode", "gen", "-", stdin=PLANTED_GEN_D6)
if _r.returncode != 1 or "D6" not in _r.stdout:
    failures.append(f"CLI stdin gen: 预期 exit 1 且报 D6，实际 exit {_r.returncode}\n{_r.stdout}{_r.stderr}")
_r = _cli("--mode", "bogus", "-", stdin=PLANTED_B11)
if _r.returncode != 2:
    failures.append(f"CLI 非法 mode: 预期 exit 2，实际 exit {_r.returncode}")

# ---------- CLI：BOM 豁免 / GBK 回退 / B3 无空行告警 ----------
import tempfile
import _loader

with tempfile.TemporaryDirectory() as _td:
    _bom = Path(_td) / "bom.md"
    _bom.write_bytes("\ufeff".encode("utf-8")
                     + "---\nname: 采集、存储、展示、分析\n---\n\n正文。\n".encode("utf-8"))
    _r = _cli(str(_bom))
    if _r.returncode != 0:
        failures.append(f"CLI BOM: frontmatter 豁免被 BOM 击穿，预期 exit 0，实际 exit {_r.returncode}\n{_r.stdout}")

    _gbk = Path(_td) / "gbk.txt"
    _gbk.write_bytes("说白了，这个方案不行。".encode("gbk"))
    _r = _cli(str(_gbk))
    if _r.returncode != 1 or "B10" not in _r.stdout:
        failures.append(f"CLI GBK: 预期 exit 1 且报 B10（解码后正常扫描），实际 exit {_r.returncode}\n{_r.stdout}{_r.stderr}")

    _r = _cli("-", stdin="第一段交代背景。\n值得注意的是，配置管理往往被忽视。\n")
    if _r.returncode != 0 or "未检出分段" not in _r.stdout:
        failures.append(f"CLI B3 告警: 预期 exit 0 且输出无分段提示，实际 exit {_r.returncode}\n{_r.stdout}")
    # 反向：无空行但引用块边界同样分段时 B3 已执行，不得再打印"未执行"提示
    # （旧提示按空行切段，会出现"B3 命中"与"B3 未执行"同轮并存）
    _r = _cli("-", stdin="第一段说完了。\n> 引用一行\n听起来，事情比预想的复杂。")
    if _r.returncode != 1 or "B3" not in _r.stdout or "未检出" in _r.stdout:
        failures.append(f"CLI B3 提示失真: 预期 exit 1、报 B3 且无'未检出'提示，"
                        f"实际 exit {_r.returncode}\n{_r.stdout}")

    _scan_dir = Path(_td) / "scan-dir"
    (_scan_dir / "nested").mkdir(parents=True)
    (_scan_dir / "clean.md").write_text("正文没有触发项。", encoding="utf-8")
    (_scan_dir / "nested" / "hit.txt").write_text(PLANTED_B5_SINGLE, encoding="utf-8")
    (_scan_dir / "ignored.bin").write_bytes(b"\x00\xff\x00")
    # 未闭合围栏/frontmatter 的告警：状态机坏掉（不跳过围栏后文）时扫描结果
    # 为空但退出码仍 0，用户以为扫过了——告警本身也没有用例守
    _unclosed_fence = Path(_td) / "unclosed.md"
    _unclosed_fence.write_text("正文。\n```\n说白了，代码", encoding="utf-8")
    _r = _cli(str(_unclosed_fence))
    if _r.returncode != 0 or "未闭合" not in _r.stdout:
        failures.append(f"CLI 未闭合告警: 预期 exit 0 且提示围栏未闭合，"
                        f"实际 exit {_r.returncode}\n{_r.stdout}")
    _unclosed_yaml = Path(_td) / "unyaml.md"
    _unclosed_yaml.write_text("---\nname: 未闭合\n正文。", encoding="utf-8")
    _r = _cli(str(_unclosed_yaml))
    if "未闭合" not in _r.stdout:
        failures.append(f"CLI frontmatter 未闭合告警缺失:\n{_r.stdout}")

    _r = _cli(str(_scan_dir))
    if _r.returncode != 1 or "hit.txt" not in _r.stdout or "B5" not in _r.stdout:
        failures.append(f"CLI 目录递归: 预期只扫描文本文件并报 nested/hit.txt 的 B5，实际 exit {_r.returncode}\n{_r.stdout}{_r.stderr}")

# ---------- 同点双报抑制（删除优先于加回指） ----------
# B4/B10 的改法是删掉段首提示语/起手式，删后 B3 的触发对象不复存在，
# 同线双中时 B3 不得再报（规则优先级见 SKILL.md B3）。
OVERLAP_B4 = "第一段铺垫，没有任何问题。\n\n关键在于：预算不够。\n"
OVERLAP_B10 = "第一段铺垫，没有任何问题。\n\n说白了，预算不够。\n"
check("双报-B4", OVERLAP_B4, ["B4"], [])
check("双报-B10", OVERLAP_B10, ["B10"], [])
# B4/B10 命中在行内其他位置时，同行的 B3 触发语删后照旧存在，必须照报
# （旧实现按行抑制，把同行其他位置的 B3 病灶一起吞掉）
SAME_LINE_B4_B3 = ("第一段内容在这里。\n\n值得注意的是，配置管理往往被忽视。"
                   "原因如下：一是人，二是钱。\n")
check_mode("双报-B4同行不吞B3", SAME_LINE_B4_B3, "prose", [], ["B3", "B4"])

# B4a 只对句首命中发 FIX。句中命中（"这个方案的核心是：三个模块。"）
# 按 note 教"不带信息则删"会删出病句，且与 rules-full B4"总说分说不改"矛盾，
# 降为 REVIEW 交人判。
check_mode("B4a-句首发FIX", "一句话总结：连接池打满了。",
           "prose", ["B4"], [])
check_mode("B4a-句中核心是降REVIEW", "这个方案的核心是：三个模块。",
           "prose", [], ["B4"])
check_mode("B4a-句中关键在于降REVIEW", "问题的关键在于：连接池。",
           "prose", [], ["B4"])
check_mode("B4a-句首发FIX-原因如下", "原因如下：一、人。二、钱。",
           "prose", ["B4"], [])

# ---------- 规则页机械层覆盖表 vs 扫描器模式集（防漂移） ----------
# rules-full.md 的覆盖表是规范源，FIX_RULES/REVIEW_RULES 是实现；两者不一致
# 即"规则说报而扫描器不报"（B9 曾缺 prose、B14 曾缺 fiction 的缺口类型）。
_RULES_FULL = (Path(__file__).resolve().parent.parent / "references"
               / "rules-full.md").read_text(encoding="utf-8")
_exp_fix = {"prose": set(), "fiction": set(), "gen": set()}
_exp_rev = {"prose": set(), "fiction": set(), "gen": set()}
_in_table = False
for _line in _RULES_FULL.splitlines():
    if _line.startswith("| 规则 |"):
        _in_table = True
    if not _in_table or not _line.startswith("|"):
        if _in_table:
            break
        continue
    _cells = [c.strip() for c in _line.strip().strip("|").split("|")]
    if len(_cells) < 4:
        continue
    _ids = re.findall(r"[BCD]\d{1,2}", _cells[0])
    if not _ids:
        continue
    for _mode, _cell in zip(("prose", "fiction", "gen"), _cells[1:4]):
        if _cell == "FIX":
            _exp_fix[_mode].update(_ids)
        elif _cell == "REVIEW":
            _exp_rev[_mode].update(_ids)
        elif _cell.startswith("经 "):
            _exp_rev[_mode].add("B12")
for _mode in ("prose", "fiction", "gen"):
    if set(FIX_RULES[_mode]) != _exp_fix[_mode]:
        failures.append(
            f"覆盖表-{_mode} FIX: 规则页 {sorted(_exp_fix[_mode])} vs "
            f"扫描器 {sorted(FIX_RULES[_mode])}")
    if set(REVIEW_RULES[_mode]) != _exp_rev[_mode]:
        failures.append(
            f"覆盖表-{_mode} REVIEW: 规则页 {sorted(_exp_rev[_mode])} vs "
            f"扫描器 {sorted(REVIEW_RULES[_mode])}")

# ══════════════════════ 漏报与误报补充回归 ══════════════════════
# B1 fiction 豁免：B 侧是抽象概念词时不是事实清点，两种模式都报
for _n, _t in [
    ("B1-抽象-结束开始", "这不是结束，是开始。"),
    ("B1-抽象-终点起点", "那不是终点，是新的起点。"),
    ("B1-抽象-害怕表演勇敢", "她不是害怕，是在表演勇敢。"),
    ("B1-抽象-调试赌博", "这不是调试，是赌博。"),
    ("B1-抽象-妥协智慧", "这不是妥协，是智慧。"),
    ("B1-抽象-英雄幸存者", "他不是英雄，是幸存者。"),
    ("B1-抽象-爱依赖", "这不是爱，是依赖。"),
    ("B1-抽象-主语是形", "这不是结束，这是另一个开始。"),
    ("B1-抽象-分号分隔", "这不是结束；是开始。"),
    ("B1-抽象-顿号分隔", "这不是结束、是开始。"),
    ("B1-抽象-不在A在B", "问题不在代码，在态度。"),
    ("B1-抽象-错不在方法", "错不在方法，在执行。"),
]:
    check_mode(_n, _t, "fiction", [], ["B1"])
    check_mode(_n + "-prose", _t, "prose", [], ["B1"])

# B1 fiction 豁免：B 侧能拍成画面的事实清点仍放行（"主语+是"形不得误报）。
# 裸代词重复的清点句另由 B17 的否定-对比豁免放过（fiction.md 二.8"对比复用
# 放行"），不进句内主语复现串，故 fiction 模式零命中。
for _n, _t in [
    ("B1-清点-主语是", "他不是我的老板，他是我的客户。"),
    ("B1-清点-雪盐", "那不是雪，那是盐。"),
    ("B1-清点-狗狼", "它不是狗，它是狼。"),
    ("B1-清点-告别送行", "她们不是来告别的，她们是来送行的。"),
    ("B1-清点-客人家里人", "你们不是客人，你们是家里人。"),
    ("B1-清点-逃与追", "他不是在逃，他是在追。"),
    ("B1-清点-换了路", "他不是失败了，他是换了一条路。"),
    ("B1-清点-不在家在公", "他不在家，在公司。"),
    ("B1-清点-可乐啤酒", "冰箱里没有可乐，只有啤酒。"),
    ("B1-清点-哭笑", "她不是哭，是在笑。"),
]:
    check_mode(_n, _t, "fiction", [], [])

# B9："一般"是副词（＝通常）不是明喻收尾；喻体非空的明喻照报
for _n, _t, _w in [
    ("B9-一般副词-画像", "关于他的画像一般都是披着长发。", False),
    ("B9-一般副词-情况下", "像一般情况下，我们会先备份数据。", False),
    ("B9-一般副词-而言", "像一般而言，这事没有先例。", False),
    ("B9-一般副词-图像", "图像一般存放在单独的分区。", False),
    ("B9-一般副词-像一般人", "他像一般人那样点了点头。", False),
    ("B9-明喻-羲皇时候", "寂静到像羲皇时候一般太平。", True),
    ("B9-明喻-回复乞丐", "现了十分烦厌的相貌，像回复乞丐一般的摇手道。", True),
]:
    check_mode(_n, _t, "gen", [], ["B9"] if _w else [])

# B9 新喻标记（量词已由上方量词循环全量覆盖）
for _n, _t in [
    ("B9-俨然", "他俨然一座山。"),
    ("B9-恍若", "她恍若一片落叶。"),
    ("B9-好似", "他好似一头雾。"),
    ("B9-似的", "她像一朵花似的。"),
]:
    check_mode(_n, _t, "gen", [], ["B9"])

# C5：fiction.md 二.5 明列"时间静止"，原正则只认"停止"
for _n, _t in [
    ("C5-时间仿佛凝固", "时间仿佛凝固了。"),
    ("C5-时间仿佛静止", "时间仿佛静止了。"),
    ("C5-时间似乎凝固", "时间似乎凝固了。"),
    ("C5-连时间也停止", "连时间也停止了流动。"),
    ("C5-时间终于停止", "时间终于停止了流动。"),
]:
    check_mode(_n, _t, "gen", [], ["C5"])
# 问句与事实陈述不报（N2 问句保护）
for _n, _t in [
    ("C5-问句不报", "时间停止了流动吗？"),
    ("C5-三年停止流浪不报", "他花了三年时间停止了流浪。"),
]:
    check_mode(_n, _t, "gen", [], [])

# B5：整行粗体是强调不是小标题，破折号照报；# 标题仍免责
check_mode("B5-粗体行照报", "**他说——不，他什么都没说**", "gen", [], ["B5"])
check_mode("B5-标题行免责", "## 他说——不，他什么都没说", "gen", [], [])

# B17：整行"叙述+他说：引语"算对白行，12 个标签不得因分母为 0 被跳过
_B17_INLINE_DENSE = "\n".join(
    f"他站起来。他说：\u201c第{i}条不行。\u201d" for i in range(1, 13)) + "\n"
check_mode("B17-内联标签密度", _B17_INLINE_DENSE, "gen", [], ["B17"])

# 判定必须在所有断言之后：任何一段只 append 不复检，失败就影响不了退出码
if failures:
    print("红灯测试未通过：")
    print("\n".join(failures))
    sys.exit(1)
print("红灯测试通过：人类组 FIX 零命中，重点病灶全部捕获，白名单与边界样例零误伤")
