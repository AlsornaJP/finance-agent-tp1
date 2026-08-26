# Agente de Análise de Finanças Pessoais (TP1)

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5


Agente single-turn construído com o **OpenAI Agents SDK**, acessando modelos via **OpenRouter**.
Recebe o conteúdo bruto de um CSV de extrato bancário e devolve uma análise de gastos.

## Estrutura

```
agent/
  config.py          Leitura do .env, cliente OpenRouter e configuração do SDK
  prompts.py         Instructions das Partes 3, 4 e 5 (anatomia de 4 componentes)
  schema.py          Schema Pydantic AnaliseFinanceira (output_type da Parte 5)
  finance_agent.py   Construção do Agent por etapa
  runner.py          Execução single-turn, fallback de modelo e rotação de chaves
  execution_log.py   Persistência dos logs de execução
prompts/
  parte{3,4,5}_instructions.md   Prompts documentados
  analise_resultados.md          Comparação entre as etapas e limitações observadas
  outputs/                       Logs de execução (evidência para o relatório)
samples/             CSVs de exemplo (1 mês e 2 meses)
spec/                Especificação do problema e arquitetura
main.py              CLI de execução
```

## Configuração

```bash
uv sync                      # ou: python -m venv .venv && pip install -r requirements.txt
cp .env.example .env         # preencha as chaves do OpenRouter
```

Variáveis de ambiente:

| Variável | Uso |
| --- | --- |
| `OPENAI_API_KEY` | Chave principal do OpenRouter |
| `OPENAI_SECOND_API_KEY`, `OPENAI_THIRD_API_KEY` | Chaves alternativas, usadas só mediante confirmação ao atingir rate limit |
| `OPENAI_BASE_URL` | `https://openrouter.ai/api/v1` |
| `OPENAI_DEFAULT_MODEL` | Modelo principal |
| `OPENAI_FALLBACK_MODEL` | Modelo de backup se o principal falhar |
| `OPENAI_AGENTS_DISABLE_TRACING` | `1` desativa o tracing nativo do SDK (incompatível com OpenRouter) |
| `GOOGLE_API_KEY` | Opcional. Chave pessoal do Google AI Studio, usada como provedor de fallback |
| `GOOGLE_BASE_URL` | Endpoint compatível com OpenAI do AI Studio (tem padrão embutido) |

### Cadeia de fallback

Cada execução tenta, em ordem, até obter resposta:

1. OpenRouter com `OPENAI_DEFAULT_MODEL`
2. OpenRouter com `OPENAI_FALLBACK_MODEL`
3. Google AI Studio com os mesmos modelos, na cota pessoal da chave (só se `GOOGLE_API_KEY` estiver definida)

Os modelos `:free` do OpenRouter compartilham um pool com o provedor original; quando ele satura,
todas as chaves do OpenRouter recebem 429 e trocar de chave não adianta — daí o fallback para a
cota pessoal do AI Studio. O nome do modelo é convertido automaticamente
(`google/gemma-4-31b-it:free` -> `gemma-4-31b-it`), então o `.env` continua com um único nome de modelo.

## Execução

```bash
python main.py parte3                          # output em texto livre
python main.py parte4                          # output com prompt refinado
python main.py parte5                          # output JSON estruturado (2 CSVs)
python main.py parte5 --csv caminho/extrato.csv
```

Cada execução grava um log em `prompts/outputs/` com instructions, input, output e erros.
A Parte 5 grava também o JSON de `result.final_output` validado pelo schema Pydantic.

## Decisões de design

- Sem `@function_tool`: o CSV vai como texto bruto no prompt e toda a análise é raciocínio do LLM.
- Operação single-turn: uma chamada, um CSV, uma resposta.
- A Parte 5 usa `output_type`, então `result.final_output` já é uma instância de `AnaliseFinanceira`.
- Ao atingir o rate limit diário, o agente avisa e pergunta antes de usar a próxima chave.

## Limitação conhecida

Na Parte 5, a saída estruturada degrada a precisão aritmética do modelo. O campo `transacoes`
melhora muito a extração sem torná-la confiável — em quatro execuções, a soma da lista bateu com o
CSV em duas, e nenhuma reproduziu o extrato fielmente (duplicações, descrições corrompidas, datas
alteradas). Já `total_gasto` e `resumo_por_categoria` divergem da própria lista em todas as
execuções, sempre em categorias com cinco ou mais transações.
`main.py` verifica as três consistências a cada execução e marca `[DIVERGE]` no que não fecha, em
vez de mascarar. Causa, evidências e mitigações em `prompts/analise_resultados.md`. A correção via
`@function_tool` é escopo do trabalho seguinte.
