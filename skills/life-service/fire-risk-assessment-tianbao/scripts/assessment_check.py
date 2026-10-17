# -*- coding: utf-8 -*-
"""消防安全评估报告核查。

用法:
  python assessment_check.py --file 评估报告.txt --as-of 2026-10-08
  python assessment_check.py --score 72 --date 2026-01-15
  python assessment_check.py --selftest
"""
import argparse
import datetime
import json
import os
import re
import sys

# ---- 14 项报告必备要素 ----
ELEMENTS = [
    ("基本情况", "单位名称|场所名称|建筑面积|使用性质|层数"),
    ("目的与依据", "评估依据|依据标准|GB|评估目的"),
    ("范围与边界", "评估范围|评估对象|不包含|本次评估"),
    ("评估日期与作业时长", "评估日期|现场检查日期|进场|工作时间"),
    ("方法与评估组", "评估方法|现场检查|功能测试|评估组|评估人员"),
    ("单元逐项记录", "评估单元|检查记录|检查表|分项"),
    ("扣分明细", "扣分|扣 \\d|分值|得分"),
    ("问题清单", "问题清单|存在问题|隐患清单|主要问题"),
    ("风险等级与分值", "综合得分|评估得分|风险等级|低风险|一般风险|较高风险|高风险"),
    ("直接判定项筛查", "直接判定|重大火灾隐患|停产停业|立即整改|拒不整改"),
    ("整改建议", "整改建议|整改措施|处理意见"),
    ("复核安排", "复核|复查|复检|跟踪"),
    ("签章与签字", "盖章|签章|签字|签署|技术负责人"),
    ("有效期与复评", "有效期|复评|下一次评估|再次评估"),
]

# ---- 九个一级评估单元 ----
UNITS = [
    ("消防安全合法性", 10, "合法性|消防验收|备案|投入使用|批准"),
    ("总平面布置", 10, "总平面|防火间距|消防车道|登高|回车场"),
    ("建筑防火与防火分隔", 15, "防火分区|防火分隔|防火门|防火卷帘|防火封堵|装修材料|燃烧性能"),
    ("安全疏散", 15, "安全出口|疏散通道|疏散楼梯|疏散宽度|疏散距离|避难"),
    ("消防设施设备", 20, "火灾自动报警|自动喷水|消火栓|防排烟|灭火器|联动"),
    ("电气防火", 8, "电气|配电|线路|过载|私拉乱接|用电"),
    ("消防安全管理", 12, "管理制度|责任制|值班|培训|演练|动火|台账|档案"),
    ("灭火救援能力", 5, "微型消防站|专职消防队|志愿消防|应急预案|处置"),
    ("既往隐患与动态危险源", 5, "上次评估|整改情况|遗留|危险源|动火作业|临时用电"),
]

# ---- 直接判定项（核心项标记 True）----
DIRECT_ITEMS = [
    ("擅自改变使用性质未办理手续", True, "擅自改变使用性质|擅自改建|改变用途未办理|擅自变更使用"),
    ("消防设施整体瘫痪或多处失效", True, "整体瘫痪|全部失效|大面积失效|系统停用"),
    ("疏散通道或安全出口严重堵塞锁闭", True, "严重堵塞|出口锁闭|通道堵塞|疏散通道被占"),
    ("违规住人（混合设置）", True, "违规住人|三合一|多合一|住宿与生产|留宿"),
    ("违规存放或使用易燃易爆危险品", True, "易燃易爆|违规存放|危化品|危险品储存"),
    ("消防控制室无人值班或值班无证", False, "无人值班|脱岗|无证上岗|无证值班"),
    ("防火间距被占或消防车道长期被堵", False, "防火间距被占|消防车道被堵|搭建占用"),
]

# ---- 分级阈值 ----
LEVELS = [
    ("低风险", 85, "蓝", 24),
    ("一般风险", 70, "黄", 12),
    ("较高风险", 60, "橙", 12),
    ("高风险", 0, "红", 6),
]

DEDUCT_PAT = re.compile("扣\\s*(\\d+(?:\\.\\d+)?)\\s*分")
SCORE_PAT = re.compile("(?:综合得分|评估得分|总得分|得分)[^0-9]{0,6}(\\d+(?:\\.\\d+)?)\\s*分")
DECLARED_LEVEL_PAT = re.compile("(高风险|较高风险|一般风险|低风险)")
DONE_PAT = re.compile("已整改|整改完成|已完成整改")
NEG_PAT = re.compile("未整改|尚未整改|待整改|整改中|部分整改|尚未完成")
DATE_PAT = re.compile(r"(20\d{2})[-./年](\d{1,2})[-./月](\d{1,2})")


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def hit(pattern, text):
    return re.search(pattern, text) is not None


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except Exception:
        return None


