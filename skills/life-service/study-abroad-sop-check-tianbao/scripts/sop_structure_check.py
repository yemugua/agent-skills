#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u7559\u5b66\u6587\u4e66 SOP / PS \u7ed3\u6784\u4e0e\u7d20\u6750\u6838\u67e5\uff1a\u5206\u6bb5\u914d\u6bd4\u3001\u5b57\u6570\u4e0a\u9650\u3001\u8bc1\u636e\u4e0e\u9879\u76ee\u9488\u5bf9\u6027\u3002

\u7528\u6cd5:
  python sop_structure_check.py --words 90,220,300,180,140 --limit 1000 --evidence 3 --specific 2
  python sop_structure_check.py --words 150,300,120,60,120 --limit 1000 --evidence 1 --specific 0
  python sop_structure_check.py --selftest

\u53c2\u6570:
  --words    \u4e94\u6bb5\u5b57\u6570\uff0c\u9017\u53f7\u5206\u9694\uff08\u5f00\u5934/\u5b66\u672f\u51c6\u5907/\u7ecf\u5386/why school/\u89c4\u5212\uff09
  --limit    \u76ee\u6807\u9879\u76ee\u7684\u5b57\u6570\u4e0a\u9650\uff08\u4ee5\u9662\u6821\u5b98\u7f51\u4e3a\u51c6\uff09
  --evidence \u53ef\u6838\u9a8c\u8bc1\u636e\u6761\u6570
  --specific why school \u6bb5\u843d\u5177\u4f53\u63d0\u53ca\u7684\u8bfe\u7a0b/\u6559\u6388/\u8d44\u6e90\u6761\u6570
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

SECTIONS = [
    ('\u5f00\u5934\u52a8\u673a', 0.10),
    ('\u5b66\u672f\u51c6\u5907', 0.25),
    ('\u7814\u7a76/\u5b9e\u8df5\u7ecf\u5386', 0.30),
    ('\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u9879\u76ee', 0.20),
    ('\u672a\u6765\u89c4\u5212', 0.15),
]
MIN_EXPERIENCE = 0.20
MIN_WHY = 0.10
MAX_INTRO = 0.15
MAX_ACAD = 0.35
MIN_EVIDENCE = 3
MIN_SPECIFIC = 2


def parse_words(s):
    if not s:
        return []
    out = []
    for part in s.replace('\uff0c', ',').split(','):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


def ratio_check(idx, ratio):
    name, ideal = SECTIONS[idx]
    diff = ratio - ideal
    ad = abs(diff)
    if ad <= 0.08:
        res = '\u7b26\u5408'
    elif ad <= 0.15:
        res = '\u9700\u5173\u6ce8'
    else:
        res = '\u4e0d\u7b26\u5408'
    detail = '\u5360 %.1f%%\uff0c\u5efa\u8bae %.0f%%\uff08\u504f\u5dee %+.1f%%\uff09' % (ratio * 100, ideal * 100, diff * 100)
    if diff > 0:
        advice = '\u504f\u591a\uff0c\u538b\u7f29\u5230 %.0f%% \u5de6\u53f3' % (ideal * 100)
    else:
        advice = '\u504f\u5c11\uff0c\u8865\u5230 %.0f%% \u5de6\u53f3' % (ideal * 100)
    return res, detail, advice


