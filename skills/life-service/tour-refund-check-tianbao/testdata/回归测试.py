# -*- coding: utf-8 -*-
"""旅游消费退款维权核查 · 回归测试（>=40 断言）。"""
import os
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "tour_refund_check.py")
SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")

sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import tour_refund_check as M

_py = "C:\\Users\\Ti'an'bao\\.workbuddy\\binaries\\python\\versions\\3.13.12\\python.exe"

passed = 0
failed = []

def ok(name, cond, extra=None):
    global passed
    if cond:
        passed += 1
    else:
        failed.append("%s | %s" % (name, extra))

def mk(**kw):
    return {k: v for k, v in kw.items()}

# ---- 基础工具 ----
ok("filled 正常", M.filled("跟团游") is True)
ok("filled 空", M.filled("") is False)
ok("filled 待填", M.filled("待确认") is False)
ok("filled 否为真值", M.filled("否") is True)
ok("unknown 空", M.unknown("") is True)
ok("unknown 有值", M.unknown("6800") is False)
ok("money 整数", M.money("6800") == "¥6800")
ok("money 小数", M.money("12.50") == "¥12.5")
ok("yesno 否=False", M.yesno("否") is False)
ok("yesno 没有=False", M.yesno("没有") is False)
ok("yesno 是=True", M.yesno("是") is True)
ok("yesno 空=None", M.yesno("") is None)
ok("yesno 已=True", M.yesno("已出行") is True)

# ---- 解析 ----
md = "# 标题\n| 旅游类型 | 跟团游 |\n| 已付金额 | 6800 |\n问题描述：强制购物\n"
tp = os.path.join(HERE, "_t_parse.md")
with open(tp, "w", encoding="utf-8") as fh:
    fh.write(md)
pdata = M.parse_md(tp)
ok("解析表格", M.get_text(pdata, "旅游类型") == "跟团游", pdata)
ok("解析冒号", M.get_text(pdata, "问题描述") == "强制购物", pdata)
ok("get_text 不子串泄漏", M.get_text({"有无合同": "否"}, "合同主体") == "", "应空")

# ---- check_qual ----
cq0 = M.check_qual(mk(有无资质="否"))
ok("无资质=不通过", cq0[0] == "不通过", cq0)
ok("无资质风险项", any("违规经营" in x for x in cq0[2]), cq0[2])
cq1 = M.check_qual(mk(有无资质="是", 有无合同="否", 合同主体="A社", 收款主体="A社"))
ok("无合同=有风险", cq1[0] == "有风险", cq1)
ok("无合同提示", any("未签订书面" in x for x in cq1[1]), cq1[1])
cq2 = M.check_qual(mk(有无资质="是", 有无合同="是", 合同主体="A社", 收款主体="B公司"))
ok("主体不一致=风险", any("合同主体与收款主体不一致" in x for x in cq2[2]), cq2[2])
cq3 = M.check_qual(mk(有无资质="是", 有无合同="是", 合同主体="A社", 收款主体="A社"))
ok("资质合同齐全=通过", cq3[0] == "通过", cq3)
cq4 = M.check_qual(mk())
ok("资质缺失=待确认提示", any("无法确认" in x for x in cq4[1]), cq4[1])

# ---- check_itinerary ----
ci0 = M.check_itinerary(mk(行程是否缩水="是", 强制购物="否"))
ok("行程缩水=风险", any("行程缩水" in x for x in ci0[2]), ci0[2])
ok("行程缩水状态", ci0[0] == "有风险", ci0)
ci1 = M.check_itinerary(mk(行程是否缩水="否", 强制购物="是"))
ok("强制购物=不通过", ci1[0] == "不通过", ci1)
ok("强制购物高危", any("强制购物" in x for x in ci1[3]), ci1[3])
ok("强制购物法条", any("旅游法" in x for x in ci1[3]), ci1[3])
ci2 = M.check_itinerary(mk(问题描述="旅行社跑路联系不上卷款"))
ok("跑路=不通过", ci2[0] == "不通过", ci2)
ok("跑路高危", any("跑路" in x for x in ci2[3]), ci2[3])
ci3 = M.check_itinerary(mk(行程是否缩水="否", 强制购物="否", 问题描述="正常"))
ok("行程正常=通过", ci3[0] == "通过", ci3)
ci4 = M.check_itinerary(mk(行程是否缩水="否", 强制购物="否", 问题描述="擅自变更酒店降级"))
ok("擅自变更=风险", any("擅自变更" in x for x in ci4[2]), ci4[2])

