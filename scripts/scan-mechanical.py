"""机械规则确定性扫描器：B4 / B6 / B10 / B11（FIX 级）＋ B1 / B3（REVIEW 级）。

定位：生成候选命中清单，供 LLM 复核语境后决定是否改写。
脚本只报触发标记，不做自动改写——语境判断（如 B4 提示语是否承接上文、
B11 是否法规条目）仍由模型或人完成。依据 SKILL.md 执行要求
"低成本检查一律实搜不凭印象"，本脚本把"实搜"固化下来。

覆盖规则分两级：
  FIX 级（高精度，命中基本即可改）：
  B4  冒号滥用：提示语引出（一句话总结：/核心是：……）＋空转句引列表
  B6  序数词通篇编号小标题（连续 ≥3 个才报）
  B10 起手式：说白了 / 说穿了 / 先说结论（句首位置）
  B11 顿号罗列过密：一个分句内 ≥2 个顿号串 ≥3 项并列
  REVIEW 级（[机械] 标签但须复核语境，只报候选）：
  B1  翻案腔：句中含"而是/其实/恰恰"——被否定的观点是否存在须读上下文
  B3  段首零回指评论：非首段以评论语开头且整句无"这/那/其/此/上面"

白名单（绝对原则，完全豁免）：围栏代码块、行内代码、YAML frontmatter、
表格行、引用块（> 起首）、URL、Markdown 列表内部（B11）。

输出附注：全文无空行分段时 B3 无从执行，打印一行提示，不改退出码。
文件解码按 utf-8-sig（兼容 BOM）→ gbk 依序尝试，均失败打印跳过说明并继续。

用法：
  python scripts/scan-mechanical.py <文件> [文件...] [--mode prose|fiction]
  python scripts/scan-mechanical.py -          # 读 stdin
退出码：0 无命中，1 有命中，2 用法错误。
自测：python scripts/test-scan-mechanical.py

模式（对应 SKILL.md 清理 / fiction 清理两种清理流程的带入集）：
  prose（默认）  全量规则
  fiction        只报 fiction 清理带入集内可机械定位的 B6(FIX) 与 B1(REVIEW)；
                 B3/B4/B10/B11 的倍率来自非虚构论述文体对照，fiction 不带入，
                 一律不报（对小说照报即越界误伤）
"""
import argparse
import re
import sys
from pathlib import Path

# ---------- 触发标记 ----------

# B10：句首起手式
B10_WORDS = ("说白了", "说穿了", "先说结论")

# B4a：提示语＋冒号（每个词必须出现在 references/rules-text.md 的 B4 触发行，见自测断言）
B4A_PROMPTS = ("一句话总结", "核心是", "关键在于", "原因如下", "本质上")

# B1（REVIEW 级）：翻案腔候选词
B1_WORDS = ("而是", "其实", "恰恰")

# B3（REVIEW 级）：段首评论语与回指词
B3_OPENERS = ("听起来", "看起来", "值得注意的是", "更重要的是",
              "关键在于", "问题在于", "说白了", "意味着", "不难看出")
B3_REFERENTS = ("这", "那", "其", "此", "上面")

# B6：编号小标题（一、二、三 / 第一、第二）
_HEADING_MD = re.compile(r"^(#{1,6})\s+(.+)$")
_HEADING_BOLD = re.compile(r"^\*\*(.+)\*\*\s*$")
_NUM_PREFIX = re.compile(r"^(?:[一二三四五六七八九十]+、|第[一二三四五六七八九十0-9]+[、，,\s])")

# 列表行（B4b 判定下文是否列表；B11 对列表内部豁免）
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.、)）])\s")

# 分句切分（B11 按分句判顿号密度；B10 按句判句首）
_CLAUSE_SPLIT = re.compile(r"[，。；：！？\n]")
_SENT_SPLIT = re.compile(r"[。！？；\n]")

_URL = re.compile(r"https?://\S+|www\.\S+")
_INLINE_CODE = re.compile(r"`[^`]*`")

# 各模式的报告集（见模块 docstring"模式"节）
FIX_RULES = {"prose": ("B4", "B6", "B10", "B11"), "fiction": ("B6",)}
REVIEW_RULES = {"prose": ("B1", "B3"), "fiction": ("B1",)}


def _mask_line(line):
    """行内代码与 URL 替换为等长占位，避免误命中。"""
    def _blank(m):
        return " " * len(m.group(0))
    line = _INLINE_CODE.sub(_blank, line)
    line = _URL.sub(_blank, line)
    return line


