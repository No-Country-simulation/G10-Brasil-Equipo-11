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
│   ├── schemas.py
│   └── storage.py
├── data/
│   └── interacoes_exemplo.json
├── src/
│   └── communitylab/
│       ├── adapter.py
│       └── ingestion.py
├── tests/
│   ├── test_adapter.py
│   ├── test_ingestion.py
│   └── test_pipeline.py
├── ui/
│   └── painel.py
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
streamlit run ui/painel.py
```

O painel permite carregar um lote JSON, processar interações, visualizar classificações e revisar os conteúdos gerados.

## Executando os testes

Na raiz do projeto:

```powershell
python -m pytest -v
```

Na última execução documentada, os 13 testes automatizados passaram. Execute-os novamente no seu ambiente para confirmar o estado atual.

## Modos de operação

### Modo simulado

Permite executar o fluxo sem uma chave Gemini. As respostas são produzidas pelas regras implementadas para simulação e não devem ser interpretadas como resultados de um modelo de linguagem real.

### Gemini

O uso do modelo real depende da configuração de `GEMINI_API_KEY` e das demais variáveis documentadas em `.env.example`.

### Armazenamento

O sistema pode salvar os resultados localmente ou utilizar o OCI Object Storage quando configurado. A integração real com a nuvem deve ser validada separadamente.

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
