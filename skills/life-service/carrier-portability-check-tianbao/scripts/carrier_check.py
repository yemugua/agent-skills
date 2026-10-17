#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""携号转网资格与拒绝申诉核查。

用法：
  python carrier_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python carrier_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")
HOUR_RE = re.compile(r"(\d+)\s*(?:小时|个小时|h)")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "（", "(", "有/无", "是/否",
                     "选填", "填写"]

# 政策通用口径：同一运营商连续使用满 120 天方可申请携号转网
CARRY_MIN_DAYS = 120
# 自携出通知送达之日起，24 小时内可在新运营商激活，逾期视为放弃
ACTIVATE_HOURS = 24

CARRIERS = [
    ("中国电信", ["中国电信", "电信"]),
    ("中国移动", ["中国移动", "移动"]),
    ("中国联通", ["中国联通", "联通", "沃"]),
    ("中国广电", ["中国广电", "广电"]),
    ("虚拟运营商", ["虚拟运营商", "虚商", "MVNO"]),
]

# 法定不可携 / 实操受限情形
BLOCKERS = [
    ("政企专线与集团号", ["政企", "专线", "集团", "企业总机", "集团号", "办公号"]),
    ("物联网卡与车规卡", ["物联网", "车规", "车载卡", "定位卡"]),
    ("宽带与电视捆绑", ["宽带", "ITV", "iptv", "电视"]),
    ("主副卡绑定", ["副卡", "主卡", "亲情号", "共享号", "家庭套餐"]),
    ("特殊号码合约", ["靓号", "吉祥号", "纪念号", "选号", "低消"]),
]

# 号码与账户风险
RISKS = [
    ("银行预留与贷款绑定", ["银行", "贷款", "房贷", "信用卡", "预留", "代扣"]),
    ("短信验证码接收", ["验证码", "短信验证", "接收码"]),
    ("第三方服务绑定", ["会员", "游戏", "购物", "直播", "云", "自动续费", "免密"]),
    ("单位与亲友登记", ["单位", "同事", "登记", "紧急联系人", "单位号码"]),
]

EVIDENCE = [
    ("身份与号码证明", ["身份证", "身份证复印件", "SIM卡", "合同", "入网协议", "服务协议"]),
    ("时长与在网证明", ["入网时间", "缴费记录", "话费账单", "在网证明", "开户日期"]),
    ("申请与受理证明", ["携出申请", "受理单", "工单", "短信", "验证码记录"]),
    ("拒绝与告知证据", ["拒绝", "告知书", "原因", "答复", "投诉记录"]),
    ("申诉与监管证据", ["12378", "12300", "工信部", "申诉", "监管"]),
    ("新号激活证明", ["激活", "新号", "入网", "实名", "归属地"]),
]

EVID_FIX = {
    "身份与号码证明": "拍下身份证正反面与 SIM 卡，补打一份在网协议或服务协议",
    "时长与在网证明": "调出最近 6~12 个月话费账单，或到营业厅打印在网时长证明",
    "申请与受理证明": "保留携出申请的短信、工单号、受理回执，不要只口头办理",
    "拒绝与告知证据": "要求运营商出具书面《不予携出告知书》并写明依据条款",
    "申诉与监管证据": "向 12378 银行保险消保热线或工信部 12300 渠道投诉，保存受理编号与答复",
    "新号激活证明": "携出后尽快在目标运营商完成实名与激活，保留激活成功截图",
    "合同或协议": "到营业厅索取并留存服务协议、号码使用协议",
}


# ------------------------------------------------------------------ 解析
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
    """解析 markdown 表格行与 '字段：值' 行，保留表头。"""
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
    """最长别名优先匹配。"""
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if norm(k) == na:
                return v.strip()
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if na in norm(k):
                return v.strip()
    return ""


def filled(v):
    if v is None:
        return False
    v = str(v).strip()
    if not v:
        return False
    if UNFILLED_MARK.search(v):
        return False
    for w in PLACEHOLDER_WORDS:
        if v.startswith(w):
            return False
    return True


def yes(v):
    n = norm(v)
    if n in ("有", "是", "已经", "已", "已完成", "已做", "可以", "能", "正常"):
        return True
    return n.startswith("已") or n.startswith("有") or n.startswith("正常")


