#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""费用报销单据核查脚本 v1.0.0

输入：费用报销采集表 markdown
输出：费用四层拆解 / 材料清单核查 / 硬拒情形 / 拒报事由 / 异地备案 / 复核路径 / 催办话术

只做「定性判定 + 算式拆解 + 材料补法 + 路径建议」，
不查政策、不承诺能报、不编造任何城市的起付线/比例/封顶数字。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

VERSION = "1.0.0"
TODAY = date.today()
PLACEHOLDER = ("待填写", "待填", "暂无", "—", "-", "?", "（待补）", "未填", "不涉及", "无", "", "无/无")

DATE_RE = re.compile(r"(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})")
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

# (显示名, 采集表关键词, 缺了会怎样, 现在怎么补)
DOC_ITEMS = [
    ("发票（或电子票据）", ("发票",), "没有发票连报销入口都进不去，基本全退", "医院自助机/掌上医院打印电子票据，收费处补打"),
    ("费用明细清单（已盖章）", ("费用明细清单", "明细清单",), "**最常漏的一项**：只有发票没有盖章清单，无法判定哪些进目录",
     "回住院处/病案室补打并加盖医院章；电子清单要确认有章"),
    ("出院小结 / 出院记录", ("出院小结", "出院记录",), "判断收治是否合规、有没有收治标准依据", "病案室复印带章出院记录"),
    ("诊断证明", ("诊断证明",), "病种与目录、慢特病资格挂钩，缺了连病名都证明不了", "找主治医生开，最好带 ICD 编码"),
    ("病历首页 / 入院记录", ("病历首页", "入院记录",), "争议复核时唯一能还原当时情况的东西", "病案室复印（带封条，别拆）"),
    ("医保卡刷卡记录", ("刷卡记录", "医保卡",), "证明这次发生在定点机构，缺了容易被质疑", "结算单/窗口小票留存；电子凭证有交易记录"),
    ("转诊转院单", ("转诊",), "无转诊→比例下调或直接不能直结", "回原就诊医院医保办补开并说明原因"),
    ("异地就医备案凭证", ("备案",), "没备案就变全额垫付 + 手工报销，时间翻倍", "国家医保服务平台 APP 补备案（急诊可追溯）"),
    ("本人银行卡信息（手工报销用）", ("银行卡",), "手工报销不打款 → 白跑一趟", "窗口登记卡号（本表不填卡号）"),
    ("已医保结算的盖章复印件", ("结算的盖章复印件", "盖章复印件"), "发票原件被医保收走后，商保/单位就报不了",
     "去参保地医保经办机构/医院窗口复印并加盖「已医保结算」章"),
]

# 硬拒情形：只看采集表第四节用户**明确勾选**的项（yes_no 返回 None = 没填，不算命中）。
# 踩过的坑：拿关键词扫全文 → 文档里只要出现「车祸」两个字（哪怕是举例、历史病史）就误判命中。
HARD_DENY = [
    ("第三方责任（车祸 / 打架 / 他人侵权）", ("涉及第三方责任", "第三方责任"),
     "应由责任方或其保险承担，基本医保不予支付",
     "等责任方保险结案后看能否补充；有补充险另说"),
    ("工伤 / 职业病", ("是否工伤",),
     "工伤走工伤保险基金，走基本医保属错渠道，结报后往往要退回",
     "先做工伤认定再按工伤保险报；已按医保结报的要主动问经办机构怎么处理"),
    ("美容整形 / 医美", ("美容整形", "医美"),
     "属消费或非疾病治疗，一般不予支付",
     "病理性/功能性修复（烧伤重建、术后畸形矫正）可争取，改用治疗性材料申报"),
    ("体检 / 预防性项目", ("是否含美容整形", "体检"),
     "非治疗性支出，不走医保",
     "部分城市有公卫专项经费，另找渠道，别在这条上耗"),
    ("境外 / 港澳台就医", ("境外就医", "境外"),
     "一般不符合基本医保支付范围",
     "回内地手工报销通常也不受理工伤以外情形；先问参保地"),
]

