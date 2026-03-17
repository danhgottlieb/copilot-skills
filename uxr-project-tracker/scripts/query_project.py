#!/usr/bin/env python3
"""
Query the UXR Team Projects GitHub Project Board (coreai-microsoft, project #40).

Fetches all project items via GraphQL, parses field values, and supports
filtering and multiple output formats.

Usage:
    python query_project.py [options]

Filters:
    --status STATUS          Filter by Status (e.g. "In progress", "Closed-Completed")
    --assignee LOGIN         Filter by assignee GitHub login (case-insensitive substring)
    --product PRODUCT        Filter by Product name (case-insensitive substring)
    --team TEAM              Filter by Team name (case-insensitive substring)
    --research-phase PHASE   Filter by Research Phase
    --semester SEMESTER      Filter by Semester
    --priority PRIORITY      Filter by Priority
    --closed-after DATE      Items closed on or after DATE (YYYY-MM-DD)
    --closed-before DATE     Items closed on or before DATE (YYYY-MM-DD)
    --search TEXT            Search title and body (case-insensitive substring)

Output:
    --format FORMAT          Output format: table (default), json, csv
    --fields FIELDS          Comma-separated fields to show (default: key fields)
    --all-fields             Show all available fields
    --report-urls            Show only Report URLs (with title)

Examples:
    python query_project.py --status "Closed-Completed" --closed-after 2026-02-11
    python query_project.py --assignee dagottl --status "In progress"
    python query_project.py --product "App Service" --format json
    python query_project.py --report-urls --closed-after 2026-02-04
"""

import argparse
import csv
import io
import json
import subprocess
import sys
from datetime import datetime, timezone


ORG = "coreai-microsoft"
PROJECT_NUMBER = 40

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


