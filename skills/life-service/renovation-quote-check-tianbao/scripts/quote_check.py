# -*- coding: utf-8 -*-
"""装修报价单核查与增项防范：解析报价单 -> 完整性/可疑条目/注水信号/付款风险/增项应对 -> 九段报告。

设计约束（都是前几个技能踩过的坑）：
1. 表格按表头列索引定位，不按单元格下标；
2. 字段只取第一个"能解析出值"的候选，不取第一个匹配（模板说明行会骗人）；
3. 中文关键词绝不进正则字符类（re.escape 拼接），字符类只放 ASCII；
4. 跨节隔离：只在「二、报价单明细」这一节里抓报价条目，防止把付款表当报价；
5. 构建失败返回 (None, 提示串, None)，main 里两个都要判。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

# ---------------------------------------------------------------- 关键词表
# 九项必看项：(展示名, 匹配关键词元组)
REQUIRED_ITEMS = [
    ("拆除费", ("拆除", "拆改", "拆墙", "拆除费")),
    ("垃圾清运", ("垃圾清运", "垃圾外运", "清运", "垃圾费")),
    ("水电改造", ("水电", "电改造", "水路", "电路")),
    ("防水", ("防水", "防潮")),
    ("瓦工", ("瓦工", "贴砖", "地砖", "墙砖", "砖铺贴", "泥工", "砌")),
    ("木工", ("木工", "吊顶", "石膏板", "造型", "柜")),
    ("油漆", ("油漆", "乳胶漆", "腻子", "涂装")),
    ("主材品牌型号", ("主材", "瓷砖", "地板", "卫浴", "洁具", "门", "五金")),
    ("工期与付款节点", ("工期", "付款", "进度款")),
]

# 可疑表述：(展示名, 判定, 风险说明, 应对)
SUSPECT = [
    ("按实际结算", "按实际", "量没有上限，完工时账才算清",
     "要求写死上限：如「水电不超 __ 米、贴砖不超 __ 平，超出须书面确认」"),
    ("按市价/按市场价", "按市价", "材料价格不受约束，可能用低一档货",
     "指定品牌型号；未指定部分由你指定，价差由施工方承担并写明上限"),
    ("另计", "另计", "该项被排除在总价外，等于把账留到后面",
     "要求现在就写进报价单并给出单价与数量，总价同步改"),
    ("不含", "不含", "没写的默认不做，后期全是追加",
     "让对方出一份「不含清单」，未列明项视为已包含"),
    ("视情况", "视情况", "等于没有约定，任何解释都成立",
     "把「视情况」改成具体数字或具体条件"),
    ("以实际为准", "以实际为准", "同「按实际」，把自己放在有利位置",
     "要求设上限，超出需你书面确认"),
    ("多退少补", "多退少补", "看起来公平，实际是单价不受约束",
     "单价和工程量都要锁死，多退少补不改单价"),
    ("仅供参考", "仅供参考", "报价单本身没有约束力",
     "要求改为正式报价单并双方签字确认"),
]

# 注水信号
INFLATE = [
    ("项数偏少", "同户型同档次少于 15 项的报价单，大概率漏项压总价"),
    ("单价异常低", "单价远低于同项平均值，通常是低报单价、准备高报工程量"),
    ("面积与实测不符", "面积类工程量应按现场实测结算，写进合同"),
    ("没写工程量", "只给总价不给工程量，结算时全部由对方说了算"),
]

# 合同必写六句话
CONTRACT_LINES = [
    ("固定总价", "本合同为固定总价，除经我方书面确认的变更外不再增加任何费用"),
    ("增项确认程序", "任何增项须事先书面列明项目、单价、数量，经我方签字确认后方可施工；未确认不付款"),
    ("工程量按实测", "面积类工程量以现场实测为准，不得以估算量结算"),
    ("材料品牌型号", "报价单中未指定品牌型号的由我方指定，价差由施工方承担"),
    ("不含清单", "报价单未列明的项目视为已包含，事后不得追加"),
    ("验收与质保", "隐蔽工程验收节点、竣工验收标准、隐蔽工程质保年限、5% 尾款质保期满付清"),
]

# 付款节点上限（累计 %）
PAY_STAGES = [
    ("开工", 30, "材料进场、水电放线确认"),
    ("水电验收后", 50, "隐蔽工程（水电）验收合格"),
    ("泥木验收后", 70, "瓷砖空鼓、铺贴平整、吊顶牢固"),
    ("竣工验收后", 95, "五金、灯具、门、洁具、水路全通"),
    ("质保期满", 100, "遗留问题修完"),
]

WARN_IF_GE80 = 80
LOW_ITEMS = 15

# ---------------------------------------------------------------- 基础工具


def norm(s):
    """归一：去空格、全角转半角、lower。"""
    if s is None:
        return ""
    s = str(s)
    s = s.replace("　", " ").replace("\u3000", " ")
    out = []
    for ch in s:
        c = ord(ch)
        if c == 0x3000:
            out.append(" ")
        elif 0xFF01 <= c <= 0xFF5E:
            out.append(chr(c - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out).strip().lower()


def clean(s):
    if s is None:
        return ""
    s = str(s).replace("**", "").replace("\ufffd", "")
    return re.sub(r"\s+", " ", s).strip()


def has(text, words):
    """关键词命中。**words 里不能是中文正则**，这里只做子串包含。"""
    t = norm(text)
    for w in words:
        if norm(w) and norm(w) in t:
            return True
    return False


def parse_money(s):
    """从文本里抽第一个金额。兼容 5000 / 5,000 / 5000元 / 1.2万。"""
    if s is None:
        return None
    t = str(s).replace(",", "").replace("，", "")
    m = re.search(r"\d+(?:\.\d+)?\s*万?", t)
    if not m:
        return None
    v = m.group(0).replace(" ", "")
    try:
        if v.endswith("万"):
            return float(v[:-1]) * 10000.0
        return float(v)
    except ValueError:
        return None


def parse_pct(s):
    if s is None:
        return None
    m = re.search(r"\d{1,3}(?:\.\d+)?", str(s).replace("％", "%"))
    if not m:
        return None
    try:
        v = float(m.group(0))
    except ValueError:
        return None
    return v if 0 <= v <= 100 else None


def fmt_money(v):
    if v is None:
        return "—"
    v = float(v)
    if abs(v - round(v)) < 0.005:
        return str(int(round(v)))
    return ("%.2f" % v).rstrip("0").rstrip(".")


# ---------------------------------------------------------------- 表格解析
SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}")


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def is_sep(cells):
    return bool(cells) and all(SEP_RE.match(c) for c in cells if c != "")


def is_row(line):
    return line.strip().startswith("|") and not is_sep(split_row(line))


def col_index(cells, keys):
    """按表头名找列号。找不到返回 None。"""
    for i, c in enumerate(cells):
        if any(has(c, (k,)) for k in keys):
            return i
    return None


def find_section(text, *names):
    """返回某节的范围 [start, end)。找不到返回 (0, len)。"""
    lines = text.splitlines()
    start = 0
    for i, ln in enumerate(lines):
        s = norm(ln)
        if s.startswith("#") and any(has(ln, (n,)) for n in names):
            start = i
            break
    end = len(lines)
    for j in range(start + 1, len(lines)):
        s = norm(lines[j])
        if s.startswith("#") and not any(has(lines[j], (n,)) for n in names):
            end = j
            break
    return start, end


def table_rows(lines, start, end, drop_head=True):
    """抽出区间内的表格数据行。

    ⚠️ drop_head 只给"不需要知道表头"的调用方用（如付款表）。
    报价明细表**必须** drop_head=False：表头行要被用来定位列，
    删掉它会让 i_amt/i_qty/i_note 全部错位一列，进而
    「项目名称」被当成一条报价、金额列抓到备注文本、可疑表述一个都扫不出来。
    """
    rows = []
    for ln in lines[start:end]:
        if not is_row(ln):
            continue
        cells = split_row(ln)
        if not cells or all(c == "" for c in cells):
            continue
        rows.append(cells)
    if drop_head and rows:
        rows = rows[1:]
    return rows


def field_yes(text, labels):
    """读一个「有/无」「是/否」型字段的值。

    坑：全文 `has(text, "一次付清")` 会被采集表里
    「有没有要求一次付清 | 否」这一行命中 → 明明填了「否」却判成 True。
    所以必须按列取值再看值。
    """
    for line in text.splitlines():
        cells = split_row(line) if line.strip().startswith("|") else [line]
        i = col_index(cells, labels)
        if i is None:
            continue
        val = get_cell(cells, i + 1) if i + 1 < len(cells) else ""
        if not val or is_placeholder(val):
            continue
        t = norm(val)
        if "否" in t or t in ("无", "没有") or t.startswith("没"):
            return False
        return True
    return False


def get_cell(cells, idx):
    if idx is None or idx >= len(cells):
        return ""
    return clean(cells[idx])


def find_field(text, labels, want="text"):
    """在全文逐行找 label，取第一个能得到目标值的候选。

    关键：模板说明行（如「报价方式 | 总价一口价 / 按项报价 / 按平米单价」）
    会被当成值 → 所以必须要求 parser 解析成功，且用 want 决定解析器。
    """
    for line in text.splitlines():
        if norm(line) in ("", "---"):
            continue
        cells = split_row(line) if line.strip().startswith("|") else [line]
        i = col_index(cells, labels)
        if i is None:
            continue
        val = get_cell(cells, i + 1) if i + 1 < len(cells) else ""
        if not val or is_placeholder(val):
            continue
        if want == "money":
            got = parse_money(val)
            if got is None:
                continue
            return got
        if want == "pct":
            got = parse_pct(val)
            if got is None:
                continue
            return got
        if want == "int":
            m = re.search(r"\d{1,4}", val)
            if not m:
                continue
            return int(m.group(0))
        return val
    return None


PLACEHOLDER_WORDS = ("填什么", "勾一个", "有/无", "是/否", "（元）", "(元)", "数字",
                     "照抄", "新房子", "有无", "未开工", "合格 / 不合格")


def is_placeholder(v):
    t = norm(v)
    if not t:
        return True
    # 去掉空格与斜杠再比对，否则「有 / 无」「有/无」两种写法会漏
    tight = re.sub(r"[\s/、]+", "", t)
    for w in PLACEHOLDER_WORDS:
        if norm(w) in t or re.sub(r"[\s/、]+", "", norm(w)) in tight:
            return True
    # 纯符号/空单元格
    if re.match(r"^[\s\-—/·、]+$", t):
        return True
    return False


# ---------------------------------------------------------------- 报价条目
def parse_quote_items(text):
    """只从「报价单明细」这一节抓条目，避免跨节误抓。"""
    lines = text.splitlines()
    s, e = find_section(text, "报价单明细", "报价明细", "报价单")
    rows = table_rows(lines, s, e, drop_head=False)
    if not rows:
        return []
    # 定位列：rows[0] 是表头
    head = rows[0]
    data = rows[1:]
    if not data:
        return []
    i_name = col_index(head, ("项目名称", "项目", "名称"))
    i_amt = col_index(head, ("金额",))
    i_qty = col_index(head, ("工程量", "单位", "量"))
    i_note = col_index(head, ("备注", "说明", "原话"))
    if i_name is None:
        i_name = 0
    items = []
    for cells in data:
        name = get_cell(cells, i_name)
        if not name or is_placeholder(name):
            continue
        # 第一列若是纯序号（1/2/3），往后顺延取名称
        if re.match(r"^\d{1,2}$", name) and len(cells) > 1:
            name = get_cell(cells, i_name + 1) or name
        if is_placeholder(name):
            continue
        amt = parse_money(get_cell(cells, i_amt)) if i_amt is not None else None
        qty = get_cell(cells, i_qty) if i_qty is not None else ""
        note = get_cell(cells, i_note) if i_note is not None else ""
        if not qty:
            # 工程量可能与金额同格
            qty = ""
        items.append({"name": name, "amount": amt, "qty": qty, "note": note})
    return items


# ---------------------------------------------------------------- 完整性
def check_required(text, items):
    """九项必看逐项判断：先看报价条目名，再看自查表勾选。"""
    blob = " ".join([it["name"] + " " + it["note"] for it in items])
    if not blob:
        blob = text
    res = []
    for label, keys in REQUIRED_ITEMS:
        ok = has(blob, keys)
        res.append((label, ok))
    return res


# ---------------------------------------------------------------- 可疑条目
def scan_suspicious(items, text):
    """在报价条目的名称+备注里找可疑表述。"""
    hits = []
    for it in items:
        blob = it["name"] + " " + it["note"]
        for tag, key, risk, act in SUSPECT:
            if has(blob, (key,)):
                hits.append((it["name"], tag, risk, act, it["amount"]))
    # 去重：同名项目只留一次
    seen = set()
    out = []
    for h in hits:
        if h[0] in seen:
            continue
        seen.add(h[0])
        out.append(h)
    return out


def scan_loose_suspicious(text):
    """报价单之外（如"对方有没有说哪些要另计"）命中的可疑表述。"""
    out = []
    for tag, key, risk, act in SUSPECT:
        if has(text, (key,)):
            out.append((tag, risk, act))
    return out


# ---------------------------------------------------------------- 付款
def check_payment(text):
    lines = text.splitlines()
    s, e = find_section(text, "付款安排", "付款")
    rows = table_rows(lines, s, e)
    got = []
    for cells in rows:
        name = get_cell(cells, 0)
        if not name or is_placeholder(name):
            continue
        pct = parse_pct(get_cell(cells, 1))
        if pct is None:
            continue
        got.append((name, pct))
    early = find_field(text, ("有没有要求开工前付", "开工前付"), "pct")
    # 用字段读值，不能全文搜「一次付清」——采集表那行填的是「否」
    allin = field_yes(text, ("有没有要求一次付清", "要求一次付清", "一次付清"))
    tail_amt = find_field(text, ("尾款留了多少", "尾款"), "money")
    has_tail = (tail_amt is not None and tail_amt > 0)
    return got, early, allin, has_tail


# ---------------------------------------------------------------- 增项
def check_extra(text):
    """读「四、增项情况」。只取两个真问题：哪些另计/不含、已经发生的增项。"""
    lines = text.splitlines()
    s, e = find_section(text, "增项情况")
    already = []
    stated = []
    for ln in lines[s:e]:
        if not is_row(ln):
            continue
        cells = split_row(ln)
        if not cells:
            continue
        key, desc = clean(cells[0]), get_cell(cells, 1)
        if is_placeholder(desc):
            continue
        if has(key, ("已经出现过", "已发生")):
            already.append(desc)
        elif has(key, ("另计", "不包含")):
            stated.append(desc)
    oral = has("\n".join(lines[s:e]), ("口头", "没写进合同", "未写进合同"))
    return already, stated, oral


def check_contract(text):
    """读「六、合同情况」：按行标签匹配条款，值列必须是明确的「有」。

    坑：采集表里值列是「有 / 无」两个选项（空着），
    用全文 `has(text, 条款名)` 判定会把**行标签本身**当成"合同里有这一条" → 全判成"有"。
    """
    lines = text.splitlines()
    s, e = find_section(text, "合同情况")
    got = set()
    for ln in lines[s:e]:
        if not is_row(ln):
            continue
        cells = split_row(ln)
        if not cells:
            continue
        label, val = clean(cells[0]), get_cell(cells, 1)
        if is_placeholder(val) or not val:
            continue
        t = norm(val)
        if t in ("有", "有!", "已写", "写了"):
            got.add(label)
    return got


# ---------------------------------------------------------------- 报告
def build_report(path, base=None):
    base = base or date.today()
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return None, "读取失败：%s" % e, None

    items = parse_quote_items(text)
    total = find_field(text, ("报价单总价", "总价"), "money")
    rooms = find_field(text, ("套内实测面积", "建筑面积", "房屋面积"), "int")
    mode = find_field(text, ("装修方式",))
    days = find_field(text, ("对方给的工期", "工期"), "int")
    item_count = find_field(text, ("报价单总项数", "总项数"), "int")
    old_house = has(text, ("二手房", "老破小"))

    if not items and total is None:
        return None, ("未能从文件里解析出报价信息。请确认填写了「二、报价单明细」表格"
                      "或「报价单总价」。"), None

    # 报告条目数
    n_items = item_count or len(items)
    total = total if total is not None else sum(
        it["amount"] for it in items if it["amount"] is not None)

    required = check_required(text, items)
    missing = [lab for lab, ok in required if not ok]
    suspicious = scan_suspicious(items, text)
    loose = scan_loose_suspicious(text)
    pay_rows, early_pct, allin, has_tail = check_payment(text)
    already, stated, oral = check_extra(text)
    contract_got = check_contract(text)

    # 风险计数
    risks = []
    if missing:
        risks.append(("缺项", len(missing), "报价单少了必看项，属于最常见的压总价手法"))
    if n_items < LOW_ITEMS:
        risks.append(("项数偏少", n_items, "同户型同档次少于 %d 项，多半是漏项压总价" % LOW_ITEMS))
    if suspicious or loose:
        risks.append(("可疑表述", len(suspicious) + len(loose), "报价单里有「按实际/另计/不含」这类开口条款"))
    if early_pct is not None and early_pct >= WARN_IF_GE80:
        risks.append(("开工前高比例", int(early_pct), "开工前付 %d%% 以上，资金极度不安全" % int(early_pct)))
    if allin:
        risks.append(("一次付清", 0, "一次付清出问题连人都找不到"))
    if not pay_rows:
        risks.append(("无付款节点", 0, "采集表里没填付款安排，无法核对节点风险"))
    if oral:
        risks.append(("口头增项", 0, "口头承诺的增项一律不认，除非写进合同"))
    if not has_tail:
        risks.append(("未留尾款", 0, "没留尾款，遗留问题就没抓手"))

    out = []
    A = out.append

    A("# 装修报价单核查（本地处理，不上传）")
    A("")
    A("- 基准日：%s ｜ 解析来源：%s" % (base.isoformat(), os.path.basename(path)))
    A("- 本核查只做**纸面判断**：不估市场价、不评价工艺、不判断师傅水平。")
    A("")

    # 一、摘要
    A("## 一、结论摘要")
    A("")
    A("- 装修方式：**%s**｜报价单总价：**%s 元**｜共 **%s** 项%s"
      % (mode or "【待现场填写】", fmt_money(total), n_items,
         ("（面积 %s ㎡）" % rooms) if rooms else ""))
    if days:
        A("- 对方承诺工期：%s 天" % days)
    A("- 风险共 **%d** 类%s" % (len(risks), "，最要紧的是：**%s**" % risks[0][0] if risks else ""))
    A("")
    A("| # | 风险 | 量化 | 为什么要紧 |")
    A("|---|---|---|---|")
    for i, (tag, val, why) in enumerate(risks, 1):
        v = ("%s 项" % val) if tag in ("缺项", "可疑表述") else (str(val) if val else "—")
        A("| %d | %s | %s | %s |" % (i, tag, v, why))
    A("")

    # 二、完整性
    A("## 二、九项必看项完整性")
    A("")
    A("| 项目 | 报价单里有没有 | 缺了会怎样 |")
    A("|---|---|---|")
    impact = {
        "拆除费": "进场第一天就被要求加钱",
        "垃圾清运": "清运量按车算，签完就报十几车",
        "水电改造": "报「一项 3000」，做完才知道拆了 60 米",
        "防水": "漏水返工，赔的是邻居",
        "瓦工": "拼砖、斜切、过门石被拆出来另收",
        "木工": "吊顶、柜子是最容易「惊喜」的两项",
        "油漆": "墙面开裂，基层没做是主因",
        "主材品牌型号": "「主材按市价」= 你自己跑建材市场",
        "工期与付款节点": "钱先付完，人跑了",
    }
    for label, ok in required:
        A("| %s | %s | %s |" % (label, "有" if ok else "**缺**", impact.get(label, "")))
    A("")
    if missing:
        A("> 缺 **%d** 项：%s。要求对方现在补进报价单并给出单价与数量，总价同步改。"
          % (len(missing), "、".join(missing)))
        A("")

    # 三、可疑条目
    A("## 三、可疑表述逐条")
    A("")
    if suspicious:
        A("| 出现在 | 判定 | 风险 | 现在怎么改 |")
        A("|---|---|---|---|")
        for name, tag, risk, act, amt in suspicious:
            A("| %s%s | %s | %s | %s |"
              % (name, ("（%s 元）" % fmt_money(amt)) if amt is not None else "",
                 tag, risk, act))
        A("")
    elif loose:
        A("报价单条目里没找到明显开口条款，但采集表其他位置出现了这些表述：")
        A("")
        for tag, risk, act in loose:
            A("- **%s**：%s → %s" % (tag, risk, act))
        A("")
    else:
        A("未发现「按实际 / 按市价 / 另计 / 不含」这类开口条款。")
        A("")

    # 四、注水信号
    A("## 四、单价与工程量注水信号")
    A("")
    A("| 信号 | 是否存在 | 怎么防 |")
    A("|---|---|---|")
    A("| 项数偏少 | %s | 拿同户型同档次的另外两份报价逐行对齐，**看项数不看总价** |"
      % ("**是**（%s 项 < %d）" % (n_items, LOW_ITEMS) if n_items < LOW_ITEMS else "否（%s 项）" % n_items))
    no_qty = [it["name"] for it in items if not it["qty"]]
    A("| 没写工程量 | %s | 只给总价不给量，结算全由对方说了算；要求按实测结算 |"
      % ("**是**（%d 项）" % len(no_qty) if no_qty else "否"))
    A("| 化整为零 | 需人工核对 | 要求合并同类项，只看合计 |")
    A("| 单价异常低 | 需自行比价 | 同项至少比三家，本表不估市场价 |")
    A("")
    if no_qty:
        A("> 以下项目没写工程量：%s" % "、".join(no_qty[:8]))
        A("")

    # 五、付款风险
    A("## 五、付款节点风险")
    A("")
    A("| 建议节点 | 累计上限 | 对应验收 | 你填的约定 | 是否放款 |")
    A("|---|---|---|---|---|")
    got_map = {clean(n): p for n, p in pay_rows}
    for name, cap, check in PAY_STAGES:
        mine = got_map.get(name)
        if mine is None:
            for k, v in got_map.items():
                if name[:2] in k:
                    mine = v
                    break
        if mine is None:
            A("| %s | ≤ %d%% | %s | 【待现场填写】 | ☐ |" % (name, cap, check))
        else:
            flag = "✅" if mine <= cap + 5 else "⚠️ 超上限"
            A("| %s | ≤ %d%% | %s | %d%% | %s ☐ |" % (name, cap, check, int(mine), flag))
    A("")
    if early_pct is not None and early_pct >= WARN_IF_GE80:
        A("> ⚠️ 采集表填「开工前付 %d%%」——**这是明确的红线**，见第四节「收手条件」。" % int(early_pct))
        A("")
    if allin:
        A("> ⚠️ 采集表提到**一次付清**——隐蔽工程出问题后返工，付款找不回人。")
        A("")
    if not has_tail:
        A("> 采集表里**没看到尾款/质保期满**安排。建议至少留 5% 到问题修完。")
        A("")

    # 六、增项应对
    A("## 六、增项：已发生的与该盯的")
    A("")
    if already:
        A("**已经发生的增项**（这些要一并写进合同或明确不认）：")
        A("")
        for d in already:
            A("- %s" % d)
        A("")
    else:
        A("采集表里没填已发生的增项。")
        A("")
    if stated:
        A("**对方声明要「另计 / 不包含」的**：")
        A("")
        for d in stated:
            A("- %s" % d)
        A("")
        A("> 每一项都要问清楚：现在写进报价单（改总价），还是签完再说。"
          "**签完再说的，一律不认。**")
        A("")
    if oral:
        A("> 采集表显示增项是**口头说的**。口头承诺一律不认——除非写进合同并双方签字。")
        A("")
    A("**三段话（照着说，把力气花在「写不写进合同」而不是「多少钱」上）**：")
    A("")
    A("第一段 · 摆事实")
    A("")
    A("> 「我们对照了另外几家的报价，你们这份共 %s 项，其中 ____ 没写。按现在这个口径，"
      "后面至少还要再加几项。我们不接受签完再加钱。」" % n_items)
    A("")
    A("第二段 · 给方案")
    A("")
    A("> 「如果这几项确实要算，请现在写进报价单，写明单价和数量，**总价一起改**。改完我们就签，也按新总价付款。」")
    A("")
    A("第三段 · 给底线")
    A("")
    A("> 「如果不能写进合同，我们就换一家。合同一旦签了，后面按合同走，谁的错谁承担。」")
    A("")

    # 七、合同六句话
    A("## 七、必须写进合同的六句话")
    A("")
    A("| # | 条款 | 建议表述（可直接抄） | 你现在的合同里有吗 |")
    A("|---|---|---|---|")
    for i, (k, v) in enumerate(CONTRACT_LINES, 1):
        has_it = any(has(g, (k,)) or has(g, (k.replace("合同", ""),)) for g in contract_got)
        A("| %d | %s | %s | %s |" % (i, k, v, "有" if has_it else "**无**"))
    A("")
    A("> 这六句不写进去，前面所有核查都白做——开口条款留着，签完一定加钱。")
    A("")

    # 八、隐蔽工程
    A("## 八、隐蔽工程验收（验收不过，不付下一笔）")
    A("")
    A("| 项 | 合格标准 | 你填的状态 |")
    A("|---|---|---|")

    def status(labels):
        """隐蔽工程状态：值列要么是真状态，要么标【待现场填写】。"""
        for line in text.splitlines():
            cells = split_row(line) if line.strip().startswith("|") else [line]
            i = col_index(cells, labels)
            if i is None:
                continue
            val = get_cell(cells, i + 1) if i + 1 < len(cells) else ""
            if not val:
                continue
            # 「做没做」「几小时」这类半截模板提示语不算状态
            if val.endswith(("做没做", "几小时", "结果")) or "/" in val:
                return "【待现场填写】"
            return val
        return "【待现场填写】"

    A("| 水电是否已封槽 | 未开工/已封槽未验/已验收 | %s |" % status(("水电是否已封槽",)))
    A("| 水管走向 | 横平竖直，该走顶不偷走地 | %s |" % status(("水管走向",)))
    A("| 强弱电分管 | 分开走，间距 ≥ 300mm | %s |" % status(("强弱电分管",)))
    A("| 单管穿线 | 一根管里没塞多根线 | %s |" % status(("单管穿线",)))
    A("| 承重结构开槽 | 梁柱承重墙**没有开槽** | %s |" % status(("承重墙梁柱", "承重结构开槽")))
    A("| 打压试验 | 稳压无持续掉压 | %s |" % status(("水管打压试验", "打压试验")))
    A("| 防水闭水试验 | 蓄水 ≥ 24 小时，楼下不漏 | %s |" % status(("防水闭水试验", "闭水试验")))
    A("")
    A("**四条收手条件**（出现就别再付钱）：")
    A("")
    A("1. 要求开工前付 80% 以上")
    A("2. 要求一次付清")
    A("3. 验收不合格却要求继续下一笔款")
    A("4. 水电已封槽但没有打压试验记录")
    A("")

    # 九、待办
    A("## 九、待办")
    A("")
    todo = []
    if missing:
        todo.append("向对方索要缺漏项的书面报价（%s），并要求总价同步改" % "、".join(missing))
    if suspicious or loose:
        todo.append("把「按实际/另计/不含」逐条换成具体数字或上限，书面确认")
    if n_items < LOW_ITEMS:
        todo.append("再拿 2 份同户型报价逐行对齐项数，确认是不是漏项")
    if not pay_rows or (early_pct is not None and early_pct >= WARN_IF_GE80):
        todo.append("重谈付款节点，压到开工 ≤30%、水电验收后累计 ≤50%")
    if allin:
        todo.append("拒绝一次付清，改为分节点付款")
    if not has_tail:
        todo.append("争取留 5% 尾款到质保期满")
    for k, _ in CONTRACT_LINES:
        if not any(has(g, (k,)) or has(g, (k.replace("合同", ""),)) for g in contract_got):
            todo.append("在合同里补上「%s」条款" % k)
    if oral:
        todo.append("把口头增项写成书面并签字，否则不认")
    todo.append("隐蔽工程（水电、防水）验收拍照留证，并让对方在验收单签字")
    if not todo:
        todo.append("报价单本身没发现明显问题；重点转向施工阶段的过程验收")
    for i, t in enumerate(todo, 1):
        A("%d. %s" % (i, t))
    A("")
    A("---")
    A("")
    A("**说明**：本报告不估市场价、不评价施工工艺、不代替现场监理与第三方验房；"
      "签约前建议至少比价三家，并让对方出具正式盖章报价单。")
    A("")

    body = "\n".join(out)
    meta = {"total": total, "items": n_items, "risks": len(risks),
            "missing": missing, "mode": mode or ""}
    return body, None, meta


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="装修报价单核查与增项防范")
    ap.add_argument("input", help="装修报价采集表 .md")
    ap.add_argument("--base", help="基准日 YYYY-MM-DD（默认今天）")
    ap.add_argument("--out", help="输出文件（默认打印到屏幕）")
    ap.add_argument("--json", action="store_true", help="仅输出 JSON 摘要")
    a = ap.parse_args(argv)

    base = None
    if a.base:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", a.base)
        if not m:
            print("基准日格式应为 YYYY-MM-DD")
            return 2
        base = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    body, err, meta = build_report(a.input, base)
    if body is None or meta is None:
        print(err if err is not None else "构建失败")
        return 2

    if a.json:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    if a.out:
        d = os.path.dirname(os.path.abspath(a.out))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(body)
        print("已写出：%s（%d 字，%d 段）" % (a.out, len(body), body.count("## ")))
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
