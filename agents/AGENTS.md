# Live Production Testing & Communication Safety Guidelines

These rules apply to all automated tests, agent executions, and developer operations across Casa-poki services (Twenty CRM, n8n, Relaticle, Check-in, Real Estate, and Agent Hub).

## 1. Zero Stray Communications (Email & SMS)
- **Services are LIVE.** Never generate fake, placeholder, or random email addresses or phone numbers (e.g., `@example.com`, random digits).
- If a test could trigger an email, SMS, notification, or marketing sync, **ONLY** use the owner's verified contact details:
  - **Email:** `lokeshchanana@gmail.com`
  - **Phone:** `8018601052` (or `+18018601052`)
- Under no circumstances should test messages be sent to real client records or arbitrary recipients.

## 2. Mandatory Test Cleanup
- Whenever an automated test or verification step inserts a record into Twenty CRM (or database, n8n, or external service):
  - **Immediately delete the test record** once verification is complete.
  - Leave no dummy or test artifacts lingering in the production CRM database.
