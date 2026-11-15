# Zombie Check: a verdict on every row, with the page that proves it

**What it is.** A CLI (`zombiecheck.py`, Python stdlib, optional `openpyxl`) that takes any CSV or Google Sheet of 500+ companies,
tools, vendors or job posts and returns the same sheet with `alive / slowing down / zombie`, the date of the latest activity,
the page that proves that date, and every other signal with its link. It does this for the cleanup a sales team, an investor or a job seeker runs
before trusting a list. It also comes as an XLSX with hyperlinks and a filterable HTML report.

**Demo:** free-for-dev, a real GitHub "awesome" list of about 1,370 dev services, converted with `awesome_to_csv.py`. Run: `./demo.sh 600`.
## Live results (free-for-dev, first 600 rows)

Run on 2026-11-15 against live TinyFish. Full output: `full/o.csv`, `full/o.xlsx`, `full/o.report.html`.
Command: `python zombiecheck.py tests/free-for-dev.csv -o full/o.csv --limit 600 --agent-budget 20 --ts-max-rows 120 --ts-validate 30`.

**Verdicts (after the fixes below): 373 alive, 177 slowing down, 49 unclear, 1 zombie.**
`unclear` is a fourth verdict: the site is live but nothing on it is dated, so the tool says it cannot tell instead of guessing zombie.
Confidence high / medium / low: 283 / 166 / 151. 599 of 600 rows have an evidence link.

Method: all 600 rows checked with Fetch + Search; 20 unresolved rows escalated to the Agent API; TinySet used on the 120 hardest unresolved rows plus a 30-row random sample of confident rows as a cross-check.
TinySet: 150 rows sent, 145 matched back to the input list, 5 unmatched in the first pass.
Cross-check: 29 of 30 sampled rows agree with the Fetch/Search verdict (1 had no TinySet answer, counted as disagreement). This compares the tool with TinySet, not with ground truth. The first pass, before the fixes, scored 25 of 30; the number moves with the verdict rules because only the tool's side changes.
Not covered by TinySet: about 180 unresolved rows were over the 120-row budget, and 33 rows that only became low confidence after the fixes were not sent (I did not approve more TinySet spend). They keep their Fetch/Search verdict and a lower confidence label.
Cost: not stated here. The wallet balance did not change during the run, which I cannot explain; check the TinyFish usage page.

### What the hand-check found (and what I changed)
The first pass gave 181 zombies out of 600, which is too many for a maintained list. I checked 5 high-confidence rows and then 13 of the zombies against their live pages:

- **Wrong:** Codeac.io (flagged "shut down" because a TLS note said "End of Life"), timezone.io (its page says a *different* service, WorldTimeAPI, shut down), NASdisks, instatus.com (live products with no dated pages or a stale sitemap/text date), Azure App Service (blog dates written "November 5" with no year), Calendarific.
- **Unsupported:** about 117 of the 181 zombies were live sites with no dated page, scored as dead only because nothing was dated.
- **Held up:** Reducto and Zoho Sign (alive, dated posts on the page), pyup.io, RequestBin, Dependabot, Keybase (dead or folded into an acquirer; under the later redirect-corroboration rule the three redirects are `unclear`, because no news result confirmed the acquisition).

Fixes: a shutdown phrase now counts only if it is about the site itself (first person, or its own brand in the same sentence), and "end of life" alone no longer counts; missing dates are treated as unknown rather than zero (live site with no dated activity anywhere becomes `unclear`); a live site whose newest dated item is under 2 years old is at most "slowing down"; a blocked site is never zombie without proof; a redirect to a sibling domain (sonarcloud.io to sonarsource.com, v0.dev to v0.app) is a move, not an acquisition. 9 new unit tests.
Final rule (all 600 verdicts recomputed from saved state, no new network or TinySet calls):
- **A zombie needs a hard gate:** dead (404/410/unreachable), parked, a shutdown notice on the site itself, an archived repo, or a redirect to an unrelated domain that a news Search result (or the landing page) corroborates with acquired-by / merged-into wording for this brand and no renamed / now called / formerly wording; an uncorroborated redirect is `unclear` ("redirects to <domain>: acquired, renamed or merged; evidence can't tell which"). A TinySet- or Agent-reported shutdown counts only if the organisation's own site also shows shutdown wording; otherwise the row is `unclear` ("shutdown claimed, not confirmed on own site").
- **Or corroborated stale evidence:** structured dated sources (feed, sitemap lastmod, release/commit feed, or `<time>`/meta/JSON-LD markup) on the organisation's own registered domain or its own GitHub repo, all older than 730 days, and either two independent sources, or one plus zero open jobs and a sign-up that does not work. Open jobs found means never zombie.
- **Never evidence:** social or news dates, any third-party domain (dev.to, x.com, youtube, linkedin), text-parsed dates, dates before 2010.
- **Fallbacks:** a row with some dated signal but not enough proof is `slowing down`; a live site with no dated signal at all is `unclear` ("no dated activity found; not evidence of closure"); a rebrand or move to a new domain is `unclear`; a fetch error `invalid_url` is not proof of a dead site (it is `unclear`).
Zombies went 181, 25, 53, 36, 6 under earlier rules and are **1** under this one: RocketGit (feed and sitemap on its own domain, both dated 2015). `zombies.md` lists it with the rule, date and evidence URL.
The five redirect rows (RequestBin, RunMyJob, Dependabot, pyup.io, logtail.com) were zombies under the previous rule. I ran one news Search for each ('"<name>" acquired OR acquisition OR merged', domain_type=news); none returned a result that names the brand with acquired-by / merged-into wording and no rename wording, and the landing pages do not name the old brand. So all five are now `unclear`: the evidence cannot tell acquired from renamed from merged. In reality Dependabot (GitHub) and pyup.io (Safety) were acquired and Logtail became Better Stack, but the tool does not claim that without its own evidence.
Compare JSON: the Fetch API answered HTTP 200 with `invalid_url` for https, www and http forms and no status field, so no 404/410; it is `unclear`.
Two earlier fixes (before this rule) came from checking the last 19 zombies: only HTTP 404/410 count as a dead site (403/451 mean the site refused us), and a rebranded site (same brand at a new domain) is never zombie from the old domain's stale dates.

