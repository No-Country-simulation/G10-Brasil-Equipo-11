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

import pytest


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
