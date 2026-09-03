#!/usr/bin/env python3
"""Deterministic Offline Behavioral Regression Test for Natural-Talk.

Zero-API cost, runs in milliseconds.
- Validates 0 False Positives on Human Literary & Daily Dialogue Samples (22 Invariant Cases).
- Validates 100% True Positive Detection across 8 Major AI Slop Patterns (57 Adversarial Mutation Cases).
- Validates Grammar Context Isolation (Single-line & Multi-line Code Fences, Dialogue Quotes Sovereignty).
"""

import os
import re
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Import scan_text from scan_slop
sys.path.insert(0, str(Path(__file__).parent))
from scan_slop import scan_text, PATTERNS

# 1. 22 Clean Invariant & Boundary Cases (Must PASS with 0 violations)
INVARIANT_SAMPLES = [
    ("HUMAN_01_自然日常对话", "“你昨晚去哪了？”“在老王家打牌，怎么了？”“没事，钥匙落在茶几上了。”"),
    ("HUMAN_02_台词内部包含对举", "老张敲了敲桌子：“这不是钱的问题，而是规矩问题！懂吗？”"),
    ("HUMAN_03_台词内部包含升华大词", "老和尚合十道：“这何尝不是一种修行？施主着相了。”"),
    ("HUMAN_04_正常转折否定句", "他不是本地人，但他对城里的每条胡同都了如指掌。"),
    ("HUMAN_05_心理否定非对举", "这不是真的，他一遍遍对自己说，这绝不可能是真的。"),
    ("HUMAN_06_物理动作描写", "他转过身，从抽屉里拿出一盒火柴，划燃一根点上了烟。"),
    ("HUMAN_07_环境光影声响", "早晨的雾气还没散，远处的钟楼传来六下沉闷的敲击声。"),
    ("HUMAN_08_医学与生理事实陈述", "医生用手电筒照射患者的眼部，观察瞳孔反射与对光收缩情况。"),
    ("HUMAN_09_正常破折号补充说明", "背包里装着三样必备工具——军刀、手电筒和一卷尼龙绳。"),
    ("HUMAN_10_文章引用题记破折号", "——1935年秋，写于上海寓所。"),
    ("HUMAN_11_具体时间交代", "过了大约十分钟，楼梯上传来急促的脚步声。"),
    ("HUMAN_12_时间年限陈述", "三年后，他从北方调回省城，任职于规划局。"),
    ("HUMAN_13_身体疲劳客观描述", "跑完五公里后，他感到双腿酸痛无力，坐在草地上大口喘气。"),
    ("HUMAN_14_功能性技术比喻", "分库分表的设计方案，就像把一根大木头沿着年轮自然纹理劈开一样清晰。"),
    ("HUMAN_15_直接业务回答", "优化方案包含两步：首先增加复合索引，其次在应用层开启二级缓存。"),
    ("SYNTAX_01_多行代码块注释", "```python\n# 不是A而是B\n# 瞳孔骤缩\nprint(\"希望对您有所帮助\")\n```"),
    ("SYNTAX_02_单行代码块隔离", "```x = 1 # 瞳孔骤缩```\n这里是正常正文，没有套路。"),
    ("SYNTAX_03_行内代码包裹", "在 Python 中，使用 `if not a: return b` 可以避免复杂的逻辑嵌套。"),
    ("SYNTAX_04_Markdown标题行", "# 第一章：这不仅是一场考验"),
    ("SYNTAX_05_多引号台词混合", "『这不是我的主意，』她低声道，“是王总亲自定下的。”"),
    ("SYNTAX_06_单引号台词隔离", "老李转述道：‘这不是钱的问题，而是规矩问题。’接着喝了口茶。"),
    ("SYNTAX_07_纯台词对话段落", "“空气凝固了？”“没有啊，挺凉快的。”“那你为什么不说话？”“我在想事情。”"),
]

