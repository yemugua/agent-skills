# -*- coding: utf-8 -*-
"""\u7ade\u8058\u6f14\u8bb2\u7a3f\u6838\u67e5\uff1a\u5206\u6bb5\u65f6\u957f\u63a7\u5236\u3001STAR \u5b8c\u6574\u5ea6\u3001\u6263\u5206\u8868\u8ff0\u626b\u63cf\u3002

\u7528\u6cd5:
  python competition_speech_check.py --file speech.json [--out result.md]
  python competition_speech_check.py --format json --file speech.json
  python competition_speech_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SECTIONS = ('\u81ea\u6211\u4ecb\u7ecd', '\u5c97\u4f4d\u8ba4\u77e5', '\u80dc\u4efb\u8bc1\u636e', '\u4e0a\u4efb\u6253\u7b97')
# \u5404\u6bb5\u76ee\u6807\u5360\u6bd4\uff08\u4ee5 10 \u5206\u949f\u4e3a\u57fa\u51c6\uff0c\u6309\u6bd4\u4f8b\u7f29\u653e\uff09
SHARE = {
    '\u81ea\u6211\u4ecb\u7ecd': 0.10,
    '\u5c97\u4f4d\u8ba4\u77e5': 0.20,
    '\u80dc\u4efb\u8bc1\u636e': 0.45,
    '\u4e0a\u4efb\u6253\u7b97': 0.25,
}

# \u8bed\u901f
RATE_MIN = 200
RATE_MAX = 280
RATE_DEFAULT = 240

# \u5355\u6bb5\u65f6\u957f\u504f\u5dee\u5bb9\u5fcd\uff08\u76f8\u5bf9\u76ee\u6807\u5360\u6bd4\u7684\u7edd\u5bf9\u504f\u5dee\uff09
SHARE_TOL = 0.08
# \u8d85\u65f6\u5bb9\u5fcd\u7cfb\u6570\uff08\u5141\u8bb8\u6bd4\u76ee\u6807\u7565\u957f\uff0c\u4f46\u4e0d\u8d85\u8fc7 1.1\uff09
OVER_TOL = 1.10

# \u6263\u5206\u8868\u8ff0\uff1a\u7c7b\u522b -> \u8bcd\u8868
DEDUCT = {
    '\u8868\u6001\u5f0f\u7a7a\u8bdd': ('\u6211\u5c06\u5c3d\u5168\u529b', '\u4e0d\u8f9c\u8d1f', '\u5168\u529b\u4ee5\u8d74', '\u4e00\u5b9a\u4f1a\u505a\u597d',
                  '\u575a\u51b3\u670d\u4ece', '\u8bf7\u7ec4\u7ec7\u653e\u5fc3', '\u7edd\u4e0d\u8f9c\u8d1f'),
    '\u590d\u8ff0JD': ('\u8981\u6c42\u6709\u8f83\u5f3a\u7684', '\u5c97\u4f4d\u8981\u6c42', '\u4efb\u804c\u8981\u6c42', '\u5177\u5907\u826f\u597d\u7684',
               '\u826f\u597d\u7684\u6c9f\u901a\u80fd\u529b', '\u8f83\u5f3a\u7684\u8d23\u4efb\u5fc3'),
    '\u6ca1\u6709\u6570\u5b57': ('\u63d0\u5347\u4e86\u6548\u7387', '\u83b7\u5f97\u4e86\u597d\u8bc4', '\u53d6\u5f97\u4e86\u6210\u7ee9', '\u6548\u679c\u5f88\u597d',
                 '\u660e\u663e\u6539\u5584', '\u663e\u8457\u63d0\u5347'),
    '\u5168\u5458\u6211\u4eec': ('\u6211\u4eec\u5b8c\u6210\u4e86', '\u6211\u4eec\u83b7\u5f97\u4e86', '\u6211\u4eec\u56e2\u961f', '\u6211\u4eec\u90e8\u95e8',
                 '\u6211\u4eec\u96c6\u4f53'),
    '\u8fc7\u5ea6\u627f\u8bfa': ('\u7ffb\u4e09\u500d', '\u7ffb\u4e00\u756a', '\u4fdd\u8bc1\u5b8c\u6210', '\u4e00\u5b9a\u80fd\u8fbe\u5230', '\u5fc5\u7136\u5b9e\u73b0',
                 '\u4e00\u5b9a\u8d85\u989d'),
    '\u653b\u51fb\u7ade\u8058\u8005': ('\u67d0\u4e9b\u4eba', '\u67d0\u4e9b\u540c\u4e8b', '\u6709\u4eba\u4e0d\u529b', '\u522b\u4eba\u505a\u4e0d\u597d',
                   '\u67d0\u4e9b\u9886\u5bfc'),
    '\u5426\u5b9a\u524d\u4eba': ('\u539f\u6765\u7684\u65b9\u6cd5\u4e0d\u884c', '\u6839\u672c\u4e0d\u884c', '\u5b8c\u5168\u9519\u8bef', '\u8001\u529e\u6cd5',
                 '\u4e4b\u524d\u90a3\u5957\u505a\u6cd5'),
}

STAR_KEYS = ('has_situation', 'has_task', 'has_action', 'has_result')
STAR_CN = {
    'has_situation': '\u60c5\u5883 S',
    'has_task': '\u4efb\u52a1 T',
    'has_action': '\u884c\u52a8 A',
    'has_result': '\u7ed3\u679c R',
}


def load(text=None, path=None):
    if text:
        return json.loads(text)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def rate_of(data):
    r = data.get('speech_rate')
    try:
        r = float(r)
    except (TypeError, ValueError):
        return RATE_DEFAULT, False
    if r < RATE_MIN or r > RATE_MAX:
        return r, True
    return r, False


def duration_check(data):
    rate, rate_bad = rate_of(data)
    try:
        target = float(data.get('target_minutes'))
    except (TypeError, ValueError):
        target = None

    secs = data.get('sections') or []
    rows = []
    total_chars = 0
    for s in secs:
        name = s.get('name') or '\uff08\u672a\u547d\u540d\uff09'
        t = s.get('text') or ''
        n = len(t)
        total_chars += n
        mins = round(n / rate, 2) if rate else None
        rows.append({'name': name, 'chars': n, 'minutes': mins,
                     'known': name in SHARE})

    total_min = round(total_chars / rate, 2) if rate else None
    issues = []
    if total_min is not None and target:
        ratio = total_min / target
        if ratio > 1.05:
            issues.append('\u603b\u65f6\u957f %.1f \u5206\u949f\u8d85\u51fa\u76ee\u6807 %s \u5206\u949f %.0f%%\uff0c'
                          '\u5185\u5bb9\u8fc7\u591a\u6216\u8bed\u901f\u504f\u5feb'
                          % (total_min, target, (ratio - 1) * 100))
        elif ratio < 0.85:
            issues.append('\u603b\u65f6\u957f %.1f \u5206\u949f\u4f4e\u4e8e\u76ee\u6807 %s \u5206\u949f\u7684 85%%\uff0c'
                          '\u53ef\u80fd\u8bb2\u4e0d\u6ee1\u6216\u5185\u5bb9\u5355\u8584' % (total_min, target))

    for r in rows:
        if not r['known'] or total_min in (None, None) or not total_min:
            continue
        actual = r['minutes'] / total_min
        want = SHARE[r['name']]
        diff = actual - want
        state = '\u504f\u79bb'
        if abs(diff) <= SHARE_TOL:
            state = '\u8fbe\u6807'
        elif actual > want * OVER_TOL:
            state = '\u660e\u663e\u8d85\u65f6'
        r['share_actual'] = round(actual * 100, 1)
        r['share_want'] = round(want * 100, 1)
        r['share_diff'] = round(diff * 100, 1)
        r['state'] = state
        if state == '\u660e\u663e\u8d85\u65f6':
            issues.append('\u300c%s\u300d\u5b9e\u9645\u5360 %.0f%%\uff0c\u76ee\u6807 %.0f%%\uff0c\u8be5\u6bb5\u8fc7\u957f'
                          % (r['name'], actual * 100, want * 100))
    for r in rows:
        r.setdefault('share_actual', None)
        r.setdefault('share_want', None)
        r.setdefault('share_diff', None)
        r.setdefault('state', '\u672a\u8bc6\u522b')

    if rate_bad:
        issues.append('\u8bed\u901f %s \u5b57/\u5206\u8d85\u51fa\u5408\u7406\u533a\u95f4 %d-%d\uff0c\u51c6\u5907\u65f6\u6309 %d \u5b57/\u5206\u6298\u7b97'
                      % (rate, RATE_MIN, RATE_MAX, RATE_DEFAULT))
    missing = [s for s in SECTIONS
               if not any(r['name'] == s for r in rows)]
    for m in missing:
        issues.append('\u7f3a\u5c11\u300c%s\u300d\u6bb5' % m)
    return (rows, total_chars, total_min, target, rate, issues, missing)


def evidence_check(data):
    evs = data.get('evidence') or []
    rows = []
    full = 0
    with_num = 0
    linked = 0
    not_we = 0
    for e in evs:
        label = e.get('label') or '\uff08\u672a\u547d\u540d\uff09'
        miss = [STAR_CN[k] for k in STAR_KEYS if not e.get(k)]
        ok = not miss
        if ok:
            full += 1
        if e.get('has_number'):
            with_num += 1
        if e.get('links_to_job'):
            linked += 1
        if e.get('we_only'):
            not_we += 1
        rows.append({'label': label, 'star_rate': round((4 - len(miss)) * 25.0),
                     'missing': miss, 'has_number': bool(e.get('has_number')),
                     'links_to_job': bool(e.get('links_to_job')),
                     'we_only': bool(e.get('we_only')),
                     'state': '\u5b8c\u6574' if ok else '\u7f3a\u8981\u7d20'})
    n = len(evs)
    star_rate = round(full * 100.0 / n, 1) if n else 0.0
    num_rate = round(with_num * 100.0 / n, 1) if n else 0.0
    link_rate = round(linked * 100.0 / n, 1) if n else 0.0
    issues = []
    if n and n < 2:
        issues.append('\u80dc\u4efb\u8bc1\u636e\u53ea\u6709 %d \u6bb5\uff1a\u5efa\u8bae 2-3 \u6bb5\uff0c\u8986\u76d6\u4e0d\u540c\u80fd\u529b\u7ef4\u5ea6' % n)
    if n > 3:
        issues.append('\u80dc\u4efb\u8bc1\u636e %d \u6bb5\u504f\u591a\uff1a\u8bc4\u59d4\u8bb0\u4e0d\u4f4f\uff0c\u63a7\u5236\u5728 2-3 \u6bb5' % n)
    if star_rate < 100.0:
        issues.append('STAR \u5b8c\u6574\u5ea6 %.1f%%\uff1a\u7f3a S/T/A/R \u4efb\u4e00\u8981\u7d20\u7684\u8bc1\u636e\u9700\u8865\u9f50' % star_rate)
    if num_rate < 100.0:
        issues.append('\u6709\u8bc1\u636e\u7ed3\u679c\u7f3a\u6570\u5b57\uff1a\u6ca1\u6709\u6570\u5b57\u7684\u8bc1\u636e\u53ef\u4fe1\u5ea6\u4f4e')
    if link_rate < 100.0:
        issues.append('\u6709\u8bc1\u636e\u672a\u8bb2\u5230\u7b2c\u4e09\u7ea7\u53f0\u9636\uff08links_to_job\uff09\uff1a\u9700\u8bf4\u660e\u8fd9\u5bf9\u5e94\u672c\u5c97\u4f4d\u4ec0\u4e48\u8981\u6c42')
    if not_we:
        issues.append('%d \u6bb5\u8bc1\u636e\u5168\u90e8\u5199\u6210\u300c\u6211\u4eec\u300d\uff0c\u770b\u4e0d\u51fa\u4e2a\u4eba\u8d21\u732e' % not_we)
    return rows, star_rate, num_rate, link_rate, issues


def deduct_check(data):
    blobs = []
    for s in (data.get('sections') or []):
        blobs.append((s.get('name') or '\u6bb5\u843d', s.get('text') or ''))
    for r in (data.get('risks') or []):
        blobs.append(('\u81ea\u8bc4', r or ''))

    rows = []
    for name, text in blobs:
        for cat in sorted(DEDUCT.keys()):
            hits = [w for w in DEDUCT[cat] if w in (text or '')]
            if hits:
                rows.append({'where': name, 'category': cat,
                             'hits': hits})
    issues = []
    for r in rows:
        issues.append('\u300c%s\u300d\u547d\u4e2d%s\u7c7b\u6263\u5206\u8868\u8ff0\uff1a%s'
                      % (r['where'], r['category'], '\u3001'.join(r['hits'])))
    return rows, issues


def build(data, fmt='md'):
    title = data.get('title') or '\u7ade\u8058\u6f14\u8bb2\u7a3f\u4f53\u68c0'
    (d_rows, total_chars, total_min, target, rate, d_issues,
     missing) = duration_check(data)
    e_rows, star_rate, num_rate, link_rate, e_issues = evidence_check(data)
    ded_rows, ded_issues = deduct_check(data)
    all_issues = d_issues + e_issues + ded_issues

    if fmt == 'json':
        return {'title': title, 'total_chars': total_chars,
                'total_minutes': total_min, 'target_minutes': target,
                'speech_rate': rate,
                'sections': d_rows, 'missing_sections': missing,
                'duration_issues': d_issues,
                'evidence': e_rows, 'star_rate': star_rate,
                'number_rate': num_rate, 'link_rate': link_rate,
                'evidence_issues': e_issues,
                'deduct_rows': ded_rows, 'deduct_issues': ded_issues}

    out = []
    out.append('# %s' % title)
    out.append('')
    out.append('- \u603b\u5b57\u6570\uff1a%d' % total_chars)
    out.append('- \u6298\u7b97\u65f6\u957f\uff1a%s \u5206\u949f\uff08\u8bed\u901f %s \u5b57/\u5206\uff09' % (total_min, rate))
    out.append('- \u76ee\u6807\u65f6\u957f\uff1a%s \u5206\u949f' % (target if target else '\u672a\u586b'))
    out.append('- \u7f3a\u5931\u6bb5\u843d\uff1a%s' % ('\u3001'.join(missing) if missing else '\u65e0'))
    out.append('- STAR \u5b8c\u6574\u5ea6\uff1a%.1f%%' % star_rate)
    out.append('- \u8bc1\u636e\u542b\u6570\u6bd4\u4f8b\uff1a%.1f%%' % num_rate)
    out.append('- \u8bb2\u5230\u7b2c\u4e09\u7ea7\u6bd4\u4f8b\uff1a%.1f%%' % link_rate)
    out.append('- \u6263\u5206\u8868\u8ff0\u547d\u4e2d\uff1a%d \u5904' % len(ded_rows))
    out.append('')
    out.append('## \u4e00\u3001\u5206\u6bb5\u65f6\u957f')
    out.append('')
    out.append('| \u6bb5\u843d | \u5b57\u6570 | \u6298\u7b97\u5206\u949f | \u5b9e\u9645\u5360\u6bd4 | \u76ee\u6807\u5360\u6bd4 | \u504f\u5dee | \u5224\u5b9a |')
    out.append('|---|---|---|---|---|---|---|')
    for r in d_rows:
        act = ('%.0f%%' % r['share_actual']) if r['share_actual'] is not None else '-'
        want = ('%.0f%%' % r['share_want']) if r['share_want'] is not None else '-'
        dif = ('%+.0f%%' % r['share_diff']) if r['share_diff'] is not None else '-'
        out.append('| %s | %d | %s | %s | %s | %s | %s |' % (
            r['name'], r['chars'],
            ('%.1f' % r['minutes']) if r['minutes'] is not None else '-',
            act, want, dif, r['state']))
    out.append('')
    if d_issues:
        for i, it in enumerate(d_issues, 1):
            out.append('%d. %s' % (i, it))
        out.append('')
    out.append('## \u4e8c\u3001\u80dc\u4efb\u8bc1\u636e STAR \u5b8c\u6574\u5ea6')
    out.append('')
    out.append('| \u8bc1\u636e | STAR | \u7f3a\u8981\u7d20 | \u542b\u6570\u5b57 | \u6307\u5411\u5c97\u4f4d | \u5168\u79f0\u6211\u4eec | \u5224\u5b9a |')
    out.append('|---|---|---|---|---|---|---|')
    for r in e_rows:
        out.append('| %s | %.0f%% | %s | %s | %s | %s | %s |' % (
            r['label'], r['star_rate'], '\u3001'.join(r['missing']) if r['missing'] else '-',
            'Y' if r['has_number'] else '-',
            'Y' if r['links_to_job'] else '-',
            'Y' if r['we_only'] else '-', r['state']))
    if not e_rows:
        out.append('| \uff08\u672a\u586b\u8bc1\u636e\uff09 | - | - | - | - | - | \u5efa\u8bae 2-3 \u6bb5 |')
    out.append('')
    if e_issues:
        for i, it in enumerate(e_issues, 1):
            out.append('%d. %s' % (i, it))
        out.append('')
    out.append('## \u4e09\u3001\u6263\u5206\u8868\u8ff0')
    out.append('')
    if not ded_rows:
        out.append('\u672a\u547d\u4e2d\u516b\u7c7b\u6263\u5206\u8bcd\u3002\u4ecd\u9700\u4eba\u5de5\u786e\u8ba4\uff1a\u6bcf\u6761\u8868\u8ff0\u90fd\u5e26\u7ed3\u679c\u3001\u6bcf\u6bb5\u90fd\u80fd\u63a8\u5230\u5c97\u4f4d\u8981\u6c42\u3002')
    else:
        out.append('| \u4f4d\u7f6e | \u7c7b\u522b | \u547d\u4e2d | \u6539\u6cd5 |')
        out.append('|---|---|---|---|')
        fixes = {
            '\u8868\u6001\u5f0f\u7a7a\u8bdd': '\u5220\u6389\uff0c\u6362\u6210 30 \u5929\u5177\u4f53\u505a\u4ec0\u4e48',
            '\u590d\u8ff0JD': '\u6362\u6210\u8fd9\u4e2a\u5c97\u4f4d\u5f53\u4e0b\u6700\u96be\u7684\u4e00\u4ef6\u4e8b',
            '\u6ca1\u6709\u6570\u5b57': '\u8865\u4e00\u4e2a\u53ef\u6838\u67e5\u7684\u6570\u5b57',
            '\u5168\u5458\u6211\u4eec': '\u5199\u6e05\u4eba\u6570\u3001\u5206\u5de5\u4e0e\u81ea\u5df1\u627f\u62c5\u7684\u90a3\u6bb5',
            '\u8fc7\u5ea6\u627f\u8bfa': '\u6539\u4e3a\u627f\u8bfa\u53ef\u63a7\u7684\u673a\u5236\u4e0e\u6d41\u7a0b',
            '\u653b\u51fb\u7ade\u8058\u8005': '\u5220\u6389\uff0c\u53ea\u8bb2\u5c97\u4f4d\u4e0e\u505a\u6cd5',
            '\u5426\u5b9a\u524d\u4eba': '\u6539\u4e3a\u73b0\u6709\u505a\u6cd5\u6709\u6548\u4f46\u9700\u5728\u67d0\u573a\u666f\u8865\u5145',
        }
        for r in ded_rows:
            out.append('| %s | %s | %s | %s |' % (
                r['where'], r['category'], '\u3001'.join(r['hits']),
                fixes.get(r['category'], '\u6539\u5199')))
    out.append('')
    out.append('## \u56db\u3001\u6574\u6539\u5efa\u8bae')
    out.append('')
    idx = 0
    if missing:
        idx += 1
        out.append('%d. \u7f3a\u5931\u6bb5\u843d\uff1a%s\u3002\u56db\u6bb5\u7ed3\u6784\u4e0d\u80fd\u7701\u3002' % (idx, '\u3001'.join(missing)))
    for it in d_issues:
        idx += 1
        out.append('%d. %s' % (idx, it))
    for it in e_issues:
        idx += 1
        out.append('%d. %s' % (idx, it))
    if len(ded_rows) >= 3:
        idx += 1
        out.append('%d. \u6263\u5206\u8868\u8ff0\u8f83\u96c6\u4e2d\uff08%d \u5904\uff09\uff1a\u4f18\u5148\u5220\u8868\u6001\u5f0f\u7a7a\u8bdd\u4e0e\u8fc7\u5ea6\u627f\u8bfa\uff0c'
                   '\u8fd9\u4e24\u7c7b\u6700\u5bb9\u6613\u88ab\u8bc4\u59d4\u8bb0\u4f4f\u3002' % (idx, len(ded_rows)))
    elif ded_rows:
        idx += 1
        out.append('%d. \u6263\u5206\u8868\u8ff0 %d \u5904\uff1a\u6309\u4e0a\u8868\u9010\u6761\u6539\u5199\u3002' % (idx, len(ded_rows)))
    if not idx:
        out.append('\u7ed3\u6784\u3001\u65f6\u957f\u3001STAR \u4e0e\u8868\u8ff0\u5747\u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\u3002'
                   '\u5b9a\u7a3f\u524d\u6390\u8868\u9884\u6f14\u4e09\u904d\u5e76\u56de\u653e\u5f55\u97f3\uff0c\u68c0\u67e5\u8bed\u901f\u3001\u5361\u987f\u4e0e\u7ed3\u5c3e\u3002')
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

    def mk(chars, name):
        return {'name': name, 'text': 'x' * chars}

    # 10 \u5206\u949f\u76ee\u6807\uff1a240 \u5b57/\u5206 -> 2400 \u5b57
    # \u5206\u914d\uff1a240/480/1080/600 = 2400
    secs = [mk(240, '\u81ea\u6211\u4ecb\u7ecd'), mk(480, '\u5c97\u4f4d\u8ba4\u77e5'),
            mk(1080, '\u80dc\u4efb\u8bc1\u636e'), mk(600, '\u4e0a\u4efb\u6253\u7b97')]
    good_ev = [{'label': '\u5bf9\u8d26\u6d41\u7a0b\u4f18\u5316', 'has_situation': True,
                'has_task': True, 'has_action': True, 'has_result': True,
                'has_number': True, 'links_to_job': True, 'we_only': False}]
    r = build({'target_minutes': 10, 'speech_rate': 240,
               'sections': secs, 'evidence': good_ev}, 'json')
    chk(r['total_chars'] == 2400, '\u603b\u5b57\u6570\u5e94\u4e3a 2400')
    chk(abs(r['total_minutes'] - 10.0) < 0.05, '2400 \u5b57 240 \u5b57\u6bcf\u5206\u5e94\u4e3a 10 \u5206\u949f')
    chk(r['missing_sections'] == [], '\u56db\u6bb5\u9f50\u5168\u4e0d\u5e94\u6709\u7f3a\u5931')
    chk(len(r['duration_issues']) == 0, '\u89c4\u8303\u914d\u6bd4\u4e0d\u5e94\u6709\u65f6\u957f\u95ee\u9898')
    chk(r['star_rate'] == 100.0, 'STAR \u9f50\u5168\u5e94\u4e3a 100')
    chk(r['link_rate'] == 100.0, '\u90fd\u6307\u5411\u5c97\u4f4d\u5e94\u4e3a 100')

    over = [mk(300, '\u81ea\u6211\u4ecb\u7ecd'), mk(500, '\u5c97\u4f4d\u8ba4\u77e5'),
            mk(2400, '\u80dc\u4efb\u8bc1\u636e'), mk(600, '\u4e0a\u4efb\u6253\u7b97')]
    r = build({'target_minutes': 10, 'speech_rate': 240,
               'sections': over}, 'json')
    chk(r['total_minutes'] > 10.0 * 1.05, '3800 \u5b57\u5e94\u8d85\u51fa\u76ee\u6807\u65f6\u957f')
    chk(any('\u8d85\u51fa\u76ee\u6807' in i for i in r['duration_issues']), '\u5e94\u63d0\u793a\u603b\u65f6\u957f\u8d85\u51fa')
    ev_sec = [x for x in r['sections'] if x['name'] == '\u80dc\u4efb\u8bc1\u636e'][0]
    chk(ev_sec['state'] == '\u660e\u663e\u8d85\u65f6', '\u8bc1\u636e\u6bb5\u8fc7\u957f\u5e94\u5224\u660e\u663e\u8d85\u65f6')

    short = [mk(100, '\u81ea\u6211\u4ecb\u7ecd'), mk(200, '\u5c97\u4f4d\u8ba4\u77e5'),
             mk(400, '\u80dc\u4efb\u8bc1\u636e'), mk(100, '\u4e0a\u4efb\u6253\u7b97')]
    r = build({'target_minutes': 10, 'speech_rate': 240,
               'sections': short}, 'json')
    chk(any('\u4f4e\u4e8e\u76ee\u6807' in i for i in r['duration_issues']), '\u603b\u65f6\u957f\u8fc7\u77ed\u5e94\u63d0\u793a')

    r = build({'sections': [mk(240, '\u81ea\u6211\u4ecb\u7ecd')]}, 'json')
    chk(len(r['missing_sections']) == 3, '\u5355\u6bb5\u5e94\u7f3a 3 \u6bb5')
    chk(any('\u7f3a\u5c11' in i for i in r['duration_issues']), '\u5e94\u63d0\u793a\u7f3a\u6bb5')

    bad_rate = {'target_minutes': 10, 'speech_rate': 400, 'sections': secs}
    r = build(bad_rate, 'json')
    chk(any('\u8bed\u901f' in i for i in r['duration_issues']), '\u8bed\u901f\u5f02\u5e38\u5e94\u63d0\u793a')

    r = build({'sections': secs}, 'json')
    chk(r['speech_rate'] == RATE_DEFAULT, '\u672a\u586b\u8bed\u901f\u5e94\u53d6\u9ed8\u8ba4 240')

    r = build({'sections': secs, 'target_minutes': None}, 'json')
    chk(r['target_minutes'] is None, '\u672a\u586b\u76ee\u6807\u65f6\u957f\u5e94\u4e3a None \u800c\u975e\u62a5\u9519')

    bad_ev = [{'label': 'A', 'has_situation': True, 'has_task': True,
               'has_action': False, 'has_result': False,
               'has_number': False, 'links_to_job': False, 'we_only': True}]
    r = build({'evidence': bad_ev}, 'json')
    chk(r['star_rate'] == 0.0, '\u7f3a A/R \u65f6 STAR \u5b8c\u6574\u5ea6\u4e3a 0')
    chk(len(r['evidence'][0]['missing']) == 2, '\u5e94\u62a5 2 \u4e2a\u7f3a\u5931\u8981\u7d20')
    chk(len(r['evidence_issues']) >= 5, 'we-only evidence should be flagged')

    half_ev = [
        {'label': 'A', 'has_situation': True, 'has_task': True,
         'has_action': True, 'has_result': True, 'has_number': True,
         'links_to_job': True},
        {'label': 'B', 'has_situation': True, 'has_task': True,
         'has_action': False, 'has_result': True, 'has_number': False,
         'links_to_job': False},
    ]
    r = build({'evidence': half_ev}, 'json')
    chk(r['star_rate'] == 50.0, '\u4e00\u534a\u5b8c\u6574\u5e94\u4e3a 50')
    chk(r['number_rate'] == 50.0, '\u4e00\u534a\u542b\u6570\u5e94\u4e3a 50')
    chk(r['link_rate'] == 50.0, '\u4e00\u534a\u6307\u5411\u5c97\u4f4d\u5e94\u4e3a 50')
    chk(any('\u7b2c\u4e09\u7ea7' in i for i in r['evidence_issues']), '\u5e94\u63d0\u793a\u8865\u7b2c\u4e09\u7ea7\u53f0\u9636')

    r = build({'evidence': []}, 'json')
    chk(r['star_rate'] == 0.0, '\u7a7a\u8bc1\u636e STAR \u7387\u4e3a 0 \u800c\u975e\u62a5\u9519')

    r = build({'evidence': [good_ev[0]]}, 'json')
    chk(any('\u53ea\u6709 1 \u6bb5' in i for i in r['evidence_issues']), '\u5355\u6bb5\u8bc1\u636e\u5e94\u63d0\u793a')

    r = build({'evidence': [good_ev[0]] * 5}, 'json')
    chk(any('\u504f\u591a' in i for i in r['evidence_issues']), '\u4e94\u6bb5\u8bc1\u636e\u5e94\u63d0\u793a\u504f\u591a')

    ded = {'sections': [
        {'name': '\u81ea\u6211\u4ecb\u7ecd',
         'text': '\u6211\u5c06\u5168\u529b\u4ee5\u8d74\uff0c\u8bf7\u7ec4\u7ec7\u653e\u5fc3\uff0c\u4e00\u5b9a\u8d85\u989d\u5b8c\u6210\u4efb\u52a1\u3002'},
        {'name': '\u5c97\u4f4d\u8ba4\u77e5',
         'text': '\u8fd9\u4e2a\u5c97\u4f4d\u8981\u6c42\u6709\u8f83\u5f3a\u7684\u8d23\u4efb\u5fc3\uff0c\u6211\u4eec\u56e2\u961f\u5b8c\u6210\u4e86\u6539\u9020\u3002'},
    ], 'risks': ['\u4e00\u5e74\u5185\u4e1a\u7ee9\u7ffb\u4e09\u500d', '\u539f\u6765\u7684\u65b9\u6cd5\u6839\u672c\u4e0d\u884c']}
    r = build(ded, 'json')
    cats = set(x['category'] for x in r['deduct_rows'])
    chk('\u8868\u6001\u5f0f\u7a7a\u8bdd' in cats, '\u5e94\u547d\u4e2d\u8868\u6001\u5f0f\u7a7a\u8bdd')
    chk('\u8fc7\u5ea6\u627f\u8bfa' in cats, '\u5e94\u547d\u4e2d\u8fc7\u5ea6\u627f\u8bfa')
    chk('\u590d\u8ff0JD' in cats, '\u5e94\u547d\u4e2d\u590d\u8ff0JD')
    chk('\u5168\u5458\u6211\u4eec' in cats, '\u5e94\u547d\u4e2d\u5171 \u5168\u4f53\u8868\u8ff0')
    chk('\u653b\u51fb\u7ade\u8058\u8005' not in cats, '\u65e0\u653b\u51fb\u8868\u8ff0\u4e0d\u5e94\u8bef\u62a5')
    chk(len(r['deduct_rows']) >= 4, '\u5e94\u81f3\u5c11\u547d\u4e2d 4 \u7c7b')

    clean = {'sections': [
        {'name': '\u81ea\u6211\u4ecb\u7ecd', 'text': '\u5404\u4f4d\u8bc4\u59d4\u597d\uff0c\u6211\u662f\u5f20\u4e09\uff0c\u73b0\u4efb\u67d0\u5c97\u4f4d\u3002'},
        {'name': '\u5c97\u4f4d\u8ba4\u77e5', 'text': '\u8fd9\u4e2a\u5c97\u4f4d\u5f53\u4e0b\u6700\u96be\u7684\u662f\u8de8\u7ebf\u8d44\u6e90\u51b2\u7a81\u3002'},
    ]}
    r = build(clean, 'json')
    chk(r['deduct_rows'] == [], '\u89c4\u8303\u6587\u672c\u4e0d\u5e94\u547d\u4e2d\u6263\u5206\u8bcd')

    txt = build({'sections': secs, 'evidence': good_ev}, 'md')
    chk('\u5206\u6bb5\u65f6\u957f' in txt, 'md \u5e94\u542b\u5206\u6bb5\u65f6\u957f\u8868')
    chk('STAR' in txt, 'md \u5e94\u542b STAR \u6bb5')
    chk('\u6263\u5206\u8868\u8ff0' in txt, 'md \u5e94\u542b\u6263\u5206\u8868\u8ff0\u6bb5')
    chk('\u6574\u6539\u5efa\u8bae' in txt, 'md \u5e94\u542b\u6574\u6539\u5efa\u8bae')

    r = build({}, 'json')
    chk(r['total_chars'] == 0, '\u7a7a\u8f93\u5165\u4e0d\u62a5\u9519')

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
    ap = argparse.ArgumentParser(description='\u7ade\u8058\u6f14\u8bb2\u7a3f\u7ed3\u6784\u6838\u67e5')
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
