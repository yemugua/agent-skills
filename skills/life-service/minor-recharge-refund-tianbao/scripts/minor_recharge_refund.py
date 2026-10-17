#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""未成年人游戏充值退款核查。

用法：
  python minor_recharge_refund.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python minor_recharge_refund.py 采集表.md --json
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

# 八周岁以上未成年人的民事行为能力限制
MINOR_AGE = 8
FULL_CIVIL_AGE = 18

# 游戏类型与常见退款口径（实际以平台规则与法律为准）
GAME_TYPES = [
    ("网络游戏", ["网络游戏", "手游", "端游", "游戏", "账号", "点券", "钻石", "金币", "皮肤"]),
    ("直播打赏", ["直播", "打赏", "礼物", "火箭", "嘉年华", "主播", "投币"]),
    ("短视频道具", ["短视频", "道具", "抖币", "快币", "金币充值", "会员"]),
    ("网络文学付费", ["小说", "阅读", "书币", "追更", "章节"]),
    ("社交应用充值", ["社交", "群", "会员", "SVIP", "贵族"]),
]

# 家长已尽的监管义务（越充分越有利）
DUTY_DONE = [
    ("有完整的实名与年龄信息", ["实名", "身份证", "年龄", "出生", "实名认证"]),
    ("有未成年人游戏时长/消费限制", ["时长", "消费限制", "限额", "青少年模式", "防沉迷",
                          "未成年人模式", "成长守护"]),
    ("曾主动设置过支付密码", ["支付密码", "支付限额", "绑定", "免密", "扣费"]),
    ("有与孩子沟通的记录", ["沟通", "孩子说", "承认", "问过", "家庭会议", "教育"]),
    ("有心理评估或矫治记录", ["心理", "评估", "医院", "矫治", "咨询", "诊断"]),
]

# 未尽的监管义务（这些会成为平台抗辩点）
DUTY_MISSED = [
    ("未设置支付密码或免密", ["没设", "未设", "没有密码", "绑了卡", "免密", "直接扣",
                        "没绑卡"]),
    ("未开启防沉迷或消费限制", ["没开", "未开", "没有限制", "没设限额", "不知道有",
                       "没管"]),
    ("监护人本人账号共用", ["我的号", "共用", "用我的", "我的账号", "我的身份证", "我充的"]),
    ("长期放任不管或默许", ["知道", "一直", "经常", "默许", "没管过", "没时间管"]),
    ("存在家庭矛盾或暴力因素", ["打", "骂", "家庭", "离婚", "出走", "不管"]),
]

# 平台/商家可能的抗辩
PLATFORM_DEFENSE = [
    ("账号实名成年人", ["实名是", "实名认证是", "成年人", "身份证是大人", "实名信息是父母",
                  "成年人实名", "实名认证成年", "实名是成人"]),
    ("已尽合理审查义务", ["已核验", "已验证", "已尽", "合规", "已审查", "已提示"]),
    ("充值有完整消费记录", ["有记录", "有流水", "有订单", "消费记录完整", "有凭证",
                     "完整消费记录", "消费记录清晰", "消费记录详尽"]),
    ("已设置消费提醒", ["已提醒", "已发送", "短信提醒", "弹窗", "已提示风险"]),
    ("已多次索要实名信息", ["多次要求", "反复要求", "已要求实名", "已要求绑定"]),
]

