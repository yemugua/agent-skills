# -*- coding: utf-8 -*-
"""犬猫绝育术前术后核查工具。

用法:
  python neuter_check.py --file case.json [--json]
  python neuter_check.py --selftest

本工具不给药物名称与剂量, 不判断手术适宜性。
"""
import argparse
import io
import json
import os
import sys

# 就医红线: (代号, 说明, 紧急级别)
RED_FLAGS = [
    ("bleeding_on", "切口出血 20 分钟不减少, 纱布浸透或血滴持续滴落", "尽快就医"),
    ("wound_dehiscence", "切口边缘分开, 可见皮下组织, 缝线断裂", "立即就医"),
    ("anuria_male", "公猫 24-48 小时内排不出尿", "立即就医"),
    ("persistent_vomit", "术后 12 小时以上反复呕吐且拒水", "尽快联系医生"),
    ("discharge_female", "母猫持续大量阴道分泌物, 有臭味或发热", "尽快就医"),
    ("no_intake_24h", "精神沉郁, 不吃不喝超过 24 小时", "尽快就医"),
    ("distension", "腹胀明显, 触碰腹部疼痛反应剧烈", "尽快就医"),
    ("purulent", "伤口红肿热痛, 有脓性分泌物, 结痂处崩开", "尽快就医"),
    ("temp_extreme", "术后超过 48 小时体温明显升高或偏低", "联系医生"),
    ("anesthesia_comp", "呼吸急促, 持续呕吐, 抽搐, 牙龈发白或发绀", "立即就医"),
    ("adhesion", "腹部或腹股沟出现硬结与牵拉感", "就医评估粘连"),
    ("pain_persist", "术后超过 2-3 天疼痛姿态不减, 活动明显受限", "就医评估"),
    ("base_disease", "有心肾代谢等基础疾病或长期用药", "须兽医评估手术适宜性"),
    ("window_doubt", "体重与年龄窗口存疑, 体型未成熟", "须兽医评估手术适宜性"),
]

EMERGENCY = ("wound_dehiscence", "anuria_male", "anesthesia_comp")

# 术前检查项
PREOP = [
    ("temperature", "体温", "是否在正常范围", "发热提示可能存在感染, 需先处理"),
    ("auscultation", "心肺听诊", "有无杂音, 心率是否异常", "心肺异常显著改变麻醉风险"),
    ("cbc", "血常规", "白细胞, 红细胞, 血小板", "贫血影响耐受, 感染或炎症需先处理"),
    ("biochem", "生化(肝肾)", "肝肾功能指标", "肝肾功能异常需调整麻醉方案"),
    ("coagulation", "凝血功能", "出血风险", "部分机构会做, 尤其深部手术"),
    ("screening", "传染病筛查", "按机构规定项目", "阳性需先处理或改变方案"),
    ("body_score", "体重与体况评分", "体重与脂肪覆盖", "过瘦风险高, 过胖增加麻醉与伤口愈合风险"),
    ("skin", "皮肤与毛发状况", "有无皮肤病, 剃毛区域", "感染区域避开切口"),
    ("vaccine_deworm", "疫苗与驱虫状态", "是否处于有效期", "未完成免疫需与医生确认时序"),
    ("history", "既往病史", "慢性病, 长期用药, 过敏史", "如实告知, 不隐瞒"),
    ("repro_state", "发情与妊娠状态", "母犬母猫是否处于发情期或妊娠", "直接影响时机与方案"),
]

# 体型
SIZES = {"small": "小型", "medium": "中型", "large": "大型"}

# 术后日程
SCHEDULE = [
    (0, 1, "术后当天", "未清醒属正常; 清醒后不喝水超过 12 小时需联系医生"),
    (1, 3, "术后 1-2 天", "排不出尿是急症; 呕吐反复需联系医生"),
    (3, 6, "术后 3-5 天", "切口有无红肿渗液; 脓性分泌物需就诊"),
    (6, 9, "术后 7 天", "拆线或复查, 按医嘱时间, 不自行拆线"),
    (9, 15, "术后 10-14 天", "拆线后切口状况; 活动逐步恢复"),
    (14, 31, "术后 1 个月", "体重监测, 按月记录并相应调整喂食量"),
    (31, 99999, "长期", "行为与泌尿状况观察, 记录变化供下次就诊参考"),
]

