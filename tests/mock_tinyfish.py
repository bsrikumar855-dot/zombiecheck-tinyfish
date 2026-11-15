#!/usr/bin/env python3
"""Local stand-in for TinyFish Fetch/Search/Agent/Datasets, with a fake web. Kinds by domain prefix:
alive-, slow-, stale-, dead-, parked-, moved-(rebrand, brand kept), absorbed- (redirect to bigco.example), shut-, blocked-, gh-"""
import json, re, sys, threading, time, uuid
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
T = date.today()
DS = {}
RUNS = {}

def d(days): return (T - timedelta(days=days)).isoformat()

def page(host, path):
    kind = host.split(".")[0].split("-")[0]
    brand = host.split(".")[0]
    nav = '<a href="/blog">Blog</a><a href="/changelog">Changelog</a><a href="/careers">Careers</a><a href="/signup">Sign up</a>'
    age = {"alive": 12, "slow": 200, "stale": 900, "moved": 20, "blocked": 5, "gh": 30}.get(kind, 400)
    if kind == "dead": return {"error": "target_unreachable"}
    if kind == "blocked": return {"error": "bot_blocked"}
    if kind == "parked":
        return {"url": f"https://{host}{path}", "final_url": f"https://{host}{path}", "text": "<html><body>This domain is for sale. Buy this domain at Sedo.com</body></html>"}
    if kind == "absorbed" and path == "/":
        return {"url": f"https://{host}/", "final_url": "https://bigco.example/", "text": "<html><body><h1>BigCo - enterprise cloud</h1>" + "welcome " * 200 + "</body></html>"}
    if kind == "moved" and path == "/":
        return {"url": f"https://{host}/", "final_url": f"https://{brand}.io/", "title": brand, "text": f"<html><title>{brand}</title><body>{brand} (formerly {brand}labs). {nav}</body></html>"}
    if path in ("/", ""):
        extra = " We have shut down. Thank you." if kind == "shut" else ""
        return {"url": f"https://{host}/", "final_url": f"https://{host}/", "title": brand, "text": f"<html><title>{brand}</title><body><h1>{brand}</h1>{extra}{nav}{'<a href=https://github.com/org/'+brand+'>code</a>' if kind=='gh' else ''}</body></html>"}
    if path.startswith("/blog"):
        return {"url": f"https://{host}{path}", "final_url": f"https://{host}{path}", "text": f'<html><body><article><time datetime="{d(age)}">x</time> Post</article><time datetime="{d(age+60)}">old</time></body></html>'}
    if path.startswith("/changelog"):
        return {"error": "page_not_found", "status": 404}
    if path.startswith("/careers"):
        n = 3 if kind in ("alive", "moved") else 0
        links = "".join(f'<a href="/careers/role-{i}">Role {i}</a>' for i in range(n))
        return {"url": f"https://{host}{path}", "final_url": f"https://{host}{path}", "text": f"<html><body>{links}{'' if n else 'No open positions right now.'} " + "x" * 450 + "</body></html>"}
    if path.startswith("/signup"):
        form = '<form><input type="email"></form>' if kind in ("alive", "moved", "stale", "gh") else "Join the waitlist"
        return {"url": f"https://{host}{path}", "final_url": f"https://{host}{path}", "text": f"<html><body>{form}</body></html>"}
    if "github.com" in host:
        repo = path.strip("/").split("/")
        if path.endswith(".atom"):
            age = 900 if repo[1].startswith("arch") else 5
            return {"url": f"https://{host}{path}", "final_url": f"https://{host}{path}", "text": f"<feed><entry><updated>{d(age)}T10:00:00Z</updated></entry></feed>"}
        note = "This repository was archived by the owner on Mar 3, 2024. It is now read-only." if repo[1].startswith("arch") else "Code Issues Pull requests"
        return {"url": f"https://{host}{path}", "final_url": f"https://{host}{path}", "text": f"<html><body>{note} <a href='https://github.com/careers'>Careers</a></body></html>"}
    if path == "/sitemap.xml":
        if kind == "alive":
            return {"url": f"https://{host}{path}", "final_url": f"https://{host}{path}", "text": f"<urlset><url><lastmod>{T.isoformat()}</lastmod></url><url><lastmod>{T.isoformat()}</lastmod></url></urlset>"}
        return {"error": "page_not_found", "status": 404}
    return {"error": "page_not_found", "status": 404}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        n = int(self.headers.get("Content-Length", 0)); return json.loads(self.rfile.read(n) or b"{}")
    def do_POST(self):
        u = urlparse(self.path); b = self.body()
        if u.path == "/":
            res, errs = [], []
            for url in b["urls"][:10]:
                p = urlparse(url); r = page(p.netloc, p.path or "/")
                if "error" in r: errs.append({"url": url, **r}); continue
                if b.get("links"):
                    r["links"] = [m for m in re.findall(r"href=[\"']?([^\"' >]+)", r.get("text", ""))]
                    num = re.findall(r"-(\d+)\.", p.netloc)
                    if num and int(num[0]) % 2 == 0:
                        r["text"] = re.sub(r"<a [^>]*>.*?</a>", "", r["text"])
                res.append({"url": url, **r})
            return self.send(200, {"results": res, "errors": errs})
        if u.path == "/v1/datasets":
            ents = re.findall(r"^- (.+?) :: (.*)$", b["spec"]["description"], re.M)
            did = str(uuid.uuid4()); DS[did] = {"ents": ents, "polls": 0, "spec": b["spec"]}
            return self.send(202, {"id": did, "status": "populating", "run": {"id": "r", "status": "running"}})
        if u.path == "/v1/automation/run-async":
            rid = str(uuid.uuid4()); RUNS[rid] = {"host": urlparse(b["url"]).netloc, "polls": 0}
            return self.send(200, {"run_id": rid, "error": None})
        self.send(404, {})
    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/":
            return self.send(200, {"results": [{"title": "t", "snippet": "s", "url": "https://x.example/n", "date": d(40)}]})
        rm = re.match(r"/v1/runs/([\w-]+)$", u.path)
        if rm and rm.group(1) in RUNS:
            r = RUNS[rm.group(1)]; r["polls"] += 1; host = r["host"]
            if r["polls"] < 2: return self.send(200, {"run_id": rm.group(1), "status": "RUNNING"})
            return self.send(200, {"run_id": rm.group(1), "status": "COMPLETED", "result": {"operating": True, "status_note": "active", "latest_item_date": d(15),
                "latest_item_url": f"https://{host}/news/latest", "open_roles": 4, "careers_url": f"https://{host}/careers", "signup_available": True}})
        m = re.match(r"/v1/datasets/([\w-]+)(/rows)?$", u.path)
        if m and m.group(1) in DS:
            ds = DS[m.group(1)]
            if not m.group(2):
                ds["polls"] += 1; return self.send(200, {"id": m.group(1), "status": "ready" if ds["polls"] > 1 else "populating"})
            rows = []
            for name, url in ds["ents"]:
                host = urlparse(url).netloc; k = host.split(".")[0].split("-")[0]
                age = {"alive": 9, "slow": 150, "stale": 700, "gh": 20}.get(k, 400)
                dead = k in ("dead", "parked", "shut", "absorbed")
                rows.append({"_id": str(uuid.uuid4()), "data": {"entity": name, "still_operating": not dead, "status_note": "shut down" if dead else "active",
                    "latest_update_date": None if dead else d(age), "latest_social_date": None if dead else d(age + 3), "open_jobs": 0 if dead else 2,
                    "signup_open": not dead, "evidence_urls": f"update: https://{host}/blog\nsocial: https://x.com/{k}"}})
            if ds["ents"]: rows.append({"_id": "z", "data": {"entity": "Some Hallucinated Co"}})  # must be ignored
            return self.send(200, {"columns": [], "rows": rows, "truncated": False, "next_cursor": None})
        self.send(404, {})

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8799), H).serve_forever()
