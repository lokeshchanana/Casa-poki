#!/usr/bin/env python3
"""
Generate the 22-page Branded & Interactive Home Maintenance Guide PDF
for Lokesh Chanana (Loki) — Real Broker LLC.

Preserves 100% of the vetted content from the reference Home Maintenance Guide,
styled in Lokesh Chanana's Navy & Cyan brand identity with interactive AcroForm
checkboxes on all 5 checklist pages (88 clickable checkboxes + date/notes fields).
"""

import io
import os
import pymupdf
from PIL import Image, ImageDraw, ImageOps
import numpy as np

PAGE_W = 612.0  # 8.5 in
PAGE_H = 792.0  # 11.0 in

# Brand Palette (RGB 0..1 for PyMuPDF, 0..255 for PIL)
NAVY = (15 / 255, 23 / 255, 42 / 255)          # #0f172a
NAVY_255 = (15, 23, 42)
SLATE_900 = (30 / 255, 41 / 255, 59 / 255)     # #1e293b
SLATE_900_255 = (30, 41, 59)
SLATE_700 = (51 / 255, 65 / 255, 85 / 255)     # #334155
SLATE_600 = (71 / 255, 85 / 255, 105 / 255)    # #475569
SLATE_500 = (100 / 255, 116 / 255, 139 / 255)  # #64748b
SLATE_400 = (148 / 255, 163 / 255, 184 / 255)  # #94a3b8
SLATE_200 = (226 / 255, 232 / 255, 240 / 255)  # #e2e8f0
SLATE_100 = (241 / 255, 245 / 255, 249 / 255)  # #f1f5f9
SLATE_100_255 = (241, 245, 249)
SLATE_50 = (248 / 255, 250 / 255, 252 / 255)   # #f8fafc
SLATE_50_255 = (248, 250, 252)
WHITE = (1.0, 1.0, 1.0)
WHITE_255 = (255, 255, 255)

CYAN = (6 / 255, 182 / 255, 212 / 255)         # #06b6d4
CYAN_DARK = (8 / 255, 145 / 255, 178 / 255)    # #0891b2
CYAN_LIGHT = (56 / 255, 189 / 255, 248 / 255)  # #38bdf8
CYAN_TINT = (236 / 255, 254 / 255, 255 / 255)  # #ecfeff
SKY_TINT = (240 / 255, 249 / 255, 255 / 255)   # #f0f9ff
ROYAL = (37 / 255, 99 / 255, 235 / 255)        # #2563eb
AMBER = (245 / 255, 158 / 255, 11 / 255)       # #f59e0b
AMBER_TINT = (255 / 255, 251 / 255, 235 / 255) # #fffbeb

ASSET_DIR = "/tmp/guide_assets"
PUBLIC_DIR = "/home/lokesh/Casa-poki/real-estate/public"
FONT_DIR = "/tmp/guide_assets/fonts"

