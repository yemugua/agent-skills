# -*- coding: utf-8 -*-
"""\u4eba\u50cf\u6446\u59ff\u81ea\u67e5\uff1a\u6838\u67e5\u7126\u6bb5\u3001\u91cd\u5fc3\u817f\u3001\u624b\u81c2\u4e09\u89d2\u3001\u8f6c\u4f53\u3001\u4e0b\u5df4\u3001\u88c1\u5207\u4e0e\u7559\u767d\u3002

\u7528\u6cd5:
  python pose_check.py --file poses.json [--out result.md] [--format json]
  python pose_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u9608\u503c
TOL = {
    'lens_min': 35.0,        # \u4eba\u50cf\u53ef\u63a5\u53d7\u7684\u6700\u5c0f\u7b49\u6548\u7126\u8ddd
    'lens_ideal_lo': 50.0,   # \u63a8\u8350\u7126\u6bb5\u4e0b\u9650
    'lens_ideal_hi': 135.0,  # \u63a8\u8350\u7126\u6bb5\u4e0a\u9650
    'turn_min': 20.0,        # \u8f6c\u4f53\u89d2\u5ea6\u4e0b\u9650\uff08\u5ea6\uff09
    'turn_max': 45.0,        # \u8f6c\u4f53\u89d2\u5ea6\u4e0a\u9650\uff08\u5ea6\uff09
    'shoulder_min': 5.0,     # \u80a9\u7ebf\u89d2\u5ea6\u4e0b\u9650\uff08\u5ea6\uff09
    'shoulder_max': 30.0,    # \u80a9\u7ebf\u89d2\u5ea6\u4e0a\u9650\uff08\u5ea6\uff09
    'headroom_min': 0.05,    # \u5934\u9876\u7559\u767d\u4e0b\u9650
    'headroom_max': 0.20,    # \u5934\u9876\u7559\u767d\u4e0a\u9650
}

# \u624b\u7684\u5b89\u6392\u65b9\u5f0f\uff1a\u503c\u4e3a True \u8868\u793a\u300c\u624b\u6709\u660e\u786e\u5b89\u6392\u300d
HAND_POSE = [
    ('waist', '\u624b\u53c9\u8170', '\u62c7\u6307\u671d\u540e\uff0c\u624b\u8098\u5411\u540e\u6491\u5f00\uff0c\u624b\u81c2\u4e0e\u8eaf\u5e72\u7559\u51fa\u4e09\u89d2'),
    ('pocket', '\u63d2\u515c\u9732\u62c7\u6307', '\u624b\u63d2\u88e4\u515c\u6216\u8863\u515c\uff0c\u9732\u51fa\u62c7\u6307\uff0c\u4e0d\u8981\u6574\u53ea\u624b\u585e\u8fdb\u53bb'),
    ('hold', '\u62ff\u4e1c\u897f', '\u62ff\u676f\u5b50\u3001\u5916\u5957\u3001\u5305\u3001\u82b1\uff0c\u8ba9\u624b\u6709\u4e8b\u60c5\u505a'),
    ('face', '\u62ac\u624b\u78b0\u8138', '\u8f7b\u64a9\u5934\u53d1\u3001\u6276\u773c\u955c\u3001\u642d\u4e0b\u5df4\uff0c\u624b\u6307\u653e\u677e\u4e0d\u8981\u7528\u529b\u6309'),
    ('lean', '\u6276\u5899\u6216\u6276\u6905', '\u624b\u6491\u5728\u5899\u9762\u3001\u680f\u6746\u3001\u6905\u9762\u4e0a\uff0c\u624b\u81c2\u81ea\u7136\u4f38\u957f'),
]

# \u773c\u795e\u65b9\u5411: (\u952e, \u8bf4\u660e, \u662f\u5426\u6da3\u6563)
EYE = [
    ('lens', '\u770b\u955c\u5934', False),
    ('off_axis', '\u770b\u5411\u753b\u9762\u5916\u7684\u660e\u786e\u65b9\u5411', False),
    ('closed', '\u95ed\u773c\uff08\u60c5\u7eea\u8868\u8fbe\uff09', False),
    ('down', '\u4f4e\u5934\u770b\u5730\u9762', True),
    ('wandering', '\u773c\u795e\u98d8\u5ffd\u6ca1\u6709\u843d\u70b9', True),
]

# \u88c1\u5207\u4f4d\u7f6e: (\u952e, \u8bf4\u660e, \u662f\u5426\u88c1\u5728\u5173\u8282)
CROP = [
    ('thigh', '\u5927\u817f\u4e2d\u6bb5', False),
    ('upper_arm', '\u4e0a\u81c2\u4e2d\u6bb5', False),
    ('waist', '\u8170\u90e8', False),
    ('full', '\u5168\u8eab\u5165\u753b\u4e0d\u88c1', False),
    ('wrist', '\u624b\u8155\uff08\u5173\u8282\uff09', True),
    ('elbow', '\u624b\u8098\uff08\u5173\u8282\uff09', True),
    ('knee', '\u819d\u76d6\uff08\u5173\u8282\uff09', True),
    ('ankle', '\u811a\u8e1d\uff08\u5173\u8282\uff09', True),
]


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def _f(shot, key):
    v = shot.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ValueError('%s \u5fc5\u987b\u662f\u6570\u5b57\uff0c\u5b9e\u4e3a %s' % (key, v))


def _opt(shot, key, table, required=False):
    v = shot.get(key)
    if v is None or v == '':
        if required:
            raise ValueError('\u7f3a\u5c11\u5fc5\u586b\u9879: %s' % key)
        return None
    n = norm(v)
    for row in table:
        if norm(row[0]) == n:
            return row
    raise ValueError('\u672a\u77e5\u7684 %s: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00' % (key, v, '/'.join(r[0] for r in table)))


def pose_check(shot):
    if not isinstance(shot, dict):
        raise ValueError('shots \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
    name = str(shot.get('name') or '\u672a\u547d\u540d').strip()
    lens = _f(shot, 'lens_mm')
    turn = _f(shot, 'body_turn_deg')
    shoulder = _f(shot, 'shoulder_angle_deg')
    headroom = _f(shot, 'headroom')
    weight = shot.get('weight_leg')
    arm = shot.get('arm_triangle')
    chin = shot.get('chin_forward')
    breathe = shot.get('exhaled')
    crop = _opt(shot, 'crop_at', CROP)
    eye = _opt(shot, 'eye_direction', EYE)
    hand = _opt(shot, 'hand_pose', HAND_POSE)

    issues = []
    misses = []

    # \u4e25\u91cd\u9879 1\uff1a\u7126\u6bb5
    if lens is None:
        misses.append('\u955c\u5934\u7b49\u6548\u7126\u8ddd')
    else:
        if lens < TOL['lens_min']:
            issues.append({
                'sev': 3, 'item': '\u955c\u5934\u7126\u8ddd',
                'detail': '\u7b49\u6548 %.0f mm\uff0c\u4f4e\u4e8e %.0f mm' % (lens, TOL['lens_min']),
                'why': '\u5e7f\u89d2\u4f1a\u628a\u79bb\u955c\u5934\u8fd1\u7684\u9f3b\u5b50\u989d\u5934\u653e\u5927\uff0c\u8138\u53d8\u5f62\u3001\u5934\u663e\u5927\uff1b\u6362 2 \u500d\u955c\u6216\u9000\u8fdc\u4e00\u70b9',
            })
        elif lens < TOL['lens_ideal_lo']:
            # 35 \u5230 50mm \u5c5e\u4e8e\u300c\u80fd\u7528\u4f46\u6709\u53d8\u5f62\u98ce\u9669\u300d\uff0c\u4e0d\u4e0a\u5347\u4e3a\u4e25\u91cd\u9879
            issues.append({
                'sev': 2, 'item': '\u955c\u5934\u7126\u8ddd',
                'detail': '\u7b49\u6548 %.0f mm\uff0c\u672a\u8fbe\u63a8\u8350\u7684 %.0f \u5230 %.0f mm'
                          % (lens, TOL['lens_ideal_lo'], TOL['lens_ideal_hi']),
                'why': '\u7126\u6bb5\u504f\u5e7f\uff0c\u8fb9\u7f18\u4ecd\u6709\u53d8\u5f62\u98ce\u9669\uff0c\u4eba\u50cf\u4f18\u5148\u7528 2 \u500d\u955c\u6216\u9000\u8fdc\u62cd\u6444',
            })

    # \u4e25\u91cd\u9879 2\uff1a\u88c1\u5728\u5173\u8282
    if crop is None:
        misses.append('\u88c1\u5207\u4f4d\u7f6e')
    elif crop[2]:
        issues.append({
            'sev': 3, 'item': '\u88c1\u5207\u4f4d\u7f6e',
            'detail': '\u88c1\u5728%s' % crop[1],
            'why': '\u88c1\u5728\u5173\u8282\u4e0a\u770b\u8d77\u6765\u50cf\u88ab\u622a\u80a2\uff1b\u6539\u88c1\u5927\u817f\u4e2d\u6bb5\u3001\u4e0a\u81c2\u4e2d\u6bb5\u6216\u8170\u90e8\uff0c\u8981\u4e48\u5c31\u5168\u8eab\u5165\u753b',
        })

    # \u4e25\u91cd\u9879 3\uff1a\u624b\u7684\u4f4d\u7f6e
    if hand is None:
        if shot.get('hand_pose') is None:
            misses.append('\u624b\u7684\u4f4d\u7f6e')
        else:
            issues.append({
                'sev': 3, 'item': '\u624b\u7684\u4f4d\u7f6e',
                'detail': '\u6ca1\u6709\u5b89\u6392\u624b\u7684\u52a8\u4f5c',
                'why': '\u624b\u5782\u5728\u4e24\u4fa7\u8d34\u7740\u8eab\u4f53\uff0c\u662f\u300c\u4e0d\u77e5\u9053\u5f80\u54ea\u653e\u300d\u6700\u5178\u578b\u7684\u753b\u9762\uff1b'
                       '\u76f4\u63a5\u7ed9\u5177\u4f53\u52a8\u4f5c\uff1a\u53c9\u8170\u3001\u63d2\u515c\u3001\u62ff\u676f\u5b50',
            })
    else:
        if norm(hand[0]) == 'pocket' and shot.get('thumb_out') is False:
            issues.append({
                'sev': 2, 'item': '\u624b\u7684\u4f4d\u7f6e',
                'detail': '\u63d2\u515c\u4f46\u6ca1\u9732\u62c7\u6307',
                'why': '\u6574\u53ea\u624b\u585e\u8fdb\u515c\u91cc\u4f1a\u628a\u624b\u81c2\u622a\u65ad\uff0c\u9732\u51fa\u62c7\u6307\u80fd\u8ba9\u624b\u81c2\u7ebf\u6761\u5b8c\u6574',
            })

    # \u4e25\u91cd\u9879 4\uff1a\u4e0b\u5df4
    if chin is None:
        misses.append('\u4e0b\u5df4\u662f\u5426\u524d\u4f38')
    elif not chin:
        issues.append({
            'sev': 3, 'item': '\u4e0b\u5df4',
            'detail': '\u4e0b\u5df4\u672a\u524d\u4f38',
            'why': '\u4e0b\u5df4\u56de\u6536\u4f1a\u6324\u51fa\u53cc\u4e0b\u5df4\u3001\u8116\u5b50\u6d88\u5931\u3001\u8138\u663e\u5927\uff1b\u8981\u8bf4\u300c\u4e0b\u5df4\u5f80\u524d\u4e00\u70b9\u70b9\uff0c\u5934\u7565\u4f4e\u300d',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u91cd\u5fc3\u817f
    if weight is None:
        misses.append('\u91cd\u5fc3\u817f')
    elif not weight:
        issues.append({
            'sev': 2, 'item': '\u91cd\u5fc3\u817f',
            'detail': '\u91cd\u5fc3\u5e73\u5206\u4e24\u811a',
            'why': '\u91cd\u5fc3\u5e73\u5206\u8eab\u4f53\u5c31\u50f5\u3001\u80ef\u90e8\u6b63\u3001\u817f\u4e0d\u663e\u957f\uff1b\u628a\u91cd\u5fc3\u538b\u5728\u540e\u817f\uff0c\u524d\u811a\u811a\u5c16\u70b9\u5730',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u624b\u81c2\u4e09\u89d2
    if arm is None:
        misses.append('\u624b\u81c2\u4e09\u89d2')
    elif not arm:
        issues.append({
            'sev': 2, 'item': '\u624b\u81c2\u4e09\u89d2',
            'detail': '\u624b\u81c2\u8d34\u7740\u8eaf\u5e72',
            'why': '\u624b\u81c2\u4e0e\u8eab\u4f53\u4e4b\u95f4\u6ca1\u7a7a\u9699\uff0c\u624b\u81c2\u88ab\u538b\u6241\u663e\u7c97\u3001\u8170\u663e\u5bbd\uff1b\u624b\u53c9\u8170\u628a\u624b\u8098\u5411\u540e\u6491\u5f00',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u8f6c\u4f53
    if turn is None:
        misses.append('\u8f6c\u4f53\u89d2\u5ea6')
    elif not TOL['turn_min'] <= turn <= TOL['turn_max']:
        why = ('\u5b8c\u5168\u6b63\u5bf9\u955c\u5934\u6700\u663e\u5bbd\uff0c\u80a9\u5bbd\u5168\u5c55\u5f00'
               if turn < TOL['turn_min'] else '\u8f6c\u5230\u63a5\u8fd1 90 \u5ea6\u8eab\u4f53\u592a\u8584\uff0c\u5931\u53bb\u4f53\u79ef\u611f')
        issues.append({
            'sev': 2, 'item': '\u8f6c\u4f53\u89d2\u5ea6',
            'detail': '\u8f6c\u4f53 %.0f \u5ea6\uff0c\u5408\u683c\u533a\u95f4 %.0f \u5230 %.0f \u5ea6'
                      % (turn, TOL['turn_min'], TOL['turn_max']),
            'why': why,
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u80a9\u7ebf
    if shoulder is None:
        misses.append('\u80a9\u7ebf\u89d2\u5ea6')
    elif not TOL['shoulder_min'] <= shoulder <= TOL['shoulder_max']:
        issues.append({
            'sev': 2, 'item': '\u80a9\u7ebf\u89d2\u5ea6',
            'detail': '\u80a9\u7ebf %.0f \u5ea6\uff0c\u5408\u683c\u533a\u95f4 %.0f \u5230 %.0f \u5ea6'
                      % (shoulder, TOL['shoulder_min'], TOL['shoulder_max']),
            'why': '\u80a9\u7ebf\u5b8c\u5168\u6c34\u5e73\u50cf\u8bc1\u4ef6\u7167\uff0c\u659c 5 \u5230 30 \u5ea6\u624d\u6709\u52a8\u611f',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u773c\u795e
    if eye is None:
        misses.append('\u773c\u795e\u65b9\u5411')
    elif eye[2]:
        issues.append({
            'sev': 2, 'item': '\u773c\u795e',
            'detail': '%s\uff0c\u5c5e\u4e8e\u773c\u795e\u6da3\u6563' % eye[1],
            'why': '\u773c\u795e\u6ca1\u6709\u843d\u70b9\u4f1a\u8ba9\u7167\u7247\u5931\u53bb\u7126\u70b9\uff1b\u8981\u4e48\u770b\u955c\u5934\uff0c\u8981\u4e48\u770b\u5411\u753b\u9762\u5916\u7684\u660e\u786e\u65b9\u5411',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u5934\u9876\u7559\u767d
    if headroom is not None:
        if not TOL['headroom_min'] <= headroom <= TOL['headroom_max']:
            why = ('\u7559\u5f97\u592a\u5c11\u4f1a\u9876\u5f97\u538b\u6291\u3001\u50cf\u88ab\u88c1\u6389\u989d\u5934'
                   if headroom < TOL['headroom_min'] else '\u7559\u592a\u591a\u4eba\u663e\u5c0f\u3001\u753b\u9762\u677e\u6563')
            issues.append({
                'sev': 2, 'item': '\u5934\u9876\u7559\u767d',
                'detail': '\u7559\u767d %.2f\uff0c\u5408\u683c\u533a\u95f4 %.2f \u5230 %.2f'
                          % (headroom, TOL['headroom_min'], TOL['headroom_max']),
                'why': why,
            })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u547c\u6c14
    if breathe is False:
        issues.append({
            'sev': 2, 'item': '\u547c\u5438',
            'detail': '\u618b\u6c14\u62cd\u6444',
            'why': '\u618b\u6c14\u4f1a\u8ba9\u80a9\u8180\u4e0a\u63d0\u3001\u8116\u5b50\u53d8\u77ed\uff1b\u6309\u5feb\u95e8\u524d\u558a\u4e00\u58f0\u300c\u547c\u6c14\u300d',
        })

    issues.sort(key=lambda r: -r['sev'])

    if any(i['sev'] == 3 for i in issues):
        level = '\u6446\u59ff\u6709\u660e\u663e\u95ee\u9898'
    elif issues:
        level = '\u6709\u53ef\u6539\u8fdb\u9879'
    elif misses:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u6446\u59ff\u89c4\u8303'

    return {
        'name': name, 'issues': issues, 'misses': misses, 'level': level,
        'lens': lens, 'turn': turn, 'shoulder': shoulder, 'headroom': headroom,
        'crop': crop[1] if crop else None, 'eye': eye[1] if eye else None,
        'hand': hand[1] if hand else None,
    }


def calc(data):
    shots = data.get('shots')
    if shots is None:
        raise ValueError('\u8f93\u5165\u7f3a\u5c11 shots \u5217\u8868')
    if not isinstance(shots, list) or not shots:
        raise ValueError('shots \u5fc5\u987b\u662f\u975e\u7a7a\u5217\u8868')
    rows = [pose_check(s) for s in shots]
    n_bad = len([r for r in rows if r['level'] == '\u6446\u59ff\u6709\u660e\u663e\u95ee\u9898'])
    n_mid = len([r for r in rows if r['level'] == '\u6709\u53ef\u6539\u8fdb\u9879'])
    n_unk = len([r for r in rows if r['level'] == '\u5f85\u786e\u8ba4'])
    if n_bad:
        overall = '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u4eba\u50cf'
    elif n_mid:
        overall = '\u5b58\u5728\u53ef\u6539\u8fdb\u7684\u4eba\u50cf'
    elif n_unk:
        overall = '\u5f85\u786e\u8ba4'
    else:
        overall = '\u5168\u90e8\u6446\u59ff\u89c4\u8303'

    def _sev(r):
        return max([i['sev'] for i in r['issues']], default=0)

    order = sorted(rows, key=lambda r: (-_sev(r), -len(r['issues']), r['name']))
    return {
        'overall': overall, 'rows': rows,
        'n_bad': n_bad, 'n_mid': n_mid, 'n_unk': n_unk,
        'n_ok': len(rows) - n_bad - n_mid - n_unk,
        'fix_order': [r['name'] for r in order if r['issues']],
        'hand_poses': [{'key': k, 'name': n, 'how': h} for k, n, h in HAND_POSE],
        'eyes': [{'key': k, 'name': n, 'vague': v} for k, n, v in EYE],
        'crops': [{'key': k, 'name': n, 'joint': j} for k, n, j in CROP],
        'tol': dict(TOL),
    }


def render_md(r):
    L = []
    L.append('# \u4eba\u50cf\u6446\u59ff\u81ea\u67e5')
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
    L.append('| \u6446\u59ff\u89c4\u8303 | %d |' % r['n_ok'])
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
        if row['lens'] is not None:
            L.append('- \u955c\u5934\u7b49\u6548\u7126\u8ddd\uff1a%.0f mm' % row['lens'])
        if row['crop']:
            L.append('- \u88c1\u5207\u4f4d\u7f6e\uff1a%s' % row['crop'])
        if row['hand']:
            L.append('- \u624b\u7684\u5b89\u6392\uff1a%s' % row['hand'])
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
    L.append('## \u4e09\u3001\u624b\u7684\u4e94\u79cd\u5b89\u6392')
    L.append('')
    L.append('| \u65b9\u5f0f | \u600e\u4e48\u6446 |')
    L.append('|---|---|')
    for h in r['hand_poses']:
        L.append('| %s | %s |' % (h['name'], h['how']))
    L.append('')
    L.append('## \u56db\u3001\u88c1\u5207\u4f4d\u7f6e')
    L.append('')
    L.append('| \u4f4d\u7f6e | \u662f\u5426\u5173\u8282 |')
    L.append('|---|---|')
    for c in r['crops']:
        L.append('| %s | %s |' % (c['name'], '\u662f\uff0c\u4e0d\u80fd\u88c1' if c['joint'] else '\u53ef\u4ee5\u88c1'))
    L.append('')
    L.append('## \u4e94\u3001\u9608\u503c')
    L.append('')
    L.append('| \u9879\u76ee | \u9608\u503c |')
    L.append('|---|---|')
    L.append('| \u955c\u5934\u7b49\u6548\u7126\u8ddd | \u4e0d\u4f4e\u4e8e %.0f mm\uff0c\u63a8\u8350 %.0f \u5230 %.0f mm |'
             % (r['tol']['lens_min'], r['tol']['lens_ideal_lo'], r['tol']['lens_ideal_hi']))
    L.append('| \u8f6c\u4f53\u89d2\u5ea6 | %.0f \u5230 %.0f \u5ea6 |' % (r['tol']['turn_min'], r['tol']['turn_max']))
    L.append('| \u80a9\u7ebf\u89d2\u5ea6 | %.0f \u5230 %.0f \u5ea6 |' % (r['tol']['shoulder_min'], r['tol']['shoulder_max']))
    L.append('| \u5934\u9876\u7559\u767d | %.2f \u5230 %.2f |' % (r['tol']['headroom_min'], r['tol']['headroom_max']))
    L.append('')
    L.append('## \u516d\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u7528\u7684\u662f 2 \u500d\u955c\u6216\u9000\u8fdc\u62cd\u6444\uff0c\u6ca1\u7528\u4e3b\u6444\u8d34\u8138\u62cd')
    L.append('- [ ] \u88c1\u5207\u4f4d\u7f6e\u4e0d\u5728\u624b\u8155\u3001\u624b\u8098\u3001\u819d\u76d6\u3001\u811a\u8e1d\u4e0a')
    L.append('- [ ] \u624b\u6709\u660e\u786e\u5b89\u6392\uff1a\u53c9\u8170\u3001\u63d2\u515c\u9732\u62c7\u6307\u3001\u62ff\u4e1c\u897f\u3001\u62ac\u624b\u78b0\u8138\u3001\u6276\u5899')
    L.append('- [ ] \u4e0b\u5df4\u5fae\u524d\u4f38\u5e76\u7565\u4f4e\uff0c\u6ca1\u6709\u53cc\u4e0b\u5df4')
    L.append('- [ ] \u91cd\u5fc3\u538b\u5728\u4e00\u6761\u817f\u4e0a\uff0c\u624b\u81c2\u4e0e\u8eaf\u5e72\u6709\u4e09\u89d2\u7a7a\u9699')
    L.append('- [ ] \u6bcf\u62cd\u4e00\u7ec4\u56de\u653e\u4e00\u6b21\uff0c\u653e\u5927\u770b\u773c\u775b\u6709\u6ca1\u6709\u95ed')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    good = {'name': '\u7ad9\u59ff\u534a\u8eab', 'lens_mm': 50, 'weight_leg': True, 'arm_triangle': True,
            'body_turn_deg': 30, 'shoulder_angle_deg': 15, 'chin_forward': True,
            'eye_direction': 'lens', 'headroom': 0.12, 'hand_pose': 'waist',
            'crop_at': 'waist', 'exhaled': True}

    # 1 \u6b63\u4f8b
    r1 = pose_check(good)
    ck(r1['level'] == '\u6446\u59ff\u89c4\u8303', '\u6b63\u4f8b\u5e94\u5224\u6446\u59ff\u89c4\u8303\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['issues'] == [], '\u6b63\u4f8b\u4e0d\u5e94\u6709\u95ee\u9898\u9879\uff0c\u5b9e\u4e3a %s' % r1['issues'])

    # 2 \u53cd\u4f8b\uff1a\u4e3b\u6444\u5e7f\u89d2
    r2 = pose_check(dict(good, lens_mm=24))
    ck(r2['level'] == '\u6446\u59ff\u6709\u660e\u663e\u95ee\u9898', '24mm \u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck(any(i['item'] == '\u955c\u5934\u7126\u8ddd' for i in r2['issues']), '\u5e94\u70b9\u540d\u7126\u6bb5')
    ck(pose_check(dict(good, lens_mm=35))['level'] == '\u6709\u53ef\u6539\u8fdb\u9879',
       '35mm \u8fb9\u754c\u5e94\u5224\u53ef\u6539\u8fdb\u800c\u975e\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % pose_check(dict(good, lens_mm=35))['level'])
    ck(any(i['item'] == '\u955c\u5934\u7126\u8ddd' for i in pose_check(dict(good, lens_mm=40))['issues']),
       '40mm \u672a\u8fbe\u63a8\u8350\u533a\u95f4\u4ecd\u5e94\u63d0\u793a')
    ck(pose_check(dict(good, lens_mm=50))['issues'] == [], '50mm \u5e94\u5408\u683c')
    ck(pose_check(dict(good, lens_mm=135))['issues'] == [], '135mm \u5e94\u5408\u683c')

    # 3 \u53cd\u4f8b\uff1a\u88c1\u5728\u5173\u8282
    for joint in ('wrist', 'elbow', 'knee', 'ankle'):
        r3 = pose_check(dict(good, crop_at=joint))
        ck(r3['level'] == '\u6446\u59ff\u6709\u660e\u663e\u95ee\u9898', '\u88c1\u5728 %s \u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % (joint, r3['level']))
    ck(pose_check(dict(good, crop_at='thigh'))['level'] == '\u6446\u59ff\u89c4\u8303', '\u88c1\u5927\u817f\u4e2d\u6bb5\u5e94\u5408\u683c')
    ck(pose_check(dict(good, crop_at='full'))['level'] == '\u6446\u59ff\u89c4\u8303', '\u5168\u8eab\u5165\u753b\u5e94\u5408\u683c')

    # 4 \u53cd\u4f8b\uff1a\u624b\u65e0\u5904\u5b89\u653e
    r4 = pose_check(dict(good, hand_pose=''))
    ck(r4['level'] == '\u6446\u59ff\u6709\u660e\u663e\u95ee\u9898', '\u624b\u6ca1\u5b89\u6392\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r4['level'])
    ck(any(i['item'] == '\u624b\u7684\u4f4d\u7f6e' for i in r4['issues']), '\u5e94\u70b9\u540d\u624b\u7684\u4f4d\u7f6e')
    r4b = pose_check(dict(good, hand_pose='pocket', thumb_out=False))
    ck(any(i['item'] == '\u624b\u7684\u4f4d\u7f6e' for i in r4b['issues']), '\u63d2\u515c\u4e0d\u9732\u62c7\u6307\u5e94\u63d0\u793a')
    ck(r4b['level'] == '\u6709\u53ef\u6539\u8fdb\u9879', '\u63d2\u515c\u4e0d\u9732\u62c7\u6307\u5e94\u5224\u53ef\u6539\u8fdb\uff0c\u5b9e\u4e3a %s' % r4b['level'])

    # 5 \u53cd\u4f8b\uff1a\u4e0b\u5df4\u4e0d\u524d\u4f38
    r5 = pose_check(dict(good, chin_forward=False))
    ck(r5['level'] == '\u6446\u59ff\u6709\u660e\u663e\u95ee\u9898', '\u4e0b\u5df4\u4e0d\u524d\u4f38\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r5['level'])
    ck(any(i['item'] == '\u4e0b\u5df4' for i in r5['issues']), '\u5e94\u70b9\u540d\u4e0b\u5df4\u9879')

    # 6 \u53cd\u4f8b\uff1a\u6b63\u5bf9\u955c\u5934\u4e0d\u8f6c\u4f53
    r6 = pose_check(dict(good, body_turn_deg=0))
    ck(any(i['item'] == '\u8f6c\u4f53\u89d2\u5ea6' for i in r6['issues']), '\u4e0d\u8f6c\u4f53\u5e94\u63d0\u793a')
    ck(r6['level'] == '\u6709\u53ef\u6539\u8fdb\u9879', '\u4e0d\u8f6c\u4f53\u5e94\u5224\u53ef\u6539\u8fdb\uff0c\u5b9e\u4e3a %s' % r6['level'])
    ck(pose_check(dict(good, body_turn_deg=20))['issues'] == [], '\u8f6c\u4f53 20 \u5ea6\u8fb9\u754c\u5e94\u5408\u683c')
    ck(pose_check(dict(good, body_turn_deg=45))['issues'] == [], '\u8f6c\u4f53 45 \u5ea6\u8fb9\u754c\u5e94\u5408\u683c')
    ck(any(i['item'] == '\u8f6c\u4f53\u89d2\u5ea6' for i in pose_check(dict(good, body_turn_deg=80))['issues']),
       '\u8f6c\u4f53 80 \u5ea6\u5e94\u63d0\u793a\u592a\u8584')

    # 7 \u53cd\u4f8b\uff1a\u624b\u81c2\u8d34\u8eab
    r7 = pose_check(dict(good, arm_triangle=False))
    ck(any(i['item'] == '\u624b\u81c2\u4e09\u89d2' for i in r7['issues']), '\u624b\u81c2\u8d34\u8eab\u5e94\u63d0\u793a')

    # 8 \u53cd\u4f8b\uff1a\u91cd\u5fc3\u5e73\u5206
    r8 = pose_check(dict(good, weight_leg=False))
    ck(any(i['item'] == '\u91cd\u5fc3\u817f' for i in r8['issues']), '\u91cd\u5fc3\u5e73\u5206\u5e94\u63d0\u793a')

    # 9 \u53cd\u4f8b\uff1a\u773c\u795e\u6da3\u6563
    r9 = pose_check(dict(good, eye_direction='down'))
    ck(any(i['item'] == '\u773c\u795e' for i in r9['issues']), '\u4f4e\u5934\u770b\u5730\u5e94\u63d0\u793a\u773c\u795e\u6da3\u6563')
    ck(pose_check(dict(good, eye_direction='wandering'))['level'] == '\u6709\u53ef\u6539\u8fdb\u9879',
       '\u773c\u795e\u98d8\u5ffd\u5e94\u5224\u53ef\u6539\u8fdb')
    ck(pose_check(dict(good, eye_direction='off_axis'))['issues'] == [], '\u770b\u5411\u660e\u786e\u65b9\u5411\u5e94\u5408\u683c')

    # 10 \u53cd\u4f8b\uff1a\u80a9\u7ebf\u6c34\u5e73
    r10 = pose_check(dict(good, shoulder_angle_deg=0))
    ck(any(i['item'] == '\u80a9\u7ebf\u89d2\u5ea6' for i in r10['issues']), '\u80a9\u7ebf\u6c34\u5e73\u5e94\u63d0\u793a')
    ck(pose_check(dict(good, shoulder_angle_deg=5))['issues'] == [], '\u80a9\u7ebf 5 \u5ea6\u8fb9\u754c\u5e94\u5408\u683c')

    # 11 \u53cd\u4f8b\uff1a\u7559\u767d\u8d8a\u754c\u4e0e\u8fb9\u754c\u503c
    ck(any(i['item'] == '\u5934\u9876\u7559\u767d' for i in pose_check(dict(good, headroom=0.30))['issues']),
       '\u7559\u767d 0.30 \u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u5934\u9876\u7559\u767d' for i in pose_check(dict(good, headroom=0.02))['issues']),
       '\u7559\u767d 0.02 \u5e94\u63d0\u793a')
    ck(pose_check(dict(good, headroom=0.05))['issues'] == [], '\u7559\u767d 0.05 \u8fb9\u754c\u5e94\u5408\u683c')
    ck(pose_check(dict(good, headroom=0.20))['issues'] == [], '\u7559\u767d 0.20 \u8fb9\u754c\u5e94\u5408\u683c')

    # 12 \u6392\u5e8f\u65b9\u5411\uff1a\u4e25\u91cd\u9879\u6392\u6700\u524d
    r12 = pose_check(dict(good, lens_mm=24, arm_triangle=False, headroom=0.3))
    ck(r12['issues'][0]['sev'] == 3, '\u4e25\u91cd\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r12['issues'][0]['sev'])
    ck(r12['issues'][0]['item'] == '\u955c\u5934\u7126\u8ddd', '\u9996\u4e2a\u5e94\u662f\u7126\u6bb5\uff0c\u5b9e\u4e3a %s' % r12['issues'][0]['item'])

    # 13 \u5224\u5b9a\u987a\u5e8f\uff1a\u6709\u4e25\u91cd\u9879\u65f6\u4e0d\u56e0\u7f3a\u4fe1\u606f\u5224\u5f85\u786e\u8ba4
    r13 = pose_check({'name': '\u7f3a\u7559\u767d', 'lens_mm': 24, 'chin_forward': True})
    ck(r13['level'] == '\u6446\u59ff\u6709\u660e\u663e\u95ee\u9898', '\u7f3a\u5176\u4ed6\u9879\u4f46\u6709\u4e25\u91cd\u9879\u4e0d\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r13['level'])
    r13b = pose_check({'name': '\u53ea\u586b\u7126\u6bb5', 'lens_mm': 85})
    ck(r13b['level'] == '\u5f85\u786e\u8ba4', '\u53ea\u586b\u7126\u6bb5\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r13b['level'])

    # 14 \u6c47\u603b\u4e0e\u6574\u6539\u987a\u5e8f
    r14 = calc({'shots': [good,
                          dict(good, name='\u5e7f\u89d2\u8138\u53d8\u5f62', lens_mm=24),
                          dict(good, name='\u624b\u81c2\u8d34\u8eab', arm_triangle=False)]})
    ck(r14['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u4eba\u50cf', '\u6709\u4e25\u91cd\u9879\u5e94\u5224\u9700\u8981\u91cd\u62cd\uff0c\u5b9e\u4e3a %s' % r14['overall'])
    ck(r14['n_bad'] == 1, '\u4e25\u91cd\u9879\u5e94\u4e3a 1 \u5f20\uff0c\u5b9e\u4e3a %d' % r14['n_bad'])
    ck(r14['fix_order'][0] == '\u5e7f\u89d2\u8138\u53d8\u5f62', '\u4e25\u91cd\u9879\u5e94\u5148\u6539\uff0c\u5b9e\u4e3a %s' % r14['fix_order'])
    ck(r14['fix_order'][1] == '\u624b\u81c2\u8d34\u8eab', '\u53ef\u6539\u8fdb\u9879\u6392\u5176\u540e\uff0c\u5b9e\u4e3a %s' % r14['fix_order'])

    # 15 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'shots': [dict(good, lens_mm=24)]})
    r15 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r15['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u4eba\u50cf', 'BOM \u5b57\u7b26\u4e32\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r15['overall'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_c2.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'shots': [dict(good, name='\u5e26BOM', crop_at='knee')]}))
    try:
        r15b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r15b['rows'][0]['name'] == '\u5e26BOM', 'BOM \u6587\u4ef6\u9996\u4e2a key \u5e94\u89e3\u6790\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r15b['rows'][0]['name'])
        ck(r15b['n_bad'] == 1, '\u88c1\u5728\u819d\u76d6\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %d' % r15b['n_bad'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 16 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({}, '\u7f3a shots'),
        ({'shots': []}, 'shots \u7a7a\u5217\u8868'),
        ({'shots': [{'lens_mm': 'abc'}]}, '\u7126\u6bb5\u975e\u6570\u5b57'),
        ({'shots': [dict(good, crop_at='\u811a\u540e\u8ddf')]}, '\u672a\u77e5\u88c1\u5207\u4f4d\u7f6e'),
        ({'shots': [dict(good, eye_direction='\u659c\u773c\u770b\u4eba')]}, '\u672a\u77e5\u773c\u795e\u65b9\u5411'),
        ({'shots': [dict(good, hand_pose='\u63d2\u8170')]}, '\u672a\u77e5\u624b\u7684\u5b89\u6392'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b16 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 17 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r14)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u9010\u5f20\u5224\u5b9a', '\u624b\u7684\u4e94\u79cd\u5b89\u6392', '\u88c1\u5207\u4f4d\u7f6e', '\u9608\u503c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(HAND_POSE) == 5, '\u624b\u7684\u5b89\u6392\u5e94 5 \u79cd')
    ck(len([c for c in CROP if c[2]]) == 4, '\u5173\u8282\u88c1\u5207\u4f4d\u7f6e\u5e94 4 \u4e2a')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u6b63\u4f8b/\u5e7f\u89d2\u7126\u6bb5\u53cd\u4f8b\u4e0e\u8fb9\u754c/\u5173\u8282\u88c1\u5207\u53cd\u4f8b/\u624b\u65e0\u5904\u5b89\u653e\u53cd\u4f8b/'
        '\u4e0b\u5df4\u53cd\u4f8b/\u8f6c\u4f53\u4e0e\u8fb9\u754c/\u624b\u81c2\u8d34\u8eab/\u91cd\u5fc3\u5e73\u5206/\u773c\u795e\u6da3\u6563/\u80a9\u7ebf/\u7559\u767d\u8fb9\u754c/\u4e25\u91cd\u9879\u6392\u5e8f/'
        '\u5224\u5b9a\u987a\u5e8f/\u6c47\u603b\u6574\u6539\u987a\u5e8f/BOM\u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u4eba\u50cf\u6446\u59ff\u81ea\u67e5')
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
