#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GRE \u586b\u7a7a\u9898\u5e72\u4fe1\u53f7\u8bcd\u626b\u63cf\u3001\u7a7a\u683c\u6570\u4e0e\u65b9\u5411\u5224\u5b9a\u3001\u8bcd\u6c47\u80cc\u8bf5\u8986\u76d6\u7387\u6838\u7b97\u3002

\u7528\u6cd5:
  python gre_text_completion.py --file stem.txt
  python gre_text_completion.py --text "Although the claim is ___, the evidence is ___"
  python gre_text_completion.py --vocab vocab.txt --days 21
  python gre_text_completion.py --file stem.txt --vocab vocab.txt --days 21 --out out.md
  python gre_text_completion.py --selftest

\u53c2\u6570:
  --file       \u9898\u5e72\u6587\u672c\u6587\u4ef6\uff08UTF-8\uff09\uff0c\u7a7a\u683c\u53ef\u7528\u8fde\u7eed\u4e0b\u5212\u7ebf\u6807\u8bb0
  --text       \u76f4\u63a5\u4f20\u9898\u5e72\u5b57\u7b26\u4e32\uff0c\u4e0e --file \u4e8c\u9009\u4e00
  --vocab      \u8bcd\u6c47\u6587\u4ef6\uff0c\u6bcf\u884c \u5355\u8bcd<Tab>\u72b6\u6001\uff0c\u72b6\u6001 mastered / fuzzy / unknown
  --days       \u8ddd\u8003\u8bd5\u5929\u6570\uff0c\u7528\u4e8e\u7b97\u6bcf\u65e5\u65b0\u8bcd\u91cf
  --daily-cap  \u6bcf\u65e5\u65b0\u8bcd\u4e0a\u9650\uff0c\u9ed8\u8ba4 60
  --out        \u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84
  --format     md\uff08\u9ed8\u8ba4\uff09\u6216 json
  --selftest   \u8fd0\u884c\u5185\u7f6e\u81ea\u68c0
