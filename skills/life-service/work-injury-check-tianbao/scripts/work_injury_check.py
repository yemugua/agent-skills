# -*- coding: utf-8 -*-
"""工伤认定与赔偿核查。

输入：templates/工伤认定信息采集表.md 填好的表单（字段：值 或 两列表）。
输出：结构化核查报告（认定情形判断 / 时效 / 赔偿估算 / 待办补正 / 风险提示 / 边界）。
"""
import sys, os, re

REQ = [
    ("受伤时间", "inj_time"), ("受伤地点", "inj_place"), ("受伤原因", "inj_cause"),
    ("是否工作时间", "at_work"), ("是否工作场所", "at_place"),
    ("是否工作原因", "by_work"), ("是否上下班途中", "commuting"),
    ("是否交通事故", "traffic"), ("是否非本人主要责任", "not_main_fault"),
    ("劳动关系证明", "labor_proof"), ("用人单位是否参保", "insured"),
    ("是否已申请认定", "applied"), ("申请距受伤天数", "days_since"),
    ("伤残等级", "grade"), ("本人工资(月)", "salary"), ("停工留薪期(月)", "leave_months"),
]

# 一次性伤残补助金对应月数（工伤保险条例第三十五条/三十六/三十七条）
GRADE_MONTHS = {1: 27, 2: 25, 3: 23, 4: 21, 5: 18, 6: 16, 7: 13, 8: 11, 9: 9, 10: 7}
# 1-4 级伤残津贴占本人工资比例
GRADE_ALLOWANCE = {1: 0.90, 2: 0.85, 3: 0.80, 4: 0.75}


def get_text(fs, key):
    return (fs.get(key) or "").strip()


def parse_md(text):
    fs = {}
    for line in text.splitlines():
        m = re.match(r"^\s*([\u4e00-\u9fa5A-Za-z0-9（）()／/ ]+?)\s*[:：]\s*(.*)$", line)
        if m:
            fs[m.group(1).strip()] = m.group(2).strip()
    return fs


def yes(s):
    # 仅当含明确肯定词才算"是"，中性或否定文本一律视为否
    return any(w in s for w in ("是", "有", "已", "符合", "属于", "属"))


