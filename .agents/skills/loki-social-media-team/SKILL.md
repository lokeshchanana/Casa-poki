---
name: loki-social-media-team
description: >-
  Master operating runbook for Lokesh Chanana's 5-agent Social Media Team across
  Instagram (Posts, Carousels, Reels, Stories), Facebook, TikTok, and X (Twitter).
  Use when researching WA real estate content, drafting storylines, rendering branded
  graphics/videos, analyzing past post performance, or queueing posts for owner approval.
---

# Lokesh Chanana — Social Media Team Runbook

Always read [product-marketing.md](../../product-marketing.md) and [loki-brand-design](../loki-brand-design/SKILL.md) before producing any social asset.

## 1. The 5-Agent Social Media Wing (`agent-hub`)
1. **Devon Brooks (`social_scout`)** — WA Real Estate Market & Viral Format Scout. Researches Puget Sound market data + viral hooks/edit beat sheets.
2. **Nadia Kapoor (`avatar_artist`)** — Animated Avatar Studio & Photo Curator. Generates/maintains Loki's Animated Avatar Pack (`/tank/social/avatars/`) via Antigravity `image-generator` and curates real photos from Google Photos Picker (`/tank/social/photos/`).
3. **Maya Reyes (`marketing`)** — Creative Director & Brand Storyteller. Writes warm, zero-AI-tells storylines and chooses **Real Photo vs. Animated Avatar**.
4. **Leo Bennett (`content_producer`)** — Multi-Platform Content Producer. Renders `1080×1350` carousels, `1080×1920` Reels/TikTok MP4s (with Edge-TTS + animated avatar or Ken Burns photos + kinetic captions), `1080×1920` Stories, `1200×630` FB cards, and `1200×675` X posts.
5. **Priya Nair (`social_ops`)** — Analytics, Cadence & Scheduling Strategist. Syncs Postiz + `instagram_reels.json` metrics, computes optimal Pacific Time posting cadence, runs compliance checks with Audrey Chen, and manages the Approval Queue.

## 2. Strict Human-in-the-Loop Approval Gate (CRITICAL)
- **NEVER auto-publish** to Instagram, Facebook, TikTok, or X.
- Every generated post enters status `PENDING_APPROVAL` in `social_posts`.
- Posts are dispatched to **Postiz** (`http://192.168.1.240:4007/api/public/v1`) **only** after the owner explicitly approves them in the **Social Studio** UI (`checkin.lokeshchanana.com`) or via an explicit approval command.

## 3. Platform Specifications & Safe Zones
| Platform / Format | Dimensions | Aspect | Key Rules |
| :--- | :--- | :--- | :--- |
| **Instagram Post / Carousel** | `1080 × 1350 px` | `4:5` | 1–7 slides; Slide 1 hook + graded photo/avatar; Slides 2–6 `8px` Charcoal left-accent cards; Final CTA slide. |
| **Instagram Reel / TikTok** | `1080 × 1920 px` | `9:16` | Safe zone `x: 90–990`, `y: 250–1520`; 15–60s; hook in first 2s; burned-in `#151C23` lower-third captions. |
| **Instagram Story** | `1080 × 1920 px` | `9:16` | Safe zone `y: 250–1520`; conversational poll/question sticker callout; clean Ivory/Charcoal card. |
| **Facebook Post** | `1200 × 630 px` | `1.91:1` | Neighborly storytelling, neighborhood-specific context, clear question/CTA without link-bait. |
| **X (Twitter) Post / Thread** | `1200 × 675 px` | `16:9` | Sharp data-backed hook under 280 chars (or 3–5 tweet thread), zero hashtag spam (max 1–2). |

## 4. Mandatory Editorial & Legal Checklist
- **Brokerage Prominence (WA RCW 18.85):** Include `Lokesh Chanana (Loki) • Real Broker LLC` on graphics/captions.
- **Listing Credit:** If showcasing another brokerage's listing, credit `Listed by [Agent] | [Brokerage]`.
- **Fair Housing:** Zero steering or demographic-targeting language.
- **Zero AI Tells:** No em dashes (`—`), no *"It's not X, it's Y"*, no *"No X, no Y, no Z"*, no *"Agree?"* / *"Let that sink in."*, no emoji-bullet spam.
