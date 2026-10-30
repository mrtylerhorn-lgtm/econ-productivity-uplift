"""Econ Productivity Uplift build.

  python3 tools/build.py              full build: checks the narrative, writes site/index.html
  python3 tools/build.py --data-only  used by the GitHub Action: computes everything, writes
                                      data/facts.txt and data/facts.json, appends data/history.csv,
                                      and skips the narrative checks and the page

Reads data/data.json (written by tools/fetch.py), data/editorial.json (narrative and
calendar, written by the Claude task) and site/template.html. Every derived number, the
scorecard and the verdict are computed here from the data with fixed rules.
"""
import json, sys, os, csv, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ONLY = "--data-only" in sys.argv
D = json.load(open(os.path.join(ROOT, "data", "data.json")))
ED = json.load(open(os.path.join(ROOT, "data", "editorial.json")))
D["copy"], D["calendar"] = ED["copy"], ED["calendar"]
S = D["series"]

# ---------- helpers ----------
def qi(s):  # "2023Q4" -> int
    y, q = s.split("Q"); return int(y) * 4 + int(q) - 1
def qs(i): return f"{i // 4}Q{i % 4 + 1}"
def qp(s): y, q = s.split("Q"); return f"Q{q} {y}"
def qser(k):
    s = S[k]; assert s["freq"] == "Q", k; q0 = qi(s["start"])
    return {q0 + i: v for i, v in enumerate(s["values"])}
def mser(k):
    s = S[k]; assert s["freq"] == "M", k; y, m = map(int, s["start"].split("-")); m0 = y * 12 + m - 1
    return {m0 + i: v for i, v in enumerate(s["values"])}
