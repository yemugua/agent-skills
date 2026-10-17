# -*- coding: utf-8 -*-
"""闲鱼二手交易纠纷取证与维权核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段核查报告，含结论摘要、交易方式核查、七天无理由边界、描述不符与假货判断、
      举证与时效、证据清单、平台介入与升级路径、待办补正动作、边界与纪律。

退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

# ---------------------------------------------------------------- 字段别名

FIELD_ALIAS = {
    "平台": ["平台", "交易平台", "成交平台", "购买渠道"],
    "商品类别": ["商品类别", "商品类型", "品类", "买的什么"],
    "商品描述摘录": ["商品描述摘录", "商品描述", "卖家描述", "描述原文", "描述摘录"],
    "成交价格": ["成交价格", "商品价格", "成交价", "商品金额"],
    "运费": ["运费", "邮费", "快递费", "运费金额"],
    "已付金额": ["已付金额", "已支付金额", "实付金额", "付款金额", "支付金额"],
    "已退金额": ["已退金额", "已退款金额", "退款金额", "已返还金额"],
    "支付方式": ["支付方式", "付款方式", "怎么付的", "交易方式"],
    "下单日期": ["下单日期", "拍下日期", "购买日期", "订单日期"],
    "收货日期": ["收货日期", "签收日期", "到货日期", "签收时间"],
    "是否当面交易": ["是否当面交易", "是否面交", "当面交易", "是否线下交易"],
    "是否录制开箱视频": ["是否录制开箱视频", "有无开箱视频", "开箱视频", "是否拍开箱"],
    "是否有聊天记录": ["是否有聊天记录", "聊天记录", "有无聊天记录", "是否保留聊天"],
    "问题描述": ["问题描述", "纠纷类型", "争议类型", "发生了什么", "问题类型", "实物差异描述"],
    "实物与描述差异": ["实物与描述差异", "实物差异", "实物差异描述", "差异描述",
                      "与描述不符之处", "差异说明"],
    "卖家是否承认": ["卖家是否承认", "卖家是否承认问题", "卖家是否认责", "对方是否承认", "卖家态度"],
    "是否申请平台介入": ["是否申请平台介入", "是否申请介入", "平台介入", "是否申诉"],
    "平台处理结果": ["平台处理结果", "平台判定", "申诉结果", "介入结果"],
    "是否已投诉12315": ["是否已投诉12315", "是否投诉12315", "有无投诉", "投诉情况"],
    "卖家是否注销或失联": ["卖家是否注销或失联", "卖家是否失联", "卖家是否已失联",
                          "卖家是否注销", "能否联系上卖家"],
    "是否疑似假货": ["是否疑似假货", "是否假货", "真假情况", "是否正品"],
    "是否少件或错发": ["是否少件或错发", "是否少件", "是否错发", "配件是否齐全"],
    "是否有运输损坏": ["是否有运输损坏", "运输损坏", "是否破损", "物流损坏"],
    "卖家是否职业卖家": ["卖家是否职业卖家", "卖家是否商家", "是否为商家", "卖家性质"],
    "卖家是否引导站外付款": ["卖家是否引导站外付款", "是否站外付款", "是否引导微信直转", "有无诱导站外"],
    "是否保留快递面单": ["是否保留快递面单", "有无快递面单", "面单情况", "物流凭证"],
    "是否已退货": ["是否已退货", "是否退货", "退货情况"],
    "证据留存情况": ["证据留存情况", "证据情况", "有哪些证据", "留证情况", "已保存材料"],
    "诉求": ["诉求", "希望怎么解决", "期望结果", "想要什么结果"],
}

# ---------------------------------------------------------------- 基础工具

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做", "有/无",
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
    """未填判定，必须认得「待填/待补/待确认」这类占位词。"""
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


def days_between(a, b):
    if not a or not b:
        return None
    return (b - a).days


# ---------------------------------------------------------------- 解析


def parse_md(path):
    """读 Markdown 采集表，返回 {归一字段: 值}。"""
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
                continue  # 分隔行
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
    """精确匹配表头，绝不用子串 in（会串字段）。"""
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


NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法联系")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做")


def yesno(text):
    """「是否 X」字段取值。空 → None；否/未/没有 → False；是/已 → True。"""
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


# ---------------------------------------------------------------- 判定


def classify_issue(problem, diff, desc, extra=""):
    """问题类型识别：合并多字段全文，避免只看一个字段漏判。"""
    blob = norm(" ".join([problem, diff, desc, extra]))
    hits = []
    table = [
        ("假货/仿冒", ("假货", "仿冒", "山寨", "高仿", "假的", "不是正品", "鉴定为假")),
        ("描述不符", ("描述不符", "与描述不符", "成色不符", "型号不符", "配置不符",
                     "货不对板", "实物与描述", "不符")),
        ("商品损坏", ("损坏", "破损", "摔坏", "裂", "不能开机", "开不了机", "不开机",
                      "黑屏", "死机", "无法使用", "故障")),
        ("少件/缺件", ("少件", "缺件", "少了", "缺配", "配件缺失", "缺少")),
        ("卖家收款不发货", ("不发货", "未发货", "收款不发货", "一直不发货", "收钱不发货")),
        ("发货地/承诺不符", ("发货地", "承诺不符", "不是承诺", "未按时发货")),
    ]
    for name, kws in table:
        if any(k in blob for k in kws):
            hits.append(name)
    if not hits:
        return "未识别", ["问题描述、差异说明、商品描述三处均未给出可用信息，无法定性"]
    reasons = ["命中问题类型：%s" % "、".join(hits)]
    if len(hits) > 1:
        reasons.append("同时命中多类问题，报案/申诉时应一并说明，不要只讲其中一项")
    return hits[0], reasons


def check_channel(pay, face_to_face, seller_gone):
    """交易方式与资金安全：返回 (高危项, 风险项, 说明)。"""
    crit = []
    risk = []
    items = []
    n_pay = norm(pay)

    if not filled(pay):
        items.append("未填写支付方式，**资金能否追回无法判断**")
    elif any(k in n_pay for k in ("微信直转", "微信转账", "支付宝直转", "私下转账",
                                  "站外", "直接转账", "私转", "银行卡转账")):
        crit.append("站外直接转账，资金不经平台担保：平台通常不受理，追款只能靠报警与支付渠道投诉")
        items.append("站外交易绕过了平台担保与评价约束，是二手交易损失最高发的成因")
    elif any(k in n_pay for k in ("平台担保", "平台支付", "担保交易", "支付宝担保")):
        items.append("走平台担保支付，未确认收货前资金仍在平台，可优先申请平台介入冻结货款")
    else:
        risk.append("支付方式「%s」需进一步确认是否经平台担保" % pay)

    if yesno(face_to_face) is True:
        risk.append("当面交易：缺少物流凭证与平台担保，事后举证难度显著上升，"
                    "应留存现场视频、聊天记录与对方身份信息")
    elif yesno(face_to_face) is None:
        items.append("未填写是否当面交易")

    if yesno(seller_gone) is True:
        crit.append("卖家已注销或失联：应立即向平台举报并申请披露卖家信息，"
                    "金额较大的携转账凭证到派出所报案")
    return crit, risk, items


def check_seven(recv_date, base, is_custom, is_secondhand, seller_is_biz):
    """七天无理由适用边界：返回 (结论, 说明列表)。"""
    items = []
    if recv_date is None:
        return "待补正", ["未填写收货日期，**七天无理由期限无法核算**，需补齐"]

    d = days_between(recv_date, base)
    items.append("收货日 %s，距基准日已 %s 天" % (recv_date.isoformat(), fmt_num(d)))

    if d > 7:
        return "已超期", items + ["已超过七日，七天无理由路径关闭；"
                                  "但描述不符、假货、质量问题仍可另行主张违约责任"]
    if is_custom:
        return "不适用", items + ["定制类商品一般不在七天无理由退货范围内，"
                                  "但仍可就质量与描述不符主张违约责任"]
    if is_secondhand and not seller_is_biz:
        return "有争议", items + ["二手闲置物品交易是否适用七天无理由，实践中存在争议："
                                  "《消费者权益保护法》第二十五条的七天无理由主要面向经营者与消费者之间的远程购物，"
                                  "个人闲置交易通常按双方约定与平台规则处理。"
                                  "若卖家长期大量出售同类商品，可能被认定为经营行为而适用"]
    if d > 7:
        return "已超期", items + ["已超过七日，七天无理由路径关闭；"
                                  "但描述不符、假货、质量问题仍可另行主张违约责任"]
    return "适用", items + ["尚在七日内，可主张七天无理由退货（商品应当完好）"]


def check_evidence(unbox, chat, platform_appealed):
    """举证核查：返回 (缺口条数, 缺口列表)。"""
    gaps = []
    if yesno(unbox) is False:
        gaps.append("**未录制开箱视频**：二手交易里这是证明「收到即有问题」的关键证据，"
                    "缺了它，卖家一句「发出时是好的」就能把你顶回来")
    elif unknown(unbox):
        gaps.append("未填写是否录制开箱视频")
    if yesno(chat) is False:
        gaps.append("**未保留完整聊天记录**：卖家的成色、功能、配件承诺全靠聊天记录固定，"
                    "单张截图易被质疑断章取义")
    elif unknown(chat):
        gaps.append("未填写是否保留聊天记录")
    if yesno(platform_appealed) is False:
        gaps.append("尚未申请平台介入，平台介入有期限，逾期可能关闭入口")
    return len(gaps), gaps


def calc_refund(paid, refunded, freight):
    """退款测算：应退 = 已付 − 已退（运费按约定）。"""
    items = []
    paid_n = parse_num(paid)
    ref_n = parse_num(refunded) or 0.0
    frt_n = parse_num(freight)

    if paid_n is None:
        return None, ["未填写已付金额，**应退金额无法测算**"]

    net = paid_n - ref_n
    if net < 0:
        items.append("已退 %s 大于已付 %s，请核对金额是否填写错误" % (money(ref_n), money(paid_n)))
        net = 0.0
    items.append("已付 %s − 已退 %s = 暂计应退 %s" % (money(paid_n), money(ref_n), money(net)))
    if frt_n is not None and frt_n > 0:
        items.append("另有运费 %s，若属卖家责任可一并主张由卖家承担" % money(frt_n))
        items.append("含运费的可主张总额约 %s" % money(round(net + frt_n, 2)))
    return net, items


def check_platform(appealed, result, complained):
    """平台介入与升级路径：返回动作列表。"""
    acts = []
    a = yesno(appealed)
    if a is True:
        acts.append("已申请平台介入：保留工单号，补充提交开箱视频与聊天记录原件，"
                    "平台一般在规定时限内出具判定")
        r = norm(result)
        if any(k in r for k in ("驳回", "不支持", "失败", "维持")):
            acts.append("平台判定不利：可在期限内申请平台二次复核，"
                        "同步向 12315 投诉（卖家属经营行为时）或走司法途径")
        elif filled(result):
            acts.append("平台处理结果：%s" % str(result)[:60])
    elif a is False:
        acts.append("**尚未申请平台介入**：在订单页发起退款申请与平台介入，"
                    "介入有期限，先占位再补材料")
    else:
        acts.append("未填写是否已申请平台介入")

    if yesno(complained) is True:
        acts.append("已投诉 12315：保留受理编号，等待市场监管部门调解")
    else:
        acts.append("尚未投诉 12315：卖家长期大量出售同类商品的，"
                    "可被认定为经营行为，向 12315 或平台所在地市场监管部门投诉")
    acts.append("金额较大或卖家涉嫌诈骗的：携转账凭证、聊天记录、商品照片到派出所报案，"
                "或通过人民法院在线服务提起小额诉讼")
    return acts


# ---------------------------------------------------------------- 报告


def build_report(f, base):
    rep = []
    crit = []
    risk = []
    todo = []

    platform = get_text(f, "平台")
    cat = get_text(f, "商品类别")
    desc = get_text(f, "商品描述摘录")
    problem = get_text(f, "问题描述")
    diff = get_text(f, "实物与描述差异")
    price = parse_num(get_text(f, "成交价格"))
    paid = get_text(f, "已付金额")
    paid_n = parse_num(paid)
    refunded = get_text(f, "已退金额")
    freight = get_text(f, "运费")
    pay = get_text(f, "支付方式")
    order_d = parse_date(get_text(f, "下单日期"))
    recv_d = parse_date(get_text(f, "收货日期"))
    face = get_text(f, "是否当面交易")
    unbox = get_text(f, "是否录制开箱视频")
    chat = get_text(f, "是否有聊天记录")
    admit = get_text(f, "卖家是否承认")
    appealed = get_text(f, "是否申请平台介入")
    result = get_text(f, "平台处理结果")
    complained = get_text(f, "是否已投诉12315")
    gone = get_text(f, "卖家是否注销或失联")
    guided = get_text(f, "卖家是否引导站外付款")
    biz = get_text(f, "卖家是否职业卖家")
    demand = get_text(f, "诉求")

    extra_bits = []
    if yesno(get_text(f, "是否疑似假货")) is True:
        extra_bits.append("假货仿冒")
    if yesno(get_text(f, "是否少件或错发")) is True:
        extra_bits.append("少件缺件")
    if yesno(get_text(f, "是否有运输损坏")) is True:
        extra_bits.append("运输损坏破损")

    itype, type_reasons = classify_issue(problem, diff, desc, " ".join(extra_bits))
    c_crit, c_risk, c_items = check_channel(pay, face, gone)
    if yesno(guided) is True:
        c_crit.append("卖家主动引导站外付款：绕开平台担保，是二手交易最高发的损失成因")
    is_custom = "定制" in norm(cat) or "定制" in norm(desc)
    seven, seven_items = check_seven(recv_d, base, is_custom, True,
                                     yesno(biz) is True)
    gap_n, gaps = check_evidence(unbox, chat, appealed)
    net, refund_items = calc_refund(paid_n, parse_num(refunded), freight)
    acts = check_platform(appealed, result, complained)

    # 核心事实缺失时，不得下任何风险结论
    core_missing = not filled(problem) and not filled(diff) and paid_n is None

    if not core_missing:
        crit.extend(c_crit)
        risk.extend(c_risk)
        if itype == "假货/仿冒":
            crit.append("涉及假货：属根本违约，可主张退款并依《消费者权益保护法》相关规定主张赔偿，"
                        "需先取得品牌或第三方鉴定结论")
        if seven == "已超期":
            risk.append("七天无理由已超期，路径收窄但仍可主张违约与欺诈责任")
        if yesno(admit) is False:
            risk.append("卖家否认问题：举证责任完全落在你这边，开箱视频与聊天记录决定成败")
        if gap_n > 0:
            risk.append("证据缺口 %d 项，直接影响申诉与投诉结果" % gap_n)
        if price is not None and paid_n is not None and paid_n > price * 1.2:
            risk.append("已付 %s 明显高于成交价 %s，请核对是否存在加价或重复付款"
                        % (money(paid_n), money(price)))

    if core_missing:
        verdict = "待补正"
    elif crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "有风险"

    # --- 1 结论摘要
    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 平台：%s" % (platform if filled(platform) else "未填写"))
    rep.append("- 商品：%s" % (cat if filled(cat) else "未填写"))
    rep.append("- 支付方式：%s" % (pay if filled(pay) else "未填写"))
    rep.append("- 成交价 %s / 已付 %s / 已退 %s" %
               (money(price) if price is not None else "未填写",
                money(paid_n) if paid_n is not None else "未填写",
                money(parse_num(refunded)) if parse_num(refunded) is not None else "未填写"))
    rep.append("- **问题类型：%s**" % itype)
    rep.append("- 七天无理由：%s" % seven)
    rep.append("- 暂计应退：%s" % (money(net) if net is not None else "无法测算"))
    rep.append("- 高危项 %d 项 / 风险项 %d 项" % (len(crit), len(risk)))
    rep.append("- **总体结论：%s**" % verdict)
    rep.append("")

    # --- 2 交易方式核查
    rep.append("## 交易方式与资金安全核查")
    rep.append("")
    for it in c_items:
        rep.append("- %s" % it)
    if c_crit:
        rep.append("### 高危")
        for c in c_crit:
            rep.append("- **%s**" % c)
    if c_risk:
        rep.append("### 需留意")
        for r in c_risk:
            rep.append("- %s" % r)
    if not c_crit and not c_risk and not c_items:
        rep.append("- 未填写交易方式相关信息")
    rep.append("- 当面交易：%s" % (face if filled(face) else "未填写"))
    rep.append("")

    # --- 3 七天无理由边界
    rep.append("## 七天无理由与退货权边界")
    rep.append("")
    rep.append("- 结论：%s" % seven)
    for it in seven_items:
        rep.append("- %s" % it)
    rep.append("- 下单日：%s" % (order_d.isoformat() if order_d else "未填写"))
    rep.append("- 收货日：%s" % (recv_d.isoformat() if recv_d else "未填写"))
    rep.append("")

    # --- 4 描述不符与假货判断
    rep.append("## 描述不符、假货与责任判断")
    rep.append("")
    for r in type_reasons:
        rep.append("- %s" % r)
    if filled(desc):
        rep.append("- 商品描述摘录：%s" % str(desc)[:120])
    if filled(diff):
        rep.append("- 实物差异：%s" % str(diff)[:120])
    if yesno(admit) is True:
        rep.append("- 卖家已承认问题：把承认内容截图固定，这是最有力的证据")
    elif yesno(admit) is False:
        rep.append("- 卖家否认：需靠开箱视频、聊天记录、第三方鉴定形成证据链")
    rep.append("")

    # --- 5 举证与时效
    rep.append("## 举证与时效")
    rep.append("")
    if gaps:
        for g in gaps:
            rep.append("- %s" % g)
    else:
        rep.append("- 主要证据项已填写，仍需确认原始载体（视频原文件、完整聊天导出）是否完整")
    rep.append("")
    rep.append("补充要点：")
    rep.append("1. 开箱视频要一镜到底，包含快递外包装、面单、拆封过程与商品全貌")
    rep.append("2. 聊天记录用平台自带的聊天导出或录屏，不要只截单张图")
    rep.append("3. 转账凭证保留带流水号的完整截图")
    rep.append("4. 假货争议需品牌官方或第三方鉴定机构出具结论")
    rep.append("")

    # --- 6 证据清单
    rep.append("## 证据清单与固定要点")
    rep.append("")
    rep.append("| 材料 | 状态 |")
    rep.append("| --- | --- |")
    rep.append("| 商品描述截图 | %s |" % ("已留存" if filled(desc) else "**待补**"))
    rep.append("| 开箱视频 | %s |" % ("有" if yesno(unbox) is True else "**待补**"))
    rep.append("| 聊天记录 | %s |" % ("有" if yesno(chat) is True else "**待补**"))
    rep.append("| 支付凭证 | %s |" % ("有" if paid_n is not None else "**待补**"))
    rep.append("| 物流与面单 | %s |" % ("有" if recv_d else "**待补**"))
    rep.append("")

    # --- 7 平台介入与升级路径
    rep.append("## 平台介入与升级路径")
    rep.append("")
    for a in acts:
        rep.append("- %s" % a)
    rep.append("")
    rep.append("顺序建议：平台介入 → 12315 投诉 → 报警或小额诉讼，逐级推进并保留每一级的编号与回执。")
    rep.append("")

    # --- 8 待办
    rep.append("## 待办补正动作")
    rep.append("")
    all_todo = list(todo)
    if core_missing:
        all_todo.append("补齐「问题描述 / 实物差异 / 已付金额」——这是出具任何结论的前提")
    if recv_d is None:
        all_todo.append("补齐收货日期，用于核算七天无理由期限")
    if not filled(pay):
        all_todo.append("确认支付方式是否经平台担保，这决定资金能否冻结")
    if gaps:
        all_todo.extend(gaps)
    if net is None:
        all_todo.append("补齐已付金额，否则无法测算应退")
    if yesno(get_text(f, "是否保留物流面单")) is False:
        all_todo.append("补齐物流面单与签收记录截图，用于证明收货时间与包裹来源")
    if yesno(admit) is False:
        all_todo.append("卖家否认问题：书面要求其说明依据，并通过平台介入提交完整证据链")
    if seven in ("有争议", "已超期"):
        all_todo.append("若主张七天无理由，需补充证明卖家属经营行为"
                        "（长期大量在售同类商品、有店铺或营业执照）")
    if yesno(complained) is False:
        all_todo.append("尚未投诉 12315：卖家属经营行为的可同步投诉，与平台介入并行推进")
    if not filled(demand):
        all_todo.append("明确诉求：全额退款 / 退货退款 / 赔偿差价 / 假货赔偿")
    if not all_todo:
        all_todo.append("信息已较完整，按升级路径逐级推进并保留每级回执")
    for i, t in enumerate(all_todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # --- 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见，最终以平台规则、"
               "市场监管部门及司法机关认定为准。")
    rep.append("- 二手闲置交易是否适用七天无理由在实践中存在争议，以平台规则与个案认定为准。")
    rep.append("- 是否构成假货，须以品牌官方或第三方鉴定结论为依据，不能凭主观判断。")
    rep.append("- 本技能不提供任何代办申诉、代写诉状服务。")

    return "\n".join(rep), verdict, crit + risk, all_todo


# ---------------------------------------------------------------- CLI


def main():
    ap = argparse.ArgumentParser(description="闲鱼二手交易纠纷取证与维权核查")
    ap.add_argument("md", nargs="?", default="样例.md", help="采集表 Markdown 路径")
    ap.add_argument("--input", dest="input", default=None, help="采集表路径（等价位置参数）")
    ap.add_argument("--base", default=None, help="基准日期 YYYY-MM-DD")
    ap.add_argument("--out", default="", help="报告输出路径")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    args = ap.parse_args()

    path = args.input or args.md
    base = parse_date(args.base) if args.base else date.today()

    if not path or not os.path.exists(path):
        msg = "采集表不存在：%s" % path
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2

    f = parse_md(path)
    if not f:
        msg = "采集表为空或格式无法解析，请用「| 字段 | 值 |」或「字段：值」格式填写"
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2

    report, verdict, risk, todo = build_report(f, base)

    if args.json:
        print(json.dumps({"结论": verdict, "风险项": risk, "待办": todo, "报告": report},
                         ensure_ascii=False, indent=2))
    else:
        print(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)

    if not filled(get_text(f, "问题描述")) and not filled(get_text(f, "实物与描述差异")) \
            and parse_num(get_text(f, "已付金额")) is None:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
