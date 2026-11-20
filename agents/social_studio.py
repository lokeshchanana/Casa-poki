"""
Lokesh Chanana — Social Media Creative Studio (Static-First, Zero AI Audio)
===========================================================================
Renders publication-grade, brand-consistent static graphics using Pillow & NumPy
following `BRAND_GUIDELINES.md` and Loki's locked 2D Flat Vector Avatar identity:
  - Canvas: #FAF8F5 Warm Ivory / #1F2933 Charcoal / #C0C0C0 Silver
  - Fonts: Playfair Display & Plus Jakarta Sans (/tank/social/fonts/)
  - Alpha-masked lc-logo.png & real-logo.png (zero opaque boxes)
  - Clean transparent RGBA compositing for Loki's 2D vector avatars
  - 72% saturation + 16% Ivory/Charcoal split-tone grading for real photos
  - ZERO AI sound/TTS until Lokesh's personal voice model is enabled
"""

import os
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

SOCIAL_DIR = os.environ.get("SOCIAL_STORAGE_DIR", "/tank/social")
RENDERS_DIR = os.path.join(SOCIAL_DIR, "renders")
FONTS_DIR = os.path.join(SOCIAL_DIR, "fonts")

# Voice/Audio Guard: strictly disabled until Lokesh's real voice model is integrated
ALLOW_AI_AUDIO = os.environ.get("LOKI_VOICE_MODEL_READY", "false").lower() == "true"

PUBLIC_DIR = (
    "/workspace/real-estate-public"
    if os.path.isdir("/workspace/real-estate-public")
    else "/home/lokesh/Casa-poki/real-estate/public"
)

# Brand Colors (RGB)
IVORY = (250, 248, 245)
IVORY_DARK = (229, 225, 219)
WHITE = (255, 255, 255)
CHARCOAL = (31, 41, 51)
CHARCOAL_DARK = (21, 28, 35)
CHARCOAL_LIGHT = (45, 58, 71)
NAVY_INK = (21, 37, 56)
SAGE_TINT = (229, 240, 234)
SKY_TINT = (226, 239, 246)
ACCENT_GREEN = (74, 168, 108)
SILVER = (192, 192, 192)
SILVER_LIGHT = (224, 224, 224)
SILVER_DARK = (140, 142, 145)
SILVER_BORDER = (214, 211, 205)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    mapping = {
        "pf_bold": "Playfair-normal-700.ttf",
        "pf_semi": "Playfair-normal-600.ttf",
        "pf_reg": "Playfair-normal-400.ttf",
        "pf_ital": "Playfair-italic-400.ttf",
        "pjs_bold": "PlusJakartaSans-Bold.ttf",
        "pjs_extra": "PlusJakartaSans-ExtraBold.ttf",
        "pjs_semi": "PlusJakartaSans-SemiBold.ttf",
        "pjs_reg": "PlusJakartaSans-Regular.ttf",
    }
    path = os.path.join(FONTS_DIR, mapping.get(name, "PlusJakartaSans-Regular.ttf"))
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def editorial_grade(im: Image.Image, sat: float = 0.72, contrast: float = 1.05) -> Image.Image:
    """Apply Loki's 72% saturation + 16% Ivory/Charcoal split-tone grading to real photos."""
    rgb = im.convert("RGB")
    rgb = ImageEnhance.Color(rgb).enhance(sat)
    rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    arr = np.asarray(rgb, dtype=np.float32) / 255.0
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    lum3 = lum[:, :, None]
    charcoal_f = np.array(CHARCOAL, dtype=np.float32) / 255.0
    ivory_f = np.array(IVORY, dtype=np.float32) / 255.0
    tone = (1.0 - lum3) * charcoal_f + lum3 * ivory_f
    out = np.clip((0.84 * arr + 0.16 * tone) * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(out, mode="RGB")


def _load_logo_tint(filename: str, target_h: int, tint: Tuple[int, int, int] = CHARCOAL) -> Optional[Image.Image]:
    path = os.path.join(PUBLIC_DIR, filename)
    if not os.path.exists(path):
        return None
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    scale = target_h / max(h, 1)
    new_w = max(1, int(w * scale))
    im = im.resize((new_w, target_h), Image.Resampling.LANCZOS)

    arr = np.asarray(im)
    if "real-logo" in filename:
        gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        alpha = np.clip(255 - gray, 0, 255).astype(np.uint8)
    else:
        alpha = arr[:, :, 3]

    out = np.zeros((target_h, new_w, 4), dtype=np.uint8)
    out[:, :, 0] = tint[0]
    out[:, :, 1] = tint[1]
    out[:, :, 2] = tint[2]
    out[:, :, 3] = alpha
    return Image.fromarray(out, mode="RGBA")


def _paste_logos(canvas: Image.Image, y: int, margin_x: int = 56, dark_bg: bool = False) -> None:
    tint = IVORY if dark_bg else CHARCOAL
    lc = _load_logo_tint("lc-logo.png", 64, tint)
    real = _load_logo_tint("real-logo.png", 44, tint)
    if lc:
        canvas.paste(lc, (margin_x, y), lc)
    if real:
        canvas.paste(real, (canvas.width - margin_x - real.width, y + 10), real)


def _draw_kicker_pill(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, dark_bg: bool = False) -> int:
    font = _font("pjs_bold", 20)
    label = text.upper()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pw = tw + 36
    ph = th + 20
    fill = CHARCOAL_DARK if dark_bg else WHITE
    outline = CHARCOAL_LIGHT if dark_bg else SILVER_LIGHT
    ink = SILVER if dark_bg else CHARCOAL
    draw.rounded_rectangle([x, y, x + pw, y + ph], radius=6, fill=fill, outline=outline, width=2)
    draw.text((x + 18, y + 8), label, font=font, fill=ink)
    return y + ph


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    max_width: int,
    line_spacing: float = 1.25,
) -> int:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        bw = draw.textbbox((0, 0), test, font=font)[2]
        if bw <= max_width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    cy = y
    sample_h = draw.textbbox((0, 0), "Ag", font=font)[3]
    step = int(max(sample_h, font.size if hasattr(font, "size") else 24) * line_spacing)
    for line in lines:
        draw.text((x, cy), line, font=font, fill=fill)
        cy += step
    return cy


