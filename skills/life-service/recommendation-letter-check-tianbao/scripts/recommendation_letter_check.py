#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u7559\u5b66\u63a8\u8350\u4eba\u56db\u7ef4\u6253\u5206\u4e0e\u63a8\u8350\u4fe1\u8981\u7d20\u6838\u67e5\u3002

\u7528\u6cd5:
  python recommendation_letter_check.py --relation 5 --depth 4 --title 4 --willing 5 \
      --words 520 --examples 2 --strength-level top --relationship 1
  python recommendation_letter_check.py --relation 3 --depth 2 --title 5 --willing 3 --words 800
  python recommendation_letter_check.py --selftest

\u53c2\u6570:
  --relation        \u5173\u8054\u5ea6 0~5
  --depth           \u4e86\u89e3\u6df1\u5ea6 0~5
  --title           \u804c\u79f0\u516c\u4fe1\u529b 0~5
  --willing         \u8868\u8fbe\u610f\u613f 0~5
  --words           \u63a8\u8350\u4fe1\u5b57\u6570
  --limit           \u5b57\u6570\u4e0a\u9650\uff08\u4ee5\u9662\u6821\u8981\u6c42\u4e3a\u51c6\uff09
  --examples        \u5177\u4f53\u4e8b\u4f8b\u6761\u6570
  --strength-level  \u63a8\u8350\u5f3a\u5ea6 top / middle / none
  --relationship    \u662f\u5426\u5199\u660e\u5173\u7cfb\u4e0e\u65f6\u957f\uff0c1 \u662f / 0 \u5426
  --out             \u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84
  --format          md\uff08\u9ed8\u8ba4\uff09\u6216 json
  --selftest        \u8fd0\u884c\u5185\u7f6e\u81ea\u68c0
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

DIMS = [('relation', '\u5173\u8054\u5ea6', '\u662f\u5426\u76f4\u63a5\u6307\u5bfc\u8fc7\u4f60'),
        ('depth', '\u4e86\u89e3\u6df1\u5ea6', '\u80fd\u5426\u5199\u51fa\u5177\u4f53\u4e8b\u4f8b'),
        ('title', '\u804c\u79f0\u516c\u4fe1\u529b', '\u804c\u79f0\u4e0e\u5b66\u672f/\u884c\u4e1a\u8eab\u4efd'),
        ('willing', '\u8868\u8fbe\u610f\u613f', '\u613f\u4e0d\u613f\u610f\u8ba4\u771f\u5199')]
WORD_OK = (400, 600)
MIN_EXAMPLES = 2
MIN_DEPTH = 3
MIN_TOTAL = 16
OK_TOTAL = 12


def recommender_check(scores):
    known = {k: v for k, v in scores.items() if v is not None}
    total = sum(known.values()) if known else None
    depth = scores.get('depth')
    if len(known) < 4:
        return {'result': '\u5f85\u8865\u5145', 'total': total,
                'detail': '\u56db\u7ef4\u672a\u586b\u5168\uff0c\u65e0\u6cd5\u5224\u5b9a\u53ef\u7528\u6027', 'advice': ''}
    if depth is not None and depth <= 2:
        return {'result': '\u4e0d\u7b26\u5408', 'total': total,
                'detail': '\u603b\u5206 %d\uff0c\u4f46\u4e86\u89e3\u6df1\u5ea6 %d \u5206\uff0c\u4f4e\u4e8e\u4e0b\u9650' % (total, depth),
                'advice': '\u4e86\u89e3\u6df1\u5ea6 \u22642 \u4e00\u5f8b\u4e0d\u5efa\u8bae\uff0c\u65e0\u8bba\u804c\u79f0\u591a\u9ad8\uff0c\u5e94\u6362\u63a8\u8350\u4eba'}
    if total >= MIN_TOTAL:
        return {'result': '\u7b26\u5408', 'total': total,
                'detail': '\u603b\u5206 %d\uff0c\u4e86\u89e3\u6df1\u5ea6 %d \u5206' % (total, depth),
                'advice': '\u4fdd\u6301\uff0c\u53ef\u4f5c\u4e3a\u4e3b\u8981\u63a8\u8350\u4eba'}
    if total >= OK_TOTAL:
        return {'result': '\u9700\u5173\u6ce8', 'total': total,
                'detail': '\u603b\u5206 %d\uff0c\u8fbe\u5230 %d \u4f46\u672a\u5230 %d' % (total, OK_TOTAL, MIN_TOTAL),
                'advice': '\u53ef\u4f5c\u4e3a\u7b2c\u4e8c\u6216\u7b2c\u4e09\u63a8\u8350\u4eba'}
    return {'result': '\u4e0d\u7b26\u5408', 'total': total,
            'detail': '\u603b\u5206 %d\uff0c\u4f4e\u4e8e %d' % (total, OK_TOTAL),
            'advice': '\u603b\u5206\u4e0d\u8db3\uff0c\u5efa\u8bae\u6362\u63a8\u8350\u4eba'}


