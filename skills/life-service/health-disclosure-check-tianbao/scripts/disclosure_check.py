# -*- coding: utf-8 -*-
"""Health disclosure questionnaire cross-check helper.

Structurally compares each questionnaire item against the facts supplied and
flags items that need attention. It gives no medical opinion, no diagnosis,
no underwriting promise and no claim promise.

Usage:
  python disclosure_check.py --file case.json [--out result.md] [--format json]
  python disclosure_check.py --selftest
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Chinese keywords use \\uXXXX escapes so the source stays ASCII.
K_TIJIAN = '\u4f53\u68c0'                 # physical exam
K_YICHANG = '\u5f02\u5e38'                 # abnormal
K_ZHEN = '\u8bca\u65ad'                       # diagnosis
K_ZHENDUAN = '\u786e\u8bca'              # confirmed diagnosis
K_JIUZHEN = '\u8bca\u7597'                       # medical care
K_MENZHEN = '\u95e8\u8bca'                 # outpatient
K_ZHUYUAN = '\u4f4f\u9662'                 # hospital stay
K_SHUSHOU = '\u624b\u672f'                       # surgery
K_YONGYAO = '\u7528\u836f'                 # medication
K_SUIZHEN = '\u968f\u8bbf'                 # follow-up visit
K_ZHENGZHUANG = '\u75c7\u72b6'        # symptom
K_JIATING = '\u5bb6\u5ead'                 # family
K_WUXING = '\u65e0\u75c5'                       # no illness
FOU = '\u5426'                                        # no

FACTS_TRIGGER = {
    'EXAM_ABNORMAL': [K_TIJIAN, K_YICHANG, K_ZHENGZHUANG],
    'DIAGNOSED': [K_ZHEN, K_ZHENDUAN],
    'TREATMENT': [K_JIUZHEN, K_MENZHEN, K_ZHUYUAN, K_SHUSHOU, K_YONGYAO,
                  K_SUIZHEN],
    'FAMILY': [K_JIATING],
}

DETAIL_HINTS = [K_TIJIAN, K_ZHEN, K_ZHENDUAN, K_ZHUYUAN, K_SHUSHOU,
                K_MENZHEN, K_YONGYAO, K_SUIZHEN, K_ZHENGZHUANG]

UNDERWRITING = [
    ('STANDARD', 'Standard terms: covered at the standard rate with no added '
                 'condition.'),
    ('LOADED', 'Loaded premium: covered at a rate above the standard. The '
               'premium goes up; sum insured and cover follow the contract.'),
    ('EXCLUSION', 'Exclusion: covered, but the cause concerned is excluded '
                  'from the benefit. Other responsibilities are still covered '
                  'as agreed. Confirm WHICH item is excluded.'),
    ('DEFERRED', 'Deferred: no conclusion yet. More documents or an '
                 'observation period may be needed; follow the insurer.'),
    ('DECLINED', 'Declined: not covered. You may assess other products, but '
                 'changing the answers to get through is not acceptable.'),
]

GUIDANCE = [
    ('EXAM_ABNORMAL',
     'Report that an abnormality WAS FOUND in an examination, with the item '
     'and the date. Do NOT answer no. Do NOT upgrade it into a confirmed '
     'diagnosis either.'),
    ('DIAGNOSED',
     'Report the confirmed diagnosis as it is, with the date. Having recovered '
     'does not change the fact that it happened. Whether it falls inside the '
     'asked time range follows the questionnaire wording.'),
    ('TREATMENT',
     'Report consultations, hospital stays, surgery, medication and follow-up '
     'advice as they happened. A doctor saying follow up is not the same as '
     'no abnormality, and not the same as a confirmed diagnosis.'),
    ('FAMILY',
     'Answer according to what the questionnaire actually asks about family '
     'history.'),
]


def calc(data):
    questions = data.get('questions', []) or []
    facts = data.get('facts', []) or []
    corrected = bool(data.get('corrected_after_submission', False))

    rows = []
    flags = []
    for i, q in enumerate(questions):
        qid = str(q.get('id', 'Q%d' % (i + 1)))
        qtext = str(q.get('text', ''))
        answer = str(q.get('answer', ''))
        detail = str(q.get('detail', '') or '')
        if not qtext.strip():
            raise ValueError('question %s has empty text' % qid)
        ans_norm = answer.replace(K_WUXING, '').strip()
        answered_no = answer.strip() in (FOU, FOU + '\u3002')
        answered_yes = answer.strip() in ('\u662f', '\u662f\u3002')

        triggers = []
        for f in facts:
            ftype = str(f.get('type', '')).upper()
            item = str(f.get('item', ''))
            fdate = str(f.get('date', ''))
            cat = FACTS_TRIGGER.get(ftype)
            if not cat:
                raise ValueError('unknown fact type: %s' % ftype)
            if answered_no and (item in qtext or any(k in qtext for k in cat)):
                triggers.append({'fact_type': ftype, 'item': item,
                                 'date': fdate})
            elif answered_yes and item in qtext:
                triggers.append({'fact_type': ftype, 'item': item,
                                 'date': fdate})

        needs_detail = answered_yes and bool(
            any(k in qtext for k in DETAIL_HINTS)) and not detail.strip()

        if triggers and answered_no:
            status = 'ANSWERED_NO_BUT_FACT_FOUND'
        elif needs_detail:
            status = 'ANSWERED_YES_WITHOUT_DETAIL'
        elif answered_no:
            status = 'ANSWERED_NO'
        elif answered_yes:
            status = 'ANSWERED_YES'
        elif answer.strip() == '':
            status = 'UNANSWERED'
        else:
            status = 'ANSWERED_OTHER'

        rows.append({
            'id': qid,
            'text': qtext,
            'answer': answer,
            'detail': detail,
            'status': status,
            'matching_facts': triggers,
            'needs_detail': needs_detail,
            'answer_norm_len': len(ans_norm),
        })
        if status in ('ANSWERED_NO_BUT_FACT_FOUND', 'ANSWERED_YES_WITHOUT_DETAIL',
                      'UNANSWERED'):
            flags.append(qid)

    notes = []
    notes.append('Answer what was asked. Every question on the questionnaire '
                 'must be answered according to the actual situation.')
    notes.append('The scope of the disclosure duty is what the insurance '
                 'contract asks in the questionnaire. Items that were not '
                 'asked are handled according to the contract wording and the '
                 'law in force; do not assume "not asked means never say".')
    notes.append('"Not serious" is a judgement, not a medical conclusion. A '
                 'judgement cannot replace an honest answer.')
    notes.append('Having recovered does not change the fact that it happened. '
                 'Whether it falls inside the asked time range follows the '
                 'questionnaire wording.')
    notes.append('Each person answers their own questionnaire. A family member '
                 'cannot answer for somebody else.')
    if corrected:
        notes.append('A correction was reported after submission. Report it '
                     'through the insurer channel promptly; a silent gap is '
                     'riskier than an early correction.')
    notes.append('A missed item should be corrected through the insurer '
                 'channel as early as possible. Do NOT change answers to get '
                 'a better underwriting result.')
    notes.append('Undisclosed facts may lead the insurer to decline to pay the '
                 'benefit and possibly to terminate the contract, under the '
                 'contract wording and the law in force. Whether a case counts '
                 'as non-disclosure is decided by the insurer. Do NOT state '
                 'that non-disclosure always means refusal.')
    notes.append('Honest disclosure is an obligation, not a pass ticket: even '
                 'after honest disclosure the result may be loaded, an '
                 'exclusion, deferred or declined.')
    notes.append('An exclusion applies to the excluded item only. It does NOT '
                 'mean the whole policy is void, but you MUST confirm which '
                 'item is excluded.')
    notes.append('This script gives no medical opinion, no diagnosis, no '
                 'underwriting promise and no claim promise.')

    return {
        'question_count': len(rows),
        'fact_count': len(facts),
        'corrected_after_submission': corrected,
        'rows': rows,
        'flagged_ids': flags,
        'flagged_count': len(flags),
        'guidance': GUIDANCE,
        'underwriting_types': UNDERWRITING,
        'correction_flow': [
            'obtain the underwriting conclusion notice and compare it item by '
            'item against what was declared',
            'if something does not match, request a correction or review in '
            'writing through the insurer channel',
            'keep the application form, the questionnaire, the submission '
            'record, the underwriting notice and all communications',
            'if declined or disputed, use the formal review and complaint '
            'channels',
        ],
        'notes': notes,
        'must_confirm': [
            'the original questionnaire, not a verbal summary from sales',
            'every question copied verbatim, without abbreviations',
            'each answer compared against actual medical records',
            'recent physical exam reports and outpatient records checked item '
            'by item, not from memory',
            'exam abnormality, outpatient record and confirmed diagnosis kept '
            'as three separate categories',
            'detail fields completed where the questionnaire asks for them',
            'the time range taken from the questionnaire wording',
            'the underwriting conclusion notice compared with what was declared',
            'if the result is an exclusion, which specific item is excluded',
            'if loaded, the rate change and what the rest of the cover is',
            'if deferred, what documents and observation conditions apply',
            'all documents kept: application form, questionnaire, submission '
            'record, underwriting notice, communications',
        ],
    }


def to_md(r):
    L = []
    L.append('# Health Disclosure Cross-check')
    L.append('')
    L.append('- Questions read: %d' % r['question_count'])
    L.append('- Facts supplied: %d' % r['fact_count'])
    L.append('- Correction reported after submission: %s'
             % ('YES' if r['corrected_after_submission'] else 'NO'))
    L.append('- Items needing attention: %d' % r['flagged_count'])
    L.append('')
    L.append('## Item by item')
    L.append('')
    L.append('| ID | Question | Answer | Status | Matching facts |')
    L.append('|---|---|---|---|---|')
    for row in r['rows']:
        facts = '; '.join('%s %s %s' % (f['fact_type'], f['item'], f['date'])
                          for f in row['matching_facts'])
        L.append('| %s | %s | %s | %s | %s |'
                 % (row['id'], row['text'], row['answer'] or '(blank)',
                    row['status'], facts or '-'))
    L.append('')
    L.append('- Items needing attention: %s'
             % (', '.join(r['flagged_ids']) or 'none'))
    L.append('')
    L.append('## Filling guidance by fact type')
    L.append('')
    for k, v in r['guidance']:
        L.append('- **%s**: %s' % (k, v))
    L.append('')
    L.append('## Underwriting conclusion types')
    L.append('')
    for k, v in r['underwriting_types']:
        L.append('- **%s**: %s' % (k, v))
    L.append('')
    L.append('## Correction flow after submission')
    L.append('')
    for s in r['correction_flow']:
        L.append('1. %s' % s)
    L.append('')
    L.append('## Notes')
    L.append('')
    for n in r['notes']:
        L.append('- %s' % n)
    L.append('')
    L.append('## Must be confirmed manually')
    L.append('')
    for m in r['must_confirm']:
        L.append('- [ ] %s' % m)
    L.append('')
    L.append('Structural cross-check on the supplied questionnaire and facts. '
             'The scope of the disclosure duty follows the contract '
             'questionnaire. The underwriting conclusion follows the insurer. '
             'The consequence of non-disclosure follows the contract, the law '
             'in force and the insurer decision. No medical opinion, no '
             'diagnosis, no underwriting promise and no claim promise is given '
             'here.')
    return '\n'.join(L)


def run_selftest():
    ok = 0
    fail = []

    def check(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fail.append(msg)

    TJ = K_TIJIAN       # physical exam
    ZD = K_ZHEN         # diagnosis
    MZ = K_MENZHEN      # outpatient
    yes = '\u662f'
    no = '\u5426'

    qs = [
        {'id': 'Q1', 'text': TJ + K_YICHANG, 'answer': no},
        {'id': 'Q2', 'text': ZD, 'answer': yes, 'detail': ''},
        {'id': 'Q3', 'text': MZ, 'answer': no},
    ]
    facts = [
        {'type': 'EXAM_ABNORMAL', 'item': TJ, 'date': '2025-06'},
        {'type': 'DIAGNOSED', 'item': ZD, 'date': '2021-03'},
    ]

    # 1: answered no while a matching fact exists
    r = calc({'questions': qs, 'facts': facts})
    st = {x['id']: x['status'] for x in r['rows']}
    check(st['Q1'] == 'ANSWERED_NO_BUT_FACT_FOUND',
          'Q1 answered no with an exam abnormality must be flagged, got %s'
          % st['Q1'])
    check(st['Q3'] == 'ANSWERED_NO',
          'Q3 outpatient answered no with no outpatient fact is clean; '
          'got %s' % st['Q3'])
    check(st['Q2'] == 'ANSWERED_YES_WITHOUT_DETAIL',
          'Q2 answered yes without detail must be flagged, got %s' % st['Q2'])
    check(set(r['flagged_ids']) == {'Q1', 'Q2'},
          'flagged ids should be Q1 and Q2, got %s' % r['flagged_ids'])

    # 2: the outpatient question matches the diagnosis fact too, which is
    #    exactly the kind of overlap a human must resolve
    qs2 = [
        {'id': 'Q1', 'text': TJ + K_YICHANG, 'answer': no},
        {'id': 'Q3', 'text': MZ, 'answer': no},
    ]
    r2 = calc({'questions': qs2, 'facts': facts})
    st2 = {x['id']: x['status'] for x in r2['rows']}
    check(st2['Q1'] == 'ANSWERED_NO_BUT_FACT_FOUND',
          'exam question must match the exam fact')
    check(any(x['id'] == 'Q3' for x in r2['rows']),
          'the outpatient question must still be listed')

    # 3: answered yes with detail is clean
    r3 = calc({'questions': [{'id': 'Q2', 'text': ZD, 'answer': yes,
                              'detail': '2' + '\u578b\u7cd6\u5c3f\u75c5'
                                        ' 2021-03'}]})
    check(r3['rows'][0]['status'] == 'ANSWERED_YES',
          'yes with detail must be clean, got %s' % r3['rows'][0]['status'])
    check(r3['flagged_count'] == 0, 'nothing should be flagged')

    # 4: answered no with no related fact is clean
    r4 = calc({'questions': [{'id': 'Q5', 'text': '\u5bb6\u5ead' + K_JIATING,
                              'answer': no}], 'facts': []})
    check(r4['flagged_count'] == 0,
          'a no answer with no family fact must be clean')

    # 5: unanswered question is flagged
    r5 = calc({'questions': [{'id': 'Q7', 'text': ZD, 'answer': ''}]})
    check(r5['rows'][0]['status'] == 'UNANSWERED',
          'a blank answer must be reported as unanswered')
    check('Q7' in r5['flagged_ids'], 'an unanswered question must be flagged')

    # 6: family fact matched against family question
    r6 = calc({'questions': [{'id': 'Q9', 'text': K_JIATING, 'answer': no}],
               'facts': [{'type': 'FAMILY', 'item': K_JIATING,
                          'date': '2010-01'}]})
    check(r6['rows'][0]['status'] == 'ANSWERED_NO_BUT_FACT_FOUND',
          'family question answered no with a family fact must be flagged')

    # 7: treatment facts
    r7 = calc({'questions': [{'id': 'QA', 'text': K_YONGYAO, 'answer': no}],
               'facts': [{'type': 'TREATMENT', 'item': K_YONGYAO,
                          'date': '2024-02'}]})
    check(r7['rows'][0]['status'] == 'ANSWERED_NO_BUT_FACT_FOUND',
          'medication question answered no with medication fact must be flagged')

    # 8: wording guards
    joined = ' '.join(r['notes'])
    check('Answer what was asked' in joined,
          'the answering rule must be stated')
    check('not asked means never say' in joined,
          'the not-asked case must be qualified, not cleared')
    check('judgement cannot replace an honest answer' in joined,
          'the judgement rule must be stated')
    check('obligation, not a pass ticket' in joined,
          'honest disclosure must not be presented as a pass')
    check('applies to the excluded item only' in joined,
          'exclusion scope must be stated')
    check('you MUST confirm which item is excluded' in joined,
          'the exclusion confirmation step must be stated')
    check('Do NOT state that non-disclosure always means refusal' in joined,
          'the refusal claim must be refused')
    check('Do NOT change answers' in joined,
          'answer tampering must be refused')
    check('no medical opinion' in joined.lower() or
          'no medical opinion' in joined,
          'the no-medical-opinion statement must be present')
    low = joined.lower()
    check('will be declined' not in low and 'will be rejected' not in low,
          'no underwriting promise may appear')

    # 9: correction flag
    r8 = calc({'questions': [], 'corrected_after_submission': True})
    check(any('correction was reported' in n for n in r8['notes']),
          'a reported correction must be acknowledged')
    check(any('corrected through the insurer channel as early as possible'
              in n for n in r8['notes']),
          'the early-correction advice must be present')

    # 10: underwriting types all present
    keys = [k for k, _v in r['underwriting_types']]
    check(keys == ['STANDARD', 'LOADED', 'EXCLUSION', 'DEFERRED', 'DECLINED'],
          'all five underwriting types must be listed, got %s' % keys)
    uw = ' '.join(v for _k, v in r['underwriting_types'])
    check('Other responsibilities are still covered as agreed' in uw,
          'exclusion must state that other cover remains')
    check('not acceptable' in uw,
          'declined must refuse answer tampering')

    # 11: bad inputs rejected
    for bad in ({'questions': [{'text': '   '}]},
                {'questions': [{'text': ZD, 'answer': no}],
                 'facts': [{'type': 'UNKNOWN', 'item': 'x', 'date': '2020'}]}):
        try:
            calc(bad)
            check(False, 'bad input must be rejected: %s' % bad)
        except ValueError:
            check(True, 'bad input rejected')

    # 12: empty inputs do not crash
    r9 = calc({})
    check(r9['question_count'] == 0 and r9['flagged_count'] == 0,
          'empty input must not crash')

    # 13: markdown rendering
    md = to_md(r)
    check('Underwriting conclusion types' in md
          and 'Correction flow after submission' in md
          and 'Must be confirmed manually' in md,
          'markdown output must carry types, flow and checklist')

    lines = ['SELFTEST %s (%d passed, %d failed)'
             % ('OK' if not fail else 'FAIL', ok, len(fail))]
    for f in fail:
        lines.append('FAILED: %s' % f)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '_selftest_result.txt')
    open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return 0 if not fail else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file')
    ap.add_argument('--text')
    ap.add_argument('--out')
    ap.add_argument('--format', default='md')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return run_selftest()
    if a.file:
        data = json.load(open(a.file, 'r', encoding='utf-8'))
    elif a.text:
        data = json.loads(a.text)
    else:
        ap.error('--file or --text required')
    r = calc(data)
    txt = json.dumps(r, ensure_ascii=False, indent=2) if a.format == 'json' else to_md(r)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '_last_result.txt')
    open(out, 'w', encoding='utf-8').write(txt + '\n')
    print(txt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