def run_graphql(cursor=None, retries=3):
    import time
    after = f', after: "{cursor}"' if cursor else ""
    query = GRAPHQL_QUERY % (ORG, PROJECT_NUMBER, after)
    for attempt in range(retries):
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, encoding="utf-8"
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        if attempt < retries - 1:
            wait = 2 ** (attempt + 1)
            print(f"  API error (attempt {attempt+1}/{retries}), retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
    print(f"Error querying GitHub API after {retries} attempts: {result.stderr}", file=sys.stderr)
    sys.exit(1)


def parse_field_value(node):
    """Extract a (field_name, value) pair from a field value node."""
    if not node:
        return None, None
    field_info = node.get("field", {})
    field_name = field_info.get("name", "")
    if not field_name:
        return None, None

    # Single select
    if "name" in node and "field" in node and len(node) == 2:
        return field_name, node["name"]
    # Text
    if "text" in node:
        return field_name, node["text"]
    # Date
    if "date" in node:
        return field_name, node["date"]
    # Number
    if "number" in node:
        return field_name, node["number"]
    # Users
    if "users" in node:
        users = node["users"]["nodes"]
        return field_name, [{"login": u["login"], "name": u.get("name", "")} for u in users]
    # Labels
    if "labels" in node:
        labels = node["labels"]["nodes"]
        return field_name, [l["name"] for l in labels]
    # Repository
    if "repository" in node:
        return field_name, node["repository"].get("nameWithOwner", node["repository"].get("name", ""))

    return field_name, None


def fetch_all_items():
    """Fetch all project items with pagination."""
    all_items = []
    cursor = None
    page = 0

    while True:
        page += 1
        data = run_graphql(cursor)
        items_data = data["data"]["organization"]["projectV2"]["items"]
        nodes = items_data["nodes"]

        for node in nodes:
            item = {}
            # Parse field values
            for fv in node.get("fieldValues", {}).get("nodes", []):
                fname, fval = parse_field_value(fv)
                if fname:
                    item[fname] = fval

            # Parse content (issue data)
            content = node.get("content", {})
            if content:
                item["_url"] = content.get("url", "")
                item["_state"] = content.get("state", "")
                item["_closedAt"] = content.get("closedAt", "")
                item["_createdAt"] = content.get("createdAt", "")
                item["_updatedAt"] = content.get("updatedAt", "")
                item["_number"] = content.get("number", "")
                item["_body"] = content.get("body", "")
                item["_repo"] = content.get("repository", {}).get("nameWithOwner", "") if content.get("repository") else ""

                # Assignees from issue
                if "assignees" in content:
                    assignees = content["assignees"]["nodes"]
                    if assignees and "Assignees" not in item:
                        item["Assignees"] = [{"login": a["login"], "name": a.get("name", "")} for a in assignees]

                # Labels from issue
                if "labels" in content:
                    labels = content["labels"]["nodes"]
                    if labels and "Labels" not in item:
                        item["Labels"] = [l["name"] for l in labels]

            all_items.append(item)

        page_info = items_data["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
        print(f"  Fetching page {page + 1}...", file=sys.stderr)

    return all_items


def apply_filters(items, args):
    """Apply filters to items list."""
    filtered = items

    if args.status:
        filtered = [i for i in filtered if i.get("Status", "").lower() == args.status.lower()]

    if args.assignee:
        def has_assignee(item):
            assignees = item.get("Assignees", [])
            if isinstance(assignees, list):
                return any(
                    args.assignee.lower() in (a.get("login", "") or "").lower() or
                    args.assignee.lower() in (a.get("name", "") or "").lower()
                    for a in assignees
                )
            return False
        filtered = [i for i in filtered if has_assignee(i)]

    if args.product:
        filtered = [i for i in filtered if args.product.lower() in i.get("Product", "").lower()]

    if args.team:
        filtered = [i for i in filtered if args.team.lower() in i.get("Team", "").lower()]

    if args.research_phase:
        filtered = [i for i in filtered if args.research_phase.lower() in i.get("Research Phase", "").lower()]

    if args.semester:
        filtered = [i for i in filtered if args.semester.lower() in i.get("Semester", "").lower()]

    if args.priority:
        filtered = [i for i in filtered if args.priority.lower() in i.get("Priority", "").lower()]

    if args.closed_after:
        cutoff = datetime.strptime(args.closed_after, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        def closed_after(item):
            ca = item.get("_closedAt", "")
            if not ca:
                return False
            return datetime.fromisoformat(ca.replace("Z", "+00:00")) >= cutoff
        filtered = [i for i in filtered if closed_after(i)]

    if args.closed_before:
        cutoff = datetime.strptime(args.closed_before, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        def closed_before(item):
            ca = item.get("_closedAt", "")
            if not ca:
                return False
            return datetime.fromisoformat(ca.replace("Z", "+00:00")) <= cutoff
        filtered = [i for i in filtered if closed_before(i)]

    if args.search:
        def matches_search(item):
            s = args.search.lower()
            title = item.get("Title", "").lower()
            body = item.get("_body", "").lower()
            return s in title or s in body
        filtered = [i for i in filtered if matches_search(i)]

    return filtered


def format_assignees(assignees):
    if not assignees or not isinstance(assignees, list):
        return ""
    import re
    names = []
    for a in assignees:
        name = a.get("name", a.get("login", ""))
        # Strip pronoun suffixes like "(SHE/HER)", "(HE/HIM)", "(THEY/THEM)"
        name = re.sub(r'\s*\([A-Z]+/[A-Z]+\)\s*$', '', name).strip()
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


DEFAULT_FIELDS = ["Title", "Status", "Assignees", "Product", "Team", "Research Phase", "_url"]

ALL_FIELDS = [
    "Title", "Status", "Assignees", "Product", "Team", "Research Phase",
    "Report URL", "PM", "Designer", "HPF Stage", "Lifecycle Phase",
    "Main Method", "Other Method", "Additional Methods", "Semester",
    "Effort", "Priority", "Contained status", "Start date", "Target date",
    "Coleman Customers", "User Interviews Customers", "URI Customers",
    "UserTesting Customers", "Self-Recruit/Other Customers",
    "Labels", "Repository", "_url", "_state", "_closedAt", "_createdAt", "_repo"
]


def get_display_value(item, field):
    val = item.get(field, "")
    if field == "Assignees":
        return format_assignees(val)
    if field == "Labels":
        return format_labels(val)
    if field in ("_closedAt", "_createdAt", "_updatedAt", "Start date", "Target date"):
        return format_date(val)
    if val is None:
        return ""
    return str(val)


def output_table(items, fields):
    if not items:
        print("No items found.")
        return

    # Build rows
    headers = [f.lstrip("_").replace("_", " ").title() if f.startswith("_") else f for f in fields]
    rows = []
    for item in items:
        rows.append([get_display_value(item, f) for f in fields])

    # Calculate column widths (cap at 50)
    widths = [min(50, max(len(h), max((len(r[i]) for r in rows), default=0))) for i, h in enumerate(headers)]

    # Print
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        cells = [c[:w].ljust(w) for c, w in zip(row, widths)]
        print(" | ".join(cells))

    print(f"\nTotal: {len(items)} items")


def output_json(items, fields):
    output = []
    for item in items:
        row = {}
        for f in fields:
            row[f] = item.get(f, "")
        output.append(row)
    print(json.dumps(output, indent=2, default=str))


def output_csv(items, fields):
    buf = io.StringIO()
    writer = csv.writer(buf)
    headers = [f.lstrip("_").replace("_", " ").title() if f.startswith("_") else f for f in fields]
    writer.writerow(headers)
    for item in items:
        writer.writerow([get_display_value(item, f) for f in fields])
    print(buf.getvalue())


def output_report_urls(items):
    if not items:
        print("No items found.")
        return
    found = 0
    for item in items:
        url = item.get("Report URL", "")
        if url:
            found += 1
            title = item.get("Title", "Untitled")
            assignees = format_assignees(item.get("Assignees", []))
            print(f"* {title}")
            if assignees:
                print(f"  Researcher: {assignees}")
            print(f"  Report: {url}")
            print(f"  Issue: {item.get('_url', '')}")
            print()
    print(f"Found {found} report URLs out of {len(items)} items.")


def html_escape(text):
    """Escape HTML special characters."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def output_html(items, closed_after=None, summaries=None):
    """Generate an HTML page with a styled table of completed studies.

    Args:
        items: List of project items
        closed_after: Date string for subtitle
        summaries: Optional dict mapping issue URL to summary text
    """
    if summaries is None:
        summaries = {}

    date_label = closed_after or "recently"

    rows = []
    for item in items:
        researcher = html_escape(format_assignees(item.get("Assignees", [])))
        title = html_escape(item.get("Title", ""))
        issue_url = item.get("_url", "")
        closed = format_date(item.get("_closedAt", ""))
        report_url = item.get("Report URL", "")
        summary = html_escape(summaries.get(issue_url, ""))

        study_cell = f'<a href="{html_escape(issue_url)}">{title}</a>' if issue_url else title

        if report_url:
            report_label = html_escape(report_url.split("//")[-1].split("/")[0])
            if "hits.microsoft.com" in report_url:
                # Extract HITS type and ID
                parts = report_url.rstrip("/").split("/")
                rtype = parts[-2].capitalize() if len(parts) >= 2 else "Link"
                rid = parts[-1] if len(parts) >= 1 else ""
                report_label = f"HITS {rtype} {rid}"
            elif "dataexplorer.azure.com" in report_url:
                report_label = "Azure Data Explorer Dashboard"
            elif "github.com" in report_url:
                # Shorten GitHub URLs
                path = report_url.replace("https://github.com/", "")
                report_label = f"GitHub - {path.split('/tree/')[0]}" if "/tree/" in path else f"GitHub - {path}"
                if len(report_label) > 50:
                    report_label = report_label[:47] + "..."
            elif "sharepoint.com" in report_url:
                report_label = "SharePoint Doc"
            report_cell = f'<a href="{html_escape(report_url)}">{report_label}</a>'
        else:
            report_cell = '<span class="no-link">None</span>'

        summary_cell = f'<td class="summary">{summary}</td>' if summary else '<td class="summary"></td>'

        rows.append(f"""<tr>
  <td>{study_cell}</td>
  <td>{researcher}</td>
  <td>{closed}</td>
  <td>{report_cell}</td>
  {summary_cell}
</tr>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Recently Completed UXR Studies</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; background: #f6f8fa; color: #24292f; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  .subtitle {{ color: #656d76; margin-bottom: 1.5rem; font-size: 0.9rem; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }}
  th {{ background: #24292f; color: #fff; text-align: left; padding: 10px 14px; font-size: 0.85rem; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #d0d7de; font-size: 0.85rem; vertical-align: top; }}
  .summary {{ max-width: 400px; color: #1f2328; font-size: 0.8rem; line-height: 1.4; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f0f3f6; }}
  a {{ color: #0969da; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .no-link {{ color: #8b949e; font-style: italic; }}
  .count {{ margin-top: 1rem; color: #656d76; font-size: 0.85rem; }}
</style>
</head>
<body>
<h1>Recently Completed UXR Studies</h1>
<div class="subtitle">Closed-Completed since {html_escape(date_label)} &mdash; from <a href="https://github.com/orgs/coreai-microsoft/projects/40/views/1">UXR Team Projects</a></div>
<table>
<thead>
<tr><th>Study</th><th>Researcher</th><th>Closed</th><th>Report</th><th>Summary</th></tr>
</thead>
<tbody>
{"".join(rows)}
</tbody>
</table>
<div class="count">{len(items)} studies completed since {html_escape(date_label)}</div>
</body>
</html>"""
    print(html)


def output_html_word(items, closed_after=None, summaries=None):
    """Generate a Word-friendly HTML table: Researcher, Study (linked to report), Summary.

    No Closed or Report columns. Solid borders for clean copy-paste into Word.
    Study text uses the study title but links to the report URL instead of the issue URL.
    """
    if summaries is None:
        summaries = {}

    date_label = closed_after or "recently"

    rows = []
    for item in items:
        researcher = html_escape(format_assignees(item.get("Assignees", [])))
        title = html_escape(item.get("Title", ""))
        report_url = item.get("Report URL", "")
        issue_url = item.get("_url", "")
        summary = html_escape(summaries.get(issue_url, ""))

        # Link study title to report URL; fall back to issue URL if no report
        link_url = report_url if report_url else issue_url
        study_cell = f'<a href="{html_escape(link_url)}">{title}</a>' if link_url else title

        summary_cell = f'<td class="summary">{summary}</td>' if summary else '<td class="summary"></td>'

        rows.append(f"""<tr>
  <td>{study_cell}</td>
  <td>{researcher}</td>
  {summary_cell}
</tr>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Recently Completed UXR Studies</title>
<style>
  body {{ font-family: 'Segoe UI', Calibri, Arial, sans-serif; margin: 2rem; background: #fff; color: #24292f; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  .subtitle {{ color: #656d76; margin-bottom: 1.5rem; font-size: 0.9rem; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; font-family: 'Segoe UI', Calibri, Arial, sans-serif; }}
  th, td {{ border: 1px solid #8b949e; padding: 8px 12px; font-size: 11pt; vertical-align: top; }}
  th {{ background: #24292f; color: #fff; text-align: left; font-weight: 600; }}
  .summary {{ color: #1f2328; font-size: 10pt; line-height: 1.4; }}
  a {{ color: #0969da; text-decoration: underline; }}
  .count {{ margin-top: 1rem; color: #656d76; font-size: 0.85rem; }}
</style>
</head>
<body>
<h1>Recently Completed UXR Studies</h1>
<div class="subtitle">Closed-Completed since {html_escape(date_label)} &mdash; from <a href="https://github.com/orgs/coreai-microsoft/projects/40/views/1">UXR Team Projects</a></div>
<table>
<thead>
<tr><th>Study</th><th>Researcher</th><th>Summary</th></tr>
</thead>
<tbody>
{"".join(rows)}
</tbody>
</table>
<div class="count">{len(items)} studies completed since {html_escape(date_label)}</div>
</body>
</html>"""
    print(html)


def main():
    parser = argparse.ArgumentParser(description="Query UXR Team Projects board")
    parser.add_argument("--status", help="Filter by Status")
    parser.add_argument("--assignee", help="Filter by assignee (login or name, substring)")
    parser.add_argument("--product", help="Filter by Product (substring)")
    parser.add_argument("--team", help="Filter by Team (substring)")
    parser.add_argument("--research-phase", help="Filter by Research Phase")
    parser.add_argument("--semester", help="Filter by Semester")
    parser.add_argument("--priority", help="Filter by Priority")
    parser.add_argument("--closed-after", help="Closed on or after date (YYYY-MM-DD)")
    parser.add_argument("--closed-before", help="Closed on or before date (YYYY-MM-DD)")
    parser.add_argument("--search", help="Search title and body text")
    parser.add_argument("--format", choices=["table", "json", "csv", "html", "html-word"], default="table", help="Output format")
    parser.add_argument("--fields", help="Comma-separated fields to display")
    parser.add_argument("--all-fields", action="store_true", help="Show all fields")
    parser.add_argument("--report-urls", action="store_true", help="Show report URLs only")
    parser.add_argument("--output", help="Write output to file instead of stdout")
    parser.add_argument("--summaries-json", help="JSON file mapping issue URLs to summary text (for HTML format)")

    args = parser.parse_args()

    print("Fetching project items...", file=sys.stderr)
    items = fetch_all_items()
    print(f"Fetched {len(items)} total items.", file=sys.stderr)

    filtered = apply_filters(items, args)
    print(f"After filtering: {len(filtered)} items.", file=sys.stderr)

    if args.report_urls:
        output_report_urls(filtered)
        return

    # Load summaries JSON if provided
    summaries = {}
    if args.summaries_json:
        try:
            with open(args.summaries_json, "r", encoding="utf-8") as f:
                summaries = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load summaries from {args.summaries_json}: {e}", file=sys.stderr)

    # Redirect stdout to file if --output specified
    original_stdout = sys.stdout
    if args.output:
        sys.stdout = open(args.output, "w", encoding="utf-8")

    # Determine fields
    if args.fields:
        fields = [f.strip() for f in args.fields.split(",")]
    elif args.all_fields:
        fields = ALL_FIELDS
    else:
        fields = DEFAULT_FIELDS

    if args.format == "html":
        output_html(filtered, closed_after=args.closed_after, summaries=summaries)
    elif args.format == "html-word":
        output_html_word(filtered, closed_after=args.closed_after, summaries=summaries)
    elif args.format == "json":
        output_json(filtered, fields)
    elif args.format == "csv":
        output_csv(filtered, fields)
    else:
        output_table(filtered, fields)

    if args.output:
        sys.stdout.close()
        sys.stdout = original_stdout
        print(f"Output written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
