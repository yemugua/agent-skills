#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""押金争议核查脚本 v1.0.1

输入：租赁信息 markdown（按《租赁信息采集表》填写）
输出：押金性质辨析 / 扣款逐条判定 / 证据完整度 / 逾期与时效 / 可主张金额 / 维权路径 / 催告话术

只做「定性判定 + 金额测算 + 时效推算 + 补证与路径建议」，
不代拟正式法律文书、不承诺结果、不编造条款与判例。
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

VERSION = "1.0.1"
PLACEHOLDER = ("待填写", "待填", "暂无", "—", "-", "?", "（待补）", "未填", "不涉及", "无", "", "无/无")
TODAY = date.today()
DEFAULT_REFUND_DAYS = 15
LIMIT_YEARS = 3

DATE_RE = re.compile(r"(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})")
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

# (判定, 匹配关键词, 依据, 下一步) —— 顺序即优先级，先命中先返回
DEDUCT_RULES = [
    ("正当", r"欠租|拖欠房租|租金", "欠租可从押金抵扣，但需已履行催告且金额对应", "先把欠租结清并留凭证，再谈其余"),
    ("正当", r"欠(水|水电|电|燃气|气|物业|宽带)", "水电燃气物业以结算单为准，属应结清项目", "拿结清截图，扣款才站得住"),
    ("正当", r"故意|重大过失|砸|打碎|乱涂|涂鸦|打孔|擅自|拆改|转租",
     "故意或重大过失造成的损坏可扣，需照片对照 + 交接时无此痕迹", "要求他给损坏照与报价，过高可请求调减"),
    ("存疑", r"违约金|提前退租|提前解约|违约", "提前退租违约金可扣，但约定过高可请求适当减少",
     "核一下合同金额是否超过 3 个月租金，明显过高可主张调减"),
    ("存疑", r"锁|钥匙|门禁", "只认实际换锁费用，需要票据", "要他给出换锁票据，没有票据就别认"),
    ("存疑", r"保洁|清洁|深度清洁|开荒", "除非合同明确约定且金额与市价相符", "对照入住时的交接状态，看他有没有交接单"),
    ("不成立", r"空置|没租出|找不到下家|空窗|断租", "房屋再出租是出租方经营风险，无转嫁依据", "这条直接不认，写进催告函"),
    ("不成立", r"折旧|贬值|价值贬损|折价", "无法律依据", "直接不认"),
    ("不成立", r"正常磨损|老化|正常使用|墙面.{0,4}(掉漆|起翘|发黄|破损)|墙纸|霉|渗水|管道老|家电老|漏水|发黄",
     "自然损耗属出租方风险，维修义务在房东", "直接不认，附入住照片证明接手时就是这个状态"),
    ("不成立", r"上一位|上租客|前租客|上家租客", "前租客的损耗与你无关", "直接不认"),
    ("存疑", r"抹灰|刷墙|重新刷|重刷|刷漆|翻新|维修费|修理工|家电维修",
     "墙面与电器老化属自然损耗，维修义务在房东", "要求提供维修合同与票据，自然磨损部分不应由你出"),
]

# (报告显示名, 采集表里的匹配关键词, 缺了会怎样)
EVIDENCE = [
    ("合同签字页", ("合同签字页",), "合同签没签、押金条款写的什么都没证，全靠对方良心"),
    ("付款凭证", ("付款凭证",), "押金付没付、付多少说不清，主张就缺地基"),
    ("入住时现状照片或视频", ("入住时现状", "入住现状"), "**最致命的一项**：没有它，'不是我弄坏的'没有起点"),
    ("退租时现状照片或视频", ("退租时现状",), "没有它，无法证明你交还时没变差"),
    ("水电燃气表读数与结清凭证", ("结清凭证", "表读数"), "费用结不清，房东有借口拖全款"),
    ("交接确认（交接单/聊天）", ("交接确认",), "没有交接确认，'房已还'这件事无从证明"),
    ("催告记录", ("催告记录",), "既是谈判筹码，也是 3 年时效的续命符"),
    ("房东扣款的依据（票据报价照片）", ("房东扣款的依据", "扣款的依据"), "举证责任在他，他给不出就很难站住"),
]

DEPOSIT_WORDS = ("押金", "保证金", "押一", "押二", "押三", "租押", "保证")


def clean(s):
    return re.sub(r"\s+", " ", str(s or "").strip())


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def is_ph(s):
    return clean(s) in PLACEHOLDER


