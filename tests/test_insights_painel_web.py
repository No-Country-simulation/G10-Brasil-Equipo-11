"""Agregações da tela Insights do painel web (ui/insights.py), sem banco.

Rode com:  python -m pytest tests/test_insights_painel_web.py -v
"""
from datetime import date, timedelta

import pandas as pd

from ui import insights as ins

COLUNAS = ["lote_id", "data", "comunidade", "canal", "sentimento", "topico", "rota", "autor", "tipo"]


def df_de(linhas):
    return pd.DataFrame(linhas, columns=COLUNAS)


def msg(dia, canal="#geral", sentimento="Neutro", topico="Java", rota="nenhuma", autor="Ana", lote="L1"):
    return [lote, dia, "Comunidade", canal, sentimento, topico, rota, autor, "outro"]


D1, D3 = date(2026, 11, 1), date(2026, 11, 3)

EXEMPLO = df_de([
    msg(D1, sentimento="Positivo", rota="case_sucesso", autor="Ana"),
    msg(D1, sentimento="Altamente Negativo", canal="#suporte", topico="Prazo", rota="alerta", autor="Bia"),
    msg(D3, sentimento="Neutro", canal="#suporte", topico="Prazo", rota="faq", autor="Ana", lote="L2"),
    msg(D3, sentimento="Altamente Positivo", autor="Anônimo", lote="L2"),
])


def test_tempo_preenche_dias_sem_mensagem():
    t = ins.sentimento_no_tempo(EXEMPLO)
    assert t["granularidade"] == "dia"
    assert [p["inicio"] for p in t["pontos"]] == ["2026-11-01", "2026-11-02", "2026-11-03"]
    assert t["pontos"][1]["total"] == 0
    assert t["pontos"][0]["contagens"]["Altamente Negativo"] == 1
    assert sum(t["pontos"][2]["contagens"].values()) == t["pontos"][2]["total"] == 2


def test_periodo_longo_agrupa_por_semana_comecando_na_segunda():
    df = df_de([msg(date(2026, 8, 5)), msg(date(2026, 11, 4)), msg(date(2026, 11, 6))])
    t = ins.sentimento_no_tempo(df)
    assert t["granularidade"] == "semana"
    inicios = [date.fromisoformat(p["inicio"]) for p in t["pontos"]]
    assert all(d.weekday() == 0 for d in inicios)
    assert all(b - a == timedelta(days=7) for a, b in zip(inicios, inicios[1:]))
    assert t["pontos"][-1]["total"] == 2  # 04 e 06/11 caem na mesma semana
    assert sum(p["total"] for p in t["pontos"]) == 3


def test_canais_do_mais_critico_ao_mais_positivo():
    canais = ins.canais_sentimento(EXEMPLO)
    assert [c["canal"] for c in canais] == ["#suporte", "#geral"]
    suporte = canais[0]
    assert suporte["saldo"] == -50.0 and suporte["total"] == 2
    assert round(sum(suporte["percentuais"].values())) == 100


def test_topicos_trazem_o_tom_de_cada_um():
    topicos = ins.topicos_tom(EXEMPLO)
    assert topicos[0] == {"topico": "Java", "total": 2, "negativos": 0, "neutros": 0, "positivos": 2}
    assert topicos[1] == {"topico": "Prazo", "total": 2, "negativos": 1, "neutros": 1, "positivos": 0}


def test_atividade_dobra_canais_excedentes_em_outros():
    linhas = [msg(D1, canal=f"#c{i}") for i in range(10)] + [msg(D1, canal="#c0")]
    a = ins.atividade_canal_tempo(df_de(linhas))
    nomes = [linha["canal"] for linha in a["linhas"]]
    assert len(nomes) == ins.MAX_CANAIS_HEATMAP and nomes[0] == "#c0" and nomes[-1] == "Outros"
    assert sum(linha["total"] for linha in a["linhas"]) == 11
    assert a["maximo"] == 3  # "Outros" junta 3 canais com 1 mensagem cada


def test_resumo_e_membros():
    ativos = pd.DataFrame([["L1", "post", "POST_LINKEDIN", "aprovado"], ["L1", "faq_0", "FAQ", "pendente"],
                           ["L2", "faq_1", "FAQ", "descartado"]], columns=["lote_id", "chave", "tipo", "status"])
    alertas = [{"status": "PENDENTE"}, {"status": "RESOLVIDO"}]
    r = ins.resumo(EXEMPLO, ativos, alertas)
    assert (r["interacoes"], r["lotes"], r["canais"]) == (4, 2, 2)
    assert (r["pct_positivas"], r["pct_negativas"], r["saldo"]) == (50.0, 25.0, 25.0)
    assert (r["alertas_total"], r["alertas_abertos"]) == (2, 1)
    assert (r["ativos_gerados"], r["ativos_aprovados"], r["taxa_aprovacao"]) == (3, 1, 33.3)

    tipos = {t["tipo"]: t for t in ins.aproveitamento_por_tipo(ativos)}
    assert tipos["faq"] == {"tipo": "faq", "nome": "FAQ", "total": 2, "aprovados": 0, "pendentes": 1, "descartados": 1}

    membros = ins.membros_engajados(EXEMPLO)
    assert [m["autor"] for m in membros] == ["Ana", "Bia"]  # anônimo fica de fora
    assert membros[0] == {"autor": "Ana", "total": 2, "positivos": 1, "negativos": 0, "cases": 1}


def test_fila_de_alertas_abertos_do_mais_antigo():
    alertas = [
        {"status": "PENDENTE", "data": date(2026, 11, 5), "canal": "#b", "autor": "B", "motivo": "x" * 300, "lote_id": "L"},
        {"status": "RESOLVIDO", "data": date(2026, 11, 1)},
        {"status": "PENDENTE", "data": date(2026, 11, 2), "canal": "#a", "autor": "A", "motivo": "m", "lote_id": "L"},
    ]
    t = ins.alertas_triagem(alertas, limite=1)
    assert t["por_estado"] == {"PENDENTE": 2, "ENCAMINHADO": 0, "RESOLVIDO": 1}
    assert [a["canal"] for a in t["abertos"]] == ["#a"] and t["abertos_restantes"] == 1
    assert len(ins.alertas_triagem(alertas)["abertos"][1]["motivo"]) == 180


def test_tudo_vazio_nao_quebra():
    vazio = df_de([])
    assert ins.sentimento_no_tempo(vazio) == {"granularidade": "dia", "pontos": []}
    assert ins.canais_sentimento(vazio) == ins.topicos_tom(vazio) == ins.membros_engajados(vazio) == []
    assert ins.atividade_canal_tempo(vazio)["maximo"] == 0
    assert ins.resumo(vazio, pd.DataFrame(columns=["status"]), [])["taxa_aprovacao"] == 0.0
    assert ins.alertas_triagem([])["total"] == 0
