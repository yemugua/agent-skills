# -*- coding: utf-8 -*-
"""
wechat-debt-claim / extract.py

从微信聊天记录中扫描欠款追讨要件、金额、催告时间与诉讼时效。纯标准库，不联网、不上传。

用法：
    python extract.py --file 聊天记录.md
    python extract.py --file 聊天记录.md --scenario loan          # loan借贷 | goods货款 | project工程款
    python extract.py --file 聊天记录.md --focus 催告
    python extract.py --file 聊天记录.md --as-of 2026-09-01       # 时效基准日
    python extract.py --file 聊天记录.md --format json --out out.json

输入行格式（每行一条）：
    [2026-05-12 18:42] 张三: 那三万你下月还我
    [2026-05-20 15:40] 李四: 收到，下周五转你
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# 消息解析
# ---------------------------------------------------------------------------

LINE_RE = re.compile(
    r"^\s*-?\s*\[(?P<ts>\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)\]\s*"
    r"(?:(?P<who>[^\[\]:：]{1,40}?)\s*[:：]\s*)?"
    r"(?P<text>.*)$"
)

TS_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def parse_ts(raw):
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def parse_messages(path):
    """读取聊天记录，返回 (messages, meta)。"""
    if not os.path.exists(path):
        sys.exit("[错误] 文件不存在: %s" % path)

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw_lines = fh.read().splitlines()

    messages, unmatched = [], 0
    for line in raw_lines:
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            unmatched += 1
            continue
        dt = parse_ts(m.group("ts"))
        who = (m.group("who") or "").strip()
        text = (m.group("text") or "").strip()
        if not text:
            continue
        messages.append({"ts": dt, "ts_raw": m.group("ts"),
                         "who": who, "text": text})

    meta = {
        "file": os.path.basename(path),
        "total_lines": len(raw_lines),
        "parsed": len(messages),
        "unmatched": unmatched,
        "speakers": sorted({x["who"] for x in messages if x["who"]}),
    }
    return messages, meta


# ---------------------------------------------------------------------------
# 金额抽取
# ---------------------------------------------------------------------------

AMOUNT_RE = re.compile(
    r"(?<![\d.])(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
    r"\s*(万元|万|元|块|钱|人民币)?"
)

AMONEY_CTX = re.compile(
    r"[块元万钱币]|钱|欠|借款|还|还钱|还款|借|贷|利息|逾期|尾款|定金|押金|质保|保证金|"
    r"货款|货款|账|对账|结算|报销|垫付|罚款|违约金|赔偿|赔付|转账|打款|付款|支付|"
    r"账单|发票|金额|费用|成本|价格|总价|订金|余款|欠款|结清|抵扣|报销费"
)


# ---------------------------------------------------------------------------
# 中文数字金额（「八千」「两万二」在真人口语里比阿拉伯数字还常见）
# ---------------------------------------------------------------------------

CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9}

# 必须含「万/千/百/亿」这类量级字，否则「一下」「万一」会误伤
CN_AMOUNT_RE = re.compile(r"[零一二两三四五六七八九十百千万亿]{2,8}")

# 明确不是金额的固定说法
CN_BLACKLIST = {"万一", "万般", "百万分"}


def parse_cn_number(seg):
    """把「两万二」「八千」「三万四千」解析成整数。解析不了返回 None。"""
    if not seg or seg in CN_BLACKLIST:
        return None
    if not any(ch in seg for ch in "零一二两三四五六七八九"):
        return None
    total, cur, digit = 0, 0, 0
    for ch in seg:
        if ch in CN_DIGIT:
            digit = CN_DIGIT[ch]
        elif ch == "十":
            cur += (digit if digit else 1) * 10
            digit = 0
        elif ch == "百":
            cur += (digit if digit else 1) * 100
            digit = 0
        elif ch == "千":
            cur += (digit if digit else 1) * 1000
            digit = 0
        elif ch == "万":
            if total > 0 and digit:          # 「X万Y」→ Y 是千位零头（两万二 = 22000）
                total += digit * 1000
                digit = 0
            else:
                total += cur + digit
                cur, digit = 0, 0
        elif ch == "亿":
            if total > 0 and digit:
                total += digit * 100000000
                digit = 0
            else:
                total += cur + digit
                cur, digit = 0, 0
        else:
            return None
    val = total + cur + digit
    return val if val > 0 else None


def extract_amounts(messages):
    """抽取金额（阿拉伯数字 + 中文数字）。返回去重后的列表。"""
    results = []
    for msg in messages:
        text = msg["text"]

        # 中文数字金额（八千 / 两万二 / 三万四千 / 十万）——口语里比阿拉伯数字还常见
        for cm in CN_AMOUNT_RE.finditer(text):
            seg = cm.group(0)
            if seg in CN_BLACKLIST:
                continue
            val = parse_cn_number(seg)
            if val is None or val < 10 or val > 100000000:
                continue
            head = text[max(0, cm.start() - 14):cm.start()]
            after = text[cm.end():cm.end() + 8]
            if not (AMONEY_CTX.search(head + after) or "元" in after or "块" in after):
                continue
            ctx_start = max(0, cm.start() - 20)
            results.append({
                "amount": float(val),
                "raw": seg + "元",
                "context": text[ctx_start:cm.end() + 20].strip(),
                "ts_raw": msg["ts_raw"],
                "who": msg["who"],
                "snippet": text[:70],
            })

        for m in AMOUNT_RE.finditer(text):
            raw = m.group(1).replace(",", "")
            unit = m.group(2) or ""
            tail = text[m.end():m.end() + 2]
            head = text[max(0, m.start() - 16):m.start()]
            after = text[m.end():m.end() + 8]

            # 年份不算金额
            if not unit and tail.startswith("年"):
                continue
            # 纯数字且上下文无金额语义 → 跳过（编号、条数、温度等）
            if not unit and not AMONEY_CTX.search(head + after):
                continue
            # 百分号、岁数、天数等噪声
            if re.match(r"^\s*%|^\s*岁|^\s*天|^\s*年|^\s*月", tail):
                continue

            try:
                val = float(raw)
            except ValueError:
                continue
            if unit in ("万", "万元"):
                val *= 10000
            if val < 10 or val > 100000000:
                continue

            ctx_start = max(0, m.start() - 20)
            results.append({
                "amount": val,
                "raw": m.group(0).strip(),
                "context": text[ctx_start:m.end() + 20].strip(),
                "ts_raw": msg["ts_raw"],
                "who": msg["who"],
                "snippet": text[:70],
            })

    seen, uniq = set(), []
    for r in results:
        key = (r["amount"], r["context"][:24], r["ts_raw"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


# ---------------------------------------------------------------------------
# 要件库
# ---------------------------------------------------------------------------


def kw(*words):
    return list(words)


ELEMENTS = {
    "loan": {
        "label": "民间借贷",
        "items": [
            ("借贷合意", "出借人",
             kw("借给", "借了", "借你", "借款", "借钱", "欠条", "借条", "铲借", "临时借",
                "周转", "先借", "跟你借", "让我借")),
            ("款项交付", "出借人",
             kw("转了", "打给你", "转账", "已经付", "汇了", "打款", "到账", "收款", "收到钱")),
            ("约定还款日", "出借人",
             kw("下月", "下个月", "月底", "月底前", "X月还", "什么时候还", "还款日",
                "到期", "这周末", "过两天", "过几天", "这几天", "下周五", "下周一")),
            ("欠条借条", "出借人",
             kw("欠条", "借条", "打欠条", "写欠条", "补个条", "打张条", "立个字据")),
            ("利息约定", "出借人",
             kw("利息", "利率", "月息", "年息", "分息", "算利息", "息")),
            ("利率合规", "双方",
             kw("LPR", "lpr", "四倍", "4倍", "年化", "不得超过")),
            ("已还部分", "债务人",
             kw("还了", "还你一部分", "还了一部分", "先还", "上次还", "已付", "付了")),
            ("担保保证人", "出借人",
             kw("担保", "保证人", "担保人", "见证人", "推保", "找人担保", "抵押")),
            ("身份对应", "出借人",
             kw("我是", "我姓", "手机号", "身份证", "加我", "微信实名", ".realname")),
            ("催促还款", "出借人",
             kw("催", "什么时候", "再不", "尽快", "拖了", "一直没", "还没还", "逾期")),
        ],
    },
    "goods": {
        "label": "货款与服务费",
        "items": [
            ("合同订单", "债权人",
             kw("订单", "合同", "报价", "报价单", "约定", "说好", "谈好", "协议", "定金", "订金")),
            ("交付凭证", "债权人",
             kw("发货", "送货", "物流", "签收", "收货", "验收", "交了", "做完", "交付", "完工")),
            ("结算对账", "债权人",
             kw("对账", "结算", "结账", "算一下", "账算", "核账", "盘点", "总共有", "一共")),
            ("欠条结算单", "债权人",
             kw("欠条", "结算单", "对账单", "还差", "还欠", "剩", "余款", "尾款", "欠款")),
            ("发票", "债权人",
             kw("发票", "开票", "税点", "专票", "普票", "抬头")) ,
            ("质保金押金", "债权人",
             kw("质保", "保修金", "押金", "保证金", "订金", "尾款留", "留10%", "留百分之")),
            ("逾期利息", "债权人",
             kw("逾期", "违约金", "滞纳金", "罚息", "按日", "万分之", "利息")),
            ("催告记录", "债权人",
             kw("催", "什么时候付", "尽快", "拖", "还没给", "未付", "结清")),
        ],
    },
    "project": {
        "label": "工程款与结算",
        "items": [
            ("施工合同", "债权人",
             kw("合同", "分包", "单价", "平方米", "平米", "面积", "工程量", "包工", "包干")),
            ("工程量确认", "债权人",
             kw("验收", "签到", "签单", "施工日志", "进度", "完成了", "做到", "形象进度", "签证")),
            ("结算单", "债权人",
             kw("结算", "结算单", "决算", "审计", "审价", "核价", "工程量单")),
            ("进度款节点", "债权人",
             kw("进度款", "节点", "预付", "备料款", "付80", "付百分之", "阶段付款")),
            ("质保金", "债权人",
             kw("质保", "保修金", "保修期", "缺陷责任", "质保期", "留5%", "留%")),
            ("签证变更", "债权人",
             kw("签证", "变更单", "增项", "洽商", "追加", "补充协议")),
            ("停工解除", "双方",
             kw("停工", "停了", "解除", "终止", "撤场", "结清走人", "结算退场")),
            ("违约金利息", "债权人",
             kw("逾期付款", "违约金", "利息", "按日万分之", "滞纳")),
        ],
    },
}

# 对方拒付/推诿表述
REFUSAL_RE = re.compile(
    r"拒付|不付|不给了|没法付|付不了|暂时不能|缓一缓|再等等|等公司|走流程|走审批|"
    r"老板没批|领导没批|没预算|账上没钱|没钱|手头紧|先欠着|记着|算不清|没办|"
    r"这个不归我|不是我的账|你也有|你那边|货有问题|活不行|质量|延期交付|"
    r"已经还了|还过了|我还了|还清了|你再催|没看到|不认可|无法认定|材料不齐|证据不足|"
    r"只能给|就这么多|已经是最多|打个折|少一点|扣一点|抵了|抵掉"
)

# 程序里程碑
MILESTONE_PATTERNS = {
    "借款/交易达成": kw("借给", "借了", "借款", "借条", "欠条", "定金", "订金",
                        "订了", "下单", "约定", "说好", "合同", "订单"),
    "款项交付": kw("转了", "打给你", "转账", "打款", "汇了", "发货", "送货", "交了", "付款了"),
    "约定还款日": kw("下月", "下个月", "月底", "还款日", "到期", "下周五", "过几天"),
    "欠条/结算单": kw("欠条", "借条", "结算单", "对账单", "结算", "对账"),
    "催告": kw("催", "什么时候", "尽快", "加急", "再不", "拖", "一直没", "还没还", "还没给"),
    "对方承诺还款": kw("下月还", "下个月还", "下周五", "过两天转", "过几天还", "我认",
                       "认这笔", "同意还", "还你", "付你", "转你"),
    "部分还款": kw("还了一部分", "先还", "上次还", "还你5000", "还了20000", "先付"),
    "拒付推诿": kw("拒付", "不付", "不给了", "走流程", "等公司", "老板没批", "没钱",
                   "账上没钱", "手头紧", "再等等", "缓一缓", "先欠着"),
    "协商还款计划": kw("分期", "每月还", "分几次", "还款计划", "和解", "协议", "调解"),
    "法律行动": kw("起诉", "法院", "立案", "律师函", "支付令", "仲裁", "调解书",
                   "公示催告", "强制执行", "投诉", "12315"),
}

# 有效催告的关键要素（判断是否构成时效中断）
DEMAND_RE = re.compile(
    r"欠|借款|借|还|还款|尾款|欠款|货款|工程款|尾款|结清|还你|赔|付"
)


def scan_elements(messages, scenario):
    """返回 (hits, misses, snippets)。同一条消息只归属一个要件（used 去重）。"""
    scen = ELEMENTS.get(scenario)
    if not scen:
        return [], [], []
    hits, misses, snippets = [], [], []
    used = set()
    for name, burden, words in scen["items"]:
        matched = []
        for idx, msg in enumerate(messages):
            if idx in used:
                continue
            for w in words:
                if w in msg["text"]:
                    matched.append((idx, msg, w))
                    break
        if matched:
            for idx, msg, w in matched[:2]:
                used.add(idx)
                snippets.append((name, burden, msg, w))
            hits.append({
                "name": name, "burden": burden, "count": len(matched),
                "words": sorted({w for _, _, w in matched}),
            })
        else:
            misses.append({"name": name, "burden": burden, "words": words})
    return hits, misses, snippets


def scan_milestones(messages):
    return [(label, [m for m in messages if any(w in m["text"] for w in words)])
            for label, words in MILESTONE_PATTERNS.items()]


def detect_refusals(messages):
    return [m for m in messages if REFUSAL_RE.search(m["text"])]


# ---------------------------------------------------------------------------
# 时效计算
# ---------------------------------------------------------------------------


def add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return date(d.year + years, 2, 28)


TRIGGER_WORDS = {
    "loan": kw("借给", "借了", "借款", "欠条", "借条", "借钱", "还钱", "周转"),
    "goods": kw("发货", "送货", "签收", "收货", "验收", "订单", "下单", "交货", "交付"),
    "project": kw("验收", "结算", "结算单", "完工", "交付", "签单", "签证"),
}


def find_trigger_date(messages, scenario):
    """找债务成立/到期日。优先场景专属触发词，其次任何带日期的消息。"""
    words = TRIGGER_WORDS.get(scenario, [])
    for msg in messages:
        if msg["ts"] is None:
            continue
        if any(w in msg["text"] for w in words):
            return msg["ts"].date(), msg
    dated = [m for m in messages if m["ts"]]
    if dated:
        return dated[0]["ts"].date(), dated[0]
    return None, None


def compute_deadline(start, years, as_of):
    if start is None:
        return None, None
    end = add_years(start, years)
    return end, (end - as_of).days


# ---------------------------------------------------------------------------
# 催告质量评估（判断是否构成有效的时效中断）
# ---------------------------------------------------------------------------

DEMAND_FLAG = {
    "有金额": lambda t: bool(AMOUNT_RE.search(t)),
    "有事由": lambda t: bool(DEMAND_RE.search(t)),
    "有期限": lambda t: any(w in t for w in ("前", "之内", "日前", "天内", "本周",
                                             "今天", "这两天", "这两周", "尽快")),
    "有后果指向": lambda t: any(w in t for w in ("起诉", "法院", "立案", "律师",
                                                  "投诉", "执行", "法律", "程序")),
}


def assess_demands(messages):
    """评估含催告色彩的消息，判断是不是有效催告。"""
    out = []
    for msg in messages:
        t = msg["text"]
        if not any(kw_ in t for kw_ in ("催", "还", "欠", "付", "什么时候", "尽快", "拖")):
            continue
        flags = {name: fn(t) for name, fn in DEMAND_FLAG.items()}
        score = sum(1 for v in flags.values() if v)
        out.append({"msg": msg, "flags": flags, "score": score})
    out.sort(key=lambda x: -x["score"])
    return out


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "本报告由本地脚本对聊天记录做**要件与关键词扫描**生成，"
    "仅用于整理材料、发现缺口，不构成法律意见，不预测追讨结果。"
    "涉及金额较大、对方拒认或临近时效的案件，请咨询执业律师。"
)


def fmt(n):
    return "{:,.2f}".format(n) if isinstance(n, float) else "{:,}".format(n)


def _where_to_get(name):
    table = {
        "借贷合意": "聊天原文 / 借条；让对方在微信里说清「借」字",
        "款项交付": "微信账单导出（带电子章 PDF）/ 银行流水",
        "约定还款日": "聊天原文；没约定就从催告届满起算",
        "欠条借条": "让对方补打欠条，或微信里书面确认金额",
        "利息约定": "聊天记录 / 书面协议",
        "利率合规": "起诉时按一年期 LPR 四倍口径核，超额部分不受保护",
        "已还部分": "对方转账记录，从本金里扣",
        "担保保证人": "担保人身份信息 + 书面担保意思",
        "身份对应": "微信实名手机号 / 身份证 / 共同熟人确认",
        "催促还款": "每次催告都截屏 + 导出，作为时效中断证据",
        "合同订单": "微信确认的价格、规格、数量也算",
        "交付凭证": "物流单 / 签收单 / 验收单 / 服务完成记录",
        "结算对账": "微信对账截图 + 双方确认",
        "欠条结算单": "让对方对账后确认「还欠 X 元」",
        "发票": "税控开票系统开具并送达",
        "质保金押金": "合同质保条款 + 结算单",
        "逾期利息": "合同违约条款；没约定按 LPR 主张",
        "催告记录": "微信文字催告，写明金额+事由+期限",
        "施工合同": "施工/分包协议，单价与工程量",
        "工程量确认": "施工日志 / 验收单 / 甲方或总包签字",
        "结算单": "结算书 / 审价报告 / 双方签认",
        "进度款节点": "合同付款节点条款 + 进度确认",
        "质保金": "质保条款 + 缺陷责任期起算证明",
        "签证变更": "签证单 / 变更洽商单 / 补充协议",
        "停工解除": "停工通知 / 解约函 / 撤场记录",
        "违约金利息": "合同违约条款 + 逾期天数",
    }
    return table.get(name, "按合同与聊天记录整理")


def _next_actions(res):
    acts = []
    if res["deadline_info"][1] is not None and res["deadline_info"][1] < 0:
        acts.append("**时效已过，立刻取征**：先补一次书面催告并保留记录（仍有补救空间，但对方抗辩风险高）")
    elif res["deadline_info"][1] is not None and res["deadline_info"][1] < 90:
        acts.append("**时效仅剩 %d 天，优先催告**：发一条写明「金额 + 事由 + 期限」的微信，构成时效中断"
                    % res["deadline_info"][1])
    else:
        acts.append("每 6–12 个月发一次书面催告，维持时效中断（《民法典》第 195 条）")

    weak = [d for d in res["demands"] if d["score"] <= 2]
    if weak:
        acts.append("有 %d 条催告表述偏弱（缺金额/事由/期限），补一条写清「还欠 ____ 元，____ 日前付清」的微信"
                    % len(weak))

    miss_names = {m["name"] for m in res["misses"]}
    for key, msg in (
        ("借贷合意", "先把「借 / 欠」这件事钉死：让对方回一句承认金额的话。只有转账记录，定性会被推翻"),
        ("欠条借条", "补一张欠条或结算单，比聊天记录硬得多"),
        ("款项交付", "去微信账单导出带电子章的 PDF，法院认这个形式"),
        ("身份对应", "立案要真实姓名，先把微信昵称对应到本人"),
        ("结算对账", "主动约一次对账，让他确认「还欠 X 元」"),
        ("约定还款日", "没写还款日就现在催告一次，从催告届满起算时效"),
    ):
        if key in miss_names:
            acts.append(msg)
            break

    if res["refusals"]:
        acts.append("把对方每条拒付/推诿原话列出来逐条回怼，重点打「举证责任在他」这一点"
                    "——他说还了，就得他拿转账记录")
    acts.append("债权清晰、对方只是拖（认账不付）的，优先考虑**申请支付令**，比起诉快且便宜")
    acts.append("催告只用「在吗」没用，要有金额 + 事由 + 期限，且留好对方回话")
    acts.append("导出完整连续记录（含对你不利的部分），别只截片段——"
                "对方最容易攻击「剪辑」，主动提交完整记录反而更有力")
    acts.append("材料三处备份：本机 + 云盘 + 原件；重要节点做录屏，比截图有说服力")
    return acts


def render_markdown(res):
    out = []
    w = out.append
    scen_label = ELEMENTS.get(res["scenario"], {}).get("label", res["scenario"])
    as_of = res["as_of"]

    w("# 微信催款要件扫描报告")
    w("")
    w("> 场景：**%s**　扫描日期：%s　文件：`%s`"
      % (scen_label, as_of, res["meta"]["file"]))
    w("")

    focus_mode = bool(res["meta"].get("focused"))
    if focus_mode:
        w("> ⚠️ 过滤模式：按「**%s**」（%s匹配）筛出 %d 条，要件覆盖率会偏低，属预期。"
          "完整分析请去掉 `--focus`。"
          % (res["meta"]["focused"], res["meta"].get("focus_kind", "字面"),
             res["meta"].get("matched_focus", 0)))
        w("")

    hits, misses = res["hits"], res["misses"]
    total = len(hits) + len(misses)
    cover = (len(hits) * 100.0 / total) if total else 0

    w("## 一、结论先行")
    w("")
    w("- 要件覆盖：**%d / %d（%.0f%%）**" % (len(hits), total, cover))

    expires, days_left = res["deadline_info"]
    if expires:
        if days_left is None:
            w("- 诉讼时效：**无法计算**（记录里没有可识别的借款/交付日期）")
        elif days_left < 0:
            w("- 诉讼时效：**⚠️ 已过期 %d 天**（起算 %s，3 年届满 %s）"
              % (-days_left, res["trigger_date"], expires))
        elif days_left < 90:
            w("- 诉讼时效：**⚠️ 仅剩 %d 天**（起算 %s，届满 %s）"
              % (days_left, res["trigger_date"], expires))
        else:
            w("- 诉讼时效：剩余 **%d 天**（起算 %s，届满 %s）"
              % (days_left, res["trigger_date"], expires))
    else:
        w("- 诉讼时效：**无法计算**，请先补充借款/交付日期")

    weak_demands = [d for d in res["demands"] if d["score"] <= 2]
    strong_demands = [d for d in res["demands"] if d["score"] >= 3]
    if strong_demands:
        w("- 有效催告：**%d 条**（含金额 + 事由 + 期限中的多项），可支撑时效中断" % len(strong_demands))
    if weak_demands:
        w("- ⚠️ **偏弱的催告 %d 条**——没写清金额/事由/期限，法律上难以认定" % len(weak_demands))
    if res["refusals"]:
        w("- 对方**拒付/推诿表述 %d 条**，这是本案争议焦点" % len(res["refusals"]))
    if res["amounts"]:
        w("- 抽取到 **%d 处金额**，最大 %s 元"
          % (len(res["amounts"]), fmt(max(a["amount"] for a in res["amounts"]))))
    if res["milestones"]:
        w("- 识别到 **%d 类程序节点**：%s"
          % (len(res["milestones"]), "、".join(m[0] for m in res["milestones"])))
    w("")

    if days_left is not None and days_left < 0:
        w("> **现在的第一优先级不是材料够不够，而是时效。**先补一次书面催告留痕，"
          "再回头整理债权凭证。")
        w("")

    w("## 二、要件命中表")
    w("")
    w("| 要件 | 举证方 | 命中 | 命中关键词 |")
    w("|---|---|---|---|")
    for h in hits:
        w("| %s | %s | ✅ %d 处 | %s |"
          % (h["name"], h["burden"], h["count"], "、".join(h["words"][:4])))
    for m in misses:
        w("| %s | %s | ❌ | — |" % (m["name"], m["burden"]))
    w("")

    if misses:
        w("## 三、缺失要件与补强方向")
        w("")
        w("聊天里没有 ≠ 没有材料，很可能躺在纸质单据、转账记录或对方手里。")
        w("")
        w("| 缺失要件 | 举证方 | 去哪里补 |")
        w("|---|---|---|")
        for m in misses:
            w("| %s | %s | %s |" % (m["name"], m["burden"], _where_to_get(m["name"])))
        w("")

    if focus_mode or res["refusals"]:
        w("## 四、争议焦点（拒付与推诿表述）")
        w("")
        if not res["refusals"]:
            w("本次过滤范围内没有提取到拒付/推诿表述。要看全貌请去掉 `--focus` 重跑。")
            w("")
        for i, msg in enumerate(res["refusals"][:12], 1):
            w("%d. **%s**%s" % (i, f"[{msg['ts_raw']}] " if msg["ts_raw"] else "",
                                f"{msg['who']}：" if msg["who"] else ""))
            w("   > %s" % msg["text"][:120])
        w("")
        w("> **破局参照**：")
        w("> - 《民法典》第 195 条：权利人**提出履行请求**即导致时效中断，重新计算 3 年。")
        w("> - 举证责任分配：对方主张「钱已还」，**由他举证**，要他出示转账/收条。")
        w("> - 《民法典》第 667、679 条：借贷关系需「借贷合意 + 款项交付」两项，光有转账不够。")
        w("> - 《民事诉讼法》督促程序：债权清晰、对方认账只是拖的，可考虑**申请支付令**，比起诉快。")
        w("")

    if focus_mode or res["demands"]:
        w("## 五、催告质量评估（关系时效能否中断）")
        w("")
        w("> 一条催告要构成「有效主张」，至少要写明**欠了多少 + 什么事由 + 什么时候前给**。")
        w(">「在吗」「钱呢」这类不算。")
        w("")
        w("| 时间 | 谁 | 金额 | 事由 | 期限 | 后果指向 | 得分 | 原话 |")
        w("|---|---|---|---|---|---|---|---|")
        for d in res["demands"][:12]:
            m = d["msg"]
            f = d["flags"]
            flag = lambda k: "✅" if f[k] else "—"
            w("| %s | %s | %s | %s | %s | %s | %d/4 | %s |"
              % (m["ts_raw"], m["who"] or "—", flag("有金额"), flag("有事由"),
                 flag("有期限"), flag("有后果指向"), d["score"],
                 m["text"][:36].replace("|", "/")))
        w("")
        w("> 得分 **≥3** 的才算有效催告；**≤2** 的补一条新的。")
        w("")

    if focus_mode or res["milestones"]:
        w("## 六、关键程序节点")
        w("")
        for label, msgs in res["milestones"]:
            if not msgs:
                continue
            w("**%s**（%d 条）" % (label, len(msgs)))
            for msg in sorted(msgs, key=lambda x: x["ts_raw"])[:4]:
                w("- `[%s]`%s %s"
                  % (msg["ts_raw"], ("**%s：**" % msg["who"]) if msg["who"] else "",
                     msg["text"][:90]))
            w("")

    if focus_mode or res["amounts"]:
        w("## 七、金额梳理")
        w("")
        if not res["amounts"]:
            w("本次过滤范围内没有抽到金额。金额识别依赖「元/块/万」等后缀或"
              "「欠/借款/尾款/还款」等上下文词，请把金额写成「30000元」这种带单位的写法，"
              "或用 `--focus 金额` 全量重跑。")
            w("")
        if res["amounts"]:
            w("| 时间 | 金额 | 上下文 | 出处 |")
            w("|---|---|---|---|")
            for a in sorted(res["amounts"], key=lambda x: -x["amount"])[:25]:
                w("| %s | **%s** | %s | %s |"
                  % (a["ts_raw"], fmt(a["amount"]), a["context"][:40], a["who"] or "—"))
            w("")
            w("> 最大金额 **%s 元**。请与转账记录、结算单**逐笔交叉核对**，"
              "注意把对方已经还的部分扣掉。" % fmt(max(a["amount"] for a in res["amounts"])))
            w("")
        w("> ⚠️ **先扣已还、再算利息**：催款最常见的错是把旧账一起算，或者忘了扣他已经还的部分。")
        w("")

    if res["snippets"]:
        w("## 八、关键证据片段")
        w("")
        w("> 导出完整对话时**不要只截取有利片段**。对方最常见的抗辩是\"断章取义\"和\"被剪辑\"，"
          "主动提交完整记录反而更有力。")
        w("")
        for name, burden, msg, word in res["snippets"][:15]:
            w("- **[%s] %s**（%s · 命中「%s」）" % (msg["ts_raw"], name, burden, word))
            w("  > %s" % msg["text"][:110])
        w("")

    w("## 九、下一步行动清单")
    w("")
    for i, act in enumerate(_next_actions(res), 1):
        w("%d. %s" % (i, act))
    w("")
    w("---")
    w("")
    w("**免责声明**：%s" % DISCLAIMER)
    w("")
    w("本报告由 `extract.py` v%s 生成。重新扫描：" % VERSION)
    w("```bash")
    w("python %s --file %s --scenario %s"
      % (os.path.basename(__file__), res["meta"]["file"], res["scenario"]))
    w("```")
    return "\n".join(out)


def render_json(res):
    return json.dumps({
        "scenario": res["scenario"],
        "scenarioLabel": ELEMENTS.get(res["scenario"], {}).get("label", res["scenario"]),
        "asOf": res["as_of"].isoformat(),
        "meta": res["meta"],
        "coverage": {
            "hit": len(res["hits"]),
            "miss": len(res["misses"]),
            "percent": round(len(res["hits"]) * 100.0 /
                             max(1, len(res["hits"]) + len(res["misses"])), 1),
        },
        "deadline": {
            "limitYears": 3,
            "triggerDate": res["trigger_date"].isoformat() if res["trigger_date"] else None,
            "expireDate": res["deadline_info"][0].isoformat() if res["deadline_info"][0] else None,
            "daysLeft": res["deadline_info"][1],
        },
        "hits": res["hits"],
        "misses": res["misses"],
        "amounts": res["amounts"],
        "milestones": [
            {"name": label, "count": len(msgs),
             "messages": [{"ts": m["ts_raw"], "who": m["who"], "text": m["text"]}
                          for m in msgs]}
            for label, msgs in res["milestones"]
        ],
        "refusals": [
            {"ts": m["ts_raw"], "who": m["who"], "text": m["text"]}
            for m in res["refusals"]
        ],
        "demands": [
            {"ts": d["msg"]["ts_raw"], "who": d["msg"]["who"], "text": d["msg"]["text"],
             "flags": d["flags"], "score": d["score"]}
            for d in res["demands"]
        ],
        "disclaimer": DISCLAIMER,
    }, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

FOCUS_ALIAS = {
    "催告": ["催", "什么时候", "尽快", "再不", "拖", "还没还", "还没给", "结清",
             "逾期", "付清", "法律", "起诉", "法院", "立案"],
    "金额": ["元", "块", "钱", "欠", "还", "借款", "尾款", "尾", "利息", "转账",
             "打款", "付款", "金额", "发票", "账"],
    "拒付": ["拒付", "不付", "不给了", "走流程", "等公司", "老板没批", "没钱",
             "账上没钱", "手头紧", "再等等", "缓一缓", "先欠着", "算不清",
             "已经还了", "我还了", "不认可", "只能给", "抵了"],
    "承诺": ["下月还", "下个月还", "下周五", "过两天转", "过几天还", "我认",
             "还你", "转你", "付你", "同意还", "分期", "还款计划"],
    "时效": ["起诉", "法院", "立案", "律师", "支付令", "仲裁", "时效", "过期",
             "强制执行", "投诉"],
}


def match_focus(text, focus):
    words = FOCUS_ALIAS.get(focus)
    if words:
        return any(w in text for w in words)
    return focus in text


def main():
    ap = argparse.ArgumentParser(
        description="从微信聊天记录中扫描欠款追讨要件、金额与诉讼时效（本地运行）")
    ap.add_argument("--file", required=True, help="聊天记录文件（.md / .txt）")
    ap.add_argument("--scenario", default="all",
                    help="loan借贷 | goods货款服务费 | project工程款 | all全部（默认）")
    ap.add_argument("--as-of", dest="as_of", default=None,
                    help="时效基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--focus", default=None,
                    help="只看含该关键词/类别的消息。类别：催告、金额、拒付、承诺、时效；"
                         "也可传任意字面词")
    ap.add_argument("--out", default=None, help="输出文件路径；不填打印到 stdout")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    args = ap.parse_args()

    if args.as_of:
        try:
            as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
        except ValueError:
            sys.exit("[错误] --as-of 格式应为 YYYY-MM-DD")
    else:
        as_of = date.today()

    if args.scenario not in list(ELEMENTS.keys()) + ["all"]:
        sys.exit("[错误] --scenario 取值：loan | goods | project | all")

    messages, meta = parse_messages(args.file)

    if args.focus:
        messages = [m for m in messages if match_focus(m["text"], args.focus)]
        meta["focused"] = args.focus
        meta["matched_focus"] = len(messages)
        meta["focus_kind"] = "类别" if args.focus in FOCUS_ALIAS else "字面"
        if not messages:
            hit_words = FOCUS_ALIAS.get(args.focus)
            hint = ("（该类别下可匹配的说法：%s）"
                    % "、".join(hit_words[:6])) if hit_words else ""
            sys.exit("[提示] 没有消息命中「%s」%s\n"
                     "过滤后没有可分析内容，请去掉 --focus 重新扫描。"
                     % (args.focus, hint))

    if not messages and not args.focus:
        sys.exit("[警告] 未解析出任何消息。\n"
                 "请确认文件格式为每行 `[YYYY-MM-DD HH:MM] 发送者: 内容`。\n"
                 "可先用技能 wechat-local-reader-tianbao 导出聊天记录。")

    scenario = args.scenario if args.scenario != "all" else "all"

    if scenario == "all":
        hits, misses, snippets = [], [], []
        for sc in ("loan", "goods", "project"):
            h, m, s = scan_elements(messages, sc)
            for x in h + m:
                x["scenario"] = ELEMENTS[sc]["label"]
            hits += h
            misses += m
            snippets += s
    else:
        hits, misses, snippets = scan_elements(messages, scenario)

    amounts = extract_amounts(messages)
    milestones = scan_milestones(messages)
    refusals = detect_refusals(messages)
    demands = assess_demands(messages)

    trigger_date, _ = find_trigger_date(messages, scenario)
    expires, days_left = compute_deadline(trigger_date, 3, as_of)

    res = {
        "scenario": scenario,
        "as_of": as_of,
        "meta": meta,
        "hits": hits,
        "misses": misses,
        "snippets": snippets,
        "amounts": amounts,
        "milestones": milestones,
        "refusals": refusals,
        "demands": demands,
        "trigger_date": trigger_date,
        "deadline_info": (expires, days_left),
        "limit_years": 3,
    }

    text = render_json(res) if args.format == "json" else render_markdown(res)
    if args.out:
        d = os.path.dirname(args.out)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        sys.stderr.write("已写入 %s\n" % args.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
