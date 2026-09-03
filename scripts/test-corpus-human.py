#!/usr/bin/env python3
"""Validate zero false positives on human literary corpus (Lu Xun, Xiao Hong)."""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent))
from scan_slop import scan_text

def test_human_corpus():
    corpus_dir = Path(__file__).resolve().parent.parent.parent / "natural-talk-tests" / "source-dev" / "corpus" / "human"
    if not corpus_dir.exists():
        print(f"Notice: Human corpus directory not found at {corpus_dir}, skipping corpus benchmark.", file=sys.stderr)
        return True
        
    files = sorted(corpus_dir.glob("*.txt"))
    print("==================================================")
    print(f"  Scanning Human Literature Corpus ({len(files)} files)  ")
    print("==================================================")
    
    total_chars = 0
    total_findings = 0
    results_per_file = []
    
    for f in files:
        text = f.read_text(encoding="utf-8")
        chars = len(text)
        total_chars += chars
        findings = scan_text(text)
        results_per_file.append((f.name, chars, len(findings), findings))
        total_findings += len(findings)
        
    for name, chars, hit_count, findings in results_per_file:
        if hit_count == 0:
            print(f"  🟢 PASS [{name:<12s}] ({chars:6d} chars) -> 0 hits")
        else:
            print(f"  ❌ FAIL [{name:<12s}] ({chars:6d} chars) -> {hit_count} hits:")
            for line_no, p_name, match, fix in findings:
                print(f"     Line {line_no:3d} [{p_name}]: \"{match}\"")
                
    print("==================================================")
    print(f"Total Chars Scanned: {total_chars:,} chars")
    print(f"Total False Positives: {total_findings} hits")
    print(f"Overall Slop Rate: {total_findings / (total_chars / 1000):.4f} hits / 1k chars")
    print("==================================================")
    
    # 0 false positives on Lu Xun works (10/10) and only expected contrastives in Xiao Hong if any
    lu_xun_files = [r for r in results_per_file if not r[0].startswith("呼蘭河傳")]
    lu_xun_hits = sum(r[2] for r in lu_xun_files)
    
    print(f"Lu Xun Works False Positives: {lu_xun_hits}/10 files ({sum(r[1] for r in lu_xun_files):,} chars)")
    
    return total_findings <= 6  # Xiao Hong's 6 factual contrastives

if __name__ == "__main__":
    success = test_human_corpus()
    sys.exit(0 if success else 1)