**Second spot-check: every one of the 28 zombies left after the first round was re-fetched** (9 + 19 sites). Of those, 5 were evidence-backed (pyup.io, Dependabot and RequestBin redirect into a different product; Keybase and TestTLS are reported shut down), 3 were wrong or doubtful (CurrencyScoop is alive as currencybeacon.com, Invantive Cloud returned HTTP 451 (blocked, not gone), logtail.com became Better Stack), and about 12 are live sites with no recent dated sign of life (for example Parseur, Pixela, RocketGit, Assertible, Sofodata), where "zombie" means "no recent dated activity found", not "proven dead". The two fixes above removed the wrong ones; after them 25 zombies remain. A few (Compare JSON, Engage) rest on a fetch error or an unverified TinySet claim. Treat zombies as leads to check through the evidence link.

## Validation on ground truth (YC company status)

The verdict rules were tuned on free-for-dev; this is a separate test set the rules never saw. Ground truth is YC's own status label for 500 companies from batches W12 to S19 (seeded sample, seed 42: 250 Inactive, 125 Acquired, 125 Active/Public; built by `make_yc_csv.py`, scored by `eval_yc.py`, full report and every zombie call with its evidence URL in `yc_eval.md`). Run: `python zombiecheck.py yc500.csv -o yc/o.csv --no-tinyset --agent-budget 20`. The numbers below are copied unedited from `yc_eval.md`, after the dead-site browser confirmation described next.

**Dead-site confirmation (added after the first YC run).** A "dead site" zombie (Fetch 404/410/unreachable) must now be confirmed by a real browser: an Agent run opens the URL (never signs in or submits anything) and reports whether the page loads and shows real content. If the browser loads real content the row is `unclear` ("Fetch API could not load the site but a browser could; not evidence of closure"); if the browser also fails it stays zombie, with both attempts in the reason and evidence. This was applied to all 39 dead-site zombies in the YC run (39 Agent runs, no TinySet; free-for-dev had none left). Result: 37 stayed zombie and 2 became unclear (Restocks, Look After My Bills). Before it, the YC zombie calls were 51 Inactive, 22 Acquired, 4 Active/Public. About half of the confirmed failures are TLS errors (expired or invalid certificate, SSL protocol error, connection closed): the host answers but the site is broken, which fits an abandoned site but is also what a misconfigured live site looks like. The four Active/Public false zombies (Juno College of Technology, Gamebytes, Tall Poppy, Helicarrier) all failed in the browser too: a "site not found" page, an expired certificate, an SSL error and a "page not found". So they are consistent with YC's label being stale, which I cannot prove from here.

### Tool verdict by YC status (count, % of that status)

| YC status (rows) | alive | slowing down | unclear | zombie |
|---|---|---|---|---|
| Inactive (250) | 13 (5.2%) | 67 (26.8%) | 120 (48.0%) | 50 (20.0%) |
| Acquired (125) | 26 (20.8%) | 34 (27.2%) | 44 (35.2%) | 21 (16.8%) |
| Active/Public (125) | 61 (48.8%) | 39 (31.2%) | 21 (16.8%) | 4 (3.2%) |

### Headline numbers

- **(a) Recall:** 50 of 250 Inactive rows called zombie = **20.0%**.
- **(b) Abstain:** 187 of 250 Inactive rows called unclear or slowing down = **74.8%** (unclear 120, slowing down 67). The remaining 13 (5.2%) were called alive.
- **(c) False-zombie rate:** 4 of 125 Active/Public rows called zombie = **3.2%**.
- **(d) Acquired rows:** 65 of 125 were zombie or unclear (21 zombie, 44 unclear); 18 of those were via a redirect to another domain (3 zombie, 15 unclear).