def word_check(n, limit):
    lo, hi = WORD_OK
    if n is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u5b57\u6570', ''
    if limit is not None and n > limit:
        return '\u4e0d\u7b26\u5408', '%d \u8bcd\uff0c\u8d85\u8fc7\u4e0a\u9650 %d \u8bcd' % (n, limit), '\u6309\u9662\u6821\u8981\u6c42\u538b\u7f29'
    if n < 300:
        return '\u4e0d\u7b26\u5408', '%d \u8bcd\uff0c\u8fdc\u4f4e\u4e8e\u5e38\u89c1\u533a\u95f4 %d~%d' % (n, lo, hi), '\u5185\u5bb9\u4e0d\u8db3\uff0c\u8865\u5177\u4f53\u4e8b\u4f8b'
    if n < lo:
        return '\u9700\u5173\u6ce8', '%d \u8bcd\uff0c\u7565\u4f4e\u4e8e\u5e38\u89c1\u533a\u95f4 %d~%d' % (n, lo, hi), '\u8865\u5230 %d \u8bcd\u5de6\u53f3' % lo
    if n > 700:
        return '\u4e0d\u7b26\u5408', '%d \u8bcd\uff0c\u8fdc\u9ad8\u4e8e\u5e38\u89c1\u533a\u95f4 %d~%d' % (n, lo, hi), '\u538b\u7f29\u5230\u5e38\u89c1\u533a\u95f4'
    if n > hi:
        return '\u9700\u5173\u6ce8', '%d \u8bcd\uff0c\u7565\u9ad8\u4e8e\u5e38\u89c1\u533a\u95f4 %d~%d' % (n, lo, hi), '\u538b\u7f29\u5230 %d \u8bcd\u4ee5\u5185' % hi
    return '\u7b26\u5408', '%d \u8bcd\uff0c\u5728\u5e38\u89c1\u533a\u95f4 %d~%d' % (n, lo, hi), '\u4fdd\u6301'


def example_check(n):
    if n is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u4e8b\u4f8b\u6761\u6570', ''
    if n >= MIN_EXAMPLES:
        return '\u7b26\u5408', '\u5177\u4f53\u4e8b\u4f8b %d \u6761' % n, '\u4fdd\u6301'
    if n == 1:
        return '\u9700\u5173\u6ce8', '\u5177\u4f53\u4e8b\u4f8b %d \u6761\uff0c\u5efa\u8bae\u81f3\u5c11 %d \u6761' % (n, MIN_EXAMPLES), '\u518d\u8865\u4e00\u4ef6\u5177\u4f53\u7684\u4e8b'
    return '\u4e0d\u7b26\u5408', '\u65e0\u5177\u4f53\u4e8b\u4f8b', '\u901a\u7bc7\u5f62\u5bb9\u8bcd\u7b49\u4e8e\u6ca1\u6709\u5185\u5bb9'


def strength_check(level):
    if not level:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u63a8\u8350\u5f3a\u5ea6', ''
    lv = str(level).strip().lower()
    if lv == 'top':
        return '\u7b26\u5408', '\u63a8\u8350\u5f3a\u5ea6\u660e\u786e\uff08\u5f3a\uff09', '\u4fdd\u6301'
    if lv == 'middle':
        return '\u9700\u5173\u6ce8', '\u63a8\u8350\u5f3a\u5ea6\u504f\u5f31', '\u6539\u4e3a\u660e\u786e\u7684\u5f3a\u5ea6\u8868\u8ff0'
    return '\u4e0d\u7b26\u5408', '\u63a8\u8350\u5f3a\u5ea6\u542b\u7cca', '\u542b\u7cca\u4f1a\u88ab\u8bfb\u6210\u4e0d\u591f\u5f3a\uff0c\u5fc5\u987b\u660e\u786e'