def add_months(d, months):
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = d.day
    while True:
        try:
            return datetime.date(y, m, day)
        except ValueError:
            day -= 1
            if day < 1:
                raise


def grade(score):
    """分数 -> (等级, 颜色, 复评月数)。边界取较严的一档。"""
    for name, low, color, months in LEVELS:
        if score >= low:
            return (name, color, months)
    return ("高风险", "红", 6)


def extract_score(text):
    """从文本抽综合得分：优先用显式得分，其次 100 减扣分合计。"""
    declared = None
    m = SCORE_PAT.search(text)
    if m:
        declared = float(m.group(1))
    deduct = sum(float(x) for x in DEDUCT_PAT.findall(text))
    computed = None
    if deduct > 0:
        computed = round(100.0 - deduct, 2)
        if computed < 0:
            computed = 0.0
    if computed is not None:
        return (computed, declared, deduct, "扣分合计推算")
    if declared is not None:
        return (declared, declared, 0.0, "文本显式得分")
    return (None, None, 0.0, "未提取到分值")


def scan_elements(text):
    out = []
    for name, pat in ELEMENTS:
        ok = hit(pat, text)
        out.append((name, ("有" if ok else "缺")))
    return out


def scan_units(text):
    out = []
    for name, weight, pat in UNITS:
        ok = hit(pat, text)
        out.append((name, weight, ("有" if ok else "缺")))
    return out


def scan_direct(text):
    out = []
    for name, core, pat in DIRECT_ITEMS:
        if hit(pat, text):
            out.append((name, core))
    return out


def apply_direct(base_level, direct_hits):
    """直接判定升档：命中>=1 不低于较高风险；命中>=2 或命中核心项为高风险。"""
    order = {"低风险": 0, "一般风险": 1, "较高风险": 2, "高风险": 3}
    level = base_level
    if direct_hits:
        cores = [d for d in direct_hits if d[1]]
        if len(direct_hits) >= 2 or cores:
            level = "高风险"
        else:
            level = "较高风险"
    # 不得因为未命中而降低原等级
    return level if order[level] >= order[base_level] else base_level


def closure_status(text):
    done = bool(DONE_PAT.search(text))
    neg = bool(NEG_PAT.search(text))
    if neg and not done:
        return "存在未完成整改事项"
    if neg and done:
        return "部分完成，仍有未完成事项（须逐条核对）"
    if done:
        return "有已完成整改表述（须核对复核记录）"
    return "未提取到整改表述"


def build_report(args):
    text = read_text(args.file)
    as_of = parse_date(args.as_of) or datetime.date.today()
    ev_date = parse_date(args.date)

    elements = scan_elements(text)
    units = scan_units(text)
    direct = scan_direct(text)
    if args.score is not None:
        score, declared, deduct, how = (float(args.score), None, 0.0, "命令行给定")
    else:
        score, declared, deduct, how = extract_score(text)

    miss_e = [x[0] for x in elements if x[1] == "缺"]
    miss_u = [x[0] for x in units if x[2] == "缺"]

    lines = []
    lines.append("# 消防安全评估报告核查结果")
    lines.append("")
    lines.append("核查基准日：" + str(as_of))
    lines.append("")

    lines.append("## 一、九个一级单元")
    lines.append("")
    lines.append("| # | 单元 | 权重 | 状态 |")
    lines.append("|---|---|---|---|")
    for i, (name, weight, st) in enumerate(units, 1):
        lines.append("| %d | %s | %d | %s |" % (i, name, weight, st))
    lines.append("")
    lines.append("缺失单元：" + ("、".join(miss_u) if miss_u else "无"))

    lines.append("")
    lines.append("## 二、14 项必备要素")
    lines.append("")
    lines.append("| # | 要素 | 状态 |")
    lines.append("|---|---|---|")
    for i, (name, st) in enumerate(elements, 1):
        lines.append("| %d | %s | %s |" % (i, name, st))
    lines.append("")
    lines.append("缺失要素：" + ("、".join(miss_e) if miss_e else "无"))

    lines.append("")
    lines.append("## 三、分级校验")
    lines.append("")
    if score is None:
        lines.append("未能从文本中提取分值。请人工核对报告载明得分，或用 --score 传入。")
    else:
        base_level, color, months = grade(score)
        final_level = apply_direct(base_level, direct)
        recompute = add_months(ev_date, months) if ev_date else None
        declared_level = None
        m = DECLARED_LEVEL_PAT.search(text)
        if m:
            declared_level = m.group(1)
        lines.append("| 项目 | 数值 |")
        lines.append("|---|---|")
        lines.append("| 得分来源 | %s |" % how)
        lines.append("| 扣分合计 | %g 分 |" % deduct)
        lines.append("| 综合得分 | %g 分 |" % score)
        if declared is not None:
            diff = round(abs(declared - score), 2)
            flag = "一致" if diff <= 2 else "**不自洽，退回**"
            lines.append("| 报告载明得分 | %g 分（差值 %g，判定：%s） |" % (declared, diff, flag))
        lines.append("| 按分值应定等级 | %s（%s） |" % (base_level, color))
        if declared_level:
            agree = "一致" if declared_level == final_level else "**不一致，退回**"
            lines.append("| 报告载明等级 | %s（与复核结果：%s） |" % (declared_level, agree))
        lines.append("| 复核后等级 | %s |" % final_level)
        lines.append("| 建议复评周期 | %d 个月内 |" % months)
        if recompute:
            left = (recompute - as_of).days
            lines.append("| 按评估日期推算复评截止日 | %s（距基准日 %d 天） |" % (recompute, left))
        lines.append("")
        lines.append("整改闭环状态：" + closure_status(text))

    lines.append("")
    lines.append("## 四、直接判定项")
    lines.append("")
    if direct:
        lines.append("| 序号 | 情形 | 是否核心 |")
        lines.append("|---|---|---|")
        for i, (name, core) in enumerate(direct, 1):
            lines.append("| %d | %s | %s |" % (i, name, ("核心" if core else "否")))
        lines.append("")
        lines.append("命中 %d 项。命中一项以上等级不得低于较高风险；命中两项以上或含核心项，直接定为高风险。" % len(direct))
    else:
        lines.append("未在该文本中检索到直接判定项表述。若现场实际情况存在上述情形而报告未列，属于漏报。")

    lines.append("")
    lines.append("## 五、备注")
    lines.append("")
    lines.append("- 脚本只做关键词与数字匹配，不代表专业判断；分数线与周期为常见口径，以当地要求为准。")
    lines.append("- 「未整改」「整改中」「部分整改」均按未完成处理，不得按已完成统计。")
    lines.append("- 不得用于修改、删减、伪造评估记录或报告。")
    return "\n".join(lines)


