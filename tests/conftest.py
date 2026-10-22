"""Configuração compartilhada dos testes.

Marcador "real": testes que chamam o Gemini ou o OCI de verdade.
Eles são pulados automaticamente quando as credenciais não existem.

    python -m pytest                 # tudo (os reais são pulados sem chave)
    python -m pytest -m "not real"   # só os testes simulados
    python -m pytest -m real -v      # só os testes com serviços reais
"""


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "real: chama serviços externos (Gemini ou OCI); pulado sem credenciais",
    )
