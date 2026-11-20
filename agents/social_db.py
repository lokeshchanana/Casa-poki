"""
Social Media Team SQLite Persistence Layer
========================================
Stores research briefs, media assets (avatars + Google Photos), post approval
queue items, analytics metrics, adaptive posting cadence rules, and OAuth tokens
inside Casa-poki's shared `agent_system.db`.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

DATA_DIR = os.environ.get("AGENT_DATA_DIR", "/app/data")
DB_PATH = os.path.join(DATA_DIR, "agent_system.db")
SOCIAL_DIR = os.environ.get("SOCIAL_STORAGE_DIR", "/tank/social")


def _conn() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def init_social_db() -> None:
    """Create all social media tables if they don't exist and seed defaults."""
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS social_research_briefs (
                id TEXT PRIMARY KEY,
                brief_type TEXT NOT NULL,          -- 'market_update' | 'viral_format' | 'hybrid'
                region TEXT DEFAULT 'Greater Seattle, WA',
                title TEXT NOT NULL,
                hook TEXT,
                data_points_json TEXT DEFAULT '[]',
                viral_beat_sheet_json TEXT DEFAULT '[]',
                sources_json TEXT DEFAULT '[]',
                summary TEXT,
                created_by TEXT DEFAULT 'social_scout',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS social_media_assets (
                id TEXT PRIMARY KEY,
                asset_type TEXT NOT NULL,          -- 'avatar' | 'photo' | 'upload'
                title TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                graded_path TEXT,
                pose_or_tags TEXT DEFAULT '',
                source TEXT DEFAULT 'local',       -- 'antigravity' | 'google_photos' | 'upload' | 'seed'
                approval_status TEXT DEFAULT 'PENDING_REVIEW', -- 'MASTER' | 'APPROVED' | 'PENDING_REVIEW' | 'REJECTED'
                usage_count INTEGER DEFAULT 0,
                avg_engagement REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS social_posts (
                id TEXT PRIMARY KEY,
                campaign_id TEXT,
                platform TEXT NOT NULL,            -- 'instagram_post' | 'instagram_carousel' | 'instagram_reel' | 'instagram_story' | 'facebook' | 'tiktok' | 'twitter'
                pillar TEXT DEFAULT 'market_update',
                visual_mode TEXT DEFAULT 'animated_avatar', -- 'animated_avatar' | 'real_photo' | 'hybrid'
                title TEXT NOT NULL,
                hook TEXT,
                storyline TEXT,
                caption TEXT NOT NULL,
                hashtags TEXT DEFAULT '',
                script_text TEXT DEFAULT '',
                media_paths_json TEXT DEFAULT '[]',
                asset_ids_json TEXT DEFAULT '[]',
                status TEXT DEFAULT 'PENDING_APPROVAL', -- 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'SCHEDULED_POSTIZ' | 'PUBLISHED' | 'REVISION_REQUESTED' | 'REJECTED'
                scheduled_for TEXT,
                postiz_post_id TEXT,
                postiz_integration_id TEXT,
                compliance_json TEXT DEFAULT '{}',
                revision_notes TEXT DEFAULT '',
                created_by TEXT DEFAULT 'content_producer',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS social_analytics (
                id TEXT PRIMARY KEY,
                post_id TEXT,
                external_id TEXT,
                platform TEXT NOT NULL,
                pillar TEXT DEFAULT 'market_update',
                visual_mode TEXT DEFAULT 'real_photo',
                published_at TEXT,
                impressions INTEGER DEFAULT 0,
                reach INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                engagement_score REAL DEFAULT 0.0,
                raw_json TEXT DEFAULT '{}',
                synced_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS social_cadence_rules (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                day_of_week TEXT NOT NULL,         -- 'Mon'..'Sun'
                time_pt TEXT NOT NULL,             -- '08:30', '12:00', etc.
                pillar TEXT NOT NULL,
                recommended_format TEXT NOT NULL,
                preferred_visual_mode TEXT NOT NULL,
                confidence REAL DEFAULT 0.65,
                rationale TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS social_oauth_tokens (
                provider TEXT PRIMARY KEY,
                access_token TEXT,
                refresh_token TEXT,
                expires_at TEXT,
                scope TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )
        # Safe migration for existing DBs missing approval_status
        cols = [r["name"] for r in c.execute("PRAGMA table_info(social_media_assets)").fetchall()]
        if "approval_status" not in cols:
            c.execute("ALTER TABLE social_media_assets ADD COLUMN approval_status TEXT DEFAULT 'PENDING_REVIEW'")
        # Prune DB asset rows whose backing files were removed
        rows = c.execute("SELECT id, file_path FROM social_media_assets").fetchall()
        for r in rows:
            if not os.path.exists(r["file_path"]):
                c.execute("DELETE FROM social_media_assets WHERE id = ?", (r["id"],))
    _seed_existing_assets()
    _seed_default_cadence()


def _seed_existing_assets() -> None:
    """Register any avatars/photos already on disk under /tank/social."""
    now = _now_iso()
    avatar_dir = os.path.join(SOCIAL_DIR, "avatars")
    photo_dir = os.path.join(SOCIAL_DIR, "photos")
    entries = []
    if os.path.isdir(avatar_dir):
        for fn in sorted(os.listdir(avatar_dir)):
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                full = os.path.join(avatar_dir, fn)
                pose = os.path.splitext(fn)[0].replace("loki_avatar_", "").replace("loki_vec_", "").replace("_", " ").title()
                st = "MASTER" if "master" in fn.lower() else "PENDING_REVIEW"
                entries.append(("avatar", f"Loki Avatar — {pose}", full, pose.lower(), "antigravity", st))
    if os.path.isdir(photo_dir):
        for fn in sorted(os.listdir(photo_dir)):
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                full = os.path.join(photo_dir, fn)
                label = os.path.splitext(fn)[0].replace("_", " ").replace("-", " ").title()
                entries.append(("photo", label, full, "portrait,loki,personal", "seed", "APPROVED"))

    if not entries:
        return
    with _conn() as c:
        for asset_type, title, fpath, tags, src, st in entries:
            c.execute(
                """
                INSERT OR IGNORE INTO social_media_assets
                (id, asset_type, title, file_path, pose_or_tags, source, approval_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"ast_{uuid.uuid4().hex[:10]}", asset_type, title, fpath, tags, src, st, now),
            )


def _seed_default_cadence() -> None:
    """Seed baseline Pacific Time static-image cadence rules (zero AI audio)."""
    with _conn() as c:
        count = c.execute("SELECT COUNT(*) FROM social_cadence_rules").fetchone()[0]
        if count > 0:
            return
        now = _now_iso()
        baseline = [
            ("instagram_carousel", "Mon", "08:30", "buyer_seller_tip", "4:5 Editorial Ivory Carousel (Static)", "animated_avatar", 0.78, "Start-of-week educational carousels earn strong bookmark & save rates."),
            ("market_infographic", "Tue", "12:00", "market_update", "9:16 WA Market Infographic Poster (Static)", "animated_avatar", 0.82, "Clean visual stat cards + vector Loki outperform text-heavy updates."),
            ("instagram_story", "Wed", "16:30", "personal_story", "9:16 Interactive Poll Story Card (Static)", "real_photo", 0.75, "Authentic field photos keep Story replies warm without audio."),
            ("instagram_post", "Thu", "17:30", "property_walkthrough", "4:5 Puget Sound Spotlight Graphic (Static)", "real_photo", 0.77, "Evening commute window captures local home-browsers."),
            ("facebook", "Sat", "10:30", "open_house", "1.91:1 Community Update Card (Static)", "hybrid", 0.73, "Weekend local community traffic peaks mid-morning."),
            ("twitter", "Wed", "08:00", "market_update", "16:9 Data Card + Concise Take (Static)", "animated_avatar", 0.74, "Morning PNW tech & finance audience engages with crisp data graphics."),
        ]
        for plat, dow, tpt, pil, fmt, vmode, conf, rat in baseline:
            c.execute(
                """
                INSERT INTO social_cadence_rules
                (id, platform, day_of_week, time_pt, pillar, recommended_format, preferred_visual_mode, confidence, rationale, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"cad_{uuid.uuid4().hex[:8]}", plat, dow, tpt, pil, fmt, vmode, conf, rat, now),
            )


# ---------------------------------------------------------------------------
# Research Briefs
# ---------------------------------------------------------------------------

def save_research_brief(
    brief_type: str,
    title: str,
    region: str = "Greater Seattle, WA",
    hook: str = "",
    data_points: Optional[List[str]] = None,
    viral_beat_sheet: Optional[List[Dict[str, Any]]] = None,
    sources: Optional[List[str]] = None,
    summary: str = "",
    created_by: str = "social_scout",
) -> Dict[str, Any]:
    bid = f"brf_{uuid.uuid4().hex[:10]}"
    now = _now_iso()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO social_research_briefs
            (id, brief_type, region, title, hook, data_points_json, viral_beat_sheet_json, sources_json, summary, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bid,
                brief_type,
                region,
                title,
                hook,
                json.dumps(data_points or []),
                json.dumps(viral_beat_sheet or []),
                json.dumps(sources or []),
                summary,
                created_by,
                now,
            ),
        )
    return {"id": bid, "brief_type": brief_type, "region": region, "title": title, "hook": hook, "created_at": now}


def list_research_briefs(limit: int = 20) -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM social_research_briefs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["data_points"] = json.loads(d.pop("data_points_json", "[]") or "[]")
        d["viral_beat_sheet"] = json.loads(d.pop("viral_beat_sheet_json", "[]") or "[]")
        d["sources"] = json.loads(d.pop("sources_json", "[]") or "[]")
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Media Assets (Avatars & Photos)
# ---------------------------------------------------------------------------

def register_media_asset(
    asset_type: str,
    title: str,
    file_path: str,
    pose_or_tags: str = "",
    source: str = "local",
    graded_path: Optional[str] = None,
) -> Dict[str, Any]:
    now = _now_iso()
    with _conn() as c:
        existing = c.execute("SELECT * FROM social_media_assets WHERE file_path = ?", (file_path,)).fetchone()
        if existing:
            c.execute(
                "UPDATE social_media_assets SET title=?, pose_or_tags=?, graded_path=COALESCE(?, graded_path) WHERE id=?",
                (title, pose_or_tags, graded_path, existing["id"]),
            )
            return dict(c.execute("SELECT * FROM social_media_assets WHERE id = ?", (existing["id"],)).fetchone())
        aid = f"ast_{uuid.uuid4().hex[:10]}"
        c.execute(
            """
            INSERT INTO social_media_assets
            (id, asset_type, title, file_path, graded_path, pose_or_tags, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (aid, asset_type, title, file_path, graded_path, pose_or_tags, source, now),
        )
    return {"id": aid, "asset_type": asset_type, "title": title, "file_path": file_path, "source": source, "created_at": now}


def list_media_assets(asset_type: Optional[str] = None) -> List[Dict[str, Any]]:
    _seed_existing_assets()
    with _conn() as c:
        if asset_type:
            rows = c.execute(
                "SELECT * FROM social_media_assets WHERE asset_type = ? ORDER BY created_at DESC",
                (asset_type,),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM social_media_assets ORDER BY asset_type ASC, created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_media_asset(asset_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        r = c.execute("SELECT * FROM social_media_assets WHERE id = ?", (asset_id,)).fetchone()
    return dict(r) if r else None


def update_media_asset_status(asset_id: str, approval_status: str) -> Optional[Dict[str, Any]]:
    allowed = {"MASTER", "APPROVED", "PENDING_REVIEW", "REJECTED"}
    if approval_status not in allowed:
        raise ValueError(f"Invalid approval_status: {approval_status}")
    with _conn() as c:
        if approval_status == "MASTER":
            c.execute("UPDATE social_media_assets SET approval_status = 'APPROVED' WHERE asset_type = 'avatar' AND approval_status = 'MASTER'")
        c.execute("UPDATE social_media_assets SET approval_status = ? WHERE id = ?", (approval_status, asset_id))
    return get_media_asset(asset_id)


def delete_media_asset(asset_id: str, remove_file: bool = True) -> bool:
    asset = get_media_asset(asset_id)
    if not asset:
        return False
    fpath = asset.get("file_path") or ""
    if remove_file and fpath and os.path.exists(fpath):
        # Never delete the protected reference inside avatar_refs
        if "/avatar_refs/" not in fpath:
            try:
                os.remove(fpath)
            except Exception:
                pass
    with _conn() as c:
        c.execute("DELETE FROM social_media_assets WHERE id = ?", (asset_id,))
    return True


def delete_social_post(post_id: str) -> bool:
    post = get_social_post(post_id)
    if not post:
        return False
    for mp in post.get("media_paths", []):
        if mp and os.path.exists(mp) and "/renders/" in mp:
            try:
                os.remove(mp)
            except Exception:
                pass
    with _conn() as c:
        c.execute("DELETE FROM social_posts WHERE id = ?", (post_id,))
    return True


# ---------------------------------------------------------------------------
# Social Posts & Approval Queue
# ---------------------------------------------------------------------------

def create_social_post(
    platform: str,
    title: str,
    caption: str,
    pillar: str = "market_update",
    visual_mode: str = "animated_avatar",
    hook: str = "",
    storyline: str = "",
    hashtags: str = "",
    script_text: str = "",
    media_paths: Optional[List[str]] = None,
    asset_ids: Optional[List[str]] = None,
    status: str = "PENDING_APPROVAL",
    scheduled_for: Optional[str] = None,
    compliance: Optional[Dict[str, Any]] = None,
    campaign_id: Optional[str] = None,
    created_by: str = "content_producer",
) -> Dict[str, Any]:
    pid = f"pst_{uuid.uuid4().hex[:10]}"
    now = _now_iso()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO social_posts
            (id, campaign_id, platform, pillar, visual_mode, title, hook, storyline, caption,
             hashtags, script_text, media_paths_json, asset_ids_json, status, scheduled_for,
             compliance_json, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pid,
                campaign_id or f"cmp_{uuid.uuid4().hex[:8]}",
                platform,
                pillar,
                visual_mode,
                title,
                hook,
                storyline,
                caption,
                hashtags,
                script_text,
                json.dumps(media_paths or []),
                json.dumps(asset_ids or []),
                status,
                scheduled_for,
                json.dumps(compliance or {}),
                created_by,
                now,
                now,
            ),
        )
        for aid in (asset_ids or []):
            c.execute("UPDATE social_media_assets SET usage_count = usage_count + 1 WHERE id = ?", (aid,))
    return get_social_post(pid) or {"id": pid}


def get_social_post(post_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        r = c.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["media_paths"] = json.loads(d.pop("media_paths_json", "[]") or "[]")
    d["asset_ids"] = json.loads(d.pop("asset_ids_json", "[]") or "[]")
    d["compliance"] = json.loads(d.pop("compliance_json", "{}") or "{}")
    return d


def list_social_posts(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    with _conn() as c:
        if status and status != "ALL":
            rows = c.execute(
                "SELECT * FROM social_posts WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM social_posts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["media_paths"] = json.loads(d.pop("media_paths_json", "[]") or "[]")
        d["asset_ids"] = json.loads(d.pop("asset_ids_json", "[]") or "[]")
        d["compliance"] = json.loads(d.pop("compliance_json", "{}") or "{}")
        out.append(d)
    return out


def update_social_post(post_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    allowed = {
        "caption", "hashtags", "title", "hook", "storyline", "status",
        "scheduled_for", "postiz_post_id", "postiz_integration_id",
        "revision_notes", "compliance_json", "media_paths_json",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_social_post(post_id)
    updates["updated_at"] = _now_iso()
    cols = ", ".join(f"{k} = ?" for k in updates.keys())
    vals = list(updates.values()) + [post_id]
    with _conn() as c:
        c.execute(f"UPDATE social_posts SET {cols} WHERE id = ?", vals)
    return get_social_post(post_id)


# ---------------------------------------------------------------------------
# Analytics & Cadence
# ---------------------------------------------------------------------------

def record_analytics_metric(
    platform: str,
    pillar: str = "market_update",
    visual_mode: str = "real_photo",
    impressions: int = 0,
    reach: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    saves: int = 0,
    post_id: Optional[str] = None,
    external_id: Optional[str] = None,
    published_at: Optional[str] = None,
    raw: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    score = round((likes * 1.0) + (comments * 3.0) + (shares * 4.0) + (saves * 5.0), 2)
    aid = f"anl_{uuid.uuid4().hex[:10]}"
    now = _now_iso()
    with _conn() as c:
        if external_id:
            existing = c.execute("SELECT id FROM social_analytics WHERE external_id = ?", (external_id,)).fetchone()
            if existing:
                c.execute(
                    """
                    UPDATE social_analytics
                    SET impressions=?, reach=?, likes=?, comments=?, shares=?, saves=?, engagement_score=?, synced_at=?
                    WHERE id=?
                    """,
                    (impressions, reach, likes, comments, shares, saves, score, now, existing["id"]),
                )
                return {"id": existing["id"], "engagement_score": score}
        c.execute(
            """
            INSERT INTO social_analytics
            (id, post_id, external_id, platform, pillar, visual_mode, published_at,
             impressions, reach, likes, comments, shares, saves, engagement_score, raw_json, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                aid, post_id, external_id, platform, pillar, visual_mode,
                published_at or now, impressions, reach, likes, comments, shares, saves,
                score, json.dumps(raw or {}), now,
            ),
        )
    return {"id": aid, "engagement_score": score}


def get_analytics_summary() -> Dict[str, Any]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM social_analytics ORDER BY published_at DESC LIMIT 200").fetchall()
    items = [dict(r) for r in rows]
    by_platform: Dict[str, Dict[str, Any]] = {}
    by_visual: Dict[str, Dict[str, Any]] = {}
    by_pillar: Dict[str, Dict[str, Any]] = {}

    for it in items:
        for bucket, key in [(by_platform, it["platform"]), (by_visual, it["visual_mode"]), (by_pillar, it["pillar"])]:
            b = bucket.setdefault(key, {"count": 0, "total_score": 0.0, "impressions": 0, "likes": 0, "saves": 0})
            b["count"] += 1
            b["total_score"] += float(it["engagement_score"] or 0)
            b["impressions"] += int(it["impressions"] or 0)
            b["likes"] += int(it["likes"] or 0)
            b["saves"] += int(it["saves"] or 0)

    for bucket in (by_platform, by_visual, by_pillar):
        for k, b in bucket.items():
            b["avg_score"] = round(b["total_score"] / max(b["count"], 1), 2)

    return {
        "total_tracked_posts": len(items),
        "by_platform": by_platform,
        "by_visual_mode": by_visual,
        "by_pillar": by_pillar,
        "recent": items[:15],
    }


def list_cadence_rules() -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM social_cadence_rules ORDER BY platform, day_of_week").fetchall()
    return [dict(r) for r in rows]


def replace_cadence_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = _now_iso()
    with _conn() as c:
        c.execute("DELETE FROM social_cadence_rules")
        for r in rules:
            c.execute(
                """
                INSERT INTO social_cadence_rules
                (id, platform, day_of_week, time_pt, pillar, recommended_format, preferred_visual_mode, confidence, rationale, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"cad_{uuid.uuid4().hex[:8]}",
                    r["platform"],
                    r["day_of_week"],
                    r["time_pt"],
                    r["pillar"],
                    r["recommended_format"],
                    r["preferred_visual_mode"],
                    float(r.get("confidence", 0.75)),
                    r.get("rationale", ""),
                    now,
                ),
            )
    return list_cadence_rules()


# ---------------------------------------------------------------------------
# OAuth Token Persistence (Google Photos Picker)
# ---------------------------------------------------------------------------

def save_oauth_token(provider: str, access_token: str, refresh_token: str = "", expires_at: str = "", scope: str = "") -> None:
    now = _now_iso()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO social_oauth_tokens (provider, access_token, refresh_token, expires_at, scope, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider) DO UPDATE SET
              access_token=excluded.access_token,
              refresh_token=COALESCE(NULLIF(excluded.refresh_token, ''), social_oauth_tokens.refresh_token),
              expires_at=excluded.expires_at,
              scope=excluded.scope,
              updated_at=excluded.updated_at
            """,
            (provider, access_token, refresh_token, expires_at, scope, now),
        )


def get_oauth_token(provider: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        r = c.execute("SELECT * FROM social_oauth_tokens WHERE provider = ?", (provider,)).fetchone()
    return dict(r) if r else None
