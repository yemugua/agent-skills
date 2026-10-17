#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u82f1\u8bed\u56db\u516d\u7ea7\u5206\u6570\u7ed3\u6784\u6362\u7b97\u3001\u5404\u9898\u578b\u5f97\u5206\u7387\u4e0e\u65f6\u95f4\u5206\u914d\u6838\u67e5\u3002

\u7528\u6cd5:
  python cet46_score_check.py --level 6 --longconv 6 --passage 5 --lecture 7 \
      --cloze 6 --skim 8 --careful 7 --writing 80 --translation 78 --minutes 30,35,40,25
  python cet46_score_check.py --level 4 --news 5 --longconv 6 --passage 8 \
      --cloze 5 --skim 7 --careful 6 --writing 75 --translation 70 --target 425
  python cet46_score_check.py --selftest

\u53c2\u6570:
  --level       4 \u6216 6\uff0c\u9ed8\u8ba4 4
  --news        \u77ed\u7bc7\u65b0\u95fb\u6b63\u786e\u9898\u6570\uff08\u4ec5\u56db\u7ea7\uff0c\u6ee1\u5206 7\uff09
  --longconv    \u957f\u5bf9\u8bdd\u6b63\u786e\u9898\u6570\uff08\u6ee1\u5206 8\uff09
  --passage     \u542c\u529b\u7bc7\u7ae0\u6b63\u786e\u9898\u6570\uff08\u56db\u7ea7 10 / \u516d\u7ea7 7\uff09
  --lecture     \u8bb2\u5ea7/\u8bb2\u8bdd\u6b63\u786e\u9898\u6570\uff08\u4ec5\u516d\u7ea7\uff0c\u6ee1\u5206 10\uff09
  --cloze       \u9009\u8bcd\u586b\u7a7a\u6b63\u786e\u9898\u6570\uff08\u6ee1\u5206 10\uff09
  --skim        \u957f\u7bc7\u9605\u8bfb\u6b63\u786e\u9898\u6570\uff08\u6ee1\u5206 10\uff09
  --careful     \u4ed4\u7ec6\u9605\u8bfb\u6b63\u786e\u9898\u6570\uff08\u6ee1\u5206 10\uff09
  --writing     \u5199\u4f5c\u81ea\u8bc4\u5206 0~106.5
  --translation \u7ffb\u8bd1\u81ea\u8bc4\u5206 0~106.5
  --minutes     \u56db\u90e8\u5206\u7528\u65f6\uff08\u5206\u949f\uff09\uff0c\u9017\u53f7\u5206\u9694\uff1a\u5199\u4f5c,\u542c\u529b,\u9605\u8bfb,\u7ffb\u8bd1
  --target      \u76ee\u6807\u5206\uff0c\u9ed8\u8ba4 425
  --out         \u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84
  --format      md\uff08\u9ed8\u8ba4\uff09\u6216 json
  --selftest    \u8fd0\u884c\u5185\u7f6e\u81ea\u68c0
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

LEVELS = {
    4: {'name': '\u56db\u7ea7', 'minutes': 125,
        'listening': [('\u77ed\u7bc7\u65b0\u95fb', 'news', 7, 7.1),
                      ('\u957f\u5bf9\u8bdd', 'longconv', 8, 7.1),
                      ('\u542c\u529b\u7bc7\u7ae0', 'passage', 10, 14.2)],
        'budget': [('\u5199\u4f5c', 30), ('\u542c\u529b', 25), ('\u9605\u8bfb', 40),
                   ('\u7ffb\u8bd1', 25)]},
    6: {'name': '\u516d\u7ea7', 'minutes': 130,
        'listening': [('\u957f\u5bf9\u8bdd', 'longconv', 8, 7.1),
                      ('\u542c\u529b\u7bc7\u7ae0', 'passage', 7, 7.1),
                      ('\u8bb2\u5ea7/\u8bb2\u8bdd', 'lecture', 10, 14.2)],
        'budget': [('\u5199\u4f5c', 30), ('\u542c\u529b', 30), ('\u9605\u8bfb', 40),
                   ('\u7ffb\u8bd1', 25)]},
}
READING = [('\u9009\u8bcd\u586b\u7a7a', 'cloze', 10, 3.55),
           ('\u957f\u7bc7\u9605\u8bfb', 'skim', 10, 7.1),
           ('\u4ed4\u7ec6\u9605\u8bfb', 'careful', 10, 14.2)]