def no(v):
    n = norm(v)
    if n in ("无", "否", "没有", "未", "未做", "false", "no", "不正常", "欠费", "停机"):
        return True
    return n.startswith("无") or n.startswith("未") or n.startswith("没有")


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知", "没填")


def has_keyword(v, words):
    s = norm(v)
    if not filled(s):
        return None
    for w in words:
        if norm(w) in s:
            return True
    return False


def parse_num(s):
    if s is None:
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


def carrier_name(v):
    s = norm(v)
    if not filled(s):
        return "未填"
    for name, keys in CARRIERS:
        for k in keys:
            if norm(k) in s:
                return name
    return "其他运营商"


# ------------------------------------------------------------------ 一 资格
def checks_qualify(f):
    out = []
    d = parse_date(f["online_date"])
    if d:
        used = (f["today"] - d).days
        ok = used >= CARRY_MIN_DAYS
        out.append(("连续使用是否满 %d 天" % CARRY_MIN_DAYS, "通过" if ok else "不通过",
                    "自 %s 入网至 %s 连续使用 %d 天，%s。"
                    % (d.isoformat(), f["today"].isoformat(), used,
                       "已满足携出条件" if ok
                       else "尚差 %d 天，届满后再申请" % (CARRY_MIN_DAYS - used))))
    else:
        out.append(("连续使用是否满 %d 天" % CARRY_MIN_DAYS, "待补正",
                    "未填入网/启用日期，无法核对 %d 天门槛。到营业厅打印在网时长证明，"
                    "或用最早一期的话费账单月推算。" % CARRY_MIN_DAYS))

    st = f["status"]
    if yes(st):
        out.append(("是否处于正常在网状态", "通过", "号码处于正常在网状态，无欠费与停机记录。"))
    elif no(st):
        out.append(("是否处于正常在网状态", "不通过",
                    "存在欠费、停机或非正常在网状态。**先缴清欠费并恢复正常在网，"
                    "否则申请会被直接驳回**，补缴后需留意复通时间是否影响 %d 天计算。" % CARRY_MIN_DAYS))
    else:
        out.append(("是否处于正常在网状态", "待补正", "是否欠费、停机、销户未填，这一项是能否受理的前提。"))

    if unknown(f["contract"]):
        out.append(("是否有未到期合约", "待补正",
                    "是否签过服务协议或有未到期的套餐合约未填。**合约期未满是驳回最常见的原因之一**，"
                    "请到营业厅查协议与优惠到期日。"))
    elif yes(f["contract"]):
        out.append(("是否有未到期合约", "有风险",
                    "存在未到期合约或仍在优惠期内，运营商通常会以此为由不予受理。"
                    "先问清合约类型与到期日，能提前销户或等期满再申请。"))
    else:
        out.append(("是否有未到期合约", "通过", "无未到期合约与未结优惠。"))

    if unknown(f["gift"]):
        out.append(("是否有合约赠品未结清", "待补正",
                    "是否领取合约赠品（手机、路由器、话费）未填。有赠品未结清同样可能被拒。"))
    elif yes(f["gift"]):
        out.append(("是否有合约赠品未结清", "不通过",
                    "有合约赠品未按约定结清，运营商会以此为由不予携出。"
                    "先确认赠品条款（是否需提前解约、是否需赔付），结清后再申请。"))
    else:
        out.append(("是否有合约赠品未结清", "通过", "无未结清的合约赠品。"))
    return out


# ------------------------------------------------------------------ 二 不可携情形
def checks_block(f):
    out = []
    for label, keys in BLOCKERS:
        v = f.get(_field_of(label)) or ""
        hit = has_keyword(v, keys)
        if hit is True:
            body = ("**属于不可携情形（%s）**。这类号码受合同或业务规则限制，"
                    "运营商有正当理由不予受理，需先解除绑定或改业务类型。" % label)
            if label == "政企专线与集团号":
                body += ("政企专线、集团号与企业总机通常由单位统一签约，"
                         "需由单位管理员提出并变更合同主体，个人无法自行携出。")
            elif label == "主副卡绑定":
                body += ("可先在原运营商解除主副卡/亲情号关系，"
                         "或把主号转到副卡上再申请，避免号码注销后影响使用。")
            elif label == "宽带与电视捆绑":
                body += ("建议先单独退掉宽带与电视业务（注意违约金与合约期），"
                         "或保留原业务、只携号码，确认当地是否允许。")
            out.append((label, "不通过", body))
        elif hit is False:
            out.append((label, "通过", "不属于%s情形。" % label))
        else:
            out.append((label, "待补正", "%s未填。" % label))
    return out


