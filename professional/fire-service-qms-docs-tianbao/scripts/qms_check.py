# -*- coding: utf-8 -*-
"""
qms_check.py —— 消防技术服务机构质量体系（QMS）认证材料自查与差距分析

用途：
  把一份《机构现状信息表》（markdown）喂进来，输出
    1. 结论摘要（当前能不能申报 / 差几项）
    2. 要素覆盖度矩阵（14 个过程要素 vs 现有体系文件）
    3. 人员资质与到期预警
    4. 设备校准溯源台账（超期 / 临期）
    5. 内审与管理评审间隔与下次到期日
    6. 认证时间线（含 2026-01-01 起新版认证规则的排期硬约束）
    7. 补件清单（建议文件编号 + 责任人）
    8. 高风险项（会直接导致审核不通过的项）

用法：
  python qms_check.py --file 现状.md [--today 2026-10-04] [--json out.json]
  不传 --today 则用系统当天。

注意：本脚本只做「文件/记录层面」的符合性自查，不替代现场核查，
也不对外宣称是否满足认证结论；最终结论由认证机构现场审核给出。
"""

from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import sys
from datetime import date, timedelta

VERSION = "1.0.0"

# ---------------------------------------------------------------- 常量

# 14 个过程要素：编号 / 名称 / 命中关键词（命中任一关键词即算现有文件覆盖到该要素）
ELEMENTS = [
    ("01", "质量方针与目标", "质量方针|质量目标|质量指标|年度目标|质量手册"),
    ("02", "组织机构与职责", "组织机构|岗位职责|管理者代表|技术负责人|质量负责人|任命书"),
    ("03", "人员能力与培训", "人员|注册消防工程师|消防设施操作员|培训|继续教育|社保|持证"),
    ("04", "合同与顾客要求评审", "合同评审|服务要求|顾客要求|客户需求|报价评审|合同签订"),
    ("05", "服务过程控制", "维护保养|维保|检测|评估|工作方案|作业指导书|现场记录|施工"),
    ("06", "设施设备管理", "设施设备|仪器设备|工具|移动终端|车辆|装备管理"),
    ("07", "测量溯源与校准", "校准|检定|计量|溯源|标准物质|校准证书"),
    ("08", "采购与外部供方", "供方|供应商|分包|采购|外部供方|合作单位"),
    ("09", "记录与档案管理", "记录|档案|归档|台账|保存期限|资料管理"),
    ("10", "投诉与服务满意度", "投诉|回访|满意度|意见|抱怨|服务评价"),
    ("11", "不合格与纠正改进", "不符合|整改|纠正措施|预防措施|持续改进|CAPA|不合格"),
    ("12", "内审与管理评审", "内部审核|内审|管理评审"),
    ("13", "应急与事故处置", "应急|应急预案|事故|处置|突发事件"),
    ("14", "法规标准识别更新", "法规|标准|规范|版本核查|现行有效|标准清单|法规识别"),
]

# 认证周期硬约束（2026-01-01 起新版质量管理体系认证规则落地）
MILESTONES = [
    ("证书有效期", "3 年", "获证后第 3 年需换证；撤销后 1 年内任何认证机构均不受理重新申请，务必避免违规"),
    ("内审频次", "每年 ≥ 1 次", "上次内审距今已超过 12 个月即视为失效，需补做并留存记录"),
    ("管理评审频次", "每年 ≥ 1 次", "最高管理者必须出席，输入输出不能「两张皮」，改进措施要闭环跟踪"),
    ("一阶段/二阶段间隔", "≥ 5 天", "2026 新规：两个阶段的审核间隔至少 5 天，排期要多留缓冲"),
    ("审核员年度审核上限", "≤ 180 天", "2026 新规：每位审核员全年审核不超过 180 天，热门机构排期会变长"),
    ("专职审核员全程参与", "强制", "2026 新规：审核组必须有一名专职审核员全程参与，直接推高认证成本"),
    ("监督审查", "获证后每年", "年度监督审查不通过会暂停证书，日常记录要保持可追溯"),
    ("整改回复时限", "一般 ≤ 7 个工作日", "不符合项整改回复原则上 7 个工作日内，重大隐患按法规单独定"),
]

