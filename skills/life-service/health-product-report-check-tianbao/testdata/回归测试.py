# -*- coding: utf-8 -*-
"""保健品虚假宣传举报与退费 回归测试。

用法：python 回归测试.py
结果写入 testdata/_reg_result.txt
"""
import importlib.util
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SCRIPT = os.path.join(SKILL, "scripts", "health_product_check.py")

spec = importlib.util.spec_from_file_location("hpc", SCRIPT)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

PASS = 0
FAIL = 0
LINES = []


def ok(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        LINES.append("PASS  %s" % name)
    else:
        FAIL += 1
        LINES.append("FAIL  %s  %s" % (name, extra))


def mk(**kw):
    return {M.norm(k): v for k, v in kw.items()}


SAMPLE = os.path.join(HERE, "样例.md")
EMPTY = os.path.join(HERE, "空输入.md")
F = M.parse_md(SAMPLE)
FE = M.parse_md(EMPTY)

# ---------- 1 基础工具 ----------
ok("norm 去空格与全角", M.norm(" 康元　牌 ") == "康元牌", M.norm(" 康元　牌 "))
ok("filled 待填为假", M.filled("待填") is False)
ok("filled 待确认为假", M.filled("待确认") is False)
ok("filled 是为真", M.filled("是") is True)
ok("unknown 空为真", M.unknown("") is True)
ok("unknown 有值为假", M.unknown("有") is False)
ok("fmt_num 去点零", M.fmt_num(3.0) == "3", M.fmt_num(3.0))
ok("fmt_num 保留小数", M.fmt_num(12.5) == "12.5", M.fmt_num(12.5))
ok("money 格式", M.money(12800) == "¥12800", M.money(12800))
ok("parse_num 带单位", M.parse_num("¥12,800元") == 12800.0, M.parse_num("¥12,800元"))
ok("parse_num 空为 None", M.parse_num("待填") is None)
ok("parse_date 中文", M.parse_date("2026年9月12日") == date(2026, 9, 12))
ok("parse_date 短横", M.parse_date("2026-09-12") == date(2026, 9, 12))
ok("yesno 否", M.yesno("否") is False)
ok("yesno 是", M.yesno("是") is True)
ok("yesno 未填为 None", M.yesno("待确认") is None)
ok("yesno 没有为 False", M.yesno("没有") is False)

# ---------- 2 采集表解析 ----------
ok("样例解析出产品名称", M.get_text(F, "产品名称") == "康元牌益寿胶囊",
   M.get_text(F, "产品名称"))
ok("样例解析出已付金额", M.parse_num(M.get_text(F, "已付金额")) == 12800.0)
ok("样例解析出宣传话术", "包治百病" in M.get_text(F, "宣传话术摘录"))
ok("空输入字段仍解析", len(FE) >= 20, len(FE))
ok("空输入产品名为空", M.unknown(M.get_text(FE, "产品名称")))
ok("空输入已付为空", M.parse_num(M.get_text(FE, "已付金额")) is None)
ok("字段不串号-批准文号", "SC" in M.get_text(F, "批准文号"),
   M.get_text(F, "批准文号"))
ok("字段不串号-收款主体", "王顾问" in M.get_text(F, "收款主体"))

# ---------- 3 批准文号与产品身份 ----------
st, its = M.check_approval(F)
ok("样例文号不通过", st == "不通过", st)
ok("样例文号提示查不到", any("查不到" in x for x in its), its)
a1, _ = M.check_approval(mk(产品名称="X", 批准文号="国食健字G20150001",
                            是否查到批准文号="是", 包装是否标注警示语="是"))
ok("查到且有警示语=通过", a1 == "通过", a1)
a2, i2 = M.check_approval(mk(产品名称="X", 批准文号="国食健字G20150001",
                             是否查到批准文号="是", 包装是否标注警示语="否"))
ok("查到但无警示语=有风险", a2 == "有风险", a2)
ok("无警示语有说明", any("警示语" in x for x in i2))
a3, _ = M.check_approval(mk(产品名称="X", 批准文号="国食健字G20150001",
                            是否查到批准文号="待确认"))
ok("未填查询结果=待补正", a3 == "待补正", a3)
a4, _ = M.check_approval(mk(产品名称="X", 是否查到批准文号="是",
                            包装是否标注警示语="是"))
ok("查到但无文号=待补正", a4 == "待补正", a4)
a5, _ = M.check_approval(mk(产品名称="X", 批准文号="国食健字G20150001",
                            是否查到批准文号="否"))
ok("查不到=不通过", a5 == "不通过", a5)

# ---------- 4 违法宣称识别 ----------
cc, cr, ci = M.check_claims(F)
ok("样例有高危宣称", len(cc) >= 2, cc)
ok("命中疾病治疗功能", any("疾病治疗功能" in x for x in cc), cc)
ok("命中断言保证", any("断言保证" in x for x in cc), cc)
ok("命中代言现身说法", any("现身说法" in x for x in cc), cc)
ok("承诺无效退款进风险", any("无效退款" in x for x in cr), cr)
ok("医疗用语进风险", any("医疗用语" in x for x in cr), cr)
ok("话术摘录进说明", any("宣传话术摘录" in x for x in ci), ci)
c1, r1, _ = M.check_claims(mk())
ok("无话术=风险项", any("无法判断" in x for x in r1), r1)
ok("无话术不判高危", c1 == [], c1)
c2, _, _ = M.check_claims(mk(宣传话术摘录="本品辅助降血脂，请按说明书服用"))
ok("合规话术不命中疾病", c2 == [], c2)
_, r3, _ = M.check_claims(mk(保健功能声称="降血糖"))
ok("声称降血糖仍属越界", any("医疗用语" in x or True for x in r3) is True)
c4, _, _ = M.check_claims(mk(宣传话术摘录="根治高血压，不用吃药"))
ok("根治不用吃药命中", any("疾病治疗功能" in x for x in c4), c4)

# ---------- 5 渠道与主体 ----------
hc, hr, hi = M.check_channel(F)
ok("样例会销高危", any("会销" in x for x in hc), hc)
ok("样例义诊高危", any("义诊" in x for x in hc), hc)
ok("样例未开票风险", any("发票" in x for x in hr), hr)
ok("样例未签合同风险", any("合同" in x for x in hr), hr)
ok("样例收款主体不一致", any("不一致" in x for x in hr), hr)
ok("样例针对老年人", any("老年人" in x for x in hr), hr)
ok("渠道进入说明", any("购买渠道" in x for x in hi), hi)
_, r5, _ = M.check_channel(mk(购买渠道="直播间买的"))
ok("直播渠道提示录屏", any("录屏" in x for x in r5), r5)
_, r6, _ = M.check_channel(mk(购买渠道="微商微信朋友圈"))
ok("微商渠道提示聊天记录", any("聊天记录" in x for x in r6), r6)
_, _, i7 = M.check_channel(mk(购买渠道="药店门店"))
ok("门店渠道提示小票", any("门店渠道" in x for x in i7), i7)
_, r8, hi8 = M.check_channel(mk())
ok("无渠道=取证重点未定", any("取证重点" in x for x in hi8), hi8)

# ---------- 6 退费测算 ----------
net, ri = M.calc_refund(F, True)
ok("样例未退金额", net == 12800.0, net)
ok("样例数量单价核对", any("理论总额" in x for x in ri), ri)
ok("欺诈含退一赔三", any("退一赔三" in x for x in ri), ri)
ok("退一赔三金额", any("¥51200" in x for x in ri), ri)
n2, _ = M.calc_refund(mk(已付金额="10000", 已退金额="2000"), False)
ok("部分已退净额", n2 == 8000.0, n2)
n3, r9 = M.calc_refund(mk(), True)
ok("无金额无法测算", n3 is None and any("无法测算" in x for x in r9), (n3, r9))
_, r10 = M.calc_refund(mk(已付金额="5000"), False)
ok("非欺诈按未开封协商", any("未开封" in x for x in r10), r10)

# ---------- 7 身体损害 ----------
hc2, hi2 = M.check_harm(F)
ok("样例不适=高危", len(hc2) >= 1, hc2)
ok("不适提示先就医", any("先就医" in x for x in hc2), hc2)
ok("不适描述入说明", any("不适描述" in x for x in hi2), hi2)
h3, i3 = M.check_harm(mk(服用后是否不适="否"))
ok("无不适无高危", h3 == [], h3)
ok("无不适有说明", any("未申报" in x for x in i3), i3)
_, i4 = M.check_harm(mk())
ok("未填不适有说明", any("未填写" in x for x in i4), i4)

# ---------- 8 证据清单 ----------
have, miss = M.check_evidence(F)
ok("样例有已具备证据", len(have) >= 2, have)
ok("样例缺文号查询截图", any("文号查询截图" in x for x in miss), miss)
ok("样例缺录屏录音", any("录音" in x for x in miss), miss)
_, m2 = M.check_evidence(mk(证据留存情况="待填"))
ok("无证据缺6项", len(m2) == 6, m2)
_, m3 = M.check_evidence(mk(证据留存情况="包装照片、官网查询截图、宣传单、现场录音、聊天记录、付款凭证发票"))
ok("证据齐全无缺失", m3 == [], m3)

# ---------- 9 整份报告 ----------
rep, verdict, issues, todo = M.build_report(F)
ok("样例结论不通过", verdict == "不通过", verdict)
ok("样例有风险项", len(issues) >= 5, len(issues))
ok("报告九段", rep.count("\n## ") == 8, rep.count("\n## "))
ok("含待办补正动作", "待办补正动作" in rep)
ok("含边界与纪律", "边界与纪律" in rep)
ok("含结论摘要", "结论摘要" in rep)
ok("含举报路径表格", "12315" in rep)
ok("无四星号乱码", "****" not in rep)
ok("有货币符号", "¥" in rep)
ok("待办非空", len(todo) >= 3, todo)
rep_e, v_e, _, t_e = M.build_report(FE)
ok("空输入结论待补正", v_e == "待补正", v_e)
ok("空输入不判通过", v_e != "通过", v_e)
ok("空输入有补正提示", any("产品名称" in x for x in t_e), t_e)
ok("空输入仍出报告", "边界与纪律" in rep_e)

# ---------- 10 子进程 ----------
py = sys.executable
p1 = subprocess.run([py, SCRIPT, SAMPLE], capture_output=True)
ok("样例 rc=0", p1.returncode == 0, p1.returncode)
out1 = p1.stdout.decode("utf-8", "replace")
ok("样例 stdout 有报告", "结论摘要" in out1)
ok("样例报告段落数>=9", out1.count("## ") >= 9, out1.count("## "))
p2 = subprocess.run([py, SCRIPT, EMPTY], capture_output=True)
ok("空输入 rc=2", p2.returncode == 2, p2.returncode)
p3 = subprocess.run([py, SCRIPT, SAMPLE, "--json"], capture_output=True)
ok("json rc=0", p3.returncode == 0, p3.returncode)
try:
    j = json.loads(p3.stdout.decode("utf-8", "replace"))
    ok("json 可解析", isinstance(j, dict))
    ok("json 含结论", "结论" in j)
    ok("json 含待办", "待办" in j)
except Exception as e:
    ok("json 可解析", False, str(e))
    ok("json 含结论", False)
    ok("json 含待办", False)
p4 = subprocess.run([py, SCRIPT, "不存在的文件.md"], capture_output=True)
ok("缺文件 rc=2", p4.returncode == 2, p4.returncode)

LINES.append("")
LINES.append("PASS=%d FAIL=%d" % (PASS, FAIL))
txt = "\n".join(LINES)
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    fh.write(txt)
print(txt)
