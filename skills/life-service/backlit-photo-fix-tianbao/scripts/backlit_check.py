# -*- coding: utf-8 -*-
"""\u9006\u5149\u62cd\u7167\u6838\u67e5\uff1a\u5224\u5b9a\u8865\u5149\u4e0e\u526a\u5f71\u4e24\u6761\u8def\u7ebf\uff0c\u6838\u6d4b\u5149\u65b9\u5f0f\u3001\u66dd\u5149\u9501\u5b9a\u3001\u8865\u5149\u8ddd\u79bb\u4e0e\u7729\u5149\u63a7\u5236\u3002

\u7528\u6cd5:
  python backlit_check.py --file backlit.json [--out result.md] [--format json]
  python backlit_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u8def\u7ebf: (\u952e, \u4e2d\u6587\u540d, \u76ee\u6807)
MODES = [
    ('portrait', '\u8865\u5149\u4eba\u50cf', '\u4eba\u8138\u4e0e\u80cc\u666f\u90fd\u6709\u5c42\u6b21'),
    ('silhouette', '\u526a\u5f71', '\u4e3b\u4f53\u6210\u4e3a\u7eaf\u9ed1\u8f6e\u5ed3\uff0c\u80cc\u666f\u6f02\u4eae'),
]

# \u5149\u4f4d: (\u952e, \u4e2d\u6587\u540d, \u662f\u5426\u9006\u5149)
LIGHTS = [
    ('back', '\u9006\u5149\uff08\u5149\u6e90\u5728\u4e3b\u4f53\u540e\u65b9\uff09', True),
    ('side_back', '\u4fa7\u9006\u5149\uff08\u5149\u6e90\u5728\u4fa7\u540e\u65b9 45 \u5ea6\uff09', True),
    ('side', '\u4fa7\u5149', False),
    ('front', '\u987a\u5149', False),
]

# \u6d4b\u5149\u65b9\u5f0f: (\u952e, \u4e2d\u6587\u540d, \u9006\u5149\u4e0b\u662f\u5426\u88ab\u4eae\u80cc\u666f\u5e26\u504f)
METERING = [
    ('spot_face', '\u70b9\u6d4b\u5149\u5bf9\u4eba\u8138', False),
    ('evaluative', '\u8bc4\u4ef7\u6d4b\u5149 / \u77e9\u9635\u6d4b\u5149', True),
    ('center', '\u4e2d\u592e\u91cd\u70b9\u6d4b\u5149', True),
    ('average', '\u5e73\u5747\u6d4b\u5149', True),
    ('spot_bg', '\u70b9\u6d4b\u5149\u5bf9\u80cc\u666f\uff08\u526a\u5f71\u7528\uff09', False),
]

# \u8865\u5149\u65b9\u5f0f: (\u952e, \u4e2d\u6587\u540d, \u53c2\u8003\u6709\u6548\u8ddd\u79bb, \u662f\u5426\u9700\u8981\u5224\u65ad\u8ddd\u79bb)
FILLS = [
    ('reflector', '\u53cd\u5149\u677f', 2.0, True),
    ('flash', '\u95ea\u5149\u706f / \u8865\u5149\u706f', 3.0, True),
    ('continuous', '\u5e38\u4eae\u8865\u5149', 3.0, True),
    ('hdr', 'HDR \u6216\u63d0\u66dd\u5149\u8865\u507f', 99.0, False),
    ('none', '\u4e0d\u8865\u5149', 0.0, False),
]

# \u5149\u6e90\u76f8\u5bf9\u955c\u5934\u7684\u89d2\u5ea6: (\u952e, \u4e2d\u6587\u540d, \u662f\u5426\u76f4\u5c04\u955c\u5934)
ANGLES = [
    ('shielded', '\u5149\u6e90\u88ab\u4e3b\u4f53\u6216\u7269\u4f53\u906e\u6321', False),
    ('side', '\u504f\u79bb\u5149\u6e90 15 \u5230 30 \u5ea6', False),
    ('direct', '\u6b63\u5bf9\u5149\u6e90', True),
]

# \u9608\u503c
TOL = {
    'silhouette_ev_max': -0.5,   # \u526a\u5f71\u8981\u6c42\u7684\u66dd\u5149\u8865\u507f\u4e0a\u9650
    'silhouette_ev_min': -2.0,   # \u526a\u5f71\u66dd\u5149\u8865\u507f\u4e0b\u9650
    'fill_gap_max': 2.0,         # \u4eba\u8138\u6bd4\u80cc\u666f\u6697\u7684\u6321\u6570\u4e0a\u9650
    'fill_gap_min': 1.0,         # \u4eba\u8138\u6bd4\u80cc\u666f\u6697\u7684\u6321\u6570\u4e0b\u9650
}


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
    mode = _row(MODES, shot.get('mode'), 'mode')
    light = _row(LIGHTS, shot.get('light'), 'light')
    meter = _row(METERING, shot.get('metering'), 'metering')
    fill = _row(FILLS, shot.get('fill'), 'fill')
    angle = _row(ANGLES, shot.get('angle_to_sun'), 'angle_to_sun')
    ev = shot.get('ev')
    ev = float(ev) if ev is not None else None
    dist = _f(shot, 'fill_distance_m')
    reach = _f(shot, 'flash_effective_m')
    lock = shot.get('exposure_lock')
    hood = shot.get('lens_hood')
    hdr = shot.get('hdr')
    clip = shot.get('bg_clipped')
    outline = shot.get('outline_clear')
    bg_light = shot.get('bg_has_light')

    issues = []
    misses = []

    if mode is None:
        misses.append('\u62cd\u6444\u8def\u7ebf')
    if light is None:
        misses.append('\u5149\u4f4d')

    # \u975e\u9006\u5149\u573a\u666f\uff1a\u672c\u6280\u80fd\u7684\u9006\u5149\u5224\u5b9a\u4e0d\u9002\u7528\uff0c\u53ea\u63d0\u793a
    if light is not None and not light[2] and mode is not None:
        return {
            'name': name, 'level': '\u4e0d\u9002\u7528\u9006\u5149\u5224\u5b9a', 'issues': [],
            'misses': ['\u5f53\u524d\u5149\u4f4d\u4e3a%s\uff0c\u9006\u5149\u4e13\u9879\u5224\u5b9a\u4e0d\u9002\u7528' % light[1]],
            'mode': mode[1], 'light': light[1], 'ev': ev,
        }

    if mode is not None and mode[0] == 'portrait':
        # \u4e25\u91cd\u9879 1\uff1a\u6d4b\u5149\u65b9\u5f0f\u88ab\u4eae\u80cc\u666f\u5e26\u504f\u4e14\u6ca1\u6709\u8865\u507f\u624b\u6bb5
        if meter is None:
            misses.append('\u6d4b\u5149\u65b9\u5f0f')
        else:
            if meter[2] and fill is not None and fill[0] == 'none' and not hdr:
                issues.append({
                    'sev': 3, 'item': '\u6d4b\u5149\u65b9\u5f0f',
                    'detail': '\u7528\u4e86%s\uff0c\u4e14\u65e2\u6ca1\u8865\u5149\u4e5f\u6ca1\u5f00 HDR' % meter[1],
                    'why': '\u9006\u5149\u65f6\u660e\u4eae\u80cc\u666f\u5360\u636e\u5927\u9762\u79ef\uff0c\u6d4b\u5149\u7cfb\u7edf\u4e3a\u538b\u4f4f\u4eae\u533a\u4f1a\u6574\u4f53\u964d\u66dd\u5149\uff0c'
                           '\u4eba\u8138\u5fc5\u7136\u6b20\u66dd\uff1b\u6539\u6210\u5bf9\u4eba\u8138\u70b9\u6d4b\u5149\uff0c\u6216\u5f00 HDR\u3001\u63d0\u66dd\u5149\u8865\u507f',
                })
            elif meter[2] and meter[0] == 'average':
                issues.append({
                    'sev': 3, 'item': '\u6d4b\u5149\u65b9\u5f0f',
                    'detail': '\u7528\u4e86\u5e73\u5747\u6d4b\u5149',
                    'why': '\u5e73\u5747\u6d4b\u5149\u5728\u9006\u5149\u4e0b\u6700\u4e0d\u53ef\u9760\uff0c\u4eba\u8138\u4f1a\u88ab\u660e\u4eae\u80cc\u666f\u62d6\u9ed1\uff1b'
                           '\u6539\u4e3a\u5bf9\u4eba\u8138\u70b9\u6d4b\u5149\u5e76\u9501\u5b9a\u66dd\u5149',
                })

        # \u4e25\u91cd\u9879 2\uff1a\u65e2\u6ca1\u8865\u5149\u4e5f\u6ca1 HDR
        if fill is None:
            misses.append('\u8865\u5149\u65b9\u5f0f')
        elif fill[0] == 'none' and not hdr:
            issues.append({
                'sev': 3, 'item': '\u8865\u5149',
                'detail': '\u9006\u5149\u4eba\u50cf\u65e2\u6ca1\u8865\u5149\u4e5f\u6ca1\u5f00 HDR',
                'why': '\u8865\u5149\u8def\u7ebf\u4e0b\u4e0d\u8865\u5149\uff0c\u4eba\u8138\u53ea\u80fd\u6b20\u66dd\u6210\u7070\u9ed1\uff1b'
                       '\u7528\u53cd\u5149\u677f\u3001\u95ea\u5149\u706f\u3001\u5e38\u4eae\u8865\u5149\uff0c\u6216\u8005\u81f3\u5c11\u5f00 HDR',
            })

        # \u4e25\u91cd\u9879 3\uff1a\u8865\u5149\u8d85\u51fa\u6709\u6548\u8ddd\u79bb
        if fill is not None and fill[3] and dist is not None:
            limit = reach if (fill[0] == 'flash' and reach) else fill[2]
            if dist > limit:
                issues.append({
                    'sev': 3, 'item': '\u8865\u5149\u8ddd\u79bb',
                    'detail': '%s\u8ddd\u79bb\u4e3a %.1f \u7c73\uff0c\u8d85\u51fa\u6709\u6548\u8ddd\u79bb %.1f \u7c73' % (fill[1], dist, limit),
                    'why': '\u8865\u5149\u8d85\u51fa\u6709\u6548\u8ddd\u79bb\u7b49\u4e8e\u6ca1\u8865\uff0c\u4eba\u8138\u4f9d\u7136\u9ed1\uff1b'
                           '\u8d70\u8fd1\u8865\u5149\u3001\u63d0\u9ad8\u8865\u5149\u529f\u7387\uff0c\u6216\u6539\u7528\u53cd\u5149\u677f\u8fd1\u8ddd\u79bb\u8865',
                })

        # \u53ef\u6539\u8fdb\u9879\uff1a\u66dd\u5149\u9501\u5b9a
        if meter is not None and meter[0] == 'spot_face':
            if lock is None:
                misses.append('\u66dd\u5149\u9501\u5b9a')
            elif not lock:
                issues.append({
                    'sev': 2, 'item': '\u66dd\u5149\u9501\u5b9a',
                    'detail': '\u5bf9\u4eba\u8138\u70b9\u6d4b\u5149\u540e\u6ca1\u6709\u9501\u5b9a\u66dd\u5149',
                    'why': '\u624b\u673a\u591a\u4e3a\u70b9\u54ea\u91cc\u6d4b\u54ea\u91cc\uff0c\u91cd\u65b0\u6784\u56fe\u65f6\u6d4b\u5149\u70b9\u4f1a\u6f02\u79fb\uff0c\u8138\u53c8\u9ed1\u56de\u53bb\uff1b'
                           '\u70b9\u5b8c\u4eba\u8138\u6309\u4e0b\u9501\u5b9a\u518d\u91cd\u65b0\u6784\u56fe',
                })

        # \u53ef\u6539\u8fdb\u9879\uff1a\u906e\u5149\u7f69
        if hood is False:
            issues.append({
                'sev': 2, 'item': '\u7729\u5149\u63a7\u5236',
                'detail': '\u9006\u5149\u4e0b\u6ca1\u6709\u906e\u5149\u63aa\u65bd',
                'why': '\u5149\u6e90\u76f4\u5c04\u955c\u5934\u4f1a\u4ea7\u751f\u7070\u96fe\u4e0e\u5149\u6591\uff1b\u88c5\u906e\u5149\u7f69\uff0c'
                       '\u6216\u7528\u624b\u5728\u955c\u5934\u4e0a\u65b9\u659c\u7740\u6321\uff08\u522b\u8ba9\u624b\u5165\u753b\uff09\uff0c\u6216\u8ba9\u4e3b\u4f53\u6321\u4f4f\u592a\u9633',
            })

        # \u53ef\u6539\u8fdb\u9879\uff1a\u6b63\u5bf9\u5149\u6e90
        if angle is not None and angle[2]:
            issues.append({
                'sev': 2, 'item': '\u673a\u4f4d\u89d2\u5ea6',
                'detail': '\u6b63\u5bf9\u5149\u6e90\u62cd\u6444',
                'why': '\u6b63\u5bf9\u5149\u6e90\u7729\u5149\u6700\u4e25\u91cd\u3001\u753b\u9762\u53d1\u7070\uff1b\u504f 15 \u5230 30 \u5ea6\uff0c'
                       '\u6216\u8ba9\u4e3b\u4f53\u7684\u5934\u3001\u4e00\u68f5\u6811\u6321\u4f4f\u592a\u9633',
            })

        # \u53ef\u6539\u8fdb\u9879\uff1a\u80cc\u666f\u9ad8\u5149\u6ea2\u51fa
        if clip:
            issues.append({
                'sev': 2, 'item': '\u80cc\u666f\u9ad8\u5149',
                'detail': '\u80cc\u666f\u9ad8\u5149\u6ea2\u51fa\uff08\u5929\u7a7a\u6216\u6c34\u9762\u6b7b\u767d\uff09',
                'why': '\u80cc\u666f\u6ea2\u51fa\u4f1a\u8ba9\u753b\u9762\u5931\u53bb\u5c42\u6b21\uff1b\u964d\u4f4e\u66dd\u5149\u8865\u507f\u3001'
                       '\u6362\u89d2\u5ea6\u8ba9\u592a\u9633\u88ab\u906e\u6321\uff0c\u6216\u5e72\u8106\u6539\u8d70\u526a\u5f71\u8def\u7ebf',
            })

        # \u53ef\u6539\u8fdb\u9879\uff1a\u8865\u5149\u91cf
        gap = shot.get('face_vs_bg_stops')
        if gap is not None:
            gap = float(gap)
            if gap > TOL['fill_gap_max']:
                issues.append({
                    'sev': 2, 'item': '\u8865\u5149\u91cf',
                    'detail': '\u4eba\u8138\u6bd4\u80cc\u666f\u6697 %.1f \u6321' % gap,
                    'why': '\u6697\u8d85\u8fc7 2 \u6321\u4eba\u8138\u7ec6\u8282\u5c31\u4e0d\u5bb9\u6613\u6551\u56de\u6765\uff1b\u518d\u8865\u4e00\u70b9\u5149\u6216\u63d0\u4e00\u6321\u66dd\u5149\u8865\u507f',
                })
            elif gap < TOL['fill_gap_min']:
                issues.append({
                    'sev': 2, 'item': '\u8865\u5149\u91cf',
                    'detail': '\u4eba\u8138\u4e0e\u80cc\u666f\u4eae\u5ea6\u5dee\u53ea\u6709 %.1f \u6321' % gap,
                    'why': '\u8865\u8fc7\u5934\u4f1a\u4e22\u6389\u9006\u5149\u6c1b\u56f4\uff0c\u8138\u6bd4\u80cc\u666f\u8fd8\u4eae\u5c31\u50cf\u68da\u62cd\uff1b'
                           '\u8865\u5230\u6bd4\u80cc\u666f\u6697 1 \u5230 2 \u6321\u5c31\u505c',
                })

    elif mode is not None and mode[0] == 'silhouette':
        # \u4e25\u91cd\u9879\uff1a\u6ca1\u538b\u66dd\u5149
        if ev is None:
            misses.append('\u66dd\u5149\u8865\u507f')
        elif ev > TOL['silhouette_ev_max']:
            issues.append({
                'sev': 3, 'item': '\u66dd\u5149\u8865\u507f',
                'detail': '%.1f EV\uff0c\u526a\u5f71\u8981\u6c42\u4e0d\u9ad8\u4e8e %.1f' % (ev, TOL['silhouette_ev_max']),
                'why': '\u526a\u5f71\u7684\u6838\u5fc3\u662f\u8ba9\u4e3b\u4f53\u5f7b\u5e95\u9ed1\u6389\uff1b\u6ca1\u538b\u66dd\u5149\u4f1a\u5f97\u5230\u7070\u8499\u8499\u7684\u4eba\uff0c'
                       '\u65e2\u4e0d\u662f\u4eba\u50cf\u4e5f\u4e0d\u662f\u526a\u5f71\uff0c\u538b\u5230\u8d1f 1 \u5230\u8d1f 2',
            })

        # \u4e25\u91cd\u9879\uff1a\u8f6e\u5ed3\u4e0d\u6e05\u6670
        if outline is False:
            issues.append({
                'sev': 3, 'item': '\u8f6e\u5ed3',
                'detail': '\u4e3b\u4f53\u8f6e\u5ed3\u4e0d\u6e05\u6670',
                'why': '\u526a\u5f71\u9760\u5f62\u72b6\u8bf4\u8bdd\uff1b\u4e0d\u8981\u8ba9\u4e24\u4e2a\u4eba\u7684\u8f6e\u5ed3\u53e0\u5728\u4e00\u8d77\uff0c'
                       '\u4e5f\u4e0d\u8981\u8ba9\u6811\u679d\u6321\u4f4f\u4e3b\u4f53\uff0c\u8ba9\u4eba\u5206\u5f00\u7ad9\u7559\u51fa\u95f4\u9699',
            })

        # \u4e25\u91cd\u9879\uff1a\u80cc\u666f\u6ca1\u6709\u5149
        if bg_light is False:
            issues.append({
                'sev': 3, 'item': '\u80cc\u666f',
                'detail': '\u80cc\u666f\u6ca1\u6709\u5149',
                'why': '\u7eaf\u9ed1\u80cc\u666f\u62cd\u526a\u5f71\u6beb\u65e0\u610f\u4e49\uff1b\u9009\u665a\u971e\u3001\u4eae\u6c34\u9762\u3001\u4eae\u5929\u7a7a\u505a\u80cc\u666f',
            })

        # \u53ef\u6539\u8fdb\u9879\uff1a\u538b\u8fc7\u5934
        if ev is not None and ev < TOL['silhouette_ev_min']:
            issues.append({
                'sev': 2, 'item': '\u66dd\u5149\u8865\u507f',
                'detail': '%.1f EV\uff0c\u4f4e\u4e8e %.1f' % (ev, TOL['silhouette_ev_min']),
                'why': '\u538b\u8fc7\u5934\u8fde\u80cc\u666f\u7684\u5149\u4e5f\u4e00\u8d77\u538b\u6389\uff0c\u526a\u5f71\u5c31\u6ca1\u4e86\u886c\u5e95',
            })

        # \u53ef\u6539\u8fdb\u9879\uff1a\u6b63\u5bf9\u5149\u6e90\u62cd\u526a\u5f71\u4e5f\u4f1a\u6709\u7729\u5149
        if angle is not None and angle[2] and hood is False:
            issues.append({
                'sev': 2, 'item': '\u7729\u5149\u63a7\u5236',
                'detail': '\u6b63\u5bf9\u5149\u6e90\u4e14\u6ca1\u6709\u906e\u5149\u63aa\u65bd',
                'why': '\u62cd\u526a\u5f71\u65f6\u592a\u9633\u5728\u753b\u9762\u91cc\uff0c\u66f4\u6613\u4ea7\u751f\u7070\u96fe\u4e0e\u5149\u6591\uff1b'
                       '\u8ba9\u4e3b\u4f53\u6321\u4f4f\u592a\u9633\u672c\u4f53\uff0c\u6216\u52a0\u906e\u5149\u7f69',
            })

    issues.sort(key=lambda r: -r['sev'])

    if any(i['sev'] == 3 for i in issues):
        level = '\u9006\u5149\u5904\u7406\u6709\u660e\u663e\u95ee\u9898'
    elif issues:
        level = '\u6709\u53ef\u6539\u8fdb\u9879'
    elif misses:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u5904\u7406\u5f97\u5f53'

    return {
        'name': name, 'level': level, 'issues': issues, 'misses': misses,
        'mode': mode[1] if mode else None, 'light': light[1] if light else None,
        'metering': meter[1] if meter else None, 'fill': fill[1] if fill else None,
        'angle': angle[1] if angle else None, 'ev': ev,
    }


def calc(data):
    shots = data.get('shots')
    if shots is None:
        raise ValueError('\u8f93\u5165\u7f3a\u5c11 shots \u5217\u8868')
    if not isinstance(shots, list) or not shots:
        raise ValueError('shots \u5fc5\u987b\u662f\u975e\u7a7a\u5217\u8868')
    rows = [shot_check(s) for s in shots]
    n_bad = len([r for r in rows if r['level'] == '\u9006\u5149\u5904\u7406\u6709\u660e\u663e\u95ee\u9898'])
    n_mid = len([r for r in rows if r['level'] == '\u6709\u53ef\u6539\u8fdb\u9879'])
    n_unk = len([r for r in rows if r['level'] == '\u5f85\u786e\u8ba4'])
    if n_bad:
        overall = '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u9006\u5149\u7167\u7247'
    elif n_mid:
        overall = '\u5b58\u5728\u53ef\u6539\u8fdb\u7684\u9006\u5149\u7167\u7247'
    elif n_unk:
        overall = '\u5f85\u786e\u8ba4'
    else:
        overall = '\u5168\u90e8\u5904\u7406\u5f97\u5f53'

    def _sev(r):
        return max([i['sev'] for i in r['issues']], default=0)

    order = sorted(rows, key=lambda r: (-_sev(r), -len(r['issues']), r['name']))
    return {
        'overall': overall, 'rows': rows,
        'n_bad': n_bad, 'n_mid': n_mid, 'n_unk': n_unk,
        'n_ok': len(rows) - n_bad - n_mid - n_unk,
        'fix_order': [r['name'] for r in order if r['issues']],
        'modes': [{'key': k, 'name': n, 'goal': g} for k, n, g in MODES],
        'lights': [{'key': k, 'name': n, 'backlit': b} for k, n, b in LIGHTS],
        'meterings': [{'key': k, 'name': n, 'biased': b} for k, n, b in METERING],
        'fills': [{'key': k, 'name': n, 'reach': r, 'need_dist': d} for k, n, r, d in FILLS],
        'angles': [{'key': k, 'name': n, 'direct': d} for k, n, d in ANGLES],
        'tol': dict(TOL),
    }


def render_md(r):
    L = []
    L.append('# \u9006\u5149\u62cd\u7167\u6838\u67e5')
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
    L.append('| \u5904\u7406\u5f97\u5f53 | %d |' % r['n_ok'])
    L.append('')
    if r['fix_order']:
        L.append('\u6574\u6539\u987a\u5e8f\uff08\u4e25\u91cd\u5ea6\u9ad8\u7684\u5148\u6539\uff09\uff1a%s' % '\u3001'.join(r['fix_order']))
        L.append('')
    L.append('## \u4e8c\u3001\u4e24\u6761\u8def\u7ebf')
    L.append('')
    L.append('| \u8def\u7ebf | \u76ee\u6807 |')
    L.append('|---|---|')
    for m in r['modes']:
        L.append('| %s | %s |' % (m['name'], m['goal']))
    L.append('')
    L.append('## \u4e09\u3001\u9010\u5f20\u5224\u5b9a')
    L.append('')
    for row in r['rows']:
        L.append('### %s' % row['name'])
        L.append('')
        L.append('- \u5224\u5b9a\uff1a**%s**' % row['level'])
        if row['mode']:
            L.append('- \u8def\u7ebf\uff1a%s' % row['mode'])
        if row['light']:
            L.append('- \u5149\u4f4d\uff1a%s' % row['light'])
        if row['metering']:
            L.append('- \u6d4b\u5149\uff1a%s' % row['metering'])
        if row['fill']:
            L.append('- \u8865\u5149\uff1a%s' % row['fill'])
        if row['angle']:
            L.append('- \u673a\u4f4d\uff1a%s' % row['angle'])
        if row['ev'] is not None:
            L.append('- \u66dd\u5149\u8865\u507f\uff1a%.1f EV' % row['ev'])
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
    L.append('## \u56db\u3001\u6d4b\u5149\u65b9\u5f0f')
    L.append('')
    L.append('| \u65b9\u5f0f | \u9006\u5149\u4e0b\u662f\u5426\u88ab\u4eae\u80cc\u666f\u5e26\u504f |')
    L.append('|---|---|')
    for m in r['meterings']:
        L.append('| %s | %s |' % (m['name'], '\u4f1a' if m['biased'] else '\u4e0d\u4f1a'))
    L.append('')
    L.append('## \u4e94\u3001\u8865\u5149\u65b9\u5f0f\u4e0e\u6709\u6548\u8ddd\u79bb')
    L.append('')
    L.append('| \u65b9\u5f0f | \u53c2\u8003\u6709\u6548\u8ddd\u79bb | \u9700\u6838\u5bf9\u8ddd\u79bb |')
    L.append('|---|---|---|')
    for f in r['fills']:
        L.append('| %s | %s | %s |'
                 % (f['name'], '\u4e0d\u9650' if f['reach'] > 90 else '%.1f \u7c73' % f['reach'],
                    '\u662f' if f['need_dist'] else '\u5426'))
    L.append('')
    L.append('## \u516d\u3001\u9608\u503c')
    L.append('')
    L.append('| \u9879\u76ee | \u9608\u503c |')
    L.append('|---|---|')
    L.append('| \u526a\u5f71\u66dd\u5149\u8865\u507f | \u4e0d\u9ad8\u4e8e %.1f EV\uff0c\u4e0d\u4f4e\u4e8e %.1f EV |'
             % (r['tol']['silhouette_ev_max'], r['tol']['silhouette_ev_min']))
    L.append('| \u8865\u5149\u540e\u4eba\u8138\u4e0e\u80cc\u666f\u4eae\u5ea6\u5dee | %.1f \u5230 %.1f \u6321 |'
             % (r['tol']['fill_gap_min'], r['tol']['fill_gap_max']))
    L.append('')
    L.append('## \u4e03\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5df2\u4e8c\u9009\u4e00\uff1a\u8865\u5149\u4eba\u50cf\u6216\u526a\u5f71\uff0c\u4e0d\u662f\u4e2d\u95f4\u72b6\u6001')
    L.append('- [ ] \u8865\u5149\u8def\u7ebf\u5df2\u5bf9\u4eba\u8138\u70b9\u6d4b\u5149\u5e76\u9501\u5b9a\u66dd\u5149')
    L.append('- [ ] \u8865\u5149\u8ddd\u79bb\u5728\u5668\u6750\u6709\u6548\u8ddd\u79bb\u4e4b\u5185')
    L.append('- [ ] \u6709\u906e\u5149\u63aa\u65bd\uff0c\u6216\u5149\u6e90\u5df2\u88ab\u4e3b\u4f53\u906e\u6321')
    L.append('- [ ] \u526a\u5f71\u8def\u7ebf\u5df2\u538b\u66dd\u5149\u5230\u8d1f 1 \u5230\u8d1f 2\uff0c\u8f6e\u5ed3\u6e05\u6670\u3001\u80cc\u666f\u6709\u5149')
    L.append('- [ ] \u6ca1\u6709\u957f\u65f6\u95f4\u7528\u955c\u5934\u6216\u773c\u775b\u76f4\u5bf9\u5f3a\u5149\u6e90')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    port = {'name': '\u508d\u665a\u4eba\u50cf', 'mode': 'portrait', 'light': 'side_back',
            'metering': 'spot_face', 'exposure_lock': True, 'fill': 'reflector',
            'fill_distance_m': 1.5, 'lens_hood': True, 'angle_to_sun': 'shielded',
            'face_vs_bg_stops': 1.5, 'ev': 0.0}

    # 1 \u8865\u5149\u4eba\u50cf\u6b63\u4f8b
    r1 = shot_check(port)
    ck(r1['level'] == '\u5904\u7406\u5f97\u5f53', '\u8865\u5149\u6b63\u4f8b\u5e94\u5224\u5904\u7406\u5f97\u5f53\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['issues'] == [], '\u8865\u5149\u6b63\u4f8b\u4e0d\u5e94\u6709\u95ee\u9898\u9879\uff0c\u5b9e\u4e3a %s' % r1['issues'])

    # 2 \u53cd\u4f8b\uff1a\u5e73\u5747\u6d4b\u5149
    r2 = shot_check(dict(port, metering='average'))
    ck(r2['level'] == '\u9006\u5149\u5904\u7406\u6709\u660e\u663e\u95ee\u9898', '\u5e73\u5747\u6d4b\u5149\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck(any(i['item'] == '\u6d4b\u5149\u65b9\u5f0f' for i in r2['issues']), '\u5e94\u70b9\u540d\u6d4b\u5149\u65b9\u5f0f')

    # 3 \u53cd\u4f8b\uff1a\u65e2\u6ca1\u8865\u5149\u4e5f\u6ca1 HDR
    r3 = shot_check(dict(port, metering='evaluative', fill='none', hdr=False))
    ck(any(i['item'] == '\u8865\u5149' for i in r3['issues']), '\u6ca1\u8865\u5149\u4e5f\u6ca1 HDR \u5e94\u5224\u4e25\u91cd')
    ck(r3['level'] == '\u9006\u5149\u5904\u7406\u6709\u660e\u663e\u95ee\u9898', '\u6ca1\u8865\u5149\u4e5f\u6ca1 HDR \u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r3['level'])
    ck(not any(i['item'] == '\u8865\u5149' for i in shot_check(dict(port, metering='evaluative',
                                                            fill='none', hdr=True))['issues']),
       '\u5f00\u4e86 HDR \u5c31\u4e0d\u5e94\u518d\u62a5\u6ca1\u8865\u5149')

    # 4 \u53cd\u4f8b\uff1a\u8865\u5149\u8d85\u51fa\u6709\u6548\u8ddd\u79bb
    r4 = shot_check(dict(port, fill='flash', fill_distance_m=6.0, flash_effective_m=3.0))
    ck(any(i['item'] == '\u8865\u5149\u8ddd\u79bb' for i in r4['issues']), '\u95ea\u5149 6 \u7c73\u8d85\u51fa 3 \u7c73\u5e94\u5224\u4e25\u91cd')
    ck(not any(i['item'] == '\u8865\u5149\u8ddd\u79bb' for i in shot_check(dict(port, fill='flash',
                                                               fill_distance_m=2.5,
                                                               flash_effective_m=3.0))['issues']),
       '\u95ea\u5149 2.5 \u7c73\u5728 3 \u7c73\u5185\u5e94\u5408\u683c')
    ck(any(i['item'] == '\u8865\u5149\u8ddd\u79bb' for i in shot_check(dict(port, fill='reflector',
                                                           fill_distance_m=3.5))['issues']),
       '\u53cd\u5149\u677f 3.5 \u7c73\u8d85\u51fa 2 \u7c73\u5e94\u5224\u4e25\u91cd')

    # 5 \u53ef\u6539\u8fdb\u9879\uff1a\u6ca1\u9501\u66dd\u5149
    r5 = shot_check(dict(port, exposure_lock=False))
    ck(any(i['item'] == '\u66dd\u5149\u9501\u5b9a' for i in r5['issues']), '\u6ca1\u9501\u66dd\u5149\u5e94\u63d0\u793a')
    ck(r5['level'] == '\u6709\u53ef\u6539\u8fdb\u9879', '\u6ca1\u9501\u66dd\u5149\u5e94\u5224\u53ef\u6539\u8fdb\uff0c\u5b9e\u4e3a %s' % r5['level'])

    # 6 \u53ef\u6539\u8fdb\u9879\uff1a\u65e0\u906e\u5149\u7f69 / \u6b63\u5bf9\u5149\u6e90 / \u80cc\u666f\u6ea2\u51fa
    ck(any(i['item'] == '\u7729\u5149\u63a7\u5236' for i in shot_check(dict(port, lens_hood=False))['issues']),
       '\u65e0\u906e\u5149\u63aa\u65bd\u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u673a\u4f4d\u89d2\u5ea6' for i in shot_check(dict(port, angle_to_sun='direct'))['issues']),
       '\u6b63\u5bf9\u5149\u6e90\u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u80cc\u666f\u9ad8\u5149' for i in shot_check(dict(port, bg_clipped=True))['issues']),
       '\u80cc\u666f\u6ea2\u51fa\u5e94\u63d0\u793a')

    # 7 \u53ef\u6539\u8fdb\u9879\uff1a\u8865\u5149\u91cf\u8fc7\u4e0e\u4e0d\u53ca
    ck(any(i['item'] == '\u8865\u5149\u91cf' for i in shot_check(dict(port, face_vs_bg_stops=3.0))['issues']),
       '\u6697 3 \u6321\u5e94\u63d0\u793a\u8865\u507f\u4e0d\u8db3')
    ck(any(i['item'] == '\u8865\u5149\u91cf' for i in shot_check(dict(port, face_vs_bg_stops=0.3))['issues']),
       '\u53ea\u5dee 0.3 \u6321\u5e94\u63d0\u793a\u8865\u8fc7\u5934')
    ck(shot_check(dict(port, face_vs_bg_stops=1.0))['issues'] == [], '\u5dee 1 \u6321\u8fb9\u754c\u5e94\u5408\u683c')
    ck(shot_check(dict(port, face_vs_bg_stops=2.0))['issues'] == [], '\u5dee 2 \u6321\u8fb9\u754c\u5e94\u5408\u683c')

    # 8 \u526a\u5f71\u6b63\u4f8b
    sil = {'name': '\u6d77\u8fb9\u526a\u5f71', 'mode': 'silhouette', 'light': 'back', 'ev': -1.5,
           'outline_clear': True, 'bg_has_light': True, 'angle_to_sun': 'shielded',
           'lens_hood': True}
    r8 = shot_check(sil)
    ck(r8['level'] == '\u5904\u7406\u5f97\u5f53', '\u526a\u5f71\u6b63\u4f8b\u5e94\u5224\u5904\u7406\u5f97\u5f53\uff0c\u5b9e\u4e3a %s' % r8['level'])
    ck(not any('\u8138' in i['detail'] for i in r8['issues']), '\u526a\u5f71\u4e0d\u5e94\u62a5\u8138\u9ed1')

    # 9 \u53cd\u4f8b\uff1a\u526a\u5f71\u6ca1\u538b\u66dd\u5149
    r9 = shot_check(dict(sil, ev=1.0))
    ck(r9['level'] == '\u9006\u5149\u5904\u7406\u6709\u660e\u663e\u95ee\u9898', '\u526a\u5f71\u6ca1\u538b\u66dd\u5149\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r9['level'])
    ck(any(i['item'] == '\u66dd\u5149\u8865\u507f' for i in r9['issues']), '\u5e94\u70b9\u540d\u66dd\u5149\u8865\u507f')
    ck(shot_check(dict(sil, ev=-0.5))['issues'] == [], 'EV -0.5 \u8fb9\u754c\u5e94\u5408\u683c')
    ck(any(i['item'] == '\u66dd\u5149\u8865\u507f' for i in shot_check(dict(sil, ev=-3.0))['issues']),
       'EV -3.0 \u538b\u8fc7\u5934\u5e94\u63d0\u793a')

    # 10 \u53cd\u4f8b\uff1a\u526a\u5f71\u8f6e\u5ed3\u4e0d\u6e05 / \u80cc\u666f\u65e0\u5149
    ck(any(i['item'] == '\u8f6e\u5ed3' for i in shot_check(dict(sil, outline_clear=False))['issues']),
       '\u8f6e\u5ed3\u4e0d\u6e05\u5e94\u5224\u4e25\u91cd')
    ck(any(i['item'] == '\u80cc\u666f' for i in shot_check(dict(sil, bg_has_light=False))['issues']),
       '\u80cc\u666f\u65e0\u5149\u5e94\u5224\u4e25\u91cd')

    # 11 \u975e\u9006\u5149\u573a\u666f\u4e0d\u9002\u7528
    r11 = shot_check(dict(port, light='front'))
    ck(r11['level'] == '\u4e0d\u9002\u7528\u9006\u5149\u5224\u5b9a', '\u987a\u5149\u5e94\u5224\u4e0d\u9002\u7528\uff0c\u5b9e\u4e3a %s' % r11['level'])
    ck(r11['issues'] == [], '\u4e0d\u9002\u7528\u65f6\u4e0d\u5e94\u62a5\u95ee\u9898\u9879')

    # 12 \u6392\u5e8f\u65b9\u5411\uff1a\u4e25\u91cd\u9879\u6392\u6700\u524d
    r12 = shot_check(dict(port, metering='average', fill='none', lens_hood=False,
                          bg_clipped=True))
    ck(r12['issues'][0]['sev'] == 3, '\u4e25\u91cd\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r12['issues'][0]['sev'])
    ck(r12['issues'][-1]['sev'] == 2, '\u672b\u4f4d\u5e94\u662f\u53ef\u6539\u8fdb\u9879')

    # 13 \u5224\u5b9a\u987a\u5e8f\uff1a\u6709\u4e25\u91cd\u9879\u65f6\u4e0d\u56e0\u7f3a\u4fe1\u606f\u5224\u5f85\u786e\u8ba4
    r13 = shot_check({'name': '\u53ea\u586b\u6d4b\u5149', 'mode': 'portrait', 'light': 'back',
                      'metering': 'average', 'fill': 'none', 'hdr': False})
    ck(r13['level'] == '\u9006\u5149\u5904\u7406\u6709\u660e\u663e\u95ee\u9898', '\u7f3a\u5176\u4ed6\u9879\u4f46\u6709\u4e25\u91cd\u9879\u4e0d\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r13['level'])
    r13b = shot_check({'name': '\u53ea\u586b\u8def\u7ebf', 'mode': 'portrait', 'light': 'back',
                       'metering': 'spot_face', 'fill': 'reflector', 'fill_distance_m': 1.5})
    ck(r13b['level'] == '\u5f85\u786e\u8ba4', '\u672a\u586b\u9501\u5b9a\u4e0e\u906e\u5149\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r13b['level'])

    # 14 \u6c47\u603b\u4e0e\u6574\u6539\u987a\u5e8f
    r14 = calc({'shots': [port,
                          dict(port, name='\u8138\u5168\u9ed1', metering='average', fill='none', hdr=False),
                          dict(port, name='\u6ca1\u906e\u5149', lens_hood=False)]})
    ck(r14['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u9006\u5149\u7167\u7247', '\u6709\u4e25\u91cd\u9879\u5e94\u5224\u9700\u8981\u91cd\u62cd\uff0c\u5b9e\u4e3a %s' % r14['overall'])
    ck(r14['n_bad'] == 1, '\u4e25\u91cd\u9879\u5e94\u4e3a 1 \u5f20\uff0c\u5b9e\u4e3a %d' % r14['n_bad'])
    ck(r14['fix_order'][0] == '\u8138\u5168\u9ed1', '\u4e25\u91cd\u9879\u5e94\u5148\u6539\uff0c\u5b9e\u4e3a %s' % r14['fix_order'])
    ck(r14['fix_order'][1] == '\u6ca1\u906e\u5149', '\u53ef\u6539\u8fdb\u9879\u6392\u5176\u540e\uff0c\u5b9e\u4e3a %s' % r14['fix_order'])

    # 15 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'shots': [dict(port, metering='average')]})
    r15 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r15['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u9006\u5149\u7167\u7247', 'BOM \u5b57\u7b26\u4e32\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r15['overall'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_c4.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'shots': [dict(sil, name='\u5e26BOM', ev=1.0)]}))
    try:
        r15b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r15b['rows'][0]['name'] == '\u5e26BOM', 'BOM \u6587\u4ef6\u9996\u4e2a key \u5e94\u89e3\u6790\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r15b['rows'][0]['name'])
        ck(r15b['n_bad'] == 1, '\u526a\u5f71\u6ca1\u538b\u66dd\u5149\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %d' % r15b['n_bad'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 16 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({}, '\u7f3a shots'),
        ({'shots': []}, 'shots \u7a7a\u5217\u8868'),
        ({'shots': [dict(port, mode='\u534a\u9006\u5149')]}, '\u672a\u77e5\u8def\u7ebf'),
        ({'shots': [dict(port, light='\u9876\u5149')]}, '\u672a\u77e5\u5149\u4f4d'),
        ({'shots': [dict(port, metering='\u70b9\u6d4b\u5149')]}, '\u672a\u77e5\u6d4b\u5149'),
        ({'shots': [dict(port, fill='\u6253\u5149')]}, '\u672a\u77e5\u8865\u5149'),
        ({'shots': [dict(port, angle_to_sun='\u659c\u7740')]}, '\u672a\u77e5\u673a\u4f4d'),
        ({'shots': [dict(port, fill_distance_m=-1)]}, '\u8ddd\u79bb\u4e3a\u8d1f'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b16 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 17 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r14)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u4e24\u6761\u8def\u7ebf', '\u9010\u5f20\u5224\u5b9a', '\u6d4b\u5149\u65b9\u5f0f', '\u8865\u5149\u65b9\u5f0f\u4e0e\u6709\u6548\u8ddd\u79bb',
                '\u9608\u503c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(MODES) == 2, '\u8def\u7ebf\u5e94 2 \u6761')
    ck(len([m for m in METERING if m[2]]) == 3, '\u4f1a\u88ab\u5e26\u504f\u7684\u6d4b\u5149\u65b9\u5f0f\u5e94 3 \u79cd')
    ck(any(f[0] == 'flash' for f in FILLS), '\u8865\u5149\u65b9\u5f0f\u5fc5\u987b\u542b\u95ea\u5149\u706f')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u8865\u5149\u6b63\u4f8b/\u5e73\u5747\u6d4b\u5149\u53cd\u4f8b/\u6ca1\u8865\u5149\u4e5f\u6ca1HDR\u53cd\u4f8b/\u8865\u5149\u8d85\u8ddd\u53cd\u4f8b\u4e0e\u8fb9\u754c/'
        '\u672a\u9501\u66dd\u5149/\u7729\u5149\u4e0e\u673a\u4f4d\u4e0e\u80cc\u666f\u6ea2\u51fa/\u8865\u5149\u91cf\u4e0a\u4e0b\u754c/\u526a\u5f71\u6b63\u4f8b\u4e0e\u4e0d\u62a5\u8138\u9ed1/\u526a\u5f71\u672a\u538b\u66dd\u5149\u53cd\u4f8b\u4e0e\u8fb9\u754c/'
        '\u526a\u5f71\u8f6e\u5ed3\u4e0e\u80cc\u666f\u53cd\u4f8b/\u975e\u9006\u5149\u4e0d\u9002\u7528/\u4e25\u91cd\u9879\u6392\u5e8f/\u5224\u5b9a\u987a\u5e8f/\u6c47\u603b\u6574\u6539\u987a\u5e8f/BOM\u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u9006\u5149\u62cd\u7167\u6838\u67e5')
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
