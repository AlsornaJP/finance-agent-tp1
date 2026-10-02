# TP2 — Agente de Finanças Pessoais: ferramentas, raciocínio encadeado, memória e avaliação

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5 · **Projeto de Bloco — Agentes Inteligentes**
**Repositório:** <https://github.com/AlsornaJP/finance-agent-tp1> (branch `tp2`)
**Vídeo:** `<link do YouTube — preencher>`

## 1. Introdução

No TP1 o agente recebia o CSV do extrato como texto no prompt e o modelo fazia tudo: ler as linhas,
classificar, somar, comparar meses e apontar anomalias. A análise de resultados do TP1 mostrou o limite
dessa abordagem: com saída estruturada, o modelo perdia, duplicava e corrompia transações, e errava somas
sistematicamente nas categorias com cinco ou mais itens (`prompts/analise_resultados.md`).

O TP2 reorganiza a divisão de trabalho em torno de uma regra: **o LLM nunca faz conta**. Leitura do CSV,
somas, percentuais, variações e o critério de anomalia passam a ser código Python determinístico, exposto ao
modelo como tools. O modelo fica com o que faz bem: interpretar descrições, decidir quais dados buscar,
relacionar números com regras e redigir.

Sobre essa base, o protótipo ganhou:

- **ferramentas** (`@function_tool`) sobre um banco SQLite de transações;
- **raciocínio encadeado**: chain-of-thought na classificação e uma cadeia *least-to-most* de quatro etapas
  no diagnóstico mensal;
- **memória** em duas camadas: `SQLiteSession` (curto prazo) e RAG com embeddings sobre um guia de
  orçamento e sobre as interações anteriores (longo prazo);
- **saídas tipadas** com Pydantic, inclusive combinando tools e `output_type` no mesmo agente;
- **avaliação** com métricas explícitas: comparação A/B e ciclo Prompt-Response-Reflect-Revise.

O planejamento foi feito com um assistente de IA e está registrado em `docs/tp2/registro_planejamento.md`.

## 2. Arquitetura do protótipo

Três comandos, cada um um fluxo orquestrado por código:

```
importar <csv>            CSV → SQLite (Python) → classificador com CoT grava as categorias
perguntar --sessao <id>   assistente com tools + SQLiteSession + RAG → RespostaFinanceira
diagnosticar --mes <m>    cadeia least-to-most de 4 etapas → DiagnosticoMensal
```

| Módulo | Responsabilidade |
| --- | --- |
| `agent/database.py` | Schema SQLite, importação do CSV, todas as funções de cálculo |
| `agent/tools.py` | `@function_tool` finas sobre `database.py` e `rag.py` |
| `agent/rag.py` | Trechos do guia, embeddings, busca por cosseno, memórias |
| `agent/schema.py` | Modelos Pydantic |
| `agent/prompts.py` / `agent/agents.py` | Instructions (anatomia de 4 componentes) e construção dos agentes |
| `agent/runner.py` | Fallback de modelos e chaves, sessão, restauração em falhas |
| `agent/importacao.py`, `consulta.py`, `diagnostico.py` | Os três fluxos |
| `agent/rastreio.py`, `execution_log.py` | Extração das chamadas de tool e logs |

É um sistema de **agentes especializados orquestrados por código**, não multiagente no sentido do SDK (sem
handoffs). O multiagente aparece na arquitetura-alvo dos entregáveis (seção 8).

**Escolha de modelos.** A verificação inicial (registrada em `prompts/tp2_assistente.md`) mostrou que os
modelos Gemma, quando recebem `output_type` — enviado como `response_format` JSON —, **deixam de chamar
tools e calculam sozinhos**, sem erro; e o Google recusa forçar a chamada de tool junto com JSON. Os Gemini
3.x combinam as duas coisas. Por isso o assistente usa apenas `GEMINI_MODELS` (`gemini-3.5-flash-lite`,
`gemini-3.1-flash-lite`). Os demais agentes começaram na cadeia Gemma do TP1, mas o Gemma gratuito esteve
lento e instável (429 no OpenRouter, 500/503 e JSON inválido no Google, chamadas de até 10 minutos); por
isso o Gemini passou a ser a primeira opção de todos os agentes, com a cadeia Gemma como fallback.

## 3. Ferramentas

### Implementação

