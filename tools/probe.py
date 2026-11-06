"""One-off: check candidate FRED series and run FRED searches. Writes probe/result.md."""
import csv, io, re, urllib.request, urllib.parse, html
UA = {"User-Agent": "econ-productivity-uplift/1.0 (+https://github.com/mrtylerhorn-lgtm/econ-productivity-uplift)"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r: return r.read().decode("utf-8", "replace")
IDS = open("probe/ids.txt").read().split()
QUERIES = [l.strip() for l in open("probe/queries.txt") if l.strip()]
out = ["# Probe results", "", "| id | title | first | last | last value | n |", "|---|---|---|---|---|---|"]
for fid in IDS:
    try:
        rows = [r for r in csv.reader(io.StringIO(get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fid}")))][1:]
        rows = [r for r in rows if r and r[1] not in (".", "")]
        page = get(f"https://fred.stlouisfed.org/series/{fid}")
        m = re.search(r"<title>(.*?)</title>", page, re.S); t = html.unescape(m.group(1)).split("|")[0].strip() if m else "?"
        out.append(f"| {fid} | {t} | {rows[0][0]} | {rows[-1][0]} | {rows[-1][1]} | {len(rows)} |")
    except Exception as e:
        out.append(f"| {fid} | ERROR {e} | | | | |")
for q in QUERIES:
    out += ["", f"## search: {q}"]
    try:
        page = get("https://fred.stlouisfed.org/searchresults/?st=" + urllib.parse.quote(q))
        hits = re.findall(r'href="/series/([A-Z0-9]+)"[^>]*>(?:\s*<[^>]+>)*\s*([^<]{8,200})<', page)
        seen = set()
        for sid, title in hits:
            if sid in seen: continue
            seen.add(sid); out.append(f"- {sid}: {html.unescape(title.strip())}")
            if len(seen) >= 25: break
        if not seen: out.append("- (no hits parsed)")
    except Exception as e:
        out.append(f"- ERROR {e}")
open("probe/result.md", "w").write("\n".join(out) + "\n")
print("\n".join(out))
