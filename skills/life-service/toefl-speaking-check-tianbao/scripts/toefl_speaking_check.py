#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u6258\u798f\u53e3\u8bed\u7b54\u9898\u7ed3\u6784\u6838\u67e5\uff1a\u8981\u70b9\u8986\u76d6\u3001\u4f5c\u7b54\u65f6\u957f\u3001\u4e09\u7ef4\u5ea6\u5b9a\u6863\u4e0e 0~30 \u5206\u4f30\u7b97\u3002

\u7528\u6cd5:
  python toefl_speaking_check.py --task 3 --seconds 58 --points 3 --delivery 3 --language 3 --topic 2
  python toefl_speaking_check.py --task 1 --seconds 44 --points 4 --delivery 3 --language 3 --topic 3
  python toefl_speaking_check.py --selftest

\u53c2\u6570:
  --task      1 / 2 / 3 / 4
  --seconds   \u5b9e\u9645\u4f5c\u7b54\u79d2\u6570
  --points    \u5b9e\u9645\u8986\u76d6\u7684\u8981\u70b9\u4e2a\u6570
  --delivery/--language/--topic  \u4e09\u7ef4\u5ea6\u81ea\u8bc4 0~4 \u6574\u6570
  --target    \u76ee\u6807\u53e3\u8bed\u5206\uff080~30\uff09\uff0c\u9ed8\u8ba4 23
  --out       \u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84
  --format    md\uff08\u9ed8\u8ba4\uff09\u6216 json
  --selftest  \u8fd0\u884c\u5185\u7f6e\u81ea\u68c0
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

