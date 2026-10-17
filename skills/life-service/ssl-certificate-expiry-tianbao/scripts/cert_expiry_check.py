# -*- coding: utf-8 -*-
"""SSL \u8bc1\u4e66\u5230\u671f\u5206\u7ea7\u3001\u7b97\u6cd5\u5f3a\u5ea6\u3001SAN \u5339\u914d\u4e0e\u94fe\u7ed3\u6784\u6838\u67e5\u3002

\u7528\u6cd5:
  python cert_expiry_check.py --file cert.pem --host example.com
  python cert_expiry_check.py --file cert.pem --chain chain.pem --host www.example.com
  python cert_expiry_check.py --selftest
"""
import argparse
import base64
import binascii
import datetime
import json
import os
import re
import sys

OK = "\u6b63\u5e38"
WATCH = "\u5173\u6ce8"
ALERT = "\u544a\u8b66"
URGENT = "\u7d27\u6025"
EXPIRED = "\u5df2\u8fc7\u671f"
NOTYET = "\u672a\u751f\u6548"

# \u5206\u7ea7\u9608\u503c\uff08\u5269\u4f59\u5929\u6570\u4e0a\u754c\uff0cNone \u8868\u793a\u65e0\u4e0a\u754c\uff09
GRADES = [
    (45, OK),
    (15, WATCH),
    (7, ALERT),
    (0, URGENT),
    (None, EXPIRED),
]

# \u7b7e\u540d\u7b97\u6cd5\u7981\u7528/\u5141\u8bb8
SIG_BAD = ("sha1", "md5")
SIG_GOOD = ("sha256", "sha384", "sha512")
SIG_UNKNOWN = ("unknown", "")

WEAK_KEY_BITS = 1024
MIN_RSA_BITS = 2048

CHAIN_ORDER_NOTE = (
    "\u94fe\u987a\u5e8f\u5e94\u4e3a: \u53f6\u5b50\u5728\u6700\u524d, \u4e2d\u95f4\u8bc1\u4e66\u6b21\u4e4b, \u6839\u8bc1\u4e66\u901a\u5e38\u4e0d\u4e0b\u53d1\u3002")


def pem_blocks(text):
    return re.findall(
        r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----",
        text or "", re.S)


def der_to_text(der_b64):
    """\u6781\u7b80 DER \u89e3\u6790\uff1a\u53ea\u53d6\u9700\u8981\u7684\u5b57\u6bb5\uff0c\u4e0d\u4f9d\u8d56\u7b2c\u4e09\u65b9\u5e93\u3002"""
    data = base64.b64decode(re.sub(r"\s+", "", der_b64))
    out = {}

    def read_len(buf, i):
        ln = buf[i]
        i += 1
        if ln & 0x80:
            n = ln & 0x7F
            ln = int.from_bytes(buf[i:i + n], "big")
            i += n
        return ln, i

    def parse_tlv(buf, i):
        tag = buf[i]
        i += 1
        ln, i = read_len(buf, i)
        return tag, buf[i:i + ln], i + ln

    _, seq, _ = parse_tlv(data, 0)

    # TBSCertificate
    tag, tbs, _ = parse_tlv(seq, 0)
    if tag != 0x30:
        return out
    i = 0

    # [0] version (optional)
    if tbs[i] == 0xA0:
        _, _, i = parse_tlv(tbs, i)

    # serialNumber
    _, _, i = parse_tlv(tbs, i)
    # signature AlgorithmIdentifier
    _, sigalg, i = parse_tlv(tbs, i)
    out["sigalg_der"] = sigalg.hex()
    # issuer
    _, _, i = parse_tlv(tbs, i)
    # validity
    _, validity, i = parse_tlv(tbs, i)
    tag, nb, j = parse_tlv(validity, 0)
    tag, na, _ = parse_tlv(validity, j)
    out["not_before"] = decode_time(nb)
    out["not_after"] = decode_time(na)
    # subject
    _, subject, i = parse_tlv(tbs, i)
    out["subject_der"] = subject.hex()
    # subjectPublicKeyInfo
    _, spki, i = parse_tlv(tbs, i)
    tag, alg, k = parse_tlv(spki, 0)
    out["pub_alg_der"] = alg.hex()
    tag, keybits, _ = parse_tlv(spki, k)
    # BIT STRING content 的首字节是「未使用位数」，需扣除
    out["key_bits"] = max(0, (len(keybits) - 1)) * 8
    # extensions [3]
    san = []
    while i < len(tbs) and tbs[i] == 0xA3:
        _, exts, i = parse_tlv(tbs, i)
        # Extensions ::= SEQUENCE OF Extension
        tag, extseq, _qe = parse_tlv(exts, 0)
        q = 0
        while q < len(extseq):
            tag, onext, q = parse_tlv(extseq, q)
            tag, oidval, r = parse_tlv(onext, 0)
            # OID 2.5.29.17 = subjectAltName
            if oidval.hex() == "551d11":
                tag, octet, _re = parse_tlv(onext, r)
                tag, gseq, _ge = parse_tlv(octet, 0)
                s = 0
                while s < len(gseq):
                    gtag, gval, s = parse_tlv(gseq, s)
                    if gtag == 0x82:
                        san.append(("dns", gval.decode("utf-8", "replace")))
                    elif gtag == 0x87:
                        san.append(("ip", gval.decode("utf-8", "replace")))
    out["san"] = san
    return out


