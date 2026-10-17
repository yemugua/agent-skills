# -*- coding: utf-8 -*-
"""\u5409\u4ed6\u8c03\u97f3\u6838\u67e5\uff1a\u6309 A4=440 \u8ba1\u7b97\u516d\u6839\u7a7a\u5f26\u6807\u51c6\u97f3\uff0c\u91cf\u5316\u97f3\u5206\u504f\u5dee\uff0c\u5e76\u6838\u4e94\u54c1\u8c03\u5f26\u6cd5\u6b65\u9aa4\u3002

\u7528\u6cd5:
  python guitar_tuning_check.py --file tuning.json [--out result.md] [--format json]
  python guitar_tuning_check.py --selftest
"""
import argparse
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u516d\u6839\u7a7a\u5f26: (\u952e, \u4e2d\u6587\u540d, \u97f3\u540d, MIDI \u97f3\u9ad8\u7f16\u53f7)
STRINGS = [
    ('s6', '6 \u5f26\uff08\u6700\u7c97\uff09', 'E2', 40),
    ('s5', '5 \u5f26', 'A2', 45),
    ('s4', '4 \u5f26', 'D3', 50),
    ('s3', '3 \u5f26', 'G3', 55),
    ('s2', '2 \u5f26', 'B3', 59),
    ('s1', '1 \u5f26\uff08\u6700\u7ec6\uff09', 'E4', 64),
]

# \u4e94\u54c1\u8c03\u5f26\u6cd5\u6b65\u9aa4: (\u8d77\u59cb\u5f26\u952e, \u54c1\u6570, \u76ee\u6807\u5f26\u952e, \u8bf4\u660e)
FIFTH_FRET_STEPS = [
    ('s6', 5, 's5', '6 \u5f26 5 \u54c1\u6309\u97f3\u4e0e 5 \u5f26\u7a7a\u5f26\u540c\u9ad8'),
    ('s5', 5, 's4', '5 \u5f26 5 \u54c1\u6309\u97f3\u4e0e 4 \u5f26\u7a7a\u5f26\u540c\u9ad8'),
    ('s4', 5, 's3', '4 \u5f26 5 \u54c1\u6309\u97f3\u4e0e 3 \u5f26\u7a7a\u5f26\u540c\u9ad8'),
    ('s3', 4, 's2', '3 \u5f26\u5230 2 \u5f26\u662f\u5927\u4e09\u5ea6\uff0c\u5fc5\u987b\u6309 4 \u54c1'),
    ('s2', 5, 's1', '2 \u5f26 5 \u54c1\u6309\u97f3\u4e0e 1 \u5f26\u7a7a\u5f26\u540c\u9ad8'),
]

# \u8c03\u97f3\u65b9\u6cd5: (\u952e, \u4e2d\u6587\u540d, \u7cbe\u5ea6, \u662f\u5426\u4e0d\u63a8\u8350)
METHODS = [
    ('tuner', '\u8c03\u97f3\u5668\u6216\u8c03\u97f3 App', '\u6700\u9ad8', False),
    ('fifth_fret', '\u4e94\u54c1\u8c03\u5f26\u6cd5', '\u4e2d', False),
    ('harmonic', '\u6cdb\u97f3\u6cd5', '\u9ad8', False),
    ('reference', '\u53c2\u7167\u4e50\u5668\uff08\u94a2\u7434\u3001\u5b9a\u97f3\u7b1b\uff09', '\u4e2d', False),
    ('ear', '\u7eaf\u9760\u8033\u6735\uff0c\u6ca1\u6709\u53c2\u7167\u97f3\u6e90', '\u4f4e', True),
]

# \u9608\u503c\uff08\u97f3\u5206\uff09
TOL = {
    'ok': 5.0,        # \u97f3\u51c6\u4e0a\u9650
    'minor': 10.0,    # \u9700\u5fae\u8c03\u4e0a\u9650
    'bad': 20.0,      # \u660e\u663e\u8dd1\u8c03\u4e0a\u9650\uff0c\u8d85\u8fc7\u5373\u4e25\u91cd\u8dd1\u8c03
    'a4': 440.0,      # \u53c2\u8003\u97f3\u9ad8
}


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def freq_of(midi, a4=TOL['a4']):
    """\u5341\u4e8c\u5e73\u5747\u5f8b\uff1af = A4 * 2 \u7684 ((midi - 69) / 12) \u6b21\u65b9\u3002"""
    return a4 * (2.0 ** ((midi - 69.0) / 12.0))


def cents(freq, ref):
    """\u97f3\u5206\u504f\u5dee = 1200 * log2(\u5b9e\u6d4b / \u6807\u51c6)\u3002"""
    if freq is None or ref is None or freq <= 0 or ref <= 0:
        return None
    return 1200.0 * math.log(freq / ref, 2)


def _f(obj, key):
    v = obj.get(key)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError('%s \u5fc5\u987b\u662f\u6570\u5b57\uff0c\u5b9e\u4e3a %s' % (key, v))
    if f <= 0:
        raise ValueError('%s \u5fc5\u987b\u4e3a\u6b63\u6570\uff0c\u5b9e\u4e3a %s' % (key, v))
    return f


