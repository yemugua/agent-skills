#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u5408\u540c\u6761\u6b3e\u5ba1\u67e5\u4e0e\u8fdd\u7ea6\u6551\u6d4e\u6d4b\u7b97\u3002

\u7528\u6cd5:
  python contract_review.py --file \u5408\u540c.txt
  python contract_review.py --file \u5408\u540c.txt --amount 1000000 --liquidated 500000 --loss 200000
  python contract_review.py --file \u5408\u540c.txt --amount 1000000 --deposit 300000 --liquidated 100000
  python contract_review.py --selftest

\u53c2\u6570:
  --file         \u5408\u540c\u6587\u672c\uff08.txt / .md\uff0c\u652f\u6301\u4ece Word\u3001PDF \u590d\u5236\u51fa\u6765\u7684\u7eaf\u6587\u672c\uff09
  --amount       \u5408\u540c\u6807\u7684\u989d\uff08\u4e3b\u5408\u540c\u91d1\u989d\uff09\uff0c\u7528\u4e8e\u5b9a\u91d1 20% \u4e0a\u9650\u6d4b\u7b97
  --liquidated   \u7ea6\u5b9a\u7684\u8fdd\u7ea6\u91d1\u6570\u989d
  --loss         \u5b9e\u9645\u635f\u5931\u6570\u989d\uff0c\u7528\u4e8e\u8fdd\u7ea6\u91d1\u662f\u5426\u8fc7\u5206\u9ad8\u4e8e\u7684\u901a\u884c\u53e3\u5f84\u6d4b\u7b97
  --deposit      \u7ea6\u5b9a\u7684\u5b9a\u91d1\u6570\u989d
  --out          \u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84
  --format       md\uff08\u9ed8\u8ba4\uff09\u6216 json
  --selftest     \u8fd0\u884c\u5185\u7f6e\u81ea\u68c0
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u5fc5\u5907\u6761\u6b3e\uff1a\u540d\u79f0 -> \u547d\u4e2d\u4efb\u4e00\u5173\u952e\u8bcd\u5373\u89c6\u4e3a\u5b58\u5728
MUST_CLAUSES = [
    ('\u5f53\u4e8b\u4eba\u540d\u79f0\u6216\u59d3\u540d', ['\u7532\u65b9', '\u4e59\u65b9', '\u5f53\u4e8b\u4eba', '\u4e70\u65b9', '\u5356\u65b9', '\u51fa\u79df\u65b9', '\u627f\u79df\u65b9']),
    ('\u6807\u7684', ['\u6807\u7684', '\u8d27\u7269', '\u670d\u52a1\u5185\u5bb9', '\u5de5\u7a0b\u5185\u5bb9', '\u4ea7\u54c1']),
    ('\u6570\u91cf', ['\u6570\u91cf', '\u5de5\u7a0b\u91cf', '\u53f0', '\u4ef6', '\u5428']),
    ('\u8d28\u91cf', ['\u8d28\u91cf', '\u6280\u672f\u6807\u51c6', '\u9a8c\u6536\u6807\u51c6', '\u56fd\u5bb6\u6807\u51c6']),
    ('\u4ef7\u6b3e\u6216\u8005\u62a5\u916c', ['\u4ef7\u6b3e', '\u91d1\u989d', '\u4ef7\u683c', '\u62a5\u916c', '\u8d39\u7528', '\u5355\u4ef7']),
    ('\u5c65\u884c\u671f\u9650', ['\u671f\u9650', '\u4ea4\u4ed8\u65f6\u95f4', '\u5c65\u884c\u671f\u9650', '\u5de5\u671f', '\u4ea4\u8d27\u671f', '\u5b8c\u6210\u65f6\u95f4']),
    ('\u5c65\u884c\u5730\u70b9\u548c\u65b9\u5f0f', ['\u5730\u70b9', '\u65b9\u5f0f', '\u4ea4\u8d27', '\u4ea4\u4ed8\u65b9\u5f0f', '\u8fd0\u8f93']),
    ('\u8fdd\u7ea6\u8d23\u4efb', ['\u8fdd\u7ea6\u8d23\u4efb', '\u8fdd\u7ea6\u91d1', '\u8d54\u507f\u91d1', '\u903e\u671f']),
    ('\u89e3\u51b3\u4e89\u8bae\u7684\u65b9\u6cd5', ['\u4e89\u8bae', '\u4ef2\u88c1', '\u8bc9\u8bbc', '\u7ba1\u8f96', '\u6cd5\u9662']),
]

