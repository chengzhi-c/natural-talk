# 贡献指南

## 修改范围

- 对话与通用生成规则修改 `SKILL.md`。
- 文本清理规则修改 `references/rules-full.md`。
- 小说叙事规则修改 `references/fiction.md`。
- 跨文件共用的规则需同步修改所有涉及的文档。

## 提交要求

在 Issue 或 PR 中提供适用场景、修改前反例与修改后正例。

正例必须可由反例依据对应规则直接改写得出，不得额外添加反例中不存在的事实信息；确需补充动作或实物细节的示例，须在旁注明。

完成修改后执行自检脚本，确保所有契约检查通过：

```bash
python -B tests/check_repo.py
```

## 范例与许可

`references/fiction.md` 中的叙事工法范例均节选自已进入公有领域的作品，不使用自拟文本。

提交即表示贡献内容采用 MIT License 授权，且提交者拥有相应版权或合法授权。

问题反馈与建议请至 [GitHub Issues](https://github.com/chengzhi-c/natural-talk) 提交。
