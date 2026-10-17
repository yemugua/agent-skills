#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u96c5\u601d\u5199\u4f5c\u56db\u9879\u8bc4\u5206\u6807\u51c6\u5bf9\u7167\u3001\u5b57\u6570\u4e0e\u65f6\u95f4\u6838\u67e5\u3001\u76ee\u6807\u5206\u5dee\u8ddd\u6d4b\u7b97\u3002

\u7528\u6cd5:
  python ielts_writing_check.py --task 2 --words 268 --minutes 41 --tr 6 --cc 6.5 --lr 6 --gra 6 --target 7
  python ielts_writing_check.py --task 1 --words 175 --minutes 20 --tr 6 --cc 6 --lr 6 --gra 6
  python ielts_writing_check.py --selftest

\u53c2\u6570:
  --task     1 \u6216 2\uff0c\u9ed8\u8ba4 2
  --words    \u5b9e\u9645\u5b57\u6570
  --minutes  \u5b9e\u9645\u7528\u65f6\uff08\u5206\u949f\uff09
  --tr/--cc/--lr/--gra  \u56db\u9879\u81ea\u8bc4\u6863\u4f4d 0~9\uff0c\u53ef\u5e26 .5
  --target   \u76ee\u6807\u5199\u4f5c\u5355\u9879\u5206\uff0c\u9ed8\u8ba4 7.0
  --out      \u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84
  --format   md\uff08\u9ed8\u8ba4\uff09\u6216 json
  --selftest \u8fd0\u884c\u5185\u7f6e\u81ea\u68c0
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

