
import json, sys, os
from datetime import date, datetime

def _p(d):
    if isinstance(d, (date, datetime)): return d
    return date.fromisoformat(str(d)[:10])

def days_since(d, today):
    return (today - _p(d)).days

def days_until(d, today):
    return (_p(d) - today).days

def has(r, k):
    v = r.get(k) if isinstance(r, dict) else None
    return v not in (None, "", [], {}, 0)

def lst(r, k):
    v = r.get(k) if isinstance(r, dict) else None
    return v if isinstance(v, list) else ([v] if v else [])

def count(r, k):
    return len(lst(r, k))

def yes(r, k):
    return str(r.get(k, "")).strip() in ("是", "Y", "y", "yes", "True", "true", "1")


CHECKS = [('Q1', 'FAIL', '未设内推流程与激励', '内推', "has(r,'referral_rule')"), ('Q2', 'WARN', '未含内推质量把控（筛选/背调）', '质量', "yes(r,'referral_filter')"), ('Q3', 'FAIL', '未含试用期考核标准', '考核', "has(r,'probation_kpi')"), ('Q4', 'WARN', '未含转正/解除合规（提前通知/举证）', '合规', "yes(r,'compliance')")]

SAMPLE_GOOD = {'referral_rule': '内推奖金+荣誉', 'referral_filter': True, 'probation_kpi': '月度目标+导师评价', 'compliance': True}
SAMPLE_BAD = {'referral_rule': '', 'referral_filter': False, 'probation_kpi': '', 'compliance': False}
BAD_EXPECT = ['Q1', 'Q2', 'Q3', 'Q4']

def evaluate(record, today):
    findings = []
    for qid, sev, desc, ref, expr in CHECKS:
        ns = {"r": record, "today": today, "has": has, "yes": yes, "count": count, "lst": lst, "days_since": days_since, "days_until": days_until, "_p": _p}
        safe_builtins = {"float": float, "int": int, "str": str, "len": len, "max": max, "min": min, "bool": bool, "abs": abs, "sum": sum, "round": round}
        try:
            ok = bool(eval(expr, {"__builtins__": safe_builtins}, ns))
        except Exception:
            ok = False
        if not ok:
            findings.append((sev, qid, desc, ref))
    return findings

def summary(findings):
    f = sum(1 for x in findings if x[0] == "FAIL")
    w = sum(1 for x in findings if x[0] == "WARN")
    verdict = "不通过" if f else ("建议完善" if w else "通过")
    return {"fail": f, "warn": w, "verdict": verdict}

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--today", default="2026-10-13")
    ap.add_argument("--format", default="md")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    today = date.fromisoformat(args.today)

    if args.selftest:
        g = evaluate(SAMPLE_GOOD, today)
        sg = summary(g)
        assert sg["fail"] == 0, f"good样本不应有FAIL，实际: {g}"
        b = evaluate(SAMPLE_BAD, today)
        codes = {x[1] for x in b}
        miss = [q for q in BAD_EXPECT if q not in codes]
        assert not miss, f"bad样本应命中 {BAD_EXPECT}，缺失: {miss}；实际: {[x[1] for x in b]}"
        print("SELFTEST PASS")
        return 0

    if not args.file:
        print("需提供 --file 或 --selftest"); return 2
    rec = json.load(open(args.file, encoding="utf-8"))
    if isinstance(rec, dict) and "today" not in rec:
        rec["today"] = args.today
    findings = evaluate(rec, today)
    sm = summary(findings)
    if args.format == "json":
        print(json.dumps({"findings": findings, **sm}, ensure_ascii=False, indent=2))
    else:
        for sev, qid, desc, ref in findings:
            print(f"[{sev}] {qid} {desc}（依据：{ref}）")
        print(f"结论: {sm['verdict']} | FAIL={sm['fail']} WARN={sm['warn']}")
    return 1 if sm["fail"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
