# -*- coding: utf-8 -*-
"""二手房买卖风险与费用核查脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import housing_deal_check as T  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)
PY = sys.executable


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        house="", price="", ownership="", coowner="", mortgage="",
        certificate="", earnest="", subject_risk="", lease="", hukou="",
        agent_fee="", loan="", qualify="", supervision="",
        deposit_to_whom="", mortgage_clear="", stage="",
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
ck("norm去空格", T.norm(" 浦东  ") == "浦东")
ck("norm统一冒号", T.norm("总价：320万") == "总价:320万")
ck("filled空串=False", T.filled("") is False)
ck("filled斜杠提示=False", T.filled("是/否") is False)
ck("filled待填=False", T.filled("待填") is False)
ck("filled0不为空", T.filled(0) is True)
ck("filled数字不崩", T.filled(3200000) is True)
ck("yes是", T.yes("是") is True)
ck("yes已网签", T.yes("已网签") is True)
ck("no否", T.no("否") is True)
ck("unknown不清楚", T.unknown("不清楚") is True)
ck("unknown有值=False", T.unknown("卖方本人") is False)
ck("parse_num元", T.parse_num("3200000元") == 3200000.0)
ck("parse_num空=None", T.parse_num("") is None)
ck("fmt_num去.0", T.fmt_num(96000.0) == "96000")
ck("money前缀", T.money(96000.0) == "¥96000")
ck("parse_date", T.parse_date("2026-09-20") == date(2026, 9, 20))
ck("parse_date中文", T.parse_date("2026年9月20日") == date(2026, 9, 20))
ck("hit_any命中", T.hit_any("中介公司员工个人账户", ["中介", "个人账户"]) is True)
ck("hit_any未命中=False", T.hit_any("卖方本人", ["中介", "个人账户"]) is False)
ck("hit_any空=None", T.hit_any("", ["中介"]) is None)

# ---------------------------------------------------------- 采集表解析
kv = T.build_kv(T.read_text(os.path.join(HERE, "样例.md")))
f = T.build_fields(kv)
ck("解析房屋地址", "浦东" in f["house"])
ck("解析总价", T.parse_num(f["price"]) == 3200000.0)
ck("解析产权人", "卖方本人" in f["ownership"])
ck("解析抵押", "抵押" in f["mortgage"])
ck("解析付款对象", "中介" in f["deposit_to_whom"])
ck("解析进度", "定金" in f["stage"])
ck("解析户口为否", f["hukou"] == "否")
ck("解析材料勾选", "身份证" in f["evidence_owned"])

kve = T.build_kv(T.read_text(os.path.join(HERE, "空输入.md")))
fe = T.build_fields(kve)
ck("空表全空", all((v or "").strip() == "" for v in fe.values()))

# ---------------------------------------------------------- 一 标的与权属
r = T.checks_title(mk(ownership="卖方本人", coowner="否",
                      mortgage="无", certificate="是"))
chk("产权清晰", r, "产权归属是否清晰", "通过")
chk("无共有人", r, "共有权人是否已签字", "通过")
chk("无抵押", r, "抵押查封情况", "通过")
chk("已核验产权证", r, "产权证与实际是否一致", "通过")

r = T.checks_title(mk(coowner="是"))
chk("缺产权人待补正", r, "产权归属是否清晰", "待补正")
chk("有共有人有风险", r, "共有权人是否已签字", "有风险")
chk("缺抵押待补正", r, "抵押查封情况", "待补正")
chk("缺产权证待补正", r, "产权证与实际是否一致", "待补正")

r = T.checks_title(mk(ownership="卖方", coowner="否",
                      mortgage="有，抵押80万未解", certificate="否"))
chk("有抵押有风险", r, "抵押查封情况", "有风险")
chk("未核验产权证不通过", r, "产权证与实际是否一致", "不通过")

# ---------------------------------------------------------- 二 合同条款
r = T.checks_contract(mk(earnest="是", subject_risk="主卧渗水，有租客",
                         lease="是", hukou="否"))
chk("定金有风险", r, "定金条款是否写清", "有风险")
chk("披露渗水有风险", r, "卖方是否披露已知风险", "有风险")
chk("有租客有风险", r, "租赁情况是否核实", "有风险")
# 字段是「是否已迁出」，填「否」= 还没迁，必须是有风险而不是通过
chk("户口未迁有风险", r, "户口迁出安排", "有风险")

r = T.checks_contract(mk(earnest="否", subject_risk="无异常", lease="否",
                         hukou="已迁出"))
chk("无定金通过", r, "定金条款是否写清", "通过")
chk("无租赁通过", r, "租赁情况是否核实", "通过")
chk("户口已迁通过", r, "户口迁出安排", "通过")

r = T.checks_contract(mk())
chk("缺定金待补正", r, "定金条款是否写清", "待补正")
chk("缺披露待补正", r, "卖方是否披露已知风险", "待补正")
chk("缺租赁待补正", r, "租赁情况是否核实", "待补正")
chk("缺户口待补正", r, "户口迁出安排", "待补正")

# ---------------------------------------------------------- 三 费用测算
c = T.calc_cost(mk(price="3200000", agent_fee=""))
ck("可测算", c["可测算"] is True)
ck("契税3%=96000", abs(c["已知合计"] - 96000.0) < 0.01)
ck("缺中介费", "中介服务费" in c["缺项"])
ck("算式有内容", len(c["算式"]) >= 1)

c2 = T.calc_cost(mk(price="3200000", agent_fee="32000"))
ck("含中介费合计128000", abs(c2["已知合计"] - 128000.0) < 0.01)
c3 = T.calc_cost(mk(price=""))
ck("无总价不可测算", c3["可测算"] is False)
r = T.checks_cost(mk(price=""), c3)
chk("不可测算待补正", r, "税费与中介费测算", "待补正")

# ---------------------------------------------------------- 四 贷款与资格
r = T.checks_loan(mk(loan="是", qualify="否"))
chk("需贷款通过", r, "是否需要贷款", "通过")
# 字段是「是否符合限购条件」，填「否」= 不符合，无法网签过户，应判不通过
chk("不符合限购不通过", r, "购房资格与限购", "不通过")
r = T.checks_loan(mk(loan="否", qualify="是"))
chk("全款通过", r, "是否需要贷款", "通过")
chk("资格有疑有风险", r, "购房资格与限购", "有风险")
r = T.checks_loan(mk(loan="否", qualify="是2"))
r = T.checks_loan(mk(loan="否", qualify="符合"))
chk("资格确认通过", r, "购房资格与限购", "通过")
r = T.checks_loan(mk())
chk("缺贷款待补正", r, "是否需要贷款", "待补正")
chk("缺资格待补正", r, "购房资格与限购", "待补正")

# ---------------------------------------------------------- 五 资金安全
r = T.checks_money(mk(supervision="是", deposit_to_whom="卖方本人",
                       mortgage_clear="已解押"))
chk("有监管通过", r, "是否采用资金监管", "通过")
chk("付给卖方通过", r, "款项支付对象", "通过")
chk("已解押通过", r, "解押与过户衔接", "通过")

r = T.checks_money(mk(supervision="否", deposit_to_whom="中介公司员工个人账户",
                       mortgage_clear="卖方说自己存款赎楼，解押后过户"))
chk("无监管不通过", r, "是否采用资金监管", "不通过")
chk("付中介个人不通过", r, "款项支付对象", "不通过")
# 填了内容且提到解押/赎楼 = 带押过户，应为有风险
chk("带押过户有风险", r, "解押与过户衔接", "有风险")

r = T.checks_money(mk())
chk("缺监管待补正", r, "是否采用资金监管", "待补正")
chk("缺付款对象待补正", r, "款项支付对象", "待补正")
chk("缺解押待补正", r, "解押与过户衔接", "待补正")

# ---------------------------------------------------------- 六 流程节点
r = T.checks_stage(mk(stage="已付定金"))
chk("定金阶段", r, "当前交易进度", "通过")
chk("定金阶段风险", r, "定金阶段风险", "有风险")
r = T.checks_stage(mk(stage="已过户"))
chk("跳过网签风险", r, "跳过网签风险", "有风险")
r = T.checks_stage(mk(stage="已交房"))
chk("交房风险通过", r, "交房风险", "通过")
r = T.checks_stage(mk(stage=""))
chk("缺进度待补正", r, "当前交易进度", "待补正")
r = T.checks_stage(mk(stage="在看房"))
chk("进度不明待补正", r, "当前交易进度", "待补正")

# ---------------------------------------------------------- 七 证据
r = T.checks_evidence(mk(evidence_owned="身份证,合同", evidence_desc="身份证复印件"))
chk("身份材料通过", r, "身份与产权证明", "通过")
chk("合同凭证通过", r, "合同与付款凭证", "通过")
chk("证据总览有风险", r, "身份与产权证明", "通过")
r = T.checks_evidence(mk())
chk("空证据总览待补正", r, "证据总览", "待补正")
g = T.evidence_gap(mk(supervision="否"))
ck("无监管必缺监管记录", "资金监管记录" in g)
ck("空证据缺6类", len(g) >= 6)
g2 = T.evidence_gap(mk(evidence_owned="身份证,产权证,合同,网签,监管,交房,承诺书,物业费",
                       evidence_desc="全部", supervision="是"))
ck("材料齐全缺口少", len(g2) == 0)

# ---------------------------------------------------------- 路径与待办
ck("路径7步", len(T.path_steps(mk())) == 7)
todos = T.todo_list(mk(supervision="否", certificate="否", price=""), [])
ck("无监管进待办", any("资金监管" in n for n, _s in todos))
ck("未核验产权证进待办", any("产权证" in n for n, _s in todos))

# ---------------------------------------------------------- 报告渲染
results = [
    ("标的与权属核查", T.checks_title(f)),
    ("合同条款风险", T.checks_contract(f)),
    ("税费与中介费测算", T.checks_cost(f, T.calc_cost(f))),
    ("贷款与购房资格", T.checks_loan(f)),
    ("资金安全与网签过户", T.checks_money(f)),
    ("交易进度与节点风险", T.checks_stage(f)),
    ("证据清单与缺口", T.checks_evidence(f)),
]
calc = T.calc_cost(f)
steps = T.path_steps(f)
todos = T.todo_list(f, results)
gaps = T.evidence_gap(f)
rep = T.render(f, results, calc, steps, todos, TODAY, gaps)
ck("报告有标题", rep.startswith("# 二手房买卖风险与费用核查报告"))
ck("报告无乱码", "\ufffd" not in rep)
ck("报告有8个以上段", rep.count("\n## ") >= 8)
ck("报告含四态字样", all(w in rep for w in ("通过", "有风险", "不通过", "待补正")))
ck("报告未填不算通过", "未填的一律不算通过" in rep)
ck("报告段标题齐全", all(t in rep for t in T.SECTIONS))

empty_results = [
    ("标的与权属核查", T.checks_title(fe)),
    ("合同条款风险", T.checks_contract(fe)),
    ("税费与中介费测算", T.checks_cost(fe, T.calc_cost(fe))),
    ("贷款与购房资格", T.checks_loan(fe)),
    ("资金安全与网签过户", T.checks_money(fe)),
    ("交易进度与节点风险", T.checks_stage(fe)),
    ("证据清单与缺口", T.checks_evidence(fe)),
]
rep0 = T.render(fe, empty_results, T.calc_cost(fe), T.path_steps(fe),
               T.todo_list(fe, empty_results), TODAY, T.evidence_gap(fe))
ck("空表报告仍有段", rep0.count("\n## ") >= 8)
ck("空表无乱码", "\ufffd" not in rep0)

js = T.to_json(f, results, todos, TODAY, gaps, calc)
ck("json核查日期", js["核查日期"] == "2026-10-05")
ck("json总价", js["总价"] == 3200000.0)
ck("json有不通过项", len(js["结论"]["不通过"]) >= 1)
ck("json待办非空", len(js["待办"]) >= 1)
ck("json可序列化", isinstance(json.dumps(js, ensure_ascii=False), str))

# ---------------------------------------------------------- 端到端
SCRIPT = os.path.join(SCRIPTS, "housing_deal_check.py")


def run(args):
    return subprocess.run([PY, SCRIPT] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


p = run([os.path.join(HERE, "样例.md")])
ck("样例rc=0", p.returncode == 0)
ck("样例stdout有报告", "二手房买卖风险与费用核查报告" in p.stdout)
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
    ck("json端到端可解析", data["总价"] == 3200000.0)
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
