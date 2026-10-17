# -*- coding: utf-8 -*-
"""\u516c\u4f17\u53f7\u5f00\u5934\u6838\u67e5\uff1a\u957f\u5ea6\u3001\u53e5\u957f\u5206\u5e03\u3001\u6807\u9898\u91cd\u590d\u5ea6\u3001\u56db\u7c7b\u5e94\u907f\u5f00\u5199\u6cd5\u3002

\u7528\u6cd5:
  python opening_check.py --file article.json [--out result.md] [--format json]
  python opening_check.py --selftest
"""
import argparse
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# \u9996\u6bb5\u5b57\u6570\u9608\u503c
OPEN_MIN = 80
OPEN_BEST_LO = 80
OPEN_BEST_HI = 150
OPEN_MAX = 220
# \u9996\u53e5\u957f\u5ea6
FIRST_SENT_MIN = 10
FIRST_SENT_BEST_LO = 15
FIRST_SENT_BEST_HI = 30
# \u6807\u9898\u91cd\u590d\u5ea6\u4e0a\u9650\uff08\u5b57\u9762\u91cd\u5408\u5360\u6bd4\uff09
DUP_MAX = 0.40
# \u4fe1\u606f\u70b9\u5bc6\u5ea6\u533a\u95f4
DENSITY_LO = 0.5
DENSITY_HI = 1.0

OPENING_TYPES = ('conclusion', 'scene', 'number', 'counter', 'question', 'intro')

TYPE_CN = {
    'conclusion': '\u7ed3\u8bba\u5148\u884c\u578b',
    'scene': '\u573a\u666f\u5207\u5165\u578b',
    'number': '\u6570\u5b57\u6e05\u5355\u578b',
    'counter': '\u53cd\u5e38\u8bc6\u578b',
    'question': '\u63d0\u95ee\u5207\u5165\u578b',
    'intro': '\u81ea\u6211\u4ecb\u7ecd/\u94fa\u9648\u578b\uff08\u9700\u6539\uff09',
}

# \u81ea\u6211\u4ecb\u7ecd\u5f0f\u4fe1\u53f7
SELF_INTRO = ('\u5927\u5bb6\u597d', '\u6211\u662f', '\u5f88\u9ad8\u5174\u8ba4\u8bc6', '\u4eca\u5929\u60f3\u8ddf\u5927\u5bb6', '\u4eca\u5929\u7ed9\u5927\u5bb6',
              '\u672c\u4eba', '\u4ece\u4e8b', '\u5728\u884c\u4e1a')
# \u7a7a\u8bdd\u4fe1\u53f7
CLICHE = ('\u5728\u5f53\u4eca', '\u968f\u7740\u793e\u4f1a', '\u8d8a\u6765\u8d8a', '\u65e5\u76ca', '\u4f17\u6240\u5468\u77e5',
          '\u76f8\u4fe1\u5f88\u591a', '\u5728\u8fd9\u4e2a\u4fe1\u606f\u7206\u70b8', '\u8d4b\u80fd', '\u6293\u624b')
# \u9605\u8bfb\u6307\u5f15\u4fe1\u53f7
ROADMAP_HINTS = ('\u4e0b\u9762', '\u63a5\u4e0b\u6765', '\u7b2c\u4e00', '\u9996\u5148', '\u5176\u6b21', '\u7b2c\u4e09',
                 '\u4e09\u70b9', '\u4e09\u4e2a', '\u4e24\u4e2a\u65b9\u9762', '\u7b2c\u4e00\u90e8\u5206')
# \u6838\u5fc3\u627f\u8bfa\u4fe1\u53f7
PROMISE_HINTS = ('\u770b\u5b8c', '\u8bfb\u5b8c', '\u4f60\u5c06', '\u4f60\u4f1a', '\u80fd\u5e2e', '\u672c\u6587', '\u8fd9\u7bc7',
                 '\u6559\u4f60', '\u6559\u4f60\u5982\u4f55', '\u5e2e\u4f60')
# \u573a\u666f\u4fe1\u53f7
SCENE_HINTS = ('\u5468', '\u665a\u4e0a', '\u65e9\u4e0a', '\u5f53\u65f6', '\u90a3\u5929', '\u5750\u5728', '\u6253\u5f00\u7535\u8111',
               '\u6536\u5230', '\u53d1\u73b0', '\u4e0a\u5348', '\u4e0b\u5348')
