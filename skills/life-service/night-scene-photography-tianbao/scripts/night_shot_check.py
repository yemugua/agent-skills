# -*- coding: utf-8 -*-
"""\u591c\u666f\u62cd\u6444\u6838\u67e5\uff1a\u7b97\u5b89\u5168\u5feb\u95e8\u3001\u6838 ISO \u4e0a\u9650\u3001\u95ea\u5149\u706f\u3001\u66dd\u5149\u8865\u507f\u4e0e\u4e09\u811a\u67b6\u64cd\u4f5c\u3002

\u7528\u6cd5:
  python night_shot_check.py --file night.json [--out result.md] [--format json]
  python night_shot_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u8bbe\u5907: (\u952e, \u4e2d\u6587\u540d, ISO \u5efa\u8bae\u4e0a\u9650)
DEVICES = [
    ('phone', '\u624b\u673a', 3200),
    ('aps_c', '\u76f8\u673a\uff08\u534a\u5e45\uff09', 3200),
    ('full', '\u76f8\u673a\uff08\u5168\u5e45\uff09', 6400),
]

# \u652f\u6491\u65b9\u5f0f: (\u952e, \u4e2d\u6587\u540d, \u662f\u5426\u6709\u652f\u6491)
SUPPORT = [
    ('tripod', '\u4e09\u811a\u67b6', True),
    ('rest', '\u56fa\u5b9a\u4f9d\u6258\uff08\u680f\u6746\u3001\u5730\u9762\u3001\u5305\uff09', True),
    ('handheld', '\u624b\u6301', False),
]

# \u9608\u503c
TOL = {
    'ev_min': -1.0,       # \u591c\u666f\u66dd\u5149\u8865\u507f\u4e0b\u9650
    'ev_max': 0.0,        # \u591c\u666f\u66dd\u5149\u8865\u507f\u4e0a\u9650
    'ev_under': -2.0,     # \u6b20\u66dd\u4e0b\u9650
    'ev_over': 0.3,       # \u9ad8\u5149\u5f00\u59cb\u6ea2\u51fa\u7684\u4e0a\u754c
    'tripod_iso_max': 400,  # \u4e09\u811a\u67b6\u4e0b\u5efa\u8bae\u7684 ISO \u4e0a\u9650
    'rest_shutter_max': 0.5,  # \u4ec5\u6709\u4f9d\u6258\u65f6\u7684\u5efa\u8bae\u6700\u957f\u66dd\u5149
}

# \u9898\u6750\u66dd\u5149\u65f6\u957f\u53c2\u8003: (\u952e, \u4e2d\u6587\u540d, \u5feb\u95e8\u533a\u95f4, \u8981\u70b9)
SUBJECTS = [
    ('city', '\u57ce\u5e02\u591c\u666f\u3001\u5efa\u7b51', '2 \u5230 10 \u79d2', '\u7b49\u8f66\u5c11\u7684\u65f6\u5019\u62cd\uff0c\u907f\u514d\u8f66\u706f\u8fc7\u66dd'),
    ('trail', '\u8f66\u6d41\u5149\u8f68', '8 \u5230 30 \u79d2', '\u9700\u8981\u4e09\u811a\u67b6\uff0cISO \u538b\u5230\u6700\u4f4e\uff0c\u7528\u5c0f\u5149\u5708'),
    ('water', '\u6c34\u9762\u5012\u5f71', '1 \u5230 5 \u79d2', '\u6c34\u9762\u5e73\u9759\u65f6\u5012\u5f71\u624d\u6e05\u6670'),
    ('star', '\u661f\u7a7a\uff08\u65e0\u8d64\u9053\u4eea\uff09', '15 \u5230 25 \u79d2', '\u8d85\u8fc7 30 \u79d2\u661f\u661f\u4f1a\u62d6\u7ebf\uff0c\u7528\u5927\u5149\u5708\u9ad8 ISO'),
    ('handheld', '\u624b\u6301\u591c\u666f', '\u4e0d\u957f\u4e8e\u5b89\u5168\u5feb\u95e8', '\u9760\u63d0 ISO \u548c\u8fde\u62cd\u6311\u7247'),
]


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def _f(shot, key):
    v = shot.get(key)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError('%s \u5fc5\u987b\u662f\u6570\u5b57\uff0c\u5b9e\u4e3a %s' % (key, v))
    if f <= 0:
        raise ValueError('%s \u5fc5\u987b\u4e3a\u6b63\u6570\uff0c\u5b9e\u4e3a %s' % (key, v))
    return f


def _row(table, key, val, label):
    if val is None or val == '':
        return None
    n = norm(val)
    for r in table:
        if norm(r[0]) == n:
            return r
    raise ValueError('\u672a\u77e5\u7684 %s: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00' % (label, val, '/'.join(r[0] for r in table)))


def safe_shutter(focal, crop):
    """\u5b89\u5168\u5feb\u95e8 = 1 / (\u7b49\u6548\u7126\u8ddd * \u88c1\u5207\u7cfb\u6570)\u3002"""
    return 1.0 / (focal * crop)


def shot_check(shot):
    if not isinstance(shot, dict):
        raise ValueError('shots \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
    name = str(shot.get('name') or '\u672a\u547d\u540d').strip()
    dev = _row(DEVICES, 'device', shot.get('device'), 'device')
    sup = _row(SUPPORT, 'support', shot.get('support'), 'support')
    focal = _f(shot, 'focal_mm')
    crop = _f(shot, 'crop') or 1.0
    shutter = _f(shot, 'shutter_s')
    iso = _f(shot, 'iso')
    ev = shot.get('ev')
    ev = float(ev) if ev is not None else None
    flash = shot.get('flash')
    night = shot.get('night_mode')
    raw = shot.get('raw')
    remote = shot.get('timer_or_remote')
    subject = _row(SUBJECTS, 'subject', shot.get('subject'), 'subject')

    issues = []
    misses = []
    facts = {}

    if dev is None:
        misses.append('\u8bbe\u5907\u7c7b\u578b')
    if sup is None:
        misses.append('\u652f\u6491\u65b9\u5f0f')
    if focal is None:
        misses.append('\u7b49\u6548\u7126\u8ddd')

    # \u5b89\u5168\u5feb\u95e8
    if focal is not None:
        safe = safe_shutter(focal, crop)
        facts['safe_shutter'] = safe
        if shutter is not None:
            facts['over_stop'] = (shutter / safe) if safe else 0.0
            # \u624b\u6301\uff1a\u5feb\u95e8\u65f6\u95f4\u5fc5\u987b\u4e0d\u957f\u4e8e\u5b89\u5168\u5feb\u95e8
            if sup is not None and not sup[2] and shutter > safe:
                issues.append({
                    'sev': 3, 'item': '\u5b89\u5168\u5feb\u95e8',
                    'detail': '\u624b\u6301 %.3f \u79d2\uff0c\u5b89\u5168\u5feb\u95e8\u4e3a 1/%.0f \u79d2\uff08\u7ea6 %.3f \u79d2\uff09\uff0c\u8d85\u51fa\u7ea6 %.0f \u500d'
                              % (shutter, 1.0 / safe, safe, shutter / safe),
                    'why': '\u624b\u6301\u66dd\u5149\u8d85\u8fc7\u5b89\u5168\u5feb\u95e8\u5fc5\u7136\u62cd\u7cca\uff0c\u5149\u5b66\u9632\u6296\u6551\u4e0d\u4e86\u8fd9\u4e48\u5927\u7684\u7f3a\u53e3\uff1b'
                           '\u4e0a\u4e09\u811a\u67b6\u3001\u627e\u56fa\u5b9a\u4f9d\u6258\uff0c\u6216\u63d0\u9ad8 ISO \u628a\u5feb\u95e8\u538b\u56de\u6765',
                })
            # \u4ec5\u6709\u4f9d\u6258\uff1a\u66dd\u5149\u4e5f\u4e0d\u5b9c\u8fc7\u957f
            elif sup is not None and sup[0] == 'rest' and shutter > TOL['rest_shutter_max']:
                issues.append({
                    'sev': 2, 'item': '\u652f\u6491\u7a33\u5b9a\u6027',
                    'detail': '\u4ec5\u6709\u4f9d\u6258\u5374\u7528\u4e86 %.2f \u79d2\u66dd\u5149' % shutter,
                    'why': '\u680f\u6746\u3001\u5305\u8fd9\u7c7b\u4f9d\u6258\u80fd\u5ef6\u957f\u4e00\u4e24\u6321\uff0c\u4f46\u6491\u4e0d\u4f4f\u79d2\u7ea7\u957f\u66dd\u5149\uff0c\u5efa\u8bae\u6539\u7528\u4e09\u811a\u67b6',
                })
        # \u4e09\u811a\u67b6\u4e0b\u5374\u7528\u4e86\u8fc7\u77ed\u66dd\u5149\u4e14\u9ad8 ISO\uff1a\u672c\u53ef\u4ee5\u66f4\u597d
        if sup is not None and sup[0] == 'tripod' and iso is not None \
                and iso > TOL['tripod_iso_max'] and shutter is not None and shutter >= 1.0:
            issues.append({
                'sev': 2, 'item': 'ISO \u504f\u9ad8',
                'detail': '\u5df2\u4e0a\u4e09\u811a\u67b6\u4e14\u66dd\u5149 %.1f \u79d2\uff0cISO \u5374\u7528\u5230 %.0f' % (shutter, iso),
                'why': '\u4e09\u811a\u67b6\u7684\u610f\u4e49\u5c31\u662f\u7528\u957f\u66dd\u5149\u6362\u4f4e ISO\uff0c\u6b64\u65f6\u5e94\u628a ISO \u538b\u5230 100 \u5230 400',
            })
    else:
        misses.append('\u5b89\u5168\u5feb\u95e8\uff08\u9700\u7126\u8ddd\uff09')

    # ISO \u4e0a\u9650
    if iso is None:
        misses.append('ISO')
    elif dev is not None:
        limit = dev[2]
        if iso > limit:
            issues.append({
                'sev': 3, 'item': 'ISO',
                'detail': 'ISO %.0f\uff0c\u8d85\u8fc7%s\u5efa\u8bae\u4e0a\u9650 %d' % (iso, dev[1], limit),
                'why': '\u8d85\u8fc7\u4e0a\u9650\u540e\u964d\u566a\u7b97\u6cd5\u4f1a\u5f3a\u529b\u6d82\u62b9\uff0c\u5efa\u7b51\u8fb9\u7f18\u53d1\u7cca\u3001\u7ec6\u8282\u53d8\u8272\u5757\u3001'
                       '\u6697\u90e8\u51fa\u73b0\u5f69\u8272\u566a\u70b9\uff1b\u6b63\u786e\u8def\u5f84\u662f\u7528\u4e09\u811a\u67b6\u6362\u957f\u66dd\u5149\uff0c\u800c\u4e0d\u662f\u786c\u62c9 ISO',
            })

    # \u95ea\u5149\u706f
    if flash is None:
        misses.append('\u95ea\u5149\u706f\u72b6\u6001')
    elif flash:
        issues.append({
            'sev': 3, 'item': '\u95ea\u5149\u706f',
            'detail': '\u5f00\u7740\u95ea\u5149\u706f\u62cd\u591c\u666f',
            'why': '\u95ea\u5149\u53ea\u7167\u4eae 2 \u5230 5 \u7c73\uff0c\u8fd1\u5904\u6b7b\u767d\u3001\u8fdc\u5904\u4f9d\u7136\u9ed1\u3001\u6696\u8272\u6c1b\u56f4\u88ab\u51b7\u767d\u5149\u538b\u6389\uff1b'
                   '\u9700\u8981\u8865\u8fd1\u5904\u4e3b\u4f53\u65f6\u7528\u5e38\u4eae\u5149\uff0c\u4e0d\u8981\u5f00\u95ea\u5149',
        })

    # \u66dd\u5149\u8865\u507f
    if ev is None:
        misses.append('\u66dd\u5149\u8865\u507f')
    else:
        if ev > TOL['ev_over']:
            issues.append({
                'sev': 2, 'item': '\u66dd\u5149\u8865\u507f',
                'detail': '%.1f EV\uff0c\u9ad8\u4e8e %.1f' % (ev, TOL['ev_over']),
                'why': '\u591c\u666f\u52a0\u66dd\u5149\u4f1a\u8ba9\u706f\u724c\u3001\u9713\u8679\u3001\u5929\u7a7a\u7684\u9ad8\u5149\u6ea2\u51fa\u6210\u6b7b\u767d\uff0c\u4e14\u540e\u671f\u62c9\u4e0d\u56de\u6765\uff1b'
                       '\u5b81\u53ef\u7a0d\u6b20\u4e0d\u53ef\u8fc7\u66dd\uff0c\u5e94\u538b\u5728\u8d1f 1.0 \u5230 0',
            })
        elif ev < TOL['ev_under']:
            issues.append({
                'sev': 2, 'item': '\u66dd\u5149\u8865\u507f',
                'detail': '%.1f EV\uff0c\u4f4e\u4e8e %.1f' % (ev, TOL['ev_under']),
                'why': '\u538b\u5f97\u592a\u72e0\u6574\u4f53\u6b20\u66dd\uff0c\u540e\u671f\u63d0\u4eae\u6697\u90e8\u4f1a\u8ba9\u566a\u70b9\u7206\u70b8',
            })

    # \u591c\u666f\u6a21\u5f0f\uff08\u624b\u673a\uff09
    if dev is not None and dev[0] == 'phone':
        if night is None:
            misses.append('\u591c\u666f\u6a21\u5f0f')
        elif not night and sup is not None and not sup[2]:
            issues.append({
                'sev': 2, 'item': '\u591c\u666f\u6a21\u5f0f',
                'detail': '\u624b\u673a\u624b\u6301\u62cd\u591c\u666f\u5374\u6ca1\u5f00\u591c\u666f\u6a21\u5f0f',
                'why': '\u624b\u6301\u591c\u666f\u9760\u591a\u5e27\u5408\u6210\u624d\u80fd\u538b\u4f4f\u566a\u70b9\uff0c\u4e0d\u5f00\u591c\u666f\u6a21\u5f0f\u753b\u8d28\u4f1a\u660e\u663e\u53d8\u5dee',
            })

    # RAW
    if raw is False:
        issues.append({
            'sev': 2, 'item': 'RAW',
            'detail': '\u672a\u62cd RAW',
            'why': '\u591c\u666f\u6697\u90e8\u9700\u8981\u540e\u671f\u63d0\u4eae\uff0cJPG \u7684\u5bbd\u5bb9\u5ea6\u4e0d\u591f\uff1b\u62cd RAW \u624d\u6709\u63d0\u4eae\u7a7a\u95f4',
        })

    # \u4e09\u811a\u67b6\u4e0a\u624b\u6309\u5feb\u95e8
    if sup is not None and sup[0] == 'tripod':
        if remote is None:
            misses.append('\u5b9a\u65f6\u6216\u9065\u63a7\u5feb\u95e8')
        elif not remote:
            issues.append({
                'sev': 2, 'item': '\u6309\u5feb\u95e8\u65b9\u5f0f',
                'detail': '\u4e09\u811a\u67b6\u4e0a\u7528\u624b\u76f4\u63a5\u6309\u5feb\u95e8',
                'why': '\u6309\u4e0b\u90a3\u4e00\u4e0b\u7684\u6296\u52a8\u5c31\u591f\u6bc1\u6389\u51e0\u79d2\u7684\u957f\u66dd\u5149\uff1b\u7528 2 \u79d2\u5b9a\u65f6\u6216\u5feb\u95e8\u7ebf',
            })

    issues.sort(key=lambda r: -r['sev'])

    if any(i['sev'] == 3 for i in issues):
        level = '\u53c2\u6570\u6709\u660e\u663e\u95ee\u9898'
    elif issues:
        level = '\u6709\u53ef\u6539\u8fdb\u9879'
    elif misses:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u53c2\u6570\u53ef\u884c'

    return {
        'name': name, 'level': level, 'issues': issues, 'misses': misses,
        'facts': facts, 'device': dev[1] if dev else None,
        'support': sup[1] if sup else None,
        'focal': focal, 'crop': crop, 'shutter': shutter, 'iso': iso, 'ev': ev,
        'subject': subject[1] if subject else None,
    }


def calc(data):
    shots = data.get('shots')
    if shots is None:
        raise ValueError('\u8f93\u5165\u7f3a\u5c11 shots \u5217\u8868')
    if not isinstance(shots, list) or not shots:
        raise ValueError('shots \u5fc5\u987b\u662f\u975e\u7a7a\u5217\u8868')
    rows = [shot_check(s) for s in shots]
    n_bad = len([r for r in rows if r['level'] == '\u53c2\u6570\u6709\u660e\u663e\u95ee\u9898'])
    n_mid = len([r for r in rows if r['level'] == '\u6709\u53ef\u6539\u8fdb\u9879'])
    n_unk = len([r for r in rows if r['level'] == '\u5f85\u786e\u8ba4'])
    if n_bad:
        overall = '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u591c\u666f'
    elif n_mid:
        overall = '\u5b58\u5728\u53ef\u6539\u8fdb\u7684\u591c\u666f'
    elif n_unk:
        overall = '\u5f85\u786e\u8ba4'
    else:
        overall = '\u5168\u90e8\u53c2\u6570\u53ef\u884c'

    def _sev(r):
        return max([i['sev'] for i in r['issues']], default=0)

    order = sorted(rows, key=lambda r: (-_sev(r), -len(r['issues']), r['name']))
    return {
        'overall': overall, 'rows': rows,
        'n_bad': n_bad, 'n_mid': n_mid, 'n_unk': n_unk,
        'n_ok': len(rows) - n_bad - n_mid - n_unk,
        'fix_order': [r['name'] for r in order if r['issues']],
        'devices': [{'key': k, 'name': n, 'iso_max': m} for k, n, m in DEVICES],
        'supports': [{'key': k, 'name': n, 'stable': s} for k, n, s in SUPPORT],
        'subjects': [{'key': k, 'name': n, 'shutter': s, 'note': nt} for k, n, s, nt in SUBJECTS],
        'tol': dict(TOL),
    }


def render_md(r):
    L = []
    L.append('# \u591c\u666f\u62cd\u6444\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['overall'])
    L.append('')
    L.append('| \u7c7b\u522b | \u5f20\u6570 |')
    L.append('|---|---|')
    L.append('| \u9700\u8981\u91cd\u62cd | %d |' % r['n_bad'])
    L.append('| \u53ef\u6539\u8fdb | %d |' % r['n_mid'])
    L.append('| \u5f85\u786e\u8ba4 | %d |' % r['n_unk'])
    L.append('| \u53c2\u6570\u53ef\u884c | %d |' % r['n_ok'])
    L.append('')
    if r['fix_order']:
        L.append('\u6574\u6539\u987a\u5e8f\uff08\u4e25\u91cd\u5ea6\u9ad8\u7684\u5148\u6539\uff09\uff1a%s' % '\u3001'.join(r['fix_order']))
        L.append('')
    L.append('## \u4e8c\u3001\u9010\u5f20\u5224\u5b9a')
    L.append('')
    for row in r['rows']:
        L.append('### %s' % row['name'])
        L.append('')
        L.append('- \u5224\u5b9a\uff1a**%s**' % row['level'])
        if row['device']:
            L.append('- \u8bbe\u5907\uff1a%s' % row['device'])
        if row['support']:
            L.append('- \u652f\u6491\uff1a%s' % row['support'])
        if row['focal'] is not None:
            L.append('- \u7b49\u6548\u7126\u8ddd\uff1a%.0f mm\uff08\u88c1\u5207\u7cfb\u6570 %.1f\uff09' % (row['focal'], row['crop']))
        if row['facts'].get('safe_shutter'):
            L.append('- \u5b89\u5168\u5feb\u95e8\uff1a\u7ea6 %.4f \u79d2\uff081/%.0f \u79d2\uff09'
                     % (row['facts']['safe_shutter'], 1.0 / row['facts']['safe_shutter']))
        if row['shutter'] is not None:
            L.append('- \u5b9e\u9645\u5feb\u95e8\uff1a%.3f \u79d2' % row['shutter'])
        if row['iso'] is not None:
            L.append('- ISO\uff1a%.0f' % row['iso'])
        if row['ev'] is not None:
            L.append('- \u66dd\u5149\u8865\u507f\uff1a%.1f EV' % row['ev'])
        if row['subject']:
            L.append('- \u9898\u6750\uff1a%s' % row['subject'])
        if row['issues']:
            L.append('')
            L.append('| \u4e25\u91cd\u5ea6 | \u9879\u76ee | \u95ee\u9898 | \u4e3a\u4ec0\u4e48\u8981\u5728\u610f |')
            L.append('|---|---|---|---|')
            for i in row['issues']:
                L.append('| %s | %s | %s | %s |'
                         % ('\u4e25\u91cd' if i['sev'] == 3 else '\u53ef\u6539\u8fdb', i['item'], i['detail'], i['why']))
        if row['misses']:
            L.append('')
            L.append('- \u672a\u586b\u5199\uff1a%s' % '\u3001'.join(row['misses']))
        L.append('')
    L.append('## \u4e09\u3001ISO \u5efa\u8bae\u4e0a\u9650')
    L.append('')
    L.append('| \u8bbe\u5907 | \u4e0a\u9650 |')
    L.append('|---|---|')
    for d in r['devices']:
        L.append('| %s | %d |' % (d['name'], d['iso_max']))
    L.append('')
    L.append('## \u56db\u3001\u9898\u6750\u66dd\u5149\u65f6\u957f\u53c2\u8003')
    L.append('')
    L.append('| \u9898\u6750 | \u5feb\u95e8\u65f6\u95f4 | \u8981\u70b9 |')
    L.append('|---|---|---|')
    for s in r['subjects']:
        L.append('| %s | %s | %s |' % (s['name'], s['shutter'], s['note']))
    L.append('')
    L.append('## \u4e94\u3001\u9608\u503c')
    L.append('')
    L.append('| \u9879\u76ee | \u9608\u503c |')
    L.append('|---|---|')
    L.append('| \u66dd\u5149\u8865\u507f | %.1f \u5230 %.1f EV\uff08\u4f4e\u4e8e %.1f \u7b97\u6b20\u66dd\uff0c\u9ad8\u4e8e %.1f \u7b97\u6ea2\u51fa\uff09 |'
             % (r['tol']['ev_min'], r['tol']['ev_max'], r['tol']['ev_under'], r['tol']['ev_over']))
    L.append('| \u4e09\u811a\u67b6\u4e0b ISO | \u4e0d\u9ad8\u4e8e %d |' % r['tol']['tripod_iso_max'])
    L.append('| \u4ec5\u6709\u4f9d\u6258\u65f6\u6700\u957f\u66dd\u5149 | %.1f \u79d2 |' % r['tol']['rest_shutter_max'])
    L.append('')
    L.append('## \u516d\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5df2\u7b97\u5b89\u5168\u5feb\u95e8\uff0c\u624b\u6301\u66dd\u5149\u4e0d\u957f\u4e8e\u8be5\u503c')
    L.append('- [ ] ISO \u672a\u8d85\u8fc7\u8bbe\u5907\u5efa\u8bae\u4e0a\u9650')
    L.append('- [ ] \u95ea\u5149\u706f\u5df2\u5173\u95ed')
    L.append('- [ ] \u66dd\u5149\u8865\u507f\u538b\u5728\u8d1f 1.0 \u5230 0')
    L.append('- [ ] \u4e09\u811a\u67b6\u65f6\u7528\u4e86 2 \u79d2\u5b9a\u65f6\u6216\u5feb\u95e8\u7ebf')
    L.append('- [ ] \u8fde\u62cd\u4e86 3 \u5230 5 \u5f20\uff0c\u56de\u5bb6\u6311\u6700\u6e05\u6670\u7684\u90a3\u5f20')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    tripod = {'name': '\u6c5f\u8fb9\u591c\u666f', 'device': 'full', 'support': 'tripod', 'focal_mm': 24,
              'crop': 1.0, 'shutter_s': 5.0, 'iso': 200, 'ev': -0.7, 'flash': False,
              'raw': True, 'timer_or_remote': True, 'subject': 'city'}

    # 1 \u4e09\u811a\u67b6\u6b63\u4f8b
    r1 = shot_check(tripod)
    ck(r1['level'] == '\u53c2\u6570\u53ef\u884c', '\u4e09\u811a\u67b6\u6b63\u4f8b\u5e94\u5224\u53c2\u6570\u53ef\u884c\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['issues'] == [], '\u4e09\u811a\u67b6\u6b63\u4f8b\u4e0d\u5e94\u6709\u95ee\u9898\u9879\uff0c\u5b9e\u4e3a %s' % r1['issues'])

    # 2 \u5b89\u5168\u5feb\u95e8\u8ba1\u7b97
    ck(abs(safe_shutter(24, 1.0) - 1.0 / 24) < 1e-9, '24mm \u5168\u5e45\u5b89\u5168\u5feb\u95e8\u5e94\u4e3a 1/24 \u79d2')
    ck(abs(safe_shutter(50, 1.5) - 1.0 / 75) < 1e-9, '50mm \u534a\u5e45\u5b89\u5168\u5feb\u95e8\u5e94\u4e3a 1/75 \u79d2')

    hand = {'name': '\u624b\u6301\u591c\u666f', 'device': 'phone', 'support': 'handheld',
            'focal_mm': 24, 'crop': 1.0, 'shutter_s': 1.0 / 30, 'iso': 1600,
            'ev': 0.0, 'flash': False, 'raw': True, 'night_mode': True}

    # 3 \u53cd\u4f8b\uff1a\u624b\u6301 24mm \u7528 0.5 \u79d2
    r3 = shot_check(dict(hand, shutter_s=0.5, ev=-0.5))
    ck(r3['level'] == '\u53c2\u6570\u6709\u660e\u663e\u95ee\u9898', '\u624b\u6301 0.5 \u79d2\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r3['level'])
    ck(any(i['item'] == '\u5b89\u5168\u5feb\u95e8' for i in r3['issues']), '\u5e94\u70b9\u540d\u5b89\u5168\u5feb\u95e8')
    ck(r3['facts']['over_stop'] > 10, '\u5e94\u7b97\u51fa\u8d85\u51fa\u500d\u6570\uff0c\u5b9e\u4e3a %s' % r3['facts']['over_stop'])

    # 4 \u624b\u6301\u8fb9\u754c\uff1a1/25 \u79d2\u5408\u683c\uff0c1/20 \u79d2\u4e0d\u5408\u683c
    r4a = shot_check(dict(hand, name='\u624b\u6301\u8fb9\u754c\u5185', shutter_s=1.0 / 25))
    r4b = shot_check(dict(hand, name='\u624b\u6301\u8d85\u754c', shutter_s=1.0 / 20))
    ck(not any(i['item'] == '\u5b89\u5168\u5feb\u95e8' for i in r4a['issues']), '1/25 \u79d2\u5e94\u4e0d\u8d85\u8fc7 1/24 \u79d2')
    ck(any(i['item'] == '\u5b89\u5168\u5feb\u95e8' for i in r4b['issues']), '1/20 \u79d2\u5e94\u8d85\u8fc7 1/24 \u79d2')

    # 5 \u53cd\u4f8b\uff1a\u624b\u673a ISO \u8d85\u4e0a\u9650
    r5 = shot_check(dict(hand, iso=6400))
    ck(any(i['item'] == 'ISO' for i in r5['issues']), '\u624b\u673a ISO 6400 \u5e94\u5224\u4e25\u91cd')
    ck(r5['level'] == '\u53c2\u6570\u6709\u660e\u663e\u95ee\u9898', 'ISO \u8d85\u9650\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r5['level'])
    ck(not any(i['item'] == 'ISO' for i in shot_check(dict(hand, iso=3200))['issues']),
       '\u624b\u673a ISO 3200 \u8fb9\u754c\u5e94\u5408\u683c')
    ck(not any(i['item'] == 'ISO' for i in shot_check(dict(tripod, device='full', iso=6400))['issues']),
       '\u5168\u5e45 ISO 6400 \u8fb9\u754c\u5e94\u5408\u683c')
    ck(any(i['item'] == 'ISO' for i in shot_check(dict(tripod, device='full', iso=12800))['issues']),
       '\u5168\u5e45 ISO 12800 \u5e94\u4e0d\u5408\u683c')

    # 6 \u53cd\u4f8b\uff1a\u5f00\u95ea\u5149\u706f
    r6 = shot_check(dict(tripod, flash=True))
    ck(any(i['item'] == '\u95ea\u5149\u706f' for i in r6['issues']), '\u5f00\u95ea\u5149\u706f\u5e94\u5224\u4e25\u91cd')
    ck(r6['level'] == '\u53c2\u6570\u6709\u660e\u663e\u95ee\u9898', '\u5f00\u95ea\u5149\u706f\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r6['level'])

    # 7 \u53cd\u4f8b\uff1a\u66dd\u5149\u8865\u507f\u8fc7\u9ad8
    r7 = shot_check(dict(tripod, ev=1.0))
    ck(any(i['item'] == '\u66dd\u5149\u8865\u507f' for i in r7['issues']), 'EV +1.0 \u5e94\u63d0\u793a')
    ck(r7['level'] == '\u6709\u53ef\u6539\u8fdb\u9879', 'EV +1.0 \u5e94\u5224\u53ef\u6539\u8fdb\uff0c\u5b9e\u4e3a %s' % r7['level'])
    ck(any(i['item'] == '\u66dd\u5149\u8865\u507f' for i in shot_check(dict(tripod, ev=-2.5))['issues']),
       'EV -2.5 \u5e94\u63d0\u793a\u6b20\u66dd')
    ck(shot_check(dict(tripod, ev=0.0))['issues'] == [], 'EV 0 \u5e94\u5408\u683c')
    ck(shot_check(dict(tripod, ev=-1.0))['issues'] == [], 'EV -1.0 \u5e94\u5408\u683c')

    # 8 \u53cd\u4f8b\uff1a\u624b\u673a\u624b\u6301\u4e0d\u5f00\u591c\u666f\u6a21\u5f0f
    r8 = shot_check(dict(hand, name='\u624b\u673a\u624b\u6301', ev=-0.5, night_mode=False))
    ck(any(i['item'] == '\u591c\u666f\u6a21\u5f0f' for i in r8['issues']), '\u624b\u673a\u624b\u6301\u4e0d\u5f00\u591c\u666f\u6a21\u5f0f\u5e94\u63d0\u793a')
    ck(shot_check(dict(hand, ev=-0.5, night_mode=True))['level'] == '\u53c2\u6570\u53ef\u884c',
       '\u5f00\u4e86\u591c\u666f\u6a21\u5f0f\u5e94\u5408\u683c\uff0c\u5b9e\u4e3a %s' % shot_check(dict(hand, ev=-0.5, night_mode=True))['level'])

    # 9 \u53cd\u4f8b\uff1a\u4e09\u811a\u67b6\u4e0a\u624b\u6309\u5feb\u95e8
    r9 = shot_check(dict(tripod, timer_or_remote=False))
    ck(any(i['item'] == '\u6309\u5feb\u95e8\u65b9\u5f0f' for i in r9['issues']), '\u4e09\u811a\u67b6\u624b\u6309\u5feb\u95e8\u5e94\u63d0\u793a')

    # 10 \u53cd\u4f8b\uff1a\u4e09\u811a\u67b6\u957f\u66dd\u5149\u5374\u9ad8 ISO
    r10 = shot_check(dict(tripod, iso=3200))
    ck(any(i['item'] == 'ISO \u504f\u9ad8' for i in r10['issues']), '\u4e09\u811a\u67b6\u9ad8 ISO \u5e94\u63d0\u793a')

    # 11 \u53cd\u4f8b\uff1a\u53ea\u6709\u4f9d\u6258\u5374\u7528 2 \u79d2
    r11 = shot_check(dict(tripod, support='rest', shutter_s=2.0, iso=800))
    ck(any(i['item'] == '\u652f\u6491\u7a33\u5b9a\u6027' for i in r11['issues']), '\u4f9d\u6258\u7528 2 \u79d2\u5e94\u63d0\u793a')

    # 12 \u53cd\u4f8b\uff1a\u672a\u62cd RAW
    r12 = shot_check(dict(tripod, raw=False))
    ck(any(i['item'] == 'RAW' for i in r12['issues']), '\u672a\u62cd RAW \u5e94\u63d0\u793a')

    # 13 \u6392\u5e8f\u65b9\u5411\uff1a\u4e25\u91cd\u9879\u6392\u6700\u524d
    r13 = shot_check(dict(tripod, iso=12800, flash=True, ev=1.0))
    ck(r13['issues'][0]['sev'] == 3, '\u4e25\u91cd\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r13['issues'][0]['sev'])
    ck(r13['issues'][-1]['sev'] == 2, '\u672b\u4f4d\u5e94\u662f\u53ef\u6539\u8fdb\u9879')

    # 14 \u5224\u5b9a\u987a\u5e8f\uff1a\u6709\u4e25\u91cd\u9879\u65f6\u4e0d\u56e0\u7f3a\u4fe1\u606f\u5224\u5f85\u786e\u8ba4
    r14 = shot_check({'name': '\u53ea\u586b\u95ea\u5149\u706f', 'flash': True})
    ck(r14['level'] == '\u53c2\u6570\u6709\u660e\u663e\u95ee\u9898', '\u7f3a\u5176\u4ed6\u9879\u4f46\u6709\u4e25\u91cd\u9879\u4e0d\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r14['level'])
    r14b = shot_check({'name': '\u53ea\u586b\u7126\u8ddd', 'focal_mm': 24})
    ck(r14b['level'] == '\u5f85\u786e\u8ba4', '\u53ea\u586b\u7126\u8ddd\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r14b['level'])

    # 15 \u6c47\u603b\u4e0e\u6574\u6539\u987a\u5e8f
    r15 = calc({'shots': [tripod,
                          dict(tripod, name='\u624b\u6301\u7cca\u4e86', support='handheld', shutter_s=1.0, iso=3200),
                          dict(tripod, name='\u6ca1\u62cdRAW', raw=False)]})
    ck(r15['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u591c\u666f', '\u6709\u4e25\u91cd\u9879\u5e94\u5224\u9700\u8981\u91cd\u62cd\uff0c\u5b9e\u4e3a %s' % r15['overall'])
    ck(r15['n_bad'] == 1, '\u4e25\u91cd\u9879\u5e94\u4e3a 1 \u5f20\uff0c\u5b9e\u4e3a %d' % r15['n_bad'])
    ck(r15['fix_order'][0] == '\u624b\u6301\u7cca\u4e86', '\u4e25\u91cd\u9879\u5e94\u5148\u6539\uff0c\u5b9e\u4e3a %s' % r15['fix_order'])
    ck(r15['fix_order'][1] == '\u6ca1\u62cdRAW', '\u53ef\u6539\u8fdb\u9879\u6392\u5176\u540e\uff0c\u5b9e\u4e3a %s' % r15['fix_order'])

    # 16 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'shots': [dict(tripod, flash=True)]})
    r16 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r16['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u591c\u666f', 'BOM \u5b57\u7b26\u4e32\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r16['overall'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_c3.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'shots': [dict(tripod, name='\u5e26BOM', iso=12800)]}))
    try:
        r16b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r16b['rows'][0]['name'] == '\u5e26BOM', 'BOM \u6587\u4ef6\u9996\u4e2a key \u5e94\u89e3\u6790\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r16b['rows'][0]['name'])
        ck(r16b['n_bad'] == 1, 'ISO \u8d85\u9650\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %d' % r16b['n_bad'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 17 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({}, '\u7f3a shots'),
        ({'shots': []}, 'shots \u7a7a\u5217\u8868'),
        ({'shots': [dict(tripod, iso='abc')]}, 'ISO \u975e\u6570\u5b57'),
        ({'shots': [dict(tripod, shutter_s=0)]}, '\u5feb\u95e8\u975e\u6b63\u6570'),
        ({'shots': [dict(tripod, device='\u65e0\u4eba\u673a')]}, '\u672a\u77e5\u8bbe\u5907'),
        ({'shots': [dict(tripod, support='\u624b\u6301\u6296\u52a8')]}, '\u672a\u77e5\u652f\u6491\u65b9\u5f0f'),
        ({'shots': [dict(tripod, subject='\u6708\u4eae')]}, '\u672a\u77e5\u9898\u6750'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b17 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 18 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r15)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u9010\u5f20\u5224\u5b9a', 'ISO \u5efa\u8bae\u4e0a\u9650', '\u9898\u6750\u66dd\u5149\u65f6\u957f\u53c2\u8003', '\u9608\u503c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(DEVICES) == 3, '\u8bbe\u5907\u7c7b\u578b\u5e94 3 \u79cd')
    ck(len(SUBJECTS) >= 4, '\u9898\u6750\u53c2\u8003\u81f3\u5c11 4 \u6761')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u4e09\u811a\u67b6\u6b63\u4f8b/\u5b89\u5168\u5feb\u95e8\u8ba1\u7b97/\u624b\u6301\u8d85\u65f6\u53cd\u4f8b\u4e0e\u8fb9\u754c/ISO\u4e0a\u9650\u4e0e\u8fb9\u754c/'
        '\u95ea\u5149\u706f\u53cd\u4f8b/\u66dd\u5149\u8865\u507f\u4e0a\u4e0b\u754c/\u591c\u666f\u6a21\u5f0f\u53cd\u4f8b/\u624b\u6309\u5feb\u95e8\u53cd\u4f8b/\u4e09\u811a\u67b6\u9ad8ISO\u53cd\u4f8b/\u4f9d\u6258\u957f\u66dd\u5149\u53cd\u4f8b/'
        '\u672a\u62cdRAW\u53cd\u4f8b/\u4e25\u91cd\u9879\u6392\u5e8f/\u5224\u5b9a\u987a\u5e8f/\u6c47\u603b\u6574\u6539\u987a\u5e8f/BOM\u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u591c\u666f\u62cd\u6444\u6838\u67e5')
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