| Tool | Retorno |
| --- | --- |
| `gasto_total_mes(mes)` | total gasto, nº de transações, renda, saldo, % da renda gasto |
| `gastos_por_categoria(mes)` | por categoria: valor, quantidade, % do total, % da renda |
| `comparar_meses(mes_atual, mes_anterior)` | por categoria: valores, diferença em R$, variação % |
| `transacoes_atipicas(mes)` | transações acima de 10× a média das demais da categoria |
| `listar_transacoes(mes, categoria)` | transações individuais |
| `buscar_conhecimento(consulta)` | 4 trechos mais similares do guia e das memórias |

Cada tool tem *type annotations* e docstring (que o SDK transforma no schema e na descrição enviados ao
modelo). O contexto (`RunContextWrapper[ContextoFinanceiro]`, com o caminho do banco) não aparece no schema.
Os cálculos ficam em funções puras de `database.py`, cobertas por testes com valores calculados à mão a
partir do CSV — por exemplo, abril de 2024: total R$ 5.573,35, 123,85% da renda; Alimentação R$ 2.853,25.

Casos de borda tratados: mês sem dados devolve ao modelo a lista de meses disponíveis (não zeros
silenciosos); mês ou categoria inválidos geram erro de validação que o SDK repassa ao modelo, que pode
corrigir a chamada.

### Integração do resultado na resposta

Log `prompts/outputs/perguntar_joao_20261002-181042.md`, pergunta *"Quanto gastei com Alimentação em abril
de 2024 e isso está dentro do recomendado?"*:

```text
[1] gastos_por_categoria({"mes":"2024-04"})
-> [{"categoria":"Alimentação","valor_total":2853.25,"quantidade_transacoes":3,
     "percentual_do_total":51.19,"percentual_da_renda":63.41}, ...]
[2] buscar_conhecimento({"consulta":"limite recomendado para alimentação"})
-> [{"origem":"guia: Alimentação","texto":"O gasto total com alimentação costuma ficar entre 10% e 15%
     da renda. ...","similaridade":0.7459}, ...]
```

Resposta validada: *"Em abril de 2024 você gastou R$ 2.853,25 com Alimentação, o que representou 63,41% da
sua renda e 51,19% do total dos seus gastos. O guia recomenda que o gasto total com alimentação fique entre
10% e 15% da renda, portanto o valor gasto está acima do recomendado."* — com `valores_citados` apontando
`gastos_por_categoria` como origem dos três números e `fontes_conhecimento = ["guia: Alimentação"]`. Os
números são cópias dos campos retornados; o juízo de valor vem da comparação entre o percentual da tool e a
faixa do guia. Detalhes em `prompts/tp2_assistente.md`.

## 4. Raciocínio encadeado

### Chain-of-thought na classificação

No `importar`, o schema `ClassificacaoTransacao` declara `justificativa` antes de `categoria`: o modelo
interpreta a descrição antes de escolher o rótulo. A categoria é um `Literal` das nove categorias fixas.
Resultado real: 30 de 30 transações do extrato de dois meses classificadas igual ao gabarito, incluindo
`PAG*7X4K9ZQ` → `Não identificado` com a justificativa "código de pagamento sem nome de estabelecimento
identificável". Documentação em `prompts/tp2_classificador_cot.md`.

### Prompt chaining least-to-most no diagnóstico

O diagnóstico mensal não cabe bem num prompt único — é justamente o tipo de tarefa que degradou no TP1.
Ele é decomposto do subproblema mais simples ao mais complexo, cada etapa usando as respostas anteriores:

| Etapa | Pergunta respondida | Executor | Saída |
| --- | --- | --- | --- |
| 1 | Quais são os números do mês? | Python (sem LLM) | `LevantamentoMensal` |
| 2 | O que nesses números merece atenção? | LLM | `PontosDeAtencao` |
| 3 | Isso está dentro do recomendado? | RAG + LLM | `AvaliacaoGuia` |
| 4 | O que fazer? | LLM | `DiagnosticoMensal` |

A sequência de prompts, os outputs intermediários de cada etapa e a análise das execuções estão em
`prompts/tp2_cadeia_diagnostico.md`.

## 5. Memória