def relationship_check(v):
    if v is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u662f\u5426\u5199\u660e\u5173\u7cfb', ''
    if int(v) == 1:
        return '\u7b26\u5408', '\u5df2\u5199\u660e\u5173\u7cfb\u4e0e\u65f6\u957f', '\u4fdd\u6301'
    return '\u4e0d\u7b26\u5408', '\u672a\u5199\u660e\u5173\u7cfb\u4e0e\u65f6\u957f', '\u7b2c\u4e00\u6bb5\u5fc5\u987b\u5199\u6e05\u600e\u4e48\u8ba4\u8bc6\u3001\u89c2\u5bdf\u591a\u4e45\u3001\u4ec0\u4e48\u8eab\u4efd'


def check(args):
    scores = {'relation': args.relation, 'depth': args.depth,
              'title': args.title, 'willing': args.willing}
    rc = recommender_check(scores)
    items = []
    for key, label, desc in DIMS:
        v = scores.get(key)
        if v is None:
            items.append({'name': label, 'result': '\u5f85\u8865\u5145', 'detail': '\u672a\u6253\u5206\uff08%s\uff09' % desc,
                          'advice': ''})
        else:
            res = '\u7b26\u5408' if v >= 4 else ('\u9700\u5173\u6ce8' if v >= 3 else '\u4e0d\u7b26\u5408')
            items.append({'name': label, 'result': res,
                          'detail': '%d \u5206\uff08%s\uff09' % (v, desc),
                          'advice': '' if res == '\u7b26\u5408' else '\u8be5\u9879\u504f\u4f4e\uff0c\u5f71\u54cd\u53ef\u7528\u6027\u5224\u5b9a'})
    items.append({'name': '\u63a8\u8350\u4eba\u53ef\u7528\u6027', 'result': rc['result'],
                  'detail': rc['detail'], 'advice': rc['advice']})
    wr, wd, wa = word_check(args.words, args.limit)
    items.append({'name': '\u5b57\u6570', 'result': wr, 'detail': wd, 'advice': wa})
    er, ed, ea = example_check(args.examples)
    items.append({'name': '\u5177\u4f53\u4e8b\u4f8b', 'result': er, 'detail': ed, 'advice': ea})
    sr, sd, sa = strength_check(args.strength_level)
    items.append({'name': '\u63a8\u8350\u5f3a\u5ea6', 'result': sr, 'detail': sd, 'advice': sa})
    rr, rd, ra = relationship_check(args.relationship)
    items.append({'name': '\u5173\u7cfb\u8bf4\u660e', 'result': rr, 'detail': rd, 'advice': ra})

    priority = []
    if rc['result'] == '\u4e0d\u7b26\u5408':
        priority.append('\u63a8\u8350\u4eba\u672c\u8eab\u4e0d\u53ef\u7528\uff1a%s\u2014\u2014%s' % (rc['detail'], rc['advice']))
    for it in items:
        if it['result'] == '\u4e0d\u7b26\u5408' and it['name'] != '\u63a8\u8350\u4eba\u53ef\u7528\u6027':
            priority.append('%s\uff1a%s\u2014\u2014%s' % (it['name'], it['detail'], it['advice']))
    for it in items:
        if it['result'] == '\u9700\u5173\u6ce8':
            priority.append('%s\uff1a%s\u2014\u2014%s' % (it['name'], it['detail'], it['advice']))
    priority.append('\u4fee\u6539\u987a\u5e8f\uff1a\u5148\u6362\u4eba\uff08\u4e86\u89e3\u6df1\u5ea6\u4e0d\u591f\u6539\u6587\u5b57\u65e0\u6548\uff09\u2192 \u518d\u8865\u4e8b\u4f8b \u2192 '
                    '\u518d\u660e\u786e\u5f3a\u5ea6 \u2192 \u6700\u540e\u4fee\u8bed\u8a00')

    if any(it['result'] == '\u4e0d\u7b26\u5408' for it in items):
        verdict = '\u9700\u4fee\u6539'
    elif any(it['result'] == '\u9700\u5173\u6ce8' for it in items):
        verdict = '\u63a5\u8fd1\u5408\u683c'
    elif any(it['result'] == '\u5f85\u8865\u5145' for it in items):
        verdict = '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4'
    else:
        verdict = '\u5408\u683c'

    return {'scores': scores, 'total': rc['total'], 'items': items,
            'verdict': verdict, 'priority': priority}


