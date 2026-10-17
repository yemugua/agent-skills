#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u6295\u8bc9\u4fe1\uff08\u6295\u8bc9\u4e66\uff09\u8981\u7d20\u5b8c\u5907\u6027\u6838\u67e5\u4e0e\u98ce\u9669\u8bcd\u626b\u63cf\u3002

\u7528\u6cd5:
  python complaint_check.py --file \u6295\u8bc9\u4fe1.txt
  python complaint_check.py --file \u6295\u8bc9\u4fe1.txt --out \u6838\u67e5\u7ed3\u679c.md --format md
  python complaint_check.py --selftest
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

# \u5fc5\u5907\u8981\u7d20: (key, \u540d\u79f0, \u6b63\u5219, \u662f\u5426\u5fc5\u586b)
ELEMENTS = [
    ('org', '\u53d7\u7406\u5355\u4f4d\u540d\u79f0', r'(\u5c0a\u656c\u7684|\u81f4\uff1a|\u81f4:|\u53d7\u7406\u5355\u4f4d|'
     r'\u5e02\u573a\u76d1\u7763|\u7ba1\u7406\u5c40|\u7ba1\u7406\u59d4\u5458\u4f1a|'
     r'\u59d4\u5458\u4f1a|\u5ba2\u670d\u4e2d\u5fc3|\u5e73\u53f0|\u603b\u516c\u53f8|'
     r'\u6d88\u8d39\u8005\u534f\u4f1a|\u6cd5\u9662)', True),
    ('name', '\u6295\u8bc9\u4eba\u59d3\u540d', r'(\u6295\u8bc9\u4eba|\u672c\u4eba|\u6211\u53eb|\u59d3\u540d|'
     r'\u6211\u662f|\u6211\u4e8e)', True),
    ('contact', '\u8054\u7cfb\u65b9\u5f0f', r'(1[3-9]\d{9}|\u7535\u8bdd|\u624b\u673a|\u8054\u7cfb\u65b9\u5f0f|'
     r'\u8054\u7cfb\u7535\u8bdd|@)', True),
    ('target', '\u88ab\u6295\u8bc9\u65b9\u5168\u79f0', r'(\u88ab\u6295\u8bc9\u65b9|\u88ab\u6295\u8bc9\u4eba|'
     r'\u88ab\u6295\u8bc9\u5355\u4f4d|\u88ab\u544a\u4eba|\u5546\u5bb6|\u5e97\u94fa|'
     r'\u7ecf\u8425\u8005|\u516c\u53f8|\u6709\u9650\u516c\u53f8)', True),
    ('timeline', '\u4e8b\u5b9e\u65f6\u95f4\u7ebf\uff08\u81f3\u5c11 3 \u4e2a\u65f6\u95f4\u70b9\uff09', None, True),
    ('demand', '\u5177\u4f53\u8bc9\u6c42', r'(\u8981\u6c42|\u8bf7\u6c42|\u8bc9\u6c42|\u5e0c\u671b|\u8bf7\u8d35|'
     r'\u4e88\u4ee5|\u9000\u8fd8|\u9000\u6b3e|\u8d54\u507f|\u9053\u6b49|'
     r'\u67e5\u5904|\u6574\u6539|\u66f4\u6362|\u7ef4\u4fee|\u8fd4\u8fd8)', True),
    ('amount', '\u4e89\u8bae\u91d1\u989d', r'(\d[\d,]*(\.\d+)?\s*\u5143|\u4eba\u6c11\u5e01|\u91d1\u989d)', False),
    ('voucher', '\u51ed\u8bc1\u7f16\u53f7', r'(\u8ba2\u5355\u53f7|\u5408\u540c\u7f16\u53f7|\u53d1\u7968\u53f7|'
     r'\u8fd0\u5355\u53f7|\u4fdd\u5355\u53f7|\u7f16\u53f7|\u6d41\u6c34\u53f7)', False),
    ('negotiate', '\u5df2\u534f\u5546\u60c5\u51b5', r'(\u534f\u5546|\u6c9f\u901a|\u8054\u7cfb\u8fc7|\u591a\u6b21|'
     r'\u7b54\u590d|\u7b54\u590d|\u62d2\u7edd|\u4e0d\u4e88|\u5ba2\u670d)', False),
    ('evidence', '\u8bc1\u636e\u6e05\u5355', r'(\u9644\u4ef6|\u8bc1\u636e|\u622a\u56fe|\u7167\u7247|\u5f55\u97f3|'
     r'\u53d1\u7968|\u6536\u636e|\u804a\u5929\u8bb0\u5f55|\u68c0\u6d4b\u62a5\u544a)', True),
    ('sign', '\u7b7e\u540d/\u843d\u6b3e', r'(\u7b7e\u540d|\u7b7e\u5b57|\u843d\u6b3e|\u6295\u8bc9\u4eba\uff1a|'
     r'\u6295\u8bc9\u4eba:)', True),
    ('date', '\u843d\u6b3e\u65e5\u671f', r'(\d{4}\s*\u5e74\s*\d{1,2}\s*\u6708\s*\d{1,2}\s*\u65e5|'
     r'\d{4}-\d{1,2}-\d{1,2})', True),
]

