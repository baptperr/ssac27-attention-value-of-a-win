"""E, part 2: odds coverage of sample B in Kaggle's "Ultimate UFC Dataset"
(mdabbert/ultimate-ufc-dataset, CC BY 4.0; its own odds source is bestfightodds.com).

A Kaggle row is matched to a B bout by fight date (+-1 day) and BOTH fighters' names,
using the observatory's corner-pair name score (token overlap, either corner order,
>= 0.5 on the weaker corner) -- the same rule its Wikipedia matching uses. A tie for
best is left unmatched rather than guessed.

Writes data/e_kaggle_odds_coverage.csv. Odds values are kept alongside the match so
the coverage is checkable, and stay under data/, which is not published.
"""
import csv
import sys
from datetime import date, timedelta

from db import DATA, OBS

sys.path.insert(0, str(OBS))
from ingest.wiki_cards import _corner_pair_score, _TOKEN_MATCH_THRESHOLD  # noqa: E402

SRC = DATA / "kaggle" / "mdabbert__ultimate-ufc-dataset" / "ufc-master.csv"


def main():
    kag = list(csv.DictReader(open(SRC)))
    by_day = {}
    for r in kag:
        by_day.setdefault(r["date"][:10], []).append(r)
    sample = list(csv.DictReader(open(DATA / "b_sample.csv")))

    out = []
    for s in sample:
        d = date.fromisoformat(s["fight_date"])
        cands = [r for k in (-1, 0, 1)
                 for r in by_day.get((d + timedelta(days=k)).isoformat(), [])]
        scored = []
        for r in cands:
            direct = _corner_pair_score(s["winner"], s["loser"], r["R_fighter"], r["B_fighter"])
            cross = _corner_pair_score(s["winner"], s["loser"], r["B_fighter"], r["R_fighter"])
            sc, winner_corner = (direct, "R") if direct >= cross else (cross, "B")
            if sc >= _TOKEN_MATCH_THRESHOLD:
                scored.append((sc, winner_corner, r))
        scored.sort(key=lambda t: t[0], reverse=True)
        rec = {"bout_id": s["bout_id"], "fight_date": s["fight_date"],
               "winner": s["winner"], "loser": s["loser"], "status": "no row",
               "kaggle_winner_corner": "", "winner_odds": "", "loser_odds": "",
               "kaggle_winner_label": ""}
        if scored and (len(scored) == 1 or scored[0][0] > scored[1][0]):
            _, wc, r = scored[0]
            lc = "B" if wc == "R" else "R"
            rec.update(kaggle_winner_corner=wc, winner_odds=r[f"{wc}_odds"],
                       loser_odds=r[f"{lc}_odds"], kaggle_winner_label=r["Winner"])
            rec["status"] = "odds" if r[f"{wc}_odds"] and r[f"{lc}_odds"] else "row, no odds"
            # Consistency: the dataset's own Winner column must name our winner's corner.
            if r["Winner"] not in ("Red" if wc == "R" else "Blue",):
                rec["status"] += " (winner disagrees)"
        elif scored:
            rec["status"] = "ambiguous"
        out.append(rec)

    with open(DATA / "e_kaggle_odds_coverage.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    from collections import Counter
    st = Counter(o["status"] for o in out)
    print(f"sample B: {len(out)} bouts; Kaggle rows {len(kag)}, dates "
          f"{min(r['date'] for r in kag)[:10]}..{max(r['date'] for r in kag)[:10]}")
    for k, v in st.most_common():
        print(f"  {k:30s} {v}")
    has = [o for o in out if o["status"].startswith("odds")]
    print(f"odds for both fighters: {len(has)}/{len(out)} ({100 * len(has) / len(out):.1f}%)")
    yrs = Counter(o["fight_date"][:4] for o in has)
    tot = Counter(o["fight_date"][:4] for o in out)
    print("  by year:", {y: f"{yrs[y]}/{tot[y]}" for y in sorted(tot)})


if __name__ == "__main__":
    main()