def ms(i): return f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][i % 12]} {i // 12}"
def m2q(m):
    out = {}
    for k, v in m.items(): out.setdefault((k // 12) * 4 + (k % 12) // 3, []).append(v)
    return {q: sum(a) / len(a) for q, a in out.items() if len(a) == 3}
def cagr(p, a, b): return ((p[b] / p[a]) ** (4 / (b - a)) - 1) * 100
def yoy(p, b): return (p[b] / p[b - 4] - 1) * 100
def r1(x): return None if x is None else round(x, 1)
def r2(x): return None if x is None else round(x, 2)

BASE = qi("2023Q4")                 # start of the current stretch (Klein's)
TR_A, TR_B = qi("2003Q4"), qi("2019Q4")   # 2004-19 trend window
B90_A, B90_B = qi("1996Q4"), qi("2003Q4") # 1997-2003 boom

def windows(p, n, a, b):
    return [cagr(p, s, s + n) for s in range(a, b - n + 1)]

# ---------- headline productivity, two measures ----------
import math
def pace_block(key):
    p = qser(key); last = max(p); n = last - BASE
    now = cagr(p, BASE, last); trend = cagr(p, TR_A, TR_B)
    w = windows(p, n, TR_A, TR_B); w90 = windows(p, n, B90_A, B90_B)
    # noise test: quarterly annualized growth in 2004-19 sets the standard error of an n-quarter average
    g = [((p[i] / p[i - 1]) ** 4 - 1) * 100 for i in range(TR_A + 1, TR_B + 1)]
    se = st.pstdev(g) / math.sqrt(n); z = (now - trend) / se
    pval = 0.5 * math.erfc(z / math.sqrt(2)) * 100   # one-sided chance of a gap this big from noise alone
    return dict(last=qs(last), n=n, now=r2(now), trend=r2(trend), yoy=r2(yoy(p, last)), yoyPrev=r2(yoy(p, last - 4)),
                since2019=r2(cagr(p, qi("2019Q4"), last)), since2022=r2(cagr(p, qi("2022Q4"), last)),
                last4=r2(cagr(p, last - 4, last)), z=r2(z), chance=round(pval), se=r2(se),
                shareFaster=round(sum(x >= now for x in w) / len(w) * 100, 1),
                w0419=[r2(x) for x in w], w9703=[r2(x) for x in w90], min9703=r2(min(w90)) if w90 else None)

nfb = pace_block("oph")
nfc = pace_block("ophnfc")
# 1990s path comparison at the same horizon
p = qser("oph"); last = max(p); n = last - BASE
path_now = p[last] / p[BASE] * 100; path_90 = p[B90_A + n] / p[B90_A] * 100
path_trend = 100 * (1 + nfb["trend"] / 100) ** (n / 4)

# ---------- income-side check ----------
gdp, gdi = qser("gdpc1"), qser("gdi_real"); lc = min(max(gdp), max(gdi))
inc = dict(last=qs(lc), gdp=r2(cagr(gdp, BASE, lc)), gdi=r2(cagr(gdi, BASE, lc)))
inc["gap"] = r2(inc["gdi"] - inc["gdp"])

# ---------- efficiency ----------
T = D["tfp"]
sf = dict(since2023=T["sinceEnd2023"]["utilAdj"], fourQTfp=T["fourQ"]["tfp"], fourQUtilAdj=T["fourQ"]["utilAdj"],
          lastQ=T["quarters"][-1][0])
decomp = [dict(q=r[0], lp=r[1], tfp=r[2], util=r[3], utilAdj=r[4], inputs=r2(r[1] - r[2])) for r in T["quarters"]]
ba = S["tfp_bls_annual"]; y0 = int(ba["start"]); bv = ba["values"]; ly = y0 + len(bv) - 1
def ga(a, b): return ((bv[b - y0] / bv[a - y0]) ** (1 / (b - a)) - 1) * 100
bls_tfp = dict(lastYear=ly, since2023=r2(ga(2023, ly)), trend=r2(ga(2003, 2019)), boom=r2(ga(1996, 2003)),
               lastYearGrowth=r2(ga(ly - 1, ly)), prevYearGrowth=r2(ga(ly - 2, ly - 1)))

# ---------- working harder ----------
ww = mser("awhman"); lw = max(ww)
work = dict(last=ms(lw), now=ww[lw], yearAgo=ww[lw - 12], twoYearsAgo=ww[lw - 24],
            peak2018=max(v for k, v in ww.items() if k // 12 == 2018))

# ---------- sectors ----------
# groups: "users" (AI-using proxy, counted), "producers" (sells computing, shown not counted),
#         "handson" (counted comparison), "other" (shown only)
SECT = D["sectors"]; T0, T1 = qi("2009Q4"), qi("2019Q4")
sect = []
for s in SECT:
    va = qser("va_" + s["key"]); hr = m2q(mser("hrs_" + s["key"]))
    pp = {q: va[q] / hr[q] for q in va if q in hr}; lq_ = max(pp)
    now = cagr(pp, BASE, lq_); tr = cagr(pp, T0, T1)
    sect.append(dict(key=s["key"], name=s["name"], group=s["group"], last=qs(lq_), now=r2(now), trend=r2(tr),
                     diff=r2(now - tr), va=r2(cagr(va, BASE, lq_)), hrs=r2(cagr(hr, BASE, lq_)), _pp=pp, _tr=tr))
lq = min(qi(x["last"]) for x in sect); ns = lq - BASE
def speed(x, e): return cagr(x["_pp"], e - ns, e) - x["_tr"]   # speed-up vs own 2010-19 trend
users = [x for x in sect if x["group"] == "users"]; hands = [x for x in sect if x["group"] == "handson"]
def gap_at(e, hs=None):
    hs = hs or hands
    return st.mean(speed(x, e) for x in users) - st.mean(speed(x, e) for x in hs)
gap_now = gap_at(lq); gap_prev = gap_at(lq - 4)
loo = min(gap_at(lq, [h for h in hands if h is not d]) for d in hands)   # drop any one hands-on industry
gw = [gap_at(e) for e in range(T0 + ns, T1 + 1)]
prod = [x for x in sect if x["group"] == "producers"]
prod_hist = {x["key"]: max(speed(x, e) for e in range(T0 + ns, T1 + 1)) for x in prod}
sectors = dict(last=qs(lq), gap=r2(gap_now), gapYearAgo=r2(gap_prev), gapLeaveOneOut=r2(loo),
               gapMax1019=r2(max(gw)), gapMedian1019=r2(st.median(gw)),
               shareWider=int(sum(x >= gap_now for x in gw) / len(gw) * 100 + 0.5),
               producers=[dict(key=x["key"], name=x["name"], speed=r2(x["now"] - x["_tr"]), maxWindow1019=r2(prod_hist[x["key"]])) for x in prod],
               rows=[{k: v for k, v in x.items() if not k.startswith("_")} for x in sect])

# ---------- investment ----------
ir, sr, im = qser("ipe_real"), qser("software_real"), qser("imports_computers")
li = max(ir); ci, cs = qser("contrib_ipe"), qser("contrib_software")
inv = dict(last=qs(li), ipeYoy=r1(yoy(ir, li)), ipeYoyPrev=r1(yoy(ir, li - 4)), ipe2y=r1((ir[li] / ir[li - 8] - 1) * 100),
           swYoy=r1(yoy(sr, li)), impYoy=r1(yoy(im, li)), imp2y=r1((im[li] / im[li - 8] - 1) * 100),
           contrib4q=r2(st.mean(ci[k] + cs[k] for k in range(li - 3, li + 1))),
           ipeNom=round(S["ipe_nom"]["values"][-1]))

# ---------- rates ----------
fm = mser("fii10"); lf = max(fm)
rates = dict(daily=D["tipsLatestDaily"]["value"], dailyDate=D["tipsLatestDaily"]["date"], monthly=fm[lf],
             month=ms(lf), yearAgo=fm[lf - 12], band=[3.5, 4.5])

# ---------- scorecard (fixed rules) ----------
def lean_pace(x):
    if x["now"] <= x["trend"]: return "against"
    return "for" if x["chance"] <= 5 else "mixed"
L_nfb, L_nfc = lean_pace(nfb), lean_pace(nfc)
L_inc = "against" if inc["gap"] < -0.5 else "pass"
L_sf = "for" if sf["since2023"] >= 1.0 else ("against" if sf["since2023"] <= 0.3 else "mixed")
L_bls = "for" if bls_tfp["since2023"] >= bls_tfp["trend"] + 0.4 else ("against" if bls_tfp["since2023"] <= bls_tfp["trend"] else "mixed")
L_work = "caution" if work["now"] - work["twoYearsAgo"] >= 0.5 else "pass"
L_sec = ("for" if (gap_now >= 1.0 and loo >= 1.0 and sectors["shareWider"] == 0)
         else ("against" if gap_now <= 0 else "mixed"))

def arrow(now, prev, unit="%", what="Past year"):
    if prev is None: return None
    d = round(now, 1) - round(prev, 1); w = "up" if d > 0.05 else ("down" if d < -0.05 else "little changed")
    return dict(dir="up" if d > 0.05 else ("down" if d < -0.05 else "flat"), text=f"{what}: {now:.1f}{unit}, {w} from {prev:.1f}{unit} a year earlier")

def chance_txt(x):
    return (f"Given how noisy quarterly data are, chance alone would produce a gap this large about {x['chance']}% of the time"
            + ("; a reliable signal needs 5% or less." if x["chance"] > 5 else ", which clears the 5% bar for a reliable signal."))
ub = users[0]["name"] if users else "AI users"
P0 = sectors["producers"][0] if sectors["producers"] else None
score = [
 dict(id="nfb", group="Is productivity growing faster?", name="Output per hour, nonfarm business", lean=L_nfb, counted=True,
      reading=f"{nfb['now']:.1f}%/yr", detail=f"Since the end of 2023, against {nfb['trend']:.1f}% in 2004–19. {chance_txt(nfb)}",
      trend=arrow(nfb["yoy"], nfb["yoyPrev"], "%", "Growth over the past year")),
 dict(id="nfc", group="Is productivity growing faster?", name="Output per hour, nonfinancial corporations", lean=L_nfc, counted=False,
      reading=f"{nfc['now']:.1f}%/yr", detail=f"Since the end of 2023, against {nfc['trend']:.1f}% in 2004–19. {chance_txt(nfc)} This measure leaves out the self-employed and the harder-to-measure parts of the economy.",
      trend=arrow(nfc["yoy"], nfc["yoyPrev"], "%", "Growth over the past year")),
 dict(id="inc", group="Is productivity growing faster?", name="Income-side check", lean=L_inc, counted=False,
      reading=f"{inc['gap']:+.1f} pts", detail=f"Real income (GDI) minus real output (GDP) growth. GDI has grown {inc['gdi']:.1f}% a year since end-2023, against {inc['gdp']:.1f}% for GDP, through {qp(inc['last'])}. " + ("Income is keeping pace, so output isn't obviously overstated." if L_inc == "pass" else "Income is lagging, so output and productivity may be overstated."),
      trend=None),
 dict(id="sf", group="Is it efficiency, or more effort and machines?", name="Underlying efficiency (SF Fed)", lean=L_sf, counted=True,
      reading=f"{sf['since2023']:+.1f}%/yr", detail=f"Since end-2023, after removing more machines, more skills and working harder ({'average of the SF Fed' + chr(39) + 's quarterly figures' if T.get('source') == 'file' else 'this page' + chr(39) + 's estimate from SF Fed figures'}). It grew about {T['periods'][1][3]:.1f}% a year in the 1997–2003 boom.",
      trend=None),
 dict(id="bls", group="Is it efficiency, or more effort and machines?", name="Official TFP (BLS, annual)", lean=L_bls, counted=False,
      reading=f"{bls_tfp['since2023']:.1f}%/yr", detail=f"2023–{bls_tfp['lastYear']}, against {bls_tfp['trend']:.1f}% in 2004–19 and {bls_tfp['boom']:.1f}% in 1997–2003. No adjustment for working harder, so it overstates efficiency in a hot economy.",
      trend=arrow(bls_tfp["lastYearGrowth"], bls_tfp["prevYearGrowth"], "%", f"Growth in {bls_tfp['lastYear']}")),
 dict(id="work", group="Is it efficiency, or more effort and machines?", name="Working harder (factory hours)", lean=L_work, counted=False,
      reading=f"{work['now']:.1f} hrs", detail=f"Weekly hours of factory production workers, {work['last']}, against {work['twoYearsAgo']:.1f} two years earlier (2018 peak {work['peak2018']:.1f}). Longer weeks suggest extra effort and machine time are flattering the numbers.",
      trend=arrow(work["now"], work["yearAgo"], " hrs", "Latest")),
 dict(id="sec", group="Is it showing up where AI is used?", name="AI users vs hands-on industries", lean=L_sec, counted=True,
      reading=f"{sectors['gap']:+.1f} pts", detail=f"How much more {ub.lower()} sped up than retail, leisure and construction, each measured against its own 2010–19 pace. {sectors['shareWider']:.0f}% of 2010–19 stretches showed a gap at least as large, and dropping any one hands-on industry leaves {sectors['gapLeaveOneOut']:+.1f} pts. To count, the gap must beat every 2010–19 stretch and stay above 1 point when any one hands-on industry is dropped.",
      trend=arrow(sectors["gap"], sectors["gapYearAgo"], " pts", "Gap")),
]
if P0:
    score.append(dict(id="prod", group="Is it showing up where AI is used?", name=f"AI producers: {P0['name'].lower()}", lean="context", counted=False,
      reading=f"{P0['speed']:+.1f} pts", detail=f"Speed-up in output per hour since end-2023 against its own 2010–19 pace, bigger than in any 2010–19 stretch (max {P0['maxWindow1019']:+.1f})." if P0["speed"] > P0["maxWindow1019"] else f"Speed-up in output per hour since end-2023 against its own 2010–19 pace (2010–19 max {P0['maxWindow1019']:+.1f}).",
      trend=None))
    score[-1]["detail"] += " This industry includes data centers and software publishers, which build and sell AI, so it shows AI production rather than use."
score += [
 dict(id="inv", group="Context", name="Tech equipment investment (inflation-adjusted)", lean="context", counted=False,
      reading=f"{inv['ipeYoy']:+.0f}%", detail=f"Real spending on computers and related equipment over the past year to {qp(inv['last'])}. Imports of computers rose {inv['impYoy']:.0f}%, so much of it is built abroad. More machines can lift output per hour without any efficiency gain.",
      trend=arrow(inv["ipeYoy"], inv["ipeYoyPrev"], "%", "Growth over the past year")),
 dict(id="rates", group="Context", name="Inflation-adjusted interest rates", lean="context", counted=False,
      reading=f"{rates['daily']:.1f}%", detail=f"10-year TIPS yield on {rates['dailyDate']}, against 3.5–4.5% in the late-1990s boom. A genuine boom tends to push it up, but deficits and Fed policy move it too.",
      trend=arrow(rates["monthly"], rates["yearAgo"], "%", f"{rates['month']} average")),
]

# ---------- verdict (fixed rules; frozen 2026-10-30) ----------
faster = nfb["now"] > nfb["trend"]
tests = {"pace": L_nfb == "for", "efficiency": L_sf == "for", "industries": L_sec == "for"}
n_for = sum(tests.values())
if not faster: verdict = "No evidence"
elif n_for == 3 and L_work != "caution": verdict = "Showing up"
elif n_for >= 2: verdict = "Early signs"
else: verdict = "Not yet"
# rules in use before 2026-10-30 (efficiency only), kept for comparison
if not faster and sf["since2023"] <= 0: old = "No evidence"
elif sf["since2023"] >= 1.5 and nfb["now"] >= 2.5 and L_work != "caution": old = "Showing up"
elif sf["since2023"] >= 1.0 and sf["fourQTfp"] >= 1.0: old = "Early signs"
else: old = "Not yet"

derived = dict(nfb=nfb, nfc=nfc, path=dict(n=n, now=r1(path_now), boom=r1(path_90), trend=r1(path_trend)),
               income=inc, sf=sf, decomp=decomp, blsTfp=bls_tfp, work=work, sectors=sectors, invest=inv, rates=rates,
               scorecard=score, tests=tests, testsFor=n_for, verdict=verdict, verdictOldRules=old)

# ---------- checks ----------
for k, s in S.items():
    assert s["values"] and all(isinstance(x, (int, float)) for x in s["values"]), k
for r in T["quarters"]: assert abs(r[2] - r[3] - r[4]) < 0.06, ("util-adj check", r)
C = D["copy"]
if not DATA_ONLY:
    for k in ("bottomLine", "changed"): assert C[k], k
    assert C["verdict"] == verdict, f"copy.verdict is {C['verdict']!r} but the rules give {verdict!r}; rewrite the copy"
    for side in ("caseFor", "caseAgainst"):
        assert 3 <= len(C[side]) <= 5 and all(x["h"] and x["body"] for x in C[side]), side
D["derived"] = derived

import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    print("FACTS (the narrative must agree with these):")
    print(f"  verdict: {verdict}  (tests for AI: {n_for}/3 {tests}); under pre-Oct-30 rules: {old}")
    print(f"  nonfarm business: {nfb['now']}%/yr since 2023Q4 to {nfb['last']} vs trend {nfb['trend']}; z {nfb['z']}, chance {nfb['chance']}%; yoy {nfb['yoy']}; {nfb['shareFaster']}% of overlapping 2004-19 windows as fast; 1997-2003 min {nfb['min9703']}; since 2019Q4 {nfb['since2019']}")
    print(f"  nonfinancial corps: {nfc['now']}%/yr vs {nfc['trend']}; z {nfc['z']}, chance {nfc['chance']}%; yoy {nfc['yoy']}; {nfc['shareFaster']}% of windows as fast")
    print(f"  1990s path at +{n}q: now {path_now:.1f}, boom {path_90:.1f}, trend {path_trend:.1f}")
    print(f"  income check through {inc['last']}: GDI {inc['gdi']} vs GDP {inc['gdp']}")
    print(f"  SF Fed util-adj since 2023: {sf['since2023']}; four-quarter TFP {sf['fourQTfp']}, util-adj {sf['fourQUtilAdj']}")
    print(f"  BLS TFP {2023}-{bls_tfp['lastYear']}: {bls_tfp['since2023']} vs 2004-19 {bls_tfp['trend']}, 1997-2003 {bls_tfp['boom']}")
    print(f"  workweek {work['last']}: {work['now']} (year ago {work['yearAgo']}, two years ago {work['twoYearsAgo']}, 2018 peak {work['peak2018']})")
    print(f"  industries through {sectors['last']}: users-vs-hands-on speed-up gap {sectors['gap']} (year ago {sectors['gapYearAgo']}; leave-one-out min {sectors['gapLeaveOneOut']}; {sectors['shareWider']}% of 2010-19 windows as wide, max {sectors['gapMax1019']}); producers {sectors['producers']}")
    for x in sectors["rows"]: print(f"     [{x['group']}] {x['name']}: {x['now']} vs 2010-19 {x['trend']} (speed-up {x['diff']}); output {x['va']}, hours {x['hrs']}")
    print(f"  investment {inv['last']}: real IPE yoy {inv['ipeYoy']}% (2y {inv['ipe2y']}%), software {inv['swYoy']}%, computer imports {inv['impYoy']}% (2y {inv['imp2y']}%), contrib to GDP growth {inv['contrib4q']}pp avg 4q")
    print(f"  rates: daily {rates['daily']} on {rates['dailyDate']}; {rates['month']} avg {rates['monthly']} (year ago {rates['yearAgo']})")
facts = buf.getvalue()
print(facts, end="")
open(os.path.join(ROOT, "data", "facts.txt"), "w").write(f"data as of {D['asOf']}\n" + facts)
json.dump(derived, open(os.path.join(ROOT, "data", "facts.json"), "w"), ensure_ascii=False, indent=1)

if DATA_ONLY and "--log-history" in sys.argv:
    hp = os.path.join(ROOT, "data", "history.csv"); new = not os.path.exists(hp)
    row = dict(asOf=D["asOf"], verdict=verdict, verdictOldRules=old, testsFor=n_for,
               pace=tests["pace"], efficiency=tests["efficiency"], industries=tests["industries"],
               nfb=nfb["now"], nfbChance=nfb["chance"], nfc=nfc["now"], utilAdjSince2023=sf["since2023"],
               industryGap=sectors["gap"], workweek=work["now"], ipeRealYoy=inv["ipeYoy"], tips=rates["daily"])
    rows = list(csv.DictReader(open(hp))) if not new else []
    rows = [r for r in rows if r["asOf"] != D["asOf"]] + [{k: str(v) for k, v in row.items()}]
    with open(hp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys())); w.writeheader(); w.writerows(rows)

if not DATA_ONLY:
    tpl = open(os.path.join(ROOT, "site", "template.html")).read()
    assert tpl.count("__DATA__") == 1
    html = tpl.replace("__DATA__", json.dumps(D, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
    out = os.path.join(ROOT, "site", "index.html")
    open(out, "w").write(html)
    print("built", out, len(html), "bytes")
