
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


CHECKS = [('Q1', 'FAIL', '未明确储存物品火灾危险性分类', 'GB 50016', "has(r,'storage_class')"), ('Q2', 'FAIL', '堆距/墙距/主通道未达标', 'XF 1131', "days_since('2000-01-01', _p(r.get('today','2026-10-13')))>=0 and float(r.get('pile_gap',0))>=1 and float(r.get('wall_gap',0))>=0.5 and float(r.get('main_aisle',0))>=2"), ('Q3', 'WARN', '甲乙类未独立库或通风防爆缺失', '甲乙类', "not has(r,'class_ab') or (yes(r,'ab_isolated') and yes(r,'explosion_proof'))"), ('Q4', 'FAIL', '电动车/充电区未独立隔离', '电动车', "yes(r,'ebike_out')"), ('Q5', 'WARN', '装卸与动火审批未单列', '动火', "has(r,'hotwork_rule')")]

SAMPLE_GOOD = {'storage_class': '丙类', 'pile_gap': 1.2, 'wall_gap': 0.6, 'main_aisle': 2.5, 'class_ab': '', 'ab_isolated': False, 'explosion_proof': False, 'ebike_out': True, 'hotwork_rule': '动火证+监护', 'today': '2026-10-13'}
SAMPLE_BAD = {'storage_class': '', 'pile_gap': 0.3, 'wall_gap': 0.1, 'main_aisle': 1.0, 'class_ab': '甲乙类', 'ab_isolated': False, 'explosion_proof': False, 'ebike_out': False, 'hotwork_rule': '', 'today': '2026-10-13'}
BAD_EXPECT = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']

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
