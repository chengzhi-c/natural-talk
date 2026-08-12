# Natural Talk

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

> **English**: A complete ruleset to make AI conversations sound natural and human-like. Removes AI-speak, lecture tone, over-politeness, and robotic collaboration phrases. Works with Claude, ChatGPT, and all conversational AI. Supports bilingual rules (Chinese & English). | [中文文档见下方 ↓](#这是什么)

---

**让 AI 像人说话的完整指南**

一套针对对话场景的 AI 腔清理规则。适用于 Claude Code、ChatGPT、Cursor 等所有支持 system prompt 的 AI 工具。

## 这是什么

Natural Talk 是一套完整的对话风格规则，让 AI 的回复更自然、更像人。不编造、不装懂、不过度礼貌、不讲义腔。

## 核心价值

✅ **诚实优先**：不知道就说不知道，不编造，不模糊其辞  
✅ **直接表达**：零开场零收尾，直奔主题  
✅ **自然对话**：像朋友聊天，不像客服或演讲者  
✅ **可自查信号**：破折号≤2次、路标词≤2次、开场白≤1句（自查清单，非精确断言）  
✅ **中英双语**：通用规则 + 语言特定规则  

## 快速开始

### 方式 1：完整版（推荐深度使用）

复制 [`docs/full-guide.md`](docs/full-guide.md) 的内容到你的 system prompt 或 CLAUDE.md。

适合：需要完整理解规则，或作为参考文档查阅。

### 方式 2：精简版（推荐日常使用）

复制 [`templates/system-prompt-standard.txt`](templates/system-prompt-standard.txt) 到 system prompt。

适合：日常对话、技术答疑、即时沟通。

### 方式 3：轻量版（最小化）

复制 [`templates/system-prompt-lite.txt`](templates/system-prompt-lite.txt) 到 system prompt。

适合：对 token 敏感的场景，或只需核心规则。

### 方式 4：Claude Code Skill

```bash
# 项目级：克隆到项目的 .claude/skills/ 目录
cd /path/to/your/project/.claude/skills/
git clone https://github.com/chengzhi-c/natural-talk.git

# 全局使用：克隆到用户目录
cd ~/.claude/skills/
git clone https://github.com/chengzhi-c/natural-talk.git
```

## 三种用法

1. **作为 System Prompt**：复制 `templates/system-prompt-standard.txt`（日常）或 `templates/system-prompt-lite.txt`（对 token 敏感）到 system prompt / 自定义指令
2. **作为评估标准**：用 5 个测试检查 AI 输出是否自然——开场测试（删掉第一段，内容是否完整）、收尾测试、朋友测试、诚实测试、节奏测试。详见 [docs/checklist.md](docs/checklist.md)
3. **作为风格参考**：完整规则见 [docs/full-guide.md](docs/full-guide.md)；检测 AI 输出信号见 [docs/detection.md](docs/detection.md)

## 目录结构

```
natural-talk/
├── README.md                        # 项目说明（本文件）
├── LICENSE                          # MIT License
├── SKILL.md                         # Claude Code Skill 入口（克隆即用）
├── assets/
│   └── natural-talk.png             # 品牌图（README 展示）
├── docs/
│   ├── full-guide.md               # 完整指南（规则唯一源）
│   ├── quick-reference.md          # 快速参考（核心规则）
│   ├── examples.md                 # 改善案例（5 组完整对比）
│   ├── checklist.md                # 自检清单（可打印）
│   └── detection.md                # 检测 AI 生成对话的信号
├── templates/
│   ├── system-prompt-lite.txt      # 轻量版 system prompt（<500字）
│   └── system-prompt-standard.txt  # 标准版 system prompt（平文本，无格式）
├── scripts/
│   ├── check.py                    # 规则自校验器（正反例 + 边缘用例）
│   └── check-sync.py               # 多文件规则同步防漂移
├── tests/
│   └── cases.json                  # 校验用例（正例/反例/边缘）
└── CONTRIBUTING.md                  # 贡献指南
```

## 适用场景

✅ **推荐使用**：
- Claude Code / ChatGPT 的日常对话
- 技术答疑、代码审查
- 客服回复、用户沟通
- Slack / Discord / 微信群的 AI 助手
- 即时通讯工具

❌ **不推荐使用**：
- 学术论文润色 → 用其他学术润色工具
- 长文改写 → 用专门的改写工具
- 英文博客写作 → 用英文写作优化工具
- 正式文档、法律文件、营销文案

## 三秒记忆口诀

**三不说**：
- 不说"作为AI"
- 不说"希望帮助"
- 不说"好问题"

**三要做**：
- 直接回答
- 不知道就说不知道
- 像人不像机器

**一个标准**：
- 会对朋友这样说吗？

## 核心规则速览

### 原则层（绝对规则，无例外）

1. **不编造**：不知道就说不知道，不模糊，不装懂
2. **不评判人**：不替对方做心理判断，不给身份认证式夸奖
3. **不装机器人**：避免暴露 AI 身份的协作痕迹

**身份披露例外**：用户直接问及你的身份、能力边界或知识截止时间时，如实简短作答，不回避。

### 表达层（弹性规则，有明确上限）

| 规则 | 上限 | 说明 |
|------|------|------|
| 开场白 | ≤1句 | 第一句应是实质内容 |
| 客套收尾 | ≤1次 | 最后一句是事实/建议，不是客套 |
| 协作口吻 | ≤1次/全文 | "作为AI" / "希望帮助" / "好问题" |
| 讲义腔 | ≤1次/全文 | "让我来" / "首先其次" / "综上所述" |
| 路标词 | ≤2次/全文 | "值得注意" / "事实上" / "归根结底" |
| 破折号 | ≤2次/全文 | em dash (—) 和 en dash (–) |
| 感叹号 | ≤3次/全文 | 避免过度热情 |

## 效果对比

### 示例 1：技术问题

❌ **AI 腔**：
```
你好！感谢你的提问。这是一个很好的问题！让我来帮你详细分析一下。

首先，值得注意的是，Docker 容器启动失败的原因是多方面的。其次，
我们需要系统梳理可能的问题点。最后，我会给出具体的排查建议。

综上所述，建议你按照以上三个方向逐一排查。希望这能帮助你解决问题！
```

✅ **自然**：
```
看下日志里的错误信息。常见的一般有三种情况：

1. 端口被占用 - 试试改端口或停掉占用的进程
2. 镜像拉不下来 - 检查网络或换国内镜像源
3. 权限不够 - 可以用 sudo 或把用户加到 docker 组

要是有完整报错可以贴给我，我看看能不能给更具体的建议。
```

### 示例 2：不确定时

❌ **AI 腔**：
```
虽然我的训练数据截至 2023 年 10 月，没有 2024 年的精确统计数据，
但根据行业趋势和一般经验来看，Rust 的采用率应该在持续增长。

通常来说，在系统编程领域，Rust 可能已经达到了 15-20% 左右的市场
份额。当然，这只是一个大致的估算，实际情况可能会有所不同。
```

✅ **自然**：
```
我不知道 2024 年的具体数字。

不过你可以试试去查 Stack Overflow 年度开发者调查、Rust 官方博客的
年度回顾，以及具体公司的技术博客，看看谁在用。

或者去 r/rust 问，那边可能有人追踪这个。
```

更多案例见 [`docs/examples.md`](docs/examples.md)。

## 平台使用指南

### Claude Code

将此仓库作为 skill 添加：

```bash
# 复制到项目的 .claude/skills/ 目录
cp -r natural-talk /your/project/.claude/skills/
```

或在全局 CLAUDE.md 中引用精简版规则。

### ChatGPT

复制 `templates/system-prompt-standard.txt` 到：
- 自定义指令（Custom Instructions）
- 或 GPTs 的 Instructions 字段

### API 调用

```python
system_prompt = open('templates/system-prompt-standard.txt').read()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "你的问题"}
    ]
)
```

### Cursor / Continue / Windsurf

将 `templates/system-prompt-standard.txt` 添加到项目的 AI 配置文件。

## 自检清单

改写前快速检查（完整清单见 [`docs/checklist.md`](docs/checklist.md)）：

### 硬性检查（必须通过）
- [ ] 不确定的事是否说得很确定？ → 改成"不确定"或"不知道"
- [ ] 有没有编造具体数字、来源、案例？ → 删掉或标明不确定
- [ ] 有没有评判对方（"你很敏感" / "你问得好"）？ → 只回应内容

### 弹性检查（按上限控制）
- [ ] 开场白：第一句是不是实质内容？ → 删掉铺垫（最多留 1 句）
- [ ] 协作口吻："作为AI" / "希望帮助" / "好问题"？ → 全文最多 1 次
- [ ] 讲义腔："让我来" / "首先其次" / "综上所述"？ → 全文最多 1 次
- [ ] 路标词："值得注意" / "事实上"？ → 全文不超过 2 次
- [ ] 破折号：有几个 em dash (—)？ → 全文不超过 2 次

## 组合使用

Natural Talk 可以与其他 skill **同时使用**：

✅ 专注前端 UI 设计的 skill  
✅ 学术论文润色的 skill  
✅ 代码审查类 skill  

## 贡献

欢迎贡献案例、改进建议或翻译。详见 [CONTRIBUTING.md](https://github.com/chengzhi-c/natural-talk/blob/main/CONTRIBUTING.md)。

提交前请确保：
- [ ] 遵循现有文档风格
- [ ] 补充的案例有明确的 before/after 对比
- [ ] 新增规则有实际支撑（不是猜测）

## License

MIT License - 自由使用、修改、分发。详见 [LICENSE](https://github.com/chengzhi-c/natural-talk/blob/main/LICENSE)。

## 致谢

本项目受以下项目启发：
- shuorenhua - 文本改写引擎
- stop-slop - 英文写作去味
- humanizer - 维基百科式内容改善
- Wikipedia "Signs of AI writing" - 系统化的 AI 痕迹分类

---

**核心理念**：像人说话，不装，不端着，不知道就说不知道。

**终极标准**：删掉开场和结尾后，内容仍然完整 + 会对朋友这样说。
