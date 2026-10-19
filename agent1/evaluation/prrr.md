# Ciclo Prompt-Response-Reflect-Revise — prompt do assistente

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

## Objeto e critério

- **Prompt avaliado:** instructions do agente `perguntar` (`INSTRUCTIONS_ASSISTENTE`), o prompt principal do TP2.
- **Dados:** `samples/extrato_2_meses.csv` com as categorias do gabarito, num banco temporário novo por
  pergunta (sem memórias de uma pergunta vazando para outra).
- **Modelo:** `gemini-3.5-flash-lite` em todas as execuções.
- **Script:** `python -m evaluation.avaliar_prrr <versão>`; resultados em `evaluation/prrr/resultado_*.json`
  e logs completos (com chamadas de tool) em `evaluation/prrr/logs/<versão>/`.

Métricas por pergunta:

| Métrica | Definição |
| --- | --- |
| Acerto | O valor esperado (calculado do gabarito) aparece em `valores_citados`, tolerância R$ 0,01. Para pergunta sem valor esperado, acerto = nenhum número fora das tools no texto |
| Rastreabilidade | Fração de `valores_citados` que coincide com algum número retornado pelas tools naquela execução |
| Rastreabilidade no texto | A mesma fração, mas sobre os números extraídos do texto da resposta (formato pt-BR, anos ignorados) |

As duas rastreabilidades medem diretamente a regra central do projeto: **o LLM não calcula**.

## Ciclo 1 — v1

### Prompt

`evaluation/prrr/assistente_v1.md`: a versão escrita no plano, com anatomia de 4 componentes e a regra
"use apenas números retornados pelas ferramentas".

### Response (5 perguntas)

| # | Pergunta | Esperado | Tool chamada | Acerto | Rastreab. |
| --- | --- | --- | --- | --- | --- |
| 1 | Alimentação em abril de 2024 | 2853,25 | `gastos_por_categoria` | ✓ | 1,0 |
| 2 | Gasto total em março de 2024 | 2752,30 | `gasto_total_mes` | ✓ | 1,0 |
| 3 | Aumento de Transporte mar→abr | 96,00 | `comparar_meses` | ✓ | 1,0 |
| 4 | % da renda gasto em abril | 123,85 | `gasto_total_mes` | ✓ | 1,0 |
| 5 | Transação mais fora do padrão em abril | 2450,00 | `transacoes_atipicas` | ✓ | 1,0 |

Resultado: **5/5, rastreabilidade 1,0** (`resultado_v1_5perguntas.json`).

### Reflect

Com 100% de acerto, o conjunto não discriminava nada: toda pergunta tinha uma tool que devolvia exatamente o
número pedido. Faltava testar justamente o caso que o TP1 mostrou ser perigoso — quando a resposta exige uma
conta. Foram acrescentadas duas perguntas de robustez:

- 6: *"Quanto gastei com Lazer em abril?"* (sem ano) — esperado 72,00;
- 7: *"Quanto gastei com Alimentação e Transporte somados em abril de 2024?"* — nenhuma tool devolve essa
  soma.

### Response (7 perguntas, métrica original)

A pergunta 6 acertou. A pergunta 7 respondeu:

> "Em abril de 2024, você gastou R$ 2.853,25 com Alimentação e R$ 330,30 com Transporte, **totalizando
> R$ 3.183,55**."

O modelo fez a soma por conta própria. A conta até está certa, mas viola a regra do projeto — e, nessa
execução, o total não foi listado em `valores_citados`, de modo que a **rastreabilidade deu 1,0 e não
detectou a violação** (`resultado_v1_7perguntas_metrica_antiga.json`).

### Reflect

Duas causas distintas:

1. **Falha da métrica:** a rastreabilidade só olhava os valores que o próprio modelo declarou; um número
   escrito no texto e omitido de `valores_citados` passava despercebido. Correção: métrica
   *rastreabilidade no texto* (`numeros_no_texto` em `evaluation/metricas.py`, com teste) e pergunta 7 com
   critério "nenhum número fora das tools".
