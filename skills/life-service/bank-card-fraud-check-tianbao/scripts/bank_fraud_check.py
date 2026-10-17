#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""银行卡盗刷（ unauthorized 交易）核查与止损追回。

用法：
  python bank_fraud_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python bank_fraud_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "（", "(", "有/无", "是/否",
                     "选填", "填写"]

# 争议类型：不同类型的处理路径与举证责任差别很大
DISPUTE_TYPES = [
    ("伪卡盗刷", ["伪卡", "假卡", "伪造", "复制卡", "卡片被复制", "盗刷"]),
    ("网络盗刷", ["网络", "线上", "手机银行", "网银", "支付平台", "第三方支付", "云闪付"]),
    ("短信诈骗转账", ["诈骗", "冒充", "客服", "公检法", "刷单", "退款", "杀猪盘", "转账", "被骗"]),
    ("他人代刷/误输账号", ["输错", "代刷", "误转", "错转", "认错", "他人操作"]),
    ("涉毒涉赌资金", ["赌博", "博彩", "毒品", "洗钱", "非法平台", "跑分"]),
]

# 责任归属关键词
FAULT_TYPES = [
    ("本人操作泄露", ["本人泄露", "自己泄露", "我把密码", "自己给的", "自己操作", "本人操作"]),
    ("银行系统问题", ["系统", "银行差错", "系统故障", "数据错", "重复扣", "银行原因"]),
    ("银行未尽义务", ["未识别", "未风控", "未验证", "银行未", "银行违规", "未尽职",
                  "银行过失", "未监测", "未拦截", "风控不足", "系统故障", "银行差错"]),
    ("第三方平台责任", ["支付平台", "第三方", "平台", "收单", "商户"]),
    ("本人授权过", ["授权", "我同意", "我签", "我办过", "委托", "代扣协议", "我确认"]),
]

# 紧急止损动作
URGENT = [
    ("挂失与冻结账户", "立即通过银行官方渠道（App/电话/柜台）挂失或冻结账户，"
                   "阻断后续盗刷。**不要相信任何自称银行主动打来的电话**。"),
    ("修改所有关联密码", "银行取款密码、网银密码、支付密码全部更换，"
                    "**密码不要复用**，邮箱、支付类 App 也一并改。"),
    ("关闭小额免密与自动扣款", "关闭所有小额免密支付、代扣协议、快捷支付授权，"
                       "防止盗刷继续发生。"),
    ("调取完整交易流水", "要求银行打印**近 6 个月完整流水**（不是 App 截图），"
                   "逐笔标注可疑交易。"),
    ("确认是否被复制了信息", "回忆卡片是否遗失、是否交给他人、是否在商户处刷过、"
                    "**磁条卡与芯片卡都有被复制的可能**。"),
    ("排查手机是否被植入木马", "近期是否安装过不明 App、点过不明链接、"
                      "接过陌生 USB 设备；必要时换机并检查。"),
    ("联系公安报案", "到公安机关报案并取得**受案回执**，这是后续所有维权的基础。"),
    ("联系征信机构", "在征信中心查询并提出异议，避免盗刷记录影响征信。"),
]

# 维权路径
PATHS = [
    ("第 1 步（当场止损，1 小时内）",
     "银行官方渠道挂失/冻结 → 改密 → 关闭免密代扣。**越快越能减少损失**，"
     "银行一般以「采取措施后发生的交易」划分责任。"),
    ("第 2 步（固定证据，24 小时内）",
     "打印完整流水、报警回执、挂失回执、账户异常明细截图，**按时间顺序编号成册**。"),
    ("第 3 步（提出书面争议，3 日内）",
     "向银行提交**书面**盗刷异议（不是电话口头说），要求书面受理回执，"
     "并明确主张**不承担该笔交易**。"),
    ("第 4 步（银行调查，通常 15~60 日）",
     "银行应核查交易渠道、验证方式、风控记录并答复。**对答复不服可要求复核**。"),
    ("第 5 步（投诉升级）",
     "银行对结果不服 → 向**金融监管总局及其派出机构**投诉；"
     "或拨 **12378** 银行服务热线；涉及商户收单 → 拨 **12363** 支付结算。"),
    ("第 6 步（涉刑则走刑事）",
     "确认是伪卡、网络盗刷或诈骗转账的，**要求银行移送公安机关**，"
     "立案后由公安机关追赃挽损。"),
    ("第 7 步（民事诉讼兜底）",
     "协商、投诉、诉讼三管齐下：向法院起诉银行或收单机构要求返还损失，"
     "或依《民法典》主张侵权责任。"),
]

