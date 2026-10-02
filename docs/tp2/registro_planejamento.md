# Registro do planejamento do TP2 com assistente de IA

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5 · **Data:** 02/10/2026
**Ferramenta:** Claude Code (modelo Claude Opus 5.5), na branch `tp2` deste repositório

Este documento registra a sessão de planejamento do TP2 feita com um assistente de codificação, desde
a leitura do enunciado até a aprovação do plano de implementação. As mensagens do aluno estão
transcritas literalmente; as respostas do assistente estão resumidas, preservando as propostas,
justificativas e decisões. O registro foi redigido pelo próprio assistente ao final da sessão, a
pedido do aluno.

Artefatos produzidos nesta sessão:
- Especificação: `docs/superpowers/specs/2026-10-02-tp2-design.md`
- Plano de implementação: `docs/superpowers/plans/2026-10-02-tp2.md`

## 1. Retomada do contexto

> **Aluno:** o que fizemos neste projeto?

O assistente leu o histórico do git, a estrutura do repositório e os documentos do TP1 e resumiu o
que já existia: o agente single-turn com OpenAI Agents SDK via OpenRouter, as Partes 3, 4 e 5, a
cadeia de fallback de modelos e chaves, e o achado principal do TP1 — na Parte 5 (saída estruturada)
o modelo perdia transações e errava somas.

> **Aluno:** Temos mudanças a fazer para o tp2. Vamos implementá-las seguindo os mesmos princípios
> do tp1: simplicidade e codigo limpo e organizado. Vou mandar as questões.

O assistente confirmou que manteria as convenções do `CLAUDE.md` e avisou que duas restrições do
TP1 (sem tools, single-turn) provavelmente cairiam com o TP2, mas que isso seria discutido antes.

## 2. Leitura do enunciado e dos slides

O aluno colou o enunciado do TP2. O assistente classificou a tarefa como **arquitetural** (muda como
os componentes se encaixam) e, por isso, seguiu o fluxo completo: perguntas, design por seções, spec
escrito e plano.

O enunciado citava os "seis entregáveis dos slides 52 a 60". A página dos slides é renderizada em
JavaScript e não pôde ser lida diretamente; o assistente então buscou os fontes Markdown no
repositório público do curso no GitHub e identificou a seção "Etapa 1.5 — Entregáveis TP2".

> **Aluno:** como você sabe sobre o conteúdo dos slides? eu não os enviei

O assistente explicou o caminho (link no enunciado → repositório público → arquivo
`slide-etapa1-5.md`), reconheceu que deveria ter informado a origem logo de início e sugeriu que o
aluno conferisse com o material de aula.

> **Aluno:** Ah sim, agora entendi. antes de continuarmos, enumere os entregáveis pedidos pelos
> slides. Preciso saber se você os verificou corretamente.

O assistente listou: (1) gatilho n8n; (2) fontes de informação estruturada e não estruturada;
(3) diagrama de arquitetura com os 9 componentes; (4) descrição textual da arquitetura;
(5) exemplo do fluxo de dados com pergunta de dupla intenção; (6) modelo do dado estruturado; além
de (7) os demais itens do enunciado. Observou que n8n, API e multiagente são implementados nas
Etapas 3–5, de modo que no TP2 os itens 1, 3, 4 e 5 são documentação do desenho-alvo, enquanto 2 e 6
entram no código.

> **Aluno:** sim, bate. pode seguir com as perguntas.

## 3. Decisões de design

### 3.1 Fontes de informação

O assistente propôs três opções: (1) SQLite de transações + guia de orçamento em Markdown para RAG;
(2) CSV lido diretamente pela tool + guia; (3) SQLite + API externa de câmbio.

> **Aluno:** Me explique a vantagem da opção 1 sobre a 2. A 2 não deixa o trabalho mais simples?

O assistente concordou que a opção 2 é mais simples (economia de 30–40 linhas e o slide aceita
arquivos estruturados), mas apontou o motivo decisivo: o CSV não tem categoria. Com SQLite, a
classificação feita pelo LLM é gravada uma vez e reaproveitada pelas tools e pelas sessões
seguintes; com CSV direto, seria preciso reclassificar a cada execução ou criar um segundo arquivo
— um banco improvisado. Também citou a memória entre sessões, o custo zero (`sqlite3` é da
biblioteca padrão e o `SQLiteSession` já usa SQLite) e o encaixe com as Etapas 3 e 4.

> **Aluno:** Entendo, vamos seguir com a opção 1 então.

### 3.2 Embeddings

Opções: Google AI Studio (`gemini-embedding-001`), modelo local com fastembed, ou OpenRouter (pago).
**Decisão do aluno:** Google AI Studio — reaproveita a chave e o cliente já existentes, sem
dependência nova.