# \u6570\u5b57\u4fe1\u53f7
NUM_RE = re.compile(r'\d+')

SENT_SPLIT = re.compile(r'[\u3002\uff01\uff1f!?\n]+')


def load(text=None, path=None):
    if text:
        return json.loads(text)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def first_paragraph(opening):
    """\u9996\u6bb5\uff1a\u4ee5\u7b2c\u4e00\u4e2a\u6362\u884c\u4e3a\u754c\u3002"""
    for line in (opening or '').split('\n'):
        if line.strip():
            return line.strip()
    return ''


def split_sentences(text):
    parts = [p.strip() for p in SENT_SPLIT.split(text or '') if p.strip()]
    return parts


def opening_check(opening):
    para = first_paragraph(opening)
    n = len(para)
    sents = split_sentences(para)
    lens = [len(s) for s in sents]
    if n == 0:
        return {'n': 0, 'verdict': '\u672a\u586b\u5f00\u5934', 'sentences': 0,
                'avg': 0, 'max': 0, 'min': 0, 'first_len': 0}
    if OPEN_BEST_LO <= n <= OPEN_BEST_HI:
        grade = '\u6700\u4f73\u533a\u95f4'
    elif n < OPEN_MIN:
        grade = '\u504f\u77ed\uff0c\u53ef\u80fd\u4fe1\u606f\u91cf\u4e0d\u8db3'
    elif n <= OPEN_MAX:
        grade = '\u53ef\u7528'
    else:
        grade = '\u504f\u957f\uff0c\u5b58\u5728\u94fa\u57ab\u8fc7\u591a\u98ce\u9669'
    return {'n': n, 'verdict': grade, 'sentences': len(sents),
            'avg': round(sum(lens) / len(lens), 1) if lens else 0,
            'max': max(lens) if lens else 0, 'min': min(lens) if lens else 0,
            'first_len': lens[0] if lens else 0}


def dup_check(title, opening):
    """\u6807\u9898\u4e0e\u9996\u6bb5\u7684\u5b57\u9762\u91cd\u5408\u5360\u6bd4\uff08\u6309\u5b57\u7b26\u96c6\u5408\u4ea4\u96c6\u8fd1\u4f3c\uff09\u3002"""
    t = title or ''
    o = first_paragraph(opening)
    if not t or not o:
        return {'rate': 0.0, 'state': '\u65e0\u6cd5\u5224\u5b9a'}
    tc = set(t)
    s0 = split_sentences(o)
    base = len(s0[0]) if s0 else len(o)
    rate = round(len(tc & set(s0[0] if s0 else o)) * 1.0 / base, 3) if base else 0.0
    state = '\u504f\u9ad8\uff0c\u5b58\u5728\u6807\u9898\u539f\u53e5\u590d\u8ff0\u98ce\u9669' if rate > DUP_MAX else '\u5408\u89c4'
    return {'rate': rate, 'state': state}


def density_check(opening, sentences):
    """\u4fe1\u606f\u70b9\u5bc6\u5ea6\uff1a\u6709\u6548\u4fe1\u53f7\u6570 / \u53e5\u6570\u3002"""
    para = first_paragraph(opening)
    if not para or not sentences:
        return 0.0
    pts = 0
    if any(w in para for w in PROMISE_HINTS):
        pts += 1
    if any(w in para for w in ROADMAP_HINTS):
        pts += 1
    if any(w in para for w in SCENE_HINTS):
        pts += 1
    if NUM_RE.search(para):
        pts += 1
    if any(w in para for w in CLICHE):
        pts += 0
    return round(pts * 1.0 / len(sentences), 3)


