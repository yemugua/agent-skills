# -*- coding: utf-8 -*-
"""医美退费与纠纷维权核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段核查报告，含结论摘要、机构与医师资质、合同与承诺、效果与事故、
      退款测算、证据清单、维权路径、待办补正动作、边界与纪律。

退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

FIELD_ALIAS = {
    "机构名称": ["机构名称", "医美机构", "医院名称", "门店名称", "商家名称"],
    "是否有医疗机构执业许可证": ["是否有医疗机构执业许可证", "有无执业许可证", "机构资质", "是否持牌"],
    "操作医师姓名": ["操作医师姓名", "主刀医生", "医师姓名", "医生姓名"],
    "医师是否注册执业": ["医师是否注册执业", "医师是否注册", "医师资质", "医生有无执业证"],
    "项目名称": ["项目名称", "做的项目", "消费项目", "做了什么"],
    "已付金额": ["已付金额", "已支付金额", "实付金额", "付款金额", "总花费"],
    "已退金额": ["已退金额", "已退款金额", "退款金额"],
    "付款方式": ["付款方式", "怎么付的钱", "支付渠道", "是否分期"],
    "收款主体": ["收款主体", "收款方", "收款单位", "打款给谁"],
    "是否签合同": ["是否签合同", "有无合同", "是否签约", "合同签订情况"],
    "合同是否写明项目次数价格": ["合同是否写明项目次数价格", "合同是否明细", "合同写没写项目", "合同约定"],
    "是否承诺效果": ["是否承诺效果", "有无效果承诺", "承诺了什么效果"],
 "实际效果是否达标": ["实际效果是否达标", "效果如何", "是否达到承诺", "效果满意吗"],
    "是否有增项收费": ["是否有增项收费", "有无额外收费", "是否加价", "中途收费"],
    "是否办理分期或贷款": ["是否办理分期或贷款", "有无分期", "是否贷款", "办了医美贷"],
    "术前术后照片留存": ["术前术后照片留存", "有无照片", "照片情况", "术前术后对比"],
    "聊天记录留存": ["聊天记录留存", "有无聊天记录", "沟通记录"],
    "是否出现并发症或事故": ["是否出现并发症或事故", "有无事故", "是否出事", "并发症"],
    "事故发生时间": ["事故发生时间", "出事时间", "问题发现时间"],
    "是否已投诉": ["是否已投诉", "有无投诉", "投诉情况", "是否已举报"],
    "诉求": ["诉求", "希望怎么解决", "期望结果"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)


def norm(s):
    if s is None:
        return ""
    out = str(s).strip()
    out = out.replace("：", ":").replace("　", " ")
    out = out.replace("（", "(").replace("）", ")")
    out = re.sub(r"\s+", "", out)
    return out.lower()


def filled(v):
    if v is None:
        return False
    return norm(v) not in {norm(t) for t in EMPTY_TOKENS}


def unknown(v):
    return not filled(v)


def fmt_num(n):
    if n is None:
        return "-"
    if isinstance(n, float):
        if n == int(n):
            return str(int(n))
        return ("%.2f" % n).rstrip("0").rstrip(".")
    return str(n)


def money(n):
    if n is None:
        return "-"
    return "¥" + fmt_num(round(float(n), 2))


def parse_num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("，", "")
    s = re.sub(r"[¥￥元人民币rmb$]", "", s)
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_date(v):
    if v is None or unknown(v):
        return None
    s = str(v).strip()
    s = s.replace("年", "-").replace("月", "-").replace("日", "")
    s = s.replace("/", "-").replace(".", "-")
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def parse_md(path):
    data = {}
    if not path or not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            line = line.lstrip(">").strip()
        if not line:
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2:
                continue
            key_raw = cells[0]
            if set(key_raw) <= set("-: "):
                continue
            val = " ".join(c.strip() for c in cells[1:]).strip()
            if val:
                data[norm(key_raw)] = val
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    aliases = sorted(FIELD_ALIAS.get(key, [key]), key=len, reverse=True)
    for a in aliases:
        na = norm(a)
        if not na:
            continue
        if na in f:
            v = f.get(na)
            if filled(v):
                return v
        stripped = re.sub(r"^\d+[.、)]\s*", "", na)
        if stripped != na and stripped in f:
            v = f.get(stripped)
            if filled(v):
                return v
    return ""


NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做")


def yesno(text):
    if unknown(text):
        return None
    n = norm(text)
    for w in NEG_WORDS:
        if n.startswith(w):
            return False
    for w in POS_WORDS:
        if n.startswith(w):
            return True
    return None


def check_license(f):
    items = []
    name = get_text(f, "机构名称")
    has = yesno(get_text(f, "是否有医疗机构执业许可证"))
    items.append("机构名称：%s" % (name if filled(name) else "未填写"))
    if has is False:
        items.append("**无医疗机构执业许可证**：生活美容与医疗美容分界明确，"
                     "注射、激光、手术类项目必须在持有《医疗机构执业许可证》的机构由执业医师操作，"
                     "无证开展属非法行医，可向卫生健康行政部门举报")
        status = "不通过"
    elif has is True:
        items.append("持有执业许可证：仍需核对「诊疗科目」是否包含所选项目，"
                     "超范围执业同样违法")
        status = "通过"
    else:
        items.append("未填写执业许可证情况，**机构资质无法确认**")
        status = "待补正"
    return status, items


def check_doctor(f):
    crit = []
    risk = []
    items = []
    doc = get_text(f, "操作医师姓名")
    reg = yesno(get_text(f, "医师是否注册执业"))
    if filled(doc):
        items.append("操作医师：%s" % doc)
    else:
        items.append("未填写操作医师姓名")
    if reg is False:
        crit.append("操作医师未注册执业或执业范围不符：医疗美容主诊医师须具备相应资质，"
                    "无资质操作可向卫健部门举报")
    elif reg is None:
        items.append("未填写医师注册执业情况")
    return crit, risk, items


def check_contract(f):
    crit = []
    risk = []
    items = []
    signed = yesno(get_text(f, "是否签合同"))
    detail = yesno(get_text(f, "合同是否写明项目次数价格"))
    if signed is False:
        risk.append("未签订书面合同：权利义务无载体，退费主张难度上升")
    elif signed is None:
        items.append("未填写是否签合同")
    if detail is False:
        risk.append("合同未写明项目、次数、单价：极易在退费时扯皮，"
                    "属典型格式条款陷阱")
    elif detail is None and signed is True:
        items.append("合同已签但未确认是否写明项目明细")
    return crit, risk, items


def check_effect(f):
    crit = []
    risk = []
    items = []
    promised = yesno(get_text(f, "是否承诺效果"))
    reached = yesno(get_text(f, "实际效果是否达标"))
    accident = yesno(get_text(f, "是否出现并发症或事故"))
    if promised is True and reached is False:
        risk.append("承诺了效果但实际未达标：可主张未实现约定服务内容，"
                    "要求退还对应部分费用")
    elif promised is None:
        items.append("未填写是否承诺效果")
    if accident is True:
        crit.append("出现并发症或事故：**先就医固定伤情证据**，"
                    "并保留病历、缴费与剩余产品，向卫健部门投诉并评估医疗损害鉴定")
    elif accident is None:
        items.append("未填写是否出现并发症或事故")
    return crit, risk, items


def check_extra(f):
    risk = []
    items = []
    extra = yesno(get_text(f, "是否有增项收费"))
    if extra is True:
        risk.append("存在增项/中途加价：未事前明示并征得同意的加收费用可拒付，"
                    "属价格违法线索")
    elif extra is None:
        items.append("未填写是否有增项收费")
    return risk, items


def check_finance(f):
    risk = []
    items = []
    loan = yesno(get_text(f, "是否办理分期或贷款"))
    pay = get_text(f, "付款方式")
    if loan is True:
        risk.append("办理了医美分期/贷款：**机构诱导贷款不等于债务转移**，"
                    "与机构的服务纠纷不影响还款，但可就欺诈主张撤销合同；"
                    "警惕「套路贷」，保留诱导办贷的聊天与录音")
    elif loan is None:
        items.append("未填写是否办理分期或贷款")
    if filled(pay) and any(k in norm(pay) for k in ("贷", "分期", "白条", "花呗")):
        risk.append("付款方式含信贷成分：注意区分机构责任与金融债务")
    return risk, items


def calc_refund(f, liability):
    items = []
    paid = parse_num(get_text(f, "已付金额"))
    back = parse_num(get_text(f, "已退金额")) or 0.0
    if paid is None:
        return None, ["未填写已付金额，**应退无法测算**"]
    net = paid - back
    items.append("已付 %s − 已退 %s = 未退 %s" % (money(paid), money(back), money(net)))
    if liability == "机构全责":
        items.append("**机构存在无资质/事故/欺诈等重大过错**，可主张全额退款，"
                     "造成人身损害的还可要求赔偿损失")
    elif liability == "部分责任":
        items.append("机构存在部分过错（如未写明合同、增项、效果未达）："
                     "按已消费比例协商退还未消费部分")
    else:
        items.append("暂未认定机构过错：一般按已消费、未消费部分协商退款")
    return net, items


def check_evidence(f):
    ev = " ".join(norm(get_text(f, k)) for k in (
        "聊天记录留存", "术前术后照片留存", "付款方式", "收款主体", "是否签合同"))
    need = [
        ("合同/知情同意书", ("合同", "同意书", "协议", "签字")),
        ("付款凭证", ("付款", "发票", "收据", "转账", "凭证", "分期", "贷款")),
        ("术前术后照片/影像", ("照片", "影像", "对比", "术前", "术后")),
        ("聊天记录", ("聊天", "微信", "沟通", "记录")),
        ("病历与诊疗记录", ("病历", "诊疗", "就诊", "诊断")),
    ]
    have, miss = [], []
    for name, kws in need:
        if any(k in ev for k in kws):
            have.append(name)
        else:
            miss.append(name)
    return have, miss


def build_report(f, base=None):
    rep = []
    crit = []
    risk = []
    todo = []

    name = get_text(f, "机构名称")
    paid_n = parse_num(get_text(f, "已付金额"))
    demand = get_text(f, "诉求")

    li_status, li_items = check_license(f)
    d_crit, d_risk, d_items = check_doctor(f)
    c_crit, c_risk, c_items = check_contract(f)
    e_crit, e_risk, e_items = check_effect(f)
    x_risk, x_items = check_extra(f)
    fin_risk, fin_items = check_finance(f)
    have_ev, miss_ev = check_evidence(f)

    core_missing = not filled(name) and paid_n is None
    accident = yesno(get_text(f, "是否出现并发症或事故")) is True
    no_license = yesno(get_text(f, "是否有医疗机构执业许可证")) is False

    liability = "无"
    if accident or no_license:
        liability = "机构全责"
    elif (c_risk or x_risk or e_risk):
        liability = "部分责任"

    crit.extend(d_crit)
    crit.extend(e_crit)
    risk.extend(d_risk)
    risk.extend(c_risk)
    risk.extend(e_risk)
    risk.extend(x_risk)
    risk.extend(fin_risk)
    if li_status == "不通过":
        crit.append("机构资质不通过：无照经营医疗美容属非法行医")
    elif li_status == "待补正":
        risk.append("机构资质未核验")

    if core_missing:
        verdict = "待补正"
    elif crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"

    net, refund_items = calc_refund(f, liability)

    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 机构：%s" % (name if filled(name) else "未填写"))
    rep.append("- 机构资质核查：%s" % li_status)
    rep.append("- 已付金额：%s" % (money(paid_n) if paid_n is not None else "未填写"))
    rep.append("- 过错认定：%s" % liability)
    rep.append("- 高危项 %d 项 / 风险项 %d 项" % (len(crit), len(risk)))
    rep.append("- 参考应退：%s" % (money(round(net, 2)) if net is not None else "无法测算"))
    rep.append("- **总体结论：%s**" % verdict)
    rep.append("")

    rep.append("## 机构与医师资质核查")
    rep.append("")
    for it in li_items:
        rep.append("- %s" % it)
    for c in d_crit:
        rep.append("- **%s**" % c)
    for it in d_items:
        rep.append("- %s" % it)
    rep.append("- 查询入口：国家卫生健康委员会「医疗机构执业登记」与「医师执业注册」"
               "信息查询平台；核验许可证诊疗科目与医师执业范围")
    rep.append("")

    rep.append("## 合同与承诺核查")
    rep.append("")
    for c in c_crit:
        rep.append("- **%s**" % c)
    for r in c_risk:
        rep.append("- %s" % r)
    for it in c_items:
        rep.append("- %s" % it)
    rep.append("")

    rep.append("## 效果与事故核查")
    rep.append("")
    for c in e_crit:
        rep.append("- **%s**" % c)
    for r in e_risk:
        rep.append("- %s" % r)
    for it in e_items:
        rep.append("- %s" % it)
    rep.append("")

    rep.append("## 退款测算与依据")
    rep.append("")
    for it in refund_items:
        rep.append("- %s" % it)
    for r in x_risk:
        rep.append("- %s" % r)
    for r in fin_risk:
        rep.append("- %s" % r)
    rep.append("- 法律依据：无资质/欺诈/事故情形可主张全额退款与赔偿；"
               "一般情形按《消费者权益保护法》与合同约定协商未消费部分")
    rep.append("")

    rep.append("## 证据清单与固定要点")
    rep.append("")
    if have_ev:
        rep.append("已具备：")
        for h in have_ev:
            rep.append("- %s" % h)
    else:
        rep.append("- 采集表未填写任何已留存证据")
    rep.append("")
    if miss_ev:
        rep.append("仍缺失：")
        for m in miss_ev:
            rep.append("- **%s**" % m)
    else:
        rep.append("- 主要证据类别已覆盖")
    rep.append("")
    rep.append("固定要点：术前术后照片要带时间水印；诱导贷款与效果承诺务必用文字留痕；"
               "病历和缴费单据原件不要交回机构。")
    rep.append("")

    rep.append("## 维权路径")
    rep.append("")
    rep.append("| 情形 | 向谁投诉 | 说明什么 |")
    rep.append("| --- | --- | --- |")
    rep.append("| 无执业许可证/超范围执业 | 卫生健康行政部门 | 机构名、地址、项目、时间 |")
    rep.append("| 虚假宣传、效果未达、增项加价 | 12315 / 市场监管 | 合同、付款、承诺原话 |")
    rep.append("| 并发症/医疗事故 | 卫健部门 + 医疗纠纷调解 | 病历、伤情、剩余产品 |")
    rep.append("| 诱导贷款/套路贷 | 金融监管部门 + 公安 | 聊天、办贷记录 |")
    rep.append("| 协商无果 | 法院（小额诉讼） | 全套证据链 |")
    rep.append("")
    if yesno(get_text(f, "是否已投诉")) is True:
        rep.append("- 已投诉，请保留受理编号与处理结果")
    else:
        rep.append("- 尚未投诉：先补齐资质查询截图与合同/付款证据，再一次性提交，效率最高")
    rep.append("")

    rep.append("## 待办补正动作")
    rep.append("")
    if core_missing:
        todo.append("补齐「机构名称」「已付金额」——出具结论的前提")
    if li_status != "通过":
        todo.append("到卫健部门平台核验机构执业许可证与诊疗科目、医师执业注册")
    if not filled(get_text(f, "操作医师姓名")):
        todo.append("确认操作医师姓名与执业资质")
    if yesno(get_text(f, "是否出现并发症或事故")) is True:
        todo.append("立即就医固定伤情，保留病历与缴费单据")
    for m in miss_ev:
        todo.append("补齐证据：%s" % m)
    if not filled(demand):
        todo.append("明确诉求：全额退款 / 退未消费部分 / 赔偿人身损害 / 举报查处")
    todo.append("书面提出退费要求并留送达凭证")
    for i, t in enumerate(todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见与医学判断，"
               "最终以主管部门及司法机关认定为准。")
    rep.append("- 执业许可证与医师注册的唯一权威来源是官方查询平台，本技能不代替官方核验。")
    rep.append("- 医美纠纷兼具消费与医疗属性，人身损害部分优先走医疗损害鉴定路径。")
    rep.append("- 涉及诱导贷款，债务与机构服务纠纷相互独立，勿轻信「退费即免债」。")

    return "\n".join(rep), verdict, crit + risk, todo


def main():
    ap = argparse.ArgumentParser(description="医美退费与纠纷维权核查")
    ap.add_argument("md", nargs="?", default="样例.md")
    ap.add_argument("--input", dest="input", default=None)
    ap.add_argument("--base", default=None)
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path = args.input or args.md
    if not path or not os.path.exists(path):
        msg = "采集表不存在：%s" % path
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2
    f = parse_md(path)
    if not f:
        msg = "采集表为空或格式无法解析，请用「| 字段 | 值 |」或「字段：值」格式填写"
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2

    report, verdict, issues, todo = build_report(f)
    if args.json:
        print(json.dumps({"结论": verdict, "风险项": issues, "待办": todo, "报告": report},
                         ensure_ascii=False, indent=2))
    else:
        print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)

    if not filled(get_text(f, "机构名称")) and parse_num(get_text(f, "已付金额")) is None:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
