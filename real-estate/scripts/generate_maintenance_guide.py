#!/usr/bin/env python3
"""
Generate the 22-page Branded & Interactive Home Maintenance Guide PDF
for Lokesh Chanana (Loki) — Real Broker LLC.

Matches the exact Light Mode editorial architecture theme of https://lokeshchanana.com:
- Warm Ivory (#FAF8F5) & Ivory-Dark (#E5E1DB) canvas
- Crisp White (#FFFFFF) cards with Silver (#E0E0E0 / #C0C0C0) borders and 4pt Charcoal (#1F2933) left accents
- Playfair Display editorial serif headings + Plus Jakarta Sans body & wide-tracked uppercase kickers
- Cohesive Pacific Northwest luxury architectural photography with unified warm-ivory & charcoal editorial color grading
- 88 interactive AcroForm checkboxes + 6 fillable text fields across Pages 17-21
"""

import argparse
import io
import os
import pymupdf
from PIL import Image, ImageDraw, ImageOps, ImageEnhance
import numpy as np

PAGE_W = 612.0  # 8.5 in
PAGE_H = 792.0  # 11.0 in

# Website Light Mode Palette (from tailwind.config.js)
IVORY = (250 / 255, 248 / 255, 245 / 255)         # #FAF8F5 (bg-ivory)
IVORY_255 = (250, 248, 245)
IVORY_DARK = (229 / 255, 225 / 255, 219 / 255)    # #E5E1DB (bg-ivory-dark)
IVORY_DARK_255 = (229, 225, 219)
IVORY_CARD = (253 / 255, 252 / 255, 250 / 255)    # #FDFCFA

CHARCOAL = (31 / 255, 41 / 255, 51 / 255)         # #1F2933 (text-charcoal / bg-charcoal)
CHARCOAL_255 = (31, 41, 51)
CHARCOAL_DARK = (21 / 255, 28 / 255, 35 / 255)    # #151C23 (charcoal-dark)
CHARCOAL_DARK_255 = (21, 28, 35)
CHARCOAL_LIGHT = (45 / 255, 58 / 255, 71 / 255)   # #2D3A47 (text-charcoal-light)

SILVER = (192 / 255, 192 / 255, 192 / 255)        # #C0C0C0 (silver)
SILVER_DARK = (140 / 255, 142 / 255, 145 / 255)   # #8C8E91 (silver-dark legible on light)
SILVER_LIGHT = (224 / 255, 224 / 255, 224 / 255)  # #E0E0E0 (silver-light border)
SILVER_BORDER_255 = (214, 211, 205)

WHITE = (1.0, 1.0, 1.0)
WHITE_255 = (255, 255, 255)

ASSET_V2_DIR = "/tmp/guide_assets_v2"
DEFAULT_SAT = 0.58
PUBLIC_DIR = "/home/lokesh/Casa-poki/real-estate/public"
FONT_DIR = "/tmp/guide_assets/fonts"

FONTS = {
    "PF-Reg": f"{FONT_DIR}/Playfair-normal-400.ttf",
    "PF-Semi": f"{FONT_DIR}/Playfair-normal-600.ttf",
    "PF-Bold": f"{FONT_DIR}/Playfair-normal-700.ttf",
    "PF-Ital": f"{FONT_DIR}/Playfair-italic-400.ttf",
    "PF-SemiItal": f"{FONT_DIR}/Playfair-italic-600.ttf",
    "PJS-Reg": f"{FONT_DIR}/PlusJakartaSans-Regular.ttf",
    "PJS-Med": f"{FONT_DIR}/PlusJakartaSans-Medium.ttf",
    "PJS-Semi": f"{FONT_DIR}/PlusJakartaSans-SemiBold.ttf",
    "PJS-Bold": f"{FONT_DIR}/PlusJakartaSans-Bold.ttf",
    "PJS-Extra": f"{FONT_DIR}/PlusJakartaSans-ExtraBold.ttf",
    "PJS-Ital": f"{FONT_DIR}/PlusJakartaSans-Italic.ttf",
}


def register_fonts(page):
    for name, path in FONTS.items():
        page.insert_font(fontname=name, fontfile=path)


def paint_ivory_canvas(page):
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, PAGE_H), color=None, fill=IVORY)


def add_text(page, rect, text, font="PJS-Reg", size=10.5, color=CHARCOAL_LIGHT, align=0, lineheight=1.28):
    r = pymupdf.Rect(rect)
    rc = page.insert_textbox(
        r,
        text,
        fontname=font,
        fontsize=size,
        color=color,
        align=align,
        lineheight=lineheight,
    )
    if rc < 0:
        for s in [size - 0.5, size - 1.0, size - 1.5, size - 2.0]:
            rc = page.insert_textbox(
                r,
                text,
                fontname=font,
                fontsize=s,
                color=color,
                align=align,
                lineheight=lineheight - 0.05,
            )
            if rc >= 0:
                break
        if rc < 0:
            print(f"[WARN] Text overflow on page {page.number + 1}: {text[:45]}... (rc={rc})")
    return rc


def draw_vector_check(page, cx, cy, size=5.0, color=CHARCOAL, width=1.6):
    p1 = pymupdf.Point(cx - size * 0.75, cy + size * 0.05)
    p2 = pymupdf.Point(cx - size * 0.15, cy + size * 0.65)
    p3 = pymupdf.Point(cx + size * 0.85, cy - size * 0.55)
    page.draw_line(p1, p2, color=color, width=width)
    page.draw_line(p2, p3, color=color, width=width)


def editorial_grade(im, sat=0.58, contrast=1.05):
    """
    Harmonize photography to match lokeshchanana.com's Light Mode theme:
    - Muted editorial saturation (58%) so architectural wood, stone, glass, and greenery feel cohesive
    - Subtle warm-ivory (#FAF8F5) highlight & deep-charcoal (#1F2933) shadow split-tone
    """
    im = ImageEnhance.Color(im).enhance(sat)
    im = ImageEnhance.Contrast(im).enhance(contrast)
    arr = np.array(im, dtype=np.float32) / 255.0
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    ivory = np.array([250 / 255.0, 247 / 255.0, 242 / 255.0])
    charcoal = np.array([31 / 255.0, 41 / 255.0, 51 / 255.0])
    lum3 = lum[:, :, None]
    tone = charcoal * (1.0 - lum3) + ivory * lum3
    blended = np.clip(arr * 0.84 + tone * 0.16, 0.0, 1.0)
    return Image.fromarray((blended * 255.0).astype(np.uint8), "RGB")


