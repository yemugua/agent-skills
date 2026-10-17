# -*- coding: utf-8 -*-
"""\u5821\u5792\u673a\u90e8\u7f72\u4e0e\u6743\u9650\u5ba1\u8ba1\u7684\u9759\u6001\u914d\u7f6e\u6838\u67e5\u3002

\u7528\u6cd5:
  python bastion_audit_check.py --file sshd_config.txt --profile prod-db
  python bastion_audit_check.py --file sshd_config.txt --shared-accounts ops,root
  python bastion_audit_check.py --selftest
"""
import argparse
import json
import os
import re
import sys

PASS = "\u901a\u8fc7"
FAIL = "\u4e0d\u5408\u89c4"
WARN = "\u9700\u786e\u8ba4"

LEVEL_ORDER = {PASS: 0, WARN: 1, FAIL: 2}

STRICT_PROFILES = ("prod-db", "prod-web")

# sshd_config \u5173\u952e\u9879: key -> (\u8bf4\u660e, \u89c4\u5219)
#   must_no  \u8981\u6c42\u503c\u4e3a no
#   pw       \u5bc6\u7801\u8ba4\u8bc1\u7b56\u7565
#   num:3-6  \u6570\u503c\u533a\u95f4
#   presence \u53ea\u9700\u5b58\u5728
SSH_KEYS = [
    ("PermitRootLogin", "\u7981\u6b62 root \u76f4\u767b", "must_no"),
    ("PasswordAuthentication", "\u5bc6\u7801\u8ba4\u8bc1\u7b56\u7565", "pw"),
    ("PubkeyAuthentication", "\u5bc6\u94a5\u8ba4\u8bc1", "presence"),
    ("X11Forwarding", "\u5173\u95ed X11 \u8f6c\u53d1", "must_no"),
    ("PermitEmptyPasswords", "\u7981\u6b62\u7a7a\u53e3\u4ee4", "must_no"),
    ("MaxAuthTries", "\u9650\u5236\u8ba4\u8bc1\u5c1d\u8bd5\u6b21\u6570", "num:3-6"),
    ("LoginGraceTime", "\u9650\u5236\u767b\u5f55\u5bbd\u9650\u671f", "num:10-120"),
    ("ClientAliveInterval", "\u56de\u6536\u6b7b\u8fde\u63a5", "presence"),
    ("AllowTcpForwarding", "TCP \u8f6c\u53d1\u7b56\u7565", "presence"),
]

# \u63d0\u6743\u9003\u9038\u8def\u5f84\uff1asudo/ForceCommand \u767d\u540d\u5355\u91cc\u51fa\u73b0\u5373\u81f4\u547d
ESCAPE_CMDS = [
    ("su", "sudo su \u4f1a\u8fdb\u5165\u65b0 shell\uff0c\u547d\u4ee4\u8fc7\u6ee4\u5728\u6b64\u4e4b\u540e\u5b8c\u5168\u5931\u6548"),
    ("bash", "sudo bash \u4f1a\u542f\u52a8\u672a\u53d7\u63a7\u7684\u4ea4\u4e92 shell"),
    ("sh", "sudo sh \u540c\u7406\uff0c\u7ed5\u8fc7\u5168\u90e8\u547d\u4ee4\u5ba1\u8ba1"),
    ("dash", "sudo dash \u540c\u7406"),
    ("zsh", "sudo zsh \u540c\u7406"),
    ("-i", "sudo -i \u76f4\u63a5\u8fdb\u5165\u767b\u5f55 shell\uff0c\u547d\u4ee4\u8fc7\u6ee4\u5931\u6548"),
    ("-s", "sudo -s \u542f\u52a8 shell\uff0c\u547d\u4ee4\u8fc7\u6ee4\u5931\u6548"),
    ("sudoedit", "sudoedit \u53ef\u7f16\u8f91\u4efb\u610f\u6587\u4ef6\uff0c\u7b49\u540c root \u5199\u6743\u9650"),
]

