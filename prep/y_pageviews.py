"""The outcome: Y for every fighter in every eligible decision bout, baseline AND
post-fight. Runs only now that DECISIONS.md records the OSF pre-registration
(CLAUDE.md rule 1, 2026-09-29).

Y = log1p(mean daily views, days +2..+30) − log1p(mean daily views, days −60..−8),
en.wikipedia, all-access, agent=user, redirects merged, day 0 = the fight date.
D = Y_winner − Y_loser. S = mean of the two.

Per FIGHTER, not per window: one request covers that fighter's whole span
(earliest bout − 60 days .. latest bout + 30), and the windows are sliced locally.
That is ~1,500 requests instead of ~5,400. Redirects are fetched the same way and
summed into the article's views.

Phases (resumable): redirects -> views -> compute.
  data/y_redirects.csv       article, redirect  (for titles G did not already cover)
  data/y_daily.csv           title, day, views  (raw, one row per day with traffic)
  data/y_by_fighter_bout.csv bout_id, fighter_id, result, baseline/outcome means, Y
  data/bout_D_S.csv          bout_id, date, decision, fotn, D, S, p, ...
"""
import csv
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, timedelta

from db import DATA, OBS, UNIVERSE, connect

sys.path.insert(0, str(OBS))
from observatory.http import Client                 # noqa: E402
from observatory.sources import pageviews           # noqa: E402

BASE_LO, BASE_HI = -60, -8
OUT_LO, OUT_HI = 2, 30
UA = "FirstLightObservatory/1.0 (baptperr18@gmail.com) SSAC27 research query"
API = "https://en.wikipedia.org/w/api.php"
RED = DATA / "y_redirects.csv"
DAILY = DATA / "y_daily.csv"
# `--to90` extends the fetched span to day +90 for PAP §11's secondary outcome window
# (+31..+90), into its own file so the primary series stays untouched.
if "--to90" in sys.argv:
    OUT_HI = 90
    DAILY = DATA / "y_daily_to90.csv"


def articles():
    out = {}
    for f in ("fighter_articles.csv", "g_fighter_articles.csv", "h3_fighter_articles.csv"):
        p = DATA / f
        if p.exists():
            for r in csv.DictReader(open(p)):
                if r["en_title"] and r["created_utc"]:
                    out[int(r["fighter_id"])] = r
    return out


def eligible_bouts(arts):
    dec = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "decision_bouts.csv"))}
    with connect() as c:
        rows = c.execute(f"""with u as ({UNIVERSE})
            select u.bout_id, u.date, bf.fighter_id, bf.result
              from u join bout_fighters bf using(bout_id)
             where u.event_kind = 'ufc_card'
               and u.date between '2015-08-30' and '2026-08-20'""").fetchall()
    per = defaultdict(list)
    for r in rows:
        per[r["bout_id"]].append(r)
    out = []
    for bid, fs in per.items():
        if bid not in dec or len(fs) != 2:
            continue
        d = fs[0]["date"]
        if all(f["fighter_id"] in arts
               and date.fromisoformat(arts[f["fighter_id"]]["created_utc"][:10])
               <= d - timedelta(days=60) for f in fs):
            out.append((bid, d, fs, dec[bid]))
    return sorted(out, key=lambda t: t[1])


def phase_redirects(titles):
    known = set()
    if RED.exists():
        known = {r["asked"] for r in csv.DictReader(open(RED))}
    # G asked for these already; reuse its answers.
    g = DATA / "g_redirects.csv"
    if g.exists() and not RED.exists():
        with RED.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["asked", "article", "redirect"])
            w.writeheader()
            for r in csv.DictReader(open(g)):
                w.writerow({"asked": r["article"], "article": r["article"],
                            "redirect": r["redirect"]})
        known = {r["asked"] for r in csv.DictReader(open(RED))}
    g_asked = {r["en_title"] for r in csv.DictReader(open(DATA / "g_prefight_views.csv"))}
    todo = sorted(titles - known - g_asked)
    print(f"[redirects] {len(todo)} titles to ask", flush=True)
    if not todo:
        return
    with RED.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["asked", "article", "redirect"])
        for i in range(0, len(todo), 50):
            batch, cont = todo[i:i + 50], {}
            while True:
                q = {"action": "query", "format": "json", "formatversion": "2",
                     "prop": "redirects", "titles": "|".join(batch), "rdlimit": "max",
                     "rdnamespace": "0", "rdprop": "title", "maxlag": "5", **cont}
                req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(q)}",
                                             headers={"User-Agent": UA})
                d = json.loads(urllib.request.urlopen(req, timeout=30).read())
                norm = {n["to"]: n["from"] for n in d.get("query", {}).get("normalized", [])}
                for p in d.get("query", {}).get("pages", []):
                    art = norm.get(p["title"], p["title"])
                    for r in p.get("redirects", []):
                        w.writerow({"asked": art, "article": art, "redirect": r["title"]})
                fh.flush()
                time.sleep(1.0)
                if "continue" not in d:
                    break
                cont = d["continue"]
    # record that these titles were asked, even when they have no redirects
    with RED.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["asked", "article", "redirect"])
        for t in todo:
            w.writerow({"asked": t, "article": t, "redirect": ""})


