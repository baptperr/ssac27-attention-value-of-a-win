# The attention value of a win in mixed martial arts

Data and code for an MIT Sloan Sports Analytics Conference 2027 abstract.

**Pre-registered before any post-fight outcome data was collected:**
[10.17605/OSF.IO/DXUPH](https://doi.org/10.17605/OSF.IO/DXUPH)

## The question

After a close fight, the winner gets more public attention than the loser. How much of
that gap is caused by the official win itself, how much by having performed better, and
how does either compare with being in an entertaining fight?

Split decisions are the natural experiment: the judges disagreed, so performance was
near-equal, while the official label is close to arbitrary.

## Findings

| | Estimate | 95% CI |
|---|---|---|
| **α** — the win label, at equal striking output | **+0.283 log points (+33%)** | 0.169 – 0.396 |
| **β** — return to out-striking (per unit of share) | +0.789, inconclusive | −0.224 – 1.811 |
| **γ** — Fight of the Night | **+0.232 log points (+26%)** | 0.146 – 0.322 |

α and γ are not distinguishable from each other (α − γ = +0.05, CI −0.10 to +0.20).
A placebo on two pre-fight windows returns +0.06 (CI −0.01 – 0.13), so α should be read
net of it. Losing a Fight of the Night is worth 15% *less* than winning an unremarkable
fight, not more.

## Layout

```
prep/        numbered-by-letter scripts, in the order they run
data/        their outputs, plus data/SOURCES.md — every source and its licence
notebooks/   abstract.ipynb — the two figures and the abstract
figures/     the figures at 300 dpi
CLAUDE.md    the study's own rules (scope, data rights, reproducibility)
DECISIONS.md append-only decision log, including every deviation from the plan
STATUS.md    running record of what was done, with deviations
```

Reproduce from a Postgres copy of the First Light Observatory (bout records) plus the
public APIs named in `data/SOURCES.md`:

```
prep/a_sanity.py         bout universe and integrity checks
prep/b_articles.py       fighter → Wikipedia article, creation dates
prep/b_sample.py         the paired sample
prep/c_wiki_cards.py     Fight of the Night, card position, title flags
prep/y_pageviews.py      daily pageviews, redirects merged
prep/z_analysis.py       H1–H3, placebo, bootstrap, clustered errors, Holm
prep/r_robustness.py     year drops, main events, odds control
prep/r_window90.py       the +31..+90 outcome window
```

`data/y_daily.csv` (~45 MB of raw daily pageviews) is not committed; `y_pageviews.py`
regenerates it from the Wikimedia API. Everything derived from it is committed.

## Data, licences and attribution

Full detail, including the exact terms checked and when, is in
[`data/SOURCES.md`](data/SOURCES.md). In short:

- **Wikipedia / Wikimedia pageviews** — article text CC BY-SA 4.0; pageview counts CC0.
- **Wikidata** (P2818, Sherdog ID ↔ article) — CC0.
- **Sherdog** — bout records, used as facts, cited not redistributed wholesale.
- **Kaggle, "Ultimate UFC Dataset" by mdabbert** — closing odds. Licensed
  **CC BY 4.0**; its own upstream sources are ufcstats.com and bestfightodds.com.
  <https://www.kaggle.com/datasets/mdabbert/ultimate-ufc-dataset>
- **Kaggle, "UFC Dataset (1994–2026)" by jossilva3110** — significant strikes,
  takedowns and control time. Licensed **MIT**; scraped from ufcstats.com.
  <https://www.kaggle.com/datasets/jossilva3110/ufc-dataset-1994-2026>
- **Kaggle, "UFC Stats Complete Dataset" by leandroiber** (CC0) — obtained but **not
  used**: it attributes strikes to the wrong fighter in about a third of fights (on
  1,001 knockout wins it gives the winner fewer strikes 854 times). Kept only as the
  evidence for that rejection.
- **MMADecisions** — media scorecards were collected on 2026-09-22 and are **not used
  in this study and not included in this repository**. The site's robots.txt disallows
  automated collection; permission was requested and had not been granted. See
  `data/SOURCES.md` for the full account.

## Licence

Code in `prep/` and `notebooks/`: MIT (`LICENSE`).
Data produced by this study in `data/` and `figures/`: CC BY 4.0 — attribute this
repository, and attribute the upstream sources listed above, whose own terms continue
to apply to anything derived from them.
