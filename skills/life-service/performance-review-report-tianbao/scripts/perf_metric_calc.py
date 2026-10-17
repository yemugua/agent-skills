# -*- coding: utf-8 -*-
"""\u8ff0\u804c\u4e1a\u7ee9\u91cf\u5316\u6838\u67e5\uff1a\u540c\u6bd4 / \u73af\u6bd4 / \u76ee\u6807\u8fbe\u6210\u7387 / \u52a0\u6743\u8fbe\u6210\u7387 / \u91cf\u5316\u8986\u76d6\u7387\u3002

\u7528\u6cd5:
  python perf_metric_calc.py --file metrics.json [--out \u8ff0\u804c\u91cf\u5316\u6838\u7b97.md] [--format json]
  python perf_metric_calc.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u5355\u9879\u8fbe\u6210\u7387\u5c01\u9876\uff0c\u907f\u514d\u4e00\u9879\u8d85\u989d\u628a\u6574\u4f53\u62ac\u4e0a\u53bb
CAP = 1.20
# \u6574\u4f53\u5224\u5b9a\u6863\u4f4d
V_GOOD = 1.00
V_BASIC = 0.90
V_PART = 0.70
# \u91cf\u5316\u8986\u76d6\u7387\u7ea2\u7ebf
COVER_RED = 0.80
# \u63a8\u8350\u6307\u6807\u6570\u533a\u95f4
N_MIN = 3
N_BEST_LO = 5
N_BEST_HI = 8
N_MAX = 12

# \u5b9a\u6027\u8bcd\u9ed1\u540d\u5355\uff08\u8ff0\u804c\u91cc\u51fa\u73b0\u5373\u5e94\u66ff\u6362\u4e3a\u6570\u503c\uff09
QUAL_WORDS = ['\u663e\u8457\u63d0\u5347', '\u5927\u5e45\u63d0\u5347', '\u660e\u663e\u6539\u5584', '\u5706\u6ee1\u5b8c\u6210',
              '\u6210\u6548\u663e\u8457', '\u7a33\u6b65\u63a8\u8fdb', '\u9ad8\u5ea6\u91cd\u89c6', '\u79ef\u6781\u53c2\u4e0e']

DIRECTIONS = ('up', 'down')


def pct(x, nd=2):
    if x is None:
        return '\u4e0d\u9002\u7528'
    return ('%.' + str(nd) + 'f%%') % (x * 100)


def signed(x, nd=1):
    if x is None:
        return '\u4e0d\u9002\u7528'
    return ('%+.1f%%' % (x * 100))


def num(v):
    """\u628a\u8f93\u5165\u8f6c\u6210 float\uff0c\u7a7a\u503c\u4e0e\u975e\u6cd5\u503c\u8fd4\u56de None\u3002"""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def grade_of(ach, direction):
    if ach is None:
        return '\u65e0\u6cd5\u5224\u5b9a'
    if direction == 'up':
        if ach >= 1.0:
            return '\u8fbe\u6210'
        if ach >= 0.9:
            return '\u57fa\u672c\u8fbe\u6210'
        return '\u672a\u8fbe\u6210'
    # down\uff1a\u8d8a\u5c0f\u8d8a\u597d\u3002ach = target / current\uff0c\u5b9e\u9645\u7b49\u4e8e\u76ee\u6807\u65f6\u4e3a 1.0
    if ach >= 1.0:
        return '\u8fbe\u6210'
    if ach >= (1.0 / 1.1):
        return '\u57fa\u672c\u8fbe\u6210'
    return '\u672a\u8fbe\u6210'


def quadrant_of(yoy, ach):
    if yoy is None or ach is None:
        return '\u6570\u636e\u4e0d\u5168'
    if yoy > 0 and ach >= 1.0:
        return '\u771f\u589e\u957f\u771f\u8fbe\u6210'
    if yoy > 0:
        return '\u6709\u589e\u957f\u672a\u8fbe\u6807'
    if ach >= 1.0:
        return '\u8fbe\u6210\u4f46\u540c\u6bd4\u4e0b\u6ed1'
    return '\u4e0b\u6ed1\u4e14\u672a\u8fbe'


def calc(data):
    title = data.get('title', '\u672a\u547d\u540d\u8ff0\u804c')
    owner = data.get('owner', '')
    period = data.get('period', '')
    metrics = data.get('metrics') or []
    if not isinstance(metrics, list) or not metrics:
        raise ValueError('\u6307\u6807\u5217\u8868\u4e3a\u7a7a\uff0c\u8bf7\u81f3\u5c11\u63d0\u4f9b\u4e00\u9879\u6307\u6807')

    rows = []
    warns = []
    wsum = 0.0
    scored_w = 0.0
    scored_sum = 0.0
    covered = 0

    for idx, m in enumerate(metrics, 1):
        name = str(m.get('name') or ('\u6307\u6807%d' % idx))
        unit = str(m.get('unit') or '')
        direction = str(m.get('direction') or 'up').lower()
        if direction not in DIRECTIONS:
            raise ValueError('\u6307\u6807\u300c%s\u300d\u7684\u65b9\u5411\u53ea\u80fd\u586b up \u6216 down\uff0c\u5b9e\u4e3a %s' % (name, m.get('direction')))
        weight = num(m.get('weight'))
        if weight is None:
            weight = 0.0
        cur = num(m.get('current'))
        base = num(m.get('baseline'))
        prev = num(m.get('previous'))
        tgt = num(m.get('target'))

        if cur is None:
            raise ValueError('\u6307\u6807\u300c%s\u300d\u7f3a\u5c11\u672c\u671f\u503c current' % name)

        yoy = None
        if base is not None and base != 0:
            yoy = (cur - base) / abs(base)
        mom = None
        if prev is not None and prev != 0:
            mom = (cur - prev) / abs(prev)

        ach = None
        if direction == 'up':
            if tgt is not None and tgt != 0:
                ach = cur / tgt
        else:
            if cur != 0 and tgt is not None:
                ach = tgt / cur

        score = None
        if ach is not None:
            score = min(ach, CAP)

        wsum += weight
        if score is not None:
            scored_w += weight
            scored_sum += score * weight

        if cur is not None and base is not None and tgt is not None:
            covered += 1

        rows.append({
            'name': name,
            'unit': unit,
            'direction': direction,
            'direction_label': '\u8d8a\u5927\u8d8a\u597d' if direction == 'up' else '\u8d8a\u5c0f\u8d8a\u597d',
            'current': cur,
            'baseline': base,
            'previous': prev,
            'target': tgt,
            'weight': weight,
            'yoy': yoy,
            'mom': mom,
            'ach': ach,
            'grade': grade_of(ach, direction),
            'quadrant': quadrant_of(yoy, ach),
        })

        if base is None:
            warns.append('\u6307\u6807\u300c%s\u300d\u7f3a\u5c11\u4e0a\u5e74\u540c\u671f\u57fa\u7ebf\uff0c\u65e0\u6cd5\u8ba1\u7b97\u540c\u6bd4\uff0c\u5efa\u8bae\u8865\u9f50\u540e\u7eb3\u5165\u6570\u636e\u6bb5' % name)
        if tgt is None:
            warns.append('\u6307\u6807\u300c%s\u300d\u7f3a\u5c11\u76ee\u6807\u503c\uff0c\u65e0\u6cd5\u8ba1\u7b97\u8fbe\u6210\u7387' % name)
        if not unit:
            warns.append('\u6307\u6807\u300c%s\u300d\u672a\u586b\u5355\u4f4d\uff0c\u53e3\u5f84\u4e0d\u6e05\u4f1a\u88ab\u8ffd\u95ee' % name)
        if ach is not None and ach >= 1.0 and yoy is not None and yoy <= 0:
            warns.append('\u6307\u6807\u300c%s\u300d\u8fbe\u6210\u7387 %s \u4f46\u540c\u6bd4 %s\uff0c\u76ee\u6807\u53ef\u80fd\u88ab\u8c03\u4f4e\uff0c\u8ff0\u804c\u91cc\u5fc5\u987b\u4e3b\u52a8\u8bf4\u660e'
                         % (name, pct(ach), signed(yoy)))
        if weight <= 0:
            warns.append('\u6307\u6807\u300c%s\u300d\u6743\u91cd\u4e3a 0\uff0c\u8bf7\u786e\u8ba4\u662f\u5426\u7eb3\u5165\u8003\u6838' % name)
        if direction == 'down' and tgt is not None and cur > tgt * 1.1:
            warns.append('\u6307\u6807\u300c%s\u300d\u8d85\u51fa\u76ee\u6807 10%% \u4ee5\u4e0a\uff0c\u5c5e\u672a\u8fbe\u6210\uff0c\u95ee\u9898\u6bb5\u9700\u7ed9\u6839\u56e0' % name)

    total = len(metrics)
    coverage = covered / total if total else 0.0
    weighted = None
    if scored_w > 0:
        weighted = scored_sum / scored_w

    verdict = '\u65e0\u6cd5\u5224\u5b9a'
    if weighted is not None:
        if weighted >= V_GOOD:
            verdict = '\u8fbe\u6210'
        elif weighted >= V_BASIC:
            verdict = '\u57fa\u672c\u8fbe\u6210'
        elif weighted >= V_PART:
            verdict = '\u90e8\u5206\u8fbe\u6210'
        else:
            verdict = '\u672a\u8fbe\u6210'

    if abs(wsum - 1.0) > 0.01 and total > 0:
        warns.append('\u6743\u91cd\u5408\u8ba1\u4e3a %.2f\uff0c\u5e94\u4e3a 1.00\uff0c\u5426\u5219\u52a0\u6743\u8fbe\u6210\u7387\u5931\u771f' % wsum)
    if total < N_MIN:
        warns.append('\u4ec5 %d \u9879\u6307\u6807\uff0c\u8ff0\u804c\u5efa\u8bae %d-%d \u9879\uff0c\u592a\u5c11\u663e\u5f97\u5de5\u4f5c\u91cf\u8584' % (total, N_BEST_LO, N_BEST_HI))
    if total > N_MAX:
        warns.append('\u5171 %d \u9879\u6307\u6807\uff0c\u8d85\u8fc7 %d \u9879\u540e\u6bcf\u9879\u90fd\u8bb2\u4e0d\u6df1\uff0c\u5efa\u8bae\u5408\u5e76\u5230 %d-%d \u9879'
                     % (total, N_MAX, N_BEST_LO, N_BEST_HI))
    if coverage < COVER_RED:
        warns.append('\u91cf\u5316\u8986\u76d6\u7387 %s \u4f4e\u4e8e %s\uff0c\u8bf4\u660e\u8ff0\u804c\u4ecd\u505c\u7559\u5728\u5b9a\u6027\u63cf\u8ff0\u9636\u6bb5\uff0c\u4e0d\u5efa\u8bae\u63d0\u4ea4'
                     % (pct(coverage, 0), pct(COVER_RED, 0)))
    if weighted is not None and weighted < V_BASIC:
        warns.append('\u52a0\u6743\u8fbe\u6210\u7387 %s \u4f4e\u4e8e 90%%\uff0c\u95ee\u9898\u6bb5\u5fc5\u987b\u7ed9\u6839\u56e0\u4e0e\u4e0b\u671f\u6539\u8fdb\u8ba1\u5212' % pct(weighted))

    blob = json.dumps(data, ensure_ascii=False)
    hit = [w for w in QUAL_WORDS if w in blob]
    if hit:
        warns.append('\u51fa\u73b0\u5b9a\u6027\u8bcd %s\uff0c\u9700\u66ff\u6362\u4e3a\u5177\u4f53\u6570\u503c\u4e0e\u53e3\u5f84' % '\u3001'.join(hit))

    return {
        'title': title,
        'owner': owner,
        'period': period,
        'count': total,
        'rows': rows,
        'weight_sum': round(wsum, 4),
        'coverage': round(coverage, 4),
        'weighted': None if weighted is None else round(weighted, 4),
        'verdict': verdict,
        'warns': warns,
        'qual_hits': hit,
    }


def render_md(r):
    L = []
    L.append('# \u8ff0\u804c\u91cf\u5316\u6838\u7b97\uff1a%s' % r['title'])
    L.append('')
    if r['owner'] or r['period']:
        L.append('- \u8ff0\u804c\u4eba\uff1a%s\u3000\u3000\u5468\u671f\uff1a%s' % (r['owner'] or '\u672a\u586b', r['period'] or '\u672a\u586b'))
        L.append('')
    L.append('## \u4e00\u3001\u9010\u6307\u6807\u91cf\u5316')
    L.append('')
    L.append('| \u6307\u6807 | \u672c\u671f | \u540c\u6bd4 | \u73af\u6bd4 | \u8fbe\u6210\u7387 | \u65b9\u5411 | \u7b49\u7ea7 | \u4ea4\u53c9\u6838\u67e5 |')
    L.append('|---|---|---|---|---|---|---|---|')
    for x in r['rows']:
        L.append('| %s | %s%s | %s | %s | %s | %s | %s | %s |'
                 % (x['name'], fmt_num(x['current']), x['unit'], signed(x['yoy']),
                    signed(x['mom']), pct(x['ach']), x['direction_label'],
                    x['grade'], x['quadrant']))
    L.append('')
    L.append('## \u4e8c\u3001\u6574\u4f53\u7ed3\u679c')
    L.append('')
    L.append('| \u6307\u6807 | \u503c | \u8bf4\u660e |')
    L.append('|---|---|---|')
    L.append('| \u52a0\u6743\u8fbe\u6210\u7387 | %s | \u5355\u9879\u6309 120%% \u5c01\u9876\u540e\u6309\u6743\u91cd\u52a0\u6743 |' % pct(r['weighted']))
    L.append('| \u91cf\u5316\u8986\u76d6\u7387 | %s | \u56db\u6570\u9f50\u5168\u7684\u6307\u6807\u5360\u6bd4\uff0c\u7ea2\u7ebf %s |' % (pct(r['coverage'], 0), pct(COVER_RED, 0)))
    L.append('| \u6743\u91cd\u5408\u8ba1 | %.2f | \u5e94\u4e3a 1.00 |' % r['weight_sum'])
    L.append('| \u6307\u6807\u6570\u91cf | %d | \u5efa\u8bae %d-%d \u9879 |' % (r['count'], N_BEST_LO, N_BEST_HI))
    L.append('| \u6574\u4f53\u5224\u5b9a | **%s** | |' % r['verdict'])
    L.append('')
    L.append('## \u4e09\u3001\u53e3\u5f84\u63d0\u793a')
    L.append('')
    L.append('- \u540c\u6bd4 =\uff08\u672c\u671f - \u4e0a\u5e74\u540c\u671f\uff09\u00f7 \u4e0a\u5e74\u540c\u671f\uff1b\u73af\u6bd4 =\uff08\u672c\u671f - \u4e0a\u4e00\u5468\u671f\uff09\u00f7 \u4e0a\u4e00\u5468\u671f')
    L.append('- \u8d8a\u5927\u8d8a\u597d\u7c7b\u8fbe\u6210\u7387 = \u672c\u671f \u00f7 \u76ee\u6807\uff1b\u8d8a\u5c0f\u8d8a\u597d\u7c7b\u8fbe\u6210\u7387 = \u76ee\u6807 \u00f7 \u672c\u671f\uff0c\u4e0d\u8981\u7b97\u53cd')
    L.append('- \u5355\u9879\u8fbe\u6210\u7387\u6309 120%% \u5c01\u9876\uff0c\u907f\u514d\u4e00\u9879\u8d85\u989d\u63a9\u76d6\u5176\u4ed6\u672a\u8fbe\u9879')
    L.append('')
    L.append('## \u56db\u3001\u63d0\u9192')
    L.append('')
    if r['warns']:
        for w in r['warns']:
            L.append('- %s' % w)
    else:
        L.append('- \u5f53\u524d\u53c2\u6570\u4e0b\u672a\u89e6\u53d1\u63d0\u9192')
    L.append('')
    L.append('## \u4e94\u3001\u4eba\u5de5\u786e\u8ba4\uff08\u811a\u672c\u4e0d\u4ee3\u66ff\uff09')
    L.append('')
    L.append('- [ ] \u76ee\u6807\u503c\u662f\u5e74\u521d\u5b9a\u7684\u8fd8\u662f\u5e74\u4e2d\u8c03\u7684\uff0c\u8c03\u6574\u8fc7\u7684\u5df2\u5199\u660e')
    L.append('- [ ] \u8d8a\u5c0f\u8d8a\u597d\u7c7b\u6307\u6807\uff08\u6545\u969c\u3001\u6210\u672c\u3001\u8017\u65f6\uff09\u8fbe\u6210\u7387\u6ca1\u6709\u7b97\u53cd')
    L.append('- [ ] \u6240\u6709\u6570\u5b57\u6709\u6765\u6e90\uff08\u7cfb\u7edf / \u53f0\u8d26 / \u62bd\u6837 + \u6837\u672c\u91cf\uff09')
    L.append('- [ ] \u56e2\u961f\u6210\u679c\u5199\u6e05\u4e86\u4eba\u6570\u3001\u5206\u5de5\u4e0e\u81ea\u5df1\u627f\u62c5\u7684\u90a3\u4e00\u6bb5')
    L.append('- [ ] \u95ee\u9898\u6bb5\u7ed3\u8bba\u53e5\u4e0d\u662f\u5f52\u56e0\u4ed6\u4eba')
    L.append('- [ ] \u5df2\u4ea4\u76f4\u5c5e\u4e0a\u7ea7\u6838\u8fc7\u4e00\u904d\u6570\u5b57\u53e3\u5f84')
    return '\n'.join(L)


def fmt_num(v):
    if v is None:
        return '\u672a\u586b'
    if abs(v - round(v)) < 1e-9:
        return '%d' % int(round(v))
    return '%.2f' % v


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


def selftest():
    errs = []
    checks = 0

    def ck(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            errs.append(msg)

    base = {'title': '\u6d4b\u8bd5\u8ff0\u804c', 'owner': '\u672c\u4eba', 'period': '2026 \u5e74\u5ea6',
            'metrics': [
                {'name': '\u9500\u552e\u989d', 'unit': '\u4e07\u5143', 'current': 1200, 'baseline': 950,
                 'previous': 1110, 'target': 1150, 'direction': 'up', 'weight': 0.7},
                {'name': '\u7ebf\u4e0a\u6545\u969c\u6b21\u6570', 'unit': '\u6b21', 'current': 18, 'baseline': 25,
                 'previous': 22, 'target': 20, 'direction': 'down', 'weight': 0.3},
            ]}

    # 1 \u540c\u6bd4\u4e0e\u73af\u6bd4
    r1 = calc(base)
    a = r1['rows'][0]
    ck(abs(a['yoy'] - (250.0 / 950.0)) < 1e-9, '\u7528\u4f8b1 \u540c\u6bd4\u5e94\u7ea6 +26.32%%\uff0c\u5b9e\u4e3a %s' % signed(a['yoy']))
    ck(abs(a['mom'] - (90.0 / 1110.0)) < 1e-9, '\u7528\u4f8b1 \u73af\u6bd4\u5e94\u7ea6 +8.11%%\uff0c\u5b9e\u4e3a %s' % signed(a['mom']))

    # 2 \u8fbe\u6210\u7387\uff08\u8d8a\u5927\u8d8a\u597d\uff09
    ck(abs(a['ach'] - (1200.0 / 1150.0)) < 1e-9,
       '\u7528\u4f8b2 \u8fbe\u6210\u7387\u5e94\u7ea6 104.35%%\uff0c\u5b9e\u4e3a %s' % pct(a['ach']))
    ck(a['grade'] == '\u8fbe\u6210', '\u7528\u4f8b2 \u7b49\u7ea7\u5e94\u4e3a\u8fbe\u6210\uff0c\u5b9e\u4e3a %s' % a['grade'])

    # 3 \u8fbe\u6210\u7387\uff08\u8d8a\u5c0f\u8d8a\u597d\uff09\u4e0d\u8bb8\u7b97\u53cd
    b = r1['rows'][1]
    ck(abs(b['ach'] - (20.0 / 18.0)) < 1e-9,
       '\u7528\u4f8b3 \u8d8a\u5c0f\u8d8a\u597d\u7c7b\u8fbe\u6210\u7387\u5e94\u4e3a\u76ee\u6807\u00f7\u5b9e\u9645\u7ea6 111.11%%\uff0c\u5b9e\u4e3a %s' % pct(b['ach']))
    ck(b['yoy'] < 0, '\u7528\u4f8b3 \u6545\u969c\u6b21\u6570\u4e0b\u964d\uff0c\u540c\u6bd4\u5e94\u4e3a\u8d1f\uff0c\u5b9e\u4e3a %s' % signed(b['yoy']))
    ck(b['grade'] == '\u8fbe\u6210', '\u7528\u4f8b3 \u7b49\u7ea7\u5e94\u4e3a\u8fbe\u6210\uff0c\u5b9e\u4e3a %s' % b['grade'])

    # 4 \u52a0\u6743\u8fbe\u6210\u7387\u4e0e\u5c01\u9876
    expect_w = (min(1200.0 / 1150.0, CAP) * 0.7 + min(20.0 / 18.0, CAP) * 0.3) / 1.0
    ck(abs(r1['weighted'] - expect_w) < 1e-4,
       '\u7528\u4f8b4 \u52a0\u6743\u8fbe\u6210\u7387\u5e94\u7ea6 %s\uff0c\u5b9e\u4e3a %s' % (pct(expect_w), pct(r1['weighted'])))
    r4 = calc({'metrics': [{'name': 'A', 'unit': '\u4ef6', 'current': 300, 'baseline': 100,
                            'target': 100, 'direction': 'up', 'weight': 1.0}]})
    ck(abs(r4['weighted'] - CAP) < 1e-4,
       '\u7528\u4f8b4 \u5355\u9879\u8d85\u989d 300%% \u5e94\u5c01\u9876\u5230 120%%\uff0c\u5b9e\u4e3a %s' % pct(r4['weighted']))

    # 5 \u91cf\u5316\u8986\u76d6\u7387
    ck(r1['coverage'] == 1.0, '\u7528\u4f8b5 \u56db\u6570\u9f50\u5168\u65f6\u8986\u76d6\u7387\u5e94\u4e3a 100%%\uff0c\u5b9e\u4e3a %s' % pct(r1['coverage'], 0))
    r5 = calc({'metrics': [
        {'name': 'B', 'unit': '\u4ef6', 'current': 10, 'target': 12, 'direction': 'up', 'weight': 1.0}]})
    ck(r5['coverage'] == 0.0, '\u7528\u4f8b5 \u7f3a\u57fa\u7ebf\u65f6\u8986\u76d6\u7387\u5e94\u4e3a 0%%\uff0c\u5b9e\u4e3a %s' % pct(r5['coverage'], 0))
    ck(any('\u57fa\u7ebf' in w for w in r5['warns']), '\u7528\u4f8b5 \u7f3a\u57fa\u7ebf\u5e94\u6709\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r5['warns'])

    # 6 \u8fbe\u6210\u8d85\u6807\u4f46\u540c\u6bd4\u4e0b\u6ed1\u5fc5\u987b\u63d0\u9192
    r6 = calc({'metrics': [{'name': 'C', 'unit': '\u4e07\u5143', 'current': 105, 'baseline': 120,
                            'previous': 110, 'target': 100, 'direction': 'up', 'weight': 1.0}]})
    ck(any('\u540c\u6bd4' in w and '\u76ee\u6807' in w for w in r6['warns']),
       '\u7528\u4f8b6 \u8fbe\u6210\u4f46\u540c\u6bd4\u4e0b\u6ed1\u5e94\u6709\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r6['warns'])
    ck(r6['rows'][0]['quadrant'] == '\u8fbe\u6210\u4f46\u540c\u6bd4\u4e0b\u6ed1',
       '\u7528\u4f8b6 \u4ea4\u53c9\u6838\u67e5\u5e94\u4e3a\u8fbe\u6210\u4f46\u540c\u6bd4\u4e0b\u6ed1\uff0c\u5b9e\u4e3a %s' % r6['rows'][0]['quadrant'])

    # 7 \u6743\u91cd\u5408\u8ba1\u4e0d\u4e3a 1 \u8981\u63d0\u9192
    r7 = calc({'metrics': [
        {'name': 'D', 'unit': '\u4ef6', 'current': 10, 'baseline': 8, 'target': 10, 'direction': 'up', 'weight': 0.3},
        {'name': 'E', 'unit': '\u4ef6', 'current': 10, 'baseline': 8, 'target': 10, 'direction': 'up', 'weight': 0.3}]})
    ck(any('\u6743\u91cd\u5408\u8ba1' in w for w in r7['warns']), '\u7528\u4f8b7 \u6743\u91cd\u5408\u8ba1 0.6 \u5e94\u6709\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r7['warns'])

    # 8 \u6307\u6807\u6570\u91cf\u5931\u8861
    r8 = calc({'metrics': [{'name': 'F', 'unit': '\u4ef6', 'current': 10, 'baseline': 8,
                            'target': 10, 'direction': 'up', 'weight': 1.0}]})
    ck(any('\u592a\u5c11' in w for w in r8['warns']), '\u7528\u4f8b8 \u5355\u9879\u6307\u6807\u5e94\u63d0\u9192\u592a\u5c11\uff0c\u5b9e\u4e3a %s' % r8['warns'])

    # 9 \u8986\u76d6\u7387\u4f4e\u4e8e\u7ea2\u7ebf
    r9 = calc({'metrics': [
        {'name': 'G', 'unit': '\u4ef6', 'current': 10, 'baseline': 8, 'target': 10, 'direction': 'up', 'weight': 0.5},
        {'name': 'H', 'unit': '\u4ef6', 'current': 10, 'target': 10, 'direction': 'up', 'weight': 0.5}]})
    ck(any('\u91cf\u5316\u8986\u76d6\u7387' in w for w in r9['warns']), '\u7528\u4f8b9 \u8986\u76d6\u7387 50%% \u5e94\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r9['warns'])

    # 10 \u5b9a\u6027\u8bcd\u68c0\u6d4b
    r10 = calc({'metrics': [{'name': 'I', 'unit': '', 'current': 10, 'baseline': 8,
                             'target': 10, 'direction': 'up', 'weight': 1.0}],
                'summary': '\u672c\u671f\u5de5\u4f5c\u6210\u6548\u663e\u8457\uff0c\u5706\u6ee1\u5b8c\u6210\u4efb\u52a1'})
    ck(any('\u5b9a\u6027\u8bcd' in w for w in r10['warns']), '\u7528\u4f8b10 \u5b9a\u6027\u8bcd\u5e94\u88ab\u68c0\u51fa\uff0c\u5b9e\u4e3a %s' % r10['warns'])
    ck(any('\u672a\u586b\u5355\u4f4d' in w for w in r10['warns']), '\u7528\u4f8b10 \u7a7a\u5355\u4f4d\u5e94\u63d0\u9192\uff0c\u5b9e\u4e3a %s' % r10['warns'])

    # 11 \u7b49\u7ea7\u5224\u5b9a\u6863\u4f4d
    g1 = calc({'metrics': [{'name': 'J', 'unit': '\u4ef6', 'current': 95, 'baseline': 90,
                            'target': 100, 'direction': 'up', 'weight': 1.0}]})
    ck(g1['rows'][0]['grade'] == '\u57fa\u672c\u8fbe\u6210', '\u7528\u4f8b11 95%% \u5e94\u4e3a\u57fa\u672c\u8fbe\u6210\uff0c\u5b9e\u4e3a %s' % g1['rows'][0]['grade'])
    g2 = calc({'metrics': [{'name': 'K', 'unit': '\u4ef6', 'current': 80, 'baseline': 90,
                            'target': 100, 'direction': 'up', 'weight': 1.0}]})
    ck(g2['rows'][0]['grade'] == '\u672a\u8fbe\u6210', '\u7528\u4f8b11 80%% \u5e94\u4e3a\u672a\u8fbe\u6210\uff0c\u5b9e\u4e3a %s' % g2['rows'][0]['grade'])
    ck(g2['verdict'] == '\u90e8\u5206\u8fbe\u6210', '\u7528\u4f8b11 \u6574\u4f53\u5e94\u4e3a\u90e8\u5206\u8fbe\u6210\uff0c\u5b9e\u4e3a %s' % g2['verdict'])

    # 12 \u6574\u4f53\u5224\u5b9a\u56db\u6863
    v = {}
    for cur, key in ((120, 'v120'), (95, 'v95'), (75, 'v75'), (50, 'v50')):
        v[key] = calc({'metrics': [{'name': 'L', 'unit': '\u4ef6', 'current': cur, 'baseline': 100,
                                    'target': 100, 'direction': 'up', 'weight': 1.0}]})['verdict']
    ck(v['v120'] == '\u8fbe\u6210', '\u7528\u4f8b12 120%% \u5e94\u4e3a\u8fbe\u6210\uff0c\u5b9e\u4e3a %s' % v['v120'])
    ck(v['v95'] == '\u57fa\u672c\u8fbe\u6210', '\u7528\u4f8b12 95%% \u5e94\u4e3a\u57fa\u672c\u8fbe\u6210\uff0c\u5b9e\u4e3a %s' % v['v95'])
    ck(v['v75'] == '\u90e8\u5206\u8fbe\u6210', '\u7528\u4f8b12 75%% \u5e94\u4e3a\u90e8\u5206\u8fbe\u6210\uff0c\u5b9e\u4e3a %s' % v['v75'])
    ck(v['v50'] == '\u672a\u8fbe\u6210', '\u7528\u4f8b12 50%% \u5e94\u4e3a\u672a\u8fbe\u6210\uff0c\u5b9e\u4e3a %s' % v['v50'])

    # 13 \u975e\u6cd5\u53c2\u6570\u5e94\u62a5\u9519
    bad_list = [
        {'metrics': []},
        {'metrics': [{'name': 'M', 'current': 1, 'direction': 'sideways'}]},
        {'metrics': [{'name': 'M', 'direction': 'up'}]},
    ]
    for bd in bad_list:
        try:
            calc(bd)
            ck(False, '\u7528\u4f8b13 \u975e\u6cd5\u53c2\u6570 %s \u5e94\u629b\u9519' % bd)
        except ValueError:
            ck(True, '\u7528\u4f8b13 \u975e\u6cd5\u53c2\u6570 %s \u5e94\u629b\u9519' % bd)

    # 14 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r1)
    for kw in ('\u52a0\u6743\u8fbe\u6210\u7387', '\u91cf\u5316\u8986\u76d6\u7387', '\u4ea4\u53c9\u6838\u67e5', '\u4eba\u5de5\u786e\u8ba4'):
        ck(kw in md, '\u7528\u4f8b14 Markdown \u5e94\u5305\u542b %s' % kw)
    j = json.loads(render_json(r1))
    ck(j['verdict'] == r1['verdict'], '\u7528\u4f8b14 JSON \u5224\u5b9a\u5e94\u4e0e\u8ba1\u7b97\u7ed3\u679c\u4e00\u81f4')
    ck(pct(0.2632, 1) == '26.3%', '\u7528\u4f8b14 pct \u683c\u5f0f\u5316\u5e94\u4e3a 26.3%%\uff0c\u5b9e\u4e3a %s' % pct(0.2632, 1))
    ck(signed(-0.125) == '-12.5%', '\u7528\u4f8b14 signed \u8d1f\u53f7\u683c\u5f0f\u9519\uff0c\u5b9e\u4e3a %s' % signed(-0.125))

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errs:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errs)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u540c\u6bd4/\u73af\u6bd4/\u8fbe\u6210\u7387(up)/\u8fbe\u6210\u7387(down)/\u5c01\u9876/\u52a0\u6743\u8fbe\u6210\u7387/'
               '\u91cf\u5316\u8986\u76d6\u7387/\u6743\u91cd\u5408\u8ba1/\u6307\u6807\u6570\u91cf/\u5b9a\u6027\u8bcd/\u7b49\u7ea7\u6863\u4f4d/\u6574\u4f53\u5224\u5b9a/\u975e\u6cd5\u53c2\u6570/\u8f93\u51fa\u7ed3\u6784' % checks)
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u8ff0\u804c\u4e1a\u7ee9\u91cf\u5316\u6838\u67e5')
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
            print('ERROR --file \u4e0d\u5b58\u5728')
            return 2
        raw = open(a.file, 'r', encoding='utf-8', errors='replace').read()
    if not raw.strip():
        print('ERROR \u9700\u8981 --file \u6216 --text')
        return 2
    try:
        data = json.loads(raw)
    except ValueError:
        print('ERROR JSON \u89e3\u6790\u5931\u8d25')
        return 2
    try:
        r = calc(data)
    except ValueError as e:
        print('ERROR %s' % e)
        return 2

    out = render_md(r) if a.format == 'md' else render_json(r)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    target = a.out or os.path.join(out_dir, '_last_result.txt')
    with open(target, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % target)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
