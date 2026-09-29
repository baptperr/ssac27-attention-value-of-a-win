# Status (rewritten by Claude Code at the end of every task)

## Template
- **Task:** what was asked
- **Done:** what was actually done
- **Numbers:** key counts and results
- **Deviations:** anything done differently from instructions, and why
- **Decisions needed:** choices not covered by CLAUDE.md or DECISIONS.md (stopped, not guessed)
- **Next:** what's ready to run next

---

## Current — 09-29 (results)
- **Task:** post-fight pull and the confirmatory analysis, after the OSF registration
  (10.17605/OSF.IO/DXUPH) lifted the embargo.
- **Done:** `prep/y_pageviews.py` (redirect lists, daily series per article over each fighter's
  whole span, Y/D/S sliced locally), `prep/z_analysis.py` (H1-H3, placebo, descriptive,
  bootstrap 10k seed 27, two-way clustered SEs, Holm). Repo initialised and committed with the
  MMADecisions files excluded via .gitignore, matching the PAP.
- **Numbers:**
  - **H1 alpha +0.283** (+32.7%), 95% CI [+0.169, +0.396], Holm p 2.4e-06, n = 309.
    With the control-time share added: +0.284 — the bias check does not move it; control share
    itself −0.09 (p 0.53).
  - **H2 beta +0.789**, CI [−0.224, +1.811], p 0.11 — inconclusive, as the power note predicted.
  - **H3 gamma +0.232** (+26.1%), CI [+0.146, +0.322], Holm p 1.4e-06, n = 1,508.
  - Mean D over sample B = +0.302 (+35.2%).
  - **Placebo is NOT clean: alpha +0.058** (p 0.082, CI [−0.008, +0.125]) on two pre-fight
    windows — positive, ~20% of the headline. PAP §10 requires reporting it as a threat to
    identification.
  - **Descriptive, against expectation:** FOTN losers +0.208 vs non-FOTN winners +0.379;
    **−0.142 with the H3 controls (−13.3%), p 0.0026**. Losing an entertaining fight is worth
    LESS than winning an unremarkable one.
- **Deviations:** PAP §11's single weighted p replaced by separate regressors (DECISIONS.md
  09-29, with the variance reasoning); n = 309 not 314; H3 n = 1,508 not 2,662.
- **Decisions needed:** none blocking. Worth Baptiste's judgement: how prominently the
  non-clean placebo is framed in a 500-word abstract.
- **Next:** notebook (`notebooks/abstract.ipynb`) with the two figures and the 500-word draft.

## Previous — 09-29
- **Task:** add the 09-29 β line to DECISIONS.md; review the pre-analysis plan; recover the
  missing strike bouts (plan item 4); resolve articles for the H3 sample (plan item 6).
- **Done:**
  - DECISIONS.md: 09-29 β-via-strike-share line added at Baptiste's instruction, marked as
    superseding 09-22 "media scorecards only … no fight stats" and 09-22 "no permission → drop β".
  - Strike matching extended with two fallbacks (one fighter's exact full name unique on the
    date; both surnames unique on the date) — `prep/a1_kaggle_strikes.py`.
  - H3 article resolution — `prep/h3_articles.py`: only 13 fighters were new; B and G had
    already covered 1,453 of the 1,466 fighters in decision bouts.
- **Numbers:**
  - **Strikes now 309/314 (98.4%)**, up from 298. The last 5 (2026-03-14 … 2026-05-09) are past
    the Kaggle dataset's final event (2026-03-07) and unavailable without UFCStats. **H1/H2 n = 309.**
  - p (winner's strike share − 0.5): mean +0.024, SD 0.094, range −0.32..+0.40; |p| < 0.05 in
    134 bouts. The "< 20 combined strikes" exclusion removes 0 bouts.
  - **H3 achievable n = 1,508, not 2,662** (both fighters with an article ≥ 60 days old):
    1,165 unanimous, 316 split, 25 majority, 2 technical. **FOTN within it: 147, not 212.**
    764 bouts have one eligible fighter, 390 neither — article existence, not work remaining.
- **Deviations:** DECISIONS.md edited by Claude again, on instruction (rule 4).
- **Decisions needed:** none blocking. Plan edits 7-9 (measurement error biases α not β; power
  for β; placebo as a full regression) are Baptiste's to write into the PAP — all three accepted
  in chat.
- **Next:** OSF pre-registration line into DECISIONS.md, then the post-fight pull: 309 sample
  bouts + 1,508 H3 bouts ≈ 3,600 fighter-windows, ~2 h at the observatory's pacing.

## Previous — 09-23
- **Task:** decide the four open items; update CLAUDE.md's Known numbers.
- **Done:** DECISIONS.md — three lines added at Baptiste's instruction (merged-redirect placebo
  supersedes 0.683/11%; Kaggle odds publishable with attribution to it and its upstream sources;
  sample-B definition confirmed: no Road to UFC / TUF house fights, no split draws or technical
  splits, article must be a real page at fight − 60 days). CLAUDE.md "Known numbers" replaced.
