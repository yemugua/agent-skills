#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""停车收费纠纷核查。

用法：
  python parking_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python parking_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta

UNFILLED_MARK = re.compile(r"[/／]")  # 值里出现斜杠 = 是选项提示串，不是答案
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "（", "("]


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
    """解析 markdown 表格行与 '字段：值' 行。"""
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
    return n in ("有", "是", "已经", "已", "已完成", "已调取", "true", "yes")


def no(v):
    n = norm(v)
    return n in ("无", "否", "没有", "未", "未做", "false", "no")


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知")


def parse_num(s):
    if not s:
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
GOV_PRICING = ["道路", "路边", "市政", "医院", "交通枢纽", "车站", "机场", "公立"]
MARKET = ["小区", "商场", "写字楼", "商业", "酒店", "园区"]


def pricing_type(scene):
    s = scene or ""
    for k in GOV_PRICING:
        if k in s:
            return ("政府定价或政府指导价",
                    "该场景多为价格主管部门制定标准的情形，收费主体必须按公布标准执行，"
                    "不得自行上浮。具体是否列入当地定价目录，以当地价格主管部门公布为准。")
    for k in MARKET:
        if k in s:
            return ("市场调节价",
                    "由经营者（小区为业主共同决定或合同约定）自主确定，但仍必须明码标价、"
                    "提前公示，不得价格欺诈或串通涨价。")
    return ("需确认", "场景未填或无法识别，请先确认停车场所性质，再判断适用哪种定价。")


def checks_pricing(f):
    out = []
    ptype, why = pricing_type(f["scene"])
    out.append(("定价性质", ptype, why))
    if not filled(f["scene"]):
        out.append(("停车场景", "待补正", "场景是判断定价性质的前提，必须填写。"))
    # 超标准
    paid, std = f["paid"], f["std"]
    if paid is not None and std is not None:
        if paid > std + 1e-6:
            out.append(("超标准收费", "有风险",
                        "实缴 %s 元高于公示标准 %s 元，差额 %s 元可主张退还，"
                        "并可向市场监管部门举报价格违法。"
                        % (fmt_num(paid), fmt_num(std), fmt_num(paid - std))))
        else:
            out.append(("实缴与公示标准", "通过",
                        "实缴 %s 元未超过公示标准 %s 元。" % (fmt_num(paid), fmt_num(std))))
    elif paid is not None:
        out.append(("公示标准", "待补正", "已填实缴金额但缺公示标准，无法判断是否超收。"))
    return out, ptype


def checks_posting(f):
    out = []
    if yes(f["has_board"]):
        out.append(("收费公示牌", "通过", "现场有公示牌，是主张与维权的基础证据；务必拍下全景留存。"))
        if yes(f["board_tel"]):
            out.append(("公示含投诉电话", "通过", "公示内容含投诉电话，符合明码标价要求。"))
        elif no(f["board_tel"]):
            out.append(("公示含投诉电话", "有风险",
                        "公示牌未标注投诉电话，明码标价内容不完整，可作为举报的辅助理由。"))
        else:
            out.append(("公示含投诉电话", "待补正", "未填，请核对公示牌是否载明投诉电话。"))
    elif no(f["has_board"]):
        out.append(("收费公示牌", "不通过",
                    "现场无收费公示牌即属未明码标价，是价格违法行为；"
                    "请立即补拍现场照片（含出入口与收费处全景）并固定支付凭证。"))
    else:
        out.append(("收费公示牌", "待补正",
                    "未填，这是本核查最关键的一项——有无公示牌直接决定能不能主张超收。"))
    return out


