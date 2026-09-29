"""E: how many split-decision bouts in the study window have closing odds available
on BestFightOdds, measured bout by bout. Coverage only -- no odds values are stored.

BFO's robots.txt is "User-agent: * / Allow: /"; its /terms is a warranty disclaimer
with no licence grant (text recorded in data/e_licenses.md). What a settled event's
page serves is each still-listed book's LAST posted line, i.e. its closing line.
Older events serve the fight list with no lines at all: the per-book history sits
behind a scrambled JS endpoint the observatory deliberately does not decode, and
neither does this.

Reuses the observatory's BFO parser and matchers; fetches through its HTTP client
(robots-checked, 2s pacing). Writes data/e_bfo_coverage.csv, one row per bout.
"""
import csv
import sys

from db import DATA, OBS, UNIVERSE, connect

sys.path.insert(0, str(OBS))
from ingest.odds import match_bfo_event                      # noqa: E402
from ingest.wiki_cards import match_bout_fighters            # noqa: E402
from observatory.http import Client                          # noqa: E402
from observatory.sources import bestfightodds as bfo         # noqa: E402

WINDOW = ("2015-08-30", "2026-08-20")


def main():
    with connect() as c:
        split = c.execute(f"""
            with u as ({UNIVERSE})
            select u.bout_id, u.event_id, u.event_name, u.date from u
              join bout_fighters bf using(bout_id)
             where u.event_kind = 'ufc_card' and u.date between %s and %s
             group by 1, 2, 3, 4
            having min(bf.method) = 'Decision (Split)'
               and max(bf.method) = 'Decision (Split)'""", WINDOW).fetchall()
        cands = c.execute(f"""
            with u as ({UNIVERSE})
            select u.event_id, bf.fighter_id, f.full_name, bf.bout_id
              from u join bout_fighters bf using(bout_id) join fighters f using(fighter_id)
             where u.event_kind = 'ufc_card' and u.date between %s and %s""",
                          WINDOW).fetchall()
    by_event = {}
    for r in cands:
        by_event.setdefault(r["event_id"], []).append(r)
    events = {}
    for s in split:
        events.setdefault(s["event_id"], s)

    out = {s["bout_id"]: {"bout_id": s["bout_id"], "event_id": s["event_id"],
                          "fight_date": s["date"], "bfo_event": "", "status": "",
                          "listed_on_page": False, "has_odds": False, "n_books": 0}
           for s in split}
    with Client(cache_dir=OBS / "cache") as client:
        sm = bfo.parse_sitemap(client.get(bfo.EVENTS_SITEMAP_URL).text)
        for n, (eid, ev) in enumerate(sorted(events.items(), key=lambda t: t[1]["date"]), 1):
            mine = [b for b in out.values() if b["event_id"] == eid]
            m = match_bfo_event(ev["event_name"], ev["date"], sm)
            if m["status"] != "matched":
                for b in mine:
                    b["status"] = f"event {m['status']} on BFO"
                continue
            resp = client.get(m["url"])
            if not resp.ok:
                for b in mine:
                    b["status"] = f"HTTP {resp.status}"
                continue
            page = bfo.parse_event_page(resp.text)
            for b in mine:
                b["bfo_event"], b["status"] = m["url"], "page ok, bout not listed"
            for mu in page["matchups"]:
                hit = match_bout_fighters(mu["fighter_a"]["name"], mu["fighter_b"]["name"],
                                          by_event.get(eid, []))
                if hit["status"] != "matched" or hit["bout_id"] not in out:
                    continue
                b = out[hit["bout_id"]]
                books = {o.get("book") for o in mu["odds"]}
                b.update(listed_on_page=True, has_odds=bool(mu["odds"]),
                         n_books=len(books),
                         status="odds" if mu["odds"] else "listed, no lines served")
            if n % 50 == 0:
                print(f"  {n}/{len(events)}", flush=True)

    rows = sorted(out.values(), key=lambda b: (b["fight_date"], b["bout_id"]))
    with open(DATA / "e_bfo_coverage.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"done: {sum(r['has_odds'] for r in rows)}/{len(rows)} split bouts have "
          f"BFO closing lines", flush=True)


if __name__ == "__main__":
    main()
