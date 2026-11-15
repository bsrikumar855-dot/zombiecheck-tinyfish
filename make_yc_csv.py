"""Build yc500.csv: a ground-truth test set from YC's public company list (https://yc-oss.github.io/api/companies/all.json).
Batches W12..S19 with a website; seeded sample (seed 42): 250 Inactive, 125 Acquired, 125 Active/Public.
usage: python make_yc_csv.py [all.json] [out.csv]"""
import csv, json, os, random, sys, urllib.request, collections

SRC = "https://yc-oss.github.io/api/companies/all.json"
src = sys.argv[1] if len(sys.argv) > 1 else "yc_all.json"
out = sys.argv[2] if len(sys.argv) > 2 else "yc500.csv"
if not os.path.exists(src):
    urllib.request.urlretrieve(SRC, src)
data = json.load(open(src, encoding="utf-8"))
BATCHES = {f"{s} 20{y}" for y in range(12, 20) for s in ("Winter", "Summer")}  # W12 .. S19
pool = [c for c in data if c.get("batch") in BATCHES and (c.get("website") or "").strip()]
by = collections.defaultdict(list)
for c in pool:
    by[c["status"]].append(c)
print("companies per status in W12-S19 with a website:", {k: len(v) for k, v in sorted(by.items())})
all_status = collections.Counter(c["status"] for c in data if c.get("batch") in BATCHES)
print("(all companies per status in that range, with or without a website:", dict(all_status), ")")
ap = sorted(by["Active"] + by["Public"], key=lambda c: c["id"])
want = [("Inactive", sorted(by["Inactive"], key=lambda c: c["id"]), 250), ("Acquired", sorted(by["Acquired"], key=lambda c: c["id"]), 125),
        ("Active/Public", ap, 125)]
for label, p, n in want:
    if len(p) < n:
        sys.exit(f"STOP: only {len(p)} {label} companies with a website, need {n}")
rng = random.Random(42)
rows = []
for label, p, n in want:
    for c in rng.sample(p, n):
        rows.append({"name": c["name"], "url": c["website"].strip(), "batch": c["batch"], "yc_status": c["status"]})
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["name", "url", "batch", "yc_status"])
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows ->", out, dict(collections.Counter(r["yc_status"] for r in rows)))
