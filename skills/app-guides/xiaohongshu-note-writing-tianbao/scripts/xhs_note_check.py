# -*- coding: utf-8 -*-
"""\u5c0f\u7ea2\u4e66\u7b14\u8bb0\u6838\u67e5\uff1a\u6807\u9898\u957f\u5ea6\u3001\u7ed3\u6784\u5b8c\u6574\u5ea6\u3001\u5173\u952e\u8bcd\u8986\u76d6\u3001\u98ce\u9669\u8bcd\u626b\u63cf\u3002

\u7528\u6cd5:
  python xhs_note_check.py --file note.json [--out result.md] [--format json]
  python xhs_note_check.py --selftest
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

# \u6807\u9898\u957f\u5ea6\u9608\u503c
TITLE_MIN = 12
TITLE_BEST_LO = 16
TITLE_BEST_HI = 20
TITLE_MAX = 24
# \u5c01\u9762\u5b57\u6570\u9608\u503c
COVER_MIN = 4
COVER_MAX = 14
# \u5e72\u8d27\u6761\u6570
DRY_MIN = 3
DRY_MAX = 7
# \u6807\u7b7e\u6570\u91cf
TAG_MIN = 3
TAG_MAX = 5

# \u98ce\u9669\u8bcd\uff1a\u5206\u7c7b -> (\u8bcd\u8868, \u66ff\u4ee3\u8868\u8fbe)
RISK = {
    '\u6700\u9ad8\u7ea7': (['\u6700\u597d', '\u6700\u4f73', '\u6700\u5f3a', '\u6700\u6709\u6548', '\u9876\u7ea7', '\u6781\u81f4',
                '\u7b2c\u4e00\u540d', '\u5168\u7f51\u7b2c\u4e00'], '\u6539\u4e3a\u5177\u4f53\u63cf\u8ff0\uff0c\u5982\u300c\u6211\u7528\u8fc7\u91cc\u9762\u6700\u987a\u624b\u7684\u300d'),
    '\u7edd\u5bf9\u5316': (['\u7edd\u5bf9', '\u5f7b\u5e95', '\u6839\u6cbb', '\u6c38\u4e45', '\u767e\u5206\u4e4b\u767e', '100%',
                '\u5fc5\u7136', '\u4e00\u5b9a\u80fd'], '\u6539\u4e3a\u300c\u57fa\u672c\u300d\u300c\u901a\u5e38\u300d\u300c\u5728 XX \u6761\u4ef6\u4e0b\u300d'),
    '\u865a\u5047\u627f\u8bfa': (['\u5305\u8fc7', '\u5305\u7626', '\u5305\u597d', '\u7a33\u8d5a', '\u4fdd\u8bc1\u6709\u6548', '\u65e0\u6548\u9000\u6b3e',
                  '\u4e00\u5b9a\u80fd\u5b66\u4f1a', '\u96f6\u98ce\u9669'], '\u5220\u9664\uff0c\u6216\u6539\u6210\u6709\u6761\u4ef6\u7684\u8868\u8ff0'),
    '\u6743\u5a01\u6697\u793a': (['\u4e13\u5bb6\u63a8\u8350', '\u592e\u89c6\u63a8\u8350', '\u6743\u5a01\u8ba4\u8bc1', '\u5b98\u65b9\u63a8\u8350',
                  '\u56fd\u5bb6\u8ba4\u8bc1'], '\u6709\u8bc1\u660e\u5219\u5199\u660e\u5177\u4f53\u51fa\u5904\uff0c\u65e0\u5219\u5220\u9664'),
    '\u533b\u7597\u7528\u8bed': (['\u6cbb\u7597', '\u6839\u6cbb', '\u6297\u708e', '\u6d88\u708e', '\u795b\u75d8', '\u6740\u83cc',
                  '\u4fee\u590d\u53d7\u635f\u7ec6\u80de'], '\u6539\u7528\u300c\u62a4\u80a4\u300d\u300c\u6539\u5584\u300d\uff1b\u533b\u7597\u7c7b\u6539\u5408\u89c4\u8868\u8ff0'),
    '\u91d1\u878d\u7528\u8bed': (['\u4fdd\u672c', '\u7a33\u8d5a\u4e0d\u8d54', '\u9ad8\u6536\u76ca', '\u65e0\u98ce\u9669', '\u8eba\u8d5a'],
                 '\u6539\u4e3a\u300c\u53ef\u80fd\u5b58\u5728\u98ce\u9669\u300d\u300c\u6536\u76ca\u4e0d\u4fdd\u8bc1\u300d'),
    '\u865a\u5047\u4fc3\u9500': (['\u6700\u540e\u4e00\u5929', '\u4ec5\u6b64\u4e00\u6b21', '\u9a6c\u4e0a\u6da8\u4ef7', '\u6700\u540e\u673a\u4f1a'],
                 '\u5199\u660e\u5177\u4f53\u65f6\u95f4\u4e0e\u4f9d\u636e'),
    '\u5f15\u4eba\u4e0d\u9002': (['\u6b7b\u80a5\u5b85', '\u4e11\u516b\u602a', '\u80d6\u5b50', '\u77ee\u77ec\u77ec'],
                 '\u6539\u7528\u4e2d\u6027\u63cf\u8ff0'),
    '\u8fc7\u5ea6\u627f\u8bfa\u6548\u679c': (['\u4e00\u5468\u7626', '\u6708\u7626', '\u5f7b\u5e95\u544a\u522b', '\u6c38\u4e45\u544a\u522b',
                      '\u4e09\u5929\u89c1\u6548'], '\u6539\u4e3a\u300c\u6211\u4e2a\u4eba\u7684\u53d8\u5316\u662f\u2026\u2026\u300d'),
}

HIGH_RISK_CATS = ('\u6700\u9ad8\u7ea7', '\u7edd\u5bf9\u5316', '\u865a\u5047\u627f\u8bfa', '\u533b\u7597\u7528\u8bed', '\u91d1\u878d\u7528\u8bed')

# \u94a9\u5b50\u4f4e\u6548\u4fe1\u53f7\uff1a\u81ea\u6211\u4ecb\u7ecd\u5f00\u573a
SELF_INTRO = ('\u5927\u5bb6\u597d', '\u6211\u662f', '\u5f88\u9ad8\u5174\u8ba4\u8bc6', '\u4eca\u5929\u7ed9\u5927\u5bb6\u4ecb\u7ecd\u4e00\u4e0b\u6211',
              '\u672c\u4eba\u53eb')

# \u5e72\u8d27\u5206\u70b9\u7b26\u53f7
BULLET_RE = re.compile(r'(?:\u2460|\u2461|\u2462|\u2463|\u2464|\u2465|\u2466|'
                       r'\u2467|\u2468|\u2469|\d+[.\uff0e\u3001])')
ACTION_HINTS = ('\u8bc4\u8bba\u533a', '\u6536\u85cf', '\u7f6e\u9876', '\u4e0b\u671f', '\u4e0b\u4e00\u671f', '\u5173\u6ce8',
                '\u7559\u8a00', '\u544a\u8bc9\u6211', '\u60f3\u770b')


def load(text=None, path=None):
    if text:
        return json.loads(text)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def title_check(title):
    t = title or ''
    n = len(t)
    if n == 0:
        return {'n': 0, 'verdict': '\u7a7a\u6807\u9898', 'truncated': True}
    truncated = n > TITLE_MAX
    if TITLE_BEST_LO <= n <= TITLE_BEST_HI:
        grade = '\u6700\u4f73\u533a\u95f4'
    elif n < TITLE_MIN:
        grade = '\u504f\u77ed\uff0c\u4fe1\u606f\u91cf\u53ef\u80fd\u4e0d\u8db3'
    elif n <= TITLE_MAX:
        grade = '\u53ef\u7528'
    else:
        grade = '\u504f\u957f'
    return {'n': n, 'verdict': grade, 'truncated': truncated}


def cover_check(cover):
    c = cover or ''
    n = len(c)
    if n == 0:
        return {'n': 0, 'state': '\u672a\u586b', 'fix': '\u5c01\u9762\u5e94\u6709 8-14 \u5b57\u6587\u6848\u6216 3-5 \u5b57\u77ed\u8bed'}
    if n < COVER_MIN:
        return {'n': n, 'state': '\u8fc7\u77ed', 'fix': '\u8865\u5230 4 \u5b57\u4ee5\u4e0a'}
    if n > COVER_MAX:
        return {'n': n, 'state': '\u504f\u957f',
                'fix': '\u538b\u5230 14 \u5b57\u4ee5\u5185\uff0c\u7f29\u7565\u56fe\u4e0a\u5b57\u592a\u591a\u7b49\u4e8e\u6ca1\u5199'}
    return {'n': n, 'state': '\u5408\u89c4', 'fix': ''}


def structure_check(body):
    b = body or ''
    paras = [p for p in b.split('\n') if p.strip()]
    first = paras[0] if paras else ''
    head_lines = b.split('\n')[:2]
    head_text = '\n'.join(head_lines)

    bullets = BULLET_RE.findall(b)
    dry = len(bullets)
    intro_bad = any(w in head_text for w in SELF_INTRO)
    action_ok = any(w in b for w in ACTION_HINTS)

    parts = {
        'hook': bool(first.strip()) and not intro_bad,
        'dry': DRY_MIN <= dry <= DRY_MAX,
        'action': action_ok,
    }
    rate = round(sum(1 for v in parts.values() if v) * 100.0 / 3, 1)
    return {'paragraphs': len(paras), 'dry_items': dry,
            'intro_opening': intro_bad, 'parts': parts,
            'structure_rate': rate}


def keyword_check(data):
    body = data.get('body') or ''
    kws = [k for k in (data.get('keywords') or []) if (k or '').strip()]
    tags = [t for t in (data.get('hashtags') or []) if (t or '').strip()]
    title = data.get('title') or ''
    head = '\n'.join(body.split('\n')[:2])

    covered = []
    uncovered = []
    for k in kws:
        in_title = k.lower() in title.lower()
        in_head = k.lower() in head.lower()
        in_body = k.lower() in body.lower()
        if in_title and in_body:
            covered.append(k)
        else:
            uncovered.append({'keyword': k, 'in_title': in_title,
                              'in_head': in_head, 'in_body': in_body})
    rate = 0.0
    if kws:
        rate = round(len(covered) * 100.0 / len(kws), 1)
    tag_state = '\u5408\u89c4'
    if len(tags) < TAG_MIN:
        tag_state = '\u6807\u7b7e\u5c11\u4e8e %d \u4e2a\uff0c\u8986\u76d6\u4e0d\u8db3' % TAG_MIN
    elif len(tags) > TAG_MAX:
        tag_state = '\u6807\u7b7e\u591a\u4e8e %d \u4e2a\uff0c\u6807\u7b7e\u5931\u7126' % TAG_MAX
    return {'keywords': kws, 'covered': covered, 'uncovered': uncovered,
            'coverage': rate, 'tag_count': len(tags), 'tag_state': tag_state,
            'title_cover': bool([k for k in kws if k.lower() in title.lower()]),
            'head_cover': bool([k for k in kws if k.lower() in head.lower()])}


def risk_scan(text):
    t = text or ''
    rows = []
    high = 0
    for cat in sorted(RISK.keys()):
        words, fix = RISK[cat]
        hits = [w for w in words if w in t]
        if hits:
            if cat in HIGH_RISK_CATS:
                high += 1
            rows.append({'category': cat, 'hits': hits, 'fix': fix,
                         'level': '\u9ad8' if cat in HIGH_RISK_CATS else '\u4e2d'})
    return rows, high


def build(data, fmt='md'):
    title = data.get('title') or ''
    body = data.get('body') or ''
    cover = data.get('cover_text') or ''
    t = title_check(title)
    c = cover_check(cover)
    s = structure_check(body)
    k = keyword_check(data)
    rows, high = risk_scan((title + '\n' + cover + '\n' + body))

    if fmt == 'json':
        return {'title': title, 'title_len': t['n'], 'title_verdict': t['verdict'],
                'truncated': t['truncated'],
                'cover_len': c['n'], 'cover_state': c['state'],
                'dry_items': s['dry_items'], 'intro_opening': s['intro_opening'],
                'structure_rate': s['structure_rate'], 'parts': s['parts'],
                'keyword_coverage': k['coverage'],
                'uncovered_keywords': [u['keyword'] for u in k['uncovered']],
                'tag_count': k['tag_count'], 'tag_state': k['tag_state'],
                'title_cover': k['title_cover'], 'head_cover': k['head_cover'],
                'risk_rows': rows, 'high_risk_count': high}

    out = []
    out.append('# \u5c0f\u7ea2\u4e66\u7b14\u8bb0\u4f53\u68c0')
    out.append('')
    out.append('- \u6807\u9898\uff1a%s' % (title or '\uff08\u672a\u586b\uff09'))
    out.append('- \u6807\u9898\u5b57\u6570\uff1a%d\uff08\u6700\u4f73 %d-%d\uff0c\u8d85\u8fc7 %d \u6613\u88ab\u622a\u65ad\uff09'
               % (t['n'], TITLE_BEST_LO, TITLE_BEST_HI, TITLE_MAX))
    out.append('- \u6807\u9898\u5224\u5b9a\uff1a%s' % t['verdict'])
    out.append('- \u5c01\u9762\u5b57\u6570\uff1a%d\uff08%s\uff09' % (c['n'], c['state']))
    out.append('- \u5e72\u8d27\u6761\u6570\uff1a%d\uff08\u5efa\u8bae %d-%d \u6761\uff09' % (s['dry_items'], DRY_MIN, DRY_MAX))
    out.append('- \u5f00\u5934\u4e3a\u81ea\u6211\u4ecb\u7ecd\uff1a%s' % ('\u662f' if s['intro_opening'] else '\u5426'))
    out.append('- \u7ed3\u6784\u5b8c\u6574\u5ea6\uff1a%.1f%%' % s['structure_rate'])
    out.append('- \u5173\u952e\u8bcd\u8986\u76d6\u7387\uff1a%.1f%%\uff08\u6807\u9898\u547d\u4e2d %s\uff09'
               % (k['coverage'], '\u662f' if k['title_cover'] else '\u5426'))
    out.append('- \u8bdd\u9898\u6807\u7b7e\uff1a%d \u4e2a\uff08%s\uff09' % (k['tag_count'], k['tag_state']))
    out.append('- \u98ce\u9669\u8bcd\u547d\u4e2d\uff1a%d \u7c7b\uff0c\u5176\u4e2d\u9ad8\u98ce\u9669 %d \u7c7b' % (len(rows), high))
    out.append('')
    out.append('## \u4e00\u3001\u6807\u9898')
    out.append('')
    if t['truncated']:
        out.append('\u6807\u9898\u8d85\u8fc7 %d \u5b57\uff0c\u5728\u4fe1\u606f\u6d41\u4e2d\u53ef\u80fd\u88ab\u622a\u65ad\u3002\u628a\u5173\u952e\u4fe1\u606f\u538b\u5230\u524d %d \u5b57\u3002'
                   % (TITLE_MAX, TITLE_BEST_HI))
    else:
        out.append('\u6807\u9898\u957f\u5ea6%s\u3002' % t['verdict'])
    out.append('')
    out.append('## \u4e8c\u3001\u5c01\u9762')
    out.append('')
    out.append('- \u5b57\u6570\uff1a%d\uff08\u5efa\u8bae %d-%d \u5b57\uff09' % (c['n'], COVER_MIN, COVER_MAX))
    if c['fix']:
        out.append('- \u5efa\u8bae\uff1a%s' % c['fix'])
    else:
        out.append('- \u5c01\u9762\u6587\u6848\u957f\u5ea6\u5408\u89c4\u3002\u4f4d\u7f6e\u907f\u5f00\u5e95\u90e8\u906e\u6321\u533a\uff0c\u5b57\u53f7\u5728\u7f29\u7565\u56fe\u4e0b\u80fd\u770b\u6e05\u3002')
    out.append('')
    out.append('## \u4e09\u3001\u6b63\u6587\u7ed3\u6784')
    out.append('')
    p = s['parts']
    out.append('- \u94a9\u5b50\uff1a%s%s' % ('\u5177\u5907' if p['hook'] else '\u7f3a\u5931',
                                '\uff08\u5f00\u5934\u662f\u81ea\u6211\u4ecb\u7ecd\uff0c\u5e94\u6539\u4e3a\u7ed3\u8bba\u6216\u5151\u73b0\u6807\u9898\uff09'
                                if s['intro_opening'] else ''))
    out.append('- \u5e72\u8d27\uff1a%s\uff08%d \u6761\uff0c\u5efa\u8bae %d-%d \u6761\uff09'
               % ('\u8fbe\u6807' if p['dry'] else '\u4e0d\u8fbe\u6807', s['dry_items'], DRY_MIN, DRY_MAX))
    out.append('- \u884c\u52a8\uff1a%s\uff08\u9700\u7ed9\u4e00\u4e2a\u660e\u786e\u7684\u4e0b\u4e00\u6b65\uff09' % ('\u5177\u5907' if p['action'] else '\u7f3a\u5931'))
    out.append('- \u6bb5\u843d\u6570\uff1a%d' % s['paragraphs'])
    out.append('')
    out.append('## \u56db\u3001\u5173\u952e\u8bcd\u4e0e\u6807\u7b7e')
    out.append('')
    if not k['keywords']:
        out.append('\u672a\u586b\u6838\u5fc3\u5173\u952e\u8bcd\u3002\u81f3\u5c11\u5b9a 1-3 \u4e2a\uff0c\u5199\u8fdb\u6807\u9898\u3001\u5f00\u5934\u524d 2 \u884c\u4e0e\u5206\u6bb5\u5c0f\u6807\u9898\u3002')
    else:
        out.append('| \u5173\u952e\u8bcd | \u6807\u9898 | \u5f00\u5934 | \u6b63\u6587 |')
        out.append('|---|---|---|---|')
        for u in k['uncovered']:
            out.append('| %s | %s | %s | %s |' % (
                u['keyword'], 'Y' if u['in_title'] else '-',
                'Y' if u['in_head'] else '-', 'Y' if u['in_body'] else '-'))
        out.append('')
        out.append('\u8986\u76d6\u7387 %.1f%%\u3002\u6838\u5fc3\u8bcd\u5e94\u5728\u6807\u9898\u3001\u5f00\u5934\u3001\u5206\u6bb5\u5c0f\u6807\u9898\u5404\u51fa\u73b0\u4e00\u6b21\uff0c\u81ea\u7136\u5206\u5e03\u4e0d\u5806\u780c\u3002'
                   % k['coverage'])
    out.append('')
    out.append('\u8bdd\u9898\u6807\u7b7e %d \u4e2a\uff1a%s' % (k['tag_count'], k['tag_state']))
    out.append('')
    out.append('## \u4e94\u3001\u98ce\u9669\u8bcd')
    out.append('')
    if not rows:
        out.append('\u672a\u547d\u4e2d\u8bcd\u8868\u4e2d\u7684\u98ce\u9669\u8868\u8ff0\u3002\u4ecd\u9700\u4eba\u5de5\u786e\u8ba4\u65e0\u7edd\u5bf9\u5316\u8868\u8fbe\u4e0e\u865a\u5047\u5ba3\u4f20\u3002')
    else:
        out.append('| \u7b49\u7ea7 | \u7c7b\u522b | \u547d\u4e2d | \u6539\u6cd5 |')
        out.append('|---|---|---|---|')
        for r in rows:
            out.append('| %s | %s | %s | %s |' % (
                r['level'], r['category'], '\u3001'.join(r['hits']), r['fix']))
    out.append('')
    out.append('## \u516d\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if t['n'] == 0:
        idx += 1
        out.append('%d. \u672a\u586b\u6807\u9898\uff1a\u5148\u6309\u4e94\u7c7b\u516c\u5f0f\uff08\u6570\u5b57/\u75db\u70b9/\u5bf9\u6bd4/\u60ac\u5ff5/\u8eab\u4efd\u6807\u7b7e\uff09\u62df 3 \u4e2a\u5907\u9009\u3002' % idx)
    elif t['truncated']:
        idx += 1
        out.append('%d. \u6807\u9898 %d \u5b57\u8d85\u8fc7 %d \u5b57\uff0c\u538b\u5230 %d \u5b57\u4ee5\u5185\u5e76\u628a\u5173\u952e\u4fe1\u606f\u524d\u7f6e\u3002'
                   % (idx, t['n'], TITLE_MAX, TITLE_BEST_HI))
    elif t['n'] < TITLE_MIN:
        idx += 1
        out.append('%d. \u6807\u9898\u4ec5 %d \u5b57\uff0c\u4fe1\u606f\u91cf\u53ef\u80fd\u4e0d\u8db3\uff0c\u8865\u4e00\u4e2a\u4eba\u7fa4\u3001\u573a\u666f\u6216\u6570\u5b57\u3002' % (idx, t['n']))
    if s['intro_opening']:
        idx += 1
        out.append('%d. \u6b63\u6587\u5f00\u5934\u662f\u81ea\u6211\u4ecb\u7ecd\uff1a\u524d 2 \u884c\u5e94\u7ed9\u7ed3\u8bba\u6216\u76f4\u63a5\u5151\u73b0\u6807\u9898\u627f\u8bfa\u3002' % idx)
    if s['dry_items'] < DRY_MIN:
        idx += 1
        out.append('%d. \u5e72\u8d27\u53ea\u6709 %d \u6761\uff1a\u8865\u5230 %d- %d \u6761\uff0c\u6bcf\u6761\u7ed9\u6570\u636e\u6216\u6b65\u9aa4\u3002'
                   % (idx, s['dry_items'], DRY_MIN, DRY_MAX))
    elif s['dry_items'] > DRY_MAX:
        idx += 1
        out.append('%d. \u5e72\u8d27 %d \u6761\u504f\u591a\uff1a\u5408\u5e76\u5230 %d \u6761\u4ee5\u5185\uff0c\u8bfb\u8005\u8bb0\u4e0d\u4f4f\u3002'
                   % (idx, s['dry_items'], DRY_MAX))
    if not p['action']:
        idx += 1
        out.append('%d. \u884c\u52a8\u6bb5\u7f3a\u5931\uff1a\u7ed3\u5c3e\u7ed9\u4e00\u4e2a\u660e\u786e\u52a8\u4f5c\uff08\u5f15\u5bfc\u6536\u85cf\u6216\u4e0b\u671f\u9884\u544a\uff09\u3002' % idx)
    if c['n'] == 0:
        idx += 1
        out.append('%d. \u672a\u5199\u5c01\u9762\u6587\u6848\uff1a\u8865 8-14 \u5b57\uff0c\u7f29\u7565\u56fe\u4e0a\u8981\u80fd\u770b\u6e05\u3002' % idx)
    elif c['fix']:
        idx += 1
        out.append('%d. \u5c01\u9762\u6587\u6848 %s' % (idx, c['fix']))
    if k['keywords'] and k['coverage'] < 100.0:
        idx += 1
        miss = '\u3001'.join(u['keyword'] for u in k['uncovered'])
        out.append('%d. \u5173\u952e\u8bcd\u672a\u5168\u8986\u76d6\uff1a%s\u3002\u6838\u5fc3\u8bcd\u9700\u5728\u6807\u9898\u4e0e\u6b63\u6587\u90fd\u51fa\u73b0\u3002' % (idx, miss))
    if k['tag_count'] and k['tag_state'] != '\u5408\u89c4':
        idx += 1
        out.append('%d. \u8bdd\u9898\u6807\u7b7e%s\uff1a\u5efa\u8bae 3-5 \u4e2a\uff0c1 \u4e2a\u5927\u8bcd\u52a0 2-4 \u4e2a\u7cbe\u51c6\u8bcd\u3002'
                   % (idx, k['tag_state']))
    if high:
        idx += 1
        out.append('%d. \u9ad8\u98ce\u9669\u8bcd\u547d\u4e2d %d \u7c7b\uff0c\u5fc5\u987b\u6539\uff0c\u4e0d\u505a\u300c\u53ef\u80fd\u6ca1\u4e8b\u300d\u7684\u5224\u65ad\u3002' % (idx, high))
    if len(rows) > high:
        idx += 1
        out.append('%d. \u4e2d\u98ce\u9669\u8bcd\u547d\u4e2d %d \u7c7b\uff0c\u6539\u4e3a\u5177\u4f53\u6761\u4ef6\u8868\u8ff0\u3002' % (idx, len(rows) - high))
    if not idx:
        out.append('\u6807\u9898\u3001\u5c01\u9762\u3001\u7ed3\u6784\u3001\u5173\u952e\u8bcd\u4e0e\u98ce\u9669\u8bcd\u5747\u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\u3002'
                   '\u53d1\u5e03\u524d\u4ecd\u9700\u4eba\u5de5\u786e\u8ba4\u5185\u5bb9\u4e3a\u771f\u5b9e\u4f53\u9a8c\uff0c\u5546\u4e1a\u63a8\u5e7f\u5185\u5bb9\u5df2\u6309\u5e73\u53f0\u89c4\u5219\u6807\u6ce8\u3002')
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
        'title': '5 \u4e2a Excel \u516c\u5f0f\uff0c\u8d22\u52a1\u4eba\u6bcf\u5929\u7701 1 \u5c0f\u65f6',
        'cover_text': '6 \u4e2a\u65b9\u6848',
        'body': '\u8fd9 5 \u4e2a\u516c\u5f0f\u6211\u7528\u4e86\u534a\u5e74\uff0c\u6700\u5e38\u7528\u7684\u662f\u7b2c\u4e09\u4e2a\u3002\n\n'
                '\u6bcf\u5929\u505a\u8868\u7684\u91cd\u590d\u52b3\u52a8\u592a\u591a\u4e86\u3002\n\n'
                '\u2460 \u5feb\u901f\u67e5\u627e \u2461 \u65e5\u671f\u6362\u7b97 \u2462 \u5206\u7c7b\u6c47\u603b\n\n'
                '\u9700\u8981\u7684\u8bdd\u6211\u628a\u6a21\u677f\u653e\u5728\u8bc4\u8bba\u533a\u4e86\u3002',
        'keywords': ['Excel', '\u8d22\u52a1'],
        'hashtags': ['excel\u6280\u5de7', '\u804c\u573a\u6548\u7387', '\u8d22\u52a1'],
    }
    r = build(good, 'json')
    chk(r['title_len'] > 12, '\u6b63\u5e38\u6807\u9898\u5e94\u8d85\u8fc7 12 \u5b57')
    chk(r['truncated'] is False, '20 \u5b57\u6807\u9898\u4e0d\u5e94\u5224\u622a\u65ad')
    chk(r['cover_state'] == '\u5408\u89c4', '6 \u5b57\u5c01\u9762\u5e94\u5408\u89c4')
    chk(r['dry_items'] == 3, '3 \u4e2a\u5206\u70b9\u7b26\u53f7\u5e94\u8ba1\u4e3a 3 \u6761')
    chk(r['intro_opening'] is False, '\u6b63\u5e38\u5f00\u5934\u4e0d\u5e94\u5224\u81ea\u6211\u4ecb\u7ecd')
    chk(r['tag_state'] == '\u5408\u89c4', '3 \u4e2a\u6807\u7b7e\u5e94\u5408\u89c4')
    chk(r['structure_rate'] > 60.0, '\u7ed3\u6784\u5b8c\u6574\u5ea6\u5e94\u5927\u4e8e 60')

    long_t = {'title': '\u4e00\u4e2a\u666e\u901a\u4e0a\u73ed\u65cf\u7684\u5468\u672b\u4e24\u5929\u65f6\u95f4\u5b89\u6392\u7684\u5b8c\u6574\u8bb0\u5f55\u548c\u5fc3\u5f97\u5206\u4eab\u9644\u6e05\u5355'}
    r = build(long_t, 'json')
    chk(r['truncated'] is True, '\u8d85\u957f\u6807\u9898\u5e94\u5224\u622a\u65ad')
    chk(r['title_verdict'] == '\u504f\u957f', '\u8d85\u957f\u6807\u9898\u5224\u5b9a\u5e94\u4e3a\u504f\u957f')

    short_t = {'title': '\u597d\u7528\u7684\u8f6f\u4ef6'}
    r = build(short_t, 'json')
    chk(r['title_len'] == 5, '\u77ed\u6807\u9898\u5b57\u6570\u5e94\u6b63\u786e')
    chk(r['title_verdict'] == '\u504f\u77ed\uff0c\u4fe1\u606f\u91cf\u53ef\u80fd\u4e0d\u8db3', '5 \u5b57\u6807\u9898\u5e94\u5224\u504f\u77ed')

    best_t = {'title': '\u901a\u52e4\u515a\u65e9\u9910\u5403\u4ec0\u4e48\uff1f6 \u4e2a 5 \u5206\u949f\u65b9\u6848'}
    r = build(best_t, 'json')
    chk(r['title_verdict'] == '\u6700\u4f73\u533a\u95f4', '18 \u5b57\u6807\u9898\u5e94\u5c5e\u6700\u4f73\u533a\u95f4')

    r = build({'title': ''}, 'json')
    chk(r['title_len'] == 0, '\u7a7a\u6807\u9898\u957f\u5ea6\u4e3a 0')
    chk(r['title_verdict'] == '\u7a7a\u6807\u9898', '\u7a7a\u6807\u9898\u5e94\u5224\u5b9a\u4e3a\u7a7a\u6807\u9898')

    r = build({'cover_text': ''}, 'json')
    chk(r['cover_state'] == '\u672a\u586b', '\u672a\u586b\u5c01\u9762\u5e94\u5224\u672a\u586b')

    r = build({'cover_text': '\u8fd9\u662f\u4e00\u4e2a\u975e\u5e38\u975e\u5e38\u957f\u7684\u5c01\u9762\u6587\u6848\u5199\u5f97\u5bc6\u5bc6\u9ebb\u9ebb\u4e00\u5806\u5b57'}, 'json')
    chk(r['cover_state'] == '\u504f\u957f', '\u8d85\u957f\u5c01\u9762\u5e94\u5224\u504f\u957f')

    r = build({'cover_text': '\u597d'}, 'json')
    chk(r['cover_state'] == '\u8fc7\u77ed', '2 \u5b57\u5c01\u9762\u5e94\u5224\u8fc7\u77ed')

    intro = {'body': '\u5927\u5bb6\u597d\uff0c\u6211\u662f XX\uff0c\u4eca\u5e74 28 \u5c81\uff0c\u4eca\u5929\u7ed9\u5927\u5bb6\u4ecb\u7ecd\u4e00\u4e0b\u6211\u7684\u65b9\u6cd5\u3002'}
    r = build(intro, 'json')
    chk(r['intro_opening'] is True, '\u81ea\u6211\u4ecb\u7ecd\u5f00\u573a\u5e94\u547d\u4e2d')
    chk(r['parts']['hook'] is False, '\u81ea\u6211\u4ecb\u7ecd\u5f00\u573a\u94a9\u5b50\u5e94\u5224\u7f3a\u5931')

    few = {'body': '\u8fd9\u662f\u4e00\u6bb5\u53ea\u6709\u5e72\u8d27\u6ca1\u6709\u5206\u70b9\u7684\u6587\u5b57\u3002\n\u8bc4\u8bba\u533a\u89c1\u3002'}
    r = build(few, 'json')
    chk(r['dry_items'] == 0, '\u65e0\u5206\u70b9\u7b26\u53f7\u5e72\u8d27\u5e94\u4e3a 0 \u6761')
    chk(r['parts']['dry'] is False, '\u5e72\u8d27 0 \u6761\u5e94\u4e0d\u8fbe\u6807')

    many = {'body': '1. a 2. b 3. c 4. d 5. e 6. f 7. g 8. h 9. i \u8bc4\u8bba\u533a'}
    r = build(many, 'json')
    chk(r['dry_items'] >= 9, '\u591a\u5206\u70b9\u5e94\u8ba1\u6570 9 \u6761\u4ee5\u4e0a')
    chk(r['parts']['dry'] is False, '\u5e72\u8d27\u8fc7\u591a\u5e94\u4e0d\u8fbe\u6807')

    no_action = {'body': '1. a 2. b 3. c \u8fd9\u662f\u5168\u90e8\u5185\u5bb9\u3002'}
    r = build(no_action, 'json')
    chk(r['parts']['action'] is False, '\u65e0\u884c\u52a8\u5f15\u5bfc\u5e94\u5224\u7f3a\u5931')

    risk = {'title': '\u6700\u597d\u7528\u7684 Excel \u516c\u5f0f\uff0c\u5f7b\u5e95\u89e3\u51b3\u4f60\u7684\u95ee\u9898'}
    r = build(risk, 'json')
    cats = [x['category'] for x in r['risk_rows']]
    chk('\u6700\u9ad8\u7ea7' in cats, '\u6700\u597d\u7528\u5e94\u547d\u4e2d\u6700\u9ad8\u7ea7')
    chk('\u7edd\u5bf9\u5316' in cats, '\u5f7b\u5e95\u5e94\u547d\u4e2d\u7edd\u5bf9\u5316')
    chk(r['high_risk_count'] == 2, '\u4e24\u7c7b\u5747\u4e3a\u9ad8\u98ce\u9669')

    med = {'body': '\u8fd9\u4e2a\u65b9\u6cd5\u5f88\u6709\u6548\u7387\uff0c\u6bd4\u522b\u7684\u65b9\u6cd5\u66f4\u7701\u65f6\u95f4\u3002'}
    r = build(med, 'json')
    chk(r['high_risk_count'] == 0, '\u4e00\u822c\u8868\u8ff0\u4e0d\u5e94\u547d\u4e2d\u9ad8\u98ce\u9669')

    clean = {'title': '5 \u4e2a\u65b9\u6848\u5206\u4eab', 'body': '1. a 2. b 3. c \u8bc4\u8bba\u533a\u89c1',
             'cover_text': '\u65b9\u6848', 'keywords': [], 'hashtags': []}
    r = build(clean, 'json')
    chk(r['risk_rows'] == [], '\u5e72\u51c0\u6587\u672c\u4e0d\u5e94\u547d\u4e2d\u98ce\u9669\u8bcd')
    chk(r['keyword_coverage'] == 0.0, '\u672a\u586b\u5173\u952e\u8bcd\u8986\u76d6\u7387\u8bb0 0')

    kw = {'keywords': ['Excel', '\u8d22\u52a1'],
          'title': 'Excel \u516c\u5f0f\u5206\u4eab',
          'body': '1. a 2. b 3. c Excel \u7528\u5f97\u597d\u5f88\u7701\u65f6\uff0c\u8bc4\u8bba\u533a'}
    r = build(kw, 'json')
    chk(r['keyword_coverage'] == 50.0, '\u4e00\u534a\u5173\u952e\u8bcd\u672a\u8986\u76d6\u5e94\u4e3a 50')
    chk(r['title_cover'] is True, 'Excel \u5728\u6807\u9898\u5e94\u5224\u547d\u4e2d')

    few_tags = {'hashtags': ['a', 'b']}
    r = build(few_tags, 'json')
    chk('\u5c11\u4e8e' in r['tag_state'], '2 \u4e2a\u6807\u7b7e\u5e94\u63d0\u793a\u504f\u5c11')

    many_tags = {'hashtags': ['a', 'b', 'c', 'd', 'e', 'f']}
    r = build(many_tags, 'json')
    chk('\u591a\u4e8e' in r['tag_state'], '6 \u4e2a\u6807\u7b7e\u5e94\u63d0\u793a\u504f\u591a')

    empty = {}
    r = build(empty, 'json')
    chk(r['title_len'] == 0, '\u7a7a\u8f93\u5165\u4e0d\u62a5\u9519')

    txt = build(good, 'md')
    chk('\u98ce\u9669\u8bcd' in txt, 'md \u5e94\u542b\u98ce\u9669\u8bcd\u6bb5')
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
    ap = argparse.ArgumentParser(description='\u5c0f\u7ea2\u4e66\u7b14\u8bb0\u64b0\u5199\u4e0e\u6807\u9898\u6838\u67e5')
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