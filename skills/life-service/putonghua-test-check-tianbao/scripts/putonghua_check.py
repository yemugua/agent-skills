#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u666e\u901a\u8bdd\u6c34\u5e73\u6d4b\u8bd5\u7b49\u7ea7\u5224\u5b9a\u3001\u7528\u9014\u8fbe\u6807\u6838\u67e5\u3001\u8bc1\u4e66\u6709\u6548\u671f\u4e0e\u590d\u6d4b\u95f4\u9694\u6d4b\u7b97\u3002

\u7528\u6cd5:
  python putonghua_check.py --score 86.5 --purpose teacher-chinese
  python putonghua_check.py --score 90.2 --purpose teacher-other --cert-date 2019-05-20
  python putonghua_check.py --score 88 --last-test 2026-08-01 --as-of 2026-10-08
  python putonghua_check.py --selftest

\u53c2\u6570:
  --score      \u6d4b\u8bd5\u603b\u5206\uff080~100\uff09
  --purpose    teacher-chinese \u8bed\u6587\u6559\u5e08 / teacher-other \u5176\u4ed6\u5b66\u79d1\u6559\u5e08 / broadcaster \u64ad\u97f3\u4e3b\u6301\u4eba /
               tour-guide \u5bfc\u6e38 / civil-service \u516c\u52a1\u5458\u4e8b\u4e1a\u5355\u4f4d / other \u672a\u6307\u5b9a
  --cert-date  \u5df2\u6709\u8bc1\u4e66\u53d6\u5f97\u65e5\u671f YYYY-MM-DD\uff0c\u7528\u4e8e\u6709\u6548\u671f\u5224\u65ad
  --last-test  \u4e0a\u6b21\u6d4b\u8bd5\u65e5\u671f YYYY-MM-DD\uff0c\u7528\u4e8e\u590d\u6d4b\u95f4\u9694\u6d4b\u7b97
  --interval   \u8981\u6c42\u7684\u590d\u6d4b\u95f4\u9694\u5929\u6570\uff0c\u9ed8\u8ba4 90\uff08\u5404\u5730\u4e0d\u540c\uff0c\u4ee5\u5c5e\u5730\u6d4b\u8bd5\u7ad9\u89c4\u5b9a\u4e3a\u51c6\uff09
  --as-of      \u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929
  --out        \u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84
  --format     md\uff08\u9ed8\u8ba4\uff09\u6216 json
  --selftest   \u8fd0\u884c\u5185\u7f6e\u81ea\u68c0
