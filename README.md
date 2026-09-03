# Natural Talk

[English](README.en.md) | 中文

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

让 AI 的表达回归真实人类状态：真诚、直接、有在场感、无塑料套路。

> **版本选择**：强规则版见 [`natural-talk-strict`](https://github.com/chengzhi-c/natural-talk/tree/strict)。

---

## 核心设计

- **零号原则：交互姿态**：像懂行的同行一样交流，第一句直奔主题，消除客服废话、免责包装与表演性共情。
- **三大场景路由**：
  - **日常对话**：首句直给，自然段落展开，彻底封杀翻案腔（严禁先否定再肯定，只留肯定），严格执行数量词。
  - **故事叙事**：摄影机视点在场（限知叙事，Show, don't tell），严禁作者跳出镜头读心，实体阻力，拒绝伪深沉同词回环。
  - **成文清理**：局部微创降调，篇幅严格保真（80%~100%），信息严格守恒，尊重真人声口。

---

## 效果对比

<details>
<summary><b>测试设定（点击展开）</b></summary>

> **测试模型**：`大肥鲸-flash`  
> **统一提示词**：`豆包豆包，我要看女生谈恋爱，500字左右。`

</details>

| 优化前 | 优化后 |
| :---: | :---: |
| <img src="assets/detection-before.png" width="480" alt="优化前"> | <img src="assets/detection-after.png" width="480" alt="优化后"> |

<details>
<summary><b>查看生成原文详情（点击展开）</b></summary>

### 优化前

**《雨天与热牛奶》**

林知夏第一次注意到许栀，是在图书馆的最后一排。

那天雨下得很大，许栀缩在角落看书，头发被雨水淋得半湿，像只狼狈的小猫。林知夏走过去，把一杯还冒着热气的牛奶放在她手边：“图书馆楼下买的，多了一杯。”

许栀抬头，眼睛亮得像雨后洗过的天空。从此以后，每个下雨天，那排座位都会多一杯热牛奶。

后来她们一起熬夜赶论文，一起在便利店分食关东煮，一起把春天走成夏天。许栀会在林知夏打喷嚏时，自然而然地把围巾分她一半；林知夏会在许栀说“想吃甜的”时，跑三条街去买那家限量款泡芙。

谁都没有先开口，可谁都知道，那不是朋友的距离。

毕业前夜，她们坐在天台上喝酒。许栀喝得脸颊绯红，忽然小声问：“林知夏，如果我说我喜欢你……你会不会觉得奇怪？”

晚风正好。林知夏把易拉罐放下，指尖轻轻勾住许栀的手指，笑着说：“我等这句话，等了整整三年。”

那天夜里，城市的灯一盏盏亮起来，像为她们铺成一条银河。许栀靠在她肩上，声音闷闷的：“你的牛奶，以后还分我吗？”

“分。”林知夏低头吻了吻她的发顶，“一辈子都分你。”

窗外的雨，刚好停了。

---

### 优化后

雨是在九点半下来的。她站在便利店檐下，看着雾白的水汽漫过街灯，正犹豫要不要冲进雨里，肩头忽然一沉。一件还带着体温的外套披上来，然后是宋遥的声音，从身后近得发烫的地方落下来：“猜你就没带伞。”

她回头，宋遥手里攥着两把伞，一把撑开举在两个人头顶，伞骨往她这边斜了大半。

“一把就够了。”

“一把不够。”宋遥把另一把往胳膊底下一夹，空出的手理了理她沾了潮气的刘海，指尖在她额角停了一下，又收回去。“两把才显得我专门来接你。”

街灯把雨丝照成一线线亮的。她垂下眼，看见宋遥帆布鞋的鞋尖正对着自己的鞋尖，中间隔着一小洼水。她想往旁边挪半步，挪到一半又站回原处。

“你从哪儿过来的？”

“你们图书馆后门，等了四十分钟。”

她没忍住笑出声，笑完喉咙发紧。宋遥也笑，顺手把夹着的那把伞塞进她手里：“下次别让我等这么久。”

雨声把后半句泡软了。她没答话，低头摩挲伞柄上宋遥指节留下的潮气，往她那边靠了靠。两把伞挤在一起，伞沿碰着伞沿，滴下来的水连成一条线。

走到第三个路灯底下，宋遥忽然停下来，把斜了一路的伞扶正，声音被雨浸得湿漉漉的：“要不，你以后住我那儿，下雨天我不用跑两趟。”

她愣了愣。

“考虑考虑？”宋遥说。

她没回答，只是把伞收得更紧，脚步跟上去，鞋尖并着鞋尖，落进同一片水洼里。

</details>

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
