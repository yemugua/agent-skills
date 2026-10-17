# -*- coding: utf-8 -*-
"""React \u7ec4\u4ef6\u91cd\u6e32\u67d3\u98ce\u9669\u9759\u6001\u626b\u63cf\u3002

\u7528\u6cd5:
  python react_rerender_scan.py --selftest
  python react_rerender_scan.py --file src/List.jsx
  python react_rerender_scan.py --dir src --json
"""
import argparse
import io
import json
import os
import re
import sys

FAILS = []

SCAN_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs")
SKIP_DIRS = ("node_modules", "build", "dist", "coverage", ".git", "__tests__", ".next", "out")

SEVERITY_ORDER = {"\u4e25\u91cd": 0, "\u9519\u8bef": 1, "\u8b66\u793a": 2, "\u63d0\u793a": 3, "\u597d": 4}

RX_TAG = re.compile(r"<\s*([A-Z][\w.]*)")
RX_INLINE_OBJ = re.compile(r"([A-Za-z_][\w]*)=\s*\{\{")
RX_INLINE_ARR = re.compile(r"([A-Za-z_][\w]*)=\s*\{\s*\[")
RX_ARROW_PROP = re.compile(r"([A-Za-z_][\w]*)=\s*\{\s*(\([^)]*\)|[\w$.]+)\s*=>")
RX_KEY_INDEX = re.compile(r"key\s*=\s*\{\s*(index|i|idx|idx2|position|pos)\s*\}")
RX_KEY_RANDOM = re.compile(r"key\s*=\s*\{[^}]*(Math\.random|Date\.now|uuid|nanoid)")
RX_PROVIDER = re.compile(r"<\s*([A-Z][\w.]*)\.Provider[^>]*value\s*=\s*\{\{")
RX_PROVIDER_VAL = re.compile(r"value\s*=\s*\{\{")
RX_NONPURE = re.compile(r"(new Date\s*\(\s*\)|Date\.now\s*\(\s*\)|Math\.random\s*\(\s*\)|JSON\.parse\s*\()")
RX_MAP = re.compile(r"\.map\s*\(")
RX_HOOK = re.compile(r"\b(useMemo|useCallback|useEffect)\s*\(")
RX_STATE = re.compile(r"const\s*\[\s*([A-Za-z_$][\w$]*)\s*,\s*set\w+\s*\]\s*=\s*useState")
RX_PROPS_DESTRUCT = re.compile(r"const\s*\{\s*([^}]*)\}\s*=\s*(props| arguments)")
RX_PROPS_DOT = re.compile(r"\b(props|-data|params)\.([A-Za-z_$][\w$]*)")
RX_PARAM_FN = re.compile(r"function\s+[\w$]*\s*\(\s*\{([^}]*)\}")
RX_PARAM_ARROW = re.compile(r"=\s*\(\s*\{([^}]*)\}")
RX_INNER_COMPONENT = re.compile(r"^(?P<ind>\s{2,})(?:const|let)\s+(?P<name>[A-Z][\w$]*)\s*=\s*(?:\(|function)")
RX_MEMO_WRAP = re.compile(r"memo\s*\(\s*%s\b")


def ck(label, cond):
    if not cond:
        FAILS.append(label)
    return bool(cond)


def write_result(path):
    lines = ["SELFTEST %s" % ("OK" if not FAILS else "FAILED")]
    for f in FAILS:
        lines.append("  FAILED: %s" % f)
    io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


def span_from(text, open_idx):
    """\u8fd4\u56de\u4ece open_idx \u7684 '(' \u8d77\u5230\u5339\u914d ')' \u7684\u6587\u672c\u3002"""
    depth = 0
    for j in range(open_idx, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx:j + 1]
    return text[open_idx:]


def map_context_lines(text):
    """\u8ba1\u7b97\u88ab .map( \u56de\u8c03\u8986\u76d6\u7684\u884c\u53f7\u96c6\u5408\uff0c\u7528\u4e8e\u8bc6\u522b\u5217\u8868\u6e32\u67d3\u3002"""
    lines_out = set()
    pos = 0
    while True:
        i = text.find(".map(", pos)
        if i < 0:
            break
        j = text.find("(", i)
        if j < 0:
            break
        seg = span_from(text, j)
        if not seg:
            break
        begin = text.count("\n", 0, i)
        end = begin + seg.count("\n")
        for n in range(begin, end + 1):
            lines_out.add(n)
        pos = i + 5
    return lines_out


