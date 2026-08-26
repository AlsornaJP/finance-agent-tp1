# Análise dos resultados — Partes 3, 4 e 5

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5


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
