---
title: "TP1 — Agente de Análise de Finanças Pessoais"
subtitle: "Especificação, implementação e evidências de execução"
author: "João Pedro Jacob — Disciplina 26E3_5"
date: "Agosto de 2026"
---

# Sumário do documento

Este documento reúne, em ordem: a especificação do problema e a arquitetura inicial (Partes 1 e 2),
os prompts documentados com a anatomia de quatro componentes (Partes 3 a 5), a análise dos
resultados com as justificativas técnicas, e as evidências de execução registradas em log.

O código-fonte completo está no repositório que acompanha esta entrega.


# Parte I — Especificação do problema e arquitetura inicial

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

# Parte II — Prompts documentados


## Parte 3 — Instructions iniciais (texto livre)

Prompt simples, sem estruturação explícita, usado como linha de base para comparação.

```text
Você é um analista de finanças pessoais.

Você recebe o conteúdo bruto de um CSV de extrato bancário e produz uma análise dos gastos.

Classifique cada transação em uma categoria, calcule o total gasto por categoria, aponte
transações anômalas e, se o extrato cobrir mais de um mês, compare os dois meses mais recentes.

Responda em português do Brasil.
```

## Parte 4 — Instructions refinadas (anatomia de 4 componentes)

Constantes correspondentes em `agent/prompts.py`: `ANATOMIA_INSTRUCAO`, `ANATOMIA_CONTEXTO`, `ANATOMIA_EXEMPLOS`, `ANATOMIA_FORMATO_SAIDA_TEXTO`.

## Componente 1 — Instrução

```text
# INSTRUÇÃO

Você é um analista de finanças pessoais. Sua tarefa é analisar o extrato bancário em CSV
fornecido pelo usuário e produzir uma análise completa dos gastos, em uma única resposta.

Execute, nesta ordem:
1. Classifique cada transação de saída (despesa) em exatamente uma das categorias fixas listadas no CONTEXTO.
2. Some os gastos por categoria e informe quantas transações compõem cada total.
3. Calcule o total gasto no período e identifique o período analisado (primeira e última data).
4. Identifique transações anômalas: valores muito acima do padrão daquela categoria no próprio extrato.
5. Se o extrato cobrir dois ou mais meses, compare os gastos por categoria entre os dois meses mais recentes.
```

## Componente 2 — Contexto

```text
# CONTEXTO

Formato da entrada: texto bruto de um CSV com as colunas `data`, `descrição`, `valor` e,
opcionalmente, `tipo`. O extrato pode conter transações de vários meses.

Categorias fixas (use exatamente estes rótulos, sem criar novos):
- Alimentação
- Transporte
- Moradia
- Saúde
- Educação
- Lazer
- Compras
- Serviços/Assinaturas
- Não identificado

Regras de negócio:
- Toda despesa deve receber uma categoria; quando a descrição não permitir uma classificação
  confiável, use `Não identificado` em vez de adivinhar.
- Entradas (salários, transferências recebidas, estornos) não são gastos: ignore-as nos totais.
- Valores negativos representam saídas; trate-os pelo valor absoluto nos totais.
- Uma transação é anômala quando destoa claramente do padrão da própria categoria no extrato
  (ordem de grandeza acima da média das demais transações daquela categoria).
- A comparação entre meses só é válida quando há dados de dois meses ou mais. Com um único mês,
  declare explicitamente a ausência de histórico e não invente valores.
- Todos os valores monetários são em reais (R$), com duas casas decimais.
- Responda em português do Brasil.
```

## Componente 3 — Exemplos (few-shot)

```text
# EXEMPLOS

Exemplo 1 — classificação de transações individuais:
  `2024-03-05,IFOOD *RESTAURANTE SAO PAULO,-52.90` -> categoria `Alimentação`, gasto de R$ 52,90.
  `2024-03-06,UBER *TRIP,-18.40`                   -> categoria `Transporte`, gasto de R$ 18,40.
  `2024-03-07,NETFLIX.COM,-39.90`                  -> categoria `Serviços/Assinaturas`, gasto de R$ 39,90.
  `2024-03-08,PAG*7X4K9ZQ,-27.00`                  -> categoria `Não identificado` (descrição não interpretável).
  `2024-03-05,SALARIO EMPRESA XYZ,4500.00`         -> entrada, ignorada nos totais de gasto.

Exemplo 2 — detecção de anomalia:
  Se a categoria `Alimentação` tiver transações de R$ 32,00, R$ 48,50, R$ 55,10 e R$ 890,00,
  a transação de R$ 890,00 é anômala, com motivo do tipo:
  "valor cerca de 19x a média das demais despesas de Alimentação no período".

Exemplo 3 — comparação entre meses:
  Extrato com março e abril: para `Transporte`, R$ 210,00 em abril contra R$ 150,00 em março
  resulta em variação de +40% (aumento de R$ 60,00).
```

## Componente 4 — Formato de saída (texto)

```text
# FORMATO DE SAÍDA

Responda em texto estruturado, exatamente com estas seções e nesta ordem:

**Período analisado:** data inicial a data final.
**Total gasto:** valor total em R$.
**Resumo por categoria:** uma linha por categoria com gastos, no formato
`- <categoria>: R$ <valor_total> (<quantidade> transações)`.
**Gastos anômalos:** uma linha por transação anômala, no formato
`- <data> | <descrição> | R$ <valor> — <motivo da anomalia>`.
Se não houver nenhuma, escreva `Nenhum gasto anômalo identificado`.
**Comparação com o mês anterior:** uma linha por categoria, no formato
`- <categoria>: R$ <valor_atual> (mês atual) vs R$ <valor_anterior> (mês anterior) — <variação>`.
Se o extrato cobrir apenas um mês, escreva
`Sem dados históricos: o extrato cobre apenas um mês`.

Não inclua nenhum texto fora dessas seções.
```

## Parte 5 — Instructions com saída estruturada

Reaproveita os componentes 1 a 3 da Parte 4 e troca apenas o componente 4 (`ANATOMIA_FORMATO_SAIDA_JSON`), que descreve o schema Pydantic `AnaliseFinanceira` aplicado ao `Agent` via `output_type`.

## Componente 4 — Formato de saída (JSON)

```text
# FORMATO DE SAÍDA

Responda exclusivamente com um objeto JSON válido, sem texto, comentários ou blocos de código ao redor,
seguindo o schema:

- `periodo_analisado` (string): período coberto pelo extrato, ex. "2024-03-01 a 2024-04-30".
- `total_gasto` (número): soma de todas as despesas do período.
- `resumo_por_categoria` (lista): objetos com `categoria` (uma das categorias fixas),
  `valor_total` (número) e `quantidade_transacoes` (inteiro). Inclua apenas categorias com gastos.
- `gastos_anomalos` (lista): objetos com `transacao` (data, descrição e valor da transação) e
  `motivo_anomalia` (justificativa objetiva). Lista vazia se não houver anomalias.
- `comparacao_mes_anterior` (lista): objetos com `categoria`, `valor_atual` (número),
  `valor_anterior` (número) e `variacao` (string, ex. "+40%" ou "-12,5%").
  Se o extrato cobrir apenas um mês, retorne uma lista vazia.

Restrição de consistência: a soma de `valor_total` em `resumo_por_categoria` deve ser igual a `total_gasto`.
```

# Parte III — Análise dos resultados e justificativas técnicas

Documento de apoio ao relatório do TP. Compara os outputs das três etapas e registra a limitação
observada na Parte 5, junto com o experimento feito para mitigá-la.

Todas as execuções usaram `gemma-4-31b-it` pelo Google AI Studio. Os modelos `:free` do OpenRouter
estavam sob rate limit do pool compartilhado do provedor upstream durante os testes; os logs
`parte3_erro_*.md` registram esses 429 e a queda automática para o provedor de fallback.

## Mapa de evidências

| Arquivo | O que demonstra |
| --- | --- |
| `parte3_erro_*.md` (3 arquivos) | Tratamento de rate limit: 429 do pool compartilhado e fallback de provedor |
| `parte3_extrato_1_mes_*.md` | Output em texto livre, com taxonomia inventada pelo modelo |
| `parte4_extrato_1_mes_*.md` | Output com prompt refinado: categorias fixas respeitadas e aritmética correta |
| `parte5_*_172306.json` / `parte5_*_172341.json` | Saída estruturada com o schema do enunciado |
| `parte5_*_184755.json` / `parte5_*_184916.json` | Saída estruturada com o campo de enumeração acrescentado |

## Parte 3 → Parte 4: o efeito da anatomia de 4 componentes

Sem o componente de **contexto**, o agente inventou a própria taxonomia:

| Parte 3 (instructions livres) | Parte 4 (categorias fixas no contexto) |
| --- | --- |
| `Habitação` | `Moradia` |
| `Alimentação (Mercado)` + `Alimentação (Restaurantes/iFood)` | `Alimentação` (categoria única) |
| `Outros/Diversos` | `Não identificado` |
| `Saúde/Bem-estar` | `Saúde` |
| `Assinaturas` | `Serviços/Assinaturas` |

Nenhum desses rótulos pertence à lista fixa do domínio, o que inviabilizaria qualquer agregação
entre execuções. Na Parte 4 as nove categorias foram respeitadas literalmente — incluindo
`Não identificado` para `PAG*7X4K9ZQ`, caso coberto pelo exemplo few-shot do componente de
**exemplos**.

