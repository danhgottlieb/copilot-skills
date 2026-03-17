---
name: coreai-product-catalog
description: CoreAI product inventory, Big Rock to DRI mapping, and work chart data. Use when the user asks about CoreAI products, DRIs, Big Rocks, work chart, product coverage, or needs to update the product-DRI mapping.
---

# CoreAI Product Catalog & DRI Mapping

## Data Sources

1. **CoreAI Flight Deck (Product Catalog):** https://github.com/orgs/coreai-microsoft/projects/18/views/14
   - Contains all products and Big Rock items with milestones, PMs, and priority levels
   - Product field can be sliced via the project board UI

2. **CoreAI Work Chart (DRI Mapping):** https://github.com/orgs/coreai-microsoft/projects/43/views/1
   - Maps Big Rocks to DRIs, Engineering leads, Product leads, Design, and Science

3. **Work Chart README:** https://github.com/coreai-microsoft/product?tab=readme-ov-file#-work-chart
   - Contains the full work chart table in markdown

4. **Local Excel Export:** `C:\Users\dagottl\CoreAI_Product_DRI_Mapping.xlsx`
   - Sheet 1: Full product-DRI mapping with all roles
   - Sheet 2: Flight Deck product list with item counts

## Work Chart — Big Rock to DRI Mapping

| Big Rock | DRI | Engineering | Product | Design | Science |
|----------|-----|-------------|---------|--------|---------|
| 1.1 AI IDE | Joe Binder | Kai Maetzel | JC Carter | Joanna | Elsie Nallipogu |
| 1.2 Agent HQ | Mario Rodriguez | Luke Hoban | Luis Bitencourt-Emilio | Adrian Mato Gondelle | Gemma Garriga |
| 1.3 GitHub Platform | Vladimir Fedorov | Jakub Oleksy | Jared / Todd | Adrian Mato Gondelle | Gemma Garriga |
| 1.4 Intelligent Repo | Steve G | Steve G | Patrick Nikoletich | Adrian Mato Gondelle | Gemma Garriga |
| 1.5 GitHub + Foundry | Amanda Silver | Luke Hoban | Mario Rodriguez | John Maeda & Monty Hammontree | N/A |
| 2.1 Developer Experience | Amanda Silver | Tina Schuchman | Jeff Hollan | QuvanWal & MeganB | N/A |
| 2.2 Ecosystem | Steve Sweetman | Scott Van Vliet | Naomi Moneypenny | Su | Wayne X |
| 2.3 Observability & ROI | Sam Naghshineh | Sam Naghshineh | Sebastian Kohlmeier | Sarah | TBC |
| 2.4 Foundry IQ | Vinod Valloppillil | Pablo Castro | Farzad Sunavala | Trish | AlecB |
| 2.5 Continuous Learning | Yina Arenas | Tina Schuchman | Alicia Frame | QuvanWal | TBC |
| 2.6 Foundry Tools | Vinod Valloppillil | Li Jiang | Dong Li, Yabin Liu, Maria Naggaga | Li Jiang | |
| 3.1 Foundry Control Plane | Sarah Bird | Mohammad Abuomar | Peter Simones | Becky Haruyama | Sandeep Atluri |
| 3.2 GitHub Advanced Security | Marcelo Oliveira | Aaron Cathcart | Pierre T | Glòria Langreo | Gemma Garriga |
| 3.3 GitHub Enterprise Expansion | Todd Manion | Nitasha Verma | TBH | Glòria Langreo | N/A |
| 3.4 GitHub Control Plane | Todd Manion | Sharanya Doddapaneni | Greg Padak | Glòria Langreo | N/A |
| 4.1 Foundry Local | Meng Tang | Rajat Monga | Meng Tang | Su | |
| 4.2 Industrial Edge | Christa St Pierre | Ika Mar-Menachem | Inbal Sagiv | N/A | N/A |
| 4.3 Windows AI | Jatinder Mann | Vicente Rivera | Tucker Burns | N/A | Vivek Pradeep |
| 5.1 Orange | Eric Boyd | Scott Van Vliet | Chris Lauren | QuvanWal | Wayne X |
| 5.2 Efficiency | Steve Sweetman | Scott Van Vliet | Steve Sweetman | Su | |
| 5.3 Experimentation | Tina Schuchman | Tina Schuchman | Jonathan McKay | QuvanWal | |
| 5.4 EngThrive & 1ES | Julia Liuson | Magnus Hedlund | Poonam Gupta | Giorgia Paolini | N/A |

## Product Groupings for Budget Deck

### AI IDE (DRI: Joe Binder)
VS Code · Visual Studio · C++ · .NET · GitHub Copilot · Developer Tools

### Developer Experience (DRI: Amanda Silver)
App Service · Functions · Container Apps · API Management · Logic Apps · SDKs · Managed Redis · SRE Agent · Azure Native Integrations · Java Support on Azure · Mainframe Modernization

### Microsoft Foundry (Multiple DRIs)
- **Vinod Valloppillil:** Foundry IQ, Foundry Tools
- **Sarah Bird:** Control Plane, Responsible AI
- **Steve Sweetman:** Ecosystem
- **Sam Naghshineh:** Observability & ROI
- **Yina Arenas:** Continuous Learning
- **Meng Tang:** Foundry Local

### GitHub (Multiple DRIs)
- **Vladimir Fedorov:** Platform
- **Mario Rodriguez:** Copilot / Agent HQ
- **Steve G:** Intelligent Repo
- **Marcelo Oliveira:** Advanced Security
- **Todd Manion:** Enterprise

### CDC — China Development Center
M365 Agent Toolkit · AZD for Java · Migration

### IDC — India Development Center
Playwright · Azure Load Testing · Azure Native ISV

## Flight Deck Product Catalog (with item counts)

| Product | Items |
|---------|-------|
| API Management | 4 |
| App Service | 7 |
| Azure Managed Redis | 8 |
| Azure Native Integrations | 3 |
| Azure SRE Agent (Pending) | 1 |
| C++ standalone/components | 1 |
| Developer | 2 |
| Functions | 1 |
| GitHub | 290 |
| GitHub Copilot modernization | 3 |
| Java Support on Azure | 1 |
| Logic Apps | 2 |
| Mainframe Modernization (pending) | 1 |
| Microsoft Azure Container Apps | 1 |
| Microsoft Foundry | 185 |
| .NET | 4 |
| Responsible AI | 1 |
| SDKs | 4 |
| Visual Studio | 2 |
| Visual Studio Code | 1 |

## Notes
- Data scraped from GitHub project boards on 2026-03-11
- The Flight Deck uses "Product" as a field on project items; the Work Chart uses "Big Rock" as the organizing unit
- GitHub products in the Flight Deck are rolled up under a single "GitHub" product (290 items)
- Microsoft Foundry similarly rolls up (185 items) across multiple Big Rocks
- CDC and IDC products are not tracked in the Flight Deck project board
