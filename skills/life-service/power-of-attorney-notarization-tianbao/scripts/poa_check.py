# -*- coding: utf-8 -*-
"""\u6388\u6743\u59d4\u6258\u4e66\u8981\u7d20\u6838\u67e5\u3002

\u7528\u6cd5:
  python poa_check.py --file poa.txt --purpose \u4e0d\u52a8\u4ea7\u8f6c\u79fb\u767b\u8bb0
  python poa_check.py --file poa.txt --purpose \u80a1\u6743\u8f6c\u8ba9 --json
  python poa_check.py --selftest
"""
import argparse
import json
import os
import re
import sys

OK = "\u9f50\u5168"
MISS = "\u7f3a\u5931"
VAGUE = "\u7b3c\u7edf"
INFO = "\u63d0\u793a"

LEVEL_ORDER = {OK: 0, INFO: 1, VAGUE: 2, MISS: 3}

# \u516d\u9879\u5fc5\u5907\u8981\u7d20 + \u4e24\u4e2a\u8eab\u4efd\u53f7\u7ec6\u9879
ELEMENTS = [
    ("principal", "\u59d4\u6258\u4eba\u59d3\u540d",
     r"\u59d4\u6258\u4eba|\u6388\u6743\u4eba",
     "\u9700\u5199\u660e\u59d4\u6258\u4eba\u59d3\u540d\u3002"),
    ("principal_id", "\u59d4\u6258\u4eba\u8eab\u4efd\u8bc1\u53f7",
     r"\u516c\u6c11\u8eab\u4efd\u53f7\u7801|\u8eab\u4efd\u8bc1\u53f7|\u8eab\u4efd\u8bc1\u4ef6\u53f7\u7801|\u8bc1\u4ef6\u53f7\u7801|\d{17}[\dXx]",
     "\u9700\u5199\u660e\u59d4\u6258\u4eba\u8eab\u4efd\u8bc1\u53f7\uff0c\u4ec5\u6709\u59d3\u540d\u65e0\u6cd5\u4e0e\u4ea7\u6743\u6216\u767b\u8bb0\u4fe1\u606f\u5bf9\u5e94\u3002"),
    ("agent", "\u53d7\u6258\u4eba\u59d3\u540d",
     r"\u53d7\u6258\u4eba|\u4ee3\u7406\u4eba|\u53d7\u6258\u4ee3\u7406",
     "\u9700\u5199\u660e\u53d7\u6258\u4eba\u59d3\u540d\u3002"),
    ("agent_id", "\u53d7\u6258\u4eba\u8eab\u4efd\u8bc1\u53f7",
     r"\d{17}[\dXx]",
     "\u9700\u5199\u660e\u53d7\u6258\u4eba\u8eab\u4efd\u8bc1\u53f7\uff0c\u5426\u5219\u65e0\u6cd5\u5b9a\u4f4d\u8d23\u4efb\u4e3b\u4f53\u3002"),
    ("matter", "\u4ee3\u7406\u4e8b\u9879",
     r"\u4ee3\u7406\u4e8b\u9879|\u59d4\u6258\u4e8b\u9879|\u4ee3\u529e|\u529e\u7406",
     "\u9700\u5199\u660e\u4ee3\u7406\u4e8b\u9879\uff0c\u4e14\u5177\u4f53\u5230\u6807\u7684\u4e0e\u73af\u8282\u3002"),
    ("scope", "\u6743\u9650\u8303\u56f4",
     r"\u6743\u9650|\u4ee3\u7406\u6743\u9650|\u6388\u6743\u8303\u56f4|\u59d4\u6258\u6743\u9650",
     "\u9700\u5199\u660e\u6743\u9650\u8303\u56f4\uff0c\u5efa\u8bae\u7528\u5206\u9879\u5f0f\u5217\u4e3e\u5177\u4f53\u52a8\u4f5c\u3002"),
    ("term", "\u6709\u6548\u671f\u9650",
     r"\u6709\u6548\u671f|\u6709\u6548\u671f\u9650|\u671f\u9650",
     "\u9700\u5199\u660e\u6709\u6548\u671f\u9650\u7684\u8d77\u6b62\u65e5\u671f\uff08YYYY \u5e74 MM \u6708 DD \u65e5\uff09\u3002"),
    ("sign", "\u7b7e\u540d\u4e0e\u637a\u5370",
     r"\u7b7e\u540d|\u7b7e\u5b57|\u637a\u5370|\u6309\u6307\u5370|\u7b7e\u7ae0",
     "\u9700\u7531\u59d4\u6258\u4eba\u672c\u4eba\u7b7e\u540d\u5e76\u6309\u637a\u6307\u5370\uff0c\u4e0d\u5f97\u4ed6\u4eba\u4ee3\u7b7e\u3002"),
]

