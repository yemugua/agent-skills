# -*- coding: utf-8 -*-
"""\u670d\u52a1\u5668\u65e0\u6cd5\u8fdc\u7a0b\u767b\u5f55\u7684\u5206\u5c42\u5224\u5b9a\u4e0e\u6839\u56e0\u5f52\u56e0\u3002

\u7528\u6cd5:
  python ssh_login_check.py --file obs.txt --user deploy --client-ip 10.0.0.5
  python ssh_login_check.py --file obs.txt --user deploy --json
  python ssh_login_check.py --selftest
"""
import argparse
import json
import os
import re
import sys

OK = "\u6b63\u5e38"
INFO = "\u9700\u786e\u8ba4"
ISSUE = "\u6709\u95ee\u9898"
BLOCKED = "\u88ab\u963b\u65ad"
CRITICAL = "\u6709\u81ea\u9501\u98ce\u9669"

LEVEL_ORDER = {OK: 0, INFO: 1, ISSUE: 2, BLOCKED: 3, CRITICAL: 4}

BOOL_KEYS = (
    "sshd_active", "sshd_syntax_ok", "login_ok", "auth_error",
    "fail2ban_banned", "fail2ban_jail", "oom_seen", "allowusers_ok",
    "match_block_hit", "other_entry", "clock_ok",
)

INT_KEYS = ("max_auth_tries", "disk_used_pct", "inode_used_pct",
            "syn_surge", "current_sessions")

STR_KEYS = ("probe_result", "listen_addr", "client_err", "server_log")

DEFAULTS = {
    "sshd_active": 0,
    "sshd_syntax_ok": 0,
    "login_ok": 0,
    "auth_error": 0,
    "fail2ban_banned": 0,
    "fail2ban_jail": 0,
    "oom_seen": 0,
    "allowusers_ok": 1,
    "match_block_hit": 0,
    "other_entry": 0,
    "clock_ok": 1,
}

CLIENT_PATTERNS = [
    ("too many authentication failures",
     "\u5ba2\u6237\u7aef\u672c\u5730\u5bc6\u94a5\u8fc7\u591a\u3002ssh \u4f1a\u4f9d\u6b21\u5c1d\u8bd5 agent \u4e0e ~/.ssh \u4e0b\u6240\u6709\u5bc6\u94a5\uff0c"
     "\u8d85\u8fc7\u670d\u52a1\u7aef MaxAuthTries \u540e\u6b63\u786e\u5bc6\u94a5\u6839\u672c\u6ca1\u673a\u4f1a\u88ab\u9a8c\u8bc1\uff0c"
     "\u5b9e\u9645\u662f\u5c1d\u8bd5\u6b21\u6570\u8017\u5c3d\u800c\u4e0d\u662f\u51ed\u636e\u9519\u8bef\u3002"
     "\u89e3\u51b3: ssh -o IdentitiesOnly=yes -i <\u6307\u5b9a\u5bc6\u94a5> user@host"),
    ("no matching host key type",
     "\u4e3b\u673a\u5bc6\u94a5\u7b97\u6cd5\u65e0\u4ea4\u96c6\uff0c\u5ba2\u6237\u7aef\u8fc7\u65e7\u3002"
     "\u957f\u671f\u505a\u6cd5\u662f\u5347\u7ea7\u5ba2\u6237\u7aef\uff1b\u4e34\u65f6\u53ef\u7528 "
     "-o HostKeyAlgorithms=+ssh-rsa \u517c\u5bb9\uff0c\u4f46\u4f1a\u964d\u4f4e\u5b89\u5168\u6027"),
    ("no matching key exchange method",
     "KEX \u7b97\u6cd5\u65e0\u4ea4\u96c6\u3002\u5347\u7ea7\u5ba2\u6237\u7aef\u4e3a\u957f\u671f\u505a\u6cd5\uff0c"
     "\u4e34\u65f6\u53ef\u7528 -o KexAlgorithms=+diffie-hellman-group14-sha1"),
    ("no matching cipher",
     "\u52a0\u5bc6\u5957\u4ef6\u65e0\u4ea4\u96c6\u3002\u4f18\u5148\u5347\u7ea7\u5ba2\u6237\u7aef"),
    ("no matching mac",
     "MAC \u7b97\u6cd5\u65e0\u4ea4\u96c6\u3002\u4f18\u5148\u5347\u7ea7\u5ba2\u6237\u7aef"),
    ("host key verification failed",
     "\u4e3b\u673a\u5bc6\u94a5\u4e0e\u670d\u52a1\u7aef\u8bb0\u5f55\u4e0d\u4e00\u81f4\uff0c\u53ef\u80fd\u662f\u670d\u52a1\u7aef\u91cd\u88c5\u6216\u5bc6\u94a5\u53d8\u66f4\uff0c"
     "\u4e5f\u53ef\u80fd\u662f\u4e2d\u95f4\u4eba\u653b\u51fb\u3002\u5fc5\u987b\u5148\u6838\u5b9e\u670d\u52a1\u7aef\u786e\u5b9e\u53d8\u66f4\u8fc7\u5bc6\u94a5\uff0c"
     "\u786e\u8ba4\u540e\u518d\u6e05\u7406 known_hosts \u5bf9\u5e94\u6761\u76ee\uff0c\u4e0d\u8981\u76f2\u76ee\u5ffd\u7565"),
    ("connection closed by remote host",
     "\u8fde\u63a5\u5efa\u7acb\u540e\u88ab\u670d\u52a1\u7aef\u4e3b\u52a8\u65ad\u5f00\u3002\u67e5\u670d\u52a1\u7aef sshd \u65e5\u5fd7\uff0c"
     "\u5e38\u89c1\u4e8e banner \u9636\u6bb5\u88ab\u5173\u3001\u5f3a\u5236\u547d\u4ee4\u5931\u8d25\u6216\u88ab\u8e22\u4e0b\u7ebf"),
    ("connection reset by remote host",
     "\u8fde\u63a5\u88ab\u91cd\u7f6e\u3002\u5e38\u89c1\u4e8e MaxStartups \u4e22\u5f03\u672a\u8ba4\u8bc1\u8fde\u63a5\uff0c"
     "\u6216\u4e2d\u95f4\u8bbe\u5907\u91cd\u7f6e\u4f1a\u8bdd"),
    ("permission denied",
     "\u8ba4\u8bc1\u5931\u8d25\u3002\u9700\u7ed3\u5408\u5ba2\u6237\u7aef\u5c1d\u8bd5\u6b21\u6570\u4e0e\u670d\u52a1\u7aef\u65e5\u5fd7\u5224\u65ad\uff1a"
     "\u51ed\u636e\u786e\u5b9e\u9519\u3001\u5c1d\u8bd5\u6b21\u6570\u8017\u5c3d\u3001AllowUsers \u9650\u5236\u3001"
     "\u8d26\u53f7\u9501\u5b9a\u3001\u6216\u88ab fail2ban \u5c01\u7981"),
    ("operation timed out",
     "\u8fde\u63a5\u8d85\u65f6\u300222 \u7aef\u53e3\u88ab\u8fc7\u6ee4\uff0c\u67e5\u4e91\u5b89\u5168\u7ec4\u4e0e\u7cfb\u7edf\u9632\u706b\u5899\uff08\u4e24\u4fa7\u90fd\u8981\u67e5\uff09"),
    ("connection refused",
     "\u7acb\u5373\u5931\u8d25\u5e76\u6536\u5230 RST\u300222 \u7aef\u53e3\u672a\u76d1\u542c\u6216\u670d\u52a1\u7aef\u4e3b\u52a8\u62d2\u7edd\uff0c"
     "\u8f6c\u6392\u67e5\u670d\u52a1\u72b6\u6001"),
]

