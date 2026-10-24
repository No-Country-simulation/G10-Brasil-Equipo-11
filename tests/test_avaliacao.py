"""Verifica a avaliação com exemplos cujo resultado pode ser conferido à mão."""

import copy
import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.schemas import Analise
from communitylab.avaliacao import (
    avaliar,
    carregar_base,
    hash_casos,
    metricas_classificacao,
    salvar_resultados,
    validar_previsoes,
)


RAIZ = Path(__file__).resolve().parents[1]


def _gravar_json(caminho, conteudo):
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    return caminho


@pytest.fixture
def dados_base():
    especificacoes = [
        ("depoimento", "Altamente Positivo", 8, 10, "case_sucesso", "Consegui minha primeira vaga e estou muito feliz!"),
        ("pergunta_tecnica", "Neutro", 4, 6, "faq", "Como configuro a conexão do banco de dados?"),
        ("reclamacao", "Negativo", 5, 7, "alerta", "O áudio está ruim e não consigo acompanhar."),
        ("outro", "Neutro", 0, 2, "nenhuma", "A reunião está marcada para quinta-feira."),
    ]
    return {
        "versao": "teste-1",
        "natureza": "sintetica",
        "status_anotacao": "proposta_pendente_revisao_humana",
        "descricao": "Amostra sintética para verificar o avaliador.",
        "casos": [
            {
                "id": f"AV{indice:03d}",
                "grupo": "referencia",
                "entrada": {"autor": f"Pessoa {indice}", "canal": "#teste", "tipo": tipo, "texto": texto},
                "referencia": {"tipo": tipo, "sentimento": sentimento, "relevancia_min": minimo, "relevancia_max": maximo, "rota": rota},
                "justificativa": "Referência explícita usada para testar as contagens.",
                "evidencia": texto,
                "marcadores": ["teste_unitario"],
                "revisao_humana": False,
                "motivo_revisao": None,
            }
            for indice, (tipo, sentimento, minimo, maximo, rota, texto) in enumerate(especificacoes, 1)
        ],
    }


@pytest.fixture
def arquivo_base(tmp_path, dados_base):
    return _gravar_json(tmp_path / "base.json", dados_base)


@pytest.fixture
def base(arquivo_base):
    return carregar_base(arquivo_base)


@pytest.fixture
def dados_revisados(dados_base):
    dados = copy.deepcopy(dados_base)
    dados["versao"] = "teste-2"
    dados["status_anotacao"] = "revisada_individualmente"
    dados["revisao_anotacao"] = {
        "revisor": "Revisor de teste",
        "data": "2026-10-24",
        "metodo": "conferencia_individual_de_propostas",
        "decisao": "aprovado_sem_alteracoes",
        "escopo": "rotulos_justificativas_e_criterios",
        "versao_criterios": "teste-1",
        "versao_origem": dados_base["versao"],
        "dataset_origem_sha256": hashlib.sha256(json.dumps(dados_base).encode("utf-8")).hexdigest(),
        "casos_sha256": hash_casos(dados["casos"]),
        "casos_revisados": [caso["id"] for caso in dados["casos"]],
    }
    return dados


def _analise_correta(caso):
    referencia = caso["referencia"]
    return {
        **caso["entrada"],
        "tipo": referencia["tipo"],
        "sentimento": referencia["sentimento"],
        "topico": "Tema do teste",
        "relevancia": referencia["relevancia_min"],
        "rota": referencia["rota"],
    }


def _classificador_correto(base):
    por_texto = {c["entrada"]["texto"]: _analise_correta(c) for c in base["casos"]}
    return lambda entrada: copy.deepcopy(por_texto[entrada.texto])


