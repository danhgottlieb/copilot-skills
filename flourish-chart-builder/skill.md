---
name: flourish-chart-builder
description: Create professional Flourish-style interactive data visualizations from any data source — Excel files, CSV, or tables pasted directly into the terminal. Produces clean, modern D3.js SVG charts in self-contained HTML files with tooltips, legends, and PNG download buttons. Use when the user wants to create charts, graphs, visualizations, or data figures from tabular data.
---

# Flourish-Style Chart Builder

Creates professional, publication-ready interactive data visualizations styled after [Flourish](https://app.flourish.studio). Produces self-contained HTML files using D3.js with SVG rendering, hover tooltips, responsive layouts, and high-quality PNG export.

## Trigger

Use this skill when the user:
- Pastes a table or data into the terminal and asks for a chart/graph/visualization
- Provides a CSV or Excel file and wants visualizations
- Asks for "Flourish-style" or professional data figures
- Wants to create presentation-ready charts from data

## Step 1: Parse the Data

### From pasted terminal text
Parse the text as a table. Common formats:
- Tab-separated values (from Excel copy-paste)
- Comma-separated values
- Markdown tables (`| col1 | col2 |`)
- Space-aligned columns

Use Python to parse ambiguous formats:
```python
import csv, io
# Try tab-separated first, then comma, then space
for delimiter in ['\t', ',', None]:
    reader = csv.reader(io.StringIO(raw_text), delimiter=delimiter)
    rows = list(reader)
    if len(rows[0]) > 1:
        break
```

### From Excel files
- If the file is a local `.xlsx`, use Python `openpyxl` to read it
- If the file is DRM/IRM-protected or on SharePoint, use Playwright to open it in Excel Online and read via the Name Box navigation method (click Name Box combobox → type table name → Enter → screenshot to read)
- If the file is a `.csv`, read directly with Python

### From Excel Online / SharePoint links
1. Navigate to the URL with `playwright-browser_navigate`
2. Wait for load (`playwright-browser_wait_for` time: 5)
3. Use the Name Box to navigate to named tables
4. Screenshot and read cell values

## Step 2: Choose Chart Type

Based on the data shape, select the best chart type:

| Data Shape | Recommended Chart | When to Use |
|---|---|---|
| Categories + single values | **Horizontal stacked composition bar** | Showing parts of a whole (100% bar) |
| Categories + single large counts | **Pictogram / Icon array** | Conveying scale/magnitude of counts (people, sessions, units) |
| Categories + multiple time periods | **Grouped or stacked column chart** | Comparing across time |
| Two numeric dimensions | **Scatter plot** | Showing correlation or distribution |
| Single category ranking | **Horizontal bar chart** | Ranked comparisons |
| Small number of parts-of-whole | **Donut chart** | 2-5 categories summing to a total |
| Time series | **Line chart** | Trends over time |

Ask the user if the chart type isn't obvious from the data. Offer 2-3 options with a recommendation.

## Step 3: Build the Visualization

### Technology Stack
- **D3.js** v7.9+ (SVG-based — NOT Chart.js/canvas, which has screenshot issues)
- **html2canvas** v1.4+ for PNG export
- **Inter** font from Google Fonts
- Self-contained single HTML file, no build step

### CDN Dependencies
```html
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
```

### Design System

**Typography:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

**Color Palette (7 colors, expand as needed):**
```javascript
const palette = ['#6366f1','#06b6d4','#f59e0b','#10b981','#f43f5e','#8b5cf6','#64748b'];
// Indigo, Cyan, Amber, Emerald, Rose, Violet, Slate
```

For charts with fewer categories, pick a harmonious subset (e.g., 3 categories → `['#6366f1','#f59e0b','#10b981']`).

**Layout:**
```css
body { background: #f8f9fb; color: #1a1a2e; padding: 48px 24px; }
html { overflow-y: scroll; }

.chart-card {
    max-width: 1140px; /* PPT widescreen friendly */
    margin: 0 auto 56px;
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 6px 24px rgba(0,0,0,0.04);
    padding: 40px 40px 32px;
}
```

**Chart title:** 20px, weight 600, color `#1a1a2e`
**Chart subtitle:** 13px, color `#9ca3af`
**Tooltips:** dark background `#1a1a2e`, white text, `border-radius: 8px`, `box-shadow`

### SVG Best Practices
- **Always use `viewBox`** with `width: 100%` and `style="max-width: Xpx"` — never fixed width/height attributes
- **Container divs:** `overflow: hidden` to prevent elements spilling on zoom
- **Transitions:** `transition: opacity 0.2s` on interactive elements
- **Hover:** dim non-hovered elements to 0.15 opacity for focus effect

### Page Structure
```html
<div class="page-header">
    <h1>Title</h1>
    <p>Subtitle describing the data</p>
</div>

<div class="chart-card" id="chart1Card">
    <div class="chart-title">Chart Name</div>
    <div class="chart-subtitle">Description with key number highlighted</div>
    <div id="chart1" style="position:relative; overflow:hidden"></div>
    <div class="legend-row" id="chart1Legend"></div>
    <div class="total-banner" id="chart1Banner"></div>
    <button class="download-btn" onclick="downloadChart('chart1Card', 'filename')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        Download PNG
    </button>
</div>

<div class="footer">Source: [data source] · Generated [date]</div>
```

### Download Function
```javascript
function downloadChart(cardId, filename) {
    const card = document.getElementById(cardId);
    const btn = card.querySelector('.download-btn');
    btn.style.display = 'none';
    html2canvas(card, {
        scale: 3,
        backgroundColor: '#ffffff',
        useCORS: true,
        allowTaint: true,
        logging: false,
    }).then(canvas => {
        btn.style.display = '';
        const link = document.createElement('a');
        link.download = filename + '.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
    }).catch(() => { btn.style.display = ''; });
}
```

**IMPORTANT html2canvas limitations:**
- **Cannot render SVG `<image>` elements** — even with base64 `href`. Use HTML `<img>` tags instead.
- **Cannot render SVG data URIs in `<img>` tags** — `data:image/svg+xml,...` won't appear in downloads. All images must be PNG base64 (`data:image/png;base64,...`).
- **Cannot fetch cross-origin images** — Google S2 favicon API blocks CORS. Pre-download logos server-side with Python and embed as `data:image/png;base64,...` data URIs directly in the JavaScript source.
- For custom icons (no logo source), use Python **Pillow** to draw shapes and export as PNG base64.

### Common Chart Patterns

**Horizontal Stacked Composition Bar:**
- Compute cumulative positions for segments
- Use `d3.scaleLinear` mapping [0, total] to [0, barWidth]
- Inline labels for segments wider than ~52px
- Rounded corners on first/last segment (`rx: 6`, others `rx: 2`)
- Legend row below with colored dots + values + percentages

**Pictogram / Icon Array:**
- Best for count data where you want to convey magnitude (e.g., "2,121 people")
- One row per category: label on left, grid of icons flowing right
- Person bust SVG path: `M6 6.5C7.65 6.5 9 5.15 9 3.5C9 1.85 7.65 0.5 6 0.5C4.35 0.5 3 1.85 3 3.5C3 5.15 4.35 6.5 6 6.5ZM6 8C3.33 8 0 9.34 0 12V13.5H12V12C12 9.34 8.67 8 6 8Z`
- Icon size: 10×12px at scale(0.68)
- Category labels show logo/icon + name + count (percentage)
- Hover dims other categories

**Grouped/Stacked Column Chart:**
- Use `d3.scaleBand` for x-axis categories
- `d3.scaleLinear` for y-axis values
- For stacked: use `d3.stack()` to compute layouts
- Include x/y axis labels, gridlines at y ticks

**Total Banner:**
- Large centered number (36px, weight 700)
- Small uppercase label below (12px, weight 500, color `#9ca3af`)

### Tooltips Pattern
```css
.chart-tooltip {
    position: absolute; pointer-events: none;
    background: #1a1a2e; color: #fff;
    border-radius: 8px; padding: 12px 16px;
    font-size: 12.5px; line-height: 1.7;
    box-shadow: 0 4px 16px rgba(0,0,0,0.18);
    opacity: 0; transition: opacity 0.15s;
    z-index: 100; white-space: nowrap;
}
.chart-tooltip.visible { opacity: 1; }
```

Position tooltips relative to the container using `mousemove` event coordinates minus container bounding rect.

## Step 4: Serve and Preview

Start a local HTTP server and open in Playwright for screenshot preview:
```bash
python -m http.server 8765 --directory [output-dir]
```

Navigate Playwright to `http://localhost:8765/[filename].html` and take a full-page screenshot to show the user.

## Step 5: Iterate

The user will likely want tweaks. Common requests:
- Change chart type (e.g., bar → pictogram)
- Adjust colors or layout
- Add/remove labels or legends
- Change icon or logo placement
- Resize elements

Make minimal, surgical changes. The design system above should handle most requests without restructuring.

## Key Technical Notes

- **Use D3.js SVG, NOT Chart.js canvas.** Canvas renders to pixels that Playwright screenshots can't always capture. SVG renders as DOM elements and always screenshots correctly.
- **Google S2 favicon API** works for company logos: `https://www.google.com/s2/favicons?domain=example.com&sz=128`. Clearbit is dead, img.logo.dev requires auth.
- **For non-company categories** (e.g., "Self-recruit", "Conference", "Other"), create PNG icons with Python Pillow and embed as `data:image/png;base64,...`. Do NOT use SVG data URIs — html2canvas cannot render them in `<img>` tags either.
- **DRM-protected Excel files** cannot be read with openpyxl/xlrd. Must use Playwright + Excel Online.

### html2canvas & External Images (CRITICAL)

**html2canvas cannot render:**
- SVG `<image>` elements (even with base64 `href`)
- Cross-origin images fetched at runtime (CORS blocks Google S2 favicon API)

**Solution: Pre-download logos server-side and hardcode as base64 data URIs.**

1. Use Python to download external logos and convert to base64:
```python
import urllib.request, base64
url = 'https://www.google.com/s2/favicons?domain=example.com&sz=128'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
data = urllib.request.urlopen(req).read()
data_uri = f'data:image/png;base64,{base64.b64encode(data).decode()}'
```

2. Embed the data URIs directly in a JavaScript object in the HTML:
```javascript
const logoMap = {
    "CompanyA": "data:image/png;base64,iVBORw0KGgo...",
    "CompanyB": "data:image/png;base64,iVBORw0KGgo...",
    "Other": `data:image/svg+xml,${encodeURIComponent('<svg ...>...</svg>')}`,
};
```

3. Use HTML `<img src="${logoMap[name]}">` tags — NOT SVG `<image>` elements — so html2canvas renders them correctly in PNG downloads.

This pattern ensures logos appear both in the live browser view AND in downloaded PNGs.
