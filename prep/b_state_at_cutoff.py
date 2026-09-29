"""The rigorous version of B's article-age rule: for each fighter in each sample bout,
was the page a REAL ARTICLE (not a redirect, not yet uncreated) at fight - 60 days?
Reads the latest revision at or before that instant (rvdir=older from rvstart).
Same authorised action-API endpoint; 1 request/second. Writes data/b_state_at_cutoff.csv."""
import csv, json, time, urllib.parse, urllib.request
from datetime import date, timedelta
from db import DATA
UA = "FirstLightObservatory/1.0 (baptperr18@gmail.com) SSAC27 research query"
s = list(csv.DictReader(open(DATA / "b_candidates.csv")))
out = []
for r in s:
    cutoff = date.fromisoformat(r["fight_date"]) - timedelta(days=60)
    for side in ("winner", "loser"):
        q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": "2",
            "prop": "revisions", "titles": r[f"{side}_title"], "rvdir": "older", "rvlimit": "1",
            "rvstart": f"{cutoff.isoformat()}T23:59:59Z", "rvprop": "timestamp|content",
            "rvslots": "main", "redirects": "1", "maxlag": "5"})
        with urllib.request.urlopen(urllib.request.Request(
                f"https://en.wikipedia.org/w/api.php?{q}", headers={"User-Agent": UA}), timeout=30) as resp:
            d = json.loads(resp.read().decode())
        revs = d["query"]["pages"][0].get("revisions") or []
        if not revs:
            state = "no revision yet"
        else:
            txt = revs[0]["slots"]["main"].get("content", "")
            state = "redirect" if txt.lstrip().upper().startswith("#REDIRECT") else "article"
        out.append({"bout_id": r["bout_id"], "side": side, "fighter_id": r[f"{side}_id"],
                    "title": r[f"{side}_title"], "cutoff": cutoff,
                    "rev_at_cutoff": revs[0]["timestamp"] if revs else "", "state": state})
        time.sleep(1.0)
with open(DATA / "b_state_at_cutoff.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
from collections import Counter
print(Counter(o["state"] for o in out))
bad = {o["bout_id"] for o in out if o["state"] != "article"}
print(f"bouts failing (a fighter not a real article at cutoff): {len(bad)} -> B = {len(s) - len(bad)}")
final = [r for r in s if r["bout_id"] not in bad]
with open(DATA / "b_sample.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(final[0])); w.writeheader(); w.writerows(final)
print(f"wrote data/b_sample.csv: {len(final)} bouts")
