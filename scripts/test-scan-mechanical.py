"""scan-mechanical.py 自测：回归集红灯测试。

设计原则：先证明脚本能捕获已知缺陷（红灯真红），再采信"零命中"结论。
- 人类组（A1–A5、C1）：FIX 级必须 0 命中；
  A4 的"其实"与叙述破折号可报 B1/B5 候选（候选不授权自动改写）。
- AI 腔组 AI-1：必须命中 B10(FIX)＋B1(REVIEW)——测不出即脚本失效。
  AI-1 为单段文本，B3 按规则定义（非首段）不触发。
- AI 腔组 AI-2：病灶是 B2（非机械规则），必须 0 命中——误命中即误伤。
- 种植病灶组：B1/B3/B4/B5/B6/B11/F7 各一处，缺一即脚本漏检。
- 边界组：引用与行内引文豁免、行内代码、表格、B4 触发词、BOM、GBK、B3 分段。

运行：python scripts/test-scan-mechanical.py
"""
import importlib.util
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "scan_mechanical", Path(__file__).resolve().parent / "scan-mechanical.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
scan = _mod.scan

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
check("A4", A4, [], ["B1", "B5"])

# AI 腔组
check("AI-1", AI_1, ["B10"], ["B1"])
check("AI-2", AI_2, [])

# 种植病灶：漏一个都是红灯
check("种植-B1", PLANTED_B1, [], ["B1"])
check("种植-B3", PLANTED_B3, [], ["B3"])
check("种植-B4a", PLANTED_B4A, ["B4"])
check("种植-B4b", PLANTED_B4B, ["B4"])
check("种植-B5", PLANTED_B5, [], ["B5"], {"B5": 1})
check("种植-B5-单破折号", PLANTED_B5_SINGLE, [], ["B5"], {"B5": 1})
check("种植-B6", PLANTED_B6, ["B6"], [], {"B6": 3})
check("种植-B11", PLANTED_B11, ["B11"], [], {"B11": 1})

_b3_hits = scan(PLANTED_B3)
if any("加一个" in h["note"] for h in _b3_hits if h["rule"] == "B3"):
    failures.append("B3 改法仍在机械补‘这’字，会生成‘这值得注意的是’一类病句")

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

# 触发词一致性：B4A_PROMPTS 每个词必须在 rules-text.md 的 B4 触发行中
_RULES_TEXT = (Path(__file__).resolve().parent.parent
               / "references" / "rules-text.md").read_text(encoding="utf-8")
_B4_SECTION = _RULES_TEXT.split("**B5")[0]
for _w in _mod.B4A_PROMPTS:
    if _w not in _B4_SECTION:
        failures.append(f"触发词越权：B4A_PROMPTS 的「{_w}」不在 references/rules-text.md 的 B4 触发行中")

# ---------- 模式感知 ----------
# fixture 取自公版语料（呼蘭河傳）真实段落：含多处顿号串，是人类小说的正常写法。
# SKILL.md 规定 fiction 清理不带入 B3/B4/B9/B10/B11，扫描器 --mode fiction 必须抑制；
# B6/B1 在带入集内，末尾种植的编号小标题与"而是"句必须照报。
FICTION_FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "fiction-sample.txt"
                   ).read_text(encoding="utf-8")


def check_mode(name, text, mode, expect_fix, expect_review=()):
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


check_mode("fixture-fiction", FICTION_FIXTURE, "fiction", ["B6"], ["B1"])
check_mode("fixture-prose", FICTION_FIXTURE, "prose", ["B6", "B11"], ["B1"])
check_mode("fiction-叙述破折号", PLANTED_B5, "fiction", [], ["B5"])
check_mode("fiction-久到回环", PLANTED_F7, "fiction", [], ["F7"])
check_mode("fiction-句号久到回环", PLANTED_F7_PERIOD, "fiction", [], ["F7"])
check_mode("fiction-分号久到回环", PLANTED_F7_SEMICOLON, "fiction", [], ["F7"])

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
_r = _cli("--mode", "bogus", "-", stdin=PLANTED_B11)
if _r.returncode != 2:
    failures.append(f"CLI 非法 mode: 预期 exit 2，实际 exit {_r.returncode}")

# ---------- CLI：BOM 豁免 / GBK 回退 / B3 无空行告警 ----------
import tempfile

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
    if _r.returncode != 0 or "未检出空行分段" not in _r.stdout:
        failures.append(f"CLI B3 告警: 预期 exit 0 且输出无空行分段提示，实际 exit {_r.returncode}\n{_r.stdout}")

    _scan_dir = Path(_td) / "scan-dir"
    (_scan_dir / "nested").mkdir(parents=True)
    (_scan_dir / "clean.md").write_text("正文没有触发项。", encoding="utf-8")
    (_scan_dir / "nested" / "hit.txt").write_text(PLANTED_B5_SINGLE, encoding="utf-8")
    (_scan_dir / "ignored.bin").write_bytes(b"\x00\xff\x00")
    _r = _cli(str(_scan_dir))
    if _r.returncode != 1 or "hit.txt" not in _r.stdout or "B5" not in _r.stdout:
        failures.append(f"CLI 目录递归: 预期只扫描文本文件并报 nested/hit.txt 的 B5，实际 exit {_r.returncode}\n{_r.stdout}{_r.stderr}")

# ---------- 同点双报抑制（删除优先于加回指） ----------
# B4/B10 的改法是删掉段首提示语/起手式，删后 B3 的触发对象不复存在，
# 同线双中时 B3 不得再报（规则优先级见 references/rules-text.md B3）。
OVERLAP_B4 = "第一段铺垫，没有任何问题。\n\n关键在于：预算不够。\n"
OVERLAP_B10 = "第一段铺垫，没有任何问题。\n\n说白了，预算不够。\n"
check("双报-B4", OVERLAP_B4, ["B4"], [])
check("双报-B10", OVERLAP_B10, ["B10"], [])

if failures:
    print("红灯测试未通过：")
    print("\n".join(failures))
    sys.exit(1)
print("红灯测试通过：人类组 FIX 零命中，重点病灶全部捕获，白名单与边界样例零误伤")
