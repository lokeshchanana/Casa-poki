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
