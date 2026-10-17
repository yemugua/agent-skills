# -*- coding: utf-8 -*-
"""特种作业操作证核验与防骗常识脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段核验报告，含结论摘要、证书真伪与官方核验、骗局话术与办证机构、
      费用与收款、法律后果与举报入口、复审换证提醒、证据清单、待办补正动作、边界与纪律。

只做核验、防骗科普与官方查询指引，不提供任何办证、代考或制证服务。
退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

FIELD_ALIAS = {
    "证书类型": ["证书类型", "证书种类", "什么证", "工种", "作业类别"],
    "证书编号": ["证书编号", "证号", "证书号"],
    "发证机构": ["发证机构", "发证机关", "颁发单位", "发证单位"],
    "证书是否已收到": ["证书是否已收到", "是否拿到证书", "证书收到情况", "是否已取证"],
    "收到证书日期": ["收到证书日期", "取证日期", "拿到证书时间"],
    "是否已在官方平台核验": ["是否已在官方平台核验", "是否官方核验", "是否官网查询", "核验情况", "是否查验"],
    "核验平台": ["核验平台", "查询平台", "核验渠道", "查询网站"],
    "核验结果": ["核验结果", "查询结果", "查验结果", "核验情况描述"],
    "核验不一致项": ["核验不一致项", "不一致项", "差异项"],
    "办证机构名称": ["办证机构名称", "机构名称", "办证方", "中介名称", "培训机构名称"],
    "联系渠道": ["联系渠道", "怎么联系的", "来源渠道", "获客渠道"],
    "是否签协议": ["是否签协议", "是否签合同", "有无合同", "是否签约"],
    "对方宣传或承诺摘录": ["对方宣传或承诺摘录", "承诺话术", "宣传话术", "对方话术", "广告内容"],
    "办证费用": ["办证费用", "费用", "报价"],
    "已付金额": ["已付金额", "已支付金额", "实付金额", "付款金额"],
    "已退金额": ["已退金额", "已退款金额", "退款金额"],
    "付款方式": ["付款方式", "支付方式", "怎么付的"],
    "收款主体": ["收款主体", "收款方", "收款单位", "打款给谁"],
    "是否本人参加考试": ["是否本人参加考试", "本人是否考试", "是否参加考试", "考试情况"],
    "是否要求本人到场": ["是否要求本人到场", "是否需要本人到场", "是否本人到场"],
    "是否提供真题或替考": ["是否提供真题或替考", "是否提供替考", "有无替考", "是否给真题"],
    "是否完成培训学时": ["是否完成培训学时", "是否培训", "学时情况", "有无培训"],
    "出证周期天数": ["出证周期天数", "出证时间", "办证周期", "多久出证"],
    "证书用途": ["证书用途", "用途", "用来做什么"],
    "是否已用于上岗": ["是否已用于上岗", "是否用于上岗", "有无上岗"],
    "是否已举报": ["是否已举报", "有无举报", "举报情况", "是否投诉"],
    "证据留存情况": ["证据留存情况", "证据情况", "有哪些证据", "留证情况", "已保存材料"],
    "诉求": ["诉求", "希望怎么解决", "期望结果"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)


def norm(s):
    if s is None:
        return ""
    out = str(s).strip()
    out = out.replace("：", ":").replace("　", " ")
    out = out.replace("（", "(").replace("）", ")")
    out = re.sub(r"\s+", "", out)
    return out.lower()


def filled(v):
    if v is None:
        return False
    return norm(v) not in {norm(t) for t in EMPTY_TOKENS}


def unknown(v):
    return not filled(v)


def fmt_num(n):
    if n is None:
        return "-"
    if isinstance(n, float):
        if n == int(n):
            return str(int(n))
        return ("%.2f" % n).rstrip("0").rstrip(".")
    return str(n)


def money(n):
    if n is None:
        return "-"
    return "¥" + fmt_num(round(float(n), 2))


def parse_num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("，", "")
    s = re.sub(r"[¥￥元人民币rmb$]", "", s)
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_date(v):
    if v is None or unknown(v):
        return None
    s = str(v).strip()
    s = s.replace("年", "-").replace("月", "-").replace("日", "")
    s = s.replace("/", "-").replace(".", "-")
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def parse_md(path):
    data = {}
    if not path or not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            line = line.lstrip(">").strip()
        if not line:
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2:
                continue
            key_raw = cells[0]
            if set(key_raw) <= set("-: "):
                continue
            val = " ".join(c.strip() for c in cells[1:]).strip()
            if val:
                data[norm(key_raw)] = val
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, 1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    """精确匹配表头，绝不用子串 in（会串字段）。"""
    aliases = sorted(FIELD_ALIAS.get(key, [key]), key=len, reverse=True)
    for a in aliases:
        na = norm(a)
        if not na:
            continue
        if na in f:
            v = f.get(na)
            if filled(v):
                return v
        stripped = re.sub(r"^\d+[.、)]\s*", "", na)
        if stripped != na and stripped in f:
            v = f.get(stripped)
            if filled(v):
                return v
    return ""


NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做")


def yesno(text):
    if unknown(text):
        return None
    n = norm(text)
    for w in NEG_WORDS:
        if n.startswith(w):
            return False
    for w in POS_WORDS:
        if n.startswith(w):
            return True
    return None


def check_official(f):
    """官方核验：返回 (状态, 说明列表)。"""
    items = []
    ctype = get_text(f, "证书类型")
    no = get_text(f, "证书编号")
    issuer = get_text(f, "发证机构")
    verified = yesno(get_text(f, "是否已在官方平台核验"))
    platform = get_text(f, "核验平台")
    result = get_text(f, "核验结果")
    diff = get_text(f, "核验不一致项")
    got = yesno(get_text(f, "证书是否已收到"))
    status = "有风险"

    items.append("证书类型：%s" % (ctype if filled(ctype) else "未填写"))
    items.append("证书编号：%s" % (no if filled(no) else "未填写"))
    items.append("发证机构：%s" % (issuer if filled(issuer) else "未填写"))

    n_res = norm(result)
    if filled(result) and any(k in n_res for k in ("查不到", "查无", "未查询到", "无记录", "不存在", "不符")):
        items.append("**官方核验结果为查不到/不符**：该证书不能作为上岗资格使用，高度疑似伪造")
        status = "不通过"
    elif verified is True and filled(result):
        items.append("已在官方平台核验，结果：%s" % str(result)[:80])
        if filled(diff):
            items.append("**存在不一致项**：%s —— 与证书实体不符的需立即核实" % str(diff)[:80])
            status = "不通过"
        else:
            status = "通过"
    elif verified is False:
        items.append("**尚未在官方平台核验**：付款前必须先核，核不到就不要付")
        status = "不通过"
    else:
        items.append("未填写官方核验情况，**证书真伪无法判断**")
        return "待补正", items

    if got is True and status != "通过" and verified is not True:
        items.append("已收到证书但未完成官方核验：不要用于上岗，先核完再说")
    elif got is False:
        items.append("尚未收到证书")
    items.append("官方入口：应急管理部特种作业操作证查询平台（cx.mem.gov.cn）；"
                 "人社部技能人才评价证书全国联网查询用于技能等级证")
    return status, items


def check_scam(f):
    """骗局话术与办证机构：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    promo = get_text(f, "对方宣传或承诺摘录")
    agent = get_text(f, "办证机构名称")
    channel = get_text(f, "联系渠道")
    signed = yesno(get_text(f, "是否签协议"))
    exam = yesno(get_text(f, "是否本人参加考试"))
    onsite = yesno(get_text(f, "是否要求本人到场"))
    cheat = yesno(get_text(f, "是否提供真题或替考"))
    hours = yesno(get_text(f, "是否完成培训学时"))
    days = parse_num(get_text(f, "出证周期天数"))
    blob = norm(" ".join([promo, channel, agent]))

    items.append("办证机构：%s" % (agent if filled(agent) else "未填写"))
    items.append("联系渠道：%s" % (channel if filled(channel) else "未填写"))

    high_kw = {
        "包过": "「包过」——特种作业考试由应急管理部门组织，任何机构无权承诺通过",
        "免考": "「免考」——必须本人参加考试，免考即不可能取得真证",
        "不用考试": "「不用考试」——同免考，一定产生不了真证",
        "替考": "「替考」——属违法，涉事双方均需承担责任",
        "改分": "「改分」——涉及非法操作官方系统，刑事风险",
        "补录": "「补录系统」——官方数据库无第三方录入权限",
        "内部渠道": "「内部渠道」——官方数据无第三方可操作空间",
        "内部名额": "「内部名额」——同上",
        "一周出证": "「一周出证」——考核、制证、录入有法定流程，不可能凭关系加速",
        "三天出证": "「三天出证」——同上",
        "当天出证": "「当天出证」——同上",
        "全网可查": "「全网可查」——只有官方平台可查，所谓内部查询页是伪造的",
        "不用本人": "「不用本人到场」——必须本人参加考试",
    }
    for k, v in high_kw.items():
        if k in blob:
            crit.append("骗局话术：%s" % v)

    if exam is False:
        crit.append("本人未参加考试：未参加考试即取得证书，该证不可能是真证")
    elif exam is None:
        risk.append("未填写是否本人参加考试——这是判断真伪的核心事实")
    if onsite is False:
        crit.append("未要求本人到场：与法定考试要求不符")
    if cheat is True:
        crit.append("对方提供真题或替考：属违法，应立即停止并向应急管理部门举报")
    if hours is False:
        risk.append("未完成培训学时：正规取证需完成规定学时")
    elif hours is None:
        risk.append("未填写是否完成培训学时")

    if days is not None and days <= 7:
        crit.append("出证周期仅 %s 天，远低于正常考核制证流程所需时间，高度可疑" % fmt_num(days))
    elif days is not None and days <= 15:
        risk.append("出证周期 %s 天偏短，需与官方核验结果交叉确认" % fmt_num(days))

    if signed is False:
        risk.append("未签协议：退款与责任无书面依据")
    elif signed is None:
        risk.append("未填写是否签协议")
    return crit, risk, items


