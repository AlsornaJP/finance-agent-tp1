# TP2 — Classificador de transações com chain-of-thought

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

## Papel no sistema

O comando `python main.py importar <csv>` separa a ingestão em duas partes:

1. **Leitura determinística (Python, sem LLM):** `agent/database.py` lê o CSV com o módulo `csv`, normaliza
   os valores para positivos e grava cada linha na tabela `transacoes`. No TP1 o LLM recebia o CSV bruto e
   chegou a perder, duplicar e corromper linhas; aqui nenhuma linha depende do modelo para existir.
2. **Classificação (LLM):** só as saídas ainda sem categoria são enviadas ao agente classificador, em JSON
   com `id`, `descricao` e `valor`. A resposta é gravada na coluna `categoria` e reaproveitada por todas as
   tools e sessões seguintes, sem reclassificar.

## Técnica: chain-of-thought pela ordem dos campos

O schema `ClassificacaoTransacao` declara `justificativa` **antes** de `categoria`. Como o modelo gera o
JSON na ordem do schema, ele escreve primeiro a interpretação da descrição ("que tipo de estabelecimento é
este?") e só então escolhe o rótulo, condicionado ao próprio raciocínio. É o mesmo mecanismo que, no TP1,
o campo de enumeração usou para melhorar a extração: dar ao modelo espaço para pensar antes do campo que
importa.

A categoria é um `Literal` com as nove categorias fixas: qualquer rótulo inventado (como o `Habitação` da
Parte 3 do TP1) é rejeitado pela validação Pydantic.

Robustez no código (`agent/importacao.py`):
- ids que não estavam pendentes (inventados) são descartados;
- ids repetidos ficam só com a primeira classificação;
- ids omitidos são reenviados uma vez; se continuarem ausentes, recebem `Não identificado` com
  justificativa explicando o motivo.

## Instructions (anatomia de 4 componentes)

O texto completo está em `INSTRUCTIONS_CLASSIFICADOR` (`agent/prompts.py`) e no log de execução. Resumo:

| Componente | Conteúdo |
| --- | --- |
| Instrução | Classificar cada transação; justificar antes de escolher a categoria |
| Contexto | Formato da entrada, as 9 categorias fixas e regras de fronteira (contas da casa → Moradia, academia → Saúde, etc.) |
| Exemplos | Três casos fora dos dados de teste: `RAPPI *MERCADO`, `PAG*K2M8QX`, `CONTA DE AGUA SABESP` |
| Formato de saída | `classificacoes`: lista de `{id, justificativa, categoria}` nessa ordem |

Os exemplos usam descrições que **não** aparecem nos CSVs de teste, para que a avaliação não seja
inflada por cópia dos exemplos.

## Execução real

Log: `prompts/outputs/importar_extrato_2_meses_20261002-180939.md` — modelo `gemma-4-31b-it` (Google AI
Studio, após 429 no OpenRouter), 30 saídas classificadas numa única chamada.

Trecho do output:

```json
{"id": 2,  "justificativa": "Pagamento de aluguel de apartamento", "categoria": "Moradia"},
{"id": 4,  "justificativa": "Pedido de comida via iFood", "categoria": "Alimentação"},
{"id": 19, "justificativa": "Corrida de aplicativo de transporte", "categoria": "Transporte"},
{"id": 27, "justificativa": "Código de pagamento sem nome de estabelecimento identificável", "categoria": "Não identificado"},
{"id": 28, "justificativa": "Assinatura de streaming de áudio", "categoria": "Serviços/Assinaturas"}
```

Resultado contra o gabarito (`evaluation/gabarito_categorias.csv`): **30 de 30** categorias corretas,
nenhuma transação omitida. A segunda importação do mesmo CSV (`importar_extrato_2_meses_20261002-180947.md`)
inseriu 0 linhas e não chamou o LLM, pois não havia pendentes.
