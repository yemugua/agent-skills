# -*- coding: utf-8 -*-
"""银行卡盗刷核查与止损追回脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import bank_fraud_check as T  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)
PY = sys.executable


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        account="", discover_date="", detail="", channel="", amount="",
        count="", recovered="", frozen="", frozen_date="", password="",
        police="", verify="", bank_response="",
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
ck("norm去空格", T.norm(" 招商 ") == "招商")
ck("norm统一冒号", T.norm("金额：28600") == "金额:28600")
ck("filled空串=False", T.filled("") is False)
ck("filled斜杠提示=False", T.filled("是/否") is False)
ck("filled待填=False", T.filled("待填") is False)
ck("filled数字0不为空", T.filled(0) is True)
ck("filled数字不崩", T.filled(28600) is True)
ck("yes是", T.yes("是") is True)
ck("yes已挂失", T.yes("已挂失") is True)
ck("no否", T.no("否") is True)
ck("unknown不清楚", T.unknown("不清楚") is True)
ck("unknown有值=False", T.unknown("9月27日晚上") is False)
ck("parse_num元", T.parse_num("28600元") == 28600.0)
ck("parse_num空=None", T.parse_num("") is None)
ck("fmt_num去.0", T.fmt_num(28600.0) == "28600")
ck("money前缀", T.money(28600.0) == "¥28600")
ck("parse_date", T.parse_date("2026-09-28") == date(2026, 9, 28))
ck("parse_date中文", T.parse_date("2026年9月28日") == date(2026, 9, 28))
ck("hit_any命中", T.hit_any("手机银行", ["网络", "手机银行"]) is True)
ck("hit_any未命中=False", T.hit_any("柜面取款", ["网络", "手机银行"]) is False)
ck("hit_any空=None", T.hit_any("", ["网络"]) is None)

# ---------------------------------------------------------- 采集表解析
kv = T.build_kv(T.read_text(os.path.join(HERE, "样例.md")))
f = T.build_fields(kv)
ck("解析账户", "招商" in f["account"])
ck("解析金额", T.parse_num(f["amount"]) == 28600.0)
ck("解析笔数", f["count"] == "6")
ck("解析已挂失", f["frozen"] == "是")
ck("解析报警", f["police"] == "是")
ck("解析材料", "流水" in f["evidence_owned"])

kve = T.build_kv(T.read_text(os.path.join(HERE, "空输入.md")))
fe = T.build_fields(kve)
ck("空表全空", all((v or "").strip() == "" for v in fe.values()))

# ---------------------------------------------------------- 一 交易定性
kinds = T.classify(f)
ck("识别网络盗刷", "网络盗刷" in kinds)
# 样例只写了网络盗刷，没写诈骗/冒充/转账等词，不应硬判成诈骗类
ck("不误判诈骗", "短信诈骗转账" not in kinds)
ck("未提其他类型", "涉毒涉赌资金" not in kinds)
ck("空经过无类型", T.classify(mk()) == [])
ck("识别诈骗", "短信诈骗转账" in T.classify(mk(detail="被冒充客服骗了，转账给对方")))

r = T.checks_classify(mk())
chk("缺经过待补正", r, "盗刷交易性质", "待补正")
r = T.checks_classify(mk(detail="柜面取款"))
chk("未识别类型待补正", r, "盗刷交易性质", "待补正")
r = T.checks_classify(f)
chk("识别到类型有风险", r, "盗刷交易性质", "有风险")

# ---------------------------------------------------------- 二 紧急处置
r = T.checks_urgent(mk(frozen="是", password="是", police="是"))
chk("已挂失通过", r, "是否已挂失或冻结账户", "通过")
chk("已改密通过", r, "密码与免密授权是否已处理", "通过")
chk("已报警通过", r, "是否已报警并取得回执", "通过")

# 字段是「是否已挂失」，填「否」= 还没挂失，是最紧迫的动作，必须不通过
r = T.checks_urgent(mk(frozen="否", password="否", police="否"))
chk("未挂失不通过", r, "是否已挂失或冻结账户", "不通过")
chk("未改密不通过", r, "密码与免密授权是否已处理", "不通过")
chk("未报警有风险", r, "是否已报警并取得回执", "有风险")

r = T.checks_urgent(mk())
chk("缺挂失待补正", r, "是否已挂失或冻结账户", "待补正")
chk("缺改密待补正", r, "密码与免密授权是否已处理", "待补正")
chk("缺报警待补正", r, "是否已报警并取得回执", "待补正")

# ---------------------------------------------------------- 三 损失测算
c = T.calc_loss(f)
ck("可测算", c["可测算"] is True)
ck("损失等于全额", c["损失"] == 28600.0)
ck("笔数6", c["笔数"] == 6)
ck("多笔有说明", "6 笔" in c["说明"])

c2 = T.calc_loss(mk(amount="28600", recovered="5000", count="1"))
ck("扣掉已追回", c2["损失"] == 23600.0)
c3 = T.calc_loss(mk(amount=""))
ck("无金额不可测算", c3["可测算"] is False)
r = T.checks_loss(f, c)
chk("有损失有风险", r, "盗刷金额与损失", "有风险")
chk("多笔有风险", r, "盗刷笔数", "有风险")
r = T.checks_loss(mk(amount="1000", count="1", recovered="1000"), T.calc_loss(mk(amount="1000", count="1", recovered="1000")))
chk("全追回通过", r, "盗刷金额与损失", "通过")
chk("单笔通过", r, "盗刷笔数", "通过")
r = T.checks_loss(mk(), T.calc_loss(mk()))
chk("缺金额待补正", r, "盗刷金额与损失", "待补正")
chk("缺笔数待补正", r, "盗刷笔数", "待补正")

# ---------------------------------------------------------- 四 银行责任
r = T.checks_fault(mk())
chk("缺银行答复待补正", r, "银行如何答复", "待补正")
chk("缺责任待补正", r, "责任归属是否清楚", "待补正")

# 银行主张「本人授权过」= 对我不利，必须不通过
r = T.checks_fault(mk(bank_response="银行说可能是本人授权过的，要我提供授权证明"))
chk("银行称授权过不通过", r, "责任归属是否清楚", "不通过")
chk("有答复有风险", r, "银行如何答复", "有风险")

r = T.checks_fault(mk(bank_response="银行风控不足，未监测到异常交易"))
chk("银行风控不足有风险", r, "责任归属是否清楚", "有风险")
r = T.checks_fault(mk(bank_response="还在核实中"))
chk("未明确责任待补正", r, "责任归属是否清楚", "待补正")

r = T.checks_verify(mk(verify="未识别异常，风控未拦截"))
chk("未核验不通过", r, "银行是否做了交易核验", "不通过")
r = T.checks_verify(mk(verify="已核验，已监测"))
chk("已核验有风险", r, "银行是否做了交易核验", "有风险")
r = T.checks_verify(mk(verify="不清楚"))
chk("核验待补正", r, "银行是否做了交易核验", "待补正")
r = T.checks_verify(mk())
chk("缺核验待补正", r, "银行是否做了交易核验", "待补正")

# ---------------------------------------------------------- 五 时限
r = T.checks_time(mk(discover_date="2026-09-28", frozen_date="2026-09-28"), TODAY)
chk("发现时间通过", r, "发现时间与处置时长", "通过")
chk("当日挂失通过", r, "发现到挂失的间隔", "通过")
r = T.checks_time(mk(discover_date="2026-09-28", frozen_date="2026-10-02"), TODAY)
chk("隔4天不通过", r, "发现到挂失的间隔", "不通过")
r = T.checks_time(mk(discover_date="2026-09-28", frozen_date="2026-09-29"), TODAY)
chk("隔1天有风险", r, "发现到挂失的间隔", "有风险")
r = T.checks_time(mk(discover_date="2026-09-28"), TODAY)
chk("缺挂失日待补正", r, "发现到挂失的间隔", "待补正")
r = T.checks_time(mk(), TODAY)
chk("缺发现日待补正", r, "发现时间与处置时长", "待补正")
chk("有时限提示", r, "银行异议与投诉时限", "有风险")

# ---------------------------------------------------------- 六 证据
r = T.checks_evidence(mk(evidence_owned="身份证,流水,挂失,报警", evidence_desc="全部"))
chk("身份证明通过", r, "身份与账户证明", "通过")
chk("流水通过", r, "交易流水与明细", "通过")
chk("挂失通过", r, "挂失冻结记录", "通过")
chk("报警通过", r, "报警与立案材料", "通过")
r = T.checks_evidence(mk())
chk("空证据待补正", r, "证据总览", "待补正")
g = T.evidence_gap(mk(frozen="是", police="是"))
ck("空证据缺7类", len(g) == 7)
ck("挂了失但无记录需补", "挂失冻结记录" in g)
g2 = T.evidence_gap(mk(evidence_owned="身份证,银行卡,流水,挂失,冻结,报警,回执,立案,答复,函,录音,工单,支付平台,商户",
                       evidence_desc="全部", frozen="是", police="是"))
ck("材料齐全缺口0", len(g2) == 0)

# ---------------------------------------------------------- 路径与待办
ck("路径7步", len(T.path_steps(mk())) == 7)
ck("紧急动作8条", len(T.URGENT) == 8)
todos = T.todo_list(mk(), [], T.calc_loss(mk()))
ck("未挂失进待办", any("挂失" in n for n, _s in todos))
ck("未报警进待办", any("报警" in n for n, _s in todos))
ck("必含书面异议", any("书面" in n for n, _s in todos))

# ---------------------------------------------------------- 报告渲染
results = [
    ("交易性质与争议类型", T.checks_classify(f)),
    ("紧急止损处置核查", T.checks_urgent(f)),
    ("损失金额与笔数测算", T.checks_loss(f, c)),
    ("银行责任与核验核查", T.checks_fault(f) + T.checks_verify(f)),
    ("处置时限与维权时限", T.checks_time(f, TODAY)),
    ("证据清单与缺口", T.checks_evidence(f)),
]
todos = T.todo_list(f, results, c)
gaps = T.evidence_gap(f)
rep = T.render(f, results, c, T.path_steps(f), todos, TODAY, gaps)
ck("报告有标题", rep.startswith("# 银行卡盗刷核查与止损追回报告"))
ck("报告无乱码", "\ufffd" not in rep)
ck("报告有8个以上段", rep.count("\n## ") >= 8)
ck("报告含四态字样", all(w in rep for w in ("通过", "有风险", "不通过", "待补正")))
ck("报告未填不算通过", "未填的一律不算通过" in rep)
ck("报告段标题齐全", all(t in rep for t in T.SECTIONS))
ck("报告有紧急动作段", "## 八、紧急止损动作清单" in rep)
ck("报告有维权路径段", "## 九、维权路径与时限" in rep)

empty_results = [
    ("交易性质与争议类型", T.checks_classify(fe)),
    ("紧急止损处置核查", T.checks_urgent(fe)),
    ("损失金额与笔数测算", T.checks_loss(fe, T.calc_loss(fe))),
    ("银行责任与核验核查", T.checks_fault(fe) + T.checks_verify(fe)),
    ("处置时限与维权时限", T.checks_time(fe, TODAY)),
    ("证据清单与缺口", T.checks_evidence(fe)),
]
rep0 = T.render(fe, empty_results, T.calc_loss(fe), T.path_steps(fe),
               T.todo_list(fe, empty_results, T.calc_loss(fe)), TODAY,
               T.evidence_gap(fe))
ck("空表报告仍有段", rep0.count("\n## ") >= 8)
ck("空表无乱码", "\ufffd" not in rep0)

js = T.to_json(f, results, todos, TODAY, gaps, c)
ck("json核查日期", js["核查日期"] == "2026-10-05")
ck("json实际损失", js["实际损失"] == 28600.0)
ck("json有不通过项", len(js["结论"]["不通过"]) >= 1)
ck("json待办非空", len(js["待办"]) >= 1)
ck("json可序列化", isinstance(json.dumps(js, ensure_ascii=False), str))

# ---------------------------------------------------------- 端到端
SCRIPT = os.path.join(SCRIPTS, "bank_fraud_check.py")


def run(args):
    return subprocess.run([PY, SCRIPT] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


p = run([os.path.join(HERE, "样例.md")])
ck("样例rc=0", p.returncode == 0)
ck("样例stdout有报告", "银行卡盗刷核查与止损追回报告" in p.stdout)
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
    ck("json端到端可解析", data["实际损失"] == 28600.0)
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
