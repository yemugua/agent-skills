
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


CHECKS = [('Q1', 'FAIL', '未含范围界定与不适用说明', '范围', "yes(r,'scope')"), ('Q2', 'FAIL', '未含过程框架与相互关系', '过程', "yes(r,'process_map')"), ('Q3', 'WARN', '未含方针目标与职责权限', '职责', "yes(r,'responsibility')"), ('Q4', 'FAIL', '未含引用程序文件清单', '引用', "has(r,'procedures')"), ('Q5', 'WARN', '未含版本控制与发布审批', '版本', "yes(r,'version_control')")]

SAMPLE_GOOD = {'scope': True, 'process_map': True, 'responsibility': True, 'procedures': ['文件控制程序', '内审程序'], 'version_control': True}
SAMPLE_BAD = {'scope': False, 'process_map': False, 'responsibility': False, 'procedures': [], 'version_control': False}
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
