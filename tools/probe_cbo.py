"""One-off: find CBO's January 2020 potential GDP data and print nonfarm business productivity rows."""
import re, io, urllib.request, openpyxl
UA = {"User-Agent": "Mozilla/5.0 (econ-productivity-uplift data probe)"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90) as r: return r.read()
out = []
pages = ["https://www.cbo.gov/data/budget-economic-data", "https://www.cbo.gov/about/products/budget-economic-data"]
links = set()
for p in pages:
    try:
        h = get(p).decode("utf-8", "replace")
        for href in re.findall(r'href="([^"]+\.xlsx)"', h): links.add(href if href.startswith("http") else "https://www.cbo.gov" + href)
    except Exception as e: out.append(f"page {p}: {e}")
cand = sorted(l for l in links if "2020-01" in l)
out.append("xlsx links with 2020-01:\n" + "\n".join(cand))
for l in cand:
    try:
        wb = openpyxl.load_workbook(io.BytesIO(get(l)), read_only=True, data_only=True)
        out.append(f"\n## {l}\nsheets: {wb.sheetnames}")
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            for i, r in enumerate(rows):
                txt = " ".join(str(c) for c in r if c is not None)
                if re.search(r"productivity", txt, re.I) or (i < 12 and ws.title.lower().startswith(("annual", "quarterly"))):
                    out.append(f"[{ws.title} r{i}] " + " | ".join("" if c is None else (f"{c:.3f}" if isinstance(c, float) else str(c))[:18] for c in r[:40]))
    except Exception as e: out.append(f"{l}: {e}")
open("probe/cbo.md", "w").write("\n".join(out) + "\n"); print("\n".join(out)[:20000])
