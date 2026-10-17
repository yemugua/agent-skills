# -*- coding: utf-8 -*-
"""猫砂盆配置与拒绝原因排查工具。

用法:
  python litter_setup.py --file cats.json [--json]
  python litter_setup.py --selftest

本工具不推荐品牌, 不给药物, 不诊断尿路疾病。
"""
import argparse
import io
import json
import os
import sys

# 就医红线: (代号, 说明, 级别)
RED_FLAGS = [
    ("anuria", "公猫频繁进猫砂盆却尿不出、蹲坐时间异常长、频繁舔下体", "立即就医"),
    ("penis_exposed", "公猫龟头长时间露在包皮外", "立即就医"),
    ("almost_no_urine", "猫砂盆中几乎没有尿, 或只有几滴", "立即就医"),
    ("painful", "猫排尿时明显疼痛、叫声尖锐、血尿", "尽快就医"),
    ("pose_no_urine", "公猫蹲在盆外做出排尿姿势但无尿", "立即就医"),
    ("no_urine_24h", "超过 24 小时未见排尿记录, 幼猫尤其危险", "尽快就医"),
    ("hematuria", "尿血、尿液浑浊带沉淀、有明显异味", "尽快就医"),
    ("out_urine_lick", "排尿姿势正常但尿在盆外, 且伴有舔下体频繁", "尽快就医"),
    ("genital_swell", "盆外排尿同时出现舔生殖器异常、阴茎红肿", "尽快就医"),
    ("kitten_no_urine", "幼猫(尤其未满月)无法排尿", "立即就医"),
    ("female_lick", "母猫持续舔外生殖器、外生殖器异常红肿或分泌物增多", "尽快就医"),
]

EMERGENCY = ("anuria", "penis_exposed", "almost_no_urine",
             "pose_no_urine", "kitten_no_urine")

# 十二类原因
REASONS = [
    ("urine_block", "尿闭等泌尿问题(急症)", "是否频繁进盆却尿不出、蹲坐久、舔下体频繁",
     "先排红线, 是急症立即就医"),
    ("dirty_box", "盆脏", "有没有超过 1 天没铲、盆底是否有积尿块", "增加铲屎频率"),
    ("small_box", "盆太小", "猫放进去能否转身、伸展", "换大一号盆"),
    ("bad_location", "位置不合适", "是否在噪音源、走动频繁处、门口", "移位"),
    ("wrong_style", "盆型不合适", "猫是否害怕封闭、是否喜欢隐蔽",
     "换盆型或并排放新旧盆"),
    ("litter_hate", "猫砂类型不喜欢", "是否刚换过砂、是否刚倒上新砂",
     "新旧砂混合过渡, 逐步替换"),
    ("litter_deep", "猫砂太厚", "砂层厚度是否过深", "减薄到合适的厚度"),
    ("too_clean", "盆太干净或太脏", "是否刚洗过盆、有没有残留气味", "恢复正常使用即可"),
    ("multi_cat_conflict", "多猫互相抢占", "是否有猫被阻挡、是否都在用同一个盆",
     "增加盆数、分散摆放"),
    ("startle", "意外(惊吓、噪声)", "近期是否有搬家、装修、新成员",
     "恢复安静环境, 给适应时间"),
    ("age_limit", "年龄或行动不便", "幼猫、老年猫、行动不便的猫",
     "改低边入口、更大更浅的盆"),
    ("stress", "环境变化或压力", "新成员、访客、作息变化、窗外变化",
     "减少压力源, 提供退避空间"),
]

# 四类猫砂
LITTERS = {
    "clay": {"name": "膨润土(颗粒黏土)", "dust": "中等", "clump": "好",
             "ingest": "相对低", "flush": "不可冲厕",
             "note": "结团快、吸水好、易铲、价格低、接受度普遍较高"},
    "tofu": {"name": "豆腐砂", "dust": "低", "clump": "中等",
             "ingest": "较高", "flush": "部分可冲厕, 需确认产品说明",
             "note": "外观与气味接近食物, 误食风险最高; 幼猫与好奇的猫风险更高"},
    "wood": {"name": "木砂(刨花、木屑)", "dust": "低", "clump": "中等",
             "ingest": "中等", "flush": "可冲厕, 需确认产品说明",
             "note": "吸水后易碎, 清理略麻烦, 部分猫不接受"},
    "crystal": {"name": "水晶砂(硅胶颗粒)", "dust": "低", "clump": "不结团",
                "ingest": "相对低", "flush": "不可冲厕",
                "note": "吸水后不结团, 只能整盆换, 多数猫接受度一般"},
}

