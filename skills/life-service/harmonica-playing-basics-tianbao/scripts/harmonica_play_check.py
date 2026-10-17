# -*- coding: utf-8 -*-
"""\u53e3\u7434\u5439\u594f\u57fa\u7840\u6838\u67e5\uff1aC \u8c03\u5341\u5b54\u53e3\u7434\u5439/\u5438\u97f3\u5b54\u5bf9\u7167\u3001\u65cb\u5f8b\u9010\u6b65\u97f3\u5b54\u4e0e\u5439\u5438\u4e00\u81f4\u6027\u6838\u67e5\u3001\u5355\u97f3\u4e0e\u6c14\u606f\u57fa\u7840\u63d0\u793a\u3002

\u7528\u6cd5:
  python harmonica_play_check.py --file melody.json [--out result.md] [--format json]
  python harmonica_play_check.py --selftest
"""
import argparse
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# C \u8c03\u5341\u5b54\u53e3\u7434\uff1a\u5b54\u53f7 -> \u5439/\u5438 \u97f3\u540d
BLOW = {1: 'C4', 2: 'E4', 3: 'G4', 4: 'C5', 5: 'E5', 6: 'G5', 7: 'C6', 8: 'E6', 9: 'G6', 10: 'C7'}
DRAW = {1: 'D4', 2: 'G4', 3: 'B4', 4: 'D5', 5: 'F5', 6: 'A5', 7: 'B5', 8: 'D6', 9: 'F6', 10: 'A6'}

NOTE_MIDI = {
    'C4': 60, 'D4': 62, 'E4': 64, 'F4': 65, 'G4': 67, 'A4': 69, 'B4': 71,
    'C5': 72, 'D5': 74, 'E5': 76, 'F5': 77, 'G5': 79, 'A5': 81, 'B5': 83,
    'C6': 84, 'D6': 86, 'E6': 88, 'F6': 89, 'G6': 91, 'A6': 93,     'C7': 96,
}


def norm(s):
    return str(s or '').strip().lower().replace(' ', '')




NOTE_MIDI_N = {norm(k): v for k, v in NOTE_MIDI.items()}


def freq_of(note):
    m = NOTE_MIDI_N.get(norm(note))
    if m is None:
        return None
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


def note_at(hole, breath):
    """\u8fd4\u56de\u8be5\u5b54\u8be5\u5439\u5438\u65b9\u5f0f\u5bf9\u5e94\u7684\u97f3\u540d\uff0c\u65e0\u6548\u8fd4\u56de None\u3002"""
    if not isinstance(hole, int):
        try:
            hole = int(hole)
        except (TypeError, ValueError):
            return None
    if hole not in BLOW:
        return None
    b = norm(breath)
    if b == 'blow' or b == '\u5439':
        return BLOW[hole]
    if b == 'draw' or b == '\u5438':
        return DRAW[hole]
    return None


def step_check(step):
    """\u5355\u6b65\u6838\u67e5\u3002step: {'hole': 1, 'breath': 'blow', 'note': 'C4'}\u3002"""
    if not isinstance(step, dict):
        raise ValueError('sequence \u7684\u6bcf\u4e00\u9879\u5fc5\u987b\u662f\u5bf9\u8c61')
    hole = step.get('hole')
    breath = step.get('breath')
    note = norm(step.get('note'))
    if hole is None or breath is None or not note:
        raise ValueError('\u6bcf\u4e00\u6b65\u9700\u8981 hole / breath / note')
    want = note_at(hole, breath)
    if want is None:
        # \u533a\u5206\uff1a\u5b54\u65e0\u6548 vs \u5439\u5438\u65b9\u5f0f\u65e0\u6548
        try:
            h = int(hole)
        except (TypeError, ValueError):
            h = None
        if h not in BLOW:
            return {'ok': False, 'sev': 3, 'hole': hole, 'breath': breath, 'note': note,
                    'detail': '\u5b54 %s \u65e0\u6548\uff08\u5e94\u4e3a 1 \u5230 10\uff09' % hole,
                    'correct': None, 'why': '\u5b54\u53f7\u8d85\u51fa\u5341\u5b54\u8303\u56f4\uff0c\u65e0\u6cd5\u53d1\u58f0'}
        return {'ok': False, 'sev': 3, 'hole': hole, 'breath': breath, 'note': note,
                'detail': '\u5b54 %s \u7684\u5439\u5438\u65b9\u5f0f\u300c%s\u300d\u65e0\u6548\uff08\u5e94\u4e3a blow \u6216 draw\uff09' % (hole, breath),
                'correct': None, 'why': '\u5439\u5438\u65b9\u5f0f\u5199\u9519\uff0c\u811a\u672c\u65e0\u6cd5\u5224\u5b9a\u97f3'}
    if norm(want) != note:
        # \u7ed9\u51fa\u6b63\u786e\u5b54\uff1a\u627e blow/draw \u7b49\u4e8e note \u7684\u5b54
        correct = find_hole(note)
        return {'ok': False, 'sev': 2, 'hole': hole, 'breath': breath, 'note': note,
                'detail': '%s \u5b54%s \u5e94\u4e3a %s\uff0c\u5b9e\u4e3a %s'
                % (hole, breath, want, note),
                'correct': correct,
                'why': '\u5b54\u6216\u5439\u5438\u5f04\u9519\uff0c\u5439\u51fa\u6765\u5c31\u662f\u522b\u7684\u97f3\uff1b\u6b63\u786e\u5e94\u4e3a %s' % correct}
    return {'ok': True, 'sev': 0, 'hole': hole, 'breath': breath, 'note': note,
            'detail': '', 'correct': None, 'why': ''}


