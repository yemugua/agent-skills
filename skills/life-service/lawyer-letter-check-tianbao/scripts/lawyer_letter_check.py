#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u5f8b\u5e08\u51fd\u64b0\u5199\u6838\u67e5\u3001\u98ce\u9669\u8868\u8ff0\u626b\u63cf\u4e0e\u8bc9\u8bbc\u65f6\u6548\u6d4b\u7b97\u3002

\u7528\u6cd5:
  python lawyer_letter_check.py --mode send --file \u5f8b\u5e08\u51fd.txt --debt-due 2024-05-01
  python lawyer_letter_check.py --mode reply --file \u6536\u5230\u7684\u5f8b\u5e08\u51fd.txt
  python lawyer_letter_check.py --selftest

\u53c2\u6570:
  --mode        send \u53d1\u51fd\u524d\u6838\u67e5 / reply \u6536\u5230\u51fd\u540e\u6838\u67e5
  --file       \u51fd\u4ef6\u6587\u672c\uff08.txt / .md\uff09
  --debt-due   \u503a\u52a1\u5230\u671f\u65e5\u6216\u77e5\u9053\u6743\u5229\u53d7\u635f\u65e5 YYYY-MM-DD\uff0c\u7528\u4e8e\u8bc9\u8bbc\u65f6\u6548\u6d4b\u7b97
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

# \u51fd\u4ef6\u8981\u7d20\uff1a\u540d\u79f0 -> \u547d\u4e2d\u4efb\u4e00\u5173\u952e\u8bcd\u5373\u89c6\u4e3a\u5b58\u5728
ELEMENTS = [
    ('\u6807\u9898', ['\u5f8b\u5e08\u51fd']),
    ('\u53d7\u51fd\u4eba', ['\u81f4\uff1a', '\u81f4 ', '\u53d7\u51fd\u4eba']),
    ('\u59d4\u6258\u5173\u7cfb', ['\u59d4\u6258', '\u5f8b\u5e08\u4e8b\u52a1\u6240']),
    ('\u4e8b\u5b9e\u9648\u8ff0', ['\u4e8b\u5b9e', '\u7b7e\u8ba2', '\u7ea6\u5b9a', '\u622a\u81f3']),
    ('\u8bc1\u636e\u6307\u5411', ['\u8bc1\u636e', '\u4e3a\u8bc1', '\u9001\u8d27\u5355', '\u5bf9\u8d26\u5355', '\u5408\u540c']),
    ('\u6cd5\u5f8b\u4f9d\u636e', ['\u4f9d\u636e', '\u6839\u636e', '\u89c4\u5b9a', '\u6cd5\u5f8b']),
    ('\u5177\u4f53\u8981\u6c42', ['\u8981\u6c42', '\u8bf7\u4e8e', '\u652f\u4ed8\u81f3', '\u5e94\u7acb\u5373']),
    ('\u5c65\u884c\u671f\u9650', ['\u65e5\u5185', '\u65e5\u524d', '\u4e4b\u524d', '\u671f\u9650\u5185']),
    ('\u540e\u679c\u63d0\u793a', ['\u5426\u5219', '\u8bc9\u8bbc', '\u4ef2\u88c1', '\u4f9d\u6cd5\u91c7\u53d6']),
    ('\u8054\u7cfb\u65b9\u5f0f', ['\u8054\u7cfb\u7535\u8bdd', '\u8054\u7cfb\u5730\u5740', '\u7535\u8bdd']),
    ('\u843d\u6b3e\u4e0e\u65e5\u671f', ['\u627f\u529e\u5f8b\u5e08', '\u5e74', '\u6708', '\u65e5']),
]

