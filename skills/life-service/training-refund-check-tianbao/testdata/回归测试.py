# -*- coding: utf-8 -*-
"""培训退费核算脚本回归测试（断言 56 条）。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import training_refund_check as P  # noqa: E402

PASS = []
FAIL = []


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        train_type="", org="", stage="", contract_date="", paid=None,
        contract_price=None, total_lessons=None, bonus_lessons=None,
        used_lessons=None, list_price=None, material_fee=None,
        material_agreed="", material_returnable="", penalty_rate=None,
        penalty_amt=None, loss_amt=None, charge_span=None, license="",
        holiday_class="", org_status="", not_started="", long_stop="",
        teacher_mismatch="", false_promo="", venue_change="", stop_reason="",
        loan="", loan_notice="", loan_status="", loan_contact="", clause="",
        negotiated="", org_reply="", arbitration="", issue_date="", evidence="",
    )
    base.update(kw)
    return base


def chk1(name, rows, item, state=None):
    """在 rows 中按 r[0] 精确匹配 item（注意别写成 r[0]==name）。"""
    for r in rows:
        if r[0] == item:
            if state is None:
                ck(name + "被触发", True)
            else:
                ck(name + "=" + state, r[1] == state)
            return
    ck(name + "(未出现)", state is None)


def msgs(rows):
    return [r[2] for r in rows]


# ---------------------------------------------------------- 基础工具
ck("norm去空格", P.norm("  有  ") == "有")
ck("norm统一冒号", P.norm("培训类型：学科类") == "培训类型:学科类")
ck("core去括号", P.core("是（附医院病历）") == "是")
ck("filled空串=False", P.filled("") is False)
ck("filled斜杠提示=False", P.filled("是/否/不清楚") is False)
ck("filled有=True", P.filled("是") is True)
ck("filled待填=False", P.filled("待填") is False)
ck("yes带括号", P.yes("是（附医院病历）") is True)
ck("no带括号", P.no("否（教材已发）") is True)
ck("yes已放款不误判为是", P.yes("已放款，按月自动扣款") is False)
ck("no否", P.no("否") is True)
ck("unknown不清楚", P.unknown("不清楚") is True)
ck("unknown空", P.unknown("") is True)
ck("unknown已填", P.unknown("是") is False)
ck("parse_num元", P.parse_num("30000元") == 30000.0)
ck("parse_num逗号", P.parse_num("1,200") == 1200.0)
ck("parse_num空", P.parse_num("") is None)
ck("fmt_num去.0", P.fmt_num(200.0) == "200")
ck("fmt_num保留小数", P.fmt_num(200.5) == "200.5")
ck("parse_date", P.parse_date("2026-09-15") == date(2026, 9, 15))
ck("parse_date空", P.parse_date("") is None)
ck("base_date兜底", isinstance(P.base_date(""), date))
ck("add_years跨3年", P.add_years(date(2026, 9, 15), 3) == date(2029, 9, 15))

# ---------------------------------------------------------- 解析
txt = P.read_text(os.path.join(HERE, "样例.md"))
kv = P.build_kv(txt)
ck("build_kv表格取培训类型", P.get_text(kv, ["培训类型"]) == "学科类（中考语文冲刺）")
ck("build_kv取实付总额", P.get_text(kv, ["实付总额"]).strip() == "30000")
ck("build_kv取赠送课时", P.get_text(kv, ["赠送课时"]).strip() == "30")
ck("build_kv取教材费", P.get_text(kv, ["教材教辅物品费金额"]).strip() == "2000")
ck("build_kv空值行不写入",
   "" not in P.build_kv("| 合同约定的课时单价 | |\n"))
kv2 = P.build_kv("培训类型：职业技能\n实付总额：8800\n")
ck("build_kv冒号行", P.get_text(kv2, ["培训类型"]) == "职业技能")
ck("get_text最长别名优先",
   P.get_text({"培训类型": "学科类", "类型": "素质类"}, ["培训类型", "类型"]) == "学科类")
ck("get_text兜底alias", P.get_text({"所在城市": "上海"}, ["城市"]) == "上海")
ck("get_text空值不被别行抢走",
   P.get_text({"合同约定的课时单价": "", "机构主张的原价课时单价": "400"},
              ["合同约定的课时单价", "原价课时单价"]) == "400")

# ---------------------------------------------------------- 课时单价
p1, b1, n1 = P.unit_price(mk(paid=30000.0, total_lessons=120, bonus_lessons=30))
ck("折算单价=200", abs(p1 - 200.0) < 1e-6)
ck("折算basis", b1 == "优惠后折算单价")
ck("折算note含赠课口径", "赠课" in n1 and "摊薄" in n1)
p2, b2, n2 = P.unit_price(mk(paid=30000.0, total_lessons=120, bonus_lessons=30,
                             contract_price=400.0))
ck("合同单价优先", abs(p2 - 400.0) < 1e-6 and b2 == "合同约定的课时单价")
ck("合同单价高于折算有提示", "优惠后折算单价" in n2)
p3, b3, n3 = P.unit_price(mk(paid=30000.0, total_lessons=120, list_price=500.0))
ck("原价抬高有提示", "不应采纳" in n3)
p4, b4, n4 = P.unit_price(mk(paid=None, total_lessons=120))
ck("无实付未认定", p4 is None and b4 == "未认定")
p5, _b5, n5 = P.unit_price(mk(paid=30000.0, total_lessons=120, contract_price=400.0,
                              list_price=500.0))
ck("合同单价不取原价", abs(p5 - 400.0) < 1e-6)

# ---------------------------------------------------------- 金额测算
rows, s1 = P.calc_amount(mk(paid=30000.0, total_lessons=120, bonus_lessons=30,
                            used_lessons=36, material_fee=2000.0,
                            material_agreed="是", material_returnable="否",
                            penalty_rate=30.0))
chk1("已消耗课时费", rows, "已消耗课时费", "通过")
ck("已消耗课时费算式", any("36 课时 × 200 元/课时" in m for m in msgs(rows)))
ck("建议退费=11800", abs(s1["refund"] - 11800.0) < 1e-6)
ck("区间下限=11800", abs(s1["lower"] - 11800.0) < 1e-6)
ck("区间上限=20800", abs(s1["upper"] - 20800.0) < 1e-6)
rows0, s0 = P.calc_amount(mk(paid=30000.0, total_lessons=120, used_lessons=36))
chk1("无违约金待补正", rows0, "建议退费金额", "待补正")
ck("无违约金不给金额", s0["refund"] is None)

rows2, s2 = P.calc_amount(mk(paid=30000.0, total_lessons=120, bonus_lessons=30,
                             used_lessons=36, material_fee=2000.0,
                             material_agreed="是", material_returnable="否",
                             penalty_rate=30.0))
ck("教材可计入扣款", abs(s2["mat"] - 2000.0) < 1e-6)
ck("教材计入后退费=11800", abs(s2["refund"] - 11800.0) < 1e-6)

rows3, s3 = P.calc_amount(mk(paid=30000.0, total_lessons=120, used_lessons=36,
                             material_fee=2000.0, material_agreed="是",
                             material_returnable="是"))
ck("教材可回收不计入", abs(s3["mat"] - 0.0) < 1e-6)

rows4, s4 = P.calc_amount(mk(paid=30000.0, total_lessons=120, used_lessons=36,
                             material_fee=2000.0, material_agreed="否"))
ck("教材未约定不计入", abs(s4["mat"] - 0.0) < 1e-6)
ck("教材未约定有风险", ("教材教辅物品费", "有风险") in [(r[0], r[1]) for r in rows4])

rows5, s5 = P.calc_amount(mk(paid=30000.0, total_lessons=120, used_lessons=36,
                             penalty_rate=30.0, loss_amt=2000.0))
ck("违约金超损失取2000", abs(s5["pen"] - 2000.0) < 1e-6)
ck("违约金超损失有调减提示", any("调减" in m for m in msgs(rows5)))

rows6, s6 = P.calc_amount(mk(paid=30000.0, total_lessons=120, bonus_lessons=30,
                             used_lessons=36, penalty_rate=30.0, loss_amt=9000.0))
ck("违约金未超损失按9000", abs(s6["pen"] - 9000.0) < 1e-6)
ck("违约金未超损失退费=13800", abs(s6["refund"] - 13800.0) < 1e-6)

rows7, s7 = P.calc_amount(mk(paid=30000.0, total_lessons=120, used_lessons=36,
                             penalty_amt=5000.0))
ck("按比例兜底取约定金额", abs(s7["pen"] - 5000.0) < 1e-6)

rows8 = P.calc_amount(mk(paid=None))[0]
chk1("无实付", rows8, "实付总额", "待补正")

rows9, _s9 = P.calc_amount(mk(paid=30000.0, total_lessons=120, used_lessons=36,
                              list_price=400.0, penalty_rate=30.0))
chk1("原价比对", rows9, "机构原价比对", "有风险")
ck("原价比对含退费将降至", any("退费将降至" in m for m in msgs(rows9)))

rows10, _s10 = P.calc_amount(mk(paid=30000.0, total_lessons=120, used_lessons=200))
chk1("超总课时", rows10, "已消耗课时", "有风险")

# ---------------------------------------------------------- 单价认定段
rp = P.checks_price(mk(paid=30000.0, total_lessons=120, bonus_lessons=30,
                       list_price=400.0))
chk1("认定通过", rp, "课时单价认定", "通过")
chk1("不按原价扣款", rp, "不按原价扣款", "通过")
chk1("赠课摊薄", rp, "赠课摊薄单价", "通过")
rp2 = P.checks_price(mk(paid=None))
chk1("未认定待补正", rp2, "课时单价认定", "待补正")

# ---------------------------------------------------------- 格式条款
rpp = P.checks_penalty(mk(clause="概不退费，开课后不退，费用不退"))
chk1("格式条款不通过", rpp, "格式条款核查", "不通过")
ck("格式条款标出词", any("概不退费" in m for m in msgs(rpp)))
rpp2 = P.checks_penalty(mk(clause="按未完成课时比例退费"))
chk1("无绝对化表述通过", rpp2, "格式条款核查", "通过")
rpp3 = P.checks_penalty(mk())
chk1("未摘录待补正", rpp3, "格式条款核查", "待补正")
rpp4 = P.checks_penalty(mk(clause="概不退费", org_reply="合同写了概不退费，开课后不退"))
chk1("机构口径有风险", rpp4, "机构口径", "有风险")

# ---------------------------------------------------------- 许可与双减
rl = P.checks_license(mk(license="否"))
chk1("无许可不通过", rl, "办学许可", "不通过")
rl2 = P.checks_license(mk(train_type="学科类", stage="初中", holiday_class="是"))
chk1("节假日培训不通过", rl2, "双减—培训时间", "不通过")
ck("双减表述含法定节假日", any("国家法定节假日" in m for m in msgs(rl2)))
rl3 = P.checks_license(mk(train_type="学科类", stage="初中", holiday_class="否",
                          license="有", charge_span=2, total_lessons=40))
chk1("双减时间通过", rl3, "双减—培训时间", "通过")
chk1("预收费未超标通过", rl3, "预收费监管", "通过")
rl4 = P.checks_license(mk(charge_span=6, total_lessons=120))
chk1("超3月超60课时不通过", rl4, "预收费监管", "不通过")
ck("超期超额本身违规", any("本身即属违规" in m for m in msgs(rl4)))
rl5 = P.checks_license(mk(license=""))
chk1("许可未填待补正", rl5, "办学许可", "待补正")
rl5b = P.checks_license(mk(train_type="学科类", stage="初中"))
chk1("双减时间未填待补正", rl5b, "双减—培训时间", "待补正")
ck("双减未填有刚性提示", any("这是双减的硬性要求" in m for m in msgs(rl5b)))

# ---------------------------------------------------------- 机构违约
rb = P.checks_breach(mk(long_stop="是"))
chk1("长期停课不通过", rb, "长期停课", "不通过")
rb2 = P.checks_breach(mk(org_status="跑路失联"))
chk1("机构跑路不通过", rb2, "机构现状", "不通过")
rb3 = P.checks_breach(mk(org_status="正常经营"))
chk1("正常经营通过", rb3, "机构现状", "通过")
rb4 = P.checks_breach(mk(false_promo="是"))
chk1("虚假宣传不通过", rb4, "虚假宣传（保过/包就业/名师）", "不通过")
rb5 = P.checks_breach(mk())
chk1("未填待补正", rb5, "机构现状", "待补正")
ck("未填可主张力度待补正",
   any(r[0] == "可主张的退费力度" and r[1] == "待补正" for r in rb5))
rb6 = P.checks_breach(mk(long_stop="是", teacher_mismatch="是"))
ck("力度汇总计数", any("已触发 2 项" in m for m in msgs(rb6)))

# ---------------------------------------------------------- 培训贷
rl2n = P.checks_loan(mk(loan="否"))
chk1("无贷通过", rl2n, "培训贷/分期", "通过")
rl3n = P.checks_loan(mk(loan="是", loan_status="已逾期"))
chk1("逾期不通过", rl3n, "还款状态", "不通过")
ck("逾期提示征信", any("征信" in m for m in msgs(rl3n)))
rl4n = P.checks_loan(mk(loan="是", loan_status="已放款"))
chk1("已放款有风险", rl4n, "还款状态", "有风险")
rl5n = P.checks_loan(mk(loan="是", loan_status="已放款", loan_notice="否"))
chk1("未告知有风险", rl5n, "机构告知义务", "有风险")
rl6n = P.checks_loan(mk(loan="是", loan_contact="是"))
chk1("已沟通通过", rl6n, "与贷款方沟通", "通过")
rl7n = P.checks_loan(mk())
chk1("未填待补正", rl7n, "培训贷/分期", "待补正")

# ---------------------------------------------------------- 路径与待办
st = P.path_order(mk())
ck("路径第1步要求退费明细", "退费方案与计算明细" in st[0][1])
ck("路径含市场监管与12345",
   ("市场监督" in " ".join(t for _s, t in st)) and ("12345" in " ".join(t for _s, t in st)))
ck("路径含仲裁", "仲裁" in " ".join(t for _s, t in st))
ck("路径含小额诉讼", "小额诉讼" in " ".join(t for _s, t in st))
todo = P.todo_list(mk(loan="是", loan_contact="否", license="否"), [], {})
ck("待办含先保征信", any(n == "先保征信" for n, _s in todo))
ck("待办含时效倒计时", any(n == "时效倒计时" for n, _s in todo))
todo2 = P.todo_list(mk(), [], {})
ck("无贷也含书面交涉", any(n == "书面索要退费明细" for n, _s in todo2))

# ---------------------------------------------------------- 端到端
sp = os.path.join(SCRIPTS, "training_refund_check.py")
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
ck("样例含待办段", "九、待办补正动作" in o1)
ck("样例含十段", o1.count("## ") >= 9)
ck("样例含不通过", "不通过" in o1)
ck("样例含金额段", "二、退费金额核算" in o1)
ck("样例含单价段", "三、课时单价认定" in o1)
ck("样例含培训贷段", "七、培训贷与征信风险" in o1)
ck("样例含边界纪律", "边界与纪律" in o1)
ck("样例含建议退费11800", "11800" in o1)
r2 = subprocess.run([sys.executable, sp, sample, "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
try:
    d = json.loads(r2.stdout or "{}")
    ck("json可解析含三键", "结论" in d and "风险项" in d and "待办" in d)
    ck("json结论为有风险", d["结论"] == "有风险")
    ck("json退费金额", d["建议退费金额"] == 11800)
except Exception:
    ck("json可解析含三键", False)
    ck("json结论为有风险", False)
    ck("json退费金额", False)
r3 = subprocess.run([sys.executable, sp, empty],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("空输入rc=2", r3.returncode == 2)
ck("空输入不崩有输出", len(r3.stdout or "") > 200)
ck("空输入提示缺失", "关键信息缺失" in (r3.stdout or ""))
ck("空输入含待补正", "待补正" in (r3.stdout or ""))

# ---------------------------------------------------------- 汇总
total = len(PASS) + len(FAIL)
lines = ["=== 培训退费核算 回归测试 ===",
         "PASS=%d FAIL=%d TOTAL=%d" % (len(PASS), len(FAIL), total), ""]
for n in PASS:
    lines.append("  ok  " + n)
for n in FAIL:
    lines.append("  FAIL " + n)
lines.append("")
lines.append("RESULT: %s" % ("ALL PASS" if not FAIL else "FAILED"))
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(lines[:3]))
sys.exit(1 if FAIL else 0)