def render_md(r):
    lines = ['# \u7559\u5b66\u63a8\u8350\u4fe1\u6838\u67e5\u7ed3\u679c', '']
    lines.append('- \u63a8\u8350\u4eba\u56db\u7ef4\u603b\u5206\uff1a%s' % (r['total'] if r['total'] is not None else '\u5f85\u8865\u5145'))
    lines.append('- \u5224\u5b9a\uff1a**%s**' % r['verdict'])
    lines.append('')
    lines.append('| \u6838\u67e5\u9879 | \u5224\u5b9a | \u8bf4\u660e | \u4fee\u6539\u65b9\u5411 |')
    lines.append('|---|---|---|---|')
    for it in r['items']:
        lines.append('| %s | %s | %s | %s |' % (it['name'], it['result'], it['detail'],
                                                it['advice'] or '\u2014'))
    lines.append('')
    if r['priority']:
        lines.append('## \u4fee\u6539\u65b9\u5411')
        lines.append('')
        for p in r['priority']:
            lines.append('- %s' % p)
        lines.append('')
    lines.append('> \u5b57\u6570\u533a\u95f4\u4e3a\u5e38\u89c1\u6574\u7406\uff0c\u5177\u4f53\u7bc7\u5e45\u4ee5\u76ee\u6807\u9662\u6821\u5f53\u5e74\u5b98\u7f51\u8981\u6c42\u4e3a\u51c6\uff1b'
                 '\u63a8\u8350\u4fe1\u5e94\u7531\u63a8\u8350\u4eba\u672c\u4eba\u64b0\u5199\u5e76\u7f72\u540d\u3002')
    return '\n'.join(lines)


