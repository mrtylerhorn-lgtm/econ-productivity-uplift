Write this week's commentary for the "Econ Productivity Uplift" tracker (page title "Productivity Smoke"), a public page on whether AI is showing up in U.S. productivity data, and republish it.

A GitHub Action has already fetched the data and computed every number, the scorecard and the verdict. Your job is the words, the release calendar and the publish. You never fetch data series yourself and never edit data/data.json, the template or the tools.

REPO: mrtylerhorn-lgtm/econ-productivity-uplift (public). LIVE PAGE: https://claude.ai/artifact/Suz3bBPDbSBRKaaxTyHftj

## Steps
1. Attach the repo with the add_repo tool (owner mrtylerhorn-lgtm, repo econ-productivity-uplift, access "push"), then clone it as that tool's result says. Work inside the clone.
2. Check the Action ran today: the first line of data/fetch-log.md should carry today's Tokyo date. If it doesn't, the Action failed or hasn't run. Don't write new commentary. Republish nothing, and end with a message saying the Action didn't run, so the user can check the Actions tab on GitHub.
3. Read data/fetch-log.md (what changed, what failed), data/facts.txt (every computed number and the verdict) and data/editorial.json (last week's words).
4. Calendar: list the upcoming releases as rows [date, release, what it updates]. Include:
   - BLS Productivity and Costs (output per hour, both measures)
   - BLS Employment Situation (factory hours, industry hours)
   - BEA GDP (investment; GDI comes with the second estimate)
   - BEA GDP by industry (industry test; it comes with the third GDP estimate)
   - SF Fed TFP (no fixed schedule)
   Check https://www.bls.gov/schedule/ and https://www.bea.gov/news/schedule with WebFetch (add a throwaway ?cb=… query). Never guess a date. Drop past dates. Save with `python3 tools/update.py set calendar '<JSON>'`.
5. Write the narrative from facts.txt and fetch-log.md with `python3 tools/update.py set copy.FIELD '<JSON>'`:
   - `copy.verdict`: exactly the verdict facts.txt gives.
   - `copy.bottomLine`: 3–4 short sentences, the so-what for a non-economist: what the evidence says, the main thing holding the verdict back, and what would change it.
   - `copy.changed`: 1–2 sentences starting "Latest releases:". Name each release with its date and what it changed. If the verdict moved, say so and why. If nothing new came out, say "Latest releases: no new data this week." and name the next release. If fetch-log lists problems, say which source wasn't updated.
   - `copy.caseFor` and `copy.caseAgainst`: 3–5 items each, as [{"h": short claim, "body": ≤55 words}]. Write each side as its most capable honest advocate would argue it. Lead with the strongest evidence; no strawmen. Every number must come from facts.txt, at the rounding the page shows (usually one decimal). Don't hedge inside a case (the other column does that), but never overstate what a number shows. Keep points that are still true, and refresh their numbers.
6. Run `python3 tools/build.py`. It must pass every check; it fails if copy.verdict disagrees with the rules. Extract the last inline `<script>` (the one without a type) from site/index.html and run `node --check`. Render once with Python Playwright (preinstalled; wrap the file in `<!doctype html><html><head><meta charset=utf-8></head><body>…</body></html>`) at 1100px and 390px, and confirm there are no page errors and no horizontal scroll. A failed Google Fonts load is fine.
7. Commit data/editorial.json and site/index.html with the message "Commentary YYYY-MM-DD" and push to main. If the push fails, carry on and mention it at the end.
8. Republish with the Artifact tool: file_path = the clone's site/index.html, url = the live page above. Never create a new artifact, and omit `icon`.
9. End with 2–3 sentences: what changed, and whether the verdict moved (if it moved, say so first). Name any source that failed.

## Writing rules
- Readers are mostly non-economists. Use plain English and short sentences. The tone is careful and skeptical, in the spirit of Matthew C. Klein: separate working smarter (underlying efficiency) from working harder (utilization), and remember that the 1990s boom showed up in the data only around 1997.
- Terms:
  - "Underlying efficiency", not "real efficiency".
  - "Inflation-adjusted interest rates", not "real rates".
  - The factory-hours series is "factory production workers".
  - Information-processing equipment is "computers and related equipment" (it covers communications gear and instruments, not chips).
  - Period labels: "1997–2003", "2004–19", "2010–19" (industry trend), "since the end of 2023".
- Industry groups are fixed:
  - information = "AI producers" (data centers, software publishers): shown, not counted
  - professional & business services = "AI users" proxy (it includes office support and staffing)
  - retail, leisure, construction = hands-on
  Never write as if the industry data proves AI use.
- Never change the verdict rules, the industry groups, the template or the tools. They were frozen on 2026-10-30. If the data seems to call for a change, say so in your final message instead.
- Report significance the way facts.txt does ("chance alone would produce this about X% of the time"). Don't call a result unusual unless its test passes.
- Check every "highest since …" or "wider than any …" claim against facts.txt.