def find_hole(note):
    """\u8fd4\u56de\u300c\u5b54 \u5439/\u5438\u300d\u5b57\u7b26\u4e32\uff0c\u627e\u4e0d\u5230\u8fd4\u56de None\u3002\u6309\u97f3\u540d\uff08\u5ffd\u7565\u516b\u5ea6\uff09\u5339\u914d\u6700\u4f4e\u97f3\u5b54\u3002"""
    n = norm(note).rstrip('0123456789')
    for h in range(1, 11):
        if norm(BLOW[h]).rstrip('0123456789') == n:
            return '%d \u5b54\u5439' % h
        if norm(DRAW[h]).rstrip('0123456789') == n:
            return '%d \u5b54\u5438' % h
    return None


def calc(data):
    seq = data.get('sequence')
    if seq is None:
        raise ValueError('\u8f93\u5165\u7f3a\u5c11 sequence \u5217\u8868')
    if not isinstance(seq, list) or not seq:
        raise ValueError('sequence \u5fc5\u987b\u662f\u975e\u7a7a\u5217\u8868')
    steps = [step_check(s) for s in seq]
    issues = []
    for i, st in enumerate(steps):
        if not st['ok']:
            issues.append({'sev': st['sev'], 'item': '\u7b2c %d \u6b65' % (i + 1),
                           'detail': st['detail'],
                           'why': st['why'], 'correct': st.get('correct')})
    issues.sort(key=lambda r: -r['sev'])
    n_err = len([s for s in steps if not s['ok']])
    if any(i['sev'] == 3 for i in issues):
        level = '\u6709\u660e\u663e\u95ee\u9898'
    elif n_err:
        level = '\u6709\u5439\u594f\u9519\u8bef'
    else:
        level = '\u5408\u683c'
    return {'level': level, 'steps': steps, 'issues': issues,
            'n_err': n_err, 'blow': BLOW, 'draw': DRAW}


def render_md(r):
    L = []
    L.append('# \u53e3\u7434\u5439\u594f\u6838\u67e5')
    L.append('')
    L.append('## \u4e00\u3001\u603b\u4f53\u5224\u5b9a')
    L.append('')
    L.append('**%s**' % r['level'])
    L.append('')
    L.append('## \u4e8c\u3001\u9010\u97f3\u5b54\u5224\u5b9a')
    L.append('')
    L.append('| \u6b65 | \u5b54 | \u5439\u5438 | \u76ee\u6807\u97f3 | \u7ed3\u679c |')
    L.append('|---|---|---|---|---|')
    for i, st in enumerate(r['steps']):
        L.append('| %d | %s | %s | %s | %s |'
                 % (i + 1, st.get('hole'), st.get('breath'), st.get('note'),
                    '\u6b63\u786e' if st['ok'] else '\u9519\u8bef'))
    L.append('')
    if r['issues']:
        L.append('## \u4e09\u3001\u9519\u8bef\u4e0e\u6574\u6539')
        L.append('')
        L.append('| \u4e25\u91cd\u5ea6 | \u6b65\u9aa4 | \u95ee\u9898 | \u4e3a\u4ec0\u4e48\u8981\u5728\u610f |')
        L.append('|---|---|---|---|')
        for it in r['issues']:
            L.append('| %s | %s | %s | %s |'
                     % ('\u4e25\u91cd' if it['sev'] == 3 else '\u53ef\u6539\u8fdb', it['item'], it['detail'], it['why']))
        L.append('')
    L.append('## \u56db\u3001\u4eba\u5de5\u786e\u8ba4\u6e05\u5355')
    L.append('')
    L.append('- [ ] \u5df2\u80cc\u4e0b\u5341\u5b54\u5439\u5438\u5bf9\u7167')
    L.append('- [ ] \u5355\u97f3\u80fd\u5439\u5e72\u51c0\u4e0d\u7834\u97f3')
    L.append('- [ ] \u5439\u5438\u7528\u8179\u90e8\u6c14\u606f\u4e0d\u9f13\u816e')
    L.append('- [ ] \u5c0f\u661f\u661f\u80fd\u9010\u5b54\u627e\u51c6')
    return '\n'.join(L)