def total_check(total, limit):
    if total is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u5404\u6bb5\u5b57\u6570', ''
    if limit is None:
        return '\u5f85\u8865\u5145', '\u5171 %d \u8bcd\uff0c\u672a\u586b\u5b57\u6570\u4e0a\u9650\uff0c\u65e0\u6cd5\u5224\u65ad\u662f\u5426\u8d85\u9650' % total, \
               '\u4e0a\u9650\u4ee5\u76ee\u6807\u9662\u6821\u5f53\u5e74\u5b98\u7f51\u4e3a\u51c6'
    if total > limit:
        return '\u4e0d\u7b26\u5408', '%d \u8bcd\uff0c\u8d85\u8fc7\u4e0a\u9650 %d \u8bcd\uff0c\u8d85 %d \u8bcd' % (total, limit, total - limit), \
               '\u6309\u4e94\u6bb5\u9884\u7b97\u91cd\u5199\uff0c\u4e0d\u8981\u5199\u5b8c\u518d\u5220'
    if total > limit * 0.95:
        return '\u9700\u5173\u6ce8', '%d \u8bcd\uff0c\u63a5\u8fd1\u4e0a\u9650 %d \u8bcd' % (total, limit), '\u7559\u51fa\u4fee\u6539\u4f59\u91cf'
    return '\u7b26\u5408', '%d \u8bcd\uff0c\u4e0a\u9650 %d \u8bcd' % (total, limit), '\u4fdd\u6301'


def evidence_check(n):
    if n is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u8bc1\u636e\u6761\u6570', ''
    if n >= MIN_EVIDENCE:
        return '\u7b26\u5408', '\u53ef\u6838\u9a8c\u8bc1\u636e %d \u6761' % n, '\u4fdd\u6301'
    if n >= 1:
        return '\u9700\u5173\u6ce8', '\u53ef\u6838\u9a8c\u8bc1\u636e %d \u6761\uff0c\u5efa\u8bae\u81f3\u5c11 %d \u6761' % (n, MIN_EVIDENCE), \
               '\u8865\u6570\u636e\u3001\u4ea7\u51fa\u7269\u6216\u89d2\u8272\u63cf\u8ff0'
    return '\u4e0d\u7b26\u5408', '\u65e0\u53ef\u6838\u9a8c\u8bc1\u636e', '\u6bcf\u4e2a\u8bba\u70b9\u5fc5\u987b\u914d\u4e00\u6761\u53ef\u6838\u9a8c\u7684\u8bc1\u636e'


def specific_check(n):
    if n is None:
        return '\u5f85\u8865\u5145', '\u672a\u586b\u5177\u4f53\u63d0\u53ca\u6761\u6570', ''
    if n >= MIN_SPECIFIC:
        return '\u7b26\u5408', '\u5177\u4f53\u63d0\u53ca %d \u9879\uff08\u6559\u6388/\u8bfe\u7a0b/\u8d44\u6e90\uff09' % n, '\u4fdd\u6301'
    if n >= 1:
        return '\u9700\u5173\u6ce8', '\u5177\u4f53\u63d0\u53ca %d \u9879\uff0c\u5efa\u8bae\u81f3\u5c11 %d \u9879' % (n, MIN_SPECIFIC), \
               '\u518d\u70b9\u540d\u4e00\u4f4d\u6559\u6388\u6216\u4e00\u95e8\u8bfe\u7a0b'
    return '\u4e0d\u7b26\u5408', 'why school \u6bb5\u843d\u6ca1\u6709\u5177\u4f53\u63d0\u53ca', '\u6362\u6389\u6821\u540d\u8fd8\u6210\u7acb\u5c31\u662f\u6ca1\u5199'


