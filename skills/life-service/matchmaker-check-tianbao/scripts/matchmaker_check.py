#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""婚介服务合同与退费核查。

用法：
  python matchmaker_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python matchmaker_check.py 采集表.md --json
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

# 婚介服务类型
SERVICE_TYPES = [
    ("线下门店婚介", ["门店", "线下", "实体店", "门店婚介", "到店"]),
    ("线上婚恋平台", ["线上", "网络", "APP", "平台", "网站", "在线"]),
    ("红娘牵线", ["红娘", "牵线", "撮合", "介绍"]),
    ("相亲角活动", ["相亲角", "活动", "专场", "联谊"]),
    ("定制一对一服务", ["定制", "一对一", "专属", "高端", "定制服务", "管家"]),
    ("综合服务包", ["套餐", "服务包", "综合", "全套", "钻石"]),
]

# 婚介常见套路
FRAUD_PATTERNS = [
    ("承诺成功/包结婚", ["包结婚", "包成功", "保证成功", "一定能结", "不结婚退",
                    "包脱单", "保证脱单", "一年内结婚"]),
    ("虚假资源与成功率", ["资源多", "优质资源", "成功率", "九成", "高成功率", "名额有限",
                    "内部名额", "优质单身", "成功案例上千"]),
    ("诱导签约与分期", ["先签", "先交", "分期", "贷款", "限时优惠", "今天下单",
                  "马上付", "仅限今日", "锁定名额"]),
    ("信息不实与隐瞒", ["学历造假", "年龄造假", "隐瞒", "编的", "包装", "美化",
                   "假照片", "盗图", "职业编", "查不到"]),
    ("限制人身与社交", ["不许离婚", "不许退出", "不能退", "不得中途退出", "必须配合",
                   "禁止接触", "不准见别人", "限制社交"]),
    ("拖延与换人", ["换人", "一直换", "不合适", "再等等", "缘分没到", "下一个",
                "介绍了好几个"]),
    ("冒用资质与格式合同", ["资质", "备案", "监管", "门店", "总部", "连锁",
                     "工商注册", "公司直营"]),
]

# 正规婚介服务应有的要素
LEGAL_ELEMENTS = [
    ("机构有登记信息", ["营业执照", "注册", "公司", "工商", "统一社会信用", "企业"]),
    ("有书面服务合同", ["合同", "协议", "服务协议", "条款", "签字", "盖章"]),
    ("有明确服务内容", ["服务内容", "推荐次数", "介绍人数", "服务期限", "服务项目",
                  "几次", "安排几次"]),
    ("有明确费用与发票", ["费用", "收费", "价格", "多少钱", "发票", "收据", "付款"]),
    ("有退费规则", ["退费", "退款", "退费规则", "违约金", "解约"]),
]

# 服务期与时间风险
TIMING_RISKS = [
    ("承诺的服务期很短", ["一个月", "两个月", "三个月", "短期", "体验期"]),
    ("服务期太长无节点", ["一年", "两年", "三年", "长期", "直到结婚"]),
    ("介绍频率未写", ["尽快", "抓紧", "很快", "近期", "优先安排"]),
    ("退费按月不退", ["按月不退", "当月不退", "月费不退", "过月作废"]),
]

