#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""二手房买卖风险与费用核查。

用法：
  python housing_deal_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python housing_deal_check.py 采集表.md --json
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

# 权属与标的瑕疵关键词
TITLE_RISKS = [
    ("一房二卖或重复抵押", ["一房二卖", "二卖", "重复抵押", "多头抵押", "再次出售"]),
    ("产权证缺失或未办证", ["无证", "未办证", "没有房产证", "房本未下", "未取得产权证"]),
    ("抵押未解除", ["抵押", "查封", "冻结", "抵押未解", "未解押"]),
    ("共有权人未签字", ["共有", "共有人", "夫妻共有", "继承", "析产", "一人名下"]),
    ("租赁未披露", ["租", "租客", "承租", "租赁", "未告知租赁"]),
    ("户口未迁出", ["户口", "户籍", "迁户", "户口未迁"]),
    ("房屋性质受限", ["经济适用", "限售", "央产", "军产", "小产权", "两限房"]),
    ("面积或格局不符", ["面积", "户型", "格局", "公摊", "赠送面积", "缩水"]),
]

# 费用项目（通用口径，实际以当地现行标准与合同约定为准）
COST_ITEMS = [
    ("契税", ["契税"], 0.03),
    ("增值税及附加", ["增值税", "个税", "所得税", "土地增值税"], 0.05),
    ("中介服务费", ["中介费", "服务费", "佣金"], None),
    ("贷款评估费", ["评估费", "贷款服务", "抵押登记"], None),
    ("公证与登记费", ["公证", "登记费", "工本费"], None),
]