VAGUE_SCOPE = [
    (r"\u5168\u6743\u4ee3\u7406[^\u3002;\uff1b\n]{0,4}(?:\u4e00\u5207|\u6240\u6709|\u5168\u90e8)?(?:\u4e8b\u52a1|\u4e8b\u5b9c|\u4e8b\u9879)",
     "\u300c\u5168\u6743\u4ee3\u7406\u4e00\u5207\u4e8b\u52a1\u300d\u7c7b\u8868\u8ff0\u6388\u6743\u8303\u56f4\u4e0d\u53ef\u6267\u884c\uff0c"
     "\u53ef\u80fd\u88ab\u53d7\u7406\u673a\u6784\u6216\u76f8\u5bf9\u65b9\u62d2\u6536\uff0c\u5efa\u8bae\u6539\u4e3a\u5206\u9879\u5f0f"),
    (r"(?:\u529e\u7406|\u5904\u7406|\u4ee3\u529e)\u4e00\u5207",
     "\u300c\u4e00\u5207\u300d\u7c7b\u8868\u8ff0\u8fc7\u4e8e\u7b3c\u7edf\uff0c\u5e94\u6539\u4e3a\u5206\u9879\u5217\u4e3e\u5177\u4f53\u52a8\u4f5c"),
    (r"\u5168\u6743\u5904\u7406", "\u300c\u5168\u6743\u5904\u7406\u300d\u672a\u5217\u4e3e\u5177\u4f53\u52a8\u4f5c\uff0c\u5efa\u8bae\u6539\u4e3a\u5206\u9879\u5f0f"),
    (r"\u6709\u5173(?:\u7684)?(?:\u4e00\u5207)?(?:\u76f8\u5173)?(?:\u4e8b\u5b9c|\u4e8b\u52a1|\u4e8b\u9879)[\u3002;\uff1b]?$",
     "\u300c\u76f8\u5173\u4e8b\u5b9c\u300d\u672a\u6307\u660e\u8303\u56f4"),
]

NO_TERM = [
    (r"\u957f\u671f\u6709\u6548|\u6c38\u4e45\u6709\u6548|\u957f\u671f\u59d4\u6258",
     "\u300c\u957f\u671f\u6709\u6548\u300d\u5728\u5b9e\u52a1\u4e2d\u5e38\u88ab\u89c6\u4e3a\u7ea6\u5b9a\u4e0d\u660e\uff0c\u5efa\u8bae\u5199\u660e\u8d77\u6b62\u65e5\u671f"),
    (r"\u6709\u6548\u671f\u9650?\s*[:\uff1a]\s*(?:$|[\u3002;\uff1b])",
     "\u6709\u6548\u671f\u9650\u4e3a\u7a7a\uff0c\u9700\u5199\u660e\u8d77\u6b62\u65e5\u671f"),
]

DATE_RE = re.compile(r"(\d{4})\s*\u5e74\s*(\d{1,2})\s*\u6708\s*(\d{1,2})\s*\u65e5")
TERM_ANCHOR = re.compile(r"\u6709\u6548\u671f\u9650|\u6709\u6548\u671f|\u59d4\u6258\u671f\u9650|\u4ee3\u7406\u671f\u9650|\u671f\u9650")

PURPOSE_MATERIALS = [
    ("\u4e0d\u52a8\u4ea7", ["\u4e0d\u52a8\u4ea7\u6743\u8bc1\u4e66\u6216\u8d2d\u623f\u5408\u540c", "\u8eab\u4efd\u8bc1", "\u6237\u53e3\u672c",
              "\u7ed3\u5a5a\u8bc1\uff08\u5982\u6d89\u53ca\u592b\u59bb\u5171\u6709\uff09"]),
    ("\u623f\u4ea7", ["\u4e0d\u52a8\u4ea7\u6743\u8bc1\u4e66\u6216\u8d2d\u623f\u5408\u540c", "\u8eab\u4efd\u8bc1", "\u6237\u53e3\u672c",
             "\u7ed3\u5a5a\u8bc1\uff08\u5982\u6d89\u53ca\u592b\u59bb\u5171\u6709\uff09"]),
    ("\u8f66\u4f4d", ["\u8f66\u4f4d\u6743\u5c5e\u8bc1\u660e\u6216\u8d2d\u623f\u5408\u540c", "\u8eab\u4efd\u8bc1", "\u6237\u53e3\u672c"]),
    ("\u80a1\u6743", ["\u8425\u4e1a\u6267\u7167", "\u516c\u53f8\u7ae0\u7a0b", "\u80a1\u4e1c\u4f1a\u51b3\u8bae", "\u80a1\u6743\u8bc1\u6216\u51fa\u8d44\u8bc1\u660e"]),
    ("\u8f6c\u8ba9", ["\u6807\u7684\u5bf9\u5e94\u7684\u6743\u5c5e\u8bc1\u660e\u6750\u6599", "\u8eab\u4efd\u8bc1"]),
    ("\u6237\u7c4d", ["\u6237\u53e3\u672c", "\u8fc1\u79fb\u4e8b\u7531\u8bc1\u660e", "\u8eab\u4efd\u8bc1"]),
    ("\u533b\u7597", ["\u4f4f\u9662\u8bc1\u660e\u6216\u75c5\u60c5\u8bc1\u660e", "\u8eab\u4efd\u8bc1"]),
    ("\u4f4f\u9662", ["\u4f4f\u9662\u8bc1\u660e\u6216\u75c5\u60c5\u8bc1\u660e", "\u8eab\u4efd\u8bc1"]),
    ("\u6d89\u5916", ["\u62a4\u7167\u6216\u901a\u884c\u8bc1", "\u76ee\u6807\u56fd\u6216\u5730\u533a\u53d7\u7406\u673a\u6784\u7684\u5177\u4f53\u8981\u6c42\u6e05\u5355",
             "\u6309\u8981\u6c42\u7684\u7ffb\u8bd1\u4ef6"]),
    ("\u8bc9\u8bbc", ["\u4e00\u822c\u7531\u5f8b\u5e08\u6267\u4e1a\u4ee3\u7406\uff0c\u4e0d\u8d70\u59d4\u6258\u516c\u8bc1",
             "\u8bf7\u5148\u5411\u5f8b\u5e08\u6216\u6cd5\u9662\u7acb\u6848\u7a97\u53e3\u786e\u8ba4\u8981\u6c42"]),
    ("\u7ee7\u627f", ["\u4eb2\u5c5e\u5173\u7cfb\u8bc1\u660e", "\u88ab\u7ee7\u627f\u4eba\u6b7b\u4ea1\u8bc1\u660e", "\u9057\u4ea7\u8303\u56f4\u8bc1\u660e"]),
    ("\u76d1\u62a4", ["\u76d1\u62a4\u5173\u7cfb\u8bc1\u660e", "\u88ab\u76d1\u62a4\u4eba\u8eab\u4efd\u8bc1\u660e"]),
    ("\u52b3\u52a8", ["\u52b3\u52a8\u5408\u540c\u6216\u52b3\u52a8\u5173\u7cfb\u8bc1\u660e", "\u8eab\u4efd\u8bc1"]),
    ("\u793e\u4fdd", ["\u53c2\u4fdd\u6216\u793e\u4fdd\u5173\u7cfb\u8bc1\u660e", "\u8eab\u4efd\u8bc1"]),
    ("\u7a0e\u52a1", ["\u7eb3\u7a0e\u4eba\u8eab\u4efd\u8bc1\u660e", "\u7533\u62a5\u6216\u7f34\u8d39\u5bf9\u5e94\u7684\u6743\u5c5e\u6750\u6599"]),
    ("\u94f6\u884c", ["\u94f6\u884c\u8981\u6c42\u7684\u6388\u6743\u683c\u5f0f\uff08\u90e8\u5206\u94f6\u884c\u6709\u4e13\u7528\u8868\u683c\uff09", "\u8eab\u4efd\u8bc1",
             "\u8d26\u6237\u6216\u5b58\u5355\u4fe1\u606f"]),
    ("\u8bc1\u5238", ["\u8bc1\u5238\u8d26\u6237\u4fe1\u606f", "\u8bc1\u5238\u516c\u53f8\u8981\u6c42\u7684\u6388\u6743\u683c\u5f0f", "\u8eab\u4efd\u8bc1"]),
    ("\u5408\u540c", ["\u5408\u540c\u6216\u5408\u540c\u76f8\u5bf9\u65b9\u4fe1\u606f", "\u7b7e\u7ea6\u4e3b\u4f53\u8d44\u683c\u8bc1\u660e"]),
]

