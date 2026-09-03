# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让 AI 像人一样说话、创作的规则集。适用于 Claude、ChatGPT 及所有支持 system prompt 的工具。

**强规则版**（natural-talk-strict）。与轻量版 [natural-talk](https://github.com/chengzhi-c/natural-talk) 相比：规则密度更高，区分生成/清理/fiction 三种模式，带信息守恒、最小改动、白名单豁免三条硬约束，附机械自查脚本与评测环；适合成稿清理、长文写作与 fiction 创作。日常轻量对话用轻量版即可。

## 核心理念

三不说：不说"作为AI"、不说"希望帮助"、不说"好问题"

三要做：直接回答、不知道就说不知道、像人不像机器

终极标准：会对朋友这样说吗？

小说、扮演等 fiction 场景不适用上述规则，另有独立体系：限制视角叙述（只写视点人物此刻的感知与盘算，作者不越界总结情绪）、喻体须为可见实物、景物随人物视线的辨认顺序展开。完整规则见 `references/fiction.md`。

## 快速开始

全部规则以根目录 `SKILL.md` 为唯一权威源。作为 skill 安装（Claude Code 等）时宿主自动读取；用于 API 或其他 system prompt 工具时，把 `SKILL.md` 内容直接注入 system prompt。

### Claude Code Skill

```bash
cd ~/.claude/skills/
git clone -b strict https://github.com/chengzhi-c/natural-talk.git natural-talk-strict
```

`SKILL.md` 在仓库根层级，clone 完即可识别。

有终端能力的宿主可在生成前对自身草稿运行机械自查（FIX 命中即改，REVIEW 命中复核后决定）：

```bash
python scripts/scan-mechanical.py <文件> --mode gen
```

### RikkaHub / SillyTavern

导入 [Release](https://github.com/chengzhi-c/natural-talk/releases) 中的 `natural-talk.zip`

### API 调用

```python
system_prompt = open('SKILL.md', encoding='utf-8').read()

response = client.chat.completions.create(
    model="<your-model>",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "你的问题"}
    ]
)
```

## 目录结构

```
natural-talk/
├── SKILL.md                         # 规则唯一权威源·核心页（D/B/C/F/N 编号，生成/清理/fiction 生成/fiction 清理四条路径）
├── references/                      # 规则详情（改法/示例/边界），命中后按需读取
│   ├── rules-text.md                # 文本层 B1–B11
│   ├── rules-dialogue.md            # 对话层 D1–D6 与经验层 C1–C6
│   └── fiction.md                   # Fiction 章完整规则
├── scripts/                          # 维护者校验（不参与模型加载）
│   ├── scan-mechanical.py            # 机械触发候选扫描
│   ├── test-scan-mechanical.py       # 扫描器固定样例测试
│   ├── check-retention.py            # 改写留存率计算
│   ├── test-eval-harness.py          # 评测环 harness 测试
│   ├── test-skill-contract.py        # 发布文件契约测试
│   └── fixtures/fiction-sample.txt    # fiction 扫描边界样例
├── evals/                            # 评测环（维护者跑分用）
└── assets/
    └── natural-talk.png             # 品牌图片
```


## 不适用

学术论文 / 公文 / 法律 / 营销文案 / 演讲稿，这些需要相反风格的场景本规则让位。

## 局限

模型写作中的"AI 味"多半来自预训练形成的表达缺陷。现阶段，skill 与 prompt 主要只能通过提醒和警示，让模型尽量避免这些问题；实际效果仍取决于模型自身的解读能力。

## 贡献

欢迎报告误判、提交案例或改进规则，流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

文本层规则与反清单的判定依据来自 [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone) 的对照研究（629 篇、约 283 万字，26 项候选特征仅 11 项成立）。感谢这项工作。

## License

MIT
