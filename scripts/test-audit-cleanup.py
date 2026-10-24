"""audit-cleanup.py 红灯自测：判分设施先证明能捕获已知缺陷，再采信跑分。

覆盖测试项：
  1. 归属通过：B10 命中行删除"说白了"→ 0 违规
  2. 无依据删除：无命中行删实句 → 无依据删除违规
  3. 越权新增：清理稿编造原文没有的实词 → 越权新增违规
  4. 移位放行：内容字跨块移动（B2 类改写）不触发（全文多重集守恒）
  5. 数字变动：20→50 同时触发净删与净增
  6. 模式感知：fiction 模式 B13 归属"微微"删除，prose 模式同改动成违规
  7. 纯标点改写：破折号改句号（B5）内容字零变化 → 0 违规

运行：python scripts/test-audit-cleanup.py
"""
import importlib.util
import sys
from pathlib import Path
import _loader

_loader.ensure_utf8()

SCRIPTS = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


audit_mod = _load("audit_cleanup", SCRIPTS / "audit-cleanup.py")
audit = audit_mod.audit

failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


def kinds(result):
    return [v["kind"] for v in result["violations"]]


# ---------- 1. 归属通过 ----------
r1 = audit("说白了，瓶颈在连接池。\n第二段正常文字。\n",
           "瓶颈在连接池。\n第二段正常文字。\n")
check("归属-B10删除0违规", r1["violations"] == [],
      f"实际 {r1['violations']}")
check("归属-B10规则命中", any("B10" in "".join(h["rules"]) for h in r1["hunks"]),
      f"hunks {r1['hunks']}")

# ---------- 2. 无依据删除 ----------
r2 = audit("我妈总说冰箱第二层的酸奶别动。\n猫今年十四岁，肾功能不太好。\n",
           "我妈总说冰箱第二层的酸奶别动。\n")
check("删除-无依据必报", "无依据删除" in kinds(r2), f"实际 {kinds(r2)}")
check("删除-字符表含十四岁",
      all(c in r2["g_removed"] for c in "十四岁"), f"g_removed {r2['g_removed']}")

# ---------- 3. 越权新增 ----------
r3 = audit("他划燃一根火柴。\n", "他划燃一根火柴。据说很有效。\n")
check("新增-越权必报", "越权新增" in kinds(r3), f"实际 {kinds(r3)}")

# ---------- 4. 移位放行 ----------
r4 = audit("性能显著提升。延迟从 120ms 降到 40ms。\n后续观察。\n",
           "延迟从 120ms 降到 40ms，性能显著提升。\n后续观察。\n")
check("移位-全文守恒0违规", r4["violations"] == [],
      f"g_removed {r4['g_removed']} g_added {r4['g_added']}")

# ---------- 5. 数字变动 ----------
r5 = audit("重试 3 次后放弃。\n", "重试 5 次后放弃。\n")
check("数字-净删净增都报", kinds(r5).count("无依据删除") == 1
      and kinds(r5).count("越权新增") == 1, f"实际 {kinds(r5)}")
check("数字-字符定位", "3" in r5["g_removed"] and "5" in r5["g_added"],
      f"rem {r5['g_removed']} add {r5['g_added']}")

# ---------- 6. 模式感知 ----------
ORIG_FIC = "她微微点头，把碗放下。\n"
CLEAN_FIC = "她点头，把碗放下。\n"
r6f = audit(ORIG_FIC, CLEAN_FIC, mode="fiction")
check("模式-fiction归属B13", r6f["violations"] == []
      and any("B13" in "".join(h["rules"]) for h in r6f["hunks"]),
      f"violations {r6f['violations']} hunks {r6f['hunks']}")
r6p = audit(ORIG_FIC, CLEAN_FIC, mode="prose")
check("模式-prose同改动必报", "无依据删除" in kinds(r6p), f"实际 {kinds(r6p)}")

# ---------- 7. 纯标点改写 ----------
r7 = audit("他赢了——用三年时间。\n", "他赢了，用了三年时间。\n")
check("标点-内容字零变化0违规", r7["violations"] == [], f"实际 {r7['violations']}")
check("标点-B5归属在场", any("B5" in "".join(h["rules"]) for h in r7["hunks"]),
      f"hunks {r7['hunks']}")

# ---------- 8. 幅度超出归属（实测漏网：借行内一个 B1 候选洗白整段压缩） ----------
# a) 命中句被整句删除（SNF-04 形态：改法是"删否定留肯定"，不是删句；
#    逗号分句各算骨架单元——后半分句"不是性能，是权限模型"被整段删掉）
r8a = audit("这个方案被质疑得最多的一点是扩展性，但真正难办的不是性能，是权限模型。\n后续一句。\n",
            "这个方案被质疑得最多的一点是扩展性。\n后续一句。\n")
check("幅度-整句蒸发必报", "幅度超出归属" in kinds(r8a), f"实际 {kinds(r8a)}")
# b) 命中句肯定面蒸发（SF-08 形态："不是技术，而是耐心"两句全删）
r8b = audit("真正的瓶颈不是技术，而是耐心。\n用户要的不是更多的功能，而是更稳定的服务。\n",
            "用户要的是更稳定的服务。\n")
check("幅度-肯定面蒸发必报", "幅度超出归属" in kinds(r8b), f"实际 {kinds(r8b)}")
# c) 合法改写不误报：B1 删否定留肯定，肯定面保留
r8c = audit("真正的瓶颈不是技术，而是耐心。\n",
            "真正的瓶颈是耐心。\n")