def selftest():
    errors = []

    def mk(**kw):
        a = argparse.Namespace(relation=None, depth=None, title=None, willing=None,
                               words=None, limit=None, examples=None,
                               strength_level=None, relationship=None,
                               out=None, format='md')
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

    r1 = check(mk(relation=5, depth=4, title=4, willing=5, words=520,
                  examples=2, strength_level='top', relationship=1))
    eq('case01 \u56db\u7ef4\u603b\u5206 18', r1['total'], 18)
    eq('case02 \u63a8\u8350\u4eba\u53ef\u7528', item(r1, '\u63a8\u8350\u4eba\u53ef\u7528\u6027')['result'], '\u7b26\u5408')
    eq('case03 \u5b57\u6570 520 \u7b26\u5408', item(r1, '\u5b57\u6570')['result'], '\u7b26\u5408')
    eq('case04 \u4e8b\u4f8b 2 \u6761\u7b26\u5408', item(r1, '\u5177\u4f53\u4e8b\u4f8b')['result'], '\u7b26\u5408')
    eq('case05 \u5f3a\u5ea6 top \u7b26\u5408', item(r1, '\u63a8\u8350\u5f3a\u5ea6')['result'], '\u7b26\u5408')
    eq('case06 \u5173\u7cfb\u5df2\u5199\u7b26\u5408', item(r1, '\u5173\u7cfb\u8bf4\u660e')['result'], '\u7b26\u5408')
    eq('case07 \u7efc\u5408\u5224\u5b9a\u5408\u683c', r1['verdict'], '\u5408\u683c')

    r2 = check(mk(relation=3, depth=2, title=5, willing=3, words=520))
    eq('case08 \u4e86\u89e3\u6df1\u5ea6 2 \u5206\u5224\u4e0d\u7b26\u5408',
       item(r2, '\u63a8\u8350\u4eba\u53ef\u7528\u6027')['result'], '\u4e0d\u7b26\u5408')
    eq('case09 \u6df1\u5ea6\u4e0d\u8db3\u63d0\u793a\u6362\u4eba', '\u6362\u63a8\u8350\u4eba' in item(r2, '\u63a8\u8350\u4eba\u53ef\u7528\u6027')['advice'], True)

    r3 = check(mk(relation=3, depth=3, title=3, willing=3))
    eq('case10 \u603b\u5206 12 \u5224\u9700\u5173\u6ce8', item(r3, '\u63a8\u8350\u4eba\u53ef\u7528\u6027')['result'], '\u9700\u5173\u6ce8')
    r4 = check(mk(relation=2, depth=3, title=2, willing=2))
    eq('case11 \u603b\u5206 9 \u5224\u4e0d\u7b26\u5408', item(r4, '\u63a8\u8350\u4eba\u53ef\u7528\u6027')['result'], '\u4e0d\u7b26\u5408')

    eq('case12 \u5b57\u6570 280 \u4e0d\u7b26\u5408', item(check(mk(words=280)), '\u5b57\u6570')['result'], '\u4e0d\u7b26\u5408')
    eq('case13 \u5b57\u6570 350 \u9700\u5173\u6ce8', item(check(mk(words=350)), '\u5b57\u6570')['result'], '\u9700\u5173\u6ce8')
    eq('case14 \u5b57\u6570 650 \u9700\u5173\u6ce8', item(check(mk(words=650)), '\u5b57\u6570')['result'], '\u9700\u5173\u6ce8')
    eq('case15 \u5b57\u6570 800 \u4e0d\u7b26\u5408', item(check(mk(words=800)), '\u5b57\u6570')['result'], '\u4e0d\u7b26\u5408')
    eq('case16 \u8d85\u8fc7\u4f20\u5165\u4e0a\u9650\u5224\u4e0d\u7b26\u5408',
       item(check(mk(words=650, limit=600)), '\u5b57\u6570')['result'], '\u4e0d\u7b26\u5408')
    eq('case17 \u4e8b\u4f8b 0 \u6761\u5224\u4e0d\u7b26\u5408',
       item(check(mk(examples=0)), '\u5177\u4f53\u4e8b\u4f8b')['result'], '\u4e0d\u7b26\u5408')
    eq('case18 \u4e8b\u4f8b 1 \u6761\u5224\u9700\u5173\u6ce8',
       item(check(mk(examples=1)), '\u5177\u4f53\u4e8b\u4f8b')['result'], '\u9700\u5173\u6ce8')
    eq('case19 \u5f3a\u5ea6 none \u5224\u4e0d\u7b26\u5408',
       item(check(mk(strength_level='none')), '\u63a8\u8350\u5f3a\u5ea6')['result'], '\u4e0d\u7b26\u5408')
    eq('case20 \u5f3a\u5ea6 middle \u5224\u9700\u5173\u6ce8',
       item(check(mk(strength_level='middle')), '\u63a8\u8350\u5f3a\u5ea6')['result'], '\u9700\u5173\u6ce8')
    eq('case21 \u5173\u7cfb\u672a\u5199\u5224\u4e0d\u7b26\u5408',
       item(check(mk(relationship=0)), '\u5173\u7cfb\u8bf4\u660e')['result'], '\u4e0d\u7b26\u5408')
    eq('case22 \u65e0\u8f93\u5165\u5224\u9700\u8865\u5145\u4fe1\u606f', check(mk())['verdict'], '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4')
    r5 = check(mk(relation=5, depth=4, title=4, willing=5, words=520,
                  examples=1, strength_level='top', relationship=1))
    eq('case23 \u6709\u9700\u5173\u6ce8\u9879\u5224\u63a5\u8fd1\u5408\u683c', r5['verdict'], '\u63a5\u8fd1\u5408\u683c')
    eq('case24 \u4fee\u6539\u987a\u5e8f\u63d0\u793a\u5b58\u5728',
       any('\u4fee\u6539\u987a\u5e8f' in p for p in r1['priority']), True)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 24\n\u8986\u76d6: \u56db\u7ef4\u6253\u5206\u4e0e\u53ef\u7528\u6027/'
               '\u4e86\u89e3\u6df1\u5ea6\u4e0b\u9650/\u5b57\u6570\u4e94\u6863\u4e0e\u4f20\u5165\u4e0a\u9650/'
               '\u4e8b\u4f8b\u6761\u6570/\u63a8\u8350\u5f3a\u5ea6/\u5173\u7cfb\u8bf4\u660e/\u4fe1\u606f\u7f3a\u5931')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u7559\u5b66\u63a8\u8350\u4fe1\u4e0e\u63a8\u8350\u4eba\u6838\u67e5')
    ap.add_argument('--relation', type=int, help='\u5173\u8054\u5ea6 0~5')
    ap.add_argument('--depth', type=int, help='\u4e86\u89e3\u6df1\u5ea6 0~5')
    ap.add_argument('--title', type=int, help='\u804c\u79f0\u516c\u4fe1\u529b 0~5')
    ap.add_argument('--willing', type=int, help='\u8868\u8fbe\u610f\u613f 0~5')
    ap.add_argument('--words', type=int, help='\u63a8\u8350\u4fe1\u5b57\u6570')
    ap.add_argument('--limit', type=int, help='\u5b57\u6570\u4e0a\u9650')
    ap.add_argument('--examples', type=int, help='\u5177\u4f53\u4e8b\u4f8b\u6761\u6570')
    ap.add_argument('--strength-level', dest='strength_level',
                    choices=['top', 'middle', 'none'], help='\u63a8\u8350\u5f3a\u5ea6')
    ap.add_argument('--relationship', type=int, choices=[0, 1],
                    help='\u662f\u5426\u5199\u660e\u5173\u7cfb\u4e0e\u65f6\u957f')
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
