# -*- coding: utf-8 -*-
"""宠物疫苗接种间隔与反应观察核查工具。

用法:
  python vaccine_gap.py --file record.json [--json]
  python vaccine_gap.py --selftest

本工具不给疫苗名称, 不给针数与间隔天数作为自家方案。
"""
import argparse
import io
import json
import os
import sys

# 核心与非核心的判断口径
CATEGORIES = {
    "core": {
        "name": "核心疫苗",
        "meaning": "几乎所有宠物都应接种",
        "basis": "该病一旦发生后果严重, 且本地流行",
        "example": "犬: 狂犬病、犬瘟热、犬细小病毒、犬腺病毒等; "
                   "猫: 狂犬病、猫泛白细胞减少症(猫瘟)、猫疱疹病毒、猫杯状病毒等",
    },
    "non_core": {
        "name": "非核心疫苗",
        "meaning": "取决于个体暴露风险",
        "basis": "这只宠物是否会接触到该病原",
        "example": "犬: 钩端螺旋体病、莱姆病、犬副流感等; "
                   "猫: 猫白血病病毒(主要针对有外出风险的猫)",
    },
    "not_recommended": {
        "name": "不推荐或已停用",
        "meaning": "效果有限或不推荐常规使用",
        "basis": "保护价值不足或有替代方案",
        "example": "部分覆盖不全的疫苗、不推荐常规使用的减毒活疫苗等",
    },
}

THREE_QUESTIONS = [
    "这一针是核心还是非核心? 依据是什么?",
    "如果是非核心, 依据我这只宠物的哪些情况?",
    "如果我暂不打, 会带来什么风险?",
]

RECORD_FIELDS = [
    ("接种日期", "精确到日", "算间隔的唯一依据"),
    ("疫苗名称或类别", "至少记清类别与是第几针", "不同类别程序不同"),
    ("针次序号", "首免第几针、第几次加强", "判断程序完成度"),
    ("接种机构", "便于后续查询与补种", "机构通常保留记录"),
    ("不良反应记录", "有无发热、精神差、局部肿块", "后续接种的参考"),
    ("批次或有效期", "部分记录会有", "便于追溯"),
]

PRINCIPLES = [
    ("首免起点", "由兽医按年龄与母源抗体情况确定"),
    ("母源抗体影响", "母源抗体可能干扰首免效果, 首免起点由兽医判断"),
    ("针次间隔", "由兽医确定; 不自行缩短间隔提前完成"),
    ("完成前保护有限", "未完成程序前避免接触未接种的同种动物、宠物店、寄养与高密度场所"),
    ("幼宠免疫未成熟", "幼宠在完成程序前属于易感, 外出与社交要控制"),
    ("记录每一针", "每打一针立刻记录, 不要事后补记"),
]

MISSED = [
    ("漏了一针, 但有记录", "带记录就诊, 由兽医计算补种时点"),
    ("记录不清或完全没有记录", "带宠物到机构查询; 部分机构可做抗体检测评估"),
    ("超过加强时点较久", "不要直接从现在开始按新程序打, 须由兽医判断是否需要重启程序"),
    ("幼宠未完成程序且已超期", "须由兽医确定方案, 不自行决定"),
    ("不确定是否打过", "视为记录缺失处理, 交由兽医判断"),
]

WATCH = [
    (0, 1, "接种当天", "精神、食欲、呕吐、排便、体温、注射部位",
     "呼吸困难、面部肿胀、抽搐、站立不稳"),
    (1, 3, "接种后 24 小时", "精神、进食、体温、注射部位",
     "持续高热、精神沉郁、不吃不喝"),
    (3, 5, "接种后 24-48 小时", "同上, 加观察肿胀范围变化",
     "肿胀扩大、脓性分泌物、皮肤破溃"),
    (5, 8, "接种后 72 小时", "局部硬结是否开始消退", "肿块持续增大、质地变硬"),
    (8, 999, "接种后数周", "局部肿块是否消退", "超过数周不消退"),
]

