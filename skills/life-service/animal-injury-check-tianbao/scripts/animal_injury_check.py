#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动物伤人责任与索赔核查。

用法：
  python animal_injury_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python animal_injury_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "（", "(", "有/无", "是/否",
                     "选填", "填写"]

# 赔偿项目基准（用于测算区间；各地标准与实际票据为准）
COST_TABLE = [
    ("医疗费", ["医疗费", "治疗费", "手术费", "住院费", "药费", "检查费"]),
    ("误工费", ["误工费", "误工", "工资损失", "收入损失"]),
    ("护理费", ["护理费", "护理", "护工"]),
    ("交通费", ["交通费", "打车", "公交", "出行费"]),
    ("住院伙食补助", ["伙食", "餐费", "住院伙食"]),
    ("营养费", ["营养费", "营养"]),
    ("残疾赔偿金", ["残疾", "伤残", "残疾赔偿金"]),
    ("精神损害抚慰金", ["精神损害", "精神抚慰"]),
]

# 免责事由（饲养人/管理人能证明的例外）
EXEMPTIONS = [
    ("受害人故意", ["受害人故意", "故意逗", "主动挑逗", "故意激怒", "诱打"]),
    ("受害人重大过失", ["重大过失", "未经允许", "擅自进入", "翻越", "主动接近"]),
    ("第三人过错", ["第三人", "第三人过错", "他人挑逗", "有人踢", "他人", "别人踢", "挑逗"]),
    ("动物本能避险", ["本能", "受惊", "应激", "惊吓"]),
]

# 特殊主体的加重责任
SPECIAL_DUTY = [
    ("禁止饲养的烈性犬等", ["烈性犬", "危险犬", "禁养", "大型犬", "烈性"]),
    ("无主或流浪动物", ["无主", "流浪", "野狗", "流浪猫"]),
    ("动物经营者", ["养殖", "经营", "出售", "宠物店", "犬舍", "繁育"]),
    ("动物园或公园", ["动物园", "公园", "景区", "游玩"]),
]


