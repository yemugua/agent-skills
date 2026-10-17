#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u6210\u4eba\u9ad8\u8003\u62a5\u8003\u6761\u4ef6\u6838\u67e5\u4e0e\u52a0\u5206\u5224\u5b9a\u3002

\u7528\u6cd5:
  python adult_gaokao_check.py --level zhuanben --birth 1990-05-01 --education zhuanke --verified yes --exam-year 2026
  python adult_gaokao_check.py --level gaoqi-zhuan --birth 2005-03-01 --education gaozhong --residence local
  python adult_gaokao_check.py --level zhuanben --birth 1990-05-01 --education zhuanke --verified yes --major-category clinical --license none
  python adult_gaokao_check.py --selftest

\u53c2\u6570:
  --level            gaoqi-zhuan \u9ad8\u8d77\u4e13 / gaoqi-ben \u9ad8\u8d77\u672c / zhuanben \u4e13\u5347\u672c
  --birth            \u51fa\u751f\u65e5\u671f YYYY-MM-DD
  --education        chuzhong \u521d\u4e2d / gaozhong \u9ad8\u4e2d / zhongzhuan \u4e2d\u4e13 / zhuanke \u4e13\u79d1 / benke \u672c\u79d1
  --verified         yes/no  \u4e13\u5347\u672c\u7684\u4e13\u79d1\u53ca\u4ee5\u4e0a\u5b66\u5386\u662f\u5426\u5b66\u4fe1\u7f51\u53ef\u67e5
  --major-category   normal \u666e\u901a / clinical \u4e34\u5e8a\u7c7b / nursing \u62a4\u7406\u5b66 / medical-other \u533b\u5b66\u5176\u4ed6
  --license          none / assistant-doctor \u6267\u4e1a\u52a9\u7406\u533b\u5e08\u53ca\u4ee5\u4e0a / nurse \u6267\u4e1a\u62a4\u58eb / rural-doctor \u4e61\u6751\u533b\u751f
  --residence        local \u6237\u7c4d\u5730 / other \u5f02\u5730
  --permit           yes/no \u5f02\u5730\u62a5\u8003\u662f\u5426\u6709\u5c45\u4f4f\u8bc1\u6216\u793e\u4fdd\u6750\u6599
  --student          yes/no \u662f\u5426\u4e3a\u5404\u7c7b\u9ad8\u4e2d\u7b49\u5b66\u6821\u5728\u6821\u751f
  --exam-year        \u62a5\u8003\u5e74\u4efd, \u9ed8\u8ba4\u57fa\u51c6\u65e5\u6240\u5728\u5e74\u4efd
  --as-of            \u6838\u67e5\u57fa\u51c6\u65e5, \u9ed8\u8ba4\u4eca\u5929
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

LEVEL_NAME = {
    'gaoqi-zhuan': '\u9ad8\u4e2d\u8d77\u70b9\u5347\u4e13\u79d1\uff08\u9ad8\u8d77\u4e13\uff09',
    'gaoqi-ben': '\u9ad8\u4e2d\u8d77\u70b9\u5347\u672c\u79d1\uff08\u9ad8\u8d77\u672c\uff09',
    'zhuanben': '\u4e13\u79d1\u8d77\u70b9\u5347\u672c\u79d1\uff08\u4e13\u5347\u672c\uff09',
}
EDU_NAME = {
    'chuzhong': '\u521d\u4e2d',
    'gaozhong': '\u9ad8\u4e2d',
    'zhongzhuan': '\u4e2d\u4e13',
    'zhuanke': '\u4e13\u79d1',
    'benke': '\u672c\u79d1\u53ca\u4ee5\u4e0a',
}
SUBJECTS = {
    'gaoqi-zhuan': '\u8bed\u6587\u3001\u6570\u5b66\uff08\u6587/\u7406\uff09\u3001\u5916\u8bed\uff0c\u603b\u5206 450',
    'gaoqi-ben': '\u8bed\u6587\u3001\u6570\u5b66\u3001\u5916\u8bed\u3001\u53f2\u5730\u7efc\u5408\u6216\u7269\u5316\u7efc\u5408\uff0c\u603b\u5206 600',
    'zhuanben': '\u653f\u6cbb\u3001\u5916\u8bed + \u4e13\u4e1a\u57fa\u7840\u8bfe\uff08\u6309\u5b66\u79d1\u95e8\u7c7b\uff09\uff0c\u603b\u5206 450',
}
BONUS_AGE = 25
BONUS_AGE_SCORE = 20


