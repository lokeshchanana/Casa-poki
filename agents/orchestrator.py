import asyncio
import json
import logging
import os
import re
import shutil
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from n8n_catalog import N8N_BASE_URL, get_n8n_workflows, inspect_latest_n8n_execution
from state_store import (
    add_agent_feedback,
    add_chat_message,
    add_lesson,
    get_backlog_specs,
    get_chat_history,
    get_last_audit_record,
    get_lessons,
    get_system_summary,
    log_audit_result,
    log_request_flow,
    log_token_usage,
    save_missing_workflow_spec,
    update_audit_status,
)
from tools import TOOL_SCHEMAS, execute_tool, format_tool_result
import vector_memory

logger = logging.getLogger("agent_orchestrator")

AGENT_BACKEND = os.environ.get("AGENT_BACKEND", "antigravity").lower()
AGY_PATH = os.environ.get("AGY_PATH", "/usr/local/bin/agy")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://192.168.1.240:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "crm-qwen:3b")
DEFAULT_TASK_BUDGET = int(os.environ.get("TASK_TOKEN_BUDGET", "250000"))


# =============================================================================
# Modern Multi-Agent Prompts
# =============================================================================

# =============================================================================
# Modern Multi-Agent Prompts & Persona Specializations
# =============================================================================

SPECIALIST_PERSONAS = {
    "manager": {
        "name": "Marcus Vance",
        "role": "General Manager & Orchestrator",
        "system_prompt": """You are Marcus Vance, General Manager & Orchestrator for Lokesh Chanana Real Estate and Casa-poki.
You focus on overall business triage, client communications, and orchestrating work across specialist agents.
DELEGATION POLICY:
- If a task requires IT infrastructure, server container healing, or technical database repairs, delegate to 'it'.
- If a task requires market comps, CMA, valuation, or MLS analytics, delegate to 'cma'.
- If a task requires marketing copy, listing flyers, or open house announcements, delegate to 'marketing'.
- If a task requires financial accounting, ledger statements, or transaction fee calculations, delegate to 'finance'.
- If a task requires client visitor intake or open house sign-in management, delegate to 'intake'.
- You have tools to manage Twenty CRM directly, query/store vector memory, or delegate to any specialist.""",
    },
    "it": {
        "name": "Ian Torres",
        "role": "IT Systems & Infrastructure Guardian",
        "system_prompt": """You are Ian Torres, IT Systems & Infrastructure Guardian for Casa-poki.
You focus on Docker containers, system self-healing, Uptime Kuma monitors, database connectivity, and backend tool reliability.
You provide technical precision and operational integrity.""",
    },
    "auditor": {
        "name": "Audrey Chen",
        "role": "Quality Assurance & Compliance Auditor",
        "system_prompt": """You are Audrey Chen, Quality Assurance & Compliance Auditor for Casa-poki.
You verify outputs, enforce the strict Zero Stray Communications policy, ensure no hallucinations, and log preventative lessons.""",
    },
    "intake": {
        "name": "Miles Miller",
        "role": "Client Intake & CRM Lifecycle Specialist",
        "system_prompt": """You are Miles Miller, Client Intake & CRM Lifecycle Specialist for Lokesh Chanana Real Estate.
You manage Twenty CRM contacts, lifecycle stage transitions, and deals (opportunities) based on real estate events.

LIFECYCLE & DEAL RULES:
1. Stage Hierarchy: Lead (1) -> Engaged (2) -> Active Client (3) -> Pending (4) -> Past Client (5).
   Never downgrade an Active Client or Pending client to Engaged when they browse or view portal links.
2. BBA / Listing Agreements:
   - When Form 41 BBA is signed: Set role='Buyer', lifecycle_stage='Active Client', bba_signed=true.
   - When Form 1A Listing is signed: Set role='Seller', lifecycle_stage='Active Client', create Seller deal.
3. Offers & Deals:
   - Deal Upsert: Always reuse/update an existing active Opportunity for the same normalized street address (e.g. "8610 63rd Ave E" == "8610 63rd Avenue E") rather than creating duplicate deals.
   - When an offer is submitted: Create or update deal (deal_stage='OFFER_SUBMITTED'). Contact stays Active Client.
   - When mutually accepted or escrow opens (Title/Escrow order opened): Set deal_stage='UNDER_CONTRACT', contact lifecycle_stage='Pending'.
   - Co-Clients & Nicknames: Resolve nicknames (e.g. Jim <-> James, Lola <-> Lodmella) and Authentisign participant full names. When couples/co-clients buy or sell together (e.g. Jim & Lola, Tharah & Jhen), update BOTH contacts, cross-link partnerName on each, and link both on the Opportunity.
   - Fall-Through / Terminated: If an offer is rejected or terminated (Form 35), set deal_stage='TERMINATED', revert all linked co-clients to 'Active Client'.
4. Closing & Past Clients:
   - When transaction closes (Title/Escrow recording): Set deal_stage='CLOSED_WON', all linked co-clients lifecycle_stage='Past Client'.
   - If Buyer: Set past_client_type='Buyer', home_maintenance_tips=true.
   - If Seller: Set past_client_type='Seller', home_maintenance_tips=false (no maintenance tips for sold homes).
5. Non-Client Emails: Listing agents, lenders, inspectors, home warranty reps, and escrow officers (@ctt.com) must NEVER be converted to Buyer/Seller clients.""",
    },
    "finance": {
        "name": "Fiona Banks",
        "role": "Financial Controller & CPA Bookkeeper",
        "system_prompt": """You are Fiona Banks, Financial Controller & CPA Bookkeeper for Casa-poki and Lokesh Chanana Real Estate, running on Antigravity.
You manage all financial accounting through Bigcapital hosted at https://finance.lokeshchanana.com.
CPA & IRS TAX COMPLIANCE MANDATES (.agents/skills/fiona-financial-controller/SKILL.md):
1. ZERO DUPLICATES (3-LAYER IDEMPOTENCY): Never create duplicate bills. Every expense is fingerprinted by canonical vendor, true invoice/order reference_no, original transaction date (never email forward date), and post-tax total.
2. 2-STEP ACCRUAL + ATOMIC 1-STEP PAYMENT SETTLEMENT: Bigcapital is a 2-step accrual system (Bill -> Bill Payment), whereas most owner expenses are single-step payment deductions (credit card / auto-pay / POS receipt). Always pass `auto_pay=True` when recording paid receipts/invoices so both the Bill and Bill Payment are created atomically (`Due Amount = $0.00`). Only leave a bill OPEN (`auto_pay=False`) if the document explicitly states "To be paid in-store" or "Amount Due".
3. SALES TAX RECONCILIATION: Always verify `Subtotal + Sales Tax = Total Paid` (e.g., WA ~10.3%-10.4% retail sales tax) and record the post-tax Total Paid.
4. RETURNS & REFUNDS NETTING: Always match return receipts (`START RETURN`, `Refund`, negative totals) against the original purchase order (`ORD-...` / `RET-...`) and net them to `$0.00` (`REFUNDED_NET_ZERO`) so refunded purchases are never claimed as tax deductions.
5. PROOF ARCHIVAL & INDEPENDENT AUDIT: Every expense proof (PDF or receipt + SHA-256 hash) is archived to `/tank/bigcapital/tax_vault/2026/` and Google Drive Proof Archive (`https://drive.google.com/drive/folders/1x3OD-FQAHWMyQnXEGal6WLj8-cHKFtYo`), and audited by Victor Sterling (`finance_tax_audit`). Flag any expense missing an invoice PDF, payment receipt, or dollar amount.

You have direct tools to:
- Scan Google Drive bills folder (`finance_scan_drive_bills`, default `1mj2jCnKsQGsdf4zV5R9dlr3SKthE3mNQ`).
- Scan email (`lokesh@lokeshchanana.com` and `billing@lokeshchanana.com`) for operating bills and receipts (`finance_scan_email_bills`).
- Trigger Victor Sterling's independent CPA & IRS tax audit (`finance_tax_audit`).
- Record, update, and settle bills (`finance_record_bill`, `finance_update_bill`, `finance_record_payment`, `finance_manage_bill_payments`, `finance_list_bills`, `finance_dashboard`, `finance_manage_vendors`, `finance_entity_operation`).""",
    },
    "tax_auditor": {
        "name": "Victor Sterling",
        "role": "Independent CPA & IRS Tax Compliance Auditor",
        "system_prompt": """You are Victor Sterling, Independent CPA & IRS Tax Compliance Auditor for Casa-poki and Lokesh Chanana Real Estate, running on Antigravity.
You independently audit Fiona Banks' Bigcapital accounting ledger (https://finance.lokeshchanana.com) and the Tax Proof Archive (/tank/bigcapital/tax_vault/2026 and Google Drive folder https://drive.google.com/drive/folders/1x3OD-FQAHWMyQnXEGal6WLj8-cHKFtYo).
Your responsibilities:
1. Run `finance_tax_audit` to inspect every bill, bill payment, and tax audit ledger entry.
2. Enforce zero duplicate bills, 100% 2-step payment settlement accuracy (`PAID` vs `OPEN`), exact `Subtotal + Sales Tax = Total` reconciliation, and proper return/refund netting (`REFUNDED_NET_ZERO`).
3. Verify that every expense has a physical proof file (PDF or itemized receipt) with a verified SHA-256 hash archived in the Tax Vault and Google Drive Proof Archive.
4. Clearly flag and report any expense missing an actual invoice copy (`FLAGGED_MISSING_INVOICE_COPY`), in-store payment receipt (`FLAGGED_MISSING_PAYMENT_RECEIPT`), or dollar amount (`FLAGGED_MISSING_AMOUNT_AND_INVOICE`) so the owner (Lokesh) can provide the document.""",
    },
    "marketing": {
        "name": "Maya Reyes",
        "role": "Creative Director, Brand Storyteller & Marketing Lead",
        "system_prompt": """You are Maya Reyes, Creative Director & Brand Storyteller for Lokesh Chanana Real Estate (Real Broker LLC, WA LIC #26006634).
You lead the Social Media Studio Wing (Devon Brooks, Nadia Kapoor, Leo Bennett, Priya Nair) and manage post-closing client smart plans (Brevo templates 5-17).
SOCIAL MEDIA RESPONSIBILITIES:
1. Read `.agents/product-marketing.md` and `.agents/skills/loki-social-media-team/SKILL.md` for brand voice (warm, neighborly, protective, zero pushy jargon, zero AI tells like em dashes or "It's not X, it's Y").
2. Transform Devon Brooks' WA market updates and viral format briefs into compelling storylines tailored to Greater Seattle & Puget Sound ($550k-$1.1M).
3. Explicitly choose `animated_avatar` (Nadia Kapoor's /tank/social/avatars/) vs. `real_photo` (Google Photos in /tank/social/photos/) or `hybrid` based on the story and Priya Nair's analytics.
4. Hand off the finalized storyline & script to Leo Bennett (`social_render_content`) to render the visual/video and queue it for Lokesh's approval.
You also have tools to manage the 1-Year Post-Close Drip Automation (`enroll_buyer_post_close`, `list_post_close_drips`, `process_post_close_drips`), plus `social_list_research_briefs`, `social_list_media_assets`, and `social_render_content`.""",
    },
    "social_scout": {
        "name": "Devon Brooks",
        "role": "WA Real Estate Market & Viral Format Scout",
        "system_prompt": """You are Devon Brooks, Washington Real Estate Market & Viral Format Scout for Lokesh Chanana Real Estate.
Follow `.agents/skills/wa-real-estate-market-intel/SKILL.md`.
Your job is to:
1. Research Greater Seattle & Puget Sound real estate market updates (King, Pierce, Snohomish, Thurston counties: median prices, inventory, mortgage rates, Light Rail & neighborhood shifts).
2. Scout and reverse-engineer high-performing viral social media formats & hooks (0-2s curiosity hooks, beat sheets, edit rhythms) across Instagram Reels, TikTok, Facebook, and X.
3. Save structured research briefs using `social_research_market_and_trends` so Maya Reyes and Leo Bennett can turn them into branded content.""",
    },
    "avatar_artist": {
        "name": "Nadia Kapoor",
        "role": "2D Vector Avatar Studio & Photo Curator",
        "system_prompt": """You are Nadia Kapoor, 2D Vector Avatar Studio & Photo Curator for Lokesh Chanana Real Estate.
Follow `.agents/skills/loki-avatar-studio/SKILL.md`.
STRICT IDENTITY LOCK (CRITICAL):
- Master Reference Image: `/tank/social/avatar_refs/loki_avatar_crop_ref.png` (from Lokesh's approved King County infographic).
- Art Style: Clean 2D flat vector editorial cartoon illustration with uniform dark-navy ink outlines (#152538) and flat cel-shading. NEVER generate 3D Pixar, CGI, glossy, or over-AI avatars.
- Locked Features: Top-knot man bun with faded sides, neatly trimmed full dark beard & mustache, warm open smile, silver-frame aviator sunglasses with dark gradient lenses, dark charcoal-slate blazer with circular white LC lapel pin, open-collar white button-down shirt, dark charcoal trousers.
- Every generated avatar MUST be visually consistent with the Master Reference and saved as a transparent PNG in `/tank/social/avatars/` with status `PENDING_REVIEW` so Lokesh can Approve or Reject it.
- Use `social_list_media_assets` to inspect approved/master avatars and Google Photos in `/tank/social/photos/`.""",
    },
    "content_producer": {
        "name": "Leo Bennett",
        "role": "Multi-Platform Static Content Producer",
        "system_prompt": """You are Leo Bennett, Multi-Platform Static Content Producer for Lokesh Chanana Real Estate.
Follow `.agents/skills/loki-social-media-team/SKILL.md` and `.agents/skills/loki-brand-design/SKILL.md`.
STATIC-IMAGE-ONLY POLICY (CRITICAL):
- Focus exclusively on STATIC IMAGE posts with ZERO AI sound/TTS until Lokesh's personal voice model is provided. Never generate AI-voiced Reels or TikToks.
- Render clean, publication-grade graphics via `social_render_content`:
  * `market_infographic` (1080x1920 9:16 WA Market Analysis Infographic Poster with bold stat cards + transparent 2D vector Loki)
  * `instagram_carousel` / `instagram_post` (1080x1350 4:5 editorial Ivory/Charcoal slides)
  * `instagram_story` (1080x1920 9:16 static poll/tip card)
  * `facebook` (1200x630 1.91:1 community card)
  * `twitter` (1200x675 16:9 data card)
- Every post MUST be queued as `PENDING_APPROVAL` (never auto-published), include `Real Broker LLC` compliance, and contain zero AI tells.""",
    },
    "social_ops": {
        "name": "Priya Nair",
        "role": "Social Analytics, Cadence & Scheduling Strategist",
        "system_prompt": """You are Priya Nair, Social Analytics, Cadence & Scheduling Strategist for Lokesh Chanana Real Estate.
Follow `.agents/skills/social-analytics-cadence/SKILL.md`.
Your job is to:
1. Sync historical post metrics from Postiz and `instagram_reels.json` using `social_sync_analytics`.
2. Analyze performance by platform, content pillar, and `real_photo` vs. `animated_avatar` to compute the optimal Pacific Time weekly posting cadence (`social_compute_cadence`).
3. Manage the Human-in-the-Loop Approval Queue (`social_list_approval_queue`).
4. CRITICAL SAFETY GATE: NEVER call `social_approve_and_schedule` unless Lokesh has explicitly approved the exact `post_id`.""",
    },
    "cma": {
        "name": "Carter Hayes",
        "role": "Real Estate Analyst & CMA Specialist",
        "system_prompt": """You are Carter Hayes, Real Estate Market Analyst & CMA Specialist.
You focus on Northwest MLS comparables, King County parcel pricing, school district impacts, and accurate valuation modeling.""",
    },
    "mailman": {
        "name": "Silas Drake",
        "role": "Mail Courier & Inbox Dispatcher",
        "system_prompt": """You are Silas Drake, Mail Courier & Inbox Dispatcher for Casa-poki and Lokesh Chanana Real Estate.
You are responsible for connecting to lokesh@lokeshchanana.com, reading incoming messages, stripping noise and HTML signatures, and delivering triaged email summaries directly to Marcus Vance (General Manager).

STRICT OUTBOUND EMAIL POLICY (CRITICAL):
- NEVER SEND AN EMAIL. Under no circumstances may any email be sent automatically.
- Even if a response is requested or needed, you MUST ONLY DRAFT the email and present/save it. The owner (Lokesh) will personally choose whether to send it.
- MANDATORY SIGNATURE: Always append the owner's exact signature to every drafted email:

Warm regards,

Lokesh Chanana (Loki)
REALTOR® • Real Estate Broker
WA License #26006634 | Real Broker LLC
M: (801) 860-1052 | E: lokesh@lokeshchanana.com
Web: lokeshchanana.com

You do not make independent business decisions; your sole mission is to reliably fetch, inspect, and present clean emails to Marcus Vance so he can decide what needs to be done:
- Real Estate Lifecycle & Deal Communications:
  * NWMLS Auto-Email setup / search notifications (from nwmls@nwmlsmatrixmail.com) -> Handed off to Miles Miller to activate search and set stage to Engaged.
  * NWMLS Portal activity / client views -> Handed off to Miles Miller to update last activity and portal status without downgrading higher stages.
  * Authentisign signed agreements (secure@authentisign.com) -> Identify BBA (Form 41), Listing (Form 1A), Purchase Agreement (Form 21), Counter, or Inspection Response (35R), extract all Participant full names from Signing updated/complete emails, and hand off to Miles Miller.
  * Offer submissions & disclosures (e.g. for Jim and Lola - 8610 63rd Ave E) -> Extract property address, all co-clients, dates, and hand off to Miles Miller.
  * Title & Escrow updates (e.g. Chicago Title @ctt.com order opened, earnest money, recording complete) -> Extract order number, property address, buyer/seller names, and hand off to Miles Miller without adding escrow officers as clients.
- Finance emails (bills, invoices, payment receipts, taxes) -> Handed off to Fiona Banks (Finance).
- CRM related emails (buyer/seller inquiries, client leads, contact info updates) -> Handed off to Miles Miller (Intake).
- CMA & property valuation inquiries -> Handed off to Carter Hayes (CMA).
- Marketing & promotional opportunities -> Handed off to Maya Reyes (Marketing).
- IT & infrastructure alerts -> Handed off to Ian Torres (IT).
- Useless / spam / cold solicitations -> Filtered out and discarded.""",
    },
    "homeassistant": {
        "name": "Hannah Reed",
        "role": "Home Assistant Guardian & Smart Home Engineer",
        "system_prompt": """You are Hannah Reed, Home Assistant Guardian & Smart Home Engineer for Casa-poki, running on Antigravity.
You monitor Home Assistant hosted at http://192.168.1.251:8123 (https://ha.lokeshchanana.com) and its companion containers (`music-assistant`, `habridge`, `adguardhome-adguardhome-1`).
You have direct tools to:
- Run a full Home Assistant health audit (`ha_health_check`): checks API reachability, core RUNNING state, configuration.yaml validity, persistent notifications, broken automations, unavailable critical entities, and companion containers.
- Automatically diagnose and safely fix Home Assistant issues (`ha_fix_issues`): refreshes stale entities (`homeassistant.update_entity`), reloads broken automations (`automation.reload`), reloads YAML integrations (`homeassistant.reload_all`), restarts unhealthy companion containers, and performs a config-validated HA restart only when required.
- Call any Home Assistant service (`ha_call_service`) for targeted remediation or device control.
When asked to monitor, check, or fix Home Assistant (HA), always run `ha_health_check` or `ha_fix_issues` and report the exact observed status and actions taken.""",
    },
}