def norm(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("：", ":").replace("（", "(").replace("）", ")")
    s = s.replace("，", ",").replace("。", ".")
    s = re.sub(r"\s+", "", s)
    return s.strip()


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_kv(text):
    kv = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                k, v = cells[0], "|".join(cells[1:]).strip()
                if set(k) <= set("-: ") or set(v) <= set("-: "):
                    continue
                if k and k not in kv:
                    kv[k] = v
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k, v = parts[0].strip(), parts[1].strip()
                if k and k not in kv:
                    kv[k] = v
    return kv


def get_text(kv, aliases):
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if norm(k) == na:
                return v.strip()
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if na in norm(k):
                return v.strip()
    return ""


def filled(v):
    if v is None:
        return False
    v = str(v).strip()
    if not v:
        return False
    if UNFILLED_MARK.search(v):
        return False
    for w in PLACEHOLDER_WORDS:
        if v.startswith(w):
            return False
    return True


def yes(v):
    n = norm(v)
    if n in ("有", "是", "已经", "已", "已完成", "已做", "可以", "能", "已鉴定", "已投保"):
        return True
    return n.startswith("已") or n.startswith("有")


def no(v):
    n = norm(v)
    if n in ("无", "否", "没有", "未", "未做", "false", "no", "正常"):
        return True
    return n.startswith("无") or n.startswith("未") or n.startswith("没有")


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知", "没填")


def hit_any(v, words):
    s = norm(v)
    if not filled(s):
        return None
    for w in words:
        if norm(w) in s:
            return True
    return False


def parse_num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("，", "")
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def fmt_num(x):
    if x is None:
        return "—"
    if abs(x - round(x)) < 1e-6:
        return str(int(round(x)))
    return ("%.2f" % x).rstrip("0").rstrip(".")


def money(x):
    return "¥" + fmt_num(x) if x is not None else "—"


def parse_date(s):
    if not s:
        return None
    m = DATE_RE.search(str(s))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def base_date(s):
    d = parse_date(s or "")
    return d or date.today()


def animal_kind(v):
    s = norm(v)
    if not filled(s):
        return "未填"
    for k in ("狗", "犬"):
        if norm(k) in s:
            return "狗"
    for k in ("猫",):
        if norm(k) in s:
            return "猫"
    for k in ("驴", "马", "牛", "羊", "猪"):
        if norm(k) in s:
            return "家畜"
    for k in ("猴", "蛇", "鸟", "鸡", "鸭"):
        if norm(k) in s:
            return "其他动物"
    return "未识别"


# ------------------------------------------------------------------ 一 责任定性
def checks_liability(f):
    out = []
    k = animal_kind(f["animal"])
    out.append(("动物类型", "待补正" if k in ("未识别", "未填") else "通过",
                "识别为**%s**。按《民法典》侵权责任编，**饲养的动物造成他人损害的，"
                "由动物饲养人或者管理人承担侵权责任**；属于无主或流浪动物的，"
                "由原饲养人承担，能查明管理人时由管理人承担。" % k))

    who = f["keeper"]
    if unknown(who):
        out.append(("责任主体是否明确", "待补正",
                    "对方是饲养人还是管理人未填。**责任主体必须先锁定**："
                    "登记在谁名下、谁实际喂养看门出庭，是起诉状的第一句话。"))
    elif yes(who):
        out.append(("责任主体是否明确", "通过",
                    "已锁定饲养人或管理人，可直接主张侵权责任。"))
    else:
        out.append(("责任主体是否明确", "不通过",
                    "**找不到饲养人/管理人**是最难的情形。"
                    "此时可通过物业监控、居委会走访、现场照片锁定住所与养犬人，"
                    "必要时申请公安协助查找。"))

    t = f["third_party"]
    if unknown(t):
        out.append(("是否存在第三人过错", "待补正",
                    "当时是否有第三人挑逗、驱赶动物未填——"
                    "**这是饲养人最常用的免责理由**，也是你需要提前排除的可能。"))
    elif yes(t):
        out.append(("是否存在第三人过错", "有风险",
                    "存在第三人过错情形，饲养人可能据此主张免责或减轻责任。"
                    "**要盯住责任划分比例**，必要时把第三人一起列为被告。"))
    else:
        out.append(("是否存在第三人过错", "通过", "无第三人过错事实，饲养人免责空间小。"))

    d = f["on_leash"]
    if unknown(d):
        out.append(("是否按规定管理动物", "待补正",
                    "是否拴绳、是否有警示标志、是否按规定登记免疫未填。"
                    "**未按规定管理会加重饲养人责任**，是重要的加分项。"))
    elif no(d):
        out.append(("是否按规定管理动物", "有风险",
                    "饲养人**未按规定管理动物**（未拴绳、无警示、没登记），"
                    "这会让其过错责任更明确，索赔谈判更有底气。"))
    else:
        out.append(("是否按规定管理动物", "通过", "饲养人已按规定管理，过错责任相对轻。"))
    return out


# ------------------------------------------------------------------ 二 免责事由
def checks_exempt(f):
    out = []
    s = f["provocation"]
    if not filled(s):
        out.append(("是否存在免责事由", "待补正",
                    "事发经过未填。**免责事由必须由饲养人举证**，"
                    "但你要先知道自己有没有留下把柄（如逗狗、自行翻入围栏）。"))
        return out
    hits = []
    for label, words in EXEMPTIONS:
        if hit_any(s, words) is True:
            hits.append(label)
    if not hits:
        out.append(("是否存在免责事由", "通过",
                    "事发经过中未出现挑逗、故意激怒、翻越等情形，"
                    "**饲养人几乎没有免责空间**。"))
    else:
        out.append(("是否存在免责事由", "有风险",
                    "经过中出现**%s**等因素，饲养人可能据此主张免责或减轻责任。"
                    "注意：**「只是受害人的错」不是当然免责**，"
                    "需要饲养人自己举证，且受害人有一般过失时通常也只是减轻责任。"
                    % "、".join(hits)))

    sp = f["special_duty"]
    if unknown(sp):
        out.append(("是否属于特殊责任类型", "待补正",
                    "是否属于禁养犬只、无主流浪动物、动物经营者或动物园园区未填，"
                    "这些类型的责任规则与举证压力不同。"))
    elif yes(sp):
        out.append(("是否属于特殊责任类型", "有风险",
                    "涉及**禁养烈性犬、动物经营者或动物园园区**。"
                    "经营者与园区通常面对更高的安全义务与举证要求，"
                    "**可主张的责任范围往往更大**。"))
    else:
        out.append(("是否属于特殊责任类型", "通过", "属一般饲养动物情形。"))
    return out


# ------------------------------------------------------------------ 三 赔偿测算
def calc_comp(f):
    res = {"可测算": False, "项目": [], "已知合计": 0.0, "缺项": [], "说明": ""}
    items = f["paid_items"]
    if not filled(items):
        res["说明"] = ("未填已支出金额，无法测算。按人身损害赔偿的一般项目，"
                       "可主张：医疗费、误工费、护理费、交通费、住院伙食补助、营养费，"
                       "构成伤残的还有残疾赔偿金，另有精神损害抚慰金。")
        return res
    got = norm(items)
    total = 0.0
    used = []
    missing = []
    for label, keys in COST_TABLE:
        if any(norm(kw) in got for kw in keys):
            used.append(label)
        else:
            missing.append(label)
    # 从文本里抓金额：按"项目+数字"或纯数字
    nums = re.findall(r"\d+(?:\.\d+)?", got)
    if nums:
        total = sum(float(x) for x in nums)
        res["可测算"] = True
        res["已知合计"] = round(total, 2)
    res["项目"] = used
    res["缺项"] = missing
    res["说明"] = ("从已填支出中识别到 %s，合计 %s；尚缺 %s 等项目的凭证，"
                   "**缺项不等于不能主张，是还没收集到票据**。"
                   % ("、".join(used) if used else "（未识别到具体项目）",
                      money(total), "、".join(missing[:4])))
    return res


def checks_amount(f, calc):
    out = []
    if not calc["可测算"]:
        out.append(("赔偿金额测算", "待补正", calc["说明"]))
        return out
    out.append(("已支出金额", "通过",
                "已识别项目：%s，合计 **%s**（按填写内容中的数字汇总，**以票据为准**）。"
                % ("、".join(calc["项目"]) if calc["项目"] else "未细分",
                   money(calc["已知合计"]))))
    if calc["缺项"]:
        out.append(("赔偿项目缺口", "有风险",
                    "尚缺 %s 等项目的凭证。**没有票据的项目主张起来会很难**，"
                    "病历、发票、工资流水、护理支出凭证都要留。"
                    % "、".join(calc["缺项"][:4])))
    else:
        out.append(("赔偿项目缺口", "通过", "赔偿项目凭证基本齐全。"))

    if unknown(f["appraisal"]):
        out.append(("是否做伤情鉴定", "待补正",
                    "是否做伤情鉴定未填。**能不能拿到伤残等级，直接决定有没有残疾赔偿金**，"
                    "建议在治疗终结、伤情稳定后尽早做，不要拖到恢复完。"))
    elif yes(f["appraisal"]):
        out.append(("是否做伤情鉴定", "通过",
                    "已做鉴定，**结论等级直接决定赔偿上限**，务必附鉴定文书原件。"))
    else:
        out.append(("是否做伤情鉴定", "有风险",
                    "未做鉴定。轻伤、伤残等级对应的赔偿差距很大，"
                    "**建议先做鉴定再谈赔偿**，否则容易按低标准和解。"))

    if unknown(f["insurance"]):
        out.append(("对方是否投保", "待补正", "对方是否投保 animal 责任险或第三方责任险未填。"))
    elif yes(f["insurance"]):
        out.append(("对方是否投保", "通过",
                    "有保险的，**可直接向保险公司索赔而不必先找饲养人扯皮**，"
                    "保存报案号与理赔资料。"))
    else:
        out.append(("对方是否投保", "有风险", "对方无保险，赔偿只能向饲养人本人主张。"))
    return out


# ------------------------------------------------------------------ 四 处置与取证
def checks_treatment(f):
    out = []
    for label, key, why in [
        ("是否及时就医", "medical",
         "**无论伤情轻重都要就医留痕**，病历与诊断证明是最核心的证据；"
         "不就医会让后续索赔缺乏依据。"),
        ("是否接种疫苗", "vaccine",
         "动物致伤必须及时接种**狂犬病疫苗**；伤情重的还需破伤风免疫，"
         "接种记录既是医疗必需，也是损害证明。"),
        ("是否拍照留证", "photo",
         "伤情照片要**带时间地点水印、多角度、保留原图**；"
         "含伤口特写与整体状态，必要时录一段现场视频。"),
        ("是否报警", "police",
         "**报警记录是最快固定事实的方式**，可要求出警回执并做笔录；"
         "虽不必然立案，但记录本身是重要证据。"),
    ]:
        v = f.get(key)
        if unknown(v):
            out.append((label, "待补正", "%s未填。%s" % (label, why)))
        elif yes(v):
            out.append((label, "通过", "%s已完成。%s" % (label, why)))
        else:
            out.append((label, "有风险", "**%s未做**。%s" % (label, why)))
    return out


# ------------------------------------------------------------------ 五 维权路径
def checks_path(f):
    out = []
    steps = [
        ("协商", f["negotiate"],
         "先与饲养人直接谈：明确责任、赔偿项目与金额、支付时间，"
         "**谈成要写书面协议并分期付清**，不要只要口头承诺。"),
        ("社区与物业调解", f["mediate"],
         "居委会、物业、派出所可调解并出具记录，**调解不成也是证据**（对方态度）。"),
        ("12315 消费投诉", f["market"],
         "属消费服务或生活服务纠纷的可向 12315 投诉，"
         "对饲养人施加合规压力。"),
        ("诉讼", f["lawsuit"],
         "**人身损害赔偿纠纷由侵权行为地或被告住所地法院管辖**，"
         "可主张医疗费、误工费、护理费等实际损失与伤残相关赔偿。"),
    ]
    for label, v, body in steps:
        if unknown(v):
            out.append((label, "待补正", "是否走过%s未填。%s" % (label, body)))
        elif yes(v):
            out.append((label, "通过", body + " —— 已走过，保留过程与结果记录。"))
        else:
            out.append((label, "有风险", body + " —— 尚未走，**建议按顺序推进，不要一开始就起诉**。"))
    return out


# ------------------------------------------------------------------ 六 时效
def checks_time(f, today):
    out = []
    d = parse_date(f["accident_date"])
    if d:
        deadline = d + timedelta(days=365 * 3)
        left = (deadline - today).days
        out.append(("民事诉讼时效", "有风险" if left < 0 else "通过",
                    "事发于 %s，一般民事诉讼时效 3 年，到期日 %s，%s。"
                    % (d.isoformat(), deadline.isoformat(),
                       ("已过 %d 天" % -left) if left < 0 else ("还剩 %d 天" % left))))
    else:
        out.append(("民事诉讼时效", "待补正",
                    "未填事发日期，无法倒计时。**别拖，鉴定与索赔都要时间**。"))
    if unknown(f["treatment_done"]):
        out.append(("治疗是否终结", "待补正",
                    "治疗是否已终结未填。**伤情稳定后应尽快做鉴定**，"
                    "鉴定太晚可能因恢复而无法准确评估。"))
    elif yes(f["treatment_done"]):
        out.append(("治疗是否终结", "通过", "治疗已终结或伤情已稳定，可安排鉴定。"))
    else:
        out.append(("治疗是否终结", "有风险",
                    "治疗尚未终结。**不要急着做鉴定**：过早鉴定可能因后续恢复导致"
                    "等级评估偏差，等伤情稳定、治疗结束或达到临床治愈标准后再鉴定更准。"))
    return out


# ------------------------------------------------------------------ 七 证据
EVIDENCE = [
    ("事故事实证据", ["报警", "出警", "回执", "笔录", "现场", "监控", "视频", "照片"]),
    ("伤情证据", ["病历", "诊断", "住院", "病历首页", "检查", "诊断证明"]),
    ("费用凭证", ["发票", "费用清单", "收据", "明细"]),
    ("护理与误工", ["护理", "护工", "工资", "误工", "流水", "收入证明"]),
    ("鉴定文书", ["鉴定", "伤残", "等级", "司法鉴定", "伤情鉴定"]),
    ("责任主体证据", ["登记", "户籍", "物业", "居委会", "喂养", "饲养人", "视频"]),
]


def has_content(s):
    for part in str(s or "").split("|"):
        if filled(part):
            return True
    return False


def checks_evidence(f):
    out = []
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    if not has_content(got):
        out.append(("证据总览", "待补正",
                    "已有证据既没勾选也没写清单。**责任认定靠证据**："
                    "谁养的狗、怎么伤的、伤到什么程度，三件事都要有材料。"
                    "请逐项对照补齐。"))
        return out
    for label, keys in EVIDENCE:
        hit = [k for k in keys if k in got]
        if hit:
            out.append((label, "通过",
                        "已具备：%s。原件留存、复印件提交，**按时间顺序编号成册**。"
                        % "、".join(hit)))
        else:
            out.append((label, "有风险", "尚无%s证据，这类缺口会直接削弱主张，请尽快补齐。" % label))
    return out


def evidence_gap(f):
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    gaps = []
    if has_content(got):
        for label, keys in EVIDENCE:
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in EVIDENCE]
    if not yes(f["police"]):
        gaps.append("事故事实证据")
    if not yes(f["medical"]):
        gaps.append("伤情证据")
    seen = set()
    res = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            res.append(g)
    return res


