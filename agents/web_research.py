import asyncio
import hashlib
import ipaddress
import json
import logging
import os
import re
import socket
import xml.etree.ElementTree as ET
from typing import Any, Dict, List
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from state_store import (
    get_cached_search,
    get_search_quota_status,
    reserve_search_quota,
    set_cached_search,
)

logger = logging.getLogger("agent_web_research")

TAVILY_MONTHLY_LIMIT = 900
TAVILY_DAILY_LIMIT = 35
BRAVE_MONTHLY_LIMIT = 900
BRAVE_DAILY_LIMIT = 35


def _is_private_or_local_host(hostname: str) -> bool:
    if not hostname:
        return True
    low = hostname.strip().lower()
    if low in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or low.endswith(".local"):
        return True
    try:
        ip_obj = ipaddress.ip_address(low)
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
        )
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(low, None)
        for info in infos:
            addr = info[4][0]
            ip_obj = ipaddress.ip_address(addr)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                return True
    except Exception:
        return True
    return False


async def fetch_webpage(url: str, max_chars: int = 8000) -> Dict[str, Any]:
    """
    SSRF-safe webpage reader that extracts clean readable text from public URLs.
    """
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        return {"ok": False, "error": "Only http/https URLs are allowed"}
    if _is_private_or_local_host(parsed.hostname or ""):
        return {"ok": False, "error": f"Blocked private/internal host: {parsed.hostname}"}

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CasaPokiAgent/2.0)"},
            )
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else url
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text(separator="\n", strip=True))
    return {
        "ok": True,
        "url": url,
        "title": title,
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


async def _search_tavily(query: str, max_results: int = 5) -> Dict[str, Any]:
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key or "your_" in api_key:
        return {"ok": False, "reason": "no_key"}

    quota = reserve_search_quota("tavily", credits=1, monthly_limit=TAVILY_MONTHLY_LIMIT, daily_limit=TAVILY_DAILY_LIMIT)
    if not quota["allowed"]:
        logger.warning(f"Tavily zero-spend cap reached: {quota}")
        return {"ok": False, "reason": "quota_cap_reached", "quota": quota}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",  # Strictly locked to 1 credit/call
                    "max_results": min(max_results, 8),
                    "include_answer": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": (r.get("content") or "")[:500],
                "source": "tavily",
            }
            for r in (data.get("results") or [])
        ]
        return {
            "ok": True,
            "provider": "tavily",
            "answer": data.get("answer") or "",
            "results": results,
            "quota": quota,
        }
    except Exception as e:
        logger.warning(f"Tavily search error: {e}")
        return {"ok": False, "reason": str(e)}


async def _search_brave(query: str, max_results: int = 5) -> Dict[str, Any]:
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not api_key or "your_" in api_key:
        return {"ok": False, "reason": "no_key"}

    quota = reserve_search_quota("brave", credits=1, monthly_limit=BRAVE_MONTHLY_LIMIT, daily_limit=BRAVE_DAILY_LIMIT)
    if not quota["allowed"]:
        logger.warning(f"Brave zero-spend cap reached: {quota}")
        return {"ok": False, "reason": "quota_cap_reached", "quota": quota}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": min(max_results, 10)},
                headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            )
            resp.raise_for_status()
            data = resp.json()
        raw_results = ((data.get("web") or {}).get("results") or [])[:max_results]
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": (r.get("description") or "")[:500],
                "source": "brave",
            }
            for r in raw_results
        ]
        return {"ok": True, "provider": "brave", "answer": "", "results": results, "quota": quota}
    except Exception as e:
        logger.warning(f"Brave search error: {e}")
        return {"ok": False, "reason": str(e)}


async def _search_google_news_rss(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Free zero-key fallback using Google News RSS."""
    rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(rss_url)
            resp.raise_for_status()
        root = ET.fromstring(resp.text)
        items = root.findall(".//item")[:max_results]
        results = []
        for it in items:
            results.append({
                "title": (it.findtext("title") or "").strip(),
                "url": (it.findtext("link") or "").strip(),
                "snippet": (it.findtext("pubDate") or "").strip(),
                "source": "google_news_rss",
            })
        return {"ok": True, "provider": "google_news_rss", "answer": "", "results": results}
    except Exception as e:
        return {"ok": False, "provider": "google_news_rss", "error": str(e), "results": []}


async def web_search(query: str, max_results: int = 5, prefer: str = "auto") -> Dict[str, Any]:
    """
    Zero-Spend Live Web Search:
    1. Checks 15-minute SQLite cache first (0 credits).
    2. Reserves quota atomically (max 900/mo, 35/day) on Tavily or Brave.
    3. Automatically falls back to free Google News RSS if capped/unavailable.
    """
    q_clean = (query or "").strip()
    if not q_clean:
        return {"ok": False, "error": "Query cannot be empty"}

    cache_key = hashlib.sha256(f"{prefer}:{q_clean.lower()}:{max_results}".encode()).hexdigest()
    cached = get_cached_search(cache_key)
    if cached:
        cached["cached"] = True
        return cached

    providers = ["brave", "tavily"] if prefer == "brave" else ["tavily", "brave"]
    res: Dict[str, Any] = {"ok": False}

    for p in providers:
        res = await (_search_tavily(q_clean, max_results) if p == "tavily" else _search_brave(q_clean, max_results))
        if res.get("ok"):
            break

    if not res.get("ok"):
        res = await _search_google_news_rss(q_clean, max_results)

    if res.get("ok"):
        res["query"] = q_clean
        res["citations"] = [
            {"index": i + 1, "title": r["title"], "url": r["url"], "source": r["source"]}
            for i, r in enumerate(res.get("results") or [])
        ]
        res["quota_status"] = get_search_quota_status()
        set_cached_search(cache_key, res.get("provider", "fallback"), q_clean, res, ttl_seconds=900)
    return res


async def deep_search(question: str, depth: int = 2) -> Dict[str, Any]:
    """
    Grok-style iterative DeepSearch:
    Runs parallel sub-queries + fetches top pages + merges deduplicated citations.
    """
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "Question is required"}

    sub_queries = [q]
    if depth >= 2:
        sub_queries.append(f"{q} latest 2026 statistics")

    search_runs = await asyncio.gather(*[web_search(sq, max_results=4, prefer="tavily" if i == 0 else "brave") for i, sq in enumerate(sub_queries)])

    seen_urls = set()
    all_results: List[Dict[str, Any]] = []
    for sr in search_runs:
        for r in sr.get("results") or []:
            u = r.get("url")
            if u and u not in seen_urls:
                seen_urls.add(u)
                all_results.append(r)

    # Fetch full text of top 2 unique URLs in parallel
    top_urls = [r["url"] for r in all_results[:2] if r.get("url")]
    fetched_pages = await asyncio.gather(*[fetch_webpage(u, max_chars=4000) for u in top_urls]) if top_urls else []

    citations = [
        {"index": i + 1, "title": r.get("title", ""), "url": r.get("url", ""), "source": r.get("source", "")}
        for i, r in enumerate(all_results[:8])
    ]
    return {
        "ok": True,
        "question": q,
        "sub_queries": sub_queries,
        "results": all_results[:8],
        "extracted_pages": [p for p in fetched_pages if p.get("ok")],
        "citations": citations,
        "quota_status": get_search_quota_status(),
    }