def checks_community(f):
    out = []
    if "小区" not in (f["scene"] or ""):
        return out
    if not filled(f["space_type"]):
        out.append(("车位性质", "待补正", "小区场景必须填车位性质，才能判断涨价与收益归属。"))
        return out
    st = f["space_type"]
    if "共有" in st or "公共" in st:
        out.append(("车位性质", "有风险",
                    "占用业主共有的道路或者其他场地设置的车位属于**业主共有**，"
                    "收益扣除合理成本后归业主共有，物业无权单方面定价。"))
    elif "人防" in st:
        out.append(("车位性质", "有风险",
                    "人防车位不得买卖所有权；所谓'长期租赁''转让使用权'变相买卖存在效力风险，"
                    "租期与收益归属按当地规定与合同约定判断。"))
    elif "产权" in st:
        out.append(("车位性质", "通过",
                    "规划内产权车位，归属按出售、附赠或出租的约定确定；"
                    "购买时应核实能否办理不动产权属登记。"))
    else:
        out.append(("车位性质", "待补正", "车位性质填写不明确，请写明产权/人防/共有/租赁。"))

    if filled(f["vote"]) and no(f["vote"]):
        out.append(("涨价程序", "不通过",
                    "共有部分停车收费标准的调整属于业主共同决定事项，"
                    "未经业主共同决定的涨价对你不当然产生约束力；可要求出示业主大会决议与公示。"))
    elif yes(f["vote"]):
        if yes(f["vote_public"]):
            out.append(("涨价程序", "通过", "已经业主共同决定并公示，程序完整。"))
        else:
            out.append(("涨价程序", "有风险",
                        "已表决但未见公示，可要求公开决议内容、表决票统计与执行时间。"))
    elif filled(f["vote"]):
        out.append(("涨价程序", "待补正", "表决情况填写不明确。"))

    old, new = f["rent_old"], f["rent_new"]
    if old is not None and new is not None and new > old + 1e-6:
        pct = (new - old) / old * 100 if old else 0
        out.append(("涨幅", "有风险",
                    "月租由 %s 元涨到 %s 元，涨幅约 %s%%；涨幅明显且程序不合规的，"
                    "可主张对己不生效并要求按原标准执行。"
                    % (fmt_num(old), fmt_num(new), fmt_num(pct))))
    return out


def checks_damage(f):
    out = []
    if not (filled(f["damaged"]) and yes(f["damaged"])):
        return out
    dmg = f["damage_type"] or "未说明"
    if yes(f["ticket"]):
        out.append(("停车凭证", "通过",
                    "有停车凭证（入场记录/支付凭证/发票/月租卡），可证明车辆停放在该场——这是索赔的前提。"))
    elif no(f["ticket"]):
        out.append(("停车凭证", "不通过",
                    "无停车凭证，难以证明车辆在该场停放；请补找支付记录、月租合同、道闸记录与聊天记录。"))
    else:
        out.append(("停车凭证", "待补正", "是否持有停车凭证未填。"))

    cam = f["camera"]
    if yes(cam) or "已调" in (cam or ""):
        out.append(("监控保全", "通过", "监控已调取并保全，是认定责任的关键证据。"))
    elif "超过" in (cam or "") or "覆盖" in (cam or ""):
        out.append(("监控保全", "不通过",
                    "监控已超过保存期被覆盖，取证链条断裂，主张难度显著上升；"
                    "可改从出入记录、支付记录、巡查记录与证人证言补强。"))
    elif no(cam) or "未调" in (cam or "") or "未保全" in (cam or ""):
        out.append(("监控保全", "不通过",
                    "**监控留存期通常只有 7~30 天，这是最紧急的一步**——"
                    "请立即书面要求场方保全并复制监控，同时报警。"))
    else:
        out.append(("监控保全", "待补正", "是否已调取监控未填。"))

    if yes(f["police"]):
        out.append(("报警记录", "通过", "已报警并取得记录，有利于后续索赔与保险理赔。"))
    elif no(f["police"]):
        out.append(("报警记录", "有风险",
                    "未报警。刮擦、砸窗、整车被盗均建议报警留痕，报案记录是重要证据。"))

    if yes(f["claim"]):
        out.append(("索赔主张", "通过",
                    "已向场方书面提出索赔（情形：%s）。"
                    "场方以'只提供场地、不负责保管'抗辩的，该格式条款不能当然免除其安全保障义务。" % dmg))
    else:
        out.append(("索赔主张", "待补正",
                    "尚未书面索赔（是否已提出：%s）。请向场方提交书面索赔函并索要回执，"
                    "写明时间、地点、损害、金额与期限。" % (f["claim"] or "未填")))
    return out