# 交易流程节点
DEAL_STAGES = [
    ("定金或意向金", ["定金", "意向金", "订金", "认购金"]),
    ("首付款", ["首付款", "首付", "首期款"]),
    ("网签与备案", ["网签", "备案", "网签备案"]),
    ("贷款与评估", ["贷款", "按揭", "评估"]),
    ("资金监管", ["监管", "资金监管", "托管"]),
    ("过户", ["过户", "转移登记", "不动产登记"]),
    ("交房与户口迁出", ["交房", "交付", "户口迁出", "腾房"]),
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
    if n in ("有", "是", "已经", "已", "已完成", "已做", "可以", "能", "已网签", "已过户"):
        return True
    return n.startswith("已") or n.startswith("有")


def no(v):
    n = norm(v)
    if n in ("无", "否", "没有", "未", "未做", "false", "no", "正常", "无抵押"):
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


# ------------------------------------------------------------------ 一 标的与权属
def checks_title(f):
    out = []
    if unknown(f["ownership"]):
        out.append(("产权归属是否清晰", "待补正",
                    "产权人是谁、有几位共有人未填。**二手房第一件事是查产权**："
                    "谁登记在名下、有无共有人、有无抵押查封，这三点不清楚后面全是风险。"))
    else:
        out.append(("产权归属是否清晰", "通过", "产权人已确认：%s" % f["ownership"]))

    if unknown(f["coowner"]):
        out.append(("共有权人是否已签字", "待补正",
                    "是否需要共有人（配偶、父母、子女）共同签字未填。"
                    "**共有权人未签字的买卖，可能被认定无效或无权处分**，"
                    "这是最常见的翻车点之一。"))
    elif yes(f["coowner"]):
        out.append(("共有权人是否已签字", "有风险",
                    "涉及共有人，**必须确认每一位共有人都已在合同上签字**；"
                    "婚后购买的房屋通常属于夫妻共同财产。"))
    else:
        out.append(("共有权人是否已签字", "通过", "无共有人签字问题（以产权登记为准）。"))

    d = f["mortgage"]
    if unknown(d):
        out.append(("抵押查封情况", "待补正",
                    "有无抵押、查封、冻结未填。"
                    "**带押过户虽可办，但风险与成本高**；有抵押的必须先确认解押安排与时间。"))
    elif yes(d):
        out.append(("抵押查封情况", "有风险",
                    "存在抵押或查封。**查封状态下房屋不能交易**；"
                    "带押过户需明确解押时间、资金监管安排与违约责任，"
                    "否则容易出现房款付了但过不了户的情况。"))
    else:
        out.append(("抵押查封情况", "通过", "无抵押、查封、冻结。"))

    cert = f["certificate"]
    if unknown(cert):
        out.append(("产权证与实际是否一致", "待补正",
                    "是否已核验产权证原件、是否与房屋现状一致未填。"
                    "**必须现场看房本原件**，并到不动产登记机构查档核实。"))
    elif no(cert):
        out.append(("产权证与实际是否一致", "不通过",
                    "**未能核验产权证**，这是重大风险。二手房交易必须核对房本原件，"
                    "并到登记机构查档确认权利人、抵押与查封状态。"))
    else:
        out.append(("产权证与实际是否一致", "通过", "已核验产权证与登记信息。"))
    return out


# ------------------------------------------------------------------ 二 合同条款风险
def checks_contract(f):
    out = []
    e = f["earnest"]
    if unknown(e):
        out.append(("定金条款是否写清", "待补正",
                    "定金金额、退还与双倍返还规则是否写清未填。"
                    "**定金与订金不是一回事**：定金适用罚则，可要求双倍返还；"
                    "订金一般只能原数返还。合同里必须写明是「定金」还是「订金」。"))
    elif yes(e):
        out.append(("定金条款是否写清", "有风险",
                    "涉及定金。**务必在合同中明确是「定金」还是「订金」、金额、"
                    "退还条件与违约责任**，否则发生争议时按订金处理，"
                    "拿不到双倍返还。"))
    else:
        out.append(("定金条款是否写清", "通过", "无定金约定或条款已写清。"))

    r = f["subject_risk"]
    if not filled(r):
        out.append(("卖方是否披露已知风险", "待补正",
                    "卖方是否告知过漏水、结构、违建、凶宅、欠费、户口等情况未填。"
                    "**卖方刻意隐瞒属于违约甚至欺诈**，是后续主张解约与赔偿的关键事实。"))
    else:
        hits = [lbl for lbl, ws in TITLE_RISKS if hit_any(r, ws) is True]
        if hits:
            out.append(("卖方是否披露已知风险", "有风险",
                        "已知情况涉及**%s**。这些都要写进合同并约定处理方式，"
                        "否则事后追责极难。" % "、".join(hits)))
        else:
            out.append(("卖方是否披露已知风险", "有风险",
                        "已披露但仍需把关键事实写进合同条款，"
                        "口头承诺在纠纷中很难被采信。"))

    lease = f["lease"]
    if unknown(lease):
        out.append(("租赁情况是否核实", "待补正",
                    "房屋是否出租、租期何时结束未核实。"
                    "**买卖不破租赁**：卖方租客的租期可能影响你的实际交房时间。"))
    elif yes(lease):
        out.append(("租赁情况是否核实", "有风险",
                    "房屋有租客。租期未满时原则上**承租人有权继续承租**，"
                    "你要在合同里写明交房时间、租金由谁承担、租客不搬的违约责任。"))
    else:
        out.append(("租赁情况是否核实", "通过", "无租赁或租期已结束。"))

    h = f["hukou"]
    if unknown(h):
        out.append(("户口迁出安排", "待补正",
                    "卖方户口迁出时间与违约责任未填。"
                    "**户口迁不走不影响过户，但会给你带来长期麻烦**（上学、居住证等），"
                    "务必留尾款并约定违约金。"))
    elif hit_any(h, ["已迁出", "已迁完", "迁出完成", "迁完", "已迁"]) is True:
        out.append(("户口迁出安排", "通过", "卖方户口已迁出或已确认迁出完成。"))
    else:
        # 字段名为「是否已迁出」，填「否」「未迁」「三年内迁」都等于还没迁，一律算风险
        out.append(("户口迁出安排", "有风险",
                    "卖方户口**尚未迁出**（填的是「%s」）。建议**保留部分尾款至迁户完成**，"
                    "并约定每日违约金；否则过户后你拿不到房本原件、也无法处置。" % h))
    return out


# ------------------------------------------------------------------ 三 费用测算
def calc_cost(f):
    res = {"可测算": False, "项目": [], "已知合计": 0.0, "缺项": [], "说明": ""}
    price = parse_num(f["price"])
    agent = parse_num(f["agent_fee"])
    if price is None:
        res["说明"] = "总价未填，无法测算契税等按价计费的项目。"
        return res
    res["可测算"] = True
    items = []
    # 契税：按面积与是否首套区分，这里给首套 3% 的通用口径作参考
    deed = price * 0.03
    items.append(("契税（参考）", deed, "总价 %s × 3%%（首套常见口径，"
                  "面积 90㎡以上、非首套的税率不同，以税务与当地口径为准）" % money(price)))
    if agent is not None:
        items.append(("中介服务费（已填）", agent, "按合同约定：%s" % money(agent)))
    else:
        res["缺项"].append("中介服务费")
    res["缺项"].append("贷款评估与登记公证费")
    total = sum(x[1] for x in items)
    res["项目"] = [x[0] for x in items]
    res["已知合计"] = round(total, 2)
    res["算式"] = ["%s：%s" % (n, d) for n, _a, d in items]
    res["说明"] = ("费用随总价、面积、是否首套与当地政策变动，**以上为参考区间估算**；"
                   "另需预留贷款评估、登记公证、可能的税费与中介费差额。")
    return res


def checks_cost(f, calc):
    out = []
    if not calc["可测算"]:
        out.append(("税费与中介费测算", "待补正", calc["说明"]))
        return out
    out.append(("税费与中介费", "有风险",
                "已知项目合计约 **%s**（参考口径）：%s。%s"
                % (money(calc["已知合计"]), "；".join(calc["算式"]), calc["说明"])))
    if calc["缺项"]:
        out.append(("费用缺口", "有风险",
                    "尚未计入：%s。**签约前要求中介出具书面费用清单**，"
                    "并把「税费与中介费由谁承担」写进合同。" % "、".join(calc["缺项"])))
    else:
        out.append(("费用缺口", "通过", "费用项目已较完整。"))
    return out


# ------------------------------------------------------------------ 四 贷款与资格
def checks_loan(f):
    out = []
    if unknown(f["loan"]):
        out.append(("是否需要贷款", "待补正", "是否需要按揭未填，**这决定资金安排与流程长短**。"))
    elif yes(f["loan"]):
        out.append(("是否需要贷款", "通过",
                    "需要贷款。**注意：贷款审批不通过是常见风险**，"
                    "合同里应写明贷款不成时的责任归属（通常由买方承担违约金或解约）。"))
    else:
        out.append(("是否需要贷款", "通过", "全款交易，无贷款审批风险。"))

    if unknown(f["qualify"]):
        out.append(("购房资格与限购", "待补正",
                    "是否符合当地限购条件（社保、个税、户籍、名下房产）未核实。"
                    "**限购资格问题是能否网签的前提**，先自查再付定金。"))
    elif yes(f["qualify"]):
        out.append(("购房资格与限购", "有风险",
                    "资格存在不确定。**先到当地住建/不动产登记部门核实**"
                    "（限购查询、社保与个税记录），确认后再签合同付定金。"))
    elif no(f["qualify"]):
        # 字段是「是否符合限购条件」，填「否」= 不符合，是硬门槛问题，不是通过
        out.append(("购房资格与限购", "不通过",
                    "**按采集表填的是不符合限购条件**。"
                    "在限购城市没有购房资格**无法网签备案、无法过户**，"
                    "已付的定金很可能退不出来。**立即到当地住建部门核实**，"
                    "确认有资格再继续；确无资格的，评估解约代价并及时主张返还定金。"))
    else:
        out.append(("购房资格与限购", "通过", "已确认符合当地限购条件。"))
    return out


# ------------------------------------------------------------------ 五 资金安全
def checks_money(f):
    out = []
    if unknown(f["supervision"]):
        out.append(("是否采用资金监管", "待补正",
                    "房款是否走银行资金监管未填。"
                    "**这是二手房交易最大的防骗点**：直接付给卖方或中介，"
                    "一旦对方挪用或房子出问题，钱很难追回。"))
    elif yes(f["supervision"]):
        out.append(("是否采用资金监管", "通过",
                    "已采用资金监管：房款由银行监管，按约定条件解付。**务必确认监管账户与解付条件写进合同**。"))
    else:
        out.append(("是否采用资金监管", "不通过",
                    "**未采用资金监管**，这是高风险结构。"
                    "若坚持不走监管，应大幅提高首付比例、缩短付款节奏，"
                    "并把过户与付款严格绑定。"))

    d = f["deposit_to_whom"]
    if unknown(d):
        out.append(("款项支付对象", "待补正", "款项付给谁未填。**付给中介个人账户是常见骗局**，务必核对收款账户与合同主体一致。"))
    elif hit_any(d, ["中介", "个人账户", "经纪人"]) is True:
        out.append(("款项支付对象", "不通过",
                    "**款项付给中介或个人账户**风险极高。二手房交易应由买卖双方共同"
                    "通过银行资金监管完成，不要把钱直接转给中介或个人。"))
    else:
        out.append(("款项支付对象", "通过", "款项支付给合同相对方或监管账户。"))

    if unknown(f["mortgage_clear"]):
        out.append(("解押与过户衔接", "待补正",
                    "带押过户的解押安排未填。**解押与过户必须衔接，"
                    "否则可能出现钱付了、证没解、房没过户的僵局**。"))
    elif hit_any(f["mortgage_clear"],
                 ["已解押", "已解除", "已赎楼", "抵押已消", "已注销"]) is True:
        out.append(("解押与过户衔接", "通过", "抵押已解除或已注销，可正常过户。"))
    elif yes(f["mortgage_clear"]) or \
            hit_any(f["mortgage_clear"], ["解押", "赎楼", "带押", "抵押未解", "赎"]) is True:
        out.append(("解押与过户衔接", "有风险",
                    "涉及带押过户（填的是「%s」）。**要明确解押资金来源、"
                    "解押完成时间与过户时间**，并约定任一环节失败的违约责任；"
                    "解押资金建议同样走监管，不要直接给卖方赎楼。" % f["mortgage_clear"]))
    else:
        out.append(("解押与过户衔接", "通过", "无需带押过户或解押安排清晰。"))
    return out


# ------------------------------------------------------------------ 六 流程节点
def checks_stage(f):
    out = []
    stage = f["stage"]
    if not filled(stage):
        out.append(("当前交易进度", "待补正",
                    "当前处在哪个阶段未填。**不同阶段的风险点完全不同**："
                    "付定金后风险最大，过户后风险最小。"))
        return out
    hit = [lbl for lbl, ws in DEAL_STAGES if hit_any(stage, ws) is True]
    if not hit:
        out.append(("当前交易进度", "待补正", "进度描述不明确，用下面的词：%s。"
                    % "、".join(l[0] for l in DEAL_STAGES)))
    else:
        out.append(("当前交易进度", "通过", "当前处于：**%s**。" % "、".join(hit)))
        if hit_any(stage, ["定金", "意向金", "订金"]) is True:
            out.append(("定金阶段风险", "有风险",
                        "**已付定金/意向金是最脆弱的阶段**：房屋可能再被卖、被查封，"
                        "或卖方反悔。**此时应尽快网签并办理资金监管**，"
                        "定金退还规则必须在合同里写明。"))
        if hit_any(stage, ["网签", "备案"]) is False and hit_any(stage, ["过户"]) is True:
            out.append(("跳过网签风险", "有风险",
                        "**未网签就过户**属于高风险操作，容易出现一房二卖、"
                        "被查封无法登记等问题。**务必先网签备案再过户**。"))
        if hit_any(stage, ["交房", "交付"]) is True:
            out.append(("交房风险", "通过",
                        "进入交房阶段：注意**户口迁出、物业费结清、钥匙与门禁移交**，"
                        "并在合同中预留尾款至迁户完成。"))
    return out


# ------------------------------------------------------------------ 七 证据
EVIDENCE = [
    ("身份与产权证明", ["身份证", "房产证", "不动产权证", "房本", "产权登记", "查档"]),
    ("合同与付款凭证", ["合同", "协议", "收据", "转账", "定金", "首付", "发票"]),
    ("网签与过户凭证", ["网签", "备案", "过户", "不动产登记", "受理回执"]),
    ("资金监管记录", ["监管", "托管", "监管账户", "解付", "银行回单"]),
    ("披露与告知材料", ["告知书", "承诺", "保证", "说明书", "确认书"]),
    ("交房与结算材料", ["交房", "物业费", "水电费", "燃气费", "钥匙", "户口"]),
]


def has_content(s):
    for part in str(s or "").split("|"):
        if filled(part):
            return True
    return False


def checks_evidence(f):
    out = []
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    if not has_content(got):
        out.append(("证据总览", "待补正",
                    "已有证据既没勾选也没写清单。**二手房交易全程留痕**："
                    "查档结果、合同、付款凭证、网签与过户回执，缺一样都可能维权无门。"))
        return out
    for label, keys in EVIDENCE:
        hit = [k for k in keys if k in got]
        if hit:
            out.append((label, "通过",
                        "已具备：%s。**原件留存、复印件提交**，按时间顺序编号成册。" % "、".join(hit)))
        else:
            out.append((label, "有风险", "尚无%s材料，这类缺口会在出问题时让你被动。" % label))
    return out


def evidence_gap(f):
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    gaps = []
    if has_content(got):
        for label, keys in EVIDENCE:
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in EVIDENCE]
    if not yes(f["supervision"]):
        gaps.append("资金监管记录")
    if hit_any(f["stage"], ["定金", "首付", "订金"]) is True and \
            not any(k in got for k in ["合同", "协议"]):
        gaps.append("合同与付款凭证")
    seen = set()
    res = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            res.append(g)
    return res


