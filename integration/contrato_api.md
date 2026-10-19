# Contrato de API dos agentes

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

Dois serviços independentes. Nenhum chama o outro: quem encadeia é o n8n, só por HTTP.

| Agente | Responsabilidade | URL local | URL a partir do n8n (Docker) |
|---|---|---|---|
| Agente 1 — Finanças Pessoais | importa extratos, responde perguntas, gera diagnóstico mensal | `http://localhost:8001` | `http://host.docker.internal:8001` |
| Agente 2 — Planejador de Metas | planeja uma meta de poupança com prazo a partir dos gastos de um mês | `http://localhost:8002` | `http://host.docker.internal:8002` |

No Linux, o container do n8n precisa de `--add-host=host.docker.internal:host-gateway` (ou usar `http://172.17.0.1:<porta>`). Os serviços escutam em `0.0.0.0`.

## Padrão comum

| Método | Rota | Sucesso | Erros |
|---|---|---|---|
| `POST` | `/run` | **202** `{"task_id": "<uuid>", "status": "pending"}` | **422** corpo inválido (nenhuma tarefa é criada) |
| `GET` | `/status/{task_id}` | **200** `{"task_id", "status", "resultado", "erro"}` | **404** `{"detail": "Tarefa não encontrada"}` |
| `GET` | `/health` | **200** `{"status": "ok", "agente": "<nome>"}` | — |

Estados da tarefa:

| `status` | Significado | `resultado` | `erro` |
|---|---|---|---|
| `pending` | aceita, na fila ou executando | `null` | `null` |
| `done` | concluída | objeto da ação (abaixo) | `null` |
| `error` | o fluxo levantou exceção | `null` | `"<TipoDoErro>: <mensagem>"` |

- A execução roda em `BackgroundTasks` do FastAPI: o `POST /run` responde antes de o LLM começar.
- Cada serviço executa uma tarefa por vez; as demais esperam como `pending`.
- As tarefas ficam em memória: reiniciar o serviço apaga os `task_id` (o `GET /status` passa a dar 404).
- Quem chama faz polling em `GET /status/{task_id}` até sair de `pending`.

## Agente 1 — Finanças Pessoais (`:8001`)

`POST /run` recebe um objeto com `acao` e os campos da ação.

### `importar`

| Campo | Tipo | Regra |
|---|---|---|
| `acao` | `"importar"` | obrigatório |
| `csv` | string | conteúdo do arquivo CSV (colunas `data`, `descrição`, `valor`, `tipo` opcional), não vazio |

`resultado`: `{"log": str, "meses_disponiveis": [str]}`. CSV com linha inválida termina em `error` com a mensagem da validação.

### `perguntar`

| Campo | Tipo | Regra |
|---|---|---|
| `acao` | `"perguntar"` | obrigatório |
| `pergunta` | string | não vazia |
| `sessao_id` | string | opcional, padrão `"api"`; mesma sessão mantém o histórico da conversa |

`resultado`: `{"resposta": RespostaFinanceira, "log": str}`, com `RespostaFinanceira = {resposta: str, valores_citados: [{descricao, valor, ferramenta}], fontes_conhecimento: [str]}`.

### `diagnosticar`

| Campo | Tipo | Regra |
|---|---|---|
| `acao` | `"diagnosticar"` | obrigatório |
| `mes` | string | `AAAA-MM`; mês sem transações termina em `error` sem chamar o LLM |

`resultado`:

| Campo | Conteúdo |
|---|---|
| `diagnostico` | `DiagnosticoMensal = {mes, resumo, avaliacoes, recomendacoes}` |
| `total_mes` | `{mes, total_gasto, quantidade_transacoes, renda, saldo, percentual_renda_gasto}` |
| `gastos_por_categoria` | `[{categoria, valor_total, quantidade_transacoes, percentual_do_total, percentual_da_renda}]` |
| `log` | caminho do log da execução |

`total_mes` e `gastos_por_categoria` são calculados em Python, sem LLM, e têm exatamente o formato que o agente 2 aceita.

### Exemplos reais

```bash
curl -s -X POST http://localhost:8001/run -H 'Content-Type: application/json' \
  -d '{"acao": "perguntar", "pergunta": "Quanto gastei com Alimentação em 2024-04?", "sessao_id": "tp3-demo"}'
# 202 {"task_id":"c23eb29b-6e8e-4dae-84c5-07f56f4322bf","status":"pending"}

curl -s http://localhost:8001/status/c23eb29b-6e8e-4dae-84c5-07f56f4322bf
```

```json
{
  "task_id": "c23eb29b-6e8e-4dae-84c5-07f56f4322bf",
  "status": "done",
  "resultado": {
    "resposta": {
      "resposta": "Em abril de 2024 você gastou R$ 2853,25 com Alimentação, em 3 transações.",
      "valores_citados": [
        {"descricao": "Gasto com Alimentação em 2024-04", "valor": 2853.25, "ferramenta": "gastos_por_categoria"},
        {"descricao": "Quantidade de transações de Alimentação em 2024-04", "valor": 3.0, "ferramenta": "gastos_por_categoria"}
      ],
      "fontes_conhecimento": []
    },
    "log": "prompts/outputs/perguntar_tp3-demo_20261019-192714.md"
  },
  "erro": null
}
```