def make_editorial_jpeg(
    src_path,
    w_pt,
    h_pt,
    radius_pt=2,
    bg_rgb=IVORY_255,
    scale=2.4,
    centering=(0.5, 0.5),
    dark_gradient=False,
    ivory_fade_bottom=False,
    grade=True,
    sat=0.58,
    border_rgb=SILVER_BORDER_255,
    border_px=2,
):
    w_px = max(1, int(round(w_pt * scale)))
    h_px = max(1, int(round(h_pt * scale)))
    rad_px = int(round(radius_pt * scale))

    im = Image.open(src_path).convert("RGB")
    fitted = ImageOps.fit(im, (w_px, h_px), method=Image.Resampling.LANCZOS, centering=centering)

    if grade:
        fitted = editorial_grade(fitted, sat=sat)

    if dark_gradient:
        # Warm Charcoal (#1F2933) editorial overlay for white serif headlines on checklist banners
        overlay = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(h_px):
            t = y / max(1, h_px - 1)
            alpha = int(115 + 115 * (t ** 1.1))
            draw_ov.line([(0, y), (w_px, y)], fill=(31, 41, 51, alpha))
        fitted = Image.alpha_composite(fitted.convert("RGBA"), overlay).convert("RGB")

    if ivory_fade_bottom:
        # Subtle fade into #FAF8F5 Ivory at the very bottom edge (like Hero.jsx)
        overlay = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(h_px):
            t = max(0.0, (y / max(1, h_px - 1) - 0.65) / 0.35)
            alpha = int(235 * (t ** 1.6))
            draw_ov.line([(0, y), (w_px, y)], fill=(250, 248, 245, alpha))
        fitted = Image.alpha_composite(fitted.convert("RGBA"), overlay).convert("RGB")

    mask = Image.new("L", (w_px, h_px), 0)
    draw_m = ImageDraw.Draw(mask)
    if rad_px > 0:
        draw_m.rounded_rectangle((0, 0, w_px - 1, h_px - 1), radius=rad_px, fill=255)
    else:
        draw_m.rectangle((0, 0, w_px - 1, h_px - 1), fill=255)

    bg = Image.new("RGB", (w_px, h_px), bg_rgb)
    bg.paste(fitted, (0, 0), mask)

    if border_rgb and border_px > 0:
        draw_b = ImageDraw.Draw(bg)
        if rad_px > 0:
            draw_b.rounded_rectangle(
                (border_px // 2, border_px // 2, w_px - 1 - border_px // 2, h_px - 1 - border_px // 2),
                radius=rad_px,
                outline=border_rgb,
                width=border_px,
            )
        else:
            draw_b.rectangle(
                (border_px // 2, border_px // 2, w_px - 1 - border_px // 2, h_px - 1 - border_px // 2),
                outline=border_rgb,
                width=border_px,
            )

    buf = io.BytesIO()
    bg.save(buf, format="JPEG", quality=86, optimize=True)
    return buf.getvalue()


def insert_editorial_photo(
    page,
    rect,
    src_path,
    radius=2,
    bg_rgb=IVORY_255,
    centering=(0.5, 0.5),
    dark_gradient=False,
    ivory_fade_bottom=False,
    grade=True,
    sat=None,
    border_rgb=SILVER_BORDER_255,
    border_px=2,
):
    if sat is None:
        sat = DEFAULT_SAT
    r = pymupdf.Rect(rect)
    stream = make_editorial_jpeg(
        src_path,
        r.width,
        r.height,
        radius_pt=radius,
        bg_rgb=bg_rgb,
        centering=centering,
        dark_gradient=dark_gradient,
        ivory_fade_bottom=ivory_fade_bottom,
        grade=grade,
        sat=sat,
        border_rgb=border_rgb,
        border_px=border_px,
    )
    page.insert_image(r, stream=stream)


def insert_logo(page, rect, logo_path, bg_rgb=IVORY_255, target_rgb=CHARCOAL_255, is_real_logo=False):
    """
    Render lc-logo.png or real-logo.png cleanly in target_rgb (Charcoal #1F2933 on Ivory/White,
    or Ivory #FAF8F5 on Charcoal) with zero rectangular box artifacts.
    """
    r = pymupdf.Rect(rect)
    scale = 2.8
    w_px = max(1, int(round(r.width * scale)))
    h_px = max(1, int(round(r.height * scale)))
    logo = Image.open(logo_path).convert("RGBA")
    arr = np.array(logo, dtype=np.float32)

    if is_real_logo:
        # real-logo.png is black text on opaque white background
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        alpha = np.clip(255.0 - lum, 0, 255).astype(np.uint8)
    else:
        # lc-logo.png has native alpha channel
        alpha = arr[:, :, 3].astype(np.uint8)

    recolored = np.zeros_like(arr, dtype=np.uint8)
    recolored[:, :, 0] = target_rgb[0]
    recolored[:, :, 1] = target_rgb[1]
    recolored[:, :, 2] = target_rgb[2]
    recolored[:, :, 3] = alpha

    clean_logo = Image.fromarray(recolored, mode="RGBA")
    bbox = clean_logo.getbbox()
    if bbox:
        clean_logo = clean_logo.crop(bbox)

    clean_logo.thumbnail((w_px, h_px), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (w_px, h_px), bg_rgb + (255,))
    ox = (w_px - clean_logo.width) // 2
    oy = (h_px - clean_logo.height) // 2
    canvas.alpha_composite(clean_logo, (ox, oy))

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="JPEG", quality=92, optimize=True)
    page.insert_image(r, stream=buf.getvalue())


def draw_kicker_badge(page, x, y, text, align_center=False):
    """
    Matches Hero.jsx:
    inline-block py-1 px-3 rounded border border-charcoal/20 text-[10px] uppercase tracking-[0.2em] font-semibold text-charcoal-light
    """
    w = max(120, len(text) * 5.6 + 22)
    x0 = (PAGE_W - w) / 2.0 if align_center else x
    box = pymupdf.Rect(x0, y, x0 + w, y + 18)
    page.draw_rect(box, color=SILVER, fill=WHITE, width=0.7, radius=0.1)
    add_text(
        page,
        (x0 + 6, y + 3.2, x0 + w - 6, y + 17),
        text.upper(),
        font="PJS-Bold",
        size=7.2,
        color=CHARCOAL_LIGHT,
        align=1 if align_center else 0,
    )
    return y + 24


def draw_running_chrome(page, page_num, category_label="CLIENT RESOURCE GUIDE"):
    paint_ivory_canvas(page)

    # Top subtle Charcoal & Silver architectural rule (matching Header.jsx in light mode)
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 4), color=None, fill=CHARCOAL)
    add_text(
        page,
        (36, 15, 360, 30),
        f"LOKESH CHANANA   •   {category_label.upper()}",
        font="PJS-Bold",
        size=7.2,
        color=CHARCOAL_LIGHT,
    )
    add_text(
        page,
        (360, 15, PAGE_W - 36, 30),
        "HOME MAINTENANCE GUIDE",
        font="PF-Ital",
        size=8.5,
        color=SILVER_DARK,
        align=2,
    )
    page.draw_line(pymupdf.Point(36, 32), pymupdf.Point(PAGE_W - 36, 32), color=SILVER_LIGHT, width=0.8)

    # Bottom footer bar
    page.draw_line(pymupdf.Point(36, PAGE_H - 36), pymupdf.Point(PAGE_W - 36, PAGE_H - 36), color=SILVER_LIGHT, width=0.8)
    add_text(
        page,
        (36, PAGE_H - 28, 460, PAGE_H - 12),
        "Lokesh Chanana (Loki)  •  REALTOR®  •  Real Broker LLC   |   (801) 860-1052   |   lokeshchanana.com",
        font="PJS-Med",
        size=7.8,
        color=CHARCOAL_LIGHT,
    )
    page.insert_link({
        "kind": pymupdf.LINK_URI,
        "from": pymupdf.Rect(255, PAGE_H - 30, 330, PAGE_H - 12),
        "uri": "tel:+18018601052",
    })
    page.insert_link({
        "kind": pymupdf.LINK_URI,
        "from": pymupdf.Rect(335, PAGE_H - 30, 445, PAGE_H - 12),
        "uri": "https://lokeshchanana.com",
    })

    # Architectural square page number badge in Charcoal (#1F2933) with Ivory text
    pill = pymupdf.Rect(PAGE_W - 62, PAGE_H - 31, PAGE_W - 36, PAGE_H - 15)
    page.draw_rect(pill, color=None, fill=CHARCOAL)
    add_text(
        page,
        (PAGE_W - 62, PAGE_H - 29.5, PAGE_W - 36, PAGE_H - 14),
        f"{page_num:02d}",
        font="PF-Bold",
        size=8.5,
        color=IVORY,
        align=1,
    )


def draw_section_title(page, y, kicker, title, subtitle=None):
    cur_y = draw_kicker_badge(page, 36, y, kicker)
    add_text(
        page,
        (36, cur_y - 2, PAGE_W - 36, cur_y + 34),
        title,
        font="PF-Bold",
        size=22.5,
        color=CHARCOAL,
        lineheight=1.12,
    )
    cur_y += 32
    if subtitle:
        add_text(
            page,
            (36, cur_y, PAGE_W - 36, cur_y + 42),
            subtitle,
            font="PJS-Reg",
            size=10.0,
            color=CHARCOAL_LIGHT,
            lineheight=1.36,
        )
        cur_y += 38
    return cur_y


def draw_numbered_card(page, rect, num, title, body, bg=WHITE):
    """
    Matches BuyersGuide.jsx & Resources.jsx Light Mode cards:
    bg-white border border-silver/30 border-l-4 border-l-charcoal
    """
    r = pymupdf.Rect(rect)
    page.draw_rect(r, color=SILVER_LIGHT, fill=bg, width=0.8)
    # 3.5pt solid Charcoal left accent bar (border-l-4 border-l-charcoal)
    page.draw_rect(pymupdf.Rect(r.x0, r.y0, r.x0 + 3.5, r.y1), color=None, fill=CHARCOAL)

    # Editorial serif number badge
    badge = pymupdf.Rect(r.x0 + 13, r.y0 + 11, r.x0 + 35, r.y0 + 33)
    page.draw_rect(badge, color=SILVER_LIGHT, fill=IVORY, width=0.7)
    add_text(
        page,
        (badge.x0, badge.y0 + 3.5, badge.x1, badge.y1),
        f"{num:02d}",
        font="PF-Bold",
        size=9.2,
        color=CHARCOAL,
        align=1,
    )

    add_text(
        page,
        (r.x0 + 44, r.y0 + 9, r.x1 - 12, r.y0 + 29),
        title,
        font="PF-Bold",
        size=11.5,
        color=CHARCOAL,
    )
    add_text(
        page,
        (r.x0 + 44, r.y0 + 27, r.x1 - 12, r.y1 - 6),
        body,
        font="PJS-Reg",
        size=9.5,
        color=CHARCOAL_LIGHT,
        lineheight=1.33,
    )


# ==============================================================================
# PAGE BUILDERS (PAGES 1 - 22)
# ==============================================================================

