"""PAP §11 robustness: the secondary outcome window, days +31..+90.

Y90 = log1p(mean daily views, +31..+90) - log1p(mean daily views, -60..-8), redirects
merged, same eligible bouts. Then the same D = alpha + beta*p fit as the primary.
"""
import csv, math
from collections import defaultdict
from datetime import date, timedelta
import numpy as np
from db import DATA

series, reds = defaultdict(dict), defaultdict(list)
for r in csv.DictReader(open(DATA / "y_daily_to90.csv")):
    if r["day"]:
        series[r["title"]][date.fromisoformat(r["day"])] = int(r["views"])
for f in ("y_redirects.csv", "g_redirects.csv"):
    p = DATA / f
    if p.exists():
        for r in csv.DictReader(open(p)):
            if r.get("redirect"):
                reds[r["article"]].append(r["redirect"])

def mean_views(title, lo, hi):
    ts = [title] + reds.get(title, [])
    return sum(v for t in ts for d, v in series.get(t, {}).items() if lo <= d <= hi) / ((hi - lo).days + 1)

bouts = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "bout_D_S.csv"))}
strikes = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "b_sig_strikes.csv")) if r["winner_share"]}
fb = defaultdict(list)
for r in csv.DictReader(open(DATA / "y_by_fighter_bout.csv")):
    fb[int(r["bout_id"])].append(r)

D90, D30, P = [], [], []
for bid, b in bouts.items():
    if b["in_sample_b"] != "True" or bid not in strikes:
        continue
    d = date.fromisoformat(b["fight_date"])
    ys = {}
    for f in fb[bid]:
        base = mean_views(f["en_title"], d + timedelta(days=-60), d + timedelta(days=-8))
        out90 = mean_views(f["en_title"], d + timedelta(days=31), d + timedelta(days=90))
        ys[f["result"]] = math.log1p(out90) - math.log1p(base)
    if set(ys) >= {"win", "loss"}:
        D90.append(ys["win"] - ys["loss"]); D30.append(float(b["D"]))
        P.append(float(strikes[bid]["winner_share"]) - 0.5)
X = np.column_stack([np.ones(len(P)), np.array(P)])
for name, y in (("+2..+30 (primary)", np.array(D30)), ("+31..+90 (robustness)", np.array(D90))):
    a, bq = np.linalg.lstsq(X, y, rcond=None)[0]
    rng = np.random.default_rng(27)
    boots = [np.linalg.lstsq(X[s], y[s], rcond=None)[0][0]
             for s in (rng.integers(0, len(y), len(y)) for _ in range(4000))]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    print(f"{name:24s} n={len(y)}  alpha {a:+.4f} [{lo:+.4f}, {hi:+.4f}]  "
          f"-> {100*(math.exp(a)-1):+.1f}%   beta {bq:+.4f}")