"""
import argparse
import json
import math
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SIGNALS = [
    ('\u8f6c\u6298\u5bf9\u6bd4', '\u53cd\u5411', r'\b(?:although|though|even though|but|yet|however|nevertheless|'
                         r'nonetheless|despite|in spite of|notwithstanding|whereas|'
                         r'while|on the contrary|by contrast|in contrast|conversely|'
                         r'paradoxically|ironically|surprisingly|unexpectedly|'
                         r'rather than|instead of|far from|on the other hand)\b'),
    ('\u56e0\u679c', '\u540c\u5411', r'\b(?:because|since|therefore|thus|hence|consequently|'
                     r'as a result|accordingly|thereby|given that|in that|due to|'
                     r'owing to|thanks to|so that|account for|result in|lead to)\b'),
    ('\u9012\u8fdb\u5f3a\u8c03', '\u540c\u5411', r'\b(?:moreover|furthermore|in addition|additionally|besides|'
                         r'what is more|indeed|in fact|particularly|especially|'
                         r'above all|most importantly)\b'),
    ('\u89e3\u91ca\u91cd\u8ff0', '\u540c\u4e49\u66ff\u6362', r'\b(?:that is|that is to say|namely|specifically|'
                             r'in other words|to wit|which means|which is to say)\b'),
    ('\u5e76\u5217', '\u540c\u5411', r'\b(?:and|as well as|both|either|neither|nor|likewise|similarly|'
                     r'in the same way|also|along with|together with|coupled with)\b'),
    ('\u4e3e\u4f8b', '\u5177\u4f53\u5316', r'\b(?:for example|for instance|such as|including|'
                       r'as illustrated by|as evidenced by|a case in point)\b'),
    ('\u8ba9\u6b65', '\u770b\u4e3b\u53e5', r'\b(?:admittedly|granted|to be sure|certainly|of course|'
                       r'no doubt|while it is true that)\b'),
    ('\u65f6\u95f4\u5bf9\u6bd4', '\u53cd\u5411', r'\b(?:previously|formerly|originally|initially|once|'
                         r'in the past|until recently|heretofore|no longer|now|today|'
                         r'currently|subsequently|since then|in recent years)\b'),
    ('\u5426\u5b9a', '\u53d6\u53cd', r'\b(?:not|no|never|none|without|lack|lacking|fail to|failed to|'
                     r'unable to|absent|absence of|anything but|other than|seldom|'
                     r'hardly|rarely|barely|few|deny|refute|undermine)\b'),
]
PUNCT_SIGNALS = [('\u89e3\u91ca\u91cd\u8ff0', '\u540c\u4e49\u66ff\u6362', r':'), ('\u89e3\u91ca\u91cd\u8ff0', '\u540c\u4e49\u66ff\u6362', r'--')]
BLANK_RE = re.compile(r'_{2,}')
ORDER = {'\u540c\u5411': '\u53cd\u5411', '\u53cd\u5411': '\u540c\u5411', '\u540c\u4e49\u66ff\u6362': '\u53cd\u5411', '\u5177\u4f53\u5316': '\u4e0d\u786e\u5b9a', '\u770b\u4e3b\u53e5': '\u4e0d\u786e\u5b9a'}
VALID_STATUS = ('mastered', 'fuzzy', 'unknown')


def scan(text):
    low = text.lower()
    hits = []
    seen = set()
    for cat, direction, pattern in SIGNALS:
        for m in re.finditer(pattern, low):
            w = m.group(0)
            if (cat, w) in seen:
                continue
            seen.add((cat, w))
            hits.append({'category': cat, 'word': w, 'direction': direction,
                         'pos': m.start()})
    for cat, direction, pattern in PUNCT_SIGNALS:
        for m in re.finditer(re.escape(pattern), text):
            hits.append({'category': cat, 'word': pattern, 'direction': direction,
                         'pos': m.start()})
    hits.sort(key=lambda x: x['pos'])
    return hits


def blanks_of(text):
    return len(BLANK_RE.findall(text))


def direction_of(hits, blanks):
    cats = [h['category'] for h in hits]
    neg_count = cats.count('\u5426\u5b9a')
    base = '\u4e0d\u786e\u5b9a'
    for cat in ('\u8f6c\u6298\u5bf9\u6bd4', '\u65f6\u95f4\u5bf9\u6bd4'):
        if cat in cats:
            base = '\u53cd\u5411'
            break
    if base == '\u4e0d\u786e\u5b9a':
        for cat in ('\u89e3\u91ca\u91cd\u8ff0', '\u56e0\u679c', '\u9012\u8fdb\u5f3a\u8c03', '\u5e76\u5217'):
            if cat in cats:
                base = ('\u540c\u4e49\u66ff\u6362' if cat == '\u89e3\u91ca\u91cd\u8ff0' else '\u540c\u5411')
                break
    if base == '\u4e0d\u786e\u5b9a' and '\u4e3e\u4f8b' in cats:
        base = '\u5177\u4f53\u5316'
    if base == '\u4e0d\u786e\u5b9a' and '\u8ba9\u6b65' in cats:
        base = '\u770b\u4e3b\u53e5'
    flipped = False
    if neg_count and base in ORDER:
        base = ORDER[base]
        flipped = True
    detail = '\u5224\u5b9a\u65b9\u5411\uff1a%s' % base
    if neg_count:
        detail += '\uff08\u68c0\u6d4b\u5230\u5426\u5b9a\u8bcd %d \u5904\uff0c\u5df2\u6309\u5426\u5b9a\u7ffb\u8f6c\u5904\u7406\uff0c\u8bf7\u4eba\u5de5\u590d\u6838\uff09' % neg_count
    if not cats:
        detail = '\u672a\u547d\u4e2d\u4fe1\u53f7\u8bcd\uff0c\u9700\u4eba\u5de5\u8bfb\u53e5\u5224\u65b9\u5411'
    order = '\u5355\u7a7a\u76f4\u63a5\u5b9a\u65b9\u5411'
    if blanks >= 3:
        order = '\u4e09\u7a7a\u9898\uff1a\u5148\u9501\u6700\u786e\u5b9a\u7684\u4e00\u7a7a\uff0c\u518d\u94fe\u5f0f\u63a8\u8fdb\uff08\u4e09\u7a7a\u5168\u5bf9\u624d\u5f97\u5206\uff09'
    elif blanks == 2:
        order = '\u53cc\u7a7a\u9898\uff1a\u5148\u505a\u6709\u660e\u786e\u4fe1\u53f7\u8bcd\u7684\u90a3\u4e00\u7a7a\uff0c\u518d\u63a8\u53e6\u4e00\u7a7a'
    elif blanks == 0:
        order = '\u672a\u68c0\u6d4b\u5230\u7a7a\u683c\u6807\u8bb0\uff0c\u7a7a\u683c\u53ef\u7528\u8fde\u7eed\u4e0b\u5212\u7ebf __ \u6807\u51fa'
    return {'direction': base, 'flipped': flipped, 'neg_count': neg_count,
            'detail': detail, 'order': order, 'blanks': blanks}


def load_vocab(path):
    words = []
    if not path or not os.path.exists(path):
        return words
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = re.split(r'[\t,]+', line)
            w = parts[0].strip()
            st = parts[1].strip().lower() if len(parts) > 1 else 'unknown'
            if st not in VALID_STATUS:
                st = 'unknown'
            words.append({'word': w, 'status': st})
    return words


def vocab_report(words, days, cap):
    total = len(words)
    mastered = len([w for w in words if w['status'] == 'mastered'])
    fuzzy = len([w for w in words if w['status'] == 'fuzzy'])
    unknown = len([w for w in words if w['status'] == 'unknown'])
    todo = fuzzy + unknown
    coverage = (mastered * 100.0 / total) if total else 0.0
    if total == 0:
        level, advice = '\u5f85\u8865\u5145', '\u672a\u63d0\u4f9b\u8bcd\u6c47\u6587\u4ef6\uff0c\u65e0\u6cd5\u6838\u7b97\u8986\u76d6\u7387'
    elif coverage < 50:
        level, advice = '\u4e0d\u7b26\u5408', '\u8986\u76d6\u7387\u4f4e\u4e8e 50%\uff0c\u8bcd\u6c47\u662f\u4e3b\u8981\u74f6\u9888\uff0c\u4f18\u5148\u8865\u9ad8\u9891\u8bcd'
    elif coverage < 75:
        level, advice = '\u5f85\u8865\u5145', '\u8986\u76d6\u7387 50%~75%\uff0c\u8fb9\u5237\u9898\u8fb9\u8865\uff0c\u91cd\u70b9\u6e05 fuzzy'
    elif coverage < 90:
        level, advice = '\u7b26\u5408', '\u8986\u76d6\u7387 75%~90%\uff0c\u8f6c\u653b\u957f\u96be\u53e5\u4e0e\u903b\u8f91'
    else:
        level, advice = '\u7b26\u5408', '\u8986\u76d6\u7387\u8d85\u8fc7 90%\uff0c\u53ea\u505a\u9519\u9898\u5f52\u56e0\u4e0e\u6a21\u8003'
    daily = None
    note = ''
    if days and days > 0:
        if todo == 0:
            daily = 0
            note = '\u5f85\u653b\u514b\u8bcd\u6570\u4e3a 0\uff0c\u53ea\u505a\u590d\u4e60'
        else:
            daily = int(math.ceil(todo * 1.0 / days))
            if days <= 15:
                daily = 0
                note = '\u5269\u4f59\u4e0d\u8db3 15 \u5929\uff0c\u4e0d\u518d\u52a0\u65b0\u8bcd\uff0c\u53ea\u590d\u4e60\u5df2\u6709\u8bcd\u8868\u4e0e\u9519\u9898\u8bcd'
            elif daily > cap:
                note = ('\u6309\u5929\u6570\u7b97\u9700\u6bcf\u65e5 %d \u4e2a\uff0c\u8d85\u8fc7\u4e0a\u9650 %d\uff0c'
                        '\u5efa\u8bae\u4f18\u5148\u6e05 fuzzy \u5e76\u5ef6\u957f\u5907\u8003\u5468\u671f' % (daily, cap))
                daily = cap
    return {'total': total, 'mastered': mastered, 'fuzzy': fuzzy, 'unknown': unknown,
            'todo': todo, 'coverage': round(coverage, 1), 'level': level,
            'advice': advice, 'days': days, 'daily': daily, 'note': note, 'cap': cap}


def check(args):
    text = args.text
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    if text is None:
        text = ''
    hits = scan(text)
    direc = direction_of(hits, blanks_of(text))
    vocab = vocab_report(load_vocab(args.vocab), args.days, args.daily_cap)
    return {'text_len': len(text), 'hits': hits, 'hit_count': len(hits),
            'direction': direc, 'vocab': vocab}


def render_md(r):
    lines = []
    lines.append('# GRE \u586b\u7a7a\u6838\u67e5\u7ed3\u679c')
    lines.append('')
    d = r['direction']
    lines.append('## \u4e00\u3001\u9898\u5e72\u4fe1\u53f7\u8bcd')
    lines.append('')
    lines.append('- \u6587\u672c\u957f\u5ea6\uff1a%d \u5b57\u7b26' % r['text_len'])
    lines.append('- \u547d\u4e2d\u4fe1\u53f7\u8bcd\uff1a%d \u4e2a' % r['hit_count'])
    lines.append('- \u7a7a\u683c\u6570\uff1a%d' % d['blanks'])
    lines.append('- %s' % d['detail'])
    lines.append('- \u89e3\u9898\u987a\u5e8f\uff1a%s' % d['order'])
    lines.append('')
    if r['hits']:
        lines.append('| \u7c7b\u522b | \u547d\u4e2d\u8bcd | \u65b9\u5411 | \u4f4d\u7f6e |')
        lines.append('|---|---|---|---|')
        for h in r['hits']:
            lines.append('| %s | %s | %s | %d |' % (h['category'], h['word'],
                                                    h['direction'], h['pos']))
    else:
        lines.append('\u672a\u547d\u4e2d\u4efb\u4f55\u4fe1\u53f7\u8bcd\uff0c\u9700\u4eba\u5de5\u8bfb\u53e5\u5224\u65b9\u5411\u3002')
    lines.append('')
    v = r['vocab']
    lines.append('## \u4e8c\u3001\u8bcd\u6c47\u8fdb\u5ea6')
    lines.append('')
    if v['total'] == 0:
        lines.append('- \u672a\u63d0\u4f9b\u8bcd\u6c47\u6587\u4ef6\uff0c\u8df3\u8fc7\u8986\u76d6\u7387\u6838\u7b97')
    else:
        lines.append('- \u8bcd\u8868\u603b\u8bcd\u6570\uff1a%d' % v['total'])
        lines.append('- mastered\uff1a%d / fuzzy\uff1a%d / unknown\uff1a%d' % (v['mastered'], v['fuzzy'], v['unknown']))
        lines.append('- \u8986\u76d6\u7387\uff1a**%.1f%%**\uff08\u5224\u5b9a\uff1a%s\uff09' % (v['coverage'], v['level']))
        lines.append('- \u5efa\u8bae\uff1a%s' % v['advice'])
        if v['days']:
            lines.append('- \u8ddd\u8003\u8bd5 %d \u5929\uff0c\u5f85\u653b\u514b %d \u8bcd' % (v['days'], v['todo']))
            if v['daily'] is not None:
                lines.append('- \u6bcf\u65e5\u65b0\u8bcd\u91cf\u5efa\u8bae\uff1a**%d** \u4e2a\uff08\u4e0a\u9650 %d\uff09' % (v['daily'], v['cap']))
            if v['note']:
                lines.append('- \u63d0\u793a\uff1a%s' % v['note'])
    lines.append('')
    lines.append('> \u65b9\u5411\u5224\u5b9a\u57fa\u4e8e\u4fe1\u53f7\u8bcd\u7edf\u8ba1\uff0c\u5b9e\u9645\u8bed\u4e49\u4ee5\u6574\u53e5\u7406\u89e3\u4e3a\u51c6\uff0c\u811a\u672c\u4e0d\u66ff\u4ee3\u4eba\u5de5\u5224\u65ad\u3002')
    return '\n'.join(lines)


def selftest():
    errors = []

    def mk(**kw):
        a = argparse.Namespace(file=None, text=None, vocab=None, days=None,
                               daily_cap=60, out=None, format='md')
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    tmp = os.path.dirname(os.path.abspath(__file__))
    stem = os.path.join(tmp, '_gre_stem.txt')
    voc = os.path.join(tmp, '_gre_vocab.txt')

    with open(stem, 'w', encoding='utf-8') as f:
        f.write('Although the theory was once widely accepted, recent evidence __ its core claim.')
    with open(voc, 'w', encoding='utf-8') as f:
        f.write('undermine\tmastered\nbolster\tfuzzy\ncursory\tunknown\n'
                'catastrophic\tmastered\nubiquitous\n')

    r1 = check(mk(file=stem))
    cats1 = [h['category'] for h in r1['hits']]
    eq('case01 \u547d\u4e2d\u8f6c\u6298\u5bf9\u6bd4', '\u8f6c\u6298\u5bf9\u6bd4' in cats1, True)
    eq('case02 \u547d\u4e2d\u65f6\u95f4\u5bf9\u6bd4', '\u65f6\u95f4\u5bf9\u6bd4' in cats1, True)
    eq('case03 \u8f6c\u6298\u5224\u53cd\u5411', r1['direction']['direction'], '\u53cd\u5411')
    eq('case04 \u672a\u547d\u4e2d\u5426\u5b9a\u8bcd\u65f6 flipped \u4e3a\u5047', r1['direction']['flipped'], False)

    r2 = check(mk(text='The results are not consistent, and the method is ___'))
    eq('case05 \u5426\u5b9a\u8bcd\u88ab\u8bc6\u522b', r2['direction']['neg_count'] >= 1, True)
    eq('case06 \u5426\u5b9a\u7ffb\u8f6c\u751f\u6548', r2['direction']['flipped'], True)

    r3 = check(mk(text='The manager is known for her __: she always meets every deadline.'))
    eq('case07 \u5192\u53f7\u89e6\u53d1\u89e3\u91ca\u91cd\u8ff0', '\u89e3\u91ca\u91cd\u8ff0' in [h['category'] for h in r3['hits']], True)
    eq('case08 \u89e3\u91ca\u91cd\u8ff0\u5224\u540c\u4e49\u66ff\u6362', r3['direction']['direction'], '\u540c\u4e49\u66ff\u6362')

    r4 = check(mk(text='A __ B __ C __ D'))
    eq('case09 \u4e09\u7a7a\u8bc6\u522b', r4['direction']['blanks'], 3)
    eq('case10 \u4e09\u7a7a\u89e3\u9898\u987a\u5e8f\u63d0\u793a', '\u4e09\u7a7a\u9898' in r4['direction']['order'], True)

    r5 = check(mk(text='A __ B __ C'))
    eq('case11 \u53cc\u7a7a\u89e3\u9898\u987a\u5e8f\u63d0\u793a', '\u53cc\u7a7a\u9898' in r5['direction']['order'], True)

    r6 = check(mk(text='The sky is blue'))
    eq('case12 \u65e0\u4fe1\u53f7\u8bcd\u65f6\u65b9\u5411\u4e0d\u786e\u5b9a', r6['direction']['direction'], '\u4e0d\u786e\u5b9a')
    eq('case13 \u65e0\u4fe1\u53f7\u8bcd\u65f6\u63d0\u793a\u4eba\u5de5\u5224', '\u4eba\u5de5\u8bfb\u53e5' in r6['direction']['detail'], True)

    r7 = check(mk(vocab=voc, days=21))
    v7 = r7['vocab']
    eq('case14 \u8bcd\u8868\u603b\u6570', v7['total'], 5)
    eq('case15 mastered \u6570', v7['mastered'], 2)
    eq('case16 fuzzy \u6570', v7['fuzzy'], 1)
    eq('case17 unknown \u6570\uff08\u7f3a\u7701\u8865 unknown\uff09', v7['unknown'], 2)
    eq('case18 \u8986\u76d6\u7387 40.0', v7['coverage'], 40.0)
    eq('case19 \u8986\u76d6\u7387\u4f4e\u4e8e 50 \u5224\u4e0d\u7b26\u5408', v7['level'], '\u4e0d\u7b26\u5408')
    eq('case20 \u6bcf\u65e5\u65b0\u8bcd\u91cf ceil(3/21)=1', v7['daily'], 1)

    r8 = check(mk(vocab=voc, days=10))
    eq('case21 \u5269\u4f59 10 \u5929\u4e0d\u518d\u52a0\u65b0\u8bcd', r8['vocab']['daily'], 0)

    voc2 = os.path.join(tmp, '_gre_vocab2.txt')
    with open(voc2, 'w', encoding='utf-8') as f:
        for i in range(100):
            f.write('word%03d\tunknown\n' % i)
    r9 = check(mk(vocab=voc2, days=20, daily_cap=1))
    eq('case22 \u6bcf\u65e5\u65b0\u8bcd\u5c01\u9876', r9['vocab']['daily'], 1)
    eq('case23 \u5c01\u9876\u63d0\u793a\u5b58\u5728', '\u8d85\u8fc7\u4e0a\u9650' in r9['vocab']['note'], True)
    eq('case23b \u5c01\u9876\u524d\u539f\u59cb\u9700\u6c42\u91cf 5', '\u6bcf\u65e5 5 \u4e2a' in r9['vocab']['note'], True)
    r9b = check(mk(vocab=voc2, days=20))
    eq('case23c \u672a\u5c01\u9876\u65f6\u6309\u5929\u6570\u7b97', r9b['vocab']['daily'], 5)

    r10 = check(mk())
    eq('case24 \u65e0\u8f93\u5165\u65f6\u8bcd\u6c47\u5f85\u8865\u5145', r10['vocab']['level'], '\u5f85\u8865\u5145')

    for p in (stem, voc, voc2):
        if os.path.exists(p):
            os.remove(p)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 24\n\u8986\u76d6: \u4e5d\u7c7b\u4fe1\u53f7\u8bcd\u547d\u4e2d/\u8f6c\u6298\u4e0e\u89e3\u91ca\u65b9\u5411\u5224\u5b9a/\u5426\u5b9a\u7ffb\u8f6c/'
               '\u53cc\u7a7a\u4e09\u7a7a\u89e3\u9898\u987a\u5e8f/\u65e0\u4fe1\u53f7\u8bcd/\u8bcd\u6c47\u8986\u76d6\u7387\u4e0e\u72b6\u6001\u7edf\u8ba1/\u6bcf\u65e5\u65b0\u8bcd\u91cf\u4e0e\u5c01\u9876')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='GRE \u586b\u7a7a\u89e3\u9898\u903b\u8f91\u4e0e\u8bcd\u6c47\u6838\u67e5')
    ap.add_argument('--file', help='\u9898\u5e72\u6587\u672c\u6587\u4ef6')
    ap.add_argument('--text', help='\u9898\u5e72\u5b57\u7b26\u4e32')
    ap.add_argument('--vocab', help='\u8bcd\u6c47\u6587\u4ef6\uff0c\u6bcf\u884c \u5355\u8bcd<Tab>\u72b6\u6001')
    ap.add_argument('--days', type=int, help='\u8ddd\u8003\u8bd5\u5929\u6570')
    ap.add_argument('--daily-cap', dest='daily_cap', type=int, default=60,
                    help='\u6bcf\u65e5\u65b0\u8bcd\u4e0a\u9650\uff0c\u9ed8\u8ba4 60')
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