def build_page_01_cover(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    paint_ivory_canvas(page)

    # Top Charcoal architectural bar
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 6), color=None, fill=CHARCOAL)

    # Top Header Bar (matching Header.jsx in Light Mode)
    insert_logo(page, (36, 18, 86, 62), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=IVORY_255, target_rgb=CHARCOAL_255)
    add_text(page, (94, 24, 300, 44), "LOKESH CHANANA", font="PF-Bold", size=12.5, color=CHARCOAL)
    add_text(page, (94, 42, 300, 58), "REAL ESTATE AGENT  •  GREATER SEATTLE", font="PJS-Semi", size=7.2, color=CHARCOAL_LIGHT)

    insert_logo(page, (PAGE_W - 110, 24, PAGE_W - 36, 54), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=IVORY_255, target_rgb=CHARCOAL_255, is_real_logo=True)
    page.draw_line(pymupdf.Point(36, 68), pymupdf.Point(PAGE_W - 36, 68), color=SILVER_LIGHT, width=0.8)

    # Outlined Kicker Badge (matching Hero.jsx)
    draw_kicker_badge(page, 36, 82, "GREATER SEATTLE SPECIALISTS  •  CLIENT RESOURCE", align_center=True)

    # Editorial Playfair Display Title (matching Hero.jsx: Bold + Italic Light)
    add_text(
        page,
        (36, 105, PAGE_W - 36, 158),
        "Dedicated, Proactive",
        font="PF-Bold",
        size=30.0,
        color=CHARCOAL,
        align=1,
    )
    add_text(
        page,
        (36, 141, PAGE_W - 36, 194),
        "Home Maintenance Guide.",
        font="PF-Ital",
        size=29.0,
        color=CHARCOAL_LIGHT,
        align=1,
    )

    add_text(
        page,
        (64, 190, PAGE_W - 64, 232),
        "A practical, season-by-season architectural handbook with interactive checklists to protect your investment, prevent costly surprises, and preserve your home's long-term value.",
        font="PJS-Reg",
        size=10.2,
        color=CHARCOAL_LIGHT,
        align=1,
        lineheight=1.38,
    )

    # Main Pacific Northwest Luxury Architecture Hero Photo + 3 Architectural Vignettes
    insert_editorial_photo(
        page,
        (36, 238, PAGE_W - 36, 488),
        f"{ASSET_V2_DIR}/site_north.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        sat=0.55,
        border_rgb=SILVER_BORDER_255,
        border_px=2,
    )

    strip_y0, strip_y1 = 498, 610
    col_w = (PAGE_W - 72 - 20) / 3.0
    strip_imgs = [
        f"{ASSET_V2_DIR}/puget_spring.jpg",
        f"{ASSET_V2_DIR}/puget_summer.jpg",
        f"{ASSET_V2_DIR}/puget_fall.jpg",
    ]
    for i, img_p in enumerate(strip_imgs):
        x0 = 36 + i * (col_w + 10)
        insert_editorial_photo(
            page,
            (x0, strip_y0, x0 + col_w, strip_y1),
            img_p,
            radius=2,
            bg_rgb=IVORY_255,
            sat=0.55,
            border_rgb=SILVER_BORDER_255,
            border_px=2,
        )

    # Interactive Checklist Callout Bar (matching BuyersGuide.jsx callout box)
    banner = pymupdf.Rect(36, 624, PAGE_W - 36, 664)
    page.draw_rect(banner, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    page.draw_rect(pymupdf.Rect(36, 624, 40, 664), color=None, fill=CHARCOAL)
    draw_vector_check(page, 58, 644, size=5.0, color=CHARCOAL, width=1.8)
    add_text(
        page,
        (72, 636, PAGE_W - 48, 658),
        "INCLUDES 5 INTERACTIVE FILLABLE CHECKLISTS (Pages 17–21) — Check off items digitally or print!",
        font="PJS-Bold",
        size=9.0,
        color=CHARCOAL,
    )

    # Bottom Agent Footer Card (Crisp White & Charcoal on Ivory)
    footer_card = pymupdf.Rect(36, 676, PAGE_W - 36, 756)
    page.draw_rect(footer_card, color=SILVER_LIGHT, fill=CHARCOAL, width=0.8)

    insert_editorial_photo(
        page,
        (50, 686, 106, 746),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=2,
        bg_rgb=CHARCOAL_255,
        centering=(0.5, 0.2),
        grade=False,
        border_rgb=(192, 192, 192),
        border_px=2,
    )
    add_text(page, (120, 688, 430, 710), "Lokesh Chanana (Loki)", font="PF-Bold", size=14.0, color=IVORY)
    add_text(page, (120, 709, 430, 726), "YOUR TRUSTED REALTOR®  •  REAL BROKER LLC  (LIC #26006634)", font="PJS-Semi", size=8.0, color=SILVER)
    add_text(page, (120, 727, 550, 746), "(801) 860-1052   •   lokesh@lokeshchanana.com   •   lokeshchanana.com", font="PJS-Med", size=8.8, color=IVORY)

    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(120, 726, 200, 746), "uri": "tel:+18018601052"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(205, 726, 355, 746), "uri": "mailto:lokesh@lokeshchanana.com"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(360, 726, 490, 746), "uri": "https://lokeshchanana.com"})


