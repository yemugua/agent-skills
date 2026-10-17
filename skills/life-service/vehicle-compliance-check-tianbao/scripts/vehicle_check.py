#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""车务合规自查脚本 v1.0.0

输入：车辆信息 markdown（采集表格式）
输出：到期倒计时 / 年检节点推算 / 记分核验 / 过户保险自查 / 风险待办 / 数据质量

只做「时间推算 + 常见档位核对 + 待办生成」，不代办、不承诺、不编造网点与费用；
法规口径一律标注「以当地车管所、12123 与最新规章为准」。
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime

VERSION = "1.0.0"
PLACEHOLDER = ("待填写", "待填", "暂无", "—", "-", "?", "（待补）", "未填", "不涉及")
BASE_TODAY = date.today()

DATE_RE = re.compile(r"(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")

POINT_RULES = [
    (12, r"酒驾|醉驾|饮酒后驾驶|吊销|逃逸|伪造|变造|准驾不符|超速.{0,4}(50|百分之五十)|"
         r"故意遮挡|故意污损|不按规定安装号牌"),
    (9, r"7座|七座|超载.{0,4}(50|百分之五十)以上|违法停车|违停.{0,2}高速|高速公路.{0,6}停车"),
    (6, r"闯红灯|红灯|违反禁令|禁令标志|禁止标线|不按规定让行|让行|避让校车|校车|"
        r"超速.{0,4}(20|百分之二十|30|百分之三十|50|百分之五十)|驾驶证被暂扣|暂扣期间"),
    (3, r"超速|违停|不按导向|导向车道|接打手机|开车打电话|安全带|不系安全带|号牌不清|会车|超车"),
    (1, r"未按规定.{0,4}灯|低能见度|未放标志|校车标志"),
]

TRANSFER_RE = re.compile(r"违章|事故|抵押|查封|指标|提档|过户")


def clean(s):
    return re.sub(r"\s+", " ", str(s or "").strip())


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def is_ph(s):
    t = clean(s)
    return t == "" or t in PLACEHOLDER


def parse_date(tok):
    t = clean(tok)
    if is_ph(t) or t in ("未上线", "未领", "已过户"):
        return None
    m = DATE_RE.search(t)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except Exception:
        return d.replace(year=d.year + n, day=28)


def days_to(d, base):
    return (d - base).days


def grade(days):
    """返回 (状态文案, 级别) 级别: 高/中/低"""
    if days < 0:
        d = -days
        if d > 90:
            return "已逾期 %d 天" % d, "高"
        if d > 30:
            return "已逾期 %d 天" % d, "中"
        return "已逾期 %d 天" % d, "低"
    if days <= 30:
        return "%d 天后" % days, "中"
    if days <= 90:
        return "%d 天后" % days, "低"
    return "%d 天后" % days, "低"


def get_field(text, *labels):
    for line in text.splitlines():
        if norm(line) in ("", "---"):
            continue
        for lab in labels:
            if lab in norm(line):
                if "|" in line:
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    for i, c in enumerate(cells):
                        if lab in norm(c) and i + 1 < len(cells):
                            v = cells[i + 1]
                            if not is_ph(v):
                                return v
                            return ""
                m = re.search(r"%s\s*[:：]\s*(.*)$" % re.escape(lab), line)
                if m:
                    v = m.group(1).strip()
                    return "" if is_ph(v) else v
    return ""


def get_int(text, *labels):
    v = get_field(text, *labels)
    m = NUM_RE.search(clean(v))
    if not m:
        return 0
    try:
        return int(float(m.group(0)))
    except Exception:
        return 0


def yes_no(text, *labels):
    v = clean(get_field(text, *labels))
    if "否" in v:
        return False
    if "是" in v or "有" in v:
        return True
    return None


def inspection_nodes(reg, base):
    """推算未来几个年检/领标节点"""
    yrs = (base - reg).days // 365
    # 只有 2/4/8 年是「免检领标」、6/10 年是「上线检验」，
    # 不能因为要多列几年就凭空造出「第 9 年领标」这种不存在的节点；
    # 10 年以上才追加逐年节点。
    cand = [n for n in (2, 4, 6, 8, 10) if n >= yrs]
    if yrs >= 10:
        y = yrs + 1
        while y <= yrs + 4:
            cand.append(y)
            y += 1
    out = []
    for n in sorted(set(cand)):
        d = add_years(reg, n)
        action = "上线检验" if n in (6, 10) else "领取检验标志（免检）"
        if n > 10 or yrs >= 10:
            action = "上线检验（10 年以上每年一检）"
        # 已过期的节点不能直接丢掉：用户很可能没领标/没上线，这正是要提醒的地方
        out.append((n, d, action, "需处理完全部违章" if action.startswith("上线") else "12123 申领"))
    return out[:5]


