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
| Token敏感 | `templates/system-prompt-lite.txt` | 最小化核心规则 |

`templates/preset-*.txt` 是客服/技术博客/社交媒体/Fiction 四个场景预设，在上面模板之上叠加。

### Claude Code Skill

```bash
cd ~/.claude/skills/
git clone https://github.com/chengzhi-c/natural-talk.git
```

`SKILL.md` 在仓库根层级，clone 完即可识别。

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
├── SKILL.md                         # 规则唯一权威源·核心页（D/B/C/F/N 编号，生成/清理/fiction 三模式）
├── references/                      # 规则详情（改法/示例/边界），命中后按需读取
│   ├── rules-text.md                # 文本层 B1–B11
│   ├── rules-dialogue.md            # 对话层 D1–D5 与经验层 C1–C5
│   └── fiction.md                   # Fiction 章完整规则
├── templates/
│   ├── system-prompt-standard.txt   # 对话场景注入
│   ├── system-prompt-fiction.txt    # Fiction创作注入（含范文标注）
│   ├── system-prompt-lite.txt       # 轻量版（D 层分层配额＋上游 B 层倍率 top-5）
│   └── preset-*.txt                 # 场景预设
├── scripts/
│   ├── scan-mechanical.py           # 机械规则确定性扫描（B4/B6/B10/B11 FIX 级＋B1/B3 REVIEW 级候选；退出码 1=有命中）
│   ├── test-scan-mechanical.py      # 扫描器红灯自测（种植病灶必须捕获、人类成文零 FIX 误伤）
│   ├── check-sync.py                # 同步校验（在场＋判据锚＋规则指纹三层）
│   ├── test-sync.py                 # 注入攻击自测（语义反转必须被抓到）
│   ├── measure-fiction.py           # fiction 对照测量（人类/生成每千字频率）
│   └── sync-manifest.json           # 规则编号、触发词、判据锚与指纹清单
└── docs/
    ├── full-guide.md                # 阅读指引（指向 SKILL.md）
    ├── self-check.md                # 自检清单与回归门
    ├── misjudgments.md              # 防矫枉过正参考
    ├── porting-map.md               # 上游对照与裁剪理由（lieflat）
    ├── regression-baseline.md       # 回归集（清理/fiction/对话三组）与改后回归
    ├── d-layer-research.md          # 对话域成对采样研究
    └── fiction-research.md          # fiction 公版语料对照研究
```

改规则后：`python scripts/check-sync.py --update-fingerprints` 重算指纹，`python scripts/test-sync.py` 过一遍注入自测，再按 `docs/regression-baseline.md` 重跑回归门。

## 不适用

学术论文 / 公文 / 法律 / 营销文案 / 演讲稿，这些需要相反风格的场景本规则让位。

## 局限

模型写作的"AI 味"多是模型预训练的缺陷。skill 与 prompt 目前只能提醒、警示模型尽量避免，效果也依赖模型本身的解读能力。

## 贡献

欢迎报告误判、提交案例或改进规则，流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

文本层规则与反清单的判定依据来自 [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone) 的对照研究（629 篇、约 283 万字，26 项候选特征仅 11 项成立）。感谢这项工作。

## License

MIT