### 3.3 Forma de interação

> **Aluno:** Como o agente vai receber os extratos?

O assistente propôs separar ingestão de consulta: um comando `importar` lê o CSV de forma
determinística (sem LLM, eliminando a perda de linhas observada no TP1), grava no SQLite e então um
agente classifica as transações; depois disso o agente de perguntas trabalha só sobre o banco.
Explicou por que não colocar a importação como tool do agente: é uma etapa sempre igual, que não
precisa de decisão do LLM.

> **Aluno:** não entendi a pergunta

O assistente reformulou com exemplos de terminal: (A) um comando por pergunta, com `--sessao`, em
que cada pergunta é um processo novo — o que demonstra literalmente a memória entre execuções; ou
(B) um chat interativo.

> **Aluno:** pode ser a A

### 3.4 Código do TP1

**Decisão do aluno:** enxugar e reaproveitar — remover os comandos das Partes 3 e 4 do código
(a documentação e os logs do TP1 permanecem) e usar o prompt da Parte 5 como "variante A" da
avaliação, comparada com a versão com tools.

### 3.5 Raciocínio em etapas

Opções: diagnóstico mensal em cadeia, cadeia na classificação, ou CoT dentro do agente de perguntas.
**Decisão do aluno:** diagnóstico mensal com prompt chaining *least-to-most* (levantamento →
pontos de atenção → confronto com o guia → recomendações), mais chain-of-thought leve na
classificação (campo de justificativa antes da categoria).

### 3.6 Memória em "sessão nova"

O assistente apontou uma ambiguidade do enunciado: o `SQLiteSession` só lembra da mesma sessão; uma
sessão nova começa vazia. **Decisão do aluno:** usar o RAG também sobre as interações anteriores
(memória de longo prazo). Demonstração prevista: na sessão `joao-1` o usuário declara uma meta; na
sessão nova `joao-2` o agente a recupera por busca semântica.

### 3.7 Arquitetura e módulos

O assistente apresentou a organização em módulos (`database`, `rag`, `tools`, `agents`, `importacao`,
`consulta`, `diagnostico`, runner genérico) e os defaults assumidos (vetores em JSON no próprio
SQLite com cosseno em Python puro; Telegram como gatilho documentado).

> **Aluno:** Sim, faz sentido. Caso o Gemma dê problemas, pode incluir modelos gemini no env
> também. Acredito que tenham uma cota razoavél

### 3.8 Tools de cálculo

O assistente apresentou o modelo de dados e três tools. O aluno pediu maior granularidade:

> **Aluno:** Acho que precisamos de tools para calcular gastos mensais e gastos por categoria também.
> Durante o TP1 tive problemas onde o modelo começava a errar calculos devido a alta carga de tarefas
> para fazer, esmiuçar essas tarefas matemáticas ajuda na qualidade do resultado final.

O assistente adotou a regra "**o LLM nunca faz conta**" e dividiu os cálculos em tools pequenas e
determinísticas: `gasto_total_mes`, `gastos_por_categoria`, `comparar_meses`, `transacoes_atipicas`,
`listar_transacoes` e `buscar_conhecimento`. Percentuais e variações também passaram a sair prontos
das tools.

> **Aluno:** fechado, pode seguir

### 3.9 Agentes e fluxos

O assistente detalhou os três fluxos e seus schemas Pydantic (incluindo `valores_citados`, que torna
verificável de qual tool veio cada número da resposta).

> **Aluno:** Então será um sistema multiagentes?

O assistente esclareceu que não no sentido do Agents SDK (sem handoffs nem agentes como tools): são
agentes especializados orquestrados por código, num workflow de prompt chaining. O multiagente
aparece na arquitetura-alvo dos slides, documentada no TP2 e implementada nas próximas etapas.
Recomendou não antecipar handoffs agora (mais chamadas de LLM sob rate limit, e o enunciado não pede).

> **Aluno:** Sim, fica. Pode seguir

### 3.10 Avaliação e entregáveis

O assistente propôs: A/B (sem tools × com tools) medido por precisão numérica, erro do total e
acurácia de classificação contra um gabarito; ciclo Prompt-Response-Reflect-Revise sobre o prompt do
assistente, medido por rastreabilidade dos números e acerto; testes `pytest` da parte determinística.

> **Aluno:** esse gerar_video faz o que mesmo?

O assistente explicou que o script do TP1 só comprime uma gravação já feita (ffmpeg, 15 fps, áudio
mono).

> **Aluno:** Ah, não vamos precisar disso, vou subir o vídeo para o youtube e colar o link no readme

