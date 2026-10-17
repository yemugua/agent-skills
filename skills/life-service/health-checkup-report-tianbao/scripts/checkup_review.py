#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""体检报告异常项核验脚本 v1.0.0

只做三件事：逐项比对参考区间 -> 四档分级 -> 标红旗并给出带时间的复查建议。
不诊断、不替代医生、不上传任何数据。
参考区间优先取报告自带；没有才回退内置兜底表（输出里会显式标注）。
"""
import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"

CLOCK = "YYYY-MM-DD"
PLACEHOLDER = ("待填写", "待填", "暂无", "—", "-", "?", "（待补）", "无")

# ---------------------------------------------------------------- 内置兜底区间
# key: 项目名(含别名用 | 分隔); lo/hi: 区间; unit: 单位; low_ok: 越低越好时 True(仍按低于下限算偏低)
_BASE = {
    "收缩压|血压|高压": {"lo": 90, "hi": 139, "unit": "mmHg"},
    "舒张压|低压": {"lo": 60, "hi": 89, "unit": "mmHg"},
    "空腹血糖|血糖|葡萄糖": {"lo": 3.9, "hi": 6.1, "unit": "mmol/L", "red": 11.1, "warn": 7.0},
    "总胆固醇|胆固醇|TC": {"hi": 5.2, "unit": "mmol/L"},
    "甘油三酯|TG": {"hi": 1.7, "unit": "mmol/L"},
    "高密度脂蛋白|HDL": {"lo": 1.0, "unit": "mmol/L"},
    "低密度脂蛋白|LDL": {"hi": 3.4, "unit": "mmol/L", "red": 4.9},
    "丙氨酸氨基转移酶|ALT|谷丙转氨酶": {"lo": 9, "hi": 50, "unit": "U/L", "red_mul": 3.0},
    "天门冬氨酸氨基转移酶|AST|谷草转氨酶": {"lo": 15, "hi": 40, "unit": "U/L", "red_mul": 3.0},
    "肌酐|Cr": {"lo": 57, "hi": 111, "unit": "umol/L", "red_mul": 2.0},
    "尿素氮|BUN|尿素": {"lo": 3.1, "hi": 8.0, "unit": "mmol/L"},
    "尿酸|UA": {"lo": 208, "hi": 428, "unit": "umol/L"},
    "血红蛋白|Hb": {"lo": 130, "hi": 175, "unit": "g/L", "red_low_ratio": 0.70},
    "红细胞|RBC": {"lo": 4.3, "hi": 5.8, "unit": "10^12/L"},
    "白细胞|WBC": {"lo": 3.5, "hi": 9.5, "unit": "10^9/L"},
    "血小板|PLT": {"lo": 125, "hi": 350, "unit": "10^9/L"},
    "谷氨酰转肽酶|GGT|r-GT": {"lo": 10, "hi": 60, "unit": "U/L"},
    "总胆红素|TBIL|胆红素": {"lo": 3.4, "hi": 20.5, "unit": "umol/L"},
    "肌酸激酶|CK|磷酸肌酸激酶": {"lo": 50, "hi": 310, "unit": "U/L"},
    "促甲状腺激素|TSH": {"lo": 0.27, "hi": 4.2, "unit": "mIU/L"},
    "游离甲状腺素|FT4": {"lo": 12, "hi": 22, "unit": "pmol/L"},
    "体脂率|体脂": {"lo": 15, "hi": 20, "unit": "%"},
    "腰围": {"hi": 90, "unit": "cm"},
}
_FEMALE = {
    "高密度脂蛋白|HDL": {"lo": 1.3, "unit": "mmol/L"},
    "血红蛋白|Hb": {"lo": 115, "hi": 150, "unit": "g/L", "red_low_ratio": 0.70},
    "红细胞|RBC": {"lo": 3.8, "hi": 5.1, "unit": "10^12/L"},
    "丙氨酸氨基转移酶|ALT|谷丙转氨酶": {"lo": 7, "hi": 40, "unit": "U/L", "red_mul": 3.0},
    "天门冬氨酸氨基转移酶|AST|谷草转氨酶": {"lo": 13, "hi": 35, "unit": "U/L", "red_mul": 3.0},
    "肌酐|Cr": {"lo": 41, "hi": 81, "unit": "umol/L", "red_mul": 2.0},
    "低密度脂蛋白|LDL": {"hi": 3.3, "unit": "mmol/L", "red": 4.9},
    "腰围": {"hi": 85, "unit": "cm"},
}
# 定性项（结果是阴性/阳性这类）
_QUAL = {
    "尿蛋白": "阴性", "尿糖": "阴性", "尿酮体": "阴性", "尿潜血": "阴性",
    "尿胆红素": "阴性", "尿白细胞": "阴性", "尿微量白蛋白": "阴性",
    "幽门螺杆菌|HP|Hp": "阴性", "乙肝表面抗原|HBsAg": "阴性",
    "粪便潜血|便潜血|OB": "阴性", "甲胎蛋白|AFP": "阴性", "癌胚抗原|CEA": "阴性",
}
# 缺失/未做项判定参考（提示补充，不判异常）
_SUPPLEMENT = [
    ("糖化血红蛋白|HbA1c", "本次血糖处于临界或偏高时，用于看近 3 个月平均血糖"),
    ("肝脏超声|腹部超声", "转氨酶升高时定位原因（脂肪肝/胆道）"),
    ("颈动脉超声", "40 岁以上或血脂边缘值"),
    ("肺部CT|肺CT|胸部CT", "吸烟、粉尘接触、50 岁以上"),
    ("骨密度", "50 岁以上或长期服用激素"),
    ("甲状腺超声", "甲功异常或结节家族史"),
    ("胃肠镜", "消化道症状或 45 岁以上常规筛查"),
]

NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
RANGE_RE = re.compile(r"(-?\d*\.?\d+)\s*[-~～—－–至到]{1,2}\s*(-?\d*\.?\d+)")
LT_RE = re.compile(r"<\s*(-?\d*\.?\d+)")
GT_RE = re.compile(r">\s*(-?\d*\.?\d+)")
HEAD_HINT = {
    "项目": 0, "名称": 0, "检验项目": 0, "检查项目": 0, "项目简称": 0,
    "结果": 1, "测定值": 1, "数值": 1, "单位": 2, "参考区间": 3, "参考值": 3,
    "正常参考值": 3, "标记": 4, "提示": 4, "异常提示": 4,
    # 影像类表格是「项目 | 结论原文 | 提示」，结论列也要认（否则整表被跳过）
    "结论": 1, "检查结果": 1, "所见": 1, "影像所见": 1, "描述": 1,
}
# 超过这个长度当文字结论，绝不按数值判（否则「0.8cm」会被当异常值）
LONG_TEXT = 24
SUGGEST_RE = re.compile(r"[^。；;\n]*?(?:建议[^。；;\n]*|随访|专科就诊|进一步检查)[^。；;\n]*")


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def clean(s):
    return re.sub(r"\s+", " ", str(s or "").strip())


def is_placeholder(s):
    t = clean(s)
    return t == "" or t in PLACEHOLDER


def build_ranges(sex):
    tbl = {}
    for k, v in _BASE.items():
        for one in k.split("|"):
            tbl[one] = dict(v)
    if sex == "女":
        for k, v in _FEMALE.items():
            for one in k.split("|"):
                tbl[one] = dict(v)
    return tbl


def lookup(name, ranges):
    """先精确；再按最长别名优先做包含匹配。
    否则「低密度脂蛋白胆固醇」会先命中「胆固醇」（总胆固醇的区间，没有红線）。
    """
    n = norm(name)
    if n in ranges:
        return n, ranges[n]
    best = (0, None, None)
    for k, v in ranges.items():
        if k and k in n and len(k) > best[0]:
            best = (len(k), k, v)
    if best[1]:
        return best[1], best[2]
    bq = (0, None, None)
    for k, v in _QUAL.items():
        if k and k in n and len(k) > bq[0]:
            bq = (len(k), k, v)
    if bq[1]:
        return bq[1], {"qual": bq[2]}
    return None, None


def parse_ref(text):
    """返回 (lo, hi, kind, raw)。kind: num / qual"""
    t = norm(text)
    if not t:
        return None, None, "none", text
    if "阴性" in t:
        return None, None, "qual", t
    m = RANGE_RE.search(t)
    if m:
        try:
            return float(m.group(1)), float(m.group(2)), "num", t
        except Exception:
            pass
    m = LT_RE.search(t)
    if m:
        try:
            return None, float(m.group(1)), "num", t
        except Exception:
            pass
    m = GT_RE.search(t)
    if m:
        try:
            return float(m.group(1)), None, "num", t
        except Exception:
            pass
    m = NUM_RE.search(t)
    if m:
        try:
            v = float(m.group(0))
            return v, v, "num", t
        except Exception:
            pass
    return None, None, "unknown", text


def judge(item, val, lo, hi, ref_src):
    """四档判定 + 红旗。返回 dict"""
    reds = []
    if lo is None and hi is None:
        return None
    if hi is not None and val > hi:
        ratio = (val - hi) / hi if hi else 0.0
        direction = "偏高"
    elif lo is not None and val < lo:
        ratio = (lo - val) / lo if lo else 0.0
        direction = "偏低"
    else:
        ratio = 0.0
        direction = "正常"
    if direction != "正常":
        if ratio <= 0.10:
            grade = "临界"
        elif ratio < 1.0:
            grade = "轻度" + direction
        else:
            grade = "明显" + direction
    else:
        grade = "正常"
    # 红旗
    spec = item.get("spec") or {}
    name = item.get("name", "")
    if spec.get("red") is not None and val >= float(spec["red"]):
        reds.append("达到红旗线 %s" % spec["red"])
    if spec.get("warn") is not None and val >= float(spec["warn"]):
        reds.append("空腹血糖 %s 以上，需尽快复查并就医" % spec["warn"])
    rm = spec.get("red_mul")
    if rm is not None and hi is not None and val >= hi * float(rm):
        reds.append("超过上限 %s 倍" % rm)
    rlr = spec.get("red_low_ratio")
    if rlr is not None and lo is not None and val <= lo * float(rlr):
        reds.append("低于下限的 %s 倍" % rlr)
    if "收缩压" in name and val >= 180:
        reds.append("收缩压 180 以上")
    if "舒张压" in name and val >= 120:
        reds.append("舒张压 120 以上")
    # 提示型（不进红旗，只做科普提示）
    tip = ""
    warn_line = spec.get("warn")
    if "血糖" in name and direction == "偏高" and lo is not None:
        if warn_line and val < float(warn_line):
            tip = "在空腹血糖受损区间（%s-%s 之间），先做糖化血红蛋白看近 3 个月" % (hi, warn_line)
        elif warn_line and val >= float(warn_line):
            tip = "已达需尽快复查的水平，建议尽快门诊"
    if "胆固醇" in name and "低密度" in name and direction == "偏高":
        tip = tip or "心血管风险关联项，结合 HDL 与血压一起看"
    if "转氨" in name and direction == "偏高":
        tip = tip or "与脂肪肝/饮酒/熬夜相关，多半可逆转"
    return {"grade": grade, "direction": direction, "ratio": round(ratio, 3),
            "reds": reds, "tip": tip, "ref_src": ref_src}


def next_visit(grade):
    if grade == "临界":
        return "3-6 个月复查"
    if grade.startswith("临界"):
        return "3-6 个月复查"
    if grade.startswith("轻度"):
        return "6-8 周复查"
    return "1-2 周内门诊 / 尽快"


# ---------------------------------------------------------------- 解析表格
def parse_tables(text):
    rows = []
    lines = text.splitlines()
    i = 0
    cur = []
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("|"):
            cur.append([c.strip() for c in ln.strip("|").split("|")])
        else:
            if len(cur) >= 2:
                rows.append(cur)
            cur = []
        i += 1
    if len(cur) >= 2:
        rows.append(cur)
    return rows


def col_map(header):
    m = {}
    for idx, cell in enumerate(header):
        c = norm(cell)
        for hint, want in HEAD_HINT.items():
            if hint in c and want not in m:
                m[want] = idx
                break
    return m


def blob_overlap(text, blob, n=10):
    """text 里是否含 blob 的一段（用来剔除已在影像表格里显示过的重复建议句）"""
    if not blob or len(text) < n:
        return False
    for i in range(0, max(1, len(blob) - n + 1), 5):
        if blob[i:i + n] in text:
            return True
    return False


def extract_categories(text):
    """抓正文里的「建议/随访/专科就诊」整句。
    必须先按句切 + 把表格竖线换成空格，否则正则会跨列抓出「建议 6 个月 | |」这种脏行。
    """
    plain = text.replace("|", " ")
    out = []
    for sent in re.split(r"[。；;\n]", plain):
        s = clean(sent)
        if len(s) < 4:
            continue
        if any(k in s for k in ("建议", "随访", "专科就诊", "进一步检查")):
            out.append(s[:80])
    seen, uniq = set(), []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq[:12]


def parse_report(text, sex="男", age=None):
    ranges = build_ranges(sex)
    items = []
    unresolved = []
    fallback = []
    suspect = []
    images = []

    for table in parse_tables(text):
        header = table[0]
        m = col_map(header)
        if 0 not in m and 1 not in m:
            continue
        i_name = m.get(0, 0)
        i_val = m.get(1)
        if i_val is None:
            continue
        i_unit = m.get(2)
        i_ref = m.get(3)
        i_mark = m.get(4)
        # 「结论/检查结果/所见」列整列都是文字（超声、CT、心电图），不看长度
        val_header = header[i_val] if (i_val is not None and i_val < len(header)) else ""
        text_col = any(k in val_header for k in ("结论", "检查结果", "所见", "描述", "影像"))
        for row in table[2:]:
            if not row or len(row) <= max(i_name, i_val):
                continue
            name = clean(row[i_name]) if i_name < len(row) else ""
            raw_val = clean(row[i_val]) if i_val < len(row) else ""
            if not name or is_placeholder(name):
                continue
            unit = clean(row[i_unit]) if (i_unit is not None and i_unit < len(row)) else ""
            ref_text = clean(row[i_ref]) if (i_ref is not None and i_ref < len(row)) else ""
            mark = clean(row[i_mark]) if (i_mark is not None and i_mark < len(row)) else ""
            if not raw_val or is_placeholder(raw_val):
                unresolved.append((name, raw_val or "空"))
                continue
            # 影像/文字列必须在 lookup 之前处理：
            # 「腹部超声/甲状腺超声」等根本不在区间表里，先 lookup 会被丢进未解析
            if text_col or len(raw_val) > LONG_TEXT:
                sug = [clean(x) for x in SUGGEST_RE.findall(raw_val) if len(clean(x)) > 3]
                images.append({"category": name, "conclusion": raw_val, "suggest": sug[:3]})
                continue
            key, spec = lookup(name, ranges)
            if spec is None:
                unresolved.append((name, raw_val))
                continue
            lo, hi, kind, rawref = parse_ref(ref_text)
            ref_src = "报告自带"
            if lo is None and hi is None and kind == "none":
                lo, hi = spec.get("lo"), spec.get("hi")
                if lo is None and hi is None:
                    unresolved.append((name, raw_val))
                    continue
                ref_src = "内置兜底"
                fallback.append(name)
            elif lo is None and hi is None:
                pass
            # 定性项
            if kind == "qual" or (spec.get("qual") is not None and not NUM_RE.fullmatch(raw_val)):
                base = spec.get("qual")
                pos = any(w in raw_val for w in ("阳性", "弱阳性", "异常", "+"))
                neg = any(w in raw_val for w in ("阴性", "正常", "-"))
                if pos:
                    grade, direction, src = "偏高", "异常（阳性）", "报告自带"
                    reds = ["定性项阳性"] if base == "阴性" else []
                elif neg:
                    grade, direction, src = "正常", "正常", "报告自带"
                    reds = []
                else:
                    unresolved.append((name, raw_val))
                    continue
                items.append({"name": name, "value": raw_val, "unit": unit,
                              "lo": None, "hi": None, "grade": grade,
                              "direction": direction, "reds": reds,
                              "tip": "", "ref_src": src, "ratio": 0.0})
                continue
            # 数值项
            mv = NUM_RE.search(raw_val)
            if not mv:
                unresolved.append((name, raw_val))
                continue
            try:
                val = float(mv.group(0))
            except Exception:
                unresolved.append((name, raw_val))
                continue
            # 单位存疑
            if spec.get("unit") and unit and norm(unit).lower() != norm(spec["unit"]).lower():
                suspect.append((name, unit, spec.get("unit")))
            j = judge({"name": name, "spec": spec}, val, lo, hi, ref_src)
            if j is None:
                unresolved.append((name, raw_val))
                continue
            items.append({"name": name, "value": val, "unit": unit,
                          "lo": lo, "hi": hi, "grade": j["grade"],
                          "direction": j["direction"], "reds": j["reds"],
                          "tip": j.get("tip", ""),
                          "ref_src": j["ref_src"], "ratio": j["ratio"]})
    # 去重（同名取最近）
    seen = {}
    for it in items:
        k = norm(it["name"])
        if k in seen:
            continue
        seen[k] = it
    return list(seen.values()), unresolved, fallback, suspect, images, extract_categories(text)


def build_report(path, sex, age):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    items, unresolved, fallback, suspect, images, cats = parse_report(text, sex=sex)
    if not items:
        return None, "未解析到任何可判定项目：请把报告表格按《体检报告采集表》格式填入（至少要有 项目|结果|单位|参考区间 四列）", text

    reds = [it for it in items if it.get("reds")]
    ordered = ["明显偏高", "明显偏低", "轻度偏高", "轻度偏低", "临界", "偏高", "正常"]
    def key(it):
        g = it["grade"]
        d = ordered.index(g) if g in ordered else len(ordered)
        return (d, it["name"])
    items_sorted = sorted(items, key=key)

    mild = [it for it in items_sorted if it["grade"].startswith("明显")]
    light = [it for it in items_sorted if it["grade"].startswith("轻度")]
    crit = [it for it in items_sorted if it["grade"] == "临界"]
    normal = [it for it in items_sorted if it["grade"] == "正常"]

    L = []
    A = L.append
    A("# 体检报告异常项核验（本地处理，不上传）")
    A("")
    A("- 体检日期：%s ｜ 性别：%s ｜ 年龄：%s ｜ 解析来源：%s"
      % (detect_date(text) or CLOCK, sex, age if age else "未填", os.path.basename(path)))
    A("- 共解析 %d 项：正常 %d ｜ 临界 %d ｜ 轻度偏高/偏低 %d ｜ 明显异常 %d ｜ **红旗 %d**"
      % (len(items), len(normal), len(crit), len(light), len(mild), len(reds)))
    A("- 参考区间为内置兜底的项：%d 个（以医院/报告为准）" % len(fallback))
    A("")
    A("## 一、结论摘要")
    A("")
    A(conclusion_line(items, reds))
    A("")
    A("## 二、红旗项（需尽快就医，1-2 周内）")
    A("")
    if reds:
        A("| # | 项目 | 结果 | 命中规则 | 建议 |")
        A("|---|---|---|---|---|")
        for i, it in enumerate(reds, 1):
            A("| %d | %s | %s %s | %s | 尽快到相应专科就诊，带本次+往年报告与用药清单 |"
              % (i, it["name"], it["value"], it.get("unit", ""), "；".join(it["reds"])))
    else:
        A("| # | 项目 | 结果 | 命中规则 | 建议 |")
        A("|---|---|---|---|---|")
        A("| 1 | 无 | — | 无命中 | 按下方复查节奏执行即可 |")
    A("")
    A("## 三、明显异常（≥2 倍 / 需门诊）")
    A("")
    A("| 项目 | 结果 | 单位 | 参考区间 | 档位 | 下一步 |")
    A("|---|---|---|---|---|---|")
    if mild:
        for it in mild:
            A("| %s | %s | %s | %s | %s | %s |"
              % (it["name"], it["value"], it.get("unit", ""), fmt_ref(it),
                 it["grade"], next_visit(it["grade"])))
    else:
        A("| 无 | — | — | — | — | — |")
    A("")
    A("## 四、偏高 / 偏低（>10%-2 倍）")
    A("")
    A("| 项目 | 结果 | 单位 | 参考区间 | 方向 | 可能原因 | 复查时间 | 备注 |")
    A("|---|---|---|---|---|---|---|---|")
    if light:
        for it in light:
            A("| %s | %s | %s | %s | %s | %s | %s | %s |"
              % (it["name"], it["value"], it.get("unit", ""), fmt_ref(it),
                 it["direction"], common_cause(it["name"]),
                 next_visit(it["grade"]), it.get("tip", "") or "—"))
    else:
        A("| 无 | — | — | — | — | — | — |")
    A("")
    A("## 五、临界（≤10%）")
    A("")
    A("| 项目 | 结果 | 单位 | 参考区间 | 建议 |")
    A("|---|---|---|---|---|")
    if crit:
        for it in crit:
            A("| %s | %s | %s | %s | 3-6 个月复查，先生活方式干预 |"
              % (it["name"], it["value"], it.get("unit", ""), fmt_ref(it)))
    else:
        A("| 无 | — | — | — | — |")
    A("")
    A("## 六、影像/检查结论（含常被漏看的「建议」）")
    A("")
    A("| 项目 | 结论要点 | 报告里的「建议」 |")
    A("|---|---|---|")
    if images:
        for im in images:
            sug = "；".join(im["suggest"]) if im["suggest"] else "—"
            A("| %s | %s | %s |" % (im["category"], im["conclusion"][:60], sug))
    else:
        A("| 无 | — | — |")
    if cats:
        blob = " ".join((im.get("conclusion") or "") + " ".join(im.get("suggest") or [])
                        for im in images)
        rest = [c for c in cats if not blob_overlap(c, blob)]
        if rest:
            A("")
            A("总检与其他建议：")
            for c in rest:
                A("- %s" % c)
    A("")
    A("## 七、建议补充检查")
    A("")
    A("| 建议项 | 针对什么 | 优先级 |")
    A("|---|---|---|")
    sup = suggest(items)
    if sup:
        for name, why in sup:
            A("| %s | %s | 高 |" % (name, why))
    else:
        A("| 无额外建议 | 本次无异常项或临界项 | — |")
    A("")
    A("## 八、下一步待办（带时间）")
    A("")
    A("| # | 事项 | 时间 | 状态 |")
    A("|---|---|---|---|")
    todo = todo_list(reds, mild, light, crit)
    for i, t in enumerate(todo, 1):
        A("| %d | %s | %s | 待办 |" % (i, t[0], t[1]))
    A("")
    A("## 九、数据质量提示")
    A("")
    A(unresolved_txt(unresolved, fallback, suspect))
    A("")
    A("---")
    A("")
    A("本核验只做与参考区间的相对位置判断，**不是诊断，不替代医生**。数据全程本地处理。")
    A("")

    body = "\n".join(L)
    result = {"version": VERSION, "sex": sex, "age": age,
              "parsed": len(items), "red_flags": len(reds),
              "normal": len(normal), "critical": len(crit),
              "light": len(light), "mild": len(mild),
              "fallback_ref": len(fallback),
              "items": [{k: v for k, v in it.items()} for it in items_sorted],
              "categories": cats,
              "images": images,
              "unresolved": [list(x) for x in unresolved]}
    return body, result, text


def detect_date(text):
    m = re.search(r"(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})", text)
    if m:
        return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
    return None


def fmt_num(v):
    """整数不显示 .0（9.0-50.0 太脏）"""
    if v is None:
        return "—"
    f = float(v)
    return str(int(f)) if f.is_integer() else str(v)


def fmt_ref(it):
    if it.get("lo") is not None and it.get("hi") is not None:
        return "%s-%s" % (fmt_num(it["lo"]), fmt_num(it["hi"]))
    if it.get("hi") is not None:
        return "<%s" % fmt_num(it["hi"])
    if it.get("lo") is not None:
        return ">%s" % fmt_num(it["lo"])
    return "—"


def common_cause(name):
    n = norm(name)
    # 注意：「丙氨酸氨基转移酶」里没有连续的「转氨」（是 氨-基-转-移-酶），要认「转移酶」
    if "转氨" in n or "转移酶" in n or "ALT" in n or "AST" in n or "GGT" in n:
        return "熬夜/饮酒/脂肪肝/用药"
    if "血糖" in n:
        return "体检前未空腹/近期糖摄入/胰岛素抵抗"
    if "尿酸" in n:
        return "海鲜啤酒火锅/饮水少/代谢因素"
    if "血脂" in n or "胆固醇" in n:
        return "饮食油腻/运动少/未服降脂药"
    if "血压" in n:
        return "白大衣效应/未静坐/熬夜"
    if "血红蛋白" in n or "红细胞" in n:
        return "节食/经期/缺铁"
    if "白细胞" in n:
        return "近几天炎症/熬夜/应激"
    if "肌酐" in n or "尿素" in n:
        return "饮水少/高蛋白饮食/肾功能关注"
    return "结合生活方式与既往史判断"


def conclusion_line(items, reds):
    if reds:
        names = "、".join(it["name"] for it in reds[:4])
        return "本次有 **%d 项红旗**（%s），需尽快就医，不要等下次体检。" % (len(reds), names)
    mild = [it for it in items if it["grade"].startswith("明显")]
    light = [it for it in items if it["grade"].startswith("轻度")]
    crit = [it for it in items if it["grade"] == "临界"]
    parts = []
    if mild:
        parts.append("明显异常 %d 项（%s）" % (len(mild), "、".join(it["name"] for it in mild[:4])))
    if light:
        parts.append("轻度偏高/偏低 %d 项（%s）" % (len(light), "、".join(it["name"] for it in light[:4])))
    if crit:
        parts.append("临界 %d 项（%s）" % (len(crit), "、".join(it["name"] for it in crit[:4])))
    if not parts:
        return "本次全部项目均在参考区间内，无红旗项；保持年度复查节奏即可。"
    return "本次主要问题：" + "；".join(parts) + "。多为生活方式相关，建议门诊确认后按时间复查。"


def suggest(items):
    names = " ".join(norm(it["name"]) for it in items)
    out = []
    for key, why in _SUPPLEMENT:
        hit = False
        for part in key.split("|"):
            if part in names:
                hit = True
                break
        if not hit:
            out.append((key.split("|")[0], why))
    return out[:6]


def todo_list(reds, mild, light, crit):
    out = []
    for it in reds:
        out.append(("挂相应专科门诊复查：%s（%s %s）" % (it["name"], it["value"], it.get("unit", "")), "1-2 周内"))
    for it in mild[:3]:
        out.append(("门诊确认 %s 并处理" % it["name"], "2 周内"))
    for it in light[:3]:
        out.append(("复查 %s，复测前 3 天清淡饮食、不饮酒、不熬夜" % it["name"], next_visit(it["grade"])))
    for it in crit[:3]:
        out.append(("关注 %s，调整生活方式" % it["name"], "3-6 个月"))
    if not out:
        out.append(("本次无异常待办，预约明年体检", "本年度内"))
    return out[:8]


def unresolved_txt(unresolved, fallback, suspect):
    L = []
    if unresolved:
        L.append("- **未解析项（%d）**：%s —— 请对照原文补全，脚本不会猜值。"
                 % (len(unresolved), "、".join("%s=%s" % (a, b) for a, b in unresolved[:8])))
    else:
        L.append("- 未解析项：无")
    L.append("- 参考区间为内置兜底（以医院为准）的项：%d 个%s"
             % (len(fallback), ("：" + "、".join(fallback[:8])) if fallback else ""))
    if suspect:
        L.append("- **单位存疑（未参与判定）**：%s —— 请人工核对单位后重跑。"
                 % ("；".join("%s 报告%s / 内置%s" % (a, b, c) for a, b, c in suspect[:5])))
    else:
        L.append("- 单位存疑项：无")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="体检报告异常项核验")
    ap.add_argument("report", help="体检报告文本（md/txt）")
    ap.add_argument("--sex", default="男", choices=["男", "女"], help="性别，影响内置兜底区间")
    ap.add_argument("--age", default=None, help="年龄，仅用于报告展示")
    ap.add_argument("--out", default=None, help="输出 md 路径（默认与报告同目录）")
    ap.add_argument("--json", action="store_true", help="额外输出 json 结果")
    args = ap.parse_args()

    if not os.path.exists(args.report):
        print("文件不存在：%s" % args.report)
        print("=EXIT= 2")
        return 2

    body, result, raw = build_report(args.report, args.sex, args.age)
    # 空/不可解析输入：body 为 None，提示串在 result 里 —— 两个都要挡，否则 f.write(None) 崩
    if body is None or result is None:
        print(result if result is not None else body)
        print("=EXIT= 2")
        return 2

    out = args.out or (os.path.splitext(args.report)[0] + "_核验报告.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    if args.json:
        jo = os.path.splitext(args.report)[0] + "_核验结果.json"
        with open(jo, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("JSON -> %s" % jo)
    print(body)
    print("=EXIT= 0")
    print("OUT=%s | parsed=%d red=%d normal=%d crit=%d light=%d mild=%d fallback=%d"
          % (out, result["parsed"], result["red_flags"], result["normal"],
             result["critical"], result["light"], result["mild"], result["fallback_ref"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
