# -*- coding: utf-8 -*-
"""公众号违规与限流避坑核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、内容来源、平台红线、敏感领域资质、限流信号、
      风险与整改、待办动作、边界与纪律。

只做风险核查与避坑建议，不替代平台判定。
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
    "公众号类型": ["公众号类型", "账号类型", "类型"],
    "账号主体": ["账号主体", "主体", "运营主体"],
    "内容领域": ["内容领域", "领域", "垂直方向", "行业"],
    "运营方式": ["运营方式", "运营形式", "是否团队"],
    "是否原创": ["是否原创", "是否原创内容", "原创与否"],
    "原创占比": ["原创占比", "原创比例", "原创率"],
    "是否有洗稿搬运": ["是否有洗稿搬运", "是否洗稿", "是否搬运", "洗稿", "搬运"],
    "是否标注原创声明": ["是否标注原创声明", "是否声明原创", "原创声明", "是否标注原创"],
    "是否含诱导分享关注": ["是否含诱导分享关注", "是否诱导分享", "是否诱导关注", "诱导分享",
                       "诱导关注", "强制分享"],
    "是否有集赞活动": ["是否有集赞活动", "是否集赞", "集赞活动", "集赞", "点赞抽奖"],
    "是否有诱导下载转发": ["是否有诱导下载转发", "是否诱导下载", "是否诱导转发", "诱导下载",
                       "诱导转发", "引导下载app"],
    "是否标题党": ["是否标题党", "标题党", "标题夸张", "震惊体"],
    "是否含虚假夸张": ["是否含虚假夸张", "是否虚假", "虚假宣传", "夸大宣传", "不实信息"],
    "是否涉色情低俗": ["是否涉色情低俗", "是否色情", "是否低俗", "色情低俗", "涉黄"],
    "是否涉政敏感": ["是否涉政敏感", "是否涉政", "政治敏感", "涉政", "时政"],
    "是否医疗财经等敏感内容": ["是否医疗财经等敏感内容", "是否医疗内容", "是否财经内容",
                         "医疗财经", "敏感领域内容"],
    "是否有敏感领域资质": ["是否有敏感领域资质", "是否有资质", "敏感领域资质", "资质认证"],
    "营销内容占比": ["营销内容占比", "营销占比", "广告占比", "营销比例"],
    "近期阅读量是否异常下跌": ["近期阅读量是否异常下跌", "阅读量下跌", "阅读异常下跌",
                         "是否限流", "流量下跌"],
    "是否被搜索屏蔽": ["是否被搜索屏蔽", "搜索屏蔽", "搜不到", "被屏蔽搜索"],
    "是否被限制推荐": ["是否被限制推荐", "限制推荐", "不被推荐", "推荐停止"],
    "是否有违规记录": ["是否有违规记录", "是否违规", "有无违规", "违规记录"],
    "违规次数": ["违规次数", "被罚次数", "违规记录次数"],
    "违规类型": ["违规类型", "违规原因", "处罚类型"],
    "期望结果": ["期望结果", "诉求", "希望怎么解决"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

# 平台红线关键词 → 风险等级
RED_LINES = [
    ("涉政敏感", ["涉政", "政治敏感", "时政", "领导人", "反动"], "严重"),
    ("色情低俗", ["色情", "低俗", "涉黄", "裸聊", "招嫖"], "严重"),
    ("诱导分享关注", ["诱导分享", "诱导关注", "强制分享", "分享后才能", "集赞", "裂变"], "中度"),
    ("诱导下载转发", ["诱导下载", "诱导转发", "引导下载app", "跳转外部", "站外引流"], "中度"),
    ("虚假夸张", ["虚假", "夸大", "不实", "绝对化用语", "最牛", "第一", "100%有效"], "中度"),
    ("标题党", ["标题党", "震惊", "不转不是", "看完泪目", "速看", "独家揭秘"], "轻度"),
    ("集赞活动", ["集赞", "点赞抽奖", "转发抽奖", "打卡领"], "中度"),
]

SENSITIVE_FIELDS = ["医疗", "财经", "金融", "股票", "保险", "基金", "新闻", "时政",
                "健康科普", "投资建议", "诊股", "荐股"]


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


def parse_num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("，", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
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
            if norm(key_raw) in ("字段", "field", "项目"):
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


NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "可以")


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


def check_content_source(f):
    items = []
    crit = []
    risk = []
    original = yesno(get_text(f, "是否原创"))
    pct = parse_num(get_text(f, "原创占比"))
    xigao = yesno(get_text(f, "是否有洗稿搬运"))
    declared = yesno(get_text(f, "是否标注原创声明"))
    if original is True:
        items.append("- 内容来源：原创")
        if pct is not None and pct < 100:
            items.append("  - 原创占比：%s%%" % int(pct))
        if declared is False:
            risk.append("原创内容未标注原创声明：声明原创须确为原创，否则可能被判非原创/侵权")
            items.append("  - 原创声明：**未标注（风险）**")
        elif declared is None:
            items.append("  - 原创声明：未确认")
        else:
            items.append("  - 原创声明：已标注")
    elif original is False:
        items.append("- 内容来源：非原创")
        if xigao is True:
            crit.append("存在洗稿/搬运且未标注授权：非原创内容须取得授权并注明来源，"
                        "否则可能被投诉侵权、被判抄袭，累积将影响推荐与信用分")
            items.append("  - 洗稿搬运：**是（高风险）**")
        elif xigao is None:
            risk.append("未确认是否存在洗稿搬运：搬运内容须有授权与来源标注")
            items.append("  - 洗稿搬运：未确认")
        else:
            items.append("  - 洗稿搬运：否（已授权/注明来源）")
    else:
        risk.append("未确认内容来源与原创情况：原创占比、授权与来源标注直接影响推荐权重与侵权风险")
        items.append("- 内容来源：未确认")
    return items, crit, risk


def check_redline(f):
    items = []
    crit = []
    risk = []
    hits = []
    for name, kws, level in RED_LINES:
        key_map = {
            "涉政敏感": "是否涉政敏感",
            "色情低俗": "是否涉色情低俗",
            "诱导分享关注": "是否含诱导分享关注",
            "诱导下载转发": "是否有诱导下载转发",
            "虚假夸张": "是否含虚假夸张",
            "标题党": "是否标题党",
            "集赞活动": "是否有集赞活动",
        }
        yn = yesno(get_text(f, key_map[name]))
        if yn is True:
            hits.append((name, level))
            if level == "严重":
                crit.append("%s：属平台严重违规红线，可能导致账号封禁，须立即移除相关内容" % name)
            elif level == "中度":
                risk.append("%s：诱导类设计属平台限制行为，建议改为自然分享、去除强制/奖励分享" % name)
            else:
                risk.append("%s：夸张标题影响推荐与体验，建议改为客观标题" % name)
            items.append("- %s：**是（%s）**" % (name, level))
        elif yn is None:
            items.append("- %s：未确认" % name)
        else:
            items.append("- %s：否" % name)
    return items, crit, risk, hits


def check_sensitive(f):
    items = []
    crit = []
    risk = []
    sensitive = yesno(get_text(f, "是否医疗财经等敏感内容"))
    field_text = get_text(f, "内容领域") + " " + get_text(f, "是否医疗财经等敏感内容")
    has_sensitive = sensitive is True or any(w in norm(field_text) for w in SENSITIVE_FIELDS)
    if has_sensitive:
        items.append("- 敏感领域内容：是")
        lic = yesno(get_text(f, "是否有敏感领域资质"))
        if lic is False:
            crit.append("医疗/财经/新闻等敏感内容缺少对应资质或认证：无资质发布医疗建议、"
                        "荐股荐基、新闻采编等会被判违规甚至封号，须先取得资质/认证或仅做科普并显著免责")
            items.append("  - 资质/认证：**无（高风险）**")
        elif lic is None:
            risk.append("未确认是否有敏感领域资质：医疗/财经/新闻类须相应资质或平台认证，"
                        "否则仅限科普且需显著免责声明")
            items.append("  - 资质/认证：未确认")
        else:
            items.append("  - 资质/认证：已具备")
    else:
        items.append("- 敏感领域内容：否/未确认")
    return items, crit, risk


def check_limit(f):
    items = []
    crit = []
    risk = []
    # 营销占比
    ad_pct = parse_num(get_text(f, "营销内容占比"))
    if ad_pct is not None:
        items.append("- 营销内容占比：%s%%" % int(ad_pct))
        if ad_pct >= 50:
            risk.append("营销/广告内容占比过高（%d%%）：纯营销比例过高易被降权限流，"
                        "建议提升有价值原创内容、降低硬广比例" % int(ad_pct))
            items.append("  - 评估：占比偏高（风险）")
        else:
            items.append("  - 评估：占比可控")
    else:
        items.append("- 营销内容占比：未确认")
    down = yesno(get_text(f, "近期阅读量是否异常下跌"))
    search_block = yesno(get_text(f, "是否被搜索屏蔽"))
    rec_block = yesno(get_text(f, "是否被限制推荐"))
    has_viol = yesno(get_text(f, "是否有违规记录"))
    times = parse_num(get_text(f, "违规次数"))
    vtype = get_text(f, "违规类型")
    if down is True:
        risk.append("阅读量异常下跌：常与诱导分享/标题党/低质或触发限流有关，"
                    "先排查近期是否触碰红线，停止违规动作并恢复原创稳定更新")
        items.append("- 阅读量异常下跌：是")
    elif down is None:
        items.append("- 阅读量异常下跌：未确认")
    else:
        items.append("- 阅读量异常下跌：否")
    if search_block is True:
        risk.append("被搜索屏蔽：内容或账号可能被降权，需排查违规并申诉")
        items.append("- 搜索屏蔽：是")
    elif search_block is None:
        items.append("- 搜索屏蔽：未确认")
    else:
        items.append("- 搜索屏蔽：否")
    if rec_block is True:
        risk.append("被限制推荐：推荐停止多与内容质量或违规相关，需整改后观察恢复")
        items.append("- 限制推荐：是")
    elif rec_block is None:
        items.append("- 限制推荐：未确认")
    else:
        items.append("- 限制推荐：否")
    if has_viol is True or (times is not None and times > 0):
        items.append("- 违规记录：是（%s 次）" % (int(times) if times else "?"))
        if times is not None and times >= 3:
            crit.append("违规次数已达 %d 次：累积违规将大幅提升封号风险，须严格整改并观察信用分" % int(times))
        if filled(vtype):
            items.append("  - 违规类型：%s" % vtype)
    elif has_viol is None:
        items.append("- 违规记录：未确认")
    else:
        items.append("- 违规记录：否")
    return items, crit, risk


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

    atype = get_text(f, "公众号类型")
    field = get_text(f, "内容领域")
    header = "# 公众号违规与限流避坑核查报告"
    if filled(atype) or filled(field):
        header += "：%s%s" % (("%s " % atype if filled(atype) else ""),
                             ("· %s" % field if filled(field) else ""))
    sections.append(header)
    sections.append("")

    src_items, src_c, src_r = check_content_source(f)
    crit += src_c
    risk += src_r
    red_items, red_c, red_r, red_hits = check_redline(f)
    crit += red_c
    risk += red_r
    sen_items, sen_c, sen_r = check_sensitive(f)
    crit += sen_c
    risk += sen_r
    lim_items, lim_c, lim_r = check_limit(f)
    crit += lim_c
    risk += lim_r

    # 结论
    if any(lv == "严重" for _, lv in red_hits) or any("封号" in c for c in crit):
        verdict = "封号风险"
    elif crit:
        verdict = "严重"
    elif len([x for x in risk if "高风险" in x or "违规次数" in x]) >= 1 or len(risk) >= 3:
        verdict = "中度"
    elif risk:
        verdict = "轻度"
    else:
        verdict = "通过"

    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(atype):
        summary += "- 账号类型：%s\n" % atype
    if filled(field):
        summary += "- 内容领域：%s\n" % field
    summary += "- 处置建议：先消除严重项，再处理诱导与限流信号。\n"
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 内容来源与原创\n" + "\n".join(src_items) + "\n\n"
    body += "### 平台红线\n" + "\n".join(red_items) + "\n\n"
    body += "### 敏感领域资质\n" + "\n".join(sen_items) + "\n\n"
    body += "### 限流与违规信号\n" + "\n".join(lim_items) + "\n"
    sections.append(body)

    rb = "## 三、风险与整改\n\n"
    if crit:
        rb += "### 阻断项（必须处理）\n"
        for i, c in enumerate(crit, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if risk:
        rb += "### 风险项（建议处理）\n"
        for i, c in enumerate(risk, 1):
            rb += "%d. %s\n" % (i, c)
        rb += "\n"
    if not crit and not risk:
        rb += "未发现明显违规红线或限流信号，保持原创与合规运营即可。\n\n"
    sections.append(rb)

    todo = "## 四、待办动作\n\n"
    order = 1
    for c in crit:
        todo += "%d. 【必办】%s\n" % (order, c.split("：")[0] if "：" in c else c[:20])
        order += 1
    for c in risk:
        todo += "%d. 【建议】%s\n" % (order, c.split("：")[0] if "：" in c else c[:20])
        order += 1
    if order == 1:
        todo += "暂无可登记待办。\n"
    todo += "\n"
    sections.append(todo)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据通用平台规则整理，不替代微信公众平台判定与处罚结论。\n"
                "- 最终以平台审核、违规记录与官方说明为准；不承诺解封或恢复推荐。\n"
                "- 本技能不鼓励任何规避处罚的违规操作，仅做合规避坑建议。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
