# -*- coding: utf-8 -*-
"""噪音扰民取证与投诉 v1.0.0

输入：按 templates/噪音扰民信息采集表.md 填写的 Markdown
输出：九段式核查报告（或 --json 摘要）

判定纪律：
- 依《噪声污染防治法》、GB 3096《声环境质量标准》等通用规则整理，不替代律师意见
- 不认定违法、不预测处罚与诉讼结果、不代写文书
- 声环境功能区类别、夜间时段起止、装修限时段等各地可另行划定并公告，一律提示以当地主管部门口径为准
- 用户填什么就用什么，未填的一律标「未填」，不算通过
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

VERSION = "1.0.0"

PLACEHOLDER = ("【待填】", "填什么", "是 / 否", "有 / 无", "___", "另填", "不确定填")

# ---------------------------------------------------------------- 基础工具


def norm(s):
    if s is None:
        return ""
    t = str(s)
    t = t.replace("\u3000", " ").replace(" ", "")
    t = t.replace("\uff08", "(").replace("\uff09", ")")
    t = t.replace("|", " ").strip()
    return t


def clean(s):
    if s is None:
        return ""
    return str(s).strip().strip("|").strip()


def is_ph(v, is_value=True):
    """is_value=True 时启用「选项串」判定（含 ' / ' 视为未填），字段名不启用。"""
    raw = "" if v is None else str(v)
    if is_value and (" / " in raw or "｜" in raw):
        return True
    t = norm(v)
    if not t:
        return True
    for w in PLACEHOLDER:
        nw = norm(w)
        if nw and nw in t:
            return True
    if t in ("-", "--", "/", "\u2014"):
        return True
    if set(t) <= set("-\u2014:=/"):
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


def parse_fields(text):
    """同时支持 `| 字段 | 值 |` 表格行 与 `字段：值` 冒号行。"""
    d = {}
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        if is_row(ln):
            c = split_row(ln)
            if len(c) < 2:
                continue
            k, v = clean(c[0]), clean(c[1])
            if not k or is_ph(k, False) or is_ph(v):
                continue
            d.setdefault(k, v)
            continue
        idx = ln.find("\uff1a")
        if idx < 0:
            idx = ln.find(":")
        if idx < 0:
            continue
        k = ln[:idx].strip().lstrip("-*>").strip()
        v = ln[idx + 1:].strip()
        if not k or not v:
            continue
        if len(norm(k)) > 30:
            continue
        if is_ph(k, False) or is_ph(v):
            continue
        d.setdefault(k, v)
    return d


def get_text(fields, *labels):
    """最长别名优先匹配，避免短别名抢走长字段。"""
    if isinstance(fields, str):
        fields = parse_fields(fields)
    for lb in sorted(labels, key=lambda x: -len(norm(x))):
        nlb = norm(lb)
        if not nlb:
            continue
        for k in fields:
            if norm(k) == nlb and not is_ph(fields[k]):
                return fields[k]
        for k in fields:
            if nlb in norm(k) and not is_ph(fields[k]):
                return fields[k]
    return ""


def get_num(fields, *labels):
    v = get_text(fields, *labels)
    if not v:
        return None
    m = re.search(r"\d+(?:\.\d+)?", norm(v).replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def get_int(fields, *labels):
    v = get_num(fields, *labels)
    if v is None:
        return None
    return int(v)


def yes(fields, *labels):
    """三态：True / False / None（未填或看不出来）。先判否定式。"""
    v = get_text(fields, *labels)
    if not v:
        return None
    t = norm(v)
    if "没有" in t or "未曾" in t or "从未" in t:
        return False
    if "无" in t or "否" in t or "未" in t:
        return False
    if "有" in t or "是" in t or "已" in t:
        return True
    return None


def parse_date(v):
    if not v:
        return None
    t = norm(v)
    m = re.search(r"(\d{4})\D{1,2}(\d{1,2})\D{1,2}(\d{1,2})", t)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            return None
    m = re.search(r"(\d{4})\D{1,2}(\d{1,2})", t)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), 1)
        except Exception:
            return None
    return None


def fmt_num(v):
    if v is None:
        return "未填"
    if isinstance(v, float) and abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    if isinstance(v, float):
        return ("%.1f" % v)
    return str(v)


def fmt_money(v):
    if v is None:
        return "未填"
    n = int(round(v))
    return "¥" + "{:,}".format(n)


def fmt_flag(v, true_s="是", false_s="**否**"):
    if v is True:
        return true_s
    if v is False:
        return false_s
    return "未填"


def fmt_yes(v):
    if v is True:
        return "有"
    if v is False:
        return "**无**"
    return "未填"


# ---------------------------------------------------------------- 领域表
TYPE_ORDER = ("社会生活", "建筑施工", "工业", "交通运输")

DEPT = {
    "社会生活": ("公安机关（110 / 属地派出所）",
                "《噪声污染防治法》关于社会生活噪声污染防治的规定，由公安机关管辖，可依法警告、罚款"),
    "建筑施工": ("生态环境主管部门",
                "《噪声污染防治法》关于建筑施工噪声污染防治的规定，由生态环境主管部门管辖"),
    "工业": ("生态环境主管部门",
             "《噪声污染防治法》关于工业噪声污染防治的规定，由生态环境主管部门管辖"),
    "交通运输": ("公安机关交通管理部门 / 铁路、民航等按职责",
                "《噪声污染防治法》关于交通运输噪声污染防治的规定，按各自职责分工管理"),
}

ACTION = {
    "社会生活": "110 报警（报「社会生活噪声」，民警出警处置）",
    "建筑施工": "向生态环境主管部门投诉查处（12345 派单 / 当地生态环境部门举报渠道）",
    "工业": "向生态环境主管部门投诉查处（12345 派单 / 当地生态环境部门举报渠道）",
    "交通运输": "122 或 12345 转公安交管部门（铁路、民航按各自渠道）",
}

SRC_KW = (
    ("建筑施工", ("工地", "打桩", "浇筑", "混凝土", "渣土", "挖掘机", "在建",
                  "盾构", "市政施工", "楼盘施工", "爆破")),
    ("工业", ("工厂", "车间", "风机", "冷却塔", "空压机", "锅炉", "生产设备",
              "矿区", "加工作坊", "排污", "机组")),
    ("交通运输", ("车流", "高速", "高架", "铁路", "地铁", "飞机", "机场",
                  "鸣笛", "炸街", "摩托车", "货车", "轻轨", "航道", "主干道")),
    ("社会生活", ("跑跳", "拖家具", "音响", "乐器", "钢琴", "宠物", "狗吠", "广场舞",
                  "喇叭", "KTV", "商铺", "麻将", "邻居", "生活", "电视", "洗衣机",
                  "唱歌", "聚会", "喧哗", "蹦", "吵闹", "外机", "水泵", "变压器", "电梯")),
)

GB_DAY = {"0": 50, "1": 55, "2": 60, "3": 65, "4a": 70, "4b": 70}
GB_NIGHT = {"0": 40, "1": 45, "2": 50, "3": 55, "4a": 55, "4b": 60}
GB_NOTE = {
    "0": "康复疗养区等特别需要安静的区域",
    "1": "以居民住宅、医疗卫生、文化教育、科研设计、行政办公为主",
    "2": "以商业金融、集市贸易为主，或居住商业工业混杂",
    "3": "以工业生产、仓储物流为主",
    "4a": "交通干线两侧一定距离内（高速公路、一二级公路、城市主次干道等）",
    "4b": "铁路干线两侧一定距离内",
}


def classify_noise(fields):
    """返回 (判定类别, 声明类别, 来源命中类别列表, 提示列表)"""
    notes = []
    decl = get_text(fields, "噪声类型")
    src = get_text(fields, "具体噪声来源")
    d_t = ""
    for k in TYPE_ORDER:
        if k in norm(decl):
            d_t = k
            break
    hits = []
    for t, kws in SRC_KW:
        for w in kws:
            if w in norm(src):
                if t not in hits:
                    hits.append(t)
                break
    deco = yes(fields, "是否住宅楼内室内装修作业")
    if "装修" in norm(src) or "电钻" in norm(src) or deco is True:
        if deco is True:
            if "社会生活" not in hits:
                hits.append("社会生活")
            notes.append("住宅楼内室内装修作业按**社会生活噪声**处理，由公安机关管辖")
        elif any(w in norm(src) for w in ("工地", "在建", "楼盘")):
            if "建筑施工" not in hits:
                hits.append("建筑施工")
            notes.append("在建工地施工按**建筑施工噪声**处理，由生态环境主管部门管辖")
        else:
            notes.append("涉及装修但没说清是住宅楼内室内装修还是在建工地施工——"
                         "两者归口不同（前者公安、后者生态环境），必须先确认")
    eff = d_t
    if not eff:
        eff = hits[0] if len(hits) == 1 else (hits[0] if hits else "")
    if d_t and hits and d_t not in hits:
        notes.append("你填的噪声类型（%s）与具体来源（%s）对不上，"
                     "按来源判定更准——请核对该选哪一类" % (d_t, "、".join(hits)))
    if len(hits) > 1:
        notes.append("存在**多类噪声源**（%s），分别归不同部门，"
                     "投诉时要分开报，别混成一件" % "、".join(hits))
    return eff, d_t, hits, notes


def pick_category(fields):
    v = get_text(fields, "所在区域声环境功能区类别")
    t = norm(v).lower()
    for k in ("4a", "4b", "0", "1", "2", "3"):
        if k in t:
            return k
    return ""


def pick_slot(fields):
    """返回 (时段标签, 是否按夜间限值判, 是否含午间, 是否含休息日节假日, 是否识别到)"""
    v = get_text(fields, "主要发生时段")
    t = norm(v)
    if not t:
        return "", False, False, False, False
    night = any(w in t for w in ("夜间", "凌晨", "半夜", "零点", "深夜"))
    noon = any(w in t for w in ("午间", "中午", "午休"))
    rest = any(w in t for w in ("休息日", "节假日", "周末", "双休"))
    all_day = "全天" in t
    day = any(w in t for w in ("昼间", "白天", "日间", "上午", "下午"))
    is_night = night or all_day
    if not (night or noon or rest or all_day or day):
        return v, False, False, False, False
    return v, is_night, noon, rest, True


# ---------------------------------------------------------------- 报告


def build_report(path, base=None):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return None, "读不了文件：%s" % e

    f = parse_fields(text)
    if base is None:
        base = dt.date.today()

    city = get_text(f, "所在城市")
    src = get_text(f, "具体噪声来源")
    slot_raw = get_text(f, "主要发生时段")
    if not (src or slot_raw or get_text(f, "噪声类型")):
        return None, ("未解析到关键信息。至少填写「具体噪声来源」或「主要发生时段」"
                      "中的一项，否则无法判断归哪个部门管。")

    ntype, decl, hits, cls_notes = classify_noise(f)
    dept = DEPT.get(ntype, ("", ""))[0]
    dept_why = DEPT.get(ntype, ("", ""))[1]

    # ---- 时段与限值
    slot_label, is_night, noon, rest, slot_ok = pick_slot(f)
    cat = pick_category(f)
    cat_unknown = not cat
    if cat_unknown:
        cat = "1"
    day_limit = GB_DAY.get(cat, 55)
    night_limit = GB_NIGHT.get(cat, 45)
    db = get_num(f, "实测分贝")
    tool = get_text(f, "测量工具")
    sud = yes(f, "是否有夜间突发噪声")
    fixed = yes(f, "是否固定设备结构传播噪声")
    limit = night_limit if is_night else day_limit
    over = None
    if db is not None:
        over = db - limit

    # ---- 装修时间
    deco = yes(f, "是否住宅楼内室内装修作业")
    deco_bad = yes(f, "装修是否在法定休息日节假日或午间夜间进行")
    deco_notes = []
    if deco is True or "装修" in norm(src):
        deco_notes.append("已竣工交付使用的住宅楼内进行室内装修作业应当**限制作业时间**，"
                          "并采取有效措施防止噪声污染")
        if deco_bad is True or rest or noon or is_night:
            deco_notes.append("装修作业落在**法定休息日 / 节假日 / 午间 / 夜间**，"
                              "通常属于被禁止产生噪声的作业时段——具体时段以当地规定为准")
        if deco_bad is False:
            deco_notes.append("你填的是未在上述禁限时段作业，请保留物业的装修备案与时间段证明")

    # ---- 取证强度
    rec = yes(f, "有无录音或视频")
    wm = yes(f, "录音视频是否带时间水印")
    diary = get_int(f, "噪声日记连续记录天数")
    report3 = yes(f, "有无第三方检测机构检测报告")
    notary = yes(f, "有无公证保全")
    pprop = yes(f, "有无物业或社区书面记录")
    police = yes(f, "有无报警回执或接处警记录")
    hot12345 = yes(f, "有无 12345 工单")
    witness = yes(f, "有无邻居愿意作证")

    score = 0
    ev_items = []
    if rec is True and wm is True:
        score += 25
        ev_items.append(("带时间水印的录音 / 视频", "有", 25, "三要素（声音 + 时间 + 地点）齐全"))
    elif rec is True and wm is not True:
        score += 8
        ev_items.append(("带时间水印的录音 / 视频", "**有录音但无时间水印**", 8,
                         "对方一句「不知道什么时候录的」就废——重录并开时间水印"))
    else:
        ev_items.append(("带时间水印的录音 / 视频", "**无**", 0,
                         "最基础的证据都没有，立即开始录"))
    if diary is None:
        ev_items.append(("噪声日记（连续记录）", "未填", 0, "每天一行：日期/起止/时长/分贝/影响"))
    elif diary >= 7:
        score += 20
        ev_items.append(("噪声日记（连续记录）", "%d 天" % diary, 20, "连续性够，能证明持续侵害"))
    elif diary >= 3:
        score += 10
        ev_items.append(("噪声日记（连续记录）", "%d 天" % diary, 10, "≥7 天更有说服力"))
    else:
        score += 5
        ev_items.append(("噪声日记（连续记录）", "%d 天" % diary, 5, "天数太少，至少记满 7 天"))
    if report3 is True:
        score += 25
        ev_items.append(("第三方检测机构检测报告", "有", 25, "执法与诉讼最认这一份"))
    else:
        ev_items.append(("第三方检测机构检测报告", "**无**", 0,
                         "要提起诉讼，这份几乎是必需的——找具备资质的检测机构"))
    if notary is True:
        score += 10
        ev_items.append(("公证保全", "有", 10, "几乎无法被推翻"))
    else:
        ev_items.append(("公证保全", "无", 0, "成本高，诉讼中可考虑"))
    if police is True:
        score += 6
        ev_items.append(("报警回执 / 接处警记录", "有", 6, "证明投诉过"))
    else:
        ev_items.append(("报警回执 / 接处警记录", "**无**", 0, "出警后务必索取回执、记下警号"))
    if hot12345 is True:
        score += 4
        ev_items.append(("12345 工单", "有", 4, "工单号要留着"))
    else:
        ev_items.append(("12345 工单", "**无**", 0, "只打电话不留单 = 没投诉"))
    if pprop is True:
        score += 5
        ev_items.append(("物业 / 社区书面记录", "有", 5, "证明已履行先协商义务"))
    else:
        ev_items.append(("物业 / 社区书面记录", "**无**", 0, "报事要留记录，别只让客服口头说说"))
    if witness is True:
        score += 5
        ev_items.append(("邻居证人", "有", 5, "佐证，效力有限"))
    else:
        ev_items.append(("邻居证人", "无", 0, "能找到同层或上下层邻居作证更好"))

    # ---- 投诉阶梯
    talk = yes(f, "是否与对方沟通过")
    trace = yes(f, "沟通是否留痕")
    prop = yes(f, "是否找过物业或业委会")
    comm = yes(f, "是否找过社区居委会")
    called = yes(f, "是否打过 12345")
    called110 = yes(f, "是否报过 110")
    eco = yes(f, "是否向生态环境部门投诉过")
    suit = yes(f, "是否已提起诉讼")

    dept_done = (called110 is True) if ntype == "社会生活" else (
        (eco is True) if ntype in ("建筑施工", "工业") else (called110 is True or eco is True))
    action_label = ACTION.get(ntype, "向主管部门投诉（先确认归口）")

    ladder = [
        (1, "当面沟通并留痕（微信文字 / 录音 / 书面）", talk is True and trace is True),
        (2, "物业 / 业委会劝阻调解（要书面记录）", prop is True),
        (3, "社区居委会调解（要调解记录）", comm is True),
        (4, "12345 市民热线（务必拿工单编号）", called is True),
        (5, action_label, dept_done),
        (6, "向人民法院提起诉讼", suit is True),
    ]
    ladder_state = []
    for i, name, done in ladder:
        if i == 1 and talk is True and trace is not True:
            ladder_state.append((i, name, "**已做但无效：没留痕**"))
        else:
            ladder_state.append((i, name, "已做" if done else "未做"))
    next_step = None
    for i, name, st in ladder_state:
        if st != "已做":
            next_step = (i, name)
            break

    # ---- 日期与时效
    first = parse_date(get_text(f, "首次发生日期"))
    last = parse_date(get_text(f, "最近一次发生日期"))
    span_days = (base - first).days if first else None
    gap_days = (base - last).days if last else None
    dur = get_num(f, "单次持续时长")
    per_week = get_num(f, "每周发生天数")

    # ---- 诉求
    claim = get_text(f, "主要诉求")
    money = get_num(f, "主张损失金额")
    medical = yes(f, "有无就医记录")
    weak = yes(f, "家中是否有婴幼儿")

    # ---- 结论
    key_missing = []
    if not src:
        key_missing.append("具体噪声来源")
    if not slot_raw:
        key_missing.append("主要发生时段")
    if not ntype:
        key_missing.append("噪声类别（社会生活 / 建筑施工 / 工业 / 交通运输）")
    if cat_unknown:
        key_missing.append("声环境功能区类别")
    complained = any(x is True for x in (police, hot12345, pprop))
    if key_missing:
        verdict = "待补正"
    elif score < 30 and not complained:
        verdict = "不通过"
    elif score >= 70 and complained:
        verdict = "通过"
    else:
        verdict = "有风险"

    todo = []
    risks = []

    # ---------------- 报告
    L = []
    A = L.append
    A("# 噪音扰民取证与投诉核查报告")
    A("")
    A("> 生成日期：%s；脚本版本 v%s%s" % (base.isoformat(), VERSION,
                                       "；所在地：%s" % city if city else ""))
    A("")

    A("## 一、结论摘要")
    A("")
    A("- **结论：%s**" % verdict)
    if key_missing:
        A("- 关键信息还缺 %d 项：%s。未填的一律不算通过，补填后重跑。"
          % (len(key_missing), "、".join(key_missing)))
    if ntype:
        A("- 噪声类别判定为 **%s噪声**，主管部门是 **%s**。" % (ntype, dept))
    else:
        A("- ⚠️ 没能判定噪声类别 → **也没法确定归哪个部门管**，这是现在最要紧的一步。")
    if db is not None and slot_ok:
        if over is not None and over > 0:
            A("- 实测 %s dB(A)，对照 %s 限值 %s dB(A)，**超出约 %s dB(A)**。"
              % (fmt_num(db), "夜间" if is_night else "昼间", fmt_num(limit), fmt_num(over)))
        else:
            A("- 实测 %s dB(A)，对照 %s 限值 %s dB(A)，**未超出**（但手机 APP 读数仅供参考）。"
              % (fmt_num(db), "夜间" if is_night else "昼间", fmt_num(limit)))
    else:
        A("- 分贝或时段未填，**超没超标无法判定**——限值对照表见第三段。")
    A("- 取证强度得分：**%d / 100**%s" % (score,
                                        "（偏低，按第四段缺口补）" if score < 50 else "（证据链较完整）"))
    if next_step:
        A("- 投诉阶梯目前走到第 %d 级前，**下一步：%s**。" % (next_step[0], next_step[1]))
    A("- 未填的一律不算通过，只按你填了的判断——补填后重跑一次。")
    A("")

    A("## 二、归哪个部门管")
    A("")
    A("| 项 | 结论 |")
    A("|---|---|")
    A("| 你填的噪声类型 | %s |" % (decl or "未填"))
    A("| 具体噪声来源 | %s |" % (src or "未填"))
    A("| 判定类别 | %s |" % ("**%s噪声**" % ntype if ntype else "**未判定**"))
    A("| 主管部门 | %s |" % (dept or "未确定"))
    A("| 执法动作 | %s |" % (action_label if ntype else "先确认归口"))
    A("")
    if dept_why:
        A("依据：%s。" % dept_why)
        A("")
    A("| 四类噪声 | 主管部门 |")
    A("|---|---|")
    A("| 社会生活噪声（邻里、家庭音响乐器、宠物、广场舞、商铺喇叭、住宅楼内室内装修） | 公安机关（110） |")
    A("| 建筑施工噪声（工地打桩、浇筑、渣土、夜间施工） | 生态环境主管部门 |")
    A("| 工业噪声（工厂车间、风机、冷却塔、生产设备） | 生态环境主管部门 |")
    A("| 交通运输噪声（道路车流、高架、铁路、地铁、飞机、炸街） | 公安交管 / 铁路民航按职责 |")
    A("")
    if cls_notes:
        for n_ in cls_notes:
            A("- %s" % n_)
        A("")
    A("> 找错部门是最常见的白跑原因：把住宅楼装修投诉到生态环境部门、把工地夜间施工当成邻里纠纷打 110，"
      "都会被推回来。个别城市有综合执法或委托执法的特殊安排，**以当地主管部门口径为准**。")
    A("")

    A("## 三、时段与限值对照")
    A("")
    A("| 项 | 数值 |")
    A("|---|---|")
    A("| 发生时段 | %s |" % (slot_label or "未填"))
    A("| 按哪套限值判 | %s |" % ("夜间" if (is_night and slot_ok) else ("昼间" if slot_ok else "无法判定")))
    A("| 声环境功能区类别 | %s 类%s |" % (cat, "（未填，暂按 1 类居民区参照，需核实）" if cat_unknown else "（%s）" % GB_NOTE.get(cat, "")))
    A("| 昼间限值（6:00–22:00） | %s dB(A) |" % fmt_num(day_limit))
    A("| 夜间限值（22:00–次日 6:00） | %s dB(A) |" % fmt_num(night_limit))
    A("| 实测值 | %s dB(A)%s |" % (fmt_num(db), "（%s）" % tool if tool else ""))
    A("| 判定 | %s |" % (("**超出约 %s dB(A)**" % fmt_num(over)) if (over is not None and over > 0)
                       else ("未超出" if over is not None else "未填，无法判定")))
    A("")
    A("- 昼间通常指 6:00–22:00，夜间 22:00–次日 6:00；**各地可另行划定并公告**，以当地公告为准。")
    A("- 限值依 GB 3096《声环境质量标准》按 0~4 类声环境功能区划分，上表为室外声环境限值体系。")
    if sud is True:
        A("- 你填了有夜间突发噪声：夜间突发噪声的最大声级，**超过限值的幅度不得高于 15 dB(A)**，"
          "即夜间突发按 %s dB(A) 判。" % fmt_num(night_limit + 15))
    if fixed is True:
        A("- 你填了固定设备结构传播噪声（空调外机、水泵、变压器、电梯等）：这类传到室内的噪声"
          "适用另一套室内限值体系（GB 22337），**不要直接拿室外限值套**，"
          "需委托检测机构按室内标准布点测量。")
    if db is not None and tool and "APP" in norm(tool).upper():
        A("- ⚠️ 你的分贝来自手机 APP：只能作为**初步证据**，不当然被采信。"
          "它能推动出警与调解，但执法与诉讼认的是有资质的检测机构按规范出具的检测报告。")
    if deco_notes:
        A("")
        A("**装修时间限制：**")
        for n_ in deco_notes:
            A("- %s" % n_)
    A("")

    A("## 四、取证强度与证据缺口")
    A("")
    A("取证强度得分：**%d / 100**" % score)
    A("")
    A("| 证据项 | 状态 | 得分 | 说明 |")
    A("|---|---|---|---|")
    for nm, st, sc, note in ev_items:
        A("| %s | %s | %d | %s |" % (nm, st, sc, note))
    A("")
    gaps = [nm for nm, st, sc, note in ev_items if sc == 0 or "**" in st]
    if gaps:
        A("证据缺口（%d 项）：" % len(gaps))
        for g in gaps:
            A("- %s" % g)
    else:
        A("证据缺口：无（已填项均具备）。")
    A("")
    A("证据效力排序：第三方检测报告 ＞ 公证保全 ＞ 带时间水印的连续录音视频 ＞ "
      "报警回执与 12345 工单 ＞ 连续噪声日记 ＞ 物业社区记录 ＞ 邻居证言 ＞ 手机 APP 读数。")
    A("")
    if span_days is not None:
        A("已持续约 **%d 天**（自 %s 起算）。" % (span_days, first.isoformat()))
    if gap_days is not None:
        if gap_days > 30:
            A("- ⚠️ 最近一次记录距今 %d 天，证据时效性偏弱，建议补录近期（近 30 天内）的录音与日记。" % gap_days)
        else:
            A("- 最近一次发生距今 %d 天，证据时效性尚可。" % gap_days)
    A("")

    A("## 五、投诉阶梯排序")
    A("")
    A("| 级别 | 动作 | 状态 |")
    A("|---|---|---|")
    for i, name, st in ladder_state:
        A("| %d | %s | %s |" % (i, name, st))
    A("")
    if next_step:
        A("**下一步（第 %d 级）：%s**" % (next_step[0], next_step[1]))
    else:
        A("六个层级都已走到，重点是**执行与取证**：把判决或调解协议的履行情况继续留证。")
    A("")
    A("顺序不能跳：前几级的记录既是证据，也是法院看重的「已尽力主张」。")
    A("")

    A("## 六、话术卡")
    A("")
    A("**1）对邻居开口（先给事实、再给影响、最后给一个他做得到的方案）**")
    A("")
    A("> 「您好，我是楼下 ×× 室的。有个事想跟您商量——最近晚上十点半以后，楼上会有比较明显的"
      "拖家具和跑动声，家里老人（孩子）这边确实休息不了。不是要计较什么，想看看能不能晚上十点以后"
      "尽量不挪重的东西，或者铺块地毯？方便的话加个微信，以后有什么我直接跟您说，也不用惊动物业。」")
    A("")
    A("说完**立刻用微信补一条文字**（这条就是留痕）。完整话术见 "
      "`templates/沟通与投诉话术卡.md`。")
    A("")
    A("**2）报警怎么说（社会生活噪声）**")
    A("")
    A("> 「我要报警，×× 区 ×× 小区 × 栋 × 单元，现在楼上正在产生**社会生活噪声**。」")
    A("")
    A("接着说四件事：① 类型（生活噪声——拖动物品 / 音响 / 宠物 / 商铺喇叭）"
      "② 已经持续 ×× 分钟 ③ **我上门沟通过、物业也调解过，都没效果**"
      "④ 我有带时间的录音和噪声记录。出警后**索取接处警记录或报警回执**，记下警号与单位。")
    A("")
    A("**3）12345 工单怎么写**")
    A("")
    A("> 【地点】×× 市 ×× 区 ×× 小区 × 栋 × 单元　【噪声类型】社会生活噪声"
      "　【时段】每日 22:30 至次日 1:00，已持续 × 个月"
      "　【已采取措施】已当面沟通 × 次（有微信记录）、物业报事 × 次调解无果、社区反映 × 次"
      "　【诉求】请转公安机关依法处理并反馈本人　【附件】噪声日记、带时间水印的录音视频")
    A("")
    A("要**工单编号**；办结不满意就再下一单并引用上一个工单号，形成连续记录。")
    if ntype in ("建筑施工", "工业"):
        A("")
        A("**4）向生态环境部门投诉（本例归口）**")
        A("")
        A("> 「×× 工地（工厂）存在夜间施工（工业设备）噪声，时间 ×× 点至 ×× 点，"
          "位于噪声敏感建筑物集中区域，影响 ×× 小区居民。请查处并反馈："
          "① 是否取得夜间连续作业证明 ② 是否进行了公告 ③ 监测结果。」")
    A("")

    A("## 七、诉讼与赔偿要点")
    A("")
    A("| 要点 | 结论 |")
    A("|---|---|")
    A("| 案由 | 相邻关系纠纷 / 噪声污染责任纠纷（侵权责任） |")
    A("| 核心诉请 | **停止侵害**（禁止在 ×× 时段产生超过 ×× dB(A) 的噪声） |")
    A("| 次要诉请 | 排除妨碍、赔偿检测费与医疗费等实际损失、赔礼道歉 |")
    A("| 精神损害抚慰金 | **一般难以支持**，不要当主要诉求 |")
    A("| 举证责任 | 谁主张谁举证：噪声存在、超标或不合理、对方是噪声源、损害、因果 |")
    A("| 持续性侵害 | 可依法申请**行为保全**（诉前 / 诉中）与**先予执行** |")
    A("| 诉讼时效 | 普通诉讼时效期间为**三年**（《民法典》关于诉讼时效的相关规定）；持续性侵权起算有特殊性，尽早起诉 |")
    A("")
    if report3 is not True:
        A("- ⚠️ **没有第三方检测报告**，诉讼中最关键的一环缺失，建议先补检测再起诉。")
    if medical is True:
        A("- 有就医记录：可主张医疗费，但需证明与噪声的因果关系，保留病历、票据与医嘱。")
    else:
        A("- 无就医记录：损害后果难以量化，建议后续就诊时主动向医生说明噪声暴露史并写入病历。")
    if money:
        A("- 主张损失 %s：需提供票据（检测费、公证费、医疗费、维权合理支出）。"
          % fmt_money(money))
    if claim:
        A("- 你的主要诉求：%s。" % claim)
    A("")

    A("## 八、待办补正动作")
    A("")
    for m in key_missing:
        todo.append("补齐关键信息「%s」" % m)
    for nm, st, sc, note in ev_items:
        if sc == 0 or "**" in st:
            todo.append("补证据「%s」：%s" % (nm, note))
    for i, name, st in ladder_state:
        if st.startswith("**"):
            todo.append("第 %d 级「%s」重做：%s" % (i, name, "沟通后必须用微信文字或录音留痕"))
    if next_step:
        todo.append("执行第 %d 级：%s" % (next_step[0], next_step[1]))
    if cat_unknown:
        todo.append("向当地生态环境部门或 12345 核实所在地声环境功能区类别与夜间时段起止")
    if deco is True and (deco_bad is True or rest or noon or is_night):
        todo.append("装修禁限时段：向物业索取装修备案与作业时间，违规的超时段作业向公安机关反映")
    if db is None:
        todo.append("补测分贝：手机 APP 先记，起诉前委托有资质的检测机构按规范测量")
    if diary is None or (diary or 0) < 7:
        todo.append("补噪声日记：连续记满 7 天，每天记日期 / 起止时刻 / 时长 / 分贝 / 影响")
    if gap_days is not None and gap_days > 30:
        todo.append("补录近 30 天内的新证据，避免证据时效性被质疑")
    if not todo:
        todo.append("已填项基本齐备，按第五段下一步推进并继续留证")
    todo.append("每一轮投诉都要拿到可引用的编号（工单号 / 接处警记录 / 物业报事记录）")
    for i, t in enumerate(todo, 1):
        A("%d. %s" % (i, t))
    A("")

    A("## 九、边界与纪律")
    A("")
    A("- 依《中华人民共和国噪声污染防治法》、GB 3096《声环境质量标准》等**通用规则**整理，"
      "**不替代律师意见**；")
    A("- **不认定违法、不预测处罚结果、不代写投诉与起诉文书**；")
    A("- 声环境功能区类别、昼夜间起止时点、装修禁限时段、临时限额等**各地可另行划定并公告**，"
      "一律以当地主管部门口径为准；")
    A("- 是否构成污染、是否侵权、是否支持赔偿，最终以主管部门与司法机关认定为准；")
    A("- **未填的一律不算通过**，只按你填了的判断。")
    A("")
    A("> 本结果依通用规则整理，不替代专业意见，最终以主管部门 / 司法机关认定为准。")

    body = "\n".join(L)

    for m in key_missing:
        risks.append("关键信息缺失：%s" % m)
    if not ntype:
        risks.append("噪声类别未判定，主管部门可能找错")
    if over is not None and over > 0:
        risks.append("实测超出限值约 %s dB(A)" % fmt_num(over))
    for nm, st, sc, note in ev_items:
        if sc == 0:
            risks.append("证据缺失：%s" % nm)
    if rec is True and wm is not True:
        risks.append("录音无时间水印，证明力大打折扣")
    if deco_bad is True or (deco is True and (rest or noon or is_night)):
        risks.append("装修作业落在禁限时段")
    if not complained:
        risks.append("没有任何投诉记录，「我投诉过」这条证据链缺失")
    if not risks:
        risks.append("未发现明显风险（未填项不算通过）")

    meta = {
        "版本": VERSION,
        "结论": verdict,
        "噪声类别": ntype or "",
        "主管部门": dept or "",
        "取证强度": score,
        "超标dB": None if over is None else round(over, 1),
        "未完成阶梯": next_step[0] if next_step else None,
        "风险项": risks,
        "待办": todo,
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
        print(meta if isinstance(meta, str) else "未能生成报告")
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(str(meta))
        return 2

    txt = json.dumps(meta, ensure_ascii=False, indent=2) if a.json else body
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(txt)
        print("written %s" % a.out)
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
