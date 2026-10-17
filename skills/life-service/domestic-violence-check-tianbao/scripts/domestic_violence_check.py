#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""家庭暴力取证与人身安全保护令申请核查。

用法：
  python domestic_violence_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python domestic_violence_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "（", "(", "有/无", "是/否"]

# 危险进行中的信号词
URGENT_WORDS = ["正在", "现在还", "今晚", "当前仍在", "尚未离开", "还在家里", "昨晚又", "今天又"]

PROTECTION_ITEMS = "禁止实施家庭暴力、禁止骚扰跟踪接触、责令迁出住所"


# ------------------------------------------------------------------ 解析
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
    """解析 markdown 表格行与 '字段：值' 行，保留表头。"""
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
    """最长别名优先匹配。"""
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
    v = (v or "").strip()
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
    return n in ("有", "是", "已经", "已", "已完成", "已做", "申请了", "已申请", "申请了")


def no(v):
    n = norm(v)
    return n in ("无", "否", "没有", "未", "未做", "未报警", "未就医", "false", "no")


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知", "没填")


def is_yesish(v):
    return yes(v) or (filled(v) and "已" in norm(v)[:2])


def has_content(s):
    """把多列拼接后的字符串归一化：全是分隔符（如 "|"）视为没有内容。"""
    for part in str(s or "").split("|"):
        if filled(part):
            return True
    return False


def parse_num(s):
    if not s:
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


# ------------------------------------------------------------------ 形态识别
FORM_LABEL = [
    ("肢体暴力", ["打", "推搡", "扇", "拳", "殴打", "掐", "拽头发", "踢", "勒", "摔东西砸到人"]),
    ("精神暴力", ["骂", "辱骂", "威胁", "恐吓", "贬低", "人格侮辱", "吼", "精神"]),
    ("控制与跟踪", ["限制", "不许", "不准", "控制", "跟踪", "查岗", "没收手机", "不让上班", "不让出门"]),
    ("经济控制", ["不给钱", "经济控制", "掌握工资", "银行卡", "花销", "生活费"]),
]

REL_RULES = [
    ("夫妻", ["夫妻", "配偶", "结婚", "婚姻"],
     "家庭成员（夫妻）",
     "配偶之间的家庭暴力是典型情形，可向法院申请人身安全保护令。"),
    ("亲属", ["父母", "子女", "兄弟", "姐妹", "儿媳", "女婿", "祖", "孙", "公婆", "岳"],
     "家庭成员（亲属）",
     "家庭成员之间的暴力属于家庭暴力，可申请人身安全保护令。"),
    ("同居或前伴侣", ["同居", "未婚", "前男友", "前女友", "前男", "前女", "恋人", "恋爱"],
     "共同生活或前伴侣（非夫妻）",
     "**同居、前男女友等共同生活关系同样适用**——与配偶以外**共同生活的人**发生暴力，"
     "以及频繁往来共同生活的情形，按现行反家庭暴力相关规定也可申请人身安全保护令；"
     "是否受理以受理法院口径为准，但**报警、就医、妇联求助等路径不受关系限制**。"),
    ("学校/其他", ["班主任", "老师", "同学", "学生", "学校", "幼儿园"],
     "非家庭（学校/其他）",
     "学校、幼儿园及其工作人员发现未成年人遭受家庭暴力的，负有向公安机关、民政等有关部门"
     "报告的义务；此类情形同步走报案与民政救助路径。"),
]


def form_match(desc):
    s = desc or ""
    return [label for label, keys in FORM_LABEL if any(k in s for k in keys)]


def cohab_type(rel):
    s = rel or ""
    if not filled(s):
        return ("待确认", "关系未填，无法判断是否属于家庭暴力的保护范围。")
    for label, keys, disp, why in REL_RULES:
        if any(k in s for k in keys):
            return (disp, why)
    return ("待确认", "关系填写不明确，请写明：夫妻 / 同居或前男女友 / "
                      "共同生活的其他家庭成员 / 学校或老师 / 其他。")


