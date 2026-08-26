# 贡献指南

## 贡献方式

### 1. 报告问题

如果你发现规则有误判或遗漏：

- 在 GitHub 开 Issue
- 说明具体场景和触发条件
- 附上 before/after 文本片段

### 2. 提交案例

好的 before/after 对比案例帮助校准规则边界：

- 在 Issue 中提交，标注 `case` 标签
- 包含：场景说明、AI 腔版本（标注问题）、自然版本（标注改进点）

### 3. 改进规则

- 先开 Issue 讨论，说明为什么需要这条规则，提供实际案例支撑
- 等待反馈后再提交 PR

**规则修改流程**：

1. 改 `SKILL.md` 或 `templates/*.txt`（运行时实际读取的文件），并同步 `core/rules.yaml` 规则总表
2. 这条规则容易被过度执行时，往 `docs/misjudgments.md` 补一条「什么不该改」；判断类规则往 `docs/self-check.md` 补自检做法
3. 拿改后的规则实际生成一段，人工读：规则真的咬住了，且没伤到正常写法

### 4. 翻译

- Fork 仓库
- 创建 `docs/[language-code]/` 目录
- 翻译核心文档
- 提交 Pull Request

## 提交前检查

- [ ] 规则改动已同步到运行时文件（`SKILL.md` / `templates/*.txt`）与 `core/rules.yaml`
- [ ] 拿改后的规则实际生成一段，人工读：规则真的咬住了，且没伤到正常写法
- [ ] 新增规则有实际案例支撑
- [ ] Markdown 格式正确，无拼写错误

## 文件职责

| 文件 | 定位 | 格式要求 |
|------|------|----------|
| core/rules.yaml | 规则总表（供人阅读，运行时不读） | YAML 极简子集，含 severity/rationale |
| SKILL.md | 注入（skill 触发时进入 context） | 无 emoji；加粗仅标题 |
| templates/*.txt | 注入（system prompt 预设） | 纯平文本：无 emoji、无加粗 |
| docs/full-guide.md | 阅读参考（完整规则指南） | 允许格式；勿整体注入 |
| docs/misjudgments.md | 阅读参考（防矫枉案例） | 允许格式 |
| docs/self-check.md | 阅读参考（生成后自查） | 允许格式 |
| scripts/*.py | 真实生成评测 | 只依赖标准库，需 OPENAI_API_KEY |

## 不接受的贡献

- 纯理论讨论，没有实际案例
- 过于主观的风格偏好（没有普遍性）
- 与现有规则严重冲突的建议

## 版权说明

提交贡献即表示你同意：

- 你的贡献将采用 MIT License
- 你拥有贡献内容的版权或已获得授权

## 联系方式

- 在 [GitHub](https://github.com/chengzhi-c/natural-talk) 开 Issue
- 通过 GitHub Discussions 讨论
