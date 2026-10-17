# -*- coding: utf-8 -*-
"""Redis 持久化配置体检：丢数窗口测算 + fork 风险 + 高危组合检查。

用法:
  python redis_persistence_check.py --selftest
  python redis_persistence_check.py --file redis.conf
  python redis_persistence_check.py --file redis.conf --maxmemory-gb 16 --role master

也支持直接解析 `redis-cli INFO persistence` 的输出（自动识别 rdb_last_bgsave_status 等字段）。
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


FSYNC_LOSS_SEC = {"always": 0.01, "everysec": 1.0, "no": 30.0}
DEFAULT_SAVE = "900 1 300 10 60 10000"


def parse_conf(text):
    """解析 redis.conf 或 CONFIG GET 输出，返回 dict（小写键）。"""
    cfg = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if len(parts) < 2:
            continue
        cfg[parts[0].lower()] = parts[1].strip()
    return cfg


def parse_keyvalues_pairs(lines):
    """处理 `CONFIG GET *` 的 key/value 交替输出。"""
    cfg = {}
    i = 0
    while i + 1 < len(lines):
        k = lines[i].strip().lower()
        v = lines[i + 1].strip()
        if k and not k.startswith("#") and re.match(r"^[a-z0-9_-]+$", k) and v:
            cfg.setdefault(k, v)
        i += 2
    return cfg


def load_config(text):
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    cfg = parse_conf(text)
    extra = parse_keyvalues_pairs(lines)
    for k, v in extra.items():
        if k not in cfg:
            cfg[k] = v
    return cfg


def getb(cfg, key, default=None):
    v = cfg.get(key, default)
    if v is None:
        return None
    return str(v).strip().strip('"').strip("'").lower()


def is_true(v):
    return str(v).lower() in ("yes", "true", "1", "on")


def parse_save_points(s):
    """'900 1 300 10 60 10000' -> [(900,1),(300,10),(60,10000)]"""
    nums = re.findall(r"\d+", s or "")
    out = []
    for i in range(0, len(nums) - 1, 2):
        out.append((int(nums[i]), int(nums[i + 1])))
    return out


def loss_window(cfg):
    """返回 (秒, 说明)。"""
    aof = is_true(getb(cfg, "appendonly", "no"))
    fsync = getb(cfg, "appendfsync", "everysec")
    if aof:
        sec = FSYNC_LOSS_SEC.get(fsync, 1.0)
        nra = is_true(getb(cfg, "no-appendfsync-on-rewrite", "no"))
        note = "AOF(%s) 理论丢失窗口约 %s 秒" % (fsync, sec)
        if nra:
            note += "；已开 no-appendfsync-on-rewrite，重写期间 fsync 暂停，窗口会拉大到重写耗时级别"
        return sec, note
    pts = parse_save_points(getb(cfg, "save", DEFAULT_SAVE))
    if not pts:
        return None, "save 为空且未开 AOF：未开启任何持久化，进程退出即全丢"
    worst = max(s for s, _ in pts)
    return float(worst), "只开 RDB，最坏丢失最后一次快照之后的 %d 秒写入" % worst


def fork_risk(maxmemory_gb, rdb_on, interval_sec):
    """返回 (级别, 说明)。"""
    if maxmemory_gb is None:
        return "未知", "未提供 --maxmemory-gb，跳过 fork 风险评估"
    if not rdb_on:
        return "低", "未开启 RDB 快照（仅 AOF 重写时需要 fork）"
    if maxmemory_gb >= 32 and interval_sec is not None and interval_sec <= 300:
        return "高", "实例 %sGB 且快照间隔 %ss：fork 耗时长、COW 抖动明显，建议放宽间隔或改 AOF 混合" % (
            maxmemory_gb, int(interval_sec))
    if maxmemory_gb >= 16:
        return "中", "实例 %sGB：fork 约需数十毫秒到百毫秒级，注意观察 latest_fork_usec" % maxmemory_gb
    return "低", "实例 %sGB，fork 成本可接受" % maxmemory_gb


def check_issues(cfg, role, maxmemory_gb):
    """返回 [(级别, 说明)]。级别: 严重/警示/提示/好。"""
    out = []
    aof = is_true(getb(cfg, "appendonly", "no"))
    fsync = getb(cfg, "appendfsync", "everysec")
    pts = parse_save_points(getb(cfg, "save", DEFAULT_SAVE))
    rdb_on = bool(pts) and getb(cfg, "save", DEFAULT_SAVE).strip() not in ('""', "''", "")
    hybrid = is_true(getb(cfg, "aof-use-rdb-preamble", "yes"))
    stop_err = is_true(getb(cfg, "stop-writes-on-bgsave-error", "yes"))
    pct = getb(cfg, "auto-aof-rewrite-percentage", "100")
    minsz = getb(cfg, "auto-aof-rewrite-min-size", "64mb")
    role_low = (role or "master").lower()

    if not aof and not pts:
        out.append(("严重", "RDB 与 AOF 都未开启：进程退出即全部数据丢失"))
        if role_low == "master":
            out.append(("严重", "主节点无持久化：崩溃自动重启后会同步清空所有从节点（经典事故）"))
    if aof and pts and hybrid:
        out.append(("好", "已开启混合持久化（AOF + RDB 序言），兼顾恢复速度与安全性"))
    if not aof and pts:
        out.append(("警示", "只开 RDB：丢失窗口取决于快照间隔，建议同时开 AOF 混合持久化"))
    if aof and not pts and rdb_on is False:
        out.append(("提示", "未开 RDB 快照：备份只能依赖 AOF 文件，建议保留一份定期 RDB 供异地归档"))
    if fsync == "no":
        out.append(("严重", "appendfsync=no：丢数窗口由操作系统决定（通常 30 秒），不适合任何有可靠性要求的实例"))
    if fsync == "always":
        out.append(("提示", "appendfsync=always 每次写都 fsync，吞吐约为 everysec 的 1/3 到 1/10，确认业务能接受"))
    if aof and fsync == "always" and is_true(getb(cfg, "no-appendfsync-on-rewrite", "no")):
        out.append(("警示", "always + no-appendfsync-on-rewrite=yes 互相矛盾：重写期间已不再是 always 语义"))
    if not aof and fsync in ("always", "everysec"):
        pass
    if pct and str(pct) == "0":
        out.append(("警示", "auto-aof-rewrite-percentage=0 关闭了自动重写，AOF 会持续膨胀"))
    if not stop_err and (pts or aof):
        out.append(("警示", "stop-writes-on-bgsave-error=no：快照失败不再拒绝写入，必须配套监控 rdb_last_bgsave_status，否则备份可能长期静默失败"))
    if pts and max(pts)[0] > 1800:
        out.append(("提示", "存在超过 30 分钟的快照间隔，长间隔意味着更大的丢失窗口"))
    if maxmemory_gb is not None and maxmemory_gb >= 16 and any(s <= 300 for s, _ in pts):
        out.append(("警示", "大内存实例配置了高频快照：关注 latest_fork_usec 与 COW 抖动"))
    if role_low in ("slave", "replica") and not (aof or pts):
        out.append(("警示", "副本未开持久化：重启会触发全量同步，短时间占满主库带宽"))
    return out


def load_health(cfg):
    """从 INFO persistence 里取健康字段。"""
    keys = {
        "rdb_last_bgsave_status": None,
        "aof_last_bgrewrite_status": None,
        "aof_last_write_status": None,
        "rdb_last_save_time": None,
        "aof_delayed_fsync": None,
        "latest_fork_usec": None,
    }
    for k in keys:
        v = cfg.get(k)
        if v is not None:
            keys[k] = str(v).strip()
    return keys


def build_report(text, role="master", maxmemory_gb=None, now_ts=None):
    cfg = load_config(text)
    lines = []
    summary = {"issues": [], "loss_window_sec": None, "fork_risk": None}
    lines.append("=" * 60)
    lines.append("Redis 持久化配置体检  角色=%s" % (role or "master"))
    lines.append("=" * 60)
    lines.append("")
    lines.append("[解析到的关键配置]")
    for k in ("appendonly", "appendfsync", "save", "aof-use-rdb-preamble",
              "auto-aof-rewrite-percentage", "auto-aof-rewrite-min-size",
              "no-appendfsync-on-rewrite", "stop-writes-on-bgsave-error", "dir"):
        v = cfg.get(k)
        lines.append("  %-32s %s" % (k, v if v is not None else "(未设置)"))

    sec, note = loss_window(cfg)
    summary["loss_window_sec"] = sec
    summary["loss_note"] = note
    lines.append("")
    lines.append("[丢数窗口]")
    lines.append("  %s" % note)

    pts = parse_save_points(getb(cfg, "save", DEFAULT_SAVE))
    interval = min(pts)[0] if pts else None
    lvl, fmsg = fork_risk(maxmemory_gb, bool(pts), interval)
    summary["fork_risk"] = {"level": lvl, "note": fmsg}
    lines.append("")
    lines.append("[fork 风险] %s：%s" % (lvl, fmsg))

    issues = check_issues(cfg, role, maxmemory_gb)
    lines.append("")
    lines.append("[配置检查]")
    for lvl2, msg in issues:
        lines.append("  [%s] %s" % (lvl2, msg))
    summary["issues"] = [{"level": a, "msg": b} for a, b in issues]

    health = load_health(cfg)
    lines.append("")
    lines.append("[持久化健康字段]")
    for k, v in health.items():
        lines.append("  %-32s %s" % (k, v if v is not None else "(未见，非 INFO 输出)"))
    for k in ("rdb_last_bgsave_status", "aof_last_bgrewrite_status", "aof_last_write_status"):
        v = health.get(k)
        if v and v.lower() not in ("ok", "0"):
            lines.append("  [严重] %s = %s，持久化存在失败记录，需立即排查磁盘与 IO" % (k, v))
    if health.get("rdb_last_save_time") and now_ts:
        try:
            gap = int(now_ts) - int(health["rdb_last_save_time"])
            lines.append("  距上次成功快照: %d 秒" % gap)
            summary["last_save_gap_sec"] = gap
        except ValueError:
            pass
    summary["health"] = health

    lines.append("")
    lines.append("免责: 静态配置检查不等于实际可靠性，必须做恢复演练验证。")
    lines.append("=" * 60)
    return "\n".join(lines), summary


def selftest():
    cfg_all = load_config("appendonly yes\nappendfsync everysec\nappendfilename x.aof\nsave 900 1\naof-use-rdb-preamble yes")
    ck("应解析 appendonly", getb(cfg_all, "appendonly") == "yes")
    ck("应解析 save", getb(cfg_all, "save") == "900 1")

    sec, note = loss_window({"appendonly": "yes", "appendfsync": "everysec"})
    ck("everysec 窗口应为 1 秒", sec == 1.0)
    ck("everysec 说明应含 seconds", "everysec" in note)

    sec2, _ = loss_window({"appendonly": "yes", "appendfsync": "always"})
    ck("always 窗口应小于 1", sec2 < 1.0)

    sec3, _ = loss_window({"appendonly": "yes", "appendfsync": "no"})
    ck("no 窗口应为 30 秒", sec3 == 30.0)

    sec4, note4 = loss_window({"appendonly": "no", "save": "900 1"})
    ck("仅 RDB 窗口应为 900", sec4 == 900.0)
    ck("仅 RDB 说明应提到快照", "快照" in note4)

    sec5, note5 = loss_window({"appendonly": "no", "save": '""'})
    ck("全关应返回 None", sec5 is None)
    ck("全关应提示全丢", "全丢" in note5)

    pts = parse_save_points("900 1 300 10 60 10000")
    ck("应解析出 3 个快照点", len(pts) == 3)
    ck("第一个快照点应为 (900,1)", pts[0] == (900, 1))

    lvl, msg = fork_risk(32, True, 300)
    ck("大内存高频快照应判高风险", lvl == "高")
    lvl2, _ = fork_risk(4, True, 900)
    ck("小内存应判低风险", lvl2 == "低")
    lvl3, _ = fork_risk(16, False, 900)
    ck("未开 RDB 应判低风险", lvl3 == "低")

    issues = check_issues({"appendonly": "no", "save": '""'}, "master", None)
    ck("全关应报严重", any(a == "严重" for a, _ in issues))
    ck("主节点无持久化应提示清空从节点", any("清空" in b for _, b in issues))

    issues2 = check_issues({"appendonly": "yes", "appendfsync": "no", "save": "900 1"}, "master", 8)
    ck("fsync=no 应报严重", any("no：" in b or "appendfsync=no" in b for _, b in issues2))

    issues3 = check_issues({"appendonly": "yes", "appendfsync": "everysec",
                            "auto-aof-rewrite-percentage": "0", "save": "900 1"}, "master", 8)
    ck("percentage=0 应报警示", any("膨胀" in b for _, b in issues3))

    _, sm = build_report("appendonly yes\nappendfsync everysec\nsave 900 1\naof-use-rdb-preamble yes",
                         role="master", maxmemory_gb=8)
    ck("混合持久化应标记良好", all(i["level"] != "严重" for i in sm["issues"]))
    ck("应输出丢数窗口", sm["loss_window_sec"] == 1.0)

    _, sm2 = build_report("appendonly no\nsave 3600 1", role="master", maxmemory_gb=4)
    ck("只开长间隔 RDB 应报警示", any(i["level"] == "警示" for i in sm2["issues"]))
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="Redis 持久化配置体检")
    ap.add_argument("--file", help="redis.conf 或 INFO persistence 输出文本")
    ap.add_argument("--role", default="master", choices=["master", "slave", "replica"], help="实例角色")
    ap.add_argument("--maxmemory-gb", type=float, help="实例 maxmemory（GB），用于 fork 风险评估")
    ap.add_argument("--now", type=int, help="当前时间戳，用于计算距上次快照间隔")
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
    report, summary = build_report(text, args.role, args.maxmemory_gb, args.now)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("结果已写入: %s" % out_path)


if __name__ == "__main__":
    main()
