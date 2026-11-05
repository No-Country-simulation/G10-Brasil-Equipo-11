# Registro de Falhas, Diagnósticos e Lições Aprendidas

Este documento segue o padrão de memória operacional (`harness2` / `ponytail`) para garantir que todo obstáculo técnico encontrado seja diagnosticado na causa raiz e nunca volte a ocorrer.

---

## F001 — Delimitador `;` em CSVs gerados pelo Excel em Português (Windows pt-BR)
- **Sintoma:** Quando o usuário salva uma planilha como "CSV (separado por vírgulas)" no Excel configurado em português do Brasil, o separador real emitido é `;` (ponto e vírgula) porque a vírgula é reservada para casas decimais. O `csv.DictReader` padrão (que espera `,`) lê o cabeçalho inteiro como uma única coluna `"autor;canal;tipo;texto"`, falhando na validação de campos obrigatórios.
- **Causa Raiz:** Ausência de inspeção do cabeçalho/delimitador antes de instanciar o `csv.DictReader` em `src/communitylab/adapter.py` e bloqueio preventivo rígido em `ui/importacao.py`.
- **Solução Aplicada:** Implementação de detecção determinística de delimitador (`_detectar_delimitador`) que analisa a linha de cabeçalho para identificar `;`, `,` ou `\t`, combinada com `csv.Sniffer` como fallback.

---

## F002 — Codificação `Windows-1252` (`cp1252`) em CSVs do Excel Legado
- **Sintoma:** Arquivos CSV exportados em versões clássicas do Excel no Windows utilizam codificação `cp1252` (ANSI/Windows-1252). Ao tentar abrir exclusivamente com `encoding="utf-8-sig"`, ocorre `UnicodeDecodeError` em palavras acentuadas (ex.: `"júnior"`, `"dúvidas"`, `"Ação"`).
- **Causa Raiz:** Leitura acoplada a uma única codificação fixa (`utf-8-sig`) sem fallback para `cp1252` / `latin-1`.
- **Solução Aplicada:** Implementação do decodificador resiliente `_decodificar_bytes()` que tenta `utf-8-sig` (suportando UTF-8 puro e UTF-8 com BOM) e faz fallback seguro para `cp1252`, preservando 100% dos caracteres acentuados da língua portuguesa.

---

## F003 — Upload de Arquivo CSV no Endpoint `POST /processar`
- **Sintoma:** O endpoint `POST /processar` em `app/main.py` aceitava apenas corpo JSON (`LoteEntrada`), retornando `422 Unprocessable Entity` ao receber upload de arquivo via `multipart/form-data` (`files={"arquivo": ...}`).
- **Causa Raiz:** O adaptador de arquivos (`communitylab.adapter`) não estava conectado à camada HTTP da API FastAPI, e `python-multipart` não constava em `requirements.txt`.
- **Solução Aplicada:** Atualização de `POST /processar` para inspecionar o `Content-Type` da requisição: requisições `application/json` continuam validadas via `LoteEntrada`, enquanto requisições `multipart/form-data` extraem o arquivo enviado, convertem via `carregar_lote_bytes()` e executam o pipeline completo. Adicionado `python-multipart` ao `requirements.txt`.
