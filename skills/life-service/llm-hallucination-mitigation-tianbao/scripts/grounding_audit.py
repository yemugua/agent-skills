#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM answer grounding and citation auditor.

Checks citation coverage, fabricated references, unsupported assertions,
numeric claims not found in the sources, confidence/evidence consistency and
refusal wording, then grades findings as ERROR / WARN / INFO.

Usage
  python grounding_audit.py --file answer.json
  python grounding_audit.py --file answer.json --check-citation
  python grounding_audit.py --file answer.json --check-assertion
  python grounding_audit.py --file answer.json --check-refusal
  python grounding_audit.py --selftest

JSON input
  {"answer": "...", "sources": [{"id":"S1","title":"...","locator":"..."}],
   "confidence": "high"}
Confidence is one of high / mid / low.
Source tags in the answer look like [S1] or [1].
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

CITATION_RE = re.compile(r'\[\s*([A-Za-z0-9_\u4e00-\u9fff]{1,12})\s*\]')

CN_DIGITS = {
    '\u96f6': 0, '\u4e00': 1, '\u4e8c': 2, '\u4e24': 2, '\u4e09': 3,
    '\u56db': 4, '\u4e94': 5, '\u516d': 6, '\u4e03': 7, '\u516b': 8,
    '\u4e5d': 9,
}
UNITS = {10: '\u5341', 100: '\u767e', 1000: '\u5343', 10000: '\u4e07'}
NUM_CHARS = ''.join(CN_DIGITS) + ''.join(UNITS.values())
PREFIX_WORDS = '\u7ea6|\u8fd1|\u8d85\u8fc7|\u81f3\u5c11|\u6700\u591a|\u4e0d\u8d85\u8fc7|\u4e0d\u5c11\u4e8e'
UNITS_CN = ('\u5de5\u4f5c\u65e5|\u5929|\u65e5|\u5468|\u6708|\u5e74|'
            '\u5c0f\u65f6|\u5206\u949f|\u5757|\u5143|\u7f8e\u5143|%')
# A numeric claim is a number (Arabic or Chinese digits) with an optional
# qualifier and a unit. It must not swallow the surrounding sentence.
DAYS_RE = re.compile(
    r'(?:%s)?\s*[0-9%s]+\s*(?:\u4e2a)?\s*(?:%s)' % (PREFIX_WORDS, NUM_CHARS,
                                                     UNITS_CN), re.I)
DAYS_RE_ASCII = re.compile(
    r'\d+\s*(?:%|days?|hours?|weeks?|months?|years?|min(?:utes?)?|yuan|rmb)',
    re.I)

# Split into sentences on Chinese and ASCII terminators.
SENT_RE = re.compile(r'[^\u3002\uff01\uff1f!?\uff1b;\n]+[\u3002\uff01\uff1f!?\uff1b;]?')

REFUSAL_MARKERS = ('\u672a\u627e\u5230\u76f8\u5173\u4fe1\u606f', '\u8d44\u6599\u4e0d\u8db3\u4ee5\u56de\u7b54', '\u65e0\u6cd5\u7ed9\u51fa\u51c6\u786e\u7b54\u590d',
                   '\u6ca1\u6709\u627e\u5230\u76f8\u5173', '\u672a\u627e\u5230\u76f8\u5173\u8bb0\u5f55', '\u672a\u68c0\u7d22\u5230\u76f8\u5173',
                   'no relevant information', 'not found in the materials',
                   'insufficient information')
HEDGE_WORDS = ('\u5927\u6982', '\u5e94\u8be5\u662f', '\u4e00\u822c\u6765\u8bf4', '\u901a\u5e38', '\u4f30\u8ba1', '\u5dee\u4e0d\u591a',
               '\u6211\u8bb0\u5f97', '\u5927\u6982\u5427', 'probably', 'roughly', 'i think')