REACTIONS = {
    "mild_lethargy": ("接种当天精神略差、食欲下降", "常见轻度反应",
                      "记录并观察; 若持续加重按红线就医"),
    "local_swelling": ("接种部位轻微红肿、硬结", "常见局部反应",
                       "记录范围变化; 不自行按摩、不自行涂抹"),
    "fever": ("发热", "可能属免疫反应", "是否异常由兽医判断; 持续不退按红线"),
    "gi": ("呕吐、腹泻", "需要重视", "持续超过 24 小时按红线"),
    "anaphylaxis": ("呼吸困难、面部肿胀、抽搐、倒地", "急性过敏反应", "立即急诊"),
    "necrosis": ("大面积红肿、脓性分泌物、皮肤坏死", "感染或组织损伤", "尽快就医"),
}

RED_FLAGS = [
    ("anaphylaxis", "呼吸困难、面部或咽喉肿胀、呕吐、站立不稳、倒地", "立即急诊"),
    ("convulsion", "接种后出现抽搐、意识障碍", "立即急诊"),
    ("fever_24h", "接种后持续高热超过 24 小时不退, 或体温明显偏低", "尽快联系兽医"),
    ("no_intake_24h", "接种后精神沉郁、不吃不喝超过 24 小时", "尽快联系兽医"),
    ("hypoglycemia", "幼宠接种后出现低血糖表现", "尽快联系兽医"),
    ("site_infection", "接种部位大面积红肿、脓性分泌物、皮肤破溃或坏死", "尽快就医"),
    ("site_mass", "接种部位肿块持续增大、质地变硬、超过数周不消退", "就医评估"),
    ("vomit_24h", "接种后出现持续呕吐、腹泻", "尽快就医"),
    ("still_sick", "已按程序接种但仍发病", "须由兽医评估"),
    ("immunosuppressed", "免疫功能异常、免疫抑制、正在使用免疫抑制药物、"
                     "患有自身免疫病或肿瘤", "须兽医评估方案"),
    ("pregnant", "妊娠期母宠", "须兽医评估方案"),
    ("unhealthy", "接种前宠物处于病中、发热、腹泻或正在使用其他药物", "不接种"),
]

EMERGENCY = ("anaphylaxis", "convulsion")

SPECIAL = [
    ("妊娠期母宠", "须兽医评估, 不自行安排接种"),
    ("正在使用免疫抑制药物", "须兽医评估"),
    ("免疫缺陷、自身免疫病、肿瘤治疗中", "须兽医评估"),
    ("幼宠接种后精神差", "幼宠风险较高; 幼犬幼猫注意低血糖表现"),
    ("老年宠", "是否继续加强、是否调整程序由兽医评估, 不自行停"),
    ("既往有严重不良反应史", "必须主动告知医生, 影响后续方案"),
    ("多宠家庭", "每只分别记录, 不共用一份记录"),
    ("短期内多次接种", "需确认间隔是否合理, 由兽医判断"),
    ("接种前刚洗澡", "部分情况下不建议同日进行"),
]

FAILURE = [
    ("接种后仍发病", "不等于疫苗没用",
     "需兽医评估: 可能是疾病本身特点、暴露量过大、免疫未建立、或该疫苗的保护范围"),
    ("免疫未建立", "程序未完成、间隔过短、母源抗体干扰", "由兽医评估是否需重启程序"),
    ("母源抗体干扰", "幼宠首免时可能影响效果", "由兽医评估处理方式"),
    ("免疫抑制个体", "用药、疾病、年龄因素", "须兽医评估方案"),
    ("保护范围有限", "疫苗针对特定病原, 不是万能的", "防护仍靠卫生与隔离"),
]


def sort_records(records):
    out = []
    for r in (records or []):
        if not isinstance(r, dict):
            continue
        d = r.get("date")
        if d is None:
            continue
        try:
            di = int(d)
        except (TypeError, ValueError):
            continue
        out.append((di, r))
    out.sort(key=lambda x: x[0])
    return out