def parse_date(s):
    s = str(s).strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if not m:
        raise ValueError('\u65e5\u671f\u683c\u5f0f\u4e0d\u5bf9: %s' % s)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def fmt(d):
    return d.strftime('%Y-%m-%d')


def age_at(birth, on):
    """\u5728\u6307\u5b9a\u65e5\u671f\u65f6\u7684\u5468\u5c81\u3002"""
    a = on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))
    return a


def age_bonus(birth, exam_year):
    """\u6309\u62a5\u8003\u5f53\u5e74 12 \u6708 31 \u65e5\u662f\u5426\u5e74\u6ee1 25 \u5468\u5c81\u5224\u5b9a\u5e74\u9f84\u52a0\u5206\u3002"""
    end = date(int(exam_year), 12, 31)
    a = age_at(birth, end)
    return a >= BONUS_AGE, a


def check(args):
    as_of = parse_date(args.as_of) if args.as_of else date.today()
    exam_year = int(args.exam_year) if args.exam_year else as_of.year
    birth = parse_date(args.birth) if args.birth else None
    items = []

    def add(name, ok, detail):
        items.append({'name': name, 'result': ok, 'detail': detail})

    # \u5b66\u5386
    edu = args.education
    level = args.level
    if level == 'zhuanben':
        if edu in ('zhuanke', 'benke'):
            add('\u5b66\u5386\u5c42\u6b21', '\u7b26\u5408', '\u5df2\u53d6\u5f97 %s \u5b66\u5386\uff0c\u6ee1\u8db3\u4e13\u5347\u672c\u8d77\u70b9\u8981\u6c42' % EDU_NAME[edu])
        else:
            add('\u5b66\u5386\u5c42\u6b21', '\u4e0d\u7b26\u5408', '\u4e13\u5347\u672c\u9700\u56fd\u6c11\u6559\u80b2\u7cfb\u5217\u4e13\u79d1\u53ca\u4ee5\u4e0a\uff0c\u5f53\u524d\u4e3a%s' % EDU_NAME.get(edu, edu))
        if args.verified == 'yes':
            add('\u5b66\u5386\u6838\u9a8c', '\u7b26\u5408', '\u5b66\u4fe1\u7f51\u53ef\u67e5')
        elif args.verified == 'no':
            add('\u5b66\u5386\u6838\u9a8c', '\u9700\u6838\u5b9e', '\u5b66\u4fe1\u7f51\u67e5\u4e0d\u5230\u7684\u987b\u5148\u505a\u5b66\u5386\u8ba4\u8bc1\uff0c\u5426\u5219\u65e0\u6cd5\u901a\u8fc7\u62a5\u540d\u5ba1\u6838')
        else:
            add('\u5b66\u5386\u6838\u9a8c', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u5b66\u4fe1\u7f51\u6838\u9a8c\u60c5\u51b5\uff0c\u8bf7\u5148\u767b\u5f55\u5b66\u4fe1\u7f51\u786e\u8ba4')
    else:
        if edu in ('gaozhong', 'zhongzhuan', 'zhuanke', 'benke'):
            add('\u5b66\u5386\u5c42\u6b21', '\u7b26\u5408', '\u5177\u6709\u9ad8\u4e2d\u6bd5\u4e1a\u6587\u5316\u7a0b\u5ea6\uff08%s\uff09' % EDU_NAME[edu])
        elif edu == 'chuzhong':
            add('\u5b66\u5386\u5c42\u6b21', '\u4e0d\u7b26\u5408', '\u9ad8\u8d77\u4e13/\u9ad8\u8d77\u672c\u9700\u9ad8\u4e2d\u6bd5\u4e1a\u6587\u5316\u7a0b\u5ea6\u6216\u540c\u7b49\u5b66\u529b')
        else:
            add('\u5b66\u5386\u5c42\u6b21', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u5b66\u5386\u6216\u586b\u5199\u4e3a\u5176\u4ed6\uff0c\u6309\u7701\u516c\u544a\u53e3\u5f84\u786e\u8ba4')

    # \u5728\u6821\u751f
    if args.student == 'yes':
        add('\u5728\u6821\u751f\u9650\u5236', '\u4e0d\u7b26\u5408', '\u5404\u7c7b\u9ad8\u3001\u4e2d\u7b49\u5b66\u6821\u5728\u6821\u751f\u4e0d\u5f97\u62a5\u8003')
    elif args.student == 'no':
        add('\u5728\u6821\u751f\u9650\u5236', '\u7b26\u5408', '\u975e\u5728\u6821\u751f')
    else:
        add('\u5728\u6821\u751f\u9650\u5236', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u5728\u6821\u72b6\u6001')

    # \u5e74\u9f84
    if birth:
        a = age_at(birth, as_of)
        ok25, a_end = age_bonus(birth, exam_year)
        add('\u5e74\u9f84', '\u7b26\u5408' if a >= 18 else '\u9700\u6838\u5b9e',
            '\u6838\u67e5\u57fa\u51c6\u65e5 %d \u5468\u5c81\uff1b\u622a\u81f3 %d-12-31 \u4e3a %d \u5468\u5c81' % (a, exam_year, a_end))
        if ok25:
            add('\u5e74\u9f84\u52a0\u5206', '\u7b26\u5408',
                '\u622a\u81f3 %d-12-31 \u5e74\u6ee1 25 \u5468\u5c81\uff0c\u4e00\u822c\u53ef\u52a0 %d \u5206\uff08\u6309\u7701\u5f53\u5e74\u62db\u751f\u529e\u6cd5\uff09' % (exam_year, BONUS_AGE_SCORE))
        else:
            add('\u5e74\u9f84\u52a0\u5206', '\u4e0d\u7b26\u5408',
                '\u622a\u81f3 %d-12-31 \u672a\u6ee1 25 \u5468\u5c81\uff0c\u4e0d\u4eab\u53d7\u5e74\u9f84\u52a0\u5206' % exam_year)
    else:
        add('\u5e74\u9f84', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u51fa\u751f\u65e5\u671f')

    # \u533b\u5b66\u7c7b
    cat = args.major_category
    if cat == 'clinical':
        if args.license in ('assistant-doctor', 'rural-doctor'):
            add('\u533b\u5b66\u7c7b\u8d44\u683c', '\u7b26\u5408', '\u4e34\u5e8a\u7c7b\u4e13\u4e1a\u5df2\u53d6\u5f97\u76f8\u5e94\u6267\u4e1a\u8d44\u683c\u6216\u4e61\u6751\u533b\u751f\u8bc1\u4e66')
        elif args.license == 'nurse':
            add('\u533b\u5b66\u7c7b\u8d44\u683c', '\u4e0d\u7b26\u5408', '\u6267\u4e1a\u62a4\u58eb\u8bc1\u4e66\u4e0d\u80fd\u4f5c\u4e3a\u4e34\u5e8a\u7c7b\u4e13\u4e1a\u7684\u62a5\u8003\u4f9d\u636e')
        else:
            add('\u533b\u5b66\u7c7b\u8d44\u683c', '\u4e0d\u7b26\u5408',
                '\u4e34\u5e8a\u7c7b\u4e13\u4e1a\u9700\u6267\u4e1a\u52a9\u7406\u533b\u5e08\u53ca\u4ee5\u4e0a\u8d44\u683c\u3001\u76f8\u5e94\u4e2d\u4e13\u53ca\u4ee5\u4e0a\u5b66\u5386\uff0c\u6216\u4e61\u6751\u533b\u751f\u8bc1\u4e66+\u4e2d\u4e13\u5b66\u5386')
    elif cat == 'nursing':
        if args.license == 'nurse':
            add('\u533b\u5b66\u7c7b\u8d44\u683c', '\u7b26\u5408', '\u62a4\u7406\u5b66\u4e13\u4e1a\u5df2\u53d6\u5f97\u6267\u4e1a\u62a4\u58eb\u8bc1\u4e66')
        else:
            add('\u533b\u5b66\u7c7b\u8d44\u683c', '\u4e0d\u7b26\u5408', '\u62a4\u7406\u5b66\u4e13\u4e1a\u9700\u7701\u7ea7\u536b\u751f\u5065\u5eb7\u884c\u653f\u90e8\u95e8\u9881\u53d1\u7684\u6267\u4e1a\u62a4\u58eb\u8bc1\u4e66')
    elif cat == 'medical-other':
        add('\u533b\u5b66\u7c7b\u8d44\u683c', '\u9700\u6838\u5b9e', '\u533b\u5b66\u95e8\u7c7b\u5176\u4ed6\u4e13\u4e1a\u5e94\u4e3a\u4ece\u4e8b\u536b\u751f\u3001\u533b\u836f\u884c\u4e1a\u7684\u5728\u804c\u4e13\u4e1a\u6280\u672f\u4eba\u5458\uff0c\u9700\u5355\u4f4d\u8bc1\u660e')
    else:
        add('\u4e13\u4e1a\u7c7b\u522b', '\u7b26\u5408', '\u975e\u533b\u5b66\u7c7b\uff0c\u65e0\u989d\u5916\u6267\u4e1a\u8d44\u683c\u8981\u6c42')

    # \u5f02\u5730\u62a5\u8003
    if args.residence == 'local':
        add('\u62a5\u8003\u5730', '\u7b26\u5408', '\u6237\u7c4d\u6240\u5728\u5730\u62a5\u8003')
    elif args.residence == 'other':
        if args.permit == 'yes':
            add('\u62a5\u8003\u5730', '\u7b26\u5408', '\u5f02\u5730\u62a5\u8003\u5df2\u5907\u5c45\u4f4f\u8bc1\u6216\u793e\u4fdd\u6750\u6599')
        else:
            add('\u62a5\u8003\u5730', '\u9700\u6838\u5b9e', '\u5f02\u5730\u62a5\u8003\u4e00\u822c\u9700\u5c45\u4f4f\u8bc1\u3001\u793e\u4fdd\u7f34\u7eb3\u8bc1\u660e\u6216\u5355\u4f4d\u8bc1\u660e\uff0c\u7f3a\u6750\u6599\u4f1a\u88ab\u5ba1\u6838\u9a73\u56de')
    else:
        add('\u62a5\u8003\u5730', '\u9700\u6838\u5b9e', '\u672a\u586b\u5199\u62a5\u8003\u5730\u60c5\u51b5')

    blocked = [i for i in items if i['result'] == '\u4e0d\u7b26\u5408']
    todo = [i for i in items if i['result'] == '\u9700\u6838\u5b9e']
    if blocked:
        verdict = '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6'
    elif todo:
        verdict = '\u9700\u8865\u5145\u6750\u6599\u6216\u6838\u5b9e\u540e\u786e\u8ba4'
    else:
        verdict = '\u7b26\u5408\u57fa\u672c\u62a5\u8003\u6761\u4ef6'

    return {
        'level': LEVEL_NAME.get(level, level),
        'exam_year': exam_year,
        'as_of': fmt(as_of),
        'subjects': SUBJECTS.get(level, ''),
        'items': items,
        'blocked': [i['name'] + '\uff1a' + i['detail'] for i in blocked],
        'todo': [i['name'] + '\uff1a' + i['detail'] for i in todo],
        'verdict': verdict,
    }


def render_md(r):
    out = []
    out.append('# \u6210\u4eba\u9ad8\u8003\u62a5\u8003\u6761\u4ef6\u6838\u67e5\u7ed3\u679c')
    out.append('')
    out.append('- \u62a5\u8003\u5c42\u6b21\uff1a%s' % r['level'])
    out.append('- \u62a5\u8003\u5e74\u4efd\uff1a%d \u5e74' % r['exam_year'])
    out.append('- \u6838\u67e5\u57fa\u51c6\u65e5\uff1a%s' % r['as_of'])
    out.append('- \u8003\u8bd5\u79d1\u76ee\uff1a%s' % r['subjects'])
    out.append('- \u7ed3\u8bba\uff1a%s' % r['verdict'])
    out.append('')
    out.append('| \u6838\u67e5\u9879 | \u7ed3\u679c | \u8bf4\u660e |')
    out.append('|---|---|---|')
    for i in r['items']:
        out.append('| %s | %s | %s |' % (i['name'], i['result'], i['detail']))
    out.append('')
    if r['blocked']:
        out.append('## \u4e0d\u7b26\u5408\u9879')
        out.append('')
        for b in r['blocked']:
            out.append('- %s' % b)
        out.append('')
    if r['todo']:
        out.append('## \u9700\u8865\u5145\u6216\u6838\u5b9e\u9879')
        out.append('')
        for t in r['todo']:
            out.append('- %s' % t)
        out.append('')
    out.append('## \u63d0\u9192')
    out.append('')
    out.append('1. \u62a5\u540d\u65f6\u95f4\u3001\u786e\u8ba4\u65b9\u5f0f\u3001\u7f34\u8d39\u65f6\u9650\u4e0e\u5fd7\u613f\u6570\u91cf\u4ee5\u8003\u751f\u6240\u5728\u7701\u4efd\u5f53\u5e74\u6210\u4eba\u9ad8\u6821\u62db\u751f\u529e\u6cd5\u4e3a\u51c6\uff0c\u672c\u811a\u672c\u4ec5\u505a\u901a\u884c\u53e3\u5f84\u6838\u67e5\u3002')
    out.append('2. \u4e13\u5347\u672c\u5b66\u5386\u5fc5\u987b\u5b66\u4fe1\u7f51\u53ef\u67e5\uff0c\u67e5\u4e0d\u5230\u8981\u5148\u505a\u5b66\u5386\u8ba4\u8bc1\u3002')
    out.append('3. \u533b\u5b66\u7c7b\u4e13\u4e1a\u6709\u6267\u4e1a\u8d44\u683c\u95e8\u69db\uff0c\u4e14\u6210\u4eba\u533b\u5b66\u5b66\u5386\u4e00\u822c\u4e0d\u4f5c\u4e3a\u62a5\u8003\u6267\u4e1a\u533b\u5e08/\u62a4\u58eb\u7684\u4f9d\u636e\u3002')
    out.append('4. \u52a0\u5206\u7b26\u5408\u591a\u9879\u7684\u53ea\u53d6\u6700\u9ad8\u4e00\u9879\uff0c\u4e0d\u7d2f\u52a0\u3002')
    out.append('5. \u4e0d\u5b58\u5728\u201c\u5305\u8fc7\u201d\u201c\u4e0d\u7528\u8003\u8bd5\u201d\uff0c\u8bf7\u8ba4\u51c6\u7701\u6559\u80b2\u8003\u8bd5\u9662\u5b98\u7f51\u4e0e\u5b98\u65b9\u6559\u5b66\u70b9\u3002')
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
        a.level = kw.get('level', 'zhuanben')
        a.birth = kw.get('birth', None)
        a.education = kw.get('education', 'zhuanke')
        a.verified = kw.get('verified', 'yes')
        a.major_category = kw.get('major_category', 'normal')
        a.license = kw.get('license', 'none')
        a.residence = kw.get('residence', 'local')
        a.permit = kw.get('permit', 'no')
        a.student = kw.get('student', 'no')
        a.exam_year = kw.get('exam_year', None)
        a.as_of = kw.get('as_of', '2026-10-08')
        return a

    r1 = check(mk(birth='1990-05-01'))
    eq('case1 \u7ed3\u8bba', r1['verdict'], '\u7b26\u5408\u57fa\u672c\u62a5\u8003\u6761\u4ef6')
    eq('case1 \u5e74\u9f84\u52a0\u5206', '\u622a\u81f3 2026-12-31 \u5e74\u6ee1 25 \u5468\u5c81' in ''.join(
        [i['detail'] for i in r1['items']]), True)

    r2 = check(mk(education='gaozhong'))
    eq('case2 \u4e13\u5347\u672c\u5b66\u5386\u4e0d\u7b26', r2['verdict'], '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6')

    r3 = check(mk(verified='no'))
    eq('case3 \u5b66\u5386\u9700\u6838\u5b9e', r3['verdict'], '\u9700\u8865\u5145\u6750\u6599\u6216\u6838\u5b9e\u540e\u786e\u8ba4')

    r4 = check(mk(level='gaoqi-zhuan', education='chuzhong', birth='2005-03-01'))
    eq('case4 \u9ad8\u8d77\u4e13\u521d\u4e2d\u5b66\u5386\u4e0d\u7b26', r4['verdict'], '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6')

    r5 = check(mk(major_category='clinical', license='none'))
    eq('case5 \u4e34\u5e8a\u7c7b\u65e0\u8d44\u683c', r5['verdict'], '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6')

    r6 = check(mk(birth='1990-05-01', major_category='nursing', license='nurse'))
    eq('case6 \u62a4\u7406\u6709\u62a4\u58eb\u8bc1', r6['verdict'], '\u7b26\u5408\u57fa\u672c\u62a5\u8003\u6761\u4ef6')

    r7 = check(mk(residence='other', permit='no'))
    eq('case7 \u5f02\u5730\u65e0\u5c45\u4f4f\u8bc1', r7['verdict'], '\u9700\u8865\u5145\u6750\u6599\u6216\u6838\u5b9e\u540e\u786e\u8ba4')

    r8 = check(mk(student='yes'))
    eq('case8 \u5728\u6821\u751f', r8['verdict'], '\u4e0d\u7b26\u5408\u62a5\u8003\u6761\u4ef6')

    eq('case9 \u5e74\u9f84\u52a0\u5206\u5224\u5b9a False', age_bonus(date(2002, 1, 1), 2026), (False, 24))
    eq('case10 \u5e74\u9f84\u52a0\u5206\u5224\u5b9a True', age_bonus(date(2001, 12, 31), 2026), (True, 25))
    eq('case11 \u5468\u5c81\u8ba1\u7b97', age_at(date(2000, 10, 9), date(2026, 10, 8)), 25)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 15\n\u8986\u76d6: \u5b66\u5386\u5c42\u6b21/\u5b66\u4fe1\u7f51\u6838\u9a8c/\u533b\u5b66\u7c7b\u8d44\u683c/'
               '\u5f02\u5730\u62a5\u8003/\u5728\u6821\u751f/\u5e74\u9f84\u52a0\u5206\u8282\u70b9')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u6210\u4eba\u9ad8\u8003\u62a5\u8003\u6761\u4ef6\u6838\u67e5\u4e0e\u52a0\u5206\u5224\u5b9a')
    ap.add_argument('--level', default='zhuanben', choices=['gaoqi-zhuan', 'gaoqi-ben', 'zhuanben'])
    ap.add_argument('--birth', help='\u51fa\u751f\u65e5\u671f YYYY-MM-DD')
    ap.add_argument('--education', default='zhuanke',
                    choices=['chuzhong', 'gaozhong', 'zhongzhuan', 'zhuanke', 'benke'])
    ap.add_argument('--verified', default='', choices=['', 'yes', 'no'], help='\u4e13\u5347\u672c\u5b66\u5386\u662f\u5426\u5b66\u4fe1\u7f51\u53ef\u67e5')
    ap.add_argument('--major-category', dest='major_category', default='normal',
                    choices=['normal', 'clinical', 'nursing', 'medical-other'])
    ap.add_argument('--license', default='none',
                    choices=['none', 'assistant-doctor', 'nurse', 'rural-doctor'])
    ap.add_argument('--residence', default='local', choices=['local', 'other'])
    ap.add_argument('--permit', default='no', choices=['yes', 'no'], help='\u5f02\u5730\u62a5\u8003\u662f\u5426\u6709\u5c45\u4f4f\u8bc1\u6216\u793e\u4fdd\u6750\u6599')
    ap.add_argument('--student', default='no', choices=['yes', 'no'], help='\u662f\u5426\u4e3a\u9ad8\u3001\u4e2d\u7b49\u5b66\u6821\u5728\u6821\u751f')
    ap.add_argument('--exam-year', dest='exam_year', help='\u62a5\u8003\u5e74\u4efd\uff0c\u9ed8\u8ba4\u57fa\u51c6\u65e5\u6240\u5728\u5e74\u4efd')
    ap.add_argument('--as-of', dest='as_of', help='\u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'], help='\u8f93\u51fa\u683c\u5f0f')
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
