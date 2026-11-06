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
    return {q0 + i: v for i, v in enumerate(s["values"]) if v is not None}
def mser(k):
    s = S[k]; assert s["freq"] == "M", k; y, m = map(int, s["start"].split("-")); m0 = y * 12 + m - 1
    return {m0 + i: v for i, v in enumerate(s["values"]) if v is not None}
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

# ---------- stages added 2026-11-06: adoption, money, work, who gains ----------
import math as _m
def xser(k): s = S[k]; return list(zip(s["dates"], s["values"]))
def avg_n(p, e, n):
    xs = [p[k] for k in range(e - n + 1, e + 1) if k in p]
    return sum(xs) / len(xs) if xs else None
def mn(s): return s.replace("-", "−")   # typographic minus for readings built here
def pct_rank_above(now, hist): return round(sum(x >= now for x in hist) / len(hist) * 100)
# significance tiers (added 2026-11-06), used by every counted test:
#   chance <= 5%  -> "for"     shown as "Clear signal"
#   5% < chance <= 20% -> "mixed"  shown as "Suggestive"
#   chance > 20%, or moving the wrong way -> "against"  shown as "No signal"
def tier(chance, right_way=True):
    if not right_way or chance is None: return "against"
    return "for" if chance <= 5 else ("mixed" if chance <= 20 else "against")
TIER_WORD = {"for": "clear signal", "mixed": "suggestive", "against": "no signal"}

# Adoption (St. Louis Fed Real-Time Population Survey)
def survey(k):
    obs = xser(k); d, v = obs[-1]; y, mo = int(d[:4]), int(d[5:7])
    prev = [(dd, vv) for dd, vv in obs if (int(dd[:4]) * 12 + int(dd[5:7])) <= (y - 1) * 12 + mo]
    # survey readings bounce, so compare the average of the last two readings with the two a year earlier
    last2 = [x for _, x in obs[-2:]]
    ya = [x for _, x in prev[-2:]] if len(prev) >= 2 else None
    return dict(date=d, now=r1(v), avg2=r1(sum(last2) / len(last2)), yearAgoAvg2=r1(sum(ya) / len(ya)) if ya else None,
                first=r1(obs[0][1]), firstDate=obs[0][0], series=[[dd, r1(vv)] for dd, vv in obs])
adopt = {k: survey(k) for k in ("ai_use_work", "ai_daily_work", "ai_timesave", "ai_use_comp", "ai_use_mgmt", "ai_use_office", "ai_use_transport")}
aw = adopt["ai_use_work"]; adopt_prev = aw["series"][-2][1]
adopt_level = "mainstream" if aw["avg2"] >= 50 else ("spreading" if aw["avg2"] >= 25 else "early")
adopt_status = {"mainstream": "Mainstream", "spreading": "Spreading", "early": "Early"}[adopt_level]

# Money: tech investment (computers and related equipment + software, current $) relative to payroll
ipe_n, sw_n, coe = qser("ipe_nom"), qser("software_nom"), qser("comp_employees")
rq = sorted(set(ipe_n) & set(sw_n) & set(coe)); ratio = {q: (ipe_n[q] + sw_n[q]) / coe[q] * 100 for q in rq}
lr = rq[-1]; pre = [ratio[q] for q in rq if q < qi("2023Q1")]
money = dict(last=qs(lr), ratio=r1(ratio[lr]), yearAgo=r1(ratio[lr - 4]), at2023Q4=r1(ratio[BASE]), maxPre2023=r1(max(pre)), maxPre2023Q=qs(max((q for q in rq if q < qi("2023Q1")), key=lambda q: ratio[q])), since=qs(rq[0]),
             series=[[qs(q), r2(ratio[q])] for q in rq])
money_status = ("Surging" if ratio[lr] > max(pre) and ratio[lr] > ratio[lr - 4] else ("Rising" if ratio[lr] > ratio[lr - 4] else "Flat"))