# 并发症
COMPLICATIONS = {
    "bleeding": ("出血", "切口持续渗血, 纱布浸透, 地上持续有血滴, 黏膜苍白",
                 "渗血 20 分钟不减少即为红线; 保持安静并压迫观察, 持续不止立即就医"),
    "dehiscence": ("切口裂开", "切口边缘分开, 可见皮下组织, 缝线断裂或崩脱",
                   "红线, 立即就医; 不自行按压或涂抹"),
    "adhesion": ("粘连", "术后长期腹部或腹股沟出现硬结, 牵拉感, 局部皮肤凹陷",
                 "非急症但需就诊评估, 可能需要康复处理"),
    "infection": ("感染", "切口红肿热痛, 脓性分泌物, 发热, 周围皮肤发烫",
                  "尽快就医; 不自行涂抹任何药膏"),
    "anuria": ("尿闭(公猫高发)", "频繁进猫砂盆却尿不出, 蹲坐时间异常长, 龟头长时间露在包皮外",
               "急症, 立即就医"),
    "vomit_refuse": ("呕吐与不进食", "反复呕吐, 拒水, 精神沉郁",
                     "超过 12 小时未改善需联系医生, 幼宠更早"),
    "fever": ("发热", "体温明显升高, 精神差, 食欲低", "联系医生"),
    "coag_weak": ("出血倾向加重", "手术部位以外的出血点, 牙龈渗血", "就医排查凝血问题"),
    "anesthesia_comp": ("麻醉后并发症", "呼吸急促, 持续呕吐, 抽搐, 牙龈发白或发绀", "急症"),
    "pain_persist": ("持续疼痛未缓解", "术后超过 2-3 天疼痛姿态不减, 活动明显受限",
                     "就医评估疼痛管理方案"),
}


def window_judge(age_months, breed_size, species):
    """只给参考口径, 不做手术适宜性结论。"""
    a = float(age_months or 0)
    size = (breed_size or "medium").strip()
    notes = []
    level = "待兽医评估"
    if a < 6:
        level = "过小"
        notes.append("月龄偏小, 过小会影响发育, 具体月龄须由兽医按品种评估")
    elif a < 12:
        level = "需评估"
        notes.append("未满周岁, 需结合品种体型与发育状态判断")
        if size == "large":
            notes.append("大型犬发育慢, 不能与小型犬套同一标准")
    else:
        level = "月龄已达参考口径"
        notes.append("月龄已过常见参考区间, 但仍须结合体型与体重")
    if size == "large":
        notes.append("大型犬与小型犬差异极大, 不可套用统一月龄标准")
    notes.append("最终由兽医面诊判断, 本工具不做手术适宜性结论")
    return level, notes


def schedule_of(days):
    d = int(days or 0)
    for lo, hi, name, focus in SCHEDULE:
        if d < hi or hi == 99999:
            return name, focus, (d < lo)
    return SCHEDULE[-1][2], SCHEDULE[-1][3], True


def readiness_score(flags):
    hit = [f for f in (flags or []) if f in dict((k, 1) for k, _, _ in RED_FLAGS)]
    if not hit:
        return 0, "未命中就医红线, 可按日程推进"
    if any(f in EMERGENCY for f in hit):
        return 3, "命中急诊项, 立即就医"
    if len(hit) >= 3:
        return 2, "命中多项红线, 尽快就医"
    return 1, "命中红线项, 按红线处置"


