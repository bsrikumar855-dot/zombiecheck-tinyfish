"""Recompute an output CSV from its saved state: no network, no TinySet. usage: python recompute_state.py <input.csv> <output.csv> [--no-tinyset]"""
import csv, sys, types
from datetime import date
import zombiecheck as z
inp, out = sys.argv[1], sys.argv[2]
raw = list(csv.reader(open(inp, encoding="utf-8-sig")))
header, rows = raw[0], raw[1:]
db = z.DB(out + ".zc/state.db")
a = types.SimpleNamespace(mode="companies", no_tinyset="--no-tinyset" in sys.argv, name_col=None, url_col=None)
z.write_partial(a, out, header, rows, db, date.today(), final=True)
