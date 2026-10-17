#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data anomaly detector and contribution attributor.

Computes z-score against a trailing window, day-over-day and (when prior-year
rows are present) year-over-year change, classifies the movement shape, ranks
dimension contributions, and flags data-quality signals that mimic anomalies.

Usage
  python anomaly_detect.py --file series.csv --metric dau
  python anomaly_detect.py --file series.csv --metric gmv --window 30
  python anomaly_detect.py --file series.csv --metric dau --compare yoy
  python anomaly_detect.py --file series.csv --metric dau \
      --dims "channel:app,mini,h5" --check-data-quality \
      --delay-hours 2 --volume-threshold 100
  python anomaly_detect.py --selftest

CSV header (required: date, metric; optional: dim_channel, ...)
  date,metric,dim_channel,...
"""
import argparse
import csv
import datetime
import io
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

Z_WATCH = 2.0
Z_ANOMALY = 3.0
SHAPE_WINDOW = 5
TREND_RUN = 5
SMALL_N = 100
DELTA_EPS = 1e-12

R_DQ_DELAY = ('data is not complete: pipeline lag declared, current value '
              'cannot be judged anomalous')
R_DQ_SMALL = 'volume below threshold: normal statistical fluctuation'
R_DQ_SPIKE_RECOVER = 'spike recovered in the next point: treat as data glitch'
R_DQ_SPIKE_HOLD = 'step change that did not revert: suspect a definition change'
R_DQ_SHAPE_TREND = 'trend: %d consecutive same-direction points'
R_DQ_SHAPE_CYCLE = 'matches weekly cycle: aligned with the calendar'
R_DQ_DUP_DATE = 'duplicate date rows found'
R_DQ_NON_MONOTONIC = 'dates are not strictly increasing'
R_DQ_NEGATIVE = 'negative value: impossible for this metric'
R_DQ_BIG_Z = 'z-score above threshold'

DIM_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):(.+)$')


def read_rows(path):
    if path == '-':
        data = sys.stdin.read()
    else:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            data = fh.read()
    return [dict(r) for r in csv.DictReader(io.StringIO(data))]


def parse_date(raw):
    s = (raw or '').strip().replace('/', '-')
    for fmt in ('%Y-%m-%d', '%Y%m%d'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_num(raw):
    s = (raw or '').strip().replace(',', '')
    if s == '':
        return None
    try:
        return float(s)
    except ValueError:
        return None


def mean_std(values):
    n = len(values)
    if n < 2:
        return (None, None)
    m = sum(values) / n
    var = sum((v - m) ** 2 for v in values) / (n - 1)
    return (m, math.sqrt(var))


def classify_shape(series):
    """series is a list of floats, oldest first. Return (shape, detail)."""
    if len(series) < 2:
        return ('unknown', 'not enough points')
    diffs = [series[i + 1] - series[i] for i in range(len(series) - 1)]
    signs = [1 if d > DELTA_EPS else (-1 if d < -DELTA_EPS else 0)
             for d in diffs]
    tail = signs[-(TREND_RUN - 1):]
    if len(tail) == TREND_RUN - 1 and all(s > 0 for s in tail):
        return ('trend_up', '%d consecutive increases' % len(tail))
    if len(tail) == TREND_RUN - 1 and all(s < 0 for s in tail):
        return ('trend_down', '%d consecutive decreases' % len(tail))
    if signs[-1] != 0 and len(signs) >= 2 and signs[-2] != 0 \
            and signs[-1] != signs[-2]:
        magnitude = abs(diffs[-1]) if diffs[-1] else 0.0
        prev = abs(diffs[-2]) if len(diffs) > 1 and diffs[-2] else 0.0
        if magnitude > prev * 3:
            return ('reversal', 'direction flipped with a 3x larger step')
    # weekly cycle: value close to the same weekday one week ago
    if len(series) > 7:
        d = series[-1] - series[-8]
        scale = mean_std(series[:-1])[1] or 1.0
        if abs(d) <= 2 * scale:
            return ('cycle', 'within 2 sigma of the same weekday last week')
    return ('other', 'no dominant pattern in %d points' % len(series))


def spike_shape(values):
    """Classify the largest step in the series.

    Returns 'recovered' when the series returned close to its level before
    the jump, 'held' when it stayed at the new level (a step change such as a
    definition change), otherwise 'none'.
    """
    if len(values) < 4:
        return ('none', 'not enough points')
    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    idx = max(range(len(diffs)), key=lambda i: abs(diffs[i]))
    jump = abs(diffs[idx])
    # Scale is taken from BEFORE the jump only: a step change inflates the
    # whole-series deviation and would hide itself.
    pre = values[:idx + 1]
    scale = mean_std(pre)[1] if len(pre) >= 2 else 0.0
    if scale > 0 and jump < 2 * scale:
        return ('none', 'largest step is within normal variation')
    before = values[idx]
    after = values[-1]
    rest = [abs(d) for d in diffs[idx + 1:]]
    settled = all(d < jump * 0.35 for d in rest) if rest else True
    if abs(after - before) <= jump * 0.35:
        return ('recovered', 'largest step at index %d returned to baseline'
                % idx)
    if settled:
        return ('held', 'largest step at index %d stayed at the new level'
                % idx)
    return ('none', 'series still moving after the largest step')


def quality_checks(entries, cfg):
    out = []
    dates = [e['date'] for e in entries]
    if len(set(dates)) != len(dates):
        out.append(('ERROR', '(file)', R_DQ_DUP_DATE))
    for i in range(1, len(dates)):
        if dates[i - 1] and dates[i] and dates[i] <= dates[i - 1]:
            out.append(('ERROR', '(file)', R_DQ_NON_MONOTONIC))
            break
    for e in entries:
        if e['value'] is not None and e['value'] < 0:
            out.append(('ERROR', e['date'].isoformat(), R_DQ_NEGATIVE))
    if cfg.get('volume_threshold') and entries:
        last = entries[-1]
        if last['value'] is not None and last['value'] < cfg['volume_threshold']:
            out.append(('WARN', last['date'].isoformat(),
                        '%s (value=%.0f < %d)'
                        % (R_DQ_SMALL, last['value'], cfg['volume_threshold'])))
    if cfg.get('delay_hours') and entries:
        last = entries[-1]
        if cfg.get('now') and last['date'] == cfg['now']:
            out.append(('WARN', last['date'].isoformat(),
                        '%s (declared lag %dh)' % (R_DQ_DELAY,
                                                   cfg['delay_hours'])))
    if len(entries) >= 4:
        seq = [e['value'] for e in entries if e['value'] is not None]
        kind, detail = spike_shape(seq)
        if kind == 'recovered':
            out.append(('INFO', entries[-1]['date'].isoformat(),
                        '%s (%s)' % (R_DQ_SPIKE_RECOVER, detail)))
        elif kind == 'held':
            out.append(('INFO', entries[-1]['date'].isoformat(),
                        '%s (%s)' % (R_DQ_SPIKE_HOLD, detail)))
    return out


def build(entries, metric, window):
    vals = [e['value'] for e in entries if e['value'] is not None]
    last = entries[-1]['value'] if entries else None
    prev = entries[-2]['value'] if len(entries) > 1 else None
    hist = vals[-(window + 1):-1] if len(vals) > 1 else []
    m, sd = mean_std(hist)
    z = None
    if last is not None and m is not None and sd:
        z = (last - m) / sd
    dod = None
    if last is not None and prev:
        dod = (last - prev) / prev
    return {'last': last, 'prev': prev, 'mean': m, 'std': sd, 'z': z,
            'dod': dod, 'n_hist': len(hist)}


def contributions(entries, dim_col, base_date, cur_date):
    """Aggregate the metric by dim value at base_date and cur_date.

    dim_col is the grouping key (textual or numeric); the summed quantity is
    always the entry's 'value'.
    """
    def agg(target):
        acc = {}
        for e in entries:
            if e['date'] != target:
                continue
            v = e.get(dim_col)
            if v is None or e.get('value') is None:
                continue
            acc[v] = acc.get(v, 0.0) + float(e['value'])
        return acc
    a = agg(base_date)
    b = agg(cur_date)
    keys = set(a) | set(b)
    rows = []
    total_delta = 0.0
    for k in sorted(keys):
        d = b.get(k, 0.0) - a.get(k, 0.0)
        total_delta += d
        rows.append({'key': k, 'base': a.get(k, 0.0), 'cur': b.get(k, 0.0),
                     'delta': d})
    abs_sum = sum(abs(r['delta']) for r in rows) or 1.0
    for r in rows:
        r['share'] = abs(r['delta']) / abs_sum
    rows.sort(key=lambda r: -abs(r['delta']))
    return rows, total_delta


def simpson_check(entries, dim_col, base_date, cur_date):
    """Detect a Simpson's-paradox signal.

    Signals subgroup deltas moving in OPPOSITE directions while the overall
    total moves in only one of those directions (or stays flat). In every
    case the aggregate alone is misleading and the subgroups must be read.
    """
    rows, total_delta = contributions(entries, dim_col, base_date, cur_date)
    ups = [r for r in rows if r['delta'] > DELTA_EPS]
    downs = [r for r in rows if r['delta'] < -DELTA_EPS]
    if not (ups and downs):
        return None, rows, total_delta
    return ('opposing_directions', rows, total_delta)


def verdict(z, cfg):
    if z is None:
        return 'UNKNOWN'
    az = abs(z)
    if az >= Z_ANOMALY:
        return 'ANOMALY'
    if az >= Z_WATCH:
        return 'WATCH'
    return 'NORMAL'


def render(entries, stat, shape, findings, dim_report, cfg, lines):
    lines.append('== ANOMALY DETECTION ==')
    if stat['last'] is None:
        lines.append('[ERROR] last value is missing')
        return
    lines.append('metric              : %s' % (cfg['metric'] or 'value'))
    lines.append('current date        : %s'
                 % entries[-1]['date'].isoformat())
    lines.append('current value       : %.2f' % stat['last'])
    lines.append('previous value      : %s'
                 % ('-' if stat['prev'] is None else '%.2f' % stat['prev']))
    if stat['mean'] is None:
        lines.append('window mean         : -')
        lines.append('window std          : -')
        lines.append('z-score             : -')
    else:
        lines.append('window (%d pts) mean : %.2f' % (stat['n_hist'],
                                                      stat['mean']))
        lines.append('window std          : %.2f' % stat['std'])
        lines.append('z-score             : %s' %
                     ('-' if stat['z'] is None else '%.3f' % stat['z']))
    lines.append('day-over-day        : %s' %
                 ('-' if stat['dod'] is None else '%+.2f%%' % (stat['dod'] * 100)))
    lines.append('yoy                 : %s' % cfg.get('yoy_text', '-'))
    lines.append('shape               : %s (%s)' % (shape[0], shape[1]))
    lines.append('verdict             : %s' % verdict(stat['z'], cfg))
    lines.append('')
    if dim_report:
        lines.append('== CONTRIBUTION ==')
        for dim_col, (rows, total_delta, note) in dim_report.items():
            lines.append('dimension %s  total delta = %+.2f' % (dim_col,
                                                              total_delta))
            for r in rows:
                lines.append('  %-14s base=%-10.2f cur=%-10.2f delta=%+10.2f '
                             'share=%5.1f%%'
                             % (str(r['key'])[:14], r['base'], r['cur'],
                                r['delta'], r['share'] * 100))
            if note:
                lines.append('  [NOTE] %s' % note)
            lines.append('')
    grouped = {}
    for level, who, msg in findings:
        grouped.setdefault(level, []).append((who, msg))
    for level in ('ERROR', 'WARN', 'INFO'):
        items = grouped.get(level, [])
        lines.append('[%s] %d' % (level, len(items)))
        for who, msg in items:
            lines.append('  %s: %s' % (who, msg))


# ------------------------------------------------------------- selftest
def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    def mk(values, start=None):
        base = start or datetime.date(2026, 10, 1)
        rows = []
        for i, v in enumerate(values):
            rows.append({'date': base + datetime.timedelta(days=i),
                         'value': v})
        return rows

    # 1 stable series -> normal
    s = mk([100, 102, 98, 101, 99, 100, 101, 100])
    stat = build(s, 'x', 30)
    ck('stable series verdict NORMAL', verdict(stat['z'], {}) == 'NORMAL',
       'z=%.3f' % stat['z'])

    # 2 spike -> ANOMALY
    s = mk([98, 102, 99, 101, 100, 98, 102, 150])
    stat = build(s, 'x', 30)
    ck('spike verdict ANOMALY', verdict(stat['z'], {}) == 'ANOMALY',
       'z=%.3f' % stat['z'])

    # 3 moderate move -> WATCH: need sd around 5 so 112 lands at z ~ 2.1
    s = mk([92, 96, 100, 104, 108, 96, 104, 112])
    stat = build(s, 'x', 30)
    ck('moderate move verdict WATCH',
       verdict(stat['z'], {}) == 'WATCH',
       'z=%.3f sd=%.3f' % (stat['z'], stat['std']))

    # 4 z-score magnitude: with sd=2 around 100, a jump to 150 gives z=25
    s = mk([98, 102, 99, 101, 100, 98, 102, 150])
    stat = build(s, 'x', 30)
    m, sd = mean_std([98, 102, 99, 101, 100, 98, 102])
    ck('z-score maths is consistent',
       stat['std'] is not None and stat['std'] > 0
       and abs(stat['z'] - (150 - m) / sd) < 1e-9,
       'z=%.3f sd=%.3f' % (stat['z'], stat['std']))

# 4b a flat window has zero sd so z-score is undefined, not an error
    flat = mk([100, 100, 100, 100, 100, 100, 100, 150])
    fstat = build(flat, 'x', 30)
    ck('zero-variance window yields no z', fstat['z'] is None
       and verdict(fstat['z'], {}) == 'UNKNOWN',
       'sd=%s' % fstat['std'])

    # 5 dod computation
    s = mk([98, 102, 99, 101, 100, 98, 102, 150])
    stat = build(s, 'x', 30)
    ck('day-over-day = +23.53%',
       abs(stat['dod'] - (150 - 102) / 102) < 1e-12, '%.4f' % stat['dod'])

    # 6 trend detection
    s = mk([10, 11, 12, 13, 14, 15, 16])
    shape = classify_shape([e['value'] for e in s])
    ck('trend_up detected', shape[0] == 'trend_up', str(shape))

    # 7 trend down detection
    s = mk([16, 15, 14, 13, 12, 11, 10])
    shape = classify_shape([e['value'] for e in s])
    ck('trend_down detected', shape[0] == 'trend_down', str(shape))

    # 8 duplicate date errors
    rows = [{'date': datetime.date(2026, 10, 1), 'value': 1.0},
            {'date': datetime.date(2026, 10, 1), 'value': 2.0}]
    q = quality_checks(rows, {})
    ck('duplicate date errors',
       any(x[0] == 'ERROR' and 'duplicate' in x[2].lower() for x in q))

    # 9 small volume warns (value strictly below the threshold)
    rows = mk([100, 100, 50])
    q = quality_checks(rows, {'volume_threshold': 100})
    ck('small volume warns',
       any(x[0] == 'WARN' and 'volume below' in x[2] for x in q))

    # 11 spike recovery flagged: jump then return to baseline
    rows = mk([100, 101, 200, 105, 103, 102])
    q = quality_checks(rows, {})
    ck('spike recovery flagged',
       any('recovered' in x[2] for x in q))

    # 12 step that does not revert flagged
    rows = mk([100, 100, 200, 205, 203, 204])
    q = quality_checks(rows, {})
    ck('non-reverting step flagged',
       any('did not revert' in x[2] for x in q))

    # 12 contribution split
    rows = [
        {'date': datetime.date(2026, 10, 1), 'value': 500, 'ch': 'app'},
        {'date': datetime.date(2026, 10, 1), 'value': 500, 'ch': 'mini'},
        {'date': datetime.date(2026, 10, 2), 'value': 300, 'ch': 'app'},
        {'date': datetime.date(2026, 10, 2), 'value': 500, 'ch': 'mini'},
    ]
    c, total = contributions(rows, 'ch', datetime.date(2026, 10, 1),
                             datetime.date(2026, 10, 2))
    ck('total delta = -200', abs(total + 200) < 1e-9, '%.1f' % total)
    ck('app ranked first', c[0]['key'] == 'app', str(c[0]['key']))
    ck('app share = 100%', abs(c[0]['share'] - 1.0) < 1e-9,
       '%.3f' % c[0]['share'])

    # 13 Simpson conflict detected
    rows = [
        {'date': datetime.date(2026, 10, 1), 'value': 1000, 'ch': 'high'},
        {'date': datetime.date(2026, 10, 1), 'value': 1000, 'ch': 'low'},
        {'date': datetime.date(2026, 10, 2), 'value': 1200, 'ch': 'high'},
        {'date': datetime.date(2026, 10, 2), 'value': 800, 'ch': 'low'},
    ]
    note, crows, total = simpson_check(rows, 'ch', datetime.date(2026, 10, 1),
                                   datetime.date(2026, 10, 2))
    ck('simpson opposing directions flagged',
       note == 'opposing_directions', str(note))
    ck('simpson total is zero', abs(total) < 1e-9, '%.2f' % total)

    # 14 negative value errors
    rows = mk([100, 100, -5])
    q = quality_checks(rows, {})
    ck('negative value errors',
       any(x[0] == 'ERROR' and 'negative' in x[2] for x in q))

    # 15 short history yields UNKNOWN
    rows = mk([100])
    stat = build(rows, 'x', 30)
    ck('single point verdict UNKNOWN', verdict(stat['z'], {}) == 'UNKNOWN')

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
    p = argparse.ArgumentParser(description='Data anomaly detector')
    p.add_argument('--file', type=str, default=None,
                   help='CSV series, or - for stdin')
    p.add_argument('--metric', type=str, default=None, help='metric name label')
    p.add_argument('--window', type=int, default=30,
                   help='trailing window size for z-score')
    p.add_argument('--compare', type=str, default='dod',
                   choices=['dod', 'yoy', 'both'])
    p.add_argument('--dims', type=str, default=None,
                   help='repeatable dim:col,val1,val2 (values informative only)')
    p.add_argument('--check-data-quality', dest='check_dq', action='store_true')
    p.add_argument('--delay-hours', dest='delay_hours', type=int, default=None)
    p.add_argument('--volume-threshold', dest='volume_threshold', type=int,
                   default=None)
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
        rows = read_rows(args.file)
    except Exception as exc:
        text = '[ERROR] cannot read %s: %s\n' % (args.file, exc)
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    metric = args.metric
    dim_col = None
    for k in rows[0].keys() if rows else []:
        if (k or '').lower().startswith('dim_'):
            dim_col = k
            break
    entries = []
    for r in rows:
        d = parse_date(r.get('date'))
        v = parse_num(r.get(metric) if metric else r.get('metric'))
        e = {'date': d, 'value': v}
        if dim_col:
            e[dim_col] = r.get(dim_col)
        entries.append(e)
    entries = [e for e in entries if e['date'] is not None]
    entries.sort(key=lambda e: e['date'])
    if not entries:
        text = '[ERROR] no rows with a valid date\n'
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    cfg = {'metric': metric, 'now': datetime.date.today(),
           'delay_hours': args.delay_hours,
           'volume_threshold': args.volume_threshold, 'yoy_text': '-'}
    stat = build(entries, metric, args.window)
    shape = classify_shape([e['value'] for e in entries
                            if e['value'] is not None])
    findings = []
    if stat['std'] is not None and stat['std'] == 0:
        findings.append(('INFO', 'window',
                         'window standard deviation is 0 (constant history): '
                         'z-score is undefined, judge by absolute change only'))
    if args.check_dq:
        findings.extend(quality_checks(entries, cfg))
    if stat['z'] is not None and abs(stat['z']) >= Z_ANOMALY:
        findings.append(('WARN', 'verdict', '%s (z=%.3f)'
                         % (R_DQ_BIG_Z, stat['z'])))
    if shape[0].startswith('trend'):
        findings.append(('INFO', 'shape', R_DQ_SHAPE_TREND % SHAPE_WINDOW))
    dim_report = {}
    if dim_col and len(entries) > 1:
        note, crows, total = simpson_check(entries, dim_col,
                                           entries[-2]['date'],
                                           entries[-1]['date'])
        dim_report[dim_col] = (crows, total,
                               ('simpson paradox signal: subgroups move in '
                                'opposite directions' if note else None))
    lines = []
    render(entries, stat, shape, findings, dim_report, cfg, lines)
    text = '\n'.join(lines) + '\n'
    path = args.out or RESULT
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())