# -*- coding: utf-8 -*-
"""natural-talk LLM 级效果评测。

回答"加载本 skill 后，模型输出是否真的更自然"：
对同一批用户提问分别调用 LLM 两次，一次带 natural-talk system prompt
（templates/system-prompt-standard.txt），一次带中性 system prompt，
两边输出成对存档，交给 scripts/eval-judge.py 盲评多数票判断哪个更像真人。

用法：
    python scripts/eval-llm.py                 # 需要 API 配置（见下）
    python scripts/eval-llm.py --list          # 只列出评测提示词（CI 用，不发请求）
    python scripts/eval-llm.py --no-save       # 只打印汇总，不写 benchmarks/

本脚本是仓库里唯一会出网的代码；skill 注入路径不上网、不采集用户对话。
默认把成对回复全文写入 benchmarks/（该目录已 gitignore），供盲评与人工判读。

环境变量（OpenAI 兼容接口，可指向任何兼容服务，如 DeepSeek/Moonshot/Ollama）：
    OPENAI_API_KEY   必填
    OPENAI_BASE_URL  可选，默认 https://api.openai.com/v1
    OPENAI_MODEL     可选，默认 gpt-4o-mini
    EVAL_TIMEOUT     可选，单次请求超时秒数，默认 60
    EVAL_MODELS      可选，逗号分隔的多模型批量（如 "gpt-4o,deepseek-chat"）

结果口径：本脚本只负责取样，不打分。"像不像人"由 eval-judge.py 的多裁判
盲评多数票给出，或人工读 benchmarks/ 里的成对输出判断。正则计数测不出
语境（同一个词在不同语境有对有错），所以这里不做违规计数。
"""
import json
import os
import sys
import time
import urllib.error
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _llm import chat  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

STANDARD_PROMPT = (ROOT / "templates" / "system-prompt-standard.txt").read_text(encoding="utf-8")
NEUTRAL_PROMPT = "You are a helpful assistant."

PROMPTS = [
    {"id": "tool-choice", "prompt": "我该学 Vue 还是 React？"},
    {"id": "vague-analysis", "prompt": "帮我分析一下这个问题的本质"},
    {"id": "knowledge-gap", "prompt": "2024 年 Rust 在工业界的采用率是多少？"},
    {"id": "complaint", "prompt": "我的 Docker 容器启动失败，折腾一天了，帮帮我"},
    {"id": "emotion", "prompt": "我父亲去世了，我很难受"},
]

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
            print(f"[{p['id']}] {tag} 取样 {len(answer)} 字")
            row[tag] = "ok"
            row[tag+"_answer"] = answer
            time.sleep(0.3)
        results.append(row)
    ok = sum(1 for r in results if r.get("with_skill") and r.get("baseline"))
    print()
    print(f"汇总 {model_name}：{ok}/{len(results)} 对取样成功")
    print("本脚本不打分。跑 `python scripts/eval-judge.py` 盲评，或人工读 benchmarks/ 里的成对输出。")
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