def check_fee(f):
    """费用与收款：返回 (风险项, 说明列表)。"""
    risk = []
    items = []
    fee = parse_num(get_text(f, "办证费用"))
    paid = parse_num(get_text(f, "已付金额"))
    back = parse_num(get_text(f, "已退金额")) or 0.0
    payee = get_text(f, "收款主体")
    agent = get_text(f, "办证机构名称")
    pay = get_text(f, "付款方式")

    if paid is None and fee is None:
        items.append("未填写办证费用与已付金额，**金额部分无法核查**")
    else:
        base = paid if paid is not None else fee
        items.append("已付 %s（办证报价 %s）" % (money(paid) if paid is not None else "未填写",
                                         money(fee) if fee is not None else "未填写"))
        net = base - back
        items.append("已付 %s − 已退 %s = 未退 %s" % (money(base), money(back), money(net)))
        if paid is not None and fee is not None and paid > fee:
            risk.append("已付 %s 超过报价 %s，超出部分无依据" % (money(paid), money(fee)))

    n_pay = norm(pay)
    if filled(pay) and any(k in n_pay for k in ("微信个人", "个人", "现金")):
        risk.append("收款为个人账户或现金：无合同主体可追，追损难度大")

    if filled(payee) and filled(agent) and norm(payee) != norm(agent):
        risk.append("收款主体「%s」与办证机构「%s」不一致，出事后极易互相推诿" % (payee, agent))
    elif not filled(payee):
        risk.append("未填写收款主体，需核对付款凭证上的收款方名称")
    return risk, items