def build_page_02_welcome(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 2, "WELCOME HOME")

    # Left Column: Warm Architectural Interior + Agent Card
    insert_editorial_photo(
        page,
        (36, 50, 255, 412),
        f"{ASSET_V2_DIR}/arch_lighting_int.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        sat=0.55,
    )

    # Agent Profile & Contact Card on Left Bottom (Crisp White & Charcoal Editorial Card)
    agent_card = pymupdf.Rect(36, 426, 255, 736)
    page.draw_rect(agent_card, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    page.draw_rect(pymupdf.Rect(36, 426, 255, 431), color=None, fill=CHARCOAL)

    insert_editorial_photo(
        page,
        (52, 444, 132, 544),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=2,
        bg_rgb=WHITE_255,
        centering=(0.5, 0.2),
        grade=False,
        border_rgb=SILVER_BORDER_255,
        border_px=2,
    )
    insert_logo(page, (146, 446, 236, 498), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=WHITE_255, target_rgb=CHARCOAL_255)
    insert_logo(page, (150, 506, 232, 536), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=WHITE_255, target_rgb=CHARCOAL_255, is_real_logo=True)

    add_text(page, (52, 556, 240, 572), "YOUR TRUSTED REALTOR®", font="PJS-Bold", size=7.5, color=SILVER_DARK)
    add_text(page, (52, 570, 240, 594), "Lokesh Chanana", font="PF-Bold", size=15.5, color=CHARCOAL)
    add_text(page, (52, 592, 240, 610), "Real Broker LLC  •  Greater Seattle & WA", font="PJS-Reg", size=8.3, color=CHARCOAL_LIGHT)

    page.draw_line(pymupdf.Point(52, 618), pymupdf.Point(239, 618), color=SILVER_LIGHT, width=0.8)

    add_text(page, (52, 628, 240, 644), "LET'S CONNECT — CALL ME ANYTIME", font="PJS-Bold", size=7.8, color=CHARCOAL)
    add_text(page, (52, 647, 240, 666), "CALL / TEXT:  (801) 860-1052", font="PJS-Semi", size=9.2, color=CHARCOAL)
    add_text(page, (52, 667, 240, 686), "EMAIL:  lokesh@lokeshchanana.com", font="PJS-Med", size=8.6, color=CHARCOAL_LIGHT)
    add_text(page, (52, 687, 240, 708), "WEB:  lokeshchanana.com", font="PJS-Bold", size=8.8, color=CHARCOAL)

    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(52, 646, 235, 666), "uri": "tel:+18018601052"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(52, 666, 235, 686), "uri": "mailto:lokesh@lokeshchanana.com"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(52, 686, 235, 708), "uri": "https://lokeshchanana.com"})

    # Right Column: Welcome Note
    draw_kicker_badge(page, 278, 50, "HEY THERE!  •  WELCOME HOME")

    add_text(
        page,
        (278, 80, PAGE_W - 36, 148),
        "Congratulations on becoming a homeowner!",
        font="PF-Bold",
        size=24.0,
        color=CHARCOAL,
        lineheight=1.16,
    )

    letter_body = (
        "There is nothing quite like the feeling of turning the key to your own place. Now that the boxes are unpacking and you're settling in, a little proactive care will go a long way toward keeping your home just as special as the day you got the keys.\n\n"
        "This guide is designed to help you maintain your property, preserve its value, and prevent costly repairs through proactive care and regular maintenance.\n\n"
        "Inside, you'll find practical room-by-room tips plus five interactive seasonal checklists at the back of the guide. You can click the checkboxes right inside this PDF on your phone or computer—or print out the checklist pages and stick them on the fridge!\n\n"
        "If you ever have any questions or need recommendations for reliable service pros, don't hesitate to reach out. I am always here to help!\n\n"
        "Wishing you lots of happiness, laughter, and great memories in your new home."
    )
    add_text(
        page,
        (278, 158, PAGE_W - 36, 536),
        letter_body,
        font="PJS-Reg",
        size=10.8,
        color=CHARCOAL_LIGHT,
        lineheight=1.48,
    )

    # Signature Block (matching BuyersGuide.jsx left-bordered callout box)
    sig_box = pymupdf.Rect(278, 552, PAGE_W - 36, 736)
    page.draw_rect(sig_box, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    page.draw_rect(pymupdf.Rect(278, 552, 282, 736), color=None, fill=CHARCOAL)

    add_text(page, (298, 568, 550, 590), "Warmest regards,", font="PF-Ital", size=12.0, color=CHARCOAL_LIGHT)
    add_text(page, (298, 592, 550, 622), "Lokesh Chanana (Loki)", font="PF-Bold", size=17.0, color=CHARCOAL)
    add_text(page, (298, 620, 550, 638), "REALTOR®  •  Real Broker LLC", font="PJS-Semi", size=9.2, color=SILVER_DARK)

    add_text(
        page,
        (298, 648, 560, 724),
        "What's Inside This Guide:\n"
        "•  Pages 03–07:  Investment, Big Repairs, Structure, Electrical & Plumbing\n"
        "•  Pages 08–15:  HVAC, Appliances, Interior, Curb Appeal, Security & Energy\n"
        "•  Pages 16–21:  5 Interactive Fillable Checklists (Pest, Spring, Summer, Fall, Winter)",
        font="PJS-Med",
        size=9.0,
        color=CHARCOAL_LIGHT,
        lineheight=1.4,
    )


def build_page_03_invest(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 3, "WHY MAINTENANCE MATTERS")

    y = draw_section_title(
        page,
        46,
        "PROTECT YOUR INVESTMENT",
        "Why Home Maintenance Matters",
        "Keeping up with your home isn't just a chore—it's a game-changer for your wallet, comfort, and peace of mind. Here's why staying on top of home maintenance is so important:",
    )

    insert_editorial_photo(
        page,
        (36, y + 6, PAGE_W - 36, y + 186),
        f"{ASSET_V2_DIR}/arch_living_glass.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        centering=(0.5, 0.55),
    )

    items = [
        (
            "Save Money Over Time",
            "Catching small issues early can prevent them from turning into big, expensive problems down the road. A little effort now can save you a lot of cash later.",
        ),
        (
            "Boost Your Comfort",
            "A well-maintained home means everything works like it should. No more drafts, leaky faucets, or temperamental appliances—just a cozy, hassle-free living space.",
        ),
        (
            "Increase Your Home's Value",
            "Regular upkeep keeps your home looking its best and functioning smoothly, which can bump up its market value if you ever decide to sell.",
        ),
        (
            "Keep Your Family Safe",
            "Routine checks can uncover potential safety hazards like faulty wiring or structural weaknesses, helping you fix them before they pose a risk.",
        ),
        (
            "Reduce Stress",
            "Knowing that your home is in good shape lets you relax and enjoy it without worrying about unexpected repairs popping up.",
        ),
    ]

    cy = y + 200
    card_h = 74
    gap = 9
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + gap


def build_page_04_repairs(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 4, "PLANNING FOR MAJOR UPGRADES")

    y = draw_section_title(
        page,
        46,
        "SMART PLANNING & OPTIONS",
        "When Big Repairs Come Knocking",
        "Sometimes, major repairs or upgrades are unavoidable. Here's how to handle them without losing sleep:",
    )

    insert_editorial_photo(
        page,
        (36, y + 6, PAGE_W - 36, y + 190),
        f"{ASSET_V2_DIR}/site_eastside.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        centering=(0.5, 0.65),
    )

    items = [
        (
            "Home Equity Line of Credit (HELOC)",
            "Borrow against your home's equity with typically lower interest rates. It's like having a financial safety net tied to your house.",
        ),
        (
            "Personal Loans",
            "An unsecured loan can cover big expenses without using your home as collateral. Just keep an eye on interest rates and terms.",
        ),
        (
            "Credit Cards",
            "Good for smaller projects, but be cautious of high interest rates if you can't pay off the balance quickly.",
        ),
        (
            "DIY When You Can",
            "Handling simple tasks yourself can save money—but know your limits. For complex jobs, it's safer (and sometimes cheaper in the long run) to hire a pro.",
        ),
        (
            "Shop Around",
            "Get multiple quotes for services and materials. You'd be surprised how much prices can vary!",
        ),
        (
            "Energy Efficiency Pays",
            "Upgrading to energy-efficient systems can lower utility bills, saving you money over time.",
        ),
    ]

    grid_y = y + 206
    col_w = (PAGE_W - 72 - 14) / 2.0
    row_h = 126
    for idx, (title, body) in enumerate(items, 1):
        r_idx, c_idx = divmod(idx - 1, 2)
        x0 = 36 + c_idx * (col_w + 14)
        y0 = grid_y + r_idx * (row_h + 12)
        draw_numbered_card(page, (x0, y0, x0 + col_w, y0 + row_h), idx, title, body, bg=WHITE)


def build_page_05_structure(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 5, "STRUCTURAL INTEGRITY")

    y = draw_section_title(
        page,
        46,
        "THE BACKBONE OF YOUR HOME",
        "Keep Your Home Standing Strong",
        "Your home's structure is its backbone, and keeping it in good shape is crucial for safety and longevity. Regular attention to key areas can prevent small issues from becoming big problems down the line.",
    )

    col_w = (PAGE_W - 72 - 12) / 2.0
    insert_editorial_photo(
        page,
        (36, y + 6, 36 + col_w, y + 166),
        f"{ASSET_V2_DIR}/puget_spring.jpg",
        radius=2,
        bg_rgb=IVORY_255,
    )
    insert_editorial_photo(
        page,
        (36 + col_w + 12, y + 6, PAGE_W - 36, y + 166),
        f"{ASSET_V2_DIR}/puget_fall.jpg",
        radius=2,
        bg_rgb=IVORY_255,
    )

    items = [
        (
            "Roof Care",
            "Start by checking your roof every few months. Look for missing, cracked, or curling shingles, and inspect the attic for any signs of leaks or water stains after heavy rain.",
        ),
        (
            "Foundation Checks",
            "Walk around your home's exterior to examine the foundation for any cracks or gaps. Inside, look for signs of moisture or cracks in the basement or crawl space walls.",
        ),
        (
            "Siding and Exterior Walls",
            "Inspect your siding for cracks, rot, or warping. Peeling or bubbling paint can signal moisture problems that need attention.",
        ),
        (
            "Windows and Doors",
            "Ensure they open and close smoothly, lubricating hinges and tracks to prevent sticking. Repair any cracked glass promptly to maintain energy efficiency and security.",
        ),
        (
            "Basement and Crawl Spaces",
            "Check for dampness, mold, or musty smells, and use a dehumidifier if necessary. Proper ventilation helps prevent moisture buildup, which can lead to structural damage over time.",
        ),
    ]

    cy = y + 180
    card_h = 77
    gap = 8
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + gap


def build_page_06_electrical(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 6, "ELECTRICAL SAFETY")

    y = draw_section_title(
        page,
        46,
        "ELECTRICAL SYSTEM CARE",
        "Power Up Safely",
        "Your home's electrical system keeps everything running—from your morning coffee to your evening TV time. Keeping it in good shape is crucial for safety and convenience. Here's how to stay on top of it and know when to bring in a pro.",
    )

    insert_editorial_photo(
        page,
        (36, y + 8, 285, y + 172),
        f"{ASSET_V2_DIR}/arch_interior_warm.jpg",
        radius=2,
        bg_rgb=IVORY_255,
    )
    insert_editorial_photo(
        page,
        (297, y + 8, PAGE_W - 36, y + 172),
        f"{ASSET_V2_DIR}/arch_wood_detail.jpg",
        radius=2,
        bg_rgb=IVORY_255,
    )

    routine_items = [
        (
            "Outlet and Switch Inspection",
            "Walk around your home and check that all outlets and switches are working properly. Look out for any that are warm to the touch, make buzzing sounds, or show scorch marks—these are red flags.",
        ),
        (
            "Test GFCI Outlets",
            "Ground Fault Circuit Interrupter (GFCI) outlets are typically found in kitchens and bathrooms. Press the \"Test\" and \"Reset\" buttons monthly to ensure they're functioning correctly.",
        ),
        (
            "Check Extension Cords and Power Strips",
            "Make sure they're not overloaded and that cords aren't frayed or damaged. Replace any that show signs of wear.",
        ),
    ]

    cy = y + 184
    for idx, (title, body) in enumerate(routine_items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + 72), idx, title, body, bg=WHITE)
        cy += 79

    # Editorial Callout Card: When to Call a Professional?
    pro_box = pymupdf.Rect(36, cy + 4, PAGE_W - 36, 742)
    page.draw_rect(pro_box, color=SILVER_LIGHT, fill=CHARCOAL, width=0.8)

    add_text(
        page,
        (52, cy + 14, PAGE_W - 52, cy + 36),
        "When to Call a Licensed Professional?",
        font="PF-Bold",
        size=14.0,
        color=IVORY,
    )
    add_text(
        page,
        (52, cy + 34, PAGE_W - 52, cy + 54),
        "Some electrical issues are too risky to handle on your own. Here's when you should reach out to a licensed electrician:",
        font="PJS-Reg",
        size=9.0,
        color=SILVER,
    )

    pro_items = [
        ("Frequent Circuit Breaker Trips", "If your breakers trip often, it could indicate overloaded circuits or faulty wiring."),
        ("Flickering or Dimming Lights", "This might mean there's a loose connection or overloaded circuit."),
        ("Warm or Sparking Outlets", "Stop using the outlet immediately and call a professional."),
        ("Installing New Outlets or Fixtures", "Adding or moving electrical outlets, or installing new light fixtures, should be done by an expert to ensure safety and compliance with local codes."),
    ]
    col_w = (PAGE_W - 104 - 16) / 2.0
    for i, (pt, pb) in enumerate(pro_items):
        r_i, c_i = divmod(i, 2)
        px = 52 + c_i * (col_w + 16)
        py = cy + 56 + r_i * 54
        page.draw_rect(pymupdf.Rect(px, py, px + col_w, py + 48), color=CHARCOAL_LIGHT, fill=CHARCOAL_DARK, width=0.7)
        add_text(page, (px + 10, py + 5, px + col_w - 8, py + 21), f"•  {pt}", font="PJS-Bold", size=9.0, color=IVORY)
        add_text(page, (px + 10, py + 20, px + col_w - 8, py + 46), pb, font="PJS-Reg", size=8.1, color=SILVER, lineheight=1.25)


def build_page_07_plumbing(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 7, "PLUMBING & WATER CARE")

    y = draw_section_title(
        page,
        46,
        "PLUMBING MAINTENANCE",
        "Keep the Water Flowing",
        "Your home's plumbing is like its circulatory system, delivering fresh water and whisking away waste. Keeping it in good shape ensures comfort and helps you avoid messy (and costly) surprises.",
    )

    col_w = (PAGE_W - 72 - 12) / 2.0
    insert_editorial_photo(
        page,
        (36, y + 6, 36 + col_w, y + 158),
        f"{ASSET_V2_DIR}/arch_bath_spa.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        centering=(0.5, 0.6),
    )
    plumbing_right_img = f"{ASSET_V2_DIR}/arch_plumbing_kitchen.jpg" if os.path.exists(f"{ASSET_V2_DIR}/arch_plumbing_kitchen.jpg") else f"{ASSET_V2_DIR}/arch_wood_detail.jpg"
    insert_editorial_photo(
        page,
        (36 + col_w + 12, y + 6, PAGE_W - 36, y + 158),
        plumbing_right_img,
        radius=2,
        bg_rgb=IVORY_255,
    )

    plumbing_items = [
        (
            "Stay Alert to Leaks",
            "A tiny drip might not seem like a big deal, but it can quickly escalate into significant damage. Regularly peek under sinks and around appliances for any signs of moisture. If you spot a leak, fixing it promptly can save you a lot of trouble down the line.",
        ),
        (
            "Mind Your Drains",
            "Slow or clogged drains are a common nuisance. Prevent buildup by using drain screens to catch hair and debris. Be cautious about what goes down the kitchen sink—grease and coffee grounds are notorious for causing blockages. If a clog does occur, a plunger or a mixture of baking soda and vinegar can often do the trick.",
        ),
        (
            "Water Heater Wisdom",
            "Your water heater works hard every day to provide hot showers and clean dishes. Extend its lifespan by draining it once a year to remove sediment buildup.",
        ),
    ]

    cy = y + 170
    heights = [74, 92, 66]
    for idx, ((title, body), h) in enumerate(zip(plumbing_items, heights), 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + h), idx, title, body, bg=WHITE)
        cy += h + 8

    tips_box = pymupdf.Rect(36, cy + 4, PAGE_W - 36, 742)
    page.draw_rect(tips_box, color=SILVER_LIGHT, fill=CHARCOAL, width=0.8)

    add_text(
        page,
        (52, cy + 14, PAGE_W - 52, cy + 36),
        "Quick Tips for a Healthy Plumbing System",
        font="PF-Bold",
        size=13.5,
        color=IVORY,
    )

    quick_tips = [
        ("REGULAR CHECK-UPS:", "Periodically walk through your home to inspect pipes and fixtures."),
        ("BE GENTLE:", "Avoid using harsh chemical drain cleaners that can corrode your pipes over time."),
        ("EDUCATE THE HOUSEHOLD:", "Make sure everyone knows what can and can't go down the drains to prevent accidental clogs."),
        ("LOCATE YOUR MAIN WATER VALVE:", "In case of a major leak, you'll want to shut off the water quickly."),
    ]
    col_w2 = (PAGE_W - 104 - 16) / 2.0
    for i, (qt, qb) in enumerate(quick_tips):
        r_i, c_i = divmod(i, 2)
        px = 52 + c_i * (col_w2 + 16)
        py = cy + 42 + r_i * 50
        page.draw_rect(pymupdf.Rect(px, py, px + col_w2, py + 44), color=CHARCOAL_LIGHT, fill=CHARCOAL_DARK, width=0.7)
        add_text(page, (px + 10, py + 5, px + col_w2 - 8, py + 20), f"•  {qt}", font="PJS-Bold", size=8.6, color=IVORY)
        add_text(page, (px + 10, py + 19, px + col_w2 - 8, py + 42), qb, font="PJS-Reg", size=8.2, color=SILVER, lineheight=1.25)


