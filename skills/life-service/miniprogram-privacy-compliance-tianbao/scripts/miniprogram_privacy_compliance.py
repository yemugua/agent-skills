# -*- coding: utf-8 -*-
"""小程序个人信息保护合规核查脚本（PIPL + 微信平台隐私规则向）。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：多段报告，含结论摘要、隐私协议核查、授权与同意核查、第三方 SDK 与共享清单核查、
      敏感个人信息核查、用户权利功能核查、数据安全核查、操作指引、边界。

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
    "主体类型": ["主体类型", "小程序主体", "账号主体", "主体"],
    "小程序是否已上线": ["小程序是否已上线", "是否上线", "上线状态", "是否已发布"],
    "是否收集个人信息": ["是否收集个人信息", "是否收集信息", "收集个人信息"],
    "收集的信息类型": ["收集的信息类型", "信息类型", "收集哪些信息", "收集范围", "收集了哪些信息"],
    "是否配置用户隐私保护指引": ["是否配置用户隐私保护指引", "用户隐私保护指引", "隐私指引",
                              "隐私协议", "隐私政策", "是否配置隐私协议"],
    "隐私协议是否列明目的范围期限": ["隐私协议是否列明目的范围期限", "隐私协议是否完整", "协议是否列明目的",
                                "是否列明保存期限", "协议内容完整"],
    "是否在使用隐私接口前取得同意": ["是否在使用隐私接口前取得同意", "是否取得同意", "授权弹窗",
                               "隐私授权", "同意机制", "是否弹窗征得同意"],
    "拒绝授权后是否仍可用基础功能": ["拒绝授权后是否仍可用基础功能", "拒绝授权后可用", "拒绝后是否强制退出",
                              "拒绝授权处理"],
    "是否使用第三方SDK或插件": ["是否使用第三方SDK或插件", "是否使用第三方sdk", "三方sdk", "第三方插件",
                            "sdk", "插件"],
    "是否已申报SDK与共享清单": ["是否已申报SDK与共享清单", "sdk申报", "第三方sdk申报",
                            "信息共享清单", "共享清单", "是否申报第三方"],
    "是否收集敏感个人信息": ["是否收集敏感个人信息", "敏感个人信息", "是否收集敏感信息", "敏感信息"],
    "敏感信息是否单独同意": ["敏感信息是否单独同意", "单独同意", "敏感信息同意方式"],
    "是否提供账号注销": ["是否提供账号注销", "账号注销", "注销功能", "注销账号", "能否注销"],
    "是否支持查阅复制更正删除": ["是否支持查阅复制更正删除", "查阅复制更正删除", "个人信息副本",
                            "查询更正删除", "权利功能"],
    "是否加密传输与存储": ["是否加密传输与存储", "加密传输", "是否加密", "数据加密", "传输加密"],
    "是否落实未成年人监护人同意": ["是否落实未成年人监护人同意", "未成年人", "监护人同意",
                             "儿童个人信息", "青少年模式"],
    "是否有违规收集或通报整改历史": ["是否有违规收集或通报整改历史", "违规收集", "通报", "整改历史",
                            "是否被通报", "监管通报"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

NEG_WORDS = ("否", "没有", "未", "不", "无", "否认", "拒绝", "不知情", "没做", "无法", "没")
POS_WORDS = ("是", "已", "有", "承认", "确认", "同意", "认可", "已做", "可以", "做过", "完成")

# 敏感个人信息类型关键词（PIPL 第 28 条）
SENSITIVE_WORDS = ("生物识别", "人脸", "指纹", "身份证", "银行卡", "金融账户", "行踪", "位置",
                   "医疗", "健康", "病历", "宗教信仰", "特定身份", "精确位置", "14岁以下", "14岁")


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


def is_sensitive(types_txt):
    if not filled(types_txt):
        return False
    n = norm(types_txt)
    return any(w in n for w in SENSITIVE_WORDS)


def check_policy(f):
    """隐私协议/用户隐私保护指引核查。"""
    items, crit, risk = [], [], []
    guide = yesno(get_text(f, "是否配置用户隐私保护指引"))
    complete = yesno(get_text(f, "隐私协议是否列明目的范围期限"))
    collect = yesno(get_text(f, "是否收集个人信息"))

    if collect is False:
        items.append("- 是否收集个人信息：否（不收集则协议项可简化，但小程序基本功能仍需服务协议）")
    elif collect is True:
        items.append("- 是否收集个人信息：是")
    else:
        items.append("- 是否收集个人信息：未确认")

    if guide is False:
        crit.append("未配置「用户隐私保护指引」：微信小程序平台要求在小程序管理后台"
                    "（设置-基本设置-服务内容声明）配置用户隐私保护指引，并覆盖第三方信息共享清单，"
                    "否则将影响隐私相关接口调用乃至被下架")
        items.append("- 用户隐私保护指引：未配置（阻断）")
    elif guide is True:
        items.append("- 用户隐私保护指引：已配置")
    else:
        crit.append("未确认是否配置用户隐私保护指引：这是平台对小程序隐私合规的硬性要求，请先在后台配置")
        items.append("- 用户隐私保护指引：未确认（阻断）")

    if complete is False:
        risk.append("隐私协议未完整列明收集目的、范围与保存期限：应按 PIPL 第十七条告知处理者名称、"
                    "联系方式、目的、方式、信息种类、保存期限及行使权利的方式程序")
        items.append("- 协议内容完整度：不完整（风险）")
    elif complete is True:
        items.append("- 协议内容完整度：已列明目的/范围/期限")
    else:
        items.append("- 协议内容完整度：未确认")
    return items, crit, risk


def check_consent(f):
    """授权与同意机制核查。"""
    items, crit, risk = [], [], []
    consent = yesno(get_text(f, "是否在使用隐私接口前取得同意"))
    reject = yesno(get_text(f, "拒绝授权后是否仍可用基础功能"))

    if consent is False:
        crit.append("未在使用隐私接口前取得用户同意：微信要求调用隐私接口（getPhoneNumber/location/"
                    "chooseImage 等）前通过隐私授权弹窗取得同意（wx.getPrivacySetting / requirePrivacyAuthorize），"
                    "未经同意调用将被平台拦截并处罚")
        items.append("- 隐私授权同意：未取得（阻断）")
    elif consent is True:
        items.append("- 隐私授权同意：已取得")
    else:
        crit.append("未确认是否在使用隐私接口前取得同意：隐私接口必须「先弹窗同意、后调用」，请确认")
        items.append("- 隐私授权同意：未确认（阻断）")

    if reject is False:
        risk.append("拒绝授权后不可用基础功能：用户拒绝提供非必要信息时，不得拒绝提供基础功能或强制退出，"
                    "除非该信息为业务所必需；建议区分「必要信息」与「可选信息」分别处理")
        items.append("- 拒绝授权处理：强制退出/不可用（风险）")
    elif reject is True:
        items.append("- 拒绝授权处理：基础功能仍可用")
    else:
        items.append("- 拒绝授权处理：未确认")
    return items, crit, risk


def check_sdk(f):
    """第三方 SDK 与信息共享清单核查。"""
    items, crit, risk = [], [], []
    uses = yesno(get_text(f, "是否使用第三方SDK或插件"))
    declared = yesno(get_text(f, "是否已申报SDK与共享清单"))

    if uses is False:
        items.append("- 第三方 SDK/插件：未使用（无需申报）")
        return items, crit, risk

    if uses is True:
        items.append("- 第三方 SDK/插件：使用")
    else:
        items.append("- 第三方 SDK/插件：未确认（若使用则必须申报）")

    if declared is False:
        crit.append("使用第三方 SDK/插件但未在后台申报：微信要求在小程序管理后台「第三方设置」"
                    "申报 SDK/插件并维护信息共享清单，未申报的 SDK 调用隐私接口会被拦截，且属平台违规")
        items.append("- SDK 申报与共享清单：未申报（阻断）")
    elif declared is True:
        items.append("- SDK 申报与共享清单：已申报")
    else:
        crit.append("未确认 SDK/插件是否已申报：如接入了统计/推送/地图/支付等第三方 SDK，"
                    "必须在后台申报并更新共享清单，请确认")
        items.append("- SDK 申报与共享清单：未确认（阻断）")
    return items, crit, risk


def check_sensitive(f):
    """敏感个人信息与单独同意核查。"""
    items, crit, risk = [], [], []
    types_txt = get_text(f, "收集的信息类型")
    sens = yesno(get_text(f, "是否收集敏感个人信息"))
    sep = yesno(get_text(f, "敏感信息是否单独同意"))

    if filled(types_txt):
        items.append("- 收集的信息类型：%s" % types_txt)
        if is_sensitive(types_txt):
            items.append("  - 含敏感个人信息：是（触发 PIPL 单独同意要求）")
    else:
        items.append("- 收集的信息类型：未填")

    if sens is True or (filled(types_txt) and is_sensitive(types_txt)):
        if sep is False:
            crit.append("收集敏感个人信息但未取得单独同意：PIPL 第二十九条要求处理敏感个人信息"
                        "（身份证/人脸/位置/健康/金融账户等）应取得个人单独同意，并告知必要性及影响")
            items.append("- 敏感信息单独同意：未取得（阻断）")
        elif sep is True:
            items.append("- 敏感信息单独同意：已取得")
        else:
            crit.append("收集了敏感个人信息但未确认单独同意方式：须以弹窗等显著方式单独取得同意，"
                        "不得并入一揽子协议")
            items.append("- 敏感信息单独同意：未确认（阻断）")
    elif sens is False:
        items.append("- 敏感个人信息：不涉及")
    else:
        items.append("- 敏感个人信息：未确认")
    return items, crit, risk


def check_rights(f):
    """用户权利功能核查（查阅/复制/更正/删除/注销）。"""
    items, crit, risk = [], [], []
    cancel = yesno(get_text(f, "是否提供账号注销"))
    rights = yesno(get_text(f, "是否支持查阅复制更正删除"))

    if cancel is False:
        crit.append("未提供账号注销功能：微信小程序平台运营规范要求提供账号注销途径，"
                    "且注销后应清除或匿名化个人信息；无注销入口将被平台处罚并影响审核")
        items.append("- 账号注销：未提供（阻断）")
    elif cancel is True:
        items.append("- 账号注销：已提供")
    else:
        crit.append("未确认是否提供账号注销：小程序须提供注销入口并说明注销后果，请确认")
        items.append("- 账号注销：未确认（阻断）")

    if rights is False:
        risk.append("未支持个人信息查阅、复制、更正、删除：PIPL 赋予个人查阅复制、更正补充、"
                    "删除等权利，应提供便捷入口（如设置页-个人信息管理）并在 15 个工作日内答复")
        items.append("- 查阅/复制/更正/删除：未支持（风险）")
    elif rights is True:
        items.append("- 查阅/复制/更正/删除：已支持")
    else:
        items.append("- 查阅/复制/更正/删除：未确认")
    return items, crit, risk


def check_security(f):
    """数据安全与未成年人核查。"""
    items, risk = [], []
    enc = yesno(get_text(f, "是否加密传输与存储"))
    minor = yesno(get_text(f, "是否落实未成年人监护人同意"))
    hist = yesno(get_text(f, "是否有违规收集或通报整改历史"))

    if enc is False:
        risk.append("传输与存储未加密：个人信息应采用加密传输（HTTPS/TLS）与加密存储，"
                    "云开发数据库应合理设置权限与脱敏，避免明文落库")
        items.append("- 加密传输与存储：未加密（风险）")
    elif enc is True:
        items.append("- 加密传输与存储：已加密")
    else:
        items.append("- 加密传输与存储：未确认")

    if minor is False:
        risk.append("未落实未成年人（14 岁以下）监护人同意：处理不满十四周岁未成年人个人信息"
                    "应取得监护人同意并制定专门规则，建议增加未成年人保护声明与家长控制入口")
        items.append("- 未成年人保护：未落实（风险）")
    elif minor is True:
        items.append("- 未成年人保护：已落实")
    else:
        items.append("- 未成年人保护：未确认")

    if hist is True:
        risk.append("存在违规收集/被通报整改历史：应完成整改并留存记录，再次被通报可能面临"
                    "下架、公示及监管处罚，建议做全量复查后再上线新功能")
        items.append("- 违规与整改历史：有（风险）")
    elif hist is False:
        items.append("- 违规与整改历史：无")
    else:
        items.append("- 违规与整改历史：未确认")
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
    subj_txt = get_text(f, "主体类型")
    online = get_text(f, "小程序是否已上线")

    header = "# 小程序个人信息保护合规核查报告"
    if filled(subj_txt):
        header += "（%s）" % subj_txt
    if filled(online):
        header += " · 状态：%s" % online
    sections.append(header)
    sections.append("")

    pol_items, pol_c, pol_r = check_policy(f)
    crit += pol_c; risk += pol_r
    con_items, con_c, con_r = check_consent(f)
    crit += con_c; risk += con_r
    sdk_items, sdk_c, sdk_r = check_sdk(f)
    crit += sdk_c; risk += sdk_r
    sen_items, sen_c, sen_r = check_sensitive(f)
    crit += sen_c; risk += sen_r
    rig_items, rig_c, rig_r = check_rights(f)
    crit += rig_c; risk += rig_r
    sec_items, sec_r = check_security(f)
    risk += sec_r

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
    summary += ("- 处置建议：先补齐隐私协议与授权弹窗，再落实第三方 SDK 申报、"
                "敏感信息单独同意与账号注销，最后完善加密、未成年人保护与用户权利功能。\n")
    sections.append(summary)

    body = "## 二、分项核查\n\n"
    body += "### 隐私协议与告知核查\n" + "\n".join(pol_items) + "\n\n"
    body += "### 授权与同意机制核查\n" + "\n".join(con_items) + "\n\n"
    body += "### 第三方 SDK 与信息共享清单核查\n" + "\n".join(sdk_items) + "\n\n"
    body += "### 敏感个人信息核查\n" + "\n".join(sen_items) + "\n\n"
    body += "### 用户权利功能核查（查阅/复制/更正/删除/注销）\n" + "\n".join(rig_items) + "\n\n"
    body += "### 数据安全与未成年人核查\n" + "\n".join(sec_items) + "\n"
    sections.append(body)

    rb = "## 三、阻断项与风险/待办\n\n"
    if crit:
        rb += "### 阻断项（必须处理，否则影响接口调用/审核/上架）\n"
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

    adv = ("## 四、整改操作指引（标准隐私合规清单）\n\n"
           "1. 配置「用户隐私保护指引」：小程序管理后台-设置-基本设置-服务内容声明，填写收集的信息类型、用途、第三方共享情况。\n"
           "2. 梳理信息收集清单：按最小必要原则列明收集的字段与用途，删除与功能无关的收集项。\n"
           "3. 接入隐私授权：调用隐私接口前使用隐私授权弹窗（wx.getPrivacySetting / requirePrivacyAuthorize）取得同意。\n"
           "4. 申报第三方 SDK：后台「第三方设置」申报 SDK/插件，维护信息共享清单，附第三方隐私协议链接。\n"
           "5. 敏感信息单独同意：身份证/人脸/位置/健康/金融账户等敏感信息以独立弹窗单独取得同意。\n"
           "6. 用户权利入口：提供账号注销与个人信息查阅/复制/更正/删除入口（设置页），注销后清除或匿名化数据。\n"
           "7. 数据安全：传输走 HTTPS/TLS，敏感字段加密存储，数据库按需授权并脱敏；落实未成年人监护人同意。\n"
           "8. 留存记录：保存自查与整改记录，被通报的完成整改闭环，避免重复违规。\n\n")
    sections.append(adv)

    boundary = ("## 五、边界与纪律\n\n"
                "- 本核查依据《个人信息保护法》《数据安全法》《网络安全法》、GB/T 35273-2020"
                "《信息安全技术 个人信息安全规范》及微信小程序平台公开规则整理，"
                "**不替代监管规定、平台规则与正式法律意见**，重大场景请咨询律师。\n"
                "- 敏感个人信息（生物识别、身份证、金融账户、行踪轨迹、医疗健康、14 岁以下未成年人信息等）"
                "须单独同意并采取严格保护措施。\n"
                "- 不得违规收集与功能无关的个人信息，不得因用户拒绝非必要授权而拒绝提供基础功能。\n"
                "- 向第三方提供、公开、跨境传输个人信息，应依法履行告知与单独同意义务。\n")
    sections.append(boundary)

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
