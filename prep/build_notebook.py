"""Write notebooks/abstract.ipynb: the two figures and the abstract draft.

Figures follow the data-viz procedure: form first (scatter for the relationship,
dot-and-interval for the estimates), colour by job (one categorical pair,
blue = confirmatory, orange = placebo/counterpoint, validated for CVD), thin marks,
recessive axes, direct labels rather than legend boxes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB = ROOT / "notebooks" / "abstract.ipynb"
NB.parent.mkdir(exist_ok=True)


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}


def code(src):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": src.splitlines(keepends=True)}


cells = [
    md("""# The attention value of a win in mixed martial arts

Figures and abstract for the SSAC 2027 submission.
Pre-registered: **OSF 10.17605/OSF.IO/DXUPH**. Analysis lives in `prep/z_analysis.py`;
this notebook only reads its outputs and draws.

Run top to bottom. Figures are written to `figures/` at 300 dpi.
"""),
    code("""import csv, math, sys
from pathlib import Path
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
DATA, FIGS = ROOT / "data", ROOT / "figures"
FIGS.mkdir(exist_ok=True)

# Validated categorical pair (dataviz skill: ALL CHECKS PASS, light surface).
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"

mpl.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 300, "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 10,
    "axes.edgecolor": "#d8d7d2", "axes.linewidth": 0.8, "axes.grid": False,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.labelcolor": INK, "xtick.major.width": 0.8, "ytick.major.width": 0.8,
    "legend.frameon": False,
})
print("ready")"""),
    code("""# --- data -------------------------------------------------------------------
bouts = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "bout_D_S.csv"))}
strikes = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "b_sig_strikes.csv"))
           if r["winner_share"]}

p, D = [], []
for bid, b in bouts.items():
    if b["in_sample_b"] == "True" and bid in strikes:
        p.append(float(strikes[bid]["winner_share"]) - 0.5)
        D.append(float(b["D"]))
p, D = np.array(p), np.array(D)
X = np.column_stack([np.ones(len(p)), p])
alpha, beta = np.linalg.lstsq(X, D, rcond=None)[0]
print(f"n = {len(p)}   alpha = {alpha:+.3f}   beta = {beta:+.3f}")"""),
    md("""## Figure 1 — the attention gap at equal output

Each point is one split decision. **x is the winner's share of the fight's significant
strikes, centred at 0.5** — so x = +0.1 is a 60/40 split, a 20-point gap between the two
fighters, not 10. y is the difference in their attention change. The fitted line's height
**at x = 0**, where both landed equally, is the label effect."""),
    code("""fig, ax = plt.subplots(figsize=(5.4, 3.5))

ax.axhline(0, color="#d8d7d2", lw=0.8, zorder=1)
ax.axvline(0, color="#d8d7d2", lw=0.8, zorder=1)
ax.scatter(p, D, s=13, color=INK2, alpha=0.30, linewidths=0, zorder=2)

xs = np.linspace(p.min(), p.max(), 100)
ax.plot(xs, alpha + beta * xs, color=BLUE, lw=2, zorder=4)

# the headline: the intercept
ax.plot([0], [alpha], marker="o", ms=9, color=BLUE, mec=SURFACE, mew=2, zorder=5)
ax.annotate(f"+{alpha:.2f} log points\\n(+{100*(math.exp(alpha)-1):.0f}% attention)\\nat equal striking",
            xy=(0, alpha), xytext=(-0.33, 4.3),
            color=INK, fontsize=8.5, ha="left", va="top",
            arrowprops=dict(arrowstyle="-", color=BLUE, lw=1.2, alpha=0.9,
                            connectionstyle="angle3,angleA=0,angleB=70",
                            shrinkA=2, shrinkB=7))

ax.set_xlabel("winner's share of significant strikes, minus 0.5")
ax.set_ylabel("winner's attention change\\nminus loser's (log points)")
ax.set_title("Winners gain more attention even when output was even", loc="left",
             color=INK, pad=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(FIGS / "fig1_label_effect.png", bbox_inches="tight")
plt.show()"""),
    md("""## Figure 2 — what moves attention, and what does not

Point estimates with 95% bootstrap intervals (10,000 resamples of bouts).
Blue: the pre-registered confirmatory estimates. Orange: the placebo, which should
sit at zero, and the descriptive comparison."""),
    code("""rows = [
    ("Winning, at equal output  (H1)",            alpha,   0.1687,  0.3960, BLUE,   "o"),
    ("Fight of the Night  (H3)",                  0.2322,  0.1462,  0.3218, BLUE,   "o"),
    # H2 rescaled so it is in the same units (log points) as the level effects: the
    # effect of the winner's share sitting 0.1 above even, i.e. a 60/40 split. The
    # slope itself is +0.79 per unit of (share - 0.5).
    ("Winning the striking 60/40  (H2)",          0.0789, -0.0224, 0.1811, BLUE,   "o"),
    ("Placebo: same test, both windows pre-fight", 0.0581, -0.0082, 0.1254, ORANGE, "D"),
    ("Losing a FOTN vs winning a plain fight",    -0.1572, -0.2486, -0.0642, ORANGE, "D"),
]
fig, ax = plt.subplots(figsize=(6.4, 3.0))
ys = np.arange(len(rows))[::-1]
ax.axvline(0, color="#d8d7d2", lw=0.8, zorder=1)
for y, (label, est, lo, hi, colour, marker) in zip(ys, rows):
    ax.plot([lo, hi], [y, y], color=colour, lw=2, solid_capstyle="round", zorder=3)
    ax.plot([est], [y], marker=marker, ms=8, color=colour, mec=SURFACE, mew=1.6, zorder=4)
    ax.text(hi + 0.012, y, f"{est:+.2f}", va="center", ha="left", color=INK, fontsize=8.5)

ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows], color=INK)
ax.set_xlabel("change in log daily Wikipedia pageviews (95% bootstrap interval)")
ax.set_title("The label moves attention; a measurable performance edge does not",
             loc="right", color=INK, pad=10, fontsize=9.5)