TASKS = {
    1: {'name': 'Task 1 \u72ec\u7acb\u9898', 'kind': '\u72ec\u7acb\u9898', 'prep': 15, 'speak': 45,
        'required': 2, 'full': 4,
        'points': ['\u660e\u786e\u7acb\u573a', '\u7406\u7531 1 + \u5177\u4f53\u4f8b\u5b50', '\u7406\u7531 2 + \u5177\u4f53\u4f8b\u5b50', '\u6536\u5c3e\u53e5']},
    2: {'name': 'Task 2 \u6821\u56ed\u60c5\u666f', 'kind': '\u6821\u56ed\u60c5\u666f\uff08\u9605\u8bfb+\u5bf9\u8bdd\uff09', 'prep': 30, 'speak': 60,
        'required': 4, 'full': 4,
        'points': ['\u9605\u8bfb\u5185\u5bb9\u4e00\u53e5\u8bdd\u4ea4\u4ee3', '\u8bf4\u8bdd\u4eba\u6001\u5ea6', '\u7406\u7531 1\uff08\u6765\u81ea\u542c\u529b\uff09', '\u7406\u7531 2\uff08\u6765\u81ea\u542c\u529b\uff09']},
    3: {'name': 'Task 3 \u5b66\u672f\u6982\u5ff5', 'kind': '\u5b66\u672f\u6982\u5ff5\uff08\u9605\u8bfb+\u8bb2\u5ea7\uff09', 'prep': 30, 'speak': 60,
        'required': 3, 'full': 4,
        'points': ['\u6982\u5ff5\u5b9a\u4e49\u4e00\u53e5\u8bdd', '\u6559\u6388\u4e3e\u7684\u4f8b\u5b50', '\u4f8b\u5b50\u5173\u952e\u7ec6\u8282\u4e24\u4e2a', '\u4f8b\u5b50\u4e0e\u6982\u5ff5\u7684\u5bf9\u5e94']},
    4: {'name': 'Task 4 \u5b66\u672f\u8bb2\u5ea7', 'kind': '\u5b66\u672f\u8bb2\u5ea7\uff08\u53ea\u6709\u542c\u529b\uff09', 'prep': 20, 'speak': 60,
        'required': 3, 'full': 4,
        'points': ['\u8bb2\u5ea7\u603b\u4e3b\u9898', '\u5206\u70b9 1 + \u7ec6\u8282', '\u5206\u70b9 2 + \u7ec6\u8282', '\u4e24\u4e2a\u5206\u70b9\u7684\u652f\u6491\u7ec6\u8282']},
}
DIMS = [
    ('delivery', 'Delivery', '\u8868\u8fbe\uff1a\u53d1\u97f3\u662f\u5426\u6e05\u695a\u3001\u8bed\u6d41\u662f\u5426\u8fde\u8d2f'),
    ('language', 'Language Use', '\u8bed\u8a00\u8fd0\u7528\uff1a\u8bed\u6cd5\u4e0e\u7528\u8bcd\u662f\u5426\u81ea\u52a8\u6709\u6548'),
    ('topic', 'Topic Development', '\u5185\u5bb9\u5c55\u5f00\uff1a\u662f\u5426\u5b8c\u6574\u7b54\u9898\u3001\u8981\u70b9\u662f\u5426\u5c55\u5f00'),
]
DIM_DESC = {
    'delivery': {
        4: '\u603b\u4f53\u6e05\u695a\u6d41\u7545\uff0c\u5076\u6709\u53d1\u97f3\u6216\u8bed\u8c03\u95ee\u9898\u4f46\u4e0d\u5f71\u54cd\u7406\u89e3',
        3: '\u603b\u4f53\u6e05\u695a\u5e76\u6709\u4e00\u5b9a\u6d41\u7545\u5ea6\uff0c\u5076\u5c14\u9700\u8981\u542c\u8005\u8d39\u529b',
        2: '\u80fd\u542c\u61c2\u4f46\u6709\u660e\u663e\u95ee\u9898\uff0c\u8bed\u6d41\u65ad\u7eed\uff0c\u542c\u8005\u9700\u8981\u8d39\u529b',
        1: '\u96be\u4ee5\u7406\u89e3\uff0c\u9891\u7e41\u505c\u987f\uff0c\u610f\u601d\u57fa\u672c\u4f20\u8fbe\u4e0d\u51fa',
        0: '\u672a\u4f5c\u7b54\u6216\u4e0e\u9898\u76ee\u65e0\u5173',
    },
    'language': {
        4: '\u8bed\u6cd5\u4e0e\u7528\u8bcd\u81ea\u52a8\u4e14\u6709\u6548\uff0c\u8868\u8fbe\u8fde\u8d2f\uff0c\u5076\u6709\u5c0f\u9519',
        3: '\u57fa\u672c\u81ea\u52a8\u6709\u6548\uff0c\u5076\u6709\u4e0d\u51c6\u786e\u6216\u7528\u8bcd\u53d7\u9650\uff0c\u4e2a\u522b\u5730\u65b9\u5f71\u54cd\u7406\u89e3',
        2: '\u7ed3\u6784\u4e0e\u7528\u8bcd\u8303\u56f4\u6709\u9650\uff0c\u9519\u8bef\u8f83\u591a\uff0c\u9700\u8981\u542c\u8005\u731c\u6d4b',
        1: '\u8868\u8fbe\u624b\u6bb5\u4e25\u91cd\u53d7\u9650\uff0c\u9519\u8bef\u9891\u7e41\uff0c\u610f\u601d\u57fa\u672c\u88ab\u6321\u4f4f',
        0: '\u672a\u4f5c\u7b54\u6216\u4e0e\u9898\u76ee\u65e0\u5173',
    },
    'topic': {
        4: '\u5b8c\u6574\u56de\u5e94\u9898\u76ee\uff0c\u5c55\u5f00\u5145\u5206\uff0c\u89c2\u70b9\u4e4b\u95f4\u5173\u7cfb\u6e05\u695a\uff0c\u4f8b\u5b50\u5177\u4f53',
        3: '\u57fa\u672c\u56de\u5e94\u9898\u76ee\uff0c\u6709\u4e00\u5b9a\u5c55\u5f00\uff0c\u4e2a\u522b\u5173\u7cfb\u4e0d\u591f\u660e\u786e',
        2: '\u90e8\u5206\u56de\u5e94\uff0c\u5c55\u5f00\u6709\u9650\uff0c\u89c2\u70b9\u4e4b\u95f4\u8054\u7cfb\u677e\u6563',
        1: '\u53ea\u89e6\u53ca\u9898\u76ee\u8868\u9762\uff0c\u5185\u5bb9\u57fa\u672c\u6ca1\u6709\u5c55\u5f00',
        0: '\u672a\u4f5c\u7b54\u6216\u4e0e\u9898\u76ee\u65e0\u5173',
    },
}
FIX = {
    'delivery': '\u8ddf\u8bfb\u4e0e\u590d\u8ff0\uff0c\u7ec3\u610f\u7fa4\u8fde\u8bfb\uff0c\u51cf\u5c11\u6bcf\u5206\u949f\u505c\u987f\u6b21\u6570',
    'language': '\u5148\u4fee\u65f6\u6001\u4e0e\u4e3b\u8c13\u4e00\u81f4\uff0c\u518d\u7ec3\u53e5\u578b\u66ff\u6362',
    'topic': '\u6309\u8981\u70b9\u6e05\u5355\u9650\u65f6\u5217\u63d0\u7eb2\uff0c\u6bcf\u4e2a\u4f8b\u5b50\u8865\u4eba\u540d\u3001\u573a\u666f\u3001\u7ed3\u679c',
}


