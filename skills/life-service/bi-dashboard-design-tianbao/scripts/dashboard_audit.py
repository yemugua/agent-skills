#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BI dashboard metric-list auditor.

Checks a metric list for layer quotas, definition completeness, chart-type
suitability and color semantics, then grades findings as ERROR / WARN / INFO.

Usage
  python dashboard_audit.py --file metrics.csv
  python dashboard_audit.py --file metrics.csv --max-total 12 --check-chart
  python dashboard_audit.py --file metrics.csv --check-chart --check-color
  python dashboard_audit.py --file - < metrics.csv
  python dashboard_audit.py --selftest

CSV header (required columns: metric, layer, period, denominator, baseline,
dimension)
  metric,layer,chart,period,denominator,baseline,dimension,version,latency,
  owner,updated_at,color
"""
import argparse
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

LAYERS = {
    'outcome': {'label': 'Result / outcome metric',
                'default_max': 6, 'min': 3},
    'driver': {'label': 'Process / driver metric',
               'default_max': 8, 'min': 4},
    'guardrail': {'label': 'Health / guardrail metric',
                  'default_max': 5, 'min': 2},
}

REQUIRED_FIELDS = ('metric', 'layer', 'period', 'denominator', 'baseline',
                   'dimension')
RECOMMENDED_FIELDS = ('version', 'latency', 'owner', 'updated_at')

# chart -> allowed data shapes
CHART_OK = {
    'line': ('time_series',),
    'area': ('time_series_composition',),
    'stacked_area': ('time_series_composition',),
    'bar': ('category_compare',),
    'hbar': ('category_compare', 'single_value'),
    'pie': ('composition_pie',),
    'bar100': ('composition_pie',),
    'scatter': ('correlation',),
    'funnel': ('funnel',),
    'histogram': ('distribution',),
    'box': ('distribution',),
    'heatmap': ('time_category',),
    'map': ('geo',),
    'number': ('single_value',),
    'gauge': ('single_value',),
    'table': ('detail', 'single_value', 'category_compare'),
}

# data shape -> allowed charts (inverse)
SHAPE_CHART = {
    'time_series': ('line',),
    'time_series_composition': ('area', 'stacked_area', 'bar'),
    'category_compare': ('bar', 'hbar'),
    'composition_pie': ('pie', 'bar100', 'stacked_area'),
    'correlation': ('scatter',),
    'funnel': ('funnel', 'hbar'),
    'distribution': ('histogram', 'box'),
    'geo': ('map',),
    'time_category': ('heatmap',),
    'single_value': ('number', 'hbar', 'table'),
    'detail': ('table',),
}

# Words that mark a driver-layer metric misfiled as an outcome metric
PROCESS_WORDS = ('click', 'impression', 'pv', 'uv', 'view', 'exposure',
                 'visit', 'session', 'scroll', 'hover', 'entry',
                 'landing', 'cart', 'browse')
BASELINE_OK = ('yoy', 'mom', 'wow', 'dod', 'none', 'no', 'target')
# words that may appear in a dimension column
DIM_WORDS = ('channel', 'source', 'media', 'region', 'province', 'city',
             'country', 'device', 'platform', 'os', 'app', 'version',
             'channelid', 'newold', 'new', 'old', 'gender', 'age',
             'tier', 'segment', 'group', 'level', 'product', 'sku',
             'category', 'industry', 'userid', 'cohort')
#  words that may appear in a denominator description
DENOM_WORDS = ('uv', 'pv', 'user', 'session', 'visit', 'order', 'count',
               'total', 'exposure', 'impression', 'view', 'click', 'entry',
               'denominator', 'exposurecount', 'totaluser', 'divisor',
               'population', 'base', 'start', 'sum')
COLOR_BAD = ('rainbow', 'rainbowpalette', 'neon')
COLOR_OK = ('trend', 'status', 'single', 'pair', 'sequential', 'diverging')

# Chinese tokens expressed as escapes to keep this source pure ASCII
C_PROC_HINT = 'process quantity'
C_GO_HINT = 'missing dimension: only a total value is on the dashboard'
C_TIME_HINT = 'missing updated_at: users may mistake partial-day data for a full day'
C_OWNER_HINT = 'missing owner'
C_VER_HINT = 'missing definition version'
C_LAT_HINT = 'missing data latency'
C_DEN_HINT = 'missing denominator basis'
C_BASE_HINT = 'missing comparison baseline: yoy/mom/none must be explicit'
C_BAD_COLOR = 'rainbow palette is not allowed for unordered categories'
C_LOWER = 'lowered'


def _norm(v):
    return (v or '').strip()


def _has_any(text, words):
    t = (text or '').lower()
    return any(w in t for w in words)


def audit(rows, max_result=6, max_driver=8, max_guard=5, max_total=12,
          check_chart=False, check_color=False, shape_by_metric=None):
    shape_by_metric = shape_by_metric or {}
    findings = []
    counts = {'outcome': 0, 'driver': 0, 'guardrail': 0}
    layers_seen = set()
    for idx, row in enumerate(rows, 1):
        metric = _norm(row.get('metric'))
        if not metric:
            findings.append(('ERROR', idx, metric or '(unnamed)',
                             'empty metric name'))
            continue
        layer = _norm(row.get('layer')).lower()
        if layer not in LAYERS:
            findings.append(('ERROR', idx, metric,
                             'unknown layer %r: use outcome/driver/guardrail'
                             % layer))
        else:
            counts[layer] += 1
            layers_seen.add(layer)
            if layer == 'outcome' and _has_any(metric, PROCESS_WORDS):
                findings.append(('WARN', idx, metric,
                                 'outcome layer contains a process quantity; '
                                 + C_PROC_HINT))
        for field in REQUIRED_FIELDS:
            if not _norm(row.get(field)):
                hint = {
                    'period': C_TIME_HINT,
                    'denominator': C_DEN_HINT,
                    'baseline': C_BASE_HINT,
                    'dimension': C_GO_HINT,
                }.get(field, 'missing %s' % field)
                findings.append(('ERROR', idx, metric, hint))
        if _norm(row.get('baseline')) and \
                not _has_any(row.get('baseline'), BASELINE_OK):
            findings.append(('WARN', idx, metric,
                             'unrecognized baseline %r' % row.get('baseline')))
        dim = _norm(row.get('dimension'))
        if dim and not _has_any(dim, DIM_WORDS):
            findings.append(('WARN', idx, metric,
                             'dimension %r does not look like a split dimension'
                             % dim))
        den = _norm(row.get('denominator'))
        if den and not _has_any(den, DENOM_WORDS) and \
                not any(c.isdigit() for c in den):
            findings.append(('WARN', idx, metric,
                             'denominator %r is not specific' % den))
        for field, hint in (('version', C_VER_HINT), ('latency', C_LAT_HINT),
                            ('owner', C_OWNER_HINT), ('updated_at', C_TIME_HINT)):
            if not _norm(row.get(field)):
                findings.append(('INFO', idx, metric, hint))
        if check_chart:
            chart = _norm(row.get('chart')).lower()
            shape = shape_by_metric.get(metric, '')
            if not chart:
                findings.append(('WARN', idx, metric,
                                 'no chart selected but --check-chart is on'))
            elif chart not in CHART_OK:
                findings.append(('WARN', idx, metric,
                                 'unknown chart type %r' % chart))
            elif shape and chart not in SHAPE_CHART.get(shape, ()):
                findings.append(('WARN', idx, metric,
                                 'chart %s mismatches data shape %s; allowed: %s'
                                 % (chart, shape,
                                    ','.join(SHAPE_CHART.get(shape, ())))))
                if chart == 'pie':
                    findings.append(('WARN', idx, metric,
                                     'pie chart: a reader cannot judge '
                                     'differences; use hbar when categories > 3'))
                if chart == 'bar' and shape == 'time_series':
                    findings.append(('WARN', idx, metric,
                                     'bar chart for a time series: use line'))
                if chart == 'line' and shape == 'category_compare':
                    findings.append(('WARN', idx, metric,
                                     'line chart for categories: use hbar'))
                if chart == 'gauge':
                    findings.append(('INFO', idx, metric,
                                     'gauge occupies large area with low '
                                     'precision; prefer a number card'))
        if check_color:
            color = _norm(row.get('color')).lower()
            if not color:
                findings.append(('WARN', idx, metric,
                                 'no color semantics declared'))
            elif _has_any(color, COLOR_BAD):
                findings.append(('ERROR', idx, metric, C_BAD_COLOR))
            elif color not in COLOR_OK:
                findings.append(('WARN', idx, metric,
                                 'unrecognized color semantics %r' % color))

    for layer, cap in (('outcome', max_result), ('driver', max_driver),
                       ('guardrail', max_guard)):
        if counts[layer] > cap:
            findings.append(('ERROR', 0, layer,
                             'quota exceeded: %d > %d' % (counts[layer], cap)))
        elif counts[layer] and counts[layer] < LAYERS[layer]['min']:
            findings.append(('INFO', 0, layer,
                             'only %d metrics in this layer (min %d); the layer '
                             'may be under-populated'
                             % (counts[layer], LAYERS[layer]['min'])))
    missing = [k for k in LAYERS if k not in layers_seen]
    if missing:
        findings.append(('ERROR', 0, '(board)',
                         'layer never used: %s' % ','.join(sorted(missing))))
    total = sum(counts.values())
    if total > max_total:
        findings.append(('ERROR', 0, '(board)',
                         'total metrics %d > %d: split into two levels'
                         % (total, max_total)))
    return {'findings': findings, 'counts': counts, 'total': total}


def render(res, lines):
    lines.append('== BI DASHBOARD AUDIT ==')
    lines.append('outcome=%d driver=%d guardrail=%d total=%d'
                 % (res['counts']['outcome'], res['counts']['driver'],
                    res['counts']['guardrail'], res['total']))
    order = {'ERROR': 0, 'WARN': 1, 'INFO': 2}
    grouped = {}
    for level, idx, who, msg in res['findings']:
        grouped.setdefault(level, []).append((idx, who, msg))
    for level in ('ERROR', 'WARN', 'INFO'):
        items = grouped.get(level, [])
        lines.append('')
        lines.append('[%s] %d' % (level, len(items)))
        for idx, who, msg in sorted(items, key=lambda t: (order[level], t[0])):
            tag = ('#%d ' % idx) if idx else ''
            lines.append('  %s%s: %s' % (tag, who, msg))
    err = len(grouped.get('ERROR', []))
    warn = len(grouped.get('WARN', []))
    lines.append('')
    if err:
        lines.append('VERDICT: NOT READY (errors=%d warns=%d)' % (err, warn))
    elif warn:
        lines.append('VERDICT: READY WITH WARNINGS (warns=%d)' % warn)
    else:
        lines.append('VERDICT: READY')


def sample_rows():
    return [
        {'metric': 'Paid order revenue', 'layer': 'outcome', 'chart': 'line',
         'period': 'natural day Asia/Shanghai', 'denominator': 'n/a',
         'baseline': 'yoy', 'dimension': 'channel,device,newold',
         'version': 'v3.1', 'latency': 'T+1 08:00', 'owner': 'data-gw',
         'updated_at': '2026-10-10 08:00', 'color': 'trend'},
        {'metric': 'Active users', 'layer': 'outcome', 'chart': 'number',
         'period': 'natural day', 'denominator': 'n/a', 'baseline': 'mom',
         'dimension': 'channel', 'version': 'v2', 'latency': 'T+1',
         'owner': 'data-gw', 'updated_at': '2026-10-10 08:00',
         'color': 'trend'},
        {'metric': 'Cumulative tenure', 'layer': 'outcome', 'chart': 'number',
         'period': 'natural day', 'denominator': 'n/a', 'baseline': 'mom',
         'dimension': 'channel', 'version': 'v1', 'latency': 'T+1',
         'owner': 'data-gw', 'updated_at': '2026-10-10 08:00',
         'color': 'trend'},
        {'metric': 'Crash rate', 'layer': 'guardrail', 'chart': 'line',
         'period': 'natural day', 'denominator': 'total session count',
         'baseline': 'dod', 'dimension': 'platform,version',
         'version': 'v1', 'latency': 'T+1', 'owner': 'qa',
         'updated_at': '2026-10-10 08:00', 'color': 'status'},
        {'metric': 'Refund rate', 'layer': 'guardrail', 'chart': 'line',
         'period': 'natural day', 'denominator': 'order count',
         'baseline': 'mom', 'dimension': 'category,channel',
         'version': 'v1', 'latency': 'T+1', 'owner': 'ops',
         'updated_at': '2026-10-10 08:00', 'color': 'status'},
        {'metric': 'Checkout conversion rate', 'layer': 'driver',
         'chart': 'funnel', 'period': 'natural day',
         'denominator': 'arrival at settlement page uv',
         'baseline': 'yoy', 'dimension': 'channel,device',
         'version': 'v1', 'latency': 'T+1', 'owner': 'growth',
         'updated_at': '2026-10-10 08:00', 'color': 'trend'},
        {'metric': 'Average order value', 'layer': 'driver', 'chart': 'line',
         'period': 'natural day', 'denominator': 'order count',
         'baseline': 'mom', 'dimension': 'channel,category',
         'version': 'v1', 'latency': 'T+1', 'owner': 'growth',
         'updated_at': '2026-10-10 08:00', 'color': 'trend'},
        {'metric': 'Delivery lead time', 'layer': 'driver', 'chart': 'hbar',
         'period': 'natural day', 'denominator': 'delivered order count',
         'baseline': 'mom', 'dimension': 'region,channel',
         'version': 'v1', 'latency': 'T+1', 'owner': 'supply',
         'updated_at': '2026-10-10 08:00', 'color': 'single'},
        {'metric': 'Add-to-cart rate', 'layer': 'driver', 'chart': 'funnel',
         'period': 'natural day', 'denominator': 'product page uv',
         'baseline': 'mom', 'dimension': 'channel,device',
         'version': 'v1', 'latency': 'T+1', 'owner': 'growth',
         'updated_at': '2026-10-10 08:00', 'color': 'trend'},
        {'metric': 'Search success rate', 'layer': 'driver', 'chart': 'line',
         'period': 'natural day', 'denominator': 'search uv',
         'baseline': 'mom', 'dimension': 'channel',
         'version': 'v1', 'latency': 'T+1', 'owner': 'search',
         'updated_at': '2026-10-10 08:00', 'color': 'trend'},
        {'metric': 'Favorite rate', 'layer': 'driver', 'chart': 'line',
         'period': 'natural day', 'denominator': 'detail page uv',
         'baseline': 'mom', 'dimension': 'channel,category',
         'version': 'v1', 'latency': 'T+1', 'owner': 'growth',
         'updated_at': '2026-10-10 08:00', 'color': 'trend'},
        {'metric': 'Review submit rate', 'layer': 'driver', 'chart': 'line',
         'period': 'natural day', 'denominator': 'order count',
         'baseline': 'mom', 'dimension': 'channel,category',
         'version': 'v1', 'latency': 'T+1', 'owner': 'growth',
         'updated_at': '2026-10-10 08:00', 'color': 'trend'},
    ]


# --------------------------------------------------------------- selftest
def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    rows = sample_rows()

    # 1 clean board passes
    res = audit(rows, check_chart=True, check_color=True,
                shape_by_metric={'Paid order revenue': 'time_series',
                                 'Active users': 'single_value',
                                 'Crash rate': 'time_series',
                                 'Refund rate': 'time_series',
                                 'Checkout conversion rate': 'funnel',
                                 'Average order value': 'time_series',
                                 'Delivery lead time': 'category_compare',
                                 'Add-to-cart rate': 'funnel',
                                 'Search success rate': 'time_series',
                                 'Favorite rate': 'time_series',
                                 'Review submit rate': 'time_series',
                                 'Cumulative tenure': 'single_value'})
    errs = [f for f in res['findings'] if f[0] == 'ERROR']
    ck('clean board has no errors', not errs,
       str([f[3] for f in errs][:2]))

    # 2 counts
    ck('counts outcome=3 driver=7 guardrail=2',
       (res['counts']['outcome'], res['counts']['driver'],
        res['counts']['guardrail']) == (3, 7, 2), str(res['counts']))

    # 3 total within cap
    ck('total 12 <= 12', res['total'] == 12, str(res['total']))

    # 4 outcome layer containing a process quantity
    bad = [dict(r) for r in rows]
    bad[0] = dict(bad[0], metric='Pv click volume')
    res2 = audit(bad)
    ck('process quantity in outcome layer warns',
       any(f[0] == 'WARN' and 'process' in f[3] for f in res2['findings']))

    # 5 missing dimension
    bad = [dict(r) for r in rows]
    bad[1] = dict(bad[1], dimension='')
    res3 = audit(bad)
    ck('missing dimension is an error',
       any(f[0] == 'ERROR' and 'dimension' in f[3] for f in res3['findings']))

    # 6 missing baseline
    bad = [dict(r) for r in rows]
    bad[1] = dict(bad[1], baseline='')
    res4 = audit(bad)
    ck('missing baseline is an error',
       any(f[0] == 'ERROR' and 'baseline' in f[3] for f in res4['findings']))

    # 7 quota exceeded
    many = rows + [dict(rows[5], metric='Extra driver %d' % i)
                   for i in range(5)]
    res5 = audit(many)
    ck('driver quota exceeded errors',
       any(f[0] == 'ERROR' and 'quota' in f[3] for f in res5['findings']))

    # 8 total cap exceeded
    res6 = audit(rows, max_total=8)
    ck('total cap exceeded errors',
       any(f[0] == 'ERROR' and 'split into two levels' in f[3]
           for f in res6['findings']))

    # 9 chart mismatch: pie for a funnel
    bad = [dict(r) for r in rows]
    bad[5] = dict(bad[5], chart='pie')
    res7 = audit(bad, check_chart=True,
                 shape_by_metric={'Checkout conversion rate': 'funnel'})
    ck('pie for funnel warns',
       any(f[0] == 'WARN' and 'mismatch' in f[3] for f in res7['findings']))

    # 10 rainbow palette is an error
    bad = [dict(r) for r in rows]
    bad[1] = dict(bad[1], color='rainbow')
    res8 = audit(bad, check_color=True)
    ck('rainbow palette errors',
       any(f[0] == 'ERROR' and 'rainbow' in f[3] for f in res8['findings']))

    # 11 missing layer errors
    nodriver = [r for r in rows if r['layer'] != 'driver']
    res9 = audit(nodriver)
    ck('never-used layer errors',
       any(f[0] == 'ERROR' and 'never used' in f[3] for f in res9['findings']))

    # 12 info hints for recommended fields
    bad = [dict(r) for r in rows]
    for r in bad:
        r['owner'] = ''
        r['updated_at'] = ''
    res10 = audit(bad)
    infos = [f for f in res10['findings'] if f[0] == 'INFO']
    ck('owner/updated_at produce INFO hints', len(infos) >= 12, str(len(infos)))

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


def read_rows(path):
    if path == '-':
        data = sys.stdin.read()
    else:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            data = fh.read()
    reader = csv.DictReader(io.StringIO(data))
    return [dict(r) for r in reader]


def build_parser():
    p = argparse.ArgumentParser(
        description='BI dashboard metric list auditor')
    p.add_argument('--file', type=str, default=None,
                   help='CSV metric list, or - for stdin')
    p.add_argument('--max-result', dest='max_result', type=int, default=6)
    p.add_argument('--max-driver', dest='max_driver', type=int, default=8)
    p.add_argument('--max-guard', dest='max_guard', type=int, default=5)
    p.add_argument('--max-total', dest='max_total', type=int, default=12)
    p.add_argument('--check-chart', dest='check_chart', action='store_true')
    p.add_argument('--check-color', dest='check_color', action='store_true')
    p.add_argument('--shapes', type=str, default=None,
                   help='JSON map metric->data shape for chart checking')
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
    shapes = {}
    if args.shapes:
        with open(args.shapes, 'r', encoding='utf-8') as fh:
            shapes = json.load(fh)
    if not shapes:
        # infer the shape from the chart type when nothing was supplied
        rev = {}
        for chart, shapes_ in CHART_OK.items():
            for s in shapes_:
                rev.setdefault(s, []).append(chart)
        for r in rows:
            m = _norm(r.get('metric'))
            c = _norm(r.get('chart')).lower()
            if m and c in rev:
                shapes[m] = rev[c][0]
    res = audit(rows, args.max_result, args.max_driver, args.max_guard,
                args.max_total, args.check_chart, args.check_color, shapes)
    lines = []
    render(res, lines)
    text = '\n'.join(lines) + '\n'
    path = args.out or RESULT
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())