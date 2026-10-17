# -*- coding: utf-8 -*-
"""DWG 图纸审查与问题记录 —— 自动核查引擎"""
import sys, re
sys.stdout.reconfigure(encoding="utf-8")

DOMAINS = [('图纸完整性', ['图框与签章齐全', '图纸目录一致', '会签栏完整', '版本号正确']), ('制图规范', ['线型与图层规范', '标注与尺寸完整', '图例符号统一', '比例标注一致']), ('专业一致性', ['各专业接口一致', '管线碰撞检查', '标高与坐标闭合', '材料表与图面一致']), ('问题记录', ['问题分类登记', '位置索引', '整改跟踪闭环'])]

EMPTY_TOKENS = ("", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
                "未确认", "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
                "null", "none", "？", "?")

def norm(s):
    return re.sub(r"[\s_\-—－・:：]+", "", str(s or "")).lower()

def parse(path):
    fields = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("- ") and ":" in line[2:]:
            k, _, v = line[2:].partition(":")
            fields[norm(k)] = v.strip()
    return fields

def get_text(fields, label):
    key = norm(label)
    if key in fields:
        return fields[key]
    for k, v in fields.items():
        if key and (key in k or k in key):
            return v
    return ""

def yesno(v):
    v = (v or "").strip()
    if not v:
        return None
    nv = norm(v)
    if nv in [norm(t) for t in EMPTY_TOKENS]:
        return None
    if nv.startswith("否") or nv == "no" or "未做" in v or "未落实" in v or "未取得" in v or "未设置" in v or "无" == nv[:1]:
        return False
    if nv.startswith("是") or nv == "yes" or nv == "已" or nv.startswith("已"):
        return True
    return None

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "testdata/样例.md"
    fields = parse(path)
    crit, risk, notes = [], [], []
    detail = []
    for dom, items in DOMAINS:
        lines = []
        for i, it in enumerate(items):
            raw = get_text(fields, it)
            v = yesno(raw)
            if v is False:
                if i == 0:
                    crit.append("%s > %s" % (dom, it))
                    lines.append("- **（阻断）** %s：不符合，须立即整改" % it)
                else:
                    risk.append("%s > %s" % (dom, it))
                    lines.append("- （风险） %s：不符合，须限期整改" % it)
            elif v is None and not raw:
                notes.append("%s > %s" % (dom, it))
                lines.append("- （待确认） %s：未填写，需补充核查" % it)
            else:
                lines.append("- （符合） %s" % it)
        detail.append((dom, lines))
    filled = sum(1 for k in fields if fields[k])
    if not filled:
        verdict, concl = "待补正", "采集表未填写任何字段，无法给出有效结论"
    elif crit:
        verdict, concl = "不通过", "存在 %d 项阻断性问题，须立即整改" % len(crit)
    elif risk:
        verdict, concl = "有风险", "存在 %d 项风险性问题，须限期整改" % len(risk)
    elif notes:
        verdict, concl = "待补正", "有 %d 项待确认，补充核查后可复跑" % len(notes)
    else:
        verdict, concl = "通过", "全部核查项均符合"
    out = []
    out.append("# DWG 图纸审查与问题记录报告")
    out.append("- 总体结论：**%s**（%s）" % (verdict, concl))
    out.append("- 阻断 %d 项 / 风险 %d 项 / 待确认 %d 项" % (len(crit), len(risk), len(notes)))
    out.append("")
    out.append("## 核查明细")
    for dom, lines in detail:
        out.append("### %s" % dom)
        out.extend(lines)
    out.append("")
    out.append("## 整改建议")
    if crit:
        for c in crit:
            out.append("- 【立即】%s：按规则要点立即整改并留存记录" % c)
    if risk:
        for r in risk:
            out.append("- 【限期】%s：制定整改计划并跟踪闭环" % r)
    if notes:
        out.append("- 【补充】将待确认项逐项核查填写后重新生成本报告")
    if not crit and not risk and not notes:
        out.append("- 维持现有管理措施，按周期复查")
    out.append("")
    out.append("> 本报告由自动核查引擎生成，结论以采集表填写内容为准。")
    print("\n".join(out))

if __name__ == "__main__":
    main()
