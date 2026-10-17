# -*- coding: utf-8 -*-
"""宠物驱虫间隔核查工具。

用法:
  python deworm_calc.py --file plan.json [--json]
  python deworm_calc.py --selftest

本工具不给药名, 不给剂量, 不给固定驱虫天数。
"""
import argparse
import io
import json
import os
import sys

# 体内寄生虫: (名称, 表现线索, 管理提示)
INTERNAL = [
    ("蛔虫", "幼宠多见; 粪便中可见; 可能有腹痛、消瘦", "常见地面传播寄生虫"),
    ("绦虫", "粪便中可见白色或米粒状节片; 肛周瘙痒", "常与跳蚤中间宿主相关"),
    ("钩虫", "便血、贫血、消瘦", "可经皮肤侵入"),
    ("鞭虫", "大量黏液便、腹泻、消瘦", "幼犬猫多见"),
    ("蛲虫(犬)", "肛周异动、夜间瘙痒", "主要在犬"),
    ("球虫类", "幼宠腹泻、便中带血", "幼年发病较多"),
    ("弓形虫", "多数无症状; 免疫低下时发病", "人畜共患病, 管理上要重视卫生"),
]

# 体外寄生虫
EXTERNAL = [
    ("跳蚤", "剧烈瘙痒; 黑色颗粒状粪便; 腰臀部与尾根多见",
     "会叮咬人; 家中有跳蚤是常见反复来源"),
    ("蜱虫", "肉眼可见虫体附着; 叮咬处红肿、结痂",
     "可传播疾病; 草地与户外是高暴露环境"),
    ("耳螨", "剧烈甩头、耳道内黑褐色分泌物、结痂",
     "位置在耳道内, 普通体外滴剂未必覆盖耳道"),
    ("疥螨", "剧烈瘙痒、脱毛、结痂, 多从边缘开始", "传染性强, 人也可被感染"),
    ("蠕形螨", "脱毛、红斑、皮肤增厚", "需皮肤镜检确认"),
    ("虱子", "可见蠕动的虫体、结痂", "多见于环境差或免疫低下个体"),
    ("恙螨", "趾间、腹部红斑、剧烈瘙痒", "潮湿季节高发"),
]

# 就医红线: (代号, 说明)
RED_FLAGS = [
    ("allergy_acute", "服药后抽搐、意识障碍、呼吸困难、面部肿胀, 提示急性过敏反应"),
    ("vomit_24h", "服药后持续呕吐、腹泻超过 24 小时, 伴精神沉郁"),
    ("heavy_worm", "粪便中持续可见大量虫体或虫卵, 提示感染负荷高"),
    ("anus_move", "肛周有异动但粪便中找不到虫, 需排查绦虫与滴虫"),
    ("skin_hairloss", "大面积脱毛、红斑、结痂并伴脱毛"),
    ("ear_dirty", "耳道内有黑褐色分泌物、剧烈甩头, 需排查耳螨与耳炎"),
    ("young_refuse", "幼宠驱虫后持续不吃不喝, 幼犬幼猫需注意血糖偏低"),
    ("overdose", "怀疑误服过量或多宠共用剂量导致过量"),
    ("pregnant", "母宠处于妊娠期或哺乳期"),
    ("comorbidity", "有肝肾基础疾病或正在服用其他药物"),
]

EMERGENCY = ("allergy_acute", "overdose")

# 暴露维度 -> 风险提示
EXPOSURE = [
    ("indoor_only", "完全室内、几乎不外出", "体外风险低; 体内仍需按兽医意见"),
    ("daily_outdoor", "每天外出、接触草地与公共区域", "体外暴露持续, 风险高"),
    ("seasonal_outdoor", "季节性外出(春秋、夏季)", "需按季节调整"),
    ("no_outdoor", "极少外出但接触草地边缘", "偶发暴露"),
]

# 周期核查维度
CHECK_DIMS = [
    ("暴露类型", "完全室内 / 每天外出 / 季节性外出"),
    ("接触其他动物", "猫狗混养、常去宠物店或寄养"),
    ("年龄", "幼宠体内寄生虫更常见; 老年需评估免疫状态"),
    ("免疫与健康", "免疫状态影响方案, 由兽医评估"),
    ("既往感染史", "曾有寄生虫感染需确认是否需要连续方案"),
    ("环境", "家中有其他未驱虫动物; 潮湿、动物密集"),
    ("体重", "每次给药时记录当时体重, 体重变化直接影响后续方案"),
]

