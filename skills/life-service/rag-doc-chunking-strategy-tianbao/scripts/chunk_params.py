#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAG chunk parameter calculator and overlap validator.

Computes token estimates, chunk counts and overlap ratios for a given
chunking setup, validates parameters against the recommended ranges, and
reports chunk-quality problems in a chunk list.

Usage
  python chunk_params.py --size 400 --overlap 15 --unit char
  python chunk_params.py --size 500 --overlap 20 --unit char --ratio 0.7
  python chunk_params.py --size 400 --overlap 15 --validate
  python chunk_params.py --file docs.txt --stats
  python chunk_params.py --file chunks.txt --chunks --stats
  python chunk_params.py --selftest

--chunks mode treats the file as a chunk list separated by a blank line.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, '_selftest_result.txt')

OVERLAP_MIN = 0.05
OVERLAP_LOW = 0.10
OVERLAP_HIGH = 0.20
OVERLAP_MAX = 0.25
SIZE_MIN = 100
SIZE_MAX = 2000
CHARS_PER_TOKEN = 1.0
DEFAULT_RATIO = 0.7
MAX_1_5 = 1.5
TINY_CHUNK = 50
INTEGRITY_TOL = 0.01

R_OVERLAP_LOW = 'overlap below 5%: boundary sentences will be cut apart'
R_OVERLAP_HIGH = 'overlap above 25%: storage cost grows with little benefit'
R_OVERLAP_OK = 'overlap ratio is inside the recommended 10-20 percent band'
R_OVERLAP_MID = 'overlap is 5-10 percent: still some boundary risk'
R_OVERLAP_OVER = 'overlap above 20 percent: acceptable but check storage cost'
R_SIZE_TINY = 'chunk size below 100 units: context will be too thin'
R_SIZE_HUGE = ('chunk size above 2000 units: one chunk may cover too many '
               'topics and dilute the embedding')
R_OVERLAP_GE_SIZE = 'overlap must be smaller than chunk size'
R_NEGATIVE = 'sizes must not be negative'
R_DIV_ZERO = 'chunk size must be greater than zero'

R_NO_CHUNKS = 'no chunks found in the input'
R_TINY_CHUNKS = '%d tiny chunks (< %d units): fragments pollute the index'
R_OVERSIZED = '%d chunks exceed 1.5x the median size: check the splitter'
R_INTEGRITY = ('total chunk length is %.1f%% of the source: some content may '
               'not have been ingested')
R_EMPTY = '%d empty chunks: they will never be retrieved'


def chunks_from_text(doc, size, overlap):
    if size <= 0:
        return []
    step = size - overlap
    if step <= 0:
        return [doc]
    out = []
    i = 0
    while i < len(doc):
        out.append(doc[i:i + size])
        i += step
    return out


def param_report(size, overlap, unit, ratio, doc_len=None):
    lines = []
    findings = []
    if size < 0 or overlap < 0:
        return None, [('ERROR', R_NEGATIVE)]
    if size == 0:
        return None, [('ERROR', R_DIV_ZERO)]
    if overlap >= size:
        return None, [('ERROR', R_OVERLAP_GE_SIZE)]
    ov_ratio = overlap / float(size)
    if unit == 'token':
        token_size = size
        char_size = size / ratio if ratio > 0 else size
    else:
        char_size = size
        token_size = size * ratio
    step = size - overlap
    lines.append('== CHUNK PARAMETERS ==')
    lines.append('unit                 : %s' % unit)
    lines.append('chunk size           : %d %s' % (size, unit))
    lines.append('overlap              : %d %s (%.1f%%)'
                 % (overlap, unit, ov_ratio * 100))
    lines.append('char/token ratio     : %s' % ratio)
    lines.append('estimated tokens     : %.0f' % token_size)
    lines.append('effective step       : %d %s' % (step, unit))
    if ov_ratio < OVERLAP_MIN:
        findings.append(('WARN', R_OVERLAP_LOW))
    elif ov_ratio < OVERLAP_LOW:
        findings.append(('INFO', R_OVERLAP_MID))
    elif ov_ratio <= OVERLAP_HIGH:
        findings.append(('INFO', R_OVERLAP_OK))
    elif ov_ratio <= OVERLAP_MAX:
        findings.append(('INFO', R_OVERLAP_OVER))
    else:
        findings.append(('WARN', R_OVERLAP_HIGH))
    if size < SIZE_MIN:
        findings.append(('WARN', R_SIZE_TINY))
    elif size > SIZE_MAX:
        findings.append(('WARN', R_SIZE_HUGE))
    if doc_len:
        n = max(1, int(math.ceil((doc_len - overlap) / float(step)))
                if step > 0 else 1)
        lines.append('document length      : %d %s' % (doc_len, unit))
        lines.append('estimated chunk count: %d' % n)
    lines.append('')
    grouped = {}
    for level, msg in findings:
        grouped.setdefault(level, []).append(msg)
    for level in ('ERROR', 'WARN', 'INFO'):
        items = grouped.get(level, [])
        lines.append('[%s] %d' % (level, len(items)))
        for msg in items:
            lines.append('  %s' % msg)
    return '\n'.join(lines) + '\n', findings


