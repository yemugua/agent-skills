# -*- coding: utf-8 -*-
"""\u6c47\u62a5\u903b\u8f91\u6838\u67e5\uff1a\u8bba\u70b9\u6536\u655b\u3001MECE\u3001\u5c42\u7ea7\u4e00\u81f4\u3001\u56fe\u8868\u9009\u914d\u3002

\u7528\u6cd5:
  python logic_check.py --file logic.json [--out result.md] [--format json]
  python logic_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u5206\u652f\u6570\u91cf\u533a\u95f4
N_MIN = 1
N_BEST_LO = 3
N_BEST_HI = 5
N_MAX = 7
# \u56fe\u8868\u6570\u636e\u70b9\u4e0a\u9650
CHART_ITEMS_MAX = 7
# \u56fe\u8868\u7c7b\u578b -> \u9002\u914d\u7684\u8868\u8fbe\u610f\u56fe
CHART_FIT = {
    'line': ('trend',),
    'bar': ('compare',),
    'pie': ('compose',),
    'scatter': ('correlate',),
    'table': ('compare', 'compose'),
    'gantt': ('schedule',),
    'hist': ('distribution',),
    'flow': ('flow',),
    'flowchart': ('flow',),
}
PURPOSE_CN = {
    'trend': '\u65f6\u95f4\u8d8b\u52bf',
    'compare': '\u7c7b\u76ee\u6bd4\u8f83',
    'compose': '\u6784\u6210\u5360\u6bd4',
    'correlate': '\u53d8\u91cf\u5173\u8054',
    'flow': '\u6d41\u7a0b\u9636\u6bb5',
    'schedule': '\u65f6\u95f4\u8de8\u5ea6',
    'distribution': '\u6570\u636e\u5206\u5e03',
}

# \u5197\u4f59\u4e0e\u7a7a\u8f6c\u8868\u8ff0
REDUNDANT = ('\u5148\u8bf4\u4e00\u4e0b\u80cc\u666f', '\u4f17\u6240\u5468\u77e5', '\u5927\u5bb6\u90fd\u77e5\u9053', '\u4f17\u6240\u5468\u77e5\u7684\u662f',
             '\u5927\u5bb6\u90fd\u77e5\u9053\u7684', '\u5148\u8bb2\u4e2a\u9898\u5916\u8bdd', '\u8dd1\u9898\u4e00\u4e0b',
             '\u6211\u5148\u7ed9\u5927\u5bb6\u79d1\u666e\u4e00\u4e0b', '\u987a\u4fbf\u8bf4\u4e00\u4e0b')

# \u9876\u53e5\u975e\u5224\u65ad\u53e5\u4fe1\u53f7\uff08\u8bdd\u9898\u5f0f\uff09
TOPIC_MARK = ('\u5173\u4e8e', '\u7684\u5206\u6790', '\u7684\u60c5\u51b5', '\u7684\u6c47\u62a5', '\u7684\u8bf4\u660e', '\u4ecb\u7ecd',
              '\u6d45\u8c08', '\u521d\u63a2')


def load(text=None, path=None):
    if text:
        return json.loads(text)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def top_check(data):
    lead = (data.get('lead_sentence') or '').strip()
    cf = bool(data.get('conclusion_first'))
    rows = []
    issues = []
    if not lead:
        issues.append('\u672a\u586b\u9876\u53e5\uff1a\u5148\u5b9a\u4e00\u53e5\u8bdd\u7ed3\u8bba\uff0c\u8fd9\u5c01\u6c47\u62a5\u5982\u679c\u53ea\u7559\u4e00\u53e5\u7559\u54ea\u53e5')
    else:
        topic_like = any(m in lead for m in TOPIC_MARK)
        has_verdict = any(k in lead for k in ('\u5efa\u8bae', '\u5e94\u8be5', '\u9700\u8981', '\u51b3\u5b9a',
                                              '\u7ed3\u8bba', '\u56e0\u6b64', '\u6240\u4ee5', '\u4e0d\u5e94'))
        if topic_like and not has_verdict:
            issues.append('\u9876\u53e5\u50cf\u8bdd\u9898\u800c\u975e\u5224\u65ad\uff1a%s' % lead)
        if len(lead) < 8:
            issues.append('\u9876\u53e5\u8fc7\u77ed\uff08%d \u5b57\uff09\uff0c\u901a\u5e38\u4e00\u53e5\u5b8c\u6574\u5224\u65ad\u81f3\u5c11 15 \u5b57' % len(lead))
        rows.append({'lead': lead, 'topic_like': topic_like,
                     'has_verdict': has_verdict,
                     'state': '\u5408\u683c' if not topic_like and has_verdict else '\u5f85\u6539'})
    if not cf:
        issues.append('\u7ed3\u8bba\u672a\u5148\u884c\uff1a\u9876\u53e5\u5e94\u653e\u5728\u7b2c\u4e00\u6bb5\uff0c\u4e0d\u4ece\u80cc\u666f\u8bb2\u8d77')
    return rows, issues, cf


def scqa_check(data):
    sc = data.get('scqa') or {}
    keys = (('s', '\u60c5\u5883 S'), ('c', '\u51b2\u7a81 C'), ('q', '\u95ee\u9898 Q'), ('a', '\u7b54\u6848 A'))
    rows = []
    miss = []
    for k, cn in keys:
        v = (sc.get(k) or '').strip()
        if not v:
            miss.append(cn)
        rows.append({'key': cn, 'text': v or '\uff08\u672a\u586b\uff09',
                     'state': '\u6709' if v else '\u7f3a'})
    issues = []
    if miss:
        issues.append('SCQA \u7f3a\uff1a%s' % '\u3001'.join(miss))
    s_len = len((sc.get('s') or '').strip())
    if s_len > 60:
        issues.append('S\uff08\u60c5\u5883\uff09%d \u5b57\u8fc7\u957f\uff1a\u60c5\u666f\u94fa\u57ab\u957f\u4e86\u8bfb\u8005\u6293\u4e0d\u5230\u51b2\u7a81' % s_len)
    return rows, issues


def branch_check(data):
    bs = data.get('branches') or []
    rows = []
    names = set()
    rows = []
    issues = []
    dims = set()
    overlaps = 0
    placeholders = 0
    not_support = 0
    mixed = 0
    for b in bs:
        name = b.get('name') or '\uff08\u672a\u547d\u540d\uff09'
        names.add(name)
    for b in bs:
        name = b.get('name') or '\uff08\u672a\u547d\u540d\uff09'
        dim = b.get('dimension') or ''
        dims.add(dim)
        ov = b.get('overlaps') or []
        ph = bool(b.get('placeholder'))
        sup = b.get('supports_top')
        gran = b.get('granularity') or 'same'
        if ov:
            overlaps += 1
        if ph:
            placeholders += 1
        if sup is False:
            not_support += 1
        if gran == 'mixed':
            mixed += 1
        issues_row = []
        if ov:
            issues_row.append('\u4e0e %s \u91cd\u53e0' % '\u3001'.join(ov))
        if ph:
            issues_row.append('\u300c\u5176\u4ed6\u300d\u5360\u4f4d\uff0c\u4e0d\u662f\u771f\u5b9e\u5206\u7c7b')
        if sup is False:
            issues_row.append('\u4e0d\u652f\u6491\u9876\u53e5')
        if gran == 'mixed':
            issues_row.append('\u7c92\u5ea6\u4e0d\u9f50')
        rows.append({'name': name, 'dimension': dim or '\uff08\u672a\u586b\uff09',
                     'placeholder': ph, 'overlaps': ov,
                     'supports_top': sup, 'granularity': gran,
                     'flags': issues_row,
                     'state': '\u5408\u683c' if not issues_row else '\u5f85\u6539'})
    n = len(bs)
    dim_rate = 100.0 if n <= 1 else round(
        (1.0 - (len(dims) - 1) / float(max(1, n - 1))) * 100.0, 1)
    sup_rate = 0.0
    sup_n = 0
    for b in bs:
        if b.get('supports_top') is not None:
            sup_n += 1
    if bs:
        sup_ok = sum(1 for b in bs if b.get('supports_top') is False)
        sup_rate = round((1.0 - sup_ok / float(n)) * 100.0, 1)
    if len(dims) > 1:
        issues.append('\u540c\u5c42\u7528\u4e86 %d \u4e2a\u5206\u7c7b\u6807\u51c6\uff08%s\uff09\uff1a\u540c\u4e00\u5c42\u5fc5\u987b\u5355\u4e00\u6807\u51c6'
                      % (len(dims), '\u3001'.join(sorted(d for d in dims if d))))
    if overlaps:
        issues.append('%d \u4e2a\u5206\u652f\u5b58\u5728\u91cd\u53e0\uff1a%s'
                      % (overlaps, '\u3001'.join(r['name'] for r in rows if r['overlaps'])))
    if placeholders:
        issues.append('%d \u4e2a\u5206\u652f\u662f\u300c\u5176\u4ed6\u300d\u5360\u4f4d\uff1a\u627e\u51fa\u8fd9\u7c7b\u5b9e\u9645\u7279\u5f81\u518d\u547d\u540d' % placeholders)
    if not_support:
        issues.append('%d \u4e2a\u5206\u652f\u4e0d\u652f\u6491\u9876\u53e5\uff1a\u786e\u8ba4\u8fd9\u4e9b\u8bba\u70b9\u5c5e\u4e8e\u672c\u6b21\u6c47\u62a5' % not_support)
    if mixed:
        issues.append('%d \u4e2a\u5206\u652f\u7c92\u5ea6\u4e0d\u9f50\uff1a\u5927\u7c7b\u4e0e\u5c0f\u9879\u5e76\u5217\u9700\u5408\u5e76' % mixed)
    if n and (n < N_MIN or n > N_BEST_HI):
        issues.append('\u5206\u652f\u6570 %d \u6761\uff1a\u5efa\u8bae %d-%d \u6761\uff0c\u2265%d \u6761\u9700\u6536\u655b'
                      % (n, N_BEST_LO, N_BEST_HI, N_MAX))
    return rows, dim_rate, sup_rate, issues, names


def chart_check(data):
    cs = data.get('charts') or []
    rows = []
    issues = []
    fit = 0
    titled = 0
    for c in cs:
        ct = (c.get('type') or '').strip()
        purpose = (c.get('purpose') or '').strip()
        concl = bool(c.get('conclusion_title'))
        items = c.get('items')
        try:
            items = int(items)
        except (TypeError, ValueError):
            items = None
        axis = c.get('axis_from_zero')
        allowed = CHART_FIT.get(ct, ())
        matched = bool(allowed) and purpose in allowed
        if matched:
            fit += 1
        if concl:
            titled += 1
        flags = []
        if not allowed:
            flags.append('\u672a\u77e5\u7684\u56fe\u8868\u7c7b\u578b\u300c%s\u300d' % ct)
        elif not matched:
            flags.append('\u300c%s\u300d\u4e0d\u9002\u5408\u8868\u8fbe\u300c%s\u300d' % (ct, PURPOSE_CN.get(purpose, purpose)))
        if not concl:
            flags.append('\u6807\u9898\u672a\u5199\u7ed3\u8bba')
        if items is not None and items > CHART_ITEMS_MAX:
            flags.append('\u6570\u636e\u70b9 %d \u4e2a\u8d85\u8fc7 %d \u4e2a\u4e0a\u9650' % (items, CHART_ITEMS_MAX))
        if axis is False and ct == 'bar':
            flags.append('\u67f1\u72b6\u56fe\u5750\u6807\u8f74\u672a\u4ece 0 \u5f00\u59cb\uff0c\u4f1a\u5938\u5927\u5dee\u5f02')
        rows.append({'type': ct, 'purpose': purpose, 'matched': matched,
                     'conclusion_title': concl, 'items': items,
                     'flags': flags, 'state': '\u5408\u89c4' if not flags else '\u5f85\u6539'})
        for f in flags:
            issues.append('\u56fe\u8868\u300c%s\u300d\uff1a%s' % (ct or '\u672a\u586b', f))
    n = len(cs)
    fit_rate = round(fit * 100.0 / n, 1) if n else 0.0
    title_rate = round(titled * 100.0 / n, 1) if n else 0.0
    if n and fit_rate < 100.0:
        issues.append('%d \u4e2a\u56fe\u8868\u7c7b\u578b\u4e0e\u8868\u8fbe\u610f\u56fe\u4e0d\u5339\u914d' % (n - fit))
    if n and title_rate < 100.0:
        issues.append('%d \u4e2a\u56fe\u8868\u6807\u9898\u672a\u5199\u7ed3\u8bba' % (n - titled))
    return rows, fit_rate, title_rate, issues


def redundant_check(data):
    hits = []
    for w in REDUNDANT:
        if w in (data.get('lead_sentence') or ''):
            hits.append(w)
    return hits


def build(data, fmt='md'):
    title = data.get('title') or '\u6c47\u62a5\u903b\u8f91\u4f53\u68c0'
    t_rows, t_issues, cf = top_check(data)
    s_rows, s_issues = scqa_check(data)
    b_rows, dim_rate, sup_rate, b_issues, names = branch_check(data)
    c_rows, fit_rate, title_rate, c_issues = chart_check(data)
    red = redundant_check(data)
    all_issues = t_issues + s_issues + b_issues + c_issues

    if fmt == 'json':
        return {'title': title,
                'conclusion_first': cf,
                'top_issues': t_issues, 'top': t_rows,
                'scqa_issues': s_issues, 'scqa': s_rows,
                'branch_count': len(b_rows),
                'dimension_rate': dim_rate, 'support_rate': sup_rate,
                'branch_issues': b_issues, 'branches': b_rows,
                'chart_fit_rate': fit_rate, 'chart_title_rate': title_rate,
                'chart_issues': c_issues, 'charts': c_rows,
                'redundant_hits': red}

    out = []
    out.append('# %s' % title)
    out.append('')
    out.append('- \u6c47\u62a5\u5bf9\u8c61\uff1a%s' % (data.get('audience') or '\uff08\u672a\u586b\uff09'))
    out.append('- \u9876\u53e5\uff1a%s' % (data.get('lead_sentence') or '\uff08\u672a\u586b\uff09'))
    out.append('- \u7ed3\u8bba\u5148\u884c\uff1a%s' % ('\u662f' if cf else '\u5426'))
    out.append('- \u5206\u652f\u6570\uff1a%d\uff08\u5efa\u8bae %d-%d\uff09' % (len(b_rows), N_BEST_LO, N_BEST_HI))
    out.append('- \u5206\u7c7b\u6807\u51c6\u4e00\u81f4\u6027\uff1a%.1f%%' % dim_rate)
    out.append('- \u5206\u652f\u652f\u6491\u9876\u53e5\u6bd4\u4f8b\uff1a%.1f%%' % sup_rate)
    out.append('- \u56fe\u8868\u5339\u914d\u7387\uff1a%.1f%%\uff08%d \u4e2a\uff09' % (fit_rate, len(c_rows)))
    out.append('- \u56fe\u8868\u7ed3\u8bba\u6807\u9898\u7387\uff1a%.1f%%' % title_rate)
    out.append('- \u5197\u4f59\u8868\u8ff0\u547d\u4e2d\uff1a%d \u5904' % len(red))
    out.append('')
    out.append('## \u4e00\u3001\u9876\u53e5\u4e0e\u7ed3\u8bba\u5148\u884c')
    out.append('')
    if t_issues:
        for i, it in enumerate(t_issues, 1):
            out.append('%d. %s' % (i, it))
    else:
        out.append('\u9876\u53e5\u4e3a\u5b8c\u6574\u5224\u65ad\u4e14\u7ed3\u8bba\u5148\u884c\u3002')
    out.append('')
    out.append('## \u4e8c\u3001SCQA \u5f15\u5165')
    out.append('')
    out.append('| \u8981\u7d20 | \u5185\u5bb9 | \u72b6\u6001 |')
    out.append('|---|---|---|')
    for r in s_rows:
        out.append('| %s | %s | %s |' % (r['key'], r['text'], r['state']))
    out.append('')
    if s_issues:
        for i, it in enumerate(s_issues, 1):
            out.append('%d. %s' % (i, it))
        out.append('')
    out.append('## \u4e09\u3001\u5206\u652f\u4e0e MECE')
    out.append('')
    out.append('| \u5206\u652f | \u5206\u7c7b\u6807\u51c6 | \u652f\u6491\u9876\u53e5 | \u5360\u4f4d | \u5224\u5b9a | \u95ee\u9898 |')
    out.append('|---|---|---|---|---|---|')
    for r in b_rows:
        sup = '\u662f' if r['supports_top'] else ('\u5426' if r['supports_top'] is False else '\u672a\u6807')
        out.append('| %s | %s | %s | %s | %s | %s |' % (
            r['name'], r['dimension'], sup,
            '\u662f' if r['placeholder'] else '\u5426', r['state'],
            '\uff1b'.join(r['flags']) if r['flags'] else '-'))
    if not b_rows:
        out.append('| \uff08\u672a\u586b\u5206\u652f\uff09 | - | - | - | - | \u81f3\u5c11 3 \u4e2a\u5206\u652f |')
    out.append('')
    if b_issues:
        for i, it in enumerate(b_issues, 1):
            out.append('%d. %s' % (i, it))
        out.append('')
    out.append('## \u56db\u3001\u56fe\u8868\u9009\u914d')
    out.append('')
    out.append('| \u7c7b\u578b | \u8868\u8fbe\u610f\u56fe | \u7c7b\u578b\u5339\u914d | \u7ed3\u8bba\u6807\u9898 | \u6570\u636e\u70b9 | \u5224\u5b9a |')
    out.append('|---|---|---|---|---|---|')
    for r in c_rows:
        out.append('| %s | %s | %s | %s | %s | %s |' % (
            r['type'], PURPOSE_CN.get(r['purpose'], r['purpose']),
            'Y' if r['matched'] else '-',
            'Y' if r['conclusion_title'] else '-',
            r['items'] if r['items'] is not None else '-', r['state']))
    if not c_rows:
        out.append('| \uff08\u65e0\u56fe\u8868\uff09 | - | - | - | - | \u8d8b\u52bf\u7528\u6298\u7ebf\uff0c\u6bd4\u8f83\u7528\u67f1\u72b6 |')
    out.append('')
    if c_issues:
        for i, it in enumerate(c_issues, 1):
            out.append('%d. %s' % (i, it))
        out.append('')
    out.append('## \u4e94\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if not (data.get('lead_sentence') or '').strip():
        idx += 1
        out.append('%d. \u5148\u5b9a\u4e00\u53e5\u8bdd\u9876\u53e5\uff1a\u53ea\u7559\u4e00\u53e5\u7684\u8bdd\uff0c\u8fd9\u5c01\u6c47\u62a5\u8981\u8bf4\u7684\u662f\u4ec0\u4e48\u3002' % idx)
    elif t_issues:
        idx += 1
        out.append('%d. \u9876\u53e5\u95ee\u9898\uff1a%s' % (idx, '\uff1b'.join(t_issues)))
    if not cf:
        idx += 1
        out.append('%d. \u7ed3\u8bba\u672a\u5148\u884c\uff1a\u628a\u9876\u53e5\u653e\u7b2c\u4e00\u6bb5\uff0c\u80cc\u666f\u538b\u5230 SCQA \u7684 S \u91cc\uff0c\u4e00\u4e24\u53e5\u5e26\u8fc7\u3002' % idx)
    if s_issues:
        idx += 1
        out.append('%d. SCQA \u4e0d\u5b8c\u6574\uff1a%s' % (idx, '\uff1b'.join(s_issues)))
    if b_issues:
        idx += 1
        out.append('%d. \u5206\u652f\u95ee\u9898 %d \u5904\uff1a\u5148\u786e\u8ba4\u540c\u5c42\u5206\u7c7b\u6807\u51c6\u5355\u4e00\uff0c\u518d\u5904\u7406\u91cd\u53e0\u4e0e\u5360\u4f4d\u3002'
                   % (idx, len(b_issues)))
    if c_issues:
        idx += 1
        out.append('%d. \u56fe\u8868\u95ee\u9898 %d \u5904\uff1a\u8d8b\u52bf\u7528\u6298\u7ebf\u3001\u7c7b\u76ee\u6bd4\u8f83\u7528\u67f1\u72b6\u3001\u6784\u6210\u5360\u6bd4\uff08\u22644 \u9879\uff09\u7528\u997c\u56fe\uff1b'
                   '\u6807\u9898\u5199\u7ed3\u8bba\uff0c\u67f1\u72b6\u56fe\u5750\u6807\u8f74\u4ece 0 \u5f00\u59cb\u3002' % (idx, len(c_issues)))
    if red:
        idx += 1
        out.append('%d. \u5197\u4f59\u8868\u8ff0 %d \u5904\uff1a%s\u3002\u5f00\u7bc7\u4e0d\u94fa\u57ab\u80cc\u666f\u3002' % (idx, len(red), '\u3001'.join(red)))
    if not idx:
        out.append('\u9876\u53e5\u3001SCQA\u3001\u5206\u652f\u4e0e\u56fe\u8868\u5747\u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\u3002'
                   '\u5b9a\u7a3f\u524d\u786e\u8ba4\u6570\u636e\u6765\u6e90\u6e05\u695a\uff0c\u6309\u6c47\u62a5\u5bf9\u8c61\u8c03\u6574\u7b2c\u4e00\u53e5\u7684\u843d\u70b9\u3002')
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

    def mk(name, dim='\u6e20\u9053\u8868\u73b0', **kw):
        d = {'name': name, 'dimension': dim, 'granularity': 'same',
             'covered': True, 'overlaps': [], 'placeholder': False,
             'supports_top': True}
        d.update(kw)
        return d

    good = {
        'title': '\u5b63\u5ea6\u590d\u76d8', 'audience': '\u76f4\u5c5e\u4e0a\u7ea7',
        'lead_sentence': '\u5efa\u8bae\u6682\u505c\u6e20\u9053 B \u6295\u653e\uff0c\u628a\u9884\u7b97\u8f6c\u5230\u6e20\u9053 C',
        'conclusion_first': True,
        'scqa': {'s': '\u4e09\u4e2a\u6e20\u9053\u6309\u6708\u6295\u653e', 'c': 'B \u6e20\u9053\u8fde\u7eed\u4e24\u6708 ROI \u4e0b\u964d',
                 'q': '\u662f\u5426\u8c03\u6574\u9884\u7b97\u5206\u914d', 'a': '\u5efa\u8bae\u8f6c\u5411 C'},
        'branches': [mk('\u6e20\u9053 B ROI \u6301\u7eed\u4e0b\u964d'), mk('\u6e20\u9053 C \u8f6c\u5316\u7387\u63d0\u5347'),
                     mk('\u6e20\u9053 A \u7ef4\u6301\u7a33\u5b9a')],
        'charts': [{'type': 'line', 'purpose': 'trend',
                    'conclusion_title': True, 'items': 6,
                    'axis_from_zero': True}],
    }
    r = build(good, 'json')
    chk(r['top_issues'] == [], '\u89c4\u8303\u9876\u53e5\u4e0d\u5e94\u6709\u95ee\u9898')
    chk(r['scqa_issues'] == [], 'SCQA \u9f50\u5168\u4e0d\u5e94\u6709\u95ee\u9898')
    chk(r['dimension_rate'] == 100.0, '\u5355\u4e00\u5206\u7c7b\u6807\u51c6\u5e94\u4e3a 100')
    chk(r['support_rate'] == 100.0, '\u90fd\u652f\u6491\u9876\u53e5\u5e94\u4e3a 100')
    chk(r['chart_fit_rate'] == 100.0, '\u56fe\u8868\u5339\u914d\u5e94\u4e3a 100')
    chk(r['branch_count'] == 3, '\u5206\u652f\u6570\u5e94\u4e3a 3')
    chk(r['redundant_hits'] == [], '\u89c4\u8303\u9876\u53e5\u4e0d\u5e94\u547d\u4e2d\u5197\u4f59')

    no_lead = build({}, 'json')
    chk(no_lead['top_issues'] != [], '\u672a\u586b\u9876\u53e5\u5e94\u62a5\u95ee\u9898')
    chk(any('\u9876\u53e5' in i for i in no_lead['top_issues']), '\u5e94\u63d0\u793a\u5b9a\u9876\u53e5')

    topic = {'lead_sentence': '\u5173\u4e8e\u7528\u6237\u6d41\u5931\u7684\u5206\u6790', 'conclusion_first': True}
    r = build(topic, 'json')
    chk(any('\u8bdd\u9898' in i for i in r['top_issues']), '\u8bdd\u9898\u5f0f\u9876\u53e5\u5e94\u63d0\u793a')

    short = {'lead_sentence': '\u9700\u8981\u6539', 'conclusion_first': True}
    r = build(short, 'json')
    chk(any('\u8fc7\u77ed' in i for i in r['top_issues']), '\u8fc7\u77ed\u9876\u53e5\u5e94\u63d0\u793a')

    not_first = {'lead_sentence': '\u5efa\u8bae\u6682\u505c\u6e20\u9053 B \u6295\u653e\u628a\u9884\u7b97\u8f6c\u5230\u6e20\u9053 C',
                 'conclusion_first': False}
    r = build(not_first, 'json')
    chk(any('\u7ed3\u8bba\u672a\u5148\u884c' in i for i in r['top_issues']), '\u672a\u7ed3\u8bba\u5148\u884c\u5e94\u63d0\u793a')

    red = {'lead_sentence': '\u5148\u8bf4\u4e00\u4e0b\u80cc\u666f\uff0c\u5efa\u8bae\u6682\u505c\u6e20\u9053 B \u6295\u653e\u628a\u9884\u7b97\u8f6c\u5230\u6e20\u9053 C',
           'conclusion_first': True}
    r = build(red, 'json')
    chk(len(r['redundant_hits']) == 1, '\u5197\u4f59\u8868\u8ff0\u5e94\u547d\u4e2d 1 \u5904')

    s_long = {'scqa': {'s': '\u80cc\u666f' * 40, 'c': '\u51b2\u7a81', 'q': '\u95ee\u9898', 'a': '\u7b54\u6848'}}
    r = build(s_long, 'json')
    chk(any('\u8fc7\u957f' in i for i in r['scqa_issues']), 'S \u8fc7\u957f\u5e94\u63d0\u793a')

    s_miss = {'scqa': {'s': '\u60c5\u5883', 'c': '\u51b2\u7a81', 'q': '\u95ee\u9898'}}
    r = build(s_miss, 'json')
    chk(any('\u7f3a' in i for i in r['scqa_issues']), 'SCQA \u7f3a\u9879\u5e94\u63d0\u793a')

    multi_dim = {'branches': [mk('A', dim='\u6e20\u9053'), mk('B', dim='\u6210\u672c'),
                              mk('C', dim='\u6e20\u9053')]}
    r = build(multi_dim, 'json')
    chk(r['dimension_rate'] < 100.0, '\u4e24\u4e2a\u5206\u7c7b\u6807\u51c6\u5e94\u62c9\u4f4e\u4e00\u81f4\u6027')
    chk(any('\u5206\u7c7b\u6807\u51c6' in i for i in r['branch_issues']), '\u5e94\u63d0\u793a\u6807\u51c6\u4e0d\u4e00')

    overlap = {'branches': [mk('A', overlaps=['B']), mk('B'), mk('C')]}
    r = build(overlap, 'json')
    chk(any('\u91cd\u53e0' in i for i in r['branch_issues']), '\u5e94\u63d0\u793a\u91cd\u53e0')

    ph = {'branches': [mk('A'), mk('B'), mk('\u5176\u4ed6', placeholder=True)]}
    r = build(ph, 'json')
    chk(any('\u5360\u4f4d' in i for i in r['branch_issues']), '\u5e94\u63d0\u793a\u5360\u4f4d\u5206\u652f')

    nosup = {'branches': [mk('A'), mk('B', supports_top=False), mk('C')]}
    r = build(nosup, 'json')
    chk(r['support_rate'] < 100.0, '\u4e0d\u652f\u6491\u9876\u53e5\u5e94\u62c9\u4f4e\u652f\u6491\u7387')

    mixed = {'branches': [mk('A'), mk('B', granularity='mixed'), mk('C')]}
    r = build(mixed, 'json')
    chk(any('\u7c92\u5ea6' in i for i in r['branch_issues']), '\u5e94\u63d0\u793a\u7c92\u5ea6\u4e0d\u9f50')

    many = {'branches': [mk('B%d' % i) for i in range(9)]}
    r = build(many, 'json')
    chk(any('\u5206\u652f\u6570' in i for i in r['branch_issues']), '9 \u6761\u5206\u652f\u5e94\u63d0\u793a\u6536\u655b')

    no_br = build({'branches': []}, 'json')
    chk(no_br['branch_count'] == 0, '\u7a7a\u5206\u652f\u5217\u8868\u4e0d\u5e94\u62a5\u9519')

    pie_trend = {'charts': [{'type': 'pie', 'purpose': 'trend',
                             'conclusion_title': True, 'items': 4}]}
    r = build(pie_trend, 'json')
    chk(r['chart_fit_rate'] == 0.0, '\u997c\u56fe\u8868\u8fbe\u8d8b\u52bf\u5e94\u5224\u4e0d\u5339\u914d')
    chk(any('\u4e0d\u9002\u5408' in i for i in r['chart_issues']), '\u5e94\u63d0\u793a\u56fe\u8868\u7c7b\u578b\u4e0d\u5339\u914d')

    line_cmp = {'charts': [{'type': 'line', 'purpose': 'compare',
                            'conclusion_title': True, 'items': 3}]}
    r = build(line_cmp, 'json')
    chk(r['chart_fit_rate'] == 0.0, '\u6298\u7ebf\u8868\u8fbe\u7c7b\u76ee\u6bd4\u8f83\u5e94\u5224\u4e0d\u5339\u914d')

    table_ok = {'charts': [{'type': 'table', 'purpose': 'compare',
                            'conclusion_title': True, 'items': 5}]}
    r = build(table_ok, 'json')
    chk(r['chart_fit_rate'] == 100.0, '\u8868\u683c\u8868\u8fbe\u6bd4\u8f83\u5e94\u5224\u5339\u914d')

    no_title = {'charts': [{'type': 'bar', 'purpose': 'compare',
                            'conclusion_title': False, 'items': 4,
                            'axis_from_zero': True}]}
    r = build(no_title, 'json')
    chk(r['chart_title_rate'] == 0.0, '\u65e0\u7ed3\u8bba\u6807\u9898\u5e94\u4e3a 0')
    chk(any('\u6807\u9898\u672a\u5199\u7ed3\u8bba' in i for i in r['chart_issues']), '\u5e94\u63d0\u793a\u6807\u9898\u95ee\u9898')

    overload = {'charts': [{'type': 'bar', 'purpose': 'compare',
                            'conclusion_title': True, 'items': 12,
                            'axis_from_zero': True}]}
    r = build(overload, 'json')
    chk(any('\u4e0a\u9650' in i for i in r['chart_issues']), '\u6570\u636e\u70b9\u8fc7\u591a\u5e94\u63d0\u793a')

    axis = {'charts': [{'type': 'bar', 'purpose': 'compare',
                        'conclusion_title': True, 'items': 4,
                        'axis_from_zero': False}]}
    r = build(axis, 'json')
    chk(any('\u5750\u6807\u8f74' in i for i in r['chart_issues']), '\u67f1\u72b6\u56fe\u975e\u96f6\u8d77\u70b9\u5e94\u63d0\u793a')

    unknown = {'charts': [{'type': 'sunburst', 'purpose': 'compose',
                           'conclusion_title': True, 'items': 3}]}
    r = build(unknown, 'json')
    chk(any('\u672a\u77e5' in i for i in r['chart_issues']), '\u672a\u77e5\u56fe\u8868\u7c7b\u578b\u5e94\u63d0\u793a')

    r = build({'charts': []}, 'json')
    chk(r['chart_fit_rate'] == 0.0, '\u7a7a\u56fe\u8868\u5217\u8868\u8bb0 0 \u800c\u975e\u62a5\u9519')

    txt = build(good, 'md')
    chk('\u9876\u53e5\u4e0e\u7ed3\u8bba\u5148\u884c' in txt, 'md \u5e94\u542b\u9876\u53e5\u6bb5')
    chk('\u5206\u652f\u4e0e MECE' in txt, 'md \u5e94\u542b MECE \u6bb5')
    chk('\u56fe\u8868\u9009\u914d' in txt, 'md \u5e94\u542b\u56fe\u8868\u6bb5')
    chk('\u6574\u6539\u5efa\u8bae' in txt, 'md \u5e94\u542b\u6574\u6539\u5efa\u8bae')

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
    ap = argparse.ArgumentParser(description='\u6c47\u62a5\u903b\u8f91\u642d\u5efa\u4e0e\u8868\u8fbe\u6838\u67e5')
    ap.add_argument('--file', help='\u8f93\u5165 JSON \u8def\u5f84')
    ap.add_argument('--text', help='\u76f4\u63a5\u7ed9 JSON \u5b57\u7b26\u4e32')
    ap.add_argument('--out', help='\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', choices=['md', 'json'], default='md')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    if a.selftest:
        res = selftest()
        write_out(res, os.path.join(here, '_selftest_result.txt'))
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
