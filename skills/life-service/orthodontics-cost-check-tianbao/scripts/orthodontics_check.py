# -*- coding: utf-8 -*-
"""牙齿矫正正畸花费与套路核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段核查报告，含结论摘要、机构与医师资质、报价与增项、付款方式与金融风险、
      疗程进度与效果争议、证据清单、维权路径、待办补正动作、边界与纪律。

退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

FIELD_ALIAS = {
    "机构名称": ["机构名称", "诊所名称", "医院名称", "就诊机构", "机构"],
    "机构类型": ["机构类型", "机构性质", "公立或私立", "诊所类型"],
    "是否核对机构执业许可": ["是否核对机构执业许可", "有无执业许可", "机构执业许可", "是否查过资质", "机构资质"],
    "医师姓名": ["医师姓名", "主治医生", "医生姓名", "正畸医生"],
    "是否核对医师执业地点": ["是否核对医师执业地点", "医师执业地点", "是否查过医师执业", "医师资质核查"],
    "矫治方式": ["矫治方式", "矫正方式", "矫治器类型", "牙套类型", "方案类型"],
    "矫治器品牌": ["矫治器品牌", "牙套品牌", "隐形品牌", "品牌"],
    "是否拿到品牌授权卡": ["是否拿到品牌授权卡", "有无授权卡", "授权卡情况", "是否提供授权证明"],
    "方案书是否写明疗程与副数": ["方案书是否写明疗程与副数", "方案书是否写明", "有无方案书", "方案书情况"],
    "约定疗程月数": ["约定疗程月数", "预计疗程", "疗程月数", "约定周期"],
    "实际已进行月数": ["实际已进行月数", "已进行月数", "已做多久", "实际疗程"],
    "是否拍片取模": ["是否拍片取模", "有无拍片", "检查情况", "是否取模", "影像资料"],
    "报价总金额": ["报价总金额", "报价金额", "合同金额", "总价", "方案报价"],
    "已付金额": ["已付金额", "已支付金额", "实付金额", "已交费用", "付款金额"],
    "已退金额": ["已退金额", "已退款金额", "退款金额", "已返还金额"],
    "增项情况": ["增项情况", "追加项目", "新增项目", "加项情况", "额外项目"],
    "增项金额": ["增项金额", "加收金额", "追加金额", "额外收费"],
    "增项是否事前告知": ["增项是否事前告知", "是否事前告知", "有无提前告知", "增项告知情况"],
    "保持器是否含在报价内": ["保持器是否含在报价内", "保持器是否包含", "保持器归属", "是否含保持器"],
    "付款方式": ["付款方式", "支付方式", "缴费方式", "怎么付的"],
    "分期机构": ["分期机构", "分期平台", "贷款机构", "放款方"],
    "分期年化利率": ["分期年化利率", "分期利率", "贷款利率", "年化利率"],
    "机构是否已停业": ["机构是否已停业", "是否停业", "机构现状", "是否跑路"],
    "是否中途更换医生": ["是否中途更换医生", "是否换医生", "有无更换主治", "医生是否更换"],
    "换医生是否事前告知": ["换医生是否事前告知", "换医生是否告知", "更换医生告知情况"],
    "是否存在效果争议": ["是否存在效果争议", "有无效果争议", "效果争议", "是否对效果不满"],
    "效果争议描述": ["效果争议描述", "争议描述", "效果问题", "问题描述"],
    "是否签知情同意书": ["是否签知情同意书", "有无知情同意书", "是否签同意书", "知情同意书"],
    "合同条款摘录": ["合同条款摘录", "合同条款", "霸王条款", "格式条款原文"],
    "宣传承诺摘录": ["宣传承诺摘录", "宣传话术", "承诺话术", "广告承诺"],
    "证据留存情况": ["证据留存情况", "证据情况", "有哪些证据", "留证情况", "已保存材料"],
    "是否已投诉": ["是否已投诉", "有无投诉", "投诉情况"],
    "诉求": ["诉求", "希望怎么解决", "期望结果", "想要什么结果"],
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


def check_qual(f):
    """机构与医师资质核查：返回 (状态, 说明列表)。"""
    items = []
    lic = yesno(get_text(f, "是否核对机构执业许可"))
    doc = yesno(get_text(f, "是否核对医师执业地点"))
    org = get_text(f, "机构名称")
    docname = get_text(f, "医师姓名")
    status = "有风险"

    if lic is None and doc is None:
        items.append("未填写机构执业许可与医师执业地点的核查情况，**资质这一段无法判断**")
        return "待补正", items
    if lic is False:
        items.append("**机构执业许可未核实**：应到当地卫生健康委员会官网「医疗机构查询」核对诊疗科目是否含口腔科")
        status = "不通过"
    elif lic is True:
        items.append("机构执业许可已核实，仍建议留存查询结果截图")
    if doc is False:
        items.append("**医师执业地点未核实**：医师执业地点必须与就诊机构一致，"
                     "不一致属违规执业，是投诉卫健部门的有力抓手")
        status = "不通过"
    elif doc is True:
        items.append("医师执业地点已核实，建议核对执业范围是否为口腔类别")
    items.append("机构：%s；医师：%s" % (org if filled(org) else "未填写",
                                  docname if filled(docname) else "未填写"))
    return status, items


def check_quote(f):
    """报价与增项核查：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    quote = parse_num(get_text(f, "报价总金额"))
    paid = parse_num(get_text(f, "已付金额"))
    addon_desc = get_text(f, "增项情况")
    addon_amt = parse_num(get_text(f, "增项金额"))
    addon_told = yesno(get_text(f, "增项是否事前告知"))
    retainer = yesno(get_text(f, "保持器是否含在报价内"))
    brand = get_text(f, "矫治器品牌")
    auth = yesno(get_text(f, "是否拿到品牌授权卡"))
    method = get_text(f, "矫治方式")
    plan = yesno(get_text(f, "方案书是否写明疗程与副数"))

    if quote is None and paid is None:
        items.append("报价总金额与已付金额均未填写，**费用核查无法开展**")
        return crit, risk, items
    if quote is not None and paid is not None and paid > quote:
        crit.append("已付 %s 超过报价 %s，超出部分无合同依据" % (money(paid), money(quote)))
    elif quote is not None and paid is not None:
        items.append("报价 %s，已付 %s，已付未超报价" % (money(quote), money(paid)))
    elif paid is not None:
        items.append("已付 %s（报价总金额未填写，无法比对）" % money(paid))

    if filled(addon_desc):
        items.append("增项内容：%s" % str(addon_desc)[:100])
        if addon_told is False:
            crit.append("增项未事前告知：方案阶段即可预见的项目（拔牙、支抗钉、扩弓）应含在初始报价内")
        elif addon_told is True:
            items.append("增项已事前告知，需核对是否取得书面确认")
        else:
            risk.append("未填写增项是否事前告知，无法判断告知义务是否履行")
        if addon_amt is not None and addon_amt > 0:
            items.append("增项金额 %s" % money(addon_amt))
            if quote is not None and addon_amt > quote * 0.3:
                crit.append("增项金额 %s 超过报价的 30%%，显著改变交易条件，应重新确认方案与费用"
                            % money(addon_amt))
    else:
        items.append("未申报增项情况；若确有加收，应要求机构出示书面说明")

    if retainer is False:
        risk.append("保持器不含在报价内——这是正畸争议高发点，签约时就应问清并写入合同")
    elif retainer is None:
        risk.append("未填写保持器是否含在报价内")

    n_method = norm(method)
    if "隐形" in n_method or "隐适美" in n_method or "时代天使" in n_method:
        if auth is False:
            crit.append("隐形矫治未取得品牌授权卡：应索要授权证明与官方查询权限，核对品牌与副数")
        elif auth is None:
            risk.append("使用隐形矫治但未填写是否拿到授权卡")
        if not filled(brand):
            risk.append("未填写矫治器品牌——宣传「进口隐形」而不写品牌的，必须要求写明品牌与型号")
        else:
            items.append("矫治器品牌：%s" % brand)

    if plan is False:
        risk.append("方案书未写明疗程与副数，后续「加副数=加钱」没有约束依据")
    elif plan is None:
        risk.append("未填写方案书是否写明疗程与副数")
    return crit, risk, items