EVID_FIX = {
    "事故事实证据": "报警要回执或做笔录；调取小区/街面监控；现场多角度拍照",
    "伤情证据": "正规医院就诊，留病历、诊断证明、检查报告与发票",
    "费用凭证": "收齐挂号费、检查费、药费、住院费等全部票据",
    "护理与误工": "护理支出凭证；误工则准备工资流水与单位误工证明",
    "鉴定文书": "在伤情稳定后做伤残等级鉴定，保留鉴定文书原件",
    "责任主体证据": "物业登记、居委会走访记录、监控视频、居委会出具的说明",
    "责任主体": "请居委会或物业出具饲养人情况说明，必要时申请公安协助查找",
}


# ------------------------------------------------------------------ 路径
def path_steps(f):
    k = animal_kind(f["animal"])
    out = [("第 1 步（先止损）",
            "**先就医、先接种疫苗、先拍照**。狂犬病疫苗不能拖，"
            "病历和照片越早固定越好，拖到伤口愈合就对不上时间线。"),
           ("第 2 步（锁定责任主体）",
            "查清**谁养的、谁管理的**：小区登记、居委会走访、物业监控、"
            "邻里证言。找不到人的，先请居委会出具说明并保留物业记录。"),
           ("第 3 步（报警留痕）",
            "报警并要求**出警回执与笔录**。虽不必然立案，"
            "但这份记录是后续所有主张的底座。"),
           ("第 4 步（治疗终结后做鉴定）",
            "**伤情稳定后尽快做伤残等级鉴定**，等级直接决定赔偿上限；"
            "鉴定太晚可能因恢复而无法准确评估。"),
           ("第 5 步（先协商后调解）",
            "与饲养人谈赔偿：医疗费、误工费、护理费、交通费、伙食补助、营养费，"
            "构成伤残的加残疾赔偿金，另主张精神损害抚慰金。"
            "**谈成要书面协议并分期付清**。"),
           ("第 6 步（投诉与调解）",
            "协商不成走居委会/物业调解、12315 投诉，"
            "让第三方施压；对饲养人态度恶劣的，可同步向公安机关反映。"),
           ("第 7 步（诉讼）",
            "仍无法解决的，向**侵权行为地或被告住所地法院**起诉，"
            "主张医疗费、误工费、护理费等实际损失与伤残相关赔偿；"
            "**是否值得走请先咨询律师**。")]
    if k == "狗":
        out.append(("特别提醒",
                    "犬类致害还需关注**当地禁止饲养烈性犬的规定**："
                    "若属禁养犬只，饲养人责任更重，**可向当地农业农村部门或城管举报违规饲养**。"))
    return out


