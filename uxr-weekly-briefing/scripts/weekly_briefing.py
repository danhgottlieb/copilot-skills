#!/usr/bin/env python3
"""
UXR Weekly Briefing Data Fetcher & Report Generator

Fetches data from the UXR Team Projects board (coreai-microsoft, project #40)
and produces a weekly 3D briefing (Deadlines, Deployments, Dependencies).

Sub-commands
------------
  fetch   Fetch project items + recent comments → JSON
  html    Generate styled HTML from the JSON (+ optional summaries)

Examples
--------
  python weekly_briefing.py fetch --days 7 --output briefing_data.json
  python weekly_briefing.py html --data briefing_data.json --summaries summaries.json --output briefing.html
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ORG = "coreai-microsoft"
PROJECT_NUMBER = 40

BLOCKER_KEYWORDS = [
    "blocked", "blocker", "blocking", "waiting on", "waiting for",
    "dependency", "dependent", "hold", "on hold", "stuck", "stalled",
    "can't proceed", "cannot proceed", "need", "requires",
]

GRAPHQL_QUERY = """
{
  organization(login: "%s") {
    projectV2(number: %d) {
      items(first: 100%s) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          fieldValues(first: 35) {
            nodes {
              ... on ProjectV2ItemFieldTextValue {
                text
                field { ... on ProjectV2Field { name } }
              }
              ... on ProjectV2ItemFieldDateValue {
                date
                field { ... on ProjectV2Field { name } }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2SingleSelectField { name } }
              }
              ... on ProjectV2ItemFieldNumberValue {
                number
                field { ... on ProjectV2Field { name } }
              }
              ... on ProjectV2ItemFieldUserValue {
                users(first: 10) { nodes { login name } }
                field { ... on ProjectV2Field { name } }
              }
              ... on ProjectV2ItemFieldLabelValue {
                labels(first: 10) { nodes { name } }
                field { ... on ProjectV2Field { name } }
              }
              ... on ProjectV2ItemFieldRepositoryValue {
                repository { name nameWithOwner }
                field { ... on ProjectV2Field { name } }
              }
            }
          }
          content {
            ... on Issue {
              title
              url
              state
              closedAt
              createdAt
              updatedAt
              number
              body
              assignees(first: 10) { nodes { login name } }
              labels(first: 15) { nodes { name } }
              repository { name nameWithOwner }
            }
            ... on DraftIssue {
              title
              body
              createdAt
              updatedAt
            }
          }
        }
      }
    }
  }
}
"""

# ---------------------------------------------------------------------------
# GraphQL helpers
# ---------------------------------------------------------------------------

def run_graphql(cursor=None, retries=3):
    import time
    after = f', after: "{cursor}"' if cursor else ""
    query = GRAPHQL_QUERY % (ORG, PROJECT_NUMBER, after)
    for attempt in range(retries):
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        if attempt < retries - 1:
            wait = 2 ** (attempt + 1)
            print(f"  API error (attempt {attempt+1}/{retries}), retrying in {wait}s…", file=sys.stderr)
            time.sleep(wait)
    print(f"Error querying GitHub API after {retries} attempts: {result.stderr}", file=sys.stderr)
    sys.exit(1)


def parse_field_value(node):
    if not node:
        return None, None
    field_info = node.get("field", {})
    field_name = field_info.get("name", "")
    if not field_name:
        return None, None
    if "name" in node and "field" in node and len(node) == 2:
        return field_name, node["name"]
    if "text" in node:
        return field_name, node["text"]
    if "date" in node:
        return field_name, node["date"]
    if "number" in node:
        return field_name, node["number"]
    if "users" in node:
        users = node["users"]["nodes"]
        return field_name, [{"login": u["login"], "name": u.get("name", "")} for u in users]
    if "labels" in node:
        labels = node["labels"]["nodes"]
        return field_name, [l["name"] for l in labels]
    if "repository" in node:
        return field_name, node["repository"].get("nameWithOwner", node["repository"].get("name", ""))
    return field_name, None


def fetch_all_items():
    all_items = []
    cursor = None
    page = 0
    while True:
        page += 1
        if page > 1:
            print(f"  Fetching page {page}…", file=sys.stderr)
        data = run_graphql(cursor)
        items_data = data["data"]["organization"]["projectV2"]["items"]
        nodes = items_data["nodes"]
        for node in nodes:
            item = {}
            for fv in node.get("fieldValues", {}).get("nodes", []):
                fname, fval = parse_field_value(fv)
                if fname:
                    item[fname] = fval
            content = node.get("content", {})
            if content:
                item["_url"] = content.get("url", "")
                item["_state"] = content.get("state", "")
                item["_closedAt"] = content.get("closedAt", "")
                item["_createdAt"] = content.get("createdAt", "")
                item["_updatedAt"] = content.get("updatedAt", "")
                item["_number"] = content.get("number", "")
                item["_body"] = content.get("body", "")
                item["_repo"] = (
                    content.get("repository", {}).get("nameWithOwner", "")
                    if content.get("repository") else ""
                )
                if "assignees" in content:
                    assignees = content["assignees"]["nodes"]
                    if assignees and "Assignees" not in item:
                        item["Assignees"] = [
                            {"login": a["login"], "name": a.get("name", "")} for a in assignees
                        ]
                if "labels" in content:
                    labels = content["labels"]["nodes"]
                    if labels and "Labels" not in item:
                        item["Labels"] = [l["name"] for l in labels]
            all_items.append(item)
        page_info = items_data["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
    return all_items

# ---------------------------------------------------------------------------
# Comment / event helpers
# ---------------------------------------------------------------------------

def parse_issue_url(url):
    """Extract (owner, repo, number) from a GitHub issue URL."""
    if not url:
        return None, None, None
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)", url)
    if m:
        return m.group(1), m.group(2), int(m.group(3))
    return None, None, None


def fetch_issue_comments(owner, repo, number, since_date):
    """Fetch comments created since *since_date* for a single issue."""
    since_str = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    result = subprocess.run(
        [
            "gh", "api",
            f"repos/{owner}/{repo}/issues/{number}/comments",
            "-q",
            f'[.[] | select(.created_at >= "{since_str}") '
            f'| {{author: .user.login, body: .body, created_at: .created_at}}]',
        ],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
    return []


def fetch_issue_events(owner, repo, number, since_date):
    """Fetch label / status change events since *since_date*."""
    result = subprocess.run(
        [
            "gh", "api",
            f"repos/{owner}/{repo}/issues/{number}/events",
            "--paginate",
        ],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        return []
    try:
        events = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    cutoff = since_date.isoformat()
    relevant = []
    for ev in events:
        created = ev.get("created_at", "")
        if created >= cutoff:
            relevant.append({
                "event": ev.get("event", ""),
                "label": ev.get("label", {}).get("name", "") if ev.get("label") else "",
                "actor": ev.get("actor", {}).get("login", "") if ev.get("actor") else "",
                "created_at": created,
            })
    return relevant

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_assignees(assignees):
    if not assignees or not isinstance(assignees, list):
        return ""
    names = []
    for a in assignees:
        name = a.get("name") or a.get("login") or ""
        name = re.sub(r"\s*\([A-Z]+/[A-Z]+\)\s*$", "", name).strip()
        if name:
            names.append(name)
    return ", ".join(names)


def format_labels(labels):
    if not labels or not isinstance(labels, list):
        return ""
    return ", ".join(labels)


def format_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return date_str


def has_blocker_language(text):
    """Return True if *text* contains blocker-related keywords."""
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in BLOCKER_KEYWORDS)


def extract_blocker_sentences(text):
    """Pull sentences that mention blocking keywords."""
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if has_blocker_language(s)]

# ---------------------------------------------------------------------------
# FETCH sub-command
# ---------------------------------------------------------------------------

def cmd_fetch(args):
    days = args.days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    print(f"Fetching UXR project items (cutoff: {cutoff_str})…", file=sys.stderr)

    all_items = fetch_all_items()
    print(f"  Total items on board: {len(all_items)}", file=sys.stderr)

    deadlines = []   # In progress with recent activity
    deployments = []  # Closed-Completed in period
    dependencies = []  # On hold / blocked
    stakeholders = {"researchers": set(), "pms": set(), "designers": set()}

    for item in all_items:
        status = item.get("Status", "")
        url = item.get("_url", "")
        owner, repo, number = parse_issue_url(url)

        # Collect stakeholders from all items with status
        researcher = format_assignees(item.get("Assignees", []))
        pm = item.get("PM", "")
        designer = item.get("Designer", "")
        if researcher:
            for r in researcher.split(", "):
                stakeholders["researchers"].add(r)
        if pm:
            stakeholders["pms"].add(pm)
        if designer:
            stakeholders["designers"].add(designer)

        # ------- DEPLOYMENTS: Closed-Completed in period -------
        if status == "Closed-Completed":
            closed_at = item.get("_closedAt", "")
            if closed_at:
                try:
                    closed_dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
                    if closed_dt >= cutoff:
                        entry = _build_item_record(item)
                        deployments.append(entry)
                except (ValueError, TypeError):
                    pass
            continue

        # ------- DEADLINES: In progress with recent activity -------
        if status == "In progress":
            updated_at = item.get("_updatedAt", "")
            created_at = item.get("_createdAt", "")
            is_new = False
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    is_new = created_dt >= cutoff
                except (ValueError, TypeError):
                    pass

            # Fetch recent comments
            comments = []
            events = []
            if owner and repo and number:
                print(f"  Fetching comments for {repo}#{number}…", file=sys.stderr)
                comments = fetch_issue_comments(owner, repo, number, cutoff)
                events = fetch_issue_events(owner, repo, number, cutoff)

            entry = _build_item_record(item)
            entry["is_new"] = is_new
            entry["recent_comments"] = comments
            entry["recent_events"] = events
            deadlines.append(entry)
            continue

        # ------- DEPENDENCIES: On hold -------
        if status == "On hold":
            comments = []
            events = []
            if owner and repo and number:
                print(f"  Fetching comments for on-hold {repo}#{number}…", file=sys.stderr)
                comments = fetch_issue_comments(owner, repo, number, cutoff)
                events = fetch_issue_events(owner, repo, number, cutoff)

            # Find blocker language in body + comments
            blocker_notes = []
            body = item.get("_body", "")
            blocker_notes.extend(extract_blocker_sentences(body))
            for c in comments:
                blocker_notes.extend(extract_blocker_sentences(c.get("body", "")))

            entry = _build_item_record(item)
            entry["recent_comments"] = comments
            entry["recent_events"] = events
            entry["blocker_notes"] = blocker_notes
            dependencies.append(entry)
            continue

    # Also check In-progress items for blocker language in recent comments
    for d in deadlines:
        blocker_notes = []
        for c in d.get("recent_comments", []):
            blocker_notes.extend(extract_blocker_sentences(c.get("body", "")))
        if blocker_notes:
            dep_entry = dict(d)
            dep_entry["blocker_notes"] = blocker_notes
            dep_entry["status"] = "In progress (blocker noted)"
            dependencies.append(dep_entry)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "cutoff_date": cutoff_str,
        "deadlines": deadlines,
        "deployments": deployments,
        "dependencies": dependencies,
        "stakeholders": {
            "researchers": sorted(stakeholders["researchers"]),
            "pms": sorted(stakeholders["pms"]),
            "designers": sorted(stakeholders["designers"]),
        },
        "counts": {
            "deadlines": len(deadlines),
            "deployments": len(deployments),
            "dependencies": len(dependencies),
        },
    }

    output = json.dumps(result, indent=2, default=str, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nSaved briefing data to {args.output}", file=sys.stderr)
        print(f"  Deadlines (In progress):  {len(deadlines)}", file=sys.stderr)
        print(f"  Deployments (Completed):  {len(deployments)}", file=sys.stderr)
        print(f"  Dependencies (Blocked):   {len(dependencies)}", file=sys.stderr)
    else:
        print(output)


def _build_item_record(item):
    """Build a standardized record dict from a project item."""
    return {
        "title": item.get("Title", ""),
        "url": item.get("_url", ""),
        "status": item.get("Status", ""),
        "researcher": format_assignees(item.get("Assignees", [])),
        "labels": item.get("Labels", []) if isinstance(item.get("Labels"), list) else [],
        "product": item.get("Product", ""),
        "team": item.get("Team", ""),
        "research_phase": item.get("Research Phase", ""),
        "report_url": item.get("Report URL", ""),
        "target_date": item.get("Target date", ""),
        "start_date": item.get("Start date", ""),
        "pm": item.get("PM", ""),
        "designer": item.get("Designer", ""),
        "semester": item.get("Semester", ""),
        "priority": item.get("Priority", ""),
        "hpf_stage": item.get("HPF Stage", ""),
        "lifecycle_phase": item.get("Lifecycle Phase", ""),
        "main_method": item.get("Main Method", ""),
        "body": item.get("_body", ""),
        "created_at": format_date(item.get("_createdAt", "")),
        "updated_at": format_date(item.get("_updatedAt", "")),
        "closed_at": format_date(item.get("_closedAt", "")),
        "number": item.get("_number", ""),
        "repo": item.get("_repo", ""),
    }

# ---------------------------------------------------------------------------
# HTML sub-command
# ---------------------------------------------------------------------------

def h(text):
    """HTML-escape."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def label_pills(labels):
    if not labels:
        return ""
    return " ".join(f'<span class="label">{h(l)}</span>' for l in labels)