def collect_outer_names(text):
    """\u6536\u96c6 state \u4e0e props \u7684\u540d\u5b57\uff0c\u7528\u4e8e\u5224\u5b9a Hook \u4f9d\u8d56\u7f3a\u5931\u3002"""
    names = set()
    for m in RX_STATE.finditer(text):
        names.add(m.group(1))
    for m in RX_PROPS_DESTRUCT.finditer(text):
        for p in m.group(1).split(","):
            p = p.strip().split(":")[0].strip()
            if p:
                names.add(p)
    for pat in (RX_PARAM_FN, RX_PARAM_ARROW):
        for m in pat.finditer(text):
            for p in m.group(1).split(","):
                p = p.strip().split(":")[0].strip()
                if p:
                    names.add(p)
    for m in RX_PROPS_DOT.finditer(text):
        names.add(m.group(2))
    return names


def extract_hook_calls(text):
    """\u63d0\u53d6 useMemo/useCallback/useEffect \u8c03\u7528\u7684\u5b8c\u6574\u7247\u6bb5\u3002"""
    out = []
    for m in RX_HOOK.finditer(text):
        j = text.find("(", m.end() - 1)
        if j < 0:
            continue
        seg = span_from(text, j)
        if not seg:
            continue
        start_line = text.count("\n", 0, m.start())
        end_line = start_line + seg.count("\n")
        out.append({"hook": m.group(1), "text": seg,
                    "start": start_line, "end": end_line})
    return out


def check_hook_deps(text):
    """\u7a7a\u4f9d\u8d56\u4f46\u95ed\u5305\u5f15\u7528\u4e86 state/props \u7684 Hook\u3002"""
    issues = []
    names = collect_outer_names(text)
    if not names:
        return issues
    for call in extract_hook_calls(text):
        m = re.search(r",\s*\[([^\]]*)\]\s*\)?\s*$", call["text"].rstrip())
        if not m:
            continue
        deps = [x.strip() for x in m.group(1).split(",") if x.strip()]
        if deps:
            continue
        body = call["text"][:m.start()]
        used = sorted(n for n in names if re.search(r"(?<![.\w$])%s(?![$\w])" % re.escape(n), body))
        if used:
            issues.append((call["start"], "\u63d0\u793a",
                           "%s \u4f9d\u8d56\u6570\u7ec4\u4e3a\u7a7a\u4f46\u95ed\u5305\u5f15\u7528\u4e86 %s\uff0c\u53ef\u80fd\u6f0f\u4f9d\u8d56\u62ff\u5230\u65e7\u503c" % (
                               call["hook"], ", ".join(used[:3]))))
    return issues


