# -*- coding: utf-8 -*-
"""车险投保与理赔核查 v1.0.0

输入：按 templates/车险信息采集表.md 填写的 Markdown
输出：九段式核查报告（或 --json 摘要）

判定纪律：
- 不内置保费率、不推荐保险公司、不估算精确保费
- 次年涨费只有在用户填了「上年商业险保费」时才估算，且明确标注假设系数
- 用户填什么就用什么，不补、不猜
"""
import argparse
import datetime as dt
import json
import os
import sys

VERSION = "1.0.0"

PLACEHOLDER = (
    "【待填】",
    "填什么",
    "是 / 否",
    "有 / 无",
    "___",
)


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
        if norm(w) in t:
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


def get_text(text, *labels):
    for line in text.splitlines():
        if not is_row(line):
            continue
        c = split_row(line)
        if len(c) < 2:
            continue
        for lb in labels:
            # label 也要 norm：norm 会吃掉空格，「是否超 48 小时」不带空格匹配不上
            if norm(lb) in norm(c[0]) and not is_ph(c[1]):
                return clean(c[1])
    return ""


def has_material(text, label):
    """材料是否已备齐：看该行的值，不是看标签出现在哪。"""
    for line in text.splitlines():
        if not is_row(line):
            continue
        c = split_row(line)
        if len(c) < 2:
            continue
        if norm(label) in norm(c[0]):
            v = norm(c[1])
            if is_ph(c[1]):
                return False
            return "有" in v and "无" not in v
    return False


def get_text_multi(text, *labels):
    out = []
    for line in text.splitlines():
        if not is_row(line):
            continue
        c = split_row(line)
        if len(c) < 2:
            continue
        for lb in labels:
            if lb in norm(c[0]) and not is_ph(c[1]):
                out.append(clean(c[1]))
                break
    return out


def get_int(text, *labels):
    v = get_text(text, *labels)
    if not v:
        return None
    dig = ""
    for ch in norm(v):
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


def get_money(text, *labels):
    return get_int(text, *labels)


def yes(text, *labels):
    v = get_text(text, *labels)
    if not v:
        return None
    t = norm(v)
    if "否" in t or "无" in t or "没" in t:
        return False
    if "是" in t or "有" in t:
        return True
    return None


def parse_date(v):
    if not v:
        return None
    t = norm(v)
    parts = t.replace("/", "-").replace(".", "-").split("-")
    try:
        if len(parts) >= 3:
            return dt.date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts) == 2:
            return dt.date(int(parts[0]), int(parts[1]), 1)
    except Exception:
        return None
    return None


# ---------------------------------------------------------------- 规则表
# (键, 命中值集合, 后果, 怎么办)
DENY_RULES = [
    ("酒驾 / 醉驾 / 毒驾", ("是", "酒驾", "醉驾", "毒驾"),
     "商业险拒赔；交强险限额内垫付后可向致害人追偿",
     "这是刑事与行政问题，先配合处理，别指望保险兜底"),
    ("驾驶证无效 / 吊销暂扣期间", ("无效", "吊销", "暂扣", "无证"),
     "商业险可拒赔",
     "先确认驾驶证状态；被冒用的要举证"),
    ("曾离开现场 / 逃逸嫌疑", ("离开现场", "逃逸"),
     "商业险可拒赔，且可能认定为逃逸",
     "主动回现场或投案，固定「不知情」的证据"),
    ("实际从事营运却按非营运投保", ("网约车", "营运"),
     "改变使用性质未告知，商业险可拒赔——近年高发",
     "如实告知保险公司并变更使用性质，补缴保费差额"),
    ("改装未告知", ("未告知",),
     "增加危险程度未告知的，可拒赔",
     "主动补充告知，看保险公司是否加费承保"),
]