# \u98ce\u9669\u8868\u8ff0\uff1a\u540d\u79f0 -> (\u5173\u952e\u8bcd, \u8bf4\u660e)
RISKS = [
    ('\u5a01\u80c1\u6050\u5413', ['\u540e\u679c\u81ea\u8d1f', '\u8ba9\u4f60\u597d\u770b', '\u7b49\u7740\u77a7', '\u4e0d\u5ba2\u6c14', '\u6536\u62fe\u4f60'],
     '\u8fdd\u53cd\u6267\u4e1a\u89c4\u8303\uff0c\u524a\u5f31\u51fd\u4ef6\u53ef\u4fe1\u5ea6\uff0c\u5e94\u6539\u4e3a\u300c\u5c06\u4f9d\u6cd5\u63d0\u8d77\u8bc9\u8bbc/\u7533\u8bf7\u4ef2\u88c1\u300d'),
    ('\u4fae\u8fb1\u8bfd\u8c24', ['\u9a97\u5b50', '\u8001\u8d56', '\u65e0\u803b', '\u4e0d\u8981\u8138'],
     '\u53ef\u80fd\u6784\u6210\u540d\u8a89\u4fb5\u6743\uff0c\u5e94\u5220\u9664\uff0c\u53ea\u9648\u8ff0\u5ba2\u89c2\u4e8b\u5b9e'),
    ('\u7edd\u5bf9\u5316\u65ad\u8a00', ['\u5fc5\u5c06\u627f\u62c5\u5211\u4e8b\u8d23\u4efb', '\u5fc5\u5b9a\u8d25\u8bc9', '\u4e00\u5b9a\u4f1a\u88ab\u5224\u5211', '100%\u80dc\u8bc9', '\u5fc5\u7136\u8d25\u8bc9'],
     '\u8d85\u51fa\u5f8b\u5e08\u8eab\u4efd\u7684\u5224\u65ad\uff0c\u5e94\u6539\u4e3a\u300c\u53ef\u80fd\u627f\u62c5\u76f8\u5e94\u6cd5\u5f8b\u8d23\u4efb\u300d'),
    ('\u5192\u5145\u516c\u6743\u529b', ['\u672c\u9662', '\u672c\u5c40', '\u5224\u5904', '\u5df2\u7ecf\u5224\u51b3', '\u5df2\u7acb\u6848'],
     '\u6697\u793a\u5df2\u7531\u53f8\u6cd5\u673a\u5173\u5904\u7406\u5c5e\u4e8e\u4e25\u91cd\u8fdd\u89c4\uff0c\u5e94\u5220\u9664\u6216\u636e\u5b9e\u8868\u8ff0'),
    ('\u9690\u79c1\u66dd\u5149\u5a01\u80c1', ['\u901a\u77e5\u4f60\u7684\u5bb6\u4eba', '\u544a\u77e5\u4f60\u7684\u5355\u4f4d', '\u516c\u5f00\u66dd\u5149', '\u5f20\u8d34'],
     '\u5c5e\u4e8e\u4e0d\u5f53\u65bd\u538b\u4e14\u53ef\u80fd\u4fb5\u72af\u4e2a\u4eba\u4fe1\u606f\uff0c\u5e94\u5220\u9664'),
    ('\u4e0d\u5f53\u627f\u8bfa\u7ed3\u679c', ['\u5305\u8d62', '\u4fdd\u8bc1\u8981\u56de', '\u4e00\u5b9a\u80dc\u8bc9', '\u4fdd\u8bc1\u80dc\u8bc9'],
     '\u8fdd\u89c4\u627f\u8bfa\u7ed3\u679c\uff0c\u5e94\u5220\u9664'),
]

MIN_REASONABLE_DAYS = 7
LIMITATION_YEARS = 3