def selftest():
    errs = []
    n = 0

    def ck(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            errs.append(msg)

    # 1 \u5439\u97f3\u9891\u7387
    ck(abs(freq_of('C4') - 261.63) < 0.01, 'C4 \u5e94\u4e3a 261.63')
    ck(abs(freq_of('E4') - 329.63) < 0.01, 'E4 \u5e94\u4e3a 329.63')
    ck(abs(freq_of('G4') - 392.00) < 0.01, 'G4 \u5e94\u4e3a 392.00')
    ck(abs(freq_of('C5') - 523.25) < 0.01, 'C5 \u5e94\u4e3a 523.25')
    ck(abs(freq_of('C7') - 2093.0) < 0.01, 'C7 \u5e94\u4e3a 2093.00')

    # 2 \u5438\u97f3\u9891\u7387
    ck(abs(freq_of('D4') - 293.66) < 0.01, 'D4 \u5e94\u4e3a 293.66')
    ck(abs(freq_of('B4') - 493.88) < 0.01, 'B4 \u5e94\u4e3a 493.88')
    ck(abs(freq_of('F5') - 698.46) < 0.01, 'F5 \u5e94\u4e3a 698.46')
    ck(abs(freq_of('A5') - 880.00) < 0.01, 'A5 \u5e94\u4e3a 880.00')

    # 3 note_at \u5bf9\u7167
    ck(note_at(1, 'blow') == 'C4', '1\u5b54\u5439\u5e94\u4e3a C4')
    ck(note_at(1, 'draw') == 'D4', '1\u5b54\u5438\u5e94\u4e3a D4')
    ck(note_at(7, 'blow') == 'C6', '7\u5b54\u5439\u5e94\u4e3a C6')
    ck(note_at(6, 'draw') == 'A5', '6\u5b54\u5438\u5e94\u4e3a A5')
    ck(note_at(11, 'blow') is None, '11\u5b54\u5e94\u65e0\u6548')
    ck(note_at(1, 'both') is None, 'both \u5439\u5438\u5e94\u65e0\u6548')

    # 4 \u5168\u6b63\u786e\u6b63\u4f8b
    seq_ok = [{'hole': 1, 'breath': 'blow', 'note': 'C4'},
              {'hole': 6, 'breath': 'blow', 'note': 'G5'},
              {'hole': 6, 'breath': 'draw', 'note': 'A5'}]
    r4 = calc({'sequence': seq_ok})
    ck(r4['level'] == '\u5408\u683c', '\u5168\u6b63\u786e\u5e94\u5408\u683c\uff0c\u5b9e\u4e3a %s' % r4['level'])
    ck(r4['n_err'] == 0, '\u5168\u6b63\u786e\u5e94 0 \u9519')

    # 5 \u53cd\u4f8b\uff1a1\u5b54\u5439\u8bf4\u6210 D4\uff08\u5439\u5438\u53cd\u4e86\uff09
    r5 = calc({'sequence': [{'hole': 1, 'breath': 'blow', 'note': 'D4'}]})
    ck(r5['level'] == '\u6709\u5439\u594f\u9519\u8bef', '1\u5b54\u5439D4\u5e94\u5224\u9519\u8bef\uff0c\u5b9e\u4e3a %s' % r5['level'])
    ck(r5['issues'][0]['detail'].find('C4') >= 0, '\u5e94\u7ed9\u51fa\u6b63\u786e\u97f3 C4\uff0c\u5b9e\u4e3a %s' % r5['issues'][0]['detail'])
    ck(r5['issues'][0]['correct'] == '1 \u5b54\u5438', '\u5e94\u6307\u51fa 1 \u5b54\u5438\uff0c\u5b9e\u4e3a %s' % r5['issues'][0]['correct'])

    # 6 \u53cd\u4f8b\uff1a4\u5b54\u5439\u8bf4\u6210 E4\uff08\u5b54\u9519\uff09
    r6 = calc({'sequence': [{'hole': 4, 'breath': 'blow', 'note': 'E4'}]})
    ck(any(i['item'] == '\u7b2c 1 \u6b65' for i in r6['issues']), '\u5e94\u6807\u8bb0\u7b2c1\u6b65')
    ck(r6['issues'][0]['correct'].find('2 \u5b54') >= 0, '\u5e94\u6307\u51fa 2 \u5b54\u5439\uff0c\u5b9e\u4e3a %s' % r6['issues'][0]['correct'])

    # 7 \u53cd\u4f8b\uff1a\u65e0\u6548\u5b54\u53f7
    r7 = calc({'sequence': [{'hole': 11, 'breath': 'blow', 'note': 'C4'}]})
    ck(r7['level'] == '\u6709\u660e\u663e\u95ee\u9898', '\u65e0\u6548\u5b54\u5e94\u5224\u4e25\u91cd\uff0c\u5b9e\u4e3a %s' % r7['level'])
    ck(r7['issues'][0]['sev'] == 3, '\u65e0\u6548\u5b54\u5e94 sev3')

    # 8 \u53cd\u4f8b\uff1a\u591a\u6b65\u9519\u8bef\u90fd\u62a5\u51fa
    r8 = calc({'sequence': [{'hole': 1, 'breath': 'blow', 'note': 'D4'},
                            {'hole': 4, 'breath': 'blow', 'note': 'E4'}]})
    ck(r8['n_err'] == 2, '\u5e94\u62a5 2 \u4e2a\u9519\uff0c\u5b9e\u4e3a %d' % r8['n_err'])

    # 9 \u5c0f\u661f\u661f\u6620\u5c04
    star = ['C4', 'C4', 'G4', 'G4', 'A4', 'A4', 'G4', 'F4', 'F4', 'E4', 'E4', 'D4', 'D4', 'C4']
    mapped = [find_hole(s) for s in star]
    ck(mapped[0] == '1 \u5b54\u5439', '\u5c0f\u661f\u661f\u9996\u97f3\u5e94\u4e3a 1 \u5b54\u5439\uff0c\u5b9e\u4e3a %s' % mapped[0])
    ck(mapped[6] == '2 \u5b54\u5438', '\u5c0f\u661f\u661f\u7b2c7\u97f3 G \u5e94\u4e3a\u6700\u4f4e\u6709\u6548\u5b54 2 \u5b54\u5438\uff0c\u5b9e\u4e3a %s' % mapped[6])
    ck(all(m is not None for m in mapped), '\u5c0f\u661f\u661f\u6240\u6709\u97f3\u90fd\u5e94\u80fd\u5728\u7434\u4e0a\u627e\u5230')

    # 10 \u5224\u5b9a\u987a\u5e8f\uff1a\u65e0\u6548\u5b54\u4e0d\u5e94\u56e0\u4fe1\u606f\u5b8c\u6574\u5224\u8f7b
    r10 = calc({'sequence': [{'hole': 11, 'breath': 'blow', 'note': 'C4'}]})
    ck(r10['level'] == '\u6709\u660e\u663e\u95ee\u9898', '\u65e0\u6548\u5b54\u4e0d\u5e94\u5224\u8f7b\uff0c\u5b9e\u4e3a %s' % r10['level'])

    # 11 \u975e\u6cd5\u8f93\u5165
    for bad, why in (
        ({}, '\u7f3a sequence'),
        ({'sequence': []}, 'sequence \u7a7a'),
        ({'sequence': [{'hole': 1}]}, '\u7f3a breath/note'),
        ({'sequence': [{'hole': 1, 'breath': 'blow'}]}, '\u7f3a note'),
        ({'sequence': 'x'}, 'sequence \u975e\u5217\u8868'),
    ):
        try:
            calc(bad)
            ck(False, '\u7528\u4f8b11 %s \u5e94\u629b\u9519' % why)
        except ValueError:
            ck(True, '')

    # 12 BOM \u4e24\u6761\u8def\u5f84
    bom = '\ufeff' + json.dumps({'sequence': [{'hole': 1, 'breath': 'blow', 'note': 'D4'}]})
    r12 = calc(json.loads(bom.lstrip('\ufeff')))
    ck(r12['level'] == '\u6709\u5439\u594f\u9519\u8bef', 'BOM \u5b57\u7b26\u4e32\u5e94\u89e3\u6790\uff0c\u5b9e\u4e3a %s' % r12['level'])
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bom_probe_h.json')
    with open(tmp, 'w', encoding='utf-8-sig') as f:
        f.write(json.dumps({'sequence': [{'hole': 4, 'breath': 'blow', 'note': 'E4'}]}))
    try:
        r12b = calc(json.loads(open(tmp, 'r', encoding='utf-8-sig').read()))
        ck(r12b['n_err'] == 1, 'BOM \u6587\u4ef6\u5e94\u89e3\u6790\u51fa 1 \u4e2a\u9519\uff0c\u5b9e\u4e3a %s' % r12b['n_err'])
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 13 \u8f93\u51fa\u7ed3\u6784
    md = render_md(r5)
    for key in ('\u603b\u4f53\u5224\u5b9a', '\u9010\u97f3\u5b54\u5224\u5b9a', '\u9519\u8bef\u4e0e\u6574\u6539', '\u4eba\u5de5\u786e\u8ba4\u6e05\u5355'):
        ck(key in md, 'Markdown \u5e94\u542b\u7ae0\u8282 %s' % key)
    ck(len(BLOW) == 10 and len(DRAW) == 10, '\u5439\u5438\u5e94\u5404 10 \u4e2a\u97f3')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selftest_result.txt')
    msg = 'SELFTEST FAIL\n' + '\n'.join(errs) if errs else (
        'SELFTEST OK\n\u65ad\u8a00\u6570: %d\n\u8986\u76d6: \u5439/\u5438\u97f3\u9891\u7387/\u5341\u5b54\u5bf9\u7167/\u5168\u6b63\u786e\u6b63\u4f8b/'
        '1\u5b54\u5439\u53cd\u4f8b/4\u5b54\u9519\u5b54\u53cd\u4f8b/\u65e0\u6548\u5b54\u53cd\u4f8b/\u591a\u6b65\u9519\u8bef/\u5c0f\u661f\u661f\u6620\u5c04/\u5224\u5b9a\u987a\u5e8f/'
        '\u975e\u6cd5\u8f93\u5165/BOM\u4e24\u6761\u8def\u5f84/\u8f93\u51fa\u7ed3\u6784' % n)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)
    return 0 if not errs else 1