HANDOFF_RE = re.compile(r'\u8f6c\u4eba\u5de5|\u4eba\u5de5\u5ba2\u670d|\u4eba\u5de5\u670d\u52a1|\u8f6c\u63a5\u4eba\u5de5|escalat|human',
                        re.I)

HIGH_MIN_SOURCES = 2
CONFIDENCES = ('high', 'mid', 'low')

R_NO_ANSWER = 'answer field is missing or empty'
R_BAD_JSON = 'input is not valid JSON'
R_NO_SOURCES = 'no sources supplied: nothing can be grounded'
R_FABRICATED = 'fabricated citation: tag not present in the source list'
R_CITATION_LOW = 'citation coverage below the threshold'
R_NO_CITATION = 'sentence has no citation tag'
R_NO_LOCATOR = 'source has no locator: the user cannot find the passage'
R_NO_TITLE = 'source has no title'
R_NUM_UNGROUNDED = 'numeric value does not appear verbatim in any source'
R_CONF_HIGH = 'confidence=high but fewer than 2 sources'
R_CONF_LOW = 'confidence=low yet the answer makes factual claims'
R_REFUSAL_HEDGE = 'refusal answer contains hedging wording'
R_REFUSAL_NO_HANDOFF = 'refusal answer offers no escalation path'
R_REFUSAL_NO_MARKER = 'low confidence but no refusal marker present'
R_ANSWER_ON_LOW = 'low confidence with a full answer: must escalate instead'
R_UNKNOWN_CONF = 'confidence must be high, mid or low'


def g(d, key):
    v = d.get(key)
    return v.strip() if isinstance(v, str) else v


def sentences(answer):
    return [s.strip() for s in SENT_RE.findall(answer) if s.strip()]


def has_refusal(answer):
    low = answer.lower()
    return any(m.lower() in low for m in REFUSAL_MARKERS)


def hedges(answer):
    return [w for w in HEDGE_WORDS if w in answer]


def source_texts(sources):
    out = []
    for s in sources:
        if not isinstance(s, dict):
            out.append('')
            continue
        parts = [g(s, 'id') or '', g(s, 'title') or '',
                 g(s, 'locator') or '', g(s, 'excerpt') or '',
                 g(s, 'text') or '']
        out.append(' '.join(p for p in parts if p))
    return out


def check_citations(answer, sources, threshold=0.8):
    findings = []
    tags = CITATION_RE.findall(answer)
    valid = set()
    for s in sources:
        if isinstance(s, dict) and g(s, 'id'):
            valid.add(str(g(s, 'id')))
    for t in tags:
        if valid and t not in valid:
            findings.append(('ERROR', 'citation',
                             '%s: [%s]' % (R_FABRICATED, t)))
    sens = sentences(answer)
    cited = 0
    uncited = []
    for s in sens:
        if CITATION_RE.search(s):
            cited += 1
        else:
            uncited.append(s[:24])
    total = len(sens)
    cov = (cited / total) if total else 0.0
    if uncited:
        findings.append(('WARN', 'coverage',
                         '%s (%d/%d = %.0f%%): %s'
                         % (R_NO_CITATION, cited, total, cov * 100,
                            '; '.join(uncited[:3]))))
    if cov < threshold and total > 0:
        findings.append(('WARN', 'coverage',
                         '%s (%.0f%% < %.0f%%)'
                         % (R_CITATION_LOW, cov * 100, threshold * 100)))
    return findings, cov, total


def check_sources(sources):
    findings = []
    for s in sources:
        sid = g(s, 'id') if isinstance(s, dict) else None
        if not sid:
            findings.append(('ERROR', 'source', 'source without an id'))
            continue
        if not g(s, 'title'):
            findings.append(('WARN', sid, R_NO_TITLE))
        if not g(s, 'locator'):
            findings.append(('WARN', sid, R_NO_LOCATOR))
    return findings


