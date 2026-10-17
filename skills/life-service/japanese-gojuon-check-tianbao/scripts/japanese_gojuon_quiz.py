#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\u65e5\u8bed\u4e94\u5341\u97f3\u9ed8\u5199\u51fa\u9898\u4e0e\u6279\u6539\uff1a\u6309\u884c\u51fa\u9898\u3001\u6309\u65b9\u5411\u51fa\u9898\u3001\u6279\u6539\u7edf\u8ba1\u8584\u5f31\u884c\u3002

\u7528\u6cd5:
  python japanese_gojuon_quiz.py --mode quiz --rows a,ka --out quiz.md
  python japanese_gojuon_quiz.py --mode grade --rows a,ka --file answers.txt
  python japanese_gojuon_quiz.py --mode quiz --set dakuon --direction roma2kana --out quiz2.md
  python japanese_gojuon_quiz.py --selftest

\u53c2\u6570:
  --mode      quiz \u51fa\u9898 / grade \u6279\u6539
  --set       seion \u6e05\u97f3\uff08\u9ed8\u8ba4\uff09/ dakuon \u6d4a\u97f3\u4e0e\u534a\u6d4a\u97f3 / all
  --rows      \u6307\u5b9a\u884c\uff0c\u9017\u53f7\u5206\u9694\uff0c\u5982 a,ka,sa\uff1b\u4e0d\u586b\u5219\u5168\u90e8
  --direction kana2roma\uff08\u9ed8\u8ba4\uff09/ roma2kana / hira2kata / kata2hira
  --file      \u6279\u6539\u6a21\u5f0f\u7684\u7b54\u6848\u6587\u4ef6\uff0c\u6bcf\u884c\u4e00\u4e2a\u7b54\u6848
  --out       \u8f93\u51fa\u6587\u4ef6\u8def\u5f84
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