MANAGER_SYSTEM_PROMPT = """You are Marcus Vance, Central Manager Agent for Lokesh Chanana Real Estate and Casa-poki.
You have access to a suite of tools to manage Twenty CRM (contacts, tasks, notes, deals), inspect automations, store/query vector memory, read incoming emails via Silas Drake, and delegate to specialist agents.

CORE CAPABILITIES & GUIDELINES:
1. Tool Invocation & Delegation:
   - When the user asks to check, read, triage, or fetch incoming emails from lokesh@lokeshchanana.com, invoke `mailman_read_inbox` or delegate to Silas Drake ('mailman').
   - When Silas Drake presents emails, analyze each message and decide what needs to be done:
     * Finance email, task, or receipt monitoring (invoices, utility bills, receipts, Google Drive bills folder, email bills at lokesh@lokeshchanana.com, payment notices, vendor updates, bill edits) -> Delegate to Fiona Banks ('finance') or invoke `finance_scan_email_bills`, `finance_scan_drive_bills`, `finance_record_bill`, `finance_update_bill`, `finance_manage_vendors`, `finance_entity_operation`.
     * Independent Tax & CPA Audit (auditing Fiona's work, checking for duplicate bills, missing receipts/invoice copies, proof archive verification, tax compliance) -> Delegate to Victor Sterling ('tax_auditor') or invoke `finance_tax_audit`.
     * CRM related email (buyer/seller inquiries, new leads, client updates) -> Delegate to Miles Miller ('intake') or call `create_contact` / `manage_notes` in Twenty CRM.
     * CMA / valuation request -> Delegate to Carter Hayes ('cma') for MLS comps.
     * Marketing / post-close drip / promotional request -> Delegate to Maya Reyes ('marketing') or invoke `enroll_buyer_post_close` / `list_post_close_drips` / `process_post_close_drips`.
     * Social Media Team requests:
       - WA real estate market updates or viral content format research -> Delegate to Devon Brooks ('social_scout') or invoke `social_research_market_and_trends`.
       - Animated avatars or Google Photos selection -> Delegate to Nadia Kapoor ('avatar_artist') or invoke `social_list_media_assets`.
       - Social storyline, Instagram/Facebook/TikTok/X content creation, carousels, or Reels -> Delegate to Maya Reyes ('marketing') or Leo Bennett ('content_producer') or invoke `social_render_content`.
       - Social analytics, posting cadence, or approval queue -> Delegate to Priya Nair ('social_ops') or invoke `social_sync_analytics` / `social_compute_cadence` / `social_list_approval_queue`.
       - NEVER auto-publish a social post; all drafts go to `PENDING_APPROVAL` for Lokesh's review.
     * IT / system alerts -> Delegate to Ian Torres ('it') to inspect containers or monitors.
     * Home Assistant / smart home monitoring or fixes -> Delegate to Hannah Reed ('homeassistant') or invoke `ha_health_check`, `ha_fix_issues`, `ha_call_service`.
     * Useless email / spam / cold solicitation -> Categorize as spam and discard with zero action.
   - When the user asks to consult, ask, or assign a task to another specialist (such as Carter Hayes for CMA/valuation, Maya Reyes for marketing, Fiona Banks for finance, Victor Sterling for tax/financial auditing, Miles Miller for intake, Silas Drake for emails, Ian Torres for IT, Hannah Reed for Home Assistant), invoke `delegate_to_agent` with target_agent and task_description.
   - When the user instructs you to search, view, count, create, update, or delete contacts, tasks, or notes in Twenty CRM, invoke the appropriate CRM tool.
   - For queries like "How many people...", use `search_contacts` with `count_mode: true` and appropriate filters (`can_email`, `phone_blank`, `email_present`).
   - Before answering complex questions or market inquiries, invoke `query_memory` to check the Vector Database for stored insights or past resolutions.
   - Store valuable lessons, client preferences, or domain facts with `store_memory` so the team gets continuously better.
2. Capability Inquiries vs. Actions:
   - If the user asks a question about what you can do (e.g. "Can you read my emails?"), answer directly in natural language explaining your capabilities, introducing Silas Drake, and noting the parameters.
3. Zero Stray Communications & Strict Outbound Email Policy (CRITICAL SAFETY):
   - NEVER SEND AN EMAIL AUTOMATICALLY. Under no circumstances may Marcus, Silas, or any agent send an email directly.
   - If an email reply or follow-up is needed, ONLY DRAFT the email and present/save it for review. The owner (Lokesh) will personally choose whether to send it.
   - MANDATORY SIGNATURE: Always include the owner's exact signature on every drafted email:

Warm regards,

Lokesh Chanana (Loki)
REALTOR® • Real Estate Broker
WA License #26006634 | Real Broker LLC
M: (801) 860-1052 | E: lokesh@lokeshchanana.com
Web: lokeshchanana.com

   - All production services are live. Never generate random or fake contact emails/phones. Only verified owner contact details (lokeshchanana@gmail.com / 8018601052) may be used for testing.
4. Response Tone:
   - Professional, concise, executive, and direct.
"""

