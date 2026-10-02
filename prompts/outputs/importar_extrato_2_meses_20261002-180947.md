# Execução — importar

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

- Timestamp: 2026-10-02T18:09:47
- CSV: samples/extrato_2_meses.csv
- Banco: data/financas.db
- Transações inseridas: 0
- Transações já existentes: 32
- Classificadas pelo LLM: 0

## Instructions do classificador

```text
# INSTRUÇÃO

Você classifica transações de saída de um extrato bancário em categorias de gasto.
Para cada transação recebida, primeiro escreva uma justificativa curta interpretando a descrição
(que tipo de estabelecimento ou serviço ela indica) e só depois escolha a categoria.

# CONTEXTO

Entrada: lista JSON de transações com `id`, `descricao` e `valor` (em reais).

Categorias fixas (use exatamente estes rótulos):
- Alimentação
- Transporte
- Moradia
- Saúde
- Educação
- Lazer
- Compras
- Serviços/Assinaturas
- Não identificado

Regras de classificação:
- Classifique todas as transações recebidas, uma única vez cada, preservando o `id` original.
- Supermercados, padarias, restaurantes e aplicativos de entrega de comida são `Alimentação`.
- Contas de consumo da residência (luz, água, gás, condomínio) e aluguel são `Moradia`.
- Farmácias, consultas, exames e academias são `Saúde`.
- Cursos, livros e plataformas de ensino são `Educação`.
- Streaming e assinaturas digitais são `Serviços/Assinaturas`.
- Combustível, aplicativos de corrida e transporte público são `Transporte`.
- Quando a descrição não permitir identificar o estabelecimento, use `Não identificado` em vez de adivinhar.

# EXEMPLOS

{"id": 41, "descricao": "RAPPI *MERCADO", "valor": 87.5}
-> justificativa "Rappi é aplicativo de entrega; a descrição indica compra de mercado", categoria `Alimentação`

{"id": 42, "descricao": "PAG*K2M8QX", "valor": 19.9}
-> justificativa "código de pagamento sem nome de estabelecimento identificável", categoria `Não identificado`

{"id": 43, "descricao": "CONTA DE AGUA SABESP", "valor": 96.3}
-> justificativa "conta de consumo de água da residência", categoria `Moradia`

# FORMATO DE SAÍDA

Objeto JSON com o campo `classificacoes`: uma lista com um objeto por transação recebida, cada um com
`id`, `justificativa` e `categoria`, nesta ordem de campos.
```

## Transações não retornadas pelo classificador

```text
[]
```
