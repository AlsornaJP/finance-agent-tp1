# Projeto de Bloco — Agentes de IA (TP1–TP3)

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5
**Repositório:** <https://github.com/AlsornaJP/finance-agent-tp1>
**Vídeos:** [TP2](https://youtu.be/fOuFfmOxcTg) · [TP3](https://drive.google.com/drive/folders/14TclvXp9F6-P7GyieWkeyh52sFXjNosH?usp=drive_link)

O projeto tem dois agentes de IA independentes para finanças pessoais, construídos com o **OpenAI Agents SDK**
e expostos como serviços REST (FastAPI):

- **Agente 1 — Finanças Pessoais** (`agent1/`, porta 8001): importa extratos bancários em CSV para um SQLite,
  classifica as transações, responde perguntas sobre os gastos (com tools, memória e RAG) e gera diagnósticos
  mensais em etapas.
- **Agente 2 — Planejador de Metas** (`agent2/`, porta 8002): recebe uma meta de poupança com prazo e os gastos
  de um mês, diz se a meta é viável, propõe cortes por categoria e projeta o acumulado mês a mês.

Os dois **não se conhecem**: não importam código um do outro, não compartilham banco e não se chamam por
HTTP. Quem encadeia os dois é o **n8n**, consumindo os endpoints de cada um.

## Princípio central: o LLM nunca calcula

Toda aritmética (leitura do CSV, somas, percentuais, variações, critério de anomalia, simulação de cortes)
é código Python determinístico, oferecido ao modelo como tools. O LLM só classifica, escolhe e redige.

- Toda saída de agente é um schema Pydantic (`output_type`), nunca texto parseado à mão.
- Todo número citado numa resposta vai em `valores_citados`, junto com a tool que o calculou.
- No agente 2, o plano final (`PlanoDeMeta`) é recalculado em código a partir dos cortes que o LLM propôs.
  Se o modelo errar, a tarefa termina em `error`; o plano nunca sai com um número errado.

A evolução que levou a essa regra está em [`evaluation/avaliacao_final.md`](evaluation/avaliacao_final.md).
No TP1, sem tools, o LLM errava totais em até R$ 1.128,00. Com tools e SQL, a precisão numérica foi 1,00 em
6 de 6 execuções.

## Arquitetura

```text
                         ┌────────────────────────── n8n (Docker) ──────────────────────────┐
                         │  POST /run → aguarda → GET /status/{id} → repete até sair de      │
                         │  pending → usa o resultado                                        │
                         └───────────────┬──────────────────────────────┬────────────────────┘
                                         │ HTTP                         │ HTTP
                         ┌───────────────▼──────────────┐ ┌─────────────▼────────────────────┐
                         │ Agente 1 — Finanças (:8001)  │ │ Agente 2 — Planejador (:8002)    │
                         │ importar · perguntar ·       │ │ planejar meta de poupança        │
                         │ diagnosticar                 │ │                                  │
                         │ SQLite · RAG · SQLiteSession │ │ simulação determinística         │
                         └───────────────┬──────────────┘ └─────────────┬────────────────────┘
                                         │                              │
                                  Gemini (Google AI Studio) · Gemma (OpenRouter, fallback)
```

O `diagnosticar` do agente 1 devolve `total_mes` e `gastos_por_categoria` já no formato aceito pelo
`POST /run` do agente 2. Assim, o n8n pode repassar esses dados sem transformá-los: diagnóstico → plano.

## Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| [`agent1/`](agent1/) | Agente de finanças pessoais (TP1–TP3): CLI, API, tools, RAG, avaliação A/B e PRRR. Tem seu próprio [README](agent1/README.md) e [CLAUDE.md](agent1/CLAUDE.md) |
| [`agent2/`](agent2/) | Planejador de metas (TP3): simulação, tools, agente e API. Ver [CLAUDE.md](agent2/CLAUDE.md) |
| [`integration/`](integration/) | [Contrato de API](integration/contrato_api.md) dos dois agentes e exemplos reais de requisição e resposta |
| [`workflows/`](workflows/) | Workflow do n8n exportado em JSON |
| [`evaluation/`](evaluation/) | [Avaliação final](evaluation/avaliacao_final.md) do pipeline de prompts, do TP1 ao TP3 |
| [`docs/`](docs/) | Especificações, planos e entregáveis de arquitetura (diagrama do TP2 em `docs/tp2/`) |
| [`entrega/`](entrega/) | Relatórios dos TPs, roteiros dos vídeos, capturas e scripts que geram o PDF e o ZIP |

Cada agente é um projeto Python separado, com `pyproject.toml`, `uv.lock`, `.venv` e `.env` próprios.

## Pré-requisitos

- Python 3.12 e [uv](https://docs.astral.sh/uv/)
- Chave do **Google AI Studio** (modelos Gemini e embeddings). É obrigatória nos dois agentes.
- Chaves do **OpenRouter**, opcionais: só o agente 1 usa, como fallback Gemma dos agentes sem tools
- Docker, para rodar o n8n
- `curl` e `jq`, para os exemplos de linha de comando

## Configuração

```bash
cd agent1 && uv sync && cp .env.example .env    # preencha as chaves
cd ../agent2 && uv sync && cp .env.example .env
```

| Variável | Agente | Uso |
|---|---|---|
| `GOOGLE_API_KEY` | 1 e 2 | Google AI Studio |
| `GOOGLE_BASE_URL` | 1 e 2 | Endpoint compatível com OpenAI do Google (`https://generativelanguage.googleapis.com/v1beta/openai/`) |
| `GEMINI_MODELS` | 1 e 2 | Lista de modelos Gemini, em ordem de preferência, ex.: `gemini-3.5-flash-lite,gemini-3.1-flash-lite` |
| `GOOGLE_EMBEDDING_MODEL` | 1 | Embeddings do RAG (`gemini-embedding-001`) |
| `OPENAI_API_KEY`, `OPENAI_SECOND_API_KEY`, `OPENAI_THIRD_API_KEY` | 1 | Chaves do OpenRouter, usadas em rotação |
| `OPENAI_BASE_URL` | 1 | `https://openrouter.ai/api/v1` |
| `OPENAI_DEFAULT_MODEL`, `OPENAI_FALLBACK_MODEL` | 1 | Modelos Gemma de fallback |
| `OPENAI_AGENTS_DISABLE_TRACING` | 1 e 2 | `1` desativa o tracing nativo do SDK |

O Gemini vem primeiro porque os modelos Gemma deixam de chamar tools quando recebem `output_type`. Os agentes
com tools (assistente do agente 1 e planejador do agente 2) usam só Gemini. Os detalhes estão em
[`docs/tp2/problemas_resolvidos.md`](docs/tp2/problemas_resolvidos.md).

## Como subir os serviços

Em dois terminais:

```bash
cd agent1 && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001
cd agent2 && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8002
```

Os serviços escutam em `0.0.0.0` para que o container do n8n consiga alcançá-los. Para conferir:

```bash
curl -s http://localhost:8001/health   # {"status":"ok","agente":"agent1-financas"}
curl -s http://localhost:8002/health   # {"status":"ok","agente":"agent2-planejador"}
```

## API

Os dois serviços seguem o mesmo padrão assíncrono: o `POST /run` responde na hora com um `task_id`, e quem
chamou consulta `GET /status/{task_id}` até o status sair de `pending`.

| Método | Rota | Resposta |
|---|---|---|
| `POST` | `/run` | **202** `{"task_id", "status": "pending"}`; **422** se o corpo for inválido |
| `GET` | `/status/{task_id}` | **200** `{"task_id", "status", "resultado", "erro"}`; **404** se o id não existir |
| `GET` | `/health` | **200** `{"status": "ok", "agente": "<nome>"}` |

Estados possíveis: `pending` → `done` (com `resultado`) ou `error` (com `erro` no formato
`"<TipoDoErro>: <mensagem>"`). As tarefas ficam em memória, então reiniciar o serviço apaga os ids. Cada
serviço executa uma tarefa por vez.

### Agente 1 — ações do `POST /run`

| `acao` | Campos | `resultado` |
|---|---|---|
| `importar` | `csv` (conteúdo do arquivo, colunas `data`, `descrição`, `valor`, `tipo` opcional) | `{log, meses_disponiveis}` |
| `perguntar` | `pergunta`, `sessao_id` (opcional, padrão `"api"`) | `{resposta: {resposta, valores_citados, fontes_conhecimento}, log}` |
| `diagnosticar` | `mes` (`AAAA-MM`) | `{diagnostico, total_mes, gastos_por_categoria, log}` |

```bash
# importar um extrato de exemplo
jq -Rs '{acao: "importar", csv: .}' agent1/samples/extrato_2_meses.csv \
  | curl -s -X POST http://localhost:8001/run -H 'Content-Type: application/json' --data-binary @-

# fazer uma pergunta
curl -s -X POST http://localhost:8001/run -H 'Content-Type: application/json' \
  -d '{"acao": "perguntar", "pergunta": "Quanto gastei com Alimentação em 2024-04?", "sessao_id": "demo"}'

# consultar o resultado
curl -s http://localhost:8001/status/<task_id>
```

Resposta real (resumida):

```json
{
  "status": "done",
  "resultado": {
    "resposta": {
      "resposta": "Em abril de 2024 você gastou R$ 2853,25 com Alimentação, em 3 transações.",
      "valores_citados": [
        {"descricao": "Gasto com Alimentação em 2024-04", "valor": 2853.25, "ferramenta": "gastos_por_categoria"}
      ],
      "fontes_conhecimento": []
    }
  }
}
```

### Agente 2 — `POST /run`

O corpo é um `PedidoPlano` com `meta {valor, prazo}`, `mes_referencia`, `total_mes {renda, total_gasto, saldo}`
e `gastos_por_categoria [{categoria, valor_total}]`. Campos extras são ignorados, então a saída do
`diagnosticar` serve sem transformação.

```bash
curl -s -X POST http://localhost:8002/run -H 'Content-Type: application/json' \
  --data-binary @integration/exemplos/agent2_run_request.json
```

Nesse exemplo real, a meta é R$ 1.200,00 até 2024-12, e o mês de referência tem saldo de −R$ 1.073,35. O
plano conclui que a meta é viável em 8 meses, com R$ 150,00 por mês. Para isso, os cortes cobrem
R$ 1.223,35: corte total de Lazer, Compras e Serviços/Assinaturas e redução de R$ 959,65 em Alimentação. A
diferença para a meta fica em R$ 0,00. A resposta completa está em
[`integration/exemplos/agent2_status_done_v2.json`](integration/exemplos/agent2_status_done_v2.json).

O contrato completo, com todos os campos, regras de validação e casos de erro, está em
[`integration/contrato_api.md`](integration/contrato_api.md).
[`integration/exemplos/curl_agent1.sh`](integration/exemplos/curl_agent1.sh) dispara as três ações do
agente 1.

## Workflow n8n

O workflow em [`workflows/tp3_diagnostico_agent1.json`](workflows/tp3_diagnostico_agent1.json) chama o
`diagnosticar` do agente 1 e faz polling até o resultado ficar pronto:

```text
Iniciar (manual) → POST run (diagnosticar 2024-04) → Aguardar 15 s → GET status
                        ↑                                              │
                        └──────────── Ainda pendente? ── sim ──────────┘
                                             │ não
                                             ▼
                                   Resultado do agente 1 (status, resultado, erro)
```

O n8n roda em Docker. Para que ele enxergue os agentes na máquina host, crie o container com
`--add-host=local:host-gateway` e use as URLs `http://local:8001` e `http://local:8002`. Sem essa opção, use
`http://172.17.0.1:<porta>`. Para usar o workflow, importe o JSON no n8n (*Import from File*).

O próximo passo (TP4) é encadear os dois agentes no n8n: importar → diagnosticar → montar o pedido do
agente 2 com a meta do usuário → planejar. O workflow também terá um ramo para tratar `error`.

## Uso pela linha de comando (agente 1)

O agente 1 também pode ser usado sem a API:

```bash
cd agent1
.venv/bin/python main.py importar samples/extrato_2_meses.csv
.venv/bin/python main.py perguntar --sessao joao "Quanto gastei com Alimentação em abril de 2024?"
.venv/bin/python main.py diagnosticar --mes 2024-04
```

Mais exemplos, inclusive de memória entre sessões, estão no [README do agente 1](agent1/README.md#uso).

## Testes

A parte determinística e as APIs têm testes `pytest`. Nos testes da API, os fluxos de LLM são substituídos
por funções falsas (`criar_app(executar)`), então os testes não usam rede nem chaves:

```bash
cd agent1 && .venv/bin/pytest -q
cd agent2 && .venv/bin/pytest -q
```

Execuções reais de LLM ficam fora do ciclo de desenvolvimento. Um diagnóstico leva cerca de 15 s com o
Gemini, mas sob rate limit o fallback pode levar vários minutos. Cada execução real grava um log em Markdown
em `prompts/outputs/` do agente, com instructions, entrada, chamadas de tool e saída validada.

## Avaliação de prompts

| Etapa | O que foi comparado | Documento |
|---|---|---|
| TP1 | instructions livres × anatomia de 4 componentes × `output_type` | [`agent1/prompts/analise_resultados.md`](agent1/prompts/analise_resultados.md) |
| TP2 | A/B: CSV no prompt (sem tools) × classificador + SQL (com tools) | [`agent1/evaluation/resultado_ab.md`](agent1/evaluation/resultado_ab.md) |
| TP2 | ciclo PRRR do assistente (v1 → v2) | [`agent1/evaluation/prrr.md`](agent1/evaluation/prrr.md) |
| TP3 | planejador v1 → v2 (valores em reais no resumo) | [`evaluation/avaliacao_final.md`](evaluation/avaliacao_final.md) |

## Documentação das entregas

| TP | Relatório | Outros documentos |
|---|---|---|
| TP1 | [`entrega/TP1_26E3_5_Joao_Pedro_Jacob.md`](entrega/TP1_26E3_5_Joao_Pedro_Jacob.md) | `agent1/spec/` |
| TP2 | [`entrega/joao_jacob_PB_TP2.md`](entrega/joao_jacob_PB_TP2.md) | [`docs/tp2/entregaveis.md`](docs/tp2/entregaveis.md), [`docs/tp2/problemas_resolvidos.md`](docs/tp2/problemas_resolvidos.md) |
| TP3 | [`entrega/joao_jacob_PB_TP3.md`](entrega/joao_jacob_PB_TP3.md) | [`integration/contrato_api.md`](integration/contrato_api.md), [`docs/superpowers/specs/2026-10-19-tp3-design.md`](docs/superpowers/specs/2026-10-19-tp3-design.md) |

## Stack

Python 3.12 · OpenAI Agents SDK · Pydantic 2 · FastAPI · Uvicorn · SQLite · uv · pytest · n8n (Docker) ·
Gemini (Google AI Studio) · Gemma (OpenRouter)
