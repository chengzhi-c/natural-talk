"""共享 LLM 客户端 — 四个 eval 脚本原先各抄一份，收敛到这里。

环境变量：OPENAI_API_KEY（必需）、OPENAI_BASE_URL、OPENAI_MODEL、OPENAI_USER_AGENT
"""
import json
import os
import urllib.request

DEFAULT_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
# 部分网关在 CDN 层按 User-Agent 拦截，urllib 默认 UA 会被判 403（Cloudflare 1010）
USER_AGENT = os.environ.get("OPENAI_USER_AGENT", "natural-talk-eval/1.0")


def model_name(override=None):
    return override or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)


def _request(model, system, user, stream):
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **({"stream": True} if stream else {}),
    }).encode("utf-8")
    url = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE).rstrip("/") + "/chat/completions"
    return urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "User-Agent": USER_AGENT,
        },
    )


def chat(system, user, timeout=120, model=None):
    req = _request(model_name(model), system, user, stream=False)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def chat_stream(system, user, timeout=300, model=None, echo=False):
    """流式读取；echo=True 时边收边打印，长文生成时能看到进度。"""
    req = _request(model_name(model), system, user, stream=True)
    parts = []
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                delta = json.loads(payload)["choices"][0].get("delta", {})
            except Exception:
                continue
            piece = delta.get("content")
            if piece:
                parts.append(piece)
                if echo:
                    print(piece, end="", flush=True)
    if echo:
        print()
    return "".join(parts)
