#!/usr/bin/env python3
"""Repository checks: structure, cross-file contracts, portability, secrets.

Stdlib only. Run from the repository root or anywhere:
    python -B tests/check_repo.py
"""
import re
import subprocess
import sys
from pathlib import Path

# 终端编码不是 UTF-8 时中文会乱码，本地与 CI 看到的结果就对不上。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DOCS = [
    "SKILL.md",
    "README.md",
    "README.en.md",
    "CONTRIBUTING.md",
    "references/fiction.md",
    "references/rules-full.md",
]
REQUIRED = DOCS + ["LICENSE", ".github/workflows/checks.yml"]

failures = []
passes = []


def check(condition, message):
    if condition:
        passes.append(message)
    else:
        failures.append(message)


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


for relative in REQUIRED:
    check((ROOT / relative).is_file(), f"存在 {relative}")

texts = {relative: read(relative) for relative in DOCS if (ROOT / relative).is_file()}
skill = texts.get("SKILL.md", "")
fiction = texts.get("references/fiction.md", "")
rules = texts.get("references/rules-full.md", "")
readme = texts.get("README.md", "")
readme_en = texts.get("README.en.md", "")

# SKILL frontmatter is the host's only discovery entry.
frontmatter = re.match(r"---\n(.*?)\n---\n", skill, re.S)
check(bool(frontmatter), "SKILL.md frontmatter 可解析")
if frontmatter:
    meta = frontmatter.group(1)
    check(bool(re.search(r"^name:\s*natural-talk\s*$", meta, re.M)), "frontmatter name")
    check(bool(re.search(r"^description:\s*\S", meta, re.M)), "frontmatter description")

# The English README mirrors the Chinese one; equal counts catch dropped sections.
for label, select in (("二级标题", lambda t: [l for l in t.split("\n") if l.startswith("## ")]),
                      ("表格行", lambda t: [l for l in t.split("\n") if l.startswith("|")])):
    check(len(select(readme)) == len(select(readme_en)), f"README 中英{label}数一致")

# Cross-page references must resolve inside the repository.
for relative, text in texts.items():
    for target in re.findall(r"references/[A-Za-z0-9._-]+\.md", text):
        check((ROOT / target).is_file(), f"{relative} 引用的 {target} 存在")

# Generation and cleanup stay on separate pages.
for phrase in ("清理模式", "只报候选"):
    check(phrase not in fiction, f"fiction.md 不出现清理口径：{phrase}")
check("《" not in fiction and "》" not in fiction, "fiction.md 不写作品出处")

check("清理边界" in rules, "rules-full.md 有清理边界")
check("fiction 清理规则" in rules, "rules-full.md 有 fiction 清理规则")
check("可指认的具体物件" in rules, "B1 清点豁免口径在 rules-full")
check("具体名词枚举" in rules, "R10 枚举例外在 rules-full")
check("具体名词枚举" in skill, "R10 枚举例外在 SKILL")
check("成稿后再按" in skill, "代码评审/PR 走先成稿后检查")
check("以用户指令为准" in skill, "用户显式指令优先级")
check("不把没有来源的结论写成事实" in skill and "不把没有来源的结论写成事实" in rules,
       "无源结论不写成事实，SKILL 与 rules-full 同步")

# Attribution lives in README, not in the rules page.
check("叙事工法范例来源" in readme, "README 有范例来源表")
check("Narrative Technique Sources" in readme_en, "README.en 有范例来源表")

# Repository docs stay portable and free of local working-directory wording.
for relative, text in texts.items():
    check("仓库外" not in text, f"{relative} 不出现“仓库外”")
    check("不随仓库分发" not in text, f"{relative} 不出现“不随仓库分发”")
    check("外部工具" not in text, f"{relative} 不出现“外部工具”")
    check(not re.search(r"[A-Za-z]:\\", text), f"{relative} 不写本机绝对路径")