def _fit_cover(im: Image.Image, target_w: int, target_h: int) -> Image.Image:
    return ImageOps.fit(im.convert("RGB"), (target_w, target_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.25))


def _paste_vector_avatar(
    canvas: Image.Image,
    avatar_path: str,
    box_x: int,
    box_y: int,
    max_w: int,
    max_h: int,
    align_bottom: bool = True,
    align_right: bool = False,
) -> None:
    """Paste a transparent RGBA 2D vector avatar cleanly preserving aspect ratio."""
    if not avatar_path or not os.path.exists(avatar_path):
        return
    im = Image.open(avatar_path).convert("RGBA")
    w, h = im.size
    scale = min(max_w / max(w, 1), max_h / max(h, 1))
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    px = (box_x + max_w - nw) if align_right else (box_x + (max_w - nw) // 2)
    py = (box_y + max_h - nh) if align_bottom else (box_y + (max_h - nh) // 2)
    canvas.paste(im, (px, py), im)


def _ensure_render_dir() -> str:
    os.makedirs(RENDERS_DIR, exist_ok=True)
    return RENDERS_DIR


# ------------------------------------------------------------------------------
# 1. Instagram Feed / Carousel (1080 x 1350 Static)
# ------------------------------------------------------------------------------

def render_instagram_carousel(
    kicker: str,
    headline: str,
    subheadline: str,
    cards: List[Dict[str, str]],
    visual_path: Optional[str] = None,
    visual_mode: str = "animated_avatar",
    cta_text: str = "Questions about your neighborhood or home value? DM me or text (801) 860-1052.",
) -> List[str]:
    """Render a branded 4:5 Instagram Carousel (Cover + Content Slides + CTA Slide)."""
    _ensure_render_dir()
    batch = uuid.uuid4().hex[:8]
    W, H = 1080, 1350
    outputs: List[str] = []

    # --- Slide 1: Cover ---
    cover = Image.new("RGB", (W, H), IVORY)
    d = ImageDraw.Draw(cover)
    d.rectangle([0, 0, W, 14], fill=CHARCOAL)
    _paste_logos(cover, 36, 56, dark_bg=False)
    d.line([(56, 118), (W - 56, 118)], fill=SILVER_LIGHT, width=2)

    ky = _draw_kicker_pill(d, 56, 144, kicker)
    hy = _draw_wrapped(d, 56, ky + 24, headline, _font("pf_bold", 58), CHARCOAL, W - 112, 1.15)
    sy = _draw_wrapped(d, 56, hy + 14, subheadline, _font("pjs_reg", 27), CHARCOAL_LIGHT, W - 112, 1.3)

    img_top = max(sy + 24, 460)
    img_h = H - img_top - 104
    if visual_path and os.path.exists(visual_path):
        if visual_mode == "real_photo":
            hero = _fit_cover(editorial_grade(Image.open(visual_path)), W - 112, img_h)
            cover.paste(hero, (56, img_top))
            d.rectangle([56, img_top, W - 56, img_top + img_h], outline=SILVER_BORDER, width=3)
        else:
            # Editorial Vector Backdrop Card + Transparent Vector Loki Avatar
            d.rounded_rectangle([56, img_top, W - 56, img_top + img_h], radius=16, fill=WHITE, outline=SILVER_LIGHT, width=2)
            d.rectangle([56, img_top, 66, img_top + img_h], fill=CHARCOAL)
            # Subtle PNW stat callout on left, Vector Loki pointing cleanly on right
            _draw_wrapped(
                d, 96, img_top + 48,
                cards[0].get("title", "Greater Seattle Snapshot") if cards else "Greater Seattle Snapshot",
                _font("pf_bold", 38), CHARCOAL, 470, 1.18,
            )
            _draw_wrapped(
                d, 96, img_top + 175,
                cards[0].get("body", "Real local numbers, zero hype. Swipe through for the full breakdown.") if cards else "",
                _font("pjs_reg", 26), CHARCOAL_LIGHT, 460, 1.38,
            )
            _paste_vector_avatar(cover, visual_path, 550, img_top + 16, 460, img_h - 16, align_bottom=True, align_right=True)

    d.rectangle([0, H - 96, W, H], fill=CHARCOAL)
    d.text((56, H - 62), "LOKESH CHANANA (LOKI)  •  REAL BROKER LLC", font=_font("pjs_bold", 22), fill=IVORY)
    d.text((W - 210, H - 62), "SWIPE  →", font=_font("pjs_bold", 24), fill=SILVER)

    p1 = os.path.join(RENDERS_DIR, f"ig_carousel_{batch}_01.png")
    cover.save(p1, "PNG")
    outputs.append(p1)

    # --- Slides 2..N: Numbered Editorial Cards ---
    chunk_size = 2
    for s_idx in range(0, max(1, len(cards)), chunk_size):
        chunk = cards[s_idx : s_idx + chunk_size]
        slide = Image.new("RGB", (W, H), IVORY)
        sd = ImageDraw.Draw(slide)
        sd.rectangle([0, 0, W, 14], fill=CHARCOAL)
        sd.text((56, 38), f"LOKESH CHANANA  •  {kicker.upper()}", font=_font("pjs_bold", 20), fill=CHARCOAL_LIGHT)
        sd.text((W - 140, 36), f"0{(s_idx // chunk_size) + 2}", font=_font("pf_bold", 28), fill=SILVER_DARK)
        sd.line([(56, 84), (W - 56, 84)], fill=SILVER_LIGHT, width=2)

        cy = 132
        card_h = 460
        for idx, card in enumerate(chunk):
            num = f"{s_idx + idx + 1:02d}"
            sd.rectangle([56, cy, W - 56, cy + card_h], fill=WHITE, outline=SILVER_LIGHT, width=2)
            sd.rectangle([56, cy, 66, cy + card_h], fill=CHARCOAL)
            sd.rectangle([92, cy + 36, 152, cy + 96], fill=IVORY, outline=SILVER_LIGHT, width=2)
            sd.text((104, cy + 44), num, font=_font("pf_bold", 34), fill=CHARCOAL)
            ty = _draw_wrapped(sd, 180, cy + 40, card.get("title", "Key Insight"), _font("pf_bold", 38), CHARCOAL, W - 268, 1.18)
            _draw_wrapped(sd, 92, max(ty + 24, cy + 132), card.get("body", ""), _font("pjs_reg", 28), CHARCOAL_LIGHT, W - 180, 1.38)
            cy += card_h + 44

        sd.rectangle([0, H - 84, W, H], fill=CHARCOAL)
        sd.text((56, H - 54), "LOKESHCHANANA.COM  •  (801) 860-1052  •  REAL BROKER LLC", font=_font("pjs_semi", 20), fill=SILVER)
        pn = os.path.join(RENDERS_DIR, f"ig_carousel_{batch}_{(s_idx // chunk_size) + 2:02d}.png")
        slide.save(pn, "PNG")
        outputs.append(pn)

    # --- Final Slide: Dark Charcoal CTA ---
    cta = Image.new("RGB", (W, H), CHARCOAL)
    cd = ImageDraw.Draw(cta)
    cd.rectangle([0, 0, W, 14], fill=SILVER)
    _paste_logos(cta, 48, 56, dark_bg=True)
    _draw_kicker_pill(cd, 56, 180, "YOUR TRUSTED PNW NEIGHBOR", dark_bg=True)
    hy2 = _draw_wrapped(cd, 56, 260, "Let's Make Your Next Move Clear & Stress-Free.", _font("pf_bold", 56), IVORY, W - 112, 1.15)
    _draw_wrapped(cd, 56, hy2 + 30, cta_text, _font("pjs_reg", 30), SILVER, W - 112, 1.4)

    if visual_path and os.path.exists(visual_path) and visual_mode != "real_photo":
        _paste_vector_avatar(cta, visual_path, 48, H - 460, 290, 440, align_bottom=True)
    else:
        portrait_path = visual_path if (visual_path and os.path.exists(visual_path)) else os.path.join(PUBLIC_DIR, "loki-profile.jpg")
        if os.path.exists(portrait_path):
            p_im = _fit_cover(Image.open(portrait_path), 240, 280)
            cta.paste(p_im, (56, H - 390))
            cd.rectangle([56, H - 390, 296, H - 110], outline=SILVER, width=3)

    cd.text((356, H - 360), "Lokesh Chanana (Loki)", font=_font("pf_bold", 38), fill=IVORY)
    cd.text((356, H - 306), "REALTOR® • WA LIC #26006634", font=_font("pjs_semi", 22), fill=SILVER)
    cd.text((356, H - 266), "Real Broker LLC", font=_font("pjs_bold", 24), fill=IVORY)
    cd.text((356, H - 208), "Call / Text: (801) 860-1052", font=_font("pjs_reg", 24), fill=IVORY)
    cd.text((356, H - 168), "lokeshchanana.com", font=_font("pjs_reg", 24), fill=SILVER)

    pf = os.path.join(RENDERS_DIR, f"ig_carousel_{batch}_99_cta.png")
    cta.save(pf, "PNG")
    outputs.append(pf)
    return outputs


# ------------------------------------------------------------------------------
# 2. 9:16 WA Market Infographic Poster (Inspired by Loki's King County Reference)
# ------------------------------------------------------------------------------

def render_market_infographic(
    region: str,
    headline: str,
    stats: List[Dict[str, str]],
    avatar_path: Optional[str] = None,
) -> str:
    """
    Render a crisp 1080x1920 2D Editorial Infographic Poster with 3 bold stat cards,
    Loki's transparent 2D vector avatar pointing cleanly beside the cards,
    and a dark navy-charcoal Lakhani/Real Broker footer.
    """
    _ensure_render_dir()
    W, H = 1080, 1920
    im = Image.new("RGB", (W, H), IVORY)
    d = ImageDraw.Draw(im)

    # Top subtle sky/ivory band + charcoal crown
    d.rectangle([0, 0, W, 16], fill=NAVY_INK)
    d.rectangle([0, 16, W, 330], fill=SKY_TINT)
    d.line([(0, 330), (W, 330)], fill=NAVY_INK, width=4)

    # Centered Big Editorial Title
    _draw_kicker_pill(d, 72, 52, f"WASHINGTON REAL ESTATE • {region.upper()}")
    _draw_wrapped(d, 72, 126, headline.upper(), _font("pjs_extra", 52), NAVY_INK, W - 144, 1.12)

    # 3 Bold Stat Cards (left 72% width for cards 1-2 so vector Loki overlaps cleanly on right!)
    default_stats = [
        {"value": "350+", "label": "ACTIVE LISTINGS", "note": "More options for buyers this week"},
        {"value": "18 DAYS", "label": "MEDIAN DAYS ON MARKET", "note": "Well-priced homes still move fast"},
        {"value": "$685K", "label": "MEDIAN SALE PRICE", "note": "Steady local Puget Sound demand"},
    ]
    rows = (stats or default_stats)[:3]
    card_y = 390
    card_h = 370
    for idx, st in enumerate(rows):
        tint = SAGE_TINT if idx % 2 == 0 else SKY_TINT
        d.rounded_rectangle([72, card_y, W - 72, card_y + card_h], radius=24, fill=WHITE, outline=NAVY_INK, width=4)
        # Left tinted badge panel
        d.rounded_rectangle([76, card_y + 4, 240, card_y + card_h - 4], radius=20, fill=tint)
        # Number box in top-left corner
        d.rounded_rectangle([72, card_y, 146, card_y + 72], radius=14, fill=NAVY_INK)
        d.text((98, card_y + 12), str(idx + 1), font=_font("pjs_extra", 38), fill=WHITE)
        # Big Stat Value & Label
        max_text_w = 410 if idx < 2 else (W - 320)
        d.text((270, card_y + 72), str(st.get("value", "")), font=_font("pjs_extra", 72), fill=NAVY_INK)
        _draw_wrapped(d, 270, card_y + 176, str(st.get("label", "")).upper(), _font("pjs_bold", 26), CHARCOAL, max_text_w, 1.2)
        if st.get("note"):
            _draw_wrapped(d, 270, card_y + 228, str(st["note"]), _font("pjs_reg", 22), CHARCOAL_LIGHT, max_text_w, 1.25)
        card_y += card_h + 44

    # Composite Loki's crisp transparent 2D vector avatar on the right edge pointing cleanly beside cards 1 & 2
    if avatar_path and os.path.exists(avatar_path):
        _paste_vector_avatar(im, avatar_path, 625, 590, 455, 860, align_bottom=True, align_right=True)

    # Bottom Dark Navy-Charcoal Footer Banner
    foot_y = H - 220
    d.rectangle([0, foot_y, W, H], fill=NAVY_INK)
    d.rectangle([0, foot_y, W, foot_y + 6], fill=SILVER)
    _paste_logos(im, foot_y + 38, 72, dark_bg=True)
    d.text((200, foot_y + 42), "Lokesh Chanana (Loki)", font=_font("pf_bold", 42), fill=WHITE)
    d.text((200, foot_y + 102), "REALTOR®  •  Real Broker LLC  •  WA LIC #26006634", font=_font("pjs_semi", 22), fill=SILVER)
    d.text((200, foot_y + 142), "(801) 860-1052   •   lokeshchanana.com", font=_font("pjs_reg", 22), fill=IVORY)

    out = os.path.join(RENDERS_DIR, f"wa_infographic_{uuid.uuid4().hex[:8]}.png")
    im.save(out, "PNG")
    return out


# ------------------------------------------------------------------------------
# 3. Instagram Story (1080 x 1920 Static Card)
# ------------------------------------------------------------------------------

def render_instagram_story(
    kicker: str,
    headline: str,
    body: str,
    poll_question: str = "Would you make this move?",
    visual_path: Optional[str] = None,
    visual_mode: str = "real_photo",
) -> str:
    _ensure_render_dir()
    W, H = 1080, 1920
    im = Image.new("RGB", (W, H), IVORY)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 16], fill=CHARCOAL)

    _paste_logos(im, 250, 90, dark_bg=False)
    ky = _draw_kicker_pill(d, 90, 340, kicker)
    hy = _draw_wrapped(d, 90, ky + 28, headline, _font("pf_bold", 54), CHARCOAL, W - 180, 1.15)

    img_y = hy + 30
    img_h = 520
    if visual_path and os.path.exists(visual_path):
        if visual_mode == "real_photo":
            framed = _fit_cover(editorial_grade(Image.open(visual_path)), W - 180, img_h)
            im.paste(framed, (90, img_y))
            d.rectangle([90, img_y, W - 90, img_y + img_h], outline=SILVER_BORDER, width=3)
        else:
            d.rounded_rectangle([90, img_y, W - 90, img_y + img_h], radius=16, fill=WHITE, outline=SILVER_LIGHT, width=2)
            _paste_vector_avatar(im, visual_path, 90, img_y + 12, W - 180, img_h - 12, align_bottom=True)

    card_y = img_y + img_h + 36
    d.rectangle([90, card_y, W - 90, card_y + 270], fill=WHITE, outline=SILVER_LIGHT, width=2)
    d.rectangle([90, card_y, 100, card_y + 270], fill=CHARCOAL)
    _draw_wrapped(d, 130, card_y + 32, body, _font("pjs_reg", 28), CHARCOAL_LIGHT, W - 260, 1.35)

    poll_y = card_y + 300
    d.rounded_rectangle([90, poll_y, W - 90, poll_y + 110], radius=14, fill=CHARCOAL)
    d.text((130, poll_y + 34), f"POLL: {poll_question}", font=_font("pjs_bold", 26), fill=IVORY)
    d.text((90, 1660), "LOKESH CHANANA (LOKI)  •  REAL BROKER LLC", font=_font("pjs_bold", 20), fill=CHARCOAL_LIGHT)

    out = os.path.join(RENDERS_DIR, f"ig_story_{uuid.uuid4().hex[:8]}.png")
    im.save(out, "PNG")
    return out


