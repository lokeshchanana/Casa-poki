#!/usr/bin/env python3
"""
Generate the 8-Page Visual Brand & Design Guidelines Book PDF
for Lokesh Chanana (Loki) — Real Broker LLC.
Uses the reusable brand_toolkit module from .agents/skills/loki-brand-design/scripts/brand_toolkit.py.
"""

import os
import sys
import pymupdf

SKILL_SCRIPTS = "/home/lokesh/Casa-poki/.agents/skills/loki-brand-design/scripts"
sys.path.insert(0, SKILL_SCRIPTS)

from brand_toolkit import (
    PAGE_W,
    PAGE_H,
    IVORY,
    IVORY_255,
    IVORY_DARK,
    IVORY_DARK_255,
    WHITE,
    WHITE_255,
    CHARCOAL,
    CHARCOAL_255,
    CHARCOAL_DARK,
    CHARCOAL_DARK_255,
    CHARCOAL_LIGHT,
    SILVER,
    SILVER_DARK,
    SILVER_LIGHT,
    EMAIL_NAVY,
    EMAIL_CYAN,
    EMAIL_SKY,
    PUBLIC_DIR,
    register_fonts,
    paint_ivory_canvas,
    add_text,
    insert_editorial_photo,
    insert_logo,
    draw_kicker_badge,
    draw_running_chrome,
    draw_section_title,
    draw_numbered_card,
)

CLASSIC_DIR = "/tmp/guide_assets_classic"
OUT_PDF = "/home/lokesh/Casa-poki/agents/assets/Lokesh_Chanana_Brand_Guidelines.pdf"


