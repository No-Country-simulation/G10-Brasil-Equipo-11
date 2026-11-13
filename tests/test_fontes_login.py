"""Testes dos seletores do lote (fonte, canal e mês) e do login do painel.

    python -m pytest tests/test_fontes_login.py -v
"""
import sys
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.storage import caminho_objeto  # noqa: E402
from ui import fontes, login  # noqa: E402


# ---------------------------------------------------------------------------
# Fonte, canal e mês
# ---------------------------------------------------------------------------
def test_fontes_na_ordem_combinada():
    assert list(fontes.CANAIS) == ["Discord", "Telegram", "WhatsApp", "Arquivo manual"]


def test_cada_fonte_tem_dois_canais_diferentes():
    for fonte, canais in fontes.CANAIS.items():
        assert len(canais) == 2 and len(set(canais)) == 2, fonte


def test_comunidade_junta_fonte_e_canal():
    assert fontes.comunidade("Discord", "Grupo ONE G10") == "Discord · Grupo ONE G10"


def test_periodo_do_mes_tem_ano_e_mes_com_dois_digitos():
    assert fontes.periodo(2026, 3) == "2026-03"
    assert fontes.periodo(2026, 11) == "2026-11"


def test_meses_em_portugues():
    assert fontes.nome_do_mes(1) == "Janeiro" and fontes.nome_do_mes(12) == "Dezembro"


def test_anos_terminam_no_ano_atual():
    anos = fontes.anos_disponiveis()
    assert anos[-1] == date.today().year and len(anos) == 3


def test_pacote_do_mes_vai_para_a_pasta_do_mes():
    assert caminho_objeto("2026-11") == "ativos/2026-11/pacote-distribuicao.json"


def test_pacote_da_semana_continua_com_o_ano_na_frente():
    assert caminho_objeto("Semana_04") == f"ativos/{date.today().year}-semana-04/pacote-distribuicao.json"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@pytest.fixture
def admin(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "admin")
    monkeypatch.setenv("ADMIN_SENHA", "segredo")


def test_login_aceita_o_admin(admin):
    assert login.confere("admin", "segredo")


def test_login_ignora_espacos_nas_pontas_do_usuario(admin):
    assert login.confere("  admin ", "segredo")


@pytest.mark.parametrize("usuario, senha", [("admin", "errada"), ("outro", "segredo"), ("", ""), ("admin", "")])
def test_login_recusa_o_resto(admin, usuario, senha):
    assert not login.confere(usuario, senha)


@pytest.mark.parametrize("usuario, senha", [("", "segredo"), ("admin", ""), ("", "")])
def test_sem_admin_configurado_ninguem_entra(monkeypatch, usuario, senha):
    monkeypatch.setenv("ADMIN_USUARIO", usuario)
    monkeypatch.setenv("ADMIN_SENHA", senha)
    assert not login.configurado()
    assert not login.confere(usuario, senha)
