"""
Google Photos Picker API Integration
==================================
Implements OAuth 2.0 + Google Photos Picker API v1 sessions so Lokesh can
securely select personal photos from Google Photos and import them into
`/tank/social/photos/` for Maya Reyes & Nadia Kapoor.

Required scope: https://www.googleapis.com/auth/photospicker.mediaitems.readonly
"""

import os
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import httpx

from social_db import SOCIAL_DIR, get_oauth_token, register_media_asset, save_oauth_token

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_PHOTOS_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_PHOTOS_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_PHOTOS_REDIRECT_URI",
    "https://checkin.lokeshchanana.com/api/manager/social/google-photos/callback",
).strip()
PICKER_SCOPE = "https://www.googleapis.com/auth/photospicker.mediaitems.readonly"


def is_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def get_auth_url(state: str = "casa_poki_social") -> Dict[str, Any]:
    if not is_configured():
        return {
            "ok": False,
            "error": "GOOGLE_PHOTOS_CLIENT_ID and GOOGLE_PHOTOS_CLIENT_SECRET are not set in /tank/agents/.env",
        }
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": PICKER_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return {"ok": True, "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)}


async def exchange_code(code: str) -> Dict[str, Any]:
    if not is_configured():
        return {"ok": False, "error": "Google Photos OAuth not configured"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if r.status_code >= 400:
            return {"ok": False, "error": r.text[:400]}
        tok = r.json()
        exp = (datetime.utcnow() + timedelta(seconds=int(tok.get("expires_in", 3600)))).isoformat() + "Z"
        save_oauth_token(
            "google_photos",
            access_token=tok.get("access_token", ""),
            refresh_token=tok.get("refresh_token", ""),
            expires_at=exp,
            scope=tok.get("scope", PICKER_SCOPE),
        )
        return {"ok": True, "connected": True}


async def _get_valid_access_token() -> Optional[str]:
    tok = get_oauth_token("google_photos")
    if not tok:
        return None
    exp_str = tok.get("expires_at") or ""
    needs_refresh = True
    if exp_str:
        try:
            exp_dt = datetime.fromisoformat(exp_str.replace("Z", ""))
            needs_refresh = datetime.utcnow() >= (exp_dt - timedelta(minutes=2))
        except Exception:
            needs_refresh = True
    if not needs_refresh and tok.get("access_token"):
        return tok["access_token"]
    if not tok.get("refresh_token") or not is_configured():
        return tok.get("access_token")

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": tok["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        if r.status_code >= 400:
            return tok.get("access_token")
        data = r.json()
        exp = (datetime.utcnow() + timedelta(seconds=int(data.get("expires_in", 3600)))).isoformat() + "Z"
        save_oauth_token("google_photos", data["access_token"], tok["refresh_token"], exp, PICKER_SCOPE)
        return data["access_token"]


async def create_picker_session() -> Dict[str, Any]:
    token = await _get_valid_access_token()
    if not token:
        return {"ok": False, "needs_auth": True, "error": "Google Photos not connected yet."}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            "https://photospicker.googleapis.com/v1/sessions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={},
        )
        if r.status_code >= 400:
            return {"ok": False, "error": r.text[:400]}
        sess = r.json()
        picker_uri = sess.get("pickerUri", "")
        if picker_uri and not picker_uri.endswith("/autoclose"):
            picker_uri = picker_uri.rstrip("/") + "/autoclose"
        return {"ok": True, "session_id": sess.get("id"), "picker_uri": picker_uri, "session": sess}


async def poll_and_import_session(session_id: str) -> Dict[str, Any]:
    token = await _get_valid_access_token()
    if not token:
        return {"ok": False, "error": "Google Photos not authenticated"}
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        sr = await client.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}", headers=headers)
        if sr.status_code >= 400:
            return {"ok": False, "error": sr.text[:400]}
        sess = sr.json()
        if not sess.get("mediaItemsSet"):
            return {"ok": True, "ready": False, "imported": []}

        mr = await client.get(
            f"https://photospicker.googleapis.com/v1/mediaItems",
            params={"sessionId": session_id, "pageSize": 50},
            headers=headers,
        )
        if mr.status_code >= 400:
            return {"ok": False, "error": mr.text[:400]}
        items = mr.json().get("mediaItems", [])
        photo_dir = os.path.join(SOCIAL_DIR, "photos")
        os.makedirs(photo_dir, exist_ok=True)
        imported: List[Dict[str, Any]] = []
        for item in items:
            mf = item.get("mediaFile") or {}
            base_url = mf.get("baseUrl")
            mime = mf.get("mimeType", "image/jpeg")
            if not base_url or not mime.startswith("image/"):
                continue
            dl_url = f"{base_url}=d"
            img_resp = await client.get(dl_url, headers=headers)
            if img_resp.status_code != 200:
                continue
            ext = ".png" if "png" in mime else ".jpg"
            fname = f"gphoto_{item.get('id', 'item')[:14]}{ext}"
            fpath = os.path.join(photo_dir, fname)
            with open(fpath, "wb") as f:
                f.write(img_resp.content)
            asset = register_media_asset(
                asset_type="photo",
                title=mf.get("filename") or fname,
                file_path=fpath,
                pose_or_tags="google_photos,personal,loki",
                source="google_photos",
            )
            imported.append(asset)
        return {"ok": True, "ready": True, "imported": imported}
