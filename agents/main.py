from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from infra_tools import (
    check_uptime_kuma,
    handle_infra_alert,
    list_docker_containers,
    restart_container,
)
from n8n_catalog import get_n8n_workflows
from orchestrator import DEFAULT_MODEL, DEFAULT_TASK_BUDGET, run_multi_agent_pipeline
from state_store import (
    add_lesson,
    delete_lesson,
    get_chat_history,
    get_office_floor_state,
    get_recent_request_flows,
    get_system_summary,
    init_store,
)
import vector_memory
from webhooks import (
    handle_bill_intake,
    handle_communication_intake,
    handle_open_house_sign_in,
    handle_payment_intake,
    handle_website_contact,
)

app = FastAPI(title="Multi-Agent Manager Hub (Manager + IT + Auditor)")

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
    vector_memory.init_vector_memory_db()


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
def office_flows(limit: int = 30) -> list:
    return get_recent_request_flows(limit=limit)


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


@app.get("/api/manager/chat/history")
async def manager_chat_history(sessionId: Optional[str] = "manager_default", limit: int = 30):
    msgs = get_chat_history(sessionId or "manager_default", limit=limit)
    return {"ok": True, "sessionId": sessionId, "messages": msgs}


@app.post("/api/manager/chat")
async def manager_chat(req: ChatRequest):
    if not req.chatInput or not req.chatInput.strip():
        raise HTTPException(status_code=400, detail="chatInput is required")

    budget = req.tokenBudget or DEFAULT_TASK_BUDGET
    return StreamingResponse(
        run_multi_agent_pipeline(
            user_message=req.chatInput.strip(),
            session_id=req.sessionId or "manager_default",
            token_budget=budget,
        ),
        media_type="application/x-ndjson",
    )


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
    return JSONResponse(content={"ok": True, "message": "Brevo event acknowledged by Agent Hub."})


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
