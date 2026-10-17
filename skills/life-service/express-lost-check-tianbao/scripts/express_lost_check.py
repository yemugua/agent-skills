#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快递丢失赔偿核算。

用法：
  python express_lost_check.py 采集表.md --base 2026-10-05 --out 核算报告.md
  python express_lost_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失（给提示串，不崩）。
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如："]


# ------------------------------------------------------------------ 解析
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
    """解析 markdown 表格行与 '字段：值' 行，保留表头行。"""
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
            parts = re.split(r"[:：]", line, maxsplit=1)
            if len(parts) == 2:
                k, v = parts[0].strip(), parts[1].strip()
                if k and k not in kv:
                    kv[k] = v
    return kv


def get_text(kv, aliases):
    """最长别名优先匹配。"""
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
    v = (v or "").strip()
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
    return n in ("有", "是", "已经", "已", "已完成", "true", "yes")


def no(v):
    n = norm(v)
    return n in ("无", "否", "没有", "未", "未做", "false", "no")


def parse_num(s):
    if not s:
        return None
    s = str(s).replace(",", "").replace("，", "").replace("¥", "").replace("元", "")
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
    return "¥" + fmt_num(x)


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


# ------------------------------------------------------------------ 规则
POSTAL_SERVICE = ["平邮", "挂号信", "挂号", "邮政普遍服务", "标准快递", "EMS"]
FRESH_KEYS = ["生鲜", "水果", "海鲜", "冷链", "冰鲜", "冻品", "鲜花", "蛋糕", "活体"]
PROHIBIT_KEYS = ["违禁", "管制", "危险品", "电池", "液体", "粉末", "打火机", "刀具", "烟花"]

SCENES = [
    ("locker", "代收点 / 快递柜投递导致丢失", ["代收点", "快递柜", "驿站", "柜子", "放门口", "未派送"]),
    ("steal", "被冒领 / 非本人签收", ["冒领", "被别人", "非本人", "别人签收", "别人拿走", "错领"]),
    ("prohibit", "违禁品或企业拒收导致的损失", PROHIBIT_KEYS),
    ("fresh", "生鲜 / 冷链腐烂变质", FRESH_KEYS),
    ("international", "国际件 / 跨境件", ["国际", "跨境", "海外", "港澳台"]),
]


def detect_scene(field):
    """返回 (中文名, code)；code 用于分支判断，中文名用于展示。"""
    s = norm(field)
    if not s:
        return ("未填", None)
    for code, name, kws in SCENES:
        for kw in kws:
            if kw in s:
                return (name, code)
    return ("普通件丢失", "plain")


def has_any(field, kws):
    s = norm(field)
    for kw in kws:
        if kw in s:
            return True
    return False


# ------------------------------------------------------------------ 赔偿口径
def calc_compensation(f):
    """返回 (企业口径, 可主张口径, 说明)。两个口径都给数。"""
    value = f["item_value"]
    insured = f["insured"]
    insured_amt = f["insured_amt"]
    postage = f["postage"]

    corp = None
    corp_basis = ""
    if insured is True:
        if insured_amt is None:
            corp, corp_basis = None, ("保价件但**未填保价金额**，企业口径算不出来；"
                                      "保价件通常按保价金额赔偿，请补填保价金额。")
        else:
            corp = insured_amt if value is None else min(insured_amt, value)
            corp_basis = ("保价件：企业按**保价金额**赔偿（保价额超过内件实际价值的，"
                          "以实际价值为限）。")
    elif postage is not None:
        corp = round(postage * 3, 2)
        if insured is False:
            who = "未保价"
        elif insured is None:
            who = "是否保价未填，暂按"
        else:
            who = "保价件，企业仍可能援引"
        corp_basis = ("%s：企业依其快递运单格式条款，常按**资费的三倍**封顶赔偿"
                      "（邮政普遍服务未保价同样适用三倍资费上限口径），"
                      "故列示企业口径 **%s**。" % (who, money(corp)))
    elif insured is False:
        corp, corp_basis = None, ("未保价且**未填资费**，企业口径算不出来；"
                                  "按三倍资费算需要资费数额。请补填资费。")

    # 可主张口径
    if value is not None:
        claim = value
        claim_basis = ("按《民法典》运输合同项下**实际损失**赔偿，内件实际价值 %s。"
                       % money(value))
        if f["heavy"] is True:
            claim = round(value + (f["extra_loss"] or 0), 2)
            claim_basis += ("另加合理的直接损失 %s。" % money(f["extra_loss"] or 0))
    elif postage is not None:
        claim = round(postage * 3, 2)
        claim_basis = ("**内件实际价值未填**，可主张口径暂时只能退到三倍资费 %s；"
                       "补齐价值凭证后可主张更高。" % money(claim))
    else:
        claim = None
        claim_basis = ("内件实际价值与资费都未填，两个口径都算不出来。")

    return corp, claim, corp_basis, claim_basis