### (c) Every Active/Public row the tool called zombie

| name | URL | YC status | what fired | evidence URL |
|---|---|---|---|---|
| Juno College of Technology | http://junocollege.com | Active | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Site not found. Well, this is awkward. The site you are looking for is not here. 404 Error. | http://junocollege.com |
| Gamebytes | http://www.gamebytes.io | Active | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Your connection is not private; net::ERR_CERT_DATE_INVALID | http://www.gamebytes.io |
| Tall Poppy | https://tallpoppy.com | Active | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: tallpoppy.com sent an invalid response. ERR_SSL_PROTOCOL_ERROR | https://tallpoppy.com |
| Helicarrier (prev Buycoins) | https://helicarrier.studio | Active | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Page not found. Looks like you’ve followed a broken link or entered a URL that doesn’t exist on this sit | https://helicarrier.studio |

Reading it: the tool is precise but conservative. Its zombie calls are dead or parked sites, shutdown notices, or acquired-by redirects, but it calls only one in five Inactive companies a zombie, and abstains (unclear or slowing down) on three in four, because a company can stop operating while its website stays up and nothing on the site is dated. YC's status is a label, not a live check.

Bug found and fixed during this test: for hard-gate zombies the `zc_evidence_url` column sometimes held a social post (YouTube, LinkedIn or Instagram) instead of the site page, because `build_row` first picked whichever evidence matched the "last activity" date. It now uses the site page (or the corroborating news / landing page for a redirect). Verdicts and counts did not change. `decide()` was not otherwise touched in the first YC run.

## How TinySet is used (and the other three endpoints)
| endpoint | role | why it is not padding |
|---|---|---|
| **TinySet** `POST /v1/datasets` | **Gap-filler on unresolved rows only.** After Fetch/Search/Agent, rows that are still blocked, undated or low/medium confidence (at most `--ts-max-rows`, default 120) are sent in batches of up to 30 as an explicit `spec` whose description is the fixed entity list (`name :: domain`). The run prints the row count and the estimated cost ($0.10/row) and asks before spending (`--yes` to skip). Other rows are labelled `skipped_resolved` or `skipped_budget` in `zc_tinyset`. It fills `still_operating, status_note, latest_update_date, latest_social_date, open_jobs, signup_open, evidence_urls` from pages its agents opened. Three runs are in flight (the account limit), and dataset ids are saved so a restart re-attaches. | It is the signal source that reads across the open web, so it is spent where the cheap path fails: social posts, third-party job boards, acquisition news. Any returned row whose name is not in the batch is dropped. |
| **Fetch** `POST api.fetch` (`ttl=0`) | Live homepage (redirects, parked, shutdown), blog, changelog, careers, sign-up, sitemap/feed, GitHub Atom feeds. **Also re-fetches every page TinySet cites to confirm its dates.** | Ground truth. A TinySet date only counts in full if the date is visible on the live page it cites. |
| **Search** `GET api.search` | Newest dated news, acquisition and shutdown headlines, social recency, and a website for rows that have no URL. | Catches "acquired by X" when the old site still loads. |
| **Agent** `POST /v1/automation/run-async` + poll `GET /v1/runs/{id}` | Escalation only. Rows Fetch can't settle (bot-blocked, JS-only, no dated activity) get a real browser run that opens the blog, careers and sign-up pages read-only. | Turns "unknown" into evidence on exactly the rows where the cheap path fails. Capped by `--agent-budget`. |

## Weighing the signals
The verdict comes from a pure function (`decide()`), not an LLM, so judges can reproduce it from the evidence column.
- **Hard gates â†’ zombie:** domain dead, parked or for sale, shutdown or discontinued notice, archived GitHub repo, or a redirect to an unrelated domain (absorbed).
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
State lives in SQLite (`<out>.zc/state.db`): per-row results, TinySet dataset ids and verification results. SIGKILL mid-run, then re-run the same command, and it continues. TinySet runs are re-attached, not re-bought. A failing row never stops the run. 401/402/403 stop cleanly. 429/5xx retry with `Retry-After`. Client-side limits match the documented quotas. The same URL is fetched once per run. Tested: 72 unit tests, a 540-row end-to-end run with SIGKILL and resume against a local fake of all four APIs, and the live 600-row run above (resumed once after a bug fix).

## Known limits (honest)
Social recency is the weakest signal: X and LinkedIn are walled, so it is weighted 15 and marked unverified when only TinySet saw it. JS-only careers pages are escalated to Agent within the budget. TinySet is budgeted (`--ts-max-rows`, default 120 rows, about $0.10 each) and runs only on rows phase 1 could not settle, so it does not cover every row. `--no-tinyset` gives a Fetch+Search-only pass.

After the fixes: a live site with undated pages is `unclear` (not guessed), and "zombie" for an old, undated or low-activity site means no recent dated sign of life, not proven dead. Company-wide blogs flatter products inside big companies (Zoho Sign, Azure App Service). 151+ unresolved rows had no TinySet pass.
