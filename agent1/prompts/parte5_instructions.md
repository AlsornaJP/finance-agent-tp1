# Parte 5 — Instructions com saída estruturada

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5


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
