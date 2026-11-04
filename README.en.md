# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

Remove the AI tone from Chinese writing. Applies to fiction writing (character, dialogue, scene and pacing), everyday conversation, code discussion, prose cleanup and fiction manuscript cleanup.

---

## Core Rules

Full rules and edge cases: [SKILL.md](SKILL.md) and [references/](references/).

| Scenario | Essentials |
| --- | --- |
| Dialogue | Lead with the conclusion; answer A when asked A, no closing elevation; honor counts and lengths; cut "great question"/"hope this helps" openers and closers and "let me summarize" shells; refer to earlier turns in the user's own words and keep one-question answers short. |
| Exposition | Cut prompt shells and macro openers; no rhetorical inversion unless A was actually asserted; five translationese forms, and do not newly write "this means" restatements (leave them in cleanup); keep enumeration commas from getting dense; numbered headings are fine when each section has its own content, and existing numbers stay in cleanup; a colon that only introduces a list stays; no dash whose right side carries explanation, enumeration, apposition, cause, supplement or reveal; do not turn an unsourced claim into fact; keep vague attributions and summary words as-is in cleanup. |
| Narrative | Keep viewpoint present and actions physical; treat decorative adverbs, physiological clichés, counting tics and decorative dialogue tags as candidates and keep them when they carry information; similes need sensory gain; no four or more consecutive standalone dialogue lines. |
| Cleanup | Prefer in-sentence rewriting; deletions only where a rule authorizes them; conserve information; every change must map to a rule ID; when in doubt, don't touch. Whole-sentence deletions need the user's consent, except pure clichés under B5/B6/B7 after confirming no equivalent information is lost, and redundant dialogue rounds under B8 from the fourth line on whose removal changes no situation or observable fact. |

## Results

One fiction prompt, 16 models, two drafts each: one with the rules disabled, one with `SKILL.md` and `references/fiction.md` enabled. AI-tone density (hits per 1,000 characters):

| Model | Baseline | With skill | Change |
| --- | ---: | ---: | ---: |
| deepseek-v4-flash-0731 | 4.6 | 3.3 | -28% |
| deepseek-v4-pro-0813 | 7.5 | 2.4 | -68% |
| deepseek-v4.1-flash | 4.8 | 1.6 | -67% |
| gemini-3.8-flash | 6.9 | 2.3 | -67% |
| gemini-4-argon | 6.5 | 0.0 | -100% |
| glm-5.3 | 3.4 | 1.0 | -71% |
| glm-5.3-flash | 7.1 | 1.5 | -79% |
| gpt-6.1-sol | 8.0 | 1.4 | -82% |
| grok-4.7 | 3.8 | 1.1 | -71% |
| kimi-k2.6 | 8.3 | 3.5 | -58% |
| kimi-k3 | 4.7 | 0.0 | -100% |
| mimo-v2.6-pro | 5.0 | 4.5 | -10% |
| minimax-m3 | 6.3 | 2.8 | -56% |
| minimax-m3.1-flash | 7.3 | 5.9 | -19% |
| qwen3.8-flash | 4.5 | 1.0 | -78% |
| step-5-preview | 11.1 | 7.3 | -34% |
| **Mean** | **6.24** | **2.48** | **-60%** |

This is an informal test: hit counts vary with the prompt and the sample, and do not measure model capability. Seven of the 16 drafts in the rules-enabled group fall short of the prompt's 2,000-character minimum; every baseline draft clears it, six baseline drafts exceed the 3,000-character maximum, and one rules-enabled draft does too.

<details>
<summary>Measurement setup</summary>

| Item | Value |
| --- | --- |
| Prompt | One fiction prompt (a 24-hour pharmacy under a flyover, 2,000–3,000 characters), full text in [examples/README.md](examples/README.md) |
| Sample | One draft per model per condition, 32 drafts in total |
| Rules disabled | A single system line: you are a Chinese writing and code-discussion assistant; complete the request. |
| Rules enabled | Full `SKILL.md` and `references/fiction.md` |
| Sampling | temperature 1.0, reasoning_effort high, max_tokens 32000 |
| Counting | Hits per 1,000 characters = total hits (B1–B9 plus viewpoint) ÷ characters × 1,000, one decimal; mean = arithmetic average of the 16 per-1,000 rates, and drop = change in that rate |

