# -*- coding: utf-8 -*-
"""消费者投诉维权路径核查 v1.0.0

输入：按 templates/消费者投诉信息采集表.md 填写的 Markdown
输出：九段式核查报告（或 --json 摘要）

判定纪律：
- 依《消费者权益保护法》等通用规则做路径与金额核对，不替代律师意见
- 不代写诉状、不代发投诉、不预测处理结果
- 用户填什么就用什么，未填的一律标「未填」，不算通过
"""
import argparse
import datetime as dt
import json
import os
import sys

VERSION = "1.0.0"

PLACEHOLDER = (
    "【待填】",
    "待填",
    "填什么",
    "是 / 否",
    "有 / 无",
    "___",
    "xxx",
    "XXX",
)

# 争议类型关键词 -> (规范化名称, 是否建议同步举报)
DISPUTE_KW = (
    ("预付跑路", ("预付", "跑路", "关门", "闭店", "停业")),
    ("虚假宣传", ("虚假宣传", "宣传不符", "夸大", "虚假")),
    ("食品安全", ("食品", "过期", "变质", "异物")),
    ("人身伤害", ("人身伤害", "受伤", "就医", "中毒")),
    ("质量问题", ("质量", "坏了", "故障", "瑕疵", "不能用")),
    ("售后不履行", ("售后", "不发货", "拒绝退", "不予退")),
    ("服务不符", ("服务", "承诺不符", "与承诺不符", "教练")),
    ("价格争议", ("价格", "涨价", "收费")),
)

# 证据项 -> (采集表标签, 是否默认关键)
EVIDENCE_BASE = (
    ("订单或合同凭证", ("订单或合同凭证", "订单凭证"), True),
    ("支付凭证", ("支付凭证",), True),
    ("发票凭证", ("发票凭证",), False),
    ("商品照片或视频", ("商品照片或视频", "商品照片"), True),
    ("快递外包装证据", ("快递外包装证据", "快递外包装"), False),
    ("聊天记录", ("聊天记录",), True),
    ("通话录音", ("通话录音",), False),
    ("检测报告", ("检测报告",), False),
    ("快递单号与签收记录", ("快递单号与签收记录", "签收记录"), False),
    ("宣传页面截图", ("宣传页面截图", "宣传截图"), False),
)


# ---------------------------------------------------------------- 基础工具
def norm(s):
    if s is None:
        return ""
    t = str(s)
    t = t.replace("\u3000", " ").replace(" ", "").replace("\t", "")
    t = t.replace("\uff08", "(").replace("\uff09", ")")
    t = t.replace("\uff0c", ",").replace("\uFFE5", "\u00a5")
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
        if norm(w) in t:
            return True
    if t in ("-", "--", "/", "\u2014", "值"):
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


def iter_pairs(text):
    """yield (label, value)：兼容 | 字段 | 值 | 表格行 与 字段：值 冒号行。"""
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if is_row(s):
            c = split_row(s)
            if len(c) >= 2:
                yield c[0], c[1]
            continue
        if s.startswith("#") or s.startswith("```"):
            continue
        sep = "\uff1a" if "\uff1a" in s else (":" if ":" in s else "")
        if not sep:
            continue
        k, _, v = s.partition(sep)
        k = k.lstrip(">*#-|\t ").strip()
        if not k or not v.strip():
            continue
        yield k, v.strip()


def get_text(text, *labels):
    """最长别名优先，避免短别名抢走长字段。"""
    lbs = sorted([l for l in labels if l], key=lambda x: -len(norm(x)))
    for lb in lbs:
        nl = norm(lb)
        if not nl:
            continue
        for k, v in iter_pairs(text):
            if nl in norm(k) and not is_ph(v):
                return clean(v)
    return ""


def get_num(text, *labels):
    v = get_text(text, *labels)
    if not v:
        return None
    t = norm(v).replace(",", "").replace("\u00a5", "")
    dig = ""
    dot = False
    for ch in t:
        if ch.isdigit():
            dig += ch
        elif ch == "." and dig and not dot:
            dig += ch
            dot = True
        elif dig:
            break
    if not dig:
        return None
    try:
        return float(dig)
    except Exception:
        return None