# 维权路径
PATHS = [
    ("第 1 步（先固定证据，24 小时内）",
     "**别急着找客服吵架**。先做四件事："
     "① 保存订单号、充值流水、扣费记录；"
     "② 保存孩子的**游戏内聊天、留言、语音**（能证明是孩子操作）；"
     "③ **申请账号所有权人变更**或申请账号保护，防止孩子继续消费；"
     "④ 记录每一笔充值的**时间、金额、渠道**。"),
    ("第 2 步（与平台/商家协商，7 日内）",
     "向游戏运营方或直播/短视频平台提交**书面**退款申请，"
     "使用「未成年人**限制民事行为能力人**实施的行为，需法定代理人追认」"
     "这一法定理由。**一次说清诉求与证据清单**，要求书面答复。"),
    ("第 3 步（申请消费退款）",
     "通过平台的**未成年人充值退款通道**申请，"
     "按平台要求提交身份证明、监护关系证明、账号归属证明。"),
    ("第 4 步（申请行业主管部门介入）",
     "对游戏：向**所在地文化和旅游部门**、**新闻出版署**相关渠道投诉；"
     "对直播打赏：向 **网信办** 及直播平台所在地的文化部门反映；"
     "对短视频道具：向**广电总局** 相关渠道反映。"),
    ("第 5 步（拨 12315 与 12345）",
     "**12315** 消费者投诉举报平台（市场监管部门）、"
     "**12345** 政务服务便民热线，可作为补充与推动渠道。"),
    ("第 6 步（提交公安报案）",
     "存在**诈骗、诱导消费、平台漏洞**情形的，"
     "可报案主张诈骗；对恶意套取或诱导未成年人消费的，可要求移送。"),
    ("第 7 步（民事诉讼）",
     "协商与投诉无果，向**游戏运营主体所属公司所在地法院**起诉，"
     "以「限制民事行为能力人实施的民事法律行为未经法定代理人追认」为请求权基础，"
     "要求**返还充值款**。"),
]

