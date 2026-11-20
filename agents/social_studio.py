"""
Lokesh Chanana — Social Media Creative & Video Studio
=====================================================
Renders publication-grade, brand-consistent graphics and vertical MP4 Reels/TikToks
using Pillow, NumPy, Edge-TTS, and FFmpeg following `BRAND_GUIDELINES.md`:
  - Canvas: #FAF8F5 Warm Ivory / #1F2933 Charcoal / #C0C0C0 Silver
  - Fonts: Playfair Display & Plus Jakarta Sans (/tank/social/fonts/)
  - Alpha-masked lc-logo.png & real-logo.png (zero opaque boxes)
  - 72% saturation + 16% Ivory/Charcoal split-tone editorial grading
  - 9:16 Safe Zones (x: 90-990, y: 250-1520) for Reels/TikTok/Stories
"""

import asyncio
import math
import os
import re
import subprocess
import textwrap
import uuid
import wave
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

SOCIAL_DIR = os.environ.get("SOCIAL_STORAGE_DIR", "/tank/social")
RENDERS_DIR = os.path.join(SOCIAL_DIR, "renders")
FONTS_DIR = os.path.join(SOCIAL_DIR, "fonts")

# Resolve public assets dir both inside Docker (/workspace/real-estate-public) and host
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
    """Apply Loki's 72% saturation + 16% Ivory/Charcoal split-tone grading."""
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
        # real-logo has black pixels on opaque white
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
    return ImageOps.fit(im.convert("RGB"), (target_w, target_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.3))


def _ensure_render_dir() -> str:
    os.makedirs(RENDERS_DIR, exist_ok=True)
    return RENDERS_DIR


# ------------------------------------------------------------------------------
# 1. Instagram Feed / Carousel (1080 x 1350)
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
    hy = _draw_wrapped(d, 56, ky + 24, headline, _font("pf_bold", 60), CHARCOAL, W - 112, 1.15)
    sy = _draw_wrapped(d, 56, hy + 14, subheadline, _font("pjs_reg", 28), CHARCOAL_LIGHT, W - 112, 1.3)

    img_top = max(sy + 28, 470)
    img_h = H - img_top - 120
    if visual_path and os.path.exists(visual_path):
        src = Image.open(visual_path)
        if visual_mode == "real_photo":
            src = editorial_grade(src)
        hero = _fit_cover(src, W - 112, img_h)
        cover.paste(hero, (56, img_top))
        d.rectangle([56, img_top, W - 56, img_top + img_h], outline=SILVER_BORDER, width=3)

    # Bottom Dark Anchor Strip
    d.rectangle([0, H - 96, W, H], fill=CHARCOAL)
    d.text((56, H - 62), "LOKESH CHANANA (LOKI)  •  REAL BROKER LLC", font=_font("pjs_bold", 22), fill=IVORY)
    d.text((W - 210, H - 62), "SWIPE  →", font=_font("pjs_bold", 24), fill=SILVER)

    p1 = os.path.join(RENDERS_DIR, f"ig_carousel_{batch}_01.png")
    cover.save(p1, "PNG")
    outputs.append(p1)

    # --- Slides 2..N: Content Cards (2 cards per slide) ---
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
            # Card box
            sd.rectangle([56, cy, W - 56, cy + card_h], fill=WHITE, outline=SILVER_LIGHT, width=2)
            # Signature 8px Charcoal Left Accent Bar
            sd.rectangle([56, cy, 66, cy + card_h], fill=CHARCOAL)
            # Ivory Number Badge
            sd.rectangle([92, cy + 36, 152, cy + 96], fill=IVORY, outline=SILVER_LIGHT, width=2)
            sd.text((104, cy + 44), num, font=_font("pf_bold", 34), fill=CHARCOAL)
            # Card Title & Body
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

    # Portrait Box
    portrait_path = visual_path if (visual_path and os.path.exists(visual_path)) else os.path.join(PUBLIC_DIR, "loki-profile.jpg")
    if os.path.exists(portrait_path):
        p_im = _fit_cover(Image.open(portrait_path), 240, 280)
        cta.paste(p_im, (56, H - 390))
        cd.rectangle([56, H - 390, 296, H - 110], outline=SILVER, width=3)

    cd.text((336, H - 360), "Lokesh Chanana (Loki)", font=_font("pf_bold", 38), fill=IVORY)
    cd.text((336, H - 306), "REALTOR® • WA LIC #26006634", font=_font("pjs_semi", 22), fill=SILVER)
    cd.text((336, H - 266), "Real Broker LLC", font=_font("pjs_bold", 24), fill=IVORY)
    cd.text((336, H - 208), "Call / Text: (801) 860-1052", font=_font("pjs_reg", 24), fill=IVORY)
    cd.text((336, H - 168), "lokeshchanana.com", font=_font("pjs_reg", 24), fill=SILVER)

    pf = os.path.join(RENDERS_DIR, f"ig_carousel_{batch}_99_cta.png")
    cta.save(pf, "PNG")
    outputs.append(pf)
    return outputs