def test_metricas_preservam_classe_sem_suporte_e_denominadores():
    resultado = metricas_classificacao(
        ["A", "A", "B", "B"], ["A", "B", "B", "C"], ["A", "B", "C"]
    )

    assert resultado["total"] == resultado["validos"] == 4
    assert resultado["rotulos"] == ["A", "B", "C"]
    assert resultado["matriz_confusao"] == [
        [1, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0],
    ]
    assert resultado["acuracia"] == pytest.approx(0.5)
    assert resultado["macro_f1"] == pytest.approx(7 / 12)
    assert resultado["ponderado_f1"] == pytest.approx(7 / 12)

    classes = {item["rotulo"]: item for item in resultado["por_classe"]}
    assert classes["A"]["suporte"] == 2
    assert classes["A"]["preditos"] == 1
    assert classes["A"]["verdadeiros_positivos"] == 1
    assert classes["A"]["precisao"] == pytest.approx(1)
    assert classes["A"]["recall"] == pytest.approx(0.5)
    assert classes["A"]["f1"] == pytest.approx(2 / 3)
    assert classes["B"]["precisao"] == pytest.approx(0.5)
    assert classes["B"]["recall"] == pytest.approx(0.5)
    assert classes["B"]["f1"] == pytest.approx(0.5)
    assert classes["C"]["suporte"] == 0
    assert classes["C"]["preditos"] == 1
    assert classes["C"]["precisao"] == 0
    assert classes["C"]["recall"] is None
    assert classes["C"]["f1"] == 0


def test_falha_conta_como_erro_e_tem_coluna_propria_na_matriz():
    resultado = metricas_classificacao(
        ["A", "A", "B", "B"], ["A", None, "B", "B"], ("A", "B", "C")
    )

    assert resultado["total"] == 4
    assert resultado["validos"] == 3
    assert resultado["acuracia"] == pytest.approx(0.75)
    assert resultado["macro_f1"] == pytest.approx(5 / 6)
    assert resultado["ponderado_f1"] == pytest.approx(5 / 6)
    assert resultado["matriz_confusao"] == [
        [1, 0, 0, 1],
        [0, 2, 0, 0],
        [0, 0, 0, 0],
    ]
    ausente = resultado["por_classe"][2]
    assert ausente["suporte"] == ausente["preditos"] == 0
    assert ausente["precisao"] is None
    assert ausente["recall"] is None
    assert ausente["f1"] is None


def test_falha_em_todas_as_previsoes_nao_produz_acuracia_perfeita():
    resultado = metricas_classificacao(["A", "B"], [None, None], ["A", "B"])

    assert resultado["validos"] == 0
    assert resultado["acuracia"] == 0
    assert resultado["macro_f1"] == 0
    assert resultado["ponderado_f1"] == 0
    assert resultado["matriz_confusao"] == [[0, 0, 1], [0, 0, 1]]
    for classe in resultado["por_classe"]:
        assert classe["precisao"] is None
        assert classe["recall"] == classe["f1"] == 0


def test_f1_ponderado_considera_o_suporte():
    resultado = metricas_classificacao(
        ["A", "A", "A", "B"], ["A", "A", "A", "A"], ["A", "B"]
    )

    assert resultado["acuracia"] == pytest.approx(3 / 4)
    assert resultado["macro_f1"] == pytest.approx(3 / 7)
    assert resultado["ponderado_f1"] == pytest.approx(9 / 14)


@pytest.mark.parametrize(
    ("referencias", "previsoes", "rotulos"),
    [
        (["A"], [], ["A"]),
        (["A"], ["A", "A"], ["A"]),
        (["fora"], ["A"], ["A"]),
        (["A"], ["fora"], ["A"]),
        (["A"], ["A"], ["A", "A"]),
    ],
)
def test_metricas_rejeitam_entradas_que_distorcem_contagens(
    referencias, previsoes, rotulos
):
    with pytest.raises(ValueError):
        metricas_classificacao(referencias, previsoes, rotulos)


def test_base_preserva_contrato_e_hash_dos_bytes(arquivo_base, base):
    assert base["_sha256"] == hashlib.sha256(arquivo_base.read_bytes()).hexdigest()
    assert len(base["casos"]) == 4
    assert base["status_anotacao"] == "proposta_pendente_revisao_humana"
    assert base["revisao_anotacao"] is None


