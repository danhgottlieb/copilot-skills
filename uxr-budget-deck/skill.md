---
name: uxr-budget-deck
description: Guidelines for editing the CoreAI UXR Budget deck. Use when the user asks to edit, update, or work on the budget presentation, ResOps deck, or CoreAI UXR Budget.pptx. Contains design principles, visual standards, and narrative approach.
---

# CoreAI UXR Budget Deck — Editing Guidelines

## File Location

**OneDrive path:** `C:\Users\dagottl\OneDrive - Microsoft\CoreAI UXR Budget.pptx`

**Important:** This file is in legacy OLE format despite the `.pptx` extension. You must use **PowerPoint COM automation** (not python-pptx) to read and edit it.

## Working with the File

```powershell
$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = 1
$pres = $ppt.Presentations.Open("C:\Users\dagottl\OneDrive - Microsoft\CoreAI UXR Budget.pptx", $false, $false, $true)
# ... make edits ...
$pres.Save()
$pres.Close()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($pres) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
```

## Narrative & Storytelling Principles

1. **Show, don't tell.** Never say "UXR is valuable." Instead, tell stories where UXR was critical and the audience is compelled to that conclusion on their own.
2. **Compelling story arc.** Each proof-of-impact section follows: THE ASK → surprising finding → what changed. The audience must feel the weight of the insight.
3. **Counterfactual framing.** Each story ends with "WITHOUT QUALITATIVE RESEARCH" — painting what would have gone wrong. This is the implicit argument for funding.
4. **Concrete origins.** Ground stories in real asks from real people (e.g., "Pierce Boggan and Joe Binder asked..." or "Leadership proposed...").
5. **Don't make it complicated or wordy.** The presentation must be extremely easy to understand and impactful. Every word earns its place.
6. **Breadth matters.** When showing the product portfolio, the visual must convey the sheer scale of products covered — use individual elements (pills/tags) rather than comma-separated lists.

## Visual Design Standards

### Color Palette (PowerPoint COM RGB values)
| Color | RGB Value | Use |
|-------|-----------|-----|
| Gold/Amber | `16765952` | Titles, DRI names, primary accent |
| Green | `508415` | Secondary accent, "what changed" titles |
| White | `16777215` | Body text on dark backgrounds |
| Soft White | `15658734` | Secondary body text |
| Dark Card | `3810597` | Card/pill backgrounds |
| GitHub Blue | `11950491` | GitHub section accent |
| CDC Green | `10271770` | CDC section accent |
| IDC Teal | `7039999` | IDC section accent, subtle accent lines |

### Typography
- **Slide titles:** 36pt, bold, gold (`16765952`)
- **Section headers:** 14-15pt, bold, white (`16777215`)
- **Sub-headers / labels:** 11pt, bold, gold or green
- **Body text:** 12-13pt, regular, white or soft white
- **Product pills:** 9.5-10pt, regular, white, LEFT-aligned inside pill
- **DRI names:** 10-11pt, bold, gold
- **"WITHOUT RESEARCH" label:** 11pt, bold, teal (`7039999`)

### Layout Conventions
- **Slide dimensions:** 960 × 540 pt (widescreen)
- **Left margin:** 57.6 pt
- **Accent lines:** 36pt wide, 2.5pt tall colored bars above section headers
- **Product pills:** Rounded rectangles (`AddShape(5, ...)`), fill=`3810597`, FLAT (no 3D/shadow/gradient). Always call `.Fill.Solid()`, `.Shadow.Visible = 0`, `.ThreeD.Visible = 0`
- **Pill sizing:** ~130pt wide × 19-21pt tall, 2-per-row with 5pt horizontal gap
- **No double separator bars** between sections — just a gap

### Proof-of-Impact Slide Pattern (2-slide pairs)
**Slide A — Findings:**
- Title: "Proof of impact: [Product]" (36pt, bold, gold)
- "THE ASK" or "THE CHALLENGE" header in gold (11pt)
- Origin story body (13pt, soft white)
- Big reveal text (36pt, bold, green) — the mic drop
- "WHAT RESEARCH REVEALED" header (11pt, green)
- Two-column findings: header (16pt, bold, gold) + body (12pt, soft white)
- Footer: synthesis line (14pt, teal)

**Slide B — Impact:**
- Title: "X impact: What changed" (36pt, bold, green)
- 4 outcome bars: dark card background with gold left accent (5pt), outcome text (15pt, white)
- "WITHOUT QUALITATIVE RESEARCH" footer section: dark card, label (11pt, teal), body (13pt, soft white)

### Product Portfolio Slide Pattern
- Top: 4 callout boxes explaining what the budget funds
- Below: 3-column layout organized by DRI
- Each column: Section header (accent line + title) → DRI name (gold) → product pills
- For sections with many DRIs (Foundry, GitHub): can use 2-column pill grid within the section
- GitHub/CDC/IDC on the right column, stacked with section headers

## Key Slide Structure (as of last edit)
- Slide 3: Original product list (preserved for reference)
- Slides 4-6: Iterative versions of the DRI-organized product slide
- Slides 8-9: VS Code compete story (THE ASK → findings → what changed)
- Slide 10: Pricing mic-drop slide (billing study impact)
- Slide 11-12: Azure AI Foundry story
