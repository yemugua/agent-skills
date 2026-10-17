# -*- coding: utf-8 -*-
"""慢 SQL 静态检查：写法反模式扫描 + 慢日志摘要解析。

用法:
  python slow_sql_check.py --selftest
  python slow_sql_check.py --file sql.txt
  python slow_sql_check.py --file slow.log --slowlog
  python slow_sql_check.py --sql "SELECT * FROM t LIMIT 10000, 20"

支持两种输入：
  1) 普通 SQL 文本（多条以 ; 分隔）
  2) MySQL 慢日志（加 --slowlog，识别 Query_time / Rows_sent / Rows_examined）
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


SEVERITY = {"严重": 0, "错误": 1, "警示": 2, "提示": 3}

RULES = [
    ("严重", "深分页", re.compile(r"\bLIMIT\s+(\d+)\s*(?:,\s*(\d+))?", re.I),
     lambda m: int(m.group(1)) > 1000,
     "偏移 %s 行，越往后越慢；改用游标分页 WHERE id > <上一页最大id> ORDER BY id LIMIT n"),

    ("严重", "列套函数/隐式类型转换", re.compile(r"(\bDATE\s*\(\s*\w+\s*\)|\bYEAR\s*\(\s*\w+\s*\)|\bLEFT\s*\(\s*\w+\s*,)", re.I),
     lambda m: True,
     "索引列被函数包裹，必定全表扫；改成日期区间 WHERE t >= 'x' AND t < 'y'"),

    ("错误", "前导通配符 LIKE", re.compile(r"\bLIKE\s+'[%_]", re.I),
     lambda m: True,
     "前导通配符无法定位索引起点；后缀匹配用反向列+函数索引，包含匹配用 FULLTEXT"),

    ("错误", "字符串列与数字比较", re.compile(r"(\w+)\s*=\s*(\d{5,})\b", re.I),
     lambda m: True,
     "%s 与数字比较：若该列是 varchar 会触发隐式转换导致索引失效，请加引号"),

    ("错误", "SELECT *", re.compile(r"SELECT\s+\*\s+FROM", re.I),
     lambda m: True,
     "SELECT * 阻止覆盖索引并放大回表成本；只查需要的列"),

    ("错误", "ORDER BY RAND()", re.compile(r"ORDER\s+BY\s+RAND\s*\(", re.I),
     lambda m: True,
     "ORDER BY RAND() 会全表计算随机值再排序；改为随机主键区间取值"),

    ("错误", "不带条件的 UPDATE/DELETE", re.compile(r"^\s*(UPDATE|DELETE\s+FROM)\s+\w+(?!.*\bWHERE\b)", re.I | re.S),
     lambda m: True,
     "缺少 WHERE 的整表写操作，长事务 + 主从延迟；请加条件并分批 LIMIT"),

    ("警示", "OR 条件", re.compile(r"\bWHERE\b[^\n]*?\bOR\b", re.I | re.S),
     lambda m: True,
     "WHERE 中出现 OR，任一支无索引即全表；改 UNION ALL 或补联合索引"),

    ("警示", "派生表/子查询", re.compile(r"FROM\s*\(\s*SELECT", re.I),
     lambda m: True,
     "FROM 子查询会生成派生表，MySQL 8 多数可合并，含聚合时不行；关注 Extra 是否出现 Using temporary"),

    ("警示", "关联子查询", re.compile(r"\bWHERE\s+\w+\s+IN\s*\(\s*SELECT", re.I),
     lambda m: True,
     "IN 子查询可能退化成依赖子查询逐行执行；改 JOIN 并用 EXPLAIN 验证"),

    ("警示", "COUNT 大表", re.compile(r"SELECT\s+COUNT\s*\(\s*\*\s*\)\s+FROM", re.I),
     lambda m: True,
     "大表 COUNT(*) 成本高；考虑近似值、计数表或只要存在性时改 SELECT 1 ... LIMIT 1"),

    ("警示", "缺少 LIMIT", re.compile(r"^\s*SELECT\b(?!.*\bLIMIT\b)(?!.*\bCOUNT\b)", re.I | re.S),
     lambda m: True,
     "查询没有 LIMIT：结果集可能很大，确认是否分页缺失"),

    ("提示", "ORDER BY 无匹配", re.compile(r"\bORDER\s+BY\b", re.I),
     lambda m: True,
     "存在 ORDER BY：检查是否有对应索引顺序，否则出现 Using filesort"),

    ("提示", "GROUP BY", re.compile(r"\bGROUP\s+BY\b", re.I),
     lambda m: True,
     "存在 GROUP BY：无匹配索引会走 Using temporary + filesort"),

    ("提示", "多表 JOIN", re.compile(r"\bJOIN\b", re.I),
     lambda m: True,
     "存在 JOIN：关联字段两端类型与字符集必须一致，否则被转换侧索引失效"),
]


def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"--[^\n]*", " ", s)
    return s


def split_sqls(text):
    out = []
    buf = ""
    for ch in text:
        buf += ch
        if ch == ";":
            out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    return [s for s in out if s.strip()]


def scan_sql(sql):
    hits = []
    for level, name, pat, cond, tpl in RULES:
        for m in pat.finditer(sql):
            try:
                if not cond(m):
                    continue
            except (TypeError, ValueError):
                continue
            try:
                msg = tpl % m.group(1) if "%s" in tpl else tpl
            except TypeError:
                msg = tpl
            hits.append({"level": level, "name": name, "msg": msg})
            break
    return hits


def parse_slow_log_blocks(text):
    items = []
    cur = None
    for line in text.splitlines():
        st = line.strip()
        if st.startswith("# Query_time") or (st.startswith("#") and "Rows_examined" in st):
            if cur:
                items.append(cur)
            cur = {"sql": []}
            for key in ("Query_time", "Lock_time", "Rows_sent", "Rows_examined"):
                m = re.search(key + r":\s*([\d.]+)", st)
                if m:
                    cur[key] = float(m.group(1))
        elif st.startswith("#") or st.upper().startswith("SET timestamp") or st.upper().startswith("USE "):
            continue
        elif st:
            if cur is None:
                cur = {"sql": []}
            cur["sql"].append(st)
    if cur:
        items.append(cur)
    out = []
    for it in items:
        sql = " ".join(it.pop("sql")).strip()
        if not sql:
            continue
        sent = it.get("Rows_sent", 0) or 0
        exam = it.get("Rows_examined", 0) or 0
        ratio = (exam / sent) if sent else float(exam)
        it["sql"] = sql
        it["scan_ratio"] = round(ratio, 1)
        it["verdict"] = scan_verdict(ratio, exam, it.get("Lock_time", 0) or 0)
        out.append(it)
    return out


def scan_verdict(ratio, exam, lock_time):
    if lock_time and exam and lock_time / max(exam, 1) > 0.01:
        return "锁等待占比偏高，优先排查行锁/事务，而非索引"
    if ratio >= 10000:
        return "严重：扫描比 %s，基本是全表扫或深分页" % round(ratio, 1)
    if ratio >= 1000:
        return "可疑：扫描行数远大于返回行数，检查索引是否生效"
    if ratio >= 10:
        return "留意：回表或过滤条件效率偏低，可考虑覆盖索引"
    return "正常"


def build_report(text, as_slowlog=False, single_sql=None):
    lines = []
    summary = {"slowlog": None, "sqls": []}
    lines.append("=" * 60)
    lines.append("慢 SQL 检查报告")
    lines.append("=" * 60)

    if as_slowlog:
        items = parse_slow_log_blocks(text)
        summary["slowlog"] = items
        lines.append("")
        lines.append("[慢日志摘要] 共 %d 条" % len(items))
        items_sorted = sorted(items, key=lambda x: -(x.get("Query_time", 0) or 0))
        for it in items_sorted[:10]:
            lines.append("  Query_time=%.3fs Lock=%.3fs Rows_sent=%s Rows_examined=%s 扫描比=%s" % (
                it.get("Query_time", 0) or 0, it.get("Lock_time", 0) or 0,
                it.get("Rows_sent", 0), it.get("Rows_examined", 0), it.get("scan_ratio", 0)))
            lines.append("    %s" % (it.get("verdict", "")))
            lines.append("    %s" % it["sql"][:180])
        worst = [i for i in items if i.get("scan_ratio", 0) and i["scan_ratio"] > 1000]
        lines.append("")
        lines.append("  扫描比超过 1000 的语句: %d 条" % len(worst))
        return "\n".join(lines) + "\n" + "=" * 60, summary

    sqls = [single_sql] if single_sql else split_sqls(strip_comments(text))
    total_score = 0
    for i, sql in enumerate(sqls, 1):
        hits = scan_sql(sql)
        hits.sort(key=lambda h: SEVERITY.get(h["level"], 9))
        score = sum(10 for h in hits if h["level"] == "严重") + \
            sum(5 for h in hits if h["level"] == "错误") + \
            sum(2 for h in hits if h["level"] == "警示") + \
            sum(1 for h in hits if h["level"] == "提示")
        total_score += score
        lines.append("")
        lines.append("[SQL %d] 风险分 %d" % (i, score))
        lines.append("  %s" % sql[:220])
        for h in hits:
            lines.append("  [%s] %s -> %s" % (h["level"], h["name"], h["msg"]))
        if not hits:
            lines.append("  未命中已知反模式")
        summary["sqls"].append({"sql": sql, "score": score, "hits": hits})
    lines.append("")
    lines.append("总风险分: %d（越高越优先处理）" % total_score)
    lines.append("")
    lines.append("免责: 静态检查只看写法，真实耗时以慢日志 / EXPLAIN ANALYZE 为准。")
    lines.append("=" * 60)
    return "\n".join(lines), summary


def selftest():
    deep = "SELECT id, order_no FROM orders WHERE tenant_id = 1 ORDER BY id LIMIT 10000, 20"
    h1 = scan_sql(deep)
    ck("深分页应被识别", any(x["name"] == "深分页" for x in h1))
    ck("深分页应为严重级", any(x["level"] == "严重" for x in h1))

    h2 = scan_sql("SELECT * FROM user WHERE DATE(create_time) = '2026-01-01'")
    ck("列套函数应被识别", any(x["name"] == "列套函数/隐式类型转换" for x in h2))
    ck("SELECT * 应被识别", any(x["name"] == "SELECT *" for x in h2))

    h3 = scan_sql("SELECT * FROM user WHERE name LIKE '%abc'")
    ck("前导通配符应被识别", any(x["name"] == "前导通配符 LIKE" for x in h3))

    h4 = scan_sql("SELECT * FROM user WHERE order_no = 20260101001")
    ck("数字比较应被识别", any(x["name"] == "字符串列与数字比较" for x in h4))

    h5 = scan_sql("SELECT * FROM user ORDER BY RAND() LIMIT 1")
    ck("RAND 排序应被识别", any(x["name"] == "ORDER BY RAND()" for x in h5))

    h6 = scan_sql("DELETE FROM user")
    ck("无条件 DELETE 应被识别", any(x["name"] == "不带条件的 UPDATE/DELETE" for x in h6))

    h7 = scan_sql("SELECT * FROM user WHERE phone = '138' OR name = 'x'")
    ck("OR 应被识别", any(x["name"] == "OR 条件" for x in h7))

    h8 = scan_sql("SELECT id FROM user WHERE id IN (SELECT user_id FROM orders)")
    ck("IN 子查询应被识别", any(x["name"] == "关联子查询" for x in h8))

    h9 = scan_sql("SELECT COUNT(*) FROM user WHERE status = 1")
    ck("COUNT 应被识别", any(x["name"] == "COUNT 大表" for x in h9))

    log = (
        "# Time: 2026-10-08T10:00:00\n"
        "# Query_time: 3.512345  Lock_time: 0.000120  Rows_sent: 10  Rows_examined: 500000\n"
        "SELECT id FROM orders WHERE tenant_id = 1 AND status = 2;\n"
        "# Query_time: 0.200000  Lock_time: 0.000000  Rows_sent: 20  Rows_examined: 400\n"
        "SELECT id FROM orders WHERE id > 100 LIMIT 20;\n"
    )
    items = parse_slow_log_blocks(log)
    ck("慢日志应解析出 2 条", len(items) == 2)
    ck("第一条扫描比应为 50000", items[0]["scan_ratio"] == 50000.0)
    ck("第一条应判定为严重", "严重" in items[0]["verdict"])
    ck("第二条应判定为留意", items[1]["verdict"].startswith("留意"))

    rep, sm = build_report(log, as_slowlog=True)
    ck("慢日志报告应为字典结构", sm["slowlog"] is not None)
    rep2, sm2 = build_report(deep + ";\n" + h9_sql(), as_slowlog=False)
    ck("SQL 模式应解析出 2 条", len(sm2["sqls"]) == 2)
    ck("总风险分应大于 0", any(s["score"] > 0 for s in sm2["sqls"]))
    return not FAILS


def h9_sql():
    return "SELECT COUNT(*) FROM user WHERE status = 1"


def main():
    ap = argparse.ArgumentParser(description="慢 SQL 静态检查器")
    ap.add_argument("--file", help="SQL 文本或慢日志文件")
    ap.add_argument("--sql", help="单条 SQL")
    ap.add_argument("--slowlog", action="store_true", help="按慢日志格式解析")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="结果写入文件")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    if not args.file and not args.sql:
        ap.error("需要 --file / --sql / --selftest")

    text = ""
    if args.file:
        text = io.open(args.file, "r", encoding="utf-8", errors="ignore").read()
    report, summary = build_report(text, as_slowlog=args.slowlog, single_sql=args.sql)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("结果已写入: %s" % out_path)


if __name__ == "__main__":
    main()