# \u5efa\u8bae\u6761\u6b3e\uff08\u975e\u6cd5\u5b9a\u5fc5\u5907\uff09
SUGGEST_CLAUSES = [
    ('\u901a\u77e5\u4e0e\u9001\u8fbe', ['\u9001\u8fbe', '\u901a\u77e5']),
    ('\u4e0d\u53ef\u6297\u529b', ['\u4e0d\u53ef\u6297\u529b']),
    ('\u9a8c\u6536', ['\u9a8c\u6536']),
    ('\u53d8\u66f4\u4e0e\u89e3\u9664', ['\u89e3\u9664', '\u53d8\u66f4']),
    ('\u4fdd\u5bc6', ['\u4fdd\u5bc6']),
    ('\u77e5\u8bc6\u4ea7\u6743\u5f52\u5c5e', ['\u77e5\u8bc6\u4ea7\u6743', '\u8457\u4f5c\u6743', '\u4e13\u5229', '\u5546\u6807']),
]

# \u9ad8\u98ce\u9669\u6761\u6b3e\uff1a\u540d\u79f0 -> (\u5173\u952e\u8bcd\u5217\u8868, \u98ce\u9669\u63d0\u793a)
RISK_CLAUSES = [
    ('\u5355\u65b9\u53d8\u66f4\u6743', ['\u6709\u6743\u968f\u65f6\u8c03\u6574', '\u5355\u65b9\u8c03\u6574', '\u968f\u65f6\u53d8\u66f4', '\u7532\u65b9\u6709\u6743\u53d8\u66f4'],
     '\u5bf9\u4ef7\u5931\u8861\uff0c\u5df1\u65b9\u5c65\u7ea6\u6210\u672c\u4e0d\u53ef\u63a7\uff0c\u5efa\u8bae\u6539\u4e3a\u53cc\u65b9\u534f\u5546\u4e00\u81f4\u5e76\u4e66\u9762\u786e\u8ba4'),
    ('\u65e0\u9650\u514d\u8d23', ['\u6982\u4e0d\u8d1f\u8d23', '\u4e0d\u627f\u62c5\u4efb\u4f55\u8d23\u4efb', '\u4efb\u4f55\u635f\u5931\u5747\u4e0d', '\u4e0d\u627f\u62c5\u4efb\u4f55\u8d54\u507f'],
     '\u4e0d\u5408\u7406\u514d\u9664\u5df1\u65b9\u8d23\u4efb\u7684\u6761\u6b3e\u53ef\u80fd\u88ab\u8ba4\u5b9a\u65e0\u6548\uff0c\u5e94\u9650\u5b9a\u514d\u8d23\u8303\u56f4\u4e0e\u60c5\u5f62'),
    ('\u6392\u9664\u5bf9\u65b9\u4e3b\u8981\u6743\u5229', ['\u4e0d\u5f97\u4e3b\u5f20', '\u653e\u5f03\u4e00\u5207\u6743\u5229', '\u65e0\u6743\u8981\u6c42', '\u4e0d\u5f97\u63d0\u51fa\u5f02\u8bae'],
     '\u683c\u5f0f\u6761\u6b3e\u4e2d\u6392\u9664\u5bf9\u65b9\u4e3b\u8981\u6743\u5229\u7684\u7ea6\u5b9a\u53ef\u80fd\u65e0\u6548\uff0c\u5efa\u8bae\u5220\u9664\u6216\u6539\u5199'),
    ('\u81ea\u52a8\u7eed\u7ea6', ['\u81ea\u52a8\u7eed', '\u81ea\u52a8\u987a\u5ef6', '\u89c6\u4e3a\u7eed\u671f'],
     '\u88ab\u52a8\u7eed\u671f\u9000\u51fa\u6210\u672c\u9ad8\uff0c\u5efa\u8bae\u6539\u4e3a\u5230\u671f\u524d\u4e66\u9762\u786e\u8ba4\u7eed\u7ea6'),
    ('\u80cc\u9760\u80cc\u4ed8\u6b3e', ['\u6536\u5230\u7b2c\u4e09\u65b9', '\u6536\u5230\u4e1a\u4e3b', '\u80cc\u9760\u80cc', '\u6536\u5230\u4e0a\u6e38'],
     '\u7b2c\u4e09\u65b9\u4e0d\u4ed8\u6b3e\u98ce\u9669\u88ab\u8f6c\u5ac1\uff0c\u5efa\u8bae\u8bbe\u7f6e\u6700\u957f\u4ed8\u6b3e\u671f\u9650'),
    ('\u5355\u65b9\u6307\u5b9a\u7ba1\u8f96', ['\u7532\u65b9\u6240\u5728\u5730\u6cd5\u9662', '\u7531\u7532\u65b9\u6240\u5728\u5730', '\u4e59\u65b9\u6240\u5728\u5730\u6cd5\u9662'],
     '\u589e\u52a0\u5df1\u65b9\u8bc9\u8bbc\u6210\u672c\uff0c\u7ea6\u5b9a\u7ba1\u8f96\u987b\u7b26\u5408\u6cd5\u5b9a\u6761\u4ef6'),
    ('\u65e0\u9650\u8fde\u5e26\u8d23\u4efb', ['\u4e00\u5207\u503a\u52a1', '\u627f\u62c5\u8fde\u5e26\u8d23\u4efb', '\u5168\u90e8\u503a\u52a1']),
    ('\u53e3\u5934\u53d8\u66f4', ['\u53e3\u5934\u53d8\u66f4', '\u53e3\u5934\u7ea6\u5b9a', '\u53e3\u5934\u901a\u77e5']),
    ('\u4ef2\u88c1\u6761\u6b3e\u4e0d\u660e\u786e', ['\u4ef2\u88c1']),
]

