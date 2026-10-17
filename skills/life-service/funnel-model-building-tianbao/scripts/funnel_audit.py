#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Funnel conversion auditor.

Computes adjacent / cumulative / overall conversion rates, per-step churn and
churn contribution share, then grades definition and monotonicity problems.

Usage
  python funnel_audit.py --file funnel.csv
  python funnel_audit.py --file funnel.csv --check-monotonic
  python funnel_audit.py --file funnel.csv --unit user \
      --window "7 days after step1" --attribution strict --check-definition
  python funnel_audit.py --selftest

CSV header (required: step, users; optional: note)
  step,users,note
"""
import argparse
import csv
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

SMALL_BASE = 100
STRICT_BASE = 30
CHURN_SHARE_HIGH = 0.30
CHURN_SHARE_MED = 0.10
POTENTIAL_HIGH = 2.0
POTENTIAL_MED = 0.5
ATTRIBUTIONS = ('strict', 'any', 'last')

# Reason phrases, kept as ASCII escape-free constants on purpose.
R_NON_MONOTONIC = ('step count exceeds the previous step: expected for '
                   '"any" order attribution or cross-day windows, otherwise '
                   'check dedup and tracking loss')
R_SMALL_BASE = ('base < 100: adjacent rate is unstable, do not use it as an '
                'optimization target')
R_VSMALL_BASE = ('base < 30: rate swings by more than 10pp, merge steps')
R_NO_UNIT = 'missing dedup unit: user/device/order/session must be declared'
R_NO_WINDOW = 'missing time window: all steps must share one window length'
R_NO_ATTRIB = 'missing attribution mode: strict/any/last must be declared'
R_BAD_ATTRIB = 'unrecognized attribution mode'
R_STEP_ZERO = 'step has zero users: downstream rates are undefined'
R_UNSORTED = 'step label looks like a metric name rather than a funnel step'
R_IDENTITY = ('product of adjacent rates does not match overall rate: steps '
              'were probably read from different windows')


def read_rows(path):
    if path == '-':
        data = sys.stdin.read()
    else:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            data = fh.read()
    return [dict(r) for r in csv.DictReader(io.StringIO(data))]


def parse_steps(rows):
    steps = []
    for idx, row in enumerate(rows, 1):
        name = (row.get('step') or '').strip()
        raw = (row.get('users') or '').strip()
        if not name:
            continue
        try:
            users = float(raw)
        except ValueError:
            users = -1.0
        steps.append({'idx': idx, 'step': name, 'users': users,
                      'note': (row.get('note') or '').strip()})
    return steps


def compute(steps):
    """Return per-step metrics plus identity check."""
    n = len(steps)
    first = steps[0]['users'] if n else 0.0
    total_churn = 0.0
    for i in range(1, n):
        d = steps[i - 1]['users'] - steps[i]['users']
        steps[i]['churn'] = d
        steps[i]['churn'] = steps[i]['churn'] if d > 0 else 0.0
        total_churn += steps[i]['churn']
    out = []
    for i, s in enumerate(steps):
        row = {'idx': s['idx'], 'step': s['step'], 'users': s['users']}
        if i == 0:
            row['adjacent'] = None
            row['cumulative'] = 1.0 if first > 0 else None
            row['churn'] = 0.0
            row['share'] = 0.0
            row['potential'] = 0.0
            row['se'] = 0.0
        else:
            prev = steps[i - 1]['users']
            row['adjacent'] = (s['users'] / prev) if prev > 0 else None
            row['cumulative'] = (s['users'] / first) if first > 0 else None
            row['churn'] = s['churn']
            row['share'] = (row['churn'] / total_churn) if total_churn > 0 else 0.0
            row['potential'] = (row['churn'] / first * 100.0) if first > 0 else 0.0
            if row['adjacent'] is not None:
                p = row['adjacent']
                if 0 < p < 1:
                    row['se'] = math.sqrt(p * (1 - p) / s['users']) * 100
                else:
                    row['se'] = 0.0
            else:
                row['se'] = 0.0
        out.append(row)
    overall = (steps[-1]['users'] / first) if (n and first > 0) else None
    prod = 1.0
    ok = True
    for r in out[1:]:
        if r['adjacent'] is not None:
            prod *= r['adjacent']
        else:
            ok = False
    identity_ok = ok and overall is not None and abs(prod - overall) < 1e-9
    return out, overall, identity_ok


def diagnose(metrics, overall, cfg, check_monotonic, check_definition):
    findings = []
    for r in metrics:
        step = r['step']
        users = r['users']
        if users < 0:
            findings.append(('ERROR', step, 'user count is not a number'))
            continue
        if users == 0:
            findings.append(('WARN', step, R_STEP_ZERO))
        if users < STRICT_BASE:
            findings.append(('WARN', step, R_VSMALL_BASE))
        elif users < SMALL_BASE:
            findings.append(('WARN', step, R_SMALL_BASE))
        if users == 0:
            continue
        if r['adjacent'] is not None and r['adjacent'] > 1.0:
            findings.append(('WARN', step, R_NON_MONOTONIC))
        if check_definition:
            if not cfg.get('unit'):
                findings.append(('ERROR', step, R_NO_UNIT))
            if not cfg.get('window'):
                findings.append(('ERROR', step, R_NO_WINDOW))
            if not cfg.get('attribution'):
                findings.append(('ERROR', step, R_NO_ATTRIB))
            elif cfg['attribution'] not in ATTRIBUTIONS:
                findings.append(('ERROR', step, R_BAD_ATTRIB + ': %r'
                                 % cfg['attribution']))
    if check_monotonic and not cfg.get('attribution'):
        findings.append(('INFO', '(board)',
                         'monotonic check requested but no attribution mode '
                         'declared; non-monotonic counts may be legitimate'))
    if check_monotonic and cfg.get('attribution') == 'strict':
        for r in metrics[1:]:
            if r['adjacent'] is not None and r['adjacent'] > 1.0:
                findings.append(('ERROR', r['step'],
                                 'strict-order attribution requires strictly '
                                 'decreasing counts'))
    # priority ranking
    ranked = sorted([r for r in metrics[1:] if r['churn'] > 0],
                    key=lambda r: -r['share'])
    for r in ranked:
        if r['share'] >= CHURN_SHARE_HIGH and r['potential'] >= POTENTIAL_HIGH:
            findings.append(('INFO', r['step'],
                             'priority: HIGH (share %.1f%%, potential %.2fpp)'
                             % (r['share'] * 100, r['potential'])))
        elif r['share'] >= CHURN_SHARE_HIGH and r['potential'] < POTENTIAL_MED:
            findings.append(('WARN', r['step'],
                             'high churn share but tiny potential: check '
                             'upstream traffic quality before optimizing'))
        elif r['share'] >= CHURN_SHARE_HIGH:
            findings.append(('INFO', r['step'],
                             'priority: HIGH (share %.1f%%, potential %.2fpp)'
                             % (r['share'] * 100, r['potential'])))
    return findings


def render(metrics, overall, identity_ok, cfg, findings, lines):
    lines.append('== FUNNEL AUDIT ==')
    if cfg.get('unit'):
        lines.append('dedup unit           : %s' % cfg['unit'])
    if cfg.get('window'):
        lines.append('time window          : %s' % cfg['window'])
    if cfg.get('attribution'):
        lines.append('attribution          : %s' % cfg['attribution'])
    lines.append('')
    lines.append('%-18s %10s %12s %12s %12s %10s %10s'
                 % ('step', 'users', 'adjacent', 'cumulative', 'churn',
                    'share', 'potential'))
    lines.append('-' * 92)
    for r in metrics:
        adj = '-' if r['adjacent'] is None else '%.2f%%' % (r['adjacent'] * 100)
        cum = '-' if r['cumulative'] is None else '%.2f%%' % (r['cumulative'] * 100)
        lines.append('%-18s %10.0f %12s %12s %12.0f %9.1f%% %9.2fpp'
                     % (r['step'][:18], r['users'], adj, cum, r['churn'],
                        r['share'] * 100, r['potential']))
    lines.append('-' * 92)
    ov = '-' if overall is None else '%.2f%%' % (overall * 100)
    lines.append('overall conversion   : %s' % ov)
    lines.append('identity check       : %s' % ('consistent'
                                                 if identity_ok else R_IDENTITY))
    small = [r['step'] for r in metrics[1:] if 0 < r['users'] < SMALL_BASE]
    if small:
        lines.append('small base steps     : %s (<%d, unstable)'
                     % (', '.join(small), SMALL_BASE))
    lines.append('')
    grouped = {}
    for level, who, msg in findings:
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


# ------------------------------------------------------------- selftest
def demo_rows():
    return [
        {'step': 'exposure', 'users': '100000'},
        {'step': 'click', 'users': '8000'},
        {'step': 'add_cart', 'users': '800'},
        {'step': 'order', 'users': '80'},
    ]


def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    cfg = {'unit': 'user', 'window': '7 days after step1',
           'attribution': 'strict'}

    # 1 basic ratios
    m, ov, ident = compute(parse_steps(demo_rows()))
    ck('overall 80/100000 = 0.0008', abs(ov - 0.0008) < 1e-12,
       '%.6f' % ov)
    ck('adjacent click = 8%', abs(m[1]['adjacent'] - 0.08) < 1e-12,
       '%.6f' % m[1]['adjacent'])

    # 2 identity holds
    ck('adjacent product equals overall', ident, str(ident))

    # 3 churn contribution: click loses 92000 of 99920 total churn
    ck('click churn share ~ 92.07%',
       abs(m[1]['share'] - 0.920744) < 0.002, '%.5f' % m[1]['share'])

    # 4 potential for click = 92pp
    ck('click potential = 92pp', abs(m[1]['potential'] - 92.0) < 0.01,
       '%.4f' % m[1]['potential'])

    # 5 small base detection
    f = diagnose(m, ov, cfg, False, True)
    ck('small base warns for click', any(x[0] == 'WARN' and 'base' in x[2]
                                         for x in f))

    # 6 monotonic strict-order violation
    bad = [{'step': 'a', 'users': '1000'}, {'step': 'b', 'users': '1200'}]
    mb, ovb, _ = compute(parse_steps(bad))
    fb = diagnose(mb, ovb, dict(cfg, attribution='strict'), True, True)
    ck('strict order non-monotonic errors',
       any(x[0] == 'ERROR' for x in fb))

    # 7 any-order non-monotonic is only a warning
    fa = diagnose(mb, ovb, dict(cfg, attribution='any'), True, True)
    ck('any order non-monotonic warns only',
       not any(x[0] == 'ERROR' for x in fa)
       and any(x[0] == 'WARN' for x in fa))

    # 8 missing definition errors (definition issues repeat per step, so count
    # distinct messages rather than rows)
    fc = diagnose(m, ov, {'unit': None, 'window': None, 'attribution': None},
                  False, True)
    distinct = set(x[2] for x in fc if x[0] == 'ERROR')
    ck('missing unit/window/attribution errors',
       len(distinct) == 3, 'distinct=%d' % len(distinct))

    # 9 priority ranking picks the big contributor
    f2 = diagnose(m, ov, cfg, False, False)
    ck('priority flagged on step click',
       any(x[1] == 'click' and 'priority' in x[2] for x in f2))

    # 10 zero step warns
    z = [{'step': 'a', 'users': '500'}, {'step': 'b', 'users': '0'},
         {'step': 'c', 'users': '0'}]
    mz, _, _ = compute(parse_steps(z))
    fz = diagnose(mz, None, cfg, False, False)
    ck('zero users warns', any(x[0] == 'WARN' and 'zero' in x[2] for x in fz))

    # 11 non-numeric users errors
    n = [{'step': 'a', 'users': 'abc'}]
    mn, _, _ = compute(parse_steps(n))
    fn = diagnose(mn, None, cfg, False, False)
    ck('non-numeric users errors',
       any(x[0] == 'ERROR' for x in fn))

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
    p = argparse.ArgumentParser(description='Funnel conversion auditor')
    p.add_argument('--file', type=str, default=None,
                   help='CSV funnel steps, or - for stdin')
    p.add_argument('--unit', type=str, default=None,
                   help='dedup unit: user/device/order/session')
    p.add_argument('--window', type=str, default=None, help='shared time window')
    p.add_argument('--attribution', type=str, default=None,
                   choices=list(ATTRIBUTIONS) + [None],
                   help='strict/any/last')
    p.add_argument('--check-monotonic', dest='check_monotonic',
                   action='store_true')
    p.add_argument('--check-definition', dest='check_definition',
                   action='store_true')
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
    try:
        steps = parse_steps(read_rows(args.file))
    except Exception as exc:
        text = '[ERROR] cannot read %s: %s\n' % (args.file, exc)
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    if not steps:
        text = '[ERROR] no steps found in %s\n' % args.file
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    metrics, overall, ident = compute(steps)
    cfg = {'unit': args.unit, 'window': args.window,
           'attribution': args.attribution}
    findings = diagnose(metrics, overall, cfg, args.check_monotonic,
                        args.check_definition)
    lines = []
    render(metrics, overall, ident, cfg, findings, lines)
    text = '\n'.join(lines) + '\n'
    path = args.out or RESULT
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())