FONTS = {
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


def add_text(page, rect, text, font="PJS-Reg", size=10.5, color=SLATE_700, align=0, lineheight=1.28):
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


def draw_vector_check(page, cx, cy, size=5.0, color=CYAN_LIGHT, width=1.6):
    p1 = pymupdf.Point(cx - size * 0.75, cy + size * 0.05)
    p2 = pymupdf.Point(cx - size * 0.15, cy + size * 0.65)
    p3 = pymupdf.Point(cx + size * 0.85, cy - size * 0.55)
    page.draw_line(p1, p2, color=color, width=width)
    page.draw_line(p2, p3, color=color, width=width)


def make_rounded_jpeg(
    src_path,
    w_pt,
    h_pt,
    radius_pt=10,
    bg_rgb=WHITE_255,
    scale=2.4,
    centering=(0.5, 0.5),
    dark_gradient=False,
    border_rgb=None,
    border_px=0,
):
    w_px = max(1, int(round(w_pt * scale)))
    h_px = max(1, int(round(h_pt * scale)))
    rad_px = int(round(radius_pt * scale))

    im = Image.open(src_path).convert("RGB")
    fitted = ImageOps.fit(im, (w_px, h_px), method=Image.Resampling.LANCZOS, centering=centering)

    if dark_gradient:
        overlay = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(h_px):
            t = y / max(1, h_px - 1)
            alpha = int(95 + 135 * (t ** 1.15))
            draw_ov.line([(0, y), (w_px, y)], fill=(15, 23, 42, alpha))
        fitted = Image.alpha_composite(fitted.convert("RGBA"), overlay).convert("RGB")

    mask = Image.new("L", (w_px, h_px), 0)
    draw_m = ImageDraw.Draw(mask)
    draw_m.rounded_rectangle((0, 0, w_px - 1, h_px - 1), radius=rad_px, fill=255)

    bg = Image.new("RGB", (w_px, h_px), bg_rgb)
    bg.paste(fitted, (0, 0), mask)

    if border_rgb and border_px > 0:
        draw_b = ImageDraw.Draw(bg)
        draw_b.rounded_rectangle(
            (border_px // 2, border_px // 2, w_px - 1 - border_px // 2, h_px - 1 - border_px // 2),
            radius=rad_px,
            outline=border_rgb,
            width=border_px,
        )

    buf = io.BytesIO()
    bg.save(buf, format="JPEG", quality=86, optimize=True)
    return buf.getvalue()


def insert_rounded_photo(
    page,
    rect,
    src_path,
    radius=10,
    bg_rgb=WHITE_255,
    centering=(0.5, 0.5),
    dark_gradient=False,
    border_rgb=None,
    border_px=0,
):
    r = pymupdf.Rect(rect)
    stream = make_rounded_jpeg(
        src_path,
        r.width,
        r.height,
        radius_pt=radius,
        bg_rgb=bg_rgb,
        centering=centering,
        dark_gradient=dark_gradient,
        border_rgb=border_rgb,
        border_px=border_px,
    )
    page.insert_image(r, stream=stream)


def insert_logo_on_bg(page, rect, logo_path, bg_rgb=NAVY_255, invert_white_bg=False):
    r = pymupdf.Rect(rect)
    scale = 2.6
    w_px = max(1, int(round(r.width * scale)))
    h_px = max(1, int(round(r.height * scale)))
    logo = Image.open(logo_path).convert("RGBA")

    if invert_white_bg:
        # Convert black-on-white logo into crisp white-on-transparent
        arr = np.array(logo, dtype=np.float32)
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        alpha = np.clip(255.0 - lum, 0, 255).astype(np.uint8)
        white_logo = np.zeros_like(arr, dtype=np.uint8)
        white_logo[:, :, 0] = 240
        white_logo[:, :, 1] = 244
        white_logo[:, :, 2] = 248
        white_logo[:, :, 3] = alpha
        logo = Image.fromarray(white_logo, mode="RGBA")
        # Crop transparent margin so logo scales cleanly
        bbox = logo.getbbox()
        if bbox:
            logo = logo.crop(bbox)

    logo.thumbnail((w_px, h_px), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (w_px, h_px), bg_rgb + (255,))
    ox = (w_px - logo.width) // 2
    oy = (h_px - logo.height) // 2
    canvas.alpha_composite(logo, (ox, oy))
    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="JPEG", quality=92, optimize=True)
    page.insert_image(r, stream=buf.getvalue())


def draw_running_chrome(page, page_num, category_label="HOMEOWNER RESOURCE GUIDE"):
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 6), color=None, fill=NAVY)
    page.draw_rect(pymupdf.Rect(0, 6, 180, 8.5), color=None, fill=CYAN)

    add_text(
        page,
        (36, 16, 360, 32),
        f"LOKESH CHANANA  •  {category_label.upper()}",
        font="PJS-Bold",
        size=7.5,
        color=CYAN_DARK,
    )
    add_text(
        page,
        (360, 16, PAGE_W - 36, 32),
        "HOME MAINTENANCE GUIDE",
        font="PJS-Semi",
        size=7.5,
        color=SLATE_400,
        align=2,
    )
    page.draw_line(pymupdf.Point(36, 33), pymupdf.Point(PAGE_W - 36, 33), color=SLATE_200, width=0.6)

    page.draw_line(pymupdf.Point(36, PAGE_H - 36), pymupdf.Point(PAGE_W - 36, PAGE_H - 36), color=SLATE_200, width=0.6)
    add_text(
        page,
        (36, PAGE_H - 29, 440, PAGE_H - 12),
        "Lokesh Chanana (Loki)  •  REALTOR®  •  Real Broker LLC  |  (801) 860-1052  |  lokeshchanana.com",
        font="PJS-Med",
        size=8.0,
        color=SLATE_500,
    )
    page.insert_link({
        "kind": pymupdf.LINK_URI,
        "from": pymupdf.Rect(255, PAGE_H - 30, 325, PAGE_H - 12),
        "uri": "tel:+18018601052",
    })
    page.insert_link({
        "kind": pymupdf.LINK_URI,
        "from": pymupdf.Rect(330, PAGE_H - 30, 430, PAGE_H - 12),
        "uri": "https://lokeshchanana.com",
    })

    pill = pymupdf.Rect(PAGE_W - 64, PAGE_H - 31, PAGE_W - 36, PAGE_H - 15)
    page.draw_rect(pill, color=None, fill=NAVY, radius=0.35)
    add_text(
        page,
        (PAGE_W - 64, PAGE_H - 29.5, PAGE_W - 36, PAGE_H - 14),
        f"{page_num:02d}",
        font="PJS-Bold",
        size=8.0,
        color=CYAN_LIGHT,
        align=1,
    )


def draw_section_title(page, y, kicker, title, subtitle=None):
    page.draw_rect(pymupdf.Rect(36, y, 40, y + 14), color=None, fill=CYAN)
    add_text(page, (46, y - 1, 560, y + 16), kicker.upper(), font="PJS-Bold", size=8.5, color=CYAN_DARK)
    add_text(page, (36, y + 16, PAGE_W - 36, y + 52), title, font="PJS-Extra", size=22.0, color=NAVY, lineheight=1.15)
    cur_y = y + 48
    if subtitle:
        add_text(page, (36, cur_y, PAGE_W - 36, cur_y + 42), subtitle, font="PJS-Reg", size=10.2, color=SLATE_600, lineheight=1.35)
        cur_y += 38
    return cur_y


def draw_numbered_card(page, rect, num, title, body, bg=SLATE_50, accent=CYAN):
    r = pymupdf.Rect(rect)
    page.draw_rect(r, color=SLATE_200, fill=bg, width=0.7, radius=0.06)
    page.draw_rect(pymupdf.Rect(r.x0, r.y0 + 8, r.x0 + 3.5, r.y1 - 8), color=None, fill=accent)

    badge = pymupdf.Rect(r.x0 + 12, r.y0 + 11, r.x0 + 34, r.y0 + 33)
    page.draw_rect(badge, color=None, fill=NAVY, radius=0.25)
    add_text(page, (badge.x0, badge.y0 + 4.5, badge.x1, badge.y1), f"{num:02d}", font="PJS-Bold", size=8.5, color=CYAN_LIGHT, align=1)

    add_text(page, (r.x0 + 42, r.y0 + 10, r.x1 - 12, r.y0 + 30), title, font="PJS-Bold", size=11.2, color=NAVY)
    add_text(page, (r.x0 + 42, r.y0 + 28, r.x1 - 12, r.y1 - 6), body, font="PJS-Reg", size=9.6, color=SLATE_700, lineheight=1.32)


# ==============================================================================
# PAGE BUILDERS (PAGES 1 - 22)
# ==============================================================================

