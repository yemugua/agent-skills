#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信证据链扫描器
================
把 wechat-cli export 出来的聊天记录，按场景要件归类，抽取金额与关键日期，
计算时效倒计时，输出证据清单 / 时间线 / 缺项报告。

只做关键词匹配与机械计算，**不做法律判断**。命中不等于有效证据。

用法
----
    python extract.py --file 导出.md --scenario labor
    python extract.py --file 导出.txt --scenario rent --as-of 2026-10-04 --out 报告.md
    python extract.py --file 导出.md --scenario all --format json

依赖：仅标准库（Python >= 3.8）
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime

# ---------------------------------------------------------------------------
# 场景要件库
#   每项: key, 名称, 关键词(任一命中), 缺失后果
# ---------------------------------------------------------------------------

SCENARIOS = {
    "labor": {
        "label": "劳动争议",
        "elements": [
            ("rel", "劳动关系存在",
             ["入职", "报到", "offer", "OFFER", "劳动合同", "试用期", "转正", "离职",
              "辞职", "离职证明", "人事", "HR", "hr", "招聘", "录用", "入职表", "工牌"],
             "无劳动关系主张的请求权基础，可能被驳回"),
            ("duty", "劳动内容与岗位",
             ["岗位", "职责", "工作内容", "工作群", "任务", "派活", "安排", "对接",
              "项目组", "部门"],
             "岗位难认定，影响加班与岗位变动认定"),
            ("wage", "工资标准",
             ["工资", "薪水", "月薪", "薪资", "薪酬", "绩效", "奖金", "提成", "底薪",
              "万/月", "元/月", "k薪"],
             "只能按最低工资主张，差额拿不到"),
            ("pay", "实际发放记录",
             ["发工资", "转账", "收款", "已付", "到账", "打款", "尾款", "补发"],
             "无法证明欠付的具体金额与期数"),
            ("owe", "欠付事实与自认",
             ["欠", "没发", "拖欠", "补上", "补发", "下个月发", "晚点发", "尽快",
              "账", "对一下", "结算"],
             "对方否认欠付则难以支撑"),
            ("ot", "工作时间构成",
             ["加班", "值班", "通宵", "熬夜", "周末", "法定节假日", "排班", "打卡",
              "考勤", "出差", "驻场", "上线", "值班表"],
             "加班费请求通常被驳回"),
            ("term", "解除或终止事实",
             ["辞退", "开除", "解除", "裁员", "优化", "不用来了", "别来了", "离职通知",
              "交接", "辞掉", "劝退", "换工作", "调岗", "降薪"],
             "违法解除的赔偿金无从主张"),
            ("insure", "社保公积金",
             ["社保", "公积金", "五险", "一金", "缴纳", "医保", "养老保险", "补缴"],
             "社保部分请求可能无法通过仲裁处理"),
            ("contract", "书面劳动合同签订情况",
             ["签合同", "签劳动合同", "签了合同", "签了劳动合同", "合同签了", "签字",
              "盖章", "合同到期", "续签", "没签", "没签合同", "什么时候签", "补签",
              "劳动合同", "合同后面补", "先干着"],
             "命中「没签/待签/补签」→ 未签书面劳动合同，可主张二倍工资；"
             "命中「签了/签字/盖章」→ 已签，无二倍工资空间"),
        ],
        "keywords_anchor": {
            "入职": "入职", "入职日期": "入职", "报到": "报到", "offer": "录用通知",
            "离职": "离职", "辞职": "辞职", "辞退": "辞退", "开除": "开除",
            "解除劳动合同": "解除", "不用来了": "解除通知", "调岗": "调岗", "降薪": "降薪",
            "最后一天": "离职", "月底走": "离职", "做到": "离职",
        },
        "time_limit_years": 1,
        "time_limit_note": "劳动争议仲裁时效 1 年（劳动关系存续期间拖欠劳动报酬不受此限）",
    },

    "rent": {
        "label": "租房押金",
        "elements": [
            ("rel", "租赁关系存在",
             ["租房", "房租", "押金", "月租", "年租", "中介", "房东", "房子", "合租",
              "整租", "押一付", "退租", "续租", "转租"],
             "无租赁关系主张基础"),
            ("amount", "押金约定与退还条件",
             ["押一付", "押金退", "退还押金", "退押金", "押金什么时候", "押金条件",
              "压一付", "定金", "退房"],
             "金额与条件不明，无法主张返还"),
            ("paid", "押金实际交付",
             ["押金", "转给你", "已收", "收到", "到账", "打给你"],
             "只凭口头约定很难支持"),
            ("checkout", "退租事实与时间",
             ["退租", "搬走", "搬出去了", "交房", "钥匙", "退房", "搬空了", "腾房",
              "最后一天", "到期了"],
             "押金退还义务的起算点不明"),
            ("owe", "押金未退还",
             ["还没退", "什么时候退", "退一下", "退给我", "拖着", "过几天", "尽快退",
              "一直没退", "催"],
             "对方否认未退则难以支撑"),
            ("deduct", "扣除理由是否成立",
             ["扣押金", "押金扣", "扣除", "扣了", "清洁费", "损耗", "家具坏", "墙脏",
              "地板", "家电", "维修费", "复原"],
             "若无合理理由扣除，属不当得利或违约"),
            ("condition", "房屋状况与损坏",
             ["漏水", "渗水", "发霉", "损坏", "破损", "裂", "碎", "掉漆", "划痕",
              "沙发", "床", "衣柜", "热水器", "空调"],
             "自然损耗与人为损坏难区分"),
            ("utility", "水电燃气物业",
             ["水电", "燃气", "物业", "宽带", "暖气", "垃圾费"],
             "属实可扣，但需单据佐证"),
        ],
        "keywords_anchor": {
            "押金": "押金", "退押金": "退押金", "退房": "退租", "搬走": "搬走",
            "交房": "交房", "钥匙": "交钥匙", "房东": "房东", "中介": "中介",
        },
        "time_limit_years": 3,
        "time_limit_note": "一般民事诉讼时效 3 年（自知道或应当知道权利受损之日起）",
    },

    "loan": {
        "label": "民间借贷",
        "elements": [
            ("consensus", "借贷合意",
             ["借我", "借你", "借款", "借条", "欠条", "欠我", "欠你", "还款", "还钱",
              "还你", "还他", "本金", "借点", "周转", "急用", "周转一下"],
             "合意不明则无法认定借贷关系"),
            ("deliver", "款项实际交付",
             ["转账", "微信转账", "收款", "到账", "已收", "打给你", "转给你", "红包",
              "支付宝", "汇款"],
             "无交付证据 = 借贷关系不成立（最常见败因）"),
            ("amount", "金额与币种",
             ["块", "元", "万", "千", "整", "多", "少"],
             "主张金额与转账金额不符会被质疑"),
            ("repay", "还款事实",
             ["还了", "还你", "还了", "已还", "还款", "转给你", "收到"],
             "部分还款可证明借贷关系真实存在"),
            ("interest", "利息约定",
             ["利息", "利率", "息", "几分", "厘", "月息", "年息", "利钱"],
             "无约定则视为无息"),
            ("demand", "催收记录与回应",
             ["催", "催款", "还钱", "什么时候还", "尽快还", "欠着", "拖", "什么时候",
              "宽限", "什么时候能"],
             "无催收记录则时效可能被抗辩"),
            ("guarantee", "担保人责任",
             ["担保", "担保人", "我替他", "我保证", "还不上我", "我负责还", "连带责任"],
             "无担保意思表示则担保不成立"),
        ],
        "keywords_anchor": {
            "借": "借", "还款": "还款", "还你": "还款", "欠": "欠款确认",
            "催": "催收", "利息": "利息", "担保": "担保",
        },
        "time_limit_years": 3,
        "time_limit_note": "一般民事诉讼时效 3 年；每次有效催收可中断重新起算",
    },

    "contract": {
        "label": "合同 / 买卖 / 服务",
        "elements": [
            ("form", "合同成立",
             ["合同", "协议", "签", "签字", "盖章", "订单", "下单", "报价", "比价",
              "确认", "就这么定", "按这个", "成交", "中标", "定做"],
             "合同未成立则无履行请求权"),
            ("term", "合同内容明确",
             ["价款", "总价", "工期", "规格", "型号", "验收", "标准", "付款方式",
              "节点", "违约金", "交期"],
             "约定不明则难以认定违约"),
            ("perform", "己方已履行",
             ["交付", "发货", "收货", "验收", "安装", "完工", "进场", "施工", "提交",
              "报了", "做完了", "已送", "签收"],
             "未证明自己先履约会被驳回"),
            ("breach", "对方未履行",
             ["没做", "没交", "延期", "拖", "没回复", "拒绝", "不确认", "没来",
              "没处理", "黄了"],
             "对方履行情况不明则无法主张违约"),
            ("loss", "损失已发生",
             ["损失", "赔", "赔偿", "返工", "停工", "延误", "亏", "损失了"],
             "主张违约金但无损失证据，支持率低"),
            ("notice", "催告与合理期限",
             ["请于", "限", "之前", "期限", "否则", "最后通牒", "给个时间",
              "什么时候完成", "催一下"],
             "未给合理期限即主张解除，可能不获支持"),
            ("settle", "结算与付款",
             ["结款", "结算", "尾款", "质保", "保修", "对账", "付款", "打款", "发票",
              "已付", "付清"],
             "无法确定欠付具体数额"),
        ],
        "keywords_anchor": {
            "合同": "合同", "签": "签约", "报价": "报价", "验收": "验收",
            "交付": "交付", "结算": "结算", "违约": "违约",
        },
        "time_limit_years": 3,
        "time_limit_note": "一般民事诉讼时效 3 年",
    },

    "tort": {
        "label": "侵权",
        "elements": [
            ("harm", "权益受损",
             ["受伤", "住院", "骨折", "诊断", "撞", "打", "摔", "泼", "毁", "损坏",
              "偷", "盗", "划", "碰坏", "挂了"],
             "无损害事实则无侵权成立基础"),
            ("act", "行为违法性",
             ["动手", "推", "踢", "撞了", "砸", "辱骂", "威胁", "泼了", "开车门",
              "甩"],
             "无法归责"),
            ("cause", "因果关系（最难）",
             ["因为", "导致", "造成", "所以", "要不是", "由于", "结果", "因此",
              "害得", "害我"],
             "最难证的一环，缺此项常被驳回"),
            ("fault", "责任自认",
             ["是我", "我的错", "我撞", "我弄", "我赔", "算我的", "我负责", "我承认",
              "对不起", "我错了"],
             "无法确定责任主体"),
            ("amount", "损害数额",
             ["医药费", "治疗", "检查", "拍片", "维修", "报价", "误工", "护理",
              "营养", "赔偿金", "补偿"],
             "数额无据则难以支持"),
            ("report", "报警与第三方记录",
             ["110", "122", "报警", "派出所", "出警", "警车", "保险", "交警", "物业调监控"],
             "缺少独立第三方印证"),
        ],
        "keywords_anchor": {
            "撞": "事故", "受伤": "受伤", "报警": "报警", "110": "报警",
            "赔": "赔偿", "是我": "责任自认",
        },
        "time_limit_years": 3,
        "time_limit_note": "人身损害 3 年（自知道或应当知道之日起）",
    },

    "family": {
        "label": "婚姻家事",
        "elements": [
            ("marry", "婚姻关系",
             ["结婚", "婚礼", "领证", "登记", "离婚", "夫妻", "老公", "老婆", "孩子",
              "女儿", "儿子", "家里"],
             "基础事实不清则无法主张"),
            ("property", "夫妻共同财产",
             ["房子", "房", "存款", "工资卡", "车", "股权", "理财", "基金", "共同财产",
              "婚前", "嫁妆", "彩礼", "首付", "装修"],
             "财产范围不明则难以分割"),
            ("separate", "分居或感情破裂",
             ["分居", "分开", "两地", "不在一起", "回娘家", "过年没回", "异地",
              "搬出去", "各过各的"],
             "调解与诉讼离婚的重要考量"),
            ("child", "子女抚养",
             ["抚养", "探视", "看孩子", "接孩子", "奶粉", "上学", "补习", "幼儿园",
              "学费", "生活费"],
             "抚养权与抚养费主张缺依据"),
            ("fault", "一方过错",
             ["出轨", "第三者", "小三", "家暴", "打", "赌", "家暴证据", "外面有人"],
             "过错方可能少分财产"),
            ("support", "抚养费支付",
             ["抚养费", "生活费", "学费", "给钱", "转了", "每月"],
             "支付记录缺失则无法主张欠付"),
        ],
        "keywords_anchor": {
            "离婚": "离婚", "分居": "分居", "彩礼": "彩礼", "孩子": "子女",
            "抚养费": "抚养费", "出轨": "过错",
        },
        "time_limit_years": None,
        "time_limit_note": "离婚诉讼无固定诉讼时效；其他依具体请求权确定",
    },
}

