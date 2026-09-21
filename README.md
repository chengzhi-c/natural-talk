# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让 AI 的表达回归真实人类状态：真诚、直接、有在场感；清掉机械套路，留足创作自由。

---

## 设计

- `SKILL.md`：核心规则（反例/正解对照）+ 防误杀三原则，日常对话只付最小上下文成本。
- `references/rules-full.md`：全量 D/B/C/N 编号规范，成文清理的逐条引用依据。
- `references/fiction.md`：叙事工法。摄影机视点在场（默认限知），动作与物理受力推进；结局、结构与角色声线不受限，管控的只有可定位的机械痕迹。
- `scripts/`：`scan-mechanical.py` 扫描草稿；`audit-cleanup.py` 审计清理稿的信息守恒与改动归属。

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

> 模型选择：`glm-5.3` `qwen3.8-27b` 指令遵循较好。规则只能提醒规避，执行靠模型自身解读——深度思考开启时完整度明显更高；弱依从模型（longcat/minimax）残留多，需扫描器兜底。

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

## 边界

学术论文、公文、法律文书、营销文案等体制文书，规则自动让位。"AI 味"多半源于预训练的表达缺陷，规则只能提醒规避，效果取决于模型自身的解读能力。

## 贡献

欢迎报告误判、提交案例：[CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua)：信息守恒、编辑边界与工程化评测的启发。
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone)：文本层反清单与实证对照的判定依据。

## 社区

[LINUX DO](https://linux.do)

## License

[MIT](LICENSE)
