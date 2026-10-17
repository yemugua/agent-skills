# -*- coding: utf-8 -*-
"""小程序审核被拒排查与整改脚本。

输入：Markdown 采集表（| 字段 | 值 | 表格 或 字段：值 冒号行）
输出：9 段报告，含结论摘要、驳回原因归类与整改、类目与资质、功能与内容、
      隐私与授权、技术可用性与提审材料、复提与申诉路径、待办整改动作、边界与纪律。

只做排查指引与整改建议，不代替平台审核结论，不承诺审核通过。
退出码：0 正常；2 关键信息缺失（打印提示，不崩）。
"""
import argparse
import json
import os
import re
import sys

FIELD_ALIAS = {
    "小程序名称": ["小程序名称", "名称", "app名称"],
    "小程序主体类型": ["小程序主体类型", "主体类型", "主体性质", "主体"],
    "主营服务类目": ["主营服务类目", "服务类目", "主营类目", "所选类目"],
    "小程序类型": ["小程序类型", "应用类型", "业务类型"],
    "是否已完成备案": ["是否已完成备案", "是否备案", "备案情况", "icp备案"],
    "是否已认证": ["是否已认证", "是否认证", "认证情况"],
    "审核结果": ["审核结果", "审核状态", "提审结果"],
    "被拒次数": ["被拒次数", "驳回次数", "被拒次数次", "第几次被拒"],
    "官方驳回原因原文": ["官方驳回原因原文", "驳回原因", "驳回理由", "官方驳回原因",
                   "审核意见", "驳回原文"],
    "驳回涉及页面或功能": ["驳回涉及页面或功能", "涉及页面", "涉及功能", "驳回位置"],
    "是否已整改": ["是否已整改", "是否整改", "整改情况"],
    "整改说明": ["整改说明", "整改内容", "已做修改"],
    "是否涉及特殊类目": ["是否涉及特殊类目", "是否特殊类目", "特殊行业"],
    "特殊类目名称": ["特殊类目名称", "特殊类目", "所属行业", "具体行业"],
    "是否已上传资质证件": ["是否已上传资质证件", "是否上传资质", "资质上传情况", "是否有资质"],
    "资质是否在有效期内": ["资质是否在有效期内", "资质有效期", "资质是否过期"],
    "服务类目与页面内容是否一致": ["服务类目与页面内容是否一致", "类目是否一致",
                         "页面内容是否一致", "类目与内容一致性"],
    "是否含用户生成内容": ["是否含用户生成内容", "是否有ugc", "是否ugc", "用户发布内容",
                     "是否有评论发帖"],
    "是否有内容审核机制": ["是否有内容审核机制", "内容审核机制", "是否有审核机制", "内容安全"],
    "是否含支付或交易功能": ["是否含支付或交易功能", "是否含支付", "是否有交易", "支付功能"],
    "是否含诱导分享关注": ["是否含诱导分享关注", "是否诱导分享", "是否诱导关注", "诱导分享"],
    "是否含外链跳转或引导下载": ["是否含外链跳转或引导下载", "是否含外链", "是否引导下载",
                        "是否有跳转"],
    "是否收集用户手机号位置相册": ["是否收集用户手机号位置相册", "是否收集用户信息",
                         "是否收集手机号", "是否获取位置", "是否读取相册"],
    "是否已配置隐私保护指引": ["是否已配置隐私保护指引", "隐私保护指引", "是否配置隐私",
                       "隐私协议"],
    "是否含虚拟支付": ["是否含虚拟支付", "虚拟支付", "是否虚拟支付", "虚拟物品购买"],
    "是否提供测试账号": ["是否提供测试账号", "测试账号是否提供", "有无测试账号"],
    "测试账号": ["测试账号", "审核账号", "体验账号"],
    "测试密码": ["测试密码", "审核密码", "体验密码"],
    "审核页面是否可正常打开": ["审核页面是否可正常打开", "页面是否正常", "是否白屏",
                      "是否能打开"],
    "是否有未完成或空白页面": ["是否有未完成或空白页面", "是否有空白页面", "是否有未完成页面",
                      "页面是否完备"],
    "是否含测试数据或占位内容": ["是否含测试数据或占位内容", "是否有测试数据", "是否有占位内容",
                        "是否有示例数据"],
    "是否已申诉": ["是否已申诉", "是否申诉", "申诉情况"],
    "申诉渠道": ["申诉渠道", "申诉方式", "反馈渠道"],
    "期望结果": ["期望结果", "诉求", "希望怎么解决"],
}