RISK_ADVICE = {
    '\u65e0\u9650\u8fde\u5e26\u8d23\u4efb': '\u8d23\u4efb\u8303\u56f4\u4e0d\u53ef\u63a7\uff0c\u5efa\u8bae\u9650\u5b9a\u4e3a\u7279\u5b9a\u503a\u52a1\u5e76\u8bbe\u4e0a\u9650',
    '\u53e3\u5934\u53d8\u66f4': '\u4e3e\u8bc1\u56f0\u96be\uff0c\u5efa\u8bae\u8981\u6c42\u53d8\u66f4\u4e00\u5f8b\u4e66\u9762\u786e\u8ba4\u5e76\u76d6\u7ae0',
    '\u4ef2\u88c1\u6761\u6b3e\u4e0d\u660e\u786e': '\u4ef2\u88c1\u534f\u8bae\u9700\u5177\u5907\u8bf7\u6c42\u4ef2\u88c1\u7684\u610f\u601d\u8868\u793a\u3001\u4ef2\u88c1\u4e8b\u9879\u3001\u9009\u5b9a\u7684\u4ef2\u88c1\u59d4\u5458\u4f1a\u4e09\u8981\u7d20\uff0c'
                      '\u672a\u9009\u5b9a\u660e\u786e\u4ef2\u88c1\u59d4\u5458\u4f1a\u7684\u53ef\u80fd\u5bfc\u81f4\u4ef2\u88c1\u534f\u8bae\u65e0\u6548',
}

RATIO_HIGH = 1.3


def clauses_hit(text):
    text = text or ''
    must = []
    for name, kws in MUST_CLAUSES:
        ok = any(k in text for k in kws)
        must.append({'name': name, 'result': '\u6709' if ok else '\u7f3a',
                     'detail': '' if ok else '\u672a\u68c0\u7d22\u5230\u76f8\u5173\u8868\u8ff0\uff0c\u9700\u4eba\u5de5\u786e\u8ba4\u662f\u5426\u4ee5\u5176\u4ed6\u65b9\u5f0f\u7ea6\u5b9a'})
    sug = []
    for name, kws in SUGGEST_CLAUSES:
        ok = any(k in text for k in kws)
        sug.append({'name': name, 'result': '\u6709' if ok else '\u7f3a',
                    'detail': '' if ok else '\u5efa\u8bae\u8865\u5145'})
    return must, sug


