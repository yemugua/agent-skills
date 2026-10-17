#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼职刷单返利诈骗识别与止损追回。

用法：
  python parttime_scam_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python parttime_scam_check.py 采集表.md --json
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

# 刷单诈骗的阶段特征：这是判断"是否已进入圈套"的核心
SCAM_STAGES = [
    ("引流话术阶段", ["点赞", "关注", "加好友", "做任务", "点赞关注", "关注公众号",
                   "加群", "下载app", "刷抖音", "刷快手", "点链接", "扫码",
                   "抢单", "点赞员", "任务群", "兼职群", "日结", "手机就能做",
                   "招聘", "招募", "拉群", "进群", "加微信", "加我微信",
                   "带你做", "做单", "第一单", "先做几单"]),
    ("小额返利阶段", ["返利", "返现", "佣金", "提成", "几块钱", "一两块", "十几块",
                   "小额", "尝到甜头", "第一单", "先返", "垫付几十", "垫了几十",
                   "红包", "奖励", "提现", "到账"]),
    ("垫资放大阶段", ["垫付", "垫资", "充值", "连单", "多单", "大单", "凑单",
                   "组合单", "订单金额", "本金", "连充", "大额垫付", "一万",
                   "两万", "三万", "五万", "十万", "越多返", "按比例返"]),
    ("冻结解冻阶段", ["解冻", "冻结", "刷满", "做完任务", "完成指标", "达标",
                   "未完成", "任务失败", "需要继续", "继续转", "补单", "解冻费",
                   "保证金", "申诉", "取消资格", "信誉", "流水不够", "再充"]),
    ("威胁拉黑阶段", ["拉黑", "删除", "举报", "曝光", "威胁", "不能报警",
                   "别报警", "丢人", "告诉家人", "收回", "起诉你", "曝光隐私"]),
]

# 诈骗平台类型
SCAM_PLATFORMS = [
    ("刷单返利类", ["刷单", "返利", "返现", "垫付", "垫资", "刷单返", "刷单兼职",
                "任务返", "垫了", "返了", "做单", "垫单", "本金", "拍下", "下单"]),
    ("点赞点赞类", ["点赞", "关注", "短视频点赞", "视频号点赞", "快手", "抖音任务"]),
    ("打字录入类", ["打字", "录入", "问卷", "数据标注", "转写", "客服", "话术",
                 "抄写", "录入员"]),
    ("虚假投资类", ["投资", "炒股", "基金", "虚拟币", "数字货币", "博彩", "彩票",
                 "带单", "操盘", "内部消息", "稳赚"]),
    ("仿冒客服类", ["客服", "刷好评", "好评返现", "退款客服", "假一赔十", "理赔"]),
]

# 核心红旗信号
RED_FLAGS = [
    ("以招聘兼职为名引流", ["招兼职", "招聘", "招募", "轻松日入", "月入过万",
                     "高薪", "门槛低", "零经验", "学生党", "宝妈", "在家就能做",
                     "手机就能做", "动动手指"]),
    ("要求垫资做任务", ["垫付", "垫资", "充值", "本金", "先付", "自己出钱",
                  "资金垫付", "拍下", "下单"]),
    ("以高额返利诱导", ["返利", "返现", "佣金", "提成", "高额返", "利润", "分成",
                  "利息", "日息", "回报率", "千分之五", "万分之一"]),
    ("宣称零风险稳赚", ["无风险", "零风险", "稳赚", "包赚", "保本", "一定",
                  "百分百", "保证", "必返", "无风险"]),
    ("制造时间紧迫感", ["名额有限", "限时", "马上", "立刻", "抓紧", "最后一天",
                  "只招", "先到先得", "过期不候", "赶紧"]),
    ("拉群或转到隐蔽环境操作", ["群里", "私聊", "加微信", "下载", "专用app",
                       "境外", "国外", "不受监管", "不方便说", "保密"]),
]

# 财务损失要素
COST_ITEMS = [
    ("已充值 / 已垫付本金", ["充值", "垫付", "本金", "投入", "转出", "汇入",
                     "付了", "打了"]),
    ("返利到账", ["返利", "返现", "到账", "提现", "收到", "到帐", "返了"]),
    ("解冻 / 补单追加", ["解冻", "补单", "追加", "继续转", "再充", "保证金"]),
]

