# TP2 — Assistente com tools, memória e saída tipada

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

## Papel no sistema

O comando `python main.py perguntar --sessao <id> "<pergunta>"` executa um único agente que combina, no
mesmo `Agent`:

- **tools** (`@function_tool`, em `agent/tools.py`) que calculam tudo a partir do SQLite;
- **`output_type=RespostaFinanceira`**, validado pelo Pydantic e acessado em `result.final_output`;
- **memória de curto prazo** via `SQLiteSession(sessao, "data/financas.db")`;
- **memória de longo prazo** via RAG: a tool `buscar_conhecimento` consulta o guia de orçamento e as
  interações anteriores gravadas com embeddings.

## Regra central: o LLM nunca faz conta

O TP1 mostrou que o modelo errava somas quando acumulava muitas tarefas. No TP2 cada operação numérica é uma
tool pequena e determinística:

| Tool | Retorno |
| --- | --- |
| `gasto_total_mes(mes)` | total gasto, nº de transações, renda, % da renda gasto |
| `gastos_por_categoria(mes)` | por categoria: valor, quantidade, % do total, % da renda |
| `comparar_meses(mes_atual, mes_anterior)` | por categoria: valores, diferença em R$, variação % |
| `transacoes_atipicas(mes)` | transações > 10× a média das demais da categoria |
| `listar_transacoes(mes, categoria)` | transações individuais |
| `buscar_conhecimento(consulta)` | 4 trechos mais similares do guia e das memórias |

Mês inexistente ou em formato inválido não devolve zeros silenciosos: a tool responde ao modelo com os
meses disponíveis, ou com o erro de validação, e ele pode corrigir a chamada.

O schema de saída exige `valores_citados`: cada número da resposta acompanhado da tool de origem. Isso torna
a regra verificável — a métrica de rastreabilidade do ciclo PRRR (`evaluation/prrr.md`) confere cada valor
citado contra os retornos das tools daquela execução.

## Modelo

Os modelos Gemma, quando recebem `output_type` (enviado como `response_format` JSON), deixam de chamar
tools e calculam sozinhos — exatamente o que o projeto quer evitar. Os modelos Gemini 3.x combinam as duas
coisas. Por isso o assistente usa `GOOGLE_TOOL_MODELS` (`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`),
enquanto os agentes sem tools seguem na cadeia Gemma do TP1.

## Instructions (anatomia de 4 componentes)

Texto completo em `INSTRUCTIONS_ASSISTENTE` (`agent/prompts.py`); a evolução do texto pelo ciclo
Prompt-Response-Reflect-Revise está em `evaluation/prrr.md`.

| Componente | Conteúdo |
| --- | --- |
| Instrução | Identificar mês e categoria, obter números só por tools, buscar conhecimento quando houver juízo de valor |
| Contexto | Descrição de cada tool, categorias fixas, uso das memórias, metas pessoais acima do guia |
| Exemplos | Pergunta → chamada de tool → saída com `valores_citados` |
| Formato de saída | `resposta`, `valores_citados`, `fontes_conhecimento` |

## Como o resultado da tool vira a resposta final

Log: `prompts/outputs/perguntar_joao_20261002-181042.md` (modelo `gemini-3.5-flash-lite`).

Pergunta: *"Quanto gastei com Alimentação em abril de 2024 e isso está dentro do recomendado?"*

Chamadas de tool registradas:

```text
[1] gastos_por_categoria({"mes":"2024-04"})
-> [{"categoria":"Alimentação","valor_total":2853.25,"quantidade_transacoes":3,
     "percentual_do_total":51.19,"percentual_da_renda":63.41}, ...]

[2] buscar_conhecimento({"consulta":"limite recomendado para alimentação"})
-> [{"origem":"guia: Alimentação","texto":"O gasto total com alimentação costuma ficar entre 10% e 15%
     da renda. ...","similaridade":0.7459}, ...]
```

Saída validada (`RespostaFinanceira`):

```json
{
  "resposta": "Em abril de 2024 você gastou R$ 2.853,25 com Alimentação, o que representou 63,41% da sua renda e 51,19% do total dos seus gastos. O guia recomenda que o gasto total com alimentação fique entre 10% e 15% da renda, portanto o valor gasto está acima do recomendado.",
  "valores_citados": [
    {"descricao": "Gasto com Alimentação em abril de 2024", "valor": 2853.25, "ferramenta": "gastos_por_categoria"},
    {"descricao": "Percentual da renda gasto com Alimentação em abril de 2024", "valor": 63.41, "ferramenta": "gastos_por_categoria"},
    {"descricao": "Percentual do total gasto com Alimentação em abril de 2024", "valor": 51.19, "ferramenta": "gastos_por_categoria"}
  ],
  "fontes_conhecimento": ["guia: Alimentação"]
}
```

Os três números da resposta são cópias exatas de campos do retorno de `gastos_por_categoria`; o juízo
"acima do recomendado" vem da comparação entre 63,41% (tool) e a faixa de 10%–15% (trecho do guia
recuperado pelo RAG).

## Memória entre execuções

| Comando (cada um é um processo novo) | Itens na sessão antes | O que demonstra |
| --- | --- | --- |
| `--sessao joao` "Quanto gastei com Alimentação em abril de 2024…?" | 0 | tools + RAG do guia |
| `--sessao joao` "E em março?" | 6 | `SQLiteSession`: entendeu "Alimentação" pelo histórico; respondeu R$ 382,80 |
| `--sessao joao-1` "Minha meta é gastar no máximo R$ 100 por mês com Lazer." | 0 | a interação é gravada como memória com embedding |
| `--sessao joao-2` "Estou dentro da minha meta de lazer em abril de 2024?" | 0 | sessão nova: `buscar_conhecimento` recuperou a memória da `joao-1`; resposta "R$ 72,00, dentro da meta" |

Logs: `prompts/outputs/perguntar_joao_*.md`, `perguntar_joao-1_*.md`, `perguntar_joao-2_*.md`.