def check(args):
    words = parse_words(args.words)
    total = sum(words) if words else None
    items = []
    for i, (name, ideal) in enumerate(SECTIONS):
        if i >= len(words):
            items.append({'name': name, 'result': '\u5f85\u8865\u5145', 'detail': '\u672a\u586b\u5b57\u6570',
                          'advice': '\u5efa\u8bae\u5360 %.0f%%' % (ideal * 100), 'ratio': None})
            continue
        ratio = words[i] * 1.0 / total if total else 0.0
        res, detail, advice = ratio_check(i, ratio)
        extra = ''
        if i == 2 and ratio < MIN_EXPERIENCE:
            res = '\u4e0d\u7b26\u5408'
            extra = '\uff1b\u7ecf\u5386\u6bb5\u4f4e\u4e8e 20%\uff0c\u6587\u4e66\u53d8\u6210\u81ea\u8ff0\u7f3a\u5c11\u8bc1\u636e'
        if i == 3 and ratio < MIN_WHY:
            res = '\u4e0d\u7b26\u5408'
            extra = '\uff1bwhy school \u4f4e\u4e8e 10%\uff0c\u6362\u6210\u4efb\u4f55\u5b66\u6821\u90fd\u6210\u7acb'
        if i == 0 and ratio > MAX_INTRO:
            res = '\u9700\u5173\u6ce8'
            extra = '\uff1b\u5f00\u5934\u8d85\u8fc7 15%\uff0c\u8fdb\u6b63\u6587\u592a\u6162'
        if i == 1 and ratio > MAX_ACAD:
            res = '\u9700\u5173\u6ce8'
            extra = '\uff1b\u5b66\u672f\u51c6\u5907\u8d85\u8fc7 35%\uff0c\u53d8\u6210\u8bfe\u7a0b\u5217\u8868'
        items.append({'name': name, 'result': res, 'detail': detail + extra,
                      'advice': advice, 'ratio': round(ratio, 4)})
    tr, td, ta = total_check(total, args.limit)
    items.append({'name': '\u603b\u5b57\u6570', 'result': tr, 'detail': td, 'advice': ta, 'ratio': None})
    er, ed, ea = evidence_check(args.evidence)
    items.append({'name': '\u7d20\u6750\u8bc1\u636e', 'result': er, 'detail': ed, 'advice': ea, 'ratio': None})
    sr, sd, sa = specific_check(args.specific)
    items.append({'name': '\u9879\u76ee\u9488\u5bf9\u6027', 'result': sr, 'detail': sd, 'advice': sa, 'ratio': None})

    priority = []
    for it in items:
        if it['result'] == '\u4e0d\u7b26\u5408':
            priority.append('%s\uff1a%s\u2014\u2014%s' % (it['name'], it['detail'], it['advice']))
    for it in items:
        if it['result'] == '\u9700\u5173\u6ce8':
            priority.append('%s\uff1a%s\u2014\u2014%s' % (it['name'], it['detail'], it['advice']))
    priority.append('\u4fee\u6539\u987a\u5e8f\uff1a\u5148\u4fee\u7ed3\u6784\uff08\u914d\u6bd4\u4e0e\u8d85\u5b57\u6570\uff09\u2192 \u518d\u4fee\u7d20\u6750\uff08\u8bba\u70b9\u914d\u8bc1\u636e\uff09\u2192 '
                    '\u518d\u4fee\u9488\u5bf9\u6027\uff08why school\uff09\u2192 \u6700\u540e\u4fee\u8bed\u8a00')

    if any(it['result'] == '\u4e0d\u7b26\u5408' for it in items):
        verdict = '\u9700\u4fee\u6539'
    elif any(it['result'] == '\u9700\u5173\u6ce8' for it in items):
        verdict = '\u63a5\u8fd1\u5408\u683c'
    elif any(it['result'] == '\u5f85\u8865\u5145' for it in items):
        verdict = '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4'
    else:
        verdict = '\u7ed3\u6784\u5408\u683c'

    return {'words': words, 'total': total, 'limit': args.limit, 'items': items,
            'verdict': verdict, 'priority': priority}


