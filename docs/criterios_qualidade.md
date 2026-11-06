# Critérios de qualidade das classificações

**Responsável pela frente:** Everson — Análise de Dados

**Versão da rubrica:** 1.0.0

**Situação:** revisão individual concluída por Everson em 24/10/2026. Os 60 casos, suas classificações, intervalos, justificativas e os critérios foram aceitos sem alterações. As metas da avaliação foram aprovadas pelo responsável pela frente analítica.

**Método:** conferência individual de propostas, registrada na base 1.1.0. Não houve dupla anotação independente nem medição de concordância entre revisores. A aprovação registrada se limita a Everson, sem atribuí-la a outros integrantes ou aos avaliadores do hackathon.

Esta avaliação atende à entrega de analisar classificações e definir critérios de qualidade, aproveitando os contratos da branch `data-scientist`. O escopo é a classificação de interações e a consistência das rotas existentes. Não altera o pipeline, os prompts, a API nem as responsabilidades de integração, persistência e interface.

A referência técnica é [`app/schemas.py`](../app/schemas.py), [`app/prompts.py`](../app/prompts.py) e a função `decidir_rota` em [`app/ia.py`](../app/ia.py). A relevância mantém o significado do classificador atual: **potencial de transformar uma mensagem em conteúdo de marketing ou FAQ**, em escala inteira de 0 a 10. Ela não é uma medida de urgência, gravidade, risco, valor da pessoa ou prioridade de atendimento.

## Conjunto de avaliação

O arquivo [`data/avaliacao_classificacoes.json`](../data/avaliacao_classificacoes.json) contém 60 mensagens sintéticas inéditas, diferentes dos exemplos de demonstração e dos exemplos dos prompts. Todos os autores são identificadores fictícios no formato `participante_XXX`. Nomes de projetos, situações, quantidades e resultados fazem parte dos cenários fictícios. Não foram usados registros de uma comunidade real.

| Recorte | Quantidade | Finalidade |
| --- | ---: | --- |
| Referência | 48 | Intenções identificáveis e variação de conteúdo, sentimento e relevância |
| Desafio | 12 | Negação, ironia, intenção mista, citação e pistas enganosas de canal ou pontuação |
| Cada tipo oficial | 10 | Comparação entre categorias sem predomínio artificial de um único tipo |
| Referência por tipo | 8 | Comparação do recorte regular |
| Desafio por tipo | 2 | Inspeção separada das situações que exigem interpretação contextual |

O balanceamento por tipo é deliberado para diagnóstico; não representa a frequência dessas categorias em uso real. Os cinco sentimentos e as quatro rotas estão presentes também no recorte de referência, mas não foram artificialmente balanceados. O recorte de desafio não contém os dois extremos de sentimento: seu foco é interpretação contextual, não cobertura independente de todo o vocabulário.

| Dimensão | Classe | Total | Referência | Desafio |
| --- | --- | ---: | ---: | ---: |
| Sentimento | Altamente Positivo | 6 | 6 | 0 |
| Sentimento | Positivo | 14 | 10 | 4 |
| Sentimento | Neutro | 20 | 15 | 5 |
| Sentimento | Negativo | 13 | 10 | 3 |
| Sentimento | Altamente Negativo | 7 | 7 | 0 |
| Rota | `case_sucesso` | 8 | 6 | 2 |
| Rota | `faq` | 7 | 6 | 1 |
| Rota | `alerta` | 24 | 19 | 5 |
| Rota | `nenhuma` | 21 | 17 | 4 |

As contagens devem acompanhar os relatórios para tornar explícito o suporte de cada métrica. Os 17 casos originalmente sinalizados para revisão prioritária são os 12 desafios e cinco casos de referência. Todos foram incluídos na revisão dos 60 casos.

Cada caso registra a mensagem, a classificação de referência, uma faixa de relevância, a rota, uma justificativa e uma evidência literal extraída do texto. `marcadores` identificam propriedades analíticas do caso, sem integrar o contrato de produção. Não devem ser fornecidos ao classificador.