def cn_to_int(text):
    """Convert a Chinese numeral string to an int (supports up to99999)."""
    text = text.strip()
    if not text:
        return None
    if any(ch.isdigit() for ch in text):
        try:
            return int(text)
        except ValueError:
            return None
    total = 0
    section = 0
    number = 0
    for ch in text:
        if ch in CN_DIGITS:
            number = CN_DIGITS[ch]
        elif ch in UNITS:
            section = (section + (number or 1)) * UNITS[ch]
            number = 0
            total += section
            section = 0
        else:
            return None
    total += section + number
    return total or None


def norm_number(raw):
    """Normalize a numeric claim so Chinese and Arabic forms compare equal."""
    s = re.sub(r'\s+', '', str(raw))
    m = re.search(r'[%s0-9]+' % NUM_CHARS, s)
    if not m:
        return s
    val = cn_to_int(m.group(0))
    if val is None:
        return s
    unit = s[m.end():]
    return '%d%s' % (val, unit)


def check_numbers(answer, sources):
    """Flag numeric claims that do not appear verbatim in any source.

    Both the answer and the sources are normalized so that Chinese numerals
    ("seven days") and Arabic numerals ("7") in different notation match.
    """
    findings = []
    blob = ' '.join(source_texts(sources))
    if not blob:
        return findings
    blob_nospace = re.sub(r'\s+', '', blob)
    blob_norms = set()
    for m in DAYS_RE.findall(blob):
        blob_norms.add(norm_number(m))
    for m in DAYS_RE_ASCII.findall(blob):
        blob_norms.add(norm_number(m))
    if not blob_norms:
        blob_norms.add(blob_nospace)
    hits = list(DAYS_RE.findall(answer)) + list(DAYS_RE_ASCII.findall(answer))
    seen = set()
    for raw in hits:
        needle = norm_number(raw)
        if not needle or needle in seen:
            continue
        seen.add(needle)
        if needle in blob_norms or needle in blob_nospace:
            continue
        findings.append(('WARN', 'numeric',
                         '%s: %s' % (R_NUM_UNGROUNDED, needle)))
    return findings


def check_confidence(conf, answer, sources, n_sources):
    findings = []
    conf = (conf or '').lower()
    if conf and conf not in CONFIDENCES:
        findings.append(('ERROR', 'confidence',
                         '%s: %r' % (R_UNKNOWN_CONF, conf)))
        return findings
    if conf == 'high' and n_sources < HIGH_MIN_SOURCES:
        findings.append(('ERROR', 'confidence',
                         '%s (%d source(s))' % (R_CONF_HIGH, n_sources)))
    if conf == 'low':
        if not has_refusal(answer):
            # A low-confidence run must refuse or escalate, never answer in
            # full. Both conditions are reported so the reason is explicit.
            findings.append(('ERROR', 'confidence', R_REFUSAL_NO_MARKER))
            findings.append(('ERROR', 'answer', R_ANSWER_ON_LOW))
    return findings


def check_refusal(answer, conf):
    findings = []
    if not has_refusal(answer):
        return findings
    hs = hedges(answer)
    if hs:
        findings.append(('ERROR', 'refusal',
                         '%s: %s' % (R_REFUSAL_HEDGE, ', '.join(hs))))
    if not HANDOFF_RE.search(answer):
        findings.append(('WARN', 'refusal', R_REFUSAL_NO_HANDOFF))
    return findings


def audit(payload, check_cit=False, check_assert=False, check_ref=False,
          threshold=0.8):
    findings = []
    answer = g(payload, 'answer')
    if not answer:
        return [('ERROR', 'answer', R_NO_ANSWER)], 0.0, 0
    sources = payload.get('sources') or []
    conf = g(payload, 'confidence')
    if not sources:
        findings.append(('ERROR', 'sources', R_NO_SOURCES))
    if check_cit:
        f, cov, total = check_citations(answer, sources, threshold)
        findings.extend(f)
    else:
        cov, total = 0.0, 0
    findings.extend(check_sources(sources))
    if check_assert:
        findings.extend(check_numbers(answer, sources))
    findings.extend(check_confidence(conf, answer, sources, len(sources)))
    if check_ref:
        findings.extend(check_refusal(answer, conf))
    return findings, cov, total


