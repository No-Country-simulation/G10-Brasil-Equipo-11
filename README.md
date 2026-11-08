# Sender AI

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
CommunityLab/
├── .github/workflows/tests.yml
├── .streamlit/config.toml
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
│   ├── avaliacao_classificacoes.json
│   ├── interacoes_exemplo.json
│   └── interacoes_outubro_2026.json   # 54 mensagens fictícias de outubro, para a demo dos Insights
├── docs/
│   ├── EXECUCAO.md
│   ├── analise_resultados.md
│   ├── avaliacao_classificacoes.md
│   ├── criterios_qualidade.md
│   └── indicadores_comunidade.md
├── scripts/
│   ├── analisar_comunidade.py
│   └── avaliar_classificacoes.py
├── supabase/
│   └── migrations/
├── src/
│   └── communitylab/
│       ├── adapter.py
│       ├── avaliacao.py
│       ├── ingestion.py
│       ├── radar.py
│       └── relatorio_avaliacao.py
├── tests/
│   ├── test_adapter.py
│   ├── test_avaliacao.py
│   ├── test_ingestion.py
│   ├── test_integracao.py
│   ├── test_painel.py
│   ├── test_pipeline.py
│   └── test_radar.py
├── ui/
│   ├── curadoria.py
│   ├── estilo.py
│   ├── importacao.py
│   ├── insights.py
│   ├── painel.py
│   └── tela_insights.py
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── verificar.py
├── verificar.ps1
└── verificar.sh
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

O painel abre em http://localhost:8501 com uma tela de login. Há um único usuário, o admin, definido no `.env` por `ADMIN_USUARIO` e `ADMIN_SENHA` (o `.env.example` traz `admin` / `admin123`). É uma trava de demonstração: a senha fica em texto no `.env`, recarregar a página (F5) pede o login de novo e o botão **Sair** do cabeçalho volta para o login com o painel zerado.

Depois de entrar, são quatro telas:

| Tela | O que faz |
| --- | --- |
| **Importar** | Recebe um JSON ou CSV (colunas `autor`, `canal`, `tipo`, `texto` e, opcional, `data`), mostra as primeiras linhas e explica como corrigir CSV do Excel com ponto e vírgula ou codificação antiga. Antes de processar, escolha a **fonte dos dados** (Discord, Telegram, WhatsApp ou Arquivo manual), o **canal** dessa fonte e o **mês de referência**. O lote é salvo como `<fonte> · <canal>` e o pacote vai para `ativos/<ano>-<mês>/` |
| **Visão geral** | Indicadores, sentimento, rotas, membros que precisam de apoio e tabela de interações com filtro por rota |
| **Curadoria** | Edição, aprovação e descarte do post, da newsletter e das dicas de FAQ. O post só é aprovado com a autorização do membro marcada. Os aprovados são exportados para `saida_local/ativos/<ano>-<mês>/aprovados.json` |
| **Insights** | Histórico dia a dia das mensagens guardadas no Supabase (veja a seção Supabase) |

A `data` de cada mensagem é o dia em que ela foi escrita, no formato `2026-10-05` ou `05/10/2026`. Sem ela, vale o dia da importação.

Os canais de cada fonte são fictícios, para demonstração, e ficam em `ui/fontes.py`. A origem e o período que vierem dentro do arquivo são ignorados pelo painel; valem os escolhidos na tela.

Código do painel: `ui/painel.py` (telas), `ui/login.py` (login), `ui/fontes.py` (fontes e canais), `ui/importacao.py` (leitura de arquivos), `ui/curadoria.py` (regras de aprovação e exportação) e `ui/estilo.py` (visual). Os testes ficam em `tests/test_painel.py`.

## Executando os testes

Na raiz do projeto:

```powershell
python -m pytest -v -m "not real"
```

