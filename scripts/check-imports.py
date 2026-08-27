# -*- coding: utf-8 -*-
"""无网络脚本检查：语法编译 + 模块级依赖验证。

py_compile 只查语法，eval-llm.py --list 只走一个脚本，两者都会漏掉
"模块级 read_text 崩溃"这类问题（eval-regression 曾因 baseline-src/
不入库而 clone 后直接 FileNotFoundError，CI 两步全绿）。

用法：
    python scripts/check-imports.py                # import 检查 scripts/ 与 benchmarks/
    python scripts/check-imports.py --compile-only # 只做 py_compile（CI 步骤 1）
    python scripts/check-imports.py --verbose      # 逐个打印
"""
import py_compile
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = sorted((ROOT / "scripts").glob("*.py")) + sorted((ROOT / "benchmarks").glob("*.py"))

# 这些脚本 import 阶段就需要网络、密钥或命令行参数，不在此检查范围
SKIP = {"check-imports.py", "_llm.py", "retry-runner.py"}


def compile_only():
    """对全部目标（含 SKIP 的）做语法编译。glob 在 Python 内展开，空目录不报错。"""
    failed = []
    for f in TARGETS:
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            failed.append(f"{f.relative_to(ROOT)}: {e}")
    if failed:
        print("编译检查失败：")
        for m in failed:
            print(f"  {m}")
        return 1
    print(f"编译检查通过：{len(TARGETS)} 个脚本")
    return 0


def main():
    if "--compile-only" in sys.argv:
        return compile_only()
    verbose = "--verbose" in sys.argv
    failed = []
    for f in TARGETS:
        if f.name in SKIP:
            continue
        try:
            runpy.run_path(str(f), run_name="not_main")
        except SystemExit:
            pass  # 脚本在模块级因缺参数主动退出，属正常路径
        except Exception as e:
            failed.append(f"{f.relative_to(ROOT)}: {type(e).__name__}: {e}")
        if verbose:
            print(f"[ok] {f.relative_to(ROOT)}")
    if failed:
        print("import 检查失败：")
        for m in failed:
            print(f"  {m}")
        return 1
    print(f"import 检查通过：{len([t for t in TARGETS if t.name not in SKIP])} 个脚本")
    return 0


if __name__ == "__main__":
    sys.exit(main())