def build_page_01_cover(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)

    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, PAGE_H), color=None, fill=NAVY)

    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 8), color=None, fill=CYAN)
    page.draw_rect(pymupdf.Rect(36, 28, 195, 50), color=None, fill=SLATE_900, radius=0.2)
    page.draw_rect(pymupdf.Rect(36, 28, 40, 50), color=None, fill=CYAN)
    add_text(page, (48, 33.5, 192, 48), "CLIENT HANDBOOK", font="PJS-Bold", size=8.5, color=CYAN_LIGHT)

    # Top Right Logos (Real Broker inverted to white + LC logo)
    insert_logo_on_bg(page, (PAGE_W - 180, 26, PAGE_W - 110, 54), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=NAVY_255, invert_white_bg=True)
    insert_logo_on_bg(page, (PAGE_W - 95, 18, PAGE_W - 36, 64), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=NAVY_255)

    add_text(
        page,
        (36, 68, PAGE_W - 36, 118),
        "HOME MAINTENANCE",
        font="PJS-Extra",
        size=36.0,
        color=WHITE,
        lineheight=1.05,
    )
    add_text(
        page,
        (36, 112, 340, 162),
        "GUIDE",
        font="PJS-Extra",
        size=36.0,
        color=CYAN_LIGHT,
        lineheight=1.05,
    )
    page.draw_rect(pymupdf.Rect(168, 132, PAGE_W - 36, 135), color=None, fill=CYAN)

    add_text(
        page,
        (36, 162, PAGE_W - 36, 206),
        "A practical, season-by-season handbook with interactive checklists to protect your investment, prevent costly surprises, and keep your home feeling brand new.",
        font="PJS-Reg",
        size=10.8,
        color=SLATE_200,
        lineheight=1.38,
    )

    insert_rounded_photo(
        page,
        (36, 214, PAGE_W - 36, 484),
        f"{ASSET_DIR}/hero_foyer.jpg",
        radius=12,
        bg_rgb=NAVY_255,
        border_rgb=(56, 189, 248),
        border_px=3,
    )

    strip_y0, strip_y1 = 496, 616
    col_w = (PAGE_W - 72 - 20) / 3.0
    strip_imgs = [
        f"{ASSET_DIR}/hero_kitchen.jpg",
        f"{ASSET_DIR}/hero_living.jpg",
        f"{ASSET_DIR}/hero_patio.jpg",
    ]
    for i, img_p in enumerate(strip_imgs):
        x0 = 36 + i * (col_w + 10)
        insert_rounded_photo(
            page,
            (x0, strip_y0, x0 + col_w, strip_y1),
            img_p,
            radius=9,
            bg_rgb=NAVY_255,
            border_rgb=(30, 41, 59),
            border_px=2,
        )

    banner = pymupdf.Rect(36, 632, PAGE_W - 36, 674)
    page.draw_rect(banner, color=CYAN, fill=SLATE_900, width=1.0, radius=0.15)
    draw_vector_check(page, 64, 653, size=5.5, color=CYAN_LIGHT, width=2.0)
    add_text(
        page,
        (78, 645, PAGE_W - 48, 668),
        "INCLUDES 5 INTERACTIVE FILLABLE CHECKLISTS (Pages 17–21) — Check off items right on your device or print!",
        font="PJS-Semi",
        size=9.3,
        color=CYAN_LIGHT,
    )

    footer_card = pymupdf.Rect(36, 688, PAGE_W - 36, 760)
    page.draw_rect(footer_card, color=None, fill=SLATE_900, radius=0.12)
    page.draw_rect(pymupdf.Rect(36, 688, 42, 760), color=None, fill=CYAN)

    insert_rounded_photo(
        page,
        (54, 697, 108, 751),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=8,
        bg_rgb=SLATE_900_255,
        centering=(0.5, 0.2),
    )
    add_text(page, (120, 698, 420, 718), "LOKESH CHANANA (LOKI)", font="PJS-Extra", size=13.0, color=WHITE)
    add_text(page, (120, 716, 420, 734), "Your Trusted REALTOR®  •  Real Broker LLC  (Lic #26006634)", font="PJS-Med", size=9.2, color=CYAN_LIGHT)
    add_text(page, (120, 733, 550, 752), "(801) 860-1052   •   lokesh@lokeshchanana.com   •   lokeshchanana.com", font="PJS-Reg", size=9.0, color=SLATE_200)

    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(120, 732, 200, 752), "uri": "tel:+18018601052"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(205, 732, 355, 752), "uri": "mailto:lokesh@lokeshchanana.com"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(360, 732, 490, 752), "uri": "https://lokeshchanana.com"})


