# Roteiro de execução e verificação

Este roteiro leva qualquer pessoa do zero até o Sender AI rodando, com um resultado esperado em cada etapa. Se o seu resultado for diferente do esperado, vá para [Problemas comuns](#7-problemas-comuns).

Responsável: Renato. Testado em modo simulado com Python 3.13 no Linux e Windows.

A interface oficial é o **site**, servido pelo próprio FastAPI em http://127.0.0.1:8000. O painel Streamlit continua no projeto como alternativa.

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
[ OK ] Testes automatizados — 338 passed, 14 deselected
[ OK ] API sobe e responde /saude — porta ..., modo_llm=mock
[ OK ] Site abre — http://127.0.0.1:.../
[ OK ] Login protege a API — /processar sem login respondeu 401
[ OK ] Login do site — usuário 'admin' entrou
[ OK ] Processar lote de exemplo — 12 interações em 0.0 s; rotas: alerta=2, case_sucesso=3, faq=5, nenhuma=2
[ OK ] Pacote salvo — local: saida_local/ativos/2026-semana-04/pacote-distribuicao.json
[ OK ] Painel Streamlit (alternativo) inicia — porta ...

TUDO OK — relatório em saida_local/relatorio_verificacao.txt
```

O número de testes cresce conforme a equipe adiciona novos. O que importa é não aparecer `failed`.

| Etapa | O que confere |
| --- | --- |
| Site abre | A página inicial e os scripts do site carregam |
| Login protege a API | Sem login, a API recusa processar um lote (HTTP 401) |
| Login do site | O usuário e a senha do `.env` são aceitos pelo servidor |

Se aparecer **`[AVISO] Login do site — ADMIN_USUARIO ou ADMIN_SENHA vazio`**, o site está abrindo sem pedir senha. Funciona para desenvolver, mas preencha os dois no `.env` antes de qualquer apresentação.

Se alguma etapa falhar, o relatório em `saida_local/relatorio_verificacao.txt` mostra qual foi e por quê. Anexe esse arquivo ao pedir ajuda no grupo.

## 3. Passo a passo manual (Windows)

Use esta seção para entender cada etapa ou para rodar o site e usá-lo de verdade. Todos os comandos são executados **na pasta raiz do projeto**.

| # | Comando | Resultado esperado |
| --- | --- | --- |
| 1 | `py -m venv .venv` | Aparece uma pasta `.venv`. Não imprime nada. |
| 2 | `.\.venv\Scripts\Activate.ps1` | O início da linha do terminal passa a mostrar `(.venv)`. |
| 3 | `python -m pip install -r requirements.txt` | Termina com `Successfully installed ...`. |
| 4 | `python -m pip install -e .` | Termina com `Successfully installed communitylab-0.1.0`. |
| 5 | `Copy-Item .env.example .env` | Aparece o arquivo `.env`. Não imprime nada. |
| 6 | `notepad .env` | Confira `ADMIN_USUARIO` e `ADMIN_SENHA`. O `.env.example` traz `admin` e `admin123`; troque a senha se o site for ficar acessível para outras pessoas. |
| 7 | `python -m pytest` | Última linha sem nenhum `failed`, por exemplo `338 passed, 14 skipped`. O total cresce conforme a equipe adiciona testes. |

> Use sempre `python -m pytest`, e não só `pytest`. A forma com `python -m` garante que os testes encontram a pasta `app`.

### Abrir o site (interface oficial)

O jeito mais simples, no Windows: dê dois cliques em **`iniciar_web_vanilla.bat`**, na pasta do projeto. Ele libera a porta 8000 se estiver ocupada, inicia o servidor e abre o navegador sozinho. Para parar, use `encerrar_web_vanilla.bat` ou feche a janela preta.

Pelo terminal, com o `.venv` ativado:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Esperado:** `Uvicorn running on http://127.0.0.1:8000`. Deixe esse terminal aberto e acesse http://127.0.0.1:8000 no navegador.

> O servidor lê o `.env` só quando inicia. Se mudar a senha ou a chave do Gemini, pare (`Ctrl+C`) e inicie de novo.

Para conferir o fluxo completo:

1. Na página inicial, clique em **Entrar** (canto superior direito) e use o usuário e a senha do `.env`. Você cai na tela **Importar**.
2. Clique em **Lote de exemplo (12 msgs)**. Aparece o botão **Processar 12 interações**. Clique nele.
3. O site vai sozinho para **Visão geral**: 12 interações, rotas FAQ 5, Case de sucesso 3, Alerta 2 e Sem ação 2, e **2** membros que precisam de apoio.
4. Clique em **Revisar 7 ativos**. Na **Curadoria**, o botão **Aprovar post** fica bloqueado até você marcar a caixa de autorização do membro.
5. Marque a autorização, clique em **Aprovar post** e depois em **Exportar aprovados**. Deve aparecer "Salvo em `...saida_local/ativos/<ano>-<mês>/aprovados.json`".
6. Clique em **Sair**. Você volta para a página inicial, e as telas internas só abrem depois de entrar de novo.

No topo da tela aparecem a fonte, o canal e o mês do lote, o número de ativos pendentes e o selo **Modo simulado** (ou Gemini). O botão ☾ troca entre os temas claro e escuro.

### Usar a API direto

Com o servidor rodando, http://127.0.0.1:8000/saude deve mostrar `{"status":"ok","modo_llm":"mock"}`, e http://127.0.0.1:8000/docs lista os endpoints.

`/processar` exige login. Para enviar o lote de exemplo pelo PowerShell, em **outro** terminal com o `.venv` ativado, entre primeiro e depois mande o lote com o token (troque `admin123` pela senha do seu `.env`):

```powershell
$login = @{ usuario = "admin"; senha = "admin123" } | ConvertTo-Json
$token = (Invoke-RestMethod -Uri http://127.0.0.1:8000/api/auth/login -Method Post `
           -ContentType "application/json" -Body $login).token

