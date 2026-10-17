# -*- coding: utf-8 -*-
"""\u624b\u673a\u6444\u5f71\u6784\u56fe\u81ea\u67e5\uff1a\u6309\u6240\u9009\u6784\u56fe\u6cd5\u6838\u67e5\u4e3b\u4f53\u4f4d\u7f6e\u3001\u6c34\u5e73\u3001\u5730\u5e73\u7ebf\u3001\u7559\u767d\u4e0e\u6742\u7269\u3002

\u7528\u6cd5:
  python composition_check.py --file shots.json [--out result.md] [--format json]
  python composition_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u6784\u56fe\u6cd5: (\u952e, \u4e2d\u6587\u540d, \u8981\u70b9, \u9002\u7528\u9898\u6750, \u5e38\u89c1\u9519\u8bef)
METHODS = [
    ('thirds', '\u4e09\u5206\u6cd5', '\u4e3b\u4f53\u653e\u5728\u56db\u6761\u4e09\u5206\u7ebf\u7684\u56db\u4e2a\u4ea4\u70b9\u9644\u8fd1', '\u98ce\u666f\u3001\u4eba\u50cf\u3001\u8857\u62cd\u901a\u7528',
     '\u628a\u4e3b\u4f53\u653e\u5728\u753b\u9762\u6b63\u4e2d\u592e'),
    ('center', '\u4e2d\u5fc3\u6784\u56fe', '\u4e3b\u4f53\u5c45\u4e2d\uff0c\u753b\u9762\u5de6\u53f3\u5bf9\u79f0', '\u5efa\u7b51\u6b63\u9762\u3001\u5bf9\u79f0\u573a\u666f\u3001\u8bc1\u4ef6\u7167',
     '\u4e3b\u4f53\u504f\u4e00\u8fb9\u5bfc\u81f4\u91cd\u5fc3\u4e0d\u7a33'),
    ('symmetry', '\u5bf9\u79f0\u6784\u56fe', '\u5de6\u53f3\u6216\u4e0a\u4e0b\u5b8c\u5168\u5bf9\u79f0\uff0c\u6c34\u5e73\u5fc5\u987b\u6781\u6b63', '\u5012\u5f71\u3001\u5efa\u7b51\u3001\u8d70\u5eca',
     '\u6c34\u5e73\u5dee\u4e00\u70b9\u70b9\u5c31\u6bc1\u6389\u6574\u5f20'),
    ('leading', '\u5f15\u5bfc\u7ebf\u6784\u56fe', '\u7528\u9053\u8def\u680f\u6746\u6cb3\u6d41\u628a\u89c6\u7ebf\u5f15\u5411\u4e3b\u4f53', '\u9053\u8def\u3001\u6865\u6881\u3001\u6cb3\u9053\u3001\u53f0\u9636',
     '\u7ebf\u6761\u6307\u5411\u753b\u9762\u5916\u800c\u4e0d\u662f\u4e3b\u4f53'),
    ('frame', '\u6846\u67b6\u6784\u56fe', '\u7528\u95e8\u7a97\u6811\u679d\u505a\u524d\u666f\u6846\u4f4f\u4e3b\u4f53', '\u6709\u524d\u666f\u7ed3\u6784\u7684\u573a\u666f',
     '\u524d\u666f\u6846\u592a\u539a\u62a2\u4e3b\u4f53'),
    ('negative', '\u7559\u767d\u6784\u56fe', '\u4e3b\u4f53\u5360\u6bd4\u5c0f\uff0c\u5927\u91cf\u7559\u767d', '\u6781\u7b80\u3001\u5927\u9762\u79ef\u5929\u7a7a\u3001\u96fe\u666f\u3001\u526a\u5f71',
     '\u7559\u767d\u6ca1\u6709\u610f\u4e49\uff0c\u53ea\u662f\u4e3b\u4f53\u592a\u5c0f'),
    ('fill', '\u586b\u5145\u6784\u56fe', '\u4e3b\u4f53\u5145\u6ee1\u753b\u9762\uff0c\u53bb\u6389\u591a\u4f59\u80cc\u666f', '\u7279\u5199\u3001\u7f8e\u98df\u3001\u82b1\u5349\u3001\u5c40\u90e8\u7ec6\u8282',
     '\u753b\u9762\u8fb9\u7f18\u628a\u4e3b\u4f53\u5207\u6389'),
]

# \u9608\u503c
TOL = {
    'tilt_max': 1.0,        # \u4e00\u822c\u6784\u56fe\u5141\u8bb8\u7684\u6700\u5927\u503e\u659c\u5ea6\u6570
    'tilt_symmetry': 0.5,   # \u5bf9\u79f0\u6784\u56fe\u5141\u8bb8\u7684\u6700\u5927\u503e\u659c\u5ea6\u6570
    'headroom_min': 0.05,   # \u5934\u9876\u7559\u767d\u4e0b\u9650
    'headroom_max': 0.20,   # \u5934\u9876\u7559\u767d\u4e0a\u9650
    'horizon_lo': 0.45,     # \u5730\u5e73\u7ebf\u5c45\u4e2d\u5224\u5b9a\u7684\u4e0b\u754c
    'horizon_hi': 0.55,     # \u5730\u5e73\u7ebf\u5c45\u4e2d\u5224\u5b9a\u7684\u4e0a\u754c
    'subject_min': 0.15,    # \u4e3b\u4f53\u5360\u6bd4\u4e0b\u9650
    'negative_max': 0.35,   # \u7559\u767d\u6784\u56fe\u4e3b\u4f53\u5360\u6bd4\u4e0a\u9650
    'fill_min': 0.5,        # \u586b\u5145\u6784\u56fe\u4e3b\u4f53\u5360\u6bd4\u4e0b\u9650
}

def _band(v):
    """\u4e09\u5206\u5e26\u7684\u5224\u5b9a\uff1a\u843d\u5728 0.25-0.42 \u6216 0.58-0.75\u3002"""
    return 0.25 <= v <= 0.42 or 0.58 <= v <= 0.75


# \u4e3b\u4f53\u843d\u70b9\u89c4\u5219: \u952e -> (\u533a\u95f4\u8bf4\u660e, \u5224\u5b9a\u51fd\u6570)
POS_RULE = {
    'thirds': ('\u6a2a\u5750\u6807\u4e0e\u7eb5\u5750\u6807\u5747\u843d\u5728 0.25-0.42 \u6216 0.58-0.75',
               lambda x, y: _band(x) and _band(y)),
    'center': ('\u6a2a\u5750\u6807 0.42-0.58\uff0c\u7eb5\u5750\u6807 0.35-0.65',
               lambda x, y: 0.42 <= x <= 0.58 and 0.35 <= y <= 0.65),
    'symmetry': ('\u6a2a\u5750\u6807 0.45-0.55',
                 lambda x, y: 0.45 <= x <= 0.55),
    'leading': ('\u6a2a\u5750\u6807 0.25-0.42 \u6216 0.58-0.75\uff0c\u7eb5\u5750\u6807 0.25-0.75',
                lambda x, y: _band(x) and 0.25 <= y <= 0.75),
    'frame': ('\u6a2a\u7eb5\u5750\u6807\u5747\u843d\u5728 0.2-0.8',
              lambda x, y: 0.2 <= x <= 0.8 and 0.2 <= y <= 0.8),
    'negative': ('\u4e0d\u9650\uff0c\u4f46\u7559\u767d\u8981\u6709\u660e\u786e\u610f\u4e49',
                 lambda x, y: True),
    'fill': ('\u6a2a\u7eb5\u5750\u6807\u5747\u843d\u5728 0.3-0.7',
             lambda x, y: 0.3 <= x <= 0.7 and 0.3 <= y <= 0.7),
}


def norm(k):
    return str(k or '').strip().lower().replace(' ', '')


def _num(shot, key, required=False):
    v = shot.get(key)
    if v is None:
        if required:
            raise ValueError('\u7f3a\u5c11\u5fc5\u586b\u9879: %s' % key)
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError('%s \u5fc5\u987b\u662f\u6570\u5b57\uff0c\u5b9e\u4e3a %s' % (key, v))
    if not 0.0 <= f <= 1.0:
        raise ValueError('%s \u5fc5\u987b\u5728 0 \u5230 1 \u4e4b\u95f4\uff0c\u5b9e\u4e3a %s' % (key, v))
    return f


def shot_check(shot):
    """\u5bf9\u5355\u5f20\u7167\u7247\u505a\u6784\u56fe\u81ea\u67e5\uff0c\u8fd4\u56de(\u7ed3\u679c\u5b57\u5178)\u3002"""
    if not isinstance(shot, dict):
        raise ValueError('shots \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
    name = str(shot.get('name') or '\u672a\u547d\u540d').strip()
    method = norm(shot.get('method'))
    if method not in POS_RULE:
        raise ValueError('\u672a\u77e5\u7684\u6784\u56fe\u6cd5: %s\uff0c\u53ef\u9009 %s \u4e4b\u4e00'
                         % (shot.get('method'), '/'.join(sorted(POS_RULE))))
    x = _num(shot, 'subject_x', required=True)
    y = _num(shot, 'subject_y', required=True)
    tilt = shot.get('horizon_tilt_deg')
    tilt = float(tilt) if tilt is not None else None
    horizon = _num(shot, 'horizon_y')
    headroom = _num(shot, 'headroom')
    ratio = _num(shot, 'subject_ratio')
    clutter = bool(shot.get('clutter'))
    edge_cut = bool(shot.get('edge_cut'))
    leading = shot.get('leading_lines')

    issues = []
    misses = []

    # 1 \u6c34\u5e73\uff08\u4e25\u91cd\u9879\uff09
    if tilt is None:
        misses.append('\u6c34\u5e73\u503e\u659c')
    else:
        lim = TOL['tilt_symmetry'] if method == 'symmetry' else TOL['tilt_max']
        if abs(tilt) > lim:
            issues.append({
                'sev': 3, 'item': '\u6c34\u5e73',
                'detail': '\u503e\u659c %.2f \u5ea6\uff0c\u8d85\u8fc7 %s \u6784\u56fe\u5141\u8bb8\u7684 %.1f \u5ea6' % (abs(tilt), _mname(method), lim),
                'why': '\u6a2a\u5e73\u7ad6\u76f4\u7684\u7ebf\u503e\u659c\u8d85\u8fc7 1 \u5ea6\u5c31\u8089\u773c\u53ef\u89c1\uff0c\u5bf9\u79f0\u6784\u56fe\u5dee 0.5 \u5ea6\u5373\u7834\u574f\u5bf9\u79f0\u611f',
            })

    # 2 \u4e3b\u4f53\u4f4d\u7f6e\uff08\u4e25\u91cd\u9879\uff09
    ok, desc = POS_RULE[method][1](x, y), POS_RULE[method][0]
    if not ok:
        issues.append({
            'sev': 3, 'item': '\u4e3b\u4f53\u4f4d\u7f6e',
            'detail': '\u5f53\u524d\u5750\u6807 (%.2f, %.2f)\uff0c%s \u8981\u6c42 %s' % (x, y, _mname(method), desc),
            'why': '\u4e3b\u4f53\u4f4d\u7f6e\u51b3\u5b9a\u89c2\u4f17\u7b2c\u4e00\u773c\u770b\u54ea\u91cc\uff0c\u843d\u70b9\u4e0d\u5bf9\u6574\u5f20\u56fe\u7684\u91cd\u5fc3\u5c31\u6563\u4e86',
        })

    # 3 \u5f15\u5bfc\u7ebf\u5fc5\u987b\u6307\u5411\u4e3b\u4f53\uff08\u4e25\u91cd\u9879\uff09
    if method == 'leading':
        if leading is None:
            misses.append('\u5f15\u5bfc\u7ebf\u662f\u5426\u6307\u5411\u4e3b\u4f53')
        elif not leading:
            issues.append({
                'sev': 3, 'item': '\u5f15\u5bfc\u7ebf',
                'detail': '\u7ebf\u6761\u6ca1\u6709\u6307\u5411\u4e3b\u4f53',
                'why': '\u5f15\u5bfc\u7ebf\u7684\u4f5c\u7528\u662f\u628a\u89c6\u7ebf\u9001\u5230\u4e3b\u4f53\u4e0a\uff0c\u6307\u5411\u753b\u9762\u5916\u4f1a\u628a\u89c2\u4f17\u5e26\u8dd1',
            })

    # 4 \u5730\u5e73\u7ebf\u5c45\u4e2d\uff08\u53ef\u6539\u8fdb\u9879\uff09
    if horizon is not None and method != 'symmetry':
        if TOL['horizon_lo'] <= horizon <= TOL['horizon_hi']:
            issues.append({
                'sev': 2, 'item': '\u5730\u5e73\u7ebf',
                'detail': '\u5730\u5e73\u7ebf\u5728 %.2f\uff0c\u843d\u5728 0.45 \u5230 0.55 \u4e4b\u95f4' % horizon,
                'why': '\u5730\u5e73\u7ebf\u5c45\u4e2d\u628a\u753b\u9762\u4e0a\u4e0b\u5207\u6210\u4e24\u534a\uff0c\u89c2\u4f17\u4e0d\u77e5\u9053\u8be5\u770b\u5929\u8fd8\u662f\u770b\u5730\uff1b'
                       '\u8868\u73b0\u5929\u7a7a\u538b\u5230 0.33\uff0c\u8868\u73b0\u5730\u9762\u62ac\u5230 0.67',
            })

    # 5 \u5934\u9876\u7559\u767d\uff08\u53ef\u6539\u8fdb\u9879\uff09
    if headroom is not None:
        if not TOL['headroom_min'] <= headroom <= TOL['headroom_max']:
            why = ('\u5c0f\u4e8e 0.05 \u4f1a\u9876\u5f97\u592a\u6ee1\u3001\u538b\u6291\uff0c\u50cf\u88ab\u88c1\u6389\u989d\u5934'
                   if headroom < TOL['headroom_min'] else
                   '\u5927\u4e8e 0.20 \u5934\u9876\u7a7a\u4e00\u5927\u7247\uff0c\u4eba\u663e\u5f97\u5c0f\u3001\u753b\u9762\u677e\u6563')
            issues.append({
                'sev': 2, 'item': '\u5934\u9876\u7559\u767d',
                'detail': '\u7559\u767d\u6bd4\u4f8b %.2f\uff0c\u5408\u683c\u533a\u95f4 0.05 \u5230 0.20' % headroom,
                'why': why,
            })

    # 6 \u6742\u7269\u4e0e\u7a7f\u5e2e\uff08\u53ef\u6539\u8fdb\u9879\uff09
    if clutter:
        issues.append({
            'sev': 2, 'item': '\u753b\u9762\u6742\u7269',
            'detail': '\u753b\u9762\u56db\u89d2\u6216\u4e3b\u4f53\u5468\u56f4\u6709\u6742\u7269',
            'why': '\u5783\u573e\u6876\u3001\u7535\u7ebf\u6746\u3001\u8def\u4eba\u624b\u81c2\u4f1a\u62a2\u6ce8\u610f\u529b\uff0c\u62cd\u524d\u626b\u56db\u89d2\u6bd4\u540e\u671f\u88c1\u526a\u53ef\u9760',
        })
    if edge_cut:
        issues.append({
            'sev': 2, 'item': '\u8fb9\u7f18\u7a7f\u5e2e',
            'detail': '\u753b\u9762\u8fb9\u7f18\u628a\u4e3b\u4f53\u5207\u6389\u4e00\u622a',
            'why': '\u811a\u8e1d\u3001\u624b\u8098\u3001\u5934\u9876\u88ab\u5207\u4f1a\u8ba9\u4eba\u89c9\u5f97\u662f\u5e9f\u7247\uff0c\u6539\u53d8\u673a\u4f4d\u6216\u5f80\u540e\u9000\u534a\u6b65',
        })

    # 7 \u4e3b\u4f53\u5360\u6bd4\uff08\u53ef\u6539\u8fdb\u9879\uff09
    if ratio is not None:
        if ratio < TOL['subject_min'] and method != 'negative':
            issues.append({
                'sev': 2, 'item': '\u4e3b\u4f53\u5360\u6bd4',
                'detail': '\u5360\u6bd4 %.2f\uff0c\u4f4e\u4e8e 0.15' % ratio,
                'why': '\u4e3b\u4f53\u592a\u5c0f\u89c2\u4f17\u7b2c\u4e00\u773c\u770b\u4e0d\u51fa\u5728\u62cd\u4ec0\u4e48\uff0c\u8d70\u8fd1\u51e0\u6b65\u6216\u6539\u7528\u957f\u7126\u6bb5',
            })
        elif method == 'negative' and ratio > TOL['negative_max']:
            issues.append({
                'sev': 2, 'item': '\u4e3b\u4f53\u5360\u6bd4',
                'detail': '\u7559\u767d\u6784\u56fe\u4e0b\u5360\u6bd4 %.2f\uff0c\u9ad8\u4e8e 0.35' % ratio,
                'why': '\u7559\u767d\u6784\u56fe\u8981\u7684\u5c31\u662f\u5c0f\u4e3b\u4f53\u52a0\u5927\u7247\u7559\u767d\uff0c\u5360\u6bd4\u8fc7\u9ad8\u5c31\u4e0d\u662f\u7559\u767d\u4e86',
            })
        elif method == 'fill' and ratio < TOL['fill_min']:
            issues.append({
                'sev': 2, 'item': '\u4e3b\u4f53\u5360\u6bd4',
                'detail': '\u586b\u5145\u6784\u56fe\u4e0b\u5360\u6bd4 %.2f\uff0c\u4f4e\u4e8e 0.5' % ratio,
                'why': '\u586b\u5145\u6784\u56fe\u8981\u4e3b\u4f53\u5145\u6ee1\u753b\u9762\uff0c\u5360\u6bd4\u4e0d\u591f\u8bf4\u660e\u80cc\u666f\u8fd8\u6ca1\u53bb\u6389',
            })

    # \u4e25\u91cd\u9879\u6392\u6700\u524d\uff0c\u540c\u7ea7\u522b\u4fdd\u6301\u53d1\u73b0\u987a\u5e8f
    issues.sort(key=lambda r: -r['sev'])

    if any(i['sev'] == 3 for i in issues):
        level = '\u6784\u56fe\u6709\u660e\u663e\u95ee\u9898'
    elif issues:
        level = '\u6709\u53ef\u6539\u8fdb\u9879'
    elif misses:
        level = '\u5f85\u786e\u8ba4'
    else:
        level = '\u6784\u56fe\u89c4\u8303'

    return {
        'name': name, 'method': method, 'method_name': _mname(method),
        'pos_desc': desc, 'x': x, 'y': y,
        'issues': issues, 'misses': misses, 'level': level,
    }


def _mname(key):
    for k, n, _, _, _ in METHODS:
        if k == key:
            return n
    return key


def calc(data):
    shots = data.get('shots')
    if shots is None:
        raise ValueError('\u8f93\u5165\u7f3a\u5c11 shots \u5217\u8868')
    if not isinstance(shots, list) or not shots:
        raise ValueError('shots \u5fc5\u987b\u662f\u975e\u7a7a\u5217\u8868')
    rows = [shot_check(s) for s in shots]
    n_bad = len([r for r in rows if r['level'] == '\u6784\u56fe\u6709\u660e\u663e\u95ee\u9898'])
    n_mid = len([r for r in rows if r['level'] == '\u6709\u53ef\u6539\u8fdb\u9879'])
    n_unk = len([r for r in rows if r['level'] == '\u5f85\u786e\u8ba4'])
    # \u5148\u770b\u771f\u5b9e\u7f3a\u9677\uff0c\u518d\u770b\u53ef\u6539\u8fdb\u9879\uff0c\u6700\u540e\u624d\u770b\u4fe1\u606f\u662f\u5426\u5b8c\u6574
    if n_bad:
        overall = '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u7167\u7247'
    elif n_mid:
        overall = '\u5b58\u5728\u53ef\u6539\u8fdb\u7684\u7167\u7247'
    elif n_unk:
        overall = '\u5f85\u786e\u8ba4'
    else:
        overall = '\u5168\u90e8\u6784\u56fe\u89c4\u8303'
    # \u6574\u6539\u987a\u5e8f\uff1a\u5148\u770b\u6700\u9ad8\u4e25\u91cd\u5ea6(\u4e25\u91cd\u7684\u6392\u6700\u524d)\uff0c\u518d\u770b\u95ee\u9898\u6761\u6570\uff0c\u6700\u540e\u6309\u540d\u5b57\u7a33\u5b9a\u6392\u5e8f
    def _sev(r):
        return max([i['sev'] for i in r['issues']], default=0)

    order = sorted(rows, key=lambda r: (-_sev(r), -len(r['issues']), r['name']))
    return {
        'overall': overall, 'rows': rows,
        'n_bad': n_bad, 'n_mid': n_mid, 'n_unk': n_unk, 'n_ok': len(rows) - n_bad - n_mid - n_unk,
        'fix_order': [r['name'] for r in order if r['issues']],
        'methods': [{'key': k, 'name': n, 'how': h, 'where': w, 'wrong': e}
                    for k, n, h, w, e in METHODS],
        'tol': dict(TOL),
    }


def render_md(r):
    L = []
    L.append('# \u624b\u673a\u6444\u5f71\u6784\u56fe\u81ea\u67e5')
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
    L.append('| \u6784\u56fe\u89c4\u8303 | %d |' % r['n_ok'])
    L.append('')
    if r['fix_order']:
        L.append('\u6574\u6539\u987a\u5e8f\uff08\u95ee\u9898\u591a\u7684\u5148\u6539\uff09\uff1a%s' % '\u3001'.join(r['fix_order']))
        L.append('')
    L.append('## \u4e8c\u3001\u9010\u5f20\u5224\u5b9a')
    L.append('')
    for row in r['rows']:
        L.append('### %s\uff08%s\uff09' % (row['name'], row['method_name']))
        L.append('')
        L.append('- \u4e3b\u4f53\u5750\u6807\uff1a(%.2f, %.2f)\uff0c\u8be5\u6784\u56fe\u6cd5\u8981\u6c42 %s' % (row['x'], row['y'], row['pos_desc']))
        L.append('- \u5224\u5b9a\uff1a**%s**' % row['level'])
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
    L.append('## \u4e09\u3001\u4e03\u79cd\u6784\u56fe\u6cd5\u901f\u67e5')
    L.append('')
    L.append('| \u6784\u56fe\u6cd5 | \u8981\u70b9 | \u9002\u7528\u9898\u6750 | \u5e38\u89c1\u9519\u8bef |')
    L.append('|---|---|---|---|')
    for m in r['methods']:
        L.append('| %s | %s | %s | %s |' % (m['name'], m['how'], m['where'], m['wrong']))
    L.append('')
    L.append('## \u56db\u3001\u9608\u503c')
    L.append('')
    L.append('| \u9879\u76ee | \u9608\u503c |')
    L.append('|---|---|')
    L.append('| \u6c34\u5e73\u503e\u659c | \u4e0d\u8d85\u8fc7 %.1f \u5ea6\uff0c\u5bf9\u79f0\u6784\u56fe\u4e0d\u8d85\u8fc7 %.1f \u5ea6 |'
             % (r['tol']['tilt_max'], r['tol']['tilt_symmetry']))
    L.append('| \u5934\u9876\u7559\u767d | %.2f \u5230 %.2f |' % (r['tol']['headroom_min'], r['tol']['headroom_max']))
    L.append('| \u5730\u5e73\u7ebf\u5c45\u4e2d\u5224\u5b9a | %.2f \u5230 %.2f |' % (r['tol']['horizon_lo'], r['tol']['horizon_hi']))
    L.append('| \u4e3b\u4f53\u5360\u6bd4 | \u4e0d\u4f4e\u4e8e %.2f |' % r['tol']['subject_min'])
    L.append('')
    L.append('## \u4e94\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355\uff08\u811a\u672c\u4e0d\u66ff\u4ee3\uff09')
    L.append('')
    L.append('- [ ] \u6253\u5f00\u624b\u673a\u53c2\u8003\u7ebf\uff0c\u5730\u5e73\u7ebf\u538b\u5728\u7f51\u683c\u6a2a\u7ebf\u4e0a')
    L.append('- [ ] \u6309\u5feb\u95e8\u524d\u626b\u8fc7\u753b\u9762\u56db\u4e2a\u89d2\uff0c\u6ca1\u6709\u6742\u7269')
    L.append('- [ ] \u4e3b\u4f53\u5934\u9876\u4e0e\u753b\u9762\u4e0a\u8fb9\u7f18\u7559\u767d\u5408\u9002\uff0c\u6ca1\u6709\u88ab\u5207')
    L.append('- [ ] \u62cd\u4eba\u50cf\u65f6\u773c\u775b\u6c34\u5e73\u4f4d\u7f6e\u5728\u753b\u9762\u9ad8\u5ea6 0.3 \u5230 0.5 \u4e4b\u95f4')
    L.append('- [ ] \u62cd\u5b8c\u653e\u5927\u5230\u767e\u5206\u4e4b\u767e\u518d\u770b\u4e00\u6b21\u6c34\u5e73')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u4e09\u5206\u6cd5\u6b63\u4f8b
    good = {'name': '\u6e56\u8fb9', 'method': 'thirds', 'subject_x': 0.33, 'subject_y': 0.33,
            'horizon_tilt_deg': 0.4, 'horizon_y': 0.33, 'headroom': 0.1,
            'subject_ratio': 0.4}
    r1 = shot_check(good)
    ck(r1['level'] == '\u6784\u56fe\u89c4\u8303', '\u4e09\u5206\u6cd5\u6b63\u4f8b\u5e94\u5224\u6784\u56fe\u89c4\u8303\uff0c\u5b9e\u4e3a %s' % r1['level'])
    ck(r1['issues'] == [], '\u4e09\u5206\u6cd5\u6b63\u4f8b\u4e0d\u5e94\u6709\u95ee\u9898\u9879\uff0c\u5b9e\u4e3a %s' % r1['issues'])

    # 2 \u53cd\u4f8b\uff1a\u8bf4\u662f\u4e09\u5206\u6cd5\u5374\u628a\u4e3b\u4f53\u653e\u6b63\u4e2d\u592e
    r2 = shot_check(dict(good, subject_x=0.5, subject_y=0.5))
    ck(r2['level'] == '\u6784\u56fe\u6709\u660e\u663e\u95ee\u9898', '\u4e09\u5206\u6cd5\u4e3b\u4f53\u5c45\u4e2d\u5e94\u5224\u6709\u660e\u663e\u95ee\u9898\uff0c\u5b9e\u4e3a %s' % r2['level'])
    ck(any(i['item'] == '\u4e3b\u4f53\u4f4d\u7f6e' for i in r2['issues']),
       '\u5e94\u70b9\u540d\u4e3b\u4f53\u4f4d\u7f6e\uff0c\u5b9e\u4e3a %s' % [i['item'] for i in r2['issues']])

    # 3 \u53cd\u4f8b\uff1a\u6c34\u5e73\u503e\u659c 3 \u5ea6
    r3 = shot_check(dict(good, horizon_tilt_deg=3.0))
    ck(r3['level'] == '\u6784\u56fe\u6709\u660e\u663e\u95ee\u9898', '\u503e\u659c 3 \u5ea6\u5e94\u5224\u6709\u660e\u663e\u95ee\u9898\uff0c\u5b9e\u4e3a %s' % r3['level'])
    ck(any(i['item'] == '\u6c34\u5e73' for i in r3['issues']), '\u5e94\u70b9\u540d\u6c34\u5e73\u9879')

    # 4 \u5bf9\u79f0\u6784\u56fe 0.8 \u5ea6\u4e0d\u5408\u683c\uff0c0.4 \u5ea6\u5408\u683c
    sym = dict(good, method='symmetry', subject_x=0.5, subject_y=0.5, horizon_y=0.5)
    r4a = shot_check(dict(sym, horizon_tilt_deg=0.8))
    r4b = shot_check(dict(sym, horizon_tilt_deg=0.4))
    ck(any(i['item'] == '\u6c34\u5e73' for i in r4a['issues']), '\u5bf9\u79f0\u6784\u56fe 0.8 \u5ea6\u5e94\u4e0d\u5408\u683c')
    ck(not any(i['item'] == '\u6c34\u5e73' for i in r4b['issues']), '\u5bf9\u79f0\u6784\u56fe 0.4 \u5ea6\u5e94\u5408\u683c')
    ck(not any(i['item'] == '\u5730\u5e73\u7ebf' for i in r4b['issues']), '\u5bf9\u79f0\u6784\u56fe\u5730\u5e73\u7ebf\u5c45\u4e2d\u4e0d\u62a5\u95ee\u9898')

    # 5 \u53cd\u4f8b\uff1a\u5730\u5e73\u7ebf\u5c45\u4e2d
    r5 = shot_check(dict(good, horizon_y=0.5))
    ck(any(i['item'] == '\u5730\u5e73\u7ebf' for i in r5['issues']), '\u5730\u5e73\u7ebf\u5c45\u4e2d\u5e94\u62a5\u53ef\u6539\u8fdb\u9879')
    ck(r5['level'] == '\u6709\u53ef\u6539\u8fdb\u9879', '\u5730\u5e73\u7ebf\u5c45\u4e2d\u5e94\u5224\u53ef\u6539\u8fdb\uff0c\u5b9e\u4e3a %s' % r5['level'])

    # 6 \u53cd\u4f8b\uff1a\u5934\u9876\u7559\u767d\u8fc7\u5927 / \u8fc7\u5c0f
    r6a = shot_check(dict(good, headroom=0.3))
    r6b = shot_check(dict(good, headroom=0.02))
    ck(any(i['item'] == '\u5934\u9876\u7559\u767d' for i in r6a['issues']), '\u7559\u767d 0.3 \u5e94\u4e0d\u5408\u683c')
    ck(any(i['item'] == '\u5934\u9876\u7559\u767d' for i in r6b['issues']), '\u7559\u767d 0.02 \u5e94\u4e0d\u5408\u683c')
    ck(shot_check(dict(good, headroom=0.05))['issues'] == [], '\u7559\u767d 0.05 \u8fb9\u754c\u5e94\u5408\u683c')
    ck(shot_check(dict(good, headroom=0.2))['issues'] == [], '\u7559\u767d 0.2 \u8fb9\u754c\u5e94\u5408\u683c')

    # 7 \u53cd\u4f8b\uff1a\u5f15\u5bfc\u7ebf\u6ca1\u6307\u5411\u4e3b\u4f53
    r7 = shot_check(dict(good, method='leading', leading_lines=False))
    ck(any(i['item'] == '\u5f15\u5bfc\u7ebf' for i in r7['issues']), '\u5f15\u5bfc\u7ebf\u672a\u6307\u5411\u4e3b\u4f53\u5e94\u4e0d\u5408\u683c')
    ck(shot_check(dict(good, method='leading', leading_lines=True))['level'] == '\u6784\u56fe\u89c4\u8303',
       '\u5f15\u5bfc\u7ebf\u6b63\u786e\u5e94\u5408\u683c')

    # 8 \u53cd\u4f8b\uff1a\u7559\u767d\u6784\u56fe\u4e3b\u4f53\u5360\u6bd4\u8fc7\u9ad8\uff1b\u586b\u5145\u6784\u56fe\u5360\u6bd4\u8fc7\u4f4e
    r8a = shot_check(dict(good, method='negative', subject_ratio=0.6))
    ck(any(i['item'] == '\u4e3b\u4f53\u5360\u6bd4' for i in r8a['issues']), '\u7559\u767d\u6784\u56fe\u5360\u6bd4 0.6 \u5e94\u4e0d\u5408\u683c')
    r8b = shot_check(dict(good, method='fill', subject_x=0.5, subject_y=0.5, subject_ratio=0.3))
    ck(any(i['item'] == '\u4e3b\u4f53\u5360\u6bd4' for i in r8b['issues']), '\u586b\u5145\u6784\u56fe\u5360\u6bd4 0.3 \u5e94\u4e0d\u5408\u683c')

    # 9 \u6392\u5e8f\u65b9\u5411\uff1a\u4e25\u91cd\u9879\u5fc5\u987b\u6392\u5728\u6700\u524d
    r9 = shot_check(dict(good, horizon_tilt_deg=2.0, clutter=True, horizon_y=0.5))
    ck(r9['issues'][0]['sev'] == 3, '\u4e25\u91cd\u9879\u5e94\u6392\u6700\u524d\uff0c\u5b9e\u4e3a %s' % r9['issues'][0]['sev'])
    ck(r9['issues'][0]['item'] == '\u6c34\u5e73', '\u9996\u4e2a\u95ee\u9898\u5e94\u662f\u6c34\u5e73\uff0c\u5b9e\u4e3a %s' % r9['issues'][0]['item'])
    ck(r9['issues'][-1]['sev'] == 2, '\u672b\u4f4d\u5e94\u662f\u53ef\u6539\u8fdb\u9879')

    # 10 \u5224\u5b9a\u987a\u5e8f\uff1a\u6709\u4e25\u91cd\u9879\u65f6\u4e0d\u80fd\u56e0\u4e3a\u7f3a\u4fe1\u606f\u5224\u6210\u5f85\u786e\u8ba4
    r10 = shot_check({'name': '\u7f3a\u7559\u767d', 'method': 'thirds', 'subject_x': 0.5, 'subject_y': 0.5})
    ck(r10['level'] == '\u6784\u56fe\u6709\u660e\u663e\u95ee\u9898', '\u7f3a\u7559\u767d\u4f46\u6709\u4e25\u91cd\u9879\u4e0d\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r10['level'])
    r10b = shot_check({'name': '\u4ec5\u7f3a\u6c34\u5e73', 'method': 'thirds', 'subject_x': 0.33, 'subject_y': 0.33})
    ck(r10b['level'] == '\u5f85\u786e\u8ba4', '\u5750\u6807\u5bf9\u4f46\u672a\u586b\u6c34\u5e73\u5e94\u5224\u5f85\u786e\u8ba4\uff0c\u5b9e\u4e3a %s' % r10b['level'])

    # 11 \u6c47\u603b\u4e0e\u6574\u6539\u987a\u5e8f
    r11 = calc({'shots': [good, dict(good, name='\u6b6a\u7684', horizon_tilt_deg=3.0),
                          dict(good, name='\u6742\u7269', clutter=True)]})
    ck(r11['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u7167\u7247', '\u6709\u4e25\u91cd\u9879\u5e94\u5224\u9700\u8981\u91cd\u62cd\uff0c\u5b9e\u4e3a %s' % r11['overall'])
    ck(r11['n_bad'] == 1, '\u4e25\u91cd\u9879\u5e94\u4e3a 1 \u5f20\uff0c\u5b9e\u4e3a %d' % r11['n_bad'])
    ck(r11['fix_order'][0] == '\u6b6a\u7684',
       '\u6574\u6539\u987a\u5e8f\u9996\u4e2a\u5e94\u662f\u4e25\u91cd\u5ea6\u6700\u9ad8\u7684\uff08\u4e25\u91cd\u9879\u4f18\u5148\u4e8e\u6761\u6570\uff09\uff0c\u5b9e\u4e3a %s' % r11['fix_order'])
    ck(r11['fix_order'][1] == '\u6742\u7269', '\u4e25\u91cd\u9879\u4e4b\u540e\u624d\u662f\u53ef\u6539\u8fdb\u9879\uff0c\u5b9e\u4e3a %s' % r11['fix_order'])

    # 12 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'shots': [dict(good, subject_x=0.5, subject_y=0.5)]})
    r12 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r12['overall'] == '\u5b58\u5728\u9700\u8981\u91cd\u62cd\u7684\u7167\u7247', 'BOM \u5b57\u7b26\u4e32\u5e94\u6b63\u786e\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r12['overall'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_c1.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'shots': [dict(good, name='\u5e26BOM', horizon_tilt_deg=2.5)]}))
    try:
        r12b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r12b['rows'][0]['name'] == '\u5e26BOM', 'BOM \u6587\u4ef6\u9996\u4e2a key \u5e94\u89e3\u6790\u6b63\u5e38\uff0c\u5b9e\u4e3a %s' % r12b['rows'][0]['name'])
        ck(r12b['n_bad'] == 1, 'BOM \u6587\u4ef6\u5e94\u5224\u51fa 1 \u5f20\u4e25\u91cd\uff0c\u5b9e\u4e3a %d' % r12b['n_bad'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 13 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({'shots': []}, 'shots \u7a7a\u5217\u8868'),
        ({}, '\u7f3a shots'),
        ({'shots': [{'method': 'thirds'}]}, '\u7f3a\u5750\u6807'),
        ({'shots': [{'method': '\u4e0d\u5b58\u5728\u7684\u6784\u56fe', 'subject_x': 0.3, 'subject_y': 0.3}]}, '\u672a\u77e5\u6784\u56fe\u6cd5'),
        ({'shots': [{'method': 'thirds', 'subject_x': 1.5, 'subject_y': 0.3}]}, '\u5750\u6807\u8d8a\u754c'),
        ({'shots': [{'method': 'thirds', 'subject_x': 'abc', 'subject_y': 0.3}]}, '\u5750\u6807\u975e\u6570\u5b57'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b13 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 14 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r11)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u9010\u5f20\u5224\u5b9a', '\u4e03\u79cd\u6784\u56fe\u6cd5\u901f\u67e5', '\u9608\u503c', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u8f93\u51fa\u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(METHODS) == 7, '\u6784\u56fe\u6cd5\u5e94 7 \u79cd')
    ck(all(m[0] in POS_RULE for m in METHODS), '\u6bcf\u79cd\u6784\u56fe\u6cd5\u90fd\u8981\u6709\u843d\u70b9\u89c4\u5219')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u4e09\u5206\u6cd5\u6b63\u4f8b/\u4e3b\u4f53\u5c45\u4e2d\u53cd\u4f8b/\u503e\u659c3\u5ea6\u53cd\u4f8b/\u5bf9\u79f0\u6784\u56fe0.8\u4e0e0.4\u5ea6/'
        '\u5730\u5e73\u7ebf\u5c45\u4e2d\u53cd\u4f8b/\u7559\u767d\u4e0a\u4e0b\u754c\u4e0e\u8fb9\u754c\u503c/\u5f15\u5bfc\u7ebf\u53cd\u4f8b/\u7559\u767d\u4e0e\u586b\u5145\u5360\u6bd4\u53cd\u4f8b/\u4e25\u91cd\u9879\u6392\u5e8f/'
        '\u5224\u5b9a\u987a\u5e8f/\u6c47\u603b\u6574\u6539\u987a\u5e8f/BOM\u4e24\u6761\u8def\u5f84/\u975e\u6cd5\u8f93\u5165/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u624b\u673a\u6444\u5f71\u6784\u56fe\u81ea\u67e5')
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