GENERAL_MATERIALS = [
    "\u59d4\u6258\u4eba\u8eab\u4efd\u8bc1\u539f\u4ef6\uff08\u516c\u8bc1\u5904\u9700\u6838\u9a8c\u539f\u4ef6\u5e76\u7559\u5b58\u590d\u5370\u4ef6\uff09",
    "\u53d7\u6258\u4eba\u8eab\u4efd\u8bc1\u4ef6\uff08\u539f\u4ef6\u6216\u590d\u5370\u4ef6\u89c6\u673a\u6784\u8981\u6c42\uff09",
    "\u59d4\u6258\u4e66\u6b63\u6587\uff08\u4e00\u822c\u8981\u6c42\u73b0\u573a\u624b\u5199\uff0c\u4e0d\u63d0\u524d\u6253\u5370\uff09",
    "\u4ee3\u7406\u4eba\u7b7e\u540d\u4e0e\u6309\u637a\u6307\u5370\uff08\u987b\u672c\u4eba\u5b8c\u6210\uff0c\u4e0d\u5f97\u4ee3\u7b7e\uff09",
]

PROXY_PATTERNS = [
    (r"\u4ee3\u7b7e|\u4ed6\u4eba\u4ee3\u4e3a\u7b7e\u540d|\u4ed6\u4eba\u4ee3\u7b7e|\u4ee3\u4e3a\u7b7e\u540d",
     "\u51fa\u73b0\u4ee3\u7b7e\u76f8\u5173\u8868\u8ff0\u3002\u59d4\u6258\u7b7e\u540d\u987b\u672c\u4eba\u5b8c\u6210\uff0c\u4ee3\u7b7e\u65e0\u6548\u3002"),
    (r"\u4ee3\u4e3a(?:\u637a\u5370|\u6309\u6307\u5370)|\u4ed6\u4eba\u4ee3(?:\u4e3a)?(?:\u637a\u5370|\u6309\u6307\u5370)",
     "\u51fa\u73b0\u4ee3\u4e3a\u637a\u5370\u76f8\u5173\u8868\u8ff0\u3002\u637a\u5370\u987b\u672c\u4eba\u5b8c\u6210\u3002"),
]

EXTRA_NOTES = [
    "\u5148\u786e\u8ba4\u662f\u5426\u771f\u7684\u9700\u8981\u516c\u8bc1\uff1a\u591a\u6570\u4e8b\u9879\u51ed\u59d4\u6258\u4e66\u539f\u4ef6\u52a0\u8eab\u4efd\u8bc1\u660e\u5373\u53ef\uff0c"
    "\u662f\u5426\u5fc5\u987b\u53d6\u51b3\u4e8e\u53d7\u7406\u673a\u6784\u4e0e\u76f8\u5bf9\u65b9\u7684\u8981\u6c42",
    "\u6d89\u53ca\u8bc9\u8bbc\u7684\u59d4\u6258\u4e66\u6709\u4e13\u95e8\u6cd5\u5f8b\u8981\u6c42\u4e0e\u683c\u5f0f\uff0c\u901a\u5e38\u4e0d\u8d70\u59d4\u6258\u516c\u8bc1\uff0c"
    "\u8bf7\u5148\u54a8\u8be2\u5f8b\u5e08\u6216\u6cd5\u9662\u7acb\u6848\u7a97\u53e3",
    "\u59d4\u6258\u4eba\u672c\u4eba\u65e0\u6cd5\u5230\u573a\u65f6\uff0c\u53ef\u80fd\u9700\u4e0a\u95e8\u89c1\u8bc1\u6216\u89c6\u9891\u89c1\u8bc1\uff0c\u5404\u673a\u6784\u505a\u6cd5\u4e0d\u540c\uff0c"
    "\u8bf7\u63d0\u524d\u7535\u8bdd\u54a8\u8be2",
    "\u53d7\u6258\u4eba\u987b\u5df2\u786e\u8ba4\u63a5\u53d7\u59d4\u6258\uff0c\u4e14\u8eab\u4efd\u8bc1\u4fe1\u606f\u4e0e\u59d4\u6258\u4e66\u5b8c\u5168\u4e00\u81f4\uff0c"
    "\u5426\u5219\u53ef\u80fd\u5230\u573a\u540e\u65e0\u6cd5\u8865\u6b63",
    "\u529e\u7406\u65f6\u9650\u4ee5\u53d7\u7406\u673a\u6784\u7b54\u590d\u4e3a\u51c6\uff1b\u91cd\u8981\u4e8b\u9879\u5efa\u8bae\u9884\u7559 1 \u5230 2 \u5468\uff0c"
    "\u5e76\u51c6\u5907\u4e0d\u9700\u8981\u516c\u8bc1\u7684\u5907\u9009\u7248\u672c",
    "\u6750\u6599\u6e05\u5355\u4ee5\u53d7\u7406\u673a\u6784\u5b9e\u9645\u8981\u6c42\u4e3a\u51c6\uff0c\u4e0d\u540c\u673a\u6784\u4e0e\u533a\u53bf\u8981\u6c42\u53ef\u80fd\u4e0d\u540c",
]