A Parte 4 também acertou a aritmética: reportou `R$ 5.310,90`, idêntico à soma real das saídas do
CSV.

## Parte 4 → Parte 5: o custo da saída estruturada

O `output_type` cumpriu seu papel: `result.final_output` retorna instância válida de
`AnaliseFinanceira`, sem parsing manual de string. As categorias fixas continuaram respeitadas, a
anomalia foi detectada nos dois CSVs e `comparacao_mes_anterior` veio vazio no extrato de um mês e
preenchido no de dois — sem inventar histórico.

A precisão numérica, porém, regrediu:

| | 1 mês | 2 meses |
| --- | --- | --- |
| `total_gasto` reportado | 4182,90 | 7613,35 |
| Soma de `resumo_por_categoria` | 4970,90 | 7792,95 |
| Total real do CSV | **5310,90** | **8325,65** |
| Transações de saída contadas | 18 (real: 19) | 28 (real: 30) |

Havia dois defeitos sobrepostos e indistinguíveis a partir dessa saída: transações perdidas *e*
erro de adição. Em `Alimentação`, por exemplo, o modelo declarou quatro transações somando
R$ 1.988,35, valor que não corresponde a nenhum subconjunto do CSV (descartar qualquer uma das
cinco daria 2015,60, 2275,45, 2299,75, 438,35 ou 2284,25).

### Causa provável

A Parte 4 produziu, antes da resposta, um bloco `<thought>` extenso em que o modelo somou categoria
por categoria e conferiu o resultado ao final (visível em `parte4_extrato_1_mes_*.md`). Na Parte 5,
o `response_format` de JSON schema obriga a saída a começar já no objeto JSON, eliminando esse
rascunho: o modelo precisa emitir `valor_total` como primeiro token daquele campo, sem espaço para
cálculo intermediário.

## Experimento: campo de enumeração

Para testar essa hipótese, o schema recebeu um campo `transacoes` (lista de `data`, `descricao`,
`valor`, `categoria`) posicionado **antes** de todos os campos agregados — a ordem das propriedades
é preservada no JSON Schema gerado, então o modelo é obrigado a enumerar o extrato linha a linha
antes de produzir qualquer total. O componente de formato de saída passou a instruir que os totais
sejam calculados a partir dessa lista.

### Resultado: extração muito melhorada, mas não confiável

Foram feitas quatro execuções com o campo de enumeração — duas por extrato — para verificar se o
comportamento se repete:

| Execução | Linhas enumeradas | Soma enumerada | Total real | Integridade da lista |
| --- | --- | --- | --- | --- |
| 1 mês, 18:47 | 20 | 5310,90 | 5310,90 | data alterada + linha inexistente de R$ 0,00 |
| 1 mês, 19:54 | 20 | 5339,50 | 5310,90 | transação duplicada |
| 2 meses, 18:49 | 30 | 8325,65 | 8325,65 | descrição corrompida |
| 2 meses, 19:55 | 31 | 8365,55 | 8325,65 | transação duplicada |

A soma da lista coincidiu com o CSV em duas das quatro execuções, e **nenhuma das quatro reproduziu
o extrato fielmente**. Comparado ao schema do enunciado, que perdia transações e errava por centenas
de reais, é uma melhora expressiva: o erro caiu de −1128,00 para, no pior caso, +39,90. Mas a
enumeração não é fiel, e as duas execuções cujo total bateu o fizeram por compensação, não por
acerto — na de 18:47, a `PADARIA CENTRAL` foi deslocada de 09/03 para 03/03 e uma linha fantasma de
R$ 0,00 foi acrescentada; como a data não entra na soma e o valor fantasma era zero, o total
permaneceu exato.

Os defeitos de integridade se concentram na geração das descrições:

```text
METRO SP RECARGA  ->  "METRO SP RE carved"
PADARIA CENTRAL   ->  "እየሱስce"            (caracteres em amárico)
NETFLIX.COM       ->  "descricao own"
(inexistente)     ->  "Tarefas extras"
```

São falhas de geração token a token, típicas de modelos pequenos em saídas longas e repetitivas. Nas
duas execuções em que a soma divergiu, a diferença equivale exatamente ao valor de uma transação
duplicada — R$ 28,60 (`PADARIA CENTRAL`) e R$ 39,90 (`NETFLIX.COM`).

### Resultado: agregação ainda incorreta

Comparando cada categoria informada contra o valor derivado da lista que o próprio modelo produziu,
nas quatro execuções:

| Execução | Categorias exatas | Categorias com erro de soma |
| --- | --- | --- |
| 1 mês, 18:47 | 8 de 9 | `Alimentação` (5 tx) |
| 1 mês, 19:54 | 8 de 9 | `Alimentação` (6 tx) |
| 2 meses, 18:49 | 7 de 9 | `Alimentação` (6 tx), `Transporte` (7 tx) |
| 2 meses, 19:55 | 6 de 9 | `Alimentação` (6 tx), `Transporte` (7 tx), `Serviços/Assinaturas` (5 tx) |

`total_gasto` divergiu da soma das próprias categorias em todas as execuções, sem exceção.

O padrão se manteve nas quatro rodadas: **toda categoria com uma ou duas transações saiu exata;
todo erro está em categoria com cinco ou mais.** A repetição reforçou a hipótese em vez de
enfraquecê-la — a categoria que passou a errar na última execução, `Serviços/Assinaturas`, tem
exatamente cinco transações, o limiar identificado nas rodadas anteriores.

A taxa de erro escala com o número de parcelas da soma, não com o valor envolvido nem com a
categoria específica. Note ainda que `Alimentação` erra nas quatro execuções e `Transporte` nas duas
do extrato maior: as categorias mais numerosas erram de forma sistemática, não ocasional.

### Conclusão do experimento

O campo de enumeração melhorou muito a extração sem torná-la confiável, e não resolveu a
aritmética. O ganho é sobretudo diagnóstico: com a lista à vista, é possível separar o que antes era
uma divergência ambígua em dois defeitos independentes — falhas de integridade na enumeração
(duplicações, descrições corrompidas, datas alteradas) e erros de adição sobre valores que o próprio
modelo registrou corretamente. O critério de verificação do enunciado
(`soma de resumo_por_categoria == total_gasto`) continua **não satisfeito** em todas as execuções.

A alteração foi mantida por dominar a versão anterior: mesma falha no critério, porém com dados
corretos na saída e uma limitação caracterizada com precisão.

## Por que a limitação permanece

A restrição de design do TP proíbe `@function_tool`: o CSV é entregue como texto bruto no input
(`agent/runner.py:97,110`) e toda a análise é raciocínio do LLM. Somar 19 ou 30 parcelas mentalmente
é justamente o tipo de tarefa em que um LLM pequeno é frágil e uma chamada de função seria trivial —
e os dados necessários para o cálculo correto já estão presentes na saída, bastando somá-los. A
limitação é consequência direta da restrição, e sua superação por tool calling é escopo do trabalho
seguinte.

A implementação não mascara o problema: `main.py` recalcula as três consistências a cada execução da
Parte 5 (soma da lista vs `total_gasto`, soma das categorias vs `total_gasto`, contagem das
categorias vs itens enumerados) e marca `[DIVERGE]` no que não fecha.

## Mitigações restantes (não aplicadas)

- **Campo de raciocínio textual** — um campo `str` antes dos numéricos, para o modelo escrever a
  conta antes de emitir o resultado. Complementar à enumeração, ataca diretamente a adição.
- **Recálculo em código** — derivar `total_gasto` e `resumo_por_categoria` da lista enumerada faria
  todos os critérios fecharem, já que a lista está correta. Descartado por mascarar o erro em vez de
  corrigi-lo, contrariando o enunciado.
- **Modelo maior** — o defeito é de capacidade aritmética; modelos maiores erram menos, ao custo de
  sair da camada gratuita.

# Parte IV — Evidências de execução

Os logs abaixo reproduzem o cabeçalho de cada execução e a resposta do modelo. As *instructions* enviadas foram omitidas por já constarem da Parte II, e os CSVs de entrada constam do apêndice.

## Parte 3 — tentativa interrompida por rate limit do OpenRouter

- Timestamp: 2026-08-26T17:09:16
- Modelo: google/gemma-4-26b-a4b-it:free
- Chave de API: OPENAI_API_KEY
- CSV de entrada: samples/extrato_1_mes.csv

*Arquivo: `parte3_erro_20260826-170916.md`*

### Erro

```text
RateLimitError: Error code: 429 - {'error': {'message': 'Provider returned error', 'code': 429, 'metadata': {'raw': 'google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations', 'provider_name': 'Google AI Studio', 'is_byok': False, 'provider_error_code': '429', 'limit_source': 'upstream_provider_shared_pool', 'remedy_hint': 'Retry shortly, add your own provider key (https://openrouter.ai/settings/integrations), or route to another provider with provider routing: https://openrouter.ai/docs/features/provider-routing'}}, 'user_id': 'user_3HAnyQU9OrbN5ImHaGaPrZYLqFk'}
```

## Parte 3 — tentativa interrompida por rate limit do OpenRouter

- Timestamp: 2026-08-26T17:13:23
- Modelo: google/gemma-4-26b-a4b-it:free
- Chave de API: OPENAI_API_KEY
- CSV de entrada: samples/extrato_1_mes.csv

*Arquivo: `parte3_erro_20260826-171323.md`*

### Erro

