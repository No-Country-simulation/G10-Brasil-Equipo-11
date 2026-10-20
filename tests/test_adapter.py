import json

import pytest

from communitylab.adapter import carregar_lote


def test_carregar_json_da_equipe():
    lote = carregar_lote("data/interacoes_exemplo.json")

    assert lote.origem_comunidade == "Discord_Grupo_ONE_G10"
    assert lote.periodo_referencia == "Semana_04"
    assert len(lote.interacoes) == 12


def test_preservar_campos_da_interacao():
    lote = carregar_lote("data/interacoes_exemplo.json")
    primeira = lote.interacoes[0]

    assert primeira.autor == "Mariana Souza"
    assert primeira.canal == "#conquistas-e-vagas"
    assert primeira.tipo == "depoimento"
    assert primeira.texto.startswith("Pessoal, passei")


def test_converter_campos_em_ingles(tmp_path):
    arquivo = tmp_path / "interacoes.json"
    arquivo.write_text(
        json.dumps(
            {
                "interactions": [
                    {
                        "author": "Pessoa Teste",
                        "channel": "#geral",
                        "type": "feedback",
                        "text": "Mensagem de teste",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    lote = carregar_lote(arquivo)

    assert len(lote.interacoes) == 1
    assert lote.interacoes[0].autor == "Pessoa Teste"
    assert lote.interacoes[0].canal == "#geral"
    assert lote.interacoes[0].tipo == "feedback"
    assert lote.interacoes[0].texto == "Mensagem de teste"


def test_gerar_identificador_anonimo(tmp_path):
    arquivo = tmp_path / "interacoes.json"
    arquivo.write_text(
        json.dumps(
            [
                {
                    "channel": "#geral",
                    "type": "outro",
                    "text": "Mensagem sem autor",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    lote = carregar_lote(arquivo)

    assert lote.interacoes[0].autor == "anônimo_001"


def test_rejeitar_lista_vazia(tmp_path):
    arquivo = tmp_path / "interacoes.json"
    arquivo.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="não contém interações"):
        carregar_lote(arquivo)
