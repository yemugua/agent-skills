# -*- coding: utf-8 -*-
"""微信云开发资源用量与成本核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段报告，含结论摘要、云函数用量、数据库用量、存储与流量、套餐与成本、
      超额风险与防护、降本优化清单、待办动作、边界与纪律。

只做用量核算与优化建议，实际费用以微信云开发控制台账单与官方计费说明为准。
不做单价换算，不杜撰计费标准。
退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys

FIELD_ALIAS = {
    "环境名称或ID": ["环境名称或id", "环境名称", "环境id", "环境"],
    "套餐类型": ["套餐类型", "套餐", "计费方式", "版本"],
    "当前月费用元": ["当前月费用元", "当前月费用", "月费用", "月支出", "每月费用"],
    "使用时长月": ["使用时长月", "使用时长", "已用月数", "运行月数"],
    "月调用次数万次": ["月调用次数万次", "月调用次数", "函数调用次数", "调用量"],
    "月资源使用量GBs": ["月资源使用量gbs", "月资源使用量", "资源使用量", "gbs"],
    "平均单次执行耗时ms": ["平均单次执行耗时ms", "平均单次执行耗时", "函数耗时", "执行耗时"],
    "平均内存配置MB": ["平均内存配置mb", "平均内存配置", "内存配置", "函数内存"],
    "是否有高频定时触发器": ["是否有高频定时触发器", "高频定时触发器", "定时触发器", "定时器"],
    "是否有长耗时函数": ["是否有长耗时函数", "长耗时函数", "慢函数", "是否有慢函数"],
    "月读次数万次": ["月读次数万次", "月读次数", "数据库读次数", "读次数"],
    "月写次数万次": ["月写次数万次", "月写次数", "数据库写次数", "写次数"],
    "数据库存储GB": ["数据库存储gb", "数据库存储", "数据库容量", "数据存储"],
    "是否有索引优化": ["是否有索引优化", "索引优化", "是否加索引", "索引情况"],
    "单次查询返回条数": ["单次查询返回条数", "单次查询条数", "查询返回条数", "返回条数"],
    "是否有全表扫描": ["是否有全表扫描", "全表扫描", "是否全表扫描", "大集合查询"],
    "云存储容量GB": ["云存储容量gb", "云存储容量", "存储容量", "存储使用"],
    "月下行流量GB": ["月下行流量gb", "月下行流量", "外网下行流量", "流量"],
    "是否开启静态网站托管": ["是否开启静态网站托管", "静态网站托管", "静态托管", "是否托管"],
    "是否有大文件": ["是否有大文件", "大文件", "是否有大体积文件"],
    "是否有历史冗余文件": ["是否有历史冗余文件", "历史冗余文件", "冗余文件", "是否有冗余数据"],
    "是否有突发活动流量": ["是否有突发活动流量", "突发活动流量", "活动流量", "是否有大促"],
    "是否设置用量告警": ["是否设置用量告警", "用量告警", "是否告警", "告警设置"],
    "是否清理历史数据": ["是否清理历史数据", "清理历史数据", "是否清理数据", "数据清理"],
    "期望月成本目标元": ["期望月成本目标元", "期望月成本", "成本目标", "预算"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做", "未测", "没测",
)

# 用量参考量级（仅用于判断量级，非计费标准，实际额度与计费以官方为准）
CALL_MID = 10.0        # 万次/月
CALL_HIGH = 100.0      # 万次/月
GBS_MID = 40.0         # GBs/月
READ_MID = 50.0        # 万次/月
READ_HIGH = 500.0      # 万次/月
WRITE_MID = 20.0       # 万次/月
WRITE_HIGH = 100.0     # 万次/月
DB_GB_MID = 2.0
DB_GB_HIGH = 5.0
STORE_GB_MID = 5.0
STORE_GB_HIGH = 10.0
FLOW_GB_MID = 5.0
FLOW_GB_HIGH = 20.0
ROWS_MID = 20.0
ROWS_HIGH = 100.0
FUNC_MS_MID = 1000.0
FUNC_MS_HIGH = 3000.0


def norm(s):
    if s is None:
        return ""
    out = str(s).strip()
    out = out.replace("：", ":").replace("　", " ")
    out = out.replace("（", "(").replace("）", ")")
    out = re.sub(r"\s+", "", out)
    return out.lower()


def filled(v):
    if v is None:
        return False
    return norm(v) not in {norm(t) for t in EMPTY_TOKENS}


def unknown(v):
    return not filled(v)


def fmt_num(n):
    if n is None:
        return "-"
    if isinstance(n, float):
        if n == int(n):
            return str(int(n))
        return ("%.2f" % n).rstrip("0").rstrip(".")
    return str(n)


def money(n):
    if n is None:
        return "-"
    return "¥" + fmt_num(round(float(n), 2))


def parse_num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("，", "")
    s = re.sub(r"[¥￥元人民币rmb$个次]", "", s)
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_md(path):
    data = {}
    if not path or not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            line = line.lstrip(">").strip()
        if not line:
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2:
                continue
            key_raw = cells[0]
            if set(key_raw) <= set("-: "):
                continue
            val = " ".join(c.strip() for c in cells[1:]).strip()
            if val:
                data[norm(key_raw)] = val
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    """精确匹配表头，绝不用子串 in（会串字段）。兼容未归一化的 key。"""
    aliases = sorted(FIELD_ALIAS.get(key, [key]), key=len, reverse=True)
    idx = {}
    for k, v in f.items():
        idx.setdefault(norm(k), v)
    for a in aliases:
        na = norm(a)
        if not na:
            continue
        if na in idx:
            v = idx.get(na)
            if filled(v):
                return v
        stripped = re.sub(r"^\d+[.、)]\s*", "", na)
        if stripped != na and stripped in idx:
            v = idx.get(stripped)
            if filled(v):
                return v
    return ""


NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "可以")


def yesno(text):
    if unknown(text):
        return None
    n = norm(text)
    for w in NEG_WORDS:
        if n.startswith(w):
            return False
    for w in POS_WORDS:
        if n.startswith(w):
            return True
    return None


def level(v, mid, high):
    """量级分级：0=低 1=中 2=高。"""
    if v is None:
        return None
    if v > high:
        return 2
    if v > mid:
        return 1
    return 0


def check_function(f):
    """云函数用量：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    calls = parse_num(get_text(f, "月调用次数万次"))
    gbs = parse_num(get_text(f, "月资源使用量GBs"))
    ms = parse_num(get_text(f, "平均单次执行耗时ms"))
    mem = parse_num(get_text(f, "平均内存配置MB"))
    timer = yesno(get_text(f, "是否有高频定时触发器"))
    slow = yesno(get_text(f, "是否有长耗时函数"))

    lv_calls = level(calls, CALL_MID, CALL_HIGH)
    lv_gbs = level(gbs, GBS_MID, GBS_MID * 5)
    lv_ms = level(ms, FUNC_MS_MID, FUNC_MS_HIGH)

    items.append("月调用次数：%s" % (("%s 万次" % fmt_num(calls)) if calls is not None else "未填写"))
    items.append("月资源使用量：%s" % (("%s GBs" % fmt_num(gbs)) if gbs is not None else "未填写"))
    items.append("平均单次执行耗时：%s" % (("%s ms" % fmt_num(ms)) if ms is not None else "未填写"))
    items.append("平均内存配置：%s" % (("%s MB" % fmt_num(mem)) if mem is not None else "未填写"))

    if calls is None and gbs is None:
        risk.append("未填写云函数调用次数与资源使用量，无法评估函数侧用量")
    else:
        if lv_calls == 2:
            risk.append("月调用 %s 万次属高量级：优先排查是否有轮询、重复调用或定时器空转" % fmt_num(calls))
        elif lv_calls == 1:
            risk.append("月调用 %s 万次达中等量级，关注增长趋势" % fmt_num(calls))
        if lv_gbs == 2:
            risk.append("月资源使用量 %s GBs 属高量级：与函数耗时和内存配置直接相关" % fmt_num(gbs))
        elif lv_gbs == 1:
            risk.append("月资源使用量 %s GBs 偏高于参考量级" % fmt_num(gbs))

    if ms is not None:
        if lv_ms == 2:
            crit.append("平均单次执行耗时 %s ms 属严重偏慢：GBs 消耗随耗时线性放大，"
                        "是最常见的成本黑洞" % fmt_num(ms))
        elif lv_ms == 1:
            risk.append("平均单次执行耗时 %s ms 偏慢，建议定位慢在数据库查询还是外部请求" % fmt_num(ms))
    if slow is True:
        risk.append("存在长耗时函数：把耗时操作异步化或拆分，避免长时间占用资源")
    elif slow is None:
        risk.append("未填写是否有长耗时函数")

    if timer is True:
        risk.append("存在高频定时触发器：定时器会持续产生调用，确认触发间隔是否必要")
    elif timer is None:
        risk.append("未填写是否有高频定时触发器")
    return crit, risk, items


