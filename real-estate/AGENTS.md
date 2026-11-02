# Real Estate Website (`lokeshchanana.com`) — Agent Instructions

## Mandatory Deployment Workflow: Dev First (`dev.lokeshchanana.com`) -> User Approval -> Production (`lokeshchanana.com`)

1. **Stage Changes on `dev.lokeshchanana.com` First:**
   - Whenever making any code, content, or styling change in `/home/lokesh/Casa-poki/real-estate`, build and deploy **only** the `real-estate-dev` service (port `8089`, proxied by `/tank/npm/conf.d/re.conf` for `dev.lokeshchanana.com`):
     ```bash
     sudo docker compose up -d --build real-estate-dev
     ```
   - Ask the user to review the live changes at `https://dev.lokeshchanana.com`.

2. **Promote to Production (`lokeshchanana.com`) Only After Approval:**
   - Do **not** touch the `real-estate` container (port `8088`) until the user explicitly approves the changes on `dev.lokeshchanana.com`.
   - Once approved, promote to production:
     ```bash
     sudo docker compose up -d --build real-estate
     ```

## Mandatory Live Service Testing & Communication Safety (CRITICAL)
- **All production services are LIVE.**
- **Zero Stray Communications:**
  - **NEVER** use randomly generated, placeholder, or fake emails or phone numbers (e.g., `@example.com`, random digits).
  - Any test that sends, drafts, or triggers an email or SMS MUST ONLY use:
    - **Email:** `lokeshchanana@gmail.com`
    - **Phone:** `8018601052` (or `+18018601052`)
- **Mandatory Immediate Cleanup:**
  - Whenever an automated test or verification step inserts or updates a record into Twenty CRM (or database, n8n, or external service), **immediately delete the test record** once the test is finished.
  - Never leave test or dummy records in the live CRM or database.

