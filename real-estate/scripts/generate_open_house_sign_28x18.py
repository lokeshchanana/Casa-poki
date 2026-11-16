#!/usr/bin/env python3
"""
Generate a Print-Ready 28" x 18" Landscape Open House Sign (PDF with Bleed + Trimmed PNG)
for Lokesh Chanana (Loki) — Real Broker LLC.
Follows BRAND_GUIDELINES.md (Section 9.3) and loki-brand-design/brand_toolkit.py.
"""

import io
import os
import sys
import pymupdf
import qrcode

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

# 28" x 18" Landscape Trim Dimensions (72 pt = 1 inch) + 0.125" (9 pt) Bleed
BLEED = 9.0
TRIM_W = 28.0 * 72.0   # 2016.0 pt
TRIM_H = 18.0 * 72.0   # 1296.0 pt
CANVAS_W = TRIM_W + 2 * BLEED  # 2034.0 pt
CANVAS_H = TRIM_H + 2 * BLEED  # 1314.0 pt

OUTPUT_DIR = "/home/lokesh/Casa-poki/real-estate/output"
PDF_PATH = os.path.join(OUTPUT_DIR, "Open_House_Sign_28x18_Print.pdf")
PNG_PATH = os.path.join(OUTPUT_DIR, "Open_House_Sign_28x18.png")


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
    """Draw subtle corner crop marks at the 28" x 18" trim boundary."""
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

    # 2. Top Charcoal Header Banner (full-bleed top, 354 pt inside trim)
    header_bottom = 354.0
    page.draw_rect(
        pymupdf.Rect(0, 0, CANVAS_W, ty(header_bottom)),
        color=None,
        fill=CHARCOAL,
    )
    page.draw_rect(
        pymupdf.Rect(0, ty(header_bottom), CANVAS_W, ty(header_bottom + 6.0)),
        color=None,
        fill=SILVER,
    )

    # Outlined Kicker Pill
    pill_w, pill_h = 460.0, 42.0
    pill_x0 = (TRIM_W - pill_w) / 2.0
    pill_y0 = 40.0
    page.draw_rect(
        tr(pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h),
        color=SILVER,
        fill=CHARCOAL_DARK,
        width=1.6,
    )
    rc_pill = add_text(
        page,
        tr(pill_x0, pill_y0 + 9.0, pill_x0 + pill_w, pill_y0 + pill_h + 6.0),
        "W E L C O M E   •   C O M E   O N   I N",
        font="PJS-Bold",
        size=19.0,
        color=IVORY,
        align=1,
    )
    assert rc_pill >= 0, f"Pill text overflow: {rc_pill}"

    # Massive Single-Line OPEN HOUSE Headline
    rc_title = add_text(
        page,
        tr(40, 100, TRIM_W - 40, 345),
        "OPEN HOUSE",
        font="PF-Bold",
        size=195.0,
        color=IVORY,
        align=1,
        lineheight=1.0,
    )
    assert rc_title >= 0, f"Title text overflow: {rc_title}"

    # 3. Middle Signature Card on Ivory Field
    card_x0, card_y0 = 72.0, 412.0
    card_x1, card_y1 = TRIM_W - 72.0, 976.0
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

    # Left Zone: Agent Identity, Phone & Website
    left_x0 = card_x0 + 64.0
    left_x1 = 1410.0

    rc_name = add_text(
        page,
        tr(left_x0, 452, left_x1, 560),
        "LOKESH CHANANA",
        font="PF-Bold",
        size=74.0,
        color=CHARCOAL,
        align=1,
    )
    rc_cred = add_text(
        page,
        tr(left_x0, 548, left_x1, 600),
        "(LOKI)   •   REALTOR®   •   REAL BROKER LLC",
        font="PJS-Bold",
        size=22.0,
        color=CHARCOAL_LIGHT,
        align=1,
    )

    page.draw_line(
        pymupdf.Point(tx(left_x0 + 40), ty(616)),
        pymupdf.Point(tx(left_x1 - 40), ty(616)),
        color=SILVER_LIGHT,
        width=1.8,
    )

    rc_phone = add_text(
        page,
        tr(left_x0, 646, left_x1, 825),
        "(801) 860-1052",
        font="PJS-Extra",
        size=114.0,
        color=CHARCOAL,
        align=1,
    )
    rc_web = add_text(
        page,
        tr(left_x0, 816, left_x1, 895),
        "lokeshchanana.com",
        font="PF-Semi",
        size=44.0,
        color=CHARCOAL_LIGHT,
        align=1,
    )
    assert rc_name >= 0 and rc_cred >= 0 and rc_phone >= 0 and rc_web >= 0, (
        f"Left card text overflow: {rc_name}, {rc_cred}, {rc_phone}, {rc_web}"
    )

    # Vertical Divider inside card
    div_x = 1455.0
    page.draw_line(
        pymupdf.Point(tx(div_x), ty(card_y0 + 48)),
        pymupdf.Point(tx(div_x), ty(card_y1 - 48)),
        color=SILVER_LIGHT,
        width=1.8,
    )

    # Right Zone: QR Code + Scan Prompt
    right_cx = (div_x + card_x1) / 2.0
    qr_size = 240.0
    qr_x0 = right_cx - qr_size / 2.0
    qr_y0 = 468.0
    page.draw_rect(
        tr(qr_x0 - 10, qr_y0 - 10, qr_x0 + qr_size + 10, qr_y0 + qr_size + 10),
        color=SILVER_LIGHT,
        fill=WHITE,
        width=1.5,
    )
    page.insert_image(
        tr(qr_x0, qr_y0, qr_x0 + qr_size, qr_y0 + qr_size),
        stream=make_qr_png("https://lokeshchanana.com"),
    )

    pill2_w, pill2_h = 310.0, 38.0
    pill2_x0 = right_cx - pill2_w / 2.0
    pill2_y0 = 752.0
    page.draw_rect(
        tr(pill2_x0, pill2_y0, pill2_x0 + pill2_w, pill2_y0 + pill2_h),
        color=SILVER_LIGHT,
        fill=IVORY,
        width=1.4,
    )
    rc_qr_kicker = add_text(
        page,
        tr(pill2_x0, pill2_y0 + 8.0, pill2_x0 + pill2_w, pill2_y0 + pill2_h + 6.0),
        "SCAN FOR LISTINGS & INFO",
        font="PJS-Bold",
        size=16.5,
        color=CHARCOAL,
        align=1,
    )
    rc_qr_sub = add_text(
        page,
        tr(div_x + 30, 812, card_x1 - 30, 910),
        "View Photos, Pricing & Details",
        font="PF-Bold",
        size=29.0,
        color=CHARCOAL,
        align=1,
        lineheight=1.2,
    )
    assert rc_qr_kicker >= 0 and rc_qr_sub >= 0, (
        f"Right card text overflow: {rc_qr_kicker}, {rc_qr_sub}"
    )

    # 4. Bottom Co-Branded Footer
    insert_logo(
        page,
        tr(96, 1006, 366, 1236),
        os.path.join(PUBLIC_DIR, "lc-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=False,
    )

    rc_comp = add_text(
        page,
        tr(420, 1106, TRIM_W - 420, 1165),
        "REAL BROKER LLC   •   WA LICENSE #26006634   •   GREATER SEATTLE & EASTSIDE",
        font="PJS-Semi",
        size=20.0,
        color=SILVER_DARK,
        align=1,
    )
    assert rc_comp >= 0, f"Compliance text overflow: {rc_comp}"

    insert_logo(
        page,
        tr(TRIM_W - 416, 1020, TRIM_W - 96, 1220),
        os.path.join(PUBLIC_DIR, "real-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=True,
    )

    # Bottom Crown Bar (20 pt inside trim + bleed)
    page.draw_rect(
        pymupdf.Rect(0, ty(TRIM_H - 20.0), CANVAS_W, CANVAS_H),
        color=None,
        fill=CHARCOAL,
    )

    draw_crop_marks(page)

    doc.save(PDF_PATH, garbage=4, deflate=True)

    # Render Trimmed 28" x 18" PNG at 150 DPI (4200 x 2700 px)
    trim_clip = pymupdf.Rect(BLEED, BLEED, BLEED + TRIM_W, BLEED + TRIM_H)
    pix = page.get_pixmap(dpi=150, clip=trim_clip)
    pix.save(PNG_PATH)
    doc.close()

    print(f"Saved PDF: {PDF_PATH}")
    print(f"Saved PNG: {PNG_PATH} ({pix.width}x{pix.height} px)")


if __name__ == "__main__":
    build_sign()
