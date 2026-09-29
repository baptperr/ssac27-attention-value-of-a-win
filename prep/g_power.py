"""G: SD of the within-bout pre-fight attention difference, UNANIMOUS decisions only,
for the power calculation. NOTHING POST-FIGHT is requested, stored or read.

Window rule, enforced three ways:
  1. every pageview request asks for exactly [fight-60, fight-8] and nothing else;
  2. every returned day is asserted to lie inside that range before it is kept;
  3. no stored pageview table is read at all (pageviews_daily covers 2026 only and
     may hold post-fight days -- this script never queries it).

Population mirrors sample B's selection, applied to unanimous decisions: UFC cards,
fight date 2015-08-30..2026-08-20, both fighters with a verified English article
created >= 60 days before the fight.

Phases (each resumable, each writing its own CSV under data/):
  1. articles  resolve fighters lacking a QID with the observatory's resolver
               (read-only: nothing written back), then English title + creation date
  2. state     was each page a real article (not a redirect) at fight - 60 days?
               -- the same test sample B applies
  3. views     one request per fighter-bout for its own pre-fight window
  4. stats     mean daily views per window -> per-fighter change -> within-bout
               difference (winner minus loser) -> SD, with variants

Creation dates come from en.wikipedia.org/w/api.php, authorised by the operator for
this analysis and called directly (the observatory's client refuses that path).
"""
import csv
import json
import math
import random
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

from db import DATA, OBS, UNIVERSE, connect

sys.path.insert(0, str(OBS))
from ingest.pageviews import _resolve_by_name                  # noqa: E402
from observatory.http import Client                            # noqa: E402
from observatory.sources import pageviews, wikidata            # noqa: E402

WINDOW = ("2015-08-30", "2026-08-20")
W1 = (-60, -31)   # 30 days
W2 = (-30, -8)    # 23 days
MIN_ARTICLE_AGE = 60

ART = DATA / "g_fighter_articles.csv"
VIEWS = DATA / "g_prefight_views.csv"
STATE = DATA / "g_state_at_cutoff.csv"
B_ART = DATA / "fighter_articles.csv"      # sample B's lookups, reused where present
UA = "FirstLightObservatory/1.0 (baptperr18@gmail.com) SSAC27 research query"
API = "https://en.wikipedia.org/w/api.php"
ART_FIELDS = ["fighter_id", "name", "sherdog_id", "qid", "en_title", "created_utc", "note"]
VIEW_FIELDS = ["bout_id", "fighter_id", "fight_date", "en_title", "start", "end",
               "status", "days_returned", "views_w1", "views_w2"]


class StubJob:
    def quarantine(self, kind, payload):
        pass


def unanimous_bouts(conn):
    return conn.execute(f"""
        with u as ({UNIVERSE}),
        ud as (select u.bout_id, u.date from u join bout_fighters bf using(bout_id)
                where u.event_kind = 'ufc_card' and u.date between %s and %s
                group by 1, 2
               having min(bf.method) = 'Decision (Unanimous)'
                  and max(bf.method) = 'Decision (Unanimous)')
        select ud.bout_id, ud.date, bf.fighter_id, bf.result, f.full_name as name,
               s.external_id as sherdog_id, w.external_id as qid
          from ud join bout_fighters bf using(bout_id)
          join fighters f using(fighter_id)
          join fighter_ids s on s.fighter_id = f.fighter_id and s.source = 'sherdog'
          left join fighter_ids w on w.fighter_id = f.fighter_id and w.source = 'wikidata'
         order by ud.date, ud.bout_id""", WINDOW).fetchall()


def read_csv(path):
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def first_revision(title):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2",
        "prop": "revisions", "titles": title, "rvdir": "newer", "rvlimit": "1",
        "rvprop": "timestamp", "redirects": "1", "maxlag": "5"})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    pages = data.get("query", {}).get("pages", [])
    revs = (pages[0].get("revisions") if pages else None) or []
    return revs[0]["timestamp"] if revs else None