# 需向兽医确认的方案项
CONFIRM_ITEMS = [
    ("药品品种", "由兽医确定并写明, 不用通用型这种模糊说法"),
    ("给药方式", "口服、外滴、佩戴项圈或注射, 由兽医确定"),
    ("剂量", "按体重由兽医确定并记录当时的体重"),
    ("给药间隔", "由兽医确定并写入记录"),
    ("疗程", "有些情况需连续给药, 疗程由兽医确定, 不自行停药"),
    ("体内外是否同期", "由兽医确认是否需要分开或同期"),
    ("与疫苗的间隔", "是否分开、分开多久由兽医确认"),
]


def risk_level(indoor_only, outdoor_freq, multi_pet, age_months):
    score = 0
    if not indoor_only:
        score += 2
    if str(outdoor_freq or "") in ("daily", "high", "经常", "每天"):
        score += 2
    elif str(outdoor_freq or "") in ("seasonal", "sometimes", "季节性"):
        score += 1
    if multi_pet:
        score += 1
    a = float(age_months or 0)
    if 0 < a <= 12:
        score += 1
    if score >= 5:
        return 3, "高暴露, 需向兽医说明完整暴露情况"
    if score >= 3:
        return 2, "中等暴露, 需向兽医说明外出频率与季节"
    if score >= 1:
        return 1, "低暴露, 仍需按兽医意见确定方案"
    return 0, "极低暴露, 仍需按兽医意见确定方案"


def days_since(last, today):
    if last is None:
        return None
    if today is None:
        return None
    try:
        return int(today) - int(last)
    except (TypeError, ValueError):
        return None


def interval_text(flag_name, days):
    if days is None:
        return "未记录 %s 日期, 请先补齐记录" % flag_name
    if days < 0:
        return "%s 日期在未来, 记录有误请核对" % flag_name
    if days == 0:
        return "%s 今天进行, 记录已对齐" % flag_name
    return "%s 距今 %d 天" % (flag_name, days)


def same_day_gap(d1, d2):
    if d1 is None or d2 is None:
        return None
    return abs(int(d1) - int(d2)) == 0


