# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

Make AI speak and write like a real person: genuine, direct, immersive; clean the mechanical tropes, keep the creative freedom.

---

## Core Rules

**Dialogue**:

1. First sentence delivers: avoid mechanical openers, the first sentence is the conclusion.
2. Answer A when asked A: take a stance, end on facts or a concrete next step.
3. Exact counts: asked for 3, give exactly 3.
4. No rhetorical inversions: "it's not A, it's B" banned unless A was actually asserted ("no A, only B" and similar patterns included).
5. No macro openers: "In today's world… / With the development of…" cut unless it carries concrete context.
6. Dashes only for interrupted speech.

**Narrative**:

7. Abstract-word reversal pairs banned; concrete actions and sensory facts pass.
8. "微微/轻轻/缓缓"-style adverb hedges on action cut; the verb carries the weight.
9. "猛地一僵/瞳孔骤缩/低吼一声" freeze-tropes become stillness and held breath; tension written as physical strain.
10. Decorative dialogue tags ("commanded / intoned / growled") zeroed out.

Cleanup mode: in-place surgery, information conservation, rule-ID citations. Three anti-over-correction principles protect questions, parallelism, and author habits.

Mechanical backstops: `scripts/scan-mechanical.py` scans drafts; `audit-cleanup.py` audits cleanup outputs.

---

## Measured Effects

<details>
<summary><b>Test setup</b></summary>

> `scripts/scan-mechanical.py` (gen mode) scans for rhetorical-inversion variants and dash density; every hit is located by line with its trigger snippet. Short-text: 4 endpoints × 10 models × 6 scenes, 106 texts; fiction long-form: 10 models × 4 scenes, 38 texts of 2000-8000 chars each; full-scenario batteries (3 scenarios, same-prompt long-scene A/B, multi-turn RP, romance prompt) cover mimo-v2.6-pro / minimax-m3.1-flash-preview / kimi-k3, plus 7 daily-dialogue tasks.

</details>

**Fiction**:

| Model | FIX-level hits | Genuine residuals |
| :--- | :---: | :---: |
| qwen3.8-27b / glm-5.3 / glm-5.3-flash / gemini-3.8 / step-5-preview / deepseek-v4-flash / longcat-2.0 | 0 | 0 |
| kimi-k2.6 / deepseek-v4-pro / minimax-m2.7 | 0 | 1 (minimax-m2.7) |
| mimo-v2.6-pro | 0 | 2 |
| minimax-m3.1-flash-preview / kimi-k3 | 0 | 0 |

> Long-form benchmark (38 texts): 35 score zero; the 3 raw residuals were manually reviewed down to 1 genuine (minimax-m2.7), the other 2 being legal reversals and concrete-object pairs. Battery results: mimo-v2.6-pro's 13 B1-variant candidates all reviewed as legal forms (concrete action pairs, second-person colloquialisms, in-dialogue exemption); its genuine residuals are 2 reveal-type dashes (1 enumeration, 1 flashback); minimax-m3.1-flash-preview and kimi-k3 have none, and all their dashes are legal speech interruptions or cut-offs. Rule adherence is markedly higher with deep thinking enabled.
>
> No-skill baselines: glm-5.3 dual-arm control (same prompt, same card) without the skill 1 variant + 10 reveal-type dashes + 20 REVIEW flags, with the skill 0 + 0 + 1; mimo-v2.6-pro same-prompt 20 REVIEW flags without the skill (including 5 reveal-type dashes), 11 with it (including 2); minimax-m3.1-flash-preview 10 → 6. Short-text adversarial scenes, 5 models bare, 0-2 variants/text.

**Long-form boundary**: with 20K+ character-card systems on weakly-compliant models, rhetorical inversions regress, an attention-decay limit of the model, not a rule failure; mitigations are in SKILL.md's scenario routing.

**Cleanup benchmark (17 frozen cases)**:

| Model | L1 failures | FIX clear rate | REVIEW clear rate | Over-deletion | Retention |
| :--- | :---: | :---: | :---: | :---: | :---: |
| glm-5.3 | 0/17 | 100% | 71% | 0/8 | 0.66–1.00 |
| kimi-k2.6 | 0/17 | 100% | 68% | 0/8 | 0.69–1.00 |
| qwen3.8-27b | 0/17 | 100% | 81% | 0/8 | 0.65–1.00 |
| deepseek-v4-flash | 4/17 | 100% | 55% | 3/8 | 0.70–1.00 |

> All four L1 failures come from deepseek-v4-flash and are all over-deletion (dropping a legal rebuttal's premise clause, dropping step ordinals, under-retention, a term swapped for a synonym); `audit-cleanup.py` catches all four mechanically; L2 warnings are residual tropes left in outputs (soft).

---

## Usage

> Model choice: `glm-5.3` / `qwen3.8-27b` / `kimi-k2.6` score zero failures on the cleanup benchmark and follow instructions well; `deepseek-v4-flash` over-deletes noticeably (4/17 failures, 3/8 over-deletion) and needs the `audit-cleanup.py` backstop on cleanup drafts. Rules only remind the model to avoid these patterns; execution depends on the model's own interpretation. Deep thinking markedly improves adherence; weakly-compliant models (longcat/minimax) leave residuals and need the scanner backstop.

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

## Not For

Academic papers, official documents, legal writing, marketing copy, speeches: scenarios that call for the opposite register. The rules yield to genre conventions there.

## Limitations

Most "AI flavor" in model writing comes from expression flaws formed during pretraining. At this stage, a skill or prompt can mainly remind and warn the model to avoid these issues; the actual effect still depends on the model's own ability to interpret instructions.

## Contributing

Misjudgment reports and before/after cases welcome: [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua): Chinese-first rewrite skill; thanks for its exploration and insights into information conservation, editing boundaries, and engineering evaluations.
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone): Chinese de-AI-tone prompt research; thanks for its empirical comparative study and criteria for the text-layer negative whitelist.

## Community

Join the [LINUX DO](https://linux.do) community, "a new ideal type of community".

## License

[MIT](LICENSE)
