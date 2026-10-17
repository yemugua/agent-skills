# -*- coding: utf-8 -*-
"""小程序广告与流量主合规核查脚本（小程序广告变现 / 流量主向）。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、流量主接入资质、广告位与形式合规、广告内容合规、
      个性化广告与数据合规、未成年人与诱导营销、结算税务与平台规则、
      整改操作指引、边界。

只做合规核查与整改指引，不替代监管规定、微信平台规则与正式法律意见。
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
    "subject": ["主体类型", "小程序主体", "账号主体", "主体", "开发者类型"],
    "online": ["小程序是否已上线", "是否上线", "上线状态", "是否已发布", "运营状态"],
    "has_ad": ["是否接入广告或流量主", "是否接广告", "是否开通流量主", "广告/流量主", "接入广告", "流量主"],
    "ad_type": ["广告形式", "广告类型", "流量主广告形式", "广告位形式", "广告样式"],
    "is_individual": ["主体是否个人", "是否为个人主体", "个人主体", "主体性质"],
    "induce_click": ["是否存在诱导点击", "诱导点击", "诱导点击行为", "误导点击", "伪装按钮", "虚假按钮"],
    "fake_click": ["是否有虚假点击或刷量", "虚假点击", "刷量", "机器点击", "恶意点击", "刷流量", "点击作弊"],
    "reward_gated": ["是否强制观看广告才能使用功能", "功能捆绑广告", "看广告才能用", "强制看广告", "激励视频捆绑"],
    "ad_distinct": ["广告是否与内容明确区分或标识", "广告标识", "广告区分", "是否标明广告", "广告标注"],
    "ad_content_check": ["是否审核广告主资质与广告内容", "广告主资质审核", "广告内容审核", "审核广告", "广告审核"],
    "extreme_words": ["广告是否使用极限词或绝对化用语", "极限词", "绝对化用语", "夸大用语", "最/第一"],
    "forbidden_cat": ["是否涉及需资质的广告类目(医疗/药品/保健/金融等)", "需资质类目", "特殊类目广告", "医疗广告", "金融广告", "保健广告"],
    "forbidden_license": ["这些类目是否具备相应资质", "类目资质", "广告资质", "特殊类目资质", "经营许可"],
    "personalized_ad": ["是否使用个性化广告", "个性化广告", "精准广告", "定向广告", "个性化推荐", "精准投放"],
    "ad_consent": ["个性化广告是否告知并取得同意", "个性化广告告知", "个性化同意", "广告授权告知", "个性化授权"],
    "minor_ad": ["是否有未成年人广告限制", "未成年人广告", "青少年广告限制", "未成年广告保护", "未成年广告"],
    "ad_share_induce": ["是否用分享或拉新换广告收益并诱导", "分享换收益", "拉新换广告", "诱导分享广告", "点击广告支持", "分享得收益"],
    "settlement": ["结算与税务是否合规", "流量主结算", "广告收益结算", "税务合规", "提现税务", "结算税务"],
    "violation": ["是否有违规或处罚历史", "违规历史", "处罚历史", "被封流量主", "违规记录", "封禁记录"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

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


def check_qualification(f):
    """流量主接入资质核查。"""
    items, crit, risk = [], [], []
    has_ad = yesno(get_text(f, "has_ad"))
    if has_ad is False:
        items.append("- 广告/流量主接入：当前未接入（以下为未来接入的前置资质要点）")
        items.append("- 流量主开通门槛：需满足平台当前累计独立访问用户等开通条件，且主体已完成认证")
        return items, crit, risk
    if has_ad is None:
        items.append("- 广告/流量主接入：未确认")
    else:
        items.append("- 广告/流量主接入：已接入")

    subj = get_text(f, "subject")
    is_ind = yesno(get_text(f, "is_individual"))
    # 个人主体判断：显式"个人"或主体类型含"个人"
    if filled(subj) and norm(subj).startswith("个人"):
        is_ind = True
    if is_ind is True:
        crit.append("主体为个人却接入广告/流量主：微信流量主仅向已完成认证的企业或个体工商户开放，"
                    "个人主体无法合规开通流量主，须先用企业/个体户资质注册或变更主体，否则收益无法结算且违规")
        items.append("- 主体资质：个人主体（阻断）")
    elif is_ind is False:
        items.append("- 主体资质：企业/个体工商户（合规）")
    else:
        if filled(subj):
            items.append("- 主体资质：%s（请确认非个人主体）" % subj)
        else:
            risk.append("未确认主体类型：流量主要求企业或个体工商户主体，个人主体不可开通，请确认并补充主体资质")
            items.append("- 主体资质：未确认（风险）")

    if is_ind is None:
        risk.append("未确认主体类型与开通门槛：流量主要求企业或个体工商户主体并满足平台当前开通条件，"
                    "个人主体不可开通，请确认资质并不得刷量冲量")
        items.append("- 主体资质/开通门槛：未确认（风险）")
    else:
        items.append("- 开通门槛：满足平台当前条件（已接入即默认达标，勿刷量冲量）")
    return items, crit, risk


def check_placement(f):
    """广告位与形式合规核查。"""
    items, crit, risk = [], [], []
    ad_type = get_text(f, "ad_type")
    if filled(ad_type):
        items.append("- 广告形式：%s" % ad_type)
    induce = yesno(get_text(f, "induce_click"))
    if induce is True:
        crit.append("存在诱导点击/误导点击/伪装成功能按钮/虚假关闭按钮等行为：平台对欺骗性点击零容忍，"
                    "触发即可能清退广告位、封禁流量主权限并追回收益")
        items.append("- 诱导/误导点击：存在（阻断）")
    elif induce is False:
        items.append("- 诱导/误导点击：不存在")
    else:
        risk.append("未确认是否存在诱导点击：广告点击须用户真实意愿，不得用虚假按钮、伪装功能入口、"
                    "倒计时误导等方式骗取点击")
        items.append("- 诱导/误导点击：未确认（风险）")

    fake = yesno(get_text(f, "fake_click"))
    if fake is True:
        crit.append("存在虚假点击/刷量/机器点击/恶意点击：属严重作弊，平台检测即封禁流量主权限、"
                    "清零/追回收益并可能追究责任，必须杜绝")
        items.append("- 虚假点击/刷量：存在（阻断）")
    elif fake is False:
        items.append("- 虚假点击/刷量：不存在")
    else:
        risk.append("未确认是否存在虚假点击/刷量：不得自点、互点、接刷量服务，"
                    "异常点击率会触发平台风控")
        items.append("- 虚假点击/刷量：未确认（风险）")

    gated = yesno(get_text(f, "reward_gated"))
    if gated is True:
        crit.append("强制观看广告才能使用核心功能：微信禁止以观看激励视频/广告作为使用小程序核心功能的前提，"
                    "广告激励只能用于去广告、解锁增值/装饰等可选功能，否则会被限制广告能力乃至下架")
        items.append("- 功能捆绑广告（强制看广告才能用核心功能）：存在（阻断）")
    elif gated is False:
        items.append("- 功能捆绑广告：不存在")
    else:
        items.append("- 功能捆绑广告：未确认")

    distinct = yesno(get_text(f, "ad_distinct"))
    if distinct is False:
        risk.append("广告未与内容明确区分/未标识「广告」：用户应可识别广告位，"
                    "建议所有广告位明确标注「广告」字样并与正文/功能区隔")
        items.append("- 广告标识：未明确（风险）")
    elif distinct is True:
        items.append("- 广告标识：已明确标注")
    else:
        items.append("- 广告标识：未确认")
    return items, crit, risk


def check_content(f):
    """广告内容合规核查（广告法/平台规则）。"""
    items, crit, risk = [], [], []
    chk = yesno(get_text(f, "ad_content_check"))
    if chk is False:
        risk.append("未审核广告主资质与广告内容：作为流量主/广告发布方对展示内容负有审核义务，"
                    "应核验广告主资质与广告素材合法合规，留存审核记录")
        items.append("- 广告主/内容审核：未审核（风险）")
    elif chk is True:
        items.append("- 广告主/内容审核：已审核")
    else:
        risk.append("未确认是否审核广告主资质与广告内容：建议建立广告审核流程并留存记录")
        items.append("- 广告主/内容审核：未确认（风险）")

    ext = yesno(get_text(f, "extreme_words"))
    if ext is True:
        crit.append("广告使用极限词/绝对化用语（如「最」「第一」「国家级」「顶级」等）：违反《广告法》"
                    "第九条，面临行政处罚与平台处罚，必须删除并整改文案")
        items.append("- 极限词/绝对化用语：存在（阻断）")
    elif ext is False:
        items.append("- 极限词/绝对化用语：不存在")
    else:
        risk.append("未确认广告是否含极限词/绝对化用语：广告文案不得使用「最/第一/国家级/顶级」等，"
                    "须自查并规避夸大表述")
        items.append("- 极限词/绝对化用语：未确认（风险）")

    fcat = yesno(get_text(f, "forbidden_cat"))
    if fcat is True:
        lic = yesno(get_text(f, "forbidden_license"))
        if lic is False:
            crit.append("广告涉及医疗/药品/保健品/医疗器械/金融/烟酒等需资质类目但无相应资质："
                        "此类广告须取得对应审批/经营许可（如医疗广告审查批准文、金融业务资质），"
                        "无资质投放属违规，平台会拒登并可能处罚")
            items.append("- 需资质类目广告：涉及且无资质（阻断）")
        elif lic is True:
            items.append("- 需资质类目广告：涉及且具备资质")
        else:
            crit.append("广告涉及需资质类目但未确认资质：医疗/药品/保健/金融/烟酒等类目广告须持相应审批与许可，"
                        "请确认已取得并展示，否则不得投放")
            items.append("- 需资质类目广告：涉及且未确认资质（阻断）")
    elif fcat is False:
        items.append("- 需资质类目广告：不涉及")
    else:
        items.append("- 需资质类目广告：未确认")
    return items, crit, risk


def check_personalized(f):
    """个性化广告与数据合规核查（与隐私合规衔接）。"""
    items, crit, risk = [], [], []
    pa = yesno(get_text(f, "personalized_ad"))
    if pa is False:
        items.append("- 个性化广告：未使用（走通用广告即可，无需额外告知）")
        return items, crit, risk
    if pa is None:
        items.append("- 个性化广告：未确认")
        return items, crit, risk
    items.append("- 个性化广告：使用（须告知并取得同意，另见隐私合规核查）")
    consent = yesno(get_text(f, "ad_consent"))
    if consent is False:
        crit.append("使用个性化广告但未向用户告知并取得同意：基于用户画像的精准投放属个人信息处理，"
                    "须依《个人信息保护法》在隐私指引中告知、取得同意并提供关闭个性化广告的选项，"
                    "否则违规（与隐私合规核查联动）")
        items.append("- 个性化广告告知与同意：未取得（阻断）")
    elif consent is True:
        items.append("- 个性化广告告知与同意：已取得并提供关闭选项")
    else:
        crit.append("使用个性化广告但未确认是否告知并取得同意：请确认隐私指引已说明个性化广告、"
                    "已获同意且提供关闭入口")
        items.append("- 个性化广告告知与同意：未确认（阻断）")
    return items, crit, risk


def check_minor_marketing(f):
    """未成年人与诱导营销核查。"""
    items, crit, risk = [], [], []
    minor = yesno(get_text(f, "minor_ad"))
    if minor is False:
        risk.append("未设置未成年人广告限制：不得向未成年人推送烟酒、成人、高风险消费等不适宜广告，"
                    "不得诱导未成年人点击广告或消费，建议启用未成年保护过滤")
        items.append("- 未成年人广告限制：未设置（风险）")
    elif minor is True:
        items.append("- 未成年人广告限制：已设置")
    else:
        items.append("- 未成年人广告限制：未确认")

    share_induce = yesno(get_text(f, "ad_share_induce"))
    if share_induce is True:
        crit.append("用「分享/拉新换广告收益」并诱导分享：以广告收益为诱饵诱导用户分享、拉新、点击，"
                    "触碰微信诱导分享红线（与内容安全/私域合规衔接），触发即可能封禁分享接口与广告能力")
        items.append("- 分享/拉新换广告收益诱导：存在（阻断）")
    elif share_induce is False:
        items.append("- 分享/拉新换广告收益诱导：不存在")
    else:
        items.append("- 分享/拉新换广告收益诱导：未确认")
    return items, crit, risk


def check_settlement(f):
    """结算税务与平台规则核查。"""
    items, risk = [], []
    settle = yesno(get_text(f, "settlement"))
    if settle is False:
        risk.append("流量主结算与税务不合规：企业主体收益须合规入账并申报纳税，提现须绑定与主体一致的结算账户，"
                    "不得用个人账号截留公转，避免税务与平台结算风险")
        items.append("- 结算与税务：不合规（风险）")
    elif settle is True:
        items.append("- 结算与税务：合规")
    else:
        risk.append("未确认结算与税务合规性：建议核对平台结算规则、绑定正确结算主体并依法申报纳税")
        items.append("- 结算与税务：未确认（风险）")

    v = yesno(get_text(f, "violation"))
    if v is True:
        risk.append("存在违规/处罚历史（如曾被限流、清退广告位、封禁流量主）：须完成整改闭环并留存证据，"
                    "再次违规将加重处罚（清零收益/永久封禁），建议全量复查广告与机制后再继续投放")
        items.append("- 违规/处罚历史：有（风险）")
    elif v is False:
        items.append("- 违规/处罚历史：无")
    else:
        items.append("- 违规/处罚历史：未确认")
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
    subj_txt = get_text(f, "subject")
    online = get_text(f, "online")

    has_ad = yesno(get_text(f, "has_ad"))
    if has_ad is False:
        head = "# 小程序广告与流量主合规核查报告"
        if filled(subj_txt):
            head += "（%s）" % subj_txt
        if filled(online):
            head += " · 状态：%s" % online
        lines = [head, "",
                 "## 一、结论摘要\n",
                 "- 总体结论：**通过**（暂不涉及广告合规）\n",
                 "- 说明：当前未接入广告/流量主，无需广告合规整改；以下为未来接入的前置要点，供提前规划。\n"]
        if filled(subj_txt):
            lines.append("- 主体类型：%s\n" % subj_txt)
        lines += ["## 二、未来接入广告/流量主的前置合规要点\n",
                  "1. 主体须为企业或个体工商户（个人不可开通流量主），并完成认证、满足平台开通门槛。\n",
                  "2. 广告位须标明「广告」、禁止诱导/误导点击与虚假点击刷量、不得强制看广告才能用核心功能。\n",
                  "3. 广告文案禁用极限词，医疗/药品/保健/金融/烟酒等类目须持资质。\n",
                  "4. 个性化广告须告知同意并提供关闭选项（衔接隐私合规）。\n",
                  "5. 不向未成年人推送不适宜广告，不得用分享/拉新换广告收益诱导分享。\n",
                  "6. 绑定与主体一致结算账户，依法申报纳税。\n",
                  "\n## 三、边界与纪律\n",
                  "- 本核查依据《广告法》《个人信息保护法》及微信流量主规则公开规则整理，不替代正式法律意见。\n"]
        print("\n".join(lines))
        return 0

    header = "# 小程序广告与流量主合规核查报告"
    if filled(subj_txt):
        header += "（%s）" % subj_txt
    if filled(online):
        header += " · 状态：%s" % online
    sections.append(header)
    sections.append("")

    q_items, q_c, q_r = check_qualification(f)
    crit += q_c; risk += q_r
    p_items, p_c, p_r = check_placement(f)
    crit += p_c; risk += p_r
    c_items, c_c, c_r = check_content(f)
    crit += c_c; risk += c_r
    pa_items, pa_c, pa_r = check_personalized(f)
    crit += pa_c; risk += pa_r
    mm_items, mm_c, mm_r = check_minor_marketing(f)
    crit += mm_c; risk += mm_r
    s_items, s_r = check_settlement(f)
    risk += s_r

    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"
    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险与待办项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(subj_txt):
        summary += "- 主体类型：%s\n" % subj_txt
    summary += ("- 处置建议：先确认主体为可开通流量主的企业/个体户，再清除诱导点击、虚假点击与强制捆绑广告，"
                "整改广告文案极限词与需资质类目，落实个性化广告告知同意与未成年人保护，最后规范结算税务。\n")
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 流量主接入资质核查\n" + "\n".join(q_items) + "\n\n"
    body += "### 广告位与形式合规核查\n" + "\n".join(p_items) + "\n\n"
    body += "### 广告内容合规核查（广告法/平台规则）\n" + "\n".join(c_items) + "\n\n"
    body += "### 个性化广告与数据合规核查\n" + "\n".join(pa_items) + "\n\n"
    body += "### 未成年人与诱导营销核查\n" + "\n".join(mm_items) + "\n\n"
    body += "### 结算税务与平台规则核查\n" + "\n".join(s_items) + "\n"
    sections.append(body)

    rb = "## 三、阻断项与风险/待办\n\n"
    if crit:
        rb += "### 阻断项（必须处理，否则影响广告能力/流量主权限/合规）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险/待办项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "各核查项均满足，建议上线前再做一次全量自查并留存记录。\n\n"
    sections.append(rb)

    adv = ("## 四、整改操作指引（标准广告/流量主合规清单）\n\n"
           "1. 主体资质：确认小程序主体为企业或个体工商户（个人主体不可开通流量主），并已完成认证、满足开通门槛。\n"
           "2. 广告位合规：所有广告位明确标注「广告」、与内容区隔；不得诱导/误导点击、不得虚假按钮；"
           "严禁机器点击/刷量/互点等作弊。\n"
           "3. 禁止功能捆绑：激励视频/广告只能用于去广告、解锁装饰等可选功能，不得作为使用核心功能的前提。\n"
           "4. 广告内容审核：建立广告主资质与素材审核流程并留存记录；广告文案不得含「最/第一/国家级」等极限词；"
           "医疗/药品/保健/金融/烟酒等类目须持相应审批与许可方可投放。\n"
           "5. 个性化广告：若启用精准投放，须在隐私指引中告知、取得同意并提供关闭个性化广告的选项"
           "（与隐私合规核查联动）。\n"
           "6. 未成年人与诱导营销：不向未成年人推送不适宜/诱导消费广告；不得以「分享/拉新换广告收益」诱导分享"
           "（触碰诱导分享红线）。\n"
           "7. 结算税务：绑定与主体一致的结算账户，企业收益合规入账并依法申报纳税，避免公转私税务风险。\n\n")
    sections.append(adv)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据《广告法》《个人信息保护法》、微信小程序流量主相关规则与平台运营规范公开规则整理，"
                "**不替代监管规定、平台规则与正式法律意见**，重大场景请咨询律师。\n"
                "- 流量主仅向完成认证的企业/个体工商户开放，个人主体不可开通；虚假点击/刷量将清退权限并追回收益。\n"
                "- 广告内容须合法合规：禁用极限词、拒绝违禁类目无资质投放、明示「广告」、不得诱导/误导点击。\n"
                "- 个性化广告须告知同意并提供关闭选项；不得诱导分享或以广告收益利诱用户（与内容安全/私域合规衔接）。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