def build_page_02_welcome(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 2, "WELCOME HOME")

    insert_rounded_photo(
        page,
        (36, 52, 255, 420),
        f"{ASSET_DIR}/p02_welcome.jpg",
        radius=12,
        bg_rgb=WHITE_255,
    )

    agent_card = pymupdf.Rect(36, 434, 255, 736)
    page.draw_rect(agent_card, color=None, fill=NAVY, radius=0.06)
    page.draw_rect(pymupdf.Rect(36, 434, 255, 440), color=None, fill=CYAN)

    insert_rounded_photo(
        page,
        (54, 454, 134, 554),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=10,
        bg_rgb=NAVY_255,
        centering=(0.5, 0.2),
        border_rgb=(6, 182, 212),
        border_px=2,
    )
    insert_logo_on_bg(page, (148, 454, 236, 506), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=NAVY_255)
    insert_logo_on_bg(page, (152, 514, 232, 544), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=NAVY_255, invert_white_bg=True)

    add_text(page, (54, 566, 240, 584), "YOUR TRUSTED REALTOR®", font="PJS-Bold", size=8.0, color=CYAN_LIGHT)
    add_text(page, (54, 581, 240, 604), "Lokesh Chanana", font="PJS-Extra", size=15.0, color=WHITE)
    add_text(page, (54, 601, 240, 620), "Real Broker LLC  •  Greater Seattle & WA", font="PJS-Reg", size=8.5, color=SLATE_200)

    page.draw_line(pymupdf.Point(54, 626), pymupdf.Point(237, 626), color=SLATE_700, width=0.8)

    add_text(page, (54, 634, 240, 652), "LET'S CONNECT — CALL ME ANYTIME!", font="PJS-Bold", size=8.2, color=CYAN_LIGHT)
    add_text(page, (54, 653, 240, 673), "CALL/TEXT:  (801) 860-1052", font="PJS-Semi", size=9.5, color=WHITE)
    add_text(page, (54, 673, 240, 693), "EMAIL:  lokesh@lokeshchanana.com", font="PJS-Med", size=8.8, color=SLATE_200)
    add_text(page, (54, 693, 240, 715), "WEB:  lokeshchanana.com", font="PJS-Semi", size=9.0, color=CYAN_LIGHT)

    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(54, 652, 235, 672), "uri": "tel:+18018601052"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(54, 672, 235, 692), "uri": "mailto:lokesh@lokeshchanana.com"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(54, 692, 235, 714), "uri": "https://lokeshchanana.com"})

    page.draw_rect(pymupdf.Rect(278, 52, 378, 76), color=None, fill=CYAN_TINT, radius=0.2)
    add_text(page, (278, 57, 378, 74), "HEY THERE!", font="PJS-Extra", size=10.0, color=CYAN_DARK, align=1)

    add_text(
        page,
        (278, 86, PAGE_W - 36, 154),
        "Congratulations on becoming a homeowner!",
        font="PJS-Extra",
        size=24.0,
        color=NAVY,
        lineheight=1.18,
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
        (278, 164, PAGE_W - 36, 540),
        letter_body,
        font="PJS-Reg",
        size=11.0,
        color=SLATE_700,
        lineheight=1.48,
    )

    sig_box = pymupdf.Rect(278, 555, PAGE_W - 36, 736)
    page.draw_rect(sig_box, color=SLATE_200, fill=SLATE_50, width=0.8, radius=0.06)
    page.draw_rect(pymupdf.Rect(278, 555, 283, 736), color=None, fill=CYAN)

    add_text(page, (298, 572, 550, 594), "Warmest regards,", font="PJS-Ital", size=11.0, color=SLATE_600)
    add_text(page, (298, 596, 550, 628), "Lokesh Chanana (Loki)", font="PJS-Extra", size=17.0, color=NAVY)
    add_text(page, (298, 624, 550, 644), "REALTOR®  •  Real Broker LLC", font="PJS-Semi", size=10.0, color=CYAN_DARK)

    add_text(
        page,
        (298, 654, 560, 724),
        "What's Inside This Guide:\n"
        "•  Pages 03–07:  Investment, Big Repairs, Structure, Electrical & Plumbing\n"
        "•  Pages 08–15:  HVAC, Appliances, Interior, Curb Appeal, Security & Energy\n"
        "•  Pages 16–21:  5 Interactive Fillable Checklists (Pest, Spring, Summer, Fall, Winter)",
        font="PJS-Med",
        size=9.2,
        color=SLATE_700,
        lineheight=1.4,
    )


