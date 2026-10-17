# -*- coding: utf-8 -*-
"""家政服务纠纷维权核查。

输入：Markdown 采集表（支持 | 字段 | 值 | 表格与 字段：值 两种写法，全角冒号均认）
输出：9 段核查报告，结论四态：通过 / 有风险 / 不通过 / 待补正

核心事实缺失（家政类型、问题描述、已付金额三选一为空）→ 退出码 2，锁「待补正」。
"""
import os
import sys
import re
import json
import argparse
from datetime import date, datetime

# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

FIELD_ALIAS = [
    "家政服务类型", "服务提供者", "服务人员身份", "有无合同", "合同主体",
    "付款方式", "收款主体", "已付金额", "问题描述", "发生时间",
    "服务起止日期", "有无平台", "平台名称", "损害情况", "是否预付费",
    "剩余服务期", "证据留存", "诉求",
]


def norm(s):
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s)).strip()


def filled(v):
    return norm(v) != "" and norm(v).lower() not in [t.lower() for t in EMPTY_TOKENS]


def unknown(v):
    return not filled(v)


def money(v):
    if v is None:
        return "¥0"
    try:
        f = float(v)
        s = ("%.2f" % f).rstrip("0").rstrip(".")
        return "¥" + s
    except Exception:
        return "¥" + str(v)


def fmt_num(v):
    try:
        f = float(v)
        s = ("%.2f" % f).rstrip("0").rstrip(".")
        return s
    except Exception:
        return str(v)


def parse_md(path):
    """解析采集表，返回 dict(归一字段名 -> 值)。"""
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    for line in lines:
        s = line.strip()
        if not s:
            continue
        # 表格行 | 字段 | 值 |
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            # 跳过分隔行
            if cells and set(norm(c) for c in cells) <= set("-: "):
                continue
            if len(cells) >= 2:
                key_raw, val = cells[0], cells[1]
                data[key_raw] = val
            continue
        # 冒号行 字段：值
        if ":" in s or "：" in s:
            parts = re.split(r"[:：]", s, 1)
            if len(parts) == 2:
                key_raw, val = parts[0].strip(), parts[1].strip()
                data[key_raw] = val
    return data


def get_text(f, field):
    """按别名精确匹配字段值，去掉 '1. ' 之类前缀。"""
    target = norm(field)
    # 先精确匹配
    for k, v in f.items():
        if norm(k) == target:
            return v
    # 别名按长度降序匹配（避免 '金额' 串到 '已付金额'）
    aliases = FIELD_ALIAS
    for alias in sorted(aliases, key=len, reverse=True):
        if norm(alias) == target:
            for k, v in f.items():
                nk = re.sub(r"^\d+[.、)]\s*", "", norm(k))
                if nk == norm(alias):
                    return v
    return ""


def yesno(v):
    if not filled(v):
        return None
    s = norm(v)
    # 先判否定词（"没有"含"有"，必须先于 POS 处理，避免误判为肯定）
    NEG = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "没有做")
    POS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "做过")
    for w in NEG:
        if w in s:
            return False
    for w in POS:
        if w in s:
            return True
    return None