def render(payload, findings, cov, total, lines):
    answer = g(payload, 'answer') or ''
    sources = payload.get('sources') or []
    lines.append('== GROUNDING AUDIT ==')
    lines.append('answer length        : %d chars' % len(answer))
    lines.append('sources              : %d' % len(sources))
    lines.append('confidence           : %s' % (g(payload, 'confidence') or '-'))
    lines.append('refusal detected     : %s' % ('yes' if has_refusal(answer)
                                               else 'no'))
    hs = hedges(answer)
    lines.append('hedging words        : %s' % (', '.join(hs) if hs else 'none'))
    if total:
        cited = int(round(cov * total))
        lines.append('citation coverage    : %.0f%% (%d/%d sentences)'
                     % (cov * 100, cited, total))
    lines.append('')
    grouped = {}
    for level, who, msg in findings:
        grouped.setdefault(level, []).append((who, msg))
    for level in ('ERROR', 'WARN', 'INFO'):
        items = grouped.get(level, [])
        lines.append('[%s] %d' % (level, len(items)))
        for who, msg in items:
            lines.append('  %s: %s' % (who, msg))
    err = len(grouped.get('ERROR', []))
    lines.append('')
    if err:
        lines.append('VERDICT: REJECT (errors=%d)' % err)
    else:
        lines.append('VERDICT: PASS (errors=0, warns=%d)'
                     % len(grouped.get('WARN', [])))


def good_payload():
    return {
        'answer': ('\u81ea\u7b7e\u6536\u8d77\u4e03\u65e5\u5185\u53ef\u7533\u8bf7\u65e0\u7406\u7531\u9000\u8d27 [\u6765\u6e901]\u3002'
                   '\u8de8\u5883\u5546\u54c1\u8fd0\u8d39\u9700\u8054\u7cfb\u4eba\u5de5\u5ba2\u670d\u786e\u8ba4 [\u6765\u6e902]\u3002'),
        'sources': [
            {'id': '\u6765\u6e901', 'title': '\u552e\u540e\u653f\u7b56 v3', 'locator': '\u7b2c2\u7ae0',
             'excerpt': '\u81ea\u7b7e\u6536\u8d77 7 \u65e5\u5185\u53ef\u7533\u8bf7\u65e0\u7406\u7531\u9000\u8d27'},
            {'id': '\u6765\u6e902', 'title': '\u8de8\u5883\u552e\u540e\u8bf4\u660e', 'locator': '\u7b2c1\u8282',
             'excerpt': '\u8de8\u5883\u5546\u54c1\u8fd0\u8d39\u9700\u8054\u7cfb\u5ba2\u670d\u786e\u8ba4'},
        ],
        'confidence': 'high',
    }


