# TP1 — Agente de Análise de Finanças Pessoais

**Aluno:** João Pedro Jacob
**Disciplina:** 26E3_5
**Data:** Agosto de 2026

---

## Parte 1 — Definição do Problema e Requisitos

### 1.1 Descrição do problema

O agente tem como objetivo auxiliar usuários no controle de finanças pessoais, analisando um extrato bancário fornecido em formato CSV e produzindo um retorno estruturado (JSON) com o resumo de gastos por categoria, identificação de gastos anômalos e comparação com o mês anterior, quando dados históricos estiverem disponíveis. O objetivo é dar ao usuário uma visão clara e acionável de seu comportamento financeiro sem que ele precise analisar manualmente cada transação.

**Premissa adotada:** o usuário fornece um **único arquivo CSV**, que pode conter transações de múltiplos meses. Quando há dados de mais de um mês, o agente realiza a comparação entre os dois períodos mais recentes (RF4). Essa escolha prioriza simplicidade de uso (um único upload) em vez de exigir múltiplos arquivos separados.

### 1.2 Requisitos funcionais (verificáveis)

| # | Requisito | Critério de verificação |
|---|-----------|--------------------------|
| RF1 | O agente deve classificar cada transação do CSV em uma das categorias fixas pré-definidas | Toda transação no JSON de saída possui um campo `categoria` preenchido com um valor pertencente ao conjunto fixo |
| RF2 | O agente deve calcular o total gasto por categoria no período analisado | O JSON de saída contém um resumo (`resumo_por_categoria`) cuja soma dos valores é igual ao total de despesas do CSV de entrada |
| RF3 | O agente deve identificar transações anômalas (valores muito acima do padrão da categoria) | O JSON de saída contém uma lista (`gastos_anomalos`) com transações sinalizadas e uma justificativa mínima |
| RF4 | Quando houver dados de mais de um mês, o agente deve comparar o total gasto por categoria entre os dois períodos mais recentes | O JSON de saída contém um campo `comparacao_mes_anterior` com a variação percentual ou absoluta por categoria |

*RF1 e RF2 satisfazem o mínimo de 2 requisitos verificáveis exigido pelo enunciado; RF3 e RF4 aprofundam o "feedback detalhado".*

### 1.3 Categorias fixas

`Alimentação`, `Transporte`, `Moradia`, `Saúde`, `Educação`, `Lazer`, `Compras`, `Serviços/Assinaturas`, `Não identificado`

*A categoria "Não identificado" cobre transações que o agente não consegue classificar com confiança, garantindo que RF1 seja sempre satisfeito.*

### 1.4 Inputs

- **Formato:** arquivo CSV (ou conteúdo CSV colado como texto), lido como texto bruto e repassado diretamente ao agente (ver Parte 2, seção 2.1, sobre a decisão de não fazer parsing estruturado)
- **Colunas esperadas:** `data`, `descrição`, `valor` (e opcionalmente `tipo` — entrada/saída)
- **Período:** idealmente cobrindo 2 meses ou mais, para permitir a comparação (RF4)

### 1.5 Outputs

- **Formato:** JSON estruturado, validado via `output_type` do OpenAI Agents SDK (schema Pydantic)
- **Campos principais:** `periodo_analisado`, `total_gasto`, `resumo_por_categoria`, `gastos_anomalos`, `comparacao_mes_anterior`

### 1.6 Restrições técnicas

- Operação **single-turn**: uma chamada, um CSV, um JSON de saída — sem necessidade de conversação multi-turn no escopo do TP1
- O CSV é passado como **texto bruto** ao agente, sem parsing estruturado prévio (decisão deliberada — ver 2.1)
- O modelo utilizado deve suportar geração de saída estruturada compatível com `output_type`
- O modelo é acessado via **OpenRouter** (camada gratuita), sujeito a limites de requisições por dia (variando entre ~50–200/dia na conta gratuita, até 1.000/dia após adição de créditos) e à rotação do catálogo de modelos gratuitos — disponibilidade deve ser reverificada periodicamente em openrouter.ai/models

---

## Parte 2 — Arquitetura Inicial

### 2.1 Componentes

| Componente | Descrição |
|---|---|
| **Pré-processamento (Python mínimo)** | Apenas leitura do arquivo/texto CSV — sem parsing estruturado nem validação de colunas. O conteúdo bruto é passado como string no prompt |
| **Agent** | Único agente (`Agent` do SDK), responsável por interpretar o CSV, categorizar transações, calcular totais, identificar anomalias e comparar meses |
| **Runner** | Executa o agente de forma single-turn, recebendo o CSV bruto como parte do input |
| **LLM** | `google/gemma-4-26b-a4b-it:free`, acessado via OpenRouter (ver 2.3) |
| **Output** | JSON estruturado, validado via `output_type` (schema Pydantic) |

