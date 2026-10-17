#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""房屋漏水责任核查。

用法：
  python water_leak_check.py 采集表.md --base 2026-10-05 --out 核查报告.md
  python water_leak_check.py 采集表.md --json
退出码：0 正常；2 关键信息缺失（给提示串，不崩、不抛异常）。
"""
import argparse
import json
import re
import sys
from datetime import date

UNFILLED_MARK = re.compile(r"[/／]")
DATE_RE = re.compile(r"(20\d{2})[-年\.](\d{1,2})[-月\.](\d{1,2})")
PLACEHOLDER_WORDS = ["待填", "请填", "例如", "示例", "如：", "(", "（"]

# ------------------------------------------------------------------ 通用工具
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
    """最长别名优先匹配；空值不参与匹配。"""
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if norm(k) == na and filled(v):
                return v.strip()
    for a in sorted(aliases, key=len, reverse=True):
        na = norm(a)
        for k, v in kv.items():
            if na in norm(k) and filled(v):
                return v.strip()
    return ""


def filled(v):
    v = ("" if v is None else str(v)).strip()
    if not v:
        return False
    if UNFILLED_MARK.search(v):
        return False
    for w in PLACEHOLDER_WORDS:
        if v.startswith(w):
            return False
    return True


def core(v):
    n = norm(v)
    n = re.sub(r"[（(].*?[)）]", "", n)
    return n


def yes(v):
    n = core(v)
    if n in ("有", "是", "已经", "已", "已完成", "true", "yes"):
        return True
    return bool(re.match(r"^(是|有|已经)", n))


def no(v):
    n = core(v)
    if n in ("无", "否", "没有", "未", "未做", "false", "no"):
        return True
    return bool(re.match(r"^(否|无|没|未)", n))


def unknown(v):
    n = norm(v)
    return (not filled(v)) or n in ("不清楚", "不确定", "不知道", "待确认", "未知")


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


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except Exception:
        return d.replace(year=d.year + n, day=1)


# ------------------------------------------------------------------ 保修期
WATER_PARTS = ("屋面", "屋顶", "外墙", "卫生间", "浴室", "厨房", "防水", "地下室", "阳台", "窗边")
PIPE_PARTS = ("给排水", "水管", "管道", "下水管", "暖气管", "电路", "电气", "排污", "立管", "主管道")
FIT_PARTS = ("装修", "地板", "瓷砖", "吊顶", "墙面", "腻子", "涂料", "橱柜")


def warranty_years(part=""):
    """按部位给最低保修年限（《建设工程质量管理条例》相关规定的最低保修期）。"""
    if any(k in part for k in WATER_PARTS):
        return 5, "屋面防水工程、有防水要求的卫生间/房间和外墙面防渗漏"
    if any(k in part for k in PIPE_PARTS):
        return 2, "电气管线、给排水管道、设备安装"
    if any(k in part for k in FIT_PARTS):
        return 2, "装修工程"
    return None, "地基基础与主体结构按设计文件规定的合理使用年限；其他部位需按施工合同与相关规定确定"


def warranty_check(f, today):
    """返回 (年限, 到期日, 状态, 说明)。"""
    part = f["part"] or ""
    years, what = warranty_years(part)
    d = parse_date(f["completion_date"])
    if d is None:
        return None, None, "待补正", ("未填房屋竣工验收合格/交付日期，无法计算保修期。"
                               "建设工程质量保修期自**竣工验收合格之日**起算，请补填该日期。")
    if years is None:
        return None, None, "待补正", (
            "漏水部位为「%s」，%s，请先明确部位后重算保修期。"
            "（保修期自竣工验收合格之日 %s 起算）" % (part or "未填", what, d.isoformat()))
    dl = add_years(d, years)
    left = (dl - today).days
    state = "有风险" if left < 0 else "通过"
    msg = ("%s的最低保修期为 **%d 年**（自竣工验收合格之日 %s 起算，至 %s）。"
           % (what, years, d.isoformat(), dl.isoformat()))
    if left < 0:
        msg += ("已超过 %d 天，保修期已届满——一般不能再向开发商主张保修责任；"
                "但能证明**原始施工缺陷**仍在的，仍可依法主张。" % -left)
    else:
        msg += ("仍在保修期内（还剩 %d 天），属施工质量/防水缺陷导致的，"
                "应由**开发商**承担保修责任。" % left)
    return years, dl, state, msg


# ------------------------------------------------------------------ 责任归属
PUBLIC_KW = ("公共管道", "公共部位", "屋面", "外墙", "下水立管", "立管", "主管道",
             "公共下水", "屋顶", "管道井")
UPSTAIRS_KW = ("装修", "改造", "水龙头", "地漏", "堵塞", "防水层破坏", "忘关",
               "楼上", "住户", "擅自", "开水")


def responsibility(f, years_left_txt):
    rows = []
    part = f["part"] or ""
    up = f["upstairs_reason"] or ""
    pub = yes(f["public_part"])

    if not filled(part):
        rows.append(("漏水部位", "待补正",
                     "未填漏水部位/位置。部位决定适用哪种保修年限、也决定责任分支，必须先定。"))
    else:
        hit_up = [k for k in UPSTAIRS_KW if k in up and k not in ("楼上", "住户")]
        is_public = pub or any(k in part for k in PUBLIC_KW)
        if up and hit_up:
            rows.append(("责任归属", "不通过",
                         "楼上住户存在可归责行为（%s），属楼上住户原因，"
                         "由楼上业主承担相邻关系/侵权责任；先固定其行为的证据，再主张赔偿。"
                         % "、".join(hit_up[:5])))
        elif is_public:
            rows.append(("责任归属", "有风险",
                         "漏水点位于公共部位（公共管道、屋面、外墙、下水立管等），"
                         "属物业服务人或业主共有部分的维修责任，可依法申请使用"
                         "**住宅专项维修资金**（需按程序业主表决）；物业怠于履职的，"
                         "可主张其承担相应责任。"))
        elif years_left_txt == "保修期内":
            rows.append(("责任归属", "不通过",
                         "仍在保修期内且不属于楼上住户原因、也不在公共部位，"
                         "属施工质量或防水缺陷，由**开发商**承担保修责任，"
                         "可书面催告其履行保修义务。"))
        elif years_left_txt == "保修期外":
            rows.append(("责任归属", "有风险",
                         "已过保修期且非楼上住户行为、也非公共部位，"
                         "需先查清水源（如相邻方使用不当、自然渗水、原始施工缺陷），"
                         "现状不明的应先申请**渗漏原因鉴定**再定比例。"))
        else:
            rows.append(("责任归属", "待补正",
                         "尚不能确定责任分支（可能是楼上住户、也可能是开发商保修或公共部位）。"
                         "请填楼上住户原因、漏水点是否属公共部位、以及竣工日期后重跑。"))

    if up and not any(k in up for k in UPSTAIRS_KW):
        rows.append(("楼上住户原因", "待补正",
                     "填了楼上住户原因但读不出具体行为（常见：装修、管道改造、忘关水龙头、"
                     "地漏堵塞、破坏防水层），请写明其一。"))
    elif not filled(up):
        rows.append(("楼上住户原因", "待补正",
                     "未填楼上住户是否存在可归责行为。这是三分支里最常见的一条，"
                     "填了才能锁定楼上业主责任。"))
    else:
        rows.append(("楼上住户原因", "通过",
                     "楼上住户原因已查明（%s），可向其主张停止侵害、恢复原状与赔偿损失。"
                     % up[:24]))

    if filled(part) and any(k in part for k in PUBLIC_KW):
        rows.append(("公共部位判定", "通过",
                     "漏水点「%s」属于公共部位。公共部分的维修属物业服务人/业主共有部分的责任；"
                     "金额较大的可启动住宅专项维修资金（需业主表决程序）。" % part))
    elif filled(f["public_part"]):
        rows.append(("公共部位判定", "通过",
                     "漏水点已认定为非公共部位，按楼上/开发商分支处理。"))
    else:
        rows.append(("公共部位判定", "待补正",
                     "漏水点是否属公共部位未填。公共管道、屋面、外墙、下水立管属公共部位，"
                     "走维修资金；户内管线走楼上或开发商。"))
    return rows


# ------------------------------------------------------------------ 取证与鉴定
def checks_evidence(f):
    rows = []
    rep = f["policy_reported"]
    if yes(rep):
        rows.append(("物业报修", "通过",
                     "已向物业报修，这是**最关键的取证动作**——物业的到场记录与派单记录能证明"
                     "漏水客观存在、发生时间与已通知义务人，后续主张都靠它。"))
        onsite = yes(f["policy_on_site"])
        if onsite:
            rows.append(("物业到场记录", "通过",
                         "物业已到场并留下书面记录，证明漏水事实与原因的关键证据链完整。"))
        elif filled(f["policy_on_site"]):
            rows.append(("物业到场记录", "待补正",
                         "物业到场情况填了但未认定，请确认是否有派单、工单、照片或签到记录。"))
        else:
            rows.append(("物业到场记录", "有风险",
                         "已报修但物业是否到场无书面记录。**请立即要求物业出具书面记录"
                         "（工单号、到场时间、现场照片、处理意见）并签字/盖章留存。**"))
    elif no(rep):
        rows.append(("物业报修", "不通过",
                     "未向物业报修。这既是取证缺口，也可能被拿来主张你未及时止损、"
                     "扩大损失部分自担。**现在马上书面报修并索要工单号**。"))
    else:
        rows.append(("物业报修", "待补正",
                     "是否向物业报修未填。物业报修记录是漏水侵权案里最基础的证据，务必补上。"))

    notified = yes(f["notified"])
    if notified:
        rows.append(("书面通知", "通过",
                     "已书面通知物业与楼上住户（通知内容：%s）。通知是主张'及时止损'与"
                     "'对方知情不纠'的基础。" % (f["notify_to"] or "未说明对象")))
    elif no(f["notified"]):
        rows.append(("书面通知", "有风险",
                     "尚未书面通知。请补发书面通知（微信/短信/EMS 均可），写明漏水时间、"
                     "部位、已造成的损失、要求对方在几日内到场查勘并修复。"))
    else:
        rows.append(("书面通知", "待补正", "是否已书面通知物业与楼上住户未填。"))

    appr = yes(f["appraised"])
    clear = yes(f["cause_clear"])
    if appr:
        rows.append(("渗漏原因鉴定", "通过",
                     "已做渗漏原因鉴定（鉴定报告是划分责任比例的核心证据）。"
                     "鉴定费一般先由申请方垫付，最终由责任方按责任比例负担。"))
    elif clear:
        rows.append(("渗漏原因鉴定", "通过",
                     "漏水原因已明确（%s），可不带鉴定直接主张；"
                     "但对方若否认，鉴定报告仍是最省力的说服材料。" % (f["cause_desc"] or "已查明")))
    else:
        rows.append(("渗漏原因鉴定", "有风险",
                     "漏水原因未查明且未做鉴定。混合原因（楼上装修＋管道老化＋公共部位）"
                     "必须靠鉴定划分比例；**先评估是否值得鉴定**——鉴定费一般先由申请方垫付、"
                     "最终由责任方按责任比例负担，若损失远小于鉴定费则先谈判。"))

    if yes(f["repair_done"]):
        rows.append(("修复情况", "通过", "已修复，请保留维修记录与发票，作为修复费主张的凭证。"))
    else:
        rows.append(("修复情况", "待补正",
                     "是否已修复未填。修复前务必先拍照、留报价、再施工，否则修复费难以主张。"))

    if yes(f["scope_expanded"]):
        rows.append(("维修范围", "不通过",
                     "自行扩大了维修范围。**扩大部分的主张通常不被支持**——只修漏水及直接受损部位，"
                     "顺手做的翻新、换主材、美化项目不要算进索赔。"))
    elif no(f["scope_expanded"]):
        rows.append(("维修范围", "通过", "维修范围限于漏水及直接受损部位，符合可索赔范围。"))
    else:
        rows.append(("维修范围", "待补正", "是否自行扩大维修范围未填。扩大部分一般不被支持。"))
    return rows


# ------------------------------------------------------------------ 损失核算
def checks_loss(f):
    rows = []
    repair = f["repair_cost"] or 0.0
    prop = f["property_loss"] or 0.0
    other = f["other_cost"] or 0.0
    appr = f["appraisal_fee"] or 0.0
    rent = f["rent_loss"] or 0.0

    rows.append(("直接损失合计", "通过",
                 "修复费 %s 元＋财产损失 %s 元＋其他 %s 元＝ **%s 元**。"
                 % (fmt_num(repair), fmt_num(prop), fmt_num(other),
                    fmt_num(repair + prop + other))))
    rows.append(("可主张赔偿范围", "通过",
                 "按侵权/相邻关系赔偿规则，通常可主张：**修复费、财产损失、必要的鉴定费**，"
                 "合计口径 %s 元（含鉴定费 %s 元）。"
                 % (fmt_num(repair + prop + other + appr), fmt_num(appr))))

    if rent > 0:
        rows.append(("租金与住宿损失", "有风险",
                     "已列租金/住宿损失 %s 元。这类损失**一般难以获得全额支持**，"
                     "需证明其必要性与实际发生（租赁合同、付款凭证、住宿发票、时长对应）"
                     "且属于漏水必然导致的直接损失，别把它当必得项。" % fmt_num(rent)))
    else:
        rows.append(("租金与住宿损失", "待补正",
                     "未填租金/住宿损失。若因漏水临时租房或住宿，留下合同、付款与发票；"
                     "但这类损失一般难全额支持，要有心理预期。"))

    if appr > 0 and (repair + prop) > 0 and appr > (repair + prop) * 0.5:
        rows.append(("鉴定费占比", "有风险",
                     "鉴定费 %s 元已超过直接损失的一半（%s 元）。性价比偏低，"
                     "建议先做无修复的止损与书面交涉，再决定是否鉴定。"
                     % (fmt_num(appr), fmt_num(repair + prop))))

    if not filled(f["repair_cost"]):
        rows.append(("修复费用", "待补正",
                     "未填修复费用/修复报价。修复前先做**多家书面报价（至少两家）**，"
                     "并保留施工记录与发票。"))
    else:
        rows.append(("修复费用", "通过", "已列修复费用 %s 元，作为修复费主张的基础。" % fmt_num(repair)))

    if not filled(f["property_loss"]):
        rows.append(("财产损失", "待补正",
                     "未填财产损失（家具、电器、装修、物品）。受损物品要拍照、列清单、"
                     "附购买凭证或折旧估算。"))
    else:
        rows.append(("财产损失", "通过", "已列财产损失 %s 元，附受损照片与购买凭证。" % fmt_num(prop)))
    return rows


# ------------------------------------------------------------------ 特殊情形
def checks_special(f):
    rows = []
    if yes(f["fund_possible"]):
        if yes(f["vote_done"]):
            rows.append(("住宅专项维修资金", "通过",
                         "已按程序完成业主表决并使用维修资金。维修资金的动用属业主共同决定事项，"
                         "物业应公示表决与使用情况。"))
        elif no(f["vote_done"]):
            rows.append(("住宅专项维修资金", "有风险",
                         "公共部位可动用住宅专项维修资金，但需经**业主表决程序**；物业未启动的，"
                         "可提请业主委员会或向住建（房管）主管部门、街道反映。"))
        else:
            rows.append(("住宅专项维修资金", "待补正", "维修资金的表决情况未填。"))
    elif filled(f["fund_possible"]):
        rows.append(("住宅专项维修资金", "通过", "该情形不适用住宅专项维修资金，走责任方赔偿路径。"))
    else:
        rows.append(("住宅专项维修资金", "待补正",
                     "公共部位的维修是否可动用住宅专项维修资金未填（需业主表决程序）。"))

    if yes(f["rental"]):
        tn = yes(f["tenant_notified"])
        if tn:
            rows.append(("承租人通知义务", "通过",
                         "已及时通知房东（%s）并留痕。承租人应及时通知是减损义务，"
                         "及时通知可避免扩大损失部分自担。" % (f["notify_to"] or "已通知")))
        else:
            rows.append(("承租人通知义务", "不通过",
                         "租房场景下承租人**应及时通知房东并留痕**；未及时通知导致损失扩大的，"
                         "扩大部分可能由承租人自担。请立即书面/微信通知房东并保留记录，"
                         "同时报物业查勘。"))
        rows.append(("出租人维修义务", "有风险",
                     "租房场景的维修义务看租赁合同与当地规定：通常出租人负有出租房屋及附属设施的"
                     "维修义务（当事人另有约定的从约定），但承租人因使用不当造成损坏的由承租人承担。"
                     "先固定'是自然渗漏还是使用不当'。"))
    elif filled(f["rental"]):
        rows.append(("房屋性质", "通过", "非承租房屋，按业主/相邻关系路径处理。"))
    else:
        rows.append(("房屋性质", "待补正", "是否属承租房屋未填（影响维修义务与通知义务的主体）。"))

    if yes(f["fee_owed"]):
        rows.append(("以拒交物业费对抗", "不通过",
                     "不能用水费/物业费抵扣或拒交来对冲漏水赔偿——**这是两个独立的法律关系**。"
                     "拒交物业费的，物业可另行主张，甚至可能成为你违约的把柄。要赔偿就单独谈、单独诉。"))
    elif filled(f["fee_owed"]):
        rows.append(("以拒交物业费对抗", "通过", "未以拒交物业费的方式主张权利，处理正确。"))
    else:
        rows.append(("以拒交物业费对抗", "待补正",
                     "是否以拒交物业费/抵扣来主张权利未填。漏水赔偿与物业费是两个法律关系，"
                     "不能混同处理。"))
    return rows


# ------------------------------------------------------------------ 路径
def path_order(f):
    steps = []
    if yes(f["rental"]):
        steps = [
            ("第 1 步", "立即止损并留痕：关闭水阀/电源、拍照拍视频（带时间水印），"
                        "书面或微信通知**房东与物业**，要求到场查勘并出具记录，索要工单号"),
            ("第 2 步", "向房东主张维修义务并索赔；先做无修复的止损与报价，"
                        "不要自行大规模拆改，扩大部分自担"),
            ("第 3 步", "向**社区/居委会**或人民调解委员会申请调解；涉及公共部位的同步要求物业启动维修资金程序"),
            ("第 4 步", "向住建（房管）主管部门、**12345** 反映物业不履职；涉及开发商保修的向住建部门投诉"),
            ("第 5 步", "协商不成的，就赔偿提起民事诉讼（相邻关系/侵权责任，诉讼时效 3 年）；"
                        "必要时诉前保全或申请先予执行"),
        ]
    else:
        steps = [
            ("第 1 步", "立即止损：关水阀、断相关电源、挡水擦干，防止损失扩大"),
            ("第 2 步", "固定证据：拍漏水点与发展过程（带时间）、受损财产清单与照片、"
                        "**向物业报修并索要到场记录/工单号**，同时书面通知楼上住户"),
            ("第 3 步", "书面要求责任方（开发商／楼上业主／物业）修复并赔偿，"
                        "写明金额构成与期限，索要回执；楼上推诿的可请求社区/居委会调解"),
            ("第 4 步", "向**社区/居委会**、人民调解委员会申请调解；公共部位可请物业启动"
                        "住宅专项维修资金程序（业主表决）"),
            ("第 5 步", "向**住建（房管）主管部门**、**12345** 反映物业怠于履职；"
                        "保修期内的同时向住建部门投诉开发商不履行保修义务"),
            ("第 6 步", "调解不成的，按相邻关系/侵权主张**停止侵害、排除妨碍、恢复原状、赔偿损失**"
                        "起诉；必要时申请诉前保全或先予执行（诉讼时效 3 年）"),
        ]
    return steps


def todo_list(f, results):
    todos = []
    for _t, rows in results:
        for name, state, _msg in rows:
            if state in ("不通过", "有风险", "待补正"):
                todos.append((name, state))
    extra = []
    extra.append(("立即止损", "关水阀、断电源、挡水擦干，别让损失继续扩大"))
    extra.append(("固定带时间的影像", "漏水点、渗水痕迹、受损财产逐张拍，中途录一段连续视频"))
    extra.append(("物业报修养工单", "书面报修并索取工单号、到场记录与现场照片"))
    if not yes(f["notified"]):
        extra.append(("书面通知楼上", "微信/短信通知楼上住户写明时间、部位、要求到场合查"))
    if not yes(f["appraised"]):
        extra.append(("评估是否鉴定", "先算损失与鉴定费的比例，再决定要不要做渗漏原因鉴定"))
    if yes(f["rental"]):
        extra.append(("通知房东", "第一时间书面/微信通知房东并留痕，避免扩大损失自担"))
    if yes(f["fee_owed"]) or filled(f["fee_owed"]):
        extra.append(("别拿物业费对冲", "漏水赔偿与物业费是两个法律关系，分开谈、分开诉"))
    extra.append(("修复前留报价", "至少两家书面报价，先拍照后施工，保留发票与维修记录"))
    seen = set()
    out = []
    for n, st in todos + extra:
        if n in seen:
            continue
        seen.add(n)
        out.append((n, st))
    return out


# ------------------------------------------------------------------ 报告
def render(f, results, steps, todos, today, deadline_txt, branch):
    L = []
    L.append("# 房屋漏水责任核查报告")
    L.append("")
    L.append("- 核查日期：%s" % today.isoformat())
    L.append("- 漏水部位：%s" % (f["part"] or "未填"))
    L.append("- 房屋性质：%s" % (f["scene"] or "未填"))
    L.append("")
    bad = [r for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r for _t, rows in results for r in rows if r[1] == "待补正"]
    L.append("## 一、结论摘要")
    L.append("")
    if bad:
        L.append("**判定：责任相对明确，存在必须补正的取证缺口，可主张赔偿**。")
    elif risk:
        L.append("**判定：存在风险点，需补正后主张**。")
    else:
        L.append("**判定：未发现明显风险点；若协商不成，按第六段路径推进**。")
    L.append("")
    L.append("| 项 | 数量 |")
    L.append("|---|---|")
    L.append("| 不通过 | %d |" % len(bad))
    L.append("| 有风险 | %d |" % len(risk))
    L.append("| 待补正 | %d |" % len(todo))
    L.append("")
    L.append("- **责任归属初判：%s**。" % branch)
    L.append("")
    for name, _st, msg in bad[:6]:
        L.append("- **%s**：%s" % (name, msg.replace("**", "")))
    for name, _st, msg in risk[:6]:
        L.append("- %s：%s" % (name, msg.replace("**", "")))
    L.append("")

    secs = [("二、责任归属判定", results[0][1]),
            ("三、保修期与开发商责任", results[1][1]),
            ("四、取证与鉴定", results[2][1]),
            ("五、损失核算与赔偿范围", results[3][1])]
    for title, rows in secs:
        if not rows:
            continue
        L.append("## %s" % title)
        L.append("")
        L.append("| 核查项 | 判定 | 说明 |")
        L.append("|---|---|---|")
        for name, state, msg in rows:
            L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
        L.append("")

    L.append("## 六、交涉路径与时效")
    L.append("")
    for step, txt in steps:
        L.append("- **%s**：%s" % (step, txt))
    L.append("")
    L.append("| 事项 | 期限 |")
    L.append("|---|---|")
    L.append("| 时效倒计时 | %s |" % deadline_txt)
    L.append("| 民事诉讼时效 | 3 年，自知道或应当知道权利被侵害及义务人之日起算 |")
    L.append("| 报修与索赔 | 越早越好；拖久会造成证据灭失、现场被修复、责任无法划分 |")
    L.append("| 诉讼时效中断 | 书面催告、投诉、起诉均可中断，中断后重新起算 3 年 |")
    L.append("")

    L.append("## 七、租房与特殊情形")
    L.append("")
    L.append("| 核查项 | 判定 | 说明 |")
    L.append("|---|---|---|")
    for name, state, msg in results[4][1]:
        L.append("| %s | %s | %s |" % (name, state, msg.replace("|", " ")))
    L.append("")

    L.append("## 八、待办补正动作")
    L.append("")
    if not todos:
        L.append("当前未发现必须补正的事项。")
    else:
        L.append("| 动作 | 状态 |")
        L.append("|---|---|")
        for n, st in todos:
            L.append("| %s | %s |" % (n, st))
    L.append("")

    L.append("## 九、边界与纪律")
    L.append("")
    L.append("- 本结果依通用规则整理，**不替代律师意见**；最终以主管部门认定与司法机关裁判为准。")
    L.append("- 建设工程质量保修的具体年限范围、住宅专项维修资金的动用条件与表决比例、"
             "各地口径不同，**一律以当地住建（房管）主管部门口径为准**。")
    L.append("- 责任比例、赔偿范围是否获支持，**由司法机关认定**；租金/住宿损失、误工费、"
             "精神损害通常难以全额支持，本表如实提示，不作结果承诺。")
    L.append("- **未填的一律不算通过**，只按已填内容判断。")
    L.append("- 擅自破坏现场导致无法鉴定的，主张会大幅削弱——查勘定损前不要动现场。")
    return "\n".join(L) + "\n"


def to_json(f, results, todos, today, branch):
    bad = [r[0] for _t, rows in results for r in rows if r[1] == "不通过"]
    risk = [r[0] for _t, rows in results for r in rows if r[1] == "有风险"]
    todo = [r[0] for _t, rows in results for r in rows if r[1] == "待补正"]
    concl = "有风险" if (bad or risk) else ("待补正" if todo else "通过")
    return {
        "核查日期": today.isoformat(),
        "漏水部位": f["part"],
        "房屋性质": f["scene"],
        "结论": concl,
        "责任归属初判": branch,
        "风险项": bad + risk,
        "待办": todo,
        "待办动作": [{"动作": n, "状态": s} for n, s in todos],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = read_text(args.input)
    kv = build_kv(text)
    today = base_date(args.base)

    f = {
        "part": get_text(kv, ["漏水部位", "渗水部位", "漏水位置"]),
        "scene": get_text(kv, ["房屋性质", "房屋类型", "住宅类型"]),
        "found_date": get_text(kv, ["发现漏水日期", "漏水发生时间", "发现日期"]),
        "completion_date": get_text(kv, ["竣工验收合格日期", "房屋交付日期", "交房日期", "竣工日期"]),
        "upstairs_reason": get_text(kv, ["楼上住户原因", "楼上原因", "楼上漏水原因"]),
        "public_part": get_text(kv, ["漏水点是否属公共部位", "是否公共部位"]),
        "public_kw": get_text(kv, ["漏水点描述", "漏水位置描述"]),
        "cause_clear": get_text(kv, ["漏水原因是否明确", "原因是否查清"]),
        "cause_desc": get_text(kv, ["漏水原因已经查明为", "查明的漏水原因"]),
        "appraised": get_text(kv, ["是否已做渗漏原因鉴定", "是否做过鉴定", "鉴定情况"]),
        "appraisal_fee": parse_num(get_text(kv, ["鉴定费金额", "渗漏原因鉴定费"])),
        "repair_cost": parse_num(get_text(kv, ["修复费用", "修复报价", "维修费用"])),
        "property_loss": parse_num(get_text(kv, ["财产损失金额", "财物损失金额"])),
        "other_cost": parse_num(get_text(kv, ["其他损失金额"])),
        "rent_loss": parse_num(get_text(kv, ["租金住宿损失金额", "住宿损失金额"])),
        "repair_done": get_text(kv, ["是否已维修", "维修情况"]),
        "scope_expanded": get_text(kv, ["是否扩大维修范围", "维修范围是否自行扩大"]),
        "policy_reported": get_text(kv, ["是否已向物业报修", "是否向物业报修"]),
        "policy_on_site": get_text(kv, ["物业是否到场并记录", "物业到场情况"]),
        "notified": get_text(kv, ["是否已书面通知物业与楼上", "书面通知情况"]),
        "notify_to": get_text(kv, ["已通知对象", "通知对象"]),
        "community": get_text(kv, ["是否已找社区居委会调解", "社区调解情况"]),
        "fund_possible": get_text(kv, ["是否可动用住宅专项维修资金", "维修资金情况"]),
        "vote_done": get_text(kv, ["维修资金业主表决情况", "业主表决情况"]),
        "rental": get_text(kv, ["是否属承租房屋", "是否租住", "是否租房"]),
        "tenant_notified": get_text(kv, ["是否已及时通知房东", "房东通知情况"]),
        "fee_owed": get_text(kv, ["是否以拒交物业费主张权利", "物业费欠缴情况"]),
        "claim": get_text(kv, ["是否已向责任方主张", "索赔情况"]),
        "evidence": get_text(kv, ["证据清单", "已有证据"]),
    }

    missing = [k for k in ("part",) if not filled(f[k])]

    _y, _dl, wstate, wmsg = warranty_check(f, today)
    years_left = "保修期内" if wstate == "通过" else ("保修期外" if wstate == "有风险" else "待定")
    branch_txt = responsibility_text(f, years_left)
    results = [
        ("责任归属判定", responsibility(f, years_left)),
        ("保修期与开发商责任", [("保修期核查", wstate, wmsg)]),
        ("取证与鉴定", checks_evidence(f)),
        ("损失核算与赔偿范围", checks_loss(f)),
        ("租房与特殊情形", checks_special(f)),
    ]
    steps = path_order(f)
    todos = todo_list(f, results)

    if args.json:
        print(json.dumps(to_json(f, results, todos, today, branch_txt),
                         ensure_ascii=False, indent=2))
        return 0

    d = parse_date(f["found_date"])
    if d:
        dl = add_years(d, 3)
        left = (dl - today).days
        deadline_txt = ("发现漏水日期 %s 起算的 3 年时效截至 %s，%s"
                        % (d.isoformat(), dl.isoformat(),
                           ("已超期 %d 天" % -left) if left < 0 else ("还剩 %d 天" % left)))
    else:
        deadline_txt = ("未填发现漏水日期，民事诉讼时效为 3 年，"
                        "自知道或应当知道权利被侵害及义务人之日起算，请补填后重跑")

    rep = render(f, results, steps, todos, today, deadline_txt, branch_txt)
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


def responsibility_text(f, years_left):
    up = f["upstairs_reason"] or ""
    pub = yes(f["public_part"])
    part = f["part"] or ""
    if up and any(k in up for k in UPSTAIRS_KW):
        return "楼上住户（相邻关系/侵权责任）"
    if pub or any(k in part for k in PUBLIC_KW):
        return "物业服务人 / 业主共有部分（可申请住宅专项维修资金）"
    if years_left == "保修期内":
        return "开发商（建设工程质量保修责任）"
    if years_left == "保修期外":
        return "待查清（楼上/开发商原始缺陷/公共部位混合，需渗漏原因鉴定）"
    return "待补正（缺竣工日期或楼上原因）"


if __name__ == "__main__":
    sys.exit(main())
