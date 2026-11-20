---
name: loki-avatar-studio
description: >-
  Locked 2D flat-vector Character Bible and curation rules for Nadia Kapoor
  (Avatar Studio & Photo Curator) to generate 100% identity-consistent avatars
  of Lokesh Chanana using Antigravity's image-generator and manage Google Photos Picker assets.
---

# Loki 2D Vector Avatar Studio & Character Bible

## 1. Master Reference & Storage Paths (MANDATORY)
- **Locked Character Reference Crop:** `/tank/social/avatar_refs/loki_avatar_crop_ref.png`
- **Full Reference Infographic:** `/tank/social/avatar_refs/loki_master_avatar_ref.png`
- **Transparent Avatar Pack:** `/tank/social/avatars/` (all stored as clean transparent RGBA PNGs)
- **Personal Photos (Google Photos Picker & Uploads):** `/tank/social/photos/`

## 2. Non-Negotiable Character Identity Bible (NEVER DEVIATE)
Every single avatar pose MUST reference `/tank/social/avatar_refs/loki_avatar_crop_ref.png` directly so all poses share 100% identical features:
- **Art Style:** Crisp **2D flat vector editorial cartoon illustration** with uniform dark-navy ink outlines (`#152538`) and clean flat cel-shading.
  - **FORBIDDEN:** NEVER generate 3D Pixar, CGI, glossy airbrushed skin, photorealistic AI, or inconsistent face shapes.
- **Hair:** Dark brown-black hair pulled back tightly into a neat **top-knot man bun** with short faded sides.
- **Face & Beard:** Warm medium-tan skin tone, neatly trimmed full dark brown beard and connected mustache, warm friendly open-tooth smile.
- **Signature Eyewear:** Sleek silver-frame **aviator sunglasses** with translucent dark charcoal-to-grey gradient lenses.
- **Wardrobe:** Tailored dark charcoal-slate blazer (`#4A5560`) with tiny circular white `LC` monogram lapel pin on the left chest, open-collar white button-down shirt (no tie), dark charcoal trousers with black belt and silver buckle.
- **Background & Transparency:** Generate on pure solid `#FFFFFF` white background with zero background icons/text, then flood-fill remove ONLY exterior white pixels from image edges (preserving his white shirt & teeth) into a transparent RGBA PNG.

## 3. Approval & Rejection Workflow
- Every new generated avatar enters `/tank/social/avatars/` as `PENDING_REVIEW`.
- Always visually inspect every generated avatar before presenting it to Lokesh. Discard any pose with drifted features or over-AI texture immediately.
- Lokesh can click **Approve**, **Set Master**, or **Reject & Remove** inside **Social Studio → Avatars & Google Photos**. Rejected avatars are permanently deleted and never used.
