#!/usr/bin/env python3
"""
Lokesh Chanana (Loki) — Reusable Brand & PDF Design Toolkit
===========================================================
Provides the exact color tokens, typography helpers, alpha-mask logo renderer,
editorial photo color-grading pipeline, and structural card/header/footer builders
used across Loki's print & digital marketing collateral.
"""

import io
import os
import pymupdf
from PIL import Image, ImageDraw, ImageOps, ImageEnhance
import numpy as np

# Standard US Letter Print Dimensions (72 pt = 1 inch)
PAGE_W = 612.0  # 8.5 in
PAGE_H = 792.0  # 11.0 in

# ==============================================================================
# 1. BRAND COLOR TOKENS (Light Mode, Dark Mode & Print)
# ==============================================================================

# Primary Light Mode / Print Surfaces
IVORY = (250 / 255, 248 / 255, 245 / 255)          # #FAF8F5 (bg-ivory)
IVORY_255 = (250, 248, 245)
IVORY_DARK = (229 / 255, 225 / 255, 219 / 255)     # #E5E1DB (bg-ivory-dark)
IVORY_DARK_255 = (229, 225, 219)
WHITE = (1.0, 1.0, 1.0)                            # #FFFFFF (bg-white)
WHITE_255 = (255, 255, 255)

# Primary Ink (Light Mode) & Primary Surfaces (Dark Mode)
CHARCOAL = (31 / 255, 41 / 255, 51 / 255)          # #1F2933 (charcoal)
CHARCOAL_255 = (31, 41, 51)
CHARCOAL_DARK = (21 / 255, 28 / 255, 35 / 255)     # #151C23 (charcoal-dark)
CHARCOAL_DARK_255 = (21, 28, 35)
CHARCOAL_LIGHT = (45 / 255, 58 / 255, 71 / 255)    # #2D3A47 (charcoal-light)
CHARCOAL_LIGHT_255 = (45, 58, 71)

# Metallic Silver & Neutral Borders
SILVER = (192 / 255, 192 / 255, 192 / 255)         # #C0C0C0 (silver)
SILVER_255 = (192, 192, 192)
SILVER_DARK = (140 / 255, 142 / 255, 145 / 255)    # #8C8E91 (print silver-dark)
SILVER_WEB_DARK = (160 / 255, 160 / 255, 160 / 255)# #A0A0A0 (web silver-dark)
SILVER_LIGHT = (224 / 255, 224 / 255, 224 / 255)   # #E0E0E0 (silver-light border)
SILVER_BORDER_255 = (214, 211, 205)                # #D6D3CD (2px photo frame)

# Secondary Email / Digital Accent Tokens
EMAIL_NAVY = (15 / 255, 23 / 255, 42 / 255)        # #0F172A
EMAIL_CYAN = (6 / 255, 182 / 255, 212 / 255)       # #06B6D4
EMAIL_SKY = (56 / 255, 189 / 255, 248 / 255)       # #38BDF8

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


# ==============================================================================
# 2. TYPOGRAPHY & CANVAS HELPERS
# ==============================================================================

def register_fonts(page):
    for name, path in FONTS.items():
        if os.path.exists(path):
            page.insert_font(fontname=name, fontfile=path)


def paint_ivory_canvas(page, w=PAGE_W, h=PAGE_H):
    page.draw_rect(pymupdf.Rect(0, 0, w, h), color=None, fill=IVORY)


def add_text(page, rect, text, font="PJS-Reg", size=10.0, color=CHARCOAL_LIGHT, align=0, lineheight=1.28):
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
    return rc


# ==============================================================================
# 3. EDITORIAL PHOTO COLOR-GRADING & FRAMING PIPELINE
# ==============================================================================