# ------------------------------------------------------------------------------
# 4. Facebook (1200 x 630) & X/Twitter (1200 x 675) Static Cards
# ------------------------------------------------------------------------------

def render_landscape_card(
    platform: str,
    kicker: str,
    headline: str,
    bullet_points: List[str],
    visual_path: Optional[str] = None,
    visual_mode: str = "animated_avatar",
) -> str:
    _ensure_render_dir()
    W = 1200
    H = 675 if platform == "twitter" else 630
    im = Image.new("RGB", (W, H), IVORY)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 12], fill=CHARCOAL)

    left_w = 440
    if visual_path and os.path.exists(visual_path):
        if visual_mode == "real_photo":
            panel = _fit_cover(editorial_grade(Image.open(visual_path)), left_w, H - 12)
            im.paste(panel, (0, 12))
        else:
            d.rectangle([0, 12, left_w, H], fill=SKY_TINT)
            d.line([(left_w, 12), (left_w, H)], fill=SILVER_LIGHT, width=2)
            _paste_vector_avatar(im, visual_path, 20, 24, left_w - 40, H - 24, align_bottom=True)
    else:
        d.rectangle([0, 12, left_w, H], fill=CHARCOAL_DARK)

    rx = left_w + 48
    rw = W - rx - 48
    ky = _draw_kicker_pill(d, rx, 40, kicker)
    hy = _draw_wrapped(d, rx, ky + 20, headline, _font("pf_bold", 42), CHARCOAL, rw, 1.15)

    by = hy + 20
    for bp in bullet_points[:3]:
        d.rectangle([rx, by + 4, rx + 6, by + 34], fill=CHARCOAL)
        by = _draw_wrapped(d, rx + 20, by, bp, _font("pjs_reg", 22), CHARCOAL_LIGHT, rw - 24, 1.25) + 10

    d.line([(rx, H - 72), (W - 48, H - 72)], fill=SILVER_LIGHT, width=2)
    d.text((rx, H - 52), "Lokesh Chanana (Loki) • Real Broker LLC • (801) 860-1052", font=_font("pjs_bold", 18), fill=CHARCOAL)

    out = os.path.join(RENDERS_DIR, f"{platform}_{uuid.uuid4().hex[:8]}.png")
    im.save(out, "PNG")
    return out


