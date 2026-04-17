---
name: "Marvin Research Platform — Effective Integration & Usage"
description: "How to work effectively with Marvin research data: MCP tools, URL patterns, file discovery, API quirks, and the Powerful Moments workflow that has been validated across 20+ research moments."
domain: "research-operations, interview-management, data-access"
confidence: "high"
source: "earned"
tools:
  - name: "Marvin-list_projects"
    description: "Discover all Marvin projects accessible to the user; returns project metadata including IDs, names, and descriptions."
    when: "When you need to find the project ID for a study or understand what research projects exist."
  
  - name: "Marvin-list_project_files"
    description: "List interview/survey files within a project; supports pagination with cursor/count parameters; returns file metadata including IDs, names, dates."
    when: "When you need to find the file ID for a specific interview or survey within a project."
  
  - name: "Marvin-get_file_content"
    description: "Retrieve the FULL transcript or survey content; for interviews returns the complete transcript + notes; for surveys returns paginated responses."
    when: "When you need exact quotes, full context, or when analyzing complete interviews (can be large); avoid for quick overviews."
  
  - name: "Marvin-get_file_summary"
    description: "Get an AI-generated summary of an interview/survey without full content; returns key topics, themes, highlights."
    when: "When you only need an overview or to scan what a recording contains quickly (preferred over get_file_content for speed)."
  
  - name: "Marvin-search"
    description: "Keyword-matched search across file content, transcripts, notes, and insights; returns matching excerpts with context."
    when: "When searching for specific quotes, topics, or patterns across multiple interviews; best for exact phrase matching."
  
  - name: "Marvin-ask"
    description: "AI-synthesized answer to a natural language question about research data; queries all transcripts/insights; takes 10-55 seconds and may return 'in_progress'."
    when: "When you need a synthesized insight or answer that requires reasoning across multiple interviews (not just keyword search)."
  
  - name: "Marvin-get_ask_status"
    description: "Poll the status of an in-progress ask() call; returns final answer when ready."
    when: "When ask() returned 'in_progress' — use this to retrieve the final answer without re-asking."
  
  - name: "Marvin-link_context"
    description: "Extract context from a Marvin platform URL; returns file metadata and content preview from links."
    when: "When you have a Marvin URL and need to programmatically extract its content or verify what it contains."

---

## Context

This team has learned Marvin's behavior, quirks, and best practices through real usage. The key breakthrough: **Marvin's `search` tool returns `wav_id` + `project_id` in every result — always use these directly for URL construction.**

---

## CRITICAL: The Working Search Pattern

**This is the proven approach for getting quotes with correct Marvin links.**

### Step 1: Initialize MCP session
```
POST https://mcp.heymarvin.com
Headers: Content-Type: application/json, Authorization: Bearer {token}, Accept: application/json, text/event-stream
Body: {"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"copilot","version":"1.0"}},"id":1}
```
Save the `Mcp-Session-Id` header from the response.

Then send the initialized notification:
```
POST https://mcp.heymarvin.com
Headers: Content-Type: application/json, Authorization: Bearer {token}, Mcp-Session-Id: {session_id}
Body: {"jsonrpc":"2.0","method":"notifications/initialized"}
```

### Step 2: Call search tool
```
POST https://mcp.heymarvin.com
Headers: Content-Type: application/json, Authorization: Bearer {token}, Accept: application/json, text/event-stream, Mcp-Session-Id: {session_id}
Body: {"jsonrpc":"2.0","method":"tools/call","params":{"name":"search","arguments":{"query":"your search terms","limit":10}},"id":2}
```

### Step 3: Parse results — the key fields
Response is SSE. Each result has:
```json
{
  "wav_id": 31584111,        // ← THIS IS THE FILE ID
  "wav_name": "Meeting - Name",
  "project_id": 53908,       // ← THIS IS THE PROJECT ID
  "project_name": "Project Name",
  "matches": [
    {
      "text": "quote with <em>highlights</em>",
      "speaker": "Speaker Name",
      "timestamp": { "start": "00:07:02", "end": "00:07:26" }
    }
  ]
}
```

### Step 4: Build URL directly
```
https://app.heymarvin.com/projects/{project_id}/media/{wav_id}/
```

**⚠️ NEVER use catalogs, name-matching, or file registries for URL construction. The search results already have the exact IDs you need.**

### OAuth Token
Stored at: `C:\Users\dagottl\caidr-uxr-hub\webapp-logs\.marvin-token` (raw JWT, expires April 2026)

