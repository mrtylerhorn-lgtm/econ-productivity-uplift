"""Safe edits for the Claude task.

  python3 tools/update.py set DOTTED.PATH JSON
      Set a field in data/editorial.json, e.g.
        set copy.bottomLine '"text"'
        set calendar '[["2026-11-05","Productivity and Costs, Q3 (BLS)","Output per hour"]]'
  python3 tools/update.py show KEY [N]
      Print the last N observations of a series in data/data.json with their dates.

data/data.json is written only by tools/fetch.py (the GitHub Action). Don't edit it by hand.
"""
import json, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cmd = sys.argv[1]
if cmd == "set":
    fn = os.path.join(ROOT, "data", "editorial.json"); E = json.load(open(fn))
    path, val = sys.argv[2].split("."), json.loads(sys.argv[3]); o = E
    for k in path[:-1]: o = o[int(k)] if isinstance(o, list) else o[k]
    if isinstance(o, list): o[int(path[-1])] = val
    else: o[path[-1]] = val
    json.dump(E, open(fn, "w"), ensure_ascii=False, indent=1)
    print("set", sys.argv[2])
elif cmd == "show":
    s = json.load(open(os.path.join(ROOT, "data", "data.json")))["series"][sys.argv[2]]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6; f, st = s["freq"], s["start"]
    for i in range(max(0, len(s["values"]) - n), len(s["values"])):
        if f == "Q": y, q = st.split("Q"); k = int(y) * 4 + int(q) - 1 + i; lab = f"{k // 4}Q{k % 4 + 1}"
        elif f == "M": y, m = map(int, st.split("-")); k = y * 12 + m - 1 + i; lab = f"{k // 12}-{k % 12 + 1:02d}"
        else: lab = str(int(st) + i)
        print(lab, s["values"][i])
else:
    raise SystemExit(__doc__)