SEION = [
    ('a', '\u3042', '\u30a2', 'a'), ('a', '\u3044', '\u30a4', 'i'),
    ('a', '\u3046', '\u30a6', 'u'), ('a', '\u3048', '\u30a8', 'e'),
    ('a', '\u304a', '\u30aa', 'o'),
    ('ka', '\u304b', '\u30ab', 'ka'), ('ka', '\u304d', '\u30ad', 'ki'),
    ('ka', '\u304f', '\u30af', 'ku'), ('ka', '\u3051', '\u30b1', 'ke'),
    ('ka', '\u3053', '\u30b3', 'ko'),
    ('sa', '\u3055', '\u30b5', 'sa'), ('sa', '\u3057', '\u30b7', 'shi'),
    ('sa', '\u3059', '\u30b9', 'su'), ('sa', '\u305b', '\u30bb', 'se'),
    ('sa', '\u305d', '\u30bd', 'so'),
    ('ta', '\u305f', '\u30bf', 'ta'), ('ta', '\u3061', '\u30c1', 'chi'),
    ('ta', '\u3064', '\u30c4', 'tsu'), ('ta', '\u3066', '\u30c6', 'te'),
    ('ta', '\u3068', '\u30c8', 'to'),
    ('na', '\u306a', '\u30ca', 'na'), ('na', '\u306b', '\u30cb', 'ni'),
    ('na', '\u306c', '\u30cc', 'nu'), ('na', '\u306d', '\u30cd', 'ne'),
    ('na', '\u306e', '\u30ce', 'no'),
    ('ha', '\u306f', '\u30cf', 'ha'), ('ha', '\u3072', '\u30d2', 'hi'),
    ('ha', '\u3075', '\u30d5', 'fu'), ('ha', '\u3078', '\u30d8', 'he'),
    ('ha', '\u307b', '\u30db', 'ho'),
    ('ma', '\u307e', '\u30de', 'ma'), ('ma', '\u307f', '\u30df', 'mi'),
    ('ma', '\u3080', '\u30e0', 'mu'), ('ma', '\u3081', '\u30e1', 'me'),
    ('ma', '\u3082', '\u30e2', 'mo'),
    ('ya', '\u3084', '\u30e4', 'ya'), ('ya', '\u3086', '\u30e6', 'yu'),
    ('ya', '\u3088', '\u30e8', 'yo'),
    ('ra', '\u3089', '\u30e9', 'ra'), ('ra', '\u308a', '\u30ea', 'ri'),
    ('ra', '\u308b', '\u30eb', 'ru'), ('ra', '\u308c', '\u30ec', 're'),
    ('ra', '\u308d', '\u30ed', 'ro'),
    ('wa', '\u308f', '\u30ef', 'wa'), ('wa', '\u3092', '\u30f2', 'o'),
    ('n', '\u3093', '\u30f3', 'n'),
]
DAKUON = [
    ('ga', '\u304c', '\u30ac', 'ga'), ('ga', '\u304e', '\u30ae', 'gi'),
    ('ga', '\u3050', '\u30b0', 'gu'), ('ga', '\u3052', '\u30b2', 'ge'),
    ('ga', '\u3054', '\u30b4', 'go'),
    ('za', '\u3056', '\u30b6', 'za'), ('za', '\u3058', '\u30b8', 'ji'),
    ('za', '\u305a', '\u30ba', 'zu'), ('za', '\u305c', '\u30bc', 'ze'),
    ('za', '\u305e', '\u30be', 'zo'),
    ('da', '\u3060', '\u30c0', 'da'), ('da', '\u3062', '\u30c2', 'ji'),
    ('da', '\u3065', '\u30c5', 'zu'), ('da', '\u3067', '\u30c7', 'de'),
    ('da', '\u3069', '\u30c9', 'do'),
    ('ba', '\u3070', '\u30d0', 'ba'), ('ba', '\u3073', '\u30d3', 'bi'),
    ('ba', '\u3076', '\u30d6', 'bu'), ('ba', '\u3079', '\u30d9', 'be'),
    ('ba', '\u307c', '\u30dc', 'bo'),
    ('pa', '\u3071', '\u30d1', 'pa'), ('pa', '\u3074', '\u30d4', 'pi'),
    ('pa', '\u3077', '\u30d7', 'pu'), ('pa', '\u307a', '\u30da', 'pe'),
    ('pa', '\u307d', '\u30dd', 'po'),
]
SETS = {'seion': SEION, 'dakuon': DAKUON, 'all': SEION + DAKUON}
DIRECTIONS = {
    'kana2roma': ('\u5e73\u5047\u540d', 'roma', '\u7f57\u9a6c\u97f3'),
    'roma2kana': ('\u7f57\u9a6c\u97f3', 'hira', '\u5e73\u5047\u540d'),
    'hira2kata': ('\u5e73\u5047\u540d', 'kata', '\u7247\u5047\u540d'),
    'kata2hira': ('\u7247\u5047\u540d', 'hira', '\u5e73\u5047\u540d'),
}
FIELD = {'hira': 1, 'kata': 2, 'roma': 3}
PASS_RATE = 90.0


def items_of(set_name, rows):
    data = SETS.get(set_name, SEION)
    if not rows:
        return list(data)
    keys = [r.strip().lower() for r in rows.replace('\uff0c', ',').split(',') if r.strip()]
    out = [x for x in data if x[0] in keys]
    return out


def prompt_of(item, direction):
    if direction not in DIRECTIONS:
        direction = 'kana2roma'
    key_field = DIRECTIONS[direction][1]
    prompt_field = 'roma' if key_field == 'hira' else ('hira' if key_field in ('kata', 'roma') else 'hira')
    if direction == 'kata2hira':
        prompt_field = 'kata'
    return item[FIELD[prompt_field]]


def key_of(item, direction):
    if direction not in DIRECTIONS:
        direction = 'kana2roma'
    return item[FIELD[DIRECTIONS[direction][1]]]


def build_quiz(items, direction):
    out = []
    for i, item in enumerate(items, 1):
        out.append({'no': i, 'row': item[0], 'prompt': prompt_of(item, direction),
                    'key': key_of(item, direction)})
    return out


def read_answers(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip() != '']


