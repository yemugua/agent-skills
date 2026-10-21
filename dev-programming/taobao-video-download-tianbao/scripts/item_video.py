#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝商品视频下载（主图视频 / 详情视频）
=====================================
原理：连接本机已登录的 Edge（CDP 9222 端口，与签到脚本同一套方案），
打开商品详情页，从两个渠道抓视频直链：
  1) DOM 里 <video> 元素的 src / currentSrc（主图视频最可靠）
  2) 网络层监听响应（content-type 含 video，或 URL 含 .mp4/.m3u8/.flv 等）

主图视频默认不自动播放，脚本会 hover 主图 + 点播放按钮 + JS 强制 play() 来触发加载。

用法（bat 一键）：
    双击 下载淘宝商品视频.bat，按提示粘贴商品链接

命令行：
    python item_video.py <商品链接> [--mode auto|main|detail] [--list] [--out DIR]

输出：
    out/ 目录下的 .mp4

说明：
    - mp4 直链：直接下载
    - m3u8：本机有 ffmpeg 时自动合并，否则只打印直链
    - 遇登录弹窗/滑块会停下来等你手动处理，不绕过
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from playwright.sync_api import sync_playwright

try:
    import requests
except ImportError:
    requests = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
OUT_DIR = os.path.join(BASE_DIR, "out")
CDP = "http://127.0.0.1:9222"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0")

VIDEO_EXT = (".mp4", ".m3u8", ".flv", ".mov", ".webm", ".ts")
VIDEO_HINT = ("video", "cloudvideo", "videotrans", "taobao.com/video")


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Log:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(LOG_DIR, "item_video_%s.log" % name)
        self._f = open(self.path, "a", encoding="utf-8")

    def log(self, msg):
        line = "[%s] %s" % (now_str(), msg)
        try:
            print(line, flush=True)
        except Exception:  # noqa: BLE001
            pass
        self._f.write(line + "\n")
        self._f.flush()


def looks_video(url, ctype=""):
    u = (url or "").split("?")[0].lower()
    if any(u.endswith(x) for x in VIDEO_EXT):
        return True
    c = (ctype or "").lower()
    if "video" in c or "mpegurl" in c:
        return True
    return any(h in u for h in VIDEO_HINT)


def collect_dom_videos(page):
    """从 DOM 里读 <video> 的 src / currentSrc / source。"""
    js = """
() => {
  const out = [];
  for (const v of document.querySelectorAll('video')) {
    const cands = [v.currentSrc, v.src];
    v.querySelectorAll('source').forEach(s => cands.push(s.src));
    for (const c of cands) {
      if (c && c.startsWith('http')) out.push(c);
    }
  }
  for (const f of document.querySelectorAll('iframe')) {
    try {
      const d = f.contentDocument;
      if (!d) continue;
      d.querySelectorAll('video').forEach(v => {
        const cands = [v.currentSrc, v.src];
        v.querySelectorAll('source').forEach(s => cands.push(s.src));
        for (const c of cands) { if (c && c.startsWith('http')) out.push(c); }
      });
    } catch (e) {}
  }
  return out;
}
"""
    try:
        return page.evaluate(js) or []
    except Exception:  # noqa: BLE001
        return []


def force_play(page, log):
    """JS 强制播放页面上所有 video（静音），触发真实加载。"""
    js = """
() => {
  let n = 0;
  for (const v of document.querySelectorAll('video')) {
    try { v.muted = true; v.volume = 0; const p = v.play(); if (p) p.catch(()=>{}); n++; } catch (e) {}
  }
  return n;
}
"""
    try:
        n = page.evaluate(js)
        if n:
            log.log("  JS 强制播放 %d 个 video 元素（静音）" % n)
    except Exception:  # noqa: BLE001
        pass


