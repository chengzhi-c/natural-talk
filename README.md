# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让 AI 像人一样说话、创作的规则集。适用于 Claude、ChatGPT 及所有支持 system prompt 的工具。

## 核心理念

三不说：不说"作为AI"、不说"希望帮助"、不说"好问题"

三要做：直接回答、不知道就说不知道、像人不像机器

终极标准：会对朋友这样说吗？

小说、扮演等 fiction 场景不适用上述规则，另有独立体系：限制视角叙述（只写视点人物此刻的感知与盘算，作者不越界总结情绪）、喻体须为可见实物、景物随人物视线的辨认顺序展开。完整规则与标注范文见 `templates/system-prompt-fiction.txt`。

## 快速开始

按场景选注入模板，复制文件内容到 system prompt：

| 场景 | 文件 | 说明 |
|------|------|------|
| 日常对话 | `templates/system-prompt-standard.txt` | 默认推荐 |
| Fiction创作 | `templates/system-prompt-fiction.txt` | 小说/扮演/同人/情感向 |
| Token敏感 | `templates/system-prompt-lite.txt` | 高收益核心＋定向 B5/C6 |

`templates/preset-*.txt` 是客服/技术博客/社交媒体/Fiction 四个场景预设，在上面模板之上叠加。

### Claude Code Skill

```bash
cd ~/.claude/skills/
git clone https://github.com/chengzhi-c/natural-talk.git
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
system_prompt = open('templates/system-prompt-fiction.txt').read()

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
├── templates/
│   ├── system-prompt-standard.txt   # 对话场景注入
│   ├── system-prompt-fiction.txt    # Fiction创作注入（含范文标注）
│   ├── system-prompt-lite.txt       # 轻量版（高收益核心＋定向 B5/C6）
│   └── preset-*.txt                 # 场景预设
├── scripts/                          # 维护者校验（不参与模型加载）
│   ├── check-sync.py                 # 规则与模板同步校验
│   ├── scan-mechanical.py            # 机械触发候选扫描
│   ├── test-scan-mechanical.py       # 扫描器固定样例测试
│   ├── test-sync.py                  # 同步反向指令测试
│   ├── test-skill-contract.py        # 发布文件契约测试
│   ├── sync-manifest.json             # 规则、锚点与指纹清单
│   └── fixtures/fiction-sample.txt    # fiction 扫描边界样例
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