def grade(quiz, answers):
    rows = {}
    total = len(quiz)
    correct = 0
    detail = []
    for i, q in enumerate(quiz):
        ans = answers[i].strip().lower() if i < len(answers) else ''
        ok = (ans == q['key'].lower())
        if ok:
            correct += 1
        r = rows.setdefault(q['row'], {'total': 0, 'correct': 0})
        r['total'] += 1
        if ok:
            r['correct'] += 1
        detail.append({'no': q['no'], 'row': q['row'], 'prompt': q['prompt'],
                       'key': q['key'], 'answer': ans, 'ok': ok})
    rate = (correct * 100.0 / total) if total else 0.0
    row_stats = []
    weak = []
    for name in sorted(rows):
        r = rows[name]
        rr = r['correct'] * 100.0 / r['total']
        row_stats.append({'row': name, 'total': r['total'], 'correct': r['correct'],
                          'rate': round(rr, 1), 'pass': rr >= PASS_RATE})
        if rr < PASS_RATE:
            weak.append(name)
    return {'total': total, 'correct': correct, 'rate': round(rate, 1),
            'pass': rate >= PASS_RATE, 'row_stats': row_stats, 'weak': weak,
            'detail': detail}


def render_quiz_md(quiz, direction, set_name):
    lines = ['# \u4e94\u5341\u97f3\u9ed8\u5199\u6d4b\u9a8c', '']
    desc = DIRECTIONS.get(direction, DIRECTIONS['kana2roma'])
    lines.append('- \u8303\u56f4\uff1a%s' % ('\u6e05\u97f3' if set_name == 'seion'
                                             else ('\u6d4a\u97f3\u4e0e\u534a\u6d4a\u97f3' if set_name == 'dakuon' else '\u5168\u90e8')))
    lines.append('- \u65b9\u5411\uff1a\u7ed9%s\u5199%s' % (desc[0], desc[2]))
    lines.append('- \u9898\u6570\uff1a%d' % len(quiz))
    lines.append('')
    lines.append('| \u9898\u53f7 | \u884c | \u9898\u76ee | \u7b54\u6848 |')
    lines.append('|---|---|---|---|')
    for q in quiz:
        lines.append('| %d | %s | %s | |' % (q['no'], q['row'], q['prompt']))
    lines.append('')
    lines.append('> \u7f57\u9a6c\u97f3\u8f6c\u5199\u91c7\u7528\u5e38\u89c1\u65b9\u6848\uff08\u3057=shi\u3001\u3064=tsu\u3001\u3075=fu\uff09\uff0c\u5b9e\u9645\u53e3\u578b\u4ee5\u6559\u6750\u97f3\u9891\u4e0e\u6559\u5e08\u793a\u8303\u4e3a\u51c6\u3002')
    return '\n'.join(lines)


def render_grade_md(g, direction, set_name):
    desc = DIRECTIONS.get(direction, DIRECTIONS['kana2roma'])
    lines = ['# \u4e94\u5341\u97f3\u9ed8\u5199\u6279\u6539\u7ed3\u679c', '']
    lines.append('- \u65b9\u5411\uff1a\u7ed9%s\u5199%s' % (desc[0], desc[2]))
    lines.append('- \u9898\u6570\uff1a%d\uff0c\u7b54\u5bf9\uff1a%d' % (g['total'], g['correct']))
    lines.append('- \u6b63\u786e\u7387\uff1a**%.1f%%**\uff08\u8fbe\u6807\u7ebf %.0f%%\uff09' % (g['rate'], PASS_RATE))
    lines.append('- \u5224\u5b9a\uff1a**%s**' % ('\u8fbe\u6807' if g['pass'] else '\u672a\u8fbe\u6807'))
    lines.append('')
    lines.append('| \u9898\u53f7 | \u884c | \u9898\u76ee | \u6b63\u786e\u7b54\u6848 | \u4f60\u7684\u7b54\u6848 | \u5224\u5b9a |')
    lines.append('|---|---|---|---|---|---|')
    for d in g['detail']:
        lines.append('| %d | %s | %s | %s | %s | %s |'
                     % (d['no'], d['row'], d['prompt'], d['key'],
                        d['answer'] or '\u7a7a', '\u5bf9' if d['ok'] else '\u9519'))
    lines.append('')
    lines.append('## \u6309\u884c\u7edf\u8ba1')
    lines.append('')
    lines.append('| \u884c | \u9898\u6570 | \u7b54\u5bf9 | \u6b63\u786e\u7387 | \u662f\u5426\u8fbe\u6807 |')
    lines.append('|---|---|---|---|---|')
    for r in g['row_stats']:
        lines.append('| %s | %d | %d | %.1f%% | %s |'
                     % (r['row'], r['total'], r['correct'], r['rate'],
                        '\u662f' if r['pass'] else '\u5426'))
    lines.append('')
    if g['weak']:
        lines.append('## \u8584\u5f31\u884c\uff08\u660e\u65e5\u91cd\u9ed8\uff09')
        lines.append('')
        for w in g['weak']:
            lines.append('- %s \u884c' % w)
        lines.append('')
        lines.append('\u4e0d\u5230 %.0f%% \u7684\u884c\u4e0d\u8bb8\u5f80\u4e0b\u8d70\uff0c\u7b2c\u4e8c\u5929\u628a\u8fd9\u4e00\u884c\u4e0e\u65b0\u884c\u4e00\u8d77\u9ed8\u5199\u3002' % PASS_RATE)
        lines.append('')
    else:
        lines.append('## \u6309\u884c\u5168\u90e8\u8fbe\u6807')
        lines.append('')
        lines.append('-\u53ef\u4ee5\u8fdb\u5165\u4e0b\u4e00\u884c\uff0c\u5e76\u628a\u5df2\u8fbe\u6807\u7684\u884c\u653e\u8fdb\u590d\u4e60\u95f4\u9694\u5e8f\u5217\u3002')
        lines.append('')
    lines.append('> \u7f57\u9a6c\u97f3\u8f6c\u5199\u53ea\u662f\u8f85\u52a9\uff0c\u5b9e\u9645\u53d1\u97f3\u4ee5\u6559\u6750\u97f3\u9891\u4e0e\u6559\u5e08\u793a\u8303\u4e3a\u51c6\u3002')
    return '\n'.join(lines)


