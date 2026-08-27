# -*- coding: utf-8 -*-
"""fiction 红线字面项检查：只测 SKILL.md Fiction 章里能用正则定位的红线。

测不了的（必须人工读，本脚本不假装覆盖）：
  - 比喻质地（喻体是否可见、是否换属性）
  - 纯景段长度、景物是否被人物动作打断
  - 事实推演 vs 价值说教的边界
  - 角色语汇是否符合身份
正则能测的都是"套路模板"类：字面固定，模型爱用，人类罕用。

用法：
    python scripts/check-fiction-redline.py <文本.md>
    python scripts/check-fiction-redline.py --selftest
"""
import re
import sys

# (红线名, 正则, 豁免说明)
REDLINES = [
    ("套路化情绪特征",
     r"眼中闪过一丝|眼底闪过一丝|眸中闪过|闪过一丝[^，。]{0,6}(?:情绪|异样|慌乱|惊恐|笑意)",
     "改成具体动作或对白停顿"),
    ("空气凝固模板",
     r"空气(?:仿佛|似乎|瞬间)?凝固|时间(?:仿佛|似乎)?静止",
     "删掉，写此刻真实的动作"),
    ("不是A只有B",
     r"没有[^，。！？\n]{1,12}，只有[^，。！？\n]{1,12}",
     "直接写 B，不立 A"),
    ("伪高级生理反应",
     r"瞳孔(?:收缩|骤缩|紧缩)|指甲掐进(?:掌心|肉里)|喉结(?:上下)?滚动|指尖(?:泛白|掐进)",
     "换微小物理动作"),
    ("玄虚打斗修辞",
     r"宛如鬼魅|撕裂虚空|弥漫着?(?:令人窒息的)?威压|气劲纵横|空间涟漪",
     "写受力的物理后果"),
    ("上帝视角剧透-不知道",
     r"他不知道的是|她不知道的是|他们(?:都)?不知道的是",
     "删掉，让读者和角色同速"),
    ("上帝视角剧透-多年以后",
     r"多年(?:以后|之后)(?:他|她|他们|才会|才会明白|会明白)",
     "删掉，不预支结局"),
    ("作者外部总结-终于明白",
     r"(?:他|她|他们)(?:终于|这才|恍然|顿时)(?:明白|领悟|意识到|懂得)",
     "这是作者盖章，改成动作"),
    ("作者外部总结-意识到",
     r"(?:他|她)(?:忽然|突然|瞬间)?意识到",
     "同上"),
    ("翻案腔-叙述中",
     r"(?:不是|并非|不是[^，。！？\n]{0,16}，?)[^，。！？\n]{0,16}(?:而是|而是说)",
     "叙述内不写对举，删否定留肯定"),
    ("提示语-值得一提",
     r"值得一提的(?:是)?|简单来说|说白了|换句话说",
     "叙述里不写讲义腔提示语"),
]

# 引号内豁免：角色台词不受风格规则约束（SKILL.md Fiction 章豁免条款）
DIALOGUE = re.compile(r"「[^」]*」|“[^”]*”|\"[^\"]*\"")


def strip_dialogue(text):
    return DIALOGUE.sub("", text)


def check(text):
    issues = []
    body = strip_dialogue(text)
    for name, pat, fix in REDLINES:
        for m in re.finditer(pat, body):
            ctx_start = max(0, m.start() - 10)
            ctx = body[ctx_start:m.end() + 10].replace("\n", " ")
            issues.append(f"{name}: …{ctx}… → {fix}")
    return issues


# ---- 自测：违例必抓，合法写法不误报 ----
SELFTEST_VIOLATIONS = [
    "她眼中闪过一丝慌乱，随即恢复平静。",
    "空气仿佛凝固了，谁都没说话。",
    "这里没有退路，只有死战。",
    "他瞳孔收缩，意识到大事不好。",
    "那道身影宛如鬼魅，撕裂虚空而来，周身弥漫着令人窒息的威压。",
    "他不知道的是，此刻门后已经站了三个人。",
    "多年以后他才会明白，这个决定改变了一切。",
    "他终于明白了，她一直在等他开口。",
    "她顿时领悟到，真正重要的东西早已失去。",
    "这条路不是通往自由，而是通往更深的牢笼。",
    "值得一提的是，那晚的雨下得很大。",
]

SELFTEST_LEGAL = [
    "她把杯子放下，杯底磕在桌面上，很响。",  # 动作
    "他说：“我不是不去，是不想去。”",  # 台词内翻案腔，豁免
    "“说白了，你就是怕。”她笑着补了一句。",  # 台词内提示语，豁免
    "她盯着那扇门，看了很久。",  # 平静叙述
    "多年以后，他再想起那个下午，只记得蝉声很吵。",  # 闪回开头？"多年以后他才会明白"才触发
]


def selftest():
    fails = 0
    caught = 0
    for s in SELFTEST_VIOLATIONS:
        issues = check(s)
        if issues:
            caught += 1
        else:
            fails += 1
            print(f"[FAIL-漏报] {s}")
    print(f"违例抓到 {caught}/{len(SELFTEST_VIOLATIONS)}")

    for s in SELFTEST_LEGAL:
        issues = check(s)
        if issues:
            fails += 1
            print(f"[FAIL-误报] {s} -> {issues}")

    if fails:
        print(f"\n自测失败 {fails} 项")
        return 1
    print("自测全部通过（含台词豁免）")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    issues = check(text)
    if issues:
        print(f"fiction 红线：{len(issues)} 处命中")
        for i in issues:
            print(f"  - {i}")
        return 1
    print("fiction 红线字面项：无命中（比喻质地、纯景段仍需人工读）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