EMPTY_TOKENS = (
    "", "-", "--", "/", "|", "无", "未知", "不详", "待填", "待补", "待确认",
    "不清楚", "不知道", "没填", "未填写", "空", "暂无", "n/a", "na",
    "null", "none", "？", "?", "填什么", "做没做",
)

# 驳回类型库：(类型名, 关键词, 说明, 整改动作)
REJECT_RULES = [
    ("类目不符", ["类目不符", "服务类目", "类目选择", "与实际不符", "所选类目",
               "类目不匹配", "经营范围", "类目不一致", "超出类目"],
     "服务类目与实际提供的服务不一致",
     "在「设置 → 基本设置 → 服务类目」核对并选择与实际页面一致的类目，类目变更生效后再提审。"),
    ("资质缺失", ["资质", "许可证", "证件", "icp", "备案", "营业执照", "许可",
               "审批文件", "证照", "未提供相关材料"],
     "缺少行业资质或备案材料",
     "在「设置 → 基本设置 → 资质管理」提交对应资质原件照片，确认在有效期内；特殊行业需先取得主管部门许可。"),
    ("内容违规", ["违规", "违法", "色情", "赌博", "暴力", "侵权", "虚假", "夸大",
               "敏感", "不实", "谣言", "低俗"],
     "页面内容存在违规或不实表述",
     "删除违规文案与图片，复核宣传用语是否有绝对化用语与虚假承诺；涉及第三方内容需取得授权。"),
    ("诱导分享关注", ["诱导分享", "诱导关注", "集赞", "打卡", "转发", "拉新",
                 "邀请奖励", "分享后才能", "分享得"],
     "存在以利益诱导分享、关注、集赞的设计",
     "移除「分享/关注/集赞后才能使用」的强制入口与奖励文案，功能不得以分享为前置条件。"),
    ("外链与引导下载", ["外链", "外部链接", "引导下载", "下载app", "跳转至",
                  "引导至", "二维码引流", "站外"],
     "存在跳转外部页面或引导下载 App 的行为",
     "移除跳外部 App 与站外下载的引导；确需展示网页的，使用 web-view 并配置已备案的业务域名，且须在类目允许范围内。"),
    ("隐私与授权", ["隐私", "用户信息", "授权", "手机号", "位置", "相册",
                "通讯录", "个人信息", "过度收集", "强制授权"],
     "用户信息的收集或授权方式不符合隐私保护要求",
     "在「设置 → 服务内容声明 → 用户隐私保护指引」中如实配置并同步到代码；只在必要时申请授权，不得强制授权才能使用基础功能。"),
    ("技术缺陷", ["白屏", "报错", "无法打开", "闪退", "加载失败", "页面空白",
               "功能不可用", "无法登录", "测试账号", "崩溃", "无响应", "超时"],
     "页面存在白屏、报错或审核账号无法登录等技术问题",
     "提供真实可用的测试账号与密码并写在提审备注里；修复路径上所有页面报错，确保审核人员可走完全流程。"),
    ("未完成或占位", ["未完成", "开发中", "敬请期待", "占位", "示例", "测试数据",
                 "临时", "正在建设"],
     "存在未完成页面、空白页或占位测试数据",
     "补齐页面内容，移除占位与测试数据；未开发完成的功能入口先下线再提审。"),
    ("名称侵权", ["名称侵权", "商标", "重名", "命名", "涉及他人", "名称不规范"],
     "小程序名称与既有主体或商标存在混淆",
     "修改名称避免与已有小程序、品牌或商标混淆；如确有权属，准备商标或授权材料备查。"),
    ("支付合规", ["支付", "虚拟支付", "ios", "苹果", "虚拟物品", "充值", "币种", "代币"],
     "支付或虚拟物品交易方式不符合平台规则",
     "核对支付场景与类目是否匹配；虚拟内容在 iOS 端需遵守平台虚拟支付相关规则，不得绕开规则引导支付。"),
    ("UGC 审核机制", ["ugc", "评论", "发帖", "用户发布", "内容安全", "审核机制",
                  "社区", "留言", "上传"],
     "用户可发布内容但缺少内容审核机制",
     "接入内容安全检测接口，配置先审后发或先发后审策略，并保留举报入口与处置记录。"),
]

