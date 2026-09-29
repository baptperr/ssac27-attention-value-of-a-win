"""PAP §11 robustness, the checks that need no further fetching:
  * closing-odds favourite added as a control, on the bouts that have odds
  * each fight year dropped in turn
  * main events excluded
The +31..+90 outcome window is handled by r_window90.py once its pull finishes.
All-language-editions summed is NOT run (see STATUS.md).
"""
import csv
import math

import numpy as np

from db import DATA


def ols(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def implied(american):
    a = float(american)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def main():
    bouts = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "bout_D_S.csv"))}
    strikes = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "b_sig_strikes.csv"))
               if r["winner_share"]}
    odds = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "e_kaggle_odds_coverage.csv"))
            if r["status"].startswith("odds")}

    rows = []
    for bid, b in bouts.items():
        if b["in_sample_b"] != "True" or bid not in strikes:
            continue
        rows.append(dict(bid=bid, D=float(b["D"]),
                         p=float(strikes[bid]["winner_share"]) - 0.5,
                         year=b["fight_date"][:4],
                         main=b["card_position"] == "main_event",
                         fav=(implied(odds[bid]["winner_odds"]) >
                              implied(odds[bid]["loser_odds"])) if bid in odds else None))

    def fit(rs, extra=None):
        y = np.array([r["D"] for r in rs])
        cols = [np.ones(len(rs)), np.array([r["p"] for r in rs])]
        if extra:
            cols.append(np.array([float(r[extra]) for r in rs]))
        b = ols(np.column_stack(cols), y)
        return len(rs), b[0], b[1], (b[2] if extra else None)

    n, a, bt, _ = fit(rows)
    print(f"baseline                         n={n:>4}  alpha {a:+.4f}  beta {bt:+.4f}")

    with_odds = [r for r in rows if r["fav"] is not None]
    n, a, bt, _ = fit(with_odds)
    print(f"odds subsample, no control       n={n:>4}  alpha {a:+.4f}  beta {bt:+.4f}")
    n, a, bt, c = fit(with_odds, "fav")
    print(f"  + favourite-won control        n={n:>4}  alpha {a:+.4f}  beta {bt:+.4f}"
          f"  favourite {c:+.4f}")

    no_main = [r for r in rows if not r["main"]]
    n, a, bt, _ = fit(no_main)
    print(f"main events excluded             n={n:>4}  alpha {a:+.4f}  beta {bt:+.4f}")

    print("\ndrop each year in turn:")
    alphas = []
    for y in sorted({r["year"] for r in rows}):
        rs = [r for r in rows if r["year"] != y]
        n, a, bt, _ = fit(rs)
        alphas.append(a)
        print(f"  without {y}                      n={n:>4}  alpha {a:+.4f}  beta {bt:+.4f}")
    print(f"  alpha range across drops: {min(alphas):+.4f} to {max(alphas):+.4f} "
          f"({100*(math.exp(min(alphas))-1):+.1f}% to {100*(math.exp(max(alphas))-1):+.1f}%)")


if __name__ == "__main__":
    main()