SERVER_PATTERNS = [
    ("timeout, client not responding",
     "\u670d\u52a1\u7aef\u5224\u5b9a\u5ba2\u6237\u7aef\u4e0d\u54cd\u5e94\u800c\u65ad\u5f00\u3002\u67e5 ClientAliveInterval \u4e0e CountMax\uff0c"
     "\u4ee5\u53ca\u5ba2\u6237\u7aef\u7f51\u7edc\u6296\u52a8"),
    ("maxstartups",
     "\u670d\u52a1\u7aef\u8fbe\u5230 MaxStartups \u4e0a\u9650\u5e76\u5f00\u59cb\u4e22\u5f03\u672a\u8ba4\u8bc1\u8fde\u63a5\uff0c"
     "\u8868\u73b0\u4e3a\u65f6\u597d\u65f6\u574f\u3002\u4ec5\u8c03\u5927 MaxStartups \u4f1a\u66f4\u7cdf\uff0c"
     "\u5fc5\u987b\u540c\u65f6\u5c01\u7981\u6765\u6e90\u5e76\u6539\u7528\u5bc6\u94a5\u8ba4\u8bc1"),
    ("failed password",
     "\u670d\u52a1\u7aef\u8bb0\u5f55\u5230\u5bc6\u7801\u8ba4\u8bc1\u5931\u8d25\u3002\u67e5\u662f\u5426\u6b63\u5728\u88ab\u7206\u7834\uff1a"
     "journalctl -u sshd | grep -c 'Invalid user'"),
    ("invalid user",
     "\u670d\u52a1\u7aef\u8bb0\u5f55\u5230\u4e0d\u5b58\u5728\u7684\u7528\u6237\u540d\u5c1d\u8bd5\uff0c\u662f\u66b4\u529b\u7834\u89e3\u7684\u5178\u578b\u7279\u5f81"),
    ("maximum authentication attempts exceeded",
     "\u670d\u52a1\u7aef\u5df2\u8017\u5c3d MaxAuthTries\uff0c\u4e0e\u5ba2\u6237\u7aef\u5bc6\u94a5\u8fc7\u591a\u9ad8\u5ea6\u76f8\u5173"),
    ("not listed in allowusers",
     "\u5f53\u524d\u7528\u6237\u88ab AllowUsers \u9650\u5236\u3002"
     "\u6838\u5bf9 sshd -T -C user=<\u7528\u6237>,addr=<\u5ba2\u6237\u7aefIP>"),
    ("refuse list",
     "\u88ab TCP Wrappers \u6216\u7b49\u4ef7\u673a\u5236\u62d2\u7edd"),
]

