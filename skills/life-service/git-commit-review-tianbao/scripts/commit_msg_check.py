# -*- coding: utf-8 -*-
"""提交信息格式校验 + PR 尺寸分级。

用法:
  python commit_msg_check.py --selftest
  python commit_msg_check.py --file commits.txt
  python commit_msg_check.py --file pr.txt --files 42 --additions 1300

commits.txt：多条提交用单独一行 ^^^^ 分隔，每块第一行为 subject，其余为正文/footer。
同时可用 --subject 直接校验单行标题。
"""
import argparse
import io
import json
import os
import re
import sys

TYPES = ["feat", "fix", "perf", "refactor", "style", "docs", "test", "build", "ci", "chore", "revert"]
BODY_REQUIRED = ["feat", "refactor", "perf"]
RISK_TYPES = ["feat", "fix", "perf", "refactor", "revert"]

HEADER_RE = re.compile(r"^([a-z]+)(!\s*)?(\(([^)]*)\))?:\s*(.+)$")
SCOPE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
FOOTER_RE = re.compile(r"^([A-Za-z][A-Za-z \t-]*):\s*(.*)$")
VALID_FOOTERS = ["Refs", "Closes", "Resolves", "BREAKING CHANGE", "Impact", "Co-authored-by",
                 "Reviewed-by", "Skip-Reason"]
FOOTER_TYPO = {
    "Breaking Change": "BREAKING CHANGE",
    "BREAKING-CHANGE": "BREAKING CHANGE",
    "refs": "Refs",
    "closes": "Closes",
    "Close": "Closes",
    "Ref": "Refs",
    "Beadline": "Refs",
}

FAILS = []


def ck(label, cond):
    if not cond:
        FAILS.append(label)
    return bool(cond)


def write_result(path):
    lines = ["SELFTEST %s" % ("OK" if not FAILS else "FAILED")]
    for f in FAILS:
        lines.append("  FAILED: %s" % f)
    io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


def check_subject(subject):
    """校验单行标题，返回 (等级 list, 说明 list)。等级含 error/warn/info。"""
    errs, warns, infos = [], [], []
    s = subject.strip()
    if not s:
        return ["error"], ["标题为空"]
    if s.endswith("。") or s.endswith("."):
        errs.append("标题结尾不应加句号")
    m = HEADER_RE.match(s)
    if not m:
        errs.append("不符合 <type>(<scope>): <subject> 格式")
        return ["error"], errs + warns + infos
    typ = m.group(1)
    bang = bool(m.group(2))
    scope = m.group(4)
    desc = m.group(5)
    if typ not in TYPES:
        errs.append("type 非法(%s)，允许的取值: %s" % (typ, " ".join(TYPES)))
    if scope is not None:
        if scope == "":
            errs.append("scope 为空，请写成 type: xxx 不要留空括号")
        elif not SCOPE_RE.match(scope):
            errs.append("scope 只能小写英文数字与 ._- (%s)" % scope)
        elif "/" in scope:
            warns.append("scope 只保留一层(%s)" % scope)
    if len(s) > 72:
        errs.append("标题长度 %d 超过 72 字符" % len(s))
    elif len(s) > 50:
        warns.append("标题长度 %d 超过建议值 50 字符" % len(s))
    if len(desc) < 6:
        warns.append("描述过短，说不清改了什么(%s)" % desc)
    for bad in ["update code", "修复bug", "修复 bug", "提交代码", "wip", "WIP", "finish", "done", "修改"]:
        if desc.strip().lower() == bad.lower():
            warns.append("描述无信息量(%s)，请写明模块与现象" % desc)
    for word in ["了", "已", "过的"]:
        if desc.startswith(word):
            warns.append("建议用祈使句动词开头，不要以「%s」开头" % word)
    if bang:
        infos.append("含破坏性变更标记 !，正文必须写迁移方案")
    return (["error"] if errs else []) + (["warn"] if warns else []), errs + warns + infos