FULL = {'listening': 248.5, 'reading': 248.5, 'writing': 106.5, 'translation': 106.5}
WEIGHT = {'listening': 0.35, 'reading': 0.35, 'writing': 0.15, 'translation': 0.15}


def parse_minutes(s):
    if not s:
        return []
    out = []
    for part in s.replace('\uff0c', ',').split(','):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


def section_score(defs, values):
    rows = []
    total = 0.0
    known = False
    for label, key, cap, pt in defs:
        v = values.get(key)
        if v is None:
            rows.append({'name': label, 'correct': None, 'cap': cap, 'pt': pt,
                         'score': None, 'rate': None})
            continue
        known = True
        c = max(0, min(int(v), cap))
        sc = c * pt
        total += sc
        rows.append({'name': label, 'correct': c, 'cap': cap, 'pt': pt,
                     'score': round(sc, 2), 'rate': round(c * 100.0 / cap, 1)})
    return rows, (round(total, 2) if known else None), known


def time_check(idx, name, used, budget):
    if used is None:
        return {'name': name, 'result': '\u5f85\u8865\u5145', 'detail': '\u672a\u586b\u7528\u65f6',
                'advice': '\u5efa\u8bae %d \u5206\u949f' % budget}
    if used > budget + 5:
        return {'name': name, 'result': '\u4e0d\u7b26\u5408',
                'detail': '%d \u5206\u949f\uff0c\u8d85\u9884\u7b97 %d \u5206\u949f\u8f83\u591a' % (used, budget),
                'advice': '\u8be5\u90e8\u5206\u6324\u5360\u4e86\u5176\u4ed6\u90e8\u5206\u65f6\u95f4'}
    if used > budget:
        return {'name': name, 'result': '\u9700\u5173\u6ce8',
                'detail': '%d \u5206\u949f\uff0c\u6bd4\u9884\u7b97 %d \u5206\u949f\u591a %d \u5206\u949f' % (used, budget, used - budget),
                'advice': '\u538b\u7f29\u5230 %d \u5206\u949f\u4ee5\u5185' % budget}
    if used < budget * 0.6:
        return {'name': name, 'result': '\u9700\u5173\u6ce8',
                'detail': '%d \u5206\u949f\uff0c\u5c11\u4e8e\u9884\u7b97 %d \u5206\u949f\u7684 60%%' % (used, budget),
                'advice': '\u7528\u65f6\u8fc7\u77ed\uff0c\u5185\u5bb9\u53ef\u80fd\u4e0d\u5b8c\u6574'}
    return {'name': name, 'result': '\u7b26\u5408',
            'detail': '%d \u5206\u949f\uff0c\u9884\u7b97 %d \u5206\u949f' % (used, budget), 'advice': '\u4fdd\u6301'}


