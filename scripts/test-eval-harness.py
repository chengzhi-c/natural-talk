"""评测环 harness 自测：先证明判分设施能捕获已知缺陷，再采信跑分。

覆盖测试项：
  1. 留存率边界：84% 报警与 86% 通过恰好相反；膨胀上限 124% 通过与 126% 报警恰好相反
  2. 断言解析：require/forbid 命中与漏报
  3. SHA256 冻结：篡改样例一字节必须拒绝判分
  4. Windows 换行：write_bytes 写出的样例可正常冻结与校验（CRLF 翻译会导致校验和失配）
  5. 扫描判分接线：FIX 残留计入 L2，REVIEW 残留只计数
  6. 缺输出按缺失记录不崩；score_run 优先判 rN 且 ID 不漂移
  7. summarize 按用例 ID 并轨：rN 重复跑不把 2 例算成 3 例
  8. min_output_chars 与实词 2-gram 重合度下限

红灯验证方式：临时注释掉 check-eval.py 的 forbid 分支、check-retention.py 的
阈值比较、score_run 的 rN 优先级、summarize 的 ID 并轨、freeze 的 --reason
闸门或 content_overlap 的下限比较 → 本测试必须转红 → 恢复。

运行：python scripts/test-eval-harness.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import _loader

_loader.ensure_utf8()

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
# 判分器复用同一护栏：膨胀超上限同样 FAIL（只判下限时，把原文重复一遍也能过）
BLOAT = {"id": "T-02", "prompt_type": "clean", "scan_mode": "prose",
         "overlap_min": 0,
         "assertions": [{"type": "require_final_regex", "pattern": "呼兰河",
                         "level": "l1"}],
         "retention_min": 0.5}
bloat = check_eval.evaluate_case(BLOAT, ORIG, ORIG + ORIG)
check("判分-膨胀超上限必须FAIL", bloat["verdict"] == "FAIL",
      json.dumps(bloat, ensure_ascii=False))
check("判分-膨胀归因上限",
      any(d.get("kind") == "retention" and "膨胀" in d.get("why", "")
          for d in bloat["details"]), json.dumps(bloat, ensure_ascii=False))

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
    # 单测夹具是短句，2-gram 重合度天然低；显式关掉下限，只测断言语义
    "overlap_min": 0,
    "assertions": [
        {"type": "require_final_regex", "pattern": "连接池", "level": "l1"},
        {"type": "forbid_final_regex", "pattern": "说白了", "level": "l2"},
    ],
}
ASSERT_ORIG = ("说白了，连接池的瓶颈一直摆在那里没人管，压测数据也在手里，"
               "就是没人愿意动那一行配置。")
hit = check_eval.evaluate_case(ENTRY, ASSERT_ORIG, "瓶颈在连接池。")
check("断言-require命中", hit["verdict"] == "PASS", json.dumps(hit, ensure_ascii=False))
miss = check_eval.evaluate_case(ENTRY, ASSERT_ORIG, "瓶颈在缓存。")
check("断言-require漏报必须FAIL", miss["verdict"] == "FAIL",
      json.dumps(miss, ensure_ascii=False))
residual = check_eval.evaluate_case(ENTRY, ASSERT_ORIG, "说白了，瓶颈在连接池，压测数据也在手里。")
check("断言-forbid残留必须WARN", residual["verdict"] == "WARN",
      json.dumps(residual, ensure_ascii=False))
check("断言-forbid残留明细含forbid",
      any(d.get("kind") == "forbid" for d in residual["details"]),
      "明细里没有 forbid 条目：verdict 被 scan_fix 兜住，注释掉 forbid 分支也测不出来")
# 病灶词换成扫描器抓不到的词：此时只有 forbid 分支能让它 WARN，这是唯一能证明
# "注释 forbid 分支会转红"的形态（"说白了"同时是 B10 的 FIX 词，会被 scan 兜住）
STEALTH = {"id": "T-03", "prompt_type": "clean", "scan_mode": "prose",
           "overlap_min": 0,
           "assertions": [{"type": "forbid_final_regex",
                           "pattern": "连接池打满了", "level": "l2"}]}
stealth = check_eval.evaluate_case(STEALTH, ASSERT_ORIG, "原因很简单：连接池打满了。")
check("断言-扫描器外的forbid残留必须WARN", stealth["verdict"] == "WARN",
      json.dumps(stealth, ensure_ascii=False))
check("断言-扫描器外的forbid明细含forbid",
      any(d.get("kind") == "forbid" for d in stealth["details"]),
      json.dumps(stealth, ensure_ascii=False))

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

    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"),
                         "--evals", str(mini), "--freeze"],
                        capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-首次成功", r.returncode == 0, f"{r.stdout}{r.stderr}")
    manifest = json.loads((mini / "manifest.json").read_text(encoding="utf-8"))
    check("冻结-记录SHA256", "T-01" in manifest.get("cases", {}),
          "manifest 未记录样例指纹")

    # 篡改一字节 → 拒绝判分
    (mini / "cases" / "T-01.txt").write_bytes(
        case_body.replace("小城".encode("utf-8"), "小城！".encode("utf-8")))
    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"),
                        "--evals", str(mini)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-篡改必须拒绝", r.returncode != 0, "篡改样例后判分仍通过")

    # 恢复并跑一次空 run（无输出文件 → 按缺失记录，不崩）
    (mini / "cases" / "T-01.txt").write_bytes(case_body)
    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"),
                        "--evals", str(mini)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-恢复后校验通过", r.returncode == 0, f"{r.stdout}{r.stderr}")

    # ---- --reason 闸门：判据漂移后无理由必须拒绝冻结 ----
    # 没有这条，"有意变更须在 manifest.changes 记理由"只靠自觉：改掉断言直接
    # --freeze 会把痕迹一并抹掉，changes 永远停在首次冻结时的条目。
    bench["assertions"] = [{"type": "require_final_regex",
                            "pattern": "三条大街", "level": "l1"}]
    (mini / "benchmark.jsonl").write_bytes(
        (json.dumps(bench, ensure_ascii=False) + "\n").encode("utf-8"))
    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"),
                        "--evals", str(mini), "--freeze"],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-判据漂移无reason必须拒绝", r.returncode != 0
          and "拒绝冻结" in (r.stdout + r.stderr), f"{r.stdout}{r.stderr}")
    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"),
                        "--evals", str(mini), "--freeze",
                        "--reason", "断言口径收紧"],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-判据漂移带reason必须成功", r.returncode == 0,
          f"{r.stdout}{r.stderr}")
    _man = json.loads((mini / "manifest.json").read_text(encoding="utf-8"))
    _last = _man["changes"][-1] if _man["changes"] else {}
    check("冻结-changes记理由与用例",
          _last.get("reason") == "断言口径收紧"
          and _last.get("cases") == ["T-01"],
          json.dumps(_man["changes"], ensure_ascii=False))

    # 闸门的另一半：判分器指纹漂移（改判分逻辑）同样要记理由。
    # 指纹含真实仓库脚本，CLI 路径改不动，故进程内替身跑 freeze()。
    _fp = check_eval.scorer_fingerprint
    check_eval.scorer_fingerprint = lambda: dict(
        _fp(), **{"scripts/scan-mechanical.py": "0" * 64})
    try:
        try:
            check_eval.freeze(mini)
            check("冻结-判分器漂移无reason必须拒绝", False,
                  "freeze() 未抛 SystemExit：闸门被注释掉也没人发现")
        except SystemExit as e:
            check("冻结-判分器漂移无reason必须拒绝",
                  "拒绝冻结" in str(e), str(e))
        check_eval.freeze(mini, reason="判分阈值调整")
        _man = json.loads((mini / "manifest.json").read_text(encoding="utf-8"))
        check("冻结-判分器漂移带reason写入新指纹",
              _man["scorer"]["scripts/scan-mechanical.py"] == "0" * 64
              and any(c.get("scorer") for c in _man["changes"]),
              json.dumps(_man["changes"], ensure_ascii=False))
    finally:
        check_eval.scorer_fingerprint = _fp


    # ---- 冻结契约：判据字段 / 反向遍历 / 判分器指纹 / 缩水下限 ----
    # 判据字段漂移（改 scan_mode 不改样例）必须拒绝：只冻样例文本不冻判据，
    # 跑分后改一个 prompt_type 就能把留存约束整条绕开
    bench["scan_mode"] = "fiction"
    (mini / "benchmark.jsonl").write_bytes(
        (json.dumps(bench, ensure_ascii=False) + "\n").encode("utf-8"))
    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"),
                        "--evals", str(mini)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-判据字段漂移必须拒绝", r.returncode != 0
          and "判据" in (r.stdout + r.stderr), f"{r.stdout}{r.stderr}")
    bench["scan_mode"] = "prose"
    (mini / "benchmark.jsonl").write_bytes(
        (json.dumps(bench, ensure_ascii=False) + "\n").encode("utf-8"))

    # manifest 反向遍历：benchmark 里删掉的用例同样报失败，否则删掉难看的
    # 一例就能无声提高通过率
    (mini / "benchmark.jsonl").write_bytes(b"")
    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"),
                        "--evals", str(mini)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    check("冻结-删用例必须拒绝", r.returncode != 0
          and "T-01" in (r.stdout + r.stderr), f"{r.stdout}{r.stderr}")
    (mini / "benchmark.jsonl").write_bytes(
        (json.dumps(bench, ensure_ascii=False) + "\n").encode("utf-8"))

    # 判分器指纹比对：改判分逻辑必须被 check_frozen 抓住（CLI 路径改不动真实
    # 脚本，进程内替身）
    _fp = check_eval.scorer_fingerprint
    # 假值与前一节冻进的不同（那节已把 0*64 写进 manifest），
    # 否则两次替身值相同，比对不出差异
    check_eval.scorer_fingerprint = lambda: dict(
        _fp(), **{"scripts/scan-mechanical.py": "1" * 64})
    try:
        check("冻结-判分器指纹不符必须拒判",
              check_eval.check_frozen(mini) != [], "check_frozen 未报指纹不符")
    finally:
        check_eval.scorer_fingerprint = _fp

    # 缩水下限：低于 retention_min 必须 FAIL（膨胀上限早有对应用例，下限没有）
    _floor_entry = {"id": "T-09", "prompt_type": "clean", "scan_mode": "prose",
                    "overlap_min": 0, "retention_min": 0.9, "assertions": []}
    _shrunk = check_eval.evaluate_case(_floor_entry, ORIG, "字" * 800)
    check("判分-缩水下限必须FAIL", _shrunk["verdict"] == "FAIL"
          and any(d.get("kind") == "retention" for d in _shrunk["details"]),
          json.dumps(_shrunk, ensure_ascii=False))


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

# ---------- 6. 缺输出按缺失记录，不崩 ----------
# ---------- 7. rN 判分优先级与 ID 稳定性 ----------
# ---------- 8. summarize 按用例 ID 并轨 ----------
# ---------- 9. min_output_chars 与实词 2-gram 重合度下限 ----------
with tempfile.TemporaryDirectory() as td:
    mini = Path(td) / "evals"
    (mini / "cases").mkdir(parents=True)
    case_body = "呼兰河就是这样的小城，只有两条大街。\n".encode("utf-8")
    (mini / "cases" / "T-01.txt").write_bytes(case_body)
    (mini / "cases" / "T-02.txt").write_bytes(case_body)
    bench1 = {"id": "T-01", "case": "cases/T-01.txt", "prompt_type": "clean",
              "scan_mode": "prose", "overlap_min": 0,
              "assertions": [{"type": "require_final_regex",
                              "pattern": "两条大街", "level": "l1"}]}
    bench2 = {"id": "T-02", "case": "cases/T-02.txt", "prompt_type": "clean",
              "scan_mode": "prose", "overlap_min": 0,
              "assertions": [{"type": "min_output_chars", "level": "l1",
                              "value": 30}]}
    # T-03 不关重合度下限：专测"关键词 + 填充"这条路
    bench3 = {"id": "T-03", "case": "cases/T-01.txt",
              "prompt_type": "clean", "scan_mode": "prose",
              "assertions": [{"type": "require_final_regex",
                              "pattern": "两条大街", "level": "l1"}]}
    (mini / "benchmark.jsonl").write_bytes(
        (json.dumps(bench1, ensure_ascii=False) + "\n"
         + json.dumps(bench2, ensure_ascii=False) + "\n"
         + json.dumps(bench3, ensure_ascii=False) + "\n").encode("utf-8"))
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # 判分前先冻结：没有 manifest 时 check_frozen 直接拒判，后面的断言全空转
    subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"),
                    "--evals", str(mini), "--freeze"],
                   capture_output=True, text=True, encoding="utf-8", env=env)
    run = Path(td) / "run"
    run.mkdir()
    # 只放 T-01：T-02 缺输出必须记 missing_output，不能 FileNotFoundError
    (run / "T-01.txt").write_bytes(case_body)
    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"), str(run),
                         "--evals", str(mini)],
                        capture_output=True, text=True, encoding="utf-8", env=env)
    check("缺输出-不崩", r.returncode in (0, 1) and "Traceback" not in r.stderr,
          f"{r.stdout}{r.stderr}")
    check("缺输出-记入missing_outputs",
          "missing_outputs" in r.stdout and "T-02" in r.stdout, r.stdout)

    # rN 优先于 <id>.txt，且 ID 用用例 ID 不漂移
    (run / "T-01.r1.txt").write_bytes(case_body)

    def _probe(body):
        return subprocess.run(
            [sys.executable, "-B", "-c", body,
             str(EVALS / "check-eval.py"), str(run), str(mini)],
            capture_output=True, text=True, encoding="utf-8", env=env)

    LOAD = ("import importlib.util,sys;"
            "spec=importlib.util.spec_from_file_location('ce',sys.argv[1]);"
            "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);")
    rep = _probe(LOAD + "import json;print(json.dumps("
                 "m.score_run(sys.argv[2],sys.argv[3]),ensure_ascii=False))")
    if rep.returncode != 0:
        check("rN-score_run可调用", False, rep.stderr)
    else:
        got = json.loads(rep.stdout)
        check("rN-判rN不判txt",
              [x["source"] for x in got if x["id"] == "T-01"] == ["T-01.r1.txt"],
              json.dumps(got, ensure_ascii=False))
        check("rN-ID不漂移",
              all(x["id"] in ("T-01", "T-02", "T-03") for x in got),
              json.dumps(got, ensure_ascii=False))
        check("rN-缺输出仍记录", any(x["id"] == "T-02" for x in got),
              json.dumps(got, ensure_ascii=False))
        # summarize 按用例 ID 并轨：两份 rN 不能把 2 例算成 3 例
        (run / "T-01.r2.txt").write_bytes(case_body)
        rep = _probe(LOAD + "import json;print(json.dumps("
                     "m.summarize(m.score_run(sys.argv[2],sys.argv[3])),"
                     "ensure_ascii=False))")
        if rep.returncode != 0:
            check("rN-summarize可调用", False, rep.stderr)
        else:
            s = json.loads(rep.stdout)
            check("rN-并轨后cases仍是3", s["cases"] == 3,
                  json.dumps(s, ensure_ascii=False))

    # min_output_chars：短输出必须 FAIL（此前 SF-07 靠 10 字门槛被糊弄）
    short_run = Path(td) / "short"
    short_run.mkdir()
    (short_run / "T-02.txt").write_bytes("太短".encode("utf-8"))
    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"), str(short_run),
                         "--evals", str(mini)],
                        capture_output=True, text=True, encoding="utf-8", env=env)
    check("短输出-必须FAIL", r.returncode == 1
          and "min_output_chars" in r.stdout, r.stdout)

    # 实词 2-gram 重合度：关键词 + 填充补字数必须 FAIL
    stuff_run = Path(td) / "stuff"
    stuff_run.mkdir()
    # 字数留在区间内、内容却换掉：只有重合度下限能抓住（留存率此时还是绿的）
    (stuff_run / "T-03.txt").write_bytes(
        "两条大街，小城里有河有树有桥。".encode("utf-8"))
    r = subprocess.run([sys.executable, "-B", str(EVALS / "check-eval.py"), str(stuff_run),
                         "--evals", str(mini)],
                        capture_output=True, text=True, encoding="utf-8", env=env)
    check("关键词填充-必须FAIL", r.returncode == 1 and "overlap" in r.stdout,
          r.stdout)

if failures:
    print("评测环 harness 测试未通过：")
    print("\n".join(failures))
    sys.exit(1)
print("评测环 harness 测试通过：留存率边界、断言解析、SHA256 冻结、"
      "Windows 换行、扫描接线、缺输出与 rN 判分、并轨汇总、"
      "重合度下限全部符合预期")
