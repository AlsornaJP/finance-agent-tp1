# CLAUDE.md — Agente 2: Planejador de Metas

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

## Responsabilidade
Dada uma meta de poupança com prazo, a renda e o saldo de um mês de referência e os gastos desse mês por categoria, diz se a meta é viável, propõe cortes mensais por categoria e projeta o acumulado mês a mês. Exposto como serviço REST (FastAPI, porta 8002). Projeto de Bloco — Agentes de IA (TP3), OpenAI Agents SDK.

## Invariantes (não mudar sem discutir)
- O LLM nunca calcula: toda aritmética fica em `planner/simulacao.py` e chega ao LLM pelas tools (`planner/tools.py`)
- O LLM só escolhe onde cortar e redige o resumo; os números do `PlanoDeMeta` são recalculados por `montar_plano` sobre os cortes propostos
- Todo número do plano é rastreável à tool de origem (`valores_citados`)
- A sobra atual do mês (`saldo`) conta para a meta; com saldo negativo, os cortes cobrem primeiro o déficit
- Saída do agente via `output_type` (`PropostaDePlano`), nunca string parseada manualmente
- Só modelos Gemini: o agente usa tools e `output_type` juntos, combinação que os Gemma ignoram

## Fora do escopo deste projeto
- O agente de finanças (agente 1) e a orquestração entre agentes não são assunto daqui
- Este projeto não lê banco de outro agente, não importa código dele e não o chama por HTTP: os gastos chegam no corpo do `/run`
- Só meta de poupança com prazo; outros tipos de objetivo não são suportados

## Estrutura
- `planner/schema.py` — pedido (`PedidoPlano`), resultados intermediários e saída (`PlanoDeMeta`)
- `planner/simulacao.py` — meses do plano, necessidade e simulação de cortes (determinístico)
- `planner/tools.py` — `calcular_necessidade_da_meta` e `simular_cortes`, com `ContextoPlanejamento`
- `planner/agente.py`, `planner/prompts.py` — construção do agente e instructions
- `planner/planejamento.py` — `montar_plano` (puro) e `planejar` (roda o agente e salva o log)
- `planner/runner.py`, `planner/config.py` — execução com fallback entre os modelos de `GEMINI_MODELS`
- `planner/execution_log.py`, `planner/rastreio.py` — log em Markdown e chamadas de tool
- `api/` — FastAPI: `main.py` (rotas) e `tarefas.py` (registro de tarefas)
- `prompts/` — `planejador_v2.md` em uso e `planejador_v1.md` como registro (anatomia de 4 componentes); logs em `prompts/outputs/`
- `tests/` — `pytest` de schemas, simulação, plano, tools e API

## Tools
- `calcular_necessidade_da_meta()` → meses disponíveis, economia mensal necessária, sobra atual, valor a cobrir com cortes
- `simular_cortes(cortes)` → economia mensal planejada, projeção mês a mês, `atinge_meta`, diferença para a meta; cortes inválidos voltam como texto para o LLM corrigir

## API
| Método | Rota | Resposta |
|---|---|---|
| `POST` | `/run` | 202 `{task_id, status: "pending"}`; 422 se o corpo for inválido |
| `GET` | `/status/{task_id}` | 200 `{task_id, status, resultado, erro}`; 404 se o id não existir |
| `GET` | `/health` | `{"status": "ok", "agente": "agent2-planejador"}` |

Estados: `pending` → `done` | `error`. Tarefas ficam em memória e executam uma por vez.

Corpo do `/run`: `PedidoPlano` em `planner/schema.py` — `meta {valor, prazo}`, `mes_referencia`, `total_mes {renda, total_gasto, saldo}`, `gastos_por_categoria [{categoria, valor_total}]`. Campos extras são ignorados, para aceitar a saída de outro serviço sem transformação. Resultado em `done`: `{plano: PlanoDeMeta, log}`. Contrato completo: `../integration/contrato_api.md`.

## Stack e ambiente
- Python 3.12 + OpenAI Agents SDK, Pydantic 2, FastAPI, Uvicorn, uv
- `.env` próprio (nunca commitado; nomes em `.env.example`): `GOOGLE_API_KEY`, `GEMINI_MODELS` (lista separada por vírgula), `GOOGLE_BASE_URL` (opcional), `OPENAI_AGENTS_DISABLE_TRACING=1`

## Comandos (sempre de dentro de `agent2/`)
- `uv sync`
- `.venv/bin/pytest -q`
- `.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8002`

## Domínio — categorias fixas
`Alimentação`, `Transporte`, `Moradia`, `Saúde`, `Educação`, `Lazer`, `Compras`, `Serviços/Assinaturas`, `Não identificado`

Prioridade de cortes: `Lazer`, `Compras`, `Serviços/Assinaturas` → `Alimentação`, `Transporte`, `Não identificado` → `Moradia`, `Saúde`, `Educação`.

## Convenções
- Evite comentários no código; use nomes de variáveis e funções claros, em português
- Toda execução gera log em `prompts/outputs/`
- Testes com `pytest`; na API, o fluxo de LLM é substituído por função falsa via `criar_app(executar)`
- Execuções reais de LLM só uma vez por entrega e em segundo plano; nunca repetir no ciclo de desenvolvimento