`revisao_humana: true` preserva a **prioridade histórica de encaminhamento para revisão**, e `motivo_revisao` explica a ambiguidade ou o ponto de atenção. Essa sinalização não é um estado de aprovação ou pendência. O estado atual vem da raiz `status_anotacao: revisada_individualmente` e do registro `revisao_anotacao`, com responsável, data, método, decisão, versões, hashes e IDs conferidos. Todos os casos AV001–AV060 foram aceitos individualmente por Everson. Em uma base legada com `status_anotacao: proposta_pendente_revisao_humana`, os rótulos continuam propostos até a revisão efetiva.

## Regras de anotação de tipo

O tipo decorre da intenção principal expressa na mensagem, considerando o texto completo. Não deve ser deduzido apenas do canal, de uma palavra isolada ou da presença de `?`. Se houver mais de uma intenção, identificar a ação principal pedida ou apresentada; registrar a ambiguidade para revisão quando não houver predominância clara.

| Tipo do contrato | Regra de inclusão | Fronteira a observar |
| --- | --- | --- |
| `depoimento` | Narrativa pessoal de trajetória, experiência, aprendizado, conquista ou dificuldade vivida | O centro é a experiência da pessoa. Apresentar um artefato como entrega é `projeto`; uma saudação ou aviso de disponibilidade é `outro` |
| `pergunta_tecnica` | Solicitação de explicação, diagnóstico ou orientação sobre tecnologia, programação, dados ou ferramentas | Pode não conter `?`. Dúvida social é `outro`; cobrar reparação de serviço é `reclamacao`; sugerir conteúdo futuro é `feedback` |
| `feedback` | Avaliação de material, atividade ou experiência, com elogio, crítica ou proposta de melhoria | Uma crítica continua sendo feedback quando seu centro é avaliar ou sugerir evolução. Demanda de reparar falha concreta de serviço é `reclamacao` |
| `reclamacao` | Relato de falha de serviço, atendimento ou entrega da organização com cobrança, pedido ou necessidade de reparação | Pode ter tom neutro ou incluir elogio. Problemas no próprio código com pedido de orientação permanecem `pergunta_tecnica` |
| `projeto` | Apresentação, compartilhamento ou atualização de artefato, protótipo, solução ou entrega técnica | O centro é o que foi construído ou disponibilizado. A emoção pode ser positiva, neutra ou negativa |
| `outro` | Saudações, avisos logísticos, conversas sociais e mensagens que não atendem aos critérios anteriores | A presença de tema técnico em uma citação ou título não basta para criar uma pergunta técnica |

Exemplos de fronteira no conjunto:

- **AV024 × AV031:** sugerir mais prática em futuras aulas é feedback; pedir a restauração do acesso bloqueado é reclamação.
- **AV003 × AV042:** contar uma evolução de aprendizagem é depoimento; anunciar uma versão de software é projeto.
- **AV017 × AV051:** pedir orientação técnica sem interrogação é pergunta técnica; perguntar quem vai a um café é outro.
- **AV039:** elogio ao atendimento pode coexistir com uma reclamação cujo objetivo é corrigir uma falha pendente.
- **AV050 e AV060:** citar “feedback” ou uma pergunta técnica não substitui a análise da intenção principal.

## Regras de anotação de sentimento

Anotar a avaliação afetiva expressa pelo autor sobre a situação principal. Não inferir emoção apenas porque ocorreu uma entrega, porque existe um erro técnico ou porque o autor fez uma pergunta. Negação, ironia, citação e contexto podem inverter ou neutralizar a interpretação de palavras isoladas.

| Sentimento do contrato | Critério |
| --- | --- |
| `Altamente Positivo` | Entusiasmo, celebração ou satisfação excepcional e explícita, com intensidade além de aprovação comum |
| `Positivo` | Satisfação, aprovação, gratidão ou esperança favorável expressa, sem intensidade excepcional |
| `Neutro` | Descrição factual, pedido objetivo ou proposta sem valência afetiva predominante expressa |
| `Negativo` | Insatisfação, decepção, irritação, preocupação ou tristeza expressa, sem intensificação excepcional |
| `Altamente Negativo` | Indignação, raiva, rejeição ou frustração intensa e explícita; não deve ser inferida apenas por exclamação ou uso de caixa alta |