DANGEROUS = [
    ("rm -rf /", "\u4e0d\u53ef\u6062\u590d\u7684\u6574\u76d8\u5220\u9664"),
    ("mkfs", "\u6587\u4ef6\u7cfb\u7edf\u683c\u5f0f\u5316"),
    ("dd if=", "\u78c1\u76d8\u8bbe\u5907\u8986\u5199"),
    ("fdisk", "\u5206\u533a\u8868\u64cd\u4f5c"),
    ("> /dev/sd", "\u76f4\u63a5\u5411\u5757\u8bbe\u5907\u5199\u5165"),
    ("history -c", "\u6e05\u9664\u5f53\u524d\u4f1a\u8bdd\u5386\u53f2"),
    ("unset HISTFILE", "\u7981\u7528\u5386\u53f2\u8bb0\u5f55"),
    ("iptables -F", "\u6e05\u7a7a\u9632\u706b\u5899\u89c4\u5219"),
    ("setenforce 0", "\u5173\u95ed SELinux \u5f3a\u5236\u6a21\u5f0f"),
    ("systemctl stop auditd", "\u5173\u95ed\u7cfb\u7edf\u5ba1\u8ba1\u670d\u52a1"),
]

BOUNDARY = [
    ("VPN", "\u4ece\u5916\u90e8\u7f51\u7edc\u63a5\u5165\u5185\u7f51\uff0c\u7f51\u7edc\u53ef\u8fbe\u6027\u63a7\u5236", "\u901a\u5e38\u4ec5\u767b\u5f55\u65e5\u5fd7",
     "\u4e0d\u80fd\u66ff\u4ee3\u5821\u5792\u673a"),
    ("\u5821\u5792\u673a", "\u5bf9\u8fd0\u7ef4\u64cd\u4f5c\u505a\u4f1a\u8bdd\u4e0e\u547d\u4ee4\u5ba1\u8ba1", "\u5b8c\u6574\u4f1a\u8bdd\u5ba1\u8ba1",
     "\u4e0d\u80fd\u66ff\u4ee3 VPN \u7684\u63a5\u5165\u80fd\u529b"),
    ("\u96f6\u4fe1\u4efb", "\u6309\u8eab\u4efd\u4e0e\u8bbe\u5907\u72b6\u6001\u9010\u6b21\u6388\u6743\u8bbf\u95ee", "\u6709\uff0c\u504f\u8bbf\u95ee\u51b3\u7b56",
     "\u7406\u5ff5\u8986\u76d6\u90e8\u5206\u573a\u666f\uff0c\u843d\u5730\u4ecd\u9700\u5ba1\u8ba1\u624b\u6bb5"),
]

SHARED_NAMES = ("root", "ops", "admin", "test", "deploy", "user", "ubuntu")


def parse_sshd(text):
    """\u89e3\u6790 sshd_config\uff0c\u8fd4\u56de {key_lower: value}\uff08\u540e\u51fa\u73b0\u8986\u76d6\u5148\u51fa\u73b0\uff09\u3002"""
    out = {}
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9]*)\s+(.*)$", ln)
        if not m:
            continue
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def judge(key, value):
    """\u8fd4\u56de (\u7b49\u7ea7, \u8bf4\u660e)\u3002"""
    v = (value or "").lower()
    if key == "PermitRootLogin":
        if v == "no":
            return PASS, "\u503c\u4e3a no\uff0c\u5df2\u7981\u6b62 root \u76f4\u767b"
        if v in ("without-password", "prohibit-password"):
            return WARN, ("\u503c\u4e3a %s: \u7981\u6b62\u4e86\u5bc6\u7801 root \u76f4\u767b\u4f46\u4ecd\u5141\u8bb8\u5bc6\u94a5 root \u76f4\u767b\uff0c"
                          "\u9700\u786e\u8ba4\u662f\u5426\u7b26\u5408\u672c\u573a\u666f\u8981\u6c42" % value)
        return FAIL, "\u503c\u4e3a %s\uff0c\u5e94\u4e3a no" % value
    if key in ("X11Forwarding", "PermitEmptyPasswords"):
        if v == "no":
            return PASS, "\u503c\u4e3a no"
        if v == "yes":
            return FAIL, "\u503c\u4e3a yes\uff0c\u5e94\u4e3a no"
        return WARN, "\u503c\u4e3a %s\uff0c\u9700\u4eba\u5de5\u786e\u8ba4" % value
    if key == "PasswordAuthentication":
        if v == "no":
            return PASS, "\u5df2\u7981\u7528\u5bc6\u7801\u8ba4\u8bc1\uff0c\u4ec5\u5141\u8bb8\u5bc6\u94a5"
        return WARN, ("\u503c\u4e3a %s: \u5bc6\u7801\u8ba4\u8bc1\u5f00\u542f\u65f6\u5fc5\u987b\u6709\u5f3a\u5bc6\u7801\u7b56\u7565\u4e0e\u66b4\u529b\u7834\u89e3\u9632\u62a4"
                      % value)
    if key == "MaxAuthTries":
        try:
            n = int(value)
        except (TypeError, ValueError):
            return FAIL, "\u503c\u65e0\u6cd5\u89e3\u6790\u4e3a\u6570\u5b57: %s" % value
        if n == 0:
            return FAIL, "\u503c\u4e3a 0 \u8868\u793a\u4e0d\u9650\u5c1d\u8bd5\u6b21\u6570\uff0c\u7b49\u4e8e\u6ca1\u6709\u9632\u62a4"
        if 3 <= n <= 6:
            return PASS, "\u503c\u4e3a %d" % n
        return WARN, "\u503c\u4e3a %d\uff0c\u5efa\u8bae 3 \u5230 6" % n
    if key == "LoginGraceTime":
        try:
            n = int(value)
        except (TypeError, ValueError):
            return FAIL, "\u503c\u65e0\u6cd5\u89e3\u6790\u4e3a\u6570\u5b57: %s" % value
        if n == 0:
            return FAIL, ("\u503c\u4e3a 0 \u8868\u793a\u4e0d\u9650\u5236\u767b\u5f55\u5bbd\u9650\u671f\uff0c"
                          "\u534a\u5f00\u8fde\u63a5\u53ef\u957f\u671f\u5360\u7528 sshd \u8d44\u6e90")
        if 10 <= n <= 120:
            return PASS, "\u503c\u4e3a %d \u79d2" % n
        return WARN, "\u503c\u4e3a %d \u79d2\uff0c\u5efa\u8bae 10 \u5230 120" % n
    return WARN, "\u5df2\u914d\u7f6e\u4e3a %s\uff0c\u5b58\u5728\u5373\u9700\u8bc4\u4f30" % value