```text
RateLimitError: Error code: 429 - {'error': {'message': 'Provider returned error', 'code': 429, 'metadata': {'raw': 'google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations', 'provider_name': 'Google AI Studio', 'is_byok': False, 'provider_error_code': '429', 'limit_source': 'upstream_provider_shared_pool', 'remedy_hint': 'Retry shortly, add your own provider key (https://openrouter.ai/settings/integrations), or route to another provider with provider routing: https://openrouter.ai/docs/features/provider-routing'}}, 'user_id': 'user_3HAnyQU9OrbN5ImHaGaPrZYLqFk'}
```

## Parte 3 — tentativa interrompida por rate limit do OpenRouter

- Timestamp: 2026-08-26T17:16:42
- Modelo: google/gemma-4-26b-a4b-it:free, google/gemma-4-31b-it:free
- Chave de API: OPENAI_API_KEY
- CSV de entrada: samples/extrato_1_mes.csv

*Arquivo: `parte3_erro_20260826-171642.md`*

### Erro

```text
[OpenRouter/OPENAI_API_KEY | google/gemma-4-31b-it:free] RateLimitError: Error code: 429 - {'error': {'message': 'Provider returned error', 'code': 429, 'metadata': {'raw': 'google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations', 'provider_name': 'Google AI Studio', 'is_byok': False, 'provider_error_code': '429', 'limit_source': 'upstream_provider_shared_pool', 'remedy_hint': 'Retry shortly, add your own provider key (https://openrouter.ai/settings/integrations), or route to another provider with provider routing: https://openrouter.ai/docs/features/provider-routing'}}, 'user_id': 'user_3HAnyQU9OrbN5ImHaGaPrZYLqFk'}

[OpenRouter/OPENAI_API_KEY | google/gemma-4-26b-a4b-it:free] RateLimitError: Error code: 429 - {'error': {'message': 'Provider returned error', 'code': 429, 'metadata': {'raw': 'google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations', 'provider_name': 'Google AI Studio', 'is_byok': False, 'provider_error_code': '429', 'limit_source': 'upstream_provider_shared_pool', 'remedy_hint': 'Retry shortly, add your own provider key (https://openrouter.ai/settings/integrations), or route to another provider with provider routing: https://openrouter.ai/docs/features/provider-routing'}}, 'user_id': 'user_3HAnyQU9OrbN5ImHaGaPrZYLqFk'}
```

## Parte 3 — extrato de 1 mês (texto livre)

- Timestamp: 2026-08-26T17:21:07
- Modelo: gemma-4-31b-it
- Chave de API: GoogleAIStudio/chave-pessoal
- CSV de entrada: samples/extrato_1_mes.csv

*Arquivo: `parte3_extrato_1_mes_20260826-172107.md`*

### Output

```text
<thought>
*   Role: Personal Finance Analyst.
*   Input: Raw CSV content of a bank statement.
*   Tasks:
    1.  Classify each transaction into a category.
    2.  Calculate total spent per category.
    3.  Identify anomalous transactions.
    4.  Compare the two most recent months (if applicable).
*   Language: Brazilian Portuguese.

    *   Columns: `data` (date), `descrição` (description), `valor` (value), `tipo` (type).
    *   Period: All entries are from March 2024 (`2024-03`).
    *   Entry: Salary (4500.00).
    *   Exits: Various (Rent, Groceries, Transport, Food, Subscriptions, Fuel, Health, Entertainment, Education, Utilities, Shopping, Fitness).

    *   *ALUGUEL APTO 302* $\rightarrow$ Habitação (Housing)
    *   *SUPERMERCADO BOM PRECO* $\rightarrow$ Alimentação/Mercado (Groceries)
    *   *UBER *TRIP* (x2), *METRO SP RECARGA* $\rightarrow$ Transporte (Transport)
    *   *IFOOD (x2), *PADARIA CENTRAL*, *RESTAURANTE OUTBACK* $\rightarrow$ Alimentação/Lazer (Dining/Eating Out)
    *   *NETFLIX, *SPOTIFY $\rightarrow$ Assinaturas (Subscriptions)
    *   *POSTO IPIRANGA COMBUSTIVEL* $\rightarrow$ Transporte (Fuel/Car)
    *   *DROGARIA SAO PAULO* $\rightarrow$ Saúde (Health)
    *   *CINEMA CINEMARK* $\rightarrow$ Lazer (Entertainment)
    *   *LIVRARIA CULTURA CURSO ONLINE* $\rightarrow$ Educação (Education)
    *   *CONTA DE LUZ ENEL* $\rightarrow$ Habitação (Housing/Utilities)
    *   *PAG*7X4K9ZQ* $\rightarrow$ Outros/Diversos (Misc) - *Looks like a generic payment*
    *   *MAGAZINE LUIZA* $\rightarrow$ Compras/Eletrônicos (Shopping)
    *   *ACADEMIA SMARTFIT* $\rightarrow$ Saúde/Bem-estar (Health/Wellness)

    *   *Habitação:* 1450.00 + 198.45 = 1648.45
    *   *Alimentação (Mercado):* 312.75
    *   *Alimentação (Restaurantes/iFood):* 52.90 + 28.60 + 1890.00 + 44.10 = 2015.60
    *   *Transporte:* 21.40 + 180.00 + 33.80 + 50.00 = 285.20
    *   *Assinaturas:* 39.90 + 21.90 = 61.80
    *   *Saúde/Bem-estar:* 87.30 + 99.90 = 187.20
    *   *Lazer:* 64.00
    *   *Educação:* 249.00
    *   *Compras:* 459.90
    *   *Outros:* 27.00

    *   *Total Outflows:* $\approx$ 4999.15 (wait, let me double-check).
    *   Actually, calculating total spent is easier by summing the `saida` values.
    *   Check for anomalies: "RESTAURANTE OUTBACK" is -1890.00. This is extremely high for a single meal compared to everything else.

    *   The data provided only covers March 2024. Therefore, a comparison between months is not possible.

    *   Introduction.
    *   Categorized List (for clarity).
    *   Summary table (Category | Value).
    *   Financial Health Analysis (Income vs. Expense).
    *   Anomalies.
    *   Conclusion/Recommendation.</thought>Olá! Como analista de finanças pessoais, processei os dados do seu extrato bancário de março de 2024. Abaixo, apresento a análise detalhada dos seus gastos.

### 1. Classificação de Transações

| Data | Descrição | Categoria | Valor (R$) |
| :--- | :--- | :--- | :--- |
| 01/03 | SALARIO EMPRESA XYZ | **Renda** | +4.500,00 |
| 02/03 | ALUGUEL APTO 302 | Habitação | -1.450,00 |
| 03/03 | SUPERMERCADO BOM PRECO | Alimentação (Mercado) | -312,75 |
| 04/03 | UBER *TRIP | Transporte | -21,40 |
| 05/03 | IFOOD *RESTAURANTE SAO PAULO | Alimentação (Lazer) | -52,90 |
| 06/03 | NETFLIX.COM | Assinaturas | -39,90 |
| 07/03 | POSTO IPIRANGA COMBUSTIVEL | Transporte | -180,00 |
| 08/03 | DROGARIA SAO PAULO | Saúde | -87,30 |
| 09/03 | PADARIA CENTRAL | Alimentação (Lazer) | -28,60 |
| 10/03 | SPOTIFY BRASIL | Assinaturas | -21,90 |
| 12/03 | CINEMA CINEMARK | Lazer | -64,00 |
| 14/03 | UBER *TRIP | Transporte | -33,80 |
| 15/03 | RESTAURANTE OUTBACK | Alimentação (Lazer) | -1.890,00 |
| 17/03 | LIVRARIA CULTURA CURSO ONLINE | Educação | -249,00 |
| 19/03 | CONTA DE LUZ ENEL | Habitação | -198,45 |
| 21/03 | PAG*7X4K9ZQ | Outros/Diversos | -27,00 |
| 23/03 | MAGAZINE LUIZA | Compras | -459,90 |
| 25/03 | ACADEMIA SMARTFIT | Saúde/Bem-estar | -99,90 |
| 27/03 | IFOOD *LANCHONETE | Alimentação (Lazer) | -44,10 |
| 29/03 | METRO SP RECARGA | Transporte | -50,00 |

---

### 2. Resumo de Gastos por Categoria

| Categoria | Total Gasto (R$) | % do Gasto Total |
| :--- | :--- | :--- |
| **Alimentação (Lazer/Restaurantes)** | 2.015,60 | 40,4% |
| **Habitação** | 1.648,45 | 33,0% |
| **Compras** | 459,90 | 9,2% |
| **Transporte** | 285,20 | 5,7% |
| **Educação** | 249,00 | 5,0% |
| **Saúde/Bem-estar** | 187,20 | 3,8% |
| **Alimentação (Mercado)** | 312,75 | 6,3% |
| **Assinaturas** | 61,80 | 1,2% |
| **Lazer** | 64,00 | 1,3% |
| **Outros** | 27,00 | 0,5% |
| **TOTAL GERAL** | **4.999,15** | **100%** |

---

### 3. Análise de Saúde Financeira

*   **Balanço do Mês:**
    *   Entradas: R$ 4.500,00
    *   Saídas: R$ 4.999,15
    *   **Resultado: Saldo Negativo de R$ 499,15**
*   **Observação:** Você gastou mais do que recebeu neste mês, indicando que utilizou reservas financeiras ou entrou no cheque especial.

### 4. Transações Anômalas

Identifiquei a seguinte anomalia:
*   **RESTAURANTE OUTBACK (15/03) - R$ 1.890,00**: Este gasto é extremamente elevado para a categoria de alimentação, representando sozinho quase 38% de todos os seus gastos no mês. É um valor atípico comparado às outras refeições (iFood, Padaria) e foi o principal motivo do saldo negativo do mês.

### 5. Comparativo Mensal

*   **Análise:** O extrato fornecido contém dados de apenas um mês (Março/2024). Portanto, não há dados suficientes para realizar a comparação entre os dois meses mais recentes.

---

**💡 Recomendação do Analista:**
O seu custo fixo de habitação está equilibrado, porém o gasto com "Alimentação Fora de Casa" está excessivo. Caso o gasto no Outback tenha sido um evento único e extraordinário, a situação é pontual. Caso contrário, recomendo a criação de um teto mensal para lazer gastronômico para evitar que o saldo final do mês fique negativo.
```

