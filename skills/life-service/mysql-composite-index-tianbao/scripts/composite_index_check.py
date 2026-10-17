# -*- coding: utf-8 -*-
"""MySQL 联合索引失效静态检查器。

用法:
  python composite_index_check.py --selftest
  python composite_index_check.py --file case.sql
  python composite_index_check.py --index "a,b,c" --sql "SELECT * FROM t WHERE a=1 AND b>2 AND c=3"

输入文件支持两种指令行：
  INDEX idx_abc (tenant_id, status, create_time)
  SQL ...（可跨行，以英文分号结尾）

按「最左前缀 + 范围右侧截断 + 索引列不得被加工」三条基准做判定。
"""
import argparse
import io
import json
import os
import re
import sys

FAILS = []


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


FUNC_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*(=|>|<|>=|<=|<>|!=)\s*", re.S)

EQ_OPS = ["=", "<=>"]
RANGE_OPS = [">", ">=", "<", "<=", "<>", "!=", "BETWEEN"]
NOT_WORDS = ["NOT IN", "NOT LIKE", "NOT EXISTS"]

CMP_SPLIT = re.compile(r"(<=|>=|<>|!=|=|>|<)")


def strip_sql_comments(s):
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"--[^\n]*", " ", s)
    return s


def parse_input(text):
    """返回 (indexes, sqls)。indexes: dict name -> list[col]；sqls: list[str]。"""
    text = strip_sql_comments(text)
    indexes = {}
    current = None
    seen_index = False
    for m in re.finditer(r"INDEX\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)", text, re.I):
        seen_index = True
        cols = [c.strip().split()[0] for c in m.group(2).split(",") if c.strip()]
        indexes[m.group(1)] = cols
    sqls = []
    buf = []
    for line in text.splitlines():
        st = line.strip()
        if re.match(r"^INDEX\s+", st, re.I):
            continue
        if not st:
            continue
        if buf and re.match(r"^(SELECT|WITH|UPDATE|DELETE)", st, re.I) and not re.search(r";\s*$", buf[-1]):
            sqls.append(" ".join(buf))
            buf = [st]
        else:
            buf.append(st)
        if ";" in st:
            sqls.append(" ".join(buf))
            buf = []
    if buf:
        sqls.append(" ".join(buf))
    sqls = [s.strip().rstrip(";").strip() for s in sqls if s.strip()]
    # 若没有 INDEX 指令，尝试从 CREATE TABLE 的 KEY 定义里提取
    if not seen_index:
        for m in re.finditer(r"(?:UNIQUE\s+)?KEY\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)", text, re.I):
            cols = [c.strip().split()[0] for c in m.group(2).split(",") if c.strip()]
            indexes[m.group(1)] = cols
    return indexes, sqls


def where_clause(sql):
    m = re.search(r"\bWHERE\b(.*?)(?=\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|\bHAVING\b|$)",
                  sql, re.S | re.I)
    if not m:
        return ""
    return " " + m.group(1).strip() + " "


def order_clause(sql):
    m = re.search(r"\bORDER\s+BY\b(.*?)(?=\bLIMIT\b|$)", sql, re.S | re.I)
    return m.group(1).strip() if m else ""


def group_clause(sql):
    m = re.search(r"\bGROUP\s+BY\b(.*?)(?=\bORDER\s+BY\b|\bHAVING\b|\bLIMIT\b|$)", sql, re.S | re.I)
    return m.group(1).strip() if m else ""


def select_columns(sql):
    m = re.match(r"\s*SELECT\s+(.*?)\s+FROM\s", sql, re.S | re.I)
    if not m:
        return []
    return [c.strip() for c in m.group(1).split(",")]


