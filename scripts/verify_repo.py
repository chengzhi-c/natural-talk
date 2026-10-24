#!/usr/bin/env python3
"""verify_repo.py - natural-talk 仓库一键全量自动化体检与契约测试工具 (纯标准库)

运行本脚本将执行如下自检（项数随 results 列表变化）：
  1. 结构与契约体检 (SKILL.md frontmatter、导航死链、references完备性、锚点契约)
  2. 离线回归与反套路测试 (不变性用例 0 误杀 + AI 塑料套路 100% 捕获)
  3. 隐私与安全审查 (全仓库扫描 API Key、敏感端点与过程草稿)
  4. 正解示例自检 (✅ 行零病灶，规则不得带病示人)
  5. 规则页与扫描器词表一致性
  6. 扫描器红灯测试 (test-scan-mechanical.py)
  7. 清理审计测试 (test-audit-cleanup.py)
  8. 评测环 harness 自测 (test-eval-harness.py)
  9. turing 判分纯函数自测 (test-turing-eval.py)
 10. 真实 manifest 冻定态校验（判分器指纹与冻结快照比对，防历史成绩被静默改写）

交付范围：仓库只放 skill 本体（SKILL.md + references/ + scripts/ + evals/）。
分发包只含 SKILL.md 与 references/，在仓库外构建；本脚本不校验 README 与分发包。

用法:
    python scripts/verify_repo.py
"""

import subprocess
import importlib.util
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _loader

_loader.ensure_utf8()

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
# 自检项总数。新增一项时同步改这里，[N/M] 标签才对得上。
_TOTAL_CHECKS = 10
# 契约锚点下限：test-skill-contract.py 的 REQUIRED_ANCHORS 被删条目时转红
_MIN_ANCHORS = 32

# 规则 × 扫描器词表常量 × 期望词集。这是回归守卫，不是文档同步：
# 删词会让这层转红。刻意不拿规则页反查——文档写禁用词会被弱模型照抄，
# 词表只进扫描器。
_WORD_TABLES = [
    ("B10", "B10_WORDS",
     ("说白了", "说穿了", "简单来说", "简单说", "先说结论", "说到底", "归根结底")),
    ("B4a", "B4A_PROMPTS",
     ("一句话总结", "核心是", "关键在于", "原因如下", "本质上", "直接给答案")),
    ("B13", "_B13_ADVERBS",
     ("微微", "极轻", "极慢", "极细", "轻轻", "缓缓")),
    ("B17", "_B17_FANCY_TAGS",
     ("命令道", "吩咐道", "沉声道", "轻声道", "低声说", "低吼道",
      "低声道", "冷声道", "感叹道", "开口道", "沉声说", "轻声说")),
    ("B9", "_B9_CLICHE",
     ("枯井", "一潭死水", "抽走", "从水里捞出来",
      "一床湿透的棉被", "一道晴空霹雳", "被雷劈中", "被泼了一盆冷水")),
    # 明喻标记：词表缺一词即静默漏检（变异测试实测），含"一般/一样"两个口语形。
    ("B9", "_B9_SIMILE",
     ("就像", "如同", "宛如", "仿佛", "犹如", "恰似", "相当于", "一般", "一样")),
    ("B1", "B1_WORDS", ("而是", "其实", "恰恰")),
    ("B3", "B3_OPENERS", ("听起来", "看起来", "值得注意的是", "更重要的是",
                          "关键在于", "问题在于", "说白了")),
    ("B3", "B3_REFERENTS", ("这", "那", "其", "此", "上面")),
    ("B12", "_MACRO_OPENER", ("在当今", "众所周知", "的今天", "时代", "背景",
                              "环境", "随着", "不断", "发展")),
    ("D2", "_D2_OPENERS", ("好问题", "问得好", "这是个好问题", "这真是个好问题",
                           "感谢提问", "感谢你的提问", "希望对你有帮助",
                           "希望对您有帮助", "希望对您有所帮助", "希望对你有启发",
                           "希望这些建议对你有帮助", "如有疑问", "如有任何问题",
                           "欢迎随时提问", "欢迎随时向我提问")),
    ("D2", "_D2_SUMMARY_OPENERS", ("综上所述", "由此可见")),
    ("D3", "_D3_DISCLAIM", ("语言模型", "训练数据", "知识截止")),
    ("D4", "_D4_BALANCE", ("关键在于找到平衡", "要结合实际情况", "没有绝对的对错")),
    ("D5", "_D5_META", ("下面", "我先", "首先由我", "让我们")),
    ("D6", "_D6_ATTRIB", ("研究", "业内", "行业", "专家", "观察者", "用户",
                          "反馈", "认为", "指出", "表示")),
    ("C5", "_C5_ATMOS", ("填满", "充满", "弥漫", "重量", "世界退回")),
]


