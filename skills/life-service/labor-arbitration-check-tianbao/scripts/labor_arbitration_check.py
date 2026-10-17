# -*- coding: utf-8 -*-
"""劳动仲裁维权核查。

输入：templates/劳动仲裁信息采集表.md 填好的表单（字段：值 或 两列表）。
输出：结构化核查报告（受理范围 / 时效 / 权益估算 / 待办补正 / 风险提示 / 边界）。
"""
import sys, os, re

REQ = [
    ("争议类型", "dtype"), ("入职时间", "entry"), ("离职时间", "leave"),
    ("工作年限(年)", "years"), ("月工资(元)", "salary"),
    ("是否已签劳动合同", "signed"), ("是否缴纳社保", "social"),
    ("解除方式", "terminate"), ("是否出具解除通知", "notice"),
    ("欠薪金额(元)", "arrears"), ("平时加班(小时)", "ot_normal"),
    ("周末加班(小时)", "ot_weekend"), ("法定假日加班(小时)", "ot_holiday"),
    ("证据情况", "evidence"), ("申请仲裁距侵权天数", "days"),
]

# 解除方式分类
TERM_ILLEGAL = ("违法", "单方解除", "无故", "开除", "辞退且无")
TERM_NOPAY = ("协商", "合同到期", "期满", "客观情况", "不续签")
TERM_QUIT = ("主动辞职", "个人原因", "自离", "辞职")


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
    return any(w in s for w in ("是", "有", "已", "签", "缴", "交", "符合", "属"))


def num(s):
    m = re.search(r"(\d+(?:\.\d+)?)", s.replace(",", ""))
    return float(m.group(1)) if m else None


def comp_months(years):
    """经济补偿金 N 月数：满年按年计，余≥6月算1月，余>0且<6月算0.5月。"""
    if years is None:
        return None
    full = int(years)
    rem = years - full
    if rem >= 0.5:
        add = 1
    elif rem > 0:
        add = 0.5
    else:
        add = 0
    return full + add