# 紧急止损
URGENT = [
    ("立即停止一切转账", "**这是第一位**。刷单诈骗的破局点就是「不再加钱」——"
                    "对方说的解冻、申诉、继续做单，全是让你交更多钱。"),
    ("拨打 96110 反诈专线", "96110 是全国反诈专线，可咨询并**协助对涉诈账户止付**。"
                      "也可拨 110 直接报警。"),
    ("申请紧急止付与冻结", "第一时间联系银行、支付平台（支付宝/云闪付等）"
                      "申请**紧急止付、账户冻结**，防止更多资金流出。"
                      "**越快越能保住剩余资金**。"),
    ("保存全部证据，不要删除", "**不要删 App、不要删聊天记录、不要退出群**。"
                        "这些是对接警和追赃挽损的基础。"),
    ("不要受「恐吓」而沉默", "对方说「不能报警」「会曝光隐私」正是诈骗的典型施压话术。"
                      "**报警是你的权利**，恐吓恰恰说明对方心虚。"),
    ("修改支付相关密码", "修改支付密码、网银密码，关闭小额免密与代扣授权，"
                    "**不要与他人共用账户**。"),
    ("排查是否被「帮信罪」牵连", "若在知情情况下提供了银行卡、收款码收款，"
                       "可能被认定为帮助信息网络犯罪活动罪，"
                       "**主动报警说明，争取从宽**。"),
    ("征信与账户安全自查", "查询征信报告，看是否因延迟还款留下不良记录；"
                     "确认名下无不明贷款与账户。"),
]

# 维权路径
PATHS = [
    ("第 1 步（1 小时内：止付与报警）",
     "停止转账 → 拨 **96110 / 110** 报警 → 联系银行与支付平台申请紧急止付。"
     "**说明自己被骗的时间线与对方账号**。"),
    ("第 2 步（24 小时内：固定证据）",
     "导出聊天记录（截图 + 录屏）、转账记录、App 页面、对方账号信息、"
     "群聊信息，**按时间顺序编号成册**。"),
    ("第 3 步（3 日内：提交材料）",
     "到派出所提交**受案回执**，这是后续所有维权的基础。"
     "如金额较大或对方有组织，**争取立为刑事案件（诈骗罪）**。"),
    ("第 4 步（配合调查与冻结）",
     "配合提供资金流向线索。**已转出资金若能快速止付，可望部分挽回**；"
     "已被取走或转移的，追赃周期较长。"),
    ("第 5 步（平台与渠道投诉）",
     "向涉事 App 平台投诉举报涉诈店铺与账号；"
     "若涉未成年人，**同步联系监护人保护与学校**。"),
    ("第 6 步（刑事追赃为主）",
     "此类案件以**刑事追赃**为主要途径。可通过律师申请追赃挽损，"
     "或参与法院审理阶段的**退赔退赃**程序。"),
    ("第 7 步（民事/行政兜底）",
     "若涉及平台未尽审核义务、支付机构风控不足，"
     "可另行主张相应责任。金额巨大的建议咨询律师。"),
]

