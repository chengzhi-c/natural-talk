# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让 AI 的表达回归真实人类状态：真诚、直接、有在场感、无塑料套路。

---

## 核心设计

- **零号原则**：事实与设定守恒、角色台词完全豁免、文风自由不设限（只除 AI 塑料套路）。
- **三大心智**：
  - **日常对话**：像懂行的朋友一样交流，第一句直奔主题，消除客服废话与表演性共情。
  - **故事叙事**：摄影机视点在场（Show, don't tell），角色在生活，作者不讲戏、不说教。
  - **成文清理**：局部微创降调，长文不缩水，尊重真人声口。

---

## 快速使用

### 1. Agent Skill 安装

```bash
# 方式一：通过 npx skills 一键安装
npx skills add chengzhi-c/natural-talk

# 方式二：Git Clone 至 Claude Code / Cursor / Codex 技能目录
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

### 2. 作为 System Prompt 注入

复制 `templates/` 下与场景匹配的模板作为系统提示词：

| 场景 | 模板文件 | 说明 |
| :--- | :--- | :--- |
| **日常对话 / 通用助手** | [`templates/system-prompt-standard.txt`](templates/system-prompt-standard.txt) | 消除客服套话、真诚直给 |
| **故事 / 小说 / 网文创作** | [`templates/system-prompt-fiction.txt`](templates/system-prompt-fiction.txt) | 视点在场、对白潜台词、去网文塑料感 |
| **Token 敏感 / 极简场景** | [`templates/system-prompt-lite.txt`](templates/system-prompt-lite.txt) | 高浓度极简核心规则 |

`templates/preset-*.txt` 提供客服、技术博客、社交媒体等细分场景预设。

**API 调用示例**：
```python
from openai import OpenAI

client = OpenAI()
system_prompt = open('templates/system-prompt-fiction.txt', encoding='utf-8').read()

response = client.chat.completions.create(
    model="your-model-name",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "你的创作或对话提示词"}
    ]
)
print(response.choices[0].message.content)
```

### 3. RikkaHub / SillyTavern

导入 [Release](https://github.com/chengzhi-c/natural-talk/releases) 中的 `natural-talk.zip`。

---

## 目录结构

```
natural-talk/
├── SKILL.md                         # 核心规范唯一源（日常对话 / 故事创作 / 成文清理）
├── references/                      # 细化参考与正反例（按需查阅）
│   ├── polish.md                    # 文本成文清洗与保真润色参考
│   ├── dialogue.md                  # 日常人味与角色对白指南
│   └── fiction.md                   # 叙事创作与空间在场参考
├── templates/                       # 提示词注入模板
│   ├── system-prompt-standard.txt   # 日常对话模板
│   ├── system-prompt-fiction.txt    # 故事创作模板
│   ├── system-prompt-lite.txt       # 极简轻量模板
│   └── preset-*.txt                 # 场景预设
├── scripts/                         # 检测与体检脚本 (scan_slop.py / verify_repo.py)
├── evals/                           # 评测基准与用例
└── assets/                          # 静态资源
```

---

## 不适用

学术论文、公文、法律文书、营销文案、演讲稿等需要相反风格的特定体制文书，本规则自动让位。

---

## 局限

模型写作中的“AI 味”多半来自预训练形成的表达缺陷。现阶段，skill 与 prompt 主要只能通过提醒和警示，让模型尽量避免这些问题；实际效果仍取决于模型自身的解读能力。

---

## 贡献

欢迎报告误判、提交案例或改进规则，流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 致谢

文本层规则与反清单的判定依据来自 [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone) 的对照研究（629 篇、约 283 万字，26 项候选特征仅 11 项成立）。感谢这项工作。

---

## License

[MIT](LICENSE)
