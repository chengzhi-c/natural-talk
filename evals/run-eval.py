"""natural-talk-strict 评测环 API harness：按 benchmark.jsonl 生成各席位输出。

密钥纪律：凭据从 --credentials 文件（用户自管路径）
或 NT_BASE/NT_KEY 环境变量运行时读取；任何输出文件只记模型 ID、时间、
prompt SHA256 与字数，不落密钥与 prompt 全文（模板有 SHA256 即可复现）。

Windows 纪律（write_text 会把 LF 翻译成 CRLF，导致校验和失配）：所有写出走 write_bytes，
换行统一 \\n，禁裸 write_text 写含校验和的内容。

分批与断点：每例独立落盘，一例失败重试至多 2 次（429/5xx 退避），
仍失败则记录到 metadata 并继续，不中断整轮。

用法：
  python evals/run-eval.py --model deepseek-v4-flash-0731 ^
      [--credentials <file>] [--endpoint-index 1] [--tag baseline] ^
      [--cases SF-01,SF-07] [--repeat 2] [--workers 4]
输出：evals/runs/<日期>-<模型>[-<tag>]/<case-id>[.rN].txt + metadata.json
"""
import argparse
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

EVALS_DIR = Path(__file__).resolve().parent
ROOT = EVALS_DIR.parent

URL_RE = re.compile(r"https?://[^\s，,]+")
KEY_RE = re.compile(r"\bsk(?:_|-)[A-Za-z0-9_-]+\b")

RETRYABLE = {429, 502, 503, 504}
CLEAN_INSTRUCTION = "请清理这段文字，只输出正文："
RETELL_INSTRUCTION = "用自然的话复述以下材料："

MAX_TOKENS = 8000


def parse_endpoints(text):
    endpoints = []
    for line in text.splitlines():
        url = URL_RE.search(line)
        key = KEY_RE.search(line)
        if url and key:
            endpoints.append((url.group(0).rstrip("/"), key.group(0)))
    if not endpoints:
        raise SystemExit("凭据文件未找到 端点URL+密钥 同行记录")
    return endpoints


def resolve_credentials(args):
    if args.credentials:
        pairs = parse_endpoints(
            args.credentials.read_text(encoding="utf-8-sig"))
        idx = min(args.endpoint_index, len(pairs)) - 1
        return pairs[idx]
    base, key = args.nt_base, args.nt_key
    if not base or not key:
        raise SystemExit("缺少凭据：用 --credentials 或设置 NT_BASE/NT_KEY")
    return base.rstrip("/"), key


def build_messages(entry, case_text):
    system = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if entry["prompt_type"] == "retell":
        user = RETELL_INSTRUCTION + "\n\n" + case_text
    else:
        user = CLEAN_INSTRUCTION + "\n\n" + case_text
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}], system


def call_chat(base, key, model, messages, temperature, timeout, retries=2):
    payload = json.dumps({"model": model, "messages": messages, "stream": False,
                          "temperature": temperature, "max_tokens": MAX_TOKENS},
                         ensure_ascii=False).encode("utf-8")
    request = Request(f"{base}/chat/completions", data=payload, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json"}, method="POST")
    last = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                body = json.load(response)
            content = body["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(x.get("text", "") for x in content
                                  if isinstance(x, dict))
            if not str(content).strip():
                raise ValueError("empty content")
            return str(content), body["choices"][0].get("finish_reason")
        except HTTPError as error:
            last = f"HTTP {error.code}"
            if error.code in RETRYABLE and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(last)
        except Exception as error:  # noqa: BLE001
            last = type(error).__name__
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(last)


def main(argv):
    parser = argparse.ArgumentParser(description="评测环 API harness")
    parser.add_argument("--model", required=True)
    parser.add_argument("--credentials", type=Path)
    parser.add_argument("--endpoint-index", type=int, default=1)
    parser.add_argument("--tag", default="")
    parser.add_argument("--cases", default="",
                        help="逗号分隔的样例 ID 过滤，空为全量")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output-root", type=Path, default=None,
                        help="输出根目录，默认 evals/runs；测试产物可隔离到主仓库外")
    args = parser.parse_args(argv[1:])

    import os
    args.nt_base = os.environ.get("NT_BASE")
    args.nt_key = os.environ.get("NT_KEY")
    base, key = resolve_credentials(args)

    entries = []
    for line in (EVALS_DIR / "benchmark.jsonl").read_text(
            encoding="utf-8-sig").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    if args.cases:
        wanted = {x.strip() for x in args.cases.split(",") if x.strip()}
        entries = [e for e in entries if e["id"] in wanted]
        missing = wanted - {e["id"] for e in entries}
        if missing:
            raise SystemExit(f"未知样例 ID：{sorted(missing)}")

    run_name = time.strftime("%Y%m%d") + "-" + args.model
    if args.tag:
        run_name += "-" + args.tag
    out_root = args.output_root or (EVALS_DIR / "runs")
    run_dir = out_root / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for entry in entries:
        case_text = (EVALS_DIR / entry["case"]).read_text(encoding="utf-8-sig")
        messages, system = build_messages(entry, case_text)
        prompt_sha = hashlib.sha256(
            json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()
        for rep in range(1, args.repeat + 1):
            suffix = "" if args.repeat == 1 else f".r{rep}"
            jobs.append({"entry": entry, "messages": messages,
                         "prompt_sha": prompt_sha, "system_sha":
                         hashlib.sha256(system.encode("utf-8")).hexdigest(),
                         "suffix": suffix})

    meta = {"model": args.model, "started_at":
            time.strftime("%Y-%m-%dT%H:%M:%S%z"), "repeat": args.repeat,
            "cases": [e["id"] for e in entries], "results": []}
    meta_lock_write = run_dir / "metadata.json"

    def run_job(job):
        entry = job["entry"]
        started = time.perf_counter()
        out_path = run_dir / f"{entry['id']}{job['suffix']}.txt"
        try:
            content, finish = call_chat(
                base, key, args.model, job["messages"],
                entry.get("temperature", 0.2), args.timeout)
            out_path.write_bytes(content.encode("utf-8"))
            record = {"id": entry["id"], "file": out_path.name, "status": "ok",
                      "prompt_sha256": job["prompt_sha"],
                      "system_sha256": job["system_sha"],
                      "finish_reason": finish, "chars": len(content),
                      "elapsed_ms": round((time.perf_counter() - started) * 1000)}
        except Exception as error:  # noqa: BLE001
            record = {"id": entry["id"], "file": out_path.name,
                      "status": "error", "error": str(error)[:200],
                      "prompt_sha256": job["prompt_sha"]}
        return record

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_job, job): job for job in jobs}
        for done, future in enumerate(as_completed(futures), 1):
            record = future.result()
            meta["results"].append(record)
            print(f"[{done:02d}/{len(jobs)}] {record['id']} {record['status']}")
            if record["status"] == "error":
                print(f"        {record.get('error')}")

    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    ok = sum(1 for r in meta["results"] if r["status"] == "ok")
    meta["summary"] = {"ok": ok, "error": len(meta["results"]) - ok}
    meta_lock_write.write_bytes(
        (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"完成：{ok}/{len(jobs)} 成功，输出目录 {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