# 证据类别
EVIDENCE = [
    ("引流与承诺记录", ["招聘", "兼职", "招工", "日结", "高薪", "承诺", "返利",
                   "截图", "宣传", "海报", "广告"]),
    ("聊天与任务指令", ["聊天", "微信", "qq", "群", "私信", "截图", "录屏", "记录"]),
    ("转账与支付记录", ["转账", "银行", "支付宝", "微信支付", "云闪付", "账单",
                  "流水", "凭证", "回单"]),
    ("任务平台页面", ["app", "页面", "订单", "任务", "截图", "录屏", "后台",
                 "链接", "小程序"]),
    ("对方账号与身份信息", ["账号", "银行卡", "收款码", "实名", "身份", "手机号",
                    "对方", "客服", "名字"]),
    ("报警与受案材料", ["报警", "受案", "回执", "派出所", "笔录", "立案"]),
    ("止损与冻结记录", ["止付", "冻结", "银行", "客服记录", "工单", "回执"]),
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
    if n in ("有", "是", "已经", "已", "已完成", "已做", "对", "没错"):
        return True
    return n.startswith("已") or n.startswith("有")


def no(v):
    n = norm(v)
    if n in ("无", "否", "没有", "未", "未做", "没", "正常"):
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
    s = str(s).replace(",", "").replace("，", "").replace("元", "")
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


def has_content(s):
    for part in str(s or "").split("|"):
        if filled(part):
            return True
    return False


# ------------------------------------------------------------------ 一 定性
def classify(f):
    # 类型判断要看全部经历类字段：平台名本身常常不含"刷单"，
    # 而"垫付/返利"往往只出现在任务流程和聊天要点里。
    txt = "|".join([
        f.get("platform", "") or "", f.get("detail", "") or "",
        f.get("promise", "") or "", f.get("task_flow", "") or "",
        f.get("chat_log", "") or "",
    ])
    if not has_content(txt):
        return []
    return [lbl for lbl, ws in SCAM_PLATFORMS if hit_any(txt, ws) is True]


def detect_stages(f):
    txt = "|".join([
        f.get("detail", "") or "", f.get("chat_log", "") or "",
        f.get("task_flow", "") or "",
    ])
    if not has_content(txt):
        return []
    return [lbl for lbl, ws in SCAM_STAGES if hit_any(txt, ws) is True]


def checks_classify(f):
    out = []
    kinds = classify(f)
    stages = detect_stages(f)
    detail = f.get("detail", "")
    if unknown(detail):
        out.append(("事件性质", "待补正",
                    "怎么被找到、对方让做什么、你怎么付的钱未填。"
                    "**经历描述决定了后面所有判断**，"
                    "请尽量按时间顺序写清：引流 → 做任务 → 返利 → "
                    "垫资 → 出问题。"))
    elif not kinds:
        out.append(("事件性质", "待补正",
                    "经历描述里没识别出明确类型。请补充关键词："
                    "刷单/返利/垫付、点赞/关注、打字/录入、"
                    "投资/炒股/博彩、客服/退款。"))
    else:
        out.append(("事件性质", "有风险",
                    "本次涉及：**%s**。**刷单返利本身几乎必然是诈骗**——"
                    "**正常的兼职不会要求你先掏钱**。凡是以「做任务」"
                    "为名要求垫资的，都应按诈骗处理。" % "、".join(kinds)))
    if stages:
        out.append(("被骗阶段定位", "不通过",
                    "经历中出现：**%s**。**这是最经典的刷单诈骗推进套路**——"
                    "先用小额返利建立信任，再诱导大额垫付，"
                    "最后以「解冻/补单/保证金」为名继续要钱。"
                    "**整个流程是设计好的，不存在「做完就能提现」**。"
                    % "、".join(stages)))
    else:
        out.append(("被骗阶段定位", "待补正",
                    "没识别出明显的诈骗阶段。请补充具体过程："
                    "对方让你做什么、要你付什么钱、"
                    "后来为什么拿不出来。"))
    return out


# ------------------------------------------------------------------ 二 红旗信号
def checks_redflags(f):
    out = []
    txt = "|".join([
        f.get("promise", "") or "", f.get("chat_log", "") or "",
        f.get("task_flow", "") or "", f.get("detail", "") or "",
    ])
    if not has_content(txt):
        out.append(("话术红旗信号", "待补正",
                    "对方当初怎么说的、现在怎么说的都没填。"
                    "**话术原话是判定的核心依据**，"
                    "请尽量把对方的原话抄进采集表。"))
        return out
    hits = [lbl for lbl, ws in RED_FLAGS if hit_any(txt, ws) is True]
    if hits:
        out.append(("话术红旗信号", "不通过",
                    "命中 **%d 项**红旗信号：%s。"
                    "**每一项单独看都像巧合，合在一起就是标准的"
                    "刷单诈骗话术**。" % (len(hits), "、".join(hits))))
    else:
        out.append(("话术红旗信号", "有风险",
                    "未命中典型话术，但仍要留意："
                    "**只要要求垫资做任务，就已具备诈骗特征**。"
                    "话术可能换新，结构不会变。"))
    # 是否已提出要钱
    ask = hit_any(txt, ["垫付", "充值", "本金", "自己出钱", "先付", "转出"]) is True
    if ask:
        out.append(("是否已被要求出资", "不通过",
                    "**对方已要求你先出资**。这是刷单诈骗的核心动作——"
                    "**你在这一步就已经是被害人了**，"
                    "后面所有「解冻」都是继续骗你。"))
    else:
        out.append(("是否已被要求出资", "待补正",
                    "对方是否要求过你出资未填。"
                    "**这一步决定了是否已实际受骗**。"))
    return out


# ------------------------------------------------------------------ 三 资金与损失
def calc_loss(f):
    """净损失 = 已投入 − 已退回。

    ⚠️ 解冻/追加投入 **通常已经包含在已投入总额里**（是总额中后来又追加的那部分），
    **不能再加一次**，否则损失会重复计算、虚高一倍。
    """
    a = parse_num(f.get("paid_amount", ""))
    b = parse_num(f.get("refunded", ""))
    if a is None:
        return None, None, None
    back = b if b is not None else 0.0
    return a, back, a - back


def checks_money(f):
    out = []
    a = f.get("paid_amount", "")
    if unknown(a):
        out.append(("已投入金额", "待补正",
                    "一共给对方转了多少钱没填。**金额决定案件性质与管辖**——"
                    "金额较大的应尽快报警并争取刑事立案。"))
    else:
        amt = parse_num(a)
        _, back, net = calc_loss(f)
        extra = parse_num(f.get("extra_frozen", ""))
        tip = ""
        if extra and extra > 0 and amt is not None and extra <= amt:
            tip = ("　注意：追加投入 %s **已包含在已投入总额里**，"
                   "**没有重复计入净损失**。" % money(extra))
        out.append(("已投入金额", "有风险",
                    "累计转出 **%s**，已退回 %s，**净损失约 %s**。%s"
                    "**每一笔都要有转账记录**，"
                    "**没有凭证的单笔可能不被认定**。"
                    % (money(amt), money(back), money(net), tip)))
        if amt is not None and amt >= 50000:
            out.append(("损失金额是否已达刑事报案标准", "不通过",
                        "净损失 **%s**，已达到刑事案件通常的报案量级。"
                        "**立即报警并争取立为诈骗案**——"
                        "刑事追赃是这类钱唯一现实的追回路径。"
                        % money(net)))
        elif amt is not None and amt >= 5000:
            out.append(("损失金额是否已达刑事报案标准", "有风险",
                        "净损失 **%s**，属较大金额。"
                        "**建议报警并提供全部材料**，"
                        "即便最终按治安案件受理，也应留受案回执。"
                        % money(net)))
        else:
            out.append(("损失金额是否已达刑事报案标准", "有风险",
                        "净损失 **%s**。金额虽小，**也建议报警备案**——"
                        "小额同样属于合法权益受侵害。" % money(net)))
    b = f.get("refunded", "")
    if unknown(b):
        out.append(("已退回金额", "待补正",
                    "有没有拿回来一部分没填。**已退回的要在流水里区分**，"
                    "否则容易把返利和本金算混。"))
    elif parse_num(b) is not None and parse_num(b) > 0:
        out.append(("已退回金额", "有风险",
                    "已退回 %s。**注意区分**：刷单初期返的几十元"
                    "是小额诱饵，**不能当成对方守信**。" % b))
    else:
        out.append(("已退回金额", "不通过",
                    "**一分钱都没退**。这符合诈骗特征——"
                    "对方从头到尾的目标就是钱。"))
    c = f.get("extra_frozen", "")
    if unknown(c):
        out.append(("解冻或追加投入", "待补正",
                    "「解冻/补单/追加投入」这一项请务必如实填写。"
                    "**这是诈骗最容易让你加码的环节**——"
                    "如果你还没付，**现在停止就是止损**。"))
    elif parse_num(c) and parse_num(c) > 0:
        out.append(("解冻或追加投入", "不通过",
                    "在出问题后**又追加投入了 %s**。"
                    "**这正是对方的目的**。**现在立刻停止，"
                    "不要再信任何「再充一次就放款」的说法**。" % c))
    else:
        out.append(("解冻或追加投入", "通过",
                    "**未在出问题时追加投入**。"
                    "**这是当前最重要的一条止损成果**——"
                    "**接下来务必守住，不要再转任何钱**。"))
    return out


# ------------------------------------------------------------------ 四 处置与报案
def checks_report(f):
    out = []
    a = f.get("reported", "")
    if unknown(a):
        out.append(("是否已报警", "待补正",
                    "报没报警未填。**刷单诈骗只有走刑事才有追回可能**——"
                    "民事协商在这个场景下基本没用。"))
    elif yes(a):
        out.append(("是否已报警", "通过",
                    "已报警。**这是当前最正确的一步**。"
                    "**务必取得受案回执**，并保留后续联系记录。"))
    else:
        out.append(("是否已报警", "不通过",
                    "**尚未报警**。这类钱追回几乎全靠刑事程序，"
                    "**时间越早越好**——资金流向越往下追，"
                    "越容易被转走取现。**现在就拨 96110 或 110**。"))
    b = f.get("stopped", "")
    if unknown(b):
        out.append(("是否已停止转账", "待补正",
                    "停了没停未填。**停止转账是破局点**——"
                    "只要不再加钱，损失就不会扩大。"))
    elif yes(b) or hit_any(b, ["停了", "停止", "不转了", "没再转", "已经停"]) is True:
        out.append(("是否已停止转账", "通过",
                    "**已停止转账，做得对**。"
                    "**守住这一点比什么都重要**——"
                    "任何后续「解冻」都是骗局。"))
    else:
        out.append(("是否已停止转账", "不通过",
                    "**尚未停止转账**。如果对方正在以「解冻」「申诉」"
                    "为名要钱，**现在立刻停止**。"
                    "**再转下去只会让损失扩大，且无法追回**。"))
    c = f.get("contacted_bank", "")
    if unknown(c):
        out.append(("是否已联系银行或支付平台止付", "待补正",
                    "有没有申请止付没填。"
                    "**止付是时间窗口内最有效的动作**——"
                    "资金还在流转时有机会拦下。"))
    elif yes(c) or hit_any(c, ["打了", "联系了", "申请了", "止付", "冻结"]) is True:
        out.append(("是否已联系银行或支付平台止付", "通过",
                    "已申请止付/冻结。**继续跟进书面结果**。"))
    else:
        out.append(("是否已联系银行或支付平台止付", "不通过",
                    "**尚未申请止付**。**立刻联系银行与支付平台**"
                    "（支付宝/云闪付客服）申请紧急止付与账户冻结。"
                    "**这是钱还能不能追回来的关键窗口**。"))
    d = f.get("kept_evidence", "")
    if unknown(d):
        out.append(("证据是否已保留", "待补正",
                    "证据留没留未填。**不要删 App、不要删聊天记录**——"
                    "删了等于自己毁掉证据。"))
    elif yes(d) or hit_any(d, ["截图", "录屏", "保存", "导出", "留了", "备份"]) is True:
        out.append(("证据是否已保留", "通过",
                    "证据已保留。**建议按时间顺序编号成册**，"
                    "并做一次完整备份。"))
    else:
        out.append(("证据是否已保留", "不通过",
                    "**证据可能缺失**。立即开始保留："
                    "聊天截图与录屏、转账记录、App 页面、"
                    "对方账号信息、群聊记录。"))
    e = f.get("account_risk", "")
    if unknown(e):
        out.append(("是否涉及出借账户", "待补正",
                    "有没有用自己的银行卡或收款码帮对方过账未填。"
                    "**这可能让你被牵连进刑事案件**，"
                    "知情也要说清。"))
    elif hit_any(e, ["出借", "借出", "借给", "出借账户", "提供", "帮忙收", "帮忙转",
                   "过账", "收款码", "账户", "借卡", "帮收", "代收", "代为收",
                   "用我的卡", "用我的账户", "我的银行卡给"]) is True:
        out.append(("是否涉及出借账户", "不通过",
                    "**存在为对方提供账户或收款通道的情形**。"
                    "这可能涉及**帮助信息网络犯罪活动罪（帮信罪）**。"
                    "**主动向公安机关说明，争取从宽处理**——"
                    "**隐瞒会更被动**。"))
    else:
        out.append(("是否涉及出借账户", "通过",
                    "**未涉及账户出借**。这是好事——"
                    "**你的责任范围仅止于自己被骗**。"))
    return out


# ------------------------------------------------------------------ 五 证据
def checks_evidence(f):
    out = []
    a = f.get("evidence_owned", "") or ""
    b = f.get("evidence_desc", "") or ""
    if not has_content(a) and not has_content(b):
        out.append(("证据总览", "待补正",
                    "已有证据既没勾选也没写清单。"
                    "**这类案件全靠证据说话**——"
                    "没有转账记录和聊天记录，"
                    "几乎不可能立案与追赃。"))
        return out
    for label, keys in EVIDENCE:
        hit = [k for k in keys if k in a or k in b]
        if hit:
            out.append((label, "通过",
                        "已具备：%s。**原件留存、多处备份**。" % "、".join(hit)))
        else:
            out.append((label, "有风险", "尚无%s材料，这类缺口会让追赃难以推进。" % label))
    return out


EVID_FIX = {
    "引流与承诺记录": "保存招聘广告、承诺返利的截图、门店/群公告",
    "聊天与任务指令": "截图 + 录屏完整聊天，含对方账号昵称与头像",
    "转账与支付记录": "打印银行/支付平台账单，逐笔标注金额与时间",
    "任务平台页面": "录屏任务页面、订单页、后台数据页",
    "对方账号与身份信息": "记录收款账号、实名信息、链接域名、App 来源",
    "报警与受案材料": "留存受案回执、笔录、后续联系记录",
    "止损与冻结记录": "保存银行与平台客服工单、止付与冻结结果",
}


def evidence_gap(f):
    a = f.get("evidence_owned", "") or ""
    b = f.get("evidence_desc", "") or ""
    got = a + "|" + b
    if not has_content(got):
        return [x[0] for x in EVIDENCE]
    gaps = []
    for label, keys in EVIDENCE:
        if not any(k in got for k in keys):
            gaps.append(label)
    if not any(k in got for k in ["转账", "银行", "支付宝", "支付", "账单"]):
        gaps.append("转账与支付记录")
    if not any(k in got for k in ["聊天", "微信", "qq", "群", "私信"]):
        gaps.append("聊天与任务指令")
    seen = set()
    res = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            res.append(g)
    return res


# ------------------------------------------------------------------ 路径与待办
def path_steps(f):
    return [(k, v) for k, v in PATHS]


def todo_list(f, results):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not yes(f.get("stopped", "")):
        extra.append(("立即停止一切转账", "破局点是「不再加钱」"))
    if not yes(f.get("reported", "")):
        extra.append(("拨打 96110 或 110 报警", "刑事追赃是这类钱唯一现实追回路径"))
    if not yes(f.get("contacted_bank", "")):
        extra.append(("申请紧急止付与账户冻结", "资金流转中的窗口很短，越快越好"))
    if hit_any(f.get("account_risk", ""), ["出借", "过账", "收款码", "代收", "帮收"]) is True:
        extra.append(("主动说明账户出借情况", "可能涉及帮信罪，主动说明争取从宽"))
    if not yes(f.get("kept_evidence", "")):
        extra.append(("保存全部证据", "不要删 App、不要删聊天记录"))
    seen = set()
    res = []
    for n, s in todos + extra:
        if n not in seen:
            seen.add(n)
            res.append((n, s))
    return res


# ------------------------------------------------------------------ 报告
SECTIONS = [
    "二、事件性质与骗局阶段",
    "三、话术红旗信号识别",
    "四、资金投入与损失核算",
    "五、处置与报案核查",
    "六、证据清单与缺口",
]


def render(f, results, steps, todos, today, gaps):
    L = []
    L.append("# 兼职刷单返利诈骗核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 事件类型：%s" % ("、".join(classify(f)) or "未填"))
    L.append("- 已投入：%s" % (f.get("paid_amount", "") or "未填"))
    L.append("- 净损失：%s" % money(calc_loss(f)[2]))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：已符合刷单返利诈骗的典型特征，存在明确不利因素。**"
                 "**请立即停止任何转账，并尽快报警**——"
                 "**这类资金追回主要依靠刑事程序，民事协商基本无效**。")
    elif risk:
        L.append("**判定：未发现明确不利因素，但经历描述不完整，"
                 "无法给出确定结论。**"
                 "**只要对方要求你先垫资，就已具备诈骗特征**。")
    else:
        L.append("**判定：采集表关键项未填，暂时给不出确定结论；**"
                 "请把事件经过、对方承诺、已投入金额、"
                 "是否报警与是否已停止转账填完再重跑。"
                 "**未填的一律不算通过。**")
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(todo))
    L.append("")
    L.append("**最该先做的三件事**：")
    L.append("")
    L.append("1. **立刻停止一切转账**——解冻、补单、申诉都是继续骗钱")
    L.append("2. **拨 96110 或 110 报警**，并申请紧急止付")
    L.append("3. **保存全部证据**：不要删 App、不要删聊天记录")
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

    L.append("## 七、紧急止损动作")
    L.append("")
    for k, v in URGENT:
        L.append("- **%s**：%s" % (k, v))
    L.append("")

    L.append("## 八、路径与维权流程")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 九、报警要点与法律提示")
    L.append("")
    L.append("| 项 | 内容 |")
    L.append("|---|---|")
    L.append("| 报警电话 | 110（报警）、96110（全国反诈专线） |")
    L.append("| 主要罪名 | 诈骗罪（以非法占有为目的，虚构事实骗取财物） |")
    L.append("| 关键证据 | 转账记录、聊天记录、对方账号信息、任务页面 |")
    L.append("| 必拿文书 | 受案回执（没有就再去要） |")
    L.append("| 追回方式 | 刑事追赃为主，也可参与退赔退赃程序 |")
    L.append("")

    L.append("## 十、证据缺口速查")
    L.append("")
    if not gaps:
        L.append("当前填写的材料已较完整。")
    else:
        L.append("| 缺失类别 | 补法 |")
        L.append("|---|---|")
        for g in gaps[:12]:
            L.append("| %s | %s |" % (g, EVID_FIX.get(g, "尽快补齐并备份")))
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
             "案件性质与追赃结果，**以公安机关与司法机关认定为准**。")
    L.append("- 报告金额按已填凭证汇总，**实际追回金额以侦查与司法结果为准**。")
    L.append("- **不预测能否追回、能追回多少**。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 涉及**双方账号、身份证、银行卡等个人信息**，"
             "**本地处理，不要外发**；"
             "**不要在公开平台曝光对方，也不要联系对方家属**。")
    L.append("- 本结果依通用规则整理，不替代专业意见，"
             "最终以主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps):
    main_loss, back, net = calc_loss(f)
    return {
        "核查日期": today.isoformat(),
        "事件类型": classify(f),
        "骗局阶段": detect_stages(f),
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "已投入": main_loss,
        "已退回": back,
        "净损失": net,
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "detail": get_text(kv, ["事件经过", "事情经过", "经过", "被骗经过"]),
        "platform": get_text(kv, ["对方平台或App", "对方平台", "平台", "在哪个App"]),
        "promise": get_text(kv, ["对方承诺", "机构承诺", "对方怎么说", "承诺内容"]),
        "task_flow": get_text(kv, ["任务流程", "让你做什么", "任务内容", "要求"]),
        "chat_log": get_text(kv, ["聊天记录要点", "聊天要点", "对方说法", "聊天记录"]),
        "paid_amount": get_text(kv, ["已投入金额", "一共转了多少钱", "已付金额",
                              "充值金额"]),
        "refunded": get_text(kv, ["已退回金额", "拿回来多少", "退回金额"]),
        "extra_frozen": get_text(kv, ["解冻或追加投入", "追加投入", "补单金额",
                                 "解冻投入"]),
        "reported": get_text(kv, ["是否已报警", "报警没有", "是否报案"]),
        "stopped": get_text(kv, ["是否已停止转账", "是否停止转账", "停了没停"]),
        "contacted_bank": get_text(kv, ["是否已联系银行或支付平台止付",
                                  "是否已止付", "联系银行没有"]),
        "kept_evidence": get_text(kv, ["证据是否已保留", "证据是否保留", "证据留没留"]),
        "account_risk": get_text(kv, ["是否涉及出借账户", "是否出借账户",
                                 "有没有借银行卡"]),
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
        missing.append("事件经过")
    if not filled(f["paid_amount"]):
        missing.append("已投入金额")
    if not filled(f["reported"]):
        missing.append("是否已报警")

    results = [
        ("事件性质与骗局阶段", checks_classify(f)),
        ("话术红旗信号识别", checks_redflags(f)),
        ("资金投入与损失核算", checks_money(f)),
        ("处置与报案核查", checks_report(f)),
        ("证据清单与缺口", checks_evidence(f)),
    ]
    steps = path_steps(f)
    todos = todo_list(f, results)
    gaps = evidence_gap(f)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today, gaps),
                         ensure_ascii=False, indent=2))
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