SAFE_STEPS = [
    ("\u7b2c 0 \u6b65 \u786e\u8ba4\u6709\u5176\u4ed6\u767b\u5f55\u5165\u53e3", [
        "\u662f\u5426\u6709\u4e91\u63a7\u5236\u53f0 VNC\u3001\u63a7\u5236\u53f0\u767b\u5f55\u6216\u7269\u7406\u8bbf\u95ee",
        "\u6ca1\u6709\u5176\u4ed6\u5165\u53e3\u65f6\u4e0d\u8981\u52a8\u8ba4\u8bc1\u914d\u7f6e",
    ]),
    ("\u7b2c 1 \u5c42 \u5ba2\u6237\u7aef", [
        "ssh -vvv <user>@<host>        # \u5fc5\u987b\u62ff\u5230\u5b8c\u6574\u65e5\u5fd7",
        "ssh -G <host>                 # \u770b\u6700\u7ec8\u751f\u6548\u7684\u672c\u5730\u914d\u7f6e",
        "ssh-add -l                    # \u770b agent \u91cc\u7684\u5bc6\u94a5\u6570\u91cf",
        "env | grep -i proxy           # \u6392\u9664\u4ee3\u7406\u5e72\u6270",
        "cat ~/.ssh/config ; cat ~/.ssh/known_hosts",
        "date -u                       # \u6838\u5bf9\u5ba2\u6237\u7aef\u65f6\u949f",
    ]),
    ("\u7b2c 2 \u5c42 \u7f51\u7edc\u4e0e\u7aef\u53e3", [
        "nc -zv -w 3 <host> 22",
        "traceroute -n -T -p 22 <host>",
    ]),
    ("\u7b2c 3 \u5c42 sshd \u670d\u52a1\uff08\u9700\u670d\u52a1\u5668\u672c\u5730\u6267\u884c\uff09", [
        "systemctl status sshd ; systemctl is-active sshd",
        "sshd -t                        # \u914d\u7f6e\u8bed\u6cd5\uff0c\u8f93\u51fa\u4e3a\u7a7a\u624d\u6b63\u786e",
        "sshd -T | grep -iE 'permitrootlogin|passwordauthentication|maxauthtries|maxstartups'",
        "ss -lntp | grep :22             # \u770b\u76d1\u542c\u5730\u5740",
        "journalctl -u sshd -n 200 --no-pager",
    ]),
    ("\u7b2c 4 \u5c42 \u8ba4\u8bc1\u7b56\u7565", [
        "grep -n -A10 '^Match' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf",
        "sshd -T -C user=<\u7528\u6237>,host=<\u5ba2\u6237\u7aefIP>,addr=<\u5ba2\u6237\u7aefIP>",
        "fail2ban-client status sshd",
        "passwd -S <\u7528\u6237>                # \u8d26\u53f7\u9501\u5b9a\u72b6\u6001",
    ]),
    ("\u7b2c 5 \u5c42 \u8fde\u63a5\u6570\u4e0e\u8d44\u6e90", [
        "sshd -T | grep -i maxstartups",
        "journalctl -u sshd --since '-10m' --no-pager | grep -icE 'Failed password|Invalid user'",
        "who ; w",
        "df -h ; df -i                 # \u78c1\u76d8\u6ee1\u4f1a\u5bfc\u81f4 sshd \u8d77\u4e0d\u6765",
        "dmesg -T | grep -i 'out of memory' | tail",
    ]),
]

SAFE_ORDER = [
    "\u786e\u8ba4\u6709\u5176\u4ed6\u767b\u5f55\u5165\u53e3\uff08\u4e91\u63a7\u5236\u53f0 VNC / \u63a7\u5236\u53f0 / \u7269\u7406\uff09",
    "\u5907\u4efd\u914d\u7f6e\uff1acp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak",
    "\u4fee\u6539\u914d\u7f6e",
    "sshd -t                    # \u8bed\u6cd5\u5fc5\u987b\u901a\u8fc7\uff0c\u8f93\u51fa\u4e3a\u7a7a",
    "sshd -T                    # \u786e\u8ba4\u5b9e\u9645\u751f\u6548\u503c\u7b26\u5408\u9884\u671f",
    "\u4fdd\u7559\u5f53\u524d\u767b\u5f55\u4f1a\u8bdd\uff0c\u4e0d\u8981\u9000\u51fa",
    "\u5f00\u65b0\u4f1a\u8bdd\u9a8c\u8bc1\u80fd\u8fde\u4e0a",
    "\u901a\u8fc7\u540e\u518d reload\uff1asystemctl reload sshd",
    "\u786e\u8ba4\u65e0\u5f02\u5e38\u540e\u518d\u5173\u95ed\u65e7\u4f1a\u8bdd",
]

MANUAL = [
    "\u6709\u5176\u4ed6\u767b\u5f55\u5165\u53e3\u5417\uff08\u4e91\u63a7\u5236\u53f0 VNC / \u63a7\u5236\u53f0 / \u7269\u7406\uff09",
    "\u5ba2\u6237\u7aef -vvv \u7684\u5b8c\u6574\u65e5\u5fd7",
    "\u670d\u52a1\u7aef journalctl -u sshd \u7684\u65e5\u5fd7",
    "sshd -t \u662f\u5426\u901a\u8fc7\u3001sshd -T \u7684\u5b9e\u9645\u751f\u6548\u503c",
    "\u662f\u5426\u5b58\u5728 Match \u5757\uff08\u7528 sshd -T -C \u9a8c\u8bc1\uff09",
    "AllowUsers / DenyUsers \u662f\u5426\u9650\u5236\u5f53\u524d\u7528\u6237",
    "\u5ba2\u6237\u7aef\u662f\u5426\u5e26\u4e86\u8fc7\u591a\u5bc6\u94a5",
    "\u662f\u5426\u88ab fail2ban \u5c01\u7981",
    "\u78c1\u76d8\u4e0e inode \u662f\u5426\u5df2\u6ee1",
    "24 \u5c0f\u65f6\u5185\u662f\u5426\u6709 OOM",
    "\u662f\u5426\u6b63\u5728\u906d\u53d7\u7206\u7834\uff08Invalid user \u7edf\u8ba1\uff09",
    "\u5ba2\u6237\u7aef\u4e0e\u670d\u52a1\u7aef\u65f6\u949f\u504f\u5dee\u662f\u5426\u8fc7\u5927",
]