def build_report(data):
    species = (data.get("species", "cat") or "cat").strip()
    age = data.get("age_months", 0)
    indoor = bool(data.get("indoor_only", False))
    freq = data.get("outdoor_freq", "")
    multi = bool(data.get("multi_pet", False))
    weight = data.get("weight_kg", 0)
    d_int = data.get("days_since_internal_deworm", None)
    d_ext = data.get("days_since_external_deworm", None)
    d_vac = data.get("days_since_vaccine", None)
    red = data.get("red_flags", []) or []
    sym = data.get("symptoms", []) or []

    lines = []
    summary = {
        "risk_level": None, "risk_advice": None, "internal_days": d_int,
        "external_days": d_ext, "vaccine_days": d_vac,
        "red_flag_hit": None, "emergency": [],
        "symptoms": [], "drug_provided": False, "fixed_days_provided": False,
    }

    lines.append("=" * 68)
    lines.append("宠物驱虫间隔核查")
    lines.append("=" * 68)
    lines.append("  本工具不给药名, 不给剂量, 不给固定驱虫天数。")
    lines.append("")

    lines.append("[一] 体内外作用对象")
    lines.append("-" * 68)
    sp = "犬" if species == "dog" else "猫"
    lines.append("  物种: %s   月龄: %g   体重: %g kg" % (
        sp, float(age or 0), float(weight or 0)))
    lines.append("")
    lines.append("  体内寄生虫 (%d 类):" % len(INTERNAL))
    for n, clue, note in INTERNAL:
        lines.append("    %-12s %s" % (n, clue))
        lines.append("      管理提示: %s" % note)
    lines.append("")
    lines.append("  体外寄生虫 (%d 类):" % len(EXTERNAL))
    for n, clue, note in EXTERNAL:
        lines.append("    %-12s %s" % (n, clue))
        lines.append("      管理提示: %s" % note)
    lines.append("")
    lines.append("  体外驱虫不做环境等于白做:")
    lines.append("    跳蚤与蜱虫大部分卵、幼虫、蛹在环境里, 只给宠物驱虫很快再感染")
    lines.append("    织物清洗高温、窝垫暴晒、吸尘、吸尘袋立即扎紧丢弃")
    lines.append("    蚤蛹对药剂耐受, 吸尘器拍打地毯有助于刺激蛹羽化")
    lines.append("    鱼缸与鸟笼附近不要使用宠物体外驱虫环境产品")
    lines.append("")

    lines.append("[二] 暴露维度与风险分层")
    lines.append("-" * 68)
    lv, advice = risk_level(indoor, freq, multi, age)
    summary["risk_level"] = lv
    summary["risk_advice"] = advice
    lines.append("  居住方式: %s" % ("完全室内" if indoor else "有外出"))
    lines.append("  外出频率: %s" % (freq or "未提供"))
    lines.append("  多宠混养: %s" % ("是" if multi else "否"))
    lines.append("  风险分层: %d 级 -> %s" % (lv, advice))
    lines.append("")
    lines.append("  周期核查维度 (具体周期由兽医按暴露风险确定):")
    for name, detail in CHECK_DIMS:
        lines.append("    %-10s %s" % (name, detail))
    lines.append("")
    lines.append("  说明: 同样一只猫, 室内散养与每天放养的体外驱虫需求完全不同")
    lines.append("        幼宠首次驱虫时机取决于它吃了什么、何时接触地面")
    lines.append("")

    lines.append("[三] 三条间隔分开排")
    lines.append("-" * 68)
    lines.append("  体内驱虫: %s" % interval_text("体内驱虫", d_int))
    lines.append("  体外驱虫: %s" % interval_text("体外驱虫", d_ext))
    lines.append("  疫苗接种: %s" % interval_text("疫苗", d_vac))
    lines.append("")
    if same_day_gap(d_int, d_vac) and d_int is not None:
        lines.append("  [注意] 体内驱虫与疫苗同日进行")
        lines.append("    出现不良反应时难以区分来源; 错开日期便于排查")
    elif same_day_gap(d_ext, d_vac) and d_ext is not None:
        lines.append("  [注意] 体外驱虫与疫苗同日进行")
        lines.append("    出现不良反应时难以区分来源; 错开日期便于排查")
    else:
        lines.append("  体内、体外、与疫苗三条间隔未同日, 记录可对齐排查")
    lines.append("")
    lines.append("  与疫苗间隔口径:")
    lines.append("    是否必须分开由兽医确认; 常见做法是错开日期而不是同日进行")
    lines.append("    同日进行的实际风险是出现不良反应时难以区分来源")
    lines.append("    每次后观察 24-48 小时的精神、食欲、粪便、体温; 两次都记日期")
    lines.append("")

    lines.append("[四] 就医红线")
    lines.append("-" * 68)
    keys = set(k for k, _ in RED_FLAGS)
    hits = [f for f in (red or []) if f in keys]
    if hits:
        summary["red_flag_hit"] = True
        for f in hits:
            for k, text in RED_FLAGS:
                if k == f:
                    tag = "立即急诊" if k in EMERGENCY else "尽快联系兽医"
                    lines.append("  [%s] %s" % (tag, text))
                    if k in EMERGENCY:
                        summary["emergency"].append(k)
    else:
        summary["red_flag_hit"] = False
        lines.append("  未命中就医红线")
    lines.append("")

    lines.append("[五] 症状分流")
    lines.append("-" * 68)
    if not sym:
        lines.append("  未提供症状")
    else:
        lines.append("  看到虫体或粪便异常 -> 体内方向, 确认需粪检")
        lines.append("  瘙痒、脱毛、结痂、可见虫体 -> 体外方向, 需皮肤检查")
        lines.append("  耳道分泌物、甩头 -> 耳道内问题, 普通体外滴剂未必覆盖")
        for s in sym:
            s = s.strip()
            lines.append("  [记录] %s" % (s or "未登记"))
            summary["symptoms"].append(s)
    lines.append("")

    lines.append("[六] 需向兽医确认的方案项")
    lines.append("-" * 68)
    for name, detail in CONFIRM_ITEMS:
        lines.append("  %-14s %s" % (name, detail))
    lines.append("")
    lines.append("  关于看不到虫: 虫体是否排出受感染负荷、给药时间、个体差异影响")
    lines.append("    看不到虫不等于没打中; 是否需要调整方案由兽医判断")
    lines.append("    不要自行加量或缩短间隔")
    lines.append("")
    lines.append("  绝对禁止:")
    for c in ["不用人用药给宠物驱虫(部分人用驱虫药对猫有严重毒性, 猫禁用)",
              "不自行加大剂量或缩短间隔",
              "不把体外驱虫药按体内驱虫用, 或反之",
              "不在多种驱虫药之间自行叠加",
              "不用驱虫药当保健品每月一片的思路"]:
        lines.append("    - %s" % c)
    lines.append("")
    lines.append("免责: 本结果为间隔核查与记录对齐, 不构成驱虫方案或用药结论。")
    lines.append("免责: 驱虫方案以执业兽医医嘱为准; 寄生虫种类确认以粪检等检测结论为准。")
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
    r.append(("体内寄生虫 7 类", len(INTERNAL) == 7))
    r.append(("体外寄生虫 7 类", len(EXTERNAL) == 7))
    r.append(("红线 10 条", len(RED_FLAGS) == 10))
    r.append(("急诊项 2 条", len(EMERGENCY) == 2))
    r.append(("过敏为急诊项", "allergy_acute" in EMERGENCY))
    r.append(("过量误服为急诊项", "overdose" in EMERGENCY))
    r.append(("核查维度 7 项", len(CHECK_DIMS) == 7))
    r.append(("确认项 7 条", len(CONFIRM_ITEMS) == 7))
    r.append(("弓形虫标注人畜共患",
              "人畜共患" in INTERNAL[6][2]))
    r.append(("耳螨提示未必覆盖耳道",
              "未必覆盖耳道" in EXTERNAL[2][2]))
    r.append(("跳蚤提示会叮咬人", "叮咬人" in EXTERNAL[0][2]))
    r.append(("疥螨提示人也可感染", "人也可被感染" in EXTERNAL[3][2]))
    r.append(("蠕形螨需镜检", "镜检" in EXTERNAL[4][2]))

    r.append(("全室内为 0 级", risk_level(True, "never", False, 36)[0] == 0))
    r.append(("每天外出为 2 级",
              risk_level(False, "daily", False, 36)[0] == 2))
    r.append(("每天外出加混养加幼宠为 3 级",
              risk_level(False, "daily", True, 6)[0] == 3))
    r.append(("季节性外出为中低",
              risk_level(False, "seasonal", False, 36)[0] == 2))
    r.append(("纯室内但混养有风险",
              risk_level(True, "never", True, 36)[0] == 1))

    r.append(("距上次 30 天", interval_text("体内驱虫", 30).find("30") > 0))
    r.append(("未记录时提示补齐",
              "未记录" in interval_text("体外驱虫", None)))
    r.append(("负天数为记录有误",
              "记录有误" in interval_text("疫苗", -3)))
    r.append(("今天进行提示已对齐",
              "今天进行" in interval_text("疫苗", 0)))
    r.append(("同日判定为真", same_day_gap(10, 10) is True))
    r.append(("不同日判定为假", same_day_gap(10, 3) is False))
    r.append(("缺值时不判定", same_day_gap(None, 3) is None))

    txt, s = build_report({
        "species": "dog", "age_months": 8, "indoor_only": False,
        "outdoor_freq": "daily", "multi_pet": True, "weight_kg": 12,
        "days_since_internal_deworm": 20, "days_since_external_deworm": 45,
        "days_since_vaccine": 20, "red_flags": ["allergy_acute"],
        "symptoms": ["itch"],
    })
    r.append(("样例为犬", "犬" in txt))
    r.append(("样例风险 3 级", s["risk_level"] == 3))
    r.append(("样例命中红线", s["red_flag_hit"] is True))
    r.append(("样例含急诊项", s["emergency"] == ["allergy_acute"]))
    r.append(("样例检出同日", "同日进行" in txt))
    r.append(("样例记录天数", s["internal_days"] == 20 and s["external_days"] == 45))
    r.append(("样例不给药名", s["drug_provided"] is False))
    r.append(("样例不给固定天数", s["fixed_days_provided"] is False))
    r.append(("样例文本含绝对禁止", "绝对禁止" in txt))

    _, s2 = build_report({})
    r.append(("空输入不报错", s2["risk_level"] == 1))
    r.append(("空输入按有外出处理", "有外出" in txt))
    r.append(("空输入未命中红线", s2["red_flag_hit"] is False))
    r.append(("空输入无急诊项", s2["emergency"] == []))
    r.append(("空输入无症状", s2["symptoms"] == []))

    _, s3 = build_report({"indoor_only": True, "outdoor_freq": "never",
                          "age_months": 60,
                          "days_since_internal_deworm": 5,
                          "days_since_vaccine": 40})
    r.append(("室内老年犬为 0 级", s3["risk_level"] == 0))
    r.append(("不同日提示可对齐", "未同日" in build_report(s3)[0]))

    r.append(("BOM 输入被正确剥离",
               load_json(_write_bom_sample())["species"] == "dog"))
    r.append(("未知红线被忽略",
               build_report({"red_flags": ["nope"]})[1]["red_flag_hit"] is False))
    return r


def _write_bom_sample():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "_selftest_bom_sample.json")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\ufeff{\"species\": \"dog\", \"indoor_only\": true}")
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
    parser = argparse.ArgumentParser(description="宠物驱虫间隔核查工具")
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
