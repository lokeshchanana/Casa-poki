#!/usr/bin/env python3
"""
Generate a Print-Ready 18" x 28" Open House Sign (PDF with Bleed + Trimmed PNG)
for Lokesh Chanana (Loki) — Real Broker LLC.
Follows BRAND_GUIDELINES.md (Section 9.3) and loki-brand-design/brand_toolkit.py.
"""

import io
import os
import sys
import pymupdf
import qrcode
from PIL import Image

SKILL_SCRIPTS = "/home/lokesh/Casa-poki/.agents/skills/loki-brand-design/scripts"
sys.path.insert(0, SKILL_SCRIPTS)

from brand_toolkit import (
    CHARCOAL,
    CHARCOAL_255,
    CHARCOAL_DARK,
    CHARCOAL_LIGHT,
    IVORY,
    IVORY_255,
    PUBLIC_DIR,
    SILVER,
    SILVER_DARK,
    SILVER_LIGHT,
    WHITE,
    WHITE_255,
    add_text,
    insert_logo,
    register_fonts,
)

# 18" x 28" Trim Dimensions (72 pt = 1 inch) + 0.125" (9 pt) Bleed
BLEED = 9.0
TRIM_W = 18.0 * 72.0   # 1296.0 pt
TRIM_H = 28.0 * 72.0   # 2016.0 pt
CANVAS_W = TRIM_W + 2 * BLEED  # 1314.0 pt
CANVAS_H = TRIM_H + 2 * BLEED  # 2034.0 pt

OUTPUT_DIR = "/home/lokesh/Casa-poki/real-estate/output"
PDF_PATH = os.path.join(OUTPUT_DIR, "Open_House_Sign_18x28_Print.pdf")
PNG_PATH = os.path.join(OUTPUT_DIR, "Open_House_Sign_18x28.png")


def tx(x):
    return x + BLEED


def ty(y):
    return y + BLEED


def tr(x0, y0, x1, y1):
    return pymupdf.Rect(tx(x0), ty(y0), tx(x1), ty(y1))


def make_qr_png(url, fill_rgb=CHARCOAL_255, back_rgb=WHITE_255):
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=24,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_rgb, back_color=back_rgb).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def draw_crop_marks(page):
    """Draw subtle corner crop marks at the 18" x 28" trim boundary."""
    mark_len = 6.0
    for cx, cy, dx, dy in [
        (BLEED, BLEED, -1, -1),
        (BLEED + TRIM_W, BLEED, 1, -1),
        (BLEED, BLEED + TRIM_H, -1, 1),
        (BLEED + TRIM_W, BLEED + TRIM_H, 1, 1),
    ]:
        page.draw_line(
            pymupdf.Point(cx, cy + dy * 2),
            pymupdf.Point(cx, cy + dy * (2 + mark_len)),
            color=SILVER_DARK,
            width=0.5,
        )
        page.draw_line(
            pymupdf.Point(cx + dx * 2, cy),
            pymupdf.Point(cx + dx * (2 + mark_len), cy),
            color=SILVER_DARK,
            width=0.5,
        )


