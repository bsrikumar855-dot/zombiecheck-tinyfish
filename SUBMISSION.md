# Zombie Check: a verdict on every row, with the page that proves it

**What it is.** A CLI (`zombiecheck.py`, Python stdlib, optional `openpyxl`) that takes any CSV or Google Sheet of 500+ companies,
tools, vendors or job posts and returns the same sheet with `alive / slowing down / zombie`, the date of the latest activity,
the page that proves that date, and every other signal with its link. It does this for the cleanup a sales team, an investor or a job seeker runs
before trusting a list. It also comes as an XLSX with hyperlinks and a filterable HTML report.

**Demo:** free-for-dev, a real GitHub "awesome" list of about 1,370 dev services, converted with `awesome_to_csv.py`. Run: `./demo.sh 600`.
## Live results (free-for-dev, first 600 rows)

Run on 2026-11-15 against live TinyFish. Full output: `full/o.csv`, `full/o.xlsx`, `full/o.report.html`.
Command: `python zombiecheck.py tests/free-for-dev.csv -o full/o.csv --limit 600 --agent-budget 20 --ts-max-rows 120 --ts-validate 30`.

**Verdicts (after the fixes below): 373 alive, 132 slowing down, 67 unclear, 28 zombie.**
`unclear` is a fourth verdict: the site is live but nothing on it is dated, so the tool says it cannot tell instead of guessing zombie.
Confidence high / medium / low: 289 / 171 / 140. 599 of 600 rows have an evidence link.

Method: all 600 rows checked with Fetch + Search; 20 unresolved rows escalated to the Agent API; TinySet used on the 120 hardest unresolved rows plus a 30-row random sample of confident rows as a cross-check.
TinySet: 150 rows sent, 145 matched back to the input list, 5 unmatched in the first pass.
Cross-check: 28 of 30 sampled rows agree with the Fetch/Search verdict (1 had no TinySet answer, counted as disagreement). This compares the tool with TinySet, not with ground truth. The first pass, before the fixes, scored 25 of 30.
Not covered by TinySet: about 180 unresolved rows were over the 120-row budget, and 30 rows that only became low confidence after the fixes were not sent (I did not approve more TinySet spend). They keep their Fetch/Search verdict and a lower confidence label.
Cost: not stated here. The wallet balance did not change during the run, which I cannot explain; check the TinyFish usage page.

### What the hand-check found (and what I changed)
The first pass gave 181 zombies out of 600, which is too many for a maintained list. I checked 5 high-confidence rows and then 13 of the zombies against their live pages:

- **Wrong:** Codeac.io (flagged "shut down" because a TLS note said "End of Life"), timezone.io (its page says a *different* service, WorldTimeAPI, shut down), NASdisks, instatus.com (live products with no dated pages or a stale sitemap/text date), Azure App Service (blog dates written "November 5" with no year), Calendarific.
- **Unsupported:** about 117 of the 181 zombies were live sites with no dated page, scored as dead only because nothing was dated.
- **Held up:** Reducto and Zoho Sign (alive, dated posts on the page), pyup.io, RequestBin, Dependabot, Keybase (dead or folded into an acquirer).

Fixes: a shutdown phrase now counts only if it is about the site itself (first person, or its own brand in the same sentence), and "end of life" alone no longer counts; missing dates are treated as unknown rather than zero (live site with no dated activity anywhere becomes `unclear`); a live site whose newest dated item is under 2 years old is at most "slowing down"; a blocked site is never zombie without proof; a redirect to a sibling domain (sonarcloud.io to sonarsource.com, v0.dev to v0.app) is a move, not an acquisition. 9 new unit tests.
Zombies went from 181 to 28.

**Second spot-check of the remaining zombies (9 sites re-fetched).** 4 were backed by evidence (redirect to the acquirer or a sunset notice: pyup.io, RequestBin, Dependabot, Keybase). 1 is probably wrong (Calendarific: a live product page with 2026 dates). The other 4 (Parseur, Pixela, Scaledrone, Webpushr, plus Gemfury and Hound as live pages) load fine and have no recent dated item, so "zombie" there means "no recent dated sign of life", not "proven dead". Treat the 28 as leads to check through the evidence link. The remaining 19 zombies were not hand-checked.