def build_page_08_hvac(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 8, "HEATING & COOLING")

    y = draw_section_title(
        page,
        46,
        "YEAR-ROUND CLIMATE COMFORT",
        "HVAC Maintenance Made Simple",
        "Your Heating, Ventilation, and Air Conditioning (HVAC) system is the heart of your home's comfort. It keeps you cool during sweltering summers and warm on chilly winter nights. Giving it a little attention ensures it runs efficiently and lasts longer.",
    )

    insert_editorial_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 235),
        f"{ASSET_V2_DIR}/arch_spring_home.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        centering=(0.5, 0.55),
    )

    items = [
        (
            "Show Your Filters Some Love",
            "One of the easiest ways to maintain your HVAC system is by regularly changing or cleaning the air filters. Over time, filters collect dust, pollen, and other particles, which can restrict airflow and make your system work harder.",
        ),
        (
            "Keep It Clean",
            "The outdoor unit (condenser) can accumulate leaves, dirt, and debris. Gently clean around the unit and remove any obstructions to ensure proper airflow. Make sure shrubs and plants are trimmed back at least two feet from the unit.",
        ),
        (
            "Professional Tune-Ups",
            "Just like your car, your HVAC system benefits from regular professional check-ups. Having a licensed technician inspect your system annually—ideally once in the spring for cooling and once in the fall for heating—can improve efficiency and spot potential issues before they become costly repairs.",
        ),
    ]

    cy = y + 252
    card_h = 104
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + 12


def build_page_09_appliances(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 9, "KITCHEN & LAUNDRY CARE")

    y = draw_section_title(
        page,
        46,
        "EXTEND APPLIANCE LIFESPAN",
        "Appliance Care",
        "Your home's appliances work hard every day, making life more convenient. With a bit of routine care, you can extend their lifespan and keep them operating efficiently.",
    )

    app_img = f"{ASSET_V2_DIR}/arch_appliances.jpg" if os.path.exists(f"{ASSET_V2_DIR}/arch_appliances.jpg") else f"{ASSET_V2_DIR}/arch_wood_detail.jpg"
    insert_editorial_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        app_img,
        radius=2,
        bg_rgb=IVORY_255,
        centering=(0.5, 0.55),
    )

    items = [
        (
            "Refrigerator Refresher",
            "Clean the condenser coils at least twice a year to help your fridge run efficiently. They're usually located at the back or bottom of the appliance. Simply unplug the refrigerator and use a coil brush or vacuum to remove dust and debris.",
        ),
        (
            "Dishwasher TLC",
            "Over time, food particles can clog your dishwasher's filter and spray arms. Remove and clean the filter regularly, and wipe down the door seals to prevent leaks. Running an empty cycle with a cup of white vinegar can help eliminate odors and mineral buildup.",
        ),
        (
            "Laundry Lineup",
            "For your washing machine, avoid overloading it to prevent strain on the motor and drum. Check hoses periodically for signs of wear or leaks, and replace them every five years.",
        ),
        (
            "Stove and Oven Attention",
            "Keep your stovetop and oven clean to ensure even cooking and prevent fires. For electric stovetops, wipe spills promptly to avoid baked-on messes. Gas stovetops may need burner ports cleaned with a pin or needle if they become clogged.",
        ),
    ]

    cy = y + 234
    card_h = 86
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + 10


def build_page_10_interior(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 10, "INTERIOR UPKEEP")

    y = draw_section_title(
        page,
        46,
        "HEALTHY & BEAUTIFUL LIVING SPACES",
        "Essential Interior Home Maintenance Tips",
        "The inside of your home is where life happens. Regular upkeep keeps it looking great and ensures a healthy living environment.",
    )

    insert_editorial_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_V2_DIR}/arch_pest_perimeter.jpg",
        radius=2,
        bg_rgb=IVORY_255,
    )

    items = [
        (
            "Floor Care Fundamentals",
            "Different flooring types require specific care. Vacuum carpets weekly to remove dirt and allergens, and consider a professional deep clean once a year.",
        ),
        (
            "Wall and Ceiling Upkeep",
            "Keep an eye out for cracks or discoloration on walls and ceilings, which could indicate settling or moisture issues. Touch up paint as needed to keep your home looking fresh. When hanging items, use appropriate anchors to prevent damage.",
        ),
        (
            "Window Care",
            "Clean windows not only look better but also let in more natural light. Wipe down glass surfaces with a streak-free cleaner, and don't forget to clean the window tracks and sills where dirt can accumulate.",
        ),
        (
            "Bathroom Basics",
            "Prevent mold and mildew by running the exhaust fan during and after showers. Regularly clean grout and caulk lines to keep them looking good and sealed against moisture. Fix leaky faucets promptly to avoid water waste and potential water damage.",
        ),
    ]

    cy = y + 234
    card_h = 86
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + 10


def build_page_11_curb_appeal(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 11, "EXTERIOR & CURB APPEAL")

    y = draw_section_title(
        page,
        46,
        "EXTERIOR PROTECTION",
        "Curb Appeal Made Easy",
        "The exterior of your home makes the first impression and protects everything inside. A little maintenance goes a long way in keeping it attractive and durable.",
    )

    insert_editorial_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_V2_DIR}/arch_curb_walkway.jpg",
        radius=2,
        bg_rgb=IVORY_255,
    )

    items = [
        (
            "Siding and Paint Protection",
            "Inspect your home's siding for cracks, gaps, or signs of damage. Clean siding annually using a garden hose or pressure washer on a gentle setting to remove dirt and mildew. Touch up paint or stain as needed to protect wood surfaces from the elements.",
        ),
        (
            "Gutter Guardians",
            "Clean gutters and downspouts at least twice a year, in the spring and fall. Clear out leaves and debris to prevent water from backing up and damaging your roof or foundation. Ensure downspouts direct water at least five feet away from your home.",
        ),
        (
            "Roof Review",
            "While you might leave the climbing to professionals, you can use binoculars to check your roof for missing or damaged shingles. Addressing minor issues promptly can prevent leaks and more significant repairs later on.",
        ),
        (
            "Driveway and Walkway Watch",
            "Fill in cracks in your driveway or walkways to prevent them from expanding. Sealing concrete or asphalt surfaces every few years can extend their life and enhance appearance.",
        ),
    ]

    cy = y + 234
    card_h = 86
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + 10


def build_page_12_security(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 12, "SAFETY & PEACE OF MIND")

    y = draw_section_title(
        page,
        46,
        "PROTECTING YOUR SANCTUARY",
        "Safety and Security",
        "Your home is your sanctuary, and keeping it safe doesn't have to be complicated. Here are some straightforward ways to boost your home's safety and security.",
    )

    insert_editorial_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_V2_DIR}/arch_kitchen_lux.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        centering=(0.5, 0.55),
    )

    items = [
        (
            "Light Up the Night",
            "A well-lit exterior can deter unwelcome visitors. Consider installing motion-sensor lights around entrances and dark corners. Not only does it enhance security, but it also adds convenience when you come home after dark.",
        ),
        (
            "Lock It Down",
            "Make sure all your doors and windows have sturdy locks. Deadbolts are a great addition to exterior doors. Don't forget about sliding doors—adding a rod in the track can prevent them from being forced open.",
        ),
        (
            "Smart Security",
            "Think about investing in a home security system. Even a basic setup with door and window sensors can provide peace of mind. There are plenty of smart home options these days that allow you to monitor your home right from your phone.",
        ),
        (
            "Fire Safety First",
            "Check your smoke detectors regularly—test them monthly and replace batteries at least once a year. It's also wise to have a fire extinguisher in key areas like the kitchen and garage. And if you have gas appliances, a carbon monoxide detector is a must.",
        ),
    ]

    cy = y + 234
    card_h = 86
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + 10