FIELD_OF = {
    "政企专线与集团号": "enterprise",
    "物联网卡与车规卡": "iot",
    "宽带与电视捆绑": "bundle",
    "主副卡绑定": "subcard",
    "特殊号码合约": "special_no",
    "银行预留与贷款绑定": "bank",
    "短信验证码接收": "sms",
    "第三方服务绑定": "thirdparty",
    "单位与亲友登记": "org",
}


def _field_of(label):
    return FIELD_OF.get(label, "unknown")


# ------------------------------------------------------------------ 三 风险
def checks_risk(f):
    out = []
    b = f["bank"]
    if unknown(b):
        out.append(("银行预留与贷款绑定", "待补正",
                    "该号码是否用于银行预留、房贷、信用卡代扣未填。"
                    "携出后原服务可能失效或短信验证码收不到，**先到银行把预留手机号改掉**。"))
    elif yes(b):
        out.append(("银行预留与贷款绑定", "有风险",
                    "号码绑定银行预留或代扣。**携出后原号码可能停机，验证码收不到会影响还贷、扣款与解绑**，"
                    "请先到银行或线上渠道把预留号码改为新号或本人常用号。"))
    else:
        out.append(("银行预留与贷款绑定", "通过", "未用于银行预留或代扣。"))

    s = f["sms"]
    if unknown(s):
        out.append(("短信验证码接收", "待补正", "携出后能否继续接收该号码的验证码未填。"))
    elif yes(s):
        out.append(("短信验证码接收", "通过", "携出后仍能正常接收该号码的验证码，账号类服务影响较小。"))
    else:
        out.append(("短信验证码接收", "有风险",
                    "携出后收不到原号码验证码。**先登录常用 App 更换绑定手机号**，"
                    "否则支付、社交、会员、免密支付都可能失效。"))

    t = f["thirdparty"]
    if unknown(t):
        out.append(("第三方服务绑定", "待补正", "该号码绑定了哪些会员、购物、免密支付类服务未填。"))
    elif yes(t):
        out.append(("第三方服务绑定", "有风险",
                    "该号码绑定了第三方服务或开通了自动续费/免密支付。"
                    "**逐项解绑或换绑新号**，避免原号停机后被自动扣费。"))
    else:
        out.append(("第三方服务绑定", "通过", "无第三方服务与自动续费绑定。"))

    o = f["org"]
    if unknown(o):
        out.append(("单位与亲友登记", "待补正", "该号码是否登记为单位或亲友常用联络号未填。"))
    elif yes(o):
        out.append(("单位与亲友登记", "有风险",
                    "该号码被单位或亲友登记为常用联络号，携出后会收到陌生电话与短信骚扰。"
                    "**携出前先到 12321 / 运营商处取消商业营销呼叫登记**，"
                    "并在通讯录里把亲友号码同步更新。"))
    else:
        out.append(("单位与亲友登记", "通过", "未被登记为单位或亲友常用联络号。"))
    return out