def risks_hit(text):
    text = text or ''
    out = []
    for item in RISK_CLAUSES:
        name, kws = item[0], item[1]
        advice = item[2] if len(item) > 2 else RISK_ADVICE.get(name, '')
        hit = [k for k in kws if k in text]
        if not hit:
            continue
        if name == '\u4ef2\u88c1\u6761\u6b3e\u4e0d\u660e\u786e':
            if '\u4ef2\u88c1\u59d4\u5458\u4f1a' in text:
                continue
            advice = RISK_ADVICE['\u4ef2\u88c1\u6761\u6b3e\u4e0d\u660e\u786e']
        out.append({'name': name, 'keywords': hit, 'advice': advice})
    return out


def money_checks(amount, liquidated, loss, deposit, text):
    """\u8fdd\u7ea6\u91d1\u8c03\u6574\u4e0e\u5b9a\u91d1\u4e0a\u9650\u6d4b\u7b97\u3002"""
    out = []
    has_liquidated = liquidated is not None
    has_deposit = deposit is not None or ('\u5b9a\u91d1' in (text or ''))

    if has_liquidated and loss is not None and loss > 0:
        ratio = liquidated / loss
        excess = liquidated - loss * RATIO_HIGH
        if liquidated > loss * RATIO_HIGH:
            out.append({
                'name': '\u8fdd\u7ea6\u91d1\u662f\u5426\u8fc7\u5206\u9ad8\u4e8e\u635f\u5931',
                'result': '\u5b58\u7591',
                'detail': '\u7ea6\u5b9a\u8fdd\u7ea6\u91d1 {}\uff0c\u5b9e\u9645\u635f\u5931 {}\uff0c\u4e3a\u635f\u5931\u7684 {:.1f} \u500d\uff1b'
                          '\u901a\u884c\u53c2\u7167\u53e3\u5f84\u4e3a\u8d85\u8fc7\u635f\u5931 30% \u53ef\u8ba4\u5b9a\u8fc7\u5206\u9ad8\u4e8e\uff0c\u8d85\u51fa\u7ea6 {}\uff0c'
                          '\u5bf9\u65b9\u53ef\u8bf7\u6c42\u9002\u5f53\u51cf\u5c11'.format(fmt_num(liquidated), fmt_num(loss),
                                                       ratio, fmt_num(excess)),
            })
        elif liquidated < loss:
            out.append({
                'name': '\u8fdd\u7ea6\u91d1\u662f\u5426\u4f4e\u4e8e\u635f\u5931',
                'result': '\u5b58\u7591',
                'detail': '\u7ea6\u5b9a\u8fdd\u7ea6\u91d1 {} \u4f4e\u4e8e\u5b9e\u9645\u635f\u5931 {}\uff0c\u53ef\u8bf7\u6c42\u4e88\u4ee5\u589e\u52a0\uff0c'
                          '\u4f46\u9700\u4e3e\u8bc1\u635f\u5931\u6570\u989d\u4e0e\u56e0\u679c\u5173\u7cfb'.format(fmt_num(liquidated), fmt_num(loss)),
            })
        else:
            out.append({
                'name': '\u8fdd\u7ea6\u91d1\u4e0e\u635f\u5931\u5339\u914d\u5ea6',
                'result': '\u7b26\u5408',
                'detail': '\u7ea6\u5b9a\u8fdd\u7ea6\u91d1 {}\uff0c\u5b9e\u9645\u635f\u5931 {}\uff0c\u4e3a\u635f\u5931\u7684 {:.1f} \u500d\uff0c'
                          '\u5904\u4e8e\u901a\u884c\u53c2\u7167\u533a\u95f4\u5185'.format(fmt_num(liquidated), fmt_num(loss), ratio),
            })

    if amount is not None and amount > 0 and deposit is not None:
        cap = amount * 0.2
        if deposit > cap:
            out.append({
                'name': '\u5b9a\u91d1\u662f\u5426\u8d85\u8fc7\u6807\u7684\u989d 20%',
                'result': '\u5b58\u7591',
                'detail': '\u6807\u7684\u989d {}\uff0c\u5b9a\u91d1\u4e0a\u9650\u4e3a {}\uff0820%\uff09\uff0c\u7ea6\u5b9a\u5b9a\u91d1 {}\uff0c'
                          '\u8d85\u51fa {} \u7684\u90e8\u5206\u4e0d\u4ea7\u751f\u5b9a\u91d1\u7684\u6548\u529b'.format(
                              fmt_num(amount), fmt_num(cap), fmt_num(deposit), fmt_num(deposit - cap)),
            })
        else:
            out.append({
                'name': '\u5b9a\u91d1\u662f\u5426\u8d85\u8fc7\u6807\u7684\u989d 20%',
                'result': '\u7b26\u5408',
                'detail': '\u7ea6\u5b9a\u5b9a\u91d1 {}\uff0c\u672a\u8d85\u8fc7\u6807\u7684\u989d 20% \u7684\u4e0a\u9650 {}'.format(fmt_num(deposit), fmt_num(cap)),
            })
        valid = min(deposit, cap)
        out.append({
            'name': '\u5b9a\u91d1\u7f5a\u5219\u6d4b\u7b97',
            'result': '\u63d0\u793a',
            'detail': '\u6709\u6548\u5b9a\u91d1 {}\uff0c\u7ed9\u4ed8\u65b9\u4e0d\u5c65\u884c\u65e0\u6743\u8bf7\u6c42\u8fd4\u8fd8\uff1b\u6536\u53d7\u65b9\u4e0d\u5c65\u884c\u5e94\u53cc\u500d\u8fd4\u8fd8 {}'.format(
                fmt_num(valid), fmt_num(valid * 2)),
        })

    if has_liquidated and has_deposit:
        out.append({
            'name': '\u8fdd\u7ea6\u91d1\u4e0e\u5b9a\u91d1\u5e76\u7528',
            'result': '\u5b58\u7591',
            'detail': '\u65e2\u7ea6\u5b9a\u8fdd\u7ea6\u91d1\u53c8\u7ea6\u5b9a\u5b9a\u91d1\u7684\uff0c\u4e00\u65b9\u8fdd\u7ea6\u65f6\u5bf9\u65b9\u53ef\u4ee5\u9009\u62e9\u9002\u7528\u8fdd\u7ea6\u91d1\u6216\u8005\u5b9a\u91d1\u6761\u6b3e\uff0c'
                      '\u4e00\u822c\u4e0d\u80fd\u540c\u65f6\u4e3b\u5f20\uff0c\u5efa\u8bae\u62e9\u4e00',
        })
    return out


