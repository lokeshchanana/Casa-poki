import json
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from state_store import (
    get_session_plan,
    get_session_summary,
    get_tool_artifact,
    save_tool_artifact,
    upsert_session_summary,
)

MAX_INLINE_CHARS = 3500
ACTIVE_HISTORY_WINDOW = 14
COMPACT_CHAR_THRESHOLD = 18000


def store_or_inline_tool_output(
    session_id: str,
    tool_name: str,
    result: Any,
    max_inline_chars: int = MAX_INLINE_CHARS,
) -> str:
    """
    Returns full JSON if <= max_inline_chars. Otherwise saves the full payload
    to SQLite `tool_artifacts` and returns a concise preview + artifact_id so
    zero records are silently truncated.
    """
    serialized = json.dumps(result, default=str)
    if len(serialized) <= max_inline_chars:
        return serialized

    row_count = 0
    if isinstance(result, dict):
        for k in ("contacts", "items", "bills", "emails", "results", "data", "rows"):
            if isinstance(result.get(k), list):
                row_count = len(result[k])
                break
    elif isinstance(result, list):
        row_count = len(result)

    artifact_id = f"art_{uuid.uuid4().hex[:10]}"
    summary = f"{tool_name} output ({len(serialized)} chars, {row_count} items)"
    save_tool_artifact(
        artifact_id=artifact_id,
        session_id=session_id,
        tool_name=tool_name,
        full_json=serialized,
        row_count=row_count,
        summary=summary,
    )
    envelope = {
        "ok": result.get("ok", True) if isinstance(result, dict) else True,
        "artifact_id": artifact_id,
        "stored_full_output": True,
        "total_chars": len(serialized),
        "row_count": row_count,
        "preview_head": serialized[:1600],
        "instruction": f"Use inspect_artifact(artifact_id='{artifact_id}', query='...', offset=0, limit=25) to search or paginate remaining data.",
    }
    return json.dumps(envelope)


def inspect_artifact_data(
    artifact_id: str,
    query: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    art = get_tool_artifact(artifact_id)
    if not art:
        return {"ok": False, "error": f"Artifact '{artifact_id}' not found"}

    try:
        parsed = json.loads(art["full_json"])
    except Exception:
        text = art["full_json"]
        if query:
            lines = [ln for ln in text.splitlines() if query.lower() in ln.lower()]
            return {"ok": True, "artifact_id": artifact_id, "matches": lines[offset : offset + limit], "total_matches": len(lines)}
        chunk = text[offset : offset + 3000]
        return {"ok": True, "artifact_id": artifact_id, "slice": chunk, "total_chars": len(text)}

    # If dict with a primary list, paginate or filter that list
    if isinstance(parsed, dict):
        for k in ("contacts", "items", "bills", "emails", "results", "data", "rows"):
            if isinstance(parsed.get(k), list):
                items = parsed[k]
                if query:
                    ql = query.lower()
                    items = [it for it in items if ql in json.dumps(it, default=str).lower()]
                sliced = items[offset : offset + limit]
                return {
                    "ok": True,
                    "artifact_id": artifact_id,
                    "field": k,
                    "total_matching": len(items),
                    "offset": offset,
                    "items": sliced,
                }

    if isinstance(parsed, list):
        items = parsed
        if query:
            ql = query.lower()
            items = [it for it in items if ql in json.dumps(it, default=str).lower()]
        return {
            "ok": True,
            "artifact_id": artifact_id,
            "total_matching": len(items),
            "offset": offset,
            "items": items[offset : offset + limit],
        }

    raw = json.dumps(parsed, default=str)
    return {"ok": True, "artifact_id": artifact_id, "slice": raw[offset : offset + 3000], "total_chars": len(raw)}


async def build_compacted_context(
    session_id: str,
    full_history: List[Dict[str, Any]],
    call_llm_fn: Optional[Callable[..., Awaitable[Dict[str, Any]]]] = None,
    task_id: str = "compact",
) -> Dict[str, Any]:
    """
    PreCompact / PostCompact rolling context manager:
    Keeps up to ACTIVE_HISTORY_WINDOW recent turns verbatim. Older turns beyond
    the window are summarized into `session_summaries` using the fast model tier,
    preserving IDs, addresses, amounts, and open decisions.
    """
    existing = get_session_summary(session_id)
    summary_text = existing["summary"] if existing else ""
    active_plan = get_session_plan(session_id)

    total_chars = sum(len(m.get("content") or "") for m in full_history)
    if len(full_history) <= ACTIVE_HISTORY_WINDOW and total_chars <= COMPACT_CHAR_THRESHOLD:
        return {
            "summary": summary_text,
            "plan": active_plan,
            "messages": full_history,
        }

    older = full_history[:-ACTIVE_HISTORY_WINDOW] if len(full_history) > ACTIVE_HISTORY_WINDOW else full_history[:-6]
    recent = full_history[len(older) :]

    if older and call_llm_fn is not None:
        older_blob = "\n".join(
            f"{m.get('role', 'user').upper()}: {(m.get('content') or '')[:800]}"
            for m in older
        )
        compact_prompt = [
            {
                "role": "system",
                "content": (
                    "Summarize the earlier conversation turns into concise bullet points. "
                    "MUST preserve exact contact UUIDs, property addresses, dollar amounts, "
                    "bill reference numbers, and pending decisions."
                ),
            },
            {
                "role": "user",
                "content": f"Prior Summary:\n{summary_text or 'None'}\n\nTurns to Compact:\n{older_blob}",
            },
        ]
        try:
            resp = await call_llm_fn(
                task_id=task_id,
                agent_name="context_compactor",
                messages=compact_prompt,
                tools=None,
                max_tokens=500,
                temperature=0.0,
                model_tier="fast",
            )
            new_summary = (resp.get("content") or "").strip()
            if new_summary and not new_summary.startswith("Antigravity Error:"):
                summary_text = new_summary
                last_id = int(older[-1].get("id") or 0)
                upsert_session_summary(session_id, summary_text, last_id)
        except Exception:
            pass

    return {
        "summary": summary_text,
        "plan": active_plan,
        "messages": recent,
    }