def build_page_01_cover(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    paint_ivory_canvas(page)

    # 1. Top Crown Bar (6pt solid Charcoal)
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 6), color=None, fill=CHARCOAL)

    # 2. Co-branded Header Bar
    insert_logo(page, (36, 18, 86, 62), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=IVORY_255, target_rgb=CHARCOAL_255)
    add_text(page, (94, 24, 340, 42), "LOKESH CHANANA", font="PF-Bold", size=11.0, color=CHARCOAL)
    add_text(page, (94, 39, 360, 54), "BRAND & MARKETING DESIGN SYSTEM  •  V2.0", font="PJS-Semi", size=6.8, color=CHARCOAL_LIGHT)
    insert_logo(page, (PAGE_W - 110, 24, PAGE_W - 36, 54), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=IVORY_255, target_rgb=CHARCOAL_255, is_real_logo=True)
    page.draw_line(pymupdf.Point(36, 68), pymupdf.Point(PAGE_W - 36, 68), color=SILVER_LIGHT, width=0.8)

    # 3. Kicker + Editorial Cover Title
    draw_kicker_badge(page, 0, 80, "OFFICIAL BRAND STYLE GUIDE  •  ONLINE & OFFLINE", align_center=True)
    add_text(
        page,
        (36, 102, PAGE_W - 36, 152),
        "Master Brand & Design",
        font="PF-Bold",
        size=28.0,
        color=CHARCOAL,
        align=1,
    )
    add_text(
        page,
        (36, 136, PAGE_W - 36, 184),
        "Guidelines & Blueprints.",
        font="PF-Ital",
        size=26.0,
        color=CHARCOAL,
        align=1,
    )
    add_text(
        page,
        (64, 178, PAGE_W - 64, 214),
        "Complete visual identity, Light & Dark Mode digital architecture, print CMYK/Pantone formulas, typography scales, photo grading, and collateral templates for posters, flyers, guides, and digital media.",
        font="PJS-Reg",
        size=9.3,
        color=CHARCOAL_LIGHT,
        align=1,
        lineheight=1.35,
    )

    # 4. Main Hero + 3-Photo Triptych
    insert_editorial_photo(
        page,
        (36, 222, PAGE_W - 36, 444),
        f"{CLASSIC_DIR}/site_north.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        centering=(0.5, 0.5),
    )
    strip_y0, strip_y1 = 453, 555
    gap = 9
    col_w = (PAGE_W - 72 - gap * 2) / 3.0
    for i, fn in enumerate(["puget_spring.jpg", "puget_summer.jpg", "puget_fall.jpg"]):
        x0 = 36 + i * (col_w + gap)
        insert_editorial_photo(page, (x0, strip_y0, x0 + col_w, strip_y1), f"{CLASSIC_DIR}/{fn}", radius=2, bg_rgb=IVORY_255)

    # 5. Summary Scope Bar
    scope_rect = pymupdf.Rect(36, 568, PAGE_W - 36, 646)
    page.draw_rect(scope_rect, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    page.draw_rect(pymupdf.Rect(36, 568, 40, 646), color=None, fill=CHARCOAL)
    add_text(
        page,
        (52, 576, PAGE_W - 48, 594),
        "WHAT'S INSIDE THIS BRAND MANUAL (PAGES 01–08):",
        font="PJS-Bold",
        size=8.2,
        color=CHARCOAL,
    )
    cols = [
        ("01–02  Identity, Voice & Logos", "Positioning, copywriting formulas, WA legal compliance & alpha-mask logo rules."),
        ("03–04  Colors & Light/Dark UI", "Print CMYK/Pantone swatches + website Light Mode vs. Dark Mode token matrix."),
        ("05–06  Type & Photo Grading", "Playfair Display + Plus Jakarta Sans scales & 72% saturation split-tone pipeline."),
        ("07–08  Print & Digital Blueprints", "Exact specs for 8.5×11 flyers, 6×9 postcards, 18×24 signs, carousels & emails."),
    ]
    cw = (PAGE_W - 96) / 2.0
    for idx, (ct, cb) in enumerate(cols):
        r_i, c_i = divmod(idx, 2)
        cx = 52 + c_i * (cw + 12)
        cy = 596 + r_i * 24
        add_text(page, (cx, cy, cx + cw, cy + 12), f"•  {ct}:", font="PJS-Bold", size=7.8, color=CHARCOAL)
        add_text(page, (cx, cy + 10, cx + cw, cy + 23), f"   {cb}", font="PJS-Reg", size=7.3, color=CHARCOAL_LIGHT)

    # 6. Dark Charcoal Agent Footer Banner
    foot = pymupdf.Rect(36, 658, PAGE_W - 36, 754)
    page.draw_rect(foot, color=None, fill=CHARCOAL)
    page.draw_rect(pymupdf.Rect(36, 658, PAGE_W - 36, 660.5), color=None, fill=SILVER)
    insert_editorial_photo(
        page,
        (50, 672, 114, 740),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=2,
        bg_rgb=CHARCOAL_255,
        centering=(0.5, 0.22),
        grade=False,
        border_rgb=(192, 192, 192),
        border_px=3,
    )
    add_text(page, (128, 673, 420, 696), "Lokesh Chanana (Loki)", font="PF-Bold", size=15.0, color=IVORY)
    add_text(page, (128, 695, 430, 710), "REALTOR®  •  REAL BROKER LLC (WA LIC #26006634)  •  GREATER SEATTLE", font="PJS-Semi", size=7.5, color=SILVER)
    add_text(page, (128, 714, 430, 734), "(801) 860-1052   •   lokesh@lokeshchanana.com   •   lokeshchanana.com", font="PJS-Med", size=8.8, color=IVORY)
    insert_logo(page, (465, 668, 558, 710), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=CHARCOAL_255, target_rgb=IVORY_255)
    insert_logo(page, (472, 714, 552, 740), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=CHARCOAL_255, target_rgb=IVORY_255, is_real_logo=True)


def build_page_02_identity_logos(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 2, "BRAND FOUNDATION, VOICE & LOGO SYSTEM")

    y = draw_section_title(
        page,
        46,
        "SECTION 01  •  IDENTITY, VOICE & LOGOS",
        "Brand Essence, Voice & Co-Branding",
        "Every marketing touchpoint—from an open house flyer in Renton to a post-close email or website page—must project warm neighborly trust paired with architectural editorial precision.",
    )

    cards = [
        (
            "Brand Positioning: Approachable PNW Editorial",
            "We serve everyday Greater Seattle & Puget Sound buyers, sellers, and homeowners ($550k–$1.1M residential neighborhoods across Renton, Puyallup, Des Moines, Redmond, Shoreline, and Eastside/Seattle). Our visual design elevates everyday suburban homes with timeless editorial polish—never cold, intimidating, or overly corporate.",
        ),
        (
            "Brand Voice & Tone: Trusted Advisor & Neighbor",
            "Write like a knowledgeable friend who fiercely protects the client's wallet, comfort, and peace of mind. Use warm, conversational openings, clear action-oriented card headings, and low-pressure invitations ('I'm only a phone call away—here for you beyond the sale'). Never use pushy all-caps sales clichés.",
        ),
        (
            "Mandatory WA State (RCW 18.85) & Real Broker Co-Branding",
            "All print and digital advertising must clearly display 'Lokesh Chanana (Loki)', 'REALTOR®', and 'Real Broker LLC' (WA License #26006634). On multi-page guides, postcards, and website footers, include the Equal Housing Opportunity & Fair Housing Act disclosure.",
        ),
    ]
    cy = y + 4
    for idx, (ct, cb) in enumerate(cards, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + 76), idx, ct, cb)
        cy += 84

    # Logo System Showcase (Light Surface vs Dark Surface)
    add_text(page, (36, cy + 4, PAGE_W - 36, cy + 24), "Logo Alpha-Mask Rendering Rules (Light Mode vs. Dark Mode)", font="PF-Bold", size=14.0, color=CHARCOAL)
    add_text(
        page,
        (36, cy + 23, PAGE_W - 36, cy + 52),
        "CRITICAL RULE: Never place lc-logo.png or real-logo.png inside opaque white or black rectangular boxes. Always extract the alpha channel and composite pure Charcoal (#1F2933) ink on light surfaces or Warm Ivory (#FAF8F5) ink on dark surfaces.",
        font="PJS-Reg",
        size=8.8,
        color=CHARCOAL_LIGHT,
    )

    box_y = cy + 56
    col_w = (PAGE_W - 72 - 14) / 2.0

    # Left: Light Mode Logo Specimen
    l_rect = pymupdf.Rect(36, box_y, 36 + col_w, box_y + 132)
    page.draw_rect(l_rect, color=SILVER_LIGHT, fill=IVORY, width=1.0)
    page.draw_rect(pymupdf.Rect(l_rect.x0, l_rect.y0, l_rect.x1, l_rect.y0 + 22), color=None, fill=WHITE)
    add_text(page, (l_rect.x0 + 10, l_rect.y0 + 5, l_rect.x1 - 10, l_rect.y0 + 20), "LIGHT SURFACES (#FAF8F5 IVORY / #FFFFFF WHITE)", font="PJS-Bold", size=7.5, color=CHARCOAL)
    insert_logo(page, (l_rect.x0 + 22, l_rect.y0 + 34, l_rect.x0 + 122, l_rect.y0 + 96), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=IVORY_255, target_rgb=CHARCOAL_255)
    insert_logo(page, (l_rect.x0 + 142, l_rect.y0 + 46, l_rect.x1 - 22, l_rect.y0 + 86), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=IVORY_255, target_rgb=CHARCOAL_255, is_real_logo=True)
    add_text(page, (l_rect.x0 + 12, l_rect.y0 + 104, l_rect.x1 - 12, l_rect.y1 - 6), "Ink: Architectural Charcoal #1F2933  •  Min Print Width: 0.75 in (54pt)", font="PJS-Med", size=7.8, color=CHARCOAL_LIGHT, align=1)

    # Right: Dark Mode Logo Specimen
    r_rect = pymupdf.Rect(36 + col_w + 14, box_y, PAGE_W - 36, box_y + 132)
    page.draw_rect(r_rect, color=CHARCOAL_LIGHT, fill=CHARCOAL, width=1.0)
    page.draw_rect(pymupdf.Rect(r_rect.x0, r_rect.y0, r_rect.x1, r_rect.y0 + 22), color=None, fill=CHARCOAL_DARK)
    add_text(page, (r_rect.x0 + 10, r_rect.y0 + 5, r_rect.x1 - 10, r_rect.y0 + 20), "DARK SURFACES (#1F2933 CHARCOAL / #151C23 DARK)", font="PJS-Bold", size=7.5, color=IVORY)
    insert_logo(page, (r_rect.x0 + 22, r_rect.y0 + 34, r_rect.x0 + 122, r_rect.y0 + 96), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=CHARCOAL_255, target_rgb=IVORY_255)
    insert_logo(page, (r_rect.x0 + 142, r_rect.y0 + 46, r_rect.x1 - 22, r_rect.y0 + 86), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=CHARCOAL_255, target_rgb=IVORY_255, is_real_logo=True)
    add_text(page, (r_rect.x0 + 12, r_rect.y0 + 104, r_rect.x1 - 12, r_rect.y1 - 6), "Ink: Warm Ivory #FAF8F5 (Web CSS: dark:invert)  •  Clear Space: 25% H", font="PJS-Med", size=7.8, color=SILVER, align=1)

    # Copywriting Quick Table at bottom
    t_y = box_y + 144
    t_box = pymupdf.Rect(36, t_y, PAGE_W - 36, 742)
    page.draw_rect(t_box, color=SILVER_LIGHT, fill=CHARCOAL, width=0.8)
    add_text(page, (50, t_y + 10, PAGE_W - 50, t_y + 28), "Headline & Copywriting Formulas", font="PF-Bold", size=12.5, color=IVORY)
    formulas = [
        ("KICKER PILL:", "2–4 words, ALL CAPS, tracked +0.15em ('GREATER SEATTLE SPECIALISTS', 'OPEN HOUSE • RENTON')"),
        ("DISPLAY HEADLINE:", "Playfair Display Bold line 1 + Italic line 2 ('Dedicated, Proactive / Home Maintenance Guide.')"),
        ("CARD HEADING:", "3–6 words, action-oriented benefit ('Save Money Over Time', 'Offer Engineering', 'Boost Your Comfort')"),
        ("WARM CTA SIGN-OFF:", "'If you ever have questions or need recommendations for reliable service pros, I am only a phone call away!'"),
    ]
    for i, (ft, fb) in enumerate(formulas):
        r_i, c_i = divmod(i, 2)
        fx = 50 + c_i * (col_w - 4 + 12)
        fy = t_y + 32 + r_i * 42
        page.draw_rect(pymupdf.Rect(fx, fy, fx + col_w - 8, fy + 36), color=CHARCOAL_LIGHT, fill=CHARCOAL_DARK, width=0.6)
        add_text(page, (fx + 8, fy + 4, fx + col_w - 14, fy + 16), ft, font="PJS-Bold", size=7.8, color=IVORY)
        add_text(page, (fx + 8, fy + 15, fx + col_w - 14, fy + 34), fb, font="PJS-Reg", size=7.3, color=SILVER, lineheight=1.22)


