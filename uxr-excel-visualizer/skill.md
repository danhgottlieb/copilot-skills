---
name: uxr-excel-visualizer
description: Create Flourish-style data visualizations from the UX Research 2025 Tables Excel file on SharePoint. Use when the user asks to visualize, chart, or graph data from the UX Research 2025 Excel, mentions named tables like Qualitative_Research_Sessions or Total_Studies, or references the SharePoint UX Research spreadsheet.
---

# UXR Excel Visualizer

Creates professional, Flourish-style interactive data visualizations from the **UX Research 2025 Tables** Excel file hosted on SharePoint. Outputs self-contained HTML files with D3.js SVG charts, hover tooltips, and PNG download buttons.

## Source File

**SharePoint URL:** `https://microsoft-my.sharepoint.com/:x:/r/personal/dagottl_microsoft_com/Documents/UX%20Research%202025%20Tables.xlsx?d=w47d0a75909324eee935120500af1f708&csf=1&web=1&e=I6jKGX`

**Local path (DRM-protected, cannot be read programmatically):** `C:\Users\dagottl\OneDrive - Microsoft\UX Research 2025 Tables.xlsx`

The file is IRM-encrypted. You **must** use Playwright to open it in Excel Online and read data from there.

## Known Named Tables

| Table Name | Location | Columns | Data |
|---|---|---|---|
| `Qualitative_Research_Sessions` | L12:M18 (headers L11:M11) | Agency, Research Sessions | Agency breakdown of qualitative sessions (Coleman=303, Self-recruit=185, URI=187, User Interview=575, UserTesting=419, Respondent.io=79, Conference=373) |
| `Total_Studies` | L38:M40 (headers L37:M37) | Study Type, Studies | Research type breakdown (Moderated=179, Survey=48, Unmoderated=41) |

**Important:** The named tables are on the far right of the sheet (columns L-M). Do NOT use the pivot tables on the left side of the sheet.

## How to Read Data from Excel Online

1. **Navigate** to the SharePoint URL using `playwright-browser_navigate`
2. **Wait** for the spreadsheet to load (use `playwright-browser_wait_for` with `time: 5`)
3. **Click the Name Box** (combobox labeled "Name Box") in the formula bar area
4. **Type the table name** (e.g., `Total_Studies`) and press Enter — this selects the table's data body
5. **Take a screenshot** to visually read the data, or read individual cells by clicking them and checking the formula bar

The user is already authenticated as Daniel Gottlieb (dagottl@microsoft.com). Sessions auto-authenticate.

## Vendor Logo Sources

For recruiting agency logos, use Google S2 favicon API to **download server-side** with Python, then embed as base64 data URIs:
- Coleman: `https://www.google.com/s2/favicons?domain=colemanrg.com&sz=128`
- URI (User Research International): `https://www.google.com/s2/favicons?domain=uriux.com&sz=128`
- User Interview: `https://www.google.com/s2/favicons?domain=userinterviews.com&sz=128`
- UserTesting: `https://www.google.com/s2/favicons?domain=usertesting.com&sz=128`
- Respondent.io: `https://www.google.com/s2/favicons?domain=respondent.io&sz=128`
- Self-recruit: person bust silhouette (cyan) — rendered as PNG with Pillow, embedded as `data:image/png;base64,...`
- Conference: tech conference monitor with chart bars (slate) — rendered as PNG with Pillow, embedded as `data:image/png;base64,...`

**All icons must be PNG base64** — html2canvas cannot render SVG data URIs in `<img>` tags either. Use Python Pillow to draw simple icons and convert to PNG base64.

**CRITICAL: Logos must be hardcoded as base64 data URIs in the HTML.** Do NOT use runtime `fetch()` — Google S2 doesn't support CORS, so fetching in the browser fails. Instead:
1. Download each logo server-side with Python `urllib.request`
2. Convert to base64 with `base64.b64encode()`
3. Embed as `data:image/png;base64,...` strings directly in the JavaScript `logoMap` object
4. Use HTML `<img>` tags (not SVG `<image>` elements) so html2canvas can render them in PNG downloads