def parse_date(tok):
    t = clean(tok)
    if is_ph(t):
        return None
    m = DATE_RE.search(t)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def parse_money(tok):
    t = clean(tok).replace(",", "").replace("元", "")
    if is_ph(t):
        return None
    m = NUM_RE.search(t)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except Exception:
        return d.replace(year=d.year + n, day=28)


def fmt_money(v):
    if v is None:
        return "—"
    f = float(v)
    if abs(f - round(f)) < 1e-9:
        return "%d" % round(f)
    return "%.2f" % f


def _find_fields(line, labels, want_index=False):
    """返回 (行索引, 值)：找含 label 的单元格并取其后一格"""
    if "|" not in line:
        return None, None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    # 踩坑：列表推导里的 c 是新作用域变量，外面用 c 会 NameError，这里必须显式遍历
    if len(cells) < 3 and any(k in norm(cc) for cc in cells for k in ("项目", "项", "填什么")):
        return None, None
    for lab in labels:
        for i, c in enumerate(cells):
            if lab in norm(c) and i + 1 < len(cells):
                return i, cells[i + 1]
    return None, None


def pick(text, labels, parser, after=None):
    """遍历全文，返回第一个能被 parser 解析的字段值。
    关键 1：表格里常有形如「| 押金金额 | 数字（元） |」的说明行，
            只取第一个单元格内容会把「数字（元）」当值 → 必须取第一个能解析的。
    关键 2：after 用来限定「只看某一节之后」（例如欠费只能取第三节，
            否则会扫到扣款表里「| 4 | 欠租 | 500 |」那一行，把同一笔钱算两遍）。"""
    started = (after is None)
    for line in text.splitlines():
        s = line.strip()
        if not started:
            if s.startswith("#") and after in s:
                started = True
            continue
        if norm(s) in ("", "---"):
            continue
        _, v = _find_fields(line, labels)
        if v is None:
            continue
        got = parser(v)
        if got is not None:
            return got
    return None


def get_text(text, *labels):
    for line in text.splitlines():
        if norm(line) in ("", "---"):
            continue
        _, v = _find_fields(line, labels)
        if v is None or is_ph(v):
            continue
        v = clean(v)
        # 形如「押金 / 保证金 / 定金 / 订金」是模板示例，不是用户填的值，跳过
        if len(v) > 8 and ("/" in v or chr(12289) in v):
            continue
        return v
    return ""


def get_amount(text, *labels, **kw):
    return pick(text, labels, parse_money, **kw)


def get_date(text, *labels, **kw):
    return pick(text, labels, parse_date, **kw)


# 踩坑：正则字符类里的中文在写入时会被换字（天 → 别的汉字），
# 直接写中文会让匹配静默失效 → 统一用 \uXXXX 转义，文件里保持纯 ASCII。
SPLIT_RE = re.compile("[|,;\uFF0C\u3001/]")
DAY_RE = re.compile(r"^(\d{1,3})\s*\u5929?$")


def get_days(text, *labels):
    """退还时限：只看「标签 … 数字」这一种形态，整文正则，不逐行走单元格"""
    for lab in labels:
        m = re.search(re.escape(lab) + r"[^0-9\u5982\u4f8b\u793a\u8303\u5f97\u6761\u4efb\u4f55]{0,6}(\d{1,3})", text)
        if m:
            return int(m.group(1))
    return None


def yes_no(text, keys):
    for line in text.splitlines():
        if norm(line) in ("", "---"):
            continue
        _, v = _find_fields(line, keys)
        if v is None:
            continue
        t = norm(v)
        if "无" in t and "有" not in t:
            return False
        if "有" in t:
            return True
        if "否" in t:
            return False
        if "是" in t:
            return True
    return False


def classify(text):
    """返回 (判定, 依据, 下一步)"""
    n = norm(text)
    if not n:
        return "存疑", "无对应可扣规则可套", "先让他讲清楚扣款依据，再逐条核对"
    for verdict, pat, reason, action in DEDUCT_RULES:
        if re.search(pat, n, re.I):
            return verdict, reason, action
    return "存疑", "无对应可扣规则可套（未识别到可扣事由关键词）", "先让他讲清楚扣款依据，再逐条核对"


def _col_index(cells, keywords):
    for i, c in enumerate(cells):
        n = norm(c)
        if n in ("#",) or n.startswith("*"):
            continue
        for k in keywords:
            if k in n:
                return i
    return None


