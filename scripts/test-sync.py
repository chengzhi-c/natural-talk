"""check-sync.py 注入自测：复制仓库到临时目录，注入已知攻击，断言能抓到。

攻击样本覆盖关键语义反转（保留规则编号与部分关键词）：
  A1 模板 D1 判据反转（评价改落在用户本人）
  A2 模板 D2 收尾反转（事实边界改开放邀约）
  A3 模板 D5 方向反转（删空预告改保留、留真步骤改删）
  A4 模板 D5 步数反转（固定步数改成可随意扩写）
  A5 fiction 模板输出边界反转（只输出正文改成附说明）
  A6 SKILL.md B1 改法反转（删翻案改保留）——指纹检测
  A7 模板 C6 条件反转（无信息气氛句改成全部保留）
  A8 fiction 模板 F8 台词边界反转（把角色真假当连续性错误）
  A9 fiction 模板 F6 延后揭示反转（延后揭示改成破折号豁免）
  A10 fiction 模板 F7 表层句式反转（有新增事实就保留原句式）
  A11 fiction 模板 F7 事实保留反转（有具体结果也删除）
  A12 fiction 模板 F8 未知原因反转（强制补写解释）
  A13 fiction 清理信息守恒反转（允许补造信息）
  A14 fiction 引文边界反转（把角色台词当资料引文）
  A15 模板 D6 判据反转（删归因改成保留并可补造）
  A16 模板 B9 无关比喻反转（装饰性比喻改成一律保留）
  A17 SKILL.md B1 排除关系反转（"不得改成不只是"改成"可改成"）——指纹检测
  A18 SKILL.md D6 泛化弱版反转（整条删改成可留弱版）——指纹检测
  A19 模板清理模式回指反转（关系断言同段共现即可作依据）
  A21 SKILL.md B12 宏观开场反转（改为一律保留）
  A22 SKILL.md B1 真修正反转（有依据也可删排除面）
  A23 SKILL.md B1 成句反转（允许残留碎片）

用法：python scripts/test-sync.py
"""
import shutil
import os
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
    ("A4 模板D5步数反转", "templates/system-prompt-standard.txt",
     "用户给出数量时按原量词执行：“给3步/3条”=恰好3，“至少3”=不少于3，“至多3”=不超过3，“3–5”=3到5；只把编号项计入数量，必要风险提示可用一句非编号说明，不借机扩成教程",
     "用户指定步数时可以任意增加额外步骤和说明"),
    ("A5 fiction输出边界反转", "templates/system-prompt-fiction.txt",
     "只输出清理后的正文",
     "输出清理后的正文并默认附说明、规则编号和改动计数"),
    ("A6 权威源B1指纹篡改", "SKILL.md",
     "被否定的观点不存在就删否定留肯定",
     "被否定的观点不存在也原样保留，翻案表达不核对"),
    ("A7 模板C6条件反转", "templates/system-prompt-standard.txt",
     "具体描写后只用\"声音填满空间/静有重量/世界退回壳里\"作气氛总结且没有新增感知、动作或结果时，删除或换成下一件可感知的事；确有新变化则保留 [C6]",
     "具体描写后用\"声音填满空间/静有重量/世界退回壳里\"作气氛总结时全部保留 [C6]"),
    ("A8 fiction模板F8台词边界反转", "templates/system-prompt-fiction.txt",
     "F1–F7 角色台词内除外；F8 对全文生效，但在台词中只检查句法、指代和已经确立的连续性，不纠正角色谎言、误判、不可靠叙述或尚未解释的事件。",
     "F1–F7 角色台词内除外；F8 把台词与旁白的冲突一律视为连续性错误并纠正。"),
    ("A9 fiction模板F6延后揭示反转", "templates/system-prompt-fiction.txt",
     "信息必要不等于破折号必要，延后揭示本身不构成豁免。",
     "信息必要即可保留破折号，延后揭示构成豁免。"),
    ("A10 fiction模板F7表层句式反转", "templates/system-prompt-fiction.txt",
     "始终改掉“很久，久到……”这一表层句式",
     "后半句有新增事实时原样保留“很久，久到……”这一表层句式"),
    ("A11 fiction模板F7事实保留反转", "templates/system-prompt-fiction.txt",
     "后半句有具体时间、动作、环境变化或感知结果时保留事实",
     "后半句有具体时间、动作、环境变化或感知结果时删除整句"),
    ("A12 fiction模板F8未知原因反转", "templates/system-prompt-fiction.txt",
     "原因暂未揭示本身不是语义缺失，突发事件、悬疑和延后解释可以保留。",
     "原因暂未揭示一律视为语义缺失，必须补写解释。"),
    ("A13 fiction清理信息守恒反转", "templates/system-prompt-fiction.txt",
     "F1–F8 只能删除、重排或改写原文已有信息，不得新造动作、神态、感知、原因、时长或人物关系，改写关系断言须能回指原文同一谓词。",
     "F1–F8 可以自由补造动作、神态、感知、原因、时长或人物关系，改写关系断言同段共现即可作依据。"),
    ("A14 fiction引文边界反转", "templates/system-prompt-fiction.txt",
     "fiction 正文中的角色台词不算资料引文，按 F1–F8 边界处理。",
     "fiction 正文中的角色台词视为资料引文，完全豁免任何检查。"),
    ("A15 模板D6判据反转", "templates/system-prompt-standard.txt",
     "6. 模糊归因 [D6]：无来源的\"有研究表明/业内普遍认为/专家指出/不少用户反馈\"删掉归因直接陈述；有来源写来源；不得补造来源",
     "6. 模糊归因 [D6]：无来源的\"有研究表明/业内普遍认为/专家指出/不少用户反馈\"保留以增强说服力，可补造来源"),
    ("A16 模板B9无关比喻反转", "templates/system-prompt-standard.txt",
     "工具类比\"像一位智慧的导师\"\"永不疲倦的管家\"一类拟人模板改写为该事物实际执行的功能；喻体与本体说不出共享属性、删后解释力不减的无关比喻删掉或直说，承载机制或权衡解释的比喻（喻体在讲原理，如\"缓存像仓库\"\"分表像切蛋糕\"）整体保留，判断依据是删掉比喻后读者是否漏掉机制或权衡 [B9]。",
     "工具类比\"像一位智慧的导师\"\"永不疲倦的管家\"一类拟人模板与无关比喻原样保留，一律不改 [B9]。"),
    ("A17 权威源B1排除关系反转", "SKILL.md",
     "删否定留肯定时肯定面不得超出原句 B 的范围，\"不是A而是B\"不得改成\"不只是A\"——排除关系不得改写成包含关系",
     "删否定留肯定时可放宽肯定面范围，\"不是A而是B\"可改成\"不只是A\"，排除关系可以改写成包含关系"),
    ("A18 权威源D6泛化弱版反转", "SKILL.md",
     "论断仅靠该无源引用支撑时整条删，不留删数字后的泛化弱版（\"40%的用户\"不得改成\"很多用户\"，\"未来十年\"不得缩成\"未来几年\"）",
     "论断仅靠该无源引用支撑时删数字留泛化弱版（\"40%的用户\"可改成\"很多用户\"，\"未来十年\"可缩成\"未来几年\"）"),
    ("A19 模板清理回指反转", "templates/system-prompt-standard.txt",
     "新增或改写的关系、能力或实现断言须能回指原文同一谓词，同段共现不算依据",
     "新增或改写的关系、能力或实现断言同段共现即可作为依据"),
    ("A21 权威源B12宏观开场反转", "SKILL.md",
     "且不含具体背景信息 → 删起手语直接进入实质；起手语承载真实背景信息时删壳留信息",
     "宏观开场是作者的节奏铺垫，一律保留，不得删除起手语"),
    ("A22 权威源B1真修正反转", "SKILL.md",
     "原文的修正有先行依据时（\"压测证明\"\"实测显示\"等）保留完整否定与排除面，那是真修正不是翻案腔",
     "原文的修正即使有先行依据也可删去否定与排除面，真修正同样按翻案腔处理"),
    ("A23 权威源B1成句反转", "SKILL.md",
     "删否定留肯定后剩余部分必须完整成句，不得残留\"是/而\"碎片",
     "删否定留肯定后剩余部分无需检查成句，残留\"是/而\"碎片可以接受"),
]


def run_check(repo):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, str(repo / "scripts" / "check-sync.py")],
                          capture_output=True, text=True, encoding="utf-8", env=env)


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
