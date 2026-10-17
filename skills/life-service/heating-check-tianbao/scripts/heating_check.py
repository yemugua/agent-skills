#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""供暖不达标退费核算。

用法：
  python heating_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python heating_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失。
"""
import argparse
import json
import re
import sys
from datetime import date

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")

PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "（", "("]

YES_WORDS = ("有", "是", "已经", "已", "已缴", "已付", "已到场", "已报备",
             "已签字", "已签", "已检定", "达标", "true", "yes")
NO_WORDS = ("无", "否", "没有", "未", "未做", "未到场", "未报备", "不达标",
            "false", "no")


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
    # 数值型字段（如已缴热费=3600.0）也会被送进 filled，不能假设一定是字符串
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
    return norm(v) in YES_WORDS


def no(v):
    return norm(v) in NO_WORDS


def yes_flag(v):
    if yes(v):
        return True
    if no(v):
        return False
    return None


def parse_num(s):
    if not s:
        return None
    s = str(s).replace(",", "").replace("，", "").replace("℃", "")
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


def add_years(d, n):
    try:
        return date(d.year + n, d.month, d.day)
    except Exception:
        return date(d.year + n, 12, 31)


# ------------------------------------------------------------------ 供暖方式
CENTRAL_KEYS = ["集中供暖", "市政供热", "区域锅炉", "热源厂"]
SELF_KEYS = ["小区自供暖", "小区自供", "自供暖", "自供"]
BOILER_KEYS = ["壁挂炉", "燃气炉", "家用燃气"]
ELEC_KEYS = ["电采暖", "电暖", "电热膜", "热泵", "电地暖"]


def mode_type(mode):
    """返回 (方式名, 责任主体, 是否适用热费退费)。"""
    s = norm(mode)
    for k in CENTRAL_KEYS:
        if k in s:
            return ("集中供暖", "供热企业（热力公司）", True)
    for k in SELF_KEYS:
        if k in s:
            return ("小区自供暖", "小区产权单位或物业服务人（受托供热单位）", True)
    for k in BOILER_KEYS:
        if k in s:
            return ("燃气壁挂炉", "设备供应商、安装方与燃气供应方（用户自担运行）", False)
    for k in ELEC_KEYS:
        if k in s:
            return ("电采暖", "设备供应商、安装方与供电方（用户自担运行）", False)
    return ("需确认", "未定性出责任主体，请先确认供暖方式", None)


def checks_mode(f):
    out = []
    mname, msubject, refundable = mode_type(f["mode"])
    out.append(("供暖方式", mname, "定性为%s，责任主体指向%s。" % (mname, msubject)))
    if refundable is None:
        out.append(("责任主体", "待补正",
                    "供暖方式没定性，先分清集中供暖、小区自供暖还是自采暖，才知道该找谁、能不能退费。"))
        return out
    if refundable:
        out.append(("责任主体", "通过",
                    "该找的是供热企业（热力公司）：供热合同是用户与供热企业之间的，"
                    "供热企业是首问负责与索赔主体；物业通常只是代收代缴。"))
        subj = f["subject"]
        if filled(subj) and ("物业" in subj) and ("热力" not in subj) and ("供热" not in subj):
            out.append(("索赔对象", "有风险",
                        "当前索赔对象填的是%s，但物业一般不是供热合同相对方。"
                        "建议书面主送供热企业、抄送物业，并向供热企业索要工单号。" % subj))
        elif filled(subj):
            out.append(("索赔对象", "通过", "已填写索赔对象：%s。" % subj))
        else:
            out.append(("索赔对象", "待补正", "供热企业名称未填，书面主张需要有明确的相对方。"))
    else:
        out.append(("责任主体", "不通过",
                    "%s属自采暖，不存在'热费退费'这一路径，应走设备维修、安装保修、"
                    "供气/供电方与保险理赔。" % mname))
    insu = f["insulation"]
    if not filled(insu):
        out.append(("自担部分", "待补正",
                    "房屋保温与遮挡未填：长期空置、暖气被包死遮挡、顶楼边户单层玻璃，"
                    "都是供热企业用来减责的理由，需先自评。"))
    else:
        hit = [k for k in ("包死", "遮挡", "单层玻璃", "无保温", "顶楼", "边户", "空置") if k in insu]
        if hit:
            out.append(("自担部分", "有风险",
                        "存在%s等情形，供热企业可能据此主张减轻责任；这部分属你自担，"
                        "但不必然免除供热企业按标准供热的义务。" % "、".join(hit)))
        else:
            out.append(("自担部分", "通过", "房屋保温与遮挡未见明显自担因素。"))
    return out


# ------------------------------------------------------------------ 达标与测温
def temp_judge(f):
    std, avg = f["std"], f["avg_temp"]
    if std is not None and avg is not None:
        if avg >= std - 0.05:
            return ("达标", "实测平均室温 %s℃，已达到（不低于）当地标准 %s℃。" % (fmt_num(avg), fmt_num(std)), False)
        return ("不达标", "实测平均室温 %s℃，低于当地标准 %s℃ 约 %s℃。"
                % (fmt_num(avg), fmt_num(std), fmt_num(std - avg)), True)
    t = f["is_standard"]
    if filled(t) and no(t):
        return ("不达标", "已自述不达标（%s），但缺少实测温度数据佐证。" % t, True)
    if filled(t) and yes(t):
        return ("达标", "已自述达标（%s），但缺少实测温度数据佐证。" % t, False)
    return ("待补正", "当地室温标准与实测平均室温都缺，无法判定是否达标。", False)


MEASURE_ROWS = [
    ("测温是否在供热期内", "in_period",
     "测温必须落在当地供热条例规定的供热期内，供热期外不产生供热义务。", "不通过", "有风险"),
    ("是否提前报备测温", "reported",
     "多数地区要求测温前一定时间向供热单位报备；报备留痕是证明你按程序走的凭据。", "有风险", "有风险"),
    ("供热单位是否到场", "onsite",
     "须双方共同到场；对方拒不到场的也照测，并把'拒不到场'写入记录、录像留证。", "不通过", "有风险"),
    ("测温仪器是否检定合格", "instrument",
     "仪器应经计量检定合格且在有效期内；民用温湿度计只能作辅助证据。", "有风险", "有风险"),
    ("是否多点多时次取值", "multipoint",
     "应多点（居室中部等处）、多时次（早中晚）、连续多日，单点单次说服力弱。", "有风险", "有风险"),
    ("是否同时测室外温度", "outdoor_meas",
     "须同时测室外温度（或取当地气象台同期气温），只测室内记录不完整。", "有风险", "有风险"),
    ("是否有双方签字测温记录", "signed",
     "测温单应载明测点、时间、室内外温度、仪器编号与双方姓名签字或盖章工号。", "不通过", "有风险"),
]


def checks_measure(f):
    out = []
    _m, _s, refundable = mode_type(f["mode"])
    state, why, _bad = temp_judge(f)
    out.append(("是否达标", state, why))

    if refundable is False:
        out.append(("测温程序", "不适用", "自采暖方式的达标认定与热费退费不适用，本段六要件不参与判定。"))
        return out

    any_filled = any(filled(f[k]) for _n, k, _h, _b, _r in MEASURE_ROWS)
    if refundable is None and not any_filled:
        return out

    for name, key, hint, bad_state, risk_state in MEASURE_ROWS:
        v = f[key]
        if yes(v):
            out.append((name, "通过", hint))
        elif no(v) or "拒不到场" in (v or "") or "未到场" in (v or "") or "未报备" in (v or ""):
            out.append((name, bad_state, hint))
        elif not filled(v):
            out.append((name, "待补正", hint))
        elif key == "signed" and "单方" in v:
            out.append((name, "有风险", hint + "现有的是单方记录，效力弱于双方签字，建议补测一次并要对方签字。"))
        else:
            out.append((name, risk_state, hint))
    return out


# ------------------------------------------------------------------ 退费测算
def norm_ratio(v):
    """接受 30（30%）与 0.3（30%）两种写法。"""
    if v is None:
        return None
    r = v
    if r > 1:
        r = r / 100.0
    if r < 0:
        return None
    return min(1.0, r)


def calc_refund(f):
    res = {"适用": True, "口径": [], "算式": [], "下限": None, "上限": None,
           "待追回": None, "参考按日退还": None, "说明": ""}
    mname, _s, refundable = mode_type(f["mode"])
    if refundable is False:
        res["适用"] = False
        res["说明"] = "自采暖（%s）不适用热费退费，请走设备维修、保修与保险路径。" % mname
        return res

    fee = f["paid"]
    if fee is None or fee <= 0:
        res["说明"] = "已缴热费未填或为 0，无法测算退费金额。"
        return res

    items = []
    if f["has_rule"] is True:
        ratio_a = norm_ratio(f["ratio"])
        if ratio_a is not None:
            amt_a = fee * ratio_a
            items.append(("口径一·当地规则或合同约定（优先）", amt_a,
                          "已缴热费 %s 元 × 约定/规定退费比例 %s%% = %s 元"
                          % (fmt_num(fee), fmt_num(ratio_a * 100), fmt_num(amt_a))))
        else:
            res["说明"] = "已确认当地规则或合同有退费约定，但'约定退费比例'没填，口径一无法算。"

    std, avg = f["std"], f["avg_temp"]
    rho = None
    if std is not None and avg is not None and std > 0:
        gap = max(0.0, std - avg)
        rho = min(1.0, gap / std)
        if rho > 0:
            amt_b = fee * rho
            items.append(("口径二·无约定时按实际损失（室温缺口）", amt_b,
                          "室温缺口 %s℃（标准 %s℃ − 实测 %s℃），缺口比例 %s%%；"
                          "已缴热费 %s 元 × 缺口比例 %s%% = %s 元"
                          % (fmt_num(gap), fmt_num(std), fmt_num(avg), fmt_num(rho * 100),
                             fmt_num(fee), fmt_num(rho * 100), fmt_num(amt_b))))
        else:
            res["说明"] = "实测室温已达标准，无室温缺口，口径二退费为 0。"

    if items:
        res["口径"] = [x[0] for x in items]
        res["算式"] = [x[2] for x in items]
        res["下限"] = min(min(x[1] for x in items), fee)
        res["上限"] = min(max(x[1] for x in items), fee)
    if not res["说明"]:
        res["说明"] = "缺少可测算要素：需要'当地规则或约定的退费比例'和/或'标准室温 + 实测平均室温'才能算出金额。"

    days, ndays = f["days_total"], f["bad_days"]
    if days and days > 0 and ndays and ndays > 0:
        daily = fee / days
        r = rho if rho is not None else 1.0
        ref = min(daily * ndays * r, fee)
        res["参考按日退还"] = ref
        res["算式"].append("参考·按日退还：日热费 %s 元（已缴热费 %s ÷ 供热期 %s 天）× 不达标 %s 天 × 缺口比例 %s%% = %s 元（以已缴热费为上限）"
                           % (fmt_num(daily), fmt_num(fee), fmt_num(days),
                              fmt_num(ndays), fmt_num(r * 100), fmt_num(ref)))
    if f["settled_amt"] is not None and res["上限"] is not None:
        res["待追回"] = max(0.0, res["上限"] - f["settled_amt"])
    return res


def checks_refund(f, calc):
    out = []
    if not calc["适用"]:
        out.append(("热费退费", "不适用", calc["说明"]))
        return out
    if calc["下限"] is None:
        out.append(("退费测算", "待补正", calc["说明"]))
        return out
    out.append(("可退金额区间", "通过",
                "按'当地规则优先、无约定按实际损失'双轨口径，可退区间 ¥%s ~ ¥%s，"
                "上限以已缴热费 ¥%s 为限，共 %d 条口径。"
                % (fmt_num(calc["下限"]), fmt_num(calc["上限"]),
                   fmt_num(f["paid"] or 0), len(calc["口径"]))))
    if f["settled_amt"] is not None:
        if calc["待追回"] and calc["待追回"] > 0:
            out.append(("尚需追回", "有风险",
                        "已获退 ¥%s，按区间上沿尚需追回 ¥%s。" % (fmt_num(f["settled_amt"]), fmt_num(calc["待追回"]))))
        else:
            out.append(("尚需追回", "通过", "已获退金额不低于测算区间上沿。"))
    paid = f["paid"]
    if paid is not None and calc["上限"] is not None:
        if calc["上限"] >= paid - 1e-6:
            out.append(("退费上限", "通过", "测算区间上沿已达已缴热费 ¥%s 全额，可主张全额退还。" % fmt_num(paid)))
        else:
            out.append(("退费上限", "有风险",
                        "区间上沿 ¥%s 低于已缴热费 ¥%s，差额 ¥%s 需按当地规则或实际损失另行主张。"
                        % (fmt_num(calc["上限"]), fmt_num(paid), fmt_num(paid - calc["上限"]))))
    return out


# ------------------------------------------------------------------ 证据缺口
EVID_KEYS = [
    ("缴费凭证", ["缴费凭证", "发票", "支付凭证"]),
    ("供热合同与温度承诺", ["供热合同", "服务承诺", "温度承诺", "承诺书"]),
    ("测温记录", ["测温记录", "测温单", "测量记录"]),
    ("与供热企业沟通记录", ["沟通记录", "通话录音", "工单"]),
    ("室外温度证据", ["气象", "室外气温", "室外温度"]),
    ("房屋保温与遮挡证据", ["保温", "遮挡", "包死"]),
]


def checks_evidence(f):
    out = []
    ev = f["evidence"]
    if not filled(ev):
        out.append(("证据清单", "待补正",
                    "证据清单未填，无法核对缺口。必备材料：缴费凭证、供热合同与温度承诺、"
                    "测温记录、报备与沟通记录、室外温度证据、房屋保温遮挡证据。"))
        return out
    for name, keys in EVID_KEYS:
        if any(k in ev for k in keys):
            out.append((name, "通过", "已列入证据清单。"))
        else:
            out.append((name, "待补正", "证据清单中未见%s，需补。" % name))
    return out


# ------------------------------------------------------------------ 路径与时限
def path_steps(f):
    mname, _s, refundable = mode_type(f["mode"])
    if refundable is False:
        return [
            ("第 1 步", "%s：先定性是设备问题还是供应问题（不热、不升温、报错），别先谈钱。" % mname),
            ("第 2 步", "查保修卡与安装合同，向设备供应商或安装方主张维修/更换；属燃气的同步向燃气公司确认供气压力"),
            ("第 3 步", "属商品质量或安装质量的，向 12315 消协投诉；造成财产损失的走保险理赔"),
            ("第 4 步", "保留维修单据、检测报告与现场照片，协商不成可提起民事诉讼（诉讼时效 3 年）"),
        ]
    return [
        ("第 1 步", "向供热企业（热力公司）书面反映：标准温度、实测温度、要求按规范测温并退费，索要工单号"),
        ("第 2 步", "书面主送供热企业、抄送物业（物业代收代缴）各发一份，避免被踢皮球，并明确给出答复期限"),
        ("第 3 步", "拨打 12345 要求派单给住建（城管/公用事业）供热主管部门，请求督办并出具处理意见"),
        ("第 4 步", "公示承诺不实、价格公示问题的，向 12315 与市场监管反映；拒不履行的可起诉或按合同申请仲裁"),
        ("第 5 步", "同一小区同症状联名提交，举证与谈判效果显著更好；供热期结束前完成一次正式主张"),
    ]


LIMITS = [
    ("供热期内书面主张", "供热期内就应提出，别拖到供热期结束"),
    ("供热期结束申请退费结算", "按当地规定时限办理，逾期可能被拒"),
    ("民事诉讼时效", "3 年，自知道或应当知道权利被侵害之日起算"),
    ("证据固定", "越早越好，测温记录与监控很快无法补"),
]


def checks_time(f, today):
    out = []
    d = parse_date(f["claim_date"])
    if d:
        deadline = add_years(d, 3)
        left = (deadline - today).days
        out.append(("诉讼时效倒计时", "有风险" if left < 0 else "通过",
                    "自 %s 主张起算，3 年到期日 %s，%s。"
                    % (d.isoformat(), deadline.isoformat(),
                       ("已过 %d 天" % -left) if left < 0 else ("还剩 %d 天" % left))))
    else:
        out.append(("诉讼时效倒计时", "待补正",
                    "未填首次/上次主张日期，无法倒计时；民事诉讼时效 3 年，别跨供热期拖。"))
    return out


# ------------------------------------------------------------------ 待办
def build_todo(f, results):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    if mode_type(f["mode"])[2] is not False:
        if not yes(f["reported"]):
            extra.append(("书面报备", "补发一条正式书面测温申请（短信/APP 工单），截图留存"))
        if not yes(f["onsite"]):
            extra.append(("补测", "书面要求供热单位按六要件重测：双方到场、检定仪器、多点多时次、同时测室外"))
        if not yes(f["signed"]):
            extra.append(("要签字", "测温单要求对方签字或盖章并写工号；不签的当场录像说明拒签"))
        if not filled(f["evidence"]):
            extra.append(("补证据", "补齐缴费凭证、供热合同与温度承诺、测温记录、报备与沟通记录、室外气温、保温遮挡照片"))
        extra.append(("查当地规则", "在当地住建/城管（供热主管）官网或 12345 查清本地室温标准与退费比例表"))
    else:
        extra.append(("走维修", "按设备保修与安装合同主张维修/更换，属燃气的同步找燃气公司"))
    extra.append(("发函", "给供热企业（或设备方）发书面主张函，索要工单号与书面答复，抄送物业"))
    seen = set()
    allt = []
    for n, s in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        allt.append((n, s))
    return allt


# ------------------------------------------------------------------ 报告
def rows_of(results, prefix):
    for t, rows in results:
        if t.startswith(prefix):
            return rows
    return []


def emit_table(L, rows, title=""):
    # 段标题必须在 emit_table 内部输出，否则某段没行时整段会从报告里消失
    if title:
        L.append("## %s" % title)
        L.append("")
    if not rows:
        L.append("暂无可核查项（未填不按通过处理）。")
        L.append("")
        return
    L.append("| 核查项 | 判定 | 说明 |")
    L.append("|---|---|---|")
    for name, state, msg in rows:
        L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
    L.append("")


def render(f, results, calc, steps, todos, today):
    L = []
    L.append("# 供暖不达标核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 所在城市：%s" % (f["city"] or "未填"))
    L.append("- 供暖方式：%s" % mode_type(f["mode"])[0])
    L.append("")

    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    pend = [r for _t, rows in results for r in rows if r[1] == "待补正"]

    L.append("## 一、结论摘要")
    L.append("")
    if calc["上限"] is not None:
        L.append("**判定：存在不达标情形，可主张退费，可退区间 ¥%s ~ ¥%s。**"
                 % (fmt_num(calc["下限"]), fmt_num(calc["上限"])))
    elif bad:
        L.append("**判定：存在明确违规点，可主张**。")
    elif risk:
        L.append("**判定：存在风险点，需补正后主张**。")
    else:
        L.append("**判定：未发现明显违规点；若有争议，按第六段处理阶梯推进**。")
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(pend))
    L.append("")
    for name, _s, msg in bad[:4]:
        L.append("- **%s**：%s" % (name, msg.replace("**", "")))
    for name, _s, msg in risk[:3]:
        L.append("- %s：%s" % (name, msg.replace("**", "")))
    L.append("")

    emit_table(L, rows_of(results, "二、"), "二、供热方式与责任主体")
    emit_table(L, rows_of(results, "三、"), "三、是否达标与测温程序")

    if not calc["适用"]:
        L.append("- %s" % calc["说明"])
        L.append("")
    elif calc["下限"] is None:
        L.append("- 当前无法测算：%s" % calc["说明"])
        L.append("")
    else:
        L.append("**测算口径：当地规则优先、无约定时按实际损失（室温缺口）双轨。**"
                 "已缴热费 ¥%s，标准室温 %s℃，实测平均室温 %s℃，供热期 %s 天。"
                 % (fmt_num(f["paid"]), fmt_num(f["std"]), fmt_num(f["avg_temp"]),
                    fmt_num(f["days_total"])))
        L.append("")
        for cal in calc["口径"]:
            L.append("- 口径：**%s**" % cal)
        L.append("")
        L.append("算式：")
        L.append("")
        for ex in calc["算式"]:
            L.append("- `%s`" % ex.replace("|", " "))
        L.append("")
        L.append("- **可退区间：¥%s ~ ¥%s**（以已缴热费 ¥%s 为上限）。"
                 % (fmt_num(calc["下限"]), fmt_num(calc["上限"]), fmt_num(f["paid"] or 0)))
        if calc["待追回"] is not None:
            L.append("- **尚需追回：¥%s**（已获退 ¥%s）。"
                     % (fmt_num(calc["待追回"]), fmt_num(f["settled_amt"] or 0)))
        L.append("")
        L.append("- 各地退费比例表不同：当地规则或合同已有明确比例的按口径一主张；"
                 "查不到规则的按口径二（室温缺口对应的实际损失）兜底。")
        L.append("")
    emit_table(L, rows_of(results, "四、"), "四、退费测算（算式与区间）")

    emit_table(L, rows_of(results, "五、"), "五、证据缺口")

    L.append("## 六、处理阶梯")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")

    L.append("## 七、时限清单")
    L.append("")
    L.append("| 事项 | 期限 |")
    L.append("|---|---|")
    for k, v in LIMITS:
        L.append("| %s | %s |" % (k, v))
    L.append("")
    emit_table(L, rows_of(results, "七、"))

    L.append("## 八、待办补正动作")
    L.append("")
    if not todos:
        L.append("当前未发现必须补正的事项。")
    else:
        L.append("| 动作 | 状态 |")
        L.append("|---|---|")
        for n, s in todos:
            L.append("| %s | %s |" % (n, s))
    L.append("")

    L.append("## 九、边界与纪律")
    L.append("")
    L.append("- 本结果依通用规则整理，**不替代律师意见**。")
    L.append("- 室温标准、退费比例、测温程序的地方差异极大，**一律以当地供热条例与供热主管部门口径为准**。")
    L.append("- 供热企业是首问负责与索赔主体，物业通常只是代收代缴，别在物业处耗时间。")
    L.append("- 不预测行政处罚、复议与诉讼结果；金额以供热单位核定、主管部门认定或司法机关认定为准。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("")
    L.append("- 本结果依通用规则整理，不替代专业意见，最终以主管部门/司法机关认定为准。")
    return "\n".join(L) + "\n"


def to_json(f, results, calc, todos, today):
    return {
        "核查日期": today.isoformat(),
        "供暖方式": mode_type(f["mode"])[0],
        "责任主体": mode_type(f["mode"])[1],
        "可退区间": {"下限": calc["下限"], "上限": calc["上限"]},
        "退费算式": calc["算式"],
        "结论": {
            "不通过": [r[0] for _t, rows in results for r in rows if r[1] == "不通过"],
            "有风险": [r[0] for _t, rows in results for r in rows if r[1] == "有风险"],
            "待补正": [r[0] for _t, rows in results for r in rows if r[1] == "待补正"],
        },
        "待办": [{"动作": n, "状态": s} for n, s in todos],
    }


def collect_fields(kv):
    f = {
        "city": get_text(kv, ["所在城市", "城市"]),
        "mode": get_text(kv, ["供暖方式", "供热方式", "采暖方式"]),
        "subject": get_text(kv, ["供热企业", "供热企业名称", "热力公司"]),
        "insulation": get_text(kv, ["房屋保温与遮挡", "房屋保温"]),
        "paid": parse_num(get_text(kv, ["已缴热费金额", "已缴热费", "实缴热费金额"])),
        "days_total": parse_num(get_text(kv, ["供热期天数"])),
        "std": parse_num(get_text(kv, ["当地室温标准", "室温标准", "标准室温"])),
        "avg_temp": parse_num(get_text(kv, ["实测平均室温", "平均室温", "实际平均室温"])),
        "is_standard": get_text(kv, ["是否达标"]),
        "bad_days": parse_num(get_text(kv, ["不达标天数"])),
        "outdoor": parse_num(get_text(kv, ["室外温度", "室外气温"])),
        "in_period": get_text(kv, ["测温是否在供热期内", "是否在供热期内"]),
        "reported": get_text(kv, ["是否提前向供热企业报备测温", "是否提前报备测温", "提前报备"]),
        "onsite": get_text(kv, ["供热单位是否到场", "供热单位到场"]),
        "instrument": get_text(kv, ["测温仪器是否检定合格", "仪器是否检定合格"]),
        "multipoint": get_text(kv, ["是否多点多时次取值", "多点多时次"]),
        "outdoor_meas": get_text(kv, ["是否同时测室外温度", "同时测室外温度"]),
        "signed": get_text(kv, ["是否有双方签字的测温记录", "双方签字测温记录", "测温记录是否双方签字"]),
        "has_rule": yes_flag(get_text(kv, ["当地或合同是否有退费比例规定", "是否有退费比例规定"])),
        "ratio": parse_num(get_text(kv, ["约定退费比例", "退费比例"])),
        "settled": get_text(kv, ["是否已获退费", "已获退费"]),
        "settled_amt": parse_num(get_text(kv, ["已退金额"])),
        "claim_date": get_text(kv, ["首次主张日期", "上次主张日期", "主张日期"]),
        "evidence": get_text(kv, ["证据清单", "已有证据"]),
    }
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = read_text(args.input)
    kv = build_kv(text)
    f = collect_fields(kv)
    today = base_date(args.base)

    std, avg = f["std"], f["avg_temp"]
    if std is not None and avg is not None:
        f["bad_temp"] = avg < std - 0.05
    else:
        f["bad_temp"] = no(f["is_standard"])

    missing = []
    if not filled(f["mode"]):
        missing.append("供暖方式")
    if not filled(f["paid"]):
        missing.append("已缴热费金额")

    calc = calc_refund(f)
    results = [
        ("二、供热方式与责任主体", checks_mode(f)),
        ("三、是否达标与测温程序", checks_measure(f)),
        ("四、退费测算（算式与区间）", checks_refund(f, calc)),
        ("五、证据缺口", checks_evidence(f)),
        ("七、时限清单", checks_time(f, today)),
    ]
    steps = path_steps(f)
    todos = build_todo(f, results)

    if args.json:
        print(json.dumps(to_json(f, results, calc, todos, today), ensure_ascii=False, indent=2))
        return 0

    rep = render(f, results, calc, steps, todos, today)
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
