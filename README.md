# Econ Productivity Uplift

A tracker for one question: **is AI showing up in U.S. productivity data?** It follows Matthew C. Klein's framing: separate working smarter (underlying efficiency) from working harder (utilization), and compare today with the 1997–2003 boom.

## How it updates
1. **GitHub Action, every Saturday 06:17 Tokyo** (`.github/workflows/weekly-data.yml`):
   - `tools/fetch.py` downloads every series from FRED, plus the SF Fed's quarterly TFP file, into `data/data.json`.
   - `tools/build.py --data-only` computes every derived number, the scorecard and the verdict with fixed rules. It writes `data/facts.txt` and `data/facts.json` and appends a row to `data/history.csv`.
   - The Action commits anything that changed and records what changed in `data/fetch-log.md`.
2. **Claude scheduled task, Saturday 08:33 Tokyo:**
   - Reads `facts.txt` and `fetch-log.md`.
   - Writes the bottom line and the strongest case each way into `data/editorial.json`, and updates the release calendar.
   - Runs the full build, which checks that the narrative agrees with the computed verdict and writes `site/index.html`.
   - Commits, then republishes the live page.

Run it by hand from the Actions tab ("Weekly data update" → Run workflow).

## Files
| Path | What | Written by |
|---|---|---|
| `data/data.json` | All data series, SF Fed figures, industry groups | fetch.py |
| `data/editorial.json` | Narrative and release calendar | Claude task |
| `data/facts.txt`, `facts.json` | Every computed number and the verdict | build.py |
| `data/history.csv` | One row per week: verdict, tests, key readings | build.py |
| `data/fetch-log.md` | What the last fetch changed or failed on | fetch.py |
| `site/template.html` | The page | by hand |
| `site/index.html` | The built page | build.py |
| `tools/update.py` | Safe edits to the JSON files | — |

The verdict rules and industry groups were frozen on 2026-10-30. Change them only by hand, and say so on the page.