def default_out(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def selftest():
    errors = []

    def eq(name, got, want):
        if got != want:
            errors.append('%s: got=%r want=%r' % (name, got, want))

    def ok(name, cond):
        if not cond:
            errors.append('%s: condition failed' % name)

    eq('case01 \u6e05\u97f3\u603b\u6570 46', len(SEION), 46)
    eq('case02 \u6d4a\u97f3\u4e0e\u534a\u6d4a\u97f3\u603b\u6570 25', len(DAKUON), 25)
    eq('case03 \u5168\u90e8\u5408\u8ba1 71', len(SETS['all']), 71)
    eq('case04 \u6307\u5b9a a \u884c 5 \u9898', len(items_of('seion', 'a')), 5)
    eq('case05 \u6307\u5b9a a,ka \u884c 10 \u9898', len(items_of('seion', 'a,ka')), 10)
    eq('case06 ya \u884c 3 \u9898', len(items_of('seion', 'ya')), 3)
    eq('case07 pa \u884c 5 \u9898', len(items_of('dakuon', 'pa')), 5)
    q1 = build_quiz(items_of('seion', 'a'), 'kana2roma')
    eq('case08 kana2roma \u63d0\u793a\u4e3a\u5e73\u5047\u540d', q1[0]['prompt'], '\u3042')
    eq('case09 kana2roma \u7b54\u6848\u4e3a\u7f57\u9a6c\u97f3', q1[0]['key'], 'a')
    q2 = build_quiz(items_of('seion', 'sa'), 'roma2kana')
    eq('case10 roma2kana \u7d2b\u884c\u7b54\u6848', q2[1]['key'], '\u3057')
    eq('case11 roma2kana \u63d0\u793a\u4e3a shi', q2[1]['prompt'], 'shi')
    q3 = build_quiz(items_of('seion', 'ka'), 'hira2kata')
    eq('case12 hira2kata \u7b54\u6848\u4e3a\u7247\u5047\u540d', q3[0]['key'], '\u30ab')
    q4 = build_quiz(items_of('seion', 'ka'), 'kata2hira')
    eq('case13 kata2hira \u63d0\u793a\u4e3a\u7247\u5047\u540d', q4[0]['prompt'], '\u30ab')
    eq('case14 kata2hira \u7b54\u6848\u4e3a\u5e73\u5047\u540d', q4[0]['key'], '\u304b')
    g1 = grade(q1, ['a', 'i', 'u', 'e', 'o'])
    eq('case15 \u5168\u5bf9\u6b63\u786e\u7387 100', g1['rate'], 100.0)
    eq('case16 \u5168\u5bf9\u5224\u5b9a\u8fbe\u6807', g1['pass'], True)
    eq('case17 \u5168\u5bf9\u65e0\u8584\u5f31\u884c', g1['weak'], [])
    g2 = grade(q1, ['a', 'i', 'x', 'e', 'o'])
    eq('case18 \u9519\u4e00\u9898\u6b63\u786e\u7387 80', g2['rate'], 80.0)
    eq('case19 \u672a\u8fbe\u6807\u5217\u5165\u8584\u5f31\u884c', g2['weak'], ['a'])
    g3 = grade(q1, ['A', 'I', 'U', 'E', 'O'])
    eq('case20 \u5927\u5c0f\u5199\u4e0d\u654f\u611f', g3['rate'], 100.0)
    g4 = grade(q1, [])
    eq('case21 \u7a7a\u7b54\u6848\u6b63\u786e\u7387 0', g4['rate'], 0.0)
    g5 = grade(build_quiz(items_of('seion', 'a,ka'), 'kana2roma'),
               ['a', 'i', 'u', 'e', 'o', 'ka', 'ki', 'ku', 'ke', 'ko'])
    eq('case22 \u591a\u884c\u7edf\u8ba1\u884c\u6570', len(g5['row_stats']), 2)
    g6 = grade(build_quiz(items_of('seion', 'a,ka'), 'kana2roma'),
               ['a', 'i', 'u', 'e', 'o', 'ka', 'x', 'x', 'ke', 'ko'])
    eq('case23 \u53ea\u5217\u51fa\u672a\u8fbe\u6807\u884c', g6['weak'], ['ka'])
    eq('case24 \u6309\u884c\u6b63\u786e\u7387 60', g6['row_stats'][1]['rate'], 60.0)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(out_dir, '_selftest_result.txt')
    if errors:
        msg = 'SELFTEST FAIL\n' + '\n'.join(errors)
    else:
        msg = ('SELFTEST OK\n\u65ad\u8a00\u6570: 24\n\u8986\u76d6: \u6e05\u97f3\u4e0e\u6d4a\u97f3\u6570\u91cf/\u6309\u884c\u7b5b\u9009/'
               '\u56db\u79cd\u51fa\u9898\u65b9\u5411/\u6b63\u786e\u7387\u4e0e\u8fbe\u6807\u5224\u5b9a/\u5927\u5c0f\u5199/\u7a7a\u7b54\u6848/\u8584\u5f31\u884c\u5b9a\u4f4d')
    with open(res_path, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser(description='\u65e5\u8bed\u4e94\u5341\u97f3\u9ed8\u5199\u51fa\u9898\u4e0e\u6279\u6539')
    ap.add_argument('--mode', default='quiz', choices=['quiz', 'grade'])
    ap.add_argument('--set', dest='set_name', default='seion',
                    choices=['seion', 'dakuon', 'all'])
    ap.add_argument('--rows', help='\u6307\u5b9a\u884c\uff0c\u9017\u53f7\u5206\u9694')
    ap.add_argument('--direction', default='kana2roma',
                    choices=['kana2roma', 'roma2kana', 'hira2kata', 'kata2hira'])
    ap.add_argument('--file', help='\u6279\u6539\u6a21\u5f0f\u7684\u7b54\u6848\u6587\u4ef6')
    ap.add_argument('--out', help='\u8f93\u51fa\u6587\u4ef6\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true', help='\u8fd0\u884c\u5185\u7f6e\u81ea\u68c0')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    items = items_of(args.set_name, args.rows)
    quiz = build_quiz(items, args.direction)
    if args.mode == 'quiz':
        out = render_quiz_md(quiz, args.direction, args.set_name)
        default = default_out('_gojuon_quiz.md')
    else:
        answers = read_answers(args.file)
        g = grade(quiz, answers)
        out = render_grade_md(g, args.direction, args.set_name)
        if args.format == 'json':
            out = json.dumps(g, ensure_ascii=False, indent=2)
        default = default_out('_gojuon_result.md')
    path = args.out or default
    with open(path, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
