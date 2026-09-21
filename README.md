# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让 AI 的表达回归真实人类状态：真诚、直接、有在场感；清掉机械套路，留足创作自由。

---

## 设计

**对话**（生成模式自查，核心规则摘录）：

1. 首句直给：删"好问题！"式开场，第一句就是结论。
2. 问 A 答 A：明确给倾向，收尾停在事实或具体下一步，不升"这不仅是……更是……"式大命题。
3. 数量词严格：要 3 条就是恰好 3 条。
4. 翻案腔：没人主张过 A 就禁"不是A，而是B"式翻案（同类"没有A，只有B"一并禁），被否定的观点真实存在过才可用；改法是删否定留肯定。
5. 删宏观开场："在当今/随着……的发展"删掉，第一句进实质。
6. 叙述破折号只留话被打断的中断。

**叙事**（小说工法摘录，全量见 `references/fiction.md`）：

7. 抽象词对举的翻案禁用，能拍成画面（具体动作、感官事实）的放行。
8. "微微/轻轻/缓缓"修饰动作一律删，动词自带分量。
9. "猛地一僵/瞳孔骤缩"改成定住与呼吸停顿，紧张写成身体受力。
10. 装饰标签（"命令道/沉声道"）清零，力度让动作干活。

清理模式另有硬约束（句内手术、信息守恒、逐条引用编号，见 `SKILL.md`）；防误杀三原则保护问句、排比与作者惯用法。

机械兜底：`scripts/scan-mechanical.py` 扫描草稿，`audit-cleanup.py` 审计清理稿。

---

## 效果

<details>
<summary><b>测试设定</b></summary>

> `scripts/scan-mechanical.py`（gen 模式）自动扫描翻案腔变体与破折号密度，命中定位到字符级。短文 4 端点 × 10 模型 × 6 场景 106 份；小说长文 10 模型 × 4 场景 38 篇（每篇 2000-8000 字）。

</details>

**小说长文（10 模型 × 4 场景 × 38 篇）**：

| 模型 | 变体（累计） | 破折号（累计，合法句内形） |
| :--- | :---: | :---: |
| qwen3.8-27b / glm-5.3 / glm-5.3-flash / gemini-3.8 / step-5-preview / deepseek-v4-flash / longcat-2.0 | 0 | 0–4 |
| kimi-k2.6 / deepseek-v4-pro / minimax-m2.7 | 各 1 | 0–4 |

> 35 篇零命中；3 处残留人工复核后真病灶仅 1 处（minimax），其余 2 处为合法翻转与实物对举。FIX 级命中 0。深度思考开启时执行完整度显著更高。
>
> 无 skill 基线：glm-5.3 同题同卡双臂，不挂 1 变体 + 10 破折号 + 20 疑点，挂载后 0 + 0 + 1；短文对抗场景 5 模型裸跑 0–2 变体/篇。

**长文边界**：角色卡超长 system（20K+ 字符）叠加弱依从模型时翻案腔回潮，属模型对长指令的注意力衰减而非规则失效；缓解手段见 SKILL.md 场景路由。

**清理基准（17 例冻结语料）**：

| 模型 | L1 失败 | FIX 清除率 | REVIEW 清除率 | 误伤 | 留存率 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| kimi-k2.6 | 0/17 | 100% | 75% | 0/8 | 0.69–1.00 |
| qwen3.8-27b | 0/17 | 100% | 75% | 0/8 | 0.69–1.00 |
| deepseek-v4-flash | 5/17 | 100% | 64% | 3/8 | 0.23–1.00 |

> deepseek 的 5 处失败均为过删（应保留的实体信息被蒸发），`audit-cleanup.py` 可机械抓出全部 5 处。

---

## 使用

> 模型选择：`glm-5.3` `qwen3.8-27b` 指令遵循较好。规则只能提醒规避，执行靠模型自身解读；深度思考开启时完整度明显更高，弱依从模型（longcat/minimax）残留多，需扫描器兜底。

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
├── references/         # fiction.md 小说工法 / rules-full.md 全量规范
├── scripts/            # 扫描器、审计与体检套件
├── evals/              # 评测基准与判分
└── assets/
```

## 不适用

学术论文、公文、法律文书、营销文案、演讲稿等需要相反风格的特定体制文书，本规则自动让位。

## 局限

模型写作中的"AI 味"多半来自预训练形成的表达缺陷。现阶段，skill 与 prompt 主要只能通过提醒和警示，让模型尽量避免这些问题；实际效果仍取决于模型自身的解读能力。

## 贡献

欢迎报告误判、提交案例：[CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua)：中文优先的去 AI 味改写 skill，感谢其在信息守恒、编辑边界与工程化评测上的探索与启发。
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone)：中文去 AI 腔提示词研究，感谢其在文本层反清单与实证对照研究中提供的判定依据。

## 社区

欢迎加入 [LINUX DO](https://linux.do) 社区，一个「新的理想型社区」。

## License

[MIT](LICENSE)
