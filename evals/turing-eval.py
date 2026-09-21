"""图灵式盲评：度量 skill 是否拉近人机文本的判别差距。

静态断言只能证明"词表命中消失"，本脚本补"读起来像人"的那半度量：
判别模型逐篇回答"这段文字是 AI 生成的还是人类写的"，统计各语料组的
AI-判定率：

  人类组 --human-dir           理想 AI-判定率 ≈ 0（判别器不冤枉人类）
  实验组 --ai-dir              skill 输出（如 evals/runs/<run>/）
  基线组 --ai-baseline-dir     可选：无 skill 的 AI 输出，作前后对照

解读纪律：
  - 人类组 AI-判定率 > 40% → 判别器不构成区分力，本轮结论作废
    （把人类都判成 AI 时，实验组下降无意义）
  - 同题配对语料最强；无配对时判别依据是文风本身，说服力降级但方向仍有效

密钥纪律同 run-eval.py：凭据从 --credentials（URL+密钥同行）或
NT_BASE/NT_KEY 运行时读取；输出只记模型 ID、文件名与判定，不落密钥。

用法：
  python evals/turing-eval.py --judge-model <id> --human-dir <dir> \
      --ai-dir <dir> [--ai-baseline-dir <dir>] [--limit 20] [--workers 4]
输出：evals/turing-runs/<日期>-<judge-model>/report.json + 控制台摘要
自测：python scripts/test-turing-eval.py（纯函数：判定解析、聚合与结论）
"""
import argparse
import importlib.util
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

EVALS_DIR = Path(__file__).resolve().parent
JUDGE_INSTRUCTION = ("阅读下面这段文字，判断它是 AI 生成的还是人类写的。"
                     "只回答两个字：AI 或 人类。\n\n")
INVALID_JUDGE_THRESHOLD = 0.4


def _load_run_eval():
    spec = importlib.util.spec_from_file_location(
        "run_eval", EVALS_DIR / "run-eval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_judge_messages(text):
    return [{"role": "user", "content": JUDGE_INSTRUCTION + text}]


def parse_answer(raw):
    """判别回答 → ai / human / invalid。含混与否定式表述不硬猜。"""
    head = (raw or "").strip().splitlines()[0] if (raw or "").strip() else ""
    has_ai = "AI" in head or "ai" in head.split() or "Ai" in head
    has_human = any(w in head for w in ("人类", "人写", "是人"))
    if has_ai and has_human:
        return "invalid"
    if has_ai:
        return "ai"
    if has_human:
        return "human"
    if "机器" in head or "模型" in head or "生成" in head:
        return "ai"
    return "invalid"


def summarize(groups):
    """groups: {组名: [verdict, ...]} → 各组判定统计。"""
    out = {}
    for name, verdicts in groups.items():
        n = len(verdicts)
        ai = sum(1 for v in verdicts if v == "ai")
        invalid = sum(1 for v in verdicts if v == "invalid")
        out[name] = {"n": n, "judged_ai": ai, "invalid": invalid,
                     "ai_rate": round(ai / n, 4) if n else None}
    return out


def conclusion(summary):
    """纯函数：依人类组判定率与组间差给出结论状态与一句话。"""
    human = summary.get("human") or {}
    if (human.get("ai_rate") or 0) > INVALID_JUDGE_THRESHOLD:
        return ("invalid-judge",
                f"人类组 AI-判定率 {human.get('ai_rate')} 超过 "
                f"{INVALID_JUDGE_THRESHOLD:.0%}，判别器不构成区分力，本轮结论作废")
    exp = summary.get("experiment") or {}
    base = summary.get("baseline") or {}
    if exp and base and None not in (exp.get("ai_rate"), base.get("ai_rate")):
        delta = base["ai_rate"] - exp["ai_rate"]
        if delta > 0.05:
            return ("improved",
                    f"实验组 AI-判定率 {exp['ai_rate']} 低于基线 {base['ai_rate']}"
                    f"（回落 {delta:.1%}），skill 拉近了判别差距")
        if delta < -0.05:
            return ("regressed",
                    f"实验组 AI-判定率 {exp['ai_rate']} 高于基线 {base['ai_rate']}"
                    f"（反升 {delta:.1%}），本轮 skill 未拉近判别差距")
        return ("flat",
                f"实验组 {exp['ai_rate']} 与基线 {base['ai_rate']} 相当，未见显著移动")
    return ("ok", "已记录各组判定率（未提供基线组，无组间对照）")


def _collect(directory, limit):
    paths = sorted(p for p in Path(directory).glob("*.txt") if p.is_file())
    return paths[:limit] if limit else paths


def main(argv):
    parser = argparse.ArgumentParser(
        description="图灵式盲评：各组文本的 AI-判定率对照")
    parser.add_argument("--judge-model", required=True)
    parser.add_argument("--human-dir", required=True)
    parser.add_argument("--ai-dir", required=True)
    parser.add_argument("--ai-baseline-dir")
    parser.add_argument("--limit", type=int, default=0,
                        help="每组取样上限（0=全量）")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--credentials", type=Path)
    parser.add_argument("--endpoint-index", type=int, default=1)
    args = parser.parse_args(argv[1:])

    import os
    args.nt_base = os.environ.get("NT_BASE")
    args.nt_key = os.environ.get("NT_KEY")

    run_eval = _load_run_eval()
    base, key = run_eval.resolve_credentials(args)

    groups = [("human", args.human_dir), ("experiment", args.ai_dir)]
    if args.ai_baseline_dir:
        groups.append(("baseline", args.ai_baseline_dir))

    jobs = [(name, path) for name, directory in groups
            for path in _collect(directory, args.limit)]
    if not jobs:
        print("各组目录均无 .txt 样本", file=sys.stderr)
        return 2

    records = []

    def run_job(name, path):
        text = path.read_text(encoding="utf-8-sig")
        content, _ = run_eval.call_chat(
            base, key, args.judge_model, build_judge_messages(text),
            temperature=0.0, timeout=args.timeout)
        return {"group": name, "file": path.name,
                "verdict": parse_answer(content), "head": content.strip()[:40]}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_job, n, p): (n, p) for n, p in jobs}
        for done, future in enumerate(as_completed(futures), 1):
            record = future.result()
            records.append(record)
            print(f"[{done:02d}/{len(jobs)}] {record['group']}/{record['file']}"
                  f" → {record['verdict']}")

    grouped = {name: [r["verdict"] for r in records
                     if r["group"] == name] for name, _ in groups}
    summary = summarize(grouped)
    status, message = conclusion(summary)

    report = {"judge_model": args.judge_model,
              "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "limit": args.limit, "status": status, "summary": summary,
              "message": message, "records": records}
    out_dir = EVALS_DIR / "turing-runs" / (
        time.strftime("%Y%m%d") + "-" + args.judge_model)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_bytes(
        (json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        .encode("utf-8"))

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"结论[{status}]：{message}")
    print(f"报告：{out_dir / 'report.json'}")
    return 0 if status != "invalid-judge" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