## Parte 4 — extrato de 1 mês (prompt refinado)

- Timestamp: 2026-08-26T17:22:25
- Modelo: gemma-4-31b-it
- Chave de API: GoogleAIStudio/chave-pessoal
- CSV de entrada: samples/extrato_1_mes.csv

*Arquivo: `parte4_extrato_1_mes_20260826-172225.md`*

### Output

```text
<thought>*   Role: Personal Finance Analyst.
    *   Input: CSV text (`data`, `descrição`, `valor`, `tipo`).
    *   Task:
        1. Classify expenses into specific categories.
        2. Sum expenses by category and count transactions.
        3. Calculate total spend and period.
        4. Identify anomalies (values significantly higher than the category average).
        5. Compare months (if 2+ months present).
    *   Categories: Alimentação, Transporte, Moradia, Saúde, Educação, Lazer, Compras, Serviços/Assinaturas, Não identificado.
    *   Business Rules:
        *   Ignore inputs (positive values/salaries).
        *   Use absolute values for sums.
        *   Anomalies = order of magnitude above the average of others in that category.
        *   Only compare months if 2+ months exist.
        *   Formatting: Exact sections and order.

    *   2024-03-01, SALARIO EMPRESA XYZ, 4500.00, entrada -> IGNORE
    *   2024-03-02, ALUGUEL APTO 302, -1450.00, saida -> Moradia
    *   2024-03-03, SUPERMERCADO BOM PRECO, -312.75, saida -> Alimentação
    *   2024-03-04, UBER *TRIP, -21.40, saida -> Transporte
    *   2024-03-05, IFOOD *RESTAURANTE SAO PAULO, -52.90, saida -> Alimentação
    *   2024-03-06, NETFLIX.COM, -39.90, saida -> Serviços/Assinaturas
    *   2024-03-07, POSTO IPIRANGA COMBUSTIVEL, -180.00, saida -> Transporte
    *   2024-03-08, DROGARIA SAO PAULO, -87.30, saida -> Saúde
    *   2024-03-09, PADARIA CENTRAL, -28.60, saida -> Alimentação
    *   2024-03-10, SPOTIFY BRASIL, -21.90, saida -> Serviços/Assinaturas
    *   2024-03-12, CINEMA CINEMARK, -64.00, saida -> Lazer
    *   2024-03-14, UBER *TRIP, -33.80, saida -> Transporte
    *   2024-03-15, RESTAURANTE OUTBACK, -1890.00, saida -> Alimentação
    *   2024-03-17, LIVRARIA CULTURA CURSO ONLINE, -249.00, saida -> Educação
    *   2024-03-19, CONTA DE LUZ ENEL, -198.45, saida -> Moradia
    *   2024-03-21, PAG*7X4K9ZQ, -27.00, saida -> Não identificado
    *   2024-03-23, MAGAZINE LUIZA, -459.90, saida -> Compras
    *   2024-03-25, ACADEMIA SMARTFIT, -99.90, saida -> Saúde (or Lazer/Serviços? Usually Saúde/Bem-estar) ->Let's use Saúde as it fits fitness/health.
    *   2024-03-27, IFOOD *LANCHONETE, -44.10, saida -> Alimentação
    *   2024-03-29, METRO SP RECARGA, -50.00, saida -> Transporte

        *   Supermercado: 312.75
        *   iFood 1: 52.90
        *   Padaria: 28.60
        *   Outback: 1890.00
        *   iFood 2: 44.10
        *   Total: 312.75 + 52.90 + 28.60 + 1890.00 + 44.10 = 2328.35 (5 transações)

        *   Uber 1: 21.40
        *   Posto: 180.00
        *   Uber 2: 33.80
        *   Metro: 50.00
        *   Total: 21.40 + 180.00 + 33.80 + 50.00 = 285.20 (4 transações)

        *   Aluguel: 1450.00
        *   Luz: 198.45
        *   Total: 1648.45 (2 transações)

        *   Drogaria: 87.30
        *   Academia: 99.90
        *   Total: 187.20 (2 transações)

        *   Curso Online: 249.00
        *   Total: 249.00 (1 transação)

        *   Cinema: 64.00
        *   Total: 64.00 (1 transação)

        *   Magalu: 459.90
        *   Total: 459.90 (1 transação)

        *   Netflix: 39.90
        *   Spotify: 21.90
        *   Total: 61.80 (2 transações)

        *   PAG*7X4K9ZQ: 27.00
        *   Total: 27.00 (1 transação)

    *   Total: 2328.35 + 285.20 + 1648.45 + 187.20 + 249.00 + 64.00 + 459.90 + 61.80 + 27.00 = 5310.90

    *   Alimentação: Normal values are 312.75, 52.90, 28.60, 44.10. Average ≈ 109.59. Value 1890.00 is clearly an anomaly. (1890 / 109.59 ≈ 17.2x).
    *   Transporte: 180 is the highest, but compared to 21, 33, 50, it's not "order of magnitude" (only 4-8x), usually we look for extreme outliers. 1890 is definitely one.
    *   Moradia: 1450 (Aluguel) vs 198 (Luz). Rent is always higher, not an anomaly in a spending pattern.
    *   Others: No other extreme outliers.

    *   Period: 2024-03-01 to 2024-03-29.
    *   Only one month (March).
    *   Comparison: "Sem dados históricos: o extrato cobre apenas um mês".

    *   Período analisado: 2024-03-01 a 2024-03-29.
    *   Total gasto: R$ 5.310,90.
    *   Resumo:
        - Alimentação: R$ 2.328,35 (5 transações)
        - Transporte: R$ 285,20 (4 transações)
        - Moradia: R$ 1.648,45 (2 transações)
        - Saúde: R$ 187,20 (2 transações)
        - Educação: R$ 249,00 (1 transação)
        - Lazer: R$ 64,00 (1 transação)
        - Compras: R$ 459,90 (1 transação)
        - Serviços/Assinaturas: R$ 61,80 (2 transações)
        - Não identificado: R$ 27,00 (1 transação)
    *   Gastos anômalos:
        - 2024-03-15 | RESTAURANTE OUTBACK | R$ 1.890,00 — valor cerca de 17x a média das demais despesas de Alimentação no período.
    *   Comparação: Sem dados históricos: o extrato cobre apenas um mês.

    *   All categories used? Yes.
    *   Exact labels? Yes.
    *   Ignored salary? Yes.
    *   Absolute values used? Yes.
    *   Correct sections? Yes.
    *   Portuguese BR? Yes.

    *   Sum check:
        2328.35
        285.20
        1648.45
        187.20
        249.00
        64.00
        459.90
        61.80
        27.00
        = 5310.90. Correct.</thought>**Período analisado:** 2024-03-01 a 2024-03-29.
**Total gasto:** R$ 5.310,90.
**Resumo por categoria:**
- Alimentação: R$ 2.328,35 (5 transações)
- Transporte: R$ 285,20 (4 transações)
- Moradia: R$ 1.648,45 (2 transações)
- Saúde: R$ 187,20 (2 transações)
- Educação: R$ 249,00 (1 transação)
- Lazer: R$ 64,00 (1 transação)
- Compras: R$ 459,90 (1 transação)
- Serviços/Assinaturas: R$ 61,80 (2 transações)
- Não identificado: R$ 27,00 (1 transação)
**Gastos anômalos:**
- 2024-03-15 | RESTAURANTE OUTBACK | R$ 1.890,00 — valor cerca de 17x a média das demais despesas de Alimentação no período.
**Comparação com o mês anterior:**
Sem dados históricos: o extrato cobre apenas um mês.
```

## Parte 5 — extrato de 1 mês (schema do enunciado)

- Timestamp: 2026-08-26T17:23:06
- Modelo: gemma-4-31b-it
- Chave de API: GoogleAIStudio/chave-pessoal
- CSV de entrada: samples/extrato_1_mes.csv

*Arquivo: `parte5_extrato_1_mes_20260826-172306.md`*

### Output

```json
{
  "periodo_analisado": "2024-03-01 a 2024-03-29",
  "total_gasto": 4182.9,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 1648.45,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Alimentação",
      "valor_total": 1988.35,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Transporte",
      "valor_total": 285.2,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 161.7,
      "quantidade_transacoes": 3
    },
    {
      "categoria": "Saúde",
      "valor_total": 87.3,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Lazer",
      "valor_total": 64.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Educação",
      "valor_total": 249.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Compras",
      "valor_total": 459.9,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Não identificado",
      "valor_total": 27.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-03-15,RESTAURANTE OUTBACK, -1890.00",
      "motivo_anomalia": "valor cerca de 15x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": []
}
```

