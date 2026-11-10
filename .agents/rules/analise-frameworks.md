---
trigger: always_on
description: Diretrizes de engenharia dos frameworks da pasta analise.
---

# Diretrizes dos Frameworks de Análise (Workspace Local)

1. **Padrões de Engenharia Obrigatórios:**
   - **Ponytail:** Minimalismo pragmático, zero código especulativo, componentes < 100 linhas, asserções verificáveis.
   - **EGM (Elephant-Goldfish):** Abordagem Artifact-First (planos densos em arquivos, chat conciso), revisão de contexto zero.
   - **Humanizer:** Textos e copies em português natural, sem clichês sintéticos de IA ("não apenas X, mas Y", falsa profundidade).
   - **Harness² & E2E:** Validação empírica contínua via suíte completa de testes (`verificar.py` / `pytest`).
   - **Graphify:** Relações e telemetria comunitária modeladas em grafo.
2. Para procedimentos detalhados e referências, consulte a skill `analise-frameworks`.