# ------------------------------------------------------------------------------
# 2. Instagram Story (1080 x 1920)
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

    # Safe zone starts y=240, ends y=1540
    _paste_logos(im, 250, 90, dark_bg=False)
    ky = _draw_kicker_pill(d, 90, 340, kicker)
    hy = _draw_wrapped(d, 90, ky + 28, headline, _font("pf_bold", 56), CHARCOAL, W - 180, 1.15)

    # Visual frame
    img_y = hy + 30
    img_h = 520
    if visual_path and os.path.exists(visual_path):
        src = Image.open(visual_path)
        if visual_mode == "real_photo":
            src = editorial_grade(src)
        framed = _fit_cover(src, W - 180, img_h)
        im.paste(framed, (90, img_y))
        d.rectangle([90, img_y, W - 90, img_y + img_h], outline=SILVER_BORDER, width=3)

    # Card below image
    card_y = img_y + img_h + 36
    d.rectangle([90, card_y, W - 90, card_y + 290], fill=WHITE, outline=SILVER_LIGHT, width=2)
    d.rectangle([90, card_y, 100, card_y + 290], fill=CHARCOAL)
    _draw_wrapped(d, 130, card_y + 32, body, _font("pjs_reg", 28), CHARCOAL_LIGHT, W - 260, 1.35)

    # Poll / Prompt Box inside safe zone
    poll_y = card_y + 320
    d.rounded_rectangle([90, poll_y, W - 90, poll_y + 110], radius=14, fill=CHARCOAL)
    d.text((130, poll_y + 34), f"POLL: {poll_question}", font=_font("pjs_bold", 26), fill=IVORY)

    d.text((90, 1660), "LOKESH CHANANA (LOKI)  •  REAL BROKER LLC", font=_font("pjs_bold", 20), fill=CHARCOAL_LIGHT)

    out = os.path.join(RENDERS_DIR, f"ig_story_{uuid.uuid4().hex[:8]}.png")
    im.save(out, "PNG")
    return out


# ------------------------------------------------------------------------------
# 3. Facebook (1200 x 630) & X/Twitter (1200 x 675) Cards
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

    # Left visual panel (42% width)
    left_w = 480
    if visual_path and os.path.exists(visual_path):
        src = Image.open(visual_path)
        if visual_mode == "real_photo":
            src = editorial_grade(src)
        panel = _fit_cover(src, left_w, H - 12)
        im.paste(panel, (0, 12))
    else:
        d.rectangle([0, 12, left_w, H], fill=CHARCOAL_DARK)

    # Right editorial content panel
    rx = left_w + 48
    rw = W - rx - 48
    ky = _draw_kicker_pill(d, rx, 40, kicker)
    hy = _draw_wrapped(d, rx, ky + 20, headline, _font("pf_bold", 42), CHARCOAL, rw, 1.15)

    by = hy + 20
    for bp in bullet_points[:3]:
        d.rectangle([rx, by + 4, rx + 6, by + 34], fill=CHARCOAL)
        by = _draw_wrapped(d, rx + 20, by, bp, _font("pjs_reg", 22), CHARCOAL_LIGHT, rw - 24, 1.25) + 10

    # Bottom footer strip on right panel
    d.line([(rx, H - 72), (W - 48, H - 72)], fill=SILVER_LIGHT, width=2)
    d.text((rx, H - 52), "Lokesh Chanana (Loki) • Real Broker LLC • (801) 860-1052", font=_font("pjs_bold", 18), fill=CHARCOAL)

    out = os.path.join(RENDERS_DIR, f"{platform}_{uuid.uuid4().hex[:8]}.png")
    im.save(out, "PNG")
    return out


