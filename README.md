# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

---

- 中文去 AI 腔、恢复自然表达。适用于小说创作（人物、对白、场景、叙事节奏）、日常对话、代码沟通、论述成文清理与小说成稿清理。

---

## 核心规则

完整规则与判定边界见 [SKILL.md](SKILL.md) 与 [references/](references/)。

| 规则 | 说明与示例 |
| --- | --- |
| **首句直给** | 问什么答什么，第一句就给结论。不加“好问题 / 感谢提问 / 希望对你有帮助”等客套，结尾不强行升华。 |
| **翻案腔** | 没人主张过就不写“不是 A 而是 B”（如“这不是普通的更新，而是一次蜕变”直接改为“这是一次蜕变”）。 |
| **叙述破折号** | 叙述中不用破折号来解释原因、列举事物或引出结论，直接换成逗号或断句。 |
| **修饰副词** | 删掉动作前多余的修饰词（如“微微点头”→“点头”，“轻轻推开”→“推开”，“极轻地说”→“说”）。 |
| **烂俗比喻** | 不用机械套路比喻（如“像永不疲倦的引擎”、“像受惊的小兽”），比喻必须有真实的感官细节。 |
| **翻译腔** | 规避“当……时”、“对于……来说”、“这意味着”、“然而/此外/与此同时”等刻板连接词。 |
| **对白与视点** | 避免短句来回乒乓对白，多写具体动作推进；沉浸在视点角色的观察中，不凭空解说心理。 |
| **清理原则** | 修改稿件时以句内优化为主，只删毫无意义的纯套话，保留全部有效信息。 |

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

- **RikkaHub**：设置 → 扩展 → Skills → `+`，选择 [Releases](https://github.com/chengzhi-c/natural-talk/releases) 里的 `natural-talk.zip` 安装启用。
- **SillyTavern**：直接将 `SKILL.md` 内容填入 System Prompt。

**卸载：** 删除对应目录，或在客户端扩展列表中移除。

---

## 场景搭配

直接将 `SKILL.md` 作为基础提示词（System Prompt）。不同场景可按需搭配 `references/` 中的规则：

| 场景 | 推荐搭配 | 说明 |
| --- | --- | --- |
| 日常对话 / 代码交流 | `SKILL.md` | D 层规则约束，确保首句直给，无冗余话术 |
| 技术文档 / 代码评审 | `SKILL.md` + `references/rules-full.md` | 依 R1–R10 复查合规性 |
| 小说创作 / 角色扮演 | `SKILL.md` + `references/fiction.md` | 强调感官细节，以动作推进情节 |
| 文章 / 稿件清理修改 | `SKILL.md` + `references/rules-full.md` | 句内优化，保留原信息 |
| 只诊断不改写 | 搭配对应场景规则 | 输出“位置+编号+理由”，不进行改写 |

如果系统提示词中同时包含角色设定或业务背景，建议将本规则放在前面，设定放在后面。

---

## 目录结构

```
natural-talk/
├── SKILL.md            # 核心规则（Agent 入口）
├── README.md           # 中文说明
├── README.en.md        # 英文说明
├── CONTRIBUTING.md     # 贡献指南
├── LICENSE             # 开源许可证
├── references/         # 场景详细规则
├── tests/              # 格式与契约检查
└── assets/             # 资源文件
```

## 验证

运行自检脚本，检查文档链接、格式与规则引用的完整性：

```bash
python -B tests/check_repo.py
```

## 叙事工法范例来源

`references/fiction.md` 的三段工法范例节选自：

| 工法 | 出处 |
| --- | --- |
| 动作与身体重力推进 | 朱自清《背影》 |
| 具象实物作比 | 郁达夫《春风沉醉的晚上》 |
| 人动景才出 | 鲁迅《社戏》 |

## 不适用

非用户要求，学术论文、公文、法律文书、营销文案、演讲稿等需要相反风格的文体默认不适用。

## 局限

AI 味多数来自预训练形成的表达缺陷，本 skill 只能提醒模型规避，实际效果仍取决于模型自身的解读能力。

## 贡献

欢迎报告误判、提交案例：[CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua)：中文优先的去 AI 味改写 skill。
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone)：中文去 AI 腔提示词研究。

## 社区

[LINUX DO](https://linux.do)。

## License

[MIT](LICENSE)