# 证据类别
EVIDENCE = [
    ("身份与账户证明", ["身份证", "银行卡", "账户", "卡号", "银行"]),
    ("交易流水与明细", ["流水", "明细", "交易记录", "账单", "对账单"]),
    ("挂失冻结记录", ["挂失", "冻结", "止付", "临时冻结"]),
    ("报警与立案材料", ["报警", "受案", "回执", "立案", "派出所"]),
    ("银行书面答复", ["答复", "书面", "异议申请", "回函", "告知书"]),
    ("沟通记录", ["录音", "通话记录", "聊天", "短信", "工单"]),
    ("第三方平台材料", ["支付平台", "商户", "收单", "平台订单", "商家"]),
]


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
    if n in ("有", "是", "已经", "已", "已完成", "已做", "可以", "能", "已挂失", "已报警"):
        return True
    return n.startswith("已") or n.startswith("有")


def no(v):
    n = norm(v)
    if n in ("无", "否", "没有", "未", "未做", "false", "no", "正常"):
        return True
    return n.startswith("无") or n.startswith("未") or n.startswith("没有")


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知", "没填")


def hit_any(v, words):
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


def money(x):
    return "¥" + fmt_num(x) if x is not None else "—"


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


# ------------------------------------------------------------------ 一 交易定性
def classify(f):
    """从盗刷经过里判断争议类型。"""
    txt = (f["detail"] or "") + "|" + (f["channel"] or "")
    if not filled(txt):
        return []
    return [lbl for lbl, ws in DISPUTE_TYPES if hit_any(txt, ws) is True]


def checks_classify(f):
    out = []
    kinds = classify(f)
    detail = f["detail"]
    if unknown(detail):
        out.append(("盗刷交易性质", "待补正",
                    "钱是怎么被刷走的、发生在哪里未填。"
                    "**性质决定了走哪条路**：伪卡盗刷和网络盗刷要追银行，"
                    "诈骗转账则主要是被害人与骗子的对抗，银行可能不承担责任。"))
    elif not kinds:
        out.append(("盗刷交易性质", "待补正",
                    "交易经过描述里没识别出明确的争议类型。"
                    "请按下列词补充：伪卡/假卡、网络/手机银行/支付平台、"
                    "诈骗/客服/冒充/转账、输错/代刷/误转、赌博/洗钱。"))
    else:
        out.append(("盗刷交易性质", "有风险",
                    "本次交易涉及：**%s**。这一类情况下，"
                    "**银行是否担责要看你与银行的安全义务履行情况**，"
                    "而诈骗转账类通常需要向公安机关追赃。" % "、".join(kinds)))
    return out


# ------------------------------------------------------------------ 二 紧急处置
def checks_urgent(f):
    out = []
    if unknown(f["frozen"]):
        out.append(("是否已挂失或冻结账户", "待补正",
                    "**这是最要紧的一件事**：立刻通过银行官方渠道挂失或冻结，"
                    "越快越能减少损失。**银行一般以「你采取措施后发生的交易」"
                    "划分责任**——不挂失就继续被刷，责任可能落到你头上。"))
    elif yes(f["frozen"]):
        out.append(("是否已挂失或冻结账户", "通过",
                    "已挂失/冻结。**这一步做得对**，后续盗刷应当被阻断；"
                    "如仍发生交易，立即向银行书面追责。"))
    else:
        out.append(("是否已挂失或冻结账户", "不通过",
                    "**尚未挂失或冻结**。这是当前最紧迫的动作，"
                    "**现在就去办**——继续放任可能扩大损失，"
                    "且会成为银行免除责任的理由。"))

    if unknown(f["password"]):
        out.append(("密码与免密授权是否已处理", "待补正",
                    "取款密码、网银密码、支付密码是否已改，"
                    "小额免密与代扣协议是否已关闭未填。"
                    "**密码不换、免密不关，同一张卡会被反复盗刷**。"))
    elif yes(f["password"]):
        out.append(("密码与免密授权是否已处理", "通过",
                    "密码与免密授权已处理。**若卡已补办，"
                    "记得同时销毁或剪断旧卡**。"))
    else:
        out.append(("密码与免密授权是否已处理", "不通过",
                    "**密码未改或免密授权未关闭**。被泄露的密码与免密通道"
                    "可能被持续利用，**立即全部更换并关闭**。"))

    if unknown(f["police"]):
        out.append(("是否已报警并取得回执", "待补正",
                    "有没有报警、有没有拿到受案回执未填。"
                    "**报警记录是后续所有维权的基础材料**，"
                    "没有它，纯粹的银行纠纷很难推进。"))
    elif yes(f["police"]):
        out.append(("是否已报警并取得回执", "通过",
                    "已报警。**确认拿到书面受案回执**，"
                    "并记下警号、接警时间与办案民警姓名。"))
    else:
        out.append(("是否已报警并取得回执", "有风险",
                    "尚未报警。**建议立即报案**——涉及金额较大或疑似诈骗、"
                    "伪卡的，报案后不仅便于追赃，也更有利于银行核查。"))
    return out


