#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学历提升（专升本/成人高考/自考/网络教育）报考与退费核查。

用法：
  python edu_upgrade_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python edu_upgrade_check.py 采集表.md --json
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

# 提升途径类型
ROUTE_TYPES = [
    ("普通专升本", ["普通专升本", "专接本", "统招专升本", "普通类专升本", "全日制专升本"]),
    ("成人高考专升本", ["成人高考", "成考", "成人高招", "成教"]),
    ("自学考试", ["自考", "自学考试", "自考本科"]),
    ("网络教育/远程教育", ["网络教育", "远程教育", "网教", "现代远程教育"]),
    ("国家开放大学", ["开放大学", "国开", "广播电视大学", "电大", "开放教育"]),
    ("非全日制/函授", ["函授", "非全日制"]),
    ("中外合作办学", ["中外合作", "合作办学", "留学预备", "国际课程"]),
    ("职业资格/技能证书", ["职业资格", "技能证书", "考证", "执业资格", "职称"]),
]

# 中介常见套路特征
FRAUD_PATTERNS = [
    ("承诺包过/保录取", ["包过", "保过", "包录取", "保证录取", "不过退款", "保过班",
                    "百分百", "100%", "稳过", "内部名额"]),
    ("伪造学历/证书", ["代办毕业证", "假证", "买证", "办证", "代做作业", "替考",
                  "买学历", "代写", "代考", "代替考试", "找人考试", "挂名", "代考费"]),
    ("假借学历名义招生", ["借考", "替考", "组织考试作弊", "空挂", "挂靠学籍",
                    "学籍挂靠", "买卖学籍"]),
    ("夸大证书效力/用途", ["国家承认", "包分配", "包就业", "高薪就业", "免考",
                    "直接拿证", "不用考试", "速成", "快速拿证"]),
    ("诱导贷款/分期", ["贷款", "分期", "助学贷款", "分期付款", "花呗", "借钱",
                  "刷信用卡"]),
    ("不退费/拖延退款", ["不退", "不退费", "拖", "过两个月", "等下学期", "再等等",
                   "不能退"]),
    ("冒用办学资质", ["野鸡", "无资质", "个人账户收款", "私人账户", "个人微信",
                  "加盟", "代理"]),
    ("贬低正规途径", ["正规没用", "自己考太难", "考不过", "成人高考没用",
                  "自考没用", "含金量低"]),
]

# 正规途径应有的要素
LEGAL_ELEMENTS = [
    ("具有办学资质", ["资质", "许可证", "备案", "学校", "院校", "主办", "公办",
                "民办", "教育部", "省教育厅"]),
    ("学信网可查", ["学信网", "可查", "查询", "学籍", "学历查询"]),
    ("招生与考试由官方组织", ["考试院", "招生考试", "统考", "官方", "命题", "省考试院",
                     "招生办"]),
    ("有正式录取与学籍", ["录取", "学籍", "注册学籍", "报到", "注册"]),
    ("有书面合同与发票", ["合同", "协议", "发票", "收据", "票据", "签字", "盖章"]),
    ("退费规则写清", ["退费", "退款", "退费规则", "课时费", "退费条件", "手续费"]),
]

# 时效性风险
TIMING_RISKS = [
    ("错过当年报名期", ["错过", "过了报名", "截止", "错过时间", "报不上", "没名额"]),
    ("承诺与考试时间冲突", ["一年拿证", "半年拿证", "三个月拿证", "快速拿证",
                     "当年拿证", "保当年"]),
    ("学籍注册时间紧张", ["学籍", "注册", "报到时间", "错过注册"]),
    ("毕业时间承诺过长", ["多久毕业", "几年毕业", "什么时候拿证", "拿证时间"]),
]

