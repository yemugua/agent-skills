# -*- coding: utf-8 -*-
"""婚介服务合同与退费核查脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import matchmaker_check as T  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)
PY = sys.executable


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        service_type="", org="", detail="", contract="", promise="",
        qualification="", term="", intro_count="", intro_fake="",
        paid_amount="", installment="", refund_rule="", status="",
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
ck("norm去空格", T.norm(" 缘合 ") == "缘合")
ck("norm统一冒号", T.norm("费用：28800") == "费用:28800")
ck("filled空串=False", T.filled("") is False)
ck("filled斜杠提示=False", T.filled("是/否") is False)
ck("filled待填=False", T.filled("待填") is False)
ck("filled数字0不为空", T.filled(0) is True)
ck("filled数字不崩", T.filled(28800) is True)
ck("yes是", T.yes("是") is True)
ck("no否", T.no("否") is True)
ck("unknown不清楚", T.unknown("不清楚") is True)
ck("unknown有值=False", T.unknown("已签协议") is False)
ck("parse_num元", T.parse_num("28800元") == 28800.0)
ck("parse_num空=None", T.parse_num("") is None)
ck("fmt_num去.0", T.fmt_num(28800.0) == "28800")
ck("money前缀", T.money(28800.0) == "¥28800")
ck("parse_date", T.parse_date("2026-03-15") == date(2026, 3, 15))
ck("hit_any命中", T.hit_any("线下门店婚介", ["门店", "线下"]) is True)
ck("hit_any未命中=False", T.hit_any("自己认识", ["门店", "红娘"]) is False)
ck("hit_any空=None", T.hit_any("", ["门店"]) is None)

# ---------------------------------------------------------- 服务类型
ck("识别门店", "线下门店婚介" in T.classify(mk(service_type="线下门店婚介")))
ck("识别线上", "线上婚恋平台" in T.classify(mk(service_type="线上APP平台")))
ck("识别红娘", "红娘牵线" in T.classify(mk(service_type="红娘牵线")))
ck("空类型无结果", T.classify(mk()) == [])

r = T.checks_service(mk())
chk("缺服务类型待补正", r, "婚介服务类型", "待补正")
r = T.checks_service(mk(service_type="随便说点什么"))
chk("未识别类型待补正", r, "婚介服务类型", "待补正")
r = T.checks_service(mk(service_type="线下门店婚介"))
chk("识别类型通过", r, "婚介服务类型", "通过")

# ---------------------------------------------------------- 合同
r = T.checks_terms(mk())
chk("缺合同待补正", r, "服务合同是否规范", "待补正")
# 合同未填时，无法判断有无限制人身自由条款，不能判「通过」
chk("无合同待补正", r, "是否存在限制人身自由的条款", "待补正")
r = T.checks_terms(mk(contract="协议正常写了服务期限与介绍次数"))
chk("无限制条款通过", r, "是否存在限制人身自由的条款", "通过")
r = T.checks_terms(mk(contract="签了服务协议，写了服务期限与费用条款"))
chk("合同有风险", r, "服务合同是否规范", "有风险")
# 限制人身自由的条款 = 不通过
r = T.checks_terms(mk(contract="协议里写不准见别人，不能中途退出"))
chk("限制自由不通过", r, "是否存在限制人身自由的条款", "不通过")

# ---------------------------------------------------------- 承诺与套路
r = T.checks_promise(mk())
chk("缺承诺待补正", r, "机构做过哪些承诺", "待补正")
# 「包成功」+「限时优惠」= 不通过
r = T.checks_promise(mk(promise="说包成功，不结婚全退，优质资源多，限时优惠今天下单锁定名额"))
chk("套路承诺不通过", r, "机构做过哪些承诺", "不通过")
r = T.checks_promise(mk(promise="说会认真介绍，资源库里有很多"))
chk("未识别套路有风险", r, "机构做过哪些承诺", "有风险")

# ---------------------------------------------------------- 介绍与信息
r = T.checks_intro(mk())
chk("缺介绍数待补正", r, "实际介绍了几个人", "待补正")
chk("缺信息核实待补正", r, "介绍对象信息是否核实", "待补正")
r = T.checks_intro(mk(intro_count="4"))
chk("4人有风险（少）=通过", r, "实际介绍了几个人", "通过")
r = T.checks_intro(mk(intro_count="1"))
chk("1人有风险", r, "实际介绍了几个人", "有风险")
r = T.checks_intro(mk(intro_count="20"))
chk("20人通过", r, "实际介绍了几个人", "通过")
# 信息造假 = 不通过
r = T.checks_intro(mk(intro_count="4", intro_fake="有两个照片和本人对不上，年龄学历感觉都编的"))
chk("信息造假不通过", r, "介绍对象信息是否核实", "不通过")
r = T.checks_intro(mk(intro_count="4", intro_fake="基本都核对过"))
chk("无造假通过", r, "介绍对象信息是否核实", "通过")

# ---------------------------------------------------------- 费用
r = T.checks_fee(mk())
chk("缺费用待补正", r, "已支付费用", "待补正")
chk("缺分期待补正", r, "是否分期或贷款", "待补正")
r = T.checks_fee(mk(paid_amount="28800", installment="是"))
chk("大额有风险", r, "已支付费用", "有风险")
chk("分期不通过", r, "是否分期或贷款", "不通过")
r = T.checks_fee(mk(paid_amount="3000", installment="否"))
chk("小额通过", r, "已支付费用", "通过")
chk("无分期通过", r, "是否分期或贷款", "通过")

# ---------------------------------------------------------- 退费
r = T.checks_refund(mk())
chk("缺退费规则待补正", r, "退费规则", "待补正")
chk("缺服务状态待补正", r, "当前服务状态", "待补正")
# 「概不退款」= 不通过
r = T.checks_refund(mk(refund_rule="合同写一经付款概不退款"))
chk("概不退款不通过", r, "退费规则", "不通过")
r = T.checks_refund(mk(refund_rule="按已服务比例退，未服务部分可退"))
chk("合理退费有风险", r, "退费规则", "有风险")
r = T.checks_refund(mk(refund_rule="不明", status="已停服"))
chk("已停服通过", r, "当前服务状态", "通过")
r = T.checks_refund(mk(refund_rule="不明", status="还在做"))
chk("仍在服务有风险", r, "当前服务状态", "有风险")

# ---------------------------------------------------------- 期限
r = T.checks_timing(mk())
chk("缺期限待补正", r, "约定的服务期限", "待补正")
r = T.checks_timing(mk(term="服务期六个月，自签约日起算"))
chk("明确期限通过", r, "约定的服务期限", "通过")
# 「一直介绍到结婚为止」没有起算日与次数，属长期无节点
r = T.checks_timing(mk(term="两年，一直介绍到结婚为止"))
chk("长期无节点有风险", r, "约定的服务期限", "有风险")

# ---------------------------------------------------------- 证据
r = T.checks_evidence(mk(evidence_owned="合同,发票,介绍,照片,微信",
                         evidence_desc="全部"))
chk("合同通过", r, "合同与服务协议", "通过")
chk("介绍记录通过", r, "介绍对象信息记录", "通过")
r = T.checks_evidence(mk())
chk("空证据待补正", r, "证据总览", "待补正")
g = T.evidence_gap(mk())
ck("空证据缺7类", len(g) == 7)
ck("必含介绍记录", "介绍对象信息记录" in g)
g2 = T.evidence_gap(mk(intro_count="4",
                       evidence_owned="营业执照,注册,工商,企业,门店,合同,协议,条款,服务内容,服务期限,次数,发票,收据,转账,付款,微信,聊天,短信,录音,需求,回复,退费,要求退,投诉,协商,答复"))
ck("材料齐全仍缺介绍记录", "介绍对象信息记录" in g2)

# ---------------------------------------------------------- 路径与待办
ck("路径7步", len(T.path_steps(mk())) == 7)
todos = T.todo_list(mk(contract="不准见别人，不能中途退出", intro_fake="对方年龄造假",
                        installment="是", intro_count="", refund_rule=""), [])
ck("限制自由列入待办", any("人身自由" in n for n, _s in todos))
ck("造假列入待办", any("造假" in n for n, _s in todos))
ck("分期列入待办", any("贷款" in n for n, _s in todos))
ck("资质列入待办", any("工商" in n for n, _s in todos))

# ---------------------------------------------------------- 报告渲染
kv = T.build_kv(T.read_text(os.path.join(HERE, "样例.md")))
f = T.build_fields(kv)
ck("解析机构", "缘合" in f["org"])
ck("解析门店", "门店" in f["service_type"])
ck("解析金额", T.parse_num(f["paid_amount"]) == 28800.0)
ck("解析介绍人数", f["intro_count"] == "4")
ck("解析分期是", f["installment"].startswith("是"))

results = [
    ("服务类型与合同核查", T.checks_service(f) + T.checks_terms(f)),
    ("机构承诺与套路识别", T.checks_promise(f)),
    ("介绍服务与信息核实", T.checks_intro(f)),
    ("费用与退费规则", T.checks_fee(f) + T.checks_refund(f)),
    ("服务期限与时效风险", T.checks_timing(f)),
    ("证据清单与缺口", T.checks_evidence(f)),
]
todos = T.todo_list(f, results)
gaps = T.evidence_gap(f)
rep = T.render(f, results, T.path_steps(f), todos, TODAY, gaps)
ck("报告有标题", rep.startswith("# 婚介服务合同与退费核查报告"))
ck("报告无乱码", "\ufffd" not in rep)
ck("报告有8个以上段", rep.count("\n## ") >= 8)
ck("报告含四态字样", all(w in rep for w in ("通过", "有风险", "不通过", "待补正")))
ck("报告未填不算通过", "未填的一律不算通过" in rep)
ck("报告段标题齐全", all(t in rep for t in T.SECTIONS))
ck("报告有投诉渠道段", "## 九、投诉渠道" in rep)
ck("报告提12315", "12315" in rep)
ck("报告提醒隐私", "不要外发" in rep)

kve = T.build_kv(T.read_text(os.path.join(HERE, "空输入.md")))
fe = T.build_fields(kve)
ck("空表全空", all((v or "").strip() == "" for v in fe.values()))
empty_results = [
    ("服务类型与合同核查", T.checks_service(fe) + T.checks_terms(fe)),
    ("机构承诺与套路识别", T.checks_promise(fe)),
    ("介绍服务与信息核实", T.checks_intro(fe)),
    ("费用与退费规则", T.checks_fee(fe) + T.checks_refund(fe)),
    ("服务期限与时效风险", T.checks_timing(fe)),
    ("证据清单与缺口", T.checks_evidence(fe)),
]
rep0 = T.render(fe, empty_results, T.path_steps(fe),
                T.todo_list(fe, empty_results), TODAY, T.evidence_gap(fe))
ck("空表报告仍有段", rep0.count("\n## ") >= 8)
ck("空表无乱码", "\ufffd" not in rep0)

js = T.to_json(f, results, todos, TODAY, gaps)
ck("json核查日期", js["核查日期"] == "2026-10-05")
ck("json识别门店", "线下门店婚介" in js["服务类型"])
ck("json已支付", js["已支付"] == 28800.0)
ck("json有不通过项", len(js["结论"]["不通过"]) >= 1)
ck("json待办非空", len(js["待办"]) >= 1)
ck("json可序列化", isinstance(json.dumps(js, ensure_ascii=False), str))

# ---------------------------------------------------------- 端到端
SCRIPT = os.path.join(SCRIPTS, "matchmaker_check.py")


def run(args):
    return subprocess.run([PY, SCRIPT] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


p = run([os.path.join(HERE, "样例.md")])
ck("样例rc=0", p.returncode == 0)
ck("样例stdout有报告", "婚介服务合同与退费核查报告" in p.stdout)
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
    ck("json端到端可解析", data["已支付"] == 28800.0)
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
