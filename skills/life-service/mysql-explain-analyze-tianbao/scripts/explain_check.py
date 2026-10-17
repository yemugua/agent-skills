# -*- coding: utf-8 -*-
"""EXPLAIN 结果解析与诊断。

用法:
  python explain_check.py --selftest
  python explain_check.py --file explain.txt
  python explain_check.py --file explain.txt --cols "tenant_id:int:no,status:tinyint:no,nick:varchar(64):no" --charset utf8mb4

支持 MySQL 客户端表格输出（+---+ / | id | select_type | ... |）以及竖线分隔的简化输出。
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


TYPE_RANK = {
    "system": 1, "const": 2, "eq_ref": 3, "ref": 4, "ref_or_null": 5, "fulltext": 5,
    "unique_subquery": 6, "index_subquery": 7, "range": 8, "index_merge": 9,
    "index": 10, "ALL": 11,
}

TYPE_DESC = {
    "system": "表只有一行，最优",
    "const": "主键/唯一索引等值，一次命中",
    "eq_ref": "联表时被驱动表主键等值匹配",
    "ref": "非唯一索引等值匹配",
    "ref_or_null": "ref 的变体，额外处理 IS NULL",
    "fulltext": "全文索引",
    "unique_subquery": "IN 子查询转唯一索引查找",
    "index_subquery": "IN 子查询转普通索引查找",
    "range": "范围扫描",
    "index_merge": "合并多个索引结果，通常说明索引没建全",
    "index": "全索引扫描（扫整棵树）",
    "ALL": "全表扫描",
}

BYTES = {"tinyint": 1, "smallint": 2, "mediumint": 3, "int": 4, "bigint": 8,
         "date": 3, "timestamp": 4, "datetime": 5, "time": 3, "year": 1}

CHARSET_BYTES = {"latin1": 1, "utf8": 3, "utf8mb4": 4, "gbk": 2, "ascii": 1}


def parse_explain(text):
    """解析 EXPLAIN 表格文本，返回 list[dict]。"""
    header = None
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("+"):
            continue
        if "|" not in s:
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            low = [c.lower() for c in cells]
            if low and low[0] == "id" and "type" in low:
                header = low
            continue
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def cell(row, name):
    """EXPLAIN 列名大小写都可能，统一取值。"""
    v = row.get(name)
    if v is None:
        v = row.get(name.lower())
    if v is None:
        v = row.get(name.upper())
    return ("" if v is None else str(v)).strip()


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return 0.0


def col_bytes(typ, length, nullable, charset):
    t = typ.lower()
    if t in BYTES:
        n = BYTES[t]
    elif t == "char":
        n = int(length or 1) * charset
    elif t == "varchar":
        n = int(length or 1) * charset + 2
    elif t == "decimal":
        n = 8
    else:
        n = 4
    if nullable:
        n += 1
    return n


def parse_coldefs(s, charset):
    """'a:int:no,b:varchar(64):yes' -> [(name, bytes)]"""
    cz = CHARSET_BYTES.get(charset.lower(), 4)
    out = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        bits = part.split(":")
        name = bits[0]
        typ = bits[1] if len(bits) > 1 else "int"
        nullable = (len(bits) > 2 and bits[2].lower() in ("yes", "null", "nullable"))
        m = re.search(r"\((\d+)\)", typ)
        length = int(m.group(1)) if m else None
        base = re.sub(r"\(.*\)", "", typ)
        out.append((name, col_bytes(base, length, nullable, cz)))
    return out


def cumulative_bytes(coldefs):
    out = []
    acc = 0
    for name, b in coldefs:
        acc += b
        out.append((name, acc))
    return out


def match_prefix(key_len, cum):
    """用 key_len 反推用到第几列。返回列名或 None。"""
    if not key_len or not cum:
        return None
    hit = None
    for name, acc in cum:
        if abs(acc - key_len) < 0.01:
            return name
        if key_len > acc:
            hit = name
    return hit


def diagnose(row, coldefs, charset):
    issues = []
    goods = []
    typ = cell(row, "type")
    key = cell(row, "key")
    possible = cell(row, "possible_keys")
    rows_est = num(cell(row, "rows"))
    filtered = num(cell(row, "filtered")) or 100.0
    extra = cell(row, "Extra")
    table = cell(row, "table")
    rank = TYPE_RANK.get(typ, 99)

    if typ == "ALL":
        issues.append(("严重", "type=ALL 全表扫描，扫描 %s 行" % int(rows_est)))
    elif typ == "index":
        issues.append(("警示", "type=index 全索引扫描，扫了整棵索引树"))
    elif typ == "index_merge":
        issues.append(("警示", "type=index_merge，说明索引没建全，优先考虑联合索引"))

    if key.upper() in ("", "NULL"):
        if possible.upper() in ("", "NULL"):
            issues.append(("严重", "possible_keys 与 key 都为 NULL，没有任何可用索引"))
        elif rows_est > 5000:
            issues.append(("严重", "key 为 NULL 未使用索引，预计扫描 %s 行" % int(rows_est)))
        else:
            issues.append(("警示", "key 为 NULL 未使用索引（表较小，优化器选择全表）"))

    if rows_est >= 100000:
        issues.append(("严重", "预计扫描 %s 行，量级过大" % int(rows_est)))
    elif rows_est >= 10000:
        issues.append(("警示", "预计扫描 %s 行，需确认是否可接受" % int(rows_est)))

    if filtered and filtered <= 10 and rows_est >= 1000:
        issues.append(("警示", "filtered=%.2f%%，大量行被读到 Server 层再过滤，条件没被索引吸收" % filtered))

    if "Using filesort" in extra:
        issues.append(("错误", "Using filesort：无法用索引顺序，需要额外排序"))
    if "Using temporary" in extra:
        issues.append(("错误", "Using temporary：使用了临时表（GROUP BY / DISTINCT / UNION 常见）"))
    if "join buffer" in extra.lower():
        issues.append(("严重", "Using join buffer：关联字段没有索引，只能用 buffer 兜底"))
    if "Range checked for each record" in extra:
        issues.append(("严重", "Range checked for each record：每行都要判断能否用索引，关联写法有问题"))
    if "Impossible WHERE" in extra or "no matching row" in extra:
        issues.append(("提示", "条件恒假不需要执行：检查 SQL 是否写错或类型不匹配"))
    if "Using index condition" in extra:
        goods.append("Using index condition：索引下推已生效（仍会回表）")
    if extra.strip() == "Using index" or "Using index" in extra and "Using index condition" not in extra:
        goods.append("Using index：覆盖索引，不回表")
    if "Select tables optimized away" in extra:
        goods.append("Select tables optimized away：优化器直接算出结果")
    if typ in ("const", "system", "eq_ref", "ref") and rows_est <= 100:
        goods.append("type=%s 且预估行数小，访问路径良好" % typ)

    kl = num(cell(row, "key_len"))
    if coldefs:
        cum = cumulative_bytes(coldefs)
        col = match_prefix(kl, cum)
        if key.upper() not in ("", "NULL") and col:
            goods.append("key_len=%d 反推用到第 %d 列 %s" %
                         (int(kl), [c[0] for c in coldefs].index(col) + 1, col))
        elif key.upper() not in ("", "NULL"):
            issues.append(("提示", "key_len=%d 与给定列宽对不上，确认字符集与列定义" % int(kl)))
    return {"table": table, "type": typ, "key": key, "rows": rows_est,
            "filtered": filtered, "extra": extra, "rank": rank,
            "issues": issues, "goods": goods}


def build_report(text, coldefs=None, charset="utf8mb4"):
    rows = parse_explain(text)
    lines = []
    summary = {"rows": [], "problems": 0}
    lines.append("=" * 62)
    lines.append("EXPLAIN 诊断报告")
    lines.append("=" * 62)
    if not rows:
        lines.append("")
        lines.append("未解析到 EXPLAIN 表格。请粘贴 mysql 客户端的 EXPLAIN 输出。")
        return "\n".join(lines), summary
    worst_rank = 0
    for i, r in enumerate(rows, 1):
        d = diagnose(r, coldefs, charset)
        worst_rank = max(worst_rank, d["rank"])
        summary["rows"].append({"table": d["table"], "type": d["type"], "key": d["key"],
                                "rows": d["rows"], "filtered": d["filtered"],
                                "extra": d["extra"],
                                "issues": [{"level": a, "msg": b} for a, b in d["issues"]],
                                "goods": d["goods"]})
        summary["problems"] += len(d["issues"])
        lines.append("")
        lines.append("[表 %d] %s  type=%s  key=%s  rows=%s  filtered=%.2f%%" % (
            i, d["table"], d["type"], d["key"], int(d["rows"]), d["filtered"]))
        lines.append("  type 含义: %s" % TYPE_DESC.get(d["type"], "未知类型"))
        if d["extra"] and d["extra"].upper() != "NULL":
            lines.append("  Extra: %s" % d["extra"])
        for lvl, msg in d["issues"]:
            lines.append("  [%s] %s" % (lvl, msg))
        for g in d["goods"]:
            lines.append("  [好] %s" % g)
    lines.append("")
    lines.append("最差的访问方式: %s" % (list(TYPE_RANK.keys())[list(TYPE_RANK.values()).index(worst_rank)]
                                 if worst_rank in TYPE_RANK.values() else "未知"))
    lines.append("问题项合计: %d" % summary["problems"])
    lines.append("")
    lines.append("免责: 静态诊断基于 EXPLAIN 估算值，实际执行请以 EXPLAIN ANALYZE 为准。")
    lines.append("=" * 62)
    return "\n".join(lines), summary


TABLE_ALL = """+----+-------------+-------+------------+------+---------------+------+---------+------+--------+----------+-------------+
| id | select_type | table | partitions | type | possible_keys | key  | key_len | ref  | rows   | filtered | Extra       |
+----+-------------+-------+------------+------+---------------+------+---------+------+--------+----------+-------------+
|  1 | SIMPLE      | orders| NULL       | ALL  | NULL          | NULL | NULL    | NULL | 500000 |    10.00 | Using where |
+----+-------------+-------+------------+------+---------------+------+---------+------+--------+----------+-------------+"""

TABLE_GOOD = """| id | select_type | table | partitions | type | possible_keys | key | key_len | ref | rows | filtered | Extra |
| 1 | SIMPLE | t | NULL | ref | idx_tsn | idx_tsn | 5 | const | 20 | 100.00 | Using index |"""


def selftest():
    rows1 = parse_explain(TABLE_ALL)
    ck("应解析出 1 行", len(rows1) == 1)
    ck("应取到表名 orders", rows1[0]["table"] == "orders")
    ck("应取到 type=ALL", rows1[0]["type"] == "ALL")

    d1 = diagnose(rows1[0], None, "utf8mb4")
    ck("全表扫应判严重", any(a == "严重" for a, _ in d1["issues"]))
    ck("possible_keys 为 NULL 应报无可用索引", any("没有任何可用索引" in b for _, b in d1["issues"]))
    ck("filtered 10% 应提示", any("filtered" in b for _, b in d1["issues"]))
    ck("高扫描行应提示", any("500000" in b for _, b in d1["issues"]))

    rows2 = parse_explain(TABLE_GOOD)
    ck("简化表格也应解析", len(rows2) == 1)
    d2 = diagnose(rows2[0], None, "utf8mb4")
    ck("良好执行计划不应有严重问题", all(a != "严重" for a, _ in d2["issues"]))
    ck("覆盖索引应被标为好", any("覆盖索引" in g for g in d2["goods"]))

    ck("type 排序 const 优于 ref", TYPE_RANK["const"] < TYPE_RANK["ref"])
    ck("type 排序 ref 优于 range", TYPE_RANK["ref"] < TYPE_RANK["range"])
    ck("type 排序 range 优于 ALL", TYPE_RANK["range"] < TYPE_RANK["ALL"])

    cz = CHARSET_BYTES["utf8mb4"]
    ck("int not null 应为 4 字节", col_bytes("int", None, False, cz) == 4)
    ck("tinyint nullable 应为 2 字节", col_bytes("tinyint", None, True, cz) == 2)
    ck("varchar(64) utf8mb4 应为 258", col_bytes("varchar", 64, False, cz) == 258)

    cdefs = parse_coldefs("tenant_id:int:no,status:tinyint:no,nick:varchar(64):no", "utf8mb4")
    ck("应解析 3 列定义", len(cdefs) == 3)
    cum = cumulative_bytes(cdefs)
    ck("累计字节第三列应为 263", cum[2][1] == 263)
    ck("key_len=5 应反推到第 2 列 status", match_prefix(5, cum) == "status")
    ck("key_len=263 应反推到第 3 列 nick", match_prefix(263, cum) == "nick")

    join_row = {"type": "ALL", "key": "NULL", "possible_keys": "NULL", "rows": "10",
                "filtered": "100", "Extra": "Using join buffer (Block Nested Loop)", "table": "u"}
    d3 = diagnose(join_row, None, "utf8mb4")
    ck("join buffer 应判严重", any("关联字段没有索引" in b for _, b in d3["issues"]))

    _, sm = build_report(TABLE_ALL, cdefs, "utf8mb4")
    ck("报告应记录问题项", sm["problems"] > 0)
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="EXPLAIN 结果解析与诊断")
    ap.add_argument("--file", help="EXPLAIN 输出文本文件")
    ap.add_argument("--cols", help="索引列定义，用于 key_len 反推：a:int:no,b:varchar(64):yes")
    ap.add_argument("--charset", default="utf8mb4", help="字符集，默认 utf8mb4")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="结果写入文件")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    if not args.file:
        ap.error("需要 --file 或 --selftest")

    text = io.open(args.file, "r", encoding="utf-8", errors="ignore").read()
    cdefs = parse_coldefs(args.cols, args.charset) if args.cols else None
    report, summary = build_report(text, cdefs, args.charset)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("结果已写入: %s" % out_path)


if __name__ == "__main__":
    main()