def test_revisao_individual_registra_conteudo_confirmado_e_preserva_hash_do_arquivo(tmp_path, dados_revisados):
    arquivo = _gravar_json(tmp_path / "revisada.json", dados_revisados)
    carregada = carregar_base(arquivo)

    assert carregada["status_anotacao"] == "revisada_individualmente"
    assert carregada["revisao_anotacao"] == dados_revisados["revisao_anotacao"]
    assert carregada["_sha256"] == hashlib.sha256(arquivo.read_bytes()).hexdigest()
    assert hash_casos(carregada["casos"]) == dados_revisados["revisao_anotacao"]["casos_sha256"]


def test_hash_casos_e_independente_da_ordem_das_chaves_e_sensivel_ao_conteudo(dados_base):
    casos = dados_base["casos"]
    reordenados = [{chave: caso[chave] for chave in reversed(caso)} for caso in casos]
    assert hash_casos(casos) == hash_casos(reordenados)
    alterados = copy.deepcopy(casos)
    alterados[0]["justificativa"] += " Nova interpretação."
    assert hash_casos(casos) != hash_casos(alterados)


@pytest.mark.parametrize("registro", [None, "ausente"])
def test_base_revisada_exige_registro_de_revisao(tmp_path, dados_revisados, registro):
    if registro == "ausente":
        dados_revisados.pop("revisao_anotacao")
    else:
        dados_revisados["revisao_anotacao"] = None
    with pytest.raises(ValueError, match="exige registro"):
        carregar_base(_gravar_json(tmp_path / "invalida.json", dados_revisados))


def test_base_pendente_nao_pode_carregar_aprovacao(tmp_path, dados_revisados):
    dados_revisados["status_anotacao"] = "proposta_pendente_revisao_humana"
    with pytest.raises(ValueError, match="pendente"):
        carregar_base(_gravar_json(tmp_path / "invalida.json", dados_revisados))


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("revisor", "   "), ("revisor", 1),
        ("data", "2026-02-30"), ("data", "24/10/2026"),
        ("data", "2026-10-24T10:00:00"), ("data", "20261024"),
        ("metodo", "dupla_revisao"), ("decisao", "aprovado_com_alteracoes"),
        ("escopo", "producao"), ("versao_criterios", " "), ("versao_origem", ""),
        ("dataset_origem_sha256", "x" * 64), ("casos_sha256", "0" * 63),
        ("campo_desconhecido", True),
    ],
)
def test_registro_rejeita_metadados_invalidos(tmp_path, dados_revisados, campo, valor):
    dados_revisados["revisao_anotacao"][campo] = valor
    with pytest.raises(ValueError):
        carregar_base(_gravar_json(tmp_path / "invalida.json", dados_revisados))


@pytest.mark.parametrize("problema", ["ausente", "duplicado", "desconhecido"])
def test_revisao_precisa_cobrir_todos_os_ids_sem_duplicatas(tmp_path, dados_revisados, problema):
    ids = dados_revisados["revisao_anotacao"]["casos_revisados"]
    if problema == "ausente":
        ids.pop()
    elif problema == "duplicado":
        ids.append(ids[0])
    else:
        ids[-1] = "AV999"
    with pytest.raises(ValueError, match="todos os casos"):
        carregar_base(_gravar_json(tmp_path / "invalida.json", dados_revisados))


@pytest.mark.parametrize("alteracao", ["rotulo", "justificativa", "texto"])
def test_alterar_caso_nao_herda_revisao_anterior(tmp_path, dados_revisados, alteracao):
    caso = dados_revisados["casos"][0]
    if alteracao == "rotulo":
        caso["referencia"]["sentimento"] = "Positivo"
    elif alteracao == "justificativa":
        caso["justificativa"] += " Interpretação alterada."
    else:
        caso["entrada"]["texto"] += " Obrigado!"
    with pytest.raises(ValueError, match="conteúdo dos casos mudou"):
        carregar_base(_gravar_json(tmp_path / "alterada.json", dados_revisados))


