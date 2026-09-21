"""清理模式 diff 审计：每处改动归属规则编号，信息守恒机械核验。

把 rules-full.md 成文清理边界中"每处改动对应一条编号，指不出对应规则的
撤销"与"信息守恒：每个实词能溯源到原文"从荣誉制变成可执行检查：

  1. difflib 行级对比原文/清理稿，产出改动块（hunk）
  2. 原文跑 scan-mechanical（prose 或 fiction），命中行号给改动块归属
  3. 守恒按内容字多重集计算（CJK 去功能字；拉丁字母与数字必计——名称、
     数字不得变动）：
     - 全文净删的内容字，删除点均无规则归属 → 无依据删除（按位置分组合并）
     - 全文净增的内容字 → 越权新增（原文已有字符的移位放行，只记块）
     - 有归属的块，净删内容字超出归属规则可解释范围 → 幅度超出归属
       （REVIEW 级候选只授权触发句内的句内手术；实测漏网：整段压缩
       借行内一个 B1 候选洗白为"有归属"——解释范围按归属命中所在句子
       圈定，句外净删即报）
  4. 纯功能字/标点改写（破折号改句号、删"了"）不触发——风险本来就低

归属口径：FIX 与 REVIEW 命中均可作归属，REVIEW 属复核依据（tier 随报告
给出，由人确认）；块级归属是近似，跨块移位由全文多重集兜底。

用法：
  python scripts/audit-cleanup.py <原文> <清理稿> [--mode prose|fiction]
退出码：0 守恒与归属通过，1 存在违规，2 用法/读取错误。
自测：python scripts/test-audit-cleanup.py
"""
import argparse
import difflib
import importlib.util
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

# 功能字：语法胶水，改写中增删不构成信息守恒事件（重写连接词是合法编辑）
_FUNC = set("的了是在和与就也都而把被让对为以及或又还再只便但并等"
            "呢吧啊呀么嘛之其这那着过很不没给向从到把")

# 拉丁字母与数字必计为内容字：名称、端口号、数字改动即违规
_CJK_LO, _CJK_HI = 0x4E00, 0x9FFF


def content_chars(text):
    """内容字多重集：CJK 去功能字 + 全部字母数字。"""
    counter = {}
    for ch in text:
        o = ord(ch)
        if _CJK_LO <= o <= _CJK_HI:
            if ch not in _FUNC:
                counter[ch] = counter.get(ch, 0) + 1
        elif ch.isalnum():
            counter[ch] = counter.get(ch, 0) + 1
    return counter


