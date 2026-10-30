"""Fetch the latest data into data/data.json. Run by the weekly GitHub Action.

  python3 tools/fetch.py

- Every FRED series in data.json is re-downloaded in full from fredgraph.csv (no API key
  needed), so revisions are picked up automatically. The series start date in data.json is kept.
- The latest daily 10-year TIPS yield (DFII10).
- The SF Fed's quarterly TFP file: quarterly growth accounting, four-quarter averages, and the
  period averages used on the page, all computed from one vintage of the file.
A source that fails or looks wrong is left as it was and the problem is written to
data/fetch-log.md, which the Claude task reads when it writes the commentary.
"""
import csv, io, json, os, re, sys, datetime as dt, urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DP = os.path.join(ROOT, "data", "data.json")
D = json.load(open(DP))
UA = {"User-Agent": "econ-productivity-uplift/1.0 (+https://github.com/mrtylerhorn-lgtm/econ-productivity-uplift)"}
today = dt.datetime.now(ZoneInfo("Asia/Tokyo")).date()
log, problems = [], []

def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), dict(r.headers)

# ---------------- FRED ----------------
def idx_of(freq, start, date):
    y, m, _ = map(int, date.split("-"))
    if freq == "Q":
        y0, q0 = start.split("Q"); assert (m - 1) % 3 == 0; return y * 4 + (m - 1) // 3 - (int(y0) * 4 + int(q0) - 1)
    if freq == "M":
        y0, m0 = map(int, start.split("-")); return y * 12 + m - 1 - (y0 * 12 + m0 - 1)
    if freq == "A": return y - int(start)
    raise ValueError(freq)
def label(freq, start, i):
    if freq == "Q": y0, q0 = start.split("Q"); k = int(y0) * 4 + int(q0) - 1 + i; return f"{k // 4}Q{k % 4 + 1}"
    if freq == "M": y0, m0 = map(int, start.split("-")); k = y0 * 12 + m0 - 1 + i; return f"{k // 12}-{k % 12 + 1:02d}"
    return str(int(start) + i)

def fred_csv(fid, extra=""):
    raw, _ = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fid}{extra}")
    rows = list(csv.reader(io.StringIO(raw.decode())))
    assert rows and len(rows[0]) == 2, f"unexpected CSV header {rows[:1]}"
    return [(d, v) for d, v in rows[1:] if d]

for key, s in D["series"].items():
    try:
        rows = fred_csv(s["id"])
        vals = {}
        for d, v in rows:
            i = idx_of(s["freq"], s["start"], d)
            if i < 0: continue
            if v.strip() in (".", ""): vals[i] = None
            else: vals[i] = float(v)
        n = max(vals) + 1
        while n > 0 and vals.get(n - 1) is None: n -= 1           # drop trailing missing
        new = [vals.get(i) for i in range(n)]
        assert None not in new, f"gap in {s['id']}: missing at {label(s['freq'], s['start'], new.index(None))}"
        old = s["values"]
        assert len(new) >= len(old), f"{s['id']} shrank from {len(old)} to {len(new)} observations"
        revised = [i for i in range(len(old)) if abs(new[i] - old[i]) > 1e-9]
        big = [i for i in revised if abs(new[i] - old[i]) > 0.005 * max(abs(old[i]), 1)]
        added = len(new) - len(old)
        s["values"] = new; s["fetched"] = str(today)
        if added or revised:
            msg = f"- **{key}** ({s['id']}): "
            if added: msg += f"{added} new observation(s), latest {label(s['freq'], s['start'], len(new) - 1)} = {new[-1]}"
            if revised: msg += f"{'; ' if added else ''}{len(revised)} revised value(s)" + (f", {len(big)} by more than 0.5% (earliest {label(s['freq'], s['start'], big[0])})" if big else "")
            log.append(msg)
    except Exception as e:
        problems.append(f"- **{key}** ({s['id']}): not updated: {e}")

try:
    since = (today - dt.timedelta(days=45)).isoformat()
    rows = [(d, v) for d, v in fred_csv("DFII10", f"&cosd={since}") if v not in (".", "")]
    d, v = rows[-1]
    if d != D["tipsLatestDaily"]["date"]:
        log.append(f"- **10-year TIPS (daily)**: {v}% on {d} (was {D['tipsLatestDaily']['value']}% on {D['tipsLatestDaily']['date']})")
    D["tipsLatestDaily"] = {"date": d, "value": float(v)}
except Exception as e:
    problems.append(f"- **DFII10**: not updated: {e}")

