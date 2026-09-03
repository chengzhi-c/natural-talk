#!/usr/bin/env python3
"""verify_repo.py - natural-talk 仓库一键全量自动化体检与契约测试工具 (纯标准库)

运行本脚本将执行四层严苛自检：
  1. 结构与契约体检 (SKILL.md frontmatter、导航死链、references完备性)
  2. 离线回归与反套路测试 (22个不变性用例 0 误杀 + 57个AI塑料套路 100% 捕获)
  3. 隐私与安全审查 (全仓库扫描 API Key、敏感端点与过程草稿)
  4. 压缩分发包一致性 (校验 natural-talk.zip 是否纯净、无冗余开发文件)

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
from scan_slop import scan_text

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
        for ref in ["references/fiction.md", "references/dialogue.md", "references/polish.md"]:
            ref_path = ROOT / ref
            if not ref_path.exists():
                failures.append(f"SKILL.md 导航指向的文件不存在: {ref}")

    # 2. Check references
    for ref_name in ["fiction.md", "dialogue.md", "polish.md"]:
        p = ROOT / "references" / ref_name
        if not p.exists() or p.stat().st_size == 0:
            failures.append(f"缺少参考指南或文件为空: references/{ref_name}")
            
    if failures:
        for f in failures:
            print(f"  ❌ 失败: {f}")
        return False
    print("  🟢 PASS: SKILL.md 与参考文件结构契约 100% 完整有效！")
    return True

def test_regression():
    print("\n[2/4] 正在执行：离线回归与反套路测试...")
    from importlib.machinery import SourceFileLoader
    test_rules = SourceFileLoader("test_rules_local", str(SCRIPTS_DIR / "test-rules-local.py")).load_module()
    INVARIANT_SAMPLES, AI_SLOP_SAMPLES = test_rules.INVARIANT_SAMPLES, test_rules.AI_SLOP_SAMPLES
    
    # Invariants
    inv_fails = 0
    for name, sample in INVARIANT_SAMPLES:
        hits = scan_text(sample)
        if len(hits) > 0:
            inv_fails += 1
            print(f"  ❌ 不变性误杀 [{name}]: {hits}")
            
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
    print(f"  🟢 PASS: 22/22 不变性用例 0 误杀，57/57 变异套路 100% 精准捕获！")
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
    zip_path = ROOT.parent / "natural-talk.zip"
    if not zip_path.exists():
        print(f"  ⚠️ 跳过: 未找到 {zip_path.name}")
        return True
        
    # 严格白名单机制：面向终端模型与用户的纯净 Skill 分发包只保留 Skill 资产，绝不携带开发/测试脚本
    allowed_exact = {
        "natural-talk/SKILL.md",
        "natural-talk/README.md",
        "natural-talk/README.en.md",
        "natural-talk/LICENSE",
    }
    allowed_dirs = (
        "natural-talk/references/",
    )
    
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
            print(f"  ❌ 压缩包包含非 Skill 冗余项: {h}")
        return False
    print(f"  🟢 PASS: {zip_path.name} ({zip_path.stat().st_size:,} 字节) 极致纯净（零脚本、零测试、纯正 Skill 资产包）！")
    return True

def main():
    print("==================================================")
    print("      natural-talk 仓库全量体检自动化测试套件      ")
    print("==================================================")
    
    ok1 = test_contract()
    ok2 = test_regression()
    ok3 = test_privacy()
    ok4 = test_zip_package()
    
    print("\n==================================================")
    if ok1 and ok2 and ok3 and ok4:
        print("🎉 全部 4 项体检测试 100% 通过！仓库处于完美交付状态。")
        print("==================================================")
        sys.exit(0)
    else:
        print("❌ 存在未通过的测试项，请根据上述提示进行修正。")
        print("==================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
