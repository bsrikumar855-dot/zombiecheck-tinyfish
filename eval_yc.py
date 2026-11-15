"""Compare Zombie Check verdicts with YC's own status labels. usage: python eval_yc.py yc/o.csv yc_eval.md"""
import csv, sys, collections

src = sys.argv[1] if len(sys.argv) > 1 else "yc/o.csv"
out = sys.argv[2] if len(sys.argv) > 2 else "yc_eval.md"
rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
VERDICTS = ["alive", "slowing down", "unclear", "zombie"]
GROUPS = [("Inactive", {"Inactive"}), ("Acquired", {"Acquired"}), ("Active/Public", {"Active", "Public"})]


def grp(r):
    return next(g for g, s in GROUPS if r["yc_status"] in s)


tab = {g: collections.Counter() for g, _ in GROUPS}
for r in rows:
    tab[grp(r)][r["zc_verdict"]] += 1
n = {g: sum(tab[g].values()) for g, _ in GROUPS}
pct = lambda a, b: f"{100 * a / b:.1f}%" if b else "n/a"

inactive = [r for r in rows if grp(r) == "Inactive"]
acquired = [r for r in rows if grp(r) == "Acquired"]
active = [r for r in rows if grp(r) == "Active/Public"]
zi = sum(r["zc_verdict"] == "zombie" for r in inactive)
ab = sum(r["zc_verdict"] in ("unclear", "slowing down") for r in inactive)
fz = [r for r in active if r["zc_verdict"] == "zombie"]
redir = [r for r in acquired if r["zc_verdict"] in ("zombie", "unclear") and "redirects to" in r["zc_reason"]]
acq_zu = [r for r in acquired if r["zc_verdict"] in ("zombie", "unclear")]
acq_zu_redirect_flag = [r for r in acq_zu if "redirects_to_unrelated" in r["zc_flags"]]

L = [f"# YC ground-truth validation ({len(rows)} rows)\n",
     "Ground truth is YC's own company status (`yc-oss` list): Inactive, Acquired, Active/Public. Batches W12 to S19, companies with a website, seeded sample (seed 42): 250 Inactive, 125 Acquired, 125 Active/Public. "
     "Command: `python zombiecheck.py yc500.csv -o yc/o.csv --no-tinyset --agent-budget 20` (Fetch + Search + a 20-row Agent budget, no TinySet). No rule was changed for this test.\n",
     "## Tool verdict by YC status (count, % of that status)\n",
     "| YC status (rows) | " + " | ".join(VERDICTS) + " |", "|---|" + "---|" * len(VERDICTS)]
for g, _ in GROUPS:
    L.append(f"| {g} ({n[g]}) | " + " | ".join(f"{tab[g][v]} ({pct(tab[g][v], n[g])})" for v in VERDICTS) + " |")
L += ["", "## Headline numbers\n",
      f"- **(a) Recall:** {zi} of {len(inactive)} Inactive rows called zombie = **{pct(zi, len(inactive))}**.",
      f"- **(b) Abstain:** {ab} of {len(inactive)} Inactive rows called unclear or slowing down = **{pct(ab, len(inactive))}** "
      f"(unclear {tab['Inactive']['unclear']}, slowing down {tab['Inactive']['slowing down']}). The remaining {tab['Inactive']['alive']} ({pct(tab['Inactive']['alive'], len(inactive))}) were called alive.",
      f"- **(c) False-zombie rate:** {len(fz)} of {len(active)} Active/Public rows called zombie = **{pct(len(fz), len(active))}**.",
      f"- **(d) Acquired rows:** {len(acq_zu)} of {len(acquired)} were zombie or unclear ({sum(r['zc_verdict'] == 'zombie' for r in acquired)} zombie, {sum(r['zc_verdict'] == 'unclear' for r in acquired)} unclear); "
      f"{len(redir)} of those were via a redirect to another domain ({sum(r['zc_verdict'] == 'zombie' for r in redir)} zombie, {sum(r['zc_verdict'] == 'unclear' for r in redir)} unclear).",
      "", "## (c) Every Active/Public row the tool called zombie\n"]
if fz:
    L += ["| name | URL | YC status | what fired | evidence URL |", "|---|---|---|---|---|"]
    for r in fz:
        esc = lambda x: str(x).replace("|", "/").replace("\n", " ")
        L.append(f"| {esc(r['name'])} | {esc(r['url'])} | {r['yc_status']} | {esc(r['zc_reason'][:200])} | {esc(r['zc_evidence_url'])} |")
else:
    L.append("None.")
L += ["", "## Zombie calls by YC status, with evidence URLs\n", "| name | YC status | reason | evidence URL |", "|---|---|---|---|"]
for r in rows:
    if r["zc_verdict"] == "zombie":
        esc = lambda x: str(x).replace("|", "/").replace("\n", " ")
        L.append(f"| {esc(r['name'])} | {r['yc_status']} | {esc(r['zc_reason'][:160])} | {esc(r['zc_evidence_url'])} |")
L += ["", "## Notes\n",
      "- YC's status is a label, not a live check: an `Inactive` company may still have a working website, and an `Active` one may be dormant. Disagreement is not always a tool error.",
      "- Confidence of every row is in `yc/o.csv` (`zc_confidence`)."]
open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("\n".join(L))
