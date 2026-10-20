# Roteiro do vídeo — TP3 (até 5 min)

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

Antes de gravar: n8n rodando no Docker, workflow importado, os dois `.env` preenchidos, banco do agente 1
com 2024-03 e 2024-04 importados. O `diagnosticar` leva cerca de 15 s com o Gemini respondendo
normalmente (medido na execução do n8n), então dá para rodar ao vivo; se o Gemini estiver sob limite de uso,
o fallback pode levar minutos — tenha uma execução já concluída aberta no n8n como reserva.

| Tempo | Tela | Fala |
|---|---|---|
| 0:00–0:30 | Antigravity com o repositório aberto e o Claude Code no terminal ao lado | Apresentação; o TP3 transforma o agente em serviço e cria um segundo agente independente |
| 0:30–1:00 | Árvore do repositório: `agent1/`, `agent2/`, `integration/`, `workflows/`, `evaluation/` | Dois projetos separados, cada um com `CLAUDE.md`, `pyproject` e API próprios; nenhum chama o outro |
| 1:00–1:30 | `agent1/CLAUDE.md` e `agent2/CLAUDE.md` lado a lado | Invariantes no topo, seção "fora do escopo", schemas por referência |
| 1:30–2:30 | Terminal 1: `cd agent1 && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001`; terminal 3: `curl /health`, `POST /run perguntar` → 202, `GET /status` → `done` com `valores_citados`; `POST /run diagnosticar 2023-01` → `error` | 202 imediato com `task_id`, `BackgroundTasks`, estados `pending`/`done`/`error`, rastreabilidade mantida |
| 2:30–3:30 | Terminal 2: `cd agent2 && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8002`; `curl -d @integration/exemplos/agent2_run_request.json` → 202 → `done` | O pedido é a saída do diagnóstico do agente 1; o LLM escolhe os cortes, as tools e `montar_plano` fazem as contas; saldo negativo coberto |
| 3:30–4:15 | n8n: executar o workflow, mostrar o loop Aguardar → GET status e o nó final com o resultado | Primeiro workflow: o n8n aciona o agente por HTTP e captura a resposta; no TP4 ele encadeia os dois |
| 4:15–5:00 | `evaluation/avaliacao_final.md` | Tabela de variantes, critério (números corretos e rastreáveis), diagnóstico do assistente v1 → v2 |