# 契约锚点清单：关键文档必须包含的锚点串
REQUIRED_ANCHORS = {
    "SKILL.md": (
        "name: natural-talk",
        "description:",
        "零号原则",
        "交互姿态",
        "references/fiction.md",
        "references/rules-full.md",
        "scripts/scan-mechanical.py",
    ),
    "references/rules-full.md": (
        "D1 谄媚与评判越界",
        "D6 模糊归因",
        "D7 多轮对话",
        "B1 翻案腔",
        "B5 破折号揭晓",
        "B12 空降宏观开场",
        "B18 计数癖",
        "C6 动词精准",
        "反复写全称、少用代词",
        "防误杀白名单",
        "频率原则",
        "成文清理边界",
        "只做句内改写，不删内容（第一纪律）",
    ),
    "references/fiction.md": (
        "摄影机视点在场与实体阻力",
        "创作自由边界",
        "占位符与模板变量不得进正文",
        "叙事工法范例",
        "对白形态轮换",
        "B5 叙述层破折号：按形态改写，不设配额",
        "B9 比喻语法结构拦截律",
        "B14 四大工法正向置换律",
        "B15 舞台剧抽搐：写定住与呼吸停顿",
        "B17 代词呼吸律",
        "交付自检",
        "成稿清理子模式",
    ),
}


def _load_module(name, path):
    """按路径加载一个 .py 为模块。"""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scanner = _load_module("scan_mechanical", SCRIPTS_DIR / "scan-mechanical.py")
_test_rules = _load_module("test_rules_local",
                          SCRIPTS_DIR / "test-rules-local.py")

def test_contract():
    print("\n[1/10] 正在执行：Skill 结构与契约完整性测试...")
    failures = []
    
    # 1. Check SKILL.md
    skill_file = ROOT / "SKILL.md"
    if not skill_file.exists():
        failures.append("缺少 SKILL.md")
    else:
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---"):
            failures.append("SKILL.md 缺少起始 frontmatter '---'")
        if "name: natural-talk" not in text:
            failures.append("SKILL.md 缺少 'name: natural-talk' 声明")
        if "description:" not in text:
            failures.append("SKILL.md 缺少 'description:' 字段")
        
        # Check reference files mentioned in SKILL.md
        for ref in [
            "references/fiction.md",
            "references/rules-full.md",
            "scripts/scan-mechanical.py",
            "scripts/audit-cleanup.py",
        ]:
            ref_path = ROOT / ref
            if not ref_path.exists():
                failures.append(f"SKILL.md 导航指向的文件不存在: {ref}")

    # 2. Check references
    for ref_name in ["fiction.md", "rules-full.md"]:
        p = ROOT / "references" / ref_name
        if not p.exists() or p.stat().st_size == 0:
            failures.append(f"缺少参考指南或文件为空: references/{ref_name}")

    # 3. Check critical anchor contracts
    try:
        total_anchors = sum(len(anchors) for anchors in REQUIRED_ANCHORS.values())
        # 锚点清单自身也要有守：从 REQUIRED_ANCHORS 删一条不会让任何测试转红
        # （实测删"D6 模糊归因"后全量体检仍全绿），本层覆盖被静默削弱。
        # 下限只增不减：刻意收缩清单时才改这里
        if total_anchors < _MIN_ANCHORS:
            failures.append(f"契约锚点只剩 {total_anchors} 处（下限 "
                            f"{_MIN_ANCHORS}）：锚点清单被删会静默削弱本层覆盖")
        for rel_path, anchors in REQUIRED_ANCHORS.items():
            file_path = ROOT / rel_path
            if not file_path.exists():
                failures.append(f"文件不存在: {rel_path}")
                continue
            content = file_path.read_text(encoding="utf-8")
            for anchor in anchors:
                if anchor not in content:
                    failures.append(f"{rel_path}: 缺少必选锚点「{anchor}」")
    except Exception as e:
        failures.append(f"无法加载或执行契约锚点测试: {e}")
            
    if failures:
        for f in failures:
            print(f"  ❌ 失败: {f}")
        return False
    print(f"  🟢 PASS: SKILL.md 与全量参考文件结构及 {total_anchors} 处核心契约锚点 100% 完整有效！")
    return True