def checks_penalty(f, today):
    out = []
    if filled(f["ticket_penalty"]) and yes(f["ticket_penalty"]):
        pb = f["penalty_body"] or ""
        if filled(pb) and ("物业" in pb or "商场" in pb):
            out.append(("处罚主体", "有风险",
                        "物业、商场等不具有行政处罚权，其张贴的'罚款通知''锁车费'不当然具有法律效力，"
                        "可要求其出具执法依据。"))
        if yes(f["towed"]):
            if yes(f["tow_fee"]) or (f["tow_fee_amt"] is not None and f["tow_fee_amt"] > 0):
                amt = f["tow_fee_amt"]
                out.append(("拖车费", "不通过",
                            "因违法停车被拖移的，不得向当事人收取拖车费；"
                            "被收取 %s 元的，可要求出具收费依据并向 12345、市场监管反映。"
                            % (fmt_num(amt) if amt is not None else "相关")))
            elif no(f["tow_fee"]):
                out.append(("拖车费", "通过", "未被收取拖车费，符合规定。"))
        d = parse_date(f["penalty_date"])
        if d:
            left = (d + timedelta(days=60) - today).days
            out.append(("行政复议时限", "有风险" if left < 0 else "通过",
                        "自 %s 起算，60 日申请期限%s。"
                        % (d.isoformat(), ("已过 %d 天" % -left) if left < 0 else ("还剩 %d 天" % left))))
            left2 = (d + timedelta(days=180) - today).days
            out.append(("行政诉讼时限", "有风险" if left2 < 0 else "通过",
                        "6 个月起诉期限%s。" % (("已过 %d 天" % -left2) if left2 < 0 else ("还剩 %d 天" % left2))))
        else:
            out.append(("处罚日期", "待补正", "未填收到处罚决定的日期，无法计算复议与诉讼时限。"))
    return out


def path_order(f):
    steps = []
    if "小区" in (f["scene"] or ""):
        steps = [
            ("第 1 步", "向物业与业委会书面索要收费依据：业主大会决议、表决统计、公示照片、收费备案或定价说明"),
            ("第 2 步", "联名向业主委员会提出，要求纠正或召开业主大会；同步要求公开共有部分收益账目"),
            ("第 3 步", "向街道（乡镇）/ 社区与住建（物业管理）主管部门反映，请求协调与监督"),
            ("第 4 步", "通过 12345 派单；涉及未明码标价、超标准收费的同时向市场监管（12315）举报"),
            ("第 5 步", "涉及收益返还或赔偿的，经业主共同决定后依法主张，必要时诉讼"),
        ]
    elif any(k in (f["scene"] or "") for k in GOV_PRICING):
        steps = [
            ("第 1 步", "固定证据：公示牌全景、缴费页面、支付凭证、发票、入场与出场记录"),
            ("第 2 步", "向收费主体（或其上级运营公司）书面要求退还超收部分并说明依据"),
            ("第 3 步", "向市场监督管理部门举报价格违法，同步 12345 反映"),
            ("第 4 步", "涉及违停处罚争议的，另行申请行政复议或提起行政诉讼"),
            ("第 5 步", "多人被超收的集中投诉，效果明显好于单人"),
        ]
    else:
        steps = [
            ("第 1 步", "固定证据：公示牌与缴费记录；车辆受损的立即保全监控并报警"),
            ("第 2 步", "向场方（商场管理方 / 停车运营公司）书面提出退还或赔偿，索要回执"),
            ("第 3 步", "向 12345 与 12315 反映；价格问题由市场监管处理"),
            ("第 4 步", "涉车损的，先走保险理赔不影响另行向场方主张"),
            ("第 5 步", "协商不成的，就赔偿争议提起民事诉讼（诉讼时效 3 年）"),
        ]
    return steps


def todo_list(f, results):
    todos = []
    for _, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not yes(f["has_board"]):
        extra.append(("补拍现场", "拍摄出入口、收费岗亭、缴费处全景，证明未明码标价"))
    if yes(f["damaged"]) and not yes(f["camera"]):
        extra.append(("保全监控", "立即书面要求场方保全监控，留存期通常仅 7~30 天"))
    if yes(f["damaged"]) and not yes(f["police"]):
        extra.append(("报警留痕", "刮擦/砸窗/被盗均建议报警，取得报案回执"))
    if "小区" in (f["scene"] or ""):
        extra.append(("索要决议", "要求物业或业委会出示业主大会决议、表决统计与公示记录"))
        extra.append(("公开收益", "要求公开共有部分停车收益与使用情况"))
    if yes(f["ticket_penalty"]):
        extra.append(("复议倒计时", "对处罚不服的，60 日内申请行政复议、6 个月内提起行政诉讼"))
    seen = set()
    allt = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        allt.append((n, s))
    return allt