# 维权路径
PATHS = [
    ("第 1 步（先核资质，别急着付全款）",
     "把机构名称查到 **国家企业信用信息公示系统**（官网）确认注册信息、"
     "经营范围与存续状态。**线下门店尤其要查**——很多是加盟或纯营销壳。"
     "**先付小额、保留退路**，不要一次性交清全程费用。"),
    ("第 2 步（把服务内容写进合同）",
     "**合同必须写明**：服务期限、推荐次数或安排几次、介绍人的基本信息来源、"
     "服务未达约定次数怎么办、**双方如何解除与退费**。"
     "**只写「介绍对象」不写次数的合同，等于没有约束**。"),
    ("第 3 步（核对方信息真实性）",
     "**每介绍一个人，要求提供基础信息**：年龄、学历、职业、婚姻状况、"
     "是否有子女。**要求对方书面确认这些信息真实**。"
     "发现明显造假（照片与本人不符、年龄职业造假），**这构成欺诈，可主张解除与赔偿**。"),
    ("第 4 步（保护自己的社交自由）",
     "**人身自由是底线**。任何机构要求「不许离婚」「不准接触其他人」"
     "「不能中途退出」的条款**显失公平，可主张无效**。"
     "你有权随时终止与任何人的接触，也有权随时结束服务。"),
    ("第 5 步（留痕）",
     "**保存**：合同、付款凭证、介绍人信息（每次都要留档）、"
     "聊天记录、录音、推荐的资料、你提出的需求与对方承诺的回复。"),
    ("第 6 步（协商退费）",
     "**书面提出退费要求**，写明：已支付金额、服务已提供情况、"
     "未达约定的次数或期限、要求退还金额与时限。"
     "**先书面、后协商**，保留EMS 签收记录或现场回执。"),
    ("第 7 步（投诉与诉讼）",
     "协商不成 → **12315**（消费纠纷）与**当地民政部门**（婚介行业归口）；"
     "涉及虚假宣传、诈骗的 → **公安机关报案**；"
     "金额较大且有证据的 → **咨询律师评估诉讼**。"),
]