def parse_deductions(text):
    """只解析「扣什么」那一张表；靠列头定位，不靠行号。
    踩过的坑：默认按 cells[0]/cells[1] 取，会把
    「| 押金金额 | 5000 |」（金额列在 1）和证据表首行「| 1 | 合同签字页… |」误判成扣款。"""
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if "|" in s:
            cells = [c.strip() for c in s.strip("|").split("|")]
            joined = "".join(cells)
            if ("扣什么" in joined) or ("扣款" in joined and "金额" in joined):
                i_name = _col_index(cells, ("扣什么", "事由", "扣款项", "扣了什么"))
                i_amt = _col_index(cells, ("金额",))
                i_why = _col_index(cells, ("理由", "原因", "说明"))
                i_tk = _col_index(cells, ("票据", "照片", "凭证", "有没有"))
                j = i + 1
                while j < len(lines):
                    t = lines[j].strip()
                    if t.startswith("#") or "|" not in t:
                        break
                    c2 = [c.strip() for c in t.strip("|").split("|")]
                    if len(c2) < 3:
                        break
                    def cell(idx):
                        return c2[idx] if (idx is not None and idx < len(c2)) else ""
                    name = clean(cell(i_name)) or clean(c2[0])
                    amount = parse_money(cell(i_amt))
                    if not name or is_ph(name) or amount is None:
                        j += 1
                        continue
                    out.append({
                        "name": name,
                        "amount": amount,
                        "reason": clean(cell(i_why)),
                        "ticket": clean(cell(i_tk)),
                    })
                    j += 1
                break
        i += 1
    return out


def fix_hint(label):
    return {
        "合同签字页": "翻合同拍签字页与押金条款，微信发一份给对方留确认",
        "付款凭证": "去银行/微信账单导出转账记录，截图中含对方信息与金额",
        "入住时现状照片或视频": "最要紧的一条：现在补拍只能拍现状，尽量找同期替代（搬家记录、之前的视频通话）",
        "退租时现状照片或视频": "立刻补拍同机位全景 + 表读数，说明拍摄时间",
        "水电燃气表读数与结清凭证": "从水电 App 导出结清截图，带时间与水费单号",
        "交接确认（交接单/聊天）": "发《房屋交接确认》文字给房东，要他回「对」",
        "催告记录": "先发第一条催告（含金额+期限+后果），这就是第一次留痕",
        "房东扣款的依据（票据报价照片）": "书面要求对方提供扣款依据，他不给就写进催告函",
    }.get(label, "发书面说明并要求对方确认")


