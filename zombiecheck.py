#!/usr/bin/env python3
"""
zombiecheck - give it a spreadsheet of 500+ rows, get it back with a verdict on every row
(alive / slowing down / zombie / unclear), checked against LIVE pages via the TinyFish APIs.

  TinySet  (POST /v1/datasets)   web-wide gap filling in batches: social, updates, jobs, sign-up, status, with sources
  Fetch    (POST api.fetch)      live (ttl=0) homepage + blog/changelog/careers/sign-up/GitHub feeds; redirects, parked domains
  Search   (GET  api.search)     newest news / acquisition / shutdown mentions, resolves rows that have no URL
  Agent    (POST /v1/automation) optional: actually opens ambiguous sign-up pages (--agent-signup N)

Deterministic core, LLM/agent layer on the edge: the verdict is computed by plain code (decide()) from
dated, linkable evidence. TinySet claims are re-fetched live and only count in full if the page confirms them.
Stdlib only. Resumable: all state lives in <output>.zc/state.db.
"""
import argparse, csv, difflib, email.utils, hashlib, io, json, os, random, re, signal, sqlite3, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from html import unescape

FETCH_URL = os.environ.get("TINYFISH_FETCH_URL", "https://api.fetch.tinyfish.ai").rstrip("/")
SEARCH_URL = os.environ.get("TINYFISH_SEARCH_URL", "https://api.search.tinyfish.ai").rstrip("/")
AGENT_URL = os.environ.get("TINYFISH_AGENT_URL", "https://agent.tinyfish.ai").rstrip("/")
UA_PURPOSE = "Zombie check: decide whether this organisation or job post is still active"
ABORT = threading.Event()


class Fatal(Exception):
    pass


# ----------------------------------------------------------------------------- http / rate limits
class Limiter:
    def __init__(self, per_min):
        self.rate, self.next, self.lock = max(per_min, 1) / 60.0, 0.0, threading.Lock()

    def wait(self, n=1):
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next)
            self.next = start + n / self.rate
        if start > now:
            time.sleep(start - now)


def http(method, url, key, body=None, params=None, timeout=150, retries=5):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    headers = {"X-API-Key": key, "Content-Type": "application/json", "Accept": "application/json"}
    for attempt in range(retries):
        if ABORT.is_set():
            raise Fatal("aborted")
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"raw": raw[:300].decode("utf8", "replace")}
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                ra = e.headers.get("Retry-After", "")
                time.sleep(float(ra) if re.fullmatch(r"\d+(\.\d+)?", ra or "") else min(2 ** attempt * 2, 60))
                continue
            return e.code, payload
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt * 2, 30))
                continue
            return 0, {"error": str(e)}
    return 0, {"error": "retries exhausted"}


class TF:
    """Thin TinyFish client. Fetch/Search rate limits default to the documented personal-account limits."""

    def __init__(self, key, fetch_per_min=150, search_per_min=30):
        self.key = key
        self.fl, self.sl = Limiter(fetch_per_min), Limiter(search_per_min)
        self.stats = {"fetch_urls": 0, "search": 0, "agent": 0, "tinyset_rows": 0, "fetch_cache_hits": 0}
        self._lock = threading.Lock()
        self._cache = {}  # live results reused within one run only; never persisted, never older than the run

    def _fatal(self, st, js, what):
        if st == 401:
            raise Fatal(f"{what}: 401 invalid TINYFISH_API_KEY")
        if st == 402:
            raise Fatal(f"{what}: 402 free allowance used and wallet empty - top up, then re-run to resume")
        if st == 403:
            raise Fatal(f"{what}: 403 forbidden (Datasets need a personal key, not an organisation key)")

    def fetch(self, urls, fmt="html"):
        """urls<=10. Returns {requested_url: result_dict | {'error':code,'status':n}}. Always live (ttl=0)."""
        urls = list(dict.fromkeys(urls))[:10]
        out = {}
        with self._lock:
            for u in urls:
                if (u, fmt) in self._cache:
                    out[u] = self._cache[(u, fmt)]
                    self.stats["fetch_cache_hits"] += 1
        want = [u for u in urls if u not in out]
        if not want:
            return out
        got = self._fetch_live(want, fmt)
        with self._lock:
            for u, r in got.items():
                if r.get("error") not in ("http_0", "timeout", "proxy_error", "no_result"):
                    self._cache[(u, fmt)] = r
        out.update(got)
        return out

    def _fetch_live(self, urls, fmt):
        out = {}
        self.fl.wait(len(urls))
        st, js = http("POST", FETCH_URL, self.key, {"urls": urls, "format": fmt, "ttl": 0, "links": True,
                                                    "per_url_timeout_ms": 45000, "purpose": UA_PURPOSE})
        self._fatal(st, js, "fetch")
        with self._lock:
            self.stats["fetch_urls"] += len(urls)
        if st != 200:
            return {u: {"error": f"http_{st}"} for u in urls}
        leftovers = []
        for r in js.get("results", []):
            if r.get("url") in urls:
                out[r["url"]] = r
            else:
                leftovers.append(r)
        for e in js.get("errors", []):
            out[e.get("url")] = {"error": e.get("error", "error"), "status": e.get("status")}
        for u in urls:  # tolerate normalised URLs in the response
            if u not in out and leftovers:
                out[u] = leftovers.pop(0)
            out.setdefault(u, {"error": "no_result"})
        return out

    def fetch1(self, url, fmt="html"):
        return self.fetch([url], fmt).get(url, {"error": "no_result"})

    def search(self, query, **kw):
        self.sl.wait()
        params = {"query": query, **kw}
        st, js = http("GET", SEARCH_URL, self.key, params=params, timeout=30)
        self._fatal(st, js, "search")
        with self._lock:
            self.stats["search"] += 1
        return js.get("results", []) if st == 200 else []

    def agent_run(self, url, goal, steps=20, secs=120, poll=3.0):
        """Async run (/run-async) + poll GET /v1/runs/{id}. Returns the result only for a COMPLETED run, else None."""
        st, js = http("POST", AGENT_URL + "/v1/automation/run-async", self.key,
                      {"url": url, "goal": goal, "agent_config": {"max_duration_seconds": secs}},  # max_steps is beta-only (403 without it)
                      timeout=60, retries=3)
        self._fatal(st, js, "agent")
        run_id = js.get("run_id") if st == 200 else None
        if not run_id:
            return None
        with self._lock:
            self.stats["agent"] += 1
        deadline = time.time() + secs + 120
        while time.time() < deadline and not ABORT.is_set():
            st, js = http("GET", AGENT_URL + f"/v1/runs/{run_id}", self.key, timeout=30, retries=3)
            self._fatal(st, js, "agent")
            status = js.get("status") if st == 200 else None
            if status == "COMPLETED":
                return js.get("result")
            if status in ("FAILED", "CANCELLED"):
                return None
            time.sleep(poll)
        http("POST", AGENT_URL + f"/v1/runs/{run_id}/cancel", self.key, timeout=30, retries=1)
        return None

    def ds(self, method, path, body=None, params=None):
        st, js = http(method, AGENT_URL + path, self.key, body, params, timeout=90)
        return st, js


# ----------------------------------------------------------------------------- html / date helpers
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
ISO = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})(?:[T ]\d{2}:\d{2})?")
MDY = re.compile(MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})\b", re.I)
DMY = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+" + MON + r",?\s+(20\d{2})\b", re.I)
STRUCT = [re.compile(p, re.I) for p in (
    r"<time[^>]+datetime=[\"']([^\"']+)", r"article:published_time[\"'][^>]*content=[\"']([^\"']+)",
    r"content=[\"']([^\"']+)[\"'][^>]*article:published_time", r"\"datePublished\"\s*:\s*\"([^\"]+)\"",
    r"<(?:published|updated|pubDate|dc:date)>\s*([^<]+)<")]


def mkdate(y, m, d):
    try:
        return date(int(y), int(m), int(d))
    except (ValueError, TypeError):
        return None


def valid(d, today):
    return d if d and date(2005, 1, 1) <= d <= today + timedelta(days=1) else None


def find_dates(text, today):
    out = [mkdate(*m.groups()) for m in ISO.finditer(text)]
    out += [mkdate(m.group(3), MONTHS[m.group(1)[:3].lower()], m.group(2)) for m in MDY.finditer(text)]
    out += [mkdate(m.group(3), MONTHS[m.group(2)[:3].lower()], m.group(1)) for m in DMY.finditer(text)]
    return [d for d in (valid(x, today) for x in out) if d]


def parse_any(s, today):
    s = (s or "").strip()
    m = ISO.search(s)
    if m:
        return valid(mkdate(*m.groups()), today)
    try:
        return valid(email.utils.parsedate_to_datetime(s).date(), today)
    except Exception:
        ds = find_dates(s, today)
        return max(ds) if ds else None


def strip_tags(html):
    html = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html or "")
    return re.sub(r"\s+", " ", unescape(re.sub(r"(?s)<[^>]+>", " ", html))).strip()


def best_date(html, today):
    """Newest date on a page. Structured markup first (time/meta/JSON-LD/feed), visible text as fallback."""
    c = [parse_any(m.group(1), today) for p in STRUCT for m in p.finditer(html or "")]
    c = [d for d in c if d]
    if c:
        return max(c), "structured"
    ds = find_dates(strip_tags(html)[:40000], today)
    return (max(ds), "text") if ds else (None, None)


A_RE = re.compile(r"<a\b[^>]*?href=[\"']([^\"'#][^\"']*)[\"'][^>]*>(.*?)</a>", re.I | re.S)


def anchors(html, base):
    out = []
    for m in A_RE.finditer(html or ""):
        href = m.group(1).strip()
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        out.append((urllib.parse.urljoin(base, unescape(href)), strip_tags(m.group(2))[:80].lower()))
    return out


def reg_domain(host):
    host = (host or "").lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    p = host.split(".")
    if len(p) >= 3 and p[-2] in ("co", "com", "org", "net", "gov", "ac", "edu") and len(p[-1]) == 2:
        return ".".join(p[-3:])
    return ".".join(p[-2:]) if len(p) >= 2 else host


def norm_url(u):
    u = (u or "").strip()
    if not u or u.lower() in ("n/a", "na", "none", "-", "nan"):
        return ""
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    return u


