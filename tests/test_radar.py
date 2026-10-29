"""Oráculos de contagem, comparação e rastreabilidade do radar analítico."""

import copy
import csv
import importlib.util
import json
import os
import unicodedata
from pathlib import Path

import pytest

from app.schemas import Analise
from communitylab.avaliacao import ROTAS, SENTIMENTOS, TIPOS
from communitylab.radar import construir_radar, renderizar_radar, resumir_lote


RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def lote():
    especificacoes = [
        ("pergunta_tecnica", "Neutro", "faq", " Configuração  OCI "),
        ("pergunta_tecnica", "Negativo", "alerta", unicodedata.normalize("NFD", "configuração oci")),
        ("reclamacao", "Neutro", "alerta", "Acesso ao curso"),
        ("feedback", "Positivo", "nenhuma", "Formato das aulas"),
    ]
    return {
        "origem_comunidade": "Comunidade de teste",
        "periodo_referencia": "semana_02",
        "natureza_dados": "sintetica",
        "modo_classificacao": "importado",
        "analises": [
            {"autor": "autor_privado_repetido", "canal": "#teste", "texto": f"texto_privado_{indice}",
             "tipo": tipo, "sentimento": sentimento, "topico": topico, "relevancia": 5, "rota": rota}
            for indice, (tipo, sentimento, rota, topico) in enumerate(especificacoes, 1)
        ],
    }


def _categoria(resumo, dimensao, categoria):
    return next(c for c in resumo["distribuicoes"][dimensao] if c["categoria"] == categoria)


def test_resumo_separa_alerta_de_sentimento_e_mensagem_de_pessoa(lote):
    original = copy.deepcopy(lote)
    resumo = resumir_lote(lote)

    assert resumo["total_interacoes"] == 4
    assert resumo["indicadores"]["mensagens_negativas"] == 1
    assert resumo["indicadores"]["proporcao_mensagens_negativas"] == pytest.approx(0.25)
    assert resumo["indicadores"]["mensagens_em_alerta"] == 2
    assert resumo["indicadores"]["proporcao_mensagens_em_alerta"] == pytest.approx(0.5)
    assert resumo["indicadores"]["perguntas_tecnicas"] == 2
    assert resumo["indicadores"]["perguntas_em_alerta"] == 1
    assert lote == original
    serializado = json.dumps(resumo, ensure_ascii=False)
    assert "autor_privado_repetido" not in serializado
    assert "texto_privado_" not in serializado


def test_distribuicoes_preservam_categorias_ausentes_e_total(lote):
    resumo = resumir_lote(lote)
    for dimensao, vocabulario in (("tipo", TIPOS), ("sentimento", SENTIMENTOS), ("rota", ROTAS)):
        linhas = resumo["distribuicoes"][dimensao]
        assert [c["categoria"] for c in linhas] == list(vocabulario)
        assert sum(c["quantidade"] for c in linhas) == 4
        assert sum(c["proporcao"] for c in linhas) == pytest.approx(1)
    assert _categoria(resumo, "tipo", "projeto")["quantidade"] == 0
    assert _categoria(resumo, "tipo", "projeto")["proporcao"] == 0
    assert _categoria(resumo, "tipo", "pergunta_tecnica")["proporcao"] == pytest.approx(0.5)


def test_perguntas_agregam_unicode_caixa_espacos_e_preservam_indices(lote):
    resumo = resumir_lote(lote)
    assert resumo["indicadores"]["topicos_com_perguntas_repetidas"] == 1
    assert len(resumo["perguntas_por_topico"]) == 1
    topico = resumo["perguntas_por_topico"][0]
    assert topico["quantidade"] == 2
    assert topico["indices_origem"] == [1, 2]
    assert topico["recorrente"] is True


def test_topicos_semelhantes_nao_sao_fundidos_sem_semantica(lote):
    lote["analises"][1]["topico"] = "Configurar Oracle Cloud"
    resumo = resumir_lote(lote)
    assert len(resumo["perguntas_por_topico"]) == 2
    assert resumo["indicadores"]["topicos_com_perguntas_repetidas"] == 0
    assert all(not t["recorrente"] for t in resumo["perguntas_por_topico"])


