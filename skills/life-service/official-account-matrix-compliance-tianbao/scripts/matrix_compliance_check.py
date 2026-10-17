# -*- coding: utf-8 -*-
"""公众号矩阵合规核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、主体一致性、账号类型与认证、矩阵互推导流、
      诱导关注/分享、原创与转载授权、名称与品牌、数据打通隐私、特殊类目资质、
      历史违规牵连、阻断项与风险清单、运营合规建议、边界。

只做核查指引，不替代微信公众平台官方审核结论。
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
    "矩阵账号数量": ["矩阵账号数量", "账号数量", "公众号数量", "矩阵规模"],
    "账号主体类型": ["账号主体类型", "主体类型", "矩阵主体类型"],
    "矩阵账号主体是否一致": ["矩阵账号主体是否一致", "主体是否一致", "各账号主体一致", "主体一致性"],
    "账号类型分布": ["账号类型分布", "账号类型", "订阅号/服务号", "账号构成"],
    "是否完成微信认证": ["是否完成微信认证", "是否认证", "微信认证", "是否已认证"],
    "矩阵间是否互推或互相引流": ["矩阵间是否互推或互相引流", "是否互推", "互相引流", "矩阵互推", "是否引流"],
    "互推方式": ["互推方式", "引流方式", "互推形式", "导流方式"],
    "是否存在诱导关注/分享/集赞": ["是否存在诱导关注/分享/集赞", "是否诱导", "诱导关注", "诱导分享", "集赞", "诱导行为"],
    "内容是否原创为主": ["内容是否原创为主", "是否原创为主", "原创比例", "内容原创性"],
    "转载是否获授权": ["转载是否获授权", "转载授权", "是否授权转载", "二次转载授权"],
    "是否使用原创声明": ["是否使用原创声明", "原创声明", "是否声明原创"],
    "名称是否涉及品牌或他人商标": ["名称是否涉及品牌或他人商标", "名称侵权", "商标", "品牌名称", "是否仿冒"],
    "矩阵间是否打通用户数据": ["矩阵间是否打通用户数据", "用户数据打通", "数据打通", "跨账号数据", "数据共享"],
    "是否有特殊类目内容": ["是否有特殊类目内容", "特殊类目", "是否涉及特殊内容", "高敏内容"],
    "特殊类目资质是否齐备": ["特殊类目资质是否齐备", "资质是否齐备", "类目资质齐备", "跨账号资质"],
    "是否有账号曾违规或被封": ["是否有账号曾违规或被封", "历史违规", "曾被封", "账号被处罚", "是否封号"],
    "是否涉及诱导下载或站外导流": ["是否涉及诱导下载或站外导流", "诱导下载", "站外导流", "外链导流"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

SPECIAL_CAT = {
    "医疗": "须《医疗机构执业许可证》；互联网诊疗须另行审批",
    "药品": "须《药品经营许可证》",
    "医疗器械": "须《医疗器械经营许可证》或备案凭证",
    "食品": "须《食品经营许可证》或《食品生产许可证》",
    "金融": "须金融业务许可或备案，须持牌",
    "证券": "须《证券投资咨询》或《经营证券期货业务许可证》",
    "基金": "须基金销售业务资格",
    "保险": "须《经营保险业务许可证》或《保险中介许可证》",
    "新闻": "须《互联网新闻信息服务许可》（个人不得采编）",
    "出版": "须《出版物经营许可证》",
    "教育培训": "学科类须《办学许可证》",
    "时政": "时政新闻采编须《互联网新闻信息服务许可》",
}

INDUCE_WORDS = ("诱导", "集赞", "分享得", "关注得", "转发得", "抽奖", "裂变", "强制分享",
                "诱导分享", "诱导关注", "利诱", "红包拉新", "砍价", "助力")

NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法", "没")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "可以", "做过", "部分", "部分完成")


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


def parse_num(text):
    if unknown(text):
        return None
    m = re.search(r"\d+", str(text))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def has_special_cat(text):
    if unknown(text):
        return None
    n = norm(text)
    best = None
    for w in sorted(SPECIAL_CAT, key=len, reverse=True):
        if w in n:
            best = w
            break
    return best


def classify_subject(text):
    if unknown(text):
        return None
    n = norm(text)
    if any(k in n for k in ("企业", "公司")):
        return "enterprise"
    if any(k in n for k in ("个体", "工商户")):
        return "individual"
    if any(k in n for k in ("个人", "自然人")):
        return "personal"
    return "other"


def check_subject(f):
    items = []
    crit = []
    risk = []
    subj = classify_subject(get_text(f, "账号主体类型"))
    items.append("- 账号主体类型：%s" % (get_text(f, "账号主体类型") if filled(get_text(f, "账号主体类型")) else "未填"))
    consistent = yesno(get_text(f, "矩阵账号主体是否一致"))
    if consistent is False:
        crit.append("矩阵账号主体不一致：同一品牌矩阵应使用一致或关联主体，"
                    "混用个人/企业主体、借用他人主体易被认定违规，且一处违规牵连全矩阵")
        items.append("- 矩阵主体一致性：不一致（阻断）")
    elif consistent is True:
        items.append("- 矩阵主体一致性：一致")
    else:
        risk.append("未确认矩阵账号主体是否一致：请核对各账号主体，建议统一或明确关联关系，避免混用主体")
        items.append("- 矩阵主体一致性：未确认（风险）")
    if subj == "personal":
        risk.append("个人主体运营商业矩阵：个人号商业变现/互推受限，建议用企业/个体主体注册服务号或认证订阅号")
        items.append("- 主体性质：个人主体（矩阵商业化风险）")
    elif subj:
        items.append("- 主体性质：%s" % ("企业" if subj == "enterprise" else "个体工商户"))
    return items, crit, risk


def check_account_type(f):
    items = []
    risk = []
    dist = get_text(f, "账号类型分布")
    if filled(dist):
        items.append("- 账号类型分布：%s" % dist)
    auth = yesno(get_text(f, "是否完成微信认证"))
    if auth is False:
        risk.append("矩阵账号未完成微信认证：未认证账号功能受限、信任度低，"
                    "部分类目与接口须认证，建议核心账号完成认证")
        items.append("- 微信认证：否（风险）")
    elif auth is True:
        items.append("- 微信认证：是")
    else:
        risk.append("未确认是否完成微信认证：核心账号建议认证，提升信任与功能权限")
        items.append("- 微信认证：未确认（风险）")
    return items, risk


def check_mutual_promo(f):
    items = []
    crit = []
    risk = []
    mutual = yesno(get_text(f, "矩阵间是否互推或互相引流"))
    way = get_text(f, "互推方式")
    if mutual is True or filled(way):
        items.append("- 矩阵互推/引流：是")
        if filled(way):
            items.append("  - 互推方式：%s" % way)
            wn = norm(way)
            if any(k in wn for k in ("强制", "必须", "不转发", "集赞", "诱导")):
                crit.append("互推方式含强制/诱导成分（如强制转发、集赞）："
                            "属诱导分享违规，会被限制传播乃至封号")
                items.append("  - 互推方式：含强制/诱导（阻断）")
            elif any(k in wn for k in ("文末", "菜单", "阅读原文", "二维码", "推荐")):
                items.append("  - 互推方式：常规（文末/菜单/二维码，须避免诱导措辞）")
        else:
            risk.append("矩阵互推但未说明方式：请用文末推荐、菜单跳转等常规方式，避免强制转发/集赞等诱导")
            items.append("  - 互推方式：未说明（风险）")
    elif mutual is False:
        items.append("- 矩阵互推/引流：否")
    else:
        items.append("- 矩阵互推/引流：未确认")
    return items, crit, risk


def check_induce(f):
    items = []
    crit = []
    risk = []
    induce = yesno(get_text(f, "是否存在诱导关注/分享/集赞"))
    if induce is True:
        crit.append("存在诱导关注/分享/集赞：微信严禁利诱分享、集赞、强制关注，"
                    "违规会被删除内容、限制功能乃至封号")
        items.append("- 诱导关注/分享/集赞：是（阻断）")
    elif induce is False:
        items.append("- 诱导关注/分享/集赞：否")
    else:
        risk.append("未确认是否存在诱导行为：请排查集赞、分享得福利、强制关注等动作")
        items.append("- 诱导关注/分享/集赞：未确认（风险）")

    dl = yesno(get_text(f, "是否涉及诱导下载或站外导流"))
    if dl is True:
        risk.append("涉及诱导下载/站外导流：过度站外导流或诱导下载会被限制，"
                    "应通过合规组件引导")
        items.append("- 诱导下载/站外导流：是（风险）")
    elif dl is False:
        items.append("- 诱导下载/站外导流：否")
    else:
        items.append("- 诱导下载/站外导流：未确认")
    return items, crit, risk


def check_content(f):
    items = []
    crit = []
    risk = []
    original = yesno(get_text(f, "内容是否原创为主"))
    if original is True:
        items.append("- 内容原创为主：是")
    elif original is False:
        risk.append("内容非原创为主：矩阵大量搬运易被判定低质/侵权，建议原创为主、适量授权转载")
        items.append("- 内容原创为主：否（风险）")
    else:
        risk.append("未确认内容是否原创为主：原创度影响推荐权重与侵权风险")
        items.append("- 内容原创为主：未确认（风险）")

    auth = yesno(get_text(f, "转载是否获授权"))
    decl = yesno(get_text(f, "是否使用原创声明"))
    if auth is False:
        crit.append("转载未获授权：未经授权转载他人内容侵犯版权，会被投诉下架、扣除信用分，"
                    "须取得授权并标注来源")
        items.append("- 转载授权：否（阻断）")
    elif auth is True:
        items.append("- 转载授权：是")
    else:
        risk.append("未确认转载是否获授权：转载须获授权并注明出处，否则侵权风险")
        items.append("- 转载授权：未确认（风险）")
    if decl is True:
        items.append("- 原创声明：使用")
    elif decl is False:
        items.append("- 原创声明：未使用")
    else:
        items.append("- 原创声明：未确认")
    return items, crit, risk


def check_brand(f):
    items = []
    crit = []
    risk = []
    brand = yesno(get_text(f, "名称是否涉及品牌或他人商标"))
    if brand is True:
        crit.append("账号名称涉及品牌/他人商标：未获授权的仿冒、碰瓷名称会被投诉封号，"
                    "须使用自有品牌或获授权")
        items.append("- 名称品牌/商标：涉及（阻断）")
    elif brand is False:
        items.append("- 名称品牌/商标：不涉及")
    else:
        risk.append("未确认名称是否涉及他人商标：请自查避免仿冒、碰瓷，防止被投诉")
        items.append("- 名称品牌/商标：未确认（风险）")
    return items, crit, risk


def check_data(f):
    items = []
    risk = []
    data_link = yesno(get_text(f, "矩阵间是否打通用户数据"))
    if data_link is True:
        risk.append("矩阵间打通用户数据：跨账号共享用户个人信息须满足最小必要与告知同意，"
                    "并在隐私指引中说明，避免违规收集")
        items.append("- 用户数据打通：是（隐私合规风险）")
    elif data_link is False:
        items.append("- 用户数据打通：否")
    else:
        items.append("- 用户数据打通：未确认")
    return items, risk


def check_category(f):
    items = []
    crit = []
    risk = []
    sc = yesno(get_text(f, "是否有特殊类目内容"))
    if sc is True:
        items.append("- 特殊类目内容：涉及")
        lic = yesno(get_text(f, "特殊类目资质是否齐备"))
        if lic is False:
            crit.append("矩阵发布特殊类目内容（医疗/金融/新闻等）但资质未齐备："
                        "须各账号均持对应资质，否则下架乃至封号")
            items.append("  - 跨账号资质：未齐备（阻断）")
        elif lic is True:
            items.append("  - 跨账号资质：已齐备")
        else:
            risk.append("涉及特殊类目但未确认跨账号资质：请各账号均上传有效期内对应许可")
            items.append("  - 跨账号资质：未确认（风险）")
    elif sc is False:
        items.append("- 特殊类目内容：不涉及")
    else:
        risk.append("未确认是否涉及特殊类目内容：若涉医疗/财经/新闻须资质，请明确")
        items.append("- 特殊类目内容：未确认（风险）")
    return items, crit, risk


def check_account_risk(f):
    items = []
    risk = []
    viol = yesno(get_text(f, "是否有账号曾违规或被封"))
    if viol is True:
        risk.append("矩阵内有账号曾违规/被封：同一主体/矩阵下账号互相关联，"
                    "单账号严重违规会牵连主体权重与整体推荐，须重点整改")
        items.append("- 历史违规/封号：有（牵连风险）")
    elif viol is False:
        items.append("- 历史违规/封号：无")
    else:
        items.append("- 历史违规/封号：未确认")
    cnt = parse_num(get_text(f, "矩阵账号数量"))
    if cnt is not None:
        items.append("- 矩阵账号数量：%d" % int(cnt))
        if cnt > 50:
            risk.append("矩阵账号数量较多（%d）：大规模矩阵易被风控识别为营销号矩阵，"
                        "须保证内容差异化、主体清晰、无批量违规" % int(cnt))
            items.append("  - 规模：偏大（风控关注）")
    else:
        items.append("- 矩阵账号数量：未填")
    return items, risk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="")
    args = ap.parse_args()
    f = parse_md(args.path)
    if not f or not any(filled(v) for v in f.values()):
        print("# 待补正\n\n未读取到任何有效字段，请填写采集表后再核查。")
        return 2

    crit = []
    risk = []
    sections = []

    header = "# 公众号矩阵合规核查报告"
    subj = get_text(f, "账号主体类型")
    if filled(subj):
        header += "（%s）" % subj
    sections.append(header)
    sections.append("")

    s_items, s_c, s_r = check_subject(f)
    crit += s_c
    risk += s_r
    at_items, at_r = check_account_type(f)
    risk += at_r
    mp_items, mp_c, mp_r = check_mutual_promo(f)
    crit += mp_c
    risk += mp_r
    ind_items, ind_c, ind_r = check_induce(f)
    crit += ind_c
    risk += ind_r
    ct_items, ct_c, ct_r = check_content(f)
    crit += ct_c
    risk += ct_r
    br_items, br_c, br_r = check_brand(f)
    crit += br_c
    risk += br_r
    dt_items, dt_r = check_data(f)
    risk += dt_r
    cat_items, cat_c, cat_r = check_category(f)
    crit += cat_c
    risk += cat_r
    ar_items, ar_r = check_account_risk(f)
    risk += ar_r

    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"
    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(subj):
        summary += "- 账号主体类型：%s\n" % subj
    summary += "- 处置建议：先消除全部阻断项（主体一致性、诱导、侵权、无资质），再处理矩阵运营风险。\n"
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 主体一致性\n" + "\n".join(s_items) + "\n\n"
    body += "### 账号类型与认证\n" + "\n".join(at_items) + "\n\n"
    body += "### 矩阵互推与导流\n" + "\n".join(mp_items) + "\n\n"
    body += "### 诱导关注/分享/下载\n" + "\n".join(ind_items) + "\n\n"
    body += "### 原创与转载授权\n" + "\n".join(ct_items) + "\n\n"
    body += "### 名称与品牌合规\n" + "\n".join(br_items) + "\n\n"
    body += "### 用户数据打通隐私\n" + "\n".join(dt_items) + "\n\n"
    body += "### 特殊类目资质\n" + "\n".join(cat_items) + "\n\n"
    body += "### 历史违规与规模\n" + "\n".join(ar_items) + "\n"
    sections.append(body)

    rb = "## 三、阻断项与风险清单\n\n"
    if crit:
        rb += "### 阻断项（必须处理，否则违规/封号）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "未发现明显阻断或风险项，矩阵合规度良好。\n\n"
    sections.append(rb)

    adv = ("## 四、矩阵运营合规建议\n\n"
           "1. 主体统一：矩阵账号使用一致或明确关联的认证主体，避免混用个人/借用主体。\n"
           "2. 杜绝诱导：不集赞、不强制转发、不利诱分享关注，互推用文末/菜单/二维码等常规方式。\n"
           "3. 内容原创：以原创为主，转载须授权并标注来源，规范使用原创声明。\n"
           "4. 品牌自查：账号名称避免仿冒、碰瓷他人商标，使用自有或获授权品牌。\n"
           "5. 资质齐备：跨账号发布特殊类目须各账号均持有效资质。\n"
           "6. 数据合规：跨账号打通用户数据须最小必要、告知同意并写入隐私指引。\n"
           "7. 风险隔离：单账号严重违规会牵连主体矩阵，重点账号重点养护。\n\n")
    sections.append(adv)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据通用规则与公开参考整理，不替代微信公众平台官方审核结论。\n"
                "- 矩阵合规、诱导认定、封号判定最终以微信公众平台规则与处置结果为准。\n"
                "- 不承诺矩阵一定不被限流或封号；最终以平台处置结果为准。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