# 证书类型识别（用于人员资质判定）
CERT_PATTERNS = [
    ("一级消防工程师", "一级消防工程师|一消|注册消防工程师（一级）"),
    ("二级消防工程师", "二级消防工程师|二消"),
    ("二级建造师-建筑", "二级建造师.*建筑|二建.*建筑"),
    ("二级建造师-机电", "二级建造师.*机电|二建.*机电"),
    ("消防设施操作员四级", "消防设施操作员.*四级|四级.*消防设施操作员"),
    ("消防设施操作员三级", "消防设施操作员.*三级|三级.*消防设施操作员"),
    ("消防安全管理员", "消防安全管理员"),
]

# 顺序很重要：具体岗位必须排在泛化岗位前面，
# 否则「林凤钦，技术负责人，一级消防工程师」会被前面的「负责人」先吃掉成总经理。
ROLE_PATTERNS = [
    ("技术负责人", "技术负责人|技术负责人兼"),
    ("质量负责人", "质量负责人|质量负责人兼"),
    ("管理者代表", "管理者代表|管理者代表兼"),
    ("项目负责人", "项目负责人|项目经理"),
    ("法人/总经理", "法人|总经理|执行董事"),
    ("操作员", "操作员|值班员|巡检员"),
]

DATE_RE = re.compile(r"(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})")
MONTH_RE = re.compile(r"(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*月?")
CALIB_NO_RE = re.compile(r"(校准(?:证书)?号|证书编号|校准编号)\s*[:：]?\s*([A-Za-z0-9\-_/]{4,})")

# 要素关键词扫描用的上限：一条文件最多可被 3 个要素引用（避免单一文件刷分）
MAX_USE = 3


# ---------------------------------------------------------------- 工具


def parse_date(text):
    """从任意中文串里抽日期，支持 2026-04-09 / 2026/4/9 / 2026年4月9日 / 2026.4.9"""
    if not text:
        return None
    for m in DATE_RE.finditer(str(text)):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= calendar.monthrange(y, mo)[1]:
            return date(y, mo, d)
    return None


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(month=2, day=28, year=d.year + n)


def day_gap(a, b):
    return (a - b).days


def json_default(o):
    """date 对象必须先转字符串再进 json，否则 --json 直接崩"""
    if isinstance(o, (date,)):
        return o.isoformat()
    return str(o)


def split_lines(text):
    out = []
    for ln in str(text or "").split("\n"):
        s = ln.strip().lstrip("-").strip()
        if s:
            out.append(s)
    return out


# ---------------------------------------------------------------- 解析输入


def split_sections(text):
    """按 ## 分节，返回 [(节名, 行列表)]"""
    secs = []
    cur = ("未分类", [])
    for ln in str(text or "").split("\n"):
        if re.match(r"^#{1,3}\s*", ln.strip()):
            name = re.sub(r"^#{1,3}\s*", "", ln.strip()).strip()
            cur = (name, [])
            secs.append(cur)
        else:
            cur[1].append(ln)
    return secs


def _section_of(secs, *keys):
    for name, body in secs:
        for k in keys:
            if name and k in name:
                return "\n".join(body)
    return ""


def parse_people(text):
    """从人员段落抽 [姓名, 岗位, 证书, 有效期]"""
    people = []
    for ln in split_lines(text):
        if not re.search(r"[一-龥]", ln):
            continue
        line = ln.replace("，", ",")
        name_m = re.match(r"^([一-龥]{2,4})[,，\s]", line)
        name = name_m.group(1) if name_m else None
        if not name:
            continue
        certs = []
        for label, pat in CERT_PATTERNS:
            if re.search(pat, line):
                certs.append(label)
        role = ""
        for label, pat in ROLE_PATTERNS:
            if re.search(pat, line):
                role = label
                break
        exp = None
        if re.search(r"有效期|有效期限|证书有效", line):
            cands = []
            for tok in re.findall(r"20\d{2}\s*[-/年.]\s*\d{1,2}\s*[-/月.]\s*\d{1,2}", line):
                d = parse_date(tok)
                if d:
                    cands.append(d)
            if cands:
                exp = cands[-1]
        if not exp:
            exp = parse_date(line)
        people.append({"name": name, "role": role, "certs": certs, "expiry": exp,
                       "raw": ln})
    return people


