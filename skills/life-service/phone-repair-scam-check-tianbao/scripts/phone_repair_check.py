# -*- coding: utf-8 -*-
"""手机维修防骗与套路核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段核查报告，含结论摘要、故障诊断与报价核查、骗局手法与维修方、
      费用与收款、维修结果与质保、法律后果与举报入口、证据清单、
      待办补正动作、边界与纪律。

只做信息核查与维权指引，不提供任何维修或代修服务。
退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

FIELD_ALIAS = {
    "维修方": ["维修方", "店铺名称", "维修店", "商家名称", "维修机构", "门店名称", "门店"],
    "维修渠道": ["维修渠道", "维修方式", "在哪修的", "来源渠道", "线上还是线下", "维修来源"],
    "设备品牌型号": ["设备品牌型号", "手机型号", "机型", "设备型号", "什么手机", "设备"],
    "故障自述": ["故障自述", "原始故障", "用户报修问题", "什么问题", "故障描述", "报修问题"],
    "对方诊断结论": ["对方诊断结论", "诊断结果", "对方说哪里坏", "判定故障", "维修结论", "检测结论"],
    "是否提前报价确认": ["是否提前报价确认", "是否事先报价", "修前是否告知价格", "是否确认价格",
                      "有无事先报价", "是否先报价", "修前报价"],
    "报价金额": ["报价金额", "维修报价", "费用", "报价", "多少钱", "维修费"],
    "已付金额": ["已付金额", "已支付金额", "实付金额", "付款金额", "已交金额"],
    "已退金额": ["已退金额", "已退款金额", "退款金额", "已退"],
    "付款方式": ["付款方式", "支付方式", "怎么付的", "如何付款"],
    "收款主体": ["收款主体", "收款方", "收款单位", "打款给谁", "收款人"],
    "是否出具维修单据": ["是否出具维修单据", "有无单据", "是否开发票", "是否给凭证",
                      "有无发票", "是否出凭证", "给工单吗"],
    "是否更换零件": ["是否更换零件", "换了零件吗", "是否换件", "有无换件"],
    "更换零件明细": ["更换零件明细", "换了什么", "更换部件", "换件内容", "换的零件"],
    "更换零件是否原装正品": ["更换零件是否原装正品", "零件是否原装", "是否原装", "配件正品",
                          "是否原装正品", "零件正品"],
    "旧零件是否归还": ["旧零件是否归还", "旧件归还", "旧零件退回", "旧件是否返还", "旧件给没给"],
    "维修后原故障是否解决": ["维修后原故障是否解决", "修好没", "原故障是否消失", "是否修好",
                          "修好了吗", "原问题解决"],
    "是否出现新故障": ["是否出现新故障", "修完又坏", "有没有新毛病", "修出新问题", "又坏了",
                    "出现新故障"],
    "有无保修承诺": ["有无保修承诺", "保修期", "保修多久", "是否保修", "保修承诺", "质保"],
    "维修方资质": ["维修方资质", "有无资质", "是否有维修资质", "资质情况", "营业执照"],
    "是否官方售后": ["是否官方售后", "官方还是第三方", "是否品牌售后", "官方售后吗", "品牌授权"],
    "是否已举报": ["是否已举报", "有无举报", "是否投诉", "投诉了吗", "是否已投诉", "举报没有"],
    "证据留存情况": ["证据留存情况", "证据情况", "有哪些证据", "留证情况", "已保存材料"],
    "诉求": ["诉求", "希望怎么解决", "期望结果", "想要什么"],
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


# 报修的小故障，本不该被诊断为「主板损坏」
MINOR_FAULTS = ("屏幕", "电池", "充电", "听筒", "摄像头", "外壳", "后盖",
                "进水", "扬声器", "按键", "尾插", "信号")


def check_diagnosis(f):
    """故障诊断与报价核查：返回 (状态, 说明列表)。"""
    items = []
    official = yesno(get_text(f, "是否官方售后"))
    conf = yesno(get_text(f, "是否提前报价确认"))
    receipt = yesno(get_text(f, "是否出具维修单据"))
    diag = get_text(f, "对方诊断结论")
    fault = get_text(f, "故障自述")
    status = "有风险"

    items.append("报修问题：%s" % (fault if filled(fault) else "未填写"))
    items.append("对方诊断：%s" % (diag if filled(diag) else "未填写"))
    items.append("是否官方售后：%s" % ("是" if official is True else
                                   "否" if official is False else "未填写"))
    items.append("修前是否确认报价：%s" % ("是" if conf is True else
                                     "否" if conf is False else "未填写"))
    items.append("是否出具单据/发票：%s" % ("是" if receipt is True else
                                     "否" if receipt is False else "未填写"))

    n_diag = norm(diag)
    n_fault = norm(fault)
    if filled(diag) and filled(fault) and "主板" in n_diag \
            and any(m in n_fault for m in MINOR_FAULTS) and "主板" not in n_fault:
        items.append("**诊断与报修明显不符**：报修为屏幕/电池/充电等小故障，"
                     "却被诊断为主板损坏，典型的小病大修套路")
        status = "不通过"
    elif official is True:
        status = "通过"
    else:
        status = "有风险"

    if official is False:
        items.append("**非官方/第三方维修**：价格、配件、质保都需自行把关，"
                     "优先要求官方售后或品牌授权点")
    if conf is False:
        items.append("修前未确认报价：易被坐地起价，应先问清总价、配件与工时再同意维修")
    if receipt is False:
        items.append("未出具维修单据/发票：事后维权无书面凭证，应索要并留存")
    return status, items


def check_scam(f):
    """骗局手法与维修方：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    diag = get_text(f, "对方诊断结论")
    fault = get_text(f, "故障自述")
    parts_detail = get_text(f, "更换零件明细")
    qual = get_text(f, "维修方资质")
    official = yesno(get_text(f, "是否官方售后"))
    conf = yesno(get_text(f, "是否提前报价确认"))
    receipt = yesno(get_text(f, "是否出具维修单据"))
    genuine = yesno(get_text(f, "更换零件是否原装正品"))
    old_return = yesno(get_text(f, "旧零件是否归还"))
    solved = yesno(get_text(f, "维修后原故障是否解决"))
    new_fault = yesno(get_text(f, "是否出现新故障"))

    blob = norm(" ".join([diag, fault, parts_detail, qual]))

    shop = get_text(f, "维修方")
    items.append("维修方：%s" % (shop if filled(shop) else "未填写"))

    high_kw = {
        "偷换": "「偷换零件/掉包」——把好的零件换成劣质或坏的，属欺诈，应立即索要旧件并举报",
        "掉包": "「掉包零件」——把原装件换成劣质件，属欺诈",
        "调包": "「调包零件」——同上",
        "小病大修": "「小病大修」——把小故障说成大修，虚增维修项目与费用",
        "漫天要价": "「漫天要价/坐地起价」——修前不报价，事后开出远高于市场价的账单",
        "坐地起价": "「坐地起价」——拆机后以「发现新问题」为由加价",
        "天价": "「天价维修」——明显高于市场价的报价，应比对多家再决定",
        "以次充好": "「以次充好」——用劣质/拆机件冒充原装正品",
        "无资质": "「无维修资质」——无营业执照或维修资质却承接维修，属违规经营",
        "没有资质": "「没有资质」——同上",
    }
    for k, v in high_kw.items():
        if k in blob:
            crit.append("骗局手法：%s" % v)

    if genuine is False:
        crit.append("更换零件非原装正品：涉嫌以次充好，应要求提供配件来源与正品凭证")
    if solved is False:
        crit.append("原故障未解决：维修无效，应要求重做或退款，不得重复收费")
    if new_fault is True:
        crit.append("维修后出现新故障：疑似操作不当或故意制造故障，应拒付并要求说明")

    if old_return is False:
        risk.append("旧零件未归还：无法证明被换件，应坚持索要旧件并拍照")
    if conf is False:
        risk.append("修前未确认报价：易被坐地起价")
    if receipt is False:
        risk.append("未出具维修单据/发票：维权无书面凭证")
    if official is False and not filled(qual):
        risk.append("非官方售后但资质不明：建议核查营业执照与品牌授权")
    return crit, risk, items


