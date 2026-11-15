"""Read the hand-filled zc_audit.csv and write precision into SUBMISSION.md under "Hand-check".
Precision = rows marked y / rows checked (marked y or n). Reported per verdict AND per source (free-for-dev, yc), one line per
(source, verdict) pair; sources are NEVER pooled. Every figure is printed with its checked count (k/n). Blank rows are not counted.
usage: python audit_precision.py [zc_audit.csv] [SUBMISSION.md] [--dry-run]"""
import csv, re, sys, collections

args = [a for a in sys.argv[1:] if not a.startswith("--")]
audit = args[0] if len(args) > 0 else "zc_audit.csv"
sub = args[1] if len(args) > 1 else "SUBMISSION.md"
dry = "--dry-run" in sys.argv
BEGIN, END = "<!-- hand-check:begin -->", "<!-- hand-check:end -->"

rows = list(csv.DictReader(open(audit, encoding="utf-8-sig")))
if not rows:
    sys.exit("zc_audit.csv has no rows")
need = {"source", "verdict"}
if not need <= set(rows[0].keys()):
    sys.exit("zc_audit.csv needs a 'source' and a 'verdict' column (regenerate it with make_audit_csv.py)")
col = next(c for c in rows[0].keys() if c.strip().lower().startswith("correct"))
sent, checked, right = collections.Counter(), collections.Counter(), collections.Counter()
for r in rows:
    key = (r["source"].strip(), r["verdict"].strip())
    sent[key] += 1
    a = (r[col] or "").strip().lower()
    if a in ("y", "yes"):
        checked[key] += 1; right[key] += 1
    elif a in ("n", "no"):
        checked[key] += 1
    elif a:
        sys.exit(f"STOP: unrecognised answer {a!r} for {r['name']!r} ({key[0]}); use y or n")
if not sum(checked.values()):
    sys.exit("No rows are marked y/n yet: nothing to report. Fill the 'correct y/n' column of " + audit + " first.")

SRC_ORDER = ["free-for-dev", "yc"]
VERDICT_ORDER = ["slowing down", "zombie", "unclear", "alive"]
keys = sorted(sent, key=lambda k: (SRC_ORDER.index(k[0]) if k[0] in SRC_ORDER else 99, VERDICT_ORDER.index(k[1]) if k[1] in VERDICT_ORDER else 99))
lines = ["Hand-check precision. A person opened each evidence URL and marked the verdict correct y/n (`zc_audit.csv`, seed 42, sampled from the saved results). "
         "One line per source and verdict; sources are never pooled, and every figure shows how many rows were checked.", "",
         "| source | verdict | rows sampled | rows checked | marked correct | precision (correct / checked) |", "|---|---|---|---|---|---|"]
for k in keys:
    s, v = k
    if checked[k]:
        p = f"{100 * right[k] / checked[k]:.1f}% ({right[k]}/{checked[k]} checked)"
    else:
        p = f"n/a (0 checked of {sent[k]} sampled)"
    lines.append(f"| {s} | {v} | {sent[k]} | {checked[k]} | {right[k]} | {p} |")
lines += ["", "Small samples: read these as indicative, not as an accuracy rate. Rows left blank are not counted. "
          "A zombie in free-for-dev is a single row, so its figure is an anecdote, not a rate.", END]
block = "\n".join([BEGIN] + lines)

text = open(sub, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
text = text.replace("\r\n", "\n")
if BEGIN in text:
    text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda m: block, text, flags=re.S)
elif re.search(r"^## Hand-check\s*$", text, re.M):
    text = re.sub(r"(^## Hand-check\s*\n)", lambda m: m.group(1) + "\n" + block + "\n", text, count=1, flags=re.M)
else:
    i = text.index("## Validation on ground truth") if "## Validation on ground truth" in text else len(text)
    text = text[:i] + "## Hand-check\n\n" + block + "\n\n" + text[i:]
print(block)
if dry:
    print("(dry run: SUBMISSION.md not changed)")
else:
    open(sub, "w", encoding="utf-8", newline="").write(text.replace("\n", nl))
    print("->", sub)