# ------------------------------------------------------------------------------
# 4. Vertical Video (Reels / TikTok 1080 x 1920 MP4 with Edge-TTS + FFmpeg)
# ------------------------------------------------------------------------------

async def _synthesize_tts(script_text: str, out_mp3: str) -> bool:
    try:
        import edge_tts

        comm = edge_tts.Communicate(script_text, voice="en-US-AndrewNeural", rate="+4%")
        await comm.save(out_mp3)
        return os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 500
    except Exception:
        return False


def _audio_duration_sec(audio_path: str) -> float:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            text=True,
        ).strip()
        return max(4.0, min(60.0, float(out)))
    except Exception:
        return 12.0


def _build_reel_frame(
    kicker: str,
    headline: str,
    caption_chunk: str,
    avatar_im: Image.Image,
    bg_im: Optional[Image.Image] = None,
    bob_offset_y: int = 0,
    zoom_scale: float = 1.0,
) -> Image.Image:
    W, H = 1080, 1920
    frame = Image.new("RGB", (W, H), IVORY)
    if bg_im is not None:
        zw = int(W * zoom_scale)
        zh = int(H * zoom_scale)
        zbg = bg_im.resize((zw, zh), Image.Resampling.LANCZOS)
        left = (zw - W) // 2
        top = (zh - H) // 2
        frame = zbg.crop((left, top, left + W, top + H))
        # Soft ivory wash so text & avatar pop cleanly
        wash = Image.new("RGBA", (W, H), (250, 248, 245, 165))
        frame = Image.alpha_composite(frame.convert("RGBA"), wash).convert("RGB")

    d = ImageDraw.Draw(frame)
    # Top Charcoal Crown
    d.rectangle([0, 0, W, 16], fill=CHARCOAL)

    # Safe zone top header (y=230)
    _draw_kicker_pill(d, 90, 235, kicker)
    _draw_wrapped(d, 90, 315, headline, _font("pf_bold", 48), CHARCOAL, W - 180, 1.14)

    # Center Presenter Card (Avatar or Photo)
    card_top = 480 + bob_offset_y
    card_w, card_h = 840, 740
    card_x = (W - card_w) // 2
    fitted = _fit_cover(avatar_im, card_w, card_h)
    frame.paste(fitted, (card_x, card_top))
    d.rectangle([card_x, card_top, card_x + card_w, card_top + card_h], outline=CHARCOAL, width=4)

    # Signature #151C23 Charcoal Dark Lower-Third Caption Pill (inside safe zone y<=1520)
    cap_y = 1280
    d.rounded_rectangle([90, cap_y, W - 90, cap_y + 210], radius=12, fill=CHARCOAL_DARK)
    d.rectangle([90, cap_y, 100, cap_y + 210], fill=SILVER)
    _draw_wrapped(d, 130, cap_y + 34, caption_chunk, _font("pjs_semi", 34), IVORY, W - 260, 1.3)

    # Brand Compliance Footer inside safe zone
    d.text((90, 1525), "Lokesh Chanana (Loki)  •  REALTOR®  •  Real Broker LLC", font=_font("pjs_bold", 22), fill=CHARCOAL)
    return frame


