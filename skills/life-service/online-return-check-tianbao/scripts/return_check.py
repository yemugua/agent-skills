# -*- coding: utf-8 -*-
"""网购退货七天无理由核查 v1.0.0

输入：按 templates/网购退货信息采集表.md 填写的 Markdown
输出：九段式核查报告（或 --json 摘要）

判定纪律：
- 依《消费者权益保护法》《民法典》合同编等通用规则整理，不替代律师意见
- 法律有分歧的地方如实写"存在两种口径"，不断言裁判结果
- 用户填什么就用什么，未填的一律标「未填」，不算通过
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

VERSION = "1.0.0"

PLACEHOLDER = (
    "【待填】",
    "填什么",
    "是 / 否",
    "有 / 无",
    "___",
    "待填",
    "请填写",
)

# 质量类事由关键词（用于区分"质量问题路径"与"无理由路径"）
QUALITY_KEYS = (
    "质量问题", "质量缺陷", "瑕疵", "故障", "损坏", "破损", "变质", "腐烂",
    "无法启动", "不能用", "不能正常", "失灵", "开裂", "漏液", "屏幕",
    "描述不符", "货不对板", "不符", "假冒", "假货", "翻新",
    "错发", "漏发", "少发", "延迟发货", "延期发货",
)

# 否定式前缀（子串误判防护：非营运含营运 同理）
NEG_PREFIX = ("非", "不属于", "不是", "不含", "未", "无")

RE_COLON = re.compile(r"^(.{2,40})[:：]\s*(.*)$")
RE_DATE = re.compile(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})")
RE_DATE2 = re.compile(r"^(\d{1,2})[-/.月](\d{1,2})日?$")


# ------------------------------------------------------------------ 解析
def norm(s):
    if s is None:
        return ""
    t = str(s)
    t = t.replace("\u3000", " ").replace(" ", "")
    t = t.replace("\uff08", "(").replace("\uff09", ")")
    t = t.replace("|", " ").strip()
    return t


def clean(s):
    if s is None:
        return ""
    return str(s).strip().strip("|").strip()


def is_ph(v):
    t = norm(v)
    if not t:
        return True
    for w in PLACEHOLDER:
        if norm(w) and norm(w) in t:
            return True
    if t in ("-", "--", "/", "\u2014"):
        return True
    if t and set(t) <= set("-\u2014:=/"):
        return True
    return False


def is_row(ln):
    s = ln.strip()
    return s.startswith("|") and s.count("|") >= 2


def split_row(ln):
    s = ln.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def parse_fields(text):
    """同时支持 '| 字段 | 值 |' 表格行 和 '字段：值' 冒号行。"""
    rows = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith(">"):
            continue
        if is_row(s):
            c = split_row(s)
            if len(c) >= 2:
                rows.append((norm(c[0]), clean(c[1])))
            continue
        if s.startswith(("-", "*", ">")):
            continue
        m = RE_COLON.match(s.replace("|", " "))
        if m:
            rows.append((norm(m.group(1)), m.group(2).strip()))
    return rows


def get_text(text, *labels):
    """最长别名优先：先按标签长度降序逐个试，避免短别名抢走长字段。"""
    rows = parse_fields(text)
    labs = sorted([norm(x) for x in labels if norm(x)], key=lambda x: -len(x))
    for lb in labs:
        for k, v in rows:
            if lb in k and not is_ph(v):
                return clean(v)
    return ""


def get_int(text, *labels):
    v = get_text(text, *labels)
    if not v:
        return None
    t = norm(v)
    dig = ""
    for ch in t:
        if ch.isdigit():
            dig += ch
        elif dig:
            break
    if not dig:
        return None
    try:
        return int(dig)
    except Exception:
        return None


def parse_num(v):
    """金额/数值抽取：¥5,499.00 元 -> 5499.0。文字列不要用。"""
    if v is None:
        return None
    t = norm(str(v)).replace(",", "").replace("¥", "").replace("元", "")
    m = re.search(r"\d+(?:\.\d+)?", t)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_date(v, base=None):
    """支持 2026-09-30 / 2026年9月30日 / 09-30（补年份）。"""
    if not v:
        return None
    t = norm(v)
    m = RE_DATE.search(t)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            return None
    m2 = RE_DATE2.match(t)
    if m2 and base is not None:
        try:
            return dt.date(base.year, int(m2.group(1)), int(m2.group(2)))
        except Exception:
            return None
    return None


def yes(text, *labels):
    v = get_text(text, *labels)
    if not v:
        return None
    t = norm(v)
    if "否" in t or "无" in t or "没有" in t or "未" in t or "不曾" in t:
        return False
    if "是" in t or "有" in t or "已" in t:
        return True
    return None


def has_cat(v, *kws):
    """商品类别匹配：否定式优先（非定制 ≠ 定制）。返回 True/False/None(未填)。"""
    t = norm(v)
    if not t:
        return None
    for kw in kws:
        if kw in t:
            for ng in NEG_PREFIX:
                if (ng + kw) in t:
                    return False
            return True
    return False


def ovr(base_v, explicit):
    """显式的是/否回答优先于类别推断。"""
    return explicit if explicit is not None else base_v


def fmt_num(v):
    if v is None:
        return "未填"
    try:
        f = float(v)
    except Exception:
        return str(v)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return ("%.2f" % f).rstrip("0").rstrip(".")


def money(v):
    return "\u00a5" + fmt_num(v)


def fmt_flag(v):
    if v is True:
        return "是"
    if v is False:
        return "**否**"
    return "未填"


def add_days(d, n):
    return d + dt.timedelta(days=n)


def days_left(d, base):
    return (d - base).days


# ------------------------------------------------------------------ 报告
def build_report(path, base=None):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return None, "读不了文件：%s" % e

    if base is None:
        base = dt.date.today()

    name = get_text(text, "商品名称")
    cat = get_text(text, "商品类别/性质", "商品类别", "商品性质")
    channel = get_text(text, "购买渠道")
    amount = parse_num(get_text(text, "订单实付金额", "实付金额", "订单金额"))
    order_date = parse_date(get_text(text, "下单日期"), base)
    sign_date = parse_date(get_text(text, "签收日期"), base)

    # ---- 四类法定除外
    ex_init = [
        ("消费者定作的", has_cat(cat, "定制", "定作", "量身", "来图", "刻字"),
         yes(text, "是否为定制/定作商品", "是否定制")),
        ("鲜活易腐的", has_cat(cat, "鲜活", "易腐", "生鲜", "水果", "海鲜", "鲜花", "水产", "冷冻", "冷藏"),
         yes(text, "是否为鲜活易腐商品", "鲜活易腐")),
        ("在线下载或消费者拆封的音像制品、计算机软件等数字化商品",
         has_cat(cat, "数字化", "在线下载", "软件", "游戏", "音像", "电子书", "虚拟", "充值", "卡密", "激活码"),
         yes(text, "是否为在线下载或拆封的数字化商品", "数字化商品")),
        ("交付的报纸、期刊", has_cat(cat, "报纸", "期刊", "杂志", "报刊"),
         yes(text, "是否为报纸期刊", "报纸期刊")),
    ]
    exceptions = []
    for desc, inferred, explicit in ex_init:
        v = ovr(inferred, explicit)
        exceptions.append((desc, v))

    # 第五类：其他根据商品性质并经消费者购买时确认不宜退货的商品
    marked = yes(text, "页面是否标注", "不支持七天无理由")
    confirmed = yes(text, "购买时是否单独确认过不宜退货", "购买时单独确认", "购买时确认")

    # ---- 拆封与完好
    unsealed = yes(text, "是否已拆封")
    purpose = get_text(text, "拆封目的")
    over_use = yes(text, "是否超出查验需要使用", "超出查验")
    intact = yes(text, "商品是否完好")
    gift_ok = yes(text, "赠品与配件是否可一并退回", "赠品与配件")
    activated = yes(text, "是否已联网激活或写入个人信息", "联网激活")

    # ---- 质量问题与举证
    reason = get_text(text, "退货理由")
    r_t = norm(reason)
    is_quality = any(k in r_t for k in QUALITY_KEYS) if r_t else None
    durable = yes(text, "是否为耐用商品", "耐用商品")
    flaw_days = get_int(text, "发现瑕疵距签收天数")
    in_3pack = yes(text, "是否在三包有效期内", "三包有效期")
    two_repair = yes(text, "是否经两次修理仍不能正常使用", "两次修理")

    # ---- 运费
    ship = parse_num(get_text(text, "退货寄回运费金额", "寄回运费", "运费金额"))
    ins = parse_num(get_text(text, "是否有运费险及赔付额度", "运费险"))
    promise = yes(text, "商家是否另行承诺承担运费", "承诺承担运费")

    # ---- 进度与证据
    applied = get_text(text, "是否已发起退款申请", "退款申请")
    applied_date = parse_date(applied, base)
    applied_yn = yes(text, "是否已发起退款申请", "退款申请")
    refused = yes(text, "商家是否拒绝")
    refuse_text = get_text(text, "商家拒绝理由原文", "拒绝理由")
    platform = yes(text, "是否已申请平台介入", "平台介入")
    platform_date = parse_date(get_text(text, "是否已申请平台介入", "平台介入"), base)
    video = yes(text, "是否有开箱视频")
    photo = yes(text, "是否有商品与外包装照片", "照片")
    weigh = yes(text, "是否有物流称重记录", "称重记录")
    chat_keep = yes(text, "是否留存商家拒退的聊天记录", "聊天记录")
    page_shot = yes(text, "是否留存商品页面快照", "页面快照")
    got_back = yes(text, "商家是否已收到退回商品", "收到退回商品")
    got_back_date = parse_date(get_text(text, "商家是否已收到退回商品", "收到退回商品"), base)

    key_filled = [name, sign_date, reason, order_date, cat]
    if not any([name, sign_date, reason, order_date]) and not cat:
        return None, ("没有解析到关键信息。至少填写「商品名称」「签收日期」「退货理由」"
                      "或「商品类别」中的一到两项，否则无法判断能不能退。")

    L = []
    A = L.append
    risks = []
    todo = []

    # ---------------- 路径判定
    hit_ex = [d for d, v in exceptions if v is True]
    ex_unknown = [d for d, v in exceptions if v is None]

    # 无理由路径
    if hit_ex:
        wr_state = "不通过"
        wr_note = "命中法定除外：%s" % "、".join(hit_ex)
    elif sign_date is None:
        wr_state = "待补正"
        wr_note = "缺签收日期，无法算七天窗口"
    else:
        last_b = add_days(sign_date, 7)      # 次日起算（对消费者有利）
        if base > last_b:
            wr_state = "不通过"
            wr_note = "已超过七天窗口（截止 %s）" % last_b.isoformat()
        elif over_use is True or intact is False:
            wr_state = "有风险"
            wr_note = "可能不被认定为商品完好，商家可据此拒退"
        elif unsealed is True and purpose and not any(
                k in norm(purpose) for k in ("检查", "查验", "试用", "验货", "查看")):
            wr_state = "有风险"
            wr_note = "拆封目的不明或非查验需要，需要举证"
        elif ex_unknown:
            wr_state = "待补正"
            wr_note = "尚有 %d 类除外情形未填，需补填核控" % len(ex_unknown)
        else:
            wr_state = "通过"
            wr_note = "在七天窗口内且未命中法定除外，可无理由退货"

    # 质量问题路径
    if is_quality is None:
        q_state = "待补正"
        q_note = "未填退货理由，无法判断是否属质量/违约路径"
    elif is_quality is False:
        q_state = "不通过"
        q_note = "属纯无理由退货，不走质量路径"
    else:
        q_state = "通过"
        q_note = "存在质量 / 违约事由，可依法主张退货、更换、修理"
        if in_3pack is True and two_repair is True:
            q_note += "；且在三包有效期内经两次修理仍不能正常使用，可要求退货"
        elif in_3pack is True:
            q_note += "；在三包有效期内，先修理 / 更换为宜"
        elif in_3pack is False:
            q_note += "；但三包有效期存疑（填了\"否\"），需核实凭证"

    # 举证责任倒置
    invert = False
    invert_note = ""
    if durable is True and sign_date is not None:
        deadline6 = add_days(sign_date, 183)
        if base <= deadline6:
            invert = True
            invert_note = ("该商品属耐用商品（如计算机、电视机、冰箱、空调器、洗衣机等），"
                       "自接受商品之日起六个月内发现瑕疵，"
                           "发生争议的由**经营者**承担有关瑕疵的举证责任"
                           "（倒置期至 %s）" % deadline6.isoformat())
        else:
            invert_note = "已超过六个月举证责任倒置期，需由消费者举证"
    elif durable is True and sign_date is None:
        invert_note = "属耐用商品但未填签收日期，无法判断六个月内与否"
    elif durable is False:
        invert_note = "非耐用商品 / 非装饰装修服务，不适用举证责任倒置"

    states = [wr_state, q_state]
    if "通过" in states:
        overall = "通过"
    elif "有风险" in states:
        overall = "有风险"
    elif "待补正" in states:
        overall = "待补正"
    else:
        overall = "不通过"

    # ---------------- 运费测算
    if is_quality is True or promise is True:
        payer = "经营者"
        payer_basis = "属质量问题 / 经营者违约（或商家另行承诺），退回运费由经营者承担"
    elif is_quality is False:
        payer = "消费者"
        payer_basis = "无理由退货，退回商品的运费由**消费者**承担（另有约定的按约定）"
    else:
        payer = "待定"
        payer_basis = "退货理由未填，运费归属待定"

    ship_v = ship if ship is not None else 0.0
    ins_v = ins if ins is not None else 0.0
    cover = min(ins_v, ship_v)
    rest = round(ship_v - cover, 2)
    if payer == "消费者":
        buyer_pay, seller_pay = rest, 0.0
    elif payer == "经营者":
        buyer_pay, seller_pay = 0.0, rest
    else:
        buyer_pay, seller_pay = None, None

    # ---------------- 风险项
    if marked is True and confirmed is not True:
        risks.append("商家标了\"不支持七天无理由\"，但购买时未经你单独确认，"
                     "该排除不能对抗你——关键是**购买时确认**，未确认的无效")
    if marked is True and confirmed is True:
        risks.append("购买时已单独确认不宜退货，该类商品可能不适用无理由退货，"
                     "但质量问题路径不受影响")
    if unsealed is True and not hit_ex:
        risks.append("已拆封，商家可能拿\"拆封不能退\"说事——为检查、试用而拆封且商品本身不污损的，"
                     "仍属于商品完好")
    if activated is True and refused is True:
        risks.append("商家以\"已联网激活\"为由拒退：笔记本整机不是在线下载或拆封的数字化商品，"
                     "以此排除七天无理由缺少法律依据")
    if gift_ok is False:
        risks.append("赠品 / 配件不能一并退回，经营者可能按差额扣款或拒绝全额退款")
    if over_use is True:
        risks.append("超出查验和确认品质、功能需要使用商品，价值贬损较大的视为商品不完好")
    if sign_date is not None:
        last_b = add_days(sign_date, 7)
        left = days_left(last_b, base)
        if 0 <= left <= 2:
            risks.append("七天无理由仅剩 %d 天，务必当天在系统里提交退货申请（以提交时间为准）" % left)
    if platform is False and refused is True:
        risks.append("商家已拒绝但你还没申请平台介入，时间拖久了平台举证窗口会收紧")
    if any(x is False for x in (video, photo, weigh, chat_keep, page_shot)):
        risks.append("关键证据有缺口，见第八段")
    if not risks:
        risks.append("已填项未发现明显不利风险（未填的不算通过）")

    # ---------------- 报告正文
    A("# 网购退货核查报告")
    A("")
    A("> 商品：%s｜生成日期：%s｜脚本版本 v%s" % (name or "未填", base.isoformat(), VERSION))
    A("")

    A("## 一、结论摘要")
    A("")
    A("- **能不能退：%s**" % overall)
    A("- 无理由退货路径：**%s** —— %s" % (wr_state, wr_note))
    A("- 质量问题 / 违约路径：**%s** —— %s" % (q_state, q_note))
    if invert:
        A("- 举证责任倒置：**适用**，%s" % invert_note)
    elif invert_note:
        A("- 举证责任倒置：不适用或未填——%s" % invert_note)
    if marked is True and confirmed is not True:
        A("- 注意：商家页面写了\"不支持七天无理由\"，但**购买时未经你单独确认**，"
          "这一条排不掉你的无理由退货权。")
    A("- **未填的一律不算通过**，只按你填了的判断；补填后请重跑一次。")
    A("")
    A("**已识别的风险点：**")
    A("")
    for msg in risks[:8]:
        A("- %s" % msg.replace("|", " ").replace("**", ""))
    A("")

    A("## 二、能不能退：路径判定")
    A("")
    A("| 路径 | 结论 | 依据 |")
    A("|---|---|---|")
    A("| 七天无理由退货 | %s | %s |" % (wr_state, wr_note))
    A("| 质量问题 / 经营者违约 | %s | %s |" % (q_state, q_note))
    A("")
    A("经营者采用网络、电视、电话、邮购等方式销售商品，消费者有权自**收到商品之日起七日内**退货，"
      "且无需说明理由。")
    A("")
    A("商品实付：%s；购买渠道：%s%s" % (
        money(amount) if amount is not None else "未填",
        channel or "未填",
        "；下单 %s" % order_date.isoformat() if order_date else ""))
    A("")

    A("## 三、七天无理由逐条核查")
    A("")
    A("| 事项 | 判定 | 说明 |")
    A("|---|---|---|")
    for desc, v in exceptions:
        if v is True:
            A("| %s | **命中（不适用无理由）** | 属法定除外商品 |" % desc)
        elif v is False:
            A("| %s | 未命中 | 不影响无理由退货 |" % desc)
        else:
            A("| %s | 未填 | 填了才能判断，未填不算通过 |" % desc)
    A("| 根据商品性质且**购买时确认**不宜退货 | %s | %s |" % (
        ("**命中**" if (marked is True and confirmed is True) else
         ("不成立（未经购买时确认）" if marked is True else
          ("未标 / 未填" if marked is None else "不适用"))),
        "关键是\"购买时确认\"：未经确认的\"不支持七天无理由\"无效"))
    A("")
    if sign_date:
        last_a = add_days(sign_date, 6)
        last_b = add_days(sign_date, 7)
        A("- 签收日期：%s" % sign_date.isoformat())
        A("- 口径①（签收当日算第 1 天）：截止 %s" % last_a.isoformat())
        A("- 口径②（自签收次日起算）：截止 %s —— **取对消费者有利的口径②**" % last_b.isoformat())
        A("- 距 today(%s) 还剩 %d 天" % (base.isoformat(), days_left(last_b, base)))
    else:
        A("- **签收日期未填**，七天窗口算不出来，请补填。")
    A("")

    A("## 四、拆封与商品完好判定")
    A("")
    A("| 项 | 情况 | 说明 |")
    A("|---|---|---|")
    A("| 是否已拆封 | %s | — |" % fmt_flag(unsealed))
    A("| 拆封目的 | %s | 检查 / 查验 / 试用而拆封的属于正常查验 |" % (purpose or "未填"))
    A("| 是否超出查验需要使用 | %s | 超出查验导致价值贬损较大的，视为商品不完好 |" % fmt_flag(over_use))
    A("| 商品是否完好 | %s | 本体、配件、商标标识齐全即完好 |" % fmt_flag(intact))
    A("| 赠品与配件能否一并退回 | %s | 赠品、配件应一并退回 |" % fmt_flag(gift_ok))
    A("| 是否已联网激活 / 写入个人信息 | %s | 整机预装系统的激活不等于数字化商品 |" % fmt_flag(activated))
    A("")
    if unsealed is True and not hit_ex:
        A("**\"拆封了就不能退\"是错的**：消费者为检查、试用商品而拆封，且商品本身不污损的，"
          "属于商品完好，商家不得以\"已拆封\"为由拒绝无理由退货"
          "（在线下载或消费者拆封的数字化商品除外）。")
        A("")
    A("商品完好的标准：能够保持原有品质、功能，商品本身、配件、商标标识齐全；"
      "超出查验和确认商品品质、功能需要而使用商品，导致价值贬损较大的，视为不完好"
      "（按商品性质与程度判断）。")
    A("")

    A("## 五、质量问题、\"三包\"与举证责任")
    A("")
    A("| 项 | 情况 | 说明 |")
    A("|---|---|---|")
    A("| 退货理由 | %s | — |" % (reason or "未填"))
    A("| 是否属质量 / 违约事由 | %s | 决定走哪条路径 |" % fmt_flag(is_quality))
    A("| 是否耐用商品 / 装饰装修服务 | %s | 机动车、计算机、电视机、电冰箱、空调器、洗衣机等 |" % fmt_flag(durable))
    A("| 发现瑕疵距签收 | %s | 六个月内是关键节点 |" % (
        ("%d 天" % flaw_days) if flaw_days is not None else "未填"))
    A("| 是否在三包有效期内 | %s | 有三包规定的，按修理 / 更换 / 退货顺序处理 |" % fmt_flag(in_3pack))
    A("| 是否两次修理仍不能正常使用 | %s | 满足即可要求退货 |" % fmt_flag(two_repair))
    A("")
    if invert:
        A("**举证责任倒置适用**：%s" % invert_note)
    elif invert_note:
        A(invert_note)
    A("")
    A("质量问题路径与七天无理由是两条路：质量问题不受七日期限限制，"
      "符合法定解除条件的可退；有\"三包\"规定的按三包办理。")
    A("")

    A("## 六、运费谁出（含算式）")
    A("")
    A("| 项 | 数值 |")
    A("|---|---|")
    A("| 退回运费 | %s |" % (money(ship) if ship is not None else "未填"))
    A("| 运费险赔付额度 | %s |" % (money(ins) if ins is not None else "未填"))
    A("| 经营者是否承诺承担 | %s |" % fmt_flag(promise))
    A("| 责任归属 | **%s** |" % payer)
    A("")
    A("算式：退回运费 %s − 运费险赔付 %s = 待承担 %s" % (
        money(ship_v), money(cover), money(rest)))
    if payer == "消费者":
        A("→ 无理由退货由消费者承担；你自付 **%s**。" % money(buyer_pay))
    elif payer == "经营者":
        A("→ %s；你自付 **%s**，经营者承担 %s。" % (payer_basis, money(buyer_pay), money(seller_pay)))
    else:
        A("→ 退货理由未填，暂无法归属，请先补填退货理由。")
    A("")
    A("运费规则：无理由退货的**退回运费由消费者承担**，经营者和消费者另有约定的按约定；"
      "属质量问题或经营者违约的，运费由经营者承担；有运费险的先按赔付额度结算，不足部分再按上述规则。")
    A("")

    A("## 七、时限倒计时与退款时限")
    A("")
    rows7 = []
    if sign_date:
        last_b = add_days(sign_date, 7)
        left = days_left(last_b, base)
        rows7.append(("七天无理由窗口", last_b.isoformat(),
                      "剩 %d 天" % left if left >= 0 else "已过期 %d 天" % (-left)))
    else:
        rows7.append(("七天无理由窗口", "未填", "补签收日期才能算"))
    if sign_date and durable is True:
        rows7.append(("举证责任倒置期（六个月）", add_days(sign_date, 183).isoformat(),
                      "耐用商品瑕疵举证由经营者承担"))
    if applied_date:
        rows7.append(("已发起退款申请", applied_date.isoformat(), "系统里有记录即可"))
    elif applied_yn:
        rows7.append(("已发起退款申请", "是（未填日期）", "补填申请日期便于举证"))
    else:
        rows7.append(("是否已发起退款申请", "未填 / 否", "先在系统内提交退货退款申请"))
    if got_back_date:
        rows7.append(("经营者收到退回商品", got_back_date.isoformat(),
                      "经营者应自收到退回商品之日起**七日内**返还价款，退款截止 %s"
                      % add_days(got_back_date, 7).isoformat()))
    elif got_back is False:
        rows7.append(("经营者收到退回商品", "尚未收到（未寄回）",
                      "寄回并保留物流签收记录，起算点从经营者收到当日开始"))
    else:
        rows7.append(("经营者收到退回商品", "未填", "填了才能算退款截止日"))
    rows7.append(("12315 投诉受理", "7 日内决定是否受理",
                  "60 日内办结，情况复杂可延长 30 日"))
    rows7.append(("民事诉讼时效", "3 年",
                  "自知道或应当知道权利受损及义务人之日起算；走到诉讼的最后一道"))
    rows7.append(("开箱视频 / 页面快照留存", "越快越好",
                  "页面下架、聊天记录清理后截图失效，先存网盘再存本地"))
    A("| 时间节点 | 日期 | 说明 |")
    A("|---|---|---|")
    for a_, b_, c_ in rows7:
        A("| %s | %s | %s |" % (a_, b_, c_))
    A("")
    A("经营者应当自收到退回商品之日起**七日内**返还消费者支付的商品价款；"
      "平台介入、退款方式不同的，返还时间另看平台规则。")
    A("")

    A("## 八、证据缺口与平台介入路径")
    A("")
    A("| 证据 | 是否有 | 说明 |")
    A("|---|---|---|")
    A("| 开箱视频（面单+外包装+拆封+全景一条录完） | %s | 最重要的一份 |" % fmt_flag(video))
    A("| 商品与外包装照片 | %s | 破损、污损、色差都要拍 |" % fmt_flag(photo))
    A("| 物流称重记录 | %s | 短少、错发靠重量差证明 |" % fmt_flag(weigh))
    A("| 商家拒退的聊天记录 | %s | 把\"不支持退\"的说法留在文字里 |" % fmt_flag(chat_keep))
    A("| 商品页面快照 / 宣传承诺 | %s | 描述不符、虚假宣传靠它 |" % fmt_flag(page_shot))
    A("")
    gaps = []
    if video is False:
        gaps.append("开箱视频")
    if photo is False:
        gaps.append("商品与外包装照片")
    if weigh is False:
        gaps.append("物流称重记录")
    if chat_keep is False:
        gaps.append("拒退聊天记录")
    if page_shot is False:
        gaps.append("商品页面快照")
    A("证据缺口：%s" % ("、".join(gaps) if gaps else "已填项无缺口（未填的不算有）"))
    A("")
    A("平台介入怎么申请：")
    A("")
    A("1. 在订单页发起**退货退款**申请，写清理由并上传照片 / 视频、聊天截图；")
    A("2. 商家拒绝后，申请**平台介入**（订单详情页有入口），上传证据包并写清诉求；")
    A("3. 等平台判定；判定可退货的，按系统地址寄回并回填物流单号，**别寄到付**；")
    A("4. 对平台判定不满意的，可以走 12315 平台投诉 / 市场监管部门投诉，直至诉讼。")
    A("")
    A("商家拒绝理由原文：%s" % (refuse_text if refuse_text else "未填"))
    A("")

    A("## 九、待办补正动作与边界纪律")
    A("")
    if wr_state == "待补正" or q_state == "待补正":
        todo.append("补齐退货理由与签收日期，这是路径判定的前提")
    if any(v is None for _, v in exceptions):
        todo.append("补填商品类别相关的除外情形（定制 / 鲜活 / 数字化 / 报刊），未填不算通过")
    if sign_date is None:
        todo.append("补填签收日期（看物流签收记录或驿站取件通知），以便计算七天窗口")
    if marked is True and confirmed is not True:
        todo.append("把商家\"不支持七天无理由\"的页面截图留存，并在聊天中逼其说明"
                    "\"购买时是否单独确认过\"，留下书面回答")
    if overall in ("通过", "有风险") and not (applied_date or applied_yn is True):
        todo.append("当天在订单页提交退货退款申请，保留申请成功截图（以系统时间为准）")
    if gift_ok is False:
        todo.append("找回赠品与配件一并退回；找不回的先和商家谈折价，留存确认记录")
    if platform is not True and refused is True:
        todo.append("商家拒绝后立即申请平台介入，上传开箱视频 / 照片 / 称重记录 / 聊天截图")
    for g in gaps:
        todo.append("补证据缺口：%s" % g)
    if two_repair is not True and in_3pack is True and is_quality is True:
        todo.append("三包期内先申请修理 / 更换，留好维修工单；两次修理仍不能正常使用的，可要求退货")
    if overall == "不通过":
        todo.append("当前为难退情形，改走：质量问题举证 / 平台介入 / 12315 投诉三条线")
    todo.append("寄回前拍一组商品与包装照片、记重量，寄回后回填单号并盯退款到账（经营者收到后七日内）")
    todo.append("金额较大或商家态度强硬的，可先行咨询当地消费者协会或律师，不要单靠平台客服")
    for i, t in enumerate(todo, 1):
        A("%d. %s" % (i, t))
    A("")
    A("- 本结果依《消费者权益保护法》《民法典》合同编等**通用规则**整理，"
      "部分条款在司法实践中存在**两种口径**（如激活 / 拆封是否影响退货、"
      "耐用商品举证范围），脚本已如实标注，**不断言法院一定支持**；")
    A("- 不替代专业法律意见，最终以主管部门 / 平台 / 司法机关认定为准；")
    A("- 二手闲置、海外购、直播带货等特殊交易，还要叠加平台规则与跨境规则另行判断；")
    A("- **未填的一律不算通过**，补填后建议重跑一次。")
    A("")

    body = "\n".join(L)
    meta = {
        "version": VERSION,
        "商品": name or "未填",
        "结论": overall,
        "无理由路径": wr_state,
        "质量路径": q_state,
        "举证责任倒置": invert,
        "运费归属": payer,
        "待承担运费": rest,
        "风险项": risks,
        "待办": todo,
        "sections": body.count("## "),
    }
    return body, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    base = None
    if a.base:
        try:
            base = dt.date(*[int(x) for x in a.base.split("-")])
        except Exception:
            base = None

    body, meta = build_report(a.input, base)
    if body is None:
        hint = meta if isinstance(meta, str) else "未能生成报告"
        print(hint)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                f.write(hint)
        return 2

    txt = json.dumps(meta, ensure_ascii=False, indent=2) if a.json else body
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
        print("written %s" % a.out)
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
