---
name: loki-brand-design
description: >-
  Master brand guidelines, visual identity, color tokens (Digital Light Mode, Digital Dark Mode,
  and Print CMYK/Pantone), typography rules, photo color-grading pipeline, and layout blueprints
  for Lokesh Chanana (Loki) — Real Broker LLC. Use this skill whenever designing, generating, or
  updating posters, flyers, postcards, yard signs, PDF client guides, social media carousels/reels,
  email templates, or website UI components.
---

# Lokesh Chanana (Loki) — Brand & Marketing Design Skill

Always read [/home/lokesh/Casa-poki/real-estate/BRAND_GUIDELINES.md](/home/lokesh/Casa-poki/real-estate/BRAND_GUIDELINES.md) for full specifications and import [/home/lokesh/Casa-poki/.agents/skills/loki-brand-design/scripts/brand_toolkit.py](/home/lokesh/Casa-poki/.agents/skills/loki-brand-design/scripts/brand_toolkit.py) when generating PDFs, flyers, posters, postcards, or social media graphics in Python.

---

## 1. Core Brand Identity & Mandatory Credentials
- **Agent:** `Lokesh Chanana (Loki)` — `REALTOR®` / `Real Estate Agent`
- **Brokerage:** `Real Broker LLC` (WA License `#26006634`)
- **Direct Contact:** `(801) 860-1052` • `lokesh@lokeshchanana.com` / `hello@lokeshchanana.com` • `https://lokeshchanana.com`
- **Brand Voice:** Warm, neighborly, conversational, and protective of the client's wallet and comfort—never stiff or pushy.

---

## 2. Master Color System (Print CMYK, Digital Light Mode & Digital Dark Mode)

### 2.1 Shared Palette Tokens
- **`ivory` (`#FAF8F5`):** `RGB(250, 248, 245)` | `CMYK(0, 1, 3, 2)` | `PMS Warm Gray 1 C (10%)` — Primary Light Mode & Print Canvas
- **`ivory-dark` (`#E5E1DB`):** `RGB(229, 225, 219)` | `CMYK(0, 2, 6, 10)` | `PMS Warm Gray 2 C` — Secondary Light Surface
- **`white` (`#FFFFFF`):** `RGB(255, 255, 255)` | `CMYK(0, 0, 0, 0)` — Elevated Card Surface (Light Mode & Print)
- **`charcoal` (`#1F2933`):** `RGB(31, 41, 51)` | `CMYK(78, 64, 52, 62)` | `PMS 432 C` — Primary Ink & Left Bars (Light Mode) / Primary Canvas (Dark Mode)
- **`charcoal-dark` (`#151C23`):** `RGB(21, 28, 35)` | `CMYK(82, 68, 55, 74)` | `PMS 433 C` — Elevated Card / Header / Footer Surface (Dark Mode)
- **`charcoal-light` (`#2D3A47`):** `RGB(45, 58, 71)` | `CMYK(72, 55, 42, 40)` | `PMS 7545 C` — Body Copy (Light Mode & Print)
- **`silver` (`#C0C0C0`):** `RGB(192, 192, 192)` | `CMYK(0, 0, 0, 25)` | `PMS 877 C` — Primary Headlines & Left Bars (Dark Mode) / Portrait Borders
- **`silver-light` (`#E0E0E0`):** `RGB(224, 224, 224)` | `CMYK(0, 0, 0, 12)` — `0.8pt` / `1px` Card Borders & Dividers
- **`silver-dark` (`#A0A0A0` Web / `#8C8E91` Print):** `CMYK(0, 0, 0, 45)` — Muted Labels, Kickers & Dark Mode Body Copy

### 2.2 Digital Product Dual-Mode Pairings (`lokeshchanana.com`)
When building or modifying web/digital UI components, always support both Light Mode and Dark Mode (`darkMode: 'class'`):
- **Page Canvas:** `bg-ivory dark:bg-charcoal text-charcoal dark:text-silver transition-colors duration-300`
- **Elevated Card / Section / Footer:** `bg-white dark:bg-charcoal-dark border border-silver/30 dark:border-silver/20`
- **Signature Callout Box:** `bg-white dark:bg-charcoal-dark p-6 border border-silver/30 border-l-4 border-l-charcoal dark:border-l-silver`
- **Headlines:** `font-serif font-bold text-charcoal dark:text-silver`
- **Body Copy:** `font-sans text-charcoal-light dark:text-silver-dark`
- **Primary CTA Button:** `bg-charcoal hover:bg-charcoal-light dark:bg-silver dark:hover:bg-white text-ivory dark:text-charcoal text-xs font-bold uppercase tracking-widest`
- **Outlined CTA Button:** `border border-charcoal dark:border-silver text-charcoal dark:text-silver hover:bg-charcoal hover:text-ivory dark:hover:bg-silver dark:hover:text-charcoal`
- **Form Inputs:** `bg-ivory dark:bg-charcoal border-b border-silver/50 dark:border-silver/30 text-charcoal dark:text-silver focus:border-charcoal dark:focus:border-silver`

---

## 3. Typography & Hierarchy
- **Display & Headline Serif:** `Playfair Display` (`PF-Bold`, `PF-Semi`, `PF-Reg`, `PF-Ital`). Used for all H1/H2/H3 titles, italic sub-lines, square number badges (`01`, `02`), and page numbers.
- **UI, Kicker & Body Sans:** `Plus Jakarta Sans` (`PJS-Reg`, `PJS-Med`, `PJS-Semi`, `PJS-Bold`, `PJS-Extra`). Used for uppercase tracked kickers (`0.15em–0.20em`), body paragraphs, checklists, and metadata.

---

## 4. Signature Layout & Photography Rules (From the Classic Maintenance Guide)
1. **Top Crown & Margins:** Start every print page/flyer with a `6pt` solid `#1F2933` Charcoal top crown bar on a `#FAF8F5` Ivory canvas (`36pt` / `0.5"` margins).
2. **Outlined Kicker Pill:** `#FFFFFF` fill, `0.8pt` `#E0E0E0` border, `7.5pt` `Plus Jakarta Sans Bold` uppercase (`draw_kicker_badge()`).
3. **Numbered Content Cards:** `#FFFFFF` fill, `0.8pt` `#E0E0E0` border, **`3.5pt` solid `#1F2933` Charcoal left accent bar**, and a `22×22pt` `#FAF8F5` Ivory square number badge in `Playfair Display Bold` (`draw_numbered_card()`).
4. **Logo Alpha-Mask Rendering:** Never render `lc-logo.png` or `real-logo.png` inside opaque rectangular boxes. Always use `insert_logo()` from `brand_toolkit.py` to extract the alpha mask and composite pure `#1F2933` Charcoal (on Ivory/White) or `#FAF8F5` Ivory (on Charcoal).
5. **Relatable Puget Sound Photography & Grading:** Feature authentic Greater Seattle suburban homes (2000s Craftsman in Renton/Puyallup, Split-Levels in Shoreline, NW Contemporary cedar homes in Redmond, single-story patio homes in Des Moines) graded with `editorial_grade(im, sat=0.72, contrast=1.05)` (`72%` saturation + `16%` `#FAF8F5` Ivory / `#1F2933` Charcoal split-tone blend).
