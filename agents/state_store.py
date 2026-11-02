import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

DATA_DIR = os.environ.get("AGENT_DATA_DIR", "/app/data")
BACKLOG_DIR = os.environ.get("AGENT_BACKLOG_DIR", "/app/backlog/missing_n8n_workflows")
DB_PATH = os.path.join(DATA_DIR, "agent_system.db")


def init_store() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKLOG_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS token_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            tokens_per_sec REAL DEFAULT 0.0,
            duration_ms INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            rule TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            user_request TEXT NOT NULL,
            routed_agent TEXT NOT NULL,
            workflow_id TEXT,
            audit_status TEXT NOT NULL,
            quality_score INTEGER DEFAULT 0,
            findings TEXT NOT NULL,
            missing_capability TEXT,
            spec_file TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            user_feedback TEXT NOT NULL,
            target_agent TEXT DEFAULT 'auditor',
            action_taken TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    # Seed default lessons if empty
    cur.execute("SELECT COUNT(*) FROM agent_lessons")
    if cur.fetchone()[0] == 0:
        now = datetime.utcnow().isoformat() + "Z"
        seed_lessons = [
            (
                "manager",
                "Always check if an n8n workflow exists via the IT Agent before claiming a task can or cannot be automated.",
                "system_seed",
                now,
            ),
            (
                "manager",
                "Ration tokens strictly: keep internal agent routing JSON concise (<200 tokens) to preserve throughput budget.",
                "system_seed",
                now,
            ),
            (
                "it_agent",
                "Never fabricate API responses. Only execute active n8n workflows; if a workflow is inactive or missing, return an explicit MISSING_WORKFLOW or INACTIVE_WORKFLOW status.",
                "system_seed",
                now,
            ),
            (
                "auditor",
                "Distinguish clearly between QUALITY_IMPROVEMENT_NEEDED (agent made a mistake) and MISSING_CAPABILITY (no active n8n workflow exists for the task).",
                "system_seed",
                now,
            ),
        ]
        cur.executemany(
            "INSERT INTO agent_lessons (agent_name, rule, source, created_at) VALUES (?, ?, ?, ?)",
            seed_lessons,
        )

    conn.commit()
    conn.close()


def log_token_usage(
    task_id: str,
    agent_name: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    tokens_per_sec: float,
    duration_ms: int,
) -> Dict[str, Any]:
    init_store()
    total = prompt_tokens + completion_tokens
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO token_ledger
        (task_id, agent_name, model, prompt_tokens, completion_tokens, total_tokens, tokens_per_sec, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            agent_name,
            model,
            prompt_tokens,
            completion_tokens,
            total,
            round(tokens_per_sec, 2),
            duration_ms,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return {
        "agent": agent_name,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total,
        "tokens_per_sec": round(tokens_per_sec, 1),
        "duration_ms": duration_ms,
    }


def get_lessons(agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if agent_name:
        cur.execute(
            "SELECT id, agent_name, rule, source, created_at FROM agent_lessons WHERE agent_name = ? ORDER BY id DESC LIMIT 15",
            (agent_name,),
        )
    else:
        cur.execute(
            "SELECT id, agent_name, rule, source, created_at FROM agent_lessons ORDER BY id DESC LIMIT 50"
        )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "agent_name": r[1],
            "rule": r[2],
            "source": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]


def add_lesson(agent_name: str, rule: str, source: str = "auditor_feedback") -> Dict[str, Any]:
    init_store()
    rule_clean = rule.strip()
    if not rule_clean:
        return {}
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Avoid exact duplicates
    cur.execute(
        "SELECT id FROM agent_lessons WHERE agent_name = ? AND rule = ?",
        (agent_name, rule_clean),
    )
    existing = cur.fetchone()
    if existing:
        conn.close()
        return {"id": existing[0], "agent_name": agent_name, "rule": rule_clean, "source": source, "created_at": now}

    cur.execute(
        "INSERT INTO agent_lessons (agent_name, rule, source, created_at) VALUES (?, ?, ?, ?)",
        (agent_name, rule_clean, source, now),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": new_id,
        "agent_name": agent_name,
        "rule": rule_clean,
        "source": source,
        "created_at": now,
    }


def delete_lesson(lesson_id: int) -> bool:
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM agent_lessons WHERE id = ?", (lesson_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def log_audit_result(
    task_id: str,
    user_request: str,
    routed_agent: str,
    workflow_id: Optional[str],
    audit_status: str,
    quality_score: int,
    findings: str,
    missing_capability: Optional[str] = None,
    spec_file: Optional[str] = None,
) -> None:
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO audit_logs
        (task_id, user_request, routed_agent, workflow_id, audit_status, quality_score, findings, missing_capability, spec_file, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            user_request,
            routed_agent,
            workflow_id,
            audit_status,
            quality_score,
            findings,
            missing_capability,
            spec_file,
            now,
        ),
    )
    conn.commit()
    conn.close()