def path_order(f, scene):
    ecom = f["ecommerce"]
    steps = []
    if ecom is True:
        steps.append(("第 0 步（优先）",
                      "**电商件先找卖家退款**：货没到，卖家还没发货/未签收，"
                      "直接在订单页点「未收到货」让商家重新发货或退款——"
                      "这比跟快递打官司快得多，也不必证明内件价值。"))
    steps += [
        ("第 1 步", "向快递企业客服正式投诉并在系统里留单：提供运单号、交寄时间、"
                    "内件名称与价值、诉求金额，索取**受理工单号**（没有工单号等于没投诉）"),
        ("第 2 步", "一次申诉不成，在被投诉企业省级机构/官方申诉入口做**二次申诉**，"
                    "同样索要申诉受理编号"),
        ("第 3 步", "拨打 **12305**（邮政业消费者申诉）投诉：对申诉处理结果不服或企业逾期未答复的，"
                    "可请求邮政管理部门裁定（一般 30 日内答复）"),
        ("第 4 步", "涉及经营者违约、价值争议的，向 **12315（市场监管）** 或消协反映；"
                    "物流服务消费纠纷也可走 12345"),
        ("第 5 步", "仍不解决就提起民事诉讼，标的额小的走**小额诉讼**（诉讼时效 3 年）"),
    ]
    if scene == "locker":
        steps.append(("分支提示", "投递到代收点/快递柜的：先核实企业是否**未经同意放置**、"
                                  "有无投递通知；未征得收件人同意放置导致丢失的，"
                                  "企业不能以「已投递」免责"))
    if scene == "steal":
        steps.append(("分支提示", "疑似冒领的：立即报警并索要报案回执；"
                                  "同时要求企业提供**投递现场监控与签收影像**"))
    if scene == "international":
        steps.append(("分支提示", "国际件：先看是否走邮政渠道（邮政普遍服务适用三倍资费口径），"
                                  "商业快递则按其国际条款；跨境件还可能涉及报关与保险"))
    return steps


def todo_list(f, results, scene, corp, claim):
    todos = []
    for _, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if f["ecommerce"] is True:
        extra.append(("先找卖家", "电商件优先在订单页点「未收到货」，比打快递官司快"))
    if scene == "steal" and f["police"] is not True:
        extra.append(("报警留痕", "疑似冒领立即报警并索要报案回执"))
    if scene == "locker" and f["consent"] is not True:
        extra.append(("核实放置同意", "要求企业说明是否征得收件人同意放置到代收点/快递柜"))
    if scene == "fresh":
        extra.append(("时效 Matters", "生鲜类尽快固定霜冻、化冻、变质照片与温度记录"))
    extra.append(("保存运单与签收记录", "运单底单、下单截图、物流轨迹截图全部存好"))
    extra.append(("一年期限", "自交寄之日起一年内提出赔偿请求；诉讼时效 3 年，别拖"))
    seen = set()
    out = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        out.append((n, s))
    return out


EVIDENCE_ROWS = [
    ("快递运单（底单或电子面单截图）", "运单"),
    ("保价凭证 / 保价协议", "保价凭证"),
    ("内件价值凭证（发票、订单、付款记录）", "价值凭证"),
    ("外包装与内件照片", "包装照片"),
    ("重量记录（交寄称重或物流称重）", "重量记录"),
    ("物流轨迹 / 签收记录截图", "轨迹记录"),
    ("与快递企业的投诉工单号", "工单记录"),
    ("报警回执（疑似冒领时）", "报警回执"),
]


