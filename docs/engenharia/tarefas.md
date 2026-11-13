# Plano de Tarefas & Critérios de Aceite (Definition of Done)

Responsável: **Marcelo Sales** (`devmarcelosales`)  
Branch: `marcelo/ingestao-csv-e-grafo`

---

## Fase 1: Ingestão Resiliente de CSV & Upload via API (Core)

- [x] **T1.1 — Auto-detecção de Delimitador e Codificação em `src/communitylab/adapter.py`**
  - **Critério de Aceite:** `carregar_lote()` lê arquivos CSV separados por `,`, `;` ou `\t`, tanto em `utf-8` / `utf-8-sig` quanto em `cp1252` (`windows-1252`), convertendo para `LoteEntrada` com acentuação preservada.
  - **Função Auxiliar:** `carregar_lote_bytes(conteudo: bytes, nome_arquivo: str, ...)` implementada e testada.

- [x] **T1.2 — Preservação de Compatibilidade com `ui/importacao.py`**
  - **Critério de Aceite:** Os testes do painel (`tests/test_painel.py`) continuam 100% verdes sem regressão.

- [x] **T1.3 — Suporte a Upload Multipart em `POST /processar` (`app/main.py`)**
  - **Critério de Aceite:** O endpoint `POST /processar` aceita tanto payload `application/json` (`LoteEntrada`) quanto `multipart/form-data` com campo `arquivo` (CSV ou JSON), retornando `200 OK` com `RespostaProcessamento` e mantendo os retornos `400` (lote vazio) e `422` (payload inválido).

- [x] **T1.4 — Promoção dos 3 Testes `xfail` em `tests/test_integracao.py`**
  - **Critério de Aceite:** Removido `@pytest.mark.xfail` de `test_csv_com_ponto_e_virgula_do_excel_ptbr`, `test_csv_em_windows_1252` e `test_api_aceita_upload_de_csv`, com todos passando (`PASSED`).

---

## Fase 2: Qualidade Editorial Anti-Slop & Guardrails (Humanizer + Harness²)

- [x] **T2.1 — Refinamento de Prompts em `app/prompts.py`**
  - **Critério de Aceite:** Incorporadas diretrizes Anti-Slop (`DIRETRIZES_ANTI_SLOP`) nos prompts de LinkedIn, Newsletter e FAQ, proibindo aberturas clichês, adjetivação vazia e invenção de dados.

- [x] **T2.2 — Guardrail de Higienização Editorial e Fidelidade (`app/ia.py`)**
  - **Critério de Aceite:** Funções `higienizar_texto_editorial` e `validar_ancoragem_factual` implementadas e cobertas por testes automatizados.

---

## Fase 3: Grafo de Conhecimento da Comunidade (Graphify)

- [x] **T3.1 — Implementação de `src/communitylab/grafo_comunidade.py`**
  - **Critério de Aceite:** Grafo determinístico da comunidade mapeando nós (`membro`, `canal`, `categoria`, `topico`) e arestas classificadas em `EXTRACTED` (interação direta) e `INFERRED` (afinidade temática entre membros/canais), exportando hubs e diagrama Mermaid.

- [x] **T3.2 — Testes Unitários em `tests/test_grafo_comunidade.py`**
  - **Critério de Aceite:** 6 novos testes automatizados validando construção do grafo, classificação de arestas (`EXTRACTED` vs `INFERRED`), detecção de hubs, higienização anti-slop e leitura de CSV em `cp1252` + `;`.

---

## Fase 4: Documentação e Entrega

- [x] **T4.1 — Atualização de `docs/EXECUCAO.md`**
  - **Critério de Aceite:** Tabela de limitações conhecidas atualizada documentando a resolução dos 3 itens de CSV e a cobertura de testes expandida.
- [x] **T4.2 — Execução Completa da Suíte de Testes**
  - **Critério de Aceite:** `56 passed, 9 skipped in 2.62s` (Zero falhas, zero xfail).
