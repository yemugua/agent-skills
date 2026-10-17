# -*- coding: utf-8 -*-
"""Git 分支策略体检：策略选型 + 分支命名核对 + 陈旧/冲突风险扫描。

用法:
  python git_branch_check.py --selftest
  python git_branch_check.py --file branches.txt --as-of 2026-10-08 \
      --versions 1 --cadence weekly --stages 1 --rollback freeze --team 12

branches.txt 每行一条分支，字段用 Tab 或 | 分隔：
  分支名    最后提交日期    领先主干数    落后主干数
  feature/PROJ-142-order-refund    2026-09-20    3    40

只做静态核对，不代替现场 git 操作与人工研判。
"""
import argparse
import datetime
import io
import json
import os
import re
import sys

MAX_NAME = 60

ALLOWED_PREFIX = ("feature/", "fix/", "hotfix/", "release/", "chore/", "experiment/")
PROTECTED = ("main", "master", "develop", "trunk")

MAX_AGE_DAYS = {
    "feature/": 3,
    "fix/": 2,
    "hotfix/": 1,
    "release/": 14,
    "chore/": 14,
    "experiment/": 30,
}


def _today(s):
    if s:
        return datetime.date(*[int(x) for x in s.split("-")])
    return datetime.date.today()


def prefix_of(name):
    for p in ALLOWED_PREFIX:
        if name.startswith(p):
            return p
    return ""


def has_upper(s):
    for ch in s:
        if "A" <= ch <= "Z":
            return True
    return False


def has_cjk(s):
    for ch in s:
        if "一" <= ch <= "龥":
            return True
    return False


def check_branch_name(name):
    """返回违规清单(list[str])。空列表表示合规。工单号允许大写，简述部分必须小写。"""
    bad = []
    if not name:
        return ["空分支名"]
    pfx = prefix_of(name)
    if name in PROTECTED:
        if has_upper(name):
            bad.append("保护分支名应全小写")
        return bad
    if not pfx:
        bad.append("未使用受控前缀(feature/ fix/ hotfix/ release/ chore/ experiment/)")
        if has_upper(name):
            bad.append("含大写字母")
        return bad

    rest = name[len(pfx):]
    if has_upper(pfx):
        bad.append("前缀必须小写")
    if "/" in rest:
        bad.append("简述中出现多余斜杠")
        rest = rest.split("/")[0]
    if "_" in rest:
        bad.append("含下划线(应改用短横线)")
    if " " in name or "\t" in name:
        bad.append("含空白字符")
    if has_cjk(name):
        bad.append("含中文")
    if len(name) > MAX_NAME:
        bad.append("长度 %d 超过 %d 字符" % (len(name), MAX_NAME))
    ticket, desc = split_ticket(rest)
    if has_upper(desc):
        bad.append("简述含大写字母")
    if not ticket:
        bad.append("缺少工单号")
    elif not any(c.isdigit() for c in ticket):
        bad.append("工单号缺少数字编号")
    if pfx in ("feature/", "fix/") and desc == "":
        bad.append("缺少简述(建议 前缀/<工单号>-<小写短横线简述>)")
    return bad


