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

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_calls TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS request_flows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flow_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            agents_involved TEXT NOT NULL,
            steps TEXT NOT NULL,
            payload_preview TEXT,
            result_summary TEXT,
            duration_ms INTEGER DEFAULT 0,
            category TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )

    try:
        cur.execute("ALTER TABLE request_flows ADD COLUMN category TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

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

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_communications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            sender TEXT,
            subject TEXT,
            event_type TEXT,
            client_name TEXT,
            client_id TEXT,
            deal_id TEXT,
            details TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS post_close_drips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id TEXT NOT NULL UNIQUE,
            deal_id TEXT,
            email TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            property_address TEXT,
            close_date TEXT NOT NULL,
            is_new_construction INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ACTIVE',
            sent_templates TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS post_close_drip_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drip_id INTEGER NOT NULL,
            contact_id TEXT NOT NULL,
            template_id INTEGER NOT NULL,
            day_offset INTEGER NOT NULL,
            sent_at TEXT NOT NULL,
            status TEXT NOT NULL,
            response_details TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_drive_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT UNIQUE NOT NULL,
            file_name TEXT NOT NULL,
            vendor_name TEXT,
            amount REAL,
            bill_date TEXT,
            bill_id INTEGER,
            status TEXT NOT NULL,
            details TEXT,
            processed_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_email_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE NOT NULL,
            sender TEXT,
            subject TEXT,
            vendor_name TEXT,
            amount REAL,
            bill_date TEXT,
            due_date TEXT,
            bill_id INTEGER,
            status TEXT NOT NULL,
            details TEXT,
            processed_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ha_health_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            ha_version TEXT,
            total_entities INTEGER DEFAULT 0,
            critical_unavailable INTEGER DEFAULT 0,
            broken_automations INTEGER DEFAULT 0,
            persistent_alerts INTEGER DEFAULT 0,
            issues_json TEXT,
            actions_taken_json TEXT,
            summary TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tax_audit_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_no TEXT UNIQUE NOT NULL,
            vendor_name TEXT NOT NULL,
            bill_date TEXT NOT NULL,
            due_date TEXT,
            subtotal REAL DEFAULT 0.0,
            tax_amount REAL DEFAULT 0.0,
            total_amount REAL DEFAULT 0.0,
            category TEXT,
            payment_status TEXT NOT NULL,
            payment_method TEXT,
            bigcapital_bill_id INTEGER,
            bigcapital_payment_id INTEGER,
            proof_status TEXT NOT NULL,
            proof_path TEXT,
            proof_sha256 TEXT,
            gdrive_file_id TEXT,
            gdrive_folder_id TEXT,
            source_type TEXT,
            source_id TEXT,
            audit_notes TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tax_audit_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auditor_name TEXT NOT NULL,
            audit_status TEXT NOT NULL,
            total_bills_checked INTEGER DEFAULT 0,
            verified_count INTEGER DEFAULT 0,
            flagged_count INTEGER DEFAULT 0,
            duplicates_found INTEGER DEFAULT 0,
            unsettled_paid_found INTEGER DEFAULT 0,
            findings_json TEXT,
            summary TEXT,
            created_at TEXT NOT NULL
        )
        """
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
            "budget_per_task": 32000,
            "throughput_target_tok_s": 500,
            "by_agent": by_agent,
        },
        "lessons": get_lessons(),
        "recent_audits": recent_audits,
        "recent_feedback": recent_feedback,
        "missing_workflows_backlog": get_backlog_specs(),
    }


def add_chat_message(
    session_id: str,
    role: str,
    content: str,
    tool_calls: Optional[Any] = None,
) -> None:
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    tc_json = json.dumps(tool_calls) if tool_calls else None
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO chat_history (session_id, role, content, tool_calls, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, role, content, tc_json, now),
    )
    conn.commit()
    conn.close()


def get_chat_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content, tool_calls, created_at
        FROM chat_history
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit),
    )
    rows = cur.fetchall()
    conn.close()

    history = []
    for r in reversed(rows):
        msg: Dict[str, Any] = {"role": r[0], "content": r[1], "created_at": r[3]}
        if r[2]:
            try:
                msg["tool_calls"] = json.loads(r[2])
            except Exception:
                pass
        history.append(msg)
    return history


def clear_chat_history(session_id: str) -> None:
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def categorize_request_flow(
    source: str,
    title: str,
    agents_involved: List[str],
    payload_preview: Any = None,
) -> str:
    """Deterministically categorizes an agent request flow for log filtering."""
    blob = " ".join([
        str(source or ""),
        str(title or ""),
        " ".join(str(a) for a in (agents_involved or [])),
        json.dumps(payload_preview) if isinstance(payload_preview, (dict, list)) else str(payload_preview or ""),
    ]).lower()

    if any(k in blob for k in ("hannah reed", "ha_guardian", "ha_health", "ha_fix", "home assistant", "homeassistant", "ha.lokeshchanana.com")):
        return "home_assistant"
    if any(k in blob for k in ("uptime kuma", "infra alert", "healed service", "ian torres", "docker", "self-heal", "auto-heal", "beszel")):
        return "infra"
    if any(k in blob for k in ("fiona banks", "victor sterling", "bigcapital", "tax_audit", "finance_", "invoice", "bill", "expense", "expanse", "receipt", "tax")):
        return "finance"
    if any(k in blob for k in ("silas drake", "mailman", "inbox", "email triage", "unread email")):
        return "email"
    if any(k in blob for k in ("maya reyes", "carter hayes", "cma", "mls", "post-close", "drip", "marketing", "listing")):
        return "marketing"
    if any(k in blob for k in ("miles miller", "twenty crm", "open house", "search_contacts", "create_contact", "update_contact", "crm", "lead", "intake")):
        return "crm"
    return "general"


def log_request_flow(
    flow_id: str,
    source: str,
    title: str,
    status: str,
    agents_involved: List[str],
    steps: List[Dict[str, Any]],
    payload_preview: Optional[Any] = None,
    result_summary: Optional[str] = None,
    duration_ms: int = 0,
    category: Optional[str] = None,
) -> None:
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    agents_json = json.dumps(agents_involved)
    steps_json = json.dumps(steps)
    payload_str = json.dumps(payload_preview) if isinstance(payload_preview, (dict, list)) else str(payload_preview or "")
    resolved_cat = category or categorize_request_flow(source, title, agents_involved, payload_preview)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO request_flows (
            flow_id, source, title, status, agents_involved, steps, payload_preview, result_summary, duration_ms, category, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (flow_id, source, title, status, agents_json, steps_json, payload_str, result_summary or "", duration_ms, resolved_cat, now),
    )
    conn.commit()
    conn.close()


def _backfill_flow_categories(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, source, title, agents_involved, payload_preview FROM request_flows WHERE category IS NULL OR category = ''"
    ).fetchall()
    if not rows:
        return
    for row_id, src, title, agents_raw, payload_raw in rows:
        try:
            agents = json.loads(agents_raw) if agents_raw else []
        except Exception:
            agents = []
        cat = categorize_request_flow(src, title, agents, payload_raw)
        cur.execute("UPDATE request_flows SET category = ? WHERE id = ?", (cat, row_id))
    conn.commit()


def get_recent_request_flows(
    limit: int = 200,
    category: Optional[str] = None,
    exclude_category: Optional[str] = None,
    agent: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_store()
    conn = sqlite3.connect(DB_PATH)
    _backfill_flow_categories(conn)
    cur = conn.cursor()

    where_clauses = []
    params: List[Any] = []

    if category and category != "all":
        where_clauses.append("category = ?")
        params.append(category)
    if exclude_category:
        where_clauses.append("category != ?")
        params.append(exclude_category)
    if agent and agent != "all":
        where_clauses.append("LOWER(agents_involved) LIKE ?")
        params.append(f"%{agent.lower()}%")
    if search and search.strip():
        q = f"%{search.strip().lower()}%"
        where_clauses.append(
            "(LOWER(title) LIKE ? OR LOWER(source) LIKE ? OR LOWER(agents_involved) LIKE ? OR LOWER(result_summary) LIKE ? OR LOWER(payload_preview) LIKE ?)"
        )
        params.extend([q, q, q, q, q])

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    safe_limit = max(1, min(int(limit or 200), 500))
    params.append(safe_limit)

    cur.execute(
        f"""
        SELECT flow_id, source, title, status, agents_involved, steps, payload_preview, result_summary, duration_ms, category, created_at
        FROM request_flows
        {where_sql}
        ORDER BY id DESC
        LIMIT ?
        """,
        params,
    )
    rows = cur.fetchall()
    conn.close()

    flows = []
    for r in rows:
        try:
            agents = json.loads(r[4])
        except Exception:
            agents = []
        try:
            steps = json.loads(r[5])
        except Exception:
            steps = []
        try:
            payload = json.loads(r[6])
        except Exception:
            payload = r[6]

        flows.append({
            "flow_id": r[0],
            "source": r[1],
            "title": r[2],
            "status": r[3],
            "agents_involved": agents,
            "steps": steps,
            "payload_preview": payload,
            "result_summary": r[7],
            "duration_ms": r[8],
            "category": r[9] or categorize_request_flow(r[1], r[2], agents, payload),
            "created_at": r[10],
        })
    return flows


def get_request_flow_stats() -> Dict[str, Any]:
    """Returns total count, per-category counts, and per-agent counts across all logged flows."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    _backfill_flow_categories(conn)
    cur = conn.cursor()

    rows = cur.execute("SELECT category, agents_involved FROM request_flows").fetchall()
    conn.close()

    category_counts: Dict[str, int] = {}
    agent_counts: Dict[str, int] = {}
    total = len(rows)
    non_ha_total = 0

    for cat, agents_raw in rows:
        c = cat or "general"
        category_counts[c] = category_counts.get(c, 0) + 1
        if c != "home_assistant":
            non_ha_total += 1
        try:
            agents = json.loads(agents_raw) if agents_raw else []
        except Exception:
            agents = []
        seen_in_row = set()
        for a in agents:
            name = str(a).strip()
            if name and name not in seen_in_row:
                seen_in_row.add(name)
                agent_counts[name] = agent_counts.get(name, 0) + 1

    return {
        "total": total,
        "non_ha_total": non_ha_total,
        "category_counts": category_counts,
        "agent_counts": agent_counts,
    }


