#!/usr/bin/env python3
"""verify_repo.py - natural-talk 仓库一键全量自动化体检与契约测试工具 (纯标准库)

运行本脚本将执行十一层自检：
  1. 结构与契约体检 (SKILL.md frontmatter、导航死链、references完备性、锚点契约)
  2. 离线回归与反套路测试 (不变性用例 0 误杀 + AI 塑料套路 100% 捕获)
  3. 隐私与安全审查 (全仓库扫描 API Key、敏感端点与过程草稿)
  4. 压缩分发包一致性 (校验 natural-talk.zip 是否纯净、无冗余开发文件)
  5. 正解示例自检 (✅ 行零病灶，规则不得带病示人)
  6. 日常对话生成期回归
  7. 规则页与扫描器词表一致性
  8. 扫描器红灯测试 (test-scan-mechanical.py)
  9. 清理审计测试 (test-audit-cleanup.py)
 10. 评测环 harness 自测 (test-eval-harness.py)
 11. turing 判分纯函数自测 (test-turing-eval.py)

用法:
    python scripts/verify_repo.py
"""

import subprocess
import sys
import re
import zipfile
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _load_scanner():
    """契约扫描器：scan-mechanical.py（与 SKILL.md 引用链一致的单一规范源）。"""
    return _load_module("scan_mechanical", SCRIPTS_DIR / "scan-mechanical.py")

_scanner = _load_scanner()

def scan_text(text):
    """gen 模式扫描适配层：不变量判 FIX 级 0 命中，对抗样例判任意命中。"""
    return [(h["line"], h["rule"], h["snippet"], h["note"])
            for h in _scanner.scan(text, mode="gen")]

def test_contract():
    print("\n[1/11] 正在执行：Skill 结构与契约完整性测试...")
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
    total_anchors = 0
    try:
        contract_mod = _load_module("test_skill_contract", SCRIPTS_DIR / "test-skill-contract.py")
        total_anchors = sum(len(anchors) for anchors in contract_mod.REQUIRED_ANCHORS.values())
        for rel_path, anchors in contract_mod.REQUIRED_ANCHORS.items():
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
    print("\n[2/11] 正在执行：离线回归与反套路测试...")
    test_rules = _load_module("test_rules_local", SCRIPTS_DIR / "test-rules-local.py")
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
        hits = scan_text(sample)
        if len(hits) == 0:
            slop_fails += 1
            print(f"  ❌ 塑料漏检 [{name}]: 未捕获套路")

    if inv_fails > 0 or slop_fails > 0:
        print(f"  ❌ 失败: {inv_fails} 处误杀, {slop_fails} 处漏检")
        return False
    print(f"  🟢 PASS: {len(INVARIANT_SAMPLES)}/{len(INVARIANT_SAMPLES)} 不变性用例 0 误杀，{len(AI_SLOP_SAMPLES)}/{len(AI_SLOP_SAMPLES)} 变异套路 100% 精准捕获！")
    return True

def test_privacy():
    print("\n[3/11] 正在执行：全仓库隐私与机密信息扫描...")
    # Keywords to check (constructed dynamically to avoid self-match)
    secrets = [''.join(['sk', '_', 'tr_']), ''.join(['sk', '-', 'wZP']), ''.join(['token', 'rhythm']), ''.join(['sak', 'iko'])]
    leakages = []
    
    for p in ROOT.rglob('*'):
        if p.is_file() and not str(p).startswith(str(ROOT / '.git')) and p.name != "verify_repo.py":
            try:
                content = p.read_text(encoding='utf-8', errors='ignore')
                for s in secrets:
                    if s in content:
                        leakages.append((str(p.relative_to(ROOT)), s))
            except Exception:
                pass
                
    # Check for forbidden process dirs
    if (ROOT / '.agents').exists():
        leakages.append(('.agents 目录存在', '过程文件残留'))
    if (ROOT / 'ORIGINAL_REQUEST.md').exists():
        leakages.append(('ORIGINAL_REQUEST.md 存在', '过程文件残留'))

    if leakages:
        for f, s in leakages:
            print(f"  ❌ 泄露风险 [{f}]: 包含 \"{s}\"")
        return False
    print("  🟢 PASS: 仓库内 0 密钥、0 敏感端点、0 过程文件残留（CLEAN）！")
    return True

def test_zip_package():
    print("\n[4/11] 正在执行：分发压缩包 natural-talk.zip 规范性检查...")
    zip_paths = [
        p for p in [
            ROOT / "natural-talk.zip",
            ROOT.parent / "natural-talk.zip",
            ROOT.parent.parent / "natural-talk.zip"
        ] if p.exists()
    ]
    if not zip_paths:
        print("  ⚠️ 跳过: 未找到 natural-talk.zip")
        return True
        
    # 严格白名单机制：面向终端模型的纯净 Skill 分发包只保留模型可读可用文件，绝不携带 README、许可证、脚本或测试
    allowed_exact = {
        "natural-talk/SKILL.md",
    }
    allowed_dirs = (
        "natural-talk/references/",
    )
    
    all_ok = True
    for zip_path in zip_paths:
        forbidden_hits = []
        with zipfile.ZipFile(zip_path, 'r') as z:
            for n in z.namelist():
                if n.endswith('/'):
                    continue
                if n.endswith('.py') or 'scripts/' in n:
                    forbidden_hits.append(f"{n} (AI 不会自动执行 Python 脚本，分发包严禁携带任何脚本文件)")
                    continue
                is_allowed = (n in allowed_exact) or any(n.startswith(d) for d in allowed_dirs)
                if not is_allowed:
                    forbidden_hits.append(n)
                        
        if forbidden_hits:
            for h in forbidden_hits:
                print(f"  ❌ [{zip_path.name}] 压缩包包含非 Skill 冗余项: {h}")
            all_ok = False
        else:
            print(f"  🟢 PASS: {zip_path} ({zip_path.stat().st_size:,} 字节) 极致纯净（零脚本、零测试、纯正 Skill 资产包）！")
    return all_ok

