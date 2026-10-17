# -*- coding: utf-8 -*-
"""12315 投诉热线正确用法与维权路径核查。
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
    if s == "" or s in ["无", "未填", "暂无", "未知", "请填写", "没有", "不知道", "不记得", "没注意", "待填", "待填写"]:
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
                    head = norm(parts[0])
                    if head == a or head == norm(alias):
                        cand = parts[1].replace("|", " ").strip()
                        if filled(cand):
                            best = cand
            else:
                if "：" in s or ":" in s:
                    k, _, v = re.split(r"[:：]", s, maxsplit=1)
                    head = norm(k.strip().lstrip("-").strip())
                    if head == a or head == norm(alias):
                        cand = v.replace("|", " ").strip()
                        if filled(cand):
                            best = cand
    return best if best is not None else default

# ---------- 领域词表 ----------
# 投诉类型（用于分类与受理判断）
COMPLAINT_TYPES = [
    ("网络购物纠纷", ["网购", "淘宝", "京东", "拼多多", "抖音", "直播间", "电商", "下单", "网店", "旗舰店"]),
    ("实体店消费", ["实体店", "门店", "商场", "超市", "便利店", "专柜", "线下店"]),
    ("餐饮食品", ["餐饮", "饭店", "外卖", "食品", "吃", "餐厅", "奶茶", "过期"]),
    ("美容健身服务", ["美容", "美发", "健身", "美甲", "养生", "SPA", "医美", "护肤"]),
    ("维修售后", ["维修", "售后", "安装", "保修", "三包", "修理"]),
    ("预付卡", ["预付", "会员卡", "储值", "办卡", "余额", "健身卡"]),
    ("虚假宣传", ["虚假", "夸大", "旺旺", "刷单", "好评", "代言", "假", "宣传不符"]),
    ("价格违法", ["价格", "标价", "宰客", "乱收费", "天价", "翻倍", "虚高"]),
    ("产品质量", ["质量", "伪劣", "假冒", "三无", "缺陷", "损坏", "漏水", "开裂"]),
]

# 12315 不受理 / 引导其他渠道的情形
OUT_OF_SCOPE = [
    ("劳资纠纷", ["工资", "社保", "劳动合同", "工伤", "辞退", "加班", "老板欠"]),
    ("婚姻家事", ["离婚", "抚养", "继承", "家暴", "赡养"]),
    ("刑事诈骗", ["被骗转账", "杀猪盘", "电信诈骗", "网络诈骗", "洗钱", "被诈骗"]),
    ("借贷纠纷", ["借的钱", "欠款", "网贷", "借条", "放贷"]),
    ("二手房买卖", ["二手房", "买房", "房产过户", "中介费购房", "房东违约"]),
    ("医疗纠纷", ["医疗事故", "医院", "误诊", "看病", "手术", "医生"]),
    ("物业服务", ["物业费", "停车费物业", "业委会", "小区物业"]),
]
# 注意：刑事诈骗虽可先举报，但核心走公安；这里提示分流

# 证据
EVIDENCE_ITEMS = [
    ("订单/合同号", ["订单", "合同号", "单号", "交易号", "编号"]),
    ("支付凭证", ["转账", "支付记录", "微信支付", "支付宝", "银行流水", "刷卡", "付款截图"]),
    ("聊天记录", ["聊天", "微信记录", "客服对话", "承诺截图", "销售对话"]),
    ("商品照片/视频", ["照片", "视频", "实物图", "开箱", "损坏图"]),
    ("发票/收据", ["发票", "收据", "小票", "凭证", "票据"]),
    ("检测/鉴定报告", ["检测", "鉴定", "质检", "报告", "认证"]),
    ("宣传页面", ["宣传单", "海报", "朋友圈", "广告页", "商品详情页", "直播回放"]),
]

# 维权渠道
CHANNELS = [
    "全国 12315 平台（网站 ss12315.org / APP / 微信小程序「12315」）：在线提交投诉，自动分转商家所在地市场监管局。",
    "拨打 12315 热线（加商家所在地区号，如上海 021-12315）：人工受理，适合不擅长手机操作的人群。",
    "全国 12315 平台「举报」入口（与「投诉」不同）：针对违法经营行为（虚假宣传、价格违法、无照经营）向监管部门举报。",
    "黑猫投诉 / 消费保等第三方平台：公开曝光施压，适合商家重视口碑的情况。",
    "商家所在地市场监管局 / 消协（12315 即整合了原消协职能）：线下递交材料。",
    "调解不成或对结果不服：可向法院起诉（小额诉讼程序，50 元起步），或就行政行为申请复议。",
]

# 诉求类型与法定依据
CLAIM_TYPES = [
    ("退款", ["退款", "退钱", "退货退款", "返还"]),
    ("退一赔三", ["假一赔三", "退一赔三", "三倍", "欺诈赔偿", "赔偿三倍"]),
    ("退一赔十/千元", ["十倍", "假一赔十", "食品安全法", "一千", "1000", "保底千元"]),
    ("换货维修", ["换货", "维修", "修理", "换新"]),
    ("查处", ["查处", "罚款", "关停", "吊销", "立案调查"]),
]

# ---------- 解析采集表 ----------
def parse_md(text):
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
            parts = re.split(r"[:：]", s, maxsplit=1)
            if len(parts) == 2:
                k, v = parts
                k = k.strip().lstrip("-").strip()
                if k and v.strip():
                    data[k] = v.strip()
    return data

def build_fields():
    return [
        ("merchant", "被投诉对象（商家/平台名称）"),
        ("target_type", "对象类型"),
        ("goods", "商品或服务类型"),
        ("amount", "涉及金额（元）"),
        ("issue", "争议问题"),
        ("platform", "购买平台"),
        ("order_no", "订单号/合同号"),
        ("has_pay", "是否有支付凭证"),
        ("has_chat", "是否有聊天记录"),
        ("has_contract", "是否有合同/发票"),
        ("has_photo", "是否有商品照片/视频"),
        ("negotiated", "是否已与商家协商"),
        ("neg_result", "协商结果"),
        ("merchant_loc", "商家所在地"),
        ("deal_date", "交易时间（年月）"),
        ("expectation", "期望诉求"),
        ("special", "是否涉及特殊品类"),
        ("evidence", "已有证据清单"),
    ]

FIELD_ALIAS = {
    "merchant": ["被投诉对象（商家/平台名称）", "被投诉对象", "商家", "平台名称", "店名", "公司", "机构", "卖方", "名称"],
    "target_type": ["对象类型", "商家类型", "类型"],
    "goods": ["商品或服务类型", "商品类型", "买的东西", "服务类型"],
    "amount": ["涉及金额（元）", "涉及金额", "金额", "多少钱", "损失", "价款"],
    "issue": ["争议问题", "问题", "纠纷类型", "出了什么事", "事由"],
    "platform": ["购买平台", "平台", "在哪买的", "渠道"],
    "order_no": ["订单号/合同号", "订单号", "合同号", "单号", "交易编号"],
    "has_pay": ["是否有支付凭证", "支付凭证", "有没有付款凭证", "转账记录"],
    "has_chat": ["是否有聊天记录", "聊天记录", "有没有聊天", "客服对话"],
    "has_contract": ["是否有合同/发票", "合同发票", "有没有合同", "发票"],
    "has_photo": ["是否有商品照片/视频", "照片视频", "有没有照片", "实物图"],
    "negotiated": ["是否已与商家协商", "是否协商", "协商过", "找过商家"],
    "neg_result": ["协商结果", "商家怎么回"],
    "merchant_loc": ["商家所在地", "所在地", "商家地址", "哪里"],
    "deal_date": ["交易时间（年月）", "交易时间", "时间", "什么时候", "购买日期"],
    "expectation": ["期望诉求", "诉求", "想要什么", "要求"],
    "special": ["是否涉及特殊品类", "特殊品类", "是否涉及食品", "食品药品"],
    "evidence": ["已有证据清单", "证据清单", "有什么材料", "手头材料"],
}

def extract(f):
    out = {}
    for key, _ in build_fields():
        out[key] = get_text(f.get("_raw", ""), FIELD_ALIAS.get(key, [key]), "")
    return out

# ---------- 分类 ----------
def classify(f):
    txt = " | ".join([str(f.get(k, "")) for k in ("goods", "issue", "platform", "expectation", "special") if filled(f.get(k, ""))])
    if not has_content(txt):
        return []
    res = []
    for lbl, ws in COMPLAINT_TYPES:
        if hit_any(txt, ws):
            res.append(lbl)
    return res

# ---------- 核查函数（每个独立判断，不提前 return） ----------
def checks_scope(f):
    out = []
    issue = f.get("issue", "")
    goods = f.get("goods", "")
    full = issue + " " + goods
    if not filled(issue) and not filled(goods):
        out.append(("受理范围核查", "待补正", "请填写争议问题（质量/虚假宣传/不发货/价格等）与商品类型，才能判断 12315 是否受理。"))
        return out
    # 先判断是否落入不受理范围
    for lbl, ws in OUT_OF_SCOPE:
        if hit_any(full, ws):
            guide = {
                "劳资纠纷": "12315 不受理劳资纠纷，请向劳动监察（12333）或劳动仲裁申请。",
                "婚姻家事": "12315 不受理婚姻家事，请走法院民事诉讼。",
                "刑事诈骗": "被诈骗转账属刑事案件，请**立刻拨打 110 或到派出所报案**，12315 无法处理赃款追回。",
                "借贷纠纷": "12315 不受理借贷，请凭借条向法院起诉。",
                "二手房买卖": "二手房买卖纠纷走住建部门或法院，12315 不受理房屋交易。",
                "医疗纠纷": "医疗纠纷请向卫健委投诉或医疗纠纷调解委员会申请鉴定。",
                "物业服务": "物业费争议请通过业委会或法院解决，12315 不受理。",
            }.get(lbl, "该事项非 12315 受理范围，请走对应主管部门。")
            out.append(("受理范围核查", "不通过", "**不在 12315 受理范围**（%s）。%s" % (lbl, guide)))
            return out
    # 受理类
    out.append(("受理范围核查", "通过", "属于消费者权益争议，12315 可受理（商品质量、虚假宣传、不退款、价格违法等）。"))
    return out

def checks_evidence(f):
    out = []
    ev = f.get("evidence", "")
    # 综合判断各类证据字段
    has_pay = yes(f.get("has_pay", "")) or hit_any(ev, EVIDENCE_ITEMS[1][1])
    has_chat = yes(f.get("has_chat", "")) or hit_any(ev, EVIDENCE_ITEMS[2][1])
    has_order = filled(f.get("order_no", "")) or hit_any(ev, EVIDENCE_ITEMS[0][1])
    has_photo = yes(f.get("has_photo", "")) or hit_any(ev, EVIDENCE_ITEMS[3][1])
    has_invoice = yes(f.get("has_contract", "")) or hit_any(ev, EVIDENCE_ITEMS[4][1])
    score = sum([has_pay, has_chat, has_order, has_photo, has_invoice])
    if not filled(ev) and score == 0:
        out.append(("证据齐全度", "待补正", "请列出手头证据（订单号、支付凭证、聊天记录、商品照片、发票）。证据越全，调解成功率越高。"))
        return out
    if score >= 4:
        out.append(("证据齐全度", "通过", "核心证据较齐，足以支撑投诉与调解。"))
    elif score >= 2:
        out.append(("证据齐全度", "有风险", "证据部分齐全（已确认 %d 类），缺项尽快补：转账记录、聊天截图、商品照片最为关键。"
                    % score))
    else:
        out.append(("证据齐全度", "不通过", "证据严重不足（仅 %d 类）。**没有订单号和支付凭证，投诉很难被受理**。"
                    "尽快从支付平台导出流水、截图商品页面与聊天承诺。" % score))
    return out

def checks_jurisdiction(f):
    out = []
    loc = f.get("merchant_loc", "")
    tt = f.get("target_type", "")
    if unknown(loc) and unknown(tt):
        out.append(("管辖与主体", "待补正", "请填写商家所在地（省市）或平台名称，决定向哪个地区的 12315 投诉。"))
        return out
    # 异地提示
    if hit_any(loc, ["外地", "外省", "异地", "其他城市", "北京", "广州", "深圳", "杭州", "成都"]) or hit_any(tt, ["网店", "平台", "线上"]):
        out.append(("管辖与主体", "有风险", "**异地维权**：12315 投诉会自动分转至商家所在地（营业执照登记地）市场监管局，"
                    "你无需到场，但处理时效可能受跨地区影响。线上平台类可在平台所在地投诉。"))
    elif hit_any(tt, ["个人", "微商", "没有营业执照", "个体", "摊"]):
        out.append(("管辖与主体", "有风险", "对方若为无照个人/流动摊贩，市场监管调解手段有限，可尝试 12315 登记并同步向街道/城管反映。"))
    else:
        out.append(("管辖与主体", "通过", "主体明确，向商家所在地 12315 投诉即可，管辖无障碍。"))
    return out

def checks_time(f):
    out = []
    # 网购 7 天无理由（不依赖交易时间，独立判断）
    if hit_any(f.get("platform", ""), ["网购", "淘宝", "京东", "拼多多", "抖音", "直播间", "电商"]) and hit_any(f.get("issue", ""), ["不想要", "后悔", "不喜欢", "七天", "退"]):
        out.append(("七天无理由", "通过", "网购商品（除定制/生鲜/拆封音像等例外）支持**七天无理由退货**，商家不得拒绝。"))
    d = f.get("deal_date", "")
    if unknown(d):
        out.append(("时效核查", "待补正", "请填写交易时间（年月），判断是否超过投诉时效。"))
        return out
    # 粗略判断是否陈旧：含「年」且早于近 3 年 / 或明确「年前」
    yr = parse_num(re.search(r"(19|20)\d{2}", str(d)).group(0)) if re.search(r"(19|20)\d{2}", str(d)) else None
    this_year = datetime.date.today().year
    if yr is not None and this_year - yr >= 3:
        out.append(("时效核查", "有风险", "交易距今已超 3 年，部分诉求可能因超过合理期限被不予受理，但仍可尝试举报违法行为（无时效限制更宽松）。"))
    elif yr is not None and this_year - yr >= 1:
        out.append(("时效核查", "有风险", "交易已超过 1 年，建议尽快投诉，避免证据灭失与超期。"))
    else:
        out.append(("时效核查", "通过", "交易时间在近 1 年内，时效无忧，尽快提交即可。"))
    return out

def checks_negotiate(f):
    out = []
    neg = f.get("negotiated", "")
    res = f.get("neg_result", "")
    if unknown(neg):
        out.append(("先行协商", "待补正", "请说明是否已与商家协商、结果如何。"))
        return out
    if no(neg) or hit_any(neg, ["没", "未", "还没", "没有协商"]):
        out.append(("先行协商", "有风险", "尚未与商家协商。**建议先留痕协商一次**（文字写明诉求与依据），"
                    "协商记录本身就是证据，且部分平台要求先协商再投诉。"))
        return out
    if hit_any(res, ["拒绝", "拒", "不理", "拉黑", "拖延", "推", "一直拖"]):
        out.append(("先行协商", "不通过", "商家已明确拒绝/拖延，**直接进入 12315 投诉**，不必再耗在协商上。"))
        return out
    if hit_any(res, ["部分退", "退了一部分", "补", "换货", "同意"]):
        out.append(("先行协商", "有风险", "商家部分同意，可继续谈或据此投诉要求全部履行，保留协商截图。"))
        return out
    out.append(("先行协商", "有风险", "已协商但结果不明，建议明确记录对方回应并据此投诉。"))
    return out

def checks_claim(f):
    out = []
    exp = f.get("expectation", "")
    issue = f.get("issue", "")
    if unknown(exp):
        out.append(("诉求合理性", "待补正", "请填写你的期望诉求（退款/赔偿/换货/查处）。"))
        return out
    found = []
    for lbl, ws in CLAIM_TYPES:
        if hit_any(exp, ws) or hit_any(issue, ws):
            found.append(lbl)
    if "退一赔十/千元" in found or hit_any(issue + " " + exp, ["食品", "过期", "不符安全标准"]):
        out.append(("诉求合理性", "通过", "食品安全类可主张**退一赔十或最低 1000 元**（《食品安全法》148 条），诉求有法定依据。"))
    elif "退一赔三" in found or hit_any(issue + " " + exp, ["假", "欺诈", "虚假"]):
        out.append(("诉求合理性", "通过", "经营者有欺诈行为的，可主张**退一赔三、不足 500 按 500**（《消费者权益保护法》55 条）。"))
    elif "退款" in found or "换货维修" in found:
        out.append(("诉求合理性", "通过", "退款/换货属于法定基本诉求，12315 调解的核心范围。"))
    else:
        out.append(("诉求合理性", "有风险", "诉求表述可进一步法定化（如「退款+赔偿」比单纯「讨说法」更易被支持），建议明确具体金额或依据。"))
    return out

def checks_channel(f):
    out = []
    # 根据是否含严重情形选择推荐
    issue = f.get("issue", "")
    if unknown(issue):
        out.append(("渠道选择", "待补正", "请填写争议问题，以便判断走「投诉」还是「举报」入口。"))
        return out
    if hit_any(issue, ["虚假", "假冒", "无照", "价格违法", "宰客"]):
        out.append(("渠道选择", "通过", "涉嫌违法经营，优先走 12315「**举报**」入口（非投诉），由市场监管立案查处，比单纯调解更有力。"))
    else:
        out.append(("渠道选择", "通过", "一般消费纠纷走 12315「**投诉**」入口，由属地市场监管组织调解。"))
    return out

def checks_material(f):
    out = []
    ev = f.get("evidence", "")
    miss = []
    for lbl, ws in EVIDENCE_ITEMS:
        if unknown(ev) or not hit_any(ev, ws):
            miss.append(lbl)
    if not miss:
        out.append(("材料清单", "通过", "材料齐全，按清单整理成 PDF 一并上传即可。"))
    else:
        out.append(("材料清单", "有风险", "投诉前请备齐：①订单/合同号 ②支付凭证 ③聊天记录 ④商品照片/视频 ⑤发票收据。"
                    "当前可能缺：%s。" % "、".join(miss[:4])))
    return out

def checks_script(f):
    out = []
    exp = f.get("expectation", "")
    if unknown(exp):
        out.append(("投诉话术要点", "待补正", "明确诉求后，话术围绕「事实+法律依据+具体请求」三要素组织。"))
        return out
    out.append(("投诉话术要点", "通过", "投诉内容建议包含三要素：**①事实**（何时何地买了什么、出了什么问题）；"
                "**②依据**（对应法条或平台规则）；**③请求**（退款/赔偿的具体金额）。"
                "附上证据编号，避免情绪化描述，事实清楚更易被受理。"))
    return out

def checks_followup(f):
    out = []
    res = f.get("neg_result", "")
    if hit_any(res, ["投诉过", "已投诉", "市场监管局", "立案", "调解不成"]):
        out.append(("进度与升级", "有风险", "已进入监管程序，保存好受理编号，调解不成可在 7 个工作日后询问进展，"
                    "或就行政行为申请复议 / 向法院起诉。"))
    else:
        out.append(("进度与升级", "有风险", "提交投诉后通常 7 个工作日内受理、45 日内调解终结。超期无回应可电话催办，"
                    "调解不成不影响你另寻法律途径。"))
    return out

def evidence_gap(f):
    ev = f.get("evidence", "")
    miss = []
    for lbl, ws in EVIDENCE_ITEMS:
        if unknown(ev) or not hit_any(ev, ws):
            miss.append(lbl)
    # 字段直接确认的证据也算
    if yes(f.get("has_pay", "")):
        miss = [m for m in miss if m != "支付凭证"]
    if yes(f.get("has_chat", "")):
        miss = [m for m in miss if m != "聊天记录"]
    if filled(f.get("order_no", "")):
        miss = [m for m in miss if m != "订单/合同号"]
    if yes(f.get("has_photo", "")):
        miss = [m for m in miss if m != "商品照片/视频"]
    if yes(f.get("has_contract", "")):
        miss = [m for m in miss if m != "发票/收据"]
    return miss

def path_steps(f):
    return CHANNELS

def todo_list(f):
    todos = []
    scope_items = checks_scope(f)
    if any(s == "不通过" for _, s, _ in scope_items):
        todos.append("本事项不在 12315 受理范围，按报告指引改走正确渠道（如公安 110 / 劳动 12333 / 法院）")
        return todos
    todos.append("在全国 12315 平台（网站/APP/微信小程序）注册并提交投诉，填写商家准确名称与所在地")
    if len(evidence_gap(f)) >= 2:
        todos.append("补齐核心证据：订单号、支付凭证、聊天截图、商品照片")
    if hit_any(f.get("issue", ""), ["虚假", "假冒", "无照", "价格违法", "宰客"]):
        todos.append("同步走 12315「举报」入口，针对违法经营行为要求立案查处")
    if no(f.get("negotiated", "")) or unknown(f.get("negotiated", "")):
        todos.append("先向商家发一次书面协商（留存截图），作为投诉附件")
    todos.append("记下 12315 受理编号，7 个工作日后查询进度，调解不成准备向法院起诉")
    todos.append("把本报告与所有材料整理成一个文件夹备用")
    return todos

def render(f):
    L = []
    types = classify(f)
    scope_items = checks_scope(f)
    ev_items = checks_evidence(f)
    jur_items = checks_jurisdiction(f)
    time_items = checks_time(f)
    neg_items = checks_negotiate(f)
    claim_items = checks_claim(f)
    chan_items = checks_channel(f)
    mat_items = checks_material(f)
    scr_items = checks_script(f)
    fol_items = checks_followup(f)

    L.append("## 一、结论摘要")
    if any(s == "不通过" for _, s, _ in scope_items):
        L.append("**本事项不在 12315 受理范围**，请按报告指引改走正确渠道（如刑事诈骗走 110、劳资走 12333、医疗走卫健委）。")
    elif any(s == "不通过" for _, s, _ in ev_items):
        L.append("证据严重不足，**先补齐订单号与支付凭证再投诉**，否则很难被受理。完成补正后胜算较高。")
    else:
        L.append("属于 12315 受理范围，按本报告逐项补正证据后即可提交投诉，调解成功率较高。")
    if types:
        L.append("识别类型：" + "、".join(types))

    L.append("## 二、受理范围核查")
    for name, st, msg in scope_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 三、证据清单与缺口")
    for name, st, msg in ev_items:
        L.append("| %s | %s | %s |" % (name, st, msg))
    gap = evidence_gap(f)
    if gap:
        L.append("**证据缺口**：" + "、".join(gap) + "（尽快补齐）")
    else:
        L.append("**证据缺口**：暂无明显缺口。")

    L.append("## 四、管辖与主体核查")
    for name, st, msg in jur_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 五、时效核查")
    for name, st, msg in time_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 六、先行协商核查")
    for name, st, msg in neg_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 七、诉求合理性核查")
    for name, st, msg in claim_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 八、渠道选择建议")
    for name, st, msg in chan_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 九、材料清单与话术")
    for name, st, msg in mat_items:
        L.append("| %s | %s | %s |" % (name, st, msg))
    for name, st, msg in scr_items:
        L.append("| %s | %s | %s |" % (name, st, msg))

    L.append("## 十、维权渠道与路径")
    for i, p in enumerate(path_steps(f), 1):
        L.append("%d. %s" % (i, p))

    L.append("## 十一、待办补正动作")
    for t in todo_list(f):
        L.append("- %s" % t)

    L.append("## 十二、边界与纪律")
    L.append("本报告依《消费者权益保护法》《食品安全法》《市场监督管理投诉举报处理暂行办法》等通用规则整理，"
             "不替代专业法律意见，最终以市场监管部门或司法机关认定为准。金额与事实以你提供的凭证为准，未填项不按通过处理。")
    return "\n\n".join(L)

def to_json(f):
    types = classify(f)
    items = (checks_scope(f) + checks_evidence(f) + checks_jurisdiction(f) + checks_time(f)
             + checks_negotiate(f) + checks_claim(f) + checks_channel(f) + checks_material(f)
             + checks_script(f) + checks_followup(f))
    return {
        "结论": "不通过" if any(s == "不通过" for _, s, _ in items) else
                ("有风险" if any(s == "有风险" for _, s, _ in items) else "待补正"),
        "类型": types,
        "风险项": [{"项": n, "状态": s, "说明": m} for n, s, m in items],
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
