import asyncio
import json
import logging
import os
import re
import shutil
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import httpx

from state_store import log_token_usage

logger = logging.getLogger("agent_llm_gateway")

AGENT_BACKEND = os.environ.get("AGENT_BACKEND", "antigravity").lower()
AGY_PATH = os.environ.get("AGY_PATH", "/usr/local/bin/agy")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://192.168.1.240:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "crm-qwen:3b")

# Empty sandboxed CWD so agy does not load 24k tokens of IDE workspace context on every chat turn
AGY_SANDBOX_CWD = "/tmp/agy_agent_empty"
os.makedirs(AGY_SANDBOX_CWD, exist_ok=True)

MODEL_TIERS = {
    "fast": os.environ.get("AGY_MODEL_FAST", "gemini-3.8-flash-low"),
    "balanced": os.environ.get("AGY_MODEL_BALANCED", "gemini-4-hydrogen-medium"),
    "deep": os.environ.get("AGY_MODEL_DEEP", "gemini-4-carbon-high"),
}


def select_model_tier(
    task_type: str = "manager",
    agent_name: str = "manager",
    user_message: str = "",
) -> str:
    """
    Adaptive 3-tier model router:
    - fast: compaction, auditor verification, simple lookups
    - balanced: standard Manager routing and specialist execution
    - deep: CPA tax audits, CMAs, deep research, multi-agent synthesis
    """
    if task_type in ("compact", "audit", "triage_fast"):
        return MODEL_TIERS["fast"]
    if agent_name in ("tax_auditor", "cma") or task_type == "deep":
        return MODEL_TIERS["deep"]
    u_low = (user_message or "").lower()
    if any(k in u_low for k in ("deep search", "deep research", "tax audit", "cma", "valuation", "comprehensive")):
        return MODEL_TIERS["deep"]
    return MODEL_TIERS["balanced"]


def _normalize_tool_calls(data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("tool_calls"), list):
        out = []
        for tc in data["tool_calls"]:
            if isinstance(tc, dict) and tc.get("name"):
                out.append({"function": {"name": tc.get("name"), "arguments": tc.get("arguments", {})}})
        return out if out else None
    if isinstance(data.get("tool_call"), dict) and data["tool_call"].get("name"):
        tc = data["tool_call"]
        return [{"function": {"name": tc.get("name"), "arguments": tc.get("arguments", {})}}]
    return None


