"""A. Sanity: bouts per year, one row per bout, decisions by type."""
import csv

from db import DATA, UNIVERSE, connect

with connect() as c:
    per_bout = c.execute(f"""
        with u as ({UNIVERSE}),
        m as (select bout_id, min(method) method, count(*) nf,
                     count(distinct method) nmethods, count(result) nres
                from bout_fighters group by bout_id)
        select u.*, m.method, m.nf, m.nmethods, m.nres
          from u join m using(bout_id)""").fetchall()
    dup_pairs = c.execute(f"""
        with u as ({UNIVERSE})
        select u.event_id, array_agg(bf.fighter_id order by bf.fighter_id) pair,
               count(*) over (partition by u.event_id,
                   array_agg(bf.fighter_id order by bf.fighter_id)) n
          from u join bout_fighters bf using(bout_id)
         group by u.event_id, u.bout_id""").fetchall()

clean = [r for r in per_bout if r["event_kind"] == "ufc_card"]

print("integrity (ufc_card bouts):")
print(f"  bouts                          {len(clean)}")
print(f"  distinct bout_ids              {len({r['bout_id'] for r in clean})}")
print(f"  not exactly 2 fighter rows     {sum(r['nf'] != 2 for r in clean)}")
print(f"  fighters disagree on method    {sum(r['nmethods'] > 1 for r in clean)}")
print(f"  missing a result               {sum(r['nres'] != 2 for r in clean)}")
print(f"  same pair twice on one event   {sum(1 for d in dup_pairs if d['n'] > 1)}")

def kind(r):
    # Decided on the RESULT, not the method: an ingested-but-unfought bout carries
    # placeholder method text ('N/A', 'Referee') or none at all.
    if r["nres"] != 2:
        return "awaiting_result"
    m = r["method"]
    return {"Decision (Unanimous)": "unanimous", "Decision (Split)": "split",
            "Decision (Majority)": "majority"}.get(m) or (
        "technical_decision" if m.startswith("Technical Decision") else
        "draw" if m.startswith("Draw") else
        "no_contest" if m.startswith("No Contest") else "finish_or_other")

cols = ["unanimous", "split", "majority", "technical_decision", "draw",
        "no_contest", "finish_or_other", "awaiting_result"]
rows = {}
for r in clean:
    y = r["date"].year
    t = rows.setdefault(y, {"year": y, "events": set(), "bouts": 0, **{k: 0 for k in cols}})
    t["events"].add(r["event_id"]); t["bouts"] += 1; t[kind(r)] += 1
out = []
for y in sorted(rows):
    t = rows[y]; t["events"] = len(t["events"]); out.append(t)
tot = {"year": "total", "events": sum(t["events"] for t in out),
       "bouts": sum(t["bouts"] for t in out), **{k: sum(t[k] for t in out) for k in cols}}

print(f"\n{'year':>6} {'events':>6} {'bouts':>6} " + " ".join(f"{k[:9]:>9}" for k in cols))
for t in out + [tot]:
    print(f"{t['year']:>6} {t['events']:>6} {t['bouts']:>6} " +
          " ".join(f"{t[k]:>9}" for k in cols))

excluded = {}
for r in per_bout:
    if r["event_kind"] != "ufc_card":
        e = excluded.setdefault(r["event_kind"], [0, 0]); e[0] += 1
        e[1] += r["method"] == "Decision (Split)"
print("\nexcluded from the universe (bouts, of which split decisions):")
for k, (n, s) in excluded.items():
    print(f"  {k:22s} {n:>4}  {s:>3}")

with open(DATA / "a_bouts_per_year.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["year", "events", "bouts"] + cols)
    w.writeheader(); w.writerows(out + [tot])