## Parte 5 — extrato de 1 mês (com campo de enumeração)

- Timestamp: 2026-08-26T18:47:55
- Modelo: gemma-4-31b-it
- Chave de API: GoogleAIStudio/chave-pessoal
- CSV de entrada: samples/extrato_1_mes.csv

*Arquivo: `parte5_extrato_1_mes_20260826-184755.md`*

### Output

```json
{
  "transacoes": [
    {
      "data": "2024-03-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 312.75,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-04",
      "descricao": "UBER *TRIP",
      "valor": 21.4,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 52.9,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-07",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 180.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-08",
      "descricao": "DROGARIA SAO PAULO",
      "valor": 87.3,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-03",
      "descricao": "PADARIA CENTRAL",
      "valor": 28.6,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-10",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-12",
      "descricao": "CINEMA CINEMARK",
      "valor": 64.0,
      "categoria": "Lazer"
    },
    {
      "data": "2024-03-14",
      "descricao": "UBER *TRIP",
      "valor": 33.8,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-15",
      "descricao": "RESTAURANTE OUTBACK",
      "valor": 1890.0,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-17",
      "descricao": "LIVRARIA CULTURA CURSO ONLINE",
      "valor": 249.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-03-19",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 198.45,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-21",
      "descricao": "PAG*7X4K9ZQ",
      "valor": 27.0,
      "categoria": "Não identificado"
    },
    {
      "data": "2024-03-23",
      "descricao": "MAGAZINE LUIZA",
      "valor": 459.9,
      "categoria": "Compras"
    },
    {
      "data": "2024-03-25",
      "descricao": "ACADEMIA SMARTFIT",
      "valor": 99.9,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-27",
      "descricao": "IFOOD *LANCHONETE",
      "valor": 44.1,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-29",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-09",
      "descricao": "Tarefas extras",
      "valor": 0.0,
      "categoria": "Não identificado"
    }
  ],
  "periodo_analisado": "2024-03-01 a 2024-03-29",
  "total_gasto": 5344.7,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 1648.45,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Alimentação",
      "valor_total": 2238.35,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Transporte",
      "valor_total": 285.2,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 61.8,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Saúde",
      "valor_total": 187.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 64.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Educação",
      "valor_total": 249.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Compras",
      "valor_total": 459.9,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Não identificado",
      "valor_total": 27.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-03-15, RESTAURANTE OUTBACK, 1890.0",
      "motivo_anomalia": "valor cerca de 10x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": []
}
```

## parte5_extrato_1_mes_20260826-195401.md

- Timestamp: 2026-08-26T19:54:01
- Modelo: gemma-4-31b-it
- Chave de API: GoogleAIStudio/chave-pessoal
- CSV de entrada: samples/extrato_1_mes.csv

*Arquivo: `parte5_extrato_1_mes_20260826-195401.md`*

### Output

```json
{
  "transacoes": [
    {
      "data": "2024-03-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 312.75,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-04",
      "descricao": "UBER *TRIP",
      "valor": 21.4,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 52.9,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-07",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 180.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-08",
      "descricao": "DROGARIA SAO PAULO",
      "valor": 87.3,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-03",
      "descricao": "PADARIA CENTRAL",
      "valor": 28.6,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-10",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-12",
      "descricao": "CINEMA CINEMARK",
      "valor": 64.0,
      "categoria": "Lazer"
    },
    {
      "data": "2024-03-14",
      "descricao": "UBER *TRIP",
      "valor": 33.8,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-15",
      "descricao": "RESTAURANTE OUTBACK",
      "valor": 1890.0,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-17",
      "descricao": "LIVRARIA CULTURA CURSO ONLINE",
      "valor": 249.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-03-19",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 198.45,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-21",
      "descricao": "PAG*7X4K9ZQ",
      "valor": 27.0,
      "categoria": "Não identificado"
    },
    {
      "data": "2024-03-23",
      "descricao": "MAGAZINE LUIZA",
      "valor": 459.9,
      "categoria": "Compras"
    },
    {
      "data": "2024-03-25",
      "descricao": "ACADEMIA SMARTFIT",
      "valor": 99.9,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-27",
      "descricao": "IFOOD *LANCHONETE",
      "valor": 44.1,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-29",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-09",
      "descricao": " እየሱስce",
      "valor": 28.6,
      "categoria": "Alimentação"
    }
  ],
  "periodo_analisado": "2024-03-01 a 2024-03-29",
  "total_gasto": 5435.0,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 1648.45,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Alimentação",
      "valor_total": 2266.35,
      "quantidade_transacoes": 5
    },
    {
      "categoria": "Transporte",
      "valor_total": 285.2,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 61.8,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Saúde",
      "valor_total": 187.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 64.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Educação",
      "valor_total": 249.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Não identificado",
      "valor_total": 27.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Compras",
      "valor_total": 459.9,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-03-15,RESTAURANTE OUTBACK,1890.0",
      "motivo_anomalia": "valor cerca de 15x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": []
}
```

## Parte 5 — extrato de 2 meses (schema do enunciado)

- Timestamp: 2026-08-26T17:23:41
- Modelo: gemma-4-31b-it
- Chave de API: GoogleAIStudio/chave-pessoal
- CSV de entrada: samples/extrato_2_meses.csv

*Arquivo: `parte5_extrato_2_meses_20260826-172341.md`*

### Output

```json
{
  "periodo_analisado": "2024-03-01 a 2024-04-28",
  "total_gasto": 7613.35,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 3101.3,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Alimentação",
      "valor_total": 2843.55,
      "quantidade_transacoes": 5
    },
    {
      "categoria": "Transporte",
      "valor_total": 534.6,
      "quantidade_transacoes": 6
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 203.4,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Compras",
      "valor_total": 344.9,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Educação",
      "valor_total": 178.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Saúde",
      "valor_total": 424.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 130.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Não identificado",
      "valor_total": 33.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-04-14,RESTAURANTE OUTBACK,-2450.00",
      "motivo_anomalia": "valor cerca de 25x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": [
    {
      "categoria": "Moradia",
      "valor_atual": 1654.1,
      "valor_anterior": 1637.2,
      "variacao": "+1.03%"
    },
    {
      "categoria": "Alimentação",
      "valor_atual": 2853.25,
      "valor_anterior": 382.8,
      "variacao": "+645.3%"
    },
    {
      "categoria": "Transporte",
      "valor_atual": 320.3,
      "valor_anterior": 214.3,
      "variacao": "+49.46%"
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_atual": 61.8,
      "valor_anterior": 61.8,
      "variacao": "0%"
    },
    {
      "categoria": "Compras",
      "valor_atual": 129.9,
      "valor_anterior": 215.0,
      "variacao": "-39.58%"
    },
    {
      "categoria": "Educação",
      "valor_atual": 89.0,
      "valor_anterior": 89.0,
      "variacao": "0%"
    },
    {
      "categoria": "Saúde",
      "valor_atual": 350.0,
      "valor_anterior": 74.2,
      "variacao": "+372.4%"
    },
    {
      "categoria": "Lazer",
      "valor_atual": 72.0,
      "valor_anterior": 58.0,
      "variacao": "+24.14%"
    },
    {
      "categoria": "Não identificado",
      "valor_atual": 33.0,
      "valor_anterior": 0.0,
      "variacao": "Novo gasto"
    }
  ]
}
```

## Parte 5 — extrato de 2 meses (com campo de enumeração)

- Timestamp: 2026-08-26T18:49:16
- Modelo: gemma-4-31b-it
- Chave de API: GoogleAIStudio/chave-pessoal
- CSV de entrada: samples/extrato_2_meses.csv

*Arquivo: `parte5_extrato_2_meses_20260826-184916.md`*

### Output