DATE_RE = r'(\d{4}\s*\u5e74\s*\d{1,2}\s*\u6708\s*\d{1,2}\s*\u65e5|\d{4}-\d{1,2}-\d{1,2}|\d{4}/\d{1,2}/\d{1,2})'

RISK_WORDS = {
    '\u60c5\u7eea\u5316\u8bcd': [
        '\u5783\u573e', '\u9a97\u5b50', '\u9ed1\u5fc3', '\u8bc8\u9a97', '\u6b3a\u8bc8',
        '\u65e0\u826f', '\u5751\u4eba', '\u8840\u6c57\u94b1', '\u6001\u5ea6\u6781\u5176\u6076\u52a3',
        '\u6b7b', '\u55b7', '\u6df7\u8d26', '\u4e0d\u8981\u8138',
    ],
    '\u5a01\u80c1\u6027\u8868\u8ff0': [
        '\u66dd\u5149\u4e2a\u4eba\u4fe1\u606f', '\u4eba\u8089\u641c\u7d22', '\u4eba\u8089',
        '\u4e0a\u95e8\u627e\u4f60', '\u7f51\u7edc\u66dd\u5149', '\u5a92\u4f53\u66dd\u5149',
        '\u628a\u4f60\u4eec\u66dd\u5149', '\u516c\u5f00\u4f60\u7684\u4fe1\u606f', '\u6ca1\u5b8c',
    ],
    '\u65e0\u8bc1\u636e\u652f\u6491\u7684\u5b9a\u6027': [
        '\u6545\u610f', '\u6076\u610f', '\u4e32\u901a', '\u6536\u4e86\u597d\u5904\u8d39',
        '\u5185\u5e55', '\u5b98\u5546\u52fe\u7ed3', '\u660e\u660e\u662f', '\u80af\u5b9a\u662f',
    ],
}


def scan(text):
    lines = text.splitlines()
    date_hits = re.findall(DATE_RE, text)
    results = []
    for key, name, pattern, required in ELEMENTS:
        if key == 'timeline':
            n = len(set(date_hits))
            ok = n >= 3
            results.append({
                'key': key, 'name': name, 'required': required,
                'status': '\u6709' if ok else '\u7f3a',
                'detail': '\u547d\u4e2d\u65f6\u95f4\u70b9 %d \u4e2a\uff08\u8981\u6c42\u4e0d\u5c11\u4e8e 3 \u4e2a\uff09' % n,
            })
            continue
        m = re.search(pattern, text)
        results.append({
            'key': key, 'name': name, 'required': required,
            'status': '\u6709' if m else '\u7f3a',
            'detail': ('\u547d\u4e2d\uff1a%s' % m.group(0)) if m else '\u672a\u627e\u5230\u76f8\u5173\u8868\u8ff0',
        })

    risks = []
    for cat, words in RISK_WORDS.items():
        hits = [w for w in words if w in text]
        if hits:
            risks.append({'category': cat, 'words': hits, 'count': len(hits)})

    required_missing = [r for r in results if r['required'] and r['status'] == '\u7f3a']
    optional_missing = [r for r in results if not r['required'] and r['status'] == '\u7f3a']
    total = len(results)
    present = sum(1 for r in results if r['status'] == '\u6709')
    completeness = int(round(present * 100.0 / total))

    if not required_missing and not risks:
        verdict = '\u53ef\u4ee5\u63d0\u4ea4'
    elif len(required_missing) <= 2 and not risks:
        verdict = '\u8865\u6b63\u540e\u53ef\u63d0\u4ea4'
    elif required_missing:
        verdict = '\u4e0d\u5efa\u8bae\u63d0\u4ea4\uff08\u7f3a\u5fc5\u5907\u8981\u7d20\uff09'
    else:
        verdict = '\u4fee\u6539\u63aa\u8f9e\u540e\u518d\u63d0\u4ea4'

    return {
        'elements': results,
        'risks': risks,
        'required_missing': [r['name'] for r in required_missing],
        'optional_missing': [r['name'] for r in optional_missing],
        'completeness': completeness,
        'verdict': verdict,
        'date_count': len(set(date_hits)),
    }