def check_renew(f):
    """复审换证提醒：返回说明列表。"""
    items = []
    got = parse_date(get_text(f, "收到证书日期"))
    items.append("特种作业操作证**有效期 6 年，每 3 年复审一次**；"
                 "复审应在期满前提出申请，逾期未复审的证书失效")
    if got is not None:
        nxt = date(got.year + 3, got.month, got.day)
        end = date(got.year + 6, got.month, got.day)
        items.append("若取证日为 %s，则首次复审到期约 %s，证书有效期至约 %s" %
                     (got.isoformat(), nxt.isoformat(), end.isoformat()))
    else:
        items.append("未填写收到证书日期，**复审到期日无法推算**，请补齐")
    items.append("连续从事本工种满一定年限且符合条件的，复审周期可按应急管理部门规定延长，"
                 "具体以当地应急管理部门口径为准")
    return items


def check_evidence(f):
    ev = norm(get_text(f, "证据留存情况"))
    need = [
        ("招生/办证宣传页面与聊天记录", ("宣传", "聊天", "广告", "微信", "页面", "截图")),
        ("付款凭证与收款方信息", ("付款", "转账", "流水", "发票", "收据", "收款")),
        ("协议或收据", ("协议", "合同", "收据", "字据")),
        ("证书实物照片（正反面）", ("证书", "照片", "实物")),
        ("官方核验结果截图", ("核验", "查询", "截图", "官网")),
        ("对方联系方式与主体信息", ("联系方式", "电话", "主体", "公司名")),
    ]
    if not ev:
        return [], [n for n, _ in need]
    have = []
    miss = []
    for name, kws in need:
        if any(k in ev for k in kws):
            have.append(name)
        else:
            miss.append(name)
    return have, miss