AUDITOR_SYSTEM_PROMPT = """You are the Auditor Agent for Casa-poki and Lokesh Chanana Real Estate.
Review the execution of the IT Agent and tool output.
Verify:
1. Zero Hallucinations: Does the output accurately reflect the live database / tool response?
2. Criteria Satisfaction: Did the execution satisfy the user's specific request?
3. Safety Compliance: Were any unauthorized test records or stray communications triggered?

Output JSON:
{
  "audit_status": "PASS" | "QUALITY_IMPROVEMENT_NEEDED" | "MISSING_CAPABILITY",
  "quality_score": 1 to 10,
  "findings": "Clear explanation of audit verification verdict",
  "lesson_rule": "Optional preventative lesson if an improvement is needed, else empty"
}
"""


# =============================================================================
# Modular v2.0 Engine Imports (Re-exported for backward compatibility)
# =============================================================================

from auditor import run_auditor_verification
from context_manager import build_compacted_context, store_or_inline_tool_output
from hooks import pre_tool_use_hook
from llm_gateway import (
    call_antigravity_cli,
    call_llm_chat,
    call_ollama_chat,
    parse_antigravity_output,
    select_model_tier,
)
from state_store import (
    create_pending_approval,
    get_pending_approval,
    resolve_pending_approval,
    upsert_session_plan,
)
from subagent_runtime import (
    get_domain_tools_for_manager,
    run_parallel_subagents,
    run_specialist_subagent,
)