def norm(s):
    return (s or "").replace(" ", "").replace("\u3000", "").replace("\t", "")


def check_elements(text):
    t = norm(text)
    rows = []
    for key, cn, pat, hint in ELEMENTS:
        if re.search(pat, t, re.I):
            rows.append((key, cn, OK, "\u5df2\u8bc6\u522b"))
        else:
            rows.append((key, cn, MISS, "\u672a\u5728\u6587\u672c\u4e2d\u8bc6\u522b\u5230\u8be5\u8981\u7d20\u3002" + hint))
    return rows


def check_vague(text):
    t = norm(text)
    hits = []
    for pat, why in VAGUE_SCOPE:
        m = re.search(pat, t)
        if m:
            hits.append(("\u6743\u9650\u8868\u8ff0\u7b3c\u7edf", VAGUE,
                         "\u547d\u4e2d\u8868\u8ff0\u300c%s\u300d\uff1a%s" % (m.group(0)[:20], why)))
    return hits


def term_section(text):
    """\u53d6\u671f\u9650\u9644\u8fd1\u7684\u6587\u672c\u7247\u6bb5\uff0c\u907f\u514d\u628a\u51fa\u751f\u65e5\u671f\u5f53\u6210\u671f\u9650\u65e5\u671f\u3002"""
    t = norm(text)
    m = TERM_ANCHOR.search(t)
    if m:
        return t[m.start():]
    return t


def check_term(text):
    t = norm(text)
    hits = []
    for pat, why in NO_TERM:
        m = re.search(pat, t)
        if m:
            hits.append(("\u6709\u6548\u671f\u9650\u5199\u6cd5", VAGUE,
                         "\u547d\u4e2d\u8868\u8ff0\u300c%s\u300d\uff1a%s" % (m.group(0)[:20], why)))
    dates = DATE_RE.findall(term_section(text))
    if not dates:
        hits.append(("\u671f\u9650\u65e5\u671f\u7f3a\u5931", MISS,
                     "\u6709\u6548\u671f\u9650\u5904\u672a\u8bc6\u522b\u5230\u300cYYYY \u5e74 MM \u6708 DD \u65e5\u300d\u5f62\u5f0f\u7684\u65e5\u671f\uff0c"
                     "\u671f\u9650\u5fc5\u987b\u5177\u4f53\u5230\u65e5\u671f"))
        return hits
    if len(dates) < 2:
        hits.append(("\u671f\u9650\u65e5\u671f\u4e0d\u5b8c\u6574", MISS,
                     "\u6709\u6548\u671f\u9650\u5904\u4ec5\u8bc6\u522b\u5230 1 \u4e2a\u65e5\u671f\u3002"
                     "\u5e94\u5199\u660e\u8d77\u6b62\u4e24\u4e2a\u65e5\u671f\uff0c\u5982"
                     "\u300c\u81ea 2026 \u5e74 10 \u6708 11 \u65e5\u81f3 2027 \u5e74 10 \u6708 10 \u65e5\u300d"))
        return hits
    try:
        y1, m1, d1 = [int(x) for x in dates[0]]
        y2, m2, d2 = [int(x) for x in dates[1]]
    except (ValueError, IndexError):
        return hits
    if (y2, m2, d2) <= (y1, m1, d1):
        hits.append(("\u671f\u9650\u903b\u8f91\u9519\u8bef", MISS, "\u7ec8\u6b62\u65e5\u671f\u4e0d\u665a\u4e8e\u8d77\u59cb\u65e5\u671f\uff0c\u671f\u9650\u65e0\u6548"))
    elif ((y2 * 12 + m2) - (y1 * 12 + m1)) > 60:
        hits.append(("\u671f\u9650\u8fc7\u957f", INFO,
                     "\u6388\u6743\u671f\u9650\u8d85\u8fc7 5 \u5e74\u3002\u671f\u9650\u8fc7\u957f\u4f1a\u589e\u52a0\u540e\u7eed\u4e89\u8bae\u98ce\u9669\uff0c"
                     "\u5efa\u8bae\u6309\u4e8b\u9879\u5468\u671f\u8bbe\u5b9a\u5e76\u5728\u5230\u671f\u524d\u91cd\u65b0\u59d4\u6258"))
    return hits