def render_md(r):
    out = []
    out.append('# \u6295\u8bc9\u4fe1\u8981\u7d20\u6838\u67e5\u7ed3\u679c')
    out.append('')
    out.append('- \u8981\u7d20\u5b8c\u5907\u5ea6\uff1a%d%%' % r['completeness'])
    out.append('- \u7ed3\u8bba\uff1a%s' % r['verdict'])
    out.append('')
    out.append('## \u8981\u7d20\u6838\u67e5\u8868')
    out.append('')
    out.append('| \u8981\u7d20 | \u5fc5\u586b | \u72b6\u6001 | \u8bf4\u660e |')
    out.append('|---|---|---|---|')
    for e in r['elements']:
        out.append('| %s | %s | %s | %s |' % (
            e['name'], '\u5fc5\u586b' if e['required'] else '\u9009\u586b',
            e['status'], e['detail']))
    out.append('')
    if r['required_missing']:
        out.append('## \u7f3a\u5931\u7684\u5fc5\u5907\u8981\u7d20')
        out.append('')
        for n in r['required_missing']:
            out.append('- %s' % n)
        out.append('')
    if r['optional_missing']:
        out.append('## \u7f3a\u5931\u7684\u9009\u586b\u8981\u7d20')
        out.append('')
        for n in r['optional_missing']:
            out.append('- %s' % n)
        out.append('')
    if r['risks']:
        out.append('## \u98ce\u9669\u8868\u8ff0\uff08\u5efa\u8bae\u6539\u5199\uff09')
        out.append('')
        out.append('| \u7c7b\u522b | \u547d\u4e2d\u8bcd | \u6570\u91cf |')
        out.append('|---|---|---|')
        for k in r['risks']:
            out.append('| %s | %s | %d |' % (k['category'], '\u3001'.join(k['words']), k['count']))
        out.append('')
        out.append('\u6539\u5199\u539f\u5219\uff1a\u53ea\u5199\u4e8b\u5b9e\u548c\u8bc1\u636e\uff0c\u4e0d\u5199\u63a8\u6d4b\u3001\u52a8\u673a\u4e0e\u60c5\u7eea\u3002'
                   '\u628a\u300c\u5546\u5bb6\u6001\u5ea6\u6781\u5176\u6076\u52a3\u300d\u6539\u6210\u300c\u5546\u5bb6\u4e8e X \u6708 X \u65e5\u660e\u786e\u8868\u793a\u4e0d\u4e88\u9000\u6362\u300d\u3002')
        out.append('')
    out.append('## \u9632\u8bef\u4f24\u63d0\u9192')
    out.append('')
    out.append('1. \u811a\u672c\u53ea\u505a\u5173\u952e\u8bcd\u5339\u914d\uff0c\u547d\u4e2d\u4e0d\u7b49\u4e8e\u5199\u5bf9\u4e86\uff0c\u9010\u9879\u4eba\u5de5\u590d\u6838\u3002')
    out.append('2. \u63d0\u4ea4\u540e\u5fc5\u987b\u62ff\u5230\u53d7\u7406\u7f16\u53f7\u6216\u56de\u6267\uff0c\u6ca1\u6709\u7f16\u53f7\u7b49\u4e8e\u6ca1\u63d0\u4ea4\u3002')
    out.append('3. \u6295\u8bc9\u4e0d\u4ea7\u751f\u786e\u5b9a\u7684\u8bc9\u8bbc\u65f6\u6548\u4e2d\u65ad\u6548\u529b\uff0c\u6d89\u91d1\u989d\u8f83\u5927\u6216\u4e34\u8fd1\u5c4a\u6ee1\u7684\u5e94\u53e6\u884c\u8003\u8651\u8d77\u8bc9\u6216\u4ef2\u88c1\u3002')
    out.append('')
    return '\n'.join(out)