Mês sem dados (`{"acao": "diagnosticar", "mes": "2023-01"}`):

```json
{"task_id": "35a77651-…", "status": "error", "resultado": null,
 "erro": "ValueError: Não há transações para 2023-01. Meses disponíveis: 2024-03, 2024-04."}
```

Todos os arquivos estão em `integration/exemplos/`; `integration/exemplos/curl_agent1.sh` dispara as três ações.

## Agente 2 — Planejador de Metas (`:8002`)

`POST /run` recebe um `PedidoPlano`:

| Campo | Tipo | Regra |
|---|---|---|
| `meta.valor` | número | > 0 |
| `meta.prazo` | string | `AAAA-MM`, posterior a `mes_referencia` |
| `mes_referencia` | string | `AAAA-MM` |
| `total_mes.renda` | número | ≥ 0 |
| `total_mes.total_gasto` | número | ≥ 0 |
| `total_mes.saldo` | número | pode ser negativo |
| `gastos_por_categoria[]` | lista | ao menos um item, sem categoria repetida |
| `gastos_por_categoria[].categoria` | string | uma das 9 categorias fixas |
| `gastos_por_categoria[].valor_total` | número | ≥ 0 |

Campos extras em `total_mes` e nos itens de `gastos_por_categoria` são ignorados, para aceitar a saída do `diagnosticar` do agente 1 sem transformação.

`resultado`: `{"plano": PlanoDeMeta, "log": str}`:

| Campo | Conteúdo |
|---|---|
| `meta`, `mes_referencia` | ecoam o pedido |
| `meses_disponiveis` | do mês seguinte a `mes_referencia` até o prazo, inclusive |
| `economia_mensal_necessaria` | `meta.valor / meses_disponiveis`, arredondado para cima ao centavo |
| `sobra_atual` | `total_mes.saldo` |
| `valor_a_cobrir_com_cortes` | `max(0, necessária − sobra)` |
| `viavel` | a projeção atinge a meta no prazo |
| `cortes[]` | `{categoria, gasto_atual, corte_mensal, justificativa}` |
| `economia_mensal_planejada` | sobra + soma dos cortes |
| `projecao[]` | `{mes, acumulado}` mês a mês |
| `diferenca_para_meta` | acumulado no prazo − meta (negativo = falta) |
| `resumo` | texto do LLM |
| `valores_citados[]` | `{descricao, valor, ferramenta}` |

Uma proposta do LLM com corte maior que o gasto da categoria termina em `error` com a mensagem da validação.

### Exemplo real

Pedido em `integration/exemplos/agent2_run_request.json` (números reais de 2024-04 vindos do agente 1, meta de R$ 1.200 até 2024-12). Trecho do resultado:

```json
{
  "status": "done",
  "resultado": {
    "plano": {
      "meses_disponiveis": 8,
      "economia_mensal_necessaria": 150.0,
      "sobra_atual": -1073.35,
      "valor_a_cobrir_com_cortes": 1223.35,
      "viavel": true,
      "cortes": [
        {"categoria": "Lazer", "gasto_atual": 72.0, "corte_mensal": 72.0, "justificativa": "…"},
        {"categoria": "Compras", "gasto_atual": 129.9, "corte_mensal": 129.9, "justificativa": "…"},
        {"categoria": "Serviços/Assinaturas", "gasto_atual": 61.8, "corte_mensal": 61.8, "justificativa": "…"},
        {"categoria": "Alimentação", "gasto_atual": 2853.25, "corte_mensal": 959.65, "justificativa": "…"}
      ],
      "economia_mensal_planejada": 150.0,
      "diferenca_para_meta": 0.0
    },
    "log": "prompts/outputs/planejar_2024-12_20261019-193301.md"
  }
}
```

Resposta completa em `integration/exemplos/agent2_status_done.json`.

## Orquestração no TP4

O n8n encadeia os dois serviços sem que um conheça o outro:

1. `POST :8001/run {"acao": "importar", "csv": …}` → polling em `GET :8001/status/{id}` até `done`.
2. `POST :8001/run {"acao": "diagnosticar", "mes": …}` → polling até `done`.
3. Um nó do n8n monta o pedido do agente 2: `meta` (vinda do gatilho, ex. formulário ou mensagem), `mes_referencia = mes`, e `total_mes` e `gastos_por_categoria` copiados do resultado do passo 2.
4. `POST :8002/run` com esse pedido → polling até `done`.
5. O n8n entrega diagnóstico e plano juntos ao usuário; qualquer `error` desvia para um ramo de falha.

Toda a coordenação (ordem, repasse de dados, tratamento de erro) fica no workflow, que é determinístico. Os agentes só conhecem os próprios contratos.
