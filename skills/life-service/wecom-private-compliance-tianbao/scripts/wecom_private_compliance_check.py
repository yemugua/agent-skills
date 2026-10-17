# -*- coding: utf-8 -*-
"""企业微信私域运营合规核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、账号与功能核查、加粉合规核查、诱导分享与裂变核查、
      群发与朋友圈核查、内容资质核查、客户数据与会话存档核查、投诉与处罚记录核查、
      整改指引、边界。

只做核查与指引，不替代企业微信官方规范与审核结论。
退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

FIELD_ALIAS = {
    "企业主体类型": ["企业主体类型", "主体类型", "企业主体", "注册主体"],
    "企业微信是否认证": ["企业微信是否认证", "是否认证", "企业认证", "认证状态"],
    "是否配置客户联系功能": ["是否配置客户联系功能", "客户联系", "是否开通客户联系",
                        "外部联系人", "是否可加客户"],
    "主要加粉方式": ["主要加粉方式", "加粉方式", "加人方式", "引流方式", "获客方式"],
    "是否使用外挂或自动化工具": ["是否使用外挂或自动化工具", "外挂", "自动化工具", "自动加人",
                          "群发机器人", "爬虫", "是否用外挂"],
    "是否购买或爬取客户名单": ["是否购买或爬取客户名单", "购买名单", "爬取名单", "买卖客户",
                        "购买客户信息", "名单来源"],
    "是否做诱导分享或裂变活动": ["是否做诱导分享或裂变活动", "诱导分享", "裂变", "红包裂变",
                          "打卡", "集赞", "砍价", "助力"],
    "是否高频群发": ["是否高频群发", "高频群发", "群发频率", "是否频繁群发", "群发"],
    "是否运营客户朋友圈": ["是否运营客户朋友圈", "客户朋友圈", "朋友圈运营", "发朋友圈"],
    "是否推送金融医疗等需资质内容": ["是否推送金融医疗等需资质内容", "金融内容", "荐股",
                            "医疗内容", "理财推荐", "保险推荐"],
    "是否持有对应推送资质": ["是否持有对应推送资质", "推送资质", "金融资质", "内容资质"],
    "是否配置离职继承与客户分配": ["是否配置离职继承与客户分配", "离职继承", "客户继承",
                          "离职客户分配", "客户分配"],
    "是否使用会话存档功能": ["是否使用会话存档功能", "会话存档", "聊天存档", "存档功能"],
    "会话存档是否告知员工与客户": ["会话存档是否告知员工与客户", "存档告知", "是否告知存档",
                          "存档同意"],
    "客户信息使用是否告知并取得同意": ["客户信息使用是否告知并取得同意", "信息使用告知",
                            "客户信息告知", "隐私告知", "个人信息告知"],
    "是否收到过投诉或账号限制": ["是否收到过投诉或账号限制", "被投诉", "账号限制", "封号",
                          "被限制", "投诉记录"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

# 加粉方式关键词 → 合规判定
BAD_ADD_WORDS = ("爬虫", "批量导入", "购买", "买卖", "抓取", "脚本加人", "自动加人",
                 "爆粉", "薅", "接码", "虚拟号")
OK_ADD_WORDS = ("活码", "渠道活码", "扫一扫", "手机号", "名片", "门店二维码", "物料",
                "公众号", "小程序", "广告")

# 诱导分享/裂变关键词
INDUCE_WORDS = ("诱导分享", "红包裂变", "集赞", "砍价", "助力", "打卡返现", "分享解锁",
                "转发领取", "朋友圈集")

NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法", "没")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "可以", "做过", "完成")


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


def parse_md(path):
    data = {}
    if not path or not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
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
            if norm(key_raw) in ("字段", "field", "项目"):
                continue
            val = " ".join(c.strip() for c in cells[1:]).strip()
            if val:
                data[norm(key_raw)] = val
            continue
        if ":" in line or "：" in line:
            parts = re.split(r"[:：]", line, maxsplit=1)
            if len(parts) == 2:
                k = parts[0].strip().lstrip("-*# ").strip()
                v = parts[1].strip()
                if k and v:
                    data[norm(k)] = v
    return data


def get_text(f, key):
    aliases = sorted(FIELD_ALIAS.get(key, [key]), key=len, reverse=True)
    idx = {}
    for k, v in f.items():
        idx.setdefault(norm(k), v)
    for a in aliases:
        na = norm(a)
        if not na:
            continue
        if na in idx and filled(idx[na]):
            return idx[na]
    return ""


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


def check_account(f):
    """账号与客户联系功能核查。"""
    items, crit, risk = [], [], []
    subj = get_text(f, "企业主体类型")
    auth = yesno(get_text(f, "企业微信是否认证"))
    contact = yesno(get_text(f, "是否配置客户联系功能"))

    if filled(subj):
        items.append("- 企业主体：%s" % subj)
    if auth is False:
        risk.append("企业微信未完成主体认证：未认证企业在成员上限、客户联系能力与功能使用上受限，"
                    "建议完成认证后开展私域运营")
        items.append("- 企业认证：未认证（风险）")
    elif auth is True:
        items.append("- 企业认证：已认证")
    else:
        items.append("- 企业认证：未确认")

    if contact is False:
        crit.append("未配置客户联系功能：私域运营依赖「客户联系」（外部联系人）能力，"
                    "须在管理后台开通并配置成员使用权限，否则无法合规加客户与运营")
        items.append("- 客户联系功能：未配置（阻断）")
    elif contact is True:
        items.append("- 客户联系功能：已配置")
    else:
        crit.append("未确认是否配置客户联系功能：请先在管理后台开通客户联系并配置成员权限")
        items.append("- 客户联系功能：未确认（阻断）")
    return items, crit, risk


def check_addfans(f):
    """加粉合规核查（外挂/爬虫/购买名单/加粉方式）。"""
    items, crit, risk = [], [], []
    tool = yesno(get_text(f, "是否使用外挂或自动化工具"))
    bought = yesno(get_text(f, "是否购买或爬取客户名单"))
    way = get_text(f, "主要加粉方式")

    if filled(way):
        items.append("- 主要加粉方式：%s" % way)
        bad_hits = [w for w in BAD_ADD_WORDS if w in norm(way)]
        if bad_hits:
            items.append("  - 命中违规特征：%s" % "、".join(bad_hits))
    else:
        items.append("- 主要加粉方式：未填")

    if tool is True:
        crit.append("使用外挂或自动化工具（自动加人/自动群发/爬虫/机器人）：违反企业微信使用规范，"
                    "将被限制功能直至封号，且存在数据泄露与合规风险，应立即停用")
        items.append("- 外挂/自动化工具：使用（阻断，立即停用）")
    elif tool is False:
        items.append("- 外挂/自动化工具：未使用")
    else:
        crit.append("未确认是否使用外挂/自动化工具：任何绕过平台接口的自动加人、自动群发、"
                    "爬取行为均属违规且可能封号，请确认后停用")
        items.append("- 外挂/自动化工具：未确认（阻断）")

    if bought is True:
        crit.append("购买或爬取客户名单：买卖、非法获取公民个人信息违反《个人信息保护法》，"
                    "情节严重的涉嫌侵犯公民个人信息罪，必须立即停止并销毁来源数据")
        items.append("- 客户名单来源：购买/爬取（阻断，涉嫌违法）")
    elif bought is False:
        items.append("- 客户名单来源：合规（自有渠道）")
    else:
        items.append("- 客户名单来源：未确认（应仅为自有渠道合法获取）")
    return items, crit, risk


def check_induce(f):
    """诱导分享与裂变核查。"""
    items, crit, risk = [], [], []
    induce = yesno(get_text(f, "是否做诱导分享或裂变活动"))

    if induce is True:
        crit.append("开展诱导分享/裂变活动（红包裂变、集赞、砍价、助力、分享解锁）："
                    "违反《微信外部链接内容管理规范》诱导分享规定，将被拦截链接、限制功能乃至封号")
        items.append("- 诱导分享/裂变：开展（阻断）")
    elif induce is False:
        items.append("- 诱导分享/裂变：未开展")
    else:
        items.append("- 诱导分享/裂变：未确认（请避免任何诱导分享玩法）")
    return items, crit, risk


def check_mass(f):
    """群发与客户朋友圈核查。"""
    items, risk = [], []
    mass = yesno(get_text(f, "是否高频群发"))
    moments = yesno(get_text(f, "是否运营客户朋友圈"))

    if mass is True:
        risk.append("高频群发：企业微信客户群/客户群发有频率限制，高频打扰易被投诉，"
                    "将影响功能使用与账号信用，建议控制频次并按客户标签精准分层触达")
        items.append("- 群发频次：高频（风险）")
    elif mass is False:
        items.append("- 群发频次：正常")
    else:
        items.append("- 群发频次：未确认")

    if moments is True:
        items.append("- 客户朋友圈：运营中（注意平台频次限制：单客户每日展示条数有限，"
                     "超频将被限制发送）")
    elif moments is False:
        items.append("- 客户朋友圈：未运营")
    else:
        items.append("- 客户朋友圈：未确认")
    return items, risk


def check_content(f):
    """推送内容资质核查。"""
    items, crit, risk = [], [], []
    sens = yesno(get_text(f, "是否推送金融医疗等需资质内容"))
    lic = yesno(get_text(f, "是否持有对应推送资质"))

    if sens is True:
        if lic is False:
            crit.append("推送金融/医疗等需资质内容但未持有对应资质：证券投资咨询、基金销售、"
                        "医疗健康等内容须持牌机构与对应资格方可推送，无资质不得公开荐股、"
                        "荐基或发布医疗诊疗建议")
            items.append("- 资质内容推送：无资质（阻断）")
        elif lic is True:
            items.append("- 资质内容推送：已持有对应资质")
        else:
            crit.append("推送金融/医疗等需资质内容但未确认资质：涉及荐股、荐基、保险、"
                        "医疗健康的内容须持牌，请确认资质后再推送")
            items.append("- 资质内容推送：未确认资质（阻断）")
    elif sens is False:
        items.append("- 资质内容推送：不涉及金融/医疗等需资质内容")
    else:
        items.append("- 资质内容推送：未确认")
    return items, crit, risk


def check_data(f):
    """客户数据与会话存档合规核查。"""
    items, crit, risk = [], [], []
    inherit = yesno(get_text(f, "是否配置离职继承与客户分配"))
    archive = yesno(get_text(f, "是否使用会话存档功能"))
    arch_notice = yesno(get_text(f, "会话存档是否告知员工与客户"))
    notice = yesno(get_text(f, "客户信息使用是否告知并取得同意"))

    if inherit is False:
        risk.append("未配置离职继承与客户分配：客户是企业资产，员工离职未继承将导致客户流失"
                    "与纠纷，应在管理后台配置离职继承规则")
        items.append("- 离职继承/客户分配：未配置（风险）")
    elif inherit is True:
        items.append("- 离职继承/客户分配：已配置")
    else:
        items.append("- 离职继承/客户分配：未确认")

    if archive is True:
        if arch_notice is False:
            crit.append("使用会话存档但未告知员工与客户：会话存档须事先向员工与客户告知并取得同意，"
                        "未告知的存档内容不得作为争议处理依据，且涉嫌违反个人信息保护要求")
            items.append("- 会话存档告知：未告知（阻断）")
        elif arch_notice is True:
            items.append("- 会话存档告知：已告知")
        else:
            crit.append("使用会话存档但未确认是否已告知：存档前应完成员工与客户的告知与同意，请确认")
            items.append("- 会话存档告知：未确认（阻断）")
    else:
        items.append("- 会话存档：未使用")

    if notice is False:
        risk.append("客户信息使用未告知并取得同意：使用客户手机号、行为数据等应告知处理目的、"
                    "方式与范围并取得同意，群发/营销触达应允许客户退订")
        items.append("- 客户信息使用告知：未告知（风险）")
    elif notice is True:
        items.append("- 客户信息使用告知：已告知并取得同意")
    else:
        items.append("- 客户信息使用告知：未确认")
    return items, crit, risk


def check_record(f):
    """投诉与处罚记录核查。"""
    items, risk = [], []
    comp = yesno(get_text(f, "是否收到过投诉或账号限制"))

    if comp is True:
        risk.append("收到过投诉或账号限制：私域运营投诉（骚扰、欺诈、诱导分享）将导致"
                    "功能限制乃至封号，应先整改加粉与群发动作、建立投诉响应机制再恢复运营")
        items.append("- 投诉与限制记录：有（风险）")
    elif comp is False:
        items.append("- 投诉与限制记录：无")
    else:
        items.append("- 投诉与限制记录：未确认")
    return items, risk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="")
    args = ap.parse_args()
    f = parse_md(args.path)
    if not f or not any(filled(v) for v in f.values()):
        print("# 待补正\n\n未读取到任何有效字段，请填写采集表后再核查。")
        return 2

    crit, risk, sections = [], [], []
    subj = get_text(f, "企业主体类型")

    header = "# 企业微信私域运营合规核查报告"
    if filled(subj):
        header += "（%s）" % subj
    sections.append(header)
    sections.append("")

    acc_items, acc_c, acc_r = check_account(f)
    crit += acc_c; risk += acc_r
    add_items, add_c, add_r = check_addfans(f)
    crit += add_c; risk += add_r
    ind_items, ind_c, ind_r = check_induce(f)
    crit += ind_c; risk += ind_r
    mas_items, mas_r = check_mass(f)
    risk += mas_r
    con_items, con_c, con_r = check_content(f)
    crit += con_c; risk += con_r
    dat_items, dat_c, dat_r = check_data(f)
    crit += dat_c; risk += dat_r
    rec_items, rec_r = check_record(f)
    risk += rec_r

    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"
    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险与待办项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(subj):
        summary += "- 企业主体：%s\n" % subj
    summary += ("- 处置建议：先停用外挂与违规加粉、杜绝诱导分享，再确认内容资质与"
                "会话存档告知，最后完善离职继承、群发频次与客户信息告知。\n")
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 账号与客户联系功能核查\n" + "\n".join(acc_items) + "\n\n"
    body += "### 加粉合规核查（外挂/名单来源/方式）\n" + "\n".join(add_items) + "\n\n"
    body += "### 诱导分享与裂变核查\n" + "\n".join(ind_items) + "\n\n"
    body += "### 群发与客户朋友圈核查\n" + "\n".join(mas_items) + "\n\n"
    body += "### 推送内容资质核查\n" + "\n".join(con_items) + "\n\n"
    body += "### 客户数据与会话存档核查\n" + "\n".join(dat_items) + "\n\n"
    body += "### 投诉与处罚记录核查\n" + "\n".join(rec_items) + "\n"
    sections.append(body)

    rb = "## 三、阻断项与风险/待办\n\n"
    if crit:
        rb += "### 阻断项（必须处理，否则面临限制功能/封号/法律风险）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险/待办项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "各核查项均满足，建议定期对照企业微信最新规范自查。\n\n"
    sections.append(rb)

    adv = ("## 四、整改操作指引（私域合规清单）\n\n"
           "1. 停用外挂：立即停用任何自动加人、自动群发、爬虫类工具，改用官方接口与合规功能。\n"
           "2. 合规加粉：只用渠道活码、门店物料、名片等自有合法渠道，销毁购买/爬取的名单来源。\n"
           "3. 杜绝诱导分享：取消红包裂变、集赞、砍价、助力、分享解锁等诱导分享玩法。\n"
           "4. 触达频次：控制群发频次，按标签分层精准触达；客户朋友圈遵守平台频次限制。\n"
           "5. 内容资质：金融荐股/荐基/保险、医疗健康内容须持牌主体与对应资格，无资质不推送。\n"
           "6. 数据合规：客户信息使用告知并取得同意，提供退订；配置离职继承保护客户资产。\n"
           "7. 会话存档：如使用须事先告知员工与客户并取得同意，留存告知记录。\n"
           "8. 投诉机制：建立投诉响应与处理 SOP，定期对照《企业微信使用规范》复盘。\n\n")
    sections.append(adv)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据《个人信息保护法》《微信外部链接内容管理规范》《企业微信使用规范》"
                "及客户端使用规则等公开资料整理，**不替代企业微信官方规范与审核结论**，"
                "以官方最新规则为准。\n"
                "- 严禁使用外挂/爬虫/自动化工具，严禁购买或非法获取客户名单（涉嫌侵犯公民个人信息罪）。\n"
                "- 严禁诱导分享、诱导下载等违规玩法；金融/医疗等内容推送须持牌资质。\n"
                "- 本报告不构成法律意见；涉及刑事风险与重大合规事项请立即咨询律师。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