def judge(fs):
    risks = []
    todos = []
    est = {}
    missing = [k for k, _ in REQ if not get_text(fs, k)]
    if missing:
        risks.append("缺字段：" + "、".join(missing))
        todos.append("补全缺失字段：" + "、".join(missing))

    dtype = get_text(fs, "争议类型")
    ACCEPT = ("辞退", "解除", "欠薪", "工资", "加班", "社保", "工伤", "合同", "劳动关系", "年假", "竞业", "赔偿")
    in_scope = any(w in dtype for w in ACCEPT)
    if dtype and not in_scope:
        risks.append("争议类型可能不属于仲裁受理范围，需进一步判断")
        todos.append("核实是否属于劳动争议调解仲裁法第二条列明的受理情形")
    elif not dtype:
        risks.append("未填争议类型，受理范围存疑")

    # 时效
    days = num(get_text(fs, "申请仲裁距侵权天数"))
    applied = get_text(fs, "申请仲裁距侵权天数")
    if days is not None and days > 365:
        risks.append("距权利受侵害已超 1 年仲裁时效，存在被驳回风险")
        todos.append("尽快申请仲裁；如存在时效中断/中止事由（曾主张权利等）需举证")
    else:
        todos.append("自知道权利受侵害之日起 1 年内向劳动合同履行地或单位所在地仲裁委申请")

    # 年限与工资
    years = num(get_text(fs, "工作年限(年)"))
    salary = num(get_text(fs, "月工资(元)"))
    n = comp_months(years) if years is not None else None

    terminate = get_text(fs, "解除方式")
    if terminate and salary and n is not None:
        if any(w in terminate for w in TERM_ILLEGAL):
            est["违法解除赔偿金(2N)"] = round(salary * 2 * n, 2)
            est["2N口径"] = "月工资 × 2 × %s 个月（劳动合同法第八十七条）" % n
            est["对应经济补偿金(N)"] = round(salary * n, 2)
        elif any(w in terminate for w in TERM_NOPAY):
            est["经济补偿金(N)"] = round(salary * n, 2)
            est["N口径"] = "月工资 × %s 个月（劳动合同法第四十七条）" % n
        elif any(w in terminate for w in TERM_QUIT):
            todos.append("主动辞职一般无经济补偿金（除非单位存在法定过错）")
        else:
            todos.append("请明确解除方式以判断 N / 2N")
    elif salary is None:
        todos.append("补全月工资以估算赔偿")

    # 欠薪
    arrears = num(get_text(fs, "欠薪金额(元)"))
    if arrears is not None:
        est["欠薪主张"] = round(arrears, 2)
        todos.append("收集工资条、银行流水、欠条等证明欠薪金额")

    # 加班费
    oh = num(get_text(fs, "平时加班(小时)"))
    ow = num(get_text(fs, "周末加班(小时)"))
    ohd = num(get_text(fs, "法定假日加班(小时)"))
    if salary and (oh or ow or ohd):
        hourly = salary / 21.75 / 8
        total = 0.0
        parts = []
        if oh:
            total += oh * hourly * 1.5
            parts.append("平日%.0f小时×150%%" % oh)
        if ow:
            total += ow * hourly * 2.0
            parts.append("周末%.0f小时×200%%" % ow)
        if ohd:
            total += ohd * hourly * 3.0
            parts.append("法定%.0f小时×300%%" % ohd)
        est["加班费估算"] = round(total, 2)
        est["加班口径"] = "（%s），计薪基数=月工资/21.75/8" % "，".join(parts)
        todos.append("保留考勤记录、排班表、加班审批/聊天记录证明加班事实")

    # 未签合同二倍工资
    if not yes(get_text(fs, "是否已签劳动合同")) and salary and years:
        cap = min(11, int(years * 12) if years < 1 else 11)
        est["未签合同二倍工资差额"] = round(salary * cap, 2)
        est["二倍工资口径"] = "月工资 × %d 个月（最长 11 个月，劳动合同法第八十二条）" % cap
        todos.append("收集工资流水、工牌、考勤等证明事实劳动关系")

    # 社保
    if not yes(get_text(fs, "是否缴纳社保")):
        risks.append("单位未缴社保，可主张补缴（向社保稽核/劳动监察投诉）")
        todos.append("向社保经办机构或劳动监察投诉要求补缴；因此解除可主张 N")

    # 证据
    ev = get_text(fs, "证据情况")
    if not yes(ev):
        risks.append("缺少证据，仲裁举证困难")
        todos.append("收集：劳动合同、工资流水、社保记录、考勤、解除通知、聊天记录、录音等")

    if in_scope and not any("超 1 年" in r for r in risks):
        scope = "大概率属于仲裁受理范围"
    elif in_scope:
        scope = "属于受理范围但已超时效，需举证中断/中止"
    else:
        scope = "受理范围存疑，请补正争议类型后重核"
    return scope, risks, todos, est


def main():
    if len(sys.argv) < 2:
        print("用法: labor_arbitration_check.py <输入md>")
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
        print("# 劳动仲裁维权核查报告\n\n## 结论摘要")
        print("受理范围：待补正（输入为空，未提供任何争议信息）")
        print("\n## 边界与纪律")
        print("- 请提供至少一项争议信息后再核查。")
        return 2
    scope, risks, todos, est = judge(fs)
    print("# 劳动仲裁维权核查报告\n")
    print("## 结论摘要")
    print("受理范围：%s" % scope)
    print("\n## 风险提示")
    if risks:
        for r in risks:
            print("- %s" % r)
    else:
        print("- 未发现明显排除情形（仍以仲裁裁决为准）")
    print("\n## 法定权益估算（仅供参考）")
    if est:
        for k, v in est.items():
            if "口径" in k:
                print("- %s" % v)
            else:
                print("- %s：¥%s（约）" % (k, format(v, ",.2f")))
    else:
        print("- 信息不足，无法估算；请补全工资/年限/解除方式等")
    print("\n## 待办补正动作")
    if todos:
        for t in todos:
            print("- %s" % t)
    else:
        print("- 无")
    print("\n## 边界与纪律")
    print("- 本技能不替代仲裁委裁决，最终以仲裁裁决及法院裁判为准。")
    print("- 不提供法律代理，不承诺仲裁或胜诉结果。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