def check_database(f):
    """数据库用量：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    reads = parse_num(get_text(f, "月读次数万次"))
    writes = parse_num(get_text(f, "月写次数万次"))
    dbgb = parse_num(get_text(f, "数据库存储GB"))
    indexed = yesno(get_text(f, "是否有索引优化"))
    rows = parse_num(get_text(f, "单次查询返回条数"))
    scan = yesno(get_text(f, "是否有全表扫描"))

    lv_reads = level(reads, READ_MID, READ_HIGH)
    lv_writes = level(writes, WRITE_MID, WRITE_HIGH)
    lv_db = level(dbgb, DB_GB_MID, DB_GB_HIGH)
    lv_rows = level(rows, ROWS_MID, ROWS_HIGH)

    items.append("月读次数：%s" % (("%s 万次" % fmt_num(reads)) if reads is not None else "未填写"))
    items.append("月写次数：%s" % (("%s 万次" % fmt_num(writes)) if writes is not None else "未填写"))
    items.append("数据库存储：%s" % (("%s GB" % fmt_num(dbgb)) if dbgb is not None else "未填写"))
    items.append("单次查询返回条数：%s" % (fmt_num(rows) if rows is not None else "未填写"))

    if scan is True:
        crit.append("存在全表扫描：全表扫描会放大读次数并拖慢查询，必须加索引并改为条件分页查询")
    elif scan is None:
        risk.append("未填写是否有全表扫描，这是读次数异常的首要排查点")

    if indexed is False:
        if lv_reads in (1, 2):
            crit.append("读次数达中高量级且未做索引优化：加索引是最直接的降本动作")
        else:
            risk.append("未做索引优化：数据量增长后读次数与耗时都会快速上升")
    elif indexed is None:
        risk.append("未填写是否有索引优化")

    if reads is None and writes is None:
        risk.append("未填写数据库读写次数，无法评估数据库侧用量")
    else:
        if lv_reads == 2:
            risk.append("月读 %s 万次属高量级：检查是否重复查询、未缓存、前端轮询" % fmt_num(reads))
        elif lv_reads == 1:
            risk.append("月读 %s 万次达中等量级" % fmt_num(reads))
        if lv_writes == 2:
            risk.append("月写 %s 万次属高量级：批量写入合并，避免逐条写" % fmt_num(writes))
        elif lv_writes == 1:
            risk.append("月写 %s 万次达中等量级" % fmt_num(writes))

    if lv_rows == 2:
        crit.append("单次查询返回 %s 条过多：应分页或按需返回字段，"
                    "一次性拉全量会同时放大读耗时与流量" % fmt_num(rows))
    elif lv_rows == 1:
        risk.append("单次查询返回 %s 条偏多，建议分页" % fmt_num(rows))

    if lv_db == 2:
        risk.append("数据库存储 %s GB 偏大，可归档历史数据降低存储占用" % fmt_num(dbgb))
    elif lv_db == 1:
        risk.append("数据库存储 %s GB 达中等量级，关注增长" % fmt_num(dbgb))
    return crit, risk, items


def check_storage(f):
    """存储与流量：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    store = parse_num(get_text(f, "云存储容量GB"))
    flow = parse_num(get_text(f, "月下行流量GB"))
    host = yesno(get_text(f, "是否开启静态网站托管"))
    bigfile = yesno(get_text(f, "是否有大文件"))
    redundant = yesno(get_text(f, "是否有历史冗余文件"))

    lv_store = level(store, STORE_GB_MID, STORE_GB_HIGH)
    lv_flow = level(flow, FLOW_GB_MID, FLOW_GB_HIGH)

    items.append("云存储容量：%s" % (("%s GB" % fmt_num(store)) if store is not None else "未填写"))
    items.append("月下行流量：%s" % (("%s GB" % fmt_num(flow)) if flow is not None else "未填写"))
    items.append("静态网站托管：%s" % ("开启" if host is True else "未开启" if host is False else "未填写"))

    if lv_flow == 2:
        crit.append("月下行流量 %s GB 属高量级：流量是最容易突增且最难控的一项，"
                    "必须查清是大文件直出还是重复拉取未缓存" % fmt_num(flow))
    elif lv_flow == 1:
        risk.append("月下行流量 %s GB 偏高于参考量级" % fmt_num(flow))
    elif flow is None:
        risk.append("未填写月下行流量，无法评估流量成本")

    if bigfile is True:
        risk.append("存在大文件：大文件直出会显著推高流量，建议压缩、分片或用 CDN 分发")
    elif bigfile is None:
        risk.append("未填写是否有大文件")

    if redundant is True:
        risk.append("存在历史冗余文件：清理无用文件可直接降低存储占用")
    elif redundant is None:
        risk.append("未填写是否有历史冗余文件")

    if lv_store == 2:
        risk.append("云存储 %s GB 偏大，建议清理冗余并归档冷数据" % fmt_num(store))
    elif lv_store == 1:
        risk.append("云存储 %s GB 达中等量级，关注增长" % fmt_num(store))
    elif store is None:
        risk.append("未填写云存储容量")
    return crit, risk, items


