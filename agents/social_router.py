"""
Social Studio & Approval Queue FastAPI Router
=============================================
Exposes `/api/manager/social/*` endpoints for `checkin.lokeshchanana.com`:
  - Dashboard & Approval Queue (list, approve & schedule to Postiz, revise, reject)
  - Campaign & Research Launcher (run Devon/Maya/Leo/Priya via execute_social_tool)
  - Media Assets (avatars + photos + direct upload + secure file serving)
  - Google Photos Picker OAuth + session polling
  - Analytics & Adaptive Cadence
"""

import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

import google_photos_picker
import postiz_client
import social_db
import social_tools

router = APIRouter(prefix="/api/manager/social", tags=["Social Studio"])


class ApprovePostRequest(BaseModel):
    scheduled_for: Optional[str] = None
    integration_id: Optional[str] = None
    edited_caption: Optional[str] = None


class RevisePostRequest(BaseModel):
    revision_notes: str


class GenerateSampleRequest(BaseModel):
    platform: str = "instagram_carousel"
    visual_mode: str = "animated_avatar"
    pillar: str = "market_update"
    kicker: str = "WA MARKET PULSE"
    title: str = "What $750k Buys in Greater Seattle Right Now"
    subheadline: str = "King & Pierce County Weekly Snapshot"
    caption: str = ""
    script_text: str = ""
    asset_id: Optional[str] = None


@router.get("/overview")
async def social_overview() -> Dict[str, Any]:
    social_db.init_social_db()
    posts = social_db.list_social_posts(status="ALL", limit=60)
    assets = social_db.list_media_assets()
    briefs = social_db.list_research_briefs(limit=12)
    cadence = social_db.list_cadence_rules()
    analytics = social_db.get_analytics_summary()
    postiz_status = await postiz_client.check_status()
    return {
        "ok": True,
        "posts": posts,
        "assets": assets,
        "briefs": briefs,
        "cadence": cadence,
        "analytics": analytics,
        "postiz": postiz_status,
        "google_photos": {
            "configured": google_photos_picker.is_configured(),
            "connected": bool(social_db.get_oauth_token("google_photos")),
        },
    }


@router.get("/posts")
def list_posts(status: str = "ALL") -> Dict[str, Any]:
    social_db.init_social_db()
    return {"ok": True, "posts": social_db.list_social_posts(status=status)}


@router.post("/posts/generate")
async def generate_post(req: GenerateSampleRequest) -> Dict[str, Any]:
    caption = req.caption.strip() or (
        f"{req.title}. Across Greater Seattle, buyers are seeing more breathing room on days-on-market "
        "while well-prepped Craftsman homes in Renton, Kent, and Bothell still move fast. "
        "Want the neighborhood-by-neighborhood breakdown for your budget? Call or text (801) 860-1052.\n\n"
        "Lokesh Chanana (Loki) • Real Broker LLC"
    )
    script = req.script_text.strip() or (
        f"Here is your quick Greater Seattle market pulse. {req.title}. "
        "Instead of chasing national headlines, look at local inventory and monthly payment comfort. "
        "Reach out anytime at 801-860-1052 for a custom neighborhood breakdown."
    )
    return await social_tools.execute_social_tool(
        "social_render_content",
        {
            "platform": req.platform,
            "visual_mode": req.visual_mode,
            "pillar": req.pillar,
            "kicker": req.kicker,
            "title": req.title,
            "subheadline": req.subheadline,
            "caption": caption,
            "script_text": script,
            "asset_id": req.asset_id,
        },
    )


@router.post("/posts/{post_id}/approve")
async def approve_post(post_id: str, req: ApprovePostRequest) -> Dict[str, Any]:
    return await social_tools.approve_and_schedule_post(
        post_id=post_id,
        scheduled_for=req.scheduled_for,
        integration_id=req.integration_id,
        edited_caption=req.edited_caption,
    )


@router.post("/posts/{post_id}/revise")
def revise_post(post_id: str, req: RevisePostRequest) -> Dict[str, Any]:
    updated = social_db.update_social_post(
        post_id, status="REVISION_REQUESTED", revision_notes=req.revision_notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"ok": True, "post": updated}


@router.post("/posts/{post_id}/reject")
def reject_post(post_id: str) -> Dict[str, Any]:
    updated = social_db.update_social_post(post_id, status="REJECTED")
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"ok": True, "post": updated}


@router.get("/assets")
def list_assets(asset_type: Optional[str] = None) -> Dict[str, Any]:
    social_db.init_social_db()
    return {"ok": True, "assets": social_db.list_media_assets(asset_type=asset_type)}


@router.post("/assets/upload")
async def upload_photo(file: UploadFile = File(...), title: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    photo_dir = os.path.join(social_db.SOCIAL_DIR, "photos")
    os.makedirs(photo_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "photo.jpg")[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(status_code=400, detail="Only JPG, PNG, or WEBP images are supported")
    dest = os.path.join(photo_dir, f"upload_{uuid.uuid4().hex[:10]}{ext}")
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    asset = social_db.register_media_asset(
        asset_type="photo",
        title=title or file.filename or "Uploaded Photo",
        file_path=dest,
        pose_or_tags="upload,personal,loki",
        source="upload",
    )
    return {"ok": True, "asset": asset}


@router.get("/media-file")
def serve_media_file(path: str = Query(...)):
    """Serve rendered images/videos or avatars/photos safely from /tank/social."""
    real_base = os.path.realpath(social_db.SOCIAL_DIR)
    real_target = os.path.realpath(path)
    if not real_target.startswith(real_base + os.sep) or not os.path.exists(real_target):
        raise HTTPException(status_code=404, detail="Media file not found")
    return FileResponse(real_target)


@router.post("/analytics/sync")
async def sync_analytics() -> Dict[str, Any]:
    res = await social_tools.sync_analytics_and_reels()
    cadence = social_tools.compute_adaptive_cadence()
    return {"ok": True, "sync": res, "cadence": cadence["rules"]}


@router.get("/google-photos/auth-url")
def google_photos_auth_url() -> Dict[str, Any]:
    return google_photos_picker.get_auth_url()


@router.get("/google-photos/callback")
async def google_photos_callback(code: str = Query(...)) -> HTMLResponse:
    res = await google_photos_picker.exchange_code(code)
    if res.get("ok"):
        return HTMLResponse("<h3>Google Photos Connected! You may close this window and return to Social Studio.</h3>")
    return HTMLResponse(f"<h3>Connection error: {res.get('error')}</h3>", status_code=400)


@router.post("/google-photos/session")
async def create_google_photos_session() -> Dict[str, Any]:
    return await google_photos_picker.create_picker_session()


@router.get("/google-photos/session/{session_id}")
async def poll_google_photos_session(session_id: str) -> Dict[str, Any]:
    return await google_photos_picker.poll_and_import_session(session_id)
