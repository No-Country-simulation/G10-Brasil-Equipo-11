"""Configuração compartilhada dos testes.

Marcador "real": testes que chamam o Gemini, o OCI ou o Supabase de verdade.
Eles são pulados automaticamente quando as credenciais não existem.

Os demais testes nunca enxergam o banco: a fixture autouse `banco_desligado`
zera `DATABASE_URL` (vazio, e não removida, para o `load_dotenv` do app não
repor o valor do `.env`).

    python -m pytest                 # tudo (os reais são pulados sem chave)
    python -m pytest -m "not real"   # só os testes simulados
    python -m pytest -m real -v      # só os testes com serviços reais
"""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parent.parent


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "real: chama serviços externos (Gemini, OCI ou Supabase); pulado sem credenciais",
    )


@pytest.fixture(autouse=True)
def banco_desligado(request, monkeypatch):
    """Isola os testes sem o marcador `real` de qualquer banco de dados."""
    if request.node.get_closest_marker("real") is None:
        monkeypatch.setenv("DATABASE_URL", "")


def banco_de_teste(monkeypatch, prefixo: str):
    """Aponta o app para o banco real e devolve (url, nome da comunidade de teste).

    Lê DATABASE_URL do `.env` da raiz ou do terminal; sem ela, pula o teste. Força o modo mock e
    sem OCI. Reutilizável com outro prefixo (ex.: "Teste_Painel_").
    """
    url = dotenv_values(RAIZ / ".env").get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url or not url.strip():
        pytest.skip("DATABASE_URL não configurada no .env")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("LLM_MODO", "mock")
    monkeypatch.delenv("OCI_NAMESPACE", raising=False)
    return url, f"{prefixo}{uuid4().hex[:8]}"


def limpar_comunidade(url: str, comunidade: str):
    import psycopg
    with psycopg.connect(url) as conn:
        conn.execute("delete from lotes where comunidade_id in (select id from comunidades where nome = %s)",
                     (comunidade,))
        conn.execute("delete from comunidades where nome = %s", (comunidade,))


@pytest.fixture
def banco_real(monkeypatch):
    """Banco real para os testes do repositório; apaga a comunidade de teste no fim."""
    url, comunidade = banco_de_teste(monkeypatch, "Teste_Repositorio_")
    yield comunidade
    limpar_comunidade(url, comunidade)