# ------------------------------------------------------------------ 安全优先级
def checks_safety(f):
    out = []
    narrative = f["narrative"] or ""
    urgent = any(k in narrative for k in URGENT_WORDS)
    if urgent:
        out.append(("当前是否仍处危险中", "不通过",
                    "事发描述中出现\"正在/今晚/尚未离开/昨晚又\"等字样，提示暴力可能仍在进行或刚发生。"
                    "**第一步永远是安全**：优先离开现场（去公共场所、亲友家、单位），或拨打 110；"
                    "不要为了保存证据而继续留在冲突环境中。"))
    else:
        out.append(("当前是否仍处危险中", "通过",
                    "按填写内容看，暴力并非正在进行。但仍建议保持警惕，"
                    "必要时把重要证件、手机充电器、现金放在容易拿走的地方。"))

    left = f["left_site"]
    if is_yesish(left):
        out.append(("是否已脱离现场", "通过",
                    "已到安全处。请继续留在安全场所，随后按报警→就医顺序固定证据。"))
    elif no(left) or "未" in (left or ""):
        out.append(("是否已脱离现场", "不通过",
                    "**仍与对方处于同一现场是最危险的状态**。按优先级："
                    "① 到公共场所、亲友家、单位宿舍等安全处；② 拨打 110；"
                    "③ 向邻居、物业、楼下保安求助并请他们出面。"))
    else:
        out.append(("是否已脱离现场", "待补正", "是否已离开现场（或已到安全处）未填，这是安全动作的第一项。"))

    call = f["called_110"]
    if yes(call) or "已报警" in (call or ""):
        out.append(("是否拨打 110 报警", "通过",
                    "已报警。**请务必索要报警回执或接警编号**（现场给的单据，或事后回拨报办查询），"
                    "并明确要求**制作询问笔录**——笔录由公安机关形成，是后续认定与索赔最有力的证据。"))
    elif no(call) or "未" in (call or ""):
        out.append(("是否拨打 110 报警", "不通过",
                    "**未报警**。报警记录是认定家庭暴力最直接的材料之一；请尽快拨打 110，"
                    "到场后说明身份与被打经过，明确要求：① 出具报警回执或受案编号；"
                    "② 制作询问笔录；③ 情况需要时出具伤情初步意见。报警本身就是最强的制止手段。"))
    else:
        out.append(("是否拨打 110 报警", "待补正", "是否报过警未填，这决定证据链的起点。"))

    note = f["police_note"]
    if yes(note) or "笔录" in (note or "") or "已做" in (note or ""):
        out.append(("公安机关笔录", "通过",
                    "已做笔录（%s）。笔录会记载时间、地点、经过与伤情，请你核对内容准确后再签字；"
                    "如记录与事实不符，可要求更正或补充陈述。" % (note or "")))
    elif no(note) or ("已报警" not in (call or "") and no(call)):
        out.append(("公安机关笔录", "有风险",
                    "尚未形成笔录。**做笔录是报警环节里最有价值的一步**，"
                    "请下次报警时主动说\"我需要做笔录\"，并留存接警编号以便回查。"))
    else:
        out.append(("公安机关笔录", "待补正", "是否已做笔录未填。"))
    return out


# ------------------------------------------------------------------ 证据
def evidence_items():
    return [
        ("报警类", ["报警回执", "接警编号", "受案回执", "询问笔录", "接处警登记表"]),
        ("伤情类", ["伤情照片", "门诊病历", "急诊记录", "诊断证明", "验伤单", "法医鉴定"]),
        ("影像类", ["录音", "录像", "视频"]),
        ("文字类", ["微信记录", "短信", "聊天截图", "威胁信息"]),
        ("物证类", ["损坏物品", "撕坏衣物", "现场照片"]),
        ("人证类", ["邻居", "物业", "亲友", "证人"]),
        ("记录类", ["妇联介入", "社区调解", "社工记录", "心理咨询"]),
        ("法律类", ["保护令申请书", "裁定书", "起诉状"]),
    ]


