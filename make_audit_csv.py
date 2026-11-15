"""Write zc_audit.csv: a hand-check sample from SAVED results (no network, no API).
free-for-dev (full/o.csv): 30 random 'slowing down' rows + up to 15 random zombie rows (seed 42; that run has only 1 zombie).
YC (yc/o.csv): 14 random zombie rows (seed 42).
Every row carries a `source` column (free-for-dev or yc); precision is never pooled across sources.
usage: python make_audit_csv.py [zc_audit.csv]"""
import csv, random, sys

out = sys.argv[1] if len(sys.argv) > 1 else "zc_audit.csv"
SOURCES = [("free-for-dev", "full/o.csv", [("slowing down", 30), ("zombie", 15)]),
           ("yc", "yc/o.csv", [("zombie", 14)])]


def sentence(r):
    d = r.get("zc_last_activity_date") or ""
    src_ = r.get("zc_last_activity_source") or ""
    head = f"last activity {d} via {src_}: " if d else ""
    return (head + (r.get("zc_reason") or "")).strip()[:300]


sample = []
for source, path, plan in SOURCES:
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    rng = random.Random(42)  # one seeded generator per source, so adding a source never changes another source's rows
    for verdict, n in plan:
        pool = sorted((r for r in rows if r["zc_verdict"] == verdict), key=lambda r: r["name"])
        take = rng.sample(pool, min(n, len(pool)))
        print(f"{source}: {verdict}: {len(pool)} rows exist, sampled {len(take)} (asked for {n})")
        sample += [(source, r) for r in take]

with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["name", "url", "source", "verdict", "evidence_url", "evidence_sentence_or_date", "correct y/n"])
    for source, r in sample:
        w.writerow([r["name"], r["url"], source, r["zc_verdict"], r["zc_evidence_url"], sentence(r), ""])
print(len(sample), "rows ->", out)