# ---------------------------------------------------------------------------
# 各模块核查
# ---------------------------------------------------------------------------
def check_contract(f):
    """合同与主体核查。返回 (状态, items, risk)。"""
    items, risk = [], []
    has_contract = yesno(get_text(f, "有无合同"))
    provider = get_text(f, "服务提供者")
    entity = get_text(f, "合同主体")
    payee = get_text(f, "收款主体")
    platform = get_text(f, "有无平台")
    plat_name = get_text(f, "平台名称")

    if has_contract is False:
        items.append("未签订书面合同：口头约定难以举证，纠纷时责任与费用边界易扯皮")
    elif has_contract is True:
        items.append("已签订书面合同，后续重点核对合同主体与收款主体是否一致")
    else:
        items.append("未填写是否有合同，**合同情况无法确认**")

    if filled(entity) and filled(payee) and norm(entity) != norm(payee):
        risk.append("合同主体与收款主体不一致（%s 收钱但 %s 签约）：存在挂靠、转包或跑路风险"
                    % (norm(payee), norm(entity)))
    if filled(provider) and not filled(entity):
        items.append("填写了服务提供者但未填合同主体，**签约方身份不明**")
    if filled(platform) and yesno(platform) is True and not filled(plat_name):
        items.append("声称通过平台但**未填写平台名称**，难以走平台投诉与担保赔付")
    if yesno(platform) is False and filled(provider):
        items.append("未通过平台、直接私下交易：缺少平台担保与先行赔付机制，维权靠直接举证")
    status = "不通过" if risk else ("有风险" if has_contract is False else "通过")
    return status, items, risk


def check_pay(f):
    """付款与预付费核查。"""
    items, risk = [], []
    paid = get_text(f, "已付金额")
    prepay = yesno(get_text(f, "是否预付费"))
    remain = get_text(f, "剩余服务期")
    pay_way = get_text(f, "付款方式")

    if not filled(paid):
        items.append("未填写已付金额，**退费基数无法测算**")
    else:
        items.append("已付金额：%s" % money(paid))
    if prepay is True:
        items.append("属于预付费（先付后用）：可主张按未履约部分比例退费；"
                     "若经营者停业、跑路，可报市场监管并主张全额退")
        if not filled(remain):
            items.append("未填写剩余服务期，**可退区间无法测算**")
    elif prepay is False:
        items.append("非预付费（按次/按日结算）：退费按已发生费用扣减后结算")
    else:
        items.append("未填写是否预付费，**退费口径无法确认**")
    if filled(pay_way) and ("微信" in norm(pay_way) or "个人" in norm(pay_way)
                            or "现金" in norm(pay_way)) and "对公" not in norm(pay_way):
        risk.append("付款至个人账户/现金/微信直转：缺少对公凭证，退款追偿难，建议补开发票或收据")
    status = "不通过" if risk else "有风险" if prepay is True else "通过"
    return status, items, risk


def check_damage(f):
    """人身/财产损害核查。"""
    items, risk, crit = [], [], []
    dmg = get_text(f, "损害情况")
    if not filled(dmg):
        items.append("未填写损害情况：如有无财物损坏、人员受伤、隐私泄露等")
        return "待补正", items, risk, crit
    blob = norm(dmg)
    if any(w in blob for w in ("受伤", "骨折", "烫伤", "跌", "住院", "医疗", "医院", "就医",
                               "急诊", "伤", "撞", "碰", "摔", "病", "ICU")):
        crit.append("涉及人身伤害：保留病历、诊断证明、医疗费票据，可主张医疗费、护理费等，"
                    "严重时涉侵权责任，优先就医并报警/留存伤情照片")
        risk.append("人身损害风险高")
    if any(w in blob for w in ("损坏", "丢失", "摔碎", "碎", "划", "偷", "丢", "财产", "坏", "损")):
        risk.append("涉及财物损坏/丢失：列明物品、购买凭证与损失金额，可主张照价赔偿")
    if any(w in blob for w in ("隐私", "偷拍", "泄露", "骚扰")):
        crit.append("涉及隐私/骚扰：可主张人格权侵害，情节严重报公安")
        risk.append("隐私侵权风险")
    if not risk and not crit:
        items.append("损害情况已填但未识别到明确损害，按一般服务纠纷处理")
    status = "不通过" if crit else ("有风险" if risk else "通过")
    return status, items, risk, crit


