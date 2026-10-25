# -*- coding: utf-8 -*-
# ===== SkillHub 企业通道 本地一键脚本（通用版）=====
# 用法: python skillhub_run.py [清单URL]
#   不带参数=默认用 GITHUB_RAW 清单
# cookies.txt 同目录（两行: sid=xxx / skh_ent_token=xxx）
import json, time, uuid, sys, urllib.request, urllib.error
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

BASE = "https://api.skillhub.cn/api/v1/orgs/3839"
PUBLISHER_ID = 3390
DEFAULT_MANIFEST = "https://raw.githubusercontent.com/yemugua/agent-skills/main/_upload_queue/latest.json"

def load_cookie():
    try:
        ck = open("cookies.txt", encoding="utf-8").read().strip()
        if "sid=" in ck and "skh_ent_token=" in ck: return ck
    except FileNotFoundError: pass
    sid = input("sid: ").strip(); tok = input("skh_ent_token: ").strip()
    return f"sid={sid}; skh_ent_token={tok}"

def req(url, method="GET", data=None, ctype=None, timeout=30):
    h = {"Cookie": CK, "User-Agent": "Mozilla/5.0"}
    if ctype: h["Content-Type"] = ctype
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=timeout)
        return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def fetch_json(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=30).read())

def upload(items):
    ok, skip, fail = [], [], []
    print(f"=== 上传 {len(items)} 个 ===")
    for i, it in enumerate(items):
        slug = it["slug"]
        u = f"https://raw.githubusercontent.com/yemugua/agent-skills/main/skills/{it['category']}/{slug}/SKILL.md"
        try:
            content = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=30).read().decode("utf-8")
        except Exception as e:
            fail.append(f"{slug}:fetch:{e}"); print(f"x 拉取失败 {slug}"); time.sleep(1); continue
        b = "----skh" + uuid.uuid4().hex
        payload = json.dumps({"slug": slug, "displayName": it["name"], "version": "1.0.0", "category": it["category"]})
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"payload\"\r\n\r\n{payload}\r\n"
                f"--{b}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"SKILL.md\"\r\n"
                f"Content-Type: text/markdown\r\n\r\n{content}\r\n--{b}--\r\n").encode("utf-8")
        code, _ = req(f"{BASE}/skills", "POST", body, f"multipart/form-data; boundary={b}")
        if code in (200, 201): ok.append(slug); print(f"+ {i+1}/{len(items)} {slug}")
        elif code == 409: skip.append(slug); print(f"o 已存在 {slug}")
        elif code == 429: print("! 429 当日额度满"); break
        else: fail.append(f"{slug}:{code}"); print(f"x {slug} HTTP {code}")
        time.sleep(1.6)
    print(f"=== 上传完成 成功:{len(ok)} 跳过:{len(skip)} 失败:{len(fail)} ===")
    if fail: print("失败:", ",".join(fail))

def review_and_publish():
    print("=== 审核队列扫描 ===")
    pending, page = [], 1
    while page <= 200:
        code, body = req(f"{BASE}/admin/skills/reviews?page={page}&page_size=20")
        if code != 200: print(f"队列读取失败 HTTP {code}"); return
        d = json.loads(body)
        revs = d.get("reviews") or []
        if not revs: break
        for x in revs:
            st = x.get("reviewStatus") or x.get("status")
            if st in ("admin_review", "pending"): pending.append(x)
        page += 1; time.sleep(0.3)
    print(f"=== 待审数量: {len(pending)} ===")
    okc = failc = 0
    for s in pending:
        slug = s.get("slug"); ver = s.get("latestApprovedVersion") or s.get("version") or "1.0.0"
        code, _ = req(f"{BASE}/admin/skills/{slug}/approve", "POST",
                      json.dumps({"version": ver, "note": "自动审核通过"}).encode(), "application/json")
        if code not in (200, 201, 409): print(f"x approve {slug} {code}"); failc += 1; continue
        time.sleep(0.9)
        code, _ = req(f"{BASE}/admin/skills/{slug}/publish-to-community", "POST",
                      json.dumps({"publisherProfileId": PUBLISHER_ID}).encode(), "application/json")
        if code in (200, 201, 409): print(f"+ 已发布 {slug}"); okc += 1
        else: print(f"x publish {slug} {code}"); failc += 1
        time.sleep(0.9)
    print(f"=== 审发完成 成功:{okc} 失败:{failc} ===")

if __name__ == "__main__":
    CK = load_cookie()
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MANIFEST
    print("清单:", url)
    items = fetch_json(url)
    t0 = time.time()
    upload(items)
    print("等待2分钟后开始审核发布..."); time.sleep(120)
    review_and_publish()
    print(f"全部完成，用时 {(time.time()-t0)/60:.1f} 分钟")
