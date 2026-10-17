# -*- coding: utf-8 -*-
"""旅游消费退款维权核查。

输入：Markdown 采集表（支持 | 字段 | 值 | 与 字段：值，全角冒号均认）
输出：9 段核查报告，结论四态：通过 / 有风险 / 不通过 / 待补正

核心事实缺失（旅游类型、问题描述、已付金额三选一为空）→ 退出码 2，锁「待补正」。
"""
import os
import sys
import re
import json
import argparse

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

FIELD_ALIAS = [
    "旅游类型", "旅行社名称", "有无资质", "有无合同", "合同主体",
    "付款方式", "收款主体", "已付金额", "问题描述", "出行日期",
    "行程是否缩水", "强制购物", "有无平台", "平台名称", "退款诉求",
    "已发生费用", "是否出行", "证据留存",
]


def norm(s):
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s)).strip()


def filled(v):
    return norm(v) != "" and norm(v).lower() not in [t.lower() for t in EMPTY_TOKENS]


def unknown(v):
    return not filled(v)


def money(v):
    if v is None:
        return "¥0"
    try:
        f = float(v)
        s = ("%.2f" % f).rstrip("0").rstrip(".")
        return "¥" + s
    except Exception:
        return "¥" + str(v)


def parse_md(path):
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and set(norm(c) for c in cells) <= set("-: "):
                continue
            if len(cells) >= 2:
                data[cells[0]] = cells[1]
            continue
        if ":" in s or "：" in s:
            parts = re.split(r"[:：]", s, 1)
            if len(parts) == 2:
                data[parts[0].strip()] = parts[1].strip()
    return data


def get_text(f, field):
    target = norm(field)
    for k, v in f.items():
        if norm(k) == target:
            return v
    for alias in sorted(FIELD_ALIAS, key=len, reverse=True):
        if norm(alias) == target:
            for k, v in f.items():
                nk = re.sub(r"^\d+[.、)]\s*", "", norm(k))
                if nk == norm(alias):
                    return v
    return ""


def yesno(v):
    if not filled(v):
        return None
    s = norm(v)
    NEG = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "没有做")
    POS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "做过")
    for w in NEG:
        if w in s:
            return False
    for w in POS:
        if w in s:
            return True
    return None


# ---------------------------------------------------------------------------
def check_qual(f):
    """资质与主体核查。"""
    items, risk = [], []
    qual = yesno(get_text(f, "有无资质"))
    provider = get_text(f, "旅行社名称")
    entity = get_text(f, "合同主体")
    payee = get_text(f, "收款主体")
    has_contract = yesno(get_text(f, "有无合同"))
    if qual is False:
        risk.append("声称无资质或无法提供旅行社业务经营许可证：属违规经营，维权与赔付保障弱")
    elif qual is True:
        items.append("已确认具备资质，仍须核对许可证编号与经营范围")
    else:
        items.append("未填写资质情况，**经营主体合法性无法确认**")
    if has_contract is False:
        items.append("未签订书面旅游合同：行程、费用、退改规则缺少依据")
    if filled(entity) and filled(payee) and norm(entity) != norm(payee):
        risk.append("合同主体与收款主体不一致（%s 收钱但 %s 签约）：追偿对象不清"
                    % (norm(payee), norm(entity)))
    if filled(provider) and not filled(entity):
        items.append("填写了旅行社但未填合同主体，**签约方身份不明**")
    status = "不通过" if risk else ("有风险" if (qual is False or has_contract is False) else "通过")
    return status, items, risk


def check_itinerary(f):
    """行程与购物核查。"""
    items, risk, crit = [], [], []
    shrink = yesno(get_text(f, "行程是否缩水"))
    forced = yesno(get_text(f, "强制购物"))
    desc = norm(get_text(f, "问题描述"))
    if shrink is True:
        risk.append("行程缩水（景点/天数/标准低于约定）：可主张违约赔偿，按差额退费")
    elif shrink is False:
        items.append("行程未缩水（自述）")
    else:
        items.append("未填写行程是否缩水，**行程履约情况无法确认**")
    if forced is True:
        crit.append("存在强制购物/擅自增加自费项目：违反《旅游法》第三十五条，可投诉并主张退货退款")
        risk.append("强制购物高危")
    elif forced is False:
        items.append("无强制购物（自述）")
    else:
        items.append("未填写是否强制购物")
    # 描述里的关键词
    if any(w in desc for w in ("跑路", "停业", "消失", "联系不上", "卷款")):
        crit.append("旅行社跑路/失联：立即集体投诉并报警（涉嫌合同诈骗），同步报文旅与市场监管")
        risk.append("跑路高危")
    if any(w in desc for w in ("擅自变更", "改行程", "换酒店", "降级")):
        risk.append("擅自变更行程/降级服务：构成违约，可主张差额退费与赔偿")
    status = "不通过" if crit else ("有风险" if risk else "通过")
    return status, items, risk, crit


