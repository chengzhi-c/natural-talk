"""natural-talk 评测环静态判分：机械断言 + 留存率 + 清除率统计。

三层判分（判据先于跑分定稿）：
  L1 硬失败：require 断言缺失 / 留存率低于样例下限 / 输出缺失 → FAIL
  L2 风格：forbid 断言命中 / 扫描 FIX 残留 → WARN
  L3 观察：扫描 REVIEW 残留计数、留存率分布，只记录不进门槛

冻结协议：manifest.json 记录每份样例的 SHA256；判分前逐一核对，
不符即拒绝（防放水条款 1 的机械执行）。--freeze 首次冻结；样例或预期
有意变更须在 manifest 的 changes 里逐条记理由后重算。

用法：
  python evals/check-eval.py evals/runs/<run-dir> [--evals <dir>] [--report <md>]
  python evals/check-eval.py --freeze [--evals <dir>]
退出码：L1 失败=1；仅 L2 警告=0；冻结校验失败=1。
自测：python scripts/test-eval-harness.py
"""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import _loader

_loader.ensure_utf8()

EVALS_DIR = Path(__file__).resolve().parent
ROOT = EVALS_DIR.parent
SCRIPTS = ROOT / "scripts"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scan_mod = _load("scan_mechanical", SCRIPTS / "scan-mechanical.py")
_retention_mod = _load("check_retention", SCRIPTS / "check-retention.py")
scan = _scan_mod.scan
retention = _retention_mod.retention
RETENTION_CEILING = _retention_mod.RETENTION_CEILING

# 冻结字段：凡改变判分结果的 benchmark 字段都同样例一起冻。只冻样例文本不冻
# 判据，跑分后改一个 prompt_type 就能把留存约束整条绕开
FROZEN_FIELDS = ("case", "prompt_type", "system", "scan_mode", "temperature",
                 "assertions", "retention_min", "retention_max", "overlap_min")

# 实词 2-gram 重合度下限：留存率只是字数比，"关键词 + 的的的"填充就能把字数补回来
# （实测留存 0.91 而内容 100% 丢失）。真人清理产出的重合度最低 0.57，故下限取 0.5。
CONTENT_OVERLAP_FLOOR = 0.5


def content_overlap(original, cleaned):
    """原文 2-gram 在清理稿中的命中比例（去空白）。"""
    def grams(text):
        flat = re.sub(r"\s+", "", text)
        return {flat[i:i + 2] for i in range(len(flat) - 1)}
    base = grams(original)
    if not base:
        return 1.0
    return len(base & grams(cleaned)) / len(base)


