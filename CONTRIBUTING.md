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

1. 按规则归属改对应权威源：日常对话与生成核心规则改 `SKILL.md`；编号规范（D/B/C/N 层）改 `references/rules-full.md`；叙事工法（B13–B18）改 `references/fiction.md`。改动跨层时，各层同步
2. 这条规则容易被过度执行时，在对应权威源补一条「什么不该改」；判断类规则直接补充自检做法
3. 拿改后的规则实际生成一段，人工读：规则是否生效，有没有误伤正常写法
4. 运行全量体检套件确保通过：`python -B scripts/verify_repo.py`

### 4. 翻译

- Fork 仓库
- 创建 `README.[language-code].md`
- 翻译 README 与核心规则说明
- 提交 Pull Request

## 提交前检查

- [ ] 规则改动已同步 `SKILL.md` 与对应 `references/` 文件
- [ ] 运行本地自动化体检套件全部通过：`python -B scripts/verify_repo.py`
- [ ] 契约测试通过：`python -B scripts/test-skill-contract.py`
- [ ] 拿改后的规则实际生成一段，人工读：规则是否生效，有没有误伤正常写法
- [ ] 新增规则有实际案例支撑
- [ ] Markdown 格式正确，无拼写错误

## 文件职责

| 路径 | 定位 | 说明 |
|------|------|------|
| `SKILL.md` | 蒸馏核心（生成模式核心规则 + 防误杀 + 模式判定） | Agent 入口，保持轻量 |
| `references/rules-full.md` | D/B/C/N 编号规范权威源（清理模式引用依据） | 清理类改动的主入口 |
| `references/fiction.md` | 叙事工法权威源（B13–B18）与 fiction 清理边界 | fiction 类改动的主入口 |
| `scripts/` | 扫描器、diff 审计、离线回归与全量体检套件 | 零依赖标准库，供提交前自查 |
| `evals/` | 冻结评测环、清理基准与判分（维护者侧） | 静态判分断言，跨版本稳定比较 |
| `assets/` | 品牌资源 | 保持文件名与相对路径 |

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
