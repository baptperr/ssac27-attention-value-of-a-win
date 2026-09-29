"""Confirmatory analysis, exactly as pre-registered (OSF 10.17605/OSF.IO/DXUPH).

  H1 (alpha != 0) and H2 (beta != 0): OLS of D on p, split decisions.
  H3 (gamma != 0): OLS of S on FOTN + controls, all eligible decision bouts.
  Pre-specified descriptive: Y of losers in FOTN bouts vs Y of winners in non-FOTN bouts.
  Placebo: the same D regression on two PRE-fight windows (-60..-31 vs -30..-8).
  Inference: bootstrap over bouts (10,000 draws, seed 27) for CIs; two-way cluster-robust
  SEs on both fighters as a robustness check; Holm across the three confirmatory tests.

alpha is reported twice, per DECISIONS.md 09-29: from the primary strikes-only model, and
from a model that ALSO carries the control-time share, because measurement error in p
pushes performance effects into the intercept -- which is H1.

Deviation from PAP §11, reportable under §15. The plan said "p recomputed including
takedowns and control time as a weighted alternative". A single averaged index fails on
these data: the strike share has SD 0.094 while the takedown share (SD 0.433) and control
share (SD 0.359) are nearly all-or-nothing, so averaging lets the lumpy components dominate;
the components are also negatively correlated (strikers out-strike, grapplers out-control),
leaving the composite correlated -0.18 with the strike share and disagreeing with it about
who led in 174 of 309 bouts. Instead the components enter as SEPARATE regressors:

    D = alpha + b1 * (strike share - 0.5) + b2 * (control share - 0.5)

No exchange rate is asserted, and alpha remains the quantity H1 is about. Takedowns are not
added as a third regressor: the takedown share is defined in only 244 of 309 bouts and is
collinear with control time.
"""
import csv
import math
import sys
from collections import defaultdict

import numpy as np

from db import DATA

RNG = np.random.default_rng(27)
BOOT = 10_000


def ols(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def twoway_cluster_se(X, y, beta, g1, g2):
    """Cameron-Gelbach-Miller: V1 + V2 - V12."""
    u = y - X @ beta
    XtX_inv = np.linalg.pinv(X.T @ X)

    def meat(groups):
        M = np.zeros((X.shape[1], X.shape[1]))
        for g in set(groups):
            idx = [i for i, x in enumerate(groups) if x == g]
            Xg, ug = X[idx], u[idx]
            s = Xg.T @ ug
            M += np.outer(s, s)
        return XtX_inv @ M @ XtX_inv

    both = [f"{a}|{b}" for a, b in zip(g1, g2)]
    V = meat(g1) + meat(g2) - meat(both)
    return np.sqrt(np.clip(np.diag(V), 0, None))


def boot_ci(X, y, idx_fn=None, k=0, draws=BOOT):
    n = len(y)
    out = np.empty(draws)
    for b in range(draws):
        s = RNG.integers(0, n, n)
        try:
            out[b] = ols(X[s], y[s])[k]
        except np.linalg.LinAlgError:
            out[b] = np.nan
    out = out[~np.isnan(out)]
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def two_sided_p(est, se):
    if not se or not np.isfinite(se) or se == 0:
        return float("nan")
    from scipy.stats import norm
    return float(2 * (1 - norm.cdf(abs(est / se))))


def holm(pvals, labels):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m, adj = len(pvals), [0.0] * len(pvals)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return {labels[i]: adj[i] for i in range(m)}


def load():
    bouts = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "bout_D_S.csv"))}
    fb = defaultdict(list)
    for r in csv.DictReader(open(DATA / "y_by_fighter_bout.csv")):
        fb[int(r["bout_id"])].append(r)
    strikes = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "b_sig_strikes.csv"))
               if r["winner_share"]}
    return bouts, fb, strikes


def shares(r):
    """(winner's significant-strike share, winner's control-time share). Either is None
    when neither fighter recorded any of it."""
    def sh(a, b):
        a, b = float(a or 0), float(b or 0)
        return None if a + b <= 0 else a / (a + b)
    return sh(r["winner_sig_landed"], r["loser_sig_landed"]), \
        sh(r["winner_ctrl_sec"], r["loser_ctrl_sec"])


