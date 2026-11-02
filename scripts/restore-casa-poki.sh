#!/usr/bin/env bash
# ==============================================================================
# Casa-poki Full Bare-Metal Disaster Recovery Script
# Target OS: Fresh Ubuntu Server (22.04 LTS or 24.04 LTS)
# ==============================================================================
set -euo pipefail

TARGET_USER="lokesh"
REPO_URL="https://github.com/lokeshchanana/Casa-poki.git"
REPO_DIR="/home/${TARGET_USER}/Casa-poki"
NFS_SERVER="192.168.1.250"

# Colors for logging
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }

if [ "$(id -u)" -ne 0 ]; then
  log_err "This restore script must be executed as root (or with sudo)."
  exit 1
fi

echo "========================================================================"
echo "          CASA-POKI COMPLETE BARE-METAL RESTORATION ENGINE              "
echo "========================================================================"

# ------------------------------------------------------------------------------
# STEP 1: Ensure Target User Exists
# ------------------------------------------------------------------------------
log_info "Step 1: Checking target user (${TARGET_USER})..."
if ! id "${TARGET_USER}" >/dev/null 2>&1; then
  log_info "Creating user ${TARGET_USER}..."
  useradd -m -s /bin/bash -G sudo "${TARGET_USER}"
  log_ok "User ${TARGET_USER} created."
else
  log_ok "User ${TARGET_USER} exists."
fi

# ------------------------------------------------------------------------------
# STEP 2: Install Essential Packages & Prerequisites
# ------------------------------------------------------------------------------
log_info "Step 2: Installing system packages (ZFS, Docker, Git, NFS, tools)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  git \
  rsync \
  jq \
  nfs-common \
  zfsutils-linux \
  docker.io \
  docker-compose-plugin

systemctl enable --now docker
usermod -aG docker "${TARGET_USER}"
log_ok "System packages installed and Docker daemon active."

# ------------------------------------------------------------------------------
# STEP 3: Setup or Recover ZFS Tank
# ------------------------------------------------------------------------------
log_info "Step 3: Checking ZFS pool 'tank'..."
if zpool list tank >/dev/null 2>&1; then
  log_ok "ZFS pool 'tank' is already imported and online."
else
  # Check if existing pool can be imported
  if zpool import 2>/dev/null | grep -q "pool: tank"; then
    log_info "Existing pool 'tank' found on local storage. Importing..."
    zpool import -f tank
    log_ok "Pool 'tank' imported successfully."
  else
    log_warn "No local pool 'tank' found. Checking NFS server ${NFS_SERVER}..."
    read -rp "Would you like to (1) Replicate ZFS from NFS server ${NFS_SERVER}, or (2) Mount over NFS, or (3) Create empty tank on disk? [1/2/3]: " TANK_CHOICE
    case "${TANK_CHOICE}" in
      1)
        read -rp "Enter target disk device for new local tank (e.g. /dev/sda): " TANK_DISK
        if [ ! -b "${TANK_DISK}" ]; then
          log_err "Device ${TANK_DISK} is not a valid block device!"
          exit 1
        fi
        zpool create -f -o ashift=12 tank "${TANK_DISK}"
        log_info "Finding latest snapshot on ${NFS_SERVER}..."
        LATEST_SNAP=$(ssh "root@${NFS_SERVER}" "zfs list -H -o name -t snapshot -r nfspool | grep -v '/' | tail -n 1" || echo "nfspool@initial-sync")
        log_info "Receiving ZFS snapshot stream (${LATEST_SNAP}) from ${NFS_SERVER}..."
        ssh "root@${NFS_SERVER}" "zfs send -R ${LATEST_SNAP}" | zfs receive -F -d tank
        log_ok "ZFS pool 'tank' restored from NFS server."
        ;;
      2)
        mkdir -p /tank
        mount -t nfs -o proto=tcp,port=2049 "${NFS_SERVER}:/nfspool" /tank
        echo "${NFS_SERVER}:/nfspool /tank nfs _netdev,nofail,bg,rw 0 0" >> /etc/fstab
        log_ok "/tank mounted over NFS."
        ;;
      3)
        read -rp "Enter target disk device for empty tank (e.g. /dev/sda): " TANK_DISK
        zpool create -f -o ashift=12 tank "${TANK_DISK}"
        log_ok "Empty ZFS pool 'tank' created."
        ;;
      *)
        log_err "Invalid selection. Aborting ZFS recovery."
        exit 1
        ;;
    esac
  fi
fi

# Ensure datasets mount points are active
zfs mount -a || true

# ------------------------------------------------------------------------------
# STEP 4: Clone Casa-poki Repository
# ------------------------------------------------------------------------------
log_info "Step 4: Ensuring repository code at ${REPO_DIR}..."
if [ ! -d "${REPO_DIR}/.git" ]; then
  mkdir -p "$(dirname "${REPO_DIR}")"
  su - "${TARGET_USER}" -c "git clone ${REPO_URL} ${REPO_DIR}"
  log_ok "Repository cloned to ${REPO_DIR}."
else
  log_ok "Repository already exists at ${REPO_DIR}."
fi

# ------------------------------------------------------------------------------
# STEP 5: Re-link All Secrets from /tank/<service>/.env
# ------------------------------------------------------------------------------
log_info "Step 5: Verifying and re-linking service secrets from /tank..."

