# -*- coding: utf-8 -*-
"""狗狗误食与消化异常核查工具。

用法:
  python ingest_check.py --file case.json [--json]
  python ingest_check.py --selftest

本工具不提供任何药物名称、剂量与催吐方法。
"""
import argparse
import io
import json
import os
import sys

# 物质分类: 代号 -> (名称, 风险等级, 处置方向, 注意事项)
SUBSTANCES = {
    "chocolate": ("巧克力", "高", "不观察, 立即联系兽医",
                  "含可可碱与咖啡因; 黑巧与可可含量越高风险越大"),
    "caffeine": ("咖啡与咖啡因", "高", "不观察, 立即联系兽医",
                 "咖啡、浓茶、可乐、能量饮料; 咖啡渣与茶叶同样有咖啡因"),
    "onion": ("洋葱、大蒜、大葱", "高", "不观察, 立即联系兽医",
              "含洋葱成分的汤汁、调味汁、婴儿米粉同样有风险"),
    "grape": ("葡萄、葡萄干、葡萄汁", "高", "不观察, 立即联系兽医",
              "干燥后单位重量风险上升"),
    "xylitol": ("木糖醇", "高", "不观察, 立即联系兽医",
                "无糖口香糖、无糖糖果、部分牙膏; 猫尤其危险"),
    "alcohol": ("酒精", "高", "不观察, 立即联系兽医",
                "酒、含酒调味品、发酵物; 含酒精饮料与酒酿类同样有风险"),
    "paraquat": ("百草枯", "极高", "不催吐、不喂水, 立即就医",
                 "除草剂; 属必须立即就医的类别"),
    "human_drug": ("人用药物", "高", "不观察, 立即联系兽医",
                   "退热药、镇痛药、抗生素、安眠药等; 任何剂量都应联系兽医"),
    "high_salt": ("高盐食物", "高", "不观察, 立即联系兽医",
                  "大量咸菜、腌制品、加工肉、薯片"),
    "bean_sprout": ("大量生豆芽", "留意", "核对量并联系兽医",
                    "生豆芽与大剂量蔬菜可能有风险"),
    "raw_fish": ("大量生鱼", "留意", "核对量并联系兽医",
                 "生鱼与熟鱼在营养与风险上不同, 煮熟更稳妥"),
    "fruit_pit": ("大量果核", "留意", "核对量并联系兽医",
                  "桃、杏、樱桃、李、枣等的核有阻塞风险"),
    "nut": ("大量坚果", "留意", "核对量并联系兽医",
            "尤其带壳坚果有窒息与阻塞风险"),
    "seasoning": ("烹调调味料", "留意", "核对成分并联系兽医",
                  "尤其含洋葱粉、蒜粉等的复合调味"),
    "spoiled": ("发酵与变质食物", "留意", "核对量并联系兽医",
                "呕吐物本身也可能含危险物质"),
    "unknown": ("不明物质", "待确认", "先弄清是什么再决定",
                "包装、残留物与照片是急诊判断的第一依据"),
}

# 异物分类: 代号 -> (名称, 风险, 处置, 说明)
OBJECTS = {
    "button_battery": ("纽扣电池", "极高", "立即就医", "不观察; 催吐会加快推进且有灼伤风险"),
    "coin": ("硬币", "较高", "尽快就医", "小型犬肠道细"),
    "sharp": ("尖锐物(鱼钩、缝衣针、牙签)", "高", "立即就医", "不催吐; 二次划伤风险"),
    "corrosive": ("腐蚀性(清洁剂、消毒剂、汽油)", "高", "立即就医", "不催吐、不喂水"),
    "string": ("线、绳、袜子、塑料薄膜", "高", "尽快就医", "肠梗阻风险"),
    "bone": ("硬骨头、硬塑料", "中到高", "尽快就医", "阻塞或碎裂损伤"),
    "pit": ("果核、枣核、桃子核", "中", "尽快就医", "阻塞风险"),
    "fur": ("布球、毛发团", "较低", "呕吐排出且精神正常可观察", "排不出或精神差则尽快就医"),
    "stone": ("小石子", "低", "通常可排出, 观察", ""),
    "paper": ("纸、少量食物残渣", "低", "通常可排出, 观察", ""),
}