# 证据类别
EVIDENCE = [
    ("机构资质与登记", ["营业执照", "注册", "工商", "公示", "企业", "门店", "加盟"]),
    ("合同与服务协议", ["合同", "协议", "条款", "服务内容", "服务期限", "次数"]),
    ("付款凭证", ["发票", "收据", "转账", "付款", "账单", "刷卡", "分期记录"]),
    ("介绍对象信息记录", ["介绍", "推荐", "照片", "资料", "对方信息", "推荐人"]),
    ("沟通与承诺记录", ["微信", "聊天", "短信", "通话", "录音", "工单", "承诺"]),
    ("需求提出与回复", ["需求", "要求", "回复", "反馈", "协商", "要求介绍"]),
    ("协商与投诉记录", ["退费", "要求退", "投诉", "协商", "答复", "回执", "调解"]),
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
    if n in ("有", "是", "已经", "已", "已完成", "已做", "可以", "能", "已签", "已核实"):
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


# ------------------------------------------------------------------ 一 服务定性
def classify(f):
    txt = (f["service_type"] or "") + "|" + (f["org"] or "") + "|" + (f["detail"] or "")
    if not filled(txt):
        return []
    return [lbl for lbl, ws in SERVICE_TYPES if hit_any(txt, ws) is True]


def checks_service(f):
    out = []
    kinds = classify(f)
    t = f["service_type"]
    if unknown(t) and unknown(f["org"]):
        out.append(("婚介服务类型", "待补正",
                    "通过什么形式提供服务、找的是哪家机构未填。"
                    "**类型决定监管口径**：线下门店婚介涉及市场监管，"
                    "线上平台还要看电信与个人信息保护。"))
    elif not kinds:
        out.append(("婚介服务类型", "待补正",
                    "没识别出服务类型。请按这些词填："
                    "线下门店/实体店、线上/APP/平台、红娘牵线、"
                    "相亲角活动、一对一定制、套餐服务。"))
    else:
        out.append(("婚介服务类型", "通过", "本次服务属于：**%s**。" % "、".join(kinds)))
    return out


def checks_terms(f):
    out = []
    c = f.get("contract", "") or ""
    if unknown(c):
        out.append(("服务合同是否规范", "待补正",
                    "有没有签合同、合同里写了什么未填。"
                    "**婚介纠纷的核心是合同写了什么**——"
                    "尤其是**服务期限、推荐次数、解除与退费**三项。"))
    else:
        have = [lbl for lbl, ws in LEGAL_ELEMENTS if hit_any(c, ws) is True]
        if have:
            out.append(("服务合同是否规范", "有风险",
                        "合同含：%s。**继续检查三项是否写死**："
                        "① 服务期限多长；② 介绍或安排了几次；"
                        "③ **未达约定怎么退**。只写「协助介绍」不写次数的，"
                        "约束力很弱。" % "、".join(have)))
        else:
            out.append(("服务合同是否规范", "待补正",
                        "填的是「%s」，没识别出合同要素。"
                        "请用这些词补充：合同/协议、服务内容、服务期限、"
                        "推荐次数、费用发票、退费/违约金。" % c))
    # 限制人身自由的条款显失公平
    # 注意：即使合同未填，这一项也要输出——否则 contract 一空，整段就只剩一行
    if hit_any(c, ["不许离婚", "不准见别人", "禁止接触", "不能中途退出", "不得退出",
                   "限制社交", "必须配合"]) is True:
        out.append(("是否存在限制人身自由的条款", "不通过",
                    "**合同含限制人身自由的条款**。"
                    "**婚姻是人身自由，你有权随时终止接触、随时结束服务**。"
                    "这类条款**显失公平，可主张无效**。"
                    "同时保留相关证据，若机构以此为由限制你，"
                    "必要时向公安机关反映。"))
    elif unknown(c):
        out.append(("是否存在限制人身自由的条款", "待补正",
                    "合同未填，**无法判断是否有限制人身自由的条款**。"
                    "拿到合同后重点看：是否写了"
                    "「不准与其他人接触」「不能中途退出」这类内容。"))
    else:
        out.append(("是否存在限制人身自由的条款", "通过", "未见限制人身自由的条款。"))
    return out


# ------------------------------------------------------------------ 二 承诺与套路
def checks_promise(f):
    out = []
    p = f["promise"]
    if unknown(p):
        out.append(("机构做过哪些承诺", "待补正",
                    "机构说了什么、信誓旦旦承诺什么未填。"
                    "**「包结婚」「不结婚退款」这类话原样记下来**——"
                    "它既是判断套路的关键，也是投诉与退费的证据。"))
        return out
    hits = [lbl for lbl, ws in FRAUD_PATTERNS if hit_any(p, ws) is True]
    if not hits:
        out.append(("机构做过哪些承诺", "有风险",
                    "暂未识别到明显套路话术。"
                    "**但要注意**：婚介的承诺几乎都是**口头**的，"
                    "**没写进合同就等于没说**。追问三件事："
                    "**服务多久、介绍几次、达不到怎么退**。"))
    else:
        out.append(("机构做过哪些承诺", "不通过",
                    "涉及以下高风险表述：**%s**。"
                    "其中「包结婚」「包成功」几乎可以确定是话术——"
                    "**婚姻自主决定，任何机构都不能保证结果**。"
                    "「限时优惠」「今天下单」是用紧迫感逼你当天付钱的套路。"
                    % "、".join(hits)))
    return out


def checks_intro(f):
    out = []
    n = f.get("intro_count", "") or ""
    if unknown(n):
        out.append(("实际介绍了几个人", "待补正",
                    "到目前介绍了几个人、见过几面未填。"
                    "**这是衡量服务是否履行的唯一客观标准**——"
                    "**每次介绍都要留档**（姓名或编号、日期、联系方式或照片）。"))
    else:
        cnt = parse_num(n)
        if cnt is not None and cnt <= 2:
            out.append(("实际介绍了几个人", "有风险",
                        "只介绍了 %s 个人。**结合服务期限判断**："
                        "若合同约定了次数或期限而未达成，"
                        "**可据此主张退还未服务部分**。" % fmt_num(cnt)))
        else:
            out.append(("实际介绍了几个人", "通过",
                        "已介绍 %s 个。**仍要逐个核对信息真实性**。" % fmt_num(cnt)))
    # 信息真实性——即使介绍人数没填，这一项也要输出，否则整段会少一行
    fa = f.get("intro_fake", "") or ""
    if unknown(fa):
        out.append(("介绍对象信息是否核实", "待补正",
                    "对方的基本信息（年龄、学历、职业、婚姻状况）有没有核对过。"
                    "**这是最容易出问题的地方**：包装、盗图、年龄职业造假都常见。"
                    "**要求机构提供并书面确认信息真实**。"))
    elif hit_any(fa, ["造假", "编的", "包装", "美化", "盗图", "假照片", "查不到",
                      "对不上", "不是本人"]) is True:
        out.append(("介绍对象信息是否核实", "不通过",
                    "**发现信息不实**：%s。"
                    "**这构成欺诈**，可主张解除服务合同、"
                    "退还相应费用并赔偿损失。"
                    "**先固定证据**：与对方核实身份、"
                    "保存聊天记录与资料截图、留存原始照片来源。" % fa))
    else:
        out.append(("介绍对象信息是否核实", "通过", "未发现明显的信息造假。"))
    return out


# ------------------------------------------------------------------ 三 费用与退费
def checks_fee(f):
    out = []
    a = f.get("paid_amount", "") or ""
    if unknown(a):
        out.append(("已支付费用", "待补正",
                    "一共付了多少钱、什么时候付的未填。"
                    "**金额与凭证是退费主张的基础**。"))
    else:
        amt = parse_num(a)
        big = amt is not None and amt >= 10000
        out.append(("已支付费用", "有风险" if big else "通过",
                    "已支付 %s。%s" % (money(amt),
                                      "**金额较大，是典型维权场景**；"
                                      "**没付款是相对有利的位置**，"
                                      "很多纠纷可以协商解除而不必走诉讼。"
                                      if big else
                                      "**保存每一笔凭证**；若服务未达约定，"
                                      "可主张按未服务部分退还。")))
    inst = f.get("installment", "") or ""
    if unknown(inst):
        out.append(("是否分期或贷款", "待补正",
                    "有没有让你分期、办贷款未填。"
                    "**贷款责任不能转移**——机构失联后你照样还贷。"))
    elif yes(inst) or hit_any(inst, ["分期", "贷款", "月供", "花呗", "借呗",
                                "信用卡分期", "网贷"]) is True:
        out.append(("是否分期或贷款", "不通过",
                    "**机构让你分期或办贷款**。风险与学历培训同："
                    "**还款责任在你身上，机构跑了你照样还**，"
                    "可能同时背债务与征信污点。**应立即停止后续支付**"
                    "并向贷款机构问清总利息与提前还款规则。"))
    else:
        out.append(("是否分期或贷款", "通过", "未涉及分期与贷款。"))
    return out


def checks_refund(f):
    out = []
    r = f["refund_rule"]
    if unknown(r):
        out.append(("退费规则", "待补正",
                    "合同里怎么写退费、机构现在怎么说未填。"
                    "**婚介退费最容易扯皮的地方**——"
                    "很多合同写「介绍几个都不合适即终止服务」，"
                    "**而「不合适」由谁认定没有说**。"))
    elif hit_any(r, ["不能退", "不退", "概不退款", "不予退款", "按月不退", "当月不退",
                     "月费不退", "过月作废"]) is True:
        out.append(("退费规则", "不通过",
                    "退费规则是「**%s**」。"
                    "**这类条款实质性排除了你的主要权利**，"
                    "可主张**显失公平或属不合理免除机构责任的格式条款**。"
                    "**但主张无效需要走程序**，更实际的做法是："
                    "**先书面提出退费，协商不成再投诉**。" % r))
    else:
        out.append(("退费规则", "有风险",
                    "退费规则：**%s**。**逐条看有没有两个坑**："
                    "① 「不合适即终止」但**由谁认定没说**；"
                    "② 是否**区分已服务与未服务部分**。" % r))
    st = f["status"]
    if unknown(st):
        out.append(("当前服务状态", "待补正",
                    "还在服务中、已停止、已要求解约还是已退部分未填。"
                    "**这决定维权起点**：还在服务中的，先明确解约；"
                    "已停服的，直接主张按未服务部分退费。"))
    elif hit_any(st, ["已停", "已解约", "已终止", "不做了", "停止"]) is True:
        out.append(("当前服务状态", "通过", "服务已停止或已解约，**可主张按未服务部分退费**。"))
    elif hit_any(st, ["还在做", "继续", "仍在", "还在服务"]) is True:
        out.append(("当前服务状态", "有风险",
                    "服务仍在进行。**先明确书面解约**（EMS 或书面函 + 签收记录），"
                    "**不要一边继续接受服务一边要求全退**——"
                    "这会被视为继续接受服务，可能影响退费主张。"))
    else:
        out.append(("当前服务状态", "有风险", "状态：**%s**。" % st))
    return out


def checks_timing(f):
    out = []
    t = f["term"]
    if unknown(t):
        out.append(("约定的服务期限", "待补正",
                    "合同约定的服务期多长、什么时候开始的未填。"
                    "**期限长短直接影响退费计算**。"))
        return out
    hits = [lbl for lbl, ws in TIMING_RISKS if hit_any(t, ws) is True]
    if hits:
        out.append(("约定的服务期限", "有风险",
                    "期限描述：**%s**，涉及 %s。"
                    "**三个要问清的点**：① 期限多长、起算日是哪天；"
                    "② **期限到了没介绍成怎么算**；"
                    "③ 期限内介绍的几何算履约完成。" % (t, "、".join(hits))))
    else:
        out.append(("约定的服务期限", "通过", "服务期限：**%s**。" % t))
    return out


# ------------------------------------------------------------------ 四 证据
def has_content(s):
    for part in str(s or "").split("|"):
        if filled(part):
            return True
    return False


def checks_evidence(f):
    out = []
    a = f.get("evidence_owned", "") or ""
    b = f.get("evidence_desc", "") or ""
    if not has_content(a) and not has_content(b):
        out.append(("证据总览", "待补正",
                    "已有证据既没勾选也没写清单。"
                    "**婚介维权最缺的是「介绍记录」**——"
                    "每次介绍都留一份（日期、对方信息、联系方式/照片），"
                    "没有记录就无法证明服务未达约定。"))
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
    "机构资质与登记": "在国家企业信用信息公示系统查机构名称，截图",
    "合同与服务协议": "调取或复印合同，重点看服务期限、次数、解除退费条款",
    "付款凭证": "保存发票、收据、每一笔转账与刷卡记录",
    "介绍对象信息记录": "每次介绍都留档：日期、对方基本信息、照片、联系方式",
    "沟通与承诺记录": "保存聊天、短信、通话录音、工单，尤其是承诺内容",
    "需求提出与回复": "保留你提的需求与对方回复的记录",
    "协商与投诉记录": "保存书面退费要求、EMS 签收、投诉编号、答复",
}


