"""Fiction 层对照测量：总体＋按模型分解，逐项每千字频率。

测量项（全部可机械定位；F1 为代理词表，须抽样人工复核）：
  F1proxy  作者外部总结代理词（终于明白/意识到/第一次觉得…）
  F2      套路情绪特征（眼中闪过/空气仿佛凝固…）
  F3      生理反应模板（瞳孔/指节发白/喉结…）
  F5      叙述内对举结构（不是X而是Y 及变体）
  B5      破折号 ——

AI 文件读文件头 model= 行分组；含 __ERROR__/__EMPTY__ 的文件跳过。

用法：python measure-fiction.py <human_dir> <ai_dir...>
"""
import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROBES = {
    "F1proxy": r"(终于明白|终于懂了|意识到|领悟了|读懂了|才明白|才懂得|才读懂|第一次觉得|第一次明白|忽然明白|此刻才明白|明白了人生|深刻地认识到)",
    "F2": r"(眼中闪过|眼底闪过|闪过一丝|空气仿佛凝固|空气瞬间凝固|宛如鬼魅|撕裂虚空|弥漫着[^，。]{0,8}威压|令人窒息的|仿佛某种[^，。]{0,6})",
    "F3": r"(瞳孔[^，。]{0,3}(缩|收缩)|指节(发白|泛白|扣紧)|喉结(上下)?滚?动|指甲(掐|抠)进(肉|掌心)|呼吸一滞|心脏猛地(一缩|下沉|揪)|后背发凉|寒意从[^，。]{0,6}升起)",
    "F5": r"(不是[^，。；！？]{1,14}[，,]?而是|并非[^，。；！？]{1,14}[，,]?而是|不在于[^，。；！？]{1,14}而在于|与其说[^，。；！？]{1,14}不如说)",
    "B5": r"——",
}


def chars_of(text):
    return len(re.sub(r"\s", "", text))


def count_files(paths):
    total_chars = 0
    counts = {k: 0 for k in PROBES}
    for p in paths:
        text = p.read_text(encoding="utf-8")
        total_chars += chars_of(text)
        for k, pat in PROBES.items():
            counts[k] += len(re.findall(pat, text, flags=re.M))
    return total_chars, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("human_dir")
    ap.add_argument("ai_dirs", nargs="+")
    args = ap.parse_args()

    human_paths = list(Path(args.human_dir).glob("*.txt"))
    hc, hcounts = count_files(human_paths)
    hf = {k: (hcounts[k] / hc * 1000 if hc else 0) for k in PROBES}

    ai_paths = []
    for d in args.ai_dirs:
        for p in Path(d).glob("*.txt"):
            head = p.read_text(encoding="utf-8")[:600]
            if "__ERROR__" in head:
                continue
            if p.read_text(encoding="utf-8").split("---\n", 1)[-1].strip() == "__EMPTY__":
                continue
            ai_paths.append(p)

    by_model = {}
    for p in ai_paths:
        m = re.search(r"^model=(.+)$", p.read_text(encoding="utf-8"), flags=re.M)
        model = m.group(1).strip() if m else p.stem
        by_model.setdefault(model, []).append(p)

    ac, acounts = count_files(ai_paths)
    print(f"人类侧 {len(human_paths)} 篇 {hc} 字 | 生成侧 {len(ai_paths)} 篇 {ac} 字，{len(by_model)} 个模型\n")

    keys = list(PROBES)
    hdr = f"{'模型':<40}" + "".join(f"{k:>10}" for k in keys) + f"{'篇数':>6}{'字数':>8}"
    print(hdr)
    print("-" * len(hdr))
    print(f"{'人类(公版)':<40}" + "".join(f"{hf[k]:>10.3f}" for k in keys) + f"{len(human_paths):>6}{hc:>8}")

    total = {k: 0 for k in keys}
    for model in sorted(by_model):
        paths = by_model[model]
        c, counts = count_files(paths)
        freqs = {k: (counts[k] / c * 1000 if c else 0) for k in keys}
        for k in keys:
            total[k] += counts[k]
        print(f"{model:<40}" + "".join(f"{freqs[k]:>10.3f}" for k in keys) + f"{len(paths):>6}{c:>8}")

    print(f"{'生成(合计)':<40}" + "".join(
        (f"{total[k]/ac*1000:>10.3f}" if ac else "0") for k in keys) + f"{len(ai_paths):>6}{ac:>8}")

    print("\n原始计数（人类 / 生成合计）：")
    for k in keys:
        print(f"  {k}: {hcounts[k]} / {total[k]}")


if __name__ == "__main__":
    main()