def selftest():
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    # 用例 1：分级阈值
    check(grade(90)[0] == "低风险", "用例1 90 分应为低风险，实际：" + grade(90)[0])
    check(grade(85)[0] == "低风险", "用例1 85 分应为低风险（边界取较严），实际：" + grade(85)[0])
    check(grade(84.9)[0] == "一般风险", "用例1 84.9 分应为一般风险，实际：" + grade(84.9)[0])
    check(grade(70)[0] == "一般风险", "用例1 70 分应为一般风险，实际：" + grade(70)[0])
    check(grade(65)[0] == "较高风险", "用例1 65 分应为较高风险，实际：" + grade(65)[0])
    check(grade(60)[0] == "较高风险", "用例1 60 分应为较高风险，实际：" + grade(60)[0])
    check(grade(59.9)[0] == "高风险", "用例1 59.9 分应为高风险，实际：" + grade(59.9)[0])
    check(grade(0)[0] == "高风险", "用例1 0 分应为高风险，实际：" + grade(0)[0])

    # 用例 2：从文本抽扣分并推算得分
    t2 = "扣 5 分\n扣 3 分\n扣 12 分"
    sc2, declared2, deduct2, how2 = extract_score(t2)
    check(deduct2 == 20.0, "用例2 扣分合计应为 20，实际：" + str(deduct2))
    check(sc2 == 80.0, "用例2 推算得分应为 80，实际：" + str(sc2))

    # 用例 3：文本显式得分优先用于比对
    t3 = "综合得分 88 分"
    sc3, declared3, deduct3, how3 = extract_score(t3)
    check(sc3 == 88.0 and declared3 == 88.0, "用例3 应取显式得分 88，实际：" + str(sc3))
    check(deduct3 == 0.0, "用例3 无扣分时扣分合计应为 0")

    # 用例 4：直接判定升档不得降级
    check(apply_direct("低风险", []) == "低风险", "用例4 未命中不应改变等级")
    d1 = [("消防设施整体瘫痪或多处失效", True)]
    check(apply_direct("低风险", d1) == "高风险", "用例4 命中核心项应升为高风险，实际：" + apply_direct("低风险", d1))
    d2 = [("消防控制室无人值班或值班无证", False)]
    check(apply_direct("一般风险", d2) == "较高风险", "用例4 命中非核心单项应升为较高风险")
    check(apply_direct("高风险", d2) == "高风险", "用例4 已是高风险时不得降级")

    # 用例 5：扫描能力
    t5 = "\n".join([
        "某某商场消防安全评估报告", "建筑面积 30000 平方米",
        "建设工程已办理消防验收并备案，投入使用前手续齐全",
        "评估依据 GB 55037", "评估范围为本商场地上五层",
        "评估日期 2026-03-01，现场工作时间两天",
        "评估方法：现场检查、功能测试、资料查阅；评估组三人",
        "防火分区、防火门、防火卷帘检查记录：防火封堵局部缺失，扣 4 分",
        "安全出口、疏散通道检查：部分疏散指示不亮，扣 3 分",
        "火灾自动报警、自动喷水、消火栓联动测试正常",
        "电气线路、配电箱检查发现私拉乱接，扣 2 分",
        "管理制度、值班、培训、演练台账齐全",
        "微型消防站人员与装备清单齐全",
        "上次评估问题整改情况已逐条复核",
        "存在问题清单：见上；整改建议：限期整改；计划下季度复查",
        "综合得分 91 分，评估结论为低风险",
        "评估机构盖章，技术负责人签字，有效期十二个月",
    ])
    miss_u5 = [x[0] for x in scan_units(t5) if x[2] == "缺"]
    check(miss_u5 == [], "用例5 九个单元应全覆盖，缺：" + str(miss_u5))
    miss_e5 = [x[0] for x in scan_elements(t5) if x[1] == "缺"]
    check(miss_e5 == [], "用例5 十四项要素应全覆盖，缺：" + str(miss_e5))

    # 用例 6：否定词不得按已完成处理
    t6 = "部分问题已整改，其余尚未整改"
    check(closure_status(t6) == "部分完成，仍有未完成事项（须逐条核对）", "用例6 闭环状态判断错误：" + closure_status(t6))
    check(closure_status("所有问题尚未整改") == "存在未完成整改事项", "用例6 否定词判断错误")

    # 用例 7：复评日期推算
    check(str(add_months(parse_date("2026-01-15"), 6)) == "2026-07-15", "用例7 加 6 个月计算错误：" + str(add_months(parse_date("2026-01-15"), 6)))
    check(str(add_months(parse_date("2026-08-31"), 6)) == "2027-02-28", "用例7 月末回退计算错误：" + str(add_months(parse_date("2026-08-31"), 6)))

    lines = []
    if fails:
        lines.append("SELFTEST FAILED")
        for f in fails:
            lines.append(" - " + f)
    else:
        lines.append("SELFTEST OK")
        lines.append("断言组数：7")
        lines.append("覆盖：分级阈值与边界、扣分推算、显式得分、直接判定升档与防降级、要素与单元扫描、否定词闭环、复评日期推算")
    return "\n".join(lines), len(fails)