def to_int(v):
    m = re.match(r"^(-?\d+)", (v or "").strip())
    return int(m.group(1)) if m else None


def parse(text):
    got = {}
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or ln.startswith("//"):
            continue
        parts = re.split(r"[|\t,;=]", ln, maxsplit=1)
        if len(parts) < 2:
            continue
        k = parts[0].strip().lower()
        v = parts[1].strip()
        if k in BOOL_KEYS or k in INT_KEYS:
            n = to_int(v)
            if n is not None:
                got[k] = n
        elif k in STR_KEYS:
            got[k] = v
    return got


def classify(d):
    """\u5148\u7ed9\u6839\u56e0\u5206\u7c7b\uff0c\u51b3\u5b9a\u540e\u7eed\u67e5\u54ea\u4e9b\u5c42\u3002\u987a\u5e8f\u5373\u4f18\u5148\u7ea7\u3002"""
    p = (d.get("probe_result") or "").strip().lower()
    ce = (d.get("client_err") or "").strip().lower()
    if p == "refused":
        return "\u7aef\u53e3\u672a\u76d1\u542c", BLOCKED
    if p in ("timeout", "timedout"):
        return "\u7aef\u53e3\u88ab\u8fc7\u6ee4", BLOCKED
    if "too many authentication failures" in ce:
        return "\u5ba2\u6237\u7aef\u5bc6\u94a5\u8fc7\u591a", ISSUE
    if "host key verification failed" in ce:
        return "\u4e3b\u673a\u5bc6\u94a5\u53d8\u66f4", ISSUE
    if d.get("fail2ban_banned"):
        return "\u88ab\u5c01\u7981", BLOCKED
    if d.get("auth_error") or "permission denied" in ce:
        return "\u8ba4\u8bc1\u5931\u8d25", ISSUE
    if d.get("login_ok"):
        return "\u53ef\u767b\u5f55", OK
    return "\u672a\u5206\u7c7b", INFO


def check_entry(d):
    rows = []
    if not d.get("other_entry"):
        rows.append((CRITICAL,
         "\u6ca1\u6709\u5176\u4ed6\u767b\u5f55\u5165\u53e3\u3002\u6b64\u65f6\u4fee\u6539\u8ba4\u8bc1\u914d\u7f6e\u98ce\u9669\u6781\u9ad8\uff0c"
         "sshd -t \u672a\u901a\u8fc7\u6216 reload \u5931\u8d25\u5c31\u7b49\u4e8e\u628a\u81ea\u5df1\u9501\u6b7b\uff0c"
         "\u5fc5\u987b\u5148\u5efa\u7acb\u4e91\u63a7\u5236\u53f0 VNC \u6216\u5176\u4ed6\u5165\u53e3"))
    return rows


def check_service(d):
    rows = []
    if not d.get("sshd_active"):
        rows.append((CRITICAL,
         "sshd \u670d\u52a1\u672a\u8fd0\u884c\u3002"
         "\u5728\u53ea\u6709 SSH \u4e00\u4e2a\u5165\u53e3\u7684\u673a\u5668\u4e0a\uff0c"
         "\u670d\u52a1\u672a\u8d77\u610f\u5473\u7740\u5df2\u65e0\u6cd5\u767b\u5f55\uff0c"
         "\u5fc5\u987b\u4ece\u4e91\u63a7\u5236\u53f0\u6216\u5176\u4ed6\u5165\u53e3\u5904\u7406"))
    if not d.get("sshd_syntax_ok"):
        rows.append((CRITICAL,
         "sshd -t \u672a\u901a\u8fc7\uff0c\u8bf4\u660e\u914d\u7f6e\u6587\u4ef6\u8bed\u6cd5\u6709\u9519\uff0c\u6b64\u65f6 reload \u4f1a\u5931\u8d25\u3002"
         "\u5fc5\u987b\u5148\u4fee\u6b63\u8bed\u6cd5\u518d reload\uff0c\u5e76\u4fdd\u7559\u56de\u6eda\u7528\u7684\u5907\u4efd"))
    addr = (d.get("listen_addr") or "").strip()
    if addr and addr not in ("0.0.0.0", "*"):
        rows.append((INFO,
         "22 \u7aef\u53e3\u76d1\u542c\u5730\u5740\u662f %s\uff0c\u53ea\u5728\u672c\u673a\u53ef\u8fbe\uff0c"
         "\u4ece\u5916\u90e8\u8fde\u63a5\u4f1a\u88ab\u62d2\u7edd\u6216\u8d85\u65f6" % addr))
    return rows


