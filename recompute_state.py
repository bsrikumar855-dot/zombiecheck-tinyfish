"""Recompute an output CSV from its saved state: no network, no TinySet. usage: python recompute_state.py <input.csv> <output.csv> [--limit N] [--no-tinyset]"""
import csv, sys, types
from datetime import date
import zombiecheck as z
inp, out = sys.argv[1], sys.argv[2]
raw = list(csv.reader(open(inp, encoding="utf-8-sig")))
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
header, rows = raw[0], raw[1:1 + limit] if limit else raw[1:]
db = z.DB(out + ".zc/state.db")
a = types.SimpleNamespace(mode="companies", no_tinyset="--no-tinyset" in sys.argv, name_col=None, url_col=None)
z.write_partial(a, out, header, rows, db, date.today(), final=True)
