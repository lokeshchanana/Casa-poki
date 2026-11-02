from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from n8n_catalog import get_n8n_workflows
from orchestrator import DEFAULT_MODEL, DEFAULT_TASK_BUDGET, run_multi_agent_pipeline
from state_store import add_lesson, delete_lesson, get_system_summary, init_store

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


@app.on_event("startup")
def on_startup() -> None:
    init_store()


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