# Work 1: young graduates' job-finding edge (12-month averages; household survey, Oct 2025 missing)
gy, go, ay = mser("unemp_grads_2024"), mser("unemp_grads_25plus"), mser("unemp_2024")
E = max(gy); MB = 2023 * 12 + 11  # Dec 2023
edge = lambda e: avg_n(gy, e, 12) - avg_n(ay, e, 12)          # young grads minus all 20-24 (negative = grads do better)
ygap = lambda e: avg_n(gy, e, 12) - avg_n(go, e, 12)          # young grads minus older grads
hist_e = [edge(e) for e in range(2001 * 12 + 11, 2019 * 12 + 12)]
ng = E - MB; dedge = lambda e: edge(e) - edge(e - ng)            # change in the edge; positive = graduates' advantage narrowing
hist_de = [dedge(e) for e in range(2001 * 12 + 11 + ng, 2019 * 12 + 12)]
grads_chance = pct_rank_above(dedge(E), hist_de) if dedge(E) > 0 else None
hist_y = [ygap(e) for e in range(2001 * 12 + 11, 2019 * 12 + 12)]
grads = dict(last=ms(E), young=r1(avg_n(gy, E, 12)), allYoung=r1(avg_n(ay, E, 12)), older=r1(avg_n(go, E, 12)),
             edge=r1(edge(E)), edgeYearAgo=r1(edge(E - 12)), edge2023=r1(edge(MB)), edgeMin0219=r1(min(hist_e)), edgeMax0219=r1(max(hist_e)),
             change=r2(dedge(E)), chance=grads_chance, histStart=ms(2001 * 12 + 11 + ng), maxChange=r2(max(hist_de)), months=ng,
             ygap=r1(ygap(E)), ygapMax0219=r1(max(hist_y)), ygapMin0219=r1(min(hist_y)),
             series=[[ms(e), r2(avg_n(gy, e, 12)), r2(avg_n(ay, e, 12)), r2(avg_n(go, e, 12))] for e in range(2000 * 12 + 11, E + 1, 3)])
# each work test compares the change since Dec 2023 with every same-length change ending by Dec 2019
L_grads = tier(grads_chance, dedge(E) > 0)

# Work 2: jobs in AI-exposed services vs all private jobs (same-length windows)
pv, cs, cn, inf_ = mser("emp_private"), mser("emp_compsys"), mser("emp_consulting"), mser("emp_info")
Ej = min(max(pv), max(cs)); nj = Ej - MB
gch = lambda p, a, b: (p[b] / p[a] - 1) * 100
jdiff = lambda e: gch(cs, e - nj, e) - gch(pv, e - nj, e)
hist_j = [jdiff(e) for e in range(min(cs) + nj, 2019 * 12 + 12)]
jobs_chance = round(sum(x <= jdiff(Ej) for x in hist_j) / len(hist_j) * 100) if jdiff(Ej) < 0 else None
jobs = dict(last=ms(Ej), months=nj, compsys=r1(gch(cs, MB, Ej)), private=r1(gch(pv, MB, Ej)), consulting=r1(gch(cn, MB, Ej)),
            info=r1(gch(inf_, MB, Ej)), diff=r1(jdiff(Ej)), diffYearAgo=r1(jdiff(Ej - 12)), minHist=r1(min(hist_j)), medHist=r1(st.median(hist_j)), shareWorse=round(sum(x <= jdiff(Ej) for x in hist_j) / len(hist_j) * 100), chance=jobs_chance, histStart=ms(min(cs) + nj),
            series={k: [[ms(e), r2(p[e] / p[MB] * 100)] for e in range(2019 * 12 + 11, Ej + 1)] for k, p in (("compsys", cs), ("info", inf_), ("consulting", cn), ("private", pv))})
L_jobs = tier(jobs_chance, jdiff(Ej) < 0)

# Work 3: pay structure, managers vs office and administrative support workers (median weekly earnings, 4-quarter averages)
pm, po, pa = qser("pay_mgmt"), qser("pay_office"), qser("pay_all")
Lp = max(pm); npq = Lp - BASE
a4 = lambda p, e: avg_n(p, e, 4)
prat = lambda e: a4(pm, e) / a4(po, e)
pch = lambda e: (prat(e) / prat(e - npq) - 1) * 100
hist_p = [pch(e) for e in range(qi("2000Q4") + npq, qi("2019Q4") + 1)]
pay_chance = pct_rank_above(pch(Lp), hist_p) if pch(Lp) > 0 else None
pay = dict(last=qs(Lp), ratio=r2(prat(Lp)), ratio2023=r2(prat(BASE)), ratio2019=r2(prat(qi("2019Q4"))), change=r1(pch(Lp)), maxHist=r1(max(hist_p)), chance=pay_chance, histStart=qs(qi("2000Q4") + npq),
           mgmtGrowth=r1(((a4(pm, Lp) / a4(pm, BASE)) ** (4 / npq) - 1) * 100), officeGrowth=r1(((a4(po, Lp) / a4(po, BASE)) ** (4 / npq) - 1) * 100),
           allGrowth=r1(((a4(pa, Lp) / a4(pa, BASE)) ** (4 / npq) - 1) * 100),
           series=[[qs(e), r2(prat(e))] for e in range(qi("2000Q4"), Lp + 1) if a4(pm, e) and a4(po, e)])
