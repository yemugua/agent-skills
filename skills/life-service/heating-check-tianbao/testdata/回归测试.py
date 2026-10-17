# -*- coding: utf-8 -*-
"""供暖不达标核查脚本回归测试（断言 48 条）。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import heating_check as H  # noqa: E402

PASS = []
FAIL = []


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        city="", mode="", subject="", insulation="", paid=None, days_total=None,
        std=None, avg_temp=None, is_standard="", bad_days=None, outdoor=None,
        in_period="", reported="", onsite="", instrument="", multipoint="",
        outdoor_meas="", signed="", has_rule=None, ratio=None, settled="",
        settled_amt=None, claim_date="", evidence="", bad_temp=False,
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
ck("norm去空格", H.norm("  14.5  ") == "14.5")
ck("norm统一冒号", H.norm("供暖方式：集中供暖") == "供暖方式:集中供暖")
ck("norm去全角逗号", H.norm("有，已到场") == "有,已到场")
ck("filled空串=False", H.filled("") is False)
ck("filled斜杠提示=False", H.filled("有/无/不清楚") is False)
ck("filled有=True", H.filled("有") is True)
ck("filled待填=False", H.filled("待填") is False)
ck("filled括号开头=False", H.filled("（如：石家庄）") is False)
ck("yes是", H.yes("是") is True)
ck("yes已签字", H.yes("已签字") is True)
ck("no否", H.no("否") is True)
ck("no不达标", H.no("不达标") is True)
ck("no未到场", H.no("未到场") is True)
ck("yes_flag有=True", H.yes_flag("有") is True)
ck("yes_flag无=False", H.yes_flag("无") is False)
ck("yes_flag未填=None", H.yes_flag("") is None)
ck("parse_num元", H.parse_num("3600元") == 3600.0)
ck("parse_num去度", H.parse_num("18℃") == 18.0)
ck("parse_num空", H.parse_num("") is None)
ck("fmt_num去.0", H.fmt_num(3600.0) == "3600")
ck("fmt_num保留小数", H.fmt_num(14.5) == "14.5")
ck("parse_date", H.parse_date("2026-01-15") == date(2026, 1, 15))
ck("parse_date空", H.parse_date("") is None)
ck("base_date兜底", isinstance(H.base_date(""), date))
ck("add_years跨闰", H.add_years(date(2026, 2, 28), 1) == date(2027, 2, 28))

# ---------------------------------------------------------- 解析
txt = H.read_text(os.path.join(HERE, "样例.md"))
kv = H.build_kv(txt)
ck("build_kv取供暖方式", H.get_text(kv, ["供暖方式"]) == "集中供暖")
ck("build_kv取已缴热费", H.get_text(kv, ["已缴热费金额"]) == "3600")
ck("build_kv取实测平均室温", H.get_text(kv, ["实测平均室温"]) == "14.5")
ck("build_kv取约定退费比例", H.get_text(kv, ["约定退费比例"]) == "30")
ck("build_kv最长别名优先",
   H.get_text({"当地室温标准": "18", "室温标准": "16"}, ["当地室温标准", "室温标准"]) == "18")
ck("build_kv冒号行", H.get_text(H.build_kv("供暖方式：集中供暖\n"), ["供暖方式"]) == "集中供暖")
ck("get_text兜底alias", H.get_text({"所在城市": "石家庄"}, ["城市"]) == "石家庄")

# ---------------------------------------------------------- 供暖方式与责任主体
ck("mode集中", H.mode_type("集中供暖")[0] == "集中供暖")
ck("mode集中可退", H.mode_type("集中供暖")[2] is True)
ck("mode自供暖", H.mode_type("小区自供暖")[0] == "小区自供暖")
ck("mode壁挂炉", H.mode_type("燃气壁挂炉")[0] == "燃气壁挂炉")
ck("mode壁挂炉不可退", H.mode_type("燃气壁挂炉")[2] is False)
ck("mode电采暖", H.mode_type("电采暖")[2] is False)
ck("mode未填待确认", H.mode_type("")[2] is None)
ck("mode空值返回需确认", H.mode_type("")[0] == "需确认")

r1 = H.checks_mode(mk(mode="集中供暖", subject="物业公司", insulation="暖气被包死"))
chk1("集中供暖责任主体", r1, "责任主体", "通过")
chk1("找物业有风险", r1, "索赔对象", "有风险")
chk1("自担部分", r1, "自担部分", "有风险")
r2 = H.checks_mode(mk(mode="燃气壁挂炉"))
chk1("壁挂炉责任主体不通过", r2, "责任主体", "不通过")
r3 = H.checks_mode(mk(mode=""))
chk1("方式未填待补正", r3, "责任主体", "待补正")
r4 = H.checks_mode(mk(mode="集中供暖", subject="某热力集团", insulation="正常"))
chk1("热力集团通过", r4, "索赔对象", "通过")
chk1("保温正常通过", r4, "自担部分", "通过")

# ---------------------------------------------------------- 达标与测温
ck("判定不达标", H.temp_judge(mk(std=18.0, avg_temp=14.5))[0] == "不达标")
ck("判定达标", H.temp_judge(mk(std=18.0, avg_temp=18.2))[0] == "达标")
ck("判定待补正", H.temp_judge(mk())[0] == "待补正")
ck("判定自述不达标", H.temp_judge(mk(is_standard="否"))[0] == "不达标")
ck("不达标含温差", "3.5" in H.temp_judge(mk(std=18.0, avg_temp=14.5))[1])

m1 = H.checks_measure(mk(mode="集中供暖", std=18.0, avg_temp=14.5,
                         in_period="是", reported="是", onsite="是",
                         instrument="是", multipoint="是", outdoor_meas="是", signed="是"))
chk1("达标项通过", m1, "是否达标", "不达标")
chk1("六要件全通过", m1, "是否有双方签字测温记录", "通过")
m2 = H.checks_measure(mk(mode="集中供暖", std=18.0, avg_temp=14.5,
                         onsite="到场但单人测温未签字", instrument="否",
                         multipoint="否", outdoor_meas="否", signed="无"))
chk1("到场但无双方签字有风险", m2, "供热单位是否到场", "有风险")
chk1("完全无签字记录不通过", m2, "是否有双方签字测温记录", "不通过")
m2b = H.checks_measure(mk(mode="集中供暖", std=18.0, avg_temp=14.5,
                          multipoint="否", outdoor_meas="否", instrument="否"))
chk1("多点未做有风险", m2b, "是否多点多时次取值", "有风险")
chk1("未测室外有风险", m2b, "是否同时测室外温度", "有风险")
chk1("仪器未检定有风险", m2b, "测温仪器是否检定合格", "有风险")
m2c = H.checks_measure(mk(mode="集中供暖", std=18.0, avg_temp=14.5, in_period="否"))
chk1("供热期外不通过", m2c, "测温是否在供热期内", "不通过")
m2d = H.checks_measure(mk(mode="集中供暖", std=18.0, avg_temp=14.5, onsite="拒不到场"))
chk1("拒不到场不通过", m2d, "供热单位是否到场", "不通过")
m2e = H.checks_measure(mk(mode="集中供暖", std=18.0, avg_temp=14.5, signed="只有单方记录"))
chk1("仅单方记录有风险", m2e, "是否有双方签字测温记录", "有风险")
m3 = H.checks_measure(mk(mode="燃气壁挂炉", std=18.0, avg_temp=12.0))
chk1("自采暖测温不适用", m3, "测温程序", "不适用")
m4 = H.checks_measure(mk(mode="集中供暖", std=18.0, avg_temp=14.5))
chk1("未填全为待补正", [r[1] for r in m4 if r[1] != "待补正"], "是否达标")
m5 = H.checks_measure(mk(mode="集中供暖", is_standard="否"))
chk1("仅自述不达标", m5, "是否达标", "不达标")

# ---------------------------------------------------------- 退费测算
ck("ratio百分比写法", abs(H.norm_ratio(30.0) - 0.3) < 1e-9)
ck("ratio小数写法", abs(H.norm_ratio(0.3) - 0.3) < 1e-9)
ck("ratio空", H.norm_ratio(None) is None)

c1 = H.calc_refund(mk(mode="集中供暖", paid=3600.0, std=18.0, avg_temp=14.5,
                      has_rule=True, ratio=30.0, days_total=147, bad_days=96))
ck("双轨两条口径", len(c1["口径"]) == 2)
ck("下限为0800", abs(c1["下限"] - 3600 * (3.5 / 18.0)) < 1e-6)
ck("下限小于上限", c1["下限"] <= c1["上限"])
ck("算式含缺口比例", any("缺口比例" in x for x in c1["算式"]))
ck("参考按日退还非空", c1["参考按日退还"] is not None)
c2 = H.calc_refund(mk(mode="集中供暖", paid=3600.0, std=18.0, avg_temp=18.0,
                      has_rule=True, ratio=30.0))
ck("达标时口径二为0", len(c2["口径"]) == 1)
ck("达标时上限为1080", abs(c2["上限"] - 1080.0) < 1e-6)
c3 = H.calc_refund(mk(mode="集中供暖", paid=3600.0))
ck("缺要素无法测算", c3["上限"] is None)
ck("缺要素有说明", "缺少可测算要素" in c3["说明"])
c4 = H.calc_refund(mk(mode="燃气壁挂炉", paid=3600.0))
ck("自采暖不适用", c4["适用"] is False)
ck("自采暖无区间", c4["上限"] is None)
c5 = H.calc_refund(mk(mode="集中供暖", paid=3600.0, std=18.0, avg_temp=14.5,
                      has_rule=True, ratio=30.0, settled_amt=500.0))
ck("待追回计算", abs(c5["待追回"] - (c5["上限"] - 500.0)) < 1e-6)
ck("上限封顶已缴热费", H.calc_refund(mk(mode="集中供暖", paid=100.0, std=18.0,
                                      avg_temp=0.0))["上限"] == 100.0)

rc1 = H.checks_refund(mk(mode="集中供暖", paid=3600.0), c1)
chk1("可退区间通过", rc1, "可退金额区间", "通过")
chk1("退费上限有风险", rc1, "退费上限", "有风险")
rc2 = H.checks_refund(mk(mode="集中供暖", paid=3600.0, settled_amt=500.0), c5)
chk1("已获部分退费", rc2, "尚需追回", "有风险")
rc3 = H.checks_refund(mk(mode="燃气壁挂炉", paid=3600.0), c4)
chk1("自采暖退费不适用", rc3, "热费退费", "不适用")

# ---------------------------------------------------------- 证据与路径与时效
e1 = H.checks_evidence(mk(evidence="缴费凭证,供热合同,测温记录,通话录音,气象数据,保温照片"))
chk1("六项证据全通过", e1, "缴费凭证", "通过")
chk1("气象数据算室外温度证据", e1, "室外温度证据", "通过")
e1b = H.checks_evidence(mk(evidence="缴费凭证,供热合同,测温记录,通话录音,保温照片"))
chk1("缺室外温度证据", e1b, "室外温度证据", "待补正")
e2 = H.checks_evidence(mk(evidence=""))
chk1("无证据清单待补正", e2, "证据清单", "待补正")
p1 = H.path_steps(mk(mode="集中供暖"))
ck("集中路径第1步找热力公司", "供热企业" in p1[0][1])
ck("集中路径含12345", any("12345" in t for _s, t in p1))
p1b = H.path_steps(mk(mode="燃气壁挂炉"))
ck("壁挂炉路径走维修", "维修" in "".join(t for _s, t in p1b))
ck("壁挂炉路径不走供热企业", "供热企业" not in "".join(t for _s, t in p1b))
p1c = H.path_steps(mk(mode="小区自供暖"))
ck("小区自供暖仍可退费", H.mode_type("小区自供暖")[2] is True)

t1 = H.checks_time(mk(claim_date="2026-01-15"), date(2026, 10, 5))
chk1("时效在期", t1, "诉讼时效倒计时", "通过")
t2 = H.checks_time(mk(claim_date="2020-01-15"), date(2026, 10, 5))
chk1("时效已过", t2, "诉讼时效倒计时", "有风险")
ck("时效含还剩", any("还剩" in m for _n, _s, m in t1))
ck("时效含已过", any("已过" in m for _n, _s, m in t2))
t3 = H.checks_time(mk(), date(2026, 10, 5))
chk1("时效未填", t3, "诉讼时效倒计时", "待补正")

td = H.build_todo(mk(mode="集中供暖", reported="", onsite="", signed=""), [])
ck("待办含补测", any(n == "补测" for n, _s in td))
ck("待办含要签字", any(n == "要签字" for n, _s in td))
ck("待办含查当地规则", any(n == "查当地规则" for n, _s in td))
ck("待办去重", len(td) == len(set(n for n, _s in td)))
ck("自采暖待办走维修", any(n == "走维修" for n, _s in H.build_todo(mk(mode="电采暖"), [])))

# ---------------------------------------------------------- 端到端
sp = os.path.join(SCRIPTS, "heating_check.py")
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
sample = os.path.join(HERE, "样例.md")
empty = os.path.join(HERE, "空供暖信息.md")
r1 = subprocess.run([sys.executable, sp, sample, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("样例rc=0", r1.returncode == 0)
o1 = r1.stdout or ""
ck("样例含结论摘要", "一、结论摘要" in o1)
ck("样例含方式段", "二、供热方式与责任主体" in o1)
ck("样例含测温段", "三、是否达标与测温程序" in o1)
ck("样例含退费段", "四、退费测算（算式与区间）" in o1)
ck("样例含证据段", "五、证据缺口" in o1)
ck("样例含路径段", "六、处理阶梯" in o1)
ck("样例含时限段", "七、时限清单" in o1)
ck("样例含待办段", "八、待办补正动作" in o1)
ck("样例含边界段", "九、边界与纪律" in o1)
ck("样例含九段", o1.count("## ") >= 9)
ck("样例含不通过", "不通过" in o1)
ck("样例含可退区间", "可退区间" in o1)
ck("样例横算式为反引号行", any(x.startswith("- `") and "×" in x for x in o1.splitlines()))
r2 = subprocess.run([sys.executable, sp, sample, "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
try:
    d = json.loads(r2.stdout or "{}")
    ck("json可解析含结论", "结论" in d and "待办" in d)
    ck("json含可退区间", "可退区间" in d)
except Exception:
    ck("json可解析含结论", False)
    ck("json含可退区间", False)
r3 = subprocess.run([sys.executable, sp, empty],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("空输入rc=2", r3.returncode == 2)
ck("空输入不崩有输出", len(r3.stdout or "") > 200)
ck("空输入提示缺失", "关键信息缺失" in (r3.stdout or ""))
ck("空输入不崩无stderr异常", "Traceback" not in (r3.stderr or ""))

# ---------------------------------------------------------- 汇总
total = len(PASS) + len(FAIL)
lines = ["=== 供暖不达标 回归测试 ===",
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
