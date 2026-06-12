# Isolated runner for the Jira "Fazendo" pickup automation.
# Claude Code runs headless inside this container with --dangerously-skip-permissions,
# which is safe ONLY because (a) the container is disposable and (b) init-firewall.sh
# locks egress to an allowlist. Never run skip-permissions like this on the host.
FROM node:20-bookworm

# Base tooling: git/gh for PRs, jq/curl for the Jira REST helper,
# iptables/dnsutils for the egress firewall, sudo kept for parity with devcontainers.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl jq ca-certificates gnupg iptables dnsutils sudo \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# uv (the project's package manager) and the Claude Code CLI
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -sf /root/.local/bin/uv /usr/local/bin/uv
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /workspace
# Scripts are bind-mounted from the repo at runtime (see docker-compose.yml),
# so no COPY is needed — edits take effect without a rebuild.
ENTRYPOINT ["bash", "/workspace/automation/entrypoint.sh"]