def build_page_03_invest(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 3, "WHY MAINTENANCE MATTERS")

    y = draw_section_title(
        page,
        48,
        "PROTECT YOUR INVESTMENT",
        "Why Home Maintenance Matters",
        "Keeping up with your home isn't just a chore—it's a game-changer for your wallet, comfort, and peace of mind. Here's why staying on top of home maintenance is so important:",
    )

    insert_rounded_photo(
        page,
        (36, y + 6, PAGE_W - 36, y + 186),
        f"{ASSET_DIR}/p03_invest.jpg",
        radius=10,
        bg_rgb=WHITE_255,
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + gap


def build_page_04_repairs(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 4, "PLANNING FOR MAJOR UPGRADES")

    y = draw_section_title(
        page,
        48,
        "SMART PLANNING & OPTIONS",
        "When Big Repairs Come Knocking",
        "Sometimes, major repairs or upgrades are unavoidable. Here's how to handle them without losing sleep:",
    )

    insert_rounded_photo(
        page,
        (36, y + 6, PAGE_W - 36, y + 190),
        f"{ASSET_DIR}/p04_repairs.jpg",
        radius=10,
        bg_rgb=WHITE_255,
        centering=(0.5, 0.6),
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
        bg = SLATE_50 if (r_idx + c_idx) % 2 == 0 else SKY_TINT
        draw_numbered_card(page, (x0, y0, x0 + col_w, y0 + row_h), idx, title, body, bg=bg)


def build_page_05_structure(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 5, "STRUCTURAL INTEGRITY")

    y = draw_section_title(
        page,
        48,
        "THE BACKBONE OF YOUR HOME",
        "Keep Your Home Standing Strong",
        "Your home's structure is its backbone, and keeping it in good shape is crucial for safety and longevity. Regular attention to key areas can prevent small issues from becoming big problems down the line.",
    )

    col_w = (PAGE_W - 72 - 12) / 2.0
    insert_rounded_photo(
        page,
        (36, y + 6, 36 + col_w, y + 166),
        f"{ASSET_DIR}/p05_exterior.jpg",
        radius=10,
        bg_rgb=WHITE_255,
    )
    insert_rounded_photo(
        page,
        (36 + col_w + 12, y + 6, PAGE_W - 36, y + 166),
        f"{ASSET_DIR}/p05_porch.jpg",
        radius=10,
        bg_rgb=WHITE_255,
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + gap


def build_page_06_electrical(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 6, "ELECTRICAL SAFETY")

    y = draw_section_title(
        page,
        48,
        "ELECTRICAL SYSTEM CARE",
        "Power Up Safely",
        "Your home's electrical system keeps everything running—from your morning coffee to your evening TV time. Keeping it in good shape is crucial for safety and convenience. Here's how to stay on top of it and know when to bring in a pro.",
    )

    insert_rounded_photo(
        page,
        (36, y + 8, 285, y + 172),
        f"{ASSET_DIR}/p06_electrical.jpg",
        radius=10,
        bg_rgb=WHITE_255,
    )
    insert_rounded_photo(
        page,
        (297, y + 8, PAGE_W - 36, y + 172),
        f"{ASSET_DIR}/p06_dining.jpg",
        radius=10,
        bg_rgb=WHITE_255,
        centering=(0.5, 0.4),
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
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + 72), idx, title, body, bg=SLATE_50)
        cy += 79

    pro_box = pymupdf.Rect(36, cy + 4, PAGE_W - 36, 742)
    page.draw_rect(pro_box, color=None, fill=NAVY, radius=0.05)
    page.draw_rect(pymupdf.Rect(36, cy + 4, PAGE_W - 36, cy + 9), color=None, fill=AMBER)

    add_text(
        page,
        (52, cy + 16, PAGE_W - 52, cy + 36),
        "WHEN TO CALL A PROFESSIONAL?",
        font="PJS-Extra",
        size=13.0,
        color=CYAN_LIGHT,
    )
    add_text(
        page,
        (52, cy + 34, PAGE_W - 52, cy + 54),
        "Some electrical issues are too risky to handle on your own. Here's when you should reach out to a licensed electrician:",
        font="PJS-Reg",
        size=9.2,
        color=SLATE_200,
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
        page.draw_rect(pymupdf.Rect(px, py, px + col_w, py + 48), color=SLATE_700, fill=SLATE_900, width=0.6, radius=0.08)
        add_text(page, (px + 10, py + 5, px + col_w - 8, py + 21), f"•  {pt}", font="PJS-Bold", size=9.2, color=AMBER)
        add_text(page, (px + 10, py + 20, px + col_w - 8, py + 46), pb, font="PJS-Reg", size=8.2, color=SLATE_200, lineheight=1.25)


def build_page_07_plumbing(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 7, "PLUMBING & WATER CARE")

    y = draw_section_title(
        page,
        48,
        "PLUMBING MAINTENANCE",
        "Keep the Water Flowing",
        "Your home's plumbing is like its circulatory system, delivering fresh water and whisking away waste. Keeping it in good shape ensures comfort and helps you avoid messy (and costly) surprises.",
    )

    col_w = (PAGE_W - 72 - 12) / 2.0
    insert_rounded_photo(
        page,
        (36, y + 6, 36 + col_w, y + 158),
        f"{ASSET_DIR}/p07_plumbing_bath.jpg",
        radius=10,
        bg_rgb=WHITE_255,
    )
    insert_rounded_photo(
        page,
        (36 + col_w + 12, y + 6, PAGE_W - 36, y + 158),
        f"{ASSET_DIR}/p07_plumbing_garden.jpg",
        radius=10,
        bg_rgb=WHITE_255,
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
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + h), idx, title, body, bg=SLATE_50 if idx % 2 == 1 else SKY_TINT)
        cy += h + 8

    tips_box = pymupdf.Rect(36, cy + 4, PAGE_W - 36, 742)
    page.draw_rect(tips_box, color=None, fill=NAVY, radius=0.05)
    page.draw_rect(pymupdf.Rect(36, cy + 4, PAGE_W - 36, cy + 9), color=None, fill=CYAN)

    add_text(
        page,
        (52, cy + 16, PAGE_W - 52, cy + 36),
        "QUICK TIPS FOR A HEALTHY PLUMBING SYSTEM",
        font="PJS-Extra",
        size=12.5,
        color=CYAN_LIGHT,
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
        page.draw_rect(pymupdf.Rect(px, py, px + col_w2, py + 44), color=SLATE_700, fill=SLATE_900, width=0.6, radius=0.08)
        add_text(page, (px + 10, py + 5, px + col_w2 - 8, py + 20), f"•  {qt}", font="PJS-Bold", size=8.8, color=CYAN_LIGHT)
        add_text(page, (px + 10, py + 19, px + col_w2 - 8, py + 42), qb, font="PJS-Reg", size=8.3, color=SLATE_200, lineheight=1.25)


def build_page_08_hvac(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 8, "HEATING & COOLING")

    y = draw_section_title(
        page,
        48,
        "YEAR-ROUND CLIMATE COMFORT",
        "HVAC Maintenance Made Simple",
        "Your Heating, Ventilation, and Air Conditioning (HVAC) system is the heart of your home's comfort. It keeps you cool during sweltering summers and warm on chilly winter nights. Giving it a little attention ensures it runs efficiently and lasts longer.",
    )

    insert_rounded_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 235),
        f"{ASSET_DIR}/p08_hvac.jpg",
        radius=12,
        bg_rgb=WHITE_255,
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + 12


def build_page_09_appliances(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 9, "KITCHEN & LAUNDRY CARE")

    y = draw_section_title(
        page,
        48,
        "EXTEND APPLIANCE LIFESPAN",
        "Appliance Care",
        "Your home's appliances work hard every day, making life more convenient. With a bit of routine care, you can extend their lifespan and keep them operating efficiently.",
    )

    insert_rounded_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_DIR}/p09_appliance.jpg",
        radius=12,
        bg_rgb=WHITE_255,
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + 10


def build_page_10_interior(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 10, "INTERIOR UPKEEP")

    y = draw_section_title(
        page,
        48,
        "HEALTHY & BEAUTIFUL LIVING SPACES",
        "Essential Interior Home Maintenance Tips",
        "The inside of your home is where life happens. Regular upkeep keeps it looking great and ensures a healthy living environment.",
    )

    insert_rounded_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_DIR}/p10_interior.jpg",
        radius=12,
        bg_rgb=WHITE_255,
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + 10


def build_page_11_curb_appeal(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 11, "EXTERIOR & CURB APPEAL")

    y = draw_section_title(
        page,
        48,
        "EXTERIOR PROTECTION",
        "Curb Appeal Made Easy",
        "The exterior of your home makes the first impression and protects everything inside. A little maintenance goes a long way in keeping it attractive and durable.",
    )

    insert_rounded_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_DIR}/p11_curb.jpg",
        radius=12,
        bg_rgb=WHITE_255,
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + 10


def build_page_12_security(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 12, "SAFETY & PEACE OF MIND")

    y = draw_section_title(
        page,
        48,
        "PROTECTING YOUR SANCTUARY",
        "Safety and Security",
        "Your home is your sanctuary, and keeping it safe doesn't have to be complicated. Here are some straightforward ways to boost your home's safety and security.",
    )

    insert_rounded_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_DIR}/p12_security.jpg",
        radius=12,
        bg_rgb=WHITE_255,
        centering=(0.5, 0.65),
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + 10