# ---------------- SF Fed TFP ----------------
SFPAGE = "https://www.frbsf.org/research-and-insights/data-and-indicators/total-factor-productivity-tfp/"
diag = []
try:
    import openpyxl
    page, _ = get(SFPAGE)
    page = page.decode("utf-8", "replace")
    m = re.search(r'href="([^"]*quarterly_tfp\.xlsx[^"]*)"', page)
    url = m.group(1) if m else "https://www.frbsf.org/wp-content/uploads/quarterly_tfp.xlsx"
    if url.startswith("/"): url = "https://www.frbsf.org" + url
    um = re.search(r"Updated\s*(\d{1,2}/\d{1,2}/\d{4})", page)
    raw, hdr = get(url, timeout=120)
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    for ws in wb.worksheets:
        diag.append(f"## sheet {ws.title}")
        for r_i, row in enumerate(ws.iter_rows(max_row=12, values_only=True)):
            diag.append(" | ".join("" if c is None else str(c)[:24] for c in row[:22]))
    # find the quarterly sheet: a header row with 'date' and 'dtfp_util'
    found = None
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        for h_i, row in enumerate(rows[:40]):
            names = [str(c).strip().lower() if c is not None else "" for c in row]
            if "dtfp_util" in names and "dtfp" in names and "dutil" in names:
                found = (ws.title, h_i, names, rows); break
        if found: break
    assert found, "no sheet with dtfp, dutil and dtfp_util columns"
    title, h_i, names, rows = found
    col = {n: names.index(n) for n in ("dtfp", "dutil", "dtfp_util")}
    lpname = next((n for n in ("dlp", "dlp_bls", "dy_lp", "dlp_y") if n in names), None)
    assert lpname, f"no labor-productivity column among {names}"
    col["dlp"] = names.index(lpname)
    q = []
    for row in rows[h_i + 1:]:
        lab = row[0]
        if lab is None: continue
        m2 = re.match(r"\s*(\d{4})\s*[:Qq]+\s*Q?(\d)", str(lab))
        if not m2: continue
        vals = [row[col[k]] for k in ("dlp", "dtfp", "dutil", "dtfp_util")]
        if any(not isinstance(v, (int, float)) for v in vals): continue
        q.append((int(m2.group(1)) * 4 + int(m2.group(2)) - 1, [float(v) for v in vals]))
    q.sort()
    assert len(q) > 250, f"only {len(q)} quarterly rows parsed"
    Q = dict(q); lastq = q[-1][0]
    ql = lambda i: f"{i // 4}Q{i % 4 + 1}"
    qi = lambda s: int(s[:4]) * 4 + int(s[-1]) - 1
    def avg(col_i, a, b):  # mean over quarters a+1..b (growth from end of quarter a to end of b)
        xs = [Q[i][col_i] for i in range(a + 1, b + 1) if i in Q]; return sum(xs) / len(xs)
    T = D["tfp"]
    T["quarters"] = [[ql(i)] + [round(v, 2) for v in Q[i]] for i in range(lastq - 5, lastq + 1)]
    T["fourQ"] = {"tfp": round(avg(1, lastq - 4, lastq), 2), "utilAdj": round(avg(3, lastq - 4, lastq), 2)}
    since = round(avg(3, qi("2023Q4"), lastq), 1)
    T["sinceEnd2023"] = {"utilAdj": since, "method": f"average of SF Fed quarterly utilization-adjusted TFP growth, 2024Q1–{ql(lastq)}"}
    per = [["1984–96", "1984Q1", "1996Q4"], ["1997–2003", "1996Q4", "2003Q4"], ["2004–19", "2003Q4", "2019Q4"], ["Since end-2023", "2023Q4", "latest"]]
    T["periods"] = [[lab, a, b, round(avg(3, qi(a), lastq if b == "latest" else qi(b)), 1), None] for lab, a, b in per]
    produced = None
    for ws in wb.worksheets:
        for row in ws.iter_rows(max_row=30, values_only=True):
            for c in row:
                mm = re.search(r"Produced on\s+([A-Z][a-z]+ \d{1,2},? \d{4})", str(c or ""))
                if mm: produced = mm.group(1); break
            if produced: break
        if produced: break
    vint = produced or (um.group(1) if um else hdr.get("Last-Modified", "unknown date"))
    T["vintage"] = f"SF Fed quarterly TFP file, updated {vint} (data through {ql(lastq)})"
    T["source"] = "file"
    T["periodsNote"] = (f"Output-per-hour bars are computed from the BLS series. Underlying-efficiency bars are averages of the SF Fed's "
                        f"quarterly utilization-adjusted TFP growth, all from its latest file (data through {ql(lastq)}).")
    T["fourQNote"] = None
    log.append(f"- **SF Fed TFP**: file parsed from sheet '{title}', data through {ql(lastq)}; underlying efficiency since end-2023 {since:+.1f}%/yr; "
               f"period averages {', '.join(f'{p[0]} {p[3]}' for p in T['periods'])}")
except Exception as e:
    problems.append(f"- **SF Fed TFP**: not updated: {e}")
open(os.path.join(ROOT, "data", "sffed-file-structure.txt"), "w").write("\n".join(diag) + "\n")

# ---------------- write ----------------
D["asOf"] = str(today)
json.dump(D, open(DP, "w"), ensure_ascii=False, indent=1)
with open(os.path.join(ROOT, "data", "fetch-log.md"), "w") as f:
    f.write(f"# Fetch log, {today} (Tokyo)\n\n## Changes\n" + ("\n".join(log) if log else "- No new data.") + "\n")
    f.write("\n## Problems\n" + ("\n".join(problems) if problems else "- None.") + "\n")
print(open(os.path.join(ROOT, "data", "fetch-log.md")).read())