# 特殊类目 → 所需资质提示
SPECIAL_CATS = {
    "医疗": "医疗机构执业许可证等医疗卫生相关资质",
    "金融": "金融业务相关许可或备案材料（涉及借贷、理财、征信等须持牌）",
    "教育": "办学许可或教育相关资质，涉及学科类培训另有专门规定",
    "直播": "网络文化经营许可证、信息网络传播视听节目许可证等",
    "游戏": "游戏版号、ISBN 等游戏出版与运营相关材料",
    "药品": "药品经营许可证或医疗器械相关许可",
    "食品": "食品经营许可证或食品生产相关许可",
    "出版": "出版物经营相关许可",
    "宗教": "宗教活动场所或主管部门相关材料（宗教内容限制严格）",
    "招聘": "人力资源服务许可证",
    "婚恋": "相关经营资质与用户实名认证机制",
    "酒类": "酒类经营相关许可",
}


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


def parse_num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("，", "")
    s = re.sub(r"[¥￥元人民币rmb$个次]", "", s)
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


def check_reject(f):
    """驳回原因归类：返回 (命中类型列表, 高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    hits = []
    reason = get_text(f, "官方驳回原因原文")
    page = get_text(f, "驳回涉及页面或功能")
    fixed = yesno(get_text(f, "是否已整改"))
    times = parse_num(get_text(f, "被拒次数"))
    result = get_text(f, "审核结果")

    items.append("审核结果：%s" % (result if filled(result) else "未填写"))
    items.append("被拒次数：%s" % (fmt_num(times) if times is not None else "未填写"))
    items.append("涉及页面或功能：%s" % (page if filled(page) else "未填写"))

    if not filled(reason):
        items.append("**未填写官方驳回原因原文**：驳回原文是归类与整改的依据，"
                     "请把平台通知里的原文完整粘贴进来")
        return hits, crit, risk, items

    n_reason = norm(reason)
    for name, kws, desc, fix in REJECT_RULES:
        if any(k in n_reason for k in kws):
            hits.append(name)
            line = "%s：%s" % (name, desc)
            if fixed is True:
                risk.append("%s —— 已填「已整改」，需确认整改是否覆盖此项：%s" % (line, fix))
            else:
                crit.append("%s —— 整改动作：%s" % (line, fix))

    if not hits:
        items.append("驳回原文未匹配到常见类型，建议按原文逐句对照平台运营规范，"
                     "并把原文关键句单独列出后再核查")
    else:
        items.append("命中驳回类型 %d 类：%s" % (len(hits), "、".join(hits)))

    if times is not None and times >= 3:
        crit.append("已被拒 %s 次：反复提审不通过时不要盲目再提，"
                    "先把本报告的整改项全部落地并留存整改截图" % fmt_num(times))
    elif times is not None and times >= 2:
        risk.append("已被拒 %s 次：建议一次改到位，避免连续驳回影响后续审核" % fmt_num(times))

    if fixed is True:
        items.append("已填「已整改」，整改说明：%s" % (get_text(f, "整改说明") or "未填写具体内容"))
    elif fixed is False:
        risk.append("尚未整改：请按上列整改动作逐项处理后再提审")
    return hits, crit, risk, items


def check_category(f):
    """类目与资质：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    cat = get_text(f, "主营服务类目")
    special = yesno(get_text(f, "是否涉及特殊类目"))
    special_name = get_text(f, "特殊类目名称")
    uploaded = yesno(get_text(f, "是否已上传资质证件"))
    valid = yesno(get_text(f, "资质是否在有效期内"))
    consistent = yesno(get_text(f, "服务类目与页面内容是否一致"))
    beian = yesno(get_text(f, "是否已完成备案"))

    items.append("主营服务类目：%s" % (cat if filled(cat) else "未填写"))
    items.append("是否涉及特殊类目：%s" % ("是" if special is True else "否" if special is False else "未填写"))

    if consistent is False:
        crit.append("服务类目与页面内容不一致：提审必被拒，先把类目与内容对齐")
    elif consistent is None:
        risk.append("未填写「服务类目与页面内容是否一致」，这是审核的首要看点")

    if special is True:
        matched = [c for c in SPECIAL_CATS if c in norm(special_name)]
        if matched:
            for c in matched:
                crit.append("涉及特殊类目「%s」：需准备%s" % (c, SPECIAL_CATS[c]))
        else:
            risk.append("已填涉及特殊类目但未填具体类目名称，无法判断需要哪些资质；"
                        "常见需资质类目：%s" % "、".join(list(SPECIAL_CATS)[:6]))
        if uploaded is False:
            crit.append("涉及特殊类目但未上传资质证件：先在资质管理页提交材料，再提审")
        elif uploaded is None:
            risk.append("未填写是否已上传资质证件")
        if uploaded is True and valid is False:
            crit.append("资质已上传但不在有效期内：过期资质等同无效，需更新后重传")
        elif uploaded is True and valid is None:
            risk.append("未填写资质是否在有效期内，请核对证件有效期")
    elif special is None:
        risk.append("未填写是否涉及特殊类目；医疗、金融、教育、直播、游戏、食品等均需专门资质")

    if beian is False:
        crit.append("尚未完成小程序备案：按工信部与平台要求，未备案的小程序无法上架，"
                    "需在公众平台完成备案后再提审")
    elif beian is None:
        risk.append("未填写是否已完成备案，备案状态直接影响能否发布上线")
    return crit, risk, items