def check_refund(f):
    """退款口径测算。"""
    items, risk = [], []
    paid = get_text(f, "已付金额")
    occurred = get_text(f, "已发生费用")
    traveled = yesno(get_text(f, "是否出行"))
    if not filled(paid):
        items.append("未填写已付金额，**退款基数无法测算**")
    else:
        items.append("已付金额：%s" % money(paid))
    if traveled is True:
        items.append("已出行：依《旅游法》第六十五条，解除合同时组团社在扣除已支付且不可退还的费用后，"
                     "将余款退还旅游者；可主张扣除项须有凭证")
        if filled(occurred):
            try:
                net = float(paid) - float(occurred)
                items.append("参考可退（已付−已发生）：%s" % money(round(net, 2)))
            except Exception:
                items.append("已发生费用无法计入，**退费差额无法测算**")
        else:
            items.append("未填写已发生费用，**实际可退差额无法测算**")
    elif traveled is False:
        items.append("未出行：通常可主张全额退（扣除已实际发生且不可退的订票/签证等），"
                     "因旅行社原因取消的应全额退并可能赔偿")
    else:
        items.append("未填写是否出行，**退款口径无法确认**")
    pay_way = get_text(f, "付款方式")
    if filled(pay_way) and ("个人" in norm(pay_way) or "现金" in norm(pay_way)) and "对公" not in norm(pay_way):
        risk.append("付款至个人账户/现金：缺对公凭证，追偿难，建议补开发票或收据")
    status = "不通过" if risk else "通过"
    return status, items, risk


def check_evidence(f):
    have, miss = [], []
    ev = norm(get_text(f, "证据留存"))
    checks = [
        ("旅游合同/订单", ("合同", "订单", "协议")),
        ("付款凭证", ("付款", "转账", "收据", "发票", "记录")),
        ("行程单/确认单", ("行程", "确认单", "单")),
        ("沟通记录", ("聊天", "记录", "微信", "短信", "群")),
        ("购物/损害凭证", ("购物", "小票", "发票", "照片", "票据")),
    ]
    for label, keys in checks:
        hit = False
        for k in keys:
            if k in ev and ("无" + k) not in ev and ("没有" + k) not in ev \
                    and ("未" + k) not in ev:
                hit = True
                break
        if hit:
            have.append(label)
        else:
            miss.append(label)
    return have, miss


