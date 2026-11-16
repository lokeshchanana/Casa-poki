---
name: casa-poki-ops
description: >-
  Operational runbook for managing services, secrets, backups, and deployments
  in the Casa-poki homelab repository. Use when adding or modifying services,
  updating Docker Compose or Cloudflared/Nginx configs, testing live integrations,
  or preparing changes for Git push and disaster recovery sync.
---

# Casa-poki Operations Runbook

Follow these procedures alongside the rules in [AGENTS.md](../../../AGENTS.md).

## 1. Adding or Updating a Service

1. **Secrets in Tank Storage**:
   - Store production secrets in `/tank/<service>/.env` with `chmod 600 /tank/<service>/.env`.
   - Link the service directory to tank secrets:
     ```bash
     ln -s /tank/<service>/.env <service>/.env
     ```
   - Maintain a sanitized `<service>/.env.example` in Git with placeholder keys only.
2. **Container & Proxy Wiring**:
   - Place service Compose/config files under `<service>/` in the repo root.
   - If exposing via Cloudflare Tunnel (`cloudflared/`) or Nginx Proxy Manager (`nginx/`), document the port and hostname in `README.md`.
3. **Real Estate Staging Rule**:
   - Test web changes against `real-estate-dev` (port `8089`, `dev.lokeshchanana.com`) first.
   - Never rebuild or modify the production `real-estate` container (port `8088`) without explicit user approval.

## 2. Live Service Testing & Cleanup

- All services (Twenty CRM, n8n, Relaticle, Check-in, Webhooks, Real Estate) are **live**.
- Only use the verified owner contact details for any email/SMS test (`lokeshchanana@gmail.com`, `8018601052` / `+18018601052`).
- **Immediately delete** any test records created in Twenty CRM, Postgres, or n8n after verification completes.

## 3. Pre-Commit Hygiene & DR Verification

Before committing or pushing to `origin`:

1. Run the hygiene check script:
   ```bash
   ./.agents/skills/casa-poki-ops/scripts/check-hygiene.sh
   ```
2. For architectural changes (new service/container, altered volume mounts, network changes, or ZFS dataset updates):
   - Update [scripts/restore-casa-poki.sh](../../../scripts/restore-casa-poki.sh) and [README.md](../../../README.md).
   - Verify [DISASTER_RECOVERY.md](../../../DISASTER_RECOVERY.md) remains accurate.
3. For significant `/tank/*` dataset or config changes, run the NFS mirror sync:
   ```bash
   sudo /usr/local/bin/casa-poki-sync.sh
   ```

## 4. Service & Tank Inventory

- **Repo services**: `adguard`, `agents`, `ai`, `bigcapital`, `checkin`, `cloudflared`, `habridge`, `mic-bridge`, `monitor`, `music-assistant`, `nginx`, `ollama`, `postgres-db`, `real-estate`, `relaticle`, `twenty`
- **Tank datasets (`/tank/`)**: `adguard`, `agents`, `antigravity-backup`, `bigcapital`, `cloudflared`, `habridge`, `mic-bridge`, `monitor`, `music-assistant`, `n8n`, `npm`, `ollama`, `postgres-db`, `re_office_data`, `relaticle`, `twenty`
