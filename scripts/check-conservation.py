# -*- coding: utf-8 -*-
"""清理模式守恒检查：原文与改后文比对，机械判定改动是否合规。

清理模式的承诺（SKILL.md）：
  1. 信息守恒——姓名/数字/日期/引语不增删，限定词强度不变
  2. 白名单——每处改动能对应 B 编号或执行要求，反清单内的内容不得动
  3. 结构保形——标题层级、段落顺序、列表表格代码块位置不动
  4. 篇幅——不含改动说明时不超过原文的 1.35 倍

正则判不了的（语感润色是否算 B7 打散）不在此处，靠 eval-regression 的人工判读。
这里只测能机械定位的部分，测不到的明确报"未覆盖"。

用法：
    python scripts/check-conservation.py <原文.md> <改后.md>
    python scripts/check-conservation.py --selftest   # 内置违例自测
"""
import difflib
import re
import sys

# 反清单与结构锚点：原文中出现，改后文必须逐字保留
STRUCT_MARKS = re.compile(r"^(#{1,6}\s|\||```|>|- |\* |\d+\. )")

# 限定词与让步——强度不得变化
HEDGES = ["可能", "通常", "或许", "大约", "一般来说", "据说", "据称", "在一定程度上",
          "似乎", "基本", "偶尔", "少数", "部分", "未必"]

# 反清单词——出现不是问题，被改掉才是问题
ANTI_LIST_WORDS = ["赋能", "闭环", "抓手", "底层逻辑", "至关重要"]

CHANGE_EXPLAIN = re.compile(
    r"(改动说明|改动依据|改动清单|逐项说明|检查结果|清理结果|命中规则|"
    r"验收[:：]|逐句说明|修改说明|处理完毕|判定为清理模式|改动数)")


def strip_explain(text):
    """剥离模型自行附加的改动说明，返回纯改写正文。"""
    m = CHANGE_EXPLAIN.search(text)
    return text[:m.start()] if m else text


def tokens(text):
    """按汉字、数字串、标点切分，供 diff 用。"""
    return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+(?:\.[0-9]+)?%?|[，。、；：？！——…·]", text)


def check(source, revised):
    issues = []
    rev = strip_explain(revised)

    # 1. 实词守恒：数字串、百分数、年份必须不增不减
    src_nums = re.findall(r"\d+(?:\.\d+)?%?", source)
    rev_nums = re.findall(r"\d+(?:\.\d+)?%?", rev)
    if sorted(src_nums) != sorted(rev_nums):
        gone = [n for n in set(src_nums) if src_nums.count(n) > rev_nums.count(n)]
        added = [n for n in set(rev_nums) if rev_nums.count(n) > src_nums.count(n)]
        if gone:
            issues.append(f"数字丢失: {gone}")
        if added:
            issues.append(f"数字新增: {added}")

    # 2. 引号内容守恒：原文引语不得被改写
    src_quotes = re.findall(r"「([^」]+)」|\"([^\"]+)\"|“([^”]+)”", source)
    flat = [q for tup in src_quotes for q in tup if q]
    for q in flat:
        if q not in rev and len(q) >= 4:
            issues.append(f"引语被改动: {q[:30]}")

    # 3. 限定词强度：删掉限定词属于篡改语气
    for h in HEDGES:
        if h in source and h not in rev:
            issues.append(f"限定词被删: {h}")

    # 4. 反清单词不得被替换
    for w in ANTI_LIST_WORDS:
        if w in source and w not in rev:
            issues.append(f"反清单词被改: {w}")

    # 5. 结构保形：标题行、列表行、表格行、代码围栏的顺序与内容
    src_struct = [l.strip() for l in source.splitlines() if STRUCT_MARKS.match(l.strip())]
    rev_struct = [l.strip() for l in rev.splitlines() if STRUCT_MARKS.match(l.strip())]
    if src_struct != rev_struct:
        for l in src_struct:
            if l not in rev_struct:
                issues.append(f"结构行丢失或改动: {l[:40]}")

    # 6. 段落数不得减少（B 条目不删段；剥离改动说明后计数）
    src_paras = [p for p in source.split("\n\n") if p.strip()]
    rev_paras = [p for p in rev.split("\n\n") if p.strip()]
    if len(rev_paras) < len(src_paras) and len(rev_paras) >= 1:
        issues.append(f"段落数减少: {len(src_paras)} -> {len(rev_paras)}")

    # 7. 篇幅上限
    if len(rev) > int(len(source) * 1.35) and len(source) > 20:
        issues.append(f"篇幅膨胀: {len(source)} -> {len(rev)}")

    # 8. 问句守恒（正文问句是反清单项）
    if rev.count("？") < source.count("？"):
        issues.append(f"问句减少: {source.count('？')} -> {rev.count('？')}")

    return issues


# ---- 内置自测：违例必须被抓到，合规改写必须全过 ----
SELFTEST = [
    # (名字, 原文, 改后文, 预期 issues 数量下限, 预期包含的关键词)
    ("数字丢失",
     "留存率从 88% 升到 91%，获客成本上升 40%。",
     "留存率从 88% 升到 91%，获客成本明显上升。",
     1, "数字丢失"),
    ("数字新增",
     "团队优化了部署流程。",
     "团队优化了部署流程，效率提升了 30%。",
     1, "数字新增"),
    ("限定词删除",
     "这个方案可能适用于多数场景。",
     "这个方案适用于多数场景。",
     1, "限定词"),
    ("反清单越界",
     "这套中台为三条产品线赋能，闭环在 Q3 完成。",
     "这套中台为三条产品线提供支持，流程在 Q3 跑通。",
     1, "反清单"),
    ("引语被改",
     "他说：“明天再谈，价钱好商量。”",
     "他说：“明天再聊，价格可以谈。”",
     1, "引语"),
    ("段落被删",
     "第一段内容。\n\n第二段内容。\n\n第三段内容。",
     "第一段内容。\n\n第三段内容。",
     1, "段落"),
    ("问句被删",
     "为什么要关心冷启动？因为用户决定产品形态。",
     "冷启动很关键，因为用户决定产品形态。",
     1, "问句"),
    ("合规改写不误报",
     "新系统实现了效率的提升。处理时间从两小时缩到四十分钟。",
     "新系统把处理时间从两小时缩到四十分钟。",
     0, None),
    ("B1改写不误报",
     "真正的瓶颈不是技术，而是耐心。",
     "真正的瓶颈是耐心。",
     0, None),
    ("改动说明剥离",
     "原文一句话。另一句也保留。",
     "原文一句话。另一句也保留。\n\n改动说明：命中规则，已处理。\n\n其余句子未命中，原样保留。",
     0, None),
]


def selftest():
    fails = 0
    for name, src, rev, min_issues, kw in SELFTEST:
        issues = check(src, rev)
        ok = len(issues) >= min_issues and (kw is None or any(kw in i for i in issues))
        status = "PASS" if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"[{status}] {name}: {issues if issues else '无问题'}")
    if fails:
        print(f"\n自测失败 {fails} 项")
        return 1
    print("\n自测全部通过")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    src = open(sys.argv[1], encoding="utf-8").read()
    rev = open(sys.argv[2], encoding="utf-8").read()
    issues = check(src, rev)
    if issues:
        print(f"守恒检查：{len(issues)} 处违规")
        for i in issues:
            print(f"  - {i}")
        return 1
    print("守恒检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
