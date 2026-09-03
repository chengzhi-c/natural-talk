"""评测环 harness 自测：先证明判分设施能捕获已知缺陷，再采信跑分。

覆盖（对应方案 §3.7）：
  1. 留存率边界：84% 报警与 86% 通过恰好相反；膨胀上限 124% 通过与 126% 报警恰好相反
  2. 断言解析：require/forbid 命中与漏报
  3. SHA256 冻结：篡改样例一字节必须拒绝判分
  4. Windows 换行：write_bytes 写出的样例可正常冻结与校验（
 翻译会导致校验和失配）
  5. 扫描判分接线：FIX 残留计入 L2，REVIEW 残留只计数

红灯验证方式：临时注释掉 check-eval.py 的 forbid 分支或 check-retention.py 的
阈值比较 → 本测试必须转红 → 恢复。

运行：python scripts/test-eval-harness.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
EVALS = ROOT / "evals"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


retention = _load("check_retention", SCRIPTS / "check-retention.py")
check_eval = _load("check_eval", EVALS / "check-eval.py")

failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


# ---------- 1. 留存率边界 ----------
ORIG = "字" * 1000
cleaned_84 = "字" * 840
cleaned_86 = "字" * 860

r84 = retention.retention(ORIG, cleaned_84)
r86 = retention.retention(ORIG, cleaned_86)
check("留存率-84数值", abs(r84 - 0.84) < 1e-9, f"实际 {r84}")
check("留存率-86数值", abs(r86 - 0.86) < 1e-9, f"实际 {r86}")
check("留存率-84必须报警", not retention.is_ok(r84), f"{r84} 不应通过 85% 下限")
check("留存率-86必须通过", retention.is_ok(r86), f"{r86} 不应报警")

# 膨胀上限边界：124% 通过、126% 报警（mimo 基线 1.47 膨胀的护栏）
r124 = retention.retention(ORIG, "字" * 1240)
r126 = retention.retention(ORIG, "字" * 1260)
check("留存率-124数值", abs(r124 - 1.24) < 1e-9, f"实际 {r124}")
check("留存率-126数值", abs(r126 - 1.26) < 1e-9, f"实际 {r126}")
check("留存率-124必须通过", retention.is_ok(r124), f"{r124} 不应触发上限")
check("留存率-126必须报警", not retention.is_ok(r126), f"{r126} 应触发膨胀上限")

# 空白不计入归一化（换行、空格、制表符）
r_ws = retention.retention("a b\nc\td", "abcd")
check("留存率-空白归一", abs(r_ws - 1.0) < 1e-9, f"实际 {r_ws}")
# 空原文不应除零
check("留存率-空原文", retention.retention("", "任意") == 1.0, "空原文须按 1.0 处理")

# ---------- 2. 断言解析 ----------
ENTRY = {
    "id": "T-01",
    "prompt_type": "clean",
    "scan_mode": "prose",
    "assertions": [
        {"type": "require_final_regex", "pattern": "连接池", "level": "l1"},
        {"type": "forbid_final_regex", "pattern": "说白了", "level": "l2"},
    ],
}
hit = check_eval.evaluate_case(ENTRY, "原文有说白了。", "瓶颈在连接池。")
check("断言-require命中", hit["verdict"] == "PASS", json.dumps(hit, ensure_ascii=False))
miss = check_eval.evaluate_case(ENTRY, "原文有说白了。", "瓶颈在缓存。")
check("断言-require漏报必须FAIL", miss["verdict"] == "FAIL",
      json.dumps(miss, ensure_ascii=False))
residual = check_eval.evaluate_case(ENTRY, "原文有说白了。", "说白了，瓶颈在连接池。")
check("断言-forbid残留必须WARN", residual["verdict"] == "WARN",
      json.dumps(residual, ensure_ascii=False))

# ---------- 3+4. SHA256 冻结与 Windows 换行 ----------
with tempfile.TemporaryDirectory() as td:
    mini = Path(td) / "evals"
    (mini / "cases").mkdir(parents=True)
    # Windows 纪律：write_bytes 写 \n，避免 write_text 的 \r\n 污染校验和
    case_body = "呼兰河就是这样的小城，只有两条大街。\n".encode("utf-8")
    (mini / "cases" / "T-01.txt").write_bytes(case_body)
    bench = {"id": "T-01", "case": "cases/T-01.txt", "prompt_type": "clean",
             "scan_mode": "prose",
             "assertions": [{"type": "require_final_regex",
                             "pattern": "两条大街", "level": "l1"}]}
    (mini / "benchmark.jsonl").write_bytes(
        (json.dumps(bench, ensure_ascii=False) + "\n").encode("utf-8"))

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    r = subprocess.run([sys.executable, str(EVALS / "check-eval.py"),
                         "--evals", str(mini), "--freeze"],
                        capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-首次成功", r.returncode == 0, f"{r.stdout}{r.stderr}")
    manifest = json.loads((mini / "manifest.json").read_text(encoding="utf-8"))
    check("冻结-记录SHA256", "T-01" in manifest.get("cases", {}),
          "manifest 未记录样例指纹")

    # 篡改一字节 → 拒绝判分
    (mini / "cases" / "T-01.txt").write_bytes(
        case_body.replace("小城".encode("utf-8"), "小城！".encode("utf-8")))
    r = subprocess.run([sys.executable, str(EVALS / "check-eval.py"),
                        "--evals", str(mini)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-篡改必须拒绝", r.returncode != 0, "篡改样例后判分仍通过")

    # 恢复并跑一次空 run（无输出文件 → 按缺失记录，不崩）
    (mini / "cases" / "T-01.txt").write_bytes(case_body)
    r = subprocess.run([sys.executable, str(EVALS / "check-eval.py"),
                        "--evals", str(mini)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-恢复后校验通过", r.returncode == 0, f"{r.stdout}{r.stderr}")

# ---------- 5. 扫描判分接线 ----------
SCAN_ENTRY = {
    "id": "T-02",
    "prompt_type": "clean",
    "scan_mode": "prose",
    "assertions": [],
}
# 输入含 B10(FIX)+B1(REVIEW)；输出清了 B10 留了 B1 → FIX 清零、REVIEW 计入观察
out = check_eval.evaluate_case(SCAN_ENTRY, "说白了，不是技术，而是人。", "不是技术，是人。")
fix_left = [d for d in out["details"] if d.get("kind") == "scan_fix"]
check("扫描-FIX清零且PASS", len(fix_left) == 0 and out["verdict"] == "PASS",
      json.dumps(out, ensure_ascii=False))
out2 = check_eval.evaluate_case(SCAN_ENTRY, "说白了，不是技术，而是人。",
                                 "说白了，不是技术，而是人。")
fix_left2 = [d for d in out2["details"] if d.get("kind") == "scan_fix"]
check("扫描-FIX未清必须WARN", len(fix_left2) > 0 and out2["verdict"] == "WARN",
      json.dumps(out2, ensure_ascii=False))

if failures:
    print("评测环 harness 测试未通过：")
    print("\n".join(failures))
    sys.exit(1)
print("评测环 harness 测试通过：留存率边界、断言解析、SHA256 冻结、"
      "Windows 换行、扫描接线全部符合预期")
