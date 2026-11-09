---
name: analise-frameworks
description: >-
  Síntese metodológica dos 6 frameworks de engenharia da pasta analise
  (Elephant-Goldfish, Harness², Humanizer, Ponytail, Graphify, E2E),
  ignorando estritamente a subpasta UI. Use para guiar arquitetura, refatoração e testes no workspace.
---

# Frameworks de Engenharia Consolidada (Pasta 'analise')

Esta skill consolida os padrões de engenharia extraídos dos repositórios de referência do projeto (`analise/`), ignorando a subpasta `UI`.

## 1. Ponytail (Minimalismo Sênior)
- **Lema:** *"He says nothing. He writes one line. It works."*
- **Regras:**
  - Proibição de dependências desnecessárias ou build tools pesadas quando Vanilla resolver melhor.
  - Componentes estritamente modulares e curtos (< 100 linhas).
  - Nunca escrever 100 linhas onde 10 linhas sólidas resolvem com maior robustez.
  - Toda lógica não trivial deve conter asserções e testes associados.

## 2. Elephant-Goldfish Model (EGM)
- **Lema:** *"Design with an elephant. Review with a goldfish."*
- **Regras:**
  - **Artifact-First:** Especificações, planos e relatórios densos devem ser gravados em artefatos markdown, mantendo as respostas do chat compactas e objetivas.
  - **Revisão Contexto-Zero:** Validar o produto final a partir de testes isolados e ambientes limpos (como portas efêmeras e instâncias independentes).
  - **Anti-Sycophancy:** Foco em evidências reais de código e testes, sem bajulação ou suposições infundadas.

## 3. Humanizer (Comunicação Autêntica)
- **Regras:**
  - Neutralizar os 26 vícios de escrita sintética de IA.
  - Evitar aberturas ensaiadas ("No cerne de...", "Pense nisso..."), contrastes formulaicos e rótulos desnecessários em negrito.
  - Garantir voz humana, executiva e direta em português brasileiro nos conteúdos editoriais (LinkedIn, Newsletter, FAQ).

## 4. Harness² & E2E (Harnessing Recursivo e Testes)
- **Regras:**
  - Propose–Probe–Compose: testar hipóteses diretamente contra a suíte de testes.
  - Todo endpoint deve possuir teste automatizado associado.
  - Manter 100% de taxa de sucesso no `pytest` e `verificar.py`.
  - Loops de reflexão: persistir lições aprendidas em handoffs e documentação.

## 5. Graphify (Inteligência em Grafos)
- **Regras:**
  - Extração de entidades, conexões e fluxos de interação comunitária modelados em grafos de relacionamento.
  - Métricas de centralidade, tópicos recorrentes e telemetria de comunidades.