# 不能催吐的情形
NO_EMETIC = {
    "sharp": ("尖锐物", "催吐会让尖锐物二次划伤食道与消化道", "立即就医"),
    "corrosive": ("腐蚀性物质", "催吐会让腐蚀物再次灼伤", "立即就医, 不喂水"),
    "button_battery": ("纽扣电池", "催吐会加快电池在消化道推进, 且有灼伤风险", "立即就医"),
    "symptomatic": ("已进入症状期", "反复呕吐可能提示已有损伤, 催吐加重负担", "立即就医"),
    "oil": ("石油类、油漆类", "吸入性肺炎风险", "立即就医"),
    "already_vomit": ("已发生剧烈呕吐或腹泻", "脱水与电解质紊乱风险, 催吐无意义", "立即就医"),
    "unconscious": ("意识模糊、反应迟钝", "呛入气道风险极高", "立即就医"),
}

# 消化异常分层
SYMPTOMS = {
    "undigested": ("呕吐物中有食物残渣, 未消化", "轻度",
                   "近期换粮、进食过快、吃太多", "观察并记录; 持续或加重就医"),
    "yellow_foam": ("呕吐物有黄色泡沫", "中度",
                    "胃酸、可能空腹过久、胆汁", "少量多次给水; 持续呕吐就医"),
    "blood_vomit": ("呕吐物带血丝或咖啡渣色", "危险",
                    "消化道损伤或异物", "尽快就医"),
    "loose": ("稀便、未成形", "轻度", "换粮、轻微饮食不当", "观察并记录"),
    "blood_stool": ("便中带血", "危险", "消化道损伤、寄生虫、感染", "尽快就医"),
    "jam_stool": ("果酱样便", "危险", "出血量较大", "立即就医"),
    "tar_stool": ("黑色柏油样便", "危险", "上消化道出血", "立即就医"),
    "vomit_4h": ("持续呕吐超过 4 小时", "危险", "脱水与电解质紊乱", "尽快就医"),
    "bloat": ("呕吐伴腹胀、无法排便排气", "危险", "肠梗阻可能", "立即就医"),
    "no_food_24h": ("完全不进食超过 24 小时", "危险", "肝脂肪肝等风险, 幼宠更早",
                    "尽快就医(幼犬幼猫更早)"),
    "lethargy": ("精神沉郁、蜷缩、痛叫", "危险", "疼痛或全身性状况", "尽快就医"),
    "young_gi": ("幼犬幼猫腹泻伴呕吐", "危险", "脱水进展快", "尽快就医"),
}

DANGER_ORDER = {"轻度": 1, "中度": 2, "危险": 3}

# 环境整改
ENV_ITEMS = [
    ("药品", "全部收进抽屉或带锁柜, 不放在台面、床头、沙发扶手"),
    ("清洁剂与消毒剂", "收到孩子与宠物接触不到的位置; 用完立即盖紧"),
    ("电池类", "遥控器、玩具、饰品里的电池收好; 纽扣电池尤其收进带锁柜"),
    ("食品", "不在人吃饭时给狗猫顺口; 剩菜尤其含洋葱味的不能给"),
    ("包装", "保留包装与残留物, 便于急诊判断"),
    ("垃圾桶", "使用带盖垃圾桶; 外出时注意翻倒的垃圾桶"),
    ("线与绳", "收好线团、纱线、绳结; 玩线绳类玩具时全程看护"),
    ("花与植物", "百合类对猫有严重风险, 家有猫时不摆放; 其他植物也要确认毒性"),
    ("药物保健品", "复合保健品中的某些成分也可能有风险"),
    ("外出", "留意地面、垃圾堆、动物粪便与骨头"),
]

