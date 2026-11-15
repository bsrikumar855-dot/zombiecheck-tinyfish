#!/usr/bin/env python3
"""Turn any GitHub 'awesome'-style markdown list into name,url,description CSV (one row per external link, deduped by domain+path).
usage: awesome_to_csv.py <raw-readme-url-or-file> > list.csv"""
import csv, re, sys, urllib.request
src = sys.argv[1]
md = urllib.request.urlopen(src, timeout=60).read().decode("utf8", "replace") if src.startswith("http") else open(src, encoding="utf8").read()
seen, w = set(), csv.writer(sys.stdout)
w.writerow(["name", "url", "description"])
for line in md.splitlines():
    m = re.match(r"^\s*[-*+]\s+\[([^\]]+)\]\((https?://[^)\s]+)\)\s*[-–—:]?\s*(.*)$", line)
    if not m:
        continue
    name, url, desc = m.group(1).strip(), m.group(2).strip(), re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", m.group(3))[:200]
    key = re.sub(r"^https?://(www\.)?", "", url).rstrip("/").lower()
    if key in seen or "#" in url.split("//", 1)[1].split("/", 1)[0]:
        continue
    seen.add(key)
    w.writerow([name, url, desc])
