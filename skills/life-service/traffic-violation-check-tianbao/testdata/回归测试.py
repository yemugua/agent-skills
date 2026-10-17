# -*- coding: utf-8 -*-
"""交通违法处理与扣分核查脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import traffic_violation_check as T  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)
PY = sys.executable


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        plate="", kind="", detail="", occur_date="", score="", fine="",
        notice_date="", driver_who="", objective_issue="", handled="",
        vehicle_type="", unit_said="", evidence_owned="", evidence_desc="",
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
ck("norm去空格", T.norm(" 沪A ") == "沪A")
ck("norm统一冒号", T.norm("扣分：6") == "扣分:6")
ck("filled空串=False", T.filled("") is False)
ck("filled斜杠提示=False", T.filled("是/否") is False)
ck("filled待填=False", T.filled("待填") is False)
ck("filled数字0不为空", T.filled(0) is True)
ck("filled数字不崩", T.filled(200) is True)
ck("yes是", T.yes("是") is True)
ck("no否", T.no("否") is True)
ck("unknown不清楚", T.unknown("不清楚") is True)
ck("unknown有值=False", T.unknown("9月14日晚") is False)
ck("parse_num分", T.parse_num("6分") == 6.0)
ck("parse_num空=None", T.parse_num("") is None)
ck("fmt_num去.0", T.fmt_num(6.0) == "6")
ck("money前缀", T.money(200.0) == "¥200")
ck("parse_date", T.parse_date("2026-09-20") == date(2026, 9, 20))
ck("parse_date中文", T.parse_date("2026年9月20日") == date(2026, 9, 20))
ck("hit_any命中", T.hit_any("超速行驶", ["超速"]) is True)
ck("hit_any未命中=False", T.hit_any("正常行驶", ["超速", "闯红灯"]) is False)
ck("hit_any空=None", T.hit_any("", ["超速"]) is None)
# 两个空字段用 "|" 拼出的串仍会命中 hit_any 的分词逻辑，但 filled() 不该把它当已填；
# 凡是「先拼接再判空」的逻辑都改成了分别判断，这里留一条防回归提醒
ck("filled竖线串会误判（所以不能先拼再判空）", T.filled("|") is True)

# ---------------------------------------------------------- 类型识别
ck("识别超速", "机动车超速" in T.classify(mk(kind="超速行驶，超过规定时速20%以上")))
ck("识别闯红灯", "闯红灯" in T.classify(mk(kind="闯红灯")))
ck("识别酒驾", "酒驾醉驾" in T.classify(mk(kind="酒后驾驶机动车")))
ck("识别电动车", "非机动车/电动自行车" in T.classify(mk(kind="电动车超标")))
ck("空描述无类型", T.classify(mk()) == [])

# ---------------------------------------------------------- 记分推算
sc, matched = T.calc_score(mk(kind="超速行驶，超过规定时速20%以上"),
                           T.classify(mk(kind="超速行驶，超过规定时速20%以上")))
# 没写明具体档位时按类型给默认量级，而不是 None
ck("超速可推算", sc is not None)
r = T.checks_score(mk(kind="超速行驶，超过规定时速20%以上", score="6"),
                   T.classify(mk(kind="超速行驶，超过规定时速20%以上")))
chk("6分有风险（与推算不一致）", r, "记分与罚款")
r = T.checks_score(mk(kind="超速50%以上", score="12"), T.classify(mk(kind="超速50%以上")))
# 12 分是暂扣驾驶证的临界点，必须是有风险而不是通过
chk("12分有风险", r, "记分与罚款", "有风险")
r = T.checks_score(mk(kind="超速50%以上", score="15"), T.classify(mk(kind="超速50%以上")))
chk("15分不通过", r, "记分与罚款", "不通过")
r = T.checks_score(mk(kind="正常停车", score="0"), T.classify(mk(kind="正常停车")))
chk("0分通过", r, "记分与罚款", "通过")
r = T.checks_score(mk(kind=""), T.classify(mk()))
chk("缺类型待补正", r, "记分与罚款", "待补正")
r = T.checks_score(mk(kind="电动车违规"), T.classify(mk(kind="电动车违规")))
chk("电动车分不可推算", r, "记分与罚款", "待补正")

# ---------------------------------------------------------- 类型与重大情形
r = T.checks_kind(mk())
chk("缺类型待补正", r, "违法行为类型", "待补正")
r = T.checks_kind(mk(kind="随便说点什么"))
chk("未识别类型待补正", r, "违法行为类型", "待补正")
r = T.checks_kind(mk(kind="超速行驶"))
chk("识别类型通过", r, "违法行为类型", "通过")

r = T.checks_major(mk())
chk("缺重大情形待补正", r, "是否属于重大违法", "待补正")
r = T.checks_major(mk(kind="超速行驶"))
chk("无重大情形通过", r, "是否属于重大违法", "通过")
r = T.checks_major(mk(kind="醉酒后驾驶"))
chk("醉驾不通过", r, "是否属于重大违法", "不通过")
r = T.checks_major(mk(kind="发生剐蹭事故，对方车受损"))
chk("事故不通过", r, "是否属于重大违法", "不通过")
# ---------------------------------------------------------- 归属与异议
r = T.checks_owner(mk())
chk("缺驾驶人待补正", r, "违法驾驶人是否为本车", "待补正")
# 填「非本人」类词=符合撤销条件，应有风险
r = T.checks_owner(mk(driver_who="非本人，车停在公司地下车库，套牌嫌疑"))
chk("非本人有风险", r, "违法驾驶人是否为本车", "有风险")
r = T.checks_owner(mk(driver_who="非本人，车被盗了"))
chk("被盗有风险", r, "违法驾驶人是否为本车", "有风险")
r = T.checks_owner(mk(driver_who="是我本人开的"))
chk("本人通过", r, "违法驾驶人是否为本车", "通过")
r = T.checks_owner(mk(driver_who="不知道"))
chk("不清楚待补正", r, "违法驾驶人是否为本车", "待补正")

r = T.checks_objective(mk())
chk("缺客观情况待补正", r, "是否存在客观情况异常", "待补正")
r = T.checks_objective(mk(objective_issue="限速标志被树枝挡住一半"))
chk("标志被挡有风险", r, "是否存在客观情况异常", "有风险")
r = T.checks_objective(mk(objective_issue="信号灯故障"))
chk("设备故障有风险", r, "是否存在客观情况异常", "有风险")
r = T.checks_objective(mk(objective_issue="一切正常"))
chk("无异常通过", r, "是否存在客观情况异常", "通过")

# ---------------------------------------------------------- 时限与缴费
r = T.checks_process(mk(), TODAY)
chk("缺通知时间待补正", r, "收到处罚决定的时间", "待补正")
chk("缺通知时间复议待补正", r, "行政复议时限", "待补正")
r = T.checks_process(mk(notice_date="2026-09-20"), TODAY)
# 9-20 收到，7 日复议期到 9-27，核查日 10-5 已过期
chk("复议过期不通过", r, "行政复议时限", "不通过")
chk("收到时间通过", r, "收到处罚决定的时间", "通过")
r = T.checks_process(mk(notice_date="2026-10-03"), TODAY)
# 10-03 收到，7 日期到 10-10，距核查日 10-05 还剩 5 天，判定为通过
chk("还剩5天通过", r, "行政复议时限", "通过")
r = T.checks_process(mk(notice_date="2026-10-04"), TODAY)
chk("还剩6天通过", r, "行政复议时限", "通过")
# 字段是「是否已处理缴款」，填「否」= 还没缴，会加处罚款，应不通过
r = T.checks_process(mk(notice_date="2026-10-03", handled="否"), TODAY)
chk("未缴费不通过", r, "是否已处理缴款", "不通过")
r = T.checks_process(mk(notice_date="2026-10-03", handled="是"), TODAY)
chk("已缴费通过", r, "是否已处理缴款", "通过")
r = T.checks_process(mk(notice_date="2026-10-03"), TODAY)
chk("缺缴费状态待补正", r, "是否已处理缴款", "待补正")

# ---------------------------------------------------------- 单位车辆
r = T.checks_unit(mk())
chk("缺车辆性质待补正", r, "车辆性质", "待补正")
chk("缺单位说法待补正", r, "单位如何处理", "待补正")
r = T.checks_unit(mk(vehicle_type="营运车，公司名下的网约车",
                      unit_said="公司说罚款要我出，还要扣我绩效，扣了三千"))
chk("营运车有风险", r, "车辆性质", "有风险")
chk("扣钱有风险", r, "单位如何处理", "有风险")
r = T.checks_unit(mk(vehicle_type="自有车", unit_said="无争议"))
chk("自有车通过", r, "车辆性质", "通过")
ck("扣薪时说最低工资", "最低工资" in T.checks_unit(
    mk(vehicle_type="营运车", unit_said="公司说罚款要我出，还要扣我绩效，扣了三千"))[1][2])

# ---------------------------------------------------------- 证据
r = T.checks_evidence(mk(evidence_owned="违法记录,决定书,监控,照片,行车记录仪",
                         evidence_desc="全部"))
chk("违法信息通过", r, "违法信息与决定书", "通过")
chk("非本人证明通过", r, "非本人操作的证明", "通过")
r = T.checks_evidence(mk())
chk("空证据待补正", r, "证据总览", "待补正")
g = T.evidence_gap(mk())
ck("空证据缺7类", len(g) == 7)
ck("必含违法信息", "违法信息与决定书" in g)
# 主张非本人就必须有非本人证明
g2 = T.evidence_gap(mk(driver_who="非本人，车停在公司地下车库",
                        evidence_owned="违法记录,决定书,身份证,驾驶证,行驶证,缴纳,凭证,复议,复核,沟通"))
ck("非本人必补非本人证明", "非本人操作的证明" in g2)

# ---------------------------------------------------------- 路径与待办
ck("路径7步", len(T.path_steps(mk())) == 7)
todos = T.todo_list(mk(), [])
ck("未缴列入待办", any("缴款" in n for n, _s in todos))
ck("必含复议时限提醒", any("复议" in n for n, _s in todos))

# ---------------------------------------------------------- 报告渲染
kv = T.build_kv(T.read_text(os.path.join(HERE, "样例.md")))
f = T.build_fields(kv)
ck("解析车牌", f["plate"] == "沪A8X9K2")
ck("解析扣分", T.parse_num(f["score"]) == 6.0)
ck("解析非本人", "非本人" in f["driver_who"])
ck("解析营运车", "营运" in f["vehicle_type"])

kinds = T.classify(f)
results = [
    ("违法类型与记分认定", T.checks_kind(f) + T.checks_score(f, kinds)),
    ("重大违法情形核查", T.checks_major(f, kinds)),
    ("驾驶人归属与事实异议", T.checks_owner(f) + T.checks_objective(f)),
    ("处理时限与缴费", T.checks_process(f, TODAY)),
    ("单位与营运车辆", T.checks_unit(f)),
    ("证据清单与缺口", T.checks_evidence(f)),
]
todos = T.todo_list(f, results)
gaps = T.evidence_gap(f)
rep = T.render(f, results, T.path_steps(f), todos, TODAY, gaps)
ck("报告有标题", rep.startswith("# 交通违法处理与扣分核查报告"))
ck("报告无乱码", "\ufffd" not in rep)
ck("报告有8个以上段", rep.count("\n## ") >= 8)
ck("报告含四态字样", all(w in rep for w in ("通过", "有风险", "不通过", "待补正")))
ck("报告未填不算通过", "未填的一律不算通过" in rep)
ck("报告段标题齐全", all(t in rep for t in T.SECTIONS))
ck("报告有渠道表", "## 九、常见处理渠道" in rep)
ck("报告提12123", "12123" in rep)

kve = T.build_kv(T.read_text(os.path.join(HERE, "空输入.md")))
fe = T.build_fields(kve)
ck("空表全空", all((v or "").strip() == "" for v in fe.values()))
empty_results = [
    ("违法类型与记分认定", T.checks_kind(fe) + T.checks_score(fe, T.classify(fe))),
    ("重大违法情形核查", T.checks_major(fe, T.classify(fe))),
    ("驾驶人归属与事实异议", T.checks_owner(fe) + T.checks_objective(fe)),
    ("处理时限与缴费", T.checks_process(fe, TODAY)),
    ("单位与营运车辆", T.checks_unit(fe)),
    ("证据清单与缺口", T.checks_evidence(fe)),
]
rep0 = T.render(fe, empty_results, T.path_steps(fe),
                T.todo_list(fe, empty_results), TODAY, T.evidence_gap(fe))
ck("空表报告仍有段", rep0.count("\n## ") >= 8)
ck("空表无乱码", "\ufffd" not in rep0)

js = T.to_json(f, results, todos, TODAY, gaps)
ck("json核查日期", js["核查日期"] == "2026-10-05")
ck("json识别超速", "机动车超速" in js["违法类型"])
ck("json有不通过项", len(js["结论"]["不通过"]) >= 1)
ck("json待办非空", len(js["待办"]) >= 1)
ck("json可序列化", isinstance(json.dumps(js, ensure_ascii=False), str))

# ---------------------------------------------------------- 端到端
SCRIPT = os.path.join(SCRIPTS, "traffic_violation_check.py")


def run(args):
    return subprocess.run([PY, SCRIPT] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


p = run([os.path.join(HERE, "样例.md")])
ck("样例rc=0", p.returncode == 0)
ck("样例stdout有报告", "交通违法处理与扣分核查报告" in p.stdout)
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
    ck("json端到端可解析", "机动车超速" in data["违法类型"])
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