def check_client(d):
    rows = []
    ce = (d.get("client_err") or "").strip().lower()
    if "too many authentication failures" in ce:
        rows.append((ISSUE,
         "\u547d\u4e2d Too many authentication failures: "
         "\u672c\u5730\u5bc6\u94a5\u8fc7\u591a\u8017\u5c3d\u4e86\u670d\u52a1\u7aef\u5c1d\u8bd5\u6b21\u6570\uff0c"
         "\u6b63\u786e\u5bc6\u94a5\u6ca1\u673a\u4f1a\u88ab\u9a8c\u8bc1\u3002"
         "\u89e3\u51b3: ssh -o IdentitiesOnly=yes -i <\u5bc6\u94a5> user@host"))
    mat = int(d.get("max_auth_tries") or 6)
    if mat == 0:
        rows.append((INFO,
         "MaxAuthTries \u4e3a 0\uff0c\u8868\u793a\u4e0d\u9650\u5236\u5c1d\u8bd5\u6b21\u6570\uff0c"
         "\u7b49\u4e8e\u6ca1\u6709\u66b4\u529b\u7834\u89e3\u9632\u62a4\uff0c\u5efa\u8bae\u8bbe\u4e3a 3 \u5230 6"))
    elif mat > 6:
        rows.append((INFO,
         "MaxAuthTries \u4e3a %d\uff0c\u9ad8\u4e8e\u5e38\u89c1\u7684 3 \u5230 6\uff0c"
         "\u4f1a\u653e\u5927\u66b4\u529b\u7834\u89e3\u6536\u76ca" % mat))
    for key, why in CLIENT_PATTERNS:
        if key in ce and key != "too many authentication failures":
            rows.append((ISSUE, why))
    return rows


def check_server_log(d):
    rows = []
    sl = (d.get("server_log") or "").strip().lower()
    for key, why in SERVER_PATTERNS:
        if key in sl:
            lv = ISSUE
            if "maxstartups" in key or "maximum authentication" in key:
                lv = BLOCKED
            if "failed password" in key or "invalid user" in key:
                lv = INFO
            rows.append((lv, why))
    return rows


def check_bomb(d):
    rows = []
    ms = (d.get("max_startups") or "").strip()
    surge = d.get("syn_surge")
    if ms:
        rows.append((INFO,
         "MaxStartups \u5f53\u524d\u4e3a %s\u3002\u8fbe\u5230\u9608\u503c\u65f6 sshd \u4f1a\u968f\u673a\u4e22\u5f03"
         "\u672a\u8ba4\u8bc1\u8fde\u63a5\uff0c\u8868\u73b0\u4e3a\u65f6\u597d\u65f6\u574f\u3002" % ms))
    if surge and surge > 1000:
        rows.append((BLOCKED,
         "\u672a\u8ba4\u8bc1\u8fde\u63a5\u5806\u79ef %d\uff0c\u63a5\u8fd1\u6216\u8d85\u8fc7 MaxStartups \u9608\u503c\uff0c"
         "\u65b0\u8fde\u63a5\u4f1a\u88ab\u968f\u673a\u4e22\u5f03\u3002\u4ec5\u8c03\u5927 MaxStartups \u4f1a\u66f4\u7cdf\uff0c"
         "\u5fc5\u987b\u540c\u65f6\u5c01\u7981\u6765\u6e90\u5e76\u6539\u7528\u5bc6\u94a5\u8ba4\u8bc1" % surge))
    sess = d.get("current_sessions")
    if sess and sess > 10:
        rows.append((INFO,
         "\u5f53\u524d\u4f1a\u8bdd\u6570 %d \u8d85\u8fc7 MaxSessions \u9ed8\u8ba4\u503c 10\uff0c"
         "\u65b0\u4f1a\u8bdd\u53ef\u80fd\u88ab\u62d2\u7edd" % sess))
    return rows


def check_blocked(d):
    rows = []
    if d.get("fail2ban_banned"):
        rows.append((BLOCKED,
         "\u5f53\u524d IP \u88ab fail2ban \u5c01\u7981\u3002"
         "\u89e3\u9501: fail2ban-client set sshd unbanip <\u4f60\u7684IP>\u3002"
         "\u4e0d\u8981\u505c\u6389\u6574\u4e2a fail2ban \u670d\u52a1\uff0c"
         "\u90a3\u7b49\u4e8e\u653e\u5f03\u9632\u62a4\u4e14\u5f71\u54cd\u6574\u7f51\uff1b"
         "\u6ce8\u610f\u540c\u4e00\u51fa\u53e3 IP \u7684\u540c\u4e8b\u53ef\u80fd\u4e00\u8d77\u88ab\u5c01"))
    if not d.get("fail2ban_jail"):
        rows.append((INFO,
         "\u672a\u53d1\u73b0 fail2ban jail \u914d\u7f6e\u3002"
         "\u82e5\u73af\u5883\u9700\u8981\u9632\u66b4\u529b\u7834\u89e3\uff0c"
         "\u5efa\u8bae\u5728\u5165\u53e3\u8bbe\u5907\u6216 fail2ban \u4e0a\u5c01\u7981\u6765\u6e90\uff0c"
         "\u4ec5\u9760 sshd \u81ea\u8eab\u4e0d\u591f"))
    return rows


def check_policy(d):
    rows = []
    if not d.get("allowusers_ok", 1):
        rows.append((ISSUE,
         "AllowUsers \u6216 DenyUsers \u9650\u5236\u4e86\u5f53\u524d\u7528\u6237\u3002\u6838\u5bf9: "
         "sshd -T -C user=<\u7528\u6237>,addr=<\u5ba2\u6237\u7aefIP> "
         "| grep -iE 'allowusers|denyusers'"))
    if d.get("match_block_hit"):
        rows.append((ISSUE,
         "\u5b58\u5728 Match \u5757\u3002Match \u4e4b\u540e\u7684\u914d\u7f6e\u9879\u53ea\u5728\u8be5\u4e0a\u4e0b\u6587\u4e2d\u751f\u6548\uff0c"
         "\u4e14\u672c\u5730 sshd -T \u4e0d\u5e26 -C \u663e\u793a\u7684\u662f\u9ed8\u8ba4\u4e0a\u4e0b\u6587\u503c\uff0c"
         "\u5fc5\u987b\u7528 sshd -T -C user=<\u7528\u6237>,addr=<\u5ba2\u6237\u7aefIP> \u9a8c\u8bc1"))
    return rows