# 软性问题：(归类, 理由文本里的关键词, 采集表字段名, 是否反着读, 怎么办)
# 踩过的坑：用泛词扫全文 → 「本人银行卡信息（手工报销用）」这种材料说明会把「已提交手工报销」判成 True。
#         所以字段判定只认**完整字段名**，自由文本才做关键词匹配。
#         invert=True 表示「填『有』反而说明没问题」（如「有没有事前告知签字」填无才是问题）。
SOFT_ISSUES = [
    ("未备案异地就医", ("未备案", "没备案"), None, False, "补备案后走手工报销；比例可能下调"),
    ("无转诊转院单", ("无转诊", "没有转诊"), None, False, "回原医院补开转诊单再报"),
    ("费用清单未盖章 / 发票缺失", ("清单未盖章", "清单没章", "没盖章", "发票丢"), None, False,
     "回医院补打盖章清单、打印电子票据"),
    ("目录外项目未事前告知", ("未告知", "没告知", "不知情"), "事前告知", True,
     "向医院要自费告知签字，并可投诉医院"),
    ("卡 / 参保状态异常", ("断缴", "冻结", "挂失"), "参保状态", False, "先补缴 / 解挂 / 换卡，再重新提交"),
    ("超过手工报销时限", ("超时", "超期", "过期"), "手工报销时限", False, "问能否特批，不承诺能办"),
    ("重复报销同一笔", ("重复报销",), None, False, "发票只能收一次，商保 / 单位只能报差额"),
]


def soft_hit(text, reason_raw, item):
    _cat, keys, field, invert, _action = item
    if has_any(reason_raw, keys):
        return True
    if field:
        v = yes_no(text, (field,))
        if v is None:
            return False
        return (not v) if invert else v
    return False


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
        return round(float(m.group(0)), 2)
    except Exception:
        return None


def parse_pct(tok):
    t = clean(tok).replace("%", "").replace("％", "")
    if is_ph(t):
        return None
    m = NUM_RE.search(t)
    if not m:
        return None
    return round(float(m.group(0)), 2)


def _find_fields(line, labels):
    if "|" not in line:
        return None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 3 and any(k in norm(cc) for cc in cells for k in ("项目", "项", "填什么")):
        return None
    for lab in labels:
        for i, c in enumerate(cells):
            if lab in norm(c) and i + 1 < len(cells):
                return cells[i + 1]
    return None


def pick(text, labels, parser):
    """取第一个能被 parser 解析的候选（表格说明行常排在真实值前面）"""
    for line in text.splitlines():
        if norm(line) in ("", "---"):
            continue
        v = _find_fields(line, labels)
        if v is None:
            continue
        got = parser(v)
        if got is not None:
            return got
    return None


def get_text(text, *labels, **kw):
    """ph_ok=False：连「无」「否」这类占位也要返回（「有没有转诊转院单 | 无」是有意义的结果）"""
    ph_ok = kw.get("ph_ok", True)
    for line in text.splitlines():
        if norm(line) in ("", "---"):
            continue
        v = _find_fields(line, labels)
        if v is None:
            continue
        if ph_ok and is_ph(v):
            continue
        return clean(v)
    return ""


def get_money(text, *labels):
    return pick(text, labels, parse_money)


def get_pct(text, *labels):
    return pick(text, labels, parse_pct)


def get_date(text, *labels):
    return pick(text, labels, parse_date)


def yes_no(text, keys):
    """返回 True/False，没填过（None 候选）返回 None。
    注意：返回 None 而不是 False —— False 会被当成「用户明确说没有」。"""
    for line in text.splitlines():
        if norm(line) in ("", "---"):
            continue
        v = _find_fields(line, keys)
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
    return None


def has_any(text, words):
    n = norm(text)
    return any(w in n for w in words)