def check_keys(cfg, profile):
    strict = profile in STRICT_PROFILES
    rows = []
    for key, cn, rule in SSH_KEYS:
        low = key.lower()
        if low not in cfg:
            if rule == "presence":
                rows.append((key, cn, "\u672a\u914d\u7f6e", PASS,
                             "\u672a\u663e\u5f0f\u58f0\u660e\uff0c\u91c7\u7528 OpenSSH \u7f16\u8bd1\u9ed8\u8ba4\u503c\uff1b"
                             "\u4e0d\u540c\u7248\u672c\u9ed8\u8ba4\u503c\u4e0d\u4e00\u81f4\uff0c\u5efa\u8bae\u663e\u5f0f\u5199\u660e"))
            else:
                lvl = FAIL if strict else WARN
                rows.append((key, cn, "\u672a\u914d\u7f6e", lvl,
                             "\u672a\u914d\u7f6e\u8be5\u9879\uff0c\u5c06\u91c7\u7528 OpenSSH \u7f16\u8bd1\u9ed8\u8ba4\u503c\uff0c"
                             "\u800c\u9ed8\u8ba4\u503c\u5728\u4e0d\u540c\u7248\u672c\u95f4\u4e0d\u4e00\u81f4\uff0c\u5fc5\u987b\u663e\u5f0f\u5199\u660e"))
            continue
        val = cfg[low]
        if rule == "presence":
            rows.append((key, cn, val, PASS, "\u5df2\u914d\u7f6e"))
            continue
        lvl, note = judge(key, val)
        rows.append((key, cn, val, lvl, note))
    return rows


def check_escape(cfg):
    """\u68c0\u67e5 sudo / ForceCommand \u4e2d\u662f\u5426\u542b\u63d0\u6743\u9003\u9038\u8def\u5f84\u3002"""
    hits = []
    for key in ("forcecommand", "sudoers", "allowusers", "denyusers"):
        v = cfg.get(key)
        if not v:
            continue
        low = v.lower()
        for cmd, why in ESCAPE_CMDS:
            if cmd in ("-i", "-s"):
                pat = r"(^|\s)" + re.escape(cmd) + r"(\s|$)"
            else:
                pat = r"(^|[^a-z0-9_.-])" + re.escape(cmd) + r"($|[^a-z0-9_.-])"
            if re.search(pat, low):
                hits.append((key, cmd, why))
    return hits