```python
import urllib.request, base64
url = 'https://www.google.com/s2/favicons?domain=example.com&sz=128'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
data = urllib.request.urlopen(req).read()
data_uri = f'data:image/png;base64,{base64.b64encode(data).decode()}'
```

## Chart Types Built

### Pictogram / Icon Array (Qualitative Research Sessions)
- One row per agency with: logo → agency name → count (percentage) → grid of person bust SVG icons
- Person bust SVG path: `M6 6.5C7.65 6.5 9 5.15 9 3.5C9 1.85 7.65 0.5 6 0.5C4.35 0.5 3 1.85 3 3.5C3 5.15 4.35 6.5 6 6.5ZM6 8C3.33 8 0 9.34 0 12V13.5H12V12C12 9.34 8.67 8 6 8Z`
- Icon size: 10×12px, scale(0.68)
- Hover: dims all other agencies to 0.15 opacity, shows tooltip
- Each icon = 1 research session to convey scale

### Horizontal Stacked Composition Bar (Total Studies)
- Single horizontal bar with segments per category
- Inline labels for segments wider than 52px
- Rounded corners on first/last segment
- Legend row below with colored dots
- Total banner with large number

## Design System

### CDN Dependencies
```html
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
```

### Typography
- Font: `Inter` from Google Fonts (weights: 300, 400, 500, 600, 700)
- Font import: `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');`

### Color Palette
```javascript
const palette = ['#6366f1','#06b6d4','#f59e0b','#10b981','#f43f5e','#8b5cf6','#64748b'];
// Indigo, Cyan, Amber, Emerald, Rose, Violet, Slate
```

### Layout
- Background: `#f8f9fb`
- Card: white `#fff`, `border-radius: 16px`, subtle shadow, `padding: 40px 40px 32px`, `max-width: 1140px` (PPT widescreen friendly)
- Text: primary `#1a1a2e`, secondary `#6b7280`, muted `#9ca3af`
- Tooltips: dark `#1a1a2e` with white text, `border-radius: 8px`

### SVG Best Practices
- Use `viewBox` with `width: 100%` for responsive scaling (no fixed width/height)
- Container divs get `overflow: hidden` to prevent icon spill on zoom
- Page uses `html { overflow-y: scroll; }` to ensure scrollbar

### Download Feature
Each chart card has a "Download PNG" button using `html2canvas` at 3x scale for high quality output. The button hides itself during capture.

**html2canvas limitations:**
- **Cannot render SVG `<image>` elements** — even with base64 data URIs in `href`. Always use HTML `<img>` tags for logos/icons that need to appear in downloads.
- **Cannot render SVG data URIs in `<img>` tags** — `data:image/svg+xml,...` sources won't appear in downloads. All images must be PNG base64 (`data:image/png;base64,...`).
- **Cannot fetch cross-origin images at runtime** — Google S2 favicon API blocks CORS. All external images must be pre-downloaded and embedded as base64 data URIs.
- For custom icons without a logo source, use Python **Pillow** to draw simple shapes and export as PNG base64.

## Output

Save the HTML file to `C:\Users\dagottl\Downloads\ux_research_charts.html` and serve it via a local HTTP server:

```bash
python -m http.server 8765 --directory C:\Users\dagottl\Downloads
```

Open in Playwright at `http://localhost:8765/ux_research_charts.html` for preview.

## Reference Implementation

The current working visualization is at `C:\Users\dagottl\Downloads\ux_research_charts.html`. Use it as a reference for style, structure, and code patterns when building new charts from additional tables in the same Excel file.

## Adding New Tables

When the user asks to visualize a new table from the same Excel file:
1. Navigate to the table using the Name Box method described above
2. Read the data (screenshot + cell inspection)
3. Choose an appropriate chart type based on the data shape
4. Add a new chart card to the existing HTML file following the same design system
5. Include a Download PNG button for the new chart