# ------------------------------------------------------------------ 三 损失与责任
def sum_loss(f):
    """合计损失金额：取交易金额与已追回金额。"""
    amt = parse_num(f["amount"])
    back = parse_num(f["recovered"]) or 0.0
    loss = (amt - back) if amt is not None else None
    if loss is not None and loss < 0:
        loss = 0.0
    return amt, back, loss


def calc_loss(f):
    amt, back, loss = sum_loss(f)
    res = {"可测算": amt is not None, "交易金额": amt, "已追回": back,
           "损失": loss, "笔数": None, "说明": ""}
    cnt = parse_num(f["count"])
    if cnt is not None:
        res["笔数"] = int(cnt)
    if not res["可测算"]:
        res["说明"] = "盗刷金额未填，无法测算实际损失。"
        return res
    if res["笔数"] and res["笔数"] > 1:
        res["说明"] = ("共 %d 笔，合计 %s，已追回 %s，**实际损失 %s**。"
                       "**多笔盗刷说明账户可能已被持续控制，"
                       "务必同步排查密码泄露路径与手机是否被植入木马**。"
                       % (res["笔数"], money(amt), money(back), money(loss)))
    else:
        res["说明"] = ("合计 %s，已追回 %s，**实际损失 %s**。"
                       % (money(amt), money(back), money(loss)))
    return res


def checks_loss(f, calc):
    out = []
    amt = f["amount"]
    if not calc["可测算"]:
        out.append(("盗刷金额与损失", "待补正",
                    "盗刷金额未填。**准确金额是主张返还的基础**，"
                    "以银行打印的完整流水为准，不要凭 App 截图估算。"))
    else:
        st = "通过" if (calc["损失"] or 0) == 0 else "有风险"
        out.append(("盗刷金额与损失", st, calc["说明"]))
    cnt = f["count"]
    if unknown(cnt):
        out.append(("盗刷笔数", "待补正", "共发生几笔未填。**笔数多说明账户被持续控制，"
                                       "要排查密码泄露与设备安全**。"))
    elif parse_num(cnt) and parse_num(cnt) > 1:
        out.append(("盗刷笔数", "有风险",
                    "发生 %d 笔。**这不是一次性泄露，而是账户被持续控制**。"
                    "除改密外，还要排查手机是否被植入木马、"
                    "是否授权过第三方代扣。" % int(parse_num(cnt))))
    else:
        out.append(("盗刷笔数", "通过", "单笔交易，已在正常核查范围。"))
    return out