# ------------------------------------------------------------------ 四 时限
def checks_time(f, today):
    out = []
    d = parse_date(f["online_date"])
    if d:
        ready = d + timedelta(days=CARRY_MIN_DAYS)
        left = (ready - today).days
        out.append(("%d 天资格届满日" % CARRY_MIN_DAYS,
                    "通过" if left <= 0 else "有风险",
                    "入网 %s 满 %d 天为 %s，%s。"
                    % (d.isoformat(), CARRY_MIN_DAYS, ready.isoformat(),
                       "已届满" if left <= 0 else "还剩 %d 天" % left)))
    else:
        out.append(("%d 天资格届满日" % CARRY_MIN_DAYS, "待补正",
                    "未填入网日期，无法算资格届满日。"))

    port = parse_date(f["port_out_date"])
    if port:
        # date + timedelta 仍返回 date，24 小时窗口按自然日折算
        deadline = port + timedelta(days=1)
        left_d = (deadline - today).days
        if f["activated_yes"]:
            state = "通过"
        elif left_d < 0:
            state = "不通过"
        else:
            state = "有风险"
        out.append(("%d 小时激活窗口" % ACTIVATE_HOURS, state,
                    "携出完成日 %s，自送达之日起 %d 小时内应在目标运营商激活，"
                    "按日口径窗口到 %s；%s。"
                    % (port.isoformat(), ACTIVATE_HOURS, deadline.isoformat(),
                       "已激活新号" if f["activated_yes"] else
                       ("已逾期" if left_d < 0 else "剩余时间不多，尽快激活"))))
    elif yes(f["applied"]):
        out.append(("%d 小时激活窗口" % ACTIVATE_HOURS, "待补正",
                    "已提交申请但未填携出完成日，窗口从**携出通知送达之日**起算，"
                    "填上日期才能判断是否来得及激活。"))
    else:
        out.append(("%d 小时激活窗口" % ACTIVATE_HOURS, "待补正",
                    "尚未申请携出，激活窗口还没开始起算。"))

    ap = parse_date(f["applied_date"])
    if ap:
        passed = (today - ap).days
        out.append(("申请受理时效", "有风险" if passed > 30 else "通过",
                    "申请提交于 %s，至今 %d 天，%s。"
                    % (ap.isoformat(), passed,
                       "已超过常见的 10~15 个工作日办理周期，建议催办并要工单号"
                       if passed > 30 else "仍在常见办理周期内")))
    else:
        out.append(("申请受理时效", "待补正", "未填申请提交日期，无法核对办理时效。"))
    return out


# ------------------------------------------------------------------ 五 拒绝与申诉
def checks_refuse(f):
    out = []
    r = f["reject_reason"]
    if not filled(r):
        out.append(("是否被拒绝及理由", "待补正",
                    "未被拒绝或未填理由。**若被口头拒绝，一定要索要书面依据**"
                    "（《不予携出告知书》），这是后续申诉与诉讼唯一有分量的证据。"))
        return out
    if any(k in norm(r) for k in ["合约", "协议", "期限", "优惠", "赠品"]):
        out.append(("是否被拒绝及理由", "有风险",
                    "拒绝理由属于**合约未到期/优惠未结清**类：%s。"
                    "这类理由原则上站得住，但应要求运营商书面写明具体协议名称与到期日，"
                    "核对与自己持有的协议是否一致。" % r))
    elif any(k in norm(r) for k in ["政企", "专线", "集团", "物联网", "副卡", "宽带"]):
        out.append(("是否被拒绝及理由", "有风险",
                    "拒绝理由属于**业务类型限制**类：%s。"
                    "可先解除绑定或变更业务类型，保留书面告知后重新申请。" % r))
    elif any(k in norm(r) for k in ["欠费", "停机", "销户", "状态异常"]):
        out.append(("是否被拒绝及理由", "有风险",
                    "拒绝理由属于**在网状态异常**：%s。"
                    "缴清欠费并恢复正常在网后重新申请。" % r))
    elif any(k in norm(r) for k in ["资料", "身份证", "实名", "手续", "本人"]):
        out.append(("是否被拒绝及理由", "有风险",
                    "拒绝理由属于**资料或本人核验**：%s。"
                    "按要求带齐身份证与本人身份证件到营业厅办理，"
                    "若为代办被拒可要求书面载明依据。" % r))
    else:
        out.append(("是否被拒绝及理由", "有风险",
                    "拒绝理由为：%s。**要求书面化并核对是否属于法定可携情形**，"
                    "不在法定不可携范围之内的，可直接进入申诉阶梯。" % r))

    if yes(f["written"]):
        out.append(("是否取得书面告知", "通过",
                    "已取得书面告知或答复记录，可直接作为申诉与后续维权材料。"))
    elif no(f["written"]):
        out.append(("是否取得书面告知", "不通过",
                    "**只有口头拒绝、没有书面依据**，申诉与诉讼都缺抓手。"
                    "再次联系客服或营业厅，明确要求出具书面答复并留工单号。"))
    else:
        out.append(("是否取得书面告知", "待补正", "是否取得书面告知未填。"))
    return out