## How TinySet is used (and the other three endpoints)
| endpoint | role | why it is not padding |
|---|---|---|
| **TinySet** `POST /v1/datasets` | **Gap-filler on unresolved rows only.** After Fetch/Search/Agent, rows that are still blocked, undated or low/medium confidence (at most `--ts-max-rows`, default 120) are sent in batches of up to 30 as an explicit `spec` whose description is the fixed entity list (`name :: domain`). The run prints the row count and the estimated cost ($0.10/row) and asks before spending (`--yes` to skip). Other rows are labelled `skipped_resolved` or `skipped_budget` in `zc_tinyset`. It fills `still_operating, status_note, latest_update_date, latest_social_date, open_jobs, signup_open, evidence_urls` from pages its agents opened. Three runs are in flight (the account limit), and dataset ids are saved so a restart re-attaches. | It is the signal source that reads across the open web, so it is spent where the cheap path fails: social posts, third-party job boards, acquisition news. Any returned row whose name is not in the batch is dropped. |
| **Fetch** `POST api.fetch` (`ttl=0`) | Live homepage (redirects, parked, shutdown), blog, changelog, careers, sign-up, sitemap/feed, GitHub Atom feeds. **Also re-fetches every page TinySet cites to confirm its dates.** | Ground truth. A TinySet date only counts in full if the date is visible on the live page it cites. |
| **Search** `GET api.search` | Newest dated news, acquisition and shutdown headlines, social recency, and a website for rows that have no URL. | Catches "acquired by X" when the old site still loads. |
| **Agent** `POST /v1/automation/run-async` + poll `GET /v1/runs/{id}` | Escalation only. Rows Fetch can't settle (bot-blocked, JS-only, no dated activity) get a real browser run that opens the blog, careers and sign-up pages read-only. | Turns "unknown" into evidence on exactly the rows where the cheap path fails. Capped by `--agent-budget`. |

## Weighing the signals
The verdict comes from a pure function (`decide()`), not an LLM, so judges can reproduce it from the evidence column.
- **Hard gates → zombie:** domain dead, parked or for sale, shutdown or discontinued notice, archived GitHub repo, or a redirect to an unrelated domain (absorbed).
- **Otherwise a score** over the signals that could be determined. Unknowns are left out of the denominator and lower `zc_confidence`. Weights: update recency 45, social 15, open jobs 15, sign-up 15, site loads 10. "alive" also needs dated activity within 120 days or open jobs. Two quiet years caps the score at 25.
- **Provenance weighting:** our own live Fetch = 1.0, Agent browser = 0.9, TinySet confirmed on its cited page = 1.0, TinySet with page live but date not visible = 0.6 (only when we found nothing ourselves), TinySet unverifiable = 0.5 and labelled "not independently verified".

## Edge cases
| case | handling |
|---|---|
| redirect, same brand | `moved_to:<domain>`: treated as a rebrand or migration and judged on the new site |
| redirect to an unrelated domain | `absorbed`: zombie (acquired, or domain reassigned) |
| "acquired by" / "formerly" on the page or in news | flagged. An acquisition with no recent activity can't be "alive" |
| parked or for-sale domain | registrar host plus parking-page wording: zombie |
| bot-blocked | never treated as dead. Escalated to Agent, otherwise low confidence |
| nav stripped by semantic HTML | links read from Fetch `links[]`, plus probes of conventional paths |
| auto-generated sitemap (every lastmod = today) | ignored |
| GitHub repo rows | archived banner, newest commit and release from Atom feeds. github.com's own careers links are ignored |
| no URL in the row | resolved through Search (`url_resolved_by_search` flag) |
| ghost jobs (`--mode jobs`) | 404/410, "no longer accepting", expired `validThrough`, redirect to the careers index, posting age |

## Scale and resume
State lives in SQLite (`<out>.zc/state.db`): per-row results, TinySet dataset ids and verification results. SIGKILL mid-run, then re-run the same command, and it continues. TinySet runs are re-attached, not re-bought. A failing row never stops the run. 401/402/403 stop cleanly. 429/5xx retry with `Retry-After`. Client-side limits match the documented quotas. The same URL is fetched once per run. Tested: 40 unit tests, a 540-row end-to-end run with SIGKILL and resume against a local fake of all four APIs, and the live 600-row run above (resumed once after a bug fix).

## Known limits (honest)
Social recency is the weakest signal: X and LinkedIn are walled, so it is weighted 15 and marked unverified when only TinySet saw it. JS-only careers pages are escalated to Agent within the budget. TinySet is budgeted (`--ts-max-rows`, default 120 rows, about $0.10 each) and runs only on rows phase 1 could not settle, so it does not cover every row. `--no-tinyset` gives a Fetch+Search-only pass.

After the fixes: a live site with undated pages is `unclear` (not guessed), and "zombie" for an old, undated or low-activity site means no recent dated sign of life, not proven dead. Company-wide blogs flatter products inside big companies (Zoho Sign, Azure App Service). 151+ unresolved rows had no TinySet pass.
