# -*- coding: utf-8 -*-
"""\u4eba\u5c97\u5339\u914d\u5ea6\u6838\u7b97\uff1a\u4e94\u7ef4\u52a0\u6743\u3001\u786c\u95e8\u69db\u901a\u8fc7\u7387\u3001\u5dee\u8ddd\u4f18\u5148\u7ea7\u3002

\u7528\u6cd5:
  python jobfit_score.py --file jobfit.json [--out result.md] [--format json]
  python jobfit_score.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

DIM_KEYS = ('hard_skill', 'soft_skill', 'experience', 'industry', 'motivation')
SCORE_MIN = 1
SCORE_MAX = 5
WEIGHT_TOL = 0.001
# \u52a8\u673a\u4f4e\u4e8e\u6b64\u5206\u5224\u4e3a\u786c\u6027\u8b66\u544a
MOTIVATION_WARN = 3
# \u5339\u914d\u5ea6\u5206\u6863
F_HIGH = 85.0
F_MID = 70.0
F_LOW = 55.0
# \u5dee\u8ddd\u6863\u5224\u5b9a\uff08\u73b0\u72b6 -> \u76ee\u6807\uff09
HIGH_GAP_CUR_MAX = 2
HIGH_GAP_TGT_MIN = 4

DIM_CN = {
    'hard_skill': '\u786c\u6280\u80fd',
    'soft_skill': '\u8f6f\u6280\u80fd',
    'experience': '\u7ecf\u9a8c\u5e74\u9650',
    'industry': '\u884c\u4e1a\u80cc\u666f',
    'motivation': '\u52a8\u673a',
}


def load(text=None, path=None):
    if text:
        return json.loads(text)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def clamp_score(v):
    n = num(v)
    if n is None:
        return None
    if n < SCORE_MIN:
        return SCORE_MIN
    if n > SCORE_MAX:
        return SCORE_MAX
    return n


def dim_check(data):
    """\u4e94\u7ef4\u6253\u5206\u4e0e\u52a0\u6743\u5339\u914d\u5ea6\u3002"""
    src = data.get('dimensions') or {}
    rows = []
    total_w = 0.0
    acc = 0.0
    missing = []
    no_evidence = []
    for k in DIM_KEYS:
        d = src.get(k) or {}
        name = d.get('name') or DIM_CN[k]
        sc = clamp_score(d.get('score'))
        wt = num(d.get('weight'))
        if wt is None or wt < 0:
            wt = 0.0
        ev = (d.get('evidence') or '').strip()
        if sc is None:
            missing.append(name)
        if not ev:
            no_evidence.append(name)
        if sc is not None and wt > 0:
            acc += sc / SCORE_MAX * wt
            total_w += wt
        state = '\u5df2\u6253\u5206' if sc is not None else '\u672a\u6253\u5206'
        if sc is None:
            state = '\u672a\u6253\u5206'
        elif sc == SCORE_MIN:
            state = '\u6700\u4f4e\u5206'
        elif sc == SCORE_MAX:
            state = '\u6ee1\u5206'
        rows.append({'key': k, 'name': name, 'score': sc, 'weight': wt,
                     'evidence': ev or '\uff08\u672a\u586b\uff09', 'state': state})
    fit = round(acc * 100.0, 1) if total_w > 0 else 0.0
    return rows, fit, round(total_w, 4), missing, no_evidence


def gate_check(data):
    """\u786c\u95e8\u69db\uff1a\u4e0d\u53c2\u4e0e\u52a0\u6743\uff0c\u4e00\u7968\u5426\u51b3\u3002"""
    gates = data.get('hard_gates') or []
    rows = []
    failed = []
    for g in gates:
        p = bool(g.get('passed'))
        if not p:
            failed.append(g.get('item') or '\uff08\u672a\u547d\u540d\uff09')
        rows.append({'item': g.get('item') or '\uff08\u672a\u547d\u540d\uff09', 'passed': p,
                     'note': (g.get('note') or '').strip() or '\uff08\u672a\u586b\uff09'})
    rate = 0.0
    if gates:
        rate = round(sum(1 for r in rows if r['passed']) * 100.0 / len(rows), 1)
    return rows, failed, rate


def gap_check(data):
    """\u5dee\u8ddd\u77e9\u9635\u4e0e\u8865\u9f50\u4f18\u5148\u7ea7\u6392\u5e8f\u3002

    \u6392\u5e8f\u89c4\u5219\uff08\u987a\u5e8f\u5957\u7528\uff09\uff1a
      1. \u5f71\u54cd\u5c97\u4f4d\u7b2c\u4e00\u5173\u952e\u52a8\u4f5c\u7684\u6392\u6700\u524d
      2. \u9ad8\u5dee\u8ddd\u6863\u6392\u524d
      3. \u5dee\u8ddd\u7edd\u5bf9\u503c\u5927\u7684\u6392\u524d
    """
    gaps = data.get('gaps') or []
    rows = []
    for g in gaps:
        cur = clamp_score(g.get('current'))
        tgt = clamp_score(g.get('target'))
        diff = None
        if cur is not None and tgt is not None:
            diff = round(tgt - cur, 2)
        crit = bool(g.get('critical_to_first_task'))
        high = (cur is not None and cur <= HIGH_GAP_CUR_MAX
                and tgt is not None and tgt >= HIGH_GAP_TGT_MIN)
        if high:
            grade = '\u9ad8'
        elif diff is not None and diff >= 2:
            grade = '\u4e2d'
        elif diff is not None and diff > 0:
            grade = '\u4f4e'
        else:
            grade = '\u65e0\u5dee\u8ddd'
        prio = 1 if crit else 2
        rows.append({'name': g.get('name') or '\uff08\u672a\u547d\u540d\uff09',
                     'dimension': g.get('dimension') or '\uff08\u672a\u586b\uff09',
                     'current': cur, 'target': tgt, 'diff': diff,
                     'critical': crit, 'grade': grade, 'prio': prio,
                     'feasible_90d': not high})
    rows.sort(key=lambda r: (r['prio'],
                             0 if r['grade'] == '\u9ad8' else 1 if r['grade'] == '\u4e2d' else 2,
                             -(r['diff'] if r['diff'] is not None else 0)))
    for i, r in enumerate(rows, 1):
        r['order'] = i
    infeasible = sum(1 for r in rows if not r['feasible_90d'])
    return rows, infeasible


def verdict_of(fit, gate_failed):
    if gate_failed:
        return '\u786c\u95e8\u69db\u672a\u8fc7\uff0c\u5148\u89e3\u51b3\u95e8\u69db\u95ee\u9898\uff0c\u4e0d\u8981\u7528\u52a0\u6743\u5206\u63a9\u76d6\u786c\u4f24'
    if fit >= F_HIGH:
        return '\u9ad8\u5339\u914d\uff0c\u53ef\u91cd\u70b9\u63a8\u8fdb\uff1b\u5dee\u8ddd\u5f53\u4f5c\u52a0\u5206\u9879\u8865'
    if fit >= F_MID:
        return '\u5339\u914d\uff0c\u8865\u9f50 1-2 \u4e2a\u5173\u952e\u5dee\u8ddd\u540e\u5b89\u6392\u9762\u8bd5'
    if fit >= F_LOW:
        return '\u53ef\u8003\u8651\u4f46\u9700\u660e\u786e\u4ee3\u4ef7\uff1a\u964d\u4f4e\u9884\u671f / \u63a5\u8fc7\u6e21\u5c97 / \u6295\u5165 3-6 \u4e2a\u6708\u8865\u9f50'
    return '\u8c28\u614e\uff0c\u8bda\u5b9e\u8bc4\u4f30\u8865\u9f50\u6210\u672c\u662f\u5426\u9ad8\u4e8e\u6362\u5de5\u4f5c\u7684\u6536\u76ca'


def build(data, fmt='md'):
    title = data.get('title') or '\u4eba\u5c97\u5339\u914d\u4f53\u68c0'
    owner = data.get('owner') or '\uff08\u672a\u586b\uff09'
    role = data.get('role') or '\uff08\u672a\u586b\uff09'
    d_rows, fit, wsum, missing, no_evidence = dim_check(data)
    g_rows, gate_failed, gate_rate = gate_check(data)
    gap_rows, infeasible = gap_check(data)
    v = verdict_of(fit, gate_failed)

    if fmt == 'json':
        return {'title': title, 'owner': owner, 'role': role,
                'fit_score': fit, 'weight_sum': wsum,
                'dimensions': d_rows, 'missing_dimensions': missing,
                'no_evidence_dimensions': no_evidence,
                'hard_gates': g_rows, 'gate_failed': gate_failed,
                'gate_rate': gate_rate, 'gaps': gap_rows,
                'infeasible_90d': infeasible, 'verdict': v}

    out = []
    out.append('# %s' % title)
    out.append('')
    out.append('- \u5bf9\u8c61\uff1a%s' % owner)
    out.append('- \u76ee\u6807\u5c97\u4f4d\uff1a%s' % role)
    out.append('- \u52a0\u6743\u5339\u914d\u5ea6\uff1a%.1f%%' % fit)
    out.append('- \u6743\u91cd\u5408\u8ba1\uff1a%s' % ('%.2f\uff08\u6b63\u5e38\uff09' % wsum
                                   if abs(wsum - 1.0) <= WEIGHT_TOL else '%.2f\uff08\u4e0d\u7b49\u4e8e 1\uff09' % wsum))
    out.append('- \u786c\u95e8\u69db\u901a\u8fc7\u7387\uff1a%.1f%%\uff08%d \u9879\uff09' % (gate_rate, len(g_rows)))
    out.append('- \u672a\u8fc7\u95e8\u69db\u9879\uff1a%s' % ('\u3001'.join(gate_failed) if gate_failed else '\u65e0'))
    out.append('- \u5dee\u8ddd\u9879\u6570\uff1a%d\uff08\u5176\u4e2d 90 \u5929\u5185\u96be\u8865\u9f50 %d \u9879\uff09' % (len(gap_rows), infeasible))
    out.append('- \u7ed3\u8bba\uff1a%s' % v)
    out.append('')
    out.append('## \u4e00\u3001\u4e94\u7ef4\u6253\u5206')
    out.append('')
    out.append('| \u7ef4\u5ea6 | \u5f97\u5206 | \u6743\u91cd | \u4f9d\u636e | \u72b6\u6001 |')
    out.append('|---|---|---|---|---|')
    for r in d_rows:
        sc = ('%.0f' % r['score']) if r['score'] is not None else '\u672a\u6253\u5206'
        out.append('| %s | %s | %.2f | %s | %s |' % (
            r['name'], sc, r['weight'], r['evidence'], r['state']))
    out.append('')
    out.append('## \u4e8c\u3001\u786c\u95e8\u69db')
    out.append('')
    if not g_rows:
        out.append('\u672a\u586b\u786c\u95e8\u69db\u3002\u672c\u6280\u80fd\u7ed9\u51fa\u4e94\u7c7b\u4f9b\u53c2\u8003\uff1a\u6cd5\u5b9a\u6301\u8bc1\u8981\u6c42\u3001\u5b66\u5386\u95e8\u69db\u3001\u5173\u952e\u5de5\u5177\u72ec\u7acb\u64cd\u4f5c\u3001'
                   '\u5165\u804c\u65f6\u95f4\u51b2\u7a81\u3001\u52a8\u673a\u4e0e\u5c97\u4f4d\u65b9\u5411\u4e00\u81f4\u3002')
    else:
        out.append('| \u786c\u95e8\u69db | \u662f\u5426\u901a\u8fc7 | \u5907\u6ce8 |')
        out.append('|---|---|---|')
        for r in g_rows:
            out.append('| %s | %s | %s |' % (r['item'], '\u662f' if r['passed'] else '\u5426', r['note']))
    out.append('')
    out.append('## \u4e09\u3001\u80fd\u529b\u5dee\u8ddd\u77e9\u9635\u4e0e\u8865\u9f50\u4f18\u5148\u7ea7')
    out.append('')
    if not gap_rows:
        out.append('\u672a\u586b\u5dee\u8ddd\u9879\u3002\u5339\u914d\u5ea6\u4e0d\u7b49\u4e8e\u6ca1\u6709\u5dee\u8ddd\uff0c\u6ca1\u6709\u5dee\u8ddd\u9879\u901a\u5e38\u610f\u5473\u7740\u6253\u5206\u504f\u9ad8\u3002')
    else:
        out.append('| \u5e8f | \u5dee\u8ddd\u9879 | \u7ef4\u5ea6 | \u73b0\u72b6 | \u76ee\u6807 | \u5dee\u8ddd | \u6863 | \u5f71\u54cd\u7b2c\u4e00\u52a8\u4f5c | 90 \u5929\u53ef\u8865 |')
        out.append('|---|---|---|---|---|---|---|---|---|')
        for r in gap_rows:
            cur = ('%.0f' % r['current']) if r['current'] is not None else '-'
            tgt = ('%.0f' % r['target']) if r['target'] is not None else '-'
            diff = ('%+.0f' % r['diff']) if r['diff'] is not None else '-'
            out.append('| %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                r['order'], r['name'], r['dimension'], cur, tgt, diff, r['grade'],
                '\u662f' if r['critical'] else '\u5426',
                '\u662f' if r['feasible_90d'] else '\u5426\uff08\u9700\u5b9e\u6218\u79ef\u7d2f\uff09'))
    out.append('')
    out.append('## \u56db\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if gate_failed:
        idx += 1
        out.append('%d. \u786c\u95e8\u69db\u672a\u8fc7\uff1a%s\u3002\u786c\u95e8\u69db\u662f\u4e58\u6cd5\u9879\uff0c\u5148\u89e3\u51b3\u95e8\u69db\u518d\u8c08\u5339\u914d\u5ea6\u3002'
                   % (idx, '\u3001'.join(gate_failed)))
    if missing:
        idx += 1
        out.append('%d. %s \u672a\u6253\u5206\uff1a\u8865\u9f50\u540e\u91cd\u7b97\u5339\u914d\u5ea6\u3002' % (idx, '\u3001'.join(missing)))
    if no_evidence:
        idx += 1
        out.append('%d. %s \u7f3a\u6253\u5206\u4f9d\u636e\uff1a\u6bcf\u4e2a\u5206\u6570\u90fd\u8981\u6709\u53ef\u9a8c\u8bc1\u7684\u9879\u76ee\u6216\u4ea7\u51fa\uff0c\u4e0d\u63a5\u53d7\u300c\u5e94\u8be5\u8fd8\u884c\u300d\u3002'
                   % (idx, '\u3001'.join(no_evidence)))
    mot = [r for r in d_rows if r['key'] == 'motivation']
    if mot and mot[0]['score'] is not None and mot[0]['score'] < MOTIVATION_WARN:
        idx += 1
        out.append('%d. \u52a8\u673a\u5f97\u5206 %.0f \u4f4e\u4e8e %d\uff1a\u52a8\u673a\u4e0d\u5339\u914d\u7559\u4e0d\u4f4f\uff0c\u8fd9\u4e00\u8f6e\u4e0d\u5efa\u8bae\u6295\u3002'
                   % (idx, mot[0]['score'], MOTIVATION_WARN))
    if abs(wsum - 1.0) > WEIGHT_TOL:
        idx += 1
        out.append('%d. \u6743\u91cd\u5408\u8ba1\u4e3a %.2f\uff0c\u4e0d\u7b49\u4e8e 1\uff1a\u6309\u4e94\u7ef4\u9ed8\u8ba4\u6743\u91cd\uff080.30/0.20/0.20/0.15/0.15\uff09\u6838\u5bf9\u3002' % (idx, wsum))
    crit = [r['name'] for r in gap_rows if r['critical']]
    if crit:
        idx += 1
        out.append('%d. \u5173\u952e\u5dee\u8ddd %s \u5f71\u54cd\u5c97\u4f4d\u7b2c\u4e00\u5173\u952e\u52a8\u4f5c\uff1a\u628a\u5b83\u4eec\u6392\u5728\u8865\u9f50\u8ba1\u5212\u6700\u524d\u9762\u3002'
                   % (idx, '\u3001'.join(crit)))
    if infeasible:
        idx += 1
        out.append('%d. %d \u9879\u5dee\u8ddd 90 \u5929\u5185\u96be\u8865\u9f50\uff08\u9ad8\u5dee\u8ddd\u6863\uff09\uff1a\u82e5\u5176\u4e2d\u6709\u786c\u95e8\u69db\u66ff\u4ee3\u9879\uff0c\u91cd\u65b0\u8bc4\u4f30\u8fd9\u4e2a\u5c97\u4f4d\u662f\u5426\u503c\u5f97\u6295\u3002'
                   % (idx, infeasible))
    if not gap_rows and fit >= F_HIGH:
        idx += 1
        out.append('%d. \u5339\u914d\u5ea6\u9ad8\u4f46\u4e00\u6761\u5dee\u8ddd\u90fd\u6ca1\u5217\uff1a\u7edd\u5927\u591a\u6570\u4eba\u90fd\u6709\u81f3\u5c11\u4e00\u9879\u5dee\u8ddd\uff0c'
                   '\u96f6\u5dee\u8ddd\u901a\u5e38\u610f\u5473\u7740\u6253\u5206\u504f\u4e50\u89c2\u3002' % idx)
    if not idx:
        out.append('\u4e94\u7ef4\u6253\u5206\u3001\u95e8\u69db\u4e0e\u5dee\u8ddd\u77e9\u9635\u5747\u5df2\u586b\u9f50\u3002\u9762\u8bd5\u65f6\u4f18\u5148\u95ee \u00a7\u516d \u95ee\u9898\u6e05\u5355\u7684\u524d 4 \u9898\u3002')
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

    full_dims = {
        'hard_skill': {'score': 5, 'weight': 0.30, 'evidence': 'e'},
        'soft_skill': {'score': 4, 'weight': 0.20, 'evidence': 'e'},
        'experience': {'score': 2, 'weight': 0.20, 'evidence': 'e'},
        'industry': {'score': 2, 'weight': 0.15, 'evidence': 'e'},
        'motivation': {'score': 5, 'weight': 0.15, 'evidence': 'e'},
    }
    r = build({'dimensions': full_dims}, 'json')
    # 5/5*0.30 + 4/5*0.20 + 2/5*0.20 + 2/5*0.15 + 5/5*0.15 = 0.75 -> 75%
    chk(abs(r['fit_score'] - 75.0) < 0.05, '\u6309\u6743\u91cd\u590d\u6838\u7b97\u5e94\u5f97 75')
    chk(abs(r['weight_sum'] - 1.0) < 0.001, '\u6743\u91cd\u5408\u8ba1\u5e94\u4e3a 1')
    chk(len(r['dimensions']) == 5, '\u5e94\u8f93\u51fa 5 \u4e2a\u7ef4\u5ea6')
    chk(r['missing_dimensions'] == [], '\u9f50\u5168\u65f6\u4e0d\u5e94\u6709\u672a\u6253\u5206\u7ef4\u5ea6')

    all5 = {k: {'score': 5, 'weight': w, 'evidence': 'e'} for k, w in zip(
        DIM_KEYS, (0.30, 0.20, 0.20, 0.15, 0.15))}
    r = build({'dimensions': all5}, 'json')
    chk(abs(r['fit_score'] - 100.0) < 0.05, '\u5168\u6ee1\u5206\u5e94\u4e3a 100')

    no_ev = {'hard_skill': {'score': 3, 'weight': 0.3, 'evidence': ''}}
    r = build({'dimensions': no_ev}, 'json')
    chk(len(r['no_evidence_dimensions']) == 5, '\u672a\u586b\u4f9d\u636e\u7684 4 \u4e2a\u7ef4\u5ea6\u4e5f\u5e94\u88ab\u8bb0\u5165')
    chk('\u786c\u6280\u80fd' in r['no_evidence_dimensions'], '\u7f3a\u4f9d\u636e\u5e94\u8bb0\u5230\u786c\u6280\u80fd')

    r = build({'dimensions': {}}, 'json')
    chk(len(r['missing_dimensions']) == 5, '\u7a7a\u7ef4\u5ea6\u5e94\u6709 5 \u6761\u672a\u6253\u5206')
    chk(r['fit_score'] == 0.0, '\u7a7a\u7ef4\u5ea6\u5339\u914d\u5ea6\u4e3a 0')

    out_of_range = {
        'hard_skill': {'score': 9, 'weight': 1.0, 'evidence': 'e'},
        'soft_skill': {'score': 0, 'weight': 0, 'evidence': 'e'},
        'experience': {'score': 'x', 'weight': 0, 'evidence': 'e'},
        'industry': {'score': None, 'weight': 0, 'evidence': 'e'},
        'motivation': {'score': 5, 'weight': 0, 'evidence': 'e'},
    }
    r = build({'dimensions': out_of_range}, 'json')
    hard = [d for d in r['dimensions'] if d['key'] == 'hard_skill'][0]
    soft = [d for d in r['dimensions'] if d['key'] == 'soft_skill'][0]
    exp = [d for d in r['dimensions'] if d['key'] == 'experience'][0]
    chk(hard['score'] == 5, '\u8d85\u4e0a\u9650 9 \u5e94\u5939\u5230 5')
    chk(soft['score'] == 1, '\u4f4e\u4e8e\u4e0b\u9650 0 \u5e94\u5939\u5230 1')
    chk(exp['score'] is None, '\u975e\u6cd5\u5b57\u7b26\u4e32\u5e94\u5224\u4e3a\u672a\u6253\u5206')

    g_fail = {'hard_gates': [{'item': 'A', 'passed': True},
                             {'item': 'B', 'passed': False}]}
    r = build(g_fail, 'json')
    chk(r['gate_failed'] == ['B'], '\u672a\u8fc7\u95e8\u69db\u5e94\u53ea\u8bb0 B')
    chk(abs(r['gate_rate'] - 50.0) < 0.05, '\u4e24\u9879\u8fc7\u4e00\u5e94 50')
    chk('\u786c\u95e8\u69db' in r['verdict'], '\u95e8\u69db\u672a\u8fc7\u7ed3\u8bba\u5e94\u5148\u5904\u7406\u95e8\u69db')

    r = build({'hard_gates': []}, 'json')
    chk(r['gate_rate'] == 0.0, '\u7a7a\u95e8\u69db\u901a\u8fc7\u7387\u4e3a 0 \u800c\u975e\u62a5\u9519')

    g_ok = {'hard_gates': [{'item': 'A', 'passed': True}],
            'dimensions': all5}
    r = build(g_ok, 'json')
    chk('\u786c\u95e8\u69db\u672a\u8fc7' not in r['verdict'], '\u95e8\u69db\u5168\u8fc7\u4e0d\u5e94\u51fa\u73b0\u672a\u8fc7\u5b57\u6837')

    gaps = {'gaps': [
        {'name': '\u4f4e\u6863\u666e\u901a', 'current': 3, 'target': 4, 'critical_to_first_task': False},
        {'name': '\u5173\u952e\u9ad8\u6863', 'current': 1, 'target': 5, 'critical_to_first_task': True},
        {'name': '\u9ad8\u4f46\u4e0d\u5173\u952e', 'current': 2, 'target': 4, 'critical_to_first_task': False},
        {'name': '\u65e0\u5dee\u8ddd', 'current': 4, 'target': 4, 'critical_to_first_task': False},
    ]}
    r = build(gaps, 'json')
    names = [g['name'] for g in r['gaps']]
    chk(names[0] == '\u5173\u952e\u9ad8\u6863', '\u5f71\u54cd\u7b2c\u4e00\u52a8\u4f5c\u7684\u9ad8\u5dee\u8ddd\u5e94\u6392\u7b2c\u4e00')
    chk(names[-1] == '\u65e0\u5dee\u8ddd', '\u65e0\u5dee\u8ddd\u5e94\u6392\u6700\u540e')
    chk(r['infeasible_90d'] == 2, '\u9ad8\u5dee\u8ddd\u6863\u5e94\u4e3a 2 \u9879')
    no_gap = [g for g in r['gaps'] if g['name'] == '\u65e0\u5dee\u8ddd'][0]
    chk(no_gap['grade'] == '\u65e0\u5dee\u8ddd', '\u73b0\u72b6\u7b49\u4e8e\u76ee\u6807\u5e94\u5224\u65e0\u5dee\u8ddd')

    r = build({'gaps': [{'name': 'A', 'current': 2, 'target': 4}]}, 'json')
    chk(r['gaps'][0]['grade'] == '\u9ad8', '2 \u5230 4 \u5e94\u5224\u9ad8\u5dee\u8ddd\u6863')
    r = build({'gaps': [{'name': 'A', 'current': 1, 'target': 3}]}, 'json')
    chk(r['gaps'][0]['grade'] == '\u4e2d', '1 \u5230 2 \u5e94\u5224\u4e2d\u5dee\u8ddd\u6863')
    chk(r['gaps'][0]['diff'] == 2, 'gap diff should be 2')

    r = build({'gaps': []}, 'json')
    chk(len(r['gaps']) == 0, '\u7a7a\u5dee\u8ddd\u5217\u8868\u4e0d\u5e94\u62a5\u9519')

    txt = build(g_ok, 'md')
    chk('\u4e94\u7ef4\u6253\u5206' in txt, 'md \u5e94\u542b\u4e94\u7ef4\u6253\u5206\u8868')
    chk('\u786c\u95e8\u69db' in txt, 'md \u5e94\u542b\u786c\u95e8\u69db\u8868')
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
    ap = argparse.ArgumentParser(description='\u4eba\u5c97\u5339\u914d\u5206\u6790\u4e0e\u80fd\u529b\u5dee\u8ddd\u6838\u67e5')
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