COVER_ITEMS = [
    ("交强险", "交强险是否投保",
     "不买不能上路、不能年检；扣车并处应缴保费 2 倍罚款；脱保期间事故全自担",
     "立即投保，到期前 30 天续"),
    ("机动车损失险", "是否投保车损险",
     "自己的车撞坏了全自费；改革后已含盗抢、涉水、自燃、玻璃、不计免赔",
     "车龄不长、价值较高或贷款车建议投保"),
    ("第三者责任险", "是否投保第三者责任险",
     "超出交强险的第三方损失没人赔，撞人撞豪车可致大额自付",
     "必买，额度 100 万起，建议 200 万以上"),
    ("车上人员责任险", "是否投保座位险",
     "司机与乘客伤亡无保障",
     "常载人的建议投保，或用意外险替代"),
    ("医保外用药责任险", "是否投保医保外用药责任险",
     "三者险不赔医保目录外用药，人伤事故缺口大",
     "保费很低，强烈建议加"),
]

CLAIM_DOCS = [
    ("保险单（电子保单）", "必备", "保险公司 App 或邮箱里找"),
    ("事故认定书", "有责无责与责任比例的依据", "找处理事故的交警中队补开"),
    ("现场照片 / 记录仪视频", "定责与定损的关键证据", "记录仪立刻导出，别被覆盖"),
    ("修车发票与维修清单", "赔款核算依据，抬头要对", "修理厂补开，先定损后修车"),
    ("对方信息与损失凭证", "第三方索赔依据", "交警处可调取对方信息"),
    ("人伤医疗票据", "医疗费、误工费核算依据", "医院补打票据与诊断证明"),
]