def yes(text, *labels):
    """三态 + 不适用：True / False / None(未填) / 'NA'"""
    v = get_text(text, *labels)
    if not v:
        return None
    t = norm(v)
    if "不适用" in t or "无平台" in t or "不知道" in t or "不确定" in t:
        return "NA"
    if "否" in t or "无" in t or "没有" in t or "未" in t:
        return False
    if "是" in t or "有" in t or "已" in t:
        return True
    return None


def parse_date(v):
    if not v:
        return None
    t = norm(v)
    for sep in ("-", "/", ".", "\u5e74"):
        t = t.replace(sep, "-")
    t = t.replace("\u6708", "-").replace("\u65e5", "")
    parts = [p for p in t.split("-") if p]
    if len(parts) < 3:
        return None
    try:
        return dt.date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None


def fmt_num(n):
    if n is None:
        return "未填"
    try:
        f = float(n)
    except Exception:
        return str(n)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return ("%.2f" % f).rstrip("0").rstrip(".")


def money(n):
    return "\u00a5" + fmt_num(n)


def fmt_flag(v):
    if v is True:
        return "是"
    if v is False:
        return "**否**"
    if v == "NA":
        return "不适用"
    return "未填"


def have(v):
    if v is True:
        return "有"
    if v is False:
        return "**缺**"
    if v == "NA":
        return "不适用"
    return "未填"


def pick_dispute(text):
    v = get_text(text, "争议类型", "争议简述")
    if not v:
        return "", ""
    hits = []
    for name, kws in DISPUTE_KW:
        for k in kws:
            if k in norm(v):
                hits.append(name)
                break
    seen = []
    for h in hits:
        if h not in seen:
            seen.append(h)
    return (seen[0] if seen else "其他"), v


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