def avoid_check(opening):
    """\u56db\u7c7b\u5e94\u907f\u5f00\u7684\u5199\u6cd5\u3002"""
    para = first_paragraph(opening)
    head = '\n'.join((opening or '').split('\n')[:2])
    rows = []
    intro_hits = [w for w in SELF_INTRO if w in head]
    if intro_hits:
        rows.append({'kind': '\u81ea\u6211\u4ecb\u7ecd\u5f0f\u5f00\u573a', 'hit': intro_hits[0],
                     'fix': '\u5220\u6389\u4ecb\u7ecd\uff0c\u7b2c\u4e00\u53e5\u76f4\u63a5\u8fdb\u4e3b\u9898'})
    cliche_hits = [w for w in CLICHE if w in head]
    if cliche_hits:
        rows.append({'kind': '\u7a7a\u8bdd\u5f00\u573a', 'hit': cliche_hits[0],
                     'fix': '\u6362\u6210\u5177\u4f53\u6570\u636e\u6216\u573a\u666f'})
    bg = len(first_paragraph(opening))
    if bg > OPEN_MAX:
        rows.append({'kind': '\u957f\u94fa\u57ab', 'hit': '\u9996\u6bb5 %d \u5b57' % bg,
                     'fix': '\u80cc\u666f\u538b\u7f29\u5230 2 \u53e5\u4ee5\u5185'})
    if (not any(w in head for w in PROMISE_HINTS)
            and not any(w in head for w in ROADMAP_HINTS)):
        rows.append({'kind': '\u7f3a\u5c11\u6838\u5fc3\u627f\u8bfa', 'hit': '\u9996\u6bb5\u672a\u89c1\u627f\u8bfa\u7c7b\u8868\u8ff0',
                     'fix': '\u8865\u4e00\u53e5\u300c\u770b\u5b8c\u4f60\u80fd\u2026\u2026\u300d'})
    return rows


def rhythm_check(opening):
    """\u53e5\u957f\u8282\u594f\uff1a\u8fde\u7eed\u4e09\u53e5\u957f\u5ea6\u76f8\u8fd1\u5224\u4e3a\u8282\u594f\u5e73\u3002"""
    sents = split_sentences(first_paragraph(opening))
    lens = [len(s) for s in sents]
    flat = False
    if len(lens) >= 3:
        a, b, c = lens[-3], lens[-2], lens[-1]
        spread = max(a, b, c) - min(a, b, c)
        if spread <= 4:
            flat = True
    first = lens[0] if lens else 0
    if first and FIRST_SENT_BEST_LO <= first <= FIRST_SENT_BEST_HI:
        fs = '\u6700\u4f73'
    elif first and first >= FIRST_SENT_MIN:
        fs = '\u53ef\u63a5\u53d7'
    elif first:
        fs = '\u504f\u77ed'
    else:
        fs = '\u65e0\u9996\u53e5'
    return {'lens': lens, 'flat': flat, 'first_state': fs}