$lote = Get-Content data\interacoes_exemplo.json -Raw -Encoding UTF8
$r = Invoke-RestMethod -Uri http://127.0.0.1:8000/processar -Method Post `
       -Headers @{ "X-Sender-Token" = $token } `
       -ContentType "application/json; charset=utf-8" `
       -Body ([System.Text.Encoding]::UTF8.GetBytes($lote))
$r.resumo_comunidade
$r.armazenamento_oci
```

**Esperado:** `total_interacoes_processadas : 12` e `status : salvo_localmente`. Sem o token, a resposta é `401 Acesso restrito`.

> O `GetBytes(...)` não é enfeite. Sem ele, o Windows PowerShell 5.1 envia o texto numa codificação antiga, e os acentos chegam corrompidos na API.

### Painel Streamlit (alternativo)

```powershell
python -m streamlit run ui/painel.py
```

Abre em http://localhost:8501 com o mesmo login e as mesmas telas (Importar, Visão geral, Curadoria e Insights). No Windows também dá para usar `iniciar_streamlit.bat`.

## 4. Modo real: Gemini e OCI

### Gemini

1. Gere uma chave em [Google AI Studio](https://aistudio.google.com/apikey).
2. No `.env`, preencha `GEMINI_API_KEY=` com a chave.
3. **Apague a linha `LLM_MODO=mock`.** Enquanto ela existir, o sistema continua simulado mesmo com a chave preenchida.
4. Reinicie a API e abra `/saude`. Deve aparecer `"modo_llm":"gemini"`.

### OCI Object Storage

Siga a seção de OCI do `README.md` para criar o bucket e o arquivo `~/.oci/config`. Depois, preencha `OCI_NAMESPACE` no `.env`.

### Supabase

Opcional. Guarda os lotes processados e liga a aba **Insights** do site.

1. Crie um projeto no Supabase.
2. Abra o **SQL Editor**, cole `supabase/migrations/20261027000000_inicial.sql` e execute (ou use `supabase db push`).
3. Copie a string do **Session pooler** (a conexão direta só funciona por IPv6) para `DATABASE_URL` no `.env`.
4. Reinicie o servidor do site.

**O que muda:** os lotes processados ficam no histórico, as decisões da curadoria e o status dos alertas ("Marcar como resolvido") são gravados, e a aba **Insights** mostra o histórico dia a dia (simulado e Gemini nunca se misturam). Sem `DATABASE_URL`, o resto funciona igual e o Insights avisa que precisa do banco. Se o banco falhar, o processamento continua e o log mostra `[Supabase]`.

O painel Streamlit tem um recurso a mais: ao importar um conteúdo já processado, ele pergunta se você quer **Abrir resultado existente** ou **Processar de novo e substituir**. O site não tem essa pergunta.

**Segurança:** RLS ligado e sem policies; a chave pública (anon) do Supabase não lê nenhum dado. Use apenas dados fictícios.

**Local:** um Supabase local (Supabase CLI / Docker) também serve. Use `postgresql://postgres:postgres@127.0.0.1:54322/postgres` (ou um banco separado) em `DATABASE_URL` e aplique a migração com `psql` ou pelo SQL Editor do Studio local.

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
| Testes do Supabase (`DATABASE_URL` configurada) | Gravação, leitura, substituição de lotes e o painel com banco | Cria e apaga dados com nomes `Teste_Repositorio_*` e `Teste_Painel_*` |

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

## 6. Limitações conhecidas e Resoluções

