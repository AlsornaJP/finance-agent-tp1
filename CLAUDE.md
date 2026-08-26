# CLAUDE.md

## Projeto
Agente de análise de finanças pessoais (TP1 — disciplina de Agentes de IA). Recebe um CSV de extrato bancário e retorna uma análise de gastos. Implementado com o OpenAI Agents SDK.

## Stack
- Python + OpenAI Agents SDK (`openai-agents`)
- Modelo via **OpenRouter** (não API da OpenAI direto), configurado via variáveis de ambiente (ver `.env`, nunca commitado):
  - `OPENAI_API_KEY` — chave principal
  - `OPENAI_SECOND_API_KEY`, `OPENAI_THIRD_API_KEY` — chaves alternativas, para rotacionar caso o rate limit gratuito do OpenRouter seja atingido
  - `OPENAI_BASE_URL=https://openrouter.ai/api/v1`
  - `OPENAI_DEFAULT_MODEL=google/gemma-4-31b-it:free` — modelo principal
  - `OPENAI_FALLBACK_MODEL=google/gemma-4-26b-a4b-it:free` — usado se o principal falhar/atingir limite
  - `OPENAI_AGENTS_DISABLE_TRACING=1` — tracing do Agents SDK desativado (o tracing nativo do SDK envia dados para a plataforma da OpenAI, incompatível com o uso via OpenRouter)
- **Nunca** commitar o `.env` real; manter só um `.env.example` com os nomes das variáveis, sem valores

## Restrições de design (não mudar sem discutir)
- Sem tools (`@function_tool`): CSV é passado como texto bruto no prompt, sem parsing estruturado
- Execução single-turn: uma chamada, um CSV, uma resposta
- Saída final deve usar `output_type` (schema Pydantic), não string a ser parseada manualmente
- evite comentários no código, use nomes de variáveis e funções claros
- O código deve ser o mais limpo e organizado possível


## Domínio — categorias fixas
`Alimentação`, `Transporte`, `Moradia`, `Saúde`, `Educação`, `Lazer`, `Compras`, `Serviços/Assinaturas`, `Não identificado`

## Estrutura de pastas
- `agent/` — Agent, Runner, config do SDK
- `spec/` — especificação em Markdown (Partes 1 e 2 do TP)
- `prompts/` — instructions estruturadas (anatomia de 4 componentes) + logs de output

## Convenções
- Toda execução deve gerar log salvo em arquivo (evidência para o PDF do TP)