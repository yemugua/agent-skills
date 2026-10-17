# -*- coding: utf-8 -*-
"""健身房私教课退费与套路识别 —— 回归测试（>=40 断言）。"""
import json
import os
import re
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

import gym_pt_refund_check as M  # noqa: E402

PASS = []
FAIL = []


def chk(name, cond):
    (PASS if cond else FAIL).append(name)


BASE = date(2026, 10, 4)

chk("norm 归一", M.norm(" 未 填写 ") == "未填写")
chk("filled 正常", M.filled("29800元") is True)
chk("unknown 待填", M.unknown("待填") is True)
chk("unknown 待补", M.unknown("待补") is True)
chk("unknown 待确认", M.unknown("待确认") is True)
chk("unknown 斜杠", M.unknown("/") is True)
chk("unknown 未填写", M.unknown("未填写") is True)
chk("unknown None", M.unknown(None) is True)
chk("fmt_num 去 .0", M.fmt_num(50.0) == "50")
chk("fmt_num 小数", M.fmt_num(596.0) == "596")
chk("money", M.money(29800) == "¥29800")
chk("parse_num 带单位", M.parse_num("29800元") == 29800.0)
chk("parse_num 无数字", M.parse_num("未填写") is None)
chk("parse_date 标准", M.parse_date("2027-01-18") == date(2027, 1, 18))
chk("parse_date 中文", M.parse_date("2027年1月18日") == date(2027, 1, 18))
chk("days_between", M.days_between(date(2026, 10, 1), BASE) == 3)

chk("yesno 否", M.yesno("否") is False)
chk("yesno 没有", M.yesno("没有") is False)
chk("yesno 是", M.yesno("是") is True)
chk("yesno 空", M.yesno("未填写") is None)

f1 = {"合同主体": "力巨人健身管理有限公司", "实际收款主体": "鼎盛文化传播有限公司"}
chk("get_text 精确取", M.get_text(f1, "合同主体") == "力巨人健身管理有限公司")
chk("get_text 不串字段", M.get_text(f1, "实际收款主体") == "鼎盛文化传播有限公司")
chk("get_text 总金额不串已付",
    M.get_text({"合同总金额": "29800", "已付金额": "20000"}, "已付金额") == "20000")
chk("get_text 缺字段返空", M.get_text(f1, "健身房名称") == "")
parts = re.split(r"[:：]", "购课总节数：50", 1)
chk("re.split 两元组", len(parts) == 2 and parts[1] == "50")

s1, i1 = M.check_entity({"合同主体": "甲公司", "实际收款主体": "乙公司"})
chk("主体 不一致不通过", s1 == "不通过")
chk("主体 提示两家主张", any("不一致" in x for x in i1))
s2, i2 = M.check_entity({"合同主体": "甲公司", "实际收款主体": "甲公司"})
chk("主体 一致不判不通过", s2 != "不通过")
s3, i3 = M.check_entity({})
chk("主体 空表待补正", s3 == "待补正")
s4, i4 = M.check_entity({"合同主体": "甲公司", "门店现状": "已停业跑路"})
chk("停业 判不通过", s4 == "不通过")

c5, r5, i5 = M.check_terms({"退款条款摘录": "一经售出概不退费，最终解释权归本店所有",
                            "销售承诺摘录": "随时可以退"})
chk("条款 概不退费为高危", any("概不退费" in x for x in c5))
chk("条款 最终解释权为高危", any("最终解释权" in x for x in c5))
chk("承诺 随时退为风险", any("随时" in x for x in r5))
c6, r6, i6 = M.check_terms({})
chk("条款 空表无高危", c6 == [])
chk("条款 空表有风险提示", len(r6) >= 1)

v7, i7 = M.calc_refund({"已付金额": "29800", "合同总金额": "29800",
                        "购课总节数": "50", "已上节数": "8", "已退金额": "0"}, False)
chk("退费 有测算结果", v7 is not None)
chk("退费 剩余42节", any("42" in x for x in i7))
chk("退费 数值合理", v7 is not None and 20000 < v7 < 26000)
v8, i8 = M.calc_refund({}, False)
chk("退费 空表无法测算", v8 is None)
v9, i9 = M.calc_refund({"已付金额": "29800", "购课总节数": "50", "已上节数": "8"}, True)
chk("退费 机构原因提示全额", any("机构原因" in x for x in i9))

