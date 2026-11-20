"""
Social Studio & Approval Queue FastAPI Router (Static-First + Avatar Review)
============================================================================
Exposes `/api/manager/social/*` endpoints for `checkin.lokeshchanana.com`:
  - Dashboard & Approval Queue (list, approve & schedule to Postiz, revise, reject, delete)
  - Static Post Generator (WA Market Infographic, IG Carousel/Post/Story, Facebook, X)
  - Media Assets (Approve / Set Master / Reject & Remove avatars, upload photos, serve files)
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


class AssetStatusRequest(BaseModel):
    approval_status: str  # 'MASTER' | 'APPROVED' | 'PENDING_REVIEW' | 'REJECTED'


class GenerateSampleRequest(BaseModel):
    platform: str = "market_infographic"
    visual_mode: str = "animated_avatar"
    pillar: str = "market_update"
    kicker: str = "WA MARKET PULSE"
    region: str = "King County • Kent, WA"
    title: str = "King County Housing Market Analysis"
    subheadline: str = "Weekly Puget Sound Snapshot"
    caption: str = ""
    stats: Optional[List[Dict[str, str]]] = None
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
        "static_only_mode": True,
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
        f"{req.title} ({req.region}). Across Greater Seattle, buyers are getting a little more breathing room "
        "on days on market while well-prepped homes in Kent, Renton, and Bothell continue to move steadily. "
        "Want a neighborhood breakdown tailored to your budget? Call or text (801) 860-1052.\n\n"
        "Lokesh Chanana (Loki) • Real Broker LLC"
    )
    return await social_tools.execute_social_tool(
        "social_render_content",
        {
            "platform": req.platform,
            "visual_mode": req.visual_mode,
            "pillar": req.pillar,
            "kicker": req.kicker,
            "region": req.region,
            "title": req.title,
            "subheadline": req.subheadline,
            "caption": caption,
            "stats": req.stats or [],
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


@router.delete("/posts/{post_id}")
def delete_post(post_id: str) -> Dict[str, Any]:
    ok = social_db.delete_social_post(post_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"ok": True, "deleted": post_id}


@router.get("/assets")
def list_assets(asset_type: Optional[str] = None) -> Dict[str, Any]:
    social_db.init_social_db()
    return {"ok": True, "assets": social_db.list_media_assets(asset_type=asset_type)}


@router.post("/assets/{asset_id}/status")
def update_asset_status(asset_id: str, req: AssetStatusRequest) -> Dict[str, Any]:
    try:
        updated = social_db.update_media_asset_status(asset_id, req.approval_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"ok": True, "asset": updated}


@router.delete("/assets/{asset_id}")
def reject_and_delete_asset(asset_id: str) -> Dict[str, Any]:
    ok = social_db.delete_media_asset(asset_id, remove_file=True)
    if not ok:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"ok": True, "deleted": asset_id}


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
