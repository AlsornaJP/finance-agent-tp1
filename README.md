# Projeto de Bloco — Agentes de IA (TP1–TP3)

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5
**Repositório:** <https://github.com/AlsornaJP/finance-agent-tp1>

Dois agentes independentes, cada um com seu próprio projeto Python, `CLAUDE.md` e API FastAPI. Eles não se
chamam: a orquestração entre os dois é feita pelo n8n, consumindo os endpoints HTTP de cada um.

| Pasta | Conteúdo |
|---|---|
| `agent1/` | Agente de finanças pessoais (TP1–TP2): importa extratos CSV, responde perguntas e gera diagnósticos mensais |
| `agent2/` | Planejador de metas: dada uma meta de poupança com prazo e os gastos de um mês, propõe cortes e projeta a meta |
| `evaluation/` | Avaliação final do pipeline de prompts |
| `integration/` | Contrato de API dos dois agentes e exemplos reais de requisição e resposta |
| `workflows/` | Workflow n8n exportado em JSON |
| `docs/` | Especificações, planos e documentos de arquitetura dos TPs |
| `entrega/` | Relatórios, roteiros e scripts de entrega |

## Como subir os serviços

```bash
cd agent1 && uv sync && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001
cd agent2 && uv sync && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8002
```

Cada agente lê o seu próprio `.env` (modelo em `.env.example` dentro da pasta do agente).
