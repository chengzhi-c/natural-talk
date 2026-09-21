# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

Make AI speak and write like a real person: genuine, direct, immersive — clean the mechanical tropes, keep the creative freedom.

---

## Design

- `SKILL.md`: core rules (bad→good pairs) plus anti-over-correction principles, keeping the context cost of daily dialogue minimal.
- `references/rules-full.md`: full D/B/C/N numbered spec — the citation basis for manuscript cleanup, where every edit must cite a rule ID.
- `references/fiction.md`: narrative craft. Camera-eye perspective by default, physical resistance over abstract emotion; ending types, narrative structures, and character voices stay free — only locatable mechanical traces are governed.
- `scripts/`: `scan-mechanical.py` scans long drafts; `audit-cleanup.py` audits cleanup outputs for information conservation and rule attribution.

---

## Measured Effects

<details>
<summary><b>Test setup</b></summary>

> `scripts/scan-mechanical.py` (gen mode) scans for rhetorical-inversion variants and dash density; every hit is locatable at character level. Short-text: 4 endpoints × 10 models × 6 scenes, 106 texts; fiction long-form: 10 models × 4 scenes, 38 texts of 2000-8000 chars each.

</details>

**Fiction long-form (10 models × 4 scenes × 38 texts)**:

| Model | Variants (total) | Dashes (total, legal in-sentence) |
| :--- | :---: | :---: |
| qwen3.8-27b / glm-5.3 / glm-5.3-flash / gemini-3.8 / step-5-preview / deepseek-v4-flash / longcat-2.0 | 0 | 0-4 |
| kimi-k2.6 / deepseek-v4-pro / minimax-m2.7 | 1 each | 0-4 |

> 35 of 38 texts score zero; the 3 remaining hits were manually reviewed — 2 legal reversals or concrete-object pairs, 1 genuine residual (minimax). FIX-level hits 0. Rule adherence is markedly higher with deep thinking enabled.
>
> No-skill baselines: glm-5.3 dual-arm control (same prompt, same card) without the skill 1 variant + 10 dashes + 20 REVIEW flags, with the skill 0 + 0 + 1; short-text adversarial scenes, 5 models bare, 0-2 variants/text.

**Long-form boundary**: with 20K+ character-card systems on weakly-compliant models, rhetorical inversions regress — an attention-decay limit of the model, not a rule failure; mitigations are in SKILL.md's scenario routing.

**Cleanup benchmark (17 frozen cases)**:

| Model | L1 failures | FIX clear rate | REVIEW clear rate | Over-deletion | Retention |
| :--- | :---: | :---: | :---: | :---: | :---: |
| kimi-k2.6 | 0/17 | 100% | 75% | 0/8 | 0.69–1.00 |
| qwen3.8-27b | 0/17 | 100% | 75% | 0/8 | 0.69–1.00 |
| deepseek-v4-flash | 5/17 | 100% | 64% | 3/8 | 0.23–1.00 |

> deepseek's 5 failures are all over-deletion (entity info evaporated); `audit-cleanup.py` mechanically flags all 5.

---

## Usage

> Model choice: `glm-5.3` / `qwen3.8-27b` follow instructions well. Rules only remind the model to avoid these patterns — execution depends on the model's own interpretation. Deep thinking markedly improves adherence; weakly-compliant models (longcat/minimax) leave residuals and need the scanner backstop.

```bash
# One-line install
npx skills add chengzhi-c/natural-talk

# Or clone into Claude Code / Cursor / Codex / Antigravity skills directory
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

**API usage**: read `SKILL.md` as the system prompt and append scenario references:

```python
system = Path("SKILL.md").read_text(encoding="utf-8")
# Fiction storytelling: append fiction.md
# Manuscript cleanup: append rules-full.md (edits must cite rule IDs)
# system += "\n\n" + Path("references/fiction.md").read_text(encoding="utf-8")
```

RikkaHub / SillyTavern: import `natural-talk.zip` from [Releases](https://github.com/chengzhi-c/natural-talk/releases).

---

## Layout

```
natural-talk/
├── SKILL.md            # Core rules (Agent entry point)
├── references/         # fiction.md narrative craft / rules-full.md full spec
├── scripts/            # Scanner, audit & verification suite
├── evals/              # Benchmark & scoring
└── assets/
```

## Boundaries

Academic papers, official documents, legal writing, marketing copy — the rules yield to genre conventions there. Most "AI flavor" stems from pretraining expression flaws; rules can only remind the model to avoid them, and the effect depends on the model's own interpretation ability.

## Contributing

Misjudgment reports and before/after cases welcome: [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua): information conservation, editing boundaries, and engineering evaluations.
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone): text-layer negative whitelist and empirical comparison criteria.

## Community

[LINUX DO](https://linux.do)

## License

[MIT](LICENSE)