def get_last_audit_record() -> Optional[Dict[str, Any]]:
    """Returns the most recent execution audit record."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, task_id, user_request, routed_agent, workflow_id, audit_status, quality_score, findings, created_at FROM audit_logs ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_audit_status(
    task_id: str, new_status: str, new_score: int, additional_finding: str
) -> bool:
    """Updates an existing audit record with human feedback or re-evaluation."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE audit_logs
        SET audit_status = ?,
            quality_score = ?,
            findings = findings || ' | User Feedback: ' || ?
        WHERE task_id = ?
        """,
        (new_status, new_score, additional_finding, task_id),
    )
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def add_agent_feedback(
    user_feedback: str,
    task_id: Optional[str] = None,
    target_agent: str = "auditor",
    action_taken: str = "",
) -> Dict[str, Any]:
    """Records direct human feedback or quality notes for agents/Auditor."""
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO agent_feedback (task_id, user_feedback, target_agent, action_taken, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (task_id, user_feedback.strip(), target_agent, action_taken, now),
    )
    feedback_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": feedback_id,
        "task_id": task_id,
        "user_feedback": user_feedback,
        "target_agent": target_agent,
        "action_taken": action_taken,
        "created_at": now,
    }


def save_missing_workflow_spec(spec: Dict[str, Any], user_request: str, auditor_findings: str) -> Dict[str, Any]:
    """
    Writes a structured Markdown specification file to BACKLOG_DIR so the user
    can ask Antigravity to build the missing n8n workflow.
    """
    init_store()
    raw_name = spec.get("workflow_name") or spec.get("capability_name") or "missing_workflow"
    slug = re.sub(r"[^a-z0-9]+", "_", raw_name.lower()).strip("_") or "workflow_spec"
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    filename = f"{slug}.md"
    filepath = os.path.join(BACKLOG_DIR, filename)
    host_path = f"/home/lokesh/Casa-poki/agents/backlog/missing_n8n_workflows/{filename}"

    webhook_path = spec.get("webhook_path") or slug.replace("_", "-")
    domain = spec.get("domain") or "general"
    trigger_type = spec.get("trigger_type") or "Webhook (POST)"
    required_inputs = spec.get("required_inputs") or ["payload"]
    recommended_nodes = spec.get("recommended_n8n_nodes") or [
        "Webhook Trigger",
        "Code / HTTP Request Node",
        "Respond to Webhook",
    ]
    expected_output = spec.get("expected_output") or "JSON object with { ok: true, data: ... }"
    priority = spec.get("priority") or "Medium"
    existing_inactive_id = spec.get("existing_inactive_workflow_id")

    md_content = f"""# Missing n8n Workflow Spec: {raw_name}

- **Generated By:** Manager Agent (following Auditor Agent `MISSING_CAPABILITY` report)
- **Timestamp:** {now_str}
- **Domain / Target Agent:** `{domain}`
- **Priority:** `{priority}`
- **Status:** `PENDING_ANTIGRAVITY_BUILD`
{f"- **Existing Inactive n8n Workflow ID:** `{existing_inactive_id}` (Needs activation / webhook trigger configuration)" if existing_inactive_id else ""}

## 1. Original User Request
> {user_request}

## 2. Auditor & IT Agent Gap Report
{auditor_findings}

## 3. Proposed n8n Workflow Architecture
- **Workflow Name:** `{raw_name}`
- **Trigger Type:** `{trigger_type}`
- **Webhook Endpoint:** `POST http://192.168.1.240:5678/webhook/{webhook_path}`

### Expected Input JSON Payload
```json
{json.dumps({k: f"<{k}>" for k in (required_inputs if isinstance(required_inputs, list) else [str(required_inputs)])}, indent=2)}
```