# ---------------------------------------------------------------- 报告
def build_report(path, base=None):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return None, "读不了文件：%s" % e

    if base is None:
        base = dt.date.today()

    name = get_text(text, "消费者姓名", "姓名")
    biz = get_text(text, "经营者名称", "经营者全称")
    biz_type = get_text(text, "经营者类型")
    biz_addr = get_text(text, "经营者实际经营地", "实际经营地")
    has_pf = yes(text, "是否有电商平台", "是否有平台")
    pf_name = get_text(text, "电商平台名称", "平台名称")
    pf_addr = get_text(text, "平台经营者住所地", "平台住所地")

    goods = get_text(text, "商品或服务名称", "商品名称")
    paid = get_num(text, "消费金额", "实付金额")
    pay_way = get_text(text, "支付方式")
    trade_d = parse_date(get_text(text, "交易日期", "下单日期"))
    order_no = get_text(text, "订单号")
    sign_d = parse_date(get_text(text, "签收日期"))
    has_order = yes(text, "是否有订单或合同")
    has_invoice = yes(text, "是否开具发票")
    is_food = yes(text, "是否属于食品")

    disp, disp_raw = pick_dispute(text)
    disp_raw = get_text(text, "争议简述") or disp_raw or ""
    found_d = parse_date(get_text(text, "争议发现日期", "发现问题日期"))
    talked = yes(text, "是否已与商家协商")
    talked_doc = yes(text, "协商是否有书面记录")
    talk_res = get_text(text, "协商结果")
    pf_in = yes(text, "是否已申请平台介入")
    pf_res = get_text(text, "平台处理结果")
    to_12315 = yes(text, "是否已向12315投诉", "是否已投诉")
    st_12315 = get_text(text, "12315受理情况", "受理情况")
    reported = yes(text, "是否另行举报")
    injury = yes(text, "是否造成人身伤害")
    loss = get_num(text, "已发生损失金额", "损失金额")

    want = get_text(text, "主要诉求")
    claim_fraud = yes(text, "是否主张欺诈")
    claim_food = yes(text, "是否主张不符合食品安全标准")
    self_amt = get_num(text, "自行测算的诉求金额", "诉求金额")
    over7 = yes(text, "是否已过七天无理由期", "七天无理由")
    urged = yes(text, "是否已自行发过书面催告", "书面催告")
    extra = get_text(text, "补充说明")

    # ---- 关键信息校验
    if not disp and not goods:
        return None, ("未解析到关键信息。至少填写「争议类型」或「商品或服务名称」中的一项，"
                      "否则无法判断维权路径。")
    if paid is None:
        return None, ("未解析到「消费金额（元）」。金额是路径选择与诉求测算的前提，"
                      "请填写后重跑。")

    L = []
    A = L.append

    # ---- 证据
    need_extra = set()
    if disp == "虚假宣传":
        need_extra.update(["宣传页面截图", "检测报告"])
    if disp == "食品安全":
        need_extra.add("检测报告")
    if disp == "人身伤害":
        need_extra.add("检测报告")
    if claim_fraud is True:
        need_extra.add("宣传页面截图")
    if has_pf is True:
        need_extra.update(["快递外包装证据", "快递单号与签收记录"])
    if talked is True:
        need_extra.add("聊天记录")

    ev_rows = []
    gaps = []
    for title, labels, key in EVIDENCE_BASE:
        v = yes(text, *labels)
        is_key = key or (title in need_extra)
        ev_rows.append((title, have(v), "关键" if is_key else "加分项"))
        if v is False and is_key:
            gaps.append(title)
        elif v is None and is_key:
            gaps.append(title + "（未填，按缺计）")
    if talked is True and talked_doc is False:
        gaps.append("协商书面记录")

    # ---- 路径
    steps = []
    steps.append(("第 1 步", "商家 / 客服书面交涉", talked,
                  "平台站内文字、微信或短信，写明事实—依据—诉求—期限"))
    if has_pf is True or pf_name:
        steps.append(("第 2 步", "电商平台介入（%s）" % (pf_name or "平台"), pf_in,
                      "订单页「申请售后 / 投诉商家 / 平台介入」，附图片与聊天截图"))
    else:
        steps.append(("第 2 步", "电商平台介入", "NA", "本次无平台，本步不适用"))
    steps.append(("第 3 步", "12315 / 消费者协会", to_12315,
                  "拨打 12315 或用全国 12315 平台网站 / 小程序提交，附证据清单"))
    steps.append(("第 4 步", "行政投诉举报（违法线索）", reported,
                  "向市场监管部门提交举报材料，与投诉并行"))
    steps.append(("第 5 步", "小额诉讼 / 仲裁", None,
                  "被告住所地或合同履行地基层法院，走小额诉讼程序"))

    cur = ""
    for s in steps:
        if s[2] is False or s[2] is None:
            if s[2] == "NA":
                continue
            cur = "%s（%s）" % (s[0], s[1])
            break
    if not cur:
        cur = "第 5 步（小额诉讼 / 仲裁）"

    # ---- 时效
    limits = []
    if sign_d:
        d7 = sign_d + dt.timedelta(days=7)
        left7 = (d7 - base).days
        if left7 >= 0:
            limits.append(("七天无理由退货", "签收日 %s + 7 日 = %s" % (sign_d, d7),
                           "还剩 %d 天" % left7))
        else:
            limits.append(("七天无理由退货", "签收日 %s + 7 日 = %s" % (sign_d, d7),
                           "**已过 %d 天**" % (-left7)))
    if found_d:
        exp = add_years(found_d, 3)
        left = (exp - base).days
        elapsed = (base - found_d).days
        limits.append(("诉讼时效 3 年", "争议发现日 %s + 3 年 = %s" % (found_d, exp),
                       ("还剩 %d 天" % left) if left > 0 else "**已过 %d 天**" % (-left)))
        limits.append(("争议发生至今", "%s → %s" % (found_d, base),
                       "已 %d 天" % max(elapsed, 0)))
    if trade_d:
        limits.append(("交易至今", "%s → %s" % (trade_d, base),
                       "已 %d 天" % max((base - trade_d).days, 0)))
    limits.append(("12315 决定是否受理", "自提交之日起", "7 日内"))
    limits.append(("12315 办结", "自受理之日起", "60 日内，可延长 30 日"))

    overdue = False
    if found_d:
        exp = add_years(found_d, 3)
        if (exp - base).days <= 0 and urged is not True:
            overdue = True

    # ---- 金额测算
    refund = paid
    tri = None
    food_amt = None
    if claim_fraud is True:
        tri = paid * 3
        if tri < 500:
            tri = 500.0
    if claim_food is True:
        a = paid * 10
        b = (loss or 0) * 3
        food_amt = max(a, b)
        if food_amt < 1000:
            food_amt = 1000.0
    punish = None
    if tri is not None and food_amt is not None:
        punish = max(tri, food_amt)
    elif tri is not None:
        punish = tri
    elif food_amt is not None:
        punish = food_amt
    total = refund + (punish or 0) + (loss or 0)

    # ---- 风险项
    risks = []
    if overdue:
        risks.append("诉讼时效可能已届满，且未见中断事由")
    if len(gaps) >= 3:
        risks.append("关键证据缺口 %d 项，投诉易被退回" % len(gaps))
    elif gaps:
        risks.append("证据缺 %s" % "、".join(gaps))
    if claim_fraud is True and ("宣传页面截图" in "".join(gaps) or "检测报告" in "".join(gaps)):
        risks.append("主张欺诈但缺少宣传截图或检测报告，三倍赔偿举证不足")
    if talked is False and (to_12315 is True or reported is True):
        risks.append("未与商家协商即越级投诉，调解成功率下降")
    if talked is True and talked_doc is False:
        risks.append("与商家沟通过但无书面记录，等于没沟通过")
    if has_pf is True and pf_in is False and to_12315 is False:
        risks.append("有平台但未申请平台介入，跳步会拖长周期")
    if over7 is True and disp in ("质量问题", "虚假宣传", "服务不符"):
        risks.append("已过七天无理由期，需改按质量问题或与约定不符主张")
    if pay_way and ("分期" in norm(pay_way) or "贷" in norm(pay_way)):
        risks.append("采用分期贷付款，商家违约不当然免除还款义务，需单独处理")
    if biz and not biz_addr:
        risks.append("未填经营者实际经营地，管辖部门无法确定")
    if "最终解释权" in norm(text) or "概不退" in norm(text):
        risks.append("对方以「最终解释权归本店 / 概不退费」拒退——该类格式条款无效，不能据此免责")
    if not risks:
        risks.append("未发现明显风险（未填的不算通过）")

    # ---- 结论四态
    if overdue:
        concl = "不通过"
    elif paid is None or not disp:
        concl = "待补正"
    elif len(gaps) >= 3 or (claim_fraud is True and "宣传页面截图" in "".join(gaps)):
        concl = "有风险"
    elif gaps:
        concl = "有风险"
    else:
        concl = "通过"

    # ---------------- 输出
    A("# 消费者投诉维权路径核查报告")
    A("")
    A("> 生成日期：%s；脚本版本 v%s" % (base.isoformat(), VERSION))
    A("")

    A("## 一、结论摘要")
    A("")
    A("- 综合结论：**%s**" % concl)
    A("- 当前应先走：%s" % cur)
    if disp:
        A("- 争议类型：**%s**" % disp)
    A("- 交易标的：%s，实付 %s，交易日期 %s" % (
        goods or "未填", money(paid), trade_d.isoformat() if trade_d else "未填"))
    A("- 诉求测算合计：%s（算式见第六段）" % money(total))
    A("- 风险 %d 项：%s" % (len(risks), "；".join(risks)))
    A("- **未填的一律不算通过**，只按你填了的判断——补填后重跑一次。")
    A("")

    A("## 二、维权路径排序（第几步找谁）")
    A("")
    A("| 顺序 | 找谁 | 是否已走 | 怎么提 |")
    A("|---|---|---|---|")
    for s in steps:
        A("| %s | %s | %s | %s |" % (s[0], s[1], fmt_flag(s[2]), s[3]))
    A("")
    A("升级判据：对方**不回应 / 明确拒绝 / 超时未办结 / 方案低于法定标准** → 立刻升一级，"
      "不要在同一级反复拉扯。")
    A("")

    A("## 三、投诉与举报定性")
    A("")
    A("| 维度 | 投诉 | 举报 |")
    A("|---|---|---|")
    A("| 性质 | 消费争议，解决你和商家之间的事 | 违法线索，要求查处违法行为 |")
    A("| 结果 | 组织调解，促成退赔 | 立案查处，作出行政处罚 |")
    A("| 能不能拿回钱 | 能 | **不能**，不解决个人退赔 |")
    A("| 期限 | 7 日内决定是否受理，60 日内办结（可延 30 日） | 按行政执法程序办理 |")
    A("")
    if disp in ("虚假宣传", "食品安全", "预付跑路"):
        A("本次争议类型为**%s**，属于同时含违法线索的情形：**建议投诉与举报并行**，"
          "投诉书里写诉求与金额，举报信里写违法事实与证据。" % disp)
    else:
        A("本次争议类型为**%s**，以**投诉**为主：投诉书里必须写清具体诉求与金额；"
          "若另有违法线索（无证经营、假冒伪劣等），可另行举报。" % (disp or "未填"))
    A("")
    A("已提投诉：%s；已另行举报：%s。12315 受理情况：%s" % (
        fmt_flag(to_12315), fmt_flag(reported), st_12315 or "未填"))
    A("")

    A("## 四、管辖与受理口径")
    A("")
    A("| 项 | 情况 |")
    A("|---|---|")
    A("| 经营者 | %s |" % (biz or "未填"))
    A("| 经营者类型 | %s |" % (biz_type or "未填"))
    A("| 实际经营地 | %s |" % (biz_addr or "未填"))
    A("| 平台 | %s |" % ((pf_name or "有平台未填名称") if has_pf is True else
                        ("无平台" if has_pf is False else "未填")))
    A("| 平台住所地 | %s |" % (pf_addr or "未填"))
    A("")
    if has_pf is True:
        A("- 网络交易：可向**平台住所地**或**经营者所在地**县级以上市场监管部门提出；"
          "优先用平台投诉入口留痕。")
    else:
        A("- 一般：向**经营者实际经营地**县级以上市场监管部门提出；12315 会自动分流转办。")
    if disp == "预付跑路":
        A("- 预付式消费：除市场监管外，可同时向**商务主管部门**（单用途商业预付卡主管部门）反映。")
    if disp == "食品安全" or is_food is True:
        A("- 食品类：向市场监管部门投诉举报；涉身体不适的同步保留就医记录。")
    if disp == "虚假宣传":
        A("- 虚假宣传 / 违法广告：向市场监管部门广告监管条线举报。")
    if "最终解释权" in norm(text) or "概不退" in norm(text):
        A("- 对方若以「最终解释权归本店」「概不退费」等条款拒退：经营者以格式条款作出排除或者"
          "限制消费者权利、减轻或者免除经营者责任、加重消费者责任等对消费者不公平、不合理的"
          "规定，**该条款无效**，不能作为拒绝退赔的依据。")
    A("- 各地 12315 分流规则与平台规则存在差异，**以当地市场监管部门与平台最新口径为准**；"
      "查询入口：全国 12315 平台网站、12315 微信小程序、当地市场监管局官网或公众号。")
    A("")

    A("## 五、证据清单与缺口")
    A("")
    A("| 证据 | 持有情况 | 重要性 |")
    A("|---|---|---|")
    for t_, h_, k_ in ev_rows:
        A("| %s | %s | %s |" % (t_, h_, k_))
    A("")
    if gaps:
        A("- **缺口 %d 项**：%s" % (len(gaps), "、".join(gaps)))
        A("- 补证优先级：先补「订单或合同凭证」「支付凭证」「商品照片或视频」，"
          "这三项缺一样就可能被退回。")
        if "宣传页面截图" in "".join(gaps):
            A("- ⚠️ 宣传页面截图下架即灭失，虚假宣传最难补的就是这一项，"
              "立刻去平台快照、缓存或他人转发里找。")
        if "检测报告" in "".join(gaps) and disp in ("食品安全", "虚假宣传"):
            A("- ⚠️ 缺少检测报告：需找有资质的第三方机构出具，否则十倍赔偿或欺诈难以成立。")
    else:
        A("- 已填项未见关键缺口（未填的不算通过）。")
    A("")

    A("## 六、诉求金额测算")
    A("")
    A("```")
    A("实付金额（退款基数）          = %s" % money(paid))
    if claim_fraud is True:
        A("三倍赔偿                    = %s x 3 = %s%s" % (
            money(paid), money(paid * 3),
            "  → 不足 500 元，按 500 元保底" if paid * 3 < 500 else ""))
    if claim_food is True:
        A("食品十倍 / 损失三倍（择高）  = max(%s x 10, %s x 3) = %s%s" % (
            money(paid), money(loss or 0), money(max(paid * 10, (loss or 0) * 3)),
            "  → 不足 1000 元，按 1000 元保底" if max(paid * 10, (loss or 0) * 3) < 1000 else ""))
    A("实际损失（凭票据）            = %s" % money(loss or 0))
    A("------------------------------------------")
    A("诉求合计                      = 退款 + 惩罚性赔偿 + 实际损失 = %s" % money(total))
    A("```")
    A("")
    if claim_fraud is True and claim_food is True:
        A("注意：三倍赔偿与食品十倍赔偿**不能叠加**，脚本已按择高取 %s。" % money(punish))
    if claim_fraud is not True and claim_food is not True:
        A("未勾选欺诈或不符合食品安全标准：按**退货退款 / 修理更换 + 实际损失**主张，"
          "惩罚性赔偿需要另行举证欺诈行为或食品不符合安全标准。")
    if injury is True and not loss:
        A("勾选了人身伤害但未填已发生损失金额：医疗费、护理费、交通费、误工费需凭票据另行举证。")
    if self_amt is not None:
        A("自行测算金额 %s，脚本测算 %s%s。" % (
            money(self_amt), money(total),
            "，两者一致" if abs(self_amt - total) < 1 else "，**存在差异，请核对算式**"))
    A("")

    A("## 七、时效与期限倒计时")
    A("")
    A("| 期限 | 起算与到期 | 状态 |")
    A("|---|---|---|")
    for a_, b_, c_ in limits:
        A("| %s | %s | %s |" % (a_, b_, c_))
    A("")
    if overdue:
        A("- ⚠️ 自争议发现日起算的 3 年诉讼时效**可能已届满**且未见中断事由："
          "尽快发出书面催告并保留送达证据（可中断时效），必要时咨询律师。")
    if over7 is True and disp in ("质量问题", "虚假宣传", "服务不符"):
        A("- 七天无理由期已过，但质量问题、与约定不符的主张**不受 7 日限制**，改走这条。")
    A("- 12315 自提交之日起 7 日内决定是否受理，受理后 60 日内办结，复杂情况可延长 30 日。")
    A("")

    A("## 八、话术模板（可直接复制）")
    A("")
    A("```")
    A("【关于%s的投诉】" % (goods or "本次消费"))
    A("")
    A("一、事实")
    A("本人于 %s 通过 %s 向 %s 购买 %s，订单号 %s，实付 %s（付款方式：%s），于 %s 收到。" % (
        trade_d.isoformat() if trade_d else "【交易日期】",
        pf_name or "【平台/门店】", biz or "【经营者全称】", goods or "【商品名称】",
        order_no or "【订单号】", money(paid), pay_way or "【支付方式】",
        sign_d.isoformat() if sign_d else "【签收日期】"))
    _dr = (disp_raw or "【客观描述，不写情绪，不写形容词】").rstrip("。. ")
    A("收货后发现：%s。" % _dr)
    A("本人于【首次沟通日期】通过【渠道】向商家提出【诉求】，对方【回复或拒不回复】。")
    A("")
    A("二、依据")
    A("1. 经营者提供的商品与宣传或约定不符，属于未按约定提供商品；")
    A("2. 经营者以格式条款作出排除或限制消费者权利、减轻或免除自身责任的规定，该条款无效；")
    A("3. 经营者有欺诈行为的，消费者有权要求退还价款并增加赔偿其受到的损失。")
    A("")
    A("三、诉求")
    A("1. 退还货款 %s；" % money(refund))
    if punish:
        A("2. 支付增加赔偿金 %s；" % money(punish))
        A("3. 合计 %s。" % money(total))
    else:
        A("2. 承担修理 / 更换及由此产生的必要费用；")
        A("3. 合计 %s（含实际损失）。" % money(total))
    A("")
    A("四、期限")
    A("请于收到本函之日起 7 日内，将款项支付至本人原支付账户，或通过上述联系方式给出书面方案。")
    A("逾期未答复的，本人将向 12315 及经营者所在地市场监管部门投诉，并依法提起诉讼。")
    A("")
    A("五、证据清单（随附）")
    _n = 0
    for t_, h_, k_ in ev_rows:
        if h_ == "有":
            _n += 1
            A("%d. %s" % (_n, t_))
    if not _n:
        A("（暂未持有任何证据，先按第五段补齐）")
    A("```")
    A("")
    A("电话沟通三条纪律：开场先问对方单位与工号；要求把口头方案用文字重发一遍；"
      "挂电话后立刻发文字复述并留原始录音。")
    A("")

    A("## 九、待办补正动作与纪律")
    A("")
    todo = []
    for g in gaps:
        todo.append("补齐证据「%s」" % g)
    if talked is False:
        todo.append("先向商家发起**书面**交涉（站内文字或微信），写明事实—依据—诉求—期限，保留截图")
    if talked is True and talked_doc is False:
        todo.append("把已发生的口头沟通补成文字：向商家发一条复述消息要求确认")
    if has_pf is True and pf_in is False:
        todo.append("在 %s 订单页发起「申请售后 / 平台介入」，并保存平台回复" % (pf_name or "平台"))
    if to_12315 is False:
        todo.append("向 12315（全国 12315 平台网站或小程序）提交投诉，被投诉人写营业执照全称与实际经营地")
    if disp in ("虚假宣传", "食品安全", "预付跑路") and reported is False:
        todo.append("同步提交举报材料（违法事实 + 证据），举报不解决退赔，需与投诉并行")
    if disp == "预付跑路":
        todo.append("同时向商务主管部门反映单用途商业预付卡问题")
    if not biz:
        todo.append("查明经营者营业执照全称与实际经营地（平台店铺资质页或国家企业信用信息公示系统）")
    if not biz_addr:
        todo.append("补填经营者实际经营地，确定管辖部门")
    if overdue:
        todo.append("立即发出书面催告并保留送达证据以中断诉讼时效，必要时咨询律师")
    if claim_fraud is True:
        todo.append("为欺诈主张补强：宣传页截图（带 URL 与时间）+ 第三方检测报告对照")
    if pay_way and ("分期" in norm(pay_way) or "贷" in norm(pay_way)):
        todo.append("单独处理分期贷：与贷款机构沟通停贷或展期，避免逾期影响征信")
    todo.append("按时间轴整理材料：下单→付款→收货→发现问题→沟通→平台→投诉，缺一环补一环")
    todo.append("所有交涉均留痕：文字优先，通话录音保存原始文件，截图用原图")
    for i, t in enumerate(todo, 1):
        A("%d. %s" % (i, t))
    A("")
    A("**边界与纪律**")
    A("")
    A("- 依《中华人民共和国消费者权益保护法》等**通用规则**整理，**不替代律师意见**；")
    A("- 不代写诉状、不代发投诉、不预测处理结果；")
    A("- 12315 受理范围、各地消协流程、平台规则以**当地主管部门与平台最新口径为准**；")
    A("- 跨境购、金融理财、医疗纠纷、商品房买卖、劳动争议等特殊领域不适用本路径；")
    A("- 本结果依通用规则整理，不替代专业意见，最终以主管部门或司法机关认定为准。")
    A("")

    body = "\n".join(L)
    meta = {
        "版本": VERSION,
        "结论": concl,
        "争议类型": disp or "未填",
        "当前步骤": cur,
        "实付金额": paid,
        "诉求合计": total,
        "惩罚性赔偿": punish,
        "实际损失": loss,
        "证据缺口": gaps,
        "风险项": risks,
        "待办": todo,
        "诉讼时效是否届满": overdue,
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
        print(meta if isinstance(meta, str) else "未能生成报告")
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                f.write(str(meta))
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
