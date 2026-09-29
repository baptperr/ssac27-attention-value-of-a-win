"""Coverage report for sample B: C (FOTN), E (odds), F (card position / title).

Reads the CSVs the other steps wrote plus the observatory DB (read-only).
"""
import csv
from collections import Counter

from db import DATA, connect


def read(name):
    p = DATA / name
    if not p.exists():
        return None
    with p.open() as f:
        return list(csv.DictReader(f))


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.1f}%)" if b else f"{a}/0"


def main():
    sample = read("b_sample.csv")
    if not sample:
        raise SystemExit("data/b_sample.csv missing -- run b_sample.py first")
    ids = [int(s["bout_id"]) for s in sample]
    n = len(ids)
    print(f"SAMPLE B: {n} bouts\n")

    # --- C: Fight of the Night (from d_decision_bouts.py, which folds in the resolved
    # unknowns of c2_fotn_unknowns.py) ------------------------------------------------
    wiki = {int(r["bout_id"]): r for r in (read("wiki_bouts.csv") or [])}
    dec = {int(r["bout_id"]): r for r in (read("decision_bouts.csv") or [])}
    known = [b for b in ids if dec.get(b, {}).get("fotn") in ("True", "False")]
    fotn = [b for b in ids if dec.get(b, {}).get("fotn") == "True"]
    print("C. Fight of the Night")
    print(f"  B bouts with known FOTN status                  {pct(len(known), n)}")
    print(f"  FOTN bouts in B                                  {pct(len(fotn), n)}")
    allk = [r for r in dec.values() if r["fotn"] in ("True", "False")]
    print(f"  all decision bouts in window: "
          f"{sum(r['fotn'] == 'True' for r in allk)} FOTN of {len(allk)}\n")

    # --- E: closing odds -------------------------------------------------------------
    cov = {int(r["bout_id"]): r for r in (read("e_bfo_coverage.csv") or [])}
    with connect() as c:
        db_odds = {r["bout_id"] for r in c.execute(
            "select distinct bout_id from odds where bout_id = any(%s)", (ids,))}
        db = {r["bout_id"]: r for r in c.execute("""
            select b.bout_id, b.bout_order, b.is_main, b.is_title,
                   (b.bout_order = max(b.bout_order) over (partition by b.event_id) - 1)
                       as second_from_top,
                   bb.section_tier, bb.card_section
              from bouts b left join bout_billing bb using(bout_id)
             where b.event_id in (select event_id from bouts where bout_id = any(%s))""",
            (ids,)).fetchall() if r["bout_id"] in set(ids)}
    bfo = [b for b in ids if cov.get(b, {}).get("has_odds") == "True"]
    books = Counter(int(cov[b]["n_books"]) for b in bfo)
    print("E. Closing odds")
    print(f"  in observatory DB (captured since 2026-09-19)    {pct(len(db_odds), n)}")
    print(f"  available on BestFightOdds (bout-level)         {pct(len(bfo), n)}")
    if bfo:
        yrs = Counter(cov[b]["fight_date"][:4] for b in bfo)
        print(f"    by year: {dict(sorted(yrs.items()))}")
        print(f"    books per bout: {dict(sorted(books.items()))}")
    status = Counter(cov.get(b, {}).get("status", "not measured") for b in ids)
    print(f"    status: {dict(status)}")
    print("  licence: BFO grants none (terms = warranty disclaimer); Kaggle unchecked "
          "-- see data/e_licenses.md\n")

    # --- F: card position and title flag -------------------------------------------
    print("F. Card position / title")
    print("  from the observatory DB:")
    print(f"    bout order                                     "
          f"{pct(sum(db[b]['bout_order'] is not None for b in ids), n)}")
    print(f"    main-event flag (is_main)                      "
          f"{pct(sum(db[b]['is_main'] is not None for b in ids), n)}"
          f"   [{sum(bool(db[b]['is_main']) for b in ids)} main events]")
    print(f"    co-main (derived: second-highest bout order)   "
          f"{pct(n, n)}   [{sum(bool(db[b]['second_from_top']) for b in ids)} co-mains]"
          "  -- positional, see note")
    sect = [b for b in ids if db[b]["section_tier"]]
    print(f"    main card / prelims (bout_billing)             {pct(len(sect), n)}")
    print(f"    title flag, KNOWN (bout_billing present)       {pct(len(sect), n)}"
          f"   -- is_title is a default 'false' before 2024-09, not a fact")
    wsect = [b for b in ids if wiki.get(b, {}).get("section_tier")]
    print("  with this study's Wikipedia pass (data/wiki_bouts.csv):")
    print(f"    card section                                   {pct(len(wsect), n)}")
    print(f"    title flag                                     {pct(len(wsect), n)}"
          f"   [{sum(wiki[b]['is_title'] == 'True' for b in wsect)} title fights]")
    tiers = Counter(wiki[b]["card_section"] for b in wsect)
    print(f"    breakdown: {dict(tiers.most_common())}")
    both = [b for b in ids if db[b]["card_section"] and wiki.get(b, {}).get("card_section")]
    agree = sum(db[b]["card_section"] == wiki[b]["card_section"] for b in both)
    t_agree = sum(str(bool(db[b]["is_title"])) == wiki[b]["is_title"] for b in both)
    print(f"  cross-check vs the observatory's own billing, where both exist: "
          f"section agrees {agree}/{len(both)}, title agrees {t_agree}/{len(both)}")


if __name__ == "__main__":
    main()
