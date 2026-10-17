# -*- coding: utf-8 -*-
"""社保转移接续办理核查 v1.0.0

输入：按 templates/社保转移信息采集表.md 填写的 Markdown
输出：八段式核查报告（或 --json 摘要）

判定纪律：
- 只做形式逻辑推演（年龄门槛、10 年规则），金额/年限一律以用户填写为准
- 不内置任何城市的基数、社平工资、最低年限
- 不代填政务表单、不承诺办结时间
"""
import argparse
import datetime as dt
import json
import os
import sys

VERSION = "1.0.0"

# 占位符：模板里没填的内容，一律不当真
PLACEHOLDER = (
    "【待填】",     # 【待填】
    "填什么",           # 填什么
    "是 / 否",              # 是 / 否
    "有 / 无",              # 有 / 无
    "喵",                       # 喵（防止误写）
    "___",
)


def norm(s):
    """归一化：去空格、全角括号、竖线。"""
    if s is None:
        return ""
    t = str(s)
    t = t.replace("　", " ").replace(" ", "")
    t = t.replace("（", "(").replace("）", ")")
    t = t.replace("|", " ").strip()
    return t


def clean(s):
    if s is None:
        return ""
    return str(s).strip().strip("|").strip()


def is_ph(v):
    t = norm(v)
    if not t:
        return True
    for w in PLACEHOLDER:
        if norm(w) in t:
            return True
    if t in ("-", "--", "/", "—"):
        return True
    # 表格分隔行：|---|---|
    if t and set(t) <= set("-—:=/"):
        return True
    return False


def is_row(ln):
    s = ln.strip()
    return s.startswith("|") and s.count("|") >= 2


def split_row(ln):
    s = ln.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def rows_of(lines, i):
    """从行号 i 开始向下收集连续表格行，返回 (cells 列表, 结束行号)。"""
    cells = []
    j = i
    while j < len(lines):
        if is_row(lines[j]):
            cells.append(split_row(lines[j]))
            j += 1
        elif lines[j].strip() == "":
            j += 1
            if j < len(lines) and is_row(lines[j]):
                continue
            break
        else:
            break
    return cells, j


def section(text, *names):
    """返回某节标题下的 (起始行号, 结束行号)。"""
    lines = text.splitlines()
    s = None
    for i, ln in enumerate(lines):
        if ln.startswith("#"):
            for n in names:
                if n in ln:
                    s = i + 1
                    break
        elif s is not None and ln.startswith("#") and not ln.startswith("###"):
            return s, i
        if s is not None:
            continue
    return (s or 0), len(lines)


def get_text(text, *labels):
    """两列表里按标签取值，跳过占位符。"""
    for line in text.splitlines():
        if not is_row(line):
            continue
        c = split_row(line)
        if len(c) < 2:
            continue
        k, v = c[0], c[1]
        for lb in labels:
            if lb in norm(k):
                if not is_ph(v):
                    return clean(v)
    return ""


def get_text_multi(text, *labels):
    out = []
    for line in text.splitlines():
        if not is_row(line):
            continue
        c = split_row(line)
        if len(c) < 2:
            continue
        for lb in labels:
            if lb in norm(c[0]) and not is_ph(c[1]):
                out.append(clean(c[1]))
                break
    return out


def get_int(text, *labels):
    v = get_text(text, *labels)
    if not v:
        return None
    digits = ""
    for ch in norm(v):
        if ch.isdigit() or ch == ".":
            digits += ch
        else:
            break
    if not digits:
        return None
    try:
        return int(float(digits))
    except Exception:
        return None


def yes(text, *labels):
    """是/有 → True；否/无 → False；没填 → None。"""
    v = get_text(text, *labels)
    if not v:
        return None
    t = norm(v)
    if "否" in t or "无" in t or "没" in t:   # 否 / 无 / 没
        return False
    if "是" in t or "有" in t:                    # 是 / 有
        return True
    return None


