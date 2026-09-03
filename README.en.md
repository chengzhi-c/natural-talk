# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

Make AI speak and write like a real person: genuine, direct, immersive, and free of synthetic tropes.

---

## Core Design

- **Rule Zero: Interaction Stance**: Converse as an experienced peer: direct answers, zero corporate platitudes, disclaimer wrappers, or performative praise.
- **Three Scenario Routes**:
  - **Conversational**: Conclusion first, natural paragraph development, total ban on antithetical lecturing (only affirmative statements), strict quantity compliance.
  - **Fiction & Narrative**: Camera-eye viewpoint (limited POV, Show, don't tell), no authorial mind-reading or moralizing, physical resistance, anti-cliché repetitive phrasing.
  - **Text Polishing**: Non-destructive micro-tuning, strictly preserving length (80%~100%) and facts, authentic human voice.

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
│   └── polish.md                    # Text cleanup & fidelity polishing reference
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

Text-layer rules and negative whitelist criteria are based on comparative research from [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone) (629 articles, ~2.83M words, 11 of 26 candidate features confirmed). Thanks for this work.

---

## License

[MIT](LICENSE)