def check_finance(f):
    """付款方式与金融风险：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    pay = get_text(f, "付款方式")
    inst = get_text(f, "分期机构")
    rate = parse_num(get_text(f, "分期年化利率"))
    closed = yesno(get_text(f, "机构是否已停业"))
    n_pay = norm(pay)

    if not filled(pay):
        items.append("未填写付款方式，无法判断金融风险")
        return crit, risk, items

    if any(k in n_pay for k in ("分期", "贷款", "医美贷", "花呗", "信用卡分期", "借贷")):
        items.append("采用分期/贷款方式支付，金融合同与服务合同是**相互独立**的")
        risk.append("分期合同独立于服务合同：机构关门或服务不到位，并不自动免除还款义务")
        if rate is None:
            risk.append("未填写分期年化利率，签约前应看清利率、提前终止条款与逾期责任")
        else:
            items.append("分期年化利率 %s%%" % fmt_num(rate))
            if rate >= 24:
                crit.append("分期年化利率 %s%% 过高，应核查放款方资质与利率合规性" % fmt_num(rate))
            elif rate >= 15:
                risk.append("分期年化利率 %s%% 偏高，建议核算总利息后再决定是否提前结清" % fmt_num(rate))
        if filled(inst):
            items.append("分期机构：%s" % inst)
        if closed is True:
            crit.append("机构已停业但仍在还款：一边向放款方与金融监管部门申诉，"
                        "一边向市场监管部门投诉机构，并保留报案权利")
    else:
        items.append("付款方式「%s」，未见明显金融杠杆风险" % pay)

    if closed is True:
        crit.append("机构已停业：立即固定合同、付款凭证与剩余疗程证据，尽早提出书面退费主张")
    elif closed is None:
        risk.append("未填写机构现状，无法判断履约风险")
    return crit, risk, items


def check_progress(f):
    """疗程进度与效果争议：返回 (风险项, 说明列表)。"""
    risk = []
    items = []
    promised = parse_num(get_text(f, "约定疗程月数"))
    done = parse_num(get_text(f, "实际已进行月数"))
    changed = yesno(get_text(f, "是否中途更换医生"))
    told = yesno(get_text(f, "换医生是否事前告知"))
    dispute = yesno(get_text(f, "是否存在效果争议"))
    desc = get_text(f, "效果争议描述")
    consent = yesno(get_text(f, "是否签知情同意书"))

    if promised is not None and done is not None:
        ratio = done / promised if promised else 0
        items.append("约定疗程 %s 个月，已进行 %s 个月，进度约 %s%%" %
                     (fmt_num(promised), fmt_num(done), fmt_num(round(ratio * 100))))
        if done > promised * 1.2:
            risk.append("已进行时间超出约定疗程 20%% 以上，属逾期未完成的履约问题")
    else:
        items.append("约定疗程或已进行月数未填写，**疗程进度无法核算**")

    if changed is True:
        if told is False:
            risk.append("中途更换主治医生且未事前告知——正畸高度依赖医生连续性，"
                        "单方换人条款显失公平")
        elif told is True:
            items.append("已告知更换医生，需核对接手医生的资质与方案延续性")
        else:
            risk.append("更换医生但是否告知未填写")
    elif changed is None:
        items.append("未填写是否更换医生")

    if dispute is True:
        risk.append("存在效果争议：先复印封存病历与影像资料，是否构成医疗损害须以鉴定意见为准")
        if filled(desc):
            items.append("争议描述：%s" % str(desc)[:100])
    elif dispute is None:
        items.append("未填写是否存在效果争议")

    if consent is False:
        risk.append("**未签知情同意书**：正畸属有创医疗行为，未履行告知义务的，机构存在过错")
    elif consent is None:
        risk.append("未填写是否签知情同意书")
    return risk, items


def check_terms(term_text, promo_text):
    """格式条款与宣传承诺核查：返回 (高危项, 风险项)。"""
    crit = []
    risk = []
    t = norm(term_text)
    if filled(term_text):
        bad = {
            "概不退费": "「概不退费」属不合理免除自身责任、排除消费者主要权利，可主张无效",
            "最终解释权": "「最终解释权归机构」是典型的排除消费者权利表述",
            "不承担任何责任": "免除全部责任的条款无效",
            "单方更换": "单方更换主治医生的条款显失公平",
            "概不负责": "免除责任的条款无效",
        }
        for k, v in bad.items():
            if k in t:
                crit.append("合同条款问题：%s" % v)
    p = norm(promo_text)
    if filled(promo_text):
        promo_bad = ("终身免费调整", "包效果", "保证效果", "100%", "绝对", "没有任何风险",
                     "包治", "一次搞定", "无痛")
        for k in promo_bad:
            if k in p:
                risk.append("宣传承诺「%s」属于夸大或无法兑现的表述，应截图留存作为证据" % k)
    return crit, risk


def calc_refund(f, org_reason):
    """参考退费测算：返回 (金额或 None, 说明列表)。"""
    items = []
    paid = parse_num(get_text(f, "已付金额"))
    back = parse_num(get_text(f, "已退金额")) or 0.0
    promised = parse_num(get_text(f, "约定疗程月数"))
    done = parse_num(get_text(f, "实际已进行月数"))
    if paid is None:
        return None, ["未填写已付金额，**参考应退无法测算**"]
    net = paid - back
    if net <= 0:
        items.append("已付 %s，已退 %s，无未退余额" % (money(paid), money(back)))
        return 0.0, items
    items.append("已付 %s − 已退 %s = 未退余额 %s" % (money(paid), money(back), money(net)))
    if org_reason:
        refund = net * 0.8
        items.append("因**机构原因**中断（停业/换医生未告知/方案失误），"
                     "参考应退按未退余额的 80%% 计：%s" % money(round(refund, 2)))
    elif promised and done:
        ratio = min(done / promised, 1.0)
        refund = net * (1 - ratio)
        items.append("按已完成疗程占比 %s%% 扣除已提供服务的对价，参考应退 %s" %
                     (fmt_num(round(ratio * 100)), money(round(refund, 2))))
    else:
        refund = None
        items.append("约定疗程或已进行月数未填写，**参考应退无法按比例测算**，"
                     "需以实际已交付的矫治器副数与已发生处置为准")
    if refund is not None:
        items.append("说明：已交付且不可回收的定制矫治器、已完成的拔牙补牙等处置，"
                     "机构可主张扣除相应成本，最终以协商或裁判为准")
    return refund, items


def check_evidence(f):
    ev = norm(get_text(f, "证据留存情况"))
    need = [
        ("方案书与报价单原件", ("方案", "报价", "计划书", "费用明细")),
        ("合同或知情同意书", ("合同", "同意书", "协议")),
        ("付款凭证与发票", ("付款", "发票", "收据", "转账", "流水")),
        ("矫治器包装与授权卡", ("授权", "包装", "牙套袋", "品牌卡")),
        ("影像资料与病历", ("片", "病历", "cbct", "影像", "取模")),
        ("宣传页面截图", ("宣传", "截图", "广告", "页面")),
        ("沟通记录与录音", ("聊天", "录音", "微信", "沟通")),
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

    org = get_text(f, "机构名称")
    method = get_text(f, "矫治方式")
    demand = get_text(f, "诉求")
    paid = parse_num(get_text(f, "已付金额"))
    quote = parse_num(get_text(f, "报价总金额"))
    closed = yesno(get_text(f, "机构是否已停业"))
    changed = yesno(get_text(f, "是否中途更换医生"))
    told = yesno(get_text(f, "换医生是否事前告知"))

    qual_status, qual_items = check_qual(f)
    q_crit, q_risk, q_items = check_quote(f)
    f_crit, f_risk, f_items = check_finance(f)
    p_risk, p_items = check_progress(f)
    t_crit, t_risk = check_terms(get_text(f, "合同条款摘录"), get_text(f, "宣传承诺摘录"))

    org_reason = (closed is True) or (changed is True and told is False)
    refund, refund_items = calc_refund(f, org_reason)
    have_ev, miss_ev = check_evidence(f)

    core_missing = paid is None and quote is None
    if not core_missing:
        crit.extend(q_crit)
        crit.extend(f_crit)
        crit.extend(t_crit)
        if qual_status == "不通过":
            crit.append("资质核查未通过：见机构与医师资质核查")
        risk.extend(q_risk)
        risk.extend(f_risk)
        risk.extend(p_risk)
        risk.extend(t_risk)
        if qual_status == "待补正":
            risk.append("机构与医师资质未核实，需在当地卫健部门官网查询后补录")
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
    rep.append("- 就诊机构：%s" % (org if filled(org) else "未填写"))
    rep.append("- 矫治方式：%s" % (method if filled(method) else "未填写"))
    rep.append("- 报价：%s；已付：%s" % (money(quote) if quote is not None else "未填写",
                                 money(paid) if paid is not None else "未填写"))
    rep.append("- 资质核查：%s" % qual_status)
    rep.append("- 参考应退：%s" % (money(round(refund, 2)) if refund is not None else "无法测算"))
    rep.append("- 高危项 %d 项 / 风险项 %d 项" % (len(crit), len(risk)))
    rep.append("- **总体结论：%s**" % verdict)
    rep.append("")

    # 2 资质
    rep.append("## 机构与医师资质核查")
    rep.append("")
    for it in qual_items:
        rep.append("- %s" % it)
    rep.append("- 查询入口：当地卫生健康委员会官网「医疗机构查询」「医师执业信息查询」；"
               "主体一致性用国家企业信用信息公示系统核对")
    rep.append("")

    # 3 报价与增项
    rep.append("## 报价与增项核查")
    rep.append("")
    for it in q_items:
        rep.append("- %s" % it)
    for c in q_crit:
        rep.append("- **%s**" % c)
    for r in q_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 4 付款
    rep.append("## 付款方式与金融风险")
    rep.append("")
    for it in f_items:
        rep.append("- %s" % it)
    for c in f_crit:
        rep.append("- **%s**" % c)
    for r in f_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 5 疗程与效果
    rep.append("## 疗程进度与效果争议")
    rep.append("")
    for it in p_items:
        rep.append("- %s" % it)
    for r in p_risk:
        rep.append("- %s" % r)
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
        rep.append("- 主要证据类别已覆盖，仍需确认原件与原始载体完整")
    rep.append("")
    rep.append("固定要点：病历与影像资料要复印封存；矫治器包装不要丢弃；"
               "宣传页面要截图保存原始链接与时间。")
    rep.append("")

    # 7 维权路径
    rep.append("## 维权路径")
    rep.append("")
    rep.append("| 层级 | 找谁 | 适用 |")
    rep.append("| --- | --- | --- |")
    rep.append("| 1 | 机构医务科/客服书面协商 | 全部情形，先书面留痕 |")
    rep.append("| 2 | 第三方平台介入 | 经平台下单的 |")
    rep.append("| 3 | 12315 投诉 | 收费争议、虚假宣传、格式条款 |")
    rep.append("| 4 | 当地卫生健康行政部门 | 无证执业、医师执业地点不符、超范围执业 |")
    rep.append("| 5 | 医疗纠纷人民调解委员会 | 效果争议、医疗损害 |")
    rep.append("| 6 | 医疗损害鉴定 → 法院起诉 | 造成实际损害、金额较大 |")
    rep.append("")
    if yesno(get_text(f, "是否已投诉")) is True:
        rep.append("- 已申报投诉，请保留受理编号与处理时限")
    else:
        rep.append("- 尚未投诉：收费争议走 12315 与市场监管，资质问题走卫健部门，"
                   "造成人身损害走鉴定与司法途径，三条可并行")
    rep.append("")

    # 8 待办
    rep.append("## 待办补正动作")
    rep.append("")
    if core_missing:
        todo.append("补齐「报价总金额」与「已付金额」——这是出具任何结论的前提")
    if qual_status != "有风险":
        todo.append("到当地卫健部门官网核对机构执业许可与医师执业地点，并截图留存")
    if not filled(get_text(f, "增项情况")) and not filled(get_text(f, "增项金额")):
        todo.append("核实是否存在未在初始方案中写明的加收项目及金额")
    if not filled(get_text(f, "约定疗程月数")) or not filled(get_text(f, "实际已进行月数")):
        todo.append("补齐约定疗程月数与实际已进行月数，用于测算参考应退")
    for m in miss_ev:
        todo.append("补齐证据：%s" % m)
    if not filled(get_text(f, "合同条款摘录")):
        todo.append("调取合同原件，摘录退费、变更医生、违约责任条款")
    if not filled(demand):
        todo.append("明确诉求：退还未完成部分费用 / 撤销不合理增项 / 转诊继续治疗 / 赔偿")
    todo.append("书面提出退费申请并用 EMS 寄送，保留面单或签收凭证")
    if not todo:
        todo.append("信息已较完整，可直接进入协商，协商不成按维权路径升级")
    for i, t in enumerate(todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见与临床诊断，"
               "最终以卫生健康主管部门、市场监管部门及司法机关认定为准。")
    rep.append("- 「参考应退」是按疗程占比或机构过错推算的**参考值**，不是法定结论。")
    rep.append("- 是否构成医疗损害，须经医疗损害鉴定或司法鉴定认定，不依主观感受判断。")
    rep.append("- 本技能不提供任何代办投诉、代写诉状或代为谈判服务。")

    return "\n".join(rep), verdict, crit + risk, todo


def main():
    ap = argparse.ArgumentParser(description="牙齿矫正正畸花费与套路核查")
    ap.add_argument("md", nargs="?", default="样例.md", help="采集表 Markdown 路径")
    ap.add_argument("--input", dest="input", default=None)
    ap.add_argument("--base", default=None, help="基准日期 YYYY-MM-DD")
    ap.add_argument("--out", default="", help="报告输出路径")
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

    if parse_num(get_text(f, "已付金额")) is None and parse_num(get_text(f, "报价总金额")) is None:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
