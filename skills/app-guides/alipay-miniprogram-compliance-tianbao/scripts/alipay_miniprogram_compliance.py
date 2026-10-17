# -*- coding: utf-8 -*-
"""支付宝小程序开发合规核查脚本（类目资质 / 支付与虚拟商品 / 隐私 / 内容安全 / 营销 / 违规处罚向）。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、类目资质与备案、支付与虚拟商品、隐私与数据、
      内容安全、营销与诱导、违规处罚与整改指引、边界。

只做合规核查与整改指引，不替代监管规定、支付宝平台规则与正式法律意见。
退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

FIELD_ALIAS = {
    "account": ["小程序名称", "应用名称", "支付宝小程序", "名称", "账号名称"],
    "subject": ["主体类型", "小程序主体", "账号主体", "主体", "开发者类型"],
    "category_set": ["是否完成小程序类目设置", "类目设置", "经营类目", "小程序类目", "类目"],
    "category_match": ["类目与经营范围是否匹配", "类目匹配", "类目一致性", "类目与执照"],
    "special_cat": ["是否涉及特殊类目资质(医疗/金融/食品/教育等)", "特殊类目", "需资质类目",
                   "医疗/金融/食品", "特许类目"],
    "special_license": ["特殊类目是否具备相应资质", "类目资质", "特殊资质", "经营许可", "特许资质"],
    "icp_filed": ["是否完成小程序备案与主体认证", "小程序备案", "备案", "主体认证", "ICP备案"],
    "pay_connected": ["是否接入支付", "支付接入", "小程序支付", "当面付", "支付功能"],
    "virtual_goods": ["是否售卖虚拟商品或会员", "虚拟商品", "虚拟支付", "会员", "虚拟权益"],
    "virtual_compliant": ["虚拟商品售卖是否合规", "虚拟商品合规", "虚拟售卖规范"],
    "order_funds": ["订单与资金是否合规", "资金合规", "订单合规", "资金结算", "对公结算"],
    "privacy_policy": ["是否有隐私协议", "隐私协议", "隐私政策", "隐私声明"],
    "user_auth": ["用户授权是否合规", "用户授权", "授权获取", "获取用户信息", "授权弹窗"],
    "sdk_declare": ["第三方SDK是否申报", "SDK申报", "信息共享", "第三方SDK", "SDK清单"],
    "sensitive_info": ["敏感信息是否规范处理", "敏感信息", "敏感个人信息", "个人信息保护"],
    "content_review": ["是否有内容审核机制", "内容审核", "先审后发", "内容机审"],
    "ugc": ["是否含UGC内容", "UGC", "用户生成内容", "用户发布"],
    "ugc_handle": ["UGC是否有举报与处置机制", "UGC处置", "举报入口", "违规处置", "下架处置"],
    "induce": ["是否有诱导分享或关注", "诱导分享", "诱导关注", "裂变", "诱导下载"],
    "false_ad": ["是否有虚假宣传或违规广告", "虚假宣传", "违规广告", "夸大宣传", "极限词"],
    "promo": ["红包优惠券营销是否合规", "红包", "优惠券", "营销合规", "活动合规"],
    "violation": ["是否有违规或处罚历史", "违规历史", "处罚历史", "被处罚", "下架记录"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "未确认", "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法", "没")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "可以", "做过", "完成")


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


def parse_md(path):
    data = {}
    if not path or not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
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
            if norm(key_raw) in ("字段", "field", "项目"):
                continue
            val = " ".join(c.strip() for c in cells[1:]).strip()
            if val:
                data[norm(key_raw)] = val
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, maxsplit=1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    aliases = sorted(FIELD_ALIAS.get(key, [key]), key=len, reverse=True)
    idx = {}
    for k, v in f.items():
        idx.setdefault(norm(k), v)
    for a in aliases:
        na = norm(a)
        if not na:
            continue
        if na in idx and filled(idx[na]):
            return idx[na]
    return ""


def yesno(text):
    if not filled(text):
        return None
    n = norm(text)
    for w in NEG_WORDS:
        if n.startswith(w):
            return False
    for w in POS_WORDS:
        if n.startswith(w):
            return True
    return None


def check_category(f):
    """类目资质与备案核查。"""
    items, crit, risk = [], [], []
    cs = yesno(get_text(f, "category_set"))
    if cs is False:
        crit.append("未完成小程序类目设置：支付宝小程序须按实际经营内容设置类目，"
                    "未设置或类目不符会被限制功能、下架甚至封禁，须在开发者后台如实配置")
        items.append("- 类目设置：未完成（阻断）")
    elif cs is True:
        items.append("- 类目设置：已完成")
    else:
        risk.append("未确认是否完成类目设置：支付宝小程序须按实际经营内容如实设置类目，请尽快配置")
        items.append("- 类目设置：未确认（风险）")

    cm = yesno(get_text(f, "category_match"))
    if cm is False:
        crit.append("类目与经营范围不匹配：小程序经营类目须与营业执照经营范围一致，"
                    "超范围经营须先增补经营范围或调整业务，否则属违规经营")
        items.append("- 类目与经营范围匹配：不匹配（阻断）")
    elif cm is True:
        items.append("- 类目与经营范围匹配：匹配")
    else:
        items.append("- 类目与经营范围匹配：未确认")

    sc = yesno(get_text(f, "special_cat"))
    if sc is True:
        sl = yesno(get_text(f, "special_license"))
        if sl is False:
            crit.append("涉及特殊类目（医疗/金融/食品/教育/医疗美容等）但无相应资质："
                        "此类类目须取得对应审批与经营许可，无资质不得经营，平台会拒登并处罚")
            items.append("- 特殊类目资质：涉及且无资质（阻断）")
        elif sl is True:
            items.append("- 特殊类目资质：涉及且具备资质")
        else:
            crit.append("涉及特殊类目但未确认资质：医疗/金融/食品/教育等类目须持相应审批与许可，"
                        "请确认已取得，否则不得经营")
            items.append("- 特殊类目资质：涉及且未确认资质（阻断）")
    elif sc is False:
        items.append("- 特殊类目资质：不涉及")
    else:
        items.append("- 特殊类目资质：未确认")

    icp = yesno(get_text(f, "icp_filed"))
    if icp is False:
        crit.append("未完成小程序备案/主体认证：支付宝小程序须完成主体认证与（按监管要求的）小程序备案，"
                    "未备案/未认证会被限制发布与部分能力，须先完成")
        items.append("- 小程序备案/主体认证：未完成（阻断）")
    elif icp is True:
        items.append("- 小程序备案/主体认证：已完成")
    else:
        risk.append("未确认是否完成备案/主体认证：支付宝小程序须完成主体认证与备案，请尽快落实")
        items.append("- 小程序备案/主体认证：未确认（风险）")
    return items, crit, risk


def check_payment(f):
    """支付与虚拟商品核查。"""
    items, crit, risk = [], [], []
    pay = yesno(get_text(f, "pay_connected"))
    if pay is True:
        items.append("- 支付接入：已接入")
    elif pay is False:
        items.append("- 支付接入：未接入（无交易则跳过支付相关）")
    else:
        items.append("- 支付接入：未确认")

    vg = yesno(get_text(f, "virtual_goods"))
    if vg is False:
        items.append("- 虚拟商品/会员：未售卖")
    else:
        vc = yesno(get_text(f, "virtual_compliant"))
        if vc is False:
            crit.append("售卖虚拟商品/会员不合规：支付宝对虚拟商品/会员售卖有专门规范，"
                        "须明示商品内容、价格、有效期与退款规则，不得虚假承诺或设置不合理退款门槛，"
                        "否则会被限制交易能力并引发投诉")
            items.append("- 虚拟商品售卖合规：不合规（阻断）")
        elif vc is True:
            items.append("- 虚拟商品售卖合规：合规（已明示内容/价格/有效期/退款规则）")
        else:
            risk.append("未确认虚拟商品售卖是否合规：售卖虚拟商品/会员须明示内容、价格、有效期与退款规则，"
                        "不得虚假承诺或不合理退款门槛，请自查")
            items.append("- 虚拟商品售卖合规：未确认（风险）")

    of = yesno(get_text(f, "order_funds"))
    if of is False:
        risk.append("订单与资金不合规：交易资金须通过支付宝合规结算通道入账到对公/个体户结算账户，"
                    "不得诱导场外交易（私下转账/加微信付款），避免二清与资金风险")
        items.append("- 订单与资金合规：不合规（风险）")
    elif of is True:
        items.append("- 订单与资金合规：合规")
    else:
        items.append("- 订单与资金合规：未确认")
    return items, crit, risk


def check_privacy(f):
    """隐私与数据合规核查。"""
    items, crit, risk = [], [], []
    pp = yesno(get_text(f, "privacy_policy"))
    if pp is False:
        crit.append("无隐私协议：支付宝小程序须提供隐私协议/政策，告知个人信息收集使用规则，"
                    "缺失会被限制相关能力并违反《个人信息保护法》")
        items.append("- 隐私协议：缺失（阻断）")
    elif pp is True:
        items.append("- 隐私协议：已提供")
    else:
        risk.append("未确认是否有隐私协议：须提供隐私协议并告知个人信息收集使用规则")
        items.append("- 隐私协议：未确认（风险）")

    ua = yesno(get_text(f, "user_auth"))
    if ua is False:
        crit.append("用户授权不合规：获取用户信息（授权登录/手机号/地理位置等）须先告知并取得用户授权，"
                    "不得默认勾选或强制过度授权，拒绝后应保障基础功能可用")
        items.append("- 用户授权合规：不合规（阻断）")
    elif ua is True:
        items.append("- 用户授权合规：合规")
    else:
        risk.append("未确认用户授权是否合规：获取用户信息须先告知并取得授权，不得默认勾选/过度授权")
        items.append("- 用户授权合规：未确认（风险）")

    sd = yesno(get_text(f, "sdk_declare"))
    if sd is False:
        risk.append("第三方 SDK 未申报：使用第三方 SDK 须在后台申报/说明信息共享情况，"
                    "未申报会被要求整改并可能下架")
        items.append("- 第三方 SDK 申报：未申报（风险）")
    elif sd is True:
        items.append("- 第三方 SDK 申报：已申报")
    else:
        items.append("- 第三方 SDK 申报：未确认")

    si = yesno(get_text(f, "sensitive_info"))
    if si is False:
        crit.append("敏感信息处理不规范：处理敏感个人信息须取得单独同意、最小必要并加密存储，"
                    "不得超范围收集或明文传输，违反《个人信息保护法》")
        items.append("- 敏感信息处理：不规范（阻断）")
    elif si is True:
        items.append("- 敏感信息处理：规范")
    else:
        risk.append("未确认敏感信息是否规范处理：敏感个人信息须单独同意、最小必要、加密存储")
        items.append("- 敏感信息处理：未确认（风险）")
    return items, crit, risk


def check_content(f):
    """内容安全核查。"""
    items, crit, risk = [], [], []
    cr = yesno(get_text(f, "content_review"))
    if cr is False:
        risk.append("无内容审核机制：小程序含发布/展示内容应建立机审+人审机制，过滤违禁内容，"
                    "否则违规内容传播将承担责任")
        items.append("- 内容审核机制：无（风险）")
    elif cr is True:
        items.append("- 内容审核机制：已建立")
    else:
        risk.append("未确认是否有内容审核机制：建议建立机审+人审过滤违禁内容")
        items.append("- 内容审核机制：未确认（风险）")

    ugc = yesno(get_text(f, "ugc"))
    if ugc is True:
        uh = yesno(get_text(f, "ugc_handle"))
        if uh is False:
            crit.append("含 UGC 但无举报与处置机制：用户生成内容须提供举报入口、违规下架处置并留存记录，"
                        "平台要求运营者对 UGC 负责，缺失会被处罚")
            items.append("- UGC 举报与处置：无（阻断）")
        elif uh is True:
            items.append("- UGC 举报与处置：已建立")
        else:
            crit.append("含 UGC 但未确认举报与处置机制：须提供举报入口、违规下架处置并留存记录")
            items.append("- UGC 举报与处置：未确认（阻断）")
    elif ugc is False:
        items.append("- UGC 内容：不含")
    else:
        items.append("- UGC 内容：未确认")
    return items, crit, risk


def check_marketing(f):
    """营销与诱导核查。"""
    items, crit, risk = [], [], []
    ind = yesno(get_text(f, "induce"))
    if ind is True:
        crit.append("存在诱导分享/关注/下载：以奖励利诱用户分享、关注、下载或跳转外部，"
                    "触碰平台诱导分享红线，触发即可能封禁分享接口、下架乃至封号")
        items.append("- 诱导分享/关注/下载：存在（阻断）")
    elif ind is False:
        items.append("- 诱导分享/关注/下载：不存在")
    else:
        risk.append("未确认是否存在诱导分享/关注：不得以奖励利诱分享、关注、下载或跳转外部")
        items.append("- 诱导分享/关注/下载：未确认（风险）")

    fa = yesno(get_text(f, "false_ad"))
    if fa is True:
        crit.append("存在虚假宣传/违规广告（含极限词）：违反《广告法》与平台规则，面临处罚，"
                    "须删除夸大表述并整改文案")
        items.append("- 虚假宣传/违规广告：存在（阻断）")
    elif fa is False:
        items.append("- 虚假宣传/违规广告：不存在")
    else:
        risk.append("未确认是否有虚假宣传/违规广告：文案不得含「最/第一/国家级」等极限词与夸大表述")
        items.append("- 虚假宣传/违规广告：未确认（风险）")

    pr = yesno(get_text(f, "promo"))
    if pr is False:
        risk.append("红包/优惠券营销不合规：营销活动须明示规则、有效期、使用门槛与限制，"
                        "不得虚假优惠或设置陷阱条款，避免纠纷与投诉")
        items.append("- 红包/优惠券营销合规：不合规（风险）")
    elif pr is True:
        items.append("- 红包/优惠券营销合规：合规")
    else:
        items.append("- 红包/优惠券营销合规：未确认")
    return items, crit, risk


def check_violation(f):
    """违规处罚与历史核查。"""
    items, crit, risk = [], [], []
    v = yesno(get_text(f, "violation"))
    if v is True:
        risk.append("存在违规/处罚历史（如被警告、限流、下架、封禁）：须完成整改闭环并留存证据，"
                    "再次违规将加重处罚，建议全量复查类目、支付、隐私、内容、营销后再提交审核")
        items.append("- 违规/处罚历史：有（风险）")
    elif v is False:
        items.append("- 违规/处罚历史：无")
    else:
        items.append("- 违规/处罚历史：未确认")
    return items, crit, risk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="")
    args = ap.parse_args()
    f = parse_md(args.path)
    if not f or not any(filled(v) for v in f.values()):
        print("# 待补正\n\n未读取到任何有效字段，请填写采集表后再核查。\n\n**待补正**")
        return 2

    crit, risk, sections = [], [], []
    acc = get_text(f, "account")
    subj = get_text(f, "subject")

    header = "# 支付宝小程序开发合规核查报告"
    if filled(acc):
        header += "（%s）" % acc
    sections.append(header)
    sections.append("")

    c_items, c_c, c_r = check_category(f)
    crit += c_c; risk += c_r
    p_items, p_c, p_r = check_payment(f)
    crit += p_c; risk += p_r
    pr_items, pr_c, pr_r = check_privacy(f)
    crit += pr_c; risk += pr_r
    ct_items, ct_c, ct_r = check_content(f)
    crit += ct_c; risk += ct_r
    m_items, m_c, m_r = check_marketing(f)
    crit += m_c; risk += m_r
    v_items, v_c, v_r = check_violation(f)
    crit += v_c; risk += v_r

    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"
    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险与待办项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(acc):
        summary += "- 小程序名称：%s\n" % acc
    if filled(subj):
        summary += "- 主体类型：%s\n" % subj
    summary += ("- 处置建议：先补齐类目设置、类目与经营范围匹配、特殊类目资质、备案/主体认证等准入阻断，"
                "再处理支付与虚拟商品合规、隐私协议与授权、SDK 申报、敏感信息处理，"
                "最后建立内容审核/UGC 处置并清除诱导分享与虚假宣传。\n")
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 类目资质与备案核查\n" + "\n".join(c_items) + "\n\n"
    body += "### 支付与虚拟商品核查\n" + "\n".join(p_items) + "\n\n"
    body += "### 隐私与数据合规核查\n" + "\n".join(pr_items) + "\n\n"
    body += "### 内容安全核查\n" + "\n".join(ct_items) + "\n\n"
    body += "### 营销与诱导核查\n" + "\n".join(m_items) + "\n\n"
    body += "### 违规处罚与历史核查\n" + "\n".join(v_items) + "\n"
    sections.append(body)

    rb = "## 三、阻断项与风险/待办\n\n"
    if crit:
        rb += "### 阻断项（必须处理，否则限制能力/下架/封禁）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险/待办项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "各核查项均满足，建议提交审核前再做一次全量自查并留存记录。\n\n"
    sections.append(rb)

    adv = ("## 四、整改操作指引（支付宝小程序合规清单）\n\n"
           "1. 类目与备案：按实际经营内容如实设置类目，确保类目与营业执照经营范围一致；"
           "完成主体认证与（监管要求的）小程序备案；特殊类目（医疗/金融/食品/教育等）先取得资质再经营。\n"
           "2. 支付与虚拟商品：支付走支付宝合规通道；售卖虚拟商品/会员须明示内容、价格、有效期与退款规则，"
           "资金结算到对公/个体户账户，严禁诱导场外交易。\n"
           "3. 隐私与数据：提供隐私协议；获取用户信息先告知并取得授权、拒绝后基础功能可用、不过度授权；"
           "第三方 SDK 申报；敏感个人信息单独同意、最小必要、加密存储（与隐私合规核查联动）。\n"
           "4. 内容安全：建立机审+人审过滤违禁内容；含 UGC 须提供举报入口、违规下架处置并留存记录。\n"
           "5. 营销合规：不诱导分享/关注/下载；文案禁用极限词与夸大表述；红包/优惠券活动明示规则与限制。\n"
           "6. 违规整改：有处罚历史的完成整改闭环并留存证据，再次提交审核前全量复查。\n\n")
    sections.append(adv)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据《个人信息保护法》《广告法》及支付宝小程序平台规则公开规则整理，"
                "**不替代监管规定、平台规则与正式法律意见**，重大场景请咨询律师。\n"
                "- 类目须与经营范围一致，特殊类目须持资质；未备案/未认证会被限制能力。\n"
                "- 虚拟商品售卖须明示规则，资金须合规结算，严禁场外交易与二清。\n"
                "- 隐私协议、用户授权、SDK 申报、敏感信息处理缺一不可；UGC 须有举报处置；不得诱导分享或虚假宣传。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