def checks_fault(f):
    out = []
    resp = f["bank_response"]
    if unknown(resp):
        out.append(("银行如何答复", "待补正",
                    "银行说了什么、态度如何未填。"
                    "**银行主动调查并书面答复是正常流程**；"
                    "如果只让你「等通知」或直接拒赔，要书面要求受理并保留回执。"))
        out.append(("责任归属是否清楚", "待补正",
                    "银行是否承认担责未填。**核对你在这笔交易里做了什么**："
                    "有没有把密码告诉别人、有没有在陌生设备上操作、"
                    "有没有开通并使用过免密支付——这些直接决定责任划分。"))
        return out

    hits = [lbl for lbl, ws in FAULT_TYPES if hit_any(resp, ws) is True]
    if not hits:
        out.append(("责任归属是否清楚", "待补正",
                    "银行答复里没有明确的责任表述。建议**书面要求**明确："
                    "是否承担赔偿责任、依据哪一条内部规定、"
                    "拒赔的具体理由是什么。"))
    else:
        risky = [h for h in hits if h in ("本人操作泄露", "本人授权过")]
        if risky:
            out.append(("责任归属是否清楚", "不通过",
                        "银行主张**责任在本人**：%s。"
                        "**这一点必须认真对待**——如果你确实出过验证码、"
                        "在公用设备登录过、或开通过代扣，"
                        "银行可能不承担赔偿责任。**但银行仍负有核验与风控义务**，"
                        "可要求其说明是否履行了异常交易监测。"
                        % "、".join(risky)))
        else:
            out.append(("责任归属是否清楚", "有风险",
                        "银行主张：%s。**核实其说法是否有事实依据**，"
                        "银行应当提供核验记录、风控记录与拒赔依据。"
                        % "、".join(hits)))
    out.append(("银行如何答复", "有风险",
                "已答复：**%s**。**看清是「受理」还是「拒赔」**："
                "如为拒赔，要求书面写明依据，并保留答复函原件。"
                "对答复不服可向上级银行或监管机构投诉复核。" % f["bank_response"]))
    return out


def checks_verify(f):
    out = []
    v = f["verify"]
    if unknown(v):
        out.append(("银行是否做了交易核验", "待补正",
                    "银行有没有做身份核验、验证码验证、有没有监测到异常未拦截，"
                    "这些未填。**这是银行是否尽责的核心证据**，"
                    "要求银行书面说明：是否验证、验证方式是什么、"
                    "是否触发过风控、是否拦截。"))
        return out
    if hit_any(v, ["未识别", "未验证", "未风控", "未拦截", "未尽职", "银行违规",
                   "系统故障", "未监控", "放过"]) is True:
        out.append(("银行是否做了交易核验", "不通过",
                    "**银行未做核验或未拦截异常**：%s。"
                    "这是银行未尽安全义务的直接证据，"
                    "**要求银行书面说明并承担赔偿责任**，"
                    "必要时向金融监管部门投诉。" % v))
    elif hit_any(v, ["已核验", "已验证", "有风控", "已监测", "已拦截", "已尽调"]) is True:
        out.append(("银行是否做了交易核验", "有风险",
                    "银行称：%s。**核实方式**——银行做了什么核验、"
                    "核验结果如何、有没有留下可查的记录；"
                    "「已核验」不等于「已尽到全部义务」。" % v))
    else:
        out.append(("银行是否做了交易核验", "待补正",
                    "填的是「%s」，无法判断责任归属。"
                    "建议用这些词补充：未识别/未验证/未拦截/风控不足/系统故障/"
                    "银行违规/已核验/已监测。" % v))
    return out


# ------------------------------------------------------------------ 四 时限
def checks_time(f, today):
    out = []
    d = f["discover_date"]
    dt = parse_date(d)
    if unknown(d):
        out.append(("发现时间与处置时长", "待补正",
                    "什么时候发现被盗刷的未填。"
                    "**发现到挂失的间隔越长，越可能被银行主张"
                    "「已尽提示义务」或「损失扩大」**。"))
    else:
        out.append(("发现时间与处置时长", "通过",
                    "发现日期：%s（距核查日 %d 天）。"
                    % (d, (today - dt).days)))
    fr = f["frozen_date"]
    frd = parse_date(fr)
    if dt and frd:
        gap = (frd - dt).days
        if gap <= 0:
            out.append(("发现到挂失的间隔", "通过",
                        "发现当日即挂失/冻结。**这对你最有利**，"
                        "后续银行难以主张你未尽止损义务。"))
        elif gap <= 3:
            out.append(("发现到挂失的间隔", "有风险",
                        "从发现到挂失间隔 %d 天。**间隔越短越有利**，"
                        "银行可能主张期间损失扩大应由你承担。" % gap))
        else:
            out.append(("发现到挂失的间隔", "不通过",
                        "从发现到挂失间隔 %d 天，**明显偏长**。"
                        "银行很可能主张这段时间的损失是损失扩大部分，"
                        "要求你承担。**今后遇到盗刷应第一时间挂失**。" % gap))
    else:
        out.append(("发现到挂失的间隔", "待补正",
                    "挂失日期未填，**无法计算处置间隔**。"
                    "这个间隔直接决定银行能否主张「损失扩大」责任。"))

    out.append(("银行异议与投诉时限", "有风险",
                "**银行内部调查通常需 15~30 日，监管投诉一般 30~60 日有答复**。"
                "银行拒绝受理的，可拨 **12378** 银行服务热线；"
                "涉收单机构的拨 **12363** 支付结算服务热线。"))
    return out