def fmt_num(v):
    if v is None:
        return ''
    if float(v).is_integer():
        return '{:,.0f}'.format(float(v))
    return '{:,.2f}'.format(float(v))


def review(text, amount=None, liquidated=None, loss=None, deposit=None):
    must, sug = clauses_hit(text)
    risks = risks_hit(text)
    money = money_checks(amount, liquidated, loss, deposit, text)
    missing = [m['name'] for m in must if m['result'] == '\u7f3a']
    if missing:
        verdict = '\u5fc5\u5907\u6761\u6b3e\u7f3a\u5931 {} \u9879\uff0c\u9700\u8865\u6b63'.format(len(missing))
    elif risks or any(m['result'] == '\u5b58\u7591' for m in money):
        verdict = '\u6761\u6b3e\u57fa\u672c\u9f50\u5168\uff0c\u4f46\u5b58\u5728\u9700\u91cd\u70b9\u8c08\u5224\u7684\u98ce\u9669\u9879'
    else:
        verdict = '\u5fc5\u5907\u6761\u6b3e\u9f50\u5168\uff0c\u672a\u53d1\u73b0\u9ad8\u98ce\u9669\u6761\u6b3e'
    return {
        'must': must,
        'suggest': sug,
        'risks': risks,
        'money': money,
        'missing': missing,
        'missing_suggest': [s['name'] for s in sug if s['result'] == '\u7f3a'],
        'verdict': verdict,
    }