def check_signature(text):
    t = norm(text)
    hits = []
    for pat, why in PROXY_PATTERNS:
        if re.search(pat, t):
            hits.append(("\u7b7e\u540d\u65b9\u5f0f", MISS, why))
    return hits


def materials_for(purpose):
    p = purpose or ""
    extra = []
    seen = set()
    for key, mats in PURPOSE_MATERIALS:
        if key in p and key not in seen:
            seen.add(key)
            extra.append(("%s\u7c7b\u4e8b\u9879\u8ffd\u52a0\u6750\u6599" % key, list(mats)))
    return GENERAL_MATERIALS, extra


def worst(levels):
    lv = OK
    for x in levels:
        if LEVEL_ORDER.get(x, 0) > LEVEL_ORDER.get(lv, 0):
            lv = x
    return lv


def build(text, purpose):
    rows = check_elements(text)
    issues = check_vague(text) + check_term(text) + check_signature(text)
    gen, extra = materials_for(purpose)
    if not norm(text or ""):
        overall = MISS
        issues = issues + [("\u6587\u672c\u4e3a\u7a7a", MISS,
                           "\u672a\u8bfb\u53d6\u5230\u4efb\u4f55\u59d4\u6258\u4e66\u5185\u5bb9\uff0c\u65e0\u6cd5\u6838\u67e5")]
    else:
        overall = worst([r[2] for r in rows] + [i[1] for i in issues])
    return {
        "overall": overall,
        "purpose": purpose or "\u672a\u6307\u5b9a",
        "elements": [{"key": k, "name": n, "level": lv, "note": note}
                     for k, n, lv, note in rows],
        "issues": [{"name": n, "level": lv, "note": note}
                   for n, lv, note in issues],
        "general_materials": list(gen),
        "extra_materials": [{"group": g, "items": it} for g, it in extra],
        "notes": list(EXTRA_NOTES),
    }


SCOPE_TEMPLATE = """\u4ee3\u7406\u6743\u9650\uff1a
1. \u4ee3\u4e3a\u7b7e\u7f72\u4e0e\u672c\u6b21\u4e8b\u9879\u76f8\u5173\u7684\u5408\u540c\u3001\u534f\u8bae\u53ca\u6587\u4ef6\uff1b
2. \u4ee3\u4e3a\u529e\u7406\u672c\u6b21\u4e8b\u9879\u6d89\u53ca\u7684\u624b\u7eed\u3001\u6750\u6599\u63d0\u4ea4\u4e0e\u9886\u53d6\uff1b
3. \u4ee3\u4e3a\u63a5\u6536\u4e0e\u672c\u6b21\u4e8b\u9879\u76f8\u5173\u7684\u6b3e\u9879\uff08\u4ec5\u9650 ______ \u5143\uff09\uff1b
4. \u4ee3\u4e3a\u529e\u7406\u672c\u6b21\u4e8b\u9879\u6d89\u53ca\u7684\u5176\u4ed6\u5fc5\u8981\u624b\u7eed\u3002

\u4ee5\u4e0b\u4e8b\u9879\u4e0d\u5728\u6388\u6743\u8303\u56f4\u5185\uff08\u672c\u59d4\u6258\u4e66\u4e0d\u6388\u4e88\uff09\uff1a
1. \u8f6c\u8ba9\u3001\u51fa\u79df\u3001\u51fa\u552e\u4e0a\u8ff0\u6807\u7684\uff1b
2. \u8bbe\u5b9a\u62b5\u62bc\u3001\u8d28\u62bc\uff1b
3. \u529e\u7406\u4e0e\u672c\u4e8b\u9879\u65e0\u5173\u7684\u767b\u8bb0\u6216\u53d8\u66f4\uff1b
4. \u518d\u59d4\u6258\u7b2c\u4e09\u4eba\uff08\u9664\u975e\u53e6\u6709\u4e66\u9762\u7ea6\u5b9a\uff09\u3002"""


def render_md(r):
    L = []
    L.append("# \u6388\u6743\u59d4\u6258\u4e66\u8981\u7d20\u6838\u67e5\u62a5\u544a")
    L.append("")
    L.append("- \u4ee3\u7406\u4e8b\u9879: %s" % r["purpose"])
    L.append("- \u7efc\u5408\u7ed3\u8bba: **%s**" % r["overall"])
    L.append("")
    L.append("## \u4e00 \u516d\u9879\u5fc5\u5907\u8981\u7d20")
    L.append("")
    L.append("| \u8981\u7d20 | \u5224\u5b9a | \u8bf4\u660e |")
    L.append("|---|---|---|")
    for it in r["elements"]:
        L.append("| %s | %s | %s |" % (it["name"], it["level"], it["note"]))
    L.append("")
    L.append("## \u4e8c \u9700\u4fee\u6539\u7684\u95ee\u9898")
    L.append("")
    if r["issues"]:
        for it in r["issues"]:
            L.append("- **[%s] %s**\uff1a%s" % (it["level"], it["name"], it["note"]))
    else:
        L.append("- \u672a\u53d1\u73b0\u660e\u663e\u95ee\u9898\uff0c\u4f46\u4ecd\u9700\u672c\u4eba\u5230\u573a\u7b7e\u7f72\u5e76\u7531\u53d7\u7406\u673a\u6784\u6700\u7ec8\u786e\u8ba4")
    L.append("")
    L.append("## \u4e09 \u6743\u9650\u8303\u56f4\u63a8\u8350\u5199\u6cd5")
    L.append("")
    L.append("```text")
    L.append(SCOPE_TEMPLATE)
    L.append("```")
    L.append("")
    L.append("## \u56db \u6750\u6599\u6e05\u5355")
    L.append("")
    L.append("### \u901a\u7528\u6750\u6599")
    L.append("")
    for m in r["general_materials"]:
        L.append("- [ ] %s" % m)
    L.append("")
    if r["extra_materials"]:
        L.append("### \u8ffd\u52a0\u6750\u6599")
        L.append("")
        for g in r["extra_materials"]:
            L.append("**%s**" % g["group"])
            L.append("")
            for m in g["items"]:
                L.append("- [ ] %s" % m)
            L.append("")
    L.append("## \u4e94 \u529e\u7406\u524d\u540e\u6ce8\u610f\u4e8b\u9879")
    L.append("")
    for t in r["notes"]:
        L.append("- %s" % t)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> \u811a\u672c\u53ea\u505a\u6587\u672c\u8981\u7d20\u68c0\u67e5\u3002\u5b83\u65e0\u6cd5\u5224\u65ad\u5185\u5bb9\u662f\u5426\u771f\u5b9e\u3001\u662f\u5426\u4e0e\u5b9e\u9645\u76f8\u7b26\uff0c")
    L.append("> \u4e5f\u4e0d\u80fd\u66ff\u4ee3\u516c\u8bc1\u5458\u7684\u9762\u8be2\u3002**\u6700\u7ec8\u80fd\u5426\u53d7\u7406\u7531\u516c\u8bc1\u673a\u6784\u51b3\u5b9a\u3002**")
    return "\n".join(L) + "\n"