```json
{
  "transacoes": [
    {
      "data": "2024-03-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 298.4,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 52.9,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-07",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 160.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-09",
      "descricao": "UBER *TRIP",
      "valor": 24.3,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-11",
      "descricao": "DROGARIA SAO PAULO",
      "valor": 74.2,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-13",
      "descricao": "CINEMA CINEMARK",
      "valor": 58.0,
      "categoria": "Lazer"
    },
    {
      "data": "2024-03-16",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 187.2,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-18",
      "descricao": "PADARIA CENTRAL",
      "valor": 31.5,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-20",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-22",
      "descricao": "MAGAZINE LUIZA",
      "valor": 215.0,
      "categoria": "Compras"
    },
    {
      "data": "2024-03-25",
      "descricao": "PLATAFORMA ALURA CURSOS",
      "valor": 89.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-03-28",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-04-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 341.85,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-04",
      "descricao": "UBER *TRIP",
      "valor": 28.7,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 61.4,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-08",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 210.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-10",
      "descricao": "CONSULTA MEDICA CLINICA VIDA",
      "valor": 350.0,
      "categoria": "Saúde"
    },
    {
      "data": "2024-04-12",
      "descricao": "UBER *TRIP",
      "valor": 41.6,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-14",
      "descricao": "RESTAURANTE OUTBACK",
      "valor": 2450.0,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-15",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 204.1,
      "categoria": "Moradia"
    },
    {
      "data": "2024-04-17",
      "descricao": "PAG*7X4K9ZQ",
      "valor": 33.0,
      "categoria": "Não identificado"
    },
    {
      "data": "2024-04-19",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-21",
      "descricao": "MAGAZINE LUIZA",
      "valor": 129.9,
      "categoria": "Compras"
    },
    {
      "data": "2024-04-23",
      "descricao": "PLATAFORMA ALURA CURSOS",
      "valor": 89.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-04-26",
      "descricao": "METRO SP RE carved",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-28",
      "descricao": "CINEMA CINEMARK",
      "valor": 72.0,
      "categoria": "Lazer"
    }
  ],
  "periodo_analisado": "2024-03-01 a 2024-04-28",
  "total_gasto": 8572.35,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 3291.3,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Alimentação",
      "valor_total": 3245.65,
      "quantidade_transacoes": 5
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 123.6,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Transporte",
      "valor_total": 584.6,
      "quantidade_transacoes": 7
    },
    {
      "categoria": "Saúde",
      "valor_total": 424.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 130.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Compras",
      "valor_total": 344.9,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Educação",
      "valor_total": 178.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Não identificado",
      "valor_total": 33.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-04-14, RESTAURANTE OUTBACK, 2450.00",
      "motivo_anomalia": "valor cerca de 6x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": [
    {
      "categoria": "Moradia",
      "valor_atual": 1637.1,
      "valor_anterior": 1637.2,
      "variacao": "-0.01%"
    },
    {
      "categoria": "Alimentação",
      "valor_atual": 2853.25,
      "valor_anterior": 383.8,
      "variacao": "+640%"
    },
    {
      "categoria": "Transporte",
      "valor_atual": 320.3,
      "valor_anterior": 234.3,
      "variacao": "+36.7%"
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_atual": 61.8,
      "valor_anterior": 61.8,
      "variacao": "0%"
    },
    {
      "categoria": "Saúde",
      "valor_atual": 350.0,
      "valor_anterior": 74.2,
      "variacao": "+371%"
    },
    {
      "categoria": "Lazer",
      "valor_atual": 72.0,
      "valor_anterior": 58.0,
      "variacao": "+24.1%"
    },
    {
      "categoria": "Compras",
      "valor_atual": 129.9,
      "valor_anterior": 215.0,
      "variacao": "-39.6%"
    },
    {
      "categoria": "Educação",
      "valor_atual": 89.0,
      "valor_anterior": 89.0,
      "variacao": "0%"
    }
  ]
}
```

## parte5_extrato_2_meses_20260826-195503.md

- Timestamp: 2026-08-26T19:55:03
- Modelo: gemma-4-31b-it
- Chave de API: GoogleAIStudio/chave-pessoal
- CSV de entrada: samples/extrato_2_meses.csv

*Arquivo: `parte5_extrato_2_meses_20260826-195503.md`*

### Output

```json
{
  "transacoes": [
    {
      "data": "2024-03-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 298.4,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 52.9,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-07",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 160.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-09",
      "descricao": "UBER *TRIP",
      "valor": 24.3,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-11",
      "descricao": "DROGARIA SAO PAULO",
      "valor": 74.2,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-13",
      "descricao": "CINEMA CINEMARK",
      "valor": 58.0,
      "categoria": "Lazer"
    },
    {
      "data": "2024-03-16",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 187.2,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-18",
      "descricao": "PADARIA CENTRAL",
      "valor": 31.5,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-20",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-22",
      "descricao": "MAGAZINE LUIZA",
      "valor": 215.0,
      "categoria": "Compras"
    },
    {
      "data": "2024-03-25",
      "descricao": "PLATAFORMA ALURA CURSOS",
      "valor": 89.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-03-28",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-04-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 341.85,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-04",
      "descricao": "UBER *TRIP",
      "valor": 28.7,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 61.4,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-06",
      "descricao": "descricao own",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-08",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 210.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-10",
      "descricao": "CONSULTA MEDICA CLINICA VIDA",
      "valor": 350.0,
      "categoria": "Saúde"
    },
    {
      "data": "2024-04-12",
      "descricao": "UBER *TRIP",
      "valor": 41.6,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-14",
      "descricao": "RESTAURANTE OUTBACK",
      "valor": 2450.0,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-15",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 204.1,
      "categoria": "Moradia"
    },
    {
      "data": "2024-04-17",
      "descricao": "PAG*7X4K9ZQ",
      "valor": 33.0,
      "categoria": "Não identificado"
    },
    {
      "data": "2024-04-19",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-21",
      "descricao": "MAGAZINE LUIZA",
      "valor": 129.9,
      "categoria": "Compras"
    },
    {
      "data": "2024-04-23",
      "descricao": "PLATAFORMA ALURA CURSOS",
      "valor": 89.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-04-26",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-28",
      "descricao": "CINEMA CINEMARK",
      "valor": 72.0,
      "categoria": "Lazer"
    }
  ],
  "periodo_analisado": "2024-03-01 a 2024-04-28",
  "total_gasto": 8441.45,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 3291.3,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Alimentação",
      "valor_total": 3285.55,
      "quantidade_transacoes": 6
    },
    {
      "categoria": "Transporte",
      "valor_total": 574.6,
      "quantidade_transacoes": 7
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 123.6,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Saúde",
      "valor_total": 424.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 130.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Compras",
      "valor_total": 344.9,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Educação",
      "valor_total": 178.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Não identificado",
      "valor_total": 33.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-04-14, RESTAURANTE OUTBACK, 2450.0",
      "motivo_anomalia": "valor cerca de 8x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": [
    {
      "categoria": "Moradia",
      "valor_atual": 1654.1,
      "valor_anterior": 1637.2,
      "variacao": "+0.8%"
    },
    {
      "categoria": "Alimentação",
      "valor_atual": 2853.25,
      "valor_anterior": 382.8,
      "variacao": "+645.3%"
    },
    {
      "categoria": "Transporte",
      "valor_atual": 330.3,
      "valor_anterior": 234.3,
      "variacao": "+40.9%"
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_atual": 61.8,
      "valor_anterior": 61.8,
      "variacao": "0%"
    },
    {
      "categoria": "Saúde",
      "valor_atual": 350.0,
      "valor_anterior": 74.2,
      "variacao": "+371.7%"
    },
    {
      "categoria": "Lazer",
      "valor_atual": 72.0,
      "valor_anterior": 58.0,
      "variacao": "+24.1%"
    },
    {
      "categoria": "Compras",
      "valor_atual": 129.9,
      "valor_anterior": 215.0,
      "variacao": "-39.6%"
    },
    {
      "categoria": "Educação",
      "valor_atual": 89.0,
      "valor_anterior": 89.0,
      "variacao": "0%"
    }
  ]
}
```

# Apêndice A — CSVs de teste


## `samples/extrato_1_mes.csv`

```csv
data,descrição,valor,tipo
2024-03-01,SALARIO EMPRESA XYZ,4500.00,entrada
2024-03-02,ALUGUEL APTO 302,-1450.00,saida
2024-03-03,SUPERMERCADO BOM PRECO,-312.75,saida
2024-03-04,UBER *TRIP,-21.40,saida
2024-03-05,IFOOD *RESTAURANTE SAO PAULO,-52.90,saida
2024-03-06,NETFLIX.COM,-39.90,saida
2024-03-07,POSTO IPIRANGA COMBUSTIVEL,-180.00,saida
2024-03-08,DROGARIA SAO PAULO,-87.30,saida
2024-03-09,PADARIA CENTRAL,-28.60,saida
2024-03-10,SPOTIFY BRASIL,-21.90,saida
2024-03-12,CINEMA CINEMARK,-64.00,saida
2024-03-14,UBER *TRIP,-33.80,saida
2024-03-15,RESTAURANTE OUTBACK,-1890.00,saida
2024-03-17,LIVRARIA CULTURA CURSO ONLINE,-249.00,saida
2024-03-19,CONTA DE LUZ ENEL,-198.45,saida
2024-03-21,PAG*7X4K9ZQ,-27.00,saida
2024-03-23,MAGAZINE LUIZA,-459.90,saida
2024-03-25,ACADEMIA SMARTFIT,-99.90,saida
2024-03-27,IFOOD *LANCHONETE,-44.10,saida
2024-03-29,METRO SP RECARGA,-50.00,saida
```

## `samples/extrato_2_meses.csv`

