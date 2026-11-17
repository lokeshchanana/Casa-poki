"""
Hannah Reed — Home Assistant Guardian & Smart Home Engineer (Antigravity-Powered)
Casa-poki Intelligent Agent Hub

Monitors Home Assistant (192.168.1.251:8123 / https://ha.lokeshchanana.com),
companion smart-home containers (music-assistant, habridge, adguard),
and automatically diagnoses & safely remediates issues using Antigravity.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from typing import Any, Dict, List, Optional

import httpx

from infra_tools import docker_api_request
from state_store import init_store, log_ha_health_event, log_request_flow

logger = logging.getLogger("ha_guardian")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

HA_URL = os.environ.get("HA_URL", "http://192.168.1.251:8123").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN", "").strip("\"'")
AGY_PATH = os.environ.get("AGY_PATH", "/usr/local/bin/agy")

# Companion smart-home containers hosted on Casa-poki
COMPANION_CONTAINERS = ["music-assistant", "habridge", "adguardhome-adguardhome-1"]

# Controllable / critical entity domains worth monitoring & refreshing
CRITICAL_DOMAINS = {
    "light",
    "switch",
    "climate",
    "lock",
    "cover",
    "fan",
    "media_player",
    "camera",
    "vacuum",
    "valve",
    "siren",
    "automation",
}

# Benign transient/mobile patterns excluded from critical unavailable alerts
BENIGN_PATTERNS = (
    "_identify_",
    "pixel_",
    "motorola_",
    "favorite_current_song",
)

# Rate limiting for auto-remediation
_HEAL_HISTORY: List[float] = []
MAX_HEALS_PER_WINDOW = 2
HEAL_WINDOW_SECONDS = 900  # 15 minutes


class HomeAssistantClient:
    """Async REST API client for Home Assistant."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or HA_URL).rstrip("/")
        self.token = (token or HA_TOKEN).strip("\"'")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 12.0,
    ) -> Dict[str, Any]:
        if not self.token:
            return {"ok": False, "status": 401, "error": "HA_TOKEN is not configured in environment."}
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    method=method,
                    url=url,
                    json=payload,
                    headers=self._headers(),
                )
                text = resp.text
                try:
                    data = resp.json() if text else {}
                except Exception:
                    data = {"raw": text}

                if resp.status_code >= 400:
                    return {
                        "ok": False,
                        "status": resp.status_code,
                        "error": data.get("message") or text or f"HTTP {resp.status_code}",
                        "data": data,
                    }
                return {"ok": True, "status": resp.status_code, "data": data}
        except Exception as e:
            logger.error(f"Home Assistant request failed [{method} {url}]: {e}")
            return {"ok": False, "status": 503, "error": str(e)}

    async def get_api_status(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/")

    async def get_config(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/config")

    async def get_states(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/states", timeout=15.0)

    async def check_config(self) -> Dict[str, Any]:
        return await self._request("POST", "/api/config/core/check_config", timeout=20.0)

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/services/{domain}/{service}",
            payload=service_data or {},
            timeout=20.0,
        )


ha_client = HomeAssistantClient()


def _check_companion_containers() -> List[Dict[str, Any]]:
    """Checks Docker status of smart-home companion containers on Casa-poki."""
    res = docker_api_request("GET", "/containers/json?all=true")
    if not res.get("ok"):
        return [{"name": "docker_socket", "status": "error", "error": res.get("error")}]

    containers_raw = res.get("data", [])
    by_name = {}
    for c in containers_raw:
        for n in c.get("Names", []):
            by_name[n.lstrip("/")] = c

    results = []
    for cname in COMPANION_CONTAINERS:
        info = by_name.get(cname)
        if not info:
            results.append({"name": cname, "present": False, "state": "missing", "healthy": True})
            continue
        state = info.get("State", "unknown")
        status_txt = info.get("Status", "")
        healthy = state == "running" and "unhealthy" not in status_txt.lower()
        results.append({
            "name": cname,
            "present": True,
            "state": state,
            "status": status_txt,
            "healthy": healthy,
        })
    return results


async def check_ha_health(persist_log: bool = False) -> Dict[str, Any]:
    """
    Performs a comprehensive health audit of Home Assistant and companion containers.
    """
    issues: List[Dict[str, Any]] = []

    api_res = await ha_client.get_api_status()
    if not api_res.get("ok"):
        issues.append({
            "severity": "critical",
            "type": "api_unreachable",
            "message": f"Home Assistant API unreachable at {ha_client.base_url}: {api_res.get('error')}",
        })
        companions = _check_companion_containers()
        result = {
            "ok": False,
            "status": "CRITICAL",
            "ha_url": ha_client.base_url,
            "api_reachable": False,
            "issues": issues,
            "companion_containers": companions,
            "error": api_res.get("error"),
        }
        if persist_log:
            log_ha_health_event(status="CRITICAL", issues=issues, summary=issues[0]["message"])
        return result

    cfg_res = await ha_client.get_config()
    cfg = cfg_res.get("data", {}) if cfg_res.get("ok") else {}
    ha_version = cfg.get("version", "unknown")
    core_state = cfg.get("state", "unknown")

    if core_state != "RUNNING":
        issues.append({
            "severity": "critical",
            "type": "core_not_running",
            "message": f"Home Assistant core state is '{core_state}' (expected RUNNING).",
        })

    # Validate configuration.yaml
    chk_res = await ha_client.check_config()
    chk_data = chk_res.get("data", {}) if chk_res.get("ok") else {}
    config_valid = chk_data.get("result") == "valid"
    if chk_res.get("ok") and not config_valid:
        issues.append({
            "severity": "critical",
            "type": "invalid_config",
            "message": f"configuration.yaml validation failed: {chk_data.get('errors')}",
        })

    # Inspect states
    states_res = await ha_client.get_states()
    states = states_res.get("data", []) if states_res.get("ok") else []

    persistent_alerts: List[Dict[str, str]] = []
    broken_automations: List[str] = []
    critical_unavailable: List[str] = []
    benign_unavailable_count = 0

    for s in states:
        eid = s.get("entity_id", "")
        state_val = s.get("state", "")
        attrs = s.get("attributes", {}) or {}

        # Ignore our own guardian notifications
        if eid.startswith("persistent_notification."):
            if "ha_guardian" in eid:
                continue
            persistent_alerts.append({
                "entity_id": eid,
                "title": str(attrs.get("title") or "Alert"),
                "message": str(attrs.get("message") or "")[:300],
            })
            continue

        if state_val == "unavailable":
            domain = eid.split(".")[0] if "." in eid else ""
            if domain == "automation":
                broken_automations.append(eid)
            elif domain in CRITICAL_DOMAINS and not any(p in eid for p in BENIGN_PATTERNS):
                critical_unavailable.append(eid)
            else:
                benign_unavailable_count += 1

    if persistent_alerts:
        issues.append({
            "severity": "warning",
            "type": "persistent_notifications",
            "count": len(persistent_alerts),
            "alerts": persistent_alerts,
            "message": f"{len(persistent_alerts)} active Home Assistant persistent notification(s).",
        })

    if broken_automations:
        issues.append({
            "severity": "warning",
            "type": "broken_automations",
            "entities": broken_automations,
            "message": f"{len(broken_automations)} automation(s) are unavailable.",
        })

    if critical_unavailable:
        issues.append({
            "severity": "warning",
            "type": "critical_unavailable_entities",
            "count": len(critical_unavailable),
            "entities": critical_unavailable[:30],
            "message": f"{len(critical_unavailable)} critical/controllable entity(ies) are unavailable.",
        })

    # Check companion Docker containers on Casa-poki
    companions = _check_companion_containers()
    for c in companions:
        if c.get("present") and not c.get("healthy"):
            issues.append({
                "severity": "critical",
                "type": "companion_container_unhealthy",
                "container": c["name"],
                "message": f"Companion container '{c['name']}' is {c.get('state')} ({c.get('status')}).",
            })

    overall_status = "HEALTHY"
    if any(i["severity"] == "critical" for i in issues):
        overall_status = "CRITICAL"
    elif issues:
        overall_status = "DEGRADED"

    summary = (
        f"HA {ha_version} ({core_state}): {len(states)} entities, "
        f"{len(critical_unavailable)} critical unavailable, "
        f"{len(broken_automations)} broken automations, "
        f"{len(persistent_alerts)} alerts."
    )

    if persist_log:
        log_ha_health_event(
            status=overall_status,
            ha_version=ha_version,
            total_entities=len(states),
            critical_unavailable=len(critical_unavailable),
            broken_automations=len(broken_automations),
            persistent_alerts=len(persistent_alerts),
            issues=issues,
            summary=summary,
        )

    return {
        "ok": True,
        "status": overall_status,
        "ha_url": ha_client.base_url,
        "api_reachable": True,
        "ha_version": ha_version,
        "core_state": core_state,
        "config_valid": config_valid,
        "total_entities": len(states),
        "critical_unavailable_count": len(critical_unavailable),
        "critical_unavailable": critical_unavailable[:30],
        "benign_unavailable_count": benign_unavailable_count,
        "broken_automations": broken_automations,
        "persistent_alerts": persistent_alerts,
        "companion_containers": companions,
        "issues": issues,
        "summary": summary,
    }


async def heal_ha_issues(
    allow_restart: bool = False,
    target_entities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Runs safe automated remediation on detected Home Assistant issues.
    Rate-limited to MAX_HEALS_PER_WINDOW per HEAL_WINDOW_SECONDS.
    """
    now = time.time()
    recent = [ts for ts in _HEAL_HISTORY if now - ts < HEAL_WINDOW_SECONDS]
    _HEAL_HISTORY[:] = recent

    if len(recent) >= MAX_HEALS_PER_WINDOW:
        return {
            "ok": False,
            "rate_limited": True,
            "error": f"Auto-heal rate limit reached ({MAX_HEALS_PER_WINDOW} actions in 15m). Manual review advised.",
        }

    audit = await check_ha_health(persist_log=False)
    actions_taken: List[Dict[str, Any]] = []

    if not audit.get("api_reachable"):
        # Check companion containers first, then report HA host unreachable
        for c in audit.get("companion_containers", []):
            if c.get("present") and not c.get("healthy"):
                r = docker_api_request("POST", f"/containers/{c['name']}/restart")
                actions_taken.append({"action": "restart_container", "target": c["name"], "ok": r.get("ok")})
        log_ha_health_event(status="CRITICAL", issues=audit.get("issues"), actions_taken=actions_taken, summary="HA API unreachable")
        return {
            "ok": False,
            "status": "CRITICAL",
            "audit": audit,
            "actions_taken": actions_taken,
            "message": "Home Assistant API at 192.168.1.251:8123 is unreachable; restarted any unhealthy companion containers.",
        }

    # 1. Restart unhealthy Casa-poki companion containers
    for c in audit.get("companion_containers", []):
        if c.get("present") and not c.get("healthy"):
            r = docker_api_request("POST", f"/containers/{c['name']}/restart")
            actions_taken.append({
                "action": "restart_companion_container",
                "target": c["name"],
                "ok": r.get("ok"),
            })

    # 2. Reload automations if any automation.* is unavailable
    if audit.get("broken_automations"):
        r = await ha_client.call_service("automation", "reload")
        actions_taken.append({
            "action": "automation.reload",
            "targets": audit["broken_automations"],
            "ok": r.get("ok"),
        })

    # 3. Force state refresh on unavailable critical entities (or explicit target_entities)
    refresh_targets = target_entities or audit.get("critical_unavailable", [])
    if refresh_targets:
        batch = refresh_targets[:25]
        r = await ha_client.call_service("homeassistant", "update_entity", {"entity_id": batch})
        actions_taken.append({
            "action": "homeassistant.update_entity",
            "count": len(batch),
            "entities": batch[:10],
            "ok": r.get("ok"),
        })

    # 4. Reload integrations if persistent alerts mention setup/integration failure and config is valid
    if audit.get("persistent_alerts") and audit.get("config_valid"):
        r = await ha_client.call_service("homeassistant", "reload_all")
        actions_taken.append({"action": "homeassistant.reload_all", "ok": r.get("ok")})

    # 5. Validated Core Restart only if explicitly requested or core_state != RUNNING, AND config is valid
    if (allow_restart or audit.get("core_state") != "RUNNING") and audit.get("config_valid"):
        r = await ha_client.call_service("homeassistant", "restart")
        actions_taken.append({"action": "homeassistant.restart", "ok": r.get("ok")})

    if actions_taken:
        _HEAL_HISTORY.append(now)
        # Re-verify briefly after entity updates if no full restart was triggered
        if not any(a["action"] == "homeassistant.restart" for a in actions_taken):
            await asyncio.sleep(2)
        post_audit = await check_ha_health(persist_log=False)

        # Post summary notification inside Home Assistant
        summary_lines = [f"- `{a['action']}` ({'OK' if a.get('ok') else 'FAILED'})" for a in actions_taken]
        await ha_client.call_service(
            "persistent_notification",
            "create",
            {
                "notification_id": "ha_guardian_report",
                "title": "Hannah Reed (HA Guardian) Auto-Remediation Report",
                "message": (
                    f"Detected status `{audit['status']}` and executed:\n"
                    + "\n".join(summary_lines)
                    + f"\n\nPost-fix status: `{post_audit.get('status')}` "
                    f"({post_audit.get('critical_unavailable_count', 0)} critical unavailable)."
                ),
            },
        )
    else:
        post_audit = audit

    summary = (
        f"Audit status: {audit['status']}. Actions executed: {len(actions_taken)}. "
        f"Post-check status: {post_audit.get('status')}."
    )
    log_ha_health_event(
        status=post_audit.get("status", audit["status"]),
        ha_version=audit.get("ha_version"),
        total_entities=audit.get("total_entities", 0),
        critical_unavailable=post_audit.get("critical_unavailable_count", 0),
        broken_automations=len(post_audit.get("broken_automations", [])),
        persistent_alerts=len(post_audit.get("persistent_alerts", [])),
        issues=audit.get("issues", []),
        actions_taken=actions_taken,
        summary=summary,
    )
    log_request_flow(
        flow_id=f"ha_heal_{int(now)}",
        source="ha_guardian",
        title="Hannah Reed (HA Guardian) Auto-Remediation",
        status="SUCCESS",
        agents_involved=["Hannah Reed"],
        steps=actions_taken,
        result_summary=summary,
    )

    return {
        "ok": True,
        "pre_status": audit["status"],
        "post_status": post_audit.get("status"),
        "actions_taken": actions_taken,
        "audit": post_audit,
        "summary": summary,
    }


def _invoke_antigravity_diagnosis(audit: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invokes Antigravity CLI (/usr/local/bin/agy) as Hannah Reed to reason over
    Home Assistant issues and decide the safest remediation plan.
    """
    if not os.path.exists(AGY_PATH):
        return {"used_antigravity": False, "reason": "agy binary not found", "action": "heal"}

    prompt = (
        "You are Hannah Reed, the Home Assistant Guardian Agent running on Antigravity.\n"
        "Review this live Home Assistant health snapshot and decide the safest remediation.\n"
        "Respond ONLY with valid JSON: "
        '{"should_heal": true/false, "allow_restart": false, "target_entities": [...], "reasoning": "..."}\n\n'
        f"HEALTH SNAPSHOT:\n{json.dumps(audit, default=str)[:4500]}"
    )

    try:
        proc = subprocess.run(
            [AGY_PATH, "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        raw = (proc.stdout or "").strip()
        if proc.returncode == 0 and raw:
            data = json.loads(raw)
            result_text = str(data.get("response") or data.get("result") or raw).strip()
            # Extract JSON object from result_text
            start = result_text.find("{")
            end = result_text.rfind("}")
            if start != -1 and end != -1:
                decision = json.loads(result_text[start : end + 1])
                decision["used_antigravity"] = True
                return decision
    except Exception as e:
        logger.warning(f"Antigravity diagnosis fallback triggered: {e}")

    return {"used_antigravity": False, "should_heal": True, "allow_restart": False, "reasoning": "Fallback deterministic heal"}


async def run_autonomous_monitor(auto_fix: bool = True) -> Dict[str, Any]:
    """
    Entry point for the 5-minute systemd timer.
    Checks HA health; if issues are detected and auto_fix=True, invokes Hannah Reed on
    Antigravity to diagnose and execute safe remediation.
    """
    init_store()
    audit = await check_ha_health(persist_log=False)

    if audit.get("status") == "HEALTHY":
        log_ha_health_event(
            status="HEALTHY",
            ha_version=audit.get("ha_version"),
            total_entities=audit.get("total_entities", 0),
            summary=audit.get("summary"),
        )
        return {"ok": True, "status": "HEALTHY", "summary": audit.get("summary"), "actions_taken": []}

    if not auto_fix:
        log_ha_health_event(
            status=audit["status"],
            ha_version=audit.get("ha_version"),
            total_entities=audit.get("total_entities", 0),
            critical_unavailable=audit.get("critical_unavailable_count", 0),
            broken_automations=len(audit.get("broken_automations", [])),
            persistent_alerts=len(audit.get("persistent_alerts", [])),
            issues=audit.get("issues", []),
            summary=audit.get("summary"),
        )
        return audit

    decision = _invoke_antigravity_diagnosis(audit)
    logger.info(f"Hannah Reed (Antigravity) diagnosis decision: {decision}")

    if decision.get("should_heal", True):
        heal_res = await heal_ha_issues(
            allow_restart=bool(decision.get("allow_restart", False)),
            target_entities=decision.get("target_entities") or None,
        )
        heal_res["antigravity_decision"] = decision
        return heal_res

    return {"ok": True, "status": audit["status"], "audit": audit, "antigravity_decision": decision, "actions_taken": []}


if __name__ == "__main__":
    import sys

    auto_fix = "--auto-fix" in sys.argv
    res = asyncio.run(run_autonomous_monitor(auto_fix=auto_fix))
    print(json.dumps(res, indent=2, default=str))