SERVICES=("twenty" "postgres-db" "relaticle" "monitor" "mic-bridge" "cloudflared")

for s in "${SERVICES[@]}"; do
  if [ -f "/tank/${s}/.env" ]; then
    rm -f "${REPO_DIR}/${s}/.env"
    ln -sf "/tank/${s}/.env" "${REPO_DIR}/${s}/.env"
    log_ok "Linked /tank/${s}/.env -> ${REPO_DIR}/${s}/.env"
  else
    log_warn "Secret /tank/${s}/.env not found. Please review .env.example template."
  fi
done

# Special case for ai/n8n
if [ -f "/tank/n8n/.env" ]; then
  rm -f "${REPO_DIR}/ai/n8n/.env"
  ln -sf "/tank/n8n/.env" "${REPO_DIR}/ai/n8n/.env"
  log_ok "Linked /tank/n8n/.env -> ${REPO_DIR}/ai/n8n/.env"
fi

# ------------------------------------------------------------------------------
# STEP 6: Recreate Docker Networks
# ------------------------------------------------------------------------------
log_info "Step 6: Creating required external Docker networks..."
for net in "postgres-network" "relaticle-internal"; do
  if ! docker network inspect "${net}" >/dev/null 2>&1; then
    docker network create "${net}"
    log_ok "Created Docker network: ${net}"
  else
    log_ok "Docker network exists: ${net}"
  fi
done

# ------------------------------------------------------------------------------
# STEP 7: Restore Antigravity Instance
# ------------------------------------------------------------------------------
log_info "Step 7: Restoring Antigravity CLI and daemon..."
USER_HOME="/home/${TARGET_USER}"

if [ -f "/tank/antigravity-backup/agy" ]; then
  mkdir -p "${USER_HOME}/.local/bin"
  cp -a /tank/antigravity-backup/agy "${USER_HOME}/.local/bin/agy"
  chmod +x "${USER_HOME}/.local/bin/agy"
  log_ok "Restored agy binary to ${USER_HOME}/.local/bin/agy."
fi

if [ -f "/tank/antigravity-backup/settings.json" ]; then
  mkdir -p "${USER_HOME}/.gemini/antigravity-cli"
  cp -a /tank/antigravity-backup/settings.json "${USER_HOME}/.gemini/antigravity-cli/settings.json"
  log_ok "Restored Antigravity settings.json."
fi

if [ -f "/tank/antigravity-backup/antigravity-cli-daemon.service" ]; then
  mkdir -p "${USER_HOME}/.config/systemd/user"
  cp -a /tank/antigravity-backup/antigravity-cli-daemon.service "${USER_HOME}/.config/systemd/user/antigravity-cli-daemon.service"
  
  # Enable user lingering so background daemon runs across sessions
  loginctl enable-linger "${TARGET_USER}"
  
  # Start and enable user systemd service
  TARGET_UID=$(id -u "${TARGET_USER}")
  sudo -u "${TARGET_USER}" XDG_RUNTIME_DIR="/run/user/${TARGET_UID}" systemctl --user daemon-reload || true
  sudo -u "${TARGET_USER}" XDG_RUNTIME_DIR="/run/user/${TARGET_UID}" systemctl --user enable --now antigravity-cli-daemon.service || true
  log_ok "Antigravity CLI daemon enabled and running."
fi

chown -R "${TARGET_USER}:${TARGET_USER}" "${USER_HOME}/.local" "${USER_HOME}/.gemini" "${USER_HOME}/.config" 2>/dev/null || true

# ------------------------------------------------------------------------------
# STEP 8: Launch Docker Containers in Dependency Order
# ------------------------------------------------------------------------------
log_info "Step 8: Bringing up Docker compose services..."

COMPOSE_DIRS=(
  "postgres-db"
  "twenty"
  "relaticle"
  "ai/n8n"
  "monitor"
  "ollama"
  "adguard"
  "habridge"
  "nginx"
  "cloudflared"
  "real-estate"
  "checkin"
  "agents"
)

for d in "${COMPOSE_DIRS[@]}"; do
  TARGET_COMPOSE_DIR="${REPO_DIR}/${d}"
  if [ -d "${TARGET_COMPOSE_DIR}" ]; then
    log_info "Starting service: ${d}..."
    (cd "${TARGET_COMPOSE_DIR}" && docker compose up -d) || log_warn "Warning starting ${d}"
  fi
done

# ------------------------------------------------------------------------------
# STEP 9: Enable Nightly Backup Timer
# ------------------------------------------------------------------------------
log_info "Step 9: Installing nightly replication timer..."
if [ -f "${REPO_DIR}/scripts/casa-poki-sync.sh" ]; then
  cp -a "${REPO_DIR}/scripts/casa-poki-sync.sh" /usr/local/bin/casa-poki-sync.sh
  chmod +x /usr/local/bin/casa-poki-sync.sh
  cp -a "${REPO_DIR}/scripts/systemd/casa-poki-sync.service" /etc/systemd/system/
  cp -a "${REPO_DIR}/scripts/systemd/casa-poki-sync.timer" /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable --now casa-poki-sync.timer
  log_ok "Nightly replication timer enabled."
fi

echo "========================================================================"
log_ok "CASA-POKI RESTORATION COMPLETED SUCCESSFULLY!"
echo "========================================================================"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