def norm_name(s):
    s = re.sub(r"[^a-z0-9 ]", "", (s or "").lower())
    s = re.sub(r"\b(inc|ltd|llc|corp|co|gmbh|limited|labs|technologies|technology|the)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ----------------------------------------------------------------------------- signal detectors
PARK = re.compile(r"(domain (name )?(is |may be )?(for sale|available)|buy this domain|this domain (has expired|is parked|is for sale)|"
                  r"parked (free|domain|by|at)|sedo\.com|hugedomains|dan\.com|afternic|domain.{0,25}available for purchase|"
                  r"related searches|sponsored listings|account suspended|default web site page|it works!)", re.I)
PARK_HOSTS = ("sedo.com", "dan.com", "hugedomains.com", "afternic.com", "godaddy.com", "parkingcrew.net", "bodis.com",
              "namecheap.com", "above.com", "squadhelp.com", "undeveloped.com")
ARCHIVED = re.compile(r"(this repository (has been|was) archived|archived by the owner|is now read-only|this project is no longer maintained|deprecated[:.] (use|see|moved))", re.I)
SHUT = re.compile(r"(has (shut|closed|wound) down|have (shut|closed) down|no longer (available|operating|in business|supported|maintained|accepting)|"
                  r"(has been|was|is) (discontinued|sunset|decommissioned|archived)|we('| a)re (shutting down|sunsetting|closing)|"
                  r"service (has )?ended|ceased operations|this (project|product|service|repository) is (archived|deprecated|discontinued|no longer))", re.I)
def own_shutdown(head, toks):
    """True only if a shutdown phrase is about this site: first person / 'this product', or one of the row's own brand tokens just before it.
    'WorldTimeAPI has shut down' on timezone.io's page (a replacement service) is not a shutdown of timezone.io."""
    for m in SHUT.finditer(head):
        phrase = m.group(0).lower()
        before = re.split(r"(?<=[.!?])" + chr(92) + "s+|[<>" + chr(92) + "n]", head[max(0, m.start() - 120):m.start()].lower())[-1]  # same sentence only
        if re.match(r"we|this ", phrase) or re.search(r"\b(we|our)\s*$", before) or any(t in before for t in toks):
            return True
    return False


ACQ = re.compile(r"(has been acquired by|was acquired by|is now part of|acquired by [A-Z]|joined (forces )?with [A-Z]|now (part of|owned by))", re.I)
REBRAND = re.compile(r"(formerly( known as)?|previously known as|we('| ha)ve rebranded|rebranded (as|to)|now (called|known as))", re.I)
CLOSED_SIGNUP = re.compile(r"(wait ?list|invite[- ]only|sign-?ups? (are )?(currently )?(closed|paused|disabled)|registration (is )?(closed|disabled)|"
                           r"no longer accepting (new )?(sign|users|registr)|request (early )?access)", re.I)
NO_JOBS = re.compile(r"(no (current |open )?(openings|positions|vacancies|roles)|not (currently )?hiring|don.?t have any open|0 open)", re.I)
JOB_CLOSED = re.compile(r"(no longer (accepting|available)|position (has been |is )?(filled|closed)|(job|posting|role|vacancy) (is |has )?(closed|expired|been removed)|"
                        r"not accepting (new )?applications|applications? (are )?closed|this job (is )?no longer|job (posting )?has expired|expired)", re.I)
ATS = ("greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "bamboohr.com", "smartrecruiters.com", "recruitee.com",
       "teamtailor.com", "breezy.hr", "applytojob.com", "myworkdayjobs.com", "rippling.com", "jobs.", "careers.")
NOT_JOB = re.compile(r"/(benefits|culture|values|life|teams?|internships?|faq|about|perks|locations|diversity|students|how-we-hire|process|blog|privacy|terms)(/|$)")
KINDS = {
    "blog": (re.compile(r"/(blog|news|newsroom|press|updates|insights|articles|stories|journal)(/|$)"), re.compile(r"\b(blog|news|press|updates|insights)\b")),
    "changelog": (re.compile(r"/(changelog|release-?notes|releases|what-?s-?new|product-?updates|roadmap)(/|$)"), re.compile(r"(changelog|release notes|what.?s new)")),
    "careers": (re.compile(r"/(careers?|jobs?|join-?us|work-?with-?us|hiring|opportunities)(/|$)"), re.compile(r"\b(careers?|jobs|we.?re hiring|join us)\b")),
    "signup": (re.compile(r"/(sign-?up|register|get-?started|start|trial|waitlist|join|auth/register)(/|$)"), re.compile(r"(sign ?up|get started|register|create (an )?account|start (free|trial)|try (it )?free)")),
}


def page_links(r, base):
    """(url, anchor_text) from inline <a> tags PLUS Fetch's links[] array. Fetch returns semantic HTML with boilerplate
    removed, so nav/footer links (blog, careers, sign-up) often survive only in links[]."""
    html = r.get("text") if isinstance(r.get("text"), str) else ""
    out = anchors(html, base)
    seen = {u for u, _ in out}
    for u in r.get("links") or []:
        u = urllib.parse.urljoin(base, u if isinstance(u, str) else (u or {}).get("url", ""))
        if u.startswith("http") and u not in seen:
            seen.add(u)
            out.append((u, ""))
    for m in re.finditer(r"\[([^\]]{1,80})\]\((https?://[^)\s]+|/[^)\s]*)\)", html):  # markdown links
        u = urllib.parse.urljoin(base, m.group(2))
        if u not in seen:
            seen.add(u)
            out.append((u, m.group(1).lower()))
    return out


def classify_links(links, base):
    """pick at most one link per kind; prefer same registered domain, then known job boards."""
    home = reg_domain(urllib.parse.urlparse(base).netloc)
    picks = {}
    for u, text in links:
        p = urllib.parse.urlparse(u)
        for kind, (pat, txt) in KINDS.items():
            if kind in picks:
                continue
            same = reg_domain(p.netloc) == home
            ats = kind == "careers" and any(a in p.netloc.lower() for a in ATS)
            if (pat.search(p.path.lower() + "/") or txt.search(text)) and (same or ats or kind == "signup"):
                picks[kind] = u
    return picks


def count_jobs(r, base):
    links = set()
    for u, _ in page_links(r, base):
        p = urllib.parse.urlparse(u)
        path = p.path.rstrip("/").lower()
        depth = len([x for x in path.split("/") if x])
        if NOT_JOB.search(path + "/"):
            continue
        on_ats = any(a in p.netloc.lower() for a in ATS)
        if (on_ats and depth >= 2) or (re.search(r"/(jobs?|careers?|positions?|openings?|opportunities)/[^/]+", path) and depth >= 2):
            links.add(u.split("#")[0])
    return min(len(links), 99)


def eval_signup(r):
    if "error" in r:
        return "broken", f"sign-up page error: {r.get('error')}"
    html = r.get("text") or ""
    text = strip_tags(html)
    if CLOSED_SIGNUP.search(text):
        return "closed", "waitlist / invite-only / closed wording on sign-up page"
    if re.search(r"<input[^>]+type=[\"']?(email|password)", html, re.I) or \
            re.search(r"(sign ?up|continue|register|create account)[^<]{0,30}(with )?(google|github|email|apple)", text, re.I):
        return "works", "sign-up form / SSO present"
    return "unclear", "page loads but no sign-up form found"


# ----------------------------------------------------------------------------- per-row analysis (Fetch + Search)
def ev(signal, d, url, basis):
    return {"signal": signal, "date": d.isoformat() if d else "", "url": url, "basis": basis}


def brand_tokens(name, url):
    t = {w for w in re.split(r"[^a-z0-9]+", (name or "").lower()) if len(w) >= 4}
    dom = reg_domain(urllib.parse.urlparse(url).netloc).split(".")[0]
    t.add(dom)
    return {x for x in t if len(x) >= 3 or x == dom}


def resolve_url(tf, name):
    skip = ("linkedin.", "twitter.", "x.com", "facebook.", "wikipedia.", "crunchbase.", "youtube.", "instagram.", "reddit.", "github.com")
    for r in tf.search(f"{name} official website"):
        if not any(s in r.get("url", "") for s in skip):
            return r["url"]
    return ""


def analyze_site(tf, name, url, today, do_search=True):
    out = {"site_state": "unknown", "final_url": "", "flags": [], "evidence": [], "checked": ["site"],
           "update": None, "release": None, "news": None, "social": None, "jobs": None, "signup": None, "reason_bits": []}
    flags, E = out["flags"], out["evidence"]
    base = norm_url(url)
    if not base:
        flags.append("no_url_given")
        base = resolve_url(tf, name) if do_search else ""
        if not base:
            out["site_state"] = "unknown"
            out["reason_bits"].append("no website to check")
            return out
        flags.append("url_resolved_by_search")
    p0 = urllib.parse.urlparse(base)
    gh = None
    parts = [x for x in p0.path.split("/") if x]
    if p0.netloc.lower() in ("github.com", "www.github.com") and len(parts) >= 2:
        gh = (parts[0], parts[1])

    r = tf.fetch1(base)
    if "error" in r:
        code, st = r.get("error"), r.get("status")
        if code in ("bot_blocked", "login_required", "timeout", "proxy_error", "content_too_large") or (code == "target_http_error" and (st or 0) in (401, 403, 429)):
            out["site_state"] = "blocked"
            flags.append(f"fetch_{code}")
        else:
            alt = None
            if code in ("page_not_found", "target_http_error") and parts:
                alt = f"{p0.scheme}://{p0.netloc}/"
                flags.append("page_gone_root_tried")
            elif code in ("target_unreachable", "invalid_url"):
                h = p0.netloc[4:] if p0.netloc.startswith("www.") else "www." + p0.netloc
                alt = f"{p0.scheme}://{h}{p0.path or '/'}"
            r2 = tf.fetch1(alt) if alt else r
            if "error" not in r2:
                r, base = r2, alt
            else:
                c2 = r2.get("error")
                gone = c2 in ("target_unreachable", "invalid_url", "page_not_found") or (c2 == "target_http_error" and r2.get("status") in (404, 410))  # 403/451/429 etc. mean "refused us", not "gone"
                out["site_state"] = "dead" if gone else "blocked"
                flags.append(f"fetch_{c2}")
                if out["site_state"] == "dead":
                    out["reason_bits"].append(f"site unreachable ({c2}{' ' + str(r2.get('status')) if r2.get('status') else ''})")
                E.append(ev("site", None, base, f"live fetch failed: {c2}"))
    if "error" not in r:
        html = r.get("text") if isinstance(r.get("text"), str) else json.dumps(r.get("text"))
        final = r.get("final_url") or base
        out["final_url"] = final
        text = strip_tags(html)
        head = (r.get("title") or "") + " " + (r.get("description") or "") + " " + text[:2500]
        fh = urllib.parse.urlparse(final).netloc.lower()
        out["site_state"] = "live"
        E.append(ev("site", None, final, "live fetch ok"))
        if any(h in fh for h in PARK_HOSTS) and reg_domain(fh) != reg_domain(p0.netloc) or (PARK.search(text[:4000]) and len(text) < 3000):
            out["site_state"] = "parked"
            out["reason_bits"].append("domain is parked / for sale")
            flags.append("parked_domain")
        elif reg_domain(fh) != reg_domain(p0.netloc):
            toks = brand_tokens(name, base)
            tgt = reg_domain(fh).split(".")[0]
            sib = any(len(t) >= 4 and len(os.path.commonprefix([t, tgt])) >= 4 for t in toks)  # sonarcloud.io -> sonarsource.com
            if sib or any(t in head.lower() for t in toks):
                flags.append(f"moved_to:{reg_domain(fh)}")
                out["reason_bits"].append(f"moved to {reg_domain(fh)} (brand still present: rebrand/migration)")
            else:
                out["site_state"] = "absorbed"
                flags.append(f"redirects_to_unrelated:{reg_domain(fh)}")
                out["reason_bits"].append(f"redirects to unrelated {reg_domain(fh)} (acquired / domain reassigned)")
        if out["site_state"] == "live" and gh and ARCHIVED.search(text[:6000]):
            out["site_state"] = "archived"
            out["reason_bits"].append("GitHub repository is archived (read-only)")
            flags.append("github_archived")
            ad = find_dates(text[:6000], today)
            if ad:
                E.append(ev("archived", max(ad), final, "archive notice on repository page"))
        if out["site_state"] == "live":
            if own_shutdown(head, brand_tokens(name, base)):
                out["site_state"] = "shutdown"
                out["reason_bits"].append("site says it has shut down / been discontinued")
                flags.append("shutdown_notice")
            elif ACQ.search(head):
                flags.append("acquisition_notice")
                out["reason_bits"].append("homepage mentions an acquisition")
            if REBRAND.search(head):
                flags.append("rebrand_notice")
        if out["site_state"] in ("live",):
            links = page_links(r, final)
            urls, probed = {}, set()
            if not gh:  # a GitHub repo row: github.com's own careers/sign-up links are not the project's
                picks = classify_links(links, final)
                urls = {k: picks[k] for k in ("blog", "changelog", "careers", "signup") if k in picks}
                for k, path in (("blog", "/blog"), ("changelog", "/changelog"), ("careers", "/careers")):
                    if k not in urls:  # not linked (or stripped): probe the conventional path
                        urls[k] = urllib.parse.urljoin(final, path)
                        probed.add(k)
                urls["sitemap"] = urllib.parse.urljoin(final, "/sitemap.xml")
                urls["feed"] = urllib.parse.urljoin(final, "/feed")
                probed |= {"sitemap", "feed"}
            if not gh:
                for u, _ in links:
                    m = re.match(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/?$", u)
                    if m and m.group(1).lower() not in ("sponsors", "features", "orgs", "apps", "login", "topics"):
                        gh = (m.group(1), m.group(2))
                        break
            fetch_map = {k: v for k, v in urls.items()}
            if gh:
                fetch_map["gh_release"] = f"https://github.com/{gh[0]}/{gh[1]}/releases.atom"
                fetch_map["gh_commit"] = f"https://github.com/{gh[0]}/{gh[1]}/commits.atom"
            res = tf.fetch(list(fetch_map.values()))
            for kind, u in fetch_map.items():
                rr = res.get(u, {"error": "no_result"})
                out["checked"].append(kind)
                if "error" in rr and kind in probed:
                    continue  # a missing conventional path is not evidence of anything
                if kind in ("sitemap", "feed"):
                    body = rr.get("text") if isinstance(rr.get("text"), str) else json.dumps(rr.get("text"))
                    ds = [x for x in (parse_any(m.group(1), today) for m in re.finditer(r"<(?:lastmod|pubDate|updated|published)>\s*([^<]+)<", body or "", re.I)) if x]
                    if not ds:
                        ds = find_dates(strip_tags(body or "")[:60000], today)
                    if ds and not (kind == "sitemap" and len(set(ds)) == 1 and max(ds) >= today - timedelta(days=1)):
                        # sitemaps whose every lastmod == today are auto-generated: ignored
                        d = max(ds)
                        out["update"] = max(out["update"], d) if out["update"] else d
                        E.append(ev(kind, d, rr.get("final_url") or u, f"newest of {len(ds)} dated entries"))
                    continue
                if kind in ("blog", "changelog"):
                    if "error" in rr:
                        E.append(ev(kind, None, u, f"page error: {rr.get('error')}"))
                        continue
                    d, how = best_date(rr.get("text") or "", today)
                    pd = parse_any(rr.get("published_date") or "", today) if rr.get("published_date") else None
                    d = max([x for x in (d, pd) if x], default=None)
                    key = "update" if kind == "blog" else "release"
                    if d:
                        out[key] = max(out[key], d) if out[key] else d
                    E.append(ev(kind, d, rr.get("final_url") or u, f"newest date on page ({how or 'none found'})"))
                elif kind in ("gh_release", "gh_commit"):
                    if "error" in rr:
                        continue
                    d, _ = best_date(rr.get("text") or "", today)
                    if d:
                        out["release"] = max(out["release"], d) if out["release"] else d
                    E.append(ev("release" if kind == "gh_release" else "commit", d, u, "GitHub Atom feed, newest entry"))
                elif kind == "careers":
                    if "error" in rr:
                        E.append(ev("jobs", None, u, f"careers page error: {rr.get('error')}"))
                        continue
                    chtml = rr.get("text") or ""
                    n = count_jobs(rr, rr.get("final_url") or u)
                    if n == 0 and not NO_JOBS.search(strip_tags(chtml)) and len(strip_tags(chtml)) < 400:
                        n = None
                    out["jobs"] = n
                    jd, _ = best_date(chtml, today) if n else (None, None)
                    if jd:
                        out["update"] = max(out["update"], jd) if out["update"] else jd
                    E.append(ev("jobs", jd, rr.get("final_url") or u, f"{n} job links" if n is not None else "careers page too thin to count"))
                elif kind == "signup":
                    s, why = eval_signup(rr)
                    out["signup"] = s
                    out["signup_url"] = rr.get("final_url") or u
                    E.append(ev("signup", None, out["signup_url"], f"{s}: {why}"))
            if not gh and "gh_release" not in fetch_map:
                pass
    if do_search and out["site_state"] not in ("dead",):
        q = f'"{name}"'
        dom = reg_domain(urllib.parse.urlparse(base).netloc)
        res = tf.search(q + " " + dom, domain_type="news", recency_minutes=525600 * 2)
        out["checked"].append("news")
        nd = None
        for x in res[:10]:
            d = parse_any(x.get("date") or "", today)
            if d and (any(t in (x.get("title", "") + x.get("snippet", "")).lower() for t in brand_tokens(name, base)) or dom in x.get("url", "")):
                if not nd or d > nd[0]:
                    nd = (d, x.get("url"))
            blob = (x.get("title", "") + " " + x.get("snippet", ""))
            if re.search(r"(acquired by|shuts? down|shutting down|ceas(es|ed) operations|winds? down)", blob, re.I) and name.lower().split()[0] in blob.lower():
                flags.append("news_mentions_acquisition_or_shutdown")
                E.append(ev("news", parse_any(x.get("date") or "", today), x.get("url", ""), "headline mentions acquisition/shutdown: " + blob[:90]))
        if nd:
            out["news"] = nd[0]
            E.append(ev("news", nd[0], nd[1], "newest dated news result"))
        soc = tf.search(f'"{name}" {dom}', include_domains="x.com,twitter.com,linkedin.com,bsky.app,youtube.com,mastodon.social,instagram.com")
        out["checked"].append("social_search")
        sd = None
        toks = brand_tokens(name, base)
        for x in soc[:10]:
            d = parse_any(x.get("date") or "", today)
            blob = (x.get("title", "") + " " + x.get("snippet", "") + " " + x.get("url", "")).lower()
            if d and any(t in blob for t in toks) and (not sd or d > sd[0]):
                sd = (d, x.get("url"))
        if sd:
            out["social"] = sd[0]
            E.append(ev("social", sd[0], sd[1], "newest dated social search result"))
        elif soc:
            E.append(ev("social", None, soc[0].get("url", ""), "profile found, no date exposed"))
    if E and E[0]["signal"] == "site" and out["site_state"] != "live":
        E[0]["basis"] = f"live fetch ok, but classified {out['site_state']}"
    # serialise dates
    for k in ("update", "release", "news", "social"):
        out[k] = out[k].isoformat() if out[k] else None
    return out


def analyze_job(tf, name, url, today):
    """Ghost-job mode: every row is a job post URL."""
    out = {"site_state": "unknown", "final_url": "", "flags": [], "evidence": [], "checked": ["job_page"], "job_state": None,
           "update": None, "release": None, "news": None, "social": None, "jobs": None, "signup": None, "reason_bits": []}
    base = norm_url(url)
    if not base:
        out["reason_bits"].append("no job URL")
        return out
    r = tf.fetch1(base)
    if "error" in r:
        code, st = r.get("error"), r.get("status")
        out["job_state"] = "gone" if code == "page_not_found" or (code == "target_http_error" and st in (404, 410)) else "unknown"
        out["site_state"] = "live" if out["job_state"] == "gone" else "blocked"
        out["evidence"].append(ev("job_page", None, base, f"live fetch: {code} {st or ''}".strip()))
        out["reason_bits"].append("job page returns 404/410" if out["job_state"] == "gone" else f"could not load job page ({code})")
        return out
    html, final = r.get("text") or "", r.get("final_url") or base
    text = strip_tags(html)
    out["site_state"], out["final_url"] = "live", final
    pu, fu = urllib.parse.urlparse(base), urllib.parse.urlparse(final)
    redirected_to_index = fu.path.rstrip("/") != pu.path.rstrip("/") and len([x for x in fu.path.split("/") if x]) < len([x for x in pu.path.split("/") if x])
    closed = bool(JOB_CLOSED.search(text[:6000]))
    apply_ok = bool(re.search(r"(apply now|apply for this|submit application|apply to this|easy apply)", text, re.I) or re.search(r"<form[^>]+(apply|application)", html, re.I))
    posted = None
    m = re.search(r"\"datePosted\"\s*:\s*\"([^\"]+)\"", html)
    if m:
        posted = parse_any(m.group(1), today)
    if not posted:
        posted, _ = best_date(html, today)
    vt = re.search(r"\"validThrough\"\s*:\s*\"([^\"]+)\"", html)
    expired = False
    if vt:
        vd = mkdate(*vt.group(1)[:10].split("-")) if re.match(r"\d{4}-\d{2}-\d{2}", vt.group(1)) else None
        expired = bool(vd and vd < today)
    out["evidence"].append(ev("job_page", posted, final, f"posted date; apply={'yes' if apply_ok else 'no'}; closed_wording={closed}; validThrough_expired={expired}"))
    out["update"] = posted.isoformat() if posted else None
    out["job_state"] = "closed" if (closed or expired) else ("redirected_to_index" if redirected_to_index else ("open" if apply_ok else "unclear"))
    if redirected_to_index:
        out["flags"].append("redirects_to_careers_index")
    if expired:
        out["flags"].append("validThrough_expired")
    out["signup"] = "works" if apply_ok else ("closed" if closed else "unclear")
    # company side: does its careers page still list roles / is the company alive?
    root = f"{fu.scheme}://{fu.netloc}/"
    if reg_domain(fu.netloc) not in ("greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "linkedin.com", "indeed.com", "myworkdayjobs.com"):
        co = analyze_site(tf, name or fu.netloc, root, today, do_search=False)
        out["news"] = co["update"] or co["release"]
        out["evidence"] += [e for e in co["evidence"] if e["signal"] in ("blog", "changelog", "release", "commit")]
        out["jobs"] = co["jobs"]
        out["checked"] += co["checked"]
        if co["site_state"] in ("dead", "parked", "absorbed", "shutdown", "archived"):
            out["flags"].append("company_site_" + co["site_state"])
    return out


# ----------------------------------------------------------------------------- Agent escalation
AGENT_GOAL = """You are checking whether "{name}" is still an active organisation/product. Browse like a normal visitor.
NEVER sign up, log in, submit a form or accept anything. Steps: 1) open the site; 2) open its blog/news/changelog/release-notes
page if one exists and read the date of the NEWEST item; 3) open its careers/jobs page if one exists and count open roles;
4) check whether a visitor could begin sign-up/registration (form or button visible, not waitlist-only).
Report only what you saw. Use null when you could not see it.
Return JSON: {{"operating": true|false|null, "status_note": "active | acquired by X | rebranded to X | shut down | parked | unknown",
"latest_item_date": "YYYY-MM-DD"|null, "latest_item_url": url|null, "open_roles": int|null, "careers_url": url|null,
"signup_available": true|false|null, "signup_url": url|null}}"""


def agent_candidates(det, items, today):
    """Rows the cheap path could not settle: bot-blocked/JS-only sites, or live sites with no dated activity at all."""
    out = []
    for i, s in det.items():
        if s.get("site_state") == "blocked" and (s.get("final_url") or norm_url(items[i][1])):
            out.append((0, i))
        elif s.get("site_state") == "live" and not any(s.get(k) for k in ("update", "release", "news", "social")):
            out.append((1, i))
    return [i for _, i in sorted(out)]


def agent_probe(tf, name, url):
    res = tf.agent_run(url, AGENT_GOAL.format(name=name.replace('"', "'")), steps=30, secs=180)
    if isinstance(res, str):
        m = re.search(r"\{.*\}", res, re.S)
        try:
            res = json.loads(m.group(0)) if m else None
        except Exception:
            res = None
    if isinstance(res, dict) and isinstance(res.get("result"), dict):
        res = res["result"]
    return res if isinstance(res, dict) else None


def apply_agent(s, res, today):
    """Merge an Agent browser report into a row's signals. Agent facts fill gaps; they do not overwrite live Fetch findings."""
    if not res:
        s.setdefault("flags", []).append("agent_no_result")
        return
    E, flags = s.setdefault("evidence", []), s.setdefault("flags", [])
    note = str(res.get("status_note") or "")
    if s.get("site_state") == "blocked" and res.get("operating") is not None:
        s["site_state"] = "live"
        flags.append("reached_via_agent")
        E.append(ev("site_agent", None, s.get("final_url") or "", f"agent browser loaded the site: {note or 'ok'}"))
    d = parse_any(str(res.get("latest_item_date") or ""), today)
    url = res.get("latest_item_url") or ""
    if d and str(url).startswith("http"):
        s["agent_update"] = d.isoformat()
        E.append(ev("update_agent", d, url, "agent opened the page and read the newest item date"))
    if res.get("operating") is False and re.search(r"(shut|acquired|parked|closed|discontinued)", note, re.I):
        s["site_state"] = "shutdown"
        s.setdefault("reason_bits", []).append(f"agent browser reports: {note}")
        E.append(ev("status_agent", None, s.get("final_url") or url, f"agent: {note}"))
    if s.get("jobs") is None and isinstance(res.get("open_roles"), (int, float)) and str(res.get("careers_url") or "").startswith("http"):
        s["jobs"] = int(res["open_roles"])
        E.append(ev("jobs_agent", None, res["careers_url"], f"agent counted {int(res['open_roles'])} open roles"))
    if s.get("signup") in (None, "unclear") and res.get("signup_available") is not None:
        s["signup"] = "works" if res["signup_available"] else "closed"
        E.append(ev("signup_agent", None, res.get("signup_url") or s.get("final_url") or "", "agent: sign-up " + ("visible" if res["signup_available"] else "not available")))
    s.setdefault("checked", []).append("agent")


# ----------------------------------------------------------------------------- verdict (pure function, no I/O)
def days_since(iso, today):
    return (today - date.fromisoformat(iso)).days if iso else None


def decide(sig, ts, today, mode="companies"):
    """sig: analyze_*() output; ts: {'update':(iso,status),'social':(iso,status),'jobs':n,'signup':bool,'operating':bool,'note':str} or None.
    Returns verdict, score, confidence, reason, last_date, last_signal."""
    ts = ts or {}
    bits = list(sig.get("reason_bits", []))
    cands = []  # (iso, signal, weight)
    for k in ("update", "release", "news"):
        if sig.get(k):
            cands.append((sig[k], k, 1.0))
    if sig.get("agent_update"):  # a real browser run opened the page and read the date
        cands.append((sig["agent_update"], "agent_update", 0.9))
    t_upd = ts.get("update")
    if t_upd and t_upd[0]:
        cands.append((t_upd[0], "tinyset_update", 1.0 if t_upd[1] == "verified" else 0.6 if t_upd[1] == "page_live" else 0.0))
    own = [c for c in cands if not c[1].startswith("tinyset")]
    # a TinySet date our own live fetch could not confirm never overrides a date we found ourselves
    cands = [c for c in cands if c[2] > 0 and (not own or c[1] not in ("tinyset_update",) or c[2] == 1.0)]
    best = max(cands, key=lambda c: (c[0], c[2]), default=None)
    last_iso, last_sig = (best[0], best[1]) if best else ("", "")
    soc_iso, soc_w = sig.get("social"), 1.0
    if ts.get("social") and ts["social"][0] and not soc_iso:
        soc_iso, soc_w = ts["social"][0], (1.0 if ts["social"][1] == "verified" else 0.5)
    # headline "last activity" = newest date we could check ourselves, and its source always travels with it
    if soc_iso and soc_w == 1.0 and (not last_iso or soc_iso > last_iso):
        overall, last_sig = soc_iso, "social"
    else:
        overall = last_iso

    # ---- hard gates
    state = sig.get("site_state")
    if mode == "jobs":
        js = sig.get("job_state")
        age = days_since(sig.get("update"), today)
        if js in ("gone", "closed"):
            return ("zombie", 0, "high", "job post is gone/closed: " + "; ".join(bits or [js]), sig.get("update") or "", "job_page")
        if js == "redirected_to_index":
            return ("zombie", 10, "medium", "job URL redirects to the generic careers index (role removed)", sig.get("update") or "", "job_page")
        pts, den = 0, 0
        if age is not None:
            den += 60; pts += 60 if age <= 30 else 45 if age <= 60 else 25 if age <= 90 else 8 if age <= 150 else 0
        den += 25; pts += 25 if js == "open" else 8 if js == "unclear" else 0
        if sig.get("jobs") is not None:
            den += 15; pts += 15 if sig["jobs"] > 0 else 0
        if any(f.startswith("company_site_") for f in sig.get("flags", [])):
            pts = min(pts, 20)
            bits.append("company website itself looks dead")
        score = round(100 * pts / den) if den else 0
        v = "alive" if score >= 65 else "slowing down" if score >= 35 else "zombie"
        conf = "high" if age is not None and js in ("open", "unclear") else "low"
        bits.append(f"posted {age}d ago" if age is not None else "no posting date on page")
        return (v, score, conf, "; ".join(bits), sig.get("update") or "", "job_page")

    if state in ("dead", "parked", "absorbed", "shutdown", "archived"):
        # a TinySet note saying "rebranded to X" with a live verified update still gets a chance at not being a zombie
        return ("zombie", 0, "high" if state != "dead" else "medium", "; ".join(bits) or state, overall, last_sig if overall else "")
    if ts.get("operating") is False and ts.get("note") and re.search(r"(shut|acquired|parked|closed)", ts["note"], re.I) and not (last_iso and days_since(last_iso, today) <= 120):
        bits.append(f"TinySet reports: {ts['note']}")
        return ("zombie", 5, "medium", "; ".join(bits), overall, last_sig)

    # ---- weighted score over applicable signals
    pts = den = 0.0
    known = 0
    # activity (45)
    den += 45
    a = days_since(last_iso, today)
    if a is not None:
        pts += 45 * best[2] * (1 if a <= 60 else .85 if a <= 120 else .62 if a <= 180 else .27 if a <= 365 else 0)
        known += 1
        bits.append(f"latest update {last_iso} via {last_sig} ({a}d ago)")
    elif state == "live":
        bits.append("no dated update found on checked pages")
        den -= 45  # unknown, not zero: a live site with undated pages is not evidence of death
    # social (15)
    s = days_since(soc_iso, today)
    if s is not None:
        den += 15; known += 1
        pts += 15 * soc_w * (1 if s <= 90 else .6 if s <= 180 else .2 if s <= 365 else 0)
        bits.append(f"social {soc_iso} ({s}d ago{'' if soc_w == 1 else ', not independently verified'})")
    # jobs (15)
    n = sig.get("jobs")  # our own live count wins; TinySet only fills a gap
    if n is None and ts.get("jobs") is not None:
        n = ts["jobs"]
    if n is not None:
        den += 15; known += 1
        pts += 15 if n > 0 else 0
        bits.append(f"{n} open jobs" if n else "no open jobs")
    # sign-up (15)
    su = sig.get("signup")
    if su is None and ts.get("signup") is not None:
        su = "works" if ts["signup"] else "closed"
    if su is not None:
        den += 15; known += 1
        pts += {"works": 15, "unclear": 7, "closed": 4, "broken": 0}.get(su, 0)
        bits.append(f"sign-up {su}")
    # site (10)
    if state == "live":
        den += 10; pts += 10; known += 1
    elif state == "blocked":
        bits.append("site blocked automated fetch (unverified)")
    score = round(100 * pts / den) if den else 0
    ages = [x for x in (a, s if soc_w == 1.0 else None) if x is not None]  # newest dated thing we verified ourselves
    newest = min(ages) if ages else None
    NO_DATES = "no dated activity found; not evidence of closure"
    rest = [b_ for b_ in bits if b_ != "no dated update found on checked pages"]
    if newest is None and not (n and n > 0) and state in ("live", "blocked"):
        # nothing dated anywhere: absence of dates is not evidence of closure
        return ("unclear", min(score, 45), "low", "; ".join([NO_DATES] + rest), overall, last_sig)
    if newest is not None and newest > 730 and not (n and n > 0):
        score = min(score, 25)
        bits.append(f"newest dated activity is {newest} days old (over 730)")
    v = "alive" if score >= 60 else "slowing down" if score >= 30 else "zombie"
    if v == "zombie" and not (newest is not None and newest > 730):
        # not a hard gate (those returned above) and no dated signal older than 730 days: cannot call it a zombie
        if newest is None:
            return ("unclear", min(score, 45), "low", "; ".join([NO_DATES] + rest), overall, last_sig)
        v = "slowing down"
        bits.append("newest dated activity is under 730 days old")
    if v == "zombie" and any(f.startswith("moved_to:") for f in sig.get("flags", [])):
        v = "unclear"  # same brand lives on at a new domain; the old domain's stale dates prove nothing
        bits.append("brand continues at its new domain")
    recent = (a is not None and a <= 120) or (s is not None and s <= 120)
    if v == "alive" and not recent and not (n and n > 0):
        v = "slowing down"  # a site that loads and takes sign-ups but has published nothing in 4 months is not "alive"
        bits.append("no dated activity in 120 days")
    if v == "zombie" and any(f.startswith("moved_to:") for f in sig.get("flags", [])):
        v = "unclear"  # same brand lives on at a new domain; the old domain's stale dates prove nothing
        bits.append("brand continues at its new domain")
    if "acquisition_notice" in sig.get("flags", []) and v == "alive" and (a is None or a > 120):
        v = "slowing down"
    conf = "high" if known >= 4 else "medium" if known == 3 else "low"
    if v in ("slowing down", "unclear") and a is None:
        conf = "low"
    if state == "blocked":
        conf = "low"
    return (v, score, conf, "; ".join(bits), overall, last_sig)


# ----------------------------------------------------------------------------- state (resume)
class DB:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.c = sqlite3.connect(path, check_same_thread=False, timeout=60)
        self.l = threading.Lock()
        with self.l:
            self.c.executescript("""CREATE TABLE IF NOT EXISTS rows(idx INTEGER PRIMARY KEY, det TEXT, ver TEXT);
            CREATE TABLE IF NOT EXISTS batches(no INTEGER PRIMARY KEY, idxs TEXT, dataset_id TEXT, status TEXT, data TEXT, note TEXT);
            CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);""")
            self.c.commit()

    def q(self, sql, args=(), commit=False):
        with self.l:
            cur = self.c.execute(sql, args)
            if commit:
                self.c.commit()
            return cur.fetchall()

    def meta(self, k, v=None):
        if v is None:
            r = self.q("SELECT v FROM meta WHERE k=?", (k,))
            return r[0][0] if r else None
        self.q("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, v), True)

    def put(self, col, idx, obj):
        self.q(f"INSERT OR IGNORE INTO rows(idx) VALUES(?)", (idx,), True)
        self.q(f"UPDATE rows SET {col}=? WHERE idx=?", (json.dumps(obj), idx), True)

    def get_all(self, col):
        return {i: json.loads(v) for i, v in self.q(f"SELECT idx,{col} FROM rows WHERE {col} IS NOT NULL")}


# ----------------------------------------------------------------------------- TinySet stage
TS_COLS = [
    ("entity", "string", True, "Exactly the entity name as written in the list in the dataset description.", None),
    ("still_operating", "boolean", False, "true if the organisation/product is visibly operating today (live site, recent activity). false if shut down, acquired and sunset, or domain parked/for sale.", None),
    ("status_note", "string", False, "Status in a few words.", "One of: active | acquired by <name> | rebranded to <name> | shut down | domain parked | unknown"),
    ("latest_update_date", "date", False, "Date of the newest dated item on the organisation's OWN blog, changelog, release notes, press page or GitHub. Leave empty if not confirmed on a page you opened.", None),
    ("latest_social_date", "date", False, "Date of the newest post on its official X/Twitter, LinkedIn, Bluesky, Mastodon or YouTube account. Leave empty if not confirmed.", None),
    ("open_jobs", "number", False, "Number of job listings currently open on its careers page or job board. 0 if the page shows none.", None),
    ("signup_open", "boolean", False, "true if a visitor can start sign-up/registration right now; false if it is closed, waitlist-only or broken. Leave empty if the product has no sign-up.", None),
    ("evidence_urls", "string", False, "One line per signal formatted 'signal: URL' with signal in update|social|jobs|signup|status. Only pages that were actually opened.", None),
]


TS_DESC_MAX = 1900  # TinySet rejects long descriptions (2049 chars -> INVALID_INPUT; 400 ok); stay under 2000
TS_PREAMBLE = ("One row per entity in the FIXED list below; entity = the exact name before '::'. "
               "Do not add or substitute entities. Check live pages for whether each is still active. Leave cells empty rather than guess.\n")


def ts_line(n, u):
    host = re.sub(r"^https?://(www\.)?", "", u or "").split("/")[0] if u else ""
    return f"- {n[:50]} :: {host or '(no site)'}"


def ts_spec(batch):
    desc = TS_PREAMBLE + "\n".join(ts_line(n, u) for n, u in batch)
    assert len(desc) <= TS_DESC_MAX + 100, f"TinySet description too long ({len(desc)}); batch by budget via new_batches(items=...)"
    cols = []
    for name, typ, pk, hint, fmt in TS_COLS:
        c = {"name": name, "label": name.replace("_", " ").title(), "type": typ, "is_primary_key": pk, "retrieval_hint": hint}
        if fmt:
            c["format"] = fmt
        cols.append(c)
    return {"name": "zombiecheck batch", "description": desc, "columns": cols}


TS_COST_PER_ROW = 0.10


def ts_select(det, items, today, budget):
    """Rows phase 1 could not settle, best candidates first, capped at `budget`.
    Priority: site blocked, live with no dated activity, confidence low, confidence medium.
    Returns (chosen, skip) where skip = {idx: 'skipped_resolved' | 'skipped_budget'} for every other row."""
    ranked = []
    for i, s in det.items():
        if s.get("site_state") == "blocked":
            p = 0
        elif s.get("site_state") == "live" and not any(s.get(k) for k in ("update", "release", "news", "social")):
            p = 1
        else:
            conf = decide(s, None, today)[2]
            p = {"low": 2, "medium": 3}.get(conf)
        if p is not None:
            ranked.append((p, i))
    ranked.sort()
    order = [i for _, i in ranked]
    chosen = order[:max(0, budget)]
    cset = set(chosen)
    skip = {i: ("skipped_budget" if i in order else "skipped_resolved") for i in det if i not in cset}
    return chosen, skip


TS_VALIDATE_SEED = 20261115


def ts_validate_sample(skip, n):
    """Seeded random sample of rows phase 1 resolved with high confidence; same input -> same rows on every re-run."""
    pool = sorted(i for i, v in skip.items() if v == "skipped_resolved")
    return sorted(random.Random(TS_VALIDATE_SEED).sample(pool, min(max(0, n), len(pool))))


def verdict_side(v):
    return {"alive": "A", "zombie": "Z"}.get(v)  # 'slowing down' (None) agrees with either side


def ts_crosscheck(pairs):
    """pairs: [(fetch_search_verdict, tinyset_verdict_or_None)] for the sampled rows.
    -> (agree, answered, sampled). A row with no TinySet answer counts in `sampled` but never as agreeing."""
    agree = answered = 0
    for fs, tsv in pairs:
        if tsv is None:
            continue
        answered += 1
        a, b = verdict_side(fs), verdict_side(tsv)
        if a is None or b is None or a == b:
            agree += 1
    return agree, answered, len(pairs)


def ts_dict(ts_claims, vv):
    """TinySet claims + our live re-verification -> the `ts` argument of decide()."""
    return {"update": vv.get("update"), "social": vv.get("social"),
            "operating": ts_claims.get("still_operating"), "note": str(ts_claims.get("status_note") or ""),
            "jobs": ts_claims.get("open_jobs") if isinstance(ts_claims.get("open_jobs"), (int, float)) else None,
            "signup": ts_claims.get("signup_open")}


def ts_confirm(n_rows, assume_yes, stream_in=None, n_validate=0):
    """Print the row count and estimated cost; ask unless --yes. Non-interactive without --yes means no."""
    extra = f" (including {n_validate} cross-check sample rows)" if n_validate else ""
    print(f"TinySet: {n_rows} rows{extra} x ${TS_COST_PER_ROW:.2f} = estimated ${n_rows * TS_COST_PER_ROW:.2f}", file=sys.stderr)
    if assume_yes:
        return True
    stream_in = stream_in or sys.stdin
    if not stream_in.isatty():
        print("TinySet skipped: confirmation needed. Re-run with --yes to approve this spend.", file=sys.stderr)
        return False
    print("Proceed with TinySet? [y/N] ", end="", file=sys.stderr, flush=True)
    return stream_in.readline().strip().lower() in ("y", "yes")


def new_batches(db, idxs, size, items=None):
    """Batch every row index not already in some batch, so a later run with a different --limit (or after a partial run) covers all rows."""
    seen = set()
    for (j,) in db.q("SELECT idxs FROM batches"):
        seen.update(json.loads(j))
    todo = [i for i in idxs if i not in seen]
    mx = db.q("SELECT MAX(no) FROM batches")[0][0]
    nxt = 0 if mx is None else mx + 1
    groups, cur, used = [], [], len(TS_PREAMBLE)
    for i in todo:  # close a batch at `size` rows or when the TinySet description would exceed its length limit
        cost = len(ts_line(*items[i])) + 1 if items else 0
        if cur and (len(cur) >= size or used + cost > TS_DESC_MAX):
            groups.append(cur); cur, used = [], len(TS_PREAMBLE)
        cur.append(i); used += cost
    if cur:
        groups.append(cur)
    for g in groups:
        db.q("INSERT INTO batches(no,idxs,status) VALUES(?,?,?)", (nxt, json.dumps(g), "new"), True)
        nxt += 1


def run_tinyset(tf, db, items, args, idxs=None):
    """items: {idx:(name,url)}. Creates batches (<=250 rows, default 30), keeps <=3 runs in flight, resumes by dataset id."""
    new_batches(db, sorted(items if idxs is None else idxs), args.ts_batch, items)
    ts_stop = threading.Event()

    def work(no):
        _, idxs_j, ds_id, status, data_j, note = db.q("SELECT * FROM batches WHERE no=?", (no,))[0]
        idxs = json.loads(idxs_j)
        if status == "collected" or status == "no_credits" or ts_stop.is_set():
            return
        try:
            if not ds_id:
                spec = ts_spec([items[i] for i in idxs])
                st, js = tf.ds("POST", "/v1/datasets", {"spec": spec, "target_rows": len(idxs), "populate": True})
                if st == 403:
                    print("TinySet needs a personal API key, not an org key", file=sys.stderr)
                    db.q("UPDATE batches SET status='failed',note=? WHERE no=?", ("create http 403: personal API key needed", no), True)
                    ts_stop.set()
                    return
                if st == 402:
                    db.q("UPDATE batches SET status='no_credits',note=? WHERE no=?", ("TinySet: insufficient credits", no), True)
                    return
                if st not in (200, 201, 202):
                    db.q("UPDATE batches SET status='failed',note=? WHERE no=?", (f"create http {st}: {str(js)[:200]}", no), True)
                    return
                ds_id = js["id"]
                db.q("UPDATE batches SET dataset_id=?,status='populating' WHERE no=?", (ds_id, no), True)
            deadline = time.time() + args.ts_timeout
            final = None
            while time.time() < deadline and not ABORT.is_set():
                st, js = tf.ds("GET", f"/v1/datasets/{ds_id}")
                final = js.get("status") if st == 200 else None
                if final in ("ready", "failed", "cancelled"):
                    break
                time.sleep(args.ts_poll)
            rows, cursor = [], None
            while True:
                st, js = tf.ds("GET", f"/v1/datasets/{ds_id}/rows", params={"limit": 2000, **({"after": cursor} if cursor else {})})
                if st != 200:
                    break
                rows += [r.get("data", {}) for r in js.get("rows", [])]
                cursor = js.get("next_cursor")
                if not js.get("truncated") or not cursor:
                    break
            tf.stats["tinyset_rows"] += len(rows)
            st_final = "collected" if final in ("ready", "failed", "cancelled") else "partial"
            db.q("UPDATE batches SET status=?,data=?,note=? WHERE no=?", (st_final, json.dumps(rows), f"dataset {final}", no), True)
        except Fatal:
            raise
        except Exception as e:  # noqa
            db.q("UPDATE batches SET status='failed',note=? WHERE no=?", (f"{type(e).__name__}: {e}", no), True)

    nos = [r[0] for r in db.q("SELECT no FROM batches WHERE status NOT IN ('collected','no_credits')")]
    with ThreadPoolExecutor(max_workers=max(1, min(args.ts_concurrency, 3))) as ex:
        for f in as_completed([ex.submit(work, n) for n in nos]):
            try:
                f.result()
            except Fatal as e:
                print("TinySet:", e, file=sys.stderr)
                ABORT.set()


def ts_collect(db, items):
    """-> {idx: parsed TinySet claims} by matching entity names to input rows within each batch."""
    out = {}
    for no, idxs_j, data_j in db.q("SELECT no,idxs,data FROM batches WHERE data IS NOT NULL"):
        idxs = json.loads(idxs_j)
        names = {i: norm_name(items[i][0]) for i in idxs}
        for row in json.loads(data_j):
            key = norm_name(str(row.get("entity", "")))
            hit = next((i for i, n in names.items() if n == key), None)
            if hit is None:
                m = difflib.get_close_matches(key, list(names.values()), 1, 0.9)
                hit = next((i for i, n in names.items() if m and n == m[0]), None)
            if hit is not None and hit not in out:
                out[hit] = row
    return out


def parse_evidence_urls(s):
    d = {}
    for m in re.finditer(r"(\w+)\s*[:\-]\s*(https?://[^\s,;)]+)", s or ""):
        d.setdefault(m.group(1).lower(), m.group(2))
    return d


def verify_claims(tf, claims, today):
    """Re-fetch the page TinySet cites for each date claim, live. -> {'update':(iso,status),'social':...}"""
    out, ev_out = {}, []
    ev_urls = parse_evidence_urls(claims.get("evidence_urls"))
    for field, sig_name in (("latest_update_date", "update"), ("latest_social_date", "social")):
        iso = str(claims.get(field) or "")[:10]
        d = parse_any(iso, today) if iso else None
        if not d:
            continue
        url = ev_urls.get(sig_name) or (ev_urls.get("status") if sig_name == "update" else None)
        if not url:
            out[sig_name] = (d.isoformat(), "unverified")
            ev_out.append(ev("tinyset_" + sig_name, d, "", "TinySet claim without a source URL (ignored)"))
            continue
        r = tf.fetch1(url)
        if "error" in r:
            status = "blocked" if r.get("error") in ("bot_blocked", "login_required", "timeout") else "unverified"
            out[sig_name] = (d.isoformat(), status if status == "blocked" and sig_name == "social" else "unverified")
            ev_out.append(ev("tinyset_" + sig_name, d, url, f"cited page not fetchable ({r.get('error')})"))
            continue
        seen = find_dates(strip_tags(r.get("text") or ""), today) + [x for x in (parse_any(m.group(1), today) for p in STRUCT for m in p.finditer(r.get("text") or "")) if x]
        ok = any(abs((x - d).days) <= 1 for x in seen)
        out[sig_name] = (d.isoformat(), "verified" if ok else "page_live")
        ev_out.append(ev("tinyset_" + sig_name, d, r.get("final_url") or url, "date confirmed on live page" if ok else "page live, claimed date not visible on it"))
    return out, ev_out


# ----------------------------------------------------------------------------- IO
def read_input(src):
    if re.match(r"https?://", src):
        m = re.search(r"docs\.google\.com/spreadsheets/d/([\w-]+)", src)
        if m:
            gid = re.search(r"[#&?]gid=(\d+)", src)
            src = f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv" + (f"&gid={gid.group(1)}" if gid else "")
        with urllib.request.urlopen(src, timeout=60) as r:
            raw = r.read().decode("utf-8-sig", "replace")
    else:
        with open(src, encoding="utf-8-sig", newline="") as f:
            raw = f.read()
    rows = list(csv.reader(io.StringIO(raw)))
    rows = [r for r in rows if any(c.strip() for c in r)]
    return rows[0], rows[1:], hashlib.sha1(raw.encode()).hexdigest()[:12]


def detect_cols(header, rows, name_col, url_col):
    low = [h.strip().lower() for h in header]

    def pick(hints, explicit):
        if explicit:
            if explicit in header:
                return header.index(explicit)
            raise SystemExit(f"column '{explicit}' not found; columns: {header}")
        for h in hints:
            for i, c in enumerate(low):
                if c == h:
                    return i
        for h in hints:
            for i, c in enumerate(low):
                if h in c:
                    return i
        return None
    ui = pick(["website", "url", "domain", "link", "homepage", "site", "job url", "apply"], url_col)
    if ui is None:
        for i in range(len(header)):
            vals = [r[i] for r in rows[:50] if i < len(r) and r[i].strip()]
            if vals and sum(bool(re.match(r"^(https?://)?[\w-]+(\.[\w-]+)+(/|$)", v.strip())) for v in vals) / len(vals) > .6:
                ui = i
                break
    ni = pick(["name", "company", "title", "product", "tool", "vendor", "organization", "organisation", "startup", "project", "position"], name_col)
    if ni is None:
        ni = 0 if ui != 0 else 1
    return ni, ui


ZC = ["zc_verdict", "zc_confidence", "zc_score", "zc_last_activity_date", "zc_last_activity_source", "zc_evidence_url", "zc_reason", "zc_evidence",
      "zc_flags", "zc_final_url", "zc_blog_date", "zc_release_date", "zc_news_date", "zc_social_date", "zc_jobs_open", "zc_signup",
      "zc_tinyset", "zc_signals_checked", "zc_checked_at"]


def build_row(i, sig, ts_claims, ver, today, mode, ts_skip=None):
    """ver = {'v': {...verified claims}, 'e': [evidence]} or None"""
    ts = None
    ts_flag = "not_run"
    vv = ver["v"] if ver else {}
    if ts_claims is not None:
        ts_flag = "matched"
        ts = ts_dict(ts_claims, vv)
    elif ver is not None:
        ts_flag = "unmatched"
    elif ts_skip:
        ts_flag = ts_skip
    v, score, conf, reason, last, last_sig = decide(sig, ts, today, mode)
    evid = list(sig.get("evidence", [])) + (ver["e"] if ver else [])
    evid = [e for e in evid if e["url"]]
    ev_txt = "\n".join(f"{e['signal']} | {e['date'] or '-'} | {e['url']} | {e['basis']}" for e in evid)
    prim = next((e["url"] for e in evid if last and e["date"] == last), None) \
        or next((e["url"] for e in evid if e["signal"] in ("site", "site_agent", "job_page", "status_agent")), "")
    return {"zc_verdict": v, "zc_confidence": conf, "zc_score": score, "zc_last_activity_date": last, "zc_last_activity_source": last_sig,
            "zc_evidence": ev_txt, "zc_evidence_url": prim, "zc_reason": reason, "zc_flags": ",".join(sig.get("flags", [])), "zc_final_url": sig.get("final_url", ""),
            "zc_blog_date": sig.get("update") or "", "zc_release_date": sig.get("release") or "", "zc_news_date": sig.get("news") or "",
            "zc_social_date": sig.get("social") or (ts["social"][0] if ts and ts.get("social") else ""),
            "zc_jobs_open": "" if sig.get("jobs") is None else sig["jobs"], "zc_signup": sig.get("signup") or "",
            "zc_tinyset": ts_flag, "zc_signals_checked": ",".join(dict.fromkeys(sig.get("checked", []))),
            "zc_checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")}


def write_csv(path, header, rows, results):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header + ZC)
        for i, r in enumerate(rows):
            r = r + [""] * (len(header) - len(r))
            res = results.get(i)
            w.writerow(r + ([res.get(c, "") for c in ZC] if res else ["pending"] + [""] * (len(ZC) - 1)))
    os.replace(tmp, path)


REPORT = """<!doctype html><html><head><meta charset="utf-8"><title>Zombie Check report</title><style>
body{font:14px/1.45 system-ui,sans-serif;margin:24px;color:#1c1c1c;background:#fafaf8}h1{font-size:20px;margin:0 0 4px}
.sub{color:#666;margin-bottom:16px}.bar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}button{border:1px solid #ccc;background:#fff;
border-radius:16px;padding:4px 12px;cursor:pointer}button.on{background:#1c1c1c;color:#fff;border-color:#1c1c1c}
input{padding:5px 10px;border:1px solid #ccc;border-radius:6px;min-width:240px}table{border-collapse:collapse;width:100%;background:#fff}
th,td{border-bottom:1px solid #eee;padding:7px 8px;text-align:left;vertical-align:top}th{position:sticky;top:0;background:#f2f2ee;cursor:pointer}
.p{display:inline-block;padding:1px 9px;border-radius:10px;font-size:12px;font-weight:600}.alive{background:#dff3e4;color:#17663a}
.slowing{background:#fdf0d5;color:#8a5a00}.zombie{background:#fbe1e1;color:#9b1c1c}.pending{background:#eee;color:#555}
details summary{cursor:pointer;color:#0b57d0}.ev{font-size:12px;color:#444}.ev a{color:#0b57d0;word-break:break-all}small{color:#777}
</style></head><body><h1>Zombie Check</h1><div class="sub" id="sum"></div><div class="bar" id="f"></div>
<input id="q" placeholder="Filter by name, reason, flag..."><table><thead><tr><th data-k="n">Name</th><th data-k="v">Verdict</th>
<th data-k="s">Score</th><th data-k="d">Last activity</th><th>Why</th><th>Evidence</th></tr></thead><tbody id="b"></tbody></table>
<script>const D=__DATA__;let F="all",S="s",dir=-1;const C={};D.forEach(r=>C[r.v]=(C[r.v]||0)+1);
document.getElementById("sum").textContent=D.length+" rows · "+Object.entries(C).map(([k,v])=>v+" "+k).join(" · ")+" · generated __WHEN__";
["all","alive","slowing down","zombie","unclear"].forEach(k=>{const b=document.createElement("button");b.textContent=k+(k=="all"?"":" ("+(C[k]||0)+")");
b.onclick=()=>{F=k;draw()};b.dataset.k=k;document.getElementById("f").appendChild(b)});
document.querySelectorAll("th[data-k]").forEach(t=>t.onclick=()=>{dir=S==t.dataset.k?-dir:-1;S=t.dataset.k;draw()});
document.getElementById("q").oninput=draw;const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const lk=u=>/^https?:/.test(u)?'<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(u)+'</a>':esc(u);
function draw(){document.querySelectorAll("#f button").forEach(b=>b.className=b.dataset.k==F?"on":"");const q=document.getElementById("q").value.toLowerCase();
const R=D.filter(r=>(F=="all"||r.v==F)&&(!q||(r.n+r.r+r.fl+r.u).toLowerCase().includes(q))).sort((a,b)=>(a[S]>b[S]?1:a[S]<b[S]?-1:0)*dir);
document.getElementById("b").innerHTML=R.map(r=>'<tr><td><b>'+esc(r.n)+'</b><br><small>'+lk(r.u)+'</small></td><td><span class="p '+r.v.split(" ")[0]+'">'+esc(r.v)+
'</span><br><small>'+esc(r.c)+' confidence</small></td><td>'+r.s+'</td><td>'+esc(r.d||"–")+'<br><small>'+esc(r.ds)+'</small></td><td>'+esc(r.r)+
(r.fl?'<br><small>'+esc(r.fl)+'</small>':'')+'</td><td class="ev"><details><summary>'+r.e.length+' signals</summary>'+r.e.map(e=>'<div><b>'+esc(e[0])+'</b> '+esc(e[1])+' '+lk(e[2])+'<br><small>'+esc(e[3])+'</small></div>').join("")+'</details></td></tr>').join("")}
draw()</script></body></html>"""


def write_report(path, header, rows, results, ni, ui):
    data = []
    for i, r in enumerate(rows):
        x = results.get(i) or {"zc_verdict": "pending"}
        evs = [l.split(" | ", 3) for l in (x.get("zc_evidence") or "").split("\n") if l.count(" | ") >= 3]
        data.append({"n": r[ni] if ni < len(r) else "", "u": (r[ui] if ui is not None and ui < len(r) else "") or x.get("zc_final_url", ""),
                     "v": x.get("zc_verdict", ""), "c": x.get("zc_confidence", ""), "s": x.get("zc_score", 0) or 0,
                     "d": x.get("zc_last_activity_date", ""), "ds": x.get("zc_last_activity_source", ""), "r": x.get("zc_reason", ""),
                     "fl": x.get("zc_flags", ""), "e": evs})
    html = REPORT.replace("__DATA__", json.dumps(data).replace("</", "<\\/")).replace("__WHEN__", datetime.now().strftime("%Y-%m-%d %H:%M"))
    open(path, "w", encoding="utf-8").write(html)


def write_xlsx(path, header, rows, results):
    """Same sheet as the CSV, with verdict colours, frozen header, filters and clickable evidence links. Needs openpyxl (optional)."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "zombie check"
    ws.append(header + ZC)
    fills = {"alive": "DFF3E4", "slowing down": "FDF0D5", "zombie": "FBE1E1", "unclear": "E6E6E6"}
    vcol, ucol, ecol = len(header) + ZC.index("zc_verdict") + 1, len(header) + ZC.index("zc_evidence_url") + 1, len(header) + ZC.index("zc_evidence") + 1
    for i, r in enumerate(rows):
        res = results.get(i) or {}
        vals = (r + [""] * (len(header) - len(r)))[:len(header)] + [res.get(c, "") for c in ZC]
        ws.append([v[:32000] if isinstance(v, str) else v for v in vals])
        row = ws.max_row
        v = res.get("zc_verdict", "")
        if v in fills:
            ws.cell(row, vcol).fill = PatternFill("solid", fgColor=fills[v])
        u = res.get("zc_evidence_url", "")
        if u.startswith("http"):
            ws.cell(row, ucol).hyperlink = u
            ws.cell(row, ucol).font = Font(color="0B57D0", underline="single")
        ws.cell(row, ecol).alignment = Alignment(wrap_text=False)
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


# ----------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="Zombie Check: alive / slowing down / zombie verdict for every row of a spreadsheet, from live pages.")
    ap.add_argument("input", help="CSV path, public CSV URL or Google Sheet URL")
    ap.add_argument("-o", "--output", help="output CSV (default <input>.zombiecheck.csv)")
    ap.add_argument("--mode", choices=["companies", "jobs"], default="companies", help="jobs = every row is a job-post URL (ghost-job detector)")
    ap.add_argument("--name-col"), ap.add_argument("--url-col")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--fetch-per-min", type=int, default=150), ap.add_argument("--search-per-min", type=int, default=30)
    ap.add_argument("--no-search", action="store_true", help="skip Search API (news/social/URL resolution)")
    ap.add_argument("--no-tinyset", action="store_true")
    ap.add_argument("--ts-max-rows", type=int, default=120, metavar="N", help="max rows sent to TinySet (only rows phase 1 could not settle; $0.10/row)")
    ap.add_argument("--ts-validate", type=int, default=30, metavar="N", help="also send a seeded random sample of N high-confidence rows to TinySet and report how often it agrees ($0.10/row)")
    ap.add_argument("--yes", action="store_true", help="do not ask before spending on TinySet")
    ap.add_argument("--ts-batch", type=int, default=30, help="rows per TinySet dataset (<=250)")
    ap.add_argument("--ts-concurrency", type=int, default=3, help="TinySet runs in flight (account limit 3)")
    ap.add_argument("--ts-poll", type=int, default=20), ap.add_argument("--ts-timeout", type=int, default=2400)
    ap.add_argument("--agent-budget", type=int, default=50, metavar="N", help="max rows escalated to an Agent browser run (blocked / undated sites). 0 = off")
    ap.add_argument("--agent-concurrency", type=int, default=2)
    ap.add_argument("--limit", type=int, help="only the first N rows (testing)")
    ap.add_argument("--print-tinyset-spec", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="ignore saved state")
    a = ap.parse_args(argv)

    key = os.environ.get("TINYFISH_API_KEY", "")
    if not key:
        sys.exit("Set TINYFISH_API_KEY (https://agent.tinyfish.ai/api-keys)")
    header, rows, h = read_input(a.input)
    if a.limit:
        rows = rows[:a.limit]
    ni, ui = detect_cols(header, rows, a.name_col, a.url_col)
    if ui is None:
        print("warning: no URL column found; will resolve websites via Search", file=sys.stderr)
    if len(rows) < 500:
        print(f"note: {len(rows)} rows (bounty asks for 500+; tool works on any size)", file=sys.stderr)
    out_path = a.output or re.sub(r"\.csv$", "", a.input if not a.input.startswith("http") else "sheet") + ".zombiecheck.csv"
    sdir = out_path + ".zc"
    if a.fresh and os.path.isdir(sdir):
        for fn in os.listdir(sdir):
            os.remove(os.path.join(sdir, fn))
    db = DB(os.path.join(sdir, "state.db"))
    if db.meta("input") not in (None, h + a.mode):
        sys.exit(f"{sdir} holds state for a different input. Use --fresh or another -o.")
    db.meta("input", h + a.mode)
    today = date.today()
    items = {i: (r[ni].strip() if ni < len(r) else "", (r[ui].strip() if ui is not None and ui < len(r) else "")) for i, r in enumerate(rows)}
    if a.print_tinyset_spec:
        print(json.dumps(ts_spec([items[i] for i in list(items)[:a.ts_batch]]), indent=1)); return
    tf = TF(key, a.fetch_per_min, a.search_per_min)
    print(f"{len(rows)} rows | name='{header[ni]}' url='{header[ui] if ui is not None else None}' | mode={a.mode} | state {sdir}", file=sys.stderr)

    use_ts = not a.no_tinyset and a.mode == "companies"

    det = db.get_all("det")
    todo = [i for i in items if i not in det]
    print(f"phase 1: live checks - {len(det)} done, {len(todo)} to go", file=sys.stderr)
    t0, done_n = time.time(), 0
    lock = threading.Lock()

    def job(i):
        name, url = items[i]
        try:
            sig = analyze_job(tf, name, url, today) if a.mode == "jobs" else analyze_site(tf, name, url, today, not a.no_search)
        except Fatal:
            raise
        except Exception as e:  # one bad row must never stop the run
            sig = {"site_state": "unknown", "final_url": "", "flags": ["analysis_error"], "evidence": [], "checked": [], "update": None,
                   "release": None, "news": None, "social": None, "jobs": None, "signup": None, "reason_bits": [f"analysis error: {type(e).__name__}: {e}"]}
        db.put("det", i, sig)
        return i, sig

    def interrupted(*_):
        ABORT.set()
    signal.signal(signal.SIGTERM, interrupted)
    try:
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            for f in as_completed([ex.submit(job, i) for i in todo]):
                try:
                    f.result()
                except Fatal as e:
                    print("STOP:", e, file=sys.stderr)
                    ABORT.set()
                    break
                with lock:
                    done_n += 1
                    if done_n % 25 == 0:
                        print(f"  {done_n}/{len(todo)}  {done_n / max(time.time() - t0, 1):.1f} rows/s", file=sys.stderr)
                        write_partial(a, out_path, header, rows, db, today)
    except KeyboardInterrupt:
        ABORT.set()
        print("\ninterrupted - state saved, re-run the same command to resume", file=sys.stderr)
    det = db.get_all("det")

    # phase 1b: escalate rows Fetch could not settle to a real browser (Agent API)
    if a.agent_budget and a.mode == "companies" and not ABORT.is_set():
        cand = agent_candidates(det, items, today)
        done_ag = sum(1 for s in det.values() if s.get("agent_checked"))
        cand = [i for i in cand if not det[i].get("agent_checked")][:max(0, a.agent_budget - done_ag)]
        if cand:
            print(f"phase 1b: Agent browser check on {len(cand)} unresolved rows (budget {a.agent_budget})", file=sys.stderr)
        agent_stop = threading.Event()

        def ag(i):
            if ABORT.is_set() or agent_stop.is_set():
                return
            s = det[i]
            try:
                apply_agent(s, agent_probe(tf, items[i][0], s.get("final_url") or norm_url(items[i][1])), today)
            except Fatal as e:
                print("Agent stage stopped:", e, file=sys.stderr)
                if re.search(r"\b40[12]\b", str(e)):
                    ABORT.set()      # bad key / empty wallet: nothing else can run either
                else:
                    agent_stop.set()  # e.g. 403: skip the Agent step, keep going with TinySet
                return
            except Exception as e:  # noqa
                s.setdefault("flags", []).append(f"agent_error:{type(e).__name__}")
            s["agent_checked"] = True
            db.put("det", i, s)
        with ThreadPoolExecutor(max_workers=a.agent_concurrency) as ex:
            list(ex.map(ag, cand))
        det = db.get_all("det")

    if use_ts and not ABORT.is_set():
        chosen, skip = ts_select(det, items, today, a.ts_max_rows)
        saved = db.meta("ts_validate")  # keep the first sample on re-runs: those are the rows TinySet was actually sent
        sample = json.loads(saved) if saved else ts_validate_sample(skip, a.ts_validate)
        for i in sample:
            skip.pop(i, None)
        db.meta("ts_skip", json.dumps(skip))
        db.meta("ts_validate", json.dumps(sample))
        chosen = chosen + sample
        already = {i for (j,) in db.q("SELECT idxs FROM batches") for i in json.loads(j)}
        new_rows = [i for i in chosen if i not in already]
        print(f"phase 2: TinySet on {len(chosen) - len(sample)} unresolved rows (budget {a.ts_max_rows}) + {len(sample)} cross-check sample; "
              f"{sum(v == 'skipped_resolved' for v in skip.values())} more resolved by phase 1, "
              f"{sum(v == 'skipped_budget' for v in skip.values())} unresolved but over budget", file=sys.stderr)
        if (not new_rows and not already) or (new_rows and not ts_confirm(len(new_rows), a.yes, n_validate=len([i for i in sample if i in new_rows]))):
            chosen = []
        if chosen:
            ts_thread = threading.Thread(target=run_tinyset, args=(tf, db, items, a, chosen), daemon=True)
            ts_thread.start()
            while ts_thread.is_alive():
                ts_thread.join(30)
                b = db.q("SELECT status,COUNT(*) FROM batches GROUP BY status")
                print("  TinySet batches:", dict(b), file=sys.stderr)
                write_partial(a, out_path, header, rows, db, today)

    # phase 3: verify TinySet claims live, final verdicts
    claims = ts_collect(db, items) if use_ts else {}
    ver_all = db.get_all("ver")
    pending = [i for i in claims if i not in ver_all and i in det and not ABORT.is_set()]
    if pending:
        print(f"phase 3: re-fetching cited evidence for {len(pending)} TinySet rows", file=sys.stderr)
        def vjob(i):
            v, e = verify_claims(tf, claims[i], today)
            db.put("ver", i, {"v": v, "e": e})
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            list(ex.map(vjob, pending))
        ver_all = db.get_all("ver")
    write_partial(a, out_path, header, rows, db, today, final=True)
    st = tf.stats
    print(f"done -> {out_path}\nAPI usage: fetch URLs={st['fetch_urls']} search={st['search']} agent={st['agent']} tinyset rows={st['tinyset_rows']}", file=sys.stderr)
    return 2 if ABORT.is_set() else 0


def write_partial(a, out_path, header, rows, db, today, final=False):
    det = db.get_all("det")
    ver = db.get_all("ver")
    items = {i: None for i in det}
    claims = {}
    if a.mode == "companies" and not a.no_tinyset:
        names = {}
        ni, ui = detect_cols(header, rows, a.name_col, a.url_col)
        names = {i: (rows[i][ni].strip() if ni < len(rows[i]) else "", "") for i in range(len(rows))}
        claims = ts_collect(db, names) if db.q("SELECT 1 FROM batches WHERE data IS NOT NULL") else {}
    results = {}
    sent = {i for (j,) in db.q("SELECT idxs FROM batches WHERE status IN ('collected','partial')") for i in json.loads(j)}
    skip = json.loads(db.meta("ts_skip") or "{}") if a.mode == "companies" and not a.no_tinyset else {}
    for i, sig in det.items():
        results[i] = build_row(i, sig, claims.get(i) if (final or i in ver) else None, ver.get(i), today, a.mode,
                               skip.get(str(i)) or ("unmatched" if final and i in sent and i not in claims else None))
    write_csv(out_path, header, rows, results)
    if final:
        ni, ui = detect_cols(header, rows, a.name_col, a.url_col)
        write_report(out_path.rsplit(".csv", 1)[0] + ".report.html", header, rows, results, ni, ui)
        write_xlsx(out_path.rsplit(".csv", 1)[0] + ".xlsx", header, rows, results)
        from collections import Counter
        c = Counter(r["zc_verdict"] for r in results.values())
        lines = [f"# Zombie Check summary\n", f"rows: {len(rows)}  checked: {len(results)}\n"] + [f"- {k}: {n}" for k, n in c.most_common()]
        sample = json.loads(db.meta("ts_validate") or "[]")
        if sample:
            pairs = []
            for i in sample:
                if i not in det:
                    continue
                fs = decide(det[i], None, today, a.mode)[0]
                cl = claims.get(i)
                tsv = decide({"site_state": "live", "flags": [], "evidence": [], "reason_bits": [], "jobs": None, "signup": None,
                              "update": None, "release": None, "news": None, "social": None},
                             ts_dict(cl, (ver.get(i) or {}).get("v", {})), today, a.mode)[0] if cl is not None else None
                pairs.append((fs, tsv))
            agree, answered, n = ts_crosscheck(pairs)
            lines += ["", f"TinySet cross-check: {agree} of {n} sampled rows agree with the Fetch/Search verdict"
                          f" ({n - answered} had no TinySet answer; 'slowing down' counts as agreeing with either side)"]
        open(out_path + ".summary.md", "w").write("\n".join(lines) + "\n")
        print("\n".join(lines), file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
