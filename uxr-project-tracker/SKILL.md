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

### Step 3: Scrape report summaries using Playwright

For each item that has a non-empty `Report URL`, use Playwright MCP browser tools. **Don't scrape the same URL twice** — cache results for shared report URLs.

1. **Navigate** to the report URL using `playwright-browser_navigate`
2. **Wait** for the page to load (use `playwright-browser_wait_for` with `time: 5`)
3. **Extract summary text** using `playwright-browser_evaluate` with this JavaScript:
   ```javascript
   () => {
     const paragraphs = document.querySelectorAll('p');
     const texts = [];
     for (const p of paragraphs) {
       const text = p.textContent.trim();
       if (text.length > 80) texts.push(text);
     }
     return texts.slice(0, 12).join('\n\n');
   }
   ```
4. For **SharePoint documents** (URLs containing `sharepoint.com`), content is in an iframe. Use `playwright-browser_run_code` instead:
   ```javascript
   async (page) => {
     const frames = page.frames();
     for (const frame of frames) {
       try {
         const text = await frame.evaluate(() => {
           const paras = document.querySelectorAll('p');
           const texts = [];
           for (const p of paras) {
             const t = p.textContent.trim();
             if (t.length > 60) texts.push(t);
           }
           return texts.slice(0, 20).join('\n\n');
         });
         if (text && text.length > 100) return text;
       } catch(e) { continue; }
     }
     return '';
   }
   ```
5. For **Azure Data Explorer dashboards** (URLs containing `dataexplorer.azure.com`), look for the dashboard title and description from the page snapshot. These are metric dashboards, not text reports, so summarize what the dashboard tracks based on its title and visible metadata.
6. For **GitHub repos**, navigate to markdown files and extract the rendered article content.

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

- Some report URLs may require Microsoft authentication. If a page shows "Authenticating..." for more than 10 seconds, skip that summary.
- HITS pages (hits.microsoft.com) load via SPA — always wait 5 seconds after navigation.
- If a report URL is empty or "None", skip it — leave Summary blank.
- Researcher names may have pronoun suffixes like "(SHE/HER)" from GitHub profiles — the script auto-strips these.

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