GAP_FIX = {
    "报警类": "拨打 110 并要求做笔录、出具报警回执或接警编号",
    "伤情类": "立即到正规医院就诊并说明致伤原因，必要时申请伤情鉴定",
    "影像类": "争吵中录音录像，保留手机原始文件（不要只转存后删原图）",
    "文字类": "微信/短信中的威胁、辱骂记录不要删，截图并做录屏保全",
    "物证类": "被砸坏的家具、撕坏的衣物原地拍照，注明时间地点",
    "人证类": "请邻居、物业、亲友作证，或请其留下书面证言与联系方式",
    "记录类": "到居委会/妇联反映并要求记录在册，心理咨询留就诊记录",
    "法律类": "写好保护令申请书，保留法院送达回执与裁定书",
    "伤情照片": "多角度 + 时间地点水印 + 保留原图",
    "就医病历": "正规医院就诊，病历与诊断证明写明致伤成因",
    "报警笔录与回执": "110 出警后要求形成笔录并给回执",
    "关系证明": "户口本/结婚证/居住证明等，证明与该人的共同生活或亲属关系",
}


def checks_evidence(f):
    out = []
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    if not has_content(got):
        out.append(("证据总览", "待补正",
                    "已有证据既没勾选、也没写清单，无法判断证据链是否完整。"
                    "请逐项对照第六节表格勾选你手上已有的材料；一项都没有的也要如实写\"无\"。"))
        return out
    for label, keys in evidence_items():
        hit = [k for k in keys if k in got]
        if hit:
            out.append((label + "证据", "通过",
                        "已具备：%s。请原件拍照、复印件留存，按时间顺序整理成册，"
                        "每份注明\"证据名称—来源—证明目的\"。" % "、".join(hit)))
        else:
            out.append((label + "证据", "有风险",
                        "尚无%s证据。这类缺口会明显削弱后续主张，请尽快补齐。" % label))
    return out


def evidence_gap(f):
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    gaps = []
    if has_content(got):
        for label, keys in evidence_items():
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in evidence_items()]
    if not is_yesish(f["photo"]):
        gaps.append("伤情照片")
    if not is_yesish(f["medical"]):
        gaps.append("就医病历")
    if not (yes(f["called_110"]) or "已报警" in (f["called_110"] or "")):
        gaps.append("报警笔录与回执")
    if not filled(f["relation"]):
        gaps.append("关系证明")
    seen = set()
    out = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            out.append(g)
    return out


