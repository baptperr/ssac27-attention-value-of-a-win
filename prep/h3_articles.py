"""H3 sample: English article + creation date for every fighter in a decision bout in the
window, so S can be computed on the same article rule as sample B.

Same identity chain as B and G: the observatory's verified Wikidata QID (P2818 checked
against the Sherdog id), or the fixed resolver when no QID is on file; then the first
revision's timestamp from /w/api.php. Nothing is written back to the observatory.

Reuses what B (fighter_articles.csv) and G (g_fighter_articles.csv) already looked up.
Resumable: data/h3_fighter_articles.csv.

NO pageviews here -- article identity only. Post-fight views wait for the OSF
pre-registration line in DECISIONS.md (CLAUDE.md rule 1).
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request

from db import DATA, OBS, UNIVERSE, connect

sys.path.insert(0, str(OBS))
from ingest.pageviews import _resolve_by_name          # noqa: E402
from observatory.http import Client                    # noqa: E402
from observatory.sources import wikidata               # noqa: E402

WINDOW = ("2015-08-30", "2026-08-20")
OUT = DATA / "h3_fighter_articles.csv"
FIELDS = ["fighter_id", "name", "sherdog_id", "qid", "en_title", "created_utc", "note"]
UA = "FirstLightObservatory/1.0 (baptperr18@gmail.com) SSAC27 research query"
API = "https://en.wikipedia.org/w/api.php"


class StubJob:
    def quarantine(self, kind, payload):
        pass


def first_revision(title):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2", "prop": "revisions",
        "titles": title, "rvdir": "newer", "rvlimit": "1", "rvprop": "timestamp",
        "redirects": "1", "maxlag": "5"})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    pages = d.get("query", {}).get("pages", [])
    revs = (pages[0].get("revisions") if pages else None) or []
    return revs[0]["timestamp"] if revs else None


def main():
    with connect() as c:
        rows = c.execute(f"""
            with u as ({UNIVERSE}),
            dec as (select u.bout_id from u join bout_fighters bf using(bout_id)
                     where u.event_kind = 'ufc_card' and u.date between %s and %s
                     group by 1 having min(bf.method) ~ '^(Technical )?Decision')
            select distinct f.fighter_id, f.full_name as name,
                   s.external_id as sherdog_id, w.external_id as qid
              from dec join bout_fighters bf using(bout_id)
              join fighters f using(fighter_id)
              join fighter_ids s on s.fighter_id = f.fighter_id and s.source = 'sherdog'
              left join fighter_ids w on w.fighter_id = f.fighter_id and w.source = 'wikidata'
             order by f.fighter_id""", WINDOW).fetchall()

    known = {}
    for f in ("fighter_articles.csv", "g_fighter_articles.csv", OUT.name):
        p = DATA / f
        if p.exists():
            for r in csv.DictReader(open(p)):
                known.setdefault(int(r["fighter_id"]), r)
    todo = [r for r in rows if r["fighter_id"] not in known]
    print(f"{len(rows)} fighters in decision bouts; {len(rows)-len(todo)} "
          f"already looked up by B/G/this run; {len(todo)} to do", flush=True)

    new = not OUT.exists()
    with OUT.open("a", newline="") as fh, Client(cache_dir=OBS / "cache") as client:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for n, f in enumerate(todo, 1):
            rec = {"fighter_id": f["fighter_id"], "name": f["name"],
                   "sherdog_id": f["sherdog_id"], "qid": f["qid"] or "",
                   "en_title": "", "created_utc": "", "note": ""}
            try:
                qid, payload = f["qid"], None
                if qid:
                    resp = client.get(wikidata.entity_url(qid))
                    if resp.ok:
                        cand = json.loads(resp.text)
                        if wikidata.parse_entity(cand, qid)["sherdog_id"] == f["sherdog_id"]:
                            payload = cand
                if payload is None:
                    found = _resolve_by_name(StubJob(), client, f["fighter_id"], f["name"],
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
            w.writerow(rec)
            fh.flush()
            if n % 50 == 0:
                print(f"  {n}/{len(todo)}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