L_pay = tier(pay_chance, pch(Lp) > 0)
work_leans = {"graduates": L_grads, "exposedJobs": L_jobs, "payStructure": L_pay}
work_tests = {k: v == "for" for k, v in work_leans.items()}
nw = sum(work_tests.values()); nw_s = sum(v == "mixed" for v in work_leans.values())
# stage rule: needs clear signals; suggestive ones are shown but don't move the status
work_status = "Clear shift" if nw == 3 else ("Early signs" if nw == 2 else "Not yet")

# Who gains: labor's share of income in the nonfarm business sector
ls = qser("labor_share"); Ll = max(ls); nl = Ll - BASE
ls_now = cagr(ls, BASE, Ll); ls_tr = cagr(ls, TR_A, TR_B)
gls = [((ls[i] / ls[i - 1]) ** 4 - 1) * 100 for i in range(TR_A + 1, TR_B + 1)]
z_ls = (ls_now - ls_tr) / (st.pstdev(gls) / _m.sqrt(nl)); chance_ls = round(0.5 * _m.erfc(-z_ls / _m.sqrt(2)) * 100)
share = dict(last=qs(Ll), now=r1(ls[Ll]), at2023=r1(ls[BASE]), at2019=r1(ls[qi("2019Q4")]), pace=r2(ls_now), trend=r2(ls_tr), chance=chance_ls,
             recordLow=ls[Ll] <= min(ls.values()), since=S["labor_share"]["start"][:4], prevQ=r1(ls[Ll - 1]),
             series=[[qs(q), r2(ls[q])] for q in sorted(ls)])
L_share = tier(chance_ls, ls_now < ls_tr)
gains_status = {"for": "Shifting to capital", "mixed": "Leaning to capital", "against": "No clear shift"}[L_share]

# Benchmarks for claims people make: the Brynjolfsson-Gordon bet, and the latest quarter in context
o_ = qser("oph"); Lo = max(o_); b19 = qi("2019Q4"); end29 = qi("2029Q4")
bet_pace = cagr(o_, b19, Lo); need = ((1.018 ** 10 * o_[b19] / o_[Lo]) ** (4 / (end29 - Lo)) - 1) * 100
qg = [((o_[i] / o_[i - 1]) ** 4 - 1) * 100 for i in range(qi("2004Q1"), qi("2019Q4") + 1)]
lq_g = ((o_[Lo] / o_[Lo - 1]) ** 4 - 1) * 100
bench = dict(last=qs(Lo), betPace=r2(bet_pace), betNeed=r2(need), latestQ=r1(lq_g), shareQuartersAsFast=round(sum(x >= lq_g for x in qg) / len(qg) * 100),
             avg0719=r2(cagr(o_, qi("2007Q4"), qi("2019Q4"))))

# New firms (context)
bh = mser("biz_apps_hp"); Eb = max(bh)
firms = dict(last=ms(Eb), now=round(avg_n(bh, Eb, 12)), at2023=round(avg_n(bh, MB, 12)), at2019=round(avg_n(bh, 2019 * 12 + 11, 12)))

# ---------- scorecard (fixed rules) ----------
jobs_gap = mn(f"{jobs['diff']:+.1f}")
def lean_pace(x): return tier(x["chance"], x["now"] > x["trend"])
L_nfb, L_nfc = lean_pace(nfb), lean_pace(nfc)
# efficiency noise test: same z-test as output per hour, using the spread of quarterly SF Fed figures in 2004-19
TN = T["noise"]; se_sf = TN["sdQ0419"] / math.sqrt(TN["nSince2023"]); z_sf = (TN["since2023Exact"] - TN["avg0419"]) / se_sf
sf.update(trend=r2(TN["avg0419"]), z=r2(z_sf), chance=round(0.5 * math.erfc(z_sf / math.sqrt(2)) * 100))
L_inc = "caution" if inc["gap"] < -0.5 else "pass"
L_sf = tier(sf["chance"], TN["since2023Exact"] > TN["avg0419"])
L_bls = "context"   # annual, no utilization adjustment and no noise test: shown as a cross-check only
L_work = "caution" if work["now"] - work["twoYearsAgo"] >= 0.5 else "pass"
# industry test: chance = share of 2010-19 stretches with a gap as wide; must also stay positive when any one hands-on industry is dropped
sectors["chance"] = sectors["shareWider"]
L_sec = tier(sectors["shareWider"], gap_now > 0 and loo > 0)

def arrow(now, prev, unit="%", what="Past year"):
    if prev is None: return None
    d = round(now, 1) - round(prev, 1); w = "up" if d > 0.05 else ("down" if d < -0.05 else "little changed")
    return dict(dir="up" if d > 0.05 else ("down" if d < -0.05 else "flat"), text=f"{what}: {now:.1f}{unit}, {w} from {prev:.1f}{unit} a year earlier")

