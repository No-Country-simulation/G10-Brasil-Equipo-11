# Radar analítico e comparação de lotes

O radar transforma análises já produzidas pelo pipeline em distribuições, contagens de perguntas por tópico e comparação descritiva entre lotes. Atende à contribuição de Análise de Dados nas prioridades de radar da comunidade e comparação entre períodos. Seus indicadores dependem da qualidade das classificações, avaliada separadamente em [Avaliação das classificações](avaliacao_classificacoes.md).

Não há um índice numérico de saúde, inferência de satisfação de pessoas ou medição de impacto. O radar não modifica o classificador, não implementa armazenamento, autenticação nem uma nova interface de curadoria. O relatório HTML pode ser aberto localmente e os módulos podem ser consumidos pela interface existente após alinhamento com a frente responsável.

## Demonstração reproduzível

Com o ambiente do projeto ativado, na raiz:

```powershell
python scripts/analisar_comunidade.py --demonstracao
```

Abra `data/output/radar/radar.html`. O comando produz dois lotes sintéticos de 30 mensagens, selecionando posições alternadas da base de avaliação. A classificação usa **mock e tipo oculto**, mesmo se houver chave Gemini configurada. A variável de modo é restaurada ao final. Os lotes A/B são recortes artificiais, não períodos observados de uma comunidade; essa informação aparece no relatório.

O relatório expõe as limitações do mock, inclusive quando perguntas sociais recebem tipo técnico ou quando nenhum depoimento é reconhecido. Não substitui as previsões por referências para melhorar a demonstração.

## Entrada para lotes existentes

A API atual retorna `analises`, mas não inclui os metadados de origem e período em sua resposta. Monte um envelope analítico usando os metadados do lote de entrada correspondente, preservando cada análise retornada:

```json
{
  "origem_comunidade": "comunidade_identificada",
  "periodo_referencia": "2026-10-01_a_2026-10-07",
  "natureza_dados": "sintetica",
  "modo_classificacao": "mock",
  "analises": [
    {
      "autor": "participante_001",
      "canal": "#duvidas-sql",
      "texto": "Como evito duplicar clientes ao juntar os pedidos?",
      "tipo": "pergunta_tecnica",
      "sentimento": "Neutro",
      "topico": "SQL JOIN",
      "relevancia": 8,
      "rota": "faq"
    }
  ]
}
```

`natureza_dados` aceita `sintetica`, `real` ou `nao_informada`; `modo_classificacao` aceita `mock`, `gemini`, `importado` ou `nao_informado`. Esses valores são declarações da origem, não prova de execução externa. Os cinco campos do envelope são obrigatórios. Análises vazias, campos desconhecidos, rótulos fora do contrato e pontuações não inteiras são rejeitados. Uma rota formalmente válida, mas divergente da regra do pipeline, permanece na contagem original e gera um indicador de inconsistência.

```powershell
python scripts/analisar_comunidade.py --atual caminho/lote_atual.json
python scripts/analisar_comunidade.py --atual caminho/lote_atual.json --anterior caminho/lote_anterior.json --saida data/output/comparacao
```

Lotes comparados precisam declarar a mesma comunidade, natureza e modo, além de períodos distintos. A identidade dos metadados é condição necessária, mas não comprova comparabilidade: confira também duração, canais cobertos, critério de coleta e composição das amostras. O sistema não possui datas por mensagem para verificar essas condições.

## Dicionário de indicadores

| Indicador | Definição e denominador | Leitura adequada |
| --- | --- | --- |
| Total de interações | Número de registros válidos do lote | Mensagens, não pessoas únicas |
| Distribuição de tipo, sentimento e rota | Quantidade por categoria / total de mensagens; classes ausentes aparecem com zero | Composição das classificações do lote |
| Mensagens negativas | Sentimento `Negativo` ou `Altamente Negativo` / total | Sinal expresso nas mensagens, sujeito a erro de classificação |
| Mensagens em alerta | Rota `alerta` / total | Encaminhamento pela regra, não gravidade confirmada |
| Perguntas técnicas | Registros com tipo `pergunta_tecnica` | Inclui perguntas enviadas a alerta |
| Perguntas em alerta | Tipo `pergunta_tecnica` e rota `alerta` | Dúvidas que continuam relevantes mesmo fora da rota FAQ |
| Tópicos repetidos nas perguntas | Tópicos com pelo menos duas perguntas após normalização textual | Candidatos a inspeção de recorrência |
| Possíveis duplicatas | Total menos combinações distintas de autor, canal e texto | Sinal para conferir importação; os registros são preservados |
| Inconsistências de rota | Rota prevista diferente da aplicação de `decidir_rota` à própria previsão | Problema de coerência a investigar, sem reclassificação automática |
| Variação em pontos percentuais | `100 × (proporção atual − proporção anterior)` | Diferença descritiva entre participações, com denominadores próprios |

