# -*- coding: utf-8 -*-
"""Webpack \u6784\u5efa\u914d\u7f6e\u4f53\u68c0\u4e0e stats.json \u4f53\u79ef\u5206\u6790\u3002

\u7528\u6cd5:
  python webpack_config_check.py --selftest
  python webpack_config_check.py --file webpack.config.js
  python webpack_config_check.py --file webpack.prod.js --prod
  python webpack_config_check.py --stats stats.json --top 20
"""
import argparse
import io
import json
import os
import re
import sys

FAILS = []

DEVTOOL_SLOW = ("eval-source-map", "inline-source-map", "cheap-source-map",
                "module-source-map", "source-map")
HEAVY_PATTERNS = ("moment/locale", "lodash", "echarts", "monaco", "three",
                  "antd", "element-ui", "xlsx", "babylon", "core-js")
MAX_EXTENSIONS = 5


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


def strip_comment(line):
    s = line.strip()
    if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
        return ""
    if "//" in line:
        line = line.split("//", 1)[0]
    return line


def detect_mode(text):
    m = re.search(r"\bmode\s*[:=]\s*['\"]?([A-Za-z_]+)", text)
    if not m:
        return "none"
    return m.group(1).lower()


def detect_cache(text):
    return {
        "has_cache": bool(re.search(r"\bcache\s*:", text)),
        "has_filesystem": "filesystem" in text,
        "has_build_deps": "buildDependencies" in text,
        "has_cache_loader": "cache-loader" in text,
    }


def detect_devtool(text):
    m = re.search(r"\bdevtool\s*[:=]\s*['\"]([^'\"]+)", text)
    return m.group(1) if m else None


def parse_extensions(text):
    m = re.search(r"\bextensions\s*:\s*\[([^\]]*)\]", text)
    if not m:
        return []
    return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]


def detect_split_chunks(text):
    has = "splitChunks" in text
    chunks = None
    m = re.search(r"\bchunks\s*:\s*['\"]?([A-Za-z_]+)", text)
    if has and m:
        chunks = m.group(1)
    return {"present": has, "chunks": chunks}


def check_loader_scope(text):
    """\u6bcf\u6761\u5e26 use/loader \u7684 rule\uff0c\u90fd\u5fc5\u987b\u6709 include \u6216 exclude\u3002"""
    lines = text.splitlines()
    offenders = []
    for i, raw in enumerate(lines):
        code = strip_comment(raw)
        if not re.search(r"\btest\s*:\s*", code):
            continue
        window = []
        for j in range(i, min(i + 14, len(lines))):
            window.append(strip_comment(lines[j]))
        block = "\n".join(window)
        if "use:" not in block and "loader:" not in block:
            continue
        if "include" not in block and "exclude" not in block:
            mt = re.search(r"\btest\s*:\s*(\S{0,40})", code)
            offenders.append(mt.group(1).rstrip(",") if mt else code.strip()[:40])
    return offenders


