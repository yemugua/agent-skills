# -*- coding: utf-8 -*-
"""家政服务纠纷核查 · 回归测试（>=40 断言）。"""
import os
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "home_service_dispute_check.py")
SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")
PY = r"C:\Users\Ti'an'bao\.workbuddy\binaries\python\versions\3.13.12\python.exe"

sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "scripts")))
import home_service_dispute_check as M

_results = []
def ok(name, cond, extra=""):
    _results.append((name, bool(cond), extra))

def mk(**kw):
    d = {}
    for k, v in kw.items():
        d[k] = v
    return d

# ---- 基础工具 ----
ok("filled 正常", M.filled("月嫂") is True)
ok("filled 空", M.filled("") is False)
ok("filled 待填", M.filled("待填") is False)
ok("filled 待确认", M.filled("待确认") is False)
ok("unknown 空", M.unknown("") is True)
ok("unknown 有值", M.unknown("有") is False)
ok("yesno 是", M.yesno("是") is True)
ok("yesno 否", M.yesno("否") is False)
ok("yesno 未填", M.yesno("待填") is None)
ok("yesno 没有", M.yesno("没有合同") is False)
ok("money 整数", M.money("6800") == "¥6800")
ok("money 小数", M.money("19800.5") == "¥19800.5")
ok("norm 去空格", M.norm(" 月嫂 ") == "月嫂")

# ---- get_text 精确匹配 ----
f1 = {"已付金额": "19800", "金额": "999"}
ok("get_text 精确", M.get_text(f1, "已付金额") == "19800")
ok("get_text 不串字段", M.get_text(f1, "金额") == "999")
ok("get_text 前缀去号", M.get_text({"1. 已付金额": "5000"}, "已付金额") == "5000")
ok("get_text 缺失", M.get_text(f1, "问题描述") == "")

# ---- parse_md ----
pf = M.parse_md(SAMPLE)
ok("parse 表格", M.get_text(pf, "家政服务类型") == "月嫂")
ok("parse 已付", M.get_text(pf, "已付金额") == "19800")
ok("parse 收款主体", M.get_text(pf, "收款主体") == '个人微信"王姐"')

# ---- check_contract ----
cc = M.check_contract(mk(有无合同="否", 合同主体="", 收款主体="", 服务提供者="某中介"))
ok("无合同=有风险", cc[0] == "有风险", cc)
ok("无合同提示", any("未签订书面合同" in x for x in cc[1]), cc[1])
st2, it2, rk2 = M.check_contract(mk(有无合同="是", 合同主体="甲公司", 收款主体="乙公司"))
ok("主体不一致=不通过", st2 == "不通过", (st2, rk2))
ok("主体不一致风险项", any("合同主体与收款主体不一致" in x for x in rk2), rk2)
st3, it3, rk3 = M.check_contract(mk(有无合同="是", 合同主体="同公司", 收款主体="同公司"))
ok("主体一致=通过", st3 == "通过", (st3, rk3))
cc4 = M.check_contract(mk(有无合同="待填", 合同主体="", 收款主体=""))
ok("合同未填=待确认提示", any("未填写是否有合同" in x for x in cc4[1]), cc4[1])

# ---- check_pay ----
cp = M.check_pay(mk(已付金额="", 是否预付费="是"))
ok("无金额=无法测算", any("退费基数无法测算" in x for x in cp[1]), cp[1])
cp2 = M.check_pay(mk(已付金额="19800", 是否预付费="是", 剩余服务期=""))
ok("预付无剩余=无法测算", any("可退区间无法测算" in x for x in cp2[1]), cp2[1])
cp3 = M.check_pay(mk(已付金额="19800", 是否预付费="否"))
ok("非预付=按次结算", any("按次/按日结算" in x for x in cp3[1]), cp3[1])
cp4 = M.check_pay(mk(已付金额="19800", 是否预付费="是", 付款方式="微信转个人", 剩余服务期="2个月"))
ok("个人收款=风险", any("付款至个人账户" in x for x in cp4[2]), cp4[2])
ok("预付款=有风险", cp4[0] == "不通过", cp4)
cp5 = M.check_pay(mk(已付金额="19800", 是否预付费="是", 付款方式="对公转账", 剩余服务期="2个月"))
ok("预付对公=有风险", cp5[0] == "有风险", cp5)