---

## Patterns

### 1. URL Construction — The Correct Pattern

**The URL pattern for Marvin interviews is:**
```
https://app.heymarvin.com/projects/{project_id}/media/{file_id}/
```

**Why this matters:**
Early work used an incorrect pattern (`https://app.heymarvin.com/project/{project_id}` without `/projects/` and `/media/{file_id}/`). The team discovered and validated the correct pattern through testing with Mike Brzozowski. This is NOT intuitive and had to be corrected explicitly.

**Example — Agentic Ops Study interviews:**
- Quinn (Reyes Holdings): `https://app.heymarvin.com/projects/53424/media/29411718/`
- Raghu (Crossbow): `https://app.heymarvin.com/projects/53424/media/29412559/`
- Christoph (Volkswagen): `https://app.heymarvin.com/projects/53424/media/30486509/`

**Key elements:**
- Project ID: 53424 (Agentic Ops discovery research)
- File IDs: Unique per interview; can be obtained via `list_project_files` or from transcript metadata headers that include `file ID: NNNNNNN`

---

### 2. Project Structure — How Marvin Organizes Research

**Marvin projects** are containers for related research (interviews, surveys, notes, insights).

**Example project:** Agentic Ops Discovery Study (ID: 53424)
- Contains 12 interview recordings (files)
- Files are indexed by file ID (e.g., 29411718, 29412559, 29474833, …)
- Each file can have full transcripts, metadata, timestamps, linked insights
- Supports full-text search across all content

**To work with a project:**
1. Call `list_projects()` to find the project ID
2. Call `list_project_files(project_id)` to find interview/file IDs
3. Use `get_file_content()` or `get_file_summary()` to access interview data
4. Or use `search()` / `ask()` to find specific topics across all files at once

---

### 3. File ID Discovery — Two Methods

**Method A: Via list_project_files**
```
Call: Marvin-list_project_files(project_id=53424, count=50)
Returns: Metadata for all files, including file_id, name (usually participant/company name), upload date
```

This is reliable but requires pagination if a project has many files.

**Method B: From transcript metadata**
Modern transcripts include metadata headers:
```
**Source:** Marvin (file ID: 29922223, project: 53424)
```

Older transcripts use:
```
**Source:** Marvin — Agentic Ops discovery research
```

If adding this metadata, backfill the `file ID: NNNNNNN` format for consistency and discoverability.

---

### 4. Known File ID Mappings — Agentic Ops Study

**The 12 participants with confirmed file IDs:**

| Participant | Company | File ID |
|-------------|---------|---------|
| Quinn | Reyes Holdings | 29411718 |
| Raghu | Crossbow | 29412559 |
| Miklos | Wundergraph | 29474833 |
| Martin | RWE | 29503539 |
| Frederick | CVS Health | 29586817 |
| Pawan | Walmart | 29596261 |
| Christian | Swedish Export Credit | 29877339 |
| Pooran | University College Birmingham | 29922223 |
| Ruixin | DirecTV | 29926396 |
| Yiftah | C3.ai | 30422170 |
| Christoph | Volkswagen | 30486509 |
| Soumya | London Stock Exchange Group (LSEG) | 30525550 |

**Source:** `.research/agentic-ops-study/marvin-urls.md` — a single reference file that the team maintains for Marvin traceability.

**Usage:** When citing a Powerful Moment or interview finding, link to the Marvin URL using these file IDs. This makes it easy for leadership, researchers, and designers to jump directly to the source recording.

---

### 5. Marvin API Behavior — Quirks & Guardrails

#### `ask()` Tool — Latency & Polling Pattern

- **Latency:** Typically takes 10–55 seconds to return a synthesized answer
- **Return type:** May return `'in_progress'` status instead of an immediate answer
- **Polling pattern:** If `ask()` returns `'in_progress'`, use `get_ask_status(request_id)` to retrieve the final answer

**Why this matters:** Designing workflows that expect long latency and async completion. Don't block on `ask()` — consider running in parallel with other tasks.

**Example workflow:**
```
1. Call ask() with question: "What are the top deployment concerns?"
2. If response is 'in_progress', note the request_id
3. Continue with other work (search, read files, etc.)
4. Poll get_ask_status(request_id) to get the final answer
```

#### `get_file_content()` — Full Transcript Size

- **Returns:** Complete transcript + all notes for an interview
- **Size:** Can be large (10–50 KB for a 1-hour interview transcript)
- **Use case:** When you need exact quotes, line-by-line analysis, or context that summaries don't provide