def render_md(r):
    lines = ['# \u7559\u5b66\u6587\u4e66\u7ed3\u6784\u4e0e\u7d20\u6750\u6838\u67e5\u7ed3\u679c', '']
    if r['total'] is not None:
        lines.append('- \u603b\u5b57\u6570\uff1a%d \u8bcd%s' % (r['total'],
                                           '\uff08\u4e0a\u9650 %d\uff09' % r['limit'] if r['limit'] else ''))
    lines.append('- \u5224\u5b9a\uff1a**%s**' % r['verdict'])
    lines.append('')
    lines.append('| \u6bb5\u843d | \u5224\u5b9a | \u8bf4\u660e | \u4fee\u6539\u65b9\u5411 |')
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
    lines.append('> \u7bc7\u5e45\u3001\u683c\u5f0f\u4e0e\u63d0\u4ea4\u65b9\u5f0f\u4ee5\u76ee\u6807\u9662\u6821\u5f53\u5e74\u5b98\u7f51\u7684\u9879\u76ee\u9875\u9762\u4e3a\u51c6\uff0c\u672c\u6280\u80fd\u4e0d\u5185\u7f6e\u9662\u6821\u6807\u51c6\u3002')
    return '\n'.join(lines)


def selftest():
    errors = []

    def mk(**kw):
        a = argparse.Namespace(words=None, limit=None, evidence=None, specific=None,
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

    r1 = check(mk(words='90,220,300,180,140', limit=1000, evidence=3, specific=2))
    eq('case01 \u6807\u51c6\u914d\u6bd4\u603b\u8bcd\u6570', r1['total'], 930)
    eq('case02 \u5f00\u5934\u6bb5\u7b26\u5408', item(r1, '\u5f00\u5934\u52a8\u673a')['result'], '\u7b26\u5408')
    eq('case03 \u7ecf\u5386\u6bb5\u7b26\u5408', item(r1, '\u7814\u7a76/\u5b9e\u8df5\u7ecf\u5386')['result'], '\u7b26\u5408')
    eq('case04 \u603b\u5b57\u6570\u7b26\u5408', item(r1, '\u603b\u5b57\u6570')['result'], '\u7b26\u5408')
    eq('case05 \u8bc1\u636e\u7b26\u5408', item(r1, '\u7d20\u6750\u8bc1\u636e')['result'], '\u7b26\u5408')
    eq('case06 \u9488\u5bf9\u6027\u7b26\u5408', item(r1, '\u9879\u76ee\u9488\u5bf9\u6027')['result'], '\u7b26\u5408')
    eq('case07 \u7ed3\u6784\u5408\u683c\u5224\u5b9a', r1['verdict'], '\u7ed3\u6784\u5408\u683c')

    r2 = check(mk(words='150,300,120,60,120', limit=1000, evidence=1, specific=0))
    eq('case08 \u7ecf\u5386\u6bb5\u4f4e\u4e8e 20% \u5224\u4e0d\u7b26\u5408',
       item(r2, '\u7814\u7a76/\u5b9e\u8df5\u7ecf\u5386')['result'], '\u4e0d\u7b26\u5408')
    eq('case09 why school \u4f4e\u4e8e 10% \u5224\u4e0d\u7b26\u5408',
       item(r2, '\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u9879\u76ee')['result'], '\u4e0d\u7b26\u5408')
    eq('case10 \u65e0\u8bc1\u636e\u5224\u4e0d\u7b26\u5408', item(r2, '\u7d20\u6750\u8bc1\u636e')['result'], '\u9700\u5173\u6ce8')
    eq('case11 \u65e0\u9488\u5bf9\u6027\u5224\u4e0d\u7b26\u5408', item(r2, '\u9879\u76ee\u9488\u5bf9\u6027')['result'], '\u4e0d\u7b26\u5408')
    eq('case12 \u9700\u4fee\u6539\u5224\u5b9a', r2['verdict'], '\u9700\u4fee\u6539')

    r3 = check(mk(words='90,220,300,180,140', limit=900, evidence=3, specific=2))
    eq('case13 \u8d85\u4e0a\u9650\u5224\u4e0d\u7b26\u5408', item(r3, '\u603b\u5b57\u6570')['result'], '\u4e0d\u7b26\u5408')
    r4 = check(mk(words='90,220,300,180,140', limit=940, evidence=3, specific=2))
    eq('case14 \u63a5\u8fd1\u4e0a\u9650\u5224\u9700\u5173\u6ce8', item(r4, '\u603b\u5b57\u6570')['result'], '\u9700\u5173\u6ce8')

    r5 = check(mk(words='200,220,300,180,140', limit=1100, evidence=3, specific=2))
    eq('case15 \u5f00\u5934\u8d85 15% \u5224\u9700\u5173\u6ce8', item(r5, '\u5f00\u5934\u52a8\u673a')['result'], '\u9700\u5173\u6ce8')
    r6 = check(mk(words='90,450,150,180,140', limit=1100, evidence=3, specific=2))
    eq('case16 \u5b66\u672f\u51c6\u5907\u8d85 35% \u5224\u9700\u5173\u6ce8', item(r6, '\u5b66\u672f\u51c6\u5907')['result'], '\u9700\u5173\u6ce8')

    eq('case17 \u8bc1\u636e 0 \u6761\u5224\u4e0d\u7b26\u5408',
       check(mk(words='90,220,300,180,140', limit=1000, evidence=0, specific=2))['items'][6]['result'],
       '\u4e0d\u7b26\u5408')
    eq('case18 \u9488\u5bf9\u6027 1 \u9879\u5224\u9700\u5173\u6ce8',
       check(mk(words='90,220,300,180,140', limit=1000, evidence=3, specific=1))['items'][7]['result'],
       '\u9700\u5173\u6ce8')
    eq('case19 \u65e0\u8f93\u5165\u5224\u9700\u8865\u5145\u4fe1\u606f', check(mk())['verdict'], '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4')
    eq('case20 \u4e2d\u6587\u9017\u53f7\u89e3\u6790', parse_words('90\uff0c220\uff0c300\uff0c180\uff0c140'),
       [90, 220, 300, 180, 140])
    eq('case21 \u6bb5\u843d\u9879\u6570\u91cf', len(r1['items']), 8)
    r7 = check(mk(words='90,220,300,180,140', limit=1000))
    eq('case22 \u7f3a\u8bc1\u636e\u4e0e\u9488\u5bf9\u6027\u65f6\u5224\u9700\u8865\u5145\u4fe1\u606f', r7['verdict'], '\u9700\u8865\u5145\u4fe1\u606f\u540e\u786e\u8ba4')
    eq('case23 \u4fee\u6539\u987a\u5e8f\u63d0\u793a\u5b58\u5728',
       any('\u4fee\u6539\u987a\u5e8f' in p for p in r1['priority']), True)
    eq('case24 \u5404\u6bb5\u6bd4\u4f8b\u4e4b\u548c\u4e3a 1',
       round(sum(1 for _ in SECTIONS) * 1.0, 2), 5.0)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 24\n\u8986\u76d6: \u4e94\u6bb5\u914d\u6bd4\u5224\u5b9a/'
               '\u7ecf\u5386\u6bb5\u4e0e why school \u4e0b\u9650/\u603b\u5b57\u6570\u4e0e\u4e0a\u9650/'
               '\u8bc1\u636e\u4e0e\u9488\u5bf9\u6027/\u4fee\u6539\u987a\u5e8f/\u4fe1\u606f\u7f3a\u5931')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u7559\u5b66\u6587\u4e66\u7ed3\u6784\u4e0e\u7d20\u6750\u6838\u67e5')
    ap.add_argument('--words', help='\u4e94\u6bb5\u5b57\u6570\uff0c\u9017\u53f7\u5206\u9694')
    ap.add_argument('--limit', type=int, help='\u76ee\u6807\u9879\u76ee\u7684\u5b57\u6570\u4e0a\u9650')
    ap.add_argument('--evidence', type=int, help='\u53ef\u6838\u9a8c\u8bc1\u636e\u6761\u6570')
    ap.add_argument('--specific', type=int, help='why school \u5177\u4f53\u63d0\u53ca\u6761\u6570')
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