def check_allowusers_misuse(cfg):
    """\u8bc6\u522b\u300c\u4ee5\u4e3a AllowUsers \u80fd\u9650\u5236\u6765\u6e90\u300d\u7684\u8bef\u89e3\u3002"""
    notes = []
    au = cfg.get("allowusers")
    if au and not cfg.get("match"):
        notes.append(
            "\u914d\u7f6e\u4e86 AllowUsers \u4f46\u6ca1\u6709 Match \u5757: AllowUsers \u53ea\u9650\u5236**\u54ea\u4e9b\u7528\u6237**"
            "\u53ef\u767b\u5f55\uff0c**\u4e0d\u9650\u5236\u6765\u6e90 IP**\u3002\u82e5\u76ee\u7684\u662f\u9650\u5236\u53ea\u80fd\u4ece\u5821\u5792\u673a\u767b\u5f55\uff0c"
            "\u5fc5\u987b\u914d\u9632\u706b\u5899\u89c4\u5219\u6216\u7f51\u7edc\u5206\u5c42\uff0c\u5426\u5219\u76f4\u8fde\u901a\u9053\u5e76\u672a\u5c01\u5835")
    return notes


def check_profile_strict(cfg, profile):
    """\u751f\u4ea7\u73af\u5883\u989d\u5916\u5fc5\u68c0\u9879\u3002"""
    outs = []
    if profile not in STRICT_PROFILES:
        return outs
    pw = (cfg.get("passwordauthentication") or "yes").lower()
    pk = (cfg.get("pubkeyauthentication") or "yes").lower()
    if pw == "yes" and pk == "yes":
        outs.append(
            "\u5bc6\u7801\u4e0e\u5bc6\u94a5\u8ba4\u8bc1\u540c\u65f6\u5f00\u542f: \u4e24\u79cd\u65b9\u5f0f\u5e76\u5b58\u610f\u5473\u7740\u4e00\u65e6\u5bc6\u94a5\u88ab\u7206\u7834\uff0c"
            "\u4ecd\u53ef\u7528\u5f31\u5bc6\u7801\u767b\u5f55\u3002\u751f\u4ea7\u73af\u5883\u81f3\u5c11\u6536\u7d27\u4e00\u9879")
    if not cfg.get("allowusers") and not cfg.get("allowgroups"):
        outs.append(
            "\u672a\u914d\u7f6e AllowUsers \u6216 AllowGroups: \u65e0\u6cd5\u5728 sshd \u5c42\u9650\u5b9a\u53ef\u767b\u5f55\u8d26\u53f7\uff0c"
            "\u8d26\u53f7\u6cbb\u7406\u9700\u5b8c\u5168\u4f9d\u8d56\u7cfb\u7edf\u8d26\u53f7\u5c42")
    if not cfg.get("clientaliveinterval"):
        outs.append(
            "\u672a\u914d\u7f6e ClientAliveInterval: \u6b7b\u8fde\u63a5\u4e0d\u4f1a\u88ab\u53ca\u65f6\u56de\u6536\uff0c"
            "\u957f\u671f\u8fd0\u884c\u4f1a\u7d2f\u79ef\u8d44\u6e90\u5360\u7528")
    return outs


def check_shared_accounts(names):
    outs = []
    for n in [x.strip() for x in (names or "").split(",") if x.strip()]:
        low = n.lower()
        if low in SHARED_NAMES:
            outs.append((n, FAIL,
                         "\u8d26\u53f7 %s \u7591\u4f3c\u5171\u4eab\u8d26\u53f7: \u591a\u4eba\u5171\u7528\u540c\u4e00\u8d26\u53f7\u4f1a\u4f7f\u5ba1\u8ba1\u65e5\u5fd7\u5168\u90e8"
                         "\u6307\u5411\u540c\u4e00\u4e2a\u4e3b\u4f53\uff0c\u7b49\u4e8e\u6ca1\u6709\u5ba1\u8ba1\u3002\u5fc5\u987b\u62c6\u5206\u4e3a\u4e2a\u4eba\u8d26\u53f7" % n))
        else:
            outs.append((n, WARN,
                         "\u8d26\u53f7 %s \u9700\u4eba\u5de5\u786e\u8ba4\u662f\u5426\u4e3a\u5171\u4eab\u8d26\u53f7: "
                         "\u8003\u6838\u53e3\u5f84\u662f\u5821\u5792\u673a\u8d26\u53f7\u6570\u5e94\u4e0d\u5c11\u4e8e\u5b9e\u9645\u8fd0\u7ef4\u4eba\u6570" % n))
    return outs


