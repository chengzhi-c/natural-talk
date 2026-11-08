# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

Remove the AI tone from Chinese writing. Applies to fiction writing (character, dialogue, scene and pacing), everyday conversation, code discussion, prose cleanup and fiction manuscript cleanup.

---

## Core Rules

Full rules and edge cases: [SKILL.md](SKILL.md) and [references/](references/).

| Rule | Explanation & Examples |
| --- | --- |
| **Direct Answers** | Address the user directly; give the conclusion in the first sentence. No "Good question" or "Hope this helps". |
| **Inversion (翻案)** | If not asserted before, do not write "not A but B" (e.g., change "This is not an ordinary update, but a transformation" to "This is a transformation"). |
| **Dashes** | In narration, do not use dashes to explain, enumerate, or conclude. Replace with commas or sentence breaks. |
| **Adverbs** | Remove redundant adverbs before actions (e.g., "nodded slightly" → "nodded", "pushed open gently" → "pushed open"). |
| **Cliché Similes** | Avoid mechanical similes (e.g., "like a tireless engine"); similes must have concrete sensory details. |
| **Translationese** | Avoid rigid connectives like "when...", "for...", "this means", "however/meanwhile". |
| **Dialogue & Viewpoint** | Avoid ping-pong dialogue; use concrete actions to advance scenes. Stay immersed in the character's viewpoint. |
| **Cleanup** | Primarily intra-sentence optimization; keep original intent and information intact, deleting only pure cliché fillers. |

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
- **SillyTavern**: Use `SKILL.md` directly as the system prompt.

**Uninstallation:** Delete the corresponding directory or remove from the client's extension list.

---

## Scenario Assembly

Use `SKILL.md` as the base System Prompt. Append reference modules from `references/` as needed:

| Scenario | Recommended Combination | Description |
| --- | --- | --- |
| Daily Interaction / Code Discussion | `SKILL.md` | D-layer constraints: direct answers, no filler |
| Technical Docs / Code Review | `SKILL.md` + `references/rules-full.md` | Compliance check against R1–R10 |
| Fiction / Role-play | `SKILL.md` + `references/fiction.md` | Sensory-first, action-driven pacing |
| Prose / Manuscript Cleanup | `SKILL.md` + `references/rules-full.md` | Intra-sentence optimization, preserve information |
| Diagnosis / Audit Only | Match relevant scenario rules | Output "Location + Rule ID + Reason" only |

When the system prompt contains character or background settings, place these rules at the beginning, followed by settings.

---

## Directory Layout

```
natural-talk/
├── SKILL.md            # Core rules specification (Agent entry point)
├── README.md           # Chinese project documentation
├── README.en.md        # English project documentation
├── CONTRIBUTING.md     # Contributing and testing guide
├── LICENSE             # MIT Open Source License
├── references/         # Scenario-specific rule specifications
├── tests/              # Repository contract and consistency checks
└── assets/             # Static design assets
```

## Validation

Execute the automated contract check to ensure cross-reference validity and structural integrity:

```bash
python -B tests/check_repo.py
```

This verification script comprehensively covers directory structure, Markdown link integrity, Frontmatter metadata, consistent line endings, sensitive data scanning, and the validity and cross-consistency of rule-ID references (R/B/C/D/N) across all documentation modules.

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
