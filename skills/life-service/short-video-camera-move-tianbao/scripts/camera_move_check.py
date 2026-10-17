# -*- coding: utf-8 -*-
"""\u77ed\u89c6\u9891\u8fd0\u955c\u6838\u67e5\uff1a\u6309\u8d77\u5e45\u3001\u8fd0\u955c\u6bb5\u3001\u843d\u5e45\u4e09\u6bb5\u7ed3\u6784\u6838\u67e5\u6bcf\u4e2a\u955c\u5934\uff0c\u5e76\u6838\u8fd0\u955c\u79cd\u7c7b\u4e0e\u8282\u594f\u3002

\u7528\u6cd5:
  python camera_move_check.py --file shots.json [--out result.md] [--format json]
  python camera_move_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u8fd0\u955c\u624b\u6cd5: (\u952e, \u4e2d\u6587\u540d, \u753b\u9762\u6548\u679c, \u9002\u7528\u5185\u5bb9, \u5e38\u89c1\u9519\u8bef, \u8fd0\u955c\u6bb5\u4e0b\u9650)
MOVES = [
    ('push', '\u63a8', '\u753b\u9762\u9010\u6e10\u9760\u8fd1\u4e3b\u4f53\uff0c\u6ce8\u610f\u529b\u6536\u7d27', '\u5f00\u573a\u5f15\u5165\u3001\u5f3a\u8c03\u7ec6\u8282\u3001\u60c5\u7eea\u9012\u8fdb',
     '\u63a8\u5f97\u592a\u5feb\u663e\u5f97\u6025\u8e81\uff1b\u63a8\u5230\u5e95\u6ca1\u505c\u4f4f', 0.8),
    ('pull', '\u62c9', '\u753b\u9762\u9010\u6e10\u8fdc\u79bb\uff0c\u4ea4\u4ee3\u73af\u5883', '\u7ed3\u5c3e\u6536\u675f\u3001\u63ed\u793a\u573a\u666f\u3001\u8f6c\u573a',
     '\u62c9\u51fa\u53bb\u9732\u51fa\u7a7f\u5e2e\u7684\u8fb9\u89d2', 0.8),
    ('pan', '\u6447', '\u955c\u5934\u5de6\u53f3\u8f6c\u52a8\uff0c\u6a2a\u5411\u626b\u8fc7', '\u5c55\u793a\u6a2a\u5411\u7a7a\u95f4\u3001\u8ddf\u968f\u6a2a\u5411\u8fd0\u52a8',
     '\u6447\u8fc7\u5934\u6765\u56de\u627e\uff1b\u901f\u5ea6\u5ffd\u5feb\u5ffd\u6162', 0.5),
    ('tilt', '\u4fef\u4ef0', '\u955c\u5934\u4e0a\u4e0b\u8f6c\u52a8', '\u5c55\u793a\u9ad8\u5ea6\u3001\u4ece\u811a\u5230\u5934\u4ecb\u7ecd\u4eba\u7269',
     '\u4ef0\u62cd\u5230\u9876\u5168\u662f\u5929\u7a7a', 0.5),
    ('truck', '\u6a2a\u79fb', '\u673a\u8eab\u6574\u4f53\u5de6\u53f3\u5e73\u79fb', '\u8ddf\u968f\u5e76\u6392\u884c\u8d70\u3001\u5c55\u793a\u4fa7\u9762\u5c42\u6b21',
     '\u5e73\u79fb\u65f6\u8ddd\u79bb\u5ffd\u8fdc\u5ffd\u8fd1', 0.5),
    ('follow', '\u8ddf\u62cd', '\u8ddf\u7740\u8fd0\u52a8\u4e3b\u4f53\u540c\u901f\u79fb\u52a8', '\u8d70\u8def\u3001\u8dd1\u6b65\u3001\u9a91\u884c',
     '\u8ddf\u5f97\u592a\u8fd1\u4e3b\u4f53\u51fa\u753b', 0.5),
    ('pedestal', '\u5347\u964d', '\u673a\u8eab\u5782\u76f4\u5347\u9ad8\u6216\u964d\u4f4e', '\u5c55\u793a\u9ad8\u5ea6\u5c42\u6b21\u3001\u4ece\u4f4e\u5904\u63ed\u793a\u573a\u666f',
     '\u5347\u964d\u901f\u5ea6\u4e0d\u5747', 0.5),
    ('arc', '\u73af\u7ed5', '\u56f4\u7ed5\u4e3b\u4f53\u8f6c', '\u5c55\u793a\u4ea7\u54c1\u3001\u7a81\u51fa\u4eba\u7269',
     '\u8f6c\u592a\u5feb\u89c2\u4f17\u53d1\u6655\uff1b\u7ed5\u4e0d\u5230\u4e00\u534a\u5c31\u505c', 0.5),
    ('static', '\u56fa\u5b9a', '\u955c\u5934\u4e0d\u52a8', '\u7a7f\u63d2\u5728\u8fd0\u955c\u4e4b\u95f4\u505a\u547c\u5438\u70b9',
     '\u5168\u7247\u6ca1\u6709\u56fa\u5b9a\u955c\u5934\u4f1a\u8ba9\u89c2\u4f17\u75b2\u52b3', 0.0),
]

# \u9608\u503c
TOL = {
    'shot_min': 1.5,        # \u5355\u4e2a\u8fd0\u955c\u955c\u5934\u7684\u6700\u77ed\u65f6\u957f
    'static_head': 0.5,     # \u8d77\u5e45\u6700\u77ed\u65f6\u957f
    'static_tail': 0.5,     # \u843d\u5e45\u6700\u77ed\u65f6\u957f
    'move_min': 0.5,        # \u8fd0\u955c\u6bb5\u6700\u77ed\u65f6\u957f
    'arc_shot_min': 2.0,    # \u73af\u7ed5\u955c\u5934\u6700\u77ed\u603b\u65f6\u957f
    'kinds_max': 3,         # \u4e00\u4e2a\u7247\u5b50\u5141\u8bb8\u7684\u8fd0\u955c\u79cd\u7c7b\u4e0a\u9650
    'repeat_max': 3,        # \u8fde\u7eed\u540c\u7c7b\u578b\u8fd0\u955c\u7684\u5141\u8bb8\u4e2a\u6570
    'long_video': 20.0,     # \u9700\u8981\u7a7f\u63d2\u56fa\u5b9a\u955c\u5934\u7684\u7247\u957f\u95e8\u69db
    'arc_half': 0.6,        # \u73af\u7ed5\u81f3\u5c11\u8f6c\u8fc7\u7684\u5708\u6570\u6bd4\u4f8b
}

# \u8fd0\u955c\u76ee\u7684\u6e05\u5355: (\u952e, \u4e2d\u6587\u540d, \u63a8\u8350\u624b\u6cd5)
PURPOSES = [
    ('intro', '\u5f15\u5165\u4e3b\u4f53\uff0c\u628a\u6ce8\u610f\u529b\u6536\u8fdb\u6765', '\u63a8'),
    ('context', '\u4ea4\u4ee3\u73af\u5883\uff0c\u5c55\u793a\u4e3b\u4f53\u5728\u54ea', '\u62c9\u3001\u6447'),
    ('detail', '\u5f3a\u8c03\u67d0\u4e2a\u7ec6\u8282', '\u63a8\uff08\u6162\u63a8\uff09'),
    ('follow_action', '\u8ddf\u968f\u6b63\u5728\u8fd0\u52a8\u7684\u4e3b\u4f53', '\u8ddf\u62cd\u3001\u6a2a\u79fb'),
    ('height', '\u5c55\u793a\u9ad8\u5ea6\u6216\u5c42\u6b21', '\u4fef\u4ef0\u3001\u5347\u964d'),
    ('product', '\u5c55\u793a\u4ea7\u54c1\u5168\u8c8c', '\u73af\u7ed5'),
    ('emotion', '\u60c5\u7eea\u9012\u8fdb\u6216\u6536\u675f', '\u63a8\u3001\u62c9'),
    ('transition', '\u8f6c\u573a', '\u62c9\u3001\u6447'),
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
    if f < 0:
        raise ValueError('%s \u4e0d\u80fd\u4e3a\u8d1f\u6570\uff0c\u5b9e\u4e3a %s' % (key, v))
    return f


def _row(table, val, label):
    if val is None or val == '':
        return None
    n = norm(val)
    for r in table:
        if norm(r[0]) == n:
            return r
    raise ValueError('\u672a\u77e5\u7684 %s: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00' % (label, val, '/'.join(r[0] for r in table)))


def shot_check(shot):
    if not isinstance(shot, dict):
        raise ValueError('shots \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
    name = str(shot.get('name') or '\u672a\u547d\u540d').strip()
    move = _row(MOVES, shot.get('move'), 'move')
    if move is None:
        raise ValueError('\u7f3a\u5c11\u5fc5\u586b\u9879: move')
    dur = _f(shot, 'duration_s')
    head = _f(shot, 'start_static_s')
    tail = _f(shot, 'end_static_s')
    speed = norm(shot.get('speed') or '')
    purpose = _row(PURPOSES, shot.get('purpose'), 'purpose')
    arc_turn = _f(shot, 'arc_turn_ratio')

    issues = []
    misses = []

    # \u56fa\u5b9a\u955c\u5934\uff1a\u53ea\u505a\u8282\u594f\u5c42\u9762\u7684\u68c0\u67e5\uff0c\u4e0d\u505a\u4e09\u6bb5\u7ed3\u6784\u68c0\u67e5
    if move[0] == 'static':
        if dur is None:
            misses.append('\u955c\u5934\u65f6\u957f')
        elif dur < TOL['static_head']:
            issues.append({
                'sev': 2, 'item': '\u955c\u5934\u65f6\u957f',
                'detail': '\u56fa\u5b9a\u955c\u5934 %.2f \u79d2\uff0c\u77ed\u4e8e %.1f \u79d2' % (dur, TOL['static_head']),
                'why': '\u56fa\u5b9a\u955c\u5934\u592a\u77ed\u8d77\u4e0d\u5230\u547c\u5438\u70b9\u7684\u4f5c\u7528\uff0c\u89c2\u4f17\u8fd8\u6ca1\u770b\u6e05\u5c31\u5207\u8d70\u4e86',
            })
        return {'name': name, 'move': move[1], 'level': _level(issues, misses),
                'issues': issues, 'misses': misses, 'duration': dur,
                'head': None, 'tail': None, 'move_span': None, 'purpose': None}

    # \u4e25\u91cd\u9879 1\uff1a\u955c\u5934\u603b\u65f6\u957f
    if dur is None:
        misses.append('\u955c\u5934\u65f6\u957f')
    elif dur < TOL['shot_min']:
        issues.append({
            'sev': 3, 'item': '\u955c\u5934\u65f6\u957f',
            'detail': '%.2f \u79d2\uff0c\u77ed\u4e8e %.1f \u79d2' % (dur, TOL['shot_min']),
            'why': '\u8fd0\u955c\u955c\u5934\u77ed\u4e8e 1.5 \u79d2\uff0c\u8d77\u5e45\u8fd0\u955c\u6bb5\u843d\u5e45\u585e\u4e0d\u4e0b\uff0c\u8fd0\u955c\u5fc5\u7136\u663e\u5f97\u62bd\u6410',
        })

    # \u4e25\u91cd\u9879 2\uff1a\u8d77\u5e45
    if head is None:
        misses.append('\u8d77\u5e45')
    elif head < TOL['static_head']:
        issues.append({
            'sev': 3, 'item': '\u8d77\u5e45',
            'detail': '\u8d77\u5e45 %.2f \u79d2\uff0c\u77ed\u4e8e %.1f \u79d2' % (head, TOL['static_head']),
            'why': '\u6ca1\u6709\u8d77\u5e45\uff0c\u526a\u8f91\u63a5\u7247\u65f6\u627e\u4e0d\u5230\u5e72\u51c0\u7684\u5165\u70b9\uff0c\u89c2\u4f17\u4e5f\u6765\u4e0d\u53ca\u770b\u6e05\u753b\u9762',
        })

    # \u4e25\u91cd\u9879 3\uff1a\u843d\u5e45
    if tail is None:
        misses.append('\u843d\u5e45')
    elif tail < TOL['static_tail']:
        issues.append({
            'sev': 3, 'item': '\u843d\u5e45',
            'detail': '\u843d\u5e45 %.2f \u79d2\uff0c\u77ed\u4e8e %.1f \u79d2' % (tail, TOL['static_tail']),
            'why': '\u6ca1\u6709\u843d\u5e45\u5c31\u6ca1\u6709\u5e72\u51c0\u7684\u5207\u70b9\uff0c\u63a5\u4e0a\u53bb\u5c31\u662f\u6296\u4e00\u4e0b\u63a5\u6296\u4e00\u4e0b\uff0c\u89c2\u4f17\u4f1a\u89c9\u5f97\u6655',
        })

    # \u8fd0\u955c\u6bb5\u65f6\u957f
    span = None
    if dur is not None and head is not None and tail is not None:
        span = dur - head - tail
        if span < 0:
            issues.append({
                'sev': 3, 'item': '\u65f6\u957f\u77db\u76fe',
                'detail': '\u8d77\u5e45 %.2f \u52a0\u843d\u5e45 %.2f \u5df2\u8d85\u8fc7\u603b\u65f6\u957f %.2f \u79d2' % (head, tail, dur),
                'why': '\u4e09\u6bb5\u65f6\u957f\u81ea\u76f8\u77db\u76fe\uff0c\u8bf4\u660e\u8ba1\u65f6\u6709\u8bef\uff0c\u9700\u8981\u91cd\u65b0\u6838\u5bf9',
            })
        elif span < TOL['move_min'] - 1e-9:
            issues.append({
                'sev': 3, 'item': '\u8fd0\u955c\u6bb5',
                'detail': '\u8fd0\u955c\u6bb5 %.2f \u79d2\uff0c\u77ed\u4e8e %.1f \u79d2' % (span, TOL['move_min']),
                'why': '\u8fd0\u955c\u8fc7\u7a0b\u592a\u77ed\u663e\u5f97\u62bd\u6410\uff1b\u52a0\u957f\u955c\u5934\u603b\u65f6\u957f\u6216\u7f29\u77ed\u8d77\u5e45\u843d\u5e45\u4e4b\u5916\u7684\u505c\u987f',
            })
        elif move[5] > TOL['move_min'] and span < move[5] - 1e-9:
            issues.append({
                'sev': 2, 'item': '\u8fd0\u955c\u6bb5',
                'detail': '%s\u955c\u7684\u8fd0\u955c\u6bb5 %.2f \u79d2\uff0c\u77ed\u4e8e\u8be5\u624b\u6cd5\u5efa\u8bae\u7684 %.1f \u79d2' % (move[1], span, move[5]),
                'why': '\u63a8\u62c9\u9700\u8981\u66f4\u957f\u7684\u8fd0\u52a8\u8fc7\u7a0b\u624d\u4e0d\u663e\u5f97\u6025\u8e81\uff0c\u52a0\u957f\u5230 0.8 \u79d2\u4ee5\u4e0a',
            })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u53d8\u901f
    if speed == '':
        misses.append('\u8fd0\u955c\u901f\u5ea6')
    elif speed != 'const':
        issues.append({
            'sev': 2, 'item': '\u8fd0\u955c\u901f\u5ea6',
            'detail': '\u8fd0\u955c\u901f\u5ea6\u4e0d\u5747\u5300',
            'why': '\u5ffd\u5feb\u5ffd\u6162\u662f\u65b0\u624b\u6700\u660e\u663e\u7684\u7279\u70b9\uff1b\u8d77\u624b\u7f13\u3001\u4e2d\u95f4\u5300\u3001\u6536\u624b\u7f13',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u6ca1\u6709\u76ee\u7684
    if purpose is None:
        if shot.get('purpose') is None:
            misses.append('\u8fd0\u955c\u76ee\u7684')
        else:
            issues.append({
                'sev': 2, 'item': '\u8fd0\u955c\u76ee\u7684',
                'detail': '\u8bf4\u4e0d\u51fa\u8fd9\u4e2a\u8fd0\u955c\u4e3a\u4e86\u4ec0\u4e48',
                'why': '\u6ca1\u6709\u76ee\u7684\u7684\u8fd0\u955c\u662f\u7eaf\u7cb9\u7684\u5e72\u6270\uff1b\u5bf9\u7167\u76ee\u7684\u6e05\u5355\u9009\u4e00\u4e2a',
            })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u73af\u7ed5\u8981\u6c42
    if move[0] == 'arc':
        if dur is not None and dur < TOL['arc_shot_min']:
            issues.append({
                'sev': 2, 'item': '\u73af\u7ed5\u65f6\u957f',
                'detail': '\u73af\u7ed5\u955c\u5934 %.2f \u79d2\uff0c\u77ed\u4e8e %.1f \u79d2' % (dur, TOL['arc_shot_min']),
                'why': '\u73af\u7ed5\u662f\u8f6c\u901f\u6700\u6162\u7684\u8fd0\u955c\uff0c\u955c\u5934\u592a\u77ed\u53ea\u80fd\u8f6c\u4e00\u5c0f\u6bb5\uff0c\u770b\u7740\u50cf\u624b\u6296',
            })
        if arc_turn is not None and arc_turn < TOL['arc_half']:
            issues.append({
                'sev': 2, 'item': '\u73af\u7ed5\u5e45\u5ea6',
                'detail': '\u53ea\u8f6c\u4e86 %.0f%% \u5708' % (arc_turn * 100 - 50),
                'why': '\u73af\u7ed5\u53ea\u8f6c\u56db\u5206\u4e4b\u4e00\u5708\u5c31\u5207\uff0c\u770b\u7740\u50cf\u6643\u52a8\uff1b\u8981\u4e48\u8f6c\u5b8c\u6574\uff0c\u8981\u4e48\u6362\u624b\u6cd5',
            })

    return {
        'name': name, 'move': move[1], 'level': _level(issues, misses),
        'issues': issues, 'misses': misses, 'duration': dur,
        'head': head, 'tail': tail, 'move_span': span,
        'purpose': purpose[1] if purpose else None,
    }


def _level(issues, misses):
    if any(i['sev'] == 3 for i in issues):
        return '\u8fd0\u955c\u6709\u660e\u663e\u95ee\u9898'
    if issues:
        return '\u6709\u53ef\u6539\u8fdb\u9879'
    if misses:
        return '\u5f85\u786e\u8ba4'
    return '\u8fd0\u955c\u89c4\u8303'


def calc(data):
    shots = data.get('shots')
    if shots is None:
        raise ValueError('\u8f93\u5165\u7f3a\u5c11 shots \u5217\u8868')
    if not isinstance(shots, list) or not shots:
        raise ValueError('shots \u5fc5\u987b\u662f\u975e\u7a7a\u5217\u8868')
    rows = [shot_check(s) for s in shots]

    total = _f(data, 'total_duration_s') or sum(r['duration'] or 0 for r in rows)
    global_issues = []

    # \u8fd0\u955c\u79cd\u7c7b\u4e0d\u8d85\u8fc7 3 \u79cd
    kinds = sorted(set(norm(s.get('move')) for s in shots if norm(s.get('move')) != 'static'))
    if len(kinds) > TOL['kinds_max']:
        global_issues.append({
            'sev': 2, 'item': '\u8fd0\u955c\u79cd\u7c7b',
            'detail': '\u5171\u7528\u4e86 %d \u79cd\u8fd0\u955c\uff08%s\uff09\uff0c\u8d85\u8fc7 %d \u79cd'
                      % (len(kinds), '\u3001'.join(_mname(k) for k in kinds), TOL['kinds_max']),
            'why': '\u4e00\u4e2a\u7247\u5b50\u8fd0\u955c\u79cd\u7c7b\u8d85\u8fc7 3 \u79cd\uff0c\u98ce\u683c\u5c31\u4e0d\u7edf\u4e00\uff0c\u89c2\u4f17\u4f1a\u89c9\u5f97\u6742\u4e71',
        })

    # \u4e0d\u8981\u8fde\u7eed 3 \u4e2a\u4ee5\u4e0a\u540c\u7c7b\u578b\u8fd0\u955c
    seq = [norm(s.get('move')) for s in shots if norm(s.get('move')) != 'static']
    run, worst = 1, 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            run += 1
            worst = max(worst, run)
        else:
            run = 1
    if worst >= TOL['repeat_max']:
        global_issues.append({
            'sev': 2, 'item': '\u8fd0\u955c\u91cd\u590d',
            'detail': '\u5b58\u5728\u8fde\u7eed %d \u4e2a\u540c\u7c7b\u578b\u8fd0\u955c\u955c\u5934' % worst,
            'why': '\u8fde\u7eed\u91cd\u590d\u540c\u4e00\u79cd\u8fd0\u955c\u4f1a\u8ba9\u89c2\u4f17\u75b2\u52b3\uff0c\u4e5f\u4f1a\u663e\u5f97\u5077\u61d2\uff1b\u4e2d\u95f4\u6362\u624b\u6cd5\u6216\u63d2\u56fa\u5b9a\u955c\u5934',
        })

    # \u957f\u7247\u5fc5\u987b\u6709\u56fa\u5b9a\u955c\u5934\u7a7f\u63d2
    n_static = len([s for s in shots if norm(s.get('move')) == 'static'])
    if total and total > TOL['long_video'] and n_static == 0 and len(shots) > 1:
        global_issues.append({
            'sev': 2, 'item': '\u7f3a\u5c11\u56fa\u5b9a\u955c\u5934',
            'detail': '\u5168\u7247 %.0f \u79d2\u5168\u90e8\u662f\u8fd0\u955c\u955c\u5934\uff0c\u6ca1\u6709\u56fa\u5b9a\u955c\u5934' % total,
            'why': '20 \u79d2\u4ee5\u4e0a\u7684\u7247\u5b50\u5168\u7a0b\u90fd\u5728\u52a8\u89c2\u4f17\u4f1a\u6655\uff1b\u8fd0\u955c\u4e4b\u95f4\u8981\u63d2\u56fa\u5b9a\u955c\u5934\u505a\u547c\u5438\u70b9',
        })

    global_issues.sort(key=lambda r: -r['sev'])

    n_bad = len([r for r in rows if r['level'] == '\u8fd0\u955c\u6709\u660e\u663e\u95ee\u9898'])
    n_mid = len([r for r in rows if r['level'] == '\u6709\u53ef\u6539\u8fdb\u9879'])
    n_unk = len([r for r in rows if r['level'] == '\u5f85\u786e\u8ba4'])
    if n_bad:
        overall = '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u8fd0\u955c\u955c\u5934'
    elif n_mid or global_issues:
        overall = '\u5b58\u5728\u53ef\u6539\u8fdb\u7684\u8fd0\u955c'
    elif n_unk:
        overall = '\u5f85\u786e\u8ba4'
    else:
        overall = '\u5168\u90e8\u8fd0\u955c\u89c4\u8303'

    def _sev(r):
        return max([i['sev'] for i in r['issues']], default=0)

    order = sorted(rows, key=lambda r: (-_sev(r), -len(r['issues']), r['name']))
    return {
        'overall': overall, 'rows': rows, 'global_issues': global_issues,
        'n_bad': n_bad, 'n_mid': n_mid, 'n_unk': n_unk,
        'n_ok': len(rows) - n_bad - n_mid - n_unk,
        'n_static': n_static, 'total': total, 'kinds': [_mname(k) for k in kinds],
        'fix_order': [r['name'] for r in order if r['issues']],
        'moves': [{'key': k, 'name': n, 'effect': e, 'use': u, 'wrong': w, 'span_min': s}
                  for k, n, e, u, w, s in MOVES],
        'purposes': [{'key': k, 'name': n, 'move': m} for k, n, m in PURPOSES],
        'tol': dict(TOL),
    }


def _mname(key):
    for k, n, _, _, _, _ in MOVES:
        if k == key:
            return n
    return key


def render_md(r):
    L = []
    L.append('# \u77ed\u89c6\u9891\u8fd0\u955c\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['overall'])
    L.append('')
    L.append('| \u7c7b\u522b | \u4e2a\u6570 |')
    L.append('|---|---|')
    L.append('| \u9700\u8981\u91cd\u62cd | %d |' % r['n_bad'])
    L.append('| \u53ef\u6539\u8fdb | %d |' % r['n_mid'])
    L.append('| \u5f85\u786e\u8ba4 | %d |' % r['n_unk'])
    L.append('| \u8fd0\u955c\u89c4\u8303 | %d |' % r['n_ok'])
    L.append('')
    L.append('- \u7247\u957f\uff1a%.1f \u79d2\uff0c\u5176\u4e2d\u56fa\u5b9a\u955c\u5934 %d \u4e2a\uff0c\u7528\u5230\u7684\u8fd0\u955c\uff1a%s'
             % (r['total'], r['n_static'], '\u3001'.join(r['kinds']) or '\u65e0'))
    L.append('')
    if r['global_issues']:
        L.append('## \u4e8c\u3001\u6574\u7247\u5c42\u9762\u7684\u95ee\u9898')
        L.append('')
        L.append('| \u4e25\u91cd\u5ea6 | \u9879\u76ee | \u95ee\u9898 | \u4e3a\u4ec0\u4e48\u8981\u5728\u610f |')
        L.append('|---|---|---|---|')
        for i in r['global_issues']:
            L.append('| %s | %s | %s | %s |'
                     % ('\u4e25\u91cd' if i['sev'] == 3 else '\u53ef\u6539\u8fdb', i['item'], i['detail'], i['why']))
        L.append('')
    if r['fix_order']:
        L.append('\u6574\u6539\u987a\u5e8f\uff08\u4e25\u91cd\u5ea6\u9ad8\u7684\u5148\u6539\uff09\uff1a%s' % '\u3001'.join(r['fix_order']))
        L.append('')
    L.append('## \u4e09\u3001\u9010\u955c\u5934\u5224\u5b9a')
    L.append('')
    for row in r['rows']:
        L.append('### %s\uff08%s\uff09' % (row['name'], row['move']))
        L.append('')
        L.append('- \u5224\u5b9a\uff1a**%s**' % row['level'])
        if row['duration'] is not None:
            L.append('- \u603b\u65f6\u957f\uff1a%.2f \u79d2' % row['duration'])
        if row['head'] is not None:
            L.append('- \u8d77\u5e45\uff1a%.2f \u79d2' % row['head'])
        if row['move_span'] is not None:
            L.append('- \u8fd0\u955c\u6bb5\uff1a%.2f \u79d2' % row['move_span'])
        if row['tail'] is not None:
            L.append('- \u843d\u5e45\uff1a%.2f \u79d2' % row['tail'])
        if row['purpose']:
            L.append('- \u76ee\u7684\uff1a%s' % row['purpose'])
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
    L.append('## \u56db\u3001\u516b\u79cd\u8fd0\u955c\u624b\u6cd5')
    L.append('')
    L.append('| \u624b\u6cd5 | \u753b\u9762\u6548\u679c | \u9002\u7528\u5185\u5bb9 | \u5e38\u89c1\u9519\u8bef | \u8fd0\u955c\u6bb5\u4e0b\u9650 |')
    L.append('|---|---|---|---|---|')
    for m in r['moves']:
        L.append('| %s | %s | %s | %s | %s |'
                 % (m['name'], m['effect'], m['use'], m['wrong'],
                    '\u4e0d\u9002\u7528' if m['span_min'] == 0 else '%.1f \u79d2' % m['span_min']))
    L.append('')
    L.append('## \u4e94\u3001\u8fd0\u955c\u76ee\u7684\u6e05\u5355')
    L.append('')
    L.append('| \u76ee\u7684 | \u63a8\u8350\u624b\u6cd5 |')
    L.append('|---|---|')
    for p in r['purposes']:
        L.append('| %s | %s |' % (p['name'], p['move']))
    L.append('')
    L.append('## \u516d\u3001\u9608\u503c')
    L.append('')
    L.append('| \u9879\u76ee | \u9608\u503c |')
    L.append('|---|---|')
    L.append('| \u8fd0\u955c\u955c\u5934\u603b\u65f6\u957f | \u4e0d\u77ed\u4e8e %.1f \u79d2 |' % r['tol']['shot_min'])
    L.append('| \u8d77\u5e45 / \u843d\u5e45 | \u5404\u4e0d\u77ed\u4e8e %.1f \u79d2 |' % r['tol']['static_head'])
    L.append('| \u8fd0\u955c\u6bb5 | \u4e0d\u77ed\u4e8e %.1f \u79d2\uff08\u63a8\u62c9 %.1f \u79d2\uff09|' % (r['tol']['move_min'], 0.8))
    L.append('| \u73af\u7ed5\u955c\u5934 | \u4e0d\u77ed\u4e8e %.1f \u79d2 |' % r['tol']['arc_shot_min'])
    L.append('| \u8fd0\u955c\u79cd\u7c7b | \u4e0d\u8d85\u8fc7 %d \u79cd |' % r['tol']['kinds_max'])
    L.append('| \u8fde\u7eed\u540c\u7c7b\u578b | \u5c11\u4e8e %d \u4e2a |' % r['tol']['repeat_max'])
    L.append('')
    L.append('## \u4e03\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u6bcf\u4e2a\u8fd0\u955c\u955c\u5934\u90fd\u6709\u8d77\u5e45\u4e0e\u843d\u5e45\uff0c\u5404\u4e0d\u5c11\u4e8e 0.5 \u79d2')
    L.append('- [ ] \u8fd0\u955c\u8fc7\u7a0b\u662f\u5300\u901f\u7684\uff0c\u8d77\u624b\u7f13\u3001\u6536\u624b\u7f13')
    L.append('- [ ] \u6bcf\u4e2a\u8fd0\u955c\u90fd\u80fd\u8bf4\u51fa\u76ee\u7684')
    L.append('- [ ] \u4e00\u4e2a\u7247\u5b50\u8fd0\u955c\u79cd\u7c7b\u4e0d\u8d85\u8fc7 3 \u79cd')
    L.append('- [ ] \u957f\u7247\u6709\u56fa\u5b9a\u955c\u5934\u7a7f\u63d2\u505a\u547c\u5438\u70b9')
    L.append('- [ ] \u62cd\u6444\u65f6\u4eba\u8eab\u4e0e\u8bbe\u5907\u5b89\u5168\uff0c\u6ca1\u6709\u5728\u79fb\u52a8\u4e2d\u64cd\u4f5c\u8bbe\u5907')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    good = {'name': '\u5f00\u573a\u63a8\u955c', 'move': 'push', 'duration_s': 3.0,
            'start_static_s': 0.6, 'end_static_s': 0.8, 'speed': 'const',
            'purpose': 'intro'}

    # 1 \u6b63\u4f8b
    r1 = shot_check(good)
    ck(r1['level'] == '\u8fd0\u955c\u89c4\u8303', '\u6b63\u4f8b\u5e94\u5224\u8fd0\u955c\u89c4\u8303\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['issues'] == [], '\u6b63\u4f8b\u4e0d\u5e94\u6709\u95ee\u9898\u9879\uff0c\u5b9e\u4e3a %s' % r1['issues'])
    ck(abs(r1['move_span'] - 1.6) < 1e-9, '\u8fd0\u955c\u6bb5\u5e94\u4e3a 1.6 \u79d2\uff0c\u5b9e\u4e3a %s' % r1['move_span'])

    # 2 \u53cd\u4f8b\uff1a\u7f3a\u8d77\u5e45
    r2 = shot_check(dict(good, start_static_s=0.2))
    ck(r2['level'] == '\u8fd0\u955c\u6709\u660e\u663e\u95ee\u9898', '\u7f3a\u8d77\u5e45\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck(any(i['item'] == '\u8d77\u5e45' for i in r2['issues']), '\u5e94\u70b9\u540d\u8d77\u5e45')
    ck(shot_check(dict(good, start_static_s=0.5))['issues'] == [], '\u8d77\u5e45 0.5 \u79d2\u8fb9\u754c\u5e94\u5408\u683c')

    # 3 \u53cd\u4f8b\uff1a\u7f3a\u843d\u5e45
    r3 = shot_check(dict(good, end_static_s=0.1))
    ck(any(i['item'] == '\u843d\u5e45' for i in r3['issues']), '\u7f3a\u843d\u5e45\u5e94\u5224\u4e25\u91cd')
    ck(shot_check(dict(good, end_static_s=0.5))['issues'] == [], '\u843d\u5e45 0.5 \u79d2\u8fb9\u754c\u5e94\u5408\u683c')

    # 4 \u53cd\u4f8b\uff1a\u955c\u5934\u592a\u77ed
    r4 = shot_check(dict(good, duration_s=1.0, start_static_s=0.3, end_static_s=0.3))
    ck(r4['level'] == '\u8fd0\u955c\u6709\u660e\u663e\u95ee\u9898', '\u955c\u5934 1 \u79d2\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r4['level'])
    ck(any(i['item'] == '\u955c\u5934\u65f6\u957f' for i in r4['issues']), '\u5e94\u70b9\u540d\u955c\u5934\u65f6\u957f')
    r4b = shot_check(dict(good, duration_s=1.5, start_static_s=0.5, end_static_s=0.5))
    ck(not any(i['sev'] == 3 for i in r4b['issues']), '1.5 \u79d2\u8fb9\u754c\u4e0d\u5e94\u6709\u4e25\u91cd\u9879\uff0c\u5b9e\u4e3a %s' % r4b['issues'])
    ck(any(i['item'] == '\u8fd0\u955c\u6bb5' for i in r4b['issues']),
       '\u63a8\u955c\u8fd0\u955c\u6bb5 0.5 \u79d2\u4ecd\u5e94\u63d0\u793a\u504f\u77ed')

    # 5 \u53cd\u4f8b\uff1a\u8fd0\u955c\u6bb5\u592a\u77ed
    r5 = shot_check(dict(good, duration_s=2.0, start_static_s=0.8, end_static_s=0.8))
    ck(r5['move_span'] < 0.5, '\u8fd0\u955c\u6bb5\u5e94\u4e0d\u8db3 0.5 \u79d2')
    ck(any(i['item'] == '\u8fd0\u955c\u6bb5' for i in r5['issues']), '\u8fd0\u955c\u6bb5\u592a\u77ed\u5e94\u5224\u4e25\u91cd')

    # 6 \u53cd\u4f8b\uff1a\u63a8\u62c9\u8fd0\u955c\u6bb5\u4e0d\u8db3 0.8 \u79d2
    r6 = shot_check(dict(good, duration_s=2.2, start_static_s=0.8, end_static_s=0.8))
    ck(abs(r6['move_span'] - 0.6) < 1e-9, '\u8fd0\u955c\u6bb5\u5e94\u4e3a 0.6 \u79d2')
    ck(any(i['item'] == '\u8fd0\u955c\u6bb5' and i['sev'] == 2 for i in r6['issues']),
       '\u63a8\u955c\u8fd0\u955c\u6bb5 0.6 \u79d2\u5e94\u5224\u53ef\u6539\u8fdb')
    ck(shot_check(dict(good, duration_s=2.4, start_static_s=0.8, end_static_s=0.8))['issues'] == [],
       '\u63a8\u955c\u8fd0\u955c\u6bb5 0.8 \u79d2\u8fb9\u754c\u5e94\u5408\u683c')
    ck(shot_check(dict(good, move='pan', duration_s=2.2, start_static_s=0.8,
                       end_static_s=0.8))['issues'] == [], '\u6447\u955c\u8fd0\u955c\u6bb5 0.6 \u79d2\u5e94\u5408\u683c')

    # 7 \u53cd\u4f8b\uff1a\u65f6\u957f\u81ea\u76f8\u77db\u76fe
    r7 = shot_check(dict(good, duration_s=1.0, start_static_s=0.8, end_static_s=0.8))
    ck(any(i['item'] == '\u65f6\u957f\u77db\u76fe' for i in r7['issues']), '\u8d77\u843d\u5e45\u8d85\u8fc7\u603b\u65f6\u957f\u5e94\u5224\u4e25\u91cd')

    # 8 \u53cd\u4f8b\uff1a\u53d8\u901f
    r8 = shot_check(dict(good, speed='variable'))
    ck(any(i['item'] == '\u8fd0\u955c\u901f\u5ea6' for i in r8['issues']), '\u53d8\u901f\u5e94\u63d0\u793a')
    ck(r8['level'] == '\u6709\u53ef\u6539\u8fdb\u9879', '\u53d8\u901f\u5e94\u5224\u53ef\u6539\u8fdb\uff0c\u5b9e\u4e3a %s' % r8['level'])

    # 9 \u53cd\u4f8b\uff1a\u6ca1\u8bf4\u76ee\u7684
    r9 = shot_check(dict(good, purpose=''))
    ck(any(i['item'] == '\u8fd0\u955c\u76ee\u7684' for i in r9['issues']), '\u6ca1\u8bf4\u76ee\u7684\u5e94\u63d0\u793a')

    # 10 \u53cd\u4f8b\uff1a\u73af\u7ed5\u592a\u77ed\u3001\u8f6c\u4e0d\u5230\u4e00\u534a
    r10 = shot_check(dict(good, move='arc', purpose='product', duration_s=1.5,
                          start_static_s=0.5, end_static_s=0.5, arc_turn_ratio=0.25))
    ck(any(i['item'] == '\u73af\u7ed5\u65f6\u957f' for i in r10['issues']), '\u73af\u7ed5 1.5 \u79d2\u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u73af\u7ed5\u5e45\u5ea6' for i in r10['issues']), '\u53ea\u8f6c 0.25 \u5708\u5e94\u63d0\u793a')
    ck(not any(i['item'] in ('\u73af\u7ed5\u65f6\u957f', '\u73af\u7ed5\u5e45\u5ea6')
               for i in shot_check(dict(good, move='arc', purpose='product', duration_s=3.0,
                                        start_static_s=0.6, end_static_s=0.8,
                                        arc_turn_ratio=1.0))['issues']),
       '\u73af\u7ed5 3 \u79d2\u8f6c\u6ee1\u4e00\u5708\u5e94\u5408\u683c')

    # 11 \u56fa\u5b9a\u955c\u5934
    r11 = shot_check({'name': '\u547c\u5438\u70b9', 'move': 'static', 'duration_s': 2.0})
    ck(r11['level'] == '\u8fd0\u955c\u89c4\u8303', '\u56fa\u5b9a\u955c\u5934 2 \u79d2\u5e94\u5408\u683c\uff0c\u5b9e\u4e3a %s' % r11['level'])
    ck(any(i['item'] == '\u955c\u5934\u65f6\u957f'
           for i in shot_check({'name': '\u592a\u77ed\u56fa\u5b9a', 'move': 'static', 'duration_s': 0.3})['issues']),
       '\u56fa\u5b9a\u955c\u5934 0.3 \u79d2\u5e94\u63d0\u793a')

    # 12 \u6392\u5e8f\u65b9\u5411\uff1a\u4e25\u91cd\u9879\u6392\u6700\u524d
    r12 = shot_check(dict(good, start_static_s=0.1, speed='variable'))
    ck(r12['issues'][0]['sev'] == 3, '\u4e25\u91cd\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r12['issues'][0]['sev'])
    ck(r12['issues'][0]['item'] == '\u8d77\u5e45', '\u9996\u4e2a\u5e94\u662f\u8d77\u5e45\uff0c\u5b9e\u4e3a %s' % r12['issues'][0]['item'])

    # 13 \u5224\u5b9a\u987a\u5e8f\uff1a\u6709\u4e25\u91cd\u9879\u65f6\u4e0d\u56e0\u7f3a\u4fe1\u606f\u5224\u5f85\u786e\u8ba4
    r13 = shot_check({'name': '\u53ea\u586b\u65f6\u957f', 'move': 'push', 'duration_s': 1.0})
    ck(r13['level'] == '\u8fd0\u955c\u6709\u660e\u663e\u95ee\u9898', '\u7f3a\u5176\u4ed6\u9879\u4f46\u6709\u4e25\u91cd\u9879\u4e0d\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r13['level'])
    r13b = shot_check({'name': '\u53ea\u586b\u624b\u6cd5', 'move': 'push', 'duration_s': 3.0,
                       'start_static_s': 0.6, 'end_static_s': 0.8})
    ck(r13b['level'] == '\u5f85\u786e\u8ba4', '\u672a\u586b\u901f\u5ea6\u4e0e\u76ee\u7684\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r13b['level'])

    # 14 \u6574\u7247\uff1a\u8fd0\u955c\u79cd\u7c7b\u8d85\u8fc7 3 \u79cd
    many = [dict(good, move=m, purpose='intro') for m in ('push', 'pull', 'pan', 'arc', 'tilt')]
    r14 = calc({'shots': many})
    ck(any(i['item'] == '\u8fd0\u955c\u79cd\u7c7b' for i in r14['global_issues']), '5 \u79cd\u8fd0\u955c\u5e94\u63d0\u793a\u98ce\u683c\u4e0d\u7edf\u4e00')
    ck(len(r14['kinds']) == 5, '\u5e94\u7edf\u8ba1\u51fa 5 \u79cd\uff0c\u5b9e\u4e3a %s' % r14['kinds'])
    r14b = calc({'shots': [dict(good, move=m, purpose='intro') for m in ('push', 'pull', 'pan')]})
    ck(not any(i['item'] == '\u8fd0\u955c\u79cd\u7c7b' for i in r14b['global_issues']), '3 \u79cd\u8fd0\u955c\u5e94\u5408\u683c')

    # 15 \u6574\u7247\uff1a\u8fde\u7eed 3 \u4e2a\u540c\u7c7b\u578b
    r15 = calc({'shots': [dict(good, name='\u63a81'), dict(good, name='\u63a82'), dict(good, name='\u63a83')]})
    ck(any(i['item'] == '\u8fd0\u955c\u91cd\u590d' for i in r15['global_issues']), '\u8fde\u7eed 3 \u4e2a\u63a8\u955c\u5e94\u63d0\u793a')
    r15b = calc({'shots': [dict(good, name='\u63a81'), dict(good, name='\u63a82'),
                           dict(good, name='\u62c91', move='pull')]})
    ck(not any(i['item'] == '\u8fd0\u955c\u91cd\u590d' for i in r15b['global_issues']), '\u8fde\u7eed 2 \u4e2a\u540c\u7c7b\u578b\u5e94\u5408\u683c')

    # 16 \u6574\u7247\uff1a\u957f\u7247\u6ca1\u6709\u56fa\u5b9a\u955c\u5934
    r16 = calc({'shots': [dict(good, name='\u955c%d' % i, move=m, purpose='intro')
                          for i, m in enumerate(('push', 'pull', 'pan'))],
                'total_duration_s': 30})
    ck(any(i['item'] == '\u7f3a\u5c11\u56fa\u5b9a\u955c\u5934' for i in r16['global_issues']), '30 \u79d2\u5168\u8fd0\u955c\u5e94\u63d0\u793a')
    r16b = calc({'shots': [dict(good, name='\u63a81'), dict(good, name='\u62c91', move='pull'),
                           {'name': '\u547c\u5438\u70b9', 'move': 'static', 'duration_s': 2.0}],
                 'total_duration_s': 30})
    ck(not any(i['item'] == '\u7f3a\u5c11\u56fa\u5b9a\u955c\u5934' for i in r16b['global_issues']),
       '\u6709\u56fa\u5b9a\u955c\u5934\u7a7f\u63d2\u5e94\u5408\u683c')

    # 17 \u6c47\u603b\u4e0e\u6574\u6539\u987a\u5e8f
    r17 = calc({'shots': [good,
                          dict(good, name='\u7f3a\u8d77\u5e45', start_static_s=0.1),
                          dict(good, name='\u53d8\u901f', speed='variable')]})
    ck(r17['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u8fd0\u955c\u955c\u5934', '\u6709\u4e25\u91cd\u9879\u5e94\u5224\u9700\u8981\u91cd\u62cd\uff0c\u5b9e\u4e3a %s' % r17['overall'])
    ck(r17['n_bad'] == 1, '\u4e25\u91cd\u9879\u5e94\u4e3a 1 \u4e2a\uff0c\u5b9e\u4e3a %d' % r17['n_bad'])
    ck(r17['fix_order'][0] == '\u7f3a\u8d77\u5e45', '\u4e25\u91cd\u9879\u5e94\u5148\u6539\uff0c\u5b9e\u4e3a %s' % r17['fix_order'])
    ck(r17['fix_order'][1] == '\u53d8\u901f', '\u53ef\u6539\u8fdb\u9879\u6392\u5176\u540e\uff0c\u5b9e\u4e3a %s' % r17['fix_order'])

    # 18 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'shots': [dict(good, start_static_s=0.1)]})
    r18 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r18['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u8fd0\u955c\u955c\u5934', 'BOM \u5b57\u7b26\u4e32\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r18['overall'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_c6.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'shots': [dict(good, name='\u5e26BOM', duration_s=1.0)]}))
    try:
        r18b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r18b['rows'][0]['name'] == '\u5e26BOM', 'BOM \u6587\u4ef6\u9996\u4e2a key \u5e94\u89e3\u6790\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r18b['rows'][0]['name'])
        ck(r18b['n_bad'] == 1, '\u955c\u5934 1 \u79d2\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %d' % r18b['n_bad'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 19 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({}, '\u7f3a shots'),
        ({'shots': []}, 'shots \u7a7a\u5217\u8868'),
        ({'shots': [{'duration_s': 3}]}, '\u7f3a move'),
        ({'shots': [dict(good, move='\u7529\u955c')]}, '\u672a\u77e5\u8fd0\u955c'),
        ({'shots': [dict(good, purpose='\u968f\u4fbf\u52a8\u52a8')]}, '\u672a\u77e5\u76ee\u7684'),
        ({'shots': [dict(good, duration_s='abc')]}, '\u65f6\u957f\u975e\u6570\u5b57'),
        ({'shots': [dict(good, start_static_s=-1)]}, '\u8d77\u5e45\u4e3a\u8d1f'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b19 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 20 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r17)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u9010\u955c\u5934\u5224\u5b9a', '\u516b\u79cd\u8fd0\u955c\u624b\u6cd5', '\u8fd0\u955c\u76ee\u7684\u6e05\u5355', '\u9608\u503c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(MOVES) == 9, '\u8fd0\u955c\u624b\u6cd5\u5e94 9 \u79cd\uff08\u542b\u56fa\u5b9a\uff09')
    ck(len(PURPOSES) >= 6, '\u76ee\u7684\u6e05\u5355\u81f3\u5c11 6 \u6761')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u6b63\u4f8b\u4e0e\u8fd0\u955c\u6bb5\u8ba1\u7b97/\u7f3a\u8d77\u5e45\u53cd\u4f8b\u4e0e\u8fb9\u754c/\u7f3a\u843d\u5e45\u53cd\u4f8b\u4e0e\u8fb9\u754c/'
        '\u955c\u5934\u592a\u77ed\u53cd\u4f8b/\u8fd0\u955c\u6bb5\u592a\u77ed\u53cd\u4f8b/\u63a8\u62c90.8\u79d2\u8fb9\u754c/\u65f6\u957f\u77db\u76fe\u53cd\u4f8b/\u53d8\u901f\u53cd\u4f8b/\u65e0\u76ee\u7684\u53cd\u4f8b/'
        '\u73af\u7ed5\u65f6\u957f\u4e0e\u5e45\u5ea6\u53cd\u4f8b/\u56fa\u5b9a\u955c\u5934/\u4e25\u91cd\u9879\u6392\u5e8f/\u5224\u5b9a\u987a\u5e8f/\u8fd0\u955c\u79cd\u7c7b/\u8fde\u7eed\u91cd\u590d/\u7f3a\u56fa\u5b9a\u955c\u5934/'
        '\u6c47\u603b\u6574\u6539\u987a\u5e8f/BOM\u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u77ed\u89c6\u9891\u8fd0\u955c\u6838\u67e5')
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
