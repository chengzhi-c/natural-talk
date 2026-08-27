# Natural Talk

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让 AI 像人一样说话、创作的规则集。适用于 Claude、ChatGPT 及所有支持 system prompt 的工具。

## 核心理念

三不说：不说"作为AI"、不说"希望帮助"、不说"好问题"

三要做：直接回答、不知道就说不知道、像人不像机器

终极标准：会对朋友这样说吗？

Fiction 场景另有一套：写具体动作而非情感定论，比喻看质地不看数量，景物按视线辨认的顺序展开。范文标注见 `templates/system-prompt-fiction.txt`。

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
├── SKILL.md                         # 规则唯一权威源（生成/清理/fiction 三模式）
├── core/rules.yaml                  # 已冻结的历史存档，勿参照
├── templates/
│   ├── system-prompt-standard.txt   # 对话场景注入
│   ├── system-prompt-fiction.txt    # Fiction创作注入（含范文标注）
│   ├── system-prompt-lite.txt       # 轻量版
│   └── preset-*.txt                 # 场景预设
├── scripts/                         # 真实生成评测脚本
└── docs/
    ├── full-guide.md                # 完整指南
    ├── self-check.md                # 自检清单
    └── misjudgments.md              # 防矫枉过正参考
```

## 不适用

学术论文 / 公文 / 法律 / 营销文案 / 演讲稿，这些需要相反风格的场景本规则让位。

## 贡献

欢迎报告误判、提交案例或改进规则，流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

MIT