def check_evidence(f):
    """证据清单核查。"""
    have, miss = [], []
    ev = norm(get_text(f, "证据留存"))
    checks = [
        ("合同/协议", ("合同", "协议", "订单")),
        ("付款凭证", ("付款", "转账", "收据", "发票", "记录")),
        ("沟通记录", ("聊天", "记录", "微信", "短信")),
        ("服务过程记录", ("照片", "视频", "打卡", "工单")),
        ("损害证明", ("病历", "诊断", "票据", "照片", "鉴定")),
    ]
    for label, keys in checks:
        if any(k in ev for k in keys):
            have.append(label)
        else:
            miss.append(label)
    return have, miss


def build_report(f, cc, ci, cp, cd, have, miss):
    lines = []
    lines.append("# 家政服务纠纷维权核查报告")
    lines.append("")
    # 1 结论摘要
    lines.append("## 一、结论摘要")
    core_missing = []
    if not filled(get_text(f, "家政服务类型")):
        core_missing.append("家政服务类型")
    if not filled(get_text(f, "问题描述")):
        core_missing.append("问题描述")
    if not filled(get_text(f, "已付金额")):
        core_missing.append("已付金额")
    if core_missing:
        concl = "**待补正**"
        reason = "以下核心信息缺失，暂无法给出明确结论：" + "、".join(core_missing)
    else:
        # 综合判定
        blocking = []
        for name, st in [("合同主体", cc[0]), ("付款", cp[0]), ("损害", cd[0])]:
            if st == "不通过":
                blocking.append(name)
        if blocking:
            concl = "**不通过**"
            reason = "存在明确风险点：" + "、".join(blocking) + "，建议谨慎并立即固定证据"
        elif any(st == "有风险" for st in (cc[0], cp[0], cd[0])):
            concl = "**有风险**"
            reason = "部分环节存在风险，可按本报告补正后推进维权"
        else:
            concl = "**通过**"
            reason = "核心环节未见重大风险，可按标准路径维权"
    lines.append("- 综合结论：%s" % concl)
    lines.append("- 说明：%s" % reason)
    lines.append("")

    # 2 家政类型与服务方
    lines.append("## 二、家政类型与服务方核查")
    lines.append("- 家政服务类型：%s" % (get_text(f, "家政服务类型") or "（未填）"))
    lines.append("- 服务提供者：%s" % (get_text(f, "服务提供者") or "（未填）"))
    lines.append("- 服务人员身份：%s" % (get_text(f, "服务人员身份") or "（未填）"))
    lines.append("- 有无平台：%s" % (get_text(f, "有无平台") or "（未填）"))
    lines.append("")
    for x in ci:
        lines.append("- " + x)
    lines.append("")

    # 3 合同与主体
    lines.append("## 三、合同与主体一致性")
    for x in cc[1]:
        lines.append("- " + x)
    if cc[2]:
        lines.append("- **风险项**：")
        for x in cc[2]:
            lines.append("  - " + x)
    lines.append("")

    # 4 付款与预付费
    lines.append("## 四、付款与预付费退费口径")
    for x in cp[1]:
        lines.append("- " + x)
    if cp[2]:
        lines.append("- **风险项**：")
        for x in cp[2]:
            lines.append("  - " + x)
    lines.append("")

    # 5 损害情况
    lines.append("## 五、人身与财产损害识别")
    if cd[1]:
        for x in cd[1]:
            lines.append("- " + x)
    if cd[3]:
        lines.append("- **高危项**：")
        for x in cd[3]:
            lines.append("  - " + x)
    if cd[2]:
        lines.append("- 风险项：")
        for x in cd[2]:
            lines.append("  - " + x)
    lines.append("")

    # 6 证据清单
    lines.append("## 六、证据清单与固定要点")
    lines.append("- 已具备：%s" % ("、".join(have) if have else "（无）"))
    lines.append("- 缺失/待补：%s" % ("、".join(miss) if miss else "（齐全）"))
    lines.append("- 通用要点：合同/订单截图、付款转账记录、与平台的聊天记录、"
                 "服务人员上门打卡或工单、损害照片/视频、病历票据，均应在纠纷发生前后及时固定")
    lines.append("")

    # 7 维权路径
    lines.append("## 七、维权与投诉路径")
    lines.append("- 平台内投诉：若经家政平台，先走平台纠纷处理与先行赔付")
    lines.append("- 12315 / 全国 12315 平台（网站、APP、微信小程序）：服务类消费纠纷统一入口")
    lines.append("- 市场监管部门：经营者无照经营、虚假宣传、预付费跑路")
    lines.append("- 公安：涉及盗窃、人身伤害、诈骗（如虚构家政公司收钱跑路）")
    lines.append("- 人民法院 / 人民调解：小额诉讼、诉前调解，主张退费与赔偿")
    lines.append("- 商务主管部门：部分城市对家政服务有行业规范与备案要求，可咨询当地")
    lines.append("")

    # 8 待办补正动作
    lines.append("## 八、待办补正动作")
    todos = []
    if core_missing:
        todos.append("补齐核心信息：" + "、".join(core_missing))
    if miss:
        todos.append("补充证据：" + "、".join(miss))
    if cc[2]:
        todos.append("核实合同主体与收款方工商信息（国家企业信用信息公示系统），确认是否同一主体")
    if cp[2]:
        todos.append("补开正规发票或收据，固定付款凭证")
    if cd[3]:
        todos.append("立即就医并封存病历票据，必要时报警固定伤情")
    if not todos:
        todos.append("证据齐全，可直接走 12315 或平台投诉发起退费/赔偿诉求")
    for i, t in enumerate(todos, 1):
        lines.append("%d. %s" % (i, t))
    lines.append("")

    # 9 边界与纪律
    lines.append("## 九、边界与纪律")
    lines.append("- 本报告仅做信息核查与维权路径指引，**不构成法律意见**，复杂或涉诉案件请咨询律师")
    lines.append("- 不提供任何家政中介、代办投诉或代制证据服务")
    lines.append("- 地域差异：投诉受理口径、家政行业备案要求以当地市场监管与商务部门公布为准")
    lines.append("- 证据关键：时间越早固定越有利，切勿等对方注销或跑路后再补证")
    lines.append("")
    return "\n".join(lines), concl


