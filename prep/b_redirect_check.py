"""Does each sample-B fighter's article START as a redirect? If so its first-revision
date overstates how long a real article existed. Same authorised action-API endpoint
as the creation dates; 1 request/second."""
import csv, json, time, urllib.parse, urllib.request
from db import DATA
UA = "FirstLightObservatory/1.0 (baptperr18@gmail.com) SSAC27 research query"
s = list(csv.DictReader(open(DATA / "b_candidates.csv")))
titles = sorted({r["winner_title"] for r in s} | {r["loser_title"] for r in s})
out = []
for t in titles:
    q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": "2",
        "prop": "revisions", "titles": t, "rvdir": "newer", "rvlimit": "1",
        "rvprop": "timestamp|size|content", "rvslots": "main", "redirects": "1", "maxlag": "5"})
    with urllib.request.urlopen(urllib.request.Request(f"https://en.wikipedia.org/w/api.php?{q}",
                                headers={"User-Agent": UA}), timeout=30) as r:
        d = json.loads(r.read().decode())
    rev = d["query"]["pages"][0]["revisions"][0]
    txt = rev["slots"]["main"].get("content", "")
    out.append({"en_title": t, "first_rev": rev["timestamp"], "first_size": rev["size"],
                "starts_as_redirect": txt.lstrip().upper().startswith("#REDIRECT")})
    time.sleep(1.0)
with open(DATA / "b_first_revision.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(f"{len(out)} articles; start as redirect: {sum(o['starts_as_redirect'] for o in out)}")
