# -*- coding: utf-8 -*-
"""natural-talk-article LLM 级效果评测。

回答"加载本 skill 后，模型写的文章是否真的更自然"：
对同一批文章类提问各调用 LLM 两次——一次带 natural-talk-article system prompt
（templates/system-prompt-standard.txt），一次带中性 prompt——
再用 scripts/check.py 的规则表给两边输出计数违规，汇总对比。

用法：
    python scripts/eval-llm.py            # 需要 API 配置（见下）
    python scripts/eval-llm.py --list     # 只列出评测提示词（CI 用，不发请求）

环境变量（OpenAI 兼容接口，可指向任何兼容服务，如 DeepSeek/Moonshot/Ollama）：
    OPENAI_API_KEY   必填
    OPENAI_BASE_URL  可选，默认 https://api.openai.com/v1
    OPENAI_MODEL     可选，默认 gpt-4o-mini
    EVAL_TIMEOUT     可选，单次请求超时秒数，默认 60

结果口径：violations 越少越接近规则要求；关注 with-skill 相对 baseline 的
零违规率提升与违规总数下降，而不是单条输出的绝对分数。违规计数只测客观
信号（禁用词、密度、格式），"像不像人"仍需人工读输出下最终判断。

注：本脚本的 check_article() 与 scripts/check.py 保持同步；
若规则表变更，两处一起改（或改为 import，见 check.py）。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from engine.detector import article_check  # noqa: E402

STANDARD_PROMPT = (ROOT / "templates" / "system-prompt-standard.txt").read_text(encoding="utf-8")
NEUTRAL_PROMPT = "You are a helpful assistant."

# 评测提示词：刻意覆盖文章场景下容易诱发 AI 腔的提问
# （空泛标题、空泛引入、讲义腔、三点并列、强行升华、设问钩子）。
PROMPTS = [
    {"id": "tutorial", "prompt": "写一篇给新手看的 Docker 容器启动失败排查指南"},
    {"id": "opinion", "prompt": "该学 Vue 还是 React？写篇文章说说你的看法"},
    {"id": "retro", "prompt": "写一篇线上事故复盘，讲讲团队从中学到了什么"},
    {"id": "deep-dive", "prompt": "详细讲讲 MySQL 索引的原理和常见误区"},
    {"id": "worst-case", "prompt": "帮我分析一下这个问题的本质"},
]


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


def summarize(violations):
    counts = {}
    for name, _ in violations:
        counts[name] = counts.get(name, 0) + 1
    return ", ".join("{}×{}".format(n, c) for n, c in sorted(counts.items())) or "无"


def main():
    if "--list" in sys.argv:
        for p in PROMPTS:
            print("[{}] {}".format(p["id"], p["prompt"]))
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        print("未配置 OPENAI_API_KEY，无法发起评测请求。")
        print("配置方法见本脚本 docstring；可先跑 `python scripts/eval-llm.py --list` 查看评测提示词。")
        return 2

    timeout = int(os.environ.get("EVAL_TIMEOUT", "60"))
    results = []
    for p in PROMPTS:
        row = {"id": p["id"]}
        for tag, system in (("with_skill", STANDARD_PROMPT), ("baseline", NEUTRAL_PROMPT)):
            try:
                raw = chat(system, p["prompt"], timeout)
            except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
                print("[{}] {} 调用失败：{}".format(p["id"], tag, e))
                row[tag] = None
                continue
            # LLM 输出通常是整篇正文；这里用中性占位标题（模型生成的标题质量需人工评）。
            violations, _ = check_article("文章", raw)
            row[tag] = violations
            print("[{}] {} 违规 {} 条：{}".format(p["id"], tag, len(violations), summarize(violations)))
            time.sleep(0.3)  # 轻度限速，避免触发服务端节流
        results.append(row)

    def zero_rate(tag):
        scored = [r[tag] for r in results if r[tag] is not None]
        if not scored:
            return (0, 0, 0)
        return (sum(1 for v in scored if not v), len(scored), sum(len(v) for v in scored))

    w_zero, w_n, w_total = zero_rate("with_skill")
    b_zero, b_n, b_total = zero_rate("baseline")
    print()
    print("汇总：")
    print("  with_skill 零违规率：{}/{}，违规总数 {}".format(w_zero, w_n, w_total))
    print("  baseline   零违规率：{}/{}，违规总数 {}".format(b_zero, b_n, b_total))
    print("注：违规计数只测客观信号；'像不像人'仍需人工读输出下判断。")
    return 0


if __name__ == "__main__":
    sys.exit(main())