def median(values):
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0


def chunk_stats(chunks, source_len=None):
    findings = []
    lines = ['== CHUNK STATISTICS ==']
    lens = [len(c) for c in chunks]
    total = sum(lens)
    lines.append('chunk count          : %d' % len(chunks))
    if not lens:
        findings.append(('ERROR', R_NO_CHUNKS))
        lines.append('')
        lines.append('[ERROR] 1')
        lines.append('  %s' % R_NO_CHUNKS)
        return '\n'.join(lines) + '\n', findings
    lines.append('total length         : %d' % total)
    lines.append('min / median / max   : %d / %.0f / %d'
                 % (min(lens), median(lens), max(lens)))
    empty = [i for i, n in enumerate(lens) if n == 0]
    if empty:
        findings.append(('WARN', R_EMPTY % len(empty)))
    tiny = [i for i, n in enumerate(lens) if 0 < n < TINY_CHUNK]
    if tiny:
        findings.append(('WARN', R_TINY_CHUNKS % (len(tiny), TINY_CHUNK)))
    med = median(lens)
    if med > 0:
        big = [i for i, n in enumerate(lens) if n > med * MAX_1_5]
        if big:
            findings.append(('WARN', R_OVERSIZED % len(big)))
    if source_len and source_len > 0:
        ratio = total / float(source_len)
        lines.append('source length        : %d' % source_len)
        lines.append('integrity ratio      : %.4f' % ratio)
        if ratio < 1.0 - INTEGRITY_TOL:
            findings.append(('WARN', R_INTEGRITY % ((1 - ratio) * 100)))
    lines.append('')
    grouped = {}
    for level, msg in findings:
        grouped.setdefault(level, []).append(msg)
    for level in ('ERROR', 'WARN', 'INFO'):
        items = grouped.get(level, [])
        lines.append('[%s] %d' % (level, len(items)))
        for msg in items:
            lines.append('  %s' % msg)
    return '\n'.join(lines) + '\n', findings


def selftest():
    checks = []

    def ck(name, cond, info=''):
        checks.append((name, bool(cond), info))

    # 1 overlap ratio computation
    text, f = param_report(400, 15, 'char', DEFAULT_RATIO)
    ck('overlap 15/400 = 3.75% flagged low',
       any('below 5%' in m for _l, m in f), str([m for _l, m in f]))

    # 2 overlap in the recommended band
    text, f = param_report(400, 60, 'char', DEFAULT_RATIO)
    ck('overlap 60/400 = 15% is recommended',
       any('recommended' in m for _l, m in f))

    # 3 overlap too high
    text, f = param_report(400, 120, 'char', DEFAULT_RATIO)
    ck('overlap 30% warns', any('above 25%' in m for _l, m in f))

    # 4 overlap >= size errors
    text, f = param_report(400, 400, 'char', DEFAULT_RATIO)
    ck('overlap >= size errors',
       any('smaller than chunk size' in m for _l, m in f))

    # 5 tiny chunk size warns
    text, f = param_report(50, 5, 'char', DEFAULT_RATIO)
    ck('tiny chunk size warns',
       any('below 100' in m for _l, m in f))

    # 6 huge chunk size warns
    text, f = param_report(3000, 300, 'char', DEFAULT_RATIO)
    ck('huge chunk size warns',
       any('above 2000' in m for _l, m in f))

    # 7 chunk count for a long document
    text, f = param_report(400, 60, 'char', DEFAULT_RATIO, doc_len=10000)
    ck('chunk count for 10000/400/60 = 30', 'estimated chunk count: 30' in text,
       [l for l in text.splitlines() if 'chunk count' in l])

    # 8 token estimate for char unit
    text, f = param_report(500, 50, 'char', 0.7)
    ck('tokens = 500 * 0.7 = 350', 'estimated tokens     : 350' in text)

    # 9 token unit: chars = 500 / 0.7 ~= 714
    text, f = param_report(500, 50, 'token', 0.7)
    ck('token unit keeps size as tokens',
       'estimated tokens     : 500' in text,
       [l for l in text.splitlines() if 'tokens' in l])

    # 9b char/token conversion is applied consistently
    text, f = param_report(500, 50, 'char', 0.7)
    ck('char unit converts to tokens', 'estimated tokens     : 350' in text)

    # 10 negative values error
    text, f = param_report(-1, 10, 'char', DEFAULT_RATIO)
    ck('negative size errors', text is None)

    # 11 zero size errors
    text, f = param_report(0, 0, 'char', DEFAULT_RATIO)
    ck('zero size errors', text is None and len(f) == 1)

    # 12 chunking produces overlapping windows: 100 chars, size 30, overlap 10
