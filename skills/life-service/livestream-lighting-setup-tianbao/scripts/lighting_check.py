# -*- coding: utf-8 -*-
"""\u76f4\u64ad\u5e03\u5149\u6838\u67e5\uff1a\u6838\u4e3b\u5149\u4f4d\u7f6e\u4e0e\u7167\u5ea6\u3001\u8f85\u5149\u6bd4\u4f8b\u3001\u8f6e\u5ed3\u5149\u4e0e\u80cc\u666f\u5149\u3001\u8272\u6e29\u7edf\u4e00\u4e0e\u773c\u955c\u53cd\u5149\u3002

\u7528\u6cd5:
  python lighting_check.py --file lighting.json [--out result.md] [--format json]
  python lighting_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u4e3b\u5149\u9ad8\u5ea6: (\u952e, \u4e2d\u6587\u540d, \u662f\u5426\u5408\u683c, \u8bf4\u660e)
HEIGHTS = [
    ('above_eye', '\u7565\u9ad8\u4e8e\u89c6\u7ebf', True, '\u773c\u90e8\u6709\u795e\u3001\u4e0b\u5df4\u9634\u5f71\u81ea\u7136\uff0c\u63a8\u8350'),
    ('eye_level', '\u4e0e\u89c6\u7ebf\u9f50\u5e73', True, '\u53ef\u7528\uff0c\u4f46\u7acb\u4f53\u611f\u7565\u5e73'),
    ('below', '\u4f4e\u4e8e\u89c6\u7ebf', False, '\u9634\u5f71\u5f80\u4e0a\u8d70\uff0c\u89c2\u611f\u602a\u5f02'),
]

# \u573a\u666f: (\u952e, \u4e2d\u6587\u540d, \u8981\u70b9)
SCENES = [
    ('sit', '\u5750\u64ad\uff08\u684c\u9762\u8fd1\u8ddd\uff09', '\u4e3b\u5149\u4fa7\u524d\u65b9 45 \u5ea6\uff0c\u5173\u6389\u623f\u95f4\u9876\u706f\uff0c\u684c\u9762\u53cd\u5149\u6750\u8d28\u907f\u5f00\u76f4\u5c04'),
    ('stand', '\u7ad9\u64ad\uff08\u5168\u8eab\uff09', '\u4e3b\u5149\u62ac\u9ad8\u8986\u76d6\u5168\u8eab\uff0c\u5fc5\u987b\u6709\u8f6e\u5ed3\u5149\uff0c\u80cc\u666f\u6574\u4f53\u63d0\u4eae\u4e00\u6863'),
    ('product', '\u4ea7\u54c1\u5c55\u793a', '\u67d4\u5149\u7bb1\u8d34\u8fd1\u4ea7\u54c1\u7a81\u51fa\u7eb9\u7406\uff0c\u53cd\u5149\u677f\u8865\u5149\uff0c5600K \u8272\u5f69\u66f4\u51c6'),
]

# \u9608\u503c
TOL = {
    'angle_min': 30.0,        # \u4e3b\u5149\u89d2\u5ea6\u4e0b\u9650\uff08\u5ea6\uff09
    'angle_max': 60.0,        # \u4e3b\u5149\u89d2\u5ea6\u4e0a\u9650\uff08\u5ea6\uff09
    'angle_flat': 15.0,       # \u6b63\u9762\u76f4\u6253\u5224\u5b9a\u9608\u503c\uff08\u5ea6\uff09
    'key_lux_min': 300.0,     # \u4e3b\u5149\u7167\u5ea6\u4e0b\u9650\uff08\u52d2\u514b\u65af\uff09
    'key_lux_ideal': 600.0,   # \u4e3b\u5149\u7167\u5ea6\u63a8\u8350\u4e0b\u9650
    'fill_min': 0.3,          # \u8f85\u5149\u4e0e\u4e3b\u5149\u4e4b\u6bd4\u4e0b\u9650
    'fill_max': 0.7,          # \u8f85\u5149\u4e0e\u4e3b\u5149\u4e4b\u6bd4\u4e0a\u9650
    'fill_dead': 0.2,         # \u6697\u90e8\u6b7b\u9ed1\u7684\u5224\u5b9a\u7ebf
    'ambient_ratio_min': 3.0,  # \u4e3b\u5149\u4e0e\u73af\u5883\u5149\u4e4b\u6bd4\u4e0b\u9650
    'ambient_ratio_max': 8.0,  # \u4e3b\u5149\u4e0e\u73af\u5883\u5149\u4e4b\u6bd4\u4e0a\u9650
    'glass_angle_min': 30.0,  # \u6234\u773c\u955c\u65f6\u7684\u4e3b\u5149\u89d2\u5ea6\u4e0b\u9650
    'back_angle': 150.0,      # \u5224\u5b9a\u4e3a\u300c\u6b63\u540e\u65b9\u5149\u6e90\u300d\u7684\u89d2\u5ea6
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


def setup_check(s):
    if not isinstance(s, dict):
        raise ValueError('setups \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
    name = str(s.get('name') or '\u672a\u547d\u540d').strip()
    angle = _f(s, 'key_angle_deg')
    height = _row(HEIGHTS, s.get('key_height'), 'key_height')
    scene = _row(SCENES, s.get('scene'), 'scene')
    key_lux = _f(s, 'key_lux')
    amb_lux = _f(s, 'ambient_lux')
    fill = _f(s, 'fill_ratio')
    temp_k = _f(s, 'color_temp_k')

    issues = []
    misses = []

    # \u4e25\u91cd\u9879 1\uff1a\u6b63\u540e\u65b9\u5149\u6e90\u6216\u80cc\u540e\u5f3a\u7a97
    behind = bool(s.get('window_behind')) or (angle is not None and angle >= TOL['back_angle'])
    if behind:
        issues.append({
            'sev': 3, 'item': '\u5149\u6e90\u65b9\u4f4d',
            'detail': '\u4e3b\u5149\u5728\u6b63\u540e\u65b9\u6216\u80cc\u540e\u6709\u5f3a\u5149\u6e90\uff08\u7a97\u6237\uff09',
            'why': '\u80cc\u540e\u6781\u4eae\u4f1a\u8ba9\u6444\u50cf\u8bbe\u5907\u6574\u4f53\u964d\u66dd\u5149\uff0c\u4eba\u8138\u76f4\u63a5\u53d8\u9ed1\uff1b'
                   '\u62c9\u4e0a\u7a97\u5e18\u3001\u5173\u6389\u80cc\u540e\u5149\u6e90\uff0c\u6216\u6539\u6210\u4fa7\u5bf9\u3001\u9762\u5bf9\u7a97\u6237',
        })

    # \u4e25\u91cd\u9879 2\uff1a\u53ea\u6709\u9876\u5149
    if s.get('top_light_only'):
        issues.append({
            'sev': 3, 'item': '\u9876\u5149',
            'detail': '\u53ea\u6709\u9876\u5149',
            'why': '\u9876\u5149\u4f1a\u5728\u773c\u7a9d\u3001\u9f3b\u4e0b\u3001\u4e0b\u5df4\u7559\u4e0b\u6d53\u91cd\u9634\u5f71\uff0c\u773c\u795e\u53d1\u9ed1\uff1b'
                   '\u5728\u4fa7\u524d\u65b9 30 \u5230 60 \u5ea6\u8865\u4e00\u76cf\u4e3b\u5149',
        })

    # \u4e25\u91cd\u9879 3\uff1a\u7167\u5ea6\u4e0d\u8db3
    if key_lux is None:
        misses.append('\u4e3b\u5149\u7167\u5ea6')
    else:
        if key_lux < TOL['key_lux_min']:
            issues.append({
                'sev': 3, 'item': '\u4e3b\u5149\u7167\u5ea6',
                'detail': '%.0f \u52d2\u514b\u65af\uff0c\u4f4e\u4e8e %.0f' % (key_lux, TOL['key_lux_min']),
                'why': '\u7167\u5ea6\u4e0d\u8db3\u65f6\u8bbe\u5907\u4f1a\u81ea\u52a8\u63d0\u9ad8\u611f\u5149\u5ea6\uff0c\u753b\u9762\u51fa\u73b0\u566a\u70b9\u4e0e\u6d82\u62b9\u611f\uff1b\u5148\u52a0\u706f\uff0c\u4e0d\u8981\u6307\u671b\u540e\u671f',
            })
        elif key_lux < TOL['key_lux_ideal']:
            issues.append({
                'sev': 2, 'item': '\u4e3b\u5149\u7167\u5ea6',
                'detail': '%.0f \u52d2\u514b\u65af\uff0c\u672a\u8fbe\u5efa\u8bae\u7684 %.0f' % (key_lux, TOL['key_lux_ideal']),
                'why': '\u7167\u5ea6\u504f\u4f4e\uff0c\u753b\u9762\u5bb9\u6613\u53d1\u6697\uff1b\u628a\u4e3b\u5149\u8c03\u4eae\u6216\u62c9\u8fd1\u4e00\u70b9',
            })

    # \u4e25\u91cd\u9879 4\uff1a\u8272\u6e29\u4e0d\u4e00\u81f4
    if s.get('temp_consistent') is False:
        issues.append({
            'sev': 3, 'item': '\u8272\u6e29',
            'detail': '\u73b0\u573a\u6df7\u7528\u4e86\u4e0d\u540c\u8272\u6e29\u7684\u5149\u6e90',
            'why': '\u4e00\u4fa7\u53d1\u9ec4\u4e00\u4fa7\u53d1\u9752\uff0c\u540e\u671f\u600e\u4e48\u8c03\u90fd\u8c03\u4e0d\u56de\u6765\uff1b'
                   '\u5173\u6389\u623f\u95f4\u539f\u6709\u9876\u706f\uff0c\u6216\u7ed9\u76f4\u64ad\u706f\u52a0\u540c\u8272\u6e29\u7684\u8272\u7247',
        })

    # \u4e25\u91cd\u9879 5\uff1a\u4e3b\u5149\u9ad8\u5ea6\u4f4e\u4e8e\u89c6\u7ebf
    if height is not None and not height[2]:
        issues.append({
            'sev': 3, 'item': '\u4e3b\u5149\u9ad8\u5ea6',
            'detail': '%s' % height[1],
            'why': '\u5149\u6e90\u4f4e\u4e8e\u89c6\u7ebf\u65f6\u9634\u5f71\u5f80\u4e0a\u8d70\uff0c\u89c2\u611f\u602a\u5f02\uff1b\u628a\u4e3b\u5149\u62ac\u5230\u7565\u9ad8\u4e8e\u89c6\u7ebf',
        })

    # \u4e25\u91cd\u9879 6\uff1a\u6b63\u9762\u96f6\u89d2\u5ea6\u76f4\u6253
    if angle is None:
        misses.append('\u4e3b\u5149\u89d2\u5ea6')
    else:
        if angle < TOL['angle_flat'] and not behind:
            issues.append({
                'sev': 3, 'item': '\u4e3b\u5149\u89d2\u5ea6',
                'detail': '%.0f \u5ea6\uff0c\u5c5e\u4e8e\u6b63\u9762\u76f4\u6253' % angle,
                'why': '\u6b63\u9762\u96f6\u89d2\u5ea6\u76f4\u6253\u4f1a\u8ba9\u8138\u50cf\u4e00\u5f20\u5e73\u677f\uff0c\u6ca1\u6709\u7acb\u4f53\u611f\uff1b'
                       '\u628a\u4e3b\u5149\u504f\u5230 30 \u5230 60 \u5ea6',
            })
        elif angle < TOL['angle_min'] and not behind:
            issues.append({
                'sev': 2, 'item': '\u4e3b\u5149\u89d2\u5ea6',
                'detail': '%.0f \u5ea6\uff0c\u672a\u8fbe\u5efa\u8bae\u7684 %.0f \u5ea6' % (angle, TOL['angle_min']),
                'why': '\u89d2\u5ea6\u504f\u5c0f\u7acb\u4f53\u611f\u4e0d\u8db3\uff1b\u504f\u5230 30 \u5230 60 \u5ea6\u6548\u679c\u6700\u597d',
            })
        elif angle > TOL['angle_max'] and not behind:
            issues.append({
                'sev': 2, 'item': '\u4e3b\u5149\u89d2\u5ea6',
                'detail': '%.0f \u5ea6\uff0c\u8d85\u8fc7 %.0f \u5ea6' % (angle, TOL['angle_max']),
                'why': '\u89d2\u5ea6\u8fc7\u5927\u53e6\u4e00\u4fa7\u8138\u4f1a\u5168\u9ed1\uff1b\u56de\u5230 30 \u5230 60 \u5ea6\uff0c\u6216\u52a0\u8f85\u5149\u8865\u6697\u90e8',
            })
        # \u6234\u773c\u955c\u65f6\u7684\u53cd\u5149
        if s.get('glasses') and angle < TOL['glass_angle_min'] and not behind:
            issues.append({
                'sev': 3, 'item': '\u773c\u955c\u53cd\u5149',
                'detail': '\u6234\u773c\u955c\u4e14\u4e3b\u5149\u89d2\u5ea6 %.0f \u5ea6\uff0c\u5c0f\u4e8e %.0f \u5ea6' % (angle, TOL['glass_angle_min']),
                'why': '\u955c\u7247\u4f1a\u628a\u5149\u6e90\u76f4\u63a5\u53cd\u5c04\u8fdb\u955c\u5934\u5f62\u6210\u767d\u6591\u906e\u4f4f\u773c\u775b\uff1b'
                       '\u628a\u4e3b\u5149\u89d2\u5ea6\u52a0\u5927\u5e76\u62ac\u9ad8\uff0c\u6216\u7528\u67d4\u5149\u7bb1\u6269\u5927\u5149\u6e90\u9762\u79ef',
            })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u8f85\u5149\u6bd4\u4f8b
    if fill is None:
        misses.append('\u8f85\u5149\u6bd4\u4f8b')
    else:
        if fill < TOL['fill_dead']:
            issues.append({
                'sev': 2, 'item': '\u8f85\u5149\u6bd4\u4f8b',
                'detail': '\u8f85\u5149\u4e3a\u4e3b\u5149\u7684 %.2f\uff0c\u4f4e\u4e8e %.1f' % (fill, TOL['fill_dead']),
                'why': '\u8f85\u5149\u592a\u5f31\u6697\u90e8\u4f1a\u6b7b\u9ed1\uff1b\u8f85\u5149\u8c03\u5230\u4e3b\u5149\u7684 0.3 \u5230 0.7',
            })
        elif fill < TOL['fill_min']:
            issues.append({
                'sev': 2, 'item': '\u8f85\u5149\u6bd4\u4f8b',
                'detail': '\u8f85\u5149\u4e3a\u4e3b\u5149\u7684 %.2f\uff0c\u672a\u8fbe\u5efa\u8bae\u7684 %.1f' % (fill, TOL['fill_min']),
                'why': '\u8f85\u5149\u504f\u5f31\uff0c\u6697\u90e8\u7ec6\u8282\u4e0d\u8db3\uff1b\u8f85\u5149\u662f\u63d0\u4eae\u6697\u90e8\uff0c\u4e0d\u662f\u6d88\u706d\u9634\u5f71',
            })
        elif fill > TOL['fill_max']:
            issues.append({
                'sev': 2, 'item': '\u8f85\u5149\u6bd4\u4f8b',
                'detail': '\u8f85\u5149\u4e3a\u4e3b\u5149\u7684 %.2f\uff0c\u8d85\u8fc7 %.1f' % (fill, TOL['fill_max']),
                'why': '\u8f85\u5149\u592a\u5f3a\u4f1a\u628a\u4e3b\u5149\u7684\u9020\u578b\u5168\u62b9\u5e73\uff0c\u8138\u53c8\u53d8\u6210\u5e73\u677f\uff1b'
                       '\u8f85\u5149\u964d\u5230\u4e3b\u5149\u7684 0.3 \u5230 0.7',
            })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u8f6e\u5ed3\u5149\u4e0e\u80cc\u666f\u5149
    if s.get('backlight') is False:
        issues.append({
            'sev': 2, 'item': '\u8f6e\u5ed3\u5149',
            'detail': '\u6ca1\u6709\u8f6e\u5ed3\u5149',
            'why': '\u6ca1\u6709\u8f6e\u5ed3\u5149\u4eba\u4e0e\u80cc\u666f\u4f1a\u7cca\u5728\u4e00\u8d77\uff1b\u4ece\u4fa7\u540e\u65b9\u8865\u4e00\u76cf\uff0c'
                   '\u5728\u5934\u53d1\u80a9\u8180\u8fb9\u7f18\u52fe\u4e00\u9053\u4eae\u8fb9',
        })
    if s.get('bg_light') is False:
        issues.append({
            'sev': 2, 'item': '\u80cc\u666f\u5149',
            'detail': '\u80cc\u666f\u6ca1\u6709\u72ec\u7acb\u6253\u5149',
            'why': '\u80cc\u666f\u5168\u9ed1\u4f1a\u8ba9\u753b\u9762\u7f3a\u5c11\u5c42\u6b21\uff1b\u7ed9\u80cc\u666f\u5355\u72ec\u8865\u5149\uff0c'
                   '\u4f46\u4e0d\u8981\u8ba9\u80cc\u666f\u6bd4\u4eba\u8138\u8fd8\u4eae',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u4e3b\u5149\u4e0e\u73af\u5883\u5149\u4e4b\u6bd4
    if key_lux is not None and amb_lux is not None and amb_lux > 0:
        ratio = key_lux / amb_lux
        if ratio < TOL['ambient_ratio_min']:
            issues.append({
                'sev': 2, 'item': '\u5149\u6bd4',
                'detail': '\u4e3b\u5149\u4e0e\u73af\u5883\u5149\u4e4b\u6bd4\u4e3a %.1f\uff0c\u4f4e\u4e8e %.1f' % (ratio, TOL['ambient_ratio_min']),
                'why': '\u73af\u5883\u592a\u4eae\u4e3b\u4f53\u4e0d\u7a81\u51fa\uff0c\u753b\u9762\u53d1\u5e73\uff1b\u964d\u4f4e\u73af\u5883\u5149\u6216\u63d0\u9ad8\u4e3b\u5149',
            })
        elif ratio > TOL['ambient_ratio_max']:
            issues.append({
                'sev': 2, 'item': '\u5149\u6bd4',
                'detail': '\u4e3b\u5149\u4e0e\u73af\u5883\u5149\u4e4b\u6bd4\u4e3a %.1f\uff0c\u8d85\u8fc7 %.1f' % (ratio, TOL['ambient_ratio_max']),
                'why': '\u73af\u5883\u592a\u6697\u4f1a\u663e\u5f97\u50cf\u5728\u6d1e\u91cc\uff1b\u7ed9\u80cc\u666f\u8865\u4e00\u70b9\u5149',
            })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u4eba\u8d34\u5899
    if s.get('too_close_to_wall'):
        issues.append({
            'sev': 2, 'item': '\u4eba\u7269\u8ddd\u79bb',
            'detail': '\u4eba\u7269\u79bb\u5899\u592a\u8fd1',
            'why': '\u8d34\u7740\u5899\u4f1a\u628a\u5f71\u5b50\u6295\u5728\u5899\u4e0a\uff1b\u79bb\u5899\u81f3\u5c11 0.5 \u7c73',
        })

    issues.sort(key=lambda r: -r['sev'])

    if any(i['sev'] == 3 for i in issues):
        level = '\u5e03\u5149\u6709\u660e\u663e\u95ee\u9898'
    elif issues:
        level = '\u6709\u53ef\u6539\u8fdb\u9879'
    elif misses:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u5e03\u5149\u5408\u7406'

    return {
        'name': name, 'level': level, 'issues': issues, 'misses': misses,
        'angle': angle, 'height': height[1] if height else None,
        'key_lux': key_lux, 'amb_lux': amb_lux, 'fill': fill, 'temp_k': temp_k,
        'scene': scene[1] if scene else None,
    }


def calc(data):
    setups = data.get('setups')
    if setups is None:
        raise ValueError('\u8f93\u5165\u7f3a\u5c11 setups \u5217\u8868')
    if not isinstance(setups, list) or not setups:
        raise ValueError('setups \u5fc5\u987b\u662f\u975e\u7a7a\u5217\u8868')
    rows = [setup_check(s) for s in setups]
    n_bad = len([r for r in rows if r['level'] == '\u5e03\u5149\u6709\u660e\u663e\u95ee\u9898'])
    n_mid = len([r for r in rows if r['level'] == '\u6709\u53ef\u6539\u8fdb\u9879'])
    n_unk = len([r for r in rows if r['level'] == '\u5f85\u786e\u8ba4'])
    if n_bad:
        overall = '\u5b58\u5728\u9700\u8981\u91cd\u8c03\u7684\u5e03\u5149'
    elif n_mid:
        overall = '\u5b58\u5728\u53ef\u6539\u8fdb\u7684\u5e03\u5149'
    elif n_unk:
        overall = '\u5f85\u786e\u8ba4'
    else:
        overall = '\u5168\u90e8\u5e03\u5149\u5408\u7406'

    def _sev(r):
        return max([i['sev'] for i in r['issues']], default=0)

    order = sorted(rows, key=lambda r: (-_sev(r), -len(r['issues']), r['name']))
    return {
        'overall': overall, 'rows': rows,
        'n_bad': n_bad, 'n_mid': n_mid, 'n_unk': n_unk,
        'n_ok': len(rows) - n_bad - n_mid - n_unk,
        'fix_order': [r['name'] for r in order if r['issues']],
        'heights': [{'key': k, 'name': n, 'ok': o, 'note': nt} for k, n, o, nt in HEIGHTS],
        'scenes': [{'key': k, 'name': n, 'note': nt} for k, n, nt in SCENES],
        'tol': dict(TOL),
    }


def render_md(r):
    L = []
    L.append('# \u76f4\u64ad\u5e03\u5149\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['overall'])
    L.append('')
    L.append('| \u7c7b\u522b | \u4e2a\u6570 |')
    L.append('|---|---|')
    L.append('| \u9700\u8981\u91cd\u8c03 | %d |' % r['n_bad'])
    L.append('| \u53ef\u6539\u8fdb | %d |' % r['n_mid'])
    L.append('| \u5f85\u786e\u8ba4 | %d |' % r['n_unk'])
    L.append('| \u5e03\u5149\u5408\u7406 | %d |' % r['n_ok'])
    L.append('')
    if r['fix_order']:
        L.append('\u6574\u6539\u987a\u5e8f\uff08\u4e25\u91cd\u5ea6\u9ad8\u7684\u5148\u6539\uff09\uff1a%s' % '\u3001'.join(r['fix_order']))
        L.append('')
    L.append('## \u4e8c\u3001\u4e09\u70b9\u5e03\u5149')
    L.append('')
    L.append('| \u706f | \u4f4d\u7f6e | \u4f5c\u7528 | \u4eae\u5ea6 |')
    L.append('|---|---|---|---|')
    L.append('| \u4e3b\u5149 | \u955c\u5934\u4fa7\u524d\u65b9 30 \u5230 60 \u5ea6\uff0c\u7565\u9ad8\u4e8e\u89c6\u7ebf | \u51b3\u5b9a\u57fa\u672c\u660e\u6697\u4e0e\u7acb\u4f53\u611f | \u57fa\u51c6 |')
    L.append('| \u8f85\u5149 | \u53e6\u4e00\u4fa7\u9760\u8fd1\u955c\u5934\u8f74\u7ebf | \u63d0\u4eae\u6697\u90e8\uff0c\u4e0d\u6d88\u706d\u9634\u5f71 | \u4e3b\u5149\u7684 0.3 \u5230 0.7 |')
    L.append('| \u8f6e\u5ed3\u5149 | \u4fa7\u540e\u65b9\uff0c\u4ece\u80a9\u8180\u659c\u540e\u65b9\u6253 | \u628a\u4eba\u4e0e\u80cc\u666f\u5206\u5f00 | \u4e0e\u4e3b\u5149\u76f8\u5f53\u6216\u7565\u9ad8 |')
    L.append('')
    L.append('## \u4e09\u3001\u9010\u5957\u5224\u5b9a')
    L.append('')
    for row in r['rows']:
        L.append('### %s' % row['name'])
        L.append('')
        L.append('- \u5224\u5b9a\uff1a**%s**' % row['level'])
        if row['scene']:
            L.append('- \u573a\u666f\uff1a%s' % row['scene'])
        if row['angle'] is not None:
            L.append('- \u4e3b\u5149\u89d2\u5ea6\uff1a%.0f \u5ea6' % row['angle'])
        if row['height']:
            L.append('- \u4e3b\u5149\u9ad8\u5ea6\uff1a%s' % row['height'])
        if row['key_lux'] is not None:
            L.append('- \u4e3b\u5149\u7167\u5ea6\uff1a%.0f \u52d2\u514b\u65af' % row['key_lux'])
        if row['amb_lux'] is not None:
            L.append('- \u73af\u5883\u7167\u5ea6\uff1a%.0f \u52d2\u514b\u65af' % row['amb_lux'])
        if row['fill'] is not None:
            L.append('- \u8f85\u5149\u6bd4\u4f8b\uff1a%.2f' % row['fill'])
        if row['temp_k'] is not None:
            L.append('- \u8272\u6e29\uff1a%.0f K' % row['temp_k'])
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
    L.append('## \u56db\u3001\u4e3b\u5149\u9ad8\u5ea6')
    L.append('')
    L.append('| \u9ad8\u5ea6 | \u662f\u5426\u53ef\u7528 | \u8bf4\u660e |')
    L.append('|---|---|---|')
    for h in r['heights']:
        L.append('| %s | %s | %s |' % (h['name'], '\u53ef\u4ee5' if h['ok'] else '\u4e0d\u53ef\u4ee5', h['note']))
    L.append('')
    L.append('## \u4e94\u3001\u4e09\u79cd\u573a\u666f\u65b9\u6848')
    L.append('')
    L.append('| \u573a\u666f | \u8981\u70b9 |')
    L.append('|---|---|')
    for s in r['scenes']:
        L.append('| %s | %s |' % (s['name'], s['note']))
    L.append('')
    L.append('## \u516d\u3001\u9608\u503c')
    L.append('')
    L.append('| \u9879\u76ee | \u9608\u503c |')
    L.append('|---|---|')
    L.append('| \u4e3b\u5149\u89d2\u5ea6 | %.0f \u5230 %.0f \u5ea6\uff08\u5c0f\u4e8e %.0f \u5ea6\u4e3a\u6b63\u9762\u76f4\u6253\uff09 |'
             % (r['tol']['angle_min'], r['tol']['angle_max'], r['tol']['angle_flat']))
    L.append('| \u4e3b\u5149\u7167\u5ea6 | \u4e0d\u4f4e\u4e8e %.0f \u52d2\u514b\u65af\uff0c\u5efa\u8bae %.0f \u4ee5\u4e0a |'
             % (r['tol']['key_lux_min'], r['tol']['key_lux_ideal']))
    L.append('| \u8f85\u5149\u4e0e\u4e3b\u5149\u4e4b\u6bd4 | %.1f \u5230 %.1f |' % (r['tol']['fill_min'], r['tol']['fill_max']))
    L.append('| \u4e3b\u5149\u4e0e\u73af\u5883\u5149\u4e4b\u6bd4 | %.0f \u5230 %.0f |'
             % (r['tol']['ambient_ratio_min'], r['tol']['ambient_ratio_max']))
    L.append('| \u6234\u773c\u955c\u65f6\u4e3b\u5149\u89d2\u5ea6 | \u4e0d\u5c0f\u4e8e %.0f \u5ea6 |' % r['tol']['glass_angle_min'])
    L.append('')
    L.append('## \u4e03\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u770b\u8138\uff1a\u8138\u662f\u4e0d\u662f\u5747\u5300\u4eae\uff0c\u6709\u6ca1\u6709\u4e00\u8fb9\u5168\u9ed1')
    L.append('- [ ] \u770b\u80cc\u666f\uff1a\u80cc\u666f\u6709\u72ec\u7acb\u6253\u5149\uff0c\u4eba\u548c\u80cc\u666f\u5206\u5f97\u5f00')
    L.append('- [ ] \u770b\u8272\u6e29\uff1a\u5173\u6389\u623f\u95f4\u9876\u706f\uff0c\u5168\u573a\u53ea\u6709\u4e00\u79cd\u8272\u6e29')
    L.append('- [ ] \u6234\u773c\u955c\u7684\u8bdd\u955c\u7247\u4e0a\u6ca1\u6709\u767d\u6591')
    L.append('- [ ] \u4eba\u79bb\u5899\u81f3\u5c11 0.5 \u7c73\uff0c\u5899\u4e0a\u6ca1\u6709\u5f71\u5b50')
    L.append('- [ ] \u706f\u5177\u7528\u7535\u5b89\u5168\uff0c\u6ca1\u6709\u8d85\u8d1f\u8377\u4f7f\u7528\u63d2\u7ebf\u677f')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    good = {'name': '\u5750\u64ad\u684c\u9762', 'scene': 'sit', 'key_angle_deg': 45,
            'key_height': 'above_eye', 'key_lux': 900, 'ambient_lux': 150,
            'fill_ratio': 0.5, 'color_temp_k': 5600, 'temp_consistent': True,
            'backlight': True, 'bg_light': True, 'glasses': False,
            'window_behind': False, 'top_light_only': False,
            'too_close_to_wall': False}

    # 1 \u6b63\u4f8b
    r1 = setup_check(good)
    ck(r1['level'] == '\u5e03\u5149\u5408\u7406', '\u6b63\u4f8b\u5e94\u5224\u5e03\u5149\u5408\u7406\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['issues'] == [], '\u6b63\u4f8b\u4e0d\u5e94\u6709\u95ee\u9898\u9879\uff0c\u5b9e\u4e3a %s' % r1['issues'])

    # 2 \u53cd\u4f8b\uff1a\u80cc\u540e\u6709\u7a97
    r2 = setup_check(dict(good, window_behind=True))
    ck(r2['level'] == '\u5e03\u5149\u6709\u660e\u663e\u95ee\u9898', '\u80cc\u540e\u6709\u7a97\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck(any(i['item'] == '\u5149\u6e90\u65b9\u4f4d' for i in r2['issues']), '\u5e94\u70b9\u540d\u5149\u6e90\u65b9\u4f4d')

    # 3 \u53cd\u4f8b\uff1a\u4e3b\u5149\u5728\u6b63\u540e\u65b9
    r3 = setup_check(dict(good, key_angle_deg=170))
    ck(any(i['item'] == '\u5149\u6e90\u65b9\u4f4d' for i in r3['issues']), '\u4e3b\u5149 170 \u5ea6\u5e94\u5224\u6b63\u540e\u65b9\u5149\u6e90')

    # 4 \u53cd\u4f8b\uff1a\u53ea\u6709\u9876\u5149
    r4 = setup_check(dict(good, top_light_only=True))
    ck(any(i['item'] == '\u9876\u5149' for i in r4['issues']), '\u53ea\u6709\u9876\u5149\u5e94\u5224\u4e25\u91cd')
    ck(r4['level'] == '\u5e03\u5149\u6709\u660e\u663e\u95ee\u9898', '\u53ea\u6709\u9876\u5149\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r4['level'])

    # 5 \u53cd\u4f8b\uff1a\u7167\u5ea6\u4e0d\u8db3\u4e0e\u8fb9\u754c
    r5 = setup_check(dict(good, key_lux=150))
    ck(any(i['item'] == '\u4e3b\u5149\u7167\u5ea6' and i['sev'] == 3 for i in r5['issues']),
       '150 \u52d2\u514b\u65af\u5e94\u5224\u4e25\u91cd')
    ck(any(i['item'] == '\u4e3b\u5149\u7167\u5ea6' and i['sev'] == 2
           for i in setup_check(dict(good, key_lux=450))['issues']),
       '450 \u52d2\u514b\u65af\u5e94\u5224\u53ef\u6539\u8fdb')
    ck(setup_check(dict(good, key_lux=600))['issues'] == [], '600 \u52d2\u514b\u65af\u8fb9\u754c\u5e94\u5408\u683c')
    ck(setup_check(dict(good, key_lux=300))['level'] != '\u5e03\u5149\u6709\u660e\u663e\u95ee\u9898',
       '300 \u52d2\u514b\u65af\u8fb9\u754c\u4e0d\u5e94\u5224\u4e25\u91cd')

    # 6 \u53cd\u4f8b\uff1a\u8272\u6e29\u6df7\u7528
    r6 = setup_check(dict(good, temp_consistent=False))
    ck(any(i['item'] == '\u8272\u6e29' for i in r6['issues']), '\u8272\u6e29\u6df7\u7528\u5e94\u5224\u4e25\u91cd')
    ck(r6['level'] == '\u5e03\u5149\u6709\u660e\u663e\u95ee\u9898', '\u8272\u6e29\u6df7\u7528\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r6['level'])

    # 7 \u53cd\u4f8b\uff1a\u4e3b\u5149\u4f4e\u4e8e\u89c6\u7ebf
    r7 = setup_check(dict(good, key_height='below'))
    ck(any(i['item'] == '\u4e3b\u5149\u9ad8\u5ea6' for i in r7['issues']), '\u4e3b\u5149\u4f4e\u4e8e\u89c6\u7ebf\u5e94\u5224\u4e25\u91cd')
    ck(setup_check(dict(good, key_height='eye_level'))['level'] != '\u5e03\u5149\u6709\u660e\u663e\u95ee\u9898',
       '\u4e0e\u89c6\u7ebf\u9f50\u5e73\u4e0d\u5e94\u5224\u4e25\u91cd')

    # 8 \u53cd\u4f8b\uff1a\u6b63\u9762\u96f6\u89d2\u5ea6\u76f4\u6253
    r8 = setup_check(dict(good, key_angle_deg=5))
    ck(any(i['item'] == '\u4e3b\u5149\u89d2\u5ea6' and i['sev'] == 3 for i in r8['issues']),
       '5 \u5ea6\u76f4\u6253\u5e94\u5224\u4e25\u91cd')
    ck(any(i['item'] == '\u4e3b\u5149\u89d2\u5ea6'
           for i in setup_check(dict(good, key_angle_deg=20))['issues']),
       '20 \u5ea6\u5e94\u63d0\u793a\u504f\u5c0f')
    ck(setup_check(dict(good, key_angle_deg=30))['issues'] == [], '30 \u5ea6\u8fb9\u754c\u5e94\u5408\u683c')
    ck(setup_check(dict(good, key_angle_deg=60))['issues'] == [], '60 \u5ea6\u8fb9\u754c\u5e94\u5408\u683c')
    ck(any(i['item'] == '\u4e3b\u5149\u89d2\u5ea6' for i in setup_check(dict(good, key_angle_deg=80))['issues']),
       '80 \u5ea6\u5e94\u63d0\u793a\u53e6\u4e00\u4fa7\u5168\u9ed1')

    # 9 \u53cd\u4f8b\uff1a\u6234\u773c\u955c\u4e14\u89d2\u5ea6\u8fc7\u5c0f
    r9 = setup_check(dict(good, glasses=True, key_angle_deg=20))
    ck(any(i['item'] == '\u773c\u955c\u53cd\u5149' for i in r9['issues']), '\u6234\u773c\u955c 20 \u5ea6\u5e94\u5224\u4e25\u91cd')
    ck(r9['level'] == '\u5e03\u5149\u6709\u660e\u663e\u95ee\u9898', '\u773c\u955c\u53cd\u5149\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r9['level'])
    ck(not any(i['item'] == '\u773c\u955c\u53cd\u5149'
               for i in setup_check(dict(good, glasses=True, key_angle_deg=45))['issues']),
       '\u6234\u773c\u955c 45 \u5ea6\u4e0d\u5e94\u62a5\u53cd\u5149')
    ck(any(i['item'] == '\u773c\u955c\u53cd\u5149'
           for i in setup_check(dict(good, glasses=True, key_angle_deg=10))['issues']),
       '\u6234\u773c\u955c 10 \u5ea6\u540c\u65f6\u547d\u4e2d\u76f4\u6253\u4e0e\u53cd\u5149')

    # 10 \u53cd\u4f8b\uff1a\u8f85\u5149\u6bd4\u4f8b
    ck(any(i['item'] == '\u8f85\u5149\u6bd4\u4f8b' for i in setup_check(dict(good, fill_ratio=0.1))['issues']),
       '\u8f85\u5149 0.1 \u5e94\u63d0\u793a\u6697\u90e8\u6b7b\u9ed1')
    ck(any(i['item'] == '\u8f85\u5149\u6bd4\u4f8b' for i in setup_check(dict(good, fill_ratio=0.25))['issues']),
       '\u8f85\u5149 0.25 \u5e94\u63d0\u793a\u504f\u5f31')
    ck(any(i['item'] == '\u8f85\u5149\u6bd4\u4f8b' for i in setup_check(dict(good, fill_ratio=1.2))['issues']),
       '\u8f85\u5149 1.2 \u5e94\u63d0\u793a\u8fc7\u5f3a')
    ck(setup_check(dict(good, fill_ratio=0.3))['issues'] == [], '0.3 \u8fb9\u754c\u5e94\u5408\u683c')
    ck(setup_check(dict(good, fill_ratio=0.7))['issues'] == [], '0.7 \u8fb9\u754c\u5e94\u5408\u683c')

    # 11 \u53cd\u4f8b\uff1a\u65e0\u8f6e\u5ed3\u5149\u3001\u65e0\u80cc\u666f\u5149\u3001\u8d34\u5899
    ck(any(i['item'] == '\u8f6e\u5ed3\u5149' for i in setup_check(dict(good, backlight=False))['issues']),
       '\u65e0\u8f6e\u5ed3\u5149\u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u80cc\u666f\u5149' for i in setup_check(dict(good, bg_light=False))['issues']),
       '\u65e0\u80cc\u666f\u5149\u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u4eba\u7269\u8ddd\u79bb'
           for i in setup_check(dict(good, too_close_to_wall=True))['issues']),
       '\u8d34\u5899\u5e94\u63d0\u793a')

    # 12 \u53cd\u4f8b\uff1a\u5149\u6bd4
    ck(any(i['item'] == '\u5149\u6bd4' for i in setup_check(dict(good, ambient_lux=400))['issues']),
       '\u73af\u5883 400 \u52d2\u514b\u65af\u5e94\u63d0\u793a\u4e3b\u4f53\u4e0d\u7a81\u51fa')
    ck(any(i['item'] == '\u5149\u6bd4' for i in setup_check(dict(good, ambient_lux=10))['issues']),
       '\u73af\u5883 10 \u52d2\u514b\u65af\u5e94\u63d0\u793a\u592a\u6697')
    ck(setup_check(dict(good, ambient_lux=150))['issues'] == [], '\u73af\u5883 150 \u52d2\u514b\u65af\u5e94\u5408\u683c')

    # 13 \u6392\u5e8f\u65b9\u5411\uff1a\u4e25\u91cd\u9879\u6392\u6700\u524d
    r13 = setup_check(dict(good, window_behind=True, backlight=False, fill_ratio=1.2))
    ck(r13['issues'][0]['sev'] == 3, '\u4e25\u91cd\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r13['issues'][0]['sev'])
    ck(r13['issues'][0]['item'] == '\u5149\u6e90\u65b9\u4f4d', '\u9996\u4e2a\u5e94\u662f\u5149\u6e90\u65b9\u4f4d\uff0c\u5b9e\u4e3a %s' % r13['issues'][0]['item'])
    ck(r13['issues'][-1]['sev'] == 2, '\u672b\u4f4d\u5e94\u662f\u53ef\u6539\u8fdb\u9879')

    # 14 \u5224\u5b9a\u987a\u5e8f\uff1a\u6709\u4e25\u91cd\u9879\u65f6\u4e0d\u56e0\u7f3a\u4fe1\u606f\u5224\u5f85\u786e\u8ba4
    r14 = setup_check({'name': '\u53ea\u586b\u9876\u5149', 'top_light_only': True})
    ck(r14['level'] == '\u5e03\u5149\u6709\u660e\u663e\u95ee\u9898', '\u7f3a\u5176\u4ed6\u9879\u4f46\u6709\u4e25\u91cd\u9879\u4e0d\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r14['level'])
    r14b = setup_check({'name': '\u53ea\u586b\u89d2\u5ea6', 'key_angle_deg': 45, 'key_height': 'above_eye'})
    ck(r14b['level'] == '\u5f85\u786e\u8ba4', '\u672a\u586b\u7167\u5ea6\u4e0e\u8f85\u5149\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r14b['level'])

    # 15 \u6c47\u603b\u4e0e\u6574\u6539\u987a\u5e8f
    r15 = calc({'setups': [good,
                           dict(good, name='\u80cc\u540e\u6709\u7a97', window_behind=True),
                           dict(good, name='\u65e0\u8f6e\u5ed3\u5149', backlight=False)]})
    ck(r15['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u8c03\u7684\u5e03\u5149', '\u6709\u4e25\u91cd\u9879\u5e94\u5224\u9700\u8981\u91cd\u8c03\uff0c\u5b9e\u4e3a %s' % r15['overall'])
    ck(r15['n_bad'] == 1, '\u4e25\u91cd\u9879\u5e94\u4e3a 1 \u5957\uff0c\u5b9e\u4e3a %d' % r15['n_bad'])
    ck(r15['fix_order'][0] == '\u80cc\u540e\u6709\u7a97', '\u4e25\u91cd\u9879\u5e94\u5148\u6539\uff0c\u5b9e\u4e3a %s' % r15['fix_order'])
    ck(r15['fix_order'][1] == '\u65e0\u8f6e\u5ed3\u5149', '\u53ef\u6539\u8fdb\u9879\u6392\u5176\u540e\uff0c\u5b9e\u4e3a %s' % r15['fix_order'])

    # 16 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'setups': [dict(good, window_behind=True)]})
    r16 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r16['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u8c03\u7684\u5e03\u5149', 'BOM \u5b57\u7b26\u4e32\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r16['overall'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_c7.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'setups': [dict(good, name='\u5e26BOM', top_light_only=True)]}))
    try:
        r16b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r16b['rows'][0]['name'] == '\u5e26BOM', 'BOM \u6587\u4ef6\u9996\u4e2a key \u5e94\u89e3\u6790\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r16b['rows'][0]['name'])
        ck(r16b['n_bad'] == 1, '\u53ea\u6709\u9876\u5149\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %d' % r16b['n_bad'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 17 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({}, '\u7f3a setups'),
        ({'setups': []}, 'setups \u7a7a\u5217\u8868'),
        ({'setups': [dict(good, key_lux='abc')]}, '\u7167\u5ea6\u975e\u6570\u5b57'),
        ({'setups': [dict(good, key_height='\u5934\u9876')]}, '\u672a\u77e5\u9ad8\u5ea6'),
        ({'setups': [dict(good, scene='\u6237\u5916')]}, '\u672a\u77e5\u573a\u666f'),
        ({'setups': [dict(good, fill_ratio=-0.5)]}, '\u6bd4\u4f8b\u4e3a\u8d1f'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b17 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 18 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r15)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u4e09\u70b9\u5e03\u5149', '\u9010\u5957\u5224\u5b9a', '\u4e3b\u5149\u9ad8\u5ea6', '\u4e09\u79cd\u573a\u666f\u65b9\u6848', '\u9608\u503c',
                '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(HEIGHTS) == 3, '\u4e3b\u5149\u9ad8\u5ea6\u5e94 3 \u6863')
    ck(len([h for h in HEIGHTS if not h[2]]) == 1, '\u4e0d\u5408\u683c\u9ad8\u5ea6\u5e94 1 \u6863')
    ck(len(SCENES) == 3, '\u573a\u666f\u65b9\u6848\u5e94 3 \u79cd')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u6b63\u4f8b/\u80cc\u540e\u6709\u7a97\u53cd\u4f8b/\u4e3b\u5149\u6b63\u540e\u65b9\u53cd\u4f8b/\u53ea\u6709\u9876\u5149\u53cd\u4f8b/'
        '\u7167\u5ea6\u4e0e\u8fb9\u754c/\u8272\u6e29\u6df7\u7528\u53cd\u4f8b/\u4e3b\u5149\u4f4e\u4e8e\u89c6\u7ebf\u53cd\u4f8b/\u6b63\u9762\u76f4\u6253\u4e0e\u89d2\u5ea6\u8fb9\u754c/\u773c\u955c\u53cd\u5149\u53cd\u4f8b/'
        '\u8f85\u5149\u6bd4\u4f8b\u4e0a\u4e0b\u754c/\u8f6e\u5ed3\u5149\u80cc\u666f\u5149\u8d34\u5899/\u5149\u6bd4/\u4e25\u91cd\u9879\u6392\u5e8f/\u5224\u5b9a\u987a\u5e8f/\u6c47\u603b\u6574\u6539\u987a\u5e8f/'
        'BOM\u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u76f4\u64ad\u5e03\u5149\u6838\u67e5')
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