# ------------------------------------------------------------------ 报警与就医
def checks_medical(f):
    out = []
    photo = f["photo"]
    if is_yesish(photo) or "有" in (photo or ""):
        out.append(("伤情照片规范", "通过",
                    "已拍伤情照片。规范要求：**带时间地点水印**、多角度（正面/侧面/整体）、"
                    "近景拍清伤口、远景拍出人整体状态与所处环境、留存原图"
                    "（不要只发微信后删掉原图）。照片的时间戳本身就是证据链的一环。"))
    elif no(photo) or "无" in (photo or ""):
        out.append(("伤情照片规范", "不通过",
                    "**未拍伤情照片是最大的证据缺口**。请立刻在自然光下拍：伤口特写 + 全身照 + "
                    "含时间地点水印的原图，并开启手机\"位置信息\"保存。当天拍最好，"
                    "拖久伤口愈合就对不上时间线。"))
    else:
        out.append(("伤情照片规范", "待补正", "是否拍摄伤情照片未填。"))

    medical = f["medical"]
    if is_yesish(medical) or "已" in (medical or ""):
        out.append(("就医记录", "通过",
                    "已就医。请向医生**如实说明致伤成因**（例如\"被配偶打伤\"），"
                    "**医院记录里的致伤原因表述非常关键**；同时留存病历复印件、诊断证明、"
                    "检查报告与发票，均可作为证据提交。"))
        reason = f["record_reason"]
        if yes(reason) or "写明" in (reason or "") or "写了" in (reason or ""):
            out.append(("病历致伤原因表述", "通过",
                        "病历/诊断证明已写明致伤原因，证据力最强。"))
        elif no(reason) or "未" in (reason or "") or "没写" in (reason or "") \
                or "没有写" in (reason or "") or "未写明" in (reason or ""):
            out.append(("病历致伤原因表述", "有风险",
                        "病历或诊断证明未写明致伤原因（或当时未说明）。"
                        "可**带着已有病历回到原就诊科室补一份伤情说明**，"
                        "或请医生在病历中补充\"患者自述系他人殴打致伤\"之类表述，"
                        "补记前先咨询医院能否修改。"))
        else:
            out.append(("病历致伤原因表述", "待补正",
                        "病历是否写明致伤原因未填——这是就医环节最容易被忽略、却最要紧的一处。"))
    elif no(medical) or "未" in (medical or ""):
        out.append(("就医记录", "不通过",
                    "未就医。**请立即到正规医院急诊或外科就诊**，即使自认为\"没伤\"也应就诊留痕。"
                    "医生记录的伤情与成因是认定家暴的核心材料；没有外伤也不代表不能认定，"
                    "但就医记录能显著补强证据链。"))
    else:
        out.append(("就医记录", "待补正", "是否去医院就诊未填。"))

    rec = f["recording"]
    if yes(rec) or "有" in (rec or ""):
        out.append(("录音录像", "通过",
                    "已有争吵或威胁的录音录像。**留存手机原始文件**，不要只上传云端后删原文件；"
                    "剪辑过的片段证据力会打折扣。"))
    elif no(rec) or "无" in (rec or ""):
        out.append(("录音录像", "有风险",
                    "无录音录像。下次冲突可尝试在确保自身安全的前提下用手机录音（先开录音再对话），"
                    "内容包含对方自报身份与威胁语句的最有价值。"))
    else:
        out.append(("录音录像", "待补正", "是否有争吵/威胁的录音录像未填。"))

    chat = f["chat"]
    if yes(chat) or "有" in (chat or ""):
        out.append(("威胁辱骂文字记录", "通过",
                    "已有微信/短信威胁或辱骂记录。**不要删除**，"
                    "做截图 + 录屏保全（录屏能看到完整对话界面与时间），并导出原始记录。"))
    elif no(chat) or "无" in (chat or ""):
        out.append(("威胁辱骂文字记录", "有风险",
                    "无威胁辱骂的文字记录。有的话请务必别删；目前没有也不代表少了一条路——"
                    "报警笔录、病历、证人证言可以补位。"))
    else:
        out.append(("威胁辱骂文字记录", "待补正", "是否有微信/短信威胁辱骂记录未填。"))

    wit = f["witness"]
    if yes(wit) or "有" in (wit or ""):
        out.append(("证人", "通过",
                    "已有证人。请记下证人姓名与联系方式，"
                    "必要时请其出具书面证言；法院也认可证人证言。"))
    elif no(wit) or "无" in (wit or ""):
        out.append(("证人", "有风险",
                    "无证人。家暴多发生在私密空间，证人稀缺是常态——可用报警回执、"
                    "妇联/社区记录、物业监控、邻居证言相互补强。"))
    else:
        out.append(("证人", "待补正", "是否有证人（邻居/物业/亲友）未填。"))
    return out


