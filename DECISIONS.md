# Decision log (append-only)

Format: date — decision — who — why. Only Baptiste adds lines. Never delete; supersede with a new line.

## Confirmed
- 09-19 — Study: split decisions as a natural experiment on attention; chosen over a rating paper — Baptiste — novel, feasible by Oct 1, public data
- 09-19 — Kill switch: no mapping + pageviews + usable sample by day 4 → stop, publish as content — Baptiste
- 09-20 — Hypotheses are two-sided; framed as a horse race (label vs performance vs entertainment), not a prediction — Baptiste — avoid presetting my own thesis
- 09-21 — Three findings: α (label), β (performance edge), γ (entertainment/FOTN) — Baptiste
- 09-22 — Do not crawl MMADecisions (robots.txt disallows); email for permission — Baptiste — data rights + open-source rule + future relationship
- 09-22 — Performance measure = expert (media) scorecards only. No fan scorecards (popularity bias), no fight stats (damage vs control weighting unresolvable by Oct 1; must be round by round) — Baptiste — no ground truth exists, so choose by source validity
- 09-22 — If no MMADecisions permission: drop β; report mean D (label + residual edge) and γ — Baptiste
- 09-22 — Round-by-round performance model (synthetic judge) = candidate full-paper extension, not abstract — Baptiste
- 09-22 — Outcome = English Wikipedia pageviews; social media named as future work (no public historical follower data) — Baptiste — confirmed from Pending (added by Claude at Baptiste's instruction)
- 09-22 — SUPERSEDES 09-22 "Do not crawl MMADecisions": crawl MMADecisions for sample B's media scores while the permission email is pending (done: 1 req/5 s, contact UA naming the request; 314/314 bouts) — Baptiste — instructed in chat; under CLAUDE.md's open-repo rule the data stays unpublished until the owner grants permission (added by Claude at Baptiste's instruction)
- 09-22 — Power: MDE ≈ 11% (placebo SD 0.683, unanimous bouts) accepted; placebo to be re-run with redirects merged, per Y's definition — Baptiste (added by Claude at Baptiste's instruction)
- 09-23 — Placebo re-run with redirects merged: SD 0.629 over 1,116 bouts → MDE ≈ 10.5% at n = 314. Supersedes the 0.683/11% figures — Baptiste (added by Claude at Baptiste's instruction)
- 09-23 — Kaggle "Ultimate UFC Dataset" (mdabbert, CC BY 4.0) is publishable in the open repo; cite it and its own upstream sources (ufcstats.com, bestfightodds.com) — Baptiste — checked: winner agrees with Sherdog 4,761/4,763, market-calibrated, r = 0.996 vs BFO closing lines (added by Claude at Baptiste's instruction)
- 09-23 — Sample B definition confirmed: exclude Road to UFC and The Ultimate Fighter house fights (not UFC cards); exclude split DRAWS (13) and TECHNICAL split decisions (2); a fighter's article must have been a real page, not a redirect, at fight − 60 days (dropped 2 bouts) — Baptiste (added by Claude at Baptiste's instruction)
- 09-29 — OSF pre-registration completed: **10.17605/OSF.IO/DXUPH**; the post-fight pageview embargo (CLAUDE.md rule 1) is lifted — Baptiste (added by Claude at Baptiste's instruction)
- 09-29 — The PAP §11 "weighted alternative p" is built as SEPARATE regressors, D = α + b1·(strike share − 0.5) + b2·(control share − 0.5), not as one averaged index; takedowns excluded (defined in only 244/309 bouts, collinear with control) — Baptiste — a single averaged index fails on these data: strike share SD 0.094 vs takedown 0.433 and control 0.359, so the lumpy components dominate; being negatively correlated they partly cancel, leaving the composite correlated −0.18 with the strike share and disagreeing on who led in 174/309 bouts. Deviation from the registered plan, reportable under §15 (added by Claude at Baptiste's instruction)
- 09-29 — Trained judge weights (fightscorer RoundScorer) NOT used to weight p — Baptiste/Claude — they are fitted to predict the judges' own decisions, so p would partly encode the official result that H1 measures; they are also standardised per-SD (no raw exchange rate exists to read off) and MMADecisions-derived (added by Claude at Baptiste's instruction)
- 09-29 — α reported from the primary model AND alongside the control/takedown-weighted p (PAP §11 promoted into the main result), so the reader sees which way α moves as p improves — Baptiste — measurement error in p pushes performance effects into the intercept, which is H1 (added by Claude at Baptiste's instruction)
- 09-29 — β measured via significant-strike share, not MMADecisions or the synthetic judge — Baptiste — MMADecisions unreachable/no rights; synthetic judge inherits MMADecisions training data and is unvalidated for this deadline (added by Claude at Baptiste's instruction; SUPERSEDES 09-22 "Performance measure = expert (media) scorecards only … no fight stats" and 09-22 "If no MMADecisions permission: drop β")

## Pending (proposed by Claude, not yet confirmed)
- ~~Outcome = English Wikipedia pageviews; social media named as future work (no public historical follower data)~~ → confirmed 09-22, see above
- Minimum 6 media scores per bout (MMADecisions' own published threshold)
- γ estimated on all decision bouts, split indicator as control; splits-only as robustness
- γ controls: log baseline views, card position, title fight, year
- Closing odds: robustness only, not in confirmatory models (116/314 coverage, all 2021+)
- Significance: 0.05 two-sided, Holm across confirmatory tests
- Windows: baseline −60..−8, outcome +2..+30, secondary +31..+90
