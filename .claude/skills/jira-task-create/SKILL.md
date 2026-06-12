---
name: jira-task-create
description: Cria issues no Jira do projeto POOL (Pool AI) a partir de uma descrição em linguagem natural. Use SEMPRE que o usuário pedir para criar/abrir/registrar uma task, tarefa, bug, história, card ou "issue" no Jira — mesmo que ele não diga "Jira" explicitamente, desde que o contexto seja registrar trabalho a fazer no projeto POOL. Exemplos de gatilho: "cria uma task pra...", "abre um bug no Jira sobre...", "registra uma história pra implementar...", "joga isso no board". NÃO use para pegar/implementar tasks existentes (isso é o /jira-pickup) nem para editar issues já criadas.
---

# Criar task no Jira (POOL)

Transforma um pedido em linguagem natural numa issue bem-formada no Jira da Pool AI.
O fluxo é: **entender → montar rascunho → confirmar com o humano → criar → devolver o link.**

## Constantes do projeto

- **cloudId:** `7734ec2b-d8cf-422f-b558-efba1e35bbcd`
- **projectKey:** `POOL`
- **Tipos de issue disponíveis:** `Tarefa` (padrão), `Bug`, `História`, `Função`, `Epic`, `Subtask`
- **Coluna de destino:** issues novas caem em **"A fazer"** (o backlog) — é o padrão, **não** aplique transição.
- **Idioma do conteúdo:** o board é em **português**. Título e descrição da issue vão em português (mesmo que o código do projeto seja em inglês).

As ferramentas do Jira são MCP e podem estar "deferred". Carregue o schema antes de chamar:

```
ToolSearch: select:mcp__136ceb69-1426-4cff-9010-4b90f0822309__createJiraIssue
```

Se em algum momento precisar do account id de uma pessoa (ex.: o usuário pedir explicitamente para atribuir a alguém), carregue também `lookupJiraAccountId`.

## Passos

### 1. Entender o pedido e inferir o tipo

Leia o que o usuário descreveu e decida o **tipo de issue** pelo conteúdo:

- **Bug** — algo está quebrado / comportamento errado / "tá dando erro", "não funciona", "deveria fazer X mas faz Y".
- **História** — funcionalidade nova relativamente grande, voltada ao usuário/negócio ("como cliente, quero...").
- **Tarefa** — qualquer trabalho técnico ou pontual que não é claramente bug nem história. **É o default na dúvida.**
- **Epic / Função / Subtask** — só se o usuário pedir explicitamente.

Não pergunte o tipo se der pra inferir com confiança razoável; o humano confirma no rascunho de qualquer forma.

### 2. Montar o rascunho

**Título (summary):** uma linha, imperativa e específica, sem ponto final. Bom: "Avaliar mídia (áudio/imagem) no harness de evals". Ruim: "Evals".

**Descrição:** use markdown com este template (omita uma seção se realmente não houver conteúdo — não preencha com "N/A" à toa):

```markdown
**Contexto**
Por que isso existe / qual o problema ou a oportunidade.

**O que fazer**
O escopo concreto da mudança, em bullets se ajudar.

**Critérios de aceite**
- [ ] Condição verificável 1
- [ ] Condição verificável 2
```

Preencha o template com o que o usuário deu. Se faltar algo importante (ex.: não dá pra escrever nenhum critério de aceite porque o escopo está vago), **faça 1–2 perguntas curtas** antes de montar o rascunho — não invente requisitos de negócio. Detalhes técnicos óbvios você pode inferir do `CLAUDE.md` do projeto.

### 3. Confirmar com o humano

Mostre o rascunho assim, e **espere o OK antes de criar**:

```
Vou criar esta issue no POOL:

  Tipo:   Tarefa
  Título: <summary>
  Descrição:
  <descrição renderizada>

Confirma? (ou me diga o que ajustar)
```

Se o usuário pedir ajustes, edite e mostre de novo. Só prossiga após confirmação explícita ("pode criar", "isso", "ok", etc.).

### 4. Criar a issue

Chame `createJiraIssue` com:

- `cloudId`: a constante acima
- `projectKey`: `POOL`
- `issueTypeName`: o tipo decidido (ex.: `Tarefa`)
- `summary`: o título
- `description`: a descrição em markdown
- `contentFormat`: `markdown`

**Não** preencha assignee por padrão (issues nascem sem responsável). Só atribua se o usuário pedir — aí use `lookupJiraAccountId` para achar o `accountId` e passe em `assignee_account_id`.

Se o usuário mencionar um epic-pai ("dentro do epic POOL-X"), passe `parent: "POOL-X"`.

### 5. Devolver o resultado

Confirme com a chave e o link clicável:

```
✅ Criada POOL-123 — <título>
https://<seu-site>.atlassian.net/browse/POOL-123
```

Use a `key` e a URL que o `createJiraIssue` retornar (não invente o número). Se a chamada falhar, mostre o erro real e o rascunho, para o humano não perder o que foi escrito.

## Regras

- **Uma issue por pedido**, a menos que o usuário peça várias explicitamente — nesse caso, monte os rascunhos de todas e confirme em bloco antes de criar.
- **Nunca** mova a issue de coluna nem atribua responsável sem o usuário pedir.
- Título e descrição **em português**; objetivos e específicos.
- Na dúvida sobre tipo, use **Tarefa**.
