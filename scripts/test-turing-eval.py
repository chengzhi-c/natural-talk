"""turing-eval.py 纯函数自测：判定解析、聚合与结论判读。

网络调用（判别模型 API）不在自测范围；红灯验证方式：临时改坏
parse_answer 的否定式分支或 conclusion 的失灵阈值 → 本测试必须转红。

运行：python scripts/test-turing-eval.py
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

EVALS = Path(__file__).resolve().parent.parent / "evals"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


turing = _load("turing_eval", EVALS / "turing-eval.py")

failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


# ---------- 判定解析 ----------
check("解析-AI", turing.parse_answer("AI") == "ai")
check("解析-AI带标点", turing.parse_answer("AI。") == "ai")
check("解析-人类", turing.parse_answer("人类") == "human")
check("解析-是人类写的", turing.parse_answer("这段是人类写的。") == "human")
check("解析-机器生成", turing.parse_answer("机器生成") == "ai")
check("解析-否定式含混作废", turing.parse_answer("不是AI，是人类写的") == "invalid",
      "否定式表述须作废，不得硬猜")
check("解析-空回答", turing.parse_answer("") == "invalid")
check("解析-跑题回答", turing.parse_answer("我认为这段写得不错") == "invalid")

# ---------- 聚合 ----------
s = turing.summarize({"a": ["ai", "human", "ai", "invalid"], "b": []})
check("聚合-计数", s["a"]["n"] == 4 and s["a"]["judged_ai"] == 2
      and s["a"]["invalid"] == 1, str(s))
check("聚合-比率", abs(s["a"]["ai_rate"] - 0.5) < 1e-9, str(s))
check("聚合-空组", s["b"]["ai_rate"] is None, str(s))

# ---------- 结论判读 ----------
c1 = turing.conclusion({"human": {"ai_rate": 0.5}})
check("结论-判别器失灵作废", c1[0] == "invalid-judge", str(c1))
c2 = turing.conclusion({"human": {"ai_rate": 0.1},
                        "experiment": {"ai_rate": 0.3},
                        "baseline": {"ai_rate": 0.8}})
check("结论-回落即改善", c2[0] == "improved", str(c2))
c3 = turing.conclusion({"human": {"ai_rate": 0.1},
                        "experiment": {"ai_rate": 0.85},
                        "baseline": {"ai_rate": 0.7}})
check("结论-反升即恶化", c3[0] == "regressed", str(c3))
c4 = turing.conclusion({"human": {"ai_rate": 0.1},
                        "experiment": {"ai_rate": 0.8},
                        "baseline": {"ai_rate": 0.82}})
check("结论-五点内持平", c4[0] == "flat", str(c4))
c5 = turing.conclusion({"human": {"ai_rate": 0.1},
                        "experiment": {"ai_rate": 0.3}})
check("结论-无基线只记录", c5[0] == "ok", str(c5))

# ---------- 判别消息构造 ----------
m = turing.build_judge_messages("测试文本")
check("消息-单条user", len(m) == 1 and m[0]["role"] == "user", str(m))
check("消息-指令与正文同在",
      "只回答两个字" in m[0]["content"] and m[0]["content"].endswith("测试文本"),
      m[0]["content"])

if failures:
    print("turing-eval 测试未通过：")
    print("\n".join(failures))
    sys.exit(1)
print("turing-eval 测试通过：判定解析、聚合统计、结论判读、消息构造全部符合预期")
