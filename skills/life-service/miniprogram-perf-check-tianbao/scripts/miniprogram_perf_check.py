# -*- coding: utf-8 -*-
"""小程序启动与渲染性能核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段报告，含结论摘要、包体积与代码加载、启动性能、渲染与交互、网络与资源、
      优先级优化清单、复测与验收建议、待办动作、边界与纪律。

只做性能诊断与优化建议，不替代真机实测与官方体验评分。
退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys

FIELD_ALIAS = {
    "小程序名称": ["小程序名称", "名称", "app名称"],
    "主要使用场景": ["主要使用场景", "使用场景", "核心场景", "业务场景"],
    "目标机型": ["目标机型", "机型定位", "适配机型", "用户机型"],
    "测试方式": ["测试方式", "测量方式", "数据来源", "测试工具"],
    "主包体积MB": ["主包体积mb", "主包体积", "主包大小", "主包mb"],
    "分包数量": ["分包数量", "分包数", "有几个分包"],
    "总包体积MB": ["总包体积mb", "总包体积", "总包大小", "整体包大小"],
    "是否使用分包加载": ["是否使用分包加载", "是否分包", "分包情况", "有无分包"],
    "是否开启按需注入": ["是否开启按需注入", "按需注入", "是否按需注入"],
    "是否开启用时注入": ["是否开启用时注入", "用时注入", "是否用时注入"],
    "冷启动耗时ms": ["冷启动耗时ms", "冷启动耗时", "冷启动时间", "启动耗时"],
    "首屏渲染耗时ms": ["首屏渲染耗时ms", "首屏渲染耗时", "首屏耗时", "首屏时间"],
    "页面切换耗时ms": ["页面切换耗时ms", "页面切换耗时", "切换耗时", "跳转耗时"],
    "是否使用骨架屏": ["是否使用骨架屏", "骨架屏", "有无骨架屏"],
    "是否预请求数据": ["是否预请求数据", "预请求", "数据预拉取", "是否预拉取"],
    "启动页请求数": ["启动页请求数", "启动请求数", "首屏请求数", "启动时请求数"],
    "单次setData数据量KB": ["单次setdata数据量kb", "单次setdata数据量", "setdata数据量",
                       "单次setdata大小"],
    "setData每秒调用次数": ["setdata每秒调用次数", "setdata频率", "setdata调用频率",
                      "setdata次数"],
    "是否长列表": ["是否长列表", "长列表", "是否有长列表", "列表数据量大"],
    "长列表是否虚拟滚动": ["长列表是否虚拟滚动", "是否虚拟滚动", "虚拟列表", "是否分页加载"],
    "是否使用自定义组件": ["是否使用自定义组件", "自定义组件", "有无自定义组件"],
    "是否有高频滚动监听": ["是否有高频滚动监听", "高频滚动监听", "滚动监听", "onscroll频率"],
    "首页接口请求数": ["首页接口请求数", "首页请求数", "首屏接口数"],
    "接口平均响应ms": ["接口平均响应ms", "接口平均响应", "接口响应时间", "接口耗时"],
    "图片平均大小KB": ["图片平均大小kb", "图片平均大小", "图片大小", "图片体积"],
    "是否压缩图片": ["是否压缩图片", "图片压缩", "是否压缩"],
    "是否使用CDN": ["是否使用cdn", "cdn", "是否用cdn", "cdn加速"],
    "是否使用WebP": ["是否使用webp", "webp", "图片格式", "是否webp"],
    "是否有未使用资源": ["是否有未使用资源", "未使用资源", "冗余资源", "是否有无用代码"],
    "是否有内存泄漏或页面栈过深": ["是否有内存泄漏或页面栈过深", "内存泄漏", "页面栈过深",
                        "是否有内存问题"],
    "已做优化项": ["已做优化项", "已优化", "已做优化"],
    "性能目标": ["性能目标", "优化目标", "期望指标", "目标值"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做", "未测", "没测",
)

# 参考阈值（公开通用参考值，最终以官方文档与真机实测为准）
LIMIT_MAIN_PACKAGE = 2.0        # MB，主包常见上限
LIMIT_TOTAL_PACKAGE = 20.0      # MB，总包参考上限
T_COLD_GOOD = 3000.0            # ms 冷启动达标
T_COLD_BAD = 5000.0             # ms 冷启动严重
T_FIRST_GOOD = 2000.0           # ms 首屏达标
T_FIRST_BAD = 3500.0            # ms 首屏严重
T_SWITCH_GOOD = 500.0           # ms 页面切换达标
SETDATA_GOOD = 256.0            # KB 单次 setData 建议上限
SETDATA_BAD = 1024.0            # KB 单次 setData 严重
SETDATA_FREQ_GOOD = 20.0        # 次/秒 建议上限
IMG_GOOD = 100.0                # KB 图片建议
IMG_BAD = 300.0                 # KB 图片严重
API_GOOD = 500.0                # ms 接口响应达标
API_BAD = 1500.0                # ms 接口响应严重
REQ_GOOD = 5.0                  # 首页请求数建议


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


def check_package(f):
    """包体积与代码加载：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    main_p = parse_num(get_text(f, "主包体积MB"))
    total_p = parse_num(get_text(f, "总包体积MB"))
    sub_n = parse_num(get_text(f, "分包数量"))
    use_sub = yesno(get_text(f, "是否使用分包加载"))
    ondemand = yesno(get_text(f, "是否开启按需注入"))
    lazy = yesno(get_text(f, "是否开启用时注入"))

    items.append("主包体积：%s" % (("%s MB" % fmt_num(main_p)) if main_p is not None else "未填写"))
    items.append("总包体积：%s" % (("%s MB" % fmt_num(total_p)) if total_p is not None else "未填写"))
    items.append("分包数量：%s" % (fmt_num(sub_n) if sub_n is not None else "未填写"))

    if main_p is not None:
        if main_p > LIMIT_MAIN_PACKAGE:
            crit.append("主包体积 %s MB 超过 %s MB 上限：超限的包无法上传，"
                        "必须拆分到分包或清理资源" % (fmt_num(main_p), fmt_num(LIMIT_MAIN_PACKAGE)))
        elif main_p > LIMIT_MAIN_PACKAGE * 0.75:
            risk.append("主包体积 %s MB 已接近 %s MB 上限，建议提前拆包" %
                        (fmt_num(main_p), fmt_num(LIMIT_MAIN_PACKAGE)))
    else:
        risk.append("未填写主包体积，无法判断是否超限")

    if total_p is not None and total_p > LIMIT_TOTAL_PACKAGE:
        risk.append("总包体积 %s MB 超过参考上限 %s MB，需按业务拆分或清理历史资源"
                    % (fmt_num(total_p), fmt_num(LIMIT_TOTAL_PACKAGE)))

    if use_sub is False and (main_p is not None and main_p > LIMIT_MAIN_PACKAGE * 0.6):
        crit.append("主包偏大且未使用分包加载：应把非首屏页面拆到分包")
    elif use_sub is None:
        risk.append("未填写是否使用分包加载；主包较大时分包是最直接的解法")

    if ondemand is False:
        risk.append("未开启按需注入：开启后只注入当前页面需要的代码，可降低启动开销")
    elif ondemand is None:
        risk.append("未填写是否开启按需注入")

    if lazy is False and (sub_n is not None and sub_n > 0):
        risk.append("已有分包但未开启用时注入/分包预下载策略，可进一步优化启动")

    if yesno(get_text(f, "是否有未使用资源")) is True:
        risk.append("存在未使用资源：清理无用代码、图片与库，直接减少包体积")
    return crit, risk, items