def parse_year(v):
    if not v:
        return None
    t = norm(v)
    year = ""
    for ch in t:
        if ch.isdigit():
            year += ch
            if len(year) == 4:
                break
        elif year:
            break
    if len(year) == 4:
        y = int(year)
        if 1940 <= y <= 2026:
            return y
    return None


# ---------------------------------------------------------------- 险种规则
INSURANCE = [
    ("养老保险", "可转", "个人账户全额 + 统筹基金 12%",
     "统筹部分不全额转"),
    ("医疗保险", "可转", "个人账户余额 + 职工医保缴费年限累计",
     "居民医保年限不累计"),
    ("失业保险", "可转", "缴费年限累计",
     "领取失业金期间不能办转移"),
    ("工伤保险", "不转", "—", "由新参保地重新参保，无年限概念"),
    ("生育保险", "不转", "—", "同上"),
]

MATERIALS = [
    ("身份证 / 社会保障卡", "必备", "先补办或用户口本替代"),
    ("原参保地《参保缴费凭证》", "多数地区已免", "原参保地窗口或网上打印"),
    ("新参保地参保记录", "必备", "先让新单位办理增员"),
    ("已提交转移申请", "必备", "国家社会保险公共服务平台或新参保地窗口"),
]


def parse_years(text):
    """第三节：各地养老缴费年限。返回 [(城市, 是否户籍地, 年限, 首次参保年)]"""
    lines = text.splitlines()
    s, e = section(text, "养老缴费年限", "缴费年限")
    out = []
    for ln in lines[s:e]:
        if not is_row(ln):
            continue
        c = split_row(ln)
        if len(c) < 3:
            continue
        head = " ".join(c)
        if "城市" in norm(head) or "参保城市" in norm(head):
            continue
        city = clean(c[0])
        if is_ph(city):
            continue
        is_reg = "是" in norm(c[1]) and "否" not in norm(c[1])
        yrs = None
        v = norm(c[2])
        dig = ""
        for ch in v:
            if ch.isdigit() or ch == ".":
                dig += ch
            elif dig:
                break
        if dig:
            try:
                yrs = float(dig)
            except Exception:
                yrs = None
        first = parse_year(c[3]) if len(c) > 3 else None
        out.append((city, is_reg, yrs, first))
    return out