def test_regression():
    print("\n[2/10] 正在执行：离线回归与反套路测试...")
    test_rules = _test_rules
    INVARIANT_SAMPLES, AI_SLOP_SAMPLES = test_rules.INVARIANT_SAMPLES, test_rules.AI_SLOP_SAMPLES

    inv_fails = 0
    for name, sample in INVARIANT_SAMPLES:
        hits = _scanner.scan(sample, mode="gen")
        fix_hits = [h for h in hits if h["tier"] == "FIX"]
        if len(fix_hits) > 0:
            inv_fails += 1
            print(f"  ❌ 不变性误杀 [{name}]: {fix_hits}")
            
    # Adversarial
    slop_fails = 0
    for name, sample in AI_SLOP_SAMPLES:
        hits = _scanner.scan(sample, mode="gen")
        if len(hits) == 0:
            slop_fails += 1
            print(f"  ❌ 塑料漏检 [{name}]: 未捕获套路")

    if inv_fails > 0 or slop_fails > 0:
        print(f"  ❌ 失败: {inv_fails} 处误杀, {slop_fails} 处漏检")
        return False
    print(f"  🟢 PASS: {len(INVARIANT_SAMPLES)}/{len(INVARIANT_SAMPLES)} 不变性用例 0 FIX 误杀（REVIEW 层由 test-scan-mechanical 精确集合断言守），{len(AI_SLOP_SAMPLES)}/{len(AI_SLOP_SAMPLES)} 变异套路 100% 精准捕获！")
    return True

# 隐私模式合成正例：逐条证明每个 pattern 还能匹配。
# 原来只扫仓库，删掉某个密钥格式同样全绿——漏报的格式没人发现。
# 正例全部为合成字符串，不含任何真实凭据。
SECRET_PROBES = (
    (r"\bsk[-_][A-Za-z0-9_-]{16,}\b", "sk-" + "a" * 20),
    (r"\bAKIA[0-9A-Z]{16}\b", "AKIA" + "0" * 16),
    (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "ghp_" + "a" * 20),
    (r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
     "eyJ" + "a" * 10 + "." + "b" * 10 + "." + "c" * 10),
    (r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]{6,}",
     'password = "hunter2secret"'),
    (r"\b1[3-9]\d{9}\b", "138" + "0013" + "8000"),
    (r"\b\d{17}[\dXx]\b", "110101" + "19900307" + "761X"),
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "someone" + "@" + "example.com"),
    (r"\b(?:10|127)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "10." + "0.0." + "1"),
    (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "192." + "168." + "1.1"),
    (r"C:\\Users\\[A-Za-z0-9._-]+", "C:\\Users\\someone"),
)