# 证据类别
EVIDENCE = [
    ("身份与监护证明", ["身份证", "户口", "出生证", "监护", "亲子", "关系证明"]),
    ("账号归属与实名信息", ["实名", "账号", "注册", "身份证号", "账号信息"]),
    ("充值消费记录", ["订单", "流水", "充值记录", "扣费", "消费记录", "交易"]),
    ("孩子操作证据", ["聊天", "留言", "语音", "录屏", "视频", "朋友圈", "同学"]),
    ("沟通与教育记录", ["沟通", "录音", "孩子的", "承认", "学校", "老师"]),
    ("监护义务履行材料", ["防沉迷", "青少年模式", "支付密码", "限额", "设置截图"]),
    ("平台答复与协商记录", ["答复", "工单", "申请记录", "客服", "协商", "拒绝"]),
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
    if n in ("有", "是", "已经", "已", "已完成", "已做", "可以", "能", "已设置"):
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


def child_age(f):
    """从出生日期算周岁；未填返回 None。"""
    b = parse_date(f["child_birth"])
    if not b:
        return None
    today = base_date(f.get("_today") or "")
    y = today.year - b.year
    if (today.month, today.day) < (b.month, b.day):
        y -= 1
    return y


# ------------------------------------------------------------------ 一 主体与年龄
def checks_subject(f, today):
    out = []
    name = f["child_name"]
    if unknown(name):
        out.append(("未成年人身份", "待补正",
                    "孩子姓名、年龄、监护关系未填。"
                    "**退款主张的第一要件是「谁是未成年人」**："
                    "要提供身份证明与监护关系证明，否则平台不会受理。"))
    else:
        out.append(("未成年人身份", "通过", "孩子：%s" % name))

    b = f["child_birth"]
    age = child_age(dict(f, _today=today.isoformat()))
    if unknown(b):
        out.append(("未成年人年龄", "待补正",
                    "出生日期未填。**年龄决定适用哪条法律**："
                    "八周岁以上未成年人是限制民事行为能力人，"
                    "其实施的充值行为需法定代理人追认才有效。"))
    else:
        if age is None:
            out.append(("未成年人年龄", "待补正", "出生日期「%s」无法解析成日期。" % b))
        elif age < MINOR_AGE:
            out.append(("未成年人年龄", "有风险",
                        "孩子约 %d 周岁，**不满八周岁属于无民事行为能力人**。"
                        "这一点**对你更有利**：无民事行为能力人实施的民事法律行为"
                        "一律无效，平台**必须全额返还**。" % age))
        elif age < FULL_CIVIL_AGE:
            out.append(("未成年人年龄", "有风险",
                        "孩子 %d 周岁（%d~18 周岁），属于**限制民事行为能力人**。"
                        "充值行为效力处于「待追认」状态，**法定代理人明确表示不追认的，"
                        "该行为无效、可要求返还**。这是退款的主要法律依据。"
                        % (age, MINOR_AGE)))
        else:
            out.append(("未成年人年龄", "不通过",
                        "按填写的出生日期，孩子已满 18 周岁。"
                        "**成年人自主消费的充值一般不支持退款**，"
                        "除非能证明存在欺诈、诱导或平台漏洞。"))
    return out


# ------------------------------------------------------------------ 二 事实与场景
def classify(f):
    txt = (f["platform"] or "") + "|" + (f["scene"] or "")
    if not filled(txt):
        return []
    return [lbl for lbl, ws in GAME_TYPES if hit_any(txt, ws) is True]


def checks_scene(f):
    out = []
    kinds = classify(f)
    if unknown(f["platform"]):
        out.append(("消费场景", "待补正",
                    "在哪个平台、玩什么、充的什么项目未填。"
                    "**场景决定走哪个投诉渠道**：游戏找文旅与新闻出版，"
                    "直播打赏找网信与文化部门，短视频道具找广电。"))
    elif not kinds:
        out.append(("消费场景", "待补正",
                    "没识别出消费类型。平台与项目请按这些词填："
                    "游戏/手游/点券/皮肤、直播/打赏/礼物、"
                    "短视频/道具/抖币、小说/书币。"))
    else:
        out.append(("消费场景", "有风险",
                    "本次消费属于：**%s**。"
                    "不同类型的退款口径与投诉渠道不同，"
                    "**直播打赏最难退**，需重点证明未成年人行为与诱导情形。" % "、".join(kinds)))
    return out


def checks_consume(f):
    out = []
    if unknown(f["detail"]):
        out.append(("充值经过与操作人", "待补正",
                    "是谁充的、怎么发现孩子充的、孩子的年龄与认知情况未填。"
                    "**这是争议的核心事实**：平台会问「是否监护人本人操作」。"
                    "把发现的经过原样记下来，包括孩子一开始怎么说的。"))
    else:
        out.append(("充值经过与操作人", "有风险",
                    "已描述经过。**注意与孩子的沟通方式**："
                    "先了解孩子为什么要充、是否被诱导、是否有同学攀比，"
                    "这些情节会影响协商与投诉的说服力。"))
    it = f["is_minor_op"]
    if unknown(it):
        out.append(("是否为未成年人独立操作", "待补正",
                    "充值是孩子自己操作还是监护人代充未填。"
                    "**这一项对平台抗辩影响最大**，"
                    "如果有间接证据（游戏内留言、同学证言、设备记录）要一并提供。"))
    elif yes(it):
        out.append(("是否为未成年人独立操作", "通过",
                    "确认为未成年人独立操作。**这是主张成立的关键**，"
                    "请配合提供聊天记录、录屏等间接证据。"))
    else:
        out.append(("是否为未成年人独立操作", "不通过",
                    "若是监护人本人操作或授权操作，**退款主张很难成立**。"
                    "请核对是否为共享账号、代付、误操作或未识别到真实操作人。"))
    return out


# ------------------------------------------------------------------ 三 金额
def calc_amount(f):
    total = parse_num(f["amount"])
    times = parse_num(f["times"])
    period = parse_num(f["period_days"])
    first = parse_date(f["first_date"])
    res = {"可测算": total is not None, "总额": total, "笔数": None,
           "跨度": None, "日均": None, "说明": ""}
    if times is not None:
        res["笔数"] = int(times)
    if first is not None and period:
        res["跨度"] = "%d 天" % int(period)
        if period:
            res["日均"] = round(total / period, 2) if total else None
    if not res["可测算"]:
        res["说明"] = "充值总额未填，无法测算。"
        return res
    parts = ["合计 %s" % money(total)]
    if res["笔数"]:
        parts.append("共 %d 笔" % res["笔数"])
    if res["跨度"]:
        parts.append("跨度 %s" % res["跨度"])
    if res["日均"]:
        parts.append("日均 %s" % money(res["日均"]))
    detail = "；".join(parts)
    if res["笔数"] and res["笔数"] >= 10:
        res["说明"] = ("%s。**笔数多说明存在持续消费**，"
                       "这既增加了主张力度，也说明账户缺少消费限制，"
                       "**要求平台说明防沉迷与消费限制的落实情况**。" % detail)
    elif res["笔数"] and res["笔数"] >= 2:
        res["说明"] = ("%s。**存在多笔重复消费**，"
                       "足以说明行为超出未成年人年龄与认知范围。" % detail)
    else:
        res["说明"] = "%s。单笔金额较低，**建议仍走流程**，" \
                      "多数平台对未成年人充值的处理比协商态度更积极。" % detail
    return res


def checks_amount(f, calc):
    out = []
    if not calc["可测算"]:
        out.append(("充值金额", "待补正",
                    "充值总额未填。**金额以订单与流水为准**，"
                    "不要凭印象估算，否则申请时平台会要求核对。"))
    else:
        out.append(("充值金额", "通过", calc["说明"]))
    if unknown(f["first_date"]):
        out.append(("首次与末次充值时间", "待补正",
                    "第一次和最后一次充值是什么时候未填。"
                    "**时间跨度与发生时长的孩子年龄都影响主张**。"))
    else:
        out.append(("首次与末次充值时间", "通过",
                    "首次充值：%s。**与孩子当时年龄对应的时间点要写进申请材料**。"
                    % f["first_date"]))
    return out


# ------------------------------------------------------------------ 四 监护义务
def checks_duty(f):
    out = []
    done = f["duty_done"]
    if unknown(done):
        out.append(("已尽的监护义务", "待补正",
                    "是否设过支付密码、是否开过防沉迷、是否与孩子沟通过未填。"
                    "**家长已做的监管动作是争取全额退款的关键**，"
                    "证明你不是完全放任。"))
    else:
        hits = [lbl for lbl, ws in DUTY_DONE if hit_any(done, ws) is True]
        if hits:
            out.append(("已尽的监护义务", "通过",
                        "已做：%s。**这些都是有利的材料**，"
                        "截图或截图配合说明一并提交。" % "、".join(hits)))
        else:
            out.append(("已尽的监护义务", "待补正",
                        "填的是「%s」，没识别出已做的监管动作。"
                        "请用这些词补充：实名/年龄、支付密码/限额、"
                        "防沉迷/青少年模式、沟通/承认、支付密码设置截图。" % done))

    missed = f["duty_missed"]
    if unknown(missed):
        out.append(("未尽或被指出的监护义务", "待补正",
                    "有没有没设支付密码、共用自己账号、长期不管等情况未填。"
                    "**这些是平台最常用的抗辩点**，先自己想清楚比被对方指出来好。"))
    else:
        hits = [lbl for lbl, ws in DUTY_MISSED if hit_any(missed, ws) is True]
        if hits:
            out.append(("未尽或被指出的监护义务", "不通过",
                        "存在对你不利的因素：%s。"
                        "**这些会显著降低退款成功率**。"
                        "但也不是没有余地：平台仍应说明其防沉迷与消费限制是否落实、"
                        "是否尽到未成年人保护义务，可把主张重点转向平台的监管责任。"
                        % "、".join(hits)))
        else:
            out.append(("未尽或被指出的监护义务", "通过",
                        "未发现明显的监护缺失情形。**建议主动说明你已做的监管动作**。"))
    return out


# ------------------------------------------------------------------ 五 平台抗辩
def checks_defense(f):
    out = []
    d = f["platform_said"]
    if unknown(d):
        out.append(("平台的说法", "待补正",
                    "平台怎么答复的未填。"
                    "**平台常见抗辩有三条**：账号实名成年人、已尽审查义务、"
                    "充值有完整消费记录。逐条拆开看，别被一句「已尽义务」挡回去。"))
        return out
    hits = [lbl for lbl, ws in PLATFORM_DEFENSE if hit_any(d, ws) is True]
    if not hits:
        out.append(("平台的说法", "有风险",
                    "平台称：**%s**。**要求其提供具体证据**——"
                    "实名信息是谁提交的、有无核验记录、是否提示过、"
                    "免密支付是如何开通的。" % f["platform_said"]))
        return out
    weak = []
    if "账号实名成年人" in hits:
        weak.append("实名信息是谁填的？**若是用家长身份证注册的，"
                    "平台有没有向监护人核实过孩子的年龄**？")
    if "已尽合理审查义务" in hits:
        weak.append("**核实与提示的具体动作是什么**？有没有留存核验记录？"
                    "有没有对监护人发出风险提示？")
    if "充值有完整消费记录" in hits:
        weak.append("**消费记录完整不代表意思表示真实**。"
                    "限制民事行为能力人的行为效力待定，不因记录完整而有效。")
    if "已设置消费提醒" in hits:
        weak.append("**弹窗或短信提醒不等于有效告知**。"
                    "对未成年人，监护人主张不追认的，提示不能替代追认。")
    if "已多次索要实名信息" in hits:
        weak.append("**索要实名不等于核实实际使用人年龄**。"
                    "平台是否核实过实际操作人的年龄与身份？")
    out.append(("平台的说法", "有风险",
                "平台主张：%s。**逐条要求其举证**，重点是："
                "%s" % ("、".join(hits), "".join(weak))))
    return out


# ------------------------------------------------------------------ 六 证据
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
                    "已有证据既没勾选也没写清单。"
                    "**未成年人充值的核心争议是「究竟谁操作的」，"
                    "证据要围绕这一点组织**，而不是只堆订单截图。"))
        return out
    for label, keys in EVIDENCE:
        hit = [k for k in keys if k in got]
        if hit:
            out.append((label, "通过",
                        "已具备：%s。**原件留存、复印件提交**。" % "、".join(hit)))
        else:
            out.append((label, "有风险", "尚无%s材料，这类缺口会让申请被驳回。" % label))
    return out


