"""Recompute verdicts from saved state (no network, no TinySet) and list every zombie row with the reason it fired.
usage: python make_zombies_md.py <input.csv> <output.csv> <rows> <zombies.md>"""
import csv, sys, types, collections
from datetime import date
import zombiecheck as z

inp, out, nrows, md = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
raw = list(csv.reader(open(inp, encoding="utf-8-sig")))
header, rows = raw[0], raw[1:1 + nrows]
db = z.DB(out + ".zc/state.db")
a = types.SimpleNamespace(mode="companies", no_tinyset=False, name_col=None, url_col=None)
today = date.today()
z.write_partial(a, out, header, rows, db, today, final=True)  # pure recompute: no network, no TinySet
res = list(csv.DictReader(open(out, encoding="utf-8-sig")))
det = db.get_all("det")
print(len(res), dict(collections.Counter(r["zc_verdict"] for r in res)))
print("confidence", dict(collections.Counter(r["zc_confidence"] for r in res)))

GATE = {"dead": "dead site (404/410/unreachable)", "parked": "parked / for-sale domain", "absorbed": "redirect to an unrelated domain",
        "shutdown": "shutdown notice about the site itself", "archived": "archived repository"}
lines = []
for i, r in enumerate(res):
    if r["zc_verdict"] != "zombie":
        continue
    sig = det.get(i, {})
    st = sig.get("site_state")
    reason = r["zc_reason"]
    ev = [e for e in sig.get("evidence", []) if e.get("url")]
    if "agent browser reports" in reason.lower():
        fired, d, url = "hard gate: Agent browser reported shutdown", "", r["zc_evidence_url"] or r["url"]
    elif st in GATE:
        fired, d = "hard gate: " + GATE[st], ""
        url = next((e["url"] for e in ev if e["signal"] in ("site", "site_agent", "archived")), r["zc_final_url"] or r["url"])
    elif "TinySet reports" in reason:
        fired, d, url = "hard gate: TinySet-reported shutdown (" + reason.split("TinySet reports:")[1].split(";")[0].strip() + ")", "", r["zc_evidence_url"] or r["url"]
    else:
        cands = [(sig[k], k) for k in ("update", "release", "agent_update") if sig.get(k)]
        d, k = max(cands) if cands else ("", "")
        label = {"update": "blog / changelog / sitemap-feed date", "release": "release / commit-feed date", "agent_update": "page date read by Agent browser"}.get(k, k)
        fired = f"staleness: newest own-page dated signal ({label}) over 730 days old"
        url = next((e["url"] for e in ev if e.get("date") == d), r["zc_evidence_url"] or r["url"])
    lines.append((r["name"], r["url"], fired, d or "-", url, r["zc_confidence"]))

with open(md, "w", encoding="utf-8", newline="\n") as f:
    f.write(f"# Zombie rows ({len(lines)} of {len(res)})\n\n")
    f.write("Every row with verdict `zombie` in `full/o.csv`, with the rule that fired. Hard gates: dead 404/410/unreachable, parked, shutdown notice about the site itself, archived repo, redirect to an unrelated domain, TinySet/Agent-reported shutdown. Otherwise a zombie needs a dated signal from the organisation's own pages older than 730 days (social and third-party news dates never count).\n\n")
    f.write("| # | name | URL | what fired | date | evidence URL | confidence |\n|---|---|---|---|---|---|---|\n")
    for n, (nm, u, fired, d, ev_url, conf) in enumerate(lines, 1):
        esc = lambda x: str(x).replace("|", "/").replace("\n", " ")
        f.write(f"| {n} | {esc(nm)} | {esc(u)} | {esc(fired)} | {d} | {esc(ev_url)} | {conf} |\n")
print("zombies listed:", len(lines), "->", md)
