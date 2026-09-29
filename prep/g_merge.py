"""G, redirect merging (step 2): the placebo SD with Y's definition -- "redirects merged".

A fighter's views in a window = views of the article's current title + views of every
title that redirects to it (data/g_redirects.csv). An article renamed after the window
recorded that window's views under its OLD title, which is now a redirect -- the reason
109 windows came back empty under the current title alone.

Same NOTHING-POST-FIGHT rule as g_power.py: each request asks for exactly
[fight-60, fight-8]; a returned day outside it stops the run. Same pacing (observatory
client, 2 s/host, robots-checked). Resumable: data/g_redirect_views.csv.

Caveat kept, not hidden: a redirect title that pointed at a DIFFERENT page during the
window would add unrelated views. Not detectable from pageviews alone; expected rare
for fighter-name redirects.
"""
import csv
import json
import math
import random
import statistics
import sys
from datetime import date, timedelta

from db import DATA, OBS

sys.path.insert(0, str(OBS))
from observatory.http import Client                 # noqa: E402
from observatory.sources import pageviews           # noqa: E402

W1, W2 = (-60, -31), (-30, -8)
MAIN = DATA / "g_prefight_views.csv"
RED = DATA / "g_redirects.csv"
OUT = DATA / "g_redirect_views.csv"
FIELDS = ["bout_id", "fighter_id", "redirect", "status", "views_w1", "views_w2"]


def fetch(client):
    reds = {}
    for r in csv.DictReader(open(RED)):
        reds.setdefault(r["article"], []).append(r["redirect"])
    main = list(csv.DictReader(open(MAIN)))
    done = set()
    if OUT.exists():
        done = {(r["bout_id"], r["fighter_id"], r["redirect"]) for r in csv.DictReader(open(OUT))}
    todo = [(m, rd) for m in main for rd in reds.get(m["en_title"], [])
            if (m["bout_id"], m["fighter_id"], rd) not in done]
    print(f"{len(todo)} redirect windows to fetch", flush=True)
    new = not OUT.exists()
    with OUT.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for n, (m, rd) in enumerate(todo, 1):
            fight = date.fromisoformat(m["fight_date"])
            start, end = fight + timedelta(days=W1[0]), fight + timedelta(days=W2[1])
            rec = {"bout_id": m["bout_id"], "fighter_id": m["fighter_id"], "redirect": rd,
                   "status": "", "views_w1": 0, "views_w2": 0}
            resp = client.get(pageviews.daily_article_url("en.wikipedia", rd, start, end))
            if resp.status == 404:
                rec["status"] = "no data in window"
            elif not resp.ok:
                rec["status"] = f"HTTP {resp.status}"
            else:
                days = pageviews.parse_daily_views(json.loads(resp.text))
                stray = [d for d in days if not (start <= d <= end)]
                if stray:
                    raise SystemExit(f"days outside window for {rd}: {stray[:3]} -- stopping")
                w1_hi = fight + timedelta(days=W1[1])
                rec.update(status="ok",
                           views_w1=sum(v for d, v in days.items() if d <= w1_hi),
                           views_w2=sum(v for d, v in days.items() if d > w1_hi))
            w.writerow(rec)
            fh.flush()
            if n % 200 == 0:
                print(f"  {n}/{len(todo)}", flush=True)


def stats():
    """SD of D = winner's change minus loser's change, main title alone vs merged."""
    main = list(csv.DictReader(open(MAIN)))
    red = list(csv.DictReader(open(OUT))) if OUT.exists() else []
    extra = {}
    for r in red:
        if r["status"] == "ok":
            k = (r["bout_id"], r["fighter_id"])
            a, b = extra.get(k, (0, 0))
            extra[k] = (a + int(r["views_w1"]), b + int(r["views_w2"]))
    # winner/loser per fighter-window, from the same source g_power.py used
    sys.path.insert(0, ".")
    from g_power import unanimous_bouts
    from db import connect
    with connect() as c:
        result = {(str(r["bout_id"]), str(r["fighter_id"])): r["result"] for r in unanimous_bouts(c)}

    n1, n2 = W1[1] - W1[0] + 1, W2[1] - W2[0] + 1
    out = {}
    for label, merge in (("main title only", False), ("redirects merged", True)):
        per = {}
        for m in main:
            k = (m["bout_id"], m["fighter_id"])
            v1 = int(m["views_w1"] or 0) if m["status"] == "ok" else 0
            v2 = int(m["views_w2"] or 0) if m["status"] == "ok" else 0
            has = m["status"] == "ok"
            if merge and k in extra:
                v1, v2 = v1 + extra[k][0], v2 + extra[k][1]
                has = has or (extra[k][0] + extra[k][1]) > 0
            if not has:
                continue
            y = math.log1p(v2 / n2) - math.log1p(v1 / n1)
            per.setdefault(m["bout_id"], {})[result.get(k)] = y
        d = [p["win"] - p["loss"] for p in per.values() if set(p) >= {"win", "loss"}]
        rng = random.Random(27)
        dr = [x if rng.random() < 0.5 else -x for x in d]
        out[label] = (len(d), statistics.mean(d), statistics.stdev(d), statistics.stdev(dr))
    for label, (n, mu, sd, sdr) in out.items():
        mde = 2.8 * sd / math.sqrt(314)
        print(f"  {label:18s} bouts {n:>5}  mean D {mu:+.4f}  SD {sd:.4f}  "
              f"(random order {sdr:.4f})  -> MDE at n=314: {mde:.3f} log pts "
              f"= {100 * (math.exp(mde) - 1):.1f}%")
    with open(DATA / "g_power_merged.csv", "w", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["variant", "n_bouts", "mean_D", "sd_D", "sd_D_random_order"])
        for label, row in out.items():
            cw.writerow([label, *row])


if __name__ == "__main__":
    if "stats" not in sys.argv[1:]:
        with Client(cache_dir=OBS / "cache") as client:
            fetch(client)
    stats()