def split_or(clause):
    parts = []
    depth = 0
    cur = ""
    for i, ch in enumerate(clause):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0 and clause[i:i + 4].upper() == " OR ":
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def split_and(clause):
    parts = []
    depth = 0
    cur = ""
    upper = clause.upper()
    i = 0
    while i < len(clause):
        ch = clause[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0 and upper[i:i + 5] == " AND ":
            parts.append(cur)
            cur = ""
            i += 5
            continue
        cur += ch
        i += 1
    parts.append(cur)
    return [p.strip(" ()") for p in parts if p.strip(" ()")]


def classify_pred(pred):
    """返回 (列名, 类别)。类别: eq/range/in/func/like_ok/like_bad/not/isnull/or/other"""
    p = pred.strip()
    up = p.upper()
    if re.search(r"\bOR\b", up):
        return None, "or"
    for w in NOT_WORDS:
        if w in up:
            m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_.]*)", p)
            return (m.group(1) if m else None), "not"
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_.]*)\s+IS\s+(NOT\s+)?NULL\b", p, re.I)
    if m:
        return m.group(1), "isnull"
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_.]*)\s+IN\s*\(", p, re.I)
    if m:
        return m.group(1), "in"
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_.]*)\s+LIKE\s+'([^']*)'", p, re.I)
    if m:
        pattern = m.group(2)
        if pattern.startswith("%") or pattern.startswith("_"):
            return m.group(1), "like_bad"
        return m.group(1), "like_ok"
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_.]*)\s*[*/+-]\s*[\w.]+\s*(=|>|<|>=|<=)", p)
    if m:
        return m.group(1), "func"
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)\s*(=|>|<|>=|<=|<>|!=)", p)
    if m:
        cm = re.match(r"\s*([A-Za-z_][A-Za-z0-9_.]*)", m.group(2))
        return (cm.group(1) if cm else None), "func"
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_.]*)\s*(<=|>=|<>|!=|=|>|<)\s*(.*)", p, re.S)
    if not m:
        return None, "other"
    col, op, val = m.group(1), m.group(2), m.group(3).strip()
    if re.match(r"LIKE\s+'", val, re.I):
        lm = re.search(r"LIKE\s+'([^']*)'", val, re.I)
        pattern = lm.group(1) if lm else ""
        if pattern.startswith("%") or pattern.startswith("_"):
            return col, "like_bad"
        return col, "like_ok"
    if re.match(r"BETWEEN\b", val, re.I):
        return col, "range"
    if op in ("<", ">", "<=", ">="):
        return col, "range"
    if op in ("<>", "!="):
        return col, "not"
    return col, "eq"


def analyze_index(cols, preds, sql):
    """返回 dict: used(list), stop_reason, notes(list)。"""
    kinds = {}
    for c, k in preds:
        kinds.setdefault(c, []).append(k)
    used = []
    notes = []
    stop = ""
    for i, col in enumerate(cols):
        ks = kinds.get(col)
        if not ks:
            if used:
                stop = "第 %d 列 %s 没有条件，索引在此截断" % (i + 1, col)
            else:
                stop = "缺少最左列 %s，索引不可用" % col
            break
        if "func" in ks:
            notes.append("%s 被函数/运算包裹，该列无法用索引定位" % col)
            stop = "%s 被加工，索引无法继续" % col
            break
        if "like_bad" in ks:
            notes.append("%s 的 LIKE 以前导通配符开头，无法定位起点" % col)
            stop = "%s 前导通配符，索引无法继续" % col
            break
        if "not" in ks:
            notes.append("%s 使用了否定条件(≠/NOT IN)，通常走全表" % col)
            stop = "%s 否定条件，索引在此停止" % col
            break
        used.append(col)
        if any(k in ("range", "like_ok") for k in ks):
            rest = cols[i + 1:]
            if rest:
                notes.append("%s 是范围条件，其右侧的 %s 只能做索引下推过滤，无法减少扫描行数" %
                             (col, "、".join(rest)))
            stop = "范围列 %s 之后截断" % col
            break
        if "isnull" in ks and "eq" not in ks:
            notes.append("%s 为 IS NULL 条件，可以走索引但 selectivity 需确认" % col)
    return {"used": used, "stop": stop, "notes": notes}