def tier_txt(lean): return {"for": "That is a clear signal (5% or less).", "mixed": "That is suggestive (between 5% and 20%), not yet clear.", "against": "That is within normal noise (above 20%)."}[lean]
def chance_txt(x, lean):
    return f"Given how noisy quarterly data are, chance alone would produce a gap this large about {x['chance']}% of the time. " + tier_txt(lean)
ub = users[0]["name"] if users else "AI users"
P0 = sectors["producers"][0] if sectors["producers"] else None
G_AD, G_MO, G_WK, G_OUT, G_WHO, G_CX = ("Adoption: are people using it?", "Money: are firms investing?", "Work: are jobs and pay shifting?",
                                         "Output: is productivity rising faster?", "Who gains?", "Context")
def mdate(d): y, mo = int(d[:4]), int(d[5:7]); return f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][mo-1]} {y}"
score = [
 dict(id="adopt", group=G_AD, name="Workers using generative AI at work", lean="context", counted=False,
      reading=f"{int(aw['now']+0.5)}%", detail=f"Share of employed adults aged 18–64 who used generative AI for work in the past week, St. Louis Fed survey, {mdate(aw['date'])}" + (f", down from {int(adopt_prev+0.5)}% in the reading before. Survey readings bounce, so the trend below averages two." if adopt_prev - aw['now'] >= 1 else ".") + f" Highest in computer and math jobs ({int(adopt['ai_use_comp']['now']+0.5)}%) and management ({int(adopt['ai_use_mgmt']['now']+0.5)}%); lower in office support ({int(adopt['ai_use_office']['now']+0.5)}%) and transportation ({int(adopt['ai_use_transport']['now']+0.5)}%). Time it saves equals about {adopt['ai_timesave']['now']:.1f}% of all hours worked, by users' own estimates.",
      trend=arrow(aw["avg2"], aw["yearAgoAvg2"], "%", "Average of the last two readings")),
 dict(id="money", group=G_MO, name="Tech investment relative to payroll", lean="context", counted=False,
      reading=f"{money['ratio']:.1f}%", detail=f"Business spending on information-processing equipment (computers, communications gear and instruments) and software, as a share of total employee pay, {qp(money['last'])}. Before 2023 the peak was {money['maxPre2023']:.1f}% ({qp(money['maxPre2023Q'])}). Much of the recent jump is data-center building, and these are dollar figures, so part of the rise is prices.",
      trend=arrow(money["ratio"], money["yearAgo"], "%", "Latest")),
 dict(id="inv", group=G_MO, name="Tech equipment investment (inflation-adjusted)", lean="context", counted=False,
      reading=mn(f"{inv['ipeYoy']:+.0f}%"), detail=f"Real spending on information-processing equipment over the past year to {qp(inv['last'])}. Imports of computers rose {inv['impYoy']:.0f}%, so much of it is built abroad. More machines can lift output per hour without any efficiency gain.",
      trend=arrow(inv["ipeYoy"], inv["ipeYoyPrev"], "%", "Growth over the past year")),
 dict(id="grads", group=G_WK, name="Young graduates' job-finding edge", lean=L_grads, counted=True,
      reading=mn(f"{grads['change']:+.1f} pts"), detail=f"Change since Dec 2023 in how much better college graduates aged 20–24 do than all 20–24-year-olds (unemployment, 12-month averages, to {grads['last']}). Graduates now average {grads['young']:.1f}% against {grads['allYoung']:.1f}%, an edge of {-grads['edge']:.1f} points; it was {-grads['edge2023']:.1f} at the end of 2023, already smaller than in any month of 2002–19. " + (f"Narrowing of {grads['change']:.1f} points over {grads['months']} months: {grads['chance']}% of same-length stretches from {grads['histStart']} to Dec 2019 narrowed as much. " if grads['chance'] is not None else "The edge has not narrowed since then. ") + tier_txt(L_grads) + " The edge also swings with the business cycle.",
      trend=arrow(-grads["edge"], -grads["edgeYearAgo"], " pts", "Graduates' edge")),
 dict(id="jobs", group=G_WK, name="Jobs in computer systems design", lean=L_jobs, counted=True,
      reading=mn(f"{jobs['compsys']:+.1f}%"), detail=mn(f"Change since Dec 2023, to {jobs['last']}, against {jobs['private']:+.1f}% for all private jobs; information jobs {jobs['info']:+.1f}%. ") + (f"The gap with all private jobs ({jobs_gap} points) was as bad in {jobs['chance']}% of same-length stretches from {jobs['histStart']} to Dec 2019, all of them right after the dot-com bust. " if jobs['chance'] is not None else "It has kept pace with all private jobs. ") + tier_txt(L_jobs) + " Tech hiring also slumped in 2023 as interest rates rose, before most firms used AI.",
      trend=arrow(jobs["diff"], jobs["diffYearAgo"], " pts", "Gap vs all private jobs")),
 dict(id="pay", group=G_WK, name="Management, business & financial pay vs office support", lean=L_pay, counted=True,
      reading=mn(f"{pay['change']:+.1f}%"), detail=f"Change since late 2023 in median weekly pay of management, business and financial workers relative to office and administrative support workers, to {qp(pay['last'])}. One theory (Imas, Koh and Legg, 2026) predicts people who coordinate work gain while routine specialists lose; this group mixes managers with accountants and analysts, so it is a rough proxy. " + (f"So far office pay has grown faster ({pay['officeGrowth']:.1f}% a year vs {pay['mgmtGrowth']:.1f}%), the opposite. " if pay["change"] <= 0 else f"{pay['chance']}% of same-length stretches from {pay['histStart']} to 2019 saw a rise as large. ") + tier_txt(L_pay),
      trend=None),
 dict(id="nfb", group=G_OUT, name="Output per hour, nonfarm business", lean=L_nfb, counted=True,
      reading=f"{nfb['now']:.1f}%/yr", detail=f"Since the end of 2023, against {nfb['trend']:.1f}% in 2004–19. {chance_txt(nfb, L_nfb)}",
      trend=arrow(nfb["yoy"], nfb["yoyPrev"], "%", "Growth over the past year")),
 dict(id="nfc", group=G_OUT, name="Output per hour, nonfinancial corporations", lean=L_nfc, counted=False,
      reading=f"{nfc['now']:.1f}%/yr", detail=f"Since the end of 2023, against {nfc['trend']:.1f}% in 2004–19. {chance_txt(nfc, L_nfc)} This measure leaves out the self-employed and the harder-to-measure parts of the economy.",
      trend=arrow(nfc["yoy"], nfc["yoyPrev"], "%", "Growth over the past year")),
 dict(id="inc", group=G_OUT, name="Income-side check", lean=L_inc, counted=False,
      reading=mn(f"{inc['gap']:+.1f} pts"), detail=f"Real income (GDI) minus real output (GDP) growth. GDI has grown {inc['gdi']:.1f}% a year since end-2023, against {inc['gdp']:.1f}% for GDP, through {qp(inc['last'])}. " + ("Income is keeping pace, so output isn't obviously overstated." if L_inc == "pass" else "Income is lagging, so output and productivity may be overstated."),
      trend=None),
 dict(id="sf", group=G_OUT, name="Underlying efficiency (SF Fed)", lean=L_sf, counted=True,
      reading=mn(f"{sf['since2023']:+.1f}%/yr"), detail=f"Since end-2023, after removing more machines, more skills and working harder (average of the SF Fed's quarterly figures), against {sf['trend']:.1f}% a year in 2004–19 and about {T['periods'][1][3]:.1f}% in the 1997–2003 boom. " + (f"Chance alone would produce a gain this large about {sf['chance']}% of the time. " if TN["since2023Exact"] > TN["avg0419"] else "It is below its 2004–19 pace. ") + tier_txt(L_sf),
      trend=None),
 dict(id="bls", group=G_OUT, name="Official TFP (BLS, annual)", lean=L_bls, counted=False,
      reading=f"{bls_tfp['since2023']:.1f}%/yr", detail=f"2023–{bls_tfp['lastYear']}, against {bls_tfp['trend']:.1f}% in 2004–19 and {bls_tfp['boom']:.1f}% in 1997–2003. No adjustment for working harder, so it overstates efficiency in a hot economy.",
      trend=arrow(bls_tfp["lastYearGrowth"], bls_tfp["prevYearGrowth"], "%", f"Growth in {bls_tfp['lastYear']}")),
 dict(id="work", group=G_OUT, name="Working harder (factory hours)", lean=L_work, counted=False,
      reading=f"{work['now']:.1f} hrs", detail=f"Weekly hours of factory production workers, {work['last']}, against {work['twoYearsAgo']:.1f} two years earlier (2018 peak {work['peak2018']:.1f}). A quick gauge of whether a hot economy is making people work harder; the SF Fed's adjustment uses a broader set of hours across industries.",
      trend=arrow(work["now"], work["yearAgo"], " hrs", "Latest")),
 dict(id="sec", group=G_OUT, name="AI users vs hands-on industries", lean=L_sec, counted=True,
      reading=mn(f"{sectors['gap']:+.1f} pts"), detail=mn(f"How much more {ub.lower()} sped up than retail, leisure and construction, each measured against its own 2010–19 pace. {sectors['shareWider']:.0f}% of 2010–19 stretches showed a gap at least as large, and dropping any one hands-on industry leaves {sectors['gapLeaveOneOut']:+.1f} pts. ") + tier_txt(L_sec),
      trend=arrow(sectors["gap"], sectors["gapYearAgo"], " pts", "Gap")),
]
if P0:
    score.append(dict(id="prod", group=G_OUT, name=f"AI producers: {P0['name'].lower()}", lean="context", counted=False,
      reading=mn(f"{P0['speed']:+.1f} pts"), detail=mn(f"Speed-up in output per hour since end-2023 against its own 2010–19 pace, bigger than in any 2010–19 stretch (max {P0['maxWindow1019']:+.1f})." if P0["speed"] > P0["maxWindow1019"] else f"Speed-up in output per hour since end-2023 against its own 2010–19 pace (2010–19 max {P0['maxWindow1019']:+.1f}).") + " This industry includes data centers and software publishers, which build and sell AI, so it shows AI production rather than use.",
      trend=None))