def check_content(f):
    """功能与内容：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    ugc = yesno(get_text(f, "是否含用户生成内容"))
    audit = yesno(get_text(f, "是否有内容审核机制"))
    pay = yesno(get_text(f, "是否含支付或交易功能"))
    induce = yesno(get_text(f, "是否含诱导分享关注"))
    outlink = yesno(get_text(f, "是否含外链跳转或引导下载"))
    vpay = yesno(get_text(f, "是否含虚拟支付"))

    items.append("是否含用户生成内容：%s" % ("是" if ugc is True else "否" if ugc is False else "未填写"))
    items.append("是否含支付或交易功能：%s" % ("是" if pay is True else "否" if pay is False else "未填写"))

    if induce is True:
        crit.append("含诱导分享/关注/集赞：属明确违规设计，必须移除后再提审")
    elif induce is None:
        risk.append("未填写是否含诱导分享关注，请自查是否有「分享后解锁」类设计")

    if outlink is True:
        crit.append("含外链跳转或引导下载：移除站外引导；确需网页的用 web-view 并配置业务域名")
    elif outlink is None:
        risk.append("未填写是否含外链跳转或引导下载")

    if ugc is True:
        if audit is False:
            crit.append("含用户发布内容但无内容审核机制：需接入内容安全检测并配置审核策略")
        elif audit is None:
            risk.append("含用户发布内容但未填写是否有审核机制，审核必查此项")
    elif ugc is None:
        risk.append("未填写是否含用户生成内容（评论、发帖、上传等均属此类）")

    if vpay is True:
        risk.append("含虚拟支付：需核对 iOS 端虚拟物品交易是否符合平台虚拟支付规则，"
                    "不得引导绕开规则支付")
    elif vpay is None:
        risk.append("未填写是否含虚拟支付；涉及虚拟物品购买的需单独确认合规")

    if pay is True:
        risk.append("含支付或交易功能：需确认服务类目支持交易，并核对经营主体与结算资质")
    return crit, risk, items


def check_privacy(f):
    """隐私与授权：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    collect = yesno(get_text(f, "是否收集用户手机号位置相册"))
    guide = yesno(get_text(f, "是否已配置隐私保护指引"))

    items.append("是否收集用户手机号/位置/相册：%s" %
                 ("是" if collect is True else "否" if collect is False else "未填写"))
    items.append("是否已配置隐私保护指引：%s" %
                 ("是" if guide is True else "否" if guide is False else "未填写"))

    if collect is True and guide is False:
        crit.append("收集用户信息但未配置隐私保护指引：属高发驳回原因，"
                    "需在服务内容声明中配置并同步到代码")
    elif collect is True and guide is None:
        risk.append("收集用户信息但未填写是否已配置隐私保护指引，请核实")
    elif collect is None:
        risk.append("未填写是否收集用户信息；手机号、位置、相册、通讯录均在此列")
    if guide is False and collect is not True:
        risk.append("未配置隐私保护指引：即使当前不收集，后续接入授权时仍需补齐")
    return crit, risk, items