```csv
data,descrição,valor,tipo
2024-03-01,SALARIO EMPRESA XYZ,4500.00,entrada
2024-03-02,ALUGUEL APTO 302,-1450.00,saida
2024-03-03,SUPERMERCADO BOM PRECO,-298.40,saida
2024-03-05,IFOOD *RESTAURANTE SAO PAULO,-52.90,saida
2024-03-06,NETFLIX.COM,-39.90,saida
2024-03-07,POSTO IPIRANGA COMBUSTIVEL,-160.00,saida
2024-03-09,UBER *TRIP,-24.30,saida
2024-03-11,DROGARIA SAO PAULO,-74.20,saida
2024-03-13,CINEMA CINEMARK,-58.00,saida
2024-03-16,CONTA DE LUZ ENEL,-187.20,saida
2024-03-18,PADARIA CENTRAL,-31.50,saida
2024-03-20,SPOTIFY BRASIL,-21.90,saida
2024-03-22,MAGAZINE LUIZA,-215.00,saida
2024-03-25,PLATAFORMA ALURA CURSOS,-89.00,saida
2024-03-28,METRO SP RECARGA,-50.00,saida
2024-04-01,SALARIO EMPRESA XYZ,4500.00,entrada
2024-04-02,ALUGUEL APTO 302,-1450.00,saida
2024-04-03,SUPERMERCADO BOM PRECO,-341.85,saida
2024-04-04,UBER *TRIP,-28.70,saida
2024-04-05,IFOOD *RESTAURANTE SAO PAULO,-61.40,saida
2024-04-06,NETFLIX.COM,-39.90,saida
2024-04-08,POSTO IPIRANGA COMBUSTIVEL,-210.00,saida
2024-04-10,CONSULTA MEDICA CLINICA VIDA,-350.00,saida
2024-04-12,UBER *TRIP,-41.60,saida
2024-04-14,RESTAURANTE OUTBACK,-2450.00,saida
2024-04-15,CONTA DE LUZ ENEL,-204.10,saida
2024-04-17,PAG*7X4K9ZQ,-33.00,saida
2024-04-19,SPOTIFY BRASIL,-21.90,saida
2024-04-21,MAGAZINE LUIZA,-129.90,saida
2024-04-23,PLATAFORMA ALURA CURSOS,-89.00,saida
2024-04-26,METRO SP RECARGA,-50.00,saida
2024-04-28,CINEMA CINEMARK,-72.00,saida
```

# Apêndice B — Saídas validadas pelo schema Pydantic


## Parte 5 — extrato de 1 mês (schema do enunciado)

*Arquivo: `parte5_extrato_1_mes_20260826-172306.json`*

```json
{
  "periodo_analisado": "2024-03-01 a 2024-03-29",
  "total_gasto": 4182.9,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 1648.45,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Alimentação",
      "valor_total": 1988.35,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Transporte",
      "valor_total": 285.2,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 161.7,
      "quantidade_transacoes": 3
    },
    {
      "categoria": "Saúde",
      "valor_total": 87.3,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Lazer",
      "valor_total": 64.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Educação",
      "valor_total": 249.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Compras",
      "valor_total": 459.9,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Não identificado",
      "valor_total": 27.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-03-15,RESTAURANTE OUTBACK, -1890.00",
      "motivo_anomalia": "valor cerca de 15x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": []
}
```

## Parte 5 — extrato de 1 mês (com campo de enumeração)

*Arquivo: `parte5_extrato_1_mes_20260826-184755.json`*

```json
{
  "transacoes": [
    {
      "data": "2024-03-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 312.75,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-04",
      "descricao": "UBER *TRIP",
      "valor": 21.4,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 52.9,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-07",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 180.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-08",
      "descricao": "DROGARIA SAO PAULO",
      "valor": 87.3,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-03",
      "descricao": "PADARIA CENTRAL",
      "valor": 28.6,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-10",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-12",
      "descricao": "CINEMA CINEMARK",
      "valor": 64.0,
      "categoria": "Lazer"
    },
    {
      "data": "2024-03-14",
      "descricao": "UBER *TRIP",
      "valor": 33.8,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-15",
      "descricao": "RESTAURANTE OUTBACK",
      "valor": 1890.0,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-17",
      "descricao": "LIVRARIA CULTURA CURSO ONLINE",
      "valor": 249.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-03-19",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 198.45,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-21",
      "descricao": "PAG*7X4K9ZQ",
      "valor": 27.0,
      "categoria": "Não identificado"
    },
    {
      "data": "2024-03-23",
      "descricao": "MAGAZINE LUIZA",
      "valor": 459.9,
      "categoria": "Compras"
    },
    {
      "data": "2024-03-25",
      "descricao": "ACADEMIA SMARTFIT",
      "valor": 99.9,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-27",
      "descricao": "IFOOD *LANCHONETE",
      "valor": 44.1,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-29",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-09",
      "descricao": "Tarefas extras",
      "valor": 0.0,
      "categoria": "Não identificado"
    }
  ],
  "periodo_analisado": "2024-03-01 a 2024-03-29",
  "total_gasto": 5344.7,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 1648.45,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Alimentação",
      "valor_total": 2238.35,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Transporte",
      "valor_total": 285.2,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 61.8,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Saúde",
      "valor_total": 187.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 64.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Educação",
      "valor_total": 249.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Compras",
      "valor_total": 459.9,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Não identificado",
      "valor_total": 27.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-03-15, RESTAURANTE OUTBACK, 1890.0",
      "motivo_anomalia": "valor cerca de 10x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": []
}
```

## parte5_extrato_1_mes_20260826-195401.json

*Arquivo: `parte5_extrato_1_mes_20260826-195401.json`*

```json
{
  "transacoes": [
    {
      "data": "2024-03-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 312.75,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-04",
      "descricao": "UBER *TRIP",
      "valor": 21.4,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 52.9,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-07",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 180.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-08",
      "descricao": "DROGARIA SAO PAULO",
      "valor": 87.3,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-03",
      "descricao": "PADARIA CENTRAL",
      "valor": 28.6,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-10",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-12",
      "descricao": "CINEMA CINEMARK",
      "valor": 64.0,
      "categoria": "Lazer"
    },
    {
      "data": "2024-03-14",
      "descricao": "UBER *TRIP",
      "valor": 33.8,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-15",
      "descricao": "RESTAURANTE OUTBACK",
      "valor": 1890.0,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-17",
      "descricao": "LIVRARIA CULTURA CURSO ONLINE",
      "valor": 249.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-03-19",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 198.45,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-21",
      "descricao": "PAG*7X4K9ZQ",
      "valor": 27.0,
      "categoria": "Não identificado"
    },
    {
      "data": "2024-03-23",
      "descricao": "MAGAZINE LUIZA",
      "valor": 459.9,
      "categoria": "Compras"
    },
    {
      "data": "2024-03-25",
      "descricao": "ACADEMIA SMARTFIT",
      "valor": 99.9,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-27",
      "descricao": "IFOOD *LANCHONETE",
      "valor": 44.1,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-29",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-09",
      "descricao": " እየሱስce",
      "valor": 28.6,
      "categoria": "Alimentação"
    }
  ],
  "periodo_analisado": "2024-03-01 a 2024-03-29",
  "total_gasto": 5435.0,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 1648.45,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Alimentação",
      "valor_total": 2266.35,
      "quantidade_transacoes": 5
    },
    {
      "categoria": "Transporte",
      "valor_total": 285.2,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 61.8,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Saúde",
      "valor_total": 187.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 64.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Educação",
      "valor_total": 249.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Não identificado",
      "valor_total": 27.0,
      "quantidade_transacoes": 1
    },
    {
      "categoria": "Compras",
      "valor_total": 459.9,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-03-15,RESTAURANTE OUTBACK,1890.0",
      "motivo_anomalia": "valor cerca de 15x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": []
}
```

## Parte 5 — extrato de 2 meses (schema do enunciado)

*Arquivo: `parte5_extrato_2_meses_20260826-172341.json`*

```json
{
  "periodo_analisado": "2024-03-01 a 2024-04-28",
  "total_gasto": 7613.35,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 3101.3,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Alimentação",
      "valor_total": 2843.55,
      "quantidade_transacoes": 5
    },
    {
      "categoria": "Transporte",
      "valor_total": 534.6,
      "quantidade_transacoes": 6
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 203.4,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Compras",
      "valor_total": 344.9,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Educação",
      "valor_total": 178.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Saúde",
      "valor_total": 424.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 130.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Não identificado",
      "valor_total": 33.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-04-14,RESTAURANTE OUTBACK,-2450.00",
      "motivo_anomalia": "valor cerca de 25x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": [
    {
      "categoria": "Moradia",
      "valor_atual": 1654.1,
      "valor_anterior": 1637.2,
      "variacao": "+1.03%"
    },
    {
      "categoria": "Alimentação",
      "valor_atual": 2853.25,
      "valor_anterior": 382.8,
      "variacao": "+645.3%"
    },
    {
      "categoria": "Transporte",
      "valor_atual": 320.3,
      "valor_anterior": 214.3,
      "variacao": "+49.46%"
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_atual": 61.8,
      "valor_anterior": 61.8,
      "variacao": "0%"
    },
    {
      "categoria": "Compras",
      "valor_atual": 129.9,
      "valor_anterior": 215.0,
      "variacao": "-39.58%"
    },
    {
      "categoria": "Educação",
      "valor_atual": 89.0,
      "valor_anterior": 89.0,
      "variacao": "0%"
    },
    {
      "categoria": "Saúde",
      "valor_atual": 350.0,
      "valor_anterior": 74.2,
      "variacao": "+372.4%"
    },
    {
      "categoria": "Lazer",
      "valor_atual": 72.0,
      "valor_anterior": 58.0,
      "variacao": "+24.14%"
    },
    {
      "categoria": "Não identificado",
      "valor_atual": 33.0,
      "valor_anterior": 0.0,
      "variacao": "Novo gasto"
    }
  ]
}
```

## Parte 5 — extrato de 2 meses (com campo de enumeração)

*Arquivo: `parte5_extrato_2_meses_20260826-184916.json`*