def build_report(data):
    species = (data.get("species", "cat") or "cat").strip()
    age = data.get("age_months", 0)
    weight = data.get("weight_kg", 0)
    size = (data.get("breed_size", "medium") or "medium").strip()
    in_heat = bool(data.get("in_heat", False))
    pregnant = bool(data.get("pregnant", False))
    preop = data.get("preop_done", []) or []
    red = data.get("red_flags", []) or []
    post_sym = data.get("postop_symptoms", []) or []
    days = data.get("days_after", 0)
    cat_intact = data.get("cat_intact", None)

    lines = []
    summary = {
        "red_flag_hit": None, "emergency": [], "readiness": None,
        "preop_missing": [], "window_level": None, "current_task": None,
        "symptoms": [], "medication_provided": False,
    }

    lines.append("=" * 68)
    lines.append("犬猫绝育术前术后核查")
    lines.append("=" * 68)
    lines.append("  本工具不给药物名称与剂量, 不判断手术适宜性。")
    lines.append("")

    lines.append("[一] 就医红线核对")
    lines.append("-" * 68)
    hits = [f for f in (red or []) if f in dict((k, 1) for k, _, _ in RED_FLAGS)]
    if hits:
        summary["red_flag_hit"] = True
        for f in hits:
            name, text, level = _red_text(f)
            lines.append("  [%s] %s" % (level, text))
            if f in EMERGENCY:
                summary["emergency"].append(f)
    else:
        summary["red_flag_hit"] = False
        lines.append("  未命中就医红线")
    lv, advice = readiness_score(red)
    summary["readiness"] = lv
    lines.append("  结论: %s" % advice)
    lines.append("")
    lines.append("  红线一览 (共 %d 条):" % len(RED_FLAGS))
    for k, text, level in RED_FLAGS:
        lines.append("    %-16s %-8s %s" % (k, level, text))
    lines.append("")

    lines.append("[二] 术前检查项核实")
    lines.append("-" * 68)
    done = set(preop or [])
    missing = []
    for k, name, check, meaning in PREOP:
        ok = k in done
        if not ok:
            missing.append(name)
        lines.append("  [%s] %s" % ("已确认" if ok else "未确认", name))
        lines.append("    核对: %s" % check)
        lines.append("    异常意义: %s" % meaning)
    summary["preop_missing"] = missing
    lines.append("")
    lines.append("  未确认项: %s" % ("、".join(missing) if missing else "无"))
    lines.append("  两条硬要求:")
    lines.append("    既往病史与长期用药必须如实告知, 隐瞒会直接影响麻醉方案")
    lines.append("    检查结果要拿到手, 不能只听一句看着还行")
    lines.append("")

    lines.append("[三] 年龄体重与时机")
    lines.append("-" * 68)
    sp = "犬" if species == "dog" else "猫"
    sz = SIZES.get(size, "中型")
    lines.append("  物种: %s   体型: %s   月龄: %g   体重: %g kg" % (
        sp, sz, float(age or 0), float(weight or 0)))
    lvl, notes = window_judge(age, size, species)
    summary["window_level"] = lvl
    lines.append("  窗口判定: %s" % lvl)
    for n in notes:
        lines.append("    - %s" % n)
    lines.append("")
    lines.append("  时机核对:")
    lines.append("    [%s] 处于发情期" % ("是" if in_heat else "否"))
    if in_heat:
        lines.append("      发情期子宫与血管充血明显, 出血风险上升, 应避开")
    lines.append("    [%s] 妊娠状态" % ("是" if pregnant else "否/未确认"))
    if pregnant:
        lines.append("      妊娠状态须由兽医评估, 不属于常规择期安排")
    lines.append("    发情结束后的具体间隔由兽医按品种与个体判断, 本工具不给固定天数")
    lines.append("")

    lines.append("[四] 术后日程 (术后第 %d 天)" % int(days or 0))
    lines.append("-" * 68)
    sname, sfocus, spassed = schedule_of(days)
    summary["current_task"] = sname
    lines.append("  当前节点: %s" % sname)
    lines.append("    关注: %s" % sfocus)
    lines.append("")
    lines.append("  日程表:")
    for lo, hi, name, focus in SCHEDULE:
        mark = "<<" if name == sname else "  "
        lines.append("   %s %-12s %s" % (mark, name, focus))
    lines.append("")
    lines.append("  活动限制:")
    lines.append("    猫: 术后限制跳跃攀爬, 尤其母猫; 限制进入高处")
    lines.append("    狗: 限制奔跑, 跳跃, 上下沙发与楼梯; 外出全程牵引")
    lines.append("    时长: 切口完全愈合前, 按医嘱; 逐步恢复, 不一步到位")
    lines.append("  饮食口径:")
    lines.append("    禁食禁水时长按医嘱执行, 不自行延长也不自行缩短")
    lines.append("    术后早期是否流质或软食按医嘱; 恢复后逐步过渡")
    lines.append("    绝育后代谢率下降, 需按月监测体重并相应调整喂食量; 不额外加餐")
    lines.append("  伊丽莎白圈:")
    lines.append("    舔咬风险高或医生明确要求时佩戴; 佩戴期间完全不进食需及时联系医生")
    lines.append("    佩戴时长按医嘱, 愈合前不取")
    lines.append("")

    lines.append("[五] 术后并发症排查")
    lines.append("-" * 68)
    if not post_sym:
        lines.append("  未报告术后并发症")
        lines.append("  逐日记录: 体温, 精神, 饮水, 排尿, 进食, 呕吐, 切口渗液, 活动")
    for s in post_sym:
        s = s.strip()
        if not s:
            continue
        if s in COMPLICATIONS:
            name, signal, action = COMPLICATIONS[s]
            lines.append("  [%s] %s" % (name, s))
            lines.append("    识别信号: %s" % signal)
            lines.append("    处置: %s" % action)
            summary["symptoms"].append(name)
        else:
            lines.append("  [未登记] %s -> 需人工比对并发症表" % s)
    lines.append("")
    lines.append("  粘连为什么容易被忽略: 不红, 不肿, 不化脓, 只是硬结与牵拉感")
    lines.append("    发现牵拉感就应该就诊, 不要以为过几个月就好了")
    lines.append("")
    if cat_intact is True:
        lines.append("  公猫尿闭识别五条:")
        lines.append("    频繁进猫砂盆; 猫砂盆里几乎无尿; 频繁舔下体")
        lines.append("    龟头长时间露在包皮外; 叫声异常, 躲藏, 食欲下降")
        lines.append("    任一条出现立即就医, 尿闭拖延会危及生命")
    lines.append("")

    lines.append("免责: 本结果为围手术期自查, 不构成手术适宜性结论或用药方案。")
    lines.append("免责: 手术与麻醉决策以执业兽医判断为准; 用药遵医嘱。")
    lines.append("=" * 68)
    return "\n".join(lines), summary


