"""Windows 控制台 UTF-8 兜底。

被 scripts/ 与 evals/ 下的可执行脚本共用（扫描器、判分器、自测与 verify_repo）。
"""

import sys

sys.dont_write_bytecode = True

import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def ensure_utf8():
    """Windows 控制台默认 GBK，脚本按 UTF-8 读写必须先 reconfigure。"""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

