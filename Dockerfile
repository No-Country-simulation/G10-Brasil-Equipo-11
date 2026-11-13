# Sender AI: painel web + API (FastAPI) num container só.
# Credenciais NÃO entram na imagem: .env, wallet do Oracle e chave da OCI chegam
# em tempo de execução (veja docker-compose.yml e docs/deploy-vps.md).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Dependências primeiro: mudar só o código não refaz esta camada.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY src ./src
COPY ui ./ui
COPY web ./web
COPY data ./data

# Usuário sem privilégios; saida_local guarda pacotes quando OCI_STORAGE_MODE=local.
RUN useradd --create-home --uid 10001 sender \
    && mkdir -p /app/saida_local \
    && chown sender /app/saida_local
USER sender

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/saude', timeout=4)"

# Um processo só: as sessões de login ficam na memória do processo.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
