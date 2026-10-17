# -*- coding: utf-8 -*-
"""Kafka \u5206\u533a\u6570\u4f30\u7b97\u4e0e topic \u4f53\u68c0\u3002

\u7528\u6cd5:
  python kafka_partition_calc.py --selftest
  python kafka_partition_calc.py --target-mbps 120 --cons-mbps 200 \
      --prod-per-partition 10 --cons-per-partition 5 \
      --consumers 8 --brokers 3 --rf 3 --growth 1.5 --retention-hours 168
  python kafka_partition_calc.py --file topics.txt --consumers-file groups.txt --ulimit 65536
"""
import argparse
import io
import json
import math
import os
import re
import sys

FAILS = []

FD_PER_REPLICA = 3
FILES_PER_SEGMENT = 3
MAX_PART_PER_BROKER = 4000
WARN_PART_PER_BROKER = 2000
MAX_PART_SINGLE_TOPIC = 200
MAX_SIZE_PER_PARTITION_GB = 100


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


def ceil_to_multiple(n, m):
    """\u5411\u4e0a\u53d6\u6574\u5230 m \u7684\u6574\u6570\u500d\uff0c\u4fdd\u8bc1\u5206\u533a\u5728 broker \u95f4\u5747\u5300\u5206\u5e03\u3002"""
    if n <= 0:
        return 0
    if m is None or m <= 1:
        return int(n)
    return int(math.ceil(float(n) / m) * m)


def suggest_partitions(target_mbps, cons_mbps, prod_pp, cons_pp,
                       consumers, brokers, growth=1.5):
    """\u4e09\u4fa7\u53d6\u6700\u5927\uff1a\u751f\u4ea7\u4fa7 / \u6d88\u8d39\u4fa7 / \u6d88\u8d39\u8005\u5e76\u53d1\u3002"""
    need_prod = int(math.ceil(target_mbps * growth / prod_pp)) if target_mbps > 0 and prod_pp > 0 else 0
    need_cons = int(math.ceil(cons_mbps * growth / cons_pp)) if cons_mbps > 0 and cons_pp > 0 else 0
    need_user = int(consumers) if consumers and consumers > 0 else 0
    raw = max(need_prod, need_cons, need_user)
    aligned = ceil_to_multiple(raw, brokers)
    driver = "\u751f\u4ea7\u4fa7"
    if need_cons >= need_prod and need_cons >= need_user and need_cons > 0:
        driver = "\u6d88\u8d39\u4fa7"
    if need_user > need_prod and need_user > need_cons and need_user > 0:
        driver = "\u6d88\u8d39\u8005\u5e76\u53d1"
    return {"need_prod": need_prod, "need_cons": need_cons, "need_user": need_user,
            "raw": raw, "recommended": aligned, "driver": driver, "growth": growth}


def per_partition_mbps(total_mbps, partitions):
    if partitions <= 0:
        return 0.0
    return total_mbps / float(partitions)


def partition_gb(per_part_mbps, hours):
    """\u5355\u5206\u533a\u4fdd\u7559\u6570\u636e\u91cf(GB) = \u901f\u7387(MB/s) * 3600 * \u5c0f\u65f6 / 1024\u3002"""
    if per_part_mbps <= 0 or hours <= 0:
        return 0.0
    return per_part_mbps * 3600.0 * float(hours) / 1024.0


def file_count(partitions, rf, seg_gb, per_gb):
    """\u78c1\u76d8\u6587\u4ef6\u6570\u4f30\u7b97\uff1a\u6bcf\u526f\u672c ceil(\u6570\u636e\u91cf/segment) \u4e2a\u6bb5\uff0c\u6bcf\u6bb5 3 \u4e2a\u6587\u4ef6\u3002"""
    if partitions <= 0:
        return 0, 0
    segs = 1
    if seg_gb and seg_gb > 0 and per_gb > 0:
        segs = max(1, int(math.ceil(per_gb / float(seg_gb))))
    total = partitions * max(1, rf) * segs * FILES_PER_SEGMENT
    return segs, total


def fd_estimate(partitions, rf, brokers):
    """\u6253\u5f00\u7684\u6587\u4ef6\u53e5\u67c4\u4f30\u7b97\uff1a\u6bcf\u5206\u533a\u6bcf\u526f\u672c\u7684\u6d3b\u52a8\u6bb5\u7ea6 FD_PER_REPLICA \u4e2a fd\u3002"""
    if partitions <= 0 or brokers <= 0:
        return 0
    return int(math.ceil(partitions * max(1, rf) / float(brokers) * FD_PER_REPLICA))


def failover_leaders(partitions, rf, brokers):
    """\u5355\u4e2a broker \u5b95\u673a\u540e\u9700\u8981\u91cd\u65b0\u9009\u4e3b\u7684\u5927\u81f4 leader \u6570\u3002"""
    if partitions <= 0 or brokers <= 0:
        return 0
    return int(math.ceil(partitions * max(1, rf) / float(brokers)))


