# Avaliação final do pipeline de prompts (TP1 → TP3)

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

Este documento fecha o ciclo de refinamento de prompts iniciado no TP1. Ele consolida as variantes testadas,
as métricas aplicadas e as decisões tomadas, sem novas execuções: todos os números vêm das avaliações
registradas nos TPs anteriores e da validação do agente 2 neste TP, com o caminho de cada fonte.

## Fontes

| Etapa | Documento | Dados brutos |
|---|---|---|
| TP1 — Partes 3, 4 e 5 | `agent1/prompts/analise_resultados.md` | `agent1/prompts/outputs/parte*` |
| TP2 — A/B sem tools × com tools | `agent1/evaluation/resultado_ab.md` | `agent1/evaluation/resultados/ab_20261002-192220.json` |
| TP2 — PRRR do assistente | `agent1/evaluation/prrr.md` | `agent1/evaluation/prrr/resultado_*.json` |
| TP3 — planejador de metas | este documento | `agent2/prompts/outputs/planejar_2024-12_20261019-193301.md` |

## Métricas aplicadas

| Métrica | Onde | Definição |
|---|---|---|
| Aderência às categorias fixas | TP1 P3→P4 | rótulos produzidos ⊂ as 9 categorias do domínio |
| Consistência aritmética | TP1 P5 | soma das categorias = `total_gasto` = total real do CSV |
| Precisão numérica (principal do A/B) | TP2 A/B | fração das categorias com total correto, tolerância R$ 0,01 |
| Erro absoluto do total | TP2 A/B | \|soma obtida − total real\| |
| Acurácia de classificação | TP2 A/B | fração das transações com a categoria do gabarito |
| Acerto | TP2 PRRR | valor esperado presente em `valores_citados` |
| Rastreabilidade / no texto | TP2 PRRR | fração dos números (declarados / escritos no texto) que vieram de uma tool |
| Fechamento da simulação | TP3 agente 2 | sobra + soma dos cortes = economia planejada; acumulado no prazo ≥ meta |

## Variantes testadas

| # | Variante | Métrica | Resultado | Decisão |
|---|---|---|---|---|
| 1 | TP1 P3 — instructions livres | aderência às categorias | 5 rótulos fora do domínio (`Habitação`, `Outros/Diversos`…) | descartada |
| 2 | TP1 P4 — anatomia de 4 componentes, categorias no contexto | aderência / aritmética | 9/9 categorias; total R$ 5.310,90 = real | adotada como estrutura de todos os prompts |
| 3 | TP1 P5 — P4 + `output_type` | consistência aritmética | total 4.182,90 vs real 5.310,90 (1 mês); 7.613,35 vs 8.325,65 (2 meses) | mantida a saída tipada, problema registrado |
| 4 | TP1 P5 + campo de enumeração | consistência aritmética | soma bateu em 2/4 execuções; erro máximo caiu de −1.128,00 para +39,90; critério não satisfeito em 4/4 | mantida por dominar a variante 3; limitação atribuída à ausência de tools |
| 5 | TP2 A — sem tools (prompt P5) | precisão numérica | 1,00 (1 mês) e 0,667 em 3/3 execuções (2 meses), erro de até R$ 228,10 | descartada |
| 6 | TP2 B — com tools (classificador CoT + SQL) | precisão numérica | 1,00 em 6/6 execuções, erro R$ 0,00, classificação 1,00 | **adotada** |
| 7 | TP2 assistente v1 | acerto / rastreabilidade | 6/7; rastreabilidade média 0,952 | revisada (ver diagnóstico) |
| 8 | TP2 assistente v2 | acerto / rastreabilidade | 7/7; rastreabilidade e rastreabilidade no texto 1,0 | **adotada** |
| 9 | TP3 planejador v1 + recálculo em código | fechamento da simulação | caso real com saldo −1.073,35: cortes somam 1.223,35, economia 150,00 × 8 = 1.200,00, diferença 0,00 | **adotada**, com uma observação aberta |

## Configuração final adotada