# ------------------------------------------------------------------ 保护令
def order_apply(f):
    out = []
    judged = f["protection_applied"]
    if yes(judged) or "已" in (judged or ""):
        out.append(("人身安全保护令（是否已申请）", "通过",
                    "已提出申请或已走申请流程（%s）。**保护令由人民法院作出**，"
                    "作出后**可由公安机关协助执行**；对方违反裁定的，"
                    "可就其行为请求拘留、罚款，构成犯罪的依法追究刑事责任。"
                    % (f["protection_status"] or "请填写具体进展")))
        got = f["protection_order"]
        if is_yesish(got) or "已" in (got or ""):
            out.append(("是否已取得裁定书", "通过",
                        "已取得裁定书，请保管原件并留存送达回证；有效期以裁定书载明为准"
                        "（实践中常见为数个月），到期需要延续的及时重新申请。"))
        elif no(got) or "未" in (got or ""):
            out.append(("是否已取得裁定书", "有风险",
                        "已申请但尚未取得裁定书。法院审查期间可主动联系承办法官补充材料；"
                        "紧急情况下可说明面临现实危险。"))
        else:
            out.append(("是否已取得裁定书", "待补正", "是否已取得裁定书未填。"))
    elif no(judged) or "未" in (judged or ""):
        out.append(("人身安全保护令（是否已申请）", "待补正",
                    "尚未申请。**人身安全保护令由人民法院作出**："
                    "① 申请人**自己**向法院直接申请；"
                    "② 部分地方可向居住地或家庭暴力发生地的**基层人民法院**申请；"
                    "③ 居委会/村委会、妇联、学校、幼儿园、医疗机构等**可以代为申请**。"
                    "可请求的事项通常包括：%s。"
                    "**有效期以裁定书为准**（实践中常见为数个月，届满可续）。"
                    "具体受理条件、管辖与材料清单**以受理法院与当地现行规定为准**。"
                    % PROTECTION_ITEMS))
    else:
        out.append(("人身安全保护令（是否已申请）", "待补正", "是否申请过人身安全保护令未填。"))

    aid = f["legal_aid"]
    if yes(aid) or "已" in (aid or ""):
        out.append(("法律援助", "通过", "已获得法律援助，律师可代写申请书并代理立案。"))
    elif no(aid) or "未" in (aid or ""):
        out.append(("法律援助", "待补正",
                    "未申请法律援助。符合当地法律援助经济困难标准的，可向**法律援助机构**申请；"
                    "也可通过妇联获取指引。**是否符合条件由当地法律援助机构认定**。"))
    else:
        out.append(("法律援助", "待补正", "是否申请法律援助未填。"))
    return out


# ------------------------------------------------------------------ 其他渠道
def checks_other(f):
    out = []
    for key, label, body in [
        ("women_fed", "妇联（12338）",
         "拨打 **12338** 妇女维权热线，可咨询取证、保护令申请、调解与转介；"
         "妇联可协助代写材料、出具情况说明，并联系社区介入。"),
        ("community", "居委会/村委会/社区",
         "到社区综治窗口或居委会反映，**要求介入并在台账上记录**；"
         "社区调解记录、情况证明都是可用材料，还能协助代为申请保护令。"),
        ("shelter", "庇护与临时安置",
         "部分地区设有**反家庭暴力庇护中心**或救助安置场所，"
         "可向当地**民政部门**询问（或拨打 12345 转接）；" "是否设有、怎么申请以当地民政口径为准。"),
        ("counsel", "心理咨询与精神科就诊",
         "长期遭受精神暴力的，心理咨询与精神科就诊记录可证明精神损害，"
         "也是后续主张的辅助材料，同时对你本人的恢复有帮助。"),
    ]:
        v = f.get(key) or ""
        short = label.split("（")[0]
        if is_yesish(v) or "已" in v[:2]:
            out.append((label, "通过", body + " —— 已使用或已联系。"))
        elif no(v) or "未" in v[:2]:
            out.append((label, "有风险", body + " —— 尚未使用。这一步几乎不花成本，建议尽快联系。"))
        else:
            out.append((label, "待补正", "是否向%s求助未填，这一条填了不会让你吃亏，只会多一条路。"
                        % short))
    return out