def build_report(path, base=None):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return None, "读不了文件：%s" % e

    if base is None:
        base = dt.date.today()
    L = []
    A = L.append

    gender_raw = get_text(text, "性别")
    gender = ""
    if "男" in norm(gender_raw):
        gender = "男"
    elif "女" in norm(gender_raw):
        gender = "女"

    birth = get_text(text, "出生年月")
    byear = parse_year(birth)
    age = (base.year - byear) if byear else None

    region = get_text(text, "户籍地")
    src_city = get_text(text, "原参保地")
    dst_city = get_text(text, "新参保地")
    identity = get_text(text, "参保身份")

    pensioning = yes(text, "领取基本养老金", "领取养老金")
    retired = yes(text, "法定退休年龄", "退休年龄")
    dst_joined = yes(text, "新参保地是否已参保缴费", "新参保地已参保")
    src_stopped = yes(text, "原参保地是否已停保", "原参保地已停保")
    dup = yes(text, "重复缴费", "同时缴费")
    owe = yes(text, "欠费")
    on_dole = yes(text, "失业金", "领取失业金")
    gap_months = get_int(text, "医保断缴", "断缴几个月")
    to_retire = get_int(text, "距离预计退休", "距离退休")

    years = parse_years(text)

    # 空表保护：三样关键信息都没填，直接给提示，不做空报告
    if not src_city and not dst_city and not gender:
        return None, ("未解析到关键信息。至少要填："
                      "「性别」、「原参保地」、「新参保地」"
                      "中的任一项，否则无法判定。")

    # ---- 账户性质
    tmp = None
    tmp_reason = ""
    if gender and byear:
        gate = 50 if gender == "男" else 40
        non_local = bool(dst_city and region and norm(dst_city) != norm(region))
        # 临时账户看的是「在新参保地首次参保时的年龄」，不是最早的参保记录
        first_year = None
        for c, isreg, y, fy in years:
            if fy and dst_city and (norm(c) in norm(dst_city) or norm(dst_city) in norm(c)):
                first_year = fy
                break
        if first_year is None:
            for c, isreg, y, fy in years:
                if fy and (first_year is None or fy < first_year):
                    first_year = fy
        age_at = (first_year - byear) if first_year else age
        if non_local and age_at is not None and age_at >= gate:
            tmp = True
            tmp_reason = ("首次参保时 %d 岁，已过 %s 性 %d 岁门槛，"
                          "且参保地非户籍地" % (age_at, gender, gate))
        else:
            tmp = False
            tmp_reason = ("未触及临时账户条件"
                          + ("（现龄 %s 岁）" % age if age is not None else ""))
    else:
        tmp_reason = "性别或出生年月未填，判不了"

    # ---- 待遇领取地
    place = ""
    place_reason = ""
    if years:
        # 只有「户籍地确实缴过」才算关系在户籍地；年限填 0 等于没参保
        reg_rows = [x for x in years if x[1] and (x[2] or 0) > 0]
        if reg_rows:
            place = reg_rows[0][0]
            place_reason = "养老关系在户籍地，由户籍地办理"
        else:
            ten = [x for x in years if x[2] is not None and x[2] >= 10]
            if ten:
                place = ten[-1][0]
                place_reason = "最后一个累计缴满 10 年的参保地"
            else:
                place = region or "户籍地"
                place_reason = "各参保地均不满 10 年，转回户籍地"
    else:
        place_reason = "未填各地缴费年限，无法推演"

    blockers = []
    if pensioning:
        blockers.append(("已开始领取基本养老金",
                         "不能办理转移", "待遇已核定并开始支付，关系就此固定"))
    if tmp:
        blockers.append(("新参保地为临时账户",
                         "不能转入", "先定真正的待遇领取地，再从临时账户地转出"))
    if dup:
        blockers.append(("存在重复缴费", "先清退再转",
                         "重复时段只能保留一个，统筹部分不退"))
    if owe:
        blockers.append(("原参保地有欠费", "先补缴或核减",
                         "欠费月份不计入转移"))
    if on_dole:
        blockers.append(("正在领取失业金", "领完或书面放弃后再办",
                         "领金期间不受理转移"))

    missing_pre = []
    if dst_joined is False:
        missing_pre.append(("新参保地尚未参保缴费", "先让新单位办理增员，或以灵活就业身份自行参保"))
    if src_stopped is False:
        missing_pre.append(("原参保地尚未停保", "联系原单位办理停保或减员"))
    if not src_city:
        missing_pre.append(("未填原参保地", "补上要转出的城市"))
    if not dst_city:
        missing_pre.append(("未填新参保地", "补上要转入的城市"))

    have = get_text_multi(text, "身份证", "参保缴费凭证",
                          "新参保地参保记录", "转移申请")

    # ---------------- 报告
    A("# 社保转移接续核查报告")
    A("")
    A("> 生成日期：%s；脚本版本 v%s" % (base.isoformat(), VERSION))
    A("")

    A("## 一、结论摘要")
    A("")
    if blockers:
        A("- 现阶段**办不了**，共 %d 处硬性卡点，先解决再提交。" % len(blockers))
        for name, _, _ in blockers:
            A("  - %s" % name)
    elif missing_pre:
        A("- 没有硬性阻断，但**前置条件还差 %d 项**，补上就能提交。" % len(missing_pre))
    else:
        A("- 未发现硬性阻断，前置条件也具备，**可以直接向新参保地提出申请**。")
    if tmp:
        A("- ⚠️ 新参保地判定为**临时账户**：外地账户转不进来，只能往外转出。")
    if place:
        A("- 按 10 年规则推演，待遇领取地倒向于：**%s**（以经办机构核定为准）。" % place)
    A("- 法定时限 **45 个工作日**，实务常 1–3 个月；养老、医保、失业要**分别申请**。")
    A("")

    A("## 二、能不能办：硬性阻断检查")
    A("")
    A("| 检查项 | 结果 | 说明 |")
    A("|---|---|---|")
    def verdict(flag, hit_txt):
        """结果列 + 说明列联动：没命中就别把后果写出来，免得看着像命中了。"""
        if flag is True:
            return "**是**", hit_txt
        if flag is False:
            return "否", "不构成阻断"
        return "未填", "填了才能判断"

    checks = [
        ("是否已在领取基本养老金",) + verdict(pensioning, "待遇已核定并开始支付，关系就此固定，办不了转移"),
        ("新参保地是否为临时账户",) + (("**是**", "外地账户转不进来，只能往外转") if tmp
                                  else (("否", tmp_reason) if tmp is False
                                        else ("判不出", "需要性别、出生年月、户籍地、首次参保年份"))),
        ("是否重复缴费未清退",) + verdict(dup, "重复时段只能保留一个，统筹部分不退，先办清退"),
        ("原参保地是否欠费",) + verdict(owe, "欠费月份不计入转移，先补缴或核减"),
        ("是否正在领取失业金",) + verdict(on_dole, "领金期间不受理转移，领完或书面放弃后再办"),
    ]
    for a, b, c in checks:
        A("| %s | %s | %s |" % (a, b, c))
    A("")

    A("## 三、账户性质判定")
    A("")
    A("| 项 | 情况 |")
    A("|---|---|")
    A("| 性别 | %s |" % (gender or "未填"))
    A("| 出生年月 | %s |" % (birth or "未填"))
    A("| 现年龄 | %s |" % ("%d 岁" % age if age is not None else "未填"))
    A("| 户籍地 | %s |" % (region or "未填"))
    A("| 新参保地 | %s |" % (dst_city or "未填"))
    A("| 判定 | %s |" % ("**临时账户**" if tmp else ("一般账户" if tmp is False else "无法判定")))
    A("")
    if tmp:
        A("门槛：男 50 岁 / 女 40 岁，且在**非户籍地首次参保**。")
        A("")
        A("- 外地账户 **转不进来**；")
        A("- 临时账户可以 **转出** 到真正的待遇领取地；")
        A("- 里面的钱和年限不作废，退休前合并计算。")
    else:
        A("判定依据：%s。" % (tmp_reason or "信息不全"))
    A("")

    A("## 四、待遇领取地推演")
    A("")
    if years:
        A("| 参保城市 | 是否户籍地 | 累计年限 | 首次参保年份 |")
        A("|---|---|---|---|")
        for c, isreg, y, fy in years:
            A("| %s | %s | %s | %s |" % (c, "是" if isreg else "否",
                                         ("%g" % y) if y is not None else "未填",
                                         fy or "未填"))
        A("")
        if place:
            A("**推演结果：%s**——%s。" % (place, place_reason))
            A("")
            A("判定顺序：户籍地有参保 → 户籍地；"
              "否则找累计满 10 年的参保地；"
              "都不满 10 年 → 回户籍地。")
    else:
        A("采集表里没填各地缴费年限，无法推演。"
          "补上后重跑一次。")
    A("")

    A("## 五、能转什么 / 不转什么")
    A("")
    A("| 险种 | 能否转移 | 转什么 | 不转什么 |")
    A("|---|---|---|---|")
    for name, can, yes_, no_ in INSURANCE:
        A("| %s | %s | %s | %s |" % (name, can, yes_, no_))
    A("")

    A("## 六、前置条件与材料")
    A("")
    A("| 项 | 状态 | 缺了怎么办 |")
    A("|---|---|---|")
    if missing_pre:
        for k, fix in missing_pre:
            A("| %s | **缺** | %s |" % (k, fix))
    else:
        A("| 前置条件 | 齐备 | 可以提交申请 |")
    joined = " ".join(have)
    for label, need, fix in MATERIALS:
        got = any(lab in joined for lab in (label.split(" / ")[0], label))
        A("| %s | %s | %s |" % (label, "有" if got else "**缺**", fix))
    A("")

    A("## 七、办理流程与时限")
    A("")
    A("| 环节 | 时限 |")
    A("|---|---|")
    A("| 新参保地受理、发出《联系函》 | 15 个工作日内 |")
    A("| 原参保地生成《信息表》并划转基金 | 15 个工作日内 |")
    A("| 新参保地收到后办结并通知 | 15 个工作日内 |")
    A("")
    A("合计 **45 个工作日**。查进度：国家社会保险公共服务平台"
      " `si.12333.gov.cn`、掌上 12333、电子社保卡；超时打 12333 催办。")
    A("")

    A("## 八、风险与断缴影响")
    A("")
    risks = []
    if gap_months:
        risks.append(("医保已断缴 %d 个月" % gap_months,
                      "断缴期间看病全自费，重新参保可能有等待期；"
                      "购戼/落户/生育津贴多要求连续缴费，补缴通常不算连续"))
    else:
        risks.append(("医保断缴",
                      "停保次月起待遇中断，转移期间不能报销"))
    if to_retire is not None and to_retire <= 1:
        risks.append(("距离退休仅 %d 年" % to_retire,
                      "45 个工作日只是法定下限，实务常 1–3 个月，"
                      "出问题还要补正，建议立即启动"))
    if identity and "灵活就业" in norm(identity):
        risks.append(("参保身份为灵活就业",
                      "部分城市对灵活就业人员跨省转移有额外限制，"
                      "先打 12333 问新参保地口径"))
    if dup:
        risks.append(("重复缴费", "统筹部分不退，只退个人账户部分，"
                                              "先算清退金额再决定值不值得办"))
    if tmp:
        risks.append(("临时账户", "外地账户转不进来，先定待遇领取地再转，"
                                       "否则白跑"))
    if not risks:
        risks.append(("未发现特殊风险", "按流程办即可"))
    A("| 风险 | 影响与处置 |")
    A("|---|---|")
    for k, v in risks:
        A("| %s | %s |" % (k, v))
    A("")

    A("## 九、待办动作")
    A("")
    todo = []
    for name, _, fix in blockers:
        todo.append("%s：%s" % (name, fix))
    for k, fix in missing_pre:
        todo.append("%s：%s" % (k, fix))
    for label, _need, fix in MATERIALS:
        if not any(lab in joined for lab in (label.split(" / ")[0], label)):
            todo.append("准备%s：%s" % (label, fix))
    todo.append("向**新参保地**提出转移申请（不是回原参保地）")
    todo.append("养老、医保、失业分别申请，工伤生育不用管")
    todo.append("记下申请编号，第 15 / 30 / 45 个工作日各查一次进度")
    if gap_months:
        todo.append("先问新参保地：补缴算不算连续缴费（购戼/落户/入学资格需要）")
    for i, t in enumerate(todo, 1):
        A("%d. %s" % (i, t))
    A("")

    A("## 十、输出纪律与免责")
    A("")
    A("- 本报告只做形式逻辑推演（年龄门槛、10 年规则），"
      "年限、金额、账户性质最终以参保地经办机构核定为准；")
    A("- 不代拟正式申请书、不代填政务表单、不承诺办结时间；")
    A("- 各地口径（尤其是灵活就业能否办理、居民医保年限能否折算）"
      "差异极大，一律以参保地经办机构答复为准。")
    A("")

    body = "\n".join(L)
    meta = {
        "version": VERSION,
        "blockers": len(blockers),
        "missing_pre": len(missing_pre),
        "risks": len(risks),
        "temporary_account": tmp,
        "pension_place": place,
        "age": age,
    }
    return body, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    base = None
    if a.base:
        try:
            base = dt.date(*[int(x) for x in a.base.split("-")])
        except Exception:
            base = None

    body, meta = build_report(a.input, base)
    if body is None:
        print(meta if isinstance(meta, str) else "未能生成报告：请检查采集表是否填写了「原参保地 / 新参保地 / 出生年月」等关键项")
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                f.write(str(meta))
        return 2

    if a.json:
        txt = json.dumps(meta, ensure_ascii=False, indent=2)
    else:
        txt = body

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
        print("written %s" % a.out)
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