def analyze_config(text, prod=False):
    issues = []
    goods = []
    mode = detect_mode(text)
    if mode == "none":
        issues.append(("\u9519\u8bef", "\u672a\u663e\u5f0f\u58f0\u660e mode\uff0cwebpack \u4f1a\u6309 development \u5904\u7406\uff08\u7f3a\u538b\u7f29\u4e0e\u6447\u6811\u4f18\u5316\uff09"))
    elif mode != "production" and prod:
        issues.append(("\u4e25\u91cd", "\u751f\u4ea7\u914d\u7f6e\u91cc mode=%s\uff0c\u672a\u4f7f\u7528 production\uff0c\u4ea7\u7269\u4e0d\u4f1a\u538b\u7f29\u4e5f\u4e0d\u4f1a\u6447\u6811" % mode))
    elif mode == "production":
        goods.append("mode=production\uff0c\u5df2\u542f\u7528\u5185\u7f6e\u4f18\u5316")

    cache = detect_cache(text)
    if not cache["has_cache"]:
        issues.append(("\u4e25\u91cd", "\u672a\u914d\u7f6e cache\uff1awebpack 5 \u7684\u751f\u4ea7\u6784\u5efa\u9ed8\u8ba4\u4e0d\u5f00\u542f filesystem \u7f13\u5b58"))
    elif not cache["has_filesystem"]:
        if cache["has_cache_loader"]:
            issues.append(("\u8b66\u793a", "\u4f7f\u7528\u4e86 cache-loader\uff0cwebpack 5 \u5efa\u8bae\u6539\u7528\u5185\u7f6e cache.type=filesystem"))
        else:
            issues.append(("\u4e25\u91cd", "cache \u5df2\u914d\u7f6e\u4f46\u6ca1\u6709 type: 'filesystem'\uff0c\u6301\u4e45\u5316\u4e0d\u751f\u6548"))
    else:
        goods.append("\u5df2\u542f\u7528 filesystem \u7f13\u5b58")
        if not cache["has_build_deps"]:
            issues.append(("\u9519\u8bef", "cache \u672a\u58f0\u660e buildDependencies\uff0c\u6539\u4e86 webpack \u914d\u7f6e\u6587\u4ef6\u4e5f\u4e0d\u4f1a\u5931\u6548\uff0c\u4f1a\u51fa\u73b0\u300c\u6539\u4e86\u6ca1\u53d8\u5316\u300d"))

    for bad in check_loader_scope(text):
        issues.append(("\u9519\u8bef", "loader \u89c4\u5219 %s \u65e2\u6ca1\u6709 include \u4e5f\u6ca1\u6709 exclude\uff0c\u4f1a\u628a node_modules \u4e5f\u626b\u4e00\u904d" % bad))

    exts = parse_extensions(text)
    if len(exts) > MAX_EXTENSIONS:
        issues.append(("\u8b66\u793a", "resolve.extensions \u6709 %d \u9879\uff0c\u6bcf\u4e00\u9879\u90fd\u4f1a\u89e6\u53d1\u989d\u5916\u6587\u4ef6\u63a2\u6d4b" % len(exts)))
    elif exts:
        goods.append("resolve.extensions \u7cbe\u7b80\u4e3a %d \u9879" % len(exts))

    dev = detect_devtool(text)
    if dev:
        if dev.startswith("eval") and dev in DEVTOOL_SLOW:
            issues.append(("\u8b66\u793a", "devtool=%s \u4f1a\u5185\u8054 sourcemap\uff0c\u4ea7\u7269\u4f53\u79ef\u66b4\u6da8\u4e14\u6bcf\u6b21\u91cd\u5efa\u90fd\u91cd\u7b97" % dev))
        elif dev in ("inline-source-map", "eval-source-map"):
            issues.append(("\u8b66\u793a", "devtool=%s \u4e0d\u5efa\u8bae\u7528\u4e8e\u751f\u4ea7\u6216\u5927\u578b\u9879\u76ee" % dev))
        elif prod and dev.startswith("eval"):
            issues.append(("\u8b66\u793a", "\u751f\u4ea7\u6784\u5efa\u4f7f\u7528 devtool=%s\uff0c\u8c03\u8bd5\u4fe1\u606f\u4e0e\u6784\u5efa\u901f\u5ea6\u90fd\u4e0d\u7406\u60f3" % dev))

    sc = detect_split_chunks(text)
    if not sc["present"]:
        issues.append(("\u8b66\u793a", "\u672a\u914d\u7f6e optimization.splitChunks\uff0c\u7b2c\u4e09\u65b9\u4f9d\u8d56\u4e0d\u4f1a\u4e0e\u4e1a\u52a1\u4ee3\u7801\u5206\u79bb"))
    elif sc["chunks"] and sc["chunks"] != "all":
        issues.append(("\u63d0\u793a", "splitChunks.chunks=%s\uff0c\u9ed8\u8ba4 async \u4e0d\u4f1a\u62c6\u5206\u540c\u6b65 chunk\uff0c\u5efa\u8bae\u6539\u6210 all" % sc["chunks"]))
    elif sc["present"] and sc["chunks"] == "all":
        goods.append("splitChunks \u5df2\u914d\u7f6e chunks: all")

    if "thread-loader" not in text:
        issues.append(("\u63d0\u793a", "\u672a\u4f7f\u7528 thread-loader\uff1b\u6a21\u5757\u6570\u591a\u7684\u9879\u76ee\u53ef\u8003\u8651\uff0c\u4f46\u6a21\u5757\u6570\u5c0f\u4e8e 500 \u65f6\u53cd\u800c\u66f4\u6162"))
    if "babel-loader" in text and "cacheDirectory" not in text:
        issues.append(("\u63d0\u793a", "babel-loader \u672a\u5f00\u542f cacheDirectory: true"))
    if "ts-loader" in text and "transpileOnly" not in text:
        issues.append(("\u63d0\u793a", "ts-loader \u672a\u5f00\u542f transpileOnly\uff0c\u5efa\u8bae\u628a\u7c7b\u578b\u68c0\u67e5\u4ea4\u7ed9 fork-ts-checker \u5e76\u884c\u6267\u884c"))
    if "moment" in text and "IgnorePlugin" not in text and "ContextReplacementPlugin" not in text:
        issues.append(("\u63d0\u793a", "\u9879\u76ee\u5305\u542b moment \u4f46\u672a\u914d IgnorePlugin\uff0c\u53ef\u80fd\u628a\u5168\u90e8\u8bed\u8a00\u5305\u6253\u8fdb\u4ea7\u7269"))
    if "TerserPlugin" in text and "parallel" not in text:
        issues.append(("\u9519\u8bef", "TerserPlugin \u672a\u5f00\u542f parallel: true\uff0c\u538b\u7f29\u9636\u6bb5\u6ca1\u6709\u5e76\u884c"))
    if "externals" not in text:
        issues.append(("\u63d0\u793a", "\u672a\u914d\u7f6e externals\uff1b\u8d85\u5927\u4e14\u7a33\u5b9a\u7684\u7b2c\u4e09\u65b9\u5e93\u53ef\u8bc4\u4f30\u8d70 CDN\uff08\u6ce8\u610f SRI \u4e0e\u53ef\u7528\u6027\uff09"))
    if "parallelism" not in text:
        issues.append(("\u63d0\u793a", "\u672a\u914d\u7f6e optimization.parallelism\uff0c\u9ed8\u8ba4\u5e76\u884c\u5ea6\u8f83\u4fdd\u5b88"))
    return issues, goods