EVID_FIX = {
    "身份与产权证明": "到不动产登记机构查档，核对权利人、共有情况、抵押与查封",
    "合同与付款凭证": "签署完整合同，付款一律留转账凭证与收据",
    "网签与过户凭证": "完成网签备案与过户，保留受理回执与新证",
    "资金监管记录": "通过银行做资金监管，保留监管协议与解付记录",
    "披露与告知材料": "把卖方告知的房屋状况、户口、租约写成书面条款",
    "交房与结算材料": "交房时结清物业水电燃气，抄表留档，钥匙门禁签收",
}


# ------------------------------------------------------------------ 路径
def path_steps(f):
    out = [("第 1 步（先查产权再谈钱）",
            "到不动产登记机构**查档**：确认权利人、共有情况、抵押与查封状态。"
            "**房本原件必须现场核对**。这一步不做，后面所有谈判都可能是空谈。"),
           ("第 2 步（核资格与贷款）",
            "核实限购资格（社保/个税/户籍/名下房产）与贷款审批可能性。"
            "**资格和贷款是签约的前提**，先确认再付定金。"),
           ("第 3 步（把风险写进合同）",
            "房屋已知瑕疵、户口迁出时间、租客情况、税费与中介费承担方，"
            "**全部写成书面条款并约定违约责任**，口头承诺一律无效。"),
           ("第 4 步（定金与首付安全）",
            "写清是「定金」还是「订金」、金额、退还与双倍返还规则；"
            "**大额款项走银行资金监管，不要直接付给卖方或中介个人账户**。"),
           ("第 5 步（网签备案与过户）",
            "**先网签备案再付款过户**，顺序不能反。带押过户要明确解押资金与时间衔接。"),
           ("第 6 步（交房与尾款）",
            "结清物业、水电、燃气、供暖费，抄表留档；"
            "**预留尾款至卖方户口迁出**，约定每日违约金。"),
           ("第 7 步（发现重大瑕疵）",
            "卖方刻意隐瞒漏水、结构、违建、凶宅或一房二卖的，"
            "**可主张解约、赔偿损失**；协商不成走投诉与诉讼。")]
    return out


