# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

---

中文去 AI 腔、恢复自然表达。适用于日常对话、小说创作、代码沟通、论述成文清理与小说成稿清理。

---

## 核心规则

完整规则与判定边界见 [SKILL.md](SKILL.md) 与 [references/](references/)。

| 规则 | 说明与示例 |
| --- | --- |
| **首句直给** | 切题作答，首句直接给出结论。不加“好问题 / 感谢提问 / 希望对你有帮助”等客套用语，结尾不作空泛拔高。 |
| **翻案句式** | 无人主张过前提 A 时，不写“不是 A 而是 B”（如“这不是普通的更新，而是一次蜕变”直接改为“这是一次蜕变”）。 |
| **叙述破折号** | 叙述中不使用破折号解释原因、列举事物或引出结论，改为逗号或正常断句。 |
| **修饰副词** | 删去动作前多余的修饰副词（如“微微点头”→“点头”，“轻轻推开”→“推开”，“极轻地说”→“说”）。 |
| **装饰性比喻** | 禁用缺乏真实感官的陈旧套话比喻（如“像一潭死水”）与人物兽化比喻（如“像受惊的小兽”）；比喻须体现具体感官细节。 |
| **否定用户未提及的问题** | 给出结论后，不自行追加“但这并不代表/这并不意味着……”去否定用户并未提出的想法；确有限制条件时直接写明适用边界。 |
| **清理原则** | 修改稿件时以句内局部修改为主，仅删去无实质信息的纯套话，完整保留原文有效信息。 |

## 安装与使用

**一键安装（Skills CLI）：**

```bash
npx skills add chengzhi-c/natural-talk
```

**克隆到本地目录（以 Claude Code 为例）：**

```bash
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

**常见客户端集成：**

- **RikkaHub**：设置 → 扩展 → Skills → `+`，选择 [Releases](https://github.com/chengzhi-c/natural-talk/releases) 中的 `natural-talk.zip` 安装启用。
- **SillyTavern**：直接将 `references/fiction.md` 内容填入 System Prompt。

**卸载：** 删除对应目录，或在客户端扩展列表中移除。

---

## 场景搭配

直接将 `SKILL.md` 作为基础提示词（System Prompt）。不同场景可按需搭配 `references/` 中的规则模块：

| 场景 | 推荐搭配 | 说明 |
| --- | --- | --- |
| 日常对话 / 代码交流 | `SKILL.md` | D 层对话规范约束，首句直给，去除冗余客套 |
| 技术文档 / 代码评审 | `SKILL.md` + `references/rules-full.md` | 成稿后依 R1–R8 复查文本规范 |
| 小说创作 / 角色扮演 | `SKILL.md` + `references/fiction.md` | 具象感官描写，以具体动作与物理细节推进情节 |
| 文章 / 稿件清理修改 | `SKILL.md` + `references/rules-full.md`（小说另加 `fiction.md`） | 句内局部修改，完整保留原文实质信息 |
| 仅诊断不改写 | 搭配对应场景规则 | 仅输出“命中位置＋规则编号＋简短理由”，不修改正文 |

若系统提示词中同时包含角色设定或业务背景，建议将本规则置于设定之前。

---

## 目录结构

```
natural-talk/
├── SKILL.md            # 核心规则（Agent 入口）
├── README.md           # 中文说明
├── README.en.md        # 英文说明
├── CONTRIBUTING.md     # 贡献指南
├── LICENSE             # 开源许可证
├── references/         # 场景详细规则（清理 / 小说）
├── tests/              # 格式与契约检查
└── assets/             # 资源文件
```

## 验证

运行自检脚本，检查文档链接、格式与规则编号引用的完整性：

```bash
python -B tests/check_repo.py
```

## 叙事工法范例来源

`references/fiction.md` 的三段工法范例节选自：

| 工法 | 出处 |
| --- | --- |
| 动作与身体重力推进 | 朱自清《背影》 |
| 具象实物作比 | 郁达夫《春风沉醉的晚上》 |
| 人动景随 | 鲁迅《社戏》 |

## 不适用场景

学术论文、公文、法律文书、营销文案、演讲稿等文体默认不适用（用户明确指定按本规则清理时除外）。

## 局限说明

AI 腔多源于模型预训练形成的表达惯性，本规则通过显式约束引导模型规避，实际效果仍取决于所用模型的指令遵循能力。

## 贡献

欢迎报告误判或提交正反例对照：[CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua)：中文优先的去 AI 味改写 skill。
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone)：中文去 AI 腔提示词研究。

## 社区

[LINUX DO](https://linux.do)。

## License

[MIT](LICENSE)
