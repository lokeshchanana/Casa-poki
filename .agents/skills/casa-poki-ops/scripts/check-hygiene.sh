#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
ERRORS=0

echo "Checking Casa-poki secret & Git hygiene in: $REPO_ROOT"

# 1. Check for regular .env files in the repo (should be symlinks to /tank/<service>/.env)
while IFS= read -r -d '' env_file; do
  if [[ ! -L "$env_file" ]]; then
    echo "[ERROR] Regular .env file found (must be symlink to /tank/<service>/.env): $env_file"
    ERRORS=$((ERRORS + 1))
  else
    target="$(readlink -f "$env_file" || true)"
    if [[ "$target" != /tank/* ]]; then
      echo "[WARN] Symlink does not point into /tank/: $env_file -> $target"
    fi
  fi
done < <(find "$REPO_ROOT" -maxdepth 3 -name ".env" -not -path "*/.git/*" -print0)

# 2. Check /tank/*/.env permissions (must be 600)
if [[ -d /tank ]]; then
  for tank_env in /tank/*/.env; do
    [[ -e "$tank_env" ]] || continue
    perms="$(stat -c '%a' "$tank_env" 2>/dev/null || true)"
    if [[ "$perms" != "600" ]]; then
      echo "[ERROR] Expected 600 permissions on $tank_env (found $perms)"
      ERRORS=$((ERRORS + 1))
    fi
  done
fi

# 3. Check git status for staged/untracked secrets or local databases
if command -v git >/dev/null 2>&1 && git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  while IFS= read -r line; do
    file="${line:3}"
    case "$file" in
      *.env|*/.env|*.db|*.sqlite|*.sqlite3|*.pem|*.key)
        echo "[ERROR] Sensitive or local DB file in git status: $file"
        ERRORS=$((ERRORS + 1))
        ;;
    esac
  done < <(git -C "$REPO_ROOT" status --porcelain)
fi

if [[ "$ERRORS" -gt 0 ]]; then
  echo "Hygiene check failed with $ERRORS error(s)."
  exit 1
fi

echo "Hygiene check passed."
