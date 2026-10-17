# -*- coding: utf-8 -*-
"""抖音视频下载与去水印保存核查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段报告，含能否下载判定、途径推荐、画质选择、水印处理、
      形态差异、失败排查、环境准备、待办补正动作、边界与纪律。

退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

FIELD_ALIAS = {
    "视频归属": ["视频归属", "作品归属", "归属类别", "这是谁的作品", "归属"],
    "获取方式": ["获取方式", "链接来源", "来源形式", "链接类型", "拿到的是什么"],
    "链接状态": ["链接状态", "链接是否有效", "链接可访问性", "能否打开"],
    "内容形态": ["内容形态", "作品形态", "作品类型", "是视频还是图文", "形态"],
    "作者设置": ["作者设置", "是否允许保存", "保存开关", "作者是否开启保存"],
    "是否登录可见": ["是否登录可见", "是否需要登录", "登录要求", "可见性"],
    "账号类型": ["账号类型", "目标账号类型", "是否私密账号", "账号可见范围"],
    "用途": ["用途", "下载来做什么", "使用目的", "准备怎么用"],
    "是否商用": ["是否商用", "是否用于商业", "有没有商业用途", "商用与否"],
    "有无授权": ["有无授权", "是否获得授权", "授权情况", "是否有书面授权"],
    "授权范围": ["授权范围", "授权用途范围", "授权怎么写的"],
    "是否需要去水印": ["是否需要去水印", "要不要去水印", "去水印需求", "水印要求"],
    "水印类型": ["水印类型", "水印是哪种", "水印来源"],
    "画质要求": ["画质要求", "需要的画质", "画质期望", "清晰度要求"],
    "原文件是否还在": ["原文件是否还在", "有没有原文件", "原始视频还在吗", "原片是否保留"],
    "本机环境": ["本机环境", "运行环境", "电脑环境", "系统环境"],
    "是否安装ffmpeg": ["是否安装ffmpeg", "ffmpeg是否安装", "有没有ffmpeg", "ffmpe情况"],
    "已尝试途径": ["已尝试途径", "试过哪些方法", "已试途径", "尝试情况"],
    "报错信息": ["报错信息", "遇到的错误", "失败现象", "报错内容"],
    "是否合集": ["是否合集", "是不是合集", "合集情况"],
    "作品数量": ["作品数量", "要下几个", "批量数量", "数量"],
    "网络环境": ["网络环境", "所在网络", "是否内网", "网络情况"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "没有", "n/a", "na",
    "null", "none", "？", "?",
)


def norm(s):
    if s is None:
        return ""
    out = str(s).strip()
    out = out.replace("：", ":").replace("　", " ")
    out = re.sub(r"\s+", "", out)
    return out.lower()


def filled(v):
    if v is None:
        return False
    return norm(v) not in {norm(t) for t in EMPTY_TOKENS}


def unknown(v):
    return not filled(v)


NEG = ("否", "没有", "未", "不", "无", "不在", "不是", "拒绝", "关闭")
POS = ("是", "已", "有", "在", "允许", "开启", "同意", "确认")


def yesno(t):
    """判定是/否。含否定式优先。"""
    if unknown(t):
        return None
    n = norm(t)
    for w in NEG:
        if n.startswith(w):
            return False
    for w in POS:
        if n.startswith(w):
            return True
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
            kraw = cells[0]
            if set(kraw) <= set("-: "):
                continue
            val = " ".join(c.strip() for c in cells[1:]).strip()
            if val:
                data[norm(kraw)] = val
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
    """精确匹配别名，绝不用子串 in（会串字段）。"""
    aliases = FIELD_ALIAS.get(key, [key])
    aliases = sorted(aliases, key=len, reverse=True)
    for a in aliases:
        na = norm(a)
        if na and na in f:
            v = f.get(na)
            if filled(v):
                return v
        stripped = re.sub(r"^\d+[.、)]\s*", "", na)
        if stripped != na and stripped in f:
            v = f.get(stripped)
            if filled(v):
                return v
    return ""


def judge_permission(owner, purpose, authorized, save_on, commercial):
    """能否下载判定。返回 (判定, 理由, 途径列表)。"""
    own = norm(owner)
    reasons = []
    paths = []

    if "自己" in own or "自有" in own or "本人" in own or "我方" in own:
        reasons.append("标注为自有作品，下载与二次使用不存在权属障碍")
        paths = ["原文件", "创作者后台下载", "官方保存本地", "命令行工具"]
        return "可以下载", reasons, paths

    if yesno(authorized) is True:
        reasons.append("已获得作者授权，可在授权范围内使用")
        if filled(commercial) and yesno(commercial) is True:
            reasons.append("用途涉及商用，商用前须确认授权范围覆盖商业使用")
        paths = ["作者提供的原文件", "官方保存本地", "命令行工具"]
        return "可以下载", reasons, paths

    if yesno(save_on) is True:
        reasons.append("作者开启了「允许他人保存」，可通过官方途径保存")
        reasons.append("官方保存仅限个人留存，**不得二次分发或搬运**")
        paths = ["官方保存本地"]
        return "仅限官方保存", reasons, paths

    if yesno(authorized) is False:
        reasons.append("明确未获得作者授权")
        reasons.append("下载第三方作品用于搬运或二次分发可能构成侵权")
        return "不建议下载", reasons, []

    if yesno(save_on) is False:
        reasons.append("作者未开启保存权限")
        reasons.append("绕过该设置下载可能违反平台服务协议")
        return "不建议下载", reasons, []

    reasons.append("归属与授权信息未填写完整，无法判定")
    return "待补正", reasons, []


def check_env(system, ffmpeg, purpose):
    """环境准备核查。"""
    items = []
    need_tool = False
    sysn = norm(system)
    if not filled(system):
        items.append("未填写本机环境，无法判断命令可用性")
    elif "windows" in sysn or "win" in sysn:
        items.append("Windows 环境：建议用 PowerShell 或 Windows Terminal 执行命令，避免编码问题")
    elif "mac" in sysn or "苹果" in sysn:
        items.append("macOS 环境：可用终端执行，建议先 `brew install ffmpeg`")
    elif "linux" in sysn:
        items.append("Linux 环境：用包管理器安装 ffmpeg 即可")

    if yesno(ffmpeg) is False:
        items.append("未安装 ffmpeg：**画面与声音无法合并**，会下出无声视频")
        need_tool = True
    elif yesno(ffmpeg) is None:
        items.append("ffmpeg 安装情况未知，建议先执行 `ffmpeg -version` 确认")

    n = None
    try:
        from importlib import util as _u
        n = _u.find_spec("yt_dlp")
    except Exception:
        pass
    if n is not None:
        items.append("检测到 yt-dlp 已安装，可直接调用")
    else:
        items.append("未检测到 yt-dlp：命令行为 `pip install -U yt-dlp`")

    return items


def diagnose(err_msg, tried, n_env, cnt):
    """失败排查。返回匹配到的问题列表。"""
    findings = []
    e = norm(err_msg)
    tr = norm(tried)
    if not filled(err_msg) and not filled(tried):
        return findings
    table = [
        ("401,403,登录,验证", "需要登录态才能访问，改用带 cookies 的方式，或换用自有账号途径"),
        ("429,频繁,限流,太快", "触发平台限流：降低请求频率、间隔重试，不要高频连续请求"),
        ("404,失效,不存在,找不到", "链接失效或作品已删除：让对方重新生成分享链接"),
        ("口令,过期", "分享口令有时效性：重新获取"),
        ("私密,不可见,关注后可看", "私密或未公开作品：属不可下载情形，应联系作者"),
        ("无声音,没声音,静音", "音轨未合并：确认 ffmpeg 已安装，用 -f \"bv*+ba/b\" 让工具合并"),
        ("解析失败,格式不支持", "站点接口变动：把工具更新到新版本后重试"),
        ("画质,模糊,不清晰", "源本身只有低码率版本，下载无法提升画质"),
        ("超时,timeout,连接失败", "网络或代理问题：检查网络连通性后重试"),
    ]
    for keys, advice in table:
        for k in keys.split(","):
            if k and k in e:
                findings.append(advice)
                break
    n = None
    if filled(cnt):
        m = re.search(r"\d+", cnt)
        n = int(m.group(0)) if m else None
    if n and n > 30:
        findings.append("批量数量 %d 条：建议分批、每批间隔数秒，避免触发限流" % n)
    if "命令行" in tr and "官方" not in tr:
        findings.append("已试命令行但未试官方途径：官方保存更稳定，建议先回到途径 2")

    # 无声：不要只匹配「没声音」这种连写，需识别"声音"配合否定词的各种说法
    if e:
        has_sound_word = any(k in e for k in ("声音", "音轨", "配音", "音频"))
        has_neg = any(k in e for k in ("没有", "无", "不", "缺", "丢失", "静音", "没"))
        if has_sound_word and has_neg:
            findings.append("音轨未合并：确认 ffmpeg 已安装，"
                            "用 -f \"bv*+ba/b\" 让工具自动合并视频轨与音频轨")
    return list(dict.fromkeys(findings))


def quality_advice(q, src_exists, form):
    """画质建议。注意：不得提前 return，否则形态提示会被吞掉。"""
    out = []
    qn = norm(q)
    is_pic = bool(form) and ("图文" in norm(form) or "轮播" in norm(form))

    # 形态提示先入列，保证不被后面的分支挡掉
    if is_pic:
        out.append("图文形态：官方保存通常只留第一张，完整导出建议用原文件或命令行途径")

    if yesno(src_exists) is True:
        out.append("原始文件仍在 → **直接用原文件**，画质最优且无水印问题")
        return out

    if not filled(q):
        out.append("未填写画质要求，默认按平台提供的最高码率下载")
    elif "4k" in qn or "2k" in qn or "超清" in qn:
        out.append("要求超高画质：能否达到取决于作者上传时的原始码率，下载无法凭空提升")
        out.append("若对方是自有作品，优先索取原始导出文件")
    elif "1080" in qn or "高清" in qn:
        out.append("1080p 需作者在发布时选择了高质量上传，否则只能取到较低码率")
    elif "720" in qn or "标清" in qn:
        out.append("720p 一般可直接获取")
    else:
        out.append("画质要求「%s」：默认取平台提供的最高码率版本" % str(q)[:20])
    return out


def water_mark_advice(need, wtype, owner):
    """水印处理建议。"""
    out = []
    if yesno(need) is None:
        out.append("是否需要去水印未填写；未明确前建议**保留水印**")
        return out
    if yesno(need) is False:
        out.append("不需要去水印 → 直接保存，无需额外处理")
        return out
    out.append("需要去水印，先分清类型：")
    wt = norm(wtype)
    if not filled(wtype):
        out.append("  未填写水印类型：请先确认是平台自动水印还是作者署名")
    elif "署名" in wt or "作者" in wt or "logo" in wt:
        out.append("  **作者署名水印**：去除可能侵犯署名权，法律风险高，不建议处理")
    elif "平台" in wt or "抖音" in wt or "右下角" in wt:
        out.append("  平台自动水印：属平台标识，去除后二次发布可能违反平台规则")
    own = norm(owner)
    if "自己" in own or "自有" in own or "本人" in own:
        out.append("  自有作品：改用发布前的原始导出文件，本身不含水印，是最干净的做法")
    else:
        out.append("  非自有作品：保留水印最安全，不要去除后二次分发")
    return out


def path_detail(paths, form, is_album, cnt):
    """途径操作明细。"""
    det = []
    for p in paths:
        if p == "原文件":
            det.append(("原文件", "优先。找发布时的原始导出成品（手机相册/剪映导出），"
                                 "画质无损无水印；若仍在，后面几条都不必尝试"))
        elif p == "作者提供的原文件":
            det.append(("作者提供原文件", "向作者索取原始文件，比任何下载途径都干净"))
        elif p == "创作者后台下载":
            det.append(("创作者后台下载", "creator.douyin.com 登录**自己的账号**，"
                                      "在内容管理里下载已发布作品，可拿较高画质"))
        elif p == "官方保存本地":
            det.append(("官方保存本地", "分享面板 → 保存本地/保存到相册。"
                                    "带平台水印，画质接近上传源；作者关闭开关时该入口不出现"))
        elif p == "命令行工具":
            cmd = 'yt-dlp -f "bv*+ba/b" <链接>'
            if is_album:
                cmd = 'yt-dlp -f "bv*+ba/b" <合集链接>'
            det.append(("命令行工具", "本机需 Python + ffmpeg，安装 `pip install -U yt-dlp`。"
                                  "常用形态：`%s`" % cmd))
    return det


def build_report(f, base):
    rep, risk, todo = [], [], []

    owner = get_text(f, "视频归属")
    purpose = get_text(f, "用途")
    authorized = get_text(f, "有无授权")
    save_on = get_text(f, "作者设置")
    commercial = get_text(f, "是否商用")
    form = get_text(f, "内容形态")
    quality = get_text(f, "画质要求")
    src = get_text(f, "原文件是否还在")
    need_wm = get_text(f, "是否需要去水印")
    wm_type = get_text(f, "水印类型")
    system = get_text(f, "本机环境")
    ffmpeg = get_text(f, "是否安装ffmpeg")
    err = get_text(f, "报错信息")
    tried = get_text(f, "已尝试途径")
    cnt = get_text(f, "作品数量")
    is_album = yesno(get_text(f, "是否合集")) is True
    login_only = get_text(f, "是否登录可见")
    acct = get_text(f, "账号类型")

    verdict, reasons, paths = judge_permission(owner, purpose, authorized,
                                               save_on, commercial)

    if verdict == "不建议下载":
        risk.append("判定为不建议下载，继续操作存在侵权或违反平台协议的风险")
    if yesno(login_only) is True:
        risk.append("目标要求登录可见，匿名抓取可能失败，且需评估是否有权访问")
    if acct and ("私密" in norm(acct) or "仅粉丝" in norm(acct)):
        risk.append("目标账号为私密或限定可见，属不可下载情形")
    if verdict == "待补正":
        risk.append("归属与授权信息不完整，暂无法给出下载途径")

    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 视频归属：%s" % (owner if filled(owner) else "未填写"))
    rep.append("- 用途：%s" % (purpose if filled(purpose) else "未填写"))
    rep.append("- 内容形态：%s" % (form if filled(form) else "未填写"))
    if is_album:
        rep.append("- 合集：是")
    rep.append("- **能否下载：%s**" % verdict)
    rep.append("- 推荐途径：%s" % (" → ".join(paths) if paths else "暂无可用途径"))
    rep.append("")
    for r in reasons:
        rep.append("- %s" % r)
    rep.append("")

    rep.append("## 途径操作明细")
    rep.append("")
    det = path_detail(paths, form, is_album, cnt)
    if det:
        rep.append("| 途径 | 操作要点 |")
        rep.append("| --- | --- |")
        for nm, txt in det:
            rep.append("| %s | %s |" % (nm, txt))
    else:
        rep.append("无可用途径。若确需该素材，应先取得作者授权，或改用自己拍摄/制作的内容。")
        todo.append("联系作者取得书面授权后再来核查")
    rep.append("")

    rep.append("## 画质选择与建议")
    rep.append("")
    if verdict == "不建议下载":
        rep.append("- 判定为不建议下载，画质选择不适用")
        rep.append("- 若后续取得作者授权，自有作品一律优先取发布前的原始文件，画质最优")
    else:
        for q in quality_advice(quality, src, form):
            rep.append("- %s" % q)
    rep.append("")

    rep.append("## 水印处理")
    rep.append("")
    for w in water_mark_advice(need_wm, wm_type, owner):
        rep.append("- %s" % w)
    rep.append("")

    rep.append("## 环境与工具准备")
    rep.append("")
    if verdict == "不建议下载":
        rep.append("- 判定为不建议下载，无需准备任何下载工具")
        rep.append("- 若后续取得作者授权，再按推荐途径准备环境")
    else:
        for e in check_env(system, ffmpeg, purpose):
            rep.append("- %s" % e)
    rep.append("")

    rep.append("## 常见失败排查")
    rep.append("")
    dg = diagnose(err, tried, system, cnt)
    if dg:
        for d in dg:
            rep.append("- **%s**" % d)
    else:
        rep.append("- 未填写报错或已尝试途径，暂无针对性排查")
        rep.append("- 通用兜底：换入口（官方优先）→ 更新工具到最新版 → 降低频率重试")
    rep.append("")

    rep.append("## 数量与频率建议")
    rep.append("")
    n = None
    if filled(cnt):
        m = re.search(r"\d+", cnt)
        n = int(m.group(0)) if m else None
    if verdict == "不建议下载":
        rep.append("- 判定为不建议下载，数量与频率策略不适用")
        if n and n > 1:
            rep.append("- 涉及 %d 件内容：数量越多风险越大，建议先就整体用途取得授权" % n)
    elif n and n > 1:
        rep.append("- 目标数量 %d 条，属批量场景" % n)
        rep.append("- 建议分批执行，每批间隔数秒，避免触发平台限流")
        rep.append("- 批量抓取第三方内容前务必确认已取得授权")
    elif n == 1:
        rep.append("- 单条下载，直接按推荐途径操作即可")
    else:
        rep.append("- 未填写数量；若超过 10 条请按批量场景处理")
    rep.append("")

    rep.append("## 待办补正动作")
    rep.append("")
    all_todo = list(todo)
    if not filled(owner):
        all_todo.append("填写视频归属（自有/已授权/第三方），这是判定的前提")
    if verdict == "可以下载" and filled(authorized) and not filled(get_text(f, "授权范围")):
        all_todo.append("补充授权范围，确认是否覆盖你的实际用途")
    if yesno(src) is None and (verdict == "可以下载"):
        all_todo.append("确认发布时的原始导出文件是否还在 —— 有的话就不用下载")
    if paths and "命令行工具" in paths and yesno(ffmpeg) is not False and ffmpeg == "":
        all_todo.append("执行 `ffmpeg -version` 确认 ffmpeg 可用，否则会下出无声视频")
    if not all_todo:
        all_todo.append("信息已完整，可直接按推荐途径执行")
    for i, t in enumerate(all_todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 技术上能下载 ≠ 法律上可以使用，两者必须分开判断。")
    rep.append("- 不得去除作者署名水印后二次分发，可能侵犯署名权。")
    rep.append("- 不得将他人作品搬运至自己的账号，含剪辑、配音后重新发布。")
    rep.append("- 不得下载或传播私密账号、付费内容。")
    rep.append("- 批量高频抓取可能违反平台服务协议，导致账号受限。")
    rep.append("- 本结果依通用规则整理，不替代专业法律意见，最终以平台规则与《中华人民共和国著作权法》"
               "及司法机关认定为准。")

    return "\n".join(rep), verdict, risk, all_todo


def main():
    ap = argparse.ArgumentParser(description="抖音视频下载与去水印保存核查")
    ap.add_argument("--input", required=True)
    ap.add_argument("--base", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.input):
        print("采集表不存在：%s" % a.input)
        if a.json:
            print(json.dumps({"结论": "待补正", "错误": "collect file missing"},
                             ensure_ascii=False))
        return 2

    f = parse_md(a.input)
    if not f:
        print("采集表为空或无法解析，请用「| 字段 | 值 |」或「字段：值」格式")
        if a.json:
            print(json.dumps({"结论": "待补正", "错误": "empty"}, ensure_ascii=False))
        return 2

    rep, verdict, risk, todo = build_report(f, date.today())

    if a.json:
        print(json.dumps({"结论": verdict, "风险项": risk,
                          "待办": todo, "报告": rep},
                         ensure_ascii=False, indent=2))
    else:
        print(rep)

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(rep)

    if unknown(get_text(f, "视频归属")):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())