def split_ticket(rest):
    """从 '<工单号>-<简述>' 中拆出工单号。工单号形如 PROJ-142 / JIRA123 / 1234。"""
    m = re.match(r"^[A-Za-z]{2,}[-_]?\d+(?=-|$)", rest)
    if m:
        return m.group(0), rest[m.end() + 1:]
    parts = rest.split("-", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def parse_num(v):
    try:
        return int(str(v).strip())
    except ValueError:
        return 0


def conflict_risk(ahead, behind):
    """落后越多、两边改动越大，合并冲突概率与解决成本越高。"""
    score = 0
    score += min(behind, 400) / 2.0
    score += min(ahead, 200) / 4.0
    if ahead > 0 and behind > 0:
        score += 15
    if ahead * behind > 1000:
        score += 20
    if score >= 120:
        return score, "高", "合并前先同步主干，建议拆小 PR 或分批 cherry-pick"
    if score >= 50:
        return score, "中", "先同步主干(rebase / pull --rebase)再跑一次流水线"
    if score > 0:
        return score, "低", "可直接合并，合并后跑全量单测"
    return score, "无", "无分支差异"


def age_days(last_commit, today):
    try:
        d = _today(last_commit)
    except ValueError:
        return None
    return (today - d).days


def recommend_strategy(versions, cadence, stages, rollback, team):
    """按 4 个硬指标选型。返回 dict。"""
    reasons = []
    branches = []
    warnings = []
    if versions >= 2:
        strategy = "GitFlow"
        reasons.append("同时维护 %d 个线上版本，需要 v1/v2 双分支并行热修" % versions)
        branches = ["master", "develop", "feature/*", "release/x.y.z", "hotfix/x.y.z"]
        if team <= 5:
            warnings.append("团队仅 %d 人却要并行维护 %d 个版本，人力不足，建议先收敛版本" % (team, versions))
    elif stages >= 2 or cadence in ("monthly", "quarterly"):
        strategy = "GitLab Flow"
        reasons.append("存在多级发布环境或固定发版窗口，需要环境分支承载")
        branches = ["main", "pre-prod", "prod", "feature/*", "release/x.y.z"]
        if cadence == "monthly":
            reasons.append("按月发布，发版窗口内只允许修缺陷")
    elif cadence == "daily":
        strategy = "Trunk-Based"
        reasons.append("每天可发布，分支存活控制在 24 小时内")
        branches = ["main", "短分支 < 24h"]
        if rollback != "anytime":
            warnings.append("Trunk-Based 依赖 Feature Flag 才能关闭半成品功能，未落地不建议选")
    elif rollback == "freeze":
        strategy = "GitLab Flow"
        reasons.append("要求版本冻结、冻结期只修缺陷")
        branches = ["main", "pre-prod", "prod", "feature/*", "release/x.y.z"]
    else:
        strategy = "GitHub Flow"
        reasons.append("单一线上版本、每周发布、需要 PR 评审")
        branches = ["main", "feature/*", "PR + squash merge"]
    return {
        "strategy": strategy,
        "branches": branches,
        "reasons": reasons,
        "warnings": warnings,
    }


def scan_report(text, today):
    items = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.replace("|", "\t").replace(",", "\t").split("\t") if p.strip()]
        if len(parts) < 2:
            continue
        name = parts[0]
        date = parts[1]
        ahead = parse_num(parts[2]) if len(parts) > 2 else 0
        behind = parse_num(parts[3]) if len(parts) > 3 else 0
        violations = check_branch_name(name)
        days = age_days(date, today)
        limit = MAX_AGE_DAYS.get(prefix_of(name), 30)
        stale = days is not None and days > limit
        score, level, advice = conflict_risk(ahead, behind)
        items.append({
            "name": name,
            "last_commit": date,
            "days": days,
            "limit": limit,
            "stale": stale,
            "ahead": ahead,
            "behind": behind,
            "risk_score": round(score, 1),
            "risk_level": level,
            "advice": advice,
            "violations": violations,
        })
    return items


def report_lines(items, today, rec):
    out = []
    out.append("=" * 58)
    out.append("Git 分支策略体检报告  基准日 %s" % today.isoformat())
    out.append("=" * 58)
    out.append("")
    out.append("[一] 策略推荐")
    out.append("  推荐策略: %s" % rec["strategy"])
    out.append("  分支构成: %s" % " / ".join(rec["branches"]))
    for r in rec["reasons"]:
        out.append("  依据: %s" % r)
    for w in rec["warnings"]:
        out.append("  [警示] %s" % w)
    out.append("")
    out.append("[二] 分支清单 (%d 条)" % len(items))
    for it in items:
        flags = []
        if it["violations"]:
            flags.append("命名:%s" % ";".join(it["violations"]))
        if it["stale"]:
            flags.append("超时(%d天>%d天)" % (it["days"], it["limit"]))
        flags.append("冲突风险%s(%s)" % (it["risk_level"], it["risk_score"]))
        out.append("  - %s  [ %s ]" % (it["name"], " | ".join(flags)))
        out.append("    处理建议: %s" % it["advice"])
    out.append("")
    nbad = len([i for i in items if i["violations"]])
    nstale = len([i for i in items if i["stale"]])
    nhigh = len([i for i in items if i["risk_level"] == "高"])
    out.append("[三] 汇总: 命名不合规 %d, 超期分支 %d, 高冲突风险 %d" % (nbad, nstale, nhigh))
    out.append("")
    out.append("免责: 本报告为静态核对，不构成发布决策依据。")
    out.append("=" * 58)
    return "\n".join(out)


