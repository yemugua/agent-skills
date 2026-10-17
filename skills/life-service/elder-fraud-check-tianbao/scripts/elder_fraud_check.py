# -*- coding: utf-8 -*-
"""养老诈骗识别与止损追回核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段核查报告，含结论摘要、骗局类型识别、红线信号、止损窗口与时效、
      资金流水与账户核查、证据固定清单、案件定性与处置路径、待办补正动作、边界与纪律。

退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

# ---------------------------------------------------------------- 字段别名

FIELD_ALIAS = {
    "当事人年龄": ["当事人年龄", "老人年龄", "受害人年龄", "年龄"],
    "与当事人关系": ["与当事人关系", "填报人关系", "你的身份", "填报人身份"],
    "骗局类型": ["骗局类型", "诈骗类型", "遭遇的情形", "事情经过", "纠纷类型", "类型"],
    "接触渠道": ["接触渠道", "怎么接触的", "认识途径", "获客渠道", "来源渠道"],
    "对方身份自称": ["对方身份自称", "对方自称", "业务员身份", "对方身份"],
    "机构名称": ["机构名称", "公司全称", "对方公司", "涉事机构", "收款单位"],
    "是否有营业执照": ["是否有营业执照", "有无营业执照", "执照情况", "是否具备资质", "机构资质"],
    "是否签合同": ["是否签合同", "有无签订合同", "是否签约", "合同签订情况"],
    "合同名称": ["合同名称", "签署文件名称", "协议名称", "签了什么文件"],
    "首次接触日期": ["首次接触日期", "初次接触", "认识时间", "第一次接触"],
    "首次转账日期": ["首次转账日期", "第一次转账", "首笔转账日期", "初次付款日期"],
    "最近转账日期": ["最近转账日期", "最后一次转账", "末次转账日期", "最近一次付款"],
    "转账总金额": ["转账总金额", "已付总金额", "损失金额", "投入总额", "已支付金额", "涉及金额"],
    "转账笔数": ["转账笔数", "付款笔数", "交易笔数", "次数"],
    "收款账户类型": ["收款账户类型", "收款账户", "打款账户", "收款方式", "付款方式"],
    "收款户名": ["收款户名", "收款人姓名", "账户名", "收款方名称"],
    "资金去向": ["资金去向", "资金现状", "款项现状", "当前状态"],
    "已追回金额": ["已追回金额", "已退回金额", "已挽回损失", "追回金额"],
    "承诺收益率": ["承诺收益率", "承诺回报", "许诺收益", "收益率", "利息承诺"],
    "承诺话术摘录": ["承诺话术摘录", "对方话术", "宣传话术", "推销话术", "话术摘录"],
    "是否涉及房产抵押": ["是否涉及房产抵押", "是否抵押房产", "房产是否被抵押", "有无房产抵押"],
    "是否办理公证": ["是否办理公证", "有无公证", "公证情况", "是否做过公证"],
    "证据留存情况": ["证据留存情况", "证据情况", "有哪些证据", "留证情况", "已保存材料"],
    "是否已报警": ["是否已报警", "是否报案", "报警情况", "有无报案"],
    "报警日期": ["报警日期", "报案日期", "报案时间"],
    "是否已联系银行": ["是否已联系银行", "是否联系银行", "有无申请止付", "是否申请冻结"],
    "是否仍在联系对方": ["是否仍在联系对方", "是否还有联系", "是否继续接触", "现在还联系吗"],
    "是否被威胁": ["是否被威胁", "有无威胁恐吓", "是否受到威胁", "是否被恐吓"],
    "是否已告知家属": ["是否已告知家属", "家属是否知情", "是否告诉子女"],
    "诉求": ["诉求", "希望怎么解决", "期望结果", "想要什么结果"],
}

# ---------------------------------------------------------------- 基础工具

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)


def norm(s):
    """归一：去空格、全角转半角、小写。"""
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
    """未填判定，必须认得「待填/待补/待确认」这类占位词。"""
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


def parse_date(v):
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
    """读 Markdown 采集表，返回 {归一字段: 值}。"""
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
                continue  # 分隔行
            val = " ".join(c.strip() for c in cells[1:]).strip()
            if val:
                data[norm(key_raw)] = val
            continue

        # 冒号行必须同时认半角与全角；re.split(...,1) 只返 2 元组
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    """按字段名取别名值，精确匹配（绝不用子串 in）。"""
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


# ---------------------------------------------------------------- 判定


NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做")


def yesno(text):
    """「是否 X」类字段取值。空 → None；否/未/没有 → False；是/已 → True。"""
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


def classify_type(scene, channel, identity, promise, contract_name):
    """骗局类型识别：合并多字段全文，避免只看一个字段漏判。"""
    blob = norm(" ".join([scene, channel, identity, promise, contract_name]))
    table = [
        ("以房养老诈骗", ("以房养老", "房产抵押", "房屋抵押", "反向抵押", "房子抵押", "抵押房产", "养老公寓抵押")),
        ("高息理财/非法集资", ("高息", "理财", "保本保息", "年化", "返利", "分红", "投资养老项目", "养老投资", "高额回报", "利息")),
        ("保健品会销诈骗", ("保健品", "会销", "讲座", "送鸡蛋", "免费体检", "理疗仪", "保健食品", "养生", "包治百病")),
        ("冒充子女/熟人诈骗", ("冒充子女", "冒充熟人", "你儿子", "你女儿", "孙子", "出事了", "被抓", "急需用钱", "冒充亲友")),
        ("虚假养老服务", ("养老服务", "养老床位", "养老公寓", "预付养老", "会员卡养老", "旅居养老")),
        ("代办社保/补缴诈骗", ("代办社保", "补缴", "代办退休", "代办养老金", "特殊渠道退休", "一次性补缴")),
        ("收藏品回购诈骗", ("收藏品", "纪念币", "邮票", "字画", "回购", "高价回收")),
        ("冒充公检法诈骗", ("公检法", "公安局", "检察院", "法院", "涉嫌洗钱", "资金清查", "安全账户")),
    ]
    hits = []
    for name, kws in table:
        for k in kws:
            if k in blob:
                hits.append(name)
                break
    if not hits:
        return "未识别", ["采集信息不足以判定骗局类型，需补充事情经过与对方话术"]
    reasons = ["命中类型：%s" % "、".join(hits)]
    if len(hits) > 1:
        reasons.append("同时命中多类特征，常见于复合话术（先送鸡蛋再卖理财），报案时应一并说明")
    return hits[0], reasons


def check_redflags(f):
    """红线信号核查：返回 (危急红线列表, 一般红线列表)。"""
    scene = get_text(f, "骗局类型")
    promise = get_text(f, "承诺话术摘录")
    rate = get_text(f, "承诺收益率")
    acct = get_text(f, "收款账户类型")
    contract = get_text(f, "合同名称")
    identity = get_text(f, "对方身份自称")
    blob = norm(" ".join([scene, promise, rate, acct, contract, identity]))

    critical = []
    normal = []

    crit_kw = {
        "要求把钱转到个人账户": ("个人账户", "私人账户", "转到个人", "打给个人", "微信转个人", "转到业务员"),
        "以房产抵押或处置房产为前提": ("以房养老", "房产抵押", "房子抵押", "抵押房产", "卖房", "过户房产"),
        "冒充公检法要求资金清查": ("公检法", "安全账户", "资金清查", "涉嫌洗钱", "公安局", "检察院"),
        "要求删除聊天记录或保密": ("删除聊天", "删掉记录", "别告诉子女", "不要告诉家人", "保密", "不许告诉"),
        "要求现金交易或上门收钱": ("现金", "上门收", "取现", "现金支付"),
        "已被威胁恐吓": ("威胁", "恐吓", "不放过", "报复"),
    }
    for label, kws in crit_kw.items():
        for k in kws:
            if k in blob:
                critical.append(label)
                break

    if yesno(get_text(f, "是否被威胁")) is True:
        if "已被威胁恐吓" not in critical:
            critical.append("已被威胁恐吓")
    if yesno(get_text(f, "是否涉及房产抵押")) is True:
        if "以房产抵押或处置房产为前提" not in critical:
            critical.append("以房产抵押或处置房产为前提")
    if yesno(get_text(f, "是否办理公证")) is True:
        normal.append("已办理公证：需立即核对公证书内容与真实意思是否一致")

    rate_n = parse_num(rate)
    if rate_n is not None and rate_n >= 10:
        critical.append("承诺年化收益 %s%% 远超正常理财水平，属于典型非法集资话术" % fmt_num(rate_n))
    elif rate_n is not None and rate_n >= 6:
        normal.append("承诺年化收益 %s%% 偏高，需核验是否为持牌机构产品" % fmt_num(rate_n))

    nrm_kw = {
        "承诺保本保息": ("保本", "保息", "零风险", "稳赚", "不会亏", "兜底"),
        "以免费礼品或体检引流": ("送鸡蛋", "免费体检", "免费旅游", "送米面油", "听讲座送"),
        "宣称能治病或替代药物": ("包治", "治愈", "不用吃药", "替代药物", "根治"),
        "自称有特殊内部渠道": ("内部渠道", "有关系", "领导", "特殊名额", "内部名额", "限量"),
        "催促当场签约付款": ("今天最后一天", "名额有限", "当场签", "马上交", "限时"),
    }
    for label, kws in nrm_kw.items():
        for k in kws:
            if k in blob:
                normal.append(label)
                break

    return critical, normal


def check_window(f, base):
    """止损窗口：以首次转账日为起算点。返回 (等级, 说明列表)。"""
    first = parse_date(get_text(f, "首次转账日期"))
    last = parse_date(get_text(f, "最近转账日期"))
    items = []
    if first is None and last is None:
        items.append("未填写首次/最近转账日期，**止损窗口无法计算**，这是最需要立刻补齐的一项")
        return "待补正", items
    anchor = last or first
    d = days_between(anchor, base)
    if d is None:
        return "待补正", items
    items.append("以最近转账日 %s 起算，距基准日已 %s 天" % (anchor.isoformat(), fmt_num(d)))
    if d <= 3:
        level = "黄金止损期"
        items.append("**处于黄金止损窗口（一般 3 日内）**：立即拨打 96110 或到开户行申请止付/冻结，"
                     "同时拨打 110 报案并索取受案回执")
    elif d <= 30:
        level = "可止损期"
        items.append("仍可申请止付与冻结，但资金多已层层转出，重点是提交流水申请协查")
    else:
        level = "追损期"
        items.append("已超过 30 天，资金大概率已转移，重点是刑事立案后的追赃挽损与民事追偿并行")
    if first and last and first != last:
        span = days_between(first, last)
        if span is not None:
            items.append("首次至最近转账跨度 %s 天，属持续投入型，需逐笔列出时间与金额" % fmt_num(span))
    return level, items


def check_funds(f):
    """资金与账户核查：返回 (状态, 说明列表)。"""
    items = []
    paid = parse_num(get_text(f, "转账总金额"))
    back = parse_num(get_text(f, "已追回金额")) or 0.0
    acct = get_text(f, "收款账户类型")
    acct_name = get_text(f, "收款户名")
    org = get_text(f, "机构名称")
    cnt = parse_num(get_text(f, "转账笔数"))
    status = "有风险"

    if paid is None:
        items.append("未填写转账总金额，**净损失无法测算**，报案时需以银行流水为准")
        return "待补正", items

    net = paid - back
    if net < 0:
        items.append("已追回 %s 大于投入 %s，请核对是否把退款重复计入" % (money(back), money(paid)))
        net = paid
    items.append("投入 %s − 已追回 %s = 净损失 %s" % (money(paid), money(back), money(net)))

    if cnt is not None:
        items.append("共 %s 笔转账，逐笔打印流水是立案与追赃的基础材料" % fmt_num(cnt))
    else:
        items.append("未填写转账笔数，建议按流水逐笔编号，便于报案时列明")

    n_acct = norm(acct)
    if filled(acct):
        if any(k in n_acct for k in ("个人", "私人", "微信", "支付宝个人")):
            items.append("**收款为个人账户**：正规机构不得用个人账户收取投资款，这是非法集资与诈骗的强信号")
            status = "不通过"
        elif "现金" in n_acct:
            items.append("**现金交付**：无流水可查，追损难度最大，应立即固定取现凭证与交付现场证据")
            status = "不通过"
        elif any(k in n_acct for k in ("对公", "公司账户", "单位账户")):
            items.append("收款为对公账户，需核验账户名与合同主体是否一致")
        else:
            items.append("收款方式「%s」需进一步核实账户性质" % acct)
    else:
        items.append("未填写收款账户类型，账户性质直接决定追损路径")

    if filled(acct_name) and filled(org) and norm(acct_name) != norm(org):
        items.append("**收款户名「%s」与机构名称「%s」不一致**，属于典型的资金体外循环" %
                     (acct_name, org))
        status = "不通过"
    elif not filled(acct_name):
        items.append("未填写收款户名，无法核验账户与主体是否一致")

    if paid >= 50000:
        items.append("单案金额 %s 已达多数地区刑事立案关注的数额门槛，应坚持索取受案回执" % money(paid))
    return status, items


def check_evidence(f):
    """证据固定清单：返回 (已具备列表, 缺失列表)。"""
    ev = get_text(f, "证据留存情况")
    blob = norm(ev)
    need = [
        ("转账凭证与银行流水", ("流水", "转账凭证", "汇款", "回单", "支付记录", "银行")),
        ("聊天记录与通话录音", ("聊天", "录音", "微信记录", "通话")),
        ("宣传单/合同/收据原件", ("宣传单", "合同", "收据", "协议", "宣传册", "票据")),
        ("对方身份与联系方式", ("名片", "联系方式", "电话", "工号", "身份")),
        ("活动现场照片或视频", ("照片", "视频", "现场", "录像")),
    ]
    have = []
    miss = []
    if not filled(ev):
        return have, [n for n, _ in need]
    for name, kws in need:
        if any(k in blob for k in kws):
            have.append(name)
        else:
            miss.append(name)
    return have, miss


def decide_nature(f, types, critical):
    """案件定性：民事纠纷 / 非法集资 / 电信网络诈骗 / 待定。"""
    scene = get_text(f, "骗局类型")
    promise = get_text(f, "承诺话术摘录")
    blob = norm(" ".join([scene, promise, types]))
    if any(k in blob for k in ("冒充公检法", "冒充警察", "冒充公安局", "冒充子女", "冒充亲友",
                               "安全账户", "涉嫌洗钱", "电信")):
        return "电信网络诈骗", "应立即拨打 110 或 96110 报案，走刑事侦查程序"
    if any(k in blob for k in ("高息", "理财", "返利", "投资", "非法集资", "分红")):
        return "涉嫌非法集资/非法吸收公众存款", "向公安机关报案的同时，可向地方金融监管部门与市场监管部门反映"
    if any(k in blob for k in ("保健品", "会销", "理疗", "养生")):
        return "虚假宣传与消费欺诈", "可向 12315 投诉举报，涉刑部分另行报案"
    if critical:
        return "涉嫌诈骗", "存在高危红线信号，应立即报案，不要继续与对方周旋"
    return "待定", "信息不足，先按最坏情形做止损，补齐信息后再确定定性"


def check_path(f, nature, critical, window_level):
    """处置路径：返回动作列表（按顺序）。"""
    acts = []
    reported = yesno(get_text(f, "是否已报警"))
    bank = yesno(get_text(f, "是否已联系银行"))
    still = yesno(get_text(f, "是否仍在联系对方"))

    if critical:
        acts.append("① 立即停止一切转账，不再追加任何「保证金」「解冻费」「税费」")
    if reported is True:
        acts.append("② 已报案：保留受案回执与案件编号，7 日后可查询是否立案，不立案的索取《不予立案通知书》并申请复议")
    else:
        acts.append("② **尚未报案**：立即拨打 110（或 96110 反诈专线）报案，索取受案回执；"
                    "线上可同步通过国家反诈中心 App 举报")
    if bank is True:
        acts.append("③ 已联系银行：补充提交报案回执，申请延长止付并调取对方账户流水")
    else:
        acts.append("③ **尚未联系银行**：携带身份证到开户行或通过手机银行申请紧急止付/冻结，"
                    "并打印完整流水（含对方账号、户名、时间）")
    acts.append("④ 通知家属与社区：老年人单独处置极易二次受骗，告知子女并请社区民警或网格员协助留证")
    if still is True:
        acts.append("⑤ **仍在联系对方**：立即切断联系，对方常用「再投一笔就返本」话术诱导追加")
    if "以房养老" in nature or any("以房产抵押" in c for c in critical):
        acts.append("⑥ 房产已被抵押或过户的：立即到不动产登记中心查询登记状态，"
                    "申请异议登记并咨询律师提起撤销之诉，同时向公证机构申请复查公证书")
    if window_level == "黄金止损期":
        acts.append("⑦ 处于黄金止损期：以分钟计，先止付再报案，顺序不要颠倒")
    acts.append("⑧ 涉养老服务或机构无照经营的，同步向民政部门与市场监管部门反映")
    return acts


# ---------------------------------------------------------------- 报告


def build_report(f, base):
    rep = []
    risk = []
    todo = []

    age = get_text(f, "当事人年龄")
    rel = get_text(f, "与当事人关系")
    scene = get_text(f, "骗局类型")
    channel = get_text(f, "接触渠道")
    identity = get_text(f, "对方身份自称")
    org = get_text(f, "机构名称")
    lic = get_text(f, "是否有营业执照")
    signed = get_text(f, "是否签合同")
    cname = get_text(f, "合同名称")
    promise = get_text(f, "承诺话术摘录")
    rate = get_text(f, "承诺收益率")
    paid = get_text(f, "转账总金额")
    paid_n = parse_num(paid)
    acct = get_text(f, "收款账户类型")
    acct_name = get_text(f, "收款户名")
    demand = get_text(f, "诉求")
    ev = get_text(f, "证据留存情况")

    types, type_reasons = classify_type(scene, channel, identity, promise, cname)
    critical, normal = check_redflags(f)
    window_level, window_items = check_window(f, base)
    fund_status, fund_items = check_funds(f)
    have_ev, miss_ev = check_evidence(f)
    nature, nature_advice = decide_nature(f, types, critical)
    acts = check_path(f, nature, critical, window_level)

    # --- 风险汇总（核心事实缺失时不得下任何风险结论）
    core_missing = not filled(scene) and paid_n is None
    if not core_missing:
        for c in critical:
            risk.append("高危红线：%s" % c)
        for n in normal:
            risk.append("可疑信号：%s" % n)
        if fund_status == "不通过":
            risk.append("资金流向异常：见资金流水与账户核查")
        if yesno(lic) is False:
            risk.append("对方无营业执照，机构主体真实性存疑")
        if yesno(signed) is False and paid_n:
            risk.append("已付款但未签任何书面合同，权利义务无载体，追损难度显著上升")
        if miss_ev:
            risk.append("证据缺失 %d 项：%s" % (len(miss_ev), "、".join(miss_ev[:3])))
        if window_level == "追损期":
            risk.append("已过黄金止损期，资金追回概率下降")

    if core_missing:
        verdict = "待补正"
    elif paid_n is not None and paid_n <= 0:
        verdict = "通过"
    elif critical:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "有风险"

    # --- 1 结论摘要
    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 当事人：%s 岁（%s）" % (parse_num(age) is not None and fmt_num(parse_num(age)) or "未填写",
                                   filled(rel) and rel or "关系未填写"))
    rep.append("- 接触渠道：%s" % (channel if filled(channel) else "未填写"))
    rep.append("- 对方自称：%s" % (identity if filled(identity) else "未填写"))
    rep.append("- 涉事机构：%s" % (org if filled(org) else "未填写"))
    rep.append("- **识别类型：%s**" % types)
    rep.append("- **案件定性：%s**" % nature)
    rep.append("- 止损窗口：%s" % window_level)
    rep.append("- 资金核查：%s" % fund_status)
    rep.append("- 高危红线 %d 项 / 可疑信号 %d 项" % (len(critical), len(normal)))
    rep.append("- **总体结论：%s**" % verdict)
    rep.append("")

    # --- 2 骗局类型识别
    rep.append("## 骗局类型识别")
    rep.append("")
    for r in type_reasons:
        rep.append("- %s" % r)
    rep.append("- 接触渠道：%s" % (channel if filled(channel) else "未填写"))
    rep.append("- 对方身份自称：%s" % (identity if filled(identity) else "未填写"))
    rep.append("- 机构名称：%s；营业执照：%s" % (org if filled(org) else "未填写",
                                    lic if filled(lic) else "未填写"))
    rep.append("- 是否签合同：%s；合同名称：%s" % (signed if filled(signed) else "未填写",
                                     cname if filled(cname) else "未填写"))
    rep.append("")

    # --- 3 红线信号
    rep.append("## 红线信号核查")
    rep.append("")
    if critical:
        rep.append("### 高危（立即停止接触并报警）")
        for c in critical:
            rep.append("- **%s**" % c)
    else:
        rep.append("- 未识别到高危红线信号%s" % ("（信息不足，不等于安全）" if core_missing else ""))
    rep.append("")
    if normal:
        rep.append("### 可疑（需进一步核验）")
        for n in normal:
            rep.append("- %s" % n)
    else:
        rep.append("- 未识别到可疑话术信号")
    rep.append("")
    if filled(promise):
        rep.append("- 话术摘录：%s" % str(promise)[:120])
    rep.append("")

    # --- 4 止损窗口
    rep.append("## 止损窗口与时效")
    rep.append("")
    for it in window_items:
        rep.append("- %s" % it)
    rep.append("- 已报警：%s；已联系银行：%s" % (get_text(f, "是否已报警") or "未填写",
                                     get_text(f, "是否已联系银行") or "未填写"))
    rep.append("")

    # --- 5 资金流水与账户
    rep.append("## 资金流水与账户核查")
    rep.append("")
    for it in fund_items:
        rep.append("- %s" % it)
    rep.append("- 收款账户类型：%s；收款户名：%s" % (acct if filled(acct) else "未填写",
                                       acct_name if filled(acct_name) else "未填写"))
    rep.append("- 资金去向：%s" % (get_text(f, "资金去向") or "未填写"))
    rep.append("")

    # --- 6 证据
    rep.append("## 证据固定清单")
    rep.append("")
    if have_ev:
        rep.append("已具备：")
        for h in have_ev:
            rep.append("- %s" % h)
    else:
        rep.append("- 采集表未填写任何已留存证据")
    rep.append("")
    if miss_ev:
        rep.append("仍缺失（按重要性排序）：")
        for m in miss_ev:
            rep.append("- **%s**" % m)
    else:
        rep.append("- 主要证据类别已覆盖，仍需确认原始载体（手机、银行 App）未被清理")
    rep.append("")
    rep.append("固定要点：转账流水需银行盖章或 App 导出的完整版；聊天记录要连上下文导出，"
               "不要只截单张图；通话录音保留原始文件。")
    rep.append("")

    # --- 7 定性与处置路径
    rep.append("## 案件定性与处置路径")
    rep.append("")
    rep.append("- 定性：%s" % nature)
    rep.append("- 处置建议：%s" % nature_advice)
    rep.append("")
    CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
    acts_clean = [re.sub(r"^[①-⑩]\s*", "", a) for a in acts]
    for i, a in enumerate(acts_clean, 1):
        rep.append("%s %s" % (CIRCLED[i - 1] if i <= len(CIRCLED) else "%d." % i, a))
    rep.append("")
    rep.append("投诉举报入口：110 / 96110 反诈专线、国家反诈中心 App、12315 平台、"
               "当地民政部门（涉养老机构）、地方金融监管部门（涉非法集资）。")
    rep.append("")

    # --- 8 待办补正动作
    rep.append("## 待办补正动作")
    rep.append("")
    all_todo = []
    if core_missing:
        all_todo.append("补齐「骗局类型/事情经过」与「转账总金额」——这是出具任何结论的前提")
    if not filled(get_text(f, "首次转账日期")) and not filled(get_text(f, "最近转账日期")):
        all_todo.append("补齐首次与最近转账日期，用于计算止损窗口")
    if not filled(acct):
        all_todo.append("核实收款账户性质（对公/个人/现金）与收款户名")
    if not filled(org):
        all_todo.append("通过国家企业信用信息公示系统查询对方机构是否登记、是否异常经营")
    for m in miss_ev:
        all_todo.append("补齐证据：%s" % m)
    if yesno(get_text(f, "是否已报警")) is not True and (paid_n or 0) > 0:
        all_todo.append("尚未报案：立即报案并索取受案回执")
    if yesno(get_text(f, "是否仍在联系对方")) is True:
        all_todo.append("切断与对方的联系，不再追加任何款项")
    if not filled(demand):
        all_todo.append("明确诉求：止损止付 / 全额追回 / 撤销合同 / 报案立案")
    if not all_todo:
        all_todo.append("信息已较完整，按处置路径顺序立即执行，并保留每一步的回执")
    for i, t in enumerate(all_todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # --- 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见，最终以公安机关及司法机关认定为准。")
    rep.append("- 「止损窗口」「净损失」均为依填写信息推算的**参考值**，不是法律结论。")
    rep.append("- 涉刑案件应立即报警，不要依赖本技能自行与对方交涉或自行追讨。")
    rep.append("- 本技能不提供任何代办报案、代办追损或代写诉状服务。")

    return "\n".join(rep), verdict, risk, all_todo


# ---------------------------------------------------------------- CLI


def main():
    ap = argparse.ArgumentParser(description="养老诈骗识别与止损追回核查")
    ap.add_argument("md", nargs="?", default="样例.md", help="采集表 Markdown 路径")
    ap.add_argument("--input", dest="input", default=None, help="采集表路径（等价位置参数）")
    ap.add_argument("--base", default=None, help="基准日期 YYYY-MM-DD")
    ap.add_argument("--out", default="", help="报告输出路径")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    args = ap.parse_args()

    path = args.input or args.md
    base = parse_date(args.base) if args.base else date.today()

    if not path or not os.path.exists(path):
        msg = "采集表不存在：%s" % path
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2

    f = parse_md(path)
    if not f:
        msg = "采集表为空或格式无法解析，请用「| 字段 | 值 |」或「字段：值」格式填写"
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2

    report, verdict, risk, todo = build_report(f, base)

    if args.json:
        print(json.dumps({"结论": verdict, "风险项": risk, "待办": todo, "报告": report},
                         ensure_ascii=False, indent=2))
    else:
        print(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)

    if not filled(get_text(f, "骗局类型")) or parse_num(get_text(f, "转账总金额")) is None:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