- **Numbers:** unchanged from 09-22 (late); CLAUDE.md now states them.
- **Deviations:** CLAUDE.md edited by Claude (rule 4 reserves it for Baptiste) — on his explicit
  instruction, only the Known numbers block, after showing him the replacement.
- **Decisions needed:** none open.
  - RESOLVED 09-23: **the raw MMADecisions scorecards are cleared for publication too**, by
    Baptiste's decision, recorded in SOURCES.md as WITHOUT the owner's permission (no reply to the
    09-22 email). Claude declined only to write that permission had been granted. NOTHING IS
    PUBLISHED YET: SSAC27 is not a repo; the decision takes effect if and when the open repo is
    created, which is also the last point to reconsider.
- **Next:** OSF pre-registration into DECISIONS.md, then the post-fight pageview pull for the 314
  (the last data the abstract needs). Submit target 09-30.

## Previous — 09-22 (late)
- **Task:** supersede DECISIONS.md 09-22 "Do not crawl" (Claude to add it); merge redirects and
  re-run the placebo SD.
- **Done:** two lines added to DECISIONS.md at Baptiste's instruction (crawl superseded; MDE ≈ 11%
  accepted pending the merged re-run). Redirects listed via `prep/g_redirects.py` (768 articles,
  583 redirects), their pre-fight windows fetched and merged via `prep/g_merge.py` (1,786 windows,
  strict −60..−8, no out-of-window day returned).
- **Numbers:** placebo SD **0.629** with redirects merged (was 0.683 on the current title only);
  bouts 1,116 (was 1,048; 68 of 103 empty ones recovered); redirects = 6.0% of all window views.
  **MDE at n = 314: 0.099 log points ≈ 10.5%** (was 11.4%). Random corner order: SD 0.631.
- **Deviations:** redirect lists came from `/w/api.php` (the same robots-disallowed endpoint as the
  creation dates; see SOURCES.md and deviation 3 below).
- **Decisions needed:** none new. The 11% already accepted holds (10.5%). Proposed CLAUDE.md
  "Known numbers": SD of within-bout difference = 0.629 (redirects merged) → MDE ≈ 10.5%.
- **Next:** unchanged — nothing post-fight before the OSF pre-registration is in DECISIONS.md.

## Previous — 09-22 (evening)
- **Task:** fix the 9 unmatched media bouts; assess the Kaggle dataset; explain the power SD;
  delete the empty `prep/STATUS.md`.
- **Done:**
  - Media: **all 314 matched** (15 new pages). Causes: 5 on TUF Finales the site titles
    "TUF … Finale" (no "UFC"); 4 name variants (Oleinik, ONeill, OMalley, "Khaos" Williams) →
    matched on one fighter's exact full name, unique on the card (flagged `match = one fighter`).
    Picks now classified against the site's own surnames (fixes "Saint Preux", "Carlos
    Junior", "O'Neill", and Bradley Scott vs Scott Askham): 0 unclear.
  - Kaggle quality check, `prep/k_kaggle_quality.py` (read-only).
  - `prep/STATUS.md` (empty) deleted.
- **Numbers:**
  - Media: **314/314 bouts with ≥ 6 scores** (min 6, median 16); 5,197 picks: 3,265 winner /
    1,804 loser / 128 draw. Official winner's media share: mean 0.632, median 0.722. Media
    majority picked the official loser in **103/314**, exactly split in 5.
  - Kaggle odds (mdabbert): winner agrees with Sherdog in 4,761/4,763 matched UFC bouts;
    calibrated like real market prices (overround 1.04; favourites win 66.3%); vs observatory
    BFO-closing on 48 overlapping 2026 bouts: r = 0.996, median |Δ prob| 0.031 → near-closing,
    not provably closing.
- **Deviations:** none new. (MMADecisions: 15 more pages fetched under the same instruction as
  before; see below.)
- **Decisions needed:** unchanged from the list below — #1 (supersede DECISIONS.md 09-22) is now
  more pressing, since β's data exists for all 314 bouts.
- **Next:** re-run G with redirects merged; nothing post-fight before OSF pre-registration.

## Previous — 09-22 (afternoon)
- **Task:** (1) UFCStats sig. strikes for B; (2) resolve 8 unknown FOTN; (3) FOTN + card position
  for all decision bouts in window; (4) Kaggle "Ultimate UFC Dataset" odds + licence; (5) no
  post-fight pageviews; (6) MMADecisions crawl; + move "Outcome = en.wikipedia pageviews" to
  Confirmed in DECISIONS.md.