def global_antipatterns(index_name, cols, sql):
    """与索引无关的全局写法问题，返回 list[(级别, 说明)]。"""
    out = []
    w = where_clause(sql)
    up = w.upper()
    sel = select_columns(sql)
    if any(s.strip() == "*" for s in sel):
        out.append(("提示", "SELECT * 会阻止覆盖索引，且回表成本高，建议只查需要的列"))
    if re.search(r"\bOR\b", up):
        parts = split_or(w)
        if len(parts) > 1:
            out.append(("警示", "WHERE 中出现 OR，任一支无索引即全表扫；建议改 UNION ALL 或补联合索引"))
    if re.search(r"'\s*\)?\s*$", w) and re.search(r"\w+\s*=\s*'?\d+'", w):
        out.append(("提示", "字符串类型的列用带引号数字比较时不会失效，反向（字符串列给数字）会失效，需确认列类型"))
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(\d+)", w):
        out.append(("提示", "%s 与数字 %s 比较：若该列是 varchar，会触发隐式转换导致索引失效" % (m.group(1), m.group(2))))
        break
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_.]*)\s*([*/+\-])\s*\d+\s*(?:=|>|<)", w):
        out.append(("错误", "%s 参与算术运算，索引列被加工，必定失效；把运算移到右值" % m.group(1)))
        break
    ob = order_clause(sql)
    if ob:
        terms = [t.strip() for t in ob.split(",")]
        names = [re.match(r"([A-Za-z_][A-Za-z0-9_.]*)", t).group(1) if re.match(r"([A-Za-z_][A-Za-z0-9_.]*)", t) else t
                 for t in terms]
        dirs = [t.upper().endswith("DESC") for t in terms]
        idx_pos = [cols.index(n) if n in cols else -1 for n in names]
        if all(p >= 0 for p in idx_pos) and idx_pos != sorted(idx_pos):
            out.append(("错误", "ORDER BY 列顺序与索引顺序不一致，会产生 filesort"))
        if len(set(dirs)) > 1:
            out.append(("错误", "ORDER BY 混用 ASC/DESC，MySQL 5.7 需 filesort；MySQL 8 应建对应降序索引"))
    gb = group_clause(sql)
    if gb:
        out.append(("警示", "存在 GROUP BY，若无匹配索引会出现 Using temporary + Using filesort"))
    if re.search(r"\bLIMIT\s+(\d+)\s*,\s*(\d+)", sql, re.I):
        m = re.search(r"\bLIMIT\s+(\d+)\s*,\s*(\d+)", sql, re.I)
        if int(m.group(1)) > 1000:
            out.append(("错误", "深分页 LIMIT %s,%s：偏移越大越慢，应改游标分页（记录上一页最大 id）" %
                        (m.group(1), m.group(2))))
    return out


def build_report(indexes, sqls):
    lines = []
    summary = {"indexes": indexes, "sqls": []}
    lines.append("=" * 60)
    lines.append("MySQL 联合索引检查报告")
    lines.append("=" * 60)
    if indexes:
        lines.append("")
        lines.append("[索引定义]")
        for name, cols in indexes.items():
            lines.append("  %s (%s)" % (name, ", ".join(cols)))
    else:
        lines.append("")
        lines.append("[提示] 未提供索引定义，只做写法检查。用 'INDEX idx_name (a,b,c)' 声明。")
    for i, sql in enumerate(sqls, 1):
        preds_raw = split_and(where_clause(sql))
        preds = []
        for p in preds_raw:
            c, k = classify_pred(p)
            preds.append((c, k))
        lines.append("")
        lines.append("[SQL %d] %s" % (i, sql[:200]))
        if not any(k in ("eq", "range", "in", "like_ok", "like_bad", "not", "func", "isnull")
                   for _, k in preds):
            lines.append("  未识别到 WHERE 条件，跳过索引判定")
        for name, cols in indexes.items():
            res = analyze_index(cols, preds, sql)
            lines.append("  索引 %s (%s):" % (name, ", ".join(cols)))
            if res["used"]:
                lines.append("    实际可用列: %s" % ", ".join(res["used"]))
            else:
                lines.append("    实际可用列: 无")
            if res["stop"]:
                lines.append("    截断原因: %s" % res["stop"])
            for n in res["notes"]:
                lines.append("    - %s" % n)
            summary_entry = {"index": name, "used": res["used"], "stop": res["stop"],
                             "notes": res["notes"]}
            summary["sqls"].append({"sql": sql, **summary_entry})
        for lvl, msg in global_antipatterns("", [c for cs in indexes.values() for c in cs], sql):
            lines.append("  [%s] %s" % (lvl, msg))
    lines.append("")
    lines.append("免责: 静态检查不解析实际执行成本，最终以 EXPLAIN / EXPLAIN ANALYZE 为准。")
    lines.append("=" * 60)
    return "\n".join(lines), summary