def flatten_modules(mods, out=None):
    out = [] if out is None else out
    for m in mods or []:
        nested = m.get("modules")
        if isinstance(nested, list) and nested:
            flatten_modules(nested, out)
            continue
        name = m.get("name") or m.get("identifier") or ""
        out.append({"name": name, "size": int(m.get("size") or 0)})
    return out


def top_modules(stats, top):
    mods = flatten_modules(stats.get("modules") or [])
    mods.sort(key=lambda x: (-x["size"], x["name"]))
    picked = mods[:max(1, top)]
    total = sum(m["size"] for m in mods) or 1
    nm = sum(m["size"] for m in mods if "node_modules" in m["name"])
    return mods, picked, total, nm


def analyze_stats(stats, top=20):
    mods, picked, total, nm = top_modules(stats, top)
    lines = []
    heavy = []
    for m in mods[:2000]:
        for pat in HEAVY_PATTERNS:
            if pat in m["name"]:
                heavy.append({"pattern": pat, "name": m["name"], "size": m["size"]})
                break
    lines.append("[\u4f53\u79ef\u5206\u6790] \u6a21\u5757\u603b\u6570 %d\uff0c\u5408\u8ba1 %.1f KB" % (len(mods), total / 1024.0))
    lines.append("  node_modules \u5360\u6bd4 %.1f%%" % (nm * 100.0 / total))
    lines.append("")
    lines.append("  \u4f53\u79ef\u6700\u5927\u7684 %d \u4e2a\u6a21\u5757\uff1a" % len(picked))
    for m in picked:
        lines.append("    %8.1f KB  %s" % (m["size"] / 1024.0, m["name"][:96]))
    if heavy:
        lines.append("")
        lines.append("  \u547d\u4e2d\u5df2\u77e5\u4f53\u79ef\u5927\u6237\uff1a")
        seen = set()
        for h in heavy:
            if h["pattern"] in seen and len(seen) > 6:
                continue
            seen.add(h["pattern"])
            lines.append("    [\u63d0\u793a] %s -> %s (%.1f KB)" % (
                h["pattern"], h["name"][:60], h["size"] / 1024.0))
            if len(seen) >= 8:
                break
    summary = {"modules": len(mods), "total_kb": round(total / 1024.0, 1),
               "node_modules_ratio": round(nm * 100.0 / total, 2),
               "top": [{"name": m["name"], "kb": round(m["size"] / 1024.0, 1)} for m in picked],
               "heavy": heavy[:20]}
    return "\n".join(lines), summary


