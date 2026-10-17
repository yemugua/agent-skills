# -*- coding: utf-8 -*-
"""小程序内容安全合规核查脚本（内容类/UGC 小程序向）。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、内容审核机制核查、版权与知识产权核查、
      诱导分享核查、未成年人内容保护核查、UGC 平台责任核查、违规记录核查、
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
    "content_type": ["内容类型", "小程序类型", "业务类型", "内容形态", "产品形态"],
    "is_ugc": ["是否用户生成内容", "是否ugc", "是否 UGC", "用户发布内容", "是否有用户发帖", "ugc"],
    "pre_review": ["是否先审后发", "先审后发", "是否先审后播", "审核顺序", "发布前审核"],
    "has_review": ["是否接入内容审核", "内容审核", "是否有人工审核", "机器审核", "是否审核内容", "审核机制"],
    "has_wx_sec": ["是否使用微信内容安全接口(msgSecCheck/imgSecCheck/mediaCheckAsync)",
                "是否使用微信内容安全接口", "微信内容安全", "内容安全接口", "msgSecCheck",
                "imgSecCheck", "mediaCheckAsync", "是否接微信安全"],
    "has_wordlist": ["是否配置违规词库", "违规词库", "敏感词库", "屏蔽词", "关键词过滤", "词库"],
    "has_audio": ["是否涉及音频或音乐内容", "音频内容", "音乐内容", "是否有音频", "音频", "音乐", "语音"],
    "audio_license": ["音频或音乐是否有版权授权", "音乐版权", "音频授权", "音乐授权", "版权授权", "歌曲授权"],
    "has_media": ["是否涉及图片或视频内容", "图片内容", "视频内容", "是否有图片", "图文", "短视频"],
    "media_license": ["图片或视频是否有授权", "图片授权", "视频授权", "素材授权", "配图授权", "转载授权"],
    "has_induce": ["是否有诱导分享或利诱", "诱导分享", "利诱分享", "强制分享", "诱导下载", "集赞", "诱导行为"],
    "has_report": ["是否有举报与处置机制", "举报机制", "举报入口", "违规处置", "投诉处理", "举报"],
    "has_minor": ["是否有未成年人内容保护措施", "未成年人保护", "青少年模式", "防沉迷", "儿童保护"],
    "has_violation": ["是否有违规或下架历史", "违规历史", "下架历史", "被处罚", "被投诉", "整改历史"],
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


def is_ugc_scene(f):
    """判断是否 UGC 或内容型小程序。"""
    ugc = yesno(get_text(f, "is_ugc"))
    if ugc is True:
        return True
    ct = get_text(f, "content_type")
    if filled(ct):
        n = norm(ct)
        if any(w in n for w in ("ugc", "用户", "社区", "论坛", "日记", "社交", "内容", "短视频", "直播")):
            return True
    return False


def check_review(f):
    """内容审核机制核查。"""
    items, crit, risk = [], [], []
    ugc = is_ugc_scene(f)
    pre = yesno(get_text(f, "pre_review"))
    review = yesno(get_text(f, "has_review"))
    wxsec = yesno(get_text(f, "has_wx_sec"))
    wl = yesno(get_text(f, "has_wordlist"))

    if not ugc:
        items.append("- 内容形态：非 UGC（工具/纯展示类），内容安全以版权与合规为主，审核机制非强制")
        return items, crit, risk

    items.append("- 内容形态：UGC / 内容型（必须建立内容审核与版权机制）")

    if review is False:
        crit.append("未接入任何内容审核机制：UGC 小程序须配置机器审核与/或人工审核，"
                    "对发布内容进行先审后发或实时监控，否则极易出现违禁内容导致下架、封禁乃至行政处罚")
        items.append("- 内容审核机制：未接入（阻断）")
    elif review is True:
        items.append("- 内容审核机制：已接入（机器/人工）")
    else:
        crit.append("未确认是否接入内容审核机制：UGC 必备，请确认是否配置了审核流程")
        items.append("- 内容审核机制：未确认（阻断）")

    if wxsec is False:
        crit.append("未使用微信内容安全接口：平台要求 UGC 接入文本（msgSecCheck）、图片（imgSecCheck）、"
                    "音视频（mediaCheckAsync）内容安全检测，未接入将无法通过审核且违规内容会连带处罚")
        items.append("- 微信内容安全接口：未接入（阻断）")
    elif wxsec is True:
        items.append("- 微信内容安全接口：已接入")
    else:
        crit.append("未确认是否接入微信内容安全接口：请确认已调用 msgSecCheck/imgSecCheck/mediaCheckAsync")
        items.append("- 微信内容安全接口：未确认（阻断）")

    if pre is False:
        risk.append("非先审后发（先发后审）：如采取先发后审，须配合实时监控、关键词拦截与分钟级处置，"
                    "否则违规内容公开传播窗口过长，建议核心频道改为先审后发")
        items.append("- 审核顺序：先发后审（风险）")
    elif pre is True:
        items.append("- 审核顺序：先审后发")
    else:
        items.append("- 审核顺序：未确认")

    if wl is False:
        risk.append("未配置违规词库：建议自建违禁词库（涉政/涉黄/暴恐/赌博/诈骗/辱骂）+ 平台词库，"
                    "与微信内容安全接口互补，降低漏检")
        items.append("- 违规词库：未配置（风险）")
    elif wl is True:
        items.append("- 违规词库：已配置")
    else:
        items.append("- 违规词库：未确认")
    return items, crit, risk


def check_copyright(f):
    """版权与知识产权核查。"""
    items, crit, risk = [], [], []
    audio = yesno(get_text(f, "has_audio"))
    media = yesno(get_text(f, "has_media"))

    if audio is True:
        lic = yesno(get_text(f, "audio_license"))
        items.append("- 音频/音乐内容：涉及")
        if lic is False:
            crit.append("含音频/音乐内容但未取得版权授权：音乐版权是 UGC 内容类小程序最高频的侵权点，"
                        "无授权上传/播放他人歌曲易被权利人投诉下架并承担赔偿，建议使用正版曲库或原创/已授权音频")
            items.append("- 音频/音乐版权授权：未授权（阻断）")
        elif lic is True:
            items.append("- 音频/音乐版权授权：已取得")
        else:
            crit.append("含音频/音乐内容但未确认版权授权：请确认曲库/音频来源已获授权或使用原创/免费授权素材")
            items.append("- 音频/音乐版权授权：未确认（阻断）")
    elif audio is False:
        items.append("- 音频/音乐内容：不涉及")
    else:
        items.append("- 音频/音乐内容：未确认")

    if media is True:
        lic = yesno(get_text(f, "media_license"))
        items.append("- 图片/视频内容：涉及")
        if lic is False:
            risk.append("含图片/视频内容但未确认授权：转载、用户上传、配图素材须取得授权或属于可商用/公有领域，"
                        "避免图文盗用、影视剪辑侵权")
            items.append("- 图片/视频授权：未确认（风险）")
        elif lic is True:
            items.append("- 图片/视频授权：已取得")
        else:
            items.append("- 图片/视频授权：未确认")
    elif media is False:
        items.append("- 图片/视频内容：不涉及")
    else:
        items.append("- 图片/视频内容：未确认")
    return items, crit, risk


def check_induce(f):
    """诱导分享与诱导行为核查。"""
    items, crit, risk = [], [], []
    induce = yesno(get_text(f, "has_induce"))
    if induce is True:
        crit.append("存在诱导分享/利诱分享/强制分享/诱导下载等行为：微信《外部链接内容管理规范》《小程序运营规范》"
                    "明确禁止利诱用户分享（如分享得红包/积分/解锁）、强制分享后方可使用、诱导添加好友或下载，"
                    "触发即可能封禁分享接口乃至下架")
        items.append("- 诱导分享/利诱：存在（阻断）")
    elif induce is False:
        items.append("- 诱导分享/利诱：不存在")
    else:
        items.append("- 诱导分享/利诱：未确认")
    return items, crit, risk


def check_minor(f):
    """未成年人内容保护核查。"""
    items, risk = [], []
    minor = yesno(get_text(f, "has_minor"))
    if minor is False:
        risk.append("未落实未成年人内容保护措施：若内容面向未成年人或含 UGC，应设青少年模式/内容过滤、"
                    "防沉迷与监护人同意，避免不良内容触达未成年人")
        items.append("- 未成年人保护：未落实（风险）")
    elif minor is True:
        items.append("- 未成年人保护：已落实")
    else:
        items.append("- 未成年人保护：未确认")
    return items, risk


def check_ugc_duty(f):
    """UGC 平台责任核查（举报与处置）。"""
    items, crit, risk = [], [], []
    ugc = is_ugc_scene(f)
    report = yesno(get_text(f, "has_report"))
    if not ugc:
        items.append("- 举报与处置机制：非 UGC，非强制（建议保留基础投诉入口）")
        return items, crit, risk
    if report is False:
        crit.append("UGC 未建立举报与处置机制：平台要求提供举报入口与违禁内容处置流程，"
                    "并对举报在约定时限内响应处理，缺失将被处罚")
        items.append("- 举报与处置机制：未建立（阻断）")
    elif report is True:
        items.append("- 举报与处置机制：已建立")
    else:
        crit.append("未确认是否建立举报与处置机制：UGC 必备，请确认有举报入口与处置 SOP")
        items.append("- 举报与处置机制：未确认（阻断）")
    return items, crit, risk


def check_violation(f):
    """违规与下架历史核查。"""
    items, risk = [], []
    v = yesno(get_text(f, "has_violation"))
    if v is True:
        risk.append("存在违规/下架历史：应完成整改闭环并留存记录，再次违规将触发更严处罚（限流/封禁/主体连带），"
                    "建议全量复查历史内容与机制后再上新功能")
        items.append("- 违规/下架历史：有（风险）")
    elif v is False:
        items.append("- 违规/下架历史：无")
    else:
        items.append("- 违规/下架历史：未确认")
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

    header = "# 小程序内容安全合规核查报告"
    if filled(subj_txt):
        header += "（%s）" % subj_txt
    if filled(online):
        header += " · 状态：%s" % online
    sections.append(header)
    sections.append("")

    rev_items, rev_c, rev_r = check_review(f)
    crit += rev_c; risk += rev_r
    cop_items, cop_c, cop_r = check_copyright(f)
    crit += cop_c; risk += cop_r
    ind_items, ind_c, ind_r = check_induce(f)
    crit += ind_c; risk += ind_r
    min_items, min_r = check_minor(f)
    risk += min_r
    duty_items, duty_c, duty_r = check_ugc_duty(f)
    crit += duty_c; risk += duty_r
    vio_items, vio_r = check_violation(f)
    risk += vio_r

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
    summary += ("- 处置建议：先补齐内容审核机制与微信内容安全接口接入，再落实音频/音乐版权授权、"
                "清除诱导分享行为、完善举报处置与未成年人保护，最后整改历史违规闭环。\n")
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 内容审核机制核查\n" + "\n".join(rev_items) + "\n\n"
    body += "### 版权与知识产权核查\n" + "\n".join(cop_items) + "\n\n"
    body += "### 诱导分享与诱导行为核查\n" + "\n".join(ind_items) + "\n\n"
    body += "### 未成年人内容保护核查\n" + "\n".join(min_items) + "\n\n"
    body += "### UGC 平台责任核查（举报与处置）\n" + "\n".join(duty_items) + "\n\n"
    body += "### 违规与下架历史核查\n" + "\n".join(vio_items) + "\n"
    sections.append(body)

    rb = "## 三、阻断项与风险/待办\n\n"
    if crit:
        rb += "### 阻断项（必须处理，否则影响审核/上架/分享接口）\n"
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

    adv = ("## 四、整改操作指引（标准内容安全清单）\n\n"
           "1. 接入内容审核：UGC 配置机器+人工审核，核心频道先审后发；接入微信内容安全接口"
           "（文本 msgSecCheck、图片 imgSecCheck、音视频 mediaCheckAsync）。\n"
           "2. 配置违规词库：自建违禁词库（涉政/涉黄/暴恐/赌博/诈骗/辱骂）+ 平台词库，与机器审核互补。\n"
           "3. 版权合规：音频/音乐使用正版曲库或原创/已授权素材；图片/视频取得授权或可用免费授权；"
           "保留授权证明备查。\n"
           "4. 清除诱导分享：移除利诱分享（分享得红包/积分/解锁）、强制分享、诱导下载/添加好友等设计。\n"
           "5. 举报与处置：提供举报入口与处置 SOP，约定时限内响应举报并下架违禁内容，留存处置记录。\n"
           "6. 未成年人保护：面向未成年人的内容设青少年模式/内容过滤与防沉迷，落实监护人同意。\n"
           "7. 历史违规闭环：完成既往违规整改并留存证据，避免重复违规触发主体连带处罚。\n\n")
    sections.append(adv)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据《网络安全法》《网络信息内容生态治理规定》、微信小程序平台运营规范与"
                "《微信外部链接内容管理规范》公开规则整理，**不替代监管规定、平台规则与正式法律意见**，"
                "重大场景请咨询律师。\n"
                "- 违禁内容（涉政、涉黄、暴恐、赌博、诈骗、谣言、侵权）一经发现应立即下架并留存记录。\n"
                "- 音乐、图片、视频、字体等素材须取得合法授权或使用自有/免费可商用素材，UGC 应尽到审核与通知-删除义务。\n"
                "- 不得设置利诱、强制分享或诱导下载，不得违规收集与功能无关的个人信息（另见隐私合规核查）。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