def check_body(subject, body_lines):
    errs, warns, infos = [], [], []
    body = [l for l in body_lines]
    body_text = "\n".join(body).strip()
    m = HEADER_RE.match(subject.strip())
    typ = m.group(1) if m else ""
    bang = bool(m.group(2)) if m else False
    need_body = (typ in BODY_REQUIRED) or bang or (typ == "revert")
    if need_body and not body_text:
        errs.append("type=%s 必须写正文%s" % (typ, "（破坏性变更要写迁移方案）" if bang else ""))
    if body_text:
        for line in body:
            if len(line) > 72 and not line.startswith("http"):
                warns.append("正文单行超过 72 字符(第 %d 字符行)" % len(line))
                break
    footers = []
    for line in body:
        fm = FOOTER_RE.match(line.strip())
        if fm and fm.group(1).lower() not in ("http", "https"):
            footers.append((fm.group(1), fm.group(2)))
    breaking = False
    for key, val in footers:
        if key in FOOTER_TYPO:
            errs.append("footer 写法错误(%s)，应为 %s" % (key, FOOTER_TYPO[key]))
        elif key not in VALID_FOOTERS:
            warns.append("footer 键名未在白名单(%s)" % key)
        if key == "BREAKING CHANGE":
            breaking = True
            if len(val) < 15:
                errs.append("BREAKING CHANGE 描述过短，必须写清「改了什么 + 怎么迁移」")
        if key in ("Closes", "Resolves") and not val.strip():
            errs.append("%s 缺少工单号" % key)
    if bang and not breaking:
        errs.append("标题带 ! 但正文没有 BREAKING CHANGE 段落")
    if breaking and not bang:
        warns.append("正文有 BREAKING CHANGE，建议标题也写成 type!:")
    if typ == "revert" and "@" not in body_text and not re.search(r"\b[0-9a-f]{7,40}\b", body_text):
        errs.append("revert 提交正文必须写明被回滚的 commit")
    return errs, warns, infos


def split_commits(text):
    blocks = []
    cur = []
    for line in text.splitlines():
        if line.strip() == "^^^^":
            blocks.append(cur)
            cur = []
        else:
            cur.append(line)
    blocks.append(cur)
    out = []
    for b in blocks:
        if not any(l.strip() for l in b):
            continue
        subject = b[0]
        rest = []
        if len(b) > 1 and b[1].strip() == "":
            rest = b[2:]
        else:
            rest = b[1:]
        if len(b) == 1:
            rest = []
        out.append((subject, rest))
    return out


def pr_grade(files, additions):
    """按 PR 尺寸分级，返回 (级别, 评审要求, 建议)。"""
    if files <= 5 and additions <= 30:
        return "XS", "1 人评审", "直接合"
    if files <= 15 and additions <= 150:
        return "S", "1 人评审", "直接合"
    if files <= 30 and additions <= 500:
        return "M", "1-2 人评审且至少 1 人为模块 owner", "正文需写清验证方式"
    if files <= 60 or additions <= 1500:
        return "L", "2 人评审 + 附测试证据", "建议按 重构/功能/格式 拆成多个 PR"
    return "XL", "不建议直接合", "必须拆 PR；自动生成与格式化结果单独成 PR"


def risk_paths(diff_text):
    """按路径关键字给出必须参与评审的角色。"""
    table = [
        ("pay refund settle account", "交易组 owner"),
        ("auth permission token crypto", "安全/基础 owner"),
        ("db/migration .sql schema", "DBA + 后端 owner"),
        ("Dockerfile k8s/ terraform/ .github/workflows", "SRE"),
        ("common/ sdk/ utils/", "架构组"),
    ]
    hits = []
    low = diff_text.lower()
    for keys, who in table:
        for k in keys.split():
            if k in low:
                hits.append((k, who))
                break
    return hits


def build_report(text, files=None, additions=None):
    commits = split_commits(text)
    lines = []
    summary = {"commits": [], "pr": None}
    lines.append("=" * 58)
    lines.append("提交信息与 PR 尺寸检查报告")
    lines.append("=" * 58)
    for i, (subject, body) in enumerate(commits, 1):
        levels, sub_msgs = check_subject(subject)
        errs, warns, infos = check_body(subject, body)
        lines.append("")
        lines.append("[提交 %d] %s" % (i, subject.strip()))
        for m in sub_msgs:
            lines.append("    - %s" % m)
        for m in errs:
            lines.append("    [错误] %s" % m)
        for m in warns:
            lines.append("    [建议] %s" % m)
        for m in infos:
            lines.append("    [提示] %s" % m)
        if not sub_msgs and not errs and not warns:
            lines.append("    通过")
        summary["commits"].append({
            "subject": subject.strip(),
            "subject_issues": sub_msgs,
            "body_errors": errs,
            "body_warnings": warns,
            "ok": not sub_msgs and not errs and not warns,
        })
    if files is not None and additions is not None:
        level, need, advice = pr_grade(files, additions)
        summary["pr"] = {"files": files, "additions": additions, "level": level,
                         "review": need, "advice": advice}
        lines.append("")
        lines.append("[PR 尺寸] 文件 %d / 改动 %d 行 -> %s 级" % (files, additions, level))
        lines.append("  评审要求: %s" % need)
        lines.append("  建议: %s" % advice)
    hits = risk_paths(text)
    if hits:
        lines.append("")
        lines.append("[必审路径]")
        for k, who in hits:
            lines.append("  命中 %s -> 需 %s 批准" % (k, who))
    summary["risk_paths"] = [{"key": k, "owner": w} for k, w in hits]
    lines.append("")
    lines.append("免责: 本工具只做格式与尺寸检查，不判断代码正确性。")
    lines.append("=" * 58)
    return "\n".join(lines), summary