SAMPLE_GOOD = """\u6388\u6743\u59d4\u6258\u4e66

\u59d4\u6258\u4eba\uff1a\u5f20\u4e09\uff0c\u7537\uff0c1985\u5e743\u670812\u65e5\u51fa\u751f\uff0c\u516c\u6c11\u8eab\u4efd\u53f7\u7801 110101198503121234\uff0c
\u4f4f\u5317\u4eac\u5e02\u671d\u9633\u533a\u67d0\u5c0f\u533a 1 \u53f7 1 \u5355\u5143 101 \u5ba4\uff0c\u8054\u7cfb\u7535\u8bdd 13800000000\u3002

\u53d7\u6258\u4eba\uff1a\u674e\u56db\uff0c\u7537\uff0c1990\u5e746\u67081\u65e5\u51fa\u751f\uff0c\u516c\u6c11\u8eab\u4efd\u53f7\u7801 110101199006011234\uff0c
\u4f4f\u5317\u4eac\u5e02\u6d77\u6dc0\u533a\u67d0\u8def 2 \u53f7\uff0c\u8054\u7cfb\u7535\u8bdd 13900000000\u3002

\u4ee3\u7406\u4e8b\u9879\uff1a\u4ee3\u4e3a\u529e\u7406\u4f4d\u4e8e\u5317\u4eac\u5e02\u671d\u9633\u533a\u67d0\u8def 9 \u53f7\u4e0d\u52a8\u4ea7\u7684\u8f6c\u79fb\u767b\u8bb0\u624b\u7eed\u3002

\u4ee3\u7406\u6743\u9650\uff1a
1. \u4ee3\u4e3a\u7b7e\u7f72\u4e0e\u672c\u6b21\u4e8b\u9879\u76f8\u5173\u7684\u5408\u540c\u3001\u534f\u8bae\u53ca\u6587\u4ef6\uff1b
2. \u4ee3\u4e3a\u529e\u7406\u672c\u6b21\u4e8b\u9879\u6d89\u53ca\u7684\u624b\u7eed\u3001\u6750\u6599\u63d0\u4ea4\u4e0e\u9886\u53d6\uff1b
3. \u4ee3\u4e3a\u9886\u53d6\u672c\u6b21\u4e8b\u9879\u6d89\u53ca\u7684\u8bc1\u4ef6\u3002
\u4ee5\u4e0b\u4e8b\u9879\u4e0d\u5728\u6388\u6743\u8303\u56f4\u5185\uff1a\u672c\u59d4\u6258\u4e66\u4e0d\u6388\u4e88\u8f6c\u8ba9\u3001\u8bbe\u5b9a\u62b5\u62bc\u53ca\u518d\u59d4\u6258\u7b2c\u4e09\u4eba\u7684\u6743\u9650\u3002

\u6709\u6548\u671f\u9650\uff1a\u81ea 2026 \u5e74 10 \u6708 11 \u65e5 \u81f3 2027 \u5e74 10 \u6708 10 \u65e5\u3002

\u59d4\u6258\u4eba\u7b7e\u540d\uff1a\u5f20\u4e09
\u637a\u5370\uff1a\u5f20\u4e09
"""

SAMPLE_VAGUE = """\u59d4\u6258\u4e66
\u59d4\u6258\u4eba\uff1a\u738b\u4e94
\u53d7\u6258\u4eba\uff1a\u8d75\u516d
\u4ee3\u7406\u4e8b\u9879\uff1a\u529e\u7406\u623f\u4ea7\u76f8\u5173\u624b\u7eed
\u4ee3\u7406\u6743\u9650\uff1a\u5168\u6743\u4ee3\u7406\u4e00\u5207\u4e8b\u52a1
\u6709\u6548\u671f\u9650\uff1a\u957f\u671f\u6709\u6548
"""

SAMPLE_PARTIAL = """\u59d4\u6258\u4e66
\u59d4\u6258\u4eba\uff1a\u5b59\u4e03\uff0c\u7537\uff0c\u516c\u6c11\u8eab\u4efd\u53f7\u7801 110101199001011111
\u4ee3\u7406\u4e8b\u9879\uff1a\u529e\u7406\u80a1\u6743\u8f6c\u8ba9
\u6709\u6548\u671f\u9650\uff1a\u81ea 2026 \u5e74 10 \u6708 11 \u65e5\u81f3 2027 \u5e74 10 \u6708 10 \u65e5
\u59d4\u6258\u4eba\u7b7e\u540d\uff1a\u5b59\u4e03
"""