# 盆型
BOXES = {
    "open": {"name": "开放式", "note": "无顶盖、侧壁低, 视野好、进出自由; 多数猫更容易接受"},
    "covered": {"name": "半封闭(顶盖)", "note": "有顶盖, 视觉遮蔽、聚味; 部分猫偏好隐蔽感, 部分不喜欢封闭"},
    "auto": {"name": "全自动猫砂盆", "note": "自动或半自动清理; 噪音、震动、滚筒转动可能吓到猫"},
    "oversized": {"name": "极大号盆", "note": "空间充裕, 常配合顶盖; 跳跃力好的猫可能喜欢"},
}

# 位置要求
LOCATIONS = [
    ("安静", "噪音、震动、机器运转会劝退"),
    ("不堵", "人流经过、门口、洗衣机旁会让猫觉得不安全"),
    ("有遮挡但不压抑", "猫需要能观察、也能退避的空间"),
    ("通风但无穿堂风", "聚味太重会被嫌弃, 直吹也会不适"),
    ("分散摆放", "多猫时集中摆放会互相抢占"),
    ("靠近饮水与休息区", "猫倾向在自己的领地核心区排泄"),
    ("不在洗衣机旁", "震动与噪音是常见干扰源"),
]

# 清洁口径
CLEAN = [
    ("铲屎频率", "每天至少 1-2 次; 多猫时按猫数增加"),
    ("铲的时机", "猫排便后尽快铲; 猫对正在使用的盆接受度低"),
    ("换砂频率", "结团砂盆面脏了换底砂; 不结团砂按使用状况整盆更换"),
    ("洗盆", "按脏污程度; 洗净后完全晾干再放回"),
    ("洗盆用品", "中性清洁剂即可; 避免强烈香味清洁剂"),
    ("除味来源", "尿味多来自盆本身、地面残留与织物, 不只是猫砂"),
    ("环境", "通风; 除味产品注意对猫的呼吸道刺激与舔食风险"),
]

SYMPTOMS = {
    "outside_normal": ("尿在盆外但排尿姿势正常、能排出尿",
                      "多为盆型、位置、清洁或情绪标记, 按十二类顺序排查"),
    "no_urine": ("排不出尿或排尿疼痛", "尿闭或尿路问题, 急症; 立即就医, 不做行为排查"),
    "sudden_change": ("本来一直用盆的猫突然乱尿",
                      "更可能是身体或环境出了问题, 不是行为变坏; 先排红线"),
}


def boxes_needed(cat_count):
    n = int(cat_count or 0)
    if n <= 0:
        return 2
    return n + 1


def emergency_level(flags):
    hits = [f for f in (flags or []) if f in dict((k, 1) for k, _, _ in RED_FLAGS)]
    if not hits:
        return 0, hits, "未命中就医红线"
    if any(f in EMERGENCY for f in hits):
        return 3, hits, "命中急诊项, 立即就医; 不做行为排查"
    if len(hits) >= 2:
        return 2, hits, "命中多项红线, 尽快就医"
    return 1, hits, "命中红线项, 按红线处置"


