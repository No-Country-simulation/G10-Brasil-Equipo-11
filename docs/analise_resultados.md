# Análise dos resultados de classificação

**Responsável pela frente:** Everson — Análise de Dados

**Base de código:** `data-scientist`, commit `4e47b060000916a2f7ca38c84c98471ff62751bc`

**Conjunto:** `avaliacao_classificacoes.json`, versão 1.1.0, 60 mensagens sintéticas

**SHA256 da base:** `a3ca1abd0462adc66ac67644f63dd421b6c15bad9a67644099f54629becc30d4`

**Modo avaliado:** mock, regras existentes de `app/ia.py`

**Situação das referências:** revisão individual de propostas concluída por Everson em 24/10/2026, com os 60 casos, classificações, intervalos, justificativas e critérios aceitos sem alterações. As metas da avaliação foram aprovadas pelo responsável pela frente analítica. Não houve dupla anotação independente nem aprovação atribuída a outros integrantes.

A versão 1.1.0 acrescenta o registro de revisão da base 1.0.0, identificada pelo SHA256 `dbebc85a8322b4d864fcd42a4ad90074aeb635598733e93dcb23c5d8fd491a6a`. Os casos e o classificador de `app/ia.py` foram preservados; por isso, as métricas permanecem iguais às da rodada anterior.

## Conclusão da avaliação

O classificador simulado produziu saídas válidas nos 60 casos, mas não atingiu as metas de qualidade da avaliação no cenário principal. O resultado é compatível com a finalidade declarada do mock: exercitar os contratos e o fluxo com regras simples. Não é uma avaliação do Gemini e não sustenta conclusões sobre qualidade em uma comunidade real.

A principal diferença metodológica é o tratamento do tipo na entrada. Com o tipo oculto, o mock acerta 15 de 60 tipos; com o tipo informado, acerta 57. A melhoria vem do reaproveitamento da anotação recebida, não de uma capacidade adicional de interpretar o texto. Separar os cenários evita apresentar esse ganho como inferência autônoma.

As métricas e os erros apontam quatro prioridades para a avaliação posterior do modelo real: intenção além da interrogação, negação/contexto, intensidade do sentimento e relevância editorial independente da emoção. O código do classificador e suas regras foram preservados para que essa evidência possa orientar a frente de Dados/IA sem alterar sua implementação.

## Resultados no conjunto completo

| Indicador — 60 casos | Tipo oculto | Tipo informado |
| --- | ---: | ---: |
| Saídas válidas | 60/60 (100%) | 60/60 (100%) |
| Acurácia de tipo | 15/60 (25,00%) | 57/60 (95,00%) |
| Macro-F1 de tipo | 0,1614 | 0,9488 |
| Acurácia de sentimento | 23/60 (38,33%) | 23/60 (38,33%) |
| Macro-F1 de sentimento | 0,2027 | 0,2027 |
| Acurácia de rota | 26/60 (43,33%) | 38/60 (63,33%) |
| Macro-F1 de rota | 0,3444 | 0,5657 |
| Relevância dentro da faixa de referência | 25/60 (41,67%) | 25/60 (41,67%) |
| Distância média à faixa de relevância | 1,15 ponto | 1,15 ponto |
| Alertas de referência não recuperados | 20 de 24 | 11 de 24 |
| Coerência da rota com a própria previsão | 60/60 (100%) | 60/60 (100%) |

No cenário com tipo oculto, 48 mensagens receberam `outro` e 12 receberam `pergunta_tecnica`. Nenhuma recebeu os quatro tipos restantes. O mock só infere pergunta pela presença de `?`; ele não implementa a inferência textual completa dos seis tipos.

Nos dois cenários, os sentimentos previstos foram 51 neutros, sete negativos e dois altamente positivos. Não houve previsão de `Positivo` nem de `Altamente Negativo`, categorias que não são emitidas pelas regras atuais. Por isso, o desempenho nessas classes é limitado por construção.

Coerência de rota em 100% dos casos confirma que a regra foi aplicada às previsões. Não confirma que essas previsões estavam corretas: sentimento, tipo e relevância incorretos podem encaminhar a mensagem para uma rota inadequada mesmo sem violar a regra.

## Metas da avaliação no recorte de referência

As metas de qualidade usam os 48 casos de referência. Os 12 desafios permanecem visíveis no relatório e no resultado agregado acima. Valores arredondados nesta tabela; as comparações no avaliador usam a precisão completa.

| Critério | Meta da avaliação | Tipo oculto | Tipo informado |
| --- | ---: | ---: | ---: |
| Macro-F1 de tipo | ≥ 0,80 | 0,1944 | 0,9791 |
| Macro-F1 de sentimento | ≥ 0,75 | 0,2124 | 0,2124 |
| Macro-F1 de rota | ≥ 0,85 | 0,4274 | 0,6468 |
| Recall de alerta | ≥ 0,90 | 0,2105 | 0,5789 |
| Relevância dentro da faixa | ≥ 0,80 | 0,4375 | 0,4375 |

Cobertura de saídas, cobertura do vocabulário de referência e consistência de rota atingiram 100%. Esses controles verificam condições necessárias de avaliação; não compensam as metas de qualidade não atendidas. As metas foram aprovadas por Everson para esta avaliação, sem constituir decisão de toda a equipe ou autorização para uso em produção.