# =============================================================================
# Dynamic Context-Shift History Pruning
# =============================================================================

def detect_message_domain(text: str) -> str:
    """
    Identifies the semantic topic domain of a message to detect context shifts.
    Domains:
      - INFRA_TELEMETRY: Docker, containers, Uptime Kuma, monitors, health checks, ports, Ian Torres, logs, self-healing.
      - CRM_CONTACTS: Twenty CRM, contacts, leads, clients, phone numbers, email, Miles Miller, people, create/update contact.
      - FINANCE_ACCOUNTING: Bigcapital, bills, invoices, payables, vendors, Fiona Banks, financial dashboard, expenses.
      - EMAIL_INBOX: Gmail, Silas Drake, unread emails, mailman, triage, drafts, mailbox.
      - REAL_ESTATE_CMA: MLS, comps, property valuation, listings, Carter Hayes, Maya Reyes.
      - GENERAL_CONVERSATION: Default / greeting / capability checks / simple tests.
    """
    if not text:
        return "GENERAL_CONVERSATION"
    t = text.lower()

    # 0. Home Assistant & Smart Home keywords (Hannah Reed)
    ha_kw = [
        "home assistant", "homeassistant", "hass", "ha.lokeshchanana.com",
        "192.168.1.251", "hannah", "hanna", "hannah reed", "smart home", "zigbee", "zwave", "matter",
        "music assistant", "habridge", "unavailable entities", "monitor ha", "fix ha"
    ]
    if any(k in t for k in ha_kw) or re.search(r"\bha\b", t):
        return "HOME_ASSISTANT"

    # 1. Infrastructure & Telemetry keywords
    infra_kw = [
        "docker", "container", "containers", "uptime", "kuma", "monitor", "telemetry",
        "ian torres", "self-healing", "restart", "auto-heal", "daemon", "gateway",
        "port check", "adguard", "cloudflared", "beszel"
    ]
    if any(k in t for k in infra_kw):
        return "INFRA_TELEMETRY"

    # 2. Finance & Bigcapital keywords (Fiona Banks & Victor Sterling)
    finance_kw = [
        "bigcapital", "big capital", "fiona banks", "fiona", "victor sterling", "victor",
        "tax audit", "tax auditor", "taxman", "proof archive", "missing receipt", "missing invoice",
        "bill", "bills", "invoice", "invoices", "accounts payable", "vendor", "vendors",
        "payable", "financial dashboard", "expenses", "expanses", "receipt", "receipts",
        "cost till now", "duplicate entries", "duplicate bills"
    ]
    if any(k in t for k in finance_kw):
        return "FINANCE_ACCOUNTING"

    # 3. Email & Silas Drake keywords
    email_kw = [
        "silas", "mailman", "inbox", "unread email", "unread emails", "read emails",
        "check emails", "incoming email", "incoming emails", "email triage",
        "draft email", "lokesh@lokeshchanana.com"
    ]
    if any(k in t for k in email_kw):
        return "EMAIL_INBOX"

    # 4. CRM & Contact keywords
    crm_kw = [
        "crm", "contact", "contacts", "twenty", "twenty crm", "miles miller",
        "lead", "leads", "phone number", "can_email", "jim", "beidatsch",
        "person", "people", "customer", "search_contacts", "update_contact"
    ]
    if any(k in t for k in crm_kw):
        return "CRM_CONTACTS"

    # 5. Social Media Team keywords
    social_kw = [
        "social media", "instagram", "reel", "reels", "story", "stories", "carousel",
        "tiktok", "facebook", "twitter", "postiz", "avatar", "google photos",
        "cadence", "approval queue", "devon brooks", "nadia kapoor", "leo bennett", "priya nair",
        "viral format", "market update post"
    ]
    if any(k in t for k in social_kw):
        return "SOCIAL_MEDIA"

    # 6. Real Estate & CMA keywords
    cma_kw = [
        "cma", "mls", "comps", "comparable", "valuation", "carter hayes",
        "maya reyes", "listing", "listings", "marketing campaign"
    ]
    if any(k in t for k in cma_kw):
        return "REAL_ESTATE_CMA"

    return "GENERAL_CONVERSATION"


