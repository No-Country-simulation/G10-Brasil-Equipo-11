"""Testes de integração do CommunityLab. Responsável: Renato.

Verificam o sistema como um todo, do arquivo de entrada até o pacote salvo:

    arquivo (JSON ou CSV) -> adaptador -> API /processar -> pipeline -> pacote salvo

Organização:
  1. Fluxo ponta a ponta com JSON
  2. Roteamento: cada tipo de mensagem cai na rota certa
  3. Entradas inválidas são recusadas sem travar
  4. Acentos e emojis preservados do começo ao fim
  5. Importação de CSV pelo adaptador (o painel tem testes próprios em tests/test_painel.py)
  6. Limitações conhecidas (xfail): passam a "XPASS" quando forem resolvidas
  7. Serviços reais (Gemini e OCI): pulados sem credenciais

Rode da raiz do projeto com:  python -m pytest tests/test_integracao.py -v
"""
import json
import os
from datetime import date
from pathlib import Path

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import RespostaProcessamento
from communitylab.adapter import carregar_lote

RAIZ = Path(__file__).resolve().parent.parent
LOTE_EXEMPLO = json.loads((RAIZ / "data" / "interacoes_exemplo.json").read_text(encoding="utf-8"))
ROTAS_VALIDAS = {"case_sucesso", "faq", "alerta", "nenhuma"}

cliente = TestClient(app)


@pytest.fixture(autouse=True)
def ambiente_isolado(request, tmp_path, monkeypatch):
    """Cada teste roda numa pasta temporária, para não sujar o projeto com saida_local/.

    Testes simulados forçam o modo mock e desligam o OCI, mesmo que o .env tenha chaves.
    """
    monkeypatch.chdir(tmp_path)
    if request.node.get_closest_marker("real") is None:
        monkeypatch.setenv("LLM_MODO", "mock")
        monkeypatch.delenv("OCI_NAMESPACE", raising=False)


def lote(*interacoes, periodo="Semana_99"):
    return {
        "origem_comunidade": "Teste_Integracao",
        "periodo_referencia": periodo,
        "interacoes": [
            {"autor": autor, "canal": canal, "tipo": tipo, "texto": texto}
            for autor, canal, tipo, texto in interacoes
        ],
    }


def caminho_pacote_local(periodo: str) -> Path:
    semana = periodo.lower().replace("_", "-")
    return Path("saida_local") / "ativos" / f"{date.today().year}-{semana}" / "pacote-distribuicao.json"


# ---------------------------------------------------------------------------
# 1. Fluxo ponta a ponta com JSON
# ---------------------------------------------------------------------------
def test_api_saude_responde():
    r = cliente.get("/saude")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "modo_llm": "mock"}


def test_lote_exemplo_ponta_a_ponta_respeita_contrato():
    r = cliente.post("/processar", json=LOTE_EXEMPLO)

    assert r.status_code == 200, r.text
    corpo = r.json()
    RespostaProcessamento(**corpo)  # levanta erro se fugir do contrato

    assert corpo["status"] == "sucesso"
    assert corpo["resumo_comunidade"]["total_interacoes_processadas"] == len(LOTE_EXEMPLO["interacoes"])
    assert len(corpo["analises"]) == len(LOTE_EXEMPLO["interacoes"])
    assert {a["rota"] for a in corpo["analises"]} <= ROTAS_VALIDAS
    for a in corpo["analises"]:
        assert 0 <= a["relevancia"] <= 10


def test_lote_exemplo_gera_todos_os_tipos_de_ativo():
    ativos = cliente.post("/processar", json=LOTE_EXEMPLO).json()["ativos_distribuicao_gerados"]

    assert ativos["post_linkedin"]["copy"].strip()
    assert ativos["destaque_newsletter_semanal"]["chamada"].strip()
    assert len(ativos["sugestao_conteudo_faq"]) >= 1
    assert len(ativos["alertas_comunidade"]) >= 1


def test_pacote_salvo_no_caminho_combinado_e_igual_a_resposta():
    corpo = cliente.post("/processar", json=LOTE_EXEMPLO).json()
    arquivo = caminho_pacote_local(LOTE_EXEMPLO["periodo_referencia"])

    assert corpo["armazenamento_oci"]["status"] == "salvo_localmente"
    assert arquivo.exists(), f"pacote não encontrado em {arquivo}"
    salvo = json.loads(arquivo.read_text(encoding="utf-8"))
    assert salvo["resumo_comunidade"] == corpo["resumo_comunidade"]
    assert salvo["ativos_distribuicao_gerados"] == corpo["ativos_distribuicao_gerados"]


