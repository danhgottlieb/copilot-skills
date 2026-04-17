---
name: github-friday-minutes-formatter
description: Converts the Friday Minutes Word document into GitHub-flavored markdown for pasting into a GitHub comment. Use when the user says "format friday minutes", "convert the minutes to markdown", "post minutes to GitHub", "friday minutes formatter", or shares a SharePoint link to the Friday Minutes document. Handles all the tricky Word-to-markdown conversion issues including hyperlink display text, bullet detection, fragment anchors, and HTML tables for multi-line cells.
---

# GitHub Friday Minutes Formatter

Convert the CoreAI Design and Research Friday Minutes Word document into clean GitHub-flavored markdown, ready to paste into a GitHub comment.

## When to Use

- User shares a SharePoint link to the Friday Minutes .docx
- User asks to format/convert the Friday Minutes for GitHub
- User asks to post the minutes as a GitHub comment

## Critical Rules (Lessons Learned)

These rules are non-negotiable. Every one was learned from a real conversion failure:

### 1. NEVER paraphrase or edit text
Copy every word verbatim from the document. Do not summarize, shorten, reorganize, or "clean up" any text. You are converting FORMAT only, not content.

### 2. Hyperlink display text must be preserved
Word hyperlinks have DISPLAY TEXT that is different from the URL. You must extract and use the correct display text for every link. Common display texts in this document:
- Study titles (e.g., "Knowledge, Tools, and Agent Building - JTBD and Pain Points - Customer Interview Learnings")
- "Link to work" (in the Creative table)
- "PR #NN" (in the Lil' Azure section)
- Named descriptions (e.g., "Agents dashboard prototype (Lil Azure),", "CoreAI Design & Research Shared Resources")

**Never show raw URLs as link text.** Always use `[Display Text](URL)` format.

### 3. Check for Word anchor fragments (`w:anchor`)
Word stores URL fragment anchors (like `#main`) SEPARATELY from the URL in a `w:anchor` attribute on the `<w:hyperlink>` element. Text extraction tools will SILENTLY DROP these anchors. You must:
1. Ask WorkIQ to check for `w:anchor` attributes in `document.xml`
2. Append any anchor values to the corresponding URL as `#anchorvalue`
3. Verify by asking the user to test links if unsure

### 4. Detect bullet formatting from Word XML, not text
Word bullet lists are defined by `w:numPr` (numbering properties) and `ListParagraph` styles in the XML — NOT by whether text starts with a dash. Plain text extraction WILL MISS real bullet lists. You must:
1. Ask WorkIQ to check the Word XML `w:pPr/w:numPr` numbering properties for each cell
2. Items with `w:numPr` or `ListParagraph` style are bullets — format them with `- ` prefix
3. Items without these are plain paragraphs — separate with blank lines
4. Some cells mix bullets and non-bulleted headers (e.g., Row 5 with "Pilot Study 1" header followed by bulleted findings)

### 5. Strip internal document labels
The document contains `L1:`, `L2:`, etc. labels before some paragraphs. These are internal reference markers — remove them from the output.

### 6. Strip Word artifacts
Remove `<span style="color:...">` tags, trailing page numbers (e.g., "455" at end of a paragraph), and other Word rendering artifacts. Preserve the text content within the spans.

### 7. Use HTML tables for complex table cells
The UXR studies table has multi-line cells with bullets, bold text, and paragraphs. GitHub markdown tables cannot handle this. Use HTML `<table>` tags for complex tables. Simple tables (like the Creative work table) can use standard markdown table syntax.

## Workflow

### Step 1: Extract verbatim content

Use WorkIQ with the document URL to get the full verbatim text:

```
workiq-ask_work_iq(
  fileUrls: ["<sharepoint_url>"],
  question: "Copy the ENTIRE document word-for-word. Do NOT paraphrase. For EVERY hyperlink, give both display text AND URL. For each section tell me which lines are bullet points vs plain paragraphs."
)
```

### Step 2: Extract all hyperlinks with display text

Make a SEPARATE call to get a complete hyperlink inventory:

```
workiq-ask_work_iq(
  fileUrls: ["<sharepoint_url>"],
  question: "List EVERY hyperlink as a numbered list. For each: 1) exact display text 2) exact URL. Include ALL hyperlinks in all sections."
)
```

### Step 3: Check for anchor fragments

```
workiq-ask_work_iq(
  fileUrls: ["<sharepoint_url>"],
  question: "Check the Word XML for any w:anchor attributes on hyperlink elements. List every hyperlink that has a w:anchor value — I need to append these as #fragment to the URLs."
)
```

### Step 4: Check bullet formatting in Word XML

```
workiq-ask_work_iq(
  fileUrls: ["<sharepoint_url>"],
  question: "Check the Word XML w:pPr/w:numPr numbering properties and ListParagraph styles. For each table cell and section, tell me which paragraphs are Word bullet list items vs plain paragraphs."
)
```

### Step 5: Build the markdown

Using all the extracted information, build the markdown file:

1. **Title** as `# heading`, date as bold text (no labels like "L1:")
2. **UXR studies table** as HTML `<table>` with:
   - Study column: `[Study Title Display Text](URL)` on one line, researcher name on next line
   - Key Learnings column: verbatim text with correct bullet (`- `) vs paragraph formatting
3. **Design updates sections** as markdown headings with:
   - Inline links using correct display text
   - Bullet lists where the original has bullets
   - Links with fragment anchors where needed
4. **Creative table** as standard markdown table with `[Link to work](URL)` in Summary column

### Step 6: Save and copy to clipboard

Save to the session files directory and copy to clipboard:

```powershell
Get-Content "<path_to_file>" | Set-Clipboard
```

### Step 7: Verify

After building, verify:
1. Every hyperlink has the correct display text (not raw URLs)
2. All anchor fragments are present
3. Bullet formatting matches the Word document
4. No text has been paraphrased or modified
5. No Word artifacts remain (span tags, L-labels, page numbers)

## Document Structure Reference

The Friday Minutes typically follows this structure:

```
# Friday Minutes: CoreAI Design and Research
<date>

## 🔍 CAIDR UXR Staff Research Project Area Updates
### ⭐ Recently completed UXR studies
<table> ... 5 study rows ... </table>

## 🎨 CAIDR Design Project Area Updates
### Azure Dev Services
#### ⭐ Compute – Austin Auth
#### ⭐ Lil' Azure – <names>
#### ⭐ Agentic Application Modernization
### Foundry — DRI: <name>
### RAI, IES, Creative — DRI: <name>
#### ⭐ Creative — <name>
<creative work table>
```

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| AI paraphrases text during extraction | Always request "verbatim, word-for-word" and verify |
| Hyperlinks show as raw URLs | Always extract display text separately |
| `#main` or other anchors missing from URLs | Check `w:anchor` in Word XML |
| Bullet lists rendered as plain paragraphs | Check `w:numPr` in Word XML, don't trust text extraction |
| Word span tags leak into output | Strip `<span>` tags, keep inner text |
| Labels like "L1:" appear in output | Strip all `Ln:` prefixes |
| Markdown tables break with multi-line cells | Use HTML `<table>` for complex cells |
| Smart quotes or special chars get mangled | Preserve Unicode as-is |
