#!/usr/bin/env python3
"""
24" x 6" Co-Listing SOLD BY Rider — Remade in Lokesh Chanana's Brand Design Style
Combines the layout structure of Lokesh's existing rider (SOLD BY left, Co-listing Agent /
Lokesh Chanana (Loki) / 801.860.1052 / Lakhani Team + Real Broker LLC) with the
Ivory / Charcoal / Silver palette, Playfair Display + Plus Jakarta Sans typography,
and alpha-masked logos from BRAND_GUIDELINES.md.
"""

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

# 24" W x 6" H Trim + 0.125" (9 pt) Bleed
BLEED = 9.0
TRIM_W = 24.0 * 72.0   # 1728.0 pt
TRIM_H = 6.0 * 72.0    # 432.0 pt
CANVAS_W = TRIM_W + 2 * BLEED
CANVAS_H = TRIM_H + 2 * BLEED

SPLIT_X = 420.0

OUTPUT_DIR = "/home/lokesh/Casa-poki/real-estate/output"
PDF_PATH = os.path.join(OUTPUT_DIR, "Rider_Sold_By_Loki_Style_24x6_Print.pdf")
PNG_PATH = os.path.join(OUTPUT_DIR, "Rider_Sold_By_Loki_Style_24x6.png")


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


def build_rider():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=CANVAS_W, height=CANVAS_H)
    register_fonts(page)

    # 1. Split Architectural Canvas (Full Bleed)
    page.draw_rect(pymupdf.Rect(0, 0, tx(SPLIT_X), CANVAS_H), color=None, fill=CHARCOAL)
    page.draw_rect(pymupdf.Rect(tx(SPLIT_X), 0, CANVAS_W, CANVAS_H), color=None, fill=IVORY)

    # Subtle blueprint grid lines inside Charcoal block
    for gx in [64.0, 210.0, 356.0]:
        page.draw_line(pymupdf.Point(tx(gx), 0), pymupdf.Point(tx(gx), CANVAS_H), color=CHARCOAL_LIGHT, width=0.6)
    for gy in [96.0, 216.0, 336.0]:
        page.draw_line(pymupdf.Point(0, ty(gy)), pymupdf.Point(tx(SPLIT_X), ty(gy)), color=CHARCOAL_LIGHT, width=0.6)

    # Vertical Silver Datum Divider
    page.draw_rect(
        pymupdf.Rect(tx(SPLIT_X - 2.0), 0, tx(SPLIT_X + 2.0), CANVAS_H),
        color=None,
        fill=SILVER,
    )

    # 2. Left Charcoal Block: SOLD BY
    rc_sold = add_text(
        page,
        tr(20, 96, SPLIT_X - 20, 275),
        "SOLD",
        font="PF-Bold",
        size=122.0,
        color=IVORY,
        align=1,
        lineheight=1.0,
    )
    rc_by = add_text(
        page,
        tr(20, 250, SPLIT_X - 20, 330),
        "BY",
        font="PF-Bold",
        size=48.0,
        color=SILVER,
        align=1,
        lineheight=1.0,
    )
    # Flanking Silver lines beside BY
    page.draw_line(pymupdf.Point(tx(68), ty(282)), pymupdf.Point(tx(148), ty(282)), color=SILVER, width=1.8)
    page.draw_line(pymupdf.Point(tx(272), ty(282)), pymupdf.Point(tx(352), ty(282)), color=SILVER, width=1.8)
    assert rc_sold >= 0 and rc_by >= 0

    # 3. Right Ivory Field
    rx0 = SPLIT_X + 48.0   # 468.0
    rx1 = TRIM_W - 44.0    # 1684.0

    # Top-Left: Co-listing Agent & Name
    rc_role = add_text(
        page,
        tr(rx0, 44, 1240, 72),
        "CO-LISTING AGENT",
        font="PJS-Bold",
        size=15.0,
        color=SILVER_DARK,
        align=0,
    )
    rc_name = add_text(
        page,
        tr(rx0, 68, 1260, 160),
        "Lokesh Chanana (Loki)",
        font="PF-Bold",
        size=64.0,
        color=CHARCOAL,
        align=0,
    )
    assert rc_role >= 0 and rc_name >= 0

    # Top-Right: Alpha-masked Lakhani Team + Real Broker LLC logos
    insert_logo(
        page,
        tr(1310, 40, 1445, 134),
        os.path.join(PUBLIC_DIR, "lakhani-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=False,
    )
    page.draw_line(
        pymupdf.Point(tx(1465), ty(46)),
        pymupdf.Point(tx(1465), ty(128)),
        color=SILVER_LIGHT,
        width=1.4,
    )
    insert_logo(
        page,
        tr(1485, 46, rx1, 126),
        os.path.join(PUBLIC_DIR, "real-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=True,
    )
    rc_brok = add_text(
        page,
        tr(1280, 138, rx1, 166),
        "REAL BROKER LLC   •   WA LIC #26006634",
        font="PJS-Semi",
        size=13.0,
        color=CHARCOAL_LIGHT,
        align=2,
    )
    assert rc_brok >= 0

    # Horizontal Divider
    page.draw_line(
        pymupdf.Point(tx(rx0), ty(176)),
        pymupdf.Point(tx(rx1), ty(176)),
        color=SILVER_LIGHT,
        width=1.5,
    )

    # Massive Street-Legible Phone Number
    rc_phone = add_text(
        page,
        tr(rx0, 186, rx1, 392),
        "801.860.1052",
        font="PJS-Extra",
        size=150.0,
        color=CHARCOAL,
        align=0,
        lineheight=1.0,
    )
    assert rc_phone >= 0, f"Phone overflow: {rc_phone}"

    # Outer 12 pt Charcoal Frame (full bleed around all 4 sides)
    bw = 12.0
    page.draw_rect(pymupdf.Rect(0, 0, CANVAS_W, ty(bw)), color=None, fill=CHARCOAL)
    page.draw_rect(pymupdf.Rect(0, ty(TRIM_H - bw), CANVAS_W, CANVAS_H), color=None, fill=CHARCOAL)
    page.draw_rect(pymupdf.Rect(0, 0, tx(bw), CANVAS_H), color=None, fill=CHARCOAL)
    page.draw_rect(pymupdf.Rect(tx(TRIM_W - bw), 0, CANVAS_W, CANVAS_H), color=None, fill=CHARCOAL)

    # Inset Architectural Frame (Silver on Charcoal side, Charcoal on Ivory side)
    inset = 22.0
    page.draw_polyline(
        [
            pymupdf.Point(tx(SPLIT_X), ty(inset)),
            pymupdf.Point(tx(inset), ty(inset)),
            pymupdf.Point(tx(inset), ty(TRIM_H - inset)),
            pymupdf.Point(tx(SPLIT_X), ty(TRIM_H - inset)),
        ],
        color=SILVER,
        width=2.4,
        closePath=False,
    )
    page.draw_polyline(
        [
            pymupdf.Point(tx(SPLIT_X), ty(inset)),
            pymupdf.Point(tx(TRIM_W - inset), ty(inset)),
            pymupdf.Point(tx(TRIM_W - inset), ty(TRIM_H - inset)),
            pymupdf.Point(tx(SPLIT_X), ty(TRIM_H - inset)),
        ],
        color=CHARCOAL,
        width=2.4,
        closePath=False,
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
