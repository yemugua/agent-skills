# -*- coding: utf-8 -*-
"""\u5411\u4e0a\u7ba1\u7406\u8282\u594f\u4e0e\u6c47\u62a5\u5bf9\u9f50\u6838\u67e5\uff1a\u8282\u594f\u5b8c\u6574\u7387\u3001\u7a7a\u8f6c\u7387\u3001\u574f\u6d88\u606f\u5ef6\u8fdf\u3001\u8d8a\u7ea7\u7ea2\u7ebf\u3002

\u7528\u6cd5:
  python report_cadence_check.py --file cadence.json [--out result.md] [--format json]
  python report_cadence_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

LEVELS = ('day', 'week', 'month', 'quarter')
LEVEL_CN = {
    'day': '\u65e5\u6863',
    'week': '\u5468\u6863',
    'month': '\u6708\u6863',
    'quarter': '\u5b63\u6863',
}

# \u7a7a\u8f6c\u5224\u5b9a\u9608\u503c
COVERAGE_RED = 80.0
# \u574f\u6d88\u606f\u4e0a\u62a5\u65f6\u9650\uff08\u5c0f\u65f6\uff09\u3002P0 \u7acb\u5373\u6309 0 \u5904\u7406\uff0c\u5176\u4f59\u6309 4 \u5c0f\u65f6\u3002
LIMIT_HOURS = 4.0
P0_CATEGORIES = ('safety', 'compliance', 'fund', 'legal', 'data-leak')

# \u6c47\u62a5\u5f52\u56e0\u53e5\u7684\u7529\u9505\u7279\u5f81\u8bcd\uff1a\u7ed3\u8bba\u53e5\u4e3b\u8bed\u4f4d\u7f6e\u51fa\u73b0\u5373\u63d0\u793a
BLAME_PATTERNS = ('\u56e0\u4e3a\u5176\u4ed6\u90e8\u95e8', '\u56e0\u4e3a\u522b\u7684\u90e8\u95e8', '\u7531\u4e8e\u8d44\u6e90\u4e0d\u8db3', '\u522b\u7684\u90e8\u95e8\u4e0d\u914d\u5408',
                  '\u4ed6\u4eec\u4e0d\u914d\u5408', '\u5168\u662f\u4ed6\u4eec\u7684\u95ee\u9898', '\u8fd9\u4e0d\u662f\u6211\u7684\u95ee\u9898')


def load(text=None, path=None):
    if text:
        return json.loads(text)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def cadence_check(data):
    """\u8fd4\u56de (\u6761\u76ee\u5217\u8868, \u5b8c\u6574\u7387, \u7a7a\u8f6c\u6761\u76ee\u5217\u8868, \u7f3a\u5931\u6863\u4f4d\u5217\u8868)"""
    plan = data.get('cadence_plan') or []
    rows = []
    good = 0
    idle = []
    seen = set()
    missing = []
    for lv in LEVELS:
        hit = [p for p in plan if p.get('level') == lv]
        if not hit:
            missing.append(LEVEL_CN[lv])
            continue
        seen.add(lv)
        for p in hit:
            gaps = []
            if not p.get('fixed_time'):
                gaps.append('\u65e0\u56fa\u5b9a\u65f6\u70b9')
            if not p.get('audience'):
                gaps.append('\u65e0\u6c47\u62a5\u5bf9\u8c61')
            if not p.get('content'):
                gaps.append('\u65e0\u5185\u5bb9\u5b57\u6bb5')
            if not p.get('form'):
                gaps.append('\u65e0\u5f62\u5f0f\u7ea6\u5b9a')
            status = '\u5b8c\u6574' if not gaps else '\u7a7a\u8f6c'
            if gaps:
                idle.append((LEVEL_CN[lv], gaps))
            else:
                good += 1
            rows.append({'level': LEVEL_CN[lv], 'content': p.get('content') or '\uff08\u672a\u586b\uff09',
                         'audience': p.get('audience') or '\uff08\u672a\u586b\uff09',
                         'form': p.get('form') or '\uff08\u672a\u586b\uff09',
                         'fixed_time': p.get('fixed_time') or '\uff08\u672a\u586b\uff09',
                         'status': status, 'gaps': gaps})
    coverage = 0.0
    if plan:
        coverage = round(good * 100.0 / len(plan), 1)
    return rows, coverage, idle, missing


def bad_news_check(data):
    """\u574f\u6d88\u606f\u65f6\u9650\u5224\u5b9a\uff1aP0 \u7acb\u5373\uff1b\u5f71\u54cd\u4e0b\u6e38 4 \u5c0f\u65f6\uff1b\u5426\u5219\u6b21\u65e5\u3002"""
    items = data.get('bad_news') or []
    rows = []
    late = 0
    for it in items:
        cat = (it.get('category') or '').strip()
        hrs = it.get('discovered_hours_ago')
        try:
            hrs = float(hrs)
        except (TypeError, ValueError):
            hrs = None
        reported = bool(it.get('reported'))
        if cat in P0_CATEGORIES:
            limit = 0.0
            grade = '\u7acb\u5373'
        elif it.get('has_downstream'):
            limit = LIMIT_HOURS
            grade = '\u5f53\u5929'
        else:
            limit = 24.0
            grade = '\u6b21\u65e5'
        if hrs is None:
            verdict = '\u7f3a\u5c11\u53d1\u73b0\u65f6\u95f4\uff0c\u65e0\u6cd5\u5224\u5b9a\u65f6\u9650'
            state = '\u672a\u77e5'
        else:
            if reported:
                if limit <= 0 and hrs > limit:
                    verdict = '\u5df2\u4e0a\u62a5\uff0c\u4f46\u5df2\u8fc7 %.0f \u5c0f\u65f6\uff0c\u6d89 P0 \u5e94\u7acb\u5373\u4e0a\u62a5' % hrs
                    state = '\u8fdf\u62a5'
                    late += 1
                elif hrs > limit:
                    verdict = '\u5df2\u4e0a\u62a5\uff0c\u8d85\u8fc7 %s \u65f6\u9650\uff08%.0f \u5c0f\u65f6\uff09' % (grade, limit)
                    state = '\u8fdf\u62a5'
                    late += 1
                else:
                    verdict = '\u5df2\u4e0a\u62a5\uff0c\u5728 %s \u65f6\u9650\u5185\uff08%.0f \u5c0f\u65f6\uff09' % (grade, limit)
                    state = '\u5408\u89c4'
            else:
                verdict = '\u672a\u4e0a\u62a5\uff0c\u5e94\u5728 %s \u65f6\u9650\u5185\u4e0a\u62a5' % grade
                state = '\u672a\u4e0a\u62a5'
                late += 1
        rows.append({'item': it.get('item') or '\uff08\u672a\u547d\u540d\uff09', 'grade': grade,
                     'limit': limit, 'hours': hrs, 'state': state, 'verdict': verdict})
    return rows, late


def skip_check(data):
    """\u8d8a\u7ea7\u6c47\u62a5\u56db\u6761\u7ea2\u7ebf\u3002"""
    items = data.get('upward_skips') or []
    rows = []
    risk = 0
    for it in items:
        flags = []
        if not it.get('reason'):
            flags.append('\u7ea2\u7ebf1/2\uff1a\u672a\u8bf4\u660e\u7d27\u6025\u7406\u7531')
        if not it.get('told_direct_first'):
            flags.append('\u7ea2\u7ebf2\uff1a\u672a\u5148\u544a\u77e5\u76f4\u5c5e\u4e0a\u7ea7')
        if not it.get('conclusion_only'):
            flags.append('\u7ea2\u7ebf3\uff1a\u7591\u4f3c\u5305\u542b\u7ed3\u8bba\u6216\u5bf9\u4eba\u7684\u8bc4\u4ef7')
        if it.get('ask_resource') or it.get('ask_commitment'):
            flags.append('\u7ea2\u7ebf4\uff1a\u8d8a\u7ea7\u8981\u8d44\u6e90\u6216\u8981\u627f\u8bfa')
        if flags:
            risk += 1
        rows.append({'reason': it.get('reason') or '\uff08\u672a\u586b\uff09',
                     'told': bool(it.get('told_direct_first')),
                     'only_fact': bool(it.get('conclusion_only')),
                     'flags': flags,
                     'state': '\u89e6\u7ebf' if flags else '\u5408\u89c4'})
    return rows, risk


def blame_scan(text):
    """\u626b\u51fa\u7529\u9505\u53e5\uff0c\u8fd4\u56de\u547d\u4e2d\u5217\u8868\u3002"""
    if not text:
        return []
    return [w for w in BLAME_PATTERNS if w in text]


def build(data, fmt='md'):
    title = data.get('title') or '\u5411\u4e0a\u7ba1\u7406\u8282\u594f\u4f53\u68c0'
    owner = data.get('owner') or '\uff08\u672a\u586b\uff09'
    rows, coverage, idle, missing = cadence_check(data)
    bn_rows, bn_late = bad_news_check(data)
    sk_rows, sk_risk = skip_check(data)
    blame = blame_scan(data.get('recent_report_text'))

    out = []
    if fmt == 'json':
        return {'title': title, 'owner': owner,
                'cadence_coverage': coverage, 'idle': [i[0] for i in idle],
                'missing_levels': missing,
                'cadence': rows, 'bad_news': bn_rows,
                'bad_news_late': bn_late,
                'upward_skips': sk_rows, 'skip_risk': sk_risk,
                'blame_hits': blame}
    out.append('# %s' % title)
    out.append('')
    out.append('- \u5bf9\u8c61\uff1a%s' % owner)
    out.append('- \u6c47\u62a5\u53d7\u4f17\u6570\uff1a%d' % len(data.get('audiences') or []))
    out.append('- \u8282\u594f\u5b8c\u6574\u7387\uff1a%.1f%%' % coverage)
    out.append('- \u7a7a\u8f6c\u6863\u4f4d\u6570\uff1a%d' % len(idle))
    out.append('- \u7f3a\u5931\u6863\u4f4d\uff1a%s' % ('\u3001'.join(missing) if missing else '\u65e0'))
    out.append('- \u574f\u6d88\u606f\u8fdf\u62a5/\u672a\u62a5\u6570\uff1a%d' % bn_late)
    out.append('- \u8d8a\u7ea7\u89e6\u7ebf\u6761\u6570\uff1a%d' % sk_risk)
    out.append('- \u7529\u9505\u53e5\u547d\u4e2d\uff1a%s' % ('\u3001'.join(blame) if blame else '\u65e0'))
    out.append('')
    out.append('## \u4e00\u3001\u8282\u594f\u8868\u4f53\u68c0')
    out.append('')
    out.append('| \u6863\u4f4d | \u5185\u5bb9 | \u6c47\u62a5\u5bf9\u8c61 | \u5f62\u5f0f | \u56fa\u5b9a\u65f6\u70b9 | \u5224\u5b9a | \u7f3a\u53e3 |')
    out.append('|---|---|---|---|---|---|---|')
    for r in rows:
        out.append('| %s | %s | %s | %s | %s | %s | %s |' % (
            r['level'], r['content'], r['audience'], r['form'], r['fixed_time'],
            r['status'], '\u3001'.join(r['gaps']) if r['gaps'] else '-'))
    out.append('')
    out.append('## \u4e8c\u3001\u574f\u6d88\u606f\u4e0a\u62a5\u65f6\u9650')
    out.append('')
    out.append('| \u4e8b\u9879 | \u5206\u7ea7 | \u65f6\u9650(h) | \u53d1\u73b0\u81f3\u4eca(h) | \u72b6\u6001 | \u5224\u5b9a |')
    out.append('|---|---|---|---|---|---|')
    for r in bn_rows:
        out.append('| %s | %s | %.0f | %s | %s | %s |' % (
            r['item'], r['grade'], r['limit'],
            ('%.0f' % r['hours']) if r['hours'] is not None else '\u672a\u77e5',
            r['state'], r['verdict']))
    out.append('')
    out.append('## \u4e09\u3001\u8d8a\u7ea7\u6c47\u62a5\u7ea2\u7ebf')
    out.append('')
    if not sk_rows:
        out.append('\u672a\u8bb0\u5f55\u8d8a\u7ea7\u6c9f\u901a\u3002')
    else:
        out.append('| \u7406\u7531 | \u5df2\u5148\u544a\u77e5\u672c\u7ea7 | \u4ec5\u540c\u6b65\u4e8b\u5b9e | \u5224\u5b9a | \u89e6\u7ebf |')
        out.append('|---|---|---|---|---|')
        for r in sk_rows:
            out.append('| %s | %s | %s | %s | %s |' % (
                r['reason'], '\u662f' if r['told'] else '\u5426',
                '\u662f' if r['only_fact'] else '\u5426', r['state'],
                '\uff1b'.join(r['flags']) if r['flags'] else '-'))
    out.append('')
    out.append('## \u56db\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if coverage < COVERAGE_RED:
        idx += 1
        out.append('%d. \u8282\u594f\u5b8c\u6574\u7387 %.1f%% \u4f4e\u4e8e %.0f%%\uff1a\u7ed9\u6bcf\u4e2a\u6863\u4f4d\u8865\u9f50\u300c\u56fa\u5b9a\u65f6\u70b9 + \u6c47\u62a5\u5bf9\u8c61 + \u5f62\u5f0f\u300d\u4e09\u9879\uff0c\u7f3a\u6863\u4f4d\u5199\u660e\u4e0d\u505a\u7684\u7406\u7531\u3002'
                   % (idx, coverage, COVERAGE_RED))
    if missing:
        idx += 1
        out.append('%d. \u7f3a\u5931\u6863\u4f4d %s\uff1a\u82e5\u786e\u5b9a\u4e0d\u9700\u8981\uff0c\u5199\u660e\u7406\u7531\uff08\u5982\u56e2\u961f\u4ec5 3 \u4eba\uff0c\u6708\u62a5\u4e0e\u5468\u62a5\u5408\u5e76\uff09\uff0c\u4e0d\u8981\u9ed8\u9ed8\u7a7a\u7740\u3002'
                   % (idx, '\u3001'.join(missing)))
    if bn_late:
        idx += 1
        out.append('%d. \u6709 %d \u9879\u574f\u6d88\u606f\u8fdf\u62a5\u6216\u672a\u4e0a\u62a5\uff1a\u6309\u300c\u4e8b\u5b9e-\u5f71\u54cd-\u5f52\u56e0-\u65b9\u6848\u300d\u56db\u6b65\u5f53\u5929\u53d1\u51fa\uff0c\u5e76\u4fdd\u7559 IM \u6216\u7eaa\u8981\u7559\u75d5\u3002'
                   % (idx, bn_late))
    if sk_risk:
        idx += 1
        out.append('%d. \u8d8a\u7ea7\u6c9f\u901a\u6709 %d \u5904\u89e6\u7ebf\uff1a\u5148\u672c\u7ea7\u6c9f\u901a\u5e76\u8bb0\u5f55\u65f6\u95f4\uff0c\u786e\u6709\u635f\u5931\u98ce\u9669\u65f6\u4ee5\u300c\u540c\u6b65\u8fdb\u5c55\u300d\u540d\u4e49\u540c\u6b65\u9694\u7ea7\u5e76\u6284\u9001\u672c\u7ea7\u3002'
                   % (idx, sk_risk))
    if blame:
        idx += 1
        out.append('%d. \u6c47\u62a5\u6587\u672c\u547d\u4e2d\u7529\u9505\u53e5 %s\uff1a\u7ed3\u8bba\u53e5\u4e3b\u8bed\u6539\u6210\u81ea\u5df1\u7684\u52a8\u4f5c\u3002'
                   % (idx, '\u3001'.join(blame)))
    if not idx:
        out.append('\u8282\u594f\u8868\u7ed3\u6784\u4e0e\u65f6\u9650\u5747\u5408\u89c4\uff0c\u7ee7\u7eed\u4fdd\u6301\u56fa\u5b9a\u65f6\u70b9\u4e0e\u300c\u9700\u8981\u300d\u6bb5\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    ok = 0
    fails = []

    def chk(cond, name):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(name)

    full = {
        'title': 'T', 'owner': 'me',
        'cadence_plan': [
            {'level': lv, 'content': 'c', 'audience': 'a', 'form': 'f',
             'fixed_time': 'x'} for lv in LEVELS
        ],
        'bad_news': [], 'upward_skips': [],
    }
    r = build(full, 'json')
    chk(r['cadence_coverage'] == 100.0, '\u56db\u6863\u9f50\u5168\u5b8c\u6574\u7387\u5e94\u4e3a 100')
    chk(r['missing_levels'] == [], '\u56db\u6863\u9f50\u5168\u4e0d\u5e94\u6709\u7f3a\u5931')

    partial = {'cadence_plan': [
        {'level': 'day', 'content': 'c', 'audience': 'a', 'form': 'f', 'fixed_time': 'x'},
        {'level': 'week', 'content': '', 'audience': '', 'form': ''},
    ]}
    r = build(partial, 'json')
    chk(abs(r['cadence_coverage'] - 50.0) < 0.01, '\u4e24\u6761\u4e2d\u4e00\u6761\u5b8c\u6574\uff0c\u5b8c\u6574\u7387\u5e94\u4e3a 50')
    chk(len(r['idle']) == 1, '\u5e94\u6709 1 \u6761\u7a7a\u8f6c')
    chk(r['missing_levels'] == ['\u6708\u6863', '\u5b63\u6863'], '\u53ea\u6709\u65e5\u5468\u6863\u65f6\u7f3a\u6708\u6863\u5b63\u6863')

    r = build({'cadence_plan': []}, 'json')
    chk(r['cadence_coverage'] == 0.0, '\u7a7a\u8ba1\u5212\u5b8c\u6574\u7387\u4e3a 0')
    chk(len(r['missing_levels']) == 4, '\u7a7a\u8ba1\u5212\u5e94\u7f3a 4 \u6863')

    bn_on_time = {'bad_news': [{'item': 'A', 'category': 'schedule',
                                 'discovered_hours_ago': 2,
                                 'has_downstream': True, 'reported': True}]}
    r = build(bn_on_time, 'json')
    chk(r['bad_news'][0]['state'] == '\u5408\u89c4', '\u5f71\u54cd\u4e0b\u6e38 2 \u5c0f\u65f6\u5185\u4e0a\u62a5\u5e94\u5408\u89c4')
    chk(r['bad_news'][0]['limit'] == 4.0, '\u5f71\u54cd\u4e0b\u6e38\u65f6\u9650\u5e94\u4e3a 4 \u5c0f\u65f6')

    bn_late = {'bad_news': [{'item': 'B', 'category': 'schedule',
                             'discovered_hours_ago': 10,
                             'has_downstream': True, 'reported': False}]}
    r = build(bn_late, 'json')
    chk(r['bad_news'][0]['state'] == '\u672a\u4e0a\u62a5', '\u672a\u4e0a\u62a5\u5e94\u5224\u672a\u4e0a\u62a5')
    chk(r['bad_news_late'] == 1, '\u672a\u62a5\u8ba1\u6570\u5e94\u4e3a 1')

    p0 = {'bad_news': [{'item': 'C', 'category': 'compliance',
                        'discovered_hours_ago': 1, 'reported': True}]}
    r = build(p0, 'json')
    chk(r['bad_news'][0]['limit'] == 0.0, '\u5408\u89c4\u7c7b\u65f6\u9650\u5e94\u4e3a 0')
    chk(r['bad_news'][0]['state'] == '\u8fdf\u62a5', '\u5408\u89c4\u7c7b 1 \u5c0f\u65f6\u540e\u4e0a\u62a5\u5e94\u5224\u8fdf\u62a5')

    p2 = {'bad_news': [{'item': 'D', 'category': 'self',
                        'discovered_hours_ago': 10, 'has_downstream': False,
                        'reported': False}]}
    r = build(p2, 'json')
    chk(r['bad_news'][0]['limit'] == 24.0, '\u65e0\u4e0b\u6e38\u65f6\u9650\u5e94\u4e3a 24 \u5c0f\u65f6')

    sk_bad = {'upward_skips': [{'reason': '', 'told_direct_first': False,
                               'conclusion_only': False, 'ask_resource': True}]}
    r = build(sk_bad, 'json')
    chk(r['skip_risk'] == 1, '\u8d8a\u7ea7\u89e6\u7ebf\u5e94\u8ba1\u6570 1')
    chk(len(r['upward_skips'][0]['flags']) >= 3, '\u5e94\u547d\u4e2d\u81f3\u5c11 3 \u6761\u7ea2\u7ebf')

    sk_ok = {'upward_skips': [{'reason': '\u6d89\u5b89\u5168\u98ce\u9669',
                               'told_direct_first': True, 'conclusion_only': True}]}
    r = build(sk_ok, 'json')
    chk(r['skip_risk'] == 0, '\u5408\u89c4\u8d8a\u7ea7\u4e0d\u5e94\u8ba1\u6570')

    blame = build({'recent_report_text': '\u56e0\u4e3a\u5176\u4ed6\u90e8\u95e8\u4e0d\u914d\u5408\u6240\u4ee5\u5ef6\u671f'}, 'json')
    chk(len(blame['blame_hits']) == 1, '\u7529\u9505\u53e5\u5e94\u547d\u4e2d 1 \u6761')
    clean = build({'recent_report_text': '\u6211\u5df2\u4e24\u6b21\u50ac\u529e\uff0c\u9700\u534f\u8c03\u5347\u7ea7'}, 'json')
    chk(clean['blame_hits'] == [], '\u6b63\u5e38\u8868\u8ff0\u4e0d\u5e94\u547d\u4e2d')

    txt = build(full, 'md')
    chk('\u8282\u594f\u5b8c\u6574\u7387' in txt, 'md \u8f93\u51fa\u5e94\u542b\u5b8c\u6574\u7387')
    chk('\u6574\u6539\u5efa\u8bae' in txt, 'md \u8f93\u51fa\u5e94\u542b\u6574\u6539\u5efa\u8bae')

    if fails:
        lines = ['SELFTEST FAIL: %d/%d passed' % (ok, ok + len(fails))]
        for f in fails:
            lines.append('  - %s' % f)
        text = '\n'.join(lines)
    else:
        text = 'SELFTEST OK: %d assertions passed' % ok
    return text


def write_out(text, out):
    if not out:
        base = os.path.dirname(os.path.abspath(__file__))
        out = os.path.join(base, '_last_result.txt')
    d = os.path.dirname(os.path.abspath(out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    return out


def main():
    ap = argparse.ArgumentParser(description='\u5411\u4e0a\u7ba1\u7406\u8282\u594f\u4e0e\u6c47\u62a5\u5bf9\u9f50\u6838\u67e5')
    ap.add_argument('--file', help='\u8f93\u5165 JSON \u8def\u5f84')
    ap.add_argument('--text', help='\u76f4\u63a5\u7ed9 JSON \u5b57\u7b26\u4e32')
    ap.add_argument('--out', help='\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', choices=['md', 'json'], default='md')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    if a.selftest:
        res = selftest()
        p = write_out(res, os.path.join(here, '_selftest_result.txt'))
        print('SELFTEST -> %s' % p)
        print(res)
        return 0 if res.startswith('SELFTEST OK') else 1
    if not a.file and not a.text:
        ap.print_help()
        return 2
    data = load(a.text, a.file)
    if a.format == 'json':
        out = json.dumps(build(data, 'json'), ensure_ascii=False, indent=2)
    else:
        out = build(data, 'md')
    p = write_out(out, a.out)
    print('written: %s' % p)
    return 0


if __name__ == '__main__':
    sys.exit(main())