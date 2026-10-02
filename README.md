# Agente de Análise de Finanças Pessoais (Projeto de Bloco — TP1 e TP2)

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5
**Repositório:** <https://github.com/AlsornaJP/finance-agent-tp1>
**Vídeo do TP2:** `<link do YouTube — preencher>`

Agente construído com o **OpenAI Agents SDK**, acessando modelos via **OpenRouter** e **Google AI Studio**.
Importa extratos bancários em CSV para um banco SQLite, responde perguntas sobre os gastos usando tools e
memória, e gera diagnósticos mensais em etapas.

Princípio central do TP2: **o LLM nunca faz conta**. Leitura do CSV, somas, percentuais, variações e o
critério de anomalia são código Python determinístico, exposto ao modelo como tools. O LLM classifica,
interpreta e redige.

## Estrutura

```
agent/
  config.py          Leitura do .env e clientes OpenRouter / Google AI Studio
  database.py        SQLite: schema, importação de CSV e todas as funções de cálculo
  tools.py           @function_tool que expõem os cálculos e a busca do RAG ao agente
  rag.py             Divisão do guia em trechos, embeddings, busca por cosseno, memórias
  schema.py          Modelos Pydantic (saídas dos agentes e resultados das consultas)
  prompts.py         Instructions de cada agente (anatomia de 4 componentes)
  agents.py          Construção dos agentes
  runner.py          Execução com fallback de modelos/chaves, sessão e restauração em falhas
  importacao.py      Comando importar (classificação com chain-of-thought)
  consulta.py        Comando perguntar (tools + SQLiteSession + memória semântica)
  diagnostico.py     Comando diagnosticar (cadeia least-to-most)
  rastreio.py        Extração das chamadas de tool para logs e métricas
  execution_log.py   Logs de execução em Markdown
knowledge/           Guia de orçamento (fonte não estruturada do RAG)
evaluation/          Gabarito, métricas, avaliação A/B e ciclo PRRR
docs/tp2/            Entregáveis de arquitetura (gatilho, fontes, diagrama, fluxo, dados)
prompts/             Prompts documentados e logs de execução (prompts/outputs/)
samples/             CSVs de exemplo (1 mês e 2 meses)
tests/               Testes pytest da parte determinística
main.py              CLI
```

## Configuração

```bash
uv sync                      # ou: python -m venv .venv && pip install -r requirements.txt pytest
cp .env.example .env         # preencha as chaves
```

| Variável | Uso |
| --- | --- |
| `OPENAI_API_KEY`, `OPENAI_SECOND_API_KEY`, `OPENAI_THIRD_API_KEY` | Chaves do OpenRouter (rotação mediante confirmação) |
| `OPENAI_BASE_URL` | `https://openrouter.ai/api/v1` |
| `OPENAI_DEFAULT_MODEL`, `OPENAI_FALLBACK_MODEL` | Modelos Gemma, fallback dos agentes sem tools |
| `GOOGLE_API_KEY`, `GOOGLE_BASE_URL` | Google AI Studio: fallback de modelos e embeddings |
| `GOOGLE_EMBEDDING_MODEL` | Embeddings do RAG (`gemini-embedding-001`) |
| `GEMINI_MODELS` | Modelos Gemini, primeira opção de todos os agentes, ex.: `gemini-3.5-flash-lite,gemini-3.1-flash-lite` |
| `OPENAI_AGENTS_DISABLE_TRACING` | `1` desativa o tracing nativo do SDK |

Por que Gemini primeiro: os modelos Gemma, quando recebem `output_type` (enviado como `response_format`
JSON), deixam de chamar tools e calculam sozinhos; os Gemini 3.x combinam tools e saída estruturada, então o
assistente usa só `GEMINI_MODELS`. Os demais agentes também começam pelo Gemini — o Gemma gratuito esteve
lento e instável durante o desenvolvimento — e caem na cadeia Gemma (OpenRouter → Google AI Studio) se o
Gemini falhar.

## Uso

```bash
python main.py importar samples/extrato_2_meses.csv
python main.py perguntar --sessao joao "Quanto gastei com Alimentação em abril de 2024 e isso está dentro do recomendado?"
python main.py diagnosticar --mes 2024-04
```

Demonstração de memória (cada comando é um processo novo):

```bash
python main.py perguntar --sessao joao "E em março?"                                  # SQLiteSession
python main.py perguntar --sessao joao-1 "Minha meta é gastar no máximo R$ 100 por mês com Lazer."
python main.py perguntar --sessao joao-2 "Estou dentro da minha meta de lazer em abril de 2024?"   # RAG sobre interações
```

Cada execução grava um log em `prompts/outputs/` com instructions, input, chamadas de tool (argumentos e
retorno) e a saída validada pelo Pydantic.

## Testes e avaliação

```bash
.venv/bin/pytest                                   # parte determinística
python -m evaluation.avaliar_ab --execucoes 3      # A/B: sem tools (TP1) × com tools (TP2)
python -m evaluation.avaliar_prrr v1               # ciclo Prompt-Response-Reflect-Revise
```

Resultados e decisões: `evaluation/resultado_ab.md` e `evaluation/prrr.md`.

## Documentação do TP2

- Relatório técnico: `entrega/joao_jacob_PB_TP2.md`
- Entregáveis de arquitetura: `docs/tp2/entregaveis.md`
- Prompts encadeados e outputs intermediários: `prompts/tp2_*.md`
- Registro do planejamento com o assistente de IA: `docs/tp2/registro_planejamento.md`
- Problemas encontrados e resolvidos: `docs/tp2/problemas_resolvidos.md`

## TP1

Os artefatos do TP1 continuam no repositório: `spec/`, `prompts/parte*_instructions.md`,
`prompts/analise_resultados.md`, os logs `prompts/outputs/parte*` e `entrega/TP1_*`. O prompt da Parte 5
(CSV no prompt, sem tools) é reaproveitado como variante A da avaliação do TP2.
