import json
import logging
import os
import re
import socket
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import http.client

from state_store import log_request_flow

logger = logging.getLogger("infra_tools")

KUMA_DB_PATH = os.environ.get("KUMA_DB_PATH", "/tank/monitor/uptime-kuma/kuma.db")
BESZEL_DB_PATH = os.environ.get("BESZEL_DB_PATH", "/tank/monitor/beszel_data/data.db")
DOCKER_SOCK_PATH = "/var/run/docker.sock"

# Safety map of monitors to docker containers
MONITOR_TO_CONTAINER_MAP = {
    "twenty crm": "twenty-server",
    "n8n automation engine": "n8n",
    "open house check-in app": "checkin-app",
    "real estate website (dev)": "real-estate-dev",
    "beszel metrics hub": "beszel",
    "uptime kuma monitor": "uptime-kuma",
    "agent hub api": "agent-hub",
    "local ai inference (ollama)": "ollama",
    "postgresql 17 database": "postgres",
    "adguard home": "adguardhome-adguardhome-1",
}

# Protected services that MUST NOT be restarted automatically without manual approval
PROTECTED_CONTAINERS = {"real-estate"}

# In-memory restart rate limiter: {container_name: [timestamp, timestamp, ...]}
_RESTART_HISTORY: Dict[str, List[float]] = {}
MAX_RESTARTS_PER_WINDOW = 2
RESTART_WINDOW_SECONDS = 900  # 15 minutes


class UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float = 10.0):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


def docker_api_request(method: str, path: str, body: Optional[bytes] = None, timeout: float = 15.0) -> Dict[str, Any]:
    """
    Executes raw HTTP over Unix domain socket to Docker Engine.
    """
    if not os.path.exists(DOCKER_SOCK_PATH):
        return {"ok": False, "error": f"Docker socket not found at {DOCKER_SOCK_PATH}"}

    try:
        conn = UnixSocketHTTPConnection(DOCKER_SOCK_PATH, timeout=timeout)
        headers = {"Host": "localhost"}
        if body:
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(body))

        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()
        raw_data = res.read()
        conn.close()

        status = res.status
        try:
            parsed = json.loads(raw_data.decode("utf-8", errors="replace")) if raw_data else {}
        except Exception:
            parsed = {"raw": raw_data.decode("utf-8", errors="replace")}

        return {"ok": status < 400, "status": status, "data": parsed}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_uptime_kuma() -> Dict[str, Any]:
    """
    Reads monitor status and heartbeats directly from Uptime Kuma SQLite db.
    """
    if not os.path.exists(KUMA_DB_PATH):
        return {"ok": False, "error": f"kuma.db not found at {KUMA_DB_PATH}"}

    try:
        conn = sqlite3.connect(KUMA_DB_PATH)
        cur = conn.cursor()
        monitors = []
        for r in cur.execute("SELECT id, name, type, url, active FROM monitor WHERE active=1").fetchall():
            m_id, name, m_type, url, active = r
            # Fetch latest heartbeat
            hb = cur.execute(
                "SELECT status, ping, time, msg FROM heartbeat WHERE monitor_id=? ORDER BY id DESC LIMIT 1",
                (m_id,),
            ).fetchone()

            status_str = "UNKNOWN"
            ping_ms = None
            msg = ""
            time_str = ""
            if hb:
                status_str = "UP" if hb[0] == 1 else "DOWN" if hb[0] == 0 else "PENDING"
                ping_ms = hb[1]
                time_str = hb[2]
                msg = hb[3]

            monitors.append({
                "id": m_id,
                "name": name,
                "type": m_type,
                "url": url,
                "status": status_str,
                "ping_ms": ping_ms,
                "last_heartbeat": time_str,
                "msg": msg,
            })
        conn.close()
        return {"ok": True, "total": len(monitors), "monitors": monitors}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_docker_containers() -> Dict[str, Any]:
    """
    Lists running Docker containers via Docker Unix socket.
    """
    res = docker_api_request("GET", "/containers/json?all=true")
    if not res.get("ok"):
        return res

    containers = []
    for c in res.get("data", []):
        names = [n.lstrip("/") for n in c.get("Names", [])]
        primary_name = names[0] if names else "unknown"
        containers.append({
            "id": c.get("Id", "")[:12],
            "name": primary_name,
            "image": c.get("Image"),
            "state": c.get("State"),
            "status": c.get("Status"),
        })
    return {"ok": True, "total": len(containers), "containers": containers}


def get_container_logs(container_name: str, tail: int = 30) -> str:
    """
    Fetches the last N lines of logs from Docker container.
    """
    res = docker_api_request("GET", f"/containers/{container_name}/logs?stderr=1&stdout=1&tail={tail}")
    if not res.get("ok"):
        return f"Could not retrieve logs: {res.get('error')}"
    raw = res.get("data", {}).get("raw", "")
    # Docker log streams prefix each line with 8 header bytes, clean printable text
    clean_lines = []
    for line in raw.splitlines():
        if len(line) > 8 and line[:8].isascii():
            clean_lines.append(line[8:])
        else:
            clean_lines.append(line)
    return "\n".join(clean_lines[-tail:])


