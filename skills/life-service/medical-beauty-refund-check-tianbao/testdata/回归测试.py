# -*- coding: utf-8 -*-
"""医美退费维权 回归测试。用法：python 回归测试.py
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
SCRIPT = os.path.join(SKILL, "scripts", "medical_beauty_refund_check.py")

spec = importlib.util.spec_from_file_location("mbr", SCRIPT)
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

# 1 基础工具
ok("norm", M.norm(" 美颜　坊 ") == "美颜坊")
ok("filled 待填", M.filled("待填") is False)
ok("filled 否为真值", M.filled("否") is True)
ok("unknown 空", M.unknown("") is True)
ok("money", M.money(38000) == "¥38000")
ok("parse_num 带贷", M.parse_num("分期贷两万") is None or M.parse_num("38000") == 38000.0)
ok("parse_date", M.parse_date("2026-09-20") == date(2026, 9, 20))
ok("yesno 否", M.yesno("否") is False)
ok("yesno 是", M.yesno("是") is True)
ok("yesno 待确认 None", M.yesno("待确认") is None)

# 2 解析
ok("样例机构名", M.get_text(F, "机构名称") == "美颜坊医疗美容诊所")
ok("样例已付", M.parse_num(M.get_text(F, "已付金额")) == 38000.0)
ok("样例事故", M.yesno(M.get_text(F, "是否出现并发症或事故")) is True)
ok("空输入机构空", M.unknown(M.get_text(FE, "机构名称")))
ok("空输入已付空", M.parse_num(M.get_text(FE, "已付金额")) is None)
ok("字段不串-收款主体", "王姐" in M.get_text(F, "收款主体"))

# 3 资质
st, its = M.check_license(F)
ok("样例无许可证=不通过", st == "不通过", st)
ok("样例无许可证提示非法行医", any("非法行医" in x for x in its), its)
a1, i1 = M.check_license(mk(是否有医疗机构执业许可证="是"))
ok("有证=通过", a1 == "通过", a1)
ok("有证提示核对科目", any("诊疗科目" in x for x in i1))
a2, _ = M.check_license(mk(是否有医疗机构执业许可证="待确认"))
ok("未填资质=待补正", a2 == "待补正", a2)
dc, dr, di = M.check_doctor(F)
ok("样例医师未注册=高危", any("未注册" in x or "非法行医" in x for x in dc), dc)
ok("样例医师名进说明", any("操作医师" in x for x in di), di)
d2, _, _ = M.check_doctor(mk(操作医师姓名="张医生", 医师是否注册执业="是"))
ok("医师已注册无高危", d2 == [], d2)

# 4 合同
cc, cr, ci = M.check_contract(F)
ok("样例未签合同=风险", any("未签订书面合同" in x for x in cr), cr)
ok("样例合同未写明=风险", any("未写明" in x for x in cr), cr)
c2, r2, _ = M.check_contract(mk(是否签合同="是", 合同是否写明项目次数价格="否"))
ok("签了但无明细=风险", any("未写明" in x for x in r2), r2)

# 5 效果与事故
ec, er, ei = M.check_effect(F)
ok("样例事故=高危", any("并发症" in x or "就医" in x for x in ec), ec)
ok("样例效果未达=风险", any("未达标" in x for x in er), er)
e2, er2, _ = M.check_effect(mk(是否承诺效果="否"))
ok("无承诺无事故无风险", e2 == [] and er2 == [], (e2, er2))

# 6 增项与金融
xr, _ = M.check_extra(F)
ok("样例增项=风险", any("增项" in x or "加价" in x for x in xr), xr)
fr, _ = M.check_finance(F)
ok("样例分期贷=风险", any("分期" in x or "贷款" in x for x in fr), fr)
fr2, _ = M.check_finance(mk(付款方式="微信扫码", 是否办理分期或贷款="否"))
ok("无贷无风险", fr2 == [], fr2)

# 7 退款
net, ri = M.calc_refund(F, "机构全责")
ok("样例全责全额退", net == 38000.0, net)
ok("全责提示全额退", any("全额退款" in x for x in ri), ri)
n2, r2b = M.calc_refund(mk(已付金额="10000", 已退金额="2000"), "部分责任")
ok("部分责任净额", n2 == 8000.0, n2)
n3, r3 = M.calc_refund(mk(), "无")
ok("无金额无法测算", n3 is None and any("无法测算" in x for x in r3), (n3, r3))

# 8 证据
have, miss = M.check_evidence(F)
ok("样例有合同证据?", len(have) >= 1, have)
ok("样例缺病历证据", any("病历" in x or "合同" in x for x in miss), miss)
_, m2 = M.check_evidence(mk(聊天记录留存="待填", 术前术后照片留存="待填"))
ok("无证据缺5项", len(m2) == 5, m2)
_, m3 = M.check_evidence(mk(聊天记录留存="合同付款照片聊天病历", 术前术后照片留存="都有"))
ok("证据齐全无缺失", m3 == [], m3)

# 9 整份报告
rep, verdict, issues, todo = M.build_report(F)
ok("样例结论不通过", verdict == "不通过", verdict)
ok("样例有高危项", len([x for x in issues if ("非法行医" in x or "并发症" in x or "未注册" in x)]) >= 2, issues)
ok("报告九段", rep.count("\n## ") == 8, rep.count("\n## "))
ok("含待办补正动作", "待办补正动作" in rep)
ok("含边界与纪律", "边界与纪律" in rep)
ok("含维权路径表格", "卫健委" in rep or "卫健" in rep)
ok("无四星号", "****" not in rep)
ok("有货币符号", "¥" in rep)
ok("待办非空", len(todo) >= 3, todo)
rep_e, v_e, _, t_e = M.build_report(FE)
ok("空输入待补正", v_e == "待补正", v_e)
ok("空输入不判通过", v_e != "通过", v_e)
ok("空输入补正提示", any("机构名称" in x for x in t_e), t_e)
ok("空输入仍出报告", "边界与纪律" in rep_e)

# 10 子进程
py = sys.executable
p1 = subprocess.run([py, SCRIPT, SAMPLE], capture_output=True)
ok("样例 rc=0", p1.returncode == 0, p1.returncode)
o1 = p1.stdout.decode("utf-8", "replace")
ok("样例 stdout 有报告", "结论摘要" in o1)
ok("样例段落>=9", o1.count("## ") >= 9, o1.count("## "))
p2 = subprocess.run([py, SCRIPT, EMPTY], capture_output=True)
ok("空输入 rc=2", p2.returncode == 2, p2.returncode)
p3 = subprocess.run([py, SCRIPT, SAMPLE, "--json"], capture_output=True)
ok("json rc=0", p3.returncode == 0, p3.returncode)
try:
    j = json.loads(p3.stdout.decode("utf-8", "replace"))
    ok("json 可解析", isinstance(j, dict))
    ok("json 含结论", "结论" in j)
except Exception as e:
    ok("json 可解析", False, str(e))
p4 = subprocess.run([py, SCRIPT, "不存在.md"], capture_output=True)
ok("缺文件 rc=2", p4.returncode == 2, p4.returncode)

LINES.append("")
LINES.append("PASS=%d FAIL=%d" % (PASS, FAIL))
txt = "\n".join(LINES)
with open(os.path.join(HERE, "_reg_result.txt"), "w", encoding="utf-8") as fh:
    fh.write(txt)
print(txt)