ax.set_xlim(-0.30, 0.50)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
fig.tight_layout()
fig.savefig(FIGS / "fig2_estimates.png", bbox_inches="tight")
plt.show()"""),
    md("""## Abstract (draft)

**The attention value of a win in mixed martial arts**

**Introduction.** Attention concentrates on winners, but why is unclear. Rosen's superstar
account says attention tracks talent, amplified; Adler's says it can attach to an
arbitrary early advantage and compound. Separating them is hard, because winners usually
did perform better. Split decisions break the tie: the judges disagreed, so performance
was near-equal, while the label is close to arbitrary.

**Methods.** 562 UFC split decisions, 2015-08-30 to 2026-08-20; 309 where both fighters
held an English Wikipedia article at least 60 days old and fight statistics exist. For
each fighter, attention is the change in log mean daily Wikipedia pageviews from days
−60..−8 before the fight to +2..+30 after, excluding fight week. D is the winner's change minus the loser's; p the winner's share of significant
strikes, minus 0.5. Fitting D = α + β·p, α is the gap when output
was even and β the return to out-striking. A third asks whether Fight of the Night bouts draw
more attention (1,508 decision bouts, 147 awarded). Pre-registered (OSF
10.17605/OSF.IO/DXUPH) before any post-fight data existed; intervals bootstrap over
bouts, errors cluster on both fighters, Holm across the three tests.

**Results.** The win label is worth **+0.28 log points, a 33% attention gap**
(95% CI 0.17–0.40, p < 0.001) between two fighters who landed equally. The return to
out-striking is **indistinguishable from zero** (β = 0.79, CI −0.22–1.81); the design
detects slopes above roughly 1.1, so this is inconclusive rather than null. α is unchanged when the
control-time share enters the model (+0.284; control share itself −0.09, p = 0.53), so
control time does not account for it. Fight of the Night is worth **+0.23 log points,
26%** (CI 0.15–0.32, p < 0.001). Two pre-specified
cautions: a placebo on two pre-fight windows returns +0.06 (CI −0.01–0.13), not
distinguishable from zero but positive; read conservatively, α net of the placebo is
**+0.22, a 25% gap**. And losing an entertaining fight is **not** as good as winning a
dull one: FOTN losers gain 15% less than ordinary winners
(p < 0.001), and 19% less than split-decision winners. α is stable across the pre-specified
checks: 0.25–0.32 dropping each year, 0.29 excluding main events, 0.30 with an odds
control.

**Conclusion.** In fights the judges could not separate, the official result alone
moves public attention about as much as being in the night's best fight — the two are
not distinguishable here (α − γ = +0.05, CI −0.10 to +0.20) —  while the
performance edge we can measure moves it undetectably. That is consistent with Adler's
account for close fights, though Rosen cannot be rejected: the upper bound on β would
imply a performance return exceeding the label effect. Three limits bound the claim. α is an
**upper bound** on the pure label effect: performance the strike measure cannot see loads
onto the intercept. γ is not causally identified — bonus bouts differ from others in ways
the controls only partly capture. And p is a fight-total
striking proxy, not round-by-round judging, so β bounds what strikes can explain rather
than what performance can."""),
    code("""# Word count of the abstract markdown cell above (SSAC limit: 500).
import nbformat, re
nb = nbformat.read(ROOT / "notebooks" / "abstract.ipynb", as_version=4)
cell = next(c.source for c in nb.cells
            if c.cell_type == "markdown" and c.source.lstrip().startswith("## Abstract"))
body = cell.split("**The attention value", 1)[1]
body = re.sub(r"[*_`#]", " ", body)
words = [w for w in body.split() if any(ch.isalnum() for ch in w)]
print(f"{len(words)} words (limit 500)")"""),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3",
      "language": "python", "name": "python3"},
      "language_info": {"name": "python", "version": "3.12"}},
      "nbformat": 4, "nbformat_minor": 5}
NB.write_text(json.dumps(nb, indent=1))
print(f"wrote {NB}")