@pytest.mark.parametrize("cenario", ["tipo_oculto", "tipo_informado"])
def test_revisao_nao_altera_metricas_ou_entrada_do_classificador(dados_base, dados_revisados, cenario):
    original = copy.deepcopy(dados_revisados)
    recebidos = []
    correto = _classificador_correto(dados_base)

    def classificador(entrada):
        recebidos.append(entrada.model_dump())
        previsto = correto(entrada)
        if previsto["tipo"] == "reclamacao":
            previsto.update(sentimento="Neutro", rota="nenhuma")
        return previsto

    pendente = avaliar(dados_base, classificador, cenario=cenario)
    revisado = avaliar(dados_revisados, classificador, cenario=cenario,
                       metadados={"revisao_anotacao": "registro externo não confiável"})

    assert dados_revisados == original
    for campo in ("cobertura", "metricas", "relevancia", "recortes", "criterios", "indicadores"):
        assert revisado[campo] == pendente[campo]
    assert recebidos[:4] == recebidos[4:]
    assert all(set(entrada) == {"autor", "canal", "tipo", "texto"} for entrada in recebidos)
    assert all(caso["status_anotacao"] == "revisada_individualmente" for caso in revisado["casos"])
    assert all(caso["status_anotacao"] == "proposta_pendente_revisao_humana" for caso in pendente["casos"])
    assert revisado["metadados"]["revisao_anotacao"] == dados_revisados["revisao_anotacao"]
    assert pendente["metadados"]["revisao_anotacao"] is None
    assert "aprovados individualmente" in revisado["limitacoes"][1]
    assert "pendentes de revisão humana" in pendente["limitacoes"][1]


def test_conjunto_versionado_cobre_contrato_e_mantem_desafios_identificados():
    from app import prompts
    from communitylab.avaliacao import ROTAS, SENTIMENTOS, TIPOS

    conjunto = carregar_base(RAIZ / "data/avaliacao_classificacoes.json")
    referencia = [c for c in conjunto["casos"] if c["grupo"] == "referencia"]
    desafios = [c for c in conjunto["casos"] if c["grupo"] == "desafio"]
    demonstracao = json.loads((RAIZ / "data/interacoes_exemplo.json").read_text(encoding="utf-8"))
    textos_demo = {i["texto"] for i in demonstracao["interacoes"]}

    assert {c["referencia"]["tipo"] for c in referencia} == set(TIPOS)
    assert {c["referencia"]["sentimento"] for c in referencia} == set(SENTIMENTOS)
    assert {c["referencia"]["rota"] for c in referencia} == set(ROTAS)
    assert desafios
    assert all(c["revisao_humana"] and c["motivo_revisao"] for c in desafios)
    assert all(c["entrada"]["texto"] not in textos_demo for c in conjunto["casos"])
    assert all(c["entrada"]["texto"] not in prompts.CLASSIFICADOR_SISTEMA for c in conjunto["casos"])


@pytest.mark.parametrize("conteudo", [None, [], {"casos": None}, {"casos": [None]}])
def test_estrutura_invalida_da_base_produz_erro_de_validacao(tmp_path, conteudo):
    arquivo = _gravar_json(tmp_path / "invalida.json", conteudo)
    with pytest.raises(ValueError):
        carregar_base(arquivo)


@pytest.mark.parametrize(
    ("caminho", "valor"),
    [
        (("entrada",), None),
        (("entrada", "texto"), "   "),
        (("entrada", "rotulo_esperado"), "depoimento"),
        (("entrada", "tipo"), "feedback"),
        (("referencia", "sentimento"), "positivo"),
        (("referencia", "relevancia_min"), True),
        (("referencia", "relevancia_min"), "8"),
        (("referencia", "relevancia_min"), 11),
        (("referencia", "relevancia_max"), 7),
        (("referencia", "relevancia_min"), 6),
        (("referencia", "rota"), "faq"),
        (("evidencia",), "Trecho que não existe na mensagem"),
        (("revisao_humana",), True),
        (("grupo",), "desafio"),
        (("marcadores",), []),
    ],
)
def test_base_rejeita_contratos_e_referencias_inconsistentes(
    tmp_path, dados_base, caminho, valor
):
    destino = dados_base["casos"][0]
    for parte in caminho[:-1]:
        destino = destino[parte]
    destino[caminho[-1]] = valor

    with pytest.raises(ValueError):
        carregar_base(_gravar_json(tmp_path / "invalida.json", dados_base))