def time_check(task, seconds):
    spec = TASKS[task]
    limit = spec['speak']
    if seconds is None:
        return {'result': '\u5f85\u8865\u5145', 'detail': '\u672a\u586b\u4f5c\u7b54\u79d2\u6570', 'advice': ''}
    if seconds < limit * 0.5:
        return {'result': '\u4e0d\u7b26\u5408',
                'detail': '\u4f5c\u7b54 %d \u79d2\uff0c\u4e0d\u8db3\u89c4\u5b9a %d \u79d2\u7684\u4e00\u534a' % (seconds, limit),
                'advice': '\u65f6\u957f\u4e0d\u8db3\u4f1a\u76f4\u63a5\u538b\u6863\uff0c\u8981\u70b9\u65e0\u6cd5\u5c55\u5f00'}
    if seconds < limit * 0.85:
        return {'result': '\u9700\u5173\u6ce8',
                'detail': '\u4f5c\u7b54 %d \u79d2\uff0c\u89c4\u5b9a %d \u79d2\uff0c\u4f7f\u7528\u7387\u504f\u4f4e' % (seconds, limit),
                'advice': '\u628a\u8981\u70b9\u6e05\u5355\u80cc\u719f\uff0c\u7528\u5177\u4f53\u4f8b\u5b50\u628a\u65f6\u95f4\u586b\u6ee1'}
    if seconds > limit:
        return {'result': '\u9700\u5173\u6ce8',
                'detail': '\u4f5c\u7b54 %d \u79d2\uff0c\u8d85\u8fc7\u89c4\u5b9a %d \u79d2' % (seconds, limit),
                'advice': '\u8d85\u51fa\u90e8\u5206\u4f1a\u88ab\u622a\u65ad\uff0c\u63a7\u5236\u5728\u89c4\u5b9a\u65f6\u957f\u5185\u8bf4\u5b8c'}
    return {'result': '\u7b26\u5408',
            'detail': '\u4f5c\u7b54 %d \u79d2\uff0c\u89c4\u5b9a %d \u79d2' % (seconds, limit),
            'advice': '\u4fdd\u6301'}


