#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旅游投诉维权与退款核算。

用法：
  python tour_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python tour_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta

VERSION = "1.0.0"

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "待补充", "请填", "例如", "示例", "如：", "填什么", "（", "(", "有/无"]

# ------------------------------------------------------------------ 解析
def norm(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("：", ":").replace("（", "(").replace("）", ")")
    s = s.replace("，", ",").replace("。", ".")
    s = re.sub(r"\s+", "", s)
    return s.strip()


def build_kv(text):
    """解析 markdown 表格行与 '字段：值' 行。"""
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
            parts = re.split(r"[:：]", line, maxsplit=1)
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
    if v is None:
        return False
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return True
    v = (v or "").strip()
    if not v:
        return False
    if UNFILLED_MARK.search(v):
        return False
    for w in PLACEHOLDER_WORDS:
        if w in v:
            return False
    return True


def yes(v):
    n = norm(v)
    return n in ("有", "是", "已经", "已", "已申请", "已提出", "已拨打", "已提交", "true", "yes")


def no(v):
    n = norm(v)
    return n in ("无", "否", "没有", "未", "未申请", "未提出", "未拨打", "未提交", "false", "no")


def yes_soft(v):
    """宽松「是」判定：整串命中或用「是/已」开头（兼容「是，改了行程」这类写法）。"""
    if yes(v):
        return True
    n = norm(v)
    return n.startswith("是") or n.startswith("已")


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


def fmt_money(x):
    if x is None:
        return "¥—"
    if abs(x - round(x)) < 1e-6:
        return "¥%d" % round(x)
    return "¥%s" % fmt_num(x)


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


# ------------------------------------------------------------------ 定性
FORCE_MAJEURE_WORDS = ["台风", "地震", "洪水", "暴雨", "暴雪", "疫情", "管控", "封控",
                       "管制", "交通中断", "关闭", "闭园", "极端天气"]


def has_w(s, words):
    s = s or ""
    for w in words:
        if w in s:
            return True
    return False


def classify_type(f):
    """返回 (定性串, 依据说明)。"""
    lines = []
    if has_w(f["change_plan"], ["擅自", "变更", "减少", "取消", "砍", "缩"]):
        lines.append("旅行社违约：擅自变更行程 / 减少景点（可主张退未发生费用；"
                     "造成严重后果的可主张旅游费用一倍以上三倍以下赔偿金，《旅游法》相关规定）")
    if yes_soft(f["force_shop"]):
        lines.append("旅行社违约：强迫或变相强迫购物（《旅游法》相关规定：不得强迫或变相强迫，"
                     "违反的可主张退货并先行垫付退货货款）")
    if f["extra_pay_known"] and yes(f["extra_pay"]):
        lines.append("旅行社违约：另行付费项目未事先说明（《旅游法》相关规定：应事先告知，"
                     "可拒绝支付并要求退还已收费用）")
    if f["hotel_down"] or f["meal_down"] or yes(f["guide_mismatch"]):
        lines.append("旅行社违约：降低服务标准 / 导游服务与承诺不符（可主张退差价与赔偿）")
    if has_w(f["major_break"], ["甩团", "拒载", "滞留", "未安排返程", "拒绝送回"]):
        lines.append("旅行社违约：甩团 / 拒载返程（可主张全额退费与赔偿，并行政投诉）")
    if yes(f["personal_cancel"]):
        lines.append("个人原因退团：按合同扣费阶梯核算可退区间（不适用旅行社违约的赔偿口径）")
    if has_w(f["force_majeure"], FORCE_MAJEURE_WORDS):
        lines.append("不可抗力/已尽合理注意仍不能避免的事件：扣除已支付且不可退还费用后退还余款，"
                     "额外食宿费由旅游者承担、返程费双方分担（《旅游法》相关规定）")
    if has_w(f["force_majeure"], FORCE_MAJEURE_WORDS) and (f["hotel_down"] or f["meal_down"]
                               or has_w(f["change_plan"], ["变更", "减少", "取消"])):
        lines.append("混合情形：官方公告之外仍存在服务标准降低等违约事实，应**分别主张**，"
                     "不可抗力不当然免除旅行社的违约赔偿责任")
    if f["on_platform"] and f["disagree"]:
        lines.append("平台（OTA）责任：订单页面承诺与实际不符，平台作为销售方承担合同责任，"
                     "可先行赔付后向商家追偿")
    if not lines:
        return "待补正", "纠纷事实未填或不明确，无法定性；请填「是否擅自变更行程」「是否有强迫购物」「是否因个人原因退团」等项。"
    return "；".join(lines), "依《旅游法》《民法典》通用规则对各项事实分别定性后汇总。"


# ------------------------------------------------------------------ 退款
# (距出发最少天数, 扣费比例下限%, 扣费比例上限%, 档位说明)
CANCEL_TIERS = [
    (15, 0, 5, "出发前 15 日以上"),
    (7, 10, 20, "出发前 7~15 日"),
    (4, 20, 40, "出发前 4~7 日"),
    (1, 40, 60, "出发前 1~3 日"),
    (-10 ** 6, 60, 80, "出发当日或未通知即不到"),
]


def refund_calc(f):
    """返回 (可退比例下限, 上限, 口径说明)。"""
    if not yes(f["personal_cancel"]):
        return None, None, ("非个人原因（旅行社原因/不可抗力）取消或变更：一般应全额退还"
                            "已支付但未提供服务的费用；已实际发生且不可退还的部分由旅行社举证。"
                            "因旅行社自身原因取消的，不得扣游客的钱。")
    if f["total"] is None:
        return None, None, "合同总价未填，无法折算可退区间；请先填合同总价。"
    days = f["days_left"]
    if days is None:
        return None, None, ("距出发天数未填，无法套用扣费阶梯。"
                            "可填「距出发还有几天」，或用退团通知日期与出发日期推算。")
    for min_d, cut_lo, cut_hi, label in CANCEL_TIERS:
        if days >= min_d:
            lo_pct = 100 - cut_hi
            hi_pct = 100 - cut_lo
            note = ("%s：常见扣费比例 %d%%~%d%%，对应可退比例 %d%%~%d%%，"
                    "按合同总价 %s 折算约 %s ~ %s。具体比例以你手上的合同与当地示范文本为准，"
                    "且扣费不得超过旅行社的实际损失与合理违约金；"
                    "旅行社应就已发生且不可退还的费用举证。" % (
                        label, cut_lo, cut_hi, lo_pct, hi_pct,
                        fmt_money(f["total"]),
                        fmt_money(f["total"] * lo_pct / 100.0),
                        fmt_money(f["total"] * hi_pct / 100.0)))
            return lo_pct, hi_pct, note
    return None, None, "距出发天数无法识别。"


# ------------------------------------------------------------------ 核查
def checks_breach(f):
    out = []

    def row(name, on, detail, fix):
        if on is True:
            out.append((name, "不通过", detail + " " + fix))
        elif on is False:
            out.append((name, "通过", "未发生此项。"))
        else:
            out.append((name, "待补正", "未填，" + fix))

    cp = f["change_plan"]
    if filled(cp):
        if yes_soft(cp) or has_w(cp, ["擅自", "变更", "减少", "取消", "砍", "缩"]):
            out.append(("擅自变更行程/减少景点", "不通过",
                        "情形：%s。原行程单未游玩的部分应当退费；造成严重后果的，"
                        "还可主张旅游费用一倍以上三倍以下的赔偿金（《旅游法》相关规定）。" % cp))
        elif no(cp):
            out.append(("擅自变更行程/减少景点", "通过", "行程未发生擅自变更。"))
        else:
            out.append(("擅自变更行程/减少景点", "待补正",
                        "填写不明确，请写「是（说明改了什么）」或「否」。"))
    else:
        out.append(("擅自变更行程/减少景点", "待补正", "未填。这是最常见的违约项，务必先确认。"))

    fs = f["force_shop"]
    if filled(fs):
        if yes_soft(fs):
            detail = ("情形：%s。进店时长 + 全程无自由时间 + 禁止离团，"
                      "三件事凑齐即可认定变相强迫购物。" % fs)
            out.append(("强迫或变相强迫购物", "不通过",
                        detail + " 可在**行程结束后 30 日内**要求旅行社办理退货并先行垫付退货货款。"))
        elif no(fs):
            out.append(("强迫或变相强迫购物", "通过", "未强迫购物。"))
        else:
            out.append(("强迫或变相强迫购物", "待补正", "填写不明确，请写「是/否」并说明进店时长。"))

    if f["extra_pay_known"]:
        if yes(f["extra_pay"]):
            know = f["extra_pay_known_txt"]
            if yes(know) or has_w(know, ["事先", "已说明", "合同载明"]):
                out.append(("另行付费项目", "通过", "另有另行付费且已事先说明，属约定内容。"))
            elif no(know):
                out.append(("另行付费项目未事先说明", "不通过",
                            "存在另行付费项目但合同/宣传未事先说明（《旅游法》相关规定），"
                            "可拒绝支付并要求退还已收费用。"))
            else:
                out.append(("另行付费项目是否事先说明", "待补正", "未填，请核对宣传页与行程单有无注明。"))
        elif no(f["extra_pay"]):
            out.append(("另行付费项目", "通过", "无另行付费项目。"))
        else:
            out.append(("另行付费项目", "待补正", "填写不明确。"))

    if f["hotel_down"] or f["meal_down"]:
        bits = []
        if f["hotel_down"]:
            bits.append("住宿：约定「%s」→ 实际「%s」" % (f["hotel_std"] or "未填", f["hotel_actual"] or "未填"))
        if f["meal_down"]:
            bits.append("餐食：约定「%s」→ 实际「%s」" % (f["meal_std"] or "未填", f["meal_actual"] or "未填"))
        out.append(("降低服务标准", "不通过",
                    "；".join(bits) + "。应退差价并赔偿损失，请保留现场照片与房型/餐单证据。"))
    elif filled(f["hotel_std"]) or filled(f["meal_std"]):
        out.append(("降低服务标准", "通过", "未反映住宿/餐食标准降低。"))
    else:
        out.append(("降低服务标准", "待补正",
                    "合同约定的住宿与餐标未填，无法与实际对比；请照抄合同附件行程单。"))

    mb = f["major_break"]
    if filled(mb):
        if yes_soft(mb) or has_w(mb, ["甩团", "拒载", "滞留", "未安排返程", "拒绝送回"]):
            out.append(("甩团/拒载返程", "不通过",
                        "情形：%s。属严重违约，可主张全额退费与赔偿，并向文旅主管部门投诉。" % mb))
        elif no(mb):
            out.append(("甩团/拒载返程", "通过", "未发生甩团或拒载返程。"))
        else:
            out.append(("甩团/拒载返程", "待补正", "填写不明确。"))

    w = f["waiver"]
    if filled(w) and (yes(w) or has_w(w, ["签了", "签署", "放弃"])):
        out.append(("已签免责/放弃索赔协议", "有风险",
                    "已签署（%s）。该类协议效力有争议且会显著提高举证难度；"
                    "如系受胁迫签署，请保存现场照片、沟通记录与行程事实材料，"
                    "仍可依法主张无效或撤销。" % w))
    return out


def checks_evidence(f):
    items = [
        ("旅游合同/电子合同", f["ev_contract"], "合同全文截图（含附件行程单），不要只截首屏"),
        ("行程单", f["ev_itinerary"], "逐日行程、景点、餐标、住宿标准"),
        ("付款凭证与发票", f["ev_pay"], "订单页 + 支付流水 + 发票"),
        ("宣传页/广告", f["ev_ad"], "网页快照、海报、销售聊天里的承诺"),
        ("现场照片视频", f["ev_photo"], "住宿、餐食、景点门口、购物店门头"),
        ("沟通记录", f["ev_chat"], "群聊/短信/录音，须含对方身份与时间"),
        ("门票住宿票据", f["ev_ticket"], "发票、订单确认单、房卡记录"),
        ("购物小票/发票", f["ev_shop_ticket"], "小票要写清商品名称与价格"),
        ("同行证言", f["ev_witness"], "书面证言 + 联系方式，多人更有力"),
        ("不可抗力官方公告", f["ev_announce"], "气象/交通/管制/闭园的官方发布"),
    ]
    out = []
    for name, v, need in items:
        if yes(v):
            out.append((name, "通过", "已具备。" + need))
        elif no(v):
            out.append((name, "不通过", "缺失。" + need + "这是认定事实的基础，缺一项就少一分胜算。"))
        else:
            out.append((name, "待补正", "未填。" + need))
    return out


def checks_channel(f):
    out = []
    wc = f["written_complain"]
    if yes(wc):
        out.append(("已向旅行社书面投诉", "通过",
                    "已提交（%s）。书面交涉是全程第一步，务必留存提交凭证与回复。" % wc))
    elif no(wc):
        out.append(("已向旅行社书面投诉", "待补正",
                    "尚未书面交涉。先提交书面投诉（事实 + 约定对照 + 诉求 + 金额 + 7~15 日期限），"
                    "再往上走渠道，行政受理会顺畅得多。"))
    else:
        out.append(("已向旅行社书面投诉", "待补正", "未填，请先做书面交涉。"))

    for key, label, done_word in (
        ("platform_appeal", "OTA 平台申诉", "平台介入/先行赔付"),
        ("d12345", "12345 政务服务热线", "派单到属地文旅部门，拿工单号"),
        ("cultur", "文旅主管部门投诉", "查证违规，可调取采购与结算记录"),
        ("d12315", "12315 市场监管", "购物假货、虚假宣传、价格欺诈"),
    ):
        v = f[key]
        if yes(v):
            out.append((label, "通过", "已办：%s。" % done_word))
        elif no(v):
            out.append((label, "待补正", "尚未办：%s；建议按旅行社→平台→12345→文旅→12315→仲裁诉讼的顺位推进。" % done_word))
        else:
            out.append((label, "待补正", "未填。" + done_word))
    return out


def todo_list(f, results, days90, days30):
    todos = []
    for _t, rows in results:
        for r in rows:
            if r[1] in ("不通过", "有风险", "待补正"):
                todos.append((r[0], r[1]))
    extra = []
    if days90 is not None and days90 < 0:
        extra.append(("投诉时效已过", "旅游投诉一般应在合同结束后 90 日内提出，已过 %d 天，"
                      "仍可起诉（诉讼时效 3 年），但行政投诉受理可能被卡" % -days90))
    elif days90 is not None:
        extra.append(("投诉 90 日倒计时", "距合同结束满 90 日还剩 %d 天，尽早提交" % days90))
    if days30 is not None and days30 < 0:
        extra.append(("购物退货 30 日已过", "行程结束后 30 日内可要求旅行社办理退货并先行垫付，已过 %d 天，"
                      "仍可就欺诈主张其他救济（如 12315、诉讼）" % -days30))
    elif days30 is not None and days30 <= 7:
        extra.append(("购物退货 30 日倒计时", "还剩 %d 天，尽快书面提出退货要求" % days30))
    if not filled(f["total"]):
        extra.append(("补填合同总价", "没有总价算不出可退区间"))
    if not filled(f["evidence_list"]):
        extra.append(("补证据清单", "合同、行程单、宣传页、票据、沟通记录，能存几份存几份"))
    seen = set()
    out = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        out.append((n, s))
    return out


# ------------------------------------------------------------------ 报告
def render(f, results, dtype, basis, lo, hi, refund_note, todos, today, days90, days30):
    L = []
    A = L.append

    A("# 旅游投诉维权与退款核算报告")
    A("")
    A("> 生成日期：%s；脚本版本 v%s；投诉人：%s；被投诉主体：%s；团号：%s" % (
        today.isoformat(), VERSION, f["complainant"] or "未填",
        f["target"] or "未填", f["group_no"] or "未填"))
    A("")

    bad = [r for _t, rs in results for r in rs if r[1] == "不通过"]
    risk = [r for _t, rs in results for r in rs if r[1] == "有风险"]
    todo = [r for _t, rs in results for r in rs if r[1] == "待补正"]

    A("## 一、结论摘要")
    A("")
    if bad:
        A("**判定：存在明确的旅行社违约事实，可主张退款与赔偿（不通过）**。")
    elif risk:
        A("**判定：存在风险点，需补正后主张（有风险）**。")
    elif todo:
        A("**判定：关键事实与材料还差几项（待补正）**。")
    else:
        A("**判定：未发现明显违约点；若仍有争议，按下一段渠道推进（通过）**。")
    A("")
    A("| 项 | 数量 |")
    A("|---|---|")
    A("| 不通过 | %d |" % len(bad))
    A("| 有风险 | %d |" % len(risk))
    A("| 待补正 | %d |" % len(todo))
    A("")
    A("- **纠纷定性**：%s" % dtype)
    if lo is not None and hi is not None and f["total"] is not None:
        A("- **可退金额区间**：%s ~ %s（合同总价 %s 折算）" % (
            fmt_money(f["total"] * lo / 100.0), fmt_money(f["total"] * hi / 100.0),
            fmt_money(f["total"])))
    elif f["total"] is not None:
        A("- **可退金额区间**：合同总价 %s，可退比例待定（见第四段口径）" % fmt_money(f["total"]))
    else:
        A("- **可退金额区间**：合同总价未填，无法折算")
    printed = set(["纠纷定性"])
    for r0 in (bad + risk):
        if r0[0] in printed:
            continue
        printed.add(r0[0])
        A("- **%s**：%s" % (r0[0], str(r0[2])[:60].replace("**", "")))
        if len(printed) >= 7:
            break
    A("")

    titles = ["二、纠纷定性与法条依据", "三、违约项逐条核查", "四、退款核算与可退区间",
              "五、购物与退货（30 日规则）", "六、证据清单与取证缺口", "七、渠道阶梯与时限"]
    for (title, rr), t in zip(results[:6], titles):
        if not rr:
            continue
        A("## %s" % t)
        A("")
        A("| 核查项 | 判定 | 说明 |")
        A("|---|---|---|")
        for r0 in rr:
            A("| %s | %s | %s |" % (r0[0], r0[1], str(r0[2]).replace("|", " ")))
        A("")

    A("**渠道阶梯**（按顺序推进，别跳步）：")
    A("")
    for step, txt in (
        ("第 1 步", "向旅行社书面交涉：事实 + 约定对照 + 诉求 + 金额 + 7~15 日书面答复期限"),
        ("第 2 步", "OTA 平台介入/先行赔付：走平台退款与赔付通道"),
        ("第 3 步", "12345 政务服务热线（原 12301 已并入）：派单属地文旅部门，拿工单号"),
        ("第 4 步", "文旅主管部门 / 文化市场综合执法：查证违规，可调取采购与结算记录"),
        ("第 5 步", "全国旅游监管服务平台：正式投诉受理，可查处理进度"),
        ("第 6 步", "12315 市场监管：购物假货、虚假宣传、价格欺诈"),
        ("第 7 步", "仲裁 / 诉讼：合同有有效仲裁条款的先仲裁，否则 3 年内起诉"),
    ):
        A("- **%s**：%s" % (step, txt))
    A("")

    A("## 八、待办补正动作")
    A("")
    if not todos:
        A("当前未发现必须补正的事项。")
    else:
        A("| 动作 | 状态 |")
        A("|---|---|")
        for n, s in todos:
            A("| %s | %s |" % (n, s))
    A("")

    A("## 九、边界与纪律")
    A("")
    A("- 本结果依《旅游法》《民法典》**通用规则**整理，**不替代律师意见**，"
      "不预测行政处理与诉讼结果。")
    A("- 各地投诉受理细则、退团扣费阶梯、质量保证金赔付条件**以当地文旅主管部门与市场监管口径为准**"
      "（查询入口：全国旅游监管服务平台、当地文旅局官网/公众号、12345）。")
    A("- 法条引用只写**法律名称与内容**；条文号不确定的一律按「《旅游法》相关规定」处理，不编造条号。")
    A("")
    A("- **可退区间**是依常见扣费阶梯给出的估算区间，不是承诺数；实际以合同、"
      "当地示范文本与文旅/司法认定为准。")
    A("- 不代写投诉信终稿与法律文书，只给要点与话术。")
    A("- **未填的一律不算通过**，只按已填内容判断。")
    A("")
    A("本结果依通用规则整理，不替代专业意见，最终以主管部门/司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, dtype, lo, hi, todos, today):
    return {
        "版本": VERSION,
        "生成日期": today.isoformat(),
        "被投诉主体": f["target"],
        "纠纷定性": dtype,
        "结论": f.get("verdict", "待补正"),
        "结论明细": {
            "不通过": [r[0] for _t, rs in results for r in rs if r[1] == "不通过"],
            "有风险": [r[0] for _t, rs in results for r in rs if r[1] == "有风险"],
            "待补正": [r[0] for _t, rs in results for r in rs if r[1] == "待补正"],
        },
        "风险项": [r[0] for _t, rs in results for r in rs if r[1] == "有风险"],
        "可退比例": {"下限": lo, "上限": hi},
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_report(path, base=None):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:
        return None, "读不了文件：%s" % e

    if base is None:
        base = date.today()

    kv = build_kv(text)
    today = base

    f = {
        "complainant": get_text(kv, ["投诉人姓名", "投诉人"]),
        "target": get_text(kv, ["被投诉主体", "被投诉旅行社", "组团社"]),
        "group_no": get_text(kv, ["团号 / 合同号", "团号", "合同号"]),
        "form": get_text(kv, ["旅游形式"]),
        "dep_date": get_text(kv, ["出发日期"]),
        "end_date": get_text(kv, ["行程结束日期"]),
        "total": parse_num(get_text(kv, ["合同总价（元）", "合同总价", "合同金额"])),
        "paid": parse_num(get_text(kv, ["已支付总额（元）", "已支付总额"])),
        "refunded": parse_num(get_text(kv, ["旅行社已退金额（元）", "已退金额"])),
        "deduct_items": get_text(kv, ["已扣款项名目"]),
        "personal_cancel": get_text(kv, ["是否因个人原因退团", "是否个人原因退团"]),
        "notice_date": get_text(kv, ["退团/取消通知日期", "退团通知日期", "取消通知日期"]),
        "days_left": parse_num(get_text(kv, ["距出发还有几天", "距出发天数"])),
        "clause": get_text(kv, ["合同中的扣费条款", "扣费条款"]),
        "irrevocable": get_text(kv, ["是否已发生机票/酒店等不可退费用", "不可退费用"]),
        "shop_amt": parse_num(get_text(kv, ["购物消费金额（元）", "购物消费金额"])),
        "shop_problem": get_text(kv, ["购物商品问题"]),
        "shop_return": get_text(kv, ["是否已申请退货", "是否申请退货"]),
        "change_plan": get_text(kv, ["是否擅自变更行程/减少景点", "是否变更行程", "变更行程"]),
        "force_shop": get_text(kv, ["是否有强迫或变相强迫购物", "强迫购物"]),
        "extra_pay": get_text(kv, ["是否有另行付费项目", "另行付费项目"]),
        "extra_pay_known_txt": get_text(kv, ["另行付费是否事先说明", "另行付费项目是否事先说明"]),
        "hotel_std": get_text(kv, ["合同约定的住宿标准", "住宿标准"]),
        "hotel_actual": get_text(kv, ["实际住宿情况", "实际住宿"]),
        "meal_std": get_text(kv, ["合同约定餐标", "餐标"]),
        "meal_actual": get_text(kv, ["实际餐标"]),
        "guide_mismatch": get_text(kv, ["导游服务与承诺不符", "导游与承诺不符"]),
        "major_break": get_text(kv, ["是否甩团/拒载返程", "甩团/拒载返程"]),
        "force_majeure": get_text(kv, ["是否有不可抗力事件", "不可抗力情况", "不可抗力"]),
        "ma_announce": get_text(kv, ["是否有官方公告"]),
        "ma_report": get_text(kv, ["是否及时报告并妥善安置"]),
        "written_complain": get_text(kv, ["是否已向旅行社书面投诉", "书面投诉"]),
        "reply": get_text(kv, ["旅行社回复情况"]),
        "platform_appeal": get_text(kv, ["是否向平台（OTA）申诉", "平台申诉"]),
        "d12345": get_text(kv, ["是否已拨打 12345"]),
        "cultur": get_text(kv, ["是否已向文旅主管部门投诉", "文旅投诉"]),
        "d12315": get_text(kv, ["是否已向 12315 投诉"]),
        "waiver": get_text(kv, ["是否已签署免责/放弃索赔协议", "免责协议"]),
        "claim": get_text(kv, ["处理诉求（你想拿到什么）", "诉求"]),
        "evidence_list": get_text(kv, ["已有证据清单", "证据清单"]),
        "ev_contract": get_text(kv, ["旅游合同/电子合同"]),
        "ev_itinerary": get_text(kv, ["行程单"]),
        "ev_pay": get_text(kv, ["付款凭证与发票", "付款凭证"]),
        "ev_ad": get_text(kv, ["宣传页/广告", "宣传页"]),
        "ev_photo": get_text(kv, ["现场照片视频", "现场照片"]),
        "ev_chat": get_text(kv, ["沟通记录（群聊/短信/录音）", "沟通记录"]),
        "ev_ticket": get_text(kv, ["门票住宿票据"]),
        "ev_shop_ticket": get_text(kv, ["购物小票/发票", "购物小票"]),
        "ev_witness": get_text(kv, ["同行证人", "同行证言"]),
        "ev_announce": get_text(kv, ["不可抗力官方公告"]),
    }
    f["hotel_down"] = bool(f["hotel_std"]) and bool(f["hotel_actual"]) and f["hotel_std"] != f["hotel_actual"]
    f["meal_down"] = bool(f["meal_std"]) and bool(f["meal_actual"]) and f["meal_std"] != f["meal_actual"]
    f["extra_pay_known"] = bool(f["extra_pay_known_txt"]) or bool(f["extra_pay"])
    f["on_platform"] = bool(f["platform_appeal"]) and yes(f["platform_appeal"])
    f["disagree"] = bool(f["ev_ad"]) or bool(f["ev_chat"])

    if not any([f["group_no"], f["end_date"], f["change_plan"], f["force_shop"],
                f["total"], f["dep_date"]]):
        return None, ("未解析到关键信息。至少填写「团号/合同号」或「行程结束日期」中的一项，"
                      "并填「是否擅自变更行程」「是否有强迫购物」等事实项。")

    dtype, dbasis = classify_type(f)

    # 时限计算
    days30 = days90 = None
    end_d = parse_date(f["end_date"])
    if end_d:
        days30 = (end_d + timedelta(days=30) - today).days
        days90 = (end_d + timedelta(days=90) - today).days

    lo, hi, refund_note = refund_calc(f)

    results = [
        ("纠纷定性", [("纠纷定性", "不通过" if dtype.startswith("旅行社违约")
                      else ("待补正" if dtype == "待补正" else "有风险"), dtype)]),
        ("违约项核查", checks_breach(f)),
        ("退款核算", [("可退区间与扣费口径", lo if lo is not None else "待补正", refund_note)]),
        ("购物与退货", shopping_checks(f, days30)),
        ("证据清单", checks_evidence(f)),
        ("渠道与时限", checks_channel(f)),
    ]

    todos = todo_list(f, results, days90, days30)

    bad = [r for _t, rs in results for r in rs if r[1] == "不通过"]
    risk = [r for _t, rs in results for r in rs if r[1] == "有风险"]
    todo = [r for _t, rs in results for r in rs if r[1] == "待补正"]
    if bad:
        f["verdict"] = "不通过"
    elif risk:
        f["verdict"] = "有风险"
    elif todo:
        f["verdict"] = "待补正"
    else:
        f["verdict"] = "通过"

    rep = render(f, results, dtype, dbasis, lo, hi, refund_note, todos, today, days90, days30)
    meta = to_json(f, results, dtype, lo, hi, todos, today)
    return rep, meta


def shopping_checks(f, days30):
    out = []
    amt = f["shop_amt"]
    if amt is None and not filled(f["shop_problem"]):
        out.append(("购物退货", "待补正",
                    "购物金额与商品问题均未填。若存在强迫购物，务必在行程结束后 30 日内"
                    "书面提出退货要求。"))
        return out
    if amt is not None:
        out.append(("购物金额", "通过", "购物消费 %s，请保留小票与发票（须写明商品名称与价格）。" % fmt_money(amt)))
    prob = f["shop_problem"]
    if filled(prob):
        if no(prob) or "无问题" in norm(prob):
            out.append(("商品问题", "通过", "商品无质量问题。"))
        else:
            out.append(("商品问题", "不通过",
                        "问题类型：%s。属假货/以次充好/价格虚高的，"
                        "可在行程结束后 30 日内要求旅行社办理退货并先行垫付退货货款。" % prob))
    sr = f["shop_return"]
    if yes(sr):
        out.append(("退货申请", "通过", "已向旅行社提出退货申请，请留存书面/聊天记录；"
                    "旅行社不办的，立即向文旅主管部门与 12315 投诉。"))
    elif no(sr):
        out.append(("退货申请", "不通过",
                    "尚未提出退货申请。旅行社以不合理低价组织旅游并通过安排购物获取回扣的，"
                    "旅游者在行程结束后 30 日内可要求其办理退货并先行垫付退货货款——这是最有效的一条。"))
    else:
        out.append(("退货申请", "待补正", "是否已申请退货未填。"))
    if days30 is not None:
        if days30 < 0:
            out.append(("30 日退货期限", "有风险",
                        "行程结束已满 30 日（超 %d 天）。30 日规则已过，"
                        "但如涉欺诈仍可向 12315、市场监管与法院主张。" % -days30))
        else:
            out.append(("30 日退货期限", "通过", "距行程结束满 30 日还剩 %d 天，抓紧提交退货要求。" % days30))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rep, meta = build_report(args.input, base_date(args.base))

    if rep is None:
        sys.stdout.write("%s\n" % meta)
        return 2

    if args.json:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(rep)
        sys.stdout.write("已写出 %s\n" % args.out)
    else:
        sys.stdout.write(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