# 2. 57 Adversarial AI Slop Fixtures (Must FAIL by triggering detection across all 8 patterns)
AI_SLOP_SAMPLES = [
    # --- Pattern 1: 套路生理反应 (10 cases) ---
    ("P1_01_副词修饰瞳孔", "在听到枪声的瞬间，他的瞳孔微缩，死死盯住门口。"),
    ("P1_02_下颌紧绷成线", "老李一言不发，下颌紧绷，拳头在桌下慢慢攥紧。"),
    ("P1_03_喉结滚动变体", "他喉结上下滚动，咽下喉头翻涌的苦涩。"),
    ("P1_04_倒吸凉气带了", "看到满地狼藉，众人不禁倒吸了一口凉气。"),
    ("P1_05_倒吸冷气带了", "他倒吸了一口冷气，退后两步。"),
    ("P1_06_瞳孔剧烈收缩", "强光照来，他的瞳孔剧烈收缩。"),
    ("P1_07_脊背一僵", "听到脚步声，他的脊背猛地一僵。"),
    ("P1_08_心脏猛漏一拍", "那一瞬间，她的心脏猛地漏跳了一拍。"),
    ("P1_09_指节捏得发白", "他死死攥着信封，指骨节泛白，指节捏得发白。"),
    ("P1_10_台词伴随叙述语", "“给我闭嘴！”他眼睫微颤、喉头滚动地低声咆哮。"),

    # --- Pattern 2: 二元对举翻案腔 (8 cases) ---
    ("P2_01_长从句与其说不如说", "这与其说是理性的审慎抉择，不如说是源于骨子里的恐惧。"),
    ("P2_02_表面看似实则", "表面看似风平浪静，实则各方势力早已磨刀霍霍。"),
    ("P2_03_不仅是更是变体", "这不仅仅是一次代码重构，更是对整个架构哲学的反思。"),
    ("P2_04_不只是更是", "这不只是技术升级，更是整个团队工作方式的革新。"),
    ("P2_05_不在于而在于", "真正的胜负不在于招式有多华丽，而在于能否一击毙命。"),
    ("P2_06_谈不上更多是", "他谈不上有多么同情对方，更多是一种唇亡齿寒的兔死狐悲。"),
    ("P2_07_谈不上更多的是", "他谈不上喜欢画画，更多的是为了打发无聊的时间。"),
    ("P2_08_表面看似骨子里", "他表面看似玩世不恭，骨子里却极有原则。"),

    # --- Pattern 3: 套路修辞与凝固感 (7 cases) ---
    ("P3_01_眼底掠过暗芒", "她眼底掠过一抹决绝的冷意，随即抽出了短刀。"),
    ("P3_02_眼眸深处闪过一抹", "她的眼眸深处闪过一抹淡淡的哀伤。"),
    ("P3_03_空气骤然凝固", "话音刚落，包厢里的空气仿佛在这一瞬间凝固了。"),
    ("P3_04_空气仿佛凝固一般", "空气仿佛凝固了一般沉重。"),
    ("P3_05_声音填满空间", "刺耳的防空警报声音填满了整个走廊，令人窒息。"),
    ("P3_06_声音填满大厅", "尖叫声填满了整个大厅。"),
    ("P3_07_宛如鬼魅一般", "黑衣人宛如鬼魅一般出现在屋顶，悄无声息。"),

    # --- Pattern 4: 虚假升华与大词 (8 cases) ---
    ("P4_01_这何尝不是救赎", "望着远去的绿皮火车，这何尝不是一种迟来的救赎？"),
    ("P4_02_这一刻明白了真谛", "在这一刻，他终于彻底明白了生命的真谛与宿命的沉重。"),
    ("P4_03_领悟到灵魂重量", "历经沧桑之后，他领悟到了时代的意义与人性的较量。"),
    ("P4_04_不仅关乎更关乎灵魂", "这不仅关乎个人恩怨，更关乎整座城池千万灵魂的归宿。"),
    ("P4_05_跨逗号升华大词", "这不仅关乎这场官司的输赢，更关乎整座城市千万人未来的命运。"),
    ("P4_06_在这一刻彻底明白了", "在这一刻，他终于彻底明白了生命的真谛。"),
    ("P4_07_这一瞬间他领悟到", "在这一瞬间，他仿佛领悟到了人性的深邃与复杂。"),
    ("P4_08_这不仅是一场较量", "这不仅是一场技术层面的较量，更是一次关于时代命运的抉择。"),

    # --- Pattern 5: 揭晓式破折号 (5 cases) ---
    ("P5_01_破折号那就是真相", "历经千辛万苦，他终于找到了唯一的线索——那就是真相。"),
    ("P5_02_他做出了选择离开", "站在十字路口，他做出了一个选择——离开。"),
    ("P5_03_破折号宿命", "等待着所有叛徒的结局——这便是宿命！"),
    ("P5_04_破折号那是真相", "他费尽心机追寻的结果——那是真相。"),
    ("P5_05_破折号这就是宿命", "所有抗争的终点——这就是宿命。"),

    # --- Pattern 6: 装深沉时间感 (7 cases) ---
    ("P6_01_许多年以后明白", "数年以后他才会明白，当年父亲转身离开时的沉默。"),
    ("P6_02_许多年以后他们明白", "许多年以后，他们才会明白当初的选择有多沉重。"),
    ("P6_03_不知道过了多久", "不知道过了多久，窗外的雨渐渐停了，东方泛起鱼肚白。"),
    ("P6_04_仿佛过了一个世纪", "四目相对的瞬间，仿佛过了一个世纪那么漫长。"),
    ("P6_05_好像过了一个世纪", "等待结果的几分钟，好像过了一个世纪。"),
    ("P6_06_时间失去意义", "在震耳欲聋的轰鸣中，时间在这一刻彻底失去了意义。"),
    ("P6_07_时间在此刻失去意义", "在爆炸声中，时间在此刻失去了意义。"),

    # --- Pattern 7: 情绪直接贴标签 (6 cases) ---
    ("P7_01_莫名前所未有涌上", "一种前所未有的恐慌瞬间涌上心头，令他手足无措。"),
    ("P7_02_心像被大手攥住", "听到遗嘱的刹那，他的心像被一只大手狠狠攥住。"),
    ("P7_03_无形大手攥住", "心脏像被一只无形的大手狠狠攥住。"),
    ("P7_04_感到深深的无力", "看着病床上的老人，他感到深深的无力感。"),
    ("P7_05_难以名状悲凉袭来", "一种难以名状的悲凉悄然袭来。"),
    ("P7_06_深深的无力感涌起", "心底泛起一阵深深的无力感。"),

    # --- Pattern 8: 客服套话与模板结语 (6 cases) ---
    ("P8_01_这是一个非常好的问题", "这是一个非常好的问题！让我们从三个维度进行深入剖析："),
    ("P8_02_希望对您有所帮助", "以上就是本次方案的全部内容，希望这些建议对您有所帮助！"),
    ("P8_03_如果您还有其他问题欢迎", "如果您还有其他问题，欢迎随时向我提问！"),
    ("P8_04_希望以上解答有所帮助", "希望以上解答对您有所帮助！"),
    ("P8_05_这是一个很棒的问题", "这是一个很棒的问题！"),
    ("P8_06_如您所见", "如您所见，上述配置已经成功生效。"),
]

