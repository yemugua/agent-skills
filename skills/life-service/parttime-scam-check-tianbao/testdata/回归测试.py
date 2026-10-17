# -*- coding: utf-8 -*-
"""兼职刷单返利诈骗识别与止损追回脚本回归测试。用 python 直接跑本文件。"""
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import parttime_scam_check as T  # noqa: E402

PASS = []
FAIL = []
TODAY = date(2026, 10, 5)
PY = sys.executable


def ck(name, cond):
    (PASS if cond else FAIL).append(name)


def mk(**kw):
    base = dict(
        detail="", platform="", promise="", task_flow="", chat_log="",
        paid_amount="", refunded="", extra_frozen="", reported="",
        stopped="", contacted_bank="", kept_evidence="", account_risk="",
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
ck("norm去空格", T.norm(" 甜筒 ") == "甜筒")
ck("norm统一冒号", T.norm("金额：12800") == "金额:12800")
ck("filled空串=False", T.filled("") is False)
ck("filled斜杠提示=False", T.filled("是/否") is False)
ck("filled待填=False", T.filled("待填") is False)
ck("filled数字0不为空", T.filled(0) is True)
ck("filled数字不崩", T.filled(12800) is True)
ck("yes是", T.yes("是") is True)
ck("no否", T.no("否") is True)
ck("unknown不清楚", T.unknown("不清楚") is True)
ck("unknown有值=False", T.unknown("已报警") is False)
ck("parse_num元", T.parse_num("12800元") == 12800.0)
ck("parse_num逗号", T.parse_num("12,800") == 12800.0)
ck("parse_num空=None", T.parse_num("") is None)
ck("fmt_num去.0", T.fmt_num(12800.0) == "12800")
ck("money前缀", T.money(12800.0) == "¥12800")
ck("parse_date", T.parse_date("2026-06-10") == date(2026, 6, 10))
ck("hit_any命中", T.hit_any("招聘兼职日结", ["招聘", "日结"]) is True)
ck("hit_any未命中=False", T.hit_any("朋友推荐", ["垫付", "返利"]) is False)
ck("hit_any空=None", T.hit_any("", ["垫付"]) is None)
ck("has_content竖线串=False", T.has_content("|") is False)
ck("has_content有值=True", T.has_content("a|b") is True)

# ---------------------------------------------------------- 事件类型
ck("识别刷单返利", "刷单返利类" in T.classify(mk(platform="对方给了一个甜筒任务App",
                                              task_flow="第一单垫了88，返了96")))
ck("识别点赞类", "点赞点赞类" in T.classify(mk(detail="让我点赞关注公众号做任务")))
ck("识别打字类", "打字录入类" in T.classify(mk(detail="说招打字录入员")))
ck("识别投资类", "虚假投资类" in T.classify(mk(detail="让我跟着导师炒股稳赚")))
ck("识别刷单经过", "刷单返利类" in T.classify(mk(detail="说要刷单返利")))
ck("类型空=空列表", T.classify(mk()) == [])
# 类型判断要覆盖任务流程与聊天要点（平台名本身常不含"刷单"）
ck("仅任务流程含刷单也能识别",
   "刷单返利类" in T.classify(mk(platform="某App", task_flow="让我垫付了3000")))
ck("仅聊天含刷单也能识别",
   "刷单返利类" in T.classify(mk(platform="某App", chat_log="他们让我刷单返利")))

# ---------------------------------------------------------- 骗局阶段
ck("阶段引流", "引流话术阶段" in T.detect_stages(mk(detail="在快手看到招聘，加了微信进群")))
ck("阶段小额返利", "小额返利阶段" in T.detect_stages(mk(detail="第一单垫88返96")))
ck("阶段垫资放大", "垫资放大阶段" in T.detect_stages(mk(detail="要凑单充值金额变大")))
ck("阶段冻结", "冻结解冻阶段" in T.detect_stages(mk(detail="说要解冻才能提现")))
ck("阶段威胁", "威胁拉黑阶段" in T.detect_stages(mk(detail="说不配合就拉黑我、曝光我")))
ck("阶段空=空列表", T.detect_stages(mk()) == [])

# ---------------------------------------------------------- 红旗信号
ck("红旗招聘", "以招聘兼职为名引流" in [l for l, w in T.RED_FLAGS
                                   if T.hit_any("招聘日结250", w) is True])
ck("红旗垫资", "要求垫资做任务" in [l for l, w in T.RED_FLAGS
                              if T.hit_any("要我自己出钱垫付", w) is True])
ck("红旗高返利", "以高额返利诱导" in [l for l, w in T.RED_FLAGS
                                if T.hit_any("返利佣金很高", w) is True])
ck("红旗零风险", "宣称零风险稳赚" in [l for l, w in T.RED_FLAGS
                                if T.hit_any("无风险稳赚", w) is True])
ck("红旗紧迫感", "制造时间紧迫感" in [l for l, w in T.RED_FLAGS
                                if T.hit_any("名额有限抓紧", w) is True])

# ---------------------------------------------------------- 事件性质与阶段
f_all = mk(detail="在快手看到招聘，说点赞关注做任务日结，加微信进群，"
                  "第一单垫88返96，做到第四单提示订单异常说要完成流水才能提现，"
                  "对方让我充值6800解冻，说不配合就拉黑曝光我",
            platform="甜筒任务App",
            promise="零经验都能做，日结250，满六单全额退本金",
            task_flow="在App商户下单购物，垫88返96，垫600返660，第四单要充值6800解冻",
            chat_log="对方说解冻要再充6800，承诺充完一起退；不配合就拉黑曝光",
            paid_amount="12800", refunded="1456", extra_frozen="6800",
            reported="否", stopped="是，第三次提示解冻后就没再转",
            contacted_bank="否", kept_evidence="是，聊天截图了，App页面录屏了",
            account_risk="没有，都是从自己卡里转的",
            evidence_owned="招聘,截图,聊天,微信,群,转账,银行,支付宝,账单,app,页面,录屏,任务,账号,对方",
            evidence_desc="快手广告截图，微信群聊天记录，App页面录屏，银行流水5笔，对方账号截图")

r_cls = T.checks_classify(f_all)
chk("事件性质有风险", r_cls, "事件性质", "有风险")
chk("阶段定位不通过", r_cls, "被骗阶段定位", "不通过")

# 未填经过 = 待补正
r_cls0 = T.checks_classify(mk())
chk("缺经过待补正", r_cls0, "事件性质", "待补正")

# 说了经过但没识别出类型 = 待补正
r_cls1 = T.checks_classify(mk(detail="就是网友拉我做了点事情"))
chk("无类型待补正", r_cls1, "事件性质", "待补正")

# ---------------------------------------------------------- 红旗信号核查
r_red = T.checks_redflags(f_all)
chk("红旗不通过", r_red, "话术红旗信号", "不通过")
chk("已被要求出资不通过", r_red, "是否已被要求出资", "不通过")

r_red0 = T.checks_redflags(mk())
chk("红旗全空待补正", r_red0, "话术红旗信号", "待补正")

# 没命中话术 = 有风险
r_red1 = T.checks_redflags(mk(detail="朋友介绍我去做点事情", promise="说不会出事"))
chk("红旗未命中有风险", r_red1, "话术红旗信号", "有风险")

# ---------------------------------------------------------- 资金与损失
ml, back, net = T.calc_loss(f_all)
ck("解析投入", ml == 12800.0)
ck("解析退回", back == 1456.0)
ck("净损失=投入-退回", net == 12800.0 - 1456.0)
# 防回归：追加投入已含在已投入总额里，不能再叠加一次
ck("追加投入不重复计入净损失",
   T.calc_loss(dict(paid_amount="10000", refunded="0", extra_frozen="8000"))[2] == 10000.0)
ck("无追加投入净损失也正确",
   T.calc_loss(dict(paid_amount="10000", refunded="2000", extra_frozen="0"))[2] == 8000.0)

# 「是否 X」填否 = 还没做 = 不通过（反向语义，不能判通过）
r_mon = T.checks_money(mk(paid_amount="3000", refunded="0", extra_frozen="0",
                          detail="被要求垫付了3000", promise="返利很高",
                          chat_log="对方让我垫付"))
chk("分母0退回不通过", r_mon, "已退回金额", "不通过")
chk("未追加投入通过", r_mon, "解冻或追加投入", "通过")
chk("3000属有风险", r_mon, "损失金额是否已达刑事报案标准", "有风险")

# 追加投入 > 0 = 不通过
r_mon2 = T.checks_money(mk(paid_amount="5000", refunded="1000", extra_frozen="2000"))
chk("有追加投入不通过", r_mon2, "解冻或追加投入", "不通过")

# 净损失 >= 50000 = 不通过
r_mon3 = T.checks_money(mk(paid_amount="60000", refunded="1000", extra_frozen="0"))
chk("6万不通过", r_mon3, "损失金额是否已达刑事报案标准", "不通过")

# 5000 <= 净损失 < 50000 = 有风险
r_mon4 = T.checks_money(mk(paid_amount="20000", refunded="3000", extra_frozen="0"))
chk("2万有风险", r_mon4, "损失金额是否已达刑事报案标准", "有风险")

# 投入未填 = 待补正
r_mon0 = T.checks_money(mk())
chk("缺投入待补正", r_mon0, "已投入金额", "待补正")
chk("缺退回待补正", r_mon0, "已退回金额", "待补正")

# 有退回 = 有风险（返利是小额诱饵）
r_mon5 = T.checks_money(mk(paid_amount="1000", refunded="96", extra_frozen="0"))
chk("有退回有风险", r_mon5, "已退回金额", "有风险")

# ---------------------------------------------------------- 处置与报案
r_rep = T.checks_report(f_all)
chk("未报警不通过", r_rep, "是否已报警", "不通过")
chk("已停止转账通过", r_rep, "是否已停止转账", "通过")
chk("未止付不通过", r_rep, "是否已联系银行或支付平台止付", "不通过")
chk("证据已保留通过", r_rep, "证据是否已保留", "通过")
chk("未出借账户通过", r_rep, "是否涉及出借账户", "通过")

# 「是否 X」填否的反向语义
r_rep0 = T.checks_report(mk(reported="否", stopped="否", contacted_bank="否",
                            kept_evidence="否", account_risk="否"))
chk("未报警仍不通过", r_rep0, "是否已报警", "不通过")
chk("未停止仍不通过", r_rep0, "是否已停止转账", "不通过")
chk("未止付仍不通过", r_rep0, "是否已联系银行或支付平台止付", "不通过")

# 填是 = 通过
r_rep1 = T.checks_report(mk(reported="是", stopped="是", contacted_bank="是",
                            kept_evidence="是", account_risk="否"))
chk("已报警通过", r_rep1, "是否已报警", "通过")
chk("已停止通过", r_rep1, "是否已停止转账", "通过")
chk("已止付通过", r_rep1, "是否已联系银行或支付平台止付", "通过")
chk("证据已留通过", r_rep1, "证据是否已保留", "通过")

# 带后缀的「是」也能判出
r_rep2 = T.checks_report(mk(reported="已经报警了", stopped="已经停转了",
                            contacted_bank="打了银行电话申请止付",
                            kept_evidence="截图录屏都留了"))
chk("带后缀已报警通过", r_rep2, "是否已报警", "通过")
chk("带后缀已停止通过", r_rep2, "是否已停止转账", "通过")
chk("带后缀已止付通过", r_rep2, "是否已联系银行或支付平台止付", "通过")
chk("带后缀证据通过", r_rep2, "证据是否已保留", "通过")

# 出借账户 = 不通过（可能涉帮信罪）
r_rep3 = T.checks_report(mk(reported="是", account_risk="把我的银行卡借给对方收款了"))
chk("出借账户不通过", r_rep3, "是否涉及出借账户", "不通过")
r_rep3b = T.checks_report(mk(reported="是", account_risk="把我的银行卡借给对方收款了"))
chk("借银行卡不通过", r_rep3b, "是否涉及出借账户", "不通过")

# 全空 = 待补正
r_rep4 = T.checks_report(mk())
chk("缺报警待补正", r_rep4, "是否已报警", "待补正")
chk("缺停止待补正", r_rep4, "是否已停止转账", "待补正")
chk("缺账户待补正", r_rep4, "是否涉及出借账户", "待补正")

# ---------------------------------------------------------- 证据
r_ev = T.checks_evidence(f_all)
ck("证据段有结论", len(r_ev) >= 5)
ck("聊天已具备通过", any(r[0] == "聊天与任务指令" and r[1] == "通过" for r in r_ev))
ck("转账已具备通过", any(r[0] == "转账与支付记录" and r[1] == "通过" for r in r_ev))
r_ev0 = T.checks_evidence(mk())
chk("证据全空待补正", r_ev0, "证据总览", "待补正")
gaps0 = T.evidence_gap(mk())
ck("全空缺口7类", len(gaps0) == 7)
gaps1 = T.evidence_gap(f_all)
ck("样例缺口少", len(gaps1) <= 2)

# ---------------------------------------------------------- 报告
results = [
    ("事件性质与骗局阶段", T.checks_classify(f_all)),
    ("话术红旗信号识别", T.checks_redflags(f_all)),
    ("资金投入与损失核算", T.checks_money(f_all)),
    ("处置与报案核查", T.checks_report(f_all)),
    ("证据清单与缺口", T.checks_evidence(f_all)),
]
todos = T.todo_list(f_all, results)
gaps = T.evidence_gap(f_all)
rep = T.render(f_all, results, T.path_steps(f_all), todos, TODAY, gaps)
ck("报告有标题", rep.startswith("# 兼职刷单返利诈骗核查报告"))
ck("报告无乱码", "\ufffd" not in rep)
ck("报告有8个以上段", rep.count("\n## ") >= 8)
ck("报告含四态", all(w in rep for w in ("通过", "有风险", "不通过", "待补正")))
ck("报告段标题齐全", all(t in rep for t in T.SECTIONS))
ck("报告有紧急止损段", "## 七、紧急止损动作" in rep)
ck("报告有报警要点段", "## 九、报警要点与法律提示" in rep)
ck("报告提96110", "96110" in rep)
ck("报告提110", "110" in rep)
ck("报告提三件最急", "最该先做的三件事" in rep)
ck("报告提帮信罪", "帮信罪" in rep)
ck("报告提受案回执", "受案回执" in rep)
ck("报告提未填不算通过", "未填的一律不算通过" in rep)
ck("报告提醒不外发", "不要外发" in rep)
ck("报告有不通过项", any(r[1] == "不通过" for _t, rows in results for r in rows))
ck("报告摘要判为已受骗", "已符合刷单返利诈骗的典型特征" in rep)

# 事件类型行
ck("报告标事件类型", "刷单返利类" in rep)

# 净损失出现
ck("报告含净损失", "11344" in rep)

# 待办包含立即停止
ck("待办含立即停止", any("立即停止一切转账" in n for n, s in todos))
ck("待办含报警", any("报警" in n for n, s in todos))
ck("待办含止付", any("止付" in n for n, s in todos))

# 空表
kve = T.build_kv(T.read_text(os.path.join(HERE, "空输入.md")))
fe = T.build_fields(kve)
ck("空表全空", all((v or "").strip() == "" for v in fe.values()))
empty_results = [
    ("事件性质与骗局阶段", T.checks_classify(fe)),
    ("话术红旗信号识别", T.checks_redflags(fe)),
    ("资金投入与损失核算", T.checks_money(fe)),
    ("处置与报案核查", T.checks_report(fe)),
    ("证据清单与缺口", T.checks_evidence(fe)),
]
rep0 = T.render(fe, empty_results, T.path_steps(fe),
                T.todo_list(fe, empty_results), TODAY, T.evidence_gap(fe))
ck("空表报告仍有段", rep0.count("\n## ") >= 8)
ck("空表无乱码", "\ufffd" not in rep0)
ck("空表不崩且全是待补正",
   all(r[1] in ("待补正", "有风险") for _t, rows in empty_results for r in rows))

# 缺字段不崩
f_min = {}
ck("缺字段不崩", isinstance(T.checks_classify(f_min), list))
ck("缺字段money不崩", isinstance(T.checks_money(f_min), list))
ck("缺字段report不崩", isinstance(T.checks_report(f_min), list))
ck("缺字段evidence不崩", isinstance(T.checks_evidence(f_min), list))
ck("缺字段todo不崩", isinstance(T.todo_list(f_min, []), list))
ck("缺字段gap不崩", isinstance(T.evidence_gap(f_min), list))
ck("缺字段loss不崩", T.calc_loss(f_min) == (None, None, None))

# json
js = T.to_json(f_all, results, todos, TODAY, gaps)
ck("json核查日期", js["核查日期"] == "2026-10-05")
ck("json识别类型", "刷单返利类" in js["事件类型"])
ck("json有阶段", len(js["骗局阶段"]) >= 3)
ck("json已投入", js["已投入"] == 12800.0)
ck("json净损失", js["净损失"] == 11344.0)
ck("json有不通过项", len(js["结论"]["不通过"]) >= 1)
ck("json待办非空", len(js["待办"]) >= 1)
ck("json可序列化", isinstance(json.dumps(js, ensure_ascii=False), str))

# ---------------------------------------------------------- 端到端
SCRIPT = os.path.join(SCRIPTS, "parttime_scam_check.py")


def run(args):
    return subprocess.run([PY, SCRIPT] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


p = run([os.path.join(HERE, "样例.md")])
ck("样例rc=0", p.returncode == 0)
ck("样例有报告", "兼职刷单返利诈骗核查报告" in p.stdout)
ck("样例无乱码", "\ufffd" not in p.stdout)
ck("样例有结论摘要", "## 一、结论摘要" in p.stdout)
ck("样例识别冻结阶段", "冻结解冻阶段" in p.stdout)
ck("样例识别刷单返利类型", "刷单返利类" in p.stdout)
ck("样例识别引流阶段", "引流话术阶段" in p.stdout)

p = run([os.path.join(HERE, "空输入.md")])
ck("空输入rc=2", p.returncode == 2)
ck("空输入有段", p.stdout.count("\n## ") >= 8)
ck("空输入有缺失提示", "关键信息缺失" in p.stdout)

p = run([os.path.join(HERE, "样例.md"), "--json"])
ck("json rc=0", p.returncode == 0)
try:
    data = json.loads(p.stdout)
    ck("json端到端可解析", data["已投入"] == 12800.0)
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