A suíte cobre ingestão, adaptadores, pipeline, painel e avaliação de classificações. A seleção `-m "not real"` exclui os testes de serviços externos, que exigem configuração e validação próprias. Execute a suíte no seu ambiente para confirmar o estado atual. O workflow foi preparado para executar essa seleção e gerar os relatórios em modo simulado; sua configuração não comprova uma execução remota.

## Avaliação das classificações

A frente de Análise de Dados acrescenta uma base de 60 mensagens sintéticas com referências justificadas, critérios de qualidade e avaliação reproduzível, preservando os contratos do pipeline.

```powershell
python scripts/avaliar_classificacoes.py
python scripts/avaliar_classificacoes.py --cenario tipo_informado
```

Abra `data/output/avaliacao/mock_tipo_oculto/relatorio.html` no navegador. O relatório apresenta precisão, recall e F1 por categoria, matrizes de confusão, relevância por faixa, distribuição da amostra e casos para inspeção. JSON e CSVs ficam na mesma pasta.

O cenário principal oculta o tipo anotado para evitar vazamento da referência. O segundo cenário mede o fluxo com tipo informado. Everson concluiu a revisão individual das propostas em 24/10/2026: os 60 casos, suas classificações, justificativas e os critérios foram aceitos sem alterações. A base 1.1.0 registra essa revisão; as metas da avaliação também foram aprovadas pelo responsável pela frente analítica. Essa conferência não equivale a dupla anotação independente nem a aprovação de toda a equipe. Resultados mock não medem o desempenho do Gemini nem impacto em uma comunidade real.

Consulte a [documentação da avaliação](docs/avaliacao_classificacoes.md), os [critérios de qualidade](docs/criterios_qualidade.md) e a [análise dos resultados](docs/analise_resultados.md).

## Radar analítico da comunidade

```powershell
python scripts/analisar_comunidade.py --demonstracao
```

Abra `data/output/radar/radar.html` para conferir distribuições, perguntas por tópico e comparação entre dois lotes sintéticos. A análise de lotes existentes aceita `--atual` e, opcionalmente, `--anterior`. Os indicadores representam mensagens, não pessoas únicas ou impacto real. O agrupamento de tópicos é textual e depende de revisão para confirmar dúvidas recorrentes.

Consulte o [dicionário de indicadores e contrato de entrada](docs/indicadores_comunidade.md), incluindo os limites e a relação com as prioridades de evolução.

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
2. Abra o **SQL Editor** e execute, em ordem, cada arquivo de `supabase/migrations/` (ou use `supabase db push`).
3. Copie a string do **Session pooler** (a conexão direta só funciona por IPv6) para `DATABASE_URL` no `.env`.

O que muda no painel:

* Os lotes processados ficam no histórico.
* Se o mesmo conteúdo (comunidade e interações) for processado de novo no mesmo modo (simulado ou Gemini), o painel avisa e oferece **Abrir resultado existente** ou **Processar de novo e substituir**. A API `/processar` substitui o lote em silêncio.
* As decisões da curadoria e o status dos alertas são lembrados.
* A aba **Insights** agrega as mensagens salvas pela data de cada uma, dia a dia, no período escolhido no calendário. Lotes simulados e Gemini nunca se misturam, e a aba começa no modo em que o app está rodando.

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

A ingestão, os adaptadores, o pipeline, o painel, os testes e a avaliação das classificações possuem implementação. A base sintética de avaliação tem revisão individual de Everson registrada para todos os 60 casos. As métricas disponíveis caracterizam o classificador simulado; a avaliação real do Gemini, a validação ativa da OCI e as integrações operacionais ainda exigem verificações específicas.

## Contribuição

Antes de contribuir:

1. Atualize sua branch de trabalho.
2. Crie ou utilize a branch correspondente à sua responsabilidade.
3. Execute os testes automatizados.
4. Não publique arquivos `.env`, credenciais, ambientes virtuais, caches ou resultados locais.
5. Documente alterações de comportamento e limitações conhecidas.

Consulte a equipe antes de alterar interfaces, contratos de dados ou módulos compartilhados.
