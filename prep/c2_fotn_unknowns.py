"""C, part 2: resolve Fight of the Night for the events c_wiki_cards.py left unknown.

Two shapes the observatory parser does not read:
  * a Finale whose Wikipedia coverage is its TUF season page -- the bonus awards sit
    under an h3 inside that page, not an h2 of their own;
  * "Fight of the Night award: A vs. B" -- the extra word "award" (UFC Fight Night:
    Volkov vs. Rozenstruik).
Same /wiki/ pages through the observatory client, same pair matcher as before.
Writes data/wiki_fotn_fixes.csv: one row per unknown event, with the raw FOTN line
kept as evidence, and the bout it matched.
"""
import csv
import re
import sys

from selectolax.parser import HTMLParser

from db import DATA, OBS, UNIVERSE, connect

sys.path.insert(0, str(OBS))
from ingest.wiki_cards import match_bonus_fighter, match_bout_fighters  # noqa: E402
from observatory.http import Client                  # noqa: E402

FOTN = re.compile(r"^fight of the night(?:\s+awards?)?\s*(?:\([^)]*\))?\s*:\s*(.+)$", re.I)
NONE = re.compile(r"\b(no|none|not)\b.*award", re.I)


def fotn_lines(html):
    tree = HTMLParser(html)
    out = []
    for h in tree.css("h2, h3, h4"):
        if "bonus" not in h.text(strip=True).lower():
            continue
        sec = h.parent.parent if h.parent.tag == "div" else h.parent
        for li in sec.css("li"):
            text = re.sub(r"\s+", " ", li.text(separator=" ", strip=True)).strip()
            if FOTN.match(text):
                out.append(text)
        # Some pages write the awards as one paragraph, not a list (UFC 225).
        for p in sec.css("p"):
            text = re.sub(r"\s+", " ", p.text(separator=" ", strip=True)).strip()
            for m in re.finditer(r"Fight of the Night[^:]*:\s*[^.]*?(?=\s*(?:\(|Performance of|$))",
                                 text, re.I):
                if m.group(0) not in out:
                    out.append(m.group(0))
    return out


def main():
    ev = [e for e in csv.DictReader(open(DATA / "wiki_events.csv"))
          if e["status"] == "ok"
          and (e["bonus_section"] != "True" or int(e["fotn_names"]) == 0)
          and not NONE.search(e["unmatched_fotn_names"] or "")]
    with connect() as c:
        cands = c.execute(f"""
            with u as ({UNIVERSE})
            select u.event_id, bf.fighter_id, f.full_name, bf.bout_id
              from u join bout_fighters bf using(bout_id) join fighters f using(fighter_id)
             where u.event_id = any(%s)""", ([int(e["event_id"]) for e in ev],)).fetchall()
    by_ev = {}
    for r in cands:
        by_ev.setdefault(r["event_id"], []).append(r)

    rows = []
    with Client(cache_dir=OBS / "cache") as client:
        for e in ev:
            eid = int(e["event_id"])
            from observatory.sources import wikipedia
            resp = client.get(wikipedia.article_url(e["wiki_page"]))
            lines = fotn_lines(resp.text) if resp.ok else []
            if not lines:
                rows.append({"event_id": eid, "event_name": e["event_name"],
                             "wiki_page": e["wiki_page"], "fotn_line": "",
                             "bout_id": "", "status": "no FOTN line found"})
                continue
            for line in lines:
                body = FOTN.match(line).group(1)
                if NONE.search(body):
                    rows.append({"event_id": eid, "event_name": e["event_name"],
                                 "wiki_page": e["wiki_page"], "fotn_line": line,
                                 "bout_id": "", "status": "not awarded"})
                    continue
                body = re.sub(r"\s*\(.*$", "", body)      # trailing "(... missed weight)"
                pair = [p.strip().rstrip(".") for p in re.split(r"\s+vs\.?\s+", body)]
                if len(pair) == 2:
                    m = match_bout_fighters(pair[0], pair[1], by_ev.get(eid, []))
                else:
                    # One named fighter (e.g. the other forfeited his share): the bout
                    # is that fighter's, since a fighter fights once per card.
                    hit = match_bonus_fighter(pair[0], by_ev.get(eid, []))
                    m = ({"status": "matched", "bout_id": hit["bout_id"]} if hit
                         else {"status": "unmatched"})
                rows.append({"event_id": eid, "event_name": e["event_name"],
                             "wiki_page": e["wiki_page"], "fotn_line": line,
                             "bout_id": m.get("bout_id", ""),
                             "status": "matched" if m["status"] == "matched"
                                       else f"pair {m['status']}"})

    with open(DATA / "wiki_fotn_fixes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(f"{r['event_name'][:42]:42s} {r['status']:16s} {r['fotn_line'][:70]}")


if __name__ == "__main__":
    main()