def build_report(path, base=None, ncd=25):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return None, "读不了文件：%s" % e

    if base is None:
        base = dt.date.today()
    L = []
    A = L.append

    model = get_text(text, "车型")
    reg_year = get_int(text, "初次登记年份", "初次登记")
    usage = get_text(text, "车辆使用性质", "使用性质")
    modified = get_text(text, "是否有改装", "改装")
    loan = yes(text, "是否贷款车", "贷款车")

    comp = yes(text, "交强险是否投保", "交强险")
    comp_due = parse_date(get_text(text, "交强险到期日"))
    own = yes(text, "是否投保车损险", "车损险")
    third = yes(text, "是否投保第三者责任险", "第三者责任险")
    third_amt = get_int(text, "三者险保额", "三者险")
    seat = yes(text, "是否投保座位险", "座位险")
    out_med = yes(text, "医保外用药", "医保外")
    last_fee = get_money(text, "上年商业险保费", "上年保费")
    this_fee = get_money(text, "今年报价", "今年")
    no_claim = get_int(text, "连续未出险年数", "未出险")
    transfer = yes(text, "是否过户", "过户")
    lapsed = yes(text, "是否曾脱保", "脱保")

    acc_date = get_text(text, "事故日期")
    injury = yes(text, "是否有人伤", "人伤")
    liable = yes(text, "交警是否已定责", "已定责")
    duty = get_text(text, "我方责任比例", "责任比例")
    repair = get_money(text, "预估维修费", "维修费")
    other_pay = get_text(text, "对方是否配合赔付", "对方是否配合")
    reported = yes(text, "是否已报案", "已报案")
    over48 = yes(text, "是否超 48 小时", "48 小时")

    drunk = get_text(text, "酒驾", "醉驾", "毒驾")
    lic = get_text(text, "驾驶证是否有效")
    left = get_text(text, "是否曾离开现场", "离开现场")
    run_biz = get_text(text, "是否实际从事营运", "营运")
    yearly_ok = get_text(text, "是否按期年检", "年检")
    mod_told = get_text(text, "改装是否告知", "改装")

    def got(label):
        return has_material(text, label.split("（")[0])

    if not any([model, usage, comp is not None, third is not None, repair]):
        return None, ("未解析到关键信息。至少填写「车型 / 车辆使用性质 / 交强险是否投保 / "
                      "是否投保第三者责任险」中的一项，否则无法判断。")

    # ---- 保障缺口
    gaps = []
    for name, key, risk, fix in COVER_ITEMS:
        st = None
        if key == "交强险是否投保":
            st = comp
        elif key == "是否投保车损险":
            st = own
        elif key == "是否投保第三者责任险":
            st = third
        elif key == "是否投保座位险":
            st = seat
        elif key == "是否投保医保外用药责任险":
            st = out_med
        if st is False or (st is None and name in ("交强险", "第三者责任险")):
            gaps.append((name, "**缺**", risk, fix))
        elif st is True and name == "第三者责任险" and third_amt is not None and third_amt < 100:
            gaps.append((name, "有（%d 万）" % third_amt,
                         "额度偏低：死亡伤残与豪车维修都可能远超 %d 万" % third_amt,
                         "提到 200 万以上，保费通常只多几十元"))
        elif st is True:
            gaps.append((name, "有", "无明显缺口", "—"))
        else:
            gaps.append((name, "未填", "填了才能判断", "—"))
    if comp_due:
        days = (comp_due - base).days
        if days < 0:
            gaps.append(("交强险到期", "**已过期 %d 天**" % (-days),
                         "脱保期间事故全自担，上路可被扣车并处罚款",
                         "立即续保，脱保超 3 个月 NCD 折扣清零"))
        elif days <= 30:
            gaps.append(("交强险到期", "%s（还有 %d 天）" % (comp_due.isoformat(), days),
                         "快到期，别拖到最后一天",
                         "现在就续，到期前 30 天可办"))

    # ---- 保费与 NCD
    fee_lines = []
    delta = None
    if last_fee and this_fee:
        delta = this_fee - last_fee
    if no_claim is not None and no_claim >= 3 and transfer:
        fee_lines.append("连续未出险 %d 年，但**车辆已过户**——NCD 不继承，过户后按新投保，折扣归零。" % no_claim)
    if lapsed:
        fee_lines.append("曾有脱保记录：脱保超 3 个月会中断连续投保记录，NCD 折扣清零。")
    if no_claim is not None and no_claim >= 3 and not transfer and not lapsed:
        fee_lines.append("连续未出险 %d 年，NCD 处于较好档位——"
                         "报一次险会打破折扣，第四节有算账。" % no_claim)
    if delta is not None:
        fee_lines.append("今年报价比去年%s %d 元%s。" % (
            "高" if delta > 0 else "低", abs(delta),
            "（去年 %d → 今年 %d）" % (last_fee, this_fee)))
    if last_fee and not this_fee:
        fee_lines.append("只填了去年保费（%d 元），没填今年报价，无法比较涨跌。" % last_fee)
    if not fee_lines:
        fee_lines.append("未填保费信息，无法比较。填「上年商业险保费」与「今年报价」后重跑。")

    # ---- 报不报保险
    claim_calc = None
    if repair is not None and last_fee:
        up = int(last_fee * ncd / 100)
        claim_calc = (repair, up, ncd)
    advice = ""
    if injury:
        advice = "有人伤一律报保险并报警，不要私了——伤情变化后无法再索赔。"
    elif claim_calc:
        repair_v, up_v, _ = claim_calc
        if repair_v > up_v:
            advice = ("维修费 %d 元 > 次年可能上涨约 %d 元，报保险更划算。"
                      % (repair_v, up_v))
        else:
            advice = ("维修费 %d 元 < 次年可能上涨约 %d 元，自费更划算——"
                      "一次出险会打破连续未出险折扣，恢复要好几年。" % (repair_v, up_v))
    elif repair is not None:
        advice = ("维修费 %d 元。没填上年商业险保费，算不出次年涨幅——"
                  "补上「上年商业险保费」后重跑，或打电话问业务员明年涨多少。" % repair)
    else:
        advice = "没填事故与维修费信息，本段跳过。"

    # ---- 拒赔风险
    denies = []
    checks = [
        ("酒驾 / 醉驾 / 毒驾", drunk, ("是", "酒驾", "醉驾", "毒驾")),
        ("驾驶证无效", lic, ("否", "无效", "吊销", "暂扣")),
        ("曾离开现场", left, ("是", "离开")),
        ("实际从事营运", run_biz, ("是", "网约车", "营运")),
        ("改装未告知", mod_told, ("未告知",)),
    ]
    for name, val, hits in checks:
        if not val:
            continue
        t = norm(val)
        if any(h in t for h in hits):
            for dn, _, cons, fix in DENY_RULES:
                if dn.startswith(name[:4]):
                    denies.append((dn, cons, fix))
                    break
            else:
                denies.append((name, "属于常见拒赔情形", "如实告知保险公司，别隐瞒"))
    if yearly_ok and "否" in norm(yearly_ok):
        denies.append(("车辆未按期年检",
                       "存在争议：改革后条款多数不再直接免责，但因车辆本身故障导致的事故仍可能拒赔",
                       "补办年检，并核对该事故与车辆状况有无因果关系"))
    if over48:
        denies.append(("超过 48 小时才报案", "可能被拒赔",
                       "立刻补报，说明延迟原因并留痕"))
    # 注意：「非营运」里也含「营运」两个字，不能子串判断
    u = norm(usage)
    is_ops = u.startswith("营运") or u in ("网约车", "营运车辆", "营运性")
    if is_ops and run_biz and "否" in norm(run_biz):
        denies.append(("使用性质与实际不符",
                       "保单填营运、实际又否认跑营运，口径不一致会让保险公司从严认定",
                       "向保险公司核实承保范围与实际用途，如实一致"))

    # ---- 处置步骤
    steps = []
    if injury:
        steps.append("先救人：120 + 122，不要搬动伤者")
    steps.append("报保险（48 小时内），先打电话报案，材料后补")
    steps.append("等交警定责，拿《道路交通事故认定书》")
    if not liable:
        steps.append("交警尚未定责：别现场争，等认定书")
    steps.append("先定损后修车——先修后报会被砍")
    if other_pay and "否" in norm(other_pay):
        steps.append("对方不配合：走代位求偿（己方非全责 + 车损险在保）")
    if other_pay and "失联" in norm(other_pay):
        steps.append("对方失联：向自己的保险公司申请代位求偿，由保险公司追偿")
    steps.append("交材料领赔款；理赔超 30 日未核定的，打 12378 投诉")
    if not acc_date:
        steps = ["没有事故信息，本段按通用流程给出"] + steps

    # ---------------- 报告
    A("# 车险投保与理赔核查报告")
    A("")
    A("> 生成日期：%s；脚本版本 v%s" % (base.isoformat(), VERSION))
    A("")

    A("## 一、结论摘要")
    A("")
    hard = [g for g in gaps if "缺" in g[1] or "过期" in g[1]]
    if hard:
        A("- 保障有 **%d 处缺口**，最要紧的是：%s。" % (len(hard), "、".join(g[0] for g in hard)))
    else:
        A("- 已填的险种没发现缺口（未填的不算）。")
    if denies:
        A("- ⚠️ 扫到 **%d 项拒赔风险**：%s。" % (len(denies), "、".join(d[0] for d in denies)))
    else:
        A("- 未发现拒赔风险因素（未填的不算）。")
    A("- %s" % advice)
    A("")

    A("## 二、保障缺口核查")
    A("")
    A("| 险种 | 状态 | 风险 | 建议 |")
    A("|---|---|---|---|")
    for name, st, risk, fix in gaps:
        A("| %s | %s | %s | %s |" % (name, st, risk, fix))
    A("")
    if model:
        A("车辆：%s%s%s" % (model,
                            "（%d 年登记）" % reg_year if reg_year else "",
                            "，使用性质 %s" % usage if usage else ""))
        A("")

    A("## 三、保费与 NCD")
    A("")
    for s in fee_lines:
        A("- %s" % s)
    A("")
    if claim_calc:
        repair_v, up_v, pct = claim_calc
        A("次年涨费估算：上年商业险保费 %d 元 × %d%% = 约 %d 元。"
          "（%%d%% 是假设的一次出险 NCD 回退幅度，可用 `--ncd` 调整；"
          "实际以保险公司报价为准）" % (last_fee, pct, up_v) if False else
          "次年涨费估算：上年商业险保费 %d 元 × %d%% = 约 %d 元。"
          "（%d%% 为假设的一次出险 NCD 回退幅度，可用 --ncd 调整；实际以保险公司报价为准）"
          % (last_fee, pct, up_v, pct))
        A("")

    A("## 四、本次事故：报不报保险")
    A("")
    A("**%s**" % advice)
    A("")
    if acc_date:
        A("事故日期 %s%s%s" % (acc_date,
                               "，责任：%s" % duty if duty else "",
                               "，维修费 %d 元" % repair if repair is not None else ""))
        A("")
    A("| 项 | 情况 |")
    A("|---|---|")
    A("| 是否有人伤 | %s |" % ("有" if injury else ("无" if injury is False else "未填")))
    A("| 交警是否定责 | %s |" % ("是" if liable else ("否" if liable is False else "未填")))
    A("| 是否已报案 | %s |" % ("是" if reported else ("否" if reported is False else "未填")))
    A("| 是否超 48 小时 | %s |" % ("是" if over48 else ("否" if over48 is False else "未填")))
    A("| 对方是否配合 | %s |" % (other_pay or "未填"))
    A("")

    A("## 五、拒赔风险扫描")
    A("")
    if denies:
        A("| 情形 | 后果 | 怎么办 |")
        A("|---|---|---|")
        for n, c, f in denies:
            A("| %s | %s | %s |" % (n, c, f))
    else:
        A("未命中常见拒赔情形。注意：**未填的不算通过**，"
          "酒驾 / 逃逸 / 营运转非营运 / 改装未告知这四类一旦命中，商业险基本不赔。")
    A("")

    A("## 六、理赔材料清单")
    A("")
    A("| 材料 | 作用 | 缺了怎么补 |")
    A("|---|---|---|")
    for label, role, fix in CLAIM_DOCS:
        A("| %s | %s | %s |" % (label, role, fix if not got(label) else "已有"))
    A("")

    A("## 七、处置步骤")
    A("")
    for i, s in enumerate(steps, 1):
        A("%d. %s" % (i, s))
    A("")

    A("## 八、待办动作")
    A("")
    todo = []
    for name, st, _risk, fix in gaps:
        if "缺" in st or "过期" in st or "偏低" in st:
            todo.append("%s：%s" % (name, fix))
    for n, _c, f in denies:
        todo.append("处理拒赔风险「%s」：%s" % (n, f))
    if reported is False:
        todo.append("立刻向保险公司报案（48 小时内）")
    if liable is False:
        todo.append("联系处理事故的交警中队拿《事故认定书》")
    if over48:
        todo.append("已超 48 小时：补报并书面说明延迟原因")
    if other_pay and ("否" in norm(other_pay) or "失联" in norm(other_pay)):
        todo.append("向自己的保险公司申请代位求偿（己方非全责 + 车损险在保）")
    for label, _role, fix in CLAIM_DOCS:
        if not got(label):
            todo.append("补齐 %s：%s" % (label, fix))
    todo.append("向业务员问清：出险一次次年保费具体涨多少（本报告的涨幅是估算）")
    for i, t in enumerate(todo, 1):
        A("%d. %s" % (i, t))
    A("")

    A("## 九、输出纪律与免责")
    A("")
    A("- 不推荐具体保险公司、不估算精确保费、不承诺理赔结果；")
    A("- 次年涨费只在填了「上年商业险保费」时才估算，且明确标注了假设系数；")
    A("- 责任划分以交警认定为准，是否赔付以保险公司核定为准；")
    A("- 不代拟法律文书、不代办理赔。")
    A("")

    body = "\n".join(L)
    meta = {
        "version": VERSION,
        "gaps": len([g for g in gaps if "缺" in g[1] or "过期" in g[1]]),
        "denies": len(denies),
        "risks": len(denies) + len([g for g in gaps if "缺" in g[1]]),
        "repair": repair,
        "estimated_premium_up": claim_calc[1] if claim_calc else None,
        "advice_report": claim_calc[0] > claim_calc[1] if claim_calc else None,
    }
    return body, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ncd", type=int, default=25,
                    help="假设一次出险导致的次年商业险保费回退百分比，默认 25")
    a = ap.parse_args()

    base = None
    if a.base:
        try:
            base = dt.date(*[int(x) for x in a.base.split("-")])
        except Exception:
            base = None

    body, meta = build_report(a.input, base, a.ncd)
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