def build_page_03_colors_print(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 3, "MASTER COLOR SYSTEM (DIGITAL & PRINT CMYK)")

    y = draw_section_title(
        page,
        46,
        "SECTION 02  •  COLOR SPECIFICATIONS",
        "Master Color Palette: Digital & Print",
        "Calibrated across glowing screens (HEX/RGB) and physical 4-color offset/digital printing (CMYK & Pantone PMS). Use Rich Charcoal (C:78 M:64 Y:52 K:62) in print—never 100% K alone.",
    )

    swatches = [
        ("Warm Ivory", "ivory (DEFAULT)", "#FAF8F5", "250, 248, 245", "C:0 M:1 Y:3 K:2", "PMS Warm Gray 1 C (10%)", "Primary Print & Light Mode Canvas", IVORY, CHARCOAL),
        ("Ivory Dark", "ivory-dark", "#E5E1DB", "229, 225, 219", "C:0 M:2 Y:6 K:10", "PMS Warm Gray 2 C", "Secondary Surface / Divider Tint", IVORY_DARK, CHARCOAL),
        ("Crisp White", "white", "#FFFFFF", "255, 255, 255", "C:0 M:0 Y:0 K:0", "Paper White", "Elevated Content Cards (Light/Print)", WHITE, CHARCOAL),
        ("Arch. Charcoal", "charcoal (DEFAULT)", "#1F2933", "31, 41, 51", "C:78 M:64 Y:52 K:62", "PMS 432 C / 2379 C", "Primary Ink, Left Bars & Dark Canvas", CHARCOAL, IVORY),
        ("Charcoal Dark", "charcoal-dark", "#151C23", "21, 28, 35", "C:82 M:68 Y:55 K:74", "PMS 433 C", "Dark Mode Cards, Header & Footer", CHARCOAL_DARK, IVORY),
        ("Charcoal Light", "charcoal-light", "#2D3A47", "45, 58, 71", "C:72 M:55 Y:42 K:40", "PMS 7545 C", "Body Copy & Subtitles (Light/Print)", CHARCOAL_LIGHT, IVORY),
        ("Metallic Silver", "silver (DEFAULT)", "#C0C0C0", "192, 192, 192", "C:0 M:0 Y:0 K:25", "PMS 877 C / Cool Gray 4", "Dark Mode Headlines & Portrait Frame", SILVER, CHARCOAL),
        ("Silver Light", "silver-light", "#E0E0E0", "224, 224, 224", "C:0 M:0 Y:0 K:12", "PMS Cool Gray 2 C", "0.8pt / 1px Hairline Borders & Rules", SILVER_LIGHT, CHARCOAL),
        ("Silver Dark", "silver-dark", "#A0A0A0 / #8C8E91", "160,160,160", "C:0 M:0 Y:0 K:45", "PMS Cool Gray 7 C", "Muted Kickers, Captions & Dark Body", SILVER_DARK, IVORY),
    ]

    gap_x = 10
    gap_y = 10
    card_w = (PAGE_W - 72 - gap_x * 2) / 3.0
    card_h = 126
    start_y = y + 4

    for idx, (name, token, hex_v, rgb_v, cmyk_v, pms_v, role, fill_col, txt_col) in enumerate(swatches):
        r_i, c_i = divmod(idx, 3)
        cx = 36 + c_i * (card_w + gap_x)
        cy = start_y + r_i * (card_h + gap_y)

        card = pymupdf.Rect(cx, cy, cx + card_w, cy + card_h)
        page.draw_rect(card, color=SILVER_LIGHT, fill=WHITE, width=0.8)

        # Top color swatch block
        sw_rect = pymupdf.Rect(cx, cy, cx + card_w, cy + 46)
        page.draw_rect(sw_rect, color=SILVER_LIGHT, fill=fill_col, width=0.6)
        add_text(page, (cx + 8, cy + 8, cx + card_w - 8, cy + 25), name, font="PF-Bold", size=11.0, color=txt_col)
        add_text(page, (cx + 8, cy + 25, cx + card_w - 8, cy + 42), f"{hex_v}   •   {token}", font="PJS-Bold", size=7.3, color=txt_col)

        # Specs below
        add_text(page, (cx + 8, cy + 52, cx + card_w - 8, cy + 66), f"RGB: {rgb_v}", font="PJS-Semi", size=7.6, color=CHARCOAL)
        add_text(page, (cx + 8, cy + 65, cx + card_w - 8, cy + 79), f"CMYK: {cmyk_v}", font="PJS-Semi", size=7.6, color=CHARCOAL)
        add_text(page, (cx + 8, cy + 78, cx + card_w - 8, cy + 92), f"Pantone: {pms_v}", font="PJS-Med", size=7.4, color=CHARCOAL_LIGHT)
        add_text(page, (cx + 8, cy + 94, cx + card_w - 8, cy + 122), f"Use: {role}", font="PJS-Reg", size=7.4, color=CHARCOAL_LIGHT, lineheight=1.22)

    # Bottom Section: Print Paper Stock & Transactional Email Palette
    bot_y = start_y + 3 * (card_h + gap_y) + 4
    p_box = pymupdf.Rect(36, bot_y, PAGE_W - 36, 742)
    page.draw_rect(p_box, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    page.draw_rect(pymupdf.Rect(36, bot_y, 40, 742), color=None, fill=CHARCOAL)

    add_text(page, (50, bot_y + 10, PAGE_W - 48, bot_y + 28), "Print Paper Stock Standards & Transactional Email Accent Palette", font="PF-Bold", size=12.5, color=CHARCOAL)
    stocks = [
        ("• Property Flyers (8.5\"×11\"):", "100 lb Matte Text or 100 lb Silk/Satin Text (148 gsm) — zero glare under open-house lighting."),
        ("• Multi-Page Client Guides:", "Cover: 100 lb Uncoated Cover (270 gsm Mohawk Superfine Eggshell); Interior: 80 lb Uncoated Text (118 gsm)."),
        ("• Direct Mail Postcards (6\"×9\" / 6\"×11\"):", "16 pt C2S Matte Cardstock with Satin Aqueous Coating on front; uncoated writable/inkjet back for USPS barcode zone."),
        ("• Yard Signs & Riders (18\"×24\" / 24\"×36\"):", "3mm Aluminum Composite (Dibond) with matte anti-glare laminate for listings; 4mm Coroplast for Open House A-frames."),
        ("• HTML Email Header Palette (Brevo):", "Slate Navy #0F172A header background + Electric Cyan #06B6D4 bottom border + Sky #38BDF8 uppercase kicker text."),
    ]
    sy = bot_y + 32
    for st, sb in stocks:
        add_text(page, (50, sy, 235, sy + 16), st, font="PJS-Bold", size=8.0, color=CHARCOAL)
        add_text(page, (232, sy, PAGE_W - 46, sy + 18), sb, font="PJS-Reg", size=8.0, color=CHARCOAL_LIGHT)
        sy += 19


def build_page_04_digital_light_dark(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 4, "DIGITAL PRODUCT ARCHITECTURE: LIGHT & DARK MODE")

    y = draw_section_title(
        page,
        46,
        "SECTION 03  •  WEBSITE & DIGITAL UI SYSTEM",
        "Dual-Mode Digital Architecture (Light & Dark)",
        "Digital products (lokeshchanana.com & web apps) use class-based theming (darkMode: 'class') synced to OS prefers-color-scheme with manual Sun/Moon toggle and 300ms color transitions.",
    )

    col_w = (PAGE_W - 72 - 14) / 2.0
    mock_y = y + 4
    mock_h = 248

    # 1. Left Mockup: LIGHT MODE UI SPECIMEN
    lm = pymupdf.Rect(36, mock_y, 36 + col_w, mock_y + mock_h)
    page.draw_rect(lm, color=SILVER_LIGHT, fill=IVORY, width=1.0)
    # Sticky Header bar
    page.draw_rect(pymupdf.Rect(lm.x0, lm.y0, lm.x1, lm.y0 + 28), color=SILVER_LIGHT, fill=WHITE, width=0.6)
    add_text(page, (lm.x0 + 10, lm.y0 + 8, lm.x1 - 10, lm.y0 + 22), "LIGHT MODE  •  bg-ivory (#FAF8F5)", font="PJS-Bold", size=7.8, color=CHARCOAL)
    add_text(page, (lm.x0 + 10, lm.y0 + 8, lm.x1 - 10, lm.y0 + 22), "☾ Moon (#334155)", font="PJS-Semi", size=7.4, color=CHARCOAL_LIGHT, align=2)

    # Kicker & Headline inside Light Mode
    page.draw_rect(pymupdf.Rect(lm.x0 + 12, lm.y0 + 38, lm.x0 + 148, lm.y0 + 52), color=SILVER_LIGHT, fill=IVORY, width=0.6)
    add_text(page, (lm.x0 + 16, lm.y0 + 40.5, lm.x0 + 144, lm.y0 + 51), "GREATER SEATTLE SPECIALISTS", font="PJS-Bold", size=6.5, color=CHARCOAL_LIGHT)
    add_text(page, (lm.x0 + 12, lm.y0 + 56, lm.x1 - 12, lm.y0 + 78), "Dedicated Service.", font="PF-Bold", size=15.0, color=CHARCOAL)
    add_text(page, (lm.x0 + 12, lm.y0 + 76, lm.x1 - 12, lm.y0 + 92), "Headlines in #1F2933 Charcoal; body copy in #2D3A47.", font="PJS-Reg", size=8.0, color=CHARCOAL_LIGHT)

    # Signature Callout Card inside Light Mode
    lc = pymupdf.Rect(lm.x0 + 12, lm.y0 + 98, lm.x1 - 12, lm.y0 + 152)
    page.draw_rect(lc, color=SILVER_LIGHT, fill=WHITE, width=0.7)
    page.draw_rect(pymupdf.Rect(lc.x0, lc.y0, lc.x0 + 3.5, lc.y1), color=None, fill=CHARCOAL)
    add_text(page, (lc.x0 + 12, lc.y0 + 7, lc.x1 - 8, lc.y0 + 22), "Elevated Card: bg-white (#FFFFFF)", font="PF-Bold", size=9.8, color=CHARCOAL)
    add_text(page, (lc.x0 + 12, lc.y0 + 23, lc.x1 - 8, lc.y1 - 6), "border-silver/30 + border-l-4 border-l-charcoal (#1F2933).", font="PJS-Reg", size=7.8, color=CHARCOAL_LIGHT)

    # Minimalist Form Input & Primary Button in Light Mode
    add_text(page, (lm.x0 + 12, lm.y0 + 160, lm.x1 - 12, lm.y0 + 172), "FULL NAME * (text-charcoal)", font="PJS-Bold", size=6.8, color=CHARCOAL)
    page.draw_line(pymupdf.Point(lm.x0 + 12, lm.y0 + 188), pymupdf.Point(lm.x1 - 12, lm.y0 + 188), color=CHARCOAL, width=0.9)
    add_text(page, (lm.x0 + 12, lm.y0 + 174, lm.x1 - 12, lm.y0 + 187), "Jane Doe (bg-ivory border-b border-silver/50)", font="PJS-Reg", size=7.8, color=CHARCOAL_LIGHT)

    l_btn = pymupdf.Rect(lm.x0 + 12, lm.y0 + 200, lm.x1 - 12, lm.y0 + 228)
    page.draw_rect(l_btn, color=None, fill=CHARCOAL)
    add_text(page, (l_btn.x0, l_btn.y0 + 8, l_btn.x1, l_btn.y1), "PRIMARY CTA  •  bg-charcoal text-ivory", font="PJS-Bold", size=8.0, color=IVORY, align=1)

    # 2. Right Mockup: DARK MODE UI SPECIMEN
    dm = pymupdf.Rect(36 + col_w + 14, mock_y, PAGE_W - 36, mock_y + mock_h)
    page.draw_rect(dm, color=CHARCOAL_LIGHT, fill=CHARCOAL, width=1.0)
    # Sticky Header bar
    page.draw_rect(pymupdf.Rect(dm.x0, dm.y0, dm.x1, dm.y0 + 28), color=CHARCOAL_LIGHT, fill=CHARCOAL_DARK, width=0.6)
    add_text(page, (dm.x0 + 10, dm.y0 + 8, dm.x1 - 10, dm.y0 + 22), "DARK MODE  •  dark:bg-charcoal (#1F2933)", font="PJS-Bold", size=7.8, color=SILVER)
    add_text(page, (dm.x0 + 10, dm.y0 + 8, dm.x1 - 10, dm.y0 + 22), "☀ Sun (#FBBF24)", font="PJS-Semi", size=7.4, color=SILVER_DARK, align=2)

    # Kicker & Headline inside Dark Mode
    page.draw_rect(pymupdf.Rect(dm.x0 + 12, dm.y0 + 38, dm.x0 + 148, dm.y0 + 52), color=CHARCOAL_LIGHT, fill=CHARCOAL, width=0.6)
    add_text(page, (dm.x0 + 16, dm.y0 + 40.5, dm.x0 + 144, dm.y0 + 51), "GREATER SEATTLE SPECIALISTS", font="PJS-Bold", size=6.5, color=SILVER_DARK)
    add_text(page, (dm.x0 + 12, dm.y0 + 56, dm.x1 - 12, dm.y0 + 78), "Dedicated Service.", font="PF-Bold", size=15.0, color=SILVER)
    add_text(page, (dm.x0 + 12, dm.y0 + 76, dm.x1 - 12, dm.y0 + 92), "Headlines in #C0C0C0 Silver; body in #A0A0A0 Silver-Dark.", font="PJS-Reg", size=8.0, color=SILVER_DARK)

    # Signature Callout Card inside Dark Mode
    dc = pymupdf.Rect(dm.x0 + 12, dm.y0 + 98, dm.x1 - 12, dm.y0 + 152)
    page.draw_rect(dc, color=CHARCOAL_LIGHT, fill=CHARCOAL_DARK, width=0.7)
    page.draw_rect(pymupdf.Rect(dc.x0, dc.y0, dc.x0 + 3.5, dc.y1), color=None, fill=SILVER)
    add_text(page, (dc.x0 + 12, dc.y0 + 7, dc.x1 - 8, dc.y0 + 22), "Elevated Card: dark:bg-charcoal-dark (#151C23)", font="PF-Bold", size=9.8, color=SILVER)
    add_text(page, (dc.x0 + 12, dc.y0 + 23, dc.x1 - 8, dc.y1 - 6), "dark:border-silver/20 + border-l-4 dark:border-l-silver.", font="PJS-Reg", size=7.8, color=SILVER_DARK)

    # Minimalist Form Input & Primary Button in Dark Mode
    add_text(page, (dm.x0 + 12, dm.y0 + 160, dm.x1 - 12, dm.y0 + 172), "FULL NAME * (dark:text-silver-dark)", font="PJS-Bold", size=6.8, color=SILVER_DARK)
    page.draw_line(pymupdf.Point(dm.x0 + 12, dm.y0 + 188), pymupdf.Point(dm.x1 - 12, dm.y0 + 188), color=SILVER, width=0.9)
    add_text(page, (dm.x0 + 12, dm.y0 + 174, dm.x1 - 12, dm.y0 + 187), "Jane Doe (dark:bg-charcoal border-b dark:border-silver/30)", font="PJS-Reg", size=7.8, color=SILVER)

    d_btn = pymupdf.Rect(dm.x0 + 12, dm.y0 + 200, dm.x1 - 12, dm.y0 + 228)
    page.draw_rect(d_btn, color=None, fill=SILVER)
    add_text(page, (d_btn.x0, d_btn.y0 + 8, d_btn.x1, d_btn.y1), "PRIMARY CTA  •  dark:bg-silver dark:text-charcoal", font="PJS-Bold", size=8.0, color=CHARCOAL, align=1)

    # 3. Semantic Mapping Table Below
    tb_y = mock_y + mock_h + 14
    add_text(page, (36, tb_y, PAGE_W - 36, tb_y + 20), "Website Light Mode vs. Dark Mode Semantic Token & Tailwind Class Matrix", font="PF-Bold", size=13.5, color=CHARCOAL)

    rows = [
        ("UI Component / Role", "Light Mode Token", "Dark Mode Token", "Mandatory Tailwind CSS Class Pairing"),
        ("Primary Page Canvas", "ivory (#FAF8F5)", "charcoal (#1F2933)", "bg-ivory dark:bg-charcoal transition-colors duration-300"),
        ("Elevated Section / Card / Footer", "white (#FFFFFF)", "charcoal-dark (#151C23)", "bg-white dark:bg-charcoal-dark border-silver/30 dark:border-silver/20"),
        ("Sticky Scrolled Glass Header", "white/95", "charcoal-dark/95", "bg-white/95 dark:bg-charcoal-dark/95 backdrop-blur-md"),
        ("Primary Headlines (H1–H3)", "charcoal (#1F2933)", "silver (#C0C0C0)", "font-serif font-bold text-charcoal dark:text-silver"),
        ("Body Copy & Nav Links", "charcoal-light (#2D3A47)", "silver-dark (#A0A0A0)", "font-sans text-charcoal-light dark:text-silver-dark"),
        ("Callout Box Left Bar (4px)", "charcoal (#1F2933)", "silver (#C0C0C0)", "border-l-4 border-l-charcoal dark:border-l-silver"),
        ("Primary Solid Button", "bg-charcoal text-ivory", "bg-silver text-charcoal", "bg-charcoal hover:bg-charcoal-light dark:bg-silver dark:hover:bg-white"),
        ("Secondary Outlined Button", "border-charcoal", "border-silver", "border border-charcoal dark:border-silver hover:bg-charcoal"),
        ("Hero Image Bottom Fade", "to-ivory (#FAF8F5)", "to-charcoal (#1F2933)", "bg-gradient-to-b from-transparent to-ivory dark:to-charcoal"),
        ("Brokerage Logo Inversion", "Native Black on White", "CSS Inverted White", "real-logo.png -> dark:invert  |  lakhani-logo.png -> invert dark:invert-0"),
    ]

    ry = tb_y + 24
    rh = 24.5
    for idx, (c1, c2, c3, c4) in enumerate(rows):
        is_hdr = idx == 0
        bg_c = CHARCOAL if is_hdr else (WHITE if idx % 2 == 1 else IVORY_DARK)
        fg_c = IVORY if is_hdr else CHARCOAL
        fg_c2 = IVORY if is_hdr else CHARCOAL_LIGHT
        page.draw_rect(pymupdf.Rect(36, ry, PAGE_W - 36, ry + rh), color=SILVER_LIGHT, fill=bg_c, width=0.5)
        f_name = "PJS-Bold" if is_hdr else "PJS-Semi"
        f_body = "PJS-Bold" if is_hdr else "PJS-Reg"
        add_text(page, (42, ry + 6, 175, ry + rh), c1, font=f_name, size=7.6, color=fg_c)
        add_text(page, (178, ry + 6, 275, ry + rh), c2, font=f_body, size=7.4, color=fg_c2)
        add_text(page, (278, ry + 6, 382, ry + rh), c3, font=f_body, size=7.4, color=fg_c2)
        add_text(page, (385, ry + 6, PAGE_W - 40, ry + rh), c4, font=f_body, size=7.2, color=fg_c)
        ry += rh


def build_page_05_typography(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 5, "TYPOGRAPHY & EDITORIAL HIERARCHY")

    y = draw_section_title(
        page,
        46,
        "SECTION 04  •  TYPOGRAPHY SYSTEM",
        "Editorial Serif + Geometric Sans Pairing",
        "Playfair Display establishes architectural authority on headlines and numbered badges, while Plus Jakarta Sans delivers crisp legibility across uppercase kickers, body paragraphs, checklists, and UI controls.",
    )

    col_w = (PAGE_W - 72 - 14) / 2.0
    spec_y = y + 4

    # Left: Playfair Display Specimen Card
    pf_card = pymupdf.Rect(36, spec_y, 36 + col_w, spec_y + 188)
    page.draw_rect(pf_card, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    page.draw_rect(pymupdf.Rect(pf_card.x0, pf_card.y0, pf_card.x0 + 4, pf_card.y1), color=None, fill=CHARCOAL)
    add_text(page, (pf_card.x0 + 14, pf_card.y0 + 10, pf_card.x1 - 12, pf_card.y0 + 24), "PRIMARY DISPLAY & HEADLINE SERIF", font="PJS-Bold", size=7.4, color=SILVER_DARK)
    add_text(page, (pf_card.x0 + 14, pf_card.y0 + 24, pf_card.x1 - 12, pf_card.y0 + 54), "Playfair Display", font="PF-Bold", size=22.0, color=CHARCOAL)
    add_text(page, (pf_card.x0 + 14, pf_card.y0 + 54, pf_card.x1 - 12, pf_card.y0 + 78), "Aa Bb Cc Dd Ee Ff Gg Hh Ii Jj Kk Ll Mm Nn Oo Pp Qq Rr Ss Tt Uu Vv Ww Xx Yy Zz  0123456789", font="PF-Reg", size=9.2, color=CHARCOAL_LIGHT, lineheight=1.3)
    add_text(page, (pf_card.x0 + 14, pf_card.y0 + 92, pf_card.x1 - 12, pf_card.y0 + 110), "• Playfair Display Bold (700) — Primary Headlines & Badges", font="PF-Bold", size=9.2, color=CHARCOAL)
    add_text(page, (pf_card.x0 + 14, pf_card.y0 + 110, pf_card.x1 - 12, pf_card.y0 + 128), "• Playfair Display SemiBold (600) — Sub-sections", font="PF-Semi", size=9.2, color=CHARCOAL)
    add_text(page, (pf_card.x0 + 14, pf_card.y0 + 128, pf_card.x1 - 12, pf_card.y0 + 146), "• Playfair Display Italic (400i) — Cover Sub-lines & Running Chrome", font="PF-Ital", size=9.5, color=CHARCOAL_LIGHT)
    add_text(page, (pf_card.x0 + 14, pf_card.y0 + 150, pf_card.x1 - 12, pf_card.y1 - 8), "Web Fallback: 'Playfair Display', 'Palatino Linotype', Georgia, serif", font="PJS-Med", size=7.5, color=SILVER_DARK)

    # Right: Plus Jakarta Sans Specimen Card
    pjs_card = pymupdf.Rect(36 + col_w + 14, spec_y, PAGE_W - 36, spec_y + 188)
    page.draw_rect(pjs_card, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    page.draw_rect(pymupdf.Rect(pjs_card.x0, pjs_card.y0, pjs_card.x0 + 4, pjs_card.y1), color=None, fill=CHARCOAL)
    add_text(page, (pjs_card.x0 + 14, pjs_card.y0 + 10, pjs_card.x1 - 12, pjs_card.y0 + 24), "PRIMARY BODY, KICKER & UI SANS-SERIF", font="PJS-Bold", size=7.4, color=SILVER_DARK)
    add_text(page, (pjs_card.x0 + 14, pjs_card.y0 + 24, pjs_card.x1 - 12, pjs_card.y0 + 54), "Plus Jakarta Sans", font="PJS-Bold", size=21.0, color=CHARCOAL)
    add_text(page, (pjs_card.x0 + 14, pjs_card.y0 + 54, pjs_card.x1 - 12, pjs_card.y0 + 78), "Aa Bb Cc Dd Ee Ff Gg Hh Ii Jj Kk Ll Mm Nn Oo Pp Qq Rr Ss Tt Uu Vv Ww Xx Yy Zz  0123456789", font="PJS-Reg", size=9.0, color=CHARCOAL_LIGHT, lineheight=1.3)
    add_text(page, (pjs_card.x0 + 14, pjs_card.y0 + 92, pjs_card.x1 - 12, pjs_card.y0 + 110), "• Plus Jakarta Sans Bold (700) — ALL CAPS Kickers & CTAs", font="PJS-Bold", size=8.8, color=CHARCOAL)
    add_text(page, (pjs_card.x0 + 14, pjs_card.y0 + 110, pjs_card.x1 - 12, pjs_card.y0 + 128), "• Plus Jakarta Sans Medium (500) — Checklists & Metadata", font="PJS-Med", size=8.8, color=CHARCOAL)
    add_text(page, (pjs_card.x0 + 14, pjs_card.y0 + 128, pjs_card.x1 - 12, pjs_card.y0 + 146), "• Plus Jakarta Sans Regular (400) — Body Copy & Descriptions", font="PJS-Reg", size=8.8, color=CHARCOAL_LIGHT)
    add_text(page, (pjs_card.x0 + 14, pjs_card.y0 + 150, pjs_card.x1 - 12, pjs_card.y1 - 8), "Web/Email Fallback: 'Plus Jakarta Sans', Montserrat, system-ui, sans-serif", font="PJS-Med", size=7.5, color=SILVER_DARK)

    # Master Type Scale Table
    ty = spec_y + 204
    add_text(page, (36, ty, PAGE_W - 36, ty + 20), "Master Typography Scale (Print 8.5\"×11\", Poster 18\"×24\", and Web/Digital)", font="PF-Bold", size=13.5, color=CHARCOAL)

    scale_rows = [
        ("Hierarchy Role", "Font & Weight", "Print (8.5×11)", "Poster (18×24)", "Web / Tailwind CSS", "Line / Tracking"),
        ("Display Cover Title (H1)", "Playfair Bold + Italic", "26pt – 30pt", "72pt – 96pt", "36–60px (text-4xl lg:text-6xl)", "1.12  |  -0.01em"),
        ("Section Headline (H2)", "Playfair Bold", "21pt – 23pt", "48pt – 60pt", "30–48px (text-3xl md:text-5xl)", "1.15  |  0em"),
        ("Card Heading (H3)", "Playfair Bold", "11.5pt – 13.5pt", "28pt – 34pt", "20–24px (text-xl md:text-2xl)", "1.20  |  +0.01em"),
        ("Numbered Card Badge", "Playfair Bold", "9.2pt (in 22pt box)", "22pt", "14px (font-serif font-bold)", "1.00  |  0em"),
        ("Kicker Pill Badge", "Plus Jakarta Bold (CAPS)", "7.2pt – 7.8pt", "18pt – 22pt", "10px (text-[10px] tracking-[0.2em])", "1.00  |  +0.18em"),
        ("Section Lead / Subtitle", "Plus Jakarta Regular", "10.0pt – 10.5pt", "24pt – 28pt", "16–18px (text-base md:text-lg)", "1.36  |  0em"),
        ("Card Body Copy", "Plus Jakarta Regular", "9.2pt – 9.8pt", "20pt – 22pt", "14–16px (text-sm md:text-base)", "1.33  |  0em"),
        ("Checklist / Table Item", "Plus Jakarta Medium", "8.4pt – 8.8pt", "18pt", "13–14px (text-xs md:text-sm)", "1.25  |  0em"),
        ("Running Header / Footer", "PJS Bold / PF Italic", "7.5pt – 8.5pt", "14pt – 16pt", "10–12px (text-[10px] uppercase)", "1.20  |  +0.10em"),
    ]

    ry = ty + 24
    rh = 27.5
    for idx, (r1, r2, r3, r4, r5, r6) in enumerate(scale_rows):
        is_hdr = idx == 0
        bg_c = CHARCOAL if is_hdr else (WHITE if idx % 2 == 1 else IVORY_DARK)
        fg_c = IVORY if is_hdr else CHARCOAL
        fg_c2 = IVORY if is_hdr else CHARCOAL_LIGHT
        page.draw_rect(pymupdf.Rect(36, ry, PAGE_W - 36, ry + rh), color=SILVER_LIGHT, fill=bg_c, width=0.5)
        fn_1 = "PJS-Bold" if is_hdr else "PJS-Semi"
        fn_2 = "PJS-Bold" if is_hdr else "PJS-Reg"
        add_text(page, (42, ry + 7, 155, ry + rh), r1, font=fn_1, size=7.6, color=fg_c)
        add_text(page, (158, ry + 7, 255, ry + rh), r2, font=fn_2, size=7.4, color=fg_c2)
        add_text(page, (258, ry + 7, 325, ry + rh), r3, font=fn_1, size=7.4, color=fg_c)
        add_text(page, (328, ry + 7, 395, ry + rh), r4, font=fn_2, size=7.4, color=fg_c2)
        add_text(page, (398, ry + 7, 505, ry + rh), r5, font=fn_2, size=7.2, color=fg_c2)
        add_text(page, (508, ry + 7, PAGE_W - 40, ry + rh), r6, font=fn_2, size=7.2, color=fg_c)
        ry += rh


def build_page_06_photography(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 6, "PHOTOGRAPHY DIRECTION & COLOR-GRADING FORMULA")

    y = draw_section_title(
        page,
        46,
        "SECTION 05  •  PHOTOGRAPHY STANDARDS",
        "Authentic Puget Sound Homes & Grading",
        "Imagery must reflect the real Greater Seattle neighborhoods our clients buy and sell in—never out-of-place tropical villas or ultra-luxury glass mansions—unified with our Warm Ivory & Charcoal split-tone grade.",
    )

    # 2x2 Photo Grid of Client Home Archetypes
    col_w = (PAGE_W - 72 - 12) / 2.0
    img_h = 122
    photos = [
        ("site_north.jpg", "01. 2000s PNW Suburban Craftsman (Renton / Puyallup)", "Greige lap & board-and-batten siding, stone-base tapered columns, 2–3 car garage, Douglas firs."),
        ("puget_spring.jpg", "02. Classic Seattle Split-Level / Daylight Rambler (Shoreline)", "Sage-olive siding over lower stone masonry, rockery wall, tucked-under garage, spring blossoms."),
        ("puget_fall.jpg", "03. 1970s/80s Eastside NW Contemporary (Redmond)", "Vertical grooved cedar siding, angled shed/gable rooflines, front porch deck, autumn maples."),
        ("arch_lighting_int.jpg", "04. Refreshed Everyday PNW Interiors & Backyards", "Honey-oak hardwood floors, stacked-stone fireplaces, white shaker kitchens, cedar-fenced yards."),
    ]

    gy = y + 4
    for idx, (fn, title, desc) in enumerate(photos):
        r_i, c_i = divmod(idx, 2)
        px = 36 + c_i * (col_w + 12)
        py = gy + r_i * (img_h + 48)
        insert_editorial_photo(page, (px, py, px + col_w, py + img_h), f"{CLASSIC_DIR}/{fn}", radius=2, bg_rgb=IVORY_255)
        card = pymupdf.Rect(px, py + img_h + 3, px + col_w, py + img_h + 41)
        page.draw_rect(card, color=SILVER_LIGHT, fill=WHITE, width=0.7)
        page.draw_rect(pymupdf.Rect(px, py + img_h + 3, px + 3, py + img_h + 41), color=None, fill=CHARCOAL)
        add_text(page, (px + 9, py + img_h + 6, px + col_w - 6, py + img_h + 20), title, font="PF-Bold", size=8.8, color=CHARCOAL)
        add_text(page, (px + 9, py + img_h + 20, px + col_w - 6, py + img_h + 39), desc, font="PJS-Reg", size=7.5, color=CHARCOAL_LIGHT, lineheight=1.2)

    # Automated Color-Grading Pipeline Spec Box
    box_y = gy + 2 * (img_h + 48) + 6
    g_box = pymupdf.Rect(36, box_y, PAGE_W - 36, 742)
    page.draw_rect(g_box, color=SILVER_LIGHT, fill=CHARCOAL, width=0.8)
    add_text(page, (50, box_y + 12, PAGE_W - 50, box_y + 32), "Automated Editorial Color-Grading Pipeline (editorial_grade in brand_toolkit.py)", font="PF-Bold", size=13.0, color=IVORY)

    steps = [
        ("STEP 1  •  SATURATION HARMONY (72%)", "Enhance color saturation to 0.72 (72%) for suburban homes so lawns, cedar fences, and oak floors feel warm and natural without neon oversaturation (use 0.58 for luxury)."),
        ("STEP 2  •  MICRO-CONTRAST (105%)", "Apply a 1.05x (105%) contrast curve to sharpen architectural siding lines, window trim, and interior woodwork."),
        ("STEP 3  •  16% IVORY/CHARCOAL SPLIT-TONE", "Map pixel luminance L so shadows blend toward Charcoal RGB(31,41,51) and highlights blend toward Warm Ivory RGB(250,248,245) at 16% opacity (Output = 0.84*Img + 0.16*Tone)."),
        ("STEP 4  •  FRAMING & BANNER OVERLAYS", "Frame photos with a 2px #D6D3CD border (2pt radius). For white serif text over checklist/hero banners, apply a vertical Charcoal gradient from 45% alpha (top) to 90% alpha (bottom)."),
    ]
    for i, (st, sb) in enumerate(steps):
        r_i, c_i = divmod(i, 2)
        sx = 50 + c_i * (col_w - 6 + 12)
        sy = box_y + 38 + r_i * 58
        page.draw_rect(pymupdf.Rect(sx, sy, sx + col_w - 8, sy + 52), color=CHARCOAL_LIGHT, fill=CHARCOAL_DARK, width=0.7)
        add_text(page, (sx + 8, sy + 5, sx + col_w - 14, sy + 18), st, font="PJS-Bold", size=7.8, color=IVORY)
        add_text(page, (sx + 8, sy + 18, sx + col_w - 14, sy + 49), sb, font="PJS-Reg", size=7.4, color=SILVER, lineheight=1.22)


def build_page_07_print_blueprints(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 7, "PRINT COLLATERAL BLUEPRINTS (FLYERS, POSTCARDS & SIGNS)")

    y = draw_section_title(
        page,
        46,
        "SECTION 06  •  OFFLINE HARD MARKETING",
        "Print Collateral Layouts & Specifications",
        "All print files must be exported at 300 DPI minimum in CMYK (or PDF/X-4 with embedded fonts) with a 0.125\" (9pt) full bleed on all four sides.",
    )

    specs = [
        (
            "Property Listing & Open House Flyers (8.5\" × 11\" Portrait)",
            "• Trim: 8.5\" × 11\" (612 × 792 pt)  |  With Bleed: 8.75\" × 11.25\"  |  Safe Margin: 0.5\" (36 pt).\n"
            "• Structure: 6pt Charcoal crown bar -> Co-branded LC + Real header -> Centered Kicker Pill + Playfair Bold Address + Specs Bar -> Main Exterior Hero (540×195pt) + 3-Photo Interior Triptych (3×174×92pt) -> 2×2 Grid of Numbered Highlight Cards (3.5pt Charcoal left bars) -> Dark Charcoal Agent Footer Banner with QR code.",
        ),
        (
            "Direct Mail Postcards — Just Listed / Just Sold / CMA (6\" × 9\" & 6\" × 11\" Landscape)",
            "• Trim: 9\" × 6\" (648 × 432 pt) or 11\" × 6\" (792 × 432 pt)  |  Bleed: 0.125\"  |  Safe Margin: 0.375\" (27 pt)  |  Stock: 16pt Matte Cardstock.\n"
            "• Front Side: Left 60% full-bleed graded property photo with Kicker Pill overlay; Right 40% Warm Ivory panel with Playfair headline, 2 numbered stat/feature cards, and bottom Charcoal agent strip.\n"
            "• Back Side (USPS EDDM Compliant): Left 52% neighborly message + 3 numbered market cards + signature; Right 48% top-right Permit Indicium (1.5\"×1.5\") and mandatory bottom-right 4.0\" × 2.25\" pure #FFFFFF White USPS Barcode & Address Clear Zone.",
        ),
        (
            "Yard Signs, Open House A-Frames & Event Posters (18\" × 24\" & 24\" × 36\")",
            "• Distance Legibility Rule: Readable from a moving car at 40–50 feet (max 4 data points; minimum 180pt+ primary headline).\n"
            "• Layout: Top 25% solid #1F2933 Charcoal band ('FOR SALE' or 'OPEN HOUSE' in #FAF8F5 Ivory Playfair Bold); Middle 50% #FAF8F5 Ivory field with 'LOKESH CHANANA (LOKI)', massive '(801) 860-1052' in Plus Jakarta ExtraBold, and 'lokeshchanana.com'; Bottom 25% co-branded LC Monogram + Real Broker LLC bar + 2.5\" QR code.",
        ),
        (
            "Multi-Page Client Guides & Presentations (8.5\" × 11\" Interactive & Print Booklets)",
            "• Follow the 22-Page Classic Home Maintenance Guide template: Cover (Page 1) -> Personal Welcome Letter with Portrait & Co-Branded Card (Page 2) -> Educational Numbered Card Sections with Running Chrome (Pages 3–15) -> Section Divider + Interactive AcroForm Checklists (Pages 16–21) -> Dark Anchor Back Cover (Page 22).",
        ),
    ]

    cy = y + 4
    heights = [110, 128, 114, 102]
    for idx, ((st, sb), h) in enumerate(zip(specs, heights), 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + h), idx, st, sb)
        cy += h + 10


def build_page_08_digital_back_cover(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 8, "DIGITAL MARKETING BLUEPRINTS & SUMMARY")

    y = draw_section_title(
        page,
        46,
        "SECTION 07  •  ONLINE SOFT MARKETING",
        "Social Media, Reels & Email Blueprints",
        "Consistent digital execution across Instagram/LinkedIn carousels, short-form vertical video, and Brevo automated client emails.",
    )

    digital_cards = [
        (
            "Instagram / LinkedIn Educational Carousels (1080 × 1350 px  •  4:5 Portrait)",
            "Scale the Classic Guide template to 1080×1350px (sRGB PNG/JPG): Slide 1 Cover with 12px Charcoal top bar, LC + Real logos, Kicker Pill, 64px Playfair Bold title, graded PNW home photo, and bottom Charcoal 'Swipe ->' bar. Slides 2–6 feature 2–3 White cards on #FAF8F5 Ivory with 8px solid Charcoal left bars and Playfair number badges.",
        ),
        (
            "Instagram Reels / YouTube Shorts / TikTok Overlays (1080 × 1920 px  •  9:16 Vertical)",
            "Keep all text and logos inside the safe zone (x: 90–990px, y: 250–1520px). Style lower-thirds and caption pills in Charcoal Dark #151C23 at 90% opacity with a 6px solid #C0C0C0 Silver left accent bar, #FAF8F5 Ivory Playfair Bold topic headers, and Plus Jakarta SemiBold captions.",
        ),
        (
            "Brevo Transactional & Drip HTML Emails (620 px Max-Width Responsive Table)",
            "Outer wrapper #F8FAFC; inner card #FFFFFF (12px radius). Top header in #0F172A Navy with 3px #06B6D4 Cyan bottom border, 68px circular avatar, #38BDF8 uppercase kicker, and white title. Attach private PDF guides (such as Home_Maintenance_Guide_Lokesh_Chanana.pdf) directly via Base64 'content' in /v3/smtp/email—never public links.",
        ),
    ]

    cy = y + 4
    for idx, (dt, db) in enumerate(digital_cards, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + 88), idx, dt, db)
        cy += 96

    # Antigravity Skill Callout Box
    sk_box = pymupdf.Rect(36, cy + 2, PAGE_W - 36, cy + 78)
    page.draw_rect(sk_box, color=SILVER_LIGHT, fill=IVORY_DARK, width=0.8)
    page.draw_rect(pymupdf.Rect(36, cy + 2, 40, cy + 78), color=None, fill=CHARCOAL)
    add_text(page, (50, cy + 10, PAGE_W - 48, cy + 26), "INSTALLED ANTIGRAVITY SKILL: loki-brand-design", font="PJS-Bold", size=8.5, color=CHARCOAL)
    add_text(
        page,
        (50, cy + 26, PAGE_W - 48, cy + 72),
        "• Workspace Skill: /home/lokesh/Casa-poki/.agents/skills/loki-brand-design/SKILL.md\n"
        "• Global Skill: /home/lokesh/.gemini/config/skills/loki-brand-design/SKILL.md\n"
        "• Python Toolkit: /home/lokesh/Casa-poki/.agents/skills/loki-brand-design/scripts/brand_toolkit.py",
        font="PJS-Med",
        size=8.0,
        color=CHARCOAL_LIGHT,
        lineheight=1.35,
    )

    # Signature Dark Charcoal Back Cover Footer Card
    foot = pymupdf.Rect(36, 594, PAGE_W - 36, 742)
    page.draw_rect(foot, color=None, fill=CHARCOAL)
    page.draw_rect(pymupdf.Rect(36, 594, PAGE_W - 36, 597), color=None, fill=SILVER)

    insert_editorial_photo(
        page,
        (54, 614, 134, 722),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=2,
        bg_rgb=CHARCOAL_255,
        centering=(0.5, 0.22),
        grade=False,
        border_rgb=(192, 192, 192),
        border_px=3,
    )
    add_text(page, (152, 614, 430, 628), "OFFICIAL BRAND OWNER & BROKER", font="PJS-Bold", size=7.8, color=SILVER)
    add_text(page, (152, 628, 430, 654), "Lokesh Chanana (Loki)", font="PF-Bold", size=17.5, color=IVORY)
    add_text(page, (152, 652, 430, 668), "Real Broker LLC  •  Washington License #26006634", font="PJS-Med", size=8.8, color=SILVER)
    add_text(page, (152, 674, 430, 690), "CALL / TEXT: (801) 860-1052", font="PJS-Bold", size=9.5, color=IVORY)
    add_text(page, (152, 690, 430, 706), "EMAIL: lokesh@lokeshchanana.com  |  hello@lokeshchanana.com", font="PJS-Med", size=8.5, color=IVORY)
    add_text(page, (152, 706, 430, 722), "WEB: https://lokeshchanana.com", font="PJS-Med", size=8.5, color=IVORY)

    insert_logo(page, (455, 616, 555, 676), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=CHARCOAL_255, target_rgb=IVORY_255)
    insert_logo(page, (462, 686, 548, 720), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=CHARCOAL_255, target_rgb=IVORY_255, is_real_logo=True)


def main():
    doc = pymupdf.open()
    build_page_01_cover(doc)
    build_page_02_identity_logos(doc)
    build_page_03_colors_print(doc)
    build_page_04_digital_light_dark(doc)
    build_page_05_typography(doc)
    build_page_06_photography(doc)
    build_page_07_print_blueprints(doc)
    build_page_08_digital_back_cover(doc)

    doc.set_metadata({
        "title": "Master Brand & Design Guidelines — Lokesh Chanana (Loki) | Real Broker LLC",
        "author": "Lokesh Chanana (Loki) — REALTOR®, Real Broker LLC",
        "subject": "Online (Light & Dark Mode) & Offline Print Brand Style Guide",
        "keywords": "Brand Guidelines, Lokesh Chanana, Real Broker, Light Mode, Dark Mode, Print CMYK",
    })

    os.makedirs(os.path.dirname(OUT_PDF), exist_ok=True)
    doc.subset_fonts()
    doc.save(OUT_PDF, garbage=3, deflate=True)
    sz_mb = os.path.getsize(OUT_PDF) / (1024 * 1024)
    print(f"Successfully generated {OUT_PDF} ({len(doc)} pages, {sz_mb:.2f} MB)")


if __name__ == "__main__":
    main()