def build_report(args, text=None, stats=None):
    lines = []
    summary = {}
    lines.append("=" * 62)
    lines.append("Webpack \u6784\u5efa\u4f53\u68c0\u62a5\u544a")
    lines.append("=" * 62)
    if stats is not None:
        body, summary = analyze_stats(stats, args.top)
        lines.append("")
        lines.append(body)
    elif text is not None:
        issues, goods = analyze_config(text, args.prod)
        order = ["\u4e25\u91cd", "\u9519\u8bef", "\u8b66\u793a", "\u63d0\u793a"]
        issues.sort(key=lambda x: order.index(x[0]) if x[0] in order else 9)
        summary["issues"] = [{"level": a, "msg": b} for a, b in issues]
        summary["goods"] = goods
        summary["problems"] = len(issues)
        lines.append("")
        lines.append("[\u6a21\u5f0f] %s   [\u8f93\u5165\u88ab\u89c6\u4e3a] %s" % (
            detect_mode(text), "\u751f\u4ea7\u914d\u7f6e" if args.prod else "\u901a\u7528\u914d\u7f6e"))
        lines.append("")
        for lv in order:
            group = [b for a, b in issues if a == lv]
            if not group:
                continue
            lines.append("[%s] %d \u9879" % (lv, len(group)))
            for msg in group:
                lines.append("  - %s" % msg)
        if goods:
            lines.append("")
            lines.append("[\u597d]")
            for g in goods:
                lines.append("  - %s" % g)
        lines.append("")
        lines.append("\u95ee\u9898\u9879\u5408\u8ba1: %d" % len(issues))
    lines.append("")
    lines.append("\u514d\u8d23: \u9759\u6001\u68c0\u67e5\u53ea\u53cd\u6620\u914d\u7f6e\u5199\u6cd5\uff0c\u5b9e\u9645\u52a0\u901f\u6548\u679c\u8bf7\u4ee5 SMP \u4e0e CI \u57fa\u7ebf\u4e3a\u51c6\u3002")
    lines.append("=" * 62)
    return "\n".join(lines), summary


CONFIG_BAD = """module.exports = {
  mode: 'development',
  module: {
    rules: [
      { test: /\\.js$/, use: ['babel-loader'] },
    ],
  },
  optimization: {
    minimizer: [new TerserPlugin()],
  },
  resolve: { extensions: ['.js', '.jsx', '.ts', '.tsx', '.vue', '.json', '.scss'] },
  devtool: 'eval-source-map',
};
"""

CONFIG_GOOD = """module.exports = {
  mode: 'production',
  cache: {
    type: 'filesystem',
    buildDependencies: { config: [__filename] },
  },
  module: {
    rules: [
      {
        test: /\\.jsx?$/,
        include: path.resolve(__dirname, 'src'),
        exclude: /node_modules/,
        use: ['thread-loader', 'babel-loader?cacheDirectory=true'],
      },
    ],
  },
  optimization: {
    splitChunks: { chunks: 'all' },
    minimizer: [new TerserPlugin({ parallel: true })],
  },
  resolve: { extensions: ['.js', '.jsx', '.json'] },
  devtool: 'source-map',
  externals: { react: 'React' },
};
"""