score += [
 dict(id="share", group=G_WHO, name="Workers' share of business income", lean=L_share, counted=True,
      reading=mn(f"{share['pace']:+.1f}%/yr"), detail=mn(f"Change in labor's share of nonfarm business income since the end of 2023, against {share['trend']:+.1f}% a year in 2004–19. ") + (f"It is the lowest on record (the series begins in {share['since']}). " if share["recordLow"] else "") + f"Chance alone would produce a decline this fast about {share['chance']}% of the time. " + tier_txt(L_share) + f" The share is pay per hour divided by output per hour, so a quarter of fast productivity growth pulls it down until pay catches up; it fell from {share['prevQ']:.1f} to {share['now']:.1f} last quarter. If machines substitute for people, more of the gains go to owners of capital.",
      trend=None),
 dict(id="firms", group=G_CX, name="New businesses likely to hire", lean="context", counted=False,
      reading=f"{firms['now']/1000:.0f}k/mo", detail=f"High-propensity business applications, 12-month average to {firms['last']}, against {firms['at2023']/1000:.0f}k at the end of 2023 and {firms['at2019']/1000:.0f}k in 2019. A wave of lean AI-native startups would show up here.",
      trend=None),
 dict(id="rates", group=G_CX, name="Inflation-adjusted interest rates", lean="context", counted=False,
      reading=f"{rates['daily']:.1f}%", detail=f"10-year TIPS yield on {rates['dailyDate']}. Markets tend to push this up when they expect faster growth, but deficits and Fed policy move it too. In the late-1990s boom it was about 3.5–4.5% (Klein's estimate).",
      trend=arrow(rates["monthly"], rates["yearAgo"], "%", f"{rates['month']} average")),
]