SAMPLE_EMPTY = "   "

SAMPLE_BADTERM = """\u59d4\u6258\u4e66
\u59d4\u6258\u4eba\uff1a\u5b59\u4e03\uff0c\u516c\u6c11\u8eab\u4efd\u53f7\u7801 110101199001011111
\u53d7\u6258\u4eba\uff1a\u5468\u516b\uff0c\u516c\u6c11\u8eab\u4efd\u53f7\u7801 110101199001012222
\u4ee3\u7406\u4e8b\u9879\uff1a\u529e\u7406\u80a1\u6743\u8f6c\u8ba9\u624b\u7eed
\u4ee3\u7406\u6743\u9650\uff1a\u7b7e\u7f72\u80a1\u6743\u8f6c\u8ba9\u534f\u8bae\u5e76\u529e\u7406\u53d8\u66f4\u767b\u8bb0
\u6709\u6548\u671f\u9650\uff1a\u81ea 2027 \u5e74 10 \u6708 11 \u65e5\u81f3 2026 \u5e74 10 \u6708 10 \u65e5
\u59d4\u6258\u4eba\u7b7e\u540d\uff1a\u5b59\u4e03
\u637a\u5370\uff1a\u5b59\u4e03
"""

SAMPLE_ONEDATE = """\u59d4\u6258\u4e66
\u59d4\u6258\u4eba\uff1a\u5434\u4e5d\uff0c\u516c\u6c11\u8eab\u4efd\u53f7\u7801 110101199001013333
\u53d7\u6258\u4eba\uff1a\u90d1\u5341\uff0c\u516c\u6c11\u8eab\u4efd\u53f7\u7801 110101199001014444
\u4ee3\u7406\u4e8b\u9879\uff1a\u529e\u7406\u793e\u4fdd\u5173\u7cfb\u8f6c\u79fb
\u4ee3\u7406\u6743\u9650\uff1a\u4ee3\u4e3a\u63d0\u4ea4\u6750\u6599\u5e76\u9886\u53d6\u7ed3\u679c
\u6709\u6548\u671f\u9650\uff1a\u81ea 2026 \u5e74 10 \u6708 11 \u65e5\u8d77
\u59d4\u6258\u4eba\u7b7e\u540d\uff1a\u5434\u4e5d
\u637a\u5370\uff1a\u5434\u4e5d
"""

SAMPLE_PROXY_SIGN = """\u6388\u6743\u59d4\u6258\u4e66
\u59d4\u6258\u4eba\uff1a\u5434\u4e5d\uff0c\u516c\u6c11\u8eab\u4efd\u53f7\u7801 110101199001013333
\u53d7\u6258\u4eba\uff1a\u90d1\u5341\uff0c\u516c\u6c11\u8eab\u4efd\u53f7\u7801 110101199001014444
\u4ee3\u7406\u4e8b\u9879\uff1a\u529e\u7406\u6237\u7c4d\u8fc1\u79fb
\u4ee3\u7406\u6743\u9650\uff1a\u4ee3\u4e3a\u63d0\u4ea4\u6750\u6599\uff0c\u9886\u53d6\u8bc1\u4ef6
\u6709\u6548\u671f\u9650\uff1a\u81ea 2026 \u5e74 10 \u6708 11 \u65e5 \u81f3 2027 \u5e74 10 \u6708 10 \u65e5
\u59d4\u6258\u4eba\u7b7e\u540d\uff1a\u7531\u4ed6\u4eba\u4ee3\u7b7e
\u637a\u5370\uff1a\u7531\u4ed6\u4eba\u4ee3\u4e3a\u637a\u5370
"""