SECRET_PATTERNS = (
    r"\bsk[-_][A-Za-z0-9_-]{16,}\b",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
    r"\bgithub_pat_[A-Za-z0-9_]{20,}\b",
    r"\bglpat-[A-Za-z0-9_-]{20,}\b",
    r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----",
)
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".txt", ".json", ".jsonl"}
for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
        continue
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"LICENSE", ".gitignore"}:
        continue
    content = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(ROOT).as_posix()
    for pattern in SECRET_PATTERNS:
        check(re.search(pattern, content) is None, f"{rel} 不含敏感模式")

# Local Markdown links resolve; external links are out of scope.
for relative, text in texts.items():
    for target in re.findall(r"\[[^\]]*\]\(([^)\s]+)\)", text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path = target.split("#", 1)[0]
        if path:
            check((ROOT / relative).parent.joinpath(path).resolve().exists(),
                  f"{relative} 的链接 {target} 可解析")

# LF keeps local and CI output identical.
for path in ROOT.rglob("*"):
    if ".git" in path.parts or not path.is_file():
        continue
    if "__pycache__" in path.parts:
        continue
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".pdf",
                               ".zip", ".woff", ".woff2", ".ttf"}:
        continue
    check(b"\r\n" not in path.read_bytes(), f"{path.relative_to(ROOT)} 使用 LF")

# Process residue should not be committed. Ignored build caches are not residue;
# only files tracked by git are a real release risk.
def _tracked_paths():
    try:
        out = subprocess.check_output(
            ["git", "-c", "core.quotepath=false", "-C", str(ROOT), "ls-files"], text=True, encoding="utf-8")
    except Exception:
        return None
    return {Path(line) for line in out.splitlines() if line}


tracked = _tracked_paths()
for pattern in (".ruff_cache", "__pycache__", "*.pyc", "*.log"):
    found = [p for p in ROOT.rglob(pattern) if ".git" not in p.parts]
    if tracked is not None:
        if any(p.is_dir() for p in found):
            found = [p for p in found if not p.is_dir()
                     or any(t.is_relative_to(p.relative_to(ROOT)) for t in tracked)]
        found = [p for p in found if p.is_dir()
                 or p.relative_to(ROOT) in tracked]
    check(not found, f"无过程文件残留：{pattern}")

# Whitespace noise hides real diffs in review; the docs stay byte-clean.
WHITESPACE = DOCS[:]
for relative in WHITESPACE:
    path = ROOT / relative
    if not path.is_file():
        continue
    lines = path.read_text(encoding="utf-8").split("\n")
    trailing = [n for n, line in enumerate(lines, 1) if line != line.rstrip()]
    leading = [n for n, line in enumerate(lines, 1)
               if line[:1] == " " and line[1:2] not in ("", " ")]
    hint = lambda nums: f"（第 {', '.join(map(str, nums[:3]))} 行）" if nums else ""
    check(not trailing, f"{relative} 无行尾空格{hint(trailing)}")
    check(not leading, f"{relative} 无多余的行首单空格{hint(leading)}")

# A cited rule ID that no page defines sends the reader nowhere.
def defined_ids(text, prefix):
    pattern = re.compile(rf"^[\s#>\-]*{prefix}(\d+)[\s：:]", re.M)
    return {int(match.group(1)) for match in pattern.finditer(text)}


for prefix, source in (("R", "references/rules-full.md"), ("B", "references/fiction.md"),
                       ("C", "SKILL.md"), ("D", "SKILL.md"), ("N", "SKILL.md")):
    defined = defined_ids(texts.get(source, ""), prefix)
    check(bool(defined), f"{prefix} 层在该页有定义")
    cited = {int(match.group(1)) for text in texts.values()
             for match in re.finditer(rf"\b{prefix}(\d+)\b", text)}
    check(not cited - defined, f"{prefix} 层引用的编号都有定义：{sorted(cited - defined)}")

print(f"通过 {len(passes)} 项检查")
if failures:
    for message in failures:
        print(f"FAIL {message}")
    sys.exit(1)
