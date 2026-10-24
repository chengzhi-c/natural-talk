# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让模型的表达回到具体、直接、有依据的状态：清掉机械套路，留足创作自由。

---

## 核心规则

**对话**：

1. 首句直给：删机械开场，第一句就是结论。
2. 问 A 答 A：给明确倾向，收尾停在事实或具体下一步。
3. 数量词严格：要 3 条就是恰好 3 条。
4. 字数照办：给了区间就照办，超出或低于 20% 即压回或补足，写完数字数。
5. 翻案腔：没人主张过 A 就禁“不是A，而是B”（含“没有A，只有B”等同类句式）。
6. 删宏观开场：“在当今/随着……的发展”不带具体背景就删。
7. 破折号只保留话被打断的中断。
8. 多轮与体量：一句话的问题给短回答；不复述上轮原话，不重复已给结论。

**论述**：

9. 起手式与提示语壳：“说白了/先说结论”与“一句话总结：/核心是：”删掉，第一句进实质。
10. 顿号过密与序数词小标题：一个分句内 ≥3 项顿号并列即过密（技术专名串、法规条目不算）；“一、二、三”编号小标题连发 ≥3 个是模板感。
11. 段首零回指与概括盖具体：“值得注意的是”起段而句内无“这/那”回指；同段已有具体数字还断言“显著提升”。
12. 翻译腔只认五种：过长前置定语、“当……时”前置从句、“对于……来说”话题壳、“然而/此外”句首路标、“这意味着”复述前句。

**叙事**：

13. 抽象词对举的翻案禁用；具体动作、感官事实的放行。
14. 占位符不得进正文：“{{char}}/某某/XXX”原样出现即吃设，落成具体姓名或可指认的称谓。
15. “微微/轻轻/缓缓”修饰动作的删，动词自带分量；光色声音温度的客观状态豁免。
16. “猛地一僵/瞳孔骤缩/低吼一声”改写定住与呼吸停顿，紧张靠人物当下正在做的动作带出。
17. 连续 ≥5 行独行对白、行间无叙述即判问答乒乓（四行以内放行）；引号外只挂四个字以内标签的行也算对白行，叙述成句则打断。
18. 装饰标签（“命令道/沉声道/低吼道”）清零。
19. 喻体要带感官增量；句尾比喻成片出现即过度（全文至少五处且超全文句数 8% 就改掉大半）。
20. 计数癖：作者不数拍子（“一下，两下，三下”“隔三息”）；角色在数是情节，放行。

对白边界：连续短句往返才按病灶处理；改法是插入叙述或压成转述，不是给角色加话。整场都改成转述链是同一个毛病换衣服，间接转述只压程序性拉锯那几轮。

清理模式：句内手术、信息守恒、逐条引用编号。防误杀原则保护问句、排比与重复技术名词，拿不准视为不命中。

机械兜底：`scripts/scan-mechanical.py` 扫描草稿（生成模式用 `--mode gen`，覆盖全部文体），`audit-cleanup.py` 审计清理稿。

---

## 效果

9 个模型 × 3 种场景（小说创作 / 论述清理 / 日常对话），各配不挂 skill 的对照组，
共 216 次生成。AI 腔密度（每千字机械层命中数）变化：

| 模型 | 对照组 | 挂 skill | 降幅 |
| --- | --- | --- | --- |
| deepseek-v4-flash-0731 | 5.33 | 2.35 | -56% |
| deepseek-v4-pro-0813 | 4.97 | 3.01 | -39% |
| deepseek-v4.1-flash-1017 | 4.19 | 1.07 | -74% |
| gemini-3.8-flash-high | 5.29 | 2.18 | -59% |
| kimi-k2.6 | 5.35 | 2.04 | -62% |
| kimi-k3 | 6.08 | 0.66 | -89% |
| mimo-v2.6-pro | 5.47 | 2.23 | -59% |
| qwen3.8-flash | 5.91 | 2.00 | -66% |
| step-5-preview | 5.34 | 2.33 | -56% |
| **均值** | **5.33** | **1.99** | **-63%** |

9 个模型全部下降，区间 -39% 到 -89%，无一失效。

GLM 系补充测量（单列不并入上表）：

| 模型 | 对照组 | 挂 skill | 降幅 |
| --- | --- | --- | --- |
| glm-5.3 | 6.23 | 0.44 | -93% |
| glm-5.3-flash | 5.50 | 0.56 | -90% |

<details>
<summary>测量条件</summary>

测量条件：thinking 开启且 reasoning_effort = max（所有模型）；temperature = 1.0
（client 在 reasoning 开启时对 None 取 1.0，即全部模型均为 1.0）；max_tokens = 20000，
超时 2400s。每模型 12 篇（小说创作 4 题 / 论述清理 4 例 / 日常对话 4 问），
skill 臂与 none 臂同题对照，每个格子仅 1 次生成，无重复采样，无方差。
局限：单样本对比，绝对值应视为量级参考而非稳定估计；降幅区间会随题目变化。

</details>

误报控制：9 位作者 8.8 万字人类作品（鲁迅、周作人、梁实秋、汪曾祺、王小波、
余秋雨、朱自清、林语堂、沈从文）经扫描器全量扫描，零 FIX 命中；REVIEW 级候选逐条人工判读，非自动判定。

---

## 使用

```bash
# 一键安装
npx skills add chengzhi-c/natural-talk

# 或 clone 至 Claude Code / Cursor / Codex / Antigravity 技能目录
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

**API 调用**：读 `SKILL.md` 作 system prompt，按场景拼接 references：

```python
system = Path("SKILL.md").read_text(encoding="utf-8")
# 小说创作拼接 fiction.md；成文清理拼接 rules-full.md（改动须逐条引用编号）
# system += "\n\n" + Path("references/fiction.md").read_text(encoding="utf-8")
```

RikkaHub / SillyTavern：导入 [Release](https://github.com/chengzhi-c/natural-talk/releases) 的 `natural-talk.zip`。

---

## 目录

```
natural-talk/
├── SKILL.md            # 核心规则（Agent 入口）
├── CONTRIBUTING.md     # 贡献指南
├── LICENSE             # MIT
├── references/         # fiction.md 小说工法 / rules-full.md 全量规范
├── scripts/            # 扫描器、审计与体检套件
├── evals/              # 评测基准与判分
└── assets/
```

## 不适用

学术论文、公文、法律文书、营销文案、演讲稿等需要相反风格的特定体制文书，本规则自动让位。

## 局限

模型写作中的“AI 味”多半来自预训练形成的表达缺陷。现阶段，skill 与 prompt 主要只能通过提醒和警示，让模型尽量避免这些问题；实际效果仍取决于模型自身的解读能力。

## 贡献

欢迎报告误判、提交案例：[CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua)：中文优先的去 AI 味改写 skill，感谢其在信息守恒、编辑边界与工程化评测上的探索与启发。
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone)：中文去 AI 腔提示词研究，感谢其在文本层反清单与实证对照研究中提供的判定依据。

## 社区

欢迎加入 [LINUX DO](https://linux.do) 社区，一个「新的理想型社区」。

## License

[MIT](LICENSE)