def build_page_13_energy(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 13, "ENERGY EFFICIENCY")

    y = draw_section_title(
        page,
        46,
        "LOWER BILLS & GREATER COMFORT",
        "Save Money and Stay Cozy",
        "Who doesn't love saving money and being comfortable at home? Here are some effortless ways to make your home more energy-efficient.",
    )

    insert_editorial_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_V2_DIR}/site_seattle.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        centering=(0.5, 0.5),
    )

    items = [
        (
            "Seal the Deal",
            "Drafts can sneak in through gaps around windows and doors, making your heating and cooling systems work overtime. Use weatherstripping or caulk to seal those leaks, keeping your home comfy and your energy bills lower.",
        ),
        (
            "Lighten Up",
            "Swap out old incandescent bulbs for LED ones. They use a fraction of the energy and last way longer. It's a small change that adds up over time.",
        ),
        (
            "Smart Thermostats for the Win",
            "Consider installing a programmable or smart thermostat. It adjusts the temperature based on your schedule, so you're not heating or cooling an empty house. It's convenience and savings rolled into one.",
        ),
        (
            "Efficient Appliances",
            "When it's time to replace appliances, look for energy-efficient models. They might cost a bit more upfront, but the savings on your utility bills make them a smart investment.",
        ),
    ]

    cy = y + 234
    card_h = 86
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + 10


def build_page_14_preventative(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 14, "PROACTIVE HABITS")

    y = draw_section_title(
        page,
        46,
        "STAY AHEAD OF REPAIRS",
        "Simple Preventative Measures",
        "A little prevention goes a long way in home maintenance. Here's how to nip potential problems in the bud.",
    )

    insert_editorial_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_V2_DIR}/site_south.jpg",
        radius=2,
        bg_rgb=IVORY_255,
        centering=(0.5, 0.55),
    )

    items = [
        (
            "Regular Walk-Throughs",
            "Every now and then, take a leisurely stroll around your home—inside and out. Look for signs of wear, leaks, or anything that seems out of place. Catching issues early can save you headaches later.",
        ),
        (
            "Clean to Protect",
            "Keep gutters clear to prevent water damage. Change HVAC filters to keep your system running smoothly. Regular cleaning isn't just about appearances; it helps everything function better.",
        ),
        (
            "Seasonal Prep",
            "Before the seasons change, take some time to prepare your home. In the fall, clear leaves and check your heating system. In the spring, look for any winter damage and get your cooling system ready.",
        ),
        (
            "Know Your Systems",
            "Get familiar with where your main water shut-off valve is, how to turn off your gas, and where your electrical panel is located. In an emergency, knowing these things can prevent a minor issue from becoming a disaster.",
        ),
    ]

    cy = y + 234
    card_h = 86
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + 10


def build_page_15_diy_or_pros(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 15, "SMART DECISION MAKING")

    y = draw_section_title(
        page,
        46,
        "KNOW WHEN TO CALL AN EXPERT",
        "DIY or Call in the Pros?",
        "Tackling home projects can be satisfying, but sometimes it's best to leave it to the experts. Here's how to figure out the best approach.",
    )

    insert_editorial_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_V2_DIR}/arch_craft_plan.jpg",
        radius=2,
        bg_rgb=IVORY_255,
    )

    items = [
        (
            "When DIY Makes Sense",
            "If the task is simple, low-risk, and you feel confident, go for it! Painting a room, fixing a squeaky door, or replacing a showerhead are great DIY projects that can save you money.",
        ),
        (
            "When to Bring in the Pros",
            "For anything involving major electrical work, plumbing issues, structural changes, or if permits are required, it's usually safer and more cost-effective to hire a professional. They have the tools and expertise to do the job right.",
        ),
        (
            "Consider Time and Tools",
            "Even if a project is DIY-able, think about the time commitment and whether you have (or want to buy) the necessary tools. Sometimes, the convenience of hiring a pro is worth it.",
        ),
        (
            "Quality Matters",
            "Professionals can offer a level of quality and warranty on their work that might be hard to achieve on your own. This is especially important for projects that affect your home's value.",
        ),
    ]

    cy = y + 234
    card_h = 86
    for idx, (title, body) in enumerate(items, 1):
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=WHITE)
        cy += card_h + 10


