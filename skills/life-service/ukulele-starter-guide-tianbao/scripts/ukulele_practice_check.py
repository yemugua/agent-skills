# -*- coding: utf-8 -*-
"""\u5c24\u514b\u91cc\u91cc\u5165\u95e8\u7ec3\u4e60\u8def\u5f84\u6838\u67e5\uff1agCEA \u56db\u5f26\u6807\u51c6\u97f3\u5224\u5b9a\u3001\u4e5d\u4e2a\u5165\u95e8\u548c\u5f26\u6307\u6cd5\u9010\u5f26\u6838\u5bf9\u3001\u7ec3\u4e60\u8def\u5f84\u56db\u9636\u6bb5\u987a\u5e8f\u6838\u67e5\u3002

\u7528\u6cd5:
  python ukulele_practice_check.py --file plan.json [--out result.md] [--format json]
  python ukulele_practice_check.py --selftest
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

# \u56db\u5f26\u987a\u5e8f\u56fa\u5b9a\u4e3a \u56db\u5f26(g) / \u4e09\u5f26(C) / \u4e8c\u5f26(E) / \u4e00\u5f26(A)
STRING_KEYS = ['g', 'C', 'E', 'A']
STRING_NAMES = {'g': '\u56db\u5f26(g)', 'C': '\u4e09\u5f26(C)', 'E': '\u4e8c\u5f26(E)', 'A': '\u4e00\u5f26(A)'}
STRING_MIDI = {'g': 67, 'C': 60, 'E': 64, 'A': 69}

# \u4e5d\u4e2a\u5165\u95e8\u548c\u5f26\uff0c\u6307\u6cd5\u987a\u5e8f\u540c STRING_KEYS\uff1a[\u56db\u5f26, \u4e09\u5f26, \u4e8c\u5f26, \u4e00\u5f26]\uff0c0=\u7a7a\u5f26\uff0c\u6574\u6570=\u54c1\u683c
CHORDS = {
    'C': [0, 0, 0, 3],
    'C7': [0, 0, 0, 1],
    'Am': [2, 0, 0, 0],
    'A': [2, 1, 0, 0],
    'F': [2, 0, 1, 0],
    'G': [0, 2, 3, 2],
    'G7': [0, 2, 1, 0],
    'D': [2, 2, 2, 0],
    'Dm': [2, 2, 1, 0],
    'Em': [0, 4, 3, 2],
}


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')




CHORDS_N = {norm(k): v for k, v in CHORDS.items()}

# \u7ec3\u4e60\u8def\u5f84\u56db\u9636\u6bb5\uff08\u987a\u5e8f\u4e0d\u53ef\u8df3\uff09
PLAN_STAGES = ['tuning', 'single_chord', 'transition', 'first_song']
PLAN_LABELS = {
    'tuning': '\u9636\u6bb51 \u8c03\u97f3\u6301\u7434\u5355\u97f3',
    'single_chord': '\u9636\u6bb52 \u5355\u548c\u5f26',
    'transition': '\u9636\u6bb53 \u548c\u5f26\u8f6c\u6362',
    'first_song': '\u9636\u6bb54 \u7b2c\u4e00\u9996\u5f39\u5531',
}

TOL = {'ok': 5.0, 'minor': 10.0, 'bad': 20.0}


def freq_of(midi):
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))


def cents(freq, ref):
    if freq is None or ref is None or freq <= 0 or ref <= 0:
        return None
    return 1200.0 * math.log(freq / ref, 2)


def _f(v, key):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError('%s \u5fc5\u987b\u662f\u6570\u5b57\uff0c\u5b9e\u4e3a %s' % (key, v))
    if f <= 0:
        raise ValueError('%s \u5fc5\u987b\u4e3a\u6b63\u6570\uff0c\u5b9e\u4e3a %s' % (key, v))
    return f


def tuning_check(tuning):
    """\u8fd4\u56de\u56db\u5f26\u9010\u5f26\u5224\u5b9a\u5217\u8868\u3002tuning \u4e3a {g:\u9891\u7387, C:\u9891\u7387, ...}\uff0c\u53ef\u90e8\u5206\u63d0\u4f9b\u3002"""
    rows = []
    for key in STRING_KEYS:
        v = tuning.get(key) if isinstance(tuning, dict) else None
        ref = freq_of(STRING_MIDI[key])
        if v is None:
            rows.append({'key': key, 'name': STRING_NAMES[key], 'freq': None,
                         'ref': ref, 'cents': None, 'status': '\u672a\u586b\u5199', 'sev': 0})
            continue
        f = _f(v, key)
        dev = cents(f, ref)
        a = abs(dev)
        if a <= TOL['ok'] + 1e-9:
            status, sev = '\u97f3\u51c6', 0
        elif a <= TOL['minor']:
            status, sev = '\u9700\u5fae\u8c03', 2
        elif a <= TOL['bad']:
            status, sev = '\u660e\u663e\u8dd1\u8c03', 2
        else:
            status, sev = '\u4e25\u91cd\u8dd1\u8c03', 3
        rows.append({'key': key, 'name': STRING_NAMES[key], 'freq': f,
                     'ref': ref, 'cents': dev, 'status': status, 'sev': sev})
    return rows


def chord_check(item):
    """\u5355\u548c\u5f26\u6307\u6cd5\u6838\u5bf9\u3002item: {'name': 'C', 'frets': [0,0,0,3]}\u3002"""
    if not isinstance(item, dict):
        raise ValueError('chords \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
    orig = item.get('name')
    name = norm(orig)
    if name not in CHORDS_N:
        raise ValueError('\u672a\u77e5\u548c\u5f26: %s\uff0c\u53ef\u9009 %s' % (orig, '/'.join(CHORDS.keys())))
    frets = item.get('frets')
    if not isinstance(frets, list) or len(frets) != 4:
        raise ValueError('\u548c\u5f26 %s \u7684 frets \u5fc5\u987b\u662f 4 \u4e2a\u5143\u7d20\u7684\u5217\u8868' % orig)
    want = CHORDS_N[name]
    wrong = []
    for i, key in enumerate(STRING_KEYS):
        got = frets[i]
        if got != want[i]:
            wrong.append('\u5f26%s \u5e94\u4e3a %s \u54c1\uff0c\u5b9e\u4e3a %s' % (STRING_NAMES[key], want[i], got))
    if wrong:
        return {'name': orig, 'ok': False, 'wrong': wrong, 'sev': 2}
    return {'name': orig, 'ok': True, 'wrong': [], 'sev': 0}


def plan_check(plan):
    """\u7ec3\u4e60\u8def\u5f84\u987a\u5e8f\u6838\u67e5\u3002plan \u4e3a\u9636\u6bb5 key \u5217\u8868\uff08\u6309\u987a\u5e8f\uff09\u3002"""
    issues = []
    if plan is None:
        return issues, ['\u7ec3\u4e60\u8def\u5f84']
    if not isinstance(plan, list):
        raise ValueError('plan \u5fc5\u987b\u662f\u5217\u8868')
    seq = [norm(p) for p in plan]
    # \u7f3a\u9636\u6bb5
    missing = [s for s in PLAN_STAGES if s not in seq]
    for s in missing:
        issues.append({'sev': 2, 'item': '\u7ec3\u4e60\u8def\u5f84',
                       'detail': '\u7f3a\u5c11%s' % PLAN_LABELS[s],
                       'why': '\u8df3\u8fc7\u57fa\u7840\u9636\u6bb5\u4f1a\u8ba9\u540e\u9762\u7684\u7ec3\u4e60\u4e8b\u500d\u529f\u534a\uff0c\u751a\u81f3\u4e00\u76f4\u5361\u5728\u8f6c\u6362\u4e0a'})
    # \u987a\u5e8f\u9519\uff1a\u5728 seq \u4e2d\u56db\u4e2a\u9636\u6bb5\u51fa\u73b0\u7684\u4f4d\u7f6e\u662f\u5426\u5355\u8c03\u9012\u589e
    # \u987a\u5e8f\u9519\uff1a\u4efb\u610f\u4e24\u4e2a\u5df2\u51fa\u73b0\u9636\u6bb5\uff0c\u82e5\u8ba1\u5212\u5728\u524d\u7684\u5374\u6392\u5728\u5e8f\u5217\u7684\u540e\u9762\uff0c\u5373\u98a0\u5012
    rev = None
    for a in PLAN_STAGES:
        for b in PLAN_STAGES:
            if PLAN_STAGES.index(a) < PLAN_STAGES.index(b) and \
               a in seq and b in seq and seq.index(a) > seq.index(b):
                rev = (a, b)
                break
        if rev:
            break
    if rev:
        a, b = rev
        issues.append({'sev': 2, 'item': '\u7ec3\u4e60\u8def\u5f84',
                       'detail': '\u9636\u6bb5\u987a\u5e8f\u98a0\u5012\uff1a%s \u88ab\u6392\u5728 %s \u4e4b\u540e\uff0c\u5e94\u5148\u4e8e\u5b83'
                                 % (PLAN_LABELS[b], PLAN_LABELS[a]),
                       'why': '\u9636\u6bb5\u987a\u5e8f\u5e94\u4e3a \u8c03\u97f3\u2192\u5355\u548c\u5f26\u2192\u8f6c\u6362\u2192\u5f39\u5531\uff0c\u98a0\u5012\u4f1a\u57fa\u7840\u4e0d\u7262'})
    return issues, []


def calc(data):
    tuning = data.get('tuning') or {}
    rows = tuning_check(tuning) if isinstance(tuning, dict) else tuning_check({})

    issues = []
    n_chord_wrong = 0
    chords = data.get('chords') or []
    if chords is not None:
        if not isinstance(chords, list):
            raise ValueError('chords \u5fc5\u987b\u662f\u5217\u8868')
        for c in chords:
            rc = chord_check(c)
            if not rc['ok']:
                n_chord_wrong += 1
                issues.append({'sev': rc['sev'], 'item': '%s \u548c\u5f26' % rc['name'],
                               'detail': '\uff1b'.join(rc['wrong']),
                               'why': '\u6309\u54c1\u9519\u4e86\u548c\u5f26\u53d1\u58f0\u5c31\u4e0d\u5bf9\uff0c\u5148\u7167\u6307\u6cd5\u8868\u9010\u5f26\u6838\u5bf9'})

    plan_issues, plan_miss = plan_check(data.get('plan'))
    issues.extend(plan_issues)

    # \u8c03\u97f3\u504f\u5dee\u9879
    for r in rows:
        if r['sev'] >= 3:
            issues.append({'sev': 3, 'item': r['name'],
                           'detail': '\u5b9e\u6d4b %.2f \u8d6b\u5179\uff0c\u6807\u51c6 %.2f \u8d6b\u5179\uff0c\u504f\u5dee %+.1f \u97f3\u5206'
                                     % (r['freq'], r['ref'], r['cents']),
                           'why': '\u504f\u5dee\u8d85\u8fc7 20 \u97f3\u5206\uff0c\u53ef\u80fd\u8c03\u9519\u5f26\u6216\u8c03\u9519\u516b\u5ea6\uff0c\u6574\u5f26\u91cd\u8c03'})
        elif r['sev'] == 2:
            issues.append({'sev': 2, 'item': r['name'],
                           'detail': '\u5b9e\u6d4b %.2f \u8d6b\u5179\uff0c\u6807\u51c6 %.2f \u8d6b\u5179\uff0c\u504f\u5dee %+.1f \u97f3\u5206'
                                     % (r['freq'], r['ref'], r['cents']),
                           'why': '\u504f\u5dee %s\uff0c\u5f80%s\u65b9\u5411\u5fae\u8c03'
                                  % ('\u8f83\u5927' if abs(r['cents']) > 10 else '\u8f83\u5c0f',
                                     '\u4f4e' if r['cents'] > 0 else '\u9ad8')})

    issues.sort(key=lambda r: -r['sev'])

    n_bad = len([r for r in rows if r['sev'] >= 3])
    if n_bad or any(i['sev'] == 3 for i in issues):
        level = '\u6709\u660e\u663e\u95ee\u9898'
    elif any(r['status'] == '\u660e\u663e\u8dd1\u8c03' for r in rows):
        level = '\u6709\u660e\u663e\u95ee\u9898'
    elif issues:
        level = '\u6709\u53ef\u6539\u8fdb\u9879'
    elif rows and all(r['cents'] is None for r in rows) and not chords and not plan_miss:
        level = '\u5f85\u786e\u8ba4'
    elif any(r['cents'] is None for r in rows):
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u5408\u683c'

    worst = sorted([r for r in rows if r['cents'] is not None],
                   key=lambda r: -abs(r['cents']))
    return {
        'level': level, 'rows': rows, 'issues': issues,
        'n_chord_wrong': n_chord_wrong,
        'worst': [r['name'] for r in worst[:3]],
        'chords': CHORDS, 'plan_stages': PLAN_STAGES,
    }


def render_md(r):
    L = []
    L.append('# \u5c24\u514b\u91cc\u91cc\u5165\u95e8\u7ec3\u4e60\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['level'])
    if r['worst']:
        L.append('- \u504f\u5dee\u6700\u5927\u7684\u5148\u8c03\uff1a%s' % '\u3001'.join(r['worst']))
    L.append('')
    L.append('## \u4e8c\u3001\u56db\u5f26\u8c03\u97f3\u5224\u5b9a')
    L.append('')
    L.append('| \u5f26 | \u6807\u51c6\u9891\u7387 | \u5b9e\u6d4b\u9891\u7387 | \u504f\u5dee | \u5224\u5b9a |')
    L.append('|---|---|---|---|---|')
    for row in r['rows']:
        L.append('| %s | %.2f \u8d6b\u5179 | %s | %s | %s |'
                 % (row['name'], row['ref'],
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
    L.append('## \u56db\u3001\u7ec3\u4e60\u8def\u5f84\u56db\u9636\u6bb5')
    L.append('')
    L.append('| \u987a\u5e8f | \u9636\u6bb5 |')
    L.append('|---|---|')
    for s in r['plan_stages']:
        L.append('| %s | %s |' % (PLAN_STAGES.index(s) + 1, PLAN_LABELS[s]))
    L.append('')
    L.append('## \u4e94\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355')
    L.append('')
    L.append('- [ ] \u56db\u5f26\u5df2\u8c03\u5230 gCEA \u6807\u51c6\u97f3')
    L.append('- [ ] \u6309\u54c1\u624b\u6307\u843d\u5728\u54c1\u4e1d\u540e\u65b9\u4e00\u683c')
    L.append('- [ ] \u6362\u548c\u5f26\u5148\u627e\u5171\u540c\u6307')
    L.append('- [ ] \u626b\u5f26\u7528\u624b\u8155\u5e26\u52a8')
    L.append('- [ ] \u624b\u6307\u75bc\u5c31\u505c\uff0c\u6bcf\u5929 15 \u5230 25 \u5206\u949f')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u6807\u51c6\u9891\u7387
    ck(abs(freq_of(67) - 392.0) < 0.01, 'G4 \u5e94\u4e3a 392.00\uff0c\u5b9e\u4e3a %.4f' % freq_of(67))
    ck(abs(freq_of(60) - 261.63) < 0.01, 'C4 \u5e94\u4e3a 261.63\uff0c\u5b9e\u4e3a %.4f' % freq_of(60))
    ck(abs(freq_of(64) - 329.63) < 0.01, 'E4 \u5e94\u4e3a 329.63\uff0c\u5b9e\u4e3a %.4f' % freq_of(64))
    ck(abs(freq_of(69) - 440.0) < 1e-9, 'A4 \u5e94\u4e3a 440.00\uff0c\u5b9e\u4e3a %.4f' % freq_of(69))

    # 2 \u97f3\u5206
    ck(abs(cents(440 * 2, 440) - 1200) < 1e-9, '\u9ad8\u516b\u5ea6 +1200 \u97f3\u5206')
    ck(abs(cents(440, 440)) < 1e-9, '\u540c\u9891 0 \u97f3\u5206')

    # 3 \u5168\u6807\u51c6\u6b63\u4f8b\uff08\u8c03\u97f3\uff09
    std = {k: freq_of(STRING_MIDI[k]) for k in STRING_KEYS}
    r3 = calc({'tuning': std})
    ck(r3['level'] == '\u5408\u683c', '\u5168\u6807\u51c6\u8c03\u97f3\u5e94\u5408\u683c\uff0c\u5b9e\u4e3a %s' % r3['level'])

    # 4 \u53cd\u4f8b\uff1a\u56db\u5f26\u8c03\u6210 370\uff08\u4e25\u91cd\u8dd1\u8c03\uff09
    bad = dict(std)
    bad['g'] = 370.0
    r4 = calc({'tuning': bad})
    ck(r4['level'] == '\u6709\u660e\u663e\u95ee\u9898', '\u56db\u5f26 370 \u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r4['level'])
    ck(r4['rows'][0]['sev'] == 3, '\u56db\u5f26\u5e94 sev3\uff0c\u5b9e\u4e3a %s' % r4['rows'][0]['sev'])

    # 5 \u5206\u7ea7\u8fb9\u754c
    def tun(dev):
        out = dict(std)
        out['g'] = freq_of(67) * (2 ** (dev / 1200.0))
        return out

    ck(calc({'tuning': tun(5)})['level'] == '\u5408\u683c', '5 \u97f3\u5206\u8fb9\u754c\u5e94\u5408\u683c')
    ck(calc({'tuning': tun(8)})['level'] == '\u6709\u53ef\u6539\u8fdb\u9879', '8 \u97f3\u5206\u5e94\u5224\u9700\u5fae\u8c03')
    ck(calc({'tuning': tun(15)})['level'] == '\u6709\u660e\u663e\u95ee\u9898', '15 \u97f3\u5206\u5e94\u5224\u660e\u663e\u8dd1\u8c03')
    ck(calc({'tuning': tun(40)})['level'] == '\u6709\u660e\u663e\u95ee\u9898', '40 \u97f3\u5206\u5e94\u5224\u4e25\u91cd\u8dd1\u8c03')

    # 6 \u53cd\u4f8b\uff1aC \u548c\u5f26\u6309\u6210\u4e00\u5f26 0 \u54c1
    r6 = calc({'chords': [{'name': 'C', 'frets': [0, 0, 0, 0]}]})
    ck(r6['n_chord_wrong'] == 1, 'C \u9519\u5e94\u8bb0 1 \u4e2a\u9519\u548c\u5f26\uff0c\u5b9e\u4e3a %d' % r6['n_chord_wrong'])
    ck(any(i['item'] == 'C \u548c\u5f26' for i in r6['issues']), '\u5e94\u70b9\u540d C \u548c\u5f26')
    ck('\u4e00\u5f26' in r6['issues'][0]['detail'], '\u5e94\u6307\u51fa\u4e00\u5f26\u9519\uff0c\u5b9e\u4e3a %s' % r6['issues'][0]['detail'])

    # 7 \u6b63\u786e\u7684 C \u548c\u5f26
    r7 = calc({'chords': [{'name': 'C', 'frets': [0, 0, 0, 3]}]})
    ck(r7['n_chord_wrong'] == 0, '\u6b63\u786e C \u4e0d\u5e94\u6709\u9519\u548c\u5f26')

    # 8 \u53cd\u4f8b\uff1aF \u548c\u5f26\u4e8c\u5f26\u6309\u6210 0 \u54c1
    r8 = calc({'chords': [{'name': 'F', 'frets': [2, 0, 0, 0]}]})
    ck(any(i['item'] == 'F \u548c\u5f26' for i in r8['issues']), 'F \u9519\u5e94\u70b9\u540d')
    ck('\u4e8c\u5f26' in r8['issues'][0]['detail'], '\u5e94\u6307\u51fa\u4e8c\u5f26\u9519')

    # 9 \u53cd\u4f8b\uff1a\u7ec3\u4e60\u8def\u5f84\u7f3a\u9636\u6bb51\u3001\u4e14\u987a\u5e8f\u98a0\u5012
    r9 = calc({'plan': ['first_song', 'single_chord']})
    ck(any('\u7f3a\u5c11\u9636\u6bb51' in i['detail'] for i in r9['issues']), '\u5e94\u6307\u51fa\u7f3a\u9636\u6bb51')
    ck(any('\u4e4b\u540e' in i['detail'] for i in r9['issues']), '\u5e94\u6307\u51fa\u987a\u5e8f\u98a0\u5012')

    # 10 \u6b63\u786e\u7684\u7ec3\u4e60\u8def\u5f84
    r10 = calc({'plan': ['tuning', 'single_chord', 'transition', 'first_song']})
    ck(r10['issues'] == [], '\u6b63\u786e\u8def\u5f84\u4e0d\u5e94\u6709\u95ee\u9898\uff0c\u5b9e\u4e3a %s' % r10['issues'])

    # 11 \u5224\u5b9a\u987a\u5e8f\uff1a\u8c03\u97f3\u4e25\u91cd\u8dd1\u8c03\u4e0d\u5e94\u56e0\u7f3a plan \u5224\u5f85\u786e\u8ba4
    r11 = calc({'tuning': bad})
    ck(r11['level'] == '\u6709\u660e\u663e\u95ee\u9898', '\u53ea\u586b\u8dd1\u8c03\u8c03\u97f3\u4e0d\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r11['level'])

    # 12 \u504f\u79fb\u6392\u5e8f\u65b9\u5411\uff1a\u504f\u5dee\u6700\u5927\u7684\u6392\u6700\u524d
    r12 = calc({'tuning': {k: freq_of(STRING_MIDI[k]) for k in STRING_KEYS},
                'chords': [{'name': 'C', 'frets': [0, 0, 0, 0]}]})
    ck(r12['worst'][0] == '\u56db\u5f26(g)', '\u6700\u5dee\u5e94\u56db\u5f26\uff0c\u5b9e\u4e3a %s' % r12['worst'])

    # 13 \u975e\u6cd5\u8f93\u5165
    for bad_in, why in (
        ({'tuning': {'g': 'x'}}, '\u9891\u7387\u975e\u6570\u5b57'),
        ({'tuning': {'g': 0}}, '\u9891\u7387\u4e3a 0'),
        ({'chords': [{'name': 'X', 'frets': [0, 0, 0, 3]}]}, '\u672a\u77e5\u548c\u5f26'),
        ({'chords': [{'name': 'C', 'frets': [0, 0, 0]}]}, 'frets \u957f\u5ea6\u9519'),
        ({'plan': 'tuning'}, 'plan \u975e\u5217\u8868'),
    ):
        try:
            calc(bad_in)
            ck(False, '\u7528\u4f8b13 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 14 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'tuning': bad})
    r14 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r14['level'] == '\u6709\u660e\u663e\u95ee\u9898', 'BOM \u5b57\u7b26\u4e32\u5e94\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r14['level'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_u.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'chords': [{'name': 'C', 'frets': [0, 0, 0, 0]}]}))
    try:
        r14b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r14b['n_chord_wrong'] == 1, 'BOM \u6587\u4ef6\u5e94\u89e3\u6790\u51fa\u9519\u548c\u5f26\uff0c\u5b9e\u4e3a %s' % r14b['n_chord_wrong'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 15 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r4)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u56db\u5f26\u8c03\u97f3\u5224\u5b9a', '\u7ec3\u4e60\u8def\u5f84\u56db\u9636\u6bb5', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(CHORDS) == 10, '\u548c\u5f26\u5e94 10 \u4e2a\uff0c\u5b9e\u4e3a %d' % len(CHORDS))
    ck(len(STRING_KEYS) == 4, '\u5f26\u5e94 4 \u6839')
    ck(CHORDS['C'] == [0, 0, 0, 3], 'C \u548c\u5f26\u6307\u6cd5\u5e94\u4e3a [0,0,0,3]')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u56db\u5f26\u6807\u51c6\u9891\u7387/\u97f3\u5206/\u5168\u6807\u51c6\u6b63\u4f8b/\u56db\u5f26370\u53cd\u4f8b/'
        '\u5206\u7ea7\u8fb9\u754c(5,8,15,40)/C\u548c\u5f26\u9519\u53cd\u4f8b/\u6b63\u786eC/F\u548c\u5f26\u9519\u53cd\u4f8b/\u8def\u5f84\u7f3a\u9636\u6bb5\u4e0e\u98a0\u5012/'
        '\u6b63\u786e\u8def\u5f84/\u5224\u5b9a\u987a\u5e8f/\u504f\u5dee\u6392\u5e8f/\u975e\u6cd5\u8f93\u5165/BOM\u4e24\u6761\u8def\u5f84/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u5c24\u514b\u91cc\u91cc\u5165\u95e8\u7ec3\u4e60\u6838\u67e5')
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