def check(args):
    spec = LEVELS[args.level]
    vals = {'news': args.news, 'longconv': args.longconv, 'passage': args.passage,
            'lecture': args.lecture, 'cloze': args.cloze, 'skim': args.skim,
            'careful': args.careful}
    lc_rows, lc_total, lc_known = section_score(spec['listening'], vals)
    rd_rows, rd_total, rd_known = section_score(READING, vals)
    parts = [('\u542c\u529b', 'listening', lc_total, FULL['listening'], lc_rows, lc_known),
             ('\u9605\u8bfb', 'reading', rd_total, FULL['reading'], rd_rows, rd_known),
             ('\u5199\u4f5c', 'writing', args.writing, FULL['writing'], [],
              args.writing is not None),
             ('\u7ffb\u8bd1', 'translation', args.translation, FULL['translation'], [],
              args.translation is not None)]
    part_rows = []
    total = None
    all_known = True
    acc = 0.0
    for label, key, sc, full, rows, known in parts:
        if not known:
            all_known = False
            part_rows.append({'name': label, 'score': None, 'full': full,
                              'rate': None, 'weight': WEIGHT[key], 'rows': rows})
            continue
        acc += sc
        part_rows.append({'name': label, 'score': round(sc, 2), 'full': full,
                          'rate': round(sc * 100.0 / full, 1),
                          'weight': WEIGHT[key], 'rows': rows})
    if all_known:
        total = round(acc, 2)
    gap = None
    if total is not None:
        gap = round(args.target - total, 2)

    minutes = parse_minutes(args.minutes)
    time_rows = []
    for i, (name, budget) in enumerate(spec['budget']):
        used = minutes[i] if i < len(minutes) else None
        time_rows.append(time_check(i, name, used, budget))

    weakest = None
    known_parts = [p for p in part_rows if p['rate'] is not None]
    if known_parts:
        worst = min(known_parts, key=lambda p: p['rate'])
        weakest = {'name': worst['name'], 'rate': worst['rate']}

    priority = []
    if weakest:
        priority.append('\u6700\u8584\u5f31\u7684\u4e00\u9879\uff1a%s\uff08\u5f97\u5206\u7387 %.1f%%\uff09\u2014\u2014\u6309\u5206\u503c\u5360\u6bd4\u4f18\u5148\u8865'
                        % (weakest['name'], weakest['rate']))
    for p in part_rows:
        if p['rate'] is not None and p['rate'] < 60:
            priority.append('%s \u5f97\u5206\u7387 %.1f%%\uff0c\u4f4e\u4e8e 60%%\uff0c\u662f\u4e3b\u8981\u5931\u5206\u9879' % (p['name'], p['rate']))
    for r in time_rows:
        if r['result'] == '\u4e0d\u7b26\u5408':
            priority.append('\u65f6\u95f4\uff1a%s %s\u2014\u2014%s' % (r['name'], r['detail'], r['advice']))
    for r in time_rows:
        if r['result'] == '\u9700\u5173\u6ce8':
            priority.append('\u65f6\u95f4\uff1a%s %s\u2014\u2014%s' % (r['name'], r['detail'], r['advice']))
    if rd_known:
        careful = [r for r in rd_rows if r['name'] == '\u4ed4\u7ec6\u9605\u8bfb']
        if careful and careful[0]['rate'] is not None and careful[0]['rate'] < 60:
            priority.append('\u4ed4\u7ec6\u9605\u8bfb\u4e00\u9898 14.2 \u5206\uff0c\u6b63\u786e\u7387 %.1f%%\uff0c\u4f18\u5148\u7ec3\u5b9a\u4f4d\u4e0e\u540c\u4e49\u66ff\u6362'
                            % careful[0]['rate'])
    priority.append('\u7b54\u9898\u987a\u5e8f\u5efa\u8bae\uff1a\u5199\u4f5c \u2192 \u542c\u529b \u2192 \u4ed4\u7ec6\u9605\u8bfb \u2192 \u957f\u7bc7\u9605\u8bfb \u2192 \u7ffb\u8bd1 \u2192 \u9009\u8bcd\u586b\u7a7a')

    if total is None:
        verdict = '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4'
    elif gap <= 0:
        verdict = '\u8fbe\u5230\u76ee\u6807'
    elif gap <= 25:
        verdict = '\u63a5\u8fd1\u76ee\u6807'
    else:
        verdict = '\u672a\u8fbe\u76ee\u6807'

    return {'level': spec['name'], 'total_minutes': spec['minutes'],
            'part_rows': part_rows, 'total': total, 'target': args.target,
            'gap': gap, 'verdict': verdict, 'time_rows': time_rows,
            'weakest': weakest, 'priority': priority}


