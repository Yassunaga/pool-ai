#!/usr/bin/env bash
# Lock outbound traffic to an allowlist so a worst-case command (incl. prompt
# injection via a Jira task) cannot exfiltrate data or reach arbitrary hosts.
set -euo pipefail

echo "[firewall] applying egress allowlist"

# Reset
iptables -F
iptables -X 2>/dev/null || true
iptables -t nat -F 2>/dev/null || true
iptables -t mangle -F 2>/dev/null || true

# Default: drop everything
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# Loopback + already-established connections
iptables -A INPUT  -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A INPUT  -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# DNS — needed to resolve the allowlisted hostnames below
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# Hosts the automation legitimately needs (HTTPS only)
ALLOWED_HOSTS=(
  # Claude Code backend
  api.anthropic.com
  statsig.anthropic.com
  # GitHub (clone / push / gh pr)
  github.com
  api.github.com
  codeload.github.com
  objects.githubusercontent.com
  # Atlassian / Jira REST
  api.atlassian.com
  # OpenRouter (the agent-under-test calls this when checks exercise the graph)
  openrouter.ai
  # Python + npm registries (uv sync / dependency installs)
  pypi.org
  files.pythonhosted.org
  registry.npmjs.org
)

# The user's Jira site host (set via JIRA_HOST in .env.automation)
[ -n "${JIRA_HOST:-}" ] && ALLOWED_HOSTS+=("${JIRA_HOST}")

# Any extra hosts the user opts into (comma-separated EXTRA_ALLOWED_HOSTS)
if [ -n "${EXTRA_ALLOWED_HOSTS:-}" ]; then
  IFS=',' read -ra _extra <<< "${EXTRA_ALLOWED_HOSTS}"
  for h in "${_extra[@]}"; do [ -n "$h" ] && ALLOWED_HOSTS+=("$h"); done
fi

for host in "${ALLOWED_HOSTS[@]}"; do
  ips="$(getent ahostsv4 "$host" | awk '{print $1}' | sort -u || true)"
  if [ -z "$ips" ]; then
    echo "[firewall] WARN: could not resolve ${host}, skipping"
    continue
  fi
  for ip in $ips; do
    iptables -A OUTPUT -p tcp -d "$ip" --dport 443 -j ACCEPT
  done
done

echo "[firewall] egress restricted to: ${ALLOWED_HOSTS[*]}"