def editorial_grade(im, sat=0.72, contrast=1.05):
    """
    Harmonize photography to match Lokesh Chanana's Brand System:
    - 72% saturation for warm, relatable Puget Sound neighborhood homes (or 58% for luxury)
    - 105% micro-contrast boost
    - 16% split-tone blend toward Warm Ivory (#FAF8F5) highlights & Charcoal (#1F2933) shadows
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
    sat=0.72,
    border_rgb=SILVER_BORDER_255,
    border_px=2,
):
    r = pymupdf.Rect(rect)
    scale = 2.4
    w_px = max(1, int(round(r.width * scale)))
    h_px = max(1, int(round(r.height * scale)))
    rad_px = int(round(radius * scale))

    im = Image.open(src_path).convert("RGB")
    fitted = ImageOps.fit(im, (w_px, h_px), method=Image.Resampling.LANCZOS, centering=centering)

    if grade:
        fitted = editorial_grade(fitted, sat=sat)

    if dark_gradient:
        overlay = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(h_px):
            t = y / max(1, h_px - 1)
            alpha = int(115 + 115 * (t ** 1.1))
            draw_ov.line([(0, y), (w_px, y)], fill=(31, 41, 51, alpha))
        fitted = Image.alpha_composite(fitted.convert("RGBA"), overlay).convert("RGB")

    if ivory_fade_bottom:
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
    bg.save(buf, format="JPEG", quality=88, optimize=True)
    page.insert_image(r, stream=buf.getvalue())


# ==============================================================================
# 4. ALPHA-MASK LOGO RENDERER (Zero Rectangular Box Artifacts)
# ==============================================================================

def insert_logo(page, rect, src_path, bg_rgb=IVORY_255, target_rgb=CHARCOAL_255, is_real_logo=False):
    r = pymupdf.Rect(rect)
    im = Image.open(src_path).convert("RGBA")
    arr = np.array(im, dtype=np.float32)

    if is_real_logo:
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        alpha = np.clip((250.0 - lum) / 220.0, 0.0, 1.0)
    else:
        alpha = arr[:, :, 3] / 255.0

    out = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    for c in range(3):
        out[:, :, c] = np.clip(
            bg_rgb[c] * (1.0 - alpha) + target_rgb[c] * alpha, 0, 255
        ).astype(np.uint8)

    pil_out = Image.fromarray(out, "RGB")
    scale = 3.0
    box_w = max(1, int(round(r.width * scale)))
    box_h = max(1, int(round(r.height * scale)))
    contained = ImageOps.contain(pil_out, (box_w, box_h), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (box_w, box_h), bg_rgb)
    ox = (box_w - contained.width) // 2
    oy = (box_h - contained.height) // 2
    canvas.paste(contained, (ox, oy))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    page.insert_image(r, stream=buf.getvalue())


# ==============================================================================
# 5. SIGNATURE STRUCTURAL COMPONENTS
# ==============================================================================

def draw_kicker_badge(page, x, y, text, align_center=False, page_w=PAGE_W):
    w = max(110, len(text) * 4.9 + 22)
    h = 17
    bx = (page_w - w) / 2.0 if align_center else x
    badge = pymupdf.Rect(bx, y, bx + w, y + h)
    page.draw_rect(badge, color=SILVER_LIGHT, fill=WHITE, width=0.8)
    add_text(
        page,
        (bx + 4, y + 3.2, bx + w - 4, y + h),
        text.upper(),
        font="PJS-Bold",
        size=7.4,
        color=CHARCOAL,
        align=1 if align_center else 0,
    )
    return y + h + 8


def draw_running_chrome(page, page_num, section_label, right_title="Brand & Design Guidelines"):
    paint_ivory_canvas(page)
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 5), color=None, fill=CHARCOAL)
    add_text(
        page,
        (36, 14, 380, 30),
        f"LOKESH CHANANA   •   {section_label.upper()}",
        font="PJS-Bold",
        size=7.5,
        color=CHARCOAL,
    )
    add_text(
        page,
        (360, 13, PAGE_W - 36, 30),
        right_title,
        font="PF-Ital",
        size=8.5,
        color=SILVER_DARK,
        align=2,
    )
    page.draw_line(pymupdf.Point(36, 32), pymupdf.Point(PAGE_W - 36, 32), color=SILVER_LIGHT, width=0.8)

    page.draw_line(pymupdf.Point(36, PAGE_H - 36), pymupdf.Point(PAGE_W - 36, PAGE_H - 36), color=SILVER_LIGHT, width=0.8)
    add_text(
        page,
        (36, PAGE_H - 28, 460, PAGE_H - 12),
        "Lokesh Chanana (Loki)  •  REALTOR®  •  Real Broker LLC   |   (801) 860-1052   |   lokeshchanana.com",
        font="PJS-Med",
        size=7.8,
        color=CHARCOAL_LIGHT,
    )
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
        size=22.0,
        color=CHARCOAL,
        lineheight=1.12,
    )
    cur_y += 30
    if subtitle:
        add_text(
            page,
            (36, cur_y, PAGE_W - 36, cur_y + 40),
            subtitle,
            font="PJS-Reg",
            size=9.8,
            color=CHARCOAL_LIGHT,
            lineheight=1.35,
        )
        cur_y += 34
    return cur_y


def draw_numbered_card(page, rect, num, title, body, bg=WHITE):
    r = pymupdf.Rect(rect)
    page.draw_rect(r, color=SILVER_LIGHT, fill=bg, width=0.8)
    page.draw_rect(pymupdf.Rect(r.x0, r.y0, r.x0 + 3.5, r.y1), color=None, fill=CHARCOAL)

    badge = pymupdf.Rect(r.x0 + 13, r.y0 + 11, r.x0 + 35, r.y0 + 33)
    page.draw_rect(badge, color=SILVER_LIGHT, fill=IVORY, width=0.7)
    add_text(
        page,
        (badge.x0, badge.y0 + 3.5, badge.x1, badge.y1),
        f"{num:02d}" if isinstance(num, int) else str(num),
        font="PF-Bold",
        size=9.2,
        color=CHARCOAL,
        align=1,
    )

    add_text(
        page,
        (r.x0 + 44, r.y0 + 9, r.x1 - 12, r.y0 + 28),
        title,
        font="PF-Bold",
        size=11.2,
        color=CHARCOAL,
    )
    add_text(
        page,
        (r.x0 + 44, r.y0 + 26, r.x1 - 12, r.y1 - 6),
        body,
        font="PJS-Reg",
        size=9.2,
        color=CHARCOAL_LIGHT,
        lineheight=1.32,
    )