def cmd_html(args):
    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    summaries = {}
    if args.summaries:
        with open(args.summaries, "r", encoding="utf-8") as f:
            summaries = json.load(f)

    deadlines = data.get("deadlines", [])
    deployments = data.get("deployments", [])
    dependencies = data.get("dependencies", [])
    stakeholders = data.get("stakeholders", {})
    cutoff = data.get("cutoff_date", "")
    generated = data.get("generated_at", "")[:10]

    # --- Build sections ---
    deadlines_html = _render_deadlines(deadlines, summaries)
    deployments_html = _render_deployments(deployments, summaries)
    dependencies_html = _render_dependencies(dependencies, summaries)
    stakeholders_html = _render_stakeholders(stakeholders)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UXR Weekly Briefing — 3D Report</title>
<style>
  :root {{
    --bg: #f6f8fa; --card: #ffffff; --border: #d0d7de;
    --text: #1f2328; --muted: #656d76; --link: #0969da;
    --blue: #0969da; --blue-bg: #ddf4ff; --blue-border: #54aeff;
    --green: #1a7f37; --green-bg: #dafbe1; --green-border: #4ac26b;
    --orange: #bc4c00; --orange-bg: #fff8c5; --orange-border: #d4a72c;
    --purple: #8250df; --purple-bg: #fbefff; --purple-border: #c297ff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }}

  /* Header */
  .header {{
    background: linear-gradient(135deg, #24292f 0%, #0d1117 100%);
    color: #fff; padding: 2rem 0; margin-bottom: 2rem; border-radius: 12px;
  }}
  .header .container {{ padding: 0 2rem; }}
  .header h1 {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 0.25rem; }}
  .header .subtitle {{ color: #8b949e; font-size: 0.95rem; }}
  .header .counts {{
    display: flex; gap: 1.5rem; margin-top: 1rem; flex-wrap: wrap;
  }}
  .header .count-badge {{
    background: rgba(255,255,255,0.1); border-radius: 20px;
    padding: 0.35rem 1rem; font-size: 0.85rem; font-weight: 600;
  }}
  .count-badge.blue {{ color: #79c0ff; }}
  .count-badge.green {{ color: #7ee787; }}
  .count-badge.orange {{ color: #f0883e; }}

  /* Nav */
  .nav {{
    display: flex; gap: 0.75rem; margin-bottom: 2rem;
    border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; flex-wrap: wrap;
  }}
  .nav a {{
    text-decoration: none; padding: 0.4rem 1rem; border-radius: 20px;
    font-size: 0.85rem; font-weight: 600; transition: all 0.15s;
  }}
  .nav a:hover {{ opacity: 0.85; }}
  .nav a.blue {{ background: var(--blue-bg); color: var(--blue); }}
  .nav a.green {{ background: var(--green-bg); color: var(--green); }}
  .nav a.orange {{ background: var(--orange-bg); color: var(--orange); }}
  .nav a.purple {{ background: var(--purple-bg); color: var(--purple); }}

  /* Sections */
  .section {{ margin-bottom: 2.5rem; }}
  .section-header {{
    display: flex; align-items: center; gap: 0.6rem;
    margin-bottom: 1rem; padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--border);
  }}
  .section-header h2 {{ font-size: 1.3rem; font-weight: 700; }}
  .section-header .badge {{
    font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem;
    border-radius: 12px; color: #fff;
  }}
  .badge-blue {{ background: var(--blue); }}
  .badge-green {{ background: var(--green); }}
  .badge-orange {{ background: var(--orange); }}

  /* Cards */
  .card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; padding: 1.25rem; margin-bottom: 0.75rem;
    transition: box-shadow 0.15s;
  }}
  .card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .card-header {{
    display: flex; justify-content: space-between; align-items: flex-start;
    flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.6rem;
  }}
  .card-title {{
    font-size: 1rem; font-weight: 600;
  }}
  .card-title a {{ color: var(--link); text-decoration: none; }}
  .card-title a:hover {{ text-decoration: underline; }}
  .card-meta {{
    display: flex; flex-wrap: wrap; gap: 0.75rem; font-size: 0.8rem; color: var(--muted);
    margin-bottom: 0.5rem;
  }}
  .card-meta span {{ display: inline-flex; align-items: center; gap: 0.25rem; }}
  .card-summary {{
    font-size: 0.85rem; line-height: 1.5; color: var(--text); margin-top: 0.5rem;
  }}
  .card-activity {{
    margin-top: 0.6rem; padding-top: 0.6rem; border-top: 1px solid #eee;
  }}
  .card-activity h4 {{
    font-size: 0.78rem; font-weight: 600; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 0.3rem;
  }}
  .card-activity .comment {{
    font-size: 0.8rem; color: var(--text); margin-bottom: 0.35rem;
    padding-left: 0.75rem; border-left: 2px solid var(--border);
  }}
  .card-activity .comment .author {{ font-weight: 600; color: var(--muted); }}

  /* Labels */
  .label {{
    display: inline-block; font-size: 0.7rem; font-weight: 600;
    padding: 0.15rem 0.5rem; border-radius: 12px;
    background: #ddf4ff; color: #0969da; margin-right: 0.25rem;
  }}

  /* Deadline callout */
  .deadline-callout {{
    background: #fff8c5; border: 1px solid #d4a72c; border-radius: 6px;
    padding: 0.4rem 0.75rem; font-size: 0.82rem; font-weight: 600;
    color: #6a4e00; display: inline-block; margin-top: 0.4rem;
  }}

  /* Blocker callout */
  .blocker-callout {{
    background: #ffebe9; border: 1px solid #ff7b72; border-radius: 6px;
    padding: 0.6rem 0.9rem; font-size: 0.82rem; color: #82071e; margin-top: 0.5rem;
  }}
  .blocker-callout strong {{ color: #a40e26; }}

  /* Stakeholder table */
  .stakeholder-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
  }}
  .stakeholder-card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; padding: 1rem;
  }}
  .stakeholder-card h4 {{
    font-size: 0.82rem; font-weight: 700; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 0.5rem;
  }}
  .stakeholder-card ul {{ list-style: none; }}
  .stakeholder-card li {{ font-size: 0.85rem; padding: 0.15rem 0; }}

  /* New badge */
  .new-badge {{
    background: #1a7f37; color: #fff; font-size: 0.65rem; font-weight: 700;
    padding: 0.15rem 0.45rem; border-radius: 8px; margin-left: 0.4rem;
    vertical-align: middle;
  }}

  /* Phase badge */
  .phase-badge {{
    background: var(--purple-bg); color: var(--purple); font-size: 0.7rem;
    font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 12px;
  }}

  .empty-state {{
    text-align: center; padding: 2rem; color: var(--muted); font-style: italic;
  }}

  /* Footer */
  .footer {{
    text-align: center; padding: 1.5rem; color: var(--muted);
    font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 2rem;
  }}
  .footer a {{ color: var(--link); text-decoration: none; }}
</style>
</head>
<body>

<div class="header">
  <div class="container">
    <h1>📊 UXR Weekly Briefing</h1>
    <div class="subtitle">3D Report: Deadlines · Deployments · Dependencies — Since {h(cutoff)} — Generated {h(generated)}</div>
    <div class="counts">
      <span class="count-badge blue">📅 {len(deadlines)} In Progress</span>
      <span class="count-badge green">🚀 {len(deployments)} Completed</span>
      <span class="count-badge orange">⚠️ {len(dependencies)} Blocked / Flagged</span>
    </div>
  </div>
</div>

<div class="container">
  <nav class="nav">
    <a href="#deadlines" class="blue">📅 Deadlines</a>
    <a href="#deployments" class="green">🚀 Deployments</a>
    <a href="#dependencies" class="orange">⚠️ Dependencies</a>
    <a href="#stakeholders" class="purple">👥 Stakeholders</a>
  </nav>

  {deadlines_html}
  {deployments_html}
  {dependencies_html}
  {stakeholders_html}
</div>

<div class="footer">
  Data from <a href="https://github.com/orgs/coreai-microsoft/projects/40/views/1">UXR Team Projects</a> · Generated by UXR Weekly Briefing Skill
</div>

</body>
</html>"""

    out_path = args.output or "briefing.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved HTML briefing to {out_path}", file=sys.stderr)
    print(f"  Deadlines:    {len(deadlines)}", file=sys.stderr)
    print(f"  Deployments:  {len(deployments)}", file=sys.stderr)
    print(f"  Dependencies: {len(dependencies)}", file=sys.stderr)


def _render_deadlines(items, summaries):
    if not items:
        return '<section id="deadlines" class="section"><div class="section-header"><h2>📅 Deadlines</h2></div><div class="empty-state">No in-progress studies found.</div></section>'

    cards = []
    for item in items:
        title = item["title"]
        url = item["url"]
        researcher = item["researcher"]
        labels = item.get("labels", [])
        phase = item.get("research_phase", "")
        product = item.get("product", "")
        target = item.get("target_date", "")
        start = item.get("start_date", "")
        is_new = item.get("is_new", False)
        pm = item.get("pm", "")
        designer = item.get("designer", "")
        method = item.get("main_method", "")
        comments = item.get("recent_comments", [])
        summary = summaries.get(url, "")

        new_tag = '<span class="new-badge">NEW</span>' if is_new else ""
        title_link = f'<a href="{h(url)}">{h(title)}</a>{new_tag}' if url else h(title)

        meta_parts = []
        if researcher:
            meta_parts.append(f'<span>👤 {h(researcher)}</span>')
        if phase:
            meta_parts.append(f'<span class="phase-badge">{h(phase)}</span>')
        if product:
            meta_parts.append(f'<span>📦 {h(product)}</span>')
        if method:
            meta_parts.append(f'<span>🔬 {h(method)}</span>')
        if pm:
            meta_parts.append(f'<span>PM: {h(pm)}</span>')
        if designer:
            meta_parts.append(f'<span>🎨 {h(designer)}</span>')

        deadline_html = ""
        if target:
            deadline_html = f'<div class="deadline-callout">🎯 Target date: {h(target)}</div>'
        elif start:
            deadline_html = f'<div class="deadline-callout">📅 Started: {h(start)}</div>'

        activity_html = ""
        if comments:
            comment_items = []
            for c in comments[:5]:
                author = c.get("author", "")
                body = c.get("body", "")
                # Truncate long comments
                if len(body) > 300:
                    body = body[:300] + "…"
                date = c.get("created_at", "")[:10]
                comment_items.append(
                    f'<div class="comment"><span class="author">@{h(author)}</span> ({h(date)}): {h(body)}</div>'
                )
            activity_html = f"""<div class="card-activity">
              <h4>Recent Activity (Last 7 Days)</h4>
              {"".join(comment_items)}
            </div>"""

        summary_html = f'<div class="card-summary">{h(summary)}</div>' if summary else ""

        cards.append(f"""<div class="card">
          <div class="card-header">
            <div class="card-title">{title_link}</div>
            <div>{label_pills(labels)}</div>
          </div>
          <div class="card-meta">{"".join(meta_parts)}</div>
          {deadline_html}
          {summary_html}
          {activity_html}
        </div>""")

    return f"""<section id="deadlines" class="section">
      <div class="section-header">
        <h2>📅 Deadlines</h2>
        <span class="badge badge-blue">{len(items)} studies</span>
      </div>
      {"".join(cards)}
    </section>"""


def _render_deployments(items, summaries):
    if not items:
        return '<section id="deployments" class="section"><div class="section-header"><h2>🚀 Deployments</h2></div><div class="empty-state">No recently completed studies.</div></section>'

    cards = []
    for item in items:
        title = item["title"]
        url = item["url"]
        report_url = item.get("report_url", "")
        researcher = item["researcher"]
        labels = item.get("labels", [])
        closed = item.get("closed_at", "")
        pm = item.get("pm", "")
        designer = item.get("designer", "")
        product = item.get("product", "")
        method = item.get("main_method", "")
        summary = summaries.get(url, "")

        # Hotlink title to report URL if available, otherwise to issue
        link_target = report_url if report_url else url
        title_link = f'<a href="{h(link_target)}">{h(title)}</a>' if link_target else h(title)

        meta_parts = []
        if researcher:
            meta_parts.append(f'<span>👤 {h(researcher)}</span>')
        if closed:
            meta_parts.append(f'<span>✅ Closed: {h(closed)}</span>')
        if product:
            meta_parts.append(f'<span>📦 {h(product)}</span>')
        if method:
            meta_parts.append(f'<span>🔬 {h(method)}</span>')
        if pm:
            meta_parts.append(f'<span>PM: {h(pm)}</span>')
        if designer:
            meta_parts.append(f'<span>🎨 {h(designer)}</span>')

        links_html = ""
        if url and report_url:
            links_html = f'<div style="font-size:0.78rem; margin-top:0.3rem; color:var(--muted);">📎 <a href="{h(url)}">GitHub Issue</a> · <a href="{h(report_url)}">Full Report</a></div>'
        elif url:
            links_html = f'<div style="font-size:0.78rem; margin-top:0.3rem; color:var(--muted);">📎 <a href="{h(url)}">GitHub Issue</a></div>'

        summary_html = f'<div class="card-summary">{h(summary)}</div>' if summary else ""

        cards.append(f"""<div class="card" style="border-left: 3px solid var(--green);">
          <div class="card-header">
            <div class="card-title">{title_link}</div>
            <div>{label_pills(labels)}</div>
          </div>
          <div class="card-meta">{"".join(meta_parts)}</div>
          {summary_html}
          {links_html}
        </div>""")

    return f"""<section id="deployments" class="section">
      <div class="section-header">
        <h2>🚀 Deployments</h2>
        <span class="badge badge-green">{len(items)} completed</span>
      </div>
      {"".join(cards)}
    </section>"""


def _render_dependencies(items, summaries):
    if not items:
        return '<section id="dependencies" class="section"><div class="section-header"><h2>⚠️ Dependencies</h2></div><div class="empty-state">No blocked or flagged studies — all clear! 🎉</div></section>'

    cards = []
    for item in items:
        title = item["title"]
        url = item["url"]
        researcher = item["researcher"]
        labels = item.get("labels", [])
        status = item.get("status", "")
        pm = item.get("pm", "")
        product = item.get("product", "")
        blocker_notes = item.get("blocker_notes", [])
        comments = item.get("recent_comments", [])

        title_link = f'<a href="{h(url)}">{h(title)}</a>' if url else h(title)

        meta_parts = []
        if researcher:
            meta_parts.append(f'<span>👤 {h(researcher)}</span>')
        if status:
            meta_parts.append(f'<span>⏸️ {h(status)}</span>')
        if product:
            meta_parts.append(f'<span>📦 {h(product)}</span>')
        if pm:
            meta_parts.append(f'<span>PM: {h(pm)}</span>')

        blocker_html = ""
        if blocker_notes:
            notes = "<br>".join(h(n) for n in blocker_notes[:5])
            blocker_html = f'<div class="blocker-callout"><strong>🚫 Blocker Details:</strong><br>{notes}</div>'

        activity_html = ""
        if comments:
            comment_items = []
            for c in comments[:3]:
                author = c.get("author", "")
                body = c.get("body", "")
                if len(body) > 250:
                    body = body[:250] + "…"
                date = c.get("created_at", "")[:10]
                comment_items.append(
                    f'<div class="comment"><span class="author">@{h(author)}</span> ({h(date)}): {h(body)}</div>'
                )
            activity_html = f"""<div class="card-activity">
              <h4>Recent Comments</h4>
              {"".join(comment_items)}
            </div>"""

        cards.append(f"""<div class="card" style="border-left: 3px solid var(--orange);">
          <div class="card-header">
            <div class="card-title">{title_link}</div>
            <div>{label_pills(labels)}</div>
          </div>
          <div class="card-meta">{"".join(meta_parts)}</div>
          {blocker_html}
          {activity_html}
        </div>""")

    return f"""<section id="dependencies" class="section">
      <div class="section-header">
        <h2>⚠️ Dependencies</h2>
        <span class="badge badge-orange">{len(items)} flagged</span>
      </div>
      {"".join(cards)}
    </section>"""


def _render_stakeholders(stakeholders):
    researchers = stakeholders.get("researchers", [])
    pms = stakeholders.get("pms", [])
    designers = stakeholders.get("designers", [])

    if not researchers and not pms and not designers:
        return ""

    def render_list(items):
        if not items:
            return '<li style="color:var(--muted); font-style:italic;">None listed</li>'
        return "".join(f"<li>{h(i)}</li>" for i in items)

    return f"""<section id="stakeholders" class="section">
      <div class="section-header">
        <h2>👥 Key Stakeholders</h2>
      </div>
      <div class="stakeholder-grid">
        <div class="stakeholder-card">
          <h4>Researchers</h4>
          <ul>{render_list(researchers)}</ul>
        </div>
        <div class="stakeholder-card">
          <h4>Program Managers</h4>
          <ul>{render_list(pms)}</ul>
        </div>
        <div class="stakeholder-card">
          <h4>Designers</h4>
          <ul>{render_list(designers)}</ul>
        </div>
      </div>
    </section>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="UXR Weekly Briefing Generator")
    sub = parser.add_subparsers(dest="command")

    p_fetch = sub.add_parser("fetch", help="Fetch project data → JSON")
    p_fetch.add_argument("--days", type=int, default=7, help="Look-back window in days (default: 7)")
    p_fetch.add_argument("--output", "-o", help="Output JSON file path")

    p_html = sub.add_parser("html", help="Generate HTML from data JSON")
    p_html.add_argument("--data", required=True, help="Path to briefing_data.json from fetch step")
    p_html.add_argument("--summaries", help="Path to summaries.json (issue URL → summary text)")
    p_html.add_argument("--output", "-o", help="Output HTML file (default: briefing.html)")

    args = parser.parse_args()

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "html":
        cmd_html(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