## Erros que orientam a investigação

| Caso | Evidência e referência revisada individualmente | Resultado com tipo oculto | Implicação |
| --- | --- | --- | --- |
| AV001 | Relato de evolução e entusiasmo explícito; `depoimento`, `Altamente Positivo`, `case_sucesso` | `outro`, `Neutro`, `nenhuma` | As palavras da mensagem não acionam as regras disponíveis; uma conquista pode desaparecer do fluxo editorial |
| AV009 | “Não foi uma experiência ruim”; relato positivo com negação | `Negativo`, `alerta` | A ocorrência isolada de `ruim` prevalece sobre o contexto de negação |
| AV017 | Pedido de orientação sobre ambiente virtual, sem `?` | `outro`, `nenhuma` | Interrogação não é condição necessária para haver uma dúvida técnica |
| AV033 | Cancelamento sem aviso e pedido de remarcação; reclamação negativa | `outro`, `Neutro`, `nenhuma` | Um pedido de reparação pode deixar de receber alerta |
| AV039 | Elogio ao atendimento e pedido de correção de duplicidade | `outro`, `Neutro`, `nenhuma` | A intenção de reparação precisa ser separada da polaridade; Everson aceitou o sentimento positivo, mantendo documentada a ambiguidade para eventual segunda revisão |
| AV051 | Pergunta sobre participação em café virtual | `pergunta_tecnica`, `faq` | Interrogação também ocorre em conversa social e pode gerar oportunidade de FAQ indevida |
| AV054 | Entusiasmo sobre futebol, fora do escopo técnico | Relevância 5, contra faixa 0–2 | Emoção e utilidade editorial/técnica são dimensões independentes |

O relatório completo permite conferir texto, evidência literal, justificativa, referência e previsão. A evidência selecionada sustenta a referência aceita na revisão individual; não é uma explicação interna do raciocínio de um LLM. Nenhuma confiança probabilística é inventada.

## Uso do radar

O [radar analítico](indicadores_comunidade.md) consome as análises e apresenta distribuições, perguntas por tópico e comparação entre lotes. Na demonstração, usa dois recortes intercalados de 30 mensagens sintéticas, com tipo oculto e o mesmo classificador mock. As diferenças A/B não são tendências observadas no tempo.

As limitações da classificação propagam-se aos indicadores. Uma dúvida social classificada como técnica aparece na contagem de perguntas; um relato negativo não detectado pode ficar fora dos alertas. O valor da entrega é tornar essas dependências verificáveis e oferecer indicadores com denominadores, origem e limites claros.

Perguntas que receberam rota de alerta continuam na análise de dúvidas. Tópicos repetidos são agrupados somente por igualdade textual normalizada; são candidatos a inspeção, não prova de perguntas semanticamente equivalentes. O radar também sinaliza registros possivelmente duplicados e rotas incoerentes sem substituir os dados originais.

## Reprodução e evidências

```powershell
python scripts/avaliar_classificacoes.py --modo mock --cenario tipo_oculto
python scripts/avaliar_classificacoes.py --modo mock --cenario tipo_informado
python scripts/analisar_comunidade.py --demonstracao
python -m pytest -q -m "not real"
```

Os resultados completos são gerados localmente em `data/output/`. Incluem JSON, relatório HTML, CSV de métricas por categoria, matrizes e revisão por caso. Os hashes da base e dos arquivos relevantes permitem identificar a configuração do experimento; o modo mock é determinístico para os mesmos dados e código. A suíte verifica as fórmulas com exemplos conferíveis à mão, falhas no denominador, ausência de vazamento, associação por ID, preservação do ambiente e segurança das exportações.

O workflow foi preparado para executar os testes sem a marca `real` e as demonstrações no GitHub, em Python 3.10 e 3.12, com `LLM_MODO=mock` e `OCI_NAMESPACE` vazio. A existência do arquivo não significa que esses jobs já tenham executado no remoto. A seleção acima exclui os testes de serviços externos. A validação local foi realizada em Python 3.12.

## Encaminhamentos por dependência

| Evidência produzida | Uso pela equipe |
| --- | --- |
| Base, rubrica e CSV de revisão | Consultar a revisão individual concluída por Everson e registrar futuras correções ou uma segunda revisão opcional |
| Erros por ID e cenários separados | Avaliar o classificador real e discutir melhorias com Dados/IA, preservando comparação entre versões |
| Contratos e JSON de resultados | Integrar métricas à interface e ao armazenamento sem mudar `Analise` ou `RespostaProcessamento` |
| Índices de origem e justificativas | Apoiar uma futura curadoria com histórico de responsável, data e decisão |
| Indicadores descritivos | Apoiar apresentação do comportamento observado, sem alegações de retenção, crescimento ou saúde comprovada |

A avaliação real de Gemini, a integração ativa com OCI, o histórico operacional de aprovação editorial e o controle de acesso seguem como dependências das frentes responsáveis. A revisão individual documentada conclui a conferência das referências desta versão; não valida essas integrações nem demonstra generalização. Esses limites não são resolvidos por uma pontuação alta em exemplos sintéticos.