# ------------------------------------------------------------------ 离婚与赔偿
def checks_divorce(f):
    if not filled(f["divorce_intent"]):
        return []
    v = f["divorce_intent"]
    if yes(v) or "是" in v[:2] or "打算" in v:
        out = [("离婚与损害赔偿", "通过",
                "打算结束关系（%s）。家庭暴力属于《民法典》规定的可主张离婚的情形之一，"
                "**无过错方有权就损害赔偿请求权主张赔偿**；可在离婚协议或诉讼中一并提出。"
                "具体是否支持与数额，以司法机关认定为准。" % v)]
        if unknown(f["divorce_evidence"]):
            out.append(("离婚证据册", "待补正",
                        "是否已为离婚诉讼固定证据未填。建议把报警回执、病历、伤情照片、"
                        "威胁记录整理成一份证据清单，每份注明证据来源与证明目的。"))
        return out
    out = [("离婚与损害赔偿", "待补正", "是否打算离婚未填，该分支结论取决于此项。")]
    return out


# ------------------------------------------------------------------ 时限
def checks_time(f, today):
    d = parse_date(f["last_time"])
    if d:
        left = (d + timedelta(days=365 * 3) - today).days
        return [("民事诉讼时效", "有风险" if left < 0 else "通过",
                 "最近一次家暴时间 %s，一般民事诉讼时效 3 年%s。"
                 % (d.isoformat(), ("已过 %d 天" % -left) if left < 0 else ("还剩 %d 天" % left)))]
    return [("最近一次发生时间", "待补正",
             "未填最近一次发生时间，无法计算时效倒计时；**保护令申请不受此限制，可立即启动**。")]


# ------------------------------------------------------------------ 路径
def path_order(f):
    rel = f["relation"] or ""
    out = [("第 0 步（安全，先做）",
            "先保证自身安全：离开现场或到公共场所、亲友家、单位；必要时拨打 110。"
            "**这一步不做，后面所有维权都不成立**——证据可以事后补，人受伤补不回来。")]
    if ("前男" in rel or "前女" in rel or "同居" in rel
            or "恋" in rel or "未婚" in rel):
        out[0] = ("第 0 步（安全，先做）",
                  "先保证自身安全：离开现场或到公共场所、亲友家、单位；必要时拨打 110。"
                  "**这一步不做，后面所有维权都不成立**——证据可以事后补，人受伤补不回来。"
                  "（你填写的是同居/前伴侣关系，报警、就医、妇联求助路径**不受关系限制**，"
                  "保护令也可按共同生活关系申请。）")
    out.append(("第 1 步（报案）",
                "拨打 110，明确告知\"被家暴/被打\"，要求：① 出警；② **制作询问笔录**；"
                "③ 出具**报警回执或接警编号**（务必收好，后续与法院、妇联都要用）。"))
    out.append(("第 2 步（就医取证）",
                "到正规医院急诊或外科就诊，**向医生如实说明致伤原因**，"
                "留存病历、诊断证明、检查报告、发票；同时多角度拍伤情照片"
                "（带时间地点水印、保留原图）。"))
    out.append(("第 3 步（固定其他证据）",
                "固定微信/短信威胁辱骂记录（**别删**）、争吵录音录像、被砸坏的家具与被撕坏衣物（拍照）、"
                "邻居/物业/亲友证人、社区与妇联的介入记录，全部按时间顺序编号归档。"))
    out.append(("第 4 步（申请人身安全保护令）",
                "向**人民法院**提交人身安全保护令申请书（自己申请，或由居委会/村委会/妇联/"
                "学校/幼儿园/医疗机构等代为申请）；材料一般包括申请书、身份证明、"
                "关系证明、证据清单与证据复印件；请求事项可写：%s。" % PROTECTION_ITEMS))
    out.append(("第 5 步（多线求助）",
                "拨打 **12338**（妇联维权热线）咨询与转介；到居委会/村委会反映并要求记录；"
                "询问当地民政是否有反家暴庇护场所；符合条件的可向法律援助机构申请援助。"))
    out.append(("第 6 步（离婚与赔偿）",
                "决定离开的，在离婚协议或诉讼中一并主张**损害赔偿**，"
                "并一并处理财产分割与子女抚养；证据册直接复用。"))
    return out


