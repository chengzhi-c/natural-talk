# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让 AI 的表达回归真实人类状态：真诚、直接、有在场感、无塑料套路。

---

## 核心设计

- **零号原则：交互姿态**：像懂行的同行一样交流，第一句直奔主题，消除客服废话、免责包装与表演性共情。
- **三大场景路由**：
  - **日常对话**：首句直给，自然段落展开，彻底封杀翻案腔（严禁先否定再肯定，只留肯定），严格执行数量词。
  - **故事叙事**：摄影机视点在场（限知叙事，Show, don't tell），严禁作者跳出镜头读心，实体阻力，拒绝伪深沉同词回环。
  - **成文清理**：局部微创降调，篇幅严格保真（80%~100%），信息严格守恒，尊重真人声口。

---

## 快速使用

### 1. Agent Skill 安装

```bash
# 方式一：通过 npx skills 一键安装
npx skills add chengzhi-c/natural-talk

# 方式二：Git Clone 至 Claude Code / Cursor / Codex / Antigravity 技能目录
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

### 2. 作为 System Prompt 或 Agent 工具使用

直接读取 `SKILL.md` 作为主 Prompt，并按需引入 `references/` 下的场景指南：

**API 调用示例**：
```python
from pathlib import Path
from openai import OpenAI

client = OpenAI()
root = Path("path/to/natural-talk")

# 读取主规则，根据任务按需拼接场景指南
system_prompt = (root / "SKILL.md").read_text(encoding="utf-8")
# 如为小说创作场景，可拼接 fiction.md:
# system_prompt += "\n\n" + (root / "references" / "fiction.md").read_text(encoding="utf-8")

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
├── SKILL.md                         # 核心规范与日常对话（Agent 入口与单一事实源）
├── references/                      # 垂直场景深度参考库（按需读取）
│   ├── dialogue.md                  # 对白与交互深度参考
│   ├── fiction.md                   # 叙事创作与文学张力指南
│   └── polish.md                    # 文本成文清洗与保真润色参考
├── scripts/                         # 自动化契约与全量体检脚本 (verify_repo.py)
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
