# Natural Talk

English | [中文](README.md)

<p align="center">
  <img src="assets/natural-talk.png" alt="Natural Talk" width="100%">
</p>

A rule set for making AI speak and write like a person. Works with Claude, ChatGPT, and any tool that supports system prompts.

**Strict edition.**

> The rules themselves are written for Chinese output. English users can still apply the framework; the trigger markers and examples target Chinese text.


## Core Principles

Three don'ts: no "as an AI", no "I hope this helps", no "great question".

Three dos: answer directly, say "I don't know" when you don't know, sound like a person rather than a machine.

The final test: would you say this to a friend?

Novels, roleplay, and other fiction scenarios are governed by a separate system: limited-perspective narration (only what the viewpoint character perceives and calculates in this moment; the author never steps out to summarize emotions), metaphors whose vehicles must be visible objects, and scenery rendered in the order a character's gaze actually resolves it. See `references/fiction.md` for the full rules.

## Quick Start

All rules live in the root `SKILL.md`, the single source of truth. Skill hosts (Claude Code, etc.) read it automatically; for API calls or other tools that accept a system prompt, inject the contents of `SKILL.md` directly.

### Claude Code Skill

```bash
cd ~/.claude/skills/
git clone -b strict https://github.com/chengzhi-c/natural-talk.git natural-talk-strict
```

`SKILL.md` sits at the repository root and is recognized as soon as the clone finishes.

### RikkaHub / SillyTavern

Import `natural-talk.zip` from the [Releases](https://github.com/chengzhi-c/natural-talk/releases) page.

### API

```python
system_prompt = open('SKILL.md', encoding='utf-8').read()

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
├── SKILL.md                         # Single source of truth (D/B/C/F/N rules; generation / cleanup / fiction generation / fiction cleanup)
├── references/                      # Rule details (fixes / examples / boundaries), read on demand
│   ├── rules-text.md                # Text layer B1–B11
│   ├── rules-dialogue.md            # Dialogue layer D1–D5 and experience layer C1–C6
│   └── fiction.md                   # Full fiction rules
├── scripts/                          # Maintainer checks (not loaded by the model)
│   ├── scan-mechanical.py            # Mechanical trigger candidate scan
│   ├── test-scan-mechanical.py       # Scanner fixture tests
│   ├── check-retention.py            # Rewrite retention-rate calc
│   ├── test-eval-harness.py          # Eval harness tests
│   ├── test-skill-contract.py        # Release-file contract test
│   └── fixtures/fiction-sample.txt    # Fiction scanning boundary fixture
├── evals/                            # Evaluation harness (maintainer benchmarking)
└── assets/
    └── natural-talk.png             # Brand image
```


## Not For

Academic papers, official documents, legal writing, marketing copy, speeches — scenarios that call for the opposite register. The rules yield to genre conventions there.

## Limitations

Most "AI flavor" in model writing comes from expression flaws formed during pretraining. At this stage, a skill or prompt can mainly remind and warn the model to avoid these issues; the actual effect still depends on the model's own ability to interpret instructions.

## Contributing

Misjudgment reports, before/after cases, and rule improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

The text-layer rules and the counter-list are grounded in the corpus study behind [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone) (629 articles, ~2.83 million characters; 11 of 26 candidate features survived testing). Credit to that work.

## License

MIT
