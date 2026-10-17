# -*- coding: utf-8 -*-
"""\u8bc1\u4ef6\u7167\u81ea\u67e5\uff1a\u6838\u5206\u8fa8\u7387\u3001\u50cf\u7d20\u5c3a\u5bf8\u3001\u5e95\u8272\u3001\u6784\u56fe\u6bd4\u4f8b\u3001\u4e94\u5b98\u7740\u88c5\u4e0e\u62cd\u6444\u65f6\u95f4\u3002

\u7528\u6cd5:
  python id_photo_check.py --file photo.json [--out result.md] [--format json]
  python id_photo_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u5e38\u89c1\u89c4\u683c: (\u952e, \u4e2d\u6587\u540d, \u6beb\u7c73\u5bbd, \u6beb\u7c73\u9ad8, 300dpi \u50cf\u7d20\u5bbd, 300dpi \u50cf\u7d20\u9ad8, \u5141\u8bb8\u5e95\u8272, \u5e38\u89c1\u7528\u9014)
SPECS = [
    ('one_inch', '\u4e00\u5bf8', 25, 35, 295, 413, ['white', 'blue', 'red'], '\u793e\u4fdd\u3001\u8d44\u683c\u62a5\u540d\u3001\u6863\u6848\u8868'),
    ('two_inch', '\u4e8c\u5bf8', 35, 49, 413, 579, ['white', 'blue', 'red'], '\u7b80\u5386\u3001\u8d44\u683c\u8bc1\u4e66\u3001\u90e8\u5206\u7b7e\u8bc1'),
    ('small_two', '\u5c0f\u4e8c\u5bf8', 35, 45, 413, 531, ['white', 'blue'], '\u90e8\u5206\u8003\u8bd5\u62a5\u540d'),
    ('passport', '\u62a4\u7167\u4e0e\u7b7e\u8bc1\u5e38\u7528', 33, 48, 390, 567, ['white'], '\u51fa\u5165\u5883\u8bc1\u4ef6\u3001\u591a\u6570\u56fd\u5bb6\u7b7e\u8bc1'),
]

# \u5e95\u8272: (\u952e, \u4e2d\u6587\u540d)
BACKGROUNDS = [
    ('white', '\u767d\u5e95'),
    ('blue', '\u84dd\u5e95'),
    ('red', '\u7ea2\u5e95'),
]

# \u8868\u60c5: (\u952e, \u4e2d\u6587\u540d, \u662f\u5426\u9732\u9f7f)
EXPRESSIONS = [
    ('neutral', '\u4e2d\u6027\u8868\u60c5\uff0c\u53cc\u5507\u81ea\u7136\u95ed\u5408', False),
    ('slight', '\u5fae\u5fae\u62bf\u5634', False),
    ('teeth', '\u9732\u9f7f\u5fae\u7b11', True),
]

# \u9608\u503c
TOL = {
    'dpi_min': 300,          # \u6700\u4f4e\u5206\u8fa8\u7387
    'px_tol': 3,             # \u50cf\u7d20\u5c3a\u5bf8\u5bb9\u5dee
    'face_min': 0.70,        # \u5934\u90e8\u5360\u6bd4\u4e0b\u9650
    'face_max': 0.80,        # \u5934\u90e8\u5360\u6bd4\u4e0a\u9650
    'top_min': 0.03,         # \u5934\u9876\u7559\u767d\u4e0b\u9650
    'top_max': 0.10,         # \u5934\u9876\u7559\u767d\u4e0a\u9650
    'eye_min': 0.45,         # \u773c\u775b\u6c34\u5e73\u4f4d\u7f6e\u4e0b\u9650
    'eye_max': 0.65,         # \u773c\u775b\u6c34\u5e73\u4f4d\u7f6e\u4e0a\u9650
    'months_max': 6,         # \u62cd\u6444\u65f6\u95f4\u4e0a\u9650\uff08\u6708\uff09
    'kb_min': 10,            # \u6587\u4ef6\u5927\u5c0f\u4e0b\u9650\uff08KB\uff09
    'kb_max': 300,           # \u6587\u4ef6\u5927\u5c0f\u4e0a\u9650\uff08KB\uff09
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


def shot_check(shot):
    if not isinstance(shot, dict):
        raise ValueError('photos \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
    name = str(shot.get('name') or '\u672a\u547d\u540d').strip()
    spec = _row(SPECS, shot.get('spec'), 'spec')
    bg = _row(BACKGROUNDS, shot.get('bg'), 'bg')
    expr = _row(EXPRESSIONS, shot.get('expression'), 'expression')
    px_w = _f(shot, 'px_w')
    px_h = _f(shot, 'px_h')
    dpi = _f(shot, 'dpi')
    face = _f(shot, 'face_height_ratio')
    top = _f(shot, 'head_top_margin')
    eye = _f(shot, 'eye_line_ratio')
    kb = _f(shot, 'file_kb')
    months = _f(shot, 'months_since')

    issues = []
    misses = []

    if spec is None:
        misses.append('\u89c4\u683c')

    # \u4e25\u91cd\u9879 1\uff1a\u5206\u8fa8\u7387
    if dpi is None:
        misses.append('\u5206\u8fa8\u7387')
    elif dpi < TOL['dpi_min']:
        issues.append({
            'sev': 3, 'item': '\u5206\u8fa8\u7387',
            'detail': '%.0f dpi\uff0c\u4f4e\u4e8e %d dpi' % (dpi, TOL['dpi_min']),
            'why': '\u5206\u8fa8\u7387\u4e0d\u8db3\u4f1a\u76f4\u63a5\u88ab\u53d7\u7406\u7cfb\u7edf\u9000\u56de\uff1b'
                   '\u4ece\u76f8\u518c\u622a\u56fe\u901a\u5e38\u53ea\u6709 72 dpi\uff0c\u5fc5\u987b\u6309\u89c4\u683c\u91cd\u65b0\u5bfc\u51fa\u6216\u62cd\u6444',
        })

    # \u4e25\u91cd\u9879 2\uff1a\u50cf\u7d20\u5c3a\u5bf8
    if px_w is None or px_h is None:
        misses.append('\u50cf\u7d20\u5c3a\u5bf8')
    elif spec is not None:
        want_w, want_h = spec[4], spec[5]
        if abs(px_w - want_w) > TOL['px_tol'] or abs(px_h - want_h) > TOL['px_tol']:
            issues.append({
                'sev': 3, 'item': '\u50cf\u7d20\u5c3a\u5bf8',
                'detail': '\u5f53\u524d %.0f \u00d7 %.0f\uff0c%s \u8981\u6c42 %d \u00d7 %d'
                          % (px_w, px_h, spec[1], want_w, want_h),
                'why': '\u50cf\u7d20\u5c3a\u5bf8\u4e0d\u7b26\u4f1a\u88ab\u7cfb\u7edf\u76f4\u63a5\u62d2\u6536\uff1b'
                       '\u50cf\u7d20 = \u6beb\u7c73 \u00f7 25.4 \u00d7 dpi\uff0c\u6309\u53d7\u7406\u673a\u6784\u516c\u5e03\u7684\u6570\u503c\u5bfc\u51fa',
            })

    # \u4e25\u91cd\u9879 3\uff1a\u5e95\u8272
    if bg is None:
        misses.append('\u5e95\u8272')
    elif spec is not None and norm(bg[0]) not in spec[6]:
        issues.append({
            'sev': 3, 'item': '\u5e95\u8272',
            'detail': '%s\uff0c%s \u901a\u5e38\u53ea\u63a5\u53d7 %s'
                      % (bg[1], spec[1], '\u3001'.join(_bg_name(x) for x in spec[6])),
            'why': '\u5e95\u8272\u4e0d\u7b26\u4f1a\u88ab\u53d7\u7406\u673a\u6784\u9000\u56de\uff1b\u62cd\u6444\u65f6\u5c31\u9009\u5bf9\u5e95\u8272\uff0c\u6bd4\u540e\u671f\u62a0\u56fe\u6362\u5e95\u53ef\u9760',
        })

    # \u4e25\u91cd\u9879 4\uff1a\u7709\u6bdb\u4e0e\u8033\u6735
    if shot.get('hair_cover_brow'):
        issues.append({
            'sev': 3, 'item': '\u7709\u6bdb',
            'detail': '\u5934\u53d1\u906e\u6321\u7709\u6bdb',
            'why': '\u7709\u6bdb\u5fc5\u987b\u5b8c\u6574\u9732\u51fa\uff0c\u906e\u6321\u5373\u88ab\u9000\u56de\uff1b\u5218\u6d77\u68b3\u4e0a\u53bb\u6216\u7528\u53d1\u5939\u56fa\u5b9a',
        })
    if shot.get('ears_visible') is False:
        issues.append({
            'sev': 3, 'item': '\u8033\u6735',
            'detail': '\u8033\u6735\u672a\u9732\u51fa',
            'why': '\u591a\u6570\u7528\u9014\u8981\u6c42\u9732\u51fa\u8033\u6735\uff1b\u957f\u53d1\u522b\u5230\u8033\u540e\u518d\u62cd',
        })

    # \u4e25\u91cd\u9879 5\uff1a\u5e3d\u5b50\u5934\u9970
    if shot.get('headwear'):
        issues.append({
            'sev': 3, 'item': '\u5e3d\u5b50\u5934\u9970',
            'detail': '\u4f69\u6234\u4e86\u5e3d\u5b50\u6216\u5934\u9970',
            'why': '\u8bc1\u4ef6\u7167\u4e0d\u5f97\u4f69\u6234\u5e3d\u5b50\u5934\u9970\uff08\u5b97\u6559\u4e0e\u533b\u7597\u539f\u56e0\u6309\u53d7\u7406\u673a\u6784\u8981\u6c42\u529e\u7406\uff09\uff1b'
                   '\u62cd\u6444\u524d\u53d6\u4e0b\u5e3d\u5b50\u3001\u53d1\u7b8d\u3001\u5938\u5f20\u53d1\u9970',
        })

    # \u4e25\u91cd\u9879 6\uff1a\u62cd\u6444\u65f6\u95f4
    if months is None:
        misses.append('\u62cd\u6444\u65f6\u95f4')
    elif months > TOL['months_max']:
        issues.append({
            'sev': 3, 'item': '\u62cd\u6444\u65f6\u95f4',
            'detail': '\u8ddd\u62cd\u6444\u5df2 %.0f \u4e2a\u6708\uff0c\u8d85\u8fc7 %d \u4e2a\u6708' % (months, TOL['months_max']),
            'why': '\u8bc1\u4ef6\u7167\u901a\u5e38\u8981\u6c42\u8fd1 6 \u4e2a\u6708\u5185\u62cd\u6444\uff0c\u8d85\u671f\u9700\u91cd\u62cd',
        })

    # \u4e25\u91cd\u9879 7\uff1a\u6587\u4ef6\u5927\u5c0f
    if kb is None:
        misses.append('\u6587\u4ef6\u5927\u5c0f')
    elif not TOL['kb_min'] <= kb <= TOL['kb_max']:
        why = ('\u5c0f\u4e8e %d KB \u901a\u5e38\u753b\u8d28\u4e0d\u8db3' % TOL['kb_min'] if kb < TOL['kb_min']
               else '\u5927\u4e8e %d KB \u591a\u6570\u62a5\u540d\u7cfb\u7edf\u4f20\u4e0d\u4e0a\u53bb' % TOL['kb_max'])
        issues.append({
            'sev': 3, 'item': '\u6587\u4ef6\u5927\u5c0f',
            'detail': '%.0f KB\uff0c\u5408\u683c\u533a\u95f4 %d \u5230 %d KB' % (kb, TOL['kb_min'], TOL['kb_max']),
            'why': why,
        })

    # \u4e25\u91cd\u9879 8\uff1a\u7ea2\u773c
    if shot.get('red_eye'):
        issues.append({
            'sev': 3, 'item': '\u7ea2\u773c',
            'detail': '\u5b58\u5728\u7ea2\u773c',
            'why': '\u7ea2\u773c\u4f1a\u88ab\u76f4\u63a5\u9000\u56de\uff1b\u5173\u6389\u95ea\u5149\u706f\uff0c\u6539\u7528\u4e24\u76cf\u5e38\u4eae\u706f\u4ece\u5de6\u53f3\u524d\u65b9\u8865\u5149',
        })

    # \u4e25\u91cd\u9879 9\uff1a\u670d\u88c5\u4e0e\u5e95\u8272\u5bf9\u6bd4
    if shot.get('clothes_contrast') is False:
        issues.append({
            'sev': 3, 'item': '\u670d\u88c5\u914d\u8272',
            'detail': '\u670d\u88c5\u989c\u8272\u4e0e\u5e95\u8272\u7f3a\u4e4f\u5bf9\u6bd4',
            'why': '\u767d\u5e95\u7a7f\u767d\u886c\u886b\u4f1a\u8ba9\u80a9\u8180\u4e0e\u80cc\u666f\u7cca\u5728\u4e00\u8d77\uff1b\u6362\u6210\u4e0e\u5e95\u8272\u6709\u660e\u786e\u4fdd\u6301\u5bf9\u6bd4\u7684\u989c\u8272',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u5934\u90e8\u5360\u6bd4
    if face is None:
        misses.append('\u5934\u90e8\u5360\u6bd4')
    elif not TOL['face_min'] <= face <= TOL['face_max']:
        why = ('\u5c0f\u4e8e %.2f \u4eba\u663e\u5f97\u592a\u5c0f\u3001\u753b\u9762\u7a7a' % TOL['face_min'] if face < TOL['face_min']
               else '\u5927\u4e8e %.2f \u5bb9\u6613\u5207\u5230\u4e0b\u5df4\u6216\u9876\u5f97\u592a\u6ee1' % TOL['face_max'])
        issues.append({
            'sev': 2, 'item': '\u5934\u90e8\u5360\u6bd4',
            'detail': '%.2f\uff0c\u5408\u683c\u533a\u95f4 %.2f \u5230 %.2f' % (face, TOL['face_min'], TOL['face_max']),
            'why': why,
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u5934\u9876\u7559\u767d
    if top is None:
        misses.append('\u5934\u9876\u7559\u767d')
    elif not TOL['top_min'] <= top <= TOL['top_max']:
        why = ('\u5c0f\u4e8e %.2f \u9876\u5f97\u592a\u6ee1\u751a\u81f3\u88ab\u5224\u5934\u9876\u8fc7\u6ee1' % TOL['top_min'] if top < TOL['top_min']
               else '\u5927\u4e8e %.2f \u4eba\u663e\u5c0f\u3001\u753b\u9762\u677e\u6563' % TOL['top_max'])
        issues.append({
            'sev': 2, 'item': '\u5934\u9876\u7559\u767d',
            'detail': '%.2f\uff0c\u5408\u683c\u533a\u95f4 %.2f \u5230 %.2f' % (top, TOL['top_min'], TOL['top_max']),
            'why': why,
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u773c\u775b\u4f4d\u7f6e
    if eye is None:
        misses.append('\u773c\u775b\u6c34\u5e73\u4f4d\u7f6e')
    elif not TOL['eye_min'] <= eye <= TOL['eye_max']:
        issues.append({
            'sev': 2, 'item': '\u773c\u775b\u4f4d\u7f6e',
            'detail': '%.2f\uff0c\u5408\u683c\u533a\u95f4 %.2f \u5230 %.2f' % (eye, TOL['eye_min'], TOL['eye_max']),
            'why': '\u773c\u775b\u592a\u9ad8\u50cf\u4fef\u62cd\uff0c\u592a\u4f4e\u663e\u5f97\u6ca1\u7cbe\u795e\uff1b\u955c\u5934\u9ad8\u5ea6\u4e0e\u773c\u775b\u9f50\u5e73',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u80cc\u666f
    if shot.get('bg_even') is False:
        issues.append({
            'sev': 2, 'item': '\u80cc\u666f\u5747\u5300\u5ea6',
            'detail': '\u80cc\u666f\u4e0d\u5747\u5300\u6216\u6709\u8936\u76b1\u6742\u7269',
            'why': '\u80cc\u666f\u5fc5\u987b\u7eaf\u51c0\u5747\u5300\uff1b\u6362\u5e72\u51c0\u5899\u9762\u6216\u628a\u5e03\u7ef7\u5e73',
        })
    if shot.get('shadow_on_bg'):
        issues.append({
            'sev': 2, 'item': '\u80cc\u666f\u9634\u5f71',
            'detail': '\u80cc\u666f\u4e0a\u6709\u9634\u5f71',
            'why': '\u4eba\u79bb\u5899\u592a\u8fd1\u4f1a\u628a\u5f71\u5b50\u6295\u5728\u5899\u4e0a\uff1b\u79bb\u5899\u81f3\u5c11 0.5 \u7c73\uff0c'
                   '\u5e76\u628a\u4e24\u76cf\u706f\u79fb\u5230\u5de6\u53f3\u524d\u65b9 45 \u5ea6',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u773c\u955c
    if shot.get('glasses'):
        issues.append({
            'sev': 2, 'item': '\u773c\u955c',
            'detail': '\u6234\u7740\u773c\u955c',
            'why': '\u591a\u6570\u7528\u9014\u8981\u6c42\u4e0d\u6234\u773c\u955c\uff1b\u5141\u8bb8\u6234\u65f6\u955c\u7247\u4e0d\u5f97\u53cd\u5149\u3001\u4e0d\u5f97\u906e\u6321\u773c\u775b\u3001'
                   '\u955c\u6846\u4e0d\u5f97\u906e\u7709\u6bdb\uff0c\u5efa\u8bae\u76f4\u63a5\u6458\u6389\u62cd',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u8868\u60c5
    if expr is None:
        misses.append('\u8868\u60c5')
    elif expr[2]:
        issues.append({
            'sev': 2, 'item': '\u8868\u60c5',
            'detail': '%s' % expr[1],
            'why': '\u591a\u6570\u8bc1\u4ef6\u7167\u8981\u6c42\u4e2d\u6027\u8868\u60c5\u3001\u53cc\u5507\u81ea\u7136\u95ed\u5408\uff0c\u9732\u9f7f\u7b11\u4f1a\u88ab\u9000\u56de',
        })

    # \u53ef\u6539\u8fdb\u9879\uff1a\u80a9\u8180
    if shot.get('shoulders_visible') is False:
        issues.append({
            'sev': 2, 'item': '\u80a9\u8180',
            'detail': '\u80a9\u8180\u672a\u62cd\u5168\u6216\u4e24\u4fa7\u4e0d\u5bf9\u79f0',
            'why': '\u534a\u8eab\u8bc1\u4ef6\u7167\u901a\u5e38\u8981\u6c42\u9732\u51fa\u80a9\u7ebf\u4e14\u4e24\u4fa7\u5bf9\u79f0\uff1b\u9000\u8fdc\u4e00\u70b9\uff0c'
                   '\u8ba9\u8138\u90e8\u4e2d\u8f74\u5bf9\u51c6\u7f51\u683c\u7ad6\u4e2d\u7ebf',
        })

    issues.sort(key=lambda r: -r['sev'])

    if any(i['sev'] == 3 for i in issues):
        level = '\u5b58\u5728\u9000\u56de\u98ce\u9669'
    elif issues:
        level = '\u6709\u53ef\u6539\u8fdb\u9879'
    elif misses:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u7b26\u5408\u8981\u6c42'

    return {
        'name': name, 'level': level, 'issues': issues, 'misses': misses,
        'spec': spec[1] if spec else None, 'bg': bg[1] if bg else None,
        'px_w': px_w, 'px_h': px_h, 'dpi': dpi, 'kb': kb, 'months': months,
    }


def _bg_name(key):
    for k, n in BACKGROUNDS:
        if k == key:
            return n
    return key


def calc(data):
    photos = data.get('photos')
    if photos is None:
        raise ValueError('\u8f93\u5165\u7f3a\u5c11 photos \u5217\u8868')
    if not isinstance(photos, list) or not photos:
        raise ValueError('photos \u5fc5\u987b\u662f\u975e\u7a7a\u5217\u8868')
    rows = [shot_check(p) for p in photos]
    n_bad = len([r for r in rows if r['level'] == '\u5b58\u5728\u9000\u56de\u98ce\u9669'])
    n_mid = len([r for r in rows if r['level'] == '\u6709\u53ef\u6539\u8fdb\u9879'])
    n_unk = len([r for r in rows if r['level'] == '\u5f85\u786e\u8ba4'])
    if n_bad:
        overall = '\u5b58\u5728\u4f1a\u88ab\u9000\u56de\u7684\u8bc1\u4ef6\u7167'
    elif n_mid:
        overall = '\u5b58\u5728\u53ef\u6539\u8fdb\u7684\u8bc1\u4ef6\u7167'
    elif n_unk:
        overall = '\u5f85\u786e\u8ba4'
    else:
        overall = '\u5168\u90e8\u7b26\u5408\u8981\u6c42'

    def _sev(r):
        return max([i['sev'] for i in r['issues']], default=0)

    order = sorted(rows, key=lambda r: (-_sev(r), -len(r['issues']), r['name']))
    return {
        'overall': overall, 'rows': rows,
        'n_bad': n_bad, 'n_mid': n_mid, 'n_unk': n_unk,
        'n_ok': len(rows) - n_bad - n_mid - n_unk,
        'fix_order': [r['name'] for r in order if r['issues']],
        'specs': [{'key': k, 'name': n, 'mm': '%d x %d' % (w, h),
                   'px': '%d x %d' % (pw, ph), 'bg': [_bg_name(x) for x in bgs],
                   'use': u}
                  for k, n, w, h, pw, ph, bgs, u in SPECS],
        'backgrounds': [{'key': k, 'name': n} for k, n in BACKGROUNDS],
        'expressions': [{'key': k, 'name': n, 'teeth': t} for k, n, t in EXPRESSIONS],
        'tol': dict(TOL),
    }


def render_md(r):
    L = []
    L.append('# \u8bc1\u4ef6\u7167\u81ea\u67e5')
    L.append('')
    L.append('> \u4e0d\u540c\u7528\u9014\u4e0e\u53d7\u7406\u673a\u6784\u7684\u8981\u6c42\u5dee\u5f02\u5f88\u5927\uff0c\u672c\u8868\u4e3a\u5e38\u89c1\u503c\uff0c**\u6700\u7ec8\u4ee5\u53d7\u7406\u673a\u6784\u516c\u5e03\u7684\u8981\u6c42\u4e3a\u51c6**\u3002')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['overall'])
    L.append('')
    L.append('| \u7c7b\u522b | \u5f20\u6570 |')
    L.append('|---|---|')
    L.append('| \u5b58\u5728\u9000\u56de\u98ce\u9669 | %d |' % r['n_bad'])
    L.append('| \u53ef\u6539\u8fdb | %d |' % r['n_mid'])
    L.append('| \u5f85\u786e\u8ba4 | %d |' % r['n_unk'])
    L.append('| \u7b26\u5408\u8981\u6c42 | %d |' % r['n_ok'])
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
        if row['spec']:
            L.append('- \u89c4\u683c\uff1a%s' % row['spec'])
        if row['px_w'] is not None and row['px_h'] is not None:
            L.append('- \u50cf\u7d20\uff1a%.0f \u00d7 %.0f' % (row['px_w'], row['px_h']))
        if row['dpi'] is not None:
            L.append('- \u5206\u8fa8\u7387\uff1a%.0f dpi' % row['dpi'])
        if row['bg']:
            L.append('- \u5e95\u8272\uff1a%s' % row['bg'])
        if row['kb'] is not None:
            L.append('- \u6587\u4ef6\u5927\u5c0f\uff1a%.0f KB' % row['kb'])
        if row['months'] is not None:
            L.append('- \u8ddd\u62cd\u6444\uff1a%.0f \u4e2a\u6708' % row['months'])
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
    L.append('## \u4e09\u3001\u5e38\u89c1\u89c4\u683c\uff08300 dpi\uff09')
    L.append('')
    L.append('| \u89c4\u683c | \u6beb\u7c73 | \u50cf\u7d20 | \u5141\u8bb8\u5e95\u8272 | \u5e38\u89c1\u7528\u9014 |')
    L.append('|---|---|---|---|---|')
    for s in r['specs']:
        L.append('| %s | %s | %s | %s | %s |' % (s['name'], s['mm'], s['px'],
                                                 '\u3001'.join(s['bg']), s['use']))
    L.append('')
    L.append('## \u56db\u3001\u9608\u503c')
    L.append('')
    L.append('| \u9879\u76ee | \u9608\u503c |')
    L.append('|---|---|')
    L.append('| \u5206\u8fa8\u7387 | \u4e0d\u4f4e\u4e8e %d dpi |' % r['tol']['dpi_min'])
    L.append('| \u5934\u90e8\u957f\u5ea6\u5360\u6bd4 | %.2f \u5230 %.2f |' % (r['tol']['face_min'], r['tol']['face_max']))
    L.append('| \u5934\u9876\u7559\u767d | %.2f \u5230 %.2f |' % (r['tol']['top_min'], r['tol']['top_max']))
    L.append('| \u773c\u775b\u6c34\u5e73\u4f4d\u7f6e | %.2f \u5230 %.2f |' % (r['tol']['eye_min'], r['tol']['eye_max']))
    L.append('| \u62cd\u6444\u65f6\u95f4 | \u4e0d\u8d85\u8fc7 %d \u4e2a\u6708 |' % r['tol']['months_max'])
    L.append('| \u6587\u4ef6\u5927\u5c0f | %d \u5230 %d KB |' % (r['tol']['kb_min'], r['tol']['kb_max']))
    L.append('')
    L.append('## \u4e94\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u5df2\u6838\u5bf9\u53d7\u7406\u673a\u6784\u516c\u5e03\u7684\u5177\u4f53\u50cf\u7d20\u3001\u5e95\u8272\u4e0e\u6587\u4ef6\u5927\u5c0f\u8981\u6c42')
    L.append('- [ ] \u5173\u6389\u4e86\u7f8e\u989c\u4e0e\u6ee4\u955c')
    L.append('- [ ] \u955c\u5934\u9ad8\u5ea6\u4e0e\u773c\u775b\u9f50\u5e73\uff0c\u8138\u90e8\u4e2d\u8f74\u5bf9\u51c6\u7f51\u683c\u7ad6\u4e2d\u7ebf')
    L.append('- [ ] \u7709\u6bdb\u8033\u6735\u9732\u51fa\uff0c\u6ca1\u6234\u5e3d\u5b50\u5934\u9970\uff0c\u6ca1\u6234\u773c\u955c')
    L.append('- [ ] \u80cc\u666f\u7eaf\u51c0\u5747\u5300\u3001\u65e0\u9634\u5f71\uff0c\u4eba\u79bb\u5899\u81f3\u5c11 0.5 \u7c73')
    L.append('- [ ] \u8fde\u62cd\u4e86 5 \u5230 10 \u5f20\uff0c\u653e\u5927\u68c0\u67e5\u77b3\u5b54\u6e05\u6670\u3001\u65e0\u7ea2\u773c')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    ok = {'name': '\u793e\u4fdd\u4e00\u5bf8', 'spec': 'one_inch', 'px_w': 295, 'px_h': 413, 'dpi': 300,
          'bg': 'white', 'face_height_ratio': 0.75, 'head_top_margin': 0.06,
          'eye_line_ratio': 0.55, 'file_kb': 45, 'months_since': 2,
          'hair_cover_brow': False, 'ears_visible': True, 'headwear': False,
          'red_eye': False, 'clothes_contrast': True, 'bg_even': True,
          'shadow_on_bg': False, 'glasses': False, 'expression': 'neutral',
          'shoulders_visible': True}

    # 1 \u6b63\u4f8b
    r1 = shot_check(ok)
    ck(r1['level'] == '\u7b26\u5408\u8981\u6c42', '\u6b63\u4f8b\u5e94\u5224\u7b26\u5408\u8981\u6c42\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['issues'] == [], '\u6b63\u4f8b\u4e0d\u5e94\u6709\u95ee\u9898\u9879\uff0c\u5b9e\u4e3a %s' % r1['issues'])

    # 2 \u53cd\u4f8b\uff1a\u5206\u8fa8\u7387\u4e0d\u8db3
    r2 = shot_check(dict(ok, dpi=72))
    ck(r2['level'] == '\u5b58\u5728\u9000\u56de\u98ce\u9669', '72 dpi \u5e94\u5224\u9000\u56de\u98ce\u9669\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck(any(i['item'] == '\u5206\u8fa8\u7387' for i in r2['issues']), '\u5e94\u70b9\u540d\u5206\u8fa8\u7387')
    ck(shot_check(dict(ok, dpi=300))['issues'] == [], '300 dpi \u8fb9\u754c\u5e94\u5408\u683c')

    # 3 \u53cd\u4f8b\uff1a\u50cf\u7d20\u5c3a\u5bf8\u4e0d\u7b26
    r3 = shot_check(dict(ok, px_w=200, px_h=280))
    ck(any(i['item'] == '\u50cf\u7d20\u5c3a\u5bf8' for i in r3['issues']), '\u50cf\u7d20\u4e0d\u7b26\u5e94\u5224\u9000\u56de\u98ce\u9669')
    ck(not any(i['item'] == '\u50cf\u7d20\u5c3a\u5bf8' for i in shot_check(dict(ok, px_w=297, px_h=415))['issues']),
       '3 \u50cf\u7d20\u5bb9\u5dee\u5185\u5e94\u5408\u683c')
    ck(any(i['item'] == '\u50cf\u7d20\u5c3a\u5bf8' for i in shot_check(dict(ok, px_w=299, px_h=413))['issues']),
       '\u8d85\u51fa\u5bb9\u5dee\u5e94\u4e0d\u5408\u683c')

    # 4 \u53cd\u4f8b\uff1a\u5e95\u8272\u4e0d\u7b26
    r4 = shot_check(dict(ok, spec='passport', px_w=390, px_h=567, bg='blue'))
    ck(any(i['item'] == '\u5e95\u8272' for i in r4['issues']), '\u62a4\u7167\u7528\u84dd\u5e95\u5e94\u5224\u9000\u56de\u98ce\u9669')
    ck(not any(i['item'] == '\u5e95\u8272' for i in shot_check(dict(ok, spec='two_inch',
                                                           px_w=413, px_h=579, bg='blue'))['issues']),
       '\u4e8c\u5bf8\u84dd\u5e95\u5e94\u5408\u683c')

    # 5 \u53cd\u4f8b\uff1a\u7709\u6bdb\u906e\u6321\u3001\u8033\u6735\u672a\u9732\u3001\u6234\u5e3d
    ck(any(i['item'] == '\u7709\u6bdb' for i in shot_check(dict(ok, hair_cover_brow=True))['issues']),
       '\u906e\u7709\u5e94\u5224\u9000\u56de\u98ce\u9669')
    ck(any(i['item'] == '\u8033\u6735' for i in shot_check(dict(ok, ears_visible=False))['issues']),
       '\u8033\u6735\u672a\u9732\u5e94\u5224\u9000\u56de\u98ce\u9669')
    ck(any(i['item'] == '\u5e3d\u5b50\u5934\u9970' for i in shot_check(dict(ok, headwear=True))['issues']),
       '\u6234\u5e3d\u5e94\u5224\u9000\u56de\u98ce\u9669')

    # 6 \u53cd\u4f8b\uff1a\u8d85\u8fc7 6 \u4e2a\u6708
    r6 = shot_check(dict(ok, months_since=8))
    ck(any(i['item'] == '\u62cd\u6444\u65f6\u95f4' for i in r6['issues']), '\u8d85 8 \u4e2a\u6708\u5e94\u5224\u9000\u56de\u98ce\u9669')
    ck(shot_check(dict(ok, months_since=6))['issues'] == [], '6 \u4e2a\u6708\u8fb9\u754c\u5e94\u5408\u683c')

    # 7 \u53cd\u4f8b\uff1a\u6587\u4ef6\u5927\u5c0f\u8d85\u9650
    ck(any(i['item'] == '\u6587\u4ef6\u5927\u5c0f' for i in shot_check(dict(ok, file_kb=800))['issues']),
       '800 KB \u5e94\u5224\u9000\u56de\u98ce\u9669')
    ck(any(i['item'] == '\u6587\u4ef6\u5927\u5c0f' for i in shot_check(dict(ok, file_kb=3))['issues']),
       '3 KB \u5e94\u5224\u9000\u56de\u98ce\u9669')
    ck(shot_check(dict(ok, file_kb=10))['issues'] == [], '10 KB \u8fb9\u754c\u5e94\u5408\u683c')
    ck(shot_check(dict(ok, file_kb=300))['issues'] == [], '300 KB \u8fb9\u754c\u5e94\u5408\u683c')

    # 8 \u53cd\u4f8b\uff1a\u7ea2\u773c\u3001\u670d\u88c5\u65e0\u5bf9\u6bd4
    ck(any(i['item'] == '\u7ea2\u773c' for i in shot_check(dict(ok, red_eye=True))['issues']),
       '\u7ea2\u773c\u5e94\u5224\u9000\u56de\u98ce\u9669')
    ck(any(i['item'] == '\u670d\u88c5\u914d\u8272' for i in shot_check(dict(ok, clothes_contrast=False))['issues']),
       '\u670d\u88c5\u65e0\u5bf9\u6bd4\u5e94\u5224\u9000\u56de\u98ce\u9669')

    # 9 \u53ef\u6539\u8fdb\u9879\uff1a\u5934\u90e8\u5360\u6bd4\u4e0e\u8fb9\u754c
    ck(any(i['item'] == '\u5934\u90e8\u5360\u6bd4' for i in shot_check(dict(ok, face_height_ratio=0.5))['issues']),
       '\u5934\u90e8\u5360\u6bd4 0.5 \u5e94\u63d0\u793a')
    ck(shot_check(dict(ok, face_height_ratio=0.70))['issues'] == [], '0.70 \u8fb9\u754c\u5e94\u5408\u683c')
    ck(shot_check(dict(ok, face_height_ratio=0.80))['issues'] == [], '0.80 \u8fb9\u754c\u5e94\u5408\u683c')

    # 10 \u53ef\u6539\u8fdb\u9879\uff1a\u5934\u9876\u7559\u767d\u4e0e\u773c\u775b\u4f4d\u7f6e
    ck(any(i['item'] == '\u5934\u9876\u7559\u767d' for i in shot_check(dict(ok, head_top_margin=0.2))['issues']),
       '\u7559\u767d 0.2 \u5e94\u63d0\u793a')
    ck(shot_check(dict(ok, head_top_margin=0.03))['issues'] == [], '0.03 \u8fb9\u754c\u5e94\u5408\u683c')
    ck(any(i['item'] == '\u773c\u775b\u4f4d\u7f6e' for i in shot_check(dict(ok, eye_line_ratio=0.8))['issues']),
       '\u773c\u775b\u4f4d\u7f6e 0.8 \u5e94\u63d0\u793a')

    # 11 \u53ef\u6539\u8fdb\u9879\uff1a\u773c\u955c\u3001\u9732\u9f7f\u3001\u80a9\u8180\u3001\u80cc\u666f
    ck(any(i['item'] == '\u773c\u955c' for i in shot_check(dict(ok, glasses=True))['issues']),
       '\u6234\u773c\u955c\u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u8868\u60c5' for i in shot_check(dict(ok, expression='teeth'))['issues']),
       '\u9732\u9f7f\u7b11\u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u80a9\u8180' for i in shot_check(dict(ok, shoulders_visible=False))['issues']),
       '\u80a9\u8180\u672a\u62cd\u5168\u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u80cc\u666f\u9634\u5f71' for i in shot_check(dict(ok, shadow_on_bg=True))['issues']),
       '\u80cc\u666f\u6709\u9634\u5f71\u5e94\u63d0\u793a')
    ck(any(i['item'] == '\u80cc\u666f\u5747\u5300\u5ea6' for i in shot_check(dict(ok, bg_even=False))['issues']),
       '\u80cc\u666f\u4e0d\u5747\u5300\u5e94\u63d0\u793a')

    # 12 \u6392\u5e8f\u65b9\u5411\uff1a\u4e25\u91cd\u9879\u6392\u6700\u524d
    r12 = shot_check(dict(ok, dpi=72, glasses=True, head_top_margin=0.3))
    ck(r12['issues'][0]['sev'] == 3, '\u4e25\u91cd\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r12['issues'][0]['sev'])
    ck(r12['issues'][0]['item'] == '\u5206\u8fa8\u7387', '\u9996\u4e2a\u5e94\u662f\u5206\u8fa8\u7387\uff0c\u5b9e\u4e3a %s' % r12['issues'][0]['item'])
    ck(r12['issues'][-1]['sev'] == 2, '\u672b\u4f4d\u5e94\u662f\u53ef\u6539\u8fdb\u9879')

    # 13 \u5224\u5b9a\u987a\u5e8f\uff1a\u6709\u4e25\u91cd\u9879\u65f6\u4e0d\u56e0\u7f3a\u4fe1\u606f\u5224\u5f85\u786e\u8ba4
    r13 = shot_check({'name': '\u53ea\u586b\u5206\u8fa8\u7387', 'spec': 'one_inch', 'dpi': 72})
    ck(r13['level'] == '\u5b58\u5728\u9000\u56de\u98ce\u9669', '\u7f3a\u5176\u4ed6\u9879\u4f46\u6709\u4e25\u91cd\u9879\u4e0d\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r13['level'])
    r13b = shot_check(dict(ok, months_since=None, head_top_margin=None))
    ck(r13b['level'] == '\u5f85\u786e\u8ba4', '\u7f3a\u975e\u5fc5\u586b\u9879\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r13b['level'])

    # 14 \u6c47\u603b\u4e0e\u6574\u6539\u987a\u5e8f
    r14 = calc({'photos': [ok,
                           dict(ok, name='\u4f4e\u5206\u8fa8\u7387', dpi=72),
                           dict(ok, name='\u6234\u773c\u955c', glasses=True)]})
    ck(r14['overall'] == '\u5b58\u5728\u4f1a\u88ab\u9000\u56de\u7684\u8bc1\u4ef6\u7167', '\u6709\u4e25\u91cd\u9879\u5e94\u5224\u4f1a\u88ab\u9000\u56de\uff0c\u5b9e\u4e3a %s' % r14['overall'])
    ck(r14['n_bad'] == 1, '\u4e25\u91cd\u9879\u5e94\u4e3a 1 \u5f20\uff0c\u5b9e\u4e3a %d' % r14['n_bad'])
    ck(r14['fix_order'][0] == '\u4f4e\u5206\u8fa8\u7387', '\u4e25\u91cd\u9879\u5e94\u5148\u6539\uff0c\u5b9e\u4e3a %s' % r14['fix_order'])
    ck(r14['fix_order'][1] == '\u6234\u773c\u955c', '\u53ef\u6539\u8fdb\u9879\u6392\u5176\u540e\uff0c\u5b9e\u4e3a %s' % r14['fix_order'])

    # 15 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'photos': [dict(ok, dpi=72)]})
    r15 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r15['overall'] == '\u5b58\u5728\u4f1a\u88ab\u9000\u56de\u7684\u8bc1\u4ef6\u7167', 'BOM \u5b57\u7b26\u4e32\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r15['overall'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_c5.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'photos': [dict(ok, name='\u5e26BOM', months_since=12)]}))
    try:
        r15b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r15b['rows'][0]['name'] == '\u5e26BOM', 'BOM \u6587\u4ef6\u9996\u4e2a key \u5e94\u89e3\u6790\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r15b['rows'][0]['name'])
        ck(r15b['n_bad'] == 1, '\u8d85 12 \u4e2a\u6708\u5e94\u5224\u9000\u56de\u98ce\u9669\uff0c\u5b9e\u4e3a %d' % r15b['n_bad'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 16 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({}, '\u7f3a photos'),
        ({'photos': []}, 'photos \u7a7a\u5217\u8868'),
        ({'photos': [dict(ok, dpi='abc')]}, 'dpi \u975e\u6570\u5b57'),
        ({'photos': [dict(ok, px_w=0)]}, '\u50cf\u7d20\u4e3a 0'),
        ({'photos': [dict(ok, spec='\u4e09\u5bf8')]}, '\u672a\u77e5\u89c4\u683c'),
        ({'photos': [dict(ok, bg='\u7eff\u5e95')]}, '\u672a\u77e5\u5e95\u8272'),
        ({'photos': [dict(ok, expression='\u5927\u7b11')]}, '\u672a\u77e5\u8868\u60c5'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b16 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 17 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r14)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u9010\u5f20\u5224\u5b9a', '\u5e38\u89c1\u89c4\u683c', '\u9608\u503c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355', '\u4ee5\u53d7\u7406\u673a\u6784\u516c\u5e03\u7684\u8981\u6c42\u4e3a\u51c6'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b %s' % key)
    ck(len(SPECS) == 4, '\u89c4\u683c\u5e94 4 \u79cd')
    ck(all(s[4] > 0 and s[5] > 0 for s in SPECS), '\u6bcf\u79cd\u89c4\u683c\u90fd\u8981\u6709\u50cf\u7d20\u503c')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u6b63\u4f8b/\u5206\u8fa8\u7387\u53cd\u4f8b\u4e0e\u8fb9\u754c/\u50cf\u7d20\u5c3a\u5bf8\u53cd\u4f8b\u4e0e\u5bb9\u5dee/\u5e95\u8272\u53cd\u4f8b/'
        '\u906e\u7709\u4e0e\u8033\u6735\u4e0e\u6234\u5e3d\u53cd\u4f8b/\u8d85\u671f\u53cd\u4f8b\u4e0e\u8fb9\u754c/\u6587\u4ef6\u4e0a\u4e0b\u9650\u4e0e\u8fb9\u754c/\u7ea2\u773c\u4e0e\u670d\u88c5\u53cd\u4f8b/\u5934\u90e8\u5360\u6bd4\u8fb9\u754c/'
        '\u7559\u767d\u4e0e\u773c\u775b\u4f4d\u7f6e/\u773c\u955c\u8868\u60c5\u80a9\u8180\u80cc\u666f/\u4e25\u91cd\u9879\u6392\u5e8f/\u5224\u5b9a\u987a\u5e8f/\u6c47\u603b\u6574\u6539\u987a\u5e8f/BOM\u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u8bc1\u4ef6\u7167\u81ea\u67e5')
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
