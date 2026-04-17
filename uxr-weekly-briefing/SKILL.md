---
name: uxr-weekly-briefing
description: Generate the weekly UXR 3D Briefing (Deadlines, Deployments, Dependencies) from the UXR Team Projects GitHub Project board. Use when the user asks for a weekly update, weekly briefing, 3D report, status report, or asks about deadlines/deployments/dependencies across UXR studies. Also triggers on "what's new in UXR", "research team status", "what studies are in progress", "what studies completed this week", or any reference to the UXR weekly briefing.
---

# UXR Weekly Briefing — 3D Report

Generate a comprehensive weekly briefing covering Deadlines, Deployments, and Dependencies from the UXR Team Projects board at https://github.com/orgs/coreai-microsoft/projects/40

## Prerequisites

The user must be authenticated with `gh` CLI with `read:project` scope. If queries fail with INSUFFICIENT_SCOPES, run:
```
gh auth refresh -s read:project
```

## What This Skill Produces

A clean, navigable HTML report with four sections:

1. **📅 Deadlines** — All "In progress" studies: what's new, what progressed, researcher, labels, research phase, target dates, and a summary of recent activity (last 7 days)
2. **🚀 Deployments** — All studies "Closed-Completed" in the last 7 days: study name hotlinked to the report URL, researcher, labels, and a one-line study summary
3. **⚠️ Dependencies** — Any "On hold" studies or in-progress studies with blockers: project name, blocker details, recent comments, and link to the issue
4. **👥 Key Stakeholders** — Researchers, PMs, and Designers across all relevant studies

## Workflow

### Step 1: Fetch the data

Run the data fetch script from `copilot-skills/uxr-weekly-briefing/scripts/`:

```bash
python copilot-skills/uxr-weekly-briefing/scripts/weekly_briefing.py fetch --days 7 --output copilot-skills/uxr-weekly-briefing/briefing_data.json
```

This fetches all project items via GraphQL, fetches recent comments for in-progress and on-hold issues, and outputs structured JSON with items categorized into deadlines/deployments/dependencies.

Review the output counts. If the script fails with auth errors, prompt the user to run `gh auth refresh -s read:project`.

### Step 2: Analyze the data

Read `briefing_data.json` and review each section:

#### For Deadlines (In Progress):
- **NEW studies**: Items where `is_new` is `true` (created in the last 7 days). Call these out prominently.
- **Active studies**: All other in-progress studies. Look at `recent_comments` and `recent_events` to summarize what happened in the last 7 days.
- **Target dates**: If `target_date` is set, call it out as a deadline. If the date is within 14 days, flag it as upcoming.
- **Project summary**: Use the `body` field of each issue to write a brief (1-2 sentence) summary of what the study is about.
- **Activity summary**: From `recent_comments`, write a brief summary of what happened this week (e.g., "Recruiting underway, 5 of 8 participants scheduled" or "Analysis phase — draft report shared for review").

#### For Deployments (Recently Completed):
- List every study that was closed-completed in the period.
- For each study with a `report_url`, use Playwright to scrape and read the study summary (see Step 3).
- The study name in the report should be **hotlinked to the report URL** (not the GitHub issue).
- Also include a link to the GitHub issue for reference.

#### For Dependencies (Blocked / Flagged):
- Items with status "On hold" are primary dependency items.
- Items with status "In progress" that have `blocker_notes` detected in their comments should also appear here.
- Describe the blocker clearly from the `blocker_notes` and `recent_comments`.
- Link to the issue so the reader can investigate further.

### Step 3: Scrape report summaries for Deployments (REQUIRED — not optional)

For each deployment that has a non-empty `report_url`, you **must** scrape the report to get summary content. Never write summaries from just the GitHub issue description — always get the actual report content first.

**Use the existing Playwright infrastructure.** Update `copilot-skills/uxr-project-tracker/scrape_reports.py`:

1. Update the `URLS` dict — map each issue URL to its report URL:
   ```python
   URLS = {
       "https://github.com/coreai-microsoft/caidr/issues/NNN": "https://hits.microsoft.com/...",
   }
   ```

