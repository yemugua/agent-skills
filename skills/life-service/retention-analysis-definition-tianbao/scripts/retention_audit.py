#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retention matrix auditor.

Validates an N-day retention matrix, computes size-weighted retention and churn,
checks monotonicity, cohort maturity and definition completeness.

Usage
  python retention_audit.py --file retention.csv \
      --unit user --base signup --active "app open" \
      --window "day N only" --on-day 1 --on-day 7 --on-day 30
  python retention_audit.py --file retention.csv --check-maturity
  python retention_audit.py --selftest

CSV header (required: cohort_date; dN columns optional but needed to audit)
  cohort_date,size,d1,d3,d7,d30,queue_age
Retention values are fractions in [0, 1]. Blank means "not matured".
"""
import argparse
import csv
import datetime
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

RATE_RE = re.compile(r'^d(\d+)$')
RATE_MIN = 0.0
RATE_MAX = 1.0

REQUIRED_DEF = ('unit', 'base', 'active', 'window')
DEF_LABELS = {
    'unit': 'dedup unit',
    'base': 'cohort base (signup or active)',
    'active': 'active event',
    'window': 'return window (on-day / range / rolling)',
}

D7_HIGH = 0.25
D7_MID = 0.15
D7_LOW = 0.08

R_OVER_ONE = 'rate above 100%: dedup is broken, users counted twice'
R_NON_MONOTONIC = 'retention must not increase with N: mixed window definitions or dedup error'
R_NEGATIVE = 'negative rate: impossible value'
R_ZERO_SIZE = 'cohort size is zero: weighted retention would be undefined'
R_UNMATURE_ZERO = 'queue not matured but rate filled with 0: leave blank instead'
R_WEIGHT_RANGE = 'weighted value outside the range of per-cohort values: weight is wrong'
R_D7_LOW = 'D7 absolute level is low: a flat curve only means churn stopped, not that it is acceptable'
R_D7_HIGH = 'D7 absolute level is high'
R_NO_D_COLUMNS = 'no dN column found: nothing to audit'


def read_rows(path):
    if path == '-':
        data = sys.stdin.read()
    else:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            data = fh.read()
    return [dict(r) for r in csv.DictReader(io.StringIO(data))]


def parse_rate(raw):
    """Return (value, status) where status in ok/blank/bad/over.

    A trailing '%' is required for percent form: '40%' -> 0.40. Without '%'
    the value must already be a fraction in [0, 1]; anything above 1 is
    reported as over so the dedup problem gets surfaced instead of being
    silently rescaled.
    """
    s = (raw or '').strip()
    if s == '':
        return None, 'blank'
    pct = s.endswith('%')
    if pct:
        s = s[:-1].strip()
    try:
        v = float(s)
    except ValueError:
        return None, 'bad'
    if pct:
        v = v / 100.0
    if v < 0:
        return v, 'over'
    if v > 1.0:
        return v, 'over'
    return v, 'ok'


def parse_date(raw):
    s = (raw or '').strip().replace('/', '-')
    for fmt in ('%Y-%m-%d', '%Y%m%d'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def collect_days(fieldnames):
    days = []
    for fn in fieldnames or []:
        m = RATE_RE.match((fn or '').strip().lower())
        if m:
            days.append(int(m.group(1)))
    return sorted(days)


def analyze(rows, defs, today=None):
    days = collect_days(rows[0].keys() if rows else [])
    findings = []
    if not days:
        findings.append(('ERROR', '(file)', R_NO_D_COLUMNS))
        return {'findings': findings, 'weighted': {}, 'days': days}
    per_day = dict((d, []) for d in days)
    for idx, row in enumerate(rows, 1):
        date_s = (row.get('cohort_date') or '').strip()
        if not date_s:
            findings.append(('ERROR', '#%d' % idx, 'missing cohort_date'))
            continue
        size_raw = (row.get('size') or '').strip()
        try:
            size = float(size_raw)
        except ValueError:
            size = 0.0
        if size <= 0:
            findings.append(('WARN', date_s, R_ZERO_SIZE))
        prev = None
        prev_day = None
        for d in days:
            raw = row.get('d%d' % d, '')
            val, status = parse_rate(raw)
            if status == 'bad':
                findings.append(('ERROR', '%s d%d' % (date_s, d),
                                 'rate %r is not a number' % raw))
                continue
            if status == 'over':
                if val < 0:
                    findings.append(('ERROR', '%s d%d' % (date_s, d),
                                     R_NEGATIVE))
                else:
                    findings.append(('ERROR', '%s d%d' % (date_s, d),
                                     '%s (%.4f)' % (R_OVER_ONE, val)))
                continue
            if status == 'blank':
                continue
            if val is not None:
                if size > 0:
                    per_day[d].append((val, size, date_s))
                if prev is not None and d > prev_day and val > prev + 1e-9:
                    findings.append(('ERROR', '%s d%d' % (date_s, d),
                                     '%s (d%d=%.4f, d%d=%.4f)'
                                     % (R_NON_MONOTONIC, prev_day, prev, d, val)))
            # maturity check
            cdate = parse_date(date_s)
            if cdate is not None and val is not None:
                age = (today - cdate).days
                if age < d and val == 0:
                    findings.append(('WARN', '%s d%d' % (date_s, d),
                                     '%s (queue age %dd < d%d)'
                                     % (R_UNMATURE_ZERO, age, d)))
            prev, prev_day = val, d
    weighted = {}
    for d in days:
        items = per_day[d]
        if not items:
            continue
        wsum = sum(s for _v, s, _c in items)
        if wsum <= 0:
            continue
        w = sum(v * s for v, s, _c in items) / wsum
        weighted[d] = w
        vals = [v for v, _s, _c in items]
        if w < min(vals) - 1e-9 or w > max(vals) + 1e-9:
            findings.append(('ERROR', 'd%d' % d,
                             '%s (weighted=%.4f, min=%.4f, max=%.4f)'
                             % (R_WEIGHT_RANGE, w, min(vals), max(vals))))
    return {'findings': findings, 'weighted': weighted, 'days': days,
            'per_day': per_day}


def definition_findings(defs):
    out = []
    for key in REQUIRED_DEF:
        if not defs.get(key):
            out.append(('ERROR', '(definition)',
                        'missing %s (%s)' % (key, DEF_LABELS[key])))
    return out


def level_note(weighted, findings):
    if 7 not in weighted:
        return
    w = weighted[7]
    if w < D7_LOW:
        findings.append(('WARN', 'd7',
                         '%s (weighted D7 = %.1f%%)' % (R_D7_LOW, w * 100)))
    elif w >= D7_HIGH:
        findings.append(('INFO', 'd7',
                         R_D7_HIGH + ' (weighted D7 = %.1f%%)' % (w * 100)))


def render(res, defs, lines):
    lines.append('== RETENTION AUDIT ==')
    if defs.get('unit'):
        lines.append('dedup unit           : %s' % defs['unit'])
    if defs.get('base'):
        lines.append('cohort base          : %s' % defs['base'])
    if defs.get('active'):
        lines.append('active event         : %s' % defs['active'])
    if defs.get('window'):
        lines.append('return window        : %s' % defs['window'])
    lines.append('weighting            : by cohort size')
    days = res['days']
    lines.append('')
    lines.append('weighted retention by day:')
    for d in days:
        if d in res['weighted']:
            w = res['weighted'][d]
            lines.append('  D%-3d retention %6.2f%%   churn %6.2f%%'
                         % (d, w * 100, (1 - w) * 100))
    lines.append('')
    grouped = {}
    for level, who, msg in res['findings']:
        grouped.setdefault(level, []).append((who, msg))
    for level in ('ERROR', 'WARN', 'INFO'):
        items = grouped.get(level, [])
        lines.append('[%s] %d' % (level, len(items)))
        for who, msg in items:
            lines.append('  %s: %s' % (who, msg))
    err = len(grouped.get('ERROR', []))
    lines.append('')
    if err:
        lines.append('VERDICT: NOT TRUSTWORTHY (errors=%d)' % err)
    else:
        lines.append('VERDICT: USABLE (errors=0, warns=%d)'
                     % len(grouped.get('WARN', [])))


def selftest_rows():
    return [
        {'cohort_date': '2026-09-01', 'size': '1000', 'd1': '0.40',
         'd7': '0.22', 'd30': '0.15', 'queue_age': '40'},
        {'cohort_date': '2026-09-02', 'size': '2000', 'd1': '0.45',
         'd7': '0.26', 'd30': '0.18', 'queue_age': '39'},
        {'cohort_date': '2026-09-03', 'size': '3000', 'd1': '0.50',
         'd7': '0.28', 'd30': '', 'queue_age': '38'},
    ]


def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    defs = {'unit': 'user', 'base': 'signup', 'active': 'app open',
            'window': 'day N only'}
    today = datetime.date(2026, 10, 11)
    rows = selftest_rows()

    # 1 weighted D1 = (0.40*1000 + 0.45*2000 + 0.50*3000)/6000
    # 1 weighted D1
    res = analyze(rows, defs, today)
    w1 = res['weighted'][1]
    ck('weighted D1 = 0.466667', abs(w1 - 0.4666667) < 1e-5, '%.6f' % w1)

    # 2 weighted D7 = (0.22*1000 + 0.26*2000 + 0.28*3000)/6000
    w7 = res['weighted'][7]
    ck('weighted D7 = 0.263333', abs(w7 - 0.2633333) < 1e-5, '%.6f' % w7)

    # 3 D30 has only 2 cohorts, still computed
    ck('D30 weighted present (2 cohorts)', 30 in res['weighted'])

    # 4 no errors on clean data
    errs = [f for f in res['findings'] if f[0] == 'ERROR']
    ck('clean data has no errors', not errs, str([f[2] for f in errs][:2]))

    # 5 weighted D7 lies inside the per-cohort range [0.22, 0.28]
    ck('weighted within per-cohort range', 0.22 <= w7 <= 0.28, '%.4f' % w7)

    # 6 non-monotonic errors
    bad = [{'cohort_date': '2026-09-01', 'size': '1000', 'd1': '0.20',
            'd7': '0.30'}]
    res6 = analyze(bad, defs, today)
    ck('d7 > d1 errors',
       any(f[0] == 'ERROR' and 'must not increase' in f[2]
           for f in res6['findings']))

    # 7 rate above 100% (bare 1.4, no percent sign) must error
    bad = [{'cohort_date': '2026-09-01', 'size': '1000', 'd1': '1.4'}]
    res7 = analyze(bad, defs, today)
    ck('rate above 1.0 errors',
       any(f[0] == 'ERROR' and '100%' in f[2] for f in res7['findings']))

    # 8 unmature queue filled with 0 warns
    young = [{'cohort_date': '2026-10-10', 'size': '500', 'd7': '0'}]
    res8 = analyze(young, defs, today)
    ck('unmature zero warns',
       any(f[0] == 'WARN' and 'not matured' in f[2] for f in res8['findings']))

    # 9 missing definition fields error
    res9 = analyze(selftest_rows(), {'unit': None, 'base': None,
                                     'active': None, 'window': None}, today)
    df = definition_findings({'unit': None, 'base': None, 'active': None,
                              'window': None})
    ck('four missing definition fields', len(df) == 4, str(len(df)))

    # 10 no dN columns errors
    empty = [{'cohort_date': '2026-09-01', 'size': '100'}]
    res10 = analyze(empty, defs, today)
    ck('no dN column errors',
       any(f[0] == 'ERROR' for f in res10['findings']))

    # 11 low D7 warns about the flat-curve misconception
    low = [{'cohort_date': '2026-09-01', 'size': '1000', 'd1': '0.06',
            'd7': '0.05'}]
    res11 = analyze(low, defs, today)
    level_note(res11['weighted'], res11['findings'])
    ck('low D7 warns',
       any(f[0] == 'WARN' and 'flat curve' in f[2] for f in res11['findings']))

    # 12 percent-form values are normalized
    pct = [{'cohort_date': '2026-09-01', 'size': '1000', 'd1': '40%'}]
    res12 = analyze(pct, defs, today)
    ck('percent form parsed',
       abs(res12['weighted'][1] - 0.40) < 1e-9,
       '%.6f' % res12['weighted'][1])

    # 13 zero size cohort warns
    zs = [{'cohort_date': '2026-09-01', 'size': '0', 'd1': '0.4'}]
    res13 = analyze(zs, defs, today)
    ck('zero size warns',
       any(f[0] == 'WARN' and 'size is zero' in f[2]
           for f in res13['findings']))

    # 14 churn is 1 - weighted retention
    ck('churn complements retention', abs((1 - w7) - 0.7366667) < 1e-5,
       '%.6f' % (1 - w7))

    out = []
    failed = 0
    for name, ok, info in checks:
        if not ok:
            failed += 1
        out.append('%s  %-44s %s' % ('PASS' if ok else 'FAIL', name, info))
    out.append('total=%d failed=%d' % (len(checks), failed))
    out.append('SELFTEST OK' if failed == 0 else 'SELFTEST FAILED')
    text = '\n'.join(out) + '\n'
    with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    return 0 if failed == 0 else 1


def build_parser():
    p = argparse.ArgumentParser(description='Retention matrix auditor')
    p.add_argument('--file', type=str, default=None,
                   help='CSV retention matrix, or - for stdin')
    p.add_argument('--unit', type=str, default=None)
    p.add_argument('--base', type=str, default=None,
                   help='cohort base: signup or active')
    p.add_argument('--active', type=str, default=None, help='active event')
    p.add_argument('--window', type=str, default=None,
                   help='return window: on-day / range / rolling')
    p.add_argument('--check-maturity', dest='check_maturity',
                   action='store_true')
    p.add_argument('--today', type=str, default=None,
                   help='reference date YYYY-MM-DD for maturity checks')
    p.add_argument('--out', type=str, default=None)
    p.add_argument('--selftest', action='store_true')
    return p


def main():
    args = build_parser().parse_args()
    if args.selftest:
        return selftest()
    if not args.file:
        text = '[ERROR] --file is required (use - for stdin)\n'
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    today = datetime.date.today()
    if args.today:
        d = parse_date(args.today)
        if d:
            today = d
    try:
        rows = read_rows(args.file)
    except Exception as exc:
        text = '[ERROR] cannot read %s: %s\n' % (args.file, exc)
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    defs = {'unit': args.unit, 'base': args.base, 'active': args.active,
            'window': args.window}
    res = analyze(rows, defs, today)
    res['findings'].extend(definition_findings(defs))
    level_note(res['weighted'], res['findings'])
    lines = []
    render(res, defs, lines)
    text = '\n'.join(lines) + '\n'
    path = args.out or RESULT
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())