**Best practice:** Use `get_file_summary()` first to scan what a recording contains. Only call `get_file_content()` if you need the full transcript.

#### `search()` vs `ask()` — Different Semantics

- **`search()`** — Keyword-matched excerpts from transcripts; returns literal matches with surrounding context
  - Best for: Finding exact quotes, scanning for specific topics, discovering what's in the database
  - Returns: Matching lines + context

- **`ask()`** — AI-synthesized answer synthesizing across all transcripts; requires reasoning
  - Best for: Answering analytical questions ("What are the top 3 themes?", "How do customers describe risk?")
  - Returns: Coherent, multi-source answer

**Use together:** Search for tactical "where is this quote?", ask for strategic "what does this mean across all interviews?"

#### Read-Only Access — No Clip Creation, No Editing

- **MCP tools are read-only.** You can view, search, summarize, and analyze research data.
- **Cannot:** Create clips, edit transcripts, upload new interviews, create tags/insights, or modify metadata
- **Workaround:** All modifications happen via the Marvin web UI (`app.heymarvin.com`). Use the MCP tools only for retrieval and analysis.

**Implication:** The team must maintain reference files (like `marvin-urls.md`) manually to document URLs, file IDs, and mappings that might be useful for future sessions.

#### `list_project_files()` — Pagination Support

- **Default:** Returns first ~20–30 files
- **Parameters:** `count` (default 20, max ~100) and `cursor` (for pagination)
- **Pattern:** If a project has >20 files, save the cursor from the first response and pass it to the next call to get the next batch

**Example:**
```
Call 1: list_project_files(project_id=53424, count=50)
  → Returns 50 files + nextCursor (if more exist)
Call 2: list_project_files(project_id=53424, count=50, cursor=nextCursor)
  → Returns next batch
```

---

### 6. The Powerful Moments Workflow — Proven Process

**Definition:** A "Powerful Moment" is a short, recent customer-voiced insight from real research that captures a meaningful tension or reframing—and is compelling enough to stand on its own as a short video for leadership.

**Criteria (from `.resops/powerful-moments.md`):**
1. **Concrete customer insight** — A specific realization, tension, blocker, or reframing
2. **Grounded in thick data** — From real interviews, with direct quotes or video clips
3. **Recent & time-bound** — Surfaced from the past 1–2 weeks
4. **Leadership-level relevance** — Quickly graspable, retellable, decision-anchoring
5. **Works as short video** — Emotionally/cognitively crisp, ~60 seconds when spoken aloud

**Team workflow:**
1. **Identify candidates** — During transcript review, flag moments that meet criteria
2. **Search Marvin** for context — Use `search()` to find exact timestamps or related quotes
3. **Link to Marvin recording** — Add the Marvin URL (using correct pattern) to the moment description
4. **Curate in reports** — Document in `reports/srea-powerful-moments.md` with participant → file ID mapping
5. **Share with leadership** — Marvin links provide provenance; leadership can jump to source

**Agentic Ops Study output:**
- **20 powerful moments** identified from 12 interviews
- **All moments linked** to Marvin recordings via correct URL pattern
- **Participant → file ID mapping** maintained in `research/agentic-ops-study/marvin-urls.md`
- **Moments cross-indexed** by theme, participant, and file ID

**Example moment:**
```
Moment #8: "In 15 Years We Did 1.7 Million Lines — In Three Months, a Million"
Participant: Yiftah (C3.ai)
File ID: 30422170
Marvin URL: https://app.heymarvin.com/projects/53424/media/30422170/
Theme: Agentic leverage at scale
Impact: Shows dramatic productivity multiplier for AI agents vs traditional dev
```

---

### 7. Discovery & Retrospective Workflows

#### Searching for a customer by name across all projects

**Scenario:** You know "PepsiCo" is in Marvin somewhere, but don't know which project.

**Approach:**
1. Call `search("PepsiCo")` — searches across all projects
2. Returns matching excerpts with project context
3. May return false positives (tangential mentions)
4. Verify the result is actually what you're looking for (e.g., PepsiCo in FinOps study ≠ PepsiCo SRE Agent trial)

**Lesson from FastPOC search:** Broad search works but requires context verification. Customer names in file titles (`list_project_files`) are more reliable than full-text search.

#### Mapping FastPOC customers to Marvin recordings