OFFICE_PERSONAS = [
    {
        "id": "manager",
        "name": "Marcus Vance",
        "role": "General Manager & Orchestrator",
        "station": "Corner Office Suite",
        "avatar": "👔",
        "color": "indigo",
        "default_activity": "Reviewing client portfolios & delegating requests",
    },
    {
        "id": "it",
        "name": "Ian Torres",
        "role": "IT Systems & Infrastructure Guardian",
        "station": "Server Pod & Telemetry Desk",
        "avatar": "💻",
        "color": "emerald",
        "default_activity": "Auditing Docker containers & Uptime Kuma monitors",
    },
    {
        "id": "auditor",
        "name": "Audrey Chen",
        "role": "Quality Assurance & Compliance Auditor",
        "station": "Audit & Review Station",
        "avatar": "📋",
        "color": "amber",
        "default_activity": "Verifying tool call outputs & architectural specs",
    },
    {
        "id": "intake",
        "name": "Miles Miller",
        "role": "Client Intake & Communications",
        "station": "Front Reception & Webhook Gateway",
        "avatar": "📨",
        "color": "blue",
        "default_activity": "Processing Open House sign-ins & website inquiries",
    },
    {
        "id": "finance",
        "name": "Fiona Banks",
        "role": "Financial Controller & Bigcapital Manager",
        "station": "Ledger & Financial Controller Desk",
        "avatar": "📊",
        "color": "teal",
        "default_activity": "Managing bills, payables, and Bigcapital finances at finance.lokeshchanana.com",
    },
    {
        "id": "marketing",
        "name": "Maya Reyes",
        "role": "Creative Director & Listing Promotions",
        "station": "Marketing Creative Studio",
        "avatar": "🎨",
        "color": "rose",
        "default_activity": "Drafting open house announcements & marketing collateral",
    },
    {
        "id": "cma",
        "name": "Carter Hayes",
        "role": "Real Estate Analyst & CMA Specialist",
        "station": "Market Valuation Lab",
        "avatar": "🏡",
        "color": "violet",
        "default_activity": "Analyzing Northwest MLS comps & valuation models",
    },
    {
        "id": "homeassistant",
        "name": "Hannah Reed",
        "role": "Home Assistant Guardian & Smart Home Engineer",
        "station": "Smart Home & HA Control Pod",
        "avatar": "🏠",
        "color": "cyan",
        "default_activity": "Monitoring Home Assistant (192.168.1.251) & auto-healing entities",
    },
    {
        "id": "tax_auditor",
        "name": "Victor Sterling",
        "role": "Independent CPA & IRS Tax Compliance Auditor",
        "station": "Tax & Forensic Audit Desk",
        "avatar": "⚖️",
        "color": "amber",
        "default_activity": "Auditing Fiona's Bigcapital ledger & verifying IRS proof archive",
    },
    {
        "id": "social_scout",
        "name": "Devon Brooks",
        "role": "WA Market & Viral Trends Scout",
        "station": "Social Media Wing • Trends Desk",
        "avatar": "📡",
        "color": "sky",
        "default_activity": "Tracking Greater Seattle market stats & viral Reels formats",
    },
    {
        "id": "avatar_artist",
        "name": "Nadia Kapoor",
        "role": "Animated Avatar Studio & Photo Curator",
        "station": "Social Media Wing • Avatar Lab",
        "avatar": "🎭",
        "color": "fuchsia",
        "default_activity": "Curating Google Photos & Loki's Animated Avatar Pack",
    },
    {
        "id": "content_producer",
        "name": "Leo Bennett",
        "role": "Multi-Platform Content Producer",
        "station": "Social Media Wing • Render Bay",
        "avatar": "🎬",
        "color": "orange",
        "default_activity": "Rendering 4:5 carousels & 9:16 talking-avatar Reels",
    },
    {
        "id": "social_ops",
        "name": "Priya Nair",
        "role": "Social Analytics, Cadence & Approval Desk",
        "station": "Social Media Wing • Analytics Hub",
        "avatar": "📈",
        "color": "lime",
        "default_activity": "Optimizing Pacific Time cadence & Postiz approval queue",
    },
]


