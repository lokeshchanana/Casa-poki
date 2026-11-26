import asyncio
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from infra_tools import (
    check_uptime_kuma,
    handle_infra_alert,
    list_docker_containers,
    restart_container,
)
from multimodal import save_and_extract_attachment
from n8n_catalog import get_n8n_workflows
from orchestrator import (
    DEFAULT_MODEL,
    DEFAULT_TASK_BUDGET,
    resume_approved_tool,
    run_multi_agent_pipeline,
)
from state_store import (
    add_lesson,
    cancel_post_close_drip,
    clear_chat_history,
    delete_lesson,
    get_chat_history,
    get_office_floor_state,
    get_recent_request_flows,
    get_request_flow_stats,
    get_system_summary,
    init_store,
    list_chat_sessions,
)
import vector_memory
from webhooks import (
    handle_bill_intake,
    handle_communication_intake,
    handle_open_house_sign_in,
    handle_payment_intake,
    handle_website_contact,
    sync_email_lifecycle_updates,
)
from tools import (
    _direct_enroll_buyer_post_close,
    _direct_list_post_close_drips,
    _direct_process_post_close_drips,
)
import social_db
from social_router import router as social_router
from webhooks_router import router as webhooks_router
from brevo_sync import sync_twenty_to_brevo

app = FastAPI(title="Multi-Agent Manager Hub (Manager + IT + Auditor + Social Studio)")
app.include_router(social_router)
app.include_router(webhooks_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    chatInput: str
    sessionId: Optional[str] = "manager_default"
    tokenBudget: Optional[int] = DEFAULT_TASK_BUDGET
    attachments: Optional[List[Dict[str, Any]]] = None


class ApprovalRequest(BaseModel):
    approvalId: str
    decision: str
    editedArgs: Optional[Dict[str, Any]] = None


class LessonRequest(BaseModel):
    agent_name: str
    rule: str


class HealRequest(BaseModel):
    container_name: str


class MemoryStoreRequest(BaseModel):
    agent_id: str = "manager"
    content: str
    category: str = "domain_knowledge"


class MemoryQueryRequest(BaseModel):
    query: str
    agent_id: Optional[str] = None
    category: Optional[str] = None
    top_k: Optional[int] = 4


@app.on_event("startup")
def on_startup() -> None:
    init_store()
    social_db.init_social_db()
    vector_memory.init_vector_memory_db()
    asyncio.create_task(_post_close_scheduler_loop())
    asyncio.create_task(_email_lifecycle_scheduler_loop())


async def _email_lifecycle_scheduler_loop() -> None:
    """
    Background worker that runs once per day (every 24 hours) for Silas Drake + Miles Miller
    to scan lokesh@lokeshchanana.com (last 48h, read-only BODY.PEEK[]) and sync
    real estate lifecycle updates to Twenty CRM.
    """
    await asyncio.sleep(45)
    while True:
        try:
            await sync_email_lifecycle_updates(days_back=2, max_messages=60)
        except Exception:
            pass
        await asyncio.sleep(86400)


@app.post("/api/manager/email/lifecycle-sync")
async def trigger_email_lifecycle_sync(days_back: int = 2) -> dict:
    return await sync_email_lifecycle_updates(days_back=days_back)


async def _post_close_scheduler_loop() -> None:
    """
    Background worker that runs every hour to check active buyer post-close
    drip enrollments and deliver scheduled Brevo templates.
    """
    await asyncio.sleep(15)
    while True:
        try:
            await _direct_process_post_close_drips({})
        except Exception as e:
            pass
        await asyncio.sleep(3600)


@app.get("/api/manager/health")
def health() -> dict:
    return {"status": "ok", "model": DEFAULT_MODEL}


@app.get("/api/manager/dashboard")
def dashboard() -> dict:
    summary = get_system_summary()
    workflows = get_n8n_workflows()
    return {
        "model": DEFAULT_MODEL,
        "workflows": workflows,
        **summary,
    }


@app.get("/api/manager/office/floor-state")
def office_floor_state() -> dict:
    return get_office_floor_state()


@app.get("/api/manager/office/flows")
def office_flows(
    limit: int = 200,
    category: Optional[str] = None,
    exclude_category: Optional[str] = None,
    agent: Optional[str] = None,
    search: Optional[str] = None,
) -> list:
    return get_recent_request_flows(
        limit=limit,
        category=category,
        exclude_category=exclude_category,
        agent=agent,
        search=search,
    )


@app.get("/api/manager/office/flow-stats")
def office_flow_stats() -> dict:
    return get_request_flow_stats()


@app.get("/api/manager/office/containers")
def office_containers() -> dict:
    return list_docker_containers()


@app.get("/api/manager/office/monitors")
def office_monitors() -> dict:
    return check_uptime_kuma()


@app.post("/api/manager/office/heal")
def manual_heal(req: HealRequest) -> dict:
    res = restart_container(req.container_name)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@app.post("/api/manager/lessons")
def create_lesson(req: LessonRequest) -> dict:
    saved = add_lesson(req.agent_name, req.rule, source="manual_ui")
    return {"ok": True, "lesson": saved}


@app.delete("/api/manager/lessons/{lesson_id}")
def remove_lesson(lesson_id: int) -> dict:
    deleted = delete_lesson(lesson_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return {"ok": True}


# =============================================================================
# Vector Memory Database Endpoints
# =============================================================================

@app.get("/api/manager/memory/stats")
def memory_stats() -> dict:
    return vector_memory.get_memory_stats()


@app.post("/api/manager/memory/store")
def memory_store(req: MemoryStoreRequest) -> dict:
    res = vector_memory.store_memory(
        agent_id=req.agent_id,
        content=req.content,
        category=req.category,
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@app.post("/api/manager/memory/query")
def memory_query(req: MemoryQueryRequest) -> dict:
    matches = vector_memory.query_memories(
        query=req.query,
        agent_id=req.agent_id,
        category=req.category,
        top_k=req.top_k or 4,
    )
    return {"ok": True, "query": req.query, "matches": matches, "count": len(matches)}


@app.get("/api/manager/chat/sessions")
async def manager_chat_sessions(limit: int = 30):
    return {"ok": True, "sessions": list_chat_sessions(limit=limit)}


@app.get("/api/manager/chat/history")
async def manager_chat_history(sessionId: Optional[str] = "manager_primary", limit: int = 50):
    msgs = get_chat_history(sessionId or "manager_primary", limit=limit)
    return {"ok": True, "sessionId": sessionId, "messages": msgs}


@app.delete("/api/manager/chat/history")
async def manager_delete_chat_history(sessionId: Optional[str] = "manager_primary"):
    clear_chat_history(sessionId or "manager_primary")
    return {"ok": True, "sessionId": sessionId}


@app.post("/api/manager/chat")
async def manager_chat(req: ChatRequest):
    if not req.chatInput or not req.chatInput.strip():
        raise HTTPException(status_code=400, detail="chatInput is required")

    budget = req.tokenBudget or DEFAULT_TASK_BUDGET
    return StreamingResponse(
        run_multi_agent_pipeline(
            user_message=req.chatInput.strip(),
            session_id=req.sessionId or "manager_primary",
            token_budget=budget,
            attachments=req.attachments,
        ),
        media_type="application/x-ndjson",
    )


@app.post("/api/manager/upload")
async def manager_upload(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    res = save_and_extract_attachment(
        filename=file.filename or "upload.bin",
        content_bytes=raw,
        content_type=file.content_type or "",
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Upload failed"))
    return res


@app.post("/api/manager/chat/approve")
async def manager_chat_approve(req: ApprovalRequest) -> dict:
    res = await resume_approved_tool(
        approval_id=req.approvalId,
        decision=req.decision,
        edited_args=req.editedArgs,
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Approval failed"))
    return res


# =============================================================================
# Inbound Webhook Endpoints (Direct to Agent Hub)
# =============================================================================

@app.post("/webhook/open-house-sign-in")
async def webhook_open_house(req: Request) -> JSONResponse:
    try:
        body = await req.json()
    except Exception:
        body = {}
    result = await handle_open_house_sign_in(body)
    return JSONResponse(content=result)


@app.post("/webhook/website-contact")
async def webhook_website_contact(req: Request) -> JSONResponse:
    try:
        body = await req.json()
    except Exception:
        body = {}
    result = await handle_website_contact(body)
    return JSONResponse(content=result)


@app.post("/webhook/infra-alert")
@app.post("/api/agent/webhook/infra-alert")
async def webhook_infra_alert(req: Request) -> JSONResponse:
    try:
        body = await req.json()
    except Exception:
        body = {}
    result = await handle_infra_alert(body)
    return JSONResponse(content=result)


@app.post("/webhook/twenty-brevo-sync")
async def webhook_brevo_sync(req: Request) -> JSONResponse:
    return JSONResponse(content={"ok": True, "message": "Brevo sync acknowledged by Agent Hub."})


@app.post("/webhook/brevo-event-webhook")
async def webhook_brevo_event(req: Request) -> JSONResponse:
    try:
        body = await req.json()
    except Exception:
        body = {}
    event = body.get("event")
    email = body.get("email")
    if email and event in ("unsubscribed", "hard_bounce", "complaint"):
        cancel_post_close_drip(email)
    return JSONResponse(content={"ok": True, "message": "Brevo event acknowledged by Agent Hub."})


@app.post("/webhook/post-close-enroll")
async def webhook_post_close_enroll(req: Request) -> JSONResponse:
    try:
        body = await req.json()
    except Exception:
        body = {}
    res = await _direct_enroll_buyer_post_close(body)
    return JSONResponse(content=res)


@app.post("/webhook/post-close-process")
async def webhook_post_close_process(req: Request) -> JSONResponse:
    try:
        body = await req.json()
    except Exception:
        body = {}
    res = await _direct_process_post_close_drips(body)
    return JSONResponse(content=res)


@app.get("/api/marketing/post-close-drips")
async def api_list_post_close_drips() -> JSONResponse:
    res = await _direct_list_post_close_drips({})
    return JSONResponse(content=res)


@app.post("/webhook/bill-intake")
async def webhook_bill_intake(req: Request) -> JSONResponse:
    try:
        body = await req.json()
    except Exception:
        body = {}
    result = await handle_bill_intake(body)
    return JSONResponse(content=result)


@app.post("/webhook/payment-intake")
async def webhook_payment_intake(req: Request) -> JSONResponse:
    try:
        body = await req.json()
    except Exception:
        body = {}
    result = await handle_payment_intake(body)
    return JSONResponse(content=result)


@app.post("/webhook/communication-intake")
async def webhook_communication_intake(req: Request) -> JSONResponse:
    try:
        body = await req.json()
    except Exception:
        body = {}
    result = await handle_communication_intake(body)
    return JSONResponse(content=result)


@app.on_event("startup")
async def _start_brevo_sync_scheduler() -> None:
    async def _loop() -> None:
        await asyncio.sleep(60)
        while True:
            try:
                await sync_twenty_to_brevo()
            except Exception as exc:
                print(f"[brevo_sync] Scheduled sync error: {exc}")
            await asyncio.sleep(6 * 3600)

    asyncio.create_task(_loop())