# ------------------------------------------------------------------ 六 投诉渠道
def checks_complaint(f):
    out = []
    channels = [
        ("原运营商客服工单", f["ticket"],
         "10000/10010/10099 客服热线或营业厅工单，**要工单编号**，"
         "这是后续所有申诉的底账；口头承诺不算。"),
        ("工信部申诉渠道（12300/12378）", f["miit"],
         "运营商客服仍不给明确答复的，向工信部电信服务申诉渠道（12300 等）申诉，"
         "**按属地和接入地选择受理渠道**，附工单号与书面答复。"),
        ("12345 政务热线", f["hotline"],
         "可作为补充渠道，反映运营商设置不合理障碍、拖延办理，"
         "由主管部门转办，比单纯投诉运营商更有效。"),
        ("12315 消费投诉", f["market"],
         "被当作消费服务侵权处理的，可同步向 12315 反映，形成多渠道压力。"),
    ]
    for label, v, body in channels:
        if yes(v):
            out.append((label, "通过", body + " —— 已使用，建议留存受理编号与答复内容。"))
        elif no(v):
            out.append((label, "有风险", body + " —— 尚未使用，这一步成本极低，建议尽快补上。"))
        else:
            out.append((label, "待补正", "是否走过%s未填。" % label))
    return out


# ------------------------------------------------------------------ 七 证据
def checks_evidence(f):
    out = []
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    if not has_content(got):
        out.append(("证据总览", "待补正",
                    "已有证据既没勾选也没写清单。**携号转网的胜负手就是书面材料**："
                    "入网时长证明、书面答复、工单号，缺一样申诉就软。请逐项对照补齐。"))
        return out
    for label, keys in EVIDENCE:
        hit = [k for k in keys if k in got]
        if hit:
            out.append((label + "证据", "通过",
                        "已具备：%s。请原件拍照、复印件留存，按时间顺序整理成册。" % "、".join(hit)))
        else:
            out.append((label + "证据", "有风险",
                        "尚无%s证据，这类缺口会明显削弱申诉与后续主张，请尽快补齐。" % label))
    return out


def has_content(s):
    for part in str(s or "").split("|"):
        if filled(part):
            return True
    return False


def evidence_gap(f):
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    gaps = []
    if has_content(got):
        for label, keys in EVIDENCE:
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in EVIDENCE]
    if not yes(f["written"]):
        gaps.append("拒绝与告知证据")
    if filled(f["online_date"]):
        gaps.append("时长与在网证明")
    if yes(f["applied"]):
        gaps.append("申请与受理证明")
    seen = set()
    res = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            res.append(g)
    return res


# ------------------------------------------------------------------ 路径
def path_steps(f):
    out = [("第 1 步（先自查资格）",
            "核对连续使用是否满 %d 天、是否正常在网、有无未到期合约与未结赠品。"
            "**这四项不解决，申诉也不会赢**；先到营业厅打印在网时长证明。" % CARRY_MIN_DAYS)]
    if carrier_name(f["carrier"]) != "未填":
        out.append(("第 2 步（原运营商）",
                    "携 %s 客服热线或到自有营业厅提出携号转网申请，"
                    "**当场索取受理回执与工单编号**；若被拒，要求出具书面《不予携出告知书》。"
                    % carrier_name(f["carrier"])))
    out.append(("第 3 步（解除绑定）",
                "有政企专线、物联网卡、主副卡、宽带捆绑、靓号合约的，"
                "先解除绑定或变更业务类型；涉单位统一签约的需单位管理员配合。"))
    out.append(("第 4 步（清理绑定服务）",
                "把银行预留、免密支付、会员与自动续费逐项换绑到新号或常用号，"
                "避免原号停机后收不到验证码、扣费失败。"))
    out.append(("第 5 步（申诉阶梯）",
                "原运营商不给明确答复的，按 10000/10010 工单 → 工信部电信服务申诉（12300 等）"
                "→ 12345 政务热线 → 12315 消费投诉 的顺序推进，**每次都附工单号与书面答复**。"))
    out.append(("第 6 步（时限与收尾）",
                "携出通知送达后 %d 小时内完成目标运营商激活与实名，逾期视为放弃；"
                "激活后核对归属地与套餐是否按预期生效。" % ACTIVATE_HOURS))
    out.append(("第 7 步（极端情况）",
                "运营商设置不合理障碍、拒不受理或拖延的，"
                "可向人民法院提起诉讼，请求确认受理条件成就并追究违约责任；"
                "**具体受理条件与管辖以当地现行规定和法院口径为准**。"))
    return out


