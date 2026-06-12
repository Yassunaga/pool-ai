#!/usr/bin/env bash
# Container entrypoint: lock down egress, configure git/gh, then loop the pickup.
set -uo pipefail

cd /workspace

# The repo is bind-mounted and owned by the host user; allow git to operate on it.
git config --global --add safe.directory /workspace

# Configure gh + git to push over HTTPS using GH_TOKEN (from .env.automation).
if [ -n "${GH_TOKEN:-}" ]; then
  gh auth setup-git 2>/dev/null || true
fi

# Egress firewall first — before any agent code runs. Needs NET_ADMIN.
if [ "${FIREWALL:-1}" = "1" ]; then
  bash /workspace/automation/init-firewall.sh || {
    echo "[entrypoint] FATAL: firewall init failed; refusing to run unsandboxed" >&2
    exit 1
  }
fi

# Allow `docker compose run jira-agent <cmd>` to override the loop (e.g. a one-off run).
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

INTERVAL="${RUN_INTERVAL:-900}"
echo "[entrypoint] starting pickup loop (interval=${INTERVAL}s)"
while true; do
  bash /workspace/automation/run-pickup.sh || echo "[entrypoint] run failed, continuing"
  sleep "$INTERVAL"
done