def scan_file(text, path="<inline>"):
    findings = []
    lines = text.splitlines()
    map_lines = map_context_lines(text)
    memo_names = set()
    for m in re.finditer(r"memo\s*\(\s*([A-Z][\w$]*)", text):
        memo_names.add(m.group(1))
    for m in re.finditer(r"([A-Z][\w$]*)\s*=\s*(?:React\.)?memo\s*\(", text):
        memo_names.add(m.group(1))

    for lineno, raw in enumerate(lines):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        code = line
        if "//" in code:
            head = code.split("//", 1)[0]
        else:
            head = code
        tags = RX_TAG.findall(code)
        has_component_tag = bool(tags)

        if RX_KEY_RANDOM.search(code):
            findings.append((lineno, "\u4e25\u91cd",
                             "key \u4f7f\u7528\u4e86\u968f\u673a/\u65f6\u95f4\u503c\uff0c\u6bcf\u6b21\u6e32\u67d3\u90fd\u662f\u65b0 key\uff0c\u6574\u68f5\u5b50\u6811\u4f1a\u5378\u8f7d\u91cd\u5efa"))
        elif RX_KEY_INDEX.search(code):
            findings.append((lineno, "\u9519\u8bef",
                             "key \u4f7f\u7528\u4e86\u6570\u7ec4\u7d22\u5f15\uff0c\u5217\u8868\u987a\u5e8f\u53d8\u5316\u65f6\u7ec4\u4ef6 state \u4f1a\u4e32\u4f4d"))

        if has_component_tag and RX_INLINE_OBJ.search(head):
            prop = RX_INLINE_OBJ.search(head).group(1)
            findings.append((lineno, "\u4e25\u91cd",
                             "\u7ec4\u4ef6\u5c5e\u6027 %s \u4f20\u4e86\u5185\u8054\u5bf9\u8c61\u5b57\u9762\u91cf\uff0c\u6bcf\u6b21\u6e32\u67d3\u90fd\u662f\u65b0\u5f15\u7528\uff0cmemo \u4f1a\u5931\u6548" % prop))
        if has_component_tag and RX_INLINE_ARR.search(head):
            prop = RX_INLINE_ARR.search(head).group(1)
            findings.append((lineno, "\u9519\u8bef",
                             "\u7ec4\u4ef6\u5c5e\u6027 %s \u4f20\u4e86\u5185\u8054\u6570\u7ec4\u5b57\u9762\u91cf\uff0c\u6bcf\u6b21\u6e32\u67d3\u90fd\u662f\u65b0\u5f15\u7528\uff0cmemo \u4f1a\u5931\u6548" % prop))

        if RX_PROVIDER.search(code) or (("Provider" in code) and RX_PROVIDER_VAL.search(head)):
            findings.append((lineno, "\u9519\u8bef",
                             "Provider \u7684 value \u7528\u4e86\u5185\u8054\u5bf9\u8c61\uff0cContext \u66f4\u65b0\u4f1a\u8ba9\u6240\u6709\u6d88\u8d39\u8005\u91cd\u6e32\u67d3"))

        if lineno in map_lines:
            for tag in tags:
                base = tag.split(".")[0]
                if base in memo_names:
                    continue
                if re.search(r"<\s*%s\b" % re.escape(base), code) and code.count("<") <= 2:
                    findings.append((lineno, "\u63d0\u793a",
                                     "\u5217\u8868\u9879\u7ec4\u4ef6 %s \u672a\u88ab memo \u5305\u88f9\uff0c\u7236\u7ea7\u91cd\u6e32\u67d3\u65f6\u6574\u5217\u8868\u8ddf\u7740\u6e32\u67d3" % base))
                    break

        mnp = RX_NONPURE.search(head)
        if mnp:
            level = "\u63d0\u793a" if ("useMemo" in code or "useEffect" in code or "useCallback" in code) else "\u8b66\u793a"
            findings.append((lineno, level,
                             "\u6e32\u67d3\u671f\u51fa\u73b0\u975e\u7eaf\u8ba1\u7b97 %s\uff0c\u6bcf\u6b21\u6e32\u67d3\u7ed3\u679c\u90fd\u4e0d\u540c\uff0c\u4f1a\u7834\u574f\u5f15\u7528\u6bd4\u8f83" % mnp.group(1)))

        if lineno not in map_lines:
            m_inner = RX_INNER_COMPONENT.match(line)
            if m_inner:
                findings.append((lineno, "\u8b66\u793a",
                                 "\u7ec4\u4ef6 %s \u5b9a\u4e49\u5728\u53e6\u4e00\u4e2a\u7ec4\u4ef6\u5185\u90e8\uff0c\u6bcf\u6b21\u6e32\u67d3\u90fd\u662f\u65b0\u7ec4\u4ef6\u7c7b\u578b\uff0c\u5b50\u6811\u4f1a\u91cd\u5efa" % m_inner.group("name")))

        if has_component_tag and RX_ARROW_PROP.search(head):
            m_arr = RX_ARROW_PROP.search(head)
            base = tags[0].split(".")[0]
            if base in memo_names:
                findings.append((lineno, "\u63d0\u793a",
                                 "%s \u63a5\u6536\u4e86\u5185\u8054\u7bad\u5934\u51fd\u6570 %s\uff0c\u867d\u7136\u662f memo \u7ec4\u4ef6\u4f46 handler \u5f15\u7528\u6bcf\u6b21\u90fd\u53d8\uff0c\u5efa\u8bae useCallback" % (
                                     base, m_arr.group(1))))

    for lineno, level, msg in check_hook_deps(text):
        findings.append((lineno, level, msg))
    return findings