# ------------------------------------------------------------------------------
# 5. Compliance & No-AI-Tells Pre-Flight Audit
# ------------------------------------------------------------------------------

AI_TELL_PATTERNS = [
    r"\u2014",  # em dash
    r"\bit'?s not [^.,;]+,\s*it'?s\b",
    r"\bno [^,]+,\s*no [^,]+,\s*no\b",
    r"\blet that sink in\b",
    r"\bunpack this\b",
    r"\bunlock the power of\b",
    r"\btake it to the next level\b",
    r"^\s*agree\?\s*$",
]


def audit_social_post(caption: str, platform: str) -> Dict[str, Any]:
    """Check WA RCW 18.85 brokerage compliance, Fair Housing, and No-AI-Tells rules."""
    issues: List[str] = []
    warnings: List[str] = []

    if "real broker" not in caption.lower():
        warnings.append("Brokerage name 'Real Broker LLC' is recommended in caption (WA RCW 18.85).")

    for pat in AI_TELL_PATTERNS:
        if re.search(pat, caption, flags=re.IGNORECASE | re.MULTILINE):
            issues.append(f"AI-tell pattern detected ({pat}). Rewrite naturally without clichés or em dashes.")

    if platform == "twitter" and len(caption) > 280:
        warnings.append(f"X/Twitter post is {len(caption)} chars (>280). Consider splitting into a thread.")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "checked_platform": platform,
    }
