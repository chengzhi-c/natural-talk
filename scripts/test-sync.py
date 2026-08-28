"""check-sync.py 注入自测：复制仓库到临时目录，注入已知攻击，断言能抓到。

攻击样本固化自实测诊断（语义反转但保留规则编号与关键词）：
  A1 模板 D1 判据反转（评价改落在用户本人）
  A2 模板 D2 收尾反转（事实边界改开放邀约）
  A3 模板 D5 方向反转（删空预告改保留、留真步骤改删）
  A4 SKILL.md B1 改法反转（删翻案改保留）——指纹检测

用法：python scripts/test-sync.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ATTACKS = [
    ("A1 模板D1判据反转", "templates/system-prompt-standard.txt",
     "检验：主语换成\"这个问题/这段代码\"，换不了的即越界",
     "检验：评价优先落在用户本人身上，充分肯定提问质量"),
    ("A2 模板D2收尾反转", "templates/system-prompt-standard.txt",
     "末句落在事实、建议或边界上",
     "末句落在开放邀约上"),
    ("A3 模板D5方向反转", "templates/system-prompt-standard.txt",
     "只宣布要做的空预告（\"让我们先理解背景\"）删；含具体可执行动作的真步骤（\"首先备份数据，其次关闭服务\"）保留",
     "空预告保留并鼓励；含具体可执行动作的真步骤删"),
    ("A4 权威源B1指纹篡改", "SKILL.md",
     "被否定的观点不存在就删否定留肯定",
     "被否定的观点不存在也原样保留，翻案表达不核对"),
]


def run_check(repo):
    return subprocess.run([sys.executable, str(repo / "scripts" / "check-sync.py")],
                          capture_output=True, text=True, encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory() as td:
        clean = Path(td) / "clean"
        shutil.copytree(ROOT, clean, ignore=shutil.ignore_patterns("__pycache__"))
        r = run_check(clean)
        if r.returncode != 0:
            print(f"[失败] 干净基线未通过（应通过）:\n{r.stdout}{r.stderr}")
            sys.exit(1)
        print("[通过] 干净基线")

    results = []
    for name, rel, old, new in ATTACKS:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns("__pycache__"))
            target = repo / rel
            text = target.read_text(encoding="utf-8")
            if old not in text:
                print(f"[失败] {name}: 注入点在目标文件中不存在（文本已变，请更新用例）")
                results.append(False)
                continue
            target.write_text(text.replace(old, new), encoding="utf-8")
            r = run_check(repo)
            caught = r.returncode != 0
            print(f"[{'抓到' if caught else '漏过'}] {name}")
            results.append(caught)

    if not all(results):
        sys.exit(1)
    print(f"自测通过：基线通过，{len(ATTACKS)} 项攻击全部被抓")


if __name__ == "__main__":
    main()
