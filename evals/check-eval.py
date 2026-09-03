"""natural-talk-strict 评测环静态判分：机械断言 + 留存率 + 清除率统计。

三层判分（判据先于跑分定稿，见 evals/README.md）：
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


def check_frozen(evals_dir):
    """核对每份样例与 manifest 的 SHA256；返回失败清单。"""
    manifest_path = evals_dir / "manifest.json"
    if not manifest_path.exists():
        return ["manifest.json 不存在：先运行 --freeze 冻结基线"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for entry in load_benchmark(evals_dir):
        case_id = entry["id"]
        recorded = manifest.get("cases", {}).get(case_id)
        if recorded is None:
            failures.append(f"{case_id}: manifest 未收录（新增样例须显式冻结并记理由）")
            continue
        actual = case_sha256(evals_dir / entry["case"])
        if actual != recorded["sha256"]:
            failures.append(f"{case_id}: 样例内容与冻结指纹不符（防放水条款："
                            f"跑分后不得改样例；确需变更先在 manifest.changes 记理由）")
    return failures


def freeze(evals_dir):
    manifest_path = evals_dir / "manifest.json"
    manifest = {"frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "cases": {}, "changes": []}
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["changes"] = old.get("changes", [])
    for entry in load_benchmark(evals_dir):
        manifest["cases"][entry["id"]] = {
            "case": entry["case"],
            "sha256": case_sha256(evals_dir / entry["case"]),
            "assertions": entry.get("assertions", []),
            "retention_min": entry.get("retention_min"),
        }
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
        if floor is not None and ratio < floor:
            fail({"kind": "retention", "ratio": round(ratio, 4),
                  "floor": floor, "why": "清理稿缩水超样例下限"})

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
    """对一个 run 目录全量判分。输出文件名：<case-id>.txt 或 <case-id>.rN.txt。"""
    entries = load_benchmark(evals_dir)
    results = []
    for entry in entries:
        case_path = evals_dir / entry["case"]
        case_text = case_path.read_text(encoding="utf-8-sig")
        out_path = run_dir / f"{entry['id']}.txt"
        if not out_path.exists():
            results.append({
                "id": entry["id"], "verdict": "FAIL",
                "details": [{"kind": "missing_output",
                             "why": f"run 目录缺 {out_path.name}"}],
                "metrics": {}})
            continue
        output_text = out_path.read_text(encoding="utf-8-sig")
        results.append(evaluate_case(entry, case_text, output_text))
    return results


def summarize(results):
    sf = [r for r in results if r["id"].startswith("SF-")]
    snf = [r for r in results if r["id"].startswith("SNF-")]
    l1 = [r for r in results if r["verdict"] == "FAIL"]
    l2 = [r for r in results if r["verdict"] == "WARN"]
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
    rets = [r["metrics"].get("retention") for r in results
            if r["metrics"].get("retention") is not None]
    return {
        "cases": len(results),
        "l1_failures": len(l1),
        "l1_ids": [r["id"] for r in l1],
        "l2_warnings": len(l2),
        "l2_ids": [r["id"] for r in l2],
        "snf_hurt_count": sum(1 for r in snf if r["verdict"] == "FAIL"),
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
    parser.add_argument("--report", type=Path, help="报告输出路径（默认不写文件）")
    args = parser.parse_args(argv[1:])

    if args.freeze:
        count = freeze(args.evals)
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