def evidence_gap(f):
    a = f.get("evidence_owned", "") or ""
    b = f.get("evidence_desc", "") or ""
    got = a + "|" + b
    gaps = []
    if has_content(got):
        for label, keys in EVIDENCE:
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in EVIDENCE]
    if not any(k in got for k in ["介绍", "推荐", "对方信息"]):
        gaps.append("介绍对象信息记录")
    if not any(k in got for k in ["发票", "收据", "转账", "付款"]):
        gaps.append("付款凭证")
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
    if unknown(f.get("qualification", "")):
        extra.append(("查机构工商登记信息", "国家企业信用信息公示系统查名称与存续状态"))
    if hit_any(f.get("contract", ""), ["不许离婚", "不准见别人", "不能中途退出",
                                 "禁止接触", "限制社交"]) is True:
        extra.append(("主张限制人身自由条款无效", "婚姻自主，人身自由不可被限制"))
    if hit_any(f.get("intro_fake", ""), ["造假", "编的", "包装", "盗图", "查不到"]) is True:
        extra.append(("固定信息造假证据", "与对方核实身份、留存资料来源截图"))
    if yes(f.get("installment", "")):
        extra.append(("停止后续支付并问清贷款条款", "机构跑了你照样还贷"))
    if not filled(f.get("intro_count", "")):
        extra.append(("整理介绍记录", "每次介绍的日期、对方信息都要留档"))
    if not filled(f.get("refund_rule", "")):
        extra.append(("确认退费规则", "合同怎么写、机构现在怎么说"))
    seen = set()
    res = []
    for n, s in todos + extra:
        if n not in seen:
            seen.add(n)
            res.append((n, s))
    return res


