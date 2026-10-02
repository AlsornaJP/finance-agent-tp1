# TP2 — Problemas encontrados e resolvidos

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

Problemas que surgiram durante a implementação do TP2, como foram detectados e como foram resolvidos. Os
itens 10 a 15 têm, cada um, um teste automatizado que falhava antes da correção e passa depois.

## Modelos e infraestrutura

| # | Problema | Como foi detectado | Solução |
| --- | --- | --- | --- |
| 1 | O Gemma **ignorava as tools** quando o agente tinha `output_type` (enviado como `response_format` JSON): calculava sozinho, sem erro. Forçar a chamada de tool junto com JSON é recusado pela API (erro 400) | Verificação inicial com um agente de teste (tool de soma + saída estruturada) | Agente com tools passou a usar Gemini 3.x, que combina tools e saída estruturada |
| 2 | `gemini-2.5-flash` descontinuado para novos usuários (404) | Mesma verificação | Uso dos modelos 3.x listados pela chave (`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`) |
| 3 | OpenRouter devolveu 429 (pool gratuito saturado) em todas as execuções | Logs de execução | Cadeia de fallback para o Google AI Studio |
| 4 | Gemma no Google lento e instável: erros 500/503, JSON inválido, até ~10 min por tentativa | Primeiras execuções do diagnóstico | Timeout de 180 s e 1 retentativa por chamada; Gemini como primeira opção de todos os agentes, Gemma como fallback |
| 5 | Criar o banco levava 2,3 s (um fsync por tabela) e a suíte de testes, 59 s | Medição dos tempos dos testes | Schema criado em uma única transação; suíte em ~6 s |
| 6 | mermaid-cli não abria o Chromium (sandbox bloqueado pelo AppArmor do Ubuntu) | Geração do diagrama | Renderização com `--no-sandbox`, apenas para o diagrama local |

## Comportamento do LLM

| # | Problema | Como foi detectado | Solução |
| --- | --- | --- | --- |
| 7 | O assistente somou duas categorias por conta própria ("totalizando R$ 3.183,55"), e a métrica original não percebeu, porque olhava só `valores_citados` | Pergunta de robustez no ciclo PRRR | Métrica nova sobre os números do texto; prompt v2 proíbe a conta e exige citar todo número (`evaluation/prrr.md`) |
| 8 | No diagnóstico, o LLM calculou o déficit do mês (renda − gasto) | Leitura do log da 1ª rodada | Campo `saldo` calculado em Python no levantamento |
| 9 | O diagnóstico inventava pontos de atenção para completar a lista de cinco | Leitura do log da 1ª rodada (março) | Prompt da etapa 2 restrito aos pontos que atendem aos critérios (`prompts/tp2_cadeia_diagnostico.md`) |

## Bugs de código

| # | Problema | Como foi detectado | Solução |
| --- | --- | --- | --- |
| 10 | Pontos de atenção com o mesmo assunto perdiam os trechos do guia (colisão de chave em dicionário) | Revisão dos logs do diagnóstico | Trechos em lista, na ordem dos pontos |
| 11 | Importação gravava linhas com data em formato errado ou descrição vazia | Revisão independente da branch | Validação de data (AAAA-MM-DD) e descrição, com erro citando a linha |
| 12 | Importação descartava em silêncio linhas válidas com tipo `saída`/`SAIDA` ou valor `nan`, contando-as como duplicadas | Revisão independente | Tipo normalizado (minúsculas, sem acento) e validado; valor precisa ser finito |
| 13 | Falha na segunda tentativa de classificação perdia o trabalho da primeira | Revisão independente | Classificações da primeira tentativa são preservadas |
| 14 | Divisão por zero em `transacoes_atipicas` quando a média da categoria é zero, derrubando o diagnóstico | Revisão independente | Categoria com média zero é ignorada |
| 15 | Falha ao gravar a memória perdia a resposta já obtida e não gerava log | Revisão independente | Falha registrada no log; a resposta é entregue mesmo assim |
| 16 | O script do A/B perderia todas as medições se uma execução falhasse no meio | Revisão do próprio script antes de rodar | Resultados gravados após cada medição; falhas registradas sem abortar |

## Pendente

| Problema | Impacto |
| --- | --- |
| Com mês em formato inválido, a tool devolve o erro de formato ("use AAAA-MM"), mas não a lista de meses disponíveis | Baixo: o modelo recebe a mensagem e consegue corrigir a chamada |
