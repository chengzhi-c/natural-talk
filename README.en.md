# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

Make AI speak and write like a real person: genuine, direct, immersive, and free of synthetic tropes.

> **Editions**: For the strict edition, see [`natural-talk-strict`](https://github.com/chengzhi-c/natural-talk/tree/strict).

---

## Core Design

- **Rule Zero: Interaction Stance**: Converse as an experienced peer: direct answers, zero corporate platitudes, disclaimer wrappers, or performative praise.
- **Four Scenario Routes**:
  - **Dialogue & Interaction**: Direct answers, natural paragraph flow, affirmative statements, strict compliance with count constraints.
  - **Fiction & Narrative**: Camera-eye perspective (limited POV, Show, don't tell), physical resistance, no authorial mind-reading, natural pronoun cadence.
  - **Text Polishing**: Preserving length (80%~100%) and facts, zero narrative dashes, metaphors grounded in concrete objects.
  - **Restraint & Subtext**: Deep tension and subtext, grounding unstated emotions in physical handling and daily details without authorial monologue.

---

## Quick Start

### 1. Agent Skill Installation

```bash
# Option 1: One-line install via npx skills
npx skills add chengzhi-c/natural-talk

# Option 2: Clone into Claude Code / Cursor / Codex / Antigravity skills directory
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

### 2. System Prompt or Agent Tool Usage

Read `SKILL.md` directly as the primary prompt and attach scenario guides from `references/` on demand:

**API Example**:
```python
from pathlib import Path
from openai import OpenAI

client = OpenAI()
root = Path("path/to/natural-talk")

# Load primary rules, append scenario references as needed
system_prompt = (root / "SKILL.md").read_text(encoding="utf-8")
# For fiction storytelling:
# system_prompt += "\n\n" + (root / "references" / "fiction.md").read_text(encoding="utf-8")

response = client.chat.completions.create(
    model="your-model-name",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Your prompt here"}
    ]
)
print(response.choices[0].message.content)
```

### 3. RikkaHub / SillyTavern

Import `natural-talk.zip` from [Releases](https://github.com/chengzhi-c/natural-talk/releases).

---

## Repository Layout

```
natural-talk/
├── SKILL.md                         # Primary specification & conversational core (Agent entry point)
├── references/                      # Vertical scenario reference guides (on-demand reading)
│   ├── dialogue.md                  # Dialogue & character voice guidelines
│   ├── fiction.md                   # Fiction narrative & literary tension reference
│   ├── polish.md                    # Text cleanup & fidelity polishing reference
│   └── specialized/                 # Restrained tension & subtext guidelines
├── scripts/                         # Automated contract & repository verification suite (verify_repo.py)
├── evals/                           # Evaluation benchmark and cases
└── assets/                          # Static assets
```

---

## Not For

Academic papers, official documents, legal writing, marketing copy, speeches — scenarios that call for the opposite register. The rules yield to genre conventions there.

---

## Limitations

Most "AI flavor" in model writing comes from expression flaws formed during pretraining. At this stage, a skill or prompt can mainly remind and warn the model to avoid these issues; the actual effect still depends on the model's own ability to interpret instructions.

---

## Contributing

Misjudgment reports, before/after cases, and rule improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Acknowledgements

- [shuorenhua](https://github.com/MrGeDiao/shuorenhua): Chinese-first rewrite skill; thanks for its exploration and insights into editing boundaries, information conservation, and engineering evaluations.
- [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone): Text-layer rules and negative whitelist criteria are based on comparative research from this project (629 articles, ~2.83M words, 11 of 26 candidate features confirmed).

---

## Community

Join the [LINUX DO](https://linux.do) community — "a new ideal type of community".

---

## License

[MIT](LICENSE)