def check_tech(f):
    """技术可用性：返回 (高危项, 风险项, 说明列表)。"""
    crit = []
    risk = []
    items = []
    has_acct = yesno(get_text(f, "是否提供测试账号"))
    acct = get_text(f, "测试账号")
    pwd = get_text(f, "测试密码")
    openok = yesno(get_text(f, "审核页面是否可正常打开"))
    blank = yesno(get_text(f, "是否有未完成或空白页面"))
    dummy = yesno(get_text(f, "是否含测试数据或占位内容"))

    if has_acct is True:
        if filled(acct) and filled(pwd):
            items.append("已提供测试账号：%s / 密码已填（提审时请填写到备注）" % acct)
        else:
            crit.append("已填提供测试账号，但测试账号或密码未填写完整："
                        "审核人员无法登录会直接驳回")
    elif has_acct is False:
        crit.append("未提供测试账号：需要登录才能体验的功能，无账号必被驳回")
    else:
        risk.append("未填写是否提供测试账号；有登录态的小程序必须提供可用账号")

    if openok is False:
        crit.append("审核页面无法正常打开（白屏/报错/闪退）：先修复并真机自测全流程")
    elif openok is None:
        risk.append("未填写审核页面是否可正常打开，建议提审前用真机走一遍审核路径")

    if blank is True:
        crit.append("存在未完成或空白页面：先下线未完成入口，或补齐内容")
    elif blank is None:
        risk.append("未填写是否有未完成或空白页面")

    if dummy is True:
        risk.append("含测试数据或占位内容：审核会视为内容不完整，建议替换为真实内容")
    elif dummy is None:
        risk.append("未填写是否含测试数据或占位内容")
    return crit, risk, items


def check_dispose(f):
    """申诉与期望：返回说明列表。"""
    items = []
    appealed = yesno(get_text(f, "是否已申诉"))
    channel = get_text(f, "申诉渠道")
    want = get_text(f, "期望结果")
    if appealed is True:
        items.append("已申诉，渠道：%s —— 请保留申诉单号与回复截图" % (channel or "未填写"))
    elif appealed is False:
        items.append("尚未申诉：若认为驳回有误，可在公众平台提交申诉并附整改说明与截图")
    else:
        items.append("未填写是否已申诉")
    items.append("期望结果：%s" % (want if filled(want) else "未填写"))
    return items