def todo_list(f, results):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if not yes(f["medical"]):
        extra.append(("立即就医", "无论轻重都要就诊留痕，并接种狂犬病疫苗"))
    if not yes(f["vaccine"]):
        extra.append(("接种狂犬病疫苗", "越早越好，记录接种凭证"))
    if not yes(f["photo"]):
        extra.append(("拍照留证", "带时间地点水印、多角度、保留原图"))
    if not yes(f["police"]):
        extra.append(("报警并要回执", "110 → 出警回执 + 笔录"))
    if not yes(f["appraisal"]):
        extra.append(("做伤情鉴定", "伤情稳定后尽快做伤残等级鉴定"))
    extra.append(("锁定饲养人", "物业登记 + 居委会走访 + 监控，请出具书面说明"))
    extra.append(("收齐全部票据", "医疗、护理、交通、误工证明，一张都别丢"))
    seen = set()
    res = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        res.append((n, s))
    return res


# ------------------------------------------------------------------ 报告
SECTIONS = [
    "二、责任主体与法律定性",
    "三、免责事由核查",
    "四、赔偿项目与金额测算",
    "五、伤情处置与取证",
    "六、维权路径与调解",
    "七、时效与鉴定时机",
    "八、证据清单与缺口",
]


def render(f, results, calc, steps, todos, today, gaps):
    L = []
    L.append("# 动物伤人责任与索赔核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 动物：%s" % animal_kind(f["animal"]))
    L.append("- 事发时间：%s" % (f["accident_date"] or "未填"))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在明确障碍（责任主体不明或关键动作缺失），先解决再谈赔偿。**")
    elif calc["可测算"]:
        L.append("**判定：可主张的已支出赔偿约 %s（以票据为准），"
                 "另有伤残赔偿与精神损害抚慰金需以鉴定结论确定。**"
                 % money(calc["已知合计"]))
    elif risk:
        L.append("**判定：责任方向较清楚，但证据或时机还没到位，建议先取证再谈赔偿。**")
    else:
        L.append("**判定：采集表关键项未填，暂时给不出确定结论；"
                 "请把事发经过、动物类型、是否就医与支出填完再重跑。**"
                 "**未填的一律不算通过。**")
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(todo))
    L.append("")
    for name, _s, msg in bad[:5]:
        L.append("- **%s**：%s" % (name, msg.replace("**", "")))
    for name, _s, msg in risk[:5]:
        L.append("- %s：%s" % (name, msg.replace("**", "")))
    L.append("")

    for (title, rows), t in zip(results, SECTIONS):
        if not rows:
            L.append("## %s" % t)
            L.append("")
            L.append("暂无可核查项（未填不按通过处理）。")
            L.append("")
            continue
        L.append("## %s" % t)
        L.append("")
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for row in rows:
            if len(row) < 3:
                continue
            name, state, msg = row[0], row[1], row[2]
            if not isinstance(msg, str):
                msg = str(msg)
            L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
        L.append("")

    L.append("## 九、维权路径排序")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 十、证据缺口速查")
    L.append("")
    if not gaps:
        L.append("当前填写的证据已较完整。")
    else:
        L.append("| 缺失类别 | 补法 |")
        L.append("|---|---|")
        for g in gaps[:12]:
            L.append("| %s | %s |" % (g, EVID_FIX.get(g, "按第九段操作卡补齐")))
    L.append("")

    L.append("## 十一、待办补正动作")
    L.append("")
    if not todos:
        L.append("当前未发现必须补正的事项。")
    else:
        L.append("| 动作 | 状态 |")
        L.append("|---|---|")
        for n, s in todos:
            L.append("| %s | %s |" % (n, s))
    L.append("")

    L.append("## 边界与纪律")
    L.append("")
    L.append("- 依**通用规则**整理，**不替代律师意见**；"
             "赔偿标准、禁养犬只种类与各地规定**以当地农业农村、城管等部门口径为准**。")
    L.append("- 报告中的金额为按已填票据汇总的**预估**，**不得作为索赔主张的最终数额**。")
    L.append("- 不预测公安机关是否立案、法院是否支持具体金额。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 本结果依通用规则整理，不替代专业意见，最终以主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps, calc):
    return {
        "核查日期": today.isoformat(),
        "动物类型": animal_kind(f["animal"]),
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "赔偿测算": {
            "可测算": calc["可测算"],
            "已知合计": calc["已知合计"],
            "已识别项目": calc["项目"],
            "缺失项目": calc["缺项"],
        },
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "animal": get_text(kv, ["动物种类", "伤人动物", "动物类型", "是什么动物"]),
        "accident_date": get_text(kv, ["事发时间", "被咬时间", "受伤时间", "事发日期"]),
        "keeper": get_text(kv, ["是否已锁定饲养人或管理人", "是否找到饲养人", "饲养人是否明确"]),
        "third_party": get_text(kv, ["是否存在第三人过错", "是否有人挑逗", "第三人过错"]),
        "on_leash": get_text(kv, ["是否按规定管理动物", "是否拴绳", "是否按规定管理"]),
        "provocation": get_text(kv, ["事发经过", "当时情况", "事发情形", "经过"]),
        "special_duty": get_text(kv, ["是否属于禁养犬只或动物经营者", "是否禁养犬", "是否动物经营场所"]),
        "medical": get_text(kv, ["是否及时就医", "是否就医", "就诊情况"]),
        "vaccine": get_text(kv, ["是否接种疫苗", "是否接种狂犬病疫苗", "疫苗接种"]),
        "photo": get_text(kv, ["是否拍照留证", "是否拍照", "伤情照片"]),
        "police": get_text(kv, ["是否报警", "是否110", "报警情况"]),
        "appraisal": get_text(kv, ["是否做伤情鉴定", "是否鉴定", "伤残鉴定"]),
        "insurance": get_text(kv, ["对方是否投保", "是否有动物责任险", "是否投保"]),
        "paid_items": get_text(kv, ["已支出金额与项目", "已花费金额", "医疗费与支出"]),
        "treatment_done": get_text(kv, ["治疗是否终结", "治疗是否结束", "伤情是否稳定"]),
        "negotiate": get_text(kv, ["是否与饲养人协商", "是否协商", "协商情况"]),
        "mediate": get_text(kv, ["是否经过社区或物业调解", "是否调解", "调解情况"]),
        "market": get_text(kv, ["是否已向12315投诉", "是否12315", "12315"]),
        "lawsuit": get_text(kv, ["是否已起诉", "是否诉讼", "诉讼情况"]),
        "evidence_owned": get_text(kv, ["已有证据勾选", "证据勾选"]),
        "evidence_desc": get_text(kv, ["证据清单", "已有证据", "材料清单"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    kv = build_kv(read_text(args.input))
    today = base_date(args.base)
    f = build_fields(kv)

    missing = []
    if not filled(f["animal"]):
        missing.append("动物种类")
    if not filled(f["accident_date"]):
        missing.append("事发时间")
    if not filled(f["provocation"]):
        missing.append("事发经过")

    calc = calc_comp(f)
    results = [
        ("责任主体与法律定性", checks_liability(f)),
        ("免责事由核查", checks_exempt(f)),
        ("赔偿项目与金额测算", checks_amount(f, calc)),
        ("伤情处置与取证", checks_treatment(f)),
        ("维权路径与调解", checks_path(f)),
        ("时效与鉴定时机", checks_time(f, today)),
        ("证据清单与缺口", checks_evidence(f)),
    ]
    steps = path_steps(f)
    todos = todo_list(f, results)
    gaps = evidence_gap(f)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today, gaps, calc),
                         ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, calc, steps, todos, today, gaps)
    if missing:
        rep += ("\n> 提示：关键信息缺失——%s，相关判断已按\"待补正\"处理，"
                "补齐后重跑可得到确定结论。\n" % "、".join(missing))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(rep)
        print("已写出 %s" % args.out)
    else:
        sys.stdout.write(rep)
    return 2 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
