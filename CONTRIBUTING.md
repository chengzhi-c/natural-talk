# Contributing to Natural Talk Article

欢迎贡献文章版的改进建议、案例或翻译。

## 项目结构

- `core/rules.yaml` — **规则唯一源**。改规则只改这个文件，其余由 `python scripts/build.py` 生成。
- `docs/quick-reference.md` — 快速参考
- `docs/checklist.md` — 自检清单（可打印）
- `docs/detection.md` — 检测 AI 写作文章的信号
- `docs/examples.md` — before/after 改善案例
- `templates/system-prompt-standard.txt` — 标准版 system prompt（日常用）
- `templates/system-prompt-lite.txt` — 轻量版 system prompt（对 token 敏感）
- `scripts/check.py` — 规则自校验器
- `scripts/check-sync.py` — 多文件规则同步防漂移
- `scripts/eval-llm.py` — LLM 级效果评测
- `tests/cases.json` — 校验用例

## 开发流程

1. 改规则 → 只改 `docs/full-guide.md`
2. 同步其他文件（SKILL.md / README / quick-reference / 模板）
3. 新增或修改用例 → `tests/cases.json`
4. 跑 `python scripts/check.py` 和 `python scripts/check-sync.py`，必须全绿
5. `check-sync.py` 会自动检查规则块是否漂移；如果报 FAIL，说明同步没做对

## 贡献案例

提交的案例要有明确的 before/after 对比：

- ❌ AI 腔：展示典型的 AI 文章症状（空泛标题、空泛引入、三点并列、强行升华……）
- ✅ 自然：展示改法，并在下方列出优化点

案例格式见 `docs/examples.md` 现有 5 组。

## 贡献规则

- 新增规则要有实际支撑（不是猜测）
- 遵循现有文档风格
- 不适用范围要写清楚（学术论文、正式公文、营销文案、演讲稿等让位）

## License

MIT。详见 [LICENSE](LICENSE)。