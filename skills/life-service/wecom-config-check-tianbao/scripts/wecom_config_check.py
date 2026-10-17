# -*- coding: utf-8 -*-
"""企业微信应用与配置排查脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、可信域名与网页授权、消息回调、通讯录与权限、
      客户联系与存档、安全、报错码映射、风险与整改、待办动作、边界与纪律。

只做配置核查与报错排查建议，不替代企业微信管理后台与官方文档。
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
    "应用类型": ["应用类型", "类型", "自建或第三方"],
    "应用名称": ["应用名称", "应用名", "名称"],
    "corpid": ["corpid", "企业id", "企业corpid"],
    "是否有报错": ["是否有报错", "是否报错", "报错情况"],
    "可信域名是否配置": ["可信域名是否配置", "是否配置可信域名", "可信域名"],
    "可信域名是否校验通过": ["可信域名是否校验通过", "可信域名校验", "域名是否校验"],
    "网页授权回调域名": ["网页授权回调域名", "网页授权域名", "oauth域名"],
    "OAuth2可信域名": ["oauth2可信域名", "oauth2域名", "授权域名"],
    "redirect_uri与可信域名是否一致": ["redirect_uri与可信域名是否一致", "redirect_uri一致",
                             "回调域名一致", "uri与域名一致"],
    "是否配置接收消息": ["是否配置接收消息", "是否接收消息", "消息回调", "是否配置消息回调"],
    "回调URL是否可达": ["回调URL是否可达", "回调地址可达", "回调url可达", "url可达"],
    "Token与AESKey是否填写": ["token与aeskey是否填写", "是否填写token", "token/aeskey",
                        "密钥是否填写"],
    "消息加解密模式": ["消息加解密模式", "加解密模式", "加密模式"],
    "回调URL是否公网可访问": ["回调url是否公网可访问", "回调公网可访问", "公网可访问",
                        "回调是否公网"],
    "应用可见范围": ["应用可见范围", "可见范围", "可见成员"],
    "通讯录读取权限范围": ["通讯录读取权限范围", "通讯录权限", "通讯录读取范围"],
    "secret权限范围": ["secret权限范围", "应用权限", "secret权限"],
    "是否配置IP白名单": ["是否配置ip白名单", "是否配置白名单", "ip白名单", "是否配置可信ip"],
    "可信IP是否配置": ["可信ip是否配置", "可信ip", "白名单ip", "ip是否配置"],
    "是否开通客户联系": ["是否开通客户联系", "客户联系", "是否开通客户联系功能"],
    "客户群权限": ["客户群权限", "客户群", "是否客户群"],
    "是否开通会话内容存档": ["是否开通会话内容存档", "会话存档", "内容存档", "会话内容存档"],
    "离职继承是否开启": ["离职继承是否开启", "离职继承", "是否开启离职继承"],
    "应用secret保管方式": ["应用secret保管方式", "secret保管", "secret存放", "密钥保管方式"],
    "是否开启操作审计日志": ["是否开启操作审计日志", "审计日志", "操作日志", "是否开启日志"],
    "最近报错码": ["最近报错码", "报错码", "errcode", "错误码"],
    "报错信息": ["报错信息", "错误信息", "报错描述"],
    "期望结果": ["期望结果", "诉求", "希望怎么解决"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

# 常见报错码 → (说明, 处置, 等级)
ERRCODES = {
    "40093": ("redirect_uri 与可信域名不一致", "在「应用管理 → 网页授权及JS-SDK → 可信域名」"
              "配置并校验与 redirect_uri 完全一致的域名（含协议与路径前缀）", "严重"),
    "60020": ("调用接口的 IP 不在白名单", "在「企业微信管理后台 → 企业可信IP」或应用白名单加入"
              "服务器出口 IP；本地调试可用内网穿透映射到白名单 IP", "严重"),
    "81013": ("无权限调用该接口（应用无此权限）", "在「应用 → 权限配置」勾选所需接口权限，"
              "或检查 secret 对应的应用是否正确", "严重"),
    "48002": ("API 接口无权限（接口未授权）", "确认应用已开通对应接口权限，部分接口需企业微信认证", "中度"),
    "45009": ("接口调用超限", "降低调用频率，使用批量接口与缓存，必要时申请提额", "中度"),
    "45011": ("API 调用频率超过限制", "做调用限流与退避，避免高频轮询", "中度"),
    "40089": ("不合法的 secret", "检查 secret 是否复制完整、是否被重置，重新获取", "严重"),
    "41001": ("缺少 access_token 参数", "先获取 access_token 再调用业务接口，注意缓存与过期刷新", "中度"),
    "40014": ("不合法的 access_token", "access_token 已过期或错误，重新获取", "中度"),
    "89003": ("缺少语料或模板（部分接口）", "检查接口所需参数与模板配置", "轻度"),
    "60011": ("不允许跨应用调用", "确认调用方与应用 secret 匹配", "中度"),
}

SECRET_RISK_WORDS = ("硬编码", "写在代码", "放前端", "放客户端", "明文", "提交到git", "仓库", "前端")


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


def check_domain(f):
    items = []
    crit = []
    risk = []
    configured = yesno(get_text(f, "可信域名是否配置"))
    verified = yesno(get_text(f, "可信域名是否校验通过"))
    consistent = yesno(get_text(f, "redirect_uri与可信域名是否一致"))
    oauth = get_text(f, "OAuth2可信域名")
    if configured is False:
        crit.append("未配置可信域名：网页授权、JS-SDK、分享等能力均依赖可信域名，"
                    "须在「应用管理 → 网页授权及JS-SDK」配置并校验通过")
        items.append("- 可信域名：**未配置（阻断）**")
    elif configured is None:
        risk.append("未确认是否配置可信域名：请在企业微信后台确认可信域名已配置并校验")
        items.append("- 可信域名：未确认")
    else:
        items.append("- 可信域名：已配置")
        if verified is False:
            risk.append("可信域名未校验通过：需下载校验文件放到域名根目录或按后台指引完成校验")
            items.append("  - 校验：**未通过（风险）**")
        elif verified is None:
            risk.append("未确认可信域名是否校验通过：未校验会影响 JS-SDK 与分享")
            items.append("  - 校验：未确认")
        else:
            items.append("  - 校验：已通过")
    if consistent is False:
        crit.append("redirect_uri 与可信域名不一致（对应报错 40093）：OAuth2 回调地址的域名"
                    "必须与可信域名完全一致，请核对协议、域名与路径前缀")
        items.append("- redirect_uri 一致性：**不一致（阻断/40093）**")
    elif consistent is None:
        risk.append("未确认 redirect_uri 与可信域名是否一致：不一致会报 40093，请核对")
        items.append("- redirect_uri 一致性：未确认")
    else:
        items.append("- redirect_uri 一致性：一致")
    if filled(oauth):
        items.append("- OAuth2 可信域名：%s" % oauth)
    return items, crit, risk


def check_callback(f):
    items = []
    crit = []
    risk = []
    cfg = yesno(get_text(f, "是否配置接收消息"))
    reachable = yesno(get_text(f, "回调URL是否可达"))
    token_filled = yesno(get_text(f, "Token与AESKey是否填写"))
    pub = yesno(get_text(f, "回调URL是否公网可访问"))
    mode = get_text(f, "消息加解密模式")
    if cfg is True or filled(mode):
        items.append("- 接收消息：已配置")
        if pub is False:
            crit.append("回调 URL 不可公网访问：企业微信服务器需能访问你的回调地址，"
                        "需公网可达（内网/localhost 不通），可用公网服务或内网穿透")
            items.append("  - 公网可访问：**否（阻断）**")
        elif pub is None:
            risk.append("未确认回调 URL 是否公网可访问：企业微信回调必须公网可达")
            items.append("  - 公网可访问：未确认")
        else:
            items.append("  - 公网可访问：是")
        if reachable is False:
            crit.append("回调 URL 不可达：请确认服务已启动、端口与路径正确、返回 echostr 校验通过")
            items.append("  - 可达性：**不可达（阻断）**")
        elif reachable is None:
            risk.append("未确认回调 URL 是否可达：建议用公网地址自测 GET/POST")
            items.append("  - 可达性：未确认")
        else:
            items.append("  - 可达性：可达")
        if token_filled is False:
            risk.append("Token / EncodingAESKey 未填写：接收消息与加解密需要两者，"
                        "须在后台与代码保持一致")
            items.append("  - Token/AESKey：**未填写（风险）**")
        elif token_filled is None:
            risk.append("未确认 Token/AESKey 是否填写")
            items.append("  - Token/AESKey：未确认")
        else:
            items.append("  - Token/AESKey：已填写")
        if filled(mode):
            items.append("  - 加解密模式：%s" % mode)
    elif cfg is False:
        items.append("- 接收消息：未配置（如仅需网页授权可忽略）")
    else:
        items.append("- 接收消息：未确认")
    return items, crit, risk


def check_contacts(f):
    items = []
    risk = []
    scope = get_text(f, "应用可见范围")
    contact_perm = get_text(f, "通讯录读取权限范围")
    secret_perm = get_text(f, "secret权限范围")
    ip_white = yesno(get_text(f, "是否配置IP白名单"))
    trust_ip = yesno(get_text(f, "可信IP是否配置"))
    if filled(scope):
        items.append("- 应用可见范围：%s" % scope)
    if filled(contact_perm):
        items.append("- 通讯录读取权限范围：%s" % contact_perm)
    if filled(secret_perm):
        items.append("- secret 权限范围：%s" % secret_perm)
    if ip_white is False:
        risk.append("未配置 IP 白名单：调用服务端接口若来自固定服务器，"
                    "建议配置企业可信 IP 以免触发 60020")
        items.append("- IP 白名单：**未配置（风险/60020）**")
    elif ip_white is None:
        risk.append("未确认是否配置 IP 白名单：如接口报 60020 需加入服务器出口 IP")
        items.append("- IP 白名单：未确认")
    else:
        items.append("- IP 白名单：已配置")
    if trust_ip is False:
        risk.append("可信 IP 未配置：部分接口要求可信 IP，请补充")
        items.append("- 可信 IP：**未配置（风险）**")
    elif trust_ip is None:
        items.append("- 可信 IP：未确认")
    else:
        items.append("- 可信 IP：已配置")
    return items, risk


def check_customer(f):
    items = []
    risk = []
    cust = yesno(get_text(f, "是否开通客户联系"))
    group = get_text(f, "客户群权限")
    archive = yesno(get_text(f, "是否开通会话内容存档"))
    inherit = yesno(get_text(f, "离职继承是否开启"))
    if cust is True:
        items.append("- 客户联系：已开通")
        if filled(group):
            items.append("  - 客户群权限：%s" % group)
        if inherit is False:
            risk.append("未开启离职继承：员工离职后客户资源易流失，建议开启离职继承")
            items.append("  - 离职继承：**未开启（风险）**")
        elif inherit is None:
            items.append("  - 离职继承：未确认")
        else:
            items.append("  - 离职继承：已开启")
        if archive is True:
            items.append("- 会话内容存档：已开通（须员工知情同意并签署协议）")
        elif archive is False:
            items.append("- 会话内容存档：未开通（如需存档须合规告知）")
        else:
            items.append("- 会话内容存档：未确认")
    elif cust is False:
        items.append("- 客户联系：未开通")
    else:
        items.append("- 客户联系：未确认")
    return items, risk


def check_security(f):
    items = []
    crit = []
    risk = []
    secret_way = get_text(f, "应用secret保管方式")
    audit = yesno(get_text(f, "是否开启操作审计日志"))
    if filled(secret_way):
        items.append("- secret 保管方式：%s" % secret_way)
        n = norm(secret_way)
        if any(w in n for w in SECRET_RISK_WORDS):
            crit.append("secret 保管方式存在泄露风险：secret 不得硬编码、明文落库或放前端/客户端，"
                        "应存服务端安全配置并限制可读权限，定期轮换")
            items.append("  - 评估：**高风险泄露**")
    else:
        risk.append("未说明 secret 保管方式：secret 是应用最高凭证，须服务端安全管理")
        items.append("- secret 保管方式：未说明")
    if audit is False:
        risk.append("未开启操作审计日志：建议开启以便追溯配置变更与接口调用异常")
        items.append("- 操作审计日志：**未开启（风险）**")
    elif audit is None:
        items.append("- 操作审计日志：未确认")
    else:
        items.append("- 操作审计日志：已开启")
    return items, crit, risk


def check_errcode(f):
    items = []
    crit = []
    risk = []
    code = get_text(f, "最近报错码")
    if not filled(code):
        return items, crit, risk
    code = norm(code).lstrip("0") or "0"
    # 提取数字部分
    m = re.search(r"\d+", code)
    num = m.group(0) if m else code
    info = ERRCODES.get(num)
    if info:
        desc, fix, level = info
        items.append("- 报错码 %s：%s" % (num, desc))
        if level == "严重":
            crit.append("报错 %s：%s。处置：%s" % (num, desc, fix))
        else:
            risk.append("报错 %s：%s。处置：%s" % (num, desc, fix))
    else:
        items.append("- 报错码 %s：未在常见映射表中，请对照企业微信官方错误码文档" % num)
        risk.append("报错码 %s 未识别：建议查阅企业微信官方 errcode 文档定位" % num)
    errmsg = get_text(f, "报错信息")
    if filled(errmsg):
        items.append("  - 报错信息：%s" % errmsg)
    return items, crit, risk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="")
    args = ap.parse_args()
    f = parse_md(args.path)
    if not f or not any(filled(v) for v in f.values()):
        print("# 待补正\n\n未读取到任何有效字段，请填写采集表后再排查。")
        return 2

    crit = []
    risk = []
    sections = []

    atype = get_text(f, "应用类型")
    aname = get_text(f, "应用名称")
    header = "# 企业微信应用与配置排查报告"
    if filled(aname) or filled(atype):
        header += "：%s%s" % (("%s " % atype if filled(atype) else ""),
                             ("· %s" % aname if filled(aname) else ""))
    sections.append(header)
    sections.append("")

    d_items, d_c, d_r = check_domain(f)
    crit += d_c
    risk += d_r
    c_items, c_c, c_r = check_callback(f)
    crit += c_c
    risk += c_r
    ct_items, ct_r = check_contacts(f)
    risk += ct_r
    cu_items, cu_r = check_customer(f)
    risk += cu_r
    s_items, s_c, s_r = check_security(f)
    crit += s_c
    risk += s_r
    e_items, e_c, e_r = check_errcode(f)
    crit += e_c
    risk += e_r

    if crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"

    summary = "## 一、结论摘要\n\n"
    summary += "- 总体结论：**%s**（阻断项 %d / 风险项 %d）\n" % (verdict, len(crit), len(risk))
    if filled(atype):
        summary += "- 应用类型：%s\n" % atype
    if filled(aname):
        summary += "- 应用名称：%s\n" % aname
    summary += "- 处置建议：先修复阻断项（可信域名/回调/报错码/secret 泄露），再处理风险项。\n"
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 可信域名与网页授权\n" + "\n".join(d_items) + "\n\n"
    body += "### 消息接收回调\n" + "\n".join(c_items) + "\n\n"
    body += "### 通讯录与权限\n" + "\n".join(ct_items) + "\n\n"
    body += "### 客户联系与存档\n" + "\n".join(cu_items) + "\n\n"
    body += "### 安全\n" + "\n".join(s_items) + "\n\n"
    body += "### 报错码映射\n" + ("\n".join(e_items) if e_items else "无报错码输入") + "\n"
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
        rb += "未发现明显配置阻断或风险项，配置基本合规。\n\n"
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
                "- 本核查依据通用配置经验与公开报错码整理，不替代企业微信管理后台与官方文档。\n"
                "- 报错码最终以企业微信官方 errcode 文档为准；本技能不承诺配置一定可用。\n"
                "- secret 属高敏感凭证，任何情况下不得明文分发或前端暴露。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
