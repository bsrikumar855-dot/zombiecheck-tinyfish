"""Read the hand-filled zc_audit.csv and write precision per verdict into SUBMISSION.md under "Hand-check".
Precision = rows marked y / rows checked (marked y or n), per verdict. Blank rows are not counted as checked.
usage: python audit_precision.py [zc_audit.csv] [SUBMISSION.md] [--dry-run]"""
import csv, re, sys, collections

args = [a for a in sys.argv[1:] if not a.startswith("--")]
audit = args[0] if len(args) > 0 else "zc_audit.csv"
sub = args[1] if len(args) > 1 else "SUBMISSION.md"
dry = "--dry-run" in sys.argv
BEGIN, END = "<!-- hand-check:begin -->", "<!-- hand-check:end -->"

rows = list(csv.DictReader(open(audit, encoding="utf-8-sig")))
col = next(c for c in rows[0].keys() if c.strip().lower().startswith("correct"))
checked, right, sent = collections.Counter(), collections.Counter(), collections.Counter()
for r in rows:
    v = r["verdict"]
    sent[v] += 1
    a = (r[col] or "").strip().lower()
    if a in ("y", "yes"):
        checked[v] += 1; right[v] += 1
    elif a in ("n", "no"):
        checked[v] += 1
    elif a:
        sys.exit(f"STOP: unrecognised answer {a!r} for {r['name']!r}; use y or n")
if not sum(checked.values()):
    sys.exit("No rows are marked y/n yet: nothing to report. Fill the 'correct y/n' column of " + audit + " first.")

lines = [BEGIN, "Hand-check precision (a person opened each evidence URL and marked the verdict correct y/n; `zc_audit.csv`, seed 42, sampled from the saved free-for-dev results):", "",
         "| verdict | rows sampled | rows checked | marked correct | precision |", "|---|---|---|---|---|"]
for v in ("slowing down", "zombie"):
    if sent[v]:
        p = f"{100 * right[v] / checked[v]:.1f}%" if checked[v] else "n/a"
        lines.append(f"| {v} | {sent[v]} | {checked[v]} | {right[v]} | {p} ({right[v]}/{checked[v]}) |")
lines += ["", "Precision is correct / checked. Rows left blank are not counted. Small samples: read these as indicative, not as an accuracy rate.", END]
block = "\n".join(lines)

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
