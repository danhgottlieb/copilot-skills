# GitHub Projects to Excel

Export GitHub Projects board items to an Excel file with three columns: Title, Assignees, and Report URL (custom field).

## Source

**Always pull from this URL:** https://github.com/orgs/coreai-microsoft/projects/40/views/14

- Organization: `coreai-microsoft`
- Project number: `40`
- View: `14`

## Trigger

Use this skill when the user wants to:
- Export a GitHub Projects board to Excel
- Create a table from GitHub Projects data
- Generate a spreadsheet from project board items

## Workflow

1. **Fetch project data using GitHub GraphQL API** via the `gh` CLI (always from coreai-microsoft project 40):
   ```bash
   gh api graphql -f query='
   query {
     organization(login: "coreai-microsoft") {
       projectV2(number: 40) {
         items(first: 100) {
           nodes {
             content {
               ... on Issue {
                 title
                 assignees(first: 10) {
                   nodes { login }
                 }
               }
               ... on PullRequest {
                 title
                 assignees(first: 10) {
                   nodes { login }
                 }
               }
             }
             fieldValues(first: 20) {
               nodes {
                 ... on ProjectV2ItemFieldTextValue {
                   text
                   field { ... on ProjectV2Field { name } }
                 }
               }
             }
           }
         }
       }
     }
   }'
   ```

4. **Parse the project items** to extract:
   - **Title**: The title of each issue/item from `content.title`
   - **Assignees**: Comma-separated list from `content.assignees.nodes[].login`
   - **Report URL**: The custom field value where `field.name` equals "Report URL"

5. **Generate an Excel file** using Node.js with xlsx library:
   ```javascript
   const XLSX = require('xlsx');
   
   const rows = [['Title', 'Assignees', 'Report URL']];
   items.forEach(item => {
       const title = item.content?.title || '';
       const assignees = item.content?.assignees?.nodes?.map(a => a.login).join(', ') || '';
       
       // Find the "Report URL" custom field
       const reportUrlField = item.fieldValues?.nodes?.find(
           f => f.field?.name === 'Report URL'
       );
       const reportUrl = reportUrlField?.text || '';
       
       rows.push([title, assignees, reportUrl]);
   });
   
   const wb = XLSX.utils.book_new();
   const ws = XLSX.utils.aoa_to_sheet(rows);
   ws['!cols'] = [{ wch: 60 }, { wch: 40 }, { wch: 70 }];
   XLSX.utils.book_append_sheet(wb, ws, 'Project Items');
   XLSX.writeFile(wb, 'github_project_export.xlsx');
   ```

6. **Report the output file location** to the user

## Dependencies

- GitHub CLI (`gh`) with authentication
- Node.js with xlsx library (`npm install xlsx`)

## Example Usage

User: "Export the GitHub project to Excel"

Response: Fetch the project data from coreai-microsoft/projects/40 using GraphQL to get custom fields, create an Excel file with Title, Assignees, and Report URL columns, and save it to the current directory.

## Notes

- **Important**: The "Report URL" is a custom field in the GitHub Project, NOT the issue URL
- Use GraphQL API to access custom project fields (REST API doesn't expose them)
- For large projects with 100+ items, pagination may be needed (use `after` cursor)
- Ensure `gh` CLI is authenticated with appropriate permissions
