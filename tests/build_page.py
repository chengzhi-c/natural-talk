"""由 examples/README.md 生成 examples/对照.html。

数值、计数口径表、未计入清单全部从 README 解析，页面里不重打一遍。
Run: python -B tests/build_page.py <repo-root> [--check]
--check 只比对不写文件，供 CI 用。
"""
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

args = [a for a in sys.argv[1:] if not a.startswith("-")]
ROOT = Path(args[0] if args else ".").resolve()
EXAMPLES = ROOT / "examples"

section = ""
totals, splits = {}, {}
prompt = []
rules, note, excluded, intro = [], [], [], []

for raw in (EXAMPLES / "README.md").read_text(encoding="utf-8").split("\n"):
    line = raw.rstrip()
    if line.startswith("## "):
        section = line[3:].strip()
        continue
    if section == "提示词" and line.startswith(">"):
        text = line[1:].strip()
        if text:
            prompt.append(text)
        continue
    if section == "计数口径" and line and not line.startswith("|"):
        if line.startswith("本表口径"):
            note.append(line)
        elif line.startswith("编号对应"):
            intro.append(line)
        continue
    if section == "未计入的内容" and line.startswith("- "):
        excluded.append(line[2:].strip())
        continue
    if not line.startswith("|"):
        continue
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if not cells or cells[0] in {"模型", "编号"} or set("".join(cells)) <= set("-: "):
        continue
    if section == "合计" and len(cells) == 7:
        totals[cells[0]] = cells[1:]
    elif section == "分项" and len(cells) == 11:
        splits[cells[0]] = cells[1:]
    elif section == "计数口径" and len(cells) == 2:
        rules.append((cells[0], cells[1]))

models = list(totals)
assert models and set(models) == set(splits), "合计与分项表不一致"

assert len(rules) == 10, "计数口径表应涵盖 B1–B9 与视点"
RULE_ROWS = rules
SPLIT_HEAD = [code for code, _ in RULE_ROWS]
assert note, "计数口径表下缺少口径说明段"
assert intro, "计数口径一节缺少导语"
NOTE = re.sub(r"`([^`]+)`", r"<code>\1</code>", note[0])
INTRO = re.sub(r"`([^`]+)`", r"<code>\1</code>", intro[0])
assert excluded, "未计入的内容一节缺少条目"
EXCLUDED = "\n".join(
    "        <li>" + re.sub(r"`([^`]+)`", r"<code>\1</code>", item) + "</li>"
    for item in excluded)
sum_base = sum(int(totals[m][0]) for m in models)
sum_skill = sum(int(totals[m][1]) for m in models)
improved = sum(1 for m in models if float(totals[m][5]) < float(totals[m][4]))
peak = max(float(totals[m][4]) for m in models)
peak_skill = max(float(totals[m][5]) for m in models)
scale = peak or 1.0
low_skill = sum(1 for m in models if int(totals[m][3]) < 2000)
over_base = sum(1 for m in models if int(totals[m][2]) > 3000)


def pct(base, skill):
    base, skill = float(base), float(skill)
    if not base:
        return "持平"
    change = (skill - base) / base * 100
    return "持平" if round(change) == 0 else f"{change:+.0f}%"


def tone_of(base, skill):
    base, skill = float(base), float(skill)
    return "down" if skill < base else ("up" if skill > base else "flat")


def pair(base, skill, tone):
    return (
        f'<span class="pair {tone}"><span class="was">{base}</span>'
        f'<span class="arrow">→</span><span class="now">{skill}</span></span>'
    )


def bar(value, kind):
    width = max(float(value) / scale * 100, 0)
    return f'<span class="bar"><span class="bar-fill {kind}" style="width:{width:.1f}%"></span></span>'