def _load_scanner():
    spec = importlib.util.spec_from_file_location(
        "scan_mechanical", Path(__file__).resolve().parent / "scan-mechanical.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 句边界含逗号：B1 翻案腔的骨架单元是分句（"不是A，而是B"的 A/B 各为
# 一单元），肯定面"而是B"是独立分句，整句删除时它单独塌缩。
# 最小豁免：分句内容字 ≤2 视为语气/连接成分（"说白了""，只是"类），
# 删除它们是合法句内手术，不构成骨架塌缩。
_SENT_BOUNDARY = re.compile(r"[。！？；，,]")
_CLAUSE_MIN_CHARS = 2


def _scope_chars(origin_lines, i1, i2, block_hits):
    """归属命中的解释范围：块内命中行内、以句边界切出的句子（含功能字过滤前）。

    REVIEW/FIX 命中的授权范围是其所在句子：解释力按"归属命中行的句边界"
    圈定，非命中句的内容字删除不获解释。命中行整行计入（命中行内的
    其他句子同享解释权，避免同句多命中切分过细的抖动）。
    """
    hit_lines = {h["line"] for h in block_hits}
    scope_chars = {}
    for ln, raw in enumerate(origin_lines[i1:i2], start=i1 + 1):
        if ln not in hit_lines:
            continue
        for seg in _SENT_BOUNDARY.split(raw):
            if not seg:
                continue
            for ch, n in content_chars(seg).items():
                scope_chars[ch] = scope_chars.get(ch, 0) + n
    return scope_chars


# 句子骨架存续线：授权句在清理稿中须存在共享 ≥50% 内容字的对应句。
# 合法句内手术（删"说白了"/"微微"、B1 删否定留肯定）保留句子主体；
# 整句蒸发（SNF-04）与肯定面蒸发（SF-08）都会跌破此线。
_SKELETON_RATIO = 0.5

# 触发分句整体可删的规则：改法就是重写/删除病灶分句本身
_CLAUSE_EXEMPT_RULES = {"B15", "B16", "F7", "B12", "C5"}
# 触发词短语可删的规则：按触发词内容字给预算（不动分句其余部分）
_PHRASE_BUDGET_RULES = ("B3", "B4", "B10", "C2", "C4", "C6",
                        "D2", "D3", "D4", "D5", "D6")


def _sentences(text):
    """按句边界切句，返回 [(句子文本, 内容字多重集)]。"""
    out = []
    for seg in _SENT_BOUNDARY.split(text):
        seg = seg.strip()
        if seg:
            out.append((seg, content_chars(seg)))
    return out


def _clause_spans(line):
    """返回 [(起止偏移, 分句文本)]，与 _SENT_BOUNDARY 切分一致。"""
    spans = []
    start = 0
    for part in _SENT_BOUNDARY.split(line):
        if part.strip():
            spans.append((start, start + len(part), part))
        start += len(part) + 1
    return spans


def _clause_at(spans, pos):
    for idx, (s, e, _) in enumerate(spans):
        if s <= pos < e:
            return idx
    return len(spans) - 1 if spans else 0


def _authority_scope(origin_lines, i1, i2, block_hits, cleaned_span,
                     scanner_mod):
    """授权句的骨架存续核查，返回超范围删除字表。

    以分句为骨架单元，按规则的改法给豁免与预算：
    - B1 变体（不是A，(而/只)是B / 没有A只有B / 看似A实则B）：改法
      "删否定留肯定"——否定侧分句豁免，肯定侧分句必须存活；
      实测漏网 SF-08 即肯定面蒸发、SNF-04 即命中句整句蒸发。
    - 短语删除类（B3/B4/B10/C*/D*）：触发词本身的内容字计入预算。
    - 分句重写类（B15/B16/F7/B12/C5）：触发分句豁免（改法即重写该分句）。
    - 其余命中句：与清理稿分句共享 ≥50% 内容字视为骨架存续。
    """
    hit_lines = {h["line"] for h in block_hits}
    hits_by_line = {}
    for h in block_hits:
        hits_by_line.setdefault(h["line"], []).append(h)
    clean_sents = _sentences(cleaned_span)
    over = {}
    for ln, raw in enumerate(origin_lines[i1:i2], start=i1 + 1):
        if ln not in hit_lines:
            continue
        masked = scanner_mod._mask_line(raw)
        spans = _clause_spans(masked)
        exempt = set()
        budget = {}
        for h in hits_by_line.get(ln, ()):
            rule = h["rule"]
            if rule == "B1":
                # 结构性豁免：变体否定侧分句（从触发词回溯到本句句首的
                # 全部前导分句——"用户要的不是更多的功能"这类否定对象
                # 会铺多个分句）+ "而是"所在分句的前一单元
                for m in scanner_mod._B1_VARIANT.finditer(masked):
                    start_clause = _clause_at(spans, m.start())
                    # 句首 = 同一句号/问叹号段落的起点；往前回溯到段首
                    sent_start = masked.rfind("。", 0, m.start())
                    excl_mark = max(masked.rfind("！", 0, m.start()),
                                    masked.rfind("？", 0, m.start()))
                    sent_start = max(sent_start, excl_mark, -1) + 1
                    for ci in range(_clause_at(spans, sent_start),
                                    start_clause + 1):
                        exempt.add(ci)
                pos = masked.find("而是")
                while pos >= 0:
                    idx = _clause_at(spans, pos)
                    # "而是"的否定对象在其同句前导分句，全部豁免
                    sent_start = masked.rfind("。", 0, pos)
                    excl_mark = max(masked.rfind("！", 0, pos),
                                    masked.rfind("？", 0, pos))
                    sent_start = max(sent_start, excl_mark, -1) + 1
                    first = _clause_at(spans, sent_start)
                    for ci in range(first, idx):
                        exempt.add(ci)
                    pos = masked.find("而是", pos + 2)
            elif rule in _CLAUSE_EXEMPT_RULES:
                pos = masked.find(h["snippet"][:6])
                exempt.add(_clause_at(spans, pos if pos >= 0 else 0))
            elif rule in _PHRASE_BUDGET_RULES:
                for ch, n in content_chars(h["snippet"]).items():
                    budget[ch] = budget.get(ch, 0) + n
        for idx, (_s, _e, seg) in enumerate(spans):
            if idx in exempt:
                continue
            r_chars = content_chars(seg)
            total = sum(r_chars.values())
            if not total:
                continue
            # 语气/连接成分豁免：仅对无 B1 肯定面身份的分句生效——
            # B1 的肯定侧（"而是耐心"只剩 2 个内容字）是信息本体，
            # 整体蒸发必须报，不得落入最小豁免
            is_b1_affirmative = False
            if any(h["rule"] == "B1" for h in hits_by_line.get(ln, ())):
                for m in scanner_mod._B1_VARIANT.finditer(masked):
                    if _clause_at(spans, m.end() - 1) == idx:
                        is_b1_affirmative = True
                        break
                if not is_b1_affirmative:
                    p = masked.find("而是", spans[idx][0] if idx == 0 else spans[idx - 1][1])
                    if 0 <= p < spans[idx][1] if idx < len(spans) else False:
                        is_b1_affirmative = True
            if total <= _CLAUSE_MIN_CHARS and not is_b1_affirmative:
                continue  # 语气/连接成分：删除属合法句内手术
            best_overlap = 0
            for _, c_chars in clean_sents:
                overlap = sum(min(n, c_chars.get(ch, 0))
                              for ch, n in r_chars.items())
                best_overlap = max(best_overlap, overlap)
            if best_overlap >= total * _SKELETON_RATIO:
                continue  # 骨架存续：句内手术在授权范围内
            # 骨架塌缩：先扣触发词预算，剩余计入超范围删除
            for ch, n in r_chars.items():
                spend = min(n, budget.get(ch, 0))
                if budget.get(ch, 0):
                    budget[ch] -= spend
                if n - spend > 0:
                    over[ch] = over.get(ch, 0) + (n - spend)
    return over


def audit(original, cleaned, mode="prose"):
    """返回 dict：hunks（逐块）、violations（无依据删除/越权新增/幅度超出）、净删净增字表。"""
    scanner_mod = _load_scanner()
    scan = scanner_mod.scan
    hits_by_line = {}
    for h in scan(original, mode=mode):
        hits_by_line.setdefault(h["line"], []).append(h)

    orig_lines = original.splitlines()
    clean_lines = cleaned.splitlines()
    matcher = difflib.SequenceMatcher(a=orig_lines, b=clean_lines,
                                      autojunk=False)
    hunks = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        block_hits = [h for ln in range(i1 + 1, i2 + 1)
                      for h in hits_by_line.get(ln, ())]
        rules = sorted({f"{h['rule']}/{h['tier']}" for h in block_hits})
        o_span = "\n".join(orig_lines[i1:i2])
        c_span = "\n".join(clean_lines[j1:j2])
        o_chars, c_chars = content_chars(o_span), content_chars(c_span)
        removed = {c: n for c, n in o_chars.items() if n > c_chars.get(c, 0)}
        added = {c: n for c, n in c_chars.items() if n > o_chars.get(c, 0)}
        # 幅度核查：授权句的骨架须在清理稿中存续（句内手术合法，
        # 整句蒸发与肯定面蒸发报"幅度超出归属"）
        scope_over = {}
        if rules and removed:
            over = _authority_scope(orig_lines, i1, i2, block_hits, c_span,
                                    scanner_mod)
            for ch, n in over.items():
                scope_over[ch] = n
        hunks.append({
            "tag": tag, "orig_line": i1 + 1, "clean_line": j1 + 1,
            "rules": rules, "removed": removed, "added": added,
            "scope_over": scope_over,
            "o_snippet": o_span.strip()[:60], "c_snippet": c_span.strip()[:60],
        })

    g_orig, g_clean = content_chars(original), content_chars(cleaned)
    g_removed = {c: g_orig[c] - g_clean.get(c, 0) for c in g_orig
                 if g_orig[c] > g_clean.get(c, 0)}
    g_added = {c: g_clean[c] - g_orig.get(c, 0) for c in g_clean
               if g_clean[c] > g_orig.get(c, 0)}

    # 违规按位置分组合并：同句删多字只报一处，字符表列全
    del_groups, add_groups, scope_groups = {}, {}, {}
    for ch in g_removed:
        bad = [h for h in hunks if h["removed"].get(ch) and not h["rules"]]
        if bad:
            key = tuple(h["orig_line"] for h in bad)
            del_groups.setdefault(key, {})[ch] = g_removed[ch]
    for ch in g_added:
        sites = [h for h in hunks if h["added"].get(ch)]
        if sites:
            key = tuple(h["clean_line"] for h in sites)
            add_groups.setdefault(key, {})[ch] = g_added[ch]
    for h in hunks:
        if h["scope_over"]:
            key = (h["orig_line"],)
            scope_groups.setdefault(key, {}).update(h["scope_over"])
    violations = []
    for where, chars in del_groups.items():
        first = next(h for h in hunks
                     if h["orig_line"] in where and not h["rules"])
        violations.append({"kind": "无依据删除", "chars": chars,
                           "side": "原文", "where": list(where),
                           "snippet": first["o_snippet"],
                           "hint": "无规则归属的实词删除：放回原位，或补指规则编号"})
    for where, chars in add_groups.items():
        first = next((h for h in hunks if h["clean_line"] in where), None)
        violations.append({"kind": "越权新增", "chars": chars,
                           "side": "改稿", "where": list(where),
                           "snippet": first["c_snippet"] if first else "",
                           "hint": "原文没有的实词出现在清理稿：删除，信息守恒禁增"})
    for where, chars in scope_groups.items():
        first = next(h for h in hunks if h["orig_line"] == where[0])
        violations.append({"kind": "幅度超出归属", "chars": chars,
                           "side": "原文", "where": list(where),
                           "snippet": first["o_snippet"],
                           "hint": "有归属但净删超出归属规则所在句子的解释范围："
                                   " REVIEW 候选只授权触发句内的句内手术，"
                                   "超范围压缩属过度清理，放回或按句拆块重清"})
    return {"hunks": hunks, "violations": violations,
            "g_removed": g_removed, "g_added": g_added}


def _fmt(chars):
    return ",".join(f"{c}×{n}" for c, n in sorted(chars.items())) or "-"


def render(result):
    lines = []
    for h in result["hunks"]:
        rules = ",".join(h["rules"]) or "无归属"
        lines.append(f"块 原文行{h['orig_line']} {h['tag']} "
                     f"归属[{rules}] 净删[{_fmt(h['removed'])}] "
                     f"净增[{_fmt(h['added'])}]")
    for v in result["violations"]:
        lines.append(f"违规 {v['kind']} [{_fmt(v['chars'])}] "
                     f"@{v['side']}行{v['where']} 「{v['snippet']}」 {v['hint']}")
    attributed = sum(1 for h in result["hunks"] if h["rules"])
    lines.append(f"汇总：改动块 {len(result['hunks'])}（归属 {attributed}），"
                 f"全文净删内容字 {_fmt(result['g_removed'])}，"
                 f"全文净增内容字 {_fmt(result['g_added'])}")
    return "\n".join(lines)


def main(argv):
    parser = argparse.ArgumentParser(
        description="清理模式 diff 审计（信息守恒 + 改动归属）")
    parser.add_argument("original", help="原文文件路径（- 读 stdin）")
    parser.add_argument("cleaned", help="清理稿文件路径")
    parser.add_argument("--mode", choices=("prose", "fiction"), default="prose",
                        help="fiction 清理按 fiction 带入集归属（默认 prose）")
    args = parser.parse_args(argv[1:])
    try:
        original = (sys.stdin.read() if args.original == "-"
                    else Path(args.original).read_text(encoding="utf-8-sig"))
        cleaned = Path(args.cleaned).read_text(encoding="utf-8-sig")
    except OSError as error:
        print(f"读取失败：{error}", file=sys.stderr)
        return 2
    result = audit(original, cleaned, mode=args.mode)
    print(render(result))
    return 1 if result["violations"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
