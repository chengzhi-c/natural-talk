#!/usr/bin/env python3
"""scan_slop.py - 极轻量文本 AI 塑料套路静态扫描工具 (纯 Python 标准库 / 零依赖)

用法:
    python scan_slop.py <文件路径>
    python scan_slop.py --self-test
    python scan_slop.py --json <文件路径>
"""

import sys
import re
import json
import argparse
from pathlib import Path

# 确保在 Windows 环境下标准输出使用 UTF-8 编码，防止特殊中文标点与字符引发 Unicode 编码异常
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 10 大塑料病灶正则规则
PATTERNS = [
    (
        "套路生理反应(仪表盘)",
        re.compile(
            r"瞳孔(?:微|骤|猛地?|剧烈)?(?:缩|收缩)(?![小短])|"
            r"(?:下颌|下颌线|下巴)(?:紧绷|咬得死紧|咬得死死的|收紧)|"
            r"喉结(?:微|上下|艰难地?)?滚(?:动)?|喉头(?:微|剧烈|上下)?(?:滚|动|滚动)|"
            r"指甲(?:深深)?掐[进入]|"
            r"倒[吸抽](?:了)?[一口]*(?:凉|冷)气|"
            r"(?:手指|指|骨)?(?:关节|节|骨节)(?:发|泛|捏得|捏得发)白|"
            r"呼吸(?:猛地|不由得|微微)?一?(?:滞|窒)|"
            r"(?:睫毛|眼睫)(?:微|轻轻一?)?颤(?:动)?|"
            r"心(?:跳|脏)(?:仿佛|猛地|瞬间)?(?:漏|漏跳)了一拍|"
            r"(?:后背|脊背)(?:猛地?一僵|渗出冷汗|冒出冷汗|渗出一层冷汗|一僵)"
        ),
        "建议：删除生理读数，替换为角色具体的行为取舍、视线移动或直接推进动作。"
    ),
    (
        "二元对举与变体翻案腔(不是A而是B)",
        re.compile(
            r"(?:(?:不是|非但不是|并未|并非|不只|不仅(?:仅)?是)[^，。；！？\n]{1,25}(?:[，,]?(?:而是|更不是|反倒是|反而是|更是|也(?:不|非)[^，。；！？\n]{1,15}(?:只是|而是))))|"
            r"(?:(?:不是|并未|并非)[^，。；！？\n]{1,20}[，,]?(?:也不是|也未)[^，。；！？\n]{1,20}[，,]?(?:只是|而是))|"
            r"(?:不[^，。；！？\n]{1,8}[，,]?不[^，。；！？\n]{1,8}[，,]?(?:而是|只是))|"
            r"(?:与其说[^。；！？\n]{1,25}不如说)|"
            r"(?:(?:表面(?:上|看似)?|看似)[^，。；！？\n]{1,25}(?:[，,]?(?:实则|实际上|背后却|骨子里|暗地里)))|"
            r"(?:不在于[^，。；！？\n]{1,25}[，,]?而在于)|"
            r"(?:谈不上[^，。；！？\n]{1,25}[，,]?更多(?:的)?是)"
        ),
        "建议：直接从正面给出判断或事实，避免虚立靶子再推翻，严禁多重否定折衷变体。"
    ),
    (
        "套路修辞与凝固感",
        re.compile(
            r"(?:眼(?:中|底|眸|眸深处|眸底)|眸(?:中|底|深处))(?:深处)?(?:闪过|掠过)一[丝抹道]|"
            r"空气(?:仿佛|骤然|在这一瞬间|像)*(?:凝固|静止)(?:了一般|了一样|了)?|"
            r"宛如鬼魅(?:一般)?|"
            r"寂静(?:仿佛)?有了重量|"
            r"(?:声音|尖叫声|警报声|轰鸣声|哭声)?填满(?:了整个|了整个?的?|了)?[^，。；！？\n]{0,10}(?:空间|房间|屋子|走廊|大厅|室内|车厢)|"
            r"时间仿佛停止了流动"
        ),
        "建议：删去套路词，直接描写环境的具体光影、声音或动作。"
    ),
    (
        "虚假升华与大词总结",
        re.compile(
            r"(?:(?:这不仅(?:仅)?是|这不只是|这何尝不是|这不仅关乎)[^。；！？\n]{0,35}|"
            r"(?:在?这一(?:刻|瞬间|刹那)|此时此刻)[，,]?(?:他|她|他们|她们|所有人)?[^，。；！？\n]{0,8}(?:终于|仿佛|才)?(?:彻底|深刻|深深地?)?(?:明白|领悟|读懂)了?|"
            r"领悟到了?)"
            r"[^。；！？\n]{0,25}"
            r"(?:人生|命运|时代|灵魂|人性|真谛|意义|救赎|较量|宿命|生命的重量)|"
            r"(?:一个从未被[^。；！？\n]{1,20}人[，,]?要用多少力气[^。；！？\n]{0,25})"
        ),
        "建议：删除脱离情节的大词升华与感悟金句，停留在人物最后的动作或场景物理余韵上。"
    ),
    (
        "叙述层破折号(后置补丁/揭晓)",
        re.compile(r"——(?:那就是|原来是|其实是|只是|唯一|这一刻|毫无疑问|全都是|那是|这不仅|专注|这[便就]是|离开[。！\s]?|宿命)"),
        "建议：严禁在旁白叙述中使用破折号制造刻意揭晓或后置设定补丁。改用常规标点自然融入主句；破折号限频每千字 ≤ 2 处。"
    ),
    (
        "装深沉时间感与程度回环(很久久到)",
        re.compile(
            r"(?:[久长]|很[久长]|多)[，,]?[久长多]到[^，。；！？\n]{0,20}|"
            r"(?:许多|很多|数|多|很久)年以?后[，,]?(?:他|她|他们|她们|所有人)?才会?明白|"
            r"不知道?过了多(?:久|长时间)|"
            r"(?:仿佛|像是|好像|宛如)过了(?:一个世纪|很久)|"
            r"时间在?(?:这一刻|此刻|此时)(?:彻底)?失去了意义"
        ),
        "建议：交代具体的时间点（两分钟后、雨停时）或推进客观动作，严禁‘很久，久到’同词回环。"
    ),
    (
        "上帝视角全知剧透(你不知道的是)",
        re.compile(
            r"(?:你|他|她|他们)不知道的是|"
            r"多年以后(?:他|她|他们)?才会(?:明白|知道|懂得)|"
            r"此时的(?:他|她|他们)?尚且不知"
        ),
        "建议：镜头严格锁定在视点人物此刻可见可感的半径内，严禁全知剧透。"
    ),
    (
        "推测性心理翻译垫词(像是想/像是在)",
        re.compile(
            r"像(?:是想|是在|是怕|没来得及|被烫着了似的|想|怕)[^，。；！？\n]{0,10}"
        ),
        "建议：删除‘像是在……’、‘像是想……’等作者下场推测性翻译，改写具体的物理微动或视线停留。"
    ),
    (
        "情绪直接贴标签",
        re.compile(
            r"(?:一股|一种|一阵)(?:莫名|强烈|无法言喻|前所未有|难以名状|难以抑制)的?[^，。；！？\n]{0,8}(?:涌上|袭来|蔓延|攥住|包裹|苦涩)|"
            r"心(?:脏)?像被(?:一只(?:无形|冰冷)?的?大手)?(?:狠狠)?[拧攥揪]|"
            r"(?:感到|涌起|心底泛起)(?:一阵)?深深的无力(?:感)?|"
            r"深深的无力感"
        ),
        "建议：通过动作阻碍与视线停留展现，不直接给情绪下诊断。"
    ),
    (
        "客服套话与模板结语",
        re.compile(
            r"这是一个(?:非常|很)?(?:好|棒|绝佳)的问题|"
            r"希望(?:这个回答|这些建议|以上内容|以上解答|上述分析)?对(?:您|你)(?:有所)?(?:帮助|启发)|"
            r"如(?:您|你)所(?:愿|见)|"
            r"当然可以[，。！]|"
            r"很高兴为(?:您|你)(?:解答|服务)?|"
            r"如果(?:您|你)还有(?:其他)?(?:问题|疑问)[，,]欢迎|"
            r"欢迎随时(?:向我)?提问"
        ),
        "建议：第一句直奔主题，说完即停，坚决删除客套废话。"
    ),
]