def test_base_rejeita_id_duplicado(tmp_path, dados_base):
    dados_base["casos"][1]["id"] = dados_base["casos"][0]["id"]
    with pytest.raises(ValueError, match="duplicad"):
        carregar_base(_gravar_json(tmp_path / "duplicada.json", dados_base))


def test_base_rejeita_mensagem_duplicada_com_espacos_e_caixa(tmp_path, dados_base):
    outro = copy.deepcopy(dados_base["casos"][0])
    outro["id"] = "AV100"
    outro["entrada"]["texto"] = "  " + outro["entrada"]["texto"].upper().replace(" ", "  ")
    outro["evidencia"] = outro["entrada"]["texto"]
    dados_base["casos"].append(outro)
    with pytest.raises(ValueError, match="duplicad"):
        carregar_base(_gravar_json(tmp_path / "duplicada.json", dados_base))


def test_base_rejeita_chave_json_duplicada(tmp_path):
    arquivo = tmp_path / "duplicada.json"
    arquivo.write_text('{"versao":"1","versao":"2"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicad"):
        carregar_base(arquivo)


@pytest.mark.parametrize("cenario", ["tipo_oculto", "tipo_informado"])
def test_cenario_controla_tipo_sem_vazar_gabarito_ou_mutar_base(base, cenario):
    original = copy.deepcopy(base)
    recebidos = []
    correto = _classificador_correto(base)

    def classificador(entrada):
        recebidos.append(entrada.model_dump())
        return Analise(**correto(entrada))

    resultado = avaliar(base, classificador, cenario=cenario)

    assert base == original
    assert [item["tipo"] for item in recebidos] == (
        ["outro"] * 4 if cenario == "tipo_oculto" else [c["entrada"]["tipo"] for c in base["casos"]]
    )
    assert all(set(item) == {"autor", "canal", "tipo", "texto"} for item in recebidos)
    assert resultado["cobertura"] == {"total": 4, "validos": 4, "falhas": 0, "taxa": 1}
    assert resultado["metadados"]["cenario"] == cenario
    assert resultado["metadados"]["dataset_sha256"] == base["_sha256"]
    assert all(m["acuracia"] == 1 for m in resultado["metricas"].values())


def test_falha_individual_preserva_denominador_e_nao_expoe_detalhes(base):
    correto = _classificador_correto(base)
    texto_com_falha = base["casos"][2]["entrada"]["texto"]

    def classificador(entrada):
        if entrada.texto == texto_com_falha:
            raise RuntimeError("segredo-na-mensagem-do-provedor")
        return correto(entrada)

    resultado = avaliar(base, classificador)

    assert resultado["cobertura"] == {"total": 4, "validos": 3, "falhas": 1, "taxa": 0.75}
    assert all(m["acuracia"] == pytest.approx(0.75) for m in resultado["metricas"].values())
    assert resultado["relevancia"]["proporcao_dentro_faixa"] == pytest.approx(0.75)
    assert resultado["indicadores"]["alertas_nao_detectados"] == 1
    assert "segredo-na-mensagem-do-provedor" not in json.dumps(resultado)
    caso = next(c for c in resultado["casos"] if c["id"] == "AV003")
    assert caso["previsto"] is None
    assert caso["prioridade"] == "alta"
    assert caso["divergencias"] == ["falha_classificacao"]


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("relevancia", "8"), ("relevancia", True), ("relevancia", 11),
     ("sentimento", "positivo"), ("autor", "Outra pessoa"),
     ("texto", "Outra interação"), ("canal", "#outro"), ("topico", " "),
     ("confianca", 0.9)],
)
def test_previsao_invalida_ou_de_outra_origem_conta_como_falha(base, campo, valor):
    correto = _classificador_correto(base)
    primeiro_texto = base["casos"][0]["entrada"]["texto"]

    def classificador(entrada):
        previsto = correto(entrada)
        if entrada.texto == primeiro_texto:
            previsto[campo] = valor
        return previsto

    resultado = avaliar(base, classificador)
    assert resultado["cobertura"]["falhas"] == 1
    assert resultado["metricas"]["tipo"]["acuracia"] == pytest.approx(0.75)


