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
    *sorted((ROOT / "templates").glob("*.txt")),
]

REQUIRED_ANCHORS = {
    "SKILL.md": (
        "name: natural-talk",
        "description:",
        "零号原则",
        "交互姿态",
        "叙事创作",
        "成文清理",
        "全局通杀红线",
        "静默交付契约",
        "references/fiction.md",
        "references/dialogue.md",
        "references/polish.md",
    ),
    "references/fiction.md": (
        "事实与设定守恒",
        "摄影机视点在场",
        "实体阻力",
        "比喻极度克制",
        "小动作代偿",
        "台词人设主权",
    ),
    "references/dialogue.md": (
        "第一句直奔核心",
        "拒绝表演性共情",
        "自然段落展开",
        "去翻案套话",
        "台词人设主权",
    ),
    "references/polish.md": (
        "严格信息守恒",
        "严禁脑补新剧情",
        "篇幅保护",
        "80%~100%",
        "静默成文交付",
    ),
    "templates/system-prompt-fiction.txt": (
        "事实与设定守恒",
        "台词人设主权",
        "摄影机视点在场",
        "比喻极度克制",
        "反塑料套路红线",
    ),
    "templates/system-prompt-standard.txt": (
        "事实与设定守恒",
        "台词人设主权",
        "第一句直奔主题",
        "拒绝发奖状",
        "去翻案套话",
    ),
    "templates/system-prompt-lite.txt": (
        "首句直入主题",
        "拒绝发奖状",
        "静默交付",
        "反塑料红线",
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