def evidence_rows(kv):
    labels = {
        "快递运单（底单或电子面单截图）": ["有无快递运单", "运单"],
        "保价凭证 / 保价协议": ["有无保价凭证", "保价凭证"],
        "内件价值凭证（发票、订单、付款记录）": ["有无内件价值凭证", "价值凭证"],
        "外包装与内件照片": ["有无外包装与内件照片", "包装照片"],
        "重量记录（交寄称重或物流称重）": ["有无重量记录", "重量记录"],
        "物流轨迹 / 签收记录截图": ["有无物流轨迹", "轨迹记录"],
        "与快递企业的投诉工单号": ["有无投诉工单号", "工单"],
        "报警回执（疑似冒领时）": ["有无报警回执", "报警回执"],
    }
    out = []
    for name, _d in EVIDENCE_ROWS:
        v = get_text(kv, labels[name])
        if yes(v):
            st = "是"
        elif no(v):
            st = "否"
        elif filled(v):
            st = "待确认"
        else:
            st = "未填"
        out.append((name, st))
    return out


# ------------------------------------------------------------------ 报告
def render(f, results, corp, claim, corp_basis, claim_basis, scene, steps, todos, today):
    L = []
    L.append("# 快递丢失赔偿核算报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 快递企业：%s" % (f["company"] or "未填"))
    L.append("- 运单号：%s" % (f["waybill"] or "未填"))
    L.append("- 内件：%s" % (f["item"] or "未填"))
    L.append("")

    bad = [r for _, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _, rows in results for r in rows if r[1] == "待补正"]

    L.append("## 一、结论摘要")
    L.append("")
    better = None
    if corp is not None and claim is not None:
        better = "可主张口径" if claim > corp else "企业口径"
    if corp is None and claim is None:
        L.append("**判定：关键数字都缺，暂时算不出赔偿金额。**先补「内件价值」和「资费/保价金额」，"
                 "再跑一次——赔偿的核心永远是**能不能证明这包裹里装了什么东西、值多少钱**。")
    elif better == "可主张口径":
        L.append("**判定：企业只会按它的格式条款赔（企业口径 %s），但实际损失远不止这个数（可主张口径 %s）。"
                 "优先按可主张口径主张，同时把两套数一起摆上。**" % (money(corp), money(claim)))
    elif better == "企业口径":
        L.append("**判定：企业口径（%s）不低于你的举证价值（%s），先按企业口径谈；"
                 "但如果企业并未对三倍/封顶条款作提示说明，仍可主张实际损失。**" % (money(corp), money(claim)))
    else:
        L.append("**判定：%s**" % (money(corp) if corp is not None else money(claim)))
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(todo))
    L.append("")
    for name, _s, msg in bad[:5]:
        L.append("- **%s**：%s" % (name, (msg or "").replace("**", "")))
    for name, _s, msg in risk[:5]:
        L.append("- %s：%s" % (name, (msg or "").replace("|", " ")))
    L.append("")

    titles = ["二、两套赔偿口径对比", "三、赔偿测算（含算式）",
              "四、责任与举证", "五、特殊场景分支"]
    for (title, rows), t in zip(results, titles):
        L.append("## %s" % t)
        L.append("")
        if not rows:
            L.append("暂无可核查项（相应字段未填，未填的一律不按通过处理）。")
            L.append("")
            continue
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for name, state, msg in rows:
            L.append("| %s | %s | %s |" % (name, state, (msg or "").replace("|", " ")))
        L.append("")

    L.append("## 六、阶梯路径排序")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 七、时限清单")
    L.append("")
    L.append("| 事项 | 期限 |")
    L.append("|---|---|")
    L.append("| 向企业提出赔偿请求 | 自交寄之日起**一年内**（越早越好） |")
    L.append("| 12305 邮政业申诉 | 对申诉处理不服或企业逾期未答复的可请求裁定，一般 30 日内答复 |")
    L.append("| 民事诉讼时效 | **3 年**，自知道或应当知道权利受损及义务人之日起算 |")
    L.append("| 生鲜 / 易腐品 | 当场拍照并即时投诉，超过几天再主张难度陡增 |")
    L.append("| 监控留存 | 投递点监控通常只有 7~30 天，疑似冒领的立即要求保全 |")
    L.append("")
    ship = f["ship_date"]
    if ship:
        left = (ship + timedelta(days=365) - today).days
        L.append("- 自 %s 交寄起算，一年期限%s。"
                 % (ship.isoformat(),
                    ("还剩 %d 天" % left) if left >= 0 else ("已过 %d 天" % -left)))
        L.append("- 诉讼时效 3 年，从 %s 起算还剩 %d 天。"
                 % (ship.isoformat(), (ship + timedelta(days=1095) - today).days))
    L.append("")

    L.append("## 八、证据缺口与清单核对")
    L.append("")
    L.append("| 材料 | 状态 |")
    L.append("|---|---|")
    for name, st in f["evidence_rows"]:
        L.append("| %s | %s |" % (name, st))
    L.append("")
    miss = [n for n, s in f["evidence_rows"] if s in ("否", "未填")]
    L.append("缺口：%s。" % ("、".join(miss) if miss else "已填项无缺口；未填的不算已具备"))
    L.append("")
    L.append("**举证责任提示**：主张赔偿要先证明**运单成立**（运单号、交寄记录）、"
             "**内件存在与价值**（发票/订单/付款记录/重量）、**丢失事实**（轨迹查询、"
             "企业答复、报警回执）。企业若援引三倍/封顶条款免除自身责任，须证明其"
             "对该条款作了**提示说明义务**——未加粗、未单独签字确认的快递单背面小字，"
             "消费者可主张不成为合同内容。")
    L.append("")

    L.append("## 九、待办补正动作")
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
    L.append("- 本结果依《邮政法》《民法典》运输合同及《快递市场管理办法》等**通用规则**整理，"
             "**不替代律师意见**。")
    L.append("- 保价 / 未保价的赔偿上限、三倍资费口径的适用边界，"
             "在邮政普遍服务与快递业务之间存在**两套口径**，本报告已分别给出，"
             "具体适用以主管部门认定与司法机关裁判为准。")
    L.append("- 不预测诉讼结果、不承诺必定按实际价值获赔；"
             "**能否按可主张口径拿到钱，取决于价值证据的充分程度**。")
    L.append("- 违禁品、超范围物品导致的损失，企业依法可不赔或只按约定处理，本报告会单独标注。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("")
    L.append("本结果依通用规则整理，不替代专业意见，最终以主管部门/司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, corp, claim, todos, today):
    return {
        "核查日期": today.isoformat(),
        "快递企业": f["company"],
        "运单号": f["waybill"],
        "内件": f["item"],
        "丢失场景": f["scene"][0],
        "企业口径": corp,
        "可主张口径": claim,
        "口径孰优": ("可主张口径" if (corp is not None and claim is not None and claim > corp)
                     else ("企业口径" if (corp is not None and claim is not None and corp > claim)
                           else "需补正")),
        "结论": {
            "不通过": [r[0] for _, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _, rows in results for r in rows if r[1] == "待补正"],
        },
        "风险项": [r[0] for _, rows in results for r in rows if r[1] == "有风险"],
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = read_text(args.input)
    kv = build_kv(text)
    today = base_date(args.base)

    f = {
        "company": get_text(kv, ["快递企业", "寄递企业", "快递公司"]),
        "waybill": get_text(kv, ["运单号", "快递单号", "快递单号"]),
        "item": get_text(kv, ["内件名称", "内件物品", "寄递物品"]),
        "ship_date": parse_date(get_text(kv, ["交寄日期", "寄件日期", "下单寄件日期"])),
        "postage": parse_num(get_text(kv, ["资费", "邮费", "运费"])),
        "insured": None,
        "insured_amt": parse_num(get_text(kv, ["保价金额", "声明价值"])),
        "item_value": parse_num(get_text(kv, ["内件实际价值", "内件价值", "物品价值"])),
        "extra_loss": parse_num(get_text(kv, ["其他直接损失金额", "附带损失金额"])),
        "heavy": None,
        "ecommerce": None,
        "scene": detect_scene(get_text(kv, ["丢失情形", "丢失场景", "情形说明"])),
        "police": None,
        "consent": None,
        "confirmed": None,
        "evidence_rows": evidence_rows(kv),
    }
    ins = get_text(kv, ["是否保价", "有无保价"])
    if yes(ins):
        f["insured"] = True
    elif no(ins):
        f["insured"] = False
    ec = get_text(kv, ["是否为电商件/卖家发货", "是否电商件", "卖家发货"])
    if yes(ec):
        f["ecommerce"] = True
    elif no(ec):
        f["ecommerce"] = False
    hl = get_text(kv, ["是否有其他直接损失", "其他直接损失金额"])
    if yes(hl):
        f["heavy"] = True
    pl = get_text(kv, ["是否已报警", "报警"])
    if yes(pl):
        f["police"] = True
    elif no(pl):
        f["police"] = False
    cs = get_text(kv, ["投递是否征得收件人同意", "是否征得同意放置"])
    if yes(cs):
        f["consent"] = True
    elif no(cs):
        f["consent"] = False
    cf = get_text(kv, ["企业是否确认丢件", "是否确认丢件", "企业是否承认丢失",
                       "企业是否确认丢失"])
    if yes(cf):
        f["confirmed"] = True
    elif no(cf):
        f["confirmed"] = False

    missing = []
    if not filled(f["company"]):
        missing.append("快递企业")
    if not filled(f["item"]):
        missing.append("内件名称")
    if f["item_value"] is None and not filled(f["insured_amt"] or ""):
        missing.append("内件实际价值（或保价金额）")

    corp, claim, corp_basis, claim_basis = calc_compensation(f)
    steps = path_order(f, f["scene"][1])

    # ---------------------------------------------------------- 各段
    r_two = []
    if corp is None and claim is None:
        r_two.append(("两套口径", "待补正",
                      "企业口径与可主张口径都算不出来——必须至少填「资费」或「保价金额」，"
                      "并且填「内件实际价值」，才能给出两个数。"))
    else:
        r_two.append(("企业口径", "通过" if corp is not None else "待补正",
                      (corp_basis + "金额为 **%s**。" % money(corp)) if corp is not None
                      else corp_basis))
        r_two.append(("可主张口径", "通过" if claim is not None else "待补正",
                      (claim_basis + "金额为 **%s**。" % money(claim)) if claim is not None
                      else claim_basis))
        if corp is not None and claim is not None and claim > corp:
            r_two.append(("差额", "有风险",
                          "两套口径差 **%s**。企业只会主动给它的那个数，"
                          "所以主张时必须同时摆出两个数，并把价值凭证附上。"
                          % money(claim - corp)))
        else:
            r_two.append(("差额", "通过",
                          "当前两口径接近或企业口径更高，先按企业口径谈；"
                          "但企业若未对三倍/封顶条款履行提示说明义务，仍可主张实际损失。"))

    r_calc = []
    postage = f["postage"]
    value = f["item_value"]
    if postage is not None:
        r_calc.append(("资费与三倍口径", "通过",
                       "资费 %s × 3 = %s。这是企业援引格式条款时的封顶数，"
                       "注意运单背面小字若未加粗、未单独确认，可主张不成为合同内容。"
                       % (money(postage), money(postage * 3))))
    if value is not None:
        r_calc.append(("内件实际价值", "通过",
                       "内件实际价值 %s，这是可主张口径的基数。"
                       "价值凭证（发票、订单、付款记录、同类二手成交价）要能对应到**这一件**。"
                       % money(value)))
        if f["heavy"] is True:
            r_calc.append(("其他直接损失", "通过",
                           "另计直接损失 %s，可主张口径合计 %s。"
                           % (money(f["extra_loss"]), money(value + (f["extra_loss"] or 0)))))
    if f["insured"] is True and f["insured_amt"] is None:
        r_calc.append(("保价金额", "待补正",
                       "填了保价但未填保价金额，保价件通常按保价金额赔偿，请补上。"))
    if f["insured"] is False:
        r_calc.append(("保价", "有风险",
                       "未保价：企业的格式条款封顶（常见三倍资费或固定上限）"
                       "对你极为不利，**这是你唯一能靠举证赢回差价的地方**——"
                       "把内件价值的证据做扎实。"))

    r_evidence = []
    if f["confirmed"] is True:
        r_evidence.append(("丢失事实举证", "通过",
                           "企业已确认内件丢失/未送达，丢件事实有对方自认，"
                           "可据此直接主张金额；同时把这份确认书面化并留存。"))
    elif f["confirmed"] is False:
        r_evidence.append(("丢失事实举证", "有风险",
                           "企业未确认丢件：必须先用物流轨迹截图（轨迹停在派送前或显示未送达）、"
                           "企业书面答复、报警回执固定「内件未送达」这一事实，"
                           "否则企业会以「已投递/收件人未取」抗辩。"))
    else:
        r_evidence.append(("丢失事实举证", "待补正",
                           "未填企业是否确认丢件。先用物流轨迹与企业答复固定「内件未送达」这一事实，"
                           "轨迹停在某个节点、企业答复不认的，都要截图；"
                           "拿到企业书面答复后可把此项改判为已固定。"))
    if f["waybill"] and not filled(f["waybill"]):
        r_evidence.append(("运单号", "待补正", "运单号未填，无法调取轨迹与企业记录。"))
    vps = [n for n, s in f["evidence_rows"] if s != "是"]
    if vps:
        r_evidence.append(("证据完整性", "有风险",
                           "以下材料未齐：%s。缺价值凭证是「赔不到实际价值」的头号原因。"
                           % "、".join(vps)))
    else:
        r_evidence.append(("证据完整性", "通过", "证据材料齐备，具备按实际价值主张的基础。"))
    if f["scene"][0] == "steal" and f["police"] is not True:
        r_evidence.append(("报警回执", "不通过",
                           "疑似冒领未报警。没有报案回执，难以证明是丢失还是你自己没取。"))

    r_scene = []
    scene, _kw = f["scene"]
    if scene in ("代收点 / 快递柜投递导致丢失", "被冒领 / 非本人签收"):
        r_scene.append(("场景分支", "通过",
                        "**%s**：先核实企业投递是否征得收件人同意；未经同意放置到代收点/快递柜"
                        "导致无法取件的，企业不能以「已投递」为由免责。"
                        "同时立即要求企业提供投递现场监控与签收影像（留存期通常只有 7~30 天）。"
                        % scene))
    elif scene not in ("未填", "普通件丢失"):
        r_scene.append(("场景分支", "通过", "**%s**：按该分支的救济要点处理，见第六段。" % scene))

    if f["ecommerce"] is True:
        r_scene.append(("电商件", "通过",
                        "**电商件优先找卖家**：在订单页点「未收到货」，由商家重新发货或退款。"
                        "这条路径不必先证明内件价值，通常最快最省事。"))
    elif f["ecommerce"] is False:
        r_scene.append(("电商件", "通过", "非电商件（本人直接寄递），走第二段的阶梯路径。"))
    if has_any(f["item"] or "", FRESH_KEYS):
        r_scene.append(("生鲜 / 易腐", "有风险",
                        "内件为生鲜易腐品：价值随时间快速贬损，务必**当场拍照、立即投诉**，"
                        "并留存化冻、霜变、腐坏的照片与温度记录；拖几天再主张难度陡增。"))
    if has_any(f["item"] or "", PROHIBIT_KEYS):
        r_scene.append(("违禁 / 限寄物品", "不通过",
                        "内件含违禁或限寄物品：企业依法可不赔或仅按约定处理，"
                        "主张实际损失的空间被大幅压缩，请核实是否属于禁寄范围。"))
    if has_any(f["item"] or "", POSTAL_SERVICE):
        r_scene.append(("邮政普遍服务", "有风险",
                        "走的是邮政普遍服务渠道（平邮/挂号/EMS 标准）："
                        "未保价的**邮政普遍服务**适用《邮政法》的**三倍资费上限**口径，"
                        "可主张空间小于快递的运输合同违约赔偿。"))

    results = [("两套赔偿口径", r_two), ("赔偿测算", r_calc),
               ("责任与举证", r_evidence), ("特殊场景分支", r_scene)]

    todos = todo_list(f, results, f["scene"][1], corp, claim)

    if args.json:
        print(json.dumps(to_json(f, results, corp, claim, todos, today),
                         ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, corp, claim, corp_basis, claim_basis,
                 f["scene"][0], steps, todos, today)
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
