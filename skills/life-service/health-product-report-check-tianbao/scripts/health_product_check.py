# -*- coding: utf-8 -*-
"""保健品虚假宣传举报与退费核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段核查报告，含结论摘要、批准文号与产品身份、违法宣称识别、销售渠道与主体、
      退费测算与退货依据、证据清单、举报与维权路径、待办补正动作、边界与纪律。

退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

FIELD_ALIAS = {
    "产品名称": ["产品名称", "产品名", "商品名称", "买的是什么"],
    "批准文号": ["批准文号", "产品批准文号", "保健食品批准文号", "注册号", "备案号"],
    "是否查到批准文号": ["是否查到批准文号", "文号查询结果", "能否查到文号", "文号核验情况"],
    "包装是否标注警示语": ["包装是否标注警示语", "有无警示语", "是否标注本品不能代替药物", "警示语情况"],
    "保健功能声称": ["保健功能声称", "声称的保健功能", "功能声称", "宣传的保健功能"],
    "购买渠道": ["购买渠道", "销售渠道", "在哪买的", "购买方式"],
    "销售主体": ["销售主体", "销售方", "商家名称", "机构名称"],
    "是否签合同": ["是否签合同", "有无合同", "是否签约", "合同签订情况"],
    "购买日期": ["购买日期", "付款日期", "下单日期", "交易日期"],
    "购买数量": ["购买数量", "数量", "买了多少", "疗程数量"],
    "宣称适用人群": ["宣称适用人群", "适用人群", "针对人群", "受众"],
    "单价": ["单价", "单盒价格", "每盒价格", "产品单价"],
    "已付金额": ["已付金额", "已支付金额", "实付金额", "付款金额", "总花费"],
    "已退金额": ["已退金额", "已退款金额", "退款金额"],
    "是否开具发票": ["是否开具发票", "有无发票", "发票情况"],
    "收款主体": ["收款主体", "收款方", "收款单位", "打款给谁"],
    "宣传话术摘录": ["宣传话术摘录", "宣传话术", "宣传内容", "宣称内容", "广告语"],
    "是否有会销或讲座": ["是否有会销或讲座", "是否参加讲座", "有无会销", "会销情况"],
    "是否有专家义诊": ["是否有专家义诊", "有无义诊", "是否有专家", "义诊情况"],
    "是否针对老年人": ["是否针对老年人", "是否针对老人", "受众是否老年", "是否老年人购买"],
    "是否承诺无效退款": ["是否承诺无效退款", "有无无效退款承诺", "退款承诺"],
    "是否有代言或患者现身说法": ["是否有代言或患者现身说法", "有无代言", "是否有患者现身说法", "代言情况"],
    "服用后是否不适": ["服用后是否不适", "有无不适", "是否出现不适", "身体反应"],
    "不适描述": ["不适描述", "不适症状", "身体不适描述"],
    "是否已投诉": ["是否已投诉", "有无投诉", "投诉情况", "是否已举报"],
    "证据留存情况": ["证据留存情况", "证据情况", "有哪些证据", "留证情况", "已保存材料"],
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


def check_approval(f):
    """批准文号与产品身份：返回 (状态, 说明列表)。"""
    items = []
    name = get_text(f, "产品名称")
    no = get_text(f, "批准文号")
    found = yesno(get_text(f, "是否查到批准文号"))
    warn = yesno(get_text(f, "包装是否标注警示语"))
    func = get_text(f, "保健功能声称")

    items.append("产品名称：%s" % (name if filled(name) else "未填写"))
    items.append("批准文号：%s" % (no if filled(no) else "未填写"))

    if found is True:
        items.append("已在官方平台查到该批准文号，仍需核对：产品名称、保健功能、生产企业"
                     "三项是否与包装完全一致")
        status = "通过"
        if warn is False:
            items.append("包装未标注「保健食品不是药物，不能代替药物治疗疾病」警示语，"
                         "不符合标签要求")
            status = "有风险"
    elif found is False:
        items.append("**官方平台查不到该批准文号**：该产品可能根本不是保健食品，"
                     "而是普通食品甚至三无产品，按保健食品销售属冒用或虚假标识")
        status = "不通过"
    else:
        items.append("未填写文号查询结果，**产品身份无法确认**")
        status = "待补正"

    if not filled(no):
        items.append("未填写批准文号：无法核验产品身份，应立即从包装上抄录完整文号")
        if status == "通过":
            status = "待补正"
    if filled(func):
        items.append("声称的保健功能：%s" % func)
        items.append("注意：经批准的表述是「辅助降血脂」这类，宣传成「降血脂」即属越界")
    return status, items


def check_claims(f):
    """违法宣称识别：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    promo = get_text(f, "宣传话术摘录")
    func = get_text(f, "保健功能声称")
    endorse = yesno(get_text(f, "是否有代言或患者现身说法"))
    guarantee = yesno(get_text(f, "是否承诺无效退款"))
    blob = norm(" ".join([promo, func]))

    if filled(promo):
        items.append("宣传话术摘录：%s" % str(promo)[:120])
    else:
        risk.append("未填写宣传话术摘录，**无法判断是否存在违法宣称**")

    disease = ("降血压", "降血糖", "降三高", "治", "根治", "治愈", "包治",
               "抗癌", "防癌", "不用吃药", "不用打针", "停药", "代替药物", "能治病",
               "治疗", "缓解病症", "消除病灶")
    hits = [k for k in disease if k in blob and ("辅助" + k) not in blob]
    if hits:
        crit.append("宣称疾病治疗功能（命中：%s）：违反《食品安全法》"
                    "关于保健食品不得涉及疾病预防、治疗功能的规定，"
                    "以及《广告法》第十八条关于保健食品广告不得涉及疾病预防、治疗功能的规定"
                    % "、".join(hits[:5]))
    assert_kw = ("绝对有效", "无副作用", "百分之百", "100%", "保证有效", "完全安全", "零风险")
    hits2 = [k for k in assert_kw if k in blob]
    if hits2:
        crit.append("对功效或安全性作断言保证（命中：%s）："
                    "《广告法》第十八条禁止保健食品广告表示功效、安全性的断言或者保证"
                    % "、".join(hits2[:5]))
    need_kw = ("必须吃", "不吃就", "人人都", "保障健康所必需", "必需品")
    hits3 = [k for k in need_kw if k in blob]
    if hits3:
        crit.append("暗示商品为保障健康所必需（命中：%s）：属《广告法》第十八条禁止情形"
                    % "、".join(hits3[:5]))
    med_kw = ("疗效", "治愈率", "处方", "主治", "疗程", "临床验证")
    hits4 = [k for k in med_kw if k in blob]
    if hits4:
        risk.append("使用医疗用语（命中：%s）：易使消费者误认为是药品" % "、".join(hits4[:5]))

    if endorse is True:
        crit.append("利用代言人或患者现身说法作推荐证明：《广告法》第十八条明文禁止")
    elif endorse is None:
        items.append("未填写是否有代言或患者现身说法")
    if guarantee is True:
        risk.append("承诺「无效退款」：属对功效的断言保证，且常伴随后续拒退")
    return crit, risk, items