# ------------------------------------------------------------------ 五 证据
def has_content(s):
    for part in str(s or "").split("|"):
        if filled(part):
            return True
    return False


def checks_evidence(f):
    out = []
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    if not has_content(got):
        out.append(("证据总览", "待补正",
                    "已有证据既没勾选也没写清单。**盗刷维权全靠留痕**："
                    "完整流水、挂失回执、报警回执、银行答复函，"
                    "缺一样都可能推进不下去。"))
        return out
    for label, keys in EVIDENCE:
        hit = [k for k in keys if k in got]
        if hit:
            out.append((label, "通过",
                        "已具备：%s。**原件留存、复印件提交**，"
                        "按时间顺序编号成册。" % "、".join(hit)))
        else:
            out.append((label, "有风险", "尚无%s材料，这类缺口会在出问题时让你被动。" % label))
    return out


EVID_FIX = {
    "身份与账户证明": "到银行网点打印账户信息与卡号证明，携带身份证",
    "交易流水与明细": "要求银行打印近 6 个月完整流水，不是 App 截图",
    "挂失冻结记录": "办理挂失/冻结并索取书面回执，注明办理时间",
    "报警与立案材料": "到公安机关报案，取得受案回执并记下警号",
    "银行书面答复": "以书面形式提出异议并要求受理回执，保存答复函原件",
    "沟通记录": "保存通话记录、工单号、聊天与短信记录，必要时录音",
    "第三方平台材料": "向支付平台或商户索取订单、转账与商户信息",
}


def evidence_gap(f):
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    gaps = []
    if has_content(got):
        for label, keys in EVIDENCE:
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in EVIDENCE]
    if yes(f["frozen"]) and not any(k in got for k in ["挂失", "冻结", "止付"]):
        gaps.append("挂失冻结记录")
    if not yes(f["police"]) and not any(k in got for k in ["报警", "受案", "立案"]):
        gaps.append("报警与立案材料")
    seen = set()
    res = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            res.append(g)
    return res


# ------------------------------------------------------------------ 路径与待办
def path_steps(f):
    return [("第 %s" % k, v) for k, v in PATHS]