def parse_devices(text):
    """从设备/校准段落抽 [名称, 校准号, 校准日期, 有效期至]"""
    devs = []
    for ln in split_lines(text):
        if "校准" not in ln and "检定" not in ln and "溯源" not in ln:
            continue
        name_m = re.match(r"^(-?\s*)([一-龥A-Za-z0-9]{2,20}?)\s*[,，、:：]?\s*(?=校准|检定|溯源|编号|\d)", ln)
        name = name_m.group(2) if name_m else ""
        if not name:
            name_m2 = re.match(r"^([一-龥A-Za-z0-9]{2,20})", ln)
            name = name_m2.group(1) if name_m2 else ""
        calib_no = ""
        for m in CALIB_NO_RE.finditer(ln):
            calib_no = m.group(2)
            break
        if not calib_no:
            nm = re.search(r"((?:JLSZ|JL|JD|JJF|JJG)[-_]?[0-9A-Za-z\-_]+)", ln)
            if nm:
                calib_no = nm.group(1)
        exp = None
        for m in re.finditer(r"(?:有效期(?:至|到|截止)|有效期限)\s*(?:为)?\s*[:：]?\s*("
                             r"20\d{2}[-/.年]\d{1,2}(?:[-/月.]\d{1,2})?)", ln):
            exp = parse_date(m.group(1))
        if not exp:
            # 「校准日期 X，有效期一年」类：用校准日期 +1 年
            cd = parse_date(ln)
            if cd and "有效期" in ln:
                exp = add_years(cd, 1)
        calib_date = None
        for m in re.finditer(r"(?:校准日期|校准时间|校准日)\s*[:：]?\s*("
                             r"20\d{2}[-/.年]\d{1,2}(?:[-/月.]\d{1,2})?)", ln):
            calib_date = parse_date(m.group(1))
        devs.append({"name": name, "calib_no": calib_no, "calib_date": calib_date,
                     "expiry": exp, "raw": ln})
    return devs


def parse_docs(text):
    docs = []
    for ln in split_lines(text):
        if re.search(r"[一-龥A-Za-z]", ln) and len(ln) <= 60:
            docs.append(ln)
    return docs


def parse_basic(text, secs):
    basic = {}
    for name, body in secs:
        if not any(k in name for k in ("基本信息", "机构", "概况", "基本情况")):
            continue
        for ln in body:
            m = re.match(r"^([^：:]{2,20})\s*[:：]\s*(.+)$", ln.strip())
            if m:
                basic[m.group(1).strip()] = m.group(2).strip()
    return basic


def parse_last_dates(text, secs, today):
    """找上次内审 / 上次管理评审日期"""
    last_audit = None
    last_mr = None
    for name, body in secs:
        for ln in body:
            if re.search(r"上次内审|上次内部审核|上一次内审", ln):
                last_audit = parse_date(ln) or last_audit
            if re.search(r"上次管理评审|上次评审|上一次管理评审", ln):
                last_mr = parse_date(ln) or last_mr
    if last_audit is None:
        last_audit = _last_date_keyword(text, "内审")
    if last_mr is None:
        last_mr = _last_date_keyword(text, "管理评审")
    return last_audit, last_mr


def _last_date_keyword(text, kw):
    hits = []
    for m in DATE_RE.finditer(str(text)):
        seg = str(text[max(0, m.start() - 40):m.end() + 40])
        if kw in seg:
            d = parse_date(m.group(0))
            if d:
                hits.append(d)
    return min(hits) if hits else None


# ---------------------------------------------------------------- 分析


