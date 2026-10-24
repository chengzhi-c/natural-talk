# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

Make AI speak and write like a real person: concrete, direct, grounded; clean the mechanical tropes, keep the creative freedom.

---

## Core Rules

**Dialogue**:

1. First sentence delivers: avoid mechanical openers, the first sentence is the conclusion.
2. Answer A when asked A: take a stance, end on facts or a concrete next step.
3. Exact counts: asked for 3, give exactly 3.
4. Honor word counts: given a range, deliver it; 20% over or under gets compressed or padded, count when done.
5. No rhetorical inversions: "it's not A, it's B" banned unless A was actually asserted ("no A, only B" and similar patterns included).
6. No macro openers: "In today's world… / With the development of…" cut unless it carries concrete context.
7. Dashes only for interrupted speech.
8. Multi-turn and length: a one-line question gets a short answer; don't restate the previous turn or repeat a point already made.

**Exposition**:

9. Openers and prompt-word shells: "说白了 / 先说结论" and "一句话总结： / 核心是：" cut; the first sentence goes straight to substance.
10. Dense enumeration and numbered headings: three or more items strung with enumeration commas in one clause is too dense (technical name strings and statute lists exempt); "I. II. III." section headings three in a row is template feel.
11. Zero-anaphora openers and summary-over-specifics: a paragraph starting with "值得注意的是" with no "this/that" anchor in the sentence; asserting "significantly improved" while the concrete number sits in the same paragraph.
12. Translationese, exactly five forms: overlong fronted modifiers, "当……时" clauses, "对于……来说" topic shells, "然而/此外" sentence-initial signposts, "这意味着" restating the previous sentence.

**Narrative**:

13. Abstract-word reversal pairs banned; concrete actions and sensory facts pass.
14. No placeholders in prose: "{{char}} / 某某 / XXX" appearing verbatim breaks the setting; give a concrete name or an identifiable epithet.
15. "微微/轻轻/缓缓"-style adverb hedges on action cut; the verb carries the weight. Objective states of light, sound and temperature are exempt.
16. "猛地一僵/瞳孔骤缩/低吼一声" freeze-tropes become stillness and held breath; tension carried by what the character is already doing.
17. Five or more consecutive standalone dialogue lines with no narrative between them is ping-pong (runs of four or fewer are fine). A line that is one quoted speech counts, and so does one whose only narrative is a tag of four characters or fewer; a line of real narrative breaks the run.
18. Decorative dialogue tags ("commanded / intoned / growled") zeroed out.
19. Similes must add sensory information; a tail simile on end-of-clause is fine once, a pattern when it appears at least five times and exceeds 8% of sentences.
20. Counting tics: the author doesn't count beats ("one, two, three", "after three breaths"); a character counting is plot and passes.

Dialogue boundary: a run of short lines with no narration in between is the defect. Fix it by inserting narration or compressing rounds into reported speech, not by making the character talk more. An all-reported-speech scene is the same defect in different clothes; keep reported speech for procedural rounds only.

Cleanup mode: in-place surgery, information conservation, rule-ID citations. Anti-over-correction principles protect questions, parallelism, and repeated technical terms; when in doubt, don't touch.

Mechanical backstops: `scripts/scan-mechanical.py` scans drafts; `audit-cleanup.py` audits cleanup outputs.

---

## Measured Effects

9 models × 3 scenarios (fiction writing / prose cleanup / daily dialogue), each paired
with a no-skill control arm: 216 generations in total. Change in AI-tone density
(mechanical-layer hits per 1000 characters):

| Model | Control | With skill | Drop |
| :--- | ---: | ---: | ---: |
| deepseek-v4-flash-0731 | 5.33 | 2.35 | -56% |
| deepseek-v4-pro-0813 | 4.97 | 3.01 | -39% |
| deepseek-v4.1-flash-1017 | 4.19 | 1.07 | -74% |
| gemini-3.8-flash-high | 5.29 | 2.18 | -59% |
| kimi-k2.6 | 5.35 | 2.04 | -62% |
| kimi-k3 | 6.08 | 0.66 | -89% |
| mimo-v2.6-pro | 5.47 | 2.23 | -59% |
| qwen3.8-flash | 5.91 | 2.00 | -66% |
| step-5-preview | 5.34 | 2.33 | -56% |
| **Mean** | **5.33** | **1.99** | **-63%** |

All 9 models improved, from -39% to -89%; none failed.

Supplementary GLM measurements (listed separately, not merged into the table above):

| Model | Control | With skill | Drop |
| :--- | ---: | ---: | ---: |
| glm-5.3 | 6.23 | 0.44 | -93% |
| glm-5.3-flash | 5.50 | 0.56 | -90% |

<details>
<summary>Measurement conditions</summary>

Measurement conditions: thinking enabled with reasoning_effort = max (all models);
temperature = 1.0 (the client takes 1.0 for None when reasoning is on, so every
model ran at 1.0); max_tokens = 20000 with a 2400s timeout. Each model produced 12
texts (4 fiction prompts / 4 cleanup cases / 4 daily questions); the skill arm and
the none arm answer the same prompts, one generation per cell, no repeated sampling,
no variance. Limitation: this is a single-sample comparison, so absolute values are
an order-of-magnitude reference rather than a stable estimate, and the drop range
shifts with the prompts.

</details>

False-positive control: 88,000 characters of human writing by 9 authors (Lu Xun,
Zhou Zuoren, Liang Shiqiu, Wang Zengqi, Wang Xiaobo, Yu Qiuyu, Zhu Ziqing,
Lin Yutang, Shen Congwen) were scanned in full by the scanner: zero FIX-level hits; REVIEW-level
candidates were judged case by case by hand, not by an automatic verdict.

---

## Usage

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
├── CONTRIBUTING.md     # Contributing guide
├── LICENSE             # MIT
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