```json
{
  "transacoes": [
    {
      "data": "2024-03-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 298.4,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 52.9,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-07",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 160.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-09",
      "descricao": "UBER *TRIP",
      "valor": 24.3,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-11",
      "descricao": "DROGARIA SAO PAULO",
      "valor": 74.2,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-13",
      "descricao": "CINEMA CINEMARK",
      "valor": 58.0,
      "categoria": "Lazer"
    },
    {
      "data": "2024-03-16",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 187.2,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-18",
      "descricao": "PADARIA CENTRAL",
      "valor": 31.5,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-20",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-22",
      "descricao": "MAGAZINE LUIZA",
      "valor": 215.0,
      "categoria": "Compras"
    },
    {
      "data": "2024-03-25",
      "descricao": "PLATAFORMA ALURA CURSOS",
      "valor": 89.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-03-28",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-04-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 341.85,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-04",
      "descricao": "UBER *TRIP",
      "valor": 28.7,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 61.4,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-08",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 210.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-10",
      "descricao": "CONSULTA MEDICA CLINICA VIDA",
      "valor": 350.0,
      "categoria": "Saúde"
    },
    {
      "data": "2024-04-12",
      "descricao": "UBER *TRIP",
      "valor": 41.6,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-14",
      "descricao": "RESTAURANTE OUTBACK",
      "valor": 2450.0,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-15",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 204.1,
      "categoria": "Moradia"
    },
    {
      "data": "2024-04-17",
      "descricao": "PAG*7X4K9ZQ",
      "valor": 33.0,
      "categoria": "Não identificado"
    },
    {
      "data": "2024-04-19",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-21",
      "descricao": "MAGAZINE LUIZA",
      "valor": 129.9,
      "categoria": "Compras"
    },
    {
      "data": "2024-04-23",
      "descricao": "PLATAFORMA ALURA CURSOS",
      "valor": 89.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-04-26",
      "descricao": "METRO SP RE carved",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-28",
      "descricao": "CINEMA CINEMARK",
      "valor": 72.0,
      "categoria": "Lazer"
    }
  ],
  "periodo_analisado": "2024-03-01 a 2024-04-28",
  "total_gasto": 8572.35,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 3291.3,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Alimentação",
      "valor_total": 3245.65,
      "quantidade_transacoes": 5
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 123.6,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Transporte",
      "valor_total": 584.6,
      "quantidade_transacoes": 7
    },
    {
      "categoria": "Saúde",
      "valor_total": 424.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 130.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Compras",
      "valor_total": 344.9,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Educação",
      "valor_total": 178.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Não identificado",
      "valor_total": 33.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-04-14, RESTAURANTE OUTBACK, 2450.00",
      "motivo_anomalia": "valor cerca de 6x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": [
    {
      "categoria": "Moradia",
      "valor_atual": 1637.1,
      "valor_anterior": 1637.2,
      "variacao": "-0.01%"
    },
    {
      "categoria": "Alimentação",
      "valor_atual": 2853.25,
      "valor_anterior": 383.8,
      "variacao": "+640%"
    },
    {
      "categoria": "Transporte",
      "valor_atual": 320.3,
      "valor_anterior": 234.3,
      "variacao": "+36.7%"
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_atual": 61.8,
      "valor_anterior": 61.8,
      "variacao": "0%"
    },
    {
      "categoria": "Saúde",
      "valor_atual": 350.0,
      "valor_anterior": 74.2,
      "variacao": "+371%"
    },
    {
      "categoria": "Lazer",
      "valor_atual": 72.0,
      "valor_anterior": 58.0,
      "variacao": "+24.1%"
    },
    {
      "categoria": "Compras",
      "valor_atual": 129.9,
      "valor_anterior": 215.0,
      "variacao": "-39.6%"
    },
    {
      "categoria": "Educação",
      "valor_atual": 89.0,
      "valor_anterior": 89.0,
      "variacao": "0%"
    }
  ]
}
```

## parte5_extrato_2_meses_20260826-195503.json

*Arquivo: `parte5_extrato_2_meses_20260826-195503.json`*

```json
{
  "transacoes": [
    {
      "data": "2024-03-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 298.4,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 52.9,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-07",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 160.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-09",
      "descricao": "UBER *TRIP",
      "valor": 24.3,
      "categoria": "Transporte"
    },
    {
      "data": "2024-03-11",
      "descricao": "DROGARIA SAO PAULO",
      "valor": 74.2,
      "categoria": "Saúde"
    },
    {
      "data": "2024-03-13",
      "descricao": "CINEMA CINEMARK",
      "valor": 58.0,
      "categoria": "Lazer"
    },
    {
      "data": "2024-03-16",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 187.2,
      "categoria": "Moradia"
    },
    {
      "data": "2024-03-18",
      "descricao": "PADARIA CENTRAL",
      "valor": 31.5,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-03-20",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-03-22",
      "descricao": "MAGAZINE LUIZA",
      "valor": 215.0,
      "categoria": "Compras"
    },
    {
      "data": "2024-03-25",
      "descricao": "PLATAFORMA ALURA CURSOS",
      "valor": 89.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-03-28",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-02",
      "descricao": "ALUGUEL APTO 302",
      "valor": 1450.0,
      "categoria": "Moradia"
    },
    {
      "data": "2024-04-03",
      "descricao": "SUPERMERCADO BOM PRECO",
      "valor": 341.85,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-04",
      "descricao": "UBER *TRIP",
      "valor": 28.7,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-05",
      "descricao": "IFOOD *RESTAURANTE SAO PAULO",
      "valor": 61.4,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-06",
      "descricao": "descricao own",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-06",
      "descricao": "NETFLIX.COM",
      "valor": 39.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-08",
      "descricao": "POSTO IPIRANGA COMBUSTIVEL",
      "valor": 210.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-10",
      "descricao": "CONSULTA MEDICA CLINICA VIDA",
      "valor": 350.0,
      "categoria": "Saúde"
    },
    {
      "data": "2024-04-12",
      "descricao": "UBER *TRIP",
      "valor": 41.6,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-14",
      "descricao": "RESTAURANTE OUTBACK",
      "valor": 2450.0,
      "categoria": "Alimentação"
    },
    {
      "data": "2024-04-15",
      "descricao": "CONTA DE LUZ ENEL",
      "valor": 204.1,
      "categoria": "Moradia"
    },
    {
      "data": "2024-04-17",
      "descricao": "PAG*7X4K9ZQ",
      "valor": 33.0,
      "categoria": "Não identificado"
    },
    {
      "data": "2024-04-19",
      "descricao": "SPOTIFY BRASIL",
      "valor": 21.9,
      "categoria": "Serviços/Assinaturas"
    },
    {
      "data": "2024-04-21",
      "descricao": "MAGAZINE LUIZA",
      "valor": 129.9,
      "categoria": "Compras"
    },
    {
      "data": "2024-04-23",
      "descricao": "PLATAFORMA ALURA CURSOS",
      "valor": 89.0,
      "categoria": "Educação"
    },
    {
      "data": "2024-04-26",
      "descricao": "METRO SP RECARGA",
      "valor": 50.0,
      "categoria": "Transporte"
    },
    {
      "data": "2024-04-28",
      "descricao": "CINEMA CINEMARK",
      "valor": 72.0,
      "categoria": "Lazer"
    }
  ],
  "periodo_analisado": "2024-03-01 a 2024-04-28",
  "total_gasto": 8441.45,
  "resumo_por_categoria": [
    {
      "categoria": "Moradia",
      "valor_total": 3291.3,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Alimentação",
      "valor_total": 3285.55,
      "quantidade_transacoes": 6
    },
    {
      "categoria": "Transporte",
      "valor_total": 574.6,
      "quantidade_transacoes": 7
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_total": 123.6,
      "quantidade_transacoes": 4
    },
    {
      "categoria": "Saúde",
      "valor_total": 424.2,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Lazer",
      "valor_total": 130.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Compras",
      "valor_total": 344.9,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Educação",
      "valor_total": 178.0,
      "quantidade_transacoes": 2
    },
    {
      "categoria": "Não identificado",
      "valor_total": 33.0,
      "quantidade_transacoes": 1
    }
  ],
  "gastos_anomalos": [
    {
      "transacao": "2024-04-14, RESTAURANTE OUTBACK, 2450.0",
      "motivo_anomalia": "valor cerca de 8x a média das demais despesas de Alimentação no período"
    }
  ],
  "comparacao_mes_anterior": [
    {
      "categoria": "Moradia",
      "valor_atual": 1654.1,
      "valor_anterior": 1637.2,
      "variacao": "+0.8%"
    },
    {
      "categoria": "Alimentação",
      "valor_atual": 2853.25,
      "valor_anterior": 382.8,
      "variacao": "+645.3%"
    },
    {
      "categoria": "Transporte",
      "valor_atual": 330.3,
      "valor_anterior": 234.3,
      "variacao": "+40.9%"
    },
    {
      "categoria": "Serviços/Assinaturas",
      "valor_atual": 61.8,
      "valor_anterior": 61.8,
      "variacao": "0%"
    },
    {
      "categoria": "Saúde",
      "valor_atual": 350.0,
      "valor_anterior": 74.2,
      "variacao": "+371.7%"
    },
    {
      "categoria": "Lazer",
      "valor_atual": 72.0,
      "valor_anterior": 58.0,
      "variacao": "+24.1%"
    },
    {
      "categoria": "Compras",
      "valor_atual": 129.9,
      "valor_anterior": 215.0,
      "variacao": "-39.6%"
    },
    {
      "categoria": "Educação",
      "valor_atual": 89.0,
      "valor_anterior": 89.0,
      "variacao": "0%"
    }
  ]
}
```
