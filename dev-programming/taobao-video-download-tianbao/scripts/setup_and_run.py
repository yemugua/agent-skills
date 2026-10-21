#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键启动器：装依赖 → 启动带调试端口 9222 的 Edge → 让你粘贴商品链接 → 下载视频

用法：
    python setup_and_run.py
    python setup_and_run.py <商品链接>        # 直接带链接
    python setup_and_run.py --list            # 只列直链不下载
"""
import os
import subprocess
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
ITEM_SCRIPT = os.path.join(HERE, "item_video.py")
MIRROR = "https://mirrors.aliyun.com/pypi/simple/"
EDGE_CANDS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
PORT = 9222


def run(cmd, **kw):
    return subprocess.run(cmd, **kw)


def ensure_deps():
    try:
        import playwright  # noqa: F401
        import requests    # noqa: F401
        print("依赖检查：playwright + requests 已就绪")
        return
    except ImportError:
        print("正在安装 playwright + requests（阿里源）...")
    run([sys.executable, "-m", "pip", "install", "playwright", "requests", "-i", MIRROR])
    print("安装完成")


def edge_alive():
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/json/version" % PORT, timeout=2)
        return True
    except Exception:  # noqa: BLE001
        return False


def start_edge():
    exe = None
    for c in EDGE_CANDS:
        if os.path.exists(c):
            exe = c
            break
    if not exe:
        print("未找到 Edge。请手动用以下命令启动浏览器后重跑：")
        print("  msedge.exe --remote-debugging-port=9222")
        return False
    profile = os.path.join(SKILL_ROOT, "edge_profile")
    os.makedirs(profile, exist_ok=True)
    subprocess.Popen([exe, "--remote-debugging-port=%d" % PORT,
                      "--user-data-dir=%s" % profile,
                      "--no-first-run", "--no-default-browser-check", "about:blank"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(16):
        time.sleep(1)
        if edge_alive():
            print("Edge 调试端口已就绪")
            return True
    print("Edge 启动超时，请手动打开带 --remote-debugging-port=9222 的 Edge 后重跑")
    return False


def main():
    args = sys.argv[1:]
    url = None
    for a in args:
        if a.startswith("http"):
            url = a

    ensure_deps()

    if edge_alive():
        print("Edge 调试端口已就绪")
    else:
        print("正在启动带调试端口 9222 的 Edge ...")
        if not start_edge():
            return 1

    if not url:
        try:
            url = input("粘贴商品链接后回车: ").strip()
        except EOFError:
            url = ""
    if not url or not url.startswith("http"):
        print("未提供有效的 http(s) 商品链接")
        return 1

    cmd = [sys.executable, ITEM_SCRIPT, url] + [a for a in args if not a.startswith("http")]
    print("\n开始处理: %s\n" % url)
    r = run(cmd)
    print("\n完成。视频输出目录: %s" % os.path.join(SKILL_ROOT, "out"))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