TASK_SPEC = {
    1: {'name': 'Task 1', 'min_words': 150, 'advice': (170, 190), 'budget': 20,
        'weight': '\u7ea6 1/3', 'tr_label': 'TA\uff08\u4efb\u52a1\u5b8c\u6210\u5ea6\uff09'},
    2: {'name': 'Task 2', 'min_words': 250, 'advice': (270, 300), 'budget': 40,
        'weight': '\u7ea6 2/3', 'tr_label': 'TR\uff08\u4efb\u52a1\u56de\u5e94\uff09'},
}
CRITERIA = [
    ('tr', 'TR / TA', '\u4efb\u52a1\u56de\u5e94\u4e0e\u4efb\u52a1\u5b8c\u6210\u5ea6'),
    ('cc', 'CC', '\u8fde\u8d2f\u4e0e\u8854\u63a5'),
    ('lr', 'LR', '\u8bcd\u6c47\u8d44\u6e90'),
    ('gra', 'GRA', '\u8bed\u6cd5\u591a\u6837\u6027\u4e0e\u51c6\u786e\u6027'),
]
BANDS = [4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
DESC = {
    'tr': {
        9: '\u5168\u9762\u5145\u5206\u56de\u5e94\u6240\u6709\u8981\u6c42\uff0c\u7acb\u573a\u6e05\u6670\u4e14\u8d2f\u7a7f\u5168\u6587\uff0c\u8bba\u8bc1\u6df1\u5165',
        8: '\u5145\u5206\u56de\u5e94\u6240\u6709\u8981\u6c42\uff0c\u7acb\u573a\u4e00\u8d2f\uff0c\u8bba\u8bc1\u5c55\u5f00\u5145\u5206',
        7: '\u56de\u5e94\u4e86\u6240\u6709\u8981\u6c42\uff0c\u7acb\u573a\u6e05\u6670\uff0c\u4e3b\u8981\u8bba\u70b9\u6709\u5c55\u5f00\u4e0e\u652f\u6301',
        6: '\u56de\u5e94\u4e86\u5404\u9879\u8981\u6c42\u4f46\u90e8\u5206\u5c55\u5f00\u4e0d\u8db3\uff0c\u7acb\u573a\u53ef\u8fa8\u4f46\u7ed3\u8bba\u4e0d\u6e05',
        5: '\u53ea\u56de\u5e94\u4e86\u90e8\u5206\u8981\u6c42\uff0c\u7acb\u573a\u53d1\u5c55\u4e0d\u6e05\uff0c\u4f8b\u8bc1\u6709\u9650',
        4: '\u5185\u5bb9\u4e0e\u9898\u76ee\u5173\u8054\u5f31\uff0c\u51e0\u4e4e\u6ca1\u6709\u7acb\u573a',
    },
    'cc': {
        9: '\u8854\u63a5\u6781\u81ea\u7136\uff0c\u5206\u6bb5\u5b8c\u5168\u5408\u7406\uff0c\u6307\u4ee3\u624b\u6bb5\u5145\u5206',
        8: '\u903b\u8f91\u63a8\u8fdb\u987a\u7545\uff0c\u5206\u6bb5\u6070\u5f53\uff0c\u8854\u63a5\u624b\u6bb5\u591a\u6837\u4e14\u51c6\u786e',
        7: '\u6709\u6e05\u6670\u7684\u603b\u4f53\u63a8\u8fdb\uff0c\u5206\u6bb5\u5408\u7406\uff0c\u8854\u63a5\u8bcd\u5076\u6709\u8fc7\u91cf',
        6: '\u603b\u4f53\u4e0a\u80fd\u770b\u61c2\uff0c\u5206\u6bb5\u6709\u903b\u8f91\u4f46\u4e0d\u4e00\u8d2f\uff0c\u8854\u63a5\u624b\u6bb5\u6709\u9650',
        5: '\u7ec4\u7ec7\u677e\u6563\u7f3a\u4e4f\u63a8\u8fdb\uff0c\u5206\u6bb5\u6df7\u4e71\uff0c\u8854\u63a5\u624b\u6bb5\u5c11\u4e14\u91cd\u590d',
        4: '\u57fa\u672c\u6ca1\u6709\u903b\u8f91\u7ec4\u7ec7\uff0c\u770b\u4e0d\u5230\u5206\u6bb5\u610f\u56fe',
    },
    'lr': {
        9: '\u7528\u8bcd\u7cbe\u51c6\u5730\u9053\u591a\u6837\uff0c\u642d\u914d\u81ea\u7136\uff0c\u5076\u6709\u7b14\u8bef',
        8: '\u8bcd\u6c47\u91cf\u5927\u4e14\u7075\u6d3b\uff0c\u80fd\u7528\u4f4e\u9891\u8bcd\uff0c\u5076\u6709\u642d\u914d\u4e0d\u81ea\u7136',
        7: '\u8bcd\u6c47\u8db3\u591f\u7075\u6d3b\u51c6\u786e\uff0c\u80fd\u4f7f\u7528\u4e00\u4e9b\u4f4e\u9891\u8bcd\uff0c\u5076\u6709\u642d\u914d\u6216\u62fc\u5199\u9519',
        6: '\u8bcd\u6c47\u91cf\u591f\u5b8c\u6210\u5199\u4f5c\u4efb\u52a1\uff0c\u5c1d\u8bd5\u7528\u4e0d\u719f\u6089\u7684\u8bcd\u4f46\u4e0d\u51c6',
        5: '\u8bcd\u6c47\u6709\u9650\uff0c\u91cd\u590d\u4e25\u91cd\uff0c\u62fc\u5199\u4e0e\u6784\u8bcd\u9519\u8bef\u660e\u663e',
        4: '\u53ea\u638c\u63e1\u57fa\u7840\u8bcd\u6c47\uff0c\u9519\u8bef\u9891\u7e41\u5f71\u54cd\u7406\u89e3',
    },
    'gra': {
        9: '\u53e5\u578b\u6781\u5176\u591a\u6837\u4e14\u5b8c\u5168\u51c6\u786e\uff0c\u6807\u70b9\u5b8c\u5168\u6b63\u786e',
        8: '\u53e5\u578b\u591a\u6837\uff0c\u591a\u6570\u53e5\u5b50\u65e0\u8bef\uff0c\u6807\u70b9\u57fa\u672c\u6b63\u786e',
        7: '\u53e5\u578b\u6709\u53d8\u5316\u4e14\u590d\u6742\u5ea6\u4e0d\u9519\uff0c\u591a\u6570\u53e5\u5b50\u65e0\u9519',
        6: '\u7b80\u5355\u53e5\u4e0e\u590d\u6742\u53e5\u6df7\u7528\u4f46\u7075\u6d3b\u6027\u6709\u9650\uff0c\u590d\u6742\u53e5\u9519\u8bef\u8f83\u591a',
        5: '\u53e5\u578b\u5355\u4e00\u591a\u4e3a\u7b80\u5355\u53e5\uff0c\u9519\u8bef\u9891\u7e41',
        4: '\u53ea\u4f1a\u7528\u6781\u5c11\u6570\u53e5\u578b\uff0c\u9519\u8bef\u6781\u591a\u96be\u4ee5\u7406\u89e3',
    },
}
UPGRADE = {
    'tr': '\u6bcf\u4e2a\u8bba\u70b9\u5c55\u5f00\u5230\u300c\u4e3a\u4ec0\u4e48\u300d\uff0c\u5e76\u56de\u6263\u7acb\u573a\u53e5',
    'cc': '\u4e00\u6bb5\u4e00\u4e2a\u4e2d\u5fc3\u53e5\uff0c\u6bcf\u6bb5\u8854\u63a5\u8bcd\u4e0d\u8d85\u8fc7 2 \u4e2a',
    'lr': '\u6838\u5fc3\u8bcd\u5168\u6587\u91cd\u590d\u4e0d\u8d85\u8fc7 4 \u6b21\uff0c\u66ff\u6362\u524d\u5148\u786e\u8ba4\u642d\u914d',
    'gra': '\u6bcf\u7bc7\u81f3\u5c11\u7528 3 \u79cd\u4ece\u53e5\uff0c\u4e00\u53e5\u4e0d\u8d85\u8fc7\u4e24\u4e2a\u4ece\u53e5',
}
PRIORITY_RULE = [
    (5.5, 'gra', 'GRA \u504f\u4f4e\uff0c\u5148\u8865\u53e5\u5b50\u6b63\u786e\u6027\uff08\u4e3b\u8c13\u4e00\u81f4\u3001\u65f6\u6001\u3001\u5355\u590d\u6570\uff09'),
    (5.5, 'tr', 'TR \u504f\u4f4e\uff0c\u5148\u7ec3\u5ba1\u9898\u4e0e\u63d0\u7eb2\uff0c\u4e0d\u8981\u5237\u5957\u9898'),
]


def nearest_band(band):
    """\u5411\u4e0b\u53d6\u5230\u5df2\u6536\u5f55\u7684\u6863\u4f4d\uff08\u7528\u4e8e\u5339\u914d\u5206\u6863\u63cf\u8ff0\uff09\u3002"""
    cur = 4.0
    for b in BANDS:
        if band + 1e-9 >= b:
            cur = b
    return cur


def round_half(x):
    """\u53d6\u5230\u6700\u8fd1\u7684 0.5 \u6863\uff0c.25 \u4e0e .75 \u5411\u4e0a\u53d6\u3002"""
    import math
    return math.floor(x * 2 + 0.5 + 1e-9) / 2.0


def word_check(task, words):
    spec = TASK_SPEC[task]
    lo, hi = spec['advice']
    if words is None:
        return {'result': '\u5f85\u8865\u5145', 'detail': '\u672a\u586b\u5b57\u6570\uff0c\u65e0\u6cd5\u5224\u5b9a', 'advice': ''}
    if words < spec['min_words']:
        return {'result': '\u4e0d\u7b26\u5408',
                'detail': '\u4f4e\u4e8e\u4e0b\u9650 %d \u8bcd\uff0c\u5dee %d \u8bcd' % (spec['min_words'], spec['min_words'] - words),
                'advice': '\u5b57\u6570\u4e0d\u8fbe\u6807\u4f1a\u9650\u5236\u6863\u4f4d\u4e0a\u9650\uff0c\u5148\u7ec3\u63d0\u7eb2\u6269\u5199'}
    if words > hi * 1.5:
        return {'result': '\u9700\u5173\u6ce8',
                'detail': '%d \u8bcd\uff0c\u8d85\u8fc7\u5efa\u8bae\u533a\u95f4 %d~%d \u8f83\u591a' % (words, lo, hi),
                'advice': '\u8d85\u5b57\u6570\u4e0d\u52a0\u5206\uff0c\u4f1a\u6324\u5360\u68c0\u67e5\u65f6\u95f4\u5e76\u589e\u52a0\u9519\u8bef'}
    if words > hi:
        return {'result': '\u7b26\u5408',
                'detail': '%d \u8bcd\uff0c\u8fbe\u5230\u4e0b\u9650\u4f46\u9ad8\u4e8e\u5efa\u8bae\u533a\u95f4 %d~%d' % (words, lo, hi),
                'advice': '\u5efa\u8bae\u56de\u5230 %d~%d \u8bcd\uff0c\u7559\u51fa\u68c0\u67e5\u65f6\u95f4' % (lo, hi)}
    return {'result': '\u7b26\u5408',
            'detail': '%d \u8bcd\uff0c\u8fbe\u5230\u4e0b\u9650\u4e14\u5728\u5efa\u8bae\u533a\u95f4 %d~%d' % (words, lo, hi),
            'advice': '\u4fdd\u6301'}


def time_check(task, minutes):
    spec = TASK_SPEC[task]
    if minutes is None:
        return {'result': '\u5f85\u8865\u5145', 'detail': '\u672a\u586b\u7528\u65f6', 'advice': ''}
    if minutes > spec['budget'] + 5:
        return {'result': '\u4e0d\u7b26\u5408',
                'detail': '\u7528\u65f6 %d \u5206\u949f\uff0c\u8d85\u9884\u7b97 %d \u5206\u949f\u4ee5\u4e0a' % (minutes, spec['budget']),
                'advice': '\u538b\u7f29\u5ba1\u9898\u4e0e\u5199\u4f5c\u65f6\u95f4\uff0c\u5fc5\u987b\u7559\u51fa 3~5 \u5206\u949f\u68c0\u67e5'}
    if minutes > spec['budget']:
        return {'result': '\u9700\u5173\u6ce8',
                'detail': '\u7528\u65f6 %d \u5206\u949f\uff0c\u6bd4\u9884\u7b97 %d \u5206\u949f\u591a %d \u5206\u949f' % (minutes, spec['budget'], minutes - spec['budget']),
                'advice': '\u68c0\u67e5\u65f6\u95f4\u88ab\u6324\u5360\u662f\u5206\u6570\u4e0a\u4e0d\u53bb\u7684\u5e38\u89c1\u539f\u56e0'}
    return {'result': '\u7b26\u5408',
            'detail': '\u7528\u65f6 %d \u5206\u949f\uff0c\u9884\u7b97 %d \u5206\u949f' % (minutes, spec['budget']),
            'advice': '\u4fdd\u6301'}


def priority_of(scores):
    """\u6309\u56db\u9879\u5206\u6570\u7ed9\u51fa\u63d0\u5206\u987a\u5e8f\u3002"""
    items = []
    for key, label, _ in CRITERIA:
        v = scores.get(key)
        if v is None:
            continue
        items.append((v, key, label))
    if not items:
        return []
    items.sort()
    lowest_v, lowest_key, lowest_label = items[0]
    out = []
    for floor, key, text in PRIORITY_RULE:
        if lowest_key == key and lowest_v <= floor:
            out.append(text)
            break
    if not out:
        if lowest_key == 'tr':
            out.append('TR \u6700\u4f4e\uff0c\u5148\u7ec3\u5ba1\u9898\u4e0e\u63d0\u7eb2\u6269\u5199')
        elif lowest_key == 'cc':
            out.append('CC \u6700\u4f4e\uff0c\u5148\u4fee\u5206\u6bb5\u4e0e\u8854\u63a5\u624b\u6bb5')
        elif lowest_key == 'lr':
            out.append('LR \u6700\u4f4e\uff0c\u5148\u8865\u8bdd\u9898\u8bcd\u6c47\u4e0e\u642d\u914d')
        else:
            out.append('GRA \u6700\u4f4e\uff0c\u5148\u4fee\u53e5\u5b50\u6b63\u786e\u6027\u4e0e\u53e5\u578b\u591a\u6837\u6027')
    out.append('\u6700\u77ed\u677f\uff1a%s\uff08%.1f\uff09\u2014\u2014%s' % (lowest_label, lowest_v, UPGRADE[lowest_key]))
    ranked = '\u63d0\u5206\u987a\u5e8f\uff1a' + ' \u2192 '.join('%s(%.1f)' % (lb, v) for v, k, lb in items)
    out.append(ranked)
    if max(v for v, k, lb in items) - lowest_v >= 1.5:
        out.append('\u56db\u9879\u5206\u5dee\u8fbe\u5230 1.5 \u6863\u4ee5\u4e0a\uff0c\u5c5e\u4e8e\u5355\u9879\u77ed\u677f\uff0c\u96c6\u4e2d\u7ec3\u6700\u77ed\u677f\u800c\u4e0d\u662f\u6574\u5957\u5237')
    return out


def check(args):
    task = args.task
    spec = TASK_SPEC[task]
    scores = {'tr': args.tr, 'cc': args.cc, 'lr': args.lr, 'gra': args.gra}
    items = []
    for key, label, full in CRITERIA:
        v = scores.get(key)
        if v is None:
            items.append({'name': label, 'full': full, 'band': None,
                          'result': '\u5f85\u8865\u5145', 'detail': '\u672a\u586b\u81ea\u8bc4\u6863\u4f4d', 'upgrade': UPGRADE[key]})
            continue
        nb = nearest_band(v)
        if v + 1e-9 >= 7.0:
            res = '\u7b26\u5408'
        elif v + 1e-9 >= 6.0:
            res = '\u9700\u5173\u6ce8'
        else:
            res = '\u4e0d\u7b26\u5408'
        detail = '\u81ea\u8bc4 %.1f\uff0c\u5bf9\u5e94 %s \u6863\uff1a%s' % (v, '%.0f' % nb, DESC[key][nb])
        items.append({'name': label, 'full': full, 'band': v, 'result': res,
                      'detail': detail, 'upgrade': UPGRADE[key]})
    items.append({'name': '\u5b57\u6570', 'full': '\u4f5c\u6587\u5b57\u6570\u6838\u67e5', 'band': None,
                  'result': word_check(task, args.words)['result'],
                  'detail': word_check(task, args.words)['detail'],
                  'upgrade': word_check(task, args.words)['advice']})
    items.append({'name': '\u7528\u65f6', 'full': '\u5199\u4f5c\u7528\u65f6\u6838\u67e5', 'band': None,
                  'result': time_check(task, args.minutes)['result'],
                  'detail': time_check(task, args.minutes)['detail'],
                  'upgrade': time_check(task, args.minutes)['advice']})

    known = [scores[k] for k in ('tr', 'cc', 'lr', 'gra') if scores.get(k) is not None]
    overall = None
    if len(known) == 4:
        overall = round_half(sum(known) / 4.0)
    target = args.target
    gap = None
    if overall is not None and target is not None:
        gap = round(target - overall, 2)

    if len(known) < 4:
        verdict = '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4'
    elif gap is not None and gap <= 0:
        verdict = '\u8fbe\u5230\u76ee\u6807'
    elif gap is not None and gap <= 0.5:
        verdict = '\u63a5\u8fd1\u76ee\u6807'
    else:
        verdict = '\u672a\u8fbe\u76ee\u6807'

    return {'task': spec['name'], 'weight': spec['weight'],
            'tr_label': spec['tr_label'], 'items': items,
            'overall': overall, 'target': target, 'gap': gap,
            'verdict': verdict,
            'priority': priority_of(scores)}


def render_md(r):
    lines = []
    lines.append('# \u96c5\u601d\u5199\u81ea\u67e5\u7ed3\u679c\uff1a%s' % r['task'])
    lines.append('')
    lines.append('- \u5199\u4f5c\u5355\u9879\u6743\u91cd\uff1a%s' % r['weight'])
    lines.append('- \u4efb\u52a1\u56de\u5e94\u9879\uff1a%s' % r['tr_label'])
    if r['overall'] is not None:
        lines.append('- \u56db\u9879\u6298\u7b97\u5355\u9879\u5206\uff1a**%.1f**\uff08\u76ee\u6807 %.1f\uff0c\u5dee %+.1f\uff09' % (r['overall'], r['target'], r['gap']))
    lines.append('- \u5224\u5b9a\uff1a**%s**' % r['verdict'])
    lines.append('')
    lines.append('| \u6838\u67e5\u9879 | \u5224\u5b9a | \u8bf4\u660e | \u5347\u6863\u52a8\u4f5c |')
    lines.append('|---|---|---|---|')
    for it in r['items']:
        up = it['upgrade'] or '\u2014'
        lines.append('| %s | %s | %s | %s |' % (it['name'], it['result'], it['detail'], up))
    lines.append('')
    if r['priority']:
        lines.append('## \u63d0\u5206\u4f18\u5148\u7ea7')
        lines.append('')
        for p in r['priority']:
            lines.append('- %s' % p)
        lines.append('')
    lines.append('> \u6298\u7b97\u5206\u662f\u6309\u56db\u9879\u5e73\u5747\u7684\u4f30\u7b97\uff0c\u5b98\u65b9\u7531\u4e24\u540d\u9605\u5377\u5458\u72ec\u7acb\u8bc4\u5206\uff0c\u4ee5\u5b98\u65b9\u6210\u7ee9\u5355\u4e3a\u51c6\u3002')
    return '\n'.join(lines)


def selftest():
    errors = []

    def mk(**kw):
        a = argparse.Namespace(task=2, words=None, minutes=None, tr=None, cc=None,
                               lr=None, gra=None, target=7.0)
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    def item(r, name):
        for i in r['items']:
            if i['name'] == name:
                return i
        return None

    eq('case01 \u6298\u7b97\u5206 6,6.5,6,6 -> 6.0',
       check(mk(tr=6.0, cc=6.5, lr=6.0, gra=6.0))['overall'], 6.0)
    eq('case02 \u6298\u7b97\u5206 6,6.5,7,6.5 -> 6.5',
       check(mk(tr=6.0, cc=6.5, lr=7.0, gra=6.5))['overall'], 6.5)
    eq('case03 \u6298\u7b97\u5206 6.25 \u5e73\u5747 -> 6.5',
       check(mk(tr=6.0, cc=6.5, lr=6.0, gra=6.5))['overall'], 6.5)
    eq('case04 \u6298\u7b97\u5206 \u56db\u9879 7 -> 7.0',
       check(mk(tr=7.0, cc=7.0, lr=7.0, gra=7.0))['overall'], 7.0)
    eq('case05 \u76ee\u6807\u5dee\u8ddd 6.0 vs 7.0 -> 1.0',
       check(mk(tr=6.0, cc=6.0, lr=6.0, gra=6.0))['gap'], 1.0)
    eq('case06 Task2 230 \u8bcd\u4e0d\u8db3',
       item(check(mk(task=2, words=230)), '\u5b57\u6570')['result'], '\u4e0d\u7b26\u5408')
    eq('case07 Task2 268 \u8bcd\u8fbe\u6807',
       item(check(mk(task=2, words=268)), '\u5b57\u6570')['result'], '\u7b26\u5408')
    eq('case08 Task1 140 \u8bcd\u4e0d\u8db3',
       item(check(mk(task=1, words=140)), '\u5b57\u6570')['result'], '\u4e0d\u7b26\u5408')
    eq('case09 Task1 175 \u8bcd\u8fbe\u6807',
       item(check(mk(task=1, words=175)), '\u5b57\u6570')['result'], '\u7b26\u5408')
    eq('case10 Task2 500 \u8bcd\u8d85\u6807\u63d0\u793a',
       item(check(mk(task=2, words=500)), '\u5b57\u6570')['result'], '\u9700\u5173\u6ce8')
    eq('case11 Task2 46 \u5206\u949f\u8d85\u65f6',
       item(check(mk(task=2, minutes=46)), '\u7528\u65f6')['result'], '\u4e0d\u7b26\u5408')
    eq('case11b Task2 43 \u5206\u949f\u8f7b\u5fae\u8d85\u65f6',
       item(check(mk(task=2, minutes=43)), '\u7528\u65f6')['result'], '\u9700\u5173\u6ce8')
    eq('case12 Task1 20 \u5206\u949f\u6b63\u5e38',
       item(check(mk(task=1, minutes=20)), '\u7528\u65f6')['result'], '\u7b26\u5408')
    eq('case13 GRA 6.0 \u5224\u9700\u5173\u6ce8',
       item(check(mk(gra=6.0)), 'GRA')['result'], '\u9700\u5173\u6ce8')
    eq('case14 TR 5.0 \u5224\u4e0d\u7b26\u5408',
       item(check(mk(tr=5.0)), 'TR / TA')['result'], '\u4e0d\u7b26\u5408')
    eq('case15 CC 7.0 \u5224\u7b26\u5408',
       item(check(mk(cc=7.0)), 'CC')['result'], '\u7b26\u5408')
    p = check(mk(tr=6.5, cc=6.5, lr=7.0, gra=5.5))['priority']
    eq('case16 GRA 5.5 \u65f6\u4f18\u5148\u7ea7\u4e3a\u53e5\u5b50\u6b63\u786e\u6027',
       p[0], 'GRA \u504f\u4f4e\uff0c\u5148\u8865\u53e5\u5b50\u6b63\u786e\u6027\uff08\u4e3b\u8c13\u4e00\u81f4\u3001\u65f6\u6001\u3001\u5355\u590d\u6570\uff09')
    p2 = check(mk(tr=5.5, cc=6.5, lr=6.0, gra=6.0))['priority']
    eq('case17 TR 5.5 \u65f6\u4f18\u5148\u7ea7\u4e3a\u5ba1\u9898',
       p2[0], 'TR \u504f\u4f4e\uff0c\u5148\u7ec3\u5ba1\u9898\u4e0e\u63d0\u7eb2\uff0c\u4e0d\u8981\u5237\u5957\u9898')
    eq('case18 \u7f3a\u81ea\u8bc4\u65f6\u9700\u8865\u5145\u4fe1\u606f',
       check(mk(tr=6.0))['verdict'], '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4')
    r19 = check(mk(tr=7.0, cc=7.0, lr=7.0, gra=7.0, target=7.0))
    eq('case19 \u8fbe\u6807\u5224\u5b9a', r19['verdict'], '\u8fbe\u5230\u76ee\u6807')
    r20 = check(mk(tr=6.5, cc=6.5, lr=7.0, gra=6.5, target=7.0))
    eq('case20 \u63a5\u8fd1\u76ee\u6807\u5224\u5b9a', r20['verdict'], '\u63a5\u8fd1\u76ee\u6807')
    eq('case21 nearest_band 6.5 -> 6.0', nearest_band(6.5), 6.0)
    eq('case22 nearest_band 9.0 -> 9.0', nearest_band(9.0), 9.0)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 23\n\u8986\u76d6: \u56db\u9879\u6298\u7b97/\u76ee\u6807\u5dee\u8ddd/Task1\u4e0eTask2\u5b57\u6570\u4e0b\u9650\u4e0e\u5efa\u8bae\u533a\u95f4/'
               '\u8d85\u65f6\u5224\u5b9a/\u56db\u9879\u6863\u4f4d\u5224\u5b9a/\u77ed\u677f\u4f18\u5148\u7ea7/\u4fe1\u606f\u7f3a\u5931')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u96c5\u601d\u5199\u4f5c\u8bc4\u5206\u6807\u51c6\u4e0e\u63d0\u5206\u6838\u67e5')
    ap.add_argument('--task', type=int, default=2, choices=[1, 2])
    ap.add_argument('--words', type=int, help='\u5b9e\u9645\u5b57\u6570')
    ap.add_argument('--minutes', type=int, help='\u5b9e\u9645\u7528\u65f6\uff08\u5206\u949f\uff09')
    ap.add_argument('--tr', type=float, help='TR/TA \u81ea\u8bc4\u6863\u4f4d 0~9')
    ap.add_argument('--cc', type=float, help='CC \u81ea\u8bc4\u6863\u4f4d 0~9')
    ap.add_argument('--lr', type=float, help='LR \u81ea\u8bc4\u6863\u4f4d 0~9')
    ap.add_argument('--gra', type=float, help='GRA \u81ea\u8bc4\u6863\u4f4d 0~9')
    ap.add_argument('--target', type=float, default=7.0, help='\u76ee\u6807\u5199\u4f5c\u5355\u9879\u5206')
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
