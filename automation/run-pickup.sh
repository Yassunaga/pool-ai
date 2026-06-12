#!/usr/bin/env bash
# One pickup run: ask Claude Code to execute the container-side workflow once.
set -uo pipefail
cd /workspace

echo "[pickup] $(date -u +%FT%TZ) starting run"
# --dangerously-skip-permissions is safe here ONLY because we are inside the
# firewalled, disposable container set up by entrypoint.sh / init-firewall.sh.
claude -p "/jira-pickup-ci" --dangerously-skip-permissions
status=$?
echo "[pickup] $(date -u +%FT%TZ) finished (exit ${status})"
exit "${status}"