def build_report(path, base, lpr):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    dep = get_amount(text, "押金金额", "押金")
    if dep is None:
        return None, ("未解析到押金金额：请在《租赁信息采集表》的「押金金额」栏填数字（元）。"
                      "其它项会自动跳过，但金额算不出来，后面的判定与测算都没意义。")

    base = base or TODAY
    end = get_date(text, "退租交接日期", "合同终止日", "退租交接")
    agree_days = get_days(text, "约定的退还时限", "退还时限", "退还期限")
    if not agree_days or agree_days <= 0:
        agree_days = DEFAULT_REFUND_DAYS
    due = (end + timedelta(days=agree_days)) if end else None

    kind_raw = clean(get_text(text, "押金名称", "押金性质", "押金叫什么") or "押金")
    has_deposit_word = any(w in kind_raw for w in DEPOSIT_WORDS)
    is_fine = ("定金" in kind_raw) and not has_deposit_word   # 定金 → 定金罚则
    is_earnest = ("订金" in kind_raw) and not has_deposit_word  # 订金 → 一般按预付款

    rows = parse_deductions(text)
    deduct_total = 0.0
    rows_out = []
    for r in rows:
        verdict, reason, action = classify(r["name"] + " " + r["reason"])
        deduct_total += r["amount"]
        has_ticket = "有" in r["ticket"]
        rows_out.append((r, verdict, reason, action, has_ticket))

    # 欠费只看「结算与欠费」那一节，避免把扣款表里同样一笔钱算两遍
    rent_owe = get_amount(text, "欠房租", "欠租", after="结算与欠费")
    util_owe = get_amount(text, "欠水电燃气物业", "欠水电", after="结算与欠费")
    rent_owe = 0.0 if rent_owe is None else rent_owe
    util_owe = 0.0 if util_owe is None else util_owe

    overdue = (base - due).days if due else 0

    legit = sum(r["amount"] for r, v, _, _, _ in rows_out if v == "正当")
    debt = rent_owe + util_owe
    remain = max(0.0, dep - legit - debt)
    interest = 0.0
    if overdue > 0 and remain > 0:
        interest = round(remain * lpr / 100.0 / 365 * overdue, 2)
    claimable = round(remain + interest, 2)

    limit_end = add_years(due, LIMIT_YEARS) if due else None
    left = (limit_end - base).days if limit_end else None

    have, lack = [], []
    for label, keys, impact in EVIDENCE:
        (have if yes_no(text, keys) else lack).append((label, impact))
    score = len(have)

    L = []
    A = L.append
    A("# 押金争议核查（本地处理，不上传）")
    A("")
    A("- 基准日：%s ｜ 解析来源：%s" % (base.isoformat(), os.path.basename(path)))
    A("- 本表只做定性判定与金额测算，**不构成法律意见、不承诺结果**；"
      "各地受理口径与裁判尺度不同，以现行有效文本与当地为准。")
    A("")

    # 一、摘要
    A("## 一、结论摘要")
    A("")
    if is_fine:
        A("- 押金名称写的是「%s」→ **适用定金规则**：付定金方违约不得要回，"
          "收定金方违约才**双倍返还**。" % kind_raw)
    elif is_earnest:
        A("- 押金名称写的是「%s」→ 一般按**预付款**处理，不适用定金罚则；"
          "除非合同明确写「定金」且与实际用途一致，否则**没有双倍返还**。" % kind_raw)
    else:
        A("- 押金名称写的是「%s」→ **按押金（保证金）规则**：结清费用、无违约后应退，"
          "⚠️ **押金没有双倍返还规则**（很多人搞错，想拿双倍的多半是合同写成了「押金/保证金」）。"
          % kind_raw)
    A("- 押金 %s 元，房东扣了 %s 元，其中判定「正当」约 %s 元。"
      % (fmt_money(dep), fmt_money(deduct_total), fmt_money(legit)))
    if overdue > 0:
        A("- **已逾期 %d 天**（应退日 %s%s）。"
          % (overdue, due.isoformat(), "" if agree_days != DEFAULT_REFUND_DAYS else "，合同未约定，按 15 天计"))
    else:
        A("- 尚在应退期内（应退日 %s）。" % (due.isoformat() if due else "未填退租日期，无法推算"))
    if left is not None:
        A("- 距**诉讼时效届满（3 年）约 %d 天**（%s）；催告、投诉、起诉都会**中断重算**。"
          % (left, limit_end.isoformat()))
    A("- 可主张约 **%s 元**（押金 − 正当扣款 − 欠费 ＋ 逾期资金占用）。" % fmt_money(claimable))
    if lack:
        A("- 当务之急：**%s**——%s。" % (lack[0][0], fix_hint(lack[0][0])))
    A("")

    # 二、扣款逐条（8 列，别少列：之前漏了「票据」列导致整行撑裂）
    A("## 二、扣款逐条判定")
    A("")
    A("| # | 扣什么 | 金额 | 房东理由 | 票据 | 判定 | 认定依据 | 下一步 |")
    A("|---|---|---|---|---|---|---|---|")
    if rows_out:
        for i, (r, verdict, reason, action, has_ticket) in enumerate(rows_out, 1):
            A("| %d | %s | %s | %s | %s | **%s** | %s | %s |"
              % (i, clean(r["name"]), fmt_money(r["amount"]), r["reason"] or "—",
                 "有票据" if has_ticket else "无票据", verdict, reason, action))
    else:
        A("| 1 | 未识别到扣款明细 | — | — | — | — | 请在采集表第二节逐条填「扣什么 / 金额 / 理由」 | 补填后自动判定 |")
    A("")

    # 三、性质
    A("## 三、押金性质辨析")
    A("")
    A("| | 押金 / 保证金 | 定金 | 订金 |")
    A("|---|---|---|---|")
    A("| 你合同写的 | %s | %s | %s |"
      % (kind_raw if not (is_fine or is_earnest) else "—",
         kind_raw if is_fine else "—",
         kind_raw if is_earnest else "—"))
    A("| 双倍返还 | **没有这条规则** | 仅收受方违约时双倍返还 | 一般不适用 |")
    A("| 退还规则 | 结清费用、无违约后应退 | 按定金罚则，不是退不退的问题 | 按预付款结算 |")
    A("| 上限 | 各地口径不一（常见 1～2 个月租金），超出不一定当然无效 | 一般不超过主合同标的额 20% | 无特别限制 |")
    A("")

    # 四、证据
    A("## 四、证据完整度")
    A("")
    A("- 八类证据：有 **%d** 类 / 8" % score)
    A("")
    A("| 缺失项 | 缺了会怎样 | 现在怎么补 |")
    A("|---|---|---|")
    if lack:
        for label, impact in lack:
            A("| %s | %s | %s |" % (label, impact, fix_hint(label)))
    else:
        A("| 无 | — | 八类齐全，可直接走书面催告 |")
    A("")

    # 五、逾期与时效
    A("## 五、逾期与时效")
    A("")
    A("| 项 | 日期 | 还剩/已过 |")
    A("|---|---|---|")
    A("| 合同终止（退租交接） | %s | — |" % (end.isoformat() if end else "—"))
    A("| 应退日 | %s（终止日 + %s 天%s） | %s |"
      % (due.isoformat() if due else "—", agree_days,
         "，合同约定" if agree_days != DEFAULT_REFUND_DAYS else "，未约定按 15 天计",
         ("逾期 %d 天" % overdue) if overdue > 0 else "未到期"))
    A("| 今天（基准日） | %s | — |" % base.isoformat())
    if limit_end:
        A("| 时效届满（+3 年） | %s | 还剩 %d 天 |" % (limit_end.isoformat(), left))
    A("")

    # 六、金额
    A("## 六、可主张金额测算")
    A("")
    A("| 项 | 金额 | 说明 |")
    A("|---|---|---|")
    A("| 押金 | %s | 以合同与付款凭证为准 |" % fmt_money(dep))
    A("| − 正当扣款 | %s | 欠租、欠费、故意或重大过失损坏（有凭证） |" % fmt_money(legit))
    if debt:
        A("| − 欠房租/欠费 | %s | 这部分本来就该你结清 |" % fmt_money(debt))
    if interest:
        A("| ＋ 逾期资金占用 | %s | 按 %s%% 年化、逾期 %d 天估算，以认定为准 |"
          % (fmt_money(interest), fmt_money(lpr), overdue))
    A("| **＝ 可主张约** | **%s** | 含争议部分，实际拿回多少看证据与协商 |" % fmt_money(claimable))
    A("")

    # 七、路径
    A("## 七、维权路径")
    A("")
    A("| 步 | 做什么 | 成本 | 留痕要点 |")
    A("|---|---|---|---|")
    A("| ① 协商 | 先电话/当面把逐条讲清 | 最低 | 电话完**立刻发文字复述**让他确认 |")
    A("| ② 书面催告 | 微信 + 短信/邮件各发一份（三段式见下节） | 低 | 截图 + 送达时间 |")
    A("| ③ 投诉/调解 | 12345 / 街道人民调解 / 住建房管（各地口径不同） | 低 | 工单号、调解记录 |")
    if score >= 5:
        A("| ④ 小额诉讼 | 证据 %d/8，先发催告（见⑧）谈不拢再走小额诉讼（标的额小、一审终审） | 诉讼费低，时间成本要算 | 立案回执、证据册 |"
          % score)
    else:
        A("| ④ 小额诉讼 | ⚠️ 证据不足（%d/8），先补证再考虑起诉，否则胜算低 | 诉讼费低 | 先补「入住现状」与「交接确认」 |")
    A("")
    A("顺序的意义：跳步直接起诉往往更费；而协商→催告→投诉每一步都在**固定证据、刷新时效**。")
    A("")

    # 八、话术
    A("## 八、催告话术（三段式，填空即用）")
    A("")
    A("**① 亮事实**：")
    A("")
    A("「%s 我退租交还房屋，双方已交接。按合同，押金 %s 元应于退租后 %s 日内退还。」"
      % (end.isoformat() if end else "X 年 X 月 X 日", fmt_money(dep), agree_days))
    A("")
    A("**② 逐条反驳**（只挑判定为「存疑/不成立」的写，正当的别争）：")
    A("")
    arg_rows = [(r, v) for r, v, _, _, _ in rows_out if v in ("存疑", "不成立")]
    if arg_rows:
        for r, v in arg_rows:
            A("- 「%s」%s 元 —— %s（附入住照片 / 交接视频）"
              % (clean(r["name"]), fmt_money(r["amount"]), v))
    else:
        A("- （暂无可争条目，先把扣款明细逐条填全再发）")
    A("")
    A("**③ 期限与后果**：")
    A("")
    A("「请于本函送达之日起 7 个工作日内将押金余款 %s 元支付至 ____"
      "（逾期资金占用可另行主张，以实际主张为准）；"
      "逾期未付，我保留主张资金占用损失、向住建部门投诉及提起诉讼的权利。」" % fmt_money(remain))
    A("")
    A("要点：字越少越有力量，别上情绪；**金额、期限、后果三样必须齐全**；两个渠道各发一遍互相印证。")
    A("")

    # 九、待办
    A("## 九、待办")
    A("")
    A("| # | 事项 | 时间 | 状态 |")
    A("|---|---|---|---|")
    todo = []
    for label, _ in lack[:3]:
        todo.append(("补证据：%s" % label, "今天/近期"))
    if not rows_out:
        todo.append(("把房东扣的每一笔逐条填进采集表（扣什么/金额/理由）", "催告前"))
    if overdue > 0:
        todo.append(("书面催告（微信 + 短信各一份，三段式）", "3 日内"))
    elif due:
        todo.append(("提前准备催告话术，到期前 7 天发", "%s 前" % due.isoformat()))
    if arg_rows:
        todo.append(("整理可争议 %d 条对应的照片/票据" % len(arg_rows), "催告前"))
    todo.append(("每次沟通后发一条文字复述并要求确认（顺便续时效）", "每次沟通后"))
    if left is not None and left < 365:
        todo.append(("时效仅剩 %d 天，务必先催告中断" % left, "尽快"))
    for i, t in enumerate(todo, 1):
        A("| %d | %s | %s | 待办 |" % (i, t[0], t[1]))
    A("")
    A("---")
    A("")
    A("本核查只做定性判定与金额测算，**不代拟正式法律文书、不承诺结果**；"
      "涉及诉讼请咨询当地律师或法律援助。")
    A("")

    result = {
        "version": VERSION,
        "base_date": base.isoformat(),
        "deposit": dep,
        "deducted": deduct_total,
        "legit": legit,
        "rows": [{"name": r["name"], "amount": r["amount"], "verdict": v,
                  "reason": rs, "ticket": tk} for (r, v, rs, _, tk) in rows_out],
        "refund_due": due.isoformat() if due else None,
        "overdue_days": overdue,
        "claimable": claimable,
        "interest": interest,
        "tickets": {"contract_end": end.isoformat() if end else None,
                    "limit_end": limit_end.isoformat() if limit_end else None,
                    "days_left": left},
        "evidence": {"have": len(have), "total": len(EVIDENCE), "lack": [x[0] for x in lack]},
        "kind": kind_raw,
        "kind_rule": "定金罚则" if is_fine else ("预付款" if is_earnest else "押金/保证金"),
    }
    return "\n".join(L), result