# 维权路径
PATHS = [
    ("第 1 步（先查办学资质）",
     "**在报名之前就应该做的事**：把机构与学校名称拿去查——"
     "**教育部全国高等学校名单**、**省教育厅学历教育名单**、"
     "**学信网**。**查不到的办学单位，基本可以排除**。"),
    ("第 2 步（查是不是正规途径）",
     "**自考、成考、国开、开放大学**都是国家承认的学历，**考试由教育考试院命题组织**。"
     "正规机构的收费路径是：**学校收学费 + 机构收服务费**，而不是"
     "「全部打包交给机构」——**打包费里往往含着无法退的部分**。"),
    ("第 3 步（把所有承诺变成文字）",
     "「包过」「保录取」「不用考试」**一律写进合同或补充协议**，"
     "并写明**未兑现的退费金额与退费时间**。**口头承诺一律无效**。"),
    ("第 4 步（缴费前算清总价）",
     "**把所有费用一次性列出来**：学费、教材费、试卷费、服务费、"
     "代缴费、住宿费。**问清哪些不可退**，尤其是「已报班后不退」这类条款。"),
    ("第 5 步（谨慎对待贷款与分期）",
     "**任何要求你贷款/分期的，一律拒绝或慎之又慎**。"
     "贷款的还款责任在你，中介跑了你照样还贷——**这是最容易被套路的一步**。"),
    ("第 6 步（保留全部证据）",
     "**合同、收据、转账记录、聊天记录、课程视频、承诺截图**，"
     "按时间顺序编号保存。**宣传话术截图也要存**——「包过」这种承诺常出现在朋友圈和短视频里。"),
    ("第 7 步（退费与投诉）",
     "**先书面提出退费要求**（明确金额与时限）→ 协商不成向"
     "**12315** 与当地**教育局/文化和旅游部门**投诉（培训类）→"
     "涉及诈骗、伪造证件、替考作弊的**向公安机关报案** → 仍不成的**走民事诉讼或仲裁**。"),
]

