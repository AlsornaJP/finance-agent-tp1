# Roteiro do vídeo — TP2 (até 5 minutos)

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

Preparação antes de gravar: terminal na raiz do projeto, `.env` configurado, banco limpo
(`rm -f data/financas.db`) e um editor aberto com `agent/tools.py` e um log de `prompts/outputs/`.

## 0:00–0:40 — Problema e evolução

- O TP1 recebia o CSV no prompt e o modelo fazia tudo; na saída estruturada ele perdia transações e errava
  somas em categorias com cinco ou mais itens.
- O TP2 muda a divisão de trabalho: Python lê o CSV e faz toda a aritmética; o LLM classifica, interpreta e
  redige. Três comandos: `importar`, `perguntar`, `diagnosticar`.

## 0:40–1:30 — Importação com chain-of-thought

```bash
python main.py importar samples/extrato_2_meses.csv
```

- Mostrar no log `prompts/outputs/importar_*.md` o campo `justificativa` antes de `categoria` (CoT pela ordem
  do schema) e o `PAG*7X4K9ZQ` caindo em `Não identificado`.
- Rodar de novo: "0 transações novas" — deduplicação, sem chamada ao LLM.

## 1:30–2:20 — Tools + output_type no mesmo agente

```bash
python main.py perguntar --sessao joao "Quanto gastei com Alimentação em abril de 2024 e isso está dentro do recomendado?"
```

- Abrir `agent/tools.py`: tools finas que chamam funções determinísticas.
- No log: chamadas `gastos_por_categoria` e `buscar_conhecimento` com argumentos e retorno; a saída
  `RespostaFinanceira` com `valores_citados` apontando a tool de cada número.
- Comentar: o Gemma ignora tools quando recebe `output_type`; por isso o assistente usa Gemini 3.x.

## 2:20–3:10 — Memória em duas camadas

```bash
python main.py perguntar --sessao joao "E em março?"
python main.py perguntar --sessao joao-1 "Minha meta é gastar no máximo R$ 100 por mês com Lazer."
python main.py perguntar --sessao joao-2 "Estou dentro da minha meta de lazer em abril de 2024?"
```

- "E em março?" só faz sentido pelo histórico do `SQLiteSession` (processo novo, mesma sessão).
- Na `joao-2` (sessão nova, histórico vazio) a meta vem do RAG sobre as interações anteriores.

## 3:10–4:00 — Raciocínio em etapas

```bash
python main.py diagnosticar --mes 2024-04
```

- Mostrar o log com as quatro etapas least-to-most: levantamento (Python) → pontos de atenção → confronto
  com o guia (RAG) → recomendações.

## 4:00–4:40 — Avaliação

- `evaluation/resultado_ab.md`: variante A (TP1, sem tools) × variante B (TP2, com tools) — precisão
  numérica, erro do total e acurácia de classificação.
- `evaluation/prrr.md`: ciclo Prompt-Response-Reflect-Revise do prompt do assistente, com a métrica de
  rastreabilidade.

## 4:40–5:00 — Arquitetura-alvo

- Mostrar `docs/tp2/arquitetura.png`: Telegram → n8n → API → agentes Consultor e Analista → Merge.
- O que vem nas próximas etapas: FastAPI, MCP e n8n.
