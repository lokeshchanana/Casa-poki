#!/usr/bin/env python3
"""
Measured Threshold — 24" x 6" Real Estate SOLD Rider
Generates a print-ready PDF (with 0.125" bleed & crop marks) and a trimmed 150 DPI PNG
for Lokesh Chanana (Loki) — Real Broker LLC.
"""

import math
import os
import sys
import pymupdf

SKILL_SCRIPTS = "/home/lokesh/Casa-poki/.agents/skills/loki-brand-design/scripts"
sys.path.insert(0, SKILL_SCRIPTS)

from brand_toolkit import (
    CHARCOAL,
    CHARCOAL_255,
    CHARCOAL_LIGHT,
    IVORY,
    IVORY_255,
    PUBLIC_DIR,
    SILVER,
    SILVER_DARK,
    SILVER_LIGHT,
    add_text,
    insert_logo,
    register_fonts,
)

# Standard 24" W x 6" H Rider Trim Dimensions (72 pt = 1 inch) + 0.125" (9 pt) Bleed
BLEED = 9.0
TRIM_W = 24.0 * 72.0   # 1728.0 pt
TRIM_H = 6.0 * 72.0    # 432.0 pt
CANVAS_W = TRIM_W + 2 * BLEED  # 1746.0 pt
CANVAS_H = TRIM_H + 2 * BLEED  # 450.0 pt

SPLIT_X = 1040.0

OUTPUT_DIR = "/home/lokesh/Casa-poki/real-estate/output"
PDF_PATH = os.path.join(OUTPUT_DIR, "Sold_Rider_24x6_Print.pdf")
PNG_PATH = os.path.join(OUTPUT_DIR, "Sold_Rider_24x6.png")


def tx(x):
    return x + BLEED


def ty(y):
    return y + BLEED


def tr(x0, y0, x1, y1):
    return pymupdf.Rect(tx(x0), ty(y0), tx(x1), ty(y1))


def draw_crop_marks(page):
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


def draw_crosshair(page, x, y, size=7.0, color=SILVER_DARK, width=0.8):
    page.draw_line(pymupdf.Point(tx(x - size), ty(y)), pymupdf.Point(tx(x + size), ty(y)), color=color, width=width)
    page.draw_line(pymupdf.Point(tx(x), ty(y - size)), pymupdf.Point(tx(x), ty(y + size)), color=color, width=width)


def draw_architectural_lintel(page):
    """Etch subtle blueprint grid and threshold arc into the Charcoal field."""
    for gx in [72.0, 314.0, 556.0, 798.0]:
        page.draw_line(pymupdf.Point(tx(gx), 0), pymupdf.Point(tx(gx), CANVAS_H), color=CHARCOAL_LIGHT, width=0.6)
    for gy in [96.0, 216.0, 336.0]:
        page.draw_line(pymupdf.Point(0, ty(gy)), pymupdf.Point(tx(SPLIT_X), ty(gy)), color=CHARCOAL_LIGHT, width=0.6)

    # Quarter-arc anchored at bottom-left (72, 390)
    ox, oy = 72.0, 390.0
    for radius in [340.0, 230.0]:
        pts = []
        for i in range(49):
            ang = -math.pi / 2.0 + (math.pi / 2.0) * (i / 48.0)
            pts.append(pymupdf.Point(tx(ox + radius * math.cos(ang)), ty(oy + radius * math.sin(ang))))
        page.draw_polyline(pts, color=CHARCOAL_LIGHT, width=0.7, closePath=False)

    draw_crosshair(page, 72.0, 96.0)
    draw_crosshair(page, 798.0, 336.0)