def decode_time(b):
    s = b.decode("ascii", "replace")
    fmts = ["%y%m%d%H%M%SZ", "%Y%m%d%H%M%SZ"]
    for f in fmts:
        try:
            return datetime.datetime.strptime(s, f).replace(
                tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
    return None


def cn_from_der(hexstr):
    """\u4ece subject DER \u91cc\u7c97\u53d6 CN\uff08OID 2.5.4.3 = 55 04 03\uff09\u3002"""
    if not hexstr:
        return ""
    b = binascii.unhexlify(hexstr)
    idx = b.find(binascii.unhexlify("550403"))
    if idx < 0:
        return ""
    j = idx + 3
    if j >= len(b):
        return ""
    tag = b[j]
    ln = b[j + 1]
    if ln & 0x80:
        n = ln & 0x7F
        ln = int.from_bytes(b[j + 2:j + 2 + n], "big")
        start = j + 2 + n
    else:
        start = j + 2
    return b[start:start + ln].decode("utf-8", "replace")


def parse_cert(text):
    blocks = pem_blocks(text)
    if not blocks:
        return None
    info = der_to_text(blocks[0])
    if not info:
        return None
    info["cn"] = cn_from_der(info.get("subject_der"))
    info["sigalg"] = read_sigalg(info.get("sigalg_der"))
    info["pub_alg"] = read_pubalg(info.get("pub_alg_der"))
    info["fingerprint"] = binascii.hexlify(
        base64.b64decode(re.sub(r"\s+", "", blocks[0]))).decode()[:32].upper()
    return info


def algid_oid(hexstr):
    """从 AlgorithmIdentifier 的 DER 十六进制里取出 OID 内容的十六进制。"""
    if not hexstr:
        return ""
    try:
        b = binascii.unhexlify(hexstr)
    except (binascii.Error, ValueError):
        return ""
    if len(b) < 2 or b[0] != 0x06:
        return ""
    ln = b[1]
    if ln & 0x80:
        n = ln & 0x7F
        ln = int.from_bytes(b[2:2 + n], "big")
        return b[2 + n:2 + n + ln].hex()
    return b[2:2 + ln].hex()


def read_sigalg(hexstr):
    oid = algid_oid(hexstr)
    if not oid:
        return ""
    table = oid_name_table()
    name = table.get(oid)
    if name:
        return name
    return "unknown(" + oid[:16] + ")"


def oid_name_table():
    return {
        # PKCS#1
        "2a864886f70d010104": "md5WithRSAEncryption",
        "2a864886f70d010105": "sha1WithRSAEncryption",
        "2a864886f70d01010b": "sha256WithRSAEncryption",
        "2a864886f70d01010c": "sha384WithRSAEncryption",
        "2a864886f70d01010d": "sha512WithRSAEncryption",
        "2a864886f70d010101": "RSA",
        # ECDSA
        "2a8648ce38040302": "ecdsa-with-SHA256",
        "2a8648ce38040303": "ecdsa-with-SHA384",
        "2a8648ce38040304": "ecdsa-with-SHA512",
        "2a8648ce38040301": "ecdsa-with-SHA1",
        "2a8648ce3e0301d": "sha1WithRSAEncryption",
        "2a8648ce380401": "EC",
        # RSA PKCS#1 v1.5 variants
        "2a864886f70d0101": "RSA",
    }


def read_pubalg(hexstr):
    oid = algid_oid(hexstr)
    if not oid:
        return "unknown"
    if oid.startswith("2a864886f70d0101"):
        return "RSA"
    if oid.startswith("2a8648ce380401"):
        return "EC"
    if oid.startswith("2b810400"):
        return "EC"
    return "unknown"


def parse_all(text):
    out = []
    for b in pem_blocks(text):
        info = der_to_text(b)
        if info:
            out.append(info)
    return out


def grade_days(days):
    if days is None:
        return None, "\u65e0\u6cd5\u89e3\u6790\u5230\u671f\u65f6\u95f4"
    if days > 45:
        return OK, "\u5269\u4f59 %d \u5929\uff0c\u9ad8\u4e8e\u6ce8\u610f\u7ebf 45 \u5929" % days
    if days > 15:
        return WATCH, "\u5269\u4f59 %d \u5929\uff0c\u5df2\u8fdb\u5165\u5173\u6ce8\u533a\u95f4" % days
    if days > 7:
        return ALERT, "\u5269\u4f59 %d \u5929\uff0c\u5e94\u7acb\u5373\u53d1\u8d77\u7eed\u7b7e" % days
    if days > 0:
        return URGENT, "\u5269\u4f59 %d \u5929\uff0c\u9700\u5347\u7ea7\u5904\u7406" % days
    if days == 0:
        return URGENT, "\u4eca\u5929\u5230\u671f\uff0c\u9700\u5347\u7ea7\u5904\u7406"
    return EXPIRED, "\u5df2\u8fc7\u671f %d \u5929" % (-days)


def check_alg(cert):
    """\u8fd4\u56de (\u7b49\u7ea7, \u8bf4\u660e\u5217\u8868)\u3002"""
    notes = []
    level = OK
    sig = (cert.get("sigalg") or "").lower()
    if any(k in sig for k in SIG_BAD):
        level = ALERT
        notes.append("\u7b7e\u540d\u7b97\u6cd5\u8fc7\u65e7: %s\uff0c\u5e94\u91cd\u65b0\u7b7e\u53d1\uff08\u65e0\u6cd5\u5728\u914d\u7f6e\u5c42\u8865\u6551\uff09"
                     % cert.get("sigalg"))
    elif any(k in sig for k in SIG_GOOD):
        notes.append("\u7b7e\u540d\u7b97\u6cd5: %s\uff08\u5408\u89c4\uff09" % cert.get("sigalg"))
    else:
        level = WATCH if level == OK else level
        notes.append("\u7b7e\u540d\u7b97\u6cd5\u672a\u8bc6\u522b: %s\uff0c\u9700\u4eba\u5de5\u786e\u8ba4\u662f\u5426\u4ecd\u88ab\u5ba2\u6237\u7aef\u63a5\u53d7"
                     % cert.get("sigalg"))

    bits = cert.get("key_bits") or 0
    alg = cert.get("pub_alg")
    if alg == "RSA":
        if bits < WEAK_KEY_BITS:
            level = ALERT
            notes.append("RSA \u5bc6\u94a5\u4ec5 %d \u4f4d\uff0c\u5df2\u88ab\u4e3b\u6d41\u6d4f\u89c8\u5668\u62d2\u7edd\uff0c\u5fc5\u987b\u91cd\u7b7e" % bits)
        elif bits < MIN_RSA_BITS:
            level = ALERT
            notes.append("RSA \u5bc6\u94a5 %d \u4f4d\u4f4e\u4e8e\u6700\u4f4e\u8981\u6c42 %d \u4f4d\uff0c\u5efa\u8bae\u91cd\u7b7e"
                         % (bits, MIN_RSA_BITS))
        else:
            notes.append("RSA \u5bc6\u94a5 %d \u4f4d\uff08\u5408\u89c4\uff09" % bits)
    elif alg == "EC":
        notes.append("\u516c\u94a5\u7b97\u6cd5: EC\uff08\u5408\u89c4\uff09")
    elif alg:
        level = WARN if level == OK else level
        notes.append("\u516c\u94a5\u7b97\u6cd5\u672a\u8bc6\u522b: %s\uff0c\u9700\u4eba\u5de5\u786e\u8ba4" % alg)
    return level, notes


def san_list(cert):
    return [v for k, v in cert.get("san") or [] if k == "dns"]


def san_matches(pattern, host):
    """\u901a\u914d\u7b26\u5339\u914d: * \u53ea\u5339\u914d\u4e00\u7ea7\u6807\u7b7e\uff0c\u4e14\u4e0d\u5339\u914d\u88f8\u57df\u3002"""
    p = pattern.strip().lower().lstrip(".")
    h = (host or "").strip().lower().rstrip(".")
    if not p:
        return False
    if p == h:
        return True
    if "*" not in p:
        return False
    pp = p.split(".")
    hh = h.split(".")
    if len(pp) != len(hh):
        return False
    if pp[0] != "*":
        return False
    if hh[0] == "":
        return False
    return pp[1:] == hh[1:]


def check_host(cert, host):
    if not host:
        return None, []
    sans = san_list(cert)
    if not sans:
        return ALERT, [
            "SAN \u4e3a\u7a7a\u3002\u73b0\u4ee3\u5ba2\u6237\u7aef\u5b8c\u5168\u5ffd\u7565 CN\uff0c\u4ec5 CN \u5339\u914d\u7684\u8bc1\u4e66\u4f1a\u88ab\u5224\u4e3a"
            "\u8bc1\u4e66\u540d\u4e0d\u5339\u914d\uff0c\u5fc5\u987b\u91cd\u7b7e\u3002CN=%s" % (cert.get("cn") or "\u7a7a")]
    hits = [s for s in sans if san_matches(s, host)]
    if hits:
        return OK, ["\u57df\u540d %s \u88ab SAN \u8986\u76d6\uff08\u5339\u914d\u9879: %s\uff09" % (host, ", ".join(hits))]
    wild = [s for s in sans if "*" in s]
    hints = []
    for s in wild:
        suffix = s.split("*", 1)[1]
        bare = suffix.lstrip(".")
        hl = host.lower()
        if hl == bare:
            hints.append("\u901a\u914d\u7b26 %s \u4e0d\u5339\u914d\u88f8\u57df %s"
                         "\uff08\u88f8\u57df\u5fc5\u987b\u5355\u5217\u5728 SAN\uff09"
                         % (s, host))
        elif suffix and hl.endswith(suffix):
            hints.append("\u901a\u914d\u7b26 %s \u53ea\u5339\u914d\u4e00\u7ea7\u5b50"
                         "\u57df\uff0c\u4e0d\u8de8\u70b9\uff0c%s \u5c42\u7ea7\u8fc7\u6df1"
                         "\uff1b\u5982\u9700\u8986\u76d6\u8bf7\u5355\u72ec\u7b7e\u53d1"
                         % (s, host))
        else:
            hints.append("SAN \u4e2d\u65e0 %s\uff1b\u73b0\u6709\u6761\u76ee: %s"
                         % (host, ", ".join(sans)))
        break
    if not hints:
        hints.append("SAN \u4e2d\u65e0 %s\uff1b\u73b0\u6709\u6761\u76ee: %s" % (host, ", ".join(sans)))
    return ALERT, hints


def check_chain(chain_text):
    """\u8fd4\u56de (\u7b49\u7ea7, \u8bf4\u660e\u5217\u8868)\u3002"""
    certs = parse_all(chain_text)
    notes = []
    n = len(certs)
    if n == 0:
        return WATCH, ["\u94fe\u6587\u4ef6\u4e3a\u7a7a\u6216\u65e0\u6cd5\u89e3\u6790\uff0c\u8df3\u8fc7\u94fe\u6821\u9a8c"]
    if n == 1:
        return ALERT, ["\u53ea\u6709 1 \u5f20\u8bc1\u4e66: \u4ec5\u53f6\u5b50\u8bc1\u4e66\u3002\u65b0\u5ba2\u6237\u7aef\u4f1a\u62a5 "
                       "unable to get local issuer certificate\uff0c\u5fc5\u987b\u8865\u4e2d\u95f4\u8bc1\u4e66\u3002"]
    if n == 2:
        notes.append("\u4e0b\u53d1 2 \u5f20\uff08\u53f6\u5b50 + \u4e2d\u95f4\uff09\uff0c\u7ed3\u6784\u6b63\u786e\u3002")
    elif n >= 3:
        notes.append("\u4e0b\u53d1 %d \u5f20\uff0c\u8d85\u8fc7\u5e38\u89c4\u7684 2 \u5f20\u3002\u6839\u8bc1\u4e66\u901a\u5e38\u4e0d\u5e94\u4e0b\u53d1\uff0c"
                     "\u8bf7\u786e\u8ba4\u7b2c 3 \u5f20\u662f\u5426\u4e3a\u6839\u3002" % n)
    notes.append(CHAIN_ORDER_NOTE)
    return OK, notes


VERIFY_LIST = [
    "openssl s_client \u62ff\u5230\u7684\u5e8f\u5217\u53f7\u662f\u65b0\u7684\uff08\u4e0d\u662f\u65e7\u8bc1\u4e66\uff09",
    "\u94fe\u987a\u5e8f: \u53f6\u5b50\u6700\u524d, \u4e2d\u95f4\u6b21\u4e4b, \u6839\u672a\u4e0b\u53d1",
    "openssl verify -untrusted fullchain.pem leaf.pem \u8f93\u51fa OK",
    "\u8bc1\u4e66\u4e0e\u79c1\u94a5\u914d\u5bf9: \u4e24\u4e2a md5 \u4e00\u81f4",
    "notBefore \u5df2\u751f\u6548\uff08\u4e0d\u662f\u672a\u6765\u65f6\u95f4\uff09",
    "\u4ece\u5916\u90e8\u5ba2\u6237\u7aef\u8bbf\u95ee\uff08\u4e0d\u662f\u672c\u673a curl 127.0.0.1\uff09",
    "SAN \u91cc\u6bcf\u4e00\u4e2a\u57df\u540d\u90fd\u8bbf\u95ee\u4e00\u6b21\uff0c\u4e0d\u80fd\u53ea\u6d4b\u4e3b\u57df\u540d",
    "\u8d70 CDN/WAF \u65f6\u786e\u8ba4\u8fb9\u7f18\u4e0e\u6e90\u7ad9\u8bc1\u4e66\u90fd\u5df2\u6362",
    "\u8d1f\u8f7d\u5747\u8861\u96c6\u7fa4\u9010\u53f0\u90fd\u5df2\u6362",
    "nginx -T | grep ssl_certificate \u786e\u8ba4\u5b9e\u9645\u751f\u6548\u8def\u5f84",
    "\u79c1\u94a5 600 / \u8bc1\u4e66 644 / \u76ee\u5f55 755",
    "\u65b0\u5230\u671f\u65e5\u5df2\u5f55\u5165\u76d1\u63a7\uff0c\u5e8f\u5217\u53f7\u5df2\u767b\u8bb0",
    "\u65e7\u8bc1\u4e66\u4e0e\u79c1\u94a5\u6587\u4ef6\u5df2\u4ece\u670d\u52a1\u5668\u5220\u9664",
    "\u65e5\u5fd7\u4e2d\u4e0d\u518d\u51fa\u73b0 TLS \u63e1\u624b\u5931\u8d25",
]


def build_report(cert, host, chain_text, as_of):
    now = as_of
    nb = cert.get("not_before")
    na = cert.get("not_after")
    days = None
    if na and now:
        days = int((na - now).total_seconds() // 86400)
    g, why = grade_days(days)

    notyet = False
    if nb and now and now < nb:
        notyet = True
        g = NOTYET
        why = "notBefore \u5728 %s\uff0c\u665a\u4e8e\u57fa\u51c6\u65e5 %s\uff08\u5148\u6838\u5bf9\u5ba2\u6237\u7aef\u65f6\u949f\uff09" % (
            nb.date().isoformat(), now.date().isoformat())

    alg_level, alg_notes = check_alg(cert)
    host_level, host_notes = check_host(cert, host)
    chain_level, chain_notes = check_chain(chain_text) if chain_text else (None, [])

    levels = [x for x in (g, alg_level, host_level, chain_level) if x]
    overall = max(levels, key=LEVEL_ORDER.get) if levels else OK

    return {
        "as_of": now.date().isoformat() if now else "",
        "overall": overall,
        "days_left": days,
        "expiry_grade": g,
        "expiry_note": why,
        "not_before": nb.date().isoformat() if nb else "",
        "not_after": na.date().isoformat() if na else "",
        "cn": cert.get("cn", ""),
        "san": san_list(cert),
        "sigalg": cert.get("sigalg", ""),
        "pub_alg": cert.get("pub_alg", ""),
        "key_bits": cert.get("key_bits", 0),
        "fingerprint_prefix": cert.get("fingerprint", ""),
        "host": host or "",
        "notyet_valid": notyet,
        "alg_level": alg_level or OK,
        "alg_notes": alg_notes,
        "host_level": host_level or OK,
        "host_notes": host_notes,
        "chain_level": chain_level or OK,
        "chain_notes": chain_notes,
    }


LEVEL_ORDER = {OK: 0, WATCH: 1, ALERT: 2, URGENT: 3, EXPIRED: 4, NOTYET: 2}


def render_md(r):
    L = []
    L.append("# SSL \u8bc1\u4e66\u6838\u67e5\u62a5\u544a")
    L.append("")
    L.append("- \u57fa\u51c6\u65e5: %s" % r["as_of"])
    L.append("- \u57df\u540d: %s" % (r["host"] or "\uff08\u672a\u6307\u5b9a\uff0c\u8df3\u8fc7\u5339\u914d\u6821\u9a8c\uff09"))
    L.append("- \u7efc\u5408\u7ed3\u8bba: **%s**" % r["overall"])
    L.append("")
    L.append("## \u4e00 \u5230\u671f\u72b6\u6001")
    L.append("")
    L.append("| \u9879 | \u503c |")
    L.append("|---|---|")
    L.append("| \u5206\u7ea7 | %s |" % r["expiry_grade"])
    L.append("| \u5269\u4f59\u5929\u6570 | %s |" % ("\u4e0d\u53ef\u89e3\u6790" if r["days_left"] is None else r["days_left"]))
    L.append("| notBefore | %s |" % (r["not_before"] or "\u89e3\u6790\u5931\u8d25"))
    L.append("| notAfter | %s |" % (r["not_after"] or "\u89e3\u6790\u5931\u8d25"))
    L.append("| \u8bf4\u660e | %s |" % r["expiry_note"])
    L.append("| \u6307\u7eb9(\u524d32) | %s |" % r["fingerprint_prefix"])
    L.append("")
    L.append("## \u4e8c \u8eab\u4efd\u4e0e\u7b97\u6cd5")
    L.append("")
    L.append("- CN: %s" % (r["cn"] or "\u7a7a"))
    L.append("- SAN: %s" % (", ".join(r["san"]) if r["san"] else "\u7a7a\uff08\u4e25\u91cd: \u73b0\u4ee3\u5ba2\u6237\u7aef\u5ffd\u7565 CN\uff09"))
    L.append("- \u7b7e\u540d\u7b97\u6cd5: %s\uff08\u5224\u5b9a %s\uff09" % (r["sigalg"], r["alg_level"]))
    L.append("- \u516c\u94a5: %s %s \u4f4d" % (r["pub_alg"], r["key_bits"]))
    for n in r["alg_notes"]:
        L.append("- %s" % n)
    L.append("")
    if r["host_notes"]:
        L.append("## \u4e09 \u57df\u540d\u5339\u914d\uff08%s\uff09" % r["host_level"])
        L.append("")
        for n in r["host_notes"]:
            L.append("- %s" % n)
        L.append("")
    if r["chain_notes"]:
        L.append("## \u56db \u8bc1\u4e66\u94fe\uff08%s\uff09" % r["chain_level"])
        L.append("")
        for n in r["chain_notes"]:
            L.append("- %s" % n)
        L.append("")
    L.append("## \u6362\u8bc1\u540e\u9a8c\u8bc1\u6e05\u5355")
    L.append("")
    for t in VERIFY_LIST:
        L.append("- [ ] %s" % t)
    L.append("")
    L.append("---")
    L.append("")
    L.append("> \u811a\u672c\u8bfb\u7684\u662f\u8bc1\u4e66\u6587\u672c\uff0c\u4e0d\u662f\u7ebf\u4e0a\u7aef\u53e3\u3002\u5b83\u4e0d\u80fd\u544a\u8bc9\u4f60\u670d\u52a1\u5668\u73b0\u5728\u53d1\u7684\u662f\u4e0d\u662f\u8fd9\u5f20\u8bc1\u4e66\u3001")
    L.append("> reload \u6709\u6ca1\u6709\u751f\u6548\u2014\u2014\u90a3\u4e24\u4ef6\u4e8b\u5fc5\u987b\u7528 openssl s_client \u5728\u7ebf\u9a8c\u8bc1\uff08\u52a1\u5fc5\u5e26 -servername\uff09\u3002")
    return "\n".join(L) + "\n"


def render_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)


# ---- \u81ea\u68c0\u7528\u7684\u5408\u6210 DER \u6784\u9020\uff08\u4e0d\u4f9d\u8d56 openssl \u53ef\u6267\u884c\u6587\u4ef6\uff09----
def _len(n):
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def tlv(tag, val):
    return bytes([tag]) + _len(len(val)) + val


def build_test_cert(not_before, not_after, cn="example.com",
                    san=None, sig_oid="2a864886f70d01010b",
                    pub_oid="2a864886f70d010101", key_len=2048):
    def tm(dt):
        return dt.strftime("%y%m%d%H%M%SZ").encode("ascii")

    nb = tlv(0x17, tm(not_before))
    na = tlv(0x17, tm(not_after))
    validity = tlv(0x30, nb + na)
    serial = tlv(0x02, b"\x01")
    alg = tlv(0x30, tlv(0x06, binascii.unhexlify(sig_oid)) + tlv(0x05, b""))
    name = tlv(0x30, tlv(0x06, binascii.unhexlify("550403"))
               + tlv(0x0C, cn.encode("utf-8")))
    key = bytes(key_len // 8)
    spki = tlv(0x30, tlv(0x30, tlv(0x06, binascii.unhexlify(pub_oid))
                          + tlv(0x05, b"")) + tlv(0x03, b"\x00" + key))
    exts_body = b""
    if san is not None:
        entries = b""
        for kind, val in san:
            if kind == "dns":
                entries += tlv(0x82, val.encode("utf-8"))
            else:
                entries += tlv(0x87, binascii.unhexlify(val))
        gseq = tlv(0x30, entries)
        octet = tlv(0x04, gseq)
        ext = tlv(0x30, tlv(0x06, binascii.unhexlify("551d11")) + octet)
        exts_body = tlv(0xA3, tlv(0x30, ext))
    tbs = tlv(0x30, serial + alg + name + validity + name + spki + exts_body)
    cert = tlv(0x30, tbs + alg)
    b64 = base64.b64encode(cert).decode("ascii")
    lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    return ("-----BEGIN CERTIFICATE-----\n" + "\n".join(lines)
            + "\n-----END CERTIFICATE-----\n")


def selftest():
    res = []
    ok = True

    def ck(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        res.append("%s %s got=%r want=%r"
                   % ("PASS" if good else "FAIL", name, got, want))

    as_of = datetime.datetime(2026, 10, 11, tzinfo=datetime.timezone.utc)

    # 1. \u5230\u671f\u5206\u7ea7
    ck("grade_100", grade_days(100)[0], OK)
    ck("grade_46", grade_days(46)[0], OK)
    ck("grade_45", grade_days(45)[0], WATCH)
    ck("grade_30", grade_days(30)[0], WATCH)
    ck("grade_10", grade_days(10)[0], ALERT)
    ck("grade_3", grade_days(3)[0], URGENT)
    ck("grade_0", grade_days(0)[0], URGENT)
    ck("grade_neg", grade_days(-5)[0], EXPIRED)
    ck("grade_none", grade_days(None)[0], None)

    # 2. SAN \u901a\u914d\u7b26\u5339\u914d
    ck("m_exact", san_matches("example.com", "example.com"), True)
    ck("m_wild_sub", san_matches("*.example.com", "www.example.com"), True)
    ck("m_wild_bare", san_matches("*.example.com", "example.com"), False)
    ck("m_wild_deep", san_matches("*.example.com", "a.b.example.com"), False)
    ck("m_wild_notroot", san_matches("www*.example.com", "www1.example.com"), False)
    ck("m_case", san_matches("*.Example.COM", "WWW.example.com"), True)
    ck("m_dotprefix", san_matches(".example.com", "example.com"), True)

    # 3. \u5408\u6210\u8bc1\u4e66\u89e3\u6790
    nb = datetime.datetime(2025, 10, 11, tzinfo=datetime.timezone.utc)
    na = datetime.datetime(2026, 12, 31, tzinfo=datetime.timezone.utc)
    pem = build_test_cert(nb, na, cn="example.com",
                          san=[("dns", "example.com"), ("dns", "*.example.com")])
    c = parse_cert(pem)
    ck("parse_ok", c is not None, True)
    ck("parse_cn", c.get("cn"), "example.com")
    ck("parse_notafter", c.get("not_after"), na)
    ck("parse_notbefore", c.get("not_before"), nb)
    ck("parse_san", san_list(c), ["example.com", "*.example.com"])
    ck("parse_sigalg", c.get("sigalg"), "sha256WithRSAEncryption")
    ck("parse_pubalg", c.get("pub_alg"), "RSA")
    ck("parse_bits", c.get("key_bits"), 2048)

    # 4. \u7b97\u6cd5\u5224\u5b9a
    ck("alg_ok", check_alg(c)[0], OK)
    weak = parse_cert(build_test_cert(
        nb, na, sig_oid="2a864886f70d010105", pub_oid="2a864886f70d010101",
        key_len=512))
    ck("alg_sha1", check_alg(weak)[0], ALERT)
    ck("alg_sha1_note", "\u91cd\u65b0\u7b7e\u53d1" in " ".join(check_alg(weak)[1]), True)
    small = parse_cert(build_test_cert(nb, na, key_len=512))
    ck("alg_weak_key", check_alg(small)[0], ALERT)

    # 5. \u57df\u540d\u5339\u914d
    ck("host_hit", check_host(c, "www.example.com")[0], OK)
    ck("host_bare", check_host(c, "example.com")[0], OK)
    lvl, notes = check_host(c, "a.b.example.com")
    ck("host_deep", lvl, ALERT)
    ck("host_deep_note", "\u4e0d\u8de8\u70b9" in " ".join(notes), True)
    nosan = parse_cert(build_test_cert(nb, na, san=[]))
    lv2, n2 = check_host(nosan, "example.com")
    ck("host_no_san", lv2, ALERT)
    ck("host_no_san_note", "\u5ffd\u7565 CN" in " ".join(n2), True)
    ck("host_skip", check_host(c, None)[0], None)

    # 6. \u94fe\u7ed3\u6784
    lv, n3 = check_chain(pem)
    ck("chain_one", lv, ALERT)
    ck("chain_one_note", "unable to get local issuer" in " ".join(n3), True)
    ck("chain_two", check_chain(pem + pem)[0], OK)
    ck("chain_empty", check_chain("")[0], WATCH)
    ck("chain_three", check_chain(pem + pem + pem)[0], OK)

    # 7. \u62a5\u544a\u751f\u6210
    r = build_report(c, "www.example.com", pem + pem, as_of)
    ck("r_days", r["days_left"], 81)
    ck("r_grade", r["expiry_grade"], OK)
    ck("r_notyet", r["notyet_valid"], False)
    ck("r_overall_ok", r["overall"], OK)
    ck("r_has_san", len(r["san"]), 2)

    r2 = build_report(c, "a.b.example.com", pem, as_of)
    ck("r2_overall", r2["overall"], ALERT)
    r3 = build_report(nosan, "example.com", None, as_of)
    ck("r3_no_chain_note", r3["chain_notes"], [])

    # 8. notBefore \u5728\u672a\u6765
    fut = parse_cert(build_test_cert(
        datetime.datetime(2027, 1, 1, tzinfo=datetime.timezone.utc), na))
    r4 = build_report(fut, "example.com", None, as_of)
    ck("notyet_grade", r4["expiry_grade"], NOTYET)
    ck("notyet_flag", r4["notyet_valid"], True)

    # 9. \u5df2\u8fc7\u671f
    old = parse_cert(build_test_cert(
        datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc)))
    r5 = build_report(old, "example.com", None, as_of)
    ck("expired_grade", r5["expiry_grade"], EXPIRED)
    ck("expired_overall", r5["overall"], EXPIRED)

    # 10. \u6e32\u67d3
    md = render_md(r2)
    ck("md_header", md.startswith("# "), True)
    ck("md_has_list", "\u6362\u8bc1\u540e\u9a8c\u8bc1\u6e05\u5355" in md, True)
    ck("md_list_len", len(VERIFY_LIST) >= 14, True)
    js = json.loads(render_json(r))
    ck("json_keys_min", "expiry_grade" in js and "san" in js, True)
    ck("json_level_order", LEVEL_ORDER[EXPIRED] > LEVEL_ORDER[URGENT], True)

    for line in res:
        print(line)
    print("SELFTEST %s (%d assertions)" % ("OK" if ok else "FAILED", len(res)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--chain")
    ap.add_argument("--host", default="")
    ap.add_argument("--as-of", default="")
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
    cert = parse_cert(text)
    if not cert:
        print("ERROR cannot parse certificate from --file")
        return 3

    as_of = datetime.datetime.now(datetime.timezone.utc)
    if a.as_of:
        m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", a.as_of.strip())
        if m:
            as_of = datetime.datetime(int(m.group(1)), int(m.group(2)),
                                      int(m.group(3)),
                                      tzinfo=datetime.timezone.utc)

    chain_text = ""
    if a.chain and os.path.exists(a.chain):
        chain_text = open(a.chain, "r", encoding="utf-8", errors="replace").read()

    r = build_report(cert, a.host, chain_text, as_of)
    body = render_md(r) if a.format == "md" else render_json(r)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print("WROTE %s" % a.out)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())