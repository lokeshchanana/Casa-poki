#!/usr/bin/env bash
# ==============================================================================
# Casa-poki Automated Nightly ZFS Tank Replication to NFS Server (192.168.1.250)
# ==============================================================================
set -euo pipefail

REMOTE_HOST="192.168.1.250"
REMOTE_USER="root"
REMOTE_POOL="nfspool"
LOCAL_POOL="tank"
LOG_FILE="/var/log/casa-poki-sync.log"
RETENTION_DAYS=14
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
NEW_SNAP="${LOCAL_POOL}@daily-${TIMESTAMP}"

exec >> >(tee -a "${LOG_FILE}") 2>&1

echo "========================================================================"
echo "[$(date -Is)] Starting Casa-poki ZFS Tank Nightly Replication"
echo "========================================================================"

# 1. Update Antigravity binary & config on tank
if [ -d "/home/lokesh/.local/bin" ] && [ -f "/home/lokesh/.local/bin/agy" ]; then
  mkdir -p /tank/antigravity-backup
  cp -a /home/lokesh/.local/bin/agy /tank/antigravity-backup/
  if [ -f "/home/lokesh/.gemini/antigravity-cli/settings.json" ]; then
    cp -a /home/lokesh/.gemini/antigravity-cli/settings.json /tank/antigravity-backup/
  fi
  if [ -f "/home/lokesh/.config/systemd/user/antigravity-cli-daemon.service" ]; then
    cp -a /home/lokesh/.config/systemd/user/antigravity-cli-daemon.service /tank/antigravity-backup/
  fi
  chown -R lokesh:lokesh /tank/antigravity-backup
  chmod 700 /tank/antigravity-backup
  echo "[$(date -Is)] Antigravity files backed up to /tank/antigravity-backup"
fi

# 2. Check remote host connectivity
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${REMOTE_USER}@${REMOTE_HOST}" "true" 2>/dev/null; then
  echo "[$(date -Is)] ERROR: Cannot connect to remote host ${REMOTE_HOST} via SSH." >&2
  exit 1
fi

# 3. Find latest snapshot on remote destination
echo "[$(date -Is)] Finding latest common snapshot between ${LOCAL_POOL} and ${REMOTE_HOST}:${REMOTE_POOL}/${LOCAL_POOL}..."
REMOTE_SNAPS=$(ssh -o BatchMode=yes "${REMOTE_USER}@${REMOTE_HOST}" "zfs list -H -o name -t snapshot -r ${REMOTE_POOL}/${LOCAL_POOL}" || true)

LATEST_COMMON=""
if [ -n "${REMOTE_SNAPS}" ]; then
  LOCAL_SNAPS=$(zfs list -H -o name -t snapshot -r "${LOCAL_POOL}" | awk -F'@' '{print $2}' | sort -u)
  for s in $(echo "${REMOTE_SNAPS}" | awk -F'@' '{print $2}' | sort -u | tac); do
    if echo "${LOCAL_SNAPS}" | grep -qx "${s}"; then
      LATEST_COMMON="${s}"
      break
    fi
  done
fi

# 4. Create new recursive snapshot
echo "[$(date -Is)] Creating recursive local snapshot: ${NEW_SNAP}"
zfs snapshot -r "${NEW_SNAP}"

# 5. Send stream
if [ -n "${LATEST_COMMON}" ]; then
  echo "[$(date -Is)] Sending incremental stream from @${LATEST_COMMON} to @daily-${TIMESTAMP}..."
  zfs send -R -I "${LOCAL_POOL}@${LATEST_COMMON}" "${NEW_SNAP}" | \
    ssh -o Compression=no -c aes128-gcm@openssh.com "${REMOTE_USER}@${REMOTE_HOST}" "zfs receive -F -d ${REMOTE_POOL}"
else
  echo "[$(date -Is)] No common snapshot found. Sending full recursive stream ${NEW_SNAP}..."
  zfs send -R "${NEW_SNAP}" | \
    ssh -o Compression=no -c aes128-gcm@openssh.com "${REMOTE_USER}@${REMOTE_HOST}" "zfs receive -F -d ${REMOTE_POOL}"
fi

# 6. Ensure NFS export is active on remote
echo "[$(date -Is)] Ensuring NFS export configuration on remote pool..."
ssh -o BatchMode=yes "${REMOTE_USER}@${REMOTE_HOST}" "zfs set sharenfs='rw=@192.168.1.0/24,no_subtree_check,sync,no_root_squash' ${REMOTE_POOL}/${LOCAL_POOL} || true"

# 7. Prune snapshots older than RETENTION_DAYS
CUTOFF_SEC=$(date -d "${RETENTION_DAYS} days ago" +%s)
echo "[$(date -Is)] Pruning daily snapshots older than ${RETENTION_DAYS} days..."

for snap in $(zfs list -H -o name,creation -t snapshot -p -r "${LOCAL_POOL}" | grep '@daily-' | awk -v cutoff="${CUTOFF_SEC}" '$2 < cutoff {print $1}'); do
  echo "Pruning local snapshot: ${snap}"
  zfs destroy "${snap}" || true
done

REMOTE_PRUNE_CMD=$(cat << 'EOF_PRUNE'
CUTOFF_SEC=$(date -d "14 days ago" +%s)
for snap in $(zfs list -H -o name,creation -t snapshot -p -r nfspool/tank | grep '@daily-' | awk -v cutoff="${CUTOFF_SEC}" '$2 < cutoff {print $1}'); do
  echo "Pruning remote snapshot: ${snap}"
  zfs destroy "${snap}" || true
done
EOF_PRUNE
)
ssh -o BatchMode=yes "${REMOTE_USER}@${REMOTE_HOST}" "bash -c '${REMOTE_PRUNE_CMD}'" || true

echo "========================================================================"
echo "[$(date -Is)] Nightly ZFS Tank Replication Finished Successfully!"
echo "========================================================================"