def worst(levels):
    lv = PASS
    for x in levels:
        if LEVEL_ORDER.get(x, 0) > LEVEL_ORDER.get(lv, 0):
            lv = x
    return lv


def build(text, profile, shared):
    cfg = parse_sshd(text)
    rows = check_keys(cfg, profile)
    escapes = check_escape(cfg)
    misuse = check_allowusers_misuse(cfg)
    strict = check_profile_strict(cfg, profile)
    shared_rows = check_shared_accounts(shared)

    all_rows = list(rows)
    levels = [r[3] for r in rows]
    for key, cmd, why in escapes:
        all_rows.append(("ESCAPE", "\u63d0\u6743\u9003\u9038\u8def\u5f84", cmd, FAIL, why))
        levels.append(FAIL)
    for n in misuse:
        all_rows.append(("ALLOWUSERS", "\u6765\u6e90\u9650\u5236\u8bef\u89e3", n, WARN, n))
        levels.append(WARN)
    for n in strict:
        all_rows.append(("STRICT", "\u751f\u4ea7\u5fc5\u68c0", n, WARN, n))
        levels.append(WARN)
    for name, l, note in shared_rows:
        all_rows.append(("ACCOUNT", "\u5171\u4eab\u8d26\u53f7\u6838\u67e5", name, l, note))
        levels.append(l)
    if not cfg or not [k for k, _c, _r in SSH_KEYS if k.lower() in cfg]:
        all_rows.append(("PARSE", "\u914d\u7f6e\u89e3\u6790", "\u65e0\u6709\u6548\u914d\u7f6e\u9879", FAIL,
                         "\u672a\u89e3\u6790\u5230\u4efb\u4f55\u53d7\u6838\u67e5\u7684 sshd \u914d\u7f6e\u9879\uff0c\u65e0\u6cd5\u6838\u67e5\uff0c"
                         "\u8bf7\u786e\u8ba4\u6587\u4ef6\u662f\u5426\u4e3a sshd_config \u6216\u5176\u7247\u6bb5"))
        levels.append(FAIL)
    return {
        "profile": profile,
        "overall": worst(levels),
        "rows": [{"key": k, "name": cn, "value": v, "level": l, "note": note}
                 for k, cn, v, l, note in all_rows],
        "escape_hits": [{"cmd": c, "why": w} for _k, c, w in escapes],
        "boundary": [{"name": n, "does": d, "audit": a, "cannot": c}
                     for n, d, a, c in BOUNDARY],
        "dangerous": [{"cmd": c, "risk": r} for c, r in DANGEROUS],
    }


CHECKLIST = [
    "\u76ee\u6807 22 \u7aef\u53e3\u53ea\u5bf9\u5821\u5792\u673a\u7f51\u6bb5\u5f00\u653e\uff08\u4ece\u5176\u4ed6\u7f51\u6bb5 telnet \u5fc5\u987b\u5931\u8d25\uff09",
    "\u5821\u5792\u673a\u8d26\u53f7\u6570\u4e0d\u5c11\u4e8e\u8fd0\u7ef4\u4eba\u6570\uff0c\u5171\u4eab\u8d26\u53f7\u4e3a 0",
    "PermitRootLogin \u4e3a no",
    "sudo \u767d\u540d\u5355\u4e0d\u542b su / bash / sh / -i / -s / sudoedit",
    "\u9ad8\u5371\u547d\u4ee4\u62e6\u622a\u662f\u5b9e\u6d4b\u8fc7\u7684\uff0c\u4e0d\u662f\u53ea\u770b\u914d\u7f6e\u754c\u9762",
    "\u522b\u540d\u3001eval\u3001\u4e34\u65f6\u811a\u672c\u7b49\u7ed5\u8fc7\u624b\u6cd5\u5747\u5df2\u9a8c\u8bc1\u88ab\u62e6",
    "\u547d\u4ee4\u65e5\u5fd7\u542b\u8f93\u51fa\u800c\u4e0d\u53ea\u662f\u8f93\u5165",
    "\u4f1a\u8bdd\u5f55\u50cf\u53ef\u6309\u4eba\u6309\u65f6\u95f4\u68c0\u7d22\u56de\u653e",
    "\u6587\u4ef6\u4f20\u8f93\u6709\u8bb0\u5f55\uff08\u6587\u4ef6\u540d\u3001\u5927\u5c0f\u3001\u65b9\u5411\uff09",
    "\u8fd0\u7ef4\u5bf9\u5ba1\u8ba1\u5b58\u50a8\u4f4d\u7f6e\u65e0\u5199\u6743\u9650",
    "\u5ba1\u8ba1\u65e5\u5fd7\u6709\u5bb9\u91cf\u544a\u8b66\u4e0e\u5f52\u6863\u7b56\u7565",
    "\u7559\u5b58\u5230\u671f\u6709\u6e05\u7406\u673a\u5236",
    "\u5821\u5792\u673a\u6545\u969c\u65f6\u4e3a fail-close \u800c\u975e fail-open",
    "\u76ee\u6807\u4fa7\u5ba1\u8ba1\u72ec\u7acb\u4e8e\u5821\u5792\u673a",
    "\u5e94\u6025\u7ed5\u8fc7\u901a\u9053\u6709\u5ba1\u6279\u4e14\u4e8b\u540e\u590d\u6838",
]

