"""G, redirect merging (step 1): every redirect (main namespace) pointing at each article
used in the placebo, via en.wikipedia.org/w/api.php prop=redirects, 50 titles per request,
1 req/s. That endpoint is robots-disallowed for generic crawlers; its use for this study
was authorised in chat (2026-09-20) and is logged in STATUS.md / SOURCES.md.
Writes data/g_redirects.csv: article, redirect."""
import csv, json, time, urllib.parse, urllib.request
from db import DATA
UA = "FirstLightObservatory/1.0 (baptperr18@gmail.com) SSAC27 research query"
titles = sorted({r["en_title"] for r in csv.DictReader(open(DATA / "g_prefight_views.csv"))})
out = []
for i in range(0, len(titles), 50):
    batch = titles[i:i + 50]
    cont = {}
    while True:
        q = {"action": "query", "format": "json", "formatversion": "2", "prop": "redirects",
             "titles": "|".join(batch), "rdlimit": "max", "rdnamespace": "0",
             "rdprop": "title", "maxlag": "5", **cont}
        req = urllib.request.Request("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(q),
                                     headers={"User-Agent": UA})
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        norm = {n["to"]: n["from"] for n in d.get("query", {}).get("normalized", [])}
        for p in d.get("query", {}).get("pages", []):
            art = norm.get(p["title"], p["title"])
            for r in p.get("redirects", []):
                out.append({"article": art, "redirect": r["title"]})
        time.sleep(1.0)
        if "continue" not in d:
            break
        cont = d["continue"]
with open(DATA / "g_redirects.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["article", "redirect"]); w.writeheader(); w.writerows(out)
from collections import Counter
c = Counter(o["article"] for o in out)
print(f"{len(titles)} articles, {len(out)} redirects; articles with any: {len(c)}; "
      f"median per article {sorted(c.values())[len(c)//2] if c else 0}, max {max(c.values()) if c else 0}")