def build_page_13_energy(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 13, "ENERGY EFFICIENCY")

    y = draw_section_title(
        page,
        48,
        "LOWER BILLS & GREATER COMFORT",
        "Save Money and Stay Cozy",
        "Who doesn't love saving money and being comfortable at home? Here are some effortless ways to make your home more energy-efficient.",
    )

    insert_rounded_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_DIR}/p13_energy.jpg",
        radius=12,
        bg_rgb=WHITE_255,
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + 10


def build_page_14_preventative(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 14, "PROACTIVE HABITS")

    y = draw_section_title(
        page,
        48,
        "STAY AHEAD OF REPAIRS",
        "Simple Preventative Measures",
        "A little prevention goes a long way in home maintenance. Here's how to nip potential problems in the bud.",
    )

    insert_rounded_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_DIR}/p14_prevent.jpg",
        radius=12,
        bg_rgb=WHITE_255,
        centering=(0.5, 0.65),
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + 10


def build_page_15_diy_or_pros(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)
    draw_running_chrome(page, 15, "SMART DECISION MAKING")

    y = draw_section_title(
        page,
        48,
        "KNOW WHEN TO CALL AN EXPERT",
        "DIY or Call in the Pros?",
        "Tackling home projects can be satisfying, but sometimes it's best to leave it to the experts. Here's how to figure out the best approach.",
    )

    insert_rounded_photo(
        page,
        (36, y + 8, PAGE_W - 36, y + 218),
        f"{ASSET_DIR}/p15_diy.jpg",
        radius=12,
        bg_rgb=WHITE_255,
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
        bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
        draw_numbered_card(page, (36, cy, PAGE_W - 36, cy + card_h), idx, title, body, bg=bg)
        cy += card_h + 10


def build_page_16_divider(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)

    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, PAGE_H), color=None, fill=NAVY)
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 8), color=None, fill=CYAN)

    page.draw_rect(pymupdf.Rect(206, 66, 406, 90), color=CYAN, fill=SLATE_900, width=1.0, radius=0.25)
    add_text(page, (206, 71.5, 406, 88), "INTERACTIVE CHECKLIST SECTION", font="PJS-Bold", size=8.5, color=CYAN_LIGHT, align=1)

    add_text(
        page,
        (36, 108, PAGE_W - 36, 175),
        "Let's Clean & Maintain!",
        font="PJS-Extra",
        size=38.0,
        color=WHITE,
        align=1,
    )
    add_text(
        page,
        (66, 170, PAGE_W - 66, 224),
        "Use the following 5 interactive checklists to stay ahead of seasonal upkeep and pest prevention. Click or tap any checkbox directly inside this PDF to track your progress—or print these pages for your fridge!",
        font="PJS-Reg",
        size=11.0,
        color=SLATE_200,
        align=1,
        lineheight=1.4,
    )

    insert_rounded_photo(
        page,
        (36, 244, 356, 454),
        f"{ASSET_DIR}/p16_gutter.jpg",
        radius=12,
        bg_rgb=NAVY_255,
        border_rgb=(6, 182, 212),
        border_px=2,
    )
    insert_rounded_photo(
        page,
        (36, 468, 356, 658),
        f"{ASSET_DIR}/p16_spray.jpg",
        radius=12,
        bg_rgb=NAVY_255,
        border_rgb=(30, 41, 59),
        border_px=2,
    )
    insert_rounded_photo(
        page,
        (370, 244, PAGE_W - 36, 658),
        f"{ASSET_DIR}/p16_brush.jpg",
        radius=12,
        bg_rgb=NAVY_255,
        border_rgb=(30, 41, 59),
        border_px=2,
    )

    strip = pymupdf.Rect(36, 678, PAGE_W - 36, 748)
    page.draw_rect(strip, color=None, fill=SLATE_900, radius=0.1)
    page.draw_rect(pymupdf.Rect(36, 678, 42, 748), color=None, fill=CYAN)
    add_text(
        page,
        (56, 688, PAGE_W - 52, 708),
        "YOUR 5 INTERACTIVE CHECKLISTS:",
        font="PJS-Bold",
        size=9.5,
        color=CYAN_LIGHT,
    )
    add_text(
        page,
        (56, 708, PAGE_W - 52, 740),
        "Page 17: Preventing Pest Issues (8 items)   •   Page 18: Spring (20 items)   •   Page 19: Summer (20 items)\n"
        "Page 20: Fall (20 items)   •   Page 21: Winter (20 items)",
        font="PJS-Med",
        size=9.2,
        color=SLATE_200,
        lineheight=1.35,
    )