def render_md(r):
    out = []
    out.append('# \u5408\u540c\u6761\u6b3e\u5ba1\u67e5\u7ed3\u679c')
    out.append('')
    out.append('- \u7ed3\u8bba\uff1a{}'.format(r['verdict']))
    out.append('')
    out.append('## \u4e00\u3001\u5fc5\u5907\u6761\u6b3e')
    out.append('')
    out.append('| \u6761\u6b3e | \u6709\u65e0 | \u8bf4\u660e |')
    out.append('|---|---|---|')
    for m in r['must']:
        out.append('| {} | {} | {} |'.format(m['name'], m['result'], m['detail']))
    out.append('')
    out.append('## \u4e8c\u3001\u5efa\u8bae\u6761\u6b3e')
    out.append('')
    out.append('| \u6761\u6b3e | \u6709\u65e0 | \u8bf4\u660e |')
    out.append('|---|---|---|')
    for s in r['suggest']:
        out.append('| {} | {} | {} |'.format(s['name'], s['result'], s['detail']))
    out.append('')
    out.append('## \u4e09\u3001\u9ad8\u98ce\u9669\u6761\u6b3e')
    out.append('')
    if not r['risks']:
        out.append('\u672a\u68c0\u7d22\u5230\u9ad8\u98ce\u9669\u6761\u6b3e\u8868\u8ff0\uff08\u4e0d\u4ee3\u8868\u4e0d\u5b58\u5728\uff0c\u9700\u4eba\u5de5\u901a\u8bfb\u786e\u8ba4\uff09\u3002')
        out.append('')
    else:
        out.append('| \u98ce\u9669\u6761\u6b3e | \u547d\u4e2d\u8868\u8ff0 | \u5efa\u8bae |')
        out.append('|---|---|---|')
        for k in r['risks']:
            out.append('| {} | {} | {} |'.format(k['name'], '\u3001'.join(k['keywords']), k['advice']))
        out.append('')
    out.append('## \u56db\u3001\u8fdd\u7ea6\u91d1\u4e0e\u5b9a\u91d1\u6d4b\u7b97')
    out.append('')
    if not r['money']:
        out.append('\u672a\u63d0\u4f9b\u91d1\u989d\u53c2\u6570\uff0c\u672a\u505a\u6d4b\u7b97\u3002\u53ef\u4f20\u5165 --amount / --liquidated / --loss / --deposit\u3002')
        out.append('')
    else:
        out.append('| \u9879\u76ee | \u7ed3\u8bba | \u8bf4\u660e |')
        out.append('|---|---|---|')
        for m in r['money']:
            out.append('| {} | {} | {} |'.format(m['name'], m['result'], m['detail']))
        out.append('')
    out.append('## \u4e94\u3001\u63d0\u9192')
    out.append('')
    out.append('1. \u811a\u672c\u53ea\u505a\u5173\u952e\u8bcd\u68c0\u7d22\uff0c\u547d\u4e2d\u4e0d\u7b49\u4e8e\u6761\u6b3e\u5408\u89c4\uff0c\u7f3a\u9879\u4e5f\u4e0d\u7b49\u4e8e\u5408\u540c\u65e0\u6548\uff0c\u5fc5\u987b\u4eba\u5de5\u901a\u8bfb\u590d\u6838\u3002')
    out.append('2. \u8fdd\u7ea6\u91d1\u8c03\u6574\u7684 30% \u662f\u901a\u884c\u53c2\u7167\u53e3\u5f84\uff0c\u4e0d\u662f\u786c\u6027\u516c\u5f0f\uff0c\u4e2a\u6848\u4f1a\u7efc\u5408\u5c65\u884c\u7a0b\u5ea6\u3001\u8fc7\u9519\u4e0e\u9884\u671f\u5229\u76ca\u3002')
    out.append('3. \u5b9a\u91d1\u4e0d\u5f97\u8d85\u8fc7\u4e3b\u5408\u540c\u6807\u7684\u989d\u7684 20%\uff0c\u8d85\u8fc7\u90e8\u5206\u4e0d\u4ea7\u751f\u5b9a\u91d1\u6548\u529b\u3002')
    out.append('4. \u8fdd\u7ea6\u91d1\u4e0e\u5b9a\u91d1\u4e00\u822c\u53ea\u80fd\u62e9\u4e00\u9002\u7528\u3002')
    out.append('5. \u672c\u6280\u80fd\u4e0d\u4ee3\u66ff\u5f8b\u5e08\u7684\u4e13\u4e1a\u6cd5\u5f8b\u610f\u89c1\uff0c\u6d89\u53ca\u91cd\u5927\u91d1\u989d\u6216\u590d\u6742\u4ea4\u6613\u5e94\u54a8\u8be2\u6267\u4e1a\u5f8b\u5e08\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    full = ('\u7532\u65b9\uff1a\u67d0\u67d0\u516c\u53f8 \u4e59\u65b9\uff1a\u67d0\u67d0\u516c\u53f8 \u6807\u7684\u7269\u4e3a\u8bbe\u5907\uff0c\u6570\u91cf 10 \u53f0\uff0c\u8d28\u91cf\u5e94\u7b26\u5408\u56fd\u5bb6\u6807\u51c6\uff0c'
            '\u4ef7\u6b3e 1000000 \u5143\uff0c\u5c65\u884c\u671f\u9650 30 \u65e5\uff0c\u4ea4\u4ed8\u5730\u70b9\u4e3a\u4e59\u65b9\u4ed3\u5e93\uff0c\u8fd0\u8f93\u65b9\u5f0f\u6c7d\u8fd0\uff0c'
            '\u8fdd\u7ea6\u8d23\u4efb\uff1a\u903e\u671f\u4ea4\u4ed8\u6309\u65e5\u652f\u4ed8\u8fdd\u7ea6\u91d1\uff0c\u4e89\u8bae\u63d0\u4ea4\u67d0\u67d0\u4ef2\u88c1\u59d4\u5458\u4f1a\u4ef2\u88c1\uff0c'
            '\u4e0d\u53ef\u6297\u529b\uff0c\u9a8c\u6536\uff0c\u4fdd\u5bc6\uff0c\u77e5\u8bc6\u4ea7\u6743\u5f52\u7532\u65b9\uff0c\u901a\u77e5\u4e0e\u9001\u8fbe\uff0c\u89e3\u9664')

    r1 = review(full)
    eq('case1 \u5b8c\u6574\u5408\u540c\u65e0\u7f3a\u5931', r1['missing'], [])
    eq('case1 \u7ed3\u8bba', r1['verdict'], '\u5fc5\u5907\u6761\u6b3e\u9f50\u5168\uff0c\u672a\u53d1\u73b0\u9ad8\u98ce\u9669\u6761\u6b3e')

    poor = '\u7532\u65b9\u67d0\u67d0\u516c\u53f8 \u4e59\u65b9\u67d0\u67d0\u516c\u53f8 \u4ef7\u6b3e 100 \u5143'
    r2 = review(poor)
    eq('case2 \u7f3a\u5931\u5fc5\u5907\u6761\u6b3e', len(r2['missing']) > 0, True)
    eq('case2 \u7ed3\u8bba\u542b\u7f3a\u5931', '\u7f3a\u5931' in r2['verdict'], True)

    r3 = review(full + ' \u7532\u65b9\u6709\u6743\u968f\u65f6\u8c03\u6574\u4ef7\u683c\uff0c\u4e59\u65b9\u6982\u4e0d\u8d1f\u8d23\uff0c\u672c\u5408\u540c\u81ea\u52a8\u7eed\u7ea6\u4e00\u5e74')
    names3 = [k['name'] for k in r3['risks']]
    eq('case3 \u5355\u65b9\u53d8\u66f4\u6743\u547d\u4e2d', '\u5355\u65b9\u53d8\u66f4\u6743' in names3, True)
    eq('case3 \u65e0\u9650\u514d\u8d23\u547d\u4e2d', '\u65e0\u9650\u514d\u8d23' in names3, True)
    eq('case3 \u81ea\u52a8\u7eed\u7ea6\u547d\u4e2d', '\u81ea\u52a8\u7eed\u7ea6' in names3, True)

    r4 = review(full.replace('\u67d0\u67d0\u4ef2\u88c1\u59d4\u5458\u4f1a', '\u5f53\u5730'))
    names4 = [k['name'] for k in r4['risks']]
    eq('case4 \u4ef2\u88c1\u6761\u6b3e\u4e0d\u660e\u786e\u547d\u4e2d', '\u4ef2\u88c1\u6761\u6b3e\u4e0d\u660e\u786e' in names4, True)

    m1 = money_checks(1000000, 500000, 200000, None, '')
    eq('case5 \u8fdd\u7ea6\u91d1\u8fc7\u5206\u9ad8\u4e8e', m1[0]['result'], '\u5b58\u7591')
    eq('case5 \u500d\u6570\u5224\u65ad', '2.5' in m1[0]['detail'], True)

    m2 = money_checks(1000000, 100000, 200000, None, '')
    eq('case6 \u8fdd\u7ea6\u91d1\u4f4e\u4e8e\u635f\u5931', m2[0]['result'], '\u5b58\u7591')

    m3 = money_checks(1000000, 220000, 200000, None, '')
    eq('case7 \u8fdd\u7ea6\u91d1\u5728\u5408\u7406\u533a\u95f4', m3[0]['result'], '\u7b26\u5408')

    m4 = money_checks(1000000, None, None, 300000, '')
    eq('case8 \u5b9a\u91d1\u8d8520%', m4[0]['result'], '\u5b58\u7591')
    eq('case8 \u4e0a\u9650\u63d0\u793a', '200,000' in m4[0]['detail'], True)

    m5 = money_checks(1000000, None, None, 100000, '')
    eq('case9 \u5b9a\u91d1\u672a\u8d85\u4e0a\u9650', m5[0]['result'], '\u7b26\u5408')

    m6 = money_checks(1000000, 50000, None, 100000, '\u672c\u5408\u540c\u7ea6\u5b9a\u5b9a\u91d1')
    names6 = [x['name'] for x in m6]
    eq('case10 \u8fdd\u7ea6\u91d1\u4e0e\u5b9a\u91d1\u5e76\u7528\u63d0\u793a', '\u8fdd\u7ea6\u91d1\u4e0e\u5b9a\u91d1\u5e76\u7528' in names6, True)

    r5 = review('\u7532\u65b9 \u4e59\u65b9 \u6807\u7684 \u6570\u91cf \u8d28\u91cf \u4ef7\u6b3e \u671f\u9650 \u5730\u70b9 \u8fdd\u7ea6\u8d23\u4efb \u4ef2\u88c1')
    eq('case11 \u7f3a\u9001\u8fbe\u5efa\u8bae\u6761\u6b3e', '\u901a\u77e5\u4e0e\u9001\u8fbe' in r5['missing_suggest'], True)
    eq('case11 \u7f3a\u4e0d\u53ef\u6297\u529b\u5efa\u8bae\u6761\u6b3e', '\u4e0d\u53ef\u6297\u529b' in r5['missing_suggest'], True)
    eq('case11 \u5fc5\u5907\u6761\u6b3e\u9f50\u5168', r5['missing'], [])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 13\n\u8986\u76d6: \u5fc5\u5907\u6761\u6b3e\u9f50\u5168/\u7f3a\u5931\u5224\u5b9a/\u5355\u65b9\u53d8\u66f4\u6743/\u65e0\u9650\u514d\u8d23/\u81ea\u52a8\u7eed\u7ea6/'
               '\u4ef2\u88c1\u6761\u6b3e\u4e0d\u660e\u786e/\u8fdd\u7ea6\u91d1\u8fc7\u9ad8\u8fc7\u4f4e\u4e0e\u5408\u7406\u533a\u95f4/\u5b9a\u91d120%\u4e0a\u9650/\u8fdd\u7ea6\u91d1\u4e0e\u5b9a\u91d1\u62e9\u4e00/\u5efa\u8bae\u6761\u6b3e')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u5408\u540c\u6761\u6b3e\u5ba1\u67e5\u4e0e\u8fdd\u7ea6\u6551\u6d4e\u6d4b\u7b97')
    ap.add_argument('--file', help='\u5408\u540c\u6587\u672c\u6587\u4ef6\u8def\u5f84\uff08.txt / .md\uff09')
    ap.add_argument('--amount', type=float, help='\u5408\u540c\u6807\u7684\u989d')
    ap.add_argument('--liquidated', type=float, help='\u7ea6\u5b9a\u8fdd\u7ea6\u91d1\u6570\u989d')
    ap.add_argument('--loss', type=float, help='\u5b9e\u9645\u635f\u5931\u6570\u989d')
    ap.add_argument('--deposit', type=float, help='\u7ea6\u5b9a\u5b9a\u91d1\u6570\u989d')
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
    r = review(text, args.amount, args.liquidated, args.loss, args.deposit)
    out = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