def main():
    bouts, fb, strikes = load()
    print(f"bouts with D and S: {len(bouts)}")

    # ---- H1 / H2 -------------------------------------------------------------------
    rows = []
    for bid, b in bouts.items():
        if b["in_sample_b"] != "True" or bid not in strikes:
            continue
        p_strike, p_ctrl = shares(strikes[bid])
        ids = {f["result"]: f["fighter_id"] for f in fb[bid]}
        rows.append((bid, float(b["D"]), p_strike - 0.5,
                     None if p_ctrl is None else p_ctrl - 0.5,
                     ids.get("win"), ids.get("loss")))
    D = np.array([r[1] for r in rows])
    res = {}
    for name, cols in (("primary (strikes-only p)", (2,)),
                       ("plus control-time share", (2, 3))):
        keep = [r for r in rows if all(r[c] is not None for c in cols)]
        y = np.array([r[1] for r in keep])
        X = np.column_stack([np.ones(len(y))] + [np.array([r[c] for r in keep]) for c in cols])
        beta = ols(X, y)
        se = twoway_cluster_se(X, y, beta, [r[4] for r in keep], [r[5] for r in keep])
        a_ci, b_ci = boot_ci(X, y, k=0), boot_ci(X, y, k=1)
        res[name] = dict(n=len(y), alpha=beta[0], beta=beta[1], se=se,
                         a_ci=a_ci, b_ci=b_ci, betas=beta,
                         pa=two_sided_p(beta[0], se[0]), pb=two_sided_p(beta[1], se[1]))
        r = res[name]
        print(f"\n{name}  n={r['n']}")
        print(f"  alpha  {r['alpha']:+.4f}  SE {se[0]:.4f}  95% CI [{a_ci[0]:+.4f}, {a_ci[1]:+.4f}]"
              f"  p={r['pa']:.4g}   -> {100*(math.exp(r['alpha'])-1):+.1f}% at even output")
        print(f"  b1 strike share {r['beta']:+.4f}  SE {se[1]:.4f}  "
              f"95% CI [{b_ci[0]:+.4f}, {b_ci[1]:+.4f}]  p={r['pb']:.4g}")
        if len(cols) > 1:
            c2 = boot_ci(X, y, k=2)
            print(f"  b2 control share {beta[2]:+.4f}  SE {se[2]:.4f}  "
                  f"95% CI [{c2[0]:+.4f}, {c2[1]:+.4f}]  p={two_sided_p(beta[2], se[2]):.4g}")
    print(f"\n  mean D over all sample-B bouts with Y: {D.mean():+.4f} "
          f"({100*(math.exp(D.mean())-1):+.1f}%), n={len(D)}")

    # ---- H3 ------------------------------------------------------------------------
    keep = [b for b in bouts.values()]
    years = sorted({b["fight_date"][:4] for b in keep})[1:]
    pos = sorted({b["card_position"] or "unknown" for b in keep})[1:]
    def design(b, base):
        return ([1.0, 1.0 if b["fotn"] == "True" else 0.0,
                 1.0 if b["decision"] == "split" else 0.0,
                 base, 1.0 if b["is_title"] == "True" else 0.0]
                + [1.0 if (b["card_position"] or "unknown") == c else 0.0 for c in pos]
                + [1.0 if b["fight_date"][:4] == y else 0.0 for y in years])
    basemean = {}
    for bid, fs in fb.items():
        vals = [float(f["baseline_mean"]) for f in fs]
        basemean[bid] = math.log1p(sum(vals) / len(vals))
    X3 = np.array([design(b, basemean[int(b["bout_id"])]) for b in keep])
    y3 = np.array([float(b["S"]) for b in keep])
    g1 = [fb[int(b["bout_id"])][0]["fighter_id"] for b in keep]
    g2 = [fb[int(b["bout_id"])][1]["fighter_id"] for b in keep]
    b3 = ols(X3, y3)
    se3 = twoway_cluster_se(X3, y3, b3, g1, g2)
    ci3 = boot_ci(X3, y3, k=1)
    p3 = two_sided_p(b3[1], se3[1])
    print(f"\nH3  n={len(y3)}  gamma (FOTN) {b3[1]:+.4f}  SE {se3[1]:.4f}  "
          f"95% CI [{ci3[0]:+.4f}, {ci3[1]:+.4f}]  p={p3:.4g}"
          f"  -> {100*(math.exp(b3[1])-1):+.1f}%")
    print(f"    split-decision coef {b3[2]:+.4f} (SE {se3[2]:.4f}); "
          f"controls: log baseline views, title, card position, year")

    # ---- Holm ----------------------------------------------------------------------
    prim = res["primary (strikes-only p)"]
    adj = holm([prim["pa"], prim["pb"], p3], ["H1 alpha", "H2 beta", "H3 gamma"])
    print("\nHolm-adjusted p-values:", {k: f"{v:.4g}" for k, v in adj.items()})

    # ---- placebo: D on two pre-fight windows (-60..-31 vs -30..-8) -------------------
    from datetime import date as _date, timedelta as _td
    series = defaultdict(dict)
    for r in csv.DictReader(open(DATA / "y_daily.csv")):
        if r["day"]:
            series[r["title"]][_date.fromisoformat(r["day"])] = int(r["views"])
    reds = defaultdict(list)
    for f in ("y_redirects.csv", "g_redirects.csv"):
        fp = DATA / f
        if fp.exists():
            for r in csv.DictReader(open(fp)):
                if r.get("redirect"):
                    reds[r["article"]].append(r["redirect"])

    def mean_views(title, lo, hi):
        titles = [title] + reds.get(title, [])
        return sum(v for t in titles for d, v in series.get(t, {}).items()
                   if lo <= d <= hi) / ((hi - lo).days + 1)

    pl_rows = []
    for bid, b in bouts.items():
        if b["in_sample_b"] != "True" or bid not in strikes:
            continue
        d = _date.fromisoformat(b["fight_date"])
        ys = {}
        for f in fb[bid]:
            t = f["en_title"]
            w1 = mean_views(t, d + _td(days=-60), d + _td(days=-31))
            w2 = mean_views(t, d + _td(days=-30), d + _td(days=-8))
            ys[f["result"]] = math.log1p(w2) - math.log1p(w1)
        if set(ys) >= {"win", "loss"}:
            p_s, _ = shares(strikes[bid])
            ids = {f["result"]: f["fighter_id"] for f in fb[bid]}
            pl_rows.append((ys["win"] - ys["loss"], p_s - 0.5, ids["win"], ids["loss"]))
    ypl = np.array([r[0] for r in pl_rows])
    Xpl = np.column_stack([np.ones(len(ypl)), np.array([r[1] for r in pl_rows])])
    bpl = ols(Xpl, ypl)
    sepl = twoway_cluster_se(Xpl, ypl, bpl, [r[2] for r in pl_rows], [r[3] for r in pl_rows])
    cipl = boot_ci(Xpl, ypl, k=0)
    cipl_b = boot_ci(Xpl, ypl, k=1)
    print(f"\nPLACEBO (both windows pre-fight)  n={len(ypl)}")
    print(f"  alpha {bpl[0]:+.4f}  SE {sepl[0]:.4f}  95% CI [{cipl[0]:+.4f}, {cipl[1]:+.4f}]"
          f"  p={two_sided_p(bpl[0], sepl[0]):.4g}   (expected ~0)")
    print(f"  beta  {bpl[1]:+.4f}  SE {sepl[1]:.4f}  95% CI [{cipl_b[0]:+.4f}, {cipl_b[1]:+.4f}]"
          f"  p={two_sided_p(bpl[1], sepl[1]):.4g}")

    # ---- pre-specified descriptive --------------------------------------------------
    grp, ys = [], []
    for bid, fs in fb.items():
        f_ = bouts.get(bid)
        if not f_:
            continue
        for f in fs:
            if f_["fotn"] == "True" and f["result"] == "loss":
                grp.append(1); ys.append(float(f["Y"]))
            elif f_["fotn"] != "True" and f["result"] == "win":
                grp.append(0); ys.append(float(f["Y"]))
    grp, ys = np.array(grp, float), np.array(ys)
    raw = ys[grp == 1].mean() - ys[grp == 0].mean()
    # ...and the same comparison carrying the H3 controls, as the plan specifies.
    Xd, yd, d1, d2 = [], [], [], []
    for bid, fs in fb.items():
        b = bouts.get(bid)
        if not b:
            continue
        for f in fs:
            is_fotn_loser = b["fotn"] == "True" and f["result"] == "loss"
            is_plain_winner = b["fotn"] != "True" and f["result"] == "win"
            if not (is_fotn_loser or is_plain_winner):
                continue
            Xd.append([1.0, 1.0 if is_fotn_loser else 0.0,
                       1.0 if b["decision"] == "split" else 0.0,
                       basemean[bid],   # bout mean, as the PAP specifies
                       1.0 if b["is_title"] == "True" else 0.0]
                      + [1.0 if (b["card_position"] or "unknown") == c else 0.0 for c in pos]
                      + [1.0 if b["fight_date"][:4] == y else 0.0 for y in years])
            yd.append(float(f["Y"]))
            d1.append(fs[0]["fighter_id"]); d2.append(fs[1]["fighter_id"])
    Xd, yd = np.array(Xd), np.array(yd)
    bd = ols(Xd, yd)
    sed = twoway_cluster_se(Xd, yd, bd, d1, d2)
    cid = boot_ci(Xd, yd, k=1)
    print(f"\nDescriptive: FOTN losers mean Y {ys[grp==1].mean():+.4f} (n={int(grp.sum())}) vs "
          f"non-FOTN winners {ys[grp==0].mean():+.4f} (n={int((1-grp).sum())}); "
          f"raw difference {raw:+.4f}")
    print(f"  with the H3 controls: {bd[1]:+.4f}  SE {sed[1]:.4f}  "
          f"95% CI [{cid[0]:+.4f}, {cid[1]:+.4f}]  p={two_sided_p(bd[1], sed[1]):.4g}"
          f"  -> {100*(math.exp(bd[1])-1):+.1f}%")

    with open(DATA / "results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "n", "estimate", "se", "ci_lo", "ci_hi", "p", "holm"])
        for name, r in res.items():
            w.writerow([f"alpha [{name}]", r["n"], r["alpha"], r["se"][0], *r["a_ci"], r["pa"],
                        adj["H1 alpha"] if name.startswith("primary") else ""])
            w.writerow([f"beta [{name}]", r["n"], r["beta"], r["se"][1], *r["b_ci"], r["pb"],
                        adj["H2 beta"] if name.startswith("primary") else ""])
        w.writerow(["gamma (FOTN)", len(y3), b3[1], se3[1], *ci3, p3, adj["H3 gamma"]])
    print("\nwrote data/results.csv")


if __name__ == "__main__":
    main()
