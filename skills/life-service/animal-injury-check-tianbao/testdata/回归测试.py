# -*- coding: utf-8 -*-
"""动物伤人责任与索赔核查脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import animal_injury_check as T  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        animal="", accident_date="", keeper="", third_party="", on_leash="",
        provocation="", special_duty="", medical="", vaccine="", photo="",
        police="", appraisal="", insurance="", paid_items="",
        treatment_done="", negotiate="", mediate="", market="", lawsuit="",
        evidence_owned="", evidence_desc="", today=TODAY,
    )
    base.update(kw)
    return base


def chk1(name, rows, item, state=None):
    for r in rows:
        if r[0] == item:
            if state is None:
                ck(name + "被触发", True)
            else:
                ck(name + "=" + state, r[1] == state)
            return
    ck(name + "(未出现)", state is None)


# ---------------------------------------------------------- 基础工具
ck("norm去空格", T.norm("  狗  ") == "狗")
ck("norm统一冒号", T.norm("事发经过：被咬") == "事发经过:被咬")
ck("filled空串=False", T.filled("") is False)
ck("filled斜杠提示=False", T.filled("是/否") is False)
ck("filled待填=False", T.filled("待填") is False)
ck("yes是", T.yes("是") is True)
ck("yes已鉴定", T.yes("已鉴定") is True)
ck("no否", T.no("否") is True)
ck("unknown空", T.unknown("") is True)
ck("parse_num元", T.parse_num("3800元") == 3800.0)
ck("parse_num空", T.parse_num("") is None)
ck("fmt_num去.0", T.fmt_num(6600.0) == "6600")
ck("money前缀", T.money(6600.0) == "¥6600")
ck("parse_date", T.parse_date("2026-09-28") == date(2026, 9, 28))
ck("base_date兜底", isinstance(T.base_date(""), date))
ck("hit_any命中", T.hit_any("故意逗狗", ["故意逗"]) is True)
ck("hit_any未填", T.hit_any("", ["故意逗"]) is None)

# ---------------------------------------------------------- 动物识别
ck("kind狗", T.animal_kind("狗") == "狗")
ck("kind犬", T.animal_kind("大型犬") == "狗")
ck("kind猫", T.animal_kind("猫") == "猫")
ck("kind家畜", T.animal_kind("驴") == "家畜")
ck("kind未识别", T.animal_kind("不明") == "未识别")
ck("kind空", T.animal_kind("") == "未填")

# ---------------------------------------------------------- 责任定性
l1 = T.checks_liability(mk(animal="狗", keeper="是", third_party="否", on_leash="是"))
chk1("狗定性通过", l1, "动物类型", "通过")
chk1("主体明确通过", l1, "责任主体是否明确", "通过")
chk1("无第三人通过", l1, "是否存在第三人过错", "通过")
chk1("规范管理通过", l1, "是否按规定管理动物", "通过")
l2 = T.checks_liability(mk(animal="狗", keeper="否", third_party="是", on_leash="否"))
chk1("主体不明不通过", l2, "责任主体是否明确", "不通过")
chk1("第三人有风险", l2, "是否存在第三人过错", "有风险")
chk1("未管理有风险", l2, "是否按规定管理动物", "有风险")
l3 = T.checks_liability(mk())
chk1("动物未填待补正", l3, "动物类型", "待补正")
chk1("主体未填待补正", l3, "责任主体是否明确", "待补正")

# ---------------------------------------------------------- 免责事由
e1 = T.checks_exempt(mk(provocation="被没拴绳的大狗突然扑过来咬伤"))
chk1("无免责事由通过", e1, "是否存在免责事由", "通过")
e2 = T.checks_exempt(mk(provocation="我故意逗狗，它才咬我"))
chk1("故意逗狗有风险", e2, "是否存在免责事由", "有风险")
e3 = T.checks_exempt(mk(provocation="我翻越围栏进入狗的院子"))
chk1("翻越有风险", e3, "是否存在免责事由", "有风险")
e4 = T.checks_exempt(mk(provocation="有人踢了狗一脚", special_duty="否"))
chk1("第三人过错有风险", e4, "是否存在免责事由", "有风险")
chk1("非禁养通过", e4, "是否属于特殊责任类型", "通过")
e5 = T.checks_exempt(mk(provocation="被咬", special_duty="是"))
chk1("禁养犬有风险", e5, "是否属于特殊责任类型", "有风险")
e6 = T.checks_exempt(mk())
chk1("经过未填待补正", e6, "是否存在免责事由", "待补正")

# ---------------------------------------------------------- 赔偿测算
c1 = T.calc_comp(mk(paid_items="医疗费3800,误工费2000,护理费600,交通费200"))
ck("可测算为真", c1["可测算"] is True)
ck("合计6600", abs(c1["已知合计"] - 6600.0) < 0.01)
ck("识别医疗费", "医疗费" in c1["项目"])
ck("识别误工费", "误工费" in c1["项目"])
ck("识别交通费", "交通费" in c1["项目"])
ck("缺项含残疾赔偿金", "残疾赔偿金" in c1["缺项"])
c2 = T.calc_comp(mk(paid_items=""))
ck("未填无法测算", c2["可测算"] is False)
ck("未填有说明", "无法测算" in c2["说明"])
c3 = T.calc_comp(mk(paid_items="没有票据"))
ck("无数字不测算", c3["可测算"] is False)

# ---------------------------------------------------------- 金额段
a1 = T.checks_amount(mk(paid_items="医疗费3800", appraisal="是", insurance="是"), c1)
chk1("已支出通过", a1, "已支出金额", "通过")
chk1("有缺口有风险", a1, "赔偿项目缺口", "有风险")
chk1("已鉴定通过", a1, "是否做伤情鉴定", "通过")
chk1("有保险通过", a1, "对方是否投保", "通过")
a2 = T.checks_amount(mk(paid_items=""), a2c := T.calc_comp(mk()))
chk1("无法测算待补正", a2, "赔偿金额测算", "待补正")
FULL = ("医疗费3800,误工费2000,护理费600,交通费200,"
        "住院伙食补助400,营养费300,残疾赔偿金,精神损害抚慰金")
a3c = T.calc_comp(mk(paid_items=FULL))
a3 = T.checks_amount(mk(paid_items=FULL, appraisal="是", insurance="否"), a3c)
chk1("无缺口通过", a3, "赔偿项目缺口", "通过")
chk1("无保险有风险", a3, "对方是否投保", "有风险")

# ---------------------------------------------------------- 处置取证
t1 = T.checks_treatment(mk(medical="是", vaccine="是", photo="是", police="否"))
chk1("就医通过", t1, "是否及时就医", "通过")
chk1("疫苗通过", t1, "是否接种疫苗", "通过")
chk1("拍照通过", t1, "是否拍照留证", "通过")
chk1("未报警有风险", t1, "是否报警", "有风险")
t2 = T.checks_treatment(mk(medical="否", vaccine="否", photo="否", police="否"))
chk1("未就医有风险", t2, "是否及时就医", "有风险")
t3 = T.checks_treatment(mk())
chk1("处置未填待补正", t3, "是否报警", "待补正")

# ---------------------------------------------------------- 维权路径
p1 = T.checks_path(mk(negotiate="是", mediate="否", market="否", lawsuit="否"))
chk1("已协商通过", p1, "协商", "通过")
chk1("未调解有风险", p1, "社区与物业调解", "有风险")
chk1("未起诉有风险", p1, "诉讼", "有风险")
p2 = T.checks_path(mk())
chk1("路径未填待补正", p2, "协商", "待补正")

# ---------------------------------------------------------- 时效
tt1 = T.checks_time(mk(accident_date="2026-09-28", treatment_done="否"), TODAY)
chk1("时效在期通过", tt1, "民事诉讼时效", "通过")
chk1("治疗未终结有风险", tt1, "治疗是否终结", "有风险")
tt2 = T.checks_time(mk(accident_date="2020-01-01"), TODAY)
chk1("时效已过有风险", tt2, "民事诉讼时效", "有风险")
tt3 = T.checks_time(mk(), TODAY)
chk1("时效未填待补正", tt3, "民事诉讼时效", "待补正")

# ---------------------------------------------------------- 证据
v1 = T.checks_evidence(mk(evidence_owned="报警,回执,病历,诊断,发票,护理,工资,鉴定,登记,物业"))
ck("证据条数", len(v1) == 6)
chk1("事故事实通过", v1, "事故事实证据", "通过")
chk1("鉴定证据通过", v1, "鉴定文书", "通过")
v2 = T.checks_evidence(mk())
chk1("证据未填待补正", v2, "证据总览", "待补正")
v3 = T.checks_evidence(mk(evidence_desc="只有照片"))
chk1("部分证据有风险", v3, "伤情证据", "有风险")
g1 = T.evidence_gap(mk(police="否", medical="是"))
ck("未报警含事故事实", "事故事实证据" in g1)
g2 = T.evidence_gap(mk(police="是", medical="是",
                       evidence_owned="报警,回执,病历,诊断,发票,护理,工资,鉴定,登记,物业"))
ck("证据齐全无缺口", len(g2) == 0)

# ---------------------------------------------------------- 路径与待办
sp1 = T.path_steps(mk(animal="狗"))
ck("路径含止损", any("止损" in t or "就医" in t for _s, t in sp1))
ck("路径含鉴定", any("鉴定" in t for _s, t in sp1))
ck("犬类含禁养提醒", any("禁养" in t for _s, t in sp1))
sp2 = T.path_steps(mk(animal="猫"))
ck("猫无禁养提醒", not any("禁养" in t for _s, t in sp2))
td = T.todo_list(mk(medical="否", vaccine="否", photo="否", police="否", appraisal="否"), [])
ck("待办含就医", any(n == "立即就医" for n, _s in td))
ck("待办含疫苗", any(n == "接种狂犬病疫苗" for n, _s in td))
ck("待办含报警", any(n == "报警并要回执" for n, _s in td))
ck("待办含鉴定", any(n == "做伤情鉴定" for n, _s in td))
ck("待办去重", len(td) == len(set(n for n, _s in td)))

# ---------------------------------------------------------- 端到端
sp = os.path.join(SCRIPTS, "animal_injury_check.py")
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
sample = os.path.join(HERE, "样例.md")
empty = os.path.join(HERE, "空输入.md")
r1 = subprocess.run([sys.executable, sp, sample, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("样例rc=0", r1.returncode == 0)
o1 = r1.stdout or ""
ck("样例含结论摘要", "一、结论摘要" in o1)
ck("样例含责任段", "二、责任主体与法律定性" in o1)
ck("样例含免责段", "三、免责事由核查" in o1)
ck("样例含赔偿段", "四、赔偿项目与金额测算" in o1)
ck("样例含取证段", "五、伤情处置与取证" in o1)
ck("样例含路径段", "六、维权路径与调解" in o1)
ck("样例含时效段", "七、时效与鉴定时机" in o1)
ck("样例含证据段", "八、证据清单与缺口" in o1)
ck("样例含操作段", "九、维权路径排序" in o1)
ck("样例含待办段", "十一、待办补正动作" in o1)
ck("样例含边界段", "边界与纪律" in o1)
ck("样例段数>=11", o1.count("## ") >= 11)
ck("样例含6600", "6600" in o1)
ck("样例含狗", "狗" in o1)
ck("样例含不通过", "不通过" in o1)
ck("样例无乱码", "\ufffd" not in o1)
r2 = subprocess.run([sys.executable, sp, sample, "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
try:
    d = json.loads(r2.stdout or "{}")
    ck("json可解析含结论", "结论" in d and "待办" in d)
    ck("json动物类型正确", d.get("动物类型") == "狗")
    ck("json赔偿合计", abs(d["赔偿测算"]["已知合计"] - 6600.0) < 0.01)
except Exception:
    ck("json可解析含结论", False)
    ck("json动物类型正确", False)
    ck("json赔偿合计", False)
r3 = subprocess.run([sys.executable, sp, empty, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("空输入rc=2", r3.returncode == 2)
ck("空输入不崩有输出", len(r3.stdout or "") > 400)
ck("空输入提示缺失", "关键信息缺失" in (r3.stdout or ""))
ck("空输入无异常", "Traceback" not in (r3.stderr or ""))
ck("空输入段数>=11", (r3.stdout or "").count("## ") >= 11)

# ---------------------------------------------------------- 汇总
total = len(PASS) + len(FAIL)
lines = ["=== 动物伤人 回归测试 ===",
         "PASS=%d FAIL=%d TOTAL=%d" % (len(PASS), len(FAIL), total), ""]
for n in PASS:
    lines.append("  ok  " + n)
for n in FAIL:
    lines.append("  FAIL " + n)
lines.append("")
lines.append("RESULT: %s" % ("ALL PASS" if not FAIL else "FAILED"))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines[:3]))
sys.exit(1 if FAIL else 0)
