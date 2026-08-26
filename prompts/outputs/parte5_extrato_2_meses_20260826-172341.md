# Execução — parte5

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

- Timestamp: 2026-08-26T17:23:41
- Modelo: gemma-4-31b-it
- Chave de API: GoogleAIStudio/chave-pessoal
- CSV de entrada: samples/extrato_2_meses.csv

## Instructions enviadas ao agente

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

## Input (CSV bruto)

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

## Output

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