def _read_text(path):
    """utf-8-sig 兼容 BOM；GBK 回退；均失败返回 None。"""
    for enc in ("utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return None


def _iter_scannable_lines(text):
    """逐行产出 (行号, 原文, 屏蔽后文本)，跳过白名单区。"""
    in_code = False
    in_yaml = False
    lines = text.splitlines()
    for idx, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if idx == 1 and stripped == "---":
            in_yaml = True
            continue
        if in_yaml:
            if stripped == "---":
                in_yaml = False
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith("|"):  # 表格行豁免
            continue
        if stripped.startswith(">"):  # 引用块与引文豁免：引的是他人原文
            continue
        yield idx, raw, _mask_line(raw)


def _is_heading(masked):
    """返回小标题文字，非小标题返回 None。"""
    m = _HEADING_MD.match(masked.strip())
    if m:
        return m.group(2).strip()
    m = _HEADING_BOLD.match(masked.strip())
    if m:
        return m.group(1).strip()
    return None


def scan(text, mode="prose"):
    """返回命中列表：dict(line, rule, tier, snippet, note)。

    tier=FIX 高精度可据以改写；tier=REVIEW 只是候选，须读上下文复核。
    mode 按清理流程限定报告集，见模块 docstring。
    """
    hits = []
    fix_on = set(FIX_RULES[mode])
    review_on = set(REVIEW_RULES[mode])
    scannable = list(_iter_scannable_lines(text))

    # ---- B6：编号小标题，全篇统计 ≥3 才报 ----
    numbered = []
    for idx, raw, masked in scannable:
        title = _is_heading(masked)
        if title and _NUM_PREFIX.match(title):
            numbered.append((idx, title))
    if "B6" in fix_on and len(numbered) >= 3:
        for idx, title in numbered:
            hits.append(dict(line=idx, rule="B6", tier="FIX", snippet=title,
                             note=f"全篇编号小标题共 {len(numbered)} 个（≥3 触发）"))

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
                                    note="段首评论无回指：多数情况加一个“这”字；"
                                         "首段与引语内部不改"))
                            break
            prev_blank = False

    for pos, (idx, raw, masked) in enumerate(scannable):
        stripped = masked.strip()
        if not stripped:
            continue
        is_list_line = bool(_LIST_ITEM.match(masked))
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

        # ---- B11：分句内 ≥2 顿号（Markdown 列表内部豁免） ----
        if "B11" in fix_on and not is_list_line and not heading:
            for clause in _CLAUSE_SPLIT.split(masked):
                if clause.count("、") >= 2:
                    hits.append(dict(line=idx, rule="B11", tier="FIX",
                                     snippet=clause.strip(),
                                     note="分句内 ≥2 顿号串 ≥3 项：能概括就概括"))
                    break

    # 同点双报抑制：B4/B10 的改法是删掉段首提示语/起手式，删后 B3 的触发
    # 对象不复存在，同线命中时 B3 不报（优先级见 references/rules-text.md B3）
    if "B3" in review_on:
        drop = {h["line"] for h in hits if h["rule"] in ("B4", "B10")}
        hits = [h for h in hits if not (h["rule"] == "B3" and h["line"] in drop)]

    return hits


def main():
    parser = argparse.ArgumentParser(
        description="机械规则确定性扫描器（FIX 级 B4/B6/B10/B11；REVIEW 级 B1/B3）")
    parser.add_argument("files", nargs="*", help="待扫描文件；单独的 - 读 stdin")
    parser.add_argument("--mode", choices=("prose", "fiction"), default="prose",
                        help="prose=论述清理（默认，全量）；fiction=fiction 清理（只报 B6/B1）")
    args = parser.parse_args()
    if not args.files:
        parser.print_help(file=sys.stderr)
        sys.exit(2)
    total = 0
    for target in args.files:
        if target == "-":
            text, name = sys.stdin.read(), "<stdin>"
        else:
            path = Path(target)
            if not path.is_file():
                print(f"找不到文件：{target}", file=sys.stderr)
                sys.exit(2)
            text = _read_text(path)
            if text is None:
                print(f"{target}: 无法解码（非 UTF-8/GBK），跳过", file=sys.stderr)
                continue
            name = str(path)
        hits = scan(text, mode=args.mode)
        for h in hits:
            print(f"{name}:{h['line']}\t{h['rule']}\t{h['tier']}\t{h['snippet']}\t{h['note']}")
        total += len(hits)
        if "B3" in REVIEW_RULES[args.mode]:
            _lines = [l for l in text.splitlines() if l.strip()]
            _chunks = [c for c in re.split(r"\n\s*\n", text) if c.strip()]
            if len(_lines) > 1 and len(_chunks) < 2:
                print("# 提示：未检出空行分段，B3 未执行")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
