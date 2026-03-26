---
name: uxr-project-tracker
description: Query and report on the UXR Team Projects GitHub Project board (coreai-microsoft, project #40). Use when the user asks about UXR research projects, project status, completed projects, active projects, researcher workload, report URLs, project timelines, or any questions about the UXR team's GitHub project tracker. Triggers on questions like "what projects were completed last week", "show me active projects for [person]", "get report URLs", "what is [researcher] working on", "projects by product", or any reference to UXR/research project tracking.
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

### Step 1: Ask the user TWO questions (use ask_user tool)

**Question 1 — Table format:**
"Which table format would you like?"
Choices:
- **Detailed table** — Columns: Researcher, Study (linked to issue), Closed date, Report (linked to report), Summary
- **Word-friendly table** — Columns: Researcher, Study (linked directly to the report URL), Summary. No Closed or Report columns. Solid borders for clean copy-paste into Word.

**Question 2 — Time period:**
"What start date should I use for completed studies? (e.g. 2026-02-04)"

### Step 2: Query the project board

```bash
python scripts/query_project.py --status "Closed-Completed" --closed-after DATE --format json --fields "Title,Status,Assignees,Report URL,_url,_closedAt"
```

### Step 3: Scrape report summaries using `scrape_reports.py`

**CRITICAL: Summaries MUST come from the actual linked reports, NOT from GitHub issue descriptions.** If scraping fails, leave the summary blank and tell the user — never silently substitute content from the GitHub issue.

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
   This opens Edge with cached auth, visits each URL, extracts text, and saves results to `scraped_reports.json`.

3. **Review the output** — the script prints character counts per URL. If a URL returned 0 or very few characters, the scrape likely failed (auth issue, SPA didn't render, etc.). Tell the user which ones failed.

The script handles these URL types automatically:
- **HITS pages** (`hits.microsoft.com`) — SPA, waits 8s then grabs paragraphs > 80 chars
- **SharePoint documents** (`sharepoint.com`) — tries main page first, then iframes for embedded Word docs
- **Figma decks** (`figma.com`) — attempts to extract visible text, but Figma is a canvas SPA so results may be empty
- **Azure Data Explorer dashboards** (`dataexplorer.azure.com`) — metric dashboards, not text reports; summarize based on title/visible metadata
- **GitHub repos** — use `web_fetch` or navigate to markdown files and extract rendered content

For URL types not handled by the script, add a new scraping function following the existing pattern.

### Step 4: Write catchy, accurate 2-3 sentence summaries

Take the raw scraped text and write a **concise 2-3 sentence summary** that is:
- **Factual and accurate** — no embellishment or speculation
- **Interesting and catchy** — written to grab a busy reader's attention
- **Action-oriented** — highlight key findings, surprising data points, or clear takeaways

Examples of good summary style:
- "Five power users who constantly hit rate limits didn't revolt at token-based billing -- they just want to see the meter. Give them real-time token dashboards, configurable warnings, and overage options instead of hard cutoffs, and they'll adapt."
- "Of 424 developers surveyed, 99.5% already use some AI coding tool -- the battle isn't adoption, it's tool choice. The biggest blockers for Copilot holdouts are myths ('my code must be on GitHub') and institutional friction, while Amazon Q's market share turns out to be mostly AWS lock-in in disguise."

### Step 5: Generate the HTML file

Save summaries to `summaries.json` mapping each issue URL to its summary text.

**For the Detailed table:**
```bash
python scripts/query_project.py --status "Closed-Completed" --closed-after DATE --format html --summaries-json summaries.json --output completed-studies.html
```
This produces a table with columns: Researcher | Study (linked to issue) | Closed | Report (linked to report) | Summary

**For the Word-friendly table:**
```bash
python scripts/query_project.py --status "Closed-Completed" --closed-after DATE --format html-word --summaries-json summaries.json --output completed-studies.html
```
This produces a table with columns: Researcher | Study (linked to report URL) | Summary
- No Closed or Report columns
- Solid 1px borders on all cells for clean Word paste
- Uses `font-family: 'Segoe UI', Calibri, Arial, sans-serif` and `font-size: 11pt` / `10pt`

### Step 6: Open and report results

Open the generated file with `Start-Process completed-studies.html` and tell the user:
- How many studies were included
- How many had report summaries scraped
- For Word-friendly table: remind them to select the table in the browser, Ctrl+C, Ctrl+V into Word

### Important Notes

- **Never silently substitute GitHub issue content for report summaries.** If a report can't be scraped, leave the summary blank and tell the user.
- The Playwright browser profile at `C:\Users\dagottl\AppData\Local\Temp\pw-profile` caches Microsoft SSO. If auth expires, the script may return empty content — tell the user to log in manually via Edge and retry.
- HITS pages (hits.microsoft.com) load via SPA — the script waits 8 seconds after navigation.
- If a report URL is empty or "None", skip it — leave Summary blank.
- Researcher names may have pronoun suffixes like "(SHE/HER)" from GitHub profiles — the script auto-strips these.
- Figma decks are canvas-based SPAs and may not yield text content. If scraping returns only CSS/HTML markup, treat it as a failed scrape.

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