# ---------- verdict (stage rules 2026-11-06: every test scored by the same tiers; status needs clear signals) ----------
faster = nfb["now"] > nfb["trend"]
out_leans = {"pace": L_nfb, "efficiency": L_sf, "industries": L_sec}
tests = {k: v == "for" for k, v in out_leans.items()}
n_for = sum(tests.values()); n_sug = sum(v == "mixed" for v in out_leans.values())
if not faster: verdict = "No evidence"
elif n_for == 3 and L_work != "caution": verdict = "Showing up"
elif n_for >= 2: verdict = "Early signs"
else: verdict = "Not yet"
# the same structure under the Oct 30 test definitions, kept for comparison
o_tests = [nfb["chance"] <= 5 and faster, sf["since2023"] >= 1.0, gap_now >= 1.0 and loo >= 1.0 and sectors["shareWider"] == 0]
oct30 = "No evidence" if not faster else ("Showing up" if all(o_tests) and L_work != "caution" else ("Early signs" if sum(o_tests) >= 2 else "Not yet"))
def stage_tone(status_good, leans): return "for" if status_good else ("mixed" if any(v in ("for", "mixed") for v in leans) else "against")
def cs_txt(nc, ns): return f"{nc} clear · {ns} suggestive"
# rules in use before 2026-10-30 (efficiency only), kept for comparison
if not faster and sf["since2023"] <= 0: old = "No evidence"
elif sf["since2023"] >= 1.5 and nfb["now"] >= 2.5 and L_work != "caution": old = "Showing up"
elif sf["since2023"] >= 1.0 and sf["fourQTfp"] >= 1.0: old = "Early signs"
else: old = "Not yet"