def main():
    ap = argparse.ArgumentParser(description='\u53e3\u7434\u5439\u594f\u57fa\u7840\u6838\u67e5')
    ap.add_argument('--file', help='\u8f93\u5165 JSON \u6587\u4ef6')
    ap.add_argument('--text', help='\u8f93\u5165 JSON \u5b57\u7b26\u4e32')
    ap.add_argument('--out', help='\u7ed3\u679c\u8f93\u51fa\u8def\u5f84')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    raw = a.text or ''
    if a.file:
        if not os.path.exists(a.file):
            print('ERROR --file \u4e0d\u5b58\u5728: %s' % a.file)
            return 2
        raw = open(a.file, 'r', encoding='utf-8-sig', errors='replace').read()
    if not raw.strip():
        print('ERROR \u9700\u8981 --file \u6216 --text')
        return 2
    try:
        data = json.loads(raw.lstrip('\ufeff'))
    except ValueError as e:
        print('ERROR JSON \u89e3\u6790\u5931\u8d25: %s' % e)
        return 2
    try:
        r = calc(data)
    except ValueError as e:
        print('ERROR %s' % e)
        return 2

    out = render_md(r) if a.format == 'md' else json.dumps(r, ensure_ascii=False, indent=2)
    d = os.path.dirname(os.path.abspath(__file__))
    target = a.out or os.path.join(d, '_last_result.txt')
    with open(target, 'w', encoding='utf-8') as f:
        f.write(out + '\n')
    print('\u7ed3\u679c\u5df2\u5199\u5165: %s' % target)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())





