# -*- coding: utf-8 -*-
"""预付卡退费与商家跑路维权核查。
读 Markdown 采集表（| 字段 | 值 | 或 字段：值），输出结构化核查报告。
字段未填一律按「待补正 / 有风险」处理，绝不判通过。
"""
import sys, os, re, json, argparse, datetime

# ---------- 通用工具 ----------
def norm(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("　", " ").replace(" ", " ")
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("，", ",").replace("：", ":")
    return s.strip().lower()

def hit_any(text, words):
    if text is None:
        return False
    t = norm(text)
    if t == "":
        return False
    for w in words:
        if norm(w) in t:
            return True
    return False

def has_content(t):
    return t is not None and norm(t) != ""

def parse_num(s):
    if s is None:
        return None
    t = str(s).replace(",", "").replace("，", "")
    t = re.sub(r"[¥￥元人民币RMB$]", "", t)
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    if not m:
        return None
    return float(m.group(0))

def money(v):
    if v is None:
        return "—"
    return "¥" + format(v, ",.2f").rstrip("0").rstrip(".")

def fmt_num(v):
    if v is None:
        return "—"
    s = format(v, ",.2f").rstrip("0").rstrip(".")
    return s

def filled(v):
    if v is None:
        return False
    s = str(v).strip()
    if s == "":
        return False
    placeholder = ["有", "无", "待填", "填什么", "做没做", "未填", "暂无", "未知", "请填写",
                   "示例", "此处", "xxx", "？", "?", "—", "-", "无记录", "没有记录"]
    if s in placeholder:
        return False
    if "填" in s and len(s) <= 6:
        return False
    return True

def unknown(v):
    if v is None:
        return True
    s = norm(v)
    if s == "" or s in ["无", "未填", "暂无", "未知", "请填写", "没有", "不知道", "不记得", "没注意"]:
        return True
    return False

def yes(v):
    if v is None:
        return False
    s = norm(v)
    return hit_any(s, ["是", "有", "已", "过", "ok", "对", "要", "愿意", "能", "可以", "yes", "y"])

def no(v):
    if v is None:
        return False
    s = norm(v)
    return hit_any(s, ["否", "无", "没", "未", "不", "没有", "不能", "不办", "拒绝", "no", "n"])

def get_text(block, field_aliases, default=""):
    if block is None:
        return default
    lines = block.splitlines()
    best = None
    for alias in sorted(field_aliases, key=len, reverse=True):
        a = norm(alias)
        for ln in lines:
            s = ln.strip()
            if s.startswith("|"):
                parts = [p.strip() for p in s.strip("|").split("|")]
                if len(parts) >= 2:
                    if norm(parts[0]) == a or a in norm(parts[0]):
                        cand = parts[1].replace("|", " ").strip()
                        if filled(cand):
                            best = cand
            else:
                if "：" in s or ":" in s:
                    k, _, v = re.split(r"[:：]", s, maxsplit=1)
                    if norm(k) == a or a in norm(k):
                        cand = v.replace("|", " ").strip()
                        if filled(cand):
                            best = cand
    return best if best is not None else default

# ---------- 领域词表 ----------
INDUSTRY_TYPES = [
    ("健身私教预付", ["健身", "私教", "游泳", "瑜伽", "办卡健身", "会员健身"]),
    ("美容美发预付", ["美容", "美发", "理发", "美甲", "美睫", "护肤", "养生", "SPA", "采耳"]),
    ("教育培训预付", ["培训", "教育", "辅导", "早教", "舞蹈", "乐器", "书法", "学科", "健身课包", "课程包"]),
    ("餐饮商超预付", ["餐饮", "饭店", "火锅", "奶茶", "咖啡", "商超", "超市", "水果", "烘焙", "会员储值"]),
    ("生活服务预付", ["洗衣", "洗车", "家政", "宠物", "摄影", "健身卡", "洗浴", "足疗"]),
]

# 商家经营状态：跑路类（最严重）
RUNAWAY_WORDS = ["跑路", "失联", "联系不上", "找不到", "人去楼空", "关门", "卷款", "老板跑", "撤店", "倒闭", "破产", "注销", "查封"]
# 经营异常但还在
ABNORMAL_WORDS = ["转让", "停业", "歇业", "搬走", "换老板", "缩减", "拖延营业", "限制消费"]
# 正常
NORMAL_WORDS = ["正常经营", "还在营业", "正常营业", "照常", "开门"]

# 退款条款 / 承诺
REFUND_BAD = ["概不退款", "不退", "不予退还", "一经售出", "概不退换", "不退款", "不得退", "不可退"]
REFUND_OK = ["随时退", "可退", "按比例退", "余额退", "未消费退", "可全额退", "支持退"]
REFUND_RATIO = ["按比例", "扣除", "手续费", "折旧", "已消费部分", "实付比例"]

# 证据
EVIDENCE_ITEMS = [
    ("合同/协议", ["合同", "协议", "会员协议", "办卡协议"]),
    ("付款凭证", ["转账", "支付记录", "微信支付", "支付宝", "银行流水", "刷卡单"]),
    ("收据/发票", ["收据", "发票", "小票", "凭证"]),
    ("会员卡/卡号", ["会员卡", "卡号", "储值卡", "实体卡"]),
    ("聊天记录", ["聊天", "微信记录", "承诺截图", "销售对话"]),
    ("宣传材料", ["宣传单", "海报", "朋友圈", "广告", "承诺文案"]),
    ("其他消费者", ["其他会员", "维权群", "集体", "群友"]),
]

PATHS = [
    "立刻固定证据：把合同、转账记录、聊天截图、会员卡全部拍照备份，原件不要删。",
    "确认商家是否「单用途预付卡」未备案：查发卡方营业执照与商务部门备案信息。",
    "向 12315（全国消费者投诉热线 / 全国 12315 平台）投诉，写明金额、卡种、商家现状。",
    "向发卡方所在地商务主管部门（单用途预付卡监管）举报未备案 / 违规发卡。",
    "向市场监管部门举报「虚假宣传 / 格式条款无效（概不退款）」。",
    "商家已失联 / 卷款且金额较大：带证据到公安机关报案，争取按合同诈骗或非法集资立案。",
    "联合其他消费者集体维权，人数和金额越大越容易立案与媒体关注。",
]

# 单用途预付卡监管阈值
FILING_THRESHOLD = 10000  # 规模发卡企业需备案，具体以当地商务部门为准

# ---------- 解析采集表 ----------
def parse_md(text):
    """返回 dict：字段名 -> 值。支持 | 字段 | 值 | 与 字段：值。"""
    data = {}
    if not text:
        return data
    text = text.replace("|", " | ")
    lines = text.splitlines()
    for ln in lines:
        s = ln.strip()
        if s.startswith("|") or s.count("|") >= 2:
            parts = [p.strip() for p in s.strip("|").split("|")]
            if len(parts) >= 2 and parts[0] and not parts[0].startswith("-"):
                data[parts[0]] = parts[1]
        elif ("：" in s or ":" in s):
            k, _, v = re.split(r"[:：]", s, maxsplit=1)
            k = k.strip().lstrip("-").strip()
            if k and v.strip():
                data[k] = v.strip()
    return data

def build_fields():
    return [
        ("merchant", "商家/发卡方名称"),
        ("industry", "所属行业"),
        ("card_type", "预付卡类型"),
        ("total_paid", "预付总额（元）"),
        ("consumed", "已消费金额（元）"),
        ("remain_should", "按约定应退余额（元）"),
        ("contract", "是否有合同/协议"),
        ("refund_clause", "退款条款/商家承诺内容"),
        ("merchant_status", "商家当前经营状态"),
        ("filed", "是否备案（单用途预付卡）"),
        ("pay_method", "付款方式"),
        ("has_receipt", "有哪些凭证"),
        ("promise", "销售当时承诺（随时退/不退等）"),
        ("delay", "拖延/拒退情况"),
        ("complaint_tried", "已尝试的投诉渠道"),
        ("involve_count", "涉及人数/总金额"),
        ("occur_date", "办卡时间"),
    ]

FIELD_ALIAS = {
    "merchant": ["商家", "发卡方", "店名", "公司", "机构名称", "名称"],
    "industry": ["行业", "领域", "类型行业"],
    "card_type": ["卡种", "预付卡类型", "卡类型", "会员类型"],
    "total_paid": ["预付总额", "充值金额", "办卡金额", "总额", "付款总额", "交了多少"],
    "consumed": ["已消费", "已花", "消费金额", "用了多少", "已消费金额"],
    "remain_should": ["应退余额", "剩余应退", "可退金额", "按约定应退", "未消费余额"],
    "contract": ["合同", "协议", "有没有合同", "签合同"],
    "refund_clause": ["退款条款", "退款约定", "退费规则", "退款内容", "条款"],
    "merchant_status": ["商家现状", "经营状态", "店铺状态", "现在情况", "是否营业"],
    "filed": ["备案", "是否备案", "单用途备案"],
    "pay_method": ["付款方式", "怎么付的", "支付渠道"],
    "has_receipt": ["凭证", "证据", "有什么凭证", "材料"],
    "promise": ["承诺", "当时说", "销售承诺", "口头承诺"],
    "delay": ["拖延", "拒退", "推脱", "一直拖", "情况"],
    "complaint_tried": ["投诉", "已投诉", "举报过", "找过谁"],
    "involve_count": ["人数", "涉及人数", "总金额其他", "其他消费者"],
    "occur_date": ["办卡时间", "时间", "什么时候办"],
}

def extract(f):
    out = {}
    for key, _ in build_fields():
        out[key] = get_text(f.get("_raw", ""), FIELD_ALIAS.get(key, [key]), "")
    return out

# ---------- 分类 ----------
def classify(f):
    txt = " | ".join([str(f.get(k, "")) for k in ("industry", "card_type", "merchant_status", "refund_clause", "promise", "delay") if filled(f.get(k, ""))])
    if not has_content(txt):
        return []
    res = []
    for lbl, ws in INDUSTRY_TYPES:
        if hit_any(txt, ws):
            res.append(lbl)
    if hit_any(txt, RUNAWAY_WORDS):
        res.append("商家跑路/失联")
    if hit_any(txt, REFUND_BAD):
        res.append("格式条款不退")
    return res

# ---------- 核查函数（每个独立判断，不提前 return） ----------
def checks_status(f):
    out = []
    st = f.get("merchant_status", "")
    if unknown(st):
        out.append(("商家经营状态", "待补正", "请填写商家当前是正常营业、转让、停业还是失联/跑路。"))
        return out
    if hit_any(st, RUNAWAY_WORDS):
        out.append(("商家经营状态", "不通过",
                    "商家已**失联/跑路/倒闭**，普通退款已无意义。"
                    "**立刻做三件事**：① 固定所有证据（合同、转账、聊天、会员卡）；"
                    "② 向公安机关报案，争取按合同诈骗或非法集资立案；"
                    "③ 联合其他消费者集体维权，人数和金额越大越易立案。"))
        return out
    if hit_any(st, ABNORMAL_WORDS):
        out.append(("商家经营状态", "有风险",
                    "商家出现**转让/停业/缩水**迹象，退卡难度上升。"
                    "尽快书面提出退款要求并留痕，避免商家彻底消失后再难追。"))
        return out
    if hit_any(st, NORMAL_WORDS) and not hit_any(st, RUNAWAY_WORDS + ABNORMAL_WORDS):
        out.append(("商家经营状态", "有风险",
                    "商家仍在营业，应优先走协商+12315 投诉拿回余额，不必立刻报警。"))
        return out
    out.append(("商家经营状态", "有风险", "请明确商家现状，不同状态维权路径完全不同。"))
    return out

def checks_contract(f):
    out = []
    c = f.get("contract", "")
    if hit_any(c, ["无", "没签", "没有合同", "未签", "口头", "没合同"]):
        out.append(("合同与条款", "有风险",
                    "**无书面合同**：退费只能靠转账记录、聊天承诺、宣传材料举证。"
                    "这些一样可作证据，但举证更费力，尽快全部固定。"))
    elif unknown(c) and not hit_any(c, ["有", "签"]):
        out.append(("合同与条款", "待补正", "请说明是否有书面合同/会员协议。"))
    else:
        out.append(("合同与条款", "有风险", "已有合同，重点看退款条款与格式条款是否有效（见下项）。"))
    clause = f.get("refund_clause", "")
    if unknown(clause):
        out.append(("退款条款效力", "待补正", "请摘录合同或商家承诺里的退款约定原文。"))
    elif hit_any(clause, REFUND_BAD):
        out.append(("退款条款效力", "不通过",
                    "「概不退款 / 一经售出不退」属于**格式条款**，明显加重消费者责任、排除主要权利，"
                    "依法**无效**。可主张全额退还未消费部分，并向市场监管举报该条款。"))
    elif hit_any(clause, REFUND_OK):
        out.append(("退款条款效力", "通过", "退款条款对消费者有利，可据此直接要求退还未消费余额。"))
    elif hit_any(clause, REFUND_RATIO):
        out.append(("退款条款效力", "有风险", "按比例/扣手续费退款，需核算扣除是否合理，明显高于实际损失的扣留可主张无效。"))
    else:
        out.append(("退款条款效力", "有风险", "条款表述模糊，建议按「未消费余额应退」主张，并留好凭证。"))
    return out

def calc_balance(f):
    total = parse_num(f.get("total_paid", ""))
    consumed = parse_num(f.get("consumed", ""))
    remain = parse_num(f.get("remain_should", ""))
    if total is None:
        return None, None, None
    cons = consumed if consumed is not None else 0.0
    should = remain if remain is not None else max(total - cons, 0.0)
    return total, cons, should

def checks_balance(f):
    out = []
    total, cons, should = calc_balance(f)
    if total is None:
        out.append(("应退金额核算", "待补正", "请填写预付总额与已消费金额，才能算出应退余额。"))
        return out
    if should <= 0:
        out.append(("应退金额核算", "有风险",
                    "按已填数据，未消费余额为 0 或为负，**可能已几乎消费完**，可退空间很小。"
                    "若实际还有余额未被计入，请补全「按约定应退余额」。"))
    else:
        out.append(("应退金额核算", "有风险",
                    "预付总额 %s，已消费 %s，**未消费应退约 %s**。"
                    "这是你主张退款的核心金额，所有凭证都要围绕它固定。"
                    % (money(total), money(cons), money(should))))
    return out

def checks_filed(f):
    out = []
    fl = f.get("filed", "")
    total, _, _ = calc_balance(f)
    if unknown(fl):
        out.append(("备案与监管", "待补正", "请确认该卡是否属「单用途预付卡」及发卡方是否备案。"))
        return out
    if hit_any(fl, ["未备案", "没有备案", "不知", "不清楚", "没备案"]):
        out.append(("备案与监管", "有风险",
                    "单用途预付卡发卡企业通常需在**商务主管部门备案**并接受资金存管。"
                    "未备案可向商务部门举报，这是施压退款的有效抓手。"))
        return out
    if hit_any(fl, ["已备案", "有备案", "备案过"]):
        out.append(("备案与监管", "通过", "发卡方已备案，可要求监管部门协助调解退款。"))
        return out
    out.append(("备案与监管", "有风险", "备案情况不明，建议向商务部门查询发卡方备案状态。"))
    return out

def checks_evidence(f):
    out = []
    rec = f.get("has_receipt", "")
    if unknown(rec):
        out.append(("证据齐全度", "待补正", "请列出你手头有哪些凭证（合同/转账/收据/聊天/会员卡）。"))
        return out
    got = []
    miss = []
    for lbl, ws in EVIDENCE_ITEMS:
        if hit_any(rec, ws):
            got.append(lbl)
        else:
            miss.append(lbl)
    if len(got) >= 4:
        out.append(("证据齐全度", "通过", "凭证较齐（%s），足以支撑投诉与报案。" % "、".join(got)))
    elif len(got) >= 2:
        out.append(("证据齐全度", "有风险", "已有 %s，缺 %s。尽快补齐转账记录与聊天截图，缺一都可能被商家抵赖。"
                    % ("、".join(got), "、".join(miss[:3]))))
    else:
        out.append(("证据齐全度", "不通过", "凭证严重不足（仅 %s）。**没有转账记录和合同，退款极难**。"
                    "尽快从支付平台导出流水、从聊天里找销售承诺截图。" % "、".join(got)))
    return out

def checks_promise(f):
    out = []
    p = f.get("promise", "")
    if unknown(p):
        out.append(("销售承诺", "待补正", "请写出销售当时怎么承诺退款的（随时退/不退/按比例）。"))
        return out
    if hit_any(p, REFUND_OK):
        out.append(("销售承诺", "通过", "销售承诺可退，截图留存即可作为有利证据。"))
    elif hit_any(p, REFUND_BAD):
        out.append(("销售承诺", "有风险", "销售说不退，但若与合同/宣传矛盾，属虚假宣传，可一并举报。"))
    else:
        out.append(("销售承诺", "有风险", "承诺表述不清，以书面合同和聊天截图为准。"))
    return out

def checks_delay(f):
    out = []
    d = f.get("delay", "")
    if unknown(d):
        out.append(("拖延与拒退", "待补正", "请说明商家是如何拖延或拒绝退款的。"))
        return out
    if hit_any(d, ["起诉", "已报案", "已立案", "公安", "法院"]):
        out.append(("拖延与拒退", "有风险", "已进入司法/报案程序，按法律流程推进，本报告仅作材料参考。"))
        return out
    if hit_any(d, ["一直拖", "推", "不回", "拒", "拉黑", "几个月", "半年", "一年"]):
        out.append(("拖延与拒退", "有风险", "商家长期拖延，普通协商已失效，**立刻转 12315 + 商务/市场监管举报**，必要时报警。"))
        return out
    out.append(("拖延与拒退", "有风险", "请明确拖延细节，越早固定证据越有利。"))
    return out

def checks_complaint(f):
    out = []
    c = f.get("complaint_tried", "")
    if unknown(c):
        out.append(("已尝试渠道", "待补正", "请说明是否已投诉过（12315/商务/市场监管/公安）。"))
        return out
    if hit_any(c, ["未投诉", "没投诉", "还没", "没有投诉"]):
        out.append(("已尝试渠道", "有风险", "尚未投诉，**现在就打 12315 / 上全国 12315 平台**，这是最快的施压入口。"))
        return out
    if hit_any(c, ["12315", "商务", "市场监管", "公安", "举报", "投诉过"]):
        out.append(("已尝试渠道", "通过", "已在监管渠道投诉，保持跟进并记录受理编号，必要时升级到公安报案。"))
        return out
    out.append(("已尝试渠道", "有风险", "请明确已尝试哪些渠道及受理结果。"))
    return out

def evidence_gap(f):
    rec = f.get("has_receipt", "")
    miss = []
    for lbl, ws in EVIDENCE_ITEMS:
        if unknown(rec) or not hit_any(rec, ws):
            miss.append(lbl)
    return miss

def path_steps(f):
    return PATHS

def todo_list(f):
    todos = []
    st = f.get("merchant_status", "")
    if hit_any(st, RUNAWAY_WORDS):
        todos.append("立刻固定全部证据并到公安机关报案")
        todos.append("联合其他消费者集体维权，统计总人数与总金额")
    else:
        todos.append("书面提出退款要求并保留送达证据")
        todos.append("打 12315 / 上全国 12315 平台投诉")
    if unknown(f.get("has_receipt", "")) or len(evidence_gap(f)) >= 3:
        todos.append("补齐转账记录、合同、聊天截图三类核心凭证")
    if hit_any(f.get("filed", ""), ["未备案", "没备案", "不知"]):
        todos.append("向商务主管部门查询发卡方备案状态并举报未备案")
    if hit_any(f.get("refund_clause", ""), REFUND_BAD):
        todos.append("就「概不退款」格式条款向市场监管部门举报其无效")
    todos.append("把本报告与所有材料整理成一个文件夹备用")
    return todos

def render(f):
    L = []
    types = classify(f)
    status_items = checks_status(f)
    contract_items = checks_contract(f)
    balance_items = checks_balance(f)
    filed_items = checks_filed(f)
    ev_items = checks_evidence(f)
    prom_items = checks_promise(f)
    delay_items = checks_delay(f)
    comp_items = checks_complaint(f)

    L.append("## 一、结论摘要")
    total, cons, should = calc_balance(f)
    if hit_any(f.get("merchant_status", ""), RUNAWAY_WORDS):
        L.append("商家已失联/跑路，**普通退款通道失效**，建议立刻报警+集体维权。"
                 "未消费应退约 %s。" % (money(should) if should is not None else "—"))
    elif any(s == "不通过" for _, s, _ in contract_items + ev_items + status_items):
        L.append("存在**不通过**项（条款无效/证据不足/商家跑路），退款需走投诉或报案施压。"
                 "未消费应退约 %s。" % (money(should) if should is not None else "—"))
    else:
        L.append("目前以协商+12315 投诉为主，未消费应退约 %s，按本报告逐项补正后胜算较高。"
                 % (money(should) if should is not None else "—"))
    if types:
        L.append("识别类型：" + "、".join(types))

    L.append("## 二、商家经营状态核查")
    for name, st, msg in status_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 三、合同与退款条款核查")
    for name, st, msg in contract_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 四、应退金额核算")
    for name, st, msg in balance_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 五、备案与监管")
    for name, st, msg in filed_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 六、销售承诺核查")
    for name, st, msg in prom_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 七、证据清单与缺口")
    for name, st, msg in ev_items:
        L.append("| %s | %s | %s |" % (name, st, msg))
    gap = evidence_gap(f)
    if gap:
        L.append("**证据缺口**：" + "、".join(gap) + "（尽快补齐）")
    else:
        L.append("**证据缺口**：暂无明显缺口。")

    L.append("## 八、拖延与拒退情况")
    for name, st, msg in delay_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 九、已尝试投诉渠道")
    for name, st, msg in comp_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 十、维权路径（七步）")
    for i, p in enumerate(path_steps(f), 1):
        L.append("%d. %s" % (i, p))

    L.append("## 十一、待办补正动作")
    for t in todo_list(f):
        L.append("- %s" % t)

    L.append("## 十二、边界与纪律")
    L.append("本报告依《单用途商业预付卡管理办法》等通用规则整理，不替代专业法律意见，"
             "最终以主管部门或司法机关认定为准。金额以你提供的凭证为准，未填项不按通过处理。")
    return "\n\n".join(L)

def to_json(f):
    types = classify(f)
    items = (checks_status(f) + checks_contract(f) + checks_balance(f) + checks_filed(f)
             + checks_evidence(f) + checks_promise(f) + checks_delay(f) + checks_complaint(f))
    return {
        "结论": "不通过" if any(s == "不通过" for _, s, _ in items) else
                ("有风险" if any(s == "有风险" for _, s, _ in items) else "待补正"),
        "类型": types,
        "风险项": [{"项": n, "状态": s, "说明": m} for n, s, m in items],
        "应退余额": (calc_balance(f)[2]),
        "证据缺口": evidence_gap(f),
        "待办": todo_list(f),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md", nargs="?", default="样例.md")
    ap.add_argument("--base", default=datetime.date.today().isoformat())
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        raw = open(args.md, encoding="utf-8").read()
    except Exception as e:
        sys.stderr.write("读取失败: %s\n" % e)
        return 2
    d = parse_md(raw)
    f = extract({"_raw": raw})
    for k, v in d.items():
        for key, alias in FIELD_ALIAS.items():
            if norm(k) in [norm(a) for a in alias] or norm(k) == norm(key):
                f[key] = v
    if args.json:
        print(json.dumps(to_json(f), ensure_ascii=False, indent=2))
        return 0
    rep = render(f)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(rep)
        sys.stderr.write("已写出: %s\n" % args.out)
    else:
        print(rep)
    return 0

if __name__ == "__main__":
    sys.exit(main())