# ---------------------------------------------------------------------------
# 2. Roteamento
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "tipo, texto, rota_esperada",
    [
        ("depoimento", "Fui contratada como desenvolvedora júnior, muito grata!", "case_sucesso"),
        ("pergunta_tecnica", "Como configuro o namespace do bucket na OCI?", "faq"),
        ("outro", "Estou travado há dias e pensando em desistir do curso.", "alerta"),
        ("reclamacao", "O áudio das aulas do módulo 2 está baixo.", "alerta"),
        ("feedback", "As aulas de prompts estão bem organizadas.", "nenhuma"),
    ],
    ids=["depoimento->case", "duvida->faq", "negativo->alerta", "reclamacao->alerta", "neutro->nenhuma"],
)
def test_cada_mensagem_cai_na_rota_certa(tipo, texto, rota_esperada):
    corpo = cliente.post("/processar", json=lote(("Pessoa Teste", "#teste", tipo, texto))).json()
    assert corpo["analises"][0]["rota"] == rota_esperada


def test_lote_sem_case_nao_gera_post_linkedin():
    corpo = cliente.post("/processar", json=lote(
        ("Pessoa A", "#duvidas", "pergunta_tecnica", "Como uso o LangGraph?"),
    )).json()
    ativos = corpo["ativos_distribuicao_gerados"]
    assert ativos.get("post_linkedin") is None
    assert ativos["destaque_newsletter_semanal"] is not None  # newsletter sai sempre


# ---------------------------------------------------------------------------
# 3. Entradas inválidas
# ---------------------------------------------------------------------------
def test_lote_vazio_e_recusado():
    assert cliente.post("/processar", json=lote()).status_code == 400


@pytest.mark.parametrize(
    "interacao",
    [
        {"autor": "A", "canal": "#x", "tipo": "depoimento"},                         # sem texto
        {"autor": "A", "canal": "#x", "tipo": "tipo_que_nao_existe", "texto": "oi"},  # tipo inválido
        {"canal": "#x", "tipo": "outro", "texto": "oi"},                              # sem autor
    ],
    ids=["sem-texto", "tipo-invalido", "sem-autor"],
)
def test_interacao_malformada_e_recusada_com_422(interacao):
    corpo = {"origem_comunidade": "T", "periodo_referencia": "Semana_99", "interacoes": [interacao]}
    assert cliente.post("/processar", json=corpo).status_code == 422


def test_corpo_que_nao_e_json_e_recusado():
    r = cliente.post("/processar", content=b"isto nao e json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 4. Codificação de caracteres
# ---------------------------------------------------------------------------
TEXTO_ACENTUADO = "Ação, configuração e atenção: São Paulo, Joaçaba, coração 🚀 — “aspas” ç ã õ é"


def test_acentos_e_emojis_preservados_na_resposta_e_no_arquivo():
    entrada = lote(("João Ninguém", "#geral", "feedback", TEXTO_ACENTUADO))
    corpo = cliente.post("/processar", json=entrada).json()

    assert corpo["analises"][0]["texto"] == TEXTO_ACENTUADO
    assert corpo["analises"][0]["autor"] == "João Ninguém"

    bruto = caminho_pacote_local("Semana_99").read_text(encoding="utf-8")
    assert TEXTO_ACENTUADO in bruto, "o arquivo salvo deve ter os acentos legíveis, não \\u00e7"


# ---------------------------------------------------------------------------
# 5. Importação de CSV pelo adaptador
# ---------------------------------------------------------------------------
CSV_PT = (
    "autor,canal,tipo,texto\n"
    "Ana Teste,#vagas,depoimento,Fui contratada como dev júnior! Muito grata\n"
    "Beto Teste,#duvidas,pergunta_tecnica,Como configuro o bucket?\n"
)


def test_csv_utf8_passa_pelo_adaptador_e_pela_api(tmp_path):
    arquivo = tmp_path / "lote.csv"
    arquivo.write_text(CSV_PT, encoding="utf-8")

    entrada = carregar_lote(arquivo, origem_comunidade="CSV_Teste", periodo_referencia="Semana_98")
    corpo = cliente.post("/processar", json=entrada.model_dump()).json()

    assert [a["rota"] for a in corpo["analises"]] == ["case_sucesso", "faq"]
    assert corpo["analises"][0]["texto"].endswith("Muito grata")


def test_csv_utf8_com_bom_do_excel_funciona(tmp_path):
    """Excel: Salvar como > 'CSV UTF-8 (delimitado por vírgulas)'."""
    arquivo = tmp_path / "excel_utf8.csv"
    arquivo.write_text(CSV_PT, encoding="utf-8-sig")
    assert carregar_lote(arquivo).interacoes[0].autor == "Ana Teste"


def test_csv_com_colunas_em_ingles_funciona(tmp_path):
    arquivo = tmp_path / "en.csv"
    arquivo.write_text("author,channel,type,text\nAna,#vagas,depoimento,Fui aprovada!\n", encoding="utf-8")
    assert carregar_lote(arquivo).interacoes[0].texto == "Fui aprovada!"


def test_csv_sem_coluna_obrigatoria_da_erro_claro(tmp_path):
    arquivo = tmp_path / "faltando.csv"
    arquivo.write_text("autor,texto\nAna,oi\n", encoding="utf-8")
    with pytest.raises(ValueError):
        carregar_lote(arquivo)


# ---------------------------------------------------------------------------
# 6. Limitações conhecidas
#    xfail = "sabemos que ainda falha". Quando alguém corrigir, o pytest mostra XPASS:
#    aí basta apagar o @pytest.mark.xfail e o teste vira uma garantia permanente.
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="Excel em português salva CSV com ';'. O adaptador só aceita ','.", strict=False)
def test_csv_com_ponto_e_virgula_do_excel_ptbr(tmp_path):
    """Excel: Salvar como > 'CSV (separado por vírgulas)' em Windows pt-BR."""
    arquivo = tmp_path / "excel_ptbr.csv"
    arquivo.write_text(CSV_PT.replace(",", ";"), encoding="utf-8")
    assert len(carregar_lote(arquivo).interacoes) == 2