Em mensagens mistas, considerar a intenção central, o alvo da avaliação e a evidência afetiva explícita. Um contexto misto não implica automaticamente `Neutro`. Se a interpretação depender de contexto ausente, manter a proposta rastreável e encaminhar o caso para revisão. Intensidade emocional não é diagnóstico nem medida de urgência.

AV009 e AV049 negam uma avaliação negativa; AV010, AV020 e AV030 contêm ironia; AV039 combina elogio e solicitação de reparação. AV044 e AV048 demonstram que uma entrega específica pode ter sentimento neutro. AV055 contém uma despedida positiva, mas a emoção central é a tristeza de não participar.

## Relevância: potencial de conteúdo e FAQ

Avaliar quanto o texto oferece de especificidade, contexto, aprendizado transferível e material aproveitável para uma história ou explicação. Não adicionar resultados, alcance, indicadores ou causas que não constem da mensagem. As faixas abaixo orientam a anotação; não substituem a leitura do caso.

| Pontuação | Interpretação |
| --- | --- |
| 0–2 | Saudação, conversa social, ruído ou aviso sem conteúdo reutilizável relevante para o escopo |
| 3–4 | Contexto limitado ou ocorrência individual; exigiria elaboração adicional importante para virar conteúdo |
| 5–6 | Assunto útil, mas com contexto, desenvolvimento ou diferenciação insuficientes para destaque editorial |
| 7–8 | Mensagem específica e contextualizada, com aprendizado reutilizável, dúvida bem delimitada ou entrega demonstrável |
| 9–10 | Material excepcionalmente completo para uma história ou explicação, com elementos concretos que sustentem o destaque; pontuação máxima deve ser rara |

Uma dúvida bem delimitada pode ter relevância alta sem entusiasmo. Uma reclamação importante para o suporte pode ter relevância editorial baixa. Um comentário social muito positivo ou muito negativo pode ter pontuação baixa. Esta dimensão não autoriza ignorar alertas nem priorizar pessoas por potencial de marketing.

Como a pontuação é parcialmente subjetiva, cada referência usa `relevancia_min` e `relevancia_max` inclusivos, sempre entre 0 e 10, com amplitude máxima de 3 (`max - min <= 3`). O acerto ocorre quando a previsão inteira pertence à faixa. A faixa representa tolerância de anotação, não intervalo estatístico de confiança. Não é preciso escolher o ponto médio como única resposta correta.

Para depoimentos e projetos positivos, uma faixa não pode atravessar o limiar 7: `[5, 7]` produziria rotas diferentes nos extremos e seria inválida nesse contexto. A rota de referência precisa coincidir com `decidir_rota` tanto no mínimo quanto no máximo. Nas demais combinações, a relevância não altera a rota atual. O marcador `relevancia_limite` identifica AV003 (mínimo 7, elegível a case) e AV047 (máximo 6, sem case), para inspecionar os dois lados dessa fronteira. A comparação verifica a aplicação da regra; não transforma a pontuação editorial subjetiva em uma medida exata.

## Rotas e precedência

As rotas de referência reproduzem a regra vigente de `decidir_rota`, nesta ordem:

1. **`alerta`:** sentimento `Negativo` ou `Altamente Negativo`, ou tipo `reclamacao`, qualquer que seja a relevância.
2. **`case_sucesso`:** tipo `depoimento` ou `projeto`, sentimento `Positivo` ou `Altamente Positivo` e relevância maior ou igual a 7.
3. **`faq`:** tipo `pergunta_tecnica` que não tenha sido encaminhado para alerta.
4. **`nenhuma`:** todas as demais combinações.

AV015 e AV020 devem ir para alerta, embora sejam dúvidas com potencial de FAQ. AV034 e AV037 também devem ir para alerta, apesar do sentimento neutro. AV039 deve ir para alerta mesmo com sentimento positivo, por ser reclamação. AV004 e AV047 não atingem o limiar editorial de case. AV048 tem relevância alta, mas sentimento neutro, portanto fica em `nenhuma`.