def phase_articles(rows, client):
    have = {int(r["fighter_id"]) for r in read_csv(ART)}
    b_rows = {int(r["fighter_id"]): r for r in read_csv(B_ART)}
    fighters = {}
    for r in rows:
        fighters.setdefault(r["fighter_id"], r)
    todo = [f for fid, f in fighters.items() if fid not in have]
    print(f"[articles] {len(fighters)} fighters, {len(todo)} to look up", flush=True)

    new = not ART.exists()
    with ART.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ART_FIELDS)
        if new:
            w.writeheader()
        for n, f in enumerate(todo, 1):
            fid = f["fighter_id"]
            rec = {"fighter_id": fid, "name": f["name"], "sherdog_id": f["sherdog_id"],
                   "qid": f["qid"] or "", "en_title": "", "created_utc": "", "note": ""}
            b = b_rows.get(fid)
            if b and b.get("verification") == "p2818":
                rec.update(qid=b["qid"], en_title=b["en_title"],
                           created_utc=b["created_utc"], note="from sample B lookup")
                w.writerow(rec); fh.flush(); continue
            try:
                qid, payload = f["qid"], None
                if qid:
                    resp = client.get(wikidata.entity_url(qid))
                    if resp.ok:
                        cand = json.loads(resp.text)
                        if wikidata.parse_entity(cand, qid)["sherdog_id"] == f["sherdog_id"]:
                            payload = cand
                if payload is None:
                    found = _resolve_by_name(StubJob(), client, fid, f["name"],
                                             f["sherdog_id"])
                    if found["outcome"] is None:
                        qid, payload = found["qid"], found["payload"]
                if payload is None:
                    rec["note"] = "no verified article"
                else:
                    rec["qid"] = qid
                    title = wikidata.parse_sitelinks(payload, qid).get("en.wikipedia")
                    if not title:
                        rec["note"] = "verified, but no English article"
                    else:
                        rec["en_title"] = title
                        rec["created_utc"] = first_revision(title) or ""
                        time.sleep(1.0)
            except Exception as exc:
                rec["note"] = f"error: {exc!r}"
            w.writerow(rec); fh.flush()
            if n % 50 == 0:
                print(f"  [articles] {n}/{len(todo)}", flush=True)


def eligible(rows):
    arts = {int(r["fighter_id"]): r for r in read_csv(ART)}
    bouts = {}
    for r in rows:
        bouts.setdefault(r["bout_id"], []).append(r)
    out = []
    for bid, fs in bouts.items():
        if len(fs) != 2:
            continue
        fight = fs[0]["date"]
        ok = True
        for f in fs:
            a = arts.get(f["fighter_id"])
            if not a or not a["en_title"] or not a["created_utc"]:
                ok = False; break
            created = date.fromisoformat(a["created_utc"][:10])
            if created > fight - timedelta(days=MIN_ARTICLE_AGE):
                ok = False; break
        if ok:
            out.append((bid, fight, [(f, arts[f["fighter_id"]]) for f in fs]))
    return out


def page_state_at(title, cutoff):
    """'article', 'redirect' or 'no revision yet' for `title` as it stood at the end of
    `cutoff` (UTC). The first-revision date alone overstates an article's age when the
    page began life as a redirect -- 21 of sample B's 415 articles did."""
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2",
        "prop": "revisions", "titles": title, "rvdir": "older", "rvlimit": "1",
        "rvstart": f"{cutoff.isoformat()}T23:59:59Z", "rvprop": "timestamp|content",
        "rvslots": "main", "redirects": "1", "maxlag": "5"})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    revs = data["query"]["pages"][0].get("revisions") or []
    if not revs:
        return "no revision yet"
    txt = revs[0]["slots"]["main"].get("content", "")
    return "redirect" if txt.lstrip().upper().startswith("#REDIRECT") else "article"


def phase_state(bouts):
    done = {(int(r["bout_id"]), int(r["fighter_id"])) for r in read_csv(STATE)}
    todo = [(bid, fight, f, a) for bid, fight, fs in bouts for f, a in fs
            if (bid, f["fighter_id"]) not in done]
    print(f"[state] {len(bouts)} age-eligible bouts, {len(todo)} page states to check",
          flush=True)
    new = not STATE.exists()
    with STATE.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["bout_id", "fighter_id", "cutoff", "state"])
        if new:
            w.writeheader()
        for n, (bid, fight, f, a) in enumerate(todo, 1):
            cutoff = fight - timedelta(days=MIN_ARTICLE_AGE)
            try:
                st = page_state_at(a["en_title"], cutoff)
            except Exception as exc:
                st = f"error: {exc!r}"
            w.writerow({"bout_id": bid, "fighter_id": f["fighter_id"],
                        "cutoff": cutoff, "state": st})
            fh.flush()
            time.sleep(1.0)
            if n % 100 == 0:
                print(f"  [state] {n}/{len(todo)}", flush=True)


def real_articles_only(bouts):
    """Keep a bout only when BOTH fighters' pages were real articles at the cutoff."""
    st = {(int(r["bout_id"]), int(r["fighter_id"])): r["state"] for r in read_csv(STATE)}
    return [b for b in bouts
            if all(st.get((b[0], f["fighter_id"])) == "article" for f, _ in b[2])]


