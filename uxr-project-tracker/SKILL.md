---
name: uxr-project-tracker
description: Query and report on the UXR Team Projects GitHub Project board (coreai-microsoft, project #40). Also known as the "Friday Minutes Table". Use when the user asks about UXR research projects, project status, completed projects, active projects, researcher workload, report URLs, project timelines, the Friday Minutes Table, or any questions about the UXR team's GitHub project tracker. Triggers on questions like "what projects were completed last week", "show me active projects for [person]", "get report URLs", "what is [researcher] working on", "projects by product", "Friday Minutes Table", "recently completed research table", or any reference to UXR/research project tracking.
---

# UXR Project Tracker

Query the UXR Team Projects board at https://github.com/orgs/coreai-microsoft/projects/40

## Prerequisites

The user must be authenticated with `gh` CLI with `read:project` scope. If queries fail with INSUFFICIENT_SCOPES, run:
```
gh auth refresh -s read:project
```

## How to Query

Run `scripts/query_project.py` with filters. The script fetches all items via GraphQL and filters client-side.

### Common Queries

**Completed projects in a time range:**
```bash
python scripts/query_project.py --status "Closed-Completed" --closed-after 2026-02-11
```

**Active projects (In progress):**
```bash
python scripts/query_project.py --status "In progress"
```

**Active projects by researcher:**
```bash
python scripts/query_project.py --status "In progress" --assignee "mamaleki"
```

**Projects by product:**
```bash
python scripts/query_project.py --product "App Service"
```

**Report URLs from recently closed items:**
```bash
python scripts/query_project.py --report-urls --closed-after 2026-02-04
```

**Search by keyword:**
```bash
python scripts/query_project.py --search "migration" --status "In progress"
```

### Output Formats

- `--format table` (default): Terminal table with key columns
- `--format json`: JSON array for further processing
- `--format csv`: CSV output
- `--format html`: Styled HTML page with Researcher, Study, Closed, Report, Summary columns
- `--output FILE`: Write output to a file instead of stdout

### Field Selection

- Default fields: Title, Status, Assignees, Product, Team, Research Phase, URL
- `--all-fields`: Show every field
- `--fields "Title,Status,Report URL,_closedAt"`: Custom field selection

### Available Filters

| Flag | Matches |
|------|---------|
| `--status` | Exact match on Status field |
| `--assignee` | Substring match on assignee login or name |
| `--product` | Substring match on Product |
| `--team` | Substring match on Team |
| `--research-phase` | Substring match on Research Phase |
| `--semester` | Substring match on Semester |
| `--priority` | Substring match on Priority |
| `--closed-after DATE` | Issue closed on/after YYYY-MM-DD |
| `--closed-before DATE` | Issue closed on/before YYYY-MM-DD |
| `--search TEXT` | Substring in title or body |

Filters can be combined. All filters are AND logic.

## Generating the Completed Studies HTML Page

When the user asks to produce or generate the completed studies HTML page, follow this workflow:

### Step 1: Determine what to generate

If the user asks for "both tables", generate both without asking. Otherwise, ask:

**Question 1 — Table format (use ask_user tool):**
"Which table format would you like?"
Choices:
- **Both tables (Recommended)** — Detailed + Word-friendly
- **Detailed table** — Columns: Study (linked to issue), Researcher, Closed date, Report (linked to report), Summary, Key Learnings (verbatim from closing comment, if present)
- **Word-friendly table** — Columns: Study (linked directly to the report URL), Researcher, Key Learnings / Summary. No Closed or Report columns. Solid borders for clean copy-paste into Word. If a study has a key learnings closing comment, it replaces the summary in the last column.

**Question 2 — Time period:**
"What start date should I use for completed studies? (e.g. 2026-02-04)"

### Step 2: Query the project board

```bash
python scripts/query_project.py --status "Closed-Completed" --closed-after DATE --format json --fields "Title,Status,Assignees,Report URL,_url,_closedAt"
```

### Step 3: Scrape report summaries using `scrape_reports.py` (REQUIRED)

**Summaries must come from the actual linked reports. Never write summaries from just the GitHub issue description.** If scraping fails, troubleshoot it first — re-run the script, check browser auth, try alternate extraction. Only fall back to the GitHub issue body as an absolute last resort.

For each item that has a non-empty `Report URL`, update `scrape_reports.py` with the current URLs and run it. The script uses Playwright with a persistent Edge browser profile (`C:\Users\dagottl\AppData\Local\Temp\pw-profile`) that has Microsoft SSO auth cached.

1. **Update the `URLS` dict** in `scrape_reports.py` — map each issue URL to its report URL:
   ```python
   URLS = {
       "https://github.com/coreai-microsoft/caidr/issues/NNN": "https://hits.microsoft.com/...",
       "https://github.com/coreai-microsoft/caidr/issues/MMM": "https://microsoft-my.sharepoint.com/...",
   }
   ```
   Only include items that have a non-empty Report URL. Don't scrape the same URL twice.

2. **Run the script:**
   ```bash
   python scrape_reports.py
   ```
   This opens Edge with cached auth, visits each URL in a **separate tab** (to prevent cascading navigation errors), extracts text, and saves results to `scraped_reports.json`.

3. **Review the output** — the script prints status per URL:
   - `[OK]` (>150 chars): Good content scraped
   - `[LOW]` (1-150 chars): Minimal content — likely a failed scrape or placeholder page
   - `[EMPTY]` (0 chars): Nothing extracted
   - `[ERROR]`: Navigation or auth failure

4. **Handle failures:**
   - If the first URL fails but later ones succeed, auth may not have been cached yet. Re-run the script — Playwright reuses the browser profile so auth should persist from the successful pages.
   - If a HITS page returns only boilerplate ("Tap the edit button..."), the scraper's boilerplate filter should catch this. If it still shows up, the note may be access-restricted.
   - If a SharePoint page returns 0 chars, it may be a PowerPoint rendered in an Office Online canvas that doesn't expose text to DOM queries. Use the GitHub issue body as fallback.

The script handles these URL types automatically:
- **HITS pages** (`hits.microsoft.com`) — React SPA, waits 12s, extracts from content containers first, then all elements, filters known boilerplate text. Works for both `/note/` and `/study/` URLs.
- **SharePoint documents** (`sharepoint.com`) — waits 15s, tries main page, then all iframes, then body innerText from all frames as last resort
- **Figma decks** (`figma.com`) — attempts to extract visible text, but Figma is a canvas SPA so results may be empty
- **aka.ms / short URLs** — follows redirects, detects the landing domain, then uses the appropriate scraper
- **Azure Data Explorer dashboards** (`dataexplorer.azure.com`) — metric dashboards, not text reports; summarize based on title/visible metadata
- **GitHub repos** — use `web_fetch` or navigate to markdown files and extract rendered content

For URL types not handled by the script, add a new scraping function following the existing pattern.

### Step 4: Extract key learnings from closing comments

Researchers often close GitHub issues with a comment containing "Key Learnings", "Learnings", or "Findings". These should be extracted **verbatim** and included in the tables.

1. **Fetch comments** for each completed study using the GitHub API (e.g., `gh api` or the MCP `issue_read` tool with `get_comments`).

2. **Identify key learnings comments** — look for the **last comment** on the issue that contains one of these markers near the start:
   - `Key Learnings`
   - `Learnings:`
   - `Findings`

3. **Validate the comment is ACTUALLY key learnings** — NOT every closing comment qualifies. A valid key learnings comment:
   - Presents **specific research findings or insights as bullet points** (e.g., "users struggled with X", "70% preferred Y")
   - Is structured as a list of what was learned from the research
   
   A comment is NOT key learnings if it:
   - Merely describes what happened with the study (e.g., "we combined this with another study", "the scope changed")
   - Lists outcomes/next steps without actual findings (e.g., "filed 3 bugs", "shared with team")
   - Is a status update or closing note about the project history
   
   **When in doubt, skip it.** If a closing comment doesn't clearly present research findings, do NOT include it in key_learnings.json. Instead, extract findings from the linked report/study document and use those for the summary.

4. **Extract the learnings text** — take the text starting from after the heading marker. If the whole comment is learnings-focused (no unrelated preamble), use the full comment body. Strip any leading link/report URL lines that precede the learnings content.

5. **Save to `key_learnings.json`** — map each issue URL to its extracted learnings text (GitHub markdown format):
   ```json
   {
     "https://github.com/coreai-microsoft/caidr/issues/NNN": "- Finding one\n- Finding two\n..."
   }
   ```
   Only include issues that actually have a key learnings comment. Issues without one are simply omitted.

6. **Not all issues will have key learnings** — that's fine. The detailed table shows an empty cell; the word-friendly table falls back to the AI-written summary.

### Step 5: Write catchy, outcome-focused 2-3 sentence summaries

**Summaries must come from the actual scraped report content and/or the closing comment.** If scraping failed, troubleshoot it first (re-run the script, check auth, try alternate extraction). Only fall back to the GitHub issue body as an absolute last resort after exhausting scraping options.

For **every** completed study, write a summary — not just the ones with scraped reports.

**Summary content and focus:**

Summaries should emphasize **outcomes, key learnings, decisions made, and next steps** — not methodology or sample sizes. The reader wants to know what was learned and what happens next, not how the study was conducted.

1. **What was learned or decided** — the key findings, outcomes, or decisions that resulted from the research
2. **What happens next** — next steps, recommendations, or how the findings will be applied
3. **Brief context only if needed** — a short phrase of context is fine, but don't spend a sentence just describing the study setup

**Verification rule:** Before finalizing summaries, re-read the scraped report content and confirm every claim in the summary is directly supported. Do not mix information from GitHub issue comments into the summary as if it came from the study report. If a detail only appears in a GitHub comment (not the report), either omit it or clearly attribute it.

**Priority order for summary source material:**
1. **Scraped report content** (required) — use the actual report text from `scraped_reports.json`
2. **Closing comment learnings** — the key learnings/findings from the closing comment are also valid source material
3. **GitHub issue body** (last resort fallback) — only if scraping failed after troubleshooting, or there's no report URL
4. **Issue title + labels** (emergency fallback) — if the issue body is also empty/minimal, write a brief summary based on the title and labels

**Never leave a summary blank.** A short summary from the issue description is always better than an empty cell.

Take the source material and write a **concise 2-3 sentence summary** that is:
- **Outcome-focused** — lead with what was learned, decided, or recommended, not methodology
- **Forward-looking** — mention next steps or implications when available
- **Verified** — re-read the scraped content and confirm every claim before including it
- **Factual and accurate** — no embellishment or speculation
- **Interesting and catchy** — written to grab a busy reader's attention

Examples of good summary style:
- "Five power users who constantly hit rate limits didn't revolt at token-based billing -- they just want to see the meter. Give them real-time token dashboards, configurable warnings, and overage options instead of hard cutoffs, and they'll adapt."
- "The original question — where does AITK end and Foundry begin — became moot when the decision was made to merge the two extensions. The study pivoted to mapping the developer journey across the combined experience and produced quick-win recommendations for the April GA and a prioritized list of topics to investigate at Build."

### Step 6: Generate the HTML file

Save summaries to `summaries.json` and key learnings to `key_learnings.json`, each mapping issue URLs to their respective text.

**For the Detailed table:**
```bash
python scripts/query_project.py --status "Closed-Completed" --closed-after DATE --format html --summaries-json summaries.json --key-learnings-json key_learnings.json --output completed-studies.html
```
This produces a table with columns: Study (linked to issue) | Researcher | Closed | Report (linked to report) | Summary | Key Learnings
The Key Learnings column only appears if at least one study has key learnings. Text is rendered with basic markdown formatting (bold, bullet lists).

**For the Word-friendly table:**
```bash
python scripts/query_project.py --status "Closed-Completed" --closed-after DATE --format html-word --summaries-json summaries.json --key-learnings-json key_learnings.json --report-titles-json report_titles.json --report-links-json report_links.json --output completed-studies.html
```
This produces a table with columns: Study | Key Learnings / Summary
- **Study cell** contains the study name (linked to report URL) with the researcher name below it in smaller gray text. No separate Researcher column.
- **Study names** use the report document title (from `report_titles.json`) instead of the GitHub issue title when available. Extract titles from the SharePoint/HITS document header when scraping.
- **Study links** use the board's Report URL field. If a study has no Report URL on the board but does have a report, add its URL to `report_links.json` to override the link.
- If a study has key learnings, they **replace** the summary in the last column
- If no key learnings, the AI-written summary is used
- Column header shows "Key Learnings / Summary" when any study has key learnings
- No Closed, Report, or separate Researcher columns
- Solid 1px borders on all cells for clean Word paste
- Uses `font-family: 'Segoe UI', Calibri, Arial, sans-serif` and `font-size: 11pt` / `10pt`

**Supporting JSON files for the Word-friendly table:**
- `report_titles.json` — maps issue URLs to report document titles (extracted from SharePoint headers during scraping). Used instead of GitHub issue titles for display.
- `report_links.json` — maps issue URLs to override report link URLs. Only needed when a study's Report URL field is empty on the project board but a report exists elsewhere (e.g., shared in the closing comment).

### Step 7: Open and report results

Open the generated file with `Start-Process completed-studies.html` and tell the user:
- How many studies were included
- How many had report summaries scraped
- For Word-friendly table: remind them to select the table in the browser, Ctrl+C, Ctrl+V into Word

### Important Notes

- **Never skip scraping.** Always scrape the actual report first. If scraping fails, troubleshoot (re-run, check auth, try different extraction) before falling back to the GitHub issue body. A summary from the issue body alone is a last resort, not a default.
- **Verify all summary claims** against the scraped source content. Do not include details from GitHub comments as if they were study findings. If a fact only appears in a comment, omit it or attribute it clearly.
- The scraper uses a **fresh browser tab per URL** to prevent cascading navigation errors. If one URL fails (e.g., access denied), the next URL still works.
- The scraper **filters known HITS boilerplate** ("Tap the edit button...", PII warnings, locked collection notices). If a HITS page returns only boilerplate after filtering, the scrape failed — use the GitHub issue body as fallback.
- The Playwright browser profile at `C:\Users\dagottl\AppData\Local\Temp\pw-profile` caches Microsoft SSO. If auth expires, the script may return empty content — tell the user to log in manually via Edge and retry.
- HITS pages (hits.microsoft.com) load via React SPA — the script waits 12 seconds after navigation and tries multiple extraction strategies (content containers → all elements → full body innerText).
- SharePoint pages wait 15 seconds and try main page → iframes → body innerText from all frames.
- If a report URL is empty or "None", skip it — use GitHub issue body for the summary.
- Researcher names may have pronoun suffixes like "(SHE/HER)" from GitHub profiles — the script auto-strips these.
- Figma decks are canvas-based SPAs and may not yield text content. If scraping returns only CSS/HTML markup, treat it as a failed scrape and use the issue body.
- **aka.ms and other short URLs**: The scraper follows redirects automatically, detects the landing domain, and routes to the appropriate extraction strategy.

## Key Definitions

- **"Completed"** = Status is "Closed-Completed", date based on GitHub issue closedAt
- **"Active"** = Status is "In progress" only
- **"Researchers"** = Assignees field

## Interpreting Results

- The `_url` field links to the GitHub issue
- The `Report URL` field contains links to research reports/dashboards
- When user asks for "report URLs from closed issues," use `--report-urls` with date filters
- Assignee names come from GitHub profiles; search by login or display name

## Field Reference

For all field options (Status, Product, Team, etc.), see [references/project-schema.md](references/project-schema.md).