def point_scan(lines):
    """逐行匹配常见记分档位"""
    hits = []
    for ln in lines:
        n = norm(ln)
        if len(n) < 2:
            continue
        pts = [p for p, pat in POINT_RULES if re.search(pat, n)]
        if pts:
            top = max(pts)
            # 原始行是 markdown 表格行，直接塞进新表格会把列撑裂，先把竖线抹掉
            hits.append((clean(ln).replace("|", " ")[:40], top))
    return hits


def build_report(path, base, as_of):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    reg = parse_date(get_field(text, "注册登记日期", " registration date", "注册日期"))
    missing = []
    if reg is None:
        return None, "未解析到注册登记日期：请在《车辆信息采集表》的「注册登记日期」填 YYYY-MM-DD（行驶证上的注册日期，不是买车日）。其他项会一并跳过。"

    base = base or BASE_TODAY
    sex_note = ""

    # ---- 年检节点 ----
    nodes = inspection_nodes(reg, base)
    age_yrs = (base - reg).days // 365

    # ---- 到期项 ----
    rows = []
    insur = parse_date(get_field(text, "交强险到期日", "交强险"))
    comm = parse_date(get_field(text, "商业险到期日", "商业险"))
    if insur:
        rows.append(("交强险", insur, "到期前续保；脱保上路会被扣车并罚应缴保费 2 倍"))
    else:
        missing.append("交强险到期日")
    if comm:
        rows.append(("商业险", comm, "续保前先看去年出险次数，影响费率"))
    else:
        missing.append("商业险到期日")
    transfer_day = parse_date(get_field(text, "提档日期", "档案提档"))
    if transfer_day:
        rows.append(("外迁档案落户（30 日）", add_years(transfer_day, 0), "逾期需回转出地重新提档，期间不得上路"))

    # ---- 记分 ----
    has_points = get_field(text, "本周期已累计记分", "已累计记分", "累计记分")
    cur = get_int(text, "本周期已累计记分", "已累计记分", "累计记分")
    viol_lines = []
    cur_lines = text.splitlines()
    for i, ln in enumerate(cur_lines):
        if any(k in norm(ln) for k in ("待处理违章", "疑似违章", "违章记录")):
            # 带日期才算违章描述：表头那一行自己也常常把内容写进去了
            if DATE_RE.search(ln):
                viol_lines.append(ln)
            j = i + 1
            while j < len(cur_lines) and not re.match(r"^#{1,3}\s", cur_lines[j]):
                if DATE_RE.search(cur_lines[j]) and len(norm(cur_lines[j])) > 6:
                    viol_lines.append(cur_lines[j])
                j += 1
            break
    if not viol_lines:
        for ln in cur_lines:
            if TRANSFER_RE.search(norm(ln)) and DATE_RE.search(ln) and len(norm(ln)) > 6:
                viol_lines.append(ln)
    hits = point_scan(viol_lines)
    total = cur + (max([p for _, p in hits]) if hits else 0)

    # ---- 过户 ----
    plan = yes_no(text, "是否计划过户", "计划过户")
    untr = get_int(text, "是否有未处理违章", "未处理违章")
    has_mort = yes_no(text, "是否有抵押", "车贷")
    sealed = yes_no(text, "是否被查封")
    limited = yes_no(text, "是否限牌城市")
    has_quota = yes_no(text, "买方是否已有机动车指标", "指标")

    L = []
    A = L.append
    A("# 车务合规自查（本地处理，不上传）")
    A("")
    A("- 基准日：%s ｜ 注册日期：%s ｜ 车龄：%d 年 ｜ 解析来源：%s"
      % (base.isoformat(), reg.isoformat(), age_yrs, os.path.basename(path)))
    A("- 法规口径：以当地车管所、12123 与最新规章为准；本表只做时间推算与常见档位核对。")
    A("")

    # 一、摘要
    A("## 一、结论摘要")
    A("")
    urgent = []
    if insur:
        g = grade(days_to(insur, base))
        if g[1] != "低":
            urgent.append("交强险%s" % g[0])
    if nodes:
        n, d, act, _ = nodes[0]
        if d < base:
            urgent.append("第 %d 年（%s）%s**已过期，先确认办没办**" % (n, d.isoformat(), act))
        else:
            urgent.append("第 %d 年（%s）%s" % (n, d.isoformat(), act))
    A("- 最近要办：%s" % ("；".join(urgent) if urgent else "暂无到期项"))
    A("- 记分：本周期已累计 %s 分%s" % (has_points or "0",
                                     ("，疑似违章再加 %d 分" % (total - cur)) if hits else ""))
    if total >= 12:
        A("- 判定：**触及/超过 12 分**，需参加满分学习并考科目一，期间不得开车。")
    elif total >= 9:
        A("- 判定：合计 %d 分，进入报警区，本月内别再违章，有争议的可先申诉复核。" % total)
    else:
        A("- 判定：合计 %d 分，未触及满分线，留意记分周期清零日。" % total)
    A("")

    # 二、到期倒计时
    A("## 二、到期倒计时")
    A("")
    A("| 事项 | 日期 | 状态 | 级别 | 下一步 |")
    A("|---|---|---|---|---|")
    any_urgent = False
    if rows:
        for name, d, tip in rows:
            g = grade(days_to(d, base))
            if g[1] != "低":
                any_urgent = True
            A("| %s | %s | %s | %s | %s |" % (name, d.isoformat(), g[0], g[1], tip))
    else:
        A("| 未填到期项 | — | — | 低 | 补填交强险/商业险到期日后可自动倒计时 |")
    if nodes:
        for n, d, act, note in nodes:
            g = grade(days_to(d, base))
            if g[1] != "低" or d < base:
                any_urgent = True
            st = ("%s（已过期，先确认办没办）" % g[0]) if d < base else g[0]
            A("| %s·第 %d 年 | %s | %s | %s | %s |"
              % (act, n, d.isoformat(), st, g[1], note))
    A("")

    # 三、年检周期
    A("## 三、年检周期推算（含已过期节点）")
    A("")
    A("| 车龄 | 到期日 | 要做什么 | 说明 |")
    A("|---|---|---|---|")
    if nodes:
        for n, d, act, note in nodes:
            A("| 第 %d 年 | %s | %s | %s |" % (n, d.isoformat(), act, note))
    else:
        A("| 无未来节点 | — | — | 请确认注册登记日期是否正确 |")
    A("")
    A("口径（非营运小微型载客汽车，2022-10-01 起）："
      "6 年内第 2、4 年免检领标；第 6、10 年上线检验；第 8 年免检领标；10 年以上每年一检。"
      "营运车、货车、大型车按专门规定。")
    A("")

    # 四、记分
    A("## 四、记分核验")
    A("")
    A("- 本周期已累计：%s 分" % (has_points or "0"))
    A("- 疑似违章逐条：")
    A("")
    A("| 行为 | 常见档位 | 提示 |")
    A("|---|---|---|")
    if hits:
        for txt, p in hits:
            A("| %s | %d 分 | 最终以《简易程序决定书》与 12123 显示为准 |" % (txt, p))
    else:
        A("| 未识别到可判分的违章描述 | — | 请按「日期 + 地点 + 行为」逐条写清 |")
    A("")
    A("- 合计约 **%d 分**（已累计 + 疑似最高档）" % total)
    A("- ⚠️ **买卖记分、找人代扣分属违法**，且原记分仍会落回实际违法驾驶人；"
      "本表不提供任何消分方案。")
    A("")

    # 五、过户/保险
    A("## 五、过户 / 保险自查")
    A("")
    if plan is False:
        A("- 本次未填写「计划过户」，以下为通用自查项（如不涉及可跳过）。")
    A("前置四件事（顺序不能反）：")
    A("")
    A("| # | 项目 | 状态 |")
    A("|---|---|---|")
    A("| 1 | 违章与事故处理完毕（有未处理违章窗口不受理） | %s |"
      % ("未通过（%d 条）" % untr if untr else ("待确认" if plan else "—")))
    A("| 2 | 解除抵押（车贷结清、登记证书解除抵押登记） | %s |"
      % ("未通过" if has_mort is True else ("待确认" if has_mort is None else "无抵押，已确认")))
    A("| 3 | 交强险在有效期内（脱保先补再办） | %s |"
      % ("已填到期日" if insur else "待确认"))
    A("| 4 | 车辆到场查验（人可不到，车必须到） | 待办 |")
    if plan is not None and plan:
        if limited is True and has_quota is False:
            A("| 0 | 限牌城市：买方已有机动车指标（无指标材料再全也办不了） | **未通过** |")
        elif limited is True:
            A("| 0 | 限牌城市：买方已有机动车指标 | 已确认 |")
    A("")
    A("外迁补充：提档后档案 **30 日内**须落户（逾期回转出地重提）→ 确认转入地排放门槛（国五/国六，各市不同）"
      "→ 提档后不得上路，需托运。")
    A("")
    A("保险衔接：过户前后交强险不能空窗；原保单在保的及时做**投保人批改**或退保重投，"
      "否则出险时原投保人已变更会扯皮。")
    A("")

    # 六、待办
    A("## 六、风险与待办（带时间）")
    A("")
    A("| # | 事项 | 时间节点 | 状态 |")
    A("|---|---|---|---|")
    todo = []
    if insur:
        todo.append(("续交强险，脱保上路会被扣车并罚 2 倍保费", "%s 前" % insur.isoformat()))
    if comm:
        todo.append(("续商业险（先看去年出险次数）", "%s 前" % comm.isoformat()))
    for n, d, act, _ in nodes[:2]:
        if d < base:
            todo.append(("确认第 %d 年「%s」是否已办（没办就是逾期）" % (n, act), "尽快"))
        else:
            todo.append(("%s（提前处理违章、带行驶证+交强险）" % act, "%s 前" % d.isoformat()))
    if total >= 12:
        todo.append(("满分学习 + 科目一（15 日内，期间不得开车）", "15 日内"))
    elif total >= 9:
        todo.append(("核对记分，有争议的先走 12123 申诉复核", "本月内"))
    if untr:
        todo.append(("处理未完违章 %d 条（年检与过户前都要清零）" % untr, "年检/过户前"))
    if plan is not None and plan:
        todo.append(("确认车贷结清解押 + 违章清零 + 买方可过户指标", "过户前"))
    if not todo:
        todo.append(("本次无可排期待办，保持 12123 与保单提醒开启", "—"))
    for i, t in enumerate(todo, 1):
        A("| %d | %s | %s | 待办 |" % (i, t[0], t[1]))
    A("")

    # 七、数据质量
    A("## 七、数据质量提示")
    A("")
    if missing:
        A("- **未填项（【待现场填写】）**：%s —— 补填后可出倒计时，脚本不猜值。" % "、".join(missing))
    else:
        A("- 未填项：无")
    A("- 未解析行：无（未解析的字段会列在上面）")
    A("- 法规口径：各地车管所材料清单与执行有差异，费用、网点、办理时长请以当地窗口为准。")
    A("")
    A("---")
    A("")
    A("本自查只做时间推算与常见档位核对，**不代办、不承诺、不构成法律意见**。")
    A("")

    body = "\n".join(L)
    result = {
        "version": VERSION,
        "base_date": base.isoformat(),
        "reg_date": reg.isoformat(),
        "age_years": age_yrs,
        "nodes": [{"age_year": n, "date": d.isoformat(), "action": a, "note": no}
                  for n, d, a, no in nodes],
        "deadlines": [{"item": nm, "date": d.isoformat(), "status": grade(days_to(d, base))[0],
                       "level": grade(days_to(d, base))[1]} for nm, d, _ in rows],
        "points": {"current": cur, "suspected": total - cur, "total": total,
                   "hits": hits},
        "missing": missing,
        "any_urgent": any_urgent,
    }
    return body, result


