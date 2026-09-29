"""Confirmatory analysis, exactly as pre-registered (OSF 10.17605/OSF.IO/DXUPH).

  H1 (alpha != 0) and H2 (beta != 0): OLS of D on p, split decisions.
  H3 (gamma != 0): OLS of S on FOTN + controls, all eligible decision bouts.
  Pre-specified descriptive: Y of losers in FOTN bouts vs Y of winners in non-FOTN bouts.
  Placebo: the same D regression on two PRE-fight windows (-60..-31 vs -30..-8).
  Inference: bootstrap over bouts (10,000 draws, seed 27) for CIs; two-way cluster-robust
  SEs on both fighters as a robustness check; Holm across the three confirmatory tests.

alpha is reported twice, per DECISIONS.md 09-29: with the primary strikes-only p, and with
the control-weighted p (PAP §11 promoted into the main result), because measurement error
in p pushes performance effects into the intercept.

Weighted p is the mean of three within-bout shares -- significant strikes, takedowns,
control time -- each share computed only when the pair sums above zero. Equal weights on
shares, rather than invented exchange rates between a takedown and a strike; recorded in
STATUS.md as a methods choice.
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
    def sh(a, b):
        a, b = float(a or 0), float(b or 0)
        return None if a + b <= 0 else a / (a + b)
    out = [sh(r["winner_sig_landed"], r["loser_sig_landed"]),
           sh(r["winner_td"], r["loser_td"]),
           sh(r["winner_ctrl_sec"], r["loser_ctrl_sec"])]
    got = [x for x in out if x is not None]
    return (out[0], sum(got) / len(got) if got else None)


def main():
    bouts, fb, strikes = load()
    print(f"bouts with D and S: {len(bouts)}")

    # ---- H1 / H2 -------------------------------------------------------------------
    rows = []
    for bid, b in bouts.items():
        if b["in_sample_b"] != "True" or bid not in strikes:
            continue
        p_strike, p_w = shares(strikes[bid])
        ids = {f["result"]: f["fighter_id"] for f in fb[bid]}
        rows.append((bid, float(b["D"]), p_strike - 0.5,
                     None if p_w is None else p_w - 0.5,
                     ids.get("win"), ids.get("loss")))
    D = np.array([r[1] for r in rows])
    res = {}
    for name, k in (("primary (strikes-only p)", 2), ("weighted p (strikes+TD+control)", 3)):
        keep = [r for r in rows if r[k] is not None]
        y = np.array([r[1] for r in keep])
        p = np.array([r[k] for r in keep])
        X = np.column_stack([np.ones(len(y)), p])
        beta = ols(X, y)
        se = twoway_cluster_se(X, y, beta, [r[4] for r in keep], [r[5] for r in keep])
        a_ci, b_ci = boot_ci(X, y, k=0), boot_ci(X, y, k=1)
        res[name] = dict(n=len(y), alpha=beta[0], beta=beta[1], se=se,
                         a_ci=a_ci, b_ci=b_ci,
                         pa=two_sided_p(beta[0], se[0]), pb=two_sided_p(beta[1], se[1]))
        r = res[name]
        print(f"\n{name}  n={r['n']}")
        print(f"  alpha {r['alpha']:+.4f}  SE {se[0]:.4f}  95% CI [{a_ci[0]:+.4f}, {a_ci[1]:+.4f}]"
              f"  p={r['pa']:.4g}   -> {100*(math.exp(r['alpha'])-1):+.1f}% attention gap at even output")
        print(f"  beta  {r['beta']:+.4f}  SE {se[1]:.4f}  95% CI [{b_ci[0]:+.4f}, {b_ci[1]:+.4f}]"
              f"  p={r['pb']:.4g}")
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
    print(f"\nDescriptive: FOTN losers mean Y {ys[grp==1].mean():+.4f} (n={int(grp.sum())}) vs "
          f"non-FOTN winners {ys[grp==0].mean():+.4f} (n={int((1-grp).sum())}); "
          f"difference {ys[grp==1].mean()-ys[grp==0].mean():+.4f}")

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