def todo_list(f, results):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if any(k in (f["narrative"] or "") for k in URGENT_WORDS):
        extra.append(("立即脱离现场", "安全优先：去公共场所/亲友家，或拨打 110"))
    if not (yes(f["called_110"]) or "已报警" in (f["called_110"] or "")):
        extra.append(("报警并索要回执", "110 → 要求做笔录 + 拿报警回执/接警编号"))
    if not is_yesish(f["medical"]):
        extra.append(("尽快就医", "医院如实说明致伤原因，留存病历与诊断证明"))
    if not is_yesish(f["photo"]):
        extra.append(("拍伤情照片", "多角度 + 时间地点水印 + 保留原图"))
    if not (yes(f["protection_applied"]) or "已" in (f["protection_applied"] or "")):
        extra.append(("准备保护令申请", "到人民法院立案窗口或网上立案，提交申请书、身份证明、关系证明、证据清单"))
    extra.append(("拨打 12338", "妇联维权热线，咨询取证与转介"))
    extra.append(("到居委会反映", "要求介入并记录在册，必要时出具情况证明"))
    seen = set()
    allt = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        allt.append((n, s))
    return allt


# ------------------------------------------------------------------ 报告
SECTIONS = [
    "二、形态与适用范围定性",
    "三、安全优先级动作",
    "四、证据清单与缺口",
    "五、报警与就医要点",
    "六、人身安全保护令申请路径与材料",
    "七、其他求助渠道",
    "八、时限倒计时",
]


