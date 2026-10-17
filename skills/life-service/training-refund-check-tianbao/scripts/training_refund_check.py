#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""培训退费核算与维权。

用法：
  python training_refund_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python training_refund_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失（给提示串，不崩、不抛异常）。
"""
import argparse
import json
import re
import sys
from datetime import date

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")
PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "(", "（"]

# ------------------------------------------------------------------ 通用工具
def norm(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("：", ":").replace("（", "(").replace("）", ")")
    s = s.replace("，", ",").replace("。", ".")
    s = re.sub(r"\s+", "", s)
    return s.strip()


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_kv(text):
    """解析 markdown 表格行与 '字段：值' 行。"""
    kv = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                k, v = cells[0], "|".join(cells[1:]).strip()
                if set(k) <= set("-: ") or set(v) <= set("-: "):
                    continue
                if k and k not in kv:
                    kv[k] = v
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k, v = parts[0].strip(), parts[1].strip()
                if k and k not in kv:
                    kv[k] = v
    return kv


def get_text(kv, aliases):
    """最长别名优先匹配；空值不参与匹配，避免被别的字段的空行抢走。"""
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if norm(k) == na and filled(v):
                return v.strip()
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if na in norm(k) and filled(v):
                return v.strip()
    return ""


def filled(v):
    v = ("" if v is None else str(v)).strip()
    if not v:
        return False
    if UNFILLED_MARK.search(v):
        return False
    for w in PLACEHOLDER_WORDS:
        if v.startswith(w):
            return False
    return True


def core(v):
    """去掉括号内的补充说明，再压掉空白，用于'是/否'判定。"""
    n = norm(v)
    n = re.sub(r"[（(].*?[)）]", "", n)
    return n


def yes(v):
    n = core(v)
    if n in ("有", "是", "已经", "已", "已完成", "已调取", "true", "yes"):
        return True
    return bool(re.match(r"^(是|有|已经)", n))


def no(v):
    n = core(v)
    if n in ("无", "否", "没有", "未", "未做", "false", "no"):
        return True
    return bool(re.match(r"^(否|无|没|未)", n))


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知")


def parse_num(s):
    if not s:
        return None
    s = str(s).replace(",", "").replace("，", "")
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def fmt_num(x):
    if x is None:
        return "—"
    if abs(x - round(x)) < 1e-6:
        return str(int(round(x)))
    return ("%.2f" % x).rstrip("0").rstrip(".")


def parse_date(s):
    if not s:
        return None
    m = DATE_RE.search(str(s))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def base_date(s):
    d = parse_date(s or "")
    return d or date.today()


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except Exception:
        return d.replace(year=d.year + n, day=1)


# ------------------------------------------------------------------ 课时单价
def unit_price(f):
    """课时单价认定。返回 (price, basis, note)。"""
    paid = f["paid"]
    cp = f["contract_price"]
    lp = f["list_price"]
    total = f["total_lessons"] or 0
    bonus = f["bonus_lessons"] or 0
    div_total = total + bonus
    implied = (paid / div_total) if (paid is not None and div_total > 0) else None

    if cp is not None and cp > 0:
        price = cp
        basis = "合同约定的课时单价"
        note = "已消耗课时费按合同约定的课时单价 %s 元/课时计算。" % fmt_num(cp)
        if implied is not None and cp > implied + 1e-6:
            note += ("（合同单价 %s 元/课时高于优惠后折算单价 %s 元/课时；"
                     "若该课程系优惠价购入，可主张按优惠后折算单价计扣。）"
                     % (fmt_num(cp), fmt_num(implied)))
    elif implied is not None:
        price = implied
        basis = "优惠后折算单价"
        note = ("合同未写课时单价或属优惠价购买，按实付总额 %s 元 ÷ (购买课时 %s ＋ 赠课 %s) "
                "＝ %s 元/课时计已消耗课时费。赠课不单独计价，但摊薄折算单价。"
                % (fmt_num(paid), fmt_num(total), fmt_num(bonus), fmt_num(price)))
    else:
        return None, "未认定", (
            "实付总额与课时数任一缺失，无法认定课时单价。"
            "请补填实付总额、购买课时与赠送课时。")

    if lp is not None and lp > 0 and lp > price + 1e-6:
        note += ("机构若改按原价 %s 元/课时扣款，对己不利，不应采纳。"
                 % fmt_num(lp))
    return price, basis, note


# ------------------------------------------------------------------ 金额测算
def calc_amount(f):
    rows = []
    s = {"refund": None, "upper": None, "lower": None, "pen": None}
    paid = f["paid"]
    if paid is None:
        rows.append(("实付总额", "待补正",
                     "未填实付总额（已交费用金额）。退费以实付总额为基数，"
                     "请补培训合同、付款凭证与发票。"))
        return rows, s

    price, basis, pnote = unit_price(f)
    used = f["used_lessons"] or 0
    s["paid"] = paid
    s["price"] = price
    s["used_lessons"] = used
    s["basis"] = basis
    rows.append(("实付总额", "通过",
                 "实付总额 %s 元作为退费基数（含分期/培训贷支付的部分同样计入）。"
                 % fmt_num(paid)))

    if price is None:
        rows.append(("已消耗课时费", "待补正", "课时单价未认定：" + pnote))
        rows.append(("建议退费金额", "待补正", "关键项缺失，暂无法核算。"))
        return rows, s

    used_amt = price * used
    rows.append(("已消耗课时费", "通过",
                 "已消耗 %s 课时 × %s 元/课时（%s）＝ %s 元。"
                 % (fmt_num(used), fmt_num(price), basis, fmt_num(used_amt))))

    total = (f["total_lessons"] or 0) + (f["bonus_lessons"] or 0)
    if total > 0 and used > total:
        rows.append(("已消耗课时", "有风险",
                     "已消耗 %s 课时超过购买加赠课合计 %s 课时，请核对考勤记录与课时余额截图。"
                     % (fmt_num(used), fmt_num(total))))

    # 教材教辅物品费
    mat = f["material_fee"]
    if mat is None or mat <= 0:
        mat_amt = 0.0
        rows.append(("教材教辅物品费", "待补正",
                     "未填教材教辅物品费。已发放且不可回收的教材、服装、器材可扣除（须事先约定），"
                     "已发放但可回收的应先退货再结算，未事先约定的不能当然扣除。"))
    else:
        agreed = yes(f["material_agreed"])
        ret_no = no(f["material_returnable"])
        ret_yes = yes(f["material_returnable"])
        if agreed and ret_no:
            mat_amt = mat
            rows.append(("教材教辅物品费", "通过",
                         "教材物品费 %s 元已事先约定且已发放不可回收，可计入扣款。"
                         % fmt_num(mat)))
        elif agreed and ret_yes:
            mat_amt = 0.0
            rows.append(("教材教辅物品费", "有风险",
                         "教材物品费 %s 元虽事先约定但可退货/可回收，应先退货再结算差额，"
                         "不宜整笔扣除。" % fmt_num(mat)))
        elif not agreed:
            mat_amt = 0.0
            rows.append(("教材教辅物品费", "有风险",
                         "教材物品费 %s 元未事先约定，不能当然扣减；"
                         "可要求返还未使用部分，协商不成的不计入本次退费计算。" % fmt_num(mat)))
        else:
            mat_amt = 0.0
            rows.append(("教材教辅物品费", "待补正",
                         "教材物品费 %s 元：是否事先约定、能否回收未填，暂不计入扣款。" % fmt_num(mat)))
    s["mat"] = mat_amt

    # 违约金
    rate = f["penalty_rate"]
    pa = f["penalty_amt"]
    loss = f["loss_amt"]
    org_claim = None
    if rate is not None and paid is not None:
        org_claim = paid * rate / 100.0
    elif pa is not None:
        org_claim = pa
    s["org_claim"] = org_claim
    if org_claim is None:
        s["pen"] = None
        rows.append(("违约金", "待补正",
                     "未填约定违约金比例或机构主张金额。机构主张违约金的，须以**实际损失**为限"
                     "并承担举证责任；请补填'实际损失金额'以便核定。"))
    elif loss is None:
        s["pen"] = org_claim
        rows.append(("违约金", "有风险",
                     "机构按%s 主张违约金约 %s 元，但未说明实际损失。违约金应以实际损失为限、"
                     "由机构举证；请补填实际损失金额后重新核算（参见第四节）。"
                     % (("约定比例 %s%%" % fmt_num(rate)) if rate is not None else "约定金额",
                        fmt_num(org_claim))))
    elif org_claim > loss + 1e-6:
        s["pen"] = loss
        rows.append(("违约金", "有风险",
                     "机构主张 %s 元高于实际损失 %s 元，超出部分可主张调减；"
                     "司法实践对过高违约金通常不全支持，参考区间为实付总额 20%%~30%%，"
                     "超出该区间且与实际损失明显不符的，可请求调减。"
                     % (fmt_num(org_claim), fmt_num(loss))))
    else:
        s["pen"] = loss
        rows.append(("违约金", "通过",
                     "机构主张 %s 元未超过实际损失 %s 元，按 %s 元计。"
                     % (fmt_num(org_claim), fmt_num(loss), fmt_num(loss))))

    # 退费
    if s["pen"] is None or paid is None:
        rows.append(("建议退费金额", "待补正", "关键项未定，暂无法给出确定金额。"))
        return rows, s
    base = paid - used_amt - mat_amt
    rec = base - s["pen"]
    s["refund"] = rec
    s["upper"] = base
    s["lower"] = base - org_claim
    rows.append(("建议退费金额", "通过",
                 "退费＝实付总额 %s − 已消耗课时费 %s − 教材物品费 %s − 违约金 %s ＝ **%s 元**。"
                 % (fmt_num(paid), fmt_num(used_amt), fmt_num(mat_amt),
                    fmt_num(s["pen"]), fmt_num(rec))))
    rows.append(("退费区间", "通过",
                 "下限 %s 元（按机构主张违约金全额计），上限 %s 元（按违约金以实际损失为限计）；"
                 "若按机构主张的原价课时单价扣款，退费还会更低，不应采纳。"
                 % (fmt_num(s["lower"]), fmt_num(s["upper"]))))

    if f["list_price"] is not None and price and f["list_price"] > price + 1e-6:
        wrong = paid - f["list_price"] * used - mat_amt - s["pen"]
        rows.append(("机构原价比对", "有风险",
                     "若按机构主张的原价 %s 元/课时扣已消耗课时费，退费将降至 %s 元，"
                     "明显不合理，不应采纳。" % (fmt_num(f["list_price"]), fmt_num(wrong))))
    return rows, s


# ------------------------------------------------------------------ 各项核查
def checks_price(f):
    price, basis, note = unit_price(f)
    rows = []
    if price is None:
        rows.append(("课时单价认定", "待补正", note))
        return rows
    rows.append(("课时单价认定", "通过", note))
    lp = f["list_price"]
    if lp is not None and lp > 0 and lp > price + 1e-6:
        rows.append(("不按原价扣款", "通过",
                     "已消耗课时按 %s 元/课时计，而非机构主张的原价 %s 元/课时——"
                     "原价临时抬高于实际成交价，不能用于扣减退费。"
                     % (fmt_num(price), fmt_num(lp))))
    bonus = f["bonus_lessons"] or 0
    if bonus > 0:
        rows.append(("赠课摊薄单价", "通过",
                     "赠课 %s 课时不单独计价，但摊薄折算单价（总额÷(购买课时 %s ＋赠课 %s)），"
                     "有利于降低已消耗课时费。"
                     % (fmt_num(bonus), fmt_num(f["total_lessons"] or 0), fmt_num(bonus))))
    return rows


CLAUSE_WORDS = ("概不退费", "开课后不退", "一经报名", "不退费", "费用不退", "不得退费", "一律不退")


def checks_penalty(f):
    rows = []
    cl = f["clause"]
    if not filled(cl):
        rows.append(("格式条款核查", "待补正",
                     "未摘录合同中的不退费/违约金条款原文。'概不退费''开课后一概不退'等属格式条款，"
                     "请拍照或抄录原文（含加黑加粗部分）后重跑。"))
    else:
        hits = [w for w in CLAUSE_WORDS if w in cl]
        if hits:
            rows.append(("格式条款核查", "不通过",
                         "合同含有「%s」类表述。该类排除消费者主要权利、加重消费者责任的"
                         "不公平不合理条款**无效**，机构不能据此拒绝退费或扣费。"
                         % "、".join(hits)))
        else:
            rows.append(("格式条款核查", "通过",
                         "合同未发现'概不退费'类绝对化表述，退费限制需看具体违约责任条款。"))
    rp = f["org_reply"]
    if filled(rp) and (any(w in rp for w in CLAUSE_WORDS) or "合同写了" in rp):
        rows.append(("机构口径", "有风险",
                     "机构以「%s」回应。该理由属单方声明而非法律依据；"
                     "可要求其出具书面退费方案与计算明细，并说明条款依据。"
                     % rp[:24]))
    return rows


def checks_license(f):
    rows = []
    lic = f["license"]
    if yes(lic):
        rows.append(("办学许可", "通过",
                     "机构公示了办学许可/办学许可证。请留存许可照片，并核对许可内容与所报课程是否一致。"))
    elif no(lic):
        rows.append(("办学许可", "不通过",
                     "该机构无办学许可证（或未公示许可）。无办学许可或超范围经营的，"
                     "属于违法办学，既是退费的有力抓手，也可同步向主管部门举报。"))
    else:
        rows.append(("办学许可", "待补正",
                     "未填是否有办学许可证。无许可或超范围经营是可主张全额退费的有力情形。"))

    tt = f["train_type"] or ""
    stage = f["stage"] or ""
    k12 = any(k in stage for k in ("义务教育", "小学", "初中", "高中", "中小学", "K12", "k12"))
    subject = any(k in tt for k in ("学科", "文化课", "语文", "数学", "英语", "物理", "化学", "生物", "中考", "高考"))

    if subject and k12:
        hc = f["holiday_class"]
        if yes(hc):
            rows.append(("双减—培训时间", "不通过",
                         "面向义务教育阶段学生的学科类培训机构，不得占用国家法定节假日、休息日"
                         "及寒暑假期组织培训；已在该时段排课或上课的属违规，可直接作为退费理由。"))
        elif no(hc):
            rows.append(("双减—培训时间", "通过",
                         "未在国家法定节假日、休息日及寒暑假期安排学科类培训，符合双减关于培训时间的要求。"))
        else:
            rows.append(("双减—培训时间", "待补正",
                         "未填是否占用国家法定节假日、休息日或寒暑期排课。这是双减的硬性要求，务必核实。"))

    span = f["charge_span"]
    lessons = f["total_lessons"]
    over = []
    if span is not None and span > 3:
        over.append("一次性收费超过 3 个月（实际约 %s 个月）" % fmt_num(span))
    if lessons is not None and lessons > 60:
        over.append("一次性收费超过 60 课时（共 %s 课时）" % fmt_num(lessons))
    if over:
        rows.append(("预收费监管", "不通过",
                     "存在%s。一次性收费不得超过 3 个月或 60 课时（预收费监管要求，"
                     "各地口径趋同），**超期超额收费本身即属违规**，这是退费谈判的重要抓手——"
                     "可先主张违规收费的处理，再主张退费。" % "、".join(over)))
    elif (subject and k12) or span is not None or lessons is not None:
        rows.append(("预收费监管", "通过",
                     "一次性收费未超过 3 个月且未超过 60 课时，符合预收费监管要求。"))
    else:
        rows.append(("预收费监管", "待补正",
                     "未填一次性收费跨度与购买课时，无法判断是否超过 3 个月或 60 课时。"))
    return rows


def _flag(name, v, on, off, extra_hit=None):
    """通用布尔型核查项：是→不通过；否→通过；空→待补正。"""
    if yes(v):
        return (name, "不通过", on)
    if no(v):
        return (name, "通过", off)
    if filled(v):
        return (name, "待补正",
                "填写不明确（%s）。%s请按'是/否'重填。" % (v, extra_hit or ""))
    return (name, "待补正", "本项未填，暂不认定。%s" % (extra_hit or "请按'是/否'填写。"))


def checks_breach(f):
    rows = []
    rows.append(_flag(
        "未按约定开课", f["not_started"],
        "机构未按约定开课（约定的开课日期已过仍未开班或长期未开课），可主张全额退费并主张相应赔偿。",
        "已按约定开课，此项不构成退费理由。"))
    rows.append(_flag(
        "长期停课", f["long_stop"],
        "机构长期停课、课程长期不开，属未按约定提供培训服务，可主张解除合同并要求退费。",
        "课程正常进行，未出现长期停课。"))
    rows.append(_flag(
        "师资与承诺不符", f["teacher_mismatch"],
        "师资与招生承诺严重不符（承诺名师、实际为无资质人员授课），属违约，"
        "可主张退费并要求补足差异部分的损失。",
        "师资与承诺基本一致。"))
    rows.append(_flag(
        "虚假宣传（保过/包就业/名师）", f["false_promo"],
        "招生宣传含'保过''包就业''名师授课'等承诺且未兑现：虚假宣传可作为主张退费与赔偿的依据，"
        "宣传页、聊天承诺、录音都是证据。",
        "未出现保过/包就业/名师类宣传承诺。"))
    rows.append(_flag(
        "单方面变更上课地点", f["venue_change"],
        "机构单方面变更上课地点致上课明显不便，属单方变更合同，学员有权解约并要求退费。",
        "上课地点未变更。"))
    rows.append(_flag(
        "消费者因重大疾病或不可抗力无法继续", f["stop_reason"],
        "存在重大疾病、意外或不可抗力致无法继续学习的情形且有证明材料，"
        "可主张解除合同并退还未消耗部分。",
        "无重大疾病或不可抗力情形。"))

    st = f["org_status"] or ""
    if any(k in st for k in ("停业", "跑路", "失联", "关门", "倒闭", "迁址", "搬迁", "闭店")):
        rows.append(("机构现状", "不通过",
                     "机构现状为「%s」。机构停业、跑路、迁址致你明显不便的，可主张全额或高比例退费；"
                     "单方迁至明显不便地点的，学员有权解除合约并要求退费。" % st))
    elif filled(st):
        rows.append(("机构现状", "通过", "机构目前为「%s」，尚在正常经营。" % st))
    else:
        rows.append(("机构现状", "待补正",
                     "未填机构现状（正常经营/停业/跑路失联/迁址）。机构跑路、迁址是最有力的退费情形。"))

    hits = [r[0] for r in rows if r[1] == "不通过"]
    if hits:
        rows.append(("可主张的退费力度", "有风险",
                     "已触发 %d 项可全额或高比例退费的情形（%s）。出现其中任一情形，"
                     "通常可主张全额或高比例退费，而不只是扣除已消耗课时费。"
                     % (len(hits), "、".join(hits))))
    else:
        rows.append(("可主张的退费力度", "待补正",
                     "尚未填到明确的机构违约/违规情形：停业跑路、未按约开课或长期停课、师资严重不符、"
                     "虚假宣传、无办学许可或超范围经营、单方变更上课地点、重大疾病或不可抗力。"))
    return rows


def checks_loan(f):
    rows = []
    if not filled(f["loan"]):
        rows.append(("培训贷/分期", "待补正",
                     "是否办理培训贷或分期未填。**培训贷要特别当心**：退费官司与还贷是两件事，"
                     "绝不能靠'不还钱'来维权，逾期会直接影响征信。"))
        return rows
    if not yes(f["loan"]):
        rows.append(("培训贷/分期", "通过",
                     "未办理培训贷或分期，退费即减损，不涉及贷款与征信问题。"))
        return rows

    ln = f["loan_notice"]
    if no(ln):
        rows.append(("机构告知义务", "有风险",
                     "机构办理培训贷前未尽告知义务、未说明还款义务与风险。机构与贷款方串通性推销、"
                     "或未尽告知义务的，可主张机构承担相应责任，但这不等于可以停止还款。"))
    elif yes(ln):
        rows.append(("机构告知义务", "通过", "机构已告知培训贷风险与还款义务。"))
    else:
        rows.append(("机构告知义务", "待补正", "机构是否告知培训贷风险未填。"))

    st = f["loan_status"] or ""
    if any(k in st for k in ("逾期", "违约", "欠款", "未还", "断供")):
        rows.append(("还款状态", "不通过",
                     "贷款已出现逾期/欠款。**先保征信、再打官司**：逾期记录会上传征信，"
                     "与机构最终能否退费无关。请立即书面联系贷款方协商还款或停息挂账，"
                     "同时向机构主张退费并书面转告贷款方争议情况。"))
    elif any(k in st for k in ("已放款", "已放贷", "放贷", "已审批", "在还")) or filled(st):
        rows.append(("还款状态", "有风险",
                     "贷款已放款、机构拿到的是贷款资金而非你的自有资金。请向贷款方书面说明"
                     "「款项支付给了培训机构、机构退费/停业期间请求暂停扣款或协商还款」，"
                     "并保留回执；同时向机构主张退费，退到位的部分及时用于结清贷款。"))
    if not filled(st):
        rows.append(("贷款当前状态", "待补正", "未填贷款状态（未放款/已放款在还/已结清/已逾期）。"))

    lc = f["loan_contact"]
    if yes(lc):
        rows.append(("与贷款方沟通", "通过", "已与贷款方书面沟通，这是控制征信影响的关键一步。"))
    else:
        rows.append(("与贷款方沟通", "待补正",
                     "尚未与贷款方书面沟通。请立即致电/书面联系贷款方说明争议，"
                     "要求暂停自动扣款或协商还款计划，并索要沟通记录。"))
    return rows


def path_order(f):
    return [
        ("第 1 步", "书面交涉：向机构前台/课程顾问/收银提交书面退费申请，"
                    "明确要求其出具**退费方案与计算明细**（课时单价依据、已消耗课时、教材费、违约金），"
                    "写明退款金额与期限，索要回执或书面回复（微信/短信/邮件均可，注明时间）"),
        ("第 2 步", "向机构**总部/总校或品牌方**书面投诉——很多校区只是加盟店，"
                    "总部才是真正的收费主体与责任方；同时向机构注册地的市场监管部门反映"),
        ("第 3 步", "向主管部门投诉：学科类/学历考培向**教育**主管部门，"
                    "职业技能类（人社许可）向**人力资源社会保障**主管部门；"
                    "同步向**市场监督管理（12315）**、市民热线 **12345**、消费者协会反映；"
                    "涉及预收费超期超额、无办学许可的把这两点写进投诉正文"),
        ("第 4 步", "合同订有**仲裁条款**的，按约定的仲裁机构申请仲裁；没有仲裁条款的直接进入诉讼"),
        ("第 5 步", "涉案金额小的走**小额诉讼**（标的额符合当地小额诉讼标准的实行一审终审，"
                    "流程快、成本低、费用低）；同类学员多的做**集体维权/联名投诉**，"
                    "提交共同投诉材料效果明显更好"),
        ("第 6 步", "起诉主张：解除培训合同、返还剩余培训费用、支付资金占用利息，"
                    "并承担合理维权成本；有转移财产迹象的可申请财产保全"),
    ]


def todo_list(f, results, s):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    extra.append(("书面索要退费明细", "向机构书面要求出具退费方案与计算明细，索要回执"))
    extra.append(("固定课时证据", "截图保存app/小程序里的课时余额、课程表与考勤记录并录屏"))
    if yes(f["loan"]):
        extra.append(("先保征信", "书面联系贷款方说明争议，协商暂停扣款或还款计划，切勿直接停还"))
        extra.append(("收集培训贷证据", "培训贷合同、放款凭证、推销聊天记录、机构未告知风险的材料"))
    if not yes(f["loan_contact"]) and yes(f["loan"]):
        extra.append(("与贷款方沟通", "立即致电贷款方并要求书面确认，保留通话录音与工单号"))
    if not yes(f["negotiated"]):
        extra.append(("提交书面退费申请", "按上述第 1 步提交，保留送达凭证"))
    if (f["material_fee"] or 0) > 0 and yes(f["material_agreed"]) and not no(f["material_returnable"]):
        extra.append(("核对教材可否退货", "能退的先退货再结算，不能整笔扣除"))
    if yes(f["false_promo"]) or yes(f["teacher_mismatch"]):
        extra.append(("固化宣传证据", "宣传页、保过/包就业承诺的聊天与录音、师资名单，公证或录屏保全"))
    if not yes(f["license"]):
        extra.append(("举报违法办学", "向教育/人社主管部门举报无许可或超范围经营，同步提交给 12345"))
    extra.append(("时效倒计时", "民事诉讼时效 3 年，自知道或应当知道权利受损之日起算，别拖"))
    seen = set()
    out = []
    for n, st in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        out.append((n, st))
    return out


# ------------------------------------------------------------------ 报告
def render(f, results, s, steps, todos, today, deadline_txt):
    L = []
    L.append("# 培训退费核算与维权报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 培训机构：%s" % (f["org"] or "未填"))
    L.append("- 培训类型：%s" % (f["train_type"] or "未填"))
    L.append("- 学员学段：%s" % (f["stage"] or "未填"))
    L.append("")

    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在明确违规/违约点，可主张退费**。")
    elif risk:
        L.append("**判定：存在风险点，需补正后主张**。")
    else:
        L.append("**判定：未发现明显违规点；若协商不成，按第八段路径推进**。")
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(todo))
    L.append("")
    if s.get("refund") is not None:
        L.append("- **建议退费金额：%s 元**（口径区间 %s 元 ~ %s 元，见第二节）。"
                 % (fmt_num(s["refund"]), fmt_num(s["lower"]), fmt_num(s["upper"])))
        L.append("")
    for name, _st, msg in bad[:6]:
        L.append("- **%s**：%s" % (name, msg.replace("**", "")))
    for name, _st, msg in risk[:6]:
        L.append("- %s：%s" % (name, msg.replace("**", "")))
    L.append("")

    titles = ["二、退费金额核算", "三、课时单价认定", "四、格式条款与违约金",
              "五、办学许可与双减预收费", "六、机构违约情形", "七、培训贷与征信风险"]
    for (title, rows), t in zip(results, titles):
        if not rows:
            continue
        L.append("## %s" % t)
        L.append("")
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for name, state, msg in rows:
            L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
        L.append("")

    L.append("## 八、交涉路径与时效")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")
    L.append("| 事项 | 期限 |")
    L.append("|---|---|")
    L.append("| 时效倒计时 | %s |" % deadline_txt)
    L.append("| 民事诉讼时效 | 3 年，自知道或应当知道权利被侵害及义务人之日起算 |")
    L.append("| 向主管部门投诉举报 | 无硬性前置期限，但建议尽早；拖久会导致证据灭失、主体消失 |")
    L.append("| 贷款还款 | 按贷款合同约定，逾期影响征信，不能因退费争议停还 |")
    L.append("| 协商交涉 | 建议 7~15 日内完成一轮书面交涉，再走主管部门 |")
    L.append("")

    L.append("## 九、待办补正动作")
    L.append("")
    if not todos:
        L.append("当前未发现必须补正的事项。")
    else:
        L.append("| 动作 | 状态 |")
        L.append("|---|---|")
        for n, st in todos:
            L.append("| %s | %s |" % (n, st))
    L.append("")

    L.append("## 边界与纪律")
    L.append("")
    L.append("- 本结果依通用规则整理，**不替代律师意见**；最终以主管部门认定与司法机关裁判为准。")
    L.append("- 培训退费涉及的地方口径差异较大（预收费监管细则、退费比例、可退范围各地不同），"
             "**一律以当地教育/人社主管部门、市场监督管理部门口径为准**。")
    L.append("- 违约金是否调减、能否全额退费，**由司法机关认定**，本表只给测算口径与证据方向，"
             "不对结果作承诺。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 涉及培训贷的，违约记录影响征信，任何'靠不还钱维权'的做法都请先与贷款方书面协商。")
    return "\n".join(L) + "\n"


def to_json(f, results, s, todos, today):
    bad = [r[0] for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r[0] for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r[0] for _t, rows in results for r in rows if r[1] == "待补正"]
    if bad:
        concl = "有风险"
    elif risk:
        concl = "有风险"
    elif todo:
        concl = "待补正"
    else:
        concl = "通过"
    d = {
        "核查日期": today.isoformat(),
        "培训机构": f["org"],
        "培训类型": f["train_type"],
        "结论": concl,
        "风险项": bad + risk,
        "待办": todo,
        "建议退费金额": s.get("refund"),
        "退费口径区间": [s.get("lower"), s.get("upper")],
        "课时单价": s.get("price"),
        "课时单价依据": s.get("basis", ""),
        "待办动作": [{"动作": n, "状态": st} for n, st in todos],
    }
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = read_text(args.input)
    kv = build_kv(text)
    today = base_date(args.base)

    f = {
        "train_type": get_text(kv, ["培训类型", "课程类型", "培训种类"]),
        "org": get_text(kv, ["培训机构", "机构名称", "办学主体"]),
        "stage": get_text(kv, ["学员学段", "学生学段", "学员阶段", "学段"]),
        "contract_date": get_text(kv, ["合同签订日期", "签合同日期", "合同签订时间"]),
        "paid": parse_num(get_text(kv, ["实付总额", "已交费用金额", "实际支付总额", "交费金额"])),
        "contract_price": parse_num(get_text(kv, ["合同约定的课时单价", "约定课时单价"])),
        "total_lessons": parse_num(get_text(kv, ["课程总课时", "购买课时", "合同约定课时总数"])),
        "bonus_lessons": parse_num(get_text(kv, ["赠送课时", "赠课课时", "赠课"])),
        "used_lessons": parse_num(get_text(kv, ["已消耗课时", "已上课时", "已消耗课时数"])),
        "list_price": parse_num(get_text(kv, ["机构主张的原价课时单价", "原价课时单价", "机构主张单价"])),
        "material_fee": parse_num(get_text(kv, ["教材教辅物品费金额", "教材费金额", "教材教辅费"])),
        "material_agreed": get_text(kv, ["教材费是否事先约定", "教材费事先约定"]),
        "material_returnable": get_text(kv, ["教材物品能否退还", "教材物品是否可回收"]),
        "penalty_rate": parse_num(get_text(kv, ["约定违约金比例", "违约金比例", "约定违约金比例(%)"])),
        "penalty_amt": parse_num(get_text(kv, ["机构主张违约金金额", "机构主张违约金"])),
        "loss_amt": parse_num(get_text(kv, ["实际损失金额", "实际损失"])),
        "charge_span": parse_num(get_text(kv, ["一次性收费跨度（月）", "一次性收费对应月数", "收费跨度"])),
        "license": get_text(kv, ["有无办学许可证", "办学许可证"]),
        "holiday_class": get_text(kv, ["是否存在节假日或寒暑假上课", "是否在节假日培训", "寒暑假上课情况"]),
        "org_status": get_text(kv, ["机构现状", "办学机构现状"]),
        "not_started": get_text(kv, ["是否未按约定开课", "未按约定开课"]),
        "long_stop": get_text(kv, ["是否长期停课", "长期停课情况"]),
        "teacher_mismatch": get_text(kv, ["师资是否与承诺不符", "师资与承诺是否不符"]),
        "false_promo": get_text(kv, ["是否存在虚假宣传承诺", "虚假宣传情况", "虚假宣传"]),
        "venue_change": get_text(kv, ["是否单方面变更上课地点", "上课地点变更"]),
        "stop_reason": get_text(kv, ["消费者停止上课原因", "停止上课原因"]),
        "loan": get_text(kv, ["是否办理培训贷或分期", "是否办理培训贷", "培训贷情况"]),
        "loan_notice": get_text(kv, ["机构是否事先告知培训贷风险", "是否告知培训贷风险"]),
        "loan_status": get_text(kv, ["培训贷当前状态", "贷款还款状态"]),
        "loan_contact": get_text(kv, ["是否已与贷款方书面沟通", "与贷款方沟通情况"]),
        "clause": get_text(kv, ["合同中的不退费条款", "概不退费条款", "不退费条款"]),
        "negotiated": get_text(kv, ["是否已书面交涉", "书面交涉情况"]),
        "org_reply": get_text(kv, ["机构回应", "对方回应"]),
        "arbitration": get_text(kv, ["合同是否含仲裁条款", "是否有仲裁条款"]),
        "issue_date": get_text(kv, ["发现异常的日期", "首次发现问题日期"]),
        "evidence": get_text(kv, ["证据清单", "已有证据"]),
    }

    missing = [k for k in ("train_type", "paid") if not filled(f[k])]

    r_amt, s = calc_amount(f)
    results = [
        ("退费金额核算", r_amt),
        ("课时单价认定", checks_price(f)),
        ("格式条款与违约金", checks_penalty(f)),
        ("办学许可与双减预收费", checks_license(f)),
        ("机构违约情形", checks_breach(f)),
        ("培训贷与征信风险", checks_loan(f)),
    ]
    steps = path_order(f)
    todos = todo_list(f, results, s)

    if args.json:
        print(json.dumps(to_json(f, results, s, todos, today), ensure_ascii=False, indent=2))
        return 0

    d = parse_date(f["issue_date"])
    if d:
        dl = add_years(d, 3)
        left = (dl - today).days
        deadline_txt = ("发现异常日期 %s 起算的 3 年时效截至 %s，%s"
                        % (d.isoformat(), dl.isoformat(),
                           ("已超期 %d 天" % -left) if left < 0 else ("还剩 %d 天" % left)))
    else:
        deadline_txt = ("未填发现异常的日期，民事诉讼时效为 3 年，"
                        "自知道或应当知道权利被侵害及义务人之日起算，请补填日期后重跑")

    rep = render(f, results, s, steps, todos, today, deadline_txt)
    if missing:
        rep += ("\n> 提示：关键信息缺失——%s，相关判断已按\"待补正\"处理，"
                "补齐后重跑可得到确定结论。\n" % "、".join(missing))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(rep)
        print("已写出 %s" % args.out)
    else:
        sys.stdout.write(rep)
    return 2 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
