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

| 场景 | 规则要点 |
| --- | --- |
| 对话 | 首句直给；问 A 答 A，结尾不升华；字数与数量照办；删"好问题/希望这对你有帮助"式开场收尾与"先说结论"提示语；跨轮用对方的说法，一句话的问题给短回答。 |
| 论述 | 删提示语壳与宏观开场；没人主张过 A 不写翻案句；翻译腔只认五式，"这意味着"生成不写、清理不动；顿号罗列不过密；序数小标题有内容就可以编号，清理不改已有编号；只用来引出列表的冒号句不改；破折号右侧承担解释、列举、同位、因果、补充、揭晓的不用；模糊归因与概括词在清理模式原样保留。 |
| 叙事 | 视点在场、动作与道具落地；装饰副词、生理套话、计数癖与装饰性对白标签先作候选，承载信息则保留；比喻要带感官增量；不写连续 ≥4 行独行对白。 |
| 清理 | 句内改写为主，删除限规则明示项；信息守恒，每处改动须能指认规则编号；拿不准不动；整句删除需用户同意。B5/B6/B7 的纯套话经确认无其他信息者、B8 问答乒乓里第 4 行起删掉不改变局势与可观察事实的轮次，不在此限。 |

## 效果

同一条小说提示词、16 个模型，各写两篇：一篇不启用规则，一篇启用 `SKILL.md` 与 `references/fiction.md`。AI 腔密度（每千字命中数）变化：

| 模型 | 对照组 | 挂 skill | 降幅 |
| --- | ---: | ---: | ---: |
| deepseek-v4-flash-0731 | 4.6 | 3.3 | -28% |
| deepseek-v4-pro-0813 | 7.5 | 2.4 | -68% |
| deepseek-v4.1-flash | 4.8 | 1.6 | -67% |
| gemini-3.8-flash | 6.9 | 2.3 | -67% |
| gemini-4-argon | 6.5 | 0.0 | -100% |
| glm-5.3 | 3.4 | 1.0 | -71% |
| glm-5.3-flash | 7.1 | 1.5 | -79% |
| gpt-6.1-sol | 8.0 | 1.4 | -82% |
| grok-4.7 | 3.8 | 1.1 | -71% |
| kimi-k2.6 | 8.3 | 3.5 | -58% |
| kimi-k3 | 4.7 | 0.0 | -100% |
| mimo-v2.6-pro | 5.0 | 4.5 | -10% |
| minimax-m3 | 6.3 | 2.8 | -56% |
| minimax-m3.1-flash | 7.3 | 5.9 | -19% |
| qwen3.8-flash | 4.5 | 1.0 | -78% |
| step-5-preview | 11.1 | 7.3 | -34% |
| **均值** | **6.24** | **2.48** | **-60%** |

非严谨测试，命中数随提示与样本变动，不用于评价模型能力。启用规则组的 16 篇中有 7 篇低于提示要求的两千字；对照组均不低于两千字，其中 6 篇超过三千字上限，启用规则组另有 1 篇超过。

<details>
<summary>测量条件</summary>

| 项 | 值 |
| --- | --- |
| 提示词 | 一条小说创作提示（高架桥下的二十四小时药店，2000–3000 字），全文见 [examples/README.md](examples/README.md) |
| 样本 | 每个模型每个条件一篇，共 32 篇 |
| 不启用规则 | 系统提示一句：你是一个中文写作与代码沟通助手。直接完成用户的要求。 |
| 启用规则 | `SKILL.md` 全文与 `references/fiction.md` 全文 |
| 采样 | temperature 1.0、reasoning_effort high、max_tokens 32000 |
| 计数 | 每千字 = 命中合计（B1–B9 ＋ 视点）÷ 汉字数 × 1000，保留一位小数；均值 = 16 个模型每千字率的算术平均，降幅 = 每千字率的变化 |

</details>

分项命中、逐篇字数与 32 篇原文见 [examples/README.md](examples/README.md)。命中只统计规则表内列名的形态，不评价文本质量。

## 使用

**一键安装：**

```bash
npx skills add chengzhi-c/natural-talk
```

**clone 至技能目录（以 Claude Code 为例）：**

```bash
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

**RikkaHub：** 设置 → 扩展 → Skills → `+`，选择 [Releases](https://github.com/chengzhi-c/natural-talk/releases) 里的 `natural-talk.zip`；安装后启用。主包：`SKILL.md`、`references/`、`LICENSE`。

**SillyTavern：** 把 `SKILL.md` 作为 system prompt 使用；小说或清理场景再按下表追加对应 references。

**自行打包：** 发行包里只有 `SKILL.md`、`references/fiction.md`、`references/rules-full.md` 与 `LICENSE` 四个文件，压成 zip 即为 `natural-talk.zip`；Releases 未挂包时按这个方式自取。

**卸载：** 删除 `~/.claude/skills/natural-talk`；RikkaHub 在 Skills 列表停用或删除；SillyTavern 从 system prompt 里移除对应段落。

---

## API / 规则使用：

- 读 `SKILL.md` 作 system prompt，按场景追加 references：

| 场景 | 追加 |
| --- | --- |
| 日常对话 / 一般生成 / 一般代码讨论 | `SKILL.md`（D 层作用于对话与一般生成。） |
| 代码评审 / PR 描述 / commit message / 技术长文 | `SKILL.md`；成稿后按 `references/rules-full.md`（R1–R10）过一遍 |
| 小说创作、续写、故事与扮演、同人、角色卡 | `SKILL.md` + `references/fiction.md` |
| 翻译 | `SKILL.md`（忠实原文优先，翻译腔 R6 不用于译文） |
| 论述类成文清理 | `SKILL.md` + `references/rules-full.md` |
| 小说成稿清理 | `SKILL.md` + `references/rules-full.md` 的带入 R 条与"清理边界"一节；`references/fiction.md` 取基本原则与 B1–B9 |
| 只要求指出问题、不要求改写（文章/文稿，明确只要诊断） | 按清理模式读取对应文体页，交付"命中处＋编号＋一句理由"；诊断用清理口径（只报不改，连续对白按 ≥4 行计）；代码调试/评审不按本条 |
| 清理后要求逐条说明改动 | 清理场景加 `references/rules-full.md` 全量 |

system 同时含用户设定时，规则放前部，设定放后部。

---

## 目录

```
natural-talk/
├── SKILL.md            # 核心规则（Agent 入口）
├── README.md           # 中文说明
├── README.en.md        # 英文说明
├── CONTRIBUTING.md     # 贡献指南
├── LICENSE             # MIT
├── references/         # 规则全文
├── tests/              # 仓库结构与契约自检
├── examples/           # 小说生成对照与正文
└── assets/
```

## 验证

`python -B tests/check_repo.py` 检查结构、链接、frontmatter、换行与规则编号引用，并复算 `examples/` 的字数与每千字折算、校验合计与分项自洽。扫描器、清理审计和模型评测不在本仓库。

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
