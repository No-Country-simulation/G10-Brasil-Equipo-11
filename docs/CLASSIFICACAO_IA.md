# Classificação e roteamento da IA

## 1. Objetivo

O módulo de IA do CommunityLab analisa interações de uma comunidade de
alunos de tecnologia, organiza essas interações por tipo, sentimento,
tópico e relevância e encaminha cada uma para uma rota de processamento.

As rotas orientam a geração de rascunhos de conteúdo, sugestões de FAQ
e alertas. Os materiais gerados devem passar por revisão humana antes
de qualquer publicação ou utilização externa.

## 2. Componentes envolvidos

- `app/ia.py`: classificação, decisão de rota e geração dos conteúdos.
- `app/prompts.py`: instruções utilizadas pelo modelo de linguagem.
- `app/llm.py`: seleção entre modo simulado e integração com Gemini.
- `app/schemas.py`: contratos dos dados de entrada e saída.
- `app/grafo.py`: orquestração das etapas com LangGraph.
- `app/storage.py`: persistência do pacote de resultados.

## 3. Dados de entrada

Cada interação contém os campos:

| Campo | Descrição |
|---|---|
| `autor` | Identificação textual do autor da interação. |
| `canal` | Canal de origem da mensagem. |
| `tipo` | Tipo da interação, com valor padrão `outro`. |
| `texto` | Conteúdo textual da mensagem. |

O campo `tipo` aceita os seguintes valores:

- `depoimento`
- `pergunta_tecnica`
- `feedback`
- `reclamacao`
- `projeto`
- `outro`

O lote também informa `origem_comunidade`, `periodo_referencia` e
a lista de interações a processar.

## 4. Classificação

A função `classificar()` escolhe o modo de execução por meio de
`modo_mock()`.

### 4.1. Modo simulado

No modo simulado, `_classificar_mock()` aplica regras simples:

1. Converte o texto para minúsculas.
2. Procura trechos de palavras presentes nas listas `NEGATIVOS`
   e `POSITIVOS`.
3. Se encontrar um termo negativo, atribui sentimento `Negativo`
   e relevância 6.
4. Caso contrário, se encontrar um termo positivo, atribui
   `Altamente Positivo` e relevância 9.
5. Se nenhum dos dois grupos for encontrado, atribui `Neutro`
   e relevância 5.
6. Preserva o tipo informado quando ele não ? `outro`. Se for
   `outro`, usa `pergunta_tecnica` quando o texto contém `?`;
   caso contrário, mantém `outro`.
7. Deriva o tópico do nome do canal, removendo `#`, substituindo
   hífens por espaços e aplicando capitalização.

A busca por palavras negativas tem precedência sobre a busca por
palavras positivas.

Essas regras servem para permitir o desenvolvimento e a verificação
do fluxo sem depender de uma chamada ao modelo de linguagem. Não
representam um classificador treinado nem uma avaliação semântica
completa da mensagem.

### 4.2. Modo Gemini

Quando o modo simulado não está ativo, a função envia o canal e o texto
ao Gemini, utilizando as instruções `CLASSIFICADOR_SISTEMA`, definidas
em `app/prompts.py`.

A resposta esperada contém:

- `tipo`
- `sentimento`
- `topico`
- `relevancia`

A saída deve estar em JSON. Após a interpretação da resposta, a construção
do modelo `Analise`, definido em `app/schemas.py`, aplica as validações
estruturais previstas no contrato. Isso não garante que a classificação
esteja semanticamente correta.

O cliente em `app/llm.py` utiliza o modelo configurado em
`GEMINI_MODELO`, cujo padrão no código é `gemini-2.5-flash`.
As chamadas JSON usam temperatura 0,4 e podem ser repetidas em caso
de exceção, com espera crescente entre tentativas.

A função `modo_mock()` ativa o modo simulado quando `LLM_MODO=mock`
ou quando `GEMINI_API_KEY` não está definida. Portanto, configurar
uma chave não comprova, por si só, que uma chamada real foi executada
com sucesso.

## 5. Regras de roteamento

Depois da classificação, `decidir_rota()` determina a rota.
Essa função contém regras de negócio independentes do modo de
classificação utilizado.

As regras são avaliadas nesta ordem:

| Prioridade | Condição | Rota |
|---|---|---|
| 1 | Sentimento `Negativo` ou `Altamente Negativo`, ou tipo `reclamacao` | `alerta` |
| 2 | Tipo `depoimento` ou `projeto`, sentimento `Altamente Positivo` ou `Positivo` e relevância maior ou igual a 7 | `case_sucesso` |
| 3 | Tipo `pergunta_tecnica`, sem correspondência nas regras anteriores | `faq` |
| 4 | Nenhuma das condições anteriores | `nenhuma` |

A ordem é relevante: uma reclamação ou interação negativa é
encaminhada para `alerta`, mesmo que também possa corresponder a
uma regra posterior.

### 5.1. Exemplos ilustrativos

Os exemplos abaixo descrevem o comportamento esperado das regras
de roteamento, considerando que os valores de classificação já foram obtidos.

