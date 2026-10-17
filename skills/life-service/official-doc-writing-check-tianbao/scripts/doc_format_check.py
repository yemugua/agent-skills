# -*- coding: utf-8 -*-
"""\u516c\u6587\u683c\u5f0f\u8981\u7d20\u6838\u67e5\uff1a\u8981\u7d20\u5b8c\u6574\u7387\u3001\u6587\u79cd\u5339\u914d\u3001\u8d8a\u7ea7\u4e0e\u591a\u5934\u4e3b\u9001\u3001\u53e3\u8bed\u5316\u626b\u63cf\u3002

\u7528\u6cd5:
  python doc_format_check.py --file doc.json [--out result.md] [--format json]
  python doc_format_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

DOC_TYPES = ('\u901a\u77e5', '\u901a\u62a5', '\u62a5\u544a', '\u8bf7\u793a', '\u51fd', '\u7eaa\u8981', '\u610f\u89c1')
# \u5404\u6587\u79cd\u7684\u7ed3\u5c3e\u7528\u8bed\u767d\u540d\u5355\uff08\u6309\u6587\u79cd\u5206\u6bb5\uff0c\u5339\u914d\u4efb\u4e00\u5373\u53ef\uff09
CLOSINGS = {
    '\u62a5\u544a': ('\u7279\u6b64\u62a5\u544a',),
    '\u8bf7\u793a': ('\u59a5\u5426', '\u8bf7\u6279\u793a', '\u8bf7\u4e88\u6279\u590d', '\u8bf7\u6279\u590d'),
    '\u901a\u77e5': ('\u8bf7\u9075\u7167\u6267\u884c', '\u8bf7\u8ba4\u771f\u8d2f\u5f7b\u6267\u884c', '\u8bf7\u6293\u597d', '\u671b\u5468\u77e5'),
    '\u901a\u62a5': ('\u7279\u6b64\u901a\u62a5',),
    '\u51fd': ('\u8bf7\u4e88\u652f\u6301', '\u4e13\u6b64\u51fd\u8fbe', '\u8bf7\u4e88\u590d\u51fd', '\u8bf7\u56de\u590d'),
}
# \u9700\u8981\u56de\u590d\u7684\u6587\u79cd\uff08\u5fc5\u987b\u5199\u7ed3\u5c3e\u8bf7\u6c42\u8bed\uff09
NEED_REPLY = ('\u8bf7\u793a',)

ELEMENT_KEYS = ('title', 'main_recipient', 'body', 'attachment_note',
                'issuer_signature', 'written_date', 'cc', 'printer')
ELEMENT_CN = {
    'title': '\u6807\u9898',
    'main_recipient': '\u4e3b\u9001\u673a\u5173',
    'body': '\u6b63\u6587',
    'attachment_note': '\u9644\u4ef6\u8bf4\u660e',
    'issuer_signature': '\u53d1\u6587\u673a\u5173\u7f72\u540d',
    'written_date': '\u6210\u6587\u65e5\u671f',
    'cc': '\u6284\u9001\u673a\u5173',
    'printer': '\u5370\u53d1\u673a\u5173\u4e0e\u5370\u53d1\u65e5\u671f',
}
# \u5370\u53d1\u673a\u5173\u4ec5\u5728\u9700\u5370\u53d1\u65f6\u5fc5\u5907
OPTIONAL = ('printer',)

COVERAGE_RED = 85.0

# \u53e3\u8bed\u5316 / \u4e0d\u89c4\u8303\u7528\u8bed
COLLOQUIAL = ('\u5927\u6982', '\u5dee\u4e0d\u591a', '\u57fa\u672c\u4e0a', '\u641e\u4e00\u641e', '\u5f04\u4e00\u4e0b', '\u5e72\u5417',
              '\u5927\u5bb6\u90fd\u77e5\u9053', '\u8bf4\u5b9e\u8bdd', '\u5176\u5b9e', '\u633a\u91cd\u8981', '\u7279\u522b\u91cd\u8981',
              '\u5c3d\u5feb', '\u6293\u7d27', '\u52a0\u6cb9', '\u641e\u5b9a', '\u6293\u624b', '\u75db\u70b9')
# \u65e0\u7ea6\u675f\u529b/\u6307\u4ee3\u4e0d\u6e05
VAGUE = ('\u6709\u5173\u90e8\u95e8', '\u6709\u5173\u65b9\u9762', '\u6709\u5173\u5355\u4f4d', '\u67d0\u5355\u4f4d', '\u67d0\u67d0')
# \u4e3b\u89c2\u8868\u8ff0
SUBJECTIVE = ('\u6211\u8ba4\u4e3a', '\u6211\u4e2a\u4eba\u89c9\u5f97', '\u6211\u89c9\u5f97', '\u4f9d\u6211\u770b', '\u5728\u6211\u770b\u6765')
# \u611f\u53f9/\u53cd\u95ee
EMOTION = ('\u5427\uff01', '\u5462\uff01', '\u554a\uff01', '\uff1f', '\uff01')

# \u62a5\u544a\u5939\u5e26\u8bf7\u793a\u7528\u8bed
APPLY_IN_REPORT = ('\u8bf7\u6279\u793a', '\u8bf7\u6279\u590d', '\u8bf7\u4e88\u6279\u590d', '\u59a5\u5426', '\u6073\u8bf7',
                   '\u6073\u8bf7\u6279\u51c6', '\u671b\u6279\u51c6', '\u7533\u8bf7\u7acb\u9879', '\u8bf7\u793a\u5982\u4e0b')


def load(text=None, path=None):
    if text:
        return json.loads(text)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def element_check(data):
    els = data.get('elements') or {}
    rows = []
    miss = []
    for k in ELEMENT_KEYS:
        v = bool(els.get(k))
        if k not in OPTIONAL and not v:
            miss.append(ELEMENT_CN[k])
        rows.append({'key': k, 'name': ELEMENT_CN[k], 'present': v,
                     'required': k not in OPTIONAL})
    required = [r for r in rows if r['required']]
    rate = 0.0
    if required:
        rate = round(sum(1 for r in required if r['present']) * 100.0
                     / len(required), 1)
    return rows, miss, rate


def type_check(data):
    """\u6587\u79cd\u4e0e\u8981\u7d20/\u7ed3\u5c3e/\u4e00\u6587\u4e00\u4e8b/\u5939\u5e26\u8bf7\u793a\u3002"""
    dt = (data.get('doc_type') or '').strip()
    name = (data.get('doc_name') or '').strip()
    closing = (data.get('closing') or '').strip()
    issues = []

    if not dt:
        issues.append('\u672a\u586b\u5199\u6587\u79cd\uff0c\u9700\u5148\u6309\u300c\u8981\u5bf9\u65b9\u505a\u4ec0\u4e48 / \u544a\u77e5\u53d1\u751f\u4e86\u4ec0\u4e48\u300d\u5224\u5b9a\u6587\u79cd')
    elif dt not in DOC_TYPES:
        issues.append('\u6587\u79cd\u300c%s\u300d\u4e0d\u5728\u89c4\u8303\u6587\u79cd\u8303\u56f4\u5185\uff08%s\uff09'
                      % (dt, '\u3001'.join(DOC_TYPES)))
    if dt and name and dt not in name:
        issues.append('\u6807\u9898\u672b\u5c3e\u672a\u51fa\u73b0\u6587\u79cd\u300c%s\u300d\uff0c\u6807\u9898\u4e0e\u6587\u79cd\u58f0\u660e\u4e0d\u4e00\u81f4' % dt)
    if dt in CLOSINGS:
        if not closing:
            issues.append('%s \u7c7b\u6587\u4ef6\u7f3a\u5c11\u7ed3\u5c3e\u7528\u8bed' % dt)
        elif not any(c in closing for c in CLOSINGS[dt]):
            issues.append('\u7ed3\u5c3e\u7528\u8bed\u4e0e\u6587\u79cd\u4e0d\u5339\u914d\uff1a%s \u7c7b\u6587\u4ef6\u5efa\u8bae\u7528 %s'
                          % (dt, '\u3001'.join(CLOSINGS[dt])))
    elif dt and not closing:
        issues.append('\u7f3a\u5c11\u7ed3\u5c3e\u7528\u8bed')
    if dt == '\u62a5\u544a' and not data.get('one_issue_only'):
        pass
    if dt == '\u8bf7\u793a':
        if not data.get('one_issue_only'):
            issues.append('\u8bf7\u793a\u5fc5\u987b\u4e00\u6587\u4e00\u4e8b')
    if dt == '\u62a5\u544a':
        hits = [w for w in APPLY_IN_REPORT if w in closing or w in (data.get('text_body') or '')]
        if hits:
            issues.append('\u62a5\u544a\u4e2d\u51fa\u73b0\u8bf7\u793a\u7528\u8bed\u300c%s\u300d\uff0c\u8bf7\u793a\u4e8b\u9879\u5e94\u53e6\u884c\u6210\u6587' % hits[0])
    return dt, issues


def recipient_check(data):
    rs = data.get('main_recipients') or []
    issues = []
    if not rs:
        issues.append('\u4e3b\u9001\u673a\u5173\u4e3a\u7a7a')
    elif len(rs) > 1:
        issues.append('\u591a\u5934\u4e3b\u9001\uff1a\u4e0a\u7ea7\u5bf9\u4e0b\u7ea7\u4e00\u822c\u53ea\u5199\u4e00\u4e2a\u4e3b\u9001\u673a\u5173\uff0c\u5176\u4f59\u6539\u4e3a\u6284\u9001')
    for r in rs:
        if r in VAGUE:
            issues.append('\u4e3b\u9001\u673a\u5173\u4f7f\u7528\u300c%s\u300d\uff0c\u5e94\u5199\u5177\u4f53\u673a\u5173\u540d\u79f0' % r)
    if data.get('hierarchy_ok') is False:
        issues.append('\u884c\u6587\u5173\u7cfb\u8d8a\u7ea7\uff1a\u5e94\u6309\u96b6\u5c5e\u5173\u7cfb\u9010\u7ea7\u884c\u6587')
    return rs, issues


def text_scan(data):
    body = data.get('text_body') or ''
    hits = []
    for w in COLLOQUIAL:
        if w in body:
            hits.append({'type': '\u53e3\u8bed\u5316', 'word': w,
                         'fix': _fix_colloquial(w)})
    for w in VAGUE:
        if w in body:
            hits.append({'type': '\u6307\u4ee3\u4e0d\u6e05', 'word': w,
                         'fix': '\u6539\u4e3a\u5177\u4f53\u673a\u5173\u540d\u79f0'})
    for w in SUBJECTIVE:
        if w in body:
            hits.append({'type': '\u4e3b\u89c2\u8868\u8ff0', 'word': w,
                         'fix': '\u5220\u9664\uff0c\u6539\u7528\u5ba2\u89c2\u8868\u8ff0'})
    for w in EMOTION:
        if w in body:
            hits.append({'type': '\u60c5\u7eea\u6807\u70b9', 'word': w,
                         'fix': '\u5220\u9664\u611f\u53f9\u53f7\u4e0e\u95ee\u53f7\uff0c\u6539\u4e3a\u9648\u8ff0\u53e5'})
    return hits


def _fix_colloquial(w):
    m = {'\u5927\u6982': '\u7ea6', '\u5dee\u4e0d\u591a': '\u7ea6', '\u57fa\u672c\u4e0a': '\u57fa\u672c\u5b8c\u6210',
         '\u5c3d\u5feb': '\u4e8e X \u6708 X \u65e5\u524d', '\u6293\u7d27': '\u4e8e X \u6708 X \u65e5\u524d',
         '\u641e\u4e00\u641e': '\u5f00\u5c55', '\u5f04\u4e00\u4e0b': '\u529e\u7406', '\u5e72\u5417': '\uff08\u5220\u9664\uff09',
         '\u5927\u5bb6\u90fd\u77e5\u9053': '\uff08\u5220\u9664\uff09', '\u8bf4\u5b9e\u8bdd': '\uff08\u5220\u9664\uff09', '\u5176\u5b9e': '\uff08\u5220\u9664\uff09',
         '\u633a\u91cd\u8981': '\uff08\u5220\u9664\uff0c\u7528\u5177\u4f53\u8981\u6c42\u4ee3\u66ff\uff09', '\u7279\u522b\u91cd\u8981': '\uff08\u5220\u9664\uff0c\u7528\u5177\u4f53\u8981\u6c42\u4ee3\u66ff\uff09',
         '\u52a0\u6cb9': '\uff08\u5220\u9664\uff09', '\u641e\u5b9a': '\u5b8c\u6210', '\u6293\u624b': '\uff08\u6539\u4e3a\u5177\u4f53\u5de5\u4f5c\u63aa\u65bd\uff09',
         '\u75db\u70b9': '\uff08\u6539\u4e3a\u5177\u4f53\u95ee\u9898\uff09'}
    return m.get(w, '\uff08\u5220\u9664\uff09')


def build(data, fmt='md'):
    title = data.get('title') or '\u516c\u6587\u683c\u5f0f\u4f53\u68c0'
    rows, miss, rate = element_check(data)
    dt, type_issues = type_check(data)
    rs, rec_issues = recipient_check(data)
    hits = text_scan(data)

    if fmt == 'json':
        return {'title': title, 'doc_type': dt,
                'element_coverage': rate, 'missing_elements': miss,
                'type_issues': type_issues, 'recipient_issues': rec_issues,
                'main_recipients': rs, 'text_hits': hits,
                'text_hit_count': len(hits)}

    out = []
    out.append('# %s' % title)
    out.append('')
    out.append('- \u6587\u79cd\uff1a%s' % (dt or '\uff08\u672a\u586b\uff09'))
    out.append('- \u6807\u9898\uff1a%s' % (data.get('doc_name') or '\uff08\u672a\u586b\uff09'))
    out.append('- \u4e3b\u9001\u673a\u5173\uff1a%s' % ('\u3001'.join(rs) if rs else '\uff08\u672a\u586b\uff09'))
    out.append('- \u8981\u7d20\u5b8c\u6574\u7387\uff1a%.1f%%\uff08\u7ea2\u7ebf %.0f%%\uff0c\u5370\u53d1\u673a\u5173\u4e0d\u8ba1\u5165\u5fc5\u9700\u9879\uff09' % (rate, COVERAGE_RED))
    out.append('- \u7f3a\u5931\u8981\u7d20\uff1a%s' % ('\u3001'.join(miss) if miss else '\u65e0'))
    out.append('- \u53e3\u8bed\u5316\u4e0e\u4e0d\u89c4\u8303\u7528\u8bed\u547d\u4e2d\uff1a%d' % len(hits))
    out.append('')
    out.append('## \u4e00\u3001\u683c\u5f0f\u8981\u7d20\u6838\u5bf9')
    out.append('')
    out.append('| \u8981\u7d20 | \u662f\u5426\u5177\u5907 | \u662f\u5426\u5fc5\u9700 |')
    out.append('|---|---|---|')
    for r in rows:
        out.append('| %s | %s | %s |' % (r['name'],
                                        '\u662f' if r['present'] else '\u5426',
                                        '\u662f' if r['required'] else '\u5426\uff08\u6309\u9700\u5370\u53d1\uff09'))
    out.append('')
    out.append('## \u4e8c\u3001\u6587\u79cd\u4e0e\u884c\u6587\u95ee\u9898')
    out.append('')
    all_issues = type_issues + rec_issues
    if not all_issues:
        out.append('\u6587\u79cd\u3001\u7ed3\u5c3e\u7528\u8bed\u3001\u4e3b\u9001\u673a\u5173\u4e0e\u884c\u6587\u5173\u7cfb\u5747\u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\u3002')
    else:
        for i, it in enumerate(all_issues, 1):
            out.append('%d. %s' % (i, it))
    out.append('')
    out.append('## \u4e09\u3001\u53e3\u8bed\u5316\u4e0e\u4e0d\u89c4\u8303\u7528\u8bed')
    out.append('')
    if not hits:
        out.append('\u672a\u547d\u4e2d\u626b\u63cf\u8bcd\u8868\u4e2d\u7684\u4e0d\u89c4\u8303\u7528\u8bed\u3002\u4ecd\u9700\u4eba\u5de5\u68c0\u67e5\u6807\u70b9\u3001\u4e66\u540d\u53f7\u4e0e\u9519\u522b\u5b57\u3002')
    else:
        out.append('| \u7c7b\u578b | \u547d\u4e2d | \u6539\u6cd5 |')
        out.append('|---|---|---|')
        for h in hits:
            out.append('| %s | %s | %s |' % (h['type'], h['word'], h['fix']))
    out.append('')
    out.append('## \u56db\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if miss:
        idx += 1
        out.append('%d. \u7f3a\u5931\u683c\u5f0f\u8981\u7d20\uff1a%s\u3002\u5148\u8865\u9f50\u518d\u5b9a\u7a3f\u3002' % (idx, '\u3001'.join(miss)))
    elif rate < COVERAGE_RED:
        idx += 1
        out.append('%d. \u8981\u7d20\u5b8c\u6574\u7387 %.1f%% \u4f4e\u4e8e\u7ea2\u7ebf\uff1a\u9010\u9879\u6838\u5bf9\u540e\u8865\u9f50\u3002' % (idx, rate))
    if type_issues:
        idx += 1
        out.append('%d. \u6587\u79cd\u95ee\u9898 %d \u5904\uff1a\u6587\u79cd\u9009\u9519\u4f1a\u8ba9\u6240\u6709\u683c\u5f0f\u90fd\u5bf9\u4e0d\u4e0a\uff08\u8bf7\u793a\u5fc5\u987b\u4e00\u6587\u4e00\u4e8b\u3001'
                   '\u62a5\u544a\u4e0d\u80fd\u5939\u5e26\u8bf7\u793a\u4e8b\u9879\uff09\u3002' % (idx, len(type_issues)))
    if rec_issues:
        idx += 1
        out.append('%d. \u4e3b\u9001\u4e0e\u884c\u6587\u95ee\u9898 %d \u5904\uff1a\u8d8a\u7ea7\u4e0e\u591a\u5934\u4e3b\u9001\u662f\u88ab\u9000\u56de\u7684\u9ad8\u9891\u539f\u56e0\u3002'
                   % (idx, len(rec_issues)))
    if hits:
        idx += 1
        out.append('%d. \u53e3\u8bed\u5316\u4e0e\u4e0d\u89c4\u8303\u7528\u8bed %d \u5904\uff1a\u5148\u5220\u540e\u6539\uff0c\u5220\u4e0d\u6389\u7684\u8bcd\u7528\u5177\u4f53\u8868\u8ff0\u66ff\u6362\u3002'
                   % (idx, len(hits)))
    if not idx:
        out.append('\u8981\u7d20\u3001\u6587\u79cd\u4e0e\u7528\u8bed\u5747\u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\u3002\u5b57\u4f53\u5b57\u53f7\u4e0e\u7248\u5f0f\u7f16\u6392\u8bf7\u6309\u672c\u5355\u4f4d\u516c\u6587\u683c\u5f0f\u89c4\u5b9a\u6267\u884c\uff0c'
                   '\u5e76\u4ea4\u53d1\u6587\u673a\u5173\u5ba1\u6838\u3002')
    out.append('')
    out.append('> \u7248\u5934\u3001\u4e3b\u4f53\u3001\u7248\u8bb0\u7684\u5b57\u4f53\u5b57\u53f7\u4e0e\u5b57\u53f7\u7f16\u6392\uff0c\u4ee5\u73b0\u884c\u516c\u6587\u5904\u7406\u529e\u6cd5\u53ca\u672c\u5355\u4f4d\u516c\u6587\u683c\u5f0f\u89c4\u5b9a\u4e3a\u51c6\u3002')
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

    perfect = {
        'doc_type': '\u8bf7\u793a',
        'doc_name': '\u5173\u4e8e\u7533\u8bf7 XX \u4e13\u9879\u8d44\u91d1\u7684\u8bf7\u793a',
        'elements': {k: True for k in ELEMENT_KEYS},
        'main_recipients': ['\u5e02\u53d1\u6539\u59d4'],
        'hierarchy_ok': True,
        'closing': '\u59a5\u5426\uff0c\u8bf7\u6279\u793a',
        'one_issue_only': True,
        'text_body': '\u73b0\u7533\u8bf7\u4e13\u9879\u7ecf\u8d39 500 \u4e07\u5143\uff0c\u7528\u4e8e\u8bbe\u5907\u8d2d\u7f6e\u4e0e\u7ef4\u62a4\u3002',
    }
    r = build(perfect, 'json')
    chk(r['element_coverage'] == 100.0, '\u8981\u7d20\u9f50\u5168\u5e94\u4e3a 100%')
    chk(r['missing_elements'] == [], '\u8981\u7d20\u9f50\u5168\u4e0d\u5e94\u6709\u7f3a\u5931')
    chk(r['type_issues'] == [], '\u89c4\u8303\u8bf7\u793a\u4e0d\u5e94\u6709\u95ee\u9898')
    chk(r['recipient_issues'] == [], '\u5355\u4e00\u4e3b\u9001\u4e0d\u5e94\u6709\u95ee\u9898')
    chk(r['text_hit_count'] == 0, '\u89c4\u8303\u6587\u672c\u4e0d\u5e94\u547d\u4e2d')

    no_printer = dict(perfect)
    no_printer['elements'] = {k: True for k in ELEMENT_KEYS if k != 'printer'}
    r = build(no_printer, 'json')
    chk(r['element_coverage'] == 100.0, '\u5370\u53d1\u673a\u5173\u975e\u5fc5\u9700\uff0c\u7f3a\u5931\u4e0d\u5e94\u62c9\u4f4e\u5b8c\u6574\u7387')
    chk('\u5370\u53d1\u673a\u5173\u4e0e\u5370\u53d1\u65e5\u671f' not in r['missing_elements'], '\u5370\u53d1\u673a\u5173\u7f3a\u5931\u4e0d\u7b97\u7ea2\u7ebf\u7f3a\u5931')

    no_cc = dict(perfect)
    no_cc['elements'] = {k: True for k in ELEMENT_KEYS if k != 'cc'}
    r = build(no_cc, 'json')
    chk(abs(r['element_coverage'] - (100.0 * 6 / 7)) < 0.05, '\u7f3a\u6284\u9001\u5e94\u6309 7 \u9879\u5fc5\u9700\u8981\u7d20\u6298\u7b97')

    multi = dict(perfect)
    multi['main_recipients'] = ['\u5e02\u53d1\u6539\u59d4', '\u5e02\u8d22\u653f\u5c40', '\u5e02\u4f4f\u5efa\u5c40']
    r = build(multi, 'json')
    chk(len(r['recipient_issues']) == 1, '\u591a\u5934\u4e3b\u9001\u5e94\u8bb0 1 \u6761')
    chk('\u591a\u5934\u4e3b\u9001' in r['recipient_issues'][0], '\u5e94\u63d0\u793a\u591a\u5934\u4e3b\u9001')

    vg = dict(perfect)
    vg['main_recipients'] = ['\u6709\u5173\u90e8\u95e8']
    r = build(vg, 'json')
    chk(any('\u6709\u5173\u90e8\u95e8' in i for i in r['recipient_issues']), '\u4e3b\u9001\u5199\u6709\u5173\u90e8\u95e8\u5e94\u63d0\u793a')

    empty_r = dict(perfect)
    empty_r['main_recipients'] = []
    r = build(empty_r, 'json')
    chk(any('\u4e3b\u9001\u673a\u5173\u4e3a\u7a7a' in i for i in r['recipient_issues']), '\u7a7a\u4e3b\u9001\u5e94\u63d0\u793a')

    skip = dict(perfect)
    skip['hierarchy_ok'] = False
    r = build(skip, 'json')
    chk(any('\u8d8a\u7ea7' in i for i in r['recipient_issues']), '\u884c\u6587\u5173\u7cfb\u5f02\u5e38\u5e94\u63d0\u793a\u8d8a\u7ea7')

    rep = dict(perfect)
    rep['doc_type'] = '\u62a5\u544a'
    rep['doc_name'] = '\u5173\u4e8e\u6709\u5173\u60c5\u51b5\u7684\u62a5\u544a'
    rep['closing'] = '\u7279\u6b64\u62a5\u544a'
    r = build(rep, 'json')
    chk(r['type_issues'] == [], '\u89c4\u8303\u62a5\u544a\u4e0d\u5e94\u6709\u95ee\u9898')

    rep_bad = dict(rep)
    rep_bad['closing'] = '\u4ee5\u4e0a\u60c5\u51b5\uff0c\u8bf7\u6279\u793a\u3002'
    r = build(rep_bad, 'json')
    chk(len(r['type_issues']) >= 1, '\u62a5\u544a\u7528\u8bf7\u793a\u7ed3\u5c3e\u5e94\u62a5\u9519')
    chk(any('\u5939\u5e26' in i or '\u4e0d\u5339\u914d' in i for i in r['type_issues']), '\u5e94\u63d0\u793a\u5939\u5e26\u6216\u4e0d\u5339\u914d')

    multi_issue = dict(perfect)
    multi_issue['one_issue_only'] = False
    r = build(multi_issue, 'json')
    chk(any('\u4e00\u6587\u4e00\u4e8b' in i for i in r['type_issues']), '\u8bf7\u793a\u975e\u4e00\u6587\u4e00\u4e8b\u5e94\u63d0\u793a')

    wrong_title = dict(perfect)
    wrong_title['doc_name'] = '\u5173\u4e8e\u7533\u8bf7\u8d44\u91d1\u7684\u62a5\u544a'
    r = build(wrong_title, 'json')
    chk(any('\u6807\u9898' in i for i in r['type_issues']), '\u6807\u9898\u6587\u79cd\u4e0d\u4e00\u81f4\u5e94\u63d0\u793a')

    bad_type = dict(perfect)
    bad_type['doc_type'] = '\u901a\u62a5\u51fd'
    r = build(bad_type, 'json')
    chk(any('\u4e0d\u5728\u89c4\u8303\u6587\u79cd\u8303\u56f4' in i for i in r['type_issues']), '\u751f\u9020\u6587\u79cd\u5e94\u63d0\u793a')

    no_close = dict(perfect)
    no_close['closing'] = ''
    r = build(no_close, 'json')
    chk(any('\u7f3a\u5c11\u7ed3\u5c3e\u7528\u8bed' in i for i in r['type_issues']), '\u7f3a\u7ed3\u5c3e\u7528\u8bed\u5e94\u63d0\u793a')

    tone = dict(perfect)
    tone['text_body'] = '\u8fd9\u4e2a\u4e8b\u5927\u6982\u80fd\u884c\uff0c\u8bf7\u5c3d\u5feb\u6293\u7d27\uff0c\u6211\u89c9\u5f97\u633a\u91cd\u8981\u7684\uff01'
    r = build(tone, 'json')
    kinds = set(h['type'] for h in r['text_hits'])
    chk('\u53e3\u8bed\u5316' in kinds, '\u5e94\u547d\u4e2d\u53e3\u8bed\u5316')
    chk('\u4e3b\u89c2\u8868\u8ff0' in kinds, '\u5e94\u547d\u4e2d\u4e3b\u89c2\u8868\u8ff0')
    chk('\u60c5\u7eea\u6807\u70b9' in kinds, '\u611f\u53f9\u53f7\u5e94\u547d\u4e2d\u60c5\u7eea\u6807\u70b9')
    w = [h for h in r['text_hits'] if h['word'] == '\u5c3d\u5feb']
    chk(w and 'X \u6708 X \u65e5\u524d' in w[0]['fix'], '\u5c3d\u5feb\u5e94\u7ed9\u51fa\u5177\u4f53\u65f6\u9650\u6539\u6cd5')

    empty = {}
    r = build(empty, 'json')
    chk(r['element_coverage'] == 0.0, '\u7a7a\u8f93\u5165\u5b8c\u6574\u7387\u4e3a 0')
    chk(len(r['type_issues']) >= 1, '\u7a7a\u8f93\u5165\u5e94\u62a5\u6587\u79cd\u95ee\u9898')

    txt = build(perfect, 'md')
    chk('\u683c\u5f0f\u8981\u7d20\u6838\u5bf9' in txt, 'md \u5e94\u542b\u8981\u7d20\u6838\u5bf9\u8868')
    chk('\u6574\u6539\u5efa\u8bae' in txt, 'md \u5e94\u542b\u6574\u6539\u5efa\u8bae')
    chk('\u672c\u5355\u4f4d\u516c\u6587\u683c\u5f0f\u89c4\u5b9a' in txt, 'md \u5e94\u542b\u683c\u5f0f\u4ee5\u89c4\u5b9a\u4e3a\u51c6\u7684\u63d0\u793a')

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
    ap = argparse.ArgumentParser(description='\u516c\u6587\u5199\u4f5c\u89c4\u8303\u4e0e\u5e38\u89c1\u9519\u8bef\u6838\u67e5')
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