def build_rider():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=CANVAS_W, height=CANVAS_H)
    register_fonts(page)

    # 1. Split Architectural Canvas (Full Bleed)
    page.draw_rect(pymupdf.Rect(0, 0, tx(SPLIT_X), CANVAS_H), color=None, fill=CHARCOAL)
    page.draw_rect(pymupdf.Rect(tx(SPLIT_X), 0, CANVAS_W, CANVAS_H), color=None, fill=IVORY)

    draw_architectural_lintel(page)

    # Vertical Silver Datum Rule
    page.draw_rect(
        pymupdf.Rect(tx(SPLIT_X - 1.75), 0, tx(SPLIT_X + 1.75), CANVAS_H),
        color=None,
        fill=SILVER,
    )

    # 2. Left Charcoal Field: Monumental SOLD
    rc_kicker = add_text(
        page,
        tr(72, 46, SPLIT_X - 48, 76),
        "MILESTONE   •   REPRESENTED BY LOKI",
        font="PJS-Bold",
        size=13.0,
        color=SILVER,
        align=0,
    )
    rc_sold = add_text(
        page,
        tr(64, 72, SPLIT_X - 40, 375),
        "SOLD",
        font="PF-Bold",
        size=230.0,
        color=IVORY,
        align=0,
        lineheight=1.0,
    )
    rc_sub = add_text(
        page,
        tr(72, 368, SPLIT_X - 48, 400),
        "THINKING OF SELLING?   CALL OR TEXT ANYTIME",
        font="PJS-Semi",
        size=13.0,
        color=SILVER_DARK,
        align=0,
    )
    assert rc_kicker >= 0 and rc_sold >= 0 and rc_sub >= 0, (
        f"Left field overflow: {rc_kicker}, {rc_sold}, {rc_sub}"
    )

    # 3. Right Ivory Field: Contact & Co-Branded Logos
    rx0 = SPLIT_X + 46.0  # 1086.0
    rx1 = TRIM_W - 210.0  # 1518.0 (leaves room on far right for LC + Real logos)

    rc_name = add_text(
        page,
        tr(rx0, 56, rx1, 112),
        "LOKESH CHANANA",
        font="PF-Bold",
        size=36.0,
        color=CHARCOAL,
        align=0,
    )
    rc_cred = add_text(
        page,
        tr(rx0, 102, rx1, 134),
        "(LOKI)   •   REALTOR®",
        font="PJS-Bold",
        size=14.0,
        color=CHARCOAL_LIGHT,
        align=0,
    )

    page.draw_line(
        pymupdf.Point(tx(rx0), ty(144)),
        pymupdf.Point(tx(rx1 - 20), ty(144)),
        color=SILVER_LIGHT,
        width=1.2,
    )

    rc_phone = add_text(
        page,
        tr(rx0, 162, rx1, 240),
        "(801) 860-1052",
        font="PJS-Extra",
        size=46.0,
        color=CHARCOAL,
        align=0,
    )
    rc_web = add_text(
        page,
        tr(rx0, 228, rx1, 276),
        "lokeshchanana.com",
        font="PF-Ital",
        size=24.0,
        color=CHARCOAL_LIGHT,
        align=0,
    )

    page.draw_line(
        pymupdf.Point(tx(rx0), ty(292)),
        pymupdf.Point(tx(rx1 - 20), ty(292)),
        color=SILVER_LIGHT,
        width=1.2,
    )

    rc_lic = add_text(
        page,
        tr(rx0, 322, rx1, 360),
        "REAL BROKER LLC   •   WA LIC #26006634",
        font="PJS-Semi",
        size=13.0,
        color=SILVER_DARK,
        align=0,
    )
    assert rc_name >= 0 and rc_cred >= 0 and rc_phone >= 0 and rc_web >= 0 and rc_lic >= 0

    # Far-right stacked Co-Branded Logos (LC + Real Broker)
    logo_x0 = TRIM_W - 196.0
    logo_x1 = TRIM_W - 44.0
    page.draw_line(
        pymupdf.Point(tx(logo_x0 - 22), ty(56)),
        pymupdf.Point(tx(logo_x0 - 22), ty(TRIM_H - 56)),
        color=SILVER_LIGHT,
        width=1.2,
    )
    insert_logo(
        page,
        tr(logo_x0, 56, logo_x1, 210),
        os.path.join(PUBLIC_DIR, "lc-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=False,
    )
    insert_logo(
        page,
        tr(logo_x0, 245, logo_x1, 365),
        os.path.join(PUBLIC_DIR, "real-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=True,
    )

    draw_crop_marks(page)

    doc.save(PDF_PATH, garbage=4, deflate=True)

    trim_clip = pymupdf.Rect(BLEED, BLEED, BLEED + TRIM_W, BLEED + TRIM_H)
    pix = page.get_pixmap(dpi=150, clip=trim_clip)
    pix.save(PNG_PATH)
    doc.close()

    print(f"Saved PDF: {PDF_PATH}")
    print(f"Saved PNG: {PNG_PATH} ({pix.width}x{pix.height} px)")


if __name__ == "__main__":
    build_rider()
