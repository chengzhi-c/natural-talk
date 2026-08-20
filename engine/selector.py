# 注：文章版 linter 默认不启用本模块，保留仅为与 release 复用/离线改写可选
# -*- coding: utf-8 -*-
"""动态选档器 — 根据上下文预算/用户投诉/场景选择 L0-L3.

零LLM，纯规则，<1ms。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def pick_level(ctx_budget=None, user_msg="", task_type="chat"):
    # 1. 上下文紧张
    if ctx_budget is not None and ctx_budget < 800:
        return "L0"
    # 2. 正式场景直接豁免
    if re.search(r"论文|公文|演讲稿|营销文案|学术润色", user_msg):
        return "L0"
    # 3. 用户显式投诉
    if re.search(r"太官方|太AI|像机器人|去AI味|自然一点|像人说话", user_msg):
        return "L2"
    # 4. 短问短答
    if len(user_msg) < 20:
        return "L1"
    # 5. 默认
    return "L1"

def load_prompt(level="L1"):
    mapping = {"L0": "prompt.l0.txt", "L1": "prompt.l1.txt", "L2": "prompt.l2.txt", "L3": "prompt.l3.txt"}
    fname = mapping.get(level, "prompt.l1.txt")
    p = ROOT / "dist" / "prompts" / fname
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""

if __name__ == "__main__":
    for lvl in ["L0","L1","L2","L3"]:
        print(lvl, len(load_prompt(lvl)), "chars")