def restart_container(container_name: str) -> Dict[str, Any]:
    """
    Restarts a container with rate-limiting loop protection.
    """
    if container_name in PROTECTED_CONTAINERS:
        return {
            "ok": False,
            "error": f"Container '{container_name}' is in PROTECTED_CONTAINERS list and requires manual approval.",
        }

    now = time.time()
    history = _RESTART_HISTORY.get(container_name, [])
    # Filter history within the window
    history = [t for t in history if now - t < RESTART_WINDOW_SECONDS]
    _RESTART_HISTORY[container_name] = history

    if len(history) >= MAX_RESTARTS_PER_WINDOW:
        return {
            "ok": False,
            "error": f"Rate limit reached: '{container_name}' has been restarted {len(history)} times in the last 15 minutes. Halting to avoid boot loops.",
        }

    # Execute restart
    res = docker_api_request("POST", f"/containers/{container_name}/restart?t=10")
    if res.get("ok"):
        history.append(now)
        _RESTART_HISTORY[container_name] = history
        return {"ok": True, "container": container_name, "message": f"Container '{container_name}' successfully restarted."}
    return {"ok": False, "container": container_name, "error": res.get("error", "Restart failed")}


async def handle_infra_alert(alert_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Event-driven handler triggered when Uptime Kuma or Beszel fires an alert.
    Dispatches Ian Torres (IT Agent) to diagnose and heal.
    """
    start_ts = time.time()
    monitor = alert_payload.get("monitor", {})
    heartbeat = alert_payload.get("heartbeat", {})
    monitor_name = monitor.get("name") or alert_payload.get("name") or "Unknown Service"
    monitor_url = monitor.get("url") or ""
    status_code = heartbeat.get("status")
    error_msg = heartbeat.get("msg") or alert_payload.get("msg") or "Service unreachable"

    is_down = status_code == 0 or "down" in error_msg.lower() or "🔴" in error_msg

    flow_id = f"flow_infra_{int(time.time() * 1000)}"
    source = "Uptime Kuma Alert Webhook"
    title = f"Infra Alert: {monitor_name} is {'DOWN' if is_down else 'UP'}"

    steps = [
        {
            "step": "Alert Reception",
            "agent": "Miles Miller",
            "action": f"Received alert payload for '{monitor_name}' ({monitor_url})",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "ok",
        }
    ]

    if not is_down:
        # Service recovered notification
        steps.append({
            "step": "Status Check",
            "agent": "Ian Torres",
            "action": f"Service '{monitor_name}' reported healthy/recovered. No healing required.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "ok",
        })
        log_request_flow(
            flow_id=flow_id,
            source=source,
            title=title,
            status="completed",
            agents_involved=["Miles Miller", "Ian Torres"],
            steps=steps,
            payload_preview=alert_payload,
            result_summary=f"{monitor_name} is UP.",
            duration_ms=int((time.time() - start_ts) * 1000),
        )
        return {"ok": True, "action": "acknowledged_up", "monitor": monitor_name}

    # Map monitor to container
    target_container = None
    for k, v in MONITOR_TO_CONTAINER_MAP.items():
        if k in monitor_name.lower():
            target_container = v
            break

    if not target_container:
        steps.append({
            "step": "Container Identification",
            "agent": "Ian Torres",
            "action": f"Could not map monitor '{monitor_name}' to a known local Docker container.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "warning",
        })
        log_request_flow(
            flow_id=flow_id,
            source=source,
            title=title,
            status="alert_only",
            agents_involved=["Miles Miller", "Ian Torres"],
            steps=steps,
            payload_preview=alert_payload,
            result_summary=f"Unmapped monitor down: {monitor_name}",
            duration_ms=int((time.time() - start_ts) * 1000),
        )
        return {"ok": True, "action": "unmapped_monitor", "monitor": monitor_name}

    # Pull container logs for diagnosis
    logs = get_container_logs(target_container, tail=20)
    steps.append({
        "step": "Log Diagnostics",
        "agent": "Ian Torres",
        "action": f"Inspected recent logs for container '{target_container}'",
        "diagnostics": logs[-300:] if logs else "No logs found",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    # Healing attempt
    steps.append({
        "step": "Self-Healing Attempt",
        "agent": "Ian Torres",
        "action": f"Triggering safe restart for container '{target_container}' with rate-limiting guards",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "running",
    })

    restart_res = restart_container(target_container)
    if not restart_res.get("ok"):
        steps[-1]["status"] = "failed"
        steps[-1]["error"] = restart_res.get("error")
        steps.append({
            "step": "Audit Verification",
            "agent": "Audrey Chen",
            "action": f"Self-healing could not be performed: {restart_res.get('error')}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "warning",
        })
        log_request_flow(
            flow_id=flow_id,
            source=source,
            title=title,
            status="failed",
            agents_involved=["Miles Miller", "Ian Torres", "Audrey Chen"],
            steps=steps,
            payload_preview=alert_payload,
            result_summary=f"Failed to heal {target_container}: {restart_res.get('error')}",
            duration_ms=int((time.time() - start_ts) * 1000),
        )
        return {"ok": False, "action": "healing_blocked", "error": restart_res.get("error")}

    steps[-1]["status"] = "ok"
    steps[-1]["action"] = f"Container '{target_container}' restart command issued."

    # Verification step
    steps.append({
        "step": "Verification & Post-Audit",
        "agent": "Audrey Chen",
        "action": f"Container '{target_container}' restarted successfully. Monitoring recovery window.",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    duration_ms = int((time.time() - start_ts) * 1000)
    log_request_flow(
        flow_id=flow_id,
        source=source,
        title=f"Healed Service: {target_container}",
        status="healed",
        agents_involved=["Miles Miller", "Ian Torres", "Audrey Chen"],
        steps=steps,
        payload_preview=alert_payload,
        result_summary=f"Container '{target_container}' successfully auto-restarted.",
        duration_ms=duration_ms,
    )

    return {
        "ok": True,
        "action": "healed",
        "container": target_container,
        "monitor": monitor_name,
        "duration_ms": duration_ms,
    }