Exemplo: dois alertas em dez mensagens representam 20%; três em vinte representam 15%. A quantidade aumentou em um e a participação caiu cinco pontos percentuais. Nenhuma dessas medidas, isoladamente, prova melhora ou piora da comunidade.

## Perguntas e recorrência

O agrupamento considera somente perguntas técnicas e normaliza o texto do tópico com Unicode NFC, caixa e espaços. Não remove acentos, não usa embeddings e não verifica equivalência semântica. Assim, `SQL JOIN` e `sql   join` ficam juntos; `junção de tabelas` permanece separado.

O relatório preserva os índices de origem, começando em 1, para localizar as mensagens no lote. Duas mensagens sobre um tópico podem conter dúvidas diferentes, e uma pergunta pode estar repetida sob tópicos diferentes. Cabe ao revisor conferir contexto e existência de resposta antes de recomendar FAQ. O limiar de duas ocorrências é um critério exploratório documentado, não uma medida de precisão do detector.

O mock deriva tópicos do canal. Nesse modo, a contagem pode refletir o nome do canal em vez do conteúdo das perguntas. A detecção semântica de dúvidas recorrentes segue como evolução a alinhar com Dados/IA; a avaliação de seus agrupamentos deve usar referências e revisão próprias.

## Exportação, privacidade e rastreabilidade

São produzidos `radar.html`, `radar.json`, `distribuicoes.csv` e `comparacao_categorias.csv`. Sem lote anterior, o último CSV contém apenas o cabeçalho, e a comparação fica explicitamente indisponível no relatório. A demonstração também salva seus dois lotes sintéticos para permitir reprodução e inspeção. Uma nova execução na mesma pasta substitui os relatórios; use pastas distintas para preservar versões.

As saídas agregadas omitem autores e textos, mas tópicos livres podem conter informações pessoais. Isso reduz a exposição direta; **não implementa anonimização nem controle de acesso**. Para dados reais, a autorização de coleta e compartilhamento e a revisão dos tópicos continuam necessárias. O comando de análise é local e não envia mensagens a provedores.

O JSON registra hashes SHA256 dos lotes usando serialização JSON com chaves ordenadas e os índices de origem. Esses hashes identificam o conteúdo canônico usado no radar; diferem do hash dos bytes do arquivo usado na avaliação de classificações. Nenhum dos hashes é assinatura de autenticidade.

## Relação com as oito prioridades

| Prioridade | Contribuição desta frente | Dependência ou limite |
| --- | --- | --- |
| Radar da comunidade | Indicadores, distribuições, relatório e recomendações explicadas | Qualidade do classificador e cobertura da coleta |
| Dúvidas recorrentes | Contagem de perguntas por tópico e referências à origem | Agrupamento semântico e validação da utilidade permanecem como evolução |
| Qualidade da IA | Base com 60 referências revisadas individualmente por Everson em 24/10/2026, rubrica, métricas e análise de erros | Execução real do modelo e avaliação de generalização; segunda revisão independente pode reforçar a referência |
| Curadoria explicada e rastreável | Evidência literal, justificativa, previsão, divergência e fila de revisão | Histórico operacional de aprovação depende de interface e persistência |
| Memória institucional | Requisitos de fontes e qualidade documentados na rubrica | Busca, armazenamento e recuperação não são implementados nesta frente |
| Priorização de problemas | Prioridade para conferir erros e alertas perdidos na avaliação | Não há classificação de gravidade, SLA ou automação de atendimento |
| Comparação entre períodos | Contagens e proporções por categoria com variação em p.p. | Metadados e comparabilidade da coleta precisam ser conferidos |
| Privacidade e acesso | Base fictícia, exportação agregada e proteções de HTML/CSV | Autenticação, consentimento e controle de acesso dependem das frentes responsáveis |

A contribuição acrescenta instrumentos de análise à base existente, sem declarar como concluídas capacidades que dependem das outras frentes.