def judge(fs):
    """返回 (认定判断, 风险点列表, 待办列表, 赔偿估算dict)。"""
    risks = []
    todos = []
    est = {}

    missing = [k for k, _ in REQ if not get_text(fs, k)]
    if missing:
        risks.append("缺字段：" + "、".join(missing))
        todos.append("补全缺失字段：" + "、".join(missing))

    at_work = yes(get_text(fs, "是否工作时间"))
    at_place = yes(get_text(fs, "是否工作场所"))
    by_work = yes(get_text(fs, "是否工作原因"))
    commuting = yes(get_text(fs, "是否上下班途中"))
    traffic = yes(get_text(fs, "是否交通事故"))
    not_fault = yes(get_text(fs, "是否非本人主要责任"))

    # 工伤认定情形判断
    qualifies = False
    reason = ""
    if at_work and at_place and by_work:
        qualifies = True
        reason = "工作时间、工作场所内因工作原因受伤害（条例第十四条第一项）"
    elif commuting and traffic and not_fault:
        qualifies = True
        reason = "上下班途中受非本人主要责任的交通事故伤害（条例第十四条第六项）"
    elif commuting and not traffic:
        risks.append("上下班途中但非交通事故，通常不属于工伤认定情形（除非法规特别规定）")
    elif commuting and traffic and not not_fault:
        risks.append("上下班途中交通事故但本人负主要责任，不符合工伤认定情形")
        todos.append("确认交管部门出具的事故责任认定书责任划分")

    if not (at_work or commuting):
        risks.append("未体现工作时间/场所或上下班途中，认定情形存疑")
        todos.append("补充受伤时的具体情境说明（时间、地点、与工作的关联）")

    # 排除情形（第十六条）简单提示
    cause = get_text(fs, "受伤原因")
    if any(w in cause for w in ("醉酒", "吸毒", "故意", "自残", "犯罪")):
        qualifies = False
        risks.append("受伤原因含醉酒/吸毒/故意犯罪/自残等排除情形（条例第十六条），极可能不予认定")
        todos.append("核实受伤真实原因，排除法定排除情形")

    # 时效判断
    applied = yes(get_text(fs, "是否已申请认定"))
    ds = get_text(fs, "申请距受伤天数")
    m = re.search(r"(\d+)", ds)
    days = int(m.group(1)) if m else None
    if not applied:
        if days is not None and days > 365:
            risks.append("距受伤已超 1 年且未申请，超过劳动者申请时效红线")
            todos.append("尽快咨询当地人社部门是否仍有补救通道，超期可能丧失待遇")
        elif days is not None and days > 30:
            risks.append("单位 30 日申请期已过，劳动者/近亲属应在 1 年内直接申请")
            todos.append("由劳动者本人或近亲属在受伤之日起 1 年内向人社局申请认定")
        else:
            todos.append("单位应在 30 日内、或本人 1 年内向统筹地区人社局申请工伤认定")
    else:
        todos.append("已申请，保留受理回执并跟进认定结论（一般 60 日内作出）")

    # 证据收集
    if not yes(get_text(fs, "劳动关系证明")):
        risks.append("缺少劳动关系证明，认定前置障碍")
        todos.append("收集劳动合同、工资流水、社保记录、工牌、考勤、同事证言等证明劳动关系")
    if traffic and not yes(get_text(fs, "是否非本人主要责任")):
        todos.append("取得交管部门事故责任认定书（认定非本人主要责任的关键证据）")

    # 赔偿估算
    grade_s = get_text(fs, "伤残等级")
    salary_s = get_text(fs, "本人工资(月)")
    gm = re.search(r"(\d+)", grade_s)
    sm = re.search(r"(\d+(?:\.\d+)?)", salary_s.replace(",", ""))
    grade = int(gm.group(1)) if gm else None
    salary = float(sm.group(1)) if sm else None
    if grade and salary:
        if 1 <= grade <= 10:
            months = GRADE_MONTHS[grade]
            est["一次性伤残补助金"] = round(salary * months, 2)
            est["计算口径"] = "本人工资 × %d 个月（条例第三十七条）" % months
            if 1 <= grade <= 4:
                est["按月伤残津贴"] = round(salary * GRADE_ALLOWANCE[grade], 2)
                est["津贴口径"] = "本人工资 × %.0f%%（按月，基金支付，条例第三十五条）" % (GRADE_ALLOWANCE[grade] * 100)
            if 5 <= grade <= 6:
                todos.append("5–6 级保留劳动关系，难以安排工作时由单位发伤残津贴（本人工资 70%/60%）")
            if 7 <= grade <= 10:
                todos.append("7–10 级合同终止/解除时可领一次性医疗补助金+就业补助金（标准按省规定）")
        else:
            risks.append("伤残等级填写超出 1–10 范围")
    leave_s = get_text(fs, "停工留薪期(月)")
    lm = re.search(r"(\d+(?:\.\d+)?)", leave_s)
    if lm and salary:
        leave = float(lm.group(1))
        est["停工留薪期工资"] = round(salary * min(leave, 12), 2)
        est["停工留薪口径"] = "原工资福利 × 不超过 12 个月（条例第三十三条）"
    if not yes(get_text(fs, "用人单位是否参保")):
        risks.append("用人单位未参保，法定工伤待遇由单位全额承担（仍可主张）")
        todos.append("向单位主张全部工伤待遇；拒不支付可申请劳动仲裁")

    if qualifies and not any("极可能不予认定" in r for r in risks):
        concl = "高度可能认定为工伤"
    elif qualifies:
        concl = "情形符合但存在排除/存疑点，需进一步核实"
    else:
        concl = "当前信息不足以认定工伤（请补正后重核）"
    return concl, reason, risks, todos, est


def main():
    if len(sys.argv) < 2:
        print("用法: work_injury_check.py <输入md>")
        return 2
    p = sys.argv[1]
    if not os.path.exists(p):
        print("文件不存在: %s" % p)
        return 2
    with open(p, encoding="utf-8") as f:
        text = f.read()
    fs = parse_md(text)
    filled = sum(1 for k, _ in REQ if get_text(fs, k))
    if filled == 0:
        print("# 工伤认定与赔偿核查报告\n\n## 结论摘要")
        print("认定判断：待补正（输入为空，未提供任何受伤信息）")
        print("\n## 边界与纪律")
        print("- 请提供至少一项受伤信息后再核查。")
        return 2
    concl, reason, risks, todos, est = judge(fs)
    print("# 工伤认定与赔偿核查报告\n")
    print("## 结论摘要")
    print("认定判断：%s" % concl)
    if reason:
        print("依据情形：%s" % reason)
    print("\n## 风险提示")
    if risks:
        for r in risks:
            print("- %s" % r)
    else:
        print("- 未发现明显排除情形（仍以人社部门认定为准）")
    print("\n## 法定赔偿估算（仅供参考）")
    if est:
        for k, v in est.items():
            if "口径" in k:
                print("- %s" % v)
            else:
                print("- %s：¥%s（约）" % (k, format(v, ",.2f")))
        print("- 另含：医疗费、住院伙食补助、护理费等据实结算项目（未估算）")
    else:
        print("- 信息不足，无法估算；请补全伤残等级与本人工资")
    print("\n## 待办补正动作")
    if todos:
        for t in todos:
            print("- %s" % t)
    else:
        print("- 无")
    print("\n## 边界与纪律")
    print("- 本技能不替代工伤认定机构结论，最终以人社局认定及司法裁判为准。")
    print("- 各省一次性医疗/就业补助金等标准不同，估算时已单独标注。")
    print("- 不提供法律代理，不承诺认定或赔偿结果。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