"""
import argparse
import json
import os
import re
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u5206\u6570\u4e0b\u9650 -> \u7b49\u7ea7
GRADES = [
    (97.0, '\u4e00\u7ea7\u7532\u7b49'),
    (92.0, '\u4e00\u7ea7\u4e59\u7b49'),
    (87.0, '\u4e8c\u7ea7\u7532\u7b49'),
    (80.0, '\u4e8c\u7ea7\u4e59\u7b49'),
    (70.0, '\u4e09\u7ea7\u7532\u7b49'),
    (60.0, '\u4e09\u7ea7\u4e59\u7b49'),
]
PURPOSE_REQ = {
    'teacher-chinese': (87.0, '\u4e8c\u7ea7\u7532\u7b49', '\u8bed\u6587\u6559\u5e08', '\u4ee5\u6559\u5e08\u8d44\u683c\u8ba4\u5b9a\u516c\u544a\u4e3a\u51c6'),
    'teacher-other': (80.0, '\u4e8c\u7ea7\u4e59\u7b49', '\u5176\u4ed6\u5b66\u79d1\u6559\u5e08', '\u4ee5\u6559\u5e08\u8d44\u683c\u8ba4\u5b9a\u516c\u544a\u4e3a\u51c6'),
    'broadcaster': (97.0, '\u4e00\u7ea7\u7532\u7b49', '\u64ad\u97f3\u5458\u3001\u4e3b\u6301\u4eba',
                    '\u56fd\u5bb6\u7ea7\u4e0e\u7701\u7ea7\u8981\u6c42\u4e0d\u540c\uff0c\u4ee5\u64ad\u51fa\u673a\u6784\u4e0e\u7ba1\u7406\u90e8\u95e8\u8981\u6c42\u4e3a\u51c6'),
    'tour-guide': (80.0, '\u4e8c\u7ea7\u4e59\u7b49', '\u5bfc\u6e38', '\u4ee5\u5f53\u5730\u6587\u65c5\u90e8\u95e8\u4e0e\u62a5\u8003\u8981\u6c42\u4e3a\u51c6'),
    'civil-service': (70.0, '\u4e09\u7ea7\u7532\u7b49', '\u516c\u52a1\u5458\u4e0e\u4e8b\u4e1a\u5355\u4f4d\u5c97\u4f4d',
                      '\u4ee5\u62db\u5f55\u516c\u544a\u4e3a\u51c6\uff0c\u65e0\u7edf\u4e00\u8981\u6c42'),
    'other': (None, '', '\u672a\u6307\u5b9a\u7528\u9014', ''),
}
CERT_LONG_VALID_FROM = date(2003, 6, 15)
DEFAULT_INTERVAL = 90
SUBJECT_WEIGHT = [
    ('\u8bfb\u5355\u97f3\u8282\u5b57\u8bcd 100 \u4e2a', 10),
    ('\u8bfb\u591a\u97f3\u8282\u8bcd\u8bed\u7ea6 50 \u4e2a', 20),
    ('\u6717\u8bfb\u77ed\u6587\u7ea6 400 \u97f3\u8282', 30),
    ('\u547d\u9898\u8bf4\u8bdd 3 \u5206\u949f', 40),
]


def parse_date(s):
    s = str(s).strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if not m:
        raise ValueError('\u65e5\u671f\u683c\u5f0f\u4e0d\u5bf9: %s' % s)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def fmt(d):
    return d.strftime('%Y-%m-%d')


def grade_of(score):
    if score is None:
        return None
    for floor, name in GRADES:
        if score >= floor:
            return name
    return '\u4e0d\u5165\u7ea7\uff0860 \u5206\u4ee5\u4e0b\u4e0d\u53d1\u8bc1\uff09'


def next_grade(score):
    """\u8fbe\u5230\u4e0a\u4e00\u4e2a\u7b49\u7ea7\u8fd8\u5dee\u591a\u5c11\u5206\u3002"""
    if score is None:
        return None, None
    cur = None
    for i, (floor, name) in enumerate(GRADES):
        if score >= floor:
            cur = i
            break
    if cur is None:
        return '\u4e09\u7ea7\u4e59\u7b49', 60.0
    if cur == 0:
        return None, None
    return GRADES[cur - 1][1], GRADES[cur - 1][0]


def check(args):
    as_of = parse_date(args.as_of) if args.as_of else date.today()
    items = []

    def add(name, ok, detail):
        items.append({'name': name, 'result': ok, 'detail': detail})

    score = args.score
    grade = grade_of(score)
    if score is None:
        add('\u7b49\u7ea7\u5224\u5b9a', '\u9700\u6838\u5b9e', '\u672a\u63d0\u4f9b --score\uff0c\u65e0\u6cd5\u5224\u5b9a\u7b49\u7ea7')
    else:
        ng, nd = next_grade(score)
        if ng is None:
            add('\u7b49\u7ea7\u5224\u5b9a', '\u7b26\u5408', '{} \u5206\uff0c{}\uff08\u5df2\u4e3a\u6700\u9ad8\u7b49\u7ea7\uff09'.format(score, grade))
        elif grade.startswith('\u4e0d\u5165\u7ea7'):
            add('\u7b49\u7ea7\u5224\u5b9a', '\u4e0d\u7b26\u5408',
                '{} \u5206\uff0c\u672a\u8fbe\u5230 60 \u5206\uff0c\u4e0d\u53d1\u653e\u7b49\u7ea7\u8bc1\u4e66'.format(score))
        else:
            add('\u7b49\u7ea7\u5224\u5b9a', '\u7b26\u5408',
                '{} \u5206\uff0c{}\uff1b\u8ddd\u4e0a\u4e00\u7b49\u7ea7 {} \u8fd8\u5dee {} \u5206'.format(score, grade, ng, round(nd - score, 2)))

    req_score, req_name, purpose_name, note = PURPOSE_REQ.get(
        args.purpose, (None, '', '\u672a\u6307\u5b9a\u7528\u9014', ''))
    if req_score is None:
        add('\u7528\u9014\u8fbe\u6807', '\u9700\u6838\u5b9e', '\u672a\u6307\u5b9a\u7528\u9014\uff0c\u8bf7\u5148\u67e5\u6e05\u8ba4\u5b9a\u516c\u544a\u6216\u62db\u5f55\u516c\u544a\u8981\u6c42\u7684\u7b49\u7ea7')
    elif score is None:
        add('\u7528\u9014\u8fbe\u6807', '\u9700\u6838\u5b9e', '{} \u5e38\u89c1\u8981\u6c42 {}\uff08{} \u5206\uff09\uff0c\u672a\u63d0\u4f9b\u5206\u6570\u65e0\u6cd5\u5224\u65ad'.format(
            purpose_name, req_name, req_score))
    elif score >= req_score:
        add('\u7528\u9014\u8fbe\u6807', '\u7b26\u5408', '{} \u5e38\u89c1\u8981\u6c42 {}\uff08{} \u5206\uff09\uff0c\u5f53\u524d {} \u5206\u5df2\u8fbe\u6807\u3002{}'.format(
            purpose_name, req_name, req_score, score, note))
    else:
        add('\u7528\u9014\u8fbe\u6807', '\u4e0d\u7b26\u5408',
            '{} \u5e38\u89c1\u8981\u6c42 {}\uff08{} \u5206\uff09\uff0c\u5f53\u524d {} \u5206\uff0c\u8fd8\u5dee {} \u5206\u3002{}'.format(
                purpose_name, req_name, req_score, score, round(req_score - score, 2), note))

    if args.cert_date:
        cd = parse_date(args.cert_date)
        if cd >= CERT_LONG_VALID_FROM:
            add('\u8bc1\u4e66\u6709\u6548\u671f', '\u7b26\u5408',
                '{} \u53d6\u5f97\u7684\u8bc1\u4e66\uff0c\u5c5e 2003 \u5e74 6 \u6708\u4e4b\u540e\u53d6\u5f97\uff0c\u957f\u671f\u6709\u6548\uff1b'
                '\u4f46\u7528\u4eba\u5355\u4f4d\u662f\u5426\u8ba4\u53ef\u591a\u5e74\u4ee5\u524d\u7684\u8bc1\u4e66\u5c5e\u5355\u4f4d\u81ea\u4e3b\u5224\u65ad'.format(fmt(cd)))
        else:
            add('\u8bc1\u4e66\u6709\u6548\u671f', '\u4e0d\u7b26\u5408',
                '{} \u53d6\u5f97\u7684\u8bc1\u4e66\u5c5e\u65e9\u671f\u8bc1\u4e66\uff0c\u6309\u5f53\u65f6\u89c4\u5b9a\u6267\u884c\u6709\u6548\u671f\uff08\u5e38\u89c1\u4e3a 5 \u5e74\uff09\uff0c'
                '\u4e00\u822c\u5df2\u4e0d\u88ab\u8ba4\u53ef\uff0c\u5efa\u8bae\u91cd\u65b0\u6d4b\u8bd5'.format(fmt(cd)))
    else:
        add('\u8bc1\u4e66\u6709\u6548\u671f', '\u63d0\u793a', '\u672a\u63d0\u4f9b --cert-date\uff0c\u672a\u505a\u6709\u6548\u671f\u5224\u65ad')

    if args.last_test:
        lt = parse_date(args.last_test)
        interval = args.interval or DEFAULT_INTERVAL
        passed = (as_of - lt).days
        if passed >= interval:
            add('\u590d\u6d4b\u95f4\u9694', '\u7b26\u5408',
                '\u8ddd\u4e0a\u6b21\u6d4b\u8bd5 {} \u5929\uff0c\u5df2\u6ee1\u8db3 {} \u5929\u7684\u95f4\u9694\u8981\u6c42'.format(passed, interval))
        else:
            add('\u590d\u6d4b\u95f4\u9694', '\u4e0d\u7b26\u5408',
                '\u8ddd\u4e0a\u6b21\u6d4b\u8bd5\u4ec5 {} \u5929\uff0c\u672a\u6ee1\u8db3 {} \u5929\u7684\u95f4\u9694\u8981\u6c42\uff0c\u8fd8\u5dee {} \u5929\uff1b'
                '\u95f4\u9694\u8981\u6c42\u5404\u5730\u4e0d\u540c\uff0c\u4ee5\u5c5e\u5730\u6d4b\u8bd5\u7ad9\u89c4\u5b9a\u4e3a\u51c6'.format(
                    passed, interval, interval - passed))
    else:
        add('\u590d\u6d4b\u95f4\u9694', '\u63d0\u793a', '\u672a\u63d0\u4f9b --last-test\uff0c\u672a\u505a\u95f4\u9694\u6d4b\u7b97')

    blocked = [i for i in items if i['result'] == '\u4e0d\u7b26\u5408']
    todo = [i for i in items if i['result'] == '\u9700\u6838\u5b9e']
    if blocked:
        verdict = '\u5b58\u5728\u4e0d\u8fbe\u6807\u9879\uff0c\u9700\u590d\u6d4b\u6216\u8865\u6b63'
    elif todo:
        verdict = '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4'
    else:
        verdict = '\u7b49\u7ea7\u4e0e\u7528\u9014\u8981\u6c42\u5df2\u6ee1\u8db3'
    return {
        'score': score,
        'grade': grade,
        'purpose': purpose_name,
        'required_level': req_name,
        'items': items,
        'blocked': [i['name'] + '\uff1a' + i['detail'] for i in blocked],
        'todo': [i['name'] + '\uff1a' + i['detail'] for i in todo],
        'verdict': verdict,
    }


def render_md(r):
    out = []
    out.append('# \u666e\u901a\u8bdd\u6c34\u5e73\u6d4b\u8bd5\u6838\u67e5\u7ed3\u679c')
    out.append('')
    if r['score'] is not None:
        out.append('- \u6d4b\u8bd5\u5206\u6570\uff1a{} \u5206'.format(r['score']))
        out.append('- \u5224\u5b9a\u7b49\u7ea7\uff1a{}'.format(r['grade']))
    if r['required_level']:
        out.append('- \u7528\u9014\uff1a{}\uff0c\u5e38\u89c1\u8981\u6c42 {}'.format(r['purpose'], r['required_level']))
    out.append('- \u7ed3\u8bba\uff1a{}'.format(r['verdict']))
    out.append('')
    out.append('| \u6838\u67e5\u9879 | \u7ed3\u679c | \u8bf4\u660e |')
    out.append('|---|---|---|')
    for i in r['items']:
        out.append('| {} | {} | {} |'.format(i['name'], i['result'], i['detail']))
    out.append('')
    out.append('## \u5206\u503c\u6784\u6210\u4e0e\u5907\u8003\u4f18\u5148\u7ea7')
    out.append('')
    out.append('| \u6d4b\u8bd5\u9879 | \u5206\u503c |')
    out.append('|---|---|')
    for name, w in SUBJECT_WEIGHT:
        out.append('| {} | {} \u5206 |'.format(name, w))
    out.append('')
    out.append('> \u547d\u9898\u8bf4\u8bdd\u4e0e\u6717\u8bfb\u77ed\u6587\u5408\u8ba1 70 \u5206\uff0c\u662f\u62c9\u5f00\u7b49\u7ea7\u5dee\u8ddd\u7684\u5730\u65b9\uff0c\u5e94\u4f18\u5148\u6295\u5165\u65f6\u95f4\u3002')
    out.append('')
    if r['blocked']:
        out.append('## \u4e0d\u8fbe\u6807\u9879')
        out.append('')
        for b in r['blocked']:
            out.append('- {}'.format(b))
        out.append('')
    if r['todo']:
        out.append('## \u9700\u8865\u5145\u4fe1\u606f')
        out.append('')
        for t in r['todo']:
            out.append('- {}'.format(t))
        out.append('')
    out.append('## \u63d0\u9192')
    out.append('')
    out.append('1. \u7b49\u7ea7\u8981\u6c42\u6309\u7528\u9014\u67e5\uff1a\u8bed\u6587\u6559\u5e08\u5e38\u89c1\u8981\u6c42\u4e8c\u7ea7\u7532\u7b49\uff0c\u5176\u4ed6\u5b66\u79d1\u6559\u5e08\u5e38\u89c1\u8981\u6c42\u4e8c\u7ea7\u4e59\u7b49\uff0c'
               '\u4ee5\u8ba4\u5b9a\u516c\u544a\u4e3a\u51c6\u3002')
    out.append('2. 2003 \u5e74 6 \u6708\u4e4b\u540e\u53d6\u5f97\u7684\u666e\u901a\u8bdd\u6c34\u5e73\u6d4b\u8bd5\u7b49\u7ea7\u8bc1\u4e66\u957f\u671f\u6709\u6548\uff0c'
               '"5 \u5e74\u6709\u6548\u671f"\u9488\u5bf9\u7684\u662f\u65e9\u671f\u8bc1\u4e66\u3002')
    out.append('3. \u590d\u6d4b\u95f4\u9694\u5404\u5730\u4e0d\u540c\uff0c\u5e38\u89c1\u7ea6 3 \u4e2a\u6708\uff0c\u4ee5\u5c5e\u5730\u6d4b\u8bd5\u7ad9\u89c4\u5b9a\u4e3a\u51c6\u3002')
    out.append('4. \u6210\u7ee9\u590d\u67e5\u6709\u660e\u786e\u671f\u9650\uff0c\u903e\u671f\u4e00\u822c\u4e0d\u518d\u53d7\u7406\u3002')
    out.append('5. \u5dee 0.1 \u5206\u5c31\u662f\u5dee\u4e00\u4e2a\u7b49\u7ea7\uff0c\u4e0d\u8981\u6307\u671b"\u5dee\u4e0d\u591a"\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    class A(object):
        pass

    def mk(**kw):
        a = A()
        a.score = kw.get('score', None)
        a.purpose = kw.get('purpose', 'other')
        a.cert_date = kw.get('cert_date', None)
        a.last_test = kw.get('last_test', None)
        a.interval = kw.get('interval', DEFAULT_INTERVAL)
        a.as_of = kw.get('as_of', '2026-10-08')
        return a

    eq('case1 97\u5206\u4ee5\u4e0a\u4e00\u7532', grade_of(97.0), '\u4e00\u7ea7\u7532\u7b49')
    eq('case2 96.99\u4e00\u4e59', grade_of(96.99), '\u4e00\u7ea7\u4e59\u7b49')
    eq('case3 92\u4e00\u4e59', grade_of(92.0), '\u4e00\u7ea7\u4e59\u7b49')
    eq('case4 91.99\u4e8c\u7532', grade_of(91.99), '\u4e8c\u7ea7\u7532\u7b49')
    eq('case5 87\u4e8c\u7532', grade_of(87.0), '\u4e8c\u7ea7\u7532\u7b49')
    eq('case6 86.99\u4e8c\u4e59', grade_of(86.99), '\u4e8c\u7ea7\u4e59\u7b49')
    eq('case7 80\u4e8c\u4e59', grade_of(80.0), '\u4e8c\u7ea7\u4e59\u7b49')
    eq('case8 79.99\u4e09\u7532', grade_of(79.99), '\u4e09\u7ea7\u7532\u7b49')
    eq('case9 70\u4e09\u7532', grade_of(70.0), '\u4e09\u7ea7\u7532\u7b49')
    eq('case10 60\u4e09\u4e59', grade_of(60.0), '\u4e09\u7ea7\u4e59\u7b49')
    eq('case11 59.9\u4e0d\u5165\u7ea7', grade_of(59.9), '\u4e0d\u5165\u7ea7\uff0860 \u5206\u4ee5\u4e0b\u4e0d\u53d1\u8bc1\uff09')
    eq('case12 \u4e0a\u4e00\u7b49\u7ea7\u8ba1\u7b97', next_grade(86.5), ('\u4e8c\u7ea7\u7532\u7b49', 87.0))
    eq('case13 \u6700\u9ad8\u7b49\u7ea7\u65e0\u4e0a\u4e00\u7ea7', next_grade(98.0), (None, None))

    r1 = check(mk(score=86.5, purpose='teacher-chinese'))
    eq('case14 \u8bed\u6587\u6559\u5e08\u672a\u8fbe\u6807', r1['verdict'], '\u5b58\u5728\u4e0d\u8fbe\u6807\u9879\uff0c\u9700\u590d\u6d4b\u6216\u8865\u6b63')

    r2 = check(mk(score=88.0, purpose='teacher-chinese'))
    eq('case15 \u8bed\u6587\u6559\u5e08\u8fbe\u6807', r2['verdict'], '\u7b49\u7ea7\u4e0e\u7528\u9014\u8981\u6c42\u5df2\u6ee1\u8db3')

    r3 = check(mk(score=82.0, purpose='teacher-other'))
    eq('case16 \u5176\u4ed6\u5b66\u79d1\u6559\u5e08\u8fbe\u6807', r3['verdict'], '\u7b49\u7ea7\u4e0e\u7528\u9014\u8981\u6c42\u5df2\u6ee1\u8db3')

    r4 = check(mk(score=88.0, purpose='teacher-other', cert_date='2019-05-20'))
    eq('case17 \u8bc1\u4e66\u957f\u671f\u6709\u6548', r4['verdict'], '\u7b49\u7ea7\u4e0e\u7528\u9014\u8981\u6c42\u5df2\u6ee1\u8db3')
    cert_item = [i for i in r4['items'] if i['name'] == '\u8bc1\u4e66\u6709\u6548\u671f'][0]
    eq('case17 \u6709\u6548\u671f\u5224\u5b9a', cert_item['result'], '\u7b26\u5408')

    r5 = check(mk(score=88.0, purpose='teacher-other', cert_date='2001-05-20'))
    cert_item5 = [i for i in r5['items'] if i['name'] == '\u8bc1\u4e66\u6709\u6548\u671f'][0]
    eq('case18 \u65e9\u671f\u8bc1\u4e66\u5df2\u8fc7\u671f', cert_item5['result'], '\u4e0d\u7b26\u5408')

    r6 = check(mk(score=88.0, purpose='teacher-other', last_test='2026-08-01'))
    gap_item = [i for i in r6['items'] if i['name'] == '\u590d\u6d4b\u95f4\u9694'][0]
    eq('case19 \u95f4\u9694\u4e0d\u8db3', gap_item['result'], '\u4e0d\u7b26\u5408')

    r7 = check(mk(score=88.0, purpose='teacher-other', last_test='2026-05-01'))
    gap_item7 = [i for i in r7['items'] if i['name'] == '\u590d\u6d4b\u95f4\u9694'][0]
    eq('case20 \u95f4\u9694\u6ee1\u8db3', gap_item7['result'], '\u7b26\u5408')

    r8 = check(mk(score=88.0, purpose='other'))
    eq('case21 \u672a\u6307\u5b9a\u7528\u9014\u9700\u6838\u5b9e', r8['verdict'], '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 21\n\u8986\u76d6: \u4e09\u7ea7\u516d\u7b49\u5206\u6570\u8fb9\u754c/\u4e0d\u5165\u7ea7/\u4e0a\u4e00\u7b49\u7ea7\u5dee\u503c/'
               '\u8bed\u6587\u4e0e\u5176\u4ed6\u5b66\u79d1\u6559\u5e08\u8fbe\u6807\u5224\u5b9a/\u8bc1\u4e66\u6709\u6548\u671f\u5206\u754c/\u590d\u6d4b\u95f4\u9694/\u672a\u6307\u5b9a\u7528\u9014')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u666e\u901a\u8bdd\u6c34\u5e73\u6d4b\u8bd5\u7b49\u7ea7\u4e0e\u7528\u9014\u8fbe\u6807\u6838\u67e5')
    ap.add_argument('--score', type=float, help='\u6d4b\u8bd5\u603b\u5206 0~100')
    ap.add_argument('--purpose', default='other',
                    choices=['teacher-chinese', 'teacher-other', 'broadcaster',
                             'tour-guide', 'civil-service', 'other'])
    ap.add_argument('--cert-date', dest='cert_date', help='\u5df2\u6709\u8bc1\u4e66\u53d6\u5f97\u65e5\u671f YYYY-MM-DD')
    ap.add_argument('--last-test', dest='last_test', help='\u4e0a\u6b21\u6d4b\u8bd5\u65e5\u671f YYYY-MM-DD')
    ap.add_argument('--interval', type=int, default=DEFAULT_INTERVAL,
                    help='\u8981\u6c42\u7684\u590d\u6d4b\u95f4\u9694\u5929\u6570\uff0c\u9ed8\u8ba4 90')
    ap.add_argument('--as-of', dest='as_of', help='\u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    r = check(args)
    out = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
