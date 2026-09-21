#!/usr/bin/env python3
"""test-skill-contract.py - 模型实际读取文件的轻量契约测试。"""

import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(os.environ.get("NATURAL_TALK_ROOT", Path(__file__).resolve().parent.parent))

MODEL_FILES = [
    ROOT / "SKILL.md",
    *sorted((ROOT / "references").glob("*.md")),
]

REQUIRED_ANCHORS = {
    "SKILL.md": (
        "name: natural-talk",
        "description:",
        "零号原则",
        "交互姿态",
        "references/fiction.md",
        "references/rules-full.md",
        "scripts/scan-mechanical.py",
        "scripts/audit-cleanup.py",
        "每处改动对应一条编号",
        "信息守恒",
    ),
    "references/rules-full.md": (
        "D1 谄媚与评判越界",
        "D6 模糊归因",
        "B1 翻案腔",
        "B5 破折号揭晓",
        "B12 空降宏观开场",
        "B18 计数癖",
        "C7 动词精准",
        "反复写全称、少用代词",
        "防误杀白名单",
        "频率原则",
        "成文清理边界",
    ),
    "references/fiction.md": (
        "事实与设定守恒",
        "摄影机视点在场",
        "实体阻力",
        "三大动作与场景推进工法与范例",
        "创作自由边界",
        "叙述层破折号：按形态改写",
        "比喻语法结构拦截律",
        "四大工法正向置换律",
        "舞台剧抽搐：写定住",
        "代词呼吸律",
        "感官密度调控",
    ),
}

def check_frontmatter(path: Path, failures: list) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        failures.append(f"{path.name}: frontmatter 缺起始 --- 分隔符")
        return
    try:
        close = lines.index("---", 1)
    except ValueError:
        failures.append(f"{path.name}: frontmatter 缺闭合 --- 分隔符")
        return
    block = "\n".join(lines[1:close])
    for field in ("name:", "description:"):
        if field not in block:
            failures.append(f"{path.name}: frontmatter 缺 {field} 字段")

def main():
    failures = []

    # 1. Check frontmatter of SKILL.md
    check_frontmatter(ROOT / "SKILL.md", failures)

    # 2. Check required anchors in all model files
    for rel_path, anchors in REQUIRED_ANCHORS.items():
        file_path = ROOT / rel_path
        if not file_path.exists():
            failures.append(f"文件不存在: {rel_path}")
            continue
        content = file_path.read_text(encoding="utf-8")
        for anchor in anchors:
            if anchor not in content:
                failures.append(f"{rel_path}: 缺少必选锚点「{anchor}」")

    if failures:
        print("❌ skill 契约测试未通过:")
        for f in failures:
            print(" ", f)
        sys.exit(1)

    print(f"✅ skill 契约测试全部通过 ({len(REQUIRED_ANCHORS)} 个核心文件，{sum(len(v) for v in REQUIRED_ANCHORS.values())} 处关键锚点核验完毕)")

if __name__ == "__main__":
    main()
