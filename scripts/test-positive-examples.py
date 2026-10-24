# -*- coding: utf-8 -*-
"""正解示例自检：全文档 ✅ 行与箭头改法示例不得自带病灶。

规则文档引用病灶（❌ 行）合法，但正解示例（✅ 行、→ 后的改法文本）
自身必须干净，否则"带病示人"。本脚本提取正解示例逐条过
scan-mechanical 的 B1 变体、破折号、B10/B4a 开场与 fiction 词表检查。

fiction 词表检查（B13 副词/B14 情绪贴标签/B15 抽搐与低吼/B16 回环/
B17 装饰标签/B12 宏观开场）源于一次实录：修订 B5 示例时把"极慢"
写进 ✅ 行，而 B13 明令清除该词——旧检查面（只查 B1/破折号/B10/B4a）
放行，靠人工肉眼拦截。凡正解示例命中这些词表即失败。

误报控制：❌ 行的病灶文本与 ✅ 行同行时，只提取 ✅ 之后的部分；
❌ 与 → 之间的原文不检。

豁免只看文档：某行标了"放行"（规则承认为合法输出的句式，如 B1 纠错放行），
该行的正解示例不查 B1 对举。判据写在文档里，本脚本不存字符白名单——
曾有一份白名单把"不是A，是B"的病灶示例整条跳过，绿灯是假的。
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

spec = importlib.util.spec_from_file_location(
    "scan_mechanical", Path(__file__).resolve().parent / "scan-mechanical.py")
sm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sm)

# 规则正文：参与「正解示例不得带病灶」检查。
# README 不在交付仓库里（项目文档与分发包统一放仓库外），故不纳入。
DOCS = ["SKILL.md", "CONTRIBUTING.md",
        "references/fiction.md", "references/rules-full.md"]
# 正解示例检查只针对规则文档；CONTRIBUTING 是给人看的贡献指南，
# 里面提到某个禁用词（说明历史坑）不是「带病示人」，误判成示例反而挡路。
SAMPLE_DOCS = ["SKILL.md", "references/fiction.md", "references/rules-full.md"]

# fiction 词表与宏观开场：正解示例命中即失败（规则明文清除的形态）
FICTION_CHECKS = [
    ("B13 副词", lambda s: sm._B13_ADVERBS.search(s)),
    ("B14 情绪贴标签", lambda s: sm._B14_EMOTION.search(s)),
    ("B15 抽搐/低吼", lambda s: sm._B15_SPASM.search(s)),
    ("B16 回环", lambda s: sm._B16_LOOP.search(s)
     or sm._B16_TIME_EXT.search(s)),
    ("B17 装饰标签", lambda s: sm._B17_FANCY_TAGS.search(s)),
    ("B12 宏观开场", lambda s: sm._MACRO_OPENER.search(s)),
]


# 正解示例的引号配对，逐个尝试。全角弯引号优先：文档里的示例以全角为主，且样本
# 内部可能含行内代码（“跑一下 `--version` 就能定。”），所以全角样本不把反引号
# 当终止符。反引号与 ASCII 双引号是另外两种配对（fiction.md 的示例用反引号）。
_QUOTE_PAIRS = (("\u201c", "\u201d"), ("`", "`"), ("\"", "\""))


def extract_positive_samples(line):
    """从一行提取正解示例文本：→ 后接 ✅ 的带引号部分。

    引号内即样本，不含 ✅ 后面的行尾说明——早前字符类漏了全角引号，精确提取
    永不命中，只剩贪婪回退兜底，会把行尾说明一并吞进样本。
    """
    samples = []
    for opener, closer in _QUOTE_PAIRS:
        inner = "[^" + closer + "]+"
        patterns = (r"→\s*✅\s*" + opener + r"(" + inner + r")" + closer,
                    r"(?<!❌)✅\s*" + opener + r"(" + inner + r")" + closer)
        for pattern in patterns:
            for m in re.finditer(pattern, line):
                samples.append(m.group(1))
    if not samples:
        # ✅ 后裸文本（至行尾）：没有引号样本时才兜底
        stop = "".join(c for pair in _QUOTE_PAIRS for c in pair) + "→"
        for m in re.finditer(r"✅\s*([^" + stop + r"]+)$", line):
            text = m.group(1).strip()
            if len(text) >= 6:
                samples.append(text)
    return samples


def check_doc_dashes():
    """整篇破折号纪律：规则文本自己不许有 AI 味。

    口径直接取自 CONTRIBUTING「文档正文无破折号，`——` 只允许出现在
    ❌ 病灶示例与变体名中」。变体名指用 A/B 占位符指认禁用形态的写法
    （"不是A——是B"），那是病灶的名字，不是行文里的破折号。
    """
    # 变体名：破折号两侧是 A/B 占位符
    variant = re.compile(r"[AB]\s*——\s*|——\s*[AB]")
    bad = []
    for doc in DOCS:
        path = ROOT / doc
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "——" not in line:
                continue
            if "❌" in line or variant.search(line):
                continue
            bad.append((doc, lineno, line.strip()[:80]))
    return bad


def check_ellipsis_drop():
    """❌ 改 ✅ 不得用省略号吞掉原文。

    B5 的改法明写「只改破折号，信息不删」，示例却把主语换成「……」，
    等于教模型用省略号掩盖删除。判据：从 ❌ 到其后的 ✅ 这一段里，
    ❌ 侧没有省略号而 ✅ 侧有，即病灶。两侧都有省略号是合法用法
    （用省略号标出前后还有内容，两侧省略量一致）。
    """
    bad = []
    for doc in DOCS:
        path = ROOT / doc
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # 每对 ❌…✅ 是一个改写对照，按 ❌ 切段后看该段里的 ✅
            for seg in re.split(r"❌", line)[1:]:
                if "✅" not in seg:
                    continue
                left, _, right = seg.partition("✅")
                if "……" in right and "……" not in left:
                    bad.append((doc, lineno, right.strip()[:60]))
    return bad


# 规则说明里被引号包裹的「正在讨论的词」是合法引用，不是示例；
# ❌/✅ 后的样句才是示例。两类都要从"规则自身 AI 腔"检查里剥掉。
TONE_QUOTED = re.compile("[\"\u201c\u0060]([^\"\u201d\u0060\n]{1,}?)[\"\u201d\u0060]")
TONE_BAD = re.compile(r"❌[^\n]*")
TONE_GOOD = re.compile(r"✅[^\n]*")

# 正解示例自身不得带的 AI 腔（B1 变体由扫描器 _B1_VARIANT 单独判）
B1_SAMPLE_PATS = {
    "升华大命题": re.compile(r"不仅是.{1,18}更是|不只是.{1,18}更是"),
    "万能收尾": re.compile(r"关键在于找到平衡|要结合实际情况"),
    "客服腔": re.compile(r"希望这对你(?:有所)?帮助|希望对你有帮助"),
    "宏观开场": re.compile(r"在当今|众所周知|随着.{1,12}的发展"),
}

# 规则说明文字自身不得带的 AI 腔（示例已剥离）
TONE_PATS = dict(B1_SAMPLE_PATS)


def strip_examples(line):
    """剥掉 ❌ 病灶与 ✅ 正解示例，只留规则说明。"""
    line = TONE_BAD.sub("", line)
    line = TONE_GOOD.sub("", line)
    line = TONE_QUOTED.sub("", line)
    return line.replace("❌", "").replace("✅", "")

def check_rule_tone():
    """规则正文自身不得带 AI 腔。

    用户要求：规则自己不许有 AI 味。❌ 病灶示例与被引号包裹的「正在讨论的词」
    是合法引用，先剥离再扫；剩下的说明文字命中翻案腔、升华、客服腔、
    起手式即失败。破折号由 check_doc_dashes 专项把守。
    """
    bad = []
    for doc in DOCS:
        path = ROOT / doc
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            body = strip_examples(line)
            for name, pat in TONE_PATS.items():
                m = pat.search(body)
                if m:
                    bad.append((doc, lineno, name, m.group(0)[:40]))
    return bad


def main():
    failures = []
    total_samples = 0
    for doc in SAMPLE_DOCS:
        path = ROOT / doc
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "✅" not in line and "→" not in line:
                continue
            # 规则明文放行的只有一种情形：用户前提被证伪时的纠错/否证
            # （rules-full.md B1）。豁免就按这个说法给，不认"放行"两个字，
            # 否则随便哪行写个"放行"就能把病灶挡在检查之外。
            samples = [s.strip() for s in extract_positive_samples(line)]
            samples = [s for s in samples if s]
            total_samples += len(samples)
            exempt = (("纠错" in line or "否证" in line) and len(samples) == 1)
            for sample in samples:
                variants, tone_hits = [], []
                if not exempt:
                    variants = [m.group(0) for m in sm._B1_VARIANT.finditer(sample)]
                    # 排除模式语言（含 A/B 占位符的规则描述）
                    if re.search(r"\bA\b|\bB\b|A，|B[。）\"]", sample):
                        variants = [v for v in variants if "A" not in v and "B" not in v]
                    tone_hits = [name for name, pat in B1_SAMPLE_PATS.items()
                                 if pat.search(sample)]
                dash = sample.count("——") + len(
                    re.findall(r"(?<!—)—(?!—)", sample))
                # B10 起手式：正解示例句首不得用提示语开场
                lead_in = any(sample.startswith(w) for w in sm.B10_WORDS)
                # B4a 提示语＋冒号：正解示例不得以空提示语引出
                b4a = any(sample.startswith(w + "：") or sample.startswith(w + ":")
                          for w in sm.B4A_PROMPTS)
                if variants or tone_hits or dash or lead_in or b4a:
                    failures.append({
                        "doc": doc, "line": lineno, "sample": sample[:80],
                        "variants": variants, "dash": dash,
                        "lead_in": lead_in, "b4a": b4a, "tone": tone_hits})
                # fiction 词表：正解示例不得自带规则明文清除的形态
                fic_hits = [name for name, check in FICTION_CHECKS
                            if check(sample)]
                if fic_hits:
                    failures.append({
                        "doc": doc, "line": lineno, "sample": sample[:80],
                        "variants": [], "dash": 0, "lead_in": False,
                        "b4a": False, "fiction": fic_hits})

    # 提取正则失效（如字符类漏了全角引号）时样本数为 0，failure 为空照样
    # 报通过——静默绿灯。样本数下限把这条路堵死：文档删减样本须同步改下限。
    if total_samples < 40:
        print(f"提取到的 ✅ 样本仅 {total_samples} 个（预期 ≥40），提取正则疑似失效")
        return 1

    if failures:
        print(f"发现 {len(failures)} 处正解示例带病灶：")
        for f in failures:
            print(f"  {f['doc']}:{f['line']}")
            print(f"    sample: {f['sample']}")
            if f["variants"]:
                print(f"    B1 变体: {f['variants']}")
            if f.get("tone"):
                print(f"    B1 对举: {f['tone']}")
            if f["dash"]:
                print(f"    破折号: {f['dash']}")
            if f.get("lead_in"):
                print(f"    B10 起手式: 提示语开场")
            if f.get("b4a"):
                print(f"    B4a 提示语冒号: 空提示语引出")
            if f.get("fiction"):
                print(f"    fiction 词表命中: {', '.join(f['fiction'])}")
        return 1

    dash_bad = check_doc_dashes()
    if dash_bad:
        print(f"发现 {len(dash_bad)} 处正文破折号（错误示范外一律不带）：")
        for doc, lineno, text in dash_bad:
            print(f"  {doc}:{lineno}  {text}")
        return 1

    ell_bad = check_ellipsis_drop()
    if ell_bad:
        print(f"发现 {len(ell_bad)} 处正解用省略号吞掉原文（改法明写信息不删）：")
        for doc, lineno, text in ell_bad:
            print(f"  {doc}:{lineno}  {text}")
        return 1

    tone_bad = check_rule_tone()
    if tone_bad:
        print(f"发现 {len(tone_bad)} 处规则正文自带 AI 腔（错误示例之外）：")
        for doc, lineno, name, text in tone_bad:
            print(f"  {doc}:{lineno}  [{name}] {text}")
        return 1

    print("正解示例自检通过：全部 ✅ 示例零病灶，正文破折号仅出现在错误示范与禁用形态说明中，"
          "无省略号吞原文，规则正文无 AI 腔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