def build_report(f, base=None):
    rep = []
    crit = []
    risk = []
    todo = []

    ctype = get_text(f, "证书类型")
    agent = get_text(f, "办证机构名称")
    promo = get_text(f, "对方宣传或承诺摘录")
    paid = parse_num(get_text(f, "已付金额"))
    verified = yesno(get_text(f, "是否已在官方平台核验"))
    result = get_text(f, "核验结果")
    used = yesno(get_text(f, "是否已用于上岗"))
    demand = get_text(f, "诉求")

    off_status, off_items = check_official(f)
    s_crit, s_risk, s_items = check_scam(f)
    fee_risk, fee_items = check_fee(f)
    renew_items = check_renew(f)
    have_ev, miss_ev = check_evidence(f)

    n_res = norm(result)
    not_found = filled(result) and any(k in n_res for k in
                                       ("查不到", "查无", "未查询到", "无记录", "不存在", "不符"))

    core_missing = not filled(ctype) and not filled(promo) and not filled(agent)
    if not core_missing:
        crit.extend(s_crit)
        if off_status == "不通过":
            crit.append("官方核验未通过：见证书真伪与官方核验")
        if not_found:
            crit.append("官方平台查不到该证书：不能作为上岗资格使用")
        risk.extend(s_risk)
        risk.extend(fee_risk)
        if off_status == "待补正":
            risk.append("未做官方核验，证书真伪未定")
        if used is True and off_status != "通过":
            crit.append("证书已用于上岗但未通过官方核验：属无证/持假证上岗，"
                        "应立即停止作业并向应急管理部门核实")
        if miss_ev:
            risk.append("证据缺失 %d 项：%s" % (len(miss_ev), "、".join(miss_ev[:3])))

    if core_missing:
        verdict = "待补正"
    elif crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"

    # 1 结论摘要
    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 证书类型：%s" % (ctype if filled(ctype) else "未填写"))
    rep.append("- 办证机构：%s" % (agent if filled(agent) else "未填写"))
    rep.append("- 官方核验：%s" % off_status)
    rep.append("- 已付金额：%s" % (money(paid) if paid is not None else "未填写"))
    rep.append("- 骗局话术命中 %d 项 / 风险项 %d 项" % (len(s_crit), len(s_risk)))
    rep.append("- 证书可用性：%s" % ("可用（官方核验为真）" if off_status == "通过"
                                else "未通过核验，不得用于上岗"))
    rep.append("- **总体结论：%s**" % verdict)
    rep.append("")

    # 2 真伪与核验
    rep.append("## 证书真伪与官方核验")
    rep.append("")
    for it in off_items:
        rep.append("- %s" % it)
    rep.append("")

    # 3 话术与机构
    rep.append("## 骗局话术与办证机构核查")
    rep.append("")
    for it in s_items:
        rep.append("- %s" % it)
    for c in s_crit:
        rep.append("- **%s**" % c)
    for r in s_risk:
        rep.append("- %s" % r)
    if filled(promo):
        rep.append("- 对方宣传或承诺摘录：%s" % str(promo)[:120])
    rep.append("")

    # 4 费用
    rep.append("## 费用与收款核查")
    rep.append("")
    for it in fee_items:
        rep.append("- %s" % it)
    for r in fee_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 5 后果与举报
    rep.append("## 法律后果、合规取证路径与举报入口")
    rep.append("")
    rep.append("- 持假证上岗属重大事故隐患，可依《安全生产法》"
               "《特种作业人员安全技术培训考核管理规定》相关规定对人员与用工单位予以处罚。")
    rep.append("- 伪造、买卖、使用伪造的国家机关证件或事业单位印章，情节严重的可能触及《刑法》相关规定。")
    rep.append("- 正规流程：具备资质的培训机构报名 → 完成规定学时 → "
               "**本人**参加理论与实操考试 → 应急管理部门发证并录入官方数据库 → 官方平台可查。")
    rep.append("- 举报入口：当地应急管理部门（假证与非法培训）、市场监管部门/12315"
               "（虚假宣传与无照经营）、公安机关（收钱失联涉嫌诈骗）。")
    if yesno(get_text(f, "是否已举报")) is True:
        rep.append("- 已申报举报，请保留受理编号与处理结果")
    else:
        rep.append("- 尚未举报：先完成官方核验并固定证据，再按上列入口举报")
    rep.append("")

    # 6 复审
    rep.append("## 复审换证提醒")
    rep.append("")
    for it in renew_items:
        rep.append("- %s" % it)
    rep.append("")

    # 7 证据
    rep.append("## 证据清单与固定要点")
    rep.append("")
    if have_ev:
        rep.append("已具备：")
        for h in have_ev:
            rep.append("- %s" % h)
    else:
        rep.append("- 采集表未填写任何已留存证据")
    rep.append("")
    if miss_ev:
        rep.append("仍缺失：")
        for m in miss_ev:
            rep.append("- **%s**" % m)
    else:
        rep.append("- 主要证据类别已覆盖，仍需确认原始载体完整")
    rep.append("")
    rep.append("固定要点：不要只截单张图，聊天记录要连上下文导出；"
               "官方核验要自己登平台查，不要点对方给的链接。")
    rep.append("")

    # 8 待办
    rep.append("## 待办补正动作")
    rep.append("")
    if core_missing:
        todo.append("补齐「证书类型」「办证机构名称」「对方宣传或承诺摘录」——这是出具结论的前提")
    if off_status != "通过":
        todo.append("登录应急管理部特种作业操作证查询平台（cx.mem.gov.cn）自行核验，"
                    "并截图留存查询日期与结果")
    if not_found:
        todo.append("官方查不到的：立即停止使用该证书上岗，书面要求对方退款并说明来源")
    if not filled(get_text(f, "是否本人参加考试")):
        todo.append("确认是否本人参加考试——这是判断真伪的核心事实")
    if not filled(get_text(f, "收款主体")):
        todo.append("核对付款凭证上的收款方名称，与办证机构是否一致")
    for m in miss_ev:
        todo.append("补齐证据：%s" % m)
    if not filled(get_text(f, "收到证书日期")):
        todo.append("补齐收到证书日期，用于推算复审到期日")
    if not filled(demand):
        todo.append("明确诉求：退款 / 重新参加正规培训考试 / 举报机构 / 报案")
    if not todo:
        todo.append("信息已较完整，按报告结论执行；核验为真的，建立复审到期提醒")
    for i, t in enumerate(todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见与官方核验，"
               "最终以应急管理部门、人社部门及司法机关认定为准。")
    rep.append("- 证书真伪的**唯一标准是官方平台查询结果**，二维码、查询链接、"
               "纸质证书本身都不能单独证明真伪。")
    rep.append("- **本技能仅做证书核验、防骗科普与官方查询指引，不提供任何办证、代考或制证服务，"
               "也不指引你去找这类服务。**")
    rep.append("- 涉金额较大或对方失联的，应立即向公安机关报案。")

    return "\n".join(rep), verdict, crit + risk, todo


def main():
    ap = argparse.ArgumentParser(description="特种作业操作证核验与防骗常识")
    ap.add_argument("md", nargs="?", default="样例.md")
    ap.add_argument("--input", dest="input", default=None)
    ap.add_argument("--base", default=None)
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path = args.input or args.md
    if not path or not os.path.exists(path):
        msg = "采集表不存在：%s" % path
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2
    f = parse_md(path)
    if not f:
        msg = "采集表为空或格式无法解析，请用「| 字段 | 值 |」或「字段：值」格式填写"
        print(json.dumps({"错误": msg, "结论": "待补正"}, ensure_ascii=False) if args.json else msg)
        return 2

    report, verdict, issues, todo = build_report(f)
    if args.json:
        print(json.dumps({"结论": verdict, "风险项": issues, "待办": todo, "报告": report},
                         ensure_ascii=False, indent=2))
    else:
        print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)

    if not filled(get_text(f, "证书类型")) and not filled(get_text(f, "对方宣传或承诺摘录")) \
            and not filled(get_text(f, "办证机构名称")):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