def load_benchmark(evals_dir):
    entries = []
    for line in (evals_dir / "benchmark.jsonl").read_text(
            encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def case_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scorer_fingerprint():
    """判分器指纹：三个脚本的 sha256。只冻 benchmark 与样例时，改判分逻辑
    （阈值、规则集、判分分支）能让历史成绩无声失真，指纹把这条路也堵上。"""
    paths = [Path(__file__).resolve(),
             SCRIPTS / "scan-mechanical.py",
             SCRIPTS / "check-retention.py"]
    return {str(p.relative_to(ROOT)).replace("\\", "/"):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def check_frozen(evals_dir):
    """核对样例指纹与全部判据字段；返回失败清单。

    判据与样例同冻：只冻样例文本不冻判据，改 benchmark 阈值即可放水（防放水条款的
    另一半）。凡影响判分的字段全量比对（prompt_type/system/scan_mode/temperature/
    case/assertions/retention_min），并反向遍历 manifest——benchmark 里被删掉的用例
    同样报失败，否则删掉难过的一例就能无声提高通过率。
    """
    manifest_path = evals_dir / "manifest.json"
    if not manifest_path.exists():
        return ["manifest.json 不存在：先运行 --freeze 冻结基线"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frozen_cases = manifest.get("cases", {})
    failures = []
    seen = set()
    for entry in load_benchmark(evals_dir):
        case_id = entry["id"]
        seen.add(case_id)
        recorded = frozen_cases.get(case_id)
        if recorded is None:
            failures.append(f"{case_id}: manifest 未收录（新增样例须显式冻结并记理由）")
            continue
        actual = case_sha256(evals_dir / entry["case"])
        if actual != recorded["sha256"]:
            failures.append(f"{case_id}: 样例内容与冻结指纹不符（防放水条款："
                            f"跑分后不得改样例；确需变更先在 manifest.changes 记理由）")
        for field in FROZEN_FIELDS:
            if entry.get(field) != recorded.get(field):
                failures.append(f"{case_id}: 判据 {field} 与冻结快照不符（改阈值/断言须先在 "
                                f"manifest.changes 记理由后重冻结）")
    for case_id in sorted(set(frozen_cases) - seen):
        failures.append(f"{case_id}: manifest 已冻结但 benchmark.jsonl 中没有该用例"
                        f"（删除用例同样要记理由，否则删掉难过的一例即可提高通过率）")
    recorded_scorer = manifest.get("scorer")
    if recorded_scorer and recorded_scorer != scorer_fingerprint():
        failures.append("判分器指纹与冻结快照不符：判分逻辑被动过，"
                        "历史成绩不可比（须先在 manifest.changes 记理由后重冻结）")
    return failures


def freeze(evals_dir, reason=None):
    """冻结基线。判据字段相对旧快照有变化时必须给 --reason，否则拒绝写入。

    没有这道闸，"有意变更须记理由"只靠自觉：改掉断言后直接 --freeze 会把痕迹
    一并抹掉，changes 永远停在第一次冻结时的条目。
    """
    manifest_path = evals_dir / "manifest.json"
    manifest = {"frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "cases": {}, "changes": [], "scorer": scorer_fingerprint()}
    old_cases = {}
    old_scorer = {}
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["changes"] = old.get("changes", [])
        old_cases = old.get("cases", {})
        old_scorer = old.get("scorer", {})
    drifted = []
    for entry in load_benchmark(evals_dir):
        new = {"case": entry["case"],
               "sha256": case_sha256(evals_dir / entry["case"]),
               **{f: entry.get(f) for f in FROZEN_FIELDS}}
        old = old_cases.get(entry["id"])
        # drift 比 sha256 + 全部判据字段：只比判据时，篡改样例文本再 --freeze
        # 会把指纹静默改写，changes 不新增，之后判分全放行
        if old is not None and (old.get("sha256") != new["sha256"]
                                or any(old.get(f) != new[f]
                                       for f in FROZEN_FIELDS)):
            drifted.append(entry["id"])
        manifest["cases"][entry["id"]] = new
    for case_id in sorted(set(old_cases) - set(manifest["cases"])):
        drifted.append(case_id)
    if old_scorer and old_scorer != manifest["scorer"] and not reason:
        raise SystemExit(
            "拒绝冻结：判分器指纹相对旧快照有变化"
            f"（{', '.join(sorted(old_scorer))}）。改判分逻辑同样要记理由")
    drifted_scorer = bool(old_scorer) and old_scorer != manifest["scorer"]
    if drifted and not reason:
        raise SystemExit(
            f"拒绝冻结：以下用例的判据相对旧快照有变化（{', '.join(drifted)}）。"
            f"有意变更请用 --freeze --reason 说明理由，变更会记入 manifest.changes")
    if drifted or drifted_scorer:
        entry = {"at": manifest["frozen_at"], "reason": reason}
        if drifted:
            entry["cases"] = drifted
        if drifted_scorer:
            entry["scorer"] = "判分逻辑变更（见 reason）"
        manifest["changes"].append(entry)
    manifest_path.write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return len(manifest["cases"])


def evaluate_case(entry, case_text, output_text):
    """单例判分。返回 verdict（PASS/WARN/FAIL）与明细。"""
    details = []
    verdict = "PASS"

    def fail(detail):
        nonlocal verdict
        verdict = "FAIL"
        details.append(detail)

    def warn(detail):
        nonlocal verdict
        if verdict != "FAIL":
            verdict = "WARN"
        details.append(detail)

    # ---- 断言 ----
    for a in entry.get("assertions", []):
        kind = a["type"]
        level = a.get("level", "l2")
        if kind == "require_final_regex":
            if re.search(a["pattern"], output_text) is None:
                (fail if level == "l1" else warn)(
                    {"kind": "require", "pattern": a["pattern"],
                     "why": "终稿缺失应保留内容"})
        elif kind == "forbid_final_regex":
            m = re.search(a["pattern"], output_text)
            if m is not None:
                (fail if level == "l1" else warn)(
                    {"kind": "forbid", "pattern": a["pattern"],
                     "hit": m.group(0), "why": "病灶残留"})
        elif kind == "min_output_chars":
            if len(output_text.strip()) < a["value"]:
                fail({"kind": "min_output_chars", "value": a["value"],
                      "actual": len(output_text.strip()), "why": "输出缺失或过短"})
        else:
            fail({"kind": "unknown_assertion", "type": kind,
                  "why": "断言类型未实现"})

    # ---- 留存率（retell 复述不作留存约束） ----
    ratio = None
    if entry.get("prompt_type") == "clean":
        ratio = retention(case_text, output_text)
        floor = entry.get("retention_min")
        ceiling = entry.get("retention_max", RETENTION_CEILING)
        # 三条判据各自独立：串在 else 后面时，膨胀或缩水的输出会整段跳过
        # 重合度核查，"关键词 + 填充"在膨胀形态下就抓不到
        if floor is not None and ratio < floor:
            fail({"kind": "retention", "ratio": round(ratio, 4),
                  "floor": floor, "why": "清理稿缩水超样例下限"})
        if ratio > ceiling:
            fail({"kind": "retention", "ratio": round(ratio, 4),
                  "ceiling": ceiling, "why": "清理稿膨胀超上限（加料同属新增原文没有的内容）"})
        overlap_floor = entry.get("overlap_min", CONTENT_OVERLAP_FLOOR)
        overlap = content_overlap(case_text, output_text)
        if overlap < overlap_floor:
            fail({"kind": "overlap", "ratio": round(overlap, 4),
                  "floor": overlap_floor,
                  "why": "实词 2-gram 重合度过低：关键词加填充补字数，"
                         "内容实际已丢失"})

    # ---- 扫描：FIX 残留进 L2，REVIEW 残留只计数 ----
    mode = entry.get("scan_mode", "prose")
    hits_in = scan(case_text, mode)
    hits_out = scan(output_text, mode)
    for h in hits_out:
        if h["tier"] == "FIX":
            warn({"kind": "scan_fix", "rule": h["rule"], "line": h["line"],
                  "snippet": h["snippet"], "why": "FIX 级残留"})
    return {
        "id": entry["id"],
        "verdict": verdict,
        "details": details,
        "metrics": {
            "retention": None if ratio is None else round(ratio, 4),
            "fix_in": sum(1 for h in hits_in if h["tier"] == "FIX"),
            "fix_out": sum(1 for h in hits_out if h["tier"] == "FIX"),
            "review_in": sum(1 for h in hits_in if h["tier"] == "REVIEW"),
            "review_out": sum(1 for h in hits_out if h["tier"] == "REVIEW"),
            "chars_out": len(output_text),
        },
    }


def score_run(run_dir, evals_dir):
    """对一个 run 目录全量判分。输出文件名：<case-id>.txt；--repeat 产物为 <case-id>.rN.txt（逐份判分）。"""
    run_dir, evals_dir = Path(run_dir), Path(evals_dir)
    entries = load_benchmark(evals_dir)
    results = []
    for entry in entries:
        case_path = evals_dir / entry["case"]
        case_text = case_path.read_text(encoding="utf-8-sig")
        out_paths = sorted(run_dir.glob(f"{entry['id']}.r*.txt"))
        if not out_paths:
            single = run_dir / f"{entry['id']}.txt"
            out_paths = [single] if single.exists() else []
        if not out_paths:
            # 缺输出按缺失记录，不崩：--cases 子集 run 与跑一半的 run 都必须能判分
            results.append({
                "id": entry["id"], "verdict": "FAIL",
                "details": [{"kind": "missing_output",
                             "why": f"run 目录缺 {entry['id']}.txt"}],
                "metrics": {}})
            continue
        for out_path in out_paths:
            output_text = out_path.read_text(encoding="utf-8-sig")
            result = evaluate_case(entry, case_text, output_text)
            # ID 一律用用例 ID：rN 是同一例的重复跑，换成文件名会让 cases/snf_total
            # 与 evals 的 17 例 / 8 例口径对不上
            result["id"] = entry["id"]
            result["source"] = out_path.name
            results.append(result)
    return results


def summarize(results):
    """按用例 ID 汇总：rN 是同一例的重复跑，必须先并成一例再统计。

    不并会把 repeat=2 的 run 算成 34 例、snf_total 16、清除率出现负值
    （同一例的 fix_in 被计两次而 fix_out 只计一次），17 例 / 8 例的口径
    也随 repeat 漂移。并轨规则：verdict 取最坏，清除计数取第一份，
    留存与重合度取区间。
    """
    by_id = {}
    for r in results:
        by_id.setdefault(r["id"], []).append(r)
    merged = []
    for case_id, group in by_id.items():
        worst = min((r["verdict"] for r in group),
                    key=lambda v: {"FAIL": 0, "WARN": 1, "PASS": 2}[v])
        first = next((r for r in group if r["metrics"]), group[0])
        details = [d for r in group for d in r["details"]]
        merged.append({"id": case_id, "verdict": worst,
                       "details": details, "metrics": first["metrics"],
                       "reps": len(group)})
    sf = [r for r in merged if r["id"].startswith("SF-")]
    snf = [r for r in merged if r["id"].startswith("SNF-")]
    l1 = [r for r in merged if r["verdict"] == "FAIL"]
    l2 = [r for r in merged if r["verdict"] == "WARN"]
    fix_cleared, fix_total = 0, 0
    review_cleared, review_total = 0, 0
    for r in sf:
        m = r["metrics"]
        if not m:
            continue
        fix_total += m.get("fix_in", 0)
        fix_cleared += m.get("fix_in", 0) - m.get("fix_out", 0)
        review_total += m.get("review_in", 0)
        review_cleared += m.get("review_in", 0) - m.get("review_out", 0)
    rets = [r["metrics"].get("retention") for r in merged
            if r["metrics"].get("retention") is not None]
    # 误伤只计"跑了且被改坏"：缺输出是 harness 缺失，不是清理误伤（glm run 曾被误计 2/8）
    missing = [r["id"] for r in merged
               if any(d.get("kind") == "missing_output" for d in r["details"])]
    snf_hurt = sum(1 for r in snf if r["verdict"] == "FAIL" and r["id"] not in missing)
    return {
        "cases": len(merged),
        "l1_failures": len(l1),
        "l1_ids": [r["id"] for r in l1],
        "l2_warnings": len(l2),
        "l2_ids": [r["id"] for r in l2],
        "missing_outputs": missing,
        "snf_hurt_count": snf_hurt,
        "snf_total": len(snf),
        "sf_fix_clear_rate": (fix_cleared / fix_total) if fix_total else None,
        "sf_review_clear_rate": (review_cleared / review_total) if review_total else None,
        "retention_min": min(rets) if rets else None,
        "retention_max": max(rets) if rets else None,
    }


def render_report(run_dir, results, summary):
    lines = [f"# 判分报告：{run_dir.name}", "",
             f"生成时间：{time.strftime('%Y-%m-%dT%H:%M:%S%z')}", "",
             "## 汇总", "",
             f"- L1 硬失败：{summary['l1_failures']}"
             f"{'' if not summary['l1_ids'] else '（' + ', '.join(summary['l1_ids']) + '）'}",
             f"- L2 风格警告：{summary['l2_warnings']}"
             f"{'' if not summary['l2_ids'] else '（' + ', '.join(summary['l2_ids']) + '）'}",
             f"- SNF 误伤（按例计，小样本口径）：{summary['snf_hurt_count']}/{summary['snf_total']}",
             f"- SF FIX 清除率：{summary['sf_fix_clear_rate']}",
             f"- SF REVIEW 清除率：{summary['sf_review_clear_rate']}",
             f"- 留存率范围：{summary['retention_min']} ~ {summary['retention_max']}",
             "", "## 逐例", "",
             "| ID | verdict | 留存率 | FIX(in→out) | REVIEW(in→out) | 说明 |",
             "|---|---|---|---|---|---|"]
    for r in results:
        m = r["metrics"]
        why = "; ".join(d.get("why", d.get("kind", "")) for d in r["details"])
        lines.append(
            f"| {r['id']} | {r['verdict']} | {m.get('retention', '-')} | "
            f"{m.get('fix_in', '-')}→{m.get('fix_out', '-')} | "
            f"{m.get('review_in', '-')}→{m.get('review_out', '-')} | {why[:80]} |")
    lines += ["", "## 明细", ""]
    for r in results:
        for d in r["details"]:
            lines.append(f"- {r['id']} {d.get('kind')}: {json.dumps(d, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description="评测环静态判分")
    parser.add_argument("run_dir", nargs="?", help="evals/runs/<run-dir>")
    parser.add_argument("--evals", type=Path, default=EVALS_DIR,
                        help="评测数据目录（默认脚本所在目录）")
    parser.add_argument("--freeze", action="store_true",
                        help="冻结/更新样例 SHA256 与预期快照")
    parser.add_argument("--reason", help="本次冻结相对旧快照的变更理由（判据有变必填）")
    parser.add_argument("--report", type=Path, help="报告输出路径（默认不写文件）")
    args = parser.parse_args(argv[1:])

    if args.freeze:
        count = freeze(args.evals, reason=args.reason)
        print(f"已冻结 {count} 份样例到 manifest.json")
        if not args.run_dir:
            return 0

    failures = check_frozen(args.evals)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    if not args.run_dir:
        print("冻结校验通过（未指定 run 目录，仅校验）")
        return 0

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"run 目录不存在：{run_dir}", file=sys.stderr)
        return 1
    results = score_run(run_dir, args.evals)
    summary = summarize(results)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for r in results:
        if r["verdict"] != "PASS":
            for d in r["details"]:
                print(f"  {r['id']} [{r['verdict']}] {d.get('kind')}: "
                      f"{json.dumps(d, ensure_ascii=False)}")
    if args.report:
        args.report.write_bytes(
            render_report(run_dir, results, summary).encode("utf-8"))
        print(f"报告已写入 {args.report}")
    return 1 if summary["l1_failures"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
