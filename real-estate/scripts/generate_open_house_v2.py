#!/usr/bin/env python3
"""
Measured Threshold — 28" x 18" Landscape Open House Sign (v2)
Redesigned from scratch combining canvas-design philosophy with loki-brand-design.
Outputs print-ready PDFs (0.125" bleed + crop marks) and trimmed 150 DPI PNGs
for Standard, Left, and Right directional variants.
"""

import io
import math
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

SPLIT_X = 1158.0

OUTPUT_DIR = "/home/lokesh/Casa-poki/real-estate/output"


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


def draw_crosshair(page, x, y, size=10.0, color=CHARCOAL_LIGHT, width=0.9):
    page.draw_line(pymupdf.Point(tx(x - size), ty(y)), pymupdf.Point(tx(x + size), ty(y)), color=color, width=width)
    page.draw_line(pymupdf.Point(tx(x), ty(y - size)), pymupdf.Point(tx(x), ty(y + size)), color=color, width=width)


def draw_architectural_field(page):
    """Etch subtle blueprint grid, door-swing threshold arcs, and registration ticks into the Charcoal field."""
    # Subtle vertical & horizontal datum lines
    for gx in [92.0, 358.0, 624.0, 890.0]:
        page.draw_line(
            pymupdf.Point(tx(gx), 0),
            pymupdf.Point(tx(gx), CANVAS_H),
            color=CHARCOAL_LIGHT,
            width=0.6,
        )
    for gy in [210.0, 480.0, 750.0, 1020.0]:
        page.draw_line(
            pymupdf.Point(0, ty(gy)),
            pymupdf.Point(tx(SPLIT_X), ty(gy)),
            color=CHARCOAL_LIGHT,
            width=0.6,
        )

    # Door-swing architectural quarter-arcs anchored at bottom-left threshold (92, 1210)
    ox, oy = 92.0, 1210.0
    for radius, w in [(880.0, 1.0), (660.0, 0.7), (440.0, 0.6)]:
        pts = []
        steps = 64
        for i in range(steps + 1):
            ang = -math.pi / 2.0 + (math.pi / 2.0) * (i / steps)
            px = ox + radius * math.cos(ang)
            py = oy + radius * math.sin(ang)
            if px <= SPLIT_X:
                pts.append(pymupdf.Point(tx(px), ty(py)))
        if len(pts) > 1:
            page.draw_polyline(pts, color=CHARCOAL_LIGHT, width=w, closePath=False)

    # Subtle registration crosshairs
    draw_crosshair(page, 92.0, 210.0, size=9.0, color=SILVER_DARK, width=0.9)
    draw_crosshair(page, 890.0, 210.0, size=9.0, color=SILVER_DARK, width=0.9)
    draw_crosshair(page, 890.0, 1020.0, size=9.0, color=SILVER_DARK, width=0.9)


def draw_arrow(page, direction, x0, cy, width=250.0, height=130.0, color=IVORY):
    """Draw a crisp architectural directional arrow."""
    hh = height / 2.0
    shaft_h = height * 0.30
    hsh = shaft_h / 2.0
    head_w = width * 0.44

    if direction == "left":
        tip_x = x0
        neck_x = x0 + head_w
        tail_x = x0 + width
    else:
        tip_x = x0 + width
        neck_x = tip_x - head_w
        tail_x = x0

    pts = [
        pymupdf.Point(tx(tip_x), ty(cy)),
        pymupdf.Point(tx(neck_x), ty(cy - hh)),
        pymupdf.Point(tx(neck_x), ty(cy - hsh)),
        pymupdf.Point(tx(tail_x), ty(cy - hsh)),
        pymupdf.Point(tx(tail_x), ty(cy + hsh)),
        pymupdf.Point(tx(neck_x), ty(cy + hsh)),
        pymupdf.Point(tx(neck_x), ty(cy + hh)),
    ]
    page.draw_polyline(pts, color=None, fill=color, closePath=True)


def draw_corner_brackets(page, x0, y0, x1, y1, arm=16.0, color=CHARCOAL, width=2.2):
    """Draw crisp architectural L-brackets around the QR frame."""
    corners = [
        (x0, y0, 1, 1),
        (x1, y0, -1, 1),
        (x0, y1, 1, -1),
        (x1, y1, -1, -1),
    ]
    for cx, cy, dx, dy in corners:
        page.draw_line(pymupdf.Point(tx(cx), ty(cy)), pymupdf.Point(tx(cx + dx * arm), ty(cy)), color=color, width=width)
        page.draw_line(pymupdf.Point(tx(cx), ty(cy)), pymupdf.Point(tx(cx), ty(cy + dy * arm)), color=color, width=width)