def render(f, results, steps, todos, today, gaps):
    L = []
    L.append("# 家庭暴力取证与人身安全保护令核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 与施暴方关系：%s" % (f["relation"] or "未填"))
    L.append("- 最近一次发生时间：%s" % (f["last_time"] or "未填"))
    if any(k in (f["narrative"] or "") for k in URGENT_WORDS):
        L.append("- **安全提示：按填写内容看，事件可能仍在进行或有再次发生的风险，请先读第三段。**")
    L.append("")

    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：证据链存在明显缺口，建议按第四、五段立刻补齐材料，并尽快申请人身安全保护令。**")
    elif risk:
        L.append("**判定：存在可主张的点，但关键动作尚未完成，需优先补正。**")
    elif todo:
        L.append("**判定：采集表大量未填，暂时给不出结论。请把第三段（安全）、第四段（证据）"
                 "按要求填完再重跑——**安全那一段尤其优先**。**未填的一律不算通过。**")
    else:
        L.append("**判定：未发现明确缺口；请重点核对第三段安全动作是否都已到位。**")
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
            continue
        L.append("## %s" % t)
        L.append("")
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for name, state, msg in rows:
            L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
        L.append("")

    L.append("## 九、申请与求助路径排序")
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
            L.append("| %s | %s |" % (g, GAP_FIX.get(g, "按下一段操作卡补齐")))
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
    L.append("- **安全优先**：暴力正在发生或刚发生时，先离开现场、拨打 110，"
             "不要为了\"留证据\"而继续待在危险环境里。")
    L.append("- 本结果依**通用规则**整理，**不替代律师意见**；"
             "人身安全保护令的受理条件、管辖法院、可请求事项、有效期与执行方式，"
             "**一律以受理法院与当地现行规定为准**。")
    L.append("- 不预测法院是否会签发保护令，也不预测离婚与损害赔偿的结果。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 本结果依通用规则整理，不替代专业意见，最终以主管部门/司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps):
    return {
        "核查日期": today.isoformat(),
        "关系形态": f["relation"],
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "relation": get_text(kv, ["与施暴方关系", "双方关系", "关系形态", "两人关系", "关系"]),
        "last_time": get_text(kv, ["最近一次发生时间", "事发时间", "发生时间"]),
        "narrative": get_text(kv, ["事情经过", "事发经过", "暴力情形描述", "具体经过", "经过"]),
        "left_site": get_text(kv, ["是否已脱离现场", "是否离开现场", "目前是否已安全"]),
        "called_110": get_text(kv, ["是否拨打110报警", "是否报警", "报警情况", "报警"]),
        "police_note": get_text(kv, ["公安机关笔录情况", "笔录情况", "是否做笔录", "笔录"]),
        "photo": get_text(kv, ["是否拍摄伤情照片", "伤情照片"]),
        "medical": get_text(kv, ["是否去医院就诊", "就诊情况", "是否就医", "就医"]),
        "record_reason": get_text(kv, ["病历是否写明致伤原因", "病历致伤原因"]),
        "recording": get_text(kv, ["是否有录音录像", "录音录像"]),
        "chat": get_text(kv, ["是否有威胁辱骂记录", "微信威胁记录", "聊天记录", "威胁记录"]),
        "witness": get_text(kv, ["是否有证人", "证人情况", "证人"]),
        "women_fed": get_text(kv, ["是否已联系妇联", "联系妇联", "妇联介入"]),
        "community": get_text(kv, ["是否已向居委会反映", "居委会介入", "社区介入"]),
        "shelter": get_text(kv, ["是否了解庇护渠道", "庇护情况"]),
        "counsel": get_text(kv, ["是否有心理咨询记录", "心理咨询"]),
        "protection_applied": get_text(kv, ["是否申请过人身安全保护令", "保护令申请情况"]),
        "protection_status": get_text(kv, ["保护令进展", "保护令状态"]),
        "protection_order": get_text(kv, ["是否已取得保护令裁定书", "是否取得裁定书"]),
        "legal_aid": get_text(kv, ["是否申请法律援助", "法律援助"]),
        "divorce_intent": get_text(kv, ["是否打算离婚", "离婚打算"]),
        "divorce_evidence": get_text(kv, ["是否为离婚固定证据", "离婚证据准备"]),
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

    LABELS = {"relation": "与施暴方关系"}
    missing = [LABELS[k] for k in ("relation",) if not filled(f[k])]

    rel_label, rel_why = cohab_type(f["relation"])
    forms = form_match(f["narrative"])
    form_txt = "、".join(forms) if forms else "（未填经过，未识别）"
    quality = [("适用范围与暴力形态", "%s / 识别形态：%s"
                % (rel_label, form_txt),
                rel_why + " 按填写内容识别到的暴力形态为" + form_txt + "。"
                "家庭暴力的常见形态包括**肢体暴力、精神暴力（含经常性侮辱、恐吓、威胁）、"
                "控制与跟踪行为、经济控制**；**精神暴力和经常性侮辱恐吓同样属于家庭暴力**，"
                "不是\"家务事\"，也不因为没打伤就不能申请保护。")]

    results = [
        ("形态与适用范围定性", quality),
        ("安全优先级动作", checks_safety(f)),
        ("证据清单与缺口", checks_evidence(f)),
        ("报警与就医要点", checks_medical(f)),
        ("人身安全保护令申请路径与材料", order_apply(f)),
        ("其他求助渠道", checks_other(f)),
        ("时限倒计时", checks_time(f, today)),
    ]
    results.append(("离婚与损害赔偿", checks_divorce(f)))

    steps = path_order(f)
    todos = todo_list(f, results)
    gaps = evidence_gap(f)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today, gaps), ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, steps, todos, today, gaps)
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