def check_channel(f):
    """销售渠道与主体：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    ch = get_text(f, "购买渠道")
    seller = get_text(f, "销售主体")
    payee = get_text(f, "收款主体")
    signed = yesno(get_text(f, "是否签合同"))
    invoice = yesno(get_text(f, "是否开具发票"))
    seminar = yesno(get_text(f, "是否有会销或讲座"))
    clinic = yesno(get_text(f, "是否有专家义诊"))
    elder = yesno(get_text(f, "是否针对老年人"))
    n_ch = norm(ch)

    items.append("购买渠道：%s" % (ch if filled(ch) else "未填写"))
    items.append("销售主体：%s" % (seller if filled(seller) else "未填写"))

    if not filled(ch):
        items.append("未填写购买渠道，**取证重点无法确定**")
    elif any(k in n_ch for k in ("会销", "讲座", "听课", "会场")):
        crit.append("会销/讲座渠道：针对特定人群集中营销，常伴随夸大宣传与冲动消费，"
                    "取证重点是现场录音录像与宣传单")
    elif any(k in n_ch for k in ("直播", "短视频", "主播")):
        risk.append("直播渠道：主播口播往往不在商品详情页，必须**当场录屏**才能固定，"
                    "直播结束后回放常被删除")
    elif any(k in n_ch for k in ("微商", "微信", "私域", "朋友圈")):
        risk.append("微商/私域渠道：核心证据是聊天记录里的功效承诺，"
                    "建议用文字提问让对方以文字回复")
    elif any(k in n_ch for k in ("门店", "药店", "实体")):
        items.append("门店渠道：留证重点是店内海报、店员话术录音与购物小票")
    elif any(k in n_ch for k in ("电视", "购物频道")):
        items.append("电视购物渠道：留证重点是节目录像、播出时间与订购单")

    if seminar is True:
        crit.append("存在会销或讲座场景：属高风险营销方式，是市场监管与公安的查处重点")
    if clinic is True:
        crit.append("存在「专家义诊」：以免费检查制造健康焦虑后推销，典型违规营销手法")
    if elder is True:
        risk.append("针对老年人营销：属重点监管情形，举报时应明确说明受众特征")
    if signed is False:
        risk.append("未签任何书面合同：权利义务无载体，退费主张难度上升")
    if invoice is False:
        risk.append("未开具发票：既是税务违规线索，也导致购买事实举证困难")
    if filled(payee) and filled(seller) and norm(payee) != norm(seller):
        risk.append("收款主体「%s」与销售主体「%s」不一致，出事后易互相推诿" % (payee, seller))
    elif not filled(payee):
        risk.append("未填写收款主体，需核对付款凭证上的收款方名称")
    return crit, risk, items


def calc_refund(f, fraud):
    """退费测算：返回 (金额或 None, 说明列表)。"""
    items = []
    paid = parse_num(get_text(f, "已付金额"))
    back = parse_num(get_text(f, "已退金额")) or 0.0
    cnt = parse_num(get_text(f, "购买数量"))
    unit = parse_num(get_text(f, "单价"))

    if paid is None:
        return None, ["未填写已付金额，**应退无法测算**"]
    net = paid - back
    items.append("已付 %s − 已退 %s = 未退 %s" % (money(paid), money(back), money(net)))
    if cnt is not None and unit is not None:
        items.append("购买 %s 份 × 单价 %s = 理论总额 %s，与已付 %s 请核对是否一致" %
                     (fmt_num(cnt), money(unit), money(round(cnt * unit, 2)), money(paid)))
    if fraud:
        items.append("**构成欺诈的**：可依《消费者权益保护法》第五十五条"
                     "主张增加赔偿，金额为购买价款的三倍，不足五百元的为五百元")
        items.append("参考可主张总额（退一赔三）：%s" % money(round(paid * 4, 2)))
    else:
        items.append("未认定欺诈的，一般按未开封、未食用部分协商退货退款")
    return net, items


def check_harm(f):
    """身体损害：返回 (高危项, 说明列表)。"""
    crit = []
    items = []
    bad = yesno(get_text(f, "服用后是否不适"))
    desc = get_text(f, "不适描述")
    if bad is True:
        crit.append("服用后出现不适：**先就医**，并在就诊时说明服用过该产品，"
                    "诊疗记录是后续举报与索赔的关键证据")
        if filled(desc):
            items.append("不适描述：%s" % str(desc)[:100])
    elif bad is False:
        items.append("未申报服用后不适")
    else:
        items.append("未填写服用后是否不适")
    return crit, items


def check_evidence(f):
    ev = norm(get_text(f, "证据留存情况"))
    need = [
        ("产品外包装与标签照片", ("包装", "标签", "照片", "外包装")),
        ("官方文号查询截图", ("查询", "截图", "官网", "平台")),
        ("宣传单/说明书/海报", ("宣传", "说明书", "海报", "单页", "手册")),
        ("直播录屏或现场录音", ("录屏", "录音", "录像", "直播")),
        ("聊天记录完整导出", ("聊天", "微信", "沟通", "记录")),
        ("付款凭证与发票", ("付款", "发票", "收据", "转账", "凭证")),
    ]
    if not ev:
        return [], [n for n, _ in need]
    have = []
    miss = []
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

    name = get_text(f, "产品名称")
    promo = get_text(f, "宣传话术摘录")
    paid_n = parse_num(get_text(f, "已付金额"))
    demand = get_text(f, "诉求")

    ap_status, ap_items = check_approval(f)
    c_crit, c_risk, c_items = check_claims(f)
    ch_crit, ch_risk, ch_items = check_channel(f)
    h_crit, h_items = check_harm(f)
    have_ev, miss_ev = check_evidence(f)

    core_missing = not filled(name) and not filled(promo) and paid_n is None
    fraud = False
    if not core_missing:
        crit.extend(c_crit)
        crit.extend(ch_crit)
        crit.extend(h_crit)
        risk.extend(c_risk)
        risk.extend(ch_risk)
        if ap_status == "不通过":
            crit.append("批准文号核查不通过：产品身份存疑，按保健食品销售涉嫌虚假标识")
        elif ap_status == "待补正":
            risk.append("批准文号未核验，产品身份未定")
        if miss_ev:
            risk.append("证据缺失 %d 项：%s" % (len(miss_ev), "、".join(miss_ev[:3])))
        fraud = bool(c_crit) or ap_status == "不通过"

    if core_missing:
        verdict = "待补正"
    elif crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"

    net, refund_items = calc_refund(f, fraud)

    # 1 结论摘要
    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 产品：%s" % (name if filled(name) else "未填写"))
    rep.append("- 批准文号核查：%s" % ap_status)
    rep.append("- 已付金额：%s" % (money(paid_n) if paid_n is not None else "未填写"))
    rep.append("- 违法宣称命中 %d 项 / 风险项 %d 项" % (len(c_crit), len(ch_crit) + len(c_risk) + len(ch_risk)))
    rep.append("- 是否可按欺诈主张：%s" % ("是" if fraud else "否"))
    rep.append("- 参考应退：%s" % (money(round(net, 2)) if net is not None else "无法测算"))
    rep.append("- 高危项 %d 项 / 风险项 %d 项" % (len(crit), len(risk)))
    rep.append("- **总体结论：%s**" % verdict)
    rep.append("")

    # 2 批准文号
    rep.append("## 批准文号与产品身份核查")
    rep.append("")
    for it in ap_items:
        rep.append("- %s" % it)
    rep.append("- 查询入口：国家市场监督管理总局「特殊食品信息查询平台」；"
               "核对产品名称、保健功能、生产企业三项")
    rep.append("")

    # 3 违法宣称
    rep.append("## 违法宣称识别")
    rep.append("")
    for it in c_items:
        rep.append("- %s" % it)
    for c in c_crit:
        rep.append("- **%s**" % c)
    for r in c_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 4 渠道与主体
    rep.append("## 销售渠道与主体核查")
    rep.append("")
    for it in ch_items:
        rep.append("- %s" % it)
    for c in ch_crit:
        rep.append("- **%s**" % c)
    for r in ch_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 5 退费
    rep.append("## 退费测算与退货依据")
    rep.append("")
    for it in refund_items:
        rep.append("- %s" % it)
    rep.append("- 七天无理由：网购情形可依《消费者权益保护法》第二十五条主张，"
               "以收货起七日为限；线下会销购买的一般不适用，但欺诈情形不受此限")
    rep.append("")

    # 6 证据
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
        rep.append("- 主要证据类别已覆盖，仍需确认原始载体完整")
    rep.append("")
    rep.append("固定要点：直播口播必须**当场录屏**；会销现场尽量录音并带走宣传单；"
               "官方文号查询结果要截图并注明查询日期。")
    rep.append("")

    # 7 举报路径
    rep.append("## 举报与维权路径")
    rep.append("")
    rep.append("| 情形 | 向谁举报 | 说明什么 |")
    rep.append("| --- | --- | --- |")
    rep.append("| 虚假宣传、违法宣称 | 12315 / 市场监管部门 | 产品名、文号、宣传原话、渠道、金额 |")
    rep.append("| 无批准文号、冒用文号 | 市场监管部门 | 附官方查询截图 |")
    rep.append("| 会销欺诈、针对老年人大额推销 | 市场监管部门 + 公安 | 涉诈骗的报警 |")
    rep.append("| 服用后身体损害 | 市场监管部门 + 公安 | 附诊疗记录与剩余产品 |")
    rep.append("| 直播平台不作为 | 平台投诉 + 12315 | 附录屏与订单号 |")
    rep.append("")
    rep.append("举报话术要点：说清「什么产品、什么文号、谁在卖、在哪卖、"
               "宣称了什么原话、付了多少钱」，并附截图与凭证。")
    if yesno(get_text(f, "是否已投诉")) is True:
        rep.append("- 已投诉/举报，请保留受理编号与处理结果")
    else:
        rep.append("- 尚未投诉：先补齐文号查询截图与宣传材料，再提交举报，材料一次交齐效率最高")
    rep.append("")

    # 8 待办
    rep.append("## 待办补正动作")
    rep.append("")
    if core_missing:
        todo.append("补齐「产品名称」「宣传话术摘录」「已付金额」——这是出具结论的前提")
    if ap_status != "通过":
        todo.append("到国家市场监督管理总局特殊食品信息查询平台核验批准文号，"
                    "查不到也要截图并注明查询日期")
    if not filled(get_text(f, "宣传话术摘录")):
        todo.append("补齐宣传原话——逐字记录，不要用概括的话")
    if not filled(get_text(f, "购买渠道")):
        todo.append("确认购买渠道，不同渠道的取证重点不同")
    for m in miss_ev:
        todo.append("补齐证据：%s" % m)
    if yesno(get_text(f, "服用后是否不适")) is True:
        todo.append("立即就医并在就诊时说明服用过该产品，保留诊疗记录")
    if not filled(demand):
        todo.append("明确诉求：全额退款 / 退一赔三 / 举报查处 / 赔偿身体损害")
    todo.append("书面提出退费要求并留送达凭证，口头交涉不留痕")
    for i, t in enumerate(todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见与医学判断，"
               "最终以市场监管部门及司法机关认定为准。")
    rep.append("- 批准文号的唯一权威来源是官方查询平台，本技能不代替官方核验。")
    rep.append("- 是否构成欺诈与违法宣称，最终以主管部门认定为准。")
    rep.append("- 涉及身体损害的应立即就医并保留诊疗记录；本技能不评价产品功效。")

    return "\n".join(rep), verdict, crit + risk, todo


def main():
    ap = argparse.ArgumentParser(description="保健品虚假宣传举报与退费核查")
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

    if not filled(get_text(f, "产品名称")) and not filled(get_text(f, "宣传话术摘录")) \
            and parse_num(get_text(f, "已付金额")) is None:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