def todo_list(f, results):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not yes(f["supervision"]):
        extra.append(("改用资金监管", "大额房款走银行监管，不直付卖方或中介个人"))
    if no(f["certificate"]):
        extra.append(("核验产权证原件", "房本原件 + 登记机构查档，双保险"))
    extra.append(("查档核实权利人", "确认有无共有人、抵押、查封"))
    extra.append(("把口头承诺写进合同", "户口迁出、房屋瑕疵、费用承担都要写条款和违约责任"))
    extra.append(("留存每笔付款凭证", "转账备注写房款，收据与合同对应"))
    if not filled(f["price"]):
        extra.append(("确认总价与费用清单", "要求中介出具书面费用清单"))
    seen = set()
    res = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        res.append((n, s))
    return res


# ------------------------------------------------------------------ 报告
SECTIONS = [
    "二、标的与权属核查",
    "三、合同条款风险",
    "四、税费与中介费测算",
    "五、贷款与购房资格",
    "六、资金安全与网签过户",
    "七、交易进度与节点风险",
    "八、证据清单与缺口",
]


def render(f, results, calc, steps, todos, today, gaps):
    L = []
    L.append("# 二手房买卖风险与费用核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 标的：%s" % (f["house"] or "未填"))
    L.append("- 总价：%s" % (money(parse_num(f["price"]))))
    L.append("- 当前进度：%s" % (f["stage"] or "未填"))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在明确高风险结构（未走资金监管/未核验产权/付款给个人），"
                 "先纠正再继续交易。**")
    elif calc["可测算"]:
        L.append("**判定：结构上没有致命问题，但已知费用约 %s（参考口径），"
                 "另有若干风险点需按第八段处理。**" % money(calc["已知合计"]))
    elif risk:
        L.append("**判定：有风险点需要提前处理，详见各段说明。**")
    else:
        L.append("**判定：采集表关键项未填，暂时给不出确定结论；"
                 "请把标的与产权、合同条款、资金安排填完再重跑。**"
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

    L.append("## 九、交易流程与风险控制排序")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 十、证据缺口速查")
    L.append("")
    if not gaps:
        L.append("当前填写的材料已较完整。")
    else:
        L.append("| 缺失类别 | 补法 |")
        L.append("|---|---|")
        for g in gaps[:12]:
            L.append("| %s | %s |" % (g, EVID_FIX.get(g, "按第九段操作卡补齐")))
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
             "契税、增值税等税费标准、限购政策与贷款条件，"
             "**以当地税务、住建、不动产登记与银行口径为准**。")
    L.append("- 报告金额为参考口径的**估算**，实际以合同约定、税务核算与银行核定为准。")
    L.append("- 不预测房屋市场价格涨跌，也不预测诉讼结果。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 本结果依通用规则整理，不替代专业意见，最终以主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps, calc):
    return {
        "核查日期": today.isoformat(),
        "总价": parse_num(f["price"]),
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "费用测算": {
            "可测算": calc["可测算"],
            "已知合计": calc["已知合计"],
            "项目": calc["项目"],
            "缺项": calc["缺项"],
        },
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "house": get_text(kv, ["房屋地址或项目名", "标的房屋", "房屋", "房产地址"]),
        "price": get_text(kv, ["总价", "成交价", "房屋总价", "价格"]),
        "ownership": get_text(kv, ["产权人是谁", "权利人", "产权人", "登记人"]),
        "coowner": get_text(kv, ["是否需要共有人签字", "是否有共有人", "共有人情况"]),
        "mortgage": get_text(kv, ["是否有抵押或查封", "有无抵押", "抵押查封情况"]),
        "certificate": get_text(kv, ["是否已核验产权证原件", "是否核验房本", "是否看过房本"]),
        "earnest": get_text(kv, ["是否已付定金或意向金", "是否已付定金", "定金情况"]),
        "subject_risk": get_text(kv, ["卖方告知的房屋状况", "房屋已知问题", "卖方披露的情况"]),
        "lease": get_text(kv, ["是否出租", "租赁情况", "是否有租客"]),
        "hukou": get_text(kv, ["卖方户口是否迁出", "户口迁出情况", "户口"]),
        "agent_fee": get_text(kv, ["中介服务费", "中介费", "佣金"]),
        "loan": get_text(kv, ["是否需要贷款", "是否按揭", "贷款安排"]),
        "qualify": get_text(kv, ["是否符合限购条件", "购房资格", "限购资格"]),
        "supervision": get_text(kv, ["是否采用资金监管", "资金监管", "是否走监管"]),
        "deposit_to_whom": get_text(kv, ["款项支付给谁", "付款对象", "收款方"]),
        "mortgage_clear": get_text(kv, ["解押与过户安排", "解押安排", "带押过户"]),
        "stage": get_text(kv, ["当前交易进度", "交易进度", "目前进行到哪一步"]),
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
    if not filled(f["house"]):
        missing.append("房屋地址或项目名")
    if not filled(f["price"]):
        missing.append("总价")
    if not filled(f["stage"]):
        missing.append("当前交易进度")

    calc = calc_cost(f)
    results = [
        ("标的与权属核查", checks_title(f)),
        ("合同条款风险", checks_contract(f)),
        ("税费与中介费测算", checks_cost(f, calc)),
        ("贷款与购房资格", checks_loan(f)),
        ("资金安全与网签过户", checks_money(f)),
        ("交易进度与节点风险", checks_stage(f)),
        ("证据清单与缺口", checks_evidence(f)),
    ]
    steps = path_steps(f)
    todos = todo_list(f, results)
    gaps = evidence_gap(f)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today, gaps, calc),
                         ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, calc, steps, todos, today, gaps)
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