def selftest():
    good = "fix(order): 修复退款单重复入账\n\n退款回调重入时未做幂等判断。\n改为以 refund_no 唯一索引兜底。\n\nRefs: PROJ-142"
    bad_type = "bugfix: 修复退款回调重入问题"
    no_colon = "fix order refund"
    trailing = "fix(order): 修复了退款问题。"
    too_long = "feat(order): " + "x" * 80
    breaking = "feat!: 移除旧的 /v1 接口"
    typo = "fix(order): 修复问题\n\nBreaking Change: 字段改名了会很麻烦需要通知调用方"
    revert = "revert: 回滚一次变更"

    r0, s0 = build_report(good)
    ck("合规样例应通过", s0["commits"][0]["ok"])

    _, s1 = check_subject(bad_type)
    ck("非法 type 应报错", any("type 非法" in m for m in s1))

    _, s2 = check_subject(no_colon)
    ck("缺冒号应报格式错误", any("格式" in m for m in s2))

    _, s3 = check_subject(trailing)
    ck("结尾句号应报错", any("句号" in m for m in s3))

    _, s4 = check_subject(too_long)
    ck("超长标题应报错", any("超过 72" in m for m in s4))

    e5, w5, _ = check_body(breaking, [])
    ck("破坏性变更缺正文应报错", any("必须写正文" in m for m in e5))

    e6, _, _ = check_body(typo, [line.strip() for line in typo.splitlines()[2:]])
    ck("Breaking Change 大小写错误应报错", any("BREAKING CHANGE" in m for m in e6))

    e7, _, _ = check_body(revert, [])
    ck("revert 缺 commit 说明应报错", any("revert" in m for m in e7))

    ck("XS 级判定", pr_grade(3, 20)[0] == "XS")
    ck("M 级判定", pr_grade(25, 400)[0] == "M")
    ck("L 级判定", pr_grade(45, 200)[0] == "L")
    ck("XL 级判定", pr_grade(80, 3000)[0] == "XL")

    hits = risk_paths("src/pay/refund.js\nk8s/deploy.yaml")
    ck("命中支付路径", any(k == "pay" for k, _ in hits))
    ck("命中 k8s 路径", any(k == "k8s/" for k, _ in hits))

    multi = good + "\n^^^^\n" + bad_type
    _, sm = build_report(multi, files=5, additions=20)
    ck("多提交解析应为 2 条", len(sm["commits"]) == 2)
    ck("第二提交应标记不通过", sm["commits"][1]["ok"] is False)
    ck("PR 尺寸应写入结果", sm["pr"]["level"] == "XS")
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="提交信息与 PR 尺寸检查")
    ap.add_argument("--file", help="提交信息文本文件（多条用 ^^^^ 分隔）")
    ap.add_argument("--subject", help="单独校验一条标题")
    ap.add_argument("--files", type=int, help="PR 改动文件数")
    ap.add_argument("--additions", type=int, help="PR 新增行数")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="结果写入文件")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    if args.subject:
        levels, msgs = check_subject(args.subject)
        body = "\n".join(msgs) if msgs else "标题格式通过"
        out_path = args.out or os.path.join(here, "_last_result.txt")
        io.open(out_path, "w", encoding="utf-8").write(body + "\n")
        print(body)
        sys.exit(0)

    if not args.file:
        ap.error("需要 --file / --subject / --selftest")

    text = io.open(args.file, "r", encoding="utf-8", errors="ignore").read()
    report, summary = build_report(text, args.files, args.additions)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    if args.json:
        body = json.dumps(summary, ensure_ascii=False, indent=2)
    else:
        body = report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("结果已写入: %s" % out_path)


if __name__ == "__main__":
    main()
