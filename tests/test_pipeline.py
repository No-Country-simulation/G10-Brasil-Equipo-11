"""Testes em modo simulado (não gastam cota da API). Rode com: pytest"""
import json
import os
from pathlib import Path

os.environ["LLM_MODO"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from app.ia import decidir_rota  # noqa: E402
from app.main import app  # noqa: E402

LOTE = json.loads((Path(__file__).parent.parent / "data/interacoes_exemplo.json").read_text(encoding="utf-8"))
cliente = TestClient(app)


def test_roteamento():
    assert decidir_rota("depoimento", "Altamente Positivo", 9) == "case_sucesso"
    assert decidir_rota("depoimento", "Positivo", 5) == "nenhuma"
    assert decidir_rota("pergunta_tecnica", "Neutro", 6) == "faq"
    assert decidir_rota("outro", "Negativo", 6) == "alerta"
    assert decidir_rota("reclamacao", "Neutro", 4) == "alerta"


def test_processar_lote_completo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = cliente.post("/processar", json=LOTE)
    assert r.status_code == 200
    corpo = r.json()
    ativos = corpo["ativos_distribuicao_gerados"]
    assert corpo["resumo_comunidade"]["total_interacoes_processadas"] == len(LOTE["interacoes"])
    assert ativos["post_linkedin"] is not None
    assert ativos["destaque_newsletter_semanal"] is not None
    assert len(ativos["sugestao_conteudo_faq"]) >= 1
    assert len(ativos["alertas_comunidade"]) >= 1
    assert corpo["armazenamento_oci"]["status"] == "salvo_localmente"


def test_lote_vazio():
    r = cliente.post("/processar", json={**LOTE, "interacoes": []})
    assert r.status_code == 400
