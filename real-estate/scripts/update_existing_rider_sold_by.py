#!/usr/bin/env python3
"""
Replace the QR code in Lokesh's existing navy/cyan rider with 'SOLD BY',
preserving the exact layout, colors, and branding, and export both PNG and 24"x6" Print PDF.
"""

import io
import os
import pymupdf
from PIL import Image, ImageDraw, ImageFont

SRC_IMG = "/home/lokesh/.gemini/antigravity-cli/brain/1d1622d5-e6f6-4cbe-8ea7-6c35c0080d69/.user_uploaded/media_1794876277833_a97dbf7d.png"
FONT_EXTRA = "/tmp/guide_assets/fonts/PlusJakartaSans-ExtraBold.ttf"
FONT_BOLD = "/tmp/guide_assets/fonts/PlusJakartaSans-Bold.ttf"

OUTPUT_DIR = "/home/lokesh/Casa-poki/real-estate/output"
PNG_PATH = os.path.join(OUTPUT_DIR, "Existing_Rider_Sold_By.png")
PDF_PATH = os.path.join(OUTPUT_DIR, "Existing_Rider_Sold_By_24x6_Print.pdf")

NAVY_RGB = (6, 14, 61)
CYAN_RGB = (5, 181, 234)
WHITE_RGB = (255, 255, 255)


def build():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base = Image.open(SRC_IMG).convert("RGB")
    w, h = base.size  # 1024 x 256

    # Supersample 4x for razor-sharp typography in the replaced QR zone
    scale = 4
    hi = base.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(hi)

    # Clear only the QR code region (inside outer cyan border x=21, y=21..234, left of divider x=228)
    x0, y0 = 25 * scale, 25 * scale
    x1, y1 = 222 * scale, 230 * scale
    draw.rectangle([x0, y0, x1, y1], fill=NAVY_RGB)

    cx = (x0 + x1) // 2

    # Fonts
    f_sold = ImageFont.truetype(FONT_EXTRA, 56 * scale)
    f_by = ImageFont.truetype(FONT_BOLD, 34 * scale)

    # Measure & center "SOLD" + "BY" vertically inside [y0, y1]
    sold_bbox = draw.textbbox((0, 0), "SOLD", font=f_sold)
    sold_w = sold_bbox[2] - sold_bbox[0]
    sold_h = sold_bbox[3] - sold_bbox[1]

    by_bbox = draw.textbbox((0, 0), "BY", font=f_by)
    by_w = by_bbox[2] - by_bbox[0]
    by_h = by_bbox[3] - by_bbox[1]

    gap = 18 * scale
    total_h = sold_h + gap + by_h
    start_y = (y0 + y1) // 2 - total_h // 2 - 4 * scale

    draw.text(
        (cx - sold_w // 2 - sold_bbox[0], start_y - sold_bbox[1]),
        "SOLD",
        font=f_sold,
        fill=WHITE_RGB,
    )

    by_y = start_y + sold_h + gap
    draw.text(
        (cx - by_w // 2 - by_bbox[0], by_y - by_bbox[1]),
        "BY",
        font=f_by,
        fill=CYAN_RGB,
    )

    # Subtle cyan flanking lines beside "BY"
    line_y = by_y + by_h // 2
    line_w = 34 * scale
    pad = 12 * scale
    draw.line(
        [(cx - by_w // 2 - pad - line_w, line_y), (cx - by_w // 2 - pad, line_y)],
        fill=CYAN_RGB,
        width=2 * scale,
    )
    draw.line(
        [(cx + by_w // 2 + pad, line_y), (cx + by_w // 2 + pad + line_w, line_y)],
        fill=CYAN_RGB,
        width=2 * scale,
    )

    # Save exact 1024x256 PNG (antialiased down from 4x)
    out_png = hi.resize((w, h), Image.Resampling.LANCZOS)
    out_png.save(PNG_PATH, format="PNG", optimize=True)

    # Also build 24" x 6" Print PDF with 0.125" navy bleed
    bleed = 9.0
    trim_w = 24.0 * 72.0
    trim_h = 6.0 * 72.0
    doc = pymupdf.open()
    page = doc.new_page(width=trim_w + 2 * bleed, height=trim_h + 2 * bleed)
    navy_f = tuple(c / 255.0 for c in NAVY_RGB)
    page.draw_rect(pymupdf.Rect(0, 0, trim_w + 2 * bleed, trim_h + 2 * bleed), color=None, fill=navy_f)

    buf = io.BytesIO()
    hi.save(buf, format="PNG", optimize=True)
    page.insert_image(pymupdf.Rect(bleed, bleed, bleed + trim_w, bleed + trim_h), stream=buf.getvalue())
    doc.save(PDF_PATH, garbage=4, deflate=True)
    doc.close()

    print(f"Saved PNG: {PNG_PATH} ({out_png.size[0]}x{out_png.size[1]})")
    print(f"Saved PDF: {PDF_PATH}")


if __name__ == "__main__":
    build()
