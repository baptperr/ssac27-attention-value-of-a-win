"""C (and F): Fight of the Night, card section and title status for every UFC card in
the study window, read from each event's own Wikipedia article.

Reuses the observatory's billing parser and matchers (observatory.sources.
wikipedia_cards, ingest.wiki_cards) as pure functions, but writes NOTHING to the
observatory database -- its own ingest_wiki_cards job overwrites bouts.is_title and
is deliberately bounded to the last 24 months, and neither is this study's call to
change. Output is CSV only.

All fetches are /wiki/<Title> pages through the observatory's HTTP client, i.e. the
one path en.wikipedia.org's robots.txt allows, at its 2s pacing.

Identity: a Wikipedia event is matched to one of our events by date (+-1 day, name
tokens only to split a double-header); a Wikipedia bout is matched to one of our
bouts by BOTH corners' names on that event. Anything that doesn't match is recorded
as unmatched, never guessed.

Outputs
  data/wiki_bouts.csv   one row per matched bout: section, position, title, FOTN
  data/wiki_events.csv  one row per event: what was found, for coverage reporting
"""
import csv
import sys

from db import DATA, OBS, UNIVERSE, connect

sys.path.insert(0, str(OBS))
from ingest.wiki_cards import (match_bonus_fighter, match_bout_fighters,  # noqa: E402
                               match_wiki_event)
from observatory.http import Client                                        # noqa: E402
from observatory.sources import wikipedia, wikipedia_cards                 # noqa: E402

WINDOW = ("2015-08-30", "2026-08-20")
LIST_PAGE = "List of UFC events"


def main():
    with connect() as c:
        events = c.execute(f"""
            with u as ({UNIVERSE})
            select distinct event_id, event_name as name, date from u
             where event_kind = 'ufc_card' and date between %s and %s
             order by date""", WINDOW).fetchall()
        fighters = c.execute(f"""
            with u as ({UNIVERSE})
            select u.event_id, bf.fighter_id, f.full_name, bf.bout_id
              from u join bout_fighters bf using(bout_id) join fighters f using(fighter_id)
             where u.event_kind = 'ufc_card' and u.date between %s and %s""",
                             WINDOW).fetchall()
    cands = {}
    for r in fighters:
        cands.setdefault(r["event_id"], []).append(r)
    print(f"{len(events)} UFC cards in window", flush=True)

    ev_rows, bout_rows = [], []
    with Client(cache_dir=OBS / "cache") as client:
        resp = client.get(wikipedia.article_url(LIST_PAGE))
        listed = wikipedia_cards.parse_event_list(resp.text) if resp.ok else []
        print(f"'{LIST_PAGE}': {len(listed)} entries", flush=True)

        # wiki entry per our event_id (date match, as the observatory job does)
        by_event = {}
        for we in listed:
            m = match_wiki_event(we["name"], we["date"], events)
            if m["status"] == "matched":
                by_event.setdefault(m["event_id"], we)

        for n, ev in enumerate(events, 1):
            eid = ev["event_id"]
            rec = {"event_id": eid, "event_date": ev["date"], "event_name": ev["name"],
                   "wiki_page": "", "status": "", "wiki_bouts": 0, "matched_bouts": 0,
                   "bonus_section": False, "fotn_names": 0, "fotn_bouts": 0,
                   "unmatched_fotn_names": ""}
            we = by_event.get(eid)
            if we is None:
                rec["status"] = "not on list page"
                ev_rows.append(rec)
                continue
            url = we.get("href") or wikipedia.article_url(we["name"])
            if not url.startswith("http"):
                rec["status"] = "bad href"
                ev_rows.append(rec)
                continue
            resp = client.get(url)
            if not resp.ok:
                rec["status"] = f"HTTP {resp.status}"
                ev_rows.append(rec)
                continue
            art = wikipedia.parse_article(resp.text)
            title = art["title"] or we["name"]
            rec["wiki_page"] = title
            results = wikipedia_cards.parse_results_page(resp.text, title)
            bouts = results[0]["bouts"] if results else []
            rec["wiki_bouts"] = len(bouts)

            ev_c = cands.get(eid, [])
            matched = {}
            for b in bouts:
                m = match_bout_fighters(b["fighter_a"]["name"], b["fighter_b"]["name"], ev_c)
                if m["status"] != "matched":
                    continue
                matched[m["bout_id"]] = {
                    "bout_id": m["bout_id"], "event_id": eid, "wiki_page": title,
                    "section_tier": b["section_tier"] or "",
                    "section_position": b["section_position"],
                    "card_section": wikipedia_cards.card_section_label(
                        b["section_tier"], b["section_position"]) or "",
                    "is_title": b["is_title"], "fotn": False}
            rec["matched_bouts"] = len(matched)

            bonuses = wikipedia_cards.parse_bonus_awards(resp.text)
            rec["bonus_section"] = bool(bonuses)
            names = bonuses.get("fight_of_the_night", [])
            rec["fotn_names"] = len(names)
            missed = []
            for nm in names:
                hit = match_bonus_fighter(nm, ev_c)
                if hit and hit["bout_id"] in matched:
                    matched[hit["bout_id"]]["fotn"] = True
                elif hit:
                    # FOTN bout exists on our card, but its row on the wiki table
                    # didn't match; still a real FOTN flag on a real bout.
                    matched.setdefault(hit["bout_id"], {
                        "bout_id": hit["bout_id"], "event_id": eid, "wiki_page": title,
                        "section_tier": "", "section_position": "", "card_section": "",
                        "is_title": "", "fotn": True})["fotn"] = True
                else:
                    missed.append(nm)
            rec["fotn_bouts"] = sum(1 for v in matched.values() if v["fotn"])
            rec["unmatched_fotn_names"] = "; ".join(missed)
            rec["status"] = "ok"
            ev_rows.append(rec)
            bout_rows.extend(matched.values())
            if n % 50 == 0:
                print(f"  {n}/{len(events)}  fetches={client.fetch_count}", flush=True)

    with open(DATA / "wiki_events.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ev_rows[0])); w.writeheader(); w.writerows(ev_rows)
    with open(DATA / "wiki_bouts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(bout_rows[0])); w.writeheader(); w.writerows(bout_rows)
    ok = [e for e in ev_rows if e["status"] == "ok"]
    print(f"done: {len(ok)}/{len(ev_rows)} events parsed, {len(bout_rows)} bouts matched, "
          f"{sum(e['fotn_bouts'] for e in ok)} FOTN bouts", flush=True)


if __name__ == "__main__":
    main()
