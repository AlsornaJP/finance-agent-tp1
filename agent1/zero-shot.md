# Prompt Zero-Shot para criação de um agente de IA com o OpenAI Agents SDK

## Papel

Você é um engenheiro de software Python especializado em desenvolvimento de agentes de IA com o OpenAI Agents SDK. Seu trabalho é implementar, de forma limpa, a versão completa de um agente, priorizando clareza de código e organização em etapas bem separadas — já que o resultado será documentado passo a passo em um relatório técnico.

## Tarefa

Implemente as Partes 3, 4 e 5 de um TP acadêmico: a versão completa de um agente de análise de finanças pessoais, usando o OpenAI Agents SDK. Especificamente:

**Parte 3 — Agente funcional:**

1. Configure um ambiente virtual Python (venv) e um `requirements.txt` com as dependências necessárias (`openai-agents`, `openai`, `pydantic`, e demais que forem necessárias)
2. Configure a autenticação via **OpenRouter** (não a API da OpenAI diretamente), lendo as seguintes variáveis de ambiente do `.env`:
   - `OPENAI_API_KEY`, `OPENAI_SECOND_API_KEY`, `OPENAI_THIRD_API_KEY` — chaves em ordem de prioridade
   - `OPENAI_BASE_URL` — endpoint do OpenRouter
   - `OPENAI_DEFAULT_MODEL` — modelo principal
   - `OPENAI_FALLBACK_MODEL` — modelo de backup
   - `OPENAI_AGENTS_DISABLE_TRACING` — deve ser respeitada (tracing nativo do SDK é incompatível com OpenRouter)

   Crie um cliente `OpenAI` apontando para `OPENAI_BASE_URL`, usando `OPENAI_API_KEY`, e defina-o como cliente padrão do Agents SDK via `set_default_openai_client`
3. Crie um `Agent` com instructions claras, usando o modelo lido de `OPENAI_DEFAULT_MODEL` (não hardcode o nome do modelo no código — leia do ambiente, para que trocar de modelo não exija alterar o script)
4. Implemente um `Runner` que execute o agente de forma single-turn, recebendo como input o conteúdo bruto de um CSV de extrato bancário (passado como texto, sem parsing estruturado prévio)
5. Registre (log) a execução: input enviado, output recebido, e eventuais erros

**Parte 4 — Estruturação do prompt (anatomia de 4 componentes):**

6. Reescreva as instructions do agente seguindo explicitamente a anatomia de 4 componentes: **instrução** (o que fazer), **contexto** (informações de domínio necessárias — categorias fixas, regras de negócio), **exemplos** (few-shot: pelo menos 1-2 exemplos de transação → categoria/análise esperada) e **formato de saída** (como a resposta deve ser estruturada)
7. Deixe essas 4 seções claramente identificáveis no código (ex: como blocos de string separados e comentados, ou constantes nomeadas), para que possam ser citadas individualmente na documentação do TP
8. Rode o agente com esse prompt refinado e registre o output, para comparação com a versão da Parte 3

**Parte 5 — Saída estruturada (output_type):**

9. Defina um schema Pydantic (`BaseModel`) com os campos: `periodo_analisado`, `total_gasto`, `resumo_por_categoria` (lista de objetos com `categoria`, `valor_total`, `quantidade_transacoes`), `gastos_anomalos` (lista de objetos com `transacao`, `motivo_anomalia`), `comparacao_mes_anterior` (lista de objetos com `categoria`, `valor_atual`, `valor_anterior`, `variacao`)
10. Configure o `Agent` para usar esse schema via `output_type`
11. Acesse e valide o resultado através de `result.final_output`, garantindo que ele é uma instância do schema Pydantic (não uma string a ser parseada manualmente)
12. Rode o agente com pelo menos 2 exemplos de CSV diferentes (um cobrindo 1 mês, outro cobrindo 2+ meses) e registre os outputs JSON resultantes, para servir de evidência/documentação

## Contexto

Este agente faz parte de um TP acadêmico sobre desenvolvimento de agentes de IA com o OpenAI Agents SDK. O domínio do agente é **finanças pessoais**:

- **Entrada:** um CSV de extrato bancário (colunas esperadas: `data`, `descrição`, `valor`, opcionalmente `tipo`), podendo conter transações de múltiplos meses
- **Categorias fixas** que o agente deve usar para classificar transações: `Alimentação`, `Transporte`, `Moradia`, `Saúde`, `Educação`, `Lazer`, `Compras`, `Serviços/Assinaturas`, `Não identificado`
- **O que o agente deve fazer:**
  - Classificar cada transação em uma das categorias fixas
  - Calcular o total gasto por categoria
  - Identificar transações anômalas (valores muito acima do padrão da categoria)
  - Quando houver dados de mais de um mês, comparar os gastos por categoria entre os dois meses mais recentes
- **Restrição de design:** não use tools (`@function_tool`) — o CSV é passado como texto bruto direto no prompt, e toda a análise é feita via raciocínio do LLM
- **Restrição de execução:** operação single-turn (uma chamada, um CSV, uma resposta). Economize requisições o máximo que puder (o limite são 50 por chave). Caso o limite de requisições diárias seja batido, avise e pergunte se devemos seguir com a próxima chave (`OPENAI_SECOND_API_KEY`, depois `OPENAI_THIRD_API_KEY`).
- **Modelo:** lido de `OPENAI_DEFAULT_MODEL`, acessado via OpenRouter (camada gratuita, sujeita a limite de requisições diárias). Em caso de falha, usar `OPENAI_FALLBACK_MODEL`.

## Saída e verificação

**Entregáveis esperados:**
- Estrutura de projeto organizada em pastas (`agent/` código Python do agente com Agent, Runner e configuração do SDK, `prompts/` com prompts documentados com as quatro seções da anatomia e outputs registrados, `spec/` onde posteriormente incluirei os documentos de especificação do problema e arquitetura inicial em Markdown)
- Script(s) executável(is) que rodam de ponta a ponta sem erros, dado um `.env` válido conforme as variáveis descritas acima
- Logs de execução separados por etapa (Parte 3: output em texto livre; Parte 4: output com prompt refinado; Parte 5: output JSON estruturado), salvos em arquivos, para uso como evidência no PDF do trabalho
- As 4 seções da anatomia do prompt (instrução, contexto, exemplos, formato de saída) devem estar claramente identificáveis e comentadas no código-fonte

**Critérios de verificação:**
- O ambiente virtual e as dependências instalam sem conflitos
- A execução não gera erros de autenticação ou de configuração do cliente OpenRouter
- Na Parte 5, `result.final_output` retorna uma instância válida do schema Pydantic, sem necessidade de parsing manual de string JSON
- A soma dos valores em `resumo_por_categoria` corresponde ao `total_gasto` reportado
- Pelo menos uma transação é sinalizada em `gastos_anomalos` nos testes (mesmo que forçada no CSV de exemplo), com uma justificativa coerente
- Se o CSV de teste cobrir 2+ meses, `comparacao_mes_anterior` é preenchido corretamente; se cobrir só 1 mês, o campo deve indicar ausência de dados históricos de forma explícita (não deve quebrar nem inventar dados)
- Caso algo falhe (ex: modelo indisponível, rate limit do OpenRouter atingido, erro de validação do schema), reporte o erro claramente em vez de mascará-lo