STATS_SAMPLE = {
    "modules": [
        {"name": "./src/index.js", "size": 2048},
        {"name": "./node_modules/moment/locale/zh-cn.js", "size": 300000},
        {"name": "./node_modules/lodash/lodash.js", "size": 500000},
        {"name": "./node_modules/react/index.js", "size": 8000},
        {"name": "./src/app.js", "size": 120000},
    ]
}


def selftest():
    ck("\u5e94\u8bc6\u522b development", detect_mode(CONFIG_BAD) == "development")
    ck("\u5e94\u8bc6\u522b production", detect_mode(CONFIG_GOOD) == "production")
    ck("\u65e0 mode \u65f6\u8fd4\u56de none", detect_mode("module.exports = { entry: 'a' }") == "none")

    cb = detect_cache(CONFIG_BAD)
    ck("\u574f\u6837\u672c\u6ca1\u6709 cache \u914d\u7f6e", cb["has_cache"] is False)
    cg = detect_cache(CONFIG_GOOD)
    ck("\u597d\u6837\u672c\u5e94\u6709 filesystem", cg["has_filesystem"] is True)
    ck("\u597d\u6837\u672c\u5e94\u6709 buildDependencies", cg["has_build_deps"] is True)

    ck("\u574f\u6837\u672c\u5e94\u6709 loader \u7f3a\u8303\u56f4", len(check_loader_scope(CONFIG_BAD)) == 1)
    ck("\u597d\u6837\u672c\u4e0d\u5e94\u6709 loader \u7f3a\u8303\u56f4", check_loader_scope(CONFIG_GOOD) == [])

    ck("\u5e94\u89e3\u6790\u51fa 7 \u4e2a extensions", len(parse_extensions(CONFIG_BAD)) == 7)
    ck("\u5e94\u89e3\u6790\u51fa 3 \u4e2a extensions", len(parse_extensions(CONFIG_GOOD)) == 3)

    ck("\u5e94\u53d6\u5230 devtool", detect_devtool(CONFIG_BAD) == "eval-source-map")
    ck("\u597d\u6837\u672c\u53d6\u5230 source-map", detect_devtool(CONFIG_GOOD) == "source-map")

    ck("\u574f\u6837\u672c\u6ca1\u6709 splitChunks", detect_split_chunks(CONFIG_BAD)["present"] is False)
    ck("\u597d\u6837\u672c chunks \u5e94\u4e3a all", detect_split_chunks(CONFIG_GOOD)["chunks"] == "all")

    ibad, _ = analyze_config(CONFIG_BAD, True)
    bad_msgs = [m for _, m in ibad]
    ck("\u574f\u6837\u672c\u5e94\u62a5 mode \u4e25\u91cd\u95ee\u9898", any("production" in m for m in bad_msgs))
    ck("\u574f\u6837\u672c\u5e94\u62a5\u7f3a cache", any("cache" in m for m in bad_msgs))
    ck("\u574f\u6837\u672c\u5e94\u62a5 loader \u65e0\u8303\u56f4", any("node_modules" in m for m in bad_msgs))
    ck("\u574f\u6837\u672c\u5e94\u62a5 devtool", any("devtool" in m for m in bad_msgs))
    ck("\u574f\u6837\u672c\u5e94\u62a5 TerserPlugin \u672a\u5e76\u884c", any("parallel" in m for m in bad_msgs))
    ck("\u574f\u6837\u672c\u5e94\u62a5 extensions \u8fc7\u591a", any("extensions" in m for m in bad_msgs))
    ck("\u574f\u6837\u672c\u5e94\u6709\u4e25\u91cd\u7ea7\u522b", any(l == "\u4e25\u91cd" for l, _ in ibad))

    igood, ggood = analyze_config(CONFIG_GOOD, True)
    good_msgs = [m for _, m in igood]
    ck("\u597d\u6837\u672c\u4e0d\u5e94\u6709\u4e25\u91cd\u95ee\u9898", not any(l == "\u4e25\u91cd" for l, _ in igood))
    ck("\u597d\u6837\u672c\u4e0d\u5e94\u6709\u9519\u8bef\u95ee\u9898", not any(l == "\u9519\u8bef" for l, _ in igood))
    ck("\u597d\u6837\u672c\u5e94\u62a5 filesystem \u7f13\u5b58\u751f\u6548", any("filesystem" in m for m in ggood))
    ck("\u597d\u6837\u672c\u95ee\u9898\u6570\u5e94\u5c11\u4e8e\u574f\u6837\u672c", len(igood) < len(ibad))

    flat = flatten_modules(STATS_SAMPLE["modules"])
    ck("\u5e94\u5c55\u5f00\u51fa 5 \u4e2a\u6a21\u5757", len(flat) == 5)
    nested = flatten_modules([{"name": "chunk", "modules": [
        {"name": "a.js", "size": 10}, {"name": "b.js", "size": 20}]}])
    ck("\u5d4c\u5957 modules \u5e94\u88ab\u5c55\u5f00", len(nested) == 2)

    mods, picked, total, nm = top_modules(STATS_SAMPLE, 3)
    ck("\u5e94\u6309\u4f53\u79ef\u5012\u5e8f\u53d6\u524d 3", [m["name"] for m in picked][0].endswith("lodash.js"))
    ck("\u603b\u5927\u5c0f\u5e94\u6b63\u786e", total == 2048 + 300000 + 500000 + 8000 + 120000)
    ck("node_modules \u5927\u5c0f\u5e94\u6b63\u786e", nm == 300000 + 500000 + 8000)

    txt, sm = analyze_stats(STATS_SAMPLE, 3)
    ck("stats \u5206\u6790\u5e94\u8f93\u51fa\u6807\u9898", "\u4f53\u79ef\u5206\u6790" in txt)
    ck("stats \u5e94\u8bc6\u522b node_modules \u5360\u6bd4", sm["node_modules_ratio"] > 80)
    ck("stats \u5e94\u547d\u4e2d\u5df2\u77e5\u5927\u6237", len(sm["heavy"]) >= 2)

    _, sm2 = build_report(argparse.Namespace(prod=True, top=3), text=CONFIG_BAD)
    ck("\u62a5\u544a\u5e94\u7edf\u8ba1\u95ee\u9898\u9879", sm2["problems"] > 0)
    _, sm3 = build_report(argparse.Namespace(prod=True, top=3), stats=STATS_SAMPLE)
    ck("stats \u62a5\u544a\u5e94\u7ed9\u51fa\u6a21\u5757\u6570", sm3["modules"] == 5)
    return not FAILS


