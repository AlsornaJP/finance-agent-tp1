# TP2 — Diagnóstico mensal em cadeia (least-to-most prompting)

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

## A tarefa e por que ela não cabe num prompt só

`python main.py diagnosticar --mes AAAA-MM` produz um diagnóstico do mês: o que se destacou, se isso está
dentro do recomendado pelo guia de orçamento e o que fazer. Feito num único prompt, o modelo precisaria ao
mesmo tempo somar, comparar meses, achar anomalias, consultar regras e redigir recomendações — a mesma
sobrecarga que, no TP1, levou a somas erradas e transações perdidas.

## Técnica: least-to-most

O problema é decomposto em subproblemas do mais simples ao mais complexo; cada etapa resolve o seu e
entrega a resposta, tipada, para a seguinte:

| Etapa | Subproblema | Executor | Entrada | Saída |
| --- | --- | --- | --- | --- |
| 1 | Quais são os números do mês? | Python, sem LLM | banco SQLite | `LevantamentoMensal` |
| 2 | O que nesses números merece atenção? | LLM | levantamento | `PontosDeAtencao` |
| 3 | Isso está dentro do recomendado? | RAG + LLM | pontos + trechos do guia recuperados por ponto | `AvaliacaoGuia` |
| 4 | O que fazer a respeito? | LLM | levantamento + avaliações | `DiagnosticoMensal` |

A etapa 1 não usa LLM: totais, percentuais, saldo, comparação com o mês anterior e transações atípicas vêm
das mesmas funções que alimentam as tools. As etapas 2 a 4 só interpretam números já prontos — cada prompt
diz explicitamente "não calcule valores novos". A etapa 2 também usa chain-of-thought pela ordem dos campos:
`dados` (os números que sustentam o ponto) vem antes de `motivo`.

Prompts completos: `INSTRUCTIONS_PONTOS_DE_ATENCAO`, `INSTRUCTIONS_CONFRONTO_GUIA` e
`INSTRUCTIONS_RECOMENDACOES` em `agent/prompts.py`, todos na anatomia de 4 componentes; cada log de execução
reproduz instructions, input e output de cada etapa.

## Execução final — abril de 2024

Log: `prompts/outputs/diagnosticar_2024-04_20261002-193420.md` (todas as etapas com `gemini-3.5-flash-lite`).

**Etapa 1 — levantamento (trecho):**

```json
"total": {"mes": "2024-04", "total_gasto": 5573.35, "quantidade_transacoes": 16,
          "renda": 4500.0, "saldo": -1073.35, "percentual_renda_gasto": 123.85},
"atipicas": [{"data": "2024-04-14", "descricao": "RESTAURANTE OUTBACK", "valor": 2450.0,
              "categoria": "Alimentação", "media_categoria": 157.21, "razao": 15.6}]
```

**Etapa 2 — pontos de atenção:**

| Assunto | Dados (copiados do levantamento) | Motivo |
| --- | --- | --- |
| Gasto total acima da renda | 123,85% da renda | mês fechou com gasto maior que a renda |
| Alimentação | 63,41% da renda | grande peso na renda |
| Moradia | 36,76% da renda | grande peso na renda |
| Alimentação | +645,36% sobre o mês anterior | variação acima de 30% |
| Saúde | +371,7% sobre o mês anterior | variação acima de 30% |

**Etapa 3 — trechos recuperados pelo RAG (2 por ponto) e confronto:**

| Ponto | Trechos recuperados | Situação |
| --- | --- | --- |
| Gasto total acima da renda | Sinais de alerta, Alimentação | fora do recomendado |
| Alimentação (peso) | Alimentação, Moradia | fora do recomendado (63,41% contra 10%–15%) |
| Moradia | Moradia, Alimentação | fora do recomendado (36,76% contra até 30%) |
| Alimentação (variação) | Alimentação, Sinais de alerta | fora do recomendado (crescimento > 30%) |
| Saúde | Sinais de alerta, Saúde | fora do recomendado (crescimento > 30%) |

**Etapa 4 — recomendações:**

1. Evitar gastos atípicos elevados em restaurantes e planejar eventos fora de casa com antecedência.
2. Revisar os custos fixos de moradia para adequá-los ao limite de 30% da renda.
3. Investigar os gastos com saúde para evitar oscilações acima de 30% de um mês para o outro.

## Execução final — março de 2024

Log: `prompts/outputs/diagnosticar_2024-03_20261002-193427.md`. Sem mês anterior no banco, a comparação vem
vazia. A etapa 2 apontou um único ponto — Moradia, 36,38% da renda — e a etapa 4 cita o saldo positivo de
R$ 1.747,70, número que veio pronto do levantamento.

## Como a cadeia evoluiu

A cadeia passou por três rodadas de execução; os logs de todas estão em `prompts/outputs/` e mostram o
processo de correção.

| Rodada | Logs | O que se observou | Correção |
| --- | --- | --- | --- |
| 1 | `diagnosticar_2024-04_20261002-184532.md`, `diagnosticar_2024-03_20261002-185407.md` | Abril: a etapa 4 escreveu "déficit de 1073.35" — **uma conta feita pelo LLM**, porque o saldo não existia no levantamento. Março: a etapa 2 inventou pontos de enchimento ("Estabilidade", "Verificação-se-á-em-próximos-meses") para completar "até cinco". Erro de digitação e recomendação truncada na saída do Gemma | `saldo` calculado em Python no `TotalMes`; a etapa 2 passou a incluir só pontos que atendem aos critérios |
| 2 | `diagnosticar_2024-04_20261002-190709.md`, `diagnosticar_2024-03_20261002-191052.md` | Nenhum número calculado pelo LLM; março ficou com um único ponto real. A revisão do log revelou um **bug no código**: dois pontos com o mesmo assunto ("Alimentação") compartilhavam a chave de um dicionário, e os trechos do primeiro eram sobrescritos | `recuperar_trechos` devolve uma lista na ordem dos pontos (com teste) |
| 3 | `diagnosticar_2024-04_20261002-193420.md`, `diagnosticar_2024-03_20261002-193427.md` | Cada ponto recebe seus próprios trechos; nenhum número fora do levantamento; todas as etapas no Gemini, após a troca de modelo | — |

## Limitações observadas

- O limite de cinco pontos faz a etapa 2 escolher: na rodada final de abril, a transação atípica (Outback) e
  o gasto `Não identificado` (R$ 33,00) não viraram pontos próprios — o Outback aparece de forma indireta
  na variação de Alimentação e na primeira recomendação.
- O RAG às vezes traz um trecho vizinho pouco relevante como segundo resultado (ex.: *Moradia* para o ponto
  de Alimentação); a etapa 3 ignorou esses trechos corretamente.
- A formatação dos números no resumo da etapa 4 varia (`5573.35` em vez de `R$ 5.573,35`); seria resolvida
  formatando no código em vez de pedir ao modelo.
