---
name: social-analytics-cadence
description: >-
  Analytics and posting cadence optimization skill for Priya Nair (Social Ops Strategist).
  Evaluates historical post performance across Instagram, Facebook, TikTok, and X to
  generate adaptive Pacific Time posting schedules and Avatar-vs-Photo mix recommendations.
---

# Social Analytics & Cadence Optimization Skill

## 1. Data Sources
1. **Postiz Analytics API** (`/api/public/v1/analytics` & post metrics synced into `social_analytics`).
2. **Existing Website Reels Feed** (`/home/lokesh/Casa-poki/real-estate/public/instagram_reels.json`).
3. **Owner Feedback Signals** (approvals, revision requests, and manual metric imports in Social Studio).

## 2. Core Metrics & Scoring
- **Weighted Engagement Score:**
  `Score = (Likes * 1.0) + (Comments * 3.0) + (Shares * 4.0) + (Saves * 5.0)` normalized by Impressions/Reach when available.
- **Dimension Breakdown:**
  - **By Platform:** `instagram_reel`, `instagram_carousel`, `instagram_story`, `facebook`, `tiktok`, `twitter`.
  - **By Content Pillar:** `market_update`, `property_walkthrough`, `buyer_seller_tip`, `personal_story`, `open_house`.
  - **By Visual Mode:** `real_photo` vs. `animated_avatar` vs. `hybrid`.
  - **By Time Window (`America/Los_Angeles`):** Morning commute (`07:30–09:00`), Midday (`11:30–13:00`), Evening wind-down (`17:30–20:00`).

## 3. Adaptive Cadence Rules
- Always schedule in **America/Los_Angeles** (Pacific Time).
- **Cold-Start Baseline** (until ≥10 posts have live analytics):
  - **Instagram Reels:** 3x/week (Tue 12:00 PM, Thu 5:30 PM, Sat 10:00 AM)
  - **Instagram Carousels / Feed:** 2x/week (Mon 8:30 AM, Wed 12:00 PM)
  - **Instagram Stories:** 4–5x/week (Mon–Fri 9:00 AM / 4:30 PM)
  - **Facebook:** 3x/week (Tue/Thu/Sat 10:30 AM)
  - **TikTok:** 3–4x/week (repurposed Reels at Wed/Fri/Sun 6:00 PM)
  - **X (Twitter):** 4–5x/week (Mon–Fri 8:00 AM & 12:30 PM)
- Once ≥10 posts have tracked metrics, shift slot priority and `real_photo` vs. `animated_avatar` ratio toward the top-performing quartile while preserving at least 20% exploration for new formats.