def build_sign():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=CANVAS_W, height=CANVAS_H)
    register_fonts(page)

    # 1. Full-bleed Warm Ivory Canvas
    page.draw_rect(pymupdf.Rect(0, 0, CANVAS_W, CANVAS_H), color=None, fill=IVORY)

    # 2. Top Charcoal Header Block (full-bleed top, 570 pt inside trim)
    header_bottom = 570.0
    page.draw_rect(
        pymupdf.Rect(0, 0, CANVAS_W, ty(header_bottom)),
        color=None,
        fill=CHARCOAL,
    )
    # 6 pt Silver accent rule below header
    page.draw_rect(
        pymupdf.Rect(0, ty(header_bottom), CANVAS_W, ty(header_bottom + 6.0)),
        color=None,
        fill=SILVER,
    )

    # Outlined Kicker Pill inside header
    pill_w, pill_h = 460.0, 48.0
    pill_x0 = (TRIM_W - pill_w) / 2.0
    pill_y0 = 76.0
    page.draw_rect(
        tr(pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h),
        color=SILVER,
        fill=CHARCOAL_DARK,
        width=1.6,
    )
    add_text(
        page,
        tr(pill_x0, pill_y0 + 11.0, pill_x0 + pill_w, pill_y0 + pill_h),
        "W E L C O M E   •   C O M E   O N   I N",
        font="PJS-Bold",
        size=20.0,
        color=IVORY,
        align=1,
    )

    # Massive Stacked OPEN HOUSE Title (readable at 40-50 ft)
    rc1 = add_text(
        page,
        tr(40, 145, TRIM_W - 40, 410),
        "OPEN",
        font="PF-Bold",
        size=180.0,
        color=IVORY,
        align=1,
        lineheight=1.0,
    )
    rc2 = add_text(
        page,
        tr(40, 330, TRIM_W - 40, 580),
        "HOUSE",
        font="PF-Bold",
        size=180.0,
        color=IVORY,
        align=1,
        lineheight=1.0,
    )
    assert rc1 >= 0 and rc2 >= 0, f"Header text overflow: {rc1}, {rc2}"

    # 3. Middle Signature Card on Ivory Field
    card_x0, card_y0 = 72.0, 646.0
    card_x1, card_y1 = TRIM_W - 72.0, 1474.0
    page.draw_rect(
        tr(card_x0, card_y0, card_x1, card_y1),
        color=SILVER_LIGHT,
        fill=WHITE,
        width=2.0,
    )
    # 14 pt Charcoal Left Accent Bar
    page.draw_rect(
        tr(card_x0, card_y0, card_x0 + 14.0, card_y1),
        color=None,
        fill=CHARCOAL,
    )

    inner_x0 = card_x0 + 56.0
    inner_x1 = card_x1 - 44.0

    # Agent Name & Credentials
    rc_name = add_text(
        page,
        tr(inner_x0, 676, inner_x1, 795),
        "LOKESH CHANANA",
        font="PF-Bold",
        size=66.0,
        color=CHARCOAL,
        align=1,
    )
    rc_cred = add_text(
        page,
        tr(inner_x0, 770, inner_x1, 825),
        "(LOKI)   •   REALTOR®   •   REAL BROKER LLC",
        font="PJS-Bold",
        size=22.0,
        color=CHARCOAL_LIGHT,
        align=1,
    )

    # Divider 1
    page.draw_line(
        pymupdf.Point(tx(inner_x0 + 40), ty(842)),
        pymupdf.Point(tx(inner_x1 - 40), ty(842)),
        color=SILVER_LIGHT,
        width=1.8,
    )

    # Massive Phone Number (40-50 ft legibility)
    rc_phone = add_text(
        page,
        tr(inner_x0, 864, inner_x1, 1020),
        "(801) 860-1052",
        font="PJS-Extra",
        size=96.0,
        color=CHARCOAL,
        align=1,
    )
    assert rc_name >= 0 and rc_cred >= 0 and rc_phone >= 0, (
        f"Card text overflow: {rc_name}, {rc_cred}, {rc_phone}"
    )

    # Website
    add_text(
        page,
        tr(inner_x0, 1004, inner_x1, 1068),
        "lokeshchanana.com",
        font="PF-Semi",
        size=42.0,
        color=CHARCOAL_LIGHT,
        align=1,
    )

    # Divider 2
    page.draw_line(
        pymupdf.Point(tx(inner_x0 + 40), ty(1096)),
        pymupdf.Point(tx(inner_x1 - 40), ty(1096)),
        color=SILVER_LIGHT,
        width=1.8,
    )

    # QR Code Block (3.2" x 3.2" = 230 x 230 pt)
    qr_size = 230.0
    qr_x0 = inner_x0 + 54.0
    qr_y0 = 1152.0
    qr_rect = tr(qr_x0, qr_y0, qr_x0 + qr_size, qr_y0 + qr_size)
    page.draw_rect(
        tr(qr_x0 - 10, qr_y0 - 10, qr_x0 + qr_size + 10, qr_y0 + qr_size + 10),
        color=SILVER_LIGHT,
        fill=WHITE,
        width=1.5,
    )
    page.insert_image(qr_rect, stream=make_qr_png("https://lokeshchanana.com"))

    # QR Copy Block
    copy_x0 = qr_x0 + qr_size + 46.0
    # Small Kicker Pill
    page.draw_rect(
        tr(copy_x0, 1166, copy_x0 + 286, 1206),
        color=SILVER_LIGHT,
        fill=IVORY,
        width=1.4,
    )
    add_text(
        page,
        tr(copy_x0 + 12, 1175, copy_x0 + 280, 1204),
        "SCAN FOR LISTINGS & INFO",
        font="PJS-Bold",
        size=16.5,
        color=CHARCOAL,
        align=0,
    )
    add_text(
        page,
        tr(copy_x0, 1222, inner_x1 - 20, 1310),
        "View Photos, Pricing & Details",
        font="PF-Bold",
        size=34.0,
        color=CHARCOAL,
        align=0,
        lineheight=1.15,
    )
    add_text(
        page,
        tr(copy_x0, 1316, inner_x1 - 20, 1410),
        "Point your phone camera at the code or call/text Loki directly anytime.",
        font="PJS-Reg",
        size=22.0,
        color=CHARCOAL_LIGHT,
        align=0,
        lineheight=1.32,
    )

    # 4. Bottom Co-Branded Footer (LC + Real Broker LLC)
    page.draw_line(
        pymupdf.Point(tx(72), ty(1538)),
        pymupdf.Point(tx(TRIM_W - 72), ty(1538)),
        color=SILVER_LIGHT,
        width=1.8,
    )

    insert_logo(
        page,
        tr(130, 1585, 450, 1865),
        os.path.join(PUBLIC_DIR, "lc-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=False,
    )

    page.draw_line(
        pymupdf.Point(tx(TRIM_W / 2.0), ty(1610)),
        pymupdf.Point(tx(TRIM_W / 2.0), ty(1840)),
        color=SILVER_LIGHT,
        width=2.0,
    )

    insert_logo(
        page,
        tr(740, 1605, 1166, 1845),
        os.path.join(PUBLIC_DIR, "real-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=True,
    )

    # Compliance Footer Line
    add_text(
        page,
        tr(72, 1906, TRIM_W - 72, 1948),
        "REAL BROKER LLC   •   WA LICENSE #26006634   •   GREATER SEATTLE & EASTSIDE",
        font="PJS-Semi",
        size=18.0,
        color=SILVER_DARK,
        align=1,
    )

    # Bottom Crown Bar (24 pt inside trim + bleed)
    page.draw_rect(
        pymupdf.Rect(0, ty(TRIM_H - 24.0), CANVAS_W, CANVAS_H),
        color=None,
        fill=CHARCOAL,
    )

    # Corner Crop Marks (only visible in bleed margin)
    draw_crop_marks(page)

    doc.save(PDF_PATH, garbage=4, deflate=True)

    # Render Trimmed 18" x 28" PNG at 150 DPI (2700 x 4200 px)
    trim_clip = pymupdf.Rect(BLEED, BLEED, BLEED + TRIM_W, BLEED + TRIM_H)
    pix = page.get_pixmap(dpi=150, clip=trim_clip)
    pix.save(PNG_PATH)
    doc.close()

    print(f"Saved PDF: {PDF_PATH}")
    print(f"Saved PNG: {PNG_PATH} ({pix.width}x{pix.height} px)")


if __name__ == "__main__":
    build_sign()