| Comando (cada um é um processo novo) | Histórico da sessão | Resultado |
| --- | --- | --- |
| `--sessao joao` "Quanto gastei com Alimentação em abril de 2024 …?" | 0 itens | R$ 2.853,25 + trecho do guia |
| `--sessao joao` "E em março?" | 6 itens | Entendeu "Alimentação" pelo histórico do `SQLiteSession`: R$ 382,80 |
| `--sessao joao-1` "Minha meta é gastar no máximo R$ 100 por mês com Lazer." | 0 itens | Interação gravada como memória com embedding |
| `--sessao joao-2` "Estou dentro da minha meta de lazer em abril de 2024?" | 0 itens | `buscar_conhecimento` recuperou a memória da `joao-1`: R$ 72,00, dentro da meta |

A última linha é a demonstração pedida de uso de informação de interações anteriores **em uma sessão
nova**: o `SQLiteSession` da `joao-2` estava vazio, e a meta veio do RAG sobre a tabela `memorias`. O RAG
usa `gemini-embedding-001` pelo endpoint compatível com OpenAI do Google AI Studio; os vetores ficam como
JSON no próprio SQLite e a busca é por similaridade de cosseno em Python — suficiente para algumas dezenas
de trechos, sem dependência nova.

## 6. Saídas tipadas e validadas

Todos os agentes usam `output_type` com modelos Pydantic (`agent/schema.py`), acessados por
`result.final_output`:

- `ClassificacaoLote` — `categoria` como `Literal`, rejeitando rótulos inventados;
- `RespostaFinanceira` — `resposta`, `valores_citados` (número + tool de origem), `fontes_conhecimento`;
- `PontosDeAtencao`, `AvaliacaoGuia` (com `situacao` como `Literal`), `DiagnosticoMensal` (com `prioridade`
  ≥ 1) — as saídas de cada etapa do diagnóstico.

O agente `perguntar` **combina tools e `output_type`**: as seis tools e `RespostaFinanceira` no mesmo
`Agent`. O campo `valores_citados` torna verificável a regra "o LLM não calcula" — é o que a métrica de
rastreabilidade do PRRR mede.

## 7. Avaliação

### 7.1 Comparação A/B: sem tools × com tools

Variante A: prompt da Parte 5 do TP1 (CSV no prompt, sem tools). Variante B: pipeline do TP2
(classificador + totais via tools). Mesmo modelo nas duas (`gemini-3.5-flash-lite`), três execuções por
variante em cada extrato. Métrica principal: **precisão numérica** — fração das categorias com total igual
ao gabarito (tolerância R$ 0,01); métricas auxiliares: erro absoluto do total e acurácia de classificação.

| Extrato | Variante | Precisão numérica | Erro do total | Acurácia de classificação |
| --- | --- | --- | --- | --- |
| 1 mês | A — sem tools | 1,00 nas 3 | R$ 0,00 nas 3 | 1,00 nas 3 |
| 1 mês | B — com tools | 1,00 nas 3 | R$ 0,00 nas 3 | 1,00 nas 3 |
| 2 meses | A — sem tools | 0,667 nas 3 | R$ 228,10 / 228,10 / 51,90 | 1,00 nas 3 |
| 2 meses | B — com tools | 1,00 nas 3 | R$ 0,00 nas 3 | 1,00 nas 3 |

As duas variantes classificaram 100% das transações corretamente; **todo o erro da variante A é
aritmético**, e aparece só no extrato maior, sempre em categorias com 4 ou mais transações (Alimentação,
Transporte, Serviços/Assinaturas, Moradia) — o mesmo padrão que o TP1 encontrou com o Gemma. O erro é
sistemático (execuções 1 e 2 deram os mesmos totais errados) e às vezes se compensa no total geral (R$ 51,90
na execução 3, com três categorias erradas), o que justifica medir por categoria.

**Decisão:** a variante B fica — precisão 1,00 em todas as execuções contra 0,667 da A no extrato de dois
meses, com acurácia de classificação empatada. Análise completa em `evaluation/resultado_ab.md`.

### 7.2 Ciclo Prompt-Response-Reflect-Revise

Prompt avaliado: instructions do assistente. Métricas: acerto (valor esperado presente em
`valores_citados`), rastreabilidade (valores citados que coincidem com retornos das tools) e
rastreabilidade no texto (o mesmo, sobre os números do texto da resposta).

| Versão | Perguntas | Acertos | Rastreabilidade | No texto |
| --- | --- | --- | --- | --- |
| v1 | 5 | 5/5 | 1,0 | — |
| v1 | 7 (com robustez) | 6/7 | 0,952 | 0,952 |
| v2 | 7 | 7/7 | 1,0 | 1,0 |

