# Natural Talk - 阅读指引

> 规则的权威源是 [`SKILL.md`](../SKILL.md)，它同时定义生成、清理、fiction 三种模式的加载范围。这里只讲入口，不重复条目。

## 读什么

| 想做什么 | 去哪读 |
|---------|--------|
| 看/改实际生效的规则 | `SKILL.md`（对话层 D1–D5、文本层 B1–B11、经验层 C1–C5、fiction 红线 F1–F5、反清单 N1–N11、规则×模式适用表） |
| 给聊天应用注入 system prompt | `templates/system-prompt-standard.txt`，轻量用 `-lite`，小说用 `-fiction` |
| 规则误伤了正常写法 | `docs/misjudgments.md` |
| 生成后自查与评测方法 | `docs/self-check.md` |
| 改规则后的回归验证 | `docs/regression-baseline.md` |
| 上游来源与裁剪理由 | `docs/porting-map.md` |
| 模板与权威源的同步校验 | `scripts/check-sync.py` + `scripts/sync-manifest.json` |

## 三条一直不变的原则

不编造：不知即说，不模糊，不装懂。
不评判人：不做心理判断，不给身份认证式夸奖。
不装AI：身份被直问时如实简答。

## 一句话判据

会对朋友这样说吗？删掉开场结尾后内容仍完整吗？

## 为什么规则不带数量上限

数量上限可被规避——换个说法就绕过了，触发标记不会。而"每篇不超过两次"这类约束，模型在写作过程中也无法可靠计数。现行规则一律用可定位的触发标记加反清单，见 `SKILL.md` 文本层。