A regra atual também envia comentários sociais negativos para alerta, como AV055 e AV056. Isso é comportamento esperado do contrato, embora possa produzir alertas pouco úteis. Discutir uma futura mudança de negócio é diferente de alterar os rótulos para esconder essa limitação. Aderência à regra e utilidade do encaminhamento precisam ser avaliadas separadamente.

`case_sucesso` indica candidatura a conteúdo, não aprovação para publicação. `faq` indica oportunidade de material técnico, não resposta validada. `alerta` é uma sinalização para análise, não diagnóstico de risco. Nenhuma rota representa autorização de publicação ou substitui revisão contextual.

## Protocolo de avaliação

1. Fixar a versão do conjunto, da rubrica e do código antes de comparar execuções. Registrar modo de execução, configuração de modelo quando aplicável, total de casos, falhas e identificação do conjunto utilizado. Para rodadas do modelo real, registrar também início da execução em UTC; para arquivos externos, registrar quando foram importados, sem confundir esse horário com a execução original. No mock, os resultados são determinísticos e identificados pela configuração e pelos hashes, sem timestamp variável.
2. Executar todos os casos sem fornecer `referencia`, `justificativa`, `evidencia`, `marcadores`, `grupo` ou sinalizadores de revisão ao classificador.
3. No modo principal, ocultar o tipo anotado da entrada, usando `tipo: outro`. O arquivo preserva `entrada.tipo == referencia.tipo` por consistência do contrato, mas o mock reutiliza esse tipo se ele for fornecido. Avaliar com o tipo informado deve ser tratado apenas como diagnóstico auxiliar e identificado como tal, nunca como inferência independente de tipo.
4. Comparar tipo, sentimento e rota com os rótulos de referência, informando o estado de revisão da base; comparar relevância com sua faixa inclusiva. Medir a cobertura de previsões válidas sobre o total de casos tentados. Falhas ou saídas inválidas não devem desaparecer do denominador nem ser confundidas com acertos.
5. Apresentar métricas agregadas e por classe com suporte, matrizes de confusão, resultados separados por grupo e lista de divergências com texto, evidência e justificativa de referência.
6. Examinar os erros por causa: confusão de intenção, negação, ironia, intensidade, canal, pontuação, relevância e consequência sobre a rota. Não alterar a referência apenas para melhorar a pontuação obtida.

A avaliação de classificação deve funcionar sem geração de ativos nem gravação na OCI. O modo simulado é um baseline de regras para testar contrato, relatório e diagnóstico; não mede capacidade do Gemini. Resultados de um modelo real só podem ser relatados após execução identificada e concluída, com as limitações e falhas registradas.

Separar dois testes: **aderência de rota** verifica se a rota prevista segue `decidir_rota` para a própria classificação prevista; **qualidade de rota** compara com a referência. É possível ter aderência perfeita e qualidade baixa quando o tipo, o sentimento ou a relevância estão errados.

## Indicadores e metas da avaliação

As metas a seguir foram **aprovadas por Everson em 24/10/2026 para esta avaliação**, como responsável pela frente analítica. Essa decisão não constitui aprovação de toda a equipe ou dos avaliadores do hackathon. Não são resultados já alcançados, compromissos de produção, limites universais nem evidência de confiabilidade em dados reais. As metas de qualidade usam os 48 casos de referência; cobertura de saídas válidas e consistência da rota usam todos os 60 casos. As métricas do conjunto inteiro e dos 12 desafios também devem permanecer visíveis, porque um agregado pode ocultar falhas sistemáticas.

| Indicador | Definição | Meta da avaliação |
| --- | --- | ---: |
| Macro-F1 de tipo | Média não ponderada do F1 dos seis tipos no recorte de referência | ≥ 0,80 |
| Macro-F1 de sentimento | Média não ponderada do F1 dos cinco sentimentos no recorte de referência | ≥ 0,75 |
| Macro-F1 de rota | Média não ponderada do F1 das quatro rotas no recorte de referência | ≥ 0,85 |
| Recall de `alerta` | Alertas corretamente recuperados / alertas esperados no recorte de referência | ≥ 0,90 |
| Relevância dentro da faixa | Previsões inteiras entre mínimo e máximo inclusivos / 48 casos de referência | ≥ 0,80 |
| Cobertura de previsões válidas | Casos com previsão completa e válida / 60 casos tentados | 1,00 |
| Cobertura das classes | Classes com suporte no recorte de referência / 15 classes oficiais (6 tipos, 5 sentimentos, 4 rotas) | 1,00 |
| Consistência de rota | Casos com previsão válida e rota igual à regra aplicada à própria previsão / 60 casos | 1,00 |