| Tipo | Sentimento | Relevância | Rota |
|---|---|---:|---|
| `depoimento` | `Altamente Positivo` | 9 | `case_sucesso` |
| `pergunta_tecnica` | `Neutro` | 5 | `faq` |
| `feedback` | `Negativo` | 6 | `alerta` |
| `reclamacao` | `Positivo` | 8 | `alerta` |
| `projeto` | `Positivo` | 6 | `nenhuma` |
| `outro` | `Neutro` | 5 | `nenhuma` |

Os exemplos são ilustrativos e não devem ser interpretados como
resultados de uma avaliação de desempenho do classificador.

## 6. Orquestração do processamento

Em `app/grafo.py`, o fluxo é coordenado pelo LangGraph:

1. `classificar`: analisa todas as interações do lote.
2. `roteador`: identifica as rotas presentes e seleciona os ramos
   correspondentes.
3. `gerar_case`: seleciona a interação de maior relevância entre
   as que seguem para `case_sucesso` e gera um rascunho para LinkedIn.
4. `gerar_faq`: produz sugestões de conteúdo para as interações
   encaminhadas à rota `faq`.
5. `gerar_alerta`: cria registros para as interações encaminhadas
   ? rota `alerta`.
6. `gerar_newsletter`: gera um destaque semanal com base nas análises.
7. `salvar_oci`: solicita o armazenamento do pacote de resultados.

Os ramos de casos de sucesso, FAQ e alertas são ativados conforme
as rotas encontradas no lote. Quando nenhuma dessas rotas est?
presente, o roteador direciona o fluxo diretamente à newsletter.

O nome `salvar_oci` representa a etapa de persistência no grafo;
o destino efetivo depende da configuração e do resultado retornado
pela implementação de armazenamento.

## 7. Saídas da análise

Cada análise contém:

- autor, canal e texto original;
- tipo e sentimento;
- tópico;
- relevância de 0 a 10;
- rota escolhida.

A resposta do processamento também inclui um resumo da comunidade,
os ativos gerados e as informações de armazenamento.

Os ativos podem incluir um rascunho de publicação para LinkedIn,
sugestões de FAQ, alertas e um destaque para a newsletter semanal.
A geração desses conteúdos não equivale à sua publicação.

Na rota `case_sucesso`, é selecionada a interação de maior relevância
para gerar o rascunho de LinkedIn. Na rota `faq`, é produzida uma sugestão
para cada interação encaminhada ao ramo. Os alertas incluem o autor, o
sentimento, o canal e um trecho de até 100 caracteres do texto original.

## 8. Limitações conhecidas

### 8.1. Limitações do modo simulado

- A classificação depende de palavras e trechos predefinidos.
- A busca não interpreta completamente contexto, ironia, negação
  ou intenção.
- Uma expressão pode corresponder a um trecho de palavra e provocar
  uma classificação inadequada.
- A identificação de perguntas depende do caractere `?` quando o
  tipo recebido é `outro`.
- Os valores de relevância são fixos por regra, não calculados
  individualmente a partir do significado da mensagem.
- O tópico é derivado do canal, não extraído semanticamente do texto.

### 8.2. Limitações gerais

- A rota depende dos valores produzidos na classificação e da ordem
  das regras de negócio.
- Uma classificação incorreta pode levar à geração de um ativo
  inadequado ou ao encaminhamento incorreto de uma interação.
- A resposta real do Gemini depende do modelo, das instruções e
  da resposta recebida; a implementação da integração não comprova
  que o serviço real foi validado.
- Os resultados em modo simulado não devem ser usados como evidência
  de qualidade do Gemini.
- Conteúdos gerados devem passar por revisão humana, incluindo
  verificação de contexto, privacidade, autorização e fidelidade
  às informações fornecidas.
- A configuração da OCI não garante que o upload será concluído com sucesso.
- Se o upload falhar, a implementação retorna o status `erro`, sem
  salvar automaticamente uma cópia local como alternativa.
- O caminho do objeto utiliza o ano atual do sistema junto ao período
  informado, o que pode não corresponder ao ano de um período histórico.
- O contrato de entrada não exige explicitamente uma lista não vazia
  de interações. Como a geração da newsletter utiliza a interação de
  maior relevância, um lote vazio pode provocar erro no processamento.

## 9. Verificação e avaliação

A execução dos testes automatizados ajuda a verificar contratos,
regras e integração entre componentes. Um resultado de testes
bem-sucedido não comprova, isoladamente, a qualidade semântica
da classificação.

A avaliação quantitativa do classificador, incluindo métricas,
análise de erros e conclusões sobre desempenho, deve ser documentada
separadamente a partir de um conjunto de dados e de um procedimento
de avaliação definidos pela equipe.

Antes de afirmar que a integração real está validada, é necessário
registrar uma execução efetiva com o Gemini configurado e verificar
seus resultados. A integração com armazenamento externo também deve
ser verificada separadamente do modo de armazenamento local.

## 10. Referências no código

- Classificação e roteamento: `app/ia.py`
- Instruções do modelo: `app/prompts.py`
- Cliente Gemini e seleção de modo: `app/llm.py`
- Modelos e contratos: `app/schemas.py`
- Orquestração: `app/grafo.py`
- Persistência: `app/storage.py`