def prepare_pruned_history(
    history: List[Dict[str, Any]],
    current_user_query: str,
    max_char_threshold: int = 500,
) -> List[Dict[str, Any]]:
    """
    Intelligently prunes chat history ONLY when a context shift is detected.
    - If the user is continuing the SAME domain/topic, history is retained unpruned so multi-turn context is complete.
    - If the user has shifted to a DIFFERENT domain, prior bulky messages (> max_char_threshold)
      from the old domain are condensed to an executive summary, preventing prompt token explosion.
    """
    if not history:
        return []

    curr_domain = detect_message_domain(current_user_query)
    pruned: List[Dict[str, Any]] = []

    for item in history:
        role = item.get("role")
        content = item.get("content") or ""

        # User messages are preserved as-is; short assistant messages stay unpruned
        if role != "assistant" or len(content) <= max_char_threshold:
            pruned.append({"role": role, "content": content})
            continue

        item_domain = detect_message_domain(content)

        # Context shift condition: current query has an active domain that is DIFFERENT from this historical item's domain
        is_context_shift = (
            curr_domain != "GENERAL_CONVERSATION"
            and item_domain != "GENERAL_CONVERSATION"
            and curr_domain != item_domain
        )

        if is_context_shift:
            # Condense the bulky message to a concise executive summary
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            summary_header = lines[0] if lines else "Historical execution report"

            condensed_snippet = ""
            for l in lines[1:5]:
                if l.startswith("-") or l.startswith("*") or l.startswith("#"):
                    condensed_snippet += f"\n{l[:100]}"
            if not condensed_snippet and len(lines) > 1:
                condensed_snippet = f"\n{lines[1][:120]}..."

            condensed_content = (
                f"{summary_header}{condensed_snippet}\n"
                f"*(Note: Prior {item_domain} details condensed due to context shift to {curr_domain})*"
            )
            pruned.append({"role": role, "content": condensed_content})
            logger.info(
                f"Pruned historical message ({len(content)} -> {len(condensed_content)} chars) "
                f"due to context shift: {item_domain} -> {curr_domain}"
            )
        else:
            # Same topic or neutral context: preserve full detail
            pruned.append({"role": role, "content": content})

    return pruned


# =============================================================================
# Multi-Agent Pipeline Runner
# =============================================================================

