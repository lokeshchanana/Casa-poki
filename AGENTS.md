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
