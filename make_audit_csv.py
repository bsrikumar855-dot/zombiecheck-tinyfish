"""Write zc_audit.csv: a hand-check sample from SAVED results (no network, no API). Reads full/o.csv.
30 random 'slowing down' rows and up to 15 random zombie rows (seed 42). If fewer than 15 zombies exist, all of them are taken.
usage: python make_audit_csv.py [full/o.csv] [zc_audit.csv]"""
import csv, random, sys

src = sys.argv[1] if len(sys.argv) > 1 else "full/o.csv"
out = sys.argv[2] if len(sys.argv) > 2 else "zc_audit.csv"
rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
rng = random.Random(42)


def pick(verdict, n):
    pool = sorted((r for r in rows if r["zc_verdict"] == verdict), key=lambda r: r["name"])
    take = rng.sample(pool, min(n, len(pool)))
    print(f"{verdict}: {len(pool)} rows exist, sampled {len(take)} (asked for {n})")
    return take


def sentence(r):
    d = r.get("zc_last_activity_date") or ""
    src_ = r.get("zc_last_activity_source") or ""
    head = f"last activity {d} via {src_}: " if d else ""
    return (head + (r.get("zc_reason") or "")).strip()[:300]


sample = pick("slowing down", 30) + pick("zombie", 15)
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["name", "url", "verdict", "evidence_url", "evidence_sentence_or_date", "correct y/n"])
    for r in sample:
        w.writerow([r["name"], r["url"], r["zc_verdict"], r["zc_evidence_url"], sentence(r), ""])
print(len(sample), "rows ->", out)