def todo_list(f, results):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not yes(f["written"]):
        extra.append(("索取书面告知", "要《不予携出告知书》或书面答复，带走工单号"))
    if not yes(f["ticket"]):
        extra.append(("要工单编号", "10000/10010 或营业厅受理后立刻记下工单号"))
    if parse_date(f["online_date"]) is None:
        extra.append(("打印在网时长证明", "营业厅可打，作为满 120 天的凭证"))
    if yes(f["bank"]):
        extra.append(("换绑银行预留号", "到银行把预留手机号改成新号或常用号"))
    if not yes(f["sms"]):
        extra.append(("逐项换绑验证码", "支付、会员、免密支付先换手机号"))
    extra.append(("取消营销呼叫登记", "携出前后到 12321 或运营商处取消商业营销登记"))
    extra.append(("备好工信部申诉材料", "工单号 + 书面答复 + 在网证明，一次提交"))
    seen = set()
    res = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        res.append((n, s))
    return res


# ------------------------------------------------------------------ 报告
SECTIONS = [
    "二、资格条件逐项核查",
    "三、不可携情形核查",
    "四、号码与账户风险",
    "五、时限倒计时",
    "六、拒绝情形与申诉阶梯",
    "七、投诉渠道与受理",
    "八、证据清单与缺口",
]