SAMPLE_FULL = """\u5173\u4e8e\u67d0\u5546\u57ce\u5546\u5bb6\u62d2\u4e0d\u9000\u6b3e\u7684\u6295\u8bc9\u4e66

\u5c0a\u656c\u7684\u67d0\u533a\u5e02\u573a\u76d1\u7763\u7ba1\u7406\u5c40\uff1a

\u6295\u8bc9\u4eba\uff1a\u5f20\u4e09\uff0c\u8054\u7cfb\u7535\u8bdd\uff1a13800001234
\u88ab\u6295\u8bc9\u65b9\uff1a\u67d0\u67d0\u5546\u57ce\u6709\u9650\u516c\u53f8\uff08\u5e97\u94fa\u540d\uff1aXX\u4e13\u8425\u5e97\uff09

\u4e8b\u5b9e\u7ecf\u8fc7\uff1a
2026\u5e743\u67085\u65e5\uff0c\u6211\u5728\u8be5\u5e97\u8d2d\u4e70\u5546\u54c1\uff0c\u8ba2\u5355\u53f7 20260305001\uff0c\u652f\u4ed8 1,280 \u5143\u3002
2026\u5e743\u67088\u65e5\uff0c\u5546\u54c1\u51fa\u73b0\u6545\u969c\uff0c\u4e0e\u5546\u54c1\u9875\u9762\u627f\u8bfa\u4e0d\u4e00\u81f4\u3002
2026\u5e743\u67089\u65e5\u8d7015\u65e5\uff0c\u6211\u4e09\u6b21\u4e0e\u5ba2\u670d\u6c9f\u901a\uff0c\u5ba2\u670d\u4e8e4\u67082\u65e5\u660e\u786e\u7b54\u590d\u4e0d\u4e88\u9000\u6362\u3002

\u8bc9\u6c42\uff1a1.\u9000\u8fd8\u8d27\u6b3e 1,280 \u5143\uff1b2.\u9000\u8d27\u8fd0\u8d39\u7531\u5546\u5bb6\u627f\u62c5\u3002

\u9644\u4ef6\uff1a1.\u8ba2\u5355\u622a\u56fe 2.\u5546\u54c1\u9875\u9762\u622a\u56fe 3.\u5ba2\u670d\u804a\u5929\u8bb0\u5f55 4.\u53d1\u7968

\u7b7e\u540d\uff1a\u5f20\u4e09
2026\u5e744\u67086\u65e5
"""

SAMPLE_POOR = """\u6211\u8981\u6295\u8bc9\uff01
\u90a3\u5bb6\u5e97\u771f\u7684\u592a\u8fc7\u5206\u4e86\uff0c\u4e70\u7684\u4e1c\u897f\u4e0d\u597d\u7528\uff0c
\u6211\u8ddf\u4ed6\u4eec\u8bf4\u4e86\uff0c\u4ed6\u4eec\u4e0d\u7ba1\u3002
\u5fc5\u987b\u7ed9\u6211\u4e00\u4e2a\u8bf4\u6cd5\u3002
"""