</details>

Per-rule breakdowns, character counts and all 32 texts: [examples/README.md](examples/README.md). Hits count only the patterns the rules name; they do not measure text quality.

---

## Usage

One-line install:

```bash
npx skills add chengzhi-c/natural-talk
```

Or clone into a skills directory (Claude Code shown):

```bash
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

RikkaHub: Settings → Extensions → Skills → `+`, pick `natural-talk.zip` from [Releases](https://github.com/chengzhi-c/natural-talk/releases); enable it after installing. Main package: `SKILL.md`, `references/`, `LICENSE`.

SillyTavern: use `SKILL.md` as the system prompt; for fiction or cleanup, append the corresponding references from the table below.

Packaging it yourself: the release archive holds only `SKILL.md`, `references/fiction.md`, `references/rules-full.md` and `LICENSE`; zip those four and you have `natural-talk.zip`.

Uninstall: delete `~/.claude/skills/natural-talk`; in RikkaHub disable or remove it from the skills list; in SillyTavern delete the corresponding section from the system prompt.

---

## API / Rule usage:

| Scenario | Append |
| --- | --- |
| Daily dialogue / general generation / general code discussion | `SKILL.md` (the D layer applies to dialogue and general generation) |
| Code review / PR description / commit message / technical long-form | `SKILL.md`; after drafting, check the draft against `references/rules-full.md` (R1–R10) |
| Fiction writing, continuation, stories and role-play, fan fiction, character cards | `SKILL.md` + `references/fiction.md` |
| Translation | `SKILL.md` (fidelity first; translationese rule R6 does not apply to translations) |
| Prose cleanup | `SKILL.md` + `references/rules-full.md` |
| Fiction manuscript cleanup | `SKILL.md` + the brought-in R entries and the "清理边界" section of `references/rules-full.md`; `references/fiction.md` for the basic principles and B1–B9 |
| Point out problems only, no rewriting | Read the cleanup-mode references; deliver "location + rule ID + one-line reason". Diagnosis uses cleanup thresholds (report only, no rewriting; consecutive dialogue counted at ≥4 lines); code debugging or review does not follow this row |
| Explain each change after cleanup | Cleanup scenario plus the full `references/rules-full.md` |

When the system prompt also carries user settings, put the rules first and the settings after.

---

## Layout

```
natural-talk/
├── SKILL.md            # Core rules (Agent entry point)
├── README.md           # Chinese documentation
├── README.en.md        # English documentation
├── CONTRIBUTING.md     # Contributing guide
├── LICENSE             # MIT
├── references/         # Full rules
├── tests/              # Structure and contract checks
├── examples/           # Fiction comparison and texts
└── assets/
```

## Validation

`python -B tests/check_repo.py` checks structure, links, frontmatter, line endings and rule-ID references, recomputes the character counts and per-1,000 conversion, and verifies totals against their per-rule parts. The scanner, cleanup audit and model evals are not part of this repository.

## Narrative Technique Sources

The three technique examples in `references/fiction.md` are excerpts from:

| Technique | Source |
| --- | --- |
| Motion and body-weight progression | 朱自清《背影》(Zhu Ziqing, *Back View*) |
| Concrete objects as comparison | 郁达夫《春风沉醉的晚上》(Yu Dafu, *Intoxicated Spring Evening*) |
| People move, scenery follows | 鲁迅《社戏》(Lu Xun, *Village Opera*) |

## Not For

Not for academic papers, official documents, legal writing, marketing copy or speeches, which call for the opposite register; the exception is a user explicitly asking to clean such a text with this skill.

## Limitations

Most AI tone comes from expression habits formed in pretraining. The skill can only remind the model to avoid them; actual results depend on how well it interprets the rules.

## Contributing

Misjudgment reports and before/after cases welcome: [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua): Chinese-first de-AI-tone rewrite skill.
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone): Chinese de-AI-tone prompt research.

## Community

[LINUX DO](https://linux.do).

## License

[MIT](LICENSE)