def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    p = good_payload()

    # 1 clean answer
    f, cov, total = audit(p, True, True, True)
    errs = [x for x in f if x[0] == 'ERROR']
    ck('clean answer has no errors', not errs, str([x[2] for x in errs][:2]))

    # 2 citation coverage computed
    ck('citation coverage is 100%', abs(cov - 1.0) < 1e-9,
       'cov=%.2f total=%d' % (cov, total))

    # 3 missing answer errors
    f2, _, _ = audit({'sources': []}, True, True, True)
    ck('missing answer errors',
       any(x[0] == 'ERROR' and x[1] == 'answer' for x in f2))

    # 4 no sources errors
    f3, _, _ = audit({'answer': 'abc [1]', 'sources': []}, True, False, False)
    ck('no sources errors',
       any(x[0] == 'ERROR' and 'nothing can be grounded' in x[2] for x in f3))

    # 5 fabricated citation errors
    bad = dict(p)
    bad['answer'] = '\u653f\u7b56\u8981\u6c42\u4e03\u65e5\u9000\u6362 [\u6765\u6e901]\u3002\u53e6\u6709\u89c4\u5b9a\u89c1 [\u6765\u6e909]\u3002'
    f4, _, _ = audit(bad, True, False, False)
    ck('fabricated citation errors',
       any(x[0] == 'ERROR' and 'fabricated' in x[2] for x in f4))

    # 6 uncited sentence warns
    bad = dict(p)
    bad['answer'] = '\u4e03\u65e5\u53ef\u9000 [\u6765\u6e901]\u3002\u53e6\u5916\u8fd8\u6709\u9690\u85cf\u6761\u6b3e\u503c\u5f97\u6ce8\u610f\u3002'
    f5, cov5, _ = audit(bad, True, False, False)
    ck('uncited sentence warns',
       any(x[0] == 'WARN' and 'no citation tag' in x[2] for x in f5))

    # 7 coverage below threshold warns
    bad = dict(p)
    bad['answer'] = '\u4e03\u65e5\u53ef\u9000 [\u6765\u6e901]\u3002\u7532\u3002\u4e59\u3002\u4e19\u3002\u4e01\u3002'
    f6, cov6, _ = audit(bad, True, False, False)
    ck('low coverage warns',
       any('coverage below' in x[2] for x in f6))

    # 8 source without locator warns
    bad = dict(p)
    bad['sources'] = [{'id': '\u6765\u6e901', 'title': '\u653f\u7b56'}]
    f7, _, _ = audit(bad, True, False, False)
    ck('source without locator warns',
       any(x[0] == 'WARN' and 'locator' in x[2] for x in f7))

    # 9 numeric claim not in sources warns
    bad = dict(p)
    bad['answer'] = '\u53ef\u5728\u5341\u4e94\u65e5\u5185\u7533\u8bf7\u65e0\u7406\u7531\u9000\u8d27 [\u6765\u6e901]\u3002'
    f8, _, _ = audit(bad, False, True, False)
    ck('ungrounded number warns',
       any(x[0] == 'WARN' and 'verbatim' in x[2] for x in f8))

    # 10 grounded number does not warn
    f9, _, _ = audit(p, False, True, False)
    ck('grounded number is clean',
       not any('verbatim' in x[2] for x in f9))

    # 11 high confidence with one source errors
    bad = dict(p)
    bad['sources'] = [{'id': '\u6765\u6e901', 'title': '\u653f\u7b56', 'locator': '\u7b2c1\u7ae0'}]
    bad['answer'] = '\u4e03\u65e5\u53ef\u9000 [\u6765\u6e901]\u3002'
    bad['confidence'] = 'high'
    f10, _, _ = audit(bad, False, False, False)
    ck('high confidence with one source errors',
       any(x[0] == 'ERROR' and 'confidence=high' in x[2] for x in f10))

    # 12 low confidence without refusal marker errors
    bad = dict(p)
    bad['confidence'] = 'low'
    f11, _, _ = audit(bad, False, False, False)
    ck('low confidence without refusal errors',
       any(x[0] == 'ERROR' and 'refusal marker' in x[2] for x in f11))

    # 13 low confidence with a full answer errors
    bad = dict(p)
    bad['confidence'] = 'low'
    bad['answer'] = '\u653f\u7b56\u8981\u6c42\u4e03\u65e5\u5185\u53ef\u9000 [\u6765\u6e901]\u3002'
    f12, _, _ = audit(bad, False, False, False)
    ck('low confidence full answer errors',
       any(x[0] == 'ERROR' and 'escalate' in x[2] for x in f12))

    # 14 good refusal passes
    good = {
        'answer': '\u6211\u6ca1\u6709\u627e\u5230\u5173\u4e8e\u8de8\u5883\u9000\u8d27\u8fd0\u8d39\u7684\u76f8\u5173\u8bb0\u5f55\uff0c\u5df2\u4e3a\u60a8\u8f6c\u63a5\u4eba\u5de5\u5ba2\u670d\u6838\u5b9e\u3002',
        'sources': [],
        'confidence': 'low',
    }
    f13, _, _ = audit(good, False, False, True)
    ck('well-formed refusal passes',
       not any(x[0] == 'ERROR' and x[1] == 'refusal' for x in f13))

    # 15 refusal with hedging errors
    bad = dict(good)
    bad['answer'] = '\u4e00\u822c\u6765\u8bf4\u5e94\u8be5\u6709\u89c4\u5b9a\uff0c\u6211\u6ca1\u6709\u627e\u5230\u76f8\u5173\u4fe1\u606f\uff0c\u5df2\u8f6c\u4eba\u5de5\u5ba2\u670d\u3002'
    f14, _, _ = audit(bad, False, False, True)
    ck('refusal with hedging errors',
       any(x[0] == 'ERROR' and 'hedging' in x[2] for x in f14))

    # 16 refusal without handoff warns
    bad = dict(good)
    bad['answer'] = '\u6211\u6ca1\u6709\u627e\u5230\u76f8\u5173\u4fe1\u606f\u3002'
    f15, _, _ = audit(bad, False, False, True)
    ck('refusal without handoff warns',
       any(x[0] == 'WARN' and 'escalation' in x[2] for x in f15))

    # 17 unknown confidence errors
    bad = dict(p)
    bad['confidence'] = 'medium'
    f16, _, _ = audit(bad, False, False, False)
    ck('unknown confidence errors',
       any(x[0] == 'ERROR' and 'high, mid or low' in x[2] for x in f16))

    # 18 hedge detection
    ck('hedge words detected',
       hedges('\u8fd9\u4e2a\u5927\u6982\u662f\u5341\u4e94\u5929\u5427') == ['\u5927\u6982'],
       str(hedges('\u8fd9\u4e2a\u5927\u6982\u662f\u5341\u4e94\u5929\u5427')))

    # 19 refusal detection
    ck('refusal marker detected',
       has_refusal('\u6211\u6ca1\u6709\u627e\u5230\u76f8\u5173\u4fe1\u606f') and
       not has_refusal('\u653f\u7b56\u8981\u6c42\u4e03\u65e5\u53ef\u9000'))

    out = []
    failed = 0
    for name, ok, info in checks:
        if not ok:
            failed += 1
        out.append('%s  %-44s %s' % ('PASS' if ok else 'FAIL', name, info))
    out.append('total=%d failed=%d' % (len(checks), failed))
    out.append('SELFTEST OK' if failed == 0 else 'SELFTEST FAILED')
    text = '\n'.join(out) + '\n'
    with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    return 0 if failed == 0 else 1