def total_row(model):
    base, skill, words_base, words_skill, rate_base, rate_skill = totals[model]
    rate_tone = tone_of(rate_base, rate_skill)
    return (
        "      <tr>"
        f'<th scope="row">{model}</th>'
        f'<td class="num">{pair(base, skill, tone_of(base, skill))}</td>'
        f'<td class="num delta {rate_tone}">{pct(rate_base, rate_skill)}</td>'
        f'<td class="num rate">{pair(rate_base, rate_skill, rate_tone)}'
        f'{bar(rate_base, "base")}{bar(rate_skill, "skill")}</td>'
        f'<td class="num soft">{words_base}<span class="sep"> / </span>{words_skill}</td>'
        "</tr>"
    )


def split_row(model):
    cells = "".join(
        f'<td class="split {tone_of(*pair.split("/"))}">'
        f'<span class="was">{pair.split("/")[0]}</span>'
        f'<span class="sep">/</span>'
        f'<span class="now">{pair.split("/")[1]}</span></td>'
        for pair in splits[model]
    )
    return f'      <tr><th scope="row">{model}</th>{cells}</tr>'


CSS = """
  :root {
    --ink: #23202a;
    --ink-soft: #5d5763;
    --ink-faint: #8b8494;
    --line: #e4dfe8;
    --paper: #fbf9f6;
    --card: #ffffff;
    --accent: #8c4a26;
    --accent-soft: #f2e6de;
    --down: #1f7a55;
    --up: #ac4f28;
    --radius: 10px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --ink: #eceaf1;
      --ink-soft: #b3aebd;
      --ink-faint: #857f92;
      --line: #33303c;
      --paper: #14131a;
      --card: #1b1a23;
      --accent: #d79a6e;
      --accent-soft: #2a2229;
      --down: #5fc79b;
      --up: #e5916a;
    }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font: 400 16px/1.72 "PingFang SC", "MiSans", "HarmonyOS Sans SC",
          "Source Han Sans SC", "Microsoft YaHei UI", "Microsoft YaHei",
          system-ui, sans-serif;
    font-feature-settings: "tnum" 1;
  }
  .page { max-width: 1080px; margin: 0 auto; padding: 56px 28px 96px; }
  header.masthead { border-bottom: 1px solid var(--line); padding-bottom: 28px; }
  .eyebrow {
    margin: 0 0 10px; font-size: 12px; letter-spacing: .14em;
    text-transform: uppercase; color: var(--ink-faint);
  }
  h1 { margin: 0 0 12px; font-size: 31px; font-weight: 600; letter-spacing: -.01em; line-height: 1.32; }
  .lead { margin: 0; max-width: 60ch; color: var(--ink-soft); }
  .kpis {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px; margin: 26px 0 0; padding: 0; list-style: none;
  }
  .kpis li { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 15px 18px; }
  .kpi-label { display: block; font-size: 13px; color: var(--ink-faint); margin-bottom: 6px; }
  .kpi-value { font-size: 23px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .kpi-value small { font-size: 14px; font-weight: 400; color: var(--ink-soft); }
  .kpi-value .was { color: var(--ink-faint); font-weight: 400; }
  .kpi-value .arrow { color: var(--ink-faint); margin: 0 7px; font-weight: 400; }

  nav.toc {
    position: sticky; top: 0; z-index: 5; margin: 22px 0 0;
    display: flex; flex-wrap: wrap; gap: 5px 18px;
    padding: 12px 0; background: var(--paper);
    border-bottom: 1px solid var(--line);
  }
  nav.toc a { color: var(--ink-soft); text-decoration: none; font-size: 14px; }
  nav.toc a:hover, nav.toc a:focus-visible { color: var(--accent); }

  section { margin-top: 52px; scroll-margin-top: 56px; }
  h2 {
    margin: 0 0 4px; font-size: 14px; font-weight: 600; letter-spacing: .1em;
    text-transform: uppercase; color: var(--ink-faint);
  }
  .section-body { margin-top: 16px; }
  p { margin: 0 0 14px; }
  .note { color: var(--ink-soft); font-size: 14px; margin-top: 14px; }
  .footnote + .footnote { margin-top: 10px; }
  .footnote {
    margin-top: 18px; padding: 14px 17px; color: var(--ink-soft);
    font-size: 13.5px; line-height: 1.72; border-radius: 9px;
    background: color-mix(in srgb, var(--accent-soft) 62%, transparent);
    border: 1px solid color-mix(in srgb, var(--line) 70%, transparent);
  }
  code { font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; font-size: .92em; }

  blockquote {
    margin: 0; padding: 24px 26px;
    background: color-mix(in srgb, var(--accent-soft) 38%, var(--card));
    border: 1px solid var(--line); border-radius: var(--radius);
  }
  blockquote p { margin: 0 0 14px; }
  blockquote p:last-child { margin: 0; }

  .scroll { overflow-x: auto; border: 1px solid var(--line); border-radius: var(--radius); background: var(--card); }
  table { width: 100%; border-collapse: collapse; font-size: 15px; }
  caption {
    position: absolute; width: 1px; height: 1px; overflow: hidden;
    clip-path: inset(50%); white-space: nowrap;
  }
  thead th {
    background: var(--card); text-align: right; font-weight: 600; font-size: 13px;
    color: var(--ink-faint); padding: 12px 13px; white-space: nowrap;
    border-bottom: 1px solid var(--line);
  }
  tbody th, tbody td { padding: 10px 13px; border-bottom: 1px solid var(--line); text-align: right; white-space: nowrap; }
  thead th:first-child, tbody th { text-align: left; }
  tbody th { font-weight: 500; }
  tbody tr:last-child th, tbody tr:last-child td { border-bottom: 0; }
  tbody tr:hover th, tbody tr:hover td { background: color-mix(in srgb, var(--accent-soft) 40%, transparent); }
  .num { font-variant-numeric: tabular-nums; }
  .soft { color: var(--ink-faint); }
  .sep { color: var(--ink-faint); }

  .pair .was { color: var(--ink-faint); }
  .pair .arrow { color: var(--ink-faint); margin: 0 5px; font-size: .88em; }
  .pair .now { font-weight: 600; }
  .pair.down .now { color: var(--down); }
  .pair.up .now { color: var(--up); }
  .delta.down { color: var(--down); }
  .delta.up { color: var(--up); }
  .delta.flat { color: var(--ink-faint); }

  td.rate { min-width: 118px; }
  .bar { display: block; height: 3px; margin-top: 3px; border-radius: 2px; background: color-mix(in srgb, var(--line) 55%, transparent); }
  .bar:first-of-type { margin-top: 7px; }
  .bar-fill { display: block; height: 100%; border-radius: 2px; }
  .bar-fill.base { background: var(--ink-faint); }
  .bar-fill.skill { background: var(--down); }

  table.split-table { font-size: 13.5px; }
  table.split-table thead th { padding: 10px 9px; font-size: 12px; }
  table.split-table tbody th, table.split-table tbody td { padding: 9px; }
  table.split-table tbody th { font-size: 13px; }
  .split .was { color: var(--ink-faint); }
  .split .sep { margin: 0 2px; }
  .split .now { font-weight: 600; }
  .split.down .now { color: var(--down); }
  .split.up .now { color: var(--up); }
  .split.flat .now { color: var(--ink-faint); }

  table.rules td, table.rules th { white-space: normal; text-align: left; vertical-align: top; }
  table.rules th { width: 76px; color: var(--ink-faint); font-variant-numeric: tabular-nums; font-weight: 500; }
  table.rules td { color: var(--ink-soft); font-size: 14.5px; line-height: 1.66; }

  ul.plain { margin: 0; padding-left: 1.1em; color: var(--ink-soft); }
  ul.plain li { margin-bottom: 8px; }
  ul.plain li::marker { color: var(--ink-faint); }

  dl.facts {
    margin: 0; display: grid; grid-template-columns: minmax(120px, 200px) 1fr;
    border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; background: var(--card);
  }
  dl.facts dt, dl.facts dd { margin: 0; padding: 11px 16px; border-bottom: 1px solid var(--line); }
  dl.facts dt { color: var(--ink-faint); font-size: 14px; }
  dl.facts dd { font-variant-numeric: tabular-nums; }
  dl.facts dt:nth-last-of-type(1), dl.facts dd:nth-last-of-type(1) { border-bottom: 0; }

  footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid var(--line); color: var(--ink-faint); font-size: 14px; }
  footer p { margin: 0; }
  footer a { color: var(--accent); text-decoration: none; }
  footer a:hover { text-decoration: underline; }

  @media (max-width: 640px) {
    .page { padding: 36px 18px 72px; }
    h1 { font-size: 25px; }
    dl.facts { grid-template-columns: 1fr; }
    dl.facts dt { padding-bottom: 0; border-bottom: 0; }
    dl.facts dd { padding-top: 2px; }
  }
  @media print {
    nav.toc, .kpis { display: none; }
    body { background: #fff; }
    .scroll { border: 0; }
    section, .kpis li { break-inside: avoid; }
  }
"""