METAPHOR_PATTERN = re.compile(r"(?<![画图影雕头像成不很更极其真])(?:像|仿佛|宛如|犹如|恰似)(?![素样棋子机皮素生像])|似的")

def clean_dialogue_quotes(text: str) -> str:
    """隔离角色台词（引号内的发言），确保叙述层红线规则只对旁白与叙述伴随标签生效，不误杀角色人设口语。"""
    return re.sub(r'“[^”]*”|"[^"]*"|「[^」]*」|『[^』]*』|‘[^’]*’', ' ', text)

def scan_text(text: str) -> list[tuple[int, str, str, str]]:
    """扫描文本，返回 [(行号, 命中规则名, 匹配片段, 修复建议)]"""
    results = []
    in_code_block = False
    narration_for_density = []
    
    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        
        # 多行代码块状态维护（过滤单行闭合代码块）
        if stripped.startswith("```"):
            if stripped.count("```") >= 2 and len(stripped) >= 6:
                continue
            in_code_block = not in_code_block
            continue
            
        if in_code_block:
            continue
            
        if not stripped or stripped.startswith("#"):
            continue
            
        # 移除行内代码
        line_no_code = re.sub(r'`[^`]+`', ' ', line)
        
        # 针对叙述规则隔离台词引号
        line_narration = clean_dialogue_quotes(line_no_code)
        narration_for_density.append(line_narration)
        
        for name, pattern, fix in PATTERNS:
            # 客服套话检测整行；旁白与叙述病灶检测去台词后的叙述语
            target_line = line_no_code if "客服套话" in name else line_narration
            if not target_line.strip():
                continue
            for match in pattern.finditer(target_line):
                matched_str = match.group(0)
                if matched_str:
                    results.append((idx, name, matched_str, fix))

    # 全局指标检测 (针对长文本旁白)
    full_narration = "\n".join(narration_for_density)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', full_narration))
    if chinese_chars >= 300:
        # 1. 显式比喻密度检测 (限频 2.5~3.0 处/千字)
        metaphor_matches = list(METAPHOR_PATTERN.finditer(full_narration))
        metaphor_count = len(metaphor_matches)
        density = (metaphor_count / chinese_chars) * 1000
        if density > 3.0:
            snippets = []
            for m in metaphor_matches[:3]:
                s = max(0, m.start() - 6)
                e = min(len(full_narration), m.end() + 8)
                snippets.append(full_narration[s:e].strip().replace("\n", " "))
            sample_str = "；".join(f"“{sn}”" for sn in snippets)
            results.append((
                0,
                "显式比喻密度严重超标",
                f"实测密度 {density:.1f} 处/千字 (全篇共 {metaphor_count} 处，上限 2.5~3.0 处/千字，如：{sample_str})",
                "建议：删除冗余挂件式明喻，改用空间距离位移、物理阻力、温度触感与动作停顿直接推进。"
            ))

        # 2. 叙述层破折号密度检测 (限频 ≤ 2.0 处/千字)
        all_dashes = len(re.findall(r"——|—", full_narration))
        dash_density = (all_dashes / chinese_chars) * 1000
        if dash_density > 2.0:
            results.append((
                0,
                "叙述层破折号密度超标",
                f"实测密度 {dash_density:.1f} 处/千字 (全篇共 {all_dashes} 处，上限 2.0 处/千字)",
                "建议：旁白叙述破折号每千字不超过 2 处，改用常规标点或独立短句自然推进。"
            ))

    return results

