#!/usr/bin/env python3
"""
Declarative Uptime Kuma Monitor Sync for Casa-poki.

Keeps /tank/monitor/uptime-kuma/kuma.db synchronized with the active services
in the homelab:
  - Retires/removes monitors no longer in DESIRED_MONITORS (e.g., retired n8n).
  - Adds or updates all monitors in DESIRED_MONITORS.
  - Links every monitor to Notification #1 ("Agent Hub Infra Guardian").
  - Restarts the uptime-kuma container if any DB changes were applied.
"""

import argparse
import os
import sqlite3
import subprocess
from datetime import datetime
from typing import Any, Dict, List

KUMA_DB_PATH = os.environ.get("KUMA_DB_PATH", "/tank/monitor/uptime-kuma/kuma.db")
DEFAULT_NOTIFICATION_ID = 1

RETIRED_MONITOR_NAMES = [
    "n8n Automation Engine",
]

DESIRED_MONITORS: List[Dict[str, Any]] = [
    {"name": "Casa-Poki Gateway", "type": "http", "url": "https://lokeshchanana.com/"},
    {"name": "Twenty CRM", "type": "http", "url": "https://crm.lokeshchanana.com/healthz"},
    {"name": "Home Assistant", "type": "http", "url": "http://192.168.1.251:8123/"},
    {"name": "AdGuard Home", "type": "http", "url": "http://192.168.1.240:8053/"},
    {"name": "Real Estate Website (Prod)", "type": "http", "url": "https://lokeshchanana.com/"},
    {"name": "Beszel Metrics Hub", "type": "http", "url": "https://beszel.lokeshchanana.com/"},
    {"name": "Uptime Kuma Monitor", "type": "http", "url": "https://monitor.lokeshchanana.com/"},
    {"name": "Casa-Poki Host Ping", "type": "ping", "hostname": "192.168.1.240"},
    {"name": "Casa-Poki SSH", "type": "port", "hostname": "192.168.1.240", "port": 22},
    {"name": "Real Estate Website (Dev)", "type": "http", "url": "https://dev.lokeshchanana.com/"},
    {"name": "Open House Check-in App", "type": "http", "url": "https://checkin.lokeshchanana.com/"},
    {"name": "Local AI Inference (Ollama)", "type": "http", "url": "http://192.168.1.240:11434/"},
    {"name": "Agent Hub API", "type": "http", "url": "http://192.168.1.240:8094/docs"},
    {"name": "PostgreSQL 17 Database", "type": "port", "hostname": "192.168.1.240", "port": 5432},
    {"name": "NFS Backup Server (Ping)", "type": "ping", "hostname": "192.168.1.250"},
    {"name": "NFS Backup Server (SSH)", "type": "port", "hostname": "192.168.1.250", "port": 22},
    {"name": "Bigcapital Accounting", "type": "http", "url": "http://192.168.1.240:8096/"},
    {"name": "Postiz Social Studio", "type": "http", "url": "http://192.168.1.240:4007/"},
]


def sync_kuma(dry_run: bool = False) -> bool:
    if not os.path.exists(KUMA_DB_PATH):
        raise FileNotFoundError(f"Uptime Kuma DB not found at {KUMA_DB_PATH}")

    conn = sqlite3.connect(KUMA_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    changed = False

    # 1. Remove retired monitors and their heartbeats/notification links
    for r_name in RETIRED_MONITOR_NAMES:
        row = cur.execute("SELECT id FROM monitor WHERE name = ?", (r_name,)).fetchone()
        if row:
            mid = row["id"]
            print(f"[RETIRE] Removing monitor #{mid}: {r_name}")
            if not dry_run:
                cur.execute("DELETE FROM monitor_notification WHERE monitor_id = ?", (mid,))
                cur.execute("DELETE FROM heartbeat WHERE monitor_id = ?", (mid,))
                cur.execute("DELETE FROM monitor WHERE id = ?", (mid,))
            changed = True

    # 2. Upsert desired monitors
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for spec in DESIRED_MONITORS:
        name = spec["name"]
        mtype = spec["type"]
        url = spec.get("url")
        hostname = spec.get("hostname")
        port = spec.get("port")
        existing = cur.execute("SELECT id, type, url, hostname, port, active FROM monitor WHERE name = ?", (name,)).fetchone()

        if existing:
            mid = existing["id"]
            if (
                existing["type"] != mtype
                or existing["url"] != url
                or existing["hostname"] != hostname
                or existing["port"] != port
                or existing["active"] != 1
            ):
                print(f"[UPDATE] Updating monitor #{mid}: {name}")
                if not dry_run:
                    cur.execute(
                        "UPDATE monitor SET type = ?, url = ?, hostname = ?, port = ?, active = 1 WHERE id = ?",
                        (mtype, url, hostname, port, mid),
                    )
                changed = True
        else:
            print(f"[ADD] Creating monitor: {name} ({mtype} -> {url or hostname})")
            if not dry_run:
                cur.execute(
                    """
                    INSERT INTO monitor (
                        name, active, user_id, interval, url, type, weight, hostname, port,
                        created_date, maxretries, ignore_tls, upside_down, maxredirects,
                        accepted_statuscodes_json, retry_interval, method, expiry_notification,
                        resend_interval, packet_size, timeout, gamedig_given_port_only
                    ) VALUES (?, 1, 1, 60, ?, ?, 2000, ?, ?, ?, 1, 0, 0, 10, '["200-299", "300-399"]', 0, 'GET', 1, 0, 56, 0.0, 1)
                    """,
                    (name, url, mtype, hostname, port, now_str),
                )
                mid = cur.lastrowid
                cur.execute(
                    "INSERT OR IGNORE INTO monitor_notification (monitor_id, notification_id) VALUES (?, ?)",
                    (mid, DEFAULT_NOTIFICATION_ID),
                )
            changed = True

        # Ensure notification #1 is attached
        if existing and not dry_run:
            has_notif = cur.execute(
                "SELECT 1 FROM monitor_notification WHERE monitor_id = ? AND notification_id = ?",
                (existing["id"], DEFAULT_NOTIFICATION_ID),
            ).fetchone()
            if not has_notif:
                cur.execute(
                    "INSERT INTO monitor_notification (monitor_id, notification_id) VALUES (?, ?)",
                    (existing["id"], DEFAULT_NOTIFICATION_ID),
                )
                changed = True

    if not dry_run and changed:
        conn.commit()
    conn.close()

    if changed and not dry_run:
        print("[RESTART] Restarting uptime-kuma container to reload monitors...")
        subprocess.run(["docker", "restart", "uptime-kuma"], check=True)
    elif not changed:
        print("[OK] Uptime Kuma monitors already in sync.")

    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Uptime Kuma monitors with Casa-poki services")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying kuma.db")
    args = parser.parse_args()
    sync_kuma(dry_run=args.dry_run)