def render_md(r):
    lines = ['# \u82f1\u8bed\u56db\u516d\u7ea7\u6838\u67e5\u7ed3\u679c\uff1a%s' % r['level'], '']
    lines.append('- \u8003\u8bd5\u603b\u65f6\u957f\uff1a%d \u5206\u949f' % r['total_minutes'])
    if r['total'] is not None:
        lines.append('- \u4f30\u7b97\u603b\u5206\uff1a**%.1f**\uff08\u76ee\u6807 %d\uff0c\u5dee %+.1f\uff09'
                     % (r['total'], r['target'], r['gap']))
    lines.append('- \u5224\u5b9a\uff1a**%s**' % r['verdict'])
    lines.append('')
    lines.append('| \u90e8\u5206 | \u5f97\u5206 | \u6ee1\u5206 | \u5f97\u5206\u7387 | \u6743\u91cd |')
    lines.append('|---|---|---|---|---|')
    for p in r['part_rows']:
        lines.append('| %s | %s | %.1f | %s | %d%% |'
                     % (p['name'],
                        p['score'] if p['score'] is not None else '\u2014',
                        p['full'],
                        ('%.1f%%' % p['rate']) if p['rate'] is not None else '\u2014',
                        int(p['weight'] * 100)))
    lines.append('')
    lines.append('## \u5404\u9898\u578b\u5c0f\u9898\u5f97\u5206')
    lines.append('')
    lines.append('| \u90e8\u5206 | \u9898\u578b | \u6b63\u786e/\u9898\u91cf | \u6bcf\u9898\u5206\u503c | \u5f97\u5206 |')
    lines.append('|---|---|---|---|---|')
    for p in r['part_rows']:
        if not p['rows']:
            continue
        for row in p['rows']:
            lines.append('| %s | %s | %s | %.2f | %s |'
                         % (p['name'], row['name'],
                            ('%d / %d' % (row['correct'], row['cap']))
                            if row['correct'] is not None else '\u2014',
                            row['pt'],
                            row['score'] if row['score'] is not None else '\u2014'))
    lines.append('')
    lines.append('## \u65f6\u95f4\u5206\u914d')
    lines.append('')
    lines.append('| \u90e8\u5206 | \u5224\u5b9a | \u8bf4\u660e | \u5efa\u8bae |')
    lines.append('|---|---|---|---|')
    for t in r['time_rows']:
        lines.append('| %s | %s | %s | %s |' % (t['name'], t['result'], t['detail'], t['advice']))
    lines.append('')
    if r['priority']:
        lines.append('## \u8bad\u7ec3\u65b9\u5411')
        lines.append('')
        for p in r['priority']:
            lines.append('- %s' % p)
        lines.append('')
    lines.append('> \u4f30\u5206\u662f\u6309\u5e38\u7528\u5206\u503c\u5bf9\u7167\u7684\u52a0\u6743\u4f30\u7b97\uff0c'
                 '\u5b98\u65b9\u62a5\u9053\u5206\u91c7\u7528\u5e38\u6a21\u6362\u7b97\uff0c\u4ee5\u5b98\u65b9\u6210\u7ee9\u62a5\u544a\u4e3a\u51c6\u3002')
    return '\n'.join(lines)


