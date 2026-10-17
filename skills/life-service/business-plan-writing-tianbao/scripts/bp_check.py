# -*- coding: utf-8 -*-
"""BP \u6838\u67e5\uff1a\u7ae0\u8282\u5b8c\u6574\u5ea6\u3001\u8d22\u52a1\u52fe\u7a3d\u3001\u5355\u4f4d\u7ecf\u6d4e\u3001\u6570\u636e\u6765\u6e90\u6807\u6ce8\u3002

\u7528\u6cd5:
  python bp_check.py --file bp.json [--out result.md] [--format json]
  python bp_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

MODULES = ('problem', 'solution', 'market', 'business',
           'competition', 'finance', 'team', 'funding')
CORE_MODULES = ('problem', 'solution', 'market', 'business',
                'competition', 'finance')

SECTION_RED = 80.0
ANSWER_RED = 70.0
# LTV/CAC \u5224\u5b9a\u9608\u503c
LTVCAC_MIN = 3.0
# \u56de\u672c\u5468\u671f\uff08\u6708\uff09
PAYBACK_WARN = 12
# \u98ce\u9669\u62ab\u9732\u6761\u6570
RISK_MIN = 3
# \u6536\u5165\u540c\u6bd4\u589e\u901f\u8d85\u8fc7\u6b64\u500d\u6570\u89c6\u4e3a\u9700\u8981\u62c6\u89e3\u8def\u5f84
GROWTH_JUMP = 3.0

MOD_CN = {
    'problem': '\u95ee\u9898', 'solution': '\u65b9\u6848', 'market': '\u5e02\u573a',
    'business': '\u5546\u4e1a\u6a21\u5f0f', 'competition': '\u7ade\u4e89', 'finance': '\u8d22\u52a1',
    'team': '\u56e2\u961f', 'funding': '\u878d\u8d44',
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


def series(fin, key):
    v = fin.get(key) or []
    return [num(x) for x in v]


def section_check(data):
    secs = data.get('sections') or []
    rows = []
    present = set()
    total_q = 0
    ans_q = 0
    for s in secs:
        m = s.get('module')
        p = bool(s.get('present'))
        if m and p:
            present.add(m)
        tq = int(num(s.get('total_questions')) or 0)
        aq = int(num(s.get('answered_questions')) or 0)
        if aq > tq:
            aq = tq
        total_q += tq
        ans_q += aq
        rows.append({'module': m or '', 'name': s.get('name') or MOD_CN.get(m, ''),
                     'present': p, 'answered': aq, 'total': tq,
                     'rate': round(aq * 100.0 / tq, 1) if tq else 0.0})
    for m in MODULES:
        if m not in present:
            rows.append({'module': m, 'name': MOD_CN[m], 'present': False,
                         'answered': 0, 'total': 0, 'rate': 0.0})
    cov = round(len(present) * 100.0 / len(MODULES), 1)
    ans_rate = round(ans_q * 100.0 / total_q, 1) if total_q else 0.0
    return rows, present, cov, ans_rate


def finance_check(data):
    """\u4e09\u6761\u52fe\u7a3d\u6821\u9a8c + \u6536\u5165\u589e\u901f\u8df3\u53d8\u68c0\u6d4b\u3002"""
    fin = data.get('finance') or {}
    rev = series(fin, 'revenue')
    cost = series(fin, 'cost')
    gp = series(fin, 'gross_profit')
    rd = series(fin, 'rd_expense')
    se = series(fin, 'sales_expense')
    ad = series(fin, 'admin_expense')
    op = series(fin, 'op_profit')
    beg = series(fin, 'begin_cash')
    end = series(fin, 'end_cash')
    ocf = series(fin, 'op_cash_flow')

    n = len(rev)
    years = fin.get('years') or []
    checks = []
    issues = []

    # 1. \u6bdb\u5229 = \u6536\u5165 - \u6210\u672c
    gp_rows = []
    for i in range(n):
        r, c, g = (rev[i] if i < len(rev) else None,
                   cost[i] if i < len(cost) else None,
                   gp[i] if i < len(gp) else None)
        y = years[i] if i < len(years) else i + 1
        if r is None or c is None or g is None:
            gp_rows.append({'year': y, 'rev': r, 'cost': c, 'gp': g,
                            'expect': None, 'ok': False, 'note': '\u7f3a\u5c11\u79d1\u76ee'})
            continue
        exp = r - c
        ok = abs(exp - g) <= max(1.0, abs(exp) * 0.001)
        gp_rows.append({'year': y, 'rev': r, 'cost': c, 'gp': g,
                        'expect': round(exp, 2), 'ok': ok,
                        'note': '' if ok else '\u52fe\u7a3d\u4e0d\u7b26'})
        if not ok:
            issues.append('%s \u5e74\u6bdb\u5229\u52fe\u7a3d\u4e0d\u7b26\uff1a\u6536\u5165 %s - \u6210\u672c %s = %s\uff0c\u8868\u5185\u5199 %s'
                          % (y, r, c, round(exp, 2), g))
    checks.append({'name': '\u6bdb\u5229 = \u8425\u4e1a\u6536\u5165 - \u8425\u4e1a\u6210\u672c', 'ok': not issues})

    # 2. \u7ecf\u8425\u5229\u6da6 = \u6bdb\u5229 - \u7814\u53d1 - \u9500\u552e - \u7ba1\u7406
    op_issues = []
    op_rows = []
    for i in range(n):
        g = gp[i] if i < len(gp) else None
        vals = [rd[i] if i < len(rd) else None,
                se[i] if i < len(se) else None,
                ad[i] if i < len(ad) else None]
        o = op[i] if i < len(op) else None
        y = years[i] if i < len(years) else i + 1
        if g is None or o is None or any(v is None for v in vals):
            op_rows.append({'year': y, 'gp': g, 'op': o, 'expect': None,
                            'ok': False, 'note': '\u7f3a\u5c11\u79d1\u76ee'})
            op_issues.append('%s \u5e74\u7ecf\u8425\u5229\u6da6\u7f3a\u5c11\u79d1\u76ee\uff0c\u65e0\u6cd5\u6821\u9a8c' % y)
            continue
        exp = g - vals[0] - vals[1] - vals[2]
        ok = abs(exp - o) <= max(1.0, abs(exp) * 0.001)
        op_rows.append({'year': y, 'gp': g, 'op': o, 'expect': round(exp, 2),
                        'ok': ok, 'note': '' if ok else '\u52fe\u7a3d\u4e0d\u7b26'})
        if not ok:
            op_issues.append('%s \u5e74\u7ecf\u8425\u5229\u6da6\u52fe\u7a3d\u4e0d\u7b26\uff1a\u6bdb\u5229 %s - \u8d39\u7528\u5408\u8ba1 %s = %s\uff0c\u8868\u5185\u5199 %s'
                             % (y, g, round(vals[0] + vals[1] + vals[2], 2),
                                round(exp, 2), o))
    checks.append({'name': '\u7ecf\u8425\u5229\u6da6 = \u6bdb\u5229 - \u4e09\u9879\u8d39\u7528',
                   'ok': not op_issues})

    # 3. \u671f\u672b\u73b0\u91d1 = \u671f\u521d\u73b0\u91d1 + \u7ecf\u8425\u6027\u73b0\u91d1\u6d41
    cash_rows = []
    cash_issues = []
    for i in range(n):
        b = beg[i] if i < len(beg) else None
        c = ocf[i] if i < len(ocf) else None
        e = end[i] if i < len(end) else None
        y = years[i] if i < len(years) else i + 1
        if b is None or c is None or e is None:
            cash_rows.append({'year': y, 'begin': b, 'ocf': c, 'end': e,
                              'expect': None, 'ok': False, 'note': '\u7f3a\u5c11\u79d1\u76ee'})
            cash_issues.append('%s \u5e74\u73b0\u91d1\u6d41\u7f3a\u5c11\u79d1\u76ee\uff0c\u65e0\u6cd5\u6821\u9a8c' % y)
            continue
        exp = b + c
        ok = abs(exp - e) <= max(1.0, abs(exp) * 0.01)
        cash_rows.append({'year': y, 'begin': b, 'ocf': c, 'end': e,
                          'expect': round(exp, 2), 'ok': ok,
                          'note': '' if ok else '\u52fe\u7a3d\u4e0d\u7b26'})
        if not ok:
            cash_issues.append('%s \u5e74\u671f\u672b\u73b0\u91d1\u52fe\u7a3d\u4e0d\u7b26\uff1a\u671f\u521d %s + \u7ecf\u8425\u73b0\u91d1\u6d41 %s = %s\uff0c\u8868\u5185\u5199 %s'
                               % (y, b, c, round(exp, 2), e))
    checks.append({'name': '\u671f\u672b\u73b0\u91d1 = \u671f\u521d\u73b0\u91d1 + \u7ecf\u8425\u6027\u73b0\u91d1\u6d41',
                   'ok': not cash_issues})

    # \u6536\u5165\u589e\u901f\u8df3\u53d8
    jumps = []
    for i in range(1, n):
        p, cur = rev[i - 1], rev[i]
        if p and cur and p > 0 and (cur / p) >= GROWTH_JUMP:
            y = years[i] if i < len(years) else i + 1
            jumps.append('%s \u5e74\u6536\u5165 %s \u76f8\u5bf9\u4e0a\u5e74 %s \u589e\u957f %.1f \u500d\uff0c\u9700\u62c6\u89e3\u300c\u7528\u6237\u6570 \u00d7 \u4ed8\u8d39\u7387 \u00d7 \u5ba2\u5355\u4ef7\u300d'
                         % (y, cur, p, cur / p))
    issues.extend(op_issues)
    issues.extend(cash_issues)
    issues.extend(jumps)
    passed = sum(1 for c in checks if c['ok'])
    return {'checks': checks, 'gp_rows': gp_rows, 'op_rows': op_rows,
            'cash_rows': cash_rows, 'issues': issues,
            'passed': passed, 'rate': round(passed * 100.0 / len(checks), 1),
            'jumps': jumps, 'years': years, 'revenue': rev,
            'gross_margin': [(round(gp[i] * 100.0 / rev[i], 1)
                              if i < len(gp) and rev[i] else None)
                             for i in range(n)]}


def ue_check(data):
    """\u5355\u4f4d\u7ecf\u6d4e\u6a21\u578b\u3002"""
    ue = data.get('ue') or {}
    arppu = num(ue.get('arppu'))
    vc = num(ue.get('variable_cost'))
    cac = num(ue.get('cac'))
    rep = num(ue.get('repeat_times'))
    churn = num(ue.get('churn_monthly'))

    out = {'arppu': arppu, 'variable_cost': vc, 'cac': cac,
           'repeat_times': rep, 'gross_profit': None, 'margin': None,
           'ltv': None, 'ltv_cac': None, 'payback_months': None,
           'state': '\u53c2\u6570\u4e0d\u5168'}
    issues = []
    if arppu is None or vc is None or arppu <= 0:
        issues.append('\u5ba2\u5355\u4ef7\u6216\u53d8\u52a8\u6210\u672c\u7f3a\u5931/\u975e\u6cd5\uff0c\u5355\u4f4d\u7ecf\u6d4e\u6a21\u578b\u65e0\u6cd5\u8ba1\u7b97')
        return out, issues
    gp = arppu - vc
    out['gross_profit'] = round(gp, 2)
    out['margin'] = round(gp * 100.0 / arppu, 1)
    if gp <= 0:
        out['state'] = '\u6bdb\u5229\u4e3a\u8d1f'
        issues.append('\u5ba2\u5355\u4ef7 %.2f \u5c0f\u4e8e\u7b49\u4e8e\u53d8\u52a8\u6210\u672c %.2f\uff0c\u5355\u5ba2\u6237\u6bdb\u5229\u4e3a\u8d1f' % (arppu, vc))
        return out, issues
    if rep is not None and rep >= 0:
        out['ltv'] = round(gp * rep, 2)
        if cac is not None and cac > 0:
            out['ltv_cac'] = round(gp * rep / cac, 2)
            if out['ltv_cac'] < LTVCAC_MIN:
                issues.append('LTV/CAC = %.2f \u4f4e\u4e8e %.0f\uff0c\u5355\u4f4d\u7ecf\u6d4e\u5c1a\u672a\u8dd1\u901a'
                              % (out['ltv_cac'], LTVCAC_MIN))
    if cac is not None and cac > 0 and churn and churn > 0:
        life = 1.0 / churn
        out['payback_months'] = round(cac / (gp * churn), 1)
        if out['payback_months'] > PAYBACK_WARN:
            issues.append('\u56de\u672c\u5468\u671f %.1f \u4e2a\u6708\u8d85\u8fc7 %d \u4e2a\u6708\uff0c\u73b0\u91d1\u538b\u529b\u663e\u8457'
                          % (out['payback_months'], PAYBACK_WARN))
        if life <= 0:
            issues.append('\u6708\u6d41\u5931\u7387\u5f02\u5e38')
    if rep is None:
        issues.append('\u672a\u586b\u590d\u8d2d\u6b21\u6570\uff0cLTV \u9700\u6309\u7559\u5b58\u66f2\u7ebf\u63a8\u5bfc')
    if churn is None:
        issues.append('\u672a\u586b\u6708\u6d41\u5931\u7387\uff0c\u56de\u672c\u5468\u671f\u65e0\u6cd5\u63a8\u5bfc')
    out['state'] = '\u53ef\u8ba1\u7b97'
    return out, issues


def source_check(data):
    srcs = data.get('data_sources') or []
    rows = []
    ok = 0
    for s in srcs:
        name = s.get('item') or '\uff08\u672a\u547d\u540d\uff09'
        source = (s.get('source') or '').strip()
        year = str(s.get('year') or '').strip()
        marked = bool(source)
        if marked:
            ok += 1
        miss = []
        if not source:
            miss.append('\u7f3a\u6765\u6e90')
        if not year:
            miss.append('\u7f3a\u65f6\u70b9')
        rows.append({'item': name, 'source': source or '\uff08\u672a\u586b\uff09',
                     'year': year or '\uff08\u672a\u586b\uff09', 'marked': marked,
                     'miss': miss})
    rate = 0.0
    if srcs:
        rate = round(ok * 100.0 / len(srcs), 1)
    return rows, rate


def build(data, fmt='md'):
    title = data.get('title') or 'BP \u4f53\u68c0'
    s_rows, present, cov, ans_rate = section_check(data)
    f = finance_check(data)
    ue, ue_issues = ue_check(data)
    src_rows, src_rate = source_check(data)
    risks = data.get('risks') or []
    missing = [MOD_CN[m] for m in MODULES if m not in present]

    if fmt == 'json':
        return {'title': title, 'section_coverage': cov,
                'missing_modules': missing, 'answer_rate': ans_rate,
                'finance_rate': f['rate'], 'finance_issues': f['issues'],
                'finance_checks': f['checks'],
                'ue': ue, 'ue_issues': ue_issues,
                'source_rate': src_rate,
                'unmarked_sources': [r['item'] for r in src_rows if not r['marked']],
                'risk_count': len(risks)}

    out = []
    out.append('# %s' % title)
    out.append('')
    out.append('- \u7ae0\u8282\u5b8c\u6574\u7387\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff09' % (cov, SECTION_RED))
    out.append('- \u7f3a\u5931\u7ae0\u8282\uff1a%s' % ('\u3001'.join(missing) if missing else '\u65e0'))
    out.append('- \u5fc5\u7b54\u9898\u56de\u7b54\u7387\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff09' % (ans_rate, ANSWER_RED))
    out.append('- \u8d22\u52a1\u52fe\u7a3d\u901a\u8fc7\uff1a%d/%d \u9879\uff08%.1f%%\uff09'
               % (f['passed'], len(f['checks']), f['rate']))
    out.append('- \u8d22\u52a1\u5f02\u5e38\u6761\u6570\uff1a%d' % len(f['issues']))
    out.append('- \u5355\u4f4d\u7ecf\u6d4e\u72b6\u6001\uff1a%s' % ue['state'])
    out.append('- \u6570\u636e\u6765\u6e90\u6807\u6ce8\u7387\uff1a%.1f%%' % src_rate)
    out.append('- \u98ce\u9669\u62ab\u9732\u6761\u6570\uff1a%d\uff08\u5efa\u8bae\u4e0d\u5c11\u4e8e %d \u6761\uff09' % (len(risks), RISK_MIN))
    out.append('')
    out.append('## \u4e00\u3001\u7ae0\u8282\u4e0e\u5fc5\u7b54\u9898')
    out.append('')
    out.append('| \u6a21\u5757 | \u662f\u5426\u5177\u5907 | \u5df2\u7b54 | \u5fc5\u7b54 | \u56de\u7b54\u7387 |')
    out.append('|---|---|---|---|---|')
    for r in s_rows:
        out.append('| %s | %s | %d | %d | %s |' % (
            r['name'], '\u662f' if r['present'] else '\u5426', r['answered'],
            r['total'], ('%.1f%%' % r['rate']) if r['total'] else '-'))
    out.append('')
    out.append('## \u4e8c\u3001\u8d22\u52a1\u52fe\u7a3d\u6821\u9a8c')
    out.append('')
    for c in f['checks']:
        out.append('- [%s] %s' % ('x' if c['ok'] else ' ', c['name']))
    out.append('')
    out.append('### \u6bdb\u5229')
    out.append('')
    out.append('| \u5e74 | \u6536\u5165 | \u6210\u672c | \u8868\u5185\u6bdb\u5229 | \u5e94\u4e3a | \u5224\u5b9a |')
    out.append('|---|---|---|---|---|---|')
    for r in f['gp_rows']:
        out.append('| %s | %s | %s | %s | %s | %s |' % (
            r['year'], r['rev'], r['cost'], r['gp'], r['expect'],
            '\u52fe\u7a3d\u4e0d\u7b26' if not r['ok'] else 'OK'))
    out.append('')
    out.append('### \u7ecf\u8425\u5229\u6da6')
    out.append('')
    out.append('| \u5e74 | \u6bdb\u5229 | \u8868\u5185\u7ecf\u8425\u5229\u6da6 | \u5e94\u4e3a | \u5224\u5b9a |')
    out.append('|---|---|---|---|---|')
    for r in f['op_rows']:
        out.append('| %s | %s | %s | %s | %s |' % (
            r['year'], r['gp'], r['op'], r['expect'],
            '\u52fe\u7a3d\u4e0d\u7b26' if not r['ok'] else 'OK'))
    out.append('')
    out.append('### \u73b0\u91d1\u6d41')
    out.append('')
    out.append('| \u5e74 | \u671f\u521d\u73b0\u91d1 | \u7ecf\u8425\u73b0\u91d1\u6d41 | \u8868\u5185\u671f\u672b | \u5e94\u4e3a | \u5224\u5b9a |')
    out.append('|---|---|---|---|---|---|')
    for r in f['cash_rows']:
        out.append('| %s | %s | %s | %s | %s | %s |' % (
            r['year'], r['begin'], r['ocf'], r['end'], r['expect'],
            '\u52fe\u7a3d\u4e0d\u7b26' if not r['ok'] else 'OK'))
    out.append('')
    gm = f['gross_margin']
    if any(g is not None for g in gm):
        out.append('\u6bdb\u5229\u7387\uff1a%s' % '\u3001'.join(
            '%s \u5e74 %s%%' % (f['years'][i] if i < len(f['years']) else i + 1, g)
            for i, g in enumerate(gm) if g is not None))
        out.append('')
    if f['issues']:
        out.append('### \u8d22\u52a1\u5f02\u5e38\u660e\u7ec6')
        out.append('')
        for i, it in enumerate(f['issues'], 1):
            out.append('%d. %s' % (i, it))
        out.append('')
    out.append('## \u4e09\u3001\u5355\u4f4d\u7ecf\u6d4e\u6a21\u578b')
    out.append('')
    if ue['state'] == '\u53c2\u6570\u4e0d\u5168':
        out.append('\u53c2\u6570\u4e0d\u5168\uff0c\u65e0\u6cd5\u8ba1\u7b97\u3002\u81f3\u5c11\u9700\u8981\u5ba2\u5355\u4ef7\u3001\u53d8\u52a8\u6210\u672c\u3001CAC\u3001\u590d\u8d2d\u6b21\u6570\u4e0e\u6708\u6d41\u5931\u7387\u3002')
    else:
        out.append('- \u5ba2\u5355\u4ef7\uff1a%s' % ue['arppu'])
        out.append('- \u53d8\u52a8\u6210\u672c\uff1a%s' % ue['variable_cost'])
        out.append('- \u5355\u5ba2\u6237\u6bdb\u5229\uff1a%s\uff08\u6bdb\u5229\u7387 %s%%\uff09'
                   % (ue['gross_profit'], ue['margin']))
        out.append('- CAC\uff1a%s\uff08\u542b\u6e20\u9053\u8d39\u3001\u9500\u552e\u4eba\u529b\u4e0e\u5de5\u5177\u5206\u644a\uff09' % ue['cac'])
        if ue['ltv'] is not None:
            out.append('- LTV\uff1a%s' % ue['ltv'])
        if ue['ltv_cac'] is not None:
            out.append('- LTV/CAC\uff1a%.2f\uff08\u5224\u5b9a\u7ebf %.0f\uff09' % (ue['ltv_cac'], LTVCAC_MIN))
        if ue['payback_months'] is not None:
            out.append('- \u56de\u672c\u5468\u671f\uff1a%.1f \u4e2a\u6708\uff08\u8b66\u6212 %d \u4e2a\u6708\uff09'
                       % (ue['payback_months'], PAYBACK_WARN))
    out.append('')
    if ue_issues:
        for i, it in enumerate(ue_issues, 1):
            out.append('%d. %s' % (i, it))
        out.append('')
    out.append('## \u56db\u3001\u6570\u636e\u6765\u6e90\u6807\u6ce8')
    out.append('')
    if not src_rows:
        out.append('\u672a\u5217\u6570\u636e\u6765\u6e90\u3002BP \u4e2d\u6bcf\u4e2a\u5f15\u7528\u7684\u5916\u90e8\u6570\u5b57\u90fd\u5e94\u6807\u6ce8\u6765\u6e90\u540d\u4e0e\u65f6\u70b9\u3002')
    else:
        out.append('| \u6570\u636e\u9879 | \u6765\u6e90 | \u65f6\u70b9 | \u5224\u5b9a |')
        out.append('|---|---|---|---|')
        for r in src_rows:
            out.append('| %s | %s | %s | %s |' % (
                r['item'], r['source'], r['year'],
                'OK' if r['marked'] else '\u672a\u6807\u6ce8'))
    out.append('')
    out.append('## \u4e94\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if missing:
        idx += 1
        out.append('%d. \u7f3a\u5931\u7ae0\u8282\uff1a%s\u3002\u8865\u9f50\u540e\u9010\u7ae0\u5bf9\u7167\u5fc5\u7b54\u95ee\u9898\u9010\u6761\u56de\u7b54\u3002' % (idx, '\u3001'.join(missing)))
    elif cov < SECTION_RED:
        idx += 1
        out.append('%d. \u7ae0\u8282\u5b8c\u6574\u7387 %.1f%% \u4f4e\u4e8e\u7ea2\u7ebf\u3002' % (idx, cov))
    if ans_rate < ANSWER_RED:
        idx += 1
        out.append('%d. \u5fc5\u7b54\u9898\u56de\u7b54\u7387 %.1f%% \u504f\u4f4e\uff1a\u672a\u7b54\u7684\u8981\u5199\u660e\u539f\u56e0\uff0c\u4e0d\u8981\u7559\u7a7a\u3002' % (idx, ans_rate))
    if f['issues']:
        idx += 1
        out.append('%d. \u8d22\u52a1\u5f02\u5e38 %d \u5904\uff1a\u5148\u6838\u4e09\u6761\u52fe\u7a3d\u5173\u7cfb\u3002\u52fe\u7a3d\u4e0d\u4e0a\u7684\u8d22\u52a1\u8868\u4e0d\u80fd\u7528\u4e8e\u5bf9\u5916\u6c9f\u901a\u3002'
                   % (idx, len(f['issues'])))
    if f['jumps']:
        idx += 1
        out.append('%d. \u6536\u5165\u589e\u901f\u8df3\u53d8 %d \u5904\uff1a\u62c6\u6210\u300c\u7528\u6237\u6570 \u00d7 \u4ed8\u8d39\u7387 \u00d7 \u5ba2\u5355\u4ef7\u300d\uff0c\u6bcf\u9879\u7ed9\u589e\u957f\u4f9d\u636e\u3002'
                   % (idx, len(f['jumps'])))
    if ue_issues:
        idx += 1
        out.append('%d. \u5355\u4f4d\u7ecf\u6d4e\u95ee\u9898 %d \u5904\uff1a\u6295\u8d44\u4eba\u4e0d\u770b\u5229\u6da6\u8868\uff0c\u5148\u770b UE\u3002CAC \u5fc5\u987b\u542b\u9500\u552e\u4eba\u529b\u4e0e\u5de5\u5177\u5206\u644a\u3002'
                   % (idx, len(ue_issues)))
    unmarked = [r['item'] for r in src_rows if not r['marked']]
    if unmarked:
        idx += 1
        out.append('%d. \u672a\u6807\u6ce8\u6765\u6e90\u7684\u6570\u636e\uff1a%s\u3002\u8ffd\u95ee\u4f1a\u76f4\u63a5\u5230\u300c\u54ea\u4e2a\u6765\u6e90\u3001\u4ec0\u4e48\u65f6\u70b9\u300d\u3002'
                   % (idx, '\u3001'.join(unmarked)))
    if len(risks) < RISK_MIN:
        idx += 1
        out.append('%d. \u98ce\u9669\u62ab\u9732\u4ec5 %d \u6761\uff1a\u81f3\u5c11\u5217 %d \u6761\u771f\u5b9e\u98ce\u9669\u5e76\u914d\u5e94\u5bf9\uff0c\u8bf4\u300c\u6ca1\u6709\u98ce\u9669\u300d\u901a\u5e38\u8bf4\u660e\u6ca1\u60f3\u6e05\u695a\u3002'
                   % (idx, len(risks), RISK_MIN))
    if not idx:
        out.append('\u7ae0\u8282\u3001\u8d22\u52a1\u3001\u5355\u4f4d\u7ecf\u6d4e\u4e0e\u6570\u636e\u6765\u6e90\u5747\u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\u3002'
                   '\u5bf9\u5916\u62ab\u9732\u4e49\u52a1\u76f8\u5173\u5185\u5bb9\u8bf7\u7531\u4e13\u4e1a\u673a\u6784\u5ba1\u6838\u3002')
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

    full_secs = [{'module': m, 'present': True, 'answered_questions': 5,
                  'total_questions': 5} for m in MODULES]
    r = build({'sections': full_secs}, 'json')
    chk(r['section_coverage'] == 100.0, '\u516b\u90e8\u5206\u9f50\u5168\u5e94\u4e3a 100')
    chk(r['missing_modules'] == [], '\u9f50\u5168\u65f6\u4e0d\u5e94\u6709\u7f3a\u5931')
    chk(r['answer_rate'] == 100.0, '\u5168\u7b54\u56de\u7b54\u7387\u5e94\u4e3a 100')

    partial = [{'module': m, 'present': True, 'answered_questions': 2,
                'total_questions': 4} for m in CORE_MODULES]
    r = build({'sections': partial}, 'json')
    chk(r['answer_rate'] == 50.0, '\u534a\u7b54\u56de\u7b54\u7387\u5e94\u4e3a 50')
    chk('\u56e2\u961f' in r['missing_modules'] and '\u878d\u8d44' in r['missing_modules'],
        '\u672a\u63d0\u4f9b\u7684\u56e2\u961f\u4e0e\u878d\u8d44\u5e94\u5217\u5165\u7f3a\u5931')

    r = build({'sections': []}, 'json')
    chk(r['section_coverage'] == 0.0, '\u7a7a\u7ae0\u8282\u5217\u8868\u5b8c\u6574\u7387\u4e3a 0')
    chk(len(r['missing_modules']) == 8, '\u7a7a\u5217\u8868\u5e94\u7f3a 8 \u7ae0')

    over = [{'module': 'problem', 'present': True, 'answered_questions': 9,
             'total_questions': 4}]
    r = build({'sections': over}, 'json')
    chk(r['answer_rate'] == 100.0, '\u7b54\u6570\u8d85\u5fc5\u7b54\u6570\u5e94\u88ab\u622a\u5230 100')

    good_fin = {
        'years': [2026, 2027, 2028],
        'revenue': [1000, 2000, 3000],
        'cost': [800, 1500, 2100],
        'gross_profit': [200, 500, 900],
        'rd_expense': [300, 400, 500],
        'sales_expense': [200, 250, 300],
        'admin_expense': [100, 100, 150],
        'op_profit': [-400, -250, -50],
        'begin_cash': [800, 400, 150],
        'end_cash': [400, 150, 100],
        'op_cash_flow': [-400, -250, -50],
    }
    r = build({'finance': good_fin}, 'json')
    chk(r['finance_rate'] == 100.0, '\u4e09\u8868\u52fe\u7a3d\u6b63\u786e\u5e94\u4e3a 100')
    chk(r['finance_issues'] == [], '\u52fe\u7a3d\u6b63\u786e\u4e0d\u5e94\u6709\u5f02\u5e38')

    bad_gp = dict(good_fin)
    bad_gp['gross_profit'] = [999, 500, 900]
    r = build({'finance': bad_gp}, 'json')
    chk(r['finance_rate'] < 100.0, '\u6bdb\u5229\u52fe\u7a3d\u9519\u5e94\u62c9\u4f4e\u901a\u8fc7\u7387')
    chk(any('\u6bdb\u5229\u52fe\u7a3d\u4e0d\u7b26' in i for i in r['finance_issues']), '\u5e94\u63d0\u793a\u6bdb\u5229\u52fe\u7a3d\u4e0d\u7b26')

    bad_op = dict(good_fin)
    bad_op['op_profit'] = [-400, 999, -50]
    r = build({'finance': bad_op}, 'json')
    chk(any('\u7ecf\u8425\u5229\u6da6\u52fe\u7a3d\u4e0d\u7b26' in i for i in r['finance_issues']),
        '\u5e94\u63d0\u793a\u7ecf\u8425\u5229\u6da6\u52fe\u7a3d\u4e0d\u7b26')

    bad_cash = dict(good_fin)
    bad_cash['end_cash'] = [400, 150, 9999]
    r = build({'finance': bad_cash}, 'json')
    chk(any('\u671f\u672b\u73b0\u91d1\u52fe\u7a3d\u4e0d\u7b26' in i for i in r['finance_issues']),
        '\u5e94\u63d0\u793a\u671f\u672b\u73b0\u91d1\u52fe\u7a3d\u4e0d\u7b26')

    missing_sub = {'years': [2026], 'revenue': [1000],
                   'cost': [800], 'gross_profit': [200]}
    r = build({'finance': missing_sub}, 'json')
    chk(r['finance_rate'] < 100.0, '\u7f3a\u79d1\u76ee\u5e94\u65e0\u6cd5\u5168\u901a\u8fc7')

    jump = dict(good_fin)
    jump['revenue'] = [1000, 8000, 30000]
    jump['cost'] = [800, 4800, 21000]
    jump['gross_profit'] = [200, 3200, 9000]
    jump['rd_expense'] = [300, 1600, 500]
    jump['sales_expense'] = [200, 1800, 300]
    jump['admin_expense'] = [100, 400, 150]
    jump['op_profit'] = [-400, -600, 8050]
    jump['begin_cash'] = [800, 400, 150]
    jump['end_cash'] = [400, 150, 100]
    jump['op_cash_flow'] = [-400, -250, -50]
    r = build({'finance': jump}, 'json')
    chk(len(r['finance']['jumps'] if 'finance' in r else []) >= 0, '\u8df3\u53d8\u68c0\u6d4b\u4e0d\u5e94\u62a5\u9519')
    chk(any('\u589e\u957f' in i for i in r['finance_issues']), '8 \u500d\u589e\u901f\u5e94\u63d0\u793a\u62c6\u89e3\u8def\u5f84')

    ue_ok = {'ue': {'arppu': 200, 'variable_cost': 80, 'cac': 150,
                    'repeat_times': 4, 'churn_monthly': 0.08}}
    r = build(ue_ok, 'json')
    chk(r['ue']['gross_profit'] == 120, '\u5ba2\u5355\u4ef7\u51cf\u53d8\u52a8\u6210\u672c\u5e94\u7b49\u4e8e\u6bdb\u5229')
    chk(r['ue']['margin'] == 60.0, '\u6bdb\u5229\u7387\u5e94\u4e3a 60')
    chk(r['ue']['ltv'] == 480, 'LTV \u5e94\u4e3a\u6bdb\u5229\u4e58\u590d\u8d2d\u6b21\u6570')
    chk(r['ue']['ltv_cac'] == 3.2, 'LTV/CAC \u5e94\u7ea6\u4e3a 3.2')
    chk(r['ue']['state'] == '\u53ef\u8ba1\u7b97', '\u53c2\u6570\u9f50\u5168\u72b6\u6001\u5e94\u4e3a\u53ef\u8ba1\u7b97')

    ue_neg = {'ue': {'arppu': 50, 'variable_cost': 80, 'cac': 150,
                     'repeat_times': 4, 'churn_monthly': 0.08}}
    r = build(ue_neg, 'json')
    chk(r['ue']['state'] == '\u6bdb\u5229\u4e3a\u8d1f', '\u6bdb\u5229\u4e3a\u8d1f\u5e94\u5355\u72ec\u5224\u5b9a')
    chk(r['ue']['ltv'] is None, '\u6bdb\u5229\u4e3a\u8d1f\u65f6\u4e0d\u5e94\u7ed9 LTV')

    ue_low = {'ue': {'arppu': 100, 'variable_cost': 80, 'cac': 300,
                     'repeat_times': 2, 'churn_monthly': 0.1}}
    r = build(ue_low, 'json')
    chk(r['ue']['ltv_cac'] < LTVCAC_MIN, 'LTV/CAC \u5e94\u4f4e\u4e8e\u5224\u5b9a\u7ebf')
    chk(any('LTV/CAC' in i for i in r['ue_issues']), '\u5e94\u63d0\u793a LTV/CAC \u672a\u8dd1\u901a')
    chk(r['ue']['payback_months'] > PAYBACK_WARN, '\u56de\u672c\u5468\u671f\u5e94\u8d85\u8b66\u6212')

    ue_part = {'ue': {'arppu': 200, 'variable_cost': 80}}
    r = build(ue_part, 'json')
    chk(r['ue']['ltv'] is None, '\u7f3a\u590d\u8d2d\u6b21\u6570\u4e0d\u5e94\u7ed9 LTV')
    chk(any('\u590d\u8d2d\u6b21\u6570' in i for i in r['ue_issues']), '\u5e94\u63d0\u793a\u7f3a\u590d\u8d2d\u6b21\u6570')
    chk(any('\u6708\u6d41\u5931\u7387' in i for i in r['ue_issues']), '\u5e94\u63d0\u793a\u7f3a\u6708\u6d41\u5931\u7387')

    r = build({'ue': {}}, 'json')
    chk(r['ue']['state'] == '\u53c2\u6570\u4e0d\u5168', '\u7a7a UE \u5e94\u5224\u53c2\u6570\u4e0d\u5168')

    src_ok = {'data_sources': [{'item': '\u5e02\u573a\u89c4\u6a21', 'source': '\u67d0\u62a5\u544a',
                                'year': '2025'}]}
    r = build(src_ok, 'json')
    chk(r['source_rate'] == 100.0, '\u6807\u6ce8\u5b8c\u6574\u6765\u6e90\u7387\u4e3a 100')
    chk(r['unmarked_sources'] == [], '\u6807\u6ce8\u5b8c\u6574\u4e0d\u5e94\u6709\u672a\u6807\u6ce8')

    src_bad = {'data_sources': [{'item': '\u5e02\u573a\u89c4\u6a21', 'source': '', 'year': ''},
                                {'item': '\u7528\u6237\u6570', 'source': '\u540e\u53f0', 'year': '2026'}]}
    r = build(src_bad, 'json')
    chk(r['source_rate'] == 50.0, '\u4e00\u534a\u672a\u6807\u6ce8\u5e94\u4e3a 50')
    chk(r['unmarked_sources'] == ['\u5e02\u573a\u89c4\u6a21'], '\u672a\u6807\u6ce8\u9879\u5e94\u88ab\u5217\u51fa')

    r = build({'risks': ['a', 'b', 'c']}, 'json')
    chk(r['risk_count'] == 3, '\u98ce\u9669\u6761\u6570\u5e94\u4e3a 3')
    r = build({}, 'json')
    chk(r['risk_count'] == 0, '\u672a\u586b\u98ce\u9669\u5e94\u8bb0 0')

    txt = build({'sections': full_secs, 'finance': good_fin,
                 'ue': ue_ok['ue'], 'data_sources': src_ok['data_sources'],
                 'risks': ['a', 'b', 'c']}, 'md')
    chk('\u8d22\u52a1\u52fe\u7a3d\u6821\u9a8c' in txt, 'md \u5e94\u542b\u52fe\u7a3d\u6821\u9a8c\u6bb5')
    chk('\u5355\u4f4d\u7ecf\u6d4e\u6a21\u578b' in txt, 'md \u5e94\u542b\u5355\u4f4d\u7ecf\u6d4e\u6bb5')
    chk('\u6570\u636e\u6765\u6e90\u6807\u6ce8' in txt, 'md \u5e94\u542b\u6765\u6e90\u6807\u6ce8\u6bb5')
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
    ap = argparse.ArgumentParser(description='BP \u64b0\u5199\u4e0e\u6295\u8d44\u4eba\u5173\u6ce8\u70b9\u6838\u67e5')
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