# ---------------------------------------------------------------------------
# 消息解析
# ---------------------------------------------------------------------------

# 兼容 wechat-cli export 的 markdown / txt 输出：
#   - [2026-09-01 10:23] 张三: 内容
#   - [2026-09-01 10:23] 内容
# 也兼容全角冒号、二级 - 前缀、秒级时间
LINE_RE = re.compile(
    r"^\s*-?\s*\[(?P<ts>\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)\]\s*"
    r"(?:(?P<who>[^\[\]:：]{1,40}?)\s*[:：]\s*)?"
    r"(?P<text>.*)$"
)

# 金额：8000 / 3万 / 1.5 万元 / 5000块
AMOUNT_RE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(万元|万|元|块|千元|千|亿)?"
)
AMOUNT_UNITS = {
    "万": 10000, "万元": 10000, "千": 1000, "千元": 1000,
    "亿": 100000000, "元": 1, "块": 1,
}


def parse_file(path):
    """解析导出文件 -> [(dt_or_str, sender, text)]"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    msgs = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        ts = m.group("ts")
        dt = ts
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(ts, fmt)
                break
            except ValueError:
                continue
        msgs.append((dt, (m.group("who") or "").strip(), m.group("text").strip()))
    return msgs


def dt_of(m):
    return m[0] if isinstance(m[0], datetime) else None


# ---------------------------------------------------------------------------
# 扫描
# ---------------------------------------------------------------------------

def scan(messages, scen_key, focus=None, since=None, until=None):
    scen = SCENARIOS[scen_key]
    results = []
    for ekey, ename, kws, consequence in scen["elements"]:
        hits = []
        for dt, who, text in messages:
            d = dt_of((dt, who, text))
            if since and d and d.date() < since:
                continue
            if until and d and d.date() > until:
                continue
            if focus and focus not in (who or ""):
                continue
            matched = [k for k in kws if k in text]
            if matched:
                hits.append({
                    "time": dt.strftime("%Y-%m-%d %H:%M") if isinstance(dt, datetime) else str(dt),
                    "sender": who,
                    "keywords": matched[:5],
                    "text": text[:300],
                })
        results.append({
            "key": ekey, "name": ename, "consequence": consequence,
            "count": len(hits), "hits": hits[:40],
        })
    return results


AMONEY_CTX = re.compile(
    r"[块元万钱币]|工资|月薪|年薪|薪资|薪酬|薪水|底薪|绩效|奖金|提成|报酬|费用|金额|"
    r"定金|尾款|押金|租金|房租|欠|还|价|款|贷|薪"
)


def extract_amounts(messages):
    """抽取金额 -> {金额: [{时间,人,原文}]}"""
    found = {}
    for dt, who, text in messages:
        for m in AMOUNT_RE.finditer(text):
            num_s, unit = m.group(1), (m.group(2) or "")
            # 年份不算金额："2024年的提成"
            tail = text[m.end():m.end() + 2]
            if not unit and tail.startswith("年"):
                continue
            if not unit:
                # 裸数字：位数够大，且上下文出现金额/价格类词才认
                if len(num_s.replace(",", "")) < 3:
                    continue
                if not AMONEY_CTX.search(text):
                    continue
            try:
                val = float(num_s.replace(",", ""))
            except ValueError:
                continue
            amount = int(val * AMOUNT_UNITS.get(unit, 1))
            if amount < 100:
                continue
            found.setdefault(amount, []).append({
                "time": dt.strftime("%Y-%m-%d %H:%M") if isinstance(dt, datetime) else str(dt),
                "sender": who,
                "text": text[:200],
            })
    return dict(sorted(found.items(), key=lambda kv: -kv[0]))


def find_anchors(messages, scen_key):
    """识别关键节点 -> [(时间, 标签, 说话人, 原文)]"""
    scen = SCENARIOS[scen_key]
    anchors = scen.get("keywords_anchor", {})
    out = []
    seen = set()
    for dt, who, text in messages:
        for k, label in anchors.items():
            if k in text:
                key = (label, dt)
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "time": dt.strftime("%Y-%m-%d %H:%M") if isinstance(dt, datetime) else str(dt),
                    "label": label, "sender": who, "text": text[:200],
                })
                break
    out.sort(key=lambda x: x["time"])
    return out


def compute_deadline(messages, scen_key, as_of):
    """时效倒计时：取最早消息日期作为保守起算日"""
    scen = SCENARIOS[scen_key]
    years = scen.get("time_limit_years")
    dts = [dt_of(m) for m in messages if dt_of(m)]
    if not dts:
        return None
    earliest = min(dts).date()
    if years is None:
        return {"has_limit": False,
                "note": scen["time_limit_note"],
                "earliest": str(earliest)}
    try:
        end = earliest.replace(year=earliest.year + years)
    except ValueError:
        # 2/29 落到平年，退到 2/28
        end = date(earliest.year + years, 2, 28)
    days = (end - as_of).days
    return {
        "has_limit": True,
        "earliest": str(earliest),
        "deadline": str(end),
        "days_left": days,
        "expired": days < 0,
        "note": scen["time_limit_note"],
        "caveat": "以聊天记录最早日期作为保守起算日，仅供参考；实际起算点通常是"
                  "'知道或应当知道权利受损之日'，可能更晚。建议以关键事件日期重新核算。",
    }


def _valid(y, m, d):
    try:
        date(y, m, d)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------

def render_markdown(results, amounts, anchors, deadline, scen_key, total):
    scen = SCENARIOS[scen_key]
    L = []
    L.append("# 微信证据链扫描报告")
    L.append("")
    L.append("**场景：** %s　|　**消息总数：** %d" % (scen["label"], total))
    L.append("")
    L.append("> 本报告由脚本自动生成，仅做关键词匹配与机械计算，**不构成法律判断或法律意见**。")
    L.append("> 命中不等于有效证据，必须人工逐条确认后再使用。")
    L.append("")

    covered = [r for r in results if r["count"] > 0]
    missing = [r for r in results if r["count"] == 0]
    L.append("## 一、结论先行")
    L.append("")
    L.append("| 指标 | 结果 |")
    L.append("|---|---|")
    L.append("| 场景 | %s |" % scen["label"])
    L.append("| 要件覆盖 | **%d / %d** |" % (len(covered), len(results)))
    L.append("| 有命中的要件 | %s |" % ("、".join(r["name"] for r in covered) or "无"))
    L.append("| 完全没有命中的要件 | %s |" % ("、".join(r["name"] for r in missing) or "无"))
    if deadline and deadline.get("has_limit"):
        if deadline["expired"]:
            L.append("| 时效 | ⚠️ **可能已过**（按最早记录 %s 起算，届满日 %s） |"
                     % (deadline["earliest"], deadline["deadline"]))
        else:
            L.append("| 时效 | 约剩 **%d 天**（保守估算，届满日 %s） |"
                     % (deadline["days_left"], deadline["deadline"]))
    elif deadline:
        L.append("| 时效 | %s |" % deadline["note"])
    L.append("| 抽取到金额种类 | %d |" % len(amounts))
    L.append("")

    L.append("## 二、要件命中表")
    L.append("")
    L.append("| 要件 | 命中数 | 状态 |")
    L.append("|---|---:|---|")
    for r in results:
        st = "✅ 有材料" if r["count"] else "❌ 缺失"
        L.append("| %s | %d | %s |" % (r["name"], r["count"], st))
    L.append("")

    L.append("## 三、命中片段明细")
    L.append("")
    for r in results:
        if not r["count"]:
            continue
        L.append("### %s（%d 条）" % (r["name"], r["count"]))
        L.append("")
        for h in r["hits"][:15]:
            L.append("- `%s` **%s**：%s" % (h["time"], h["sender"] or "（未知）", h["text"]))
        if r["count"] > 15:
            L.append("- _… 还有 %d 条，未展示_" % (r["count"] - 15))
        L.append("")

    if missing:
        L.append("## 四、缺失要件与补强方向")
        L.append("")
        L.append("| 缺失要件 | 缺失后果 | 去哪儿补 |")
        L.append("|---|---|---|")
        supplement = {
            "deliver": "银行流水、微信支付账单、支付宝账单",
            "paid": "支付账单、转账凭证",
            "rel": "合同、offer、入职登记、社保记录",
            "form": "合同文本、订单截图、报价单",
            "fault": "报警记录、110/122 出警单、现场监控",
            "harm": "诊断证明、医疗费票据、鉴定报告",
            "marry": "结婚证、户籍、财产登记信息",
            "contract": "劳动合同文本、续签记录",
            "insure": "社保缴纳记录、公积金明细",
            "amount": "支付账单、结算单",
            "condition": "入住交接单、损耗清单、维修票据",
            "utility": "水电燃气账单、物业费清单",
        }
        for r in missing:
            L.append("| %s | %s | %s |" % (
                r["name"], r["consequence"], supplement.get(r["key"], "需另行收集原始凭证")))
        L.append("")

    if amounts:
        L.append("## 五、金额梳理")
        L.append("")
        L.append("| 金额 | 出现次数 | 首次出现 | 说话人 |")
        L.append("|---:|---:|---|---|")
        for amt, occ in list(amounts.items())[:25]:
            first = occ[0]
            senders = sorted({o["sender"] for o in occ if o["sender"]})
            L.append("| %s | %d | %s | %s |" % (
                format(amt, ","), len(occ), first["time"], "、".join(senders) or "—"))
        L.append("")
        L.append("> ⚠️ 同一个金额可能对应不同笔款项。**不要自行取平均或合并**，"
                 "逐条核对后按主张分别列明。")
        L.append("")

    if anchors:
        L.append("## 六、关键节点时间线")
        L.append("")
        L.append("| 时间 | 标签 | 说话人 | 原文 |")
        L.append("|---|---|---|---|")
        for a in anchors[:60]:
            L.append("| %s | %s | %s | %s |" % (
                a["time"], a["label"], a["sender"] or "—", a["text"]))
        L.append("")

    if deadline:
        L.append("## 七、时效提示")
        L.append("")
        if deadline.get("has_limit"):
            L.append("- 记录中最早消息：**%s**" % deadline["earliest"])
            L.append("- 推算届满日：**%s**" % deadline["deadline"])
            if deadline["expired"]:
                L.append("- ⚠️ **按此推算已过期 %d 天**。" % abs(deadline["days_left"]))
            else:
                L.append("- 剩余约 **%d 天**。" % deadline["days_left"])
            L.append("- 法条/规则：%s" % deadline["note"])
            L.append("- ⚠️ %s" % deadline["caveat"])
        else:
            L.append("- %s" % deadline["note"])
        L.append("")

    L.append("---")
    L.append("")
    L.append("**免责声明**：本报告由脚本自动生成，仅做关键词匹配与机械计算，"
             "**不构成法律意见、不预测胜诉率**。命中与否不等于证据是否有效，"
             "必须人工逐条确认。重大金额或复杂案情请咨询专业律师或当地法律援助中心。")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="微信证据链扫描器（仅关键词匹配与机械计算，不构成法律意见）")
    ap.add_argument("--file", required=True, help="wechat-cli export 出的 .md / .txt")
    ap.add_argument("--scenario", default="all",
                    help="labor/rent/loan/contract/tort/family/all，默认 all")
    ap.add_argument("--as-of", default=None, help="时效基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--since", default=None, help="只扫该日期之后 YYYY-MM-DD")
    ap.add_argument("--until", default=None, help="只扫该日期之前 YYYY-MM-DD")
    ap.add_argument("--focus", default=None, help="只看某人（对方姓名）")
    ap.add_argument("--out", default=None, help="报告输出路径")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print("文件不存在: %s" % args.file, file=sys.stderr)
        return 2

    try:
        messages = parse_file(args.file)
    except OSError as e:
        print("读取文件失败: %s" % e, file=sys.stderr)
        return 2

    if not messages:
        print("没有解析到任何消息。请确认文件是 `wechat-cli export --format markdown` "
              "或 `--format txt` 的输出。", file=sys.stderr)
        return 1

    as_of = (datetime.strptime(args.as_of, "%Y-%m-%d").date()
             if args.as_of else date.today())
    since = datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None
    until = datetime.strptime(args.until, "%Y-%m-%d").date() if args.until else None

    keys = list(SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]
    for k in keys:
        if k not in SCENARIOS:
            print("未知场景: %s（可选: %s, all）"
                  % (k, "/".join(SCENARIOS.keys())), file=sys.stderr)
            return 2

    report = {"file": args.file, "as_of": str(as_of), "total_messages": len(messages),
              "scenarios": {}}

    md_parts = []
    for k in keys:
        results = scan(messages, k, focus=args.focus, since=since, until=until)
        amounts = extract_amounts(messages)
        anchors = find_anchors(messages, k)
        deadline = compute_deadline(messages, k, as_of)
        report["scenarios"][k] = {
            "label": SCENARIOS[k]["label"],
            "elements": results, "amounts": amounts,
            "anchors": anchors, "deadline": deadline,
        }
        if args.format == "md":
            md_parts.append(render_markdown(
                results, amounts, anchors, deadline, k, len(messages)))

    if args.format == "json":
        text = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        text = ("\n\n" + ("\n\n" + "=" * 60 + "\n\n").join(md_parts))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("报告已生成: %s" % args.out)
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