def failover_ms(partitions, rf, brokers, per_partition_ms=2):
    return failover_leaders(partitions, rf, brokers) * per_partition_ms


def parse_consumer_map(path):
    """topic=\u6d88\u8d39\u8005\u6570 \u6bcf\u884c\u4e00\u6761\uff0c\u4e5f\u652f\u6301 topic:consumers \u5199\u6cd5\u3002"""
    out = {}
    if not path or not os.path.exists(path):
        return out
    for line in io.open(path, "r", encoding="utf-8", errors="ignore"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = re.split(r"[=:]", s, maxsplit=1)
        if len(parts) != 2:
            continue
        name = parts[0].strip()
        try:
            out[name] = int(float(parts[1].strip()))
        except ValueError:
            pass
    return out


def parse_configs(s):
    cfg = {}
    for kv in (s or "").split(","):
        kv = kv.strip()
        if not kv or "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        cfg[k.strip().lower()] = v.strip()
    return cfg


def int_or(v, default=0):
    try:
        return int(float(str(v).strip()))
    except (ValueError, TypeError):
        return default


ALIAS_PART = ("partitions", "partitioncount", "partition_count", "num.partitions")
ALIAS_RF = ("rf", "replicationfactor", "replication.factor", "replication_factor")
ALIAS_CONSUMERS = ("consumers", "consumer")


def parse_describe(text):
    """\u89e3\u6790 kafka-topics --describe \u8f93\u51fa\uff0c\u4e5f\u517c\u5bb9 topic=xx partitions=xx rf=xx \u7b80\u5199\u3002"""
    topics = {}
    order = []
    for line in text.splitlines():
        raw = line.rstrip("\n")
        if not raw.strip():
            continue
        m_topic = re.search(r"Topic:\s*(\S+)", raw)
        if not m_topic:
            continue
        name = m_topic.group(1)
        m_cnt = re.search(r"PartitionCount:\s*(\d+)", raw)
        if not m_cnt:
            continue  # \u5206\u533a\u660e\u7ec6\u884c\uff0c\u8df3\u8fc7
        rf = int_or(re.search(r"ReplicationFactor:\s*(\d+)", raw).group(1)
                    if re.search(r"ReplicationFactor:\s*(\d+)", raw) else 1, 1)
        m_cfg = re.search(r"Configs:\s*(.*)$", raw)
        cfg = parse_configs(m_cfg.group(1)) if m_cfg else {}
        if name not in topics:
            topics[name] = {"topic": name, "partitions": 0, "rf": rf, "configs": cfg}
            order.append(name)
        topics[name]["partitions"] = int(m_cnt.group(1))
        topics[name]["rf"] = rf
        topics[name]["configs"].update(cfg)

    for line in text.splitlines():
        s = line.strip()
        if not s or "topic=" not in s.lower():
            continue
        if re.search(r"Topic:", s):
            continue
        kv = {}
        for tok in s.split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                kv[k.strip().lower()] = v.strip()
        if not kv:
            continue
        name = kv.get("topic")
        if not name:
            continue
        cfg = dict(kv)
        if name not in topics:
            topics[name] = {"topic": name, "partitions": 0, "rf": 1, "configs": cfg}
            order.append(name)
        for k in ALIAS_PART:
            if k in kv:
                topics[name]["partitions"] = int_or(kv[k])
        for k in ALIAS_RF:
            if k in kv:
                topics[name]["rf"] = int_or(kv[k], 1)
        for k in ALIAS_CONSUMERS:
            if k in kv:
                topics[name]["consumers"] = int_or(kv[k])
        topics[name]["configs"].update(cfg)

    return [topics[n] for n in order]


def bool_true(v):
    return str(v).strip().lower() in ("true", "yes", "1")


def audit_topic(t, brokers=1, consumer_map=None, ulimit=0,
                max_per_broker=MAX_PART_PER_BROKER, election_ms=2):
    issues = []
    goods = []
    name = t.get("topic", "?")
    p = int_or(t.get("partitions"), 0)
    rf = max(1, int_or(t.get("rf"), 1))
    cfg = t.get("configs", {}) or {}
    consumers = int_or(t.get("consumers"), 0)
    if not consumers and consumer_map:
        consumers = int_or(consumer_map.get(name), 0)

    min_isr = cfg.get("min.insync.replicas")
    unclean = cfg.get("unclean.leader.election.enable")
    ret_ms = cfg.get("retention.ms")
    ret_bytes = cfg.get("retention.bytes")

    if p <= 0:
        issues.append(("\u63d0\u793a", "\u672a\u89e3\u6790\u5230\u5206\u533a\u6570\uff0c\u8df3\u8fc7\u5bb9\u91cf\u6838\u7b97"))
        return {"topic": name, "partitions": p, "rf": rf, "consumers": consumers,
                "issues": issues, "goods": goods}

    if brokers > 1 and p < brokers:
        issues.append(("\u9519\u8bef", "\u5206\u533a\u6570 %d \u5c11\u4e8e broker \u6570 %d\uff0c\u5206\u533a\u65e0\u6cd5\u5747\u5300\u5206\u5e03\u5230\u6240\u6709\u8282\u70b9" % (p, brokers)))
    if brokers > 1 and p % brokers != 0:
        issues.append(("\u63d0\u793a", "\u5206\u533a\u6570 %d \u4e0d\u662f broker \u6570 %d \u7684\u6574\u6570\u500d\uff0c\u5206\u5e03\u53ef\u80fd\u4e0d\u5747" % (p, brokers)))
    if p == 1 and consumers > 1:
        issues.append(("\u9519\u8bef", "\u5355\u5206\u533a topic \u5374\u6709 %d \u4e2a\u6d88\u8d39\u8005\uff0c\u5b9e\u9645\u53ea\u6709 1 \u4e2a\u80fd\u5de5\u4f5c\uff08\u4e5f\u53ef\u80fd\u662f\u523b\u610f\u4fdd\u5168\u5c40\u987a\u5e8f\uff09" % consumers))
    if consumers > p:
        issues.append(("\u9519\u8bef", "\u6d88\u8d39\u8005\u6570 %d \u5927\u4e8e\u5206\u533a\u6570 %d\uff0c\u6709 %d \u4e2a\u6d88\u8d39\u8005\u62ff\u4e0d\u5230\u5206\u533a\u6c38\u8fdc\u7a7a\u8f6c" % (
            consumers, p, consumers - p)))
    elif consumers > 0 and consumers == p:
        issues.append(("\u63d0\u793a", "\u6d88\u8d39\u8005\u6570\u5df2\u7b49\u4e8e\u5206\u533a\u6570\uff0c\u518d\u6269\u5bb9\u6d88\u8d39\u8005\u65e0\u6548\uff0c\u53ea\u80fd\u52a0\u5206\u533a"))

    part_per_broker = int(math.ceil(p * rf / float(max(1, brokers))))
    if part_per_broker > max_per_broker:
        issues.append(("\u4e25\u91cd", "\u5355 broker \u542b\u526f\u672c\u5206\u533a\u6570 %d \u8d85\u8fc7\u5efa\u8bae\u4e0a\u9650 %d\uff0c\u9009\u4e3e\u4e0e\u6587\u4ef6\u53e5\u67c4\u538b\u529b\u5927" % (
            part_per_broker, max_per_broker)))
    elif part_per_broker > WARN_PART_PER_BROKER:
        issues.append(("\u8b66\u793a", "\u5355 broker \u542b\u526f\u672c\u5206\u533a\u6570 %d \u5df2\u8fbe\u544a\u8b66\u7ebf %d" % (part_per_broker, WARN_PART_PER_BROKER)))

    if p > MAX_PART_SINGLE_TOPIC:
        issues.append(("\u63d0\u793a", "\u5355 topic \u5206\u533a\u6570 %d \u8d85\u8fc7 %d\uff0c\u5148\u786e\u8ba4\u662f\u4e0d\u662f\u4e1a\u52a1\u62c6\u5206\u4e0d\u5bf9" % (p, MAX_PART_SINGLE_TOPIC)))

    if rf < 3:
        issues.append(("\u8b66\u793a", "\u526f\u672c\u56e0\u5b50 %d \u4f4e\u4e8e 3\uff0c\u5355\u526f\u672c\u5bb9\u9519\u80fd\u529b\u4e0d\u8db3\uff08\u526f\u672c\u4e22\u5931\u5373\u4e0d\u53ef\u7528\uff09" % rf))
    if min_isr is not None:
        v = int_or(min_isr, 0)
        if v >= rf and rf > 1:
            issues.append(("\u4e25\u91cd", "min.insync.replicas=%d \u7b49\u4e8e\u526f\u672c\u56e0\u5b50 %d\uff0c\u4efb\u4e00\u526f\u672c\u6296\u52a8\u5373\u5728 acks=all \u4e0b\u4e0d\u53ef\u5199" % (v, rf)))
        elif v < 2 and rf >= 2:
            issues.append(("\u8b66\u793a", "min.insync.replicas=%d \u5c0f\u4e8e 2\uff0cacks=all \u5931\u53bb\u610f\u4e49" % v))
        elif v == 2 and rf == 3:
            goods.append("min.insync.replicas=2 \u914d rf=3\uff0c\u5bb9\u5fcd 1 \u4e2a\u526f\u672c\u6389\u7ebf\uff0c\u6807\u51c6\u53ef\u7528\u914d\u7f6e")
    if unclean is not None and bool_true(unclean):
        issues.append(("\u4e25\u91cd", "unclean.leader.election.enable=true\uff1a\u5141\u8bb8\u4e0d\u540c\u6b65\u526f\u672c\u6210\u4e3a leader\uff0c\u53ef\u80fd\u9759\u9ed8\u4e22\u6570\u636e"))
    if ret_ms is not None and ret_bytes is not None:
        issues.append(("\u63d0\u793a", "retention.ms \u4e0e retention.bytes \u540c\u65f6\u914d\u7f6e\uff0c\u8c01\u5148\u89e6\u53d1\u8c01\u751f\u6548\uff0c\u786e\u8ba4\u4e1a\u52a1\u9884\u671f"))
    if ret_ms is not None and int_or(ret_ms, 0) > 30 * 24 * 3600 * 1000:
        issues.append(("\u63d0\u793a", "retention.ms \u8d85\u8fc7 30 \u5929\uff0c\u9700\u6838\u7b97\u5355\u5206\u533a\u4f53\u79ef\u662f\u5426\u4f1a\u8d85\u8fc7 %d GB" % MAX_SIZE_PER_PARTITION_GB))

    fd = fd_estimate(p, rf, max(1, brokers))
    if ulimit and fd > ulimit * 0.7:
        issues.append(("\u4e25\u91cd", "\u4f30\u7b97\u53e5\u67c4\u5360\u7528 %d \u63a5\u8fd1 ulimit %d\uff0c\u5b58\u5728 Too many open files \u98ce\u9669" % (fd, ulimit)))
    ms = failover_ms(p, rf, max(1, brokers), election_ms)
    if ms >= 60000:
        issues.append(("\u4e25\u91cd", "\u5355 broker \u5b95\u673a\u9700\u91cd\u9009\u7ea6 %d \u4e2a leader\uff0c\u6309 %dms/\u4e2a\u4f30\u7b97\u6062\u590d\u7ea6 %.1f \u5206\u949f" % (
            failover_leaders(p, rf, max(1, brokers)), election_ms, ms / 60000.0)))
    elif failover_leaders(p, rf, max(1, brokers)) > WARN_PART_PER_BROKER:
        issues.append(("\u8b66\u793a", "\u5355 broker \u5b95\u673a\u9700\u91cd\u9009\u7ea6 %d \u4e2a leader\uff0c\u6062\u590d\u65f6\u95f4\u9700\u5b9e\u6d4b\u786e\u8ba4" % (
            failover_leaders(p, rf, max(1, brokers)))))
    return {"topic": name, "partitions": p, "rf": rf, "consumers": consumers,
            "part_per_broker": part_per_broker, "open_fd": fd,
            "failover_leaders": failover_leaders(p, rf, max(1, brokers)),
            "issues": issues, "goods": goods}


def level_rank(lv):
    return {"\u4e25\u91cd": 0, "\u9519\u8bef": 1, "\u8b66\u793a": 2, "\u63d0\u793a": 3}.get(lv, 4)


def build_report(args, text=None):
    lines = []
    summary = {}
    lines.append("=" * 62)
    lines.append("Kafka \u5206\u533a\u89c4\u5212\u4e0e topic \u4f53\u68c0\u62a5\u544a")
    lines.append("=" * 62)

    if args.file and text:
        topics = parse_describe(text)
        cmap = parse_consumer_map(args.consumers_file)
        lines.append("")
        lines.append("[\u89e3\u6790] \u5171 %d \u4e2a topic" % len(topics))
        items = []
        for t in topics:
            r = audit_topic(t, args.brokers, cmap, args.ulimit,
                            MAX_PART_PER_BROKER, args.election_ms)
            items.append(r)
            lines.append("")
            lines.append("[topic] %s  \u5206\u533a=%d  rf=%d  \u6d88\u8d39\u8005=%s  \u5355broker\u542b\u526f\u672c\u5206\u533a=%s" % (
                r["topic"], r["partitions"], r["rf"],
                r["consumers"] if r["consumers"] else "-",
                r.get("part_per_broker", "-")))
            if r.get("open_fd"):
                lines.append("  \u4f30\u7b97\u53e5\u67c4/ broker: %d   \u5b95\u673a\u9700\u91cd\u9009 leader: %d" % (
                    r["open_fd"], r["failover_leaders"]))
            r["issues"].sort(key=lambda x: level_rank(x[0]))
            for lv, msg in r["issues"]:
                lines.append("  [%s] %s" % (lv, msg))
            for g in r["goods"]:
                lines.append("  [\u597d] %s" % g)
        summary["topics"] = [{
            "topic": r["topic"], "partitions": r["partitions"], "rf": r["rf"],
            "consumers": r["consumers"],
            "issues": [{"level": a, "msg": b} for a, b in r["issues"]],
            "goods": r["goods"]} for r in items]
        summary["problems"] = sum(len(r["issues"]) for r in items)
        lines.append("")
        lines.append("\u95ee\u9898\u9879\u5408\u8ba1: %d" % summary["problems"])
    else:
        s = suggest_partitions(args.target_mbps, args.cons_mbps,
                               args.prod_per_partition, args.cons_per_partition,
                               args.consumers, args.brokers, args.growth)
        summary["suggest"] = s
        lines.append("")
        lines.append("[\u8f93\u5165] \u751f\u4ea7\u76ee\u6807 %.1f MB/s  \u6d88\u8d39\u76ee\u6807 %.1f MB/s  \u5197\u4f59\u7cfb\u6570 %.2f" % (
            args.target_mbps, args.cons_mbps, args.growth))
        lines.append("       \u5355\u5206\u533a\u751f\u4ea7 %.1f MB/s  \u5355\u5206\u533a\u6d88\u8d39 %.1f MB/s  \u6d88\u8d39\u8005 %d  broker %d  rf %d" % (
            args.prod_per_partition, args.cons_per_partition, args.consumers, args.brokers, args.rf))
        lines.append("")
        lines.append("[\u5efa\u8bae\u5206\u533a\u6570]")
        lines.append("  \u751f\u4ea7\u4fa7 P_prod = ceil(%.1f * %.2f / %.1f) = %d" % (
            args.target_mbps, args.growth, args.prod_per_partition, s["need_prod"]))
        lines.append("  \u6d88\u8d39\u4fa7 P_cons = ceil(%.1f * %.2f / %.1f) = %d" % (
            args.cons_mbps, args.growth, args.cons_per_partition, s["need_cons"]))
        lines.append("  \u6d88\u8d39\u8005\u5e76\u53d1 P_user = %d" % s["need_user"])
        lines.append("  \u53d6\u6700\u5927\u503c = %d\uff0c\u5bf9\u9f50 broker \u500d\u6570\u540e = %d\uff08\u51b3\u5b9a\u4fa7\uff1a%s\uff09" % (
            s["raw"], s["recommended"], s["driver"]))

        lines.append("")
        lines.append("[\u95e8\u69db\u6838\u67e5]")
        prod_rate = per_partition_mbps(args.target_mbps, s["recommended"])
        cons_rate = per_partition_mbps(args.cons_mbps, s["recommended"])
        gb = partition_gb(max(prod_rate, cons_rate), args.retention_hours)
        flags = []
        if gb > MAX_SIZE_PER_PARTITION_GB:
            flags.append(("\u4e25\u91cd", "\u5355\u5206\u533a\u4f53\u79ef %.1f GB \u8d85\u8fc7\u5efa\u8bae\u4e0a\u9650 %d GB\uff1a\u52a0\u5206\u533a\u6216\u7f29\u77ed\u4fdd\u7559\u65f6\u95f4" % (
                gb, MAX_SIZE_PER_PARTITION_GB)))
        else:
            flags.append(("\u597d", "\u5355\u5206\u533a\u4f53\u79ef %.1f GB\uff0c\u5728 %d GB \u5efa\u8bae\u8303\u56f4\u5185" % (gb, MAX_SIZE_PER_PARTITION_GB)))
        segs, files = file_count(s["recommended"], args.rf, args.seg_gb, gb)
        fd = fd_estimate(s["recommended"], args.rf, max(1, args.brokers))
        ppb = int(math.ceil(s["recommended"] * args.rf / float(max(1, args.brokers))))
        if ppb > MAX_PART_PER_BROKER:
            flags.append(("\u4e25\u91cd", "\u5355 broker \u542b\u526f\u672c\u5206\u533a\u6570 %d \u8d85\u8fc7 %d" % (ppb, MAX_PART_PER_BROKER)))
        elif ppb > WARN_PART_PER_BROKER:
            flags.append(("\u8b66\u793a", "\u5355 broker \u542b\u526f\u672c\u5206\u533a\u6570 %d \u8d85\u8fc7\u544a\u8b66\u7ebf %d" % (ppb, WARN_PART_PER_BROKER)))
        else:
            flags.append(("\u597d", "\u5355 broker \u542b\u526f\u672c\u5206\u533a\u6570 %d" % ppb))
        if args.ulimit and fd > args.ulimit * 0.7:
            flags.append(("\u4e25\u91cd", "\u4f30\u7b97\u53e5\u67c4 %d \u63a5\u8fd1 ulimit %d" % (fd, args.ulimit)))
        leaders = failover_leaders(s["recommended"], args.rf, max(1, args.brokers))
        ms = failover_ms(s["recommended"], args.rf, max(1, args.brokers), args.election_ms)
        if ms >= 60000:
            flags.append(("\u4e25\u91cd", "\u5355 broker \u5b95\u673a\u9700\u91cd\u9009 %d \u4e2a leader\uff0c\u4f30\u7b97\u6062\u590d %.1f \u5206\u949f" % (
                leaders, ms / 60000.0)))
        else:
            flags.append(("\u597d", "\u5355 broker \u5b95\u673a\u9700\u91cd\u9009 %d \u4e2a leader\uff0c\u4f30\u7b97\u6062\u590d %.1f \u79d2" % (
                leaders, ms / 1000.0)))
        if args.consumers and args.consumers > s["recommended"]:
            flags.append(("\u9519\u8bef", "\u6d88\u8d39\u8005\u6570 %d \u5927\u4e8e\u5efa\u8bae\u5206\u533a\u6570 %d\uff0c\u6709 %d \u4e2a\u7a7a\u8f6c" % (
                args.consumers, s["recommended"], args.consumers - s["recommended"])))

        lines.append("  \u6bcf\u4e2a\u5206\u533a\u751f\u4ea7\u901f\u7387 %.2f MB/s  \u6d88\u8d39\u901f\u7387 %.2f MB/s" % (prod_rate, cons_rate))
        lines.append("  \u5355\u5206\u533a\u4fdd\u7559\u4f53\u79ef: %.1f GB\uff08\u4fdd\u7559 %d \u5c0f\u65f6\uff09" % (gb, args.retention_hours))
        lines.append("  segment \u6570/\u5206\u533a: %d\uff0c\u78c1\u76d8\u6587\u4ef6\u603b\u6570: %d" % (segs, files))
        lines.append("  \u4f30\u7b97\u53e5\u67c4/ broker: %d" % fd)
        for lv, msg in flags:
            lines.append("  [%s] %s" % (lv, msg))
        summary["checks"] = [{"level": a, "msg": b} for a, b in flags]
        summary["recommended"] = s["recommended"]

        lines.append("")
        lines.append("[\u6269\u5bb9\u98ce\u9669]")
        if args.has_key:
            lines.append("  [\u4e25\u91cd] \u8be5 topic \u6709\u4e1a\u52a1 key\uff0c\u6269\u5bb9\u4f1a\u5bfc\u81f4 hash(key) \u53d6\u6a21\u5206\u6bcd\u53d8\u5316\u9020\u6210\u91cd\u5206\u5e03\uff0c\u540c key \u987a\u5e8f\u88ab\u6253\u65ad")
            lines.append("         \u5904\u7f6e\uff1a\u65b0\u5efa topic \u53cc\u5199\u8fc1\u79fb\uff08\u89c1 rules/partition_sizing.md \u7b2c\u4e03\u8282 \u505a\u6cd5 B\uff09")
            summary["risk"] = "key-reroute"
        else:
            lines.append("  [\u63d0\u793a] \u65e0\u4e1a\u52a1 key \u65f6\u53ef\u76f4\u63a5\u6269\u5206\u533a\uff0c\u63a5\u53d7\u8dc3\u8fc1\u671f\u5206\u5e03\u4e0d\u5747")
            summary["risk"] = "plain"
        lines.append("  \u6ce8\u610f\uff1a\u5206\u533a\u6570\u53ea\u80fd\u52a0\u4e0d\u80fd\u51cf\uff0c\u4e14\u5386\u53f2\u6570\u636e\u4e0d\u4f1a\u81ea\u52a8\u642c\u8fc1\u5230\u65b0\u5206\u533a")

    lines.append("")
    lines.append("\u514d\u8d23: \u7ed3\u8bba\u57fa\u4e8e\u8f93\u5165\u53c2\u6570\u7684\u9759\u6001\u4f30\u7b97\uff0c\u771f\u5b9e\u541e\u5410\u4e0e\u6062\u590d\u65f6\u95f4\u4ee5\u538b\u6d4b\u548c\u7ebf\u4e0a\u89c2\u6d4b\u4e3a\u51c6\u3002")
    lines.append("=" * 62)
    return "\n".join(lines), summary


TOPICS_SAMPLE = """Topic: orders\tTopicId: aaa\tPartitionCount: 12\tReplicationFactor: 3\tConfigs: retention.ms=604800000,min.insync.replicas=2
Topic: logs\tTopicId: bbb\tPartitionCount: 200\tReplicationFactor: 2\tConfigs: retention.ms=604800000,retention.bytes=10737418240,unclean.leader.election.enable=true
Topic: tiny\tTopicId: ccc\tPartitionCount: 2\tReplicationFactor: 1\tConfigs:
"""

GROUPS_SAMPLE = """orders=16\nlogs=8\n"""


def selftest():
    ck("10 \u5bf9\u9f50 3 \u5e94\u4e3a 12", ceil_to_multiple(10, 3) == 12)
    ck("12 \u5bf9\u9f50 3 \u5e94\u4e3a 12", ceil_to_multiple(12, 3) == 12)

    s = suggest_partitions(120, 200, 10, 5, 8, 3, 1.5)
    ck("\u751f\u4ea7\u4fa7\u5e94\u4e3a 18", s["need_prod"] == 18)
    ck("\u6d88\u8d39\u4fa7\u5e94\u4e3a 60", s["need_cons"] == 60)
    ck("\u6700\u7ec8\u5efa\u8bae\u5e94\u4e3a 60", s["recommended"] == 60)
    ck("\u51b3\u5b9a\u4fa7\u5e94\u4e3a\u6d88\u8d39\u4fa7", s["driver"] == "\u6d88\u8d39\u4fa7")

    s2 = suggest_partitions(50, 50, 10, 20, 0, 4, 1.0)
    ck("\u65e0\u6d88\u8d39\u8005\u5e76\u53d1\u65f6\u53d6\u751f\u4ea7\u4fa7 5", s2["raw"] == 5)
    ck("5 \u5bf9\u9f50 4 \u5e94\u4e3a 8", s2["recommended"] == 8)

    ck("\u5355\u5206\u533a\u901f\u7387\u8ba1\u7b97", abs(per_partition_mbps(100, 20) - 5.0) < 0.001)
    g = partition_gb(1.0, 168)
    ck("1MB/s \u4fdd\u7559 168 \u5c0f\u65f6\u7ea6 590GB", abs(g - 590.625) < 0.5)

    segs1, f1 = file_count(60, 3, 1.0, 590.625)
    ck("590GB \u6570\u636e\u6309 1GB segment \u5e94\u4e3a 591 \u6bb5", segs1 == 591)
    ck("\u6587\u4ef6\u603b\u6570\u5e94\u4e3a 60*3*591*3", f1 == 60 * 3 * 591 * 3)

    ck("fd \u4f30\u7b97\u5e94\u4e3a 60*3/3*3=180", fd_estimate(60, 3, 3) == 180)
    ck("\u5b95\u673a\u91cd\u9009 leader \u6570\u5e94\u4e3a 60", failover_leaders(60, 3, 3) == 60)
    ck("\u91cd\u9009\u8017\u65f6\u4f30\u7b97 60*2=120ms", failover_ms(60, 3, 3, 2) == 120)

    topics = parse_describe(TOPICS_SAMPLE)
    ck("\u5e94\u89e3\u6790\u51fa 3 \u4e2a topic", len(topics) == 3)
    ck("orders \u5206\u533a\u6570\u5e94\u4e3a 12", topics[0]["partitions"] == 12)
    ck("logs \u526f\u672c\u56e0\u5b50\u5e94\u4e3a 2", topics[1]["rf"] == 2)
    ck("\u5e94\u89e3\u6790\u51fa min.insync.replicas", topics[0]["configs"].get("min.insync.replicas") == "2")
    ck("\u5e94\u89e3\u6790\u51fa unclean \u5f00\u5173", "unclean.leader.election.enable" in topics[1]["configs"])

    cmap = {"orders": 16, "logs": 8}
    r = audit_topic(topics[0], 3, cmap, 0, MAX_PART_PER_BROKER, 2)
    texts = [b for _, b in r["issues"]]
    ck("\u6d88\u8d39\u8005 16 \u5927\u4e8e\u5206\u533a 12 \u5e94\u544a\u8b66", any("\u7a7a\u8f6c" in t for t in texts))
    ck("min.insync.replicas=2 \u914d rf=3 \u5e94\u4e3a\u597d", any("\u5bb9\u5fcd 1 \u4e2a\u526f\u672c\u6389\u7ebf" in t for t in r["goods"]))

    r2 = audit_topic(topics[1], 3, cmap, 0, MAX_PART_PER_BROKER, 2)
    t2 = [b for _, b in r2["issues"]]
    ck("unclean \u9009\u4e3e\u5f00\u542f\u5e94\u5224\u4e25\u91cd", any("\u53ef\u80fd\u9759\u9ed8\u4e22\u6570\u636e" in t for t in t2))
    ck("\u540c\u65f6\u914d retention.ms \u4e0e bytes \u5e94\u63d0\u793a", any("\u8c01\u5148\u89e6\u53d1\u8c01\u751f\u6548" in t for t in t2))

    r3 = audit_topic(topics[2], 3, None, 0, MAX_PART_PER_BROKER, 2)
    t3 = [b for _, b in r3["issues"]]
    ck("\u5206\u533a\u6570\u5c11\u4e8e broker \u6570\u5e94\u62a5\u9519\u8bef", any("\u5c11\u4e8e broker \u6570" in t for t in t3))
    ck("\u526f\u672c\u56e0\u5b50\u4f4e\u4e8e 3 \u5e94\u8b66\u793a", any("\u526f\u672c\u56e0\u5b50" in t for t in t3))

    fake_map = {}
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_groups_sample.txt")
    io.open(p, "w", encoding="utf-8").write(GROUPS_SAMPLE)
    fake_map = parse_consumer_map(p)
    ck("\u5e94\u89e3\u6790\u51fa 2 \u6761\u6d88\u8d39\u8005\u6620\u5c04", len(fake_map) == 2)
    ck("orders \u5e94\u6620\u5c04\u5230 16", fake_map.get("orders") == 16)
    if os.path.exists(p):
        os.remove(p)

    _, sm = build_report(argparse.Namespace(
        target_mbps=120, cons_mbps=200, prod_per_partition=10, cons_per_partition=5,
        consumers=8, brokers=3, rf=3, growth=1.5, retention_hours=168, seg_gb=1.0,
        file=None, consumers_file=None, ulimit=65536, election_ms=2, has_key=True), None)
    ck("\u62a5\u544a\u5e94\u7ed9\u51fa\u5efa\u8bae\u5206\u533a\u6570 60", sm.get("recommended") == 60)
    ck("\u6709 key \u65f6\u5e94\u6807\u8bb0\u4e3a\u91cd\u5206\u5e03\u98ce\u9669", sm.get("risk") == "key-reroute")
    ck("\u4f53\u4f8b\u5e94\u8bb0\u5f55\u6821\u9a8c\u9879", len(sm.get("checks", [])) >= 3)

    _, sm2 = build_report(argparse.Namespace(
        target_mbps=0, cons_mbps=0, prod_per_partition=10, cons_per_partition=5,
        consumers=0, brokers=1, rf=1, growth=1.0, retention_hours=0, seg_gb=1.0,
        file="topics.txt", consumers_file=None, ulimit=0, election_ms=2,
        has_key=False), TOPICS_SAMPLE)
    ck("\u4f53\u68c0\u6a21\u5f0f\u5e94\u89e3\u6790\u51fa 3 \u4e2a topic", len(sm2.get("topics", [])) == 3)
    ck("\u4f53\u68c0\u6a21\u5f0f\u5e94\u7edf\u8ba1\u51fa\u95ee\u9898\u9879", sm2.get("problems", 0) > 0)
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="Kafka \u5206\u533a\u6570\u4f30\u7b97\u4e0e topic \u4f53\u68c0")
    ap.add_argument("--target-mbps", type=float, default=0.0, help="\u76ee\u6807\u751f\u4ea7\u541e\u5410 MB/s")
    ap.add_argument("--cons-mbps", type=float, default=0.0, help="\u76ee\u6807\u6d88\u8d39\u541e\u5410 MB/s")
    ap.add_argument("--prod-per-partition", type=float, default=10.0, help="\u5355\u5206\u533a\u751f\u4ea7\u541e\u5410 MB/s")
    ap.add_argument("--cons-per-partition", type=float, default=10.0, help="\u5355\u5206\u533a\u6d88\u8d39\u541e\u5410 MB/s")
    ap.add_argument("--consumers", type=int, default=0, help="\u6d88\u8d39\u7ec4\u5cf0\u503c\u6d88\u8d39\u8005\u6570")
    ap.add_argument("--brokers", type=int, default=3, help="broker \u6570")
    ap.add_argument("--rf", type=int, default=3, help="\u526f\u672c\u56e0\u5b50")
    ap.add_argument("--growth", type=float, default=1.5, help="\u5197\u4f59\u7cfb\u6570\uff0c\u9ed8\u8ba4 1.5")
    ap.add_argument("--retention-hours", type=float, default=168.0, help="\u4fdd\u7559\u5c0f\u65f6\u6570")
    ap.add_argument("--seg-gb", type=float, default=1.0, help="segment \u5927\u5c0f GB")
    ap.add_argument("--has-key", action="store_true", help="topic \u662f\u5426\u6709\u4e1a\u52a1 key")
    ap.add_argument("--file", help="kafka-topics --describe \u8f93\u51fa\u6587\u4ef6\uff0c\u8fdb\u5165\u4f53\u68c0\u6a21\u5f0f")
    ap.add_argument("--consumers-file", help="topic=\u6d88\u8d39\u8005\u6570 \u6620\u5c04\u6587\u4ef6")
    ap.add_argument("--ulimit", type=int, default=0, help="\u5355 broker \u6587\u4ef6\u53e5\u67c4\u4e0a\u9650")
    ap.add_argument("--election-ms", type=int, default=2, help="\u5355\u4e2a\u5206\u533a\u91cd\u9009\u8017\u65f6\u6beb\u79d2")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6587\u4ef6")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    text = None
    if args.file:
        text = io.open(args.file, "r", encoding="utf-8", errors="ignore").read()
    else:
        if args.target_mbps <= 0:
            args.target_mbps = 0.0
        if args.cons_mbps <= 0:
            args.cons_mbps = args.target_mbps

    report, summary = build_report(args, text)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % out_path)


if __name__ == "__main__":
    main()