def cover_matrix(secs, docs):
    """要素覆盖度：在「已有体系文件 + 人员 + 设备 + 项目」文本里找要素关键词"""
    use = {}
    rows = []
    for code, name, pat in ELEMENTS:
        rx = re.compile(pat)
        matched, n = [], 0
        for d in docs:
            key = use.get(d, 0)
            if key >= MAX_USE:
                continue
            if rx.search(d):
                n += 1
                use[d] = key + 1
                matched.append(d)
        rows.append({
            "code": code, "name": name, "hits": n, "files": matched,
            "status": "已建立" if n >= 2 else ("部分覆盖" if n == 1 else "缺失"),
        })
    return rows


def expires(items, today, warn_days=90):
    out = []
    for it in items:
        if not it.get("expiry"):
            out.append({"item": it, "days": None, "state": "未填有效期"})
            continue
        gap = day_gap(it["expiry"], today)
        state = "已过期" if gap < 0 else ("临期" if gap <= warn_days else "有效")
        out.append({"item": it, "days": gap, "state": state})
    return out


def build_report(raw, org, today, people, devices, docs, matrix,
                 last_audit, last_mr, basic):
    miss = [r for r in matrix if r["status"] == "缺失"]
    part = [r for r in matrix if r["status"] == "部分覆盖"]
    over_exp = [d for d in expires(devices, today) if d["state"] == "已过期"]
    soon = [d for d in expires(devices, today) if d["state"] == "临期"]
    exp_person = [p for p in people if p["expiry"] and p["expiry"] < today]
    soon_person = [p for p in people
                   if p["expiry"] and today <= p["expiry"] <= today + timedelta(days=90)]

    L = []
    A = L.append
    A(f"# 消防技术服务机构质量体系（QMS）认证材料自查报告")
    A("")
    A(f"- 生成日期：{today.isoformat()}")
    A(f"- 被核查机构：{org or '（未填写机构名称）'}")
    A(f"- 依据：DB31/T 1380-2022《社会消防技术服务机构质量管理要求》、GB/T 19001-2016、"
      f"《社会消防技术服务管理规定》")
    A(f"- 工具版本：qms_check.py v{VERSION}")
    A("")
    A("> 说明：本报告只做**文件与记录层面**的符合性自查，用于补齐受控文件包和识别认证风险，")
    A("> 不构成认证结论，最终以认证机构现场审核为准。文中未出现现场实测数据。")
    A("")

    # ---- 1 结论摘要
    total = len(matrix)
    score = (total - len(miss)) * 1.0 / max(total, 1)
    if miss and not over_exp:
        verdict = "暂不具备申报条件"
    elif miss:
        verdict = "不具备申报条件"
    else:
        verdict = "文件层面基本齐备，可进入申报排期"
    A("## 一、结论摘要")
    A("")
    A(f"| 判定项 | 结果 |")
    A(f"|---|---|")
    A(f"| 当前判定 | **{verdict}** |")
    A(f"| 过程要素覆盖 | {total - len(miss)}/{total} 已覆盖，"
      f"缺失 {len(miss)} 项、部分覆盖 {len(part)} 项（覆盖率 {score * 100:.0f}%） |")
    A(f"| 人员资质 | 共 {len(people)} 人；已过期 {len(exp_person)} 人、90 天内到期 {len(soon_person)} 人 |")
    A(f"| 设备校准溯源 | 共 {len(devices)} 台套；已超期 {len(over_exp)} 台、临期 {len(soon)} 台 |")
    A(f"| 内审 | {'上次 ' + last_audit.isoformat() if last_audit else '未查到内审记录'} |")
    A(f"| 管理评审 | {'上次 ' + last_mr.isoformat() if last_mr else '未查到管理评审记录'} |")
    A("")

    # ---- 2 要素覆盖度矩阵
    A("## 二、要素覆盖度矩阵（14 个过程要素）")
    A("")
    A("| 编号 | 过程要素 | 命中文件数 | 状态 | 缺口说明 |")
    A("|---|---|---|---|---|")
    for r in matrix:
        gap = ""
        if r["status"] == "缺失":
            gap = f"需补受控文件/记录（建议见第五节补件清单）"
        elif r["status"] == "部分覆盖":
            gap = "仅 1 处覆盖，需补充作业指导书或实现记录表单"
        A(f"| {r['code']} | {r['name']} | {r['hits']} | {r['status']} | {gap} |")
    A("")
    A("**缺失要素明细**")
    A("")
    if miss:
        for r in miss:
            A(f"- 【{r['code']} {r['name']}】现有文件里查不到任何相关记录，"
              f"审核时会被直接判定为过程未建立")
    else:
        A("- 无缺失要素")
    A("")
    if part:
        A("**部分覆盖要素（需再补实现证据）**")
        A("")
        for r in part:
            A(f"- 【{r['code']} {r['name']}】命中：{('、'.join(r['files'][:2]))}")
        A("")

    # ---- 3 人员资质
    A("## 三、人员资质与到期预警")
    A("")
    if not people:
        A("- 未解析出人员记录，请按「## 人员」分节填写「姓名，岗位，证书类型，证书有效期」")
    else:
        A("| 姓名 | 岗位 | 证书 | 证书有效期 | 状态 |")
        A("|---|---|---|---|---|")
        for p in people:
            if not p["expiry"]:
                st = "未填有效期"
            elif p["expiry"] < today:
                st = f"已过期 {day_gap(today, p['expiry'])} 天"
            elif p["expiry"] <= today + timedelta(days=90):
                st = f"{(p['expiry'] - today).days} 天后到期"
            else:
                st = "有效"
            A(f"| {p['name']} | {p['role'] or '—'} | {'、'.join(p['certs']) or '—'} | "
              f"{p['expiry'].isoformat() if p['expiry'] else '—'} | {st} |")
        A("")
        A("> 提示：审核重点看**人员数量、证书等级、注册/社保关系是否在本机构**，"
          "证书过期或人证分离都会被判不符合。")
    A("")

    # ---- 4 设备校准溯源
    A("## 四、设备校准溯源台账")
    A("")
    if not devices:
        A("- 未解析出设备校准记录")
    else:
        A("| 设备/器具 | 校准证书号 | 校准日期 | 有效期至 | 剩余天数 | 状态 |")
        A("|---|---|---|---|---|---|")
        for d in expires(devices, today):
            it = d["item"]
            exp = it["expiry"].isoformat() if it["expiry"] else "—"
            left = d["days"] if d["days"] is not None else "—"
            A(f"| {it['name'] or '—'} | {it['calib_no'] or '—'} | "
              f"{it['calib_date'].isoformat() if it['calib_date'] else '—'} | {exp} | "
              f"{left} | {d['state']} |")
        A("")
        if over_exp:
            A("**超期必须处理**（测量溯源失效，属于高风险不符合项）")
            A("")
            for d in over_exp:
                it = d["item"]
                A(f"- 【{it['name']}】{it['calib_no'] or '无证书号'} 已于 "
                  f"{it['expiry'].isoformat() if it['expiry'] else '—'} 超期 "
                  f"{abs(d['days'])} 天 → 重新送检，更新校准证书并同步修订《设施设备台账》")
        if soon:
            A("")
            A("**临期（90 天内）建议排送检计划**")
            A("")
            for d in soon:
                it = d["item"]
                A(f"- 【{it['name']}】{it['expiry'].isoformat()} 到期，剩 {d['days']} 天")
    A("")

    # ---- 5 内审与管理评审
    A("## 五、内审与管理评审")
    A("")
    A("| 项目 | 上次日期 | 距今天数 | 是否已超 12 个月 | 建议下次动作 |")
    A("|---|---|---|---|---|")
    for label, dt in (("内部审核", last_audit), ("管理评审", last_mr)):
        if dt:
            gap = day_gap(today, dt)
            bad = "是，需补做" if gap > 365 else "否"
            A(f"| {label} | {dt.isoformat()} | {gap} | {bad} | "
              f"{add_years(dt, 1).isoformat()} 前完成下一次 |")
        else:
            A(f"| {label} | 未查到记录 | — | 是 | 立即补做并留存记录 |")
    A("")
    A("> 常见扣分项：内审应付外审、审核记录空洞、不符合项开得不痛不痒；"
      "管理评审最高管理者缺席、输入输出「两张皮」、改进措施不跟踪。")
    A("")

    # ---- 6 认证时间线
    A("## 六、认证时间线与 2026 新规硬约束")
    A("")
    A("| 项目 | 要求 | 对本机构的含义 |")
    A("|---|---|---|")
    for a, b, c in MILESTONES:
        A(f"| {a} | {b} | {c} |")
    A("")
    A("**排期建议**")
    A("")
    if last_audit and day_gap(today, last_audit) > 365:
        A(f"1. 内审已超 12 个月，先补做一次内审（建议 {today.isoformat()} 起 2 周内），再报认证机构")
    else:
        A(f"1. 内审与认证审核可以一次覆盖，但需提前排期（认证机构排期常比实际间隔更长）")
    A("2. 一阶段与二阶段至少间隔 5 天，按「材料受理 → 一阶段 → 5 天 → 二阶段 → 整改 → 发证」倒排")
    A("3. 审核员全年审核不超过 180 天，旺季排期会变长，建议提前 2~3 个月锁定审核机构")
    A("")

    # ---- 7 补件清单
    A("## 七、补件清单（建议受控文件编号）")
    A("")
    A("| 序号 | 需补文件/记录 | 建议编号 | 关联要素 | 建议责任人 |")
    A("|---|---|---|---|---|")
    act_no = 1
    owners = ("林凤钦" if any(p["name"] == "林凤钦" for p in people)
              else (people[0]["name"] if people else "质量负责人"))
    # 编号起点 40：避开机构现行 DXCX01~DXCX27 与 DX/JL 系列常用号，减少撞号返工
    for r in miss + part:
        A(f"| {act_no} | 【{r['name']}】受控文件 + 实现记录表单 | "
          f"DXCX{40 + act_no:02d} | {r['code']} {r['name']} | {owners} |")
        act_no += 1
    for d in over_exp:
        A(f"| {act_no} | 【{d['item']['name']}】重新校准证书 + 台账更新 | "
          f"DX/JL{20 + act_no:03d} | 07 测量溯源与校准 | {owners} |")
        act_no += 1
    if last_audit is None or (last_audit and day_gap(today, last_audit) > 365):
        A(f"| {act_no} | 年度内部审核计划 + 检查表 + 不符合项闭环记录 | DXCX31 | 12 内审与管理评审 | {owners} |")
        act_no += 1
    if last_mr is None:
        A(f"| {act_no} | 管理评审计划 + 输入输出清单 + 决议跟踪表 | DXCX32 | 12 内审与管理评审 | 总经理（吴涛） |")
        act_no += 1
    if act_no == 1:
        A("| 1 | 暂无缺项，直接进入认证排期 | — | — | — |")
    A("")
    A("> 编号规则沿用机构现有体系（如 DXCX 系列程序文件、DX/JL 系列记录表单），"
      "实际编号以本机构《文件控制程序》为准；本表为建议值，需核对现行有效版本。")
    A("")

    # ---- 8 高风险项
    A("## 八、高风险项（会直接导致审核不通过）")
    A("")
    # risks = (风险名, 处置建议)，处置建议直接落在表里，避免「见风险描述」这种空列
    risks = []

    if exp_person:
        names = "、".join(p["name"] for p in exp_person)
        risks.append(("人员证书过期",
                      f"{names} 的证书已过期，立即换证或补录有效期，并核对社保/注册是否在本机构；"
                      f"过期人员不得作为项目技术签字人"))
    if over_exp:
        risks.append(("测量溯源失效",
                      f"{len(over_exp)} 台设备校准证书超期，审核必查《设施设备台账》与校准证书，"
                      f"超期即不符合；先停用到期设备，排送检并换证后再开工单签字"))
    if not last_audit or (last_audit and day_gap(today, last_audit) > 365):
        risks.append(("内审缺失或超 12 个月",
                      "补做一次完整内审并留存检查表、不符合项清单与闭环证据，"
                      "认证审核前必须能拿出最近 12 个月内的内审记录"))
    if not last_mr:
        risks.append(("无管理评审记录",
                      "补做管理评审，最高管理者亲自出席，输入输出一一对应，改进措施要能看到关闭证据"))
    if not doc_hit(matrix, "07"):
        risks.append(("无测量溯源控制文件",
                      "校准计划、校准周期、证书归档「三件套」缺一不可，"
                      "按设备清单逐台建台账，有效期逐条写死"))
    if not doc_hit(matrix, "10"):
        risks.append(("无投诉与服务满意度记录",
                      "补客户回访登记与服务满意度调查；抽查记录要真实，"
                      "走形式（全 5 分、无具体意见）本身就是近年监管重点"))
    risks.append(("记录真实性",
                  "签到表人数与巡查记录不一致、日期逻辑倒置、事后补签一律视为造假；"
                  "宁可留空项，也不能编记录——造假比缺项后果严重得多"))

    A("| 序 | 风险 | 处置建议 |")
    A("|---|---|---|")
    for i, (t, a) in enumerate(risks, 1):
        A(f"| {i} | {t} | {a} |")
    A("")
    A("---")
    A("")
    A("本报告由 qms_check.py 自动生成，全部结论来自输入文件中的文字信息，"
      "未接入任何现场实测数据；带【待现场填写】的字段需人工核实后回填。")

    return "\n".join(L)