def test_privacy():
    print("\n[3/10] 正在执行：全仓库隐私与机密信息扫描...")
    # 凭据形态用正则而不是已知坏串 blocklist：后者只认枚举过的那几个前缀，
    # sk-tr_ 连字符形态、AKIA、password= 赋值全部漏报，而 run-eval.py 的 KEY_RE
    # 是认可这些形态的。字面量仍用拼接写法，避免本文件扫描自己时自匹配。
    # 自守：每个密钥格式都要还能匹配自己的合成正例。
    secret_pats = [
        r"\bsk[-_][A-Za-z0-9_-]{16,}\b",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]{6,}",
        r"\b1[3-9]\d{9}\b",
        r"\b\d{17}[\dXx]\b",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"\b(?:10|127)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        r"\b192\.168\.\d{1,3}\.\d{1,3}\b",
        r"C:\\Users\\[A-Za-z0-9._-]+",
    ]
    # 删掉或改坏任一格式，这里立即转红。
    for _pat, _sample in SECRET_PROBES:
        if _pat not in secret_pats or re.search(_pat, _sample) is None:
            print(f"  ❌ FAIL: 隐私模式失效或已从 secret_pats 删除：{_pat}")
            return False
    findings = []
    for f in ROOT.rglob("*"):
        if not f.is_file() or "__pycache__" in f.parts:
            continue
        if f.suffix not in (".py", ".md", ".json", ".jsonl", ".txt"):
            continue
        # 自己扫描自己：字面量靠上面这些 pattern 的形式存在，跳过自身最稳
        if f.name == "verify_repo.py":
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pat in secret_pats:
            for m in re.finditer(pat, content):
                findings.append(f"{f.relative_to(ROOT)}: {m.group(0)[:60]}")

    # 过程文件：不该进交付物的草稿与日志
    junk = []
    for pat in ("*.log", "*.tmp", "*.bak", "*-old.*", "*-backup.*",
                "*.lock", "PROJECT-STRUCTURE.md", "ORIGINAL_REQUEST.md"):
        junk += [str(p.relative_to(ROOT)) for p in ROOT.rglob(pat)]
    for d in (".agents", "corpus"):
        if (ROOT / d).exists():
            junk.append(d + "/")

    # 行尾纪律：.gitattributes 声明 eol=lf，但仓库无 .git 时它不执行，
    # 行尾回潮只能靠机器把守。
    crlf = []
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or "__pycache__" in f.parts:
            continue
        if f.suffix not in (".md", ".py", ".json", ".jsonl", ".txt",
                            ".gitignore", ".gitattributes"):
            continue
        try:
            if f.read_bytes().count(b"\r\n"):
                crlf.append(str(f.relative_to(ROOT)))
        except OSError:
            continue

    if findings or junk or crlf:
        if findings:
            print("  ❌ FAIL: 发现敏感信息或疑似密钥:")
            for x in findings[:20]:
                print("    ", x)
        if junk:
            print("  ❌ FAIL: 发现过程文件残留:")
            for x in junk[:20]:
                print("    ", x)
        if crlf:
            print("  ❌ FAIL: 以下文件含 CRLF（.gitattributes 要求全 LF）:")
            for x in crlf[:20]:
                print("    ", x)
        return False
    print("  🟢 PASS: 仓库内 0 密钥、0 敏感端点、0 过程文件残留、全 LF（CLEAN）！")
    return True


def test_wording_sync_check():
    """词表一致性：规则页写的句首套话必须都在扫描器词表里。

    历史缺口——SKILL.md 与 rules-full.md 已写明「说到底/归根结底/直接给答案」，
    扫描器词表却停在三项，体检全绿而生成期实际漏检。本层把该漂移变成机器可查。
    """
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    full = (ROOT / "references" / "rules-full.md").read_text(encoding="utf-8")
    docs = skill + "\n" + full
    failures = []

    # 词表回归守卫：删词会让这层转红。历史缺口——这层原来只盯 B10/B4A/D2，
    # 删 B13 的"缓缓"后按合法流程重冻，全量体检仍全绿而生成期已漏检。
    # 刻意不做"文档点名 → 扫描器"的反查：文档写禁用词会被弱模型照抄。
    for rule, attr, expected in _WORD_TABLES:
        table = getattr(_scanner, attr, None)
        if table is None:
            failures.append(f"{rule} 词表常量 {attr} 不存在（被改名或删除）")
            continue
        pattern = getattr(table, "pattern", None)
        hay = pattern if pattern is not None else " ".join(table)
        for word in expected:
            if word not in hay:
                failures.append(
                    f"{rule} 词表回归：{attr} 缺少「{word}」（被删或改名）")

    # D2：规则页要求的服务腔收尾须有句尾表覆盖
    for word in ("希望能帮到你", "随时联系我"):
        if word not in docs:
            continue
        covered = (word in _scanner._D2_TAIL.pattern
                   or word in _scanner._D2_OPENERS
                   or word in _scanner._D2_SERVICE_EXT.pattern)
        if not covered:
            failures.append(f"D2 收尾「{word}」在规则页有定义但扫描器无覆盖")

    if failures:
        for f in failures:
            print(f"  ❌ 词表漂移: {f}")
        return False
    _n_words = sum(len(w) for _, _, w in _WORD_TABLES)
    print(f"  🟢 PASS: 扫描器词表回归守卫通过"
          f"（{len(_WORD_TABLES)} 张表 / {_n_words} 词 / D2 收尾已覆盖）")
    return True

