# Casa-poki Disaster Recovery Guide

This repository contains the complete configuration, compose setups, and automation scripts to recover all Casa-poki services from scratch in the event of hardware or server failure.

---

## 1. Architecture Overview

- **Code Repository**: Hosted on GitHub (`lokeshchanana/Casa-poki.git`). Contains all Docker Compose configurations, overrides, and recovery scripts. Excludes all secrets and live databases.
- **Persistent Data & Secrets (`/tank`)**:
  - Pool: ZFS pool `tank`
  - Secrets: Stored directly on `/tank/<service>/.env` with `0600` permissions.
  - Symlinks: Linked from `./<service>/.env -> /tank/<service>/.env`.
- **Secondary ZFS / NFS Mirror**:
  - Remote ZFS pool: `nfspool`
  - Nightly snapshot and incremental replication runs automatically via `casa-poki-sync.timer` at 02:00 AM.
  - NFS export: Exported to the authorized local LAN subnet for emergency mounting.

---

## 2. One-Command Restoration on Fresh Ubuntu Server

On a freshly installed Ubuntu LTS machine:

```bash
# 1. Download and run the restoration engine as root
curl -fsSL https://raw.githubusercontent.com/lokeshchanana/Casa-poki/main/scripts/restore-casa-poki.sh | sudo bash
```

Or execute directly from the cloned repository:

```bash
sudo ./scripts/restore-casa-poki.sh
```

### What the Script Automatically Restores:
1. **System Tools**: Installs `zfsutils-linux`, `docker.io`, `docker-compose-plugin`, `nfs-common`, `git`, `rsync`, and dependencies.
2. **User & Permissions**: Configures target user with Docker and administrative privileges.
3. **ZFS Tank Recovery**:
   - Detects and imports existing physical ZFS drive (`zpool import -f tank`), OR
   - Replicates `nfspool` from the backup server, OR
   - Mounts the backup pool over NFS.
4. **Secrets & Symlinks**: Automatically re-links all `.env` files from `/tank/<service>/.env` into the respective repository directories.
5. **Docker Networks**: Recreates `postgres-network` and `relaticle-internal`.
6. **Antigravity CLI**: Restores `agy` binary to `~/.local/bin/agy`, restores `settings.json`, configures user linger, and starts the systemd daemon.
7. **Containers**: Brings up all services in dependency order (`postgres`, `twenty`, `relaticle`, `n8n`, `monitor`, `ollama`, `nginx`, `cloudflared`, `real-estate`, etc.).
8. **Nightly Sync**: Installs and activates `casa-poki-sync.timer`.

---

## 3. Useful Maintenance Commands

### Trigger Manual ZFS Replication to Secondary Host:
```bash
sudo /usr/local/bin/casa-poki-sync.sh
```

### Check Nightly Sync Timer Status:
```bash
systemctl status casa-poki-sync.timer
journalctl -u casa-poki-sync.service -n 50 --no-pager
```

### Inspect Remote Snapshots on Backup Server:
```bash
ssh root@<BACKUP_HOST_IP> 'zfs list -t snapshot -r nfspool'
```

### Mount Backup Pool Over NFS Manually:
```bash
sudo mkdir -p /tank
sudo mount -t nfs <BACKUP_HOST_IP>:/nfspool /tank
```