def point_check(task, points):
    spec = TASKS[task]
    if points is None:
        return {'result': '\u5f85\u8865\u5145', 'detail': '\u672a\u586b\u8986\u76d6\u8981\u70b9\u6570',
                'advice': '', 'cap': None}
    req = spec['required']
    full = spec['full']
    if points >= full:
        res, cap = '\u7b26\u5408', 4
        detail = '\u8986\u76d6 %d \u4e2a\u8981\u70b9\uff0c\u8fbe\u5230\u6ee1\u5206\u8981\u70b9\u6570 %d' % (points, full)
    elif points >= req:
        res, cap = '\u7b26\u5408', 4
        detail = '\u8986\u76d6 %d \u4e2a\u8981\u70b9\uff0c\u8fbe\u5230\u5fc5\u8bf4\u8981\u70b9\u6570 %d\uff08\u6ee1\u5206\u9700 %d\uff09' % (points, req, full)
    elif points == req - 1:
        res, cap = '\u9700\u5173\u6ce8', 3
        detail = '\u8986\u76d6 %d \u4e2a\u8981\u70b9\uff0c\u7f3a\u5fc5\u8bf4\u8981\u70b9 1 \u4e2a\uff08\u5fc5\u8bf4 %d\uff09' % (points, req)
    elif points <= 0:
        res, cap = '\u4e0d\u7b26\u5408', 1
        detail = '\u8986\u76d6 0 \u4e2a\u8981\u70b9\uff0c\u7efc\u5408\u9898\u53ea\u8bb2\u9605\u8bfb\u4e0d\u8bb2\u542c\u529b' if task != 1 else '\u8986\u76d6 0 \u4e2a\u8981\u70b9\uff0c\u672a\u7ed9\u51fa\u7acb\u573a'
    else:
        res, cap = '\u4e0d\u7b26\u5408', 2
        detail = '\u8986\u76d6 %d \u4e2a\u8981\u70b9\uff0c\u7f3a\u5fc5\u8bf4\u8981\u70b9 %d \u4e2a\uff08\u5fc5\u8bf4 %d\uff09' % (points, req - points, req)
    return {'result': res, 'detail': detail,
            'advice': '\u5fc5\u8bf4\u8981\u70b9\uff1a%s' % ' / '.join(spec['points'][:req]), 'cap': cap}


def reported(raw):
    """\u5355\u9898\u6863\u4f4d\u6298\u7b97\u5230 0~30\uff08\u6309\u56db\u9898\u540c\u6863\u4f30\u7b97\uff09\u3002"""
    if raw is None:
        return None
    return int(raw * 30.0 / 4.0 + 0.5)