def todo_list(f, results, calc):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not yes(f["frozen"]):
        extra.append(("立即挂失或冻结账户", "越快越好，这是止损第一动作"))
    if not yes(f["password"]):
        extra.append(("更换全部密码并关闭免密代扣", "取款、网银、支付密码全部换"))
    if not yes(f["police"]):
        extra.append(("报警并取得受案回执", "维权基础材料，越早越好"))
    if not has_content((f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")):
        extra.append(("列证据清单并编号成册", "流水、挂失回执、报警回执、答复函"))
    if not filled(f["detail"]):
        extra.append(("补齐交易经过", "钱怎么被刷走的、发生在哪、什么时间"))
    if not calc["可测算"]:
        extra.append(("核算盗刷金额", "以银行完整流水为准，标明笔数与已追回"))
    extra.append(("书面提出异议并索取受理回执", "电话口头说无效，必须留书面"))
    extra.append(("查询征信并提出异议", "防止盗刷记录影响征信"))
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
    "二、交易性质与争议类型",
    "三、紧急止损处置核查",
    "四、损失金额与笔数测算",
    "五、银行责任与核验核查",
    "六、处置时限与维权时限",
    "七、证据清单与缺口",
]


def render(f, results, calc, steps, todos, today, gaps):
    L = []
    L.append("# 银行卡盗刷核查与止损追回报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 账户：%s" % (f["account"] or "未填"))
    L.append("- 交易性质：%s" % (f["detail"][:40] if filled(f["detail"]) else "未填"))
    L.append("- 实际损失：%s" % money(calc["损失"]))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在对你明显不利的状态或银行侧失职点，必须先处理。**"
                 "先把挂失、改密、报警三件事办完，再谈索赔。")
    elif risk:
        L.append("**判定：基础动作已做但仍有明确风险点，**"
                 "建议按第五、六段补齐书面材料后再向监管或法院推进。")
    else:
        L.append("**判定：采集表关键项未填，暂时给不出确定结论；**"
                 "请把交易经过、金额、已采取的处置与银行答复填完再重跑。"
                 "**未填的一律不算通过。**")
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

    L.append("## 八、紧急止损动作清单")
    L.append("")
    L.append("| 动作 | 说明 |")
    L.append("|---|---|")
    for name, txt in URGENT:
        L.append("| %s | %s |" % (name, txt.replace("|", " ")))
    L.append("")

    L.append("## 九、维权路径与时限")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 十、证据缺口速查")
    L.append("")
    if not gaps:
        L.append("当前填写的材料已较完整。")
    else:
        L.append("| 缺失类别 | 补法 |")
        L.append("|---|---|")
        for g in gaps[:12]:
            L.append("| %s | %s |" % (g, EVID_FIX.get(g, "按操作卡补齐")))
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
    L.append("- 依**通用规则**整理，**不替代律师意见**；"
             "银行与支付机构的安全义务、举证责任分配，"
             "**以监管规定与司法机关认定为准**。")
    L.append("- 报告金额按已填信息汇总，**实际损失以银行流水与最终认定为准**。")
    L.append("- 不预测公安机关是否立案、银行是否赔偿，也不预测诉讼结果。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 卡号、身份证号、账号等敏感信息**本地处理，不要外发**。")
    L.append("- 本结果依通用规则整理，不替代专业意见，最终以主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps, calc):
    return {
        "核查日期": today.isoformat(),
        "实际损失": calc["损失"],
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "损失测算": {
            "可测算": calc["可测算"],
            "交易金额": calc["交易金额"],
            "已追回": calc["已追回"],
            "损失": calc["损失"],
            "笔数": calc["笔数"],
        },
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "account": get_text(kv, ["涉事银行卡或账户", "账户", "卡号"]),
        "discover_date": get_text(kv, ["发现盗刷日期", "发现时间", "发现日期"]),
        "detail": get_text(kv, ["盗刷交易经过", "交易经过", "经过"]),
        "channel": get_text(kv, ["交易渠道", "发生渠道", "在哪里发生"]),
        "amount": get_text(kv, ["盗刷金额", "涉案金额", "金额"]),
        "count": get_text(kv, ["盗刷笔数", "笔数", "发生几笔"]),
        "recovered": get_text(kv, ["已追回金额", "已追回", "追回金额"]),
        "frozen": get_text(kv, ["是否已挂失或冻结", "是否已挂失", "挂失冻结"]),
        "frozen_date": get_text(kv, ["挂失或冻结日期", "挂失日期", "冻结日期"]),
        "password": get_text(kv, ["密码与免密授权是否已处理", "是否改密码",
                                "密码是否已更改", "免密是否关闭"]),
        "police": get_text(kv, ["是否已报警", "是否报警", "报警情况"]),
        "verify": get_text(kv, ["银行是否做了交易核验", "银行核验情况", "核验与风控情况"]),
        "bank_response": get_text(kv, ["银行如何答复", "银行答复", "银行说法"]),
        "evidence_owned": get_text(kv, ["已有材料勾选", "材料勾选", "证据勾选"]),
        "evidence_desc": get_text(kv, ["材料清单", "已有材料", "证据清单"]),
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

    missing = []
    if not filled(f["detail"]):
        missing.append("盗刷交易经过")
    if not filled(f["amount"]):
        missing.append("盗刷金额")
    if not filled(f["frozen"]):
        missing.append("是否已挂失或冻结")

    calc = calc_loss(f)
    results = [
        ("交易性质与争议类型", checks_classify(f)),
        ("紧急止损处置核查", checks_urgent(f)),
        ("损失金额与笔数测算", checks_loss(f, calc)),
        ("银行责任与核验核查", checks_fault(f) + checks_verify(f)),
        ("处置时限与维权时限", checks_time(f, today)),
        ("证据清单与缺口", checks_evidence(f)),
    ]
    steps = path_steps(f)
    todos = todo_list(f, results, calc)
    gaps = evidence_gap(f)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today, gaps, calc),
                         ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, calc, steps, todos, today, gaps)
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
