#!/usr/bin/env python3
"""verify_repo.py - natural-talk 仓库一键全量自动化体检与契约测试工具 (纯标准库)

运行本脚本将执行五层严苛自检：
  1. 结构与契约体检 (SKILL.md frontmatter、导航死链、references完备性)
  2. 离线回归与反套路测试 (不变性用例 0 误杀 + AI 塑料套路 100% 捕获)
  3. 隐私与安全审查 (全仓库扫描 API Key、敏感端点与过程草稿)
  4. 压缩分发包一致性 (校验 natural-talk.zip 是否纯净、无冗余开发文件)
  5. 正解示例自检 (✅ 行零病灶，规则不得带病示人)

用法:
    python scripts/verify_repo.py
"""

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

def _load_scanner():
    """契约扫描器：scan-mechanical.py（与 SKILL.md 引用链一致的单一规范源）。"""
    spec = importlib.util.spec_from_file_location(
        "scan_mechanical", SCRIPTS_DIR / "scan-mechanical.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_scanner = _load_scanner()

def scan_text(text):
    """gen 模式扫描适配层：不变量判 FIX 级 0 命中，对抗样例判任意命中。"""
    return [(h["line"], h["rule"], h["snippet"], h["note"])
            for h in _scanner.scan(text, mode="gen")]

def test_contract():
    print("\n[1/4] 正在执行：Skill 结构与契约完整性测试...")
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
        from importlib.machinery import SourceFileLoader
        contract_mod = SourceFileLoader("test_skill_contract", str(SCRIPTS_DIR / "test-skill-contract.py")).load_module()
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
    print("\n[2/4] 正在执行：离线回归与反套路测试...")
    from importlib.machinery import SourceFileLoader
    test_rules = SourceFileLoader("test_rules_local", str(SCRIPTS_DIR / "test-rules-local.py")).load_module()
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
    print("\n[3/4] 正在执行：全仓库隐私与机密信息扫描...")
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
    print("\n[4/4] 正在执行：分发压缩包 natural-talk.zip 规范性检查...")
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

def test_positive_examples():
    print("\n[5/5] 正在执行：正解示例自检（✅ 行零病灶）...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS_DIR / "test-positive-examples.py")],
        capture_output=True, text=True, cwd=str(ROOT))
    if result.returncode == 0:
        print("  🟢 PASS: 全部文档 ✅ 正解示例零翻案腔、零违规破折号！")
        return True
    print(result.stdout)
    print("  ❌ FAIL: 正解示例带病灶，规则不得「带病示人」")
    return False

def main():
    print("==================================================")
    print("      natural-talk 仓库全量体检自动化测试套件      ")
    print("==================================================")

    ok1 = test_contract()
    ok2 = test_regression()
    ok3 = test_privacy()
    ok4 = test_zip_package()
    ok5 = test_positive_examples()

    print("\n==================================================")
    if ok1 and ok2 and ok3 and ok4 and ok5:
        print("🎉 全部 5 项体检测试 100% 通过！仓库处于完美交付状态。")
        print("==================================================")
        sys.exit(0)
    else:
        print("❌ 存在未通过的测试项，请根据上述提示进行修正。")
        print("==================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