@pytest.mark.xfail(reason="Excel antigo salva em Windows-1252. O adaptador só lê UTF-8.", strict=False)
def test_csv_em_windows_1252(tmp_path):
    arquivo = tmp_path / "excel_cp1252.csv"
    arquivo.write_text(CSV_PT, encoding="cp1252")
    assert carregar_lote(arquivo).interacoes[0].texto.endswith("Muito grata")


@pytest.mark.xfail(reason="A API ainda não aceita CSV: o adaptador não está ligado ao /processar.", strict=False)
def test_api_aceita_upload_de_csv():
    """Combinar com Marcelo o nome final do endpoint. Ajuste aqui quando estiver pronto."""
    r = cliente.post("/processar", files={"arquivo": ("lote.csv", CSV_PT.encode("utf-8"), "text/csv")})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 7. Serviços reais — rode com:  python -m pytest -m real -v
# ---------------------------------------------------------------------------
def _config_real() -> dict:
    """Junta o .env da raiz com as variáveis do terminal (o terminal tem prioridade)."""
    arquivo = {k: v for k, v in dotenv_values(RAIZ / ".env").items() if v}
    terminal = {k: v for k, v in os.environ.items() if k.startswith(("GEMINI_", "OCI_")) and v}
    return {**arquivo, **terminal}


@pytest.fixture
def gemini_real(monkeypatch):
    cfg = _config_real()
    if not cfg.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY não configurada no .env")
    if dotenv_values(RAIZ / ".env").get("LLM_MODO", "").lower() == "mock":
        pytest.skip("O .env tem LLM_MODO=mock. Apague essa linha para testar o Gemini.")
    for chave, valor in cfg.items():
        monkeypatch.setenv(chave, valor)
    monkeypatch.delenv("LLM_MODO", raising=False)
    monkeypatch.delenv("OCI_NAMESPACE", raising=False)  # este teste não sobe nada para a nuvem


@pytest.mark.real
def test_gemini_real_respeita_contrato(gemini_real):
    """O ponto mais frágil com o LLM real: ele precisa devolver JSON no formato combinado."""
    entrada = lote(
        ("Ana Teste", "#vagas", "depoimento", "Fui contratada como analista de dados júnior graças ao projeto do curso!"),
        ("Beto Teste", "#duvidas", "pergunta_tecnica", "Qual shape de VM é Always Free na OCI?"),
        ("Carla Teste", "#geral", "outro", "Estou muito frustrada, não consigo acompanhar e penso em desistir."),
    )
    assert cliente.get("/saude").json()["modo_llm"] == "gemini"

    r = cliente.post("/processar", json=entrada)
    assert r.status_code == 200, r.text
    corpo = r.json()
    RespostaProcessamento(**corpo)

    rotas = [a["rota"] for a in corpo["analises"]]
    print("\nRotas decididas pelo Gemini:", rotas)
    assert rotas[1] == "faq"
    assert rotas[2] == "alerta"
    assert corpo["analises"][0]["sentimento"] in ("Altamente Positivo", "Positivo")


@pytest.mark.real
def test_oci_real_salva_no_bucket(monkeypatch):
    """Sobe um pacote pequeno de teste para ativos/<ano>-semana-teste-integracao/ no bucket."""
    from app.storage import oci_configurado, salvar_pacote

    for chave, valor in _config_real().items():
        monkeypatch.setenv(chave, valor)
    if not oci_configurado():
        pytest.skip("OCI não configurado: faltam OCI_NAMESPACE no .env ou o arquivo ~/.oci/config")

    resultado = salvar_pacote({"teste": "integracao", "texto": TEXTO_ACENTUADO}, "Semana_teste_integracao")
    assert resultado["status"] == "salvo_com_sucesso", resultado