Para cada classe, `precisão = VP / (VP + FP)`, `recall = VP / (VP + FN)` e `F1 = 2 × VP / (2 × VP + FP + FN)`. Precisão sem previsões e recall sem referências são indefinidos e devem aparecer como ausentes (`null`), não como sucesso. F1 é zero quando há suporte em referência ou previsão, mas nenhum acerto; é indefinido quando ambos os suportes são zero. Classe sem suporte de referência não demonstra desempenho.

A macro-F1 dá igual peso às classes com suporte de referência, e o relatório informa quantas classes participaram. Neste conjunto, todas as classes oficiais têm suporte nos 48 casos de referência. No recorte de desafio, as duas classes extremas de sentimento ficam fora da média por não terem suporte; portanto, a macro-F1 desse recorte não deve ser interpretada como cobertura dos cinco sentimentos. Falhas de previsão reduzem recall das classes de referência afetadas e a cobertura. As matrizes e o relatório precisam deixar visíveis previsões ausentes ou inválidas. Para medir o risco de perder sinais relevantes, reportar explicitamente quais alertas de referência não foram recuperados, além do recall agregado.

Uma decisão de qualidade exige examinar todas as metas conjuntamente e revisar erros relevantes, não apenas atingir uma média. Cumprir as metas neste conjunto sintético pequeno não autoriza publicação automática nem uso sem supervisão. A comparação atual é uma **avaliação contra referências sintéticas revisadas individualmente**; essa condição não demonstra generalização para comunidades reais.

## Validação humana e manutenção

A revisão da base 1.1.0 foi concluída por Everson em 24/10/2026, após a leitura de cada mensagem, classificação, intervalo, justificativa e dos critérios. Os 60 casos foram aceitos sem alterações. A rubrica permanece na versão 1.0.0 porque as regras semânticas e os limiares foram preservados; a nova versão da base acrescenta o registro de revisão. A modalidade é uma conferência individual de propostas: não equivale a uma anotação independente nem demonstra concordância entre dois revisores. A quantidade de pessoas, os casos efetivamente conferidos e o método utilizado acompanham o estado de revisão.

Como reforço metodológico, recomenda-se que duas pessoas anotem os casos independentemente, usando apenas a mensagem e a rubrica, e depois reconciliem divergências de tipo, sentimento, relevância e rota. A segunda revisão não é requisito para registrar a revisão individual ou compartilhar a implementação. Nos dois métodos, registrar quem revisou, a decisão, a data e a justificativa em uma versão identificada, sem inventar aprovações ou atribuições retroativas. Aprovar a publicação do código, por si só, não significa ter conferido os rótulos.

Em futuras revisões, dar prioridade aos 12 desafios e aos casos sinalizados, mas revisar também os exemplos regulares para evitar falsa confiança. Discordâncias podem indicar necessidade de melhorar a rubrica; um caso com mais de uma interpretação razoável não deve ser forçado a se tornar uma verdade incontestável. AV039 mantém a interpretação positiva aceita por Everson, com a ambiguidade entre elogio e reparação documentada. Qualquer mudança nos casos ou inclusão de novos exemplos exige revisão do conteúdo alterado e atualização do registro, sem herdar automaticamente a aprovação anterior. Depois, versionar a mudança e reexecutar a avaliação com comparação explícita da versão.

O conjunto é de avaliação e não deve ser copiado para exemplos de prompt, ajuste ou treinamento e depois reutilizado como teste independente. Se os erros orientarem mudanças no classificador, manter estes 60 casos como regressão e criar posteriormente um conjunto separado e não utilizado durante o desenvolvimento para estimar generalização.