def render(f, results, steps, todos, today, gaps):
    L = []
    L.append("# 携号转网资格与拒绝申诉核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 原运营商：%s" % carrier_name(f["carrier"]))
    L.append("- 号码连续使用：%s" % (parse_date(f["online_date"]).isoformat()
                                 if parse_date(f["online_date"]) else "未填"))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在明确的不可携情形或不通过项，先解决硬门槛再谈申诉。**")
    elif risk:
        L.append("**判定：资格本身可争取，但有合约、绑定或时限风险需要先处理。**")
    elif todo:
        L.append("**判定：采集表关键项未填，暂时给不出确定结论；"
                 "请把入网日期、在网状态、合约与拒绝理由填完再重跑。**"
                 "**未填的一律不算通过。**")
    else:
        L.append("**判定：未发现明确阻碍；建议按第九段路径备齐材料一次办成。**")
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(todo))
    L.append("")
    for name, _s, msg in bad[:5]:
        L.append("- **%s**：%s" % (name, msg.replace("**", "")))
    for name, _s, msg in risk[:5]:
        L.append("- %s：%s" % (name, msg.replace("**", "")))
    L.append("")

    for (title, rows), t in zip(results, SECTIONS):
        if not rows:
            L.append("## %s" % t)
            L.append("")
            L.append("暂无可核查项（未填不按通过处理）。")
            L.append("")
            continue
        L.append("## %s" % t)
        L.append("")
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for row in rows:
            if len(row) < 3:
                continue
            name, state, msg = row[0], row[1], row[2]
            if not isinstance(msg, str):
                msg = str(msg)
            L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
        L.append("")

    L.append("## 九、办理与申诉路径排序")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 十、证据缺口速查")
    L.append("")
    if not gaps:
        L.append("当前填写的证据已较完整。")
    else:
        L.append("| 缺失类别 | 补法 |")
        L.append("|---|---|")
        for g in gaps[:12]:
            L.append("| %s | %s |" % (g, EVID_FIX.get(g, "按第九段操作卡补齐")))
    L.append("")

    L.append("## 十一、待办补正动作")
    L.append("")
    if not todos:
        L.append("当前未发现必须补正的事项。")
    else:
        L.append("| 动作 | 状态 |")
        L.append("|---|---|")
        for n, s in todos:
            L.append("| %s | %s |" % (n, s))
    L.append("")

    L.append("## 边界与纪律")
    L.append("")
    L.append("- 依**通用规则**整理，**不替代律师意见**；各运营商的具体受理条件、"
             "合约条款与办理时限**以本人服务协议与运营商现行规则为准**。")
    L.append("- 不预测监管与法院的受理结果，也不承诺申诉一定通过。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 本结果依通用规则整理，不替代专业意见，最终以运营商、主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps):
    return {
        "核查日期": today.isoformat(),
        "运营商": carrier_name(f["carrier"]),
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "carrier": get_text(kv, ["原运营商", "运营商", "当前运营商", "号码所属运营商"]),
        "online_date": get_text(kv, ["入网或启用日期", "入网日期", "启用日期", "开户日期", "入网时间"]),
        "status": get_text(kv, ["是否正常在网", "在网状态", "是否欠费停机", "号码状态"]),
        "contract": get_text(kv, ["是否有未到期合约", "未到期合约", "是否有服务协议", "合约情况"]),
        "gift": get_text(kv, ["是否有合约赠品未结清", "合约赠品", "赠品未结清"]),
        "enterprise": get_text(kv, ["是否政企专线或集团号", "是否政企", "是否集团号", "是否单位号码"]),
        "iot": get_text(kv, ["是否物联网卡或车规卡", "是否物联网卡", "是否车规卡"]),
        "bundle": get_text(kv, ["是否与宽带电视捆绑", "是否宽带捆绑", "是否捆绑业务"]),
        "subcard": get_text(kv, ["是否主副卡或亲情号绑定", "是否副卡", "是否主副卡", "是否亲情号"]),
        "special_no": get_text(kv, ["是否特殊号码合约", "是否靓号", "是否吉祥号", "号码类型"]),
        "bank": get_text(kv, ["是否用于银行预留或代扣", "是否银行预留", "是否用于银行"]),
        "sms": get_text(kv, ["携出后能否接收验证码", "能否接收验证码", "验证码接收"]),
        "thirdparty": get_text(kv, ["是否绑定第三方服务", "是否绑定会员", "是否自动续费"]),
        "org": get_text(kv, ["是否被单位或亲友登记为常用号", "是否单位常用号", "是否亲友登记"]),
        "applied": get_text(kv, ["是否已提交携出申请", "是否已申请携出", "申请情况"]),
        "applied_date": get_text(kv, ["申请提交日期", "申请日期", "提交日期"]),
        "port_out_date": get_text(kv, ["携出完成或通知日期", "携出完成日期", "携出通知日期", "携出日期"]),
        "activated_yes": yes(get_text(kv, ["新号是否已激活", "是否已激活新号", "新号激活"])),
        "reject_reason": get_text(kv, ["不予携出的理由", "拒绝理由", "不予携出原因", "拒绝原因"]),
        "written": get_text(kv, ["是否取得书面告知", "是否有书面答复", "是否书面告知"]),
        "ticket": get_text(kv, ["是否取得客服工单编号", "工单编号", "是否有工单"]),
        "miit": get_text(kv, ["是否已向工信部申诉", "是否工信部申诉", "12300", "12378"]),
        "hotline": get_text(kv, ["是否已向12345反映", "是否12345", "12345"]),
        "market": get_text(kv, ["是否已向12315投诉", "是否12315", "12315"]),
        "evidence_owned": get_text(kv, ["已有证据勾选", "证据勾选"]),
        "evidence_desc": get_text(kv, ["证据清单", "已有证据", "材料清单"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    kv = build_kv(read_text(args.input))
    today = base_date(args.base)
    f = build_fields(kv)
    f["today"] = today

    missing = []
    if not filled(f["carrier"]):
        missing.append("原运营商")
    if not filled(f["online_date"]) and not yes(f["applied"]):
        missing.append("入网或启用日期")

    results = [
        ("资格条件逐项核查", checks_qualify(f)),
        ("不可携情形核查", checks_block(f)),
        ("号码与账户风险", checks_risk(f)),
        ("时限倒计时", checks_time(f, today)),
        ("拒绝情形与申诉阶梯", checks_refuse(f)),
        ("投诉渠道与受理", checks_complaint(f)),
        ("证据清单与缺口", checks_evidence(f)),
    ]

    steps = path_steps(f)
    todos = todo_list(f, results)
    gaps = evidence_gap(f)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today, gaps), ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, steps, todos, today, gaps)
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