def check_cost(f):
    """套餐与成本：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    plan = get_text(f, "套餐类型")
    paid = parse_num(get_text(f, "当前月费用元"))
    target = parse_num(get_text(f, "期望月成本目标元"))
    months = parse_num(get_text(f, "使用时长月"))
    alarm = yesno(get_text(f, "是否设置用量告警"))
    burst = yesno(get_text(f, "是否有突发活动流量"))
    cleaned = yesno(get_text(f, "是否清理历史数据"))

    items.append("套餐类型：%s" % (plan if filled(plan) else "未填写"))
    items.append("当前月费用：%s" % (money(paid) if paid is not None else "未填写"))
    items.append("期望月成本目标：%s" % (money(target) if target is not None else "未填写"))
    items.append("已使用时长：%s" % (("%s 个月" % fmt_num(months)) if months is not None else "未填写"))

    if paid is not None and target is not None:
        gap = paid - target
        if gap > 0:
            risk.append("当前月费用 %s 超出目标 %s，差额 %s（超出 %.0f%%）" %
                        (money(paid), money(target), money(gap),
                         (gap / target * 100) if target else 0))
            items.append("成本对比：%s − %s = 超支 %s" % (money(paid), money(target), money(gap)))
        else:
            items.append("成本对比：%s，在目标 %s 之内" % (money(paid), money(target)))
    elif paid is None:
        risk.append("未填写当前月费用，无法做成本对比")
    elif target is None:
        risk.append("未填写期望月成本目标，建议设定一个预算便于控制")

    if burst is True:
        if alarm is False:
            crit.append("有突发活动流量但未设置用量告警：活动期间流量与调用可能成倍增长，"
                        "无告警等于裸奔")
        else:
            risk.append("有突发活动流量：活动前做容量评估，活动中盯告警")
    elif burst is None:
        risk.append("未填写是否有突发活动流量")

    if alarm is False:
        risk.append("未设置用量告警：超额往往在账单出来后才发现，务必先配告警")
    elif alarm is None:
        risk.append("未填写是否设置用量告警")

    if cleaned is False:
        risk.append("未清理历史数据：历史数据持续占用存储并拖慢查询")
    elif cleaned is None:
        risk.append("未填写是否清理历史数据")
    return crit, risk, items


def build_report(f):
    rep = []
    crit = []
    risk = []
    todo = []

    env_name = get_text(f, "环境名称或ID")
    plan = get_text(f, "套餐类型")
    paid = parse_num(get_text(f, "当前月费用元"))
    target = parse_num(get_text(f, "期望月成本目标元"))

    fn_crit, fn_risk, fn_items = check_function(f)
    db_crit, db_risk, db_items = check_database(f)
    st_crit, st_risk, st_items = check_storage(f)
    co_crit, co_risk, co_items = check_cost(f)

    core_missing = not filled(env_name) and not filled(plan)
    if not core_missing:
        crit.extend(fn_crit + db_crit + st_crit + co_crit)
        risk.extend(fn_risk + db_risk + st_risk + co_risk)

    if core_missing:
        verdict = "待补正"
        grade = "待补正"
    elif crit:
        verdict = "不通过"
        grade = "超额风险明显"
    elif risk:
        verdict = "有风险"
        grade = "需关注"
    else:
        verdict = "通过"
        grade = "用量健康"

    # 1 结论摘要
    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 环境：%s" % (env_name if filled(env_name) else "未填写"))
    rep.append("- 套餐：%s" % (plan if filled(plan) else "未填写"))
    rep.append("- 当前月费用：%s / 目标 %s" %
               (money(paid) if paid is not None else "未填写",
                money(target) if target is not None else "未填写"))
    rep.append("- 超额风险项 %d 项 / 待关注项 %d 项" % (len(crit), len(risk)))
    rep.append("- **总体结论：%s（用量等级：%s）**" % (verdict, grade))
    rep.append("")

    # 2 云函数
    rep.append("## 云函数用量")
    rep.append("")
    for it in fn_items:
        rep.append("- %s" % it)
    for c in fn_crit:
        rep.append("- **%s**" % c)
    for r in fn_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 3 数据库
    rep.append("## 数据库用量")
    rep.append("")
    for it in db_items:
        rep.append("- %s" % it)
    for c in db_crit:
        rep.append("- **%s**" % c)
    for r in db_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 4 存储与流量
    rep.append("## 存储与流量")
    rep.append("")
    for it in st_items:
        rep.append("- %s" % it)
    for c in st_crit:
        rep.append("- **%s**" % c)
    for r in st_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 5 套餐与成本
    rep.append("## 套餐与成本")
    rep.append("")
    for it in co_items:
        rep.append("- %s" % it)
    for c in co_crit:
        rep.append("- **%s**" % c)
    for r in co_risk:
        rep.append("- %s" % r)
    rep.append("- **本技能不做单价换算**：实际额度、计费标准与账单以微信云开发控制台"
               "与官方计费说明为准。")
    rep.append("")

    # 6 超额风险与防护
    rep.append("## 超额风险与防护动作")
    rep.append("")
    rep.append("- **先配用量告警**：在控制台为调用量、数据库读写、存储与流量设置告警阈值，"
               "超额第一时间知道。")
    rep.append("- **活动前做容量评估**：有促销或突发活动的，提前估算调用与流量峰值。")
    rep.append("- **核对套餐额度**：确认当前套餐包含的额度与实际用量，超出部分按量计费。")
    rep.append("- **建立月度对账**：每月记录各项用量与费用，观察增长趋势。")
    rep.append("")

    # 7 降本清单
    rep.append("## 降本优化清单")
    rep.append("")
    rep.append("按投入产出排序：")
    rep.append("")
    rep.append("1. **加索引 + 改查询**：消灭全表扫描，改条件分页查询，读次数可显著下降")
    rep.append("2. **加缓存**：热点数据加缓存，避免重复读库；前端避免轮询")
    rep.append("3. **缩短函数耗时**：定位慢查询与外部请求，耗时下降直接降低 GBs")
    rep.append("4. **批量读写**：写操作批量合并，减少调用次数")
    rep.append("5. **清理冗余**：清理历史文件与冷数据，降低存储占用")
    rep.append("6. **图片与文件**：压缩大文件、走 CDN，降低下行流量")
    rep.append("7. **定时器治理**：确认定时触发间隔是否必要，避免空转调用")
    rep.append("")

    # 8 待办
    rep.append("## 待办动作")
    rep.append("")
    if core_missing:
        todo.append("补齐「环境名称或ID」与「套餐类型」——这是出具结论的前提")
    for c in crit:
        todo.append("处理超额风险：%s" % c.split("：")[0])
    if not filled(get_text(f, "是否设置用量告警")):
        todo.append("在控制台配置用量告警阈值")
    if not filled(get_text(f, "当前月费用元")):
        todo.append("填入当前月费用，便于与目标对比")
    if not filled(get_text(f, "是否有全表扫描")):
        todo.append("排查是否存在全表扫描，并为高频查询字段加索引")
    if not todo:
        todo.append("各项用量在参考量级内，保持月度对账与告警即可")
    for i, t in enumerate(todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用参考量级整理，**不做单价换算、不杜撰计费标准**，"
               "实际额度与费用以微信云开发控制台账单与官方计费说明为准。")
    rep.append("- 参考量级仅用于判断「量级是否偏高」，不同业务形态差异很大，"
               "应以自身历史数据与增长趋势为准。")
    rep.append("- **本技能只做用量核算与优化建议，不承诺费用数值，不代替官方计费。**")
    rep.append("- 发现账单异常时，以控制台账单明细与官方渠道核实为准。")

    return "\n".join(rep), verdict, crit + risk, todo


def main():
    ap = argparse.ArgumentParser(description="微信云开发资源用量与成本核查")
    ap.add_argument("md", nargs="?", default="样例.md")
    ap.add_argument("--input", dest="input", default=None)
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path = args.input or args.md
    if not path or not os.path.exists(path):
        msg = "采集表不存在：%s" % path
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2
    f = parse_md(path)
    if not f:
        msg = "采集表为空或格式无法解析，请用「| 字段 | 值 |」或「字段：值」格式填写"
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2

    report, verdict, issues, todo = build_report(f)
    if args.json:
        print(json.dumps({"结论": verdict, "风险项": issues, "待办": todo, "报告": report},
                         ensure_ascii=False, indent=2))
    else:
        print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)

    if not filled(get_text(f, "环境名称或ID")) and not filled(get_text(f, "套餐类型")):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
