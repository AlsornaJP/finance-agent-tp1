# CLAUDE.md

## Projeto
Agente de análise de finanças pessoais (Projeto de Bloco — disciplina de Agentes de IA; TP1 e TP2). Importa extratos bancários em CSV para um SQLite, responde perguntas sobre os gastos com tools e memória, e gera diagnósticos mensais em etapas. Implementado com o OpenAI Agents SDK.

## Stack
- Python + OpenAI Agents SDK (`openai-agents`)
- Modelo via **OpenRouter** (não API da OpenAI direto), configurado via variáveis de ambiente (ver `.env`, nunca commitado):
  - `OPENAI_API_KEY` — chave principal
  - `OPENAI_SECOND_API_KEY`, `OPENAI_THIRD_API_KEY` — chaves alternativas, para rotacionar caso o rate limit gratuito do OpenRouter seja atingido
  - `OPENAI_BASE_URL=https://openrouter.ai/api/v1`
  - `OPENAI_DEFAULT_MODEL=google/gemma-4-31b-it:free` — modelo principal
  - `OPENAI_FALLBACK_MODEL=google/gemma-4-26b-a4b-it:free` — usado se o principal falhar/atingir limite
  - `GOOGLE_API_KEY` — chave pessoal do Google AI Studio (fallback de modelos e embeddings do RAG)
  - `GOOGLE_EMBEDDING_MODEL=gemini-embedding-001` — embeddings do RAG
  - `GEMINI_MODELS` — modelos Gemini, primeira opção de todos os agentes e única dos agentes com tools (os Gemma ignoram tools quando há `output_type`); Gemma vira fallback
  - `OPENAI_AGENTS_DISABLE_TRACING=1` — tracing do Agents SDK desativado (o tracing nativo do SDK envia dados para a plataforma da OpenAI, incompatível com o uso via OpenRouter)
- **Nunca** commitar o `.env` real; manter só um `.env.example` com os nomes das variáveis, sem valores

## Restrições de design (não mudar sem discutir)
- O LLM nunca calcula: toda aritmética fica em `agent/database.py` e chega ao LLM por tools (`agent/tools.py`)
- Todo número citado em resposta deve ser rastreável à tool de origem (`valores_citados`)
- Leitura de CSV é determinística (Python); o LLM só classifica as transações
- Fluxos orquestrados por código; sem handoffs entre agentes até a Etapa 3
- Saída final deve usar `output_type` (schema Pydantic), não string a ser parseada manualmente
- evite comentários no código, use nomes de variáveis e funções claros
- O código deve ser o mais limpo e organizado possível


## Domínio — categorias fixas
`Alimentação`, `Transporte`, `Moradia`, `Saúde`, `Educação`, `Lazer`, `Compras`, `Serviços/Assinaturas`, `Não identificado`

## Estrutura de pastas
- `agent/` — agentes, runner, tools, banco, RAG e fluxos (`importacao`, `consulta`, `diagnostico`)
- `knowledge/` — documento não estruturado do RAG (guia de orçamento)
- `data/` — banco SQLite local (não versionado)
- `evaluation/` — gabarito, métricas, avaliação A/B e ciclo PRRR
- `docs/tp2/` — entregáveis de arquitetura do TP2
- `spec/` — especificação em Markdown (Partes 1 e 2 do TP1)
- `prompts/` — instructions estruturadas (anatomia de 4 componentes) + logs de output
- `tests/` — testes `pytest` da parte determinística

## Convenções
- Toda execução deve gerar log salvo em arquivo (evidência para o relatório do TP)
- Testes da parte determinística com `pytest` (`.venv/bin/pytest`)