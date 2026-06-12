---
description: (container/headless) Pega a próxima task em "Fazendo" no Jira POOL via REST, implementa e abre PR
---

Versão **headless/container** do `/jira-pickup`. Aqui **NÃO** existe MCP do Jira —
use o helper `automation/jira.sh` (REST) para toda interação com o Jira.
Trabalhe em `/workspace` (raiz do repo).

## Constantes
- Projeto: `POOL`. Status: `A fazer` → `Fazendo` → `Em análise` (transição **31**) → `Feito`.
- Marcador de "já peguei": comentário começando com `🤖 [auto]`.
- Helper: `bash automation/jira.sh {doing | comment KEY "texto" | transition KEY 31}`.

## Passos

1. **Buscar candidatas:** `bash automation/jira.sh doing` → JSON com issues em "Fazendo"
   (campos `summary`, `description`, `comment`).

2. **Filtrar as já pegas:** para cada issue, se algum comentário começa com `🤖 [auto]`, **PULE**.

3. **Escolher UMA** (a mais antiga não pega). **Máx. 1 task por execução.**
   Sem task nova em "Fazendo" → **encerre imediatamente sem fazer nada**.

4. **LOCK:** `bash automation/jira.sh comment POOL-XXX "🤖 [auto] Peguei esta task, começando a implementação..."`

5. **Implementar:**
   - `git checkout main && git pull` (ignore o pull se falhar).
   - Branch: `jira/POOL-XXX-<slug-curto>`.
   - Implemente seguindo o `CLAUDE.md` (uv; código/comentários em inglês; pydantic > TypedDict no LangGraph).
   - Checks leves: `uv run python -m py_compile <arquivos alterados>` e, se fizer sentido, `uv run python manage.py check`.
     **NÃO** rode `manage.py evals` (gasta tokens e bate na API).
   - `git add -A && git commit -m "POOL-XXX: <summary>"`.

6. **Abrir PR:**
   - `git remote -v` para confirmar que há remote.
   - **Com remote:** `git push -u origin <branch>` e
     `gh pr create --base main --title "POOL-XXX: <summary>" --body "<resumo + link da issue>"`. Capture a URL.
   - **Sem remote:** `bash automation/jira.sh comment POOL-XXX "🤖 [auto] Branch pronta localmente, mas o repo não tem remote git — não consegui abrir PR."` e **NÃO** mova a coluna. Encerre.

7. **Finalizar (só se abriu PR):**
   - `bash automation/jira.sh comment POOL-XXX "🤖 [auto] Implementação pronta. PR: <url>. Movendo para Em análise."`
   - `bash automation/jira.sh transition POOL-XXX 31`

8. **Erro na implementação:** `bash automation/jira.sh comment POOL-XXX "🤖 [auto] Falhei: <motivo>."` e **NÃO** mova a coluna.

## Regras invioláveis
- **NUNCA** faça merge. **Máx. 1 task** por execução. Toda mudança de estado no Jira passa por um comentário `🤖 [auto]`.