def trigger_main_video(page, log):
    """触发主图视频：hover 主图区 + 点播放按钮。"""
    log.log("触发主图视频：hover 主图区域 ...")
    sels = ["#J_ImgBooth", ".tb-gallery", "#J_UlThumb li", ".main-pic", ".img-main"]
    for s in sels:
        try:
            loc = page.locator(s).first
            if loc.count() == 0:
                continue
            loc.scroll_into_view_if_needed(timeout=2000)
            loc.hover(timeout=2000)
            log.log("  hover %s OK" % s)
            break
        except Exception:  # noqa: BLE001
            continue

    # 主图视频通常要滚到主图并停留一会儿才加载
    for _ in range(4):
        force_play(page, log)
        time.sleep(2)

    # 点播放按钮（可能盖在主图上）
    btn_sels = [".tb-video-play-btn", ".video-play-btn", ".J_VideoPlayBtn",
                "[class*='play']", "[aria-label*='播放']"]
    for s in btn_sels:
        try:
            loc = page.locator(s).first
            if loc.count() == 0:
                continue
            if loc.is_visible():
                loc.click(timeout=1500, force=True)
                log.log("  点击播放按钮 %s" % s)
                break
        except Exception:  # noqa: BLE001
            continue
    time.sleep(3)
    force_play(page, log)
    time.sleep(2)


def trigger_detail_video(page, log):
    """触发详情视频：缓慢滚动到详情区，边滚边强制播放。"""
    log.log("触发详情视频：滚动页面 ...")
    js_scroll = "() => { window.scrollTo(0, document.body.scrollHeight * %f); return window.scrollY; }"
    for f in (0.2, 0.35, 0.5, 0.65, 0.8, 0.95):
        try:
            page.evaluate(js_scroll % f)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.5)
        force_play(page, log)
    time.sleep(3)