# ------------------------------------------------------------------ 报告
SECTIONS = [
    "二、服务类型与合同核查",
    "三、机构承诺与套路识别",
    "四、介绍服务与信息核实",
    "五、费用与退费规则",
    "六、服务期限与时效风险",
    "七、证据清单与缺口",
]


def render(f, results, steps, todos, today, gaps):
    L = []
    L.append("# 婚介服务合同与退费核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 服务机构：%s" % (f.get("org", "") or "未填"))
    L.append("- 服务类型：%s" % (f.get("service_type", "") or "未填"))
    L.append("- 已支付：%s" % (f.get("paid_amount", "") or "未填"))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在明确的不利因素（套路承诺 / 限制人身自由条款 / "
                 "信息造假 / 不可退条款 / 贷款分期），应立即书面解约并核查资质。**")
    elif risk:
        L.append("**判定：未发现明确违法，但合同要素、退费规则与介绍记录仍有缺口，"
                 "建议补齐后再决定是否继续付费。**")
    else:
        L.append("**判定：采集表关键项未填，暂时给不出确定结论；**"
                 "请把服务类型、机构名称、机构承诺、已介绍人数与退费规则填完再重跑。"
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

    L.append("## 八、路径与维权流程")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 九、投诉渠道")
    L.append("")
    L.append("| 渠道 | 适用场景 |")
    L.append("|---|---|")
    L.append("| 12315 | 消费纠纷，婚介服务费争议的主要渠道 |")
    L.append("| 民政部门 | 婚介（婚姻介绍服务）行业归口管理 |")
    L.append("| 市场监管部门 | 虚假宣传、格式条款、消费欺诈 |")
    L.append("| 公安机关 | 诈骗、虚构信息骗取费用 |")
    L.append("| 国家企业信用信息公示系统 | 查机构是否真实存在、是否存续 |")
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
             "婚介服务的合同效力与退费规则，"
             "**以合同约定、监管规定与司法机关认定为准**。")
    L.append("- 报告金额按已填凭证汇总，**实际退费金额以协商或认定结果为准**。")
    L.append("- 不预测机构是否同意退费，也不预测投诉与诉讼结果。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 涉及**双方姓名、照片、联系方式等个人信息**，"
             "**本地处理，不要外发**。")
    L.append("- 婚介纠纷常涉及双方隐私与人际矛盾，**不建议在公开平台曝光对方信息**。")
    L.append("- 本结果依通用规则整理，不替代专业意见，"
             "最终以主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps):
    return {
        "核查日期": today.isoformat(),
        "服务类型": classify(f),
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "已支付": parse_num(f.get("paid_amount", "")),
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "service_type": get_text(kv, ["婚介服务类型", "服务形式", "服务类型"]),
        "org": get_text(kv, ["婚介机构名称", "机构名称", "找的哪家"]),
        "detail": get_text(kv, ["服务经过", "事情经过", "经过"]),
        "contract": get_text(kv, ["服务合同情况", "合同内容", "协议内容"]),
        "promise": get_text(kv, ["机构做过的承诺", "机构承诺", "机构怎么说"]),
        "qualification": get_text(kv, ["机构资质核实", "是否查过资质", "机构是否正规"]),
        "term": get_text(kv, ["约定的服务期限", "服务期", "期限多久"]),
        "intro_count": get_text(kv, ["已介绍人数", "介绍了几个人", "见过几个"]),
        "intro_fake": get_text(kv, ["介绍对象信息核实", "信息是否核实", "对方信息真不真"]),
        "paid_amount": get_text(kv, ["已支付费用", "一共付了多少钱", "已交金额"]),
        "installment": get_text(kv, ["是否分期或贷款", "是否让你分期", "有没有办贷款"]),
        "refund_rule": get_text(kv, ["退费规则", "退款规则", "怎么退"]),
        "status": get_text(kv, ["当前服务状态", "服务状态", "现在什么情况"]),
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
    if not filled(f["org"]):
        missing.append("婚介机构名称")
    if not filled(f["promise"]):
        missing.append("机构做过的承诺")
    if not filled(f["paid_amount"]):
        missing.append("已支付费用")

    results = [
        ("服务类型与合同核查", checks_service(f) + checks_terms(f)),
        ("机构承诺与套路识别", checks_promise(f)),
        ("介绍服务与信息核实", checks_intro(f)),
        ("费用与退费规则", checks_fee(f) + checks_refund(f)),
        ("服务期限与时效风险", checks_timing(f)),
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