def redirects_of():
    out = defaultdict(list)
    for f in (RED, DATA / "g_redirects.csv"):
        if f.exists():
            for r in csv.DictReader(open(f)):
                if r.get("redirect"):
                    out[r["article"]].append(r["redirect"])
    return {k: sorted(set(v)) for k, v in out.items()}


def phase_views(spans, client):
    done = set()
    if DAILY.exists():
        done = {r["title"] for r in csv.DictReader(open(DAILY))}
    todo = [(t, lo, hi) for t, (lo, hi) in spans.items() if t not in done]
    print(f"[views] {len(spans)} titles, {len(todo)} to fetch", flush=True)
    new = not DAILY.exists()
    with DAILY.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["title", "day", "views"])
        if new:
            w.writeheader()
        for n, (t, lo, hi) in enumerate(todo, 1):
            resp = client.get(pageviews.daily_article_url("en.wikipedia", t, lo, hi))
            if resp.ok:
                for day, v in sorted(pageviews.parse_daily_views(json.loads(resp.text)).items()):
                    w.writerow({"title": t, "day": day, "views": v})
            elif resp.status != 404:
                print(f"  HTTP {resp.status} on {t}", flush=True)
            w.writerow({"title": t, "day": "", "views": ""})   # marks the title as done
            fh.flush()
            if n % 100 == 0:
                print(f"  [views] {n}/{len(todo)}", flush=True)


def compute(arts, bouts, reds):
    series = defaultdict(dict)
    if DAILY.exists():
        for r in csv.DictReader(open(DAILY)):
            if r["day"]:
                series[r["title"]][date.fromisoformat(r["day"])] = int(r["views"])

    def mean_views(title, lo, hi):
        titles = [title] + reds.get(title, [])
        days = (hi - lo).days + 1
        total = sum(v for t in titles for d, v in series.get(t, {}).items() if lo <= d <= hi)
        return total / days

    rows, per_bout = [], []
    for bid, d, fs, dec in bouts:
        ys = {}
        for f in fs:
            t = arts[f["fighter_id"]]["en_title"]
            b = mean_views(t, d + timedelta(days=BASE_LO), d + timedelta(days=BASE_HI))
            o = mean_views(t, d + timedelta(days=OUT_LO), d + timedelta(days=OUT_HI))
            y = math.log1p(o) - math.log1p(b)
            ys[f["result"]] = y
            rows.append({"bout_id": bid, "fight_date": d, "fighter_id": f["fighter_id"],
                         "result": f["result"], "en_title": t,
                         "baseline_mean": round(b, 4), "outcome_mean": round(o, 4),
                         "Y": round(y, 6)})
        if set(ys) >= {"win", "loss"}:
            per_bout.append({"bout_id": bid, "fight_date": d, "decision": dec["decision"],
                             "fotn": dec["fotn"], "card_position": dec["card_position"],
                             "is_title": dec["is_title"], "in_sample_b": dec["in_sample_b"],
                             "D": round(ys["win"] - ys["loss"], 6),
                             "S": round((ys["win"] + ys["loss"]) / 2, 6)})
    with open(DATA / "y_by_fighter_bout.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(DATA / "bout_D_S.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_bout[0])); w.writeheader(); w.writerows(per_bout)
    print(f"[compute] {len(rows)} fighter-bouts, {len(per_bout)} bouts with D and S", flush=True)


def main():
    arts = articles()
    bouts = eligible_bouts(arts)
    print(f"{len(bouts)} eligible decision bouts", flush=True)
    spans = {}
    for bid, d, fs, _ in bouts:
        for f in fs:
            t = arts[f["fighter_id"]]["en_title"]
            lo, hi = d + timedelta(days=BASE_LO), d + timedelta(days=OUT_HI)
            if t in spans:
                spans[t] = (min(spans[t][0], lo), max(spans[t][1], hi))
            else:
                spans[t] = (lo, hi)
    phases = sys.argv[1:] or ["redirects", "views", "compute"]
    if "redirects" in phases:
        phase_redirects(set(spans))
    reds = redirects_of()
    for a, rs in reds.items():
        if a in spans:
            for r in rs:
                spans.setdefault(r, spans[a])
                spans[r] = (min(spans[r][0], spans[a][0]), max(spans[r][1], spans[a][1]))
    if "views" in phases:
        with Client(cache_dir=OBS / "cache") as client:
            phase_views(spans, client)
    if "compute" in phases:
        compute(arts, bouts, reds)


if __name__ == "__main__":
    main()