def selftest():
    errors = []

    def mk(**kw):
        a = argparse.Namespace(level=4, news=None, longconv=None, passage=None,
                               lecture=None, cloze=None, skim=None, careful=None,
                               writing=None, translation=None, minutes=None,
                               target=425, out=None, format='md')
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    def part(r, name):
        for p in r['part_rows']:
            if p['name'] == name:
                return p
        return None

    def row_of(p, name):
        for row in p['rows']:
            if row['name'] == name:
                return row
        return None

    r1 = check(mk(level=4, news=7, longconv=8, passage=10, cloze=10, skim=10,
                  careful=10, writing=106.5, translation=106.5))
    eq('case01 \u56db\u7ea7\u542c\u529b\u6ee1\u5206', part(r1, '\u542c\u529b')['score'], 248.5)
    eq('case02 \u56db\u7ea7\u9605\u8bfb\u6ee1\u5206', part(r1, '\u9605\u8bfb')['score'], 248.5)
    eq('case03 \u603b\u5206 710', r1['total'], 710.0)
    eq('case04 \u8fbe\u5230\u76ee\u6807', r1['verdict'], '\u8fbe\u5230\u76ee\u6807')

    r2 = check(mk(level=6, longconv=6, passage=5, lecture=7, cloze=6, skim=8,
                  careful=7, writing=80, translation=78, minutes='30,35,40,25'))
    lc = part(r2, '\u542c\u529b')['score']
    eq('case05 \u516d\u7ea7\u542c\u529b\u5c0f\u8ba1 6*7.1+5*7.1+7*14.2=177.5', lc, 177.5)
    rd = part(r2, '\u9605\u8bfb')['score']
    eq('case06 \u9605\u8bfb\u5c0f\u8ba1 6*3.55+8*7.1+7*14.2=177.5', rd, 177.5)
    eq('case07 \u603b\u5206 513', r2['total'], 513.0)
    eq('case08 \u76ee\u6807\u5dee\u989d -88', r2['gap'], -88.0)
    eq('case09 \u6700\u8584\u5f31\u9879\u4e3a\u542c\u529b', r2['weakest']['name'], '\u542c\u529b')

    r3 = check(mk(level=4, news=0, longconv=0, passage=0, cloze=0, skim=0,
                  careful=0, writing=0, translation=0))
    eq('case10 \u5168\u96f6\u603b\u5206', r3['total'], 0.0)
    eq('case11 \u672a\u8fbe\u76ee\u6807', r3['verdict'], '\u672a\u8fbe\u76ee\u6807')

    r4 = check(mk(level=4, news=4, longconv=4, passage=5, cloze=4, skim=5,
                  careful=5, writing=80, translation=80))
    eq('case12 \u4e2d\u7b49\u4f30\u5206 408.5', r4['total'], 408.5)
    eq('case13 \u63a5\u8fd1\u76ee\u6807', r4['verdict'], '\u63a5\u8fd1\u76ee\u6807')

    eq('case14 \u56db\u7ea7\u542c\u529b\u7bc7\u7ae0\u9898\u91cf 10',
       row_of(part(r1, '\u542c\u529b'), '\u542c\u529b\u7bc7\u7ae0')['cap'], 10)
    r6 = check(mk(level=6, longconv=8, passage=7, lecture=10, cloze=10, skim=10,
                  careful=10, writing=106.5, translation=106.5))
    eq('case15 \u516d\u7ea7\u542c\u529b\u7bc7\u7ae0\u9898\u91cf 7',
       row_of(part(r6, '\u542c\u529b'), '\u542c\u529b\u7bc7\u7ae0')['cap'], 7)
    eq('case16 \u516d\u7ea7\u65e0\u77ed\u7bc7\u65b0\u95fb',
       row_of(part(r6, '\u542c\u529b'), '\u77ed\u7bc7\u65b0\u95fb'), None)
    eq('case17 \u56db\u7ea7\u65e0\u8bb2\u5ea7',
       row_of(part(r1, '\u542c\u529b'), '\u8bb2\u5ea7/\u8bb2\u8bdd'), None)
    eq('case18 \u4ed4\u7ec6\u9605\u8bfb\u6bcf\u9898 14.2',
       row_of(part(r1, '\u9605\u8bfb'), '\u4ed4\u7ec6\u9605\u8bfb')['pt'], 14.2)
    eq('case19 \u9009\u8bcd\u586b\u7a7a\u6bcf\u9898 3.55',
       row_of(part(r1, '\u9605\u8bfb'), '\u9009\u8bcd\u586b\u7a7a')['pt'], 3.55)

    t1 = check(mk(level=4, minutes='30,25,40,25', writing=60, translation=60,
                  news=4, longconv=4, passage=5, cloze=4, skim=5, careful=5))
    eq('case20 \u65f6\u95f4\u5168\u90e8\u8fbe\u6807',
       all(t['result'] == '\u7b26\u5408' for t in t1['time_rows']), True)
    t2 = check(mk(level=4, minutes='30,25,50,25'))
    eq('case21 \u9605\u8bfb\u8d85\u65f6\u5224\u4e0d\u7b26\u5408',
       [t for t in t2['time_rows'] if t['name'] == '\u9605\u8bfb'][0]['result'], '\u4e0d\u7b26\u5408')
    t3 = check(mk(level=4, minutes='30,25,20,25'))
    eq('case22 \u8425\u4e1a\u4e0d\u8db3\u5224\u9700\u5173\u6ce8',
       [t for t in t3['time_rows'] if t['name'] == '\u9605\u8bfb'][0]['result'], '\u9700\u5173\u6ce8')
    eq('case23 \u65e0\u8f93\u5165\u5224\u9700\u8865\u5145\u4fe1\u606f',
       check(mk())['verdict'], '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4')
    eq('case24 \u7b54\u9898\u987a\u5e8f\u63d0\u793a\u5b58\u5728',
       any('\u7b54\u9898\u987a\u5e8f' in p for p in r2['priority']), True)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 24\n\u8986\u76d6: \u56db\u516d\u7ea7\u542c\u529b\u9898\u578b\u5dee\u5f02/'
               '\u5404\u9898\u578b\u5c0f\u9898\u5206\u503c/\u603b\u5206\u4e0e\u76ee\u6807\u5dee\u989d/\u6700\u8584\u5f31\u9879/'
               '\u65f6\u95f4\u5206\u914d\u5224\u5b9a/\u4fe1\u606f\u7f3a\u5931')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u82f1\u8bed\u56db\u516d\u7ea7\u5206\u503c\u7ed3\u6784\u4e0e\u5907\u8003\u6838\u67e5')
    ap.add_argument('--level', type=int, default=4, choices=[4, 6])
    ap.add_argument('--news', type=int, help='\u77ed\u7bc7\u65b0\u95fb\u6b63\u786e\u9898\u6570')
    ap.add_argument('--longconv', type=int, help='\u957f\u5bf9\u8bdd\u6b63\u786e\u9898\u6570')
    ap.add_argument('--passage', type=int, help='\u542c\u529b\u7bc7\u7ae0\u6b63\u786e\u9898\u6570')
    ap.add_argument('--lecture', type=int, help='\u8bb2\u5ea7/\u8bb2\u8bdd\u6b63\u786e\u9898\u6570')
    ap.add_argument('--cloze', type=int, help='\u9009\u8bcd\u586b\u7a7a\u6b63\u786e\u9898\u6570')
    ap.add_argument('--skim', type=int, help='\u957f\u7bc7\u9605\u8bfb\u6b63\u786e\u9898\u6570')
    ap.add_argument('--careful', type=int, help='\u4ed4\u7ec6\u9605\u8bfb\u6b63\u786e\u9898\u6570')
    ap.add_argument('--writing', type=float, help='\u5199\u4f5c\u81ea\u8bc4\u5206 0~106.5')
    ap.add_argument('--translation', type=float, help='\u7ffb\u8bd1\u81ea\u8bc4\u5206 0~106.5')
    ap.add_argument('--minutes', help='\u56db\u90e8\u5206\u7528\u65f6\uff0c\u9017\u53f7\u5206\u9694')
    ap.add_argument('--target', type=float, default=425, help='\u76ee\u6807\u5206')
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
