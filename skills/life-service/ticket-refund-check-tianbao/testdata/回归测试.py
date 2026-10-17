# -*- coding: utf-8 -*-
"""交通票务退改签核查脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import rail_air_refund_check as T  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        mode="", trip_no="", dep_date="", face="", paid="", insurance="",
        checked="", ticket_taken="", reason="", non_traveller_claim=False,
        rebooked="", applied="", ticket_no="", refunded="", self="",
        csr="", hotline="", market="", gov="", evidence_owned="",
        evidence_desc="", today=TODAY,
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
ck("norm去空格", T.norm("  铁路  ") == "铁路")
ck("norm统一冒号", T.norm("退改原因：生病") == "退改原因:生病")
ck("filled空串=False", T.filled("") is False)
ck("filled斜杠提示=False", T.filled("是/否") is False)
ck("filled待填=False", T.filled("待填") is False)
ck("filledNone=False", T.filled(None) is False)
ck("yes是", T.yes("是") is True)
ck("yes已取消", T.yes("已取消") is True)
ck("no否", T.no("否") is True)
ck("no正常", T.no("正常") is True)
ck("unknown空", T.unknown("") is True)
ck("parse_num元", T.parse_num("553元") == 553.0)
ck("parse_num空", T.parse_num("") is None)
ck("fmt_num去.0", T.fmt_num(553.0) == "553")
ck("fmt_num保留两位", T.fmt_num(525.35) == "525.35")
ck("money前缀", T.money(553.0) == "¥553")
ck("parse_date", T.parse_date("2026-10-08") == date(2026, 10, 8))
ck("parse_date空", T.parse_date("") is None)
ck("base_date兜底", isinstance(T.base_date(""), date))
ck("hit_any命中", T.hit_any("航班取消", ["取消", "停飞"]) is True)
ck("hit_any未命中", T.hit_any("自己不想去", ["取消"]) is False)
ck("hit_any未填", T.hit_any("", ["取消"]) is None)

# ---------------------------------------------------------- 票种识别
ck("mode铁路", T.mode_kind("铁路")[1] == "rail")
ck("mode高铁", T.mode_kind("高铁")[1] == "rail")
ck("mode12306", T.mode_kind("12306")[1] == "rail")
ck("mode民航", T.mode_kind("民航")[1] == "air")
ck("mode机票", T.mode_kind("机票")[1] == "air")
ck("mode大巴", T.mode_kind("长途客运")[1] == "other")
ck("mode空", T.mode_kind("")[1] is None)
ck("mode中文名", T.mode_kind("火车")[0] == "铁路")

# ---------------------------------------------------------- 剩余小时
ck("hours72", T.hours_to_dep(mk(dep_date="2026-10-08")) == 72.0)
ck("hours负", T.hours_to_dep(mk(dep_date="2026-10-01")) == -96.0)
ck("hours空", T.hours_to_dep(mk()) is None)

# ---------------------------------------------------------- 票种与可退性
y1 = T.checks_type(mk(mode="铁路", dep_date="2026-10-08", checked="否", ticket_taken="是"))
chk1("铁路定性通过", y1, "票种定性", "通过")
chk1("72小时有风险", y1, "距发车或起飞时间", "有风险")
chk1("已取票有风险", y1, "是否已取票或取报销凭证", "有风险")
chk1("未检票通过", y1, "是否已检票或值机", "通过")
y2 = T.checks_type(mk(mode="铁路", dep_date="2026-10-04", checked="否", ticket_taken="否"))
chk1("已发车不通过", y2, "距发车或起飞时间", "不通过")
y3 = T.checks_type(mk(mode="铁路", dep_date="2026-10-30", checked="是", ticket_taken="否"))
chk1("远期通过", y3, "距发车或起飞时间", "通过")
chk1("已检票不通过", y3, "是否已检票或值机", "不通过")
y4 = T.checks_type(mk())
chk1("票种未填待补正", y4, "票种定性", "待补正")
y5 = T.checks_type(mk(mode="民航", dep_date="2026-10-05", checked="否", ticket_taken="否"))
chk1("民航24小时内有风险", y5, "距发车或起飞时间", "有风险")
chk1("民航定性通过", y5, "票种定性", "通过")

# ---------------------------------------------------------- 原因定性
r1 = T.checks_reason(mk(reason="航班因天气取消"))
chk1("承运方原因通过", r1, "退改原因定性", "通过")
r2 = T.checks_reason(mk(reason="自己不想去了"))
chk1("个人原因有风险", r2, "退改原因定性", "有风险")
r3 = T.checks_reason(mk(reason="家中老人突发疾病住院"))
chk1("疾病有风险", r3, "退改原因定性", "有风险")
r4 = T.checks_reason(mk(reason="说不清的原因"))
chk1("其他原因有风险", r4, "退改原因定性", "有风险")
r5 = T.checks_reason(mk())
chk1("原因未填待补正", r5, "退改原因定性", "待补正")

# ---------------------------------------------------------- 手续费测算
c1 = T.calc_refund(mk(mode="铁路", dep_date="2026-10-30", face="553"))
ck("远期费率0", c1["费率"] == 0.0)
ck("远期可退全额", abs(c1["可退"] - 553.0) < 1e-9)
ck("远期算式非空", len(c1["算式"]) == 2)
c2 = T.calc_refund(mk(mode="铁路", dep_date="2026-10-08", face="553"))
ck("72小时费率5%", abs(c2["费率"] - 0.05) < 1e-9)
ck("72小时手续费27.65", abs(c2["手续费"] - 27.65) < 0.01)
ck("72小时可退525.35", abs(c2["可退"] - 525.35) < 0.01)
c3 = T.calc_refund(mk(mode="铁路", dep_date="2026-10-06", face="1000"))
ck("48小时费率10%", abs(c3["费率"] - 0.10) < 1e-9)
c4 = T.calc_refund(mk(mode="铁路", dep_date="2026-10-05", face="1000"))
ck("不足24小时费率20%", abs(c4["费率"] - 0.20) < 1e-9)
c5 = T.calc_refund(mk(mode="民航", dep_date="2026-10-30", face="2000"))
ck("民航远期0", c5["费率"] == 0.0)
c6 = T.calc_refund(mk(mode="民航", dep_date="2026-10-08", face="2000"))
ck("民航7天内10%", abs(c6["费率"] - 0.10) < 1e-9)
c7 = T.calc_refund(mk(mode="铁路", dep_date="2026-10-01", face="553"))
ck("已发车可退为None", c7["可退"] is None)
ck("已发车有说明", "开车后" in c7["说明"])
c8 = T.calc_refund(mk(mode="铁路", dep_date="2026-10-08", face=""))
ck("缺金额无法测算", c8["可退"] is None)
c9 = T.calc_refund(mk(mode="铁路", dep_date="", face="553"))
ck("缺日期无法定位档位", c9["可退"] is None)
c10 = T.calc_refund(mk(mode="大巴", dep_date="2026-10-08", face="100"))
ck("非铁路民航不适用", c10["适用"] is False)
c11 = T.calc_refund(mk(mode="铁路", dep_date="2026-10-08", face="553", paid="558"))
ck("实付不同有提示", any("实付" in x for x in c11["算式"]))
c12 = T.calc_refund(mk(mode="铁路", dep_date="2026-10-08", face="553",
                       non_traveller_claim=True))
ck("主张非旅客原因有说明", "非旅客原因" in c12["说明"])

# ---------------------------------------------------------- 金额段
a1 = T.checks_amount(mk(mode="铁路", dep_date="2026-10-30", face="553", insurance="否",
                       rebooked="否"), c1)
chk1("免手续费通过", a1, "退票手续费", "通过")
chk1("无保险通过", a1, "保险与附加费", "通过")
chk1("未改签通过", a1, "是否已改签过", "通过")
a2 = T.checks_amount(mk(mode="铁路", dep_date="2026-10-08", face="553", insurance="是",
                       rebooked="是"), c2)
chk1("收费有风险", a2, "退票手续费", "有风险")
chk1("保险有风险", a2, "保险与附加费", "有风险")
chk1("已改签有风险", a2, "是否已改签过", "有风险")
a3 = T.checks_amount(mk(mode="大巴", dep_date="2026-10-08", face="100"), c10)
chk1("不适用待补正", a3, "退票手续费测算", "待补正")

# ---------------------------------------------------------- 流程与到账
p1 = T.checks_process(mk(applied="是", ticket_no="是", refunded="否"))
chk1("已申请通过", p1, "是否已提交退改申请", "通过")
chk1("有工单通过", p1, "是否取得工单号或受理编号", "通过")
chk1("未到账有风险", p1, "票款是否已到账", "有风险")
p2 = T.checks_process(mk(applied="否", ticket_no="否"))
chk1("未申请不通过", p2, "是否已提交退改申请", "不通过")
chk1("无工单不通过", p2, "是否取得工单号或受理编号", "不通过")
p3 = T.checks_process(mk())
chk1("流程未填待补正", p3, "票款是否已到账", "待补正")

# ---------------------------------------------------------- 投诉阶梯
c_1 = T.checks_complaint(mk(self="是", csr="是", hotline="否", market="否", gov="否"))
chk1("自助通过", c_1, "承运方自助渠道（12306/航司 App）", "通过")
chk1("12345未走有风险", c_1, "12345 政务热线", "有风险")
chk1("12315未走有风险", c_1, "12315 消费投诉", "有风险")
chk1("主管部门未走有风险", c_1, "民航/铁路主管部门渠道", "有风险")
c_2 = T.checks_complaint(mk())
chk1("渠道未填待补正", c_2, "12345 政务热线", "待补正")

# ---------------------------------------------------------- 证据
e1 = T.checks_evidence(mk(evidence_owned="订单号,购票记录,退票申请,工单,扣费记录,医院,病历,答复"))
ck("证据条数", len(e1) == 6)
chk1("购票凭证通过", e1, "购票凭证证据", "通过")
chk1("原因证明通过", e1, "原因证明证据", "通过")
e2 = T.checks_evidence(mk())
chk1("证据未填待补正", e2, "证据总览", "待补正")
e3 = T.checks_evidence(mk(evidence_desc="只有订单号"))
chk1("部分证据有风险", e3, "原因证明证据", "有风险")
g1 = T.evidence_gap(mk(reason="航班因天气取消", ticket_no="否"))
ck("缺口含不可抗力证明", "不可抗力证明" in g1)
g2 = T.evidence_gap(mk(reason="自己生病住院", ticket_no="是"))
ck("缺口含原因证明", "原因证明" in g2)
ck("无工单含申请记录", "退改申请记录" in T.evidence_gap(mk(ticket_no="否")))

# ---------------------------------------------------------- 路径与待办
p_1 = T.path_steps(mk(mode="铁路"))
ck("铁路路径讲8天", any("8 天" in t for _s, t in p_1))
ck("铁路路径含12315", any("12315" in t for _s, t in p_1))
p_2 = T.path_steps(mk(mode="民航"))
ck("民航路径讲7天", any("7 天" in t for _s, t in p_2))
ck("民航路径含承运人", any("承运人" in t for _s, t in p_2))
p_3 = T.path_steps(mk(mode="大巴"))
ck("其他客运路径查规则", any("规则" in t for _s, t in p_3))
td = T.todo_list(mk(applied="否", ticket_no="否", refunded="否"), [], c2)
ck("待办含提交申请", any(n == "提交退改申请" for n, _s in td))
ck("待办含工单号", any(n == "取工单号" for n, _s in td))
ck("待办含先比改签", any(n == "先比改签" for n, _s in td))
ck("待办含盯到账", any(n == "盯退款到账" for n, _s in td))
ck("待办去重", len(td) == len(set(n for n, _s in td)))

# ---------------------------------------------------------- 端到端
sp = os.path.join(SCRIPTS, "rail_air_refund_check.py")
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
ck("样例含票种段", "二、票种与可退性定性" in o1)
ck("样例含原因段", "三、退改原因定性" in o1)
ck("样例含测算段", "四、退票手续费测算" in o1)
ck("样例含流程段", "五、办理流程与到账" in o1)
ck("样例含投诉段", "六、投诉与申诉阶梯" in o1)
ck("样例含证据段", "七、证据清单与缺口" in o1)
ck("样例含路径段", "八、退改路径排序" in o1)
ck("样例含待办段", "十、待办补正动作" in o1)
ck("样例含边界段", "边界与纪律" in o1)
ck("样例段数>=10", o1.count("## ") >= 10)
ck("样例含金额525.35", "525.35" in o1)
ck("样例含铁路", "铁路" in o1)
ck("样例含不通过或风险", ("不通过" in o1) or ("有风险" in o1))
ck("样例无乱码", "\ufffd" not in o1)
r2 = subprocess.run([sys.executable, sp, sample, "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
try:
    d = json.loads(r2.stdout or "{}")
    ck("json可解析含结论", "结论" in d and "待办" in d)
    ck("json票种正确", d.get("票种") == "铁路")
    ck("json含退费测算", abs(d["退费测算"]["可退金额"] - 525.35) < 0.01)
except Exception:
    ck("json可解析含结论", False)
    ck("json票种正确", False)
    ck("json含退费测算", False)
r3 = subprocess.run([sys.executable, sp, empty, "--base", "2026-10-05"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
ck("空输入rc=2", r3.returncode == 2)
ck("空输入不崩有输出", len(r3.stdout or "") > 400)
ck("空输入提示缺失", "关键信息缺失" in (r3.stdout or ""))
ck("空输入无异常", "Traceback" not in (r3.stderr or ""))
ck("空输入段数>=10", (r3.stdout or "").count("## ") >= 10)

# ---------------------------------------------------------- 汇总
total = len(PASS) + len(FAIL)
lines = ["=== 交通票务退改签 回归测试 ===",
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