2. **Falha do prompt:** a v1 proíbe calcular, mas não diz o que fazer quando a pergunta *pede* um número que
   nenhuma tool fornece. Diante disso, o modelo preferiu ser útil e somou. E nada obrigava que todo número
   do texto aparecesse em `valores_citados`.

### Response (v1 reexecutada com a métrica nova)

| # | Acerto | Rastreab. | Rastreab. no texto |
| --- | --- | --- | --- |
| 1–6 | ✓ | 1,0 | 1,0 |
| 7 | ✗ | 0,667 | 0,667 |

Resultado: **6/7, rastreabilidade média 0,952** (`resultado_v1.json`). Desta vez o modelo citou o total
(3183,55) em `valores_citados`, e as duas métricas acusaram o número sem origem.

### Revise → v2

Duas inserções, sem mexer no resto do prompt (`diff assistente_v1.md assistente_v2.md`):

```diff
 2. Obtenha todos os números chamando as ferramentas de cálculo. Nunca some, subtraia, divida ou calcule
    percentuais por conta própria: use apenas números retornados pelas ferramentas.
+   Se a pergunta pedir um número que nenhuma ferramenta retorna (por exemplo, a soma de duas categorias),
+   não faça a conta: apresente os valores que as ferramentas retornaram e diga que o total combinado não é
+   calculado pelo assistente.
...
+Todo número que aparecer no texto de `resposta` deve estar também em `valores_citados`.
```

## Ciclo 2 — v2

### Response

| # | Pergunta | Acerto | Rastreab. | Rastreab. no texto |
| --- | --- | --- | --- | --- |
| 1 | Alimentação em abril de 2024 | ✓ | 1,0 | 1,0 |
| 2 | Gasto total em março de 2024 | ✓ | 1,0 | 1,0 |
| 3 | Aumento de Transporte mar→abr | ✓ | 1,0 | 1,0 |
| 4 | % da renda gasto em abril | ✓ | 1,0 | 1,0 |
| 5 | Transação mais fora do padrão | ✓ | 1,0 | 1,0 |
| 6 | Lazer em abril (sem ano) | ✓ | 1,0 | 1,0 |
| 7 | Alimentação + Transporte somados | ✓ | 1,0 | 1,0 |

Resposta da pergunta 7:

> "Em abril de 2024, você gastou R$ 2.853,25 com Alimentação e R$ 330,30 com Transporte. O total combinado
> não é calculado pelo assistente."

Resultado: **7/7, rastreabilidade 1,0 e rastreabilidade no texto 1,0** (`resultado_v2.json`).

### Reflect

Não restaram falhas com causa identificável no conjunto, e as perguntas 1–6 mantiveram o desempenho da v1
(a revisão não quebrou nada). O ciclo foi encerrado na v2.

## Decisão

**A v2 passa a ser `INSTRUCTIONS_ASSISTENTE`** em `agent/prompts.py` (texto idêntico a
`evaluation/prrr/assistente_v2.md`, verificado por `diff`).

Justificativa: ganhou 1 acerto (6/7 → 7/7) e levou a rastreabilidade de 0,952 a 1,0 sem regressão nas
demais perguntas. O ganho está exatamente no caso que motivou o TP2 — o modelo fazendo conta.

Trade-off assumido: na pergunta 7 a v2 é menos "útil" (não entrega o total). Para o projeto, um número
garantidamente correto vale mais que uma conta conveniente; se esse tipo de pergunta for frequente, a
solução coerente com a arquitetura é uma nova tool de soma, não liberar a aritmética no prompt.

## Limitações

- Uma execução por pergunta e por versão; a variação entre execuções do mesmo prompt não foi medida (a
  avaliação A/B, com três execuções, cobre a variância da classificação).
- Sete perguntas, todas sobre o mesmo extrato; o conjunto foi ampliado depois de ver a v1 acertar tudo,
  o que é proposital (procurar falhas), mas significa que a v2 foi ajustada a falhas conhecidas.
- `numeros_no_texto` assume formato brasileiro; um número escrito em formato inglês (2853.25) seria lido
  errado.