MANUAL = [
    "\u300c\u8fd0\u7ef4\u80fd\u5426\u76f4\u8fde\u670d\u52a1\u5668\u300d\u7684\u7b54\u6848\u5fc5\u987b\u662f\u660e\u786e\u7684\u4e0d\u80fd",
    "\u662f\u5426\u6709\u5171\u7528\u8d26\u53f7\u6216\u5171\u7528\u5bc6\u94a5\uff08\u5fc5\u987b\u4e3a 0\uff09",
    "\u65e5\u5fd7\u7559\u5b58\u671f\u9650\u7684\u8981\u6c42\u6765\u6e90\u662f\u8c01\uff08\u6cd5\u89c4/\u884c\u4e1a\u89c4\u8303/\u5185\u90e8\u5236\u5ea6\uff09",
    "\u5e94\u6025\u901a\u9053\u662f\u5426\u6709\u4eba\u79c1\u81ea\u5f00\u901a\u8fc7",
]


def render_md(r):
    L = []
    L.append("# \u5821\u5792\u673a\u90e8\u7f72\u4e0e\u6743\u9650\u5ba1\u8ba1\u6838\u67e5\u62a5\u544a")
    L.append("")
    L.append("- \u573a\u666f: %s" % r["profile"])
    L.append("- \u7efc\u5408\u7ed3\u8bba: **%s**" % r["overall"])
    L.append("")
    L.append("## \u4e00 sshd_config \u5173\u952e\u9879")
    L.append("")
    L.append("| \u9879 | \u542b\u4e49 | \u5f53\u524d\u503c | \u5224\u5b9a | \u8bf4\u660e |")
    L.append("|---|---|---|---|---|")
    for it in r["rows"]:
        L.append("| %s | %s | %s | %s | %s |"
                 % (it["key"], it["name"], it["value"],
                    it["level"], it["note"]))
    L.append("")
    L.append("## \u4e8c VPN / \u5821\u5792\u673a / \u96f6\u4fe1\u4efb\u804c\u8d23\u8fb9\u754c")
    L.append("")
    L.append("| \u7ec4\u4ef6 | \u89e3\u51b3\u4ec0\u4e48 | \u5ba1\u8ba1\u80fd\u529b | \u4e0d\u80fd\u66ff\u4ee3 |")
    L.append("|---|---|---|---|")
    for b in r["boundary"]:
        L.append("| %s | %s | %s | %s |"
                 % (b["name"], b["does"], b["audit"], b["cannot"]))
    L.append("")
    L.append("> VPN \u901a\u4e86\u4e0d\u4ee3\u8868\u8bbf\u95ee\u6709\u5ba1\u8ba1\uff1b\u5821\u5792\u673a\u4e0a\u4e86\u4e0d\u4ee3\u8868\u7f51\u7edc\u53d7\u63a7\u3002")
    L.append("")
    L.append("## \u4e09 \u9ad8\u5371\u547d\u4ee4\u6e05\u5355")
    L.append("")
    L.append("| \u547d\u4ee4 | \u98ce\u9669 |")
    L.append("|---|---|")
    for d in r["dangerous"]:
        L.append("| %s | %s |" % (d["cmd"], d["risk"]))
    L.append("")
    L.append("## \u56db \u90e8\u7f72\u9a8c\u6536\u6e05\u5355")
    L.append("")
    for t in CHECKLIST:
        L.append("- [ ] %s" % t)
    L.append("")
    L.append("## \u4e94 \u5fc5\u987b\u4eba\u5de5\u786e\u8ba4")
    L.append("")
    for t in MANUAL:
        L.append("- [ ] %s" % t)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> \u811a\u672c\u8bfb\u7684\u662f\u914d\u7f6e\u6587\u4ef6\u6587\u672c\uff0c\u4e0d\u662f\u8fd0\u884c\u4e2d\u7684\u5821\u5792\u673a\u3002"
             "\u5b83\u4e0d\u80fd\u544a\u8bc9\u4f60\u5821\u5792\u673a\u662f\u5426\u771f\u7684\u5728\u62e6\u622a\u3001\u5ba1\u8ba1\u662f\u5426\u771f\u7684\u5728\u5f55\u50cf\uff0c"
             "\u90a3\u4e24\u4ef6\u4e8b\u5fc5\u987b\u5b9e\u6d4b\u3002")
    return "\n".join(L) + "\n"