def check_resource(d):
    rows = []
    du = d.get("disk_used_pct")
    iu = d.get("inode_used_pct")
    if du is not None and du >= 95:
        rows.append((ISSUE,
         "\u78c1\u76d8\u4f7f\u7528\u7387 %d%%\u3002\u78c1\u76d8\u6216 inode \u6ee1\u65f6 sshd \u53ef\u80fd\u65e0\u6cd5\u5199\u5165"
         "\u767b\u5f55\u8bb0\u5f55\uff0c\u767b\u5f55\u4f1a\u5361\u4f4f\u6216\u5931\u8d25\u3002"
         "\u5fc5\u987b\u5148\u6e05\u7a7a\u95f4\uff0c\u6539\u914d\u7f6e\u4e0d\u89e3\u51b3\u95ee\u9898" % du))
    if iu is not None and iu >= 95:
        rows.append((ISSUE,
         "inode \u4f7f\u7528\u7387 %d%%\uff0c\u540c\u6837\u4f1a\u5bfc\u81f4\u767b\u5f55\u8bb0\u5f55\u5199\u5165\u5931\u8d25\u3002"
         "\u5c0f\u6587\u4ef6\u8fc7\u591a\u662f\u5e38\u89c1\u6210\u56e0" % iu))
    if d.get("oom_seen"):
        rows.append((ISSUE,
         "24 \u5c0f\u65f6\u5185\u6709 OOM \u8bb0\u5f55\u3002\u5185\u5b58\u8017\u5c3d\u4f1a\u5bfc\u81f4\u4f1a\u8bdd\u88ab\u4e2d\u65ad\u6216\u670d\u52a1\u5f02\u5e38\uff0c"
         "\u7528 dmesg -T | grep -i 'out of memory' \u786e\u8ba4"))
    if not d.get("clock_ok", 1):
        rows.append((INFO,
         "\u5ba2\u6237\u7aef\u4e0e\u670d\u52a1\u7aef\u65f6\u949f\u504f\u5dee\u8f83\u5927\uff0c"
         "\u53ef\u80fd\u5bfc\u81f4 SSH \u534f\u8bae\u65f6\u95f4\u6233\u6821\u9a8c\u5931\u8d25\uff0c"
         "\u8868\u73b0\u4e3a\u96be\u4ee5\u89e3\u91ca\u7684\u8fde\u63a5\u91cd\u7f6e\u6216\u8ba4\u8bc1\u5f02\u5e38"))
    return rows


def _norm(rows, name):
    out = []
    for lv, note in rows:
        out.append((name, name, lv, note))
    return out


def worst(levels):
    lv = OK
    for x in levels:
        if LEVEL_ORDER.get(x, 0) > LEVEL_ORDER.get(lv, 0):
            lv = x
    return lv


def build(text, user, client_ip):
    raw = parse(text)
    d = dict(DEFAULTS)
    d.update(raw)
    kind, kind_level = classify(d)
    rows = [("\u5206\u7c7b", "\u6839\u56e0\u5206\u7c7b", kind_level,
             "\u6839\u56e0\u5206\u7c7b: **%s**\u3002\u540e\u7eed\u6392\u67e5\u987a\u5e8f\u636e\u6b64\u786e\u5b9a" % kind)]
    if raw:
        rows += _norm(check_entry(d), "\u5b89\u5168\u524d\u63d0")
        rows += _norm(check_service(d), "\u670d\u52a1\u4e0e\u914d\u7f6e")

    rows += _norm(check_client(d), "\u5ba2\u6237\u7aef")
    rows += _norm(check_server_log(d), "\u670d\u52a1\u7aef\u65e5\u5fd7")
    rows += _norm(check_bomb(d), "\u8fde\u63a5\u6570\u4e0e\u7206\u7834")
    rows += _norm(check_blocked(d), "\u5c01\u7981")
    rows += _norm(check_policy(d), "\u7b56\u7565\u9650\u5236")
    rows += _norm(check_resource(d), "\u8d44\u6e90")
    if not raw:
        rows.append(("\u8f93\u5165", "\u8f93\u5165", ISSUE,
                     "\u672a\u63d0\u4f9b\u4efb\u4f55\u89c2\u6d4b\u6570\u636e\u3002\u6392\u67e5\u7b2c\u4e00\u6b65\u662f\u62ff\u5230\u5ba2\u6237\u7aef ssh -vvv "
                     "\u4e0e\u670d\u52a1\u7aef journalctl -u sshd \u4e24\u4efd\u65e5\u5fd7\uff0c"
                     "\u6ca1\u6709\u65e5\u5fd7\u5c31\u6539\u914d\u7f6e\u7b49\u4e8e\u76f2\u6539"))
    return {
        "user": user or "\u672a\u6307\u5b9a",
        "client_ip": client_ip or "\u672a\u6307\u5b9a",
        "kind": kind,
        "overall": worst([r[2] for r in rows]),
        "observed": d,
        "rows": [{"group": g, "name": n, "level": lv, "note": note}
                 for g, n, lv, note in rows],
        "safe_order": list(SAFE_ORDER),
        "manual": list(MANUAL),
    }