def selftest():
    idx = "tenant_id,status,create_time"
    cols = idx.split(",")

    sql_full = "SELECT id FROM t WHERE tenant_id = 1 AND status = 2 AND create_time = '2026-01-01'"
    preds = [classify_pred(p) for p in split_and(where_clause(sql_full))]
    res = analyze_index(cols, preds, sql_full)
    ck("三列全等值时应用满三列", res["used"] == cols)

    sql_skip = "SELECT id FROM t WHERE tenant_id = 1 AND create_time = '2026-01-01'"
    preds2 = [classify_pred(p) for p in split_and(where_clause(sql_skip))]
    res2 = analyze_index(cols, preds2, sql_skip)
    ck("跳过第二列时应只用第一列", res2["used"] == ["tenant_id"])

    sql_nofirst = "SELECT id FROM t WHERE status = 2"
    preds3 = [classify_pred(p) for p in split_and(where_clause(sql_nofirst))]
    res3 = analyze_index(cols, preds3, sql_nofirst)
    ck("缺最左列应报索引不可用", res3["used"] == [] and "缺少最左列" in res3["stop"])

    sql_range = "SELECT id FROM t WHERE tenant_id = 1 AND status > 2 AND create_time = '2026-01-01'"
    preds4 = [classify_pred(p) for p in split_and(where_clause(sql_range))]
    res4 = analyze_index(cols, preds4, sql_range)
    ck("范围列之后应截断", res4["used"] == ["tenant_id", "status"])
    ck("应提示右侧列只能做索引下推", any("索引下推" in n for n in res4["notes"]))

    sql_func = "SELECT id FROM t WHERE DATE(create_time) = '2026-01-01'"
    preds5 = [classify_pred(p) for p in split_and(where_clause(sql_func))]
    c5, k5 = preds5[0]
    ck("函数包裹应判定为 func", k5 == "func")

    sql_like_bad = "SELECT id FROM t WHERE order_no LIKE '%abc'"
    c6, k6 = classify_pred("order_no LIKE '%abc'")
    ck("前导通配符应判 like_bad", k6 == "like_bad")
    c7, k7 = classify_pred("order_no LIKE 'abc%'")
    ck("前缀匹配应判 like_ok", k7 == "like_ok")

    c8, k8 = classify_pred("amount / 100 = 30")
    ck("列参与运算应判 func", k8 == "func")

    c9, k9 = classify_pred("status NOT IN (1,2)")
    ck("NOT IN 应判 not", k9 == "not")

    c10, k10 = classify_pred("deleted IS NULL")
    ck("IS NULL 应判 isnull", k10 == "isnull")

    c11, k11 = classify_pred("status IN (1,2,3)")
    ck("IN 应判 in", k11 == "in")

    _, sm = build_report({"idx_ts": cols}, [sql_range])
    ck("报告应包含 SQL 分析", len(sm["sqls"]) >= 1)

    txt = "INDEX idx_a (tenant_id,status,create_time)\n" + sql_range + ";"
    ix, sq = parse_input(txt)
    ck("应解析出索引定义", ix.get("idx_a") == cols)
    ck("应解析出 1 条 SQL", len(sq) == 1)
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="MySQL 联合索引失效静态检查器")
    ap.add_argument("--file", help="包含 INDEX 指令与 SQL 的文本文件")
    ap.add_argument("--index", help="索引列，逗号分隔，如 tenant_id,status,create_time")
    ap.add_argument("--sql", help="单条 SQL")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="结果写入文件")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    indexes = {}
    sqls = []
    if args.file:
        text = io.open(args.file, "r", encoding="utf-8", errors="ignore").read()
        indexes, sqls = parse_input(text)
    if args.index:
        indexes["cli_index"] = [c.strip() for c in args.index.split(",") if c.strip()]
    if args.sql:
        sqls.append(args.sql.strip().rstrip(";"))
    if not sqls:
        ap.error("需要 --file 或 --sql 或 --selftest")

    report, summary = build_report(indexes, sqls)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("结果已写入: %s" % out_path)


if __name__ == "__main__":
    main()