- **Prompt/Response:** a v1 acertou as cinco perguntas iniciais. Foram acrescentadas duas de robustez, uma
  delas pedindo a soma de duas categorias, que nenhuma tool fornece.
- **Reflect:** a v1 somou por conta própria ("totalizando R$ 3.183,55"). Na primeira execução o total nem
  foi citado em `valores_citados`, e a métrica original não percebeu — o que levou a uma segunda métrica,
  sobre os números do texto.
- **Revise:** a v2 acrescenta duas instruções: não fazer contas que nenhuma tool fornece (apresentar os
  valores e dizer que o total não é calculado) e citar em `valores_citados` todo número do texto.
- **Decisão:** a v2 virou o prompt do assistente — ganhou o caso que motivou o TP2 sem regredir nos demais.

Detalhes, diffs e limitações em `evaluation/prrr.md`.

## 8. Entregáveis de arquitetura

`docs/tp2/entregaveis.md` responde aos seis entregáveis da Etapa 1.5:

1. **Gatilho:** Telegram.
2. **Fontes:** SQLite de transações (estruturada) e guia de orçamento (não estruturada).
3. **Diagrama** com os 9 componentes: `docs/tp2/arquitetura.png`.
4. **Descrição textual** de cada componente, com o estado de implementação no TP2.
5. **Fluxo de dados** da pergunta de dupla intenção, com os números reais do banco.
6. **Modelo de dados** das tabelas `transacoes`, `memorias`, `trechos_guia` e `metadados`.

## 9. Decisões técnicas e justificativas

| Decisão | Justificativa |
| --- | --- |
| SQLite em vez de ler o CSV direto na tool | A categoria não existe no CSV; o banco guarda a classificação uma vez e a reaproveita em todas as consultas e sessões |
| Leitura do CSV em Python | Elimina a perda, duplicação e corrupção de linhas observadas no TP1 |
| Tools granulares para cada cálculo | Pedido do aluno a partir da lição do TP1: menos carga por chamada, cada número com origem verificável |
| Deduplicação com coluna `ocorrencia` | Reimportar não duplica, e duas compras idênticas legítimas no mesmo dia são preservadas |
| Anomalia = 10× a média das demais da categoria | Mantém o critério "ordem de grandeza" do TP1; o critério com mediana marcava o próprio supermercado |
| Embeddings do Google AI Studio, vetores no SQLite | Reaproveita chave e cliente existentes; volume pequeno dispensa vector store |
| RAG também sobre interações | `SQLiteSession` não atravessa sessões; a memória de longo prazo cobre o "sessão nova" do enunciado |
| Gemini como primeira opção | Gemma ignora tools quando há `output_type` e esteve lento e instável no plano gratuito |
| Timeout de 180 s e 1 retentativa por chamada | Gemma sob alta demanda travava até ~10 min antes do fallback |
| Sem handoffs no TP2 | O enunciado não pede; o roteamento multiagente fica para n8n (Etapa 5) |

Todos os problemas encontrados durante a implementação — de modelos, de comportamento do LLM e bugs de
código —, como foram detectados e como foram resolvidos estão listados em `docs/tp2/problemas_resolvidos.md`.

## 10. Limitações e próximos passos

- Os modelos gratuitos estiveram instáveis durante o trabalho: o OpenRouter devolveu 429 em todas as
  execuções, e o Gemma no Google teve erros 500/503 e JSON inválido. Por isso o Gemini virou a primeira
  opção; execuções anteriores a essa troca (importação e primeiros diagnósticos) usaram Gemma, e o modelo
  de cada etapa está registrado nos logs.
- A avaliação usa dois extratos sintéticos e um gabarito feito pelo próprio autor; o ciclo PRRR teve uma
  execução por versão.
- Perguntas que exigem contas sem tool correspondente agora são recusadas parcialmente (v2); a evolução
  natural é criar tools para esses casos.
- Próximas etapas: FastAPI (`/run`, `/status`), servidor MCP com as tools de cálculo e o fluxo n8n com
  Telegram, roteador e Merge.

## 11. Links

- Repositório: <https://github.com/AlsornaJP/finance-agent-tp1>
- Vídeo: `<link do YouTube — preencher>`
- Problemas encontrados e resolvidos: `docs/tp2/problemas_resolvidos.md`
- Especificação e plano do TP2: `docs/superpowers/specs/2026-10-02-tp2-design.md`,
  `docs/superpowers/plans/2026-10-02-tp2.md`