def build_page_16_divider(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 16, "SEASONAL & PREVENTATIVE CHECKLISTS")

    draw_kicker_badge(page, 36, 58, "INTERACTIVE CHECKLIST SECTION", align_center=True)

    add_text(
        page,
        (36, 86, PAGE_W - 36, 138),
        "Let's Clean & Maintain!",
        font="PF-Bold",
        size=34.0,
        color=CHARCOAL,
        align=1,
    )
    add_text(
        page,
        (64, 140, PAGE_W - 64, 192),
        "Use the following 5 interactive checklists to stay ahead of seasonal upkeep and pest prevention. Click or tap any checkbox directly inside this PDF to track your progress—or print these pages for your fridge!",
        font="PJS-Reg",
        size=10.5,
        color=CHARCOAL_LIGHT,
        align=1,
        lineheight=1.4,
    )

    # 4-Season Pacific Northwest Architectural Showcase Grid (2x2)
    spring_img = f"{ASSET_V2_DIR}/pnw_spring_estate.jpg" if os.path.exists(f"{ASSET_V2_DIR}/pnw_spring_estate.jpg") else f"{ASSET_V2_DIR}/arch_spring_home.jpg"
    summer_img = f"{ASSET_V2_DIR}/pnw_summer_estate.jpg" if os.path.exists(f"{ASSET_V2_DIR}/pnw_summer_estate.jpg") else f"{ASSET_V2_DIR}/arch_summer_patio.jpg"
    fall_img = f"{ASSET_V2_DIR}/pnw_fall_estate.jpg" if os.path.exists(f"{ASSET_V2_DIR}/pnw_fall_estate.jpg") else f"{ASSET_V2_DIR}/site_north.jpg"
    winter_img = f"{ASSET_V2_DIR}/pnw_winter_estate.jpg" if os.path.exists(f"{ASSET_V2_DIR}/pnw_winter_estate.jpg") else f"{ASSET_V2_DIR}/pnw_winter_lux.jpg"

    col_w = (PAGE_W - 72 - 14) / 2.0
    row_h = 210
    grid_imgs = [
        ("SPRING MAINTENANCE", spring_img),
        ("SUMMER MAINTENANCE", summer_img),
        ("FALL MAINTENANCE", fall_img),
        ("WINTER MAINTENANCE", winter_img),
    ]
    for i, (label, img_p) in enumerate(grid_imgs):
        r_i, c_i = divmod(i, 2)
        x0 = 36 + c_i * (col_w + 14)
        y0 = 204 + r_i * (row_h + 14)
        insert_editorial_photo(
            page,
            (x0, y0, x0 + col_w, y0 + row_h),
            img_p,
            radius=2,
            bg_rgb=IVORY_255,
            dark_gradient=True,
        )
        add_text(
            page,
            (x0 + 14, y0 + row_h - 28, x0 + col_w - 14, y0 + row_h - 8),
            label,
            font="PJS-Bold",
            size=8.5,
            color=IVORY,
        )

    # Checklist Index Strip at bottom (matching BuyersGuide.jsx callout box)
    strip = pymupdf.Rect(36, 654, PAGE_W - 36, 732)
    page.draw_rect(strip, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    page.draw_rect(pymupdf.Rect(36, 654, 40, 732), color=None, fill=CHARCOAL)
    add_text(
        page,
        (54, 666, PAGE_W - 52, 686),
        "YOUR 5 INTERACTIVE CHECKLISTS:",
        font="PF-Bold",
        size=11.0,
        color=CHARCOAL,
    )
    add_text(
        page,
        (54, 688, PAGE_W - 52, 724),
        "Page 17: Preventing Pest Issues (8 items)   •   Page 18: Spring (20 items)   •   Page 19: Summer (20 items)\n"
        "Page 20: Fall (20 items)   •   Page 21: Winter (20 items)",
        font="PJS-Med",
        size=9.2,
        color=CHARCOAL_LIGHT,
        lineheight=1.38,
    )


def build_checklist_page(doc, page_num, slug, title, subtitle, banner_img, items):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    paint_ivory_canvas(page)

    # Top subtle Charcoal bar
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 4), color=None, fill=CHARCOAL)

    # Top Header Banner Image with Warm Charcoal Editorial Gradient Overlay
    banner_rect = pymupdf.Rect(36, 24, PAGE_W - 36, 148)
    insert_editorial_photo(
        page,
        banner_rect,
        banner_img,
        radius=2,
        bg_rgb=IVORY_255,
        dark_gradient=True,
    )

    # Outlined Kicker Badge inside Banner
    badge_rect = pymupdf.Rect(52, 38, 218, 56)
    page.draw_rect(badge_rect, color=SILVER, fill=CHARCOAL_DARK, width=0.7)
    draw_vector_check(page, 65, 47, size=4.0, color=IVORY, width=1.6)
    add_text(
        page,
        (74, 41.5, 214, 55),
        "INTERACTIVE CHECKLIST",
        font="PJS-Bold",
        size=7.6,
        color=IVORY,
    )

    add_text(
        page,
        (52, 62, 425, 104),
        title,
        font="PF-Bold",
        size=24.0,
        color=IVORY,
    )
    add_text(
        page,
        (52, 102, 425, 136),
        subtitle,
        font="PJS-Reg",
        size=9.4,
        color=SILVER_LIGHT,
    )

    # Interactive Season / Year Text Widget in top-right of banner
    date_card = pymupdf.Rect(432, 40, PAGE_W - 48, 96)
    page.draw_rect(date_card, color=SILVER, fill=CHARCOAL_DARK, width=0.8)
    add_text(
        page,
        (440, 46, PAGE_W - 56, 62),
        "SEASON / YEAR:",
        font="PJS-Bold",
        size=7.2,
        color=SILVER,
    )
    tf = pymupdf.Widget()
    tf.field_name = f"txt_{slug}_date"
    tf.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    tf.rect = pymupdf.Rect(440, 64, PAGE_W - 56, 88)
    tf.text_color = (0.12, 0.16, 0.20)
    tf.fill_color = (0.98, 0.97, 0.96)
    tf.border_color = (0.75, 0.75, 0.75)
    tf.border_width = 0.8
    tf.text_fontsize = 9.0
    tf.field_value = ""
    page.add_widget(tf)

    # Instructions bar below banner
    inst_rect = pymupdf.Rect(36, 156, PAGE_W - 36, 178)
    page.draw_rect(inst_rect, color=SILVER_LIGHT, fill=WHITE, width=0.7)
    page.draw_rect(pymupdf.Rect(36, 156, 39.5, 178), color=None, fill=CHARCOAL)
    add_text(
        page,
        (48, 161, PAGE_W - 48, 176),
        "PRO TIP:  Click or tap any square checkbox below to check it off digitally, or print this page and check items with a pen!",
        font="PJS-Semi",
        size=8.2,
        color=CHARCOAL_LIGHT,
    )

    if len(items) <= 10:
        cy = 188
        row_h = 48
        gap = 7
        for idx, item_text in enumerate(items, 1):
            row_rect = pymupdf.Rect(36, cy, PAGE_W - 36, cy + row_h)
            page.draw_rect(row_rect, color=SILVER_LIGHT, fill=WHITE, width=0.7)
            page.draw_rect(pymupdf.Rect(36, cy, 39.5, cy + row_h), color=None, fill=CHARCOAL)

            cb_rect = pymupdf.Rect(50, cy + (row_h - 18) / 2, 68, cy + (row_h + 18) / 2)
            page.draw_rect(cb_rect, color=CHARCOAL, fill=IVORY, width=1.1)

            w = pymupdf.Widget()
            w.field_name = f"chk_{slug}_{idx:02d}"
            w.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
            w.rect = cb_rect
            w.border_color = (0.12, 0.16, 0.20)
            w.border_width = 1.1
            w.fill_color = (0.98, 0.97, 0.96)
            w.text_color = (0.12, 0.16, 0.20)
            w.field_value = False
            page.add_widget(w)

            top_pad = 15 if len(item_text) < 82 else 9
            add_text(
                page,
                (78, cy + top_pad, PAGE_W - 48, cy + row_h - 4),
                item_text,
                font="PJS-Med",
                size=9.8,
                color=CHARCOAL,
                lineheight=1.28,
            )
            cy += row_h + gap

        notes_box = pymupdf.Rect(36, cy + 4, PAGE_W - 36, 706)
        page.draw_rect(notes_box, color=SILVER_LIGHT, fill=WHITE, width=0.8)
        page.draw_rect(pymupdf.Rect(36, cy + 4, 39.5, 706), color=None, fill=CHARCOAL)
        add_text(
            page,
            (48, cy + 10, 440, cy + 26),
            "HOMEOWNER NOTES & SERVICE PRO REMINDERS (FILLABLE):",
            font="PJS-Bold",
            size=8.2,
            color=CHARCOAL,
        )
        nf = pymupdf.Widget()
        nf.field_name = f"txt_{slug}_notes"
        nf.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        nf.field_flags = pymupdf.PDF_TX_FIELD_IS_MULTILINE
        nf.rect = pymupdf.Rect(48, cy + 28, PAGE_W - 48, 698)
        nf.text_color = (0.12, 0.16, 0.20)
        nf.fill_color = (0.98, 0.97, 0.96)
        nf.border_color = (0.80, 0.80, 0.80)
        nf.border_width = 0.7
        nf.text_fontsize = 9.5
        nf.field_value = ""
        page.add_widget(nf)

    else:
        start_y = 188
        col_w = (PAGE_W - 72 - 14) / 2.0
        row_h = 45.0
        gap_y = 6.2

        for idx, item_text in enumerate(items, 1):
            col_idx = 0 if idx <= 10 else 1
            row_idx = (idx - 1) if idx <= 10 else (idx - 11)
            x0 = 36 + col_idx * (col_w + 14)
            y0 = start_y + row_idx * (row_h + gap_y)

            row_rect = pymupdf.Rect(x0, y0, x0 + col_w, y0 + row_h)
            page.draw_rect(row_rect, color=SILVER_LIGHT, fill=WHITE, width=0.7)
            page.draw_rect(pymupdf.Rect(x0, y0, x0 + 3.0, y0 + row_h), color=None, fill=CHARCOAL)

            cb_rect = pymupdf.Rect(x0 + 11, y0 + (row_h - 16) / 2, x0 + 27, y0 + (row_h + 16) / 2)
            page.draw_rect(cb_rect, color=CHARCOAL, fill=IVORY, width=1.1)

            w = pymupdf.Widget()
            w.field_name = f"chk_{slug}_{idx:02d}"
            w.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
            w.rect = cb_rect
            w.border_color = (0.12, 0.16, 0.20)
            w.border_width = 1.1
            w.fill_color = (0.98, 0.97, 0.96)
            w.text_color = (0.12, 0.16, 0.20)
            w.field_value = False
            page.add_widget(w)

            top_pad = 14.5 if len(item_text) < 42 else 8.5
            add_text(
                page,
                (x0 + 34, y0 + top_pad, x0 + col_w - 8, y0 + row_h - 3),
                item_text,
                font="PJS-Med",
                size=9.0,
                color=CHARCOAL,
                lineheight=1.22,
            )

    # Branded Checklist Footer Bar
    f_rect = pymupdf.Rect(36, 718, PAGE_W - 36, 764)
    page.draw_rect(f_rect, color=SILVER_LIGHT, fill=CHARCOAL, width=0.8)

    insert_editorial_photo(
        page,
        (48, 723, 84, 759),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=2,
        bg_rgb=CHARCOAL_255,
        centering=(0.5, 0.2),
        grade=False,
        border_rgb=(192, 192, 192),
        border_px=1,
    )
    add_text(
        page,
        (94, 724, 430, 742),
        "Your Trusted REALTOR®  —  Lokesh Chanana (Loki)",
        font="PF-Bold",
        size=11.0,
        color=IVORY,
    )
    add_text(
        page,
        (94, 742, 480, 758),
        "Need a trusted local contractor or service pro? Call/Text (801) 860-1052  •  lokeshchanana.com",
        font="PJS-Med",
        size=8.3,
        color=SILVER,
    )
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(310, 740, 395, 758), "uri": "tel:+18018601052"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(400, 740, 500, 758), "uri": "https://lokeshchanana.com"})

    add_text(
        page,
        (PAGE_W - 92, 732, PAGE_W - 48, 752),
        f"PAGE {page_num:02d}",
        font="PF-Bold",
        size=8.5,
        color=IVORY,
        align=2,
    )


def build_page_22_back_cover(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    paint_ivory_canvas(page)

    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 6), color=None, fill=CHARCOAL)

    # Top Hero Image
    back_hero_img = f"{ASSET_V2_DIR}/site_north.jpg" if os.path.exists(f"{ASSET_V2_DIR}/arch_appliances.jpg") else f"{ASSET_V2_DIR}/site_eastside.jpg"
    insert_editorial_photo(
        page,
        (36, 32, PAGE_W - 36, 318),
        back_hero_img,
        radius=2,
        bg_rgb=IVORY_255,
    )

    # Main Closing Editorial Card (White on Ivory with Charcoal left accent)
    card = pymupdf.Rect(36, 334, PAGE_W - 36, 580)
    page.draw_rect(card, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    page.draw_rect(pymupdf.Rect(36, 334, PAGE_W - 36, 338), color=None, fill=CHARCOAL)

    draw_kicker_badge(page, 36, 354, "HERE FOR YOU BEYOND THE SALE", align_center=True)

    add_text(
        page,
        (56, 382, PAGE_W - 56, 420),
        "I'm Only a Phone Call Away!",
        font="PF-Bold",
        size=25.0,
        color=CHARCOAL,
        align=1,
    )
    add_text(
        page,
        (56, 418, PAGE_W - 56, 444),
        "Welcome home.",
        font="PF-Ital",
        size=15.0,
        color=CHARCOAL_LIGHT,
        align=1,
    )

    closing_msg = (
        "If you have any questions or need recommendations for reliable service pros, don't hesitate to reach out. I am always here to help!\n\n"
        "Wishing you lots of happiness, laughter, and great memories in your new home.\n\n"
        "I'd love to stay in touch, and look forward to seeing you soon.\n"
        "— Lokesh Chanana (Loki)"
    )
    add_text(
        page,
        (68, 448, PAGE_W - 68, 570),
        closing_msg,
        font="PJS-Reg",
        size=10.5,
        color=CHARCOAL_LIGHT,
        align=1,
        lineheight=1.42,
    )

    # Bottom Agent Business Card (Crisp White & Charcoal Editorial Card)
    bcard = pymupdf.Rect(36, 596, PAGE_W - 36, 752)
    page.draw_rect(bcard, color=SILVER_LIGHT, fill=CHARCOAL, width=0.8)

    insert_editorial_photo(
        page,
        (56, 614, 152, 734),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=2,
        bg_rgb=CHARCOAL_255,
        centering=(0.5, 0.2),
        grade=False,
        border_rgb=(192, 192, 192),
        border_px=2,
    )

    add_text(page, (172, 616, 430, 634), "YOUR TRUSTED REALTOR®", font="PJS-Bold", size=8.0, color=SILVER)
    add_text(page, (172, 632, 430, 662), "Lokesh Chanana (Loki)", font="PF-Bold", size=18.5, color=IVORY)
    add_text(page, (172, 660, 430, 678), "Real Broker LLC  •  License #26006634", font="PJS-Med", size=9.2, color=SILVER)

    add_text(page, (172, 684, 430, 702), "CALL / TEXT:  (801) 860-1052", font="PJS-Bold", size=9.8, color=IVORY)
    add_text(page, (172, 702, 430, 720), "EMAIL:  lokesh@lokeshchanana.com", font="PJS-Med", size=9.4, color=SILVER_LIGHT)
    add_text(page, (172, 720, 430, 738), "WEB:  https://lokeshchanana.com", font="PJS-Bold", size=9.4, color=IVORY)

    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(172, 683, 340, 702), "uri": "tel:+18018601052"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(172, 702, 380, 720), "uri": "mailto:lokesh@lokeshchanana.com"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(172, 720, 380, 738), "uri": "https://lokeshchanana.com"})

    insert_logo(page, (455, 616, 555, 680), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=CHARCOAL_255, target_rgb=IVORY_255)
    insert_logo(page, (462, 690, 548, 726), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=CHARCOAL_255, target_rgb=IVORY_255, is_real_logo=True)