def build_report(files_map, is_dir):
    lines = []
    summary = {"files": [], "findings": [], "counts": {}}
    lines.append("=" * 62)
    lines.append("React \u91cd\u6e32\u67d3\u98ce\u9669\u626b\u63cf\u62a5\u544a")
    lines.append("=" * 62)
    total = 0
    for path in sorted(files_map.keys()):
        fnd = files_map[path]
        total += len(fnd)
        summary["files"].append({"file": path, "count": len(fnd)})
        lines.append("")
        lines.append("[\u6587\u4ef6] %s  \u53d1\u73b0\u95ee\u9898 %d \u6761" % (path, len(fnd)))
        if not fnd:
            lines.append("  [\u597d] \u672a\u547d\u4e2d\u5df2\u77e5\u91cd\u6e32\u67d3\u98ce\u9669\u6a21\u5f0f")
            continue
        for lineno, level, msg in sorted(fnd, key=lambda x: (SEVERITY_ORDER.get(x[1], 9), x[0])):
            lines.append("  [%s] \u7b2c %d \u884c: %s" % (level, lineno + 1, msg))
            summary["findings"].append({"file": path, "line": lineno + 1,
                                        "level": level, "msg": msg})
            summary["counts"][level] = summary["counts"].get(level, 0) + 1
    lines.append("")
    lines.append("\u5408\u8ba1: %d \u4e2a\u6587\u4ef6\uff0c%d \u6761\u98ce\u9669" % (len(files_map), total))
    for level in ("\u4e25\u91cd", "\u9519\u8bef", "\u8b66\u793a", "\u63d0\u793a"):
        if level in summary["counts"]:
            lines.append("  %s: %d" % (level, summary["counts"][level]))
    summary["total"] = total
    lines.append("")
    lines.append("\u514d\u8d23: \u9759\u6001\u626b\u63cf\u53ea\u80fd\u53d1\u73b0\u6a21\u5f0f\uff0c\u5b9e\u9645\u91cd\u6e32\u67d3\u5fc5\u987b\u7528 Profiler \u4e0e why-did-you-render \u786e\u8ba4\u3002")
    lines.append("=" * 62)
    return "\n".join(lines), summary


SAMPLE_A = """import React, { useState, useMemo } from 'react';

const Row = function Row({ item }) {
  return <li>{item.name}</li>;
};

function List({ items, onPick }) {
  const [text, setText] = useState('');
  const today = new Date();
  const sorted = useMemo(() => items.slice().sort(), []);
  return (
    <ul>
      {items.map((item, index) => (
        <Row key={index} item={{ ...item }} />
      ))}
      <Chart data={[1, 2, 3]} />
      <ThemeCtx.Provider value={{ theme: 'dark' }}>
        <Toolbar />
      </ThemeCtx.Provider>
      <HeavyPanel onClose={() => setText('')} />
    </ul>
  );
}
"""

SAMPLE_B = """import React, { memo, useState, useCallback } from 'react';

const Row = memo(function Row({ item, onClick }) {
  return <li onClick={onClick}>{item.name}</li>;
});

export default function Panel({ items }) {
  const [open, setOpen] = useState(false);
  const handle = useCallback(() => {
    console.log(open, items.length);
  }, []);
  return (
    <ul>
      {items.map((item) => (
        <Row key={item.id} item={item} onClick={handle} />
      ))}
      <Btn key={Math.random()} />
    </ul>
  );
}
"""