def selftest():
    res = []
    ok = True

    def ck(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        res.append("%s %s got=%r want=%r"
                   % ("PASS" if good else "FAIL", name, got, want))

    # 1. \u516d\u8981\u7d20\u9f50\u5168
    g = check_elements(SAMPLE_GOOD)
    gd = dict((k, lv) for k, n, lv, note in g)
    ck("good_count", len(g), 8)
    ck("good_all_ok", set(gd.values()), set([OK]))
    ck("good_principal", gd.get("principal"), OK)
    ck("good_principal_id", gd.get("principal_id"), OK)
    ck("good_agent", gd.get("agent"), OK)
    ck("good_agent_id", gd.get("agent_id"), OK)
    ck("good_matter", gd.get("matter"), OK)
    ck("good_scope", gd.get("scope"), OK)
    ck("good_term", gd.get("term"), OK)
    ck("good_sign", gd.get("sign"), OK)

    # 2. \u7f3a\u5931\u8981\u7d20
    p = check_elements(SAMPLE_PARTIAL)
    pd = dict((k, lv) for k, n, lv, note in p)
    ck("part_agent_missing", pd.get("agent"), MISS)
    ck("part_scope_missing", pd.get("scope"), MISS)
    ck("part_principal_ok", pd.get("principal"), OK)
    ck("part_matter_ok", pd.get("matter"), OK)
    pnote = dict((k, note) for k, n, lv, note in p)
    ck("part_hint_agent", "\u9700\u5199\u660e\u53d7\u6258\u4eba\u59d3\u540d" in pnote.get("agent", ""), True)
    ck("part_agent_id_from_principal_number", pd.get("agent_id"), OK)

    # 3. \u7b3c\u7edf\u6743\u9650
    v = check_vague(SAMPLE_VAGUE)
    ck("vague_hit", len(v) >= 1, True)
    ck("vague_level", all(x[1] == VAGUE for x in v), True)
    ck("vague_note", "\u5206\u9879" in " ".join(x[2] for x in v), True)
    ck("vague_good_empty", check_vague(SAMPLE_GOOD), [])

    # 4. \u671f\u9650
    ck("term_good_empty", check_term(SAMPLE_GOOD), [])
    tv = check_term(SAMPLE_VAGUE)
    ck("term_long_flag", any("\u957f\u671f\u6709\u6548" in x[2] for x in tv), True)
    ck("term_nodate_flag", any(x[1] == MISS for x in tv), True)
    tb = check_term(SAMPLE_BADTERM)
    ck("term_bad_logic",
       any("\u7ec8\u6b62\u65e5\u671f\u4e0d\u665a\u4e8e\u8d77\u59cb\u65e5\u671f" in x[2] for x in tb), True)
    to = check_term(SAMPLE_ONEDATE)
    ck("term_one_date",
       any("\u4ec5\u8bc6\u522b\u5230 1 \u4e2a\u65e5\u671f" in x[2] for x in to), True)
    ck("term_birth_not_counted",
       any("1985" in x[2] for x in check_term(SAMPLE_GOOD)), False)

    # 5. \u4ee3\u7b7e\u8bc6\u522b
    ts = check_signature(SAMPLE_PROXY_SIGN)
    ck("sign_proxy_count", len(ts), 2)
    ck("sign_proxy_miss", all(x[1] == MISS for x in ts), True)
    ck("sign_good_empty", check_signature(SAMPLE_GOOD), [])

    # 6. \u6750\u6599\u6620\u5c04
    gen, ex = materials_for("\u4e0d\u52a8\u4ea7\u8f6c\u79fb\u767b\u8bb0")
    ck("mat_general_len", len(gen), 4)
    ck("mat_realestate",
       any("\u4e0d\u52a8\u4ea7\u6743\u8bc1\u4e66" in i for _g, it in ex for i in it), True)
    _g2, ex2 = materials_for("\u80a1\u6743\u8f6c\u8ba9")
    ck("mat_equity",
       any("\u8425\u4e1a\u6267\u7167" in i for _g, it in ex2 for i in it), True)
    _g3, ex3 = materials_for("\u65e0\u5173\u4e8b\u9879")
    ck("mat_none", ex3, [])
    _g4, ex4 = materials_for("\u80a1\u6743\u8f6c\u8ba9\u4e0e\u5bf9\u5916\u8f6c\u8ba9")
    ck("mat_no_dup", len(ex4), 2)

    # 7. \u7efc\u5408\u5224\u5b9a
    ck("rep_good", build(SAMPLE_GOOD, "\u4e0d\u52a8\u4ea7\u8f6c\u79fb\u767b\u8bb0")["overall"], OK)
    ck("rep_vague", build(SAMPLE_VAGUE, "\u623f\u4ea7")["overall"], MISS)
    ck("rep_part", build(SAMPLE_PARTIAL, "\u80a1\u6743\u8f6c\u8ba9")["overall"], MISS)
    ck("rep_empty", build(SAMPLE_EMPTY, "")["overall"], MISS)
    ck("rep_proxy", build(SAMPLE_PROXY_SIGN, "\u6237\u7c4d\u8fc1\u79fb")["overall"], MISS)
    ck("rep_badterm", build(SAMPLE_BADTERM, "\u80a1\u6743\u8f6c\u8ba9")["overall"], MISS)
    ck("rep_onedate", build(SAMPLE_ONEDATE, "\u793e\u4fdd")["overall"], MISS)
    ck("level_order", LEVEL_ORDER[MISS] > LEVEL_ORDER[VAGUE], True)
    ck("level_order2", LEVEL_ORDER[VAGUE] > LEVEL_ORDER[INFO], True)
    ck("worst_fn", worst([OK, MISS, VAGUE]), MISS)

    # 8. \u6e32\u67d3
    md = render_md(build(SAMPLE_PARTIAL, "\u80a1\u6743\u8f6c\u8ba9"))
    ck("md_header", md.startswith("# "), True)
    ck("md_table", "| \u8981\u7d20 | \u5224\u5b9a |" in md, True)
    ck("md_materials", "\u6750\u6599\u6e05\u5355" in md, True)
    ck("md_notes", "\u529e\u7406\u524d\u540e\u6ce8\u610f\u4e8b\u9879" in md, True)
    ck("md_scope", "\u4ee5\u4e0b\u4e8b\u9879\u4e0d\u5728\u6388\u6743\u8303\u56f4\u5185" in md, True)
    js = json.loads(json.dumps(build(SAMPLE_GOOD, "\u4e0d\u52a8\u4ea7"), ensure_ascii=False))
    ck("json_keys", sorted(js.keys()),
       ["elements", "extra_materials", "general_materials", "issues",
        "notes", "overall", "purpose"])
    ck("json_notes_len", len(js["notes"]) >= 5, True)
    ck("json_elements_len", len(js["elements"]), 8)

    # 9. \u5e38\u91cf\u8868\u5b8c\u6574\u6027
    ck("elements_len", len(ELEMENTS), 8)
    ck("purpose_kinds", len(PURPOSE_MATERIALS) >= 15, True)
    ck("proxy_pat_len", len(PROXY_PATTERNS), 2)

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--purpose", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        rc = selftest()
        outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_selftest_result.txt")
        open(outp, "w", encoding="utf-8").write(
            "SELFTEST %s\nresult: %s\n"
            % ("OK" if rc == 0 else "FAILED", "OK" if rc == 0 else "FAILED"))
        return rc

    if not a.file or not os.path.exists(a.file):
        print("ERROR --file does not exist")
        return 2
    text = open(a.file, "r", encoding="utf-8", errors="replace").read()
    r = build(text, a.purpose)
    body = (render_md(r) if a.format == "md"
            else json.dumps(r, ensure_ascii=False, indent=2))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())