def main():
    ap = argparse.ArgumentParser(description="车务合规自查")
    ap.add_argument("vehicle", help="车辆信息文本（md/txt）")
    ap.add_argument("--base", default=None, help="基准日 YYYY-MM-DD（默认今天）")
    ap.add_argument("--out", default=None, help="输出 md 路径")
    ap.add_argument("--json", action="store_true", help="额外输出 json")
    args = ap.parse_args()

    if not os.path.exists(args.vehicle):
        print("文件不存在：%s" % args.vehicle)
        print("=EXIT= 2")
        return 2

    base = BASE_TODAY
    if args.base:
        base = parse_date(args.base) or BASE_TODAY

    body, result = build_report(args.vehicle, base, None)
    # 空/不可解析输入：body 为 None，提示串在 result 里 —— 两个都要挡
    if body is None or result is None:
        print(result if result is not None else body)
        print("=EXIT= 2")
        return 2

    out = args.out or (os.path.splitext(args.vehicle)[0] + "_合规自查.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    if args.json:
        jo = os.path.splitext(args.vehicle)[0] + "_合规自查.json"
        with open(jo, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("JSON -> %s" % jo)
    print(body)
    print("=EXIT= 0")
    print("OUT=%s | nodes=%d deadlines=%d points=%d missing=%d"
          % (out, len(result["nodes"]), len(result["deadlines"]),
             result["points"]["total"], len(result["missing"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
