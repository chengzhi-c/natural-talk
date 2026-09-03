# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

Make AI speak and write like a real person: genuine, direct, immersive, and free of synthetic tropes.

---

## Core Design

- **Rule Zero**: Fact & setting conservation, dialogue complete exemption, style freedom (eliminates synthetic AI tropes only).
- **Three Mental Models**:
  - **Conversational**: Direct answers, zero corporate platitudes, honest boundaries.
  - **Fiction & Narrative**: Camera-eye viewpoint (Show, don't tell), characters living in scene, no authorial moralizing.
  - **Text Polishing**: Non-destructive micro-tuning, preserving original facts, length, and authentic voice.

---

## Quick Start

### 1. Agent Skill Installation

```bash
# Option 1: One-line install via npx skills
npx skills add chengzhi-c/natural-talk

# Option 2: Clone into Claude Code / Cursor / Codex skills directory
git clone https://github.com/chengzhi-c/natural-talk.git ~/.claude/skills/natural-talk
```

### 2. System Prompt Injection

Pick a template from `templates/` matching your scenario:

| Scenario | Template File | Description |
| :--- | :--- | :--- |
| **Everyday Chat & General** | [`templates/system-prompt-standard.txt`](templates/system-prompt-standard.txt) | Eliminates customer-service platitudes |
| **Fiction & Storytelling** | [`templates/system-prompt-fiction.txt`](templates/system-prompt-fiction.txt) | Viewpoint immersion, subtext in dialogue |
| **Token-Sensitive / Lite** | [`templates/system-prompt-lite.txt`](templates/system-prompt-lite.txt) | Concentrated high-yield core rules |

`templates/preset-*.txt` provide presets for customer support, tech blogging, and social media.

**API Example**:
```python
from openai import OpenAI

client = OpenAI()
system_prompt = open('templates/system-prompt-fiction.txt', encoding='utf-8').read()

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
├── SKILL.md                         # Single source of truth (Conversational / Fiction / Polishing)
├── references/                      # Detailed guidance and case library (on-demand reading)
│   ├── polish.md                    # Text cleanup & polishing reference
│   ├── dialogue.md                  # Dialogue & character voice guidelines
│   └── fiction.md                   # Fiction writing reference
├── templates/                       # Injection prompt templates
│   ├── system-prompt-standard.txt   # Everyday chat template
│   ├── system-prompt-fiction.txt    # Fiction template
│   ├── system-prompt-lite.txt       # Minimalist compact template
│   └── preset-*.txt                 # Scenario presets
├── scripts/                         # Maintenance, linter, and verification scripts
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