def pick_and_download(cands, out_dir, log, referer):
    """按 Content-Length 从大到小尝试下载，成功一个就返回。"""
    if requests is None:
        log.log("未安装 requests，无法下载。请运行: pip install requests")
        return None

    os.makedirs(out_dir, exist_ok=True)
    session = requests.Session()
    headers = {"User-Agent": UA, "Referer": referer,
               "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9"}

    scored = []
    for u in cands:
        size = -1
        try:
            r = session.head(u, headers=headers, timeout=15, allow_redirects=True)
            size = int(r.headers.get("Content-Length") or -1)
            ctype = r.headers.get("Content-Type", "")
        except Exception:  # noqa: BLE001
            ctype = ""
        scored.append((size, u, ctype))
        log.log("候选: %s | 大小=%s | %s" % (u[:110], size if size > 0 else "未知", ctype or "-"))

    scored.sort(key=lambda x: x[0], reverse=True)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for size, u, ctype in scored:
        low = u.split("?")[0].lower()
        if low.endswith(".m3u8"):
            if shutil.which("ffmpeg"):
                dst = os.path.join(out_dir, "item_%s.m3u8.mp4" % ts)
                log.log("m3u8 下载中（ffmpeg）: %s" % u[:110])
                cmd = ["ffmpeg", "-y", "-user_agent", UA,
                       "-headers", "Referer: %s\r\n" % referer,
                       "-i", u, "-c", "copy", "-bsf:a", "aac_adtstoasc", dst]
                try:
                    subprocess.run(cmd, check=True, timeout=600,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(dst) and os.path.getsize(dst) > 0:
                        log.log("★ 下载完成: %s (%d 字节)" % (dst, os.path.getsize(dst)))
                        return dst
                except Exception as e:  # noqa: BLE001
                    log.log("  ffmpeg 失败: %s" % e)
            else:
                log.log("本机无 ffmpeg，m3u8 直链交给用户: %s" % u)
            continue

        # 普通 mp4/flv/webm
        ext = os.path.splitext(low)[1] or ".mp4"
        dst = os.path.join(out_dir, "item_%s%s" % (ts, ext))
        try:
            log.log("下载中: %s" % u[:110])
            with session.get(u, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = 0
                with open(dst, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 18):
                        if chunk:
                            f.write(chunk)
                            total += len(chunk)
            if total > 1024:
                log.log("★ 下载完成: %s (%d 字节)" % (dst, total))
                return dst
            os.remove(dst)
        except Exception as e:  # noqa: BLE001
            log.log("  下载失败: %s | %s" % (u[:80], e))
    return None


def main():
    ap = argparse.ArgumentParser(description="淘宝商品视频下载")
    ap.add_argument("url", nargs="?", help="商品详情页链接")
    ap.add_argument("--mode", default="auto", choices=["auto", "main", "detail"],
                    help="auto=主图+详情都试（默认）；main=只抓主图视频；detail=只抓详情视频")
    ap.add_argument("--list", action="store_true", help="只列出直链，不下载")
    ap.add_argument("--out", default=OUT_DIR, help="输出目录")
    args = ap.parse_args()

    url = args.url
    if not url:
        url = input("粘贴商品链接: ").strip()
    if not url.startswith("http"):
        # 淘口令里的短链情况很复杂，这里只支持 http(s) 链接
        print("请粘贴完整的 http(s) 商品链接")
        return 1

    log = Log()
    log.log("=== 淘宝商品视频下载启动 ===")
    log.log("商品链接: %s" % url)

    init_script = (
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        "Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});"
        "Object.defineProperty(navigator,'languages',{get:()=>['zh-CN','zh','en']});"
        "window.chrome={runtime:{}};"
    )

    net_cands = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP)
        except Exception as e:  # noqa: BLE001
            log.log("无法连接 Edge 调试端口 %s：%s" % (CDP, e))
            log.log("请先双击「下载淘宝商品视频.bat」让它自动启动带调试端口的 Edge。")
            return 1

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        try:
            context.add_init_script(init_script)
        except Exception:  # noqa: BLE001
            pass
        page = context.new_page()

        def on_response(resp):
            try:
                u = resp.url
                ct = ""
                try:
                    ct = (resp.headers or {}).get("content-type", "")
                except Exception:  # noqa: BLE001
                    pass
                if looks_video(u, ct):
                    net_cands.append(u)
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:  # noqa: BLE001
            log.log("打开商品页失败: %s" % e)
        time.sleep(4)

        # 登录检测
        try:
            txt = page.inner_text("body", timeout=5000) or ""
        except Exception:  # noqa: BLE001
            txt = ""
        if ("亲，请登录" in txt or "密码登录" in txt) and len(txt) < 3000:
            log.log("检测到未登录/登录弹窗，请在弹出的 Edge 里登录，脚本最多等 300 秒 ...")
            for _ in range(60):
                time.sleep(5)
                try:
                    t2 = page.inner_text("body", timeout=3000) or ""
                except Exception:  # noqa: BLE001
                    t2 = ""
                if "亲，请登录" not in t2 and len(t2) > 3000:
                    log.log("已登录，继续。")
                    break
        if any(k in txt for k in ["滑块", "验证码", "安全验证"]):
            log.log("检测到滑块/验证码，请在 Edge 里手动完成后重跑脚本。")
            return 1

        dom_cands = []

        if args.mode in ("auto", "main"):
            trigger_main_video(page, log)
            dom_cands += collect_dom_videos(page)

        if args.mode in ("auto", "detail"):
            trigger_detail_video(page, log)
            dom_cands += collect_dom_videos(page)

        # 兜底：再滚一轮，很多详情视频是懒加载
        try:
            page.evaluate("() => window.scrollTo(0,0)")
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
        dom_cands += collect_dom_videos(page)

        all_c = []
        seen = set()
        for u in dom_cands + net_cands:
            if not u or u in seen:
                continue
            seen.add(u)
            all_c.append(u)

        log.log("共捕获 %d 个候选直链（DOM %d / 网络 %d）"
                % (len(all_c), len(set(dom_cands)), len(set(net_cands))))

        if not all_c:
            log.log("没抓到任何视频直链。可能这个商品没有视频，或视频需要点击才加载。")
            log.log("建议：手动在 Edge 里点开视频播放几秒后，再重跑一次脚本。")
            return 1

        if args.list:
            for u in all_c:
                log.log("直链: %s" % u)
            return 0

        dst = pick_and_download(all_c, args.out, log, url)
        if dst:
            log.log("完成: %s" % dst)
        else:
            log.log("所有候选都下载失败了。可用 --list 看直链，或用浏览器/下载工具手动下。")
        # CDP：不关闭用户的 Edge
    return 0


if __name__ == "__main__":
    sys.exit(main())