def test_duplicatas_sao_sinalizadas_sem_descartar_mensagens(lote):
    lote["analises"].append(copy.deepcopy(lote["analises"][0]))
    resumo = resumir_lote(lote)
    assert resumo["total_interacoes"] == 5
    assert resumo["indicadores"]["registros_possivelmente_duplicados"] == 1
    assert resumo["perguntas_por_topico"][0]["indices_origem"] == [1, 2, 5]
    assert any("inflar" in r for r in resumo["recomendacoes_para_revisao"])


def test_rota_incoerente_e_sinalizada_preservando_previsao_original(lote):
    lote["analises"][2]["rota"] = "nenhuma"
    resultado = construir_radar(lote)
    resumo = resultado["atual"]

    assert resumo["indicadores"]["inconsistencias_rota"] == 1
    assert resumo["indicadores"]["mensagens_em_alerta"] == 1
    assert _categoria(resumo, "rota", "nenhuma")["quantidade"] == 2
    assert any("1 rotas incompatíveis" in r for r in resumo["recomendacoes_para_revisao"])
    assert "1 rotas incompatíveis" in renderizar_radar(resultado)


@pytest.mark.parametrize("valor", [None, [], {}, {"analises": []}])
def test_lote_malformado_e_rejeitado(valor):
    with pytest.raises(ValueError):
        resumir_lote(valor)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("origem_comunidade", " "), ("periodo_referencia", None),
     ("natureza_dados", "confirmada"), ("natureza_dados", []),
     ("modo_classificacao", {}), ("modo_classificacao", "automatico"),
     ("analises", []), ("analises", None)],
)
def test_metadados_e_lote_vazio_sao_rejeitados(lote, campo, valor):
    lote[campo] = valor
    with pytest.raises(ValueError):
        resumir_lote(lote)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("relevancia", "5"), ("relevancia", True), ("relevancia", 11),
     ("sentimento", "neutro"), ("topico", "   "), ("autor", ""),
     ("texto", " "), ("confianca", 0.9)],
)
def test_analise_invalida_nao_entra_nos_indicadores(lote, campo, valor):
    lote["analises"][0][campo] = valor
    with pytest.raises(ValueError):
        resumir_lote(lote)


def test_comparacao_usa_proporcoes_de_denominadores_diferentes(lote):
    anterior = copy.deepcopy(lote)
    anterior["periodo_referencia"] = "semana_01"
    anterior["analises"] = anterior["analises"][1:3]
    comparacao = construir_radar(lote, anterior)["comparacao"]
    alerta = next(c for c in comparacao["categorias"] if c["dimensao"] == "rota" and c["categoria"] == "alerta")

    assert comparacao["total_anterior"] == 2
    assert comparacao["total_atual"] == 4
    assert comparacao["variacao_total"] == 2
    assert alerta["quantidade_anterior"] == alerta["quantidade_atual"] == 2
    assert alerta["proporcao_anterior"] == 1
    assert alerta["proporcao_atual"] == pytest.approx(0.5)
    assert alerta["variacao_pontos_percentuais"] == pytest.approx(-50)
    assert "não demonstram tendência ou impacto" in comparacao["interpretacao"]


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("origem_comunidade", "Outra comunidade"), ("natureza_dados", "real"),
     ("modo_classificacao", "gemini"), ("periodo_referencia", "semana_02")],
)
def test_comparacao_rejeita_lotes_incompativeis(lote, campo, valor):
    anterior = copy.deepcopy(lote)
    anterior["periodo_referencia"] = "semana_01"
    anterior[campo] = valor
    with pytest.raises(ValueError):
        construir_radar(lote, anterior)


def test_hash_ignora_ordem_das_chaves_e_identifica_mudanca_de_dados(lote):
    primeiro = construir_radar(lote)
    reordenado = dict(reversed(list(lote.items())))
    segundo = construir_radar(reordenado)
    assert primeiro["rastreabilidade"] == segundo["rastreabilidade"]
    assert primeiro["comparacao"] is None
    assert primeiro["rastreabilidade"]["lote_anterior_sha256"] is None
    lote["analises"][0]["texto"] += " editado"
    terceiro = construir_radar(lote)
    assert primeiro["rastreabilidade"]["lote_atual_sha256"] != terceiro["rastreabilidade"]["lote_atual_sha256"]


