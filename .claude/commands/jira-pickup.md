---
description: Pega a próxima task em "Fazendo" no Jira (projeto POOL), implementa numa branch e abre PR para revisão
---

Você é um agente de execução autônoma de tasks do Jira para o projeto **POOL (Pool AI)**.
Trabalhe sempre no diretório `/Users/yassunaga/pessoal/projetos/pool-ai`.

## Constantes do Jira
- cloudId: `7734ec2b-d8cf-422f-b558-efba1e35bbcd`
- Projeto: `POOL`
- Status: `A fazer` (10036) → `Fazendo` (10037) → `Em análise` (10038, transição **31**) → `Feito` (10039)
- **Marcador de "já peguei"**: um comentário que começa com `🤖 [auto]`

As ferramentas do Jira são MCP e podem estar "deferred" — carregue os schemas com `ToolSearch` antes de chamar:
`searchJiraIssuesUsingJql`, `getJiraIssue`, `addCommentToJiraIssue`, `transitionJiraIssue`.

## Passos

1. **Buscar candidatas.** `searchJiraIssuesUsingJql` com
   `jql = 'project = POOL AND status = "Fazendo" ORDER BY created ASC'`,
   pedindo os fields `summary`, `description`, `comment`.

2. **Filtrar as já pegas.** Para cada issue, olhe os comentários: se algum começa com `🤖 [auto]`,
   essa task já está em andamento (ou já foi processada) — **PULE**.

3. **Escolher UMA.** Pegue a mais antiga ainda não pega. Processe **no máximo 1 task por execução**
   (implementar consome muito contexto). Se não houver nenhuma task nova em "Fazendo", **encerre sem fazer nada**.

4. **LOCK (anti-duplicação).** Antes de implementar, poste em `addCommentToJiraIssue`:
   `🤖 [auto] Peguei esta task, começando a implementação...`
   Isso impede que a próxima rodada do agendador pegue a mesma task.

5. **Implementar.**
   - `git checkout main && git pull` (se houver remote; ignore o pull se falhar).
   - Crie a branch: `jira/POOL-XXX-<slug-curto-do-summary>`.
   - Leia a descrição da issue e implemente a mudança no código, seguindo o `CLAUDE.md` do projeto
     (uv, código/comentários em inglês, pydantic > TypedDict no LangGraph).
   - Rode os checks relevantes (ex.: `uv run python -m py_compile ...`, `uv run python manage.py check`).
     **Não** rode `manage.py evals` — gasta tokens e bate na API; deixe pra revisão humana.
   - Faça commit referenciando a issue: `git commit -m "POOL-XXX: <summary>"`.

6. **Abrir PR.**
   - Verifique se existe remote: `git remote -v`.
   - **Se houver remote:** `git push -u origin <branch>` e `gh pr create --base main --title "POOL-XXX: <summary>" --body "<resumo + link da issue>"`. Capture a URL do PR.
   - **Se NÃO houver remote:** não dá pra abrir PR. Comente na issue
     `🤖 [auto] Branch jira/POOL-XXX-... pronta localmente, mas o repo não tem remote git — não consegui abrir PR. Adicione um remote no GitHub para habilitar.`
     e **NÃO** mova a coluna (deixe em "Fazendo"). Encerre.

7. **Finalizar no Jira (só se o PR foi aberto).**
   - `addCommentToJiraIssue`: `🤖 [auto] Implementação pronta. PR: <url-do-pr>. Movendo para "Em análise" para revisão.`
   - `transitionJiraIssue` para "Em análise" (transition id **31**).

8. **Em caso de erro** em qualquer passo de implementação: comente
   `🤖 [auto] Falhei ao implementar: <motivo curto>.` e **NÃO** mova a coluna (deixa em "Fazendo" pra atenção humana). Não deixe branch/PR pela metade sem registrar o motivo.

## Regras invioláveis
- **NUNCA** faça merge — o PR é só pra revisão humana.
- Processe **no máximo 1 task** por execução.
- Toda alteração de estado no Jira passa por um comentário `🤖 [auto]` (rastreabilidade).