def build(data, fmt='md'):
    title = data.get('title') or ''
    opening = data.get('opening') or ''
    o = opening_check(opening)
    d = dup_check(title, opening)
    sents = split_sentences(first_paragraph(opening))
    dens = density_check(opening, sents)
    avoid = avoid_check(opening)
    r = rhythm_check(opening)
    otype = (data.get('opening_type') or '').strip()
    otype_cn = TYPE_CN.get(otype, '\u672a\u6807\u6ce8')

    if fmt == 'json':
        return {'title': title, 'opening_len': o['n'],
                'opening_verdict': o['verdict'], 'sentence_count': o['sentences'],
                'avg_sentence_len': o['avg'], 'max_sentence_len': o['max'],
                'min_sentence_len': o['min'],
                'first_sentence_len': o['first_len'],
                'first_sentence_state': r['first_state'],
                'dup_rate': d['rate'], 'dup_state': d['state'],
                'density': dens, 'rhythm_flat': r['flat'],
                'opening_type': otype_cn, 'avoid_rows': avoid,
                'core_promise': bool(data.get('core_promise')),
                'relevance': bool(data.get('relevance')),
                'roadmap': bool(data.get('roadmap'))}

    out = []
    out.append('# \u516c\u4f17\u53f7\u5f00\u5934\u4f53\u68c0')
    out.append('')
    out.append('- \u6807\u9898\uff1a%s' % (title or '\uff08\u672a\u586b\uff09'))
    out.append('- \u9996\u6bb5\u5b57\u6570\uff1a%d\uff08\u6700\u4f73 %d-%d\uff0c\u8d85\u8fc7 %d \u6613\u5f62\u6210\u957f\u94fa\u57ab\uff09'
               % (o['n'], OPEN_BEST_LO, OPEN_BEST_HI, OPEN_MAX))
    out.append('- \u9996\u6bb5\u5224\u5b9a\uff1a%s' % o['verdict'])
    out.append('- \u53e5\u6570\uff1a%d\uff0c\u5e73\u5747\u53e5\u957f %s \u5b57\uff0c\u6700\u957f %d\uff0c\u6700\u77ed %d'
               % (o['sentences'], o['avg'], o['max'], o['min']))
    out.append('- \u9996\u53e5\u957f\u5ea6\uff1a%d\uff08%s\uff09' % (o['first_len'], r['first_state']))
    out.append('- \u6807\u9898\u91cd\u590d\u5ea6\uff1a%.1f%%\uff08\u4e0a\u9650 %.0f%%\uff09' % (d['rate'] * 100, DUP_MAX * 100))
    out.append('- \u91cd\u590d\u5ea6\u5224\u5b9a\uff1a%s' % d['state'])
    out.append('- \u4fe1\u606f\u70b9\u5bc6\u5ea6\uff1a%s\uff08\u5efa\u8bae %.1f-%.1f\uff09' % (dens, DENSITY_LO, DENSITY_HI))
    out.append('- \u53e5\u957f\u8282\u594f\u5e73\uff1a%s' % ('\u662f' if r['flat'] else '\u5426'))
    out.append('- \u5f00\u5934\u5199\u6cd5\uff1a%s' % otype_cn)
    out.append('- \u4e09\u8981\u7d20\uff1a\u6838\u5fc3\u627f\u8bfa %s\uff5c\u76f8\u5173\u6027 %s\uff5c\u9605\u8bfb\u6307\u5f15 %s'
               % ('\u6709' if data.get('core_promise') else '\u65e0',
                  '\u6709' if data.get('relevance') else '\u65e0',
                  '\u6709' if data.get('roadmap') else '\u65e0'))
    out.append('')
    out.append('## \u4e00\u3001\u957f\u5ea6\u4e0e\u53e5\u957f')
    out.append('')
    if o['n'] == 0:
        out.append('\u672a\u586b\u5f00\u5934\u3002\u5148\u5199\u4e00\u53e5\u8bdd\u6838\u5fc3\u627f\u8bfa\uff0c\u518d\u6309\u4e94\u7c7b\u5199\u6cd5\u62df 3 \u4e2a\u5907\u9009\u3002')
    else:
        out.append('- \u9996\u6bb5 %d \u5b57\uff1a%s' % (o['n'], o['verdict']))
        out.append('- \u9996\u53e5 %d \u5b57\uff08%s\uff09\uff1a\u5efa\u8bae 15-30 \u5b57' % (o['first_len'], r['first_state']))
        out.append('- \u53e5\u957f\u5206\u5e03\uff1a%s' % (r['lens'] if r['lens'] else '\u65e0'))
        if r['flat']:
            out.append('- \u672b\u4e09\u53e5\u957f\u5ea6\u63a5\u8fd1\uff0c\u8282\u594f\u504f\u5e73\uff1a\u4e3b\u52a8\u5236\u9020\u957f\u77ed\u843d\u5dee\uff08\u8f6c\u6298\u53e5\u7528\u77ed\u53e5\uff09\u3002')
    out.append('')
    out.append('## \u4e8c\u3001\u6807\u9898\u91cd\u590d\u5ea6')
    out.append('')
    out.append('- \u91cd\u5408\u5360\u6bd4 %.1f%%\uff1a%s' % (d['rate'] * 100, d['state']))
    if d['rate'] > DUP_MAX:
        out.append('- \u6807\u9898\u539f\u53e5\u88ab\u8bfb\u8005\u63d0\u524d\u8bfb\u5230\u4f1a\u964d\u4f4e\u7ee7\u7eed\u9605\u8bfb\u610f\u613f\u3002\u6539\u7528\u5177\u4f53\u573a\u666f\u6216\u6570\u636e\u5f00\u7bc7\u3002')
    out.append('')
    out.append('## \u4e09\u3001\u4fe1\u606f\u70b9\u5bc6\u5ea6')
    out.append('')
    if dens < DENSITY_LO:
        out.append('\u5bc6\u5ea6\u504f\u4f4e\uff08%s\uff09\uff1a\u9996\u6bb5\u591a\u662f\u94fa\u57ab\u6216\u80cc\u666f\u3002\u538b\u7f29\u80cc\u666f\uff0c\u7528\u573a\u666f\u6216\u6570\u636e\u8fdb\u4e3b\u9898\u3002' % dens)
    elif dens > DENSITY_HI:
        out.append('\u5bc6\u5ea6\u504f\u9ad8\uff08%s\uff09\uff1a\u9996\u6bb5\u585e\u4e86\u8fc7\u591a\u8bba\u70b9\u3002\u53ea\u7559 1 \u4e2a\u6838\u5fc3\u627f\u8bfa + 1 \u4e2a\u94a9\u5b50\u3002' % dens)
    else:
        out.append('\u5bc6\u5ea6 %s \u5904\u4e8e\u5efa\u8bae\u533a\u95f4\uff08%.1f-%.1f\uff09\u3002' % (dens, DENSITY_LO, DENSITY_HI))
    out.append('')
    out.append('## \u56db\u3001\u5e94\u907f\u5f00\u7684\u5199\u6cd5')
    out.append('')
    if not avoid:
        out.append('\u672a\u547d\u4e2d\u56db\u7c7b\u5e94\u907f\u5f00\u7684\u5199\u6cd5\u3002\u4ecd\u9700\u4eba\u5de5\u786e\u8ba4\u6ca1\u6709\u5ba2\u5957\u8bdd\u4e0e\u65e0\u6548\u5f62\u5bb9\u8bcd\u3002')
    else:
        out.append('| \u7c7b\u578b | \u547d\u4e2d | \u6539\u6cd5 |')
        out.append('|---|---|---|')
        for x in avoid:
            out.append('| %s | %s | %s |' % (x['kind'], x['hit'], x['fix']))
    out.append('')
    out.append('## \u4e94\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if o['n'] == 0:
        idx += 1
        out.append('%d. \u672a\u586b\u5f00\u5934\uff1a\u5148\u5b9a\u4e00\u53e5\u8bdd\u6838\u5fc3\u627f\u8bfa\uff0c\u518d\u9009\u4e94\u7c7b\u5199\u6cd5\u4e4b\u4e00\u3002' % idx)
    elif o['n'] > OPEN_MAX:
        idx += 1
        out.append('%d. \u9996\u6bb5 %d \u5b57\u504f\u957f\uff1a\u80cc\u666f\u538b\u7f29\u5230 2 \u53e5\u4ee5\u5185\uff0c\u79fb\u52a8\u7aef\u9996\u5c4f\u53ea\u6709 4-5 \u884c\u3002'
                   % (idx, o['n']))
    elif o['n'] < OPEN_MIN:
        idx += 1
        out.append('%d. \u9996\u6bb5\u4ec5 %d \u5b57\uff0c\u53ef\u80fd\u4fe1\u606f\u91cf\u4e0d\u8db3\uff1a\u8865\u4e00\u4e2a\u5177\u4f53\u573a\u666f\u6216\u6570\u636e\u3002' % (idx, o['n']))
    if r['first_state'] in ('\u504f\u77ed',):
        idx += 1
        out.append('%d. \u9996\u53e5\u504f\u77ed\uff1a15-30 \u5b57\u66f4\u5229\u4e8e\u4e00\u53e3\u6c14\u8bfb\u5b8c\u3002' % idx)
    if d['rate'] > DUP_MAX:
        idx += 1
        out.append('%d. \u6807\u9898\u91cd\u590d\u5ea6 %.1f%% \u504f\u9ad8\uff1a\u5f00\u5934\u4e0d\u8981\u590d\u8ff0\u6807\u9898\u539f\u53e5\u3002'
                   % (idx, d['rate'] * 100))
    if r['flat']:
        idx += 1
        out.append('%d. \u672b\u4e09\u53e5\u957f\u5ea6\u63a5\u8fd1\uff1a\u8f6c\u6298\u53e5\u6539\u77ed\u53e5\uff0c\u5236\u9020\u957f\u77ed\u843d\u5dee\u3002' % idx)
    if not data.get('core_promise'):
        idx += 1
        out.append('%d. \u7f3a\u6838\u5fc3\u627f\u8bfa\uff1a\u9996\u6bb5\u8865\u4e00\u53e5\u300c\u770b\u5b8c\u4f60\u80fd\u2026\u2026\u300d\u3002' % idx)
    if not data.get('relevance'):
        idx += 1
        out.append('%d. \u7f3a\u76f8\u5173\u6027\uff1a\u8bf4\u660e\u8fd9\u4e2a\u95ee\u9898\u7684\u539f\u56e0\uff0c\u8ba9\u8bfb\u8005\u786e\u8ba4\u300c\u8bf4\u7684\u662f\u6211\u300d\u3002' % idx)
    if not data.get('roadmap'):
        idx += 1
        out.append('%d. \u7f3a\u9605\u8bfb\u6307\u5f15\uff1a\u957f\u6587\u5f00\u5934\u70b9\u660e\u7ed3\u6784\uff08\u5982\u300c\u4e0b\u9762\u8bb2\u4e09\u70b9\u300d\uff09\u3002' % idx)
    if otype == 'intro':
        idx += 1
        out.append('%d. \u5f00\u5934\u5199\u6cd5\u6807\u6ce8\u4e3a\u81ea\u6211\u4ecb\u7ecd/\u94fa\u9648\u578b\uff1a\u6539\u7528\u7ed3\u8bba\u5148\u884c\u3001\u573a\u666f\u5207\u5165\u7b49\u4e94\u7c7b\u5199\u6cd5\u3002' % idx)
    if not idx:
        out.append('\u957f\u5ea6\u3001\u91cd\u590d\u5ea6\u3001\u5bc6\u5ea6\u4e0e\u8282\u594f\u5747\u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\u3002\u53d1\u5e03\u524d\u786e\u8ba4\u6807\u9898\u627f\u8bfa\u5728\u6b63\u6587\u4e2d\u5df2\u5151\u73b0\uff0c'
                   '\u5f15\u7528\u4ed6\u4eba\u5185\u5bb9\u4e0e\u6570\u636e\u5df2\u6807\u6ce8\u6765\u6e90\u3002')
    out.append('')
    return '\n'.join(out)


def selftest():
    ok = 0
    fails = []

    def chk(cond, name):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(name)

    good = {
        'title': '\u4e3a\u4ec0\u4e48\u4f60\u7684\u65b9\u6848\u603b\u662f\u6539\u5230\u7b2c\u4e03\u7248',
        'opening': '\u4e0a\u5468\u4e09\u665a\u4e0a\u5341\u70b9\uff0c\u7b2c\u4e03\u7248\u6539\u5230\u7b2c 3 \u9875\u3002\u540c\u4e00\u4e2a\u65b9\u6848\uff0c\u7b2c\u4e09\u7248\u5230\u7b2c\u4e03\u7248\u53ea\u6539\u4e86\u4e24\u884c\u5b57\u3002'
                   '\u6211\u5728 40 \u4efd\u65b9\u6848\u91cc\u505a\u4e86\u7edf\u8ba1\uff0c\u65b9\u5411\u8d8a\u660e\u786e\u7684\u90a3\u6279\u5e73\u5747\u5c11\u6539 1.8 \u7248\u3002\u4e0b\u9762\u8bb2\u4e09\u70b9\u539f\u56e0\u3002',
        'core_promise': True, 'relevance': True, 'roadmap': True,
        'opening_type': 'scene',
    }
    r = build(good, 'json')
    chk(r['opening_len'] > OPEN_MIN, '\u6b63\u5e38\u5f00\u5934\u5e94\u8d85\u8fc7 80 \u5b57')
    chk(r['opening_verdict'] == '\u6700\u4f73\u533a\u95f4', '\u6b63\u5e38\u957f\u5ea6\u5e94\u5c5e\u6700\u4f73\u533a\u95f4')
    chk(r['sentence_count'] >= 3, '\u5e94\u5207\u51fa\u81f3\u5c11 3 \u53e5')
    chk(r['avg_sentence_len'] > 0, '\u5e73\u5747\u53e5\u957f\u5e94\u5927\u4e8e 0')
    chk(r['dup_rate'] <= DUP_MAX, '\u4e0d\u91cd\u590d\u7684\u5f00\u5934\u91cd\u590d\u5ea6\u5e94\u4e0d\u8d85\u4e0a\u9650')
    chk(r['opening_type'] == '\u573a\u666f\u5207\u5165\u578b', 'scene \u5e94\u6620\u5c04\u4e3a\u573a\u666f\u5207\u5165\u578b')
    chk(len(r['avoid_rows']) == 0, '\u89c4\u8303\u5f00\u5934\u4e0d\u5e94\u547d\u4e2d\u907f\u6cd5')

    r = build({'opening': ''}, 'json')
    chk(r['opening_len'] == 0, '\u672a\u586b\u5f00\u5934\u957f\u5ea6\u4e3a 0')
    chk(r['opening_verdict'] == '\u672a\u586b\u5f00\u5934', '\u672a\u586b\u5f00\u5934\u5e94\u5224\u5b9a\u4e3a\u672a\u586b\u5f00\u5934')
    chk(len(r['avoid_rows']) >= 1, '\u672a\u586b\u5f00\u5934\u4e5f\u5e94\u63d0\u793a\u7f3a\u6838\u5fc3\u627f\u8bfa')

    intro = {'opening': '\u5927\u5bb6\u597d\uff0c\u6211\u662f\u8001\u674e\uff0c\u505a\u4e86 8 \u5e74\u4ea7\u54c1\u3002\u4eca\u5929\u60f3\u8ddf\u5927\u5bb6\u804a\u804a\u6539\u7a3f\u8fd9\u4ef6\u4e8b\u3002'
                        '\u5728\u5f53\u4eca\u5feb\u901f\u53d1\u5c55\u7684\u65f6\u4ee3\uff0c\u6548\u7387\u975e\u5e38\u91cd\u8981\u3002'}
    r = build(intro, 'json')
    kinds = [x['kind'] for x in r['avoid_rows']]
    chk('\u81ea\u6211\u4ecb\u7ecd\u5f0f\u5f00\u573a' in kinds, '\u81ea\u6211\u4ecb\u7ecd\u5f0f\u5e94\u547d\u4e2d')
    chk('\u7a7a\u8bdd\u5f00\u573a' in kinds, '\u7a7a\u8bdd\u5f00\u573a\u5e94\u547d\u4e2d')

    dup = {'title': '\u4e3a\u4ec0\u4e48\u4f60\u7684\u65b9\u6848\u603b\u662f\u6539\u5230\u7b2c\u4e03\u7248',
           'opening': '\u4e3a\u4ec0\u4e48\u4f60\u7684\u65b9\u6848\u603b\u662f\u6539\u5230\u7b2c\u4e03\u7248\uff1f\u8fd9\u4e2a\u95ee\u9898\u56f0\u6270\u4e86\u5f88\u591a\u4eba\uff0c'
                      '\u76f8\u4fe1\u5f88\u591a\u670b\u53cb\u90fd\u6709\u8fd9\u6837\u7684\u56f0\u6270\uff0c\u4e0b\u9762\u6211\u4eec\u4e00\u8d77\u6765\u770b\u770b\u3002'}
    r = build(dup, 'json')
    chk(r['dup_rate'] > DUP_MAX, '\u590d\u8ff0\u6807\u9898\u5e94\u5224\u91cd\u590d\u5ea6\u504f\u9ad8')

    flat = {'opening': 'aaa bbb ccc ddd eee fff ggg hhh iii jjj kkk\u3002'
                       'll mmm nnn ooo ppp qqq rrr sss ttt uuu vvv w\u3002'
                       'xx yyy zzz aaa bbb ccc ddd eee fff ggg hhh\u3002'}
    r = build(flat, 'json')
    chk(r['rhythm_flat'] is True, '\u672b\u4e09\u53e5\u957f\u5ea6\u76f8\u8fd1\u5e94\u5224\u8282\u594f\u5e73')

    uneven = {'opening': '\u53ea\u6709\u4e00\u53e5\u5f88\u77ed\u3002\u7b2c\u4e8c\u53e5\u660e\u663e\u957f\u4e86\u5f88\u591a\u5f88\u591a\u5f88\u591a\u5f88\u591a\u5f88\u591a\u5f88\u591a\uff0c'
                         '\u627f\u8f7d\u4e86\u66f4\u591a\u7684\u903b\u8f91\u5185\u5bb9\u5728\u91cc\u9762\u8bf4\u660e\u95ee\u9898\u3002\u7b2c\u4e09\u53e5\u77ed\u3002'}
    r = build(uneven, 'json')
    chk(r['rhythm_flat'] is False, '\u957f\u77ed\u843d\u5dee\u660e\u663e\u4e0d\u5e94\u5224\u8282\u594f\u5e73')

    long_bg = {'opening': '\u968f\u7740\u793e\u4f1a\u53d1\u5c55\uff0c\u4f01\u4e1a\u8d8a\u6765\u8d8a\u91cd\u89c6\u6548\u7387\u7ba1\u7406\u3002' * 12}
    r = build(long_bg, 'json')
    kinds = [x['kind'] for x in r['avoid_rows']]
    chk('\u957f\u94fa\u57ab' in kinds, '\u8d85\u957f\u9996\u6bb5\u5e94\u547d\u4e2d\u957f\u94fa\u57ab')

    otype = {'opening': '\u8fd9\u7bc7\u8bb2\u7684\u4e0d\u662f\u65b9\u6cd5\u8bba\uff0c\u662f\u4e09\u4e2a\u53ef\u4ee5\u76f4\u63a5\u6284\u7684\u64cd\u4f5c\u3002\u770b\u5b8c\u4f60\u80fd\u7acb\u523b\u6539\u6389\u91cd\u590d\u52b3\u52a8\u3002',
             'opening_type': 'intro'}
    r = build(otype, 'json')
    chk(r['opening_type'] == '\u81ea\u6211\u4ecb\u7ecd/\u94fa\u9648\u578b\uff08\u9700\u6539\uff09', 'intro \u7c7b\u578b\u5e94\u6620\u5c04\u4e3a\u9700\u6539\u5199\u6cd5')

    r = build({'opening': 'x' * 50}, 'json')
    chk(r['opening_len'] == 50, '\u65e0\u6807\u70b9\u957f\u53e5\u5b57\u6570\u5e94\u6b63\u786e')

    three = {'core_promise': False, 'relevance': False, 'roadmap': False}
    r = build(three, 'json')
    chk(r['core_promise'] is False and r['relevance'] is False
        and r['roadmap'] is False, '\u4e09\u8981\u7d20\u672a\u63d0\u4f9b\u65f6\u5e94\u5168\u4e3a False')

    empty = {}
    r = build(empty, 'json')
    chk(r['dup_rate'] == 0.0, '\u7a7a\u8f93\u5165\u91cd\u590d\u5ea6\u8bb0 0 \u800c\u975e\u62a5\u9519')

    txt = build(good, 'md')
    chk('\u5e94\u907f\u5f00\u7684\u5199\u6cd5' in txt, 'md \u5e94\u542b\u907f\u6cd5\u6bb5')
    chk('\u6574\u6539\u5efa\u8bae' in txt, 'md \u5e94\u542b\u6574\u6539\u5efa\u8bae')

    if fails:
        lines = ['SELFTEST FAIL: %d/%d passed' % (ok, ok + len(fails))]
        for f in fails:
            lines.append('  - %s' % f)
        text = '\n'.join(lines)
    else:
        text = 'SELFTEST OK: %d assertions passed' % ok
    return text


def write_out(text, out):
    if not out:
        base = os.path.dirname(os.path.abspath(__file__))
        out = os.path.join(base, '_last_result.txt')
    d = os.path.dirname(os.path.abspath(out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    return out


def main():
    ap = argparse.ArgumentParser(description='\u516c\u4f17\u53f7\u6587\u7ae0\u5f00\u5934\u5199\u6cd5\u6838\u67e5')
    ap.add_argument('--file', help='\u8f93\u5165 JSON \u8def\u5f84')
    ap.add_argument('--text', help='\u76f4\u63a5\u7ed9 JSON \u5b57\u7b26\u4e32')
    ap.add_argument('--out', help='\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', choices=['md', 'json'], default='md')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    if a.selftest:
        res = selftest()
        write_out(res, os.path.join(here, '_selftest_result.txt'))
        print(res)
        return 0 if res.startswith('SELFTEST OK') else 1
    if not a.file and not a.text:
        ap.print_help()
        return 2
    data = load(a.text, a.file)
    if a.format == 'json':
        out = json.dumps(build(data, 'json'), ensure_ascii=False, indent=2)
    else:
        out = build(data, 'md')
    p = write_out(out, a.out)
    print('written: %s' % p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