| Item | Status / Efeito | Teste que garante | Responsável |
| --- | --- | --- | --- |
| Upload de CSV direto na API (`POST /processar`) | **Resolvido:** A API agora aceita tanto JSON quanto upload multipart (`arquivo`) | `test_api_aceita_upload_de_csv` (`passed`) | Marcelo |
| CSV com `;` (Excel em português) | **Resolvido:** O adaptador detecta automaticamente `;`, `,` ou `\t` | `test_csv_com_ponto_e_virgula_do_excel_ptbr` (`passed`) | Marcelo |
| CSV em Windows-1252 (`cp1252`) | **Resolvido:** O adaptador decodifica UTF-8, UTF-8-BOM e Windows-1252 | `test_csv_em_windows_1252` (`passed`) | Marcelo |
| O `.env.example` já vem com `LLM_MODO=mock` | Quem só colar a chave continua em modo simulado | `test_gemini_real_respeita_contrato` avisa no motivo do pulo | Todos |

## 7. Problemas comuns

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `python` ou `py` não é reconhecido | Python não está no PATH | Reinstale o Python marcando "Add python.exe to PATH" e abra um terminal novo |
| `Activate.ps1 não pode ser carregado porque a execução de scripts foi desabilitada` | Política de segurança do PowerShell | Rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` uma vez, ou use o `verificar.ps1`, que não precisa ativar o ambiente |
| `ModuleNotFoundError: No module named 'app'` | Comando rodado fora da pasta raiz, ou `pytest` sem `python -m` | Use `cd` até a pasta que tem `app` e `ui`, e rode `python -m pytest` |
| `ModuleNotFoundError: No module named 'communitylab'` | Faltou instalar o pacote local | `python -m pip install -e .` |
| `/saude` mostra `"modo_llm":"mock"` mesmo com a chave | A linha `LLM_MODO=mock` continua no `.env` | Apague a linha e reinicie o servidor |
| O site não aceita o usuário e a senha | O servidor foi iniciado antes de você mudar o `.env`, ou há uma variável de ambiente `ADMIN_SENHA` com outro valor | Reinicie o servidor. O `verificar.ps1` mostra `[FALHOU] Login do site` nesse caso |
| `401 Acesso restrito. Faça login administrativo` | Chamada à API sem login, ou o servidor reiniciou e a sessão foi perdida | No site, entre de novo. Na API, pegue um token novo em `/api/auth/login` (seção 3) |
| O site abre direto, sem pedir senha | `ADMIN_USUARIO` ou `ADMIN_SENHA` vazio no `.env` | Preencha os dois e reinicie o servidor |
| `[Errno 10048]` ou `address already in use` | Porta 8000 ou 8501 ocupada por outra execução | Use `iniciar_web_vanilla.bat`, que libera a porta 8000, ou feche o outro terminal, ou use `--port 8001` |
| Erro `429` ou `RESOURCE_EXHAUSTED` | Limite do plano gratuito do Gemini | Espere um minuto. Durante o desenvolvimento, prefira o modo simulado |
| `armazenamento_oci.status` = `erro` | Namespace, bucket ou `~/.oci/config` incorretos | Veja `saida_local/log_api.txt`. O namespace aparece nos detalhes do bucket, e não é o nome da tenancy |
| Acentos aparecem como `Ã§` ou `?` no terminal | O terminal do Windows não está em UTF-8 | Rode `chcp 65001` antes. Os arquivos salvos ficam corretos mesmo assim |
| `UnicodeDecodeError` ao importar um CSV | CSV salvo em Windows-1252 | O adaptador (`communitylab.adapter`) já converte automaticamente; ao salvar no Excel, prefira "CSV UTF-8" |

## 8. O que os testes de integração cobrem

Arquivo: `tests/test_integracao.py` e `tests/test_grafo_comunidade.py`.

| Grupo | Verifica |
| --- | --- |
| Ponta a ponta | O lote de exemplo passa pela API, a resposta respeita o contrato, todos os tipos de ativo são gerados e o pacote salvo é igual à resposta |
| Roteamento | Depoimento → case, dúvida → FAQ, negativo → alerta, reclamação → alerta, neutro → nenhuma |
| Entradas inválidas | Lote vazio → 400; texto ausente, tipo inválido, autor ausente ou corpo que não é JSON → 422 |
| Codificação | Acentos, emojis e aspas curvas chegam iguais na resposta e no arquivo salvo |
| CSV | CSV UTF-8, CSV com BOM do Excel, CSV com `;` (Excel pt-BR), CSV em Windows-1252 (`cp1252`), upload multipart na API, colunas em inglês e coluna obrigatória faltando |
| Grafo & Anti-Slop | Mapeamento de nós e arestas (`EXTRACTED` e `INFERRED`) da comunidade e higienização editorial contra clichês de IA (`tests/test_grafo_comunidade.py`) |
| Site | Fica em `tests/test_web_vanilla.py`: arquivos do site, login e logout, rotas bloqueadas sem login, exportação recusando caminho malicioso e post sem autorização do membro |
| Painel Streamlit | Fica em `tests/test_painel.py`: importação, filtro, autorização do post e exportação, com cliques simulados |
| Serviços reais | Gemini e OCI, pulados sem credenciais |