def check_startup(f):
    """启动性能：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    cold = parse_num(get_text(f, "冷启动耗时ms"))
    first = parse_num(get_text(f, "首屏渲染耗时ms"))
    switch = parse_num(get_text(f, "页面切换耗时ms"))
    skeleton = yesno(get_text(f, "是否使用骨架屏"))
    preload = yesno(get_text(f, "是否预请求数据"))
    reqs = parse_num(get_text(f, "启动页请求数"))

    items.append("冷启动耗时：%s" % (("%s ms" % fmt_num(cold)) if cold is not None else "未填写"))
    items.append("首屏渲染耗时：%s" % (("%s ms" % fmt_num(first)) if first is not None else "未填写"))
    items.append("页面切换耗时：%s" % (("%s ms" % fmt_num(switch)) if switch is not None else "未填写"))

    if cold is not None:
        if cold > T_COLD_BAD:
            crit.append("冷启动 %s ms 超过 %s ms：属严重超标，"
                        "重点查主包体积、启动同步逻辑与首屏请求" %
                        (fmt_num(cold), fmt_num(T_COLD_BAD)))
        elif cold > T_COLD_GOOD:
            risk.append("冷启动 %s ms 超过 %s ms 达标线，建议优化" %
                        (fmt_num(cold), fmt_num(T_COLD_GOOD)))
    else:
        risk.append("未填写冷启动耗时，无法评估启动性能")

    if first is not None:
        if first > T_FIRST_BAD:
            crit.append("首屏渲染 %s ms 超过 %s ms：白屏时间过长，"
                        "应加骨架屏并把首屏数据请求前置" %
                        (fmt_num(first), fmt_num(T_FIRST_BAD)))
        elif first > T_FIRST_GOOD:
            risk.append("首屏渲染 %s ms 超过 %s ms 达标线" %
                        (fmt_num(first), fmt_num(T_FIRST_GOOD)))

    if switch is not None and switch > T_SWITCH_GOOD:
        risk.append("页面切换 %s ms 偏慢，检查跳转时的同步逻辑与数据加载时机" % fmt_num(switch))

    if skeleton is False:
        risk.append("未使用骨架屏：首屏数据未到时用户直面白屏，感知性能差")
    elif skeleton is None:
        risk.append("未填写是否使用骨架屏")

    if preload is False:
        risk.append("未做数据预请求/预拉取：可在启动阶段提前发起首屏请求")
    elif preload is None:
        risk.append("未填写是否预请求数据")

    if reqs is not None and reqs > REQ_GOOD:
        risk.append("启动页请求数 %s 个偏多，建议合并接口或延迟非必要请求" % fmt_num(reqs))
    return crit, risk, items


def check_render(f):
    """渲染与交互：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    sd = parse_num(get_text(f, "单次setData数据量KB"))
    freq = parse_num(get_text(f, "setData每秒调用次数"))
    longlist = yesno(get_text(f, "是否长列表"))
    virtual = yesno(get_text(f, "长列表是否虚拟滚动"))
    comp = yesno(get_text(f, "是否使用自定义组件"))
    scroll = yesno(get_text(f, "是否有高频滚动监听"))

    items.append("单次 setData 数据量：%s" % (("%s KB" % fmt_num(sd)) if sd is not None else "未填写"))
    items.append("setData 调用频率：%s" % (("%s 次/秒" % fmt_num(freq)) if freq is not None else "未填写"))

    if sd is not None:
        if sd > SETDATA_BAD:
            crit.append("单次 setData %s KB 超过 %s KB：属严重超标，"
                        "视图层传输压力过大，必须分片或只传变化字段" %
                        (fmt_num(sd), fmt_num(SETDATA_BAD)))
        elif sd > SETDATA_GOOD:
            risk.append("单次 setData %s KB 超过 %s KB 建议值，建议只传变更数据" %
                        (fmt_num(sd), fmt_num(SETDATA_GOOD)))
    else:
        risk.append("未填写单次 setData 数据量，无法评估渲染开销")

    if freq is not None and freq > SETDATA_FREQ_GOOD:
        risk.append("setData 每秒 %s 次偏高频，应合并更新并做节流" % fmt_num(freq))

    if longlist is True:
        if virtual is False:
            crit.append("存在长列表但未做虚拟滚动/分页：长列表全量渲染会明显卡顿")
        elif virtual is None:
            risk.append("存在长列表但未填写是否虚拟滚动，这是卡顿的常见根因")
    elif longlist is None:
        risk.append("未填写是否长列表")

    if scroll is True:
        risk.append("存在高频滚动监听：滚动回调里避免 setData 与复杂计算，必要时节流")
    elif scroll is None:
        risk.append("未填写是否有高频滚动监听")

    if comp is False:
        risk.append("未使用自定义组件：组件化可减少不必要的页面级重渲染")
    return crit, risk, items