def build_checklist_page(doc, page_num, slug, title, subtitle, banner_img, items, accent_color=CYAN):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)

    banner_rect = pymupdf.Rect(36, 28, PAGE_W - 36, 152)
    insert_rounded_photo(
        page,
        banner_rect,
        banner_img,
        radius=12,
        bg_rgb=WHITE_255,
        dark_gradient=True,
    )

    page.draw_rect(pymupdf.Rect(52, 42, 222, 62), color=None, fill=accent_color, radius=0.2)
    draw_vector_check(page, 66, 52, size=4.2, color=NAVY, width=1.8)
    add_text(
        page,
        (74, 45.5, 220, 60),
        "INTERACTIVE CHECKLIST",
        font="PJS-Extra",
        size=8.2,
        color=NAVY,
    )

    add_text(
        page,
        (52, 68, 425, 110),
        title,
        font="PJS-Extra",
        size=24.0,
        color=WHITE,
    )
    add_text(
        page,
        (52, 106, 425, 140),
        subtitle,
        font="PJS-Med",
        size=9.5,
        color=SLATE_200,
    )

    # Interactive Year / Date Completed Text Widget in top-right of banner
    date_card = pymupdf.Rect(432, 44, PAGE_W - 48, 100)
    page.draw_rect(date_card, color=CYAN_LIGHT, fill=NAVY, width=0.8, radius=0.12)
    add_text(
        page,
        (440, 50, PAGE_W - 56, 66),
        "SEASON / YEAR:",
        font="PJS-Bold",
        size=7.5,
        color=CYAN_LIGHT,
    )
    tf = pymupdf.Widget()
    tf.field_name = f"txt_{slug}_date"
    tf.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    tf.rect = pymupdf.Rect(440, 68, PAGE_W - 56, 92)
    tf.text_color = (0.06, 0.09, 0.16)
    tf.fill_color = (0.97, 0.98, 0.99)
    tf.border_color = (0.02, 0.71, 0.83)
    tf.border_width = 0.8
    tf.text_fontsize = 9.0
    tf.field_value = ""
    page.add_widget(tf)

    inst_rect = pymupdf.Rect(36, 160, PAGE_W - 36, 182)
    page.draw_rect(inst_rect, color=None, fill=SLATE_100, radius=0.15)
    add_text(
        page,
        (48, 165, PAGE_W - 48, 180),
        "PRO TIP:  Click or tap any square checkbox below to check it off digitally, or print this page and check items with a pen!",
        font="PJS-Semi",
        size=8.4,
        color=SLATE_700,
    )

    if len(items) <= 10:
        cy = 192
        row_h = 48
        gap = 7
        for idx, item_text in enumerate(items, 1):
            row_rect = pymupdf.Rect(36, cy, PAGE_W - 36, cy + row_h)
            bg = SLATE_50 if idx % 2 == 1 else SKY_TINT
            page.draw_rect(row_rect, color=SLATE_200, fill=bg, width=0.7, radius=0.08)
            page.draw_rect(pymupdf.Rect(36, cy + 8, 39.5, cy + row_h - 8), color=None, fill=accent_color)

            cb_rect = pymupdf.Rect(50, cy + (row_h - 18) / 2, 68, cy + (row_h + 18) / 2)
            page.draw_rect(cb_rect, color=CYAN_DARK, fill=WHITE, width=1.2, radius=0.1)

            w = pymupdf.Widget()
            w.field_name = f"chk_{slug}_{idx:02d}"
            w.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
            w.rect = cb_rect
            w.border_color = (0.03, 0.57, 0.70)
            w.border_width = 1.2
            w.fill_color = (1.0, 1.0, 1.0)
            w.text_color = (0.06, 0.09, 0.16)
            w.field_value = False
            page.add_widget(w)

            top_pad = 15 if len(item_text) < 82 else 9
            add_text(
                page,
                (78, cy + top_pad, PAGE_W - 48, cy + row_h - 4),
                item_text,
                font="PJS-Med",
                size=10.0,
                color=NAVY,
                lineheight=1.28,
            )
            cy += row_h + gap

        notes_box = pymupdf.Rect(36, cy + 4, PAGE_W - 36, 706)
        page.draw_rect(notes_box, color=SLATE_200, fill=SLATE_50, width=0.8, radius=0.08)
        add_text(
            page,
            (48, cy + 10, 440, cy + 26),
            "HOMEOWNER NOTES & SERVICE PRO REMINDERS (FILLABLE):",
            font="PJS-Bold",
            size=8.5,
            color=CYAN_DARK,
        )
        nf = pymupdf.Widget()
        nf.field_name = f"txt_{slug}_notes"
        nf.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        nf.field_flags = pymupdf.PDF_TX_FIELD_IS_MULTILINE
        nf.rect = pymupdf.Rect(48, cy + 28, PAGE_W - 48, 698)
        nf.text_color = (0.06, 0.09, 0.16)
        nf.fill_color = (1.0, 1.0, 1.0)
        nf.border_color = (0.80, 0.84, 0.90)
        nf.border_width = 0.7
        nf.text_fontsize = 9.5
        nf.field_value = ""
        page.add_widget(nf)

    else:
        start_y = 192
        col_w = (PAGE_W - 72 - 14) / 2.0
        row_h = 44.5
        gap_y = 6.5

        for idx, item_text in enumerate(items, 1):
            col_idx = 0 if idx <= 10 else 1
            row_idx = (idx - 1) if idx <= 10 else (idx - 11)
            x0 = 36 + col_idx * (col_w + 14)
            y0 = start_y + row_idx * (row_h + gap_y)

            row_rect = pymupdf.Rect(x0, y0, x0 + col_w, y0 + row_h)
            bg = SLATE_50 if (row_idx + col_idx) % 2 == 0 else SKY_TINT
            page.draw_rect(row_rect, color=SLATE_200, fill=bg, width=0.65, radius=0.08)
            page.draw_rect(pymupdf.Rect(x0, y0 + 6, x0 + 3.0, y0 + row_h - 6), color=None, fill=accent_color)

            cb_rect = pymupdf.Rect(x0 + 11, y0 + (row_h - 16) / 2, x0 + 27, y0 + (row_h + 16) / 2)
            page.draw_rect(cb_rect, color=CYAN_DARK, fill=WHITE, width=1.1, radius=0.1)

            w = pymupdf.Widget()
            w.field_name = f"chk_{slug}_{idx:02d}"
            w.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
            w.rect = cb_rect
            w.border_color = (0.03, 0.57, 0.70)
            w.border_width = 1.1
            w.fill_color = (1.0, 1.0, 1.0)
            w.text_color = (0.06, 0.09, 0.16)
            w.field_value = False
            page.add_widget(w)

            top_pad = 14.5 if len(item_text) < 42 else 8.5
            add_text(
                page,
                (x0 + 34, y0 + top_pad, x0 + col_w - 8, y0 + row_h - 3),
                item_text,
                font="PJS-Med",
                size=9.1,
                color=NAVY,
                lineheight=1.22,
            )

    f_rect = pymupdf.Rect(36, 718, PAGE_W - 36, 764)
    page.draw_rect(f_rect, color=None, fill=NAVY, radius=0.1)
    page.draw_rect(pymupdf.Rect(36, 718, 42, 764), color=None, fill=accent_color)

    insert_rounded_photo(
        page,
        (48, 723, 84, 759),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=6,
        bg_rgb=NAVY_255,
        centering=(0.5, 0.2),
    )
    add_text(
        page,
        (94, 724, 415, 742),
        "Your Trusted REALTOR®  —  Lokesh Chanana (Loki)",
        font="PJS-Extra",
        size=10.5,
        color=WHITE,
    )
    add_text(
        page,
        (94, 741, 465, 758),
        "Need a trusted local contractor or service pro? Call/Text (801) 860-1052  •  lokeshchanana.com",
        font="PJS-Med",
        size=8.4,
        color=CYAN_LIGHT,
    )
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(310, 740, 395, 758), "uri": "tel:+18018601052"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(400, 740, 500, 758), "uri": "https://lokeshchanana.com"})

    add_text(
        page,
        (PAGE_W - 92, 732, PAGE_W - 48, 752),
        f"PAGE {page_num:02d}",
        font="PJS-Bold",
        size=8.5,
        color=SLATE_400,
        align=2,
    )


