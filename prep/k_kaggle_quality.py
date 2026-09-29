"""How good is Kaggle's "Ultimate UFC Dataset" (mdabbert)? Three independent checks.

1. Results: its Winner column against Sherdog's result, on every UFC-card bout we can
   match 2015-08-30..2026-08-20 (not just sample B).
2. Calibration: if the odds are real market prices, fighters priced at p should win
   about p of the time (a little less, because of the bookmaker margin).
3. Opening vs closing: against the observatory's own BestFightOdds captures, which for
   a settled event are each book's LAST line (i.e. closing), on the bouts both cover.

Read-only. Prints; writes nothing.
"""
import csv
import statistics
import sys
from collections import Counter
from datetime import date, timedelta

from db import DATA, OBS, UNIVERSE, connect

sys.path.insert(0, str(OBS))
from ingest.wiki_cards import _corner_pair_score, _TOKEN_MATCH_THRESHOLD  # noqa: E402

SRC = DATA / "kaggle" / "mdabbert__ultimate-ufc-dataset" / "ufc-master.csv"


def implied(american):
    a = float(american)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def main():
    kag = list(csv.DictReader(open(SRC)))
    by_day = {}
    for r in kag:
        by_day.setdefault(r["date"][:10], []).append(r)

    with connect() as c:
        bouts = c.execute(f"""
            with u as ({UNIVERSE})
            select u.bout_id, u.date,
                   max(f.full_name) filter (where bf.result = 'win')  as winner,
                   max(f.full_name) filter (where bf.result = 'loss') as loser,
                   max(bf.fighter_id) filter (where bf.result = 'win') as winner_id,
                   max(bf.fighter_id) filter (where bf.result = 'loss') as loser_id
              from u join bout_fighters bf using(bout_id) join fighters f using(fighter_id)
             where u.event_kind = 'ufc_card' and u.date between '2015-08-30' and '2026-08-20'
             group by 1, 2
            having count(*) filter (where bf.result = 'win') = 1""").fetchall()
        bfo = c.execute("""
            select o.bout_id, o.fighter_id, avg(o.implied_prob) p, count(distinct o.book) books
              from odds o group by 1, 2""").fetchall()
    bfo_p = {(r["bout_id"], r["fighter_id"]): (float(r["p"]), r["books"]) for r in bfo}

    matched, res = [], Counter()
    for b in bouts:
        d = b["date"]
        scored = []
        for k in (-1, 0, 1):
            for r in by_day.get((d + timedelta(days=k)).isoformat(), []):
                direct = _corner_pair_score(b["winner"], b["loser"], r["R_fighter"], r["B_fighter"])
                cross = _corner_pair_score(b["winner"], b["loser"], r["B_fighter"], r["R_fighter"])
                sc, wc = (direct, "R") if direct >= cross else (cross, "B")
                if sc >= _TOKEN_MATCH_THRESHOLD:
                    scored.append((sc, wc, r))
        scored.sort(key=lambda t: t[0], reverse=True)
        if not scored or (len(scored) > 1 and scored[0][0] == scored[1][0]):
            continue
        _, wc, r = scored[0]
        lc = "B" if wc == "R" else "R"
        agrees = r["Winner"] == ("Red" if wc == "R" else "Blue")
        res["winner agrees" if agrees else "WINNER DISAGREES"] += 1
        if r[f"{wc}_odds"] and r[f"{lc}_odds"]:
            matched.append((b, implied(r[f"{wc}_odds"]), implied(r[f"{lc}_odds"])))

    print(f"1. RESULTS  UFC-card bouts in window {len(bouts)}; matched to a Kaggle row "
          f"{sum(res.values())} ({100 * sum(res.values()) / len(bouts):.1f}%)")
    print(f"   {dict(res)}")

    # 2. calibration: each bout contributes both fighters.
    bins = {}
    overround = []
    for _, pw, pl in matched:
        overround.append(pw + pl)
        tot = pw + pl
        for p, won in ((pw / tot, 1), (pl / tot, 0)):   # margin removed
            k = min(int(p * 10), 9)
            bins.setdefault(k, []).append((p, won))
    print(f"\n2. CALIBRATION  {len(matched)} bouts with odds; median overround "
          f"{statistics.median(overround):.3f} (1.00 = no margin; books run ~1.03-1.06)")
    print("   priced at   n     won    avg price")
    for k in sorted(bins):
        xs = bins[k]
        print(f"   {k * 10:>3}-{k * 10 + 10:<3}%  {len(xs):>5}  {100 * statistics.mean(w for _, w in xs):5.1f}%"
              f"   {100 * statistics.mean(p for p, _ in xs):5.1f}%")
    fav = [pw > pl for _, pw, pl in matched if pw != pl]
    print(f"   favourite won {100 * statistics.mean(fav):.1f}% of {len(fav)} bouts")

    # 3. vs the observatory's BestFightOdds closing captures.
    diffs = []
    for b, pw, pl in matched:
        o = bfo_p.get((b["bout_id"], b["winner_id"]))
        if o:
            diffs.append((pw / (pw + pl), o[0], o[1]))
    print(f"\n3. vs BESTFIGHTODDS CLOSING (observatory captures, fights 2026-01..03)  n={len(diffs)}")
    if diffs:
        ad = [abs(k - bf) for k, bf, _ in diffs]
        print(f"   winner's implied prob, Kaggle vs BFO-closing: mean |diff| "
              f"{statistics.mean(ad):.3f}, median {statistics.median(ad):.3f}, "
              f"within 0.05: {sum(a <= 0.05 for a in ad)}/{len(ad)}")
        try:
            print(f"   correlation {statistics.correlation([k for k, _, _ in diffs], [bf for _, bf, _ in diffs]):.3f}")
        except statistics.StatisticsError:
            pass


if __name__ == "__main__":
    main()