# 就医红线
RED_FLAGS = [
    ("battery", "误食纽扣电池", "立即就医"),
    ("sharp", "误食鱼钩、缝衣针、牙签等尖锐物", "立即就医"),
    ("corrosive", "误食清洁剂、汽油、消毒剂、强酸强碱", "立即就医"),
    ("human_drug", "误食人用药物", "立即就医"),
    ("xylitol", "误食木糖醇(口香糖、无糖糖果、部分牙膏)", "立即就医"),
    ("chocolate", "误食巧克力、咖啡因", "立即就医"),
    ("onion", "误食洋葱、大蒜、大葱及含洋葱成分的汤汁与调味料", "立即就医"),
    ("grape", "误食葡萄、葡萄干、葡萄汁", "立即就医"),
    ("alcohol", "误食酒精", "立即就医"),
    ("high_salt", "误食高盐食物", "立即就医"),
    ("paraquat", "误食百草枯", "立即就医"),
    ("bone", "误食大量骨头、坚硬异物", "尽快就医"),
    ("pit", "误食果核、枣核、桃子核等硬核", "尽快就医"),
    ("string", "误食线、绳、袜子、塑料薄膜等可缠绕物", "尽快就医"),
    ("blood", "呕吐物或粪便带血", "尽快就医"),
    ("vomit_long", "持续呕吐超过 4 小时", "尽快就医"),
    ("no_food", "完全不进食超过 24 小时", "尽快就医"),
    ("lethargy", "精神沉郁、蜷缩不动、痛叫", "尽快就医"),
    ("delayed", "误食后症状延迟出现(数小时到数天)", "尽快就医"),
]

IMMEDIATE = ("battery", "sharp", "corrosive", "human_drug", "xylitol",
             "chocolate", "onion", "grape", "alcohol", "high_salt", "paraquat")


def risk_of(substance):
    s = SUBSTANCES.get(substance)
    if not s:
        return None
    return s


def can_emetic(substance, symptomatic):
    """返回 (是否可自行催吐, 原因, 处置方向)"""
    if substance in ("sharp", "corrosive", "button_battery", "oil"):
        code = substance if substance in NO_EMETIC else "sharp"
        name, why, action = NO_EMETIC[code]
        return False, why, action
    if symptomatic:
        name, why, action = NO_EMETIC["symptomatic"]
        return False, why, action
    if substance == "high_risk_food":
        return False, "高风险食物是否催吐由兽医判断", "立即联系兽医"
    return None, "是否需要催吐、用什么方式与剂量, 全部由兽医决定", "立即联系兽医"


def sym_level(sym):
    s = SYMPTOMS.get(sym)
    if not s:
        return 0
    return DANGER_ORDER.get(s[1], 0)