| Componente | Configuração | Justificativa técnica |
|---|---|---|
| Estrutura de todo prompt | anatomia de 4 componentes (instrução, contexto, exemplos, formato de saída) | variante 2: o contexto com as categorias fixas eliminou a taxonomia inventada |
| Aritmética | sempre em Python, entregue por tools; o LLM nunca soma | variantes 3→6: o erro do LLM cresce com o número de parcelas e é sistemático (repete os mesmos totais errados); com SQL a precisão foi 1,00 em todas as execuções |
| Classificação | classificador com chain-of-thought, saída `ClassificacaoLote` | acurácia 1,00 nas duas variantes do A/B: classificar é a parte em que o LLM é confiável |
| Assistente (`perguntar`) | v2 do PRRR, com `valores_citados` obrigatório para todo número do texto | variante 8: 7/7 e rastreabilidade 1,0 sem regressão nas demais perguntas |
| Diagnóstico | levantamento em Python seguido de cadeia least-to-most em 3 etapas de LLM, com RAG (`agent1/prompts/tp2_cadeia_diagnostico.md`) | cada etapa recebe só o que precisa e entrega um schema próprio; números vêm do levantamento em Python |
| Planejador (agente 2) | v1 com 2 tools e, depois do agente, recálculo determinístico do plano | o LLM escolhe onde cortar; todo número do `PlanoDeMeta` vem de `simular_plano`, então um erro do modelo vira `error`, nunca um número errado |
| Modelo | `gemini-3.5-flash-lite` para agentes com tools; Gemma só como fallback de agentes sem tools | os Gemma ignoram tools quando há `output_type` (TP2, `docs/tp2/problemas_resolvidos.md`) |

Critério explícito de decisão, aplicado em todas as etapas: **entre duas variantes, vence a que entrega
números garantidamente corretos e rastreáveis**, mesmo que seja menos "útil" (variante 8 não soma
categorias) ou mais cara (variante 6 exige banco e mais chamadas).

## Diagnóstico de prompt ineficaz — assistente v1

**Sintoma.** Para *"Quanto gastei com Alimentação e Transporte somados em abril de 2024?"*, a v1 respondeu
"…R$ 2.853,25 com Alimentação e R$ 330,30 com Transporte, **totalizando R$ 3.183,55**". Nenhuma tool
devolve essa soma: o modelo a calculou sozinho.

**Categoria do problema: instrução incompleta (lacuna de especificação).** A v1 proibia calcular ("use
apenas números retornados pelas ferramentas"), mas não dizia o que fazer quando a pergunta *pede* um número
que nenhuma tool fornece. Diante do conflito entre a proibição e o pedido do usuário, o modelo preencheu a
lacuna com o comportamento padrão de ser útil — e fez a conta. Havia ainda uma segunda lacuna, de formato
de saída: nada exigia que todo número do texto aparecesse em `valores_citados`, então a violação podia
passar sem ser declarada.

**Como foi detectado.** A primeira métrica (rastreabilidade sobre `valores_citados`) deu 1,0 nessa
execução, porque o total não foi declarado. Foi preciso criar a *rastreabilidade no texto*
(`numeros_no_texto` em `agent1/evaluation/metricas.py`), que lê os números do próprio texto. Lição: a
métrica também é parte do pipeline e precisa ser avaliada.

**Correção aplicada (v2).** Duas inserções, sem mexer no resto do prompt:

```diff
+   Se a pergunta pedir um número que nenhuma ferramenta retorna (por exemplo, a soma de duas categorias),
+   não faça a conta: apresente os valores que as ferramentas retornaram e diga que o total combinado não é
+   calculado pelo assistente.
+Todo número que aparecer no texto de `resposta` deve estar também em `valores_citados`.
```

**Efeito medido.** 6/7 → 7/7; rastreabilidade média 0,952 → 1,0; perguntas 1–6 sem regressão.

## Observação aberta — formato dos números no resumo do planejador

Na validação real do agente 2, o resumo escreveu os números como `150.0` e `-1073.35`, em formato de
código, e não como `R$ 150,00`. Os números estão certos e rastreáveis (são os retornos das tools), mas a
apresentação não segue o padrão em reais do projeto. Categoria: **formato de saída subespecificado** — o
componente de formato do `planejador_v1.md` pede para citar números "como aparecem nos retornos das tools",
o que o modelo seguiu literalmente. A revisão natural (v2) é pedir valores em reais com duas casas e
vírgula decimal; ela não foi aplicada neste TP para não gastar uma nova rodada de execuções reais sem um
conjunto de casos para comparar as versões.

## Limitações

- Extratos sintéticos e pequenos (19 e 30 saídas); o efeito em extratos reais não foi medido.
- PRRR com uma execução por pergunta; a variância entre execuções foi medida só no A/B (3 por variante).
- O planejador foi validado em um único caso real; não há ainda um conjunto de avaliação com métricas por
  caso, como existe para o agente 1.
- O gabarito de categorias foi elaborado no próprio projeto e revisado pelo aluno.