def main():
    ap = argparse.ArgumentParser(description="押金争议核查")
    ap.add_argument("rent", help="租赁信息文本（md/txt）")
    ap.add_argument("--base", default=None, help="基准日 YYYY-MM-DD（默认今天）")
    ap.add_argument("--lpr", default="3.0", help="资金占用参考年利率 %%，默认 3.0（以当期 LPR 为准）")
    ap.add_argument("--out", default=None, help="输出 md 路径")
    ap.add_argument("--json", action="store_true", help="额外输出 json")
    args = ap.parse_args()

    if not os.path.exists(args.rent):
        print("文件不存在：%s" % args.rent)
        print("=EXIT= 2")
        return 2

    base = TODAY
    if args.base:
        base = parse_date(args.base) or TODAY
    try:
        lpr = float(clean(args.lpr) or "3.0")
    except Exception:
        lpr = 3.0

    body, result = build_report(args.rent, base, lpr)
    # 空/不可解析输入：body 为 None，提示串在 result 里 —— 两个都要挡
    if body is None or result is None:
        print(result if result is not None else body)
        print("=EXIT= 2")
        return 2

    out = args.out or (os.path.splitext(args.rent)[0] + "_核查报告.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    if args.json:
        jo = os.path.splitext(args.rent)[0] + "_核查结果.json"
        with open(jo, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("JSON -> %s" % jo)
    print(body)
    print("=EXIT= 0")
    print("OUT=%s | deposit=%s deducted=%s legit=%s overdue=%d claimable=%s evidence=%d/8"
          % (out, fmt_money(result["deposit"]), fmt_money(result["deducted"]),
             fmt_money(result["legit"]), result["overdue_days"],
             fmt_money(result["claimable"]), result["evidence"]["have"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