def render_md(r):
    L = []
    L.append("# \u670d\u52a1\u5668\u65e0\u6cd5\u8fdc\u7a0b\u767b\u5f55\u5b9a\u4f4d\u62a5\u544a")
    L.append("")
    L.append("- \u7528\u6237: %s" % r["user"])
    L.append("- \u5ba2\u6237\u7aef IP: %s" % r["client_ip"])
    L.append("- \u6839\u56e0\u5206\u7c7b: **%s**" % r["kind"])
    L.append("- \u7efc\u5408\u7ed3\u8bba: **%s**" % r["overall"])
    L.append("")
    L.append("## \u4e00 \u9010\u9879\u5224\u5b9a")
    L.append("")
    L.append("| \u5206\u7ec4 | \u5224\u5b9a | \u8bf4\u660e |")
    L.append("|---|---|---|")
    for it in r["rows"]:
        L.append("| %s | %s | %s |" % (it["name"], it["level"], it["note"]))
    L.append("")
    L.append("## \u4e8c \u5206\u5c42\u6392\u67e5\u547d\u4ee4")
    L.append("")
    for name, cmds in SAFE_STEPS:
        L.append("### %s" % name)
        L.append("")
        for c in cmds:
            L.append("```bash\n%s\n```" % c)
        L.append("")
    L.append("## \u4e09 \u4fee\u6539\u8ba4\u8bc1\u914d\u7f6e\u7684\u5b89\u5168\u987a\u5e8f")
    L.append("")
    for i, t in enumerate(r["safe_order"], 1):
        L.append("%d. %s" % (i, t))
    L.append("")
    L.append("> \u7b2c 6\u30017 \u6b65\u662f\u9632\u9501\u6b7b\u7684\u5173\u952e\uff1a\u5148\u5f00\u65b0\u4f1a\u8bdd\u9a8c\u8bc1\u80fd\u8fde\u4e0a\uff0c"
             "\u518d\u5173\u6389\u65e7\u4f1a\u8bdd\u3002")
    L.append("> \u53cd\u8fc7\u6765\u505a\u5c31\u662f\u6807\u51c6\u7684\u4e8b\u6545\u5236\u9020\u6d41\u7a0b\u3002")
    L.append("")
    L.append("## \u56db \u5fc5\u987b\u4eba\u5de5\u786e\u8ba4")
    L.append("")
    for t in r["manual"]:
        L.append("- [ ] %s" % t)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> \u811a\u672c\u4e0d\u53d1\u8d77\u4efb\u4f55 SSH \u8fde\u63a5\u3001\u4e0d\u4fee\u6539\u4efb\u4f55\u914d\u7f6e\uff0c\u53ea\u5f52\u62e2\u89c2\u6d4b\u7ed3\u679c\u3002")
    L.append("> \u5728\u53ea\u6709 SSH \u4e00\u4e2a\u5165\u53e3\u7684\u670d\u52a1\u5668\u4e0a\u4fee\u6539\u8ba4\u8bc1\u914d\u7f6e\u5c5e\u4e8e\u9ad8\u98ce\u9669\u64cd\u4f5c\u3002")
    return "\n".join(L) + "\n"


SAMPLE_CLIENT_KEYS = """probe_result=ok
login_ok=0
auth_error=1
client_err=Too many authentication failures
max_auth_tries=6
sshd_active=1
sshd_syntax_ok=1
listen_addr=0.0.0.0
other_entry=1
disk_used_pct=40
"""

SAMPLE_MAXSTARTUPS = """probe_result=ok
login_ok=0
auth_error=1
server_log=Maximum authentication attempts exceeded for root
max_startups=10:30:100
syn_surge=2400
sshd_active=1
sshd_syntax_ok=1
listen_addr=0.0.0.0
other_entry=1
disk_used_pct=35
"""

SAMPLE_DISK = """probe_result=ok
sshd_active=1
sshd_syntax_ok=1
listen_addr=0.0.0.0
login_ok=0
auth_error=1
disk_used_pct=99
inode_used_pct=97
other_entry=1
"""

SAMPLE_BANNED = """probe_result=ok
sshd_active=1
sshd_syntax_ok=1
listen_addr=0.0.0.0
login_ok=0
auth_error=1
fail2ban_banned=1
fail2ban_jail=1
other_entry=1
"""

SAMPLE_MATCH = """probe_result=ok
sshd_active=1
sshd_syntax_ok=1
listen_addr=0.0.0.0
login_ok=0
auth_error=1
match_block_hit=1
allowusers_ok=0
other_entry=1
disk_used_pct=30
"""

SAMPLE_LOCKED = """probe_result=refused
sshd_active=0
sshd_syntax_ok=0
login_ok=0
other_entry=0
"""

SAMPLE_OK = """probe_result=ok
sshd_active=1
sshd_syntax_ok=1
listen_addr=0.0.0.0
login_ok=1
auth_error=0
fail2ban_jail=1
allowusers_ok=1
match_block_hit=0
oom_seen=0
clock_ok=1
other_entry=1
disk_used_pct=22
inode_used_pct=15
"""

SAMPLE_EMPTY = "# \u53ea\u6709\u6ce8\u91ca\n"

