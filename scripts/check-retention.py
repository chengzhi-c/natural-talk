"""清理留存率护栏：清理稿相对原文缩水超过下限或膨胀超过上限即报警。

清理稿相对原文字符数暴跌意味着误删实句，85% 硬下限兜底；natural-talk 清理模式
有"最小改动"原则但无可测量护栏，此处补齐。

口径：去空白归一后的字符数之比（清理稿 / 原文）。清理模式的合理删减（删空话、
删装饰）会压低该值，故下限按需放宽到样例级（见 evals/benchmark.jsonl 的
retention_min 字段）；命令行默认 85%。

用法：
  python scripts/check-retention.py <原文> <清理稿>
上限：清理稿膨胀同样是信息守恒违反（加料），1.25 上限告警。

用法：
  python scripts/check-retention.py <原文> <清理稿>
退出码：0 达标，1 越界（缩水或膨胀），2 用法/读取错误。
自测：python scripts/test-eval-harness.py（84%/86% 边界两例）
"""
import re
import sys
from pathlib import Path

RETENTION_FLOOR = 0.85
RETENTION_CEILING = 1.25


def normalized_length(text):
    return len(re.sub(r"\s+", "", text))


def retention(original, cleaned):
    base = normalized_length(original)
    if base == 0:
        return 1.0
    return normalized_length(cleaned) / base


def is_ok(ratio, floor=RETENTION_FLOOR, ceiling=RETENTION_CEILING):
    return floor <= ratio <= ceiling


def main(argv):
    if len(argv) != 3:
        print("用法：python scripts/check-retention.py <原文> <清理稿>",
              file=sys.stderr)
        return 2
    try:
        original = Path(argv[1]).read_text(encoding="utf-8-sig")
        cleaned = Path(argv[2]).read_text(encoding="utf-8-sig")
    except OSError as error:
        print(f"读取失败：{error}", file=sys.stderr)
        return 2
    ratio = retention(original, cleaned)
    if is_ok(ratio):
        print(f"留存率 {ratio:.1%}（区间 {RETENTION_FLOOR:.0%}–{RETENTION_CEILING:.0%}）——OK")
        return 0
    if ratio < RETENTION_FLOOR:
        print(f"留存率 {ratio:.1%} 低于下限 {RETENTION_FLOOR:.0%}——回退检查是否误删实句")
    else:
        print(f"留存率 {ratio:.1%} 超过上限 {RETENTION_CEILING:.0%}——回退检查是否加料膨胀")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