check("幅度-合法删否定不报", "幅度超出归属" not in kinds(r8c), f"实际 {r8c['violations']}")
# e) 主张句蒸发必报（SF-08 形态：删"上一版评审认为瓶颈出在
#    数据库"，否定悬空成翻案腔；肯定面还在但合法性前提没了）
r8e = audit("上一版评审认为瓶颈出在数据库，这次压测证明瓶颈不是数据库，而是连接池的锁竞争。\n",
            "压测证明瓶颈在连接池的锁竞争，不在数据库。\n")
check("幅度-主张句蒸发必报", "幅度超出归属" in kinds(r8e), f"实际 {kinds(r8e)}")
# f) 主张句保留时不误报（正确形态）
r8f = audit("上一版评审认为瓶颈出在数据库，这次压测证明瓶颈不是数据库，而是连接池的锁竞争。\n",
            "上一版评审认为瓶颈出在数据库，压测证明瓶颈在连接池的锁竞争，不在数据库。\n")
check("幅度-主张句保留不报", "幅度超出归属" not in kinds(r8f), f"实际 {r8f['violations']}")
# g) 主张句与否定触发词同句时不误中断（"压测证明……不是数据库"属否定侧）
r8g = audit("监控显示峰值出现在晚间，瓶颈不是内存，而是连接池。\n",
            "监控显示峰值在晚间，瓶颈在连接池，不在内存。\n")
check("幅度-否定侧含主张动词不误报", "幅度超出归属" not in kinds(r8g), f"实际 {r8g['violations']}")
# h) B5 规范改法（拆句/逗号承接）不得误报：内容分散到多句，骨架按块取并集
#    （旧实现按单句取 max，把规范拆句判为塌缩，反放过真有损压缩）
r8h = audit("他终于赢了——用三年时间。\n", "他终于赢了，用了三年。\n")
check("幅度-B5逗号承接不报", "幅度超出归属" not in kinds(r8h), f"实际 {r8h['violations']}")
r8i = audit("他终于赢了——用三年时间。\n", "他终于赢了。用了三年。\n")
check("幅度-B5句号断开不报", "幅度超出归属" not in kinds(r8i), f"实际 {r8i['violations']}")
# i) 对照：真有损压缩仍须报（内容字消失过半，没过 50% 骨架线）
r8j = audit("他终于赢了——用三年时间，中间两次推倒重来。\n", "他赢了。\n")
check("幅度-有损压缩仍报", "幅度超出归属" in kinds(r8j), f"实际 {kinds(r8j)}")
# d) 无归属块不受幅度核查影响（走无依据删除通道）
r8d = audit("正常一句没有命中。\n", "改写。\n")
check("幅度-无归属走删除通道", "无依据删除" in kinds(r8d)
      and "幅度超出归属" not in kinds(r8d), f"实际 {kinds(r8d)}")

# ---------- 附加：render 与 content_chars 单元行为 ----------
check("内容字-功能字排除", "了" not in audit_mod.content_chars("他走了很远的路"),
      "功能字不应计入内容字")
check("内容字-字母数字必计", audit_mod.content_chars("CPU x86") == {
      "C": 1, "P": 1, "U": 1, "x": 1, "8": 1, "6": 1}, "字母数字计法异常")
out = audit_mod.render(r2)
check("render-违规可见", "无依据删除" in out, out)


# a) 短语预算：B10 命中行的触发词删除走短语预算，不走 50% 骨架线。
#    把 B10 从 _PHRASE_BUDGET_RULES 删掉后，本例落入骨架核查被判塌缩——
#    即"合法删除被误报"，反向也说明该常量没有用例守。
#    触发词须选内容字 >2 的起手式（"说白了"的"了"是功能字，整分句会被
#    最小豁免跳过，两个方向都测不出）
r9a = audit("归根结底，这是权限模型的问题。\n", "这是权限模型的问题。\n")
check("短语预算-B10触发词删除0违规", r9a["violations"] == [],
      f"实际 {r9a['violations']}")
# b) 分句豁免：B9 命中分句整条重写是授权改法（删装饰比喻），不得报幅度
r9b = audit("它就像一位智慧的导师，不仅传授结论，更传授信任。\n后续一句。\n",
            "它传授结论与信任。\n后续一句。\n")
check("分句豁免-B9命中分句重写不报", "幅度超出归属" not in kinds(r9b),
      f"实际 {kinds(r9b)}")
# c) 分句豁免：B17 命中分句（句内主语复现）承前省删后一个主语不得报。
#    B17 只在 fiction/gen 报，prose 模式下该删除掉进无依据删除通道，断言被绕开
r9c = audit("她知道这件事，她也明白为什么。\n后续一句。\n",
            "她知道这件事，也明白为什么。\n后续一句。\n", mode="fiction")
check("分句豁免-B17复现删主语不报", "幅度超出归属" not in kinds(r9c),
      f"实际 {kinds(r9c)}")
# d) 规则替换词：B17 装饰标签"命令道"改"说"是换词不是越权新增
r9d = audit("“坐。”她命令道。\n", "“坐。”她说。\n", mode="fiction")
check("替换词-B17命令道改说0违规", r9d["violations"] == [],
      f"实际 {r9d['violations']}")
# e) 否定触发词：含主张动词的分句只要同句带"不是"就属否定侧，豁免回溯不中断。
#    把"不是"从 _NEG_TRIGGER 删掉后，本例的否定侧分句不再豁免，删否定侧被误报
r9e = audit("他认为不是内存的问题，而是连接池的问题。\n", "问题出在连接池。\n")
check("否定触发-含主张动词的否定侧可删", "幅度超出归属" not in kinds(r9e),
      f"实际 {kinds(r9e)}")


print("audit-cleanup 测试通过：归属、无依据删除、越权新增、移位放行、"
      "数字变动、模式感知、纯标点改写全部符合预期")

if failures:
    print("audit-cleanup 测试未通过：")
    print("\n".join(failures))
    sys.exit(1)