def _row(table, val, label):
    if val is None or val == '':
        return None
    n = norm(val)
    for r in table:
        if norm(r[0]) == n:
            return r
    raise ValueError('\u672a\u77e5\u7684 %s: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00' % (label, val, '/'.join(r[0] for r in table)))


def string_check(item, a4):
    """\u5355\u6839\u5f26\u7684\u97f3\u51c6\u5224\u5b9a\u3002item \u53ef\u4e3a {'key': 's6', 'freq': 82.4}\u3002"""
    if not isinstance(item, dict):
        raise ValueError('strings \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
    key = norm(item.get('key') or item.get('string'))
    if not key:
        raise ValueError('\u7f3a\u5c11\u5f26\u7684\u6807\u8bc6 key')
    match = None
    for s in STRINGS:
        if norm(s[0]) == key or norm(s[2]) == key:
            match = s
            break
    if match is None:
        raise ValueError('\u672a\u77e5\u7684\u5f26: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00'
                         % (key, '/'.join(s[0] for s in STRINGS)))
    freq = _f(item, 'freq')
    ref = freq_of(match[3], a4)
    dev = cents(freq, ref)
    if dev is None:
        return {'key': match[0], 'name': match[1], 'note': match[2],
                'freq': None, 'ref': ref, 'cents': None,
                'status': '\u672a\u586b\u5199', 'sev': 0, 'advice': ''}
    a = abs(dev)
    if a <= TOL['ok'] + 1e-9:
        status, sev = '\u97f3\u51c6', 0
        advice = ''
    elif a <= TOL['minor']:
        status, sev = '\u9700\u5fae\u8c03', 2
        advice = '\u504f\u5dee %.1f \u97f3\u5206\uff0c\u5f80%s\u65b9\u5411\u5fae\u8c03\u4e00\u70b9\u70b9' % (a, '\u5347\u9ad8' if dev < 0 else '\u964d\u4f4e')
    elif a <= TOL['bad']:
        status, sev = '\u660e\u663e\u8dd1\u8c03', 3
        advice = '\u504f\u5dee %.1f \u97f3\u5206\uff0c\u5f80%s\u65b9\u5411\u91cd\u8c03\uff1b\u5f39\u548c\u5f26\u7acb\u523b\u80fd\u542c\u51fa\u6765' % (
            a, '\u5347\u9ad8' if dev < 0 else '\u964d\u4f4e')
    else:
        status, sev = '\u4e25\u91cd\u8dd1\u8c03', 3
        advice = '\u504f\u5dee %.1f \u97f3\u5206\uff0c\u53ef\u80fd\u662f\u8c03\u9519\u5f26\u6216\u8c03\u9519\u516b\u5ea6\uff0c\u6574\u5f26\u91cd\u8c03' % a
    return {'key': match[0], 'name': match[1], 'note': match[2],
            'freq': freq, 'ref': ref, 'cents': dev,
            'status': status, 'sev': sev, 'advice': advice}


def steps_check(steps):
    """\u4e94\u54c1\u8c03\u5f26\u6cd5\u6b65\u9aa4\u6838\u67e5\uff0c\u8fd4\u56de(\u95ee\u9898\u5217\u8868, \u672a\u586b\u5199\u63d0\u793a)\u3002"""
    issues = []
    if steps is None:
        return issues, ['\u4e94\u54c1\u8c03\u5f26\u6cd5\u6b65\u9aa4']
    if not isinstance(steps, list):
        raise ValueError('steps \u5fc5\u987b\u662f\u5217\u8868')
    for st in steps:
        if not isinstance(st, dict):
            raise ValueError('steps \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
        src = norm(st.get('from'))
        dst = norm(st.get('to'))
        fret = st.get('fret')
        if fret is None:
            raise ValueError('steps \u7f3a\u5c11 fret')
        try:
            fret = int(fret)
        except (TypeError, ValueError):
            raise ValueError('fret \u5fc5\u987b\u662f\u6574\u6570\uff0c\u5b9e\u4e3a %s' % fret)
        want = None
        for a, fr, b, desc in FIFTH_FRET_STEPS:
            if norm(a) == src and norm(b) == dst:
                want = (fr, desc)
                break
        if want is None:
            raise ValueError('\u672a\u77e5\u7684\u6b65\u9aa4: %s \u5230 %s\uff0c\u4e94\u54c1\u6cd5\u53ea\u542b\u76f8\u90bb\u7684\u4e94\u7ec4' % (src, dst))
        if fret != want[0]:
            issues.append({
                'sev': 3, 'item': '\u4e94\u54c1\u8c03\u5f26\u6cd5',
                'detail': '%s \u5f26\u7528\u4e86 %d \u54c1\u53bb\u5bf9 %s \u5f26\uff0c\u5e94\u4e3a %d \u54c1' % (src, fret, dst, want[0]),
                'why': want[1] + '\uff1b\u54c1\u6570\u9519\u4f1a\u628a\u6574\u628a\u7434\u7684\u548c\u5f26\u90fd\u8c03\u9519',
            })
    return issues, []


def calc(data):
    a4 = _f(data, 'reference_a4') or TOL['a4']
    strings = data.get('strings')
    if strings is None:
        raise ValueError('\u8f93\u5165\u7f3a\u5c11 strings \u5217\u8868')
    if not isinstance(strings, list) or not strings:
        raise ValueError('strings \u5fc5\u987b\u662f\u975e\u7a7a\u5217\u8868')
    rows = [string_check(s, a4) for s in strings]

    method = _row(METHODS, data.get('method'), 'method')
    issues = []
    miss_names = [r['name'] for r in rows if r['cents'] is None]
    # \u6ca1\u63d0\u4ea4\u7684\u5f26\u4e5f\u8981\u7b97\u4fe1\u606f\u7f3a\u5931\uff0c\u5426\u5219\u300c\u53ea\u586b\u4e00\u6839\u4e14\u662f\u51c6\u7684\u300d\u4f1a\u88ab\u8bef\u5224\u6210\u5168\u7434\u97f3\u51c6\u5408\u683c
    present = set(r['key'] for r in rows)
    for s in STRINGS:
        if s[0] not in present:
            miss_names.append(s[1])

    # \u5f26\u81ea\u8eab\u7684\u504f\u5dee
    for r in rows:
        if r['sev'] >= 3:
            issues.append({
                'sev': 3, 'item': r['name'],
                'detail': '%s \u5b9e\u6d4b %.2f \u8d6b\u5179\uff0c\u6807\u51c6 %.2f \u8d6b\u5179\uff0c\u504f\u5dee %+.1f \u97f3\u5206'
                          % (r['note'], r['freq'], r['ref'], r['cents']),
                'why': r['advice'],
            })
        elif r['sev'] == 2:
            issues.append({
                'sev': 2, 'item': r['name'],
                'detail': '%s \u5b9e\u6d4b %.2f \u8d6b\u5179\uff0c\u6807\u51c6 %.2f \u8d6b\u5179\uff0c\u504f\u5dee %+.1f \u97f3\u5206'
                          % (r['note'], r['freq'], r['ref'], r['cents']),
                'why': r['advice'],
            })

    # \u4e94\u54c1\u8c03\u5f26\u6cd5\u6b65\u9aa4\uff1a\u53ea\u6709\u58f0\u660e\u7528\u4e94\u54c1\u6cd5\u65f6\uff0c\u672a\u586b\u6b65\u9aa4\u624d\u7b97\u4fe1\u606f\u7f3a\u5931
    step_issues, step_miss = steps_check(data.get('steps'))
    issues.extend(step_issues)
    if method is not None and method[0] == 'fifth_fret':
        miss_names.extend(step_miss)

    # \u8c03\u97f3\u65b9\u6cd5
    if method is None:
        miss_names.append('\u8c03\u97f3\u65b9\u6cd5')
    elif method[3]:
        issues.append({
            'sev': 2, 'item': '\u8c03\u97f3\u65b9\u6cd5',
            'detail': '\u7528%s' % method[1],
            'why': '\u6ca1\u6709\u53c2\u7167\u97f3\u9ad8\u65f6\uff0c\u4eba\u5f88\u5bb9\u6613\u628a\u6574\u628a\u7434\u6574\u4f53\u8c03\u9ad8\u6216\u8c03\u4f4e\uff1b'
                   '\u516d\u6839\u5f26\u5f7c\u6b64\u662f\u51c6\u7684\uff0c\u4f46\u6574\u4f53\u4e0d\u5728\u6807\u51c6\u97f3\u9ad8\u4e0a',
        })

    # \u7528\u4e94\u54c1\u6cd5\u5374\u6ca1\u5148\u5b9a 6 \u5f26
    if method is not None and method[0] == 'fifth_fret':
        s6 = next((r for r in rows if r['key'] == 's6'), None)
        if s6 is not None and s6['cents'] is not None and abs(s6['cents']) > TOL['ok']:
            issues.append({
                'sev': 2, 'item': '\u4e94\u54c1\u6cd5\u524d\u63d0',
                'detail': '\u7528\u4e94\u54c1\u8c03\u5f26\u6cd5\u4f46 6 \u5f26\u672c\u8eab\u504f\u5dee %+.1f \u97f3\u5206' % s6['cents'],
                'why': '\u4e94\u54c1\u6cd5\u53ea\u80fd\u4fdd\u8bc1\u516d\u6839\u5f26\u5f7c\u6b64\u7684\u76f8\u5bf9\u5173\u7cfb\u6b63\u786e\uff1b'
                       '6 \u5f26\u4e0d\u51c6\uff0c\u5168\u7434\u90fd\u4e0d\u5728\u6807\u51c6\u97f3\u9ad8\u4e0a',
            })

    # \u53d8\u8c03\u5939
    if data.get('capo'):
        if data.get('retune_for_capo'):
            issues.append({
                'sev': 2, 'item': '\u53d8\u8c03\u5939',
                'detail': '\u56e0\u4e3a\u7528\u4e86\u53d8\u8c03\u5939\u800c\u6539\u53d8\u4e86\u8c03\u97f3\u76ee\u6807',
                'why': '\u53d8\u8c03\u5939\u53ea\u6539\u53d8\u7a7a\u5f26\u7684\u5b9e\u9645\u97f3\u9ad8\uff0c\u8c03\u97f3\u4ecd\u5e94\u6309\u6807\u51c6 EADGBE \u8c03\uff0c'
                       '\u4e0d\u8981\u56e0\u4e3a\u5939\u4e86\u53d8\u8c03\u5939\u5c31\u53bb\u6539\u5f26',
            })

    issues.sort(key=lambda r: -r['sev'])

    n_bad = len([r for r in rows if r['sev'] >= 3])
    if n_bad or any(i['sev'] == 3 for i in issues):
        level = '\u97f3\u51c6\u6709\u660e\u663e\u95ee\u9898'
    elif issues:
        level = '\u6709\u53ef\u6539\u8fdb\u9879'
    elif miss_names:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u97f3\u51c6\u5408\u683c'

    worst = sorted([r for r in rows if r['cents'] is not None],
                   key=lambda r: -abs(r['cents']))
    return {
        'level': level, 'rows': rows, 'issues': issues, 'misses': miss_names,
        'a4': a4, 'method': method[1] if method else None,
        'n_bad': n_bad,
        'n_minor': len([r for r in rows if r['sev'] == 2]),
        'n_ok': len([r for r in rows if r['sev'] == 0 and r['cents'] is not None]),
        'worst': [r['name'] for r in worst[:3]],
        'fix_order': [i['item'] for i in issues],
        'steps': [{'from': a, 'fret': f, 'to': b, 'desc': d}
                  for a, f, b, d in FIFTH_FRET_STEPS],
        'methods': [{'key': k, 'name': n, 'precision': p, 'bad': b}
                    for k, n, p, b in METHODS],
        'tol': dict(TOL),
    }


def render_md(r):
    L = []
    L.append('# \u5409\u4ed6\u8c03\u97f3\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['level'])
    L.append('')
    L.append('- \u53c2\u8003\u97f3\u9ad8\uff1aA4 = %.1f \u8d6b\u5179' % r['a4'])
    if r['method']:
        L.append('- \u8c03\u97f3\u65b9\u6cd5\uff1a%s' % r['method'])
    L.append('- \u97f3\u51c6 %d \u6839\uff0c\u9700\u5fae\u8c03 %d \u6839\uff0c\u660e\u663e\u6216\u4e25\u91cd\u8dd1\u8c03 %d \u6839'
             % (r['n_ok'], r['n_minor'], r['n_bad']))
    if r['worst']:
        L.append('- \u504f\u5dee\u6700\u5927\u7684\u5148\u8c03\uff1a%s' % '\u3001'.join(r['worst']))
    L.append('')
    L.append('## \u4e8c\u3001\u516d\u6839\u5f26\u9010\u6839\u5224\u5b9a')
    L.append('')
    L.append('| \u5f26 | \u97f3\u540d | \u6807\u51c6\u9891\u7387 | \u5b9e\u6d4b\u9891\u7387 | \u504f\u5dee | \u5224\u5b9a |')
    L.append('|---|---|---|---|---|---|')
    for row in r['rows']:
        L.append('| %s | %s | %.2f \u8d6b\u5179 | %s | %s | %s |'
                 % (row['name'], row['note'], row['ref'],
                    '%.2f \u8d6b\u5179' % row['freq'] if row['freq'] else '\u672a\u586b\u5199',
                    '%+.1f \u97f3\u5206' % row['cents'] if row['cents'] is not None else '\u672a\u586b\u5199',
                    row['status']))
    L.append('')
    if r['issues']:
        L.append('## \u4e09\u3001\u95ee\u9898\u4e0e\u6574\u6539')
        L.append('')
        L.append('| \u4e25\u91cd\u5ea6 | \u9879\u76ee | \u95ee\u9898 | \u4e3a\u4ec0\u4e48\u8981\u5728\u610f |')
        L.append('|---|---|---|---|')
        for i in r['issues']:
            L.append('| %s | %s | %s | %s |'
                     % ('\u4e25\u91cd' if i['sev'] == 3 else '\u53ef\u6539\u8fdb', i['item'], i['detail'], i['why']))
        L.append('')
    if r['misses']:
        L.append('- \u672a\u586b\u5199\uff1a%s' % '\u3001'.join(r['misses']))
        L.append('')
    L.append('## \u56db\u3001\u4e94\u54c1\u8c03\u5f26\u6cd5')
    L.append('')
    L.append('| \u6b65\u9aa4 | \u64cd\u4f5c | \u8bf4\u660e |')
    L.append('|---|---|---|')
    for s in r['steps']:
        L.append('| %s \u5f26 %d \u54c1 | \u5bf9 %s \u5f26\u7a7a\u5f26 | %s |' % (s['from'], s['fret'], s['to'], s['desc']))
    L.append('')
    L.append('## \u4e94\u3001\u8c03\u97f3\u65b9\u6cd5')
    L.append('')
    L.append('| \u65b9\u6cd5 | \u7cbe\u5ea6 | \u662f\u5426\u63a8\u8350 |')
    L.append('|---|---|---|')
    for m in r['methods']:
        L.append('| %s | %s | %s |' % (m['name'], m['precision'], '\u4e0d\u63a8\u8350' if m['bad'] else '\u63a8\u8350'))
    L.append('')
    L.append('## \u516d\u3001\u9608\u503c\uff08\u97f3\u5206\uff09')
    L.append('')
    L.append('| \u9879\u76ee | \u9608\u503c |')
    L.append('|---|---|')
    L.append('| \u97f3\u51c6 | \u504f\u5dee\u4e0d\u8d85\u8fc7 %.0f \u97f3\u5206 |' % r['tol']['ok'])
    L.append('| \u9700\u5fae\u8c03 | %.0f \u5230 %.0f \u97f3\u5206 |' % (r['tol']['ok'], r['tol']['minor']))
    L.append('| \u660e\u663e\u8dd1\u8c03 | %.0f \u5230 %.0f \u97f3\u5206 |' % (r['tol']['minor'], r['tol']['bad']))
    L.append('| \u4e25\u91cd\u8dd1\u8c03 | \u8d85\u8fc7 %.0f \u97f3\u5206 |' % r['tol']['bad'])
    L.append('')
    L.append('## \u4e03\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] 6 \u5f26\u5df2\u7528\u8c03\u97f3\u5668\u6216\u53c2\u7167\u97f3\u6e90\u8c03\u5230\u6807\u51c6 E')
    L.append('- [ ] \u4e94\u54c1\u6cd5\u7b2c 4 \u6b65\u7528\u7684\u662f 4 \u54c1\uff0c\u4e0d\u662f 5 \u54c1')
    L.append('- [ ] \u6bcf\u6839\u5f26\u662f\u4ece\u4f4e\u5f80\u9ad8\u8c03\u4e0a\u53bb\u7684\uff0c\u4e0d\u662f\u4ece\u9ad8\u5f80\u4f4e\u8c03')
    L.append('- [ ] \u516d\u6839\u8c03\u5b8c\u540e\u518d\u590d\u6838\u4e00\u904d')
    L.append('- [ ] \u5f39 C\u3001G\u3001Em \u5404\u4e00\u904d\uff0c\u8033\u6735\u542c\u7740\u8212\u670d')
    L.append('- [ ] \u6362\u5f26\u6216\u6362\u73af\u5883\u540e\u91cd\u65b0\u8c03\u8fc7')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u6807\u51c6\u9891\u7387\u8ba1\u7b97
    ck(abs(freq_of(40) - 82.41) < 0.01, 'E2 \u5e94\u4e3a 82.41\uff0c\u5b9e\u4e3a %.4f' % freq_of(40))
    ck(abs(freq_of(45) - 110.0) < 0.01, 'A2 \u5e94\u4e3a 110.00\uff0c\u5b9e\u4e3a %.4f' % freq_of(45))
    ck(abs(freq_of(50) - 146.83) < 0.01, 'D3 \u5e94\u4e3a 146.83\uff0c\u5b9e\u4e3a %.4f' % freq_of(50))
    ck(abs(freq_of(55) - 196.0) < 0.01, 'G3 \u5e94\u4e3a 196.00\uff0c\u5b9e\u4e3a %.4f' % freq_of(55))
    ck(abs(freq_of(59) - 246.94) < 0.01, 'B3 \u5e94\u4e3a 246.94\uff0c\u5b9e\u4e3a %.4f' % freq_of(59))
    ck(abs(freq_of(64) - 329.63) < 0.01, 'E4 \u5e94\u4e3a 329.63\uff0c\u5b9e\u4e3a %.4f' % freq_of(64))
    ck(abs(freq_of(69) - 440.0) < 1e-9, 'A4 \u5e94\u4e3a 440.00\uff0c\u5b9e\u4e3a %.4f' % freq_of(69))

    # 2 \u97f3\u5206\u8ba1\u7b97
    ck(abs(cents(440 * 2, 440) - 1200) < 1e-9, '\u9ad8\u516b\u5ea6\u5e94\u4e3a +1200 \u97f3\u5206')
    ck(abs(cents(440 / 2, 440) + 1200) < 1e-9, '\u4f4e\u516b\u5ea6\u5e94\u4e3a -1200 \u97f3\u5206')
    ck(abs(cents(440, 440)) < 1e-9, '\u540c\u9891\u5e94\u4e3a 0 \u97f3\u5206')

    # 3 \u5168\u90e8\u6807\u51c6\u7684\u6b63\u4f8b
    std = [{'key': k, 'freq': freq_of(m)} for k, _, _, m in STRINGS]
    r3 = calc({'strings': std, 'method': 'tuner'})
    ck(r3['level'] == '\u97f3\u51c6\u5408\u683c', '\u5168\u90e8\u6807\u51c6\u5e94\u5224\u97f3\u51c6\u5408\u683c\uff0c\u5b9e\u4e3a %s' % r3['level'])
    ck(r3['issues'] == [], '\u5168\u90e8\u6807\u51c6\u4e0d\u5e94\u6709\u95ee\u9898\u9879\uff0c\u5b9e\u4e3a %s' % r3['issues'])
    ck(r3['n_ok'] == 6, '\u97f3\u51c6\u5e94\u4e3a 6 \u6839\uff0c\u5b9e\u4e3a %d' % r3['n_ok'])

    # 4 \u53cd\u4f8b\uff1a6 \u5f26\u8c03\u5230 80 \u8d6b\u5179
    bad6 = [dict(std[0], freq=80.0)] + std[1:]
    r4 = calc({'strings': bad6, 'method': 'tuner'})
    ck(r4['level'] == '\u97f3\u51c6\u6709\u660e\u663e\u95ee\u9898', '6 \u5f26 80 \u8d6b\u5179\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r4['level'])
    ck(any(i['item'] == '6 \u5f26\uff08\u6700\u7c97\uff09' for i in r4['issues']), '\u5e94\u70b9\u540d 6 \u5f26')
    ck(abs(r4['rows'][0]['cents']) > 20, '\u504f\u5dee\u5e94\u8d85\u8fc7 20 \u97f3\u5206\uff0c\u5b9e\u4e3a %s' % r4['rows'][0]['cents'])

    # 5 \u97f3\u5206\u5206\u7ea7\u8fb9\u754c\uff1a\u53ea\u8ba9 5 \u5f26\u504f dev \u97f3\u5206\uff0c\u5176\u4f59\u4e94\u6839\u4fdd\u6301\u6807\u51c6
    def mk(dev):
        out = [{'key': k, 'freq': freq_of(m)} for k, _, _, m in STRINGS]
        out[1]['freq'] = freq_of(45) * (2 ** (dev / 1200.0))
        return out

    ck(calc({'strings': mk(5), 'method': 'tuner'})['level'] == '\u97f3\u51c6\u5408\u683c',
       '5 \u97f3\u5206\u8fb9\u754c\u5e94\u5408\u683c')
    ck(calc({'strings': mk(-5), 'method': 'tuner'})['level'] == '\u97f3\u51c6\u5408\u683c',
       '\u8d1f 5 \u97f3\u5206\u8fb9\u754c\u5e94\u5408\u683c')
    ck(calc({'strings': mk(8), 'method': 'tuner'})['level'] == '\u6709\u53ef\u6539\u8fdb\u9879',
       '8 \u97f3\u5206\u5e94\u5224\u9700\u5fae\u8c03')
    ck(calc({'strings': mk(15), 'method': 'tuner'})['level'] == '\u97f3\u51c6\u6709\u660e\u663e\u95ee\u9898',
       '15 \u97f3\u5206\u5e94\u5224\u660e\u663e\u8dd1\u8c03')
    ck(calc({'strings': mk(40), 'method': 'tuner'})['level'] == '\u97f3\u51c6\u6709\u660e\u663e\u95ee\u9898',
       '40 \u97f3\u5206\u5e94\u5224\u4e25\u91cd\u8dd1\u8c03')

    # 6 \u53cd\u4f8b\uff1a\u4e94\u54c1\u6cd5\u7b2c 4 \u6b65\u7528\u9519\u54c1\u6570
    wrong = [{'from': 's3', 'fret': 5, 'to': 's2'}]
    r6 = calc({'strings': std, 'method': 'fifth_fret', 'steps': wrong})
    ck(any(i['item'] == '\u4e94\u54c1\u8c03\u5f26\u6cd5' for i in r6['issues']), '3 \u5f26\u7528 5 \u54c1\u5e94\u5224\u4e25\u91cd')
    ck(r6['level'] == '\u97f3\u51c6\u6709\u660e\u663e\u95ee\u9898', '\u54c1\u6570\u9519\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r6['level'])
    ck('\u5e94\u4e3a 4 \u54c1' in r6['issues'][0]['detail'], '\u5e94\u7ed9\u51fa\u6b63\u786e\u54c1\u6570\uff0c\u5b9e\u4e3a %s' % r6['issues'][0]['detail'])

    # 7 \u6b63\u786e\u7684\u4e94\u54c1\u6cd5\u6b65\u9aa4
    right = [{'from': a, 'fret': f, 'to': b} for a, f, b, _ in FIFTH_FRET_STEPS]
    r7 = calc({'strings': std, 'method': 'fifth_fret', 'steps': right})
    ck(not any(i['item'] == '\u4e94\u54c1\u8c03\u5f26\u6cd5' for i in r7['issues']), '\u6b63\u786e\u6b65\u9aa4\u4e0d\u5e94\u62a5\u9519')
    ck(r7['level'] == '\u97f3\u51c6\u5408\u683c', '\u6b63\u786e\u6b65\u9aa4\u5e94\u5408\u683c\uff0c\u5b9e\u4e3a %s' % r7['level'])

    # 8 \u53cd\u4f8b\uff1a\u5176\u4ed6\u6b65\u9aa4\u4e5f\u7528\u9519\u54c1\u6570
    for a, f, b, _ in FIFTH_FRET_STEPS:
        if f == 5:
            r8 = calc({'strings': std, 'method': 'fifth_fret',
                       'steps': [{'from': a, 'fret': 4, 'to': b}]})
            ck(any(i['item'] == '\u4e94\u54c1\u8c03\u5f26\u6cd5' for i in r8['issues']),
               '%s \u5f26\u7528 4 \u54c1\u53bb\u5bf9 %s \u5f26\u5e94\u5224\u4e25\u91cd' % (a, b))

    # 9 \u53cd\u4f8b\uff1a\u7eaf\u9760\u8033\u6735\u8c03
    r9 = calc({'strings': std, 'method': 'ear'})
    ck(any(i['item'] == '\u8c03\u97f3\u65b9\u6cd5' for i in r9['issues']), '\u7eaf\u9760\u8033\u6735\u5e94\u63d0\u793a')
    ck(r9['level'] == '\u6709\u53ef\u6539\u8fdb\u9879', '\u7eaf\u9760\u8033\u6735\u5e94\u5224\u53ef\u6539\u8fdb\uff0c\u5b9e\u4e3a %s' % r9['level'])

    # 10 \u53cd\u4f8b\uff1a\u7528\u4e94\u54c1\u6cd5\u4f46 6 \u5f26\u4e0d\u51c6
    r10 = calc({'strings': [dict(std[0], freq=freq_of(40) * (2 ** (12 / 1200.0)))] + std[1:],
                'method': 'fifth_fret', 'steps': right})
    ck(any(i['item'] == '\u4e94\u54c1\u6cd5\u524d\u63d0' for i in r10['issues']), '6 \u5f26\u4e0d\u51c6\u7528\u4e94\u54c1\u6cd5\u5e94\u63d0\u793a')

    # 11 \u53cd\u4f8b\uff1a\u56e0\u53d8\u8c03\u5939\u6539\u8c03\u97f3\u76ee\u6807
    r11 = calc({'strings': std, 'method': 'tuner', 'capo': 2, 'retune_for_capo': True})
    ck(any(i['item'] == '\u53d8\u8c03\u5939' for i in r11['issues']), '\u56e0\u53d8\u8c03\u5939\u6539\u8c03\u97f3\u5e94\u63d0\u793a')
    ck(calc({'strings': std, 'method': 'tuner', 'capo': 2})['level'] == '\u97f3\u51c6\u5408\u683c',
       '\u5939\u53d8\u8c03\u5939\u4f46\u4e0d\u6539\u8c03\u97f3\u76ee\u6807\u5e94\u5408\u683c')

    # 12 \u53c2\u8003\u97f3\u9ad8\u53d8\u5316
    r12 = calc({'strings': [{'key': 's5', 'freq': 110.0}], 'method': 'tuner',
                'reference_a4': 442})
    ck(r12['a4'] == 442, '\u53c2\u8003\u97f3\u9ad8\u5e94\u4e3a 442')
    ck(r12['rows'][0]['cents'] < -5, '\u4ee5 442 \u4e3a\u57fa\u51c6\u65f6 110 \u8d6b\u5179\u5e94\u504f\u4f4e')

    # 13 \u6392\u5e8f\u65b9\u5411\uff1a\u504f\u5dee\u6700\u5927\u7684\u6392\u6700\u524d
    r13 = calc({'strings': [dict(std[0], freq=freq_of(40) * (2 ** (-50 / 1200.0))),
                            dict(std[1], freq=freq_of(45) * (2 ** (30 / 1200.0))),
                            dict(std[2], freq=freq_of(50) * (2 ** (8 / 1200.0)))],
                'method': 'tuner'})
    ck(r13['worst'][0] == '6 \u5f26\uff08\u6700\u7c97\uff09', '\u504f\u5dee\u6700\u5927\u7684\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r13['worst'])
    ck(r13['worst'][1] == '5 \u5f26', '\u7b2c\u4e8c\u5e94\u662f 5 \u5f26\uff0c\u5b9e\u4e3a %s' % r13['worst'])
    ck(r13['issues'][0]['sev'] == 3, '\u4e25\u91cd\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r13['issues'][0]['sev'])

    # 14 \u5224\u5b9a\u987a\u5e8f\uff1a\u6709\u4e25\u91cd\u9879\u65f6\u4e0d\u56e0\u7f3a\u4fe1\u606f\u5224\u5f85\u786e\u8ba4
    r14 = calc({'strings': [dict(std[0], freq=80.0)]})
    ck(r14['level'] == '\u97f3\u51c6\u6709\u660e\u663e\u95ee\u9898', '\u53ea\u586b\u4e00\u6839\u4e14\u8dd1\u8c03\u4e0d\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r14['level'])
    r14b = calc({'strings': [{'key': 's6', 'freq': freq_of(40)}], 'method': 'tuner'})
    ck(r14b['level'] == '\u5f85\u786e\u8ba4', '\u53ea\u586b 6 \u5f26\u4e14\u51c6\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r14b['level'])

    # 15 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'strings': [dict(std[0], freq=80.0)], 'method': 'tuner'})
    r15 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r15['level'] == '\u97f3\u51c6\u6709\u660e\u663e\u95ee\u9898', 'BOM \u5b57\u7b26\u4e32\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r15['level'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_c8.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'strings': std, 'method': 'fifth_fret',
                            'steps': [{'from': 's3', 'fret': 5, 'to': 's2'}]}))
    try:
        r15b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(any(i['item'] == '\u4e94\u54c1\u8c03\u5f26\u6cd5' for i in r15b['issues']),
           'BOM \u6587\u4ef6\u5e94\u89e3\u6790\u51fa steps\uff0c\u5b9e\u4e3a %s' % r15b['issues'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 16 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({}, '\u7f3a strings'),
        ({'strings': []}, 'strings \u7a7a\u5217\u8868'),
        ({'strings': [{'key': 's7', 'freq': 100}]}, '\u672a\u77e5\u5f26'),
        ({'strings': [{'freq': 100}]}, '\u7f3a\u5f26\u6807\u8bc6'),
        ({'strings': [{'key': 's6', 'freq': 'abc'}]}, '\u9891\u7387\u975e\u6570\u5b57'),
        ({'strings': [{'key': 's6', 'freq': 0}]}, '\u9891\u7387\u4e3a 0'),
        ({'strings': std, 'method': '\u62cd\u97f3\u6cd5'}, '\u672a\u77e5\u65b9\u6cd5'),
        ({'strings': std, 'steps': [{'from': 's6', 'fret': 5, 'to': 's3'}]}, '\u975e\u76f8\u90bb\u6b65\u9aa4'),
        ({'strings': std, 'steps': [{'from': 's6', 'to': 's5'}]}, '\u7f3a fret'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b16 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 17 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r4)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u516d\u6839\u5f26\u9010\u6839\u5224\u5b9a', '\u4e94\u54c1\u8c03\u5f26\u6cd5', '\u8c03\u97f3\u65b9\u6cd5', '\u9608\u503c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(STRINGS) == 6, '\u5f26\u5e94 6 \u6839')
    ck(len(FIFTH_FRET_STEPS) == 5, '\u4e94\u54c1\u6cd5\u6b65\u9aa4\u5e94 5 \u6b65')
    ck(FIFTH_FRET_STEPS[3][1] == 4, '\u7b2c 4 \u6b65\u5fc5\u987b\u662f 4 \u54c1')
    ck(all(f == 5 for i, (_, f, _, _) in enumerate(FIFTH_FRET_STEPS) if i != 3),
       '\u9664\u7b2c 4 \u6b65\u5916\u90fd\u5e94\u662f 5 \u54c1')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u516d\u6839\u5f26\u6807\u51c6\u9891\u7387/\u97f3\u5206\u8ba1\u7b97\u4e0e\u516b\u5ea6/\u5168\u6807\u51c6\u6b63\u4f8b/6\u5f2680\u8d6b\u5179\u53cd\u4f8b/'
        '\u97f3\u5206\u5206\u7ea7\u8fb9\u754c(5\u4e0e8\u4e0e15\u4e0e40)/\u4e94\u54c1\u6cd53\u5f26\u75285\u54c1\u53cd\u4f8b/\u6b63\u786e\u6b65\u9aa4/\u5176\u4f59\u6b65\u9aa4\u54c1\u6570\u53cd\u4f8b/'
        '\u7eaf\u9760\u8033\u6735\u53cd\u4f8b/\u4e94\u54c1\u6cd5\u524d\u63d0\u53cd\u4f8b/\u53d8\u8c03\u5939\u53cd\u4f8b/\u53c2\u8003\u97f3\u9ad8442/\u504f\u5dee\u6392\u5e8f/\u5224\u5b9a\u987a\u5e8f/'
        'BOM\u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u5409\u4ed6\u8c03\u97f3\u6838\u67e5')
    ap.add_argument('--file', help='\u8f93\u5165 JSON \u6587\u4ef6')
    ap.add_argument('--text', help='\u8f93\u5165 JSON \u5b57\u7b26\u4e32')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    raw = a.text or ''
    if a.file:
        if not os.path.exists(a.file):
            print('ERROR --file \u4e0d\u5b58\u5728: %s' % a.file)
            return 2
        raw = open(a.file, 'r', encoding='utf-8-sig', errors='replace').read()
    if not raw.strip():
        print('ERROR \u9700\u8981 --file \u6216 --text')
        return 2
    try:
        data = json.loads(raw.lstrip('\ufeff'))
    except ValueError as e:
        print('ERROR JSON \u89e3\u6790\u5931\u8d25: %s' % e)
        return 2
    try:
        r = calc(data)
    except ValueError as e:
        print('ERROR %s' % e)
        return 2

    out = render_md(r) if a.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    d = os.path.dirname(os.path.abspath(__file__))
    target = a.out or os.path.join(d, '_last_result.txt')
    with open(target, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % target)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