**Scenario:** You have a list of 18 FastPOC customer names; need to find Marvin recordings.

**Approach:**
1. Search for each customer name in `list_project_files` (project 37275, SRE Agent Field Trial, is the hub)
2. Expand search to all projects if not found in primary project
3. Use variations (e.g., "Caixa Geral" and "CGD")
4. Check file names (most reliable signal) before content search
5. Document findings in a reference file (e.g., `research/fastpoc/marvin-recordings.md`)

**Learning:** Some completed FastPOCs have no Marvin recordings (may have been recorded in Teams or not recorded). Accept gaps gracefully and document them.

---

## Examples

### Example 1: Finding a quote from a specific interview

**Goal:** Locate the exact quote from Christoph (Volkswagen) about cost overruns.

**Process:**
```
1. Look up Christoph's file ID from known mappings: 30486509
2. Call: Marvin-get_file_content(project_id=53424, file_id=30486509)
3. Search the transcript for "cost" or "overrun"
4. Extract quote + timestamp (if available)
5. Link back to Marvin: https://app.heymarvin.com/projects/53424/media/30486509/
6. Use this in reports or presentations
```

**Result:** Direct attribution + provenance; leadership can verify by jumping to the recording.

---

### Example 2: Identifying a theme across all Agentic Ops interviews

**Goal:** "What do customers say about risk and accountability with agentic systems?"

**Process:**
```
1. Call: Marvin-ask(question="How do customers describe concerns about risk, accountability, and agentic systems?", project_ids=[53424])
2. Wait 10–55 seconds (or poll if in_progress)
3. Receive synthesized answer with cross-interview patterns
4. Follow up with Marvin-search("accountability", "escalation", "liability") to find specific quotes
5. Combine into a findings section for a report
```

**Result:** Strategic insight + tactical support (quotes + URLs).

---

### Example 3: Maintaining a reference file for discoverability

**File:** `research/agentic-ops-study/marvin-urls.md`

**Purpose:** Single source of truth for participant ↔ file ID mappings.

**Content:**
- Interview recording URLs table (all 12 participants with file IDs and correct Marvin URLs)
- Powerful Moments ↔ participant mapping (so leadership can jump to source recordings)
- Notes on why some transcripts have file IDs in headers and others don't

**Maintenance:** Update this file whenever a new file ID is discovered or a powerful moment is added. It's the team's institutional memory for Marvin traceability.

---

### Example 4: Using search to find context for a Powerful Moment

**Scenario:** Powerful Moment #7 is "We don't have a tracking system" from Frederick at CVS Health. Leadership asks for context.

**Process:**
```
1. Look up Frederick's file ID: 29586817
2. Call: Marvin-search("tracking system", project_id=53424)
3. Get back excerpts from Frederick's interview with surrounding context
4. Assemble into a 1-2 minute excerpt that explains the moment
5. Link to full recording: https://app.heymarvin.com/projects/53424/media/29586817/
6. Distribute to leadership
```

**Result:** Leadership understands the moment in context without watching the full 1-hour interview.

---

## Anti-Patterns

### ❌ Anti-Pattern 1: Using the wrong URL format

**Incorrect:**
```
https://app.heymarvin.com/project/53424  (missing /projects/ and /media/{file_id}/)
```

**Correct:**
```
https://app.heymarvin.com/projects/53424/media/29411718/
```

**Why it matters:** The incorrect pattern was discovered and corrected through validation. Always use the full, correct pattern with `/projects/`, `/media/`, and the file ID. Test URLs by pasting them into a browser and verifying they load the recording.

---

### ❌ Anti-Pattern 2: Trying to create clips or edit transcripts via MCP tools

**What happens:**
- You call `get_file_content()`, get the transcript, edit it, and try to upload it back
- **Result:** MCP tools are read-only. There is no `update_file_content()` or `create_clip()` method.

**What to do instead:**
- All modifications (transcript edits, clip creation, tag/insight management) happen in the **Marvin web UI** at `app.heymarvin.com`
- Use MCP tools only for retrieval and analysis

---

### ❌ Anti-Pattern 3: Confusing Marvin issues with Qualtrics CSV issues

**Scenario:** Survey data shows blank rows interleaved; you assume it's a Marvin data quality issue.

**Reality:** The blank-row interleaving is a **Qualtrics CSV export quirk**, not a Marvin problem. Marvin stores interview/survey data; Qualtrics is a separate survey platform. Don't conflate the two.

