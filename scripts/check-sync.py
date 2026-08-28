"""校验注入物与规则权威源 SKILL.md 的同步。

三层检测：
  1. 在场检查（原有）：manifest 声明的规则编号与触发词必须在文件中出现
  2. 判据锚（anchor）：每条规则在 manifest 存模板侧判据原文短串，归一化后
     必须在模板文本中出现。语义反转（如「删空预告」改成「空预告保留」）
     会破坏判据锚，即被抓到
  3. 规则指纹（fingerprint）：SKILL.md 每条规则正文的归一化哈希存 manifest，
     权威源被改动而 manifest 未更新即报错，强制显式确认同步

不校验全都在，也不做语义理解——只让「改了规则但没同步」必须显式确认，
而不是静默通过。

用法：
  python scripts/check-sync.py                       # 校验
  python scripts/check-sync.py --update-fingerprints # 规则正文有意改动后重算指纹

自测（注入攻击样本）：python scripts/test-sync.py
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "scripts" / "sync-manifest.json"

_PUNCT = "，。；：、！？·…—－“”‘’\"'()（）【】[]《》〈〉|#*`_-"
_TABLE = str.maketrans("", "", _PUNCT)


def normalize(s):
    return "".join(s.translate(_TABLE).split())


def has_rule(text, rule):
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(rule)}(?![0-9])", text) is not None


def _header_patterns(rule):
    esc = re.escape(rule)
    return (
        re.compile(rf"^\*\*{esc}\b"),
        re.compile(rf"^{esc}\b(?=\s)"),
        re.compile(rf"^-\s*{esc}\b"),
        re.compile(rf"^\|\s*{esc}\s*\|"),
    )


def extract_rule_body(skill_text, rule):
    """按 D/B 加粗块、C 单行、F 列表项、N 表格行四种形态抽取规则正文。"""
    lines = skill_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if any(p.match(line) for p in _header_patterns(rule)):
            start = i
            break
    if start is None:
        return None
    if lines[start].startswith(f"**{rule}"):
        body = [lines[start]]
        stop = re.compile(r"^(\*\*[A-Z]+\d+\b|##\s)")
        for line in lines[start + 1:]:
            if stop.match(line):
                break
            body.append(line)
        return "\n".join(body)
    return lines[start]


def rule_fingerprint(skill_text, rule):
    body = extract_rule_body(skill_text, rule)
    if body is None:
        return None
    return hashlib.sha256(normalize(body).encode("utf-8")).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser(description="同步校验")
    parser.add_argument("--update-fingerprints", action="store_true",
                        help="SKILL.md 规则正文有意改动后重算指纹（须同步模板并核对判据锚）")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    texts = {}
    for rel in manifest:
        path = ROOT / rel
        if path.exists():
            texts[rel] = path.read_text(encoding="utf-8")

    if "SKILL.md" not in texts:
        print("SKILL.md 权威源缺失：请在仓库根目录运行校验，或先恢复该文件",
              file=sys.stderr)
        sys.exit(1)

    if args.update_fingerprints:
        skill = texts.get("SKILL.md", "")
        fps = {}
        for rule in manifest["SKILL.md"].get("rules", []):
            fp = rule_fingerprint(skill, rule)
            if fp is None:
                print(f"警告：SKILL.md 中未找到规则 {rule}，未写入指纹", file=sys.stderr)
                continue
            fps[rule] = fp
        manifest["SKILL.md"]["fingerprints"] = fps
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(f"已重算 {len(fps)} 条规则指纹。请确认模板侧判据锚仍成立：")

    failures = []
    skill = texts.get("SKILL.md", "")
    fps = manifest["SKILL.md"].get("fingerprints", {})
    for rule in manifest["SKILL.md"].get("rules", []):
        if rule not in fps:
            failures.append(f"SKILL.md: 规则 {rule} 无指纹（运行 --update-fingerprints 生成）")
            continue
        cur = rule_fingerprint(skill, rule)
        if cur is None:
            failures.append(f"SKILL.md: 规则 {rule} 已不存在于正文（删除规则后请同步 manifest 与模板）")
        elif cur != fps[rule]:
            failures.append(f"SKILL.md: 规则 {rule} 正文与指纹不符——确认改动后运行 "
                            f"--update-fingerprints 并同步模板")
    for rule in fps:
        if rule not in manifest["SKILL.md"].get("rules", []):
            failures.append(f"SKILL.md: 指纹表存在规则 {rule} 但 rules 清单未收录")

    anchor_count = 0
    for rel, spec in sorted(manifest.items()):
        if rel == "SKILL.md":
            continue
        if rel not in texts:
            failures.append(f"{rel}: 文件不存在")
            continue
        text = texts[rel]
        for rule in spec.get("rules", []):
            if not has_rule(text, rule):
                failures.append(f"{rel}: 缺规则编号 {rule}")
        for marker in spec.get("markers", []):
            if marker not in text:
                failures.append(f"{rel}: 缺关键内容 {marker}")
        tn = normalize(text)
        for rule, anchors in spec.get("anchors", {}).items():
            for anchor in anchors:
                anchor_count += 1
                if normalize(anchor) not in tn:
                    failures.append(f"{rel}: 规则 {rule} 判据锚失配「{anchor}」"
                                    f"（语义漂移或漏同步）")

    if failures:
        print("\n".join(failures))
        sys.exit(1)
    print(f"同步校验通过：{len(manifest)} 个文件（指纹 {len(fps)} 条，判据锚 {anchor_count} 处）")


if __name__ == "__main__":
    main()
