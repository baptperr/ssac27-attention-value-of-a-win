# SSAC27 — Split-decision attention study

## Goal
Submit a research abstract to the MIT Sloan Sports Analytics Conference 2027.
Abstract due **Oct 1, 2026, 11:59 p.m. ET (= 5:59 a.m. Oct 2, Paris)**. Target: submit Sept 30.
Under 500 words, max 2 tables/figures, sections: Introduction, Methods, Results (actual), Conclusion.
All data used must be publishable in an open repo.

## The question (one sentence)
After a close fight, how much of the winner's extra attention is caused by the official W itself,
how much by having actually fought better, and how does that compare to being in a memorable fight?

## Why split decisions
Judges disagreed, so the fight was close, so the W is nearly arbitrary. This isolates the label.
"Close" is not "identical": expert scores (if available) catch the leftover performance edge.

## Variables (the only ones in this study)
| Variable | Source | Represents | Role |
|---|---|---|---|
| Wikipedia pageviews | Wikimedia pageviews API | Public information-seeking attention | Outcome |
| Official result (split decision) | Sherdog | The W label | Treatment |
| Media agreement % | MMADecisions — ONLY with written permission | Who experts think won | Performance measure |
| Fight of the Night | Wikipedia UFC event pages ("Bonus awards") | Entertainment | Second hypothesis |

Out of scope — do NOT add without a DECISIONS.md entry: fan scorecards, fight statistics
(strikes/control) as a performance measure, social media metrics, Fight Matrix.

## Definitions
- **Sample:** UFC split decisions, fight date 2015-08-30 to 2026-08-20; both fighters have an
  English Wikipedia article created >= 60 days before the fight; exclude exhibitions and results
  overturned to no contest. Current n = 314 bouts.
- **Y (per fighter):** log(mean daily views, days +2..+30, +1) − log(mean daily views, days −60..−8, +1).
  en.wikipedia, all-access, agent=user, redirects merged. Day 0 = fight date.
- **D (per bout):** Y_winner − Y_loser.
- **p (per bout):** media share agreeing with official winner − 0.5. Only bouts with >= 6 media scores.
- **S (per bout):** mean of both fighters' Y.

## The three findings
1. **Label (α):** when performance was equal, is D > 0? Model: D = α + β·p.
2. **Performance (β):** does D grow with the winner's performance edge p?
3. **Entertainment (γ):** on ALL decision bouts in the window: S ~ FOTN + split + log baseline views
   + card position + title fight + year. Observational, not causal.

If MMADecisions does NOT grant permission: drop β. Report mean D over all 314 bouts as the
attention value of a W in split decisions (an upper bound on the pure label effect), plus γ.

## Inference
Two-sided tests, 0.05, Holm correction across the confirmatory tests. Bootstrap CIs resampling bouts.
**Placebo:** D computed on window −60..−31 vs −30..−8 (both pre-fight). Expected: zero.
**Robustness:** days +31..+90; all language editions summed; drop each year in turn;
exclude main events; closing odds on the subsample that has them.

## Known numbers
5,850 UFC bouts in window · 562 split decisions · 314 in paired sample
· 36 FOTN in sample (0 unknown; 212 FOTN across all 2,662 decision bouts in the window)
· media scores for 314/314, all with >= 6 (median 16); media sided with the official winner in
  mean 63% of scores, and the media majority picked the LOSER in 103/314
· closing odds for 278/314 (Kaggle CC BY 4.0, all years) — BestFightOdds direct covers only 116/314, 2021+
· card position + title flag for 303/314
· SD of within-bout difference = 0.629 (redirects merged) → MDE ≈ 10.5% at n = 314.

## Rules for Claude Code
1. **No post-fight pageview data** until DECISIONS.md records the OSF pre-registration.
2. **Never make a methods decision silently.** If a choice isn't specified here or in DECISIONS.md,
   stop and list it under "Decisions needed" in STATUS.md.
3. **Data rights:** check robots.txt and terms before scraping. Never scrape a site that disallows it.
   Record every source and its license in `data/SOURCES.md`.
4. **Do not edit CLAUDE.md or DECISIONS.md.** Propose changes in STATUS.md; Baptiste edits.
5. **Reproducibility:** raw data is never modified; numbered scripts; fixed random seeds.
6. **End every task** by rewriting STATUS.md using its template.