# ---- check_damage ----
cd = M.check_damage(mk(损害情况="月嫂把孩子摔了，去了医院"))
ok("人身伤害=高危", any("人身伤害" in x for x in cd[3]), cd[3])
ok("人身伤害状态", cd[0] == "不通过", cd)
cd2 = M.check_damage(mk(损害情况="家里的玉镯被摔碎了"))
ok("财物损坏=风险", any("财物损坏" in x for x in cd2[2]), cd2[2])
cd3 = M.check_damage(mk(损害情况="无"))
ok("无损害=通过", cd3[0] == "通过", cd3)
cd4 = M.check_damage(mk(损害情况="待填"))
ok("损害未填=待补正", cd4[0] == "待补正", cd4)

# ---- check_evidence ----
have, miss = M.check_evidence(mk(证据留存="有转账记录、有聊天记录"))
ok("证据含付款", "付款凭证" in have, have)
ok("证据含沟通", "沟通记录" in have, have)
ok("证据缺合同", "合同/协议" in miss, miss)
ok("证据缺损害", "损害证明" in miss, miss)

# ---- build_report 综合 ----
rep, concl = M.build_report(pf, cc, [], cp4, cd3, have, miss)
ok("报告含结论", "结论摘要" in rep)
ok("报告含待办", "待办补正动作" in rep)
ok("报告含边界", "边界与纪律" in rep)
ok("样例结论不通过或无风险", concl in ("**不通过**", "**有风险**", "**通过**"), concl)
ok("报告9段", rep.count("## ") >= 9, rep.count("## "))

# ---- 主流程：核心缺失锁待补正 ----
ec, ei, er = M.check_contract(mk(有无合同="否"))
core_rep, core_concl = M.build_report(mk(家政服务类型="", 问题描述="", 已付金额=""),
                                       ec, [],
                                       M.check_pay(mk()), M.check_damage(mk()), [], [])
ok("核心缺失=待补正", core_concl == "**待补正**", core_concl)
ok("核心缺失说明", "核心信息缺失" in core_rep, core_rep)

# ---- 子进程：样例 rc=0 ----
r_sample = subprocess.run([PY, SCRIPT, SAMPLE], capture_output=True, text=True, encoding="utf-8")
ok("样例 rc=0", r_sample.returncode == 0, r_sample.returncode)
ok("样例含结论", "结论摘要" in r_sample.stdout)

# ---- 子进程：样例 --json 可解析 ----
r_json = subprocess.run([PY, SCRIPT, SAMPLE, "--json"], capture_output=True, text=True, encoding="utf-8")
ok("json rc=0", r_json.returncode == 0, r_json.returncode)
try:
    j = json.loads(r_json.stdout)
    ok("json 可解析", True)
    ok("json 有结论", "结论" in j, list(j.keys()))
except Exception as e:
    ok("json 可解析", False, str(e))

# ---- 子进程：空输入 rc=2 ----
r_empty = subprocess.run([PY, SCRIPT, EMPTY], capture_output=True, text=True, encoding="utf-8")
ok("空输入 rc=2", r_empty.returncode == 2, r_empty.returncode)

# ---- 子进程：不存在文件 rc=2 ----
r_no = subprocess.run([PY, SCRIPT, "不存在.md"], capture_output=True, text=True, encoding="utf-8")
ok("文件缺失 rc=2", r_no.returncode == 2, r_no.returncode)

# ---- 汇总 ----
PASS = sum(1 for _, c, _ in _results if c)
FAIL = len(_results) - PASS
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    for name, c, extra in _results:
        fh.write(("PASS " if c else "FAIL ") + name + ("" if c else "  >> " + str(extra) + "\n"))
    fh.write("\nPASS=%d FAIL=%d\n" % (PASS, FAIL))
print("PASS=%d FAIL=%d" % (PASS, FAIL))
for name, c, extra in _results:
    if not c:
        print("  FAIL:", name, ">>", extra)
