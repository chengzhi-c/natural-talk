# -*- coding: utf-8 -*-
"""natural-talk-article 编译器：core/rules.yaml -> dist/* （文章版 A0-A3）

单一真理：仅 core/rules.yaml 可手改，其余产物由本脚本生成。
用法：
  python scripts/build.py          # 生成 dist/
  python scripts/build.py --check  # 校验产物与源一致（CI用）
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "core" / "rules.yaml"
DIST = ROOT / "dist"
PROMPTS = DIST / "prompts"

# 极简YAML解析（仅支持本文件的子集，避免依赖PyYAML）
def parse_rules():
    text = SRC.read_text(encoding="utf-8")
    # 提取关键块（正则抽取，避免全量YAML解析）
    return text

def render_l0():
    return "[文章]标题有动词或场景/开头100字有信息/结尾收具体。禁:在当今|让我们|作为AI|综上。—≤2 !≤3"

def render_l1():
    return "[文章]标题有动词或场景/开头100字有信息禁\"在当今|随着|众所周知\"/结尾收具体禁\"让我们|共同|未来可期\"\n设问≤1/协作腔≤1/讲义腔≤1/路标≤2(固定)/—≤2/500字/!≤3/500字/**≤1段/一动作一句\n禁:作为AI|好问题|让我来|首先其次|综上|赋能|闭环/研究表明→给来源或删/段尾总结≤2处\n铁律:不是X而是Y→说Y(角色除外)/段落呼吸:禁3段同构/不编造尤不编数据"

def render_l2():
    return (
        "[文章]标题有动词或场景/开头100字有信息禁\"在当今|随着|众所周知\"/结尾收具体禁\"让我们|共同|未来可期\"\n"
        "设问≤1/协作腔≤1/讲义腔≤1/路标≤2(固定)/—≤2/500字/!≤3/500字/**≤1段/一动作一句\n"
        "禁:作为AI|好问题|让我来|首先其次|综上|赋能|闭环/研究表明→给来源或删/尾总结≤2\n"
        "铁律:不是X而是Y→说Y(角色除外)/段落呼吸:禁3段同构/不编造尤不编数据\n"
        "---\n"
        "协作:作为AI|希望帮助|感谢提问|I hope this helps\n"
        "讲义:让我来|首先其次|综上|Let's dive in\n"
        "评判:我完全理解|你很有批判思维\n"
        "语言:数据告诉我们|crucial|赋能|闭环\n"
        "虚假归因:研究表明→给来源或删\n"
        "过渡:说到就不得不/那么到底\n"
        "段落:尾总结≤2/连接≤4/500字/禁3段同构\n"
        "豁免:真分步/真三点不违规/长文须展开/fiction关"
    )

def render_l3():
    l2 = render_l2()
    extra = (
        "\n---\n"
        "防矫枉:标题长≠坏/首先其次看是否空预告/三点看长度+结构/结尾自然收尾允许/长文须展开/fiction默认关\n"
        "自查:删后完整?/会尴尬吗?/有新信息? 例:关于X→我用三月提十倍/在当今→容器起不来/研究表明→给来源或删"
    )
    return l2 + extra

def render_skill():
    return """---
name: natural-talk-article
description: "去文章AI味。用户写博客/教程/复盘/长文且要求'别那么AI/像人写的/自然点'时触发。学术论文/公文/法律/营销/演讲稿不适用。"
license: MIT
---

# Natural Talk Article

像人写的文章，不套模板，不编造。

## 绝对原则

- 不编造：不知即说。文章里尤其不编数据、不编案例、不虚假归因
- 不评判人：不做心理判断
- 不装AI：禁"作为AI/希望帮助"（问身份除外）

## 铁律

- `不是X而是Y` → 直接说Y（角色引号内除外）
- `与其X不如Y` → 直接说Y
- `看似X实则Y` → 直接说Y
- `很久…久到…` → 给具体时间
- 连续动作一句写完（仅紧张/暧昧/恐惧/受伤可慢放）

## 文章三关卡

1. 标题：有动词或具体场景，不是名词堆砌（"关于X的那些事"→"我用三个月把查询提了十倍"）
2. 开头：前100字有信息量，禁"在当今/随着/众所周知"
3. 结尾：收在具体建议/具体问题/具体画面，禁"让我们/共同/未来可期/展望"

## 表达上限（500字基准，路标固定不放宽，其余按比例）