def write_out(path, content):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main(argv=None):
    ap = argparse.ArgumentParser(description="消防安全评估报告核查")
    ap.add_argument("--file", help="评估报告或问题清单文本文件")
    ap.add_argument("--score", type=float, help="直接给定综合得分用于校验分级")
    ap.add_argument("--date", help="评估日期 YYYY-MM-DD")
    ap.add_argument("--as-of", help="核查基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--out", help="输出文件路径")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    result_file = os.path.join(here, "_selftest_result.txt")

    if args.selftest:
        report, nfail = selftest()
        write_out(result_file, report + "\n")
        sys.stderr.write(report + "\n")
        return 0 if nfail == 0 else 1

    if not args.file:
        msg = "缺少 --file 参数，示例：python assessment_check.py --file 评估报告.txt"
        write_out(result_file, msg + "\n")
        sys.stderr.write(msg + "\n")
        return 2
    if not os.path.exists(args.file):
        msg = "文件不存在：" + args.file
        write_out(result_file, msg + "\n")
        sys.stderr.write(msg + "\n")
        return 2

    md = build_report(args)
    if args.format == "json":
        text = read_text(args.file)
        as_of = parse_date(args.as_of) or datetime.date.today()
        if args.score is not None:
            score, declared, deduct, how = (float(args.score), None, 0.0, "命令行给定")
        else:
            score, declared, deduct, how = extract_score(text)
        direct = scan_direct(text)
        base = grade(score)[0] if score is not None else None
        final_level = apply_direct(base, direct) if base else None
        data = {
            "as_of": str(as_of),
            "score": score,
            "declared_score": declared,
            "deduction": deduct,
            "score_source": how,
            "level_by_score": base,
            "final_level": final_level,
            "direct_items": [{"name": n, "core": c} for n, c in direct],
            "missing_units": [x[0] for x in scan_units(text) if x[2] == "缺"],
            "missing_elements": [x[0] for x in scan_elements(text) if x[1] == "缺"],
            "closure": closure_status(text),
        }
        out = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        out = md

    if args.out:
        write_out(args.out, out + "\n")
    write_out(result_file, (json.dumps(data, ensure_ascii=False, indent=2)[:2000] if args.format == "json" else md) + "\n")
    sys.stderr.write("结果已写入：" + (args.out or result_file) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