def get_office_floor_state() -> Dict[str, Any]:
    """
    Computes real-time persona states based on recent events and idle habits.
    """
    flows = get_recent_request_flows(limit=10)
    
    # Check if any flow happened within the last 3 minutes
    now = datetime.utcnow()
    active_agent_names = set()
    
    for f in flows:
        try:
            created_dt = datetime.fromisoformat(f["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            diff_sec = (now - created_dt).total_seconds()
            if diff_sec < 180: # Active in last 3 mins
                for a in f.get("agents_involved", []):
                    active_agent_names.add(a.lower())
        except Exception:
            pass

    # Assign dynamic statuses
    agents_state = []
    for p in OFFICE_PERSONAS:
        p_name_lower = p["name"].lower()
        is_active = any(p_name_lower in a or p["id"] in a for a in active_agent_names)
        
        # Idle status variations: coffee break, watercooler, reviewing notes
        minute = now.minute + hash(p["id"]) % 60
        if is_active:
            status = "active"
            status_text = "Processing request..."
            activity = f"Handling live task from recent flow"
        else:
            status = "idle"
            if minute % 4 == 0:
                status_text = "Coffee Break"
                activity = "Grabbing an espresso in the kitchen ☕"
            elif minute % 4 == 1:
                status_text = "Watercooler Chat"
                activity = "Chatting about current Bellevue market trends 🗣️"
            elif minute % 4 == 2:
                status_text = "Desk Research"
                activity = p["default_activity"]
            else:
                status_text = "At Desk"
                activity = "Monitoring incoming queue & reviewing logs 📖"

        agents_state.append({
            **p,
            "status": status,
            "status_text": status_text,
            "current_activity": activity,
        })

    return {
        "timestamp": now.isoformat() + "Z",
        "agents": agents_state,
        "recent_flows": flows,
    }


def is_communication_processed(message_id: str) -> bool:
    if not message_id:
        return False
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM processed_communications WHERE message_id = ?", (message_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def record_processed_communication(
    message_id: str,
    source: str,
    sender: str,
    subject: str,
    event_type: str,
    client_name: Optional[str] = None,
    client_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    if not message_id:
        return
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    details_str = json.dumps(details or {}) if isinstance(details, dict) else str(details or "")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO processed_communications 
        (message_id, source, sender, subject, event_type, client_name, client_id, deal_id, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (message_id, source, sender, subject, event_type, client_name, client_id, deal_id, details_str, now),
    )
    conn.commit()
    conn.close()


# =============================================================================
# Buyer Post-Close Drip Automation State Helpers
# =============================================================================

def enroll_post_close_drip(
    contact_id: str,
    email: str,
    first_name: str,
    last_name: str,
    property_address: str,
    close_date: str,
    is_new_construction: bool = False,
    deal_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enrolls or updates a buyer contact into the Post-Close Drip Automation.
    """
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    is_new_const_int = 1 if is_new_construction else 0
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO post_close_drips
        (contact_id, deal_id, email, first_name, last_name, property_address, close_date, is_new_construction, status, sent_templates, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', '[]', ?, ?)
        ON CONFLICT(contact_id) DO UPDATE SET
            deal_id=excluded.deal_id,
            email=excluded.email,
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            property_address=excluded.property_address,
            close_date=excluded.close_date,
            is_new_construction=excluded.is_new_construction,
            status='ACTIVE',
            updated_at=excluded.updated_at
        """,
        (contact_id, deal_id, email.lower().strip(), first_name, last_name, property_address, close_date, is_new_const_int, now, now),
    )
    drip_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "drip_id": drip_id,
        "contact_id": contact_id,
        "email": email.lower().strip(),
        "close_date": close_date,
        "is_new_construction": bool(is_new_construction),
        "status": "ACTIVE",
    }


def get_active_post_close_drips() -> List[Dict[str, Any]]:
    """
    Returns all active buyer post-close drip enrollments.
    """
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, contact_id, deal_id, email, first_name, last_name, property_address, 
               close_date, is_new_construction, status, sent_templates, created_at, updated_at
        FROM post_close_drips
        WHERE status = 'ACTIVE'
        ORDER BY id ASC
        """
    )
    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        item["is_new_construction"] = bool(item["is_new_construction"])
        try:
            item["sent_templates"] = json.loads(item["sent_templates"])
        except Exception:
            item["sent_templates"] = []
        results.append(item)
    return results


def get_post_close_drip_by_contact(contact_id_or_email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a drip enrollment by contact_id or email.
    """
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, contact_id, deal_id, email, first_name, last_name, property_address, 
               close_date, is_new_construction, status, sent_templates, created_at, updated_at
        FROM post_close_drips
        WHERE contact_id = ? OR email = ?
        LIMIT 1
        """,
        (contact_id_or_email, contact_id_or_email.lower().strip()),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    item["is_new_construction"] = bool(item["is_new_construction"])
    try:
        item["sent_templates"] = json.loads(item["sent_templates"])
    except Exception:
        item["sent_templates"] = []
    return item


def record_post_close_drip_send(
    drip_id: int,
    contact_id: str,
    template_id: int,
    day_offset: int,
    status: str = "SENT",
    details: str = "",
) -> None:
    """
    Logs an email send and appends the template_id to sent_templates.
    """
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Log entry
    cur.execute(
        """
        INSERT INTO post_close_drip_logs
        (drip_id, contact_id, template_id, day_offset, sent_at, status, response_details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (drip_id, contact_id, template_id, day_offset, now, status, details),
    )

    # 2. Update sent_templates in post_close_drips
    cur.execute("SELECT sent_templates FROM post_close_drips WHERE id = ?", (drip_id,))
    row = cur.fetchone()
    sent_list = []
    if row and row[0]:
        try:
            sent_list = json.loads(row[0])
        except Exception:
            sent_list = []
    if template_id not in sent_list:
        sent_list.append(template_id)
        cur.execute(
            "UPDATE post_close_drips SET sent_templates = ?, updated_at = ? WHERE id = ?",
            (json.dumps(sent_list), now, drip_id),
        )

    conn.commit()
    conn.close()


def cancel_post_close_drip(contact_id_or_email: str) -> bool:
    """
    Cancels or unsubscribes a contact from the drip automation.
    """
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE post_close_drips
        SET status = 'CANCELLED', updated_at = ?
        WHERE contact_id = ? OR email = ?
        """,
        (now, contact_id_or_email, contact_id_or_email.lower().strip()),
    )
    changed = cur.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def is_drive_bill_processed(file_id: str) -> bool:
    """Checks if a Google Drive bill file has already been processed into Bigcapital."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM processed_drive_bills WHERE file_id = ?", (file_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def record_processed_drive_bill(
    file_id: str,
    file_name: str,
    vendor_name: str,
    amount: float,
    bill_date: str,
    bill_id: Optional[int] = None,
    status: str = "PROCESSED",
    details: Optional[str] = None,
) -> int:
    """Records or updates a processed Google Drive bill record in the local database."""
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO processed_drive_bills (file_id, file_name, vendor_name, amount, bill_date, bill_id, status, details, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_id) DO UPDATE SET
            file_name = excluded.file_name,
            vendor_name = excluded.vendor_name,
            amount = excluded.amount,
            bill_date = excluded.bill_date,
            bill_id = excluded.bill_id,
            status = excluded.status,
            details = excluded.details,
            processed_at = excluded.processed_at
        """,
        (file_id, file_name, vendor_name, amount, bill_date, bill_id, status, details, now),
    )
    last_id = cur.lastrowid
    conn.commit()
    conn.close()
    return last_id


def list_processed_drive_bills(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns recent processed Google Drive bills from the database."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM processed_drive_bills ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_processed_drive_bill(file_id: str) -> bool:
    """Removes a processed drive bill entry (e.g. for re-processing or test cleanup)."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM processed_drive_bills WHERE file_id = ?", (file_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def is_email_bill_processed(message_id: str) -> bool:
    """Checks if an email bill/statement has already been processed into Bigcapital."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM processed_email_bills WHERE message_id = ?", (message_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def record_processed_email_bill(
    message_id: str,
    sender: str,
    subject: str,
    vendor_name: str,
    amount: float,
    bill_date: str,
    due_date: Optional[str] = None,
    bill_id: Optional[int] = None,
    status: str = "PROCESSED",
    details: Optional[str] = None,
) -> int:
    """Records or updates a processed email bill record in the local database."""
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO processed_email_bills (message_id, sender, subject, vendor_name, amount, bill_date, due_date, bill_id, status, details, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
            sender = excluded.sender,
            subject = excluded.subject,
            vendor_name = excluded.vendor_name,
            amount = excluded.amount,
            bill_date = excluded.bill_date,
            due_date = excluded.due_date,
            bill_id = excluded.bill_id,
            status = excluded.status,
            details = excluded.details,
            processed_at = excluded.processed_at
        """,
        (message_id, sender, subject, vendor_name, amount, bill_date, due_date or bill_date, bill_id, status, details, now),
    )
    last_id = cur.lastrowid
    conn.commit()
    conn.close()
    return last_id


def list_processed_email_bills(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns recent processed email bills from the database."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM processed_email_bills ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_processed_email_bill(message_id: str) -> bool:
    """Removes a processed email bill entry (e.g. for re-processing or testing)."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM processed_email_bills WHERE message_id = ?", (message_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def log_ha_health_event(
    status: str,
    ha_version: Optional[str] = None,
    total_entities: int = 0,
    critical_unavailable: int = 0,
    broken_automations: int = 0,
    persistent_alerts: int = 0,
    issues: Optional[List[Dict[str, Any]]] = None,
    actions_taken: Optional[List[Dict[str, Any]]] = None,
    summary: Optional[str] = None,
) -> int:
    """Persists a Home Assistant health audit / auto-heal event in agent_system.db."""
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ha_health_logs (
            status, ha_version, total_entities, critical_unavailable,
            broken_automations, persistent_alerts, issues_json,
            actions_taken_json, summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            status,
            ha_version,
            total_entities,
            critical_unavailable,
            broken_automations,
            persistent_alerts,
            json.dumps(issues or []),
            json.dumps(actions_taken or []),
            summary or "",
            now,
        ),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def list_ha_health_logs(limit: int = 20) -> List[Dict[str, Any]]:
    """Returns recent Home Assistant health & remediation logs."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM ha_health_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_processed_email_bill(message_id: str) -> Optional[Dict[str, Any]]:
    """Returns an existing processed_email_bills row by message_id."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM processed_email_bills WHERE message_id = ?", (message_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_processed_drive_bill(file_id: str) -> Optional[Dict[str, Any]]:
    """Returns an existing processed_drive_bills row by file_id."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM processed_drive_bills WHERE file_id = ?", (file_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_tax_audit_entry(
    reference_no: str,
    vendor_name: str,
    bill_date: str,
    due_date: Optional[str] = None,
    subtotal: float = 0.0,
    tax_amount: float = 0.0,
    total_amount: float = 0.0,
    category: str = "General Expense",
    payment_status: str = "PAID",
    payment_method: str = "",
    bigcapital_bill_id: Optional[int] = None,
    bigcapital_payment_id: Optional[int] = None,
    proof_status: str = "VERIFIED_RECEIPT",
    proof_path: str = "",
    proof_sha256: str = "",
    gdrive_file_id: str = "",
    gdrive_folder_id: str = "1x3OD-FQAHWMyQnXEGal6WLj8-cHKFtYo",
    source_type: str = "email",
    source_id: str = "",
    audit_notes: str = "",
) -> int:
    """Upserts a canonical expense/audit record into tax_audit_ledger."""
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tax_audit_ledger (
            reference_no, vendor_name, bill_date, due_date, subtotal, tax_amount,
            total_amount, category, payment_status, payment_method,
            bigcapital_bill_id, bigcapital_payment_id, proof_status, proof_path,
            proof_sha256, gdrive_file_id, gdrive_folder_id, source_type,
            source_id, audit_notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(reference_no) DO UPDATE SET
            vendor_name = excluded.vendor_name,
            bill_date = excluded.bill_date,
            due_date = excluded.due_date,
            subtotal = excluded.subtotal,
            tax_amount = excluded.tax_amount,
            total_amount = excluded.total_amount,
            category = excluded.category,
            payment_status = excluded.payment_status,
            payment_method = excluded.payment_method,
            bigcapital_bill_id = COALESCE(excluded.bigcapital_bill_id, tax_audit_ledger.bigcapital_bill_id),
            bigcapital_payment_id = COALESCE(excluded.bigcapital_payment_id, tax_audit_ledger.bigcapital_payment_id),
            proof_status = excluded.proof_status,
            proof_path = CASE WHEN excluded.proof_path != '' THEN excluded.proof_path ELSE tax_audit_ledger.proof_path END,
            proof_sha256 = CASE WHEN excluded.proof_sha256 != '' THEN excluded.proof_sha256 ELSE tax_audit_ledger.proof_sha256 END,
            gdrive_file_id = CASE WHEN excluded.gdrive_file_id != '' THEN excluded.gdrive_file_id ELSE tax_audit_ledger.gdrive_file_id END,
            gdrive_folder_id = excluded.gdrive_folder_id,
            source_type = excluded.source_type,
            source_id = excluded.source_id,
            audit_notes = excluded.audit_notes,
            updated_at = excluded.updated_at
        """,
        (
            reference_no,
            vendor_name,
            bill_date,
            due_date or bill_date,
            round(float(subtotal or 0.0), 2),
            round(float(tax_amount or 0.0), 2),
            round(float(total_amount or 0.0), 2),
            category,
            payment_status,
            payment_method,
            bigcapital_bill_id,
            bigcapital_payment_id,
            proof_status,
            proof_path,
            proof_sha256,
            gdrive_file_id,
            gdrive_folder_id,
            source_type,
            source_id,
            audit_notes,
            now,
        ),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_tax_audit_entry(reference_no: str) -> Optional[Dict[str, Any]]:
    """Fetches a tax_audit_ledger entry by canonical reference_no."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM tax_audit_ledger WHERE reference_no = ?", (reference_no,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def list_tax_audit_ledger(limit: int = 200) -> List[Dict[str, Any]]:
    """Lists all entries in tax_audit_ledger ordered by bill_date DESC."""
    init_store()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM tax_audit_ledger ORDER BY bill_date DESC, id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_tax_audit_report(
    auditor_name: str,
    audit_status: str,
    total_bills_checked: int,
    verified_count: int,
    flagged_count: int,
    duplicates_found: int,
    unsettled_paid_found: int,
    findings: List[Dict[str, Any]],
    summary: str,
) -> int:
    """Logs an independent CPA/TaxMan audit report from Victor Sterling."""
    init_store()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tax_audit_reports (
            auditor_name, audit_status, total_bills_checked, verified_count,
            flagged_count, duplicates_found, unsettled_paid_found,
            findings_json, summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            auditor_name,
            audit_status,
            total_bills_checked,
            verified_count,
            flagged_count,
            duplicates_found,
            unsettled_paid_found,
            json.dumps(findings),
            summary,
            now,
        ),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id






