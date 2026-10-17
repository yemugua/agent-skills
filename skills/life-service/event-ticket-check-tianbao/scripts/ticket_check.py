#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""演出门票退换核查。

用法：
  python ticket_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python ticket_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失（给提示串，不崩）。
"""
import argparse
import json
import re
import sys
from datetime import date

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "（", "("]


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
    v = (v or "").strip()
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
    return n in ("有", "是", "已经", "已", "已完成", "已申请", "已提交", "已退款", "true", "yes")


def no(v):
    n = norm(v)
    return n in ("无", "否", "没有", "未", "未做", "未提交", "未申请", "false", "no")


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知")


def parse_num(s):
    if not s:
        return None
    s = str(s).replace(",", "").replace("，", "").replace("%", "")
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


def money(x):
    if x is None:
        return "—"
    return "¥" + fmt_num(x)


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


# ------------------------------------------------------------------ 状态词表
CANCELLED = ["已取消", "取消", "停演"]
POSTPONED = ["已延期", "延期", "改期"]
CHANGED = ["已变更", "变更", "换演员", "换场馆"]
NORMAL = ["正常", "照常", "未受影响"]

HOST_STATES = ("已取消", "已延期", "已变更")


def status_kind(v):
    s = norm(v)
    if not s:
        return None
    if any(k in s for k in CANCELLED):
        return "已取消"
    if any(k in s for k in POSTPONED):
        return "已延期"
    if any(k in s for k in CHANGED):
        return "已变更"
    if any(k in s for k in NORMAL):
        return "正常"
    return None


def is_realname(v):
    s = norm(v)
    if not s:
        return None
    if "非实名" in s or "不实名" in s or "未实名" in s:
        return False
    if "实名" in s:
        return True
    return None


SCALPER_WORDS = ["黄牛", "二手", "转手", "倒票", "代抢", "票贩"]


def is_scalper(v):
    if yes(v):
        return True
    s = norm(v)
    return bool(s) and any(k in s for k in SCALPER_WORDS)


# ------------------------------------------------------------------ 二 票种
def checks_type(f):
    out = []
    rn = f["realname"]
    flag = is_realname(rn)
    if flag is None:
        out.append(("票种（是否实名）", "待补正",
                    "这是判断退改方向的第一步，必须填。强实名票人票绑定、一场一证、转赠收口，"
                    "能不能退看平台与主办方公布的退改规则；普通非实名票转手相对容易，退票同样按平台规则走。"
                    "填强实名或非实名，不清楚就写不清楚。"))
    elif flag:
        out.append(("票种（是否实名）", "通过",
                    "判定为强实名票：人票绑定，入场核验证件与人一致，转赠基本被收口，"
                    "能否退完全取决于平台公布的退改规则与窗口期。"))
    else:
        out.append(("票种（是否实名）", "通过",
                    "判定为普通非实名票：入场不以身份核对为前提，转手相对可行；"
                    "但退票仍按购票平台的退改规则走。"))

    tr = f["transfer"]
    if yes(tr):
        out.append(("是否支持转赠", "通过",
                    "平台支持转赠或改绑，转手路径存在，优先看能否改绑到本人以外的观演人。"))
    elif no(tr):
        out.append(("是否支持转赠", "有风险",
                    "平台不支持转赠或改绑，这张票只能由购票登记人本人使用；"
                    "想换人只能退票重买，别把二维码直接发给陌生人。"))
    else:
        out.append(("是否支持转赠", "待补正",
                    "转赠政策未填，影响第五节能不能转手的判断，请查订单页或问客服确认。"))
    return out


# ------------------------------------------------------------------ 三 定性
def checks_cause(f):
    out = []
    kind = status_kind(f["status"])
    if kind is None:
        out.append(("演出状态", "待补正",
                    "演出状态未填或无法识别（正常 / 已取消 / 已延期 / 已变更），"
                    "定性不了是谁的原因，后面金额也就算不准。"))
        return out
    if kind == "已取消":
        out.append(("演出状态", "通过", "演出已取消。属主办方原因，观众可要求全额退款，也可协商改到其它场次。"))
    elif kind == "已延期":
        out.append(("演出状态", "通过",
                    "演出已延期。延期不当然使门票作废，主办方应就新时间地点另行通知并给出退或改的方案；"
                    "不接受新安排的通常可以退票，别默认延期后票就白扔了。"))
    elif kind == "已变更":
        out.append(("演出状态", "通过",
                    "演出已变更（演员或场馆变更），属演出合同内容的重大变更。变更场馆尤其跨城的，"
                    "影响观演目的的可主张退票；变更演员一般先协商，是否构成根本违约看合同与宣传承诺。"))
    else:
        out.append(("演出状态", "通过", "演出照常进行，当前未出现取消、延期或变更。"))

    if kind in HOST_STATES:
        out.append(("退改定性（谁的原因）", "通过",
                    "定性为**主办方或场馆原因**：演出取消、延期、变更演员或场馆，观众有权选择退票，"
                    "也可选择改签或保留；主办方原因不得扣你手续费，取消通常全额退。"))
    elif kind == "正常":
        out.append(("退改定性（谁的原因）", "通过",
                    "演出状态正常，退票属**观众自身原因**：按购票平台公布的退改规则办理，"
                    "通常有演出前若干小时的窗口期并按阶梯收手续费。"))
    else:
        out.append(("退改定性（谁的原因）", "待补正", "演出状态缺失，无法定性，请补齐后再跑。"))

    if kind == "已变更" and not filled(f["change_note"]):
        out.append(("变更内容说明", "待补正",
                    "变更的是演员还是场馆、原宣传是否写明具体主演，需要写清，这决定能不能主张退票。"))
    return out


# ------------------------------------------------------------------ 四 金额
def calc_amount(f, days_left):
    """返回 (可退下限, 可退上限, 手续费或None, 口径串, 判定)。"""
    paid = f["paid"]
    face = f["face"]
    rate = f["fee_rate"]
    kind = status_kind(f["status"])
    sc = is_scalper(f["scalper"])

    if kind in HOST_STATES:
        if sc and face is not None:
            if paid is not None and paid > face + 1e-6:
                return (face, face, 0.0,
                        "主办方原因（%s）本应全额退实付金额，但你是黄牛或二手渠道买入：主办方与平台"
                        "只按**票面价**退（%s），实付 %s 中间的 %s 是溢价，只能自己扛。"
                        % (kind, money(face), money(paid), money(paid - face)), "不通过")
            base = face
            return (base, base, 0.0,
                    "主办方原因（%s），且系黄牛或二手渠道买入，可退基数按**票面价** %s 计，不收手续费。"
                    % (kind, money(face)), "不通过")
        base = paid if paid is not None else face
        if base is None:
            return (None, None, None,
                    "主办方原因，按全额退口径应退实付金额，但实付与票面金额都没填，无法算出具体数。", "待补正")
        return (base, base, 0.0,
                "主办方原因（%s），按全额退口径推：退付款 = 实付金额，不收手续费；"
                "实际到账以平台结算与主办方方案为准。" % kind, "通过")

    if sc and face is not None:
        return (face, face, None,
                "黄牛或二手渠道买入，主办方与平台只按**票面价** %s 退，实付 %s 中间的 %s 溢价自担；"
                "若人票不一致进不去，票款可能全损。"
                % (money(face), money(paid) if paid is not None else "—",
                   money((paid - face)) if paid is not None else "—"), "不通过")

    base = paid if paid is not None else face
    if base is None:
        return (None, None, None, "实付金额与票面金额均未填，无法测算。", "待补正")

    if days_left is not None and days_left <= 1:
        return (0.0, 0.0, base,
                "距演出不足 24 小时，多数平台此时已停止受理退票，可退金额趋近于 0；"
                "若仍受理，通常按阶梯收最高档手续费。", "不通过")

    if rate is not None:
        fee = base * rate / 100.0
        return (base - fee, base - fee, fee,
                "按填写的退票手续费率 %s%% 测算：手续费 = %s × %s%% = %s，可退 = %s。"
                % (fmt_num(rate), money(base), fmt_num(rate), money(fee), money(base - fee)), "有风险")

    return (base * 0.7, base * 0.9, None,
            "未填退票手续费率，给区间不给单值：按常见分档约可退票面额的 70%~90%（手续费约 10%~30%），"
            "以购票平台公布的退改规则页面为准；无约定又争议不断的，按实际损失、由双方举证确定。", "有风险")


def checks_amount(f, days_left):
    out = []
    lo, hi, fee, why, state = calc_amount(f, days_left)
    rng = money(lo) + " ~ " + money(hi) if hi != lo else money(lo)
    out.append(("可退金额测算", state, why + " 可退区间：" + rng))
    out.append(("手续费口径", "通过" if fee is not None else "有风险", why))

    if f["fee_rate"] is None and days_left is not None and days_left > 1:
        out.append(("退票手续费率", "待补正",
                    "手续费率未填，无法给出单值；请在采集表里填平台公示的档位（如 20），"
                    "或去退改规则页面截图后填进去。"))

    if f["paid"] is not None and f["face"] is not None and f["paid"] > f["face"] + 1e-6:
        loss = f["paid"] - f["face"]
        out.append(("溢价部分", "不通过",
                    "实付 %s 高于票面 %s，多付的 %s 属溢价。主办方与平台只按票面退，"
                    "溢价部分只能自担（除非能证明对方诈骗或违约）。"
                    % (money(f["paid"]), money(f["face"]), money(loss))))
    return out


# ------------------------------------------------------------------ 五 转手与黄牛
def checks_transfer(f):
    out = []
    sc_raw = f["scalper"]
    sc = is_scalper(sc_raw)
    if unknown(sc_raw):
        out.append(("购票来源", "待补正",
                    "是否从黄牛或二手平台购票未填。这一项决定第五节能不能转手、损失怎么承担，必须交代清楚。"))
    elif sc:
        out.append(("购票来源", "不通过",
                    "系黄牛或二手平台购票：溢价部分基本只能自己扛，且不受购票平台保障。"))
        bv = f["bound"]
        if filled(bv) and not yes(bv):
            out.append(("人票是否一致", "不通过",
                        "票未绑定本人实名入场，这是最要命的一条：强实名票人票不一致会直接被拒入场，"
                        "票款可能拿不回来。请立即核验证件信息，无法一致的走平台退款，不要再找人买票。"))
        elif filled(bv):
            out.append(("人票是否一致", "有风险",
                        "票已绑定本人，入场无碍；但溢价损失与后续退票仍按票面价结算。"))
        else:
            out.append(("人票是否一致", "待补正", "票是否已绑定本人实名入场未填，请核对订单页的观演人证件号。"))

        ov = norm(f["offline"])
        if ov and ("线下" in ov or "现金" in ov or "微信" in ov or "银行" in ov):
            out.append(("交易保障", "不通过",
                        "走的是线下或直接转账，脱离平台担保，一旦对方撤单或拉黑几乎无法追回；"
                        "之后只能凭转账凭证与聊天记录报警或起诉。"))
        elif not filled(f["offline"]):
            out.append(("交易方式", "待补正", "黄牛交易是走平台担保还是直接转账，未填。直接转账的基本追不回。"))

        if not yes(f["scale_rec"]):
            out.append(("黄牛交易记录", "待补正", "缺黄牛转账凭证与聊天记录，索赔与报警都要靠它，请补齐。"))
        out.append(("倒票是否可举报", "有风险",
                    "加价倒卖有价票证、变相炒票的，可举报至属地文旅主管部门与 12345；"
                    "是否构成违规、如何处罚以现行规定与主管部门认定为准。"))
    else:
        out.append(("购票来源", "通过", "系官方或正规票务渠道购票，受购票平台退改规则保障。"))
        if norm(sc_raw) not in ("有", "是"):
            out.append(("购票来源备注", "待补正",
                        "购票渠道写的是「%s」，无法判断是否属黄牛或二手转手渠道，"
                        "请回采集表把渠道写清楚（大麦 / _cat / 主办方直售 / 二手平台 / 黄牛）。" % sc_raw))

    rn = is_realname(f["realname"])
    tr = f["transfer"]
    if rn is True and filled(tr) and no(tr):
        out.append(("转手可行性", "不通过",
                    "强实名加不可转赠，这张票转手基本不可行，只能退票重买或本人前往；"
                    "别在二手平台挂出票，大概率被撤单或被骗。"))
    elif rn is False:
        out.append(("转手可行性", "通过",
                    "非实名票转手相对可行，但二手交易不受购票平台保障，"
                    "建议走平台官方转赠或二手入口，而不是直接转账给个人。"))
    else:
        out.append(("转手可行性", "待补正",
                    "票种或转赠政策未填，判定不了这张票能不能转手，请补齐两项信息。"))
    return out


# ------------------------------------------------------------------ 六 证据
EV_ITEMS = [
    ("购票订单与票面截图", "ev_order", "有没有订单号与票面，是所有退改主张的地基，先补订单页与电子票截图。"),
    ("实名绑定信息", "ev_id", "强实名票争议里绑定的是谁就是谁，缺这个说不清人票关系。"),
    ("取消或延期公告", "ev_notice", "公告发布时间是责任认定与合理时间起算的关键，务必存原图与链接。"),
    ("平台退改规则页面", "ev_rule", "规则随时会改，截图并记下截图时间，以你下单时公示的页面为准。"),
    ("客服或主办方沟通记录", "ev_chat", "客服回复与工单编号是升级投诉的抓手，别让它只停在口头。"),
    ("黄牛交易与转账记录", "ev_scale", "溢价损失要追靠的就是转账凭证、聊天与对方账号信息。"),
    ("现场被拒入场证据", "ev_refused", "若已被拒入场，现场照片与安保沟通记录是证明票款拿不回的直接材料。"),
]


def checks_evidence(f):
    out = []
    for name, key, msg in EV_ITEMS:
        v = f.get(key)
        if yes(v):
            out.append((name, "通过", "已留存，作为本次主张的基础材料。"))
        elif no(v):
            out.append((name, "不通过", msg))
        else:
            out.append((name, "待补正", "未填是否留存。" + msg))
    return out


# ------------------------------------------------------------------ 八 时限
def checks_deadline(f, today):
    out = []
    d = parse_date(f["event_date"])
    days_left = None
    if d:
        days_left = (d - today).days
        if days_left < 0:
            out.append(("距演出时间", "不通过", "演出已过（%s），退改基本失去意义，只剩违规退改或后续投诉与索赔。" % d.isoformat()))
        elif days_left <= 1:
            out.append(("距演出时间", "不通过", "距演出不足 24 小时，退票窗口基本关闭；先确认能否走主办方全额退通道。"))
        elif days_left <= 7:
            out.append(("距演出时间", "有风险", "距演出仅 %d 天，多数平台的退票窗口（演出前 24~72 小时）尚未关闭但很快关，请今天就提交申请。" % days_left))
        else:
            out.append(("距演出时间", "通过", "距演出还有 %d 天，落在常规退票窗口内。" % days_left))
    else:
        out.append(("演出日期", "待补正", "未填演出日期，无法计算退票窗口还剩多久，请补齐。"))

    cutoff = f["cutoff"]
    if cutoff is not None and days_left is not None:
        remain = days_left * 24 - cutoff
        if remain < 0:
            out.append(("退票窗口剩余", "不通过", "按演出前 %s 小时截止算，窗口已关闭，超时 %s 小时。"
                        % (fmt_num(cutoff), fmt_num(-remain))))
        elif remain <= 24:
            out.append(("退票窗口剩余", "有风险", "距截止仅剩 %s 小时，今天之内必须提交，越拖越退不动。" % fmt_num(remain)))
        else:
            out.append(("退票窗口剩余", "通过", "距退票截止约 %s 小时（%s 天），还有操作余量。"
                        % (fmt_num(remain), fmt_num(remain / 24.0))))

    nd = parse_date(f["notice_date"])
    if nd:
        days_since = (today - nd).days
        if days_since < 0:
            out.append(("公告日起算", "通过", "官方公告发布于 %s（晚于今天，请核对日期）。" % nd.isoformat()))
        elif days_since <= 30:
            out.append(("公告日起算", "通过", "官方公告发布于 %s，至今 %d 天，仍在通常的协商与投诉有效期内。"
                        % (nd.isoformat(), days_since)))
        else:
            out.append(("公告日起算", "有风险", "官方公告发布于 %s，至今已 %d 天。拖延越久，举证与协商难度越大；"
                        "民事诉讼时效 3 年，但别拖。" % (nd.isoformat(), days_since)))
    elif filled(f["notice_date"]):
        out.append(("公告日期", "待补正", "填了公告日期但格式不对，请写成 2026-09-28 这样的形式。"))
    return out


# ------------------------------------------------------------------ 七 阶梯
def path_order(f):
    kind = status_kind(f["status"])
    if is_scalper(f["scalper"]):
        return [
            ("第 1 步", "核验证件与人票是否一致：不一致的立即走平台退款通道申请退票面价，别再找人买票"),
            ("第 2 步", "向购票平台或二手平台投诉该商家：售假、人票不一致、欺诈，要求平台介入并披露卖家信息"),
            ("第 3 步", "与卖方协商退还票面金额（溢价不该你担），只走平台担保交易，脱离平台的转账基本追不回"),
            ("第 4 步", "对方失联或拉黑的：带转账凭证与聊天记录报案（涉诈骗），同时 12345 反映"),
            ("第 5 步", "加价倒票本身向文旅主管部门与 12345 举报；金额大且证据完整的，可另主张不当得利返还或起诉"),
        ]
    if kind in HOST_STATES:
        tag = {"已取消": "取消", "已延期": "延期", "已变更": "变更"}[kind]
        return [
            ("第 1 步", "平台自助退改入口走全额退通道提交申请（主办方原因应全额退，不收手续费）"),
            ("第 2 步", "平台客服工单，拿到工单编号，写明主办方原因、要求全额退款，并附官方公告截图"),
            ("第 3 步", "主办方与场馆官方渠道（官网、公众号、客服电话）书面主张，要求给出退或改的明确方案"),
            ("第 4 步", "12345 反映，同步向属地文旅主管部门举报（涉%s与主办方履约）" % tag),
            ("第 5 步", "涉格式条款不退费争议的，向 12315 投诉"),
            ("第 6 步", "合同有仲裁条款的走仲裁，没有的向被告住所地法院起诉（诉讼时效 3 年）"),
        ]
    return [
        ("第 1 步", "平台自助入口优先试改签或换场次（通常免手续费），改不了再走退票"),
        ("第 2 步", "平台客服工单，拿到工单编号，说明真实原因（病假、行程冲突、误购）并附证明材料"),
        ("第 3 步", "要求平台出具书面退改规则依据（截图并记下截图时间，规则会改）"),
        ("第 4 步", "平台拒不处理的：12345 反映并 12315 投诉，要求说明规则的提示方式"),
        ("第 5 步", "协商不成的，就退费争议提起民事诉讼（诉讼时效 3 年）"),
    ]


# ------------------------------------------------------------------ 待办
def todo_list(f, results):
    todos = []
    for _, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not yes(f["applied"]):
        extra.append(("提交退改申请", "今天就在平台自助入口提交退改或改签申请，拿到申请编号"))
    if not yes(f["contact"]):
        extra.append(("联系平台客服", "走客服工单并记下工单编号，别只停在口头"))
    if not yes(f["ev_rule"]):
        extra.append(("截图退改规则页", "把平台退改规则页面截图并存下截图时间，规则会改"))
    if yes(f["scalper"]) and not yes(f["scale_rec"]):
        extra.append(("补黄牛交易凭证", "补齐转账凭证、聊天记录与对方账号信息"))
    if yes(f["scalper"]) and not yes(f["report"]):
        extra.append(("举报倒票", "向文旅主管部门与 12345 举报加价倒票，以现行规定与主管部门认定为定"))
    seen = set()
    allt = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        allt.append((n, s))
    return allt


# ------------------------------------------------------------------ 报告
def render(f, results, steps, todos, today):
    L = []
    L.append("# 演出门票退换核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 演出名称：%s" % (f.get("event_name") or "未填"))
    L.append("- 购票渠道：%s" % (f.get("channel") or "未填"))
    L.append("")

    bad = [r for _, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在明确硬伤，可主张**。")
    elif risk:
        L.append("**判定：存在风险点，需补正后主张**。")
    else:
        L.append("**判定：未发现明显问题；若有争议，按第七段阶梯推进**。")
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(todo))
    L.append("")
    for name, _s, msg in bad[:5]:
        L.append("- **%s**：%s" % (name, msg.replace("**", "")))
    for name, _s, msg in risk[:4]:
        L.append("- %s：%s" % (name, msg.replace("**", "")))
    L.append("")

    titles = ["二、票种与是否强实名", "三、退还是改的定性", "四、可退金额与手续费测算",
              "五、转手与黄牛风险", "六、证据缺口与取证"]
    for (title, rows), t in zip(results, titles):
        L.append("## %s" % t)
        L.append("")
        if not rows:
            L.append("（本段无新增项）")
            L.append("")
            continue
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for row in rows:
            if len(row) < 3:
                continue
            name, state, msg = row[0], row[1], row[2]
            L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
        L.append("")

    L.append("## 七、处理阶梯")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 八、时限倒计时")
    L.append("")
    # results 每项都是 (段标题, 行列表)，取行列表必须再解一层 [1]
    _r5 = results[5] if len(results) > 5 else None
    rows = _r5[1] if isinstance(_r5, (list, tuple)) and len(_r5) > 1 else []
    L.append("| 核查项 | 判定 | 说明 |")
    L.append("|---|---|---|")
    for row in rows:
        if len(row) < 3:
            continue
        name, state = row[0], row[1]
        msg = row[2]
        if not isinstance(msg, str):
            msg = str(msg)
        L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
    L.append("")

    L.append("## 九、待办补正动作")
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
    L.append("- 本结果依通用规则整理，**不替代律师意见**。")
    L.append("- 退改规则、手续费阶梯、实名转赠政策平台差异极大，一律以购票平台与主办方公布的现行规则、当地文旅主管部门口径为准。")
    L.append("- 不预测平台受理结果、不预测行政投诉与诉讼结果；倒票是否违规以主管部门认定为准。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 本结果依通用规则整理，不替代专业意见，最终以主管部门 / 司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today):
    return {
        "核查日期": today.isoformat(),
        "演出名称": f.get("event_name"),
        "购票渠道": f.get("channel"),
        "演出状态": f.get("status"),
        "结论": {
            "不通过": [r[0] for _, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _, rows in results for r in rows if r[1] == "待补正"],
        },
        "风险项": [r[0] for _, rows in results for r in rows if r[1] == "有风险"],
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


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

    scale_rec = get_text(kv, ["是否留存黄牛交易与转账记录", "黄牛交易记录"])
    f = {
        "event_name": get_text(kv, ["演出名称", "演出项目"]),
        "channel": get_text(kv, ["购票渠道", "购票平台", "通过哪个平台购票"]),
        "event_date": get_text(kv, ["演出日期", "演出时间", "场次日期"]),
        "status": get_text(kv, ["演出状态", "演出当前状态", "当前演出状态"]),
        "notice_date": get_text(kv, ["取消或延期公告日期", "公告日期", "公告发布时间"]),
        "change_note": get_text(kv, ["变更内容说明", "变更内容"]),
        "cutoff": parse_num(get_text(kv, ["退票申请截止", "退票截止", "退票窗口截止", "演出前多少小时截止"])),
        "realname": get_text(kv, ["是否实名票", "是否强实名", "票种是否实名", "票种"]),
        "transfer": get_text(kv, ["是否支持转赠", "能否转赠", "可否转赠", "转赠政策"]),
        "face": parse_num(get_text(kv, ["票面金额", "票面价", "原价"])),
        "paid": parse_num(get_text(kv, ["实付金额", "购票实付金额", "支付金额"])),
        "fee_rate": parse_num(get_text(kv, ["退票手续费率", "手续费率"])),
        "applied": get_text(kv, ["是否已提交退票申请", "是否已申请退票", "是否已提交退改申请"]),
        "contact": get_text(kv, ["是否已联系平台客服", "是否联系平台客服", "客服工单编号"]),
        "scalper": get_text(kv, ["是否从黄牛或二手平台购票", "是否黄牛票", "购票来源"]),
        "bound": get_text(kv, ["票是否已绑定本人实名入场", "票是否已绑定本人", "实名绑定情况"]),
        "offline": get_text(kv, ["黄牛交易方式", "交易方式"]),
        "scale_rec": scale_rec,
        "report": get_text(kv, ["是否已向12345或文旅部门反映", "是否已举报", "举报情况"]),
        "ev_order": get_text(kv, ["是否留存购票订单与票面截图", "购票订单与票面"]),
        "ev_id": get_text(kv, ["是否留存实名绑定信息", "实名绑定信息"]),
        "ev_notice": get_text(kv, ["是否留存取消或延期公告截图", "公告截图"]),
        "ev_rule": get_text(kv, ["是否留存平台退改规则页面", "退改规则页面"]),
        "ev_chat": get_text(kv, ["是否留存与客服或主办方聊天记录", "客服沟通记录"]),
        "ev_scale": scale_rec,
        "ev_refused": get_text(kv, ["是否留存现场被拒入场证据", "现场被拒入场证据"]),
    }

    d = parse_date(f["event_date"])
    days_left = (d - today).days if d else None

    results = [
        ("票种与实名", checks_type(f)),
        ("退改定性", checks_cause(f)),
        ("可退金额与手续费", checks_amount(f, days_left)),
        ("转手与黄牛风险", checks_transfer(f)),
        ("证据缺口", checks_evidence(f)),
        ("时限倒计时", checks_deadline(f, today)),
    ]
    steps = path_order(f)
    todos = todo_list(f, results)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today), ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, steps, todos, today)
    missing = [k for k in ("event_name", "status") if not filled(f[k])]
    if missing:
        rep += ("\n> 提示：关键信息缺失——%s，相关判断已按待补正处理，"
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
