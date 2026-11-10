import pytest
from app.repository import _normalizar_data_interacao
from datetime import date, datetime
from app.repository import (
    _asset_records,
    fingerprint_request,
    json_dumps,
)


def test_fingerprint_e_estavel_independente_da_ordem_das_chaves():
    primeiro = {"a": 1, "b": {"x": 2, "y": 3}}
    segundo = {"b": {"y": 3, "x": 2}, "a": 1}

    assert fingerprint_request(primeiro) == fingerprint_request(segundo)


def test_fingerprint_muda_quando_conteudo_muda():
    assert fingerprint_request(
        {"texto": "original"}
    ) != fingerprint_request(
        {"texto": "alterado"}
    )


def test_ativos_usam_fontes_exatas_e_removem_duplicatas():
    response = {
        "ativos_distribuicao_gerados": {
            "post_linkedin": {
                "titulo": "Case",
                "copy": "Texto",
            },
            "destaque_newsletter_semanal": {
                "chamada": "Resumo",
                "resumo": "Texto",
            },
            "sugestao_conteudo_faq": [
                {"tema": "OCI", "conteudo": "Como?"}
            ],
            "alertas_comunidade": [
                {"autor": "Ana", "motivo": "Precisa de apoio"}
            ],
        },
        "fontes_ativos": {
            "post": ["int-1", "int-1"],
            "newsletter": ["int-1", "int-2"],
            "faq_0": ["int-2"],
            "alerta_0": ["int-1"],
        },
    }

    records, ids = _asset_records(
        response,
        "proc-1",
        ["int-1", "int-2"],
    )

    by_key = {
        record["key"]: record
        for record in records
    }

    assert set(ids) == {"post", "newsletter", "faq_0"}
    assert by_key["post"]["sources"] == ["int-1"]
    assert by_key["newsletter"]["sources"] == [
        "int-1", "int-2"
    ]
    assert by_key["faq_0"]["sources"] == ["int-2"]
    assert all(
        record["kind"] != "ALERTA"
        for record in records
    )


def test_ativo_nao_pode_referenciar_outro_lote():
    response = {
        "ativos_distribuicao_gerados": {
            "post_linkedin": {
                "titulo": "Case",
                "copy": "Texto",
            }
        },
        "fontes_ativos": {
            "post": ["id-de-outro-lote"],
        },
    }

    with pytest.raises(
        ValueError,
        match="não pertencem ao lote",
    ):
        _asset_records(
            response,
            "proc-1",
            ["id-valido"],
        )


def test_fontes_malformadas_sao_rejeitadas():
    response = {
        "ativos_distribuicao_gerados": {
            "post_linkedin": {
                "titulo": "Case",
                "copy": "Texto",
            }
        },
        "fontes_ativos": {
            "post": "id-valido",
        },
    }

    with pytest.raises(
        ValueError,
        match="precisa ser uma lista",
    ):
        _asset_records(
            response,
            "proc-1",
            ["id-valido"],
        )


def test_ativo_sem_fonte_e_rejeitado():
    response = {
        "ativos_distribuicao_gerados": {
            "post_linkedin": {
                "titulo": "Case",
                "copy": "Texto",
            }
        },
        "fontes_ativos": {
            "post": [],
        },
    }

    with pytest.raises(
        ValueError,
        match="não possui fonte de origem",
    ):
        _asset_records(
            response,
            "proc-1",
            ["id-valido"],
        )


def test_serializacao_nao_oculta_tipos_invalidos():
    with pytest.raises(TypeError):
        json_dumps({"valor": object()})





def test_normalizar_data_interacao():
    assert _normalizar_data_interacao(
        "2026-10-05"
    ) == date(2026, 10, 5)


def test_normalizar_data_interacao_preserva_date():
    entrada = date(2026, 10, 5)

    assert _normalizar_data_interacao(
        entrada
    ) == entrada


def test_normalizar_data_interacao_usa_data_atual():
    resultado = _normalizar_data_interacao(None)

    assert isinstance(resultado, date)