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


def _json_com(tmp_path, interacoes):
    arquivo = tmp_path / "interacoes.json"
    arquivo.write_text(json.dumps({"interacoes": interacoes}, ensure_ascii=False), encoding="utf-8")
    return arquivo


def test_ler_data_da_mensagem(tmp_path):
    from datetime import date
    arquivo = _json_com(tmp_path, [
        {"canal": "#geral", "texto": "a", "data": "2026-10-05"},
        {"canal": "#geral", "texto": "b", "date": "07/10/2026"},
        {"canal": "#geral", "texto": "c"},
    ])

    datas = [i.data for i in carregar_lote(arquivo).interacoes]

    assert datas == [date(2026, 10, 5), date(2026, 10, 7), None]


def test_ler_data_no_csv(tmp_path):
    from datetime import date
    arquivo = tmp_path / "interacoes.csv"
    arquivo.write_text("autor,canal,tipo,texto,data\nAna,#geral,outro,Oi,12/10/2026\n", encoding="utf-8")

    assert carregar_lote(arquivo).interacoes[0].data == date(2026, 10, 12)


def test_rejeitar_data_invalida(tmp_path):
    arquivo = _json_com(tmp_path, [{"canal": "#geral", "texto": "a", "data": "31/02/2026"}])

    with pytest.raises(ValueError, match="interação 1.*data"):
        carregar_lote(arquivo)