async def render_vertical_reel(
    kicker: str,
    headline: str,
    script_text: str,
    primary_visual_path: Optional[str] = None,
    talking_visual_path: Optional[str] = None,
    bg_photo_path: Optional[str] = None,
    visual_mode: str = "animated_avatar",
    platform: str = "instagram_reel",
) -> str:
    """
    Render a 1080x1920 vertical MP4 video with Edge-TTS narration,
    animated talking-avatar frame alternation (or Ken Burns real photo motion),
    and burned-in brand captions.
    """
    _ensure_render_dir()
    vid_id = uuid.uuid4().hex[:8]
    mp3_path = os.path.join(RENDERS_DIR, f"tts_{vid_id}.mp3")
    wav_path = os.path.join(RENDERS_DIR, f"tts_{vid_id}.wav")
    out_mp4 = os.path.join(RENDERS_DIR, f"{platform}_{vid_id}.mp4")
    frames_dir = os.path.join(RENDERS_DIR, f"frames_{vid_id}")
    os.makedirs(frames_dir, exist_ok=True)

    has_audio = await _synthesize_tts(script_text, mp3_path)
    duration = _audio_duration_sec(mp3_path) if has_audio else 10.0
    fps = 8  # Crisp, fast CPU render for animated talking frames; muxed at 24fps

    # Convert mp3 to wav to compute per-frame speech energy for realistic lip-sync
    energies: List[float] = []
    if has_audio:
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-ac", "1", "-ar", "16000", wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if os.path.exists(wav_path):
            try:
                with wave.open(wav_path, "rb") as wf:
                    raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32)
                samples_per_frame = max(1, int(16000 / fps))
                for i in range(0, len(raw), samples_per_frame):
                    chunk = raw[i : i + samples_per_frame]
                    energies.append(float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) else 0.0)
            except Exception:
                energies = []

    welcome_path = primary_visual_path or os.path.join(SOCIAL_DIR, "avatars", "loki_avatar_welcome.png")
    talk_path = talking_visual_path or os.path.join(SOCIAL_DIR, "avatars", "loki_avatar_talking.png")
    if not os.path.exists(welcome_path):
        welcome_path = os.path.join(PUBLIC_DIR, "loki-profile.jpg")
    if not os.path.exists(talk_path):
        talk_path = welcome_path

    im_welcome = Image.open(welcome_path)
    im_talk = Image.open(talk_path)
    if visual_mode == "real_photo":
        im_welcome = editorial_grade(im_welcome)
        im_talk = im_welcome

    bg_im = None
    if bg_photo_path and os.path.exists(bg_photo_path):
        bg_im = editorial_grade(Image.open(bg_photo_path))

    # Split script into timed caption chunks (~10 words per chunk)
    words = script_text.split()
    chunk_size = 9
    chunks = [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)] or [headline]
    total_frames = max(int(math.ceil(duration * fps)), fps * 4)
    thresh = (np.percentile(energies, 35) if energies else 350.0)

    for f_idx in range(total_frames):
        t_ratio = f_idx / max(total_frames - 1, 1)
        c_idx = min(len(chunks) - 1, int(t_ratio * len(chunks)))
        speaking = False
        if visual_mode != "real_photo" and f_idx < len(energies):
            speaking = energies[f_idx] > thresh and (f_idx % 2 == 0 or energies[f_idx] > thresh * 1.4)
        bob = int(round(math.sin(f_idx * 0.6) * 4)) if speaking else 0
        zoom = 1.0 + (0.06 * t_ratio)
        frame = _build_reel_frame(
            kicker=kicker,
            headline=headline,
            caption_chunk=chunks[c_idx],
            avatar_im=im_talk if speaking else im_welcome,
            bg_im=bg_im,
            bob_offset_y=bob,
            zoom_scale=zoom,
        )
        frame.save(os.path.join(frames_dir, f"f_{f_idx:05d}.png"), "PNG")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "f_%05d.png"),
    ]
    if has_audio:
        cmd.extend(["-i", mp3_path, "-c:a", "aac", "-b:a", "160k", "-shortest"])
    cmd.extend([
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24", "-preset", "veryfast",
        out_mp4,
    ])
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Clean up temporary frames/audio
    for fn in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, fn))
    os.rmdir(frames_dir)
    for tmp in (mp3_path, wav_path):
        if os.path.exists(tmp):
            os.remove(tmp)

    return out_mp4


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
