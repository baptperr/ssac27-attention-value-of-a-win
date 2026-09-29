"""Item 1: significant strikes landed by each fighter, per bout, for sample B, and the
winner's share of the total. From two Kaggle copies of ufcstats.com's fight totals
(ufcstats.com itself serves a bot challenge to non-browser clients and is not
fetched):

  used      jossilva3110/ufc-dataset-1994-2026, ufc_gold_dataset_final.csv  (MIT)
  NOT used  leandroiber/ufc-stats-complete-dataset, clean_ufc_dataset.csv   (CC0)

leandroiber is excluded because it attributes strikes to the wrong fighter in about a
third of fights. Matched on ufcstats fight URL the two copies carry identical number
pairs in all 8,551 shared fights, but leandroiber lists the fighters in the opposite
order in 3,005 of them without swapping the numbers. Tested on the 1,001 such fights
won by KO/TKO: under jossilva's attribution the winner out-lands the loser 854-130
and has more knockdowns 706-16; under leandroiber's it is exactly reversed.

A jossilva row is matched to a B bout by date (+-1 day) and both fighters' names with
the observatory's corner-pair score (>= 0.5 on the weaker corner, ties left
unmatched); its own Winner column is checked against ours.

winner_share = winner's sig. strikes landed / (winner's + loser's).
Writes data/b_sig_strikes.csv.
"""
import csv
import statistics
import sys
from collections import Counter
from datetime import date, timedelta

from db import DATA, OBS

sys.path.insert(0, str(OBS))
from ingest.wiki_cards import _corner_pair_score, _TOKEN_MATCH_THRESHOLD  # noqa: E402
from observatory.names import name_tokens                                   # noqa: E402

K = DATA / "kaggle"
SOURCES = {
    "jossilva3110": dict(path=K / "jossilva3110__ufc-dataset-1994-2026" / "ufc_gold_dataset_final.csv",
                         date="Event_Date", f1="Fighter_1", f2="Fighter_2",
                         s1="F1_Sig_Landed", s2="F2_Sig_Landed", url="Fight_URL",
                         winner="Winner",
                         td1="F1_TD_Landed", td2="F2_TD_Landed",
                         ct1="F1_Ctrl_Sec", ct2="F2_Ctrl_Sec"),
}


def load(src):
    by_day = {}
    for r in csv.DictReader(open(src["path"], encoding="utf-8", errors="replace")):
        by_day.setdefault(r[src["date"]][:10], []).append(r)
    return by_day


