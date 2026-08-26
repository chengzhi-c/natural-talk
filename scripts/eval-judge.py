# -*- coding: utf-8 -*-
"""盲评：多裁判多数票判断 with_skill 与 baseline 哪个更像真人。"""
import glob
import json
import os
import sys
import time
import urllib.error
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _llm import chat as _chat  # noqa: E402


def chat(model, system, user, timeout):
    return _chat(system, user, timeout=timeout, model=model)


ROOT = Path(__file__).resolve().parent.parent

JUDGE_PROMPT = (
    "下面两段文字是同一个用户提问分别得到的两个回答。请判断哪个更像真人在自然聊天。\n"
    "评分标准（按重要性排序）：\n"
    "- 直接：不铺垫、不预告动作、不绕弯子\n"
    "- 不客套：没有\"您好 / 我很乐意帮您 / 随时愿意倾听\"这类客服腔\n"
    "- 不说教：不对用户下\"你的感受是正常的 / 请允许自己\"这类评判\n"
    "- 简洁：不堆编号、不堆加粗、不长篇大论\n"
    "- 但语气不生硬，保留正常的人味\n"
    "注意：客服腔、说教、讲义腔即使听起来更\"礼貌\"，也应当扣分。\n"
    "只回答一个字母 A 或 B，不要解释。"
)

def collect_pairs():
    pairs = []
    for f in sorted(glob.glob(str(ROOT / "benchmarks" / "eval-*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        model = d.get("model", "?")
        for r in d.get("results", []):
            a = (r.get("with_skill_answer") or "").strip()
            b = (r.get("baseline_answer") or "").strip()
            if a and b:
                pairs.append((model, r["prompt"], a, b))
    return pairs

def judge_pair(model, prompt, a, b, swapped, timeout):
    """a=with_skill, b=baseline。返回 True=with_skill 胜, False=baseline 胜, None=无法解析。"""
    first, second = (b, a) if swapped else (a, b)
    user = f"问题：{prompt}\n\n回答A：\n{first[:800]}\n\n回答B：\n{second[:800]}"
    try:
        reply = chat(model, "你是文字风格裁判，只按要求输出一个字母。", user, timeout)
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
        print(f"    [{model}] 调用失败：{e}")
        return None
    reply = reply.strip().upper()
    pick = None
    for ch in reply:
        if ch in ("A", "B"):
            pick = ch
            break
    if pick is None:
        return None
    return (pick == "A") == (not swapped)

def main():
    if "--list" in sys.argv:
        pairs = collect_pairs()
        for model, prompt, _, _ in pairs:
            print(f"[{model}] {prompt}")
        print(f"共 {len(pairs)} 对")
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        print("未配置 OPENAI_API_KEY")
        return 2
    judge_models = [m.strip() for m in os.environ.get("JUDGE_MODELS", "qwen3.7-max,glm-5.2,minimax-m2.5").split(",") if m.strip()]
    timeout = int(os.environ.get("EVAL_TIMEOUT", "60"))
    pairs = collect_pairs()

    rows = []
    with_wins = base_wins = ties = 0
    for i, (gen_model, prompt, a, b) in enumerate(pairs):
        swapped = bool(i % 2)  # 同一对在所有裁判间用同一方向，分歧只反映判断差异
        votes = {}
        for jm in judge_models:
            r = judge_pair(jm, prompt, a, b, swapped, timeout)
            votes[jm] = r
            time.sleep(0.2)
        decided = {jm: r for jm, r in votes.items() if r is not None}
        w = sum(1 for r in decided.values() if r)
        b_count = sum(1 for r in decided.values() if not r)
        if not decided:
            winner = "invalid"
            ties += 1
        elif w > b_count:
            winner = "with_skill"
            with_wins += 1
        elif b_count > w:
            winner = "baseline"
            base_wins += 1
        else:
            winner = "tie"
            ties += 1
        detail = ", ".join(f"{jm}:{'W' if r else 'L'}" for jm, r in decided.items())
        rows.append({"gen_model": gen_model, "prompt": prompt, "winner": winner, "votes": {jm: r for jm, r in votes.items()}})
        print(f"[{gen_model}] {prompt} -> {winner}  ({w}W/{b_count}L)  |  {detail}")

    total = len(pairs)
    decided_total = with_wins + base_wins
    print()
    print(f"裁判：{', '.join(judge_models)}，共 {total} 对")
    print(f"多数票结果：with_skill {with_wins} / baseline {base_wins} / 平或无效 {ties}")
    if decided_total:
        print(f"with_skill 多数票偏好率：{with_wins/decided_total*100:.1f}%")
    # 裁判间分歧率：存在一对里裁判既有 W 又有 L 的比例
    split = sum(1 for r in rows if r["winner"] == "tie" or (any(r["votes"].get(j) is True for j in judge_models) and any(r["votes"].get(j) is False for j in judge_models)))
    print(f"裁判间分歧对数：{split}/{total}（越高越说明\"直接 vs 礼貌\"是口味问题，不是客观优劣）")

    if "--no-save" not in sys.argv:
        out = ROOT / "benchmarks" / f"judge-v2-{datetime.now():%Y%m%d_%H%M%S}.json"
        out.write_text(json.dumps({
            "judge_models": judge_models,
            "date": datetime.now().isoformat(),
            "with_wins": with_wins, "base_wins": base_wins, "ties": ties,
            "rows": rows,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[存档] {out.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