def test_rota_incoerente_e_identificada_sem_ocultar_previsao(base):
    correto = _classificador_correto(base)

    def classificador(entrada):
        previsto = correto(entrada)
        if previsto["tipo"] == "reclamacao":
            previsto["rota"] = "faq"
        return previsto

    resultado = avaliar(base, classificador)
    assert resultado["cobertura"]["validos"] == 4
    assert resultado["indicadores"]["inconsistencias_rota"] == 1
    assert resultado["indicadores"]["alertas_nao_detectados"] == 1
    caso = next(c for c in resultado["casos"] if c["id"] == "AV003")
    assert set(caso["divergencias"]) == {"rota", "consistencia_rota"}
    assert caso["prioridade"] == "alta"


def _envelope(base):
    return {
        "dataset_sha256": base["_sha256"],
        "cenario": "tipo_oculto",
        "modelo": "fixture_de_teste",
        "previsoes": [{"id": c["id"], "analise": _analise_correta(c)} for c in reversed(base["casos"])],
    }


def test_previsoes_sao_associadas_por_id_e_aceitam_ausencias(tmp_path, base):
    envelope = _envelope(base)
    envelope["previsoes"].pop()
    mapeadas = validar_previsoes(_gravar_json(tmp_path / "previsoes.json", envelope), base, "tipo_oculto")

    assert set(mapeadas) == {"AV002", "AV003", "AV004"}
    assert mapeadas["AV003"]["tipo"] == "reclamacao"
    assert mapeadas["AV002"]["texto"] == base["casos"][1]["entrada"]["texto"]


@pytest.mark.parametrize("problema", ["hash", "cenario", "duplicado", "desconhecido", "sem_hash"])
def test_importacao_rejeita_previsoes_sem_identidade_valida(tmp_path, base, problema):
    envelope = _envelope(base)
    if problema == "hash":
        envelope["dataset_sha256"] = "0" * 64
    elif problema == "cenario":
        envelope["cenario"] = "tipo_informado"
    elif problema == "duplicado":
        envelope["previsoes"].append(copy.deepcopy(envelope["previsoes"][0]))
    elif problema == "desconhecido":
        envelope["previsoes"][0]["id"] = "AV999"
    else:
        base.pop("_sha256")
        envelope["dataset_sha256"] = None

    with pytest.raises(ValueError):
        validar_previsoes(_gravar_json(tmp_path / "previsoes.json", envelope), base, "tipo_oculto")


