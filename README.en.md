# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

Remove the AI tone from Chinese writing. Applies to everyday conversation, fiction writing, code discussion, prose cleanup, and fiction manuscript cleanup.

---

## Core Rules

Full rules and boundary conditions: [SKILL.md](SKILL.md) and [references/](references/).

| Rule | Explanation & Examples |
| --- | --- |
| **Direct Answers** | Address the question directly and state the conclusion in the first sentence. Omit pleasantries ("Good question", "Hope this helps") and avoid empty summary endings. |
| **Unprompted Inversion** | When premise A has not been asserted in context, do not write "not A, but B" (e.g., change "This is not an ordinary update, but a transformation" to "This is a transformation"). |
| **Narrative Dashes** | Do not use dashes in narration to explain causes, list items, or reveal conclusions; replace them with commas or normal sentence breaks. |
| **Action Adverbs** | Remove redundant adverbs modifying actions (e.g., "nodded slightly" → "nodded", "pushed open gently" → "pushed open"). |
| **Decorative Similes** | Avoid cliché similes lacking concrete sensory detail (e.g., "like a stagnant pool") and animalizing similes for human expressions or actions (e.g., "like a startled animal"). |
| **Unasked Disclaimers** | After giving a conclusion, do not append "However, this does not mean..." to refute ideas the user never raised; state applicable boundaries directly. |
| **Cleanup Principle** | Focus on intra-sentence edits; delete only content-free cliché phrases and preserve all original facts and meaning. |

---

## Usage

**One-line install (Skills CLI):**

```bash
npx skills add chengzhi-c/natural-talk
```

**Git repository integration (e.g., Claude Code):**

```bash
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

**Client Integrations:**

- **RikkaHub**: Go to Settings → Extensions → Skills, click `+`, select `natural-talk.zip` from [Releases](https://github.com/chengzhi-c/natural-talk/releases), and enable it.
- **SillyTavern**: Use `references/fiction.md` directly as the system prompt.

**Uninstallation:** Delete the corresponding directory or remove from the client's extension list.

---

## Scenario Assembly

Use `SKILL.md` as the base System Prompt. Append reference modules from `references/` as needed:

| Scenario | Recommended Combination | Description |
| --- | --- | --- |
| Daily Interaction / Code Discussion | `SKILL.md` | D-layer dialogue rules: direct answers, no filler |
| Technical Docs / Code Review | `SKILL.md` + `references/rules-full.md` | Draft first, then verify against R1–R8 |
| Fiction / Role-play | `SKILL.md` + `references/fiction.md` | Concrete sensory detail and action-driven pacing |
| Prose / Manuscript Cleanup | `SKILL.md` + `references/rules-full.md` (add `fiction.md` for fiction) | Intra-sentence edits while preserving original information |
| Diagnosis / Audit Only | Match relevant scenario rules | Output "Location + Rule ID + Brief Reason" only, without rewriting |

When the system prompt also contains character or background settings, place these rules before the settings.

---

## Directory Layout

```
natural-talk/
├── SKILL.md            # Core rules specification (Agent entry point)
├── README.md           # Chinese project documentation
├── README.en.md        # English project documentation
├── CONTRIBUTING.md     # Contributing and testing guide
├── LICENSE             # MIT Open Source License
├── references/         # Scenario-specific rule specifications (cleanup / fiction)
├── tests/              # Repository contract and consistency checks
└── assets/             # Static design assets
```

## Validation

Run the check script to verify links, formatting, and rule-ID reference integrity:

```bash
python -B tests/check_repo.py
```

## Narrative Technique Sources

The three technique examples in `references/fiction.md` are excerpts from:

| Technique | Source |
| --- | --- |
| Motion and body-weight progression | 朱自清《背影》(Zhu Ziqing, *Back View*) |
| Concrete objects as comparison | 郁达夫《春风沉醉的晚上》(Yu Dafu, *Intoxicated Spring Evening*) |
| People move, scenery follows | 鲁迅《社戏》(Lu Xun, *Village Opera*) |

## Not Applicable

Academic papers, official documents, legal documents, marketing copy, and speeches are excluded by default unless the user explicitly requests cleanup under these rules.

## Limitations

AI tone largely stems from expression habits formed during model pretraining. These rules guide the model through explicit constraints, while actual effectiveness depends on the model's instruction-following capability.

## Contributing

Misjudgment reports and before/after test cases are welcome: [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua): Chinese-first de-AI-tone rewrite skill.
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone): Chinese de-AI-tone prompt research.

## Community

[LINUX DO](https://linux.do).

## License

[MIT](LICENSE)