# ------------------------------------------------------------------ 报告
def render(f, results, ptype, steps, todos, today):
    L = []
    L.append("# 停车收费纠纷核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 停车场景：%s" % (f["scene"] or "未填"))
    L.append("- 收费主体：%s" % (f["subject"] or "未填"))
    L.append("")

    # 1 结论摘要
    bad = [r for _, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在明确违规点，可主张**。")
    elif risk:
        L.append("**判定：存在风险点，需补正后主张**。")
    else:
        L.append("**判定：未发现明显违规点；若有争议，按第七段路径推进**。")
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

    titles = ["二、定价性质与收费依据", "三、明码标价核查", "四、小区车位与涨价程序",
              "五、车辆受损责任", "六、违停处罚与拖车费"]
    for (title, rows), t in zip(results, titles):
        if not rows:
            continue
        L.append("## %s" % t)
        L.append("")
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for name, state, msg in rows:
            L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
        L.append("")

    L.append("## 七、投诉路径排序")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 八、时限清单")
    L.append("")
    L.append("| 事项 | 期限 |")
    L.append("|---|---|")
    L.append("| 申请行政复议 | 知道行政行为之日起 60 日内 |")
    L.append("| 提起行政诉讼 | 知道作出行政行为之日起 6 个月内 |")
    L.append("| 民事损害赔偿诉讼时效 | 3 年 |")
    L.append("| 监控保全 | 越快越好，通常 7~30 天即被覆盖 |")
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
    L.append("- 本结果依通用规则整理，**不替代律师意见**。")
    L.append("- 停车收费的地方差异极大，是否列入政府定价目录、具体标准与公示要求，"
             "**一律以当地价格主管部门、住建（物业）主管部门、公安交管部门口径为准**。")
    L.append("- 不预测行政复议与诉讼结果；是否处罚、是否赔偿以主管部门认定与司法机关裁判为准。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    return "\n".join(L) + "\n"


def to_json(f, results, ptype, todos, today):
    return {
        "核查日期": today.isoformat(),
        "停车场景": f["scene"],
        "定价性质": ptype,
        "结论": {
            "不通过": [r[0] for _, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _, rows in results for r in rows if r[1] == "待补正"],
        },
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
        "scene": get_text(kv, ["停车场景", "场景", "停车场所"]),
        "subject": get_text(kv, ["收费主体", "收费方"]),
        "space_type": get_text(kv, ["车位性质", "车位类型"]),
        "paid": parse_num(get_text(kv, ["单次收费金额", "实缴金额", "实际支付"])),
        "std": parse_num(get_text(kv, ["公示标准金额", "公示标准", "应缴金额"])),
        "rent_old": parse_num(get_text(kv, ["涨价前月租金额", "原月租金额"])),
        "rent_new": parse_num(get_text(kv, ["月租金额", "现月租金额", "涨价后月租金额"])),
        "has_board": get_text(kv, ["现场有无收费公示牌", "有无公示牌", "收费公示牌"]),
        "board_tel": get_text(kv, ["公示是否含投诉电话", "公示含投诉电话"]),
        "vote": get_text(kv, ["涨价是否经业主大会表决", "是否经业主表决", "业主大会表决"]),
        "vote_public": get_text(kv, ["是否有业主大会决议公示", "决议公示"]),
        "damaged": get_text(kv, ["车辆是否受损", "是否受损"]),
        "damage_type": get_text(kv, ["受损情形", "损害情形"]),
        "ticket": get_text(kv, ["是否有停车凭证", "停车凭证"]),
        "camera": get_text(kv, ["是否已调取监控", "监控情况", "是否调取监控"]),
        "police": get_text(kv, ["是否已报警", "报警"]),
        "claim": get_text(kv, ["是否已向场方书面索赔", "书面索赔", "索赔情况"]),
        "ticket_penalty": get_text(kv, ["是否收到违停处罚", "收到违停处罚"]),
        "penalty_body": get_text(kv, ["处罚主体", "处罚单位"]),
        "towed": get_text(kv, ["是否被拖车", "拖车"]),
        "tow_fee": get_text(kv, ["是否被收取拖车费", "收取拖车费"]),
        "tow_fee_amt": parse_num(get_text(kv, ["拖车费金额", "拖车费"])),
        "penalty_date": get_text(kv, ["处罚决定书收到日期", "收到处罚日期", "处罚日期"]),
        "contact": get_text(kv, ["已交涉对象", "交涉情况"]),
        "evidence": get_text(kv, ["证据清单", "已有证据"]),
    }

    missing = [k for k in ("scene",) if not filled(f[k])]
    r_price, ptype = checks_pricing(f)
    results = [
        ("定价性质与收费依据", r_price),
        ("明码标价核查", checks_posting(f)),
        ("小区车位与涨价程序", checks_community(f)),
        ("车辆受损责任", checks_damage(f)),
        ("违停处罚与拖车费", checks_penalty(f, today)),
    ]
    steps = path_order(f)
    todos = todo_list(f, results)

    if args.json:
        print(json.dumps(to_json(f, results, ptype, todos, today), ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, ptype, steps, todos, today)
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