def check(args):
    spec = TASKS[args.task]
    scores = {'delivery': args.delivery, 'language': args.language, 'topic': args.topic}
    items = []
    for key, label, full in DIMS:
        v = scores.get(key)
        if v is None:
            items.append({'name': label, 'full': full, 'band': None,
                          'result': '\u5f85\u8865\u5145', 'detail': '\u672a\u586b\u81ea\u8bc4\u6863\u4f4d', 'upgrade': FIX[key]})
            continue
        lv = int(v)
        if lv >= 4:
            res = '\u7b26\u5408'
        elif lv >= 3:
            res = '\u9700\u5173\u6ce8'
        else:
            res = '\u4e0d\u7b26\u5408'
        items.append({'name': label, 'full': full, 'band': lv, 'result': res,
                      'detail': '\u81ea\u8bc4 %d \u5206\uff1a%s' % (lv, DIM_DESC[key][lv]),
                      'upgrade': FIX[key]})
    tc = time_check(args.task, args.seconds)
    items.append({'name': '\u4f5c\u7b54\u65f6\u957f', 'full': '\u4f5c\u7b54\u79d2\u6570\u6838\u67e5', 'band': None,
                  'result': tc['result'], 'detail': tc['detail'], 'upgrade': tc['advice']})
    pc = point_check(args.task, args.points)
    items.append({'name': '\u8981\u70b9\u8986\u76d6', 'full': '\u5fc5\u8bf4\u8981\u70b9\u6838\u67e5', 'band': None,
                  'result': pc['result'], 'detail': pc['detail'],
                  'upgrade': pc['advice'], 'cap': pc['cap']})

    known = [scores[k] for k in ('delivery', 'language', 'topic') if scores.get(k) is not None]
    task_score = None
    if len(known) == 3:
        avg = sum(known) / 3.0
        cap = pc['cap'] if pc['cap'] is not None else 4
        task_score = min(avg, cap) if cap is not None else avg
    est = reported(task_score)
    gap = None
    if est is not None:
        gap = args.target - est

    if len(known) < 3 or args.points is None:
        verdict = '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4'
    elif gap is not None and gap <= 0:
        verdict = '\u8fbe\u5230\u76ee\u6807'
    elif gap is not None and gap <= 3:
        verdict = '\u63a5\u8fd1\u76ee\u6807'
    else:
        verdict = '\u672a\u8fbe\u76ee\u6807'

    priority = []
    if len(known) == 3:
        order = sorted([(scores['delivery'], 'Delivery'),
                        (scores['language'], 'Language Use'),
                        (scores['topic'], 'Topic Development')])
        low_v, low_name = order[0]
        key = {'Delivery': 'delivery', 'Language Use': 'language',
               'Topic Development': 'topic'}[low_name]
        priority.append('\u6700\u77ed\u677f\uff1a%s\uff08%d \u5206\uff09\u2014\u2014%s' % (low_name, int(low_v), FIX[key]))
        priority.append('\u7ef4\u5ea6\u6392\u5e8f\uff1a' + ' \u2192 '.join('%s(%d)' % (n, int(v)) for v, n in order))
        if args.task != 1 and args.points is not None and args.points <= spec['required'] - 1:
            priority.append('\u7efc\u5408\u9898\u8981\u70b9\u6765\u81ea\u542c\u529b\uff0c\u5148\u8865\u542c\u529b\u7b14\u8bb0\u800c\u4e0d\u662f\u80cc\u6a21\u677f')
        if task_score is not None and pc['cap'] is not None and task_score >= pc['cap']:
            priority.append('\u5f53\u524d\u5206\u6570\u5df2\u88ab\u8981\u70b9\u7f3a\u5931\u5c01\u9876\uff08\u4e0a\u9650 %d \u5206\uff09\uff0c\u5148\u8865\u8981\u70b9\u518d\u7ec3\u8868\u8fbe' % pc['cap'])

    return {'task': spec['name'], 'kind': spec['kind'], 'prep': spec['prep'],
            'speak': spec['speak'], 'required': spec['required'],
            'point_list': spec['points'], 'items': items,
            'task_score': task_score, 'est': est, 'target': args.target,
            'gap': gap, 'verdict': verdict, 'priority': priority}


def render_md(r):
    lines = []
    lines.append('# \u6258\u798f\u53e3\u8bed\u81ea\u67e5\u7ed3\u679c\uff1a%s' % r['task'])
    lines.append('')
    lines.append('- \u9898\u578b\uff1a%s\uff08\u51c6\u5907 %d \u79d2 / \u4f5c\u7b54 %d \u79d2\uff09' % (r['kind'], r['prep'], r['speak']))
    lines.append('- \u5fc5\u8bf4\u8981\u70b9\u6570\uff1a%d' % r['required'])
    for i, p in enumerate(r['point_list'], 1):
        mark = '\u5fc5\u8bf4' if i <= r['required'] else '\u52a0\u5206'
        lines.append('  %d. [%s] %s' % (i, mark, p))
    if r['est'] is not None:
        lines.append('- \u672c\u9898\u4f30\u7b97\u6863\u4f4d\uff1a%.2f / 4\uff0c\u82e5\u56db\u9898\u540c\u6863\u4f30\u7b97\u62a5\u9053\u5206 **%d**\uff08\u76ee\u6807 %d\uff0c\u5dee %+d\uff09'
                     % (r['task_score'], r['est'], r['target'], r['gap']))
    lines.append('- \u5224\u5b9a\uff1a**%s**' % r['verdict'])
    lines.append('')
    lines.append('| \u6838\u67e5\u9879 | \u5224\u5b9a | \u8bf4\u660e | \u6539\u8fdb\u52a8\u4f5c |')
    lines.append('|---|---|---|---|')
    for it in r['items']:
        lines.append('| %s | %s | %s | %s |' % (it['name'], it['result'], it['detail'],
                                                it['upgrade'] or '\u2014'))
    lines.append('')
    if r['priority']:
        lines.append('## \u8bad\u7ec3\u65b9\u5411')
        lines.append('')
        for p in r['priority']:
            lines.append('- %s' % p)
        lines.append('')
    lines.append('> \u62a5\u9053\u5206\u4e3a\u6309\u56db\u9898\u540c\u6863\u7684\u7ebf\u6027\u4f30\u7b97\uff0c\u5b98\u65b9\u91c7\u7528\u8bc4\u5206\u91cf\u8868\u4e0e\u6362\u7b97\u8868\uff0c\u4ee5\u5b98\u65b9\u6210\u7ee9\u62a5\u544a\u4e3a\u51c6\u3002')
    return '\n'.join(lines)


