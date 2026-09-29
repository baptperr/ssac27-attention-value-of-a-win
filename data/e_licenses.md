# E. Closing-odds sources — licence record

Captured 2026-09-21 14:49 UTC.

## BestFightOdds (bestfightodds.com)

**robots.txt** (full file, as served):

```
User-agent: *
Allow: /

Sitemap: https://www.bestfightodds.com/sitemap.xml
Sitemap: https://www.bestfightodds.com/news-sitemap.xml
```

**Terms of service** — https://www.bestfightodds.com/terms, full substantive text,
verbatim (the typo "expressely" is in the original):

> Although the service is designed to give accurate information it is provided on
> an "as is" and "as available" basis. We expressely disclaim any and all
> warranties, express or implied, including any warranties as to the availability,
> accuracy or content of the information.

**Reading:** access is permitted (robots allows all agents; the terms place no
restriction on automated access or reuse). But **no licence is granted** — the terms
are a warranty disclaimer only. Nothing here gives permission to redistribute BFO's
odds tables. Reading them and reporting derived statistics is one thing;
publishing the raw lines alongside the paper is another, and would warrant asking
BFO first. Not legal advice.

**Historical depth:** a settled event's page serves each still-listed book's last
posted line (i.e. its closing line). Older events serve the fight list with no
lines at all — spot checks: 2018-06 none; 2021-06 lines from 3 books; 2023+ lines
from 5–6 books, sometimes for only part of the card. The per-book history is behind
a scrambled JS endpoint that neither the observatory nor this study decodes.
Bout-level coverage for the sample: data/e_bfo_coverage.csv.

## MMADecisions (mmadecisions.com) — for step D, recorded here for completeness

**robots.txt** ends with:

```
User-agent: *
Disallow: /
```

preceded by an allow-list of named search engines (template from ditig.com, "Last
update: 2025-03-04"). No terms-of-use page exists (only "Contact Us"). **Not
scraped.** Media-scorecard coverage cannot be measured without the owner's consent.

## Kaggle datasets

**Not yet checked.** kaggle.com does not serve a robots.txt to non-browser clients
(`/robots.txt` returns the web app's HTML), and dataset pages are rendered in
JavaScript, so licences are only readable through Kaggle's official API — which
needs the operator's login. No Kaggle credentials exist on this machine.

To enable: `cd ~/code/baptperr/SSAC27 && .venv/bin/kaggle auth login`