def parse_date(s):
    s = str(s).strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if not m:
        raise ValueError('\u65e5\u671f\u683c\u5f0f\u4e0d\u5bf9: %s' % s)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def add_year(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def fmt(d):
    return d.strftime('%Y-%m-%d')


def elements_hit(text):
    text = text or ''
    out = []
    for name, kws in ELEMENTS:
        hit = [k for k in kws if k in text]
        out.append({'name': name, 'result': '\u6709' if hit else '\u7f3a',
                    'detail': '' if hit else '\u672a\u68c0\u7d22\u5230\u76f8\u5173\u8868\u8ff0\uff0c\u9700\u4eba\u5de5\u786e\u8ba4'})
    return out


def risks_hit(text):
    text = text or ''
    out = []
    for name, kws, advice in RISKS:
        hit = [k for k in kws if k in text]
        if hit:
            out.append({'name': name, 'keywords': hit, 'advice': advice})
    return out


def deadline_days(text):
    """\u62bd\u53d6\u51fd\u4ef6\u4e2d\u6700\u77ed\u7684\u5c65\u884c\u671f\u9650\u5929\u6570\u3002"""
    days = [int(x) for x in re.findall(r'(\d+)\s*\u65e5\u5185', text or '')]
    return min(days) if days else None


def limitation(due, as_of):
    """\u666e\u901a\u8bc9\u8bbc\u65f6\u6548\u6d4b\u7b97\u3002"""
    if not due:
        return None
    end = add_year(due, LIMITATION_YEARS)
    remain = (end - as_of).days
    if remain < 0:
        detail = '\u65f6\u6548\u5df2\u4e8e {} \u5c4a\u6ee1\uff08\u666e\u901a\u8bc9\u8bbc\u65f6\u6548\u901a\u884c\u53e3\u5f84\u4e3a {} \u5e74\uff09\u3002'.format(fmt(end), LIMITATION_YEARS)
        detail += '\u5bf9\u65b9\u63d0\u51fa\u65f6\u6548\u6297\u8fa9\u7684\uff0c\u5c06\u96be\u4ee5\u901a\u8fc7\u6cd5\u9662\u5f3a\u5236\u5b9e\u73b0\uff1b\u5e94\u7acb\u5373\u54a8\u8be2\u6267\u4e1a\u5f8b\u5e08\u786e\u8ba4\u662f\u5426\u5b58\u5728\u4e2d\u65ad\u3001\u4e2d\u6b62\u4e8b\u7531\u3002'
        result = '\u5df2\u5c4a\u6ee1'
    elif remain <= 180:
        detail = '\u8ddd {} \u65f6\u6548\u5c4a\u6ee1\u4ec5\u5269 {} \u5929\u3002\u5efa\u8bae\u5c3d\u5feb\u53d1\u51fa\u4e66\u9762\u4e3b\u5f20\u5e76\u4fdd\u7559\u9001\u8fbe\u51ed\u8bc1\uff0c\u4ee5\u4e2d\u65ad\u65f6\u6548\u3002'.format(fmt(end), remain)
        result = '\u4e34\u8fd1\u5c4a\u6ee1'
    else:
        detail = '\u65f6\u6548\u81f3 {}\uff0c\u5269\u4f59 {} \u5929\u3002\u53d1\u51fd\u5e76\u7559\u9001\u8fbe\u51ed\u8bc1\u53ef\u4e2d\u65ad\u65f6\u6548\uff0c\u4e2d\u65ad\u540e\u91cd\u65b0\u8ba1\u7b97\u3002'.format(fmt(end), remain)
        result = '\u672a\u5c4a\u6ee1'
    return {'name': '\u8bc9\u8bbc\u65f6\u6548\u6d4b\u7b97', 'result': result, 'detail': detail,
            'end': fmt(end), 'remain_days': remain}


def check(text, mode, debt_due=None, as_of=None):
    base = parse_date(as_of) if as_of else date.today()
    elems = elements_hit(text)
    risks = risks_hit(text)
    missing = [e['name'] for e in elems if e['result'] == '\u7f3a']
    extra = []
    d = deadline_days(text)
    if d is not None and d < MIN_REASONABLE_DAYS:
        extra.append({'name': '\u5c65\u884c\u671f\u9650\u5408\u7406\u6027', 'result': '\u5b58\u7591',
                      'detail': '\u51fd\u4ef6\u4e2d\u6700\u77ed\u671f\u9650\u4e3a {} \u65e5\uff0c\u660e\u663e\u77ed\u4e8e\u5e38\u89c1\u7684 7~15 \u65e5\u5408\u7406\u533a\u95f4\uff0c'
                                '\u53ef\u80fd\u88ab\u8ba4\u4e3a\u672a\u7ed9\u4e88\u5408\u7406\u671f\u9650\uff0c\u524a\u5f31\u50ac\u544a\u6548\u529b'.format(d)})
    lim = limitation(parse_date(debt_due) if debt_due else None, base)
    if lim:
        extra.append({'name': lim['name'], 'result': lim['result'], 'detail': lim['detail']})
    return {
        'mode': mode,
        'elements': elems,
        'risks': risks,
        'extra': extra,
        'missing': missing,
        'deadline_days': d,
        'limitation': lim,
        'verdict': verdict_of(mode, missing, risks, extra),
    }


def verdict_of(mode, missing, risks, extra):
    if mode == 'send':
        if risks:
            return '\u5b58\u5728\u7981\u6b62\u6027\u8868\u8ff0\uff0c\u5fc5\u987b\u4fee\u6539\u540e\u518d\u53d1'
        if missing:
            return '\u8981\u7d20\u7f3a\u5931 {} \u9879\uff0c\u9700\u8865\u6b63\u540e\u518d\u53d1'.format(len(missing))
        if any(e['result'] == '\u5b58\u7591' for e in extra):
            return '\u8981\u7d20\u9f50\u5168\uff0c\u4f46\u671f\u9650\u8bbe\u7f6e\u9700\u8c03\u6574'
        return '\u8981\u7d20\u9f50\u5168\u4e14\u672a\u53d1\u73b0\u7981\u6b62\u6027\u8868\u8ff0\uff0c\u53ef\u8fdb\u5165\u5f8b\u5e08\u5ba1\u6838\u73af\u8282'
    if risks:
        return '\u6765\u51fd\u5b58\u5728 {} \u7c7b\u4e0d\u5f53\u8868\u8ff0\uff0c\u53ef\u4f5c\u4e3a\u6297\u8fa9\u6216\u6295\u8bc9\u7684\u6293\u624b'.format(len(risks))
    if missing:
        return '\u6765\u51fd\u8981\u7d20\u4e0d\u5168\uff0c\u89c4\u8303\u6027\u5b58\u7591\uff0c\u53ef\u8981\u6c42\u5bf9\u65b9\u8865\u5145\u4e3b\u4f53\u4e0e\u59d4\u6258\u4fe1\u606f'
    return '\u6765\u51fd\u8981\u7d20\u9f50\u5168\u3001\u8868\u8ff0\u89c4\u8303\uff0c\u5e94\u6309\u671f\u9650\u53ca\u65f6\u4e66\u9762\u56de\u590d'


def render_md(r):
    out = []
    out.append('# \u5f8b\u5e08\u51fd\u6838\u67e5\u7ed3\u679c')
    out.append('')
    out.append('- \u6838\u67e5\u6a21\u5f0f\uff1a{}'.format('\u53d1\u51fd\u524d\u6838\u67e5' if r['mode'] == 'send' else '\u6536\u5230\u51fd\u540e\u6838\u67e5'))
    out.append('- \u7ed3\u8bba\uff1a{}'.format(r['verdict']))
    if r['deadline_days'] is not None:
        out.append('- \u51fd\u4ef6\u6700\u77ed\u5c65\u884c\u671f\u9650\uff1a{} \u65e5'.format(r['deadline_days']))
    if r['limitation']:
        out.append('- \u65f6\u6548\u5c4a\u6ee1\u65e5\uff1a{}\uff0c\u5269\u4f59 {} \u5929'.format(r['limitation']['end'], r['limitation']['remain_days']))
    out.append('')
    out.append('## \u4e00\u3001\u8981\u7d20\u6838\u67e5')
    out.append('')
    out.append('| \u8981\u7d20 | \u6709\u65e0 | \u8bf4\u660e |')
    out.append('|---|---|---|')
    for e in r['elements']:
        out.append('| {} | {} | {} |'.format(e['name'], e['result'], e['detail']))
    out.append('')
    out.append('## \u4e8c\u3001\u7981\u6b62\u6027\u4e0e\u4e0d\u5f53\u8868\u8ff0')
    out.append('')
    if not r['risks']:
        out.append('\u672a\u68c0\u7d22\u5230\u7981\u6b62\u6027\u8868\u8ff0\uff08\u4e0d\u4ee3\u8868\u4e0d\u5b58\u5728\uff0c\u9700\u4eba\u5de5\u901a\u8bfb\u786e\u8ba4\uff09\u3002')
        out.append('')
    else:
        out.append('| \u7c7b\u578b | \u547d\u4e2d\u8868\u8ff0 | \u5904\u7406\u5efa\u8bae |')
        out.append('|---|---|---|')
        for k in r['risks']:
            out.append('| {} | {} | {} |'.format(k['name'], '\u3001'.join(k['keywords']), k['advice']))
        out.append('')
    out.append('## \u4e09\u3001\u671f\u9650\u4e0e\u65f6\u6548')
    out.append('')
    if not r['extra']:
        out.append('\u672a\u505a\u6d4b\u7b97\u3002\u53ef\u4f20\u5165 --debt-due \u8ba1\u7b97\u8bc9\u8bbc\u65f6\u6548\u3002')
        out.append('')
    else:
        out.append('| \u9879\u76ee | \u7ed3\u8bba | \u8bf4\u660e |')
        out.append('|---|---|---|')
        for e in r['extra']:
            out.append('| {} | {} | {} |'.format(e['name'], e['result'], e['detail']))
        out.append('')
    if r['mode'] == 'reply':
        out.append('## \u56db\u3001\u6536\u5230\u51fd\u540e\u7684\u5e94\u5bf9')
        out.append('')
        out.append('1. \u6838\u5b9e\u771f\u4f2a\uff1a\u67e5\u5f8b\u6240\u4e0e\u627f\u529e\u5f8b\u5e08\u662f\u5426\u771f\u5b9e\u5b58\u5728\uff0c\u6838\u5bf9\u843d\u6b3e\u4e0e\u8054\u7cfb\u65b9\u5f0f\u3002')
        out.append('2. \u9010\u6761\u5bf9\u8d26\uff1a\u51fd\u4e2d\u6bcf\u4e00\u53e5\u4e8b\u5b9e\u6807\u51fa\u5c5e\u5b9e\u3001\u4e0d\u5c5e\u5b9e\u3001\u9700\u6838\u5b9e\uff0c\u91d1\u989d\u4e0e\u7b97\u6cd5\u5355\u72ec\u6838\u5bf9\u3002')
        out.append('3. \u6309\u671f\u4e66\u9762\u56de\u590d\uff1a\u6c89\u9ed8\u662f\u6700\u5dee\u9009\u62e9\uff0c\u5e94\u5728\u671f\u9650\u5185\u56de\u51fd\u5e76\u4fdd\u7559\u9001\u8fbe\u51ed\u8bc1\u3002')
        out.append('4. \u56de\u51fd\u52a0\u514d\u8d23\u53e5\uff1a\u672c\u56de\u51fd\u4e0d\u6784\u6210\u5bf9\u4efb\u4f55\u8d23\u4efb\u7684\u627f\u8ba4\uff0c\u4ea6\u4e0d\u653e\u5f03\u6211\u65b9\u4f9d\u6cd5\u4eab\u6709\u7684\u4efb\u4f55\u6743\u5229\u4e0e\u6297\u8fa9\u3002')
        out.append('')
    else:
        out.append('## \u56db\u3001\u53d1\u51fd\u524d\u63d0\u9192')
        out.append('')
        out.append('1. \u5f8b\u5e08\u51fd\u6ca1\u6709\u5f3a\u5236\u6267\u884c\u529b\uff0c\u4f5c\u7528\u662f\u50ac\u544a\u3001\u56fa\u5b9a\u4e8b\u5b9e\u4e0e\u4e2d\u65ad\u65f6\u6548\u3002')
        out.append('2. \u7528 EMS \u5bc4\u9001\uff0c\u5185\u4ef6\u54c1\u540d\u5199\u660e\u300c\u67d0\u67d0\u5173\u4e8e\u67d0\u67d0\u4e8b\u5b9c\u7684\u5f8b\u5e08\u51fd\u300d\uff0c\u4fdd\u7559\u7b7e\u6536\u56de\u6267\u3002')
        out.append('3. \u540e\u679c\u63d0\u793a\u53ea\u80fd\u5199\u5df1\u65b9\u5c06\u91c7\u53d6\u7684\u5408\u6cd5\u63aa\u65bd\uff08\u63d0\u8d77\u8bc9\u8bbc\u3001\u7533\u8bf7\u4ef2\u88c1\u7b49\uff09\u3002')
        out.append('4. \u672c\u6280\u80fd\u63d0\u4f9b\u64b0\u5199\u4e0e\u6838\u67e5\u8f85\u52a9\uff0c\u6700\u7ec8\u5e94\u4ee5\u6267\u4e1a\u5f8b\u5e08\u540d\u4e49\u51fa\u5177\u5e76\u52a0\u76d6\u5f8b\u6240\u5370\u7ae0\u3002')
        out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    good = ('\u5f8b\u5e08\u51fd\n\u81f4\uff1a\u67d0\u67d0\u516c\u53f8\n\u672c\u6240\u63a5\u53d7\u67d0\u67d0\u59d4\u6258\uff0c\u6307\u6d3e\u67d0\u67d0\u5f8b\u5e08\u5c31\u67d0\u4e8b\u81f4\u51fd\u3002\n'
            '\u4e00\u3001\u4e8b\u5b9e\uff1a2024\u5e741\u67081\u65e5\u53cc\u65b9\u7b7e\u8ba2\u5408\u540c\uff0c\u7ea6\u5b9a2024\u5e745\u67081\u65e5\u524d\u4ed8\u6b3e100000\u5143\u3002'
            '\u622a\u81f3\u672c\u51fd\u53d1\u51fa\u4e4b\u65e5\u5c1a\u6b20100000\u5143\uff0c\u6709\u5408\u540c\u4e0e\u5bf9\u8d26\u5355\u4e3a\u8bc1\u3002\n'
            '\u4e8c\u3001\u4f9d\u636e\uff1a\u8d35\u65b9\u672a\u6309\u7ea6\u5b9a\u4ed8\u6b3e\uff0c\u5df2\u6784\u6210\u8fdd\u7ea6\uff0c\u5e94\u4f9d\u6cd5\u627f\u62c5\u8fdd\u7ea6\u8d23\u4efb\u3002\n'
            '\u4e09\u3001\u8981\u6c42\uff1a\u8bf7\u4e8e\u6536\u5230\u672c\u51fd\u4e4b\u65e5\u8d7710\u65e5\u5185\u652f\u4ed8\u81f3\u6307\u5b9a\u8d26\u6237\u3002\n'
            '\u56db\u3001\u5426\u5219\u59d4\u6258\u4eba\u5c06\u4f9d\u6cd5\u5411\u4eba\u6c11\u6cd5\u9662\u63d0\u8d77\u8bc9\u8bbc\u3002\n'
            '\u67d0\u67d0\u5f8b\u5e08\u4e8b\u52a1\u6240 \u627f\u529e\u5f8b\u5e08\uff1a\u67d0\u67d0 \u8054\u7cfb\u7535\u8bdd\uff1a12345678 2026\u5e7410\u67088\u65e5')

    r1 = check(good, 'send')
    eq('case1 \u89c4\u8303\u51fd\u4ef6\u65e0\u7f3a\u5931', r1['missing'], [])
    eq('case1 \u65e0\u98ce\u9669\u8868\u8ff0', r1['risks'], [])
    eq('case1 \u7ed3\u8bba', r1['verdict'], '\u8981\u7d20\u9f50\u5168\u4e14\u672a\u53d1\u73b0\u7981\u6b62\u6027\u8868\u8ff0\uff0c\u53ef\u8fdb\u5165\u5f8b\u5e08\u5ba1\u6838\u73af\u8282')
    eq('case1 \u671f\u9650\u5929\u6570', r1['deadline_days'], 10)

    r2 = check(good.replace('\u5426\u5219\u59d4\u6258\u4eba\u5c06\u4f9d\u6cd5\u5411\u4eba\u6c11\u6cd5\u9662\u63d0\u8d77\u8bc9\u8bbc', '\u5426\u5219\u540e\u679c\u81ea\u8d1f\uff0c\u8ba9\u4f60\u597d\u770b'), 'send')
    names2 = [k['name'] for k in r2['risks']]
    eq('case2 \u5a01\u80c1\u6050\u5413\u547d\u4e2d', '\u5a01\u80c1\u6050\u5413' in names2, True)
    eq('case2 \u7ed3\u8bba\u8981\u6c42\u4fee\u6539', '\u5fc5\u987b\u4fee\u6539' in r2['verdict'], True)

    r3 = check(good.replace('\u8d35\u65b9', '\u9a97\u5b50'), 'send')
    names3 = [k['name'] for k in r3['risks']]
    eq('case3 \u4fae\u8fb1\u8bfd\u8c24\u547d\u4e2d', '\u4fae\u8fb1\u8bfd\u8c24' in names3, True)

    r4 = check(good.replace('\u4f9d\u6cd5\u627f\u62c5\u8fdd\u7ea6\u8d23\u4efb', '\u5fc5\u5c06\u627f\u62c5\u5211\u4e8b\u8d23\u4efb\uff0c100%\u80dc\u8bc9'), 'send')
    names4 = [k['name'] for k in r4['risks']]
    eq('case4 \u7edd\u5bf9\u5316\u65ad\u8a00\u547d\u4e2d', '\u7edd\u5bf9\u5316\u65ad\u8a00' in names4, True)

    r5 = check(good + '\n\u672c\u9662\u5df2\u7acb\u6848\u5e76\u5c06\u5224\u5904\u4f60\u65b9\u8d54\u507f\u3002', 'send')
    names5 = [k['name'] for k in r5['risks']]
    eq('case5 \u5192\u5145\u516c\u6743\u529b\u547d\u4e2d', '\u5192\u5145\u516c\u6743\u529b' in names5, True)

    r6 = check(good + '\n\u903e\u671f\u5c06\u901a\u77e5\u4f60\u7684\u5bb6\u4eba\u5e76\u516c\u5f00\u66dd\u5149\u3002', 'send')
    names6 = [k['name'] for k in r6['risks']]
    eq('case6 \u9690\u79c1\u66dd\u5149\u5a01\u80c1\u547d\u4e2d', '\u9690\u79c1\u66dd\u5149\u5a01\u80c1' in names6, True)

    r7 = check(good.replace('\u4e4b\u65e5\u8d7710\u65e5\u5185', '\u4e4b\u65e5\u8d773\u65e5\u5185'), 'send')
    eq('case7 \u671f\u9650\u8fc7\u77ed\u88ab\u6807\u5b58\u7591', any(e['result'] == '\u5b58\u7591' for e in r7['extra']), True)
    eq('case7 \u7ed3\u8bba\u63d0\u793a\u8c03\u6574\u671f\u9650', '\u671f\u9650\u8bbe\u7f6e\u9700\u8c03\u6574' in r7['verdict'], True)

    poor = '\u5f8b\u5e08\u51fd\n\u8bf7\u5c3d\u5feb\u4ed8\u6b3e\u3002\n\u67d0\u67d0'
    r8 = check(poor, 'send')
    eq('case8 \u8981\u7d20\u7f3a\u5931', len(r8['missing']) > 0, True)
    eq('case8 \u7ed3\u8bba\u542b\u7f3a\u5931', '\u8981\u7d20\u7f3a\u5931' in r8['verdict'], True)

    r9 = check(good, 'reply')
    eq('case9 \u56de\u51fd\u6a21\u5f0f\u89c4\u8303\u6765\u51fd', r9['verdict'], '\u6765\u51fd\u8981\u7d20\u9f50\u5168\u3001\u8868\u8ff0\u89c4\u8303\uff0c\u5e94\u6309\u671f\u9650\u53ca\u65f6\u4e66\u9762\u56de\u590d')

    r10 = check(good.replace('\u5426\u5219\u59d4\u6258\u4eba\u5c06\u4f9d\u6cd5\u5411\u4eba\u6c11\u6cd5\u9662\u63d0\u8d77\u8bc9\u8bbc', '\u5426\u5219\u540e\u679c\u81ea\u8d1f'), 'reply')
    eq('case10 \u56de\u51fd\u6a21\u5f0f\u6293\u5230\u8fdd\u89c4\u70b9', '\u53ef\u4f5c\u4e3a\u6297\u8fa9' in r10['verdict'], True)

    lim1 = limitation(date(2024, 5, 1), date(2026, 10, 8))
    eq('case11 \u65f6\u6548\u672a\u5c4a\u6ee1', lim1['result'], '\u672a\u5c4a\u6ee1')
    eq('case11 \u65f6\u6548\u5c4a\u6ee1\u65e5', lim1['end'], '2027-05-01')

    lim2 = limitation(date(2020, 1, 1), date(2026, 10, 8))
    eq('case12 \u65f6\u6548\u5df2\u5c4a\u6ee1', lim2['result'], '\u5df2\u5c4a\u6ee1')

    lim3 = limitation(date(2023, 12, 1), date(2026, 10, 8))
    eq('case13 \u65f6\u6548\u4e34\u8fd1\u5c4a\u6ee1', lim3['result'], '\u4e34\u8fd1\u5c4a\u6ee1')

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 13\n\u8986\u76d6: \u4e5d\u9879\u8981\u7d20\u9f50\u5168\u4e0e\u7f3a\u5931/\u5a01\u80c1\u6050\u5413/\u4fae\u8fb1\u8bfd\u8c24/\u7edd\u5bf9\u5316\u65ad\u8a00/'
               '\u5192\u5145\u516c\u6743\u529b/\u9690\u79c1\u66dd\u5149/\u671f\u9650\u8fc7\u77ed/\u56de\u51fd\u6a21\u5f0f/\u8bc9\u8bbc\u65f6\u6548\u4e09\u6bb5\u5224\u5b9a')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u5f8b\u5e08\u51fd\u64b0\u5199\u6838\u67e5\u4e0e\u65f6\u6548\u6d4b\u7b97')
    ap.add_argument('--mode', default='send', choices=['send', 'reply'])
    ap.add_argument('--file', help='\u51fd\u4ef6\u6587\u672c\u6587\u4ef6\u8def\u5f84\uff08.txt / .md\uff09')
    ap.add_argument('--debt-due', dest='debt_due', help='\u503a\u52a1\u5230\u671f\u65e5\u6216\u77e5\u9053\u6743\u5229\u53d7\u635f\u65e5 YYYY-MM-DD')
    ap.add_argument('--as-of', dest='as_of', help='\u6838\u67e5\u57fa\u51c6\u65e5\uff0c\u9ed8\u8ba4\u4eca\u5929')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.file:
        print('\u9700\u8981 --file \u53c2\u6570\uff0c\u6216\u7528 --selftest \u8dd1\u81ea\u68c0')
        return 2
    with open(args.file, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    r = check(text, args.mode, args.debt_due, args.as_of)
    out = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