- **Done:**
  - (1) ufcstats.com serves a JS bot challenge on every page → not accessed. Strikes taken from
    Kaggle jossilva3110 (MIT) → `data/b_sig_strikes.csv`. A second Kaggle copy (leandroiber)
    was rejected: it pins strikes on the wrong fighter in ~1/3 of fights (on 1,001 KO wins it
    gives the winner fewer strikes 854 times).
  - (2) All 8 resolved from TUF season pages / an "award:" wording; plus UFC 225
    Whittaker–Romero 2 had been wrongly "no" → it was FOTN. `prep/c2_fotn_unknowns.py`.
  - (3) `data/decision_bouts.csv`, `prep/d_decision_bouts.py`.
  - (4) `data/e_kaggle_odds_coverage.csv`, `prep/e2_kaggle_odds.py`.
  - (5) Still none pulled.
  - (6) Crawled on Baptiste's explicit instruction; `data/b_media_scores.csv` (+ `_long.csv`).
  - DECISIONS.md: outcome line added under Confirmed at Baptiste's instruction; the Pending line
    struck through, not deleted (append-only rule).
  - `data/SOURCES.md` written (every source + licence), as rule 3 requires.
- **Numbers:**
  - Sample B: 314 · FOTN in B: **36** (0 unknown; was 33 + 8 unknown)
  - All decision bouts in window: 2,662 · FOTN 212 (unanimous 155/2,084 = 7.4%, split 48/528,
    majority 9/42). Rate is capped by design: ≤1 FOTN per ~12-bout card, and 108/453 events
    awarded none ("No bonus awarded", verified in Wikipedia's text). Card position known 2,511/2,662.
  - Odds (Kaggle mdabbert, CC BY 4.0): **278/314 (88.5%)**, every year 2015+ — vs 116/314 from
    BestFightOdds. Opening vs closing line not documented by the dataset.
  - Sig. strikes: 298/314; winner's median share 51.8%; winner out-landed loser in 60%.
  - Media scores: **305/314 with ≥ 6** (the p threshold) · median 16 per bout · in 101/305 the
    media majority picked the official LOSER. 9 bouts unmatched (see Next).
- **Deviations:**
  1. **MMADecisions was crawled** despite CLAUDE.md rule 3 ("never scrape a site that disallows
     it") and DECISIONS.md 09-22 ("Do not crawl"). Instructed twice in chat; the second time
     after Claude stopped the crawl and quoted DECISIONS.md. 544 pages, 1 req/5 s, contact UA
     naming the pending permission request, no block met. Data NOT publishable until the owner
     says yes.
  2. **Fight statistics (sig. strikes) were collected** though CLAUDE.md lists them out of scope
     and DECISIONS.md 09-22 rejects them as a performance measure. Requested in chat item 1.
     Not used in any model.
  3. **Wikipedia creation dates and page-state checks used `en.wikipedia.org/w/api.php`**, which
     robots.txt disallows for generic crawlers (authorised in chat 09-20, before CLAUDE.md
     existed). Same rule-3 tension; see SOURCES.md.
  4. **DECISIONS.md edited by Claude** (rule 4 says Baptiste only) — at Baptiste's explicit
     instruction, one line added, nothing deleted.
- **Decisions needed:**
  1. **Supersede DECISIONS.md 09-22 "Do not crawl MMADecisions"** with a new line (only you can),
     or tell me to delete `data/mmad_cache/` and the media-score CSVs until permission arrives.
  2. **If the owner says no:** per DECISIONS.md, β is dropped — does the crawled data get deleted?
  3. **Odds source:** Kaggle CC BY 4.0 (278/314) derives from BestFightOdds, which grants no
     licence. Is that "publishable in an open repo"? Proposal: use for robustness, publish only
     derived statistics, not the raw lines.
  4. **Sample-definition choices made while building B, not in CLAUDE.md:** (a) Road to UFC and
     TUF house fights excluded as non-UFC-card; (b) split *draws* (13) and *technical* split
     decisions (2) excluded; (c) article must be a real page, not a redirect, at fight − 60 days
     (removed 2 bouts). Proposal: confirm all three.
  5. **Placebo SD (0.683) was computed without merging redirects**; CLAUDE.md's Y says "redirects
     merged". 103/1,151 unanimous bouts were dropped for empty windows (likely renamed titles).
     Proposal: re-run G with redirect merging before relying on the MDE.
  6. **CLAUDE.md "Known numbers" are stale** — proposed replacement: "… 36 FOTN in sample (0 unknown) ·
     odds for 278/314 (Kaggle) or 116/314 (BFO, 2021+) · media ≥6 scores for 305/314 · card
     position for 303/314 · SD 0.683 → MDE ≈ 11%".
  7. DECISIONS.md Pending "Closing odds: robustness only (116/314, all 2021+)" — coverage is now
     278/314 across all years; still robustness-only?
- **Next:**
  - ~~Fix the 9 unmatched media bouts~~ → done (evening).
  - Re-run G with redirects merged (decision 5).
  - Nothing post-fight until the OSF pre-registration is in DECISIONS.md.
  - Stray empty file `prep/STATUS.md` (from an earlier nano) — safe to delete.
