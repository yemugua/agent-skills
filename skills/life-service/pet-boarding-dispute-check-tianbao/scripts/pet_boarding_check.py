# -*- coding: utf-8 -*-
"""宠物寄养纠纷责任划分与退费维权核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：8~9 段核查报告，含结论摘要、过错归因、条款效力、责任比例、退费测算、
      证据缺口、维权路径、待办补正动作、边界与纪律。

退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime

# ---------------------------------------------------------------- 字段别名

FIELD_ALIAS = {
    "寄养方式": ["寄养方式", "托管方式", "寄养类型", "托管类型"],
    "寄养地点": ["寄养地点", "门店名称", "寄养门店", "经营主体", "寄养机构", "门店"],
    "订单平台": ["订单平台", "下单平台", "交易平台", "平台", "渠道"],
    "寄养起日": ["寄养起日", "入托日期", "开始日期", "寄养开始", "起始日期"],
    "寄养止日": ["寄养止日", "接回日期", "结束日期", "寄养结束", "截止日期"],
    "实际接回日": ["实际接回日", "实际接回", "接回时间"],
    "约定天数": ["约定天数", "约定寄养天数", "寄养天数", "合同天数"],
    "宠物信息": ["宠物信息", "宠物情况", "宠物基本情况", "宠物品种年龄"],
    "疫苗免疫情况": ["疫苗免疫情况", "疫苗情况", "免疫记录", "疫苗记录", "免疫情况"],
    "寄养前健康状态": ["寄养前健康状态", "入托前健康状态", "寄养前状态", "入托前状态", "送托前健康"],
    "纠纷类型": ["纠纷类型", "争议类型", "发生了什么", "事故类型"],
    "宠物最终状态": ["宠物最终状态", "当前状态", "宠物现状", "结局"],
    "商家是否承认过错": ["商家是否承认过错", "商家是否认责", "商家承认过错", "商家是否承认"],
    "商家是否推诿": ["商家是否推诿", "是否推诿", "商家推卸责任", "商家态度"],
    "合同有无免责条款": ["合同有无免责条款", "有无免责条款", "是否有免责条款", "免责条款情况", "合同有无免责"],
    "免责条款摘录": ["免责条款摘录", "免责条款内容", "免责条款原文", "条款摘录"],
    "有无加价行为": ["有无加价行为", "是否加价", "有无擅自加价", "临时加价情况", "加价情况"],
    "加价金额": ["加价金额", "加价数额", "额外收费金额", "临时收费金额"],
    "押金金额": ["押金金额", "押金", "定金金额", "预收押金"],
    "已付总额": ["已付总额", "已支付金额", "实付总额", "已付费用", "支付总额"],
    "已退金额": ["已退金额", "已退款金额", "已返还金额", "退款金额"],
    "商家扣款理由": ["商家扣款理由", "扣款理由", "扣除费用理由", "扣费理由"],
    "有无监控": ["有无监控", "是否有监控", "监控情况", "监控是否可查"],
    "是否已就医": ["是否已就医", "有无就医", "是否就诊", "就诊情况", "有无就诊记录"],
    "就诊记录情况": ["就诊记录情况", "就诊记录", "医疗记录", "诊断结果"],
    "寄养前照片视频": ["寄养前照片视频", "寄养前影像", "入托前照片", "寄养前照片", "有无寄养前照片"],
    "沟通记录留存": ["沟通记录留存", "聊天记录", "沟通记录", "有无聊天记录", "沟通记录情况"],
    "是否已投诉": ["是否已投诉", "有无投诉", "投诉情况", "是否已反映"],
    "诉求": ["诉求", "诉求是什么", "期望结果", "希望怎么解决", "你的诉求"],
    "协商经过": ["协商经过", "协商情况", "沟通经过", "协商结果"],
    "商家经营资质": ["商家经营资质", "营业执照状态", "经营资质", "是否具备资质", "资质情况"],
}

# ---------------------------------------------------------------- 基础工具

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "没有", "n/a", "na",
    "null", "none", "？", "?",
)


def norm(s):
    """归一：去空格、全角转半角、小写。"""
    if s is None:
        return ""
    out = str(s).strip()
    out = out.replace("：", ":").replace("　", " ")
    out = re.sub(r"\s+", "", out)
    return out.lower()


def filled(v):
    """是否视为已填。"""
    if v is None:
        return False
    return norm(v) not in {norm(t) for t in EMPTY_TOKENS}


def unknown(v):
    """是否属于未填/占位。unknown 必须认得「待填」这类词。"""
    return not filled(v)


def fmt_num(n):
    """数值去掉 .0。"""
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
    """从文本抽第一个数字。"""
    if v is None:
        return None
    s = str(v)
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_date(v):
    """解析日期，容忍 2026/9/1、2026-09-01、2026年9月1日。"""
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
    """读 Markdown 采集表，返回 {字段: 值}。支持 | 字段 | 值 | 与 字段：值。"""
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

        # 表格行：| 字段 | 值 |
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

        # 冒号行：字段：值（全角「：」与半角都要认）
        # 注意：re.split(pattern, line, 1) 只返 2 元组，必须写 k, v = ，不能写 k, _, v =
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    """按字段名取别名值。

    必须精确匹配：把 label 与 key 归一后整等比较。
    绝不能用子串 in ——「品类」会命中「是否涉及特殊品类」，导致串字段。
    """
    aliases = FIELD_ALIAS.get(key, [key])
    # 最长别名优先
    aliases = sorted(aliases, key=len, reverse=True)
    nk = norm(key)
    for a in aliases:
        na = norm(a)
        if not na:
            continue
        # 精确匹配
        if na in f:
            v = f.get(na)
            if filled(v):
                return v
        # 表格首列带序数前缀时，去掉前缀再精确匹配
        stripped = re.sub(r"^\d+[.、)]\s*", "", na)
        if stripped != na and stripped in f:
            v = f.get(stripped)
            if filled(v):
                return v
    return ""


# ---------------------------------------------------------------- 判定


NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "推诿", "推卸")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可")


def yesno(text, positive=True):
    """判断是否 X 类字段的取值。空值返回 None（未判定）。"""
    if unknown(text):
        return None
    n = norm(text)
    for w in NEG_WORDS:
        if n.startswith(w) or ("：" + w) in n:
            # 先判否定式，避免「不是」→「是」误判
            return False
    for w in POS_WORDS:
        if n.startswith(w):
            return True
    return None


def classify_cause(dispute_type, pet_state, merchant_admit, clinic, has_photo):
    """过错归因：商家过错 / 主人过错 / 第三方意外 / 不可抗力 / 待定。"""
    dt = norm(dispute_type)
    ps = norm(pet_state)
    reasons = []

    death_keywords = ("死亡", "去世", "死亡原因", "猝死", "没了", "走了")
    illness_keywords = ("生病", "发病", "呕吐", "腹泻", "发烧", "咳嗽", "住院", "输液", "细小", "犬瘟", "猫瘟", "皮肤病", "绝育", "手术")
    escape_keywords = ("走失", "丢失", "跑丢", "不见了", "失踪")
    injury_keywords = ("受伤", "摔", "骨折", "外伤", "咬伤", "烫伤", "坠", "掉", "压伤")

    is_death = any(k in dt or k in ps for k in death_keywords)
    is_ill = any(k in dt or k in ps for k in illness_keywords)
    is_escape = any(k in dt or k in ps for k in escape_keywords)
    is_injury = any(k in dt or k in ps for k in injury_keywords)

    # 明确承认过错 → 直接归商家过错
    if yesno(merchant_admit) is True:
        return "商家过错", ["商家书面或口头承认过错，责任明确"]

    # 免疫缺失是主人过错的主要情形
    if any(k in norm(clinic) for k in ("未免疫", "没免疫", "无免疫", "疫苗缺失")):
        return "主人过错", ["宠物入托前免疫记录缺失，未完成基础免疫即送寄养"]

    # 未提供寄养前影像，主人举证能力弱 → 归为待定
    if (is_death or is_ill or is_injury) and not filled(has_photo):
        reasons.append("未留存寄养前宠物健康状态照片/视频，损害发生前的基线状态无法固定")
        return "责任待定", reasons

    if is_death:
        reasons.append("宠物在寄养期间死亡，需先排除入托前已患病")
        if not filled(clinic):
            reasons.append("缺少就诊或尸检记录，死亡原因不明")
        if yesno(merchant_admit) is False:
            reasons.append("商家否认过错，双方对入托前状态存在争议")
        return "责任待定", reasons

    if is_ill:
        reasons.append("寄养期间发病，需区分入托前潜伏期与寄养期间感染")
        if not filled(clinic):
            reasons.append("缺少就诊记录，发病时间与诊疗结论未固定")
        return "责任待定", reasons

    if is_injury:
        return "商家过错", ["寄养期间发生外伤，寄养方对宠物安全负有保障义务"]

    if is_escape:
        return "商家过错", ["宠物在寄养期间走失，寄养方负有妥善看管与及时告知义务"]

    return "待定", ["纠纷类型未明确，需补充事实描述后才能归因"]


def check_clause(expiry_ans, clause_text, dispute_type):
    """免责条款效力核查：返回 (状态, 理由列表)。"""
    items = []
    if yesno(expiry_ans) is None and unknown(clause_text):
        return "待补正", ["未填写合同有无免责条款，也未摘录条款内容"]

    has = yesno(expiry_ans) is True or filled(clause_text)
    if not has:
        return "通过", ["合同未见免责条款，责任不因合同而被免除"]

    reasons = []
    if filled(clause_text):
        t = norm(clause_text)
        blanket = ("概不负责", "不承担任何责任", "一切后果自负", "宠物死亡概不负责",
                   "最终解释权", "概不退款", "自行承担", "与本店无关")
        for b in blanket:
            if b in t:
                reasons.append("条款含「%s」类表述，属不合理免除自身责任、无效" % b)
        if "宠物死亡" in t or "死亡" in t:
            reasons.append("条款预先免除对宠物死亡的责任，属未尽到安全保障义务，无效")
        if "生病" in t or "疾病" in t:
            reasons.append("条款预先免除疾病责任，无效")

    status = "不通过" if reasons else "有风险"
    if not reasons:
        reasons.append("存在免责条款但表述未明显违法，建议逐条确认范围与合理性")
    return status, reasons


def calc_refund(paid, refunded, deposit, deduct_reason, deduct_claimed):
    """退费测算：应退 = 已付 − 已退 − 有依据的扣除。"""
    items = []
    paid_n = parse_num(paid)
    ref_n = parse_num(refunded) or 0.0
    dep_n = parse_num(deposit)
    ded_n = parse_num(deduct_claimed)

    if paid_n is None:
        return None, ["未填写已付总额，无法测算应退金额"]

    if dep_n is not None and dep_n > paid_n:
        items.append("押金 %s 超过已付总额 %s，请核对是否重复计入" % (money(dep_n), money(paid_n)))

    net = paid_n - ref_n
    if net < 0:
        items.append("已退金额 %s 大于已付总额 %s，请核对金额" % (money(ref_n), money(paid_n)))
        net = 0.0

    if ded_n is not None and ded_n > 0:
        if filled(deduct_reason):
            items.append("商家扣款 %s，理由「%s」，需判断该理由是否有合同依据" % (money(ded_n), str(deduct_reason)[:40]))
        else:
            items.append("商家扣款 %s 但未给出理由，属无依据扣款，应全额返还" % money(ded_n))

    items.append("已付 %s − 已退 %s = 暂计应退 %s" % (money(paid_n), money(ref_n), money(net)))
    return net, items


def check_evidence(has_photo, has_chat, monitor, is_clinic):
    """证据缺口核查：返回 (缺口条数, 缺口列表)。"""
    gaps = []
    if not filled(has_photo):
        gaps.append("寄养前宠物健康状态照片/视频缺失——损害基线无法固定，最影响归因")
    if not filled(has_chat):
        gaps.append("与商家的沟通记录未留存——加价、免责条款提示、承认过错等均无载体")
    if yesno(monitor) is False:
        gaps.append("商家明确无监控或监控已灭失——应书面提出调取申请并保留送达凭证")
    if filled(monitor) is False:
        pass
    if is_clinic and not filled(has_chat):
        gaps.append("已就医但就诊记录未留存——诊疗结论是认定因果关系的关键")
    return len(gaps), gaps


def calc_ratio(cause):
    """按过错归因给出责任分摊参考。"""
    table = {
        "商家过错": (1.0, 0.0, "寄养方对宠物安全负有全面保障义务，违约或侵权成立"),
        "主人过错": (0.0, 1.0, "入托前未履行免疫等自身注意义务，损害由主人自担"),
        "责任待定": (0.5, 0.5, "双方均未尽到义务或证据不足，按对等暂分，待举证后调整"),
        "待定": (0.5, 0.5, "事实未查清，暂按对等处理"),
    }
    return table.get(cause, (0.5, 0.5, "归因未明，暂按对等处理"))


# ---------------------------------------------------------------- 报告


def build_report(f, base):
    rep = []
    risk = []
    todo = []

    pet = get_text(f, "宠物信息")
    place = get_text(f, "寄养地点")
    dispute = get_text(f, "纠纷类型")
    state = get_text(f, "宠物最终状态")
    admit = get_text(f, "纠纷类型")  # 占位，下面单独取
    merchant_admit = get_text(f, "商家是否承认过错")
    merchant_blame = get_text(f, "商家是否推诿")
    clause_ans = get_text(f, "合同有无免责条款")
    clause_txt = get_text(f, "免责条款摘录")
    extra_ans = get_text(f, "有无加价行为")
    extra_amt = get_text(f, "加价金额")
    paid = get_text(f, "已付总额")
    refunded = get_text(f, "已退金额")
    deposit = get_text(f, "押金金额")
    deduct_reason = get_text(f, "商家扣款理由")
    monitor = get_text(f, "有无监控")
    clinic = get_text(f, "就诊记录情况")
    is_clinic = yesno(get_text(f, "是否已就医")) is True
    has_photo = get_text(f, "寄养前照片视频")
    has_chat = get_text(f, "沟通记录留存")
    vaccine = get_text(f, "疫苗免疫情况")
    pre_health = get_text(f, "寄养前健康状态")
    platform = get_text(f, "订单平台")
    d_start = parse_date(get_text(f, "寄养起日"))
    d_end = parse_date(get_text(f, "寄养止日"))
    d_actual = parse_date(get_text(f, "实际接回日"))
    promised_days = parse_num(get_text(f, "约定天数"))
    demand = get_text(f, "诉求")
    done_complaint = get_text(f, "是否已投诉")

    # --- 1 结论摘要
    cause, cause_reasons = classify_cause(dispute, state, merchant_admit, clinic, has_photo)
    m_ratio, o_ratio, ratio_note = calc_ratio(cause)
    net, refund_items = calc_refund(paid, refunded, deposit, deduct_reason, get_text(f, "商家扣款理由"))

    clause_status, clause_items = check_clause(clause_ans, clause_txt, dispute)
    gap_n, gaps = check_evidence(has_photo, has_chat, monitor, is_clinic)

    if clause_status == "不通过":
        risk.append("免责/格式条款疑似无效：%s" % clause_items[0])
    if yesno(extra_ans) is True:
        amt = parse_num(extra_amt)
        risk.append("商家擅自加价 %s，未见事前告知与同意" % (money(amt) if amt is not None else "（金额未填）"))
    if cause == "责任待定":
        risk.append("责任归属待定，关键在于寄养前健康基线与免责条款效力")
    if gap_n > 0:
        risk.append("证据缺口 %d 项，直接影响过错认定与赔偿主张" % gap_n)

    if cause == "主人过错":
        verdict = "不通过"
    elif not filled(paid) or not filled(dispute):
        # 一行没填或核心事实缺失，不得下任何风险结论，一律待补正
        verdict = "待补正"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "有风险"

    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 寄养主体：%s" % (place if filled(place) else "未填写"))
    rep.append("- 宠物：%s" % (pet if filled(pet) else "未填写"))
    rep.append("- 纠纷类型：%s" % (dispute if filled(dispute) else "未填写"))
    rep.append("- 宠物最终状态：%s" % (state if filled(state) else "未填写"))
    rep.append("- **过错归因：%s**" % cause)
    rep.append("- 责任分摊参考：寄养方 %s%% / 主人 %s%% —— %s" %
               (fmt_num(round(m_ratio * 100)), fmt_num(round(o_ratio * 100)), ratio_note))
    rep.append("- 条款效力：%s" % clause_status)
    rep.append("- 暂计应退：%s" % (money(net) if net is not None else "无法测算"))
    rep.append("- **总体结论：%s**" % verdict)
    rep.append("")

    # --- 2 事实要素核查
    rep.append("## 寄养事实要素核查")
    rep.append("")
    rep.append("| 要素 | 填写内容 | 核查 |")
    rep.append("| --- | --- | --- |")
    rows = [
        ("寄养起日", get_text(f, "寄养起日"), d_start is not None),
        ("寄养止日", get_text(f, "寄养止日"), d_end is not None),
        ("约定天数", get_text(f, "约定天数"), promised_days is not None),
        ("实际接回日", get_text(f, "实际接回日"), d_actual is not None),
        ("入托前健康状态", pre_health, filled(pre_health)),
        ("疫苗免疫情况", vaccine, filled(vaccine)),
    ]
    for name, val, ok in rows:
        rep.append("| %s | %s | %s |" % (name, val if filled(val) else "未填写", "已明确" if ok else "**待补正**"))
    rep.append("")
    if d_start and d_end:
        span = days_between(d_start, d_end)
        rep.append("- 约定寄养区间跨度：%s 天" % fmt_num(span))
        if d_actual:
            real = days_between(d_start, d_actual)
            over = real - span if span is not None else None
            if over is not None and over > 0:
                rep.append("- 实际寄养 %s 天，**超期 %s 天**，超期费主张需以合同约定标准为准" %
                           (fmt_num(real), fmt_num(over)))
                risk.append("超期 %s 天，超期费若按商家单方标准收取，属不合理" % fmt_num(over))
    else:
        rep.append("- 寄养起止日未填写完整，**超期天数无法核算**，需补齐后才能主张超期费")
        todo.append("补齐寄养起日与实际接回日，用于核算超期天数")
    rep.append("")

    # --- 3 过错归因
    rep.append("## 过错归因分析")
    rep.append("")
    for r in cause_reasons:
        rep.append("- %s" % r)
    if yesno(merchant_admit) is False:
        rep.append("- 商家明确否认过错，双方对入托前状态存在根本分歧")
        todo.append("书面要求商家说明否认依据（是否查监控、是否留存入托记录）")
    if yesno(merchant_blame) is True:
        rep.append("- 存在商家推诿情形，协商记录应完整保存")
    rep.append("")
    if not cause_reasons:
        rep.append("- 事实描述不足，归因暂列「待定」")
    rep.append("> 提示：宠物在中国法律下不属于独立民事权利主体，损害赔偿一般按**财产损失**主张，"
               "需证明寄养方存在过错或违约；重大金额或宠物死亡建议同时咨询执业律师。")
    rep.append("")

    # --- 4 条款效力
    rep.append("## 免责条款与格式条款效力")
    rep.append("")
    for c in clause_items:
        rep.append("- %s" % c)
    if filled(clause_txt):
        rep.append("- 条款原文摘录：%s" % str(clause_txt)[:120])
    rep.append("")
    if yesno(extra_ans) is True:
        amt = parse_num(extra_amt)
        rep.append("- 商家擅自加价：%s" % (money(amt) if amt is not None else "金额未填写"))
        rep.append("- 未经书面同意的费用变更，事后补收难以支持；应要求商家提供事前告知记录")
        todo.append("要求商家出示加价的合同依据或事前告知记录，无依据则主张返还")
    else:
        rep.append("- 未申报擅自加价情形")
    rep.append("")

    # --- 5 责任比例
    rep.append("## 责任分摊测算")
    rep.append("")
    rep.append("| 归因 | 寄养方责任 | 主人责任 | 说明 |")
    rep.append("| --- | --- | --- | --- |")
    rep.append("| %s | %s%% | %s%% | %s |" %
               (cause, fmt_num(round(m_ratio * 100)), fmt_num(round(o_ratio * 100)), ratio_note))
    rep.append("")
    if net is not None:
        m_share = net * m_ratio
        rep.append("- 若按寄养方承担 %s%%，应退金额中寄养方承担约 %s" %
                   (fmt_num(round(m_ratio * 100)), money(round(m_share, 2))))
        rep.append("- 若按主人自担 %s%%，实际可主张金额约 %s" %
                   (fmt_num(round(o_ratio * 100)), money(round(net * o_ratio, 2))))
    rep.append("")

    # --- 6 退费测算
    rep.append("## 退费与扣款核查")
    rep.append("")
    for r in refund_items:
        rep.append("- %s" % r)
    if filled(deduct_reason):
        rep.append("- 商家扣款理由「%s」：需与合同条款逐一比对，无约定依据的应视为不合理扣款" %
                   str(deduct_reason)[:60])
    else:
        rep.append("- 未申报商家扣款理由；若确有扣除，应要求其列明依据与计算方式")
    rep.append("")

    # --- 7 证据缺口
    rep.append("## 证据缺口与固定要点")
    rep.append("")
    if gaps:
        for g in gaps:
            rep.append("- **%s**" % g)
    else:
        rep.append("- 采集表内主要证据项已填写，仍需确认原件/原始载体是否完整")
    rep.append("")
    rep.append("需优先固定的材料：")
    rep.append("1. 寄养前宠物照片与视频（含牙齿、毛色、皮肤、在养状态）")
    rep.append("2. 疫苗本与免疫记录原件")
    rep.append("3. 寄养期间每日喂食/遛弯视频或商家每日反馈记录")
    rep.append("4. 就诊记录、诊断证明、费用票据")
    rep.append("5. 书面提出监控调取申请并保留送达凭证（EMS 面单或店内签收）")
    rep.append("6. 与商家的完整聊天记录与通话录音（通话录音须为通话当场录制）")
    rep.append("")

    # --- 8 维权路径
    rep.append("## 维权路径")
    rep.append("")
    rep.append("| 层级 | 动作 | 适用条件 |")
    rep.append("| --- | --- | --- |")
    rep.append("| 第 1 级 | 与寄养方书面协商 | 全部情形；先书面提出，留痕 |")
    rep.append("| 第 2 级 | 平台投诉与申请介入 | 订单经第三方平台下单 |")
    rep.append("| 第 3 级 | 12315 投诉（全国 12315 平台/当地市场监管） | 商家拒不退款、加价、扣款无依据 |")
    rep.append("| 第 4 级 | 消费者协会12315 站/当地消协调解 | 涉及格式条款争议 |")
    rep.append("| 第 5 级 | 公安报案 | 宠物死亡且疑人为过失、商家失联或涉嫌诈骗 |")
    rep.append("| 第 6 级 | 人民法院起诉 | 金额较大、协商与投诉均无结果 |")
    rep.append("")
    if yesno(done_complaint) is True:
        rep.append("- 已申报投诉，请保留受理编号与处理时限")
    else:
        rep.append("- 未申报投诉，建议按上表逐级推进，每级留时间戳与回执")
    rep.append("")

    # --- 9 待办补正动作
    rep.append("## 待办补正动作")
    rep.append("")
    all_todo = list(todo)
    if gaps:
        all_todo.extend(gaps)
    if net is None:
        all_todo.append("补齐已付总额与已退金额，否则无法测算应退")
    if not filled(clause_txt) and yesno(clause_ans) is not True:
        all_todo.append("调取寄养协议原件，摘录免责与退费条款")
    if not filled(demand):
        all_todo.append("明确诉求：全额退款 / 赔偿医疗费 / 赔偿宠物价值 / 道歉")
    if not all_todo:
        all_todo.append("信息已较完整，可直接进入协商，协商不成按维权路径升级")
    for i, t in enumerate(all_todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # --- 10 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见，最终以主管部门或司法机关认定为准。")
    rep.append("- 责任比例系依归因推算的**参考区间**，不是法定结论，实际以协商或裁判结果为准。")
    rep.append("- 涉及金额较大、宠物死亡或多只宠物受损的，建议同时咨询执业律师。")
    rep.append("- 本技能不提供任何代办服务，不代替你与商家谈判出具文书。")

    return "\n".join(rep), verdict, risk, all_todo


# ---------------------------------------------------------------- CLI


def main():
    ap = argparse.ArgumentParser(description="宠物寄养纠纷责任划分与退费维权核查")
    ap.add_argument("md", nargs="?", default=None, help="采集表 Markdown 路径")
    ap.add_argument("--input", default=None, help="采集表 Markdown 路径")
    ap.add_argument("--base", default=None, help="基准日期 YYYY-MM-DD")
    ap.add_argument("--out", default=None, help="报告输出路径")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    args = ap.parse_args()

    path = args.md or args.input
    base = parse_date(args.base) if args.base else date.today()

    if not path or not os.path.exists(path):
        msg = "采集表不存在：%s" % path
        if args.json:
            print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False))
        else:
            print(msg)
        return 2

    f = parse_md(path)
    if not f:
        msg = "采集表为空或格式无法解析，请确认使用「| 字段 | 值 |」或「字段：值」格式"
        if args.json:
            print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False))
        else:
            print(msg)
        return 2

    report, verdict, risk, todo = build_report(f, base)

    if args.json:
        print(json.dumps({
            "结论": verdict,
            "风险项": risk,
            "待办": todo,
            "报告": report,
        }, ensure_ascii=False, indent=2))
    else:
        print(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)

    # 关键信息缺失时返回 2，但不崩
    if unknown(get_text(f, "已付总额")):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())