def test_positive_examples():
    return run_script_test(4, "正解示例自检（✅ 行零病灶）",
                           "test-positive-examples.py")


def test_wording_sync():
    print("\n[5/10] 正在执行：规则页与扫描器词表一致性...")
    return test_wording_sync_check()


def run_script_test(index, title, script):
    """子进程跑 scripts/test-*.py（它们各自带 CLI 与退出码契约）。"""
    print(f"\n[{index}/{_TOTAL_CHECKS}] 正在执行：{title}...")
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS_DIR / script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    if result.returncode == 0:
        tail = [line for line in (result.stdout or "").splitlines() if line.strip()]
        print(f"  🟢 PASS: {tail[-1] if tail else script + ' 全绿'}")
        return True
    print(result.stdout or "")
    print(result.stderr or "")
    print(f"  ❌ FAIL: {script}")
    return False


def test_scan_mechanical():
    return run_script_test(6, "扫描器红灯测试（种植病灶/白名单/编码回退）", "test-scan-mechanical.py")


def test_audit_cleanup():
    return run_script_test(7, "清理审计测试（新增溯源/改动归属）", "test-audit-cleanup.py")


def test_eval_harness():
    return run_script_test(8, "评测环 harness 自测（冻结/判分/换行）", "test-eval-harness.py")


def test_turing_eval():
    return run_script_test(9, "turing 判分纯函数自测", "test-turing-eval.py")


def _clean_pycache():
    """测试以子进程方式跑，会往仓库写 __pycache__（import _loader 不受 -B 约束）。

    .gitignore 已忽略该目录，但整目录打包会带出去，交付前必须清干净。
    """
    import shutil
    n = 0
    for d in ROOT.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)
        n += 1
    return n


def test_real_manifest_frozen():
    """对真实 evals/manifest.json 跑一次冻定态校验。

    test-eval-harness 只在合成临时目录里测 freeze() 的逻辑，
    从不碰真实 manifest。扫描器改过而没重冻时，harness
    测试全绿而 `check-eval.py` 真实判分入口 exit 1——
    "10/10 完美"与"判分被锁死"并存。这一项把路堵上。
    """
    print("\n[10/10] 正在执行：真实 manifest 冻定态校验...")
    out = subprocess.run(
        [sys.executable, "-B", str(ROOT / "evals" / "check-eval.py")],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    if out.returncode != 0:
        print(f"  ❌ 失败: 真实判分入口被锁（exit {out.returncode}）："
              f"{(out.stdout or out.stderr).strip()[:160]}")
        print("     修法：python evals/check-eval.py --freeze --reason “<原因>”")
        return False
    print("  🟢 PASS: 真实 manifest 与判分器指纹一致，判分入口可用")
    return True


def main():
    print("==================================================")
    print("      natural-talk 仓库全量体检自动化测试套件      ")
    print("==================================================")

    results = [
        ("skill 契约", test_contract()),
        ("本地回归", test_regression()),
        ("隐私合规", test_privacy()),
        ("正解示例", test_positive_examples()),
        ("规则页措辞同步", test_wording_sync()),
        ("扫描器红灯", test_scan_mechanical()),
        ("清理审计", test_audit_cleanup()),
        ("评测环 harness", test_eval_harness()),
        ("turing 判分", test_turing_eval()),
        ("真实 manifest 冻结态", test_real_manifest_frozen()),
    ]
    failed = [name for name, ok in results if ok is False]

    print("\n==================================================")
    if failed:
        print(f"❌ 存在未通过的测试项：{'、'.join(failed)}")
        print("==================================================")
        sys.exit(1)
    cleaned = _clean_pycache()
    print(f"🎉 全部 {len(results)} 项体检测试 100% 通过！仓库处于完美交付状态。")
    if cleaned:
        print(f"   （已清理 {cleaned} 个测试再生的 __pycache__）")
    print("==================================================")
    sys.exit(0)

if __name__ == "__main__":
    main()