# 证据类别
EVIDENCE = [
    ("机构与院校资质", ["资质", "许可证", "备案", "学校", "院校", "名单", "公办", "民办"]),
    ("合同与协议", ["合同", "协议", "补充协议", "承诺", "保证", "条款"]),
    ("缴费凭证", ["收据", "发票", "转账", "缴费", "支付", "账单", "收据"]),
    ("机构宣传材料", ["海报", "宣传", "朋友圈", "视频", "截图", "广告", "直播"]),
    ("学习与考试记录", ["课程", "网课", "教材", "作业", "考试", "成绩", "签到"]),
    ("沟通记录", ["微信", "聊天", "短信", "通话", "录音", "工单", "客服"]),
    ("官方查询记录", ["学信网", "查询记录", "名单", "公示", "官网", "教育部"]),
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
    if n in ("有", "是", "已经", "已", "已完成", "已做", "可以", "能", "已签", "已查"):
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


# ------------------------------------------------------------------ 一 途径定性
def classify(f):
    txt = (f["route"] or "") + "|" + (f["org"] or "")
    if not filled(txt):
        return []
    return [lbl for lbl, ws in ROUTE_TYPES if hit_any(txt, ws) is True]


def checks_route(f):
    out = []
    kinds = classify(f)
    if unknown(f["route"]) and unknown(f["org"]):
        out.append(("提升途径类型", "待补正",
                    "打算通过什么途径提升、找的是哪家机构未填。"
                    "**途径决定正规性**：自考、成考、国开、开放大学是"
                    "国家承认且考试由教育考试院组织的；"
                    "而「包过」「不用考试」的路子几乎都是骗局。"))
    elif not kinds:
        out.append(("提升途径类型", "待补正",
                    "没识别出提升途径。请按这些词填："
                    "普通专升本/专接本/全日制、成人高考/成考、"
                    "自考、网络教育/网教、开放大学/电大/国开、"
                    "函授、中外合作、职业资格考证。"))
    else:
        out.append(("提升途径类型", "有风险",
                    "本次属于：**%s**。"
                    "**先确认这条路本身是正规的**（考试由教育考试院组织、"
                    "证书学信网可查），再谈机构靠不靠谱。" % "、".join(kinds)))
    return out


def checks_qualify(f, today):
    out = []
    age = f["age"]
    school = f["school_level"]
    if unknown(age) and unknown(school):
        out.append(("本人报考条件", "待补正",
                    "年龄、现有学历、专业未填。"
                    "**自考、成考、专升本的报考条件各不相同**："
                    "成考专升本一般要求专科毕业且满规定年限，"
                    "自考部分专业无前置学历要求。**条件不够时，"
                    "中介常会说「我们可以操作」——这就是危险信号。**"))
    else:
        out.append(("本人报考条件", "通过",
                    "现有学历：%s。**请自行对照官方报考条件核对**，"
                    "不要以机构口头说「你符合」为准。" % (school or "未填")))
    d = f["sign_up_date"]
    dt = parse_date(d)
    if unknown(d):
        out.append(("报名时间点", "待补正",
                    "什么时候报的名、准备考什么时候的未填。"
                    "**成考与自考都有固定报名窗口，错过了就要等下一轮**，"
                    "「帮你赶上今年」往往是套路。"))
    else:
        out.append(("报名时间点", "通过",
                    "报名时间：%s（距核查日 %d 天）。" % (d, (today - dt).days)))
    return out


# ------------------------------------------------------------------ 二 中介套路
def checks_fraud(f):
    out = []
    heard = f["promises"]
    if unknown(heard):
        out.append(("机构做过哪些承诺", "待补正",
                    "机构说了什么、保什么、承诺什么未填。"
                    "**把「包过」「保录取」「不用考试」「国家承认」"
                    "这些话原样记下来**——这是后面退费与投诉的核心证据。"))
        return out
    hits = [lbl for lbl, ws in FRAUD_PATTERNS if hit_any(heard, ws) is True]
    if not hits:
        out.append(("机构做过哪些承诺", "有风险",
                    "暂未识别到明显的套路话术，**但仍要逐条核实**——"
                    "**口头承诺一律无效**，尤其要问清：谁出题、谁录取、"
                    "谁发证、谁注册学籍。"))
    else:
        out.append(("机构做过哪些承诺", "不通过",
                    "机构涉及以下高风险表述：**%s**。"
                    "这几条任意一条都足以要求你**立即停止缴费并核查资质**。"
                    "尤其注意：**「包过」几乎可以确定是骗局**——"
                    "考试由教育考试院命题组织，机构无法左右；"
                    "**「不用考试」同样不可能**。" % "、".join(hits)))
    return out


def checks_qualification(f):
    out = []
    q = f["qualification"]
    if unknown(q):
        out.append(("办学资质是否核实", "待补正",
                    "机构有没有办学资质、学校是不是正规的未核实。"
                    "**这是唯一不能省的一步**：把机构与学校名称拿到"
                    "**教育部全国高等学校名单**与**省教育厅学历教育名单**查，"
                    "再在学信网核对。**查不到就直接排除。**"))
    else:
        have = [lbl for lbl, ws in LEGAL_ELEMENTS if hit_any(q, ws) is True]
        if have:
            out.append(("办学资质是否核实", "通过",
                        "已核实要素：%s。**保留查询截图**，"
                        "申请与投诉时都要用到。" % "、".join(have)))
        else:
            out.append(("办学资质是否核实", "待补正",
                        "填的是「%s」，没识别出核实过的要素。"
                        "请用这些词补充：资质/许可证/备案、学校/院校/公办、"
                        "学信网可查、招生考试院、录取学籍、合同发票、退费规则。" % q))
    org = f["org"]
    if hit_any(org, ["个人", "私人", "个人账户", "个人微信", "工作室", "代理点",
                   "加盟"]) is True:
        out.append(("收款主体是否合规", "不通过",
                    "收款方是**%s**。**正规院校的学费由学校收取，"
                    "服务费也应有机构对公账户**；"
                    "把钱打到个人账户，一旦出问题**极难追回**。" % org))
    elif unknown(org):
        out.append(("收款主体是否合规", "待补正",
                    "机构名称与收款账户未填。"
                    "**要求提供对公账户与发票**，不要打到个人账户。"))
    else:
        out.append(("收款主体是否合规", "有风险",
                    "机构为 **%s**。**确认收款账户是否与机构名称一致**，"
                    "并要求开具发票。机构名称与收款方不一致是常见的转移责任手段。"
                    % org))
    return out


def checks_loan(f):
    out = []
    loan = f["loan"]
    if unknown(loan):
        out.append(("是否涉及贷款或分期", "待补正",
                    "机构有没有让你贷款、分期、借钱未填。"
                    "**这一步风险最高**：贷款一旦签，"
                    "还款责任就在你身上，**机构跑了你照样还贷**。"))
    elif yes(loan):
        out.append(("是否涉及贷款或分期", "不通过",
                    "**机构让你贷款或分期**。这是最需要警惕的信号："
                    "**贷款的责任不能转移**，机构失联后你仍需偿还，"
                    "可能同时背上债务与征信污点。**强烈建议拒绝，改为分期付学费**"
                    "（直接付给学校或机构对公账户，不要借高息消费贷）。"))
    else:
        out.append(("是否涉及贷款或分期", "通过", "未涉及贷款与分期。"))
    pay = f["paid"]
    if unknown(pay):
        out.append(("已缴纳费用", "待补正",
                    "已经交了多少钱、什么时候交的未填。"
                    "**金额与凭证是退费主张的基础**，"
                    "以收据、转账记录、发票为准。"))
    elif yes(pay):
        out.append(("已缴纳费用", "有风险",
                    "已缴费。**核对金额是否与合同一致**，"
                    "多收的部分同样可以主张退还；"
                    "**保留每一笔凭证**。"))
    else:
        out.append(("已缴纳费用", "通过", "尚未缴费。**在核实资质前不要交钱**。"))
    return out


# ------------------------------------------------------------------ 三 合同与退费
def checks_contract(f):
    out = []
    c = f["contract"]
    if unknown(c):
        out.append(("是否签了书面合同", "待补正",
                    "有没有签合同、签的是机构还是学校未填。"
                    "**不签合同就交钱，等于放弃所有维权基础**。"
                    "**至少要签书面协议，把承诺与退费规则写进去**。"))
    else:
        have = [lbl for lbl, ws in LEGAL_ELEMENTS if hit_any(c, ws) is True]
        if have:
            out.append(("是否签了书面合同", "有风险",
                        "合同要素含：%s。**继续检查两点**："
                        "① 承诺有没有写进去（包过、保录取这类口头话没写就不算）；"
                        "② 退费规则是否具体（退多少、多久退、扣哪些）。" % "、".join(have)))
        else:
            out.append(("是否签了书面合同", "待补正",
                        "填的是「%s」，无法判断合同是否规范。"
                        "请用这些词补充：合同/协议/承诺/条款/退费/发票。" % c))
    rf = f.get("refund_rule", "")
    if unknown(rf):
        out.append(("退费规则是否写清", "待补正",
                    "退多少、多久退、扣哪些未填。"
                    "**很多合同写「已报班后不退费」**——"
                    "这是最伤的位置，一定要谈："
                    "把「已发生的教材费/已上课时费」与「未发生部分」分开，"
                    "**未发生部分必须可退**。"))
    elif hit_any(rf, ["不退", "不退费", "不能退", "概不退款", "一经报名"]) is True:
        out.append(("退费规则是否写清", "不通过",
                    "退费规则是「**%s**」。"
                    "**这是最常见的坑**。要求重谈："
                    "把费用拆成「已实际发生」与「未发生」两部分，"
                    "**未发生部分全额可退**，并写明退费时限与方式。"))
    else:
        out.append(("退费规则是否写清", "有风险",
                    "退费规则：**%s**。**逐条看清楚有没有「霸王条款」**——"
                    "不合理免除自身责任、加重对方责任的条款可能无效，"
                    "但**主张无效需要时间，先在签约前谈清楚最省事**。" % rf))
    return out


def checks_timing(f):
    out = []
    t = f["timing_promise"]
    if unknown(t):
        out.append(("拿证时间承诺", "待补正",
                    "承诺什么时候拿证、有没有说「很快」未填。"
                    "**时间承诺是时限风险的来源**："
                    "「一年拿证」往往对应着缩短考程甚至买证。"))
    else:
        hits = [lbl for lbl, ws in TIMING_RISKS if hit_any(t, ws) is True]
        if hits:
            out.append(("拿证时间承诺", "有风险",
                        "时间承诺：**%s**，涉及 %s。"
                        "**核对一下是否与官方学制、考试安排吻合**——"
                        "自考专科一般 2.5~3 年，本科 3~4 年；"
                        "成考专升本一般 2.5~3 年。**明显短于学制的承诺不可信。**"
                        % (t, "、".join(hits))))
        else:
            out.append(("拿证时间承诺", "通过", "拿证时间承诺：**%s**，未见明显时限冲突。" % t))
    return out


# ------------------------------------------------------------------ 四 证据
def has_content(s):
    for part in str(s or "").split("|"):
        if filled(part):
            return True
    return False


def checks_evidence(f):
    out = []
    a = f["evidence_owned"]
    b = f["evidence_desc"]
    if not has_content(a) and not has_content(b):
        out.append(("证据总览", "待补正",
                    "已有证据既没勾选也没写清单。"
                    "**这一类纠纷的胜负全在留痕**："
                    "合同、收据、转账记录、承诺截图、官方查询截图，"
                    "缺一样都可能维权无门。"))
        return out
    for label, keys in EVIDENCE:
        hit = [k for k in keys if k in a or k in b]
        if hit:
            out.append((label, "通过",
                        "已具备：%s。**原件留存、复印件提交**。" % "、".join(hit)))
        else:
            out.append((label, "有风险", "尚无%s材料，这类缺口会让主张难以成立。" % label))
    return out


EVID_FIX = {
    "机构与院校资质": "把机构与学校名称在教育部名单、省教育厅名单查一次并截图",
    "合同与协议": "补签书面协议，把承诺与退费规则写进去，双方签字",
    "缴费凭证": "保存收据、发票、每一笔转账记录与账单",
    "机构宣传材料": "保存含「包过」「保录取」话术的海报、朋友圈、视频、广告截图",
    "学习与考试记录": "保存课程视频、签到、作业、考试成绩记录",
    "沟通记录": "保存微信、短信、通话录音、工单号",
    "官方查询记录": "保存学信网与教育部名单的查询截图，带日期",
}


def evidence_gap(f):
    a = f["evidence_owned"] or ""
    b = f["evidence_desc"] or ""
    got = a + "|" + b
    gaps = []
    if has_content(got):
        for label, keys in EVIDENCE:
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in EVIDENCE]
    if not any(k in got for k in ["资质", "许可证", "名单", "学校", "备案"]):
        gaps.append("机构与院校资质")
    if hit_any(f["promises"], ["包过", "保过", "保录取", "不用考试"]) is True and \
            not any(k in got for k in ["宣传", "海报", "截图", "视频", "微信", "聊天"]):
        gaps.append("机构宣传材料")
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
    if unknown(f["qualification"]):
        extra.append(("查机构与学校办学资质", "教育部名单 + 省教育厅名单 + 学信网，截图留存"))
    if hit_any(f["promises"], ["包过", "保过", "保录取", "不用考试"]) is True:
        extra.append(("立即停止缴费并核查资质", "「包过」「不用考试」几乎确定是骗局"))
    if yes(f["loan"]):
        extra.append(("拒绝贷款或分期", "贷款责任无法转移，机构跑了你照样还"))
    if hit_any(f["refund_rule"], ["不退", "不能退", "概不退"]) is True:
        extra.append(("重谈退费条款", "把已发生与未发生费用拆开，未发生部分可退"))
    if not filled(f["contract"]):
        extra.append(("补签书面协议", "把承诺与退费规则写进去，双方签字"))
    if not has_content((f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")):
        extra.append(("列证据清单并编号成册", "合同、凭证、承诺截图、官方查询截图"))
    if not filled(f["promises"]):
        extra.append(("记录机构承诺原话", "包过、保录取这类话是退费与投诉的核心证据"))
    seen = set()
    res = []
    for n, s in todos + extra:
        if n not in seen:
            seen.add(n)
            res.append((n, s))
    return res


# ------------------------------------------------------------------ 报告
SECTIONS = [
    "二、提升途径与报考条件",
    "三、中介承诺与套路核查",
    "四、办学资质与缴费核查",
    "五、合同条款与退费规则",
    "六、时间承诺与时效风险",
    "七、证据清单与缺口",
]


def render(f, results, steps, todos, today, gaps):
    L = []
    L.append("# 学历提升报考与退费核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 提升途径：%s" % (f["route"] or "未填"))
    L.append("- 咨询机构：%s" % (f["org"] or "未填"))
    L.append("- 已缴费用：%s" % (f["paid_amount"] or "未填"))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在明确的高风险信号（套路承诺 / 无资质收款 / 贷款分期 /"
                 "不可退条款），应立即停止缴费并核查资质。**")
    elif risk:
        L.append("**判定：未发现明显套路话术，但资质、退费条款与承诺书面化仍有缺口，"
                 "建议补齐后再缴费。**")
    else:
        L.append("**判定：采集表关键项未填，暂时给不出确定结论；**"
                 "请把提升途径、机构名称、机构承诺与缴费情况填完再重跑。"
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

    L.append("## 八、路径选择与维权流程")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 九、查询渠道速查")
    L.append("")
    L.append("| 用途 | 渠道 |")
    L.append("|---|---|")
    L.append("| 查学校是否正规 | 教育部全国高等学校名单、省教育厅学历教育名单 |")
    L.append("| 查学历是否可查 | 学信网（中国高等教育学生信息网） |")
    L.append("| 查考试与报名 | 省级教育考试院官网 |")
    L.append("| 投诉培训机构 | 12315、当地教育局或文化和旅游部门 |")
    L.append("| 涉诈骗伪造 | 公安机关 |")
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
             "报考条件、学制、学费标准与退费规则，"
             "**以教育部、省级教育考试院与院校官方口径为准**。")
    L.append("- 不预测能否通过考试，也不预测投诉或诉讼结果。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 涉及身份证号、学历证书号、账号等敏感信息，"
             "**本地处理，不要外发**。")
    L.append("- 本结果依通用规则整理，不替代专业意见，"
             "最终以主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps):
    return {
        "核查日期": today.isoformat(),
        "提升途径": classify(f),
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "已缴费用": parse_num(f["paid_amount"]),
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "route": get_text(kv, ["提升途径", "打算怎么提升", "报考方式"]),
        "org": get_text(kv, ["咨询机构", "机构名称", "找的哪家"]),
        "school": get_text(kv, ["报考院校", "学校", "院校"]),
        "age": get_text(kv, ["年龄", "今年多大"]),
        "school_level": get_text(kv, ["现有学历", "目前学历", "最高学历"]),
        "major": get_text(kv, ["报考专业", "专业"]),
        "sign_up_date": get_text(kv, ["报名时间", "报名日期", "什么时候报的"]),
        "promises": get_text(kv, ["机构做过的承诺", "机构承诺", "机构怎么说"]),
        "qualification": get_text(kv, ["资质核实情况", "是否查过资质", "学校是否正规"]),
        "loan": get_text(kv, ["是否让你贷款或分期", "是否涉及贷款", "是否让你分期"]),
        "paid": get_text(kv, ["是否已经缴费", "是否已缴费", "交钱了吗"]),
        "paid_amount": get_text(kv, ["已缴费用", "已交金额", "一共交了多少钱"]),
        "contract": get_text(kv, ["是否签了书面合同", "合同情况", "协议签了吗"]),
        "refund_rule": get_text(kv, ["退费规则", "退款规则", "怎么退"]),
        "timing_promise": get_text(kv, ["拿证时间承诺", "承诺多久拿证", "什么时候拿证"]),
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
    if not filled(f["route"]):
        missing.append("提升途径")
    if not filled(f["org"]):
        missing.append("咨询机构")
    if not filled(f["promises"]):
        missing.append("机构做过的承诺")

    results = [
        ("提升途径与报考条件", checks_route(f) + checks_qualify(f, today)),
        ("中介承诺与套路核查", checks_fraud(f)),
        ("办学资质与缴费核查", checks_qualification(f) + checks_loan(f)),
        ("合同条款与退费规则", checks_contract(f)),
        ("时间承诺与时效风险", checks_timing(f)),
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