def check_network(f):
    """网络与资源：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    reqs = parse_num(get_text(f, "首页接口请求数"))
    api = parse_num(get_text(f, "接口平均响应ms"))
    img = parse_num(get_text(f, "图片平均大小KB"))
    compress = yesno(get_text(f, "是否压缩图片"))
    cdn = yesno(get_text(f, "是否使用CDN"))
    webp = yesno(get_text(f, "是否使用WebP"))

    items.append("首页接口请求数：%s" % (fmt_num(reqs) if reqs is not None else "未填写"))
    items.append("接口平均响应：%s" % (("%s ms" % fmt_num(api)) if api is not None else "未填写"))
    items.append("图片平均大小：%s" % (("%s KB" % fmt_num(img)) if img is not None else "未填写"))

    if api is not None:
        if api > API_BAD:
            crit.append("接口平均响应 %s ms 超过 %s ms：后端响应严重偏慢，"
                        "需优化接口或加缓存，前端只靠加载态掩盖不了" %
                        (fmt_num(api), fmt_num(API_BAD)))
        elif api > API_GOOD:
            risk.append("接口平均响应 %s ms 超过 %s ms 达标线" % (fmt_num(api), fmt_num(API_GOOD)))
    else:
        risk.append("未填写接口平均响应时间")

    if img is not None:
        if img > IMG_BAD:
            crit.append("图片平均 %s KB 超过 %s KB：图片过大是流量与渲染的双重负担，"
                        "必须压缩并改用合适格式" % (fmt_num(img), fmt_num(IMG_BAD)))
        elif img > IMG_GOOD:
            risk.append("图片平均 %s KB 超过 %s KB 建议值" % (fmt_num(img), fmt_num(IMG_GOOD)))
    else:
        risk.append("未填写图片平均大小")

    if reqs is not None and reqs > REQ_GOOD:
        risk.append("首页接口请求 %s 个偏多，建议合并或延迟加载" % fmt_num(reqs))

    for flag, name, tip in (
        (compress, "未压缩图片", "开启图片压缩，按显示尺寸出图，不要原图直出"),
        (cdn, "未使用 CDN", "静态资源走 CDN，减少首屏拉取耗时"),
        (webp, "未使用 WebP", "图片改用 WebP 等更小格式，可明显降低体积"),
    ):
        if flag is False:
            risk.append("%s：%s" % (name, tip))
        elif flag is None:
            risk.append("未填写是否%s" % name.replace("未", ""))

    if yesno(get_text(f, "是否有内存泄漏或页面栈过深")) is True:
        crit.append("存在内存泄漏或页面栈过深：会导致闪退与卡顿，"
                    "检查未清理的定时器、监听与页面栈层级")
    return crit, risk, items


def build_report(f):
    rep = []
    crit = []
    risk = []
    todo = []

    name = get_text(f, "小程序名称")
    scene = get_text(f, "主要使用场景")
    goal = get_text(f, "性能目标")
    done = get_text(f, "已做优化项")

    p_crit, p_risk, p_items = check_package(f)
    s_crit, s_risk, s_items = check_startup(f)
    r_crit, r_risk, r_items = check_render(f)
    n_crit, n_risk, n_items = check_network(f)

    core_missing = not filled(name) and not filled(scene)
    if not core_missing:
        crit.extend(p_crit + s_crit + r_crit + n_crit)
        risk.extend(p_risk + s_risk + r_risk + n_risk)

    if core_missing:
        verdict = "待补正"
        grade = "待补正"
    elif crit:
        verdict = "不通过"
        grade = "严重超标"
    elif risk:
        verdict = "有风险"
        grade = "需优化"
    else:
        verdict = "通过"
        grade = "达标"

    # 1 结论摘要
    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 小程序：%s" % (name if filled(name) else "未填写"))
    rep.append("- 使用场景：%s" % (scene if filled(scene) else "未填写"))
    rep.append("- 超标阻断项 %d 项 / 待优化风险项 %d 项" % (len(crit), len(risk)))
    rep.append("- 性能目标：%s" % (goal if filled(goal) else "未填写"))
    rep.append("- **总体结论：%s（性能等级：%s）**" % (verdict, grade))
    rep.append("")

    # 2 包体积
    rep.append("## 包体积与代码加载")
    rep.append("")
    for it in p_items:
        rep.append("- %s" % it)
    for c in p_crit:
        rep.append("- **%s**" % c)
    for r in p_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 3 启动性能
    rep.append("## 启动性能")
    rep.append("")
    for it in s_items:
        rep.append("- %s" % it)
    for c in s_crit:
        rep.append("- **%s**" % c)
    for r in s_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 4 渲染与交互
    rep.append("## 渲染与交互")
    rep.append("")
    for it in r_items:
        rep.append("- %s" % it)
    for c in r_crit:
        rep.append("- **%s**" % c)
    for r in r_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 5 网络与资源
    rep.append("## 网络与资源")
    rep.append("")
    for it in n_items:
        rep.append("- %s" % it)
    for c in n_crit:
        rep.append("- **%s**" % c)
    for r in n_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 6 优化清单
    rep.append("## 优先级优化清单")
    rep.append("")
    rep.append("按投入产出排序（先解决阻断项，再做低成本高收益项）：")
    rep.append("")
    rep.append("1. **拆包与瘦身**：主包超限时优先拆分包，清理未使用代码与资源，开启按需注入")
    rep.append("2. **首屏提速**：骨架屏 + 数据预请求 + 合并启动请求，减少白屏时间")
    rep.append("3. **渲染减负**：setData 只传变化字段、合并更新、长列表虚拟滚动或分页")
    rep.append("4. **图片与静态资源**：压缩并按显示尺寸出图，改用 WebP，静态资源走 CDN")
    rep.append("5. **接口优化**：合并请求、加缓存、后端提速，前端配合分页与懒加载")
    rep.append("6. **内存治理**：清理定时器与监听，控制页面栈层级，避免内存泄漏")
    rep.append("")
    if filled(done):
        rep.append("已做优化项：%s" % done)
    rep.append("")

    # 7 复测建议
    rep.append("## 复测与验收建议")
    rep.append("")
    rep.append("- 用**真机**在目标机型上复测，开发者工具的数值与真机差异较大，不能作为验收依据。")
    rep.append("- 冷启动取多次冷启动的中位数，避免单次抖动误判。")
    rep.append("- 每次只改一类问题并复测，便于定位哪项改动真正生效。")
    rep.append("- 关注低端机型表现：高端机达标不代表低端机达标。")
    rep.append("")

    # 8 待办
    rep.append("## 待办动作")
    rep.append("")
    if core_missing:
        todo.append("补齐「小程序名称」与「主要使用场景」——这是出具结论的前提")
    for c in crit:
        todo.append("处理超标项：%s" % c.split("：")[0])
    if not filled(get_text(f, "冷启动耗时ms")):
        todo.append("用真机测量冷启动耗时并填入")
    if not filled(get_text(f, "主包体积MB")):
        todo.append("填入主包体积，确认是否超过 2MB 上限")
    if not filled(goal):
        todo.append("明确性能目标（如冷启动 <3000ms、主包 <2MB），便于验收")
    if not todo:
        todo.append("各项指标均在参考范围内，按复测建议做真机验收即可")
    for i, t in enumerate(todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依公开通用参考值整理，不替代真机实测与官方体验评分，"
               "最终以微信公众平台与官方文档为准。")
    rep.append("- 所有阈值均为**参考值**：不同业务形态与机型差异很大，"
               "应以自身真机数据与目标机型表现为准。")
    rep.append("- **本技能只做性能诊断与优化建议，不承诺性能达标，不代替实际编码改造。**")
    rep.append("- 包体积上限以官方当前规定为准，超限会导致无法上传。")

    return "\n".join(rep), verdict, crit + risk, todo


def main():
    ap = argparse.ArgumentParser(description="小程序启动与渲染性能核查")
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

    if not filled(get_text(f, "小程序名称")) and not filled(get_text(f, "主要使用场景")):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