c10, r10, i10 = M.check_validity({"有效期至": "2026-01-18"}, BASE)
chk("过期 提示逾期", any("逾期" in x for x in i10))
chk("过期 为风险", any("过期" in x for x in r10))
c11, r11, i11 = M.check_validity({"教练是否已离职": "是", "是否指定教练": "是",
                                  "是否同意更换教练": "否"}, BASE)
chk("教练 离职不同意高危", any("指定教练离职" in x for x in c11))
c12, r12, i12 = M.check_validity({"门店是否转让": "是"}, BASE)
chk("转让 高危", any("转让" in x for x in c12))
c13, r13, i13 = M.check_validity({"转卡手续费": "1500", "是否可转卡转让": "是"}, BASE)
chk("转卡 手续费偏高", any("手续费" in x for x in r13))

h14, m14 = M.check_evidence({"证据留存情况": "有合同原件和付款记录，剩余节数有系统截图"})
chk("证据 已具备合同", any("合同" in x for x in h14))
chk("证据 缺书面申请", any("书面退费申请" in x for x in m14))
h15, m15 = M.check_evidence({})
chk("证据 空表全缺", h15 == [] and len(m15) == 6)

sample = M.parse_md(os.path.join(HERE, "样例.md"))
chk("样例解析非空", len(sample) > 10)
rep, verdict, issues, todo = M.build_report(sample, BASE)
chk("样例结论不通过", verdict == "不通过")
chk("样例高危项多", len(issues) >= 4)
chk("样例有待办", len(todo) >= 4)
chk("报告含结论摘要", "## 结论摘要" in rep)
chk("报告含待办补正动作", "## 待办补正动作" in rep)
chk("报告含边界与纪律", "## 边界与纪律" in rep)
chk("报告章节 >= 9", rep.count("## ") >= 9)
chk("样例提示12315", "12315" in rep)
chk("样例提示商务部门", "商务主管" in rep)
chk("样例提示EMS", "EMS" in rep)

empty = M.parse_md(os.path.join(HERE, "空输入.md"))
chk("空输入解析非空", len(empty) > 10)
rep2, v2, iss2, t2 = M.build_report(empty, BASE)
chk("空输入结论待补正", v2 == "待补正")
chk("空输入无风险项", iss2 == [])
chk("空输入仍出报告", len(rep2) > 500)
chk("空输入含待办", len(t2) >= 1)

env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
sp = os.path.join(SCRIPTS, "gym_pt_refund_check.py")
p1 = subprocess.run([sys.executable, sp, os.path.join(HERE, "样例.md"), "--base", "2026-10-04"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, env=env)
chk("子进程样例 rc=0", p1.returncode == 0)
chk("子进程样例有输出", len(p1.stdout) > 800)
p2 = subprocess.run([sys.executable, sp, os.path.join(HERE, "样例.md"), "--json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, env=env)
try:
    d = json.loads(p2.stdout)
    chk("json 可解析", True)
    chk("json 含结论", "结论" in d)
    chk("json 含风险项", "风险项" in d)
    chk("json 含待办", "待办" in d)
    chk("json 结论一致", d["结论"] == "不通过")
except Exception:
    for n in ("json 可解析", "json 含结论", "json 含风险项", "json 含待办", "json 结论一致"):
        chk(n, False)
p3 = subprocess.run([sys.executable, sp, os.path.join(HERE, "空输入.md")],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, env=env)
chk("空输入 rc=2", p3.returncode == 2)
chk("空输入有输出", len(p3.stdout) > 200)
chk("空输入不崩", "Traceback" not in p3.stderr)

lines = ["回归测试 私教课退费", "PASS=%d FAIL=%d" % (len(PASS), len(FAIL)), ""]
if FAIL:
    lines.append("失败项：")
    lines += ["  - %s" % x for x in FAIL]
else:
    lines.append("失败项：无")
lines += ["", "通过明细："]
lines += ["  %2d. %s" % (i, x) for i, x in enumerate(PASS, 1)]
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for x in FAIL:
    print("FAIL:", x)
sys.exit(1 if FAIL else 0)
