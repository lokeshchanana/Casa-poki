---
trigger: always_on
description: Always deploy website changes to dev.lokeshchanana.com first and wait for explicit user approval before deploying to production (lokeshchanana.com).
---

# Mandatory Dev-Before-Production Deployment Workflow

1. **Staging / Dev First (`dev.lokeshchanana.com`):**
   - Every change to the website codebase (`/home/lokesh/Casa-poki/real-estate`) MUST first be built and deployed ONLY to the `real-estate-dev` container (listening on port `8089`, served at `https://dev.lokeshchanana.com`):
     ```bash
     sudo docker compose up -d --build real-estate-dev
     ```
   - Never rebuild or restart the `real-estate` production container before the user has reviewed the changes on `https://dev.lokeshchanana.com`.

2. **Production Promotion (`lokeshchanana.com`):**
   - Only after the user explicitly approves the changes on `https://dev.lokeshchanana.com`, promote the changes to the `real-estate` production container (listening on port `8088`, served at `https://lokeshchanana.com`):
     ```bash
     sudo docker compose up -d --build real-estate
     ```