def build_page_22_back_cover(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    register_fonts(page)

    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, PAGE_H), color=None, fill=NAVY)
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, 8), color=None, fill=CYAN)

    insert_rounded_photo(
        page,
        (36, 36, PAGE_W - 36, 326),
        f"{ASSET_DIR}/hero_foyer.jpg",
        radius=14,
        bg_rgb=NAVY_255,
        border_rgb=(6, 182, 212),
        border_px=2,
    )

    card = pymupdf.Rect(36, 344, PAGE_W - 36, 586)
    page.draw_rect(card, color=SLATE_700, fill=SLATE_900, width=1.0, radius=0.05)
    page.draw_rect(pymupdf.Rect(36, 344, PAGE_W - 36, 350), color=None, fill=CYAN)

    add_text(
        page,
        (56, 366, PAGE_W - 56, 404),
        "I'm Only a Phone Call Away!",
        font="PJS-Extra",
        size=25.0,
        color=WHITE,
        align=1,
    )
    add_text(
        page,
        (56, 404, PAGE_W - 56, 430),
        "Welcome home!",
        font="PJS-Bold",
        size=14.0,
        color=CYAN_LIGHT,
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
        (68, 436, PAGE_W - 68, 574),
        closing_msg,
        font="PJS-Reg",
        size=10.8,
        color=SLATE_200,
        align=1,
        lineheight=1.42,
    )

    bcard = pymupdf.Rect(36, 602, PAGE_W - 36, 752)
    page.draw_rect(bcard, color=CYAN, fill=SLATE_900, width=1.2, radius=0.06)

    insert_rounded_photo(
        page,
        (56, 618, 152, 736),
        f"{PUBLIC_DIR}/loki-profile.jpg",
        radius=10,
        bg_rgb=SLATE_900_255,
        centering=(0.5, 0.2),
        border_rgb=(56, 189, 248),
        border_px=2,
    )

    add_text(page, (172, 620, 430, 638), "YOUR TRUSTED REALTOR®", font="PJS-Bold", size=8.5, color=CYAN_LIGHT)
    add_text(page, (172, 636, 430, 664), "Lokesh Chanana (Loki)", font="PJS-Extra", size=18.0, color=WHITE)
    add_text(page, (172, 662, 430, 680), "Real Broker LLC  •  License #26006634", font="PJS-Med", size=9.5, color=SLATE_200)

    add_text(page, (172, 686, 430, 704), "CALL / TEXT:  (801) 860-1052", font="PJS-Bold", size=10.0, color=WHITE)
    add_text(page, (172, 704, 430, 722), "EMAIL:  lokesh@lokeshchanana.com", font="PJS-Med", size=9.6, color=SLATE_200)
    add_text(page, (172, 722, 430, 740), "WEB:  https://lokeshchanana.com", font="PJS-Bold", size=9.6, color=CYAN_LIGHT)

    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(172, 685, 340, 704), "uri": "tel:+18018601052"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(172, 704, 380, 722), "uri": "mailto:lokesh@lokeshchanana.com"})
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(172, 722, 380, 740), "uri": "https://lokeshchanana.com"})

    insert_logo_on_bg(page, (455, 618, 555, 682), f"{PUBLIC_DIR}/lc-logo.png", bg_rgb=SLATE_900_255)
    insert_logo_on_bg(page, (462, 692, 548, 728), f"{PUBLIC_DIR}/real-logo.png", bg_rgb=SLATE_900_255, invert_white_bg=True)


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
        "Proactive steps to keep your home pest-free all year long",
        f"{ASSET_DIR}/p17_pest.jpg",
        pest_items,
    )

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
        f"{ASSET_DIR}/p18_spring.jpg",
        spring_items,
    )

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
        "Keep your home cool, efficient, and ready for summer fun",
        f"{ASSET_DIR}/p19_summer.jpg",
        summer_items,
    )

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
        f"{ASSET_DIR}/p20_fall.jpg",
        fall_items,
    )

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
        f"{ASSET_DIR}/p21_winter.jpg",
        winter_items,
    )

    build_page_22_back_cover(doc)

    doc.set_metadata({
        "title": "Home Maintenance Guide — Lokesh Chanana (Loki) | Real Broker LLC",
        "author": "Lokesh Chanana (Loki) — REALTOR®, Real Broker LLC",
        "subject": "Interactive Seasonal Home Maintenance Guide & Checklists",
        "keywords": "Home Maintenance, Checklist, Lokesh Chanana, Real Broker, Seattle Real Estate",
    })

    out_pdf = f"{PUBLIC_DIR}/home-maintenance-guide.pdf"
    doc.subset_fonts()
    doc.save(out_pdf, garbage=3, deflate=True)
    sz_mb = os.path.getsize(out_pdf) / (1024 * 1024)
    print(f"Successfully generated {out_pdf} ({len(doc)} pages, {sz_mb:.2f} MB)")


if __name__ == "__main__":
    main()