## 4. Especificação e plano

O assistente escreveu a especificação, revisou-a e a submeteu ao aluno.

> **Aluno:** pode criar a branch e commitar, segue pro plano

Ao preparar o plano, o assistente conferiu as APIs do SDK instalado e calculou à mão os números
esperados a partir dos CSVs, o que levou a três ajustes na especificação, informados ao aluno:

1. **Critério de anomalia:** "3× a mediana" marcaria o próprio supermercado como anômalo; adotou-se a
   regra do TP1 ("ordem de grandeza"): valor acima de 10× a média das demais transações da categoria,
   com ao menos duas para comparar. Nos dois CSVs, apenas o Outback é marcado.
2. **Deduplicação:** a chave única original descartaria duas compras idênticas legítimas no mesmo
   dia; acrescentou-se a coluna `ocorrencia`.
3. **PDF fora do escopo:** o enunciado pede o relatório em Markdown.

O plano final tem 15 tarefas com testes e commits próprios. Os números de referência dos testes
batem com o total real apurado no TP1 (R$ 8.325,65 no extrato de dois meses).

> **Aluno:** pode seguir nesta sessão. Além disso, crie um arquivo que registre nossa conversa até
> aqui. Acredito que vai ser bom pra mostrar ao professor.

## 5. Resumo das decisões

| Tema | Decisão | Quem decidiu |
| --- | --- | --- |
| Fonte estruturada | SQLite de transações alimentado pelos CSVs | Aluno, após comparação |
| Fonte não estruturada | Guia de orçamento em Markdown, via RAG | Aluno |
| Embeddings | Google AI Studio (`gemini-embedding-001`) | Aluno |
| Interface | Comandos CLI, uma pergunta por execução, com `--sessao` | Aluno |
| Cálculos | Toda aritmética em tools determinísticas, granulares | Aluno (pedido explícito) |
| Raciocínio | Diagnóstico least-to-most + CoT na classificação | Aluno |
| Memória | `SQLiteSession` + RAG sobre guia e interações | Aluno |
| Código do TP1 | Enxugado; Parte 5 vira variante A da avaliação | Aluno |
| Multiagente | Não no TP2; documentado como arquitetura-alvo | Aluno, após esclarecimento |
| Modelos | Gemma com fallback para Gemini se necessário | Aluno |
| Vídeo | YouTube, link no README | Aluno |
| Regra de anomalia, deduplicação, PDF | Ajustes técnicos propostos pelo assistente | Assistente, informado ao aluno |
| Execução do plano | Na mesma sessão, com revisão final da branch | Aluno |

## 6. Execução do plano (resumo)

O plano foi executado na mesma sessão, tarefa por tarefa, com testes escritos antes do código (TDD) e um
commit por etapa na branch `tp2`. Decisões tomadas durante a execução:

| Situação encontrada | Decisão |
| --- | --- |
| Na verificação inicial, o Gemma **ignorou as tools** quando o agente tinha `output_type`, calculando sozinho e sem erro | Agentes com tools passaram a usar modelos Gemini 3.x, que combinam tools e saída estruturada (autorizado pelo aluno no planejamento) |
| Criar o schema SQLite levava 2,3 s por banco (um fsync por tabela), e a suíte de testes, 59 s | Schema criado em uma única transação; suíte em ~6 s |
| O Gemma no Google respondia com erros 500/503 e JSON inválido, às vezes após ~10 minutos | Timeout de 180 s e 1 retentativa por chamada; Gemini como último recurso |
| No PRRR, a v1 somou duas categorias por conta própria, e a métrica original não percebeu | Nova métrica sobre os números do texto; prompt v2 proíbe a conta e exige citar todo número |
| No diagnóstico, o LLM calculou o déficit do mês e inventou pontos de atenção para completar a lista | Saldo calculado em Python; etapa 2 restrita aos critérios |
| Revisando os logs do diagnóstico, apareceu um bug: pontos com o mesmo assunto perdiam seus trechos do guia | Corrigido com teste (lista na ordem dos pontos) |

> **Aluno (durante a avaliação A/B):** falta muito?

O assistente informou o que estava pronto, o que faltava e a estimativa (cerca de 1 hora, quase toda de
espera do modelo Gemma), oferecendo reduzir as execuções.

> **Aluno:** interrompa A/B e troque o modelo por algum gemini, não da pra ficar uma hora esperando

O A/B foi interrompido e o Gemini passou a ser a primeira opção de todos os agentes (`GEMINI_MODELS`), com
o Gemma como fallback. A avaliação completa (12 execuções) terminou em cerca de 2 minutos.
