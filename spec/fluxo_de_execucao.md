# Como o agente funciona, passo a passo

**Aluno:** João Pedro Jacob · **Disciplina:** 26E3_5

Esta seção descreve, em linguagem direta, o que acontece entre digitar o comando e obter a análise
do extrato. A intenção é que alguém sem familiaridade com o SDK consiga acompanhar.

## A ideia geral

O agente não é um programa que sabe analisar extratos. Ele é um programa que **monta um pedido bem
escrito, envia esse pedido a um modelo de linguagem e confere a resposta que volta**. A análise em
si é feita pelo modelo; o código cuida de tudo o que está em volta.

Três perguntas organizam o desenho:

1. O que o modelo precisa saber antes de ver os dados? → as **instruções**
2. Quais dados ele vai receber desta vez? → o **texto do extrato**
3. Em que formato a resposta precisa voltar? → o **molde da resposta**

Essas três coisas viajam juntas, num único pedido.

## Passo 1 — O comando

```
python main.py parte5
```

O primeiro argumento diz qual etapa rodar. Cada etapa usa um conjunto diferente de instruções, e a
Parte 5 é a única que exige a resposta em formato de dados. Sem indicar arquivos, o programa usa os
dois extratos de exemplo: um cobrindo um mês, outro cobrindo dois.

## Passo 2 — Ler as configurações

O programa lê o arquivo `.env`, onde ficam as chaves de acesso, o endereço do serviço e o nome do
modelo. Nada disso está escrito dentro do código, o que permite trocar de modelo sem alterar
nenhuma linha.

Se faltar alguma informação obrigatória, o programa para aqui e avisa — antes de gastar qualquer
acesso ao serviço.

## Passo 3 — Ler o extrato como texto puro

O arquivo CSV é lido **como texto, sem nenhum tratamento**. O programa não separa colunas, não
converte datas, não soma valores. Ele apenas pega o conteúdo do arquivo do jeito que está.

É como copiar o arquivo inteiro e colar dentro de uma mensagem. O que o modelo recebe é exatamente
isto:

```
data,descrição,valor,tipo
2024-03-01,SALARIO EMPRESA XYZ,4500.00,entrada
2024-03-02,ALUGUEL APTO 302,-1450.00,saida
```

Essa escolha é uma exigência do trabalho, não uma conveniência. O objetivo é medir o quanto o
modelo consegue fazer sozinho, sem ajuda de código.

## Passo 4 — Montar o pedido

O pedido tem duas partes, com papéis diferentes:

| Parte | O que carrega | Muda a cada execução? |
| --- | --- | --- |
| Instruções | Quem o modelo é, o que fazer, as categorias válidas, exemplos | Não |
| Dados | O texto do extrato | Sim |

A separação é útil porque as instruções são o "enunciado da tarefa", válido sempre, e os dados são
"a questão desta vez". Trocar de extrato não exige reescrever nada.

## Passo 5 — Mandar junto o molde da resposta

Na Parte 5, além das instruções e dos dados, o pedido leva uma **descrição de como a resposta deve
ser organizada**: quais campos devem existir, que tipo de informação vai em cada um, e em que
ordem.

É a diferença entre pedir "me manda um resumo" e pedir "me manda um resumo preenchendo estes
campos". O segundo pedido é bem mais fácil de conferir depois.

### Por que a ordem dos campos importa

O modelo escreve a resposta **da esquerda para a direita, um pedaço de cada vez, sem voltar atrás**.
O que ele já escreveu fica à vista; o que ainda não escreveu não existe.

Isso tem uma consequência prática. No molde, a lista de transações vem antes do valor total. Então,
quando chega a hora de escrever o total, as transações já estão escritas logo acima — e ele pode
somar o que está vendo, em vez de estimar de cabeça.

Se o total viesse primeiro, ele teria de acertar o número antes de ter listado qualquer transação.

Vale ser preciso quanto ao alcance disso: **o molde é um pedido, não uma trava**. Nada impede o
modelo de responder fora de ordem, ou de inventar um campo. Existe um modo mais rígido, em que o
serviço realmente impede a resposta de fugir do formato, mas o modelo gratuito usado aqui não o
suporta — por isso ele foi desligado. Na prática, o modelo respeitou a ordem em todas as execuções,
mas isso é um comportamento observado, não uma garantia.

## Passo 6 — Enviar, com plano B

O pedido é enviado. Se falhar, o programa tenta de novo, sempre na mesma ordem:

1. Serviço principal, modelo principal
2. Serviço principal, modelo reserva
3. Serviço alternativo, modelo principal
4. Serviço alternativo, modelo reserva

Para na primeira tentativa que der certo. Essa cadeia existe por um motivo concreto: os modelos
gratuitos são compartilhados entre todos os usuários do serviço, e quando essa capacidade comum se
esgota, todas as chaves recebem a mesma recusa. Trocar de chave não adianta — por isso o programa
distingue os dois tipos de recusa e só sugere trocar de chave quando isso resolveria de fato.

## Passo 7 — Conferir a resposta

A resposta chega como texto. Duas conferências acontecem em seguida:

**A primeira é automática.** O texto é comparado com o molde. Se faltar um campo, ou se um número
vier escrito como palavra, o programa acusa erro em vez de seguir adiante com dado estragado.

**A segunda é nossa.** O programa recalcula três coisas e compara com o que o modelo afirmou:

- a soma das transações listadas bate com o total informado?
- a soma das categorias bate com o total informado?
- a quantidade de transações nas categorias bate com a quantidade listada?

O resultado sai marcado como `[ok]` ou `[DIVERGE]`. O programa **não corrige nada** — apenas mede e
mostra. Corrigir por fora esconderia a falha sem resolvê-la.

## Passo 8 — Guardar as evidências

Cada execução grava dois arquivos com data e hora no nome: um com o pedido completo e a resposta,
outro só com os dados da resposta. Nada é sobrescrito, então dá para comparar execuções diferentes
— foi assim que a limitação descrita adiante foi identificada.

## Por que o modelo erra as somas

Vale fechar com a explicação da limitação, agora que o fluxo está claro.

Somar dezenove valores exige guardar um resultado parcial e ir atualizando. O modelo não tem onde
guardar isso: ele só tem o texto que já escreveu. Quando escreve o total sem ter listado as parcelas
antes, precisa estimar — e erra.

Foi isso que a lista de transações veio resolver, e resolveu em parte: com as parcelas escritas
logo acima, o erro caiu bastante. Mas o modelo continua somando "de olho" em vez de calcular, e por
isso ainda erra nas categorias com mais transações.

Uma única linha de código somaria a lista corretamente. Ela não foi escrita de propósito: o trabalho
proíbe dar essa ajuda ao modelo, justamente porque o objetivo é medir do que ele é capaz sozinho.
