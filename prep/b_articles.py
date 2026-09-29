"""B, part 1: every split-decision fighter's English article and its creation date.

Identity: a fighter's article is accepted only through the Wikidata QID already
stored in the observatory (verified there by its Sherdog ID, P2818), and that ID is
re-checked here against the same payload the title comes from. Five fighters whose
Wikidata item has no P2818 at all were verified by hand on 2026-09-20 (the item's
own description names them as mixed martial artists, same name, same era); they are
kept, marked verification='manual', so the sample can be rebuilt without them.

Creation date: first revision's timestamp from en.wikipedia.org/w/api.php. That
path is disallowed by robots.txt; the operator authorised it for this analysis, so
it is called here directly and NOT through the observatory's HTTP client, which
refuses it by design. Paced at 1 request/second.

Resumable: fighters already in data/fighter_articles.csv are skipped.
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request

from db import DATA, OBS, UNIVERSE, connect

sys.path.insert(0, str(OBS))
from observatory.http import Client               # noqa: E402
from observatory.sources import wikidata, wikipedia  # noqa: E402

OUT = DATA / "fighter_articles.csv"
FIELDS = ["fighter_id", "name", "sherdog_id", "qid", "verification",
          "en_title", "created_utc", "note"]
UA = "FirstLightObservatory/1.0 (baptperr18@gmail.com) SSAC27 research query"
API = "https://en.wikipedia.org/w/api.php"

# Hand-verified 2026-09-20: real article, Wikidata item carries no P2818.
MANUAL = {"Joanderson Brito", "Hyder Amil", "Rabindra Dhant", "Rhys McKee",
          "Adam Fugitt"}

WINDOW = ("2015-08-30", "2026-08-20")


def split_fighters(conn):
    return conn.execute(f"""
        with u as ({UNIVERSE}),
        sd as (select u.bout_id from u join bout_fighters bf using(bout_id)
                where u.event_kind = 'ufc_card'
                  and u.date between %s and %s
                group by 1
               having min(bf.method) = 'Decision (Split)'
                  and max(bf.method) = 'Decision (Split)')
        select distinct f.fighter_id, f.full_name as name,
               s.external_id as sherdog_id, w.external_id as qid
          from sd join bout_fighters bf using(bout_id)
          join fighters f using(fighter_id)
          join fighter_ids s on s.fighter_id = f.fighter_id and s.source = 'sherdog'
          left join fighter_ids w on w.fighter_id = f.fighter_id and w.source = 'wikidata'
         order by f.fighter_id""", WINDOW).fetchall()


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


def main():
    done = set()
    if OUT.exists():
        with OUT.open() as f:
            done = {int(r["fighter_id"]) for r in csv.DictReader(f)}
    with connect() as c:
        seeds = [s for s in split_fighters(c) if s["fighter_id"] not in done]
    print(f"{len(seeds)} fighters to look up ({len(done)} already cached)", flush=True)

    new_file = not OUT.exists()
    with OUT.open("a", newline="") as f, \
            Client(cache_dir=OBS / "cache") as client:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for n, s in enumerate(seeds, 1):
            rec = {"fighter_id": s["fighter_id"], "name": s["name"],
                   "sherdog_id": s["sherdog_id"], "qid": s["qid"] or "",
                   "verification": "", "en_title": "", "created_utc": "", "note": ""}
            try:
                qid, manual = s["qid"], False
                if not qid and s["name"] in MANUAL:
                    resp = client.get(wikipedia.article_url(s["name"]))
                    qid = wikipedia.parse_article(resp.text)["qid"] if resp.ok else None
                    manual = bool(qid)
                if not qid:
                    rec["note"] = "no verified article"
                else:
                    rec["qid"] = qid
                    resp = client.get(wikidata.entity_url(qid))
                    payload = json.loads(resp.text)
                    ent = wikidata.parse_entity(payload, qid)
                    if not manual and ent["sherdog_id"] != s["sherdog_id"]:
                        rec["note"] = f"P2818 no longer matches ({ent['sherdog_id']})"
                    else:
                        rec["verification"] = "manual" if manual else "p2818"
                        title = wikidata.parse_sitelinks(payload, qid).get("en.wikipedia")
                        if not title:
                            rec["note"] = "verified, but no English article"
                        else:
                            rec["en_title"] = title
                            rec["created_utc"] = first_revision(title) or ""
                            time.sleep(1.0)
            except Exception as exc:
                rec["note"] = f"error: {exc!r}"
            w.writerow(rec)
            f.flush()
            if n % 50 == 0:
                print(f"  {n}/{len(seeds)}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