def phase_views(bouts, client):
    done = {(int(r["bout_id"]), int(r["fighter_id"])) for r in read_csv(VIEWS)}
    todo = [(bid, fight, f, a) for bid, fight, fs in bouts for f, a in fs
            if (bid, f["fighter_id"]) not in done]
    print(f"[views] {len(bouts)} eligible bouts, {len(todo)} fighter-windows to fetch",
          flush=True)
    new = not VIEWS.exists()
    with VIEWS.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=VIEW_FIELDS)
        if new:
            w.writeheader()
        for n, (bid, fight, f, a) in enumerate(todo, 1):
            start, end = fight + timedelta(days=W1[0]), fight + timedelta(days=W2[1])
            rec = {"bout_id": bid, "fighter_id": f["fighter_id"], "fight_date": fight,
                   "en_title": a["en_title"], "start": start, "end": end,
                   "status": "", "days_returned": 0, "views_w1": "", "views_w2": ""}
            resp = client.get(pageviews.daily_article_url(
                "en.wikipedia", a["en_title"], start, end))
            if resp.status == 404:
                rec["status"] = "no data in window"
            elif not resp.ok:
                rec["status"] = f"HTTP {resp.status}"
            else:
                days = pageviews.parse_daily_views(json.loads(resp.text))
                # Rule 2: anything outside the requested pre-fight window is a hard
                # stop, not something to filter quietly.
                stray = [d for d in days if not (start <= d <= end)]
                if stray:
                    raise SystemExit(f"API returned days outside window for bout {bid}: "
                                     f"{stray[:3]} -- stopping, nothing kept")
                w1_lo, w1_hi = fight + timedelta(days=W1[0]), fight + timedelta(days=W1[1])
                rec.update(status="ok", days_returned=len(days),
                           views_w1=sum(v for d, v in days.items() if w1_lo <= d <= w1_hi),
                           views_w2=sum(v for d, v in days.items() if d > w1_hi))
            w.writerow(rec); fh.flush()
            if n % 100 == 0:
                print(f"  [views] {n}/{len(todo)}", flush=True)


def phase_stats(bouts):
    views = {(int(r["bout_id"]), int(r["fighter_id"])): r for r in read_csv(VIEWS)}
    n1, n2 = W1[1] - W1[0] + 1, W2[1] - W2[0] + 1
    d_log, d_raw, d_rand = [], [], []
    no_data = 0
    rng = random.Random(27)
    for bid, fight, fs in bouts:
        per = {}
        for f, _ in fs:
            v = views.get((bid, f["fighter_id"]))
            if not v or v["status"] != "ok":
                per = None; break
            m1, m2 = int(v["views_w1"]) / n1, int(v["views_w2"]) / n2
            per[f["result"]] = (math.log1p(m2) - math.log1p(m1), m2 - m1)
        if per is None or set(per) != {"win", "loss"}:
            no_data += 1
            continue
        dl = per["win"][0] - per["loss"][0]
        d_log.append(dl)
        d_raw.append(per["win"][1] - per["loss"][1])
        d_rand.append(dl if rng.random() < 0.5 else -dl)

    def summ(xs):
        return (len(xs), statistics.mean(xs), statistics.stdev(xs)) if len(xs) > 1 else (len(xs), None, None)

    out = [
        ("log1p mean daily views, winner minus loser (primary)", *summ(d_log)),
        ("log1p mean daily views, random corner order", *summ(d_rand)),
        ("raw mean daily views, winner minus loser", *summ(d_raw)),
    ]
    print(f"\n[stats] eligible bouts {len(bouts)}, used {len(d_log)}, "
          f"dropped (a window with no data) {no_data}")
    for label, n, mu, sd in out:
        print(f"  {label:58s} n={n:<5} mean={mu:>9.4f}  SD={sd:>9.4f}")
    with open(DATA / "g_power.csv", "w", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["measure", "n_bouts", "mean", "sd"])
        cw.writerows(out)


def main():
    phases = sys.argv[1:] or ["articles", "state", "views", "stats"]
    with connect() as c:
        rows = unanimous_bouts(c)
    with Client(cache_dir=OBS / "cache") as client:
        if "articles" in phases:
            phase_articles(rows, client)
        bouts = eligible(rows)
        if "state" in phases:
            phase_state(bouts)
        age_ok = len(bouts)
        bouts = real_articles_only(bouts)
        print(f"[eligible] {age_ok} pass the first-revision age rule, {len(bouts)} were "
              f"real articles for both fighters at fight - {MIN_ARTICLE_AGE} days",
              flush=True)
        if "views" in phases:
            phase_views(bouts, client)
    if "stats" in phases:
        phase_stats(bouts)


if __name__ == "__main__":
    main()
