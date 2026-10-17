# -*- coding: utf-8 -*-
"""\u7ee9\u6548\u9762\u8c08\u51c6\u5907\u6838\u67e5\uff1a\u81ea\u8bc4\u8bc1\u636e\u94fe\u3001\u53e3\u5f84\u4e00\u81f4\u6027\u3001\u7a0b\u5e8f\u5b8c\u6574\u7387\u3002

\u7528\u6cd5:
  python review_talk_prep.py --file review.json [--out result.md] [--format json]
  python review_talk_prep.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u7ea2\u7ebf\u9608\u503c
COVERAGE_RED = 70.0
QUANT_RED = 80.0
VISIBLE_RED = 90.0
WEIGHT_TOL = 0.001
# \u7533\u8bc9\u671f\u9650\u4e34\u8fd1\u63d0\u793a\uff08\u5929\uff09
DEADLINE_WARN = 3

BLAME_CAUSES = ('\u5176\u4ed6\u90e8\u95e8', '\u522b\u7684\u90e8\u95e8', '\u8d44\u6e90\u4e0d\u8db3', '\u4ed6\u4eec\u4e0d\u914d\u5408', '\u522b\u7684\u56e2\u961f',
                '\u516c\u53f8\u5b89\u6392', '\u4e0d\u662f\u6211\u7684\u95ee\u9898', '\u5ba2\u89c2\u539f\u56e0')

# \u5efa\u8bae\u7684\u6210\u679c\u6761\u6570\u533a\u95f4
N_MIN = 3
N_BEST_LO = 5
N_BEST_HI = 8


def load(text=None, path=None):
    if text:
        return json.loads(text)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def pct(a, b):
    if not b:
        return 0.0
    return round(a * 100.0 / b, 1)


def evidence_check(data):
    """\u81ea\u8bc4\u8bc1\u636e\u94fe\uff1a\u76ee\u6807\u503c / \u5b9e\u9645\u503c / \u6765\u6e90 / \u8bc1\u636e\u7f16\u53f7 / \u4e0a\u7ea7\u53ef\u89c1\u3002"""
    items = data.get('achievements') or []
    rows = []
    n = len(items)
    with_target = 0
    with_value = 0
    with_source = 0
    with_id = 0
    visible = 0
    for it in items:
        ht = bool(it.get('has_target'))
        hv = bool(it.get('has_value'))
        hs = bool(it.get('has_source'))
        hid = bool((it.get('evidence_id') or '').strip())
        vis = bool(it.get('visible_to_manager'))
        with_target += 1 if ht else 0
        with_value += 1 if hv else 0
        with_source += 1 if hs else 0
        with_id += 1 if hid else 0
        visible += 1 if vis else 0
        gaps = []
        if not ht:
            gaps.append('\u7f3a\u76ee\u6807\u503c')
        if not hv:
            gaps.append('\u7f3a\u5b9e\u9645\u503c')
        if not hs:
            gaps.append('\u7f3a\u6570\u636e\u6765\u6e90')
        if not hid:
            gaps.append('\u7f3a\u8bc1\u636e\u7f16\u53f7')
        if not vis:
            gaps.append('\u4e0a\u7ea7\u4e0d\u53ef\u89c1')
        rows.append({'name': it.get('name') or '\uff08\u672a\u547d\u540d\uff09',
                     'evidence_id': (it.get('evidence_id') or '\uff08\u672a\u586b\uff09'),
                     'gaps': gaps, 'state': '\u5b8c\u6574' if not gaps else '\u6709\u7f3a\u53e3'})
    full = 0
    for r in rows:
        if not r['gaps']:
            full += 1
    return (rows, n, pct(full, n), pct(with_target, n), pct(with_value, n),
            pct(with_source, n), pct(with_id, n), pct(visible, n))


def dim_check(data):
    """\u7ef4\u5ea6\u53e3\u5f84\u4e00\u81f4\u6027\uff1a\u6743\u91cd\u5408\u8ba1\u3001\u8fbe\u6210\u7387\u3002"""
    dims = data.get('dimensions') or []
    rows = []
    wsum = 0.0
    w = 0.0
    r = 0.0
    for d in dims:
        try:
            wt = float(d.get('weight'))
        except (TypeError, ValueError):
            wt = 0.0
        try:
            res = float(d.get('result'))
        except (TypeError, ValueError):
            res = 0.0
        try:
            tgt = float(d.get('target'))
        except (TypeError, ValueError):
            tgt = 0.0
        wsum += wt
        w += wt
        r += wt * res
        ach = (res / tgt) if tgt else None
        rows.append({'name': d.get('name') or '\uff08\u672a\u547d\u540d\uff09', 'weight': wt,
                     'target': tgt, 'result': res,
                     'achieve': round(ach * 100, 1) if ach is not None else None,
                     'state': '\u8fbe\u6807' if (ach is not None and ach >= 1.0) else '\u672a\u8fbe\u6807'})
    weighted = round(r, 4) if w else 0.0
    weight_ok = abs(wsum - 1.0) <= WEIGHT_TOL
    return rows, round(wsum, 4), weighted, weight_ok


def cause_check(data):
    """\u5f52\u56e0\u8868\uff1a\u6839\u56e0\u662f\u5426\u843d\u5728\u53ef\u63a7\u9879\u3001\u662f\u5426\u7529\u9505\u3002"""
    items = data.get('root_causes') or []
    rows = []
    blame = 0
    not_controllable = 0
    for it in items:
        cause = (it.get('cause') or '')
        ctrl = bool(it.get('own_controllable'))
        hits = [w for w in BLAME_CAUSES if w in cause]
        if hits:
            blame += 1
        if not ctrl:
            not_controllable += 1
        flags = []
        if hits:
            flags.append('\u6839\u56e0\u7529\u9505\uff1a\u542b\u300c%s\u300d' % hits[0])
        if not ctrl:
            flags.append('\u6839\u56e0\u4e0d\u53ef\u63a7\uff0c\u9700\u8865\u53ef\u63a7\u90e8\u5206')
        rows.append({'issue': it.get('issue') or '\uff08\u672a\u547d\u540d\uff09', 'cause': cause or '\uff08\u672a\u586b\uff09',
                     'own_controllable': ctrl, 'flags': flags,
                     'state': '\u53ef\u63a7' if (ctrl and not hits) else '\u5f85\u6539'})
    return rows, blame, not_controllable


def process_check(data):
    """\u7a0b\u5e8f\u5b8c\u6574\u7387\u4e0e\u7533\u8bc9\u671f\u9650\u3002"""
    p = data.get('process') or {}
    need = ['read_policy', 'got_written_feedback', 'has_appeal_channel']
    rows = []
    ok = 0
    for k in need:
        v = bool(p.get(k))
        ok += 1 if v else 0
        rows.append({'item': {'read_policy': '\u5df2\u8bfb\u672c\u5355\u4f4d\u7ee9\u6548\u5236\u5ea6',
                              'got_written_feedback': '\u5df2\u83b7\u5f97\u4e66\u9762\u5224\u5b9a\u4f9d\u636e',
                              'has_appeal_channel': '\u5df2\u77e5\u6089\u7533\u8bc9\u6e20\u9053'}[k],
                     'state': '\u662f' if v else '\u5426'})
    try:
        days = int(p.get('appeal_deadline_days'))
    except (TypeError, ValueError):
        days = None
    if days is None:
        rows.append({'item': '\u7533\u8bc9\u671f\u9650', 'state': '\u672a\u586b'})
        warn = False
    else:
        if days < 0:
            state = '\u5df2\u8fc7\u671f'
            warn = True
        elif days <= DEADLINE_WARN:
            state = '\u4e34\u8fd1\uff08\u5269\u4f59 %d \u5929\uff09' % days
            warn = True
        else:
            state = '\u5269\u4f59 %d \u5929' % days
            warn = False
        rows.append({'item': '\u7533\u8bc9\u671f\u9650\uff08\u5929\uff09', 'state': state})
    return rows, pct(ok, len(need)), warn


def build(data, fmt='md'):
    title = data.get('title') or '\u7ee9\u6548\u9762\u8c08\u51c6\u5907\u4f53\u68c0'
    owner = data.get('owner') or '\uff08\u672a\u586b\uff09'
    period = data.get('period') or '\uff08\u672a\u586b\uff09'
    (e_rows, n, cov, quant, cover_v, cover_src, cover_id, visible) = evidence_check(data)
    (d_rows, wsum, weighted, weight_ok) = dim_check(data)
    (c_rows, blame, notctrl) = cause_check(data)
    (p_rows, proc_rate, deadline_warn) = process_check(data)

    if fmt == 'json':
        return {'title': title, 'owner': owner, 'period': period,
                'achievement_count': n, 'evidence_coverage': cov,
                'quant_coverage': quant, 'value_coverage': cover_v,
                'source_coverage': cover_src, 'evidence_id_coverage': cover_id,
                'visible_coverage': visible,
                'weight_sum': wsum, 'weight_ok': weight_ok,
                'weighted_result': weighted,
                'dimensions': d_rows, 'root_causes': c_rows,
                'blame_count': blame, 'process_rate': proc_rate,
                'deadline_warn': deadline_warn, 'process': p_rows,
                'achievements': e_rows}

    out = []
    out.append('# %s' % title)
    out.append('')
    out.append('- \u5bf9\u8c61\uff1a%s' % owner)
    out.append('- \u5468\u671f\uff1a%s' % period)
    out.append('- \u6210\u679c\u6761\u6570\uff1a%d' % n)
    out.append('- \u81ea\u8bc4\u8bc1\u636e\u8986\u76d6\u7387\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff09' % (cov, COVERAGE_RED))
    out.append('- \u91cf\u5316\u8986\u76d6\u7387\uff08\u76ee\u6807\u503c+\u5b9e\u9645\u503c\uff09\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff09' % (quant, QUANT_RED))
    out.append('- \u8bc1\u636e\u53ef\u89c1\u7387\uff08\u4e0a\u7ea7\u53ef\u8bbf\u95ee\uff09\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff09' % (visible, VISIBLE_RED))
    out.append('- \u7ef4\u5ea6\u6743\u91cd\u5408\u8ba1\uff1a%s' % ('%.2f\uff08\u6b63\u5e38\uff09' % wsum if weight_ok else '%.2f\uff08\u4e0d\u7b49\u4e8e 1\uff09' % wsum))
    out.append('- \u52a0\u6743\u8fbe\u6210\uff1a%s' % ('%.0f%%' % (weighted * 100) if weighted else '\u65e0\u6570\u636e'))
    out.append('- \u5f52\u56e0\u7529\u9505\u6761\u6570\uff1a%d' % blame)
    out.append('- \u7a0b\u5e8f\u5b8c\u6574\u7387\uff1a%.1f%%' % proc_rate)
    out.append('- \u7533\u8bc9\u671f\u9650\u63d0\u9192\uff1a%s' % ('\u662f' if deadline_warn else '\u5426'))
    out.append('')
    out.append('## \u4e00\u3001\u81ea\u8bc4\u8bc1\u636e\u94fe')
    out.append('')
    out.append('| \u6210\u679c | \u8bc1\u636e\u7f16\u53f7 | \u72b6\u6001 | \u7f3a\u53e3 |')
    out.append('|---|---|---|---|')
    for r in e_rows:
        out.append('| %s | %s | %s | %s |' % (
            r['name'], r['evidence_id'], r['state'],
            '\u3001'.join(r['gaps']) if r['gaps'] else '-'))
    if not e_rows:
        out.append('| \uff08\u672a\u586b\u6210\u679c\uff09 | - | - | \u81f3\u5c11\u5217 3-8 \u9879 |')
    out.append('')
    out.append('## \u4e8c\u3001\u7ef4\u5ea6\u53e3\u5f84')
    out.append('')
    out.append('| \u7ef4\u5ea6 | \u6743\u91cd | \u76ee\u6807 | \u5b9e\u9645 | \u8fbe\u6210\u7387 | \u72b6\u6001 |')
    out.append('|---|---|---|---|---|---|')
    for r in d_rows:
        ach = ('%.1f%%' % r['achieve']) if r['achieve'] is not None else '\u65e0\u76ee\u6807'
        out.append('| %s | %.2f | %s | %s | %s | %s |' % (
            r['name'], r['weight'], r['target'], r['result'], ach, r['state']))
    if not d_rows:
        out.append('| \uff08\u672a\u586b\u7ef4\u5ea6\uff09 | - | - | - | - | - |')
    out.append('')
    out.append('## \u4e09\u3001\u5f52\u56e0\u8868')
    out.append('')
    if not c_rows:
        out.append('\u672a\u586b\u5f52\u56e0\u3002\u672a\u8fbe\u9879\u5fc5\u987b\u5199\u6839\u56e0\u3001\u662f\u5426\u53ef\u63a7\u3001\u5df2\u505a\u52a8\u4f5c\u3001\u4e0b\u671f\u6539\u8fdb\u3002')
    else:
        out.append('| \u672a\u8fbe\u9879 | \u6839\u56e0 | \u53ef\u63a7 | \u72b6\u6001 | \u63d0\u9192 |')
        out.append('|---|---|---|---|---|')
        for r in c_rows:
            out.append('| %s | %s | %s | %s | %s |' % (
                r['issue'], r['cause'], '\u662f' if r['own_controllable'] else '\u5426',
                r['state'], '\uff1b'.join(r['flags']) if r['flags'] else '-'))
    out.append('')
    out.append('## \u56db\u3001\u7a0b\u5e8f\u5b8c\u6574\u7387')
    out.append('')
    for r in p_rows:
        out.append('- [%s] %s' % ('x' if r['state'] == '\u662f' else ' ', r['item']))
    out.append('')
    out.append('## \u4e94\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if cov < COVERAGE_RED:
        idx += 1
        out.append('%d. \u8bc1\u636e\u8986\u76d6\u7387 %.1f%% \u4f4e\u4e8e %.0f%%\uff1a\u7ed9\u6bcf\u6761\u6210\u679c\u8865\u76ee\u6807\u503c\u3001\u5b9e\u9645\u503c\u3001\u6570\u636e\u6765\u6e90\u548c\u8bc1\u636e\u7f16\u53f7\u3002'
                   % (idx, cov, COVERAGE_RED))
    if quant < QUANT_RED:
        idx += 1
        out.append('%d. \u91cf\u5316\u8986\u76d6\u7387 %.1f%% \u504f\u4f4e\uff1a\u628a\u300c\u505a\u4e86\u5f88\u591a\u300d\u6539\u5199\u6210\u300c\u4ece X \u53d8\u6210 Y\u300d\uff0c\u6765\u6e90\u5199\u6e05\u7cfb\u7edf\u6216\u53f0\u8d26\u3002'
                   % (idx, quant))
    if visible < VISIBLE_RED:
        idx += 1
        out.append('%d. \u8bc1\u636e\u53ef\u89c1\u7387 %.1f%% \u504f\u4f4e\uff1a\u628a\u5173\u952e\u4ea7\u51fa\u540c\u6b65\u5230\u5171\u4eab\u4f4d\u7f6e\u6216\u6284\u9001\u76f8\u5173\u4eba\uff0c'
                   '\u4e0a\u7ea7\u770b\u4e0d\u5230\u7684\u8bc1\u636e\u7b49\u540c\u4e8e\u4e0d\u5b58\u5728\u3002' % (idx, visible))
    if not weight_ok:
        idx += 1
        out.append('%d. \u7ef4\u5ea6\u6743\u91cd\u5408\u8ba1\u4e3a %.2f\uff0c\u4e0d\u7b49\u4e8e 1\uff1a\u6309\u672c\u5355\u4f4d\u7ee9\u6548\u5236\u5ea6\u6838\u5bf9\u6743\u91cd\u8868\u3002' % (idx, wsum))
    if n and (n < N_MIN or n > N_BEST_HI):
        idx += 1
        out.append('%d. \u6210\u679c\u6761\u6570 %d \u6761\uff1a\u5efa\u8bae\u63a7\u5236\u5728 %d-%d \u6761\uff0c\u9762\u8c08\u7684\u8bb0\u5fc6\u5bb9\u91cf\u6709\u9650\u3002'
                   % (idx, n, N_BEST_LO, N_BEST_HI))
    if blame:
        idx += 1
        out.append('%d. %d \u6761\u5f52\u56e0\u542b\u7529\u9505\u8868\u8ff0\uff1a\u7ed3\u8bba\u53e5\u4e3b\u8bed\u6539\u6210\u81ea\u5df1\u7684\u52a8\u4f5c\u3002' % (idx, blame))
    if notctrl:
        idx += 1
        out.append('%d. %d \u6761\u5f52\u56e0\u6807\u4e3a\u4e0d\u53ef\u63a7\uff1a\u8865\u4e0a\u81ea\u5df1\u80fd\u6539\u7684\u90a3\u4e00\u90e8\u5206\uff0c\u5426\u5219\u6539\u8fdb\u8ba1\u5212\u65e0\u6cd5\u843d\u5730\u3002' % (idx, notctrl))
    if deadline_warn:
        idx += 1
        out.append('%d. \u7533\u8bc9\u671f\u9650\u4e34\u8fd1\u6216\u5df2\u8fc7\u671f\uff1a\u5148\u7d22\u53d6\u5224\u5b9a\u4f9d\u636e\u4e0e\u671f\u9650\u89c4\u5b9a\uff0c\u518d\u51b3\u5b9a\u662f\u5426\u63d0\u4ea4\u4e66\u9762\u7533\u8bc9\u3002' % idx)
    if proc_rate < 100.0:
        idx += 1
        out.append('%d. \u7a0b\u5e8f\u5b8c\u6574\u7387 %.1f%%\uff1a\u8865\u9f50\u672a\u52fe\u9009\u9879\uff0c\u5c24\u5176\u662f\u4e66\u9762\u5224\u5b9a\u4f9d\u636e\u4e0e\u7533\u8bc9\u6e20\u9053\u3002' % (idx, proc_rate))
    if not idx:
        out.append('\u6750\u6599\u4e0e\u53e3\u5f84\u5747\u5408\u89c4\uff0c\u9762\u8c08\u524d\u628a\u4e09\u6761\u6700\u96be\u95ee\u9898\u7684 60 \u79d2\u7248\u672c\u5404\u5f55\u4e00\u904d\u81ea\u67e5\u8bed\u6c14\u3002')
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

    good = {
        'achievements': [
            {'name': 'a', 'has_target': True, 'has_value': True, 'has_source': True,
             'evidence_id': 'D1', 'visible_to_manager': True},
            {'name': 'b', 'has_target': True, 'has_value': True, 'has_source': True,
             'evidence_id': 'D2', 'visible_to_manager': True},
        ],
        'dimensions': [{'name': 'd', 'weight': 1.0, 'result': 0.5, 'target': 0.5}],
        'root_causes': [{'issue': 'i', 'cause': '\u6211\u5728\u4ecb\u5165\u65f6\u673a\u4e0a\u665a\u4e86', 'own_controllable': True}],
        'process': {'read_policy': True, 'got_written_feedback': True,
                    'has_appeal_channel': True, 'appeal_deadline_days': 10},
    }
    r = build(good, 'json')
    chk(r['evidence_coverage'] == 100.0, '\u4e24\u6761\u6210\u679c\u9f50\u5168\u8986\u76d6\u7387\u5e94 100')
    chk(r['visible_coverage'] == 100.0, '\u53ef\u89c1\u7387\u5e94 100')
    chk(r['weight_ok'] is True, '\u6743\u91cd\u5408\u8ba1 1 \u5e94\u5224\u5b9a\u6b63\u5e38')
    chk(r['blame_count'] == 0, '\u65e0\u7529\u9505\u6839\u56e0')
    chk(r['process_rate'] == 100.0, '\u7a0b\u5e8f\u5b8c\u6574\u7387\u5e94 100')
    chk(r['deadline_warn'] is False, '\u5269\u4f59 10 \u5929\u4e0d\u5e94\u63d0\u9192')

    bad = {'achievements': [
        {'name': 'a', 'has_target': False, 'has_value': False, 'has_source': False,
         'evidence_id': '', 'visible_to_manager': False},
    ]}
    r = build(bad, 'json')
    chk(r['evidence_coverage'] == 0.0, '\u5168\u7f3a\u65f6\u8986\u76d6\u7387\u4e3a 0')
    chk(r['quant_coverage'] == 0.0, '\u5168\u7f3a\u65f6\u91cf\u5316\u8986\u76d6\u7387\u4e3a 0')
    chk(r['visible_coverage'] == 0.0, '\u5168\u7f3a\u65f6\u53ef\u89c1\u7387\u4e3a 0')
    chk(len(r['achievements'][0]['gaps']) == 5, '\u5e94\u62a5 5 \u4e2a\u7f3a\u53e3')

    r = build({'achievements': []}, 'json')
    chk(r['achievement_count'] == 0, '\u7a7a\u6210\u679c\u5217\u8868\u6761\u6570\u4e3a 0')
    chk(r['evidence_coverage'] == 0.0, '\u7a7a\u5217\u8868\u8986\u76d6\u7387\u5e94 0 \u800c\u975e\u62a5\u9519')

    half = {'achievements': [
        {'name': 'a', 'has_target': True, 'has_value': True, 'has_source': True,
         'evidence_id': 'D1', 'visible_to_manager': True},
        {'name': 'b'},
    ]}
    r = build(half, 'json')
    chk(abs(r['evidence_coverage'] - 50.0) < 0.01, '\u4e00\u6761\u5b8c\u6574\u5e94 50')

    bad_w = {'dimensions': [{'name': 'd', 'weight': 0.4, 'result': 1, 'target': 1},
                            {'name': 'e', 'weight': 0.4, 'result': 1, 'target': 1}]}
    r = build(bad_w, 'json')
    chk(r['weight_ok'] is False, '\u6743\u91cd\u5408\u8ba1 0.8 \u5e94\u5224\u5f02\u5e38')
    chk(abs(r['weight_sum'] - 0.8) < 0.001, '\u6743\u91cd\u5408\u8ba1\u5e94\u4e3a 0.8')

    tgt_w = {'dimensions': [{'name': 'd', 'weight': 0.5, 'result': 1, 'target': 1},
                            {'name': 'e', 'weight': 0.5, 'result': 0, 'target': 1}]}
    r = build(tgt_w, 'json')
    chk(abs(r['weighted_result'] - 0.5) < 0.001, '\u52a0\u6743\u7ed3\u679c\u5e94\u4e3a 0.5')
    chk(r['dimensions'][0]['state'] == '\u8fbe\u6807', '\u7ed3\u679c=\u76ee\u6807\u5e94\u5224\u8fbe\u6807')
    chk(r['dimensions'][1]['state'] == '\u672a\u8fbe\u6807', '\u7ed3\u679c\u4f4e\u4e8e\u76ee\u6807\u5e94\u5224\u672a\u8fbe\u6807')

    no_target = {'dimensions': [{'name': 'd', 'weight': 1.0, 'result': 0.5, 'target': 0}]}
    r = build(no_target, 'json')
    chk(r['dimensions'][0]['achieve'] is None, '\u76ee\u6807\u4e3a 0 \u65f6\u8fbe\u6210\u7387\u5e94\u4e3a None')

    blame = {'root_causes': [{'issue': 'i', 'cause': '\u56e0\u4e3a\u5176\u4ed6\u90e8\u95e8\u4e0d\u914d\u5408',
                              'own_controllable': True}]}
    r = build(blame, 'json')
    chk(r['blame_count'] == 1, '\u7529\u9505\u6839\u56e0\u5e94\u8ba1\u6570 1')
    nc = {'root_causes': [{'issue': 'i', 'cause': '\u5ba2\u89c2\u539f\u56e0', 'own_controllable': False}]}
    r = build(nc, 'json')
    chk(r['blame_count'] == 1, '\u5ba2\u89c2\u539f\u56e0\u5e94\u547d\u4e2d\u7529\u9505\u8bcd')
    chk(len(r['root_causes'][0]['flags']) == 2, '\u4e0d\u53ef\u63a7\u52a0\u7529\u9505\u5e94 2 \u6761\u63d0\u9192')

    near = {'process': {'read_policy': True, 'got_written_feedback': True,
                        'has_appeal_channel': True, 'appeal_deadline_days': 2}}
    r = build(near, 'json')
    chk(r['deadline_warn'] is True, '\u5269\u4f59 2 \u5929\u5e94\u63d0\u9192')

    past = {'process': {'read_policy': True, 'got_written_feedback': True,
                        'has_appeal_channel': True, 'appeal_deadline_days': -1}}
    r = build(past, 'json')
    chk(r['deadline_warn'] is True, '\u5df2\u8fc7\u671f\u5e94\u63d0\u9192')

    nonum = {'process': {'read_policy': False, 'got_written_feedback': False,
                         'has_appeal_channel': False}}
    r = build(nonum, 'json')
    chk(r['deadline_warn'] is False, '\u671f\u9650\u672a\u586b\u4e0d\u5224\u8fc7\u671f')
    chk(r['process_rate'] == 0.0, '\u4e09\u9879\u672a\u52fe\u9009\u7a0b\u5e8f\u7387\u4e3a 0')

    txt = build(good, 'md')
    chk('\u6574\u6539\u5efa\u8bae' in txt, 'md \u5e94\u542b\u6574\u6539\u5efa\u8bae')
    chk('\u81ea\u8bc4\u8bc1\u636e\u94fe' in txt, 'md \u5e94\u542b\u8bc1\u636e\u94fe\u8868')
    chk('\u7a0b\u5e8f\u5b8c\u6574\u7387' in txt, 'md \u5e94\u542b\u7a0b\u5e8f\u5b8c\u6574\u7387')

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
    ap = argparse.ArgumentParser(description='\u7ee9\u6548\u9762\u8c08\u51c6\u5907\u4e0e\u5f02\u8bae\u6c9f\u901a\u6838\u67e5')
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