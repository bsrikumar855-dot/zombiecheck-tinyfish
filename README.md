# Zombie Check

Spreadsheet in, same spreadsheet out with a verdict on every row: **alive / slowing down / zombie**, the date of the latest
activity found, and links to the evidence. Built on TinyFish (TinySet + Fetch + Search + Agent). Stdlib-only Python 3.9+.

```bash
export TINYFISH_API_KEY=...            # personal key (Datasets reject org keys)
python3 awesome_to_csv.py https://raw.githubusercontent.com/ripienaar/free-for-dev/master/README.md > list.csv   # 1,372 real rows
python3 zombiecheck.py list.csv -o list.checked.csv                 # re-run the same command to resume
python3 zombiecheck.py jobs.csv --mode jobs                         # ghost-job detector (rows = job-post URLs)
python3 zombiecheck.py "https://docs.google.com/spreadsheets/d/<id>/edit#gid=0"   # link-shared Google Sheet
```
Columns are auto-detected (`--name-col`, `--url-col` to override). Rows without a URL are resolved with Search.

## Signals (10, all from live pages, `ttl=0`)
| signal | source |
|---|---|
| site liveness: dead, bot-blocked (never penalised), parked/for-sale, shutdown notice | Fetch homepage |
| redirects: same brand on new domain = rebrand/move; unrelated domain = absorbed/acquired; "acquired by" / "formerly" notices | Fetch final_url + page text |
| newest blog/news/press date | Fetch (structured `<time>`/meta/JSON-LD first, visible text fallback) |
| newest changelog / release / commit | Fetch changelog page + GitHub `releases.atom`, `commits.atom` |
| open jobs (+ posting dates) | Fetch careers page / ATS board |
| sign-up works / waitlist / broken | Fetch sign-up page; `--agent-signup N` has the Agent API open ambiguous ones |
| newest news + acquisition/shutdown headlines | Search (news) |
| newest social activity | Search (social domains) + TinySet |
| site content freshness: newest `sitemap.xml` lastmod / RSS-Atom feed entry (auto-generated "everything = today" sitemaps ignored) | Fetch |
| archived GitHub repository (read-only banner) and newest commit/release for repo rows | Fetch |
| browser check for rows Fetch cannot settle (bot-blocked, JS-only, no dated activity) | Agent API, `--agent-budget 50` by default |

Nav/footer links are read from Fetch's `links[]` array as well as the page body, because Fetch returns semantic HTML with
boilerplate removed. Unlinked conventional paths (`/blog`, `/changelog`, `/careers`) are probed; a missing probe is never counted as evidence.
The same URL in many rows is fetched once per run (in-memory only; nothing is read from an earlier run).

## How TinySet is used
TinySet fills a table from the live web and ties each value to a page the agent opened. It has no "enrich my rows" input,
so each batch (default 30 rows, 3 runs in flight = the account limit) is created with an explicit `spec`
whose description is a **fixed entity list** (`name :: website`) and `target_rows = batch size`. 8 columns:
`still_operating, status_note, latest_update_date, latest_social_date, open_jobs, signup_open, evidence_urls`.
Rows it returns are matched back by name; anything not in the list (hallucinated) is dropped.
TinySet is the *second opinion and gap filler* (social posts we cannot scrape, JS-rendered careers pages), never the sole judge:
every date it claims is **re-fetched live from the page it cites**. Confirmed = full weight; page live but date not visible = used only if
we found nothing ourselves; unreachable (X/LinkedIn bot walls) = half weight, flagged "not independently verified".

## Verdict (plain code, `decide()`, no LLM)
Hard gates -> **zombie**: site dead, parked, shutdown notice, archived repo, redirect to an unrelated domain.
Otherwise a weighted score over the signals that were *determinable* (unknowns are excluded, and lower `zc_confidence`):
update recency 45 / social 15 / open jobs 15 / sign-up 15 / site live 10. >=60 alive, 30-59 slowing down, <30 zombie.
Nothing newer than 2 years and no jobs caps the score at 25. "alive" also needs dated activity within 120 days or open jobs. Jobs mode: closed/404/`validThrough` expired/redirect-to-index = zombie; age 0-30d full credit.

## Output columns (appended, originals untouched)
`zc_verdict, zc_confidence, zc_score, zc_last_activity_date, zc_last_activity_source, zc_evidence_url` (the page that proves the date, clickable),
`zc_reason, zc_evidence` (one line per signal: `signal | date | url | basis`), `zc_flags, zc_final_url, zc_blog_date, zc_release_date, zc_news_date, zc_social_date, zc_jobs_open, zc_signup, zc_tinyset, zc_signals_checked, zc_checked_at`.
Plus `<output>.xlsx` (verdict colours, filters, hyperlinked evidence; needs `openpyxl`), `<output>.report.html` (filterable, sortable, every
signal expandable with links) and `<output>.summary.md`.

## Reliability
- State in `<output>.zc/state.db` (SQLite): per-row results, TinySet dataset ids. Kill it any time; re-run resumes, re-attaching to running datasets.
- One row's exception never stops the run; 401/402/403 stop cleanly with state saved; 429/5xx retry with `Retry-After`/backoff.
- Client-side limiters at the documented limits: Fetch 150 URLs/min, Search 30/min (`--fetch-per-min`, `--search-per-min`).

## Cost / limits (from the docs)
Fetch is free up to 1,000 URLs/day; this tool uses ~6 per row, so 500 rows needs wallet balance (or run ~150 rows/day free). Search free to 12,000/day.
TinySet runs take 5-20 min each; 500 rows = 17 batches ~ 1.5-2 h at 3 in flight. Use `--no-tinyset` for a fast Fetch+Search-only pass.

## Tested vs not tested
Tested: 17 unit tests on the deterministic core (`python3 -m unittest tests/test_core.py`), full pipeline, resume after SIGKILL, job mode, 540-row run against `tests/mock_tinyfish.py` (a local fake of the four APIs + a fake web).
**Not tested against live TinyFish** (no key/network in the build sandbox). Assumptions to check on first run: the TinySet `spec` honours a fixed
entity list in `description` (`--print-tinyset-spec` shows it; `zc_tinyset=unmatched` flags rows it did not return), and Fetch `format=html` returns raw page HTML in `text`.
Known weak spots: social recency (X/LinkedIn are bot-walled), JS-only careers pages, `<time>`-less blogs fall back to text dates.