def build_sign(direction=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    suffix = f"_{direction.capitalize()}" if direction else ""
    pdf_path = os.path.join(OUTPUT_DIR, f"Open_House_Sign_28x18_v2{suffix}_Print.pdf")
    png_path = os.path.join(OUTPUT_DIR, f"Open_House_Sign_28x18_v2{suffix}.png")

    doc = pymupdf.open()
    page = doc.new_page(width=CANVAS_W, height=CANVAS_H)
    register_fonts(page)

    # 1. Base Split Fields (Full Bleed)
    page.draw_rect(pymupdf.Rect(0, 0, tx(SPLIT_X), CANVAS_H), color=None, fill=CHARCOAL)
    page.draw_rect(pymupdf.Rect(tx(SPLIT_X), 0, CANVAS_W, CANVAS_H), color=None, fill=IVORY)

    # Architectural background geometry on Charcoal field
    draw_architectural_field(page)

    # Vertical Silver Datum Divider
    page.draw_rect(
        pymupdf.Rect(tx(SPLIT_X - 2.0), 0, tx(SPLIT_X + 2.0), CANVAS_H),
        color=None,
        fill=SILVER,
    )

    # 2. Left Monumental Charcoal Field
    rc_plate = add_text(
        page,
        tr(92, 74, SPLIT_X - 60, 120),
        "PLATE 01   •   THRESHOLD   •   47.6062° N",
        font="PJS-Bold",
        size=15.0,
        color=SILVER,
        align=0,
    )
    assert rc_plate >= 0

    rc_open = add_text(
        page,
        tr(84, 215, SPLIT_X - 40, 520),
        "OPEN",
        font="PF-Bold",
        size=225.0,
        color=IVORY,
        align=0,
        lineheight=1.0,
    )
    rc_house = add_text(
        page,
        tr(84, 445, SPLIT_X - 40, 750),
        "HOUSE",
        font="PF-Bold",
        size=225.0,
        color=IVORY,
        align=0,
        lineheight=1.0,
    )
    assert rc_open >= 0 and rc_house >= 0, f"Display overflow: {rc_open}, {rc_house}"

    # Direction / Welcome Gesture below HOUSE
    if direction == "left":
        draw_arrow(page, "left", x0=92.0, cy=855.0, width=250.0, height=124.0, color=IVORY)
        rc_dir = add_text(
            page,
            tr(380, 842, SPLIT_X - 60, 895),
            "THIS WAY   •   FOLLOW SIGNS",
            font="PJS-Bold",
            size=24.0,
            color=SILVER,
            align=0,
        )
        assert rc_dir >= 0
    elif direction == "right":
        rc_dir = add_text(
            page,
            tr(92, 842, 700, 895),
            "FOLLOW SIGNS   •   THIS WAY",
            font="PJS-Bold",
            size=24.0,
            color=SILVER,
            align=0,
        )
        draw_arrow(page, "right", x0=740.0, cy=855.0, width=250.0, height=124.0, color=IVORY)
        assert rc_dir >= 0
    else:
        pill_x0, pill_y0, pill_w, pill_h = 92.0, 808.0, 420.0, 54.0
        page.draw_rect(
            tr(pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h),
            color=SILVER,
            fill=CHARCOAL_DARK,
            width=1.6,
        )
        rc_wel = add_text(
            page,
            tr(pill_x0, pill_y0 + 13.0, pill_x0 + pill_w, pill_y0 + pill_h + 8.0),
            "W E L C O M E   •   C O M E   O N   I N",
            font="PJS-Bold",
            size=19.0,
            color=IVORY,
            align=1,
        )
        assert rc_wel >= 0

    # Bottom-left architectural scale notation
    page.draw_line(
        pymupdf.Point(tx(92), ty(1176)),
        pymupdf.Point(tx(320), ty(1176)),
        color=SILVER_DARK,
        width=1.2,
    )
    add_text(
        page,
        tr(92, 1188, 700, 1230),
        "GREATER SEATTLE & EASTSIDE",
        font="PJS-Semi",
        size=15.0,
        color=SILVER_DARK,
        align=0,
    )

    # 3. Right Ivory Gallery Field
    rx0 = SPLIT_X + 76.0   # 1234.0
    rx1 = TRIM_W - 76.0    # 1940.0

    # Subtle right-edge elevation ticks
    for ty_tick in [120.0, 360.0, 600.0, 840.0, 1080.0]:
        page.draw_line(
            pymupdf.Point(tx(TRIM_W - 22), ty(ty_tick)),
            pymupdf.Point(tx(TRIM_W), ty(ty_tick)),
            color=SILVER,
            width=1.0,
        )

    rc_pres = add_text(
        page,
        tr(rx0, 74, rx1, 110),
        "PRESENTED BY",
        font="PJS-Bold",
        size=14.5,
        color=SILVER_DARK,
        align=0,
    )
    rc_name = add_text(
        page,
        tr(rx0, 110, rx1, 200),
        "LOKESH CHANANA",
        font="PF-Bold",
        size=54.0,
        color=CHARCOAL,
        align=0,
    )
    rc_cred = add_text(
        page,
        tr(rx0, 184, rx1, 226),
        "(LOKI)   •   REALTOR®   •   REAL BROKER LLC",
        font="PJS-Bold",
        size=17.5,
        color=CHARCOAL_LIGHT,
        align=0,
    )
    assert rc_pres >= 0 and rc_name >= 0 and rc_cred >= 0

    page.draw_line(
        pymupdf.Point(tx(rx0), ty(244)),
        pymupdf.Point(tx(rx1), ty(244)),
        color=SILVER_LIGHT,
        width=1.5,
    )

    # Massive Street-Legible Phone + Website
    rc_phone = add_text(
        page,
        tr(rx0, 276, rx1, 405),
        "(801) 860-1052",
        font="PJS-Extra",
        size=78.0,
        color=CHARCOAL,
        align=0,
    )
    rc_web = add_text(
        page,
        tr(rx0, 384, rx1, 455),
        "lokeshchanana.com",
        font="PF-Ital",
        size=36.0,
        color=CHARCOAL_LIGHT,
        align=0,
    )
    assert rc_phone >= 0 and rc_web >= 0

    page.draw_line(
        pymupdf.Point(tx(rx0), ty(472)),
        pymupdf.Point(tx(rx1), ty(472)),
        color=SILVER_LIGHT,
        width=1.5,
    )

    # QR Code Frame (200 x 200 pt = 2.78" x 2.78") with Architectural Corner Brackets
    qr_size = 200.0
    qr_x0 = rx0 + 10.0
    qr_y0 = 524.0
    page.draw_rect(
        tr(qr_x0 - 10, qr_y0 - 10, qr_x0 + qr_size + 10, qr_y0 + qr_size + 10),
        color=SILVER_LIGHT,
        fill=(1.0, 1.0, 1.0),
        width=1.2,
    )
    draw_corner_brackets(page, qr_x0 - 10, qr_y0 - 10, qr_x0 + qr_size + 10, qr_y0 + qr_size + 10)
    page.insert_image(
        tr(qr_x0, qr_y0, qr_x0 + qr_size, qr_y0 + qr_size),
        stream=make_qr_png("https://lokeshchanana.com"),
    )

    # QR Side Copy
    qcopy_x0 = qr_x0 + qr_size + 38.0
    rc_qk = add_text(
        page,
        tr(qcopy_x0, 536, rx1, 572),
        "SCAN FOR LISTINGS",
        font="PJS-Bold",
        size=15.0,
        color=SILVER_DARK,
        align=0,
    )
    rc_qh = add_text(
        page,
        tr(qcopy_x0, 572, rx1, 676),
        "View Photos, Pricing & Property Details",
        font="PF-Bold",
        size=28.0,
        color=CHARCOAL,
        align=0,
        lineheight=1.2,
    )
    rc_qs = add_text(
        page,
        tr(qcopy_x0, 678, rx1, 745),
        "Or call or text Loki directly anytime.",
        font="PJS-Reg",
        size=18.5,
        color=CHARCOAL_LIGHT,
        align=0,
    )
    assert rc_qk >= 0 and rc_qh >= 0 and rc_qs >= 0

    page.draw_line(
        pymupdf.Point(tx(rx0), ty(792)),
        pymupdf.Point(tx(rx1), ty(792)),
        color=SILVER_LIGHT,
        width=1.5,
    )

    # Co-Branded Logo Anchor
    insert_logo(
        page,
        tr(rx0, 845, rx0 + 270, 1085),
        os.path.join(PUBLIC_DIR, "lc-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=False,
    )
    page.draw_line(
        pymupdf.Point(tx(rx0 + 318), ty(875)),
        pymupdf.Point(tx(rx0 + 318), ty(1055)),
        color=SILVER_LIGHT,
        width=1.5,
    )
    insert_logo(
        page,
        tr(rx0 + 365, 865, rx1, 1065),
        os.path.join(PUBLIC_DIR, "real-logo.png"),
        bg_rgb=IVORY_255,
        target_rgb=CHARCOAL_255,
        is_real_logo=True,
    )

    rc_lic = add_text(
        page,
        tr(rx0, 1176, rx1, 1225),
        "REAL BROKER LLC   •   WA LICENSE #26006634",
        font="PJS-Semi",
        size=15.0,
        color=SILVER_DARK,
        align=0,
    )
    assert rc_lic >= 0

    draw_crop_marks(page)

    doc.save(pdf_path, garbage=4, deflate=True)

    trim_clip = pymupdf.Rect(BLEED, BLEED, BLEED + TRIM_W, BLEED + TRIM_H)
    pix = page.get_pixmap(dpi=150, clip=trim_clip)
    pix.save(png_path)
    doc.close()

    print(f"Saved PDF: {pdf_path}")
    print(f"Saved PNG: {png_path} ({pix.width}x{pix.height} px)")


if __name__ == "__main__":
    for d in [None, "left", "right"]:
        build_sign(direction=d)