**Resolution:** Handle blank rows in CSV parsing; don't blame Marvin for Qualtrics export behavior.

---

### ❌ Anti-Pattern 4: Calling `get_file_content()` when you only need a quick overview

**Inefficient:**
```
Marvin-get_file_content(file_id=30486509)  # Returns 50 KB transcript
```

**Better:**
```
Marvin-get_file_summary(file_id=30486509)  # Returns 2-3 paragraph overview + key topics
```

**Why it matters:** Summary is fast; full content can be slow or overwhelming. Use `get_file_summary()` to scan, then call `get_file_content()` only if you need exact quotes or line-by-line analysis.

---

### ❌ Anti-Pattern 5: Assuming all completed FastPOCs have Marvin recordings

**Reality:** FastPOC project board status "Completed" ≠ "Marvin recording exists."

**Causes:**
- Meetings may not have been recorded
- Recordings may be stored in Teams, SharePoint, or elsewhere
- Recording names may not match customer names (hard to find via search)

**Solution:** Accept gaps gracefully. Document which customers have recordings and which don't. Don't assume 100% coverage. If recordings are critical, reach out to FastPOC team leads directly.

---

### ❌ Anti-Pattern 6: Not maintaining reference files like marvin-urls.md

**Problem:** File IDs and URLs get scattered across emails, notes, and different documents. Next quarter, you can't find the file ID for Quinn's interview.

**Solution:** Maintain a **single source of truth** file (e.g., `research/agentic-ops-study/marvin-urls.md`) with all participant ↔ file ID mappings. Update it once per study. Link to it from related documents.

**Benefit:** Institutional memory; discoverability; lower onboarding friction for new researchers.

---

## Confidence & Reasoning

**Confidence: HIGH**

This skill captures well-established team knowledge from:
- **4+ sessions of direct MCP usage** on Agentic Ops study (project 53424)
- **12 file ID mappings** successfully recovered and validated
- **20 powerful moments** successfully linked to Marvin recordings using the correct URL pattern
- **1 multi-project search** (FastPOC customers) with documented findings and gaps
- **Explicit validation** of URL patterns with Mike Brzozowski
- **Error corrections** (URL format, understanding of read-only MCP, Qualtrics confusion) that have been applied and tested

The team has moved from "no data access" (early 2026-03-05 scans) to "confident, proven workflows" (2026-04-01+) that work reliably.

---

## Source

**Earned** — through iterative discovery, validation, and correction across multiple real research workflows. Not inferred from documentation; learned by doing.

**Key sessions:**
- 2026-03-27: Marvin URL extraction and correction (initial Guinan scan found empty results; manual recovery of file IDs from transcripts)
- 2026-03-27: File ID mapping validation with Mike
- 2026-03-27 onwards: Powerful Moments workflow validation (20 moments linked successfully)
- 2026-04-01: FastPOC customer recording search (documented findings + gaps)

---

## Related Team Decisions

- `.squad/decisions.md` — "Marvin MCP Integration" (governance decision on data access)
- `.squad/decisions/inbox/guinan-fastpoc-marvin.md` — FastPOC recording gap resolution strategy
- `.research/agentic-ops-study/marvin-urls.md` — Reference file for participant ↔ file ID mappings
- `.reports/srea-powerful-moments.md` — Output of Powerful Moments workflow with Marvin links
- `.resops/powerful-moments.md` — Definition and criteria for Powerful Moments (Marvin's primary use case for leadership communication)

---

## Key Takeaways for Future Sessions

1. **Always test URL patterns** — The correct format is `https://app.heymarvin.com/projects/{id}/media/{file_id}/`. Verify by pasting into a browser.

2. **Use get_file_summary() first** — It's fast and tells you what a recording contains. Only call `get_file_content()` if you need exact quotes.

3. **Maintain reference files** — Keep a single source of truth (e.g., `marvin-urls.md`) with file ID mappings. Update it as you discover new IDs.

4. **Powerful Moments ↔ Marvin** — This is the highest-impact use case. Identify moments that meet criteria, link them to Marvin recordings, and share with leadership. Marvin URLs provide instant provenance.

5. **MCP tools are read-only** — All edits/uploads happen via the web UI. Use MCP only for retrieval and analysis.

6. **Accept gaps gracefully** — Not every study or project has 100% Marvin coverage. Document what's available and what isn't.

7. **Beware of cross-platform confusion** — Marvin stores interviews; Qualtrics is survey data. Don't assume issues with one are caused by the other.