def parse_antigravity_output(raw_text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Parses output from Antigravity CLI, detecting single {"tool_call": ...}
    or parallel {"tool_calls": [...]} JSON blocks, or returning natural markdown.
    """
    text = (raw_text or "").strip()
    if not text:
        return "", []

    # 1. Markdown ```json ... ``` blocks
    for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            norm = _normalize_tool_calls(data)
            if norm:
                leading = text[: match.start()].strip()
                return leading, norm
        except Exception:
            pass

    # 2. Balanced brace scan for {"tool_calls" or {"tool_call"
    for marker in ('{"tool_calls"', '{ "tool_calls"', '{"tool_call"', '{ "tool_call"'):
        idx = text.find(marker)
        if idx != -1:
            depth = 0
            end_idx = -1
            in_str = False
            escape = False
            for i in range(idx, len(text)):
                ch = text[i]
                if escape:
                    escape = False
                    continue
                if ch == "\\" and in_str:
                    escape = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if not in_str:
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            end_idx = i + 1
                            break
            if end_idx != -1:
                try:
                    data = json.loads(text[idx:end_idx])
                    norm = _normalize_tool_calls(data)
                    if norm:
                        leading = text[:idx].strip()
                        return leading, norm
                except Exception:
                    pass

    # 3. Pure JSON object
    try:
        data = json.loads(text)
        norm = _normalize_tool_calls(data)
        if norm:
            return "", norm
    except Exception:
        pass

    return text, []


def _format_agy_prompt(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]]) -> str:
    system_parts = []
    conversation_parts = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            conversation_parts.append(f"User: {content}")
        elif role == "assistant":
            if msg.get("tool_calls"):
                conversation_parts.append(f"Assistant Tool Call: {json.dumps(msg['tool_calls'])}")
            if content:
                conversation_parts.append(f"Assistant: {content}")
        elif role == "tool":
            conversation_parts.append(f"Tool Result: {content}")

    prompt_builder = []
    if system_parts:
        prompt_builder.append("### SYSTEM INSTRUCTIONS & PERSONA ###\n" + "\n\n".join(system_parts))

    if tools:
        tool_desc = json.dumps(tools, separators=(",", ":"))
        prompt_builder.append(
            f"### AVAILABLE TOOLS ###\n{tool_desc}\n\n"
            "### TOOL CALL INSTRUCTIONS ###\n"
            "If you need to execute one tool, respond ONLY with JSON:\n"
            '{"tool_call": {"name": "<tool_name>", "arguments": { ... }}}\n'
            "If multiple independent tools can run in parallel, respond ONLY with JSON:\n"
            '{"tool_calls": [{"name": "<tool_1>", "arguments": {...}}, {"name": "<tool_2>", "arguments": {...}}]}\n'
            "If no tool call is needed, provide your natural markdown answer directly."
        )

    if conversation_parts:
        prompt_builder.append("### CONVERSATION TURNS ###\n" + "\n\n".join(conversation_parts))

    return "\n\n".join(prompt_builder)


async def call_antigravity_cli(
    task_id: str,
    agent_name: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    agy_bin: str = "/usr/local/bin/agy",
    max_tokens: int = 2000,
    temperature: float = 0.1,
    model_name: Optional[str] = None,
    json_schema: Optional[str] = None,
    on_token_delta: Optional[Callable[[str], Awaitable[None]]] = None,
    on_thinking_delta: Optional[Callable[[str], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """
    Executes prompt against native Antigravity CLI runtime (agy) using stream-json
    for real-time token/thinking streaming and dynamic model tiering.
    """
    start_ts = time.time()
    full_prompt = _format_agy_prompt(messages, tools)
    chosen_model = model_name or MODEL_TIERS["balanced"]

    cmd = [
        agy_bin,
        "-p", full_prompt,
        "--output-format", "stream-json",
        "--model", chosen_model,
        "--disable-slash-commands",
        "--dangerously-skip-permissions",
    ]
    if json_schema:
        cmd.extend(["--json-schema", json_schema])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=AGY_SANDBOX_CWD,
        )

        accumulated_raw = []
        final_response = ""
        usage: Dict[str, Any] = {}
        duration_sec = 0.0
        suppress_stream = False

        assert proc.stdout is not None
        while True:
            raw_line = await proc.stdout.readline()
            if not raw_line:
                break
            line_str = raw_line.decode("utf-8", errors="replace").strip()
            if not line_str:
                continue
            try:
                evt = json.loads(line_str)
            except Exception:
                continue

            etype = evt.get("event")
            if etype == "step_update":
                su = evt.get("step_update") or {}
                t_delta = su.get("text_delta") or ""
                th_delta = su.get("thinking_delta") or ""
                if th_delta and on_thinking_delta:
                    await on_thinking_delta(th_delta)
                if t_delta:
                    accumulated_raw.append(t_delta)
                    joined = "".join(accumulated_raw).lstrip()
                    # Do not stream raw tool-call JSON blobs to user UI
                    if joined.startswith("{") or joined.startswith("```json"):
                        suppress_stream = True
                    if not suppress_stream and on_token_delta:
                        await on_token_delta(t_delta)
                if su.get("usage"):
                    usage = su["usage"]
                if su.get("duration_seconds"):
                    duration_sec = float(su["duration_seconds"])
            elif etype == "result":
                res = evt.get("result") or {}
                if res.get("response"):
                    final_response = res["response"]
                if res.get("usage"):
                    usage = res["usage"]
                if res.get("duration_seconds"):
                    duration_sec = float(res["duration_seconds"])

        stderr_bytes = await proc.stderr.read() if proc.stderr else b""
        await proc.wait()

        raw_resp = final_response or "".join(accumulated_raw)
        if proc.returncode != 0 and not raw_resp.strip():
            err_msg = stderr_bytes.decode("utf-8", errors="replace").strip() or "Empty output from Antigravity"
            raise RuntimeError(f"Antigravity CLI error: {err_msg}")

        duration_ms = int(duration_sec * 1000) if duration_sec > 0 else int((time.time() - start_ts) * 1000)
        prompt_tokens = int(usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("output_tokens") or 0)
        tok_per_sec = (completion_tokens / duration_sec) if duration_sec > 0 else 0.0

        content, tool_calls = parse_antigravity_output(raw_resp)
        metrics = log_token_usage(
            task_id=task_id,
            agent_name=agent_name,
            model=chosen_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tokens_per_sec=round(tok_per_sec, 2),
            duration_ms=duration_ms,
        )
        return {
            "content": content,
            "tool_calls": tool_calls,
            "metrics": metrics,
            "streamed_to_ui": not suppress_stream and not tool_calls,
        }
    except Exception as e:
        logger.error(f"Antigravity execution failed: {e}")
        if OLLAMA_BASE_URL:
            logger.warning("Falling back to Ollama engine...")
            return await call_ollama_chat(task_id, agent_name, messages, tools, max_tokens, temperature)
        duration_ms = int((time.time() - start_ts) * 1000)
        return {
            "content": f"Antigravity Error: {str(e)}",
            "tool_calls": [],
            "metrics": log_token_usage(task_id, agent_name, chosen_model, 0, 0, 0.0, duration_ms),
            "streamed_to_ui": False,
        }


async def call_ollama_chat(
    task_id: str,
    agent_name: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    max_tokens: int = 2000,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    start_ts = time.time()
    payload: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "24h",
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    if tools:
        payload["tools"] = tools

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        duration_ms = int((time.time() - start_ts) * 1000)
        return {
            "content": f"LLM Error: {str(e)}",
            "tool_calls": [],
            "metrics": log_token_usage(task_id, agent_name, DEFAULT_MODEL, 0, 0, 0.0, duration_ms),
            "streamed_to_ui": False,
        }

    duration_ms = int((time.time() - start_ts) * 1000)
    msg = data.get("message") or {}
    content = msg.get("content", "") or ""
    tool_calls = msg.get("tool_calls", []) or []
    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    completion_tokens = int(data.get("eval_count") or 0)
    eval_duration_ns = int(data.get("eval_duration") or 0)
    tok_per_sec = (completion_tokens / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0.0

    metrics = log_token_usage(
        task_id=task_id,
        agent_name=agent_name,
        model=DEFAULT_MODEL,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        tokens_per_sec=tok_per_sec,
        duration_ms=duration_ms,
    )
    return {"content": content, "tool_calls": tool_calls, "metrics": metrics, "streamed_to_ui": False}


async def call_llm_chat(
    task_id: str,
    agent_name: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    max_tokens: int = 2000,
    temperature: float = 0.1,
    model_tier: Optional[str] = None,
    json_schema: Optional[str] = None,
    on_token_delta: Optional[Callable[[str], Awaitable[None]]] = None,
    on_thinking_delta: Optional[Callable[[str], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    resolved_agy = None
    for candidate in [AGY_PATH, "/usr/local/bin/agy", "/home/lokesh/.local/bin/agy", shutil.which("agy")]:
        if candidate and os.path.exists(candidate):
            resolved_agy = candidate
            break

    if AGENT_BACKEND == "antigravity" and resolved_agy:
        model_name = MODEL_TIERS.get(model_tier, model_tier) if model_tier else select_model_tier(agent_name=agent_name)
        return await call_antigravity_cli(
            task_id=task_id,
            agent_name=agent_name,
            messages=messages,
            tools=tools,
            agy_bin=resolved_agy,
            max_tokens=max_tokens,
            temperature=temperature,
            model_name=model_name,
            json_schema=json_schema,
            on_token_delta=on_token_delta,
            on_thinking_delta=on_thinking_delta,
        )

    return await call_ollama_chat(
        task_id=task_id,
        agent_name=agent_name,
        messages=messages,
        tools=tools,
        max_tokens=max_tokens,
        temperature=temperature,
    )
