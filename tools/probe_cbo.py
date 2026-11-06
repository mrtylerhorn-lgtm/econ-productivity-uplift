"""One-off: look for CBO's January 2020 nonfarm business potential productivity projections in CBO's public GitHub repos."""
import subprocess, os, re, glob, json, urllib.request
out = []
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=600)
for repo in ["US-CBO/eval-projections", "US-CBO/eco-proj", "US-CBO/budget-and-economic-data"]:
    r = sh(f"git clone -q --depth 1 https://github.com/{repo} /tmp/{repo.split('/')[1]}")
    out.append(f"## {repo}: rc={r.returncode} {r.stderr.strip()[:200]}")
    d = f"/tmp/{repo.split('/')[1]}"
    if os.path.isdir(d):
        files = [f for f in glob.glob(d + "/**/*", recursive=True) if os.path.isfile(f) and "/.git/" not in f]
        out.append(f"{len(files)} files; sample: " + ", ".join(os.path.relpath(f, d) for f in files[:40]))
        hits = sh(f"grep -ril 'productivity' {d} --include=*.csv --include=*.md --include=*.txt | head -20").stdout
        out.append("files mentioning productivity:\n" + hits)
        for f in hits.split()[:6]:
            g = sh(f"grep -i 'productivity' '{f}' | head -8").stdout
            out.append(f"--- {os.path.relpath(f, d)}\n{g[:1500]}")
try:
    req = urllib.request.Request("https://api.github.com/orgs/US-CBO/repos?per_page=100", headers={"User-Agent": "probe"})
    repos = json.load(urllib.request.urlopen(req, timeout=60))
    out.append("US-CBO repos: " + ", ".join(r["name"] for r in repos))
except Exception as e: out.append(f"repo list: {e}")
open("probe/cbo.md", "w").write("\n".join(out) + "\n"); print("\n".join(out)[:20000])
