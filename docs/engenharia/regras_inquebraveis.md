# Regras Inquebráveis (Guardrails de Engenharia)

Este documento define as restrições invioláveis para qualquer alteração na camada de ingestão, API, curadoria por IA e grafo de conhecimento do **Sender AI**.

## 1. Preservação de Contratos Oficiais
- O contrato definido em `app/schemas.py` (`Interacao`, `LoteEntrada`, `AnaliseInteracao`, `AtivosDistribuicao`, `RespostaProcessamento`) **jamais** pode sofrer alterações destrutivas.
- Os serviços do Tech Lead (Renato), Backend/OCI (Pedro), Banco de Dados/Supabase (Lucas) e Data Science (Matheus) dependem estritamente desses schemas.
- Campos novos opcionais só podem ser adicionados com valores padrão retrocompatíveis.

## 2. Determinismo e Cobertura de Testes
- Nenhuma funcionalidade vai para a branch sem cobertura correspondente na suíte `pytest`.
- Testes de integração em modo mock (`FORCAR_MODO_MOCK=true`) devem executar de forma 100% determinística e sem chamadas externas de rede.
- Os 3 testes originalmente marcados como `@pytest.mark.xfail` em `tests/test_integracao.py` devem passar nativamente sem gambiarras ou supressão de erros.

## 3. Resiliência na Ingestão de Dados (CSV & JSON)
- Arquivos exportados pelo Microsoft Excel em ambientes Windows pt-BR (delimitador `;` e codificação `Windows-1252` / `cp1252` ou `UTF-8-SIG` com BOM) devem ser aceitos de forma transparente.
- Erros de estrutura (colunas obrigatórias ausentes, lote vazio, JSON malformado) devem continuar lançando `ValueError` claro no adaptador e `HTTP 400` / `HTTP 422` na API.

## 4. Qualidade Editorial e Anti-Slop (Humanizer + Harness²)
- Os prompts enviados ao LLM nunca devem incentivar clichês artificiais ("No cenário atual...", "É importante destacar...", listas genéricas vazias).
- A curadoria deve se ater estritamente aos fatos presentes nas interações da comunidade (Zero Alucinação).

## 5. Grafo de Conhecimento Auditável (Graphify)
- Toda relação mapeada na comunidade deve distinguir explicitamente entre:
  - `EXTRACTED`: Fato direto extraído da interação (ex.: autor publicou no canal X com sentimento Y).
  - `INFERRED`: Conexão semântica deduzida (ex.: dois autores discutindo o mesmo tema técnico em canais distintos).
