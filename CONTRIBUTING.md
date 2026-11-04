# 贡献指南

## 改哪里

- 对话与生成规则改 `SKILL.md`。
- 清理规则改 `references/rules-full.md`。
- 小说规则改 `references/fiction.md`。
- 同一条规则出现在两页时，两页一起改。
## 怎么改

Issue 或 PR 里给出场景、原句和改后的句子。

正例必须能从反例按这条规则改出来，不另加反例里没有的事实。需要补动作或物件的示例，在旁边注明。

改完后跑：

```bash
python -B tests/check_repo.py
```

## 范例与许可

`references/fiction.md` 的工法范例用已进入公有领域的作品，不自写。

提交即表示贡献采用 MIT License，并且你拥有这些内容的版权或已获得授权。

问题请到 [GitHub](https://github.com/chengzhi-c/natural-talk) 开 Issue。