GOOD_CONF = """# \u751f\u4ea7\u57fa\u7ebf sshd_config
Port 22
PermitRootLogin no
PasswordAuthentication yes
PubkeyAuthentication yes
X11Forwarding no
PermitEmptyPasswords no
MaxAuthTries 4
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
"""

BAD_ROOT = """PermitRootLogin yes
PasswordAuthentication yes
X11Forwarding yes
MaxAuthTries 0
LoginGraceTime 0
"""

EMPTY_CONF = """# \u53ea\u6709\u6ce8\u91ca\u548c\u7a7a\u884c
# nothing here
"""

MISUSE_CONF = """PermitRootLogin no
AllowUsers ops deploy
PasswordAuthentication yes
PubkeyAuthentication yes
X11Forwarding no
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
"""

JUNK = """\u8fd9\u4e0d\u662f\u914d\u7f6e\u6587\u4ef6
random text without separator
Port
"""


def selftest():
    res = []
    ok = True

    def ck(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        res.append("%s %s got=%r want=%r"
                   % ("PASS" if good else "FAIL", name, got, want))

    cfg = parse_sshd(GOOD_CONF)
    ck("parse_root", cfg.get("permitrootlogin"), "no")
    ck("parse_trys", cfg.get("maxauthtries"), "4")
    ck("parse_allowusers_absent", cfg.get("allowusers"), None)
    ck("parse_empty", parse_sshd(EMPTY_CONF), {})

    rows = dict((k, lv) for k, cn, v, lv, n in check_keys(cfg, "prod-db"))
    ck("judge_root_ok", rows.get("PermitRootLogin"), PASS)
    ck("judge_trys_ok", rows.get("MaxAuthTries"), PASS)
    ck("judge_grace_ok", rows.get("LoginGraceTime"), PASS)
    ck("judge_empty_pw_ok", rows.get("PermitEmptyPasswords"), PASS)
    ck("judge_pw_warn", rows.get("PasswordAuthentication"), WARN)

    bad = parse_sshd(BAD_ROOT)
    rbad = dict((k, lv) for k, cn, v, lv, n in check_keys(bad, "prod-db"))
    ck("judge_root_bad", rbad.get("PermitRootLogin"), FAIL)
    ck("judge_trys_zero", rbad.get("MaxAuthTries"), FAIL)
    ck("judge_grace_zero", rbad.get("LoginGraceTime"), FAIL)
    ck("judge_x11_bad", rbad.get("X11Forwarding"), FAIL)
    # \u751f\u4ea7\u573a\u666f\u4e0b\u672a\u914d\u7f6e\u7684\u975e presence \u9879\u5fc5\u987b\u5224\u4e0d\u5408\u89c4
    ck("missing_strict_fail", rbad.get("PermitEmptyPasswords"), FAIL)
    ck("missing_presence_ok", rbad.get("PubkeyAuthentication"), PASS)
    rdev = dict((k, lv) for k, cn, v, lv, n in check_keys(bad, "dev"))
    ck("missing_dev_warn", rdev.get("PermitEmptyPasswords"), WARN)

    esc = check_escape(parse_sshd("ForceCommand sudo su"))
    ck("escape_su", len(esc) >= 1, True)
    ck("escape_why", "\u547d\u4ee4\u8fc7\u6ee4" in esc[0][2], True)
    ck("escape_none", check_escape(parse_sshd(GOOD_CONF)), [])
    ck("escape_bash", any(c == "bash" for _k, c, _w in check_escape(
        parse_sshd("ForceCommand sudo bash"))), True)
    ck("escape_dash_i", any(c == "-i" for _k, c, _w in check_escape(
        parse_sshd("ForceCommand sudo -i"))), True)
    ck("escape_sudoedit", any(c == "sudoedit" for _k, c, _w in check_escape(
        parse_sshd("ForceCommand sudoedit /etc/passwd"))), True)

    mis = check_allowusers_misuse(parse_sshd(MISUSE_CONF))
    ck("misuse_detected", len(mis) >= 1, True)
    ck("misuse_note", "\u4e0d\u9650\u5236\u6765\u6e90" in mis[0], True)
    ck("misuse_none", check_allowusers_misuse(parse_sshd(GOOD_CONF)), [])

    sh = check_shared_accounts("ops,alice")
    ck("shared_ops_fail", sh[0][1], FAIL)
    ck("shared_alice_warn", sh[1][1], WARN)
    ck("shared_reason", "\u7b49\u4e8e\u6ca1\u6709\u5ba1\u8ba1" in sh[0][2], True)

    st = check_profile_strict(parse_sshd(MISUSE_CONF), "prod-db")
    ck("strict_dual_auth", any("\u4e24\u79cd\u65b9\u5f0f\u5e76\u5b58" in s for s in st), True)
    ck("strict_dev_none", check_profile_strict(cfg, "dev"), [])
    ck("strict_good_flags",
       any("\u4e24\u79cd\u65b9\u5f0f\u5e76\u5b58" in s for s in check_profile_strict(cfg, "prod-db")),
       True)

    rep = build(GOOD_CONF, "prod-db", "ops")
    ck("overall_with_shared", rep["overall"], FAIL)
    rep2 = build(GOOD_CONF, "prod-db", "")
    ck("overall_clean", rep2["overall"], WARN)  # \u5bc6\u7801\u8ba4\u8bc1\u5f00\u542f -> \u9700\u786e\u8ba4
    rep3 = build(BAD_ROOT, "prod-db", "")
    ck("overall_bad", rep3["overall"], FAIL)
    rep4 = build(EMPTY_CONF, "dev", "")
    ck("overall_empty", rep4["overall"], FAIL)
    rep5 = build(JUNK, "dev", "")
    ck("overall_junk", rep5["overall"], FAIL)
    rep6 = build(MISUSE_CONF, "prod-db", "")
    ck("misuse_rep_found",
       any(it["key"] == "ALLOWUSERS" for it in rep6["rows"]), True)

    md = render_md(rep3)
    ck("md_header", md.startswith("# "), True)
    ck("md_boundary", "\u804c\u8d23\u8fb9\u754c" in md, True)
    ck("md_danger", "\u9ad8\u5371\u547d\u4ee4\u6e05\u5355" in md, True)
    ck("md_checklist", "\u90e8\u7f72\u9a8c\u6536\u6e05\u5355" in md, True)
    ck("md_manual", "\u5fc5\u987b\u4eba\u5de5\u786e\u8ba4" in md, True)
    js = json.loads(json.dumps(rep2, ensure_ascii=False))
    ck("json_keys", sorted(js.keys()),
       ["boundary", "dangerous", "escape_hits", "overall", "profile", "rows"])

    ck("checklist_len", len(CHECKLIST) >= 14, True)
    ck("danger_len", len(DANGEROUS) >= 10, True)
    ck("boundary_len", len(BOUNDARY), 3)
    ck("escape_len", len(ESCAPE_CMDS) >= 7, True)
    ck("worst_fn", worst([PASS, WARN, FAIL]), FAIL)
    ck("worst_fn2", worst([PASS, PASS]), PASS)

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--profile", default="prod-db",
                    choices=["prod-db", "prod-web", "dev", "batch"])
    ap.add_argument("--shared-accounts", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        rc = selftest()
        outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_selftest_result.txt")
        open(outp, "w", encoding="utf-8").write(
            "SELFTEST %s\nresult: %s\n"
            % ("OK" if rc == 0 else "FAILED", "OK" if rc == 0 else "FAILED"))
        return rc

    if not a.file or not os.path.exists(a.file):
        print("ERROR --file does not exist")
        return 2
    text = open(a.file, "r", encoding="utf-8", errors="replace").read()
    r = build(text, a.profile, a.shared_accounts)
    body = (render_md(r) if a.format == "md"
            else json.dumps(r, ensure_ascii=False, indent=2))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())