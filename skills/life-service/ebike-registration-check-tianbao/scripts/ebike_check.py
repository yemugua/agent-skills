#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""电动车上牌资格核查。

用法：
  python ebike_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python ebike_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta

VERSION = "1.0.0"

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "待补充", "请填", "例如", "示例", "如：", "填什么", "（", "(", "有/无"]

# ------------------------------------------------------------------ 解析
def norm(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("：", ":").replace("（", "(").replace("）", ")")
    s = s.replace("，", ",").replace("。", ".")
    s = re.sub(r"\s+", "", s)
    return s.strip()


def build_kv(text):
    """解析 markdown 表格行与 '字段：值' 行，保留表头行用于列定位。"""
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
        if w in v:
            return False
    return True


def yes(v):
    n = norm(v)
    return n in ("有", "是", "已经", "已", "已办理", "已上", "true", "yes")


def no(v):
    n = norm(v)
    return n in ("无", "否", "没有", "未", "未办", "未上", "false", "no")


def parse_num(s):
    if not s:
        return None
    s = str(s).replace(",", "").replace("，", "").replace("kg", "").replace("KG", "")
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


def fmt_money(x):
    if x is None:
        return "—"
    return "¥%s" % fmt_num(x)


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


# ------------------------------------------------------------------ 车种定性
LIMITS = [
    ("脚踏骑行能力", "必须有", None, "has_pedal"),
    ("最高设计车速", "≤ 25 km/h", 25, "speed"),
    ("装配完整的整车质量", "≤ 55 kg", 55, "weight"),
    ("电动机额定连续输出功率", "≤ 400 W", 400, "power"),
    ("蓄电池标称电压", "≤ 48 V", 48, "voltage"),
]

MOTOR_VEHICLE_WORDS = ["电动轻便摩托车", "电动摩托车", "轻便摩托", "机动车"]
NON_VEHICLE_WORDS = ["电动自行车"]


def classify(f):
    """返回 (定性, 依据串, 明细行, 超标项名列表)。"""
    rows = []
    fails = []
    for label, limtext, lim, key in LIMITS:
        raw = f[key]
        val = None
        if key == "has_pedal":
            if yes(raw):
                ok = True
                shown = "有"
            elif no(raw):
                ok = False
                shown = "无"
            else:
                ok = None
                shown = raw or "未填"
            rows.append((label, limtext, shown, "符合" if ok is True
                         else ("不符合" if ok is False else "待补正")))
            if ok is False:
                fails.append(label)
            continue
        val = parse_num(raw)
        if val is None:
            rows.append((label, limtext, raw or "未填", "待补正"))
            continue
        ok = val <= lim
        rows.append((label, limtext, fmt_num(val), "符合" if ok else "不符合"))
        if not ok:
            fails.append(label)

    # 合格证/铭牌写法兜底
    vtype = (f["vtype"] or "").strip()
    hint = ""
    for w in MOTOR_VEHICLE_WORDS:
        if w in vtype:
            hint = w
            break
    if not hint:
        for w in NON_VEHICLE_WORDS:
            if w in vtype:
                hint = w
                break

    if fails:
        qual = "机动车（电动摩托车/电动轻便摩托车）"
        detail = "、".join(fails)
        basis = "以下指标不符合 GB 17761《电动自行车安全技术规范》：%s" % detail
        if hint in MOTOR_VEHICLE_WORDS:
            basis += "；合格证/铭牌写的是「%s」，与按超标机动车处理一致" % hint
        basis += "。"
    else:
        qual = "非机动车（电动自行车）"
        detail = ""
        basis = "脚踏、最高设计车速、整车质量、电机额定连续功率、蓄电池标称电压五项全部符合 GB 17761。"
        if hint:
            basis += "；合格证/铭牌写的是「%s」，与之一致。" % hint
    return qual, basis, rows, fails


def motor_extra(f, qual):
    """机动车路径下的资质与保险核查。"""
    out = []
    if qual != "机动车（电动摩托车/电动轻便摩托车）":
        return out
    if yes(f["license_ce"]):
        lt = (f["licence_type"] or "").strip()
        out.append(("摩托车类驾驶证", "通过",
                    "已持有%s证，符合驾驶电动轻便摩托车/电动摩托车的资质要求。" % (lt or "摩托车类")))
    else:
        out.append(("摩托车类驾驶证", "不通过",
                    "未填或填写为「%s」。超标车按机动车管理，无 D/E 驾驶证即属**无证驾驶**，"
                    "上路会被罚款、扣车；请先考取 D 或 E 证。"
                    % (f["license_ce"] or "未填")))
    if yes(f["insured"]):
        out.append(("交强险", "通过", "已投保机动车交通事故责任强制保险。"))
    else:
        out.append(("交强险", "不通过",
                    "未投保交强险。机动车上路前必须投保交强险，"
                    "未投保的会被扣车并处罚；请到保险公司或 12123 办理。"))
    a16 = f["age16"]
    a18 = f["age18"]
    if no(a16):
        out.append(("驾驶人年龄", "不通过",
                    "未满 16 周岁不得驾驶电动自行车；驾驶摩托车类另有法定年龄门槛，"
                    "未达年龄不得申领相应驾驶证。"))
    elif no(a18):
        out.append(("驾驶人年龄", "有风险",
                    "已满 16 周岁未满 18 周岁：可骑电动自行车，但电动摩托车一般需满 18 周岁，"
                    "请按当地口径确认能否驾驶机动车类超标车。"))
    elif yes(a16):
        out.append(("驾驶人年龄", "通过", "已达可驾驶年龄。"))
    else:
        out.append(("驾驶人年龄", "待补正", "是否年满 16 周岁未填，无法判断是否允许骑行。"))
    return out


# ------------------------------------------------------------------ 材料
def checks_material(f):
    out = []

    def have(v, ok_words=("有",), bad_words=("无", "丢失", "缺", "遗失")):
        n = norm(v)
        if not n:
            return "待补正"
        for b in bad_words:
            if b in n:
                return "缺失"
        for o in ok_words:
            if o in n:
                return "已备"
        return "待补正"

    rows = [
        ("车主身份证明", f["id"]),
        ("购车发票或销售凭证", f["invoice"]),
        ("产品合格证（带CCC）", f["cert"]),
        ("车辆（现场查验/拓号）", f["vehicle"]),
        ("居住证/暂住登记", f["residence"]),
        ("委托书（代办时）", f["proxy"]),
    ]
    for label, v in rows:
        st = have(v)
        if st == "已备":
            out.append((label, "通过", "已备齐。"))
        elif st == "缺失":
            if label == "购车发票或销售凭证":
                out.append((label, "不通过",
                            "发票缺失。可要求销售方补开**销售证明/购车情况说明 + 承诺书（盖章）**；"
                            "销售方拒不配合的，向市场监管（12315）反映。**不要买代开发票**，"
                            "虚假材料一旦被查登记可能被撤销。"))
            elif label == "产品合格证（带CCC）":
                out.append((label, "不通过",
                            "合格证缺失。联系生产厂家或经销商按车架号补办；"
                            "完全无合格证的属三无产品，向市场监管（12315）反映。"))
            elif label == "居住证/暂住登记":
                out.append((label, "待补正",
                            "异地户籍或异地购车办理时，部分地区要求居住证或暂住登记凭证。"
                            "此项各地要求不同，以当地车管所口径为准；本地户籍一般不需要。"))
            else:
                out.append((label, "不通过", "%s缺失，需补齐后才能办理登记。" % label))
        else:
            tip = {
                "居住证/暂住登记": "异地户籍或异地购车办理时，部分地区要求居住证或暂住登记凭证，以当地交管口径为准。",
                "委托书（代办时）": "委托门店或他人代办时需要委托书，本人办理则不需要。",
            }.get(label, "未填，需补齐。")
            out.append((label, "待补正", tip))
    return out


def checks_block(f, qual):
    """卡点分支：改装 / 二手车 / 车架号 / 合格证型号。"""
    out = []

    if yes(f["modified"]):
        items = (f["mod_items"] or "改装项目未说明").strip()
        out.append(("车辆已改装", "不通过",
                    "改装项目：%s。**改装车（解限速、加电池、加后座/儿童座椅、装遮阳伞雨棚、"
                    "换电机车架）通常不予登记**——原因是改装改变了车种定性。"
                    "请先到车管所/销售网点**恢复原状**，再重新申请现场查验。"
                    "改装车上路被查会被责令恢复原状并处罚，发生事故后保险也可能拒赔。" % items))
    elif no(f["modified"]):
        out.append(("车辆已改装", "通过", "车辆未改装，符合登记查验要求。"))
    else:
        out.append(("车辆已改装", "待补正",
                    "是否改装过未填。有过解限速、加电池、加后座、装遮阳伞的一律先恢复原状再办。"))

    if yes(f["used_car"]):
        tr = (f["transfer"] or "").strip()
        out.append(("二手车转让手续", "有风险",
                    "二手车需双方共同到场或持转让协议办理；当前手续为「%s」。"
                    "原车主失联的，先在交管 12123 查车辆状态（是否有抵押、查封、未处理违法），"
                    "再按当地二手车辆过户流程办理；仍办不成的向 12345 与市场监管咨询，"
                    "必要时通过民事诉讼确认车辆归属。"
                    "务必留存转让协议、转账凭证与聊天记录。" % (tr or "未填")))
    elif no(f["used_car"]):
        out.append(("二手车转让手续", "通过", "非二手车，无需转让手续。"))
    else:
        out.append(("二手车转让手续", "待补正", "是否为二手车未填，二手车需双方到场或转让协议。"))

    if f["cert_match"]:
        n = norm(f["cert_match"])
        if "不一致" in n or "不符" in n:
            out.append(("合格证型号与实车一致", "不通过",
                        "合格证型号与实车不一致（套牌/错配合格证）。**不要拿去上牌**，"
                        "现场查验会被驳回，且涉嫌提供虚假材料；请向销售方换发正确合格证并向 12315 投诉。"))
        elif "一致" in n:
            out.append(("合格证型号与实车一致", "通过", "合格证型号与实车一致。"))
        else:
            out.append(("合格证型号与实车一致", "待补正", "未填，请核对合格证型号与车架号、铭牌是否一致。"))

    fc = f["frame_clear"]
    if no(fc) or "磨损" in norm(fc) or "缺失" in norm(fc) or "磨" in norm(fc):
        out.append(("车架号可辨", "不通过",
                    "车架号（车辆识别代号）磨损/缺失/无法辨认的，**不予登记**。"
                    "需到车管所或指定维修企业补打车架号、补装铭牌后再办。"))
    elif yes(fc) or "清晰" in norm(fc) or "完整" in norm(fc):
        out.append(("车架号可辨", "通过", "车架号钢印清晰可辨；铭牌完整。"))
    else:
        out.append(("车架号可辨", "待补正", "车架号是否清晰未填，打刻不清、被打磨过的车不予登记。"))

    np_ = f["nameplate"]
    if "缺失" in norm(np_) or "脱落" in norm(np_) or no(np_):
        out.append(("铭牌完整", "不通过",
                    "车身铭牌脱落或缺失的，需补装/补打铭牌后再申请登记，"
                    "否则车辆识别信息不完整。"))
    elif filled(np_):
        out.append(("铭牌完整", "通过", "车身铭牌完整。"))
    return out


def checks_transition(f, qual, today):
    out = []
    if qual != "机动车（电动摩托车/电动轻便摩托车）":
        out.append(("超标车过渡期", "不适用", "车辆属非机动车，不涉及超标车过渡期。"))
        return out
    tr = f["transition"]
    if not filled(tr) or norm(tr) in ("不清楚", "不知道", "待确认", "未知"):
        out.append(("当地是否设过渡期", "待补正",
                    "未填。**过渡期由省级/市级设定，期限各地不同且多数已到期或临近到期，"
                    "本工具不内置任何城市的截止日**。请到当地交警公众号或车管所核实。"))
        return out
    if no(tr):
        out.append(("当地是否设过渡期", "通过", "当地未设超标车过渡期，超标车直接按机动车管理。"))
        return out
    if not yes(tr):
        out.append(("当地是否设过渡期", "待补正", "填写不明确，请填「是 / 否 / 不清楚」。"))
        return out

    d = parse_date(f["transition_end"])
    if d is None:
        out.append(("过渡期截止日", "待补正",
                    "已确认当地设过渡期，但截止日未填。请到当地交警公众号或车管所查到原文日期；"
                    "在核实之前按**已到期**作最坏情况准备（尽快置换合规车或考 D/E 证上正规机动车牌）。"))
        return out
    left = (d - today).days
    out.append(("过渡期截止日", "有风险" if left < 0 else "通过",
                "截止日 %s，距今天%s。"
                % (d.isoformat(), ("已过期 %d 天，到期后不得上路" % -left) if left < 0
                   else ("还剩 %d 天，到期前必须置换或转机动车牌" % left))))
    return out


def checks_plate(f, qual):
    out = []
    pd = f["plate_done"]
    if not filled(pd):
        out.append(("号牌办理状态", "待补正", "未填。未上牌即无牌上路，会被处罚、扣车。"))
        return out
    n = norm(pd)
    if "非机动车" in n or "电动自行车" in n:
        out.append(("号牌办理状态", "通过", "已上电动自行车（非机动车）号牌。"))
    elif "机动车" in n:
        out.append(("号牌办理状态", "通过", "已上机动车号牌（对应超标车定性）。"))
    elif "临时" in n:
        out.append(("号牌办理状态", "有风险",
                    "已上过渡期临时号牌。临时牌到期即失效，到期前必须置换或按机动车办理，别骑到被查才知道。"))
    elif no(pd) or "未" in n:
        out.append(("号牌办理状态", "不通过",
                    "尚未上牌。无牌上路会被警告或罚款、责令补办登记，超标车还会按未悬挂机动车号牌处罚并扣车。"))
    else:
        out.append(("号牌办理状态", "待补正", "填写不明确（未办 / 已上非机动车牌 / 已上机动车牌 / 已上临时号牌）。"))

    pu = f["punished"]
    if yes(pu) or "被" in norm(pu) and "警告" in norm(pu):
        out.append(("此前被查处", "有风险",
                    "已被查处过（%s）。请收好**处罚决定书**，上面载明处罚依据与救济期限："
                    "一般可自知道行政行为之日起 60 日内申请行政复议、6 个月内提起行政诉讼。"
                    "对车种认定不服的，也可在复议/诉讼中一并提出。" % (pu or "未填")))
    return out


def path_order(f, qual):
    if qual != "机动车（电动摩托车/电动轻便摩托车）":
        steps = [
            ("第 1 步", "核对合格证五项指标：脚踏、车速、整车质量、电机功率、电池电压，拍照存档"),
            ("第 2 步", "恢复原状：拆除改装（解限速、加电池、加后座、遮阳伞、雨棚）"),
            ("第 3 步", "备齐身份证、购车发票或销售证明、带 CCC 的合格证，检查车架号钢印是否清晰"),
            ("第 4 步", "选渠道办理：车管所窗口 / 有资质的带牌销售网点 / 交管 12123 线上申请"),
            ("第 5 步", "现场查验、拓号、装牌、领行驶证；办完记住戴头盔、走非机动车道、禁进楼入户充电"),
        ]
    else:
        steps = [
            ("第 1 步", "先确认自己有 D 或 E 驾驶证；没有就先报名考取，无证上路属无证驾驶"),
            ("第 2 步", "投保机动车交通事故责任强制保险（交强险）"),
            ("第 3 步", "核实超标车过渡期：当地交警公众号 / 车管所 / 12123 查原文日期"),
            ("第 4 步", "带身份证、发票、合格证、车辆、保单、驾驶证到车管所上机动车号牌"),
            ("第 5 步", "恢复原状并留存证据；与销售就'包上牌'承诺产生纠纷的走 12315 / 12345 / 诉讼"),
        ]
    return steps


def todo_list(f, results, qual):
    todos = []
    for _title, rows in results:
        for row in rows:
            name, state = row[0], row[1]
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not filled(f["city"]):
        extra.append(("补填城市", "过渡期、限行、材料与工本费全按城市走，先填常住城市"))
    if qual != "机动车（电动摩托车/电动轻便摩托车）" and not yes(f["modified"]):
        extra.append(("自查改装", "确认有没有解限速、加电池、加后座、装遮阳伞，有就先恢复原状"))
    if qual == "机动车（电动摩托车/电动轻便摩托车）":
        extra.append(("考 D/E 证", "超标车按机动车管理，无 D/E 证属无证驾驶，先解决资质"))
        extra.append(("买交强险", "机动车上路前必须投保交强险"))
    if yes(f["modified"]):
        extra.append(("恢复原状", "到车管所或销售网点拆掉改装件后再申请查验"))
    if not filled(f["evidence"]):
        extra.append(("补证据清单", "合格证照片、发票、聊天记录、转账凭证、车辆照片，能存几份存几份"))
    if yes(f["sale_dispute"]):
        extra.append(("纠纷处理", "按 商家交涉 → 12315/12345 → 仲裁诉讼 的顺位推进"))
    seen = set()
    out = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        out.append((n, s))
    return out


# ------------------------------------------------------------------ 报告
def render(f, results, qual, basis, rows, steps, todos, today):
    L = []
    A = L.append

    A("# 电动车上牌资格核查报告")
    A("")
    A("> 生成日期：%s；脚本版本 v%s；车主：%s；常住城市：%s" % (
        today.isoformat(), VERSION, f["owner"] or "未填", f["city"] or "未填"))
    A("")

    bad = [r for _t, rs in results for r in rs if r[1] == "不通过"]
    risk = [r for _t, rs in results for r in rs if r[1] == "有风险"]
    todo = [r for _t, rs in results for r in rs if r[1] == "待补正"]

    A("## 一、结论摘要")
    A("")
    if bad:
        A("**判定：存在硬卡点，暂不能上牌（不通过）**。")
    elif risk:
        A("**判定：可办但存在风险点，需先处理（有风险）**。")
    elif todo:
        A("**判定：材料还差几项（待补正）**。")
    else:
        A("**判定：未发现明显卡点，按第 8 段推进即可**。")
    A("")
    A("| 项 | 数量 |")
    A("|---|---|")
    A("| 不通过 | %d |" % len(bad))
    A("| 有风险 | %d |" % len(risk))
    A("| 待补正 | %d |" % len(todo))
    A("")
    A("- **车种定性**：%s——%s" % (qual, basis))
    for r0 in (bad + risk)[:6]:
        A("- **%s**：%s" % (r0[0], str(r0[2]).replace("**", "")))
    A("")

    titles = ["二、车种定性（非机动车还是机动车）", "三、能不能上牌（材料齐备核查）",
              "四、卡点分支（改装/二手车/车架号/合格证）", "五、超标车与过渡期",
              "六、资质、保险与号牌状态"]
    for (title, rr), t in zip(results[:5], titles):
        if not rr:
            continue
        A("## %s" % t)
        A("")
        A("| 核查项 | 判定 | 说明 |")
        A("|---|---|---|")
        for rr2 in rr:
            A("| %s | %s | %s |" % (rr2[0], rr2[1], str(rr2[2]).replace("|", " ")))
        A("")

    A("## 七、当地规则查询入口与办理路径")
    A("")
    A("| 想查什么 | 去哪查 |")
    A("|---|---|")
    A("| 本地过渡期与临时号牌政策 | 当地交警微信公众号 / 当地人民政府官网公告 |")
    A("| 材料清单与工本费 | 车管所窗口 / 交管 12123 办事指南 |")
    A("| 带牌销售网点、车管所地址 | 交管 12123 / 当地交警公众号 |")
    A("| 异地户籍是否需居住证 | 车管所窗口（以当地口径为准） |")
    A("| 限行区域与载人年龄规定 | 当地交警公告 |")
    A("")
    for step, txt in steps:
        A("- **%s**：%s" % (step, txt))
    A("")

    A("## 八、待办补正动作")
    A("")
    if not todos:
        A("当前未发现必须补正的事项。")
    else:
        A("| 动作 | 状态 |")
        A("|---|---|")
        for n, s in todos:
            A("| %s | %s |" % (n, s))
    A("")

    A("## 九、边界与纪律")
    A("")
    A("- 本结果依 GB 17761《电动自行车安全技术规范》与机动车登记相关**通用规则**整理，**不替代主管部门认定**。")
    A("- 车种定性最终以**合格证标注与当地公安交管部门认定**为准；本工具只做初步判定。")
    A("- 登记材料口径、过渡期期限、载人年龄限制、带牌销售范围、工本费等**各地差异很大，"
      "一律以当地公安交管部门最新公告与车管所现场要求为准**。")
    A("- 不承诺一定能上牌、不代办登记、不代开证明、不买代开发票。")
    A("- 不预测行政处罚金额与结果；对认定不服的，60 日内申请行政复议、6 个月内提起行政诉讼。")
    A("- **未填的一律不算通过**，只按已填内容判断。")
    A("")
    A("本结果依通用规则整理，不替代专业意见，最终以主管部门/司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, qual, todos, today):
    return {
        "版本": VERSION,
        "生成日期": today.isoformat(),
        "常住城市": f["city"],
        "车种定性": qual,
        "定性依据": f.get("basis", ""),
        "结论": f.get("verdict", "待补正"),
        "结论明细": {
            "不通过": [r[0] for _t, rs in results for r in rs if r[1] == "不通过"],
            "有风险": [r[0] for _t, rs in results for r in rs if r[1] == "有风险"],
            "待补正": [r[0] for _t, rs in results for r in rs if r[1] == "待补正"],
        },
        "风险项": [r[0] for _t, rs in results for r in rs if r[1] == "有风险"],
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_report(path, base=None):
    """读采集表 → 返回 (报告正文, 结构化元数据)。读不了或关键信息缺失时返回 (None, 提示串)。"""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:
        return None, "读不了文件：%s" % e

    if base is None:
        base = date.today()

    kv = build_kv(text)
    today = base

    f = {
        "owner": get_text(kv, ["车主姓名", "姓名"]),
        "city": get_text(kv, ["常住城市", "所在城市", "城市"]),
        "proxy": get_text(kv, ["代办方式", "是否本人办理"]),
        "residence": get_text(kv, ["是否需要异地户籍材料", "居住证", "居住证或暂住登记"]),
        "app12123": get_text(kv, ["是否已安装并登录交管12123"]),
        "has_pedal": get_text(kv, ["是否有脚踏骑行能力", "脚踏", "有无脚踏"]),
        "speed": get_text(kv, ["最高设计车速", "最高车速", "车速"]),
        "weight": get_text(kv, ["整车质量", "装配完整的整车质量"]),
        "power": get_text(kv, ["电动机额定连续输出功率", "电机功率", "额定连续输出功率"]),
        "voltage": get_text(kv, ["蓄电池标称电压", "电池电压", "标称电压"]),
        "has_ccc": get_text(kv, ["有无 CCC 认证标识", "CCC"]),
        "vtype": get_text(kv, ["车辆类型", "铭牌类型", "合格证车辆类型"]),
        "buy_date": get_text(kv, ["购车日期", "购买日期"]),
        "invoice": get_text(kv, ["购车发票", "发票"]),
        "invoice_name": get_text(kv, ["发票品名"]),
        "cert": get_text(kv, ["产品合格证", "合格证"]),
        "cert_match": get_text(kv, ["合格证型号与实车是否一致", "合格证型号与实车"]),
        "modified": get_text(kv, ["是否改装过", "是否改装"]),
        "mod_items": get_text(kv, ["改装项目", "改装情况"]),
        "used_car": get_text(kv, ["是否为二手车"]),
        "transfer": get_text(kv, ["二手车转让手续"]),
        "frame_no": get_text(kv, ["车架号（车辆识别代号）", "车辆识别代号"]),
        "frame_clear": get_text(kv, ["车架号是否清晰可辨", "车架号清晰度"]),
        "nameplate": get_text(kv, ["铭牌是否完整", "铭牌"]),
        "license_ce": get_text(kv, ["是否已取得摩托车类驾驶证", "摩托车类驾驶证", "有无摩托车驾照"]),
        "licence_type": get_text(kv, ["驾驶证准驾车型", "准驾车型"]),
        "insured": get_text(kv, ["是否已投保交强险", "交强险"]),
        "age16": get_text(kv, ["是否已年满 16 周岁", "是否年满16周岁"]),
        "age18": get_text(kv, ["是否已年满 18 周岁", "是否年满18周岁"]),
        "channel": get_text(kv, ["拟办理渠道", "办理渠道"]),
        "transition": get_text(kv, ["当地是否设过渡期（临时号牌）", "当地是否对超标车设过渡期", "当地是否设过渡期"]),
        "transition_end": get_text(kv, ["过渡期截止日"]),
        "plate_done": get_text(kv, ["号牌是否已办", "号牌办理状态"]),
        "punished": get_text(kv, ["是否已被查处过", "查处情况"]),
        "sale_dispute": get_text(kv, ["与销售的纠纷", "销售纠纷"]),
        "evidence": get_text(kv, ["已有证据清单", "证据清单"]),
    }
    f["id"] = get_text(kv, ["车主身份证明", "身份证"])
    f["vehicle"] = get_text(kv, ["车辆（现场查验/拓号）", "车辆本身"])

    if not any([filled(f[k]) for k in ("speed", "weight", "power", "voltage",
                                       "has_pedal", "vtype", "buy_date")]):
        return None, ("未解析到关键信息。至少填写「最高设计车速」或「是否有脚踏骑行能力」"
                      "中的一项，否则无法判定车种。")

    qual, basis, crow, fails = classify(f)
    f["basis"] = basis

    results = [
        ("车种定性", [("车种定性", qual, basis)] + crow),
        ("材料齐备核查", checks_material(f)),
        ("卡点分支", checks_block(f, qual)),
        ("超标车与过渡期", checks_transition(f, qual, today)),
        ("资质、保险与号牌状态", (motor_extra(f, qual)
         + checks_plate(f, qual) or
         [("资质、保险与号牌状态", "不适用", "车辆属非机动车，不需摩托车类驾驶证与交强险。")])),
    ]
    steps = path_order(f, qual)
    todos = todo_list(f, results, qual)

    bad = [r for _t, rs in results for r in rs if r[1] == "不通过"]
    risk = [r for _t, rs in results for r in rs if r[1] == "有风险"]
    todo = [r for _t, rs in results for r in rs if r[1] == "待补正"]
    if bad:
        f["verdict"] = "不通过"
    elif risk:
        f["verdict"] = "有风险"
    elif todo:
        f["verdict"] = "待补正"
    else:
        f["verdict"] = "通过"
    f["risk_items"] = [r[0] for r in risk]

    rep = render(f, results, qual, basis, crow, steps, todos, today)
    meta = to_json(f, results, qual, todos, today)
    return rep, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rep, meta = build_report(args.input, base_date(args.base))

    if rep is None:
        sys.stdout.write("%s\n" % meta)
        return 2

    if args.json:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(rep)
        sys.stdout.write("已写出 %s\n" % args.out)
    else:
        sys.stdout.write(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
