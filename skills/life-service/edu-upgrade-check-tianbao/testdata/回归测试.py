# -*- coding: utf-8 -*-
"""学历提升报考与退费核查脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import edu_upgrade_check as T  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)
PY = sys.executable


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        route="", org="", school="", age="", school_level="", major="",
        sign_up_date="", promises="", qualification="", loan="", paid="",
        paid_amount="", contract="", refund_rule="", timing_promise="",
        evidence_owned="", evidence_desc="",
    )
    base.update(kw)
    return base


def chk(name, rows, item, state=None):
    for r in rows:
        if r[0] == item:
            if state is None:
                ck(name + "被触发", True)
            else:
                ck(name + "=" + state, r[1] == state)
            return
    ck(name + "(未出现)", state is None)


# ---------------------------------------------------------- 基础工具
ck("norm去空格", T.norm(" 宏达 ") == "宏达")
ck("norm统一冒号", T.norm("费用：9800") == "费用:9800")
ck("filled空串=False", T.filled("") is False)
ck("filled斜杠提示=False", T.filled("是/否") is False)
ck("filled待填=False", T.filled("待填") is False)
ck("filled数字0不为空", T.filled(0) is True)
ck("filled数字不崩", T.filled(9800) is True)
ck("yes是", T.yes("是") is True)
ck("no否", T.no("否") is True)
ck("unknown不清楚", T.unknown("不清楚") is True)
ck("unknown有值=False", T.unknown("签了协议") is False)
ck("parse_num元", T.parse_num("9800元") == 9800.0)
ck("parse_num空=None", T.parse_num("") is None)
ck("fmt_num去.0", T.fmt_num(9800.0) == "9800")
ck("money前缀", T.money(9800.0) == "¥9800")
ck("parse_date", T.parse_date("2026-08-20") == date(2026, 8, 20))
ck("hit_any命中", T.hit_any("成人高考专升本", ["成考", "成人高考"]) is True)
ck("hit_any未命中=False", T.hit_any("搬家", ["成考", "自考"]) is False)
ck("hit_any空=None", T.hit_any("", ["成考"]) is None)

# ---------------------------------------------------------- 途径识别
ck("识别成考", "成人高考专升本" in T.classify(mk(route="成人高考专升本")))
ck("识别自考", "自学考试" in T.classify(mk(route="自考本科")))
ck("识别网教", "网络教育/远程教育" in T.classify(mk(route="远程教育")))
ck("识别国开", "国家开放大学" in T.classify(mk(route="国开大学")))
ck("空途径无类型", T.classify(mk()) == [])

# ---------------------------------------------------------- 一 途径与条件
r = T.checks_route(mk())
chk("缺途径待补正", r, "提升途径类型", "待补正")
r = T.checks_route(mk(route="随便说说"))
chk("未识别途径待补正", r, "提升途径类型", "待补正")
r = T.checks_route(mk(route="成人高考专升本"))
chk("识别途径有风险", r, "提升途径类型", "有风险")

r = T.checks_qualify(mk(), TODAY)
chk("缺条件待补正", r, "本人报考条件", "待补正")
chk("缺报名时间待补正", r, "报名时间点", "待补正")
r = T.checks_qualify(mk(school_level="专科，2013年毕业",
                         sign_up_date="2026-08-20"), TODAY)
chk("有学历通过", r, "本人报考条件", "通过")
chk("有报名时间通过", r, "报名时间点", "通过")

# ---------------------------------------------------------- 二 套路核查
r = T.checks_fraud(mk())
chk("缺承诺待补正", r, "机构做过哪些承诺", "待补正")
# 填「保过」类词 = 明确不通过
r = T.checks_fraud(mk(promises="说保过，不过退款，考试不用自己管"))
chk("保过不通过", r, "机构做过哪些承诺", "不通过")
r = T.checks_fraud(mk(promises="说可以安排人替考，还能代做作业"))
chk("替考不通过", r, "机构做过哪些承诺", "不通过")
# 「国家承认」被机构拿来当卖点，属夸大承诺那一组
r = T.checks_fraud(mk(promises="说国家承认，学信网可查，还包就业"))
chk("夸大承诺不通过", r, "机构做过哪些承诺", "不通过")
r = T.checks_fraud(mk(promises="说会安排课程和复习资料"))
chk("未识别套路有风险", r, "机构做过哪些承诺", "有风险")

# ---------------------------------------------------------- 三 资质与缴费
r = T.checks_qualification(mk())
chk("缺资质待补正", r, "办学资质是否核实", "待补正")
chk("缺机构待补正", r, "收款主体是否合规", "待补正")
r = T.checks_qualification(mk(qualification="查了教育部名单，学校是公办，学信网可查",
                              org="宏达教育咨询有限公司"))
chk("资质核实通过", r, "办学资质是否核实", "通过")
chk("机构对公有风险", r, "收款主体是否合规", "有风险")
# 收款打到个人账户 = 不通过
r = T.checks_qualification(mk(org="转给姓周的老板个人微信，不是公司账户"))
chk("个人收款不通过", r, "收款主体是否合规", "不通过")

r = T.checks_loan(mk())
chk("缺贷款待补正", r, "是否涉及贷款或分期", "待补正")
chk("缺缴费待补正", r, "已缴纳费用", "待补正")
# 填「是」= 被要求贷款分期 = 不通过
r = T.checks_loan(mk(loan="是", paid="是", paid_amount="9800"))
chk("贷款分期不通过", r, "是否涉及贷款或分期", "不通过")
chk("已缴费有风险", r, "已缴纳费用", "有风险")
r = T.checks_loan(mk(loan="否", paid="否"))
chk("无贷款通过", r, "是否涉及贷款或分期", "通过")
chk("未缴费通过", r, "已缴纳费用", "通过")

# ---------------------------------------------------------- 四 合同与退费
r = T.checks_contract(mk())
chk("缺合同待补正", r, "是否签了书面合同", "待补正")
chk("缺退费规则待补正", r, "退费规则是否写清", "待补正")
r = T.checks_contract(mk(contract="签了协议，条款里有退费规则和发票",
                         refund_rule="按未开课课时费退"))
chk("合同有风险", r, "是否签了书面合同", "有风险")
chk("退费有风险", r, "退费规则是否写清", "有风险")
# 字段缺失时不应 KeyError
r = T.checks_contract({"contract": "签了协议"})
chk("缺refund_rule不崩", r, "退费规则是否写清", "待补正")
# 「一经报名不退不费」是典型坑 = 不通过
r = T.checks_contract(mk(contract="签了协议", refund_rule="一经报名不退不费"))
chk("不可退不通过", r, "退费规则是否写清", "不通过")
r = T.checks_contract(mk(contract="没签合同"))
chk("无合同有风险", r, "是否签了书面合同", "有风险")

# ---------------------------------------------------------- 五 时限
r = T.checks_timing(mk())
chk("缺时间承诺待补正", r, "拿证时间承诺", "待补正")
# 一年拿证 vs 成考学制 2.5~3 年 = 时限风险
r = T.checks_timing(mk(timing_promise="一年拿证，明年这个时候就能拿"))
chk("一年拿证有风险", r, "拿证时间承诺", "有风险")
ck("提示学制", "学制" in r[0][2])
r = T.checks_timing(mk(timing_promise="按正常学制毕业"))
chk("正常学制通过", r, "拿证时间承诺", "通过")

# ---------------------------------------------------------- 六 证据
r = T.checks_evidence(mk(evidence_owned="合同,收据,转账,宣传,微信",
                         evidence_desc="全部"))
chk("合同通过", r, "合同与协议", "通过")
chk("缴费凭证通过", r, "缴费凭证", "通过")
chk("宣传材料通过", r, "机构宣传材料", "通过")
r = T.checks_evidence(mk())
chk("空证据待补正", r, "证据总览", "待补正")
g = T.evidence_gap(mk())
ck("空证据缺7类", len(g) == 7)
# 有保过承诺就必须有宣传材料
g2 = T.evidence_gap(mk(promises="说保过，不过退款",
                        evidence_owned="合同,收据,发票,转账,缴费,课程,网课,考试,成绩,签到,微信,聊天,短信,录音,工单,客服,学信网,查询记录,名单,公示,官网,教育部"))
ck("保过必补宣传材料", "机构宣传材料" in g2)
# 没查过资质就必须补资质材料
g3 = T.evidence_gap(mk(qualification="没查过",
                        evidence_owned="合同,协议,收据,发票,转账,缴费,宣传,海报,视频,截图,微信,聊天,课程,网课,考试,成绩,签到,工单,客服,录音"))
ck("未核实必补资质", "机构与院校资质" in g3)

# ---------------------------------------------------------- 路径与待办
ck("路径7步", len(T.path_steps(mk())) == 7)
todos = T.todo_list(mk(promises="保过", loan="是", refund_rule="不退",
                        qualification="没查", contract=""), [])
ck("保过列入待办", any("停止缴费" in n for n, _s in todos))
ck("贷款列入待办", any("贷款" in n for n, _s in todos))
ck("资质列入待办", any("资质" in n for n, _s in todos))
# 合同字段留空才触发补签待办（填了「没签」这种文字 filled() 判为已填）
ck("补签协议列入待办", any("协议" in n for n, _s in todos))

# ---------------------------------------------------------- 报告渲染
kv = T.build_kv(T.read_text(os.path.join(HERE, "样例.md")))
f = T.build_fields(kv)
ck("解析途径", "成人高考" in f["route"])
ck("解析机构", "宏达" in f["org"])
ck("解析金额", T.parse_num(f["paid_amount"]) == 9800.0)
ck("解析贷款是", f["loan"].startswith("是"))
ck("解析退费", "不退" in f["refund_rule"])

results = [
    ("提升途径与报考条件", T.checks_route(f) + T.checks_qualify(f, TODAY)),
    ("中介承诺与套路核查", T.checks_fraud(f)),
    ("办学资质与缴费核查", T.checks_qualification(f) + T.checks_loan(f)),
    ("合同条款与退费规则", T.checks_contract(f)),
    ("时间承诺与时效风险", T.checks_timing(f)),
    ("证据清单与缺口", T.checks_evidence(f)),
]
todos = T.todo_list(f, results)
gaps = T.evidence_gap(f)
rep = T.render(f, results, T.path_steps(f), todos, TODAY, gaps)
ck("报告有标题", rep.startswith("# 学历提升报考与退费核查报告"))
ck("报告无乱码", "\ufffd" not in rep)
ck("报告有8个以上段", rep.count("\n## ") >= 8)
ck("报告含四态字样", all(w in rep for w in ("通过", "有风险", "不通过", "待补正")))
ck("报告未填不算通过", "未填的一律不算通过" in rep)
ck("报告段标题齐全", all(t in rep for t in T.SECTIONS))
ck("报告有查询渠道段", "## 九、查询渠道速查" in rep)
ck("报告提学信网", "学信网" in rep)
ck("报告提12315", "12315" in rep)

kve = T.build_kv(T.read_text(os.path.join(HERE, "空输入.md")))
fe = T.build_fields(kve)
ck("空表全空", all((v or "").strip() == "" for v in fe.values()))
empty_results = [
    ("提升途径与报考条件", T.checks_route(fe) + T.checks_qualify(fe, TODAY)),
    ("中介承诺与套路核查", T.checks_fraud(fe)),
    ("办学资质与缴费核查", T.checks_qualification(fe) + T.checks_loan(fe)),
    ("合同条款与退费规则", T.checks_contract(fe)),
    ("时间承诺与时效风险", T.checks_timing(fe)),
    ("证据清单与缺口", T.checks_evidence(fe)),
]
rep0 = T.render(fe, empty_results, T.path_steps(fe),
                T.todo_list(fe, empty_results), TODAY, T.evidence_gap(fe))
ck("空表报告仍有段", rep0.count("\n## ") >= 8)
ck("空表无乱码", "\ufffd" not in rep0)

js = T.to_json(f, results, todos, TODAY, gaps)
ck("json核查日期", js["核查日期"] == "2026-10-05")
ck("json识别成考", "成人高考专升本" in js["提升途径"])
ck("json已缴费用", js["已缴费用"] == 9800.0)
ck("json有不通过项", len(js["结论"]["不通过"]) >= 1)
ck("json待办非空", len(js["待办"]) >= 1)
ck("json可序列化", isinstance(json.dumps(js, ensure_ascii=False), str))

# ---------------------------------------------------------- 端到端
SCRIPT = os.path.join(SCRIPTS, "edu_upgrade_check.py")


def run(args):
    return subprocess.run([PY, SCRIPT] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


p = run([os.path.join(HERE, "样例.md")])
ck("样例rc=0", p.returncode == 0)
ck("样例stdout有报告", "学历提升报考与退费核查报告" in p.stdout)
ck("样例stdout无乱码", "\ufffd" not in p.stdout)
ck("样例有结论摘要", "## 一、结论摘要" in p.stdout)

p = run([os.path.join(HERE, "空输入.md")])
ck("空输入rc=2", p.returncode == 2)
ck("空输入有段", p.stdout.count("\n## ") >= 8)
ck("空输入有缺失提示", "关键信息缺失" in p.stdout)

p = run([os.path.join(HERE, "样例.md"), "--json"])
ck("json rc=0", p.returncode == 0)
try:
    data = json.loads(p.stdout)
    ck("json端到端可解析", data["已缴费用"] == 9800.0)
except Exception as e:
    ck("json端到端可解析(False):%s" % e, False)

outp = os.path.join(HERE, "_e2e_report.md")
p = run([os.path.join(HERE, "样例.md"), "--base", "2026-10-05", "--out", outp])
ck("写文件rc=0", p.returncode == 0)
ck("写文件成功", os.path.exists(outp) and os.path.getsize(outp) > 800)
if os.path.exists(outp):
    txt = open(outp, encoding="utf-8").read()
    ck("写文件内容完整", "## 十一、待办补正动作" in txt)
    try:
        os.remove(outp)
    except Exception:
        pass

# ---------------------------------------------------------- 结果
res = os.path.join(HERE, "_reg_result.txt")
lines = ["PASS=%d" % len(PASS), "FAIL=%d" % len(FAIL)]
if FAIL:
    lines += ["- " + x for x in FAIL]
out = "\n".join(lines) + "\n"
with open(res, "w", encoding="utf-8") as fh:
    fh.write(out)
print(out)
sys.exit(1 if FAIL else 0)