## Relação com indicadores e curadoria

Esta avaliação fornece referências revisadas individualmente, evidências textuais e divergências rastreáveis por ID. A fila de inspeção serve para conferir resultados do conjunto; não registra decisão editorial de aprovação, correção ou rejeição de conteúdo publicado. Preservar o ID, a versão da base, a previsão original, o motivo e a decisão da revisão é um requisito proposto para uma futura curadoria com histórico, a alinhar com as frentes de interface e persistência.

As demais prioridades do projeto precisam de critérios próprios, antes de serem apresentadas como funcionalidades validadas:

| Frente | Indicador ou critério proposto | Limite desta avaliação |
| --- | --- | --- |
| Radar da comunidade | Distribuição de categorias e sentimentos com denominadores e taxa de falhas explícitos | A amostra balanceada sintética não estima a saúde de uma comunidade real |
| Dúvidas recorrentes | Precisão dos agrupamentos e utilidade das sugestões avaliadas por pessoas | Dois temas próximos não demonstram recorrência; contagem exata de tópicos não é agrupamento semântico |
| Qualidade da IA | Métricas por classe, cobertura, evidência e análise de erros | Classificação não valida automaticamente conteúdo gerado |
| Curadoria rastreável | Proporção de decisões com responsável, motivo, data e origem preservados | A sinalização `revisao_humana` não é um registro de aprovação |
| Memória da comunidade | Proporção de respostas com fonte recuperável e previamente aprovada | Este conjunto não é uma base de conhecimento factual nem valida recuperação de fontes |
| Priorização de problemas | Recall de sinais relevantes e concordância com responsáveis sobre prioridades | `alerta` e relevância editorial não medem gravidade, urgência ou prazo de resolução |
| Comparação entre períodos | Mesmos critérios, população de comparação identificada e cobertura de coleta documentada | As mensagens sintéticas não têm períodos observacionais nem sustentam tendências reais |
| Privacidade | Verificação de autorização e revisão antes de reutilizar dados reais ou publicar | Identificadores fictícios protegem a demonstração, mas não validam um controle de privacidade em produção |

Os critérios para as demais frentes são propostas para alinhamento e não comprovam suas implementações ou impacto medido. A revisão individual registrada nesta entrega se limita às referências e aos critérios da avaliação de classificações.

## Limites de interpretação

- São 60 mensagens sintéticas em português brasileiro, com apenas 10 por tipo. O suporte das classes e, especialmente, dos recortes é pequeno; diferenças de poucos casos podem alterar bastante os percentuais.
- O balanceamento de tipos não representa a distribuição real. Não extrapolar acurácia, F1, proporção de alertas, saúde da comunidade ou impacto para usuários reais.
- Rótulos, intensidade afetiva e intervalos de relevância foram aceitos em revisão individual de propostas por Everson. Não houve dupla anotação independente, estudo de concordância entre anotadores nem medição real do Gemini nesta entrega de referência.
- As mensagens são isoladas. Histórico de conversa, recorrência efetiva, consentimento, fatos citados e resolução de problemas não podem ser confirmados pelo texto sozinho.
- Temas próximos, como joins em SQL, oferecem exemplos para inspeção; não comprovam qualidade de agrupamento semântico nem recorrência real.
- As métricas cobrem classificação e roteamento. Não medem correção técnica de FAQ, fidelidade dos textos gerados, utilidade de recomendações, segurança de publicação, disponibilidade da API ou persistência na OCI.
- Sentimento negativo não equivale a crise ou alta urgência. Relevância editorial não mede gravidade e não substitui critérios específicos de atendimento.
- Conteúdos pessoais ou com acusações exigem contexto e revisão antes de reutilização. Mesmo mensagens sintéticas classificadas como case não validam um fluxo de autorização para dados reais.

A entrega permite uma avaliação reproduzível e a discussão de erros com evidências. Uma segunda revisão pode reforçar a rubrica; uma avaliação posterior do modelo real com dados apropriados, autorizados e representativos continua necessária para sustentar conclusões sobre uso real.