def main():
    doc = pymupdf.open()

    build_page_01_cover(doc)
    build_page_02_welcome(doc)
    build_page_03_invest(doc)
    build_page_04_repairs(doc)
    build_page_05_structure(doc)
    build_page_06_electrical(doc)
    build_page_07_plumbing(doc)
    build_page_08_hvac(doc)
    build_page_09_appliances(doc)
    build_page_10_interior(doc)
    build_page_11_curb_appeal(doc)
    build_page_12_security(doc)
    build_page_13_energy(doc)
    build_page_14_preventative(doc)
    build_page_15_diy_or_pros(doc)
    build_page_16_divider(doc)

    pest_items = [
        "Seal all entry points with rodent-resistant materials, focusing on gaps around pipes, vents, and foundations",
        "Eliminate food sources. Store pet food, bird-seed, and pantry items in airtight containers, and secure trash bins with tight-fitting lids",
        "Trim vegetation 3+ feet from structures, prune overhanging branches, and replace dense landscaping with gravel or open plants to remove shelter",
        "Fix moisture issues like leaks in basements or crawl spaces to deter pests seeking water",
        "Store firewood 18\" off the ground to discourage burrowing pests",
        "Conduct monthly inspections for signs of pests such as droppings, gnaw marks, or nests in attics, basements, and behind appliances",
        "Declutter storage areas and keep equipment and materials elevated and away from the walls to reduce potential nesting sites",
        "If necessary, consult with a pest management company to formulate a plan to remove and prevent any issues",
    ]
    build_checklist_page(
        doc,
        17,
        "pest",
        "Preventing Pest Issues",
        "Proactive steps to keep your home's exterior envelope pest-free all year long",
        f"{ASSET_V2_DIR}/arch_modern_ext.jpg",
        pest_items,
    )

    spring_img = f"{ASSET_V2_DIR}/pnw_spring_estate.jpg" if os.path.exists(f"{ASSET_V2_DIR}/pnw_spring_estate.jpg") else f"{ASSET_V2_DIR}/arch_spring_home.jpg"
    spring_items = [
        "Inspect roof for winter damage (shingles, flashing)",
        "Clean gutters and downspouts for spring rains",
        "Service HVAC system and replace filters",
        "Test sprinklers and irrigation systems",
        "Inspect and repair deck/patio for winter damage",
        "Wash windows and clean screens",
        "Pressure wash driveway, patio, and wash siding. Hose down exterior AC unit",
        "Prune trees and shrubs; remove dead branches",
        "Reseed and fertilize lawn",
        "Inspect exterior for cracks, peeling paint, or water damage",
        "Inspect foundation for cracks and repair as needed",
        "Check attic and crawl space for moisture or pest problems",
        "Clean and inspect outdoor furniture for damage",
        "Inspect fences and gates for any needed repairs",
        "Clean and service lawn equipment",
        "Inspect hoses and outdoor faucets for leaks",
        "Refill fire extinguishers and check expiration dates",
        "Replace batteries in smoke alarms and carbon monoxide detectors",
        "Clean or replace air filters in range hood",
        "Prepare outdoor entertainment areas for summer",
    ]
    build_checklist_page(
        doc,
        18,
        "spring",
        "Spring Home Maintenance",
        "Refresh your home after winter and get ready for warmer days",
        spring_img,
        spring_items,
    )

    summer_img = f"{ASSET_V2_DIR}/pnw_summer_estate.jpg" if os.path.exists(f"{ASSET_V2_DIR}/pnw_summer_estate.jpg") else f"{ASSET_V2_DIR}/arch_summer_patio.jpg"
    summer_items = [
        "Inspect and clean air conditioner coils and filters",
        "Test and repair outdoor lighting",
        "Inspect fences and gates for damage",
        "Check attic for proper ventilation and cooling",
        "Start the backup generator, refresh on how it works",
        "Inspect windows for broken seals or leaks",
        "Deep clean carpets and upholstery",
        "Inspect outdoor play equipment for safety",
        "Trim trees and bushes to prevent overgrowth",
        "Clean and service grill/barbecue",
        "Check for signs of pests in and around the home",
        "Service lawn mower and sharpen blades",
        "Water lawn and plants early in the day to prevent evaporation",
        "Check weatherstripping around doors and windows",
        "Inspect garage and basement for signs of moisture or mold",
        "Clean exterior dryer vent to remove any built-up lint",
        "Check roof for summer storm damage",
        "Inspect outdoor faucets and hoses for leaks",
        "Organize and clean outdoor sheds or storage spaces",
        "Vacuum and wipe freezer and refrigerator coils",
    ]
    build_checklist_page(
        doc,
        19,
        "summer",
        "Summer Home Maintenance",
        "Keep your home cool, efficient, and ready for summer living",
        summer_img,
        summer_items,
    )

    fall_img = f"{ASSET_V2_DIR}/pnw_fall_estate.jpg" if os.path.exists(f"{ASSET_V2_DIR}/pnw_fall_estate.jpg") else f"{ASSET_V2_DIR}/site_north.jpg"
    fall_items = [
        "Clean gutters and downspouts after leaves fall",
        "Inspect roof for any signs of damage",
        "Winterize outdoor faucets and irrigation systems",
        "Check weatherstripping on doors and windows",
        "Clean and service chimney and fireplace",
        "Replace furnace filter and service heating system",
        "Test smoke and carbon monoxide detectors",
        "Drain and store garden hoses",
        "Rake leaves and compost or dispose of them",
        "Aerate and fertilize the lawn",
        "Store outdoor furniture and equipment",
        "Check attic insulation and ventilation",
        "Inspect crawl spaces for pests or moisture issues",
        "Deep clean and organize the garage or shed",
        "Trim trees and shrubs before winter storms",
        "Install storm windows or ensure windows are properly sealed",
        "Clean outdoor lighting fixtures and replace bulbs",
        "Inspect foundation for cracks and repair if needed",
        "Test sump pump for proper operation",
        "Inspect driveway and walkways for cracks, and repair if necessary",
    ]
    build_checklist_page(
        doc,
        20,
        "fall",
        "Fall Home Maintenance",
        "Prepare your home's heating, exterior, and drainage before winter arrives",
        fall_img,
        fall_items,
    )

    winter_img = f"{ASSET_V2_DIR}/pnw_winter_estate.jpg" if os.path.exists(f"{ASSET_V2_DIR}/pnw_winter_estate.jpg") else f"{ASSET_V2_DIR}/pnw_winter_lux.jpg"
    winter_items = [
        "Inspect roof for snow or ice damage",
        "Clean gutters and remove icicles",
        "Test smoke and carbon monoxide detectors",
        "Replace furnace filter for optimal heating",
        "Check for drafts and seal windows/doors",
        "Insulate exposed pipes to prevent freezing",
        "Check and refill water softener",
        "Test sump pump for proper operation",
        "Inspect attic insulation and add more if needed",
        "Lubricate garage door tracks and moving parts",
        "Inspect fireplace and chimney for creosote buildup",
        "Clean dryer vents to avoid fire risks",
        "Check outdoor lighting for safety and functionality",
        "Inspect indoor plumbing for leaks or corrosion",
        "Deep clean kitchen appliances (oven, fridge)",
        "Inspect and clean exhaust fans in kitchen and bathrooms",
        "Store or cover outdoor furniture",
        "Organize and clean garage or storage spaces",
        "Test home security systems for reliability",
        "Ensure emergency kit is fully stocked and accessible",
    ]
    build_checklist_page(
        doc,
        21,
        "winter",
        "Winter Home Maintenance",
        "Protect your home from cold weather, freezing pipes, and winter storms",
        winter_img,
        winter_items,
    )

    build_page_22_back_cover(doc)

    doc.set_metadata({
        "title": "Home Maintenance Guide — Lokesh Chanana (Loki) | Real Broker LLC",
        "author": "Lokesh Chanana (Loki) — REALTOR®, Real Broker LLC",
        "subject": "Interactive Seasonal Home Maintenance Guide & Checklists",
        "keywords": "Home Maintenance, Checklist, Lokesh Chanana, Real Broker, Seattle Real Estate",
    })

    out_pdf = f"{PUBLIC_DIR}/home-maintenance-guide-classic.pdf" if EDITION == "classic" else f"{PUBLIC_DIR}/home-maintenance-guide.pdf"
    doc.subset_fonts()
    doc.save(out_pdf, garbage=3, deflate=True)
    sz_mb = os.path.getsize(out_pdf) / (1024 * 1024)
    print(f"Successfully generated {out_pdf} ({len(doc)} pages, {sz_mb:.2f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Home Maintenance Guide PDF")
    parser.add_argument("--edition", choices=["luxury", "classic"], default="luxury", help="Photo edition to build")
    args = parser.parse_args()
    EDITION = args.edition
    if EDITION == "classic":
        ASSET_V2_DIR = "/tmp/guide_assets_classic"
        DEFAULT_SAT = 0.72
    main()