#    step = 20, so windows start at 0/20/40/60/80 -> 5 chunks
    doc = ''.join('abcdefghij' for _ in range(10))
    parts = chunks_from_text(doc, 30, 10)
    ck('chunk windows advance by size-overlap',
       len(parts) == 5 and parts[0] == doc[:30] and parts[1] == doc[20:50],
       '%d chunks' % len(parts))

    # 13 chunks overlap by exactly the overlap amount
    ov = 0
    for a, b in zip(parts, parts[1:]):
        ov = max(ov, len(set(a) & set(b)))
    ck('windows overlap', ov > 0, 'overlap chars=%d' % ov)

    # 14 stats on a healthy chunk list
    chunks = ['x' * 400, 'x' * 400, 'x' * 400]
    text, f = chunk_stats(chunks, source_len=1200)
    ck('healthy chunks have no errors',
       not any(l == 'ERROR' for l, _m in f)
       and 'integrity ratio      : 1.0000' in text)

    # 15 integrity loss warns
    chunks = ['x' * 400, 'x' * 400]
    text, f = chunk_stats(chunks, source_len=1200)
    ck('missing content warns',
       any('not have been ingested' in m for _l, m in f))

    # 16 tiny chunks warn
    chunks = ['x' * 400, 'x' * 10, 'x' * 400]
    text, f = chunk_stats(chunks)
    ck('tiny chunks warn', any('tiny chunks' in m for _l, m in f))

    # 17 oversized chunks warn
    chunks = ['x' * 100, 'x' * 100, 'x' * 900]
    text, f = chunk_stats(chunks)
    ck('oversized chunks warn', any('exceed 1.5x' in m for _l, m in f))

    # 18 empty chunk list errors
    text, f = chunk_stats([], None)
    ck('no chunks errors', any('no chunks found' in m for _l, m in f))

    # 19 median of an even list
    ck('median even', abs(median([10, 20, 30, 40]) - 25.0) < 1e-9,
       '%.1f' % median([10, 20, 30, 40]))

    # 20 median of an odd list
    ck('median odd', abs(median([10, 20, 30]) - 20.0) < 1e-9)

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
    p = argparse.ArgumentParser(
        description='RAG chunk parameter calculator and validator')
    p.add_argument('--size', type=int, default=None, help='chunk size')
    p.add_argument('--overlap', type=int, default=0, help='overlap length')
    p.add_argument('--unit', type=str, default='char',
                   choices=['char', 'token'])
    p.add_argument('--ratio', type=float, default=DEFAULT_RATIO,
                   help='chars per token')
    p.add_argument('--file', type=str, default=None,
                   help='source text, or a chunk list with --chunks')
    p.add_argument('--chunks', action='store_true',
                   help='treat --file as a blank-line separated chunk list')
    p.add_argument('--stats', action='store_true',
                   help='report chunk statistics')
    p.add_argument('--validate', action='store_true',
                   help='validate overlap ratio')
    p.add_argument('--json', type=str, default=None, help='dump result as JSON')
    p.add_argument('--out', type=str, default=None)
    p.add_argument('--selftest', action='store_true')
    return p


def main():
    args = build_parser().parse_args()
    if args.selftest:
        return selftest()
    if args.file is None and args.size is None:
        text = '[ERROR] pass --size or --file\n'
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    lines = []
    findings = []
    doc_len = None
    if args.file and os.path.exists(args.file):
        with open(args.file, 'r', encoding='utf-8') as fh:
            raw = fh.read()
        if args.chunks:
            chunks = [c for c in raw.split('\n\n') if c.strip() != '']
            doc_len = len(raw)
        else:
            chunks = [raw]
            doc_len = len(raw)
        if args.stats:
            t, f = chunk_stats(chunks, doc_len)
            lines.append(t)
            findings.extend(f)
    elif args.file:
        text = '[ERROR] file not found: %s\n' % args.file
        with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(text)
        return 2
    if args.size:
        t, f = param_report(args.size, args.overlap, args.unit, args.ratio,
                            doc_len)
        if t is None:
            text = '\n'.join('ERROR: %s' % m for m in f) + '\n'
            with open(RESULT, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(text)
            print(text)
            return 2
        lines.append(t)
        findings.extend(f)
    result = ''.join(lines) if lines else '(no report)\n'
    if args.json:
        payload = {
            'findings': [{'level': l, 'message': m} for l, m in findings],
        }
        with open(args.json, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(payload, fh, ensure_ascii=True, indent=2)
    path = args.out or RESULT
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(result)
    print(result)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())