def test_wording_sync_check():
    """词表一致性：规则页写的句首套话必须都在扫描器词表里。

    历史缺口——SKILL.md 与 rules-full.md 已写明「说到底/归根结底/直接给答案」，
    扫描器词表却停在三项，体检全绿而生成期实际漏检。本层把该漂移变成机器可查。
    """
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    full = (ROOT / "references" / "rules-full.md").read_text(encoding="utf-8")
    docs = skill + "\n" + full
    failures = []

    # B10：规则页点名的句首起手式，逐词须在 B10_WORDS
    for word in ("说白了", "说穿了", "先说结论", "说到底", "归根结底"):
        if word not in docs:
            failures.append(f"规则页未提及 B10 起手式「{word}」——用例与文档脱节")
        elif word not in _scanner.B10_WORDS:
            failures.append(f"B10 起手式「{word}」在规则页有定义但扫描器词表缺失")

    # B4a：规则页点名的冒号提示语空壳
    if "直接给答案" not in docs:
        failures.append("规则页未提及「直接给答案」空壳")
    elif "直接给答案" not in _scanner.B4A_PROMPTS:
        failures.append("「直接给答案」在规则页有定义但 B4A 词表缺失")

    # D2：规则页要求的服务腔收尾须有句尾表覆盖（B4a 词表与 D2 尾表至少一处覆盖）
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
    print(f"  🟢 PASS: 规则页与扫描器词表一致（B10 {len(_scanner.B10_WORDS)} 词 / "
          f"B4A {len(_scanner.B4A_PROMPTS)} 词 / D2 收尾已覆盖）")
    return True

def test_daily_gen():
    print("\n[6/11] 正在执行：日常对话生成期回归...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS_DIR / "test-daily-gen.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    stdout = result.stdout or ""
    if result.returncode == 0:
        tail = [line for line in stdout.splitlines() if line.startswith("✅")]
        print(f"  🟢 PASS: {tail[0] if tail else '日常对话生成期回归全绿'}")
        return True
    print(stdout)
    print(result.stderr or "")
    print("  ❌ FAIL: 日常对话生成期规则存在漏检或误报")
    return False


def test_positive_examples():
    print("\n[5/11] 正在执行：正解示例自检（✅ 行零病灶）...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS_DIR / "test-positive-examples.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    if result.returncode == 0:
        print("  🟢 PASS: 全部文档 ✅ 正解示例零翻案腔、零违规破折号！")
        return True
    print(result.stdout or "")
    print("  ❌ FAIL: 正解示例带病灶，规则不得「带病示人」")
    return False


def test_wording_sync():
    print("\n[7/11] 正在执行：规则页与扫描器词表一致性...")
    if test_wording_sync_check():
        return True
    return False


def run_script_test(index, title, script):
    """子进程跑 scripts/test-*.py（它们各自带 CLI 与退出码契约）。"""
    print(f"\n[{index}/11] 正在执行：{title}...")
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
    return run_script_test(8, "扫描器红灯测试（种植病灶/白名单/编码回退）", "test-scan-mechanical.py")


def test_audit_cleanup():
    return run_script_test(9, "清理审计测试（信息守恒/改动归属）", "test-audit-cleanup.py")


def test_eval_harness():
    return run_script_test(10, "评测环 harness 自测（冻结/判分/换行）", "test-eval-harness.py")


def test_turing_eval():
    return run_script_test(11, "turing 判分纯函数自测", "test-turing-eval.py")


def main():
    print("==================================================")
    print("      natural-talk 仓库全量体检自动化测试套件      ")
    print("==================================================")

    ok1 = test_contract()
    ok2 = test_regression()
    ok3 = test_privacy()
    ok4 = test_zip_package()
    ok5 = test_positive_examples()
    ok6 = test_daily_gen()
    ok7 = test_wording_sync()
    ok8 = test_scan_mechanical()
    ok9 = test_audit_cleanup()
    ok10 = test_eval_harness()
    ok11 = test_turing_eval()

    print("\n==================================================")
    if all((ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8, ok9, ok10, ok11)):
        print("🎉 全部 11 项体检测试 100% 通过！仓库处于完美交付状态。")
        print("==================================================")
        sys.exit(0)
    else:
        print("❌ 存在未通过的测试项，请根据上述提示进行修正。")
        print("==================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