def run_regression_tests() -> bool:
    t0 = time.time()
    print("==================================================", flush=True)
    print("   Natural-Talk Local Offline Regression Test    ", flush=True)
    print("==================================================\n", flush=True)
    
    # Step 1: Check False Positives on Human & Invariant Samples (22 cases)
    print("--- [Test Suite 1: Human Baseline & Syntax Invariants (Zero False Positives)] ---")
    fp_count = 0
    for name, text in INVARIANT_SAMPLES:
        findings = scan_text(text)
        if findings:
            print(f"  ❌ FAIL (False Positive) [{name}]:")
            for line_no, p_name, match, fix in findings:
                print(f"     Line {line_no} [{p_name}] -> \"{match}\"")
            fp_count += 1
        else:
            print(f"  🟢 PASS [{name}]")
            
    # Step 2: Check True Positives on Adversarial Mutation Slop Samples (57 cases)
    print("\n--- [Test Suite 2: AI Slop Benchmark (100% Detection Rate across 8 Patterns)] ---")
    fn_count = 0
    for name, text in AI_SLOP_SAMPLES:
        findings = scan_text(text)
        if not findings:
            print(f"  ❌ FAIL (False Negative - Escaped) [{name}]: \"{text}\"")
            fn_count += 1
        else:
            hit_str = ", ".join([f"{n}: \"{m}\"" for _, n, m, _ in findings])
            print(f"  🟢 CAUGHT [{name}]: {hit_str}")
            
    t1 = time.time()
    elapsed_ms = round((t1 - t0) * 1000, 2)
    print("\n==================================================")
    print(f"Regression Result: {len(INVARIANT_SAMPLES) - fp_count}/{len(INVARIANT_SAMPLES)} Invariant Passed | {len(AI_SLOP_SAMPLES) - fn_count}/{len(AI_SLOP_SAMPLES)} AI Slop Caught")
    print(f"Execution Time: {elapsed_ms} ms (Zero API Cost)")
    print("==================================================\n")
    
    if fp_count == 0 and fn_count == 0:
        print("✅ ALL LOCAL REGRESSION TESTS (22 INVARIANTS + 57 ADVERSARIAL CASES) PASSED CLEANLY!\n")
        return True
    else:
        print(f"❌ REGRESSION FAILED! ({fp_count} false alarms, {fn_count} slop escapes)\n")
        return False

if __name__ == "__main__":
    if not run_regression_tests():
        sys.exit(1)