EVID_FIX = {
    "身份与监护证明": "提供孩子身份证或户口本、监护关系证明（户口本即可）",
    "账号归属与实名信息": "从游戏内或 App 内截图实名信息与账号 ID",
    "充值消费记录": "在游戏内导出订单与充值流水，截图带订单号",
    "孩子操作证据": "保存游戏内聊天、语音、动态、同学证言，做成录屏",
    "沟通与教育记录": "保留与孩子沟通的录音或书面记录，必要时请老师出具说明",
    "监护义务履行材料": "截图防沉迷设置、支付密码设置、限额设置界面",
    "平台答复与协商记录": "保存工单号、答复截图、客服沟通记录",
}


def evidence_gap(f):
    got = (f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")
    gaps = []
    if has_content(got):
        for label, keys in EVIDENCE:
            if not any(k in got for k in keys):
                gaps.append(label)
    else:
        gaps = [x[0] for x in EVIDENCE]
    if not any(k in got for k in ["身份证", "户口", "监护", "亲子"]):
        gaps.append("身份与监护证明")
    if not any(k in got for k in ["聊天", "留言", "语音", "录屏", "视频"]):
        gaps.append("孩子操作证据")
    seen = set()
    res = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            res.append(g)
    return res


# ------------------------------------------------------------------ 路径与待办
def path_steps(f):
    return [(k, v) for k, v in PATHS]


def todo_list(f, results, calc):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    extra.append(("先保护账号防止继续消费", "申请账号保护或变更所有权人"))
    extra.append(("导出全部订单与充值流水", "带订单号，书面申请必须用"))
    extra.append(("固定孩子操作证据", "游戏内聊天、留言、语音，做成录屏"))
    extra.append(("书面提交退款申请", "以限制民事行为能力人需追认为理由，要书面答复"))
    extra.append(("向主管部门投诉", "游戏找文旅与新闻出版，直播找网信，短视频找广电"))
    if not has_content((f["evidence_owned"] or "") + "|" + (f["evidence_desc"] or "")):
        extra.append(("列证据清单并编号成册", "身份监护、账号归属、消费记录、操作证据"))
    if not filled(f["child_birth"]):
        extra.append(("提供孩子出生日期证明", "年龄决定适用的法律规则"))
    if not calc["可测算"]:
        extra.append(("核算充值总额与笔数", "以订单与流水为准"))
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
    "二、未成年人主体与年龄认定",
    "三、消费场景与事实认定",
    "四、充值金额与时间跨度",
    "五、监护义务与责任抗辩",
    "六、平台抗辩与应对",
    "七、证据清单与缺口",
]