**Decisão de design — sem tools:** como não há parsing estruturado nem chamadas externas, o agente não utiliza `@function_tool` nesta primeira versão. Toda a lógica (categorização, soma, detecção de anomalias, comparação) é feita via raciocínio do LLM sobre o texto do CSV recebido no prompt.

**Limitação assumida:** o parsing mínimo implica risco maior de erro em CSVs mal formatados ou com muitas linhas, já que LLMs podem perder precisão em somas com grandes volumes de transações. Essa é uma limitação conhecida e aceita para o escopo do TP1.

### 2.2 Fluxo de dados

```
CSV (arquivo/texto)
      │
      ▼
[Leitura simples do arquivo — sem parsing estruturado]
      │  (conteúdo bruto do CSV como string)
      ▼
[Prompt construído com o CSV bruto + instruções]
      │
      ▼
[Agent + Runner (single-turn)]
      │
      ▼
[LLM interpreta o CSV, categoriza, soma, detecta anomalias, compara meses]
      │
      ▼
[output_type valida a estrutura da resposta]
      │
      ▼
JSON estruturado (result.final_output)
```

### 2.3 Escolha do modelo (LLM)

**Modelo principal:** `google/gemma-4-31b-it:free`, acessado via OpenRouter (endpoint compatível com a API da OpenAI, configurado como cliente padrão do Agents SDK via `set_default_openai_client`).

**Justificativa técnica:**
- Suporte a **saída estruturada (structured output)** e **function calling nativo**, essenciais para o requisito de `output_type` (Parte 5)
- Procedência confiável (Google DeepMind), relevante para documentação acadêmica
- Custo zero, adequado ao uso educacional do TP1

**Modelo de backup:** `google/gemma-4-26b-a4b-it:free`, usado automaticamente em caso de falha ou indisponibilidade do modelo principal.

**Rotação de chaves:** o `.env` do projeto define até 3 chaves de API do OpenRouter (`OPENAI_API_KEY`, `OPENAI_SECOND_API_KEY`, `OPENAI_THIRD_API_KEY`), usadas em ordem de prioridade caso o limite diário de requisições gratuitas (50/chave) seja atingido.

**Restrição documentada:** a disponibilidade de modelos gratuitos no OpenRouter é rotativa; a escolha acima reflete o catálogo consultado em agosto de 2026 e deve ser revalidada em `openrouter.ai/models` antes da implementação final.

### 2.4 Estrutura preliminar do output (JSON)

*(a ser formalizada como schema Pydantic na Parte 5)*

- `periodo_analisado`: mês(es) cobertos pela análise
- `total_gasto`: valor total do período mais recente
- `resumo_por_categoria`: lista de `{categoria, valor_total, quantidade_transacoes}`
- `gastos_anomalos`: lista de `{transacao, motivo_anomalia}`
- `comparacao_mes_anterior`: lista de `{categoria, valor_atual, valor_anterior, variacao}`

---

## Pontos em aberto / a revisar antes da implementação

- ~~Confirmar código/nome da disciplina no cabeçalho do documento~~ — resolvido (26E3_5)
- ~~Revalidar disponibilidade e capacidades do modelo escolhido em `openrouter.ai/models` no momento da implementação (Parte 3)~~ — resolvido, com consequência arquitetural: ver nota abaixo
- Nenhum outro ponto pendente das Partes 1 e 2

---

## Nota pós-implementação

Este documento registra a especificação e a arquitetura **iniciais**, anteriores à implementação, e
foi mantido como tal. Duas divergências entre o previsto aqui e o entregue estão documentadas em
`prompts/analise_resultados.md`:

1. **Provedor de fallback.** Os modelos gratuitos do OpenRouter mostraram-se sujeitos a rate limit
   do pool compartilhado do provedor upstream, situação em que a rotação entre chaves prevista
   originalmente não surte efeito. A implementação acrescentou o Google AI Studio como provedor de
   fallback, acessado pela cota pessoal via endpoint compatível com OpenAI.
2. **Campo `transacoes` no schema.** A saída estruturada da Parte 5 degradou a precisão aritmética
   do modelo. Um campo de enumeração foi acrescentado antes dos campos agregados, corrigindo a
   extração — sem, porém, corrigir a agregação. O critério de verificação do RF2 permanece não
   satisfeito, e a falha é apresentada como resultado analisado.