prompt_html = "\n".join(f"        <p>{paragraph}</p>" for paragraph in prompt)
split_head = "".join(f'<th scope="col">{name}</th>' for name in SPLIT_HEAD)
rule_rows = "\n".join(
    f'      <tr><th scope="row">{code}</th><td>{text}</td></tr>' for code, text in RULE_ROWS
)

html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>效果对照 · natural-talk</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">

  <header class="masthead">
    <p class="eyebrow">natural-talk · fiction</p>
    <h1>同一提示下的规则启用对照</h1>
    <p class="lead">同一条提示、{len(models)} 个模型，各写两篇：一篇不启用规则，一篇启用 <code>SKILL.md</code> 与 <code>references/fiction.md</code>。命中数随提示与样本变动，不用于评价模型能力。</p>
    <ul class="kpis">
      <li><span class="kpi-label">命中合计</span><span class="kpi-value"><span class="was">{sum_base}</span><span class="arrow">→</span>{sum_skill}</span></li>
      <li><span class="kpi-label">每千字命中下降的模型</span><span class="kpi-value">{improved}<small> / {len(models)}</small></span></li>
      <li><span class="kpi-label">每千字命中最高值</span><span class="kpi-value"><span class="was">{peak:g}</span><span class="arrow">→</span>{peak_skill:g}</span></li>
    </ul>
  </header>

  <nav class="toc" aria-label="目录">
    <a href="#prompt">提示词</a>
    <a href="#setup">条件</a>
    <a href="#total">合计</a>
    <a href="#split">分项</a>
    <a href="#rules">计数口径</a>
    <a href="#excluded">未计入</a>
    <a href="#env">测试设定</a>
  </nav>

  <section id="prompt">
    <h2>提示词</h2>
    <div class="section-body">
      <blockquote>
{prompt_html}
      </blockquote>
    </div>
  </section>

  <section id="setup">
    <h2>条件</h2>
    <div class="section-body">
      <dl class="facts">
        <dt>不启用规则</dt><dd>系统提示一句：你是一个中文写作与代码沟通助手。直接完成用户的要求。</dd>
        <dt>启用规则</dt><dd><code>SKILL.md</code> 全文与 <code>references/fiction.md</code> 全文</dd>
        <dt>用户提示末尾</dt><dd>两个条件均追加：直接输出结果，不要解释过程。</dd>
        <dt>样本</dt><dd>每个模型每个条件一篇</dd>
      </dl>
    </div>
  </section>

  <section id="total">
    <h2>合计</h2>
    <div class="section-body">
      <div class="scroll">
        <table>
          <caption>各模型在不启用与启用规则下的命中合计、字数与每千字命中</caption>
          <thead>
            <tr>
              <th scope="col">模型</th>
              <th scope="col">命中</th>
              <th scope="col">每千字变化</th>
              <th scope="col">每千字</th>
              <th scope="col">字数</th>
            </tr>
          </thead>
          <tbody>
{chr(10).join(total_row(model) for model in models)}
          </tbody>
        </table>
      </div>
            <p class="footnote">命中与每千字单元格格式为「不启用 → 启用」，字数单元格为「不启用 / 启用」；每千字下方的两条短线是同一比例尺下的命中量（灰＝不启用，绿＝启用）。「每千字变化」列与 README 效果表的「降幅」同为每千字口径：绿为下降，橙为上升。</p>
      <p class="footnote">字数只计汉字；每千字为命中数折算至一千字的结果，保留一位小数。非严谨测试，命中数随提示与样本变动，不用于评价模型能力。启用规则组的 {len(models)} 篇中有 {low_skill} 篇低于提示要求的两千字，对照组均不低于两千字，其中 {over_base} 篇超过三千字上限。</p>
    </div>
  </section>

  <section id="split">
    <h2>分项</h2>
    <div class="section-body">
      <div class="scroll">
        <table class="split-table">
          <caption>各模型按 B1–B9 与视点分列的命中数</caption>
          <thead>
            <tr><th scope="col">模型</th>{split_head}</tr>
          </thead>
          <tbody>
{chr(10).join(split_row(model) for model in models)}
          </tbody>
        </table>
      </div>
      <p class="footnote">单元格格式为「不启用 / 启用」；绿色表示启用后减少，橙色表示增加。合计 = B1–B9 分项和 + 视点，视点计入合计。</p>
    </div>
  </section>

  <section id="rules">
    <h2>计数口径</h2>
    <div class="section-body">
      <p class="note">{INTRO}</p>
      <div class="scroll">
        <table class="rules">
          <caption>各编号的计入范围</caption>
          <tbody>
{rule_rows}
          </tbody>
        </table>
      </div>
      <p class="footnote">{NOTE}</p>
    </div>
  </section>

  <section id="excluded">
    <h2>未计入的内容</h2>
    <div class="section-body">
      <ul class="plain">
{EXCLUDED}
      </ul>
    </div>
  </section>

  <section id="env">
    <h2>测试设定</h2>
    <div class="section-body">
      <dl class="facts">
        <dt>temperature</dt><dd>1.0</dd>
        <dt>reasoning_effort</dt><dd>high</dd>
        <dt>max_tokens</dt><dd>32000</dd>
        <dt>stream</dt><dd>true</dd>
        <dt>样本</dt><dd>每个模型每个条件一篇</dd>
        <dt>启用规则</dt><dd><code>SKILL.md</code> + <code>references/fiction.md</code></dd>
        <dt>不启用规则</dt><dd>一句系统提示，不含规则</dd>
      </dl>
    </div>
  </section>

  <footer>
    <p>同表见 <a href="README.md">README.md</a>。正文在 <code>texts</code> 目录，每个模型两篇，后缀 <code>-base</code> 为不启用规则，<code>-skill</code> 为启用规则。</p>
  </footer>

</div>
</body>
</html>
"""

out = EXAMPLES / "对照.html"

if "--check" in sys.argv:
    current = out.read_text(encoding="utf-8") if out.is_file() else ""
    if current == html:
        print("对照.html 与 examples/README.md 一致")
        sys.exit(0)
    old, new = current.split("\n"), html.split("\n")
    for i, (a, b) in enumerate(zip(old, new), start=1):
        if a != b:
            print(f"FAIL 对照.html 第 {i} 行与 README 不一致\n  页面：{a.strip()[:110]}\n  应为：{b.strip()[:110]}")
            break
    else:
        print(f"FAIL 对照.html 行数 {len(old)} 与应为的 {len(new)} 不同")
    sys.exit(1)

out.write_text(html, encoding="utf-8", newline="\n")
print(f"wrote {out} ({len(html)} chars, {len(models)} models, {sum_base}->{sum_skill}, peak {peak} -> {peak_skill})")