def build_report(f):
    rep = []
    crit = []
    risk = []
    todo = []

    name = get_text(f, "小程序名称")
    reason = get_text(f, "官方驳回原因原文")
    fixed = yesno(get_text(f, "是否已整改"))

    hits, r_crit, r_risk, r_items = check_reject(f)
    c_crit, c_risk, c_items = check_category(f)
    t_crit, t_risk, t_items = check_content(f)
    p_crit, p_risk, p_items = check_privacy(f)
    e_crit, e_risk, e_items = check_tech(f)
    d_items = check_dispose(f)

    core_missing = not (filled(name) or filled(reason))
    if not core_missing:
        crit.extend(r_crit)
        crit.extend(c_crit)
        crit.extend(t_crit)
        crit.extend(p_crit)
        crit.extend(e_crit)
        risk.extend(r_risk)
        risk.extend(c_risk)
        risk.extend(t_risk)
        risk.extend(p_risk)
        risk.extend(e_risk)

    if core_missing:
        verdict = "待补正"
    elif crit:
        verdict = "不通过"
    elif risk:
        verdict = "有风险"
    else:
        verdict = "通过"

    VERDICT_TEXT = {"通过": "可直接复提", "有风险": "建议整改后复提",
                    "不通过": "需整改后复提", "待补正": "待补正"}

    # 1 结论摘要
    rep.append("## 结论摘要")
    rep.append("")
    rep.append("- 小程序：%s" % (name if filled(name) else "未填写"))
    rep.append("- 命中驳回类型 %d 类：%s" % (len(hits), "、".join(hits) if hits else "未识别"))
    rep.append("- 阻断项（必须改）%d 项 / 风险项（建议改）%d 项" % (len(crit), len(risk)))
    rep.append("- 是否已整改：%s" % ("是" if fixed is True else "否" if fixed is False else "未填写"))
    rep.append("- **总体结论：%s（%s）**" % (verdict, VERDICT_TEXT[verdict]))
    rep.append("")

    # 2 驳回原因归类
    rep.append("## 驳回原因归类与整改")
    rep.append("")
    for it in r_items:
        rep.append("- %s" % it)
    for c in r_crit:
        rep.append("- **%s**" % c)
    for r in r_risk:
        rep.append("- %s" % r)
    if filled(reason):
        rep.append("- 驳回原文摘录：%s" % str(reason)[:200])
    rep.append("")

    # 3 类目与资质
    rep.append("## 类目、资质与备案核查")
    rep.append("")
    for it in c_items:
        rep.append("- %s" % it)
    for c in c_crit:
        rep.append("- **%s**" % c)
    for r in c_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 4 功能与内容
    rep.append("## 功能与内容合规核查")
    rep.append("")
    for it in t_items:
        rep.append("- %s" % it)
    for c in t_crit:
        rep.append("- **%s**" % c)
    for r in t_risk:
        rep.append("- %s" % r)
    rep.append("")

    # 5 隐私与授权
    rep.append("## 隐私与授权核查")
    rep.append("")
    for it in p_items:
        rep.append("- %s" % it)
    for c in p_crit:
        rep.append("- **%s**" % c)
    for r in p_risk:
        rep.append("- %s" % r)
    rep.append("- 配置入口：公众平台 → 设置 → 服务内容声明 → 用户隐私保护指引，"
               "配置后需在代码中同步调用对应授权接口。")
    rep.append("")

    # 6 技术可用性
    rep.append("## 技术可用性与提审材料")
    rep.append("")
    for it in e_items:
        rep.append("- %s" % it)
    for c in e_crit:
        rep.append("- **%s**" % c)
    for r in e_risk:
        rep.append("- %s" % r)
    rep.append("- 提审材料建议：可用测试账号密码、功能路径说明、整改前后对比截图、"
               "资质证件照片、类目说明。")
    rep.append("")

    # 7 复提与申诉
    rep.append("## 复提与申诉路径")
    rep.append("")
    for it in d_items:
        rep.append("- %s" % it)
    rep.append("- 复提顺序：先改阻断项 → 真机全流程自测 → 补齐提审材料 → 提交审核。")
    rep.append("- 若驳回原因与页面实际不符，可在公众平台「反馈与申诉」提交说明并附截图；"
               "涉及类目争议的，可同步申请类目变更或补充资质说明。")
    rep.append("- 被拒 3 次以上的，建议先把整改项逐条落地并截图留档，再一次性提审。")
    rep.append("")

    # 8 待办
    rep.append("## 待办整改动作")
    rep.append("")
    if core_missing:
        todo.append("补齐「小程序名称」与「官方驳回原因原文」——这是归类与整改的前提")
    for c in crit:
        todo.append("整改（阻断项）：%s" % c.split("——")[0])
    if not hits and filled(reason):
        todo.append("驳回原文未匹配常见类型：逐句对照平台运营规范定位问题")
    if not filled(get_text(f, "是否涉及特殊类目")):
        todo.append("确认是否涉及医疗/金融/教育/直播/游戏/食品等特殊类目")
    if not filled(get_text(f, "是否已完成备案")):
        todo.append("确认小程序备案状态，未备案的需先在公众平台完成备案")
    if yesno(get_text(f, "是否提供测试账号")) is not True:
        todo.append("准备可用的测试账号与密码，并填写到提审备注")
    if not filled(get_text(f, "期望结果")):
        todo.append("明确期望结果：直接复提 / 整改后复提 / 申诉 / 变更类目")
    if not todo:
        todo.append("未发现明显阻断项，按报告建议完善后即可复提")
    for i, t in enumerate(todo, 1):
        rep.append("%d. %s" % (i, t))
    rep.append("")

    # 9 边界
    rep.append("## 边界与纪律")
    rep.append("")
    rep.append("- 本结果依通用规则与公开运营规范整理，不代替平台审核结论，"
               "最终以微信公众平台审核结果与官方运营规范为准。")
    rep.append("- 驳回原因的**唯一权威来源是平台下发的审核意见原文**，"
               "请以其为准逐项对照整改。")
    rep.append("- **本技能只做排查指引与整改建议，不承诺审核通过，"
               "不代为提交审核，也不提供任何资质办理服务。**")
    rep.append("- 涉及医疗、金融、教育、出版等特殊行业的，须先取得主管部门许可资质。")

    return "\n".join(rep), verdict, crit + risk, todo


def main():
    ap = argparse.ArgumentParser(description="小程序审核被拒排查与整改")
    ap.add_argument("md", nargs="?", default="样例.md")
    ap.add_argument("--input", dest="input", default=None)
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

    if not filled(get_text(f, "小程序名称")) and not filled(get_text(f, "官方驳回原因原文")):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
