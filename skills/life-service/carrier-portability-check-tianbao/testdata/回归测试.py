# -*- coding: utf-8 -*-
"""携号转网核查脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import carrier_check as C  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        carrier="", online_date="", status="", contract="", gift="",
        enterprise="", iot="", bundle="", subcard="", special_no="",
        bank="", sms="", thirdparty="", org="", applied="", applied_date="",
        port_out_date="", activated_yes=False, reject_reason="", written="",
        ticket="", miit="", hotline="", market="", evidence_owned="",
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
ck("norm去空格", C.norm("  中国移动 ") == "中国移动")
ck("norm统一冒号", C.norm("是否正常在网：否") == "是否正常在网:否")
ck("norm去全角逗号", C.norm("有,已合约") == "有,已合约")
ck("filled空串=False", C.filled("") is False)
ck("filled斜杠提示=False", C.filled("是/否") is False)
ck("filled有=True", C.filled("是") is True)
ck("filled待填=False", C.filled("待填写") is False)
ck("filledNone=False", C.filled(None) is False)
ck("yes是", C.yes("是") is True)
ck("yes正常", C.yes("正常在网") is True)
ck("no否", C.no("否") is True)
ck("no欠费", C.no("欠费") is True)
ck("no未结清", C.no("未结清") is True)
ck("unknown空", C.unknown("") is True)
ck("unknown不确定", C.unknown("不确定") is True)
ck("has_keyword命中", C.has_keyword("和宽带电视打捆", ["宽带", "ITV"]) is True)
ck("has_keyword未命中", C.has_keyword("单纯的手机卡", ["宽带", "ITV"]) is False)
ck("has_keyword未填", C.has_keyword("", ["宽带"]) is None)
ck("parse_num天", C.parse_num("267天") == 267.0)
ck("parse_num空", C.parse_num("") is None)
ck("fmt_num去.0", C.fmt_num(267.0) == "267")
ck("fmt_num保留小数", C.fmt_num(24.5) == "24.5")
ck("parse_date", C.parse_date("2026-01-10") == date(2026, 1, 10))
ck("parse_date空", C.parse_date("") is None)
ck("base_date兜底", isinstance(C.base_date(""), date))
ck("常量120天", C.CARRY_MIN_DAYS == 120)
ck("常量24小时", C.ACTIVATE_HOURS == 24)

# ---------------------------------------------------------- 解析
txt = C.read_text(os.path.join(HERE, "样例.md"))
kv = C.build_kv(txt)
ck("build_kv取运营商", C.get_text(kv, ["原运营商"]) == "中国移动")
ck("build_kv取入网日期", C.get_text(kv, ["入网或启用日期"]) == "2026-01-10")
ck("build_kv取合约", C.get_text(kv, ["是否有未到期合约"]) == "是")
ck("build_kv取工单字段", C.get_text(kv, ["是否取得客服工单编号"]) == "否")
ck("build_kv冒号行", C.get_text(C.build_kv("原运营商：中国联通\n"), ["原运营商"]) == "中国联通")
ck("build_kv最长别名优先",
   C.get_text({"是否宽带捆绑": "是", "捆绑": "否"}, ["是否宽带捆绑", "捆绑"]) == "是")
ck("get_text兜底alias", C.get_text({"号码所属运营商": "中国电信"}, ["所属运营商"]) == "中国电信")
ck("build_kv表头保留", C.build_kv("| 字段 | 值 |\n|---|---|\n| 原运营商 | 移动 |\n")["字段"] == "值")

# ---------------------------------------------------------- 运营商识别
ck("carrier移动", C.carrier_name("中国移动") == "中国移动")
ck("carrier联通", C.carrier_name("中国联通") == "中国联通")
ck("carrier电信", C.carrier_name("电信") == "中国电信")
ck("carrier广电", C.carrier_name("广电") == "中国广电")
ck("carrier未填", C.carrier_name("") == "未填")
ck("carrier其他", C.carrier_name("某虚拟商") == "其他运营商")

# ---------------------------------------------------------- 资格核查
q1 = C.checks_qualify(mk(carrier="中国移动", online_date="2026-01-10", status="是",
                         contract="否", gift="否"))
chk1("满120天通过", q1, "连续使用是否满 120 天", "通过")
chk1("在网正常通过", q1, "是否处于正常在网状态", "通过")
chk1("无合约通过", q1, "是否有未到期合约", "通过")
q2 = C.checks_qualify(mk(online_date="2026-09-01", status="否", contract="是", gift="是"))
chk1("未满120天不通过", q2, "连续使用是否满 120 天", "不通过")
chk1("欠费停机不通过", q2, "是否处于正常在网状态", "不通过")
chk1("有合约有风险", q2, "是否有未到期合约", "有风险")
chk1("赠品未结清不通过", q2, "是否有合约赠品未结清", "不通过")
q3 = C.checks_qualify(mk())
chk1("日期未填待补正", q3, "连续使用是否满 120 天", "待补正")
chk1("合约未填待补正", q3, "是否有未到期合约", "待补正")

# ---------------------------------------------------------- 不可携情形
b1 = C.checks_block(mk(enterprise="否", iot="否", bundle="是和宽带打捆",
                       subcard="是主卡挂了副卡", special_no="否"))
chk1("宽带捆绑不通过", b1, "宽带与电视捆绑", "不通过")
chk1("主副卡不通过", b1, "主副卡绑定", "不通过")
chk1("政企通过", b1, "政企专线与集团号", "通过")
chk1("物联网通过", b1, "物联网卡与车规卡", "通过")
b2 = C.checks_block(mk(enterprise="单位集团号", iot="是物联网卡", bundle="否",
                       subcard="否", special_no="靓号有低消"))
chk1("集团号不通过", b2, "政企专线与集团号", "不通过")
chk1("物联网不通过", b2, "物联网卡与车规卡", "不通过")
chk1("靓号不通过", b2, "特殊号码合约", "不通过")
b3 = C.checks_block(mk())
chk1("情形未填待补正", b3, "宽带与电视捆绑", "待补正")

# ---------------------------------------------------------- 风险
r1 = C.checks_risk(mk(bank="是", sms="否", thirdparty="是", org="否"))
chk1("银行预留有风险", r1, "银行预留与贷款绑定", "有风险")
chk1("验证码有风险", r1, "短信验证码接收", "有风险")
chk1("第三方有风险", r1, "第三方服务绑定", "有风险")
chk1("单位登记通过", r1, "单位与亲友登记", "通过")
r2 = C.checks_risk(mk(bank="否", sms="是", thirdparty="否", org="是"))
chk1("银行通过", r2, "银行预留与贷款绑定", "通过")
chk1("验证码通过", r2, "短信验证码接收", "通过")
chk1("亲友登记有风险", r2, "单位与亲友登记", "有风险")
r3 = C.checks_risk(mk())
chk1("风险未填待补正", r3, "银行预留与贷款绑定", "待补正")

# ---------------------------------------------------------- 时限
t1 = C.checks_time(mk(online_date="2026-01-10"), TODAY)
chk1("资格届满通过", t1, "120 天资格届满日", "通过")
t2 = C.checks_time(mk(online_date="2026-09-30"), TODAY)
chk1("资格未到有风险", t2, "120 天资格届满日", "有风险")
t3 = C.checks_time(mk(applied="是", port_out_date="2026-10-01", activated_yes=False), TODAY)
chk1("窗口已过不通过", t3, "24 小时激活窗口", "不通过")
t4 = C.checks_time(mk(applied="是", port_out_date="2026-10-05", activated_yes=False), TODAY)
chk1("当日携出有风险", t4, "24 小时激活窗口", "有风险")
t5 = C.checks_time(mk(applied="是", port_out_date="2026-10-04", activated_yes=True), TODAY)
chk1("已激活通过", t5, "24 小时激活窗口", "通过")
t6 = C.checks_time(mk(applied="是", applied_date="2026-08-01"), TODAY)
chk1("受理超30天有风险", t6, "申请受理时效", "有风险")
t7 = C.checks_time(mk(applied="是", applied_date="2026-10-01"), TODAY)
chk1("受理中通过", t7, "申请受理时效", "通过")
t8 = C.checks_time(mk(), TODAY)
chk1("未申请窗口待补正", t8, "24 小时激活窗口", "待补正")

# ---------------------------------------------------------- 拒绝与申诉
d1 = C.checks_refuse(mk(reject_reason="号码使用协议约定的合约期未满", written="否"))
chk1("合约理由有风险", d1, "是否被拒绝及理由", "有风险")
chk1("无书面不通过", d1, "是否取得书面告知", "不通过")
d2 = C.checks_refuse(mk(reject_reason="该号码为政企专线", written="是"))
chk1("业务限制有风险", d2, "是否被拒绝及理由", "有风险")
chk1("有书面通过", d2, "是否取得书面告知", "通过")
d3 = C.checks_refuse(mk(reject_reason="号码欠费停机", written="否"))
chk1("状态异常有风险", d3, "是否被拒绝及理由", "有风险")
d4 = C.checks_refuse(mk())
chk1("未填理由待补正", d4, "是否被拒绝及理由", "待补正")
d5 = C.checks_refuse(mk(reject_reason="随便说的理由"))
chk1("其他理由有风险", d5, "是否被拒绝及理由", "有风险")

# ---------------------------------------------------------- 投诉渠道
c1 = C.checks_complaint(mk(ticket="是", miit="否", hotline="否", market="否"))
chk1("工单通过", c1, "原运营商客服工单", "通过")
chk1("工信部未走有风险", c1, "工信部申诉渠道（12300/12378）", "有风险")
chk1("12345未走有风险", c1, "12345 政务热线", "有风险")
chk1("12315未走有风险", c1, "12315 消费投诉", "有风险")
c2 = C.checks_complaint(mk())
chk1("渠道未填待补正", c2, "12345 政务热线", "待补正")

# ---------------------------------------------------------- 证据
e1 = C.checks_evidence(mk(evidence_owned="身份证复印件,话费账单,入网协议,受理单,告知书,申诉答复"))
ck("六类证据条数", len(e1) == 6)
chk1("身份证据通过", e1, "身份与号码证明证据", "通过")
chk1("时长证据通过", e1, "时长与在网证明证据", "通过")
chk1("拒绝证据通过", e1, "拒绝与告知证据证据", "通过")
e2 = C.checks_evidence(mk())
chk1("证据未填待补正", e2, "证据总览", "待补正")
e3 = C.checks_evidence(mk(evidence_desc="只有身份证复印件"))
chk1("部分证据有风险", e3, "时长与在网证明证据", "有风险")
g1 = C.evidence_gap(mk(written="否", online_date="2026-01-10", applied="是"))
ck("缺口含拒绝证据", "拒绝与告知证据" in g1)
ck("缺口含申请受理", "申请与受理证明" in g1)
g2 = C.evidence_gap(mk(evidence_owned="身份证复印件,话费账单,入网协议,受理单,告知书,申诉答复,激活截图",
                       written="是"))
ck("证据齐全无缺口", len(g2) == 0)

# ---------------------------------------------------------- 路径与待办
p1 = C.path_steps(mk(carrier="中国移动"))
ck("路径第1步讲资格", "120" in p1[0][1])
ck("路径含工单编号", any("工单号" in t for _s, t in p1))
ck("路径含12345", any("12345" in t for _s, t in p1))
ck("路径含24小时激活", any("24 小时" in t for _s, t in p1))
td = C.todo_list(mk(written="否", ticket="否", bank="是", sms="否"), [])
ck("待办含书面告知", any(n == "索取书面告知" for n, _s in td))
ck("待办含工单编号", any(n == "要工单编号" for n, _s in td))
ck("待办含银行换绑", any(n == "换绑银行预留号" for n, _s in td))
ck("待办去重", len(td) == len(set(n for n, _s in td)))

# ---------------------------------------------------------- 端到端
sp = os.path.join(SCRIPTS, "carrier_check.py")
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
ck("样例含资格段", "二、资格条件逐项核查" in o1)
ck("样例含不可携段", "三、不可携情形核查" in o1)
ck("样例含风险段", "四、号码与账户风险" in o1)
ck("样例含时限段", "五、时限倒计时" in o1)
ck("样例含拒绝段", "六、拒绝情形与申诉阶梯" in o1)
ck("样例含投诉段", "七、投诉渠道与受理" in o1)
ck("样例含证据段", "八、证据清单与缺口" in o1)
ck("样例含路径段", "九、办理与申诉路径排序" in o1)
ck("样例含待办段", "十一、待办补正动作" in o1)
ck("样例含边界段", "边界与纪律" in o1)
ck("样例段数>=11", o1.count("## ") >= 11)
ck("样例含不通过", "不通过" in o1)
ck("样例含有风险", "有风险" in o1)
ck("样例含120天", "120" in o1)
ck("样例含24小时", "24" in o1)
ck("样例含合约未满", "合约" in o1)
ck("样例无乱码", "\ufffd" not in o1)
r2 = subprocess.run([sys.executable, sp, sample, "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env)
try:
    d = json.loads(r2.stdout or "{}")
    ck("json可解析含结论", "结论" in d and "待办" in d)
    ck("json含运营商", d.get("运营商") == "中国移动")
    ck("json含证据缺口", isinstance(d.get("证据缺口"), list) and len(d["证据缺口"]) > 0)
except Exception:
    ck("json可解析含结论", False)
    ck("json含运营商", False)
    ck("json含证据缺口", False)
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
lines = ["=== 携号转网 回归测试 ===",
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
