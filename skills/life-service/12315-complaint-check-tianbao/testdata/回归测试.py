# -*- coding: utf-8 -*-
"""12315 投诉核查 回归测试。运行：python 回归测试.py"""
import sys, os, subprocess, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # 工作区根
SCR = HERE.parent / "scripts" / "complaint_12315_check.py"
sys.path.insert(0, str(HERE.parent / "scripts"))
import complaint_12315_check as T

rc = 0
total = 0
fails = []
def chk(name, cond):
    global rc, total
    total += 1
    if not cond:
        fails.append(name); rc += 1

def st(items, name):
    for n, s, m in items:
        if n == name:
            return s
    return None

def mk(**kw):
    base = {k: "" for k, _ in T.build_fields()}
    base.update(kw)
    return base

# ---- 解析 ----
chk("解析两列表格", T.parse_md("| 争议问题 | 不发货 |\n| 金额 | 500 |\n").get("争议问题") == "不发货")
chk("解析冒号格式", T.parse_md("争议问题：虚假宣传\n金额：300\n").get("争议问题") == "虚假宣传")
chk("空文本返回空dict", T.parse_md("") == {})

# ---- 分类 ----
chk("识别网购类", "网络购物纠纷" in T.classify(mk(goods="淘宝买的衣服", issue="不发货")))
chk("识别虚假宣传", "虚假宣传" in T.classify(mk(issue="直播里虚假宣传夸大功效")))
chk("识别预付卡", "预付卡" in T.classify(mk(goods="健身会员卡", issue="商家跑路")))
chk("空输入分类空", T.classify(mk()) == [])

# ---- 受理范围 ----
chk("普通消费受理通过", st(T.checks_scope(mk(issue="质量不好", goods="实物商品")), "受理范围核查") == "通过")
chk("刑事诈骗不受理(不通过)", st(T.checks_scope(mk(issue="被电信诈骗转账5万")), "受理范围核查") == "不通过")
chk("劳资不受理(不通过)", st(T.checks_scope(mk(issue="老板拖欠工资社保")), "受理范围核查") == "不通过")
chk("医疗不受理(不通过)", st(T.checks_scope(mk(issue="医院误诊手术失败")), "受理范围核查") == "不通过")
chk("二手房不受理(不通过)", st(T.checks_scope(mk(issue="买二手房房东违约不过户")), "受理范围核查") == "不通过")
chk("范围未填待补正", st(T.checks_scope(mk()), "受理范围核查") == "待补正")

# ---- 证据 ----
f_all = mk(evidence="订单号、抖音支付记录、主播承诺截图、直播间录屏", has_pay="是", has_chat="是",
           order_no="DOU2026xxxx", has_photo="是", has_contract="是")
chk("证据5类=通过", st(T.checks_evidence(f_all), "证据齐全度") == "通过")
chk("证据0类=不通过", st(T.checks_evidence(mk(evidence="只有口头说没书面材料")), "证据齐全度") == "不通过")
chk("证据2类=有风险", st(T.checks_evidence(mk(evidence="订单号、支付记录")), "证据齐全度") == "有风险")
chk("证据未填待补正", st(T.checks_evidence(mk(evidence="待填")), "证据齐全度") == "待补正")

# ---- 管辖 ----
chk("异地判定有风险", st(T.checks_jurisdiction(mk(merchant_loc="广州", target_type="网店")), "管辖与主体") == "有风险")
chk("个人无照有风险", st(T.checks_jurisdiction(mk(target_type="个人微商没有营业执照")), "管辖与主体") == "有风险")
chk("本地明确通过", st(T.checks_jurisdiction(mk(merchant_loc="上海", target_type="实体店")), "管辖与主体") == "通过")
chk("管辖未填待补正", st(T.checks_jurisdiction(mk()), "管辖与主体") == "待补正")

# ---- 时效 ----
this_year = __import__("datetime").date.today().year
old = str(this_year - 4)
chk("超3年有风险", st(T.checks_time(mk(deal_date=old+"年5月")), "时效核查") == "有风险")
chk("近1年通过", st(T.checks_time(mk(deal_date=str(this_year)+"年3月")), "时效核查") == "通过")
chk("时效未填待补正", st(T.checks_time(mk()), "时效核查") == "待补正")
chk("网购七天无理由通过", "通过" in str(T.checks_time(mk(platform="淘宝", issue="不想要了申请七天无理由"))))

# ---- 协商 ----
chk("未协商有风险", st(T.checks_negotiate(mk(negotiated="否")), "先行协商") == "有风险")
chk("被拒不通过", st(T.checks_negotiate(mk(negotiated="是", neg_result="拒绝退款还拉黑")), "先行协商") == "不通过")
chk("部分退有风险", st(T.checks_negotiate(mk(negotiated="是", neg_result="退了一部分")), "先行协商") == "有风险")
chk("协商未填待补正", st(T.checks_negotiate(mk()), "先行协商") == "待补正")