def render(f, results, calc, steps, todos, today, gaps):
    L = []
    L.append("# 未成年人游戏充值退款核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 未成年人：%s" % (f["child_name"] or "未填"))
    L.append("- 消费平台：%s" % (f["platform"] or "未填"))
    L.append("- 充值总额：%s" % money(calc["总额"]))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：存在影响退款成立的不利因素，需先针对性补强。**"
                 "建议先补齐年龄、监护证明与孩子操作证据，再提交书面申请。")
    elif risk:
        L.append("**判定：基础事实成立，主张的法律依据是「限制民事行为能力人的行为"
                 "需法定代理人追认」，但仍有需要补强的环节。**"
                 "按第七、八段补齐材料后提交书面申请。")
    else:
        L.append("**判定：采集表关键项未填，暂时给不出确定结论；**"
                 "请把孩子年龄、平台、充值金额与经过填完再重跑。"
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

    L.append("## 八、维权路径与投诉渠道")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 九、证据缺口速查")
    L.append("")
    if not gaps:
        L.append("当前填写的材料已较完整。")
    else:
        L.append("| 缺失类别 | 补法 |")
        L.append("|---|---|")
        for g in gaps[:12]:
            L.append("| %s | %s |" % (g, EVID_FIX.get(g, "按操作卡补齐")))
    L.append("")

    L.append("## 十、待办补正动作")
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
             "未成年人充值退款的处理口径，**以平台规则、"
             "行业主管部门与司法机关认定为准**。")
    L.append("- 报告金额按已填订单与流水汇总，**实际退款金额以平台或法院认定为准**。")
    L.append("- 不预测平台是否同意退款，也不预测投诉与诉讼结果。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 涉及孩子姓名、学校、身份证号等未成年人隐私信息，"
             "**本地处理，不要外发**。")
    L.append("- 本结果依通用规则整理，不替代专业意见，"
             "最终以主管部门与司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, gaps, calc):
    return {
        "核查日期": today.isoformat(),
        "充值总额": calc["总额"],
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "金额测算": {
            "可测算": calc["可测算"],
            "总额": calc["总额"],
            "笔数": calc["笔数"],
            "跨度": calc["跨度"],
            "日均": calc["日均"],
        },
        "证据缺口": gaps,
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def build_fields(kv):
    return {
        "child_name": get_text(kv, ["未成年人姓名", "孩子姓名", "姓名"]),
        "child_birth": get_text(kv, ["孩子出生日期", "出生日期", "孩子年龄"]),
        "guardian": get_text(kv, ["监护人", "监护关系", "与孩子关系"]),
        "platform": get_text(kv, ["消费平台", "游戏或平台", "平台名称"]),
        "scene": get_text(kv, ["充值项目或场景", "充了什么", "消费场景"]),
        "detail": get_text(kv, ["充值经过", "发现经过", "事情经过"]),
        "is_minor_op": get_text(kv, ["是否为未成年人独立操作", "是否孩子自己操作",
                                 "操作人是谁"]),
        "amount": get_text(kv, ["充值总额", "充值金额", "总金额"]),
        "times": get_text(kv, ["充值笔数", "笔数", "共几笔"]),
        "first_date": get_text(kv, ["首次充值时间", "第一次充值", "首次充值日期"]),
        "period_days": get_text(kv, ["持续天数", "跨度天数", "多长时间"]),
        "duty_done": get_text(kv, ["已做的监护措施", "已尽的监护义务", "此前做过什么"]),
        "duty_missed": get_text(kv, ["未做或被指出的监护问题", "监护不足之处", "没做什么"]),
        "platform_said": get_text(kv, ["平台如何答复", "平台说法", "客服怎么说"]),
        "evidence_owned": get_text(kv, ["已有材料勾选", "材料勾选", "证据勾选"]),
        "evidence_desc": get_text(kv, ["材料清单", "已有材料", "证据清单"]),
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
    if not filled(f["child_birth"]):
        missing.append("孩子出生日期")
    if not filled(f["platform"]):
        missing.append("消费平台")
    if not filled(f["amount"]):
        missing.append("充值总额")

    calc = calc_amount(f)
    results = [
        ("未成年人主体与年龄认定", checks_subject(f, today)),
        ("消费场景与事实认定", checks_scene(f) + checks_consume(f)),
        ("充值金额与时间跨度", checks_amount(f, calc)),
        ("监护义务与责任抗辩", checks_duty(f)),
        ("平台抗辩与应对", checks_defense(f)),
        ("证据清单与缺口", checks_evidence(f)),
    ]
    steps = path_steps(f)
    todos = todo_list(f, results, calc)
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