SAMPLE_RISKY = """\u5173\u4e8e\u67d0\u516c\u53f8\u7684\u6295\u8bc9\u4e66

\u5c0a\u656c\u7684\u5e02\u573a\u76d1\u7763\u7ba1\u7406\u5c40\uff1a
\u6295\u8bc9\u4eba\uff1a\u674e\u56db\uff0c\u624b\u673a 13900005678
\u88ab\u6295\u8bc9\u65b9\uff1a\u67d0\u67d0\u79d1\u6280\u6709\u9650\u516c\u53f8

2026\u5e745\u67081\u65e5\u8d2d\u4e70\uff0c2026\u5e745\u67083\u65e5\u51fa\u73b0\u95ee\u9898\uff0c2026\u5e745\u670810\u65e5\u5ba2\u670d\u62d2\u7edd\u5904\u7406\u3002
\u8fd9\u5bb6\u9ed1\u5fc3\u516c\u53f8\u660e\u660e\u662f\u9a97\u5b50\uff0c\u5783\u573e\u5546\u54c1\uff0c\u8fd8\u6545\u610f\u6b3a\u9a97\uff0c
\u5982\u679c\u4e0d\u7ed9\u89e3\u51b3\uff0c\u6211\u5c31\u628a\u4f60\u4eec\u7684\u4e2a\u4eba\u4fe1\u606f\u516c\u5f00\uff0c\u5a92\u4f53\u66dd\u5149\uff0c\u6ca1\u5b8c\uff01

\u8bf7\u6c42\u9000\u6b3e 2,000 \u5143\u3002
\u9644\u4ef6\uff1a\u8ba2\u5355\u53f7\u622a\u56fe\u3001\u804a\u5929\u8bb0\u5f55
\u7b7e\u540d\uff1a\u674e\u56db
2026\u5e746\u67081\u65e5
"""


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    r1 = scan(SAMPLE_FULL)
    eq('full: \u65e0\u7f3a\u5931\u5fc5\u5907\u9879', r1['required_missing'], [])
    eq('full: \u65e0\u98ce\u9669\u8bcd', r1['risks'], [])
    eq('full: \u7ed3\u8bba', r1['verdict'], '\u53ef\u4ee5\u63d0\u4ea4')
    eq('full: \u65f6\u95f4\u70b9\u4e0d\u5c11\u4e8e3', r1['date_count'] >= 3, True)

    r2 = scan(SAMPLE_POOR)
    eq('poor: \u6709\u7f3a\u5931', len(r2['required_missing']) >= 4, True)
    eq('poor: \u7ed3\u8bba', r2['verdict'], '\u4e0d\u5efa\u8bae\u63d0\u4ea4\uff08\u7f3a\u5fc5\u5907\u8981\u7d20\uff09')
    eq('poor: \u5b8c\u5907\u5ea6\u4f4e\u4e8e\u5b8c\u6574\u4ef6', r2['completeness'] < r1['completeness'], True)

    r3 = scan(SAMPLE_RISKY)
    eq('risky: \u547d\u4e2d\u98ce\u9669\u8bcd', len(r3['risks']) >= 2, True)
    eq('risky: \u7ed3\u8bba', r3['verdict'], '\u4fee\u6539\u63aa\u8f9e\u540e\u518d\u63d0\u4ea4')
    cats = [k['category'] for k in r3['risks']]
    eq('risky: \u542b\u5a01\u80c1\u6027\u8868\u8ff0', '\u5a01\u80c1\u6027\u8868\u8ff0' in cats, True)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 11\n'
               '\u8986\u76d6: \u5b8c\u6574\u4ef6\u901a\u8fc7 / \u7f3a\u8981\u7d20\u4ef6\u5224\u5b9a / '
               '\u98ce\u9669\u8bcd\u547d\u4e2d / \u5a01\u80c1\u6027\u8868\u8ff0\u8bc6\u522b')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u6295\u8bc9\u4fe1\u8981\u7d20\u5b8c\u5907\u6027\u6838\u67e5\u4e0e\u98ce\u9669\u8bcd\u626b\u63cf')
    ap.add_argument('--file', help='\u6295\u8bc9\u4fe1\u6587\u672c\u6587\u4ef6\u8def\u5f84\uff08.txt / .md\uff0cUTF-8\uff09')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'], help='\u8f93\u51fa\u683c\u5f0f')
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.file:
        print('\u7f3a\u5c11 --file\uff0c\u53ef\u7528 --selftest \u67e5\u770b\u793a\u4f8b')
        return 2
    if not os.path.exists(args.file):
        print('\u6587\u4ef6\u4e0d\u5b58\u5728: %s' % args.file)
        return 2

    with open(args.file, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    r = scan(text)
    out = render_md(r) if args.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % args.out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