def build_report(path, base):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    total = get_money(text, "医疗总费用", "总费用", "发票合计")
    if total is None:
        return None, ("未解析到医疗总费用：请在《费用报销采集表》第一节填「医疗总费用（发票合计）」。"
                      "后面的四层拆解与金额算式都依赖它，个数算不出来报告就废了。")

    base = base or TODAY
    selfpay = get_money(text, "目录外自费", "自费") or 0.0
    pratio = get_pct(text, "先行自付比例", "先行自付") or 0.0
    deductible = get_money(text, "本次起付线", "起付线") or 0.0
    rate = get_pct(text, "报销比例")
    cap = get_money(text, "封顶线", "年度封顶线")
    paid = get_money(text, "已由医保支付", "医保支付") or 0.0
    visit = clean(get_text(text, "就医类型", "本次就医类型") or "住院")

    inner = max(0.0, total - selfpay)
    pre = round(inner * pratio / 100.0, 2)
    base_amt = max(0.0, inner - pre - deductible)
    est = round(base_amt * rate / 100.0, 2) if rate is not None else None
    if est is not None and cap is not None:
        est = round(min(est, max(0.0, cap)), 2)
    gap = round(est - paid, 2) if est is not None else None

    # 材料清单
    have, lack = [], []
    for label, keys, impact, fix in DOC_ITEMS:
        (have if yes_no(text, keys) else lack).append((label, impact, fix))

    # 硬拒只认「用户明确勾了有」；没填就是没填，不猜
    deny_hits = []
    for cat, keys, verdict, action in HARD_DENY:
        if yes_no(text, keys):
            deny_hits.append((cat, verdict, action))

    # 软性问题：自由文本先扫（那栏是用户主动写的），再补第四节勾选
    reason_raw = get_text(text, "被拒的理由", "拒的理由", "不予支付理由")
    soft_hits = []
    for item in SOFT_ISSUES:
        if soft_hit(text, reason_raw, item):
            soft_hits.append((item[0], item[4]))

    distant = clean(get_text(text, "是否异地就医", "异地就医", ph_ok=False))
    filed = clean(get_text(text, "是否已办异地就医备案", "异地就医备案", ph_ok=False))
    transfer = clean(get_text(text, "转诊转院单", "有没有转诊", ph_ok=False))
    direct = yes_no(text, ("是否已直接结算",))
    manual_done = yes_no(text, ("已提交手工报销",))
    notice = yes_no(text, ("不予支付通知书", "通知书"))
    appeal = yes_no(text, ("复核申请", "已提交复核"))
    complaint = yes_no(text, ("投诉医保", "投诉"))

    L = []
    A = L.append
    A("# 费用报销单据核查（本地处理，不上传）")
    A("")
    A("- 基准日：%s ｜ 解析来源：%s" % (base.isoformat(), os.path.basename(path)))
    A("- 本表只做**算式拆解 + 材料核查 + 路径建议**，不查政策、不承诺能报；"
      "起付线/比例/封顶线与材料细节一律以**参保地医保经办机构现行口径**为准。")
    A("")

    # 一、摘要
    A("## 一、结论摘要")
    A("")
    A("- 本次%s：医疗总费用 **%s 元**（其中：目录外自费 %s 元）。"
      % (visit, fmt(total), fmt(selfpay)))
    if est is None:
        A("- ⚠️ **没填「报销比例」**，算不出可报金额；把第一节的比例填上，报告会给出完整算式。")
    else:
        capped = (cap is not None and (est or 0) > cap)
        A("- 按你填的三要素（先行自付 %.0f%%、起付线 %s 元、报销比例 %.0f%%%s）估算可报约 **%s 元**。"
          % (pratio, fmt(deductible), rate,
             "，封顶线剩余 %s 元（%s）" % (fmt(cap), "已按封顶截断" if capped else "未触到封顶")
             if cap is not None else "", fmt(est)))
        if paid:
            if gap >= 0:
                A("- 已由医保支付 %s 元，**按此估算还能再主张约 %s 元**（差多少看复核结论）。"
                  % (fmt(paid), fmt(gap)))
            else:
                A("- 已由医保支付 %s 元，已**高于**此估算值 %s 元 —— 先别高兴，多半是口径不同"
                  "（异地按参保地比例、起付线累计方式、封顶线已用额度），**务必拿结算单逐行对一遍**。"
                  % (fmt(paid), fmt(-gap)))
    if lack:
        A("- 10 项材料拿了 **%d** 项，最要命缺的是：**%s**。"
          % (len(have), lack[0][0]))
    if deny_hits:
        A("- ⚠️ 命中 **%d** 类「政策上多半不该报」的情形：%s。"
          % (len(deny_hits), "、".join(c for c, _, _ in deny_hits)))
    if soft_hits:
        A("- 另有 **%d** 类「手续没跟上」的问题，这类多半能救：%s。"
          % (len(soft_hits), "、".join(c for c, _ in soft_hits)))
    A("")

    # 二、四层
    A("## 二、费用四层拆解")
    A("")
    A("| 层次 | 金额 | 说明 |")
    A("|---|---|---|")
    A("| ① 医疗总费用 | %s | 发票合计 |" % fmt(total))
    A("| ② − 目录外自费 | %s | 不进可报基数 |" % fmt(selfpay))
    A("| ＝ 医保目录内金额 | %s | |" % fmt(inner))
    if pratio:
        A("| ③ − 先行自付（%.0f%%） | %s | 先自己掏一部分，剩下的仍进基数 |" % (pratio, fmt(pre)))
    if deductible:
        A("| ④ − 起付线 | %s | 多数地区**一年内累计**，不是每次重头算 |" % fmt(deductible))
    A("| ＝ 可报基数 | %s | |" % fmt(base_amt))
    if rate is not None:
        A("| ⑤ × 报销比例 %.0f%% | %s | 按医院等级递减；异地直结按**参保地**比例 |" % (rate, fmt(est or 0)))
    if cap is not None:
        A("| ⑥ 年度封顶线（剩余 %s） | %s | %s |"
          % (fmt(cap), fmt(est or 0), "本额未超封顶，不截断" if (est or 0) <= cap else "本额已超封顶，按封顶线截断"))
    if est is not None:
        A("| **＝ 估算可报** | **%s** | 以经办机构核定为准 |" % fmt(est))
    A("")
    A("算式：可报基数 = 总费用 − 目录外自费%s%s；可报 = 可报基数 × 比例%s。"
      % (" − 先行自付" if pratio else "", " − 起付线" if deductible else "", "（再扣封顶线）" if cap is not None else ""))
    A("")

    # 三、材料
    A("## 三、材料清单核查（10 项）")
    A("")
    A("- 拿了 **%d** / 10" % len(have))
    A("")
    A("| # | 材料 | 状态 | 缺了会怎样 | 现在怎么补 |")
    A("|---|---|---|---|---|")
    # 踩坑：have/lack 里存的是 (label, impact, fix) 三元组，
    # 直接 `label in have` 永远 False → 10 项全显示「缺」
    have_labels = set(x[0] for x in have)
    for i, (label, _keys, _impact, fix) in enumerate(DOC_ITEMS, 1):
        got = label in have_labels
        A("| %d | %s | %s | %s | %s |"
          % (i, label, "有" if got else "**缺**", _impact, fix))
    A("")

    # 四、硬拒
    A("## 四、「政策上多半不该报」的硬拒情形")
    A("")
    if deny_hits:
        A("| 情形 | 命中 | 怎么定性 | 下一步 |")
        A("|---|---|---|---|")
        for cat, verdict, action in deny_hits:
            A("| %s | ⚠️ | %s | %s |" % (cat, verdict, action))
    else:
        A("| 情形 | 命中 | 怎么定性 | 下一步 |")
        A("|---|---|---|---|")
        A("| 已逐项核对勾选 | 未命中 | 第三方责任 / 工伤 / 美容整形 / 体检 / 境外 都**填了「无」** | 若实际属其中某项，改填「有」后重跑 |")
    A("")

    # 五、软性
    A("## 五、「手续没跟上」的拒报事由")
    A("")
    if soft_hits:
        A("| # | 事由 | 归类 | 怎么处理 |")
        A("|---|---|---|---|")
        for i, (cat, action) in enumerate(soft_hits, 1):
            A("| %d | %s | 手续问题（多数能救） | %s |" % (i, cat, action))
    else:
        A("| # | 事由 | 归类 | 怎么处理 |")
        A("|---|---|---|---|")
        A("| 1 | 未识别到拒报事由 | — | 把窗口/结算单上写的原话填进采集表第四节，逐条自动归类 |")
    if notice:
        A("")
        A("- 已收到《不予支付通知书》：**务必先要工单/书面编号**，口头答复后面没法复核。")
    if appeal:
        A("- 已提交复核申请：等书面结论，**对结论不服再走行政复议**（当场问清法定期限）。")
    if complaint:
        A("- 已投诉：保留工单号与时间，这是后续行政复议的材料。")
    A("")

    # 六、异地
    A("## 六、异地与备案")
    A("")
    A("| 项 | 填了什么 |")
    A("|---|---|")
    A("| 是否异地就医 | %s |" % (distant or "未填"))
    A("| 是否已办异地备案 | %s |" % (filed or "未填"))
    A("| 转诊转院单 | %s |" % (transfer or "未填"))
    A("| 结算方式 | %s |" % ("已直接结算（刷卡）" if direct else "未直接结算 / 手工报销"))
    if distant and "是" in distant and filed and "是" not in filed:
        A("")
        A("- ⚠️ **异地但没备案** → 基本变成全额垫付再回参保地手工报销，比例还可能下调；"
          "现在补备案（急诊可追溯）比事后硬争划算得多。")
    A("")

    # 七、路径
    A("## 七、复核与申诉路径（按顺序走，别跳步）")
    A("")
    A("| 步 | 做什么 | 这一部的产出 |")
    A("|---|---|---|")
    A("| ① 要书面理由 | 向窗口要《不予支付通知书》或结算单上的书面理由 | 编号 / 工单号 |")
    A("| ② 提交复核 | 参保地医保经办机构窗口或线上提交（材料见《拒报复核与补正清单》） | 受理回执 |")
    A("| ③ 行政救济 | 对复核结论不服 → 行政复议 / 向同级医保主管部门投诉 | 复议受理文书 |")
    A("| ④ 医院违规 | 目录外未告知、过度收费 → 同时向卫健部门 + 医保稽核投诉 | 投诉受理号 |")
    A("| ⑤ 商保/单位 | 凭保险合同主张，不成再协商或诉讼 | — |")
    A("")
    if manual_done and not notice:
        A("- 已提交手工报销但**还没拿到不予支付通知书** → 先要书面理由，没理由就没法复核。")
    if not direct and not manual_done:
        A("- 既没直结也没交手工报销 → 时限风险最高，多数地区手工报销常见 6 个月～1 年窗口，"
          "**以参保地经办机构口径为准**，能交就先交，别等。")
    A("")

    # 八、话术
    A("## 八、催办话术（要编号、要书面、要时限）")
    A("")
    A("「我是 ____（身份证后 6 位），____ 年 ____ 月 ____ 日在 ____ 医院发生 %s 元费用，"
      "医保结算时告知不予支付/未足额支付，理由为「____」。" % fmt(total))
    A("")
    if soft_hits:
        A("「关于本次退回理由（____），我已补齐：%s。请予复核并书面告知核定金额与核定依据；"
          "如仍需补材料，请一次性列全，我当天补齐。」" % "、".join(c for c, _ in soft_hits))
    else:
        A("「请出具书面核定意见，并告知我还需要补哪些材料、补到哪里去、多少个工作日内答复。」")
    A("")
    A("「请于本函送达之日起 5 个工作日内给我**书面复核结论**（含核定额、核定依据、经办人编号）；"
      "逾期未答复，我保留向本级医保主管部门投诉及申请行政复议的权利。」")
    A("")
    A("要点：全程要**编号**——工号、工单号、受理回执号，三样缺一不可；"
      "别在电话里争对错，只问「依据哪条、要哪些材料、几天答复」。")
    A("")

    # 九、待办
    A("## 九、待办")
    A("")
    A("| # | 事项 | 时间 | 状态 |")
    A("|---|---|---|---|")
    todo = []
    for label, _i, _f in lack[:3]:
        todo.append(("补材料：%s" % label, "今天/近期"))
    if not direct and not manual_done:
        todo.append(("确认是否还能手工报销（时限以参保地为准）", "3 日内"))
    if soft_hits:
        todo.append(("把可救的手续逐条补齐（%s）" % "、".join(c for c, _ in soft_hits), "催办前"))
    if deny_hits:
        todo.append(("先确认硬拒情形是否属实（%s）" % "、".join(c for c, _, _ in deny_hits), "催办前"))
    todo.append(("每次沟通要书面理由 + 工号/工单号", "每次沟通后"))
    todo.append(("把发票原件复印并加盖「已医保结算」章（给商保/单位用）", "拿到发票当天"))
    for i, t in enumerate(todo, 1):
        A("| %d | %s | %s | 待办 |" % (i, t[0], t[1]))
    A("")
    A("---")
    A("")
    A("本核查只做算式拆解与材料核查，**不查政策、不承诺能报、不编造任何城市的起付线/比例/封顶数字**；"
      "涉及争议请咨询当地医保经办机构或专业人士。")
    A("")

    result = {
        "version": VERSION,
        "base_date": base.isoformat(),
        "visit": visit,
        "total": total,
        "self_pay": selfpay,
        "inner": inner,
        "pre_ratio": pratio,
        "pre": pre,
        "deductible": deductible,
        "base_amount": base_amt,
        "rate": rate,
        "cap": cap,
        "estimate": est,
        "paid": paid,
        "gap": gap,
        "materials": {"have": len(have), "total": len(DOC_ITEMS), "lack": [x[0] for x in lack]},
        "hard_deny": [c for c, _, _ in deny_hits],
        "soft_issues": [c for c, _ in soft_hits],
        "direct_settled": direct,
        "manual_done": manual_done,
    }
    return "\n".join(L), result


def fmt(v):
    if v is None:
        return "—"
    f = float(v)
    if abs(f - round(f)) < 1e-9:
        return "%d" % round(f)
    return "%.2f" % f


def main():
    ap = argparse.ArgumentParser(description="费用报销单据核查")
    ap.add_argument("rent", help="费用报销采集表（md/txt）")
    ap.add_argument("--base", default=None, help="基准日 YYYY-MM-DD（默认今天）")
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

    body, result = build_report(args.rent, base)
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
    print("OUT=%s | total=%s inner=%s base=%s est=%s paid=%s materials=%d/10 hard=%s soft=%s"
          % (out, fmt(result["total"]), fmt(result["inner"]), fmt(result["base_amount"]),
             fmt(result["estimate"]), fmt(result["paid"]),
             result["materials"]["have"], result["hard_deny"], result["soft_issues"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