def check_fee(f):
    """费用与收款：返回 (风险项, 说明列表)。"""
    risk = []
    items = []
    fee = parse_num(get_text(f, "报价金额"))
    paid = parse_num(get_text(f, "已付金额"))
    back = parse_num(get_text(f, "已退金额")) or 0.0
    payee = get_text(f, "收款主体")
    shop = get_text(f, "维修方")
    pay = get_text(f, "付款方式")

    if paid is None and fee is None:
        items.append("未填写报价与已付金额，**金额部分无法核查**")
    else:
        base = paid if paid is not None else fee
        items.append("已付 %s（报价 %s）" % (money(paid) if paid is not None else "未填写",
                                         money(fee) if fee is not None else "未填写"))
        net = base - back
        items.append("已付 %s − 已退 %s = 未退 %s" % (money(base), money(back), money(net)))
        if paid is not None and fee is not None and paid > fee:
            risk.append("已付 %s 超过报价 %s，超出部分无依据，应追回差价" % (money(paid), money(fee)))

    n_pay = norm(pay)
    if filled(pay) and any(k in n_pay for k in ("个人", "现金", "微信转")):
        risk.append("收款为个人账户或现金：无经营主体可追，追损难度大")
    if filled(payee) and filled(shop) and norm(payee) != norm(shop):
        risk.append("收款主体「%s」与维修方「%s」不一致，出事后极易互相推诿" % (payee, shop))
    elif not filled(payee):
        risk.append("未填写收款主体，需核对付款凭证上的收款方名称")
    return risk, items


