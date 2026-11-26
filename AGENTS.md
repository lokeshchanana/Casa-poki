# Global Casa-poki & Antigravity Operational Guidelines

## 1. Mandatory Live Service Testing & Communication Safety (CRITICAL)
- **All production services (CRM, n8n, Relaticle, Check-in, Webhooks, Real Estate) are LIVE.**
- **Zero Stray Communications:**
  - **NEVER** use randomly generated, placeholder, or fake emails or phone numbers (e.g., `@example.com`, `555-xxxx`, random digits). They can result in real outgoing emails or SMS messages.
  - If any test involves sending, drafting, testing, or syncing an email or SMS, **ONLY** use the owner's verified contact details:
    - **Email:** `lokeshchanana@gmail.com`
    - **Phone:** `8018601052` (or `+18018601052`)
- **Mandatory Immediate Cleanup:**
  - Whenever an automated test or verification step inserts or updates a record into Twenty CRM (or database, n8n, or external service), **immediately delete the test record** once the test is finished.
  - Never leave test or dummy records in the live CRM or database.

## 2. Real Estate Website Deployment Workflow
- Staging changes on `dev.lokeshchanana.com` first (`real-estate-dev` container on port 8089).
- Never modify or rebuild `real-estate` production container (port 8088) without explicit user approval.

## 3. Plan-First Execution Workflow
- For any multi-step task, system modification, or code change, **first create a single, clear plan of action** and present it to the user for approval (or via an implementation plan artifact with `RequestFeedback: true`).
- Once the user approves the plan, execute the entire plan end-to-end without stopping for step-by-step confirmation unless an unexpected blocker occurs.

## 4. Mandatory Post-Task Synchronization & Secret Hygiene
- **Secrets Management**: All secrets and environment variables MUST stay in their corresponding service tank (`/tank/<service>/.env`) with permissions `0600`, never committed to Git. Symlinks (`.env -> /tank/<service>/.env`) connect repo services to tank secrets. Always commit clean `.env.example` templates to Git.
- **Git Synchronization**: For all tasks that change code, compose files, configurations, or scripts, always update Git, ensure no secrets or local databases are staged, and push changes to `https://github.com/lokeshchanana/Casa-poki.git`.
- **NFS Replication Sync**: Maintain the nightly replication (`casa-poki-sync.timer` at 02:00 AM) to `192.168.1.250`. If significant changes to tank configurations or datasets are made, run a sync (`sudo /usr/local/bin/casa-poki-sync.sh`) to ensure the NFS mirror is current.
- **Disaster Recovery Script Maintenance**: After every major architectural change (adding a new service, new container, altered volume mounts, network adjustments, or ZFS dataset modifications), always verify and update `scripts/restore-casa-poki.sh` and `README.md` so the bare-metal restore engine stays 100% current and tested.
- **Uptime Kuma Monitoring Synchronization**: Whenever adding, retiring, or changing ports/URLs of any service, always update `scripts/sync-uptime-kuma.py` and run `sudo python3 scripts/sync-uptime-kuma.py` so `/tank/monitor/uptime-kuma/kuma.db` and the `uptime-kuma` container stay 100% current (preventing stale alerts or auto-heal restarts of retired services).

## 5. Zero-Spend External Search API Policy (CRITICAL)
- **Strict Free-Tier-Only Rule:** Tavily and Brave Search APIs MUST NEVER incur any paid charges or overages under any circumstance.
- **Hard Code-Level Caps:**
  - **Tavily:** Hard cap at **900 credits/month** and **35 credits/day** (free tier is 1,000/month). Default to `search_depth="basic"` (1 credit). Never run `advanced` depth without explicit budget headroom.
  - **Brave Search:** Hard cap at **900 requests/month** and **35 requests/day** (free tier is \$5/month ≈ 1,000 requests).
- **Atomic Pre-Flight Ledger & Cache:** Every Tavily/Brave call must reserve quota in SQLite (`search_quota_usage`) *before* dispatching HTTP requests and use a 15-minute query cache.
- **Automatic Free Fallback:** When either provider reaches its daily or monthly cap (or is rate-limited), immediately bypass the paid API and fall back to free Google-grounded `agy` `search_web` + Google News RSS.