def main():
    ap = argparse.ArgumentParser(description="Webpack \u6784\u5efa\u914d\u7f6e\u4f53\u68c0\u4e0e stats \u5206\u6790")
    ap.add_argument("--file", help="webpack \u914d\u7f6e\u6587\u4ef6")
    ap.add_argument("--stats", help="webpack --profile --json \u4ea7\u51fa\u7684 stats.json")
    ap.add_argument("--top", type=int, default=20, help="\u4f53\u79ef\u5206\u6790\u8f93\u51fa\u7684\u6a21\u5757\u6570")
    ap.add_argument("--prod", action="store_true", help="\u58f0\u660e\u8fd9\u662f\u751f\u4ea7\u914d\u7f6e")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="\u7ed3\u679c\u5199\u5165\u6587\u4ef6")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    if args.selftest:
        ok = selftest()
        write_result(os.path.join(here, "_selftest_result.txt"))
        sys.exit(0 if ok else 1)

    if not args.file and not args.stats:
        ap.error("\u9700\u8981 --file / --stats / --selftest")

    text = None
    stats = None
    if args.file:
        text = io.open(args.file, "r", encoding="utf-8", errors="ignore").read()
    if args.stats:
        stats = json.loads(io.open(args.stats, "r", encoding="utf-8").read())

    report, summary = build_report(args, text, stats)
    out_path = args.out or os.path.join(here, "_last_result.txt")
    body = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else report
    io.open(out_path, "w", encoding="utf-8").write(body)
    print(body)
    print("")
    print("\u7ed3\u679c\u5df2\u5199\u5165: %s" % out_path)


if __name__ == "__main__":
    main()
