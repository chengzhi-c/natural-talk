# -*- coding: utf-8 -*-
"""正解示例自检：全文档 ✅ 行与箭头改法示例不得自带病灶。

规则文档引用病灶（❌ 行）合法，但正解示例（✅ 行、→ 后的改法文本）
自身必须干净，否则"带病示人"。本脚本提取正解示例逐条过
scan-mechanical 的 B1 变体与破折号检查。

误报控制：❌ 行的病灶文本与 ✅ 行同行时，只提取 ✅ 之后的部分；
❌ 与 → 之间的原文不检。
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

spec = importlib.util.spec_from_file_location(
    "scan_mechanical", Path(__file__).resolve().parent / "scan-mechanical.py")
sm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sm)

DOCS = ["SKILL.md", "README.md", "README.en.md", "CONTRIBUTING.md",
        "references/fiction.md", "references/rules-full.md"]

# 明确豁免：正解示例中为了对照而保留的病灶残留说明（人工核对清单）
ALLOWLIST = [
    # （当前无豁免项）
]


def extract_positive_samples(line):
    """从一行提取正解示例文本：✅ 之后、→ 后接 ✅ 的部分。"""
    samples = []
    # → ✅"..." / → ✅`...` 形态
    for m in re.finditer(r"→\s*✅\s*[\"\"`]([^\"\"`]+)[\"\"`]", line):
        samples.append(m.group(1))
    # 行首/独立的 ✅"..." / ✅`...` 形态（不 preceded by ❌）
    for m in re.finditer(r"(?<!❌)✅\s*[\"\"`]([^\"\"`]+)[\"\"`]", line):
        samples.append(m.group(1))
    # ✅ 后裸文本（至行尾）
    for m in re.finditer(r"✅\s*([^\"\"`\`→]+)$", line):
        text = m.group(1).strip()
        if len(text) >= 6:
            samples.append(text)
    return samples


def main():
    failures = []
    for doc in DOCS:
        path = ROOT / doc
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "✅" not in line and "→" not in line:
                continue
            for sample in extract_positive_samples(line):
                sample = sample.strip()
                if not sample or sample in ALLOWLIST:
                    continue
                variants = [m.group(0) for m in sm._B1_VARIANT.finditer(sample)]
                # 排除模式语言（含 A/B 占位符的规则描述）
                if re.search(r"\bA\b|\bB\b|A，|B[。）\"]", sample):
                    variants = [v for v in variants if "A" not in v and "B" not in v]
                dash = sample.count("——") + len(
                    re.findall(r"(?<!—)—(?!—)", sample))
                # 英文文档的 em-dash 排除
                if doc == "README.en.md":
                    dash = 0
                # B10 起手式：正解示例句首不得用提示语开场
                lead_in = any(sample.startswith(w) for w in sm.B10_WORDS)
                # B4a 提示语＋冒号：正解示例不得以空提示语引出
                b4a = any(sample.startswith(w + "：") or sample.startswith(w + ":")
                          for w in sm.B4A_PROMPTS)
                if variants or dash or lead_in or b4a:
                    failures.append({
                        "doc": doc, "line": lineno, "sample": sample[:80],
                        "variants": variants, "dash": dash,
                        "lead_in": lead_in, "b4a": b4a})

    if failures:
        print(f"发现 {len(failures)} 处正解示例带病灶：")
        for f in failures:
            print(f"  {f['doc']}:{f['line']}")
            print(f"    sample: {f['sample']}")
            if f["variants"]:
                print(f"    B1 变体: {f['variants']}")
            if f["dash"]:
                print(f"    破折号: {f['dash']}")
            if f.get("lead_in"):
                print(f"    B10 起手式: 提示语开场")
            if f.get("b4a"):
                print(f"    B4a 提示语冒号: 空提示语引出")
        return 1
    print("正解示例自检通过：全部 ✅ 示例零病灶")
    return 0


if __name__ == "__main__":
    sys.exit(main())
