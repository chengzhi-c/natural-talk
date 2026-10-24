"""turing-eval.py 纯函数自测：判定解析、聚合与结论判读。

网络调用（判别模型 API）不在自测范围；红灯验证方式：临时改坏
parse_answer 的否定式分支或 conclusion 的失灵阈值 → 本测试必须转红。

运行：python scripts/test-turing-eval.py
"""
import importlib.util
import sys
from pathlib import Path
import _loader

_loader.ensure_utf8()

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
# 分句判否定："不是AI，是人类写的"两个分句各给一个判定，取未被否定的那个
check("解析-否定分句取未否定侧", turing.parse_answer("不是AI，是人类写的") == "human")
# 单句否定式是对判定的否认，不是判定本身（只看首行 + 裸子串会判成 human）
check("解析-这不是人写的不硬猜", turing.parse_answer("这不是人写的") == "invalid")
check("解析-不像是模型生成不硬猜", turing.parse_answer("这段不像是模型生成的") == "invalid")
check("解析-不像AI写的不硬猜", turing.parse_answer("不像AI写的") == "invalid")
check("解析-同句两种判定作废", turing.parse_answer("AI，但有点像人类") == "invalid",
      "两种判定同时成立时不得硬猜")
check("解析-空回答", turing.parse_answer("") == "invalid")
check("解析-跑题回答", turing.parse_answer("我认为这段写得不错") == "invalid")
# 只看首行会把判别模型的正常客套全判无效，必须全文找别名
check("解析-首行废话", turing.parse_answer("这段文字读起来很流畅。\nAI") == "ai",
      "判定在第二行也要认")
check("解析-判定在句中", turing.parse_answer("我的判断是：AI。") == "ai")
# "人工智能"是名词不是判定
check("解析-人工智能不作判定", turing.parse_answer("这段在谈人工智能的发展") == "invalid")
check("解析-人工智能加判定",
      turing.parse_answer("这段谈人工智能，但读起来像人类写的") == "human")

# ---------- 聚合 ----------
s = turing.summarize({"a": ["ai", "human", "ai", "invalid"], "b": []})
check("聚合-计数", s["a"]["n"] == 4 and s["a"]["judged_ai"] == 2
      and s["a"]["invalid"] == 1, str(s))
check("聚合-比率", abs(s["a"]["ai_rate"] - 0.5) < 1e-9, str(s))
check("聚合-空组", s["b"]["ai_rate"] is None, str(s))
check("聚合-无效率", abs(s["a"]["invalid_rate"] - 0.25) < 1e-9, str(s))

# ---------- 结论判读 ----------
c1 = turing.conclusion({"human": {"n": 5, "ai_rate": 0.5, "invalid_rate": 0}})
check("结论-判别器失灵作废", c1[0] == "invalid-judge", str(c1))
c2 = turing.conclusion({"human": {"n": 5, "ai_rate": 0.1, "invalid_rate": 0},
                        "experiment": {"ai_rate": 0.3},
                        "baseline": {"ai_rate": 0.8}})
check("结论-回落即改善", c2[0] == "improved", str(c2))
c3 = turing.conclusion({"human": {"n": 5, "ai_rate": 0.1, "invalid_rate": 0},
                        "experiment": {"ai_rate": 0.85},
                        "baseline": {"ai_rate": 0.7}})
check("结论-反升即恶化", c3[0] == "regressed", str(c3))
c4 = turing.conclusion({"human": {"n": 5, "ai_rate": 0.1, "invalid_rate": 0},
                        "experiment": {"ai_rate": 0.8},
                        "baseline": {"ai_rate": 0.82}})
check("结论-五点内持平", c4[0] == "flat", str(c4))
c5 = turing.conclusion({"human": {"n": 5, "ai_rate": 0.1, "invalid_rate": 0},
                        "experiment": {"ai_rate": 0.3}})
check("结论-无基线只记录", c5[0] == "ok", str(c5))
# 无效判定率过高：判别模型答非所问，同样作废
c6 = turing.conclusion({"human": {"n": 5, "ai_rate": 0, "invalid_rate": 0.6}})
check("结论-无效率过高作废", c6[0] == "invalid-judge", str(c6))
# 人类组零样本：无从检验判别器是否冤枉人类，拒绝出结论
c7 = turing.conclusion({"human": {"n": 0, "ai_rate": None, "invalid_rate": None},
                        "experiment": {"ai_rate": 0.3}})
check("结论-人类组缺样本不出结论", c7[0] == "no-basis", str(c7))

# ---------- 判别消息构造 ----------
m = turing.build_judge_messages("测试文本")
check("消息-单条user", len(m) == 1 and m[0]["role"] == "user", str(m))
check("消息-指令与正文同在",
      "只回答两个字" in m[0]["content"] and m[0]["content"].endswith("测试文本"),
      m[0]["content"])


# ---- A10：实验组/基线组高无效判定率必须降级 ----
# 真实报告 20261024-100445：实验组 18 样本 15 invalid，
# ai_rate 仅来自 3 个判定，修改前输出 improved。
_HIGH_INVALID = {
    "human": {"n": 61, "judged_ai": 0, "invalid": 11,
              "invalid_rate": 0.1803, "ai_rate": 0.0},
    "experiment": {"n": 18, "judged_ai": 3, "invalid": 15,
                   "invalid_rate": 0.8333, "ai_rate": 0.1667},
    "baseline": {"n": 18, "judged_ai": 18, "invalid": 0,
                 "invalid_rate": 0.0, "ai_rate": 1.0},
}
_LOW_INVALID = {
    "human": {"n": 61, "judged_ai": 0, "invalid": 2,
              "invalid_rate": 0.03, "ai_rate": 0.0},
    "experiment": {"n": 18, "judged_ai": 3, "invalid": 2,
                   "invalid_rate": 0.11, "ai_rate": 0.1667},
    "baseline": {"n": 18, "judged_ai": 18, "invalid": 0,
                 "invalid_rate": 0.0, "ai_rate": 1.0},
}
check("A10-实验组高无效率降级low-basis",
      turing.conclusion(_HIGH_INVALID)[0] == "low-basis",
      f"实际 {turing.conclusion(_HIGH_INVALID)[0]}")
check("A10-基线组高无效率降级low-basis",
      turing.conclusion({**_HIGH_INVALID, "baseline": _HIGH_INVALID["experiment"]})[0]
      == "low-basis", "基线组未降级")
check("A10-无效率正常仍给improved",
      turing.conclusion(_LOW_INVALID)[0] == "improved",
      f"实际 {turing.conclusion(_LOW_INVALID)[0]}")


if failures:
    print("turing-eval 测试未通过：")
    print("\n".join(failures))
    sys.exit(1)
print("turing-eval 测试通过：判定解析、聚合统计、结论判读、消息构造全部符合预期")
