# Natural Talk

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让 AI 像人一样说话、创作的规则集。适用于 Claude、ChatGPT 及所有支持 system prompt 的工具。

## 快速开始

按场景选择注入模板：

| 场景 | 文件 | 说明 |
|------|------|------|
| 日常对话 | `templates/system-prompt-standard.txt` | 默认推荐 |
| Fiction创作 | `templates/system-prompt-fiction.txt` | 小说/扮演/同人/情感向 |
| Token敏感 | `templates/system-prompt-lite.txt` | 最小化核心规则 |

复制对应文件内容到 system prompt 即可。

**分级 prompt**：`dist/prompts/` 下 L0-L3 四档，按需选用或由 `engine/selector.py` 自动选档。

### Claude Code Skill

```bash
cd ~/.claude/skills/
git clone https://github.com/chengzhi-c/natural-talk.git
```

### RikkaHub / SillyTavern

导入 [Release](https://github.com/chengzhi-c/natural-talk/releases) 中的发布 zip（`natural-talk.zip`）即可。

发布包已将 `SKILL.md` 打平到 zip 根层级，应用可直接识别。

> 不要直接导入本仓库完整源码——开发目录结构会导致应用无法正确加载入口文件。

### API 调用

```python
system_prompt = open('templates/system-prompt-fiction.txt').read()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "你的问题"}
    ]
)
```

## 目录结构

```
natural-talk/
├── SKILL.md                         # Claude Code Skill 入口
├── core/rules.yaml                  # 规则唯一源
├── templates/
│   ├── system-prompt-standard.txt   # 对话场景注入
│   ├── system-prompt-fiction.txt    # Fiction创作注入
│   ├── system-prompt-lite.txt       # 轻量版
│   └── preset-*.txt                 # 场景预设
├── dist/prompts/                    # L0-L3 分级 prompt
├── engine/                          # 检测/修复/选档引擎
├── scripts/                         # 构建/校验/评测脚本
├── docs/                            # 完整指南/防矫枉参考
└── tests/cases.json                 # 校验用例
```

## 核心理念

三不说：不说"作为AI"、不说"希望帮助"、不说"好问题"

三要做：直接回答、不知道就说不知道、像人不像机器

终极标准：会对朋友这样说吗？

## 不适用

学术论文 / 公文 / 法律 / 营销文案 / 演讲稿——需要相反风格的场景，本规则让位。

## License

MIT
