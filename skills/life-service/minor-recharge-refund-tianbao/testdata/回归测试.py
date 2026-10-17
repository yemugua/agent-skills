# -*- coding: utf-8 -*-
"""未成年人游戏充值退款脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import minor_recharge_refund as T  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)
PY = sys.executable


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        child_name="", child_birth="", guardian="", platform="", scene="",
        detail="", is_minor_op="", amount="", times="", first_date="",
        period_days="", duty_done="", duty_missed="", platform_said="",
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
ck("norm去空格", T.norm(" 小宇 ") == "小宇")
ck("norm统一冒号", T.norm("金额：4860") == "金额:4860")
ck("filled空串=False", T.filled("") is False)
ck("filled斜杠提示=False", T.filled("是/否") is False)
ck("filled待填=False", T.filled("待填") is False)
ck("filled数字0不为空", T.filled(0) is True)
ck("filled数字不崩", T.filled(4860) is True)
ck("yes是", T.yes("是") is True)
ck("no否", T.no("否") is True)
ck("unknown不清楚", T.unknown("不清楚") is True)
ck("unknown有值=False", T.unknown("开了青少年模式") is False)
ck("parse_num元", T.parse_num("4860元") == 4860.0)
ck("parse_num空=None", T.parse_num("") is None)
ck("fmt_num去.0", T.fmt_num(4860.0) == "4860")
ck("money前缀", T.money(4860.0) == "¥4860")
ck("parse_date", T.parse_date("2016-05-20") == date(2016, 5, 20))
ck("parse_date中文", T.parse_date("2016年5月20日") == date(2016, 5, 20))
ck("hit_any命中", T.hit_any("某网络手游", ["游戏", "手游"]) is True)
ck("hit_any未命中=False", T.hit_any("某电商", ["游戏", "手游"]) is False)
ck("hit_any空=None", T.hit_any("", ["游戏"]) is None)

# ---------------------------------------------------------- 年龄计算
ck("年龄10岁", T.child_age(mk(child_birth="2016-05-20", _today="2026-10-05")) == 10)
ck("年龄未到生日", T.child_age(mk(child_birth="2016-12-20", _today="2026-10-05")) == 9)
ck("年龄已到生日", T.child_age(mk(child_birth="2016-10-05", _today="2026-10-05")) == 10)
ck("年龄未填=None", T.child_age(mk()) is None)

# ---------------------------------------------------------- 采集表解析
kv = T.build_kv(T.read_text(os.path.join(HERE, "样例.md")))
f = T.build_fields(kv)
ck("解析姓名", f["child_name"] == "小宇")
ck("解析出生", T.parse_date(f["child_birth"]) == date(2016, 5, 20))
ck("解析平台", "手游" in f["platform"])
ck("解析总额", T.parse_num(f["amount"]) == 4860.0)
ck("解析笔数", f["times"] == "11")
ck("解析孩子操作", f["is_minor_op"] == "是")
ck("解析材料", "户口" in f["evidence_owned"])

kve = T.build_kv(T.read_text(os.path.join(HERE, "空输入.md")))
fe = T.build_fields(kve)
ck("空表全空", all((v or "").strip() == "" for v in fe.values()))

# ---------------------------------------------------------- 一 主体与年龄
r = T.checks_subject(f, TODAY)
chk("身份通过", r, "未成年人身份", "通过")
# 10 岁属限制民事行为能力人，是退款的主要法律依据
chk("10岁限制行为能力", r, "未成年人年龄", "有风险")
ck("年龄段说明含限制民事行为能力人", "限制民事行为能力人" in r[1][2])

r = T.checks_subject(mk(child_birth="2020-05-20", _today=""), TODAY)
chk("缺姓名待补正", r, "未成年人身份", "待补正")
r = T.checks_subject(mk(child_name="小宇"), TODAY)
chk("缺出生待补正", r, "未成年人年龄", "待补正")
r = T.checks_subject(mk(child_birth="2019-05-20"), TODAY)
chk("6岁无行为能力", r, "未成年人年龄", "有风险")
r = T.checks_subject(mk(child_birth="2005-05-20"), TODAY)
chk("21岁不通过", r, "未成年人年龄", "不通过")

# ---------------------------------------------------------- 二 场景与事实
ck("识别网络游戏", "网络游戏" in T.classify(f))
ck("空平台无类型", T.classify(mk()) == [])
r = T.checks_scene(mk())
chk("缺平台待补正", r, "消费场景", "待补正")
r = T.checks_scene(mk(platform="某电商", scene="买衣服"))
chk("未识别场景待补正", r, "消费场景", "待补正")
r = T.checks_scene(f)
chk("识别场景有风险", r, "消费场景", "有风险")

r = T.checks_consume(mk())
chk("缺经过待补正", r, "充值经过与操作人", "待补正")
chk("缺操作人待补正", r, "是否为未成年人独立操作", "待补正")
r = T.checks_consume(mk(detail="孩子承认自己充的", is_minor_op="是"))
chk("有经过有风险", r, "充值经过与操作人", "有风险")
chk("孩子操作通过", r, "是否为未成年人独立操作", "通过")
# 填「否」= 监护人本人操作，退款主张很难成立，应判不通过
r = T.checks_consume(mk(detail="我充的", is_minor_op="否"))
chk("监护人操作不通过", r, "是否为未成年人独立操作", "不通过")

# ---------------------------------------------------------- 三 金额
c = T.calc_amount(f)
ck("可测算", c["可测算"] is True)
ck("总额4860", c["总额"] == 4860.0)
ck("笔数11", c["笔数"] == 11)
ck("跨度20天", c["跨度"] == "20 天")
ck("日均243", c["日均"] == 243.0)
ck("多笔有说明", "11 笔" in c["说明"])

c2 = T.calc_amount(mk(amount="1200", times="1", first_date="2026-08-03"))
ck("单笔说明", "单笔金额较低" in c2["说明"])
c3 = T.calc_amount(mk(amount=""))
ck("无金额不可测算", c3["可测算"] is False)
r = T.checks_amount(f, c)
chk("金额通过", r, "充值金额", "通过")
chk("首次时间通过", r, "首次与末次充值时间", "通过")
r = T.checks_amount(mk(), T.calc_amount(mk()))
chk("缺金额待补正", r, "充值金额", "待补正")
chk("缺首充待补正", r, "首次与末次充值时间", "待补正")

# ---------------------------------------------------------- 四 监护义务
r = T.checks_duty(mk(duty_done="开了青少年模式，消费限额设过50块，支付密码是我改的",
                      duty_missed="支付密码我没设过，是默认免密的"))
chk("已做措施通过", r, "已尽的监护义务", "通过")
# 「没设过」「免密」都命中 DUTY_MISSED，应判不通过
chk("监护缺失不通过", r, "未尽或被指出的监护义务", "不通过")

r = T.checks_duty(mk(duty_done="不清楚", duty_missed=""))
chk("缺措施待补正", r, "已尽的监护义务", "待补正")
chk("缺缺失待补正", r, "未尽或被指出的监护义务", "待补正")
r = T.checks_duty(mk(duty_done="一直很重视，定期和孩子沟通",
                      duty_missed="没有其他问题"))
chk("无缺失通过", r, "未尽或被指出的监护义务", "通过")
r = T.checks_duty(mk(duty_done="刚开了防沉迷", duty_missed=""))
chk("已开防沉迷通过", r, "已尽的监护义务", "通过")
r = T.checks_duty(mk(duty_done="没做过什么特别处理", duty_missed=""))
chk("措施未识别待补正", r, "已尽的监护义务", "待补正")

# ---------------------------------------------------------- 五 平台抗辩
r = T.checks_defense(mk())
chk("缺平台答复待补正", r, "平台的说法", "待补正")
# 样例里平台四条抗辩全中，应逐条给应对
r = T.checks_defense(f)
chk("平台抗辩有风险", r, "平台的说法", "有风险")
ck("点名实名抗辩", "实名信息是谁填的" in r[0][2])
ck("指出记录完整不等于有效", "不代表意思表示真实" in r[0][2])
r = T.checks_defense(mk(platform_said="我们正在核实中"))
chk("未识别抗辩有风险", r, "平台的说法", "有风险")

# ---------------------------------------------------------- 六 证据
r = T.checks_evidence(mk(evidence_owned="户口,充值记录,聊天,录屏,答复",
                         evidence_desc="全部"))
chk("身份证明通过", r, "身份与监护证明", "通过")
chk("消费记录通过", r, "充值消费记录", "通过")
chk("孩子操作通过", r, "孩子操作证据", "通过")
r = T.checks_evidence(mk())
chk("空证据待补正", r, "证据总览", "待补正")
g = T.evidence_gap(mk())
ck("空证据缺7类", len(g) == 7)
ck("必含孩子操作证据", "孩子操作证据" in g)
g2 = T.evidence_gap(mk(evidence_owned="身份证,户口,监护,实名,账号,订单,流水,充值记录,聊天,语音,录屏,沟通,青少年模式,设置截图,答复,工单",
                       evidence_desc="全部"))
ck("材料齐全缺口0", len(g2) == 0)

# ---------------------------------------------------------- 路径与待办
ck("路径7步", len(T.path_steps(mk())) == 7)
todos = T.todo_list(mk(), [], T.calc_amount(mk()))
ck("必含保护账号", any("保护账号" in n for n, _s in todos))
ck("必含书面申请", any("书面" in n for n, _s in todos))
ck("必含主管投诉", any("投诉" in n for n, _s in todos))

# ---------------------------------------------------------- 报告渲染
results = [
    ("未成年人主体与年龄认定", T.checks_subject(f, TODAY)),
    ("消费场景与事实认定", T.checks_scene(f) + T.checks_consume(f)),
    ("充值金额与时间跨度", T.checks_amount(f, c)),
    ("监护义务与责任抗辩", T.checks_duty(f)),
    ("平台抗辩与应对", T.checks_defense(f)),
    ("证据清单与缺口", T.checks_evidence(f)),
]
todos = T.todo_list(f, results, c)
gaps = T.evidence_gap(f)
rep = T.render(f, results, c, T.path_steps(f), todos, TODAY, gaps)
ck("报告有标题", rep.startswith("# 未成年人游戏充值退款核查报告"))
ck("报告无乱码", "\ufffd" not in rep)
ck("报告有8个以上段", rep.count("\n## ") >= 8)
ck("报告含四态字样", all(w in rep for w in ("通过", "有风险", "不通过", "待补正")))
ck("报告未填不算通过", "未填的一律不算通过" in rep)
ck("报告段标题齐全", all(t in rep for t in T.SECTIONS))
ck("报告有维权路径段", "## 八、维权路径与投诉渠道" in rep)
ck("报告提隐私保护", "不要外发" in rep)

empty_results = [
    ("未成年人主体与年龄认定", T.checks_subject(fe, TODAY)),
    ("消费场景与事实认定", T.checks_scene(fe) + T.checks_consume(fe)),
    ("充值金额与时间跨度", T.checks_amount(fe, T.calc_amount(fe))),
    ("监护义务与责任抗辩", T.checks_duty(fe)),
    ("平台抗辩与应对", T.checks_defense(fe)),
    ("证据清单与缺口", T.checks_evidence(fe)),
]
rep0 = T.render(fe, empty_results, T.calc_amount(fe), T.path_steps(fe),
               T.todo_list(fe, empty_results, T.calc_amount(fe)), TODAY,
               T.evidence_gap(fe))
ck("空表报告仍有段", rep0.count("\n## ") >= 8)
ck("空表无乱码", "\ufffd" not in rep0)

js = T.to_json(f, results, todos, TODAY, gaps, c)
ck("json核查日期", js["核查日期"] == "2026-10-05")
ck("json充值总额", js["充值总额"] == 4860.0)
ck("json有不通过项", len(js["结论"]["不通过"]) >= 1)
ck("json待办非空", len(js["待办"]) >= 1)
ck("json可序列化", isinstance(json.dumps(js, ensure_ascii=False), str))

# ---------------------------------------------------------- 端到端
SCRIPT = os.path.join(SCRIPTS, "minor_recharge_refund.py")


def run(args):
    return subprocess.run([PY, SCRIPT] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


p = run([os.path.join(HERE, "样例.md")])
ck("样例rc=0", p.returncode == 0)
ck("样例stdout有报告", "未成年人游戏充值退款核查报告" in p.stdout)
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
    ck("json端到端可解析", data["充值总额"] == 4860.0)
except Exception as e:
    ck("json端到端可解析(False):%s" % e, False)

outp = os.path.join(HERE, "_e2e_report.md")
p = run([os.path.join(HERE, "样例.md"), "--base", "2026-10-05", "--out", outp])
ck("写文件rc=0", p.returncode == 0)
ck("写文件成功", os.path.exists(outp) and os.path.getsize(outp) > 800)
if os.path.exists(outp):
    txt = open(outp, encoding="utf-8").read()
    ck("写文件内容完整", "## 十、待办补正动作" in txt)
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