def run_self_test() -> int:
    """运行自测套件，全面覆盖 10 大 AI 塑料套路病灶、常见变体、代码块及台词隔离机制。"""
    test_sample = """
    在这个时代背景下，真正的救赎不是向外索取，也不是逃避，只是向内扎根。不引导，不干涉，而是等待时机。
    看到满地狼藉，众人不禁倒吸了一口凉气，他的瞳孔剧烈收缩，喉结上下滚动，指骨节泛白，心脏猛地漏跳了一拍。
    空气仿佛在这一瞬间凝固了，寂静有了重量，她的眼眸深处闪过一抹淡淡的哀伤，尖叫声填满了整个大厅。
    这不仅关乎这场官司的输赢，更关乎整座城市千万人未来的命运。在这一刻，他终于彻底明白了生命的真谛。
    他停下了脚步——那是对未知的恐惧。
    许多年以后，他们才会明白当初的选择有多沉重。他看了很久，久到连呼吸都凝固了。
    你不知道的是，背后的门已经关上了。
    他站在那里，像是在等待什么指令，又像是怕打破这片安静。
    一种前所未有的恐慌瞬间涌上心头，心脏像被一只无形的大手狠狠攥住，心底泛起一阵深深的无力感。
    这是一个很棒的问题！希望以上解答对您有所帮助！如您所见，配置已生效。
    ```python
    # 多行代码块内部豁免测试
    # 不是A而是B
    # 瞳孔骤缩
    print("希望这个回答对您有所帮助！")
    ```
    ```x = 1 # 单行闭合代码块豁免：瞳孔骤缩```
    “这不是钱的问题，也不是原则问题，只是公道。”老张说道。
    “——就今晚。”她低声说。
    老李说：‘这也是原则问题，谈不上喜欢，更多的是责任。’接着喝了口茶。
    医生用手电筒照射患者眼部，检查发现患者瞳孔缩小，对光反射正常。
    分库分表的设计方案，就像把一根大木头沿着年轮自然纹理劈开一样清晰。
    """
    findings = scan_text(test_sample)
    print(f"Self-test found {len(findings)} slop hits:")
    hit_patterns = set()
    for line_no, name, match, fix in findings:
        hit_patterns.add(name)
        print(f"  Line {line_no:2d} | [{name}] -> \"{match}\"")
        
    all_10_patterns = [p[0] for p in PATTERNS]
    missing = [p for p in all_10_patterns if p not in hit_patterns]
    
    # 验证单行代码块后多行解析未失效
    single_line_code_test = '```x = 1```\n他的瞳孔骤缩，喉结上下滚动。\n```python\n# 瞳孔骤缩\n```'
    sl_findings = scan_text(single_line_code_test)
    if len(sl_findings) != 2:
        print(f"\nFAIL: Single-line code fence isolation regression! Expected 2 hits, got {len(sl_findings)}")
        return 1
        
    # 验证单/双引号台词隔离（台词内破折号与翻案腔豁免）
    dialogue_isolation_test = "老李在雨里喊：“——快走！这不是演习，也不是开玩笑，只是命令！”然后转身跑了。"
    dlg_findings = scan_text(dialogue_isolation_test)
    if len(dlg_findings) != 0:
        print(f"\nFAIL: Dialogue isolation regression! Expected 0 hits, got {len(dlg_findings)}: {dlg_findings}")
        return 1
        
    # 验证医学与功能比喻不变性放行
    invariant_test = "检查发现，患者瞳孔缩小，对光反射迟钝。"
    inv_findings = scan_text(invariant_test)
    if len(inv_findings) != 0:
        print(f"\nFAIL: Invariant false alarm regression! Expected 0 hits, got {len(inv_findings)}")
        return 1
        
    if len(missing) == 0 and len(findings) >= 10:
        print(f"\nPASS: Self-test covered all {len(all_10_patterns)} major AI-slop patterns and all syntax invariants successfully!")
        return 0
    else:
        print(f"\nFAIL: Missing coverage for patterns: {missing}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="扫描文本中的 AI 塑料套路")
    parser.add_argument("file", nargs="?", help="待扫描的 Markdown / 文本文件路径")
    parser.add_argument("--self-test", action="store_true", help="运行自检程序")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出扫描结果")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(run_self_test())

    if not args.file:
        parser.print_help()
        sys.exit(1)

    path = Path(args.file)
    if not path.exists():
        print(f"错误: 文件不存在 -> {path}", file=sys.stderr)
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    findings = scan_text(text)

    if args.json:
        output_data = {
            "file": str(path),
            "total_hits": len(findings),
            "findings": [
                {
                    "line": line_no,
                    "pattern": name,
                    "matched": match,
                    "suggestion": fix
                }
                for line_no, name, match, fix in findings
            ]
        }
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
        sys.exit(0 if len(findings) == 0 else 1)

    if not findings:
        print(f"🟢 扫描完成 [{path.name}]：未发现明显的 AI 塑料套路！")
        sys.exit(0)

    print(f"⚠️  在 [{path.name}] 中发现 {len(findings)} 处疑似 AI 塑料套路：\n")
    for line_no, name, match, fix in findings:
        prefix = f"第 {line_no} 行 | " if line_no > 0 else "全局指标 | "
        print(f"  • {prefix}【{name}】 命中: \"{match}\"")
        print(f"    ↳ {fix}\n")
    sys.exit(1)

if __name__ == "__main__":
    main()