FAILS = []


def ck(label, cond):
    """记录失败断言，便于定位。"""
    if not cond:
        FAILS.append(label)
    return bool(cond)


def write_result(path):
    lines = ["SELFTEST %s" % ("OK" if not FAILS else "FAILED")]
    for f in FAILS:
        lines.append("  FAILED: %s" % f)
    io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


def selftest():
    today = datetime.date(2026, 10, 8)

    r1 = recommend_strategy(1, "daily", 1, "anytime", 6)
    ck("日更单版本应推荐 Trunk-Based", r1["strategy"] == "Trunk-Based")

    r2 = recommend_strategy(2, "monthly", 2, "freeze", 20)
    ck("多版本并行应推荐 GitFlow", r2["strategy"] == "GitFlow")
    ck("GitFlow 依据应提到版本", any("版本" in x for x in r2["reasons"]))

    r3 = recommend_strategy(1, "monthly", 3, "freeze", 30)
    ck("多级环境应推荐 GitLab Flow", r3["strategy"] == "GitLab Flow")

    r4 = recommend_strategy(1, "weekly", 1, "anytime", 12)
    ck("周发布单环境应推荐 GitHub Flow", r4["strategy"] == "GitHub Flow")

    def v(name):
        return "".join(check_branch_name(name))

    ck("合规名应无违规", check_branch_name("feature/PROJ-142-order-refund") == [])
    ck("大写前缀应报未受控前缀", "未使用受控前缀" in v("Feature/PROJ-1-bad"))
    ck("简述大写应报违规", "简述含大写字母" in v("feature/PROJ-1-OrderRefund"))
    ck("下划线应报违规", "含下划线(应改用短横线)" in v("feature/PROJ-1-bad_name"))
    ck("超长应报违规", any("超过" in x for x in check_branch_name("feature/PROJ-1-" + "x" * 70)))
    ck("中文应报违规", "含中文" in v("feature/订单-退款"))
    ck("非法前缀应报违规", "未使用受控前缀" in v("wip/abcdef"))
    ck("无数字工单号应报违规", "工单号缺少数字编号" in v("feature/order-refund"))
    ck("保护分支 main 应无违规", check_branch_name("main") == [])

    sample = "\n".join([
        "feature/PROJ-142-order-refund\t2026-09-20\t3\t40",
        "hotfix/2.7.1\t2026-10-07\t1\t2",
        "release/3.0.0\t2026-08-01\t0\t520",
    ])
    items = scan_report(sample, today)
    ck("应解析出 3 条分支", len(items) == 3)
    ck("feature 超 3 天应判超期", items[0]["stale"] is True)
    ck("hotfix 1 天内不应判超期", items[1]["stale"] is False)
    ck("落后 520 应判高风险", items[2]["risk_level"] == "高")
    ck("差异小应判低风险", items[1]["risk_level"] == "低")

    txt = report_lines(items, today, r4)
    ck("汇总应含高冲突风险 1", "高冲突风险 1" in txt)
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="Git 分支策略体检")
    ap.add_argument("--file", help="分支清单文本文件")
    ap.add_argument("--as-of", help="基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--versions", type=int, default=1, help="并行维护的线上版本数")
    ap.add_argument("--cadence", default="weekly", choices=["daily", "weekly", "monthly", "quarterly"])
    ap.add_argument("--stages", type=int, default=1, help="发布环境级数")
    ap.add_argument("--rollback", default="anytime", choices=["anytime", "freeze"])
    ap.add_argument("--team", type=int, default=8, help="团队人数")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="结果写入文件")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    if not args.file:
        ap.error("需要 --file 或 --selftest")

    today = _today(args.as_of)
    text = io.open(args.file, "r", encoding="utf-8", errors="ignore").read()
    items = scan_report(text, today)
    rec = recommend_strategy(args.versions, args.cadence, args.stages, args.rollback, args.team)

    if args.json:
        body = json.dumps({"strategy": rec, "items": items}, ensure_ascii=False, indent=2)
    else:
        body = report_lines(items, today, rec)

    out_path = args.out or os.path.join(here, "_last_result.txt")
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("结果已写入: %s" % out_path)


if __name__ == "__main__":
    main()