def _red_text(key):
    for k, text, level in RED_FLAGS:
        if k == key:
            return k, text, level
    return key, "未登记", "尽快就医"


def load_json(path):
    with io.open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    # PowerShell 写出的 UTF-8 文件可能带 BOM, 不剥掉会让首个 key 取不到值且不报错
    raw = raw.lstrip("\ufeff")
    return json.loads(raw)


def _run_checks():
    r = []
    r.append(("红线共 14 条", len(RED_FLAGS) == 14))
    r.append(("术前检查 11 项", len(PREOP) == 11))
    r.append(("并发症 10 类", len(COMPLICATIONS) == 10))
    r.append(("术后日程 7 节点", len(SCHEDULE) == 7))
    r.append(("急诊项 3 条", len(EMERGENCY) == 3))
    r.append(("尿闭为急诊项", "anuria_male" in EMERGENCY))
    r.append(("切口裂开为急诊项", "wound_dehiscence" in EMERGENCY))

    r.append(("月龄 3 为过小", window_judge(3, "medium", "cat")[0] == "过小"))
    r.append(("月龄 9 为需评估", window_judge(9, "medium", "cat")[0] == "需评估"))
    r.append(("月龄 24 为已过参考区间",
              window_judge(24, "medium", "cat")[0] == "月龄已达参考口径"))
    r.append(("大型犬必提示不可套统一标准",
              any("不可套用统一月龄标准" in n for n in window_judge(12, "large", "dog")[1])))
    r.append(("小型犬月龄 9 有幼犬提示",
              any("不能与小型犬套同一标准" in n
                  for n in window_judge(9, "large", "dog")[1])))
    r.append(("窗口结论含须兽医评估",
              any("最终由兽医面诊判断" in n for n in window_judge(24, "small", "dog")[1])))

    r.append(("术后 0 天为当天", schedule_of(0)[0] == "术后当天"))
    r.append(("术后 2 天为 1-2 天", schedule_of(2)[0] == "术后 1-2 天"))
    r.append(("术后 5 天为 3-5 天", schedule_of(5)[0] == "术后 3-5 天"))
    r.append(("术后 7 天为拆线节点", schedule_of(7)[0] == "术后 7 天"))
    r.append(("术后 20 天为 1 个月", schedule_of(20)[0] == "术后 1 个月"))
    r.append(("术后 60 天为长期", schedule_of(60)[0] == "长期"))

    r.append(("无红线为 0 级", readiness_score([])[0] == 0))
    r.append(("一项红线为 1 级",
              readiness_score(["bleeding_on"])[0] == 1))
    r.append(("急诊项为 3 级",
              readiness_score(["anuria_male"])[0] == 3))
    r.append(("三项有效红线为 2 级",
              readiness_score(["bleeding_on", "purulent", "distension"])[0] == 2))
    r.append(("未登记红线不计入",
              readiness_score(["bleeding_on", "fever", "nope"])[0] == 1))
    r.append(("未知红线被忽略",
              readiness_score(["no_such_flag"])[0] == 0))

    r.append(("尿闭处置为急症",
              "立即就医" in COMPLICATIONS["anuria"][2]))
    r.append(("粘连处置含就诊",
              "需就诊评估" in COMPLICATIONS["adhesion"][2]))
    r.append(("切口裂开禁止自行按压",
              "不自行按压" in COMPLICATIONS["dehiscence"][2]))
    r.append(("感染禁止自行涂药膏",
              "不自行涂抹任何药膏" in COMPLICATIONS["infection"][2]))

    txt, s = build_report({
        "species": "cat", "age_months": 24, "weight_kg": 4.5,
        "breed_size": "medium", "in_heat": False, "pregnant": False,
        "preop_done": ["temperature", "cbc", "biochem", "history"],
        "red_flags": ["anuria_male"],
        "postop_symptoms": ["adhesion"],
        "days_after": 3, "cat_intact": True,
    })
    r.append(("样例命中红线", s["red_flag_hit"] is True))
    r.append(("样例含急诊项", s["emergency"] == ["anuria_male"]))
    r.append(("样例就绪为 3 级", s["readiness"] == 3))
    r.append(("样例窗口达标", s["window_level"] == "月龄已达参考口径"))
    r.append(("样例缺 7 项检查", len(s["preop_missing"]) == 7))
    r.append(("样例节点为 3-5 天", s["current_task"] == "术后 3-5 天"))
    r.append(("样例记录粘连", s["symptoms"] == ["粘连"]))
    r.append(("样例不给药物", s["medication_provided"] is False))
    r.append(("样例文本含尿闭", "尿闭识别五条" in txt))

    _, s2 = build_report({})
    r.append(("空输入不报错", s2["red_flag_hit"] is False))
    r.append(("空输入缺全部 11 项", len(s2["preop_missing"]) == 11))
    r.append(("空输入无并发症", s2["symptoms"] == []))

    _, s3 = build_report({"preop_done": ["%s" % k for k, _, _, _ in PREOP],
                          "breed_size": "large", "age_months": 8})
    r.append(("全做完时缺项为空", s3["preop_missing"] == []))
    r.append(("大型犬 8 月为需评估", s3["window_level"] == "需评估"))

    r.append(("BOM 输入被正确剥离",
               load_json(_write_bom_sample())["species"] == "dog"))
    r.append(("字符串形式的并发症可解析",
               build_report({"postop_symptoms": ["fever"]})[1]["symptoms"] == ["发热"]))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"species\": \"dog\", \"age_months\": 12}")
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
    parser = argparse.ArgumentParser(description="犬猫绝育术前术后核查工具")
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