# ---- check_refund ----
cf0 = M.check_refund(mk(已付金额="", 是否出行="否"))
ok("未填金额=无法测算", any("无法测算" in x for x in cf0[1]), cf0[1])
cf1 = M.check_refund(mk(已付金额="6800", 是否出行="否"))
ok("未出行=全额退", any("全额退" in x for x in cf1[1]), cf1[1])
cf2 = M.check_refund(mk(已付金额="6800", 是否出行="是", 已发生费用="1200"))
ok("已出行算差额", any("参考可退" in x for x in cf2[1]), cf2[1])
cf3 = M.check_refund(mk(已付金额="6800", 是否出行="是", 付款方式="微信转个人"))
ok("个人收款=风险", any("个人账户" in x for x in cf3[2]), cf3[2])
cf4 = M.check_refund(mk(已付金额="6800", 是否出行="是", 付款方式="对公转账"))
ok("对公无风险", cf4[2] == [], cf4[2])
cf5 = M.check_refund(mk(已付金额="6800", 是否出行="", 付款方式="对公转账"))
ok("未填出行=无法确认", any("无法确认" in x for x in cf5[1]), cf5[1])

# ---- check_evidence ----
ev = M.check_evidence(mk(证据留存="有合同、付款记录、聊天记录、购物小票"))
ok("证据命中合同", "旅游合同/订单" in ev[0], ev)
ok("证据命中付款", "付款凭证" in ev[0], ev)
ok("证据缺行程单", "行程单/确认单" in ev[1], ev)
ev2 = M.check_evidence(mk(证据留存="无"))
ok("无证据全缺", len(ev2[1]) == 5, ev2[1])

# ---- build_report ----
pf = mk(旅游类型="跟团游", 问题描述="强制购物", 已付金额="6800", 旅行社名称="某社",
        有无资质="是", 有无合同="是", 合同主体="某社", 收款主体="某社",
        行程是否缩水="否", 强制购物="是", 是否出行="是", 已发生费用="1200",
        付款方式="对公转账", 证据留存="合同付款聊天")
cq = M.check_qual(pf)
ci = M.check_itinerary(pf)
cf = M.check_refund(pf)
have, miss = M.check_evidence(pf)
rep, concl = M.build_report(pf, cq, ci, ci, cf, have, miss)
ok("报告9段", rep.count("## ") == 9, rep.count("## "))
ok("报告含待办", "待办补正动作" in rep)
ok("报告含边界", "边界与纪律" in rep)
ok("强制购物报告含高危", "强制购物" in rep)
ok("结论不通过", "不通过" in concl, concl)

# 核心缺失 → 待补正
core_rep, core_concl = M.build_report(mk(旅游类型="", 问题描述="", 已付金额=""),
                                      M.check_qual(mk()), M.check_itinerary(mk()),
                                      M.check_itinerary(mk()), M.check_refund(mk()), [], [])
ok("核心缺失=待补正", "待补正" in core_concl, core_concl)
ok("核心缺失报告9段", core_rep.count("## ") == 9, core_rep.count("## "))

# 全部正常 → 通过
ok_rep, ok_concl = M.build_report(pf, cq, ci, ci, cf, have, miss)
# pf 强制购物=True → 不通过，构造无强制购物的通过场景
pf2 = dict(pf); pf2["强制购物"] = "否"
cq2b = M.check_qual(pf2); ci2b = M.check_itinerary(pf2); cf2b = M.check_refund(pf2)
rep2, concl2 = M.build_report(pf2, cq2b, ci2b, ci2b, cf2b, have, miss)
ok("无风险场景=通过", "通过" in concl2, concl2)

# ---- 子进程 rc / json ----
r1 = subprocess.run([_py, SCRIPT, SAMPLE], capture_output=True, encoding="utf-8")
ok("样例rc=0", r1.returncode == 0, r1.returncode)
ok("样例含结论摘要", "结论摘要" in r1.stdout, r1.stdout[:50])
rj = subprocess.run([_py, SCRIPT, SAMPLE, "--json"], capture_output=True, encoding="utf-8")
ok("json rc=0", rj.returncode == 0, rj.returncode)
try:
    j = json.loads(rj.stdout)
    ok("json可解析", "结论" in j and "报告" in j, list(j.keys()))
except Exception as e:
    ok("json可解析", False, str(e))
re_ = subprocess.run([_py, SCRIPT, EMPTY], capture_output=True, encoding="utf-8")
ok("空输入rc=2", re_.returncode == 2, re_.returncode)
ok("空输入锁待补正", "待补正" in re_.stdout, re_.stdout[:50])

# ---- 输出 ----
os.remove(tp)
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    fh.write("PASS=%d  FAIL=%d\n" % (passed, len(failed)))
    for f in failed:
        fh.write("FAIL: %s\n" % f)
    # 乱码扫描
    bad = [c for c in (r1.stdout + re_.stdout) if ord(c) in (0xfffd,)]
    fh.write("乱码=%d\n" % len(bad))

print("PASS=%d  FAIL=%d" % (passed, len(failed)))
if failed:
    print("FAILURES:")
    for f in failed:
        print("  " + f)