### Recommended n8n Nodes
{chr(10).join(f"{idx+1}. **{node}**" for idx, node in enumerate(recommended_nodes if isinstance(recommended_nodes, list) else [str(recommended_nodes)]))}

### Expected Output JSON Schema
```json
{{
  "ok": true,
  "workflow": "{slug}",
  "result": "{expected_output}"
}}
```

## 4. Antigravity Build Prompt
Copy and paste this to Antigravity:
> Build and activate the n8n workflow specified in `{host_path}` and register its capability in `/home/lokesh/Casa-poki/agents/n8n_catalog.py`.
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Also update index.json in BACKLOG_DIR
    index_path = os.path.join(BACKLOG_DIR, "index.json")
    index_data: List[Dict[str, Any]] = []
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        except Exception:
            index_data = []

    record = {
        "slug": slug,
        "workflow_name": raw_name,
        "domain": domain,
        "webhook_path": f"/webhook/{webhook_path}",
        "priority": priority,
        "existing_inactive_workflow_id": existing_inactive_id,
        "user_request": user_request,
        "auditor_findings": auditor_findings,
        "required_inputs": required_inputs,
        "recommended_n8n_nodes": recommended_nodes,
        "expected_output": expected_output,
        "file_name": filename,
        "host_path": host_path,
        "antigravity_prompt": f"Build and activate the n8n workflow specified in {host_path} and register it for the IT Agent.",
        "updated_at": now_str,
    }

    # Replace if slug already exists, else prepend
    index_data = [item for item in index_data if item.get("slug") != slug]
    index_data.insert(0, record)

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

    return record


def get_backlog_specs() -> List[Dict[str, Any]]:
    init_store()
    index_path = os.path.join(BACKLOG_DIR, "index.json")
    if not os.path.exists(index_path):
        return []
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def get_system_summary() -> Dict[str, Any]:
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT agent_name,
               COUNT(*) as calls,
               COALESCE(SUM(prompt_tokens), 0),
               COALESCE(SUM(completion_tokens), 0),
               COALESCE(SUM(total_tokens), 0),
               COALESCE(AVG(tokens_per_sec), 0.0)
        FROM token_ledger
        GROUP BY agent_name
        """
    )
    by_agent = [
        {
            "agent": r[0],
            "calls": r[1],
            "prompt_tokens": r[2],
            "completion_tokens": r[3],
            "total_tokens": r[4],
            "avg_tokens_per_sec": round(r[5], 1),
        }
        for r in cur.fetchall()
    ]

    cur.execute(
        "SELECT COALESCE(SUM(total_tokens), 0), COALESCE(AVG(tokens_per_sec), 0.0) FROM token_ledger"
    )
    tot_row = cur.fetchone()

    cur.execute(
        """
        SELECT id, task_id, user_request, routed_agent, workflow_id, audit_status, quality_score, findings, missing_capability, spec_file, created_at
        FROM audit_logs
        ORDER BY id DESC
        LIMIT 20
        """
    )
    recent_audits = [
        {
            "id": r[0],
            "task_id": r[1],
            "user_request": r[2],
            "routed_agent": r[3],
            "workflow_id": r[4],
            "audit_status": r[5],
            "quality_score": r[6],
            "findings": r[7],
            "missing_capability": r[8],
            "spec_file": r[9],
            "created_at": r[10],
        }
        for r in cur.fetchall()
    ]

    cur.execute(
        """
        SELECT id, task_id, user_feedback, target_agent, action_taken, created_at
        FROM agent_feedback
        ORDER BY id DESC
        LIMIT 10
        """
    )
    recent_feedback = [
        {
            "id": r[0],
            "task_id": r[1],
            "user_feedback": r[2],
            "target_agent": r[3],
            "action_taken": r[4],
            "created_at": r[5],
        }
        for r in cur.fetchall()
    ]

    conn.close()

    return {
        "token_stats": {
            "total_tokens_all_time": tot_row[0] if tot_row else 0,
            "avg_tokens_per_sec": round(tot_row[1], 1) if tot_row else 0.0,
            "budget_per_task": 2000,
            "throughput_target_tok_s": 500,
            "by_agent": by_agent,
        },
        "lessons": get_lessons(),
        "recent_audits": recent_audits,
        "recent_feedback": recent_feedback,
        "missing_workflows_backlog": get_backlog_specs(),
    }
