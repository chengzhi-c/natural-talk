# -*- coding: utf-8 -*-
"""natural-talk LLM 级效果评测。

回答"加载本 skill 后，模型输出是否真的更自然"：
对同一批用户提问分别调用 LLM 两次——一次带 natural-talk system prompt
（templates/system-prompt-standard.txt），一次带中性 system prompt——
再用 scripts/check.py 的规则表给两边输出计数违规，汇总对比。

用法：
    python scripts/eval-llm.py                 # 需要 API 配置（见下）
    python scripts/eval-llm.py --list          # 只列出评测提示词（CI 用，不发请求）
    python scripts/eval-llm.py --no-save       # 只打印汇总，不写 benchmarks/

本脚本是仓库里唯一会出网的代码；skill 注入路径不上网、不采集用户对话。
默认把违规计数和模型回复前 500 字写入 benchmarks/（该目录已 gitignore），供本地人工判读。

环境变量（OpenAI 兼容接口，可指向任何兼容服务，如 DeepSeek/Moonshot/Ollama）：
    OPENAI_API_KEY   必填
    OPENAI_BASE_URL  可选，默认 https://api.openai.com/v1
    OPENAI_MODEL     可选，默认 gpt-4o-mini
    EVAL_TIMEOUT     可选，单次请求超时秒数，默认 60
    EVAL_MODELS      可选，逗号分隔的多模型批量（如 "gpt-4o,deepseek-chat"）

结果口径：violations 越少越接近规则要求；关注 with-skill 相对 baseline 的
零违规率提升与违规总数下降，而不是单条输出的绝对分数。违规计数只测客观
信号（禁用词、密度、格式），"像不像人"仍需人工读输出下最终判断。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from check import run_checks  # noqa: E402

STANDARD_PROMPT = (ROOT / "templates" / "system-prompt-standard.txt").read_text(encoding="utf-8")
NEUTRAL_PROMPT = "You are a helpful assistant."

PROMPTS = [
    {"id": "tool-choice", "prompt": "我该学 Vue 还是 React？"},
    {"id": "vague-analysis", "prompt": "帮我分析一下这个问题的本质"},
    {"id": "knowledge-gap", "prompt": "2024 年 Rust 在工业界的采用率是多少？"},
    {"id": "complaint", "prompt": "我的 Docker 容器启动失败，折腾一天了，帮帮我"},
    {"id": "emotion", "prompt": "我父亲去世了，我很难受"},
]

# Tier 映射用于分级统计
TIER_ORDER = ["Tier1", "Tier2", "Tier3", "Tier4", "Tier5", "Tier6", "路标词", "破折号", "感叹号"]

def chat(system, user, timeout):
    body = json.dumps({
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }).encode("utf-8")
    url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

def summarize_by_tier(violations):
    counts = {}
    for name, _ in violations:
        key = name.split()[0] if name else "other"
        counts[key] = counts.get(key, 0) + 1
        # also aggregate road sign
        if "路标" in name:
            counts["路标词"] = counts.get("路标词", 0) + 0  # already handled
    # severity grouping
    critical = sum(1 for n,_ in violations if "编造" in n or "评判" in n)
    high = sum(1 for n,_ in violations if "Tier1" in n or "Tier4" in n)
    medium = sum(1 for n,_ in violations if "Tier2" in n or "Tier3" in n or "Tier5" in n)
    low = sum(1 for n,_ in violations if "Tier6" in n or "破折号" in n or "感叹号" in n or "路标" in n)
    parts = []
    if critical: parts.append(f"[critical] {critical}")
    if high: parts.append(f"[high] {high}")
    if medium: parts.append(f"[medium] {medium}")
    if low: parts.append(f"[low] {low}")
    detail = ", ".join(f"{k}×{v}" for k,v in sorted(counts.items())) or "无"
    tier_line = " ".join(parts) if parts else "无"
    return tier_line, detail

def save_report(model_name, results):
    out_dir = ROOT / "benchmarks"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"eval-{model_name}-{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "model": model_name,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    print(f"[存档] {path.relative_to(ROOT)}")

def run_for_model(model_name, timeout, no_save=False):
    os.environ["OPENAI_MODEL"] = model_name
    print(f"\n=== 模型 {model_name} ===")
    results = []
    for p in PROMPTS:
        row = {"id": p["id"], "prompt": p["prompt"]}
        for tag, system in (("with_skill", STANDARD_PROMPT), ("baseline", NEUTRAL_PROMPT)):
            try:
                answer = chat(system, p["prompt"], timeout)
            except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
                print(f"[{p['id']}] {tag} 调用失败：{e}")
                row[tag] = None
                row[tag+"_answer"] = ""
                continue
            violations, _ = run_checks(p["prompt"], answer)
            tier_line, detail = summarize_by_tier(violations)
            print(f"[{p['id']}] {tag} 违规 {len(violations)} 条 {tier_line} ｜ {detail}")
            row[tag] = [{"tier": n, "msg": m} for n,m in violations]
            row[tag+"_answer"] = answer[:500]
            time.sleep(0.3)
        results.append(row)
    def zero_rate(tag):
        scored = [r[tag] for r in results if r[tag] is not None]
        if not scored:
            return (0, 0, 0)
        return (sum(1 for v in scored if not v), len(scored), sum(len(v) for v in scored))
    w_zero, w_n, w_total = zero_rate("with_skill")
    b_zero, b_n, b_total = zero_rate("baseline")
    print()
    print(f"汇总 {model_name}：")
    print(f"  with_skill 零违规率：{w_zero}/{w_n}，违规总数 {w_total}")
    print(f"  baseline   零违规率：{b_zero}/{b_n}，违规总数 {b_total}")
    if w_n and b_n:
        print(f"  降幅：{(b_total-w_total)/max(1,b_total)*100:.1f}%")
    print("注：违规计数只测客观信号；'像不像人'仍需人工读输出下判断。")
    if not no_save:
        save_report(model_name, results)
    return results

def main():
    if "--list" in sys.argv:
        for p in PROMPTS:
            print(f"[{p['id']}] {p['prompt']}")
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        print("未配置 OPENAI_API_KEY，无法发起评测请求。")
        print("配置方法见本脚本 docstring；可先跑 `python scripts/eval-llm.py --list` 查看评测提示词。")
        # 列出提示词供离线校验
        for p in PROMPTS:
            print(f"[{p['id']}] {p['prompt']}")
        return 2
    timeout = int(os.environ.get("EVAL_TIMEOUT", "60"))
    models_str = os.environ.get("EVAL_MODELS", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    models = [m.strip() for m in models_str.split(",") if m.strip()]
    no_save = "--no-save" in sys.argv
    for m in models:
        run_for_model(m, timeout, no_save=no_save)
    return 0

if __name__ == "__main__":
    sys.exit(main())