@pytest.fixture(scope="module")
def cli():
    spec = importlib.util.spec_from_file_location("avaliar_classificacoes_cli_test", RAIZ / "scripts/avaliar_classificacoes.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.mark.parametrize("anterior", [None, "gemini"])
def test_modo_mock_forcado_restaura_ambiente_apos_excecao(cli, monkeypatch, anterior):
    if anterior is None:
        monkeypatch.delenv("LLM_MODO", raising=False)
    else:
        monkeypatch.setenv("LLM_MODO", anterior)
    monkeypatch.setenv("GEMINI_API_KEY", "chave-inerte-para-teste")

    with pytest.raises(RuntimeError, match="falha controlada"):
        with cli.configurar_modo("mock"):
            assert cli.llm.modo_mock() is True
            assert os.environ["LLM_MODO"] == "mock"
            raise RuntimeError("falha controlada")

    assert os.environ.get("LLM_MODO") == anterior
    assert os.environ["GEMINI_API_KEY"] == "chave-inerte-para-teste"


@pytest.mark.parametrize("chave", [None, "", "   "])
def test_gemini_sem_chave_e_rejeitado_sem_alterar_ambiente(cli, monkeypatch, chave):
    monkeypatch.setenv("LLM_MODO", "mock")
    if chave is None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GEMINI_API_KEY", chave)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        with cli.configurar_modo("gemini"):
            pytest.fail("O contexto não deve ser iniciado sem credencial.")
    assert os.environ["LLM_MODO"] == "mock"


def test_cli_importa_previsoes_invertidas_por_id(tmp_path, arquivo_base, base, cli):
    arquivo_previsoes = _gravar_json(tmp_path / "previsoes.json", _envelope(base))
    saida = tmp_path / "resultados"

    codigo = cli.main(["--base", str(arquivo_base), "--modo", "arquivo", "--previsoes", str(arquivo_previsoes), "--saida", str(saida)])
    resultado = json.loads((saida / "arquivo_tipo_oculto/resultado.json").read_text(encoding="utf-8"))

    assert codigo == 0
    assert resultado["cobertura"]["taxa"] == 1
    assert resultado["metricas"]["tipo"]["acuracia"] == 1
    assert resultado["metadados"]["modo"] == "arquivo"
    assert resultado["metadados"]["origem_modelo"] == "declarado_no_arquivo_nao_verificado"
    assert resultado["metadados"]["importado_em_utc"].endswith("+00:00")
    assert "inicio_execucao_utc" not in resultado["metadados"]
    assert resultado["metadados"]["previsoes_sha256"] == hashlib.sha256(arquivo_previsoes.read_bytes()).hexdigest()
    assert len(list((saida / "arquivo_tipo_oculto").iterdir())) == 7


def test_cli_previsao_ausente_conta_como_falha_e_retorna_codigo_um(tmp_path, arquivo_base, base, cli):
    envelope = _envelope(base)
    envelope["previsoes"].pop()
    arquivo_previsoes = _gravar_json(tmp_path / "previsoes.json", envelope)
    saida = tmp_path / "resultados"
    codigo = cli.main(["--base", str(arquivo_base), "--modo", "arquivo", "--previsoes", str(arquivo_previsoes), "--saida", str(saida)])
    resultado = json.loads((saida / "arquivo_tipo_oculto/resultado.json").read_text(encoding="utf-8"))

    assert codigo == 1
    assert resultado["cobertura"]["validos"] == 3
    assert resultado["metricas"]["tipo"]["acuracia"] == pytest.approx(0.75)


def test_cli_mock_e_reprodutivel_e_roda_fora_da_raiz(tmp_path, arquivo_base):
    saida = tmp_path / "resultados"
    comando = [sys.executable, "-X", "utf8", str(RAIZ / "scripts/avaliar_classificacoes.py"), "--base", str(arquivo_base), "--saida", str(saida)]
    ambiente = {**os.environ, "GEMINI_API_KEY": "", "LLM_MODO": "mock"}
    primeira = subprocess.run(comando, cwd=tmp_path, env=ambiente, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert primeira.returncode == 0, primeira.stderr
    destino = saida / "mock_tipo_oculto"
    bytes_antes = {p.name: p.read_bytes() for p in destino.iterdir()}
    segunda = subprocess.run(comando, cwd=tmp_path, env=ambiente, capture_output=True, text=True, encoding="utf-8", timeout=30)

    assert segunda.returncode == 0, segunda.stderr
    assert {p.name: p.read_bytes() for p in destino.iterdir()} == bytes_antes
    assert not (tmp_path / "saida_local").exists()
    resultado = json.loads((destino / "resultado.json").read_text(encoding="utf-8"))
    assert resultado["metadados"]["modo"] == "mock"
    assert resultado["metadados"]["modelo"] == "regras_mock"
    assert "importado_em_utc" not in resultado["metadados"]
    assert "inicio_execucao_utc" not in resultado["metadados"]
    assert resultado["metadados"]["dependencias"]["pydantic"]


def test_cli_falha_amigavelmente_com_json_invalido(tmp_path, cli, capsys):
    arquivo = _gravar_json(tmp_path / "invalida.json", None)
    assert cli.main(["--base", str(arquivo), "--saida", str(tmp_path / "saida")]) == 2
    assert "Não foi possível avaliar" in capsys.readouterr().err
    assert not (tmp_path / "saida").exists()


def test_cli_informa_revisao_individual_sem_aprovar_previsoes(tmp_path, dados_revisados, cli, capsys):
    arquivo = _gravar_json(tmp_path / "revisada.json", dados_revisados)
    codigo = cli.main(["--base", str(arquivo), "--modo", "mock", "--saida", str(tmp_path / "saida")])
    texto = capsys.readouterr().out

    assert codigo == 0
    assert "revisados individualmente por Revisor de teste em 2026-10-24" in texto
    assert "não aprova as previsões nem o uso em produção" in texto
    assert "pendentes de revisão" not in texto


def test_exportacao_escapa_html_e_mantem_revisao_pendente(tmp_path, dados_base):
    payload = '<img src=x onerror="alert(1)"><script>alert(2)</script>'
    primeiro = dados_base["casos"][0]
    primeiro["entrada"]["texto"] = payload
    primeiro["evidencia"] = payload
    primeiro["justificativa"] = payload
    correto = _classificador_correto(dados_base)

    def classificador(entrada):
        previsto = correto(entrada)
        previsto["topico"] = payload
        return previsto

    resultado = avaliar(dados_base, classificador, metadados={"modelo": payload})
    caminhos = salvar_resultados(resultado, tmp_path)
    html = (tmp_path / "relatorio.html").read_text(encoding="utf-8")
    with (tmp_path / "revisao_classificacoes.csv").open(encoding="utf-8-sig", newline="") as arquivo:
        revisoes = list(csv.DictReader(arquivo))

    assert len(caminhos) == 7
    assert "<img src=x" not in html
    assert "<script>" not in html
    assert "&lt;img src=x" in html
    assert "não definido" in html
    assert "Proposta · revisão humana pendente" in html
    assert all(linha["status_revisao"] == "pendente" for linha in revisoes)
    assert all(linha["revisor"] == linha["data_revisao"] == "" for linha in revisoes)


def test_csv_registra_confirmacao_das_referencias_sem_aprovar_previsoes(tmp_path, dados_revisados):
    correto = _classificador_correto(dados_revisados)

    def classificador(entrada):
        previsto = correto(entrada)
        previsto.update(sentimento="Neutro", relevancia=0, rota="nenhuma")
        return previsto

    resultado = avaliar(dados_revisados, classificador)
    salvar_resultados(resultado, tmp_path)
    with (tmp_path / "revisao_classificacoes.csv").open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    por_id = {caso["id"]: caso["referencia"] for caso in dados_revisados["casos"]}

    assert len(linhas) == 4
    for linha in linhas:
        ref = por_id[linha["id"]]
        assert linha["status_revisao"] == "confirmado"
        assert linha["tipo_revisado"] == ref["tipo"]
        assert linha["sentimento_revisado"] == ref["sentimento"]
        assert linha["rota_revisada"] == ref["rota"]
        assert linha["relevancia_min_revisada"] == str(ref["relevancia_min"])
        assert linha["relevancia_max_revisada"] == str(ref["relevancia_max"])
        assert linha["revisor"] == "Revisor de teste"
        assert linha["data_revisao"] == "2026-10-24"
        assert "não aprova a previsão do classificador nem a publicação" in linha["observacao"]
    assert any(linha["sentimento_revisado"] != linha["sentimento_previsto"] for linha in linhas)
    html = (tmp_path / "relatorio.html").read_text(encoding="utf-8")
    assert "Referências revisadas individualmente" in html
    assert "Revisor de teste" in html and "2026-10-24" in html
    assert "Não houve dupla anotação independente" in html
    assert "revisão humana pendente" not in html


@pytest.mark.parametrize("texto", ["=1+1", "+1+1", "-1+1", "@SUM(1)", "  =1+1", "\t=1+1", "\r=1+1", "\n=1+1"])
def test_exportacao_csv_neutraliza_formulas(tmp_path, dados_base, texto):
    primeiro = dados_base["casos"][0]
    primeiro["entrada"]["texto"] = texto
    primeiro["evidencia"] = texto
    primeiro["justificativa"] = "=FORMULA(1)"
    resultado = avaliar(dados_base, _classificador_correto(dados_base))
    salvar_resultados(resultado, tmp_path)
    with (tmp_path / "revisao_classificacoes.csv").open(encoding="utf-8-sig", newline="") as arquivo:
        linha = next(l for l in csv.DictReader(arquivo) if l["id"] == "AV001")

    assert linha["texto"] == "'" + texto
    assert linha["evidencia"] == "'" + texto
    assert linha["justificativa"] == "'=FORMULA(1)"