def check_quality(f):
    """维修结果与质保：返回说明列表。"""
    items = []
    solved = yesno(get_text(f, "维修后原故障是否解决"))
    new_fault = yesno(get_text(f, "是否出现新故障"))
    warranty = get_text(f, "有无保修承诺")
    if solved is False:
        items.append("原故障未解决，维修无效，应要求免费重做或退款")
    elif solved is True:
        items.append("原故障已解决")
    else:
        items.append("未填写原故障是否解决")
    if new_fault is True:
        items.append("出现新故障，应要求说明原因并免费修复，必要时投诉")
    elif new_fault is False:
        items.append("未出现新故障")
    if filled(warranty):
        items.append("保修承诺：%s（请留存书面保修凭证，写明期限与范围）" % str(warranty)[:60])
    else:
        items.append("未约定保修：建议补签保修凭证，避免修完即失联")
    return items


def check_evidence(f):
    ev = norm(get_text(f, "证据留存情况"))
    need = [
        ("聊天/广告与宣传记录", ("聊天", "广告", "宣传", "页面", "截图", "朋友圈", "记录")),
        ("付款凭证与收款方信息", ("付款", "转账", "流水", "发票", "收据", "收款")),
        ("维修单据/报价单/工单", ("单据", "报价", "凭证", "发票", "工单")),
        ("维修前后照片与拆机照", ("照片", "图片", "拆机", "实物", "前后")),
        ("旧零件照片", ("旧件", "旧零件", "照片")),
        ("对方主体信息", ("主体", "公司名", "店铺名", "电话", "营业执照")),
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

    shop = get_text(f, "维修方")
    fault = get_text(f, "故障自述")
    diag = get_text(f, "对方诊断结论")
    paid = parse_num(get_text(f, "已付金额"))
    official = yesno(get_text(f, "是否官方售后"))
    solved = yesno(get_text(f, "维修后原故障是否解决"))
    demand = get_text(f, "诉求")

    diag_status, diag_items = check_diagnosis(f)
    s_crit, s_risk, s_items = check_scam(f)
    fee_risk, fee_items = check_fee(f)
    qual_items = check_quality(f)
    have_ev, miss_ev = check_evidence(f)

    core_missing = not filled(shop) and not filled(fault) and not filled(diag)
    if not core_missing:
        crit.extend(s_crit)
        if diag_status == "不通过":
            crit.append("诊断与报修不符：见故障诊断与报价核查")
        risk.extend(s_risk)
        risk.extend(fee_risk)
        if diag_status == "待补正":
            risk.append("诊断与报价未明确，维修合理性待核")
        if miss_ev:
            risk.append("证据缺失 %d 项：%s" % (len(miss_ev), "、".join(miss_ev[:3])))

    if core_missing:
        verdict = "待补正"
    elif crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"

    # 1 结论摘要
    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 维修方：%s" % (shop if filled(shop) else "未填写"))
    rep.append("- 报修问题：%s" % (fault if filled(fault) else "未填写"))
    rep.append("- 是否官方售后：%s" % ("是" if official is True else
                                   "否" if official is False else "未填写"))
    rep.append("- 已付金额：%s" % (money(paid) if paid is not None else "未填写"))
    rep.append("- 骗局手法命中 %d 项 / 风险项 %d 项" % (len(s_crit), len(s_risk)))
    rep.append("- 维修结果：%s" % ("原故障已解决" if solved is True else
                               "原故障未解决" if solved is False else "未填写"))
    rep.append("- **总体结论：%s**" % verdict)
    rep.append("")

    # 2 诊断与报价
    rep.append("## 故障诊断与报价核查")
    rep.append("")
    for it in diag_items:
        rep.append("- %s" % it)
    rep.append("")

    # 3 手法与维修方
    rep.append("## 骗局手法与维修方核查")
    rep.append("")
    for it in s_items:
        rep.append("- %s" % it)
    for c in s_crit:
        rep.append("- **%s**" % c)
    for r in s_risk:
        rep.append("- %s" % r)
    if filled(diag):
        rep.append("- 对方诊断摘录：%s" % str(diag)[:120])
    rep.append("")

    # 4 费用
    rep.append("## 费用与收款核查")
    rep.append("")
    for it in fee_items:
        rep.append("- %s" % it)
    for r in fee_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 5 维修结果与质保
    rep.append("## 维修结果与质保")
    rep.append("")
    for it in qual_items:
        rep.append("- %s" % it)
    rep.append("")

    # 6 后果与举报
    rep.append("## 法律后果、合规取证路径与举报入口")
    rep.append("")
    rep.append("- 维修服务受《消费者权益保护法》《移动电话机商品修理更换退货责任规定》"
               "（手机三包规定）保护：维修应明码标价、如实告知故障与配件，不得虚列项目。")
    rep.append("- 经营无照、虚报故障、以次充好的，可依据《消费者权益保护法》第五十五条"
               "主张「退一赔三」（不足五百按五百），构成欺诈的另行处罚。")
    rep.append("- 偷换零件、故意制造故障的，情节严重时涉嫌诈骗或故意毁坏财物，可报警处理。")
    rep.append("- 正规渠道：品牌官方售后/授权服务中心（价格透明、配件正品、有保修）；"
               "第三方维修应查看营业执照与口碑评价。")
    rep.append("- 举报入口：12315（全国消协，微信/支付宝小程序或电话）、"
               "黑猫投诉等平台、市场监管部门（无照/虚假宣传）、公安机关（失联或明显诈骗）。")
    if yesno(get_text(f, "是否已举报")) is True:
        rep.append("- 已申报投诉/举报，请保留受理编号与处理进度")
    else:
        rep.append("- 尚未投诉：先固定证据（拍照、留单据、导出聊天），再按上列入口投诉")
    rep.append("")

    # 7 证据
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
    rep.append("固定要点：拆机前后各拍清晰照片与视频；旧零件必须索要并单独拍照；"
               "聊天记录连上下文导出，不要只截单张；付款用可查账的方式并备注用途。")
    rep.append("")

    # 8 待办
    rep.append("## 待办补正动作")
    rep.append("")
    if core_missing:
        todo.append("补齐「维修方」「故障自述」「对方诊断结论」——这是出具结论的前提")
    if diag_status != "通过":
        todo.append("要求维修方书面说明故障部位与依据，与报修问题逐项核对，判断是否小病大修")
    if not filled(get_text(f, "是否提前报价确认")) or yesno(get_text(f,
            "是否提前报价确认")) is False:
        todo.append("今后维修坚持「先报价、确认总价与配件后再同意」，拒绝拆机后坐地起价")
    if yesno(get_text(f, "更换零件是否原装正品")) is False:
        todo.append("要求提供配件正品凭证与来源，拒绝以次充好")
    if yesno(get_text(f, "旧零件是否归还")) is False:
        todo.append("立即索要旧零件并拍照，作为是否被换件的证据")
    if yesno(get_text(f, "维修后原故障是否解决")) is False:
        todo.append("原故障未解决：要求免费重做或退款，不得重复收费")
    if yesno(get_text(f, "是否出现新故障")) is True:
        todo.append("新故障：要求免费修复并说明原因，必要时投诉")
    if not filled(get_text(f, "收款主体")):
        todo.append("核对付款凭证上的收款方名称，与维修方是否一致")
    for m in miss_ev:
        todo.append("补齐证据：%s" % m)
    if not filled(demand):
        todo.append("明确诉求：退款 / 重做 / 赔偿 / 投诉举报")
    if not todo:
        todo.append("信息已较完整，按报告结论执行；已官方售后的保留保修凭证")
    for i, t in enumerate(todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见与官方核验，"
               "最终以市场监管部门、司法机关及品牌官方认定为准。")
    rep.append("- 维修合理性以**实物检测与官方售后复核**为准，单方诊断不能单独定论。")
    rep.append("- **本技能不提供任何维修、代修或介绍维修渠道服务**，只做核查与维权指引。")
    rep.append("- 涉及金额较大或对方失联的，应立即向公安机关报案并向 12315 投诉。")

    return "\n".join(rep), verdict, crit + risk, todo


def main():
    ap = argparse.ArgumentParser(description="手机维修防骗与套路核查")
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

    if not filled(get_text(f, "维修方")) and not filled(get_text(f, "故障自述")) \
            and not filled(get_text(f, "对方诊断结论")):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
