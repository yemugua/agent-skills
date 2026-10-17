# -*- coding: utf-8 -*-
"""小程序微信虚拟支付（xpay）接入避坑与合规核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、前置条件、接入流程节点、配置核查、回调与发货核查、
      常见报错与驳回、合规要点、下一步、边界。

只做接入核查与避坑指引，不替代微信支付/xpay 官方文档与审核结论。
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
    "主体类型": ["主体类型", "小程序主体", "账号主体", "主体"],
    "小程序是否已认证": ["小程序是否已认证", "是否认证", "小程序认证", "认证状态"],
    "是否已开通微信虚拟支付(xpay)": ["是否已开通微信虚拟支付", "是否开通xpay", "xpay开通",
                                   "虚拟支付开通", "是否已开通虚拟支付"],
    "是否持有微信支付商户号": ["是否持有微信支付商户号", "有无商户号", "微信支付商户号",
                             "商户号", "是否开通过微信支付"],
    "虚拟商品类型": ["虚拟商品类型", "商品类型", "售卖内容", "商品形态", "卖什么"],
    "是否涉及iOS独立App": ["是否涉及iOS独立App", "是否有iOS App", "上架App Store",
                           "iOS App", "独立iOS应用"],
    "offer_id是否配置": ["offer_id是否配置", "offerid配置", "offer id", "offer_id",
                         "应用id是否配置"],
    "product_id是否配置": ["product_id是否配置", "productid配置", "product id", "product_id",
                           "产品id是否配置"],
    "商品价格(分)": ["商品价格(分)", "价格", "商品价格", "金额", "goods_price"],
    "是否已配置发货回调": ["是否已配置发货回调", "发货回调", "回调配置", "消息推送回调",
                           "paycallback"],
    "回调是否幂等防重复发货": ["回调是否幂等防重复发货", "幂等", "防重复发货", "回调幂等"],
    "是否有订单补发机制": ["是否有订单补发机制", "补发机制", "补发", "掉单补发"],
    "是否已联调下单与支付": ["是否已联调下单与支付", "联调", "下单支付联调", "支付联调"],
    "是否声明虚拟商品不支持退款": ["是否声明虚拟商品不支持退款", "退款声明", "不退声明",
                                 "虚拟商品退款"],
    "是否做未成年人保护": ["是否做未成年人保护", "未成年", "青少年模式", "未成年人"],
    "当前接入阶段": ["当前接入阶段", "接入阶段", "进度", "接入状态", "开发阶段"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

IOS_APP_WORDS = ("ios app", "ios独立", "独立ios", "appstore", "app store", "上架苹果",
                 "苹果商店", "独立app", "独立应用")

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


def unknown(v):
    return not filled(v)


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


def parse_num(text):
    if unknown(text):
        return None
    m = re.search(r"-?\d+(\.\d+)?", str(text))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def classify_subject(text):
    if unknown(text):
        return None
    n = norm(text)
    if any(k in n for k in ("企业", "公司")):
        return "enterprise"
    if any(k in n for k in ("个体", "工商户", "个体户")):
        return "individual"
    if any(k in n for k in ("个人", "自然人")):
        return "personal"
    return "other"


def check_prereq(f):
    items = []
    crit = []
    risk = []
    subj = classify_subject(get_text(f, "主体类型"))
    items.append("- 主体类型：%s" % (get_text(f, "主体类型") if filled(get_text(f, "主体类型")) else "未填"))

    if subj == "personal":
        crit.append("个人主体无法开通微信虚拟支付（xpay）：虚拟支付要求已认证的企业或个体工商户小程序，"
                    "请先将小程序主体升级为企业/个体工商户并完成认证")
        items.append("- 主体资质：个人主体（阻断）")
    elif subj in ("enterprise", "individual"):
        items.append("- 主体资质：企业/个体工商户（满足虚拟支付主体要求）")
    else:
        risk.append("未确认主体类型：虚拟支付要求企业或个体工商户主体，请先确认并完成认证")
        items.append("- 主体资质：未确认（风险）")

    auth = yesno(get_text(f, "小程序是否已认证"))
    if auth is False:
        crit.append("小程序尚未完成微信认证：虚拟支付开通须以已认证小程序为前提，请先完成认证")
        items.append("- 小程序认证：否（阻断）")
    elif auth is True:
        items.append("- 小程序认证：是")
    else:
        risk.append("未确认小程序是否认证：虚拟支付须已认证小程序，请确认")
        items.append("- 小程序认证：未确认（风险）")

    # 关键区分：xpay 虚拟支付 ≠ 微信支付商户号
    mch = yesno(get_text(f, "是否持有微信支付商户号"))
    xpay = yesno(get_text(f, "是否已开通微信虚拟支付(xpay)"))
    if mch is True and xpay is not True:
        risk.append("已持有微信支付商户号但未确认开通虚拟支付（xpay）：两者不是一回事——"
                    "商户号用于实物/服务交易，虚拟商品（会员/道具/内容）须走「虚拟支付 xpay」通道，"
                    "需在微信支付侧单独开通虚拟支付能力，不能复用普通商户号下单")
        items.append("- 商户号 vs 虚拟支付：持有商户号但 xpay 状态未确认（需区分开通）")
    elif mch is True and xpay is True:
        items.append("- 商户号 vs 虚拟支付：均具备（注意两者通道不同，虚拟商品走 xpay）")
    elif mch is False and xpay is not True:
        items.append("- 商户号 vs 虚拟支付：均无（虚拟商品场景只需开通 xpay，无需普通商户号）")

    # iOS 独立 App 限制（仅当存在独立上架 App 时才触发）
    ios = get_text(f, "是否涉及iOS独立App")
    if filled(ios) and any(w in norm(ios) for w in IOS_APP_WORDS):
        crit.append("存在独立上架 App Store 的 iOS 应用：该 App 内售卖虚拟商品（会员/道具）"
                    "必须走 Apple IAP（应用内购买），不得复用微信 xpay/微信支付，否则将被 App Store 拒审乃至下架；"
                    "微信小程序内的虚拟支付不受此限（走 xpay 即可）")
        items.append("- iOS 独立 App：涉及（Apple IAP 限制，阻断小程序方案套用）")
    elif filled(ios) and yesno(ios) is False:
        items.append("- iOS 独立 App：不涉及（仅微信小程序，xpay 可用）")
    else:
        items.append("- iOS 独立 App：未确认（如有独立 iOS App 须走 Apple IAP）")
    return items, crit, risk


def check_config(f):
    items = []
    crit = []
    risk = []
    offer = yesno(get_text(f, "offer_id是否配置"))
    prod = yesno(get_text(f, "product_id是否配置"))
    price = parse_num(get_text(f, "商品价格(分)"))

    if offer is False:
        crit.append("offer_id 未配置：虚拟支付下单必须绑定应用 offer_id（虚拟支付应用 ID），"
                    "请在微信支付商户平台-虚拟支付创建应用并获取")
        items.append("- offer_id：未配置（阻断）")
    elif offer is True:
        items.append("- offer_id：已配置")
    else:
        risk.append("未确认 offer_id 是否配置：下单与回调均依赖该 ID，请确认")
        items.append("- offer_id：未确认（风险）")

    if prod is False:
        crit.append("product_id 未配置：每个虚拟商品须有唯一 product_id（如会员商品 member_permanent），"
                    "否则无法下单与发货")
        items.append("- product_id：未配置（阻断）")
    elif prod is True:
        items.append("- product_id：已配置")
    else:
        risk.append("未确认 product_id 是否配置：请确认已创建对应商品并绑定")
        items.append("- product_id：未确认（风险）")

    if price is not None:
        if price <= 0:
            crit.append("商品价格异常（<=0 分）：价格须为正数且以「分」为单位，请核对金额换算")
            items.append("- 商品价格：%s 分（异常）" % int(price))
        elif price < 1:
            risk.append("商品价格 < 1 分：金额过小可能不符合最小计价单位，请确认是否为单位错误")
            items.append("- 商品价格：%s 分（待确认单位）" % int(price))
        else:
            items.append("- 商品价格：%s 分（约 %.2f 元）" % (int(price), price / 100.0))
    else:
        if filled(get_text(f, "商品价格(分)")):
            risk.append("商品价格无法识别为数字：xpay 价格以「分」为整数单位，请填写纯数字（如 6800 表示 68 元）")
            items.append("- 商品价格：%s（无法解析）" % get_text(f, "商品价格(分)"))
        else:
            risk.append("未填写商品价格：虚拟支付下单须传以「分」为单位的整数金额，请补齐")
            items.append("- 商品价格：未填（风险）")
    return items, crit, risk


def check_callback(f):
    items = []
    risk = []
    cb = yesno(get_text(f, "是否已配置发货回调"))
    idem = yesno(get_text(f, "回调是否幂等防重复发货"))
    reissue = yesno(get_text(f, "是否有订单补发机制"))

    if cb is False:
        risk.append("未配置发货回调（消息推送 xpay_goods_deliver_notify）：用户支付成功后平台通过"
                    "事件推送通知发货，若未配置将无法自动激活权益，须人工兜底")
        items.append("- 发货回调：未配置（风险-权益可能不自动发放）")
    elif cb is True:
        items.append("- 发货回调：已配置")
    else:
        risk.append("未确认是否配置发货回调：虚拟支付依赖消息推送回调完成发货，请确认")
        items.append("- 发货回调：未确认（风险）")

    if idem is False:
        risk.append("回调未做幂等/防重复发货：同一笔支付可能触发多次回调，"
                    "须以订单号去重，否则会重复发放会员/道具（资损）")
        items.append("- 回调幂等：未做（风险-重复发货资损）")
    elif idem is True:
        items.append("- 回调幂等：已做")
    else:
        items.append("- 回调幂等：未确认（建议实现订单号去重）")

    if reissue is False:
        risk.append("无订单补发机制：回调丢失/超时会导致掉单，须提供「补发/重新激活」入口或定时对账补单")
        items.append("- 补发机制：无（风险-掉单后权益缺失）")
    elif reissue is True:
        items.append("- 补发机制：有")
    else:
        items.append("- 补发机制：未确认（建议提供）")
    return items, risk


def check_compliance(f):
    items = []
    risk = []
    refund = yesno(get_text(f, "是否声明虚拟商品不支持退款"))
    minor = yesno(get_text(f, "是否做未成年人保护"))

    if refund is False:
        risk.append("未声明虚拟商品不支持退款：虚拟商品（会员/道具/内容）一经发放通常不支持退款，"
                    "须在购买页与协议明确告知，避免投诉与纠纷")
        items.append("- 退款声明：未声明（风险-客诉）")
    elif refund is True:
        items.append("- 退款声明：已声明")
    else:
        items.append("- 退款声明：未确认")

    if minor is False:
        risk.append("未做未成年人保护：涉付费的虚拟商品须落实实名与未成年人消费限制，"
                    "建议接入未成年人守护/消费提醒，规避合规风险")
        items.append("- 未成年人保护：未做（风险）")
    elif minor is True:
        items.append("- 未成年人保护：已做")
    else:
        items.append("- 未成年人保护：未确认")
    return items, risk


def check_process(f):
    items = []
    risk = []
    stage_txt = get_text(f, "当前接入阶段")
    n = norm(stage_txt) if filled(stage_txt) else ""
    link = yesno(get_text(f, "是否已联调下单与支付"))

    if not filled(stage_txt):
        stage = "未开始"
        items.append("- 当前阶段：未确认接入阶段 → 视为「未开始」")
        risk.append("未确认接入阶段：若尚未动手，请按「开通→配置→联调→上线」顺序推进")
    elif any(k in n for k in ("未开始", "未开通", "待开通")):
        stage = "未开始"
        items.append("- 当前阶段：未开始（待开通虚拟支付）")
    elif any(k in n for k in ("配置", "参数", "填参数")):
        stage = "配置中"
        items.append("- 当前阶段：配置中（offer/product/价格/回调）")
    elif any(k in n for k in ("联调", "调试", "对接")):
        stage = "联调中"
        items.append("- 当前阶段：联调中（下单/支付/回调）")
    elif any(k in n for k in ("上线", "已发", "生产", "正式")):
        stage = "已上线"
        items.append("- 当前阶段：已上线")
    else:
        stage = "其他"
        items.append("- 当前阶段：%s（未识别）" % stage_txt)

    if stage in ("配置中", "联调中", "已上线") and link is False:
        risk.append("已进入%s阶段但未确认下单/支付联调：上线前必须完成下单→支付→回调全链路联调，"
                    "避免生产环境支付失败" % stage)
        items.append("  - 下单支付联调：未完成（待办）")
    elif link is True:
        items.append("  - 下单支付联调：已完成")
    return items, risk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="")
    args = ap.parse_args()
    f = parse_md(args.path)
    if not f or not any(filled(v) for v in f.values()):
        print("# 待补正\n\n未读取到任何有效字段，请填写采集表后再核查。")
        return 2

    crit = []
    risk = []
    sections = []

    subj_txt = get_text(f, "主体类型")
    header = "# 小程序微信虚拟支付（xpay）接入避坑与合规报告"
    if filled(subj_txt):
        header += "（%s）" % subj_txt
    sections.append(header)
    sections.append("")

    pre_items, pre_c, pre_r = check_prereq(f)
    crit += pre_c
    risk += pre_r
    conf_items, conf_c, conf_r = check_config(f)
    crit += conf_c
    risk += conf_r
    cb_items, cb_r = check_callback(f)
    risk += cb_r
    comp_items, comp_r = check_compliance(f)
    risk += comp_r
    proc_items, proc_r = check_process(f)
    risk += proc_r

    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"
    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险与待办项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(subj_txt):
        summary += "- 主体类型：%s\n" % subj_txt
    summary += ("- 处置建议：先消除全部阻断项（主体/认证/offer/product/价格硬门槛），"
                "再落实回调幂等与补发，最后补齐合规声明。\n")
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 前置条件核查\n" + "\n".join(pre_items) + "\n\n"
    body += "### 配置核查（offer/product/价格）\n" + "\n".join(conf_items) + "\n\n"
    body += "### 回调与发货核查\n" + "\n".join(cb_items) + "\n\n"
    body += "### 合规要点核查\n" + "\n".join(comp_items) + "\n\n"
    body += "### 接入流程进度与下一步\n" + "\n".join(proc_items) + "\n"
    sections.append(body)

    rb = "## 三、阻断项与风险/待办\n\n"
    if crit:
        rb += "### 阻断项（必须处理，否则无法上线/不予通过）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险/待办项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "前置条件与配置均已满足，可推进联调与上线。\n\n"
    sections.append(rb)

    adv = ("## 四、操作指引（标准接入流程）\n\n"
           "1. 主体与认证：确保小程序为企业/个体工商户且已完成微信认证。\n"
           "2. 开通虚拟支付：在微信支付侧开通「虚拟支付（xpay）」能力，创建虚拟支付应用获取 offer_id。\n"
           "3. 创建商品：在虚拟支付后台创建 product_id（如会员商品 member_permanent），设置以「分」计的价格。\n"
           "4. 下单：小程序调用 xpay 下单接口，传入 offer_id/product_id/价格/订单号等参数拉起支付。\n"
           "5. 支付：用户完成支付，微信侧校验。\n"
           "6. 发货回调：配置消息推送事件 xpay_goods_deliver_notify → 云函数/服务端回调，"
           "以订单号幂等激活权益（如激活会员）。\n"
           "7. 补发对账：提供补发入口/定时对账，处理掉单与超时订单。\n"
           "8. 上线：联调无误后发布，购买页声明虚拟商品不退并做好未成年人保护。\n\n")
    sections.append(adv)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本指引依据公开资料与通用实践整理，**不替代微信支付/xpay 官方文档与审核结论**。\n"
                "- 虚拟支付（xpay）与微信支付商户号是**两套不同通道**：虚拟商品走 xpay，"
                "实物/服务交易才用普通商户号，切勿混用或误以为有商户号即可卖虚拟商品。\n"
                "- 若另有独立上架 App Store 的 iOS 应用，其内部虚拟商品须走 Apple IAP，不得复用 xpay。\n"
                "- 不得刷量、套现、虚假交易，违者将被限制乃至清退虚拟支付能力。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
