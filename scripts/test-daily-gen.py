#!/usr/bin/env python3
"""日常对话生成期离线契约回归（零 API，毫秒级）。

覆盖 D 层机械词表与生成期 B 层句首套话的两侧行为：
  应报：B10 起手式 / B4 提示语冒号 / C5 宏观开场 / D2 服务腔开场·总结·收尾 /
        D3 免责包装 / D4 万能收尾 / D5 元话语空预告 / D6 模糊归因
  不应报：自然问答、"随时问我"、单个"可能"、名词性"好问题的定义"、
        "希望这周能上线"、句中"供你参考"、直给回答、正常时间陈述

判定口径与 verify_repo.py 第 6 层一致：漏检（应报不报）或误报（不应报而报）即失败。
新增 D 层词表时，在此补"报 / 不报各一条"再跑全量体检。
"""
import importlib.util
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_spec = importlib.util.spec_from_file_location(
    "scan_mechanical", Path(__file__).resolve().parent / "scan-mechanical.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# ---------- 应报：文本 → 期望命中的规则号 ----------
MUST_FLAG = [
    ("B10 起手式", "说白了，这就是连接池打满了。", "B10"),
    ("B4 提示语冒号", "一句话总结：连接池打满了。", "B4"),
    ("C5 宏观开场（按 B12 处理）", "在当今这个时代，系统的稳定性越来越受到重视。", "C5"),
    ("D2 服务腔开场", "好问题！P99 延迟涨到 400ms，先查连接池。", "D2"),
    ("D2 句首总结套话", "综上所述，缓存不是万能的。", "D2"),
    ("D2 客服收尾", "先看监控确认。希望对你有帮助。", "D2"),
    ("D3 免责包装", "作为一个语言模型，我没有实时数据。", "D3"),
    ("D4 万能收尾", "关键在于找到平衡。", "D4"),
    ("D4 整句万能收尾", "因人而异。", "D4"),
    ("D5 元话语空预告", "下面我将会展开分析。", "D5"),
    ("D5 元话语空预告-让我们", "让我们先来理解背景。", "D5"),
    ("D6 模糊归因", "有研究表明，缓存能提升性能。", "D6"),
]

# ---------- 不应报：自然表达与既有放行口径 ----------
MUST_PASS = [
    ("自然问答", "“你昨晚去哪了？”“在老王家打牌，怎么了？”"),
    ("随时问我（非客服腔）", "随时问我。"),
    ("单个可能是诚实", "可能是连接池打满了，先看监控。"),
    ("名词性好问题", "好问题的定义很清晰。"),
    ("希望这周能上线", "希望这周能上线。"),
    ("句中供你参考", "这部分供你参考。"),
    ("直给回答", "P99 从 80ms 涨到 400ms，先查连接池。"),
    ("正常时间陈述", "三年后，他从北方调回省城。"),
]

failures = []

for name, text, rule in MUST_FLAG:
    rules = [h["rule"] for h in _mod.scan(text, mode="gen")]
    if rule not in rules:
        failures.append(f"漏检[{name}] 期望 {rule}，实际 {rules or '无命中'}")

for name, text in MUST_PASS:
    hits = _mod.scan(text, mode="gen")
    if hits:
        rules = [h["rule"] for h in hits]
        failures.append(f"误报[{name}] 不应命中却报 {rules}")

if failures:
    print("日常对话生成期回归未通过：")
    print("\n".join(failures))
    sys.exit(1)

print(f"✅ 日常对话生成期回归通过：{len(MUST_FLAG)} 处病灶全捕获，"
      f"{len(MUST_PASS)} 处自然表达零误报")
