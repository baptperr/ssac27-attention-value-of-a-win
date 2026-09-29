# Data sources and licences

Every source this project has touched, how it was accessed, and what it permits.
Checked 2026-09-21/22. Verbatim licence/terms text: `e_licenses.md`. Not legal advice.

"Publishable" = may go in the open repo per CLAUDE.md ("All data used must be
publishable in an open repo").

| Source | Used for | Access | robots.txt / terms | Licence | Publishable? |
|---|---|---|---|---|---|
| Sherdog (via the observatory DB) | bouts, results, methods, dates | observatory's robots-checked client | allowed | none stated | facts (results) yes; cite |
| Wikipedia event & article pages (`/wiki/`) | FOTN, card position, title flag | `/wiki/<Title>` via observatory client | allowed | CC BY-SA 4.0 | yes, with attribution |
| Wikidata (`Special:EntityData`) | fighter QID + Sherdog id (P2818) | allowed path | allowed | CC0 | yes |
| Wikimedia pageviews REST API | pre-fight pageviews (G) | `wikimedia.org/api/rest_v1` | allowed | CC0 | yes |
| **en.wikipedia `/w/api.php`** | article creation dates; page state at cutoff | direct, 1 req/s, contact UA | **robots.txt disallows `/w/` for generic crawlers** | CC BY-SA (content) | see Deviations in STATUS.md |
| BestFightOdds | odds coverage (E) | observatory client | allowed | **none granted** (warranty disclaimer only) | **raw odds: no** without permission |
| Kaggle mdabbert/ultimate-ufc-dataset | odds (E) | Kaggle API, operator login | Kaggle ToS | CC BY 4.0 — odds derive from BestFightOdds, which grants no licence | **yes** (DECISIONS.md 09-23); attribute the dataset AND ufcstats.com / bestfightodds.com |
| Kaggle jossilva3110/ufc-dataset-1994-2026 | sig. strikes | Kaggle API | Kaggle ToS | MIT — data derive from ufcstats.com | licence allows it, but the study does not use these (fight stats are out of scope per CLAUDE.md) |
| Kaggle leandroiber/ufc-stats-complete-dataset | nothing (rejected) | Kaggle API | — | CC0 | not used: misattributes strikes |
| UFCStats (ufcstats.com) | nothing | 4 requests, all got a bot challenge | no robots.txt; JS bot challenge on every page | — | not accessed |
| **MMADecisions** | media scorecards (D) | **crawled 2026-09-22 on Baptiste's explicit chat instruction** (repeated after DECISIONS.md 09-22 was pointed out): 559 pages, 1 req/5s, contact UA naming the permission request; no block encountered | **`User-agent: * / Disallow: /`** | none | **Cleared for publication by Baptiste (09-23) WITHOUT the owner's permission; NOT yet published** — see the note below |

## Note on the MMADecisions data (`b_media_scores.csv`, `b_media_scores_long.csv`)

State of the permission, stated plainly because provenance is what a reader relies on:

- `mmadecisions.com/robots.txt` is `User-agent: *` / `Disallow: /` — it asks every crawler
  except a named list of search engines not to fetch anything.
- Baptiste emailed the site owner asking for permission on 2026-09-22. **As of 2026-09-23 there
  has been no reply.** Nothing here should be read as the owner having agreed.
- The crawl was run anyway, on Baptiste's explicit instruction, after being advised against it:
  559 pages, one request every 5 seconds, a User-Agent naming the study and the pending request,
  only the pages the sample needs, everything cached so no page was fetched twice. The crawler
  was written to stop on any 403, 429 or bot challenge; none occurred.
- **Both files are cleared for publication by Baptiste's decision of 2026-09-23, without
  permission. Nothing has been published yet: SSAC27 is not a repository, so these files exist
  only on the operator's machine. Publication happens if and when the open repo is created.**
- The underlying scores are the work of the media outlets named in each row and of MMADecisions,
  which compiled them. Cite both. If the owner objects or later declines, the honest response is
  to withdraw these two files; the derived results do not depend on republishing them.
