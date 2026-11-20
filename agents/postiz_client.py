"""
Postiz Self-Hosted Public API v1 Client
======================================
Connects Casa-poki Agent Hub to the local Postiz instance
(http://192.168.1.240:4007/api/public/v1) for channel discovery, media upload,
post scheduling (ONLY after owner approval), and past-post analytics.
"""

import os
from typing import Any, Dict, List, Optional
import httpx

POSTIZ_BASE_URL = os.environ.get("POSTIZ_BASE_URL", "http://192.168.1.240:4007/api/public/v1").rstrip("/")
POSTIZ_API_KEY = os.environ.get("POSTIZ_API_KEY", "").strip()


def _headers() -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if POSTIZ_API_KEY:
        h["Authorization"] = POSTIZ_API_KEY
    return h


def is_configured() -> bool:
    return bool(POSTIZ_API_KEY)


async def check_status() -> Dict[str, Any]:
    """Check Postiz reachability and whether an API key is configured."""
    base_root = POSTIZ_BASE_URL.replace("/api/public/v1", "")
    reachable = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(base_root)
            reachable = resp.status_code < 500
    except Exception:
        reachable = False

    integrations: List[Dict[str, Any]] = []
    if reachable and POSTIZ_API_KEY:
        res = await list_integrations()
        if res.get("ok"):
            integrations = res.get("integrations", [])

    return {
        "reachable": reachable,
        "api_key_configured": bool(POSTIZ_API_KEY),
        "base_url": POSTIZ_BASE_URL,
        "integrations_count": len(integrations),
        "integrations": integrations,
    }


async def list_integrations() -> Dict[str, Any]:
    if not POSTIZ_API_KEY:
        return {"ok": False, "error": "POSTIZ_API_KEY is not configured in /tank/agents/.env", "integrations": []}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{POSTIZ_BASE_URL}/integrations", headers=_headers())
            if r.status_code >= 400:
                return {"ok": False, "status": r.status_code, "error": r.text[:400], "integrations": []}
            data = r.json()
            items = data if isinstance(data, list) else data.get("integrations", data.get("data", []))
            return {"ok": True, "integrations": items}
    except Exception as e:
        return {"ok": False, "error": str(e), "integrations": []}


async def upload_media(file_path: str) -> Dict[str, Any]:
    if not POSTIZ_API_KEY:
        return {"ok": False, "error": "POSTIZ_API_KEY not configured"}
    if not os.path.exists(file_path):
        return {"ok": False, "error": f"File not found: {file_path}"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                r = await client.post(f"{POSTIZ_BASE_URL}/upload", headers=_headers(), files=files)
            if r.status_code >= 400:
                return {"ok": False, "status": r.status_code, "error": r.text[:400]}
            return {"ok": True, "media": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def create_scheduled_post(
    integration_id: str,
    provider_type: str,
    content: str,
    scheduled_at_iso: str,
    media_objects: Optional[List[Dict[str, Any]]] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Schedule an already-approved post into Postiz."""
    if not POSTIZ_API_KEY:
        return {"ok": False, "error": "POSTIZ_API_KEY not configured"}
    payload = {
        "type": "schedule",
        "date": scheduled_at_iso,
        "shortLink": False,
        "tags": [],
        "posts": [
            {
                "integration": {"id": integration_id},
                "value": [
                    {
                        "content": content,
                        "image": media_objects or [],
                    }
                ],
                "settings": {"__type": provider_type, **(settings or {})},
            }
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{POSTIZ_BASE_URL}/posts",
                headers={**_headers(), "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code >= 400:
                return {"ok": False, "status": r.status_code, "error": r.text[:500]}
            return {"ok": True, "result": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def get_analytics(days: int = 30) -> Dict[str, Any]:
    if not POSTIZ_API_KEY:
        return {"ok": False, "error": "POSTIZ_API_KEY not configured", "items": []}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(f"{POSTIZ_BASE_URL}/posts", headers=_headers())
            if r.status_code >= 400:
                return {"ok": False, "status": r.status_code, "error": r.text[:400], "items": []}
            data = r.json()
            items = data if isinstance(data, list) else data.get("posts", data.get("data", []))
            return {"ok": True, "items": items}
    except Exception as e:
        return {"ok": False, "error": str(e), "items": []}