derived = dict(nfb=nfb, nfc=nfc, path=dict(n=n, now=r1(path_now), boom=r1(path_90), trend=r1(path_trend)),
               income=inc, sf=sf, decomp=decomp, blsTfp=bls_tfp, work=work, sectors=sectors, invest=inv, rates=rates,
               scorecard=score, tests=tests, testsFor=n_for, testsSuggestive=n_sug, verdict=verdict, verdictOldRules=old, verdictOct30=oct30,
               chances=dict(pace=nfb["chance"], efficiency=sf["chance"], industries=sectors["chance"], graduates=grads["chance"], exposedJobs=jobs["chance"], payStructure=pay["chance"], laborShare=share["chance"]),
               adopt=adopt, money=money, grads=grads, jobs=jobs, pay=pay, share=share, bench=bench, firms=firms,
               workTests=work_tests, workFor=nw, workSuggestive=nw_s, workLeans=work_leans, outLeans=out_leans,
               stages=[dict(key="adopt", name="Adoption", q="Are people using it?", status=adopt_status, tone="context", reading=f"{int(aw['now']+0.5)}% of workers"),
                       dict(key="money", name="Money", q="Are firms investing?", status=money_status, tone="context", reading=f"{money['ratio']:.1f}% of payroll"),
                       dict(key="work", name="Work", q="Are jobs and pay shifting?", status=work_status, tone=stage_tone(nw >= 2, work_leans.values()), reading=cs_txt(nw, nw_s)),
                       dict(key="output", name="Output", q="Is productivity rising faster?", status=verdict, tone=stage_tone(verdict in ("Early signs", "Showing up"), out_leans.values()), reading=cs_txt(n_for, n_sug)),
                       dict(key="gains", name="Who gains", q="Is income shifting to capital?", status=gains_status, tone=L_share, reading=mn(f"labor share {share['pace']:+.1f}%/yr"))])