2. Run the script:
   ```bash
   cd copilot-skills/uxr-project-tracker && python scrape_reports.py
   ```

3. Read `scraped_reports.json` and write summaries based on the **actual scraped report content**.

**If scraping fails** (auth expired, Figma canvas, etc.), troubleshoot it first — re-run the script, check the browser profile, try a different extraction strategy. Only fall back to the GitHub issue body as a last resort after exhausting scraping options.

**Summary rules:**
- Always summarize from the scraped report content, not the GitHub issue
- Include brief context on what the study was and why (1 sentence)
- Include key takeaways only if they are clearly stated in the scraped report — do not infer or embellish
- Verify every claim against the scraped source text before including it
- Do not mix information from GitHub issue comments into the summary as if it came from the study report
- Keep it brief — 2-3 sentences total

**Summary style**: Factual, interesting, action-oriented. Examples:
- "Five power users who constantly hit rate limits didn't revolt at token-based billing — they just want to see the meter."
- "Of 424 developers surveyed, 99.5% already use some AI coding tool — the battle isn't adoption, it's tool choice."

### Step 4: Save summaries and generate HTML

Save summaries to a JSON file mapping issue URL → summary text:
```bash
# summaries.json example:
{
  "https://github.com/coreai-microsoft/caidr/issues/123": "Short catchy summary here.",
  "https://github.com/coreai-microsoft/caidr/issues/456": "Another summary."
}
```

Then generate the HTML report:
```bash
python copilot-skills/uxr-weekly-briefing/scripts/weekly_briefing.py html --data copilot-skills/uxr-weekly-briefing/briefing_data.json --summaries copilot-skills/uxr-weekly-briefing/summaries.json --output copilot-skills/uxr-weekly-briefing/briefing.html
```

### Step 5: Open and present

Open the generated file:
```powershell
Start-Process copilot-skills/uxr-weekly-briefing/briefing.html
```

Then provide a **text summary** in the chat covering:
- How many studies are in progress (deadlines)
- How many studies completed this week (deployments)
- How many are blocked/flagged (dependencies)
- Call out any upcoming deadlines within 14 days
- Call out any new studies that started this week
- Highlight any notable completions or blockers

## Shortcut: Quick text-only briefing

If the user says "just give me the summary" or "text only", skip the HTML generation and Playwright scraping. Instead:

1. Run the fetch step
2. Read the JSON
3. Present the briefing directly in the chat as formatted text with sections for Deadlines, Deployments, and Dependencies

## Field Reference

| Field | Description |
|-------|-------------|
| Status | "In progress", "On hold", "Closed-Completed", etc. |
| Assignees | Researchers assigned to the study |
| PM | Program Manager |
| Designer | Designer assigned |
| Product | Product area (e.g., "App Service", "Playwright") |
| Team | Team (Compute, Platform, Tools, App Workload) |
| Research Phase | Design, Recruiting, Running study, Data analysis, Reporting |
| Target date | Due date for the study |
| Start date | When the study began |
| Report URL | Link to the research report/dashboard |
| Labels | GitHub issue labels |
| Main Method | Interview, Survey, Usability, etc. |
| Semester | Current semester name |
| Priority | Urgent, High, Medium, Low, P0-P2 |

## Key Definitions

- **"In progress"** = Active studies currently underway
- **"On hold"** = Studies paused, likely due to blockers/dependencies
- **"Closed-Completed"** = Finished studies with results available
- **"New"** = Created within the look-back window (default 7 days)
- **Researchers** = Assignees on the GitHub issue
- **Blocker** = Keywords detected in comments: blocked, waiting on, dependency, stuck, hold

## Important Notes

- The Playwright browser profile at `C:\Users\dagottl\AppData\Local\Temp\pw-profile` caches Microsoft SSO. If auth expires, tell the user to log in manually via Edge and retry.
- HITS pages (hits.microsoft.com) load via SPA — the scraper waits 8 seconds.
- Researcher names may have pronoun suffixes like "(SHE/HER)" — the scripts auto-strip these.
- When the user asks for a specific time range, use `--days N` to adjust the look-back window.
- If running for the first time in a session, the GraphQL fetch may take 10-20 seconds for pagination.
