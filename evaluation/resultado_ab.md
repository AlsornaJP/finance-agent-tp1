# Avaliação A/B — sem tools × com tools

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

## Pergunta

A divisão de trabalho do TP2 — Python calcula, LLM classifica — produz números mais confiáveis que a
abordagem do TP1, em que o LLM recebia o CSV e fazia tudo?

## Variantes

| Variante | Descrição | Código |
| --- | --- | --- |
| **A — sem tools** | Prompt da Parte 5 do TP1: CSV bruto no prompt, o modelo devolve `AnaliseFinanceira` com transações, totais por categoria e total geral | `construir_variante_sem_tools` |
| **B — com tools** | Pipeline do TP2: Python importa o CSV para o SQLite, o classificador (CoT) atribui as categorias e os totais vêm de `gastos_por_categoria` | `classificar_pendentes` + `database` |

As duas variantes rodaram com o **mesmo modelo, `gemini-3.5-flash-lite`**, para que a diferença medida venha
da arquitetura e não do modelo.

## Critério

Gabarito: `evaluation/gabarito_categorias.csv` (categoria correta de cada descrição) aplicado às saídas do
CSV; totais esperados calculados em Python (`evaluation/metricas.py`).

| Métrica | Definição | Papel |
| --- | --- | --- |
| **Precisão numérica** | Fração das categorias (união das esperadas e das obtidas) cujo total obtido é igual ao esperado, tolerância R$ 0,01 | **Principal** — mede se os números entregues ao usuário estão certos |
| Erro absoluto do total | \|soma dos totais obtidos − total real do extrato\| | Magnitude do erro em reais |
| Acurácia de classificação | Fração das transações de saída do CSV presentes na saída com a categoria do gabarito (pareadas por descrição e valor) | Separa erro de classificação de erro aritmético |

Execução: `python -m evaluation.avaliar_ab --execucoes 3` — três execuções por variante em cada extrato
(12 no total). Resultados brutos em `evaluation/resultados/ab_20261002-192220.json`; saídas completas em
`evaluation/logs/`.

## Resultados

### Extrato de 1 mês (19 saídas, 9 categorias)

| Variante | Precisão numérica | Erro do total | Acurácia de classificação |
| --- | --- | --- | --- |
| A — sem tools | 1,00 / 1,00 / 1,00 | R$ 0,00 / 0,00 / 0,00 | 1,00 / 1,00 / 1,00 |
| B — com tools | 1,00 / 1,00 / 1,00 | R$ 0,00 / 0,00 / 0,00 | 1,00 / 1,00 / 1,00 |

### Extrato de 2 meses (30 saídas, 9 categorias)

| Variante | Precisão numérica | Erro do total | Acurácia de classificação |
| --- | --- | --- | --- |
| A — sem tools | 0,667 / 0,667 / 0,667 | R$ 228,10 / 228,10 / 51,90 | 1,00 / 1,00 / 1,00 |
| B — com tools | 1,00 / 1,00 / 1,00 | R$ 0,00 / 0,00 / 0,00 | 1,00 / 1,00 / 1,00 |

### Onde a variante A errou

| Execução | Categoria (nº de transações) | Obtido | Esperado |
| --- | --- | --- | --- |
| 1 e 2 | Alimentação (6) | 3204,15 | 3236,05 |
| 1 e 2 | Transporte (7) | 744,60 | 564,60 |
| 1 e 2 | Serviços/Assinaturas (4) | 203,60 | 123,60 |
| 3 | Alimentação (6) | 3204,15 | 3236,05 |
| 3 | Serviços/Assinaturas (4) | 203,60 | 123,60 |
| 3 | Moradia (4) | 3191,30 | 3291,30 |

## Análise

1. **A classificação não é o problema.** As duas variantes acertaram 100% das categorias em todas as
   execuções. Todo o erro da variante A é aritmético: o modelo sabia em que categoria cada transação estava
   e ainda assim somou errado.
2. **O erro aparece com o tamanho da soma.** No extrato de 1 mês (categorias com até 5 itens) a variante A
   acertou tudo; no de 2 meses ela errou sempre, e só em categorias com 4 ou mais transações. É o mesmo
   padrão que a análise do TP1 encontrou com outro modelo (Gemma), onde todo erro estava em categorias com
   5 ou mais transações — a regularidade se manteve trocando o modelo.
3. **O erro é sistemático, não aleatório.** As execuções 1 e 2 produziram exatamente os mesmos totais
   errados; repetir a chamada não corrige.
4. **Os erros se compensam e escondem o problema.** Na execução 3, o total geral ficou só R$ 51,90 acima do
   real porque erros em categorias diferentes se anularam parcialmente; três categorias continuavam erradas.
   Um teste que olhasse só o total geral subestimaria o problema — por isso a métrica principal é por
   categoria.
5. **A variante B não depende do tamanho da soma.** Os totais saem de `SUM` no SQLite; o único ponto em que
   o modelo poderia errar é a classificação, e ela foi perfeita.

## Decisão

**A variante B (com tools) fica.** Critério: precisão numérica, a métrica principal. B teve 1,00 em todas
as 6 execuções; A caiu para 0,667 em todas as 3 execuções do extrato de dois meses, com erro de até
R$ 228,10. As duas empataram em acurácia de classificação, então a diferença é exatamente a que a mudança
de arquitetura pretendia eliminar.

Custo da decisão: B faz uma chamada de classificação por importação mais as chamadas de tool em cada
pergunta, e exige um banco. Em troca, os totais deixam de depender do modelo e passam a ser testáveis com
`pytest`.

## Limitações

- Dois extratos sintéticos e pequenos; o efeito em extratos reais (centenas de linhas) tende a ser maior,
  mas não foi medido.
- O gabarito foi elaborado no próprio projeto, não por terceiros. Os dois casos ambíguos foram revisados
  pelo aluno: `CONTA DE LUZ ENEL` → Moradia, porque `Serviços/Assinaturas` reúne despesas opcionais e a
  conta de luz é um custo fixo da casa; `ACADEMIA SMARTFIT` → Saúde, apesar de também caber em Lazer. Como o
  classificador recebe essas regras no prompt, um gabarito diferente exigiria ajustar também as
  instructions.
- Três execuções por variante: suficiente para mostrar que o erro de A é sistemático, não para estimar sua
  distribuição.
- Medido com `gemini-3.5-flash-lite`. Uma primeira tentativa com o Gemma gratuito foi interrompida por
  lentidão (respostas de vários minutos) antes de concluir qualquer medição.