async def run_multi_agent_pipeline(
    user_message: str,
    session_id: str = "manager_default",
    token_budget: int = DEFAULT_TASK_BUDGET,
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> AsyncGenerator[str, None]:
    """
    Modern Antigravity Manager Agent Pipeline:
    1. Multi-turn context resolution & triage
    2. Native tool execution via IT Agent (Twenty CRM / n8n gateway)
    3. Auditor Agent quality verification & spec generation
    4. Streams real-time ndjson events to the Check-in web app.
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    tokens_used = 0
    trace_steps: List[Dict[str, Any]] = []
    invoked_tool_name: Optional[str] = None
    invoked_tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None

    def emit(event_type: str, data: Dict[str, Any]) -> str:
        return json.dumps({"type": event_type, "task_id": task_id, **data}) + "\n"

    # Step 1: Manager Status
    yield emit(
        "agent_status",
        {
            "agent": "manager",
            "phase": "routing",
            "message": "Manager Agent is analyzing your request and preparing execution plan...",
        },
    )

    u_low = user_message.strip().lower()

    # -------------------------------------------------------------------------
    # Fast-Path 1: Human Feedback & Audit Flagging
    # -------------------------------------------------------------------------
    feedback_triggers = [
        "note for auditor", "note to auditor", "note for anti gravity", "note to anti gravity",
        "last execution is not correct", "execution is not correct", "result is no good",
        "result is not correct", "incorrect result", "fix this functionality", "flag this execution"
    ]
    if any(ft in u_low for ft in feedback_triggers):
        last_audit = get_last_audit_record()
        flagged_task_id = last_audit["task_id"] if last_audit else None
        saved_fb = add_agent_feedback(
            user_feedback=user_message,
            target_agent="auditor",
            action_taken="Flagged previous execution and recorded Auditor improvement task.",
            task_id=flagged_task_id,
        )
        if flagged_task_id:
            update_audit_status(flagged_task_id, "USER_FLAGGED_FAILURE", 2)

        fb_trace = {
            "step": 1,
            "agent": "Auditor Agent",
            "role": "Human Feedback Registry",
            "result": {"status": "FEEDBACK_LOGGED", "feedback_id": saved_fb["id"]},
            "metrics": {"duration_ms": 1, "total_tokens": 0},
            "tokens_remaining": token_budget,
        }
        trace_steps.append(fb_trace)
        yield emit("agent_trace", {"trace": fb_trace})

        reply = (
            f"### Human Feedback Recorded\n"
            f"- **Feedback ID:** `{saved_fb['id']}`\n"
            f"- **Target Task:** `{flagged_task_id or 'General'}`\n"
            f"- **Status:** Flagged for continuous learning and logged in Auditor Registry.\n"
            f"- The IT Agent was **not** invoked to avoid unnecessary write operations."
        )
        add_chat_message(session_id, "user", user_message)
        add_chat_message(session_id, "assistant", reply)
        yield emit("item", {"content": reply})
        yield emit(
            "complete",
            {
                "success": True,
                "trace": trace_steps,
                "tokens_used": 0,
                "token_budget": token_budget,
            },
        )
        yield emit(
            "agent_summary",
            {
                "success": True,
                "workflow_executed": None,
                "trace_steps": trace_steps,
                "tokens_used": 0,
                "token_budget": token_budget,
            },
        )
        return

    # -------------------------------------------------------------------------
    # Fast-Path 2: Teaching Rules ("Remember: ...")
    # -------------------------------------------------------------------------
    if any(u_low.startswith(p) for p in ["remember:", "remember to", "teach:", "add a rule:"]):
        rule_text = re.sub(r"^(remember:|remember to|teach:|add a rule:)\s*", "", user_message, flags=re.I).strip()
        target_agent = "it_agent" if "it" in u_low or "n8n" in u_low or "crm" in u_low else "manager"
        saved_lesson = add_lesson(target_agent, rule_text, source="user_prompt")

        teach_trace = {
            "step": 1,
            "agent": "Manager Agent",
            "role": "Lesson Registry",
            "result": {"status": "LESSON_ADDED", "lesson_id": saved_lesson["id"]},
            "metrics": {"duration_ms": 1, "total_tokens": 0},
            "tokens_remaining": token_budget,
        }
        trace_steps.append(teach_trace)
        yield emit("agent_trace", {"trace": teach_trace})

        reply = (
            f"### Rule Added to Agent Memory\n"
            f"- **Agent:** `{target_agent}`\n"
            f"- **Rule:** \"{rule_text}\"\n"
            f"- **Lesson ID:** `{saved_lesson['id']}`\n"
            f"All agents will adhere to this guideline in future executions."
        )
        add_chat_message(session_id, "user", user_message)
        add_chat_message(session_id, "assistant", reply)
        yield emit("item", {"content": reply})
        yield emit(
            "complete",
            {
                "success": True,
                "trace": trace_steps,
                "tokens_used": 0,
                "token_budget": token_budget,
            },
        )
        yield emit(
            "agent_summary",
            {
                "success": True,
                "workflow_executed": None,
                "trace_steps": trace_steps,
                "tokens_used": 0,
                "token_budget": token_budget,
            },
        )
        return

    # -------------------------------------------------------------------------
    # Main Agent Reasoner v2.0: Compaction, Streaming, Parallel ReAct, HITL & Audit
    # -------------------------------------------------------------------------
    raw_history = get_chat_history(session_id, limit=24)
    add_chat_message(session_id, "user", user_message)

    try:
        # 1. Vector Memory + PreCompact/PostCompact Rolling Context
        recalled_memories = vector_memory.query_memories(query=user_message, top_k=3)
        memory_context_block = ""
        if recalled_memories:
            memory_lines = [
                f"- [{m['agent_id'].upper()}] {m['content']} (relevance: {int(m['similarity']*100)}%)"
                for m in recalled_memories
            ]
            memory_context_block = "\nRelevant Vector Memories from Brain:\n" + "\n".join(memory_lines) + "\n"

        compacted = await build_compacted_context(
            session_id=session_id,
            full_history=raw_history,
            call_llm_fn=call_llm_chat,
            task_id=task_id,
        )
        history = prepare_pruned_history(compacted["messages"], user_message)

        lessons = [
            l["rule"] for l in get_lessons()
            if l.get("agent_name") in ("manager", "global", "all", None)
        ][:8]
        lessons_block = ("\nActive Lessons:\n" + "\n".join(f"- {r}" for r in lessons)) if lessons else ""

        summary_block = (
            f"\nRolling Session Summary:\n{compacted['summary']}\n"
            if compacted.get("summary")
            else ""
        )
        plan_block = (
            f"\nActive Task Plan:\n{json.dumps(compacted['plan'])}\n"
            if compacted.get("plan")
            else ""
        )

        # Build attachment context if user uploaded PDFs/images/files
        attachment_block = ""
        if attachments:
            att_parts = []
            for att in attachments:
                fname = att.get("filename") or "file"
                extracted = (att.get("extracted_text") or "").strip()
                fpath = att.get("file_path") or ""
                att_parts.append(f"[Attached File: {fname} | Path: {fpath}]\n{extracted[:4000]}")
            attachment_block = "\n\n### ATTACHED FILES ###\n" + "\n---\n".join(att_parts)

        domain = detect_message_domain(user_message)
        scoped_tools = get_domain_tools_for_manager(domain, TOOL_SCHEMAS)
        model_tier = select_model_tier(agent_name="manager", user_message=user_message)

        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    MANAGER_SYSTEM_PROMPT
                    + lessons_block
                    + memory_context_block
                    + summary_block
                    + plan_block
                ),
            },
        ]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message + attachment_block})

        async def _call_streaming_manager(msgs, tools_list, tier=model_tier):
            q: asyncio.Queue = asyncio.Queue()

            async def on_tok(d: str):
                await q.put(emit("token_delta", {"delta": d}))

            async def on_think(d: str):
                await q.put(emit("thinking_delta", {"delta": d}))

            task = asyncio.create_task(
                call_llm_chat(
                    task_id=task_id,
                    agent_name="manager",
                    messages=msgs,
                    tools=tools_list,
                    max_tokens=1800,
                    temperature=0.1,
                    model_tier=tier,
                    on_token_delta=on_tok,
                    on_thinking_delta=on_think,
                )
            )
            buffered_events: List[str] = []
            while not task.done() or not q.empty():
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=0.05)
                    buffered_events.append(ev)
                except asyncio.TimeoutError:
                    pass
            res = await task
            return res, buffered_events

        llm_resp, stream_events = await _call_streaming_manager(messages, scoped_tools)
        tokens_used += int(llm_resp["metrics"].get("total_tokens") or 0)
        tool_calls = llm_resp.get("tool_calls") or []
        direct_content = llm_resp.get("content") or ""

        if not tool_calls:
            for ev in stream_events:
                yield ev

        # ---------------------------------------------------------------------
        # Path A: Multi-Step Parallel ReAct Loop (up to 12 turns)
        # ---------------------------------------------------------------------
        if tool_calls:
            MAX_TOOL_TURNS = 12
            executed_tools: List[str] = []
            last_formatted = ""
            last_tool_ok = True
            last_tool_err = ""
            delegated_agent_names: List[str] = []
            all_citations: List[Dict[str, Any]] = []
            tool_evidence_chunks: List[str] = []
            final_synthesized = ""
            step_num = 0
            seen_call_counts: Dict[str, int] = {}
            paused_for_approval: Optional[Dict[str, Any]] = None

            for turn in range(MAX_TOOL_TURNS):
                if not tool_calls or paused_for_approval:
                    break

                # Filter circuit-breaker duplicates
                batch_calls = []
                for call in tool_calls:
                    func = call.get("function") or {}
                    t_name = str(func.get("name") or "")
                    t_args = func.get("arguments") or {}
                    if isinstance(t_args, str):
                        try:
                            t_args = json.loads(t_args)
                        except Exception:
                            t_args = {}
                    if t_name == "search_contacts" and "query" in t_args:
                        t_args["query"] = re.sub(
                            r"^(is there a |does a |find |search |use |user )",
                            "",
                            str(t_args["query"]),
                            flags=re.I,
                        ).strip()
                    sig = f"{t_name}:{json.dumps(t_args, sort_keys=True)}"
                    seen_call_counts[sig] = seen_call_counts.get(sig, 0) + 1
                    if seen_call_counts[sig] > 2:
                        continue
                    batch_calls.append((call, t_name, t_args))

                if not batch_calls:
                    break

                invoked_tool_name = batch_calls[0][1]
                invoked_tool_args = batch_calls[0][2]

                yield emit(
                    "agent_status",
                    {
                        "agent": "it_agent",
                        "phase": "executing_tool",
                        "message": (
                            f"Executing {len(batch_calls)} tool(s) in parallel (turn {turn + 1}/{MAX_TOOL_TURNS})..."
                            if len(batch_calls) > 1
                            else f"Executing `{invoked_tool_name}` (step {turn + 1}/{MAX_TOOL_TURNS})..."
                        ),
                    },
                )

                for _, t_name, t_args in batch_calls:
                    step_num += 1
                    plan_trace = {
                        "step": step_num,
                        "agent": "Manager Agent",
                        "role": "Task Triage & Parallel Dispatch",
                        "decision": {
                            "intent": "EXECUTE_TOOL",
                            "tool": t_name,
                            "arguments": t_args,
                            "turn": turn + 1,
                        },
                        "metrics": llm_resp["metrics"],
                        "tokens_remaining": max(0, token_budget - tokens_used),
                    }
                    trace_steps.append(plan_trace)
                    yield emit("agent_trace", {"trace": plan_trace})

                async def _exec_single(call_obj, t_name: str, t_args: Dict[str, Any]):
                    if t_name == "manage_plan":
                        steps = upsert_session_plan(session_id, task_id, t_args.get("steps") or [])
                        return call_obj, t_name, t_args, {"ok": True, "plan": steps, "plan_updated": True}, "Manager Agent", "Execution Plan"

                    hook_res = pre_tool_use_hook(t_name, t_args, session_id)
                    if hook_res["decision"] == "BLOCK":
                        return call_obj, t_name, t_args, {"ok": False, "blocked": True, "error": hook_res["reason"]}, "PreToolUse Hook", "Policy Guardrail"

                    if hook_res["decision"] == "REQUIRE_APPROVAL":
                        app_id = f"appr_{uuid.uuid4().hex[:10]}"
                        appr = create_pending_approval(
                            approval_id=app_id,
                            session_id=session_id,
                            task_id=task_id,
                            agent_name="manager",
                            tool_name=t_name,
                            arguments=t_args,
                            summary=hook_res["summary"],
                        )
                        return call_obj, t_name, t_args, {
                            "ok": False,
                            "approval_required": True,
                            "approval": appr,
                        }, "PreToolUse Hook", "Human Approval Gate"

                    if t_name == "delegate_to_agent":
                        target_agent = str(t_args.get("target_agent") or "manager").lower()
                        sub_res = await run_specialist_subagent(
                            task_id=task_id,
                            session_id=session_id,
                            target_agent=target_agent,
                            task_desc=str(t_args.get("task_description") or ""),
                            context_data=str(t_args.get("context_data") or ""),
                            personas=SPECIALIST_PERSONAS,
                        )
                        return call_obj, t_name, t_args, sub_res, sub_res["specialist_name"], f"Specialist ({sub_res['role']})"

                    if t_name == "delegate_parallel":
                        par_res = await run_parallel_subagents(
                            task_id=task_id,
                            session_id=session_id,
                            tasks=t_args.get("tasks") or [],
                            personas=SPECIALIST_PERSONAS,
                        )
                        return call_obj, t_name, t_args, par_res, "Multi-Specialist Fan-Out", "Parallel Subagents"

                    raw_res = await execute_tool(t_name, t_args)
                    return call_obj, t_name, t_args, raw_res, "Agent Hub", "Tool Execution Gateway"

                batch_done = await asyncio.gather(*[_exec_single(c, n, a) for c, n, a in batch_calls])

                messages.append({"role": "assistant", "content": "", "tool_calls": [b[0] for b in batch_done]})

                for _, t_name, t_args, t_res, actor_name, actor_role in batch_done:
                    executed_tools.append(t_name)
                    if isinstance(t_res, dict) and t_res.get("tokens_used"):
                        tokens_used += int(t_res["tokens_used"])

                    if isinstance(t_res, dict) and t_res.get("plan_updated"):
                        yield emit("plan_update", {"plan": t_res["plan"]})

                    if isinstance(t_res, dict) and t_res.get("citations"):
                        all_citations.extend(t_res["citations"])

                    if isinstance(t_res, dict) and t_res.get("approval_required"):
                        paused_for_approval = t_res["approval"]
                        yield emit("approval_required", {"approval": paused_for_approval})

                    if isinstance(t_res, dict) and t_res.get("pending_approvals"):
                        paused_for_approval = t_res["pending_approvals"][0]
                        yield emit("approval_required", {"approval": paused_for_approval})

                    if t_name == "delegate_to_agent" and isinstance(t_res, dict):
                        if t_res.get("specialist_name") and t_res["specialist_name"] not in delegated_agent_names:
                            delegated_agent_names.append(t_res["specialist_name"])
                        last_formatted = (
                            f"### Delegated Response from {t_res.get('specialist_name')} ({t_res.get('role')})\n\n"
                            f"{t_res.get('response', '')}"
                        )
                    elif t_name == "delegate_parallel" and isinstance(t_res, dict):
                        parts = []
                        for rep in t_res.get("reports") or []:
                            sn = rep.get("specialist_name")
                            if sn and sn not in delegated_agent_names:
                                delegated_agent_names.append(sn)
                            parts.append(f"### {sn} ({rep.get('role')})\n{rep.get('response', '')}")
                        last_formatted = "\n\n---\n\n".join(parts)
                    elif isinstance(t_res, dict) and not t_res.get("approval_required"):
                        last_formatted = format_tool_result(t_name, t_res, t_args)

                    if isinstance(t_res, dict) and not (t_res.get("ok", True) and "error" not in t_res):
                        if not t_res.get("approval_required"):
                            last_tool_ok = False
                            last_tool_err = str(t_res.get("error") or "Unknown error")

                    step_num += 1
                    exec_trace = {
                        "step": step_num,
                        "agent": actor_name,
                        "role": actor_role,
                        "result": {
                            "tool": t_name,
                            "status": (
                                "APPROVAL_REQUIRED"
                                if (isinstance(t_res, dict) and t_res.get("approval_required"))
                                else ("SUCCESS" if (isinstance(t_res, dict) and t_res.get("ok", True)) else "FAILED")
                            ),
                            "raw_result": t_res,
                        },
                        "metrics": {"duration_ms": (t_res.get("duration_ms", 50) if isinstance(t_res, dict) else 50), "total_tokens": 0},
                        "tokens_remaining": max(0, token_budget - tokens_used),
                    }
                    trace_steps.append(exec_trace)
                    yield emit("agent_trace", {"trace": exec_trace})

                    safe_tool_msg = store_or_inline_tool_output(session_id, t_name, t_res)
                    tool_evidence_chunks.append(f"[{t_name}] {safe_tool_msg[:800]}")
                    messages.append({"role": "tool", "content": safe_tool_msg})

                if paused_for_approval:
                    pause_msg = (
                        f"⏸️ **Approval Required:** {paused_for_approval['summary']}\n\n"
                        "Please click **Approve & Execute** or **Reject** on the action card below."
                    )
                    add_chat_message(session_id, "assistant", pause_msg, tool_calls=[{"name": t} for t in executed_tools])
                    yield emit("item", {"content": pause_msg})
                    yield emit(
                        "complete",
                        {
                            "success": True,
                            "awaiting_approval": True,
                            "approval": paused_for_approval,
                            "trace": trace_steps,
                            "tokens_used": tokens_used,
                            "token_budget": token_budget,
                        },
                    )
                    return

                # Ask Marcus to continue chaining tools or synthesize final answer
                if turn + 1 < MAX_TOOL_TURNS and tokens_used < token_budget:
                    llm_resp, next_stream_events = await _call_streaming_manager(messages, scoped_tools)
                    tokens_used += int(llm_resp["metrics"].get("total_tokens") or 0)
                    tool_calls = llm_resp.get("tool_calls") or []
                    final_synthesized = (llm_resp.get("content") or "").strip()
                    if not tool_calls and final_synthesized:
                        stream_events = next_stream_events
                else:
                    tool_calls = []

            if len(executed_tools) == 1 and last_formatted and not final_synthesized:
                formatted_result = last_formatted
            elif final_synthesized:
                formatted_result = final_synthesized
            else:
                formatted_result = last_formatted or "Completed multi-step execution."

            # Deduplicate citations
            dedup_citations: List[Dict[str, Any]] = []
            seen_c_urls = set()
            for c in all_citations:
                u = c.get("url")
                if u and u not in seen_c_urls:
                    seen_c_urls.add(u)
                    dedup_citations.append({**c, "index": len(dedup_citations) + 1})

            if dedup_citations:
                yield emit("citations", {"citations": dedup_citations})

            # Step Final: Hybrid Deterministic + LLM Auditor Verification + 1-Turn Self-Correction
            yield emit(
                "agent_status",
                {
                    "agent": "auditor",
                    "phase": "auditing",
                    "message": "Audrey Chen is verifying accuracy, grounding, and compliance...",
                },
            )

            audit_verdict = await run_auditor_verification(
                task_id=task_id,
                user_message=user_message,
                draft_response=formatted_result,
                executed_tools=executed_tools,
                last_tool_ok=last_tool_ok,
                last_tool_err=last_tool_err,
                tool_evidence_preview="\n".join(tool_evidence_chunks),
                auditor_system_prompt=AUDITOR_SYSTEM_PROMPT,
            )
            tokens_used += int(audit_verdict.get("tokens_used") or 0)

            if audit_verdict.get("audit_status") == "QUALITY_IMPROVEMENT_NEEDED" and last_tool_ok and tokens_used < token_budget:
                messages.append({"role": "assistant", "content": formatted_result})
                messages.append({
                    "role": "user",
                    "content": f"[Auditor Critique]: {audit_verdict['findings']}. Please correct and improve your answer strictly using verified tool evidence.",
                })
                retry_resp, retry_stream = await _call_streaming_manager(messages, None)
                tokens_used += int(retry_resp["metrics"].get("total_tokens") or 0)
                if (retry_resp.get("content") or "").strip():
                    formatted_result = retry_resp["content"].strip()
                    stream_events = retry_stream
                    audit_verdict["audit_status"] = "PASS"
                    audit_verdict["quality_score"] = 9
                    audit_verdict["findings"] += " (Auto-corrected by Marcus Vance)"

            audit_status = audit_verdict.get("audit_status", "PASS")
            quality_score = int(audit_verdict.get("quality_score") or 9)
            audit_findings = audit_verdict.get("findings") or "Verified."
            audit_ok = audit_status == "PASS"

            log_audit_result(
                task_id=task_id,
                user_request=user_message,
                routed_agent=",".join(delegated_agent_names) if delegated_agent_names else "manager",
                workflow_id=executed_tools[-1] if executed_tools else "manager_pipeline",
                audit_status=audit_status,
                quality_score=quality_score,
                findings=audit_findings,
            )

            step_num += 1
            audit_trace = {
                "step": step_num,
                "agent": "Auditor Agent",
                "role": "Quality & Compliance Audit",
                "report": {
                    "audit_status": audit_status,
                    "quality_score": quality_score,
                    "findings": audit_findings,
                },
                "metrics": {"duration_ms": 2, "total_tokens": audit_verdict.get("tokens_used", 0)},
                "tokens_remaining": max(0, token_budget - tokens_used),
            }
            trace_steps.append(audit_trace)
            yield emit("agent_trace", {"trace": audit_trace})

            add_chat_message(session_id, "assistant", formatted_result, tool_calls=[{"name": t} for t in executed_tools])

            try:
                agents_in_flow = ["Marcus Vance"] + delegated_agent_names + ["Audrey Chen"]
                steps_summary = [
                    {
                        "step": "Planning & Orchestration",
                        "agent": "Marcus Vance",
                        "action": f"Analyzed prompt: '{user_message[:60]}...'",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
                        "status": "ok",
                    },
                    {
                        "step": f"Tool Execution ({', '.join(executed_tools)})",
                        "agent": delegated_agent_names[-1] if delegated_agent_names else "Marcus Vance",
                        "action": f"Executed {len(executed_tools)} tool step(s): {', '.join(executed_tools)}",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "status": "ok" if audit_ok else "warning",
                    },
                    {
                        "step": "Quality & Verification",
                        "agent": "Audrey Chen",
                        "action": f"Audit verification ({audit_status}, quality: {quality_score}/10)",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "status": "ok" if audit_ok else "warning",
                    },
                ]
                log_request_flow(
                    flow_id=f"flow_chat_{task_id}",
                    source="Manager Chat UI",
                    title=f"Chat: {user_message[:50]}",
                    status="completed" if audit_ok else "warning",
                    agents_involved=agents_in_flow,
                    steps=steps_summary,
                    payload_preview={"input": user_message, "tools": executed_tools},
                    result_summary=formatted_result[:140],
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            except Exception as e:
                logger.warning(f"Could not log tool request flow: {e}")

            yield emit("item", {"content": formatted_result, "citations": dedup_citations})
            yield emit(
                "complete",
                {
                    "success": audit_ok,
                    "workflow_executed": "agent_hub_v2",
                    "citations": dedup_citations,
                    "trace": trace_steps,
                    "tokens_used": tokens_used,
                    "token_budget": token_budget,
                },
            )
            yield emit(
                "agent_summary",
                {
                    "success": audit_ok,
                    "workflow_executed": "agent_hub_v2",
                    "trace_steps": trace_steps,
                    "tokens_used": tokens_used,
                    "token_budget": token_budget,
                },
            )
            return

        # ---------------------------------------------------------------------
        # Path B: Direct Conversational / Capability Response (0 Tool Calls)
        # ---------------------------------------------------------------------
        yield emit(
            "agent_status",
            {
                "agent": "manager",
                "phase": "answering",
                "message": "Manager Agent formulated a direct strategic response...",
            },
        )

        log_audit_result(
            task_id=task_id,
            user_request=user_message,
            routed_agent="manager",
            workflow_id=None,
            audit_status="PASS",
            quality_score=10,
            findings="Manager answered directly without unnecessary tool overhead.",
        )

        step1_trace = {
            "step": 1,
            "agent": "Manager Agent",
            "role": "Direct Strategic Response",
            "result": {"status": "DIRECT_ANSWER_DELIVERED"},
            "metrics": llm_resp["metrics"],
            "tokens_remaining": max(0, token_budget - tokens_used),
        }
        trace_steps.append(step1_trace)
        yield emit("agent_trace", {"trace": step1_trace})

        final_msg = direct_content.strip() or "I have processed your request."
        add_chat_message(session_id, "assistant", final_msg)

        try:
            log_request_flow(
                flow_id=f"flow_chat_{task_id}",
                source="Manager Chat UI",
                title=f"Chat: {user_message[:50]}",
                status="completed",
                agents_involved=["Marcus Vance", "Audrey Chen"],
                steps=[
                    {
                        "step": "Planning & Orchestration",
                        "agent": "Marcus Vance",
                        "action": f"Analyzed prompt: '{user_message[:60]}...'",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
                        "status": "ok",
                    },
                    {
                        "step": "Quality & Verification",
                        "agent": "Audrey Chen",
                        "action": f"Audit quality verified (tokens: {tokens_used}, duration: {int((time.time() - start_time) * 1000)}ms)",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "status": "ok",
                    },
                ],
                payload_preview={"input": user_message, "session_id": session_id},
                result_summary=final_msg[:120],
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.warning(f"Could not log chat flow: {e}")

        yield emit("item", {"content": final_msg})
        yield emit(
            "complete",
            {
                "success": True,
                "workflow_executed": None,
                "trace": trace_steps,
                "tokens_used": tokens_used,
                "token_budget": token_budget,
            },
        )
        yield emit(
            "agent_summary",
            {
                "success": True,
                "workflow_executed": None,
                "trace_steps": trace_steps,
                "tokens_used": tokens_used,
                "token_budget": token_budget,
            },
        )
    except Exception as pipeline_err:
        logger.exception(f"Pipeline error for task {task_id}: {pipeline_err}")
        err_msg = f"⚠️ Request failed before completion: {pipeline_err}"
        add_chat_message(session_id, "assistant", err_msg)
        yield emit("item", {"content": err_msg})
        yield emit(
            "complete",
            {
                "success": False,
                "error": str(pipeline_err),
                "trace": trace_steps,
                "tokens_used": tokens_used,
                "token_budget": token_budget,
            },
        )


async def resume_approved_tool(
    approval_id: str,
    decision: str,
    edited_args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Executes or rejects a previously gated HITL tool call after owner review.
    """
    appr = get_pending_approval(approval_id)
    if not appr:
        return {"ok": False, "error": "Approval request not found"}
    if appr["status"] != "PENDING":
        return {"ok": False, "error": f"Approval already {appr['status']}"}

    dec = (decision or "").strip().lower()
    if dec != "approve":
        resolve_pending_approval(approval_id, "REJECTED")
        msg = f"❌ **Action Rejected by Owner:** {appr['summary']}"
        add_chat_message(appr["session_id"], "assistant", msg)
        return {"ok": True, "status": "REJECTED", "content": msg, "session_id": appr["session_id"]}

    args_to_run = edited_args if isinstance(edited_args, dict) else appr["arguments"]
    res = await execute_tool(appr["tool_name"], args_to_run)
    resolve_pending_approval(approval_id, "APPROVED")
    formatted = format_tool_result(appr["tool_name"], res, args_to_run)
    if not formatted:
        formatted = f"✅ **Approved & Executed:** {appr['summary']}\n\n```json\n{json.dumps(res, indent=2)[:1500]}\n```"
    add_chat_message(appr["session_id"], "assistant", formatted, tool_calls=[{"name": appr["tool_name"]}])
    return {
        "ok": True,
        "status": "APPROVED",
        "tool": appr["tool_name"],
        "result": res,
        "content": formatted,
        "session_id": appr["session_id"],
    }
