"""模型实际读取文件的轻量契约测试。"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("NATURAL_TALK_ROOT", Path(__file__).resolve().parent.parent))
MODEL_FILES = [
    ROOT / "SKILL.md",
    *sorted((ROOT / "references").glob("*.md")),
    *sorted((ROOT / "templates").glob("*.txt")),
]

FORBIDDEN_DIRECTIONS = (
    "破折号：正常使用",
    "叠词、破折号、句长不限",
    "多数情况加一个“这”字",
    "补“这”字回指",
    "末尾附一行改动计数",
    "默认附改动计数",
    "生成模式：输出前自查对话层、文本层和 fiction 规则",
    "最多输出该数量",
    "F1–F8（角色台词内除外）",
    "引用块与引文完全豁免",
    "引用块与引文禁改",
    "确有延后揭示作用",
    "才合成一句",
    "结果须有已写出的触发动作或观察",
    "结果要能追溯到已写出的触发动作或观察",
    "说话人、指代、对象、时间和已锁定事实不能无提示地矛盾",
    "F8 语义事实不豁免",
    "F8 的语义与事实正确性仍生效",
    "F8、硬事实与绝对原则始终生效",
    "研究数字只用于维护",
    "无测量支撑",
    "回归门 A4 实证",
    "实测无差异",
    "实测无差别",
    "成对数据见 docs",
    "延后揭示构成豁免",
    "原样保留“很久，久到……”这一表层句式",
    "有具体时间、动作、环境变化或感知结果时删除整句",
    "原因暂未揭示一律视为语义缺失",
    "可以自由补造动作、神态、感知、原因、时长或人物关系",
    "角色台词视为资料引文",
    "把台词与旁白的冲突一律视为连续性错误",
)
REQUIRED = {
    "SKILL.md": ("C6", "F6", "F7", "F8", "F8（含台词）", "D6", "装饰性喻体", "不得补造机构名", "留白", "语义", "只输出正文", "硬事实", "指定动作或检查项", "范围不明时先问", "“给3步/3条”=恰好3", "N9 只保护具体且有共享属性", "fiction 正文中的角色台词不算资料引文", "始终改掉“很久，久到……”这一表层句式", "延后揭示本身不构成豁免", "原因暂未揭示本身不是语义缺失", "角色可以撒谎、误判或不可靠", "F1–F8 只能删除、重排或改写原文已有信息"),
    "references/fiction.md": ("F6", "F7", "F8", "F8（含台词）", "很久", "久到", "只输出清理后的正文", "指定动作或检查项", "N9 只保护具体且有共享属性", "角色台词不算资料引文", "始终改掉“很久，久到……”这一表层句式", "延后揭示本身不构成豁免", "原因暂未揭示本身不是语义缺失", "角色可以撒谎、误判或不可靠", "F1–F8 只能删除、重排或改写原文已有信息"),
    "references/rules-dialogue.md": ("C6", "D6", "模糊归因", "声音填满空间", "“给3步/3条”=恰好3"),
    "references/rules-text.md": ("装饰性喻体", "承载解释的比喻", "换算类衍生数字"),
    "templates/system-prompt-fiction.txt": ("F6", "F7", "F8", "在台词中只检查句法、指代和已经确立的连续性", "很久", "久到", "只输出清理后的正文", "硬事实", "输出前搜索叙述中的“—”（单个字符也会命中“——”）", "指定动作或检查项", "N9 只保护具体且有共享属性", "fiction 正文中的角色台词不算资料引文", "始终改掉“很久，久到……”这一表层句式", "延后揭示本身不构成豁免", "原因暂未揭示本身不是语义缺失", "角色可以撒谎、误判或不可靠", "F1–F8 只能删除、重排或改写原文已有信息"),
    "templates/system-prompt-standard.txt": ("C6", "D6", "声音填满空间", "“给3步/3条”=恰好3", "只含改写后的全文", "明确作为资料引用的引文", "不得补造来源", "延后揭示本身不构成豁免"),
    "templates/system-prompt-lite.txt": ("C6", "D6", "B5", "“给3步/3条”=恰好3", "定向加入 B5 与 C6", "明确作为资料引用的引文", "延后揭示本身不构成豁免"),
}


def main():
    failures = []
    for path in MODEL_FILES:
        text = path.read_text(encoding="utf-8")
        for phrase in FORBIDDEN_DIRECTIONS:
            if phrase in text:
                failures.append(f"{path.relative_to(ROOT)}: 含冲突指令「{phrase}」")

    for rel, anchors in REQUIRED.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for anchor in anchors:
            if anchor not in text:
                failures.append(f"{rel}: 缺运行时判据「{anchor}」")

    manifest_path = ROOT / "scripts" / "sync-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel in ("references/fiction.md", "references/rules-dialogue.md", "references/rules-text.md"):
            if rel not in manifest:
                failures.append(f"sync-manifest.json: 未覆盖 {rel}")

    if failures:
        print("skill 契约测试未通过：")
        print("\n".join(failures))
        sys.exit(1)
    print(f"skill 契约测试通过：{len(MODEL_FILES)} 个模型面文件")


if __name__ == "__main__":
    main()
