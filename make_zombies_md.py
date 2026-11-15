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
    sig = z.own_info(rows[i][1] if len(rows[i]) > 1 else r["url"], det.get(i, {}))
    st = sig.get("site_state")
    reason = r["zc_reason"]
    ev = [e for e in sig.get("evidence", []) if e.get("url")]
    d = "-"
    if "agent browser reports" in reason.lower():
        fired, url = "hard gate: Agent browser reported shutdown, confirmed by shutdown wording on own site", r["zc_evidence_url"] or r["url"]
    elif st in GATE:
        fired = "hard gate: " + GATE[st]
        url = next((e["url"] for e in ev if e["signal"] in ("site", "site_agent", "archived")), r["zc_final_url"] or r["url"])
        if st == "absorbed":
            url = (sig.get("redirect_check") or {}).get("url") or url
            fired = "hard gate: redirect to an unrelated domain, corroborated by acquired/merged wording (news or landing page)"
        if st == "dead":  # show the actual fetch failure behind "dead"
            fail = next((e["basis"] for e in sig.get("evidence", []) if e.get("signal") == "site" and "failed" in e.get("basis", "")), "")
            fired += f" [{fail or 'fetch failed'}; flags: {','.join(f for f in sig.get('flags', []) if f.startswith('fetch_')) or '-'}]"
    elif "TinySet reports" in reason:
        fired, url = "hard gate: TinySet-reported shutdown, confirmed by shutdown wording on own site", r["zc_evidence_url"] or r["url"]
    else:
        proof, _ = z.stale_proof(sig, today, sig.get("jobs"), sig.get("signup"))
        if proof:
            d, url = proof[0]["date"], proof[0]["url"]
            fired = f"staleness: {len(proof)} structured own-domain source(s) ({', '.join(sorted({e['signal'] for e in proof}))}), newest {d}, all over 730 days"
        else:
            fired, url = "staleness (proof missing: BUG)", r["zc_evidence_url"] or r["url"]
    own = "Y" if z.on_own_domain(url, sig) else "N"  # strict: a redirect target is the acquirer's domain, not the organisation's
    lines.append((r["name"], r["url"], fired, d, url, own, r["zc_confidence"]))

with open(md, "w", encoding="utf-8", newline="\n") as f:
    f.write(f"# Zombie rows ({len(lines)} of {len(res)})\n\n")
    f.write("Every row with verdict `zombie` in `full/o.csv`, with the rule that fired. Hard gates: dead (404/410/unreachable), parked, shutdown notice on the site itself, archived repo, redirect to an unrelated domain that a news result or the landing page corroborates as acquired/merged (no renamed/formerly wording), TinySet/Agent-reported shutdown that the own site also confirms. Otherwise a zombie needs structured dated sources on the organisation's own domain or own GitHub repo, all older than 730 days: two independent ones, or one plus zero open jobs and sign-up not working; never social, news or third-party domains, never text-parsed dates, never dates before 2010.\n\n")
    f.write("| # | name | URL | what fired | date | evidence URL | evidence on own domain (Y/N) | confidence |\n|---|---|---|---|---|---|---|---|\n")
    for n, (nm, u, fired, d, ev_url, own, conf) in enumerate(lines, 1):
        esc = lambda x: str(x).replace("|", "/").replace("\n", " ")
        f.write(f"| {n} | {esc(nm)} | {esc(u)} | {esc(fired)} | {d} | {esc(ev_url)} | {own} | {conf} |\n")
print("zombies listed:", len(lines), "->", md)
