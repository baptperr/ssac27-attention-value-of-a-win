"""B, part 2: the paired split-decision sample.

  UFC cards only (exhibitions, Road to UFC and the mislabelled regional show excluded
  by db.UNIVERSE), fight date 2015-08-30..2026-08-20, method exactly
  'Decision (Split)' for both corners -- which by construction excludes any result
  later overturned to a no contest, since Sherdog replaces the method when it is
  overturned -- and BOTH fighters with an English article created >= 60 days before
  the fight.

Reads data/fighter_articles.csv (b_articles.py). Writes data/b_candidates.csv --
bouts passing the first-revision age rule. b_state_at_cutoff.py then checks each
page was a real article (not a redirect) at the cutoff and writes the final
data/b_sample.csv.
"""
import csv
from collections import Counter
from datetime import date, timedelta

from db import DATA, UNIVERSE, connect

WINDOW = ("2015-08-30", "2026-08-20")
MIN_ARTICLE_AGE = 60


def main():
    with connect() as c:
        rows = c.execute(f"""
            with u as ({UNIVERSE}),
            sd as (select u.bout_id from u join bout_fighters bf using(bout_id)
                    where u.event_kind = 'ufc_card' and u.date between %s and %s
                    group by 1
                   having min(bf.method) = 'Decision (Split)'
                      and max(bf.method) = 'Decision (Split)')
            select u.bout_id, u.date, u.event_id, u.event_name, bf.fighter_id,
                   bf.result, f.full_name
              from sd join u using(bout_id) join bout_fighters bf using(bout_id)
              join fighters f using(fighter_id)
             order by u.date, u.bout_id""", WINDOW).fetchall()
        overturned_in_window = c.execute(f"""
            with u as ({UNIVERSE})
            select count(distinct u.bout_id) n from u join bout_fighters bf using(bout_id)
             where u.event_kind = 'ufc_card' and u.date between %s and %s
               and bf.method ~* 'overturned'""", WINDOW).fetchone()["n"]

    with open(DATA / "fighter_articles.csv") as f:
        arts = {int(r["fighter_id"]): r for r in csv.DictReader(f)}

    bouts = {}
    for r in rows:
        bouts.setdefault(r["bout_id"], []).append(r)

    sample, why = [], Counter()
    for bid, fs in bouts.items():
        fight = fs[0]["date"]
        cutoff = fight - timedelta(days=MIN_ARTICLE_AGE)
        reasons = []
        for f in fs:
            a = arts.get(f["fighter_id"])
            if a is None:
                reasons.append("not looked up")
            elif not a["en_title"]:
                reasons.append("no English article")
            elif not a["created_utc"]:
                reasons.append("no creation date")
            elif date.fromisoformat(a["created_utc"][:10]) > cutoff:
                reasons.append("article < 60 days old at fight")
        if reasons:
            # A bout fails for its WORST reason, counted once.
            order = ["not looked up", "no creation date", "no English article",
                     "article < 60 days old at fight"]
            why[min(reasons, key=order.index)] += 1
            continue
        w = next(f for f in fs if f["result"] == "win")
        l = next(f for f in fs if f["result"] == "loss")
        aw, al = arts[w["fighter_id"]], arts[l["fighter_id"]]
        sample.append({
            "bout_id": bid, "fight_date": fight, "event_id": fs[0]["event_id"],
            "event_name": fs[0]["event_name"],
            "winner_id": w["fighter_id"], "winner": w["full_name"],
            "winner_title": aw["en_title"], "winner_created": aw["created_utc"][:10],
            "winner_verification": aw["verification"],
            "loser_id": l["fighter_id"], "loser": l["full_name"],
            "loser_title": al["en_title"], "loser_created": al["created_utc"][:10],
            "loser_verification": al["verification"],
            "any_manual": "manual" in (aw["verification"], al["verification"]),
        })

    with open(DATA / "b_candidates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sample[0]))
        w.writeheader(); w.writerows(sample)

    manual = sum(s["any_manual"] for s in sample)
    print(f"split-decision bouts in window          {len(bouts)}")
    print(f"  overturned-to-NC bouts in window (any method, already not 'split') "
          f"{overturned_in_window}")
    for k, v in why.most_common():
        print(f"  dropped: {k:34s} {v}")
    print(f"candidates (first-revision age rule)     {len(sample)}")
    print(f"  of which rely on a hand-verified fighter {manual} "
          f"(-> {len(sample) - manual} without them)")


if __name__ == "__main__":
    main()