def main():
    ap = argparse.ArgumentParser(description="家政服务纠纷维权核查")
    ap.add_argument("input", nargs="?", default=None, help="采集表 Markdown 路径")
    ap.add_argument("--base", default=None, help="基准日期 YYYY-MM-DD")
    ap.add_argument("--out", default=None, help="报告输出路径")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    args = ap.parse_args()

    if not args.input or not os.path.exists(args.input):
        msg = "采集表不存在或未指定：%s" % args.input
        if args.json:
            print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False))
        else:
            print(msg)
        return 2

    f = parse_md(args.input)

    # 核心缺失锁待补正
    if not filled(get_text(f, "家政服务类型")) or not filled(get_text(f, "问题描述")) \
            or not filled(get_text(f, "已付金额")):
        cc = check_contract(f)
        cp = check_pay(f)
        cd = check_damage(f)
        have, miss = check_evidence(f)
        rep, concl = build_report(f, cc, [], cp, cd, have, miss)
        if args.json:
            print(json.dumps({"结论": concl, "报告": rep}, ensure_ascii=False))
        elif args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(rep)
        else:
            print(rep)
        return 2

    cc = check_contract(f)
    cp = check_pay(f)
    cd = check_damage(f)
    have, miss = check_evidence(f)
    rep, concl = build_report(f, cc, [], cp, cd, have, miss)

    if args.json:
        print(json.dumps({
            "结论": concl,
            "合同主体状态": cc[0],
            "付款状态": cp[0],
            "损害状态": cd[0],
            "证据已具备": have,
            "证据缺失": miss,
            "报告": rep,
        }, ensure_ascii=False))
    elif args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(rep)
    else:
        print(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