# ---------- checks ----------
for k, s in S.items():
    assert all(isinstance(x, (int, float)) or (x is None and s.get("allowGaps")) for x in s["values"]), k
    if not s["values"]:
        assert DATA_ONLY, f"series {k} ({s['id']}) has no data; check data/fetch-log.md"
        print(f"WARNING: series {k} ({s['id']}) has no data")
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
    print(f"  TIERS: chance <=5% clear signal, 5-20% suggestive, >20% or wrong direction no signal. Stage statuses count clear signals only.")
    print(f"  verdict: {verdict}  (output tests: {n_for} clear, {n_sug} suggestive; {dict((k, TIER_WORD[v]) for k, v in out_leans.items())}); under Oct 30 test definitions: {oct30}; under pre-Oct-30 rules: {old}")
    print(f"  nonfarm business: {nfb['now']}%/yr since 2023Q4 to {nfb['last']} vs trend {nfb['trend']}; z {nfb['z']}, chance {nfb['chance']}% -> {TIER_WORD[L_nfb]}; yoy {nfb['yoy']}; {nfb['shareFaster']}% of overlapping 2004-19 windows as fast; 1997-2003 min {nfb['min9703']}; since 2019Q4 {nfb['since2019']}")
    print(f"  nonfinancial corps: {nfc['now']}%/yr vs {nfc['trend']}; z {nfc['z']}, chance {nfc['chance']}%; yoy {nfc['yoy']}; {nfc['shareFaster']}% of windows as fast")
    print(f"  1990s path at +{n}q: now {path_now:.1f}, boom {path_90:.1f}, trend {path_trend:.1f}")
    print(f"  income check through {inc['last']}: GDI {inc['gdi']} vs GDP {inc['gdp']}")
    print(f"  SF Fed util-adj since 2023: {sf['since2023']} (exact {TN['since2023Exact']}) vs 2004-19 avg {sf['trend']}; z {sf['z']}, chance {sf['chance']}% -> {TIER_WORD[L_sf]}; four-quarter TFP {sf['fourQTfp']}, util-adj {sf['fourQUtilAdj']}")
    print(f"  BLS TFP {2023}-{bls_tfp['lastYear']}: {bls_tfp['since2023']} vs 2004-19 {bls_tfp['trend']}, 1997-2003 {bls_tfp['boom']}")
    print(f"  workweek {work['last']}: {work['now']} (year ago {work['yearAgo']}, two years ago {work['twoYearsAgo']}, 2018 peak {work['peak2018']})")
    print(f"  industries through {sectors['last']}: users-vs-hands-on speed-up gap {sectors['gap']} (year ago {sectors['gapYearAgo']}; leave-one-out min {sectors['gapLeaveOneOut']}; {sectors['shareWider']}% of 2010-19 windows as wide, max {sectors['gapMax1019']}) -> {TIER_WORD[L_sec]}; producers {sectors['producers']}")
    for x in sectors["rows"]: print(f"     [{x['group']}] {x['name']}: {x['now']} vs 2010-19 {x['trend']} (speed-up {x['diff']}); output {x['va']}, hours {x['hrs']}")
    print(f"  investment {inv['last']}: real IPE yoy {inv['ipeYoy']}% (2y {inv['ipe2y']}%), software {inv['swYoy']}%, computer imports {inv['impYoy']}% (2y {inv['imp2y']}%), contrib to GDP growth {inv['contrib4q']}pp avg 4q")
    print(f"  STAGES: " + " | ".join(f"{s['name']}: {s['status']} ({s['reading']})" for s in derived["stages"]))
    print(f"  adoption {aw['date']}: {aw['now']}% of employed adults use genAI for work (avg of last 2 {aw['avg2']}, a year earlier {aw['yearAgoAvg2']}; first {aw['first']} in {aw['firstDate']}); previous reading {adopt_prev}; daily use {adopt['ai_daily_work']['now']}%; time saved {adopt['ai_timesave']['now']}% of work hours; computer/math {adopt['ai_use_comp']['now']}, management {adopt['ai_use_mgmt']['now']}, office {adopt['ai_use_office']['now']}, transport {adopt['ai_use_transport']['now']}")
    print(f"  money {money['last']}: tech investment (info-processing equipment + software, current $) {money['ratio']}% of payroll (year ago {money['yearAgo']}, end-2023 {money['at2023Q4']}, max before 2023 {money['maxPre2023']} in {money['maxPre2023Q']}; data from {money['since']})")
    print(f"  WORK ({nw} clear, {nw_s} suggestive; {dict((k, TIER_WORD[v]) for k, v in work_leans.items())}):")
    print(f"     young grads through {grads['last']}: grads 20-24 {grads['young']}% vs all 20-24 {grads['allYoung']}% (edge {grads['edge']}, year ago {grads['edgeYearAgo']}, end-2023 {grads['edge2023']}; 2002-19 range {grads['edgeMin0219']} to {grads['edgeMax0219']}); older grads {grads['older']}%, young-minus-older {grads['ygap']} (2002-19 range {grads['ygapMin0219']} to {grads['ygapMax0219']}); TEST: edge change since Dec 2023 {grads['change']} pts (positive = narrowing), chance {grads['chance']}% of windows {grads['histStart']}-Dec 2019 narrowing as much (max {grads['maxChange']}) -> {TIER_WORD[L_grads]}")
    print(f"     jobs Dec 2023 to {jobs['last']}: computer systems design {jobs['compsys']}%, private {jobs['private']}%, information {jobs['info']}%, consulting {jobs['consulting']}%; gap {jobs['diff']} (year ago {jobs['diffYearAgo']}; 2002-19 worst {jobs['minHist']} (dot-com bust), median {jobs['medHist']}, {jobs['shareWorse']}% of windows {jobs['histStart']}-Dec 2019 as bad) -> {TIER_WORD[L_jobs]}")
    print(f"     pay to {pay['last']}: managers/office ratio {pay['ratio']} (end-2023 {pay['ratio2023']}, 2019 {pay['ratio2019']}); change {pay['change']}% (max in windows {pay['histStart']}-2019Q4 {pay['maxHist']}; chance {pay['chance']}); growth since end-2023 managers {pay['mgmtGrowth']}%/yr, office {pay['officeGrowth']}%/yr, all {pay['allGrowth']}%/yr -> {TIER_WORD[L_pay]}  [pay series = management, business and financial operations vs office and administrative support]")
    print(f"  who gains {share['last']}: labor share index {share['now']} (end-2023 {share['at2023']}, 2019 {share['at2019']}); {share['pace']}%/yr since end-2023 vs 2004-19 {share['trend']}; chance {share['chance']}% -> {TIER_WORD[L_share]}; previous quarter {share['prevQ']}; lowest on record (series begins {share['since']}): {share['recordLow']} -> {gains_status}")
    print(f"  benchmarks {bench['last']}: latest quarter {bench['latestQ']}% annualized ({bench['shareQuartersAsFast']}% of 2004-19 quarters as fast); 2007-19 avg {bench['avg0719']}; Brynjolfsson-Gordon bet pace since 2019Q4 {bench['betPace']}% vs 1.8 needed; rest of decade needs {bench['betNeed']}%/yr")
    print(f"  new businesses (high-propensity applications, 12m avg) {firms['last']}: {firms['now']} (end-2023 {firms['at2023']}, 2019 {firms['at2019']})")
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
               industryGap=sectors["gap"], workweek=work["now"], ipeRealYoy=inv["ipeYoy"], tips=rates["daily"],
               verdictOct30=oct30, testsSuggestive=n_sug, efficiencyChance=sf["chance"], industryChance=sectors["chance"],
               adoption=adopt_status, money=money_status, work=work_status, gains=gains_status,
               gradsChance=grads["chance"], jobsChance=jobs["chance"], payChance=pay["chance"], laborShareChance=share["chance"])
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
