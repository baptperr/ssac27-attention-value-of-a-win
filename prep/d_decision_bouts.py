"""Every decision bout on a UFC card, 2015-08-30..2026-08-20, with Fight of the Night
and card position. Writes data/decision_bouts.csv.

FOTN comes from the Wikipedia event pages: c_wiki_cards.py's flags, overridden by
c2_fotn_unknowns.py for the 11 events that parser left unknown. An event whose
bonus awards say FOTN was not awarded is a real "no".
Card position is Wikipedia's card section (main_event / co_main / main_card /
prelims / early_prelims / full_card); where Wikipedia did not match the bout, the
Sherdog main-event flag is kept as a fallback and marked as such.
"""
import csv
from collections import Counter

from db import DATA, UNIVERSE, connect

WINDOW = ("2015-08-30", "2026-08-20")


def main():
    with connect() as c:
        rows = c.execute(f"""
            with u as ({UNIVERSE})
            select u.bout_id, u.event_id, u.date, u.event_name, u.is_main, min(bf.method) method
              from u join bout_fighters bf using(bout_id)
             where u.event_kind = 'ufc_card' and u.date between %s and %s
             group by 1, 2, 3, 4, 5
            having min(bf.method) ~ '^(Technical )?Decision'""", WINDOW).fetchall()

    wiki = {int(r["bout_id"]): r for r in csv.DictReader(open(DATA / "wiki_bouts.csv"))}
    wev = {int(r["event_id"]): r for r in csv.DictReader(open(DATA / "wiki_events.csv"))}
    fixes = list(csv.DictReader(open(DATA / "wiki_fotn_fixes.csv")))
    fixed_events = {int(f["event_id"]) for f in fixes}
    fixed_fotn = {int(f["bout_id"]) for f in fixes if f["status"] == "matched"}
    b_ids = {int(r["bout_id"]) for r in csv.DictReader(open(DATA / "b_sample.csv"))}

    out = []
    for r in rows:
        bid, eid = r["bout_id"], r["event_id"]
        w, e = wiki.get(bid, {}), wev.get(eid, {})
        if eid in fixed_events:
            fotn, src = bid in fixed_fotn, "wikipedia (resolved by hand-rule)"
        elif e.get("status") == "ok" and e.get("bonus_section") == "True":
            fotn, src = w.get("fotn") == "True", "wikipedia"
        else:
            fotn, src = None, "unknown"
        if w.get("card_section"):
            pos, pos_src = w["card_section"], "wikipedia"
        elif r["is_main"]:
            pos, pos_src = "main_event", "sherdog is_main"
        else:
            pos, pos_src = "", "unknown"
        out.append({
            "bout_id": bid, "event_id": eid, "fight_date": r["date"],
            "event_name": r["event_name"],
            "decision": r["method"].replace("Decision (", "").rstrip(")").lower()
                        .replace("technical ", "technical_").replace(" (", "_"),
            "fotn": "" if fotn is None else fotn, "fotn_source": src,
            "card_position": pos, "card_position_source": pos_src,
            "is_title": w.get("is_title", ""), "in_sample_b": bid in b_ids,
        })

    with open(DATA / "decision_bouts.csv", "w", newline="") as f:
        cw = csv.DictWriter(f, fieldnames=list(out[0])); cw.writeheader(); cw.writerows(out)

    n = len(out)
    print(f"decision bouts in window: {n}  {dict(Counter(o['decision'] for o in out))}")
    print(f"  FOTN status known: {sum(o['fotn'] != '' for o in out)}/{n}")
    print(f"  FOTN bouts: {sum(o['fotn'] is True for o in out)}")
    for d, k in sorted(Counter(o["decision"] for o in out).items()):
        f_ = sum(o["fotn"] is True for o in out if o["decision"] == d)
        print(f"    {d:22s} {f_:>4} of {k:>4}  ({100 * f_ / k:.1f}%)")
    print(f"  card position known: {sum(bool(o['card_position']) for o in out)}/{n} "
          f"(wikipedia {sum(o['card_position_source'] == 'wikipedia' for o in out)}, "
          f"sherdog main-event fallback {sum(o['card_position_source'] == 'sherdog is_main' for o in out)})")
    print(f"  {dict(Counter(o['card_position'] or 'unknown' for o in out).most_common())}")
    bb = [o for o in out if o["in_sample_b"]]
    print(f"sample B: {len(bb)} bouts, FOTN {sum(o['fotn'] is True for o in bb)}, "
          f"FOTN unknown {sum(o['fotn'] == '' for o in bb)}")


if __name__ == "__main__":
    main()