def doc_hit(matrix, code):
    for r in matrix:
        if r["code"] == code:
            return r["hits"] > 0
    return False


# ---------------------------------------------------------------- 主流程


def analyze(text, today=None):
    today = today or date.today()
    text = str(text or "")
    secs = split_sections(text)

    basic = parse_basic(text, secs)
    # 「（待填写）」「暂无」「—」这类占位值不能当成真机构名，否则报告会写出假名
    PLACEHOLDER = ("待填写", "待填", "暂无", "无", "—", "-", "?", "（待补）")
    org = basic.get("机构名称") or basic.get("公司名称") or basic.get("单位名称") or ""
    org = org.strip()
    if org and any(p in org for p in PLACEHOLDER):
        org = ""
    people = parse_people(_section_of(secs, "人员", "人力资源", "员工"))
    devices = parse_devices(_section_of(secs, "设备", "校准", "计量", "器具"))
    docs = parse_docs(_section_of(secs, "已有", "体系文件", "文件清单", "受控"))
    projs = split_lines(_section_of(secs, "项目", "服务记录", "业务"))
    docs_all = docs + projs
    last_audit, last_mr = parse_last_dates(text, secs, today)
    matrix = cover_matrix(secs, docs_all)

    report = build_report(text, org, today, people, devices, docs_all,
                          matrix, last_audit, last_mr, basic)
    return {
        "generated": today.isoformat(),
        "version": VERSION,
        "org": org,
        "people": people,
        "devices": devices,
        "docs": docs,
        "projects": projs,
        "matrix": matrix,
        "last_internal_audit": last_audit.isoformat() if last_audit else None,
        "last_management_review": last_mr.isoformat() if last_mr else None,
        "report": report,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="消防技术服务机构质量体系认证材料自查")
    ap.add_argument("--file", required=True, help="现状信息表 markdown 路径")
    ap.add_argument("--today", default=None, help="指定今天（YYYY-MM-DD），默认系统当天")
    ap.add_argument("--json", default=None, help="额外输出 json 到指定路径")
    args = ap.parse_args(argv)

    if not os.path.exists(args.file):
        sys.exit(f"[错误] 找不到输入文件：{args.file}")

    with open(args.file, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    if args.today:
        t = parse_date(args.today)
        if not t:
            sys.exit(f"[错误] 日期解析失败：{args.today}")
        today = t
    else:
        today = date.today()

    if not text.strip():
        sys.exit("[警告] 输入文件为空，未做任何分析。")

    res = analyze(text, today)

    if not res["people"] and not res["devices"] and not res["docs"]:
        sys.exit("[警告] 未解析出任何人员 / 设备 / 体系文件信息，"
                 "请确认输入文件分节使用「## 人员」「## 设备与校准」「## 已有体系文件」。")

    print(res["report"])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2, default=json_default)
        print(f"\n[已输出 json] {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