SAMPLE_JUNK = """\u8fd9\u884c\u6ca1\u6709\u5206\u9694\u7b26
unknown_key|1
max_auth_tries=abc
login_ok=yes
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

    p = parse(SAMPLE_CLIENT_KEYS)
    ck("parse_probe", p.get("probe_result"), "ok")
    ck("parse_trys", p.get("max_auth_tries"), 6)
    ck("parse_err_present", p.get("client_err") is not None, True)
    ck("parse_junk_num", parse(SAMPLE_JUNK).get("max_auth_tries"), None)
    ck("parse_junk_unknown", parse(SAMPLE_JUNK).get("unknown_key"), None)
    ck("parse_empty", parse(SAMPLE_EMPTY), {})
    ck("parse_none", parse(None), {})

    r1 = build(SAMPLE_CLIENT_KEYS, "deploy", "10.0.0.5")
    ck("keys_kind", r1["kind"], "\u5ba2\u6237\u7aef\u5bc6\u94a5\u8fc7\u591a")
    j1 = " ".join(it["note"] for it in r1["rows"])
    ck("keys_identities", "IdentitiesOnly=yes" in j1, True)
    ck("keys_real_cause", "\u6b63\u786e\u5bc6\u94a5\u6ca1\u673a\u4f1a\u88ab\u9a8c\u8bc1" in j1, True)

    r2 = build(SAMPLE_MAXSTARTUPS, "alice", "10.0.0.6")
    j2 = " ".join(it["note"] for it in r2["rows"])
    ck("maxstartups_cfg", "MaxStartups" in j2, True)
    ck("maxstartups_warn", "\u4ec5\u8c03\u5927 MaxStartups \u4f1a\u66f4\u7cdf" in j2, True)
    ck("maxstartups_surge", "\u672a\u8ba4\u8bc1\u8fde\u63a5\u5806\u79ef" in j2, True)
    ck("maxstartups_authlog", "MaxAuthTries" in j2, True)

    r3 = build(SAMPLE_DISK, "alice", "10.0.0.6")
    j3 = " ".join(it["note"] for it in r3["rows"])
    ck("disk_pct", "\u78c1\u76d8\u4f7f\u7528\u7387 99%" in j3, True)
    ck("disk_first", "\u5fc5\u987b\u5148\u6e05\u7a7a\u95f4" in j3, True)
    ck("inode_pct", "inode \u4f7f\u7528\u7387 97%" in j3, True)

    r4 = build(SAMPLE_BANNED, "alice", "10.0.0.6")
    ck("banned_kind", r4["kind"], "\u88ab\u5c01\u7981")
    j4 = " ".join(it["note"] for it in r4["rows"])
    ck("banned_unban", "fail2ban-client set sshd unbanip" in j4, True)
    ck("banned_not_stop", "\u4e0d\u8981\u505c\u6389\u6574\u4e2a fail2ban" in j4, True)

    r5 = build(SAMPLE_MATCH, "deploy", "10.0.0.7")
    j5 = " ".join(it["note"] for it in r5["rows"])
    ck("match_note", "sshd -T -C" in j5, True)
    ck("allowusers_note", "AllowUsers" in j5, True)

    r6 = build(SAMPLE_LOCKED, "root", "10.0.0.8")
    ck("locked_overall", r6["overall"], CRITICAL)
    j6 = " ".join(it["note"] for it in r6["rows"])
    ck("locked_entry", "\u6ca1\u6709\u5176\u4ed6\u767b\u5f55\u5165\u53e3" in j6, True)
    ck("locked_syntax", "sshd -t \u672a\u901a\u8fc7" in j6, True)
    ck("locked_service", "sshd_active" in " ".join(it["note"] for it in r6["rows"]) or "\u672a\u8fd0\u884c" in j6, True)

    r7 = build(SAMPLE_OK, "alice", "10.0.0.9")
    ck("ok_kind", r7["kind"], "\u53ef\u767b\u5f55")
    ck("ok_overall", r7["overall"], OK)

    r8 = build(SAMPLE_EMPTY, "alice", "10.0.0.9")
    ck("empty_overall", r8["overall"], ISSUE)
    ck("empty_note", "\u6ca1\u6709\u65e5\u5fd7\u5c31\u6539\u914d\u7f6e\u7b49\u4e8e\u76f2\u6539" in " ".join(
        it["note"] for it in r8["rows"]), True)

    md = render_md(r1)
    ck("md_header", md.startswith("# "), True)
    ck("md_kind", "\u6839\u56e0\u5206\u7c7b" in md, True)
    ck("md_steps", "\u5206\u5c42\u6392\u67e5\u547d\u4ee4" in md, True)
    ck("md_safe_order", "\u4fee\u6539\u8ba4\u8bc1\u914d\u7f6e\u7684\u5b89\u5168\u987a\u5e8f" in md, True)
    ck("md_manual", "\u5fc5\u987b\u4eba\u5de5\u786e\u8ba4" in md, True)
    js = json.loads(json.dumps(r2, ensure_ascii=False))
    ck("json_keys", sorted(js.keys()),
       ["client_ip", "kind", "manual", "observed", "overall", "rows",
        "safe_order", "user"])

    ck("client_pat_len", len(CLIENT_PATTERNS) >= 11, True)
    ck("server_pat_len", len(SERVER_PATTERNS) >= 7, True)
    ck("steps_len", len(SAFE_STEPS), 6)
    ck("order_len", len(SAFE_ORDER) >= 9, True)
    ck("manual_len", len(MANUAL) >= 12, True)
    ck("level_order", LEVEL_ORDER[CRITICAL] > LEVEL_ORDER[BLOCKED], True)
    ck("worst_fn", worst([OK, INFO, ISSUE]), ISSUE)

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--user", default="")
    ap.add_argument("--client-ip", default="")
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
    r = build(text, a.user, a.client_ip)
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