def match(s, by_day, src):
    d = date.fromisoformat(s["fight_date"])
    scored = []
    for k in (-1, 0, 1):
        for r in by_day.get((d + timedelta(days=k)).isoformat(), []):
            direct = _corner_pair_score(s["winner"], s["loser"], r[src["f1"]], r[src["f2"]])
            cross = _corner_pair_score(s["winner"], s["loser"], r[src["f2"]], r[src["f1"]])
            sc, wslot = (direct, 1) if direct >= cross else (cross, 2)
            if sc >= _TOKEN_MATCH_THRESHOLD:
                scored.append((sc, wslot, r))
    scored.sort(key=lambda t: t[0], reverse=True)
    if not scored or (len(scored) > 1 and scored[0][0] == scored[1][0]):
        # Fallback, as in the media-score matcher: ONE fighter's full name, exactly and
        # uniquely on that date. Catches the spelling variants the pair score misses
        # ("Ronaldo Souza" for Jacare, "Aleksei Oleinik" for Oleynik). A fighter fights
        # once a night, so a unique exact hit identifies the bout.
        ours = {1: name_tokens(s["winner"]), 2: name_tokens(s["loser"])}
        one = []
        for k in (-1, 0, 1):
            for r in by_day.get((d + timedelta(days=k)).isoformat(), []):
                for slot, nm in ((1, r[src["f1"]]), (2, r[src["f2"]])):
                    t = name_tokens(nm)
                    if t and t == ours[1]:
                        one.append((slot, r))
                    elif t and t == ours[2]:
                        one.append((2 if slot == 1 else 1, r))
        uniq = {id(r): (slot, r) for slot, r in one}
        if len(uniq) != 1:
            # Last resort: BOTH surnames match, uniquely on the date. Catches a pair of
            # variants in one bout ("Joshua"/"Josh" Culibao and "Seung Woo"/"SeungWoo"
            # Choi). Two bouts sharing both surnames on one night does not happen.
            def last(n):
                t = (n or "").split()
                return t[-1].lower() if t else ""
            wl, ll = last(s["winner"]), last(s["loser"])
            sur = []
            for k in (-1, 0, 1):
                for r in by_day.get((d + timedelta(days=k)).isoformat(), []):
                    f1, f2 = last(r[src["f1"]]), last(r[src["f2"]])
                    if {f1, f2} == {wl, ll} and wl != ll:
                        sur.append((1 if f1 == wl else 2, r))
            if len(sur) != 1:
                return None
            wslot, r = sur[0]
        else:
            wslot, r = next(iter(uniq.values()))
        scored = [(1.0, wslot, r)]
    _, wslot, r = scored[0]
    lslot = 2 if wslot == 1 else 1
    try:
        w, l = float(r[src[f"s{wslot}"]]), float(r[src[f"s{lslot}"]])
    except ValueError:
        return None
    winner_ok = (src["winner"] is None
                 or _corner_pair_score(r[src["winner"]], "x", s["winner"], "x") >= 0.5
                 or r[src["winner"]] == r[src[f"f{wslot}"]])
    def num(key):
        try:
            return float(r[src[key]])
        except (KeyError, TypeError, ValueError):
            return None
    return {"w": w, "l": l, "url": r[src["url"]], "winner_ok": winner_ok,
            "w_td": num(f"td{wslot}"), "l_td": num(f"td{lslot}"),
            "w_ctrl": num(f"ct{wslot}"), "l_ctrl": num(f"ct{lslot}")}


def main():
    sample = list(csv.DictReader(open(DATA / "b_sample.csv")))
    data = {name: load(src) for name, src in SOURCES.items()}
    out, agree, disagree = [], 0, []
    for s in sample:
        a = match(s, data["jossilva3110"], SOURCES["jossilva3110"])
        use, src = (a, "jossilva3110") if a else (None, "")
        rec = {"bout_id": s["bout_id"], "fight_date": s["fight_date"],
               "winner": s["winner"], "loser": s["loser"], "source": src,
               "winner_sig_landed": "", "loser_sig_landed": "", "winner_share": "",
               "winner_td": "", "loser_td": "", "winner_ctrl_sec": "", "loser_ctrl_sec": "",
               "ufcstats_fight_url": "", "winner_label_agrees": ""}
        if use:
            tot = use["w"] + use["l"]
            rec.update(winner_sig_landed=int(use["w"]), loser_sig_landed=int(use["l"]),
                       winner_share=round(use["w"] / tot, 4) if tot else "",
                       ufcstats_fight_url=use["url"], winner_label_agrees=use["winner_ok"],
                       winner_td=use["w_td"], loser_td=use["l_td"],
                       winner_ctrl_sec=use["w_ctrl"], loser_ctrl_sec=use["l_ctrl"])
        out.append(rec)

    with open(DATA / "b_sig_strikes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

    got = [o for o in out if o["winner_share"] != ""]
    shares = [o["winner_share"] for o in got]
    print(f"sample B {len(out)}: strikes found for {len(got)} "
          f"({100 * len(got) / len(out):.1f}%)  by source {dict(Counter(o['source'] for o in got))}")
    print(f"  winner label disagrees with ours: "
          f"{sum(o['winner_label_agrees'] is False for o in got)}")
    print(f"  winner share: mean {statistics.mean(shares):.3f}, median "
          f"{statistics.median(shares):.3f}, sd {statistics.stdev(shares):.3f}")
    print(f"  winner out-landed the loser in {sum(x > 0.5 for x in shares)}/{len(shares)} "
          f"({100 * sum(x > 0.5 for x in shares) / len(shares):.1f}%), "
          f"tied {sum(x == 0.5 for x in shares)}, out-landed BY the loser "
          f"{sum(x < 0.5 for x in shares)}")


if __name__ == "__main__":
    main()
