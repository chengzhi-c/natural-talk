# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

A rule set for making AI speak and write like a person. Works with Claude, ChatGPT, and any tool that supports system prompts.

> The rules themselves are written for Chinese output. English users can still apply the framework; the trigger markers and examples target Chinese text.

## Core Principles

Three don'ts: no "as an AI", no "I hope this helps", no "great question".

Three dos: answer directly, say "I don't know" when you don't know, sound like a person rather than a machine.

The final test: would you say this to a friend?

Novels, roleplay, and other fiction scenarios are governed by a separate system: limited-perspective narration (only what the viewpoint character perceives and calculates in this moment; the author never steps out to summarize emotions), metaphors whose vehicles must be visible objects, and scenery rendered in the order a character's gaze actually resolves it. See `templates/system-prompt-fiction.txt` for the full rules with annotated examples.

## Quick Start

Pick a template for your scenario and paste its contents into your system prompt:

| Scenario | File | Notes |
|----------|------|-------|
| Everyday chat | `templates/system-prompt-standard.txt` | Default recommendation |
| Fiction | `templates/system-prompt-fiction.txt` | Novels, roleplay, fanfic, emotional writing |
| Token-sensitive | `templates/system-prompt-lite.txt` | Minimal core rules |

`templates/preset-*.txt` are four scenario presets (customer service, tech blog, social media, fiction) layered on top of the templates above.

### Claude Code Skill

```bash
cd ~/.claude/skills/
git clone https://github.com/chengzhi-c/natural-talk.git
```

`SKILL.md` sits at the repository root and is recognized as soon as the clone finishes.

### RikkaHub / SillyTavern

Import `natural-talk.zip` from the [Releases](https://github.com/chengzhi-c/natural-talk/releases) page.

### API

```python
system_prompt = open('templates/system-prompt-fiction.txt').read()

response = client.chat.completions.create(
    model="<your-model>",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "your question"}
    ]
)
```

## Repository Layout

```
natural-talk/
├── SKILL.md                         # Single source of truth (generation / cleanup / fiction modes)
├── templates/
│   ├── system-prompt-standard.txt   # Chat injection
│   ├── system-prompt-fiction.txt    # Fiction injection (with annotated examples)
│   ├── system-prompt-lite.txt       # Lightweight version
│   └── preset-*.txt                 # Scenario presets
└── docs/
    ├── full-guide.md                # Reading guide (points to SKILL.md)
    ├── self-check.md                # Self-check list
    └── misjudgments.md              # Against over-correction
```

## Not For

Academic papers, official documents, legal writing, marketing copy, speeches — scenarios that call for the opposite register. The rules yield to genre conventions there.

## Limitations

Most "AI flavor" in model output traces back to pretraining. A skill or prompt can only remind and warn; the effect also depends on the model's own ability to interpret instructions.

## Contributing

Misjudgment reports, before/after cases, and rule improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

The text-layer rules and the counter-list are grounded in the corpus study behind [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone) (629 articles, ~2.83 million characters; 11 of 26 candidate features survived testing). Credit to that work.

## License

MIT