def test_html_escapa_metadados_topicos_e_omite_textos_autores(lote):
    payload = '<script>alert("x")</script><img src=x onerror=alert(1)>'
    lote["origem_comunidade"] = payload
    lote["periodo_referencia"] = payload
    lote["analises"][0]["topico"] = payload
    resultado = construir_radar(lote)
    html = renderizar_radar(resultado)

    assert "<script>" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;" in html
    assert "autor_privado_repetido" not in html
    assert "texto_privado_" not in html
    assert "Sem lote anterior" in html
    assert html == renderizar_radar(resultado)


def test_nota_demonstracao_e_exibida_e_escapada_no_html(lote):
    resultado = construir_radar(lote)
    resultado["nota_demonstracao"] = 'Recortes sintéticos A/B; não são períodos observados. <script>alert(1)</script>'
    html = renderizar_radar(resultado)

    assert "Recortes sintéticos A/B; não são períodos observados." in html
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


@pytest.fixture(scope="module")
def cli_radar():
    spec = importlib.util.spec_from_file_location("analisar_comunidade_cli_test", RAIZ / "scripts/analisar_comunidade.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.mark.parametrize("anterior", [None, "gemini"])
def test_demonstracao_forca_mock_oculta_tipo_e_restaura_ambiente(cli_radar, monkeypatch, anterior):
    if anterior is None:
        monkeypatch.delenv("LLM_MODO", raising=False)
    else:
        monkeypatch.setenv("LLM_MODO", anterior)
    recebidos = []

    def classificar(entrada):
        assert os.environ["LLM_MODO"] == "mock"
        recebidos.append(entrada.tipo)
        return Analise(**entrada.model_dump(), sentimento="Neutro", topico="Geral", relevancia=5, rota="nenhuma")

    monkeypatch.setattr(cli_radar, "classificar", classificar)
    atual, passado = cli_radar._demonstracao()
    assert recebidos and set(recebidos) == {"outro"}
    assert len(atual["analises"]) == len(passado["analises"])
    assert atual["periodo_referencia"] != passado["periodo_referencia"]
    assert atual["natureza_dados"] == passado["natureza_dados"] == "sintetica"
    assert os.environ.get("LLM_MODO") == anterior


def test_demonstracao_restaura_ambiente_se_classificacao_falhar(cli_radar, monkeypatch):
    monkeypatch.setenv("LLM_MODO", "gemini")

    def falhar(entrada):
        raise RuntimeError("falha controlada")

    monkeypatch.setattr(cli_radar, "classificar", falhar)
    with pytest.raises(RuntimeError, match="falha controlada"):
        cli_radar._demonstracao()
    assert os.environ["LLM_MODO"] == "gemini"


def test_cli_exporta_apenas_agregados_para_lote_importado(tmp_path, lote, cli_radar):
    entrada = tmp_path / "entrada.json"
    entrada.write_text(json.dumps(lote, ensure_ascii=False), encoding="utf-8")
    saida = tmp_path / "saida"
    assert cli_radar.main(["--atual", str(entrada), "--saida", str(saida)]) == 0
    assert {p.name for p in saida.iterdir()} == {"radar.json", "radar.html", "distribuicoes.csv", "comparacao_categorias.csv"}
    for arquivo in saida.iterdir():
        texto = arquivo.read_text(encoding="utf-8-sig")
        assert "autor_privado_repetido" not in texto
        assert "texto_privado_" not in texto
    with (saida / "distribuicoes.csv").open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert len(linhas) == len(TIPOS) + len(SENTIMENTOS) + len(ROTAS)


def test_cli_protege_arquivo_de_entrada_e_reporta_erro(tmp_path, lote, cli_radar, capsys):
    entrada = tmp_path / "radar.json"
    original = json.dumps(lote, ensure_ascii=False)
    entrada.write_text(original, encoding="utf-8")
    assert cli_radar.main(["--atual", str(entrada), "--saida", str(tmp_path)]) == 2
    assert entrada.read_text(encoding="utf-8") == original
    assert "sobrescrever" in capsys.readouterr().err