def build_report(f, cq, ci, cr, cf, have, miss):
    lines = []
    lines.append("# 旅游消费退款维权核查报告")
    lines.append("")
    lines.append("## 一、结论摘要")
    core_missing = []
    if not filled(get_text(f, "旅游类型")):
        core_missing.append("旅游类型")
    if not filled(get_text(f, "问题描述")):
        core_missing.append("问题描述")
    if not filled(get_text(f, "已付金额")):
        core_missing.append("已付金额")
    if core_missing:
        concl = "**待补正**"
        reason = "以下核心信息缺失：" + "、".join(core_missing)
    else:
        blocking = [n for n, st in [("资质主体", cq[0]), ("行程购物", cr[0]), ("付款", cf[0])] if st == "不通过"]
        if blocking:
            concl = "**不通过**"
            reason = "存在明确风险点：" + "、".join(blocking)
        elif any(st == "有风险" for st in (cq[0], cr[0], cf[0])):
            concl = "**有风险**"
            reason = "部分环节存在风险，可按本报告补正后推进维权"
        else:
            concl = "**通过**"
            reason = "核心环节未见重大风险"
    lines.append("- 综合结论：%s" % concl)
    lines.append("- 说明：%s" % reason)
    lines.append("")

    lines.append("## 二、旅游类型与服务方")
    lines.append("- 旅游类型：%s" % (get_text(f, "旅游类型") or "（未填）"))
    lines.append("- 旅行社名称：%s" % (get_text(f, "旅行社名称") or "（未填）"))
    lines.append("- 有无平台：%s" % (get_text(f, "有无平台") or "（未填）"))
    lines.append("")

    lines.append("## 三、资质与合同主体")
    for x in cq[1]:
        lines.append("- " + x)
    if cq[2]:
        lines.append("- **风险项**：")
        for x in cq[2]:
            lines.append("  - " + x)
    lines.append("")

    lines.append("## 四、行程履约与强制购物")
    for x in ci[1]:
        lines.append("- " + x)
    if ci[3]:
        lines.append("- **高危项**：")
        for x in ci[3]:
            lines.append("  - " + x)
    if ci[2]:
        lines.append("- 风险项：")
        for x in ci[2]:
            lines.append("  - " + x)
    lines.append("")

    lines.append("## 五、退款口径测算")
    for x in cf[1]:
        lines.append("- " + x)
    if cf[2]:
        lines.append("- **风险项**：")
        for x in cf[2]:
            lines.append("  - " + x)
    lines.append("")

    lines.append("## 六、证据清单与固定要点")
    lines.append("- 已具备：%s" % ("、".join(have) if have else "（无）"))
    lines.append("- 缺失/待补：%s" % ("、".join(miss) if miss else "（齐全）"))
    lines.append("- 通用要点：旅游合同、付款凭证、行程单/确认单、与旅行社的聊天记录、"
                 "购物小票与照片、强制购物或行程缩水的现场证据，越早固定越有利")
    lines.append("")

    lines.append("## 七、维权与投诉路径")
    lines.append("- 12345 市民热线 / 全国旅游监管服务平台：旅游服务投诉主入口")
    lines.append("- 12315 / 全国 12315 平台：消费类纠纷统一入口")
    lines.append("- 文化和旅游部门：旅行社违规、强制购物、资质问题")
    lines.append("- 市场监管：虚假宣传、预付费跑路")
    lines.append("- 公安：旅行社卷款跑路、合同诈骗")
    lines.append("- 人民法院 / 人民调解：退费与赔偿诉求")
    lines.append("")

    lines.append("## 八、待办补正动作")
    todos = []
    if core_missing:
        todos.append("补齐核心信息：" + "、".join(core_missing))
    if miss:
        todos.append("补充证据：" + "、".join(miss))
    if cq[2]:
        todos.append("核实旅行社许可证与工商信息（国家企业信用信息公示系统）")
    if cf[2]:
        todos.append("补开正规发票或收据，固定付款凭证")
    if ci[3]:
        todos.append("收集强制购物/行程缩水的现场证据（录音、照片、小票），准备文旅投诉材料")
    if not todos:
        todos.append("证据齐全，可直接走 12345 / 12315 / 文旅部门发起退费诉求")
    for i, t in enumerate(todos, 1):
        lines.append("%d. %s" % (i, t))
    lines.append("")

    lines.append("## 九、边界与纪律")
    lines.append("- 本报告仅做信息核查与维权路径指引，**不构成法律意见**，复杂涉诉案件请咨询律师")
    lines.append("- 不提供任何代办投诉或代制证据服务")
    lines.append("- 法律依据：《旅游法》第三十五条（禁止强制购物）、第六十五条（解除合同的退费规则）")
    lines.append("- 地域差异：投诉受理口径以当地文旅与市场监管部门公布为准")
    lines.append("")
    return "\n".join(lines), concl


def main():
    ap = argparse.ArgumentParser(description="旅游消费退款维权核查")
    ap.add_argument("input", nargs="?", default=None, help="采集表 Markdown 路径")
    ap.add_argument("--base", default=None, help="基准日期 YYYY-MM-DD")
    ap.add_argument("--out", default=None, help="报告输出路径")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    args = ap.parse_args()
    if not args.input or not os.path.exists(args.input):
        msg = "采集表不存在或未指定：%s" % args.input
        if args.json:
            print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False))
        else:
            print(msg)
        return 2

    f = parse_md(args.input)
    if not filled(get_text(f, "旅游类型")) or not filled(get_text(f, "问题描述")) \
            or not filled(get_text(f, "已付金额")):
        cq = check_qual(f)
        ci = check_itinerary(f)
        cf = check_refund(f)
        have, miss = check_evidence(f)
        rep, concl = build_report(f, cq, ci, ci, cf, have, miss)
        if args.json:
            print(json.dumps({"结论": concl, "报告": rep}, ensure_ascii=False))
        elif args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(rep)
        else:
            print(rep)
        return 2

    cq = check_qual(f)
    ci = check_itinerary(f)
    cf = check_refund(f)
    have, miss = check_evidence(f)
    rep, concl = build_report(f, cq, ci, ci, cf, have, miss)
    if args.json:
        print(json.dumps({
            "结论": concl,
            "资质主体状态": cq[0],
            "行程购物状态": ci[0],
            "退款状态": cf[0],
            "证据已具备": have,
            "证据缺失": miss,
            "报告": rep,
        }, ensure_ascii=False))
    elif args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(rep)
    else:
        print(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
