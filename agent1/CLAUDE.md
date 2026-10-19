# CLAUDE.md — Agente 1: Finanças Pessoais

## Responsabilidade
Importa extratos bancários em CSV para um SQLite, classifica as transações, responde perguntas sobre os gastos com tools e memória, e gera diagnósticos mensais em etapas. Exposto como serviço REST (FastAPI, porta 8001). Projeto de Bloco — Agentes de IA (TP1 a TP3), OpenAI Agents SDK.

## Invariantes (não mudar sem discutir)
- O LLM nunca calcula: toda aritmética fica em `agent/database.py` e chega ao LLM por tools (`agent/tools.py`)
- Todo número citado em resposta deve ser rastreável à tool de origem (`valores_citados`)
- Leitura de CSV é determinística (Python); o LLM só classifica as transações
- Fluxos orquestrados por código, sem handoffs entre agentes
- Saída final de agente usa `output_type` (schema Pydantic), nunca string parseada manualmente
- A API só adapta HTTP para os fluxos existentes: lógica de negócio fica em `agent/`, nunca em `api/`

## Fora do escopo deste projeto
- O planejador de metas (agente 2) e a orquestração entre agentes não são assunto daqui
- Este projeto não importa código de outro agente, não chama outro agente e não expõe seu banco a ninguém
- A integração acontece só pelo n8n, consumindo os endpoints HTTP abaixo

## Estrutura
- `agent/` — agentes (`agents.py`), runner com fallback de provedores (`runner.py`), tools, banco, RAG, logs e fluxos (`importacao.py`, `consulta.py`, `diagnostico.py`)
- `api/` — FastAPI: `main.py` (rotas), `schemas.py` (pedidos do `/run`), `fluxos.py` (pedido → fluxo), `tarefas.py` (registro de tarefas)
- `knowledge/` — documento do RAG (guia de orçamento)
- `data/` — banco SQLite local e CSVs recebidos pela API (não versionado)
- `evaluation/` — gabarito, métricas, avaliação A/B e ciclo PRRR
- `prompts/` — instructions estruturadas (anatomia de 4 componentes) e logs de execução em `prompts/outputs/`
- `spec/` — especificação do TP1
- `tests/` — testes `pytest` da parte determinística e da API

## Tools do assistente
`gasto_total_mes`, `gastos_por_categoria`, `comparar_meses`, `transacoes_atipicas`, `listar_transacoes`, `buscar_conhecimento` — todas em `agent/tools.py`, todas devolvem JSON calculado em Python.

## API
| Método | Rota | Resposta |
|---|---|---|
| `POST` | `/run` | 202 `{task_id, status: "pending"}`; 422 se o corpo for inválido |
| `GET` | `/status/{task_id}` | 200 `{task_id, status, resultado, erro}`; 404 se o id não existir |
| `GET` | `/health` | `{"status": "ok", "agente": "agent1-financas"}` |

Estados: `pending` → `done` | `error`. Tarefas ficam em memória (reiniciar o serviço apaga) e executam uma por vez.

Corpo do `/run` (união discriminada por `acao`, ver `api/schemas.py`):
- `importar` — `csv` (conteúdo do arquivo) → `{log, meses_disponiveis}`
- `perguntar` — `pergunta`, `sessao_id` (padrão `"api"`) → `{resposta: RespostaFinanceira, log}`
- `diagnosticar` — `mes` (`AAAA-MM`) → `{diagnostico: DiagnosticoMensal, total_mes, gastos_por_categoria, log}`

Schemas de saída: `agent/schema.py`. Contrato completo: `../integration/contrato_api.md`.

## Stack e ambiente
- Python 3.12 + OpenAI Agents SDK, FastAPI, Uvicorn, uv
- Modelos: Gemini (Google AI Studio) é a primeira opção de todos os agentes e a única dos agentes com tools (os Gemma ignoram tools quando há `output_type`); Gemma via OpenRouter é fallback dos agentes sem tools
- Variáveis em `.env` (nunca commitado; nomes em `.env.example`): `OPENAI_API_KEY`, `OPENAI_SECOND_API_KEY`, `OPENAI_THIRD_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_DEFAULT_MODEL`, `OPENAI_FALLBACK_MODEL`, `GOOGLE_API_KEY`, `GOOGLE_EMBEDDING_MODEL`, `GEMINI_MODELS`, `OPENAI_AGENTS_DISABLE_TRACING=1`
- Sem terminal interativo (API), o runner não pergunta pela próxima chave do OpenRouter: a tarefa vira `error`

## Comandos (sempre de dentro de `agent1/`)
- `uv sync`
- `.venv/bin/pytest -q`
- `.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001`
- CLI: `.venv/bin/python main.py importar samples/extrato_2_meses.csv`, `... perguntar --sessao <id> "<pergunta>"`, `... diagnosticar --mes 2024-04`

## Domínio — categorias fixas
`Alimentação`, `Transporte`, `Moradia`, `Saúde`, `Educação`, `Lazer`, `Compras`, `Serviços/Assinaturas`, `Não identificado`

## Convenções
- Evite comentários no código; use nomes de variáveis e funções claros, em português
- Toda execução gera log salvo em arquivo (`prompts/outputs/`), evidência para o relatório
- Testes da parte determinística e da API com `pytest`; na API, os fluxos de LLM são substituídos por funções falsas via `criar_app(executar)`
- Execuções reais de LLM são lentas (o diagnóstico leva ~10 min): não repetir no ciclo de desenvolvimento, rodar uma vez por entrega e em segundo plano