def selftest():
    a = scan_file(SAMPLE_A, "a.jsx")
    msgs = [m for _, _, m in a]
    ck("\u5185\u8054\u5bf9\u8c61\u5c5e\u6027\u5e94\u88ab\u5224\u5b9a\u4e3a\u5931\u6548\u98ce\u9669", any("\u5185\u8054\u5bf9\u8c61\u5b57\u9762\u91cf" in m for m in msgs))
    ck("\u5185\u8054\u6570\u7ec4\u5c5e\u6027\u5e94\u88ab\u5224\u5b9a\u4e3a\u5931\u6548\u98ce\u9669", any("\u5185\u8054\u6570\u7ec4\u5b57\u9762\u91cf" in m for m in msgs))
    ck("Provider \u5185\u8054 value \u5e94\u88ab\u68c0\u51fa", any("Provider" in m for m in msgs))
    ck("\u7d22\u5f15 key \u5e94\u88ab\u68c0\u51fa", any("state \u4f1a\u4e32\u4f4d" in m for m in msgs))
    ck("\u6e32\u67d3\u671f\u975e\u7eaf\u8ba1\u7b97\u5e94\u88ab\u68c0\u51fa", any("\u975e\u7eaf\u8ba1\u7b97" in m for m in msgs))
    ck("\u672a memo \u7684\u5217\u8868\u9879\u5e94\u88ab\u68c0\u51fa", any("\u672a\u88ab memo \u5305\u88f9" in m for m in msgs))
    ck("\u5185\u8054\u5bf9\u8c61\u5e94\u4ee5\u4e25\u91cd\u7ea7\u522b\u62a5\u51fa", any(x[1] == "\u4e25\u91cd" and "\u5185\u8054\u5bf9\u8c61" in x[2] for x in a))

    b = scan_file(SAMPLE_B, "b.jsx")
    bmsgs = [m for _, _, m in b]
    ck("\u968f\u673a key \u5e94\u88ab\u5224\u4e25\u91cd", any("\u968f\u673a" in m for m in bmsgs))
    ck("\u968f\u673a key \u7684\u7ea7\u522b\u5e94\u4e3a\u4e25\u91cd", any(x[1] == "\u4e25\u91cd" and "\u968f\u673a" in x[2] for x in b))
    ck("\u5df2 memo \u7684\u5217\u8868\u9879\u4e0d\u5e94\u518d\u62a5\u672a memo", not any("\u672a\u88ab memo \u5305\u88f9" in m for m in bmsgs))
    ck("\u7a7a\u4f9d\u8d56\u5f15\u7528\u5916\u90e8\u53d8\u91cf\u5e94\u88ab\u68c0\u51fa", any("\u53ef\u80fd\u6f0f\u4f9d\u8d56" in m for m in bmsgs))
    ck("\u6b63\u786e\u5199\u6cd5\u6837\u672c\u95ee\u9898\u6570\u5e94\u5c11\u4e8e\u9519\u8bef\u6837\u672c", len(b) < len(a))

    ck("\u5e94\u8bc6\u522b\u51fa state \u540d open", "open" in collect_outer_names(SAMPLE_B))
    ck("\u5e94\u8bc6\u522b\u51fa props \u540d items", "items" in collect_outer_names(SAMPLE_B))
    ck("\u5e94\u63d0\u53d6\u5230 useCallback \u8c03\u7528", len(extract_hook_calls(SAMPLE_B)) >= 1)

    _, sm = build_report({"a.jsx": a, "b.jsx": b}, False)
    ck("\u62a5\u544a\u5e94\u7edf\u8ba1\u603b\u6570", sm["total"] == len(a) + len(b))
    ck("\u62a5\u544a\u5e94\u5206\u7ea7\u7edf\u8ba1", "\u4e25\u91cd" in sm["counts"])

    good = "export default function X() {\n  return <Box item={data} />;\n}\n"
    g = scan_file(good, "g.jsx")
    ck("\u5e72\u51c0\u6837\u672c\u4e0d\u5e94\u6709\u4e25\u91cd\u95ee\u9898", not any(x[1] == "\u4e25\u91cd" for x in g))

    mlines = map_context_lines(SAMPLE_A)
    ck("\u5e94\u8bc6\u522b\u51fa .map \u8986\u76d6\u7684\u884c", len(mlines) >= 3)
    ck("map \u884c\u6570\u5e94\u4e3a\u6574\u6570\u96c6\u5408", all(isinstance(x, int) for x in mlines))
    return not FAILS


def collect_files(target):
    out = []
    if os.path.isfile(target):
        return [target]
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.lower().endswith(SCAN_EXT):
                out.append(os.path.join(root, fn))
    return out


def main():
    ap = argparse.ArgumentParser(description="React \u91cd\u6e32\u67d3\u98ce\u9669\u9759\u6001\u626b\u63cf")
    ap.add_argument("--file", help="\u5355\u4e2a\u6e90\u6587\u4ef6")
    ap.add_argument("--dir", help="\u76ee\u5f55\u9012\u5f52\u626b\u63cf")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6587\u4ef6")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    if not args.file and not args.dir:
        ap.error("\u9700\u8981 --file / --dir / --selftest")

    targets = []
    if args.file:
        targets.append(args.file)
    if args.dir:
        targets.append(args.dir)
    files = []
    for t in targets:
        files.extend(collect_files(t))

    files_map = {}
    for p in sorted(set(files)):
        try:
            body = io.open(p, "r", encoding="utf-8", errors="ignore").read()
        except IOError:
            continue
        files_map[p] = scan_file(body, p)

    report, summary = build_report(files_map, bool(args.dir))
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % out_path)


if __name__ == "__main__":
    main()