# ---- 诉求 ----
chk("食品退一赔十通过", st(T.checks_claim(mk(issue="过期食品", expectation="按食品安全法赔十倍")), "诉求合理性") == "通过")
chk("欺诈退一赔三通过", st(T.checks_claim(mk(issue="虚假宣传欺诈", expectation="退一赔三")), "诉求合理性") == "通过")
chk("退款诉求通过", st(T.checks_claim(mk(expectation="要求退款")), "诉求合理性") == "通过")
chk("诉求未填待补正", st(T.checks_claim(mk()), "诉求合理性") == "待补正")

# ---- 渠道 ----
chk("违法走举报通过", st(T.checks_channel(mk(issue="假冒伪劣无照经营")), "渠道选择") == "通过")
chk("普通投诉通过", st(T.checks_channel(mk(issue="质量不好")), "渠道选择") == "通过")

# ---- 材料 ----
chk("材料缺口有风险", st(T.checks_material(mk(evidence="订单号")), "材料清单") == "有风险")
chk("材料齐通过", st(T.checks_material(mk(evidence="订单号、支付记录、聊天记录、商品照片、发票收据、检测报告、宣传海报")), "材料清单") == "通过")

# ---- 话术 ----
chk("话术待补正", st(T.checks_script(mk()), "投诉话术要点") == "待补正")
chk("话术有要点通过", st(T.checks_script(mk(expectation="退款")), "投诉话术要点") == "通过")

# ---- 进度 ----
chk("已投诉进度有风险", st(T.checks_followup(mk(neg_result="已投诉市场监管局")), "进度与升级") == "有风险")
chk("未投诉进度有风险", st(T.checks_followup(mk()), "进度与升级") == "有风险")

# ---- 证据缺口 ----
gap = T.evidence_gap(mk(evidence="订单号、支付记录"))
chk("缺口含照片", "商品照片/视频" in gap)
chk("缺口含发票", "发票/收据" in gap)
chk("已填支付不在缺口", "支付凭证" not in gap)

# ---- 待办 ----
todos = T.todo_list(mk(issue="假冒伪劣", negotiated="否", evidence="订单号"))
chk("待办含提交12315", any("12315" in t for t in todos))
chk("违法待办含举报", any("举报" in t for t in todos))
chk("未协商待办含协商", any("协商" in t for t in todos))

# ---- 渲染段数 ----
rep = T.render(mk(issue="质量不好", goods="实物", evidence="订单号、支付"))
secs = [l for l in rep.splitlines() if l.startswith("## ")]
chk("渲染12段", len(secs) == 12)
chk("含结论摘要段", "## 一、结论摘要" in rep)
chk("含受理范围段", "## 二、受理范围核查" in rep)
chk("含待办段", "## 十一、待办补正动作" in rep)
chk("含边界段", "## 十二、边界与纪律" in rep)

# ---- JSON ----
js = T.to_json(mk(issue="被电信诈骗转账5万"))
chk("json结论不通过", js["结论"] == "不通过")
chk("json含风险项", len(js["风险项"]) > 0)
chk("json含待办", len(js["待办"]) > 0)

# ---- 端到端：样例 ----
py = sys.executable
r1 = subprocess.run([py, str(SCR), str(HERE / "样例.md")], capture_output=True, text=True, encoding="utf-8")
chk("端到端样例退出0", r1.returncode == 0)
chk("端到端样例有摘要", "## 一、结论摘要" in r1.stdout)
chk("端到端样例识别不通过(协商被拒不通过)", "不通过" in r1.stdout)
rj = subprocess.run([py, str(SCR), str(HERE / "样例.md"), "--json"], capture_output=True, text=True, encoding="utf-8")
chk("端到端json退出0", rj.returncode == 0)
chk("端到端json可解析", "结论" in rj.stdout)

# ---- 端到端：空输入 ----
r2 = subprocess.run([py, str(SCR), str(HERE / "空输入.md")], capture_output=True, text=True, encoding="utf-8")
chk("空输入退出0", r2.returncode == 0)
chk("空输入有摘要", "## 一、结论摘要" in r2.stdout)
# 空输入不应把未填项判通过
chk("空输入无通过项", "| 通过 |" not in r2.stdout)

# ---- 结案 ----
if rc == 0:
    out = "PASS=%d FAIL=0\n" % total
else:
    out = "PASS=%d FAIL=%d\n%s\n" % (total - rc, rc, "\n".join(fails))
HERE.joinpath("_reg_result.txt").write_text(out, encoding="utf-8")
print(out)
sys.exit(1 if rc else 0)