def selftest():
    errors = []

    def mk(**kw):
        a = argparse.Namespace(task=1, seconds=None, points=None, delivery=None,
                               language=None, topic=None, target=23)
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

    eq('case01 Task2 \u8981\u70b9 4 \u8fbe\u6807',
       item(check(mk(task=2, points=4)), '\u8981\u70b9\u8986\u76d6')['result'], '\u7b26\u5408')
    eq('case02 Task2 \u8981\u70b9 3 \u7f3a 1 \u4e2a',
       item(check(mk(task=2, points=3)), '\u8981\u70b9\u8986\u76d6')['result'], '\u9700\u5173\u6ce8')
    eq('case03 Task2 \u8981\u70b9 3 \u5c01\u9876 3 \u5206',
       item(check(mk(task=2, points=3)), '\u8981\u70b9\u8986\u76d6')['cap'], 3)
    eq('case04 Task2 \u8981\u70b9 2 \u4e0d\u7b26\u5408',
       item(check(mk(task=2, points=2)), '\u8981\u70b9\u8986\u76d6')['result'], '\u4e0d\u7b26\u5408')
    eq('case05 Task2 \u8981\u70b9 0 \u5c01\u9876 1 \u5206',
       item(check(mk(task=2, points=0)), '\u8981\u70b9\u8986\u76d6')['cap'], 1)
    eq('case06 Task1 45 \u79d2\u7b26\u5408',
       item(check(mk(task=1, seconds=45)), '\u4f5c\u7b54\u65f6\u957f')['result'], '\u7b26\u5408')
    eq('case07 Task1 25 \u79d2\u9700\u5173\u6ce8',
       item(check(mk(task=1, seconds=25)), '\u4f5c\u7b54\u65f6\u957f')['result'], '\u9700\u5173\u6ce8')
    eq('case08 Task1 20 \u79d2\u4e0d\u7b26\u5408',
       item(check(mk(task=1, seconds=20)), '\u4f5c\u7b54\u65f6\u957f')['result'], '\u4e0d\u7b26\u5408')
    eq('case09 Task3 70 \u79d2\u8d85\u65f6\u63d0\u793a',
       item(check(mk(task=3, seconds=70)), '\u4f5c\u7b54\u65f6\u957f')['result'], '\u9700\u5173\u6ce8')
    eq('case10 \u4e09\u7ef4\u5ea6 3/3/3 \u6863\u4f4d 3.0',
       check(mk(task=1, points=4, delivery=3, language=3, topic=3))['task_score'], 3.0)
    eq('case11 \u4e09\u7ef4\u5ea6\u5168 4 \u62a5\u9053\u5206 30',
       check(mk(task=1, points=4, delivery=4, language=4, topic=4))['est'], 30)
    eq('case12 \u4e09\u7ef4\u5ea6\u5168 3 \u62a5\u9053\u5206 23',
       check(mk(task=1, points=4, delivery=3, language=3, topic=3))['est'], 23)
    eq('case13 \u4e09\u7ef4\u5ea6\u5168 2 \u62a5\u9053\u5206 15',
       check(mk(task=1, points=4, delivery=2, language=2, topic=2))['est'], 15)
    r14 = check(mk(task=2, points=3, delivery=4, language=4, topic=4))
    eq('case14 \u8981\u70b9\u7f3a\u5931\u5c01\u9876\u751f\u6548', r14['task_score'], 3.0)
    eq('case15 \u5c01\u9876\u63d0\u793a\u51fa\u73b0',
       any('\u5c01\u9876' in p for p in r14['priority']), True)
    eq('case16 \u76ee\u6807\u5dee\u8ddd 23-23=0',
       check(mk(task=1, points=4, delivery=3, language=3, topic=3))['gap'], 0)
    eq('case17 \u8fbe\u6807\u5224\u5b9a',
       check(mk(task=1, points=4, delivery=3, language=3, topic=3))['verdict'], '\u8fbe\u5230\u76ee\u6807')
    eq('case18 \u672a\u8fbe\u76ee\u6807\u5224\u5b9a',
       check(mk(task=1, points=4, delivery=2, language=2, topic=2))['verdict'], '\u672a\u8fbe\u76ee\u6807')
    eq('case19 \u7f3a\u4fe1\u606f\u5224\u5b9a', check(mk(task=1))['verdict'], '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4')
    p20 = check(mk(task=3, points=3, delivery=4, language=4, topic=2))['priority']
    eq('case20 \u6700\u77ed\u677f\u53d6 topic', p20[0].startswith('\u6700\u77ed\u677f\uff1aTopic Development'), True)
    eq('case21 Delivery 4 \u5206\u5224\u7b26\u5408',
       item(check(mk(delivery=4)), 'Delivery')['result'], '\u7b26\u5408')
    eq('case22 Delivery 2 \u5206\u5224\u4e0d\u7b26\u5408',
       item(check(mk(delivery=2)), 'Delivery')['result'], '\u4e0d\u7b26\u5408')
    eq('case23 Task4 \u5fc5\u8bf4\u8981\u70b9 3',
       check(mk(task=4))['required'], 3)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 23\n\u8986\u76d6: \u56db\u9898\u8981\u70b9\u8986\u76d6\u4e0e\u5c01\u9876/\u4f5c\u7b54\u65f6\u957f\u4e09\u6863/\u4e09\u7ef4\u5ea6\u5b9a\u6863/'
               '0~30 \u6298\u7b97/\u76ee\u6807\u5dee\u8ddd/\u4fe1\u606f\u7f3a\u5931/\u6700\u77ed\u677f\u5224\u5b9a')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u6258\u798f\u53e3\u8bed\u7b54\u9898\u7ed3\u6784\u4e0e\u8bc4\u5206\u6838\u67e5')
    ap.add_argument('--task', type=int, default=1, choices=[1, 2, 3, 4])
    ap.add_argument('--seconds', type=int, help='\u5b9e\u9645\u4f5c\u7b54\u79d2\u6570')
    ap.add_argument('--points', type=int, help='\u5b9e\u9645\u8986\u76d6\u7684\u8981\u70b9\u4e2a\u6570')
    ap.add_argument('--delivery', type=int, help='Delivery \u81ea\u8bc4 0~4')
    ap.add_argument('--language', type=int, help='Language Use \u81ea\u8bc4 0~4')
    ap.add_argument('--topic', type=int, help='Topic Development \u81ea\u8bc4 0~4')
    ap.add_argument('--target', type=int, default=23, help='\u76ee\u6807\u53e3\u8bed\u5206 0~30')
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
