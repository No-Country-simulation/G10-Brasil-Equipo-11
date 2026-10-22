# Roteiro de execução e verificação

Este roteiro leva qualquer pessoa do zero até o CommunityLab rodando, com um resultado esperado em cada etapa. Se o seu resultado for diferente do esperado, vá para [Problemas comuns](#7-problemas-comuns).

Responsável: Renato. Testado em modo simulado com Python 3.13 no Linux. A validação no Windows está em andamento.

## 1. Pré-requisitos

| Ferramenta | Versão | Onde baixar | Como conferir |
| --- | --- | --- | --- |
| Python | 3.10 ou mais novo | [python.org/downloads](https://www.python.org/downloads/) | `py --version` (Windows) ou `python3 --version` |
| Git | qualquer recente | [git-scm.com](https://git-scm.com/downloads) | `git --version` |

> **Windows:** na primeira tela do instalador do Python, marque **"Add python.exe to PATH"**. Sem isso, o terminal não reconhece o comando `python`.

Chaves do Gemini e da OCI **não são necessárias** para rodar e verificar o projeto. Sem elas, tudo funciona em modo simulado.

## 2. Verificação rápida: um comando

Baixe o projeto:

```powershell
git clone https://github.com/No-Country-simulation/G10-Brasil-Equipo-11.git
cd G10-Brasil-Equipo-11
git checkout data-scientist
```

Rode a verificação:

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File .\verificar.ps1
```

```bash
# Linux ou Mac
bash verificar.sh
```

Na primeira vez ele cria o ambiente virtual e instala as dependências, o que leva alguns minutos. **Resultado esperado:**

```text
[ OK ] Versão do Python — 3.x.x
[ OK ] Dependências instaladas
[ OK ] Arquivo .env — criado a partir do .env.example
[ OK ] Modo desta verificação — simulado (use --real para Gemini e OCI)
[ OK ] Testes automatizados — 33 passed, 2 deselected, 3 xfailed
[ OK ] API sobe e responde /saude — porta ..., modo_llm=mock
[ OK ] Processar lote de exemplo — 12 interações em 0.0 s; rotas: alerta=2, case_sucesso=3, faq=5, nenhuma=2
[ OK ] Pacote salvo — local: saida_local/ativos/2026-semana-04/pacote-distribuicao.json
[ OK ] Painel Streamlit inicia — porta ...

TUDO OK — relatório em saida_local/relatorio_verificacao.txt
```

Se alguma etapa falhar, o relatório em `saida_local/relatorio_verificacao.txt` mostra qual foi e por quê. Anexe esse arquivo ao pedir ajuda no grupo.

## 3. Passo a passo manual (Windows)

Use esta seção para entender cada etapa ou para rodar a API e o painel e usá-los de verdade. Todos os comandos são executados **na pasta raiz do projeto**.

| # | Comando | Resultado esperado |
| --- | --- | --- |
| 1 | `py -m venv .venv` | Aparece uma pasta `.venv`. Não imprime nada. |
| 2 | `.\.venv\Scripts\Activate.ps1` | O início da linha do terminal passa a mostrar `(.venv)`. |
| 3 | `python -m pip install -r requirements.txt` | Termina com `Successfully installed ...`. |
| 4 | `python -m pip install -e .` | Termina com `Successfully installed communitylab-0.1.0`. |
| 5 | `Copy-Item .env.example .env` | Aparece o arquivo `.env`. Não imprime nada. |
| 6 | `python -m pytest` | Última linha sem nenhum `failed`, por exemplo `33 passed, 2 skipped, 3 xfailed`. O total cresce conforme a equipe adiciona testes. |

> Use sempre `python -m pytest`, e não só `pytest`. A forma com `python -m` garante que os testes encontram a pasta `app`.

### Rodar a API

```powershell
python -m uvicorn app.main:app --reload
```

**Esperado:** `Uvicorn running on http://127.0.0.1:8000`. Deixe esse terminal aberto.

- Abra http://127.0.0.1:8000/saude no navegador. Deve aparecer `{"status":"ok","modo_llm":"mock"}`.
- Abra http://127.0.0.1:8000/docs para ver e testar os endpoints pelo navegador.

Para enviar o lote de exemplo, use **outro** terminal PowerShell, também com o `.venv` ativado:

```powershell
$lote = Get-Content data\interacoes_exemplo.json -Raw -Encoding UTF8
$r = Invoke-RestMethod -Uri http://127.0.0.1:8000/processar -Method Post `
       -ContentType "application/json; charset=utf-8" `
       -Body ([System.Text.Encoding]::UTF8.GetBytes($lote))
$r.resumo_comunidade
$r.armazenamento_oci
```

**Esperado:** `total_interacoes_processadas : 12` e `status : salvo_localmente`.

> O `GetBytes(...)` não é enfeite. Sem ele, o Windows PowerShell 5.1 envia o texto numa codificação antiga, e os acentos chegam corrompidos na API.

### Rodar o painel

Num terceiro terminal, com o `.venv` ativado:

```powershell
python -m streamlit run ui/painel.py
```

**Esperado:** o navegador abre em http://localhost:8501. Para conferir:

1. Na tela **Importar**, clique em **Usar lote de exemplo**. Deve aparecer "Pronto para processar" com **12** linhas lidas.
2. Clique em **Processar 12 interações**. O painel vai sozinho para **Visão geral**, com **12** interações e **2** membros que precisam de apoio.
3. Clique em **Revisar 7 ativos**. Na **Curadoria**, o botão **Aprovar post** fica bloqueado até você marcar a autorização do membro.
4. Marque a autorização, aprove o post e clique em **Exportar aprovados**. Deve aparecer "Salvo em `saida_local/ativos/.../aprovados.json`".

## 4. Modo real: Gemini e OCI

### Gemini

1. Gere uma chave em [Google AI Studio](https://aistudio.google.com/apikey).
2. No `.env`, preencha `GEMINI_API_KEY=` com a chave.
3. **Apague a linha `LLM_MODO=mock`.** Enquanto ela existir, o sistema continua simulado mesmo com a chave preenchida.
4. Reinicie a API e abra `/saude`. Deve aparecer `"modo_llm":"gemini"`.

### OCI Object Storage

Siga a seção de OCI do `README.md` para criar o bucket e o arquivo `~/.oci/config`. Depois, preencha `OCI_NAMESPACE` no `.env`.

### Verificar com os serviços reais

```powershell
powershell -ExecutionPolicy Bypass -File .\verificar.ps1 -Real
```

Ou só os testes:

```powershell
python -m pytest -m real -v
```

| Teste | O que confirma | Custo |
| --- | --- | --- |
| `test_gemini_real_respeita_contrato` | O Gemini devolve JSON no formato combinado e decide as rotas de FAQ e alerta corretamente | Cerca de 6 chamadas à API |
| `test_oci_real_salva_no_bucket` | O upload chega ao bucket | Cria `ativos/<ano>-semana-teste-integracao/` no bucket |

O modo `-Real` processa o lote de exemplo inteiro pelo Gemini. São cerca de 20 chamadas, o que pode esbarrar no limite do plano gratuito. Se aparecer erro `429`, espere um minuto e rode de novo.

## 5. Como ler o resultado dos testes

| Resultado | Significado | O que fazer |
| --- | --- | --- |
| `passed` | Funcionou | Nada |
| `failed` | Algo quebrou | Leia a mensagem e avise o responsável pela parte |
| `skipped` | Pulado de propósito, por exemplo um teste real sem chave | Nada, a não ser que você queira testar o modo real |
| `xfailed` | Limitação conhecida, que ainda falha como esperado | Nada. Veja a [seção 6](#6-limitações-conhecidas) |
| `XPASS` | Uma limitação conhecida **foi corrigida** | Apague o `@pytest.mark.xfail` desse teste em `tests/test_integracao.py`, para ele virar uma garantia permanente |

Para ver o nome de cada teste: `python -m pytest -v`. Para ver o motivo dos pulados e dos xfail: `python -m pytest -rxXs`.

## 6. Limitações conhecidas

| Limitação | Efeito para quem usa | Teste que acompanha | Responsável |
| --- | --- | --- | --- |
| A API só aceita JSON. O painel já aceita CSV (branch `frontend/painel-curadoria`) | Integrações que chamam a API direto precisam enviar JSON | `test_api_aceita_upload_de_csv` (xfail) | Marcelo |
| CSV com `;` não é aceito | O Excel em português salva assim por padrão em "CSV (separado por vírgulas)" | `test_csv_com_ponto_e_virgula_do_excel_ptbr` (xfail) | Marcelo |
| CSV em Windows-1252 não é aceito | Arquivos salvos por Excel antigo dão erro de codificação | `test_csv_em_windows_1252` (xfail) | Marcelo |
| O `.env.example` já vem com `LLM_MODO=mock` | Quem só colar a chave continua em modo simulado | `test_gemini_real_respeita_contrato` avisa no motivo do pulo | Todos |

**Para quem for gerar CSV no Excel hoje:** use *Arquivo → Salvar como → **CSV UTF-8 (delimitado por vírgulas)***. Esse formato já funciona.

## 7. Problemas comuns

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `python` ou `py` não é reconhecido | Python não está no PATH | Reinstale o Python marcando "Add python.exe to PATH" e abra um terminal novo |
| `Activate.ps1 não pode ser carregado porque a execução de scripts foi desabilitada` | Política de segurança do PowerShell | Rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` uma vez, ou use o `verificar.ps1`, que não precisa ativar o ambiente |
| `ModuleNotFoundError: No module named 'app'` | Comando rodado fora da pasta raiz, ou `pytest` sem `python -m` | Use `cd` até a pasta que tem `app` e `ui`, e rode `python -m pytest` |
| `ModuleNotFoundError: No module named 'communitylab'` | Faltou instalar o pacote local | `python -m pip install -e .` |
| `/saude` mostra `"modo_llm":"mock"` mesmo com a chave | A linha `LLM_MODO=mock` continua no `.env` | Apague a linha e reinicie a API |
| `[Errno 10048]` ou `address already in use` | Porta 8000 ou 8501 ocupada por outra execução | Feche o outro terminal ou use `--port 8001` |
| Erro `429` ou `RESOURCE_EXHAUSTED` | Limite do plano gratuito do Gemini | Espere um minuto. Durante o desenvolvimento, prefira o modo simulado |
| `armazenamento_oci.status` = `erro` | Namespace, bucket ou `~/.oci/config` incorretos | Veja `saida_local/log_api.txt`. O namespace aparece nos detalhes do bucket, e não é o nome da tenancy |
| Acentos aparecem como `Ã§` ou `?` no terminal | O terminal do Windows não está em UTF-8 | Rode `chcp 65001` antes. Os arquivos salvos ficam corretos mesmo assim |
| `UnicodeDecodeError` ao importar um CSV | CSV salvo em Windows-1252 | Salve de novo como "CSV UTF-8" (seção 6) |

## 8. O que os testes de integração cobrem

Arquivo: `tests/test_integracao.py`.

| Grupo | Verifica |
| --- | --- |
| Ponta a ponta | O lote de exemplo passa pela API, a resposta respeita o contrato, todos os tipos de ativo são gerados e o pacote salvo é igual à resposta |
| Roteamento | Depoimento → case, dúvida → FAQ, negativo → alerta, reclamação → alerta, neutro → nenhuma |
| Entradas inválidas | Lote vazio → 400; texto ausente, tipo inválido, autor ausente ou corpo que não é JSON → 422 |
| Codificação | Acentos, emojis e aspas curvas chegam iguais na resposta e no arquivo salvo |
| CSV | CSV UTF-8, CSV com BOM do Excel, colunas em inglês e coluna obrigatória faltando |
| Painel | Fica em `tests/test_painel.py`: importação, filtro, autorização do post e exportação, com cliques simulados |
| Serviços reais | Gemini e OCI, pulados sem credenciais |