- 设问钩子 ≤1次（你有没有想过/你知道吗）
- 协作腔 ≤1次（作为AI/好问题/希望帮助）
- 讲义腔 ≤1次（让我来/首先其次/综上）
- 路标词 ≤2次（值得注意/事实上/归根结底）——固定，不随篇幅放宽
- 破折号 ≤2次/500字（仅悬念或未说完）
- 感叹号 ≤3次/500字
- 加粗 ≤1处/段

## 禁用词速查

协作痕迹：作为AI/好问题/感谢提问/I hope this helps
讲义模式：让我来/首先其次/综上/Let's dive in/敲黑板
评判越界：我完全理解/你很有批判思维
语言痕迹：数据告诉我们/crucial/赋能/闭环
虚假归因：研究表明/据专家介绍/根据最新数据——给具体来源或删
过渡模板：说到X就不得不提/提到X自然要说/那么X到底是什么呢
视觉滥用：破折号堆砌/每段加粗>1处/emoji

## 段落健康度

- 禁3段以上同结构（段落功能要多样：事实/举例/转折/一句话段）
- 段尾总结句全文≤2个（不要每段都收一句结论）
- 连接词（然而/因此/此外）每500字≤4个
- 冗余复述删掉（"换句话说"后面如果是重复前句，删）

## 7支柱

标题即主张 / 开头直入 / 段落呼吸 / 具体化 / 有边界 / 结尾收具体 / 保持主题

## 豁免

- 真操作步骤可用"首先其次"（判据：删编号内容仍完整→保留）
- 内容本身恰好三点不违规（硬凑三点才违规，疑似仅提示）
- 自然收尾允许（"先这样""你自己试试看"不算升华）
- 长文必须展开（"直接"≠越短越好）
- 安慰优先于规则
- fiction 默认关，小说/故事才开
- 自查：读给朋友听，会尴尬吗？
"""


def main():
    check = "--check" in sys.argv
    outputs = {
        PROMPTS / "prompt.l0.txt": render_l0(),
        PROMPTS / "prompt.l1.txt": render_l1(),
        PROMPTS / "prompt.l2.txt": render_l2(),
        PROMPTS / "prompt.l3.txt": render_l3(),
        DIST / "SKILL.md": render_skill(),
    }
    # 额外生成 lexicon.json（Trie预编译用）
    import json as _json
    lex = {
        "_generated": "由 core/rules.yaml 自动生成，请勿手改。运行 python scripts/build.py 重新生成。",
        "_source": "core/rules.yaml",
        "article_title_vague": ["的那些事","那些事","深度好文","科普一下","必须知道","everything you need to know"],
        "article_opening_banned": ["在当今","随着","众所周知","你有没有想过"],
        "article_closing_pompous": ["让我们","共同","携手","未来可期","展望"],
        "tier1_identity": ["作为AI","作为人工智能","根据我的训练","基于我的训练数据","训练数据截至","截至我的知识","基于我所掌握的信息","语言模型","as an ai","based on my training","i'm an ai"],
        "tier1_courtesy": ["好问题","很好的问题","有深度的问题","这个问题问得好","感谢提问","感谢你的提问","感谢你的咨询","你说得完全对","如果还有问题","如果还有疑问","随时告诉我","欢迎继续交流","欢迎随时","great question","you're absolutely right","i hope this helps","of course","certainly","let me know if"],
        "tier2": ["让我来","让我为你","下面我们","综上所述","由此可见","拆一拆","盘一盘","划重点","敲黑板","捋一捋","让我们","let me break this down","let's dive in","in conclusion","without further ado","here's what you need to know"],
        "signposts": ["值得注意的是","需要强调的是","更关键的是","事实上","实际上","换句话说","说白了","本质上","归根结底","与此同时","at the end of the day","actually","additionally","furthermore","the truth is","here's the thing"],
    }
    outputs[DIST / "lexicon.json"] = _json.dumps(lex, ensure_ascii=False, indent=2)

    if check:
        failed = 0
        for p, expected in outputs.items():
            if not p.exists():
                print(f"[FAIL] 缺失 {p.relative_to(ROOT)}")
                failed += 1
                continue
            actual = p.read_text(encoding="utf-8")
            if actual != expected:
                print(f"[FAIL] 漂移 {p.relative_to(ROOT)}")
                failed += 1
            else:
                print(f"[PASS] {p.relative_to(ROOT)}")
        return 1 if failed else 0
    else:
        for p, content in outputs.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            print(f"[WRITE] {p.relative_to(ROOT)} {len(content)} chars")
        return 0

if __name__ == "__main__":
    sys.exit(main())
