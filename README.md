# CommunityLab Intelligence

Sistema de inteligência artificial para analisar interações em comunidades digitais, identificar assuntos relevantes e gerar conteúdos que apoiem o engajamento e a distribuição de informações.

O projeto está em desenvolvimento e possui uma implementação funcional em modo simulado (*mock*).

## Objetivos do MVP

* Receber lotes de interações em JSON.
* Importar e adaptar dados de diferentes formatos, incluindo CSV e JSON.
* Classificar interações por sentimento, tema, relevância e rota.
* Identificar oportunidades de conteúdo e situações que precisam de atenção.
* Gerar sugestões de publicações, newsletters e FAQs.
* Disponibilizar uma interface de curadoria para revisão humana.
* Persistir os resultados localmente ou, mediante configuração, na Oracle Cloud Infrastructure (OCI).

## Tecnologias

* Python
* FastAPI
* LangGraph
* Pydantic
* Streamlit
* Pandas
* Google GenAI
* Oracle Cloud Infrastructure SDK
* Pytest

## Estrutura do projeto

```text
communityLab/
├── app/
│   ├── grafo.py
│   ├── ia.py
│   ├── llm.py
│   ├── main.py
│   ├── prompts.py
│   ├── repositorio.py
│   ├── schemas.py
│   └── storage.py
├── data/
│   └── interacoes_exemplo.json
├── supabase/
│   └── migrations/
├── src/
│   └── communitylab/
│       ├── adapter.py
│       └── ingestion.py
├── tests/
│   ├── test_adapter.py
│   ├── test_ingestion.py
│   └── test_pipeline.py
├── ui/
│   ├── insights.py
│   ├── painel.py
│   └── tela_insights.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## Requisitos

* Python 3.10 ou superior.
* Git.
* Acesso ao terminal.
* Uma chave Gemini somente se for utilizar o modelo real.
* Configuração OCI somente se for utilizar o armazenamento em nuvem.

As dependências e versões disponíveis podem variar conforme o ambiente.

## Instalação

Clone o repositório e acesse a pasta do projeto:

```bash
git clone https://github.com/No-Country-simulation/G10-Brasil-Equipo-11.git
cd G10-Brasil-Equipo-11
```

Crie e ative um ambiente virtual.

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
python -m pip install -r requirements.txt
```

Crie uma configuração local a partir do arquivo de exemplo:

```powershell
Copy-Item .env.example .env
```

O modo simulado é a configuração inicial recomendada para executar o projeto sem credenciais externas.

## Executando a API

Na raiz do projeto:

```powershell
python -m uvicorn app.main:app --reload
```

Verifique o estado da aplicação:

```text
GET http://127.0.0.1:8000/saude
```

A API disponibiliza o endpoint `POST /processar` para receber um lote de interações.

O endpoint `GET /` não está implementado nesta versão.

## Executando o painel

Em outro terminal, com o ambiente virtual ativado:

```powershell
python -m streamlit run ui/painel.py
```

O painel abre em http://localhost:8501 e tem três telas:

| Tela | O que faz |
| --- | --- |
| **Importar** | Recebe um JSON ou CSV (colunas `autor`, `canal`, `tipo`, `texto`), mostra as primeiras linhas e explica como corrigir CSV do Excel com ponto e vírgula ou codificação antiga |
| **Visão geral** | Indicadores, sentimento, rotas, membros que precisam de apoio e tabela de interações com filtro por rota |
| **Curadoria** | Edição, aprovação e descarte do post, da newsletter e das dicas de FAQ. O post só é aprovado com a autorização do membro marcada. Os aprovados são exportados para `saida_local/ativos/<ano>-semana-XX/aprovados.json` |

Código do painel: `ui/painel.py` (telas), `ui/importacao.py` (leitura de arquivos), `ui/curadoria.py` (regras de aprovação e exportação) e `ui/estilo.py` (visual). Os testes ficam em `tests/test_painel.py`.

## Executando os testes

Na raiz do projeto:

```powershell
python -m pytest -v
```

Execute os testes no seu ambiente para confirmar o estado atual (os marcados como `real` são pulados sem credenciais).

## Modos de operação

### Modo simulado

Permite executar o fluxo sem uma chave Gemini. As respostas são produzidas pelas regras implementadas para simulação e não devem ser interpretadas como resultados de um modelo de linguagem real.

### Gemini

O uso do modelo real depende da configuração de `GEMINI_API_KEY` e das demais variáveis documentadas em `.env.example`.

### Armazenamento

O sistema pode salvar os resultados localmente ou utilizar o OCI Object Storage quando configurado. A integração real com a nuvem deve ser validada separadamente.

### Supabase

Opcional. Com um banco Postgres do Supabase, os lotes processados ficam guardados e o painel ganha histórico e a aba **Insights**.

1. Crie um projeto no Supabase.
2. Abra o **SQL Editor**, cole o conteúdo de `supabase/migrations/20261027000000_inicial.sql` e execute (ou use `supabase db push`).
3. Copie a string do **Session pooler** (a conexão direta só funciona por IPv6) para `DATABASE_URL` no `.env`.

O que muda no painel:

* Os lotes processados ficam no histórico.
* Se o mesmo conteúdo (comunidade e interações) for processado de novo no mesmo modo (simulado ou Gemini), o painel avisa e oferece **Abrir resultado existente** ou **Processar de novo e substituir**. A API `/processar` substitui o lote em silêncio.
* As decisões da curadoria e o status dos alertas são lembrados.
* A aba **Insights** agrega os lotes salvos. Lotes simulados e Gemini nunca se misturam, e a aba começa no Gemini.

Sem `DATABASE_URL`, nada muda. Se o banco falhar, o processamento continua: o painel mostra um aviso e o log registra `[Supabase]`. O tempo limite de conexão é de 5 segundos.

**Segurança:** o RLS fica ligado e sem policies, então a chave pública (anon) do Supabase não lê nenhum dado. O acesso é só pela `DATABASE_URL`. Use apenas dados fictícios.

**Desenvolvimento local:** um Supabase local (Supabase CLI / Docker) também serve. Aponte `DATABASE_URL` para o Postgres dele (padrão `postgresql://postgres:postgres@127.0.0.1:54322/postgres`, ou um banco separado) e aplique a migração com `psql` ou pelo SQL Editor do Studio local.

**Testes:** `python -m pytest -m real -v` agora também testa o banco e cria/apaga dados de teste com nomes `Teste_Repositorio_*` e `Teste_Painel_*`.

## Responsabilidade e revisão humana

Os conteúdos gerados são sugestões e não devem ser publicados automaticamente sem revisão humana.

É necessário ter cuidado especial com relatos pessoais, nomes, informações identificáveis e situações que possam expor membros da comunidade.

A quantidade de interações processadas não deve ser confundida com a quantidade de pessoas únicas.

Classificações de sentimento e relevância representam dimensões diferentes e devem ser avaliadas separadamente.

## Estado do projeto

MVP em desenvolvimento.

A ingestão, os adaptadores, o pipeline e os testes automatizados possuem implementação. A integração com serviços externos e a validação de qualidade das classificações ainda exigem verificações específicas.

## Contribuição

Antes de contribuir:

1. Atualize sua branch de trabalho.
2. Crie ou utilize a branch correspondente à sua responsabilidade.
3. Execute os testes automatizados.
4. Não publique arquivos `.env`, credenciais, ambientes virtuais, caches ou resultados locais.
5. Documente alterações de comportamento e limitações conhecidas.

Consulte a equipe antes de alterar interfaces, contratos de dados ou módulos compartilhados.
