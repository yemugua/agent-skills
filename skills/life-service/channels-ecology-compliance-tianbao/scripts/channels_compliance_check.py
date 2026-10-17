# -*- coding: utf-8 -*-
"""视频号内容运营合规与违规限流避坑核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、账号与领域、平台红线、违规与限流信号、
      变现合规、原创与版权、整改与运营建议、边界与纪律。

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
    "账号类型": ["账号类型", "视频号类型", "主体类型", "是否企业号"],
    "内容领域": ["内容领域", "内容方向", "垂直领域", "领域", "赛道"],
    "是否收到过违规通知": ["是否收到过违规通知", "是否违规", "有无违规", "是否收到违规", "被处罚"],
    "违规类型": ["违规类型", "违规原因", "处罚原因", "违规说明"],
    "收到违规通知次数": ["收到违规通知次数", "违规次数", "被罚次数"],
    "近期播放量是否异常下跌": ["近期播放量是否异常下跌", "流量是否下跌", "是否被限流", "播放量下跌", "流量异常"],
    "是否有带货或橱窗": ["是否有带货或橱窗", "是否带货", "是否有橱窗", "是否挂车", "带货功能"],
    "带货类目": ["带货类目", "带货品类", "销售类目", "商品类目"],
    "是否涉及医疗健康内容": ["是否涉及医疗健康内容", "是否做医疗", "是否健康科普", "是否医疗内容", "是否保健品"],
    "是否涉及财经荐股内容": ["是否涉及财经荐股内容", "是否荐股", "是否财经", "是否基金推荐", "财经内容"],
    "是否涉及时政新闻内容": ["是否涉及时政新闻内容", "是否发时政", "时政新闻", "是否新闻"],
    "是否原创内容": ["是否原创内容", "是否原创", "内容是否原创"],
    "是否搬运他人内容": ["是否搬运他人内容", "是否搬运", "是否转载", "是否抄袭"],
    "是否使用未授权音乐或素材": ["是否使用未授权音乐或素材", "未授权音乐", "音乐授权", "素材授权", "是否侵权素材"],
    "是否引导站外或私域": ["是否引导站外或私域", "是否引流", "是否引导加微信", "站外引流", "私域引流"],
    "是否配置了对应资质证件": ["是否配置了对应资质证件", "是否有资质", "资质情况", "是否持牌"],
    "更新频率": ["更新频率", "发布频率", "更新频次"],
    "平均完播率": ["平均完播率", "完播率", "播放完成率"],
    "是否有用户投诉或举报": ["是否有用户投诉或举报", "被举报", "被投诉", "用户举报"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

# 高敏领域 → 资质/红线提示
SENSITIVE_DOMAINS = {
    "医疗": "医疗健康内容须谨慎：个人/无资质不得发布医疗美容、药品疗效、诊疗建议；"
            "带货医疗器械、保健食品须对应经营/备案资质，医疗广告需审查",
    "健康": "健康科普不得替代诊疗建议、不得宣称疗效；带货保健食品须《食品经营许可证》等资质",
    "药品": "药品/医疗器械推广受严格限制，须持牌医药主体与广告审查，个人不得随意推广",
    "保健": "保健食品带货须食品经营资质，不得宣称疾病预防治疗功效",
    "财经": "财经荐股/基金推荐须持牌（证券投资咨询/基金销售资格），不得承诺收益、不得公开招揽",
    "证券": "证券期货内容须持牌机构与资格，个人不得公开荐股或代客理财",
    "基金": "基金推荐/销售须基金销售业务资格，不得承诺收益",
    "时政": "时政新闻采编须《互联网新闻信息服务许可》，个人不得采编发布时政新闻",
    "新闻": "新闻内容须资质，个人账号避免以新闻形式发布时政要闻",
    "美妆": "美妆带货须对应商品资质，涉及功效宣称需有依据，不得虚假夸大",
    "食品": "食品带货须《食品经营许可证》（预包装食品备案），不得虚假宣传",
    "游戏": "游戏相关内容注意版号与未成年人保护提示",
    "教育": "学科类培训须办学许可，职业培训须对应资质，注意广告合规",
}

NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法", "没")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "可以", "做过")


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
    """先对输入建 norm 索引，兼容已 norm 与未 norm 两种 key。"""
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


def has_domain(text):
    if unknown(text):
        return None
    n = norm(text)
    best = None
    for w in sorted(SENSITIVE_DOMAINS, key=len, reverse=True):
        if w in n:
            best = w
            break
    return best


def parse_num(text):
    if unknown(text):
        return None
    m = re.search(r"-?\d+(\.\d+)?", str(text))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def check_redline(f):
    items = []
    crit = []
    risk = []
    dom = get_text(f, "内容领域")
    hit = has_domain(dom)
    med = yesno(get_text(f, "是否涉及医疗健康内容"))
    fin = yesno(get_text(f, "是否涉及财经荐股内容"))
    news = yesno(get_text(f, "是否涉及时政新闻内容"))
    has_lic = yesno(get_text(f, "是否配置了对应资质证件"))
    if hit or med is True or fin is True or news is True:
        if hit:
            items.append("- 内容领域：%s（高敏领域）" % dom)
            items.append("  - 红线提示：%s" % SENSITIVE_DOMAINS[hit])
        if med is True:
            crit.append("涉及医疗健康内容且无对应资质：个人/无资质账号不得发布医疗美容、"
                        "药品疗效、诊疗建议类内容；带货医疗器械/保健食品须对应经营或备案资质，"
                        "且医疗广告须经审查，否则会被下架、限流甚至封号")
            items.append("- 医疗健康内容：涉及（阻断）")
        elif med is None and not hit:
            risk.append("未确认是否涉及医疗健康内容：若涉及须配置资质并规避疗效宣称与诊疗建议")
            items.append("- 医疗健康内容：未确认")
        if fin is True:
            crit.append("涉及财经荐股/基金推荐且无持牌资质：须持证券投资咨询/基金销售资格，"
                        "不得承诺收益、不得公开招揽，否则属违规导流且面临封号风险")
            items.append("- 财经荐股/基金：涉及（阻断）")
        elif fin is None and not hit:
            risk.append("未确认是否涉及财经荐股内容：若涉及须持牌，不得承诺收益")
            items.append("- 财经荐股/基金：未确认")
        if news is True:
            crit.append("涉及时政新闻内容：个人账号不得采编发布时政新闻，"
                        "须《互联网新闻信息服务许可》，否则违规")
            items.append("- 时政新闻：涉及（阻断）")
        elif news is None and not hit:
            risk.append("未确认是否涉及时政新闻：个人账号避免以新闻形式发布时政要闻")
            items.append("- 时政新闻：未确认")
        if has_lic is False and (med is True or fin is True or news is True or hit in ("医疗", "药品", "保健", "财经", "证券", "基金", "时政", "新闻")):
            crit.append("高敏领域内容未配置对应资质证件：须先在资质管理中上传有效期内的"
                        "执业许可/经营许可/持牌证明，否则审核不通过且可能封号")
            items.append("  - 资质证件：未配置（阻断）")
        elif has_lic is True and (med is True or fin is True or news is True):
            items.append("  - 资质证件：已配置")
        elif has_lic is None and (med is True or fin is True or news is True):
            risk.append("未确认是否已配置高敏领域资质证件：请上传并在有效期内")
            items.append("  - 资质证件：未确认")
    else:
        if hit is None and med is None and fin is None and news is None:
            risk.append("未确认内容领域与是否涉及高敏内容：请明确领域，若涉医疗/财经/时政须资质")
        items.append("- 内容领域：%s（常规领域或待确认）" % (dom if filled(dom) else "未填"))
    return items, crit, risk


def check_violation(f):
    items = []
    crit = []
    risk = []
    got = yesno(get_text(f, "是否收到过违规通知"))
    vtype = get_text(f, "违规类型")
    times = parse_num(get_text(f, "收到违规通知次数"))
    if got is True:
        items.append("- 违规通知：是")
        if filled(vtype):
            items.append("  - 违规类型：%s" % vtype)
        if times is not None:
            items.append("  - 收到次数：%s" % int(times))
            if times >= 3:
                crit.append("已多次收到违规通知（%d 次）：累计违规易触发限流、减少推荐甚至封号，"
                            "须立即停改违规动作并学习平台规范" % int(times))
                items.append("  - 评估：高频违规（阻断）")
            elif times >= 1:
                risk.append("已有违规记录：历史违规会降低账号权重、影响推荐，须彻底整改避免再犯")
                items.append("  - 评估：有违规记录（风险）")
        else:
            risk.append("已有违规记录但未说明次数：请核对其余违规动作并整改")
            items.append("  - 评估：有违规记录（风险）")
    elif got is False:
        items.append("- 违规通知：否")
    else:
        risk.append("未确认是否收到过违规通知：若曾收到请如实填写以便评估限流风险")
        items.append("- 违规通知：未确认")

    # 限流信号
    down = yesno(get_text(f, "近期播放量是否异常下跌"))
    if down is True:
        risk.append("近期播放量异常下跌：可能是已被限流的信号，需排查违规内容、搬运、"
                    "标题党、互动异常等并整改，持续下跌需申诉或养号")
        items.append("- 流量异常下跌：是（限流风险信号）")
    elif down is False:
        items.append("- 流量异常下跌：否")
    else:
        items.append("- 流量异常下跌：未确认")

    complained = yesno(get_text(f, "是否有用户投诉或举报"))
    if complained is True:
        risk.append("存在用户投诉/举报：举报累计会触发平台复核与限流，须优化内容、"
                    "减少争议表述并妥善处理投诉")
        items.append("- 用户投诉/举报：是（风险）")
    elif complained is False:
        items.append("- 用户投诉/举报：否")
    return items, crit, risk


def check_monetize(f):
    items = []
    crit = []
    risk = []
    has_shop = yesno(get_text(f, "是否有带货或橱窗"))
    cat = get_text(f, "带货类目")
    if has_shop is True or filled(cat):
        items.append("- 带货/橱窗：已开通")
        lic = yesno(get_text(f, "是否配置了对应资质证件"))
        if filled(cat):
            items.append("  - 带货类目：%s" % cat)
            cn = norm(cat)
            if any(k in cn for k in ("医疗", "药品", "器械", "保健")):
                if lic is False:
                    crit.append("带货类目涉及医疗/药品/保健食品且未配置资质：须对应经营或备案资质，"
                                "不得宣称疗效，否则违规下架")
                    items.append("  - 类目资质：需医疗/食品类资质（阻断）")
                elif lic is None:
                    risk.append("带货医疗/药品/保健食品未确认资质：须对应经营或备案资质，不得宣称疗效")
                    items.append("  - 类目资质：需医疗/食品类资质（风险-待确认）")
                else:
                    items.append("  - 类目资质：已配置")
            elif any(k in cn for k in ("食品", "美妆", "化妆品")):
                if lic is False:
                    risk.append("带货食品/美妆但未配置对应资质：须对应商品资质与功效依据，不得虚假夸大")
                    items.append("  - 类目资质：需食品/化妆品类资质（风险）")
                elif lic is None:
                    risk.append("未确认食品/美妆带货资质：请上传对应商品资质与功效依据")
                    items.append("  - 类目资质：未确认")
                else:
                    items.append("  - 类目资质：已配置")
        if lic is False and not any(k in norm(cat) for k in ("医疗", "药品", "器械", "保健", "食品", "美妆", "化妆品")):
            risk.append("带货但未确认对应资质：特殊类目须资质，请补齐")
            items.append("  - 资质：未配置（风险）")
        elif lic is None and filled(cat) and not any(k in norm(cat) for k in ("医疗", "药品", "器械", "保健", "食品", "美妆", "化妆品")):
            risk.append("未确认带货资质：请上传对应经营/备案资质")
            items.append("  - 资质：未确认")
    elif has_shop is False:
        items.append("- 带货/橱窗：未开通")
    else:
        items.append("- 带货/橱窗：未确认")
    return items, crit, risk


def check_copyright(f):
    items = []
    crit = []
    risk = []
    original = yesno(get_text(f, "是否原创内容"))
    copy = yesno(get_text(f, "是否搬运他人内容"))
    if original is True:
        items.append("- 原创内容：是")
    elif original is False:
        items.append("- 原创内容：否")
    else:
        items.append("- 原创内容：未确认")
    if copy is True:
        crit.append("存在搬运/转载他人内容：非原创且未授权会被判定侵权、限流，"
                    "严重可封号，须改为原创或取得授权后标注来源")
        items.append("- 搬运他人内容：是（阻断）")
    elif copy is False:
        items.append("- 搬运他人内容：否")
    else:
        if original is False:
            risk.append("内容非原创且未说明授权：搬运/二创须获授权并标注，否则限流")
            items.append("- 搬运/授权：非原创未确认授权（风险）")
        else:
            items.append("- 搬运/授权：未确认")

    music = yesno(get_text(f, "是否使用未授权音乐或素材"))
    if music is True:
        crit.append("使用未授权音乐/素材：侵犯版权会被下架、限流，须使用平台曲库或获授权素材")
        items.append("- 未授权音乐/素材：是（阻断）")
    elif music is False:
        items.append("- 未授权音乐/素材：否")
    else:
        items.append("- 未授权音乐/素材：未确认")
    return items, crit, risk


def check_diversion(f):
    items = []
    risk = []
    divert = yesno(get_text(f, "是否引导站外或私域"))
    if divert is True:
        risk.append("引导站外/私域引流：视频号对违规站外导流（如直接留微信/外链）会限流或处罚，"
                    "应通过平台合规组件或合规话术引导")
        items.append("- 站外/私域引流：是（风险）")
    elif divert is False:
        items.append("- 站外/私域引流：否")
    else:
        items.append("- 站外/私域引流：未确认")
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

    name = get_text(f, "账号类型")
    header = "# 视频号内容运营合规与违规限流避坑核查报告"
    if filled(name):
        header += "（%s）" % name
    sections.append(header)
    sections.append("")

    red_items, red_c, red_r = check_redline(f)
    crit += red_c
    risk += red_r
    viol_items, viol_c, viol_r = check_violation(f)
    crit += viol_c
    risk += viol_r
    mon_items, mon_c, mon_r = check_monetize(f)
    crit += mon_c
    risk += mon_r
    copy_items, copy_c, copy_r = check_copyright(f)
    crit += copy_c
    risk += copy_r
    div_items, div_r = check_diversion(f)
    risk += div_r

    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"
    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（必须处理项 %d / 风险项 %d）\n" % (verdict, len(crit), len(risk))
    dom = get_text(f, "内容领域")
    if filled(dom):
        summary += "- 内容领域：%s\n" % dom
    summary += "- 处置建议：先消除全部必须处理项（含封号风险），再处理限流与风险信号。\n"
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 平台红线与高敏领域\n" + "\n".join(red_items) + "\n\n"
    body += "### 违规记录与限流信号\n" + "\n".join(viol_items) + "\n\n"
    body += "### 变现与带货合规\n" + "\n".join(mon_items) + "\n\n"
    body += "### 原创与版权\n" + "\n".join(copy_items) + "\n\n"
    body += "### 引流合规\n" + "\n".join(div_items) + "\n"
    sections.append(body)

    rb = "## 三、风险与整改\n\n"
    if crit:
        rb += "### 必须处理项（阻断/封号风险）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "未发现明显阻断或风险项，可正常运营并持续优化。\n\n"
    sections.append(rb)

    # 运营建议
    adv = "## 四、运营合规建议\n\n"
    adv += "1. 内容合规：规避医疗疗效宣称、财经承诺收益、时政采编等红线，用平台曲库与授权素材。\n"
    adv += "2. 降低限流：坚持原创、稳定更新、避免标题党与过度营销，互动数据异常时自查违规。\n"
    adv += "3. 带货前置：特殊类目先备齐资质再挂车，功效宣称留依据，不虚假夸大。\n"
    adv += "4. 账号养护：违规后停止违规动作、按规范整改，必要时通过平台申诉渠道说明。\n"
    adv += "5. 引流合规：用平台合规组件引导，避免直接留站外联系方式触发处罚。\n\n"
    sections.append(adv)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据通用规则与公开参考整理，不替代微信公众平台官方审核结论。\n"
                "- 内容合规、限流与封号判定最终以微信公众平台与视频号规则为准。\n"
                "- 不承诺账号一定不被限流或封号；最终以平台处置结果为准。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