def build_report(data):
    species = (data.get("species", "dog") or "dog").strip()
    substance = (data.get("substance", "unknown") or "unknown").strip()
    amount = data.get("amount", "")
    hours = data.get("hours_since", 0)
    obj = (data.get("object_type", "") or "").strip()
    syms = data.get("symptoms", []) or []
    red = data.get("red_flags", []) or []
    age = data.get("age_months", 0)

    lines = []
    summary = {
        "substance_name": None, "risk": None,
        "emetic_allowed": None, "emetic_reason": None,
        "worst_symptom_level": None, "red_flag_hit": None,
        "immediate": [], "object_name": None,
        "drug_provided": False, "emetic_method_provided": False,
        "observation_hours_provided": False,
    }

    lines.append("=" * 68)
    lines.append("狗狗误食与消化异常核查")
    lines.append("=" * 68)
    lines.append("  本工具不提供任何药物名称、剂量与催吐方法。")
    lines.append("")

    lines.append("[一] 立刻确认三件事")
    lines.append("-" * 68)
    sp = "犬" if species == "dog" else "猫"
    lines.append("  1. 吃进去的是什么: 包装、残留物、照片")
    lines.append("  2. 吃了多少: %s" % (amount or "未提供"))
    lines.append("  3. 大概什么时候吃的: 距今 %g 小时" % float(hours or 0))
    lines.append("")
    lines.append("  物种: %s   月龄: %g" % (sp, float(age or 0)))
    lines.append("  不要在没弄清是什么之前就动手处理")
    lines.append("")

    lines.append("[二] 物质风险判定")
    lines.append("-" * 68)
    info = risk_of(substance)
    if info:
        name, risk, action, note = info
        summary["substance_name"] = name
        summary["risk"] = risk
        lines.append("  物质: %s" % name)
        lines.append("    风险等级: %s" % risk)
        lines.append("    处置方向: %s" % action)
        lines.append("    注意事项: %s" % note)
    else:
        lines.append("  物质代号未登记: %s, 需人工核对清单" % substance)
        lines.append("    处置方向: 先弄清是什么再决定; 保留包装与残留物")
    lines.append("")
    lines.append("  高风险物质清单:")
    for k in ("chocolate", "caffeine", "onion", "grape", "xylitol",
              "alcohol", "paraquat", "human_drug", "high_salt"):
        v = SUBSTANCES[k]
        lines.append("    %-12s %-6s %s" % (v[0], v[1], v[2]))
    lines.append("")
    lines.append("  需留意类别:")
    for k in ("bean_sprout", "raw_fish", "fruit_pit", "nut",
              "seasoning", "spoiled"):
        v = SUBSTANCES[k]
        lines.append("    %-12s %s" % (v[0], v[3]))
    lines.append("")

    if obj:
        lines.append("[三] 异物风险分层")
        lines.append("-" * 68)
        o = OBJECTS.get(obj)
        if o:
            oname, orisk, oaction, onote = o
            summary["object_name"] = oname
            lines.append("  异物: %s" % oname)
            lines.append("    风险: %s" % orisk)
            lines.append("    处置: %s" % oaction)
            if onote:
                lines.append("    说明: %s" % onote)
        else:
            lines.append("  异物代号未登记: %s, 需人工核对分层表" % obj)
        lines.append("")
        lines.append("  分层表:")
        for k in ("button_battery", "coin", "sharp", "corrosive", "string",
                  "bone", "pit", "fur", "stone", "paper"):
            v = OBJECTS[k]
            lines.append("    %-24s %-6s %s" % (v[0], v[1], v[2]))
        lines.append("")
        lines.append("  能吃能喝不等于没问题: 小型犬肠道细, 部分异物能通过但仍可能损伤")
        lines.append("  观察多久没症状才能放心: 须由兽医判断, 本工具不给具体小时数")
        lines.append("  部分损伤是延迟出现的(数小时到数天), 不能因现在没事就放心")
        lines.append("")

    lines.append("[四] 能不能催吐")
    lines.append("-" * 68)
    worst = 0
    for s in syms:
        lv = sym_level(s)
        if lv and lv > worst:
            worst = lv
    symptomatic = worst >= 3
    allowed, reason, action = can_emetic(substance, symptomatic)
    summary["emetic_allowed"] = allowed
    summary["emetic_reason"] = reason
    lines.append("  判定: %s" % ("不可自行催吐" if allowed is False else
                              "是否需要催吐由兽医决定"))
    lines.append("    原因: %s" % reason)
    lines.append("    处置方向: %s" % action)
    lines.append("")
    lines.append("  不能催吐的情形:")
    for k in ("sharp", "corrosive", "button_battery", "symptomatic",
              "oil", "already_vomit", "unconscious"):
        v = NO_EMETIC[k]
        lines.append("    %-16s %s" % (v[0], v[1]))
        lines.append("      处置: %s" % v[2])
    lines.append("")
    lines.append("  明确立场:")
    lines.append("    不推荐自行给狗或猫催吐; 是否需要催吐、用什么方式、剂量多少全部由兽医决定")
    lines.append("    灌肥皂水、灌双氧水、按压腹部等方法不要自行尝试")
    lines.append("      这些方法可能造成呛入、加重损伤或延误正确处理")
    lines.append("    不确定能不能催吐时, 正确做法是就医, 而不是试一个可能有害的方法")
    lines.append("")

    lines.append("[五] 症状分层")
    lines.append("-" * 68)
    summary["worst_symptom_level"] = worst
    if not syms:
        lines.append("  未提供症状")
    for s in syms:
        s = s.strip()
        if not s:
            continue
        if s in SYMPTOMS:
            sign, level, cause, advice = SYMPTOMS[s]
            lines.append("  [%s] %s" % (level, sign))
            lines.append("    排查方向: %s" % cause)
            lines.append("    就医口径: %s" % advice)
        else:
            lines.append("  [未登记] %s -> 需人工比对分层表" % s)
    lines.append("")
    lines.append("  前提: 已排除误食异物与有毒物质")
    lines.append("  时限口径: 本工具不给观察多少小时的固定结论")
    lines.append("    幼犬幼猫与成年犬猫差别很大, 有基础疾病的与健康的差别很大")
    lines.append("")

    lines.append("[六] 就医红线")
    lines.append("-" * 68)
    keys = set(k for k, _, _ in RED_FLAGS)
    hits = [f for f in (red or []) if f in keys]
    if hits:
        summary["red_flag_hit"] = True
        for f in hits:
            for k, text, level in RED_FLAGS:
                if k == f:
                    lines.append("  [%s] %s" % (level, text))
                    if k in IMMEDIATE:
                        summary["immediate"].append(k)
    else:
        summary["red_flag_hit"] = False
        lines.append("  未命中就医红线")
    lines.append("")

    lines.append("[七] 环境整改")
    lines.append("-" * 68)
    for n, d in ENV_ITEMS:
        lines.append("  %-14s %s" % (n, d))
    lines.append("")
    lines.append("  关于百合: 百合类植物对猫有严重风险")
    lines.append("    且可能从花粉、叶片甚至花瓶水途径发生; 有猫的家庭不摆放百合类")
    lines.append("")

    lines.append("[八] 就诊时带什么")
    lines.append("-" * 68)
    for n in ("食品包装或药品包装(判断成分的第一依据)",
              "残留物(呕吐物、食物残渣)",
              "误食时间记录",
              "大致摄入量记录",
              "症状出现的时间与表现",
              "既往病史与用药史",
              "体重"):
        lines.append("  + %s" % n)
    lines.append("")
    lines.append("免责: 本结果为误食自查与分流口径, 不构成中毒判定或治疗结论。")
    lines.append("免责: 误食处置以兽医判断为准; 用药遵医嘱。")
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
    r.append(("物质表 16 类", len(SUBSTANCES) == 16))
    r.append(("异物表 10 类", len(OBJECTS) == 10))
    r.append(("禁催吐 7 类", len(NO_EMETIC) == 7))
    r.append(("症状表 12 类", len(SYMPTOMS) == 12))
    r.append(("环境整改 10 项", len(ENV_ITEMS) == 10))
    r.append(("红线 19 条", len(RED_FLAGS) == 19))
    r.append(("立即就医 11 条", len(IMMEDIATE) == 11))

    r.append(("巧克力风险高", SUBSTANCES["chocolate"][1] == "高"))
    r.append(("百草枯风险极高", SUBSTANCES["paraquat"][1] == "极高"))
    r.append(("木糖醇标注猫危险", "猫尤其危险" in SUBSTANCES["xylitol"][3]))
    r.append(("洋葱标注汤汁风险", "汤汁" in SUBSTANCES["onion"][3]))
    r.append(("巧克力标注黑巧风险", "黑巧" in SUBSTANCES["chocolate"][3]))
    r.append(("葡萄标注干燥风险", "干燥" in SUBSTANCES["grape"][3]))
    r.append(("纽扣电池风险极高", OBJECTS["button_battery"][1] == "极高"))
    r.append(("尖锐物不催吐", OBJECTS["sharp"][2] == "立即就医"))
    r.append(("线绳类为肠梗阻", "肠梗阻" in OBJECTS["string"][3]))
    r.append(("小石子为低风险", OBJECTS["stone"][1] == "低"))

    r.append(("尖锐物判定不可催吐", can_emetic("sharp", False)[0] is False))
    r.append(("腐蚀物判定不可催吐", can_emetic("corrosive", False)[0] is False))
    r.append(("纽扣电池判定不可催吐",
              can_emetic("button_battery", False)[0] is False))
    r.append(("石油判定不可催吐", can_emetic("oil", False)[0] is False))
    r.append(("有危险症状时判定不可催吐",
              can_emetic("chocolate", True)[0] is False))
    r.append(("无危险症状时不自行判定",
              can_emetic("chocolate", False)[0] is None))

    r.append(("血便为危险", sym_level("blood_stool") == 3))
    r.append(("稀便为轻度", sym_level("loose") == 1))
    r.append(("黄泡沫为中度", sym_level("yellow_foam") == 2))
    r.append(("柏油样便为危险", sym_level("tar_stool") == 3))
    r.append(("未登记症状为 0", sym_level("nope") == 0))

    txt, s = build_report({
        "species": "dog", "substance": "chocolate", "amount": "咬了一口",
        "hours_since": 1, "object_type": "sharp",
        "symptoms": ["blood_vomit"], "red_flags": ["battery"],
        "age_months": 24,
    })
    r.append(("样例物质为巧克力", s["substance_name"] == "巧克力"))
    r.append(("样例风险高", s["risk"] == "高"))
    r.append(("样例异物为尖锐物", "尖锐物" in s["object_name"]))
    r.append(("样例不可自行催吐", s["emetic_allowed"] is False))
    r.append(("样例症状为危险", s["worst_symptom_level"] == 3))
    r.append(("样例命中红线", s["red_flag_hit"] is True))
    r.append(("样例含立即就医项", s["immediate"] == ["battery"]))
    r.append(("样例不给药物", s["drug_provided"] is False))
    r.append(("样例不给催吐方法", s["emetic_method_provided"] is False))
    r.append(("样例不给观察小时数", s["observation_hours_provided"] is False))
    r.append(("样例文本含立刻确认三件事", "立刻确认三件事" in txt))

    _, s2 = build_report({})
    r.append(("空输入不报错", s2["substance_name"] == "不明物质"))
    r.append(("空输入待确认风险", s2["risk"] == "待确认"))
    r.append(("空输入未命中红线", s2["red_flag_hit"] is False))
    r.append(("空输入无立即项", s2["immediate"] == []))

    _, s3 = build_report({"substance": "nope", "object_type": "coin",
                          "symptoms": ["loose"]})
    r.append(("未登记物质不报错", s3["risk"] is None))
    r.append(("硬币对象正确", "硬币" in s3["object_name"]))
    r.append(("稀便为轻度", s3["worst_symptom_level"] == 1))

    _, s4 = build_report({"substance": "onion", "symptoms": ["jam_stool"],
                          "red_flags": ["onion", "xylitol"]})
    r.append(("双重红线均立即", len(s4["immediate"]) == 2))
    r.append(("果酱样便为危险", s4["worst_symptom_level"] == 3))

    r.append(("BOM 输入被正确剥离",
               load_json(_write_bom_sample())["species"] == "dog"))
    r.append(("未知红线被忽略",
               build_report({"red_flags": ["nope"]})[1]["red_flag_hit"] is False))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"species\": \"dog\", \"substance\": \"grape\"}")
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
    parser = argparse.ArgumentParser(description="狗狗误食与消化异常核查工具")
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
