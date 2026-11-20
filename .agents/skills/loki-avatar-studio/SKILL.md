---
name: loki-avatar-studio
description: >-
  Guidelines and prompting system for Nadia Kapoor (Avatar Studio & Photo Curator)
  to generate consistent Animated Avatars of Lokesh Chanana using Antigravity's
  image-generator and curate/grade personal photos from Google Photos Picker.
---

# Loki Avatar Studio & Photo Curation Skill

## 1. Master Reference & Storage Paths
- **Primary Reference Photo:** `/home/lokesh/Casa-poki/real-estate/public/loki-profile.jpg`
- **Animated Avatar Pack:** `/tank/social/avatars/`
- **Curated Personal Photos (Google Photos Picker & Uploads):** `/tank/social/photos/`

## 2. Antigravity `image-generator` Consistency Prompting
Whenever generating a new animated avatar pose or seasonal outfit for Loki:
1. Always pass `/home/lokesh/Casa-poki/real-estate/public/loki-profile.jpg` (and an existing approved avatar like `/tank/social/avatars/loki_avatar_welcome.png` when available) as reference.
2. Lock the visual DNA:
   - **Style:** *"Warm Pacific Northwest Editorial 3D-illustrated character, clean Pixar/editorial-inspired stylization, expressive eyes, neatly styled dark hair and trimmed beard matching the reference photo."*
   - **Wardrobe:** *"Tailored architectural charcoal blazer (#1F2933) over a crisp warm ivory collared shirt (#FAF8F5)"* (or smart-casual PNW navy/charcoal sweater for casual Stories).
   - **Background:** *"Solid clean warm ivory studio background (#FAF8F5)"* so Pillow/FFmpeg can cleanly frame or composite it.
3. For **talking-head Reels**, generate matched pairs (`mouth closed` + `mouth open mid-sentence`) so `social_studio.py` can alternate frames dynamically with voiceover audio energy.

## 3. When to Use Real Photo vs. Animated Avatar
- **Use Real Photo (`/tank/social/photos/`):** Authentic field moments, open houses, client closings, neighborhood walk-and-talks, personal stories, and high-trust testimonials. Always apply `editorial_grade(sat=0.72, contrast=1.05)` + `16%` Ivory/Charcoal split-tone.
- **Use Animated Avatar (`/tank/social/avatars/`):** Weekly WA Market Pulse explainers, mortgage rate breakdowns, 3-step buyer/seller educational Reels, data-heavy carousels, and rapid-turnaround trend responses where filming wasn't possible.
- **Hybrid:** Real Puget Sound home/neighborhood photo as the main canvas + Animated Avatar in a clean circular/corner presenter badge!