def count_by_category(sorted_recs):
    counts = {}
    for d, r in sorted_recs:
        c = r.get("category", "未登记")
        counts[c] = counts.get(c, 0) + 1
    return counts


def days_since(last, today):
    if last is None or today is None:
        return None
    try:
        return int(today) - int(last)
    except (TypeError, ValueError):
        return None


def watch_of(days):
    d = int(days or 0)
    for lo, hi, name, what, bad in WATCH:
        if d < hi:
            return name, what, bad, (d < lo)
    return WATCH[-1][2], WATCH[-1][3], WATCH[-1][4], True


def record_state(records, today):
    sr = sort_records(records)
    if not sr:
        return "记录缺失", None, {}
    last_day = sr[-1][0]
    d = days_since(last_day, today)
    return "记录齐", d, count_by_category(sr)


def build_report(data):
    species = (data.get("species", "cat") or "cat").strip()
    age = data.get("age_months", 0)
    records = data.get("records", []) or []
    noncore_risk = data.get("noncore_risk", None)
    d_deworm = data.get("last_deworm", None)
    d_vac = data.get("last_vaccine", None)
    today = data.get("today", None)
    red = data.get("red_flags", []) or []
    reac = data.get("reactions", []) or []

    lines = []
    summary = {
        "record_state": None, "days_since_last": None,
        "counts": {}, "watch": None, "red_flag_hit": None,
        "emergency": [], "reactions": [],
        "vaccine_named": False, "schedule_days_provided": False,
    }

    lines.append("=" * 68)
    lines.append("宠物疫苗接种间隔与反应观察核查")
    lines.append("=" * 68)
    lines.append("  本工具不给疫苗名称, 不给针数与间隔天数作为自家方案。")
    lines.append("")

    lines.append("[一] 核心与非核心的区分")
    lines.append("-" * 68)
    sp = "犬" if species == "dog" else "猫"
    lines.append("  物种: %s   月龄: %g" % (sp, float(age or 0)))
    for k in ("core", "non_core", "not_recommended"):
        v = CATEGORIES[k]
        lines.append("  %s" % v["name"])
        lines.append("    含义: %s" % v["meaning"])
        lines.append("    依据: %s" % v["basis"])
        lines.append("    举例: %s" % v["example"])
    lines.append("")
    lines.append("  非核心疫苗的判断逻辑: 这只宠物是否会接触到该病原")
    lines.append("    从来不外出的室内犬、从不接触其他猫的室内猫, 很多非核心疫苗不需要")
    lines.append("")
    lines.append("  三个必须问清楚的问题:")
    for i, q in enumerate(THREE_QUESTIONS, 1):
        lines.append("    %d. %s" % (i, q))
    lines.append("  问不清楚这三问, 就容易被动接受不必要的针")
    lines.append("")
    if noncore_risk is None:
        lines.append("  非核心暴露风险: 未提供, 建议先与兽医确认暴露情况")
    elif noncore_risk:
        lines.append("  非核心暴露风险: 有(需逐项向兽医说明暴露细节)")
    else:
        lines.append("  非核心暴露风险: 低(仍需向兽医确认)")
    lines.append("")

    lines.append("[二] 接种记录核查")
    lines.append("-" * 68)
    state, days, counts = record_state(records, today)
    summary["record_state"] = state
    summary["days_since_last"] = days
    summary["counts"] = counts
    lines.append("  记录状态: %s" % state)
    if days is None:
        lines.append("    末次日期: 无法计算(记录缺失或今日日期未提供)")
        lines.append("    处置: 带宠物到机构查询; 部分机构可做抗体检测评估")
        lines.append("    处置: 不要自行重新开始一套, 是否重启程序由兽医判断")
    else:
        lines.append("    末次接种距今: %d 天" % days)
        lines.append("    是否已到加强时点: 由兽医确定, 本工具不给间隔天数")
    lines.append("    按类别已接种针数: %s" % (
        "、".join("%s %d 针" % (k, v) for k, v in sorted(counts.items()))
        if counts else "无"))
    lines.append("")
    lines.append("  记录必须包含的字段:")
    for f, how, why in RECORD_FIELDS:
        lines.append("    %-14s %-20s %s" % (f, how, why))
    lines.append("")
    lines.append("  排查顺序:")
    for i, s in enumerate([
            "拿出全部既往接种记录(纸质本、宠物芯片档案、就诊机构记录)",
            "按日期排序, 确认已完成针数与末次日期",
            "核对哪些是核心、哪些是非核心",
            "末次日期距今多久, 是否已到加强时点(由兽医确定)",
            "若记录缺失或对不上, 带宠物到机构查询或做抗体检测评估",
            "由兽医确定后续程序并写入记录"], 1):
        lines.append("    %d. %s" % (i, s))
    lines.append("")

    lines.append("[三] 幼宠首免原则")
    lines.append("-" * 68)
    for n, d in PRINCIPLES:
        lines.append("  %-16s %s" % (n, d))
    lines.append("")
    lines.append("  漏打与记录缺失的处理:")
    for n, d in MISSED:
        lines.append("    %-24s %s" % (n, d))
    lines.append("")
    lines.append("  关键原则: 漏打后不要自行重新开始一套")
    lines.append("    是否重启程序、重启几针、间隔多久, 必须由兽医判断")
    lines.append("")

    lines.append("[四] 与驱虫的间隔")
    lines.append("-" * 68)
    if d_deworm is None:
        lines.append("  驱虫日期: 未记录")
    else:
        lines.append("  驱虫距今: %s 天" % days_since(d_deworm, today))
    if d_vac is None:
        lines.append("  疫苗日期: 未记录")
    else:
        lines.append("  疫苗距今: %s 天" % days_since(d_vac, today))
    if d_deworm is not None and d_vac is not None:
        if int(d_deworm) == int(d_vac):
            lines.append("  [注意] 疫苗与驱虫同日进行")
            lines.append("    出现不良反应时难以区分来源; 错开日期便于排查")
        else:
            lines.append("  疫苗与驱虫未同日, 记录可对齐排查")
    else:
        lines.append("  是否需要分开由兽医确认; 常见做法是错开日期而不是同日进行")
    lines.append("    每次后观察 24-72 小时; 两次都记日期, 便于对齐与复盘")
    lines.append("    幼宠: 首免与首次驱虫的时间顺序由兽医安排")
    lines.append("")

    lines.append("[五] 接种后反应观察")
    lines.append("-" * 68)
    if today is not None and records:
        wname, what, bad, passed = watch_of(days if days is not None else 0)
        summary["watch"] = wname
        lines.append("  当前观察时段: %s" % wname)
        lines.append("    观察什么: %s" % what)
        lines.append("    什么算异常: %s" % bad)
    else:
        lines.append("  未提供观察起点, 请按下列时段自行对照")
    lines.append("")
    lines.append("  时段表:")
    for lo, hi, name, what, bad in WATCH:
        lines.append("    %-16s %s" % (name, what))
        lines.append("      异常: %s" % bad)
    lines.append("")
    lines.append("  记录方式: 逐项记录(时间、症状、是否用药、处理)")
    lines.append("    不写成好像有点蔫这种模糊记忆")
    lines.append("")
    lines.append("  反应性质区分(不自行判断):")
    for s in reac:
        s = s.strip()
        if not s:
            continue
        if s in REACTIONS:
            sign, kind, action = REACTIONS[s]
            lines.append("    %s" % sign)
            lines.append("      可能属于: %s" % kind)
            lines.append("      口径: %s" % action)
            summary["reactions"].append(kind)
        else:
            lines.append("    [未登记] %s -> 需人工比对反应表" % s)
    if not reac:
        for s in REACTIONS:
            sign, kind, action = REACTIONS[s]
            lines.append("    %-24s %-14s %s" % (sign, kind, action))
    lines.append("")
    lines.append("  关键原则: 轻度反应与过敏反应的区别由兽医判断, 不要自己下结论")
    lines.append("    判断错了要么延误急救, 要么把正常反应当事故")
    lines.append("  部位处理红线: 不自行按摩, 不自行涂抹任何药膏, 不自行热敷或冰敷")
    lines.append("")

    lines.append("[六] 与免疫失败的区分")
    lines.append("-" * 68)
    for n, why, action in FAILURE:
        lines.append("  %-14s %s" % (n, why))
        lines.append("    处置: %s" % action)
    lines.append("")
    lines.append("  要说清的一句话: 疫苗不是保险, 是降低特定疾病的重症与死亡风险")
    lines.append("")

    lines.append("[七] 特殊情况")
    lines.append("-" * 68)
    for n, d in SPECIAL:
        lines.append("  %-24s %s" % (n, d))
    lines.append("")

    lines.append("[八] 就医红线")
    lines.append("-" * 68)
    keys = set(k for k, _, _ in RED_FLAGS)
    hits = [f for f in (red or []) if f in keys]
    if hits:
        summary["red_flag_hit"] = True
        for f in hits:
            for k, text, level in RED_FLAGS:
                if k == f:
                    lines.append("  [%s] %s" % (level, text))
                    if k in EMERGENCY:
                        summary["emergency"].append(k)
    else:
        summary["red_flag_hit"] = False
        lines.append("  未命中就医红线")
    lines.append("")
    lines.append("  绝对禁止:")
    for c in ["不在宠物生病期间接种, 病愈后时机由兽医判断",
              "不跳过规定的针次图省事; 不自行延长或缩短间隔",
              "不在不同疫苗之间自行切换或混用",
              "不为了看着精神好就推迟必要的加强免疫"]:
        lines.append("    - %s" % c)
    lines.append("")
    lines.append("免责: 本结果为接种记录核查与反应观察口径, 不构成疫苗方案或免疫学结论。")
    lines.append("免责: 疫苗品种与程序以执业兽医判断为准; 免疫评估以检测结论为准。")
    lines.append("=" * 68)
    return "\n".join(lines), summary


def load_json(path):
    with io.open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    # PowerShell 写出的 UTF-8 文件可能带 BOM, 不剥掉会让首个 key 取不到值且不报错
    raw = raw.lstrip("\ufeff")
    return json.loads(raw)


def _run_checks():
    r = []
    r.append(("疫苗类别 3 类", len(CATEGORIES) == 3))
    r.append(("必问问题 3 条", len(THREE_QUESTIONS) == 3))
    r.append(("记录字段 6 项", len(RECORD_FIELDS) == 6))
    r.append(("首免原则 6 条", len(PRINCIPLES) == 6))
    r.append(("漏打处理 5 条", len(MISSED) == 5))
    r.append(("观察时段 5 段", len(WATCH) == 5))
    r.append(("反应类型 6 类", len(REACTIONS) == 6))
    r.append(("红线 12 条", len(RED_FLAGS) == 12))
    r.append(("急诊项 2 条", len(EMERGENCY) == 2))
    r.append(("特殊情况 9 条", len(SPECIAL) == 9))
    r.append(("免疫失败 5 类", len(FAILURE) == 5))
    r.append(("过敏为急诊项", "anaphylaxis" in EMERGENCY))
    r.append(("抽搐为急诊项", "convulsion" in EMERGENCY))
    r.append(("核心依据含后果严重",
              "后果严重" in CATEGORIES["core"]["basis"]))
    r.append(("非核心依据含接触到病原",
              "接触到该病原" in CATEGORIES["non_core"]["basis"]))

    recs = [{"date": 100, "category": "core", "seq": 1},
            {"date": 130, "category": "core", "seq": 2}]
    r.append(("记录按日期排序", sort_records(recs)[0][0] == 100))
    r.append(("空记录返回空", sort_records([]) == []))
    r.append(("非法日期被忽略", sort_records([{"date": "x"}]) == []))
    r.append(("非字典被忽略", sort_records(["x"]) == []))
    r.append(("分类计数正确", count_by_category(sort_records(recs)) == {"core": 2}))
    r.append(("未提供今日时天数为空", days_since(100, None) is None))
    r.append(("距末次 30 天", days_since(100, 130) == 30))
    r.append(("记录齐状态", record_state(recs, 160)[0] == "记录齐"))
    r.append(("无记录为缺失", record_state([], 100)[0] == "记录缺失"))

    r.append(("当天为接种当天", watch_of(0)[0] == "接种当天"))
    r.append(("第 2 天为 24 小时段", watch_of(2)[0] == "接种后 24 小时"))
    r.append(("第 4 天为 24-48 小时段", watch_of(4)[0] == "接种后 24-48 小时"))
    r.append(("第 6 天为 72 小时段", watch_of(6)[0] == "接种后 72 小时"))
    r.append(("第 20 天为数周段", watch_of(20)[0] == "接种后数周"))

    txt, s = build_report({
        "species": "dog", "age_months": 12,
        "records": recs, "today": 160,
        "noncore_risk": True,
        "last_deworm": 160, "last_vaccine": 100,
        "red_flags": ["anaphylaxis"],
        "reactions": ["fever"],
    })
    r.append(("样例为犬", "犬" in txt))
    r.append(("样例记录齐", s["record_state"] == "记录齐"))
    r.append(("样例距末次 30 天", s["days_since_last"] == 30))
    r.append(("样例核心计数 2 针", s["counts"].get("core") == 2))
    r.append(("样例命中红线", s["red_flag_hit"] is True))
    r.append(("样例含急诊项", s["emergency"] == ["anaphylaxis"]))
    r.append(("样例检出同日", "同日进行" in txt))
    r.append(("样例记录反应", s["reactions"] == ["可能属免疫反应"]))
    r.append(("样例不给疫苗名", s["vaccine_named"] is False))
    r.append(("样例不给间隔天数", s["schedule_days_provided"] is False))
    r.append(("样例文本含必问三问", "三个必须问清楚的问题" in txt))

    _, s2 = build_report({})
    r.append(("空输入不报错", s2["record_state"] == "记录缺失"))
    r.append(("空输入天数为空", s2["days_since_last"] is None))
    r.append(("空输入未命中红线", s2["red_flag_hit"] is False))
    r.append(("空输入无反应", s2["reactions"] == []))

    _, s3 = build_report({"records": [{"date": 200, "category": "non_core"}],
                          "today": 260})
    r.append(("非核心计数正确", s3["counts"].get("non_core") == 1))
    r.append(("非核心样例距 60 天", s3["days_since_last"] == 60))

    r.append(("BOM 输入被正确剥离",
               load_json(_write_bom_sample())["species"] == "dog"))
    r.append(("未知红线被忽略",
               build_report({"red_flags": ["nope"]})[1]["red_flag_hit"] is False))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"species\": \"dog\", \"today\": 100}")
    return p


def selftest():
    results = _run_checks()
    failed = [name for name, ok in results if not ok]
    ok = len(failed) == 0
    lines = ["SELFTEST %s" % ("OK" if ok else "FAILED")]
    lines.append("checks=%d passed=%d failed=%d" % (
        len(results), len(results) - len(failed), len(failed)))
    for name in failed:
        lines.append("FAILED: %s" % name)
    here = os.path.dirname(os.path.abspath(__file__))
    with io.open(os.path.join(here, "_selftest_result.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return ok


def main():
    parser = argparse.ArgumentParser(description="宠物疫苗接种间隔与反应观察核查工具")
    parser.add_argument("--file", help="输入 JSON 文件路径 (UTF-8)")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument("--out", help="结果写入指定文件")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    if not args.file:
        parser.error("需要 --file 或 --selftest")

    data = load_json(args.file)
    report, summary = build_report(data)
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    out_path = args.out or os.path.join(here, "_last_result.txt")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(body)
    print("结果已写入: %s" % out_path)


if __name__ == "__main__":
    main()