def build_parser():
    p = argparse.ArgumentParser(description='LLM grounding auditor')
    p.add_argument('--file', type=str, default=None,
                   help='JSON answer payload, or - for stdin')
    p.add_argument('--check-citation', dest='check_citation',
                   action='store_true')
    p.add_argument('--check-assertion', dest='check_assertion',
                   action='store_true')
    p.add_argument('--check-refusal', dest='check_refusal', action='store_true')
    p.add_argument('--threshold', type=float, default=0.8,
                   help='minimum citation coverage')
    p.add_argument('--out', type=str, default=None)
    p.add_argument('--selftest', action='store_true')
    return p


def main():
    args = build_parser().parse_args()
    if args.selftest:
        return selftest()
    if not args.file:
        text = '[ERROR] --file is required (use - for stdin)\n'
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    if args.file == '-':
        raw = sys.stdin.read()
    else:
        try:
            with open(args.file, 'r', encoding='utf-8') as fh:
                raw = fh.read()
        except OSError as exc:
            text = '[ERROR] cannot read %s: %s\n' % (args.file, exc)
            with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(text)
            print(text)
            return 2
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        text = '[ERROR] %s: %s\n' % (R_BAD_JSON, exc)
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    findings, cov, total = audit(payload, args.check_citation,
                                 args.check_assertion, args.check_refusal,
                                 args.threshold)
    lines = []
    render(payload, findings, cov, total, lines)
    text = '\n'.join(lines) + '\n'
    path = args.out or RESULT
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(text)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())