def build_report(data):
    cat_count = data.get("cat_count", 1)
    age = (data.get("age", "adult") or "adult").strip()
    kitten = bool(data.get("has_kitten", False))
    litter = (data.get("litter_type", "") or "").strip()
    loc_ok = data.get("location_ok", None)
    scooped = bool(data.get("scooped_today", False))
    boxes = data.get("boxes", 0)
    reasons = data.get("refuse_reasons", []) or []
    sym = data.get("symptoms", []) or []
    red = data.get("red_flags", []) or []

    lines = []
    summary = {
        "boxes_needed": None, "boxes_ok": None, "emergency_level": None,
        "emergency": [], "red_flag_hit": None,
        "litter_name": None, "reasons": [], "symptoms": [],
        "brand_recommended": False, "drug_provided": False,
    }

    lines.append("=" * 68)
    lines.append("猫砂盆配置与拒绝原因排查")
    lines.append("=" * 68)
    lines.append("  本工具不推荐品牌, 不给药物, 不诊断尿路疾病。")
    lines.append("")

    lines.append("[一] 先排就医红线")
    lines.append("-" * 68)
    lv, hits, advice = emergency_level(red)
    summary["emergency_level"] = lv
    summary["emergency"] = [f for f in hits if f in EMERGENCY]
    summary["red_flag_hit"] = bool(hits)
    if hits:
        for f in hits:
            for k, text, level in RED_FLAGS:
                if k == f:
                    lines.append("  [%s] %s" % (level, text))
    else:
        lines.append("  未命中就医红线")
    lines.append("  结论: %s" % advice)
    lines.append("")
    lines.append("  红线一览 (共 %d 条):" % len(RED_FLAGS))
    for k, text, level in RED_FLAGS:
        lines.append("    %-18s %-8s %s" % (k, level, text))
    lines.append("")
    lines.append("  关键区分:")
    lines.append("    尿在盆外但排尿姿势正常、能排出尿 -> 多为行为或环境问题")
    lines.append("    排不出尿或排尿疼痛 -> 尿闭急症, 立即就医")
    lines.append("    把前者当后者会延误救命")
    lines.append("")

    lines.append("[二] 盆数与尺寸")
    lines.append("-" * 68)
    need = boxes_needed(cat_count)
    summary["boxes_needed"] = need
    have = int(boxes or 0)
    ok = have >= need
    summary["boxes_ok"] = ok
    lines.append("  猫数: %g   现有盆数: %d   建议盆数: %d" % (
        float(cat_count or 0), have, need))
    lines.append("    数量口径: 猫数加一(通用)")
    lines.append("    判定: %s" % ("达标" if ok else "不足, 建议增加至 %d 个" % need))
    lines.append("    为什么加一: 分散需求; 清洁一个盆时另一个还能用")
    lines.append("      猫对正在被清理的盆接受度很低")
    lines.append("    多猫抢占时: 需考虑分布摆放, 不是简单放在一个角落")
    lines.append("")
    lines.append("  尺寸口径:")
    lines.append("    基本要求: 猫能完全进去并转身、能舒展趴下")
    lines.append("    更实用: 把猫放进去后能自然伸展身体、有多余空间")
    lines.append("    顶盖式盆: 开口要够猫进出")
    lines.append("    幼猫与行动不便的老猫: 适合低边入口")
    lines.append("    阶段: %s" % ("幼猫" if kitten else age))
    lines.append("")

    lines.append("[三] 盆型与位置")
    lines.append("-" * 68)
    for k in ("open", "covered", "auto", "oversized"):
        v = BOXES[k]
        lines.append("  %-16s %s" % (v["name"], v["note"]))
    lines.append("")
    lines.append("  没有哪种盆型最好, 只有哪种你的猫愿意用")
    lines.append("  换盆型的做法: 并排放新旧两个盆让猫自己选, 不要一次只留新的")
    lines.append("")
    lines.append("  位置要求:")
    for n, why in LOCATIONS:
        lines.append("    %-16s %s" % (n, why))
    lines.append("")
    lines.append("  最常见的错误位置: 马桶旁、洗衣机旁、门口走廊、封闭卫生间角落")
    lines.append("    问题不是不能放, 而是猫的主观感受不好")
    lines.append("  位置核对: %s" % ("已确认安静不堵" if loc_ok else "未确认或存在问题"))
    lines.append("")

    lines.append("[四] 四类猫砂对比")
    lines.append("-" * 68)
    info = LITTERS.get(litter)
    if info:
        summary["litter_name"] = info["name"]
        lines.append("  当前类型: %s" % info["name"])
        lines.append("    说明: %s" % info["note"])
        lines.append("    粉尘 %s | 结团 %s | 误食风险 %s | 冲厕 %s" % (
            info["dust"], info["clump"], info["ingest"], info["flush"]))
    else:
        lines.append("  未提供已登记的猫砂类型, 对照下表选择")
    lines.append("")
    lines.append("  %-16s %-6s %-8s %-8s %s" % ("类型", "粉尘", "结团", "误食", "冲厕"))
    for k in ("clay", "tofu", "wood", "crystal"):
        v = LITTERS[k]
        lines.append("  %-16s %-6s %-8s %-8s %s" % (
            v["name"], v["dust"], v["clump"], v["ingest"], v["flush"]))
    lines.append("")
    lines.append("  误食风险: 豆腐砂最容易被误食, 外观与气味接近食物")
    lines.append("    幼猫与好奇的猫风险更高; 发现误食后不要催吐, 尽快联系兽医")
    lines.append("  能否冲厕: 取决于产品说明与自家管道状况, 不确定就不要冲")
    lines.append("  换类型: 新旧砂按比例混合过渡, 一次全换容易导致拒绝使用")
    lines.append("")

    lines.append("[五] 清洁与除味")
    lines.append("-" * 68)
    for n, d in CLEAN:
        lines.append("  %-10s %s" % (n, d))
    lines.append("  今日已铲: %s" % ("是" if scooped else "否, 盆脏是常见原因"))
    lines.append("")
    lines.append("  除味的关键不是加香味: 织物、地面缝隙、墙角残留才是味道来源")
    lines.append("    用香味产品盖住, 猫反而更容易拒绝进盆")
    lines.append("")

    lines.append("[六] 症状分流")
    lines.append("-" * 68)
    if not sym:
        lines.append("  未提供症状")
    for s in sym:
        s = s.strip()
        if not s:
            continue
        if s in SYMPTOMS:
            sign, action = SYMPTOMS[s]
            lines.append("  [记录] %s" % sign)
            lines.append("    处理: %s" % action)
            summary["symptoms"].append(s)
        else:
            lines.append("  [未登记] %s -> 需人工比对分流表" % s)
    lines.append("")

    lines.append("[七] 十二类原因排查顺序")
    lines.append("-" * 68)
    given = set(x.strip() for x in (reasons or []) if x and str(x).strip())
    for i, (code, name, how, action) in enumerate(REASONS, 1):
        mark = "[已勾选]" if code in given else "[未勾]"
        lines.append("  %2d. %s %s" % (i, mark, name))
        lines.append("      怎么查: %s" % how)
        lines.append("      处理: %s" % action)
        if code in given:
            summary["reasons"].append(name)
    lines.append("")
    lines.append("  排查不能跳步; 第 1 条必须先排")
    lines.append("    把尿闭当成行为问题去调盆换砂, 是可能延误的路径")
    lines.append("")

    lines.append("[八] 记录要求")
    lines.append("-" * 68)
    for n in ("排尿次数(按天)", "排尿地点(盆内或盆外, 具体位置)",
              "盆使用情况(是否进去、停留多久、是否正常使用姿势)",
              "清洁记录(每次铲的时间、每次换砂的时间)",
              "猫砂更换(时间、类型、过渡方式)",
              "盆的位置调整(调整时间与前后对比)",
              "多猫情况下每只分别记"):
        lines.append("  + %s" % n)
    lines.append("")
    lines.append("  为什么要逐项记: 行为问题的排查靠排除法, 只有记录才能排除")
    lines.append("")

    lines.append("免责: 本结果为配置口径与排查顺序, 不构成排尿异常的诊断结论。")
    lines.append("免责: 排尿异常以兽医诊断为准; 用药遵医嘱。")
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
    r.append(("红线 11 条", len(RED_FLAGS) == 11))
    r.append(("急诊项 5 条", len(EMERGENCY) == 5))
    r.append(("十二类原因", len(REASONS) == 12))
    r.append(("四类猫砂", len(LITTERS) == 4))
    r.append(("四种盆型", len(BOXES) == 4))
    r.append(("位置要求 7 项", len(LOCATIONS) == 7))
    r.append(("清洁口径 7 项", len(CLEAN) == 7))
    r.append(("症状分流 3 类", len(SYMPTOMS) == 3))

    r.append(("1 只猫需 2 个盆", boxes_needed(1) == 2))
    r.append(("2 只猫需 3 个盆", boxes_needed(2) == 3))
    r.append(("3 只猫需 4 个盆", boxes_needed(3) == 4))
    r.append(("5 只猫需 6 个盆", boxes_needed(5) == 6))
    r.append(("猫数为 0 时给 2 个", boxes_needed(0) == 2))

    r.append(("尿闭为急诊项", "anuria" in EMERGENCY))
    r.append(("幼猫无法排尿为急诊项", "kitten_no_urine" in EMERGENCY))
    r.append(("血尿不是急诊项", "hematuria" not in EMERGENCY))
    r.append(("豆腐砂误食风险最高",
              LITTERS["tofu"]["ingest"] == "较高"))
    r.append(("膨润土不可冲厕", LITTERS["clay"]["flush"] == "不可冲厕"))
    r.append(("水晶砂不结团", LITTERS["crystal"]["clump"] == "不结团"))
    r.append(("豆腐砂标注误食",
              "误食" in LITTERS["tofu"]["note"]))
    r.append(("第一类原因为尿闭", REASONS[0][0] == "urine_block"))
    r.append(("第二类原因为盆脏", REASONS[1][0] == "dirty_box"))
    r.append(("末类原因为压力", REASONS[-1][0] == "stress"))

    r.append(("无红线为 0 级", emergency_level([])[0] == 0))
    r.append(("一项非急诊红线为 1 级", emergency_level(["hematuria"])[0] == 1))
    r.append(("急诊项为 3 级", emergency_level(["anuria"])[0] == 3))
    r.append(("两项非急诊为 2 级",
              emergency_level(["hematuria", "painful"])[0] == 2))
    r.append(("未知红线被忽略", emergency_level(["nope"])[0] == 0))

    txt, s = build_report({
        "cat_count": 2, "age": "adult", "litter_type": "tofu",
        "location_ok": False, "scooped_today": False, "boxes": 1,
        "refuse_reasons": ["small_box", "dirty_box"],
        "symptoms": ["sudden_change"], "red_flags": ["penis_exposed"],
    })
    r.append(("样例需 3 个盆", s["boxes_needed"] == 3))
    r.append(("样例盆数不足", s["boxes_ok"] is False))
    r.append(("样例命中红线", s["red_flag_hit"] is True))
    r.append(("样例为 3 级", s["emergency_level"] == 3))
    r.append(("样例含急诊项", s["emergency"] == ["penis_exposed"]))
    r.append(("样例猫砂为豆腐砂", s["litter_name"] == "豆腐砂"))
    r.append(("样例记录 2 类原因", len(s["reasons"]) == 2))
    r.append(("样例记录症状", s["symptoms"] == ["sudden_change"]))
    r.append(("样例不推荐品牌", s["brand_recommended"] is False))
    r.append(("样例不给药物", s["drug_provided"] is False))
    r.append(("样例文本含猫数加一", "猫数加一" in txt))

    _, s2 = build_report({})
    r.append(("空输入不报错", s2["boxes_needed"] == 2))
    r.append(("空输入未命中红线", s2["red_flag_hit"] is False))
    r.append(("空输入无原因勾选", s2["reasons"] == []))
    r.append(("空输入无症状", s2["symptoms"] == []))

    _, s3 = build_report({"cat_count": 4, "boxes": 5, "litter_type": "nope",
                          "refuse_reasons": ["nope"]})
    r.append(("4 只猫需 5 个", s3["boxes_needed"] == 5))
    r.append(("5 个盆达标", s3["boxes_ok"] is True))
    r.append(("未登记猫砂不报错", s3["litter_name"] is None))
    r.append(("未登记原因不计入", s3["reasons"] == []))

    r.append(("BOM 输入被正确剥离",
               load_json(_write_bom_sample())["cat_count"] == 3))
    r.append(("字符串形式的症状可解析",
               build_report({"symptoms": ["no_urine"]})[1]["symptoms"] == ["no_urine"]))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"cat_count\": 3, \"boxes\": 4}")
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
    parser = argparse.ArgumentParser(description="猫砂盆配置与拒绝原因排查工具")
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
