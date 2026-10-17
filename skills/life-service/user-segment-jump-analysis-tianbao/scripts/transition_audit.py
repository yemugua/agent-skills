#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User segment transition matrix auditor.

Computes the prev->current layer transition matrix, per-layer retention /
upgrade / downgrade rates, overall upgrade and net upgrade rates, ranks the
top leakage channels, verifies three identities and flags definition drift.

Usage
  python transition_audit.py --file transition.csv \
      --layers "S4,S3,S2,S1" --prev-col prev_layer --cur-col cur_layer
  python transition_audit.py --file transition.csv --layers "S4,S3,S2,S1" \
      --total-users 50000 --check-drift --threshold-version v1 \
      --prev-window 30d --cur-window 30d
  python transition_audit.py --selftest

CSV header (required: prev-layer-col, cur-layer-col; users optional)
  prev_layer,cur_layer,users
Layers in --layers must be ordered from HIGH to LOW.

Pure-ASCII source: all user-facing hints are ASCII strings.
"""
import argparse
import csv
import io
import os
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

CHANNEL_SHARE_HIGH = 0.20
CHANNEL_SHARE_MED = 0.08
CHANNEL_USERS_HIGH = 100
CHANNEL_USERS_MED = 30

NEWCOMER = '__new__'
LOST = '__lost__'

R_ROW = 'row-sum identity failed'
R_COL = 'column-sum identity failed'
R_RETENTION = 'layer retention plus outflow must equal 100%'
R_UNKNOWN_LAYER = 'layer value is not in --layers list'
R_ORDER = '--layers must be ordered from high to low'
R_DRIFT_WINDOW = 'window length differs between periods: everyone looks downgraded'
R_DRIFT_VERSION = 'threshold version mismatch: history must be recomputed'
R_DRIFT_COVER = 'layers do not cover all users: unclassified users must be listed'
R_LOW_N = 'leakage count < 30: too small to act on, watch the trend instead'
R_NO_ROWS = 'no usable rows in the input file'
R_DUP_LAYER = 'duplicate layer name in --layers'
R_RATE_OOB = 'layer rate outside [0, 1]: check the matrix orientation'


def read_rows(path):
    if path == '-':
        data = sys.stdin.read()
    else:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
            data = fh.read()
    return [dict(r) for r in csv.DictReader(io.StringIO(data))]


def build_matrix(rows, layers, prev_col, cur_col):
    idx = dict((name, i) for i, name in enumerate(layers))
    size = len(layers)
    mat = [[0.0 for _ in range(size)] for _ in range(size)]
    prev_total = dict((n, 0.0) for n in layers)
    cur_total = dict((n, 0.0) for n in layers)
    new_in = dict((n, 0.0) for n in layers)
    lost = dict((n, 0.0) for n in layers)
    unknown = 0.0
    total_count = 0.0
    for row in rows:
        p = (row.get(prev_col) or '').strip()
        c = (row.get(cur_col) or '').strip()
        raw = (row.get('users') or '').strip()
        w = 1.0
        if raw:
            try:
                w = float(raw)
            except ValueError:
                w = 1.0
        total_count += w
        if p not in idx or c not in idx:
            if p == NEWCOMER or c == LOST or p == '' or c == '':
                pass
            else:
                unknown += w
                continue
        if p == NEWCOMER:
            if c in idx:
                new_in[c] += w
            continue
        if c == LOST:
            if p in idx:
                lost[p] += w
            continue
        if p not in idx or c not in idx:
            unknown += w
            continue
        mat[idx[p]][idx[c]] += w
        prev_total[p] += w
        cur_total[c] += w
    return {'mat': mat, 'idx': idx, 'layers': layers,
            'prev_total': prev_total, 'cur_total': cur_total,
            'new_in': new_in, 'lost': lost, 'unknown': unknown,
            'total_count': total_count}


def analyze(cfg):
    findings = []
    layers = cfg['layers']
    idx = cfg['idx']
    mat = cfg['mat']
    size = len(layers)
    row_sums = [sum(mat[i]) for i in range(size)]
    col_sums = [sum(mat[i][j] for i in range(size)) for j in range(size)]
    covered_prev = sum(row_sums)
    covered_cur = sum(col_sums)
    for i, layer in enumerate(layers):
        exp_prev = cfg['prev_total'][layer]
        if abs(row_sums[i] - exp_prev) > 1e-6:
            findings.append(('ERROR', layer,
                             '%s (row=%.0f, prev total=%.0f)'
                             % (R_ROW, row_sums[i], exp_prev)))
        exp_cur = cfg['cur_total'][layer]
        if abs(col_sums[i] - exp_cur) > 1e-6:
            findings.append(('ERROR', layer,
                             '%s (col=%.0f, cur total=%.0f)'
                             % (R_COL, col_sums[i], exp_cur)))
    per_layer = []
    total_up = 0.0
    total_down = 0.0
    total_cells = sum(sum(r) for r in mat)
    for i, layer in enumerate(layers):
        base = row_sums[i]
        stay = mat[i][i]
        # layers are ordered HIGH -> LOW, so a SMALLER column index means a
        # HIGHER layer: j < i is an upgrade, j > i is a downgrade.
        up = sum(mat[i][j] for j in range(i))
        down = sum(mat[i][j] for j in range(i + 1, size))
        ret = (stay / base) if base > 0 else None
        up_rate = (up / base) if base > 0 else None
        down_rate = (down / base) if base > 0 else None
        if ret is not None:
            if ret < -1e-9 or ret > 1 + 1e-9:
                findings.append(('ERROR', layer, R_RATE_OOB))
            outflow = 1.0 - ret
            if abs(outflow - (up_rate + down_rate)) > 1e-9:
                findings.append(('ERROR', layer, R_RETENTION))
        per_layer.append({'layer': layer, 'base': base, 'stay': stay,
                          'up': up, 'down': down, 'ret': ret,
                          'up_rate': up_rate, 'down_rate': down_rate})
        total_up += up
        total_down += down
    overall_up = (total_up / total_cells) if total_cells > 0 else None
    overall_down = (total_down / total_cells) if total_cells > 0 else None
    net_up = (overall_up - overall_down) \
        if (overall_up is not None and overall_down is not None) else None
    channels = []
    for i in range(size):
        for j in range(i + 1, size):
            n = mat[i][j]
            if n > 0:
                channels.append({'from': layers[i], 'to': layers[j],
                                 'users': n, 'base': row_sums[i],
                                 'of_layer': n / row_sums[i] if row_sums[i] else 0.0,
                                 'of_down': n / total_down if total_down else 0.0})
    channels.sort(key=lambda c: -c['of_down'])
    for ch in channels[:3]:
        if ch['users'] < CHANNEL_USERS_MED:
            findings.append(('INFO', '%s->%s' % (ch['from'], ch['to']),
                             '%s (users=%.0f)' % (R_LOW_N, ch['users'])))
        elif ch['of_down'] >= CHANNEL_SHARE_HIGH and ch['users'] >= CHANNEL_USERS_HIGH:
            findings.append(('INFO', '%s->%s' % (ch['from'], ch['to']),
                             'priority: HIGH (of_down=%.1f%%, users=%.0f, '
                             'of_layer=%.1f%%)'
                             % (ch['of_down'] * 100, ch['users'],
                                ch['of_layer'] * 100)))
        elif ch['of_down'] >= CHANNEL_SHARE_MED:
            findings.append(('INFO', '%s->%s' % (ch['from'], ch['to']),
                             'priority: MED (of_down=%.1f%%, users=%.0f)'
                             % (ch['of_down'] * 100, ch['users'])))
    # coverage / drift
    if cfg['total_users']:
        delta = cfg['total_users'] - covered_prev
        if abs(delta) > 1e-6:
            findings.append((
                'ERROR', '(coverage)',
                '%s (prev covered=%.0f, total=%.0f, missing=%.0f)'
                % (R_DRIFT_COVER, covered_prev, cfg['total_users'], delta)))
    if cfg['check_drift']:
        if not cfg['prev_window'] or not cfg['cur_window']:
            findings.append(('ERROR', '(drift)',
                             'missing --prev-window / --cur-window'))
        elif cfg['prev_window'] != cfg['cur_window']:
            findings.append(('ERROR', '(drift)', R_DRIFT_WINDOW))
        if not cfg['threshold_version']:
            findings.append(('WARN', '(drift)',
                             'missing --threshold-version: cannot confirm the '
                             'threshold is unchanged between periods'))
    if cfg['unknown'] > 0:
        findings.append(('ERROR', '(unknown)',
                         '%d users have a layer value outside --layers'
                         % cfg['unknown']))
    return {'findings': findings, 'per_layer': per_layer,
            'row_sums': row_sums, 'col_sums': col_sums,
            'overall_up': overall_up, 'overall_down': overall_down,
            'net_up': net_up, 'channels': channels,
            'total_cells': total_cells,
            'new_in': cfg['new_in'], 'lost': cfg['lost']}


def render(cfg, res, lines):
    layers = cfg['layers']
    lines.append('== TRANSITION AUDIT ==')
    lines.append('layer order (high->low) : %s' % ' > '.join(layers))
    if cfg.get('threshold_version'):
        lines.append('threshold version     : %s' % cfg['threshold_version'])
    if cfg.get('prev_window') and cfg.get('cur_window'):
        lines.append('windows               : %s -> %s'
                     % (cfg['prev_window'], cfg['cur_window']))
    lines.append('')
    lines.append('matrix (rows=prev, cols=current):')
    head = '%-10s' % 'prev\\cur'
    for name in layers:
        head += '%10s' % name
    head += '%10s%10s' % ('lost', 'total')
    lines.append(head)
    for i, layer in enumerate(layers):
        line = '%-10s' % layer
        for j in range(len(layers)):
            line += '%10.0f' % cfg['mat'][i][j]
        line += '%10.0f%10.0f' % (cfg['lost'][layer], res['row_sums'][i])
        lines.append(line)
    line = '%-10s' % 'total'
    for j in range(len(layers)):
        line += '%10.0f' % res['col_sums'][j]
    line += '%10.0f%10.0f' % (sum(cfg['lost'].values()), res['total_cells'])
    lines.append(line)
    if sum(cfg['new_in'].values()) > 0:
        line = '%-10s' % 'newcomer'
        for j in range(len(layers)):
            line += '%10.0f' % cfg['new_in'][layers[j]]
        lines.append(line)
    lines.append('')
    lines.append('%-10s %10s %12s %10s %10s %12s'
                 % ('layer', 'prev', 'stay%', 'up%', 'down%', 'outflow%'))
    lines.append('-' * 70)
    for r in res['per_layer']:
        def f(v):
            return '-' if v is None else '%.2f' % (v * 100)
        outflow = None if r['ret'] is None else (1 - r['ret'])
        lines.append('%-10s %10.0f %12s %10s %10s %12s'
                     % (r['layer'], r['base'], f(r['ret']),
                        f(r['up_rate']), f(r['down_rate']), f(outflow)))
    lines.append('')
    def g(v):
        return '-' if v is None else '%.2f%%' % (v * 100)
    lines.append('overall upgrade : %s' % g(res['overall_up']))
    lines.append('overall downgrade: %s' % g(res['overall_down']))
    lines.append('net upgrade     : %s' % g(res['net_up']))
    lines.append('')
    lines.append('leakage channels (top):')
    if not res['channels']:
        lines.append('  (none)')
    for ch in res['channels'][:5]:
        lines.append('  %-6s -> %-6s users=%-8.0f of_down=%5.1f%% of_layer=%5.1f%%'
                     % (ch['from'], ch['to'], ch['users'],
                        ch['of_down'] * 100, ch['of_layer'] * 100))
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


def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    layers = ['S4', 'S3', 'S2', 'S1']
    rows = [
        {'prev_layer': 'S4', 'cur_layer': 'S4', 'users': '600'},
        {'prev_layer': 'S4', 'cur_layer': 'S3', 'users': '300'},
        {'prev_layer': 'S4', 'cur_layer': 'S2', 'users': '100'},
        {'prev_layer': 'S3', 'cur_layer': 'S4', 'users': '200'},
        {'prev_layer': 'S3', 'cur_layer': 'S3', 'users': '700'},
        {'prev_layer': 'S3', 'cur_layer': 'S1', 'users': '100'},
        {'prev_layer': 'S2', 'cur_layer': 'S2', 'users': '800'},
        {'prev_layer': 'S2', 'cur_layer': 'S1', 'users': '200'},
        {'prev_layer': 'S1', 'cur_layer': 'S1', 'users': '900'},
        {'prev_layer': 'S1', 'cur_layer': 'S2', 'users': '100'},
    ]
    cfg = {'layers': layers, 'prev_col': 'prev_layer',
           'cur_col': 'cur_layer', 'total_users': None,
           'check_drift': False, 'threshold_version': 'v1',
           'prev_window': '30d', 'cur_window': '30d'}
    built = build_matrix(rows, layers, 'prev_layer', 'cur_layer')
    cfg.update(built)
    res = analyze(cfg)

    # 1 row sums: S4=1000, S3=1000, S2=1000, S1=1000
    ck('row sums all 1000', all(abs(v - 1000) < 1e-9 for v in res['row_sums']),
       str(res['row_sums']))

    # 2 col sums: S4=800, S3=1000, S2=1000, S1=1200
    ck('col sums 800/1000/1000/1200',
       [round(v) for v in res['col_sums']] == [800, 1000, 1000, 1200],
       str([round(v) for v in res['col_sums']]))

    # 3 no identity errors
    errs = [f for f in res['findings'] if f[0] == 'ERROR']
    ck('identities hold', not errs, str([f[2] for f in errs][:2]))

    # 4 S4 retention 60%
    ck('S4 retention = 60%', abs(res['per_layer'][0]['ret'] - 0.6) < 1e-9,
       '%.4f' % res['per_layer'][0]['ret'])

    # 5 S4 upgrade 0% (S4 is the top layer, nothing above it)
    ck('S4 upgrade = 0%', abs(res['per_layer'][0]['up_rate']) < 1e-9,
       '%.4f' % res['per_layer'][0]['up_rate'])

    # 6 S1 downgrade 0% (S1 is the bottom layer)
    ck('S1 downgrade = 0%', abs(res['per_layer'][3]['down_rate']) < 1e-9,
       '%.4f' % res['per_layer'][3]['down_rate'])

    # 6b S4 downgrades to 400 of 1000 = 40%
    ck('S4 downgrade = 40%', abs(res['per_layer'][0]['down_rate'] - 0.4) < 1e-9,
       '%.4f' % res['per_layer'][0]['down_rate'])

    # 7 overall upgrade: S3->S4 (200) + S1->S2 (100) = 300 of 4000
    tot = res['total_cells']
    exp_up = (200 + 100) / tot
    ck('overall upgrade = 300/4000', abs(res['overall_up'] - exp_up) < 1e-12,
       '%.6f' % res['overall_up'])

    # 8 net upgrade: 300 up vs 700 down
    exp_down = (400 + 100 + 200) / tot
    ck('net upgrade = -0.10',
       abs(res['overall_down'] - exp_down) < 1e-12
       and abs(res['net_up'] - (exp_up - exp_down)) < 1e-12,
       'up=%.4f down=%.4f net=%.4f' % (res['overall_up'],
                                        res['overall_down'], res['net_up']))

    # 9 top leakage channel
    top = res['channels'][0]
    ck('top channel is S4->S3',
       (top['from'], top['to']) == ('S4', 'S3'),
       '%s->%s of_down=%.1f%%' % (top['from'], top['to'], top['of_down'] * 100))

    # 10 coverage mismatch errors
    bad = dict(cfg, total_users=5000)
    res10 = analyze(bad)
    ck('coverage mismatch errors',
       any(f[0] == 'ERROR' and 'coverage' in f[1] for f in res10['findings']))

    # 11 window drift errors
    res11 = analyze(dict(cfg, check_drift=True, cur_window='14d'))
    ck('window drift errors',
       any(f[0] == 'ERROR' and 'window' in f[2] for f in res11['findings']))

    # 12 missing threshold version warns
    res12 = analyze(dict(cfg, check_drift=True, threshold_version=None))
    ck('missing threshold version warns',
       any(f[0] == 'WARN' and 'threshold' in f[2] for f in res12['findings']))

    # 13 unknown layer value errors
    rows13 = list(rows) + [{'prev_layer': 'S9', 'cur_layer': 'S9', 'users': '5'}]
    b13 = build_matrix(rows13, layers, 'prev_layer', 'cur_layer')
    res13 = analyze(dict(cfg, **b13))
    ck('unknown layer errors',
       any(f[0] == 'ERROR' and 'outside' in f[2]
           for f in res13['findings']))

    # 14 newcomer and lost are handled separately
    rows14 = list(rows) + [{'prev_layer': '__new__', 'cur_layer': 'S3',
                            'users': '50'}]
    b14 = build_matrix(rows14, layers, 'prev_layer', 'cur_layer')
    res14 = analyze(dict(cfg, **b14))
    ck('newcomer column tracked separately',
       abs(b14['new_in']['S3'] - 50) < 1e-9,
       '%.0f' % b14['new_in']['S3'])

    # 15 small channel flagged as low-n
    rows15 = [{'prev_layer': 'S4', 'cur_layer': 'S3', 'users': '10'},
              {'prev_layer': 'S1', 'cur_layer': 'S1', 'users': '90'}]
    b15 = build_matrix(rows15, layers, 'prev_layer', 'cur_layer')
    res15 = analyze(dict(cfg, **b15))
    ck('tiny channel flagged low-n',
       any('too small to act on' in f[2] for f in res15['findings']))

    # 16 retention plus outflow equals one
    r = res['per_layer'][1]
    ck('retention + outflow = 1',
       abs((r['ret'] + (1 - r['ret'])) - 1) < 1e-12)

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
    p = argparse.ArgumentParser(description='Segment transition auditor')
    p.add_argument('--file', type=str, default=None,
                   help='CSV transition rows, or - for stdin')
    p.add_argument('--layers', type=str, default=None,
                   help='comma separated layers ordered HIGH to LOW, e.g. S4,S3,S2,S1')
    p.add_argument('--prev-col', dest='prev_col', default='prev_layer')
    p.add_argument('--cur-col', dest='cur_col', default='cur_layer')
    p.add_argument('--total-users', dest='total_users', type=float, default=None)
    p.add_argument('--check-drift', dest='check_drift', action='store_true')
    p.add_argument('--threshold-version', dest='threshold_version', default=None)
    p.add_argument('--prev-window', dest='prev_window', default=None)
    p.add_argument('--cur-window', dest='cur_window', default=None)
    p.add_argument('--out', type=str, default=None)
    p.add_argument('--selftest', action='store_true')
    return p


def main():
    args = build_parser().parse_args()
    if args.selftest:
        return selftest()
    err_lines = []
    if not args.file:
        err_lines.append('[ERROR] --file is required (use - for stdin)')
    if not args.layers:
        err_lines.append('[ERROR] --layers is required, ordered high to low')
    if err_lines:
        text = '\n'.join(err_lines) + '\n'
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    layers = [x.strip() for x in args.layers.split(',') if x.strip()]
    if len(set(layers)) != len(layers):
        text = '[ERROR] %s\n' % R_DUP_LAYER
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
    if not rows:
        text = '[ERROR] %s\n' % R_NO_ROWS
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    cfg = {'layers': layers, 'prev_col': args.prev_col,
           'cur_col': args.cur_col, 'total_users': args.total_users,
           'check_drift': args.check_drift,
           'threshold_version': args.threshold_version,
           'prev_window': args.prev_window, 'cur_window': args.cur_window}
    cfg.update(build_matrix(rows, layers, args.prev_col, args.cur_col))
    res = analyze(cfg)
    lines = []
    render(cfg, res, lines)
    text = '\n'.join(lines) + '\n'
    path = args.out or RESULT
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())