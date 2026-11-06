Write this week's commentary for the "Econ Productivity Uplift" tracker and republish it. The tracker is a public page asking "Is AI changing the U.S. economy yet?" The page leads with a headline, four key numbers and six charts (productivity, its sources, the industry fingerprint, AI investment, jobs, labor share). Each chart's headline is written automatically by the page from the data; your words are the top headline, the summary, the "Latest releases" line, and the appendix (the case each way and the claims check). The appendix also holds five stage statuses computed by fixed rules: Adoption, Money, Work, Output and Who gains.

A GitHub Action has already fetched the data and computed every number, test, significance tier, stage status and verdict. Your job is the words, the release calendar and the publish. You never fetch data series yourself and never edit data/data.json, the template or the tools.

REPO: mrtylerhorn-lgtm/econ-productivity-uplift (public, read-only for this task). LIVE PAGE: https://claude.ai/artifact/Suz3bBPDbSBRKaaxTyHftj
COMMENTARY STORE: the project doc `tracker/editorial.json` in this task's Claude project (Projects tool). This, not the repo, holds the latest commentary. Never commit or push to the repo.

## Steps
1. Clone the repo: `git clone https://github.com/mrtylerhorn-lgtm/econ-productivity-uplift.git` (public, no sign-in needed). Work inside the clone.
2. Check that the Action ran today: the first line of data/fetch-log.md should carry today's Tokyo date (`TZ=Asia/Tokyo date +%F`). If it doesn't, the Action failed or hasn't run. Don't write new commentary and republish nothing. End with a message saying the Action didn't run, so the user can check the Actions tab on GitHub (scheduled Actions can be switched off after long inactivity; re-enable them there).
3. Load last week's commentary: call the Projects tool, method `project_read`, path `tracker/editorial.json`.
   - If it returns the JSON (inline, or as a local file path), write it over data/editorial.json in the clone with Python. Check that it parses and has "copy" and "calendar" keys.
   - If the doc is missing or invalid, keep the repo's data/editorial.json and say so in your final message.
   - Then read data/fetch-log.md (what changed, what failed), data/facts.txt (every computed number, the TIERS, STAGES and CHARTS lines, and the verdict) and data/editorial.json (last week's words).
4. Calendar: list the upcoming releases as rows [date, release, what it updates]. Include:
   - BLS Employment Situation (jobs, graduate unemployment, occupation data, factory hours)
   - BLS Productivity and Costs (output per hour, labor share)
   - BEA GDP (investment, payroll; GDI comes with the second estimate)
   - BEA GDP by industry (industry test; comes with the third GDP estimate)
   - SF Fed TFP (no fixed schedule)
   - St. Louis Fed AI-use survey (no fixed schedule)
   Check https://www.bls.gov/schedule/ and https://www.bea.gov/news/schedule with WebFetch (add a throwaway ?cb=… query). Never guess a date, and drop past dates. Save with `python3 tools/update.py set calendar '<JSON>'`.
5. Write the narrative from facts.txt and fetch-log.md with `python3 tools/update.py set copy.FIELD '<JSON>'`:
   - `copy.verdict`: exactly the Output verdict facts.txt gives.
   - `copy.headline`: one line of at most 20 words. Lead with the most important new number of the week if there is one (a productivity, jobs or GDP release), then what it means, e.g. "Productivity grew at a 3.6% rate last quarter, but from more equipment and harder work, not smarter work." It must agree with facts.txt, including the CHARTS and STAGES lines.
   - `copy.bottomLine`: 3–4 short sentences, the so-what for a non-economist. Cover where AI shows up in the economy now (draw on the charts: pace, sources, industry link, investment, jobs, labor share), the biggest thing still missing, and what to watch next with dates.
   - `copy.changed`: 1–2 sentences starting "Latest releases:". Name each release with its date and what it changed. If any stage status or the verdict moved, say so and why. If nothing new came out, say "Latest releases: no new data this week." and name the next release. If fetch-log lists problems, say which source wasn't updated.
   - `copy.caseFor` and `copy.caseAgainst`: 3–5 items each, as [{"h": short claim, "body": ≤55 words}]. The question is whether AI is already changing the economy (all stages, not just productivity). Write each side as its most capable honest advocate would argue it. Lead with the strongest evidence, and no strawmen. Every number must come from facts.txt, at the rounding the page shows. Don't hedge inside a case (the other column does that), but never overstate what a number shows. Keep points that are still true, and refresh their numbers.
   - `copy.claims`: keep each existing item [{"who","claim","verdict","check"}]. Never change the "who" or "claim" (they are quotes). Refresh the "verdict" (≤6 words) and the "check" (≤60 words) so every number matches facts.txt. Don't add or remove claims; the owner does that.
6. Run `python3 tools/build.py`. It must pass every check; it fails if copy.verdict disagrees with the rules.
   - Extract the last inline `<script>` (the one without a type) from site/index.html and run `node --check` on it.
   - Render once with Python Playwright (preinstalled; wrap the file in `<!doctype html><html><head><meta charset=utf-8></head><body>…</body></html>`) at 1100px and 390px. Confirm there are no page errors and no horizontal scroll. A failed Google Fonts load is fine.
   - If any check fails, don't publish or save; report it.
7. Republish with the Artifact tool: file_path = the clone's site/index.html, url = the live page above. Never create a new artifact, and omit `icon`. If the publish is refused because the live version is newer, read the saved copy it points to. If that copy is only the previous build (plus the page skeleton), publish again unchanged.
8. Save the commentary: call the Projects tool, method `project_write`, path `tracker/editorial.json`, local_path = the clone's data/editorial.json. Do this only after a successful publish. Don't git commit or push anything.
9. End with 2–3 sentences: what changed, and whether any stage status or the verdict moved (if one did, say so first). Name any source that failed, and say if the commentary couldn't be loaded or saved.

## Writing rules
- Readers are mostly non-economists. Use plain English and short sentences.
- The tone is careful and skeptical. Weigh competing views fairly and don't anchor on any single framework. The page draws on several:
  - working smarter vs harder (SF Fed, Klein)
  - the J-curve (Brynjolfsson)
  - competence vs coordination, with wages and roles moving first (Imas, Koh and Legg)
- Terms:
  - "Underlying efficiency", not "real efficiency".
  - "Inflation-adjusted interest rates", not "real rates".
  - The factory-hours series is "factory production workers".
  - Information-processing equipment is "information-processing equipment" (computers, communications gear and instruments), not just "computers".
  - The pay test compares "management, business and financial" workers (managers plus accountants, analysts and HR specialists, a rough proxy for coordinators) with "office and administrative support" workers.
  - Period labels: "1997–2003", "2004–19", "2002–19" (work-test history), "2010–19" (industry trend), "since the end of 2023". Tech investment data begin in 1959; the labor share series begins in 1947 (say "lowest on record", not "lowest since 1947").
- Imports don't subtract from GDP. Imported goods are taken out of spending only because they were never U.S. production. Say "much of the AI spending buys computers made abroad, so it adds less to U.S. output", never that imports "cancel" or "subtract from" growth.
- The industry and occupation charts are correlations across a handful of groups. Call them a link, not proof; give the chance and the worst case when one group is dropped.
- Every work signal has other possible causes. Tech hiring fell from 2023 as interest rates rose. Graduates' edge swings with the cycle and was already small at the end of 2023, so the test is its change since then, not its level. The labor share is pay per hour over output per hour, so it dips after a fast productivity quarter, and it swings with the business cycle. Much of the tech-investment jump is data-center building, and the ratio is in current dollars. Never write as if a work or income signal proves AI is the cause.
- Industries: Information builds and sells AI, so it is shown apart and left out of the counted cross-industry test (chart 3). The earlier gap test (professional & business services vs retail, leisure and construction) is now a cross-check only.
- Never change the rules, groups, template or tools. The output tests were set on 2026-10-30; the significance tiers, stage rules, cross-industry test and chart layout on 2026-11-06. If the data seems to call for a change, say so in your final message instead.
- Significance tiers (facts.txt TIERS line): chance 5% or less is a "clear signal", 5–20% "suggestive", above 20% or the wrong direction "no signal". Use these words, give the number ("chance alone would produce this about X% of the time"), and never call a suggestive result clear, reliable, significant or unusual. Stage statuses move only on clear signals; you may say what is suggestive.
- Check every "highest since …", "lowest since …" or "wider than any …" claim against facts.txt.
