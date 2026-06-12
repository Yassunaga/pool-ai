#!/usr/bin/env bash
# Minimal Jira Cloud REST helper for the headless container (no MCP available here).
# Auth via JIRA_EMAIL + JIRA_API_TOKEN (Atlassian API token, Basic auth).
#
# Usage:
#   jira.sh doing                      # issues in "Fazendo" (POOL), JSON
#   jira.sh comment POOL-12 "text"     # add a comment
#   jira.sh transition POOL-12 31      # run transition by id (31 = "Em análise")
set -euo pipefail

: "${JIRA_BASE_URL:?set JIRA_BASE_URL}"
: "${JIRA_EMAIL:?set JIRA_EMAIL}"
: "${JIRA_API_TOKEN:?set JIRA_API_TOKEN}"

API="${JIRA_BASE_URL%/}/rest/api/3"
USERPASS="${JIRA_EMAIL}:${JIRA_API_TOKEN}"

cmd="${1:-}"; shift || true
case "$cmd" in
  doing)
    curl -fsS --user "$USERPASS" -G "${API}/search/jql" \
      --data-urlencode 'jql=project = POOL AND status = "Fazendo" ORDER BY created ASC' \
      --data-urlencode 'fields=summary,description,comment' \
      --data-urlencode 'maxResults=20'
    ;;
  comment)
    key="${1:?issue key}"; text="${2:?comment text}"
    body="$(jq -n --arg t "$text" \
      '{body:{type:"doc",version:1,content:[{type:"paragraph",content:[{type:"text",text:$t}]}]}}')"
    curl -fsS --user "$USERPASS" -X POST \
      -H 'Content-Type: application/json' \
      "${API}/issue/${key}/comment" -d "$body"
    ;;
  transition)
    key="${1:?issue key}"; tid="${2:?transition id}"
    curl -fsS --user "$USERPASS" -X POST \
      -H 'Content-Type: application/json' \
      "${API}/issue/${key}/transitions" \
      -d "{\"transition\":{\"id\":\"${tid}\"}}"
    ;;
  *)
    echo "usage: jira.sh {doing | comment KEY TEXT | transition KEY TRANSITION_ID}" >&2
    exit 2
    ;;
esac
