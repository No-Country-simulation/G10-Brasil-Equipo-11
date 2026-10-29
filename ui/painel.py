"""Painel de curadoria do CommunityLab, seguindo a prévia aprovada pela equipe.

Três telas: Importar → Visão geral → Curadoria.

Rode da raiz do projeto com:  python -m streamlit run ui/painel.py
"""
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
for caminho in (RAIZ, RAIZ / "src"):
    if str(caminho) not in sys.path:
        sys.path.insert(0, str(caminho))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ / ".env")

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app import repositorio  # noqa: E402
from app.grafo import processar_com_registro  # noqa: E402
from app.llm import modo_mock  # noqa: E402
from ui import curadoria as cur  # noqa: E402
from ui.estilo import (  # noqa: E402
    AZUL, AZUL_ESCURO, LARANJA_ESCURO, MARCA_SVG, ROTAS, aplicar_estilo, barra_sentimento,
    barras_rotas, esc, selo,
)
from ui.importacao import ler_arquivo  # noqa: E402

TELAS = ["Importar", "Visão geral", "Curadoria"]
EXEMPLO = RAIZ / "data" / "interacoes_exemplo.json"

st.set_page_config(page_title="CommunityLab", page_icon="📣", layout="wide")
aplicar_estilo()
ss = st.session_state


# ---------------------------------------------------------------------------
# Estado e navegação
# ---------------------------------------------------------------------------
def iniciar_estado():
    padrao = {
        "pagina": "Importar", "leitura": None, "arquivo_id": None, "resultado": None,
        "processado_em": None, "decisoes": {}, "alertas": {}, "exportado": None,
        "origem": "", "periodo": "", "lote_origem": "", "lote_periodo": "",
        "lote_id": None, "aviso_banco": None, "duplicado": None,
    }
    for chave, valor in padrao.items():
        ss.setdefault(chave, valor)
    if "_ir_para" in ss:  # trocar de tela por código precisa acontecer antes do seletor existir
        ss["pagina"] = ss.pop("_ir_para")
    if ss["pagina"] != "Importar":  # fora da tela, o Streamlit apagaria o que foi digitado nos campos do lote
        ss["origem"], ss["periodo"] = ss["origem"], ss["periodo"]


def ir_para(tela: str):
    ss["_ir_para"] = tela
    st.rerun()


def pendentes() -> int:
    return cur.resumo(ss["decisoes"])["pendentes"] if ss["decisoes"] else 0


def cabecalho():
    c1, c2, c3 = st.columns([2, 4, 3], vertical_alignment="center")
    c1.markdown(f'<div class="cl-marca">{MARCA_SVG}CommunityLab</div>', unsafe_allow_html=True)
    c2.container(key="nav").radio("Seção", TELAS, key="pagina", horizontal=True, label_visibility="collapsed")
    modo = selo("Modo simulado", "#FFF6EC", "#8A3A0B", "#D8B48A") if modo_mock() else selo("Gemini", "#E8EEFB", AZUL_ESCURO, "#C6D3F3")
    contexto = ""
    if ss["resultado"]:
        contexto = f'<span class="cl-mono">{esc(ss["lote_origem"])} · {esc(ss["lote_periodo"])}</span>'
        if pendentes():
            contexto += selo(f"{pendentes()} pendentes", AZUL, "#FFFFFF")
    c3.markdown(f'<div class="cl-contexto">{contexto}{modo}</div>', unsafe_allow_html=True)
    st.divider()


def sem_lote():
    st.info("Nenhum lote processado ainda. Comece importando as interações da semana.")
    if st.button("Ir para Importar", type="primary"):
        ir_para("Importar")


# ---------------------------------------------------------------------------
# Tela 1 — Importar
# ---------------------------------------------------------------------------
def limpar_chaves_do_lote():
    for chave in [k for k in ss.keys() if str(k).startswith(("txt_", "dec_", "al_"))]:
        del ss[chave]


def processar_lote(lote, substituir: bool = False):
    lote = lote.model_copy(update={
        "origem_comunidade": ss["origem"].strip() or lote.origem_comunidade,
        "periodo_referencia": ss["periodo"].strip() or lote.periodo_referencia,
    })
    ss["duplicado"], ss["aviso_banco"] = None, None
    if repositorio.banco_configurado() and not substituir:
        try:
            existente = repositorio.buscar_lote(repositorio.hash_conteudo(lote), repositorio.modo_atual())
        except Exception as e:
            existente = None
            ss["aviso_banco"] = f"Não foi possível verificar o histórico: {e}"
        if existente:
            ss["duplicado"] = existente
            st.rerun()
    with st.spinner("Analisando a comunidade e gerando os ativos..."):
        resultado, registro = processar_com_registro(lote)
    limpar_chaves_do_lote()
    ss.update({
        "resultado": resultado, "processado_em": datetime.now(), "autorizado": False,
        "decisoes": {i: cur.PENDENTE for i in cur.ids_dos_ativos(resultado)},
        "alertas": {}, "exportado": None,
        "lote_origem": lote.origem_comunidade, "lote_periodo": lote.periodo_referencia,
        "lote_id": registro["lote_id"],
    })
    if registro["erro"]:
        ss["aviso_banco"] = f"O resultado não foi salvo no histórico: {registro['erro']}"
    ir_para("Visão geral")


def abrir_lote(lote_id: int):
    """Reabre um lote do histórico do jeito que ficou (decisões, textos editados e alertas), sem chamar a IA."""
    salvo = repositorio.carregar_lote(lote_id)
    limpar_chaves_do_lote()
    ss.update({
        "resultado": salvo["resposta"], "processado_em": salvo["processado_em"].astimezone(),
        "autorizado": salvo["autorizado"], "decisoes": salvo["decisoes"], "alertas": salvo["alertas"],
        "exportado": None, "lote_origem": salvo["origem"], "lote_periodo": salvo["periodo"],
        "lote_id": lote_id, "aviso_banco": None,
    })
    for campo, texto in salvo["textos"].items():
        ss[f"txt_{campo}"] = texto
    ir_para("Visão geral")


def mostrar_leitura(leitura):
    with st.container(border=True):
        a, b = st.columns([4, 2], vertical_alignment="center")
        a.markdown(f'<div class="cl-mono" style="font-weight:600">{esc(leitura.nome)}</div>'
                   f'<div style="font-size:13px;color:#555D6B">{esc(leitura.detalhe)}</div>', unsafe_allow_html=True)
        if leitura.ok:
            b.markdown(f'<div style="text-align:right">{selo("Pronto para processar", "#E8EEFB", AZUL_ESCURO)}</div>', unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Linhas lidas", leitura.total)
            m2.metric("Com erro", 0)
            m3.metric("Sem autor (anônimas)", leitura.anonimas)
            previa = pd.DataFrame([i.model_dump() for i in leitura.lote.interacoes[:5]])
            st.dataframe(previa[["autor", "canal", "tipo", "texto"]], hide_index=True, width="stretch")
            st.caption(f"Mostrando {min(5, leitura.total)} de {leitura.total} linhas.")
        else:
            b.markdown(f'<div style="text-align:right">{selo("Precisa de ajuste", "#FCEBDF", LARANJA_ESCURO)}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="cl-alerta"><b style="color:{LARANJA_ESCURO}">{esc(leitura.titulo_erro)}</b>'
                f'<p style="margin:6px 0 0">{esc(leitura.explicacao)}</p></div>', unsafe_allow_html=True)
            if leitura.passos:
                st.markdown("**Como resolver**\n\n" + "\n".join(f"{n}. {p}" for n, p in enumerate(leitura.passos, 1)))
            if leitura.evidencia:
                st.code(leitura.evidencia, language=None)


def tela_importar():
    st.title("Importar interações")
    st.markdown('<p class="cl-sub">Envie as mensagens da semana. O pipeline classifica cada uma e gera os ativos para você revisar.</p>',
                unsafe_allow_html=True)
    esquerda, direita = st.columns([3, 2], gap="large")

    with esquerda:
        arquivo = st.file_uploader("Arquivo JSON ou CSV (colunas autor, canal, tipo e texto)", type=["json", "csv"])
        if st.button("Usar lote de exemplo"):
            ss["leitura"] = ler_arquivo(EXEMPLO.name, EXEMPLO.read_bytes())
            ss["arquivo_id"], ss["duplicado"] = "exemplo", None
            ss["origem"], ss["periodo"] = ss["leitura"].lote.origem_comunidade, ss["leitura"].lote.periodo_referencia
        elif arquivo is not None and arquivo.file_id != ss["arquivo_id"]:
            ss["leitura"] = ler_arquivo(arquivo.name, arquivo.getvalue())
            ss["arquivo_id"], ss["duplicado"] = arquivo.file_id, None
            if ss["leitura"].ok:
                ss["origem"], ss["periodo"] = ss["leitura"].lote.origem_comunidade, ss["leitura"].lote.periodo_referencia
        if ss["leitura"]:
            mostrar_leitura(ss["leitura"])

    with direita:
        leitura = ss["leitura"]
        with st.container(border=True):
            st.subheader("Dados do lote")
            st.text_input("Comunidade de origem", key="origem", placeholder="Ex.: Discord_Grupo_ONE_G10")
            st.text_input("Período de referência", key="periodo", placeholder="Ex.: Semana_04")
            if ss["periodo"].strip():
                st.caption(f"O pacote será salvo em `ativos/{datetime.now().year}-{ss['periodo'].strip().lower().replace('_', '-')}/`")
            pronto = bool(leitura and leitura.ok)
            rotulo = f"Processar {leitura.total} interações" if pronto else "Envie um arquivo válido para processar"
            if st.button(rotulo, type="primary", disabled=not pronto, width="stretch"):
                processar_lote(leitura.lote)
            existente = ss["duplicado"]
            if existente and pronto:
                quando = existente["processado_em"].astimezone().strftime("%d/%m às %H:%M")
                st.warning(f"Este conteúdo já foi processado em {quando} ({existente['total_interacoes']} interações).")
                abrir, substituir = st.columns(2)
                if abrir.button("Abrir resultado existente", width="stretch"):
                    ss["duplicado"] = None
                    abrir_lote(existente["id"])
                if substituir.button("Processar de novo e substituir", width="stretch"):
                    ss["duplicado"] = None
                    processar_lote(leitura.lote, substituir=True)
        with st.container(border=True):
            st.markdown("**Antes de enviar**")
            st.markdown("Use nomes reais só de quem autorizou. Depoimentos podem virar posts públicos.\n\n"
                        "Mensagens sem autor entram como anônimas.")


# ---------------------------------------------------------------------------
# Tela 2 — Visão geral
# ---------------------------------------------------------------------------
ACOES_ALERTA = {"reclamacao": "Encaminhar ao time de conteúdo"}


def tela_visao_geral():
    if ss["aviso_banco"]:
        st.warning(ss["aviso_banco"])
    r = ss["resultado"]
    if not r:
        st.title("Saúde da comunidade")
        sem_lote()
        return
    analises = r["analises"]
    ativos = r["ativos_distribuicao_gerados"]

    topo, botao = st.columns([4, 1], vertical_alignment="bottom")
    with topo:
        st.title("Saúde da comunidade")
        quando = ss["processado_em"].strftime("%d/%m às %H:%M") if ss["processado_em"] else ""
        st.markdown(f'<p class="cl-sub">{len(analises)} interações processadas em {quando}</p>', unsafe_allow_html=True)
    if pendentes() and botao.button(f"Revisar {pendentes()} ativos", type="primary", width="stretch"):
        ir_para("Curadoria")

    alertas = [a for a in analises if a["rota"] == "alerta"]
    abertos = [a for a in alertas if a["autor"] not in ss["alertas"]]
    n_faq = len(ativos.get("sugestao_conteudo_faq") or [])
    partes = (["1 post"] if ativos.get("post_linkedin") else []) + \
             (["1 newsletter"] if ativos.get("destaque_newsletter_semanal") else []) + ([f"{n_faq} FAQ"] if n_faq else [])
    armaz = r["armazenamento_oci"]
    status_pacote = {"salvo_localmente": "Salvo localmente", "salvo_com_sucesso": "Salvo na OCI", "erro": "Erro ao salvar"}

    k1, k2, k3, k4 = st.columns(4)
    with k1.container(border=True):
        st.metric("Interações processadas", len(analises))
        st.caption(f"de {len({a['autor'] for a in analises})} pessoas · {len({a['canal'] for a in analises})} canais")
    with k2.container(border=True):
        st.metric("Ativos para aprovar", pendentes())
        st.caption(" · ".join(partes) or "nenhum ativo gerado")
    with k3.container(border=True):
        st.metric("Membros que precisam de apoio", len(abertos))
        st.caption(f"{len(alertas) - len(abertos)} já tratados" if len(abertos) < len(alertas) else "sentimento negativo ou reclamação")
    with k4.container(border=True):
        cor = LARANJA_ESCURO if armaz["status"] == "erro" else AZUL_ESCURO
        st.markdown(f'<div class="cl-kpi-rotulo">Pacote de distribuição</div>'
                    f'<div class="cl-kpi-valor" style="color:{cor}">{esc(status_pacote.get(armaz["status"], armaz["status"]))}</div>',
                    unsafe_allow_html=True)
        st.caption(f"`{armaz['caminho_objeto']}`")

    s1, s2 = st.columns(2)
    with s1.container(border=True):
        st.subheader("Sentimento")
        st.caption(f"Predominante: {r['resumo_comunidade']['sentimento_predominante'].lower()}.")
        st.markdown(barra_sentimento(Counter(a["sentimento"] for a in analises)), unsafe_allow_html=True)
    with s2.container(border=True):
        st.subheader("Para onde foi cada mensagem")
        st.caption("Rota decidida pelo pipeline.")
        st.markdown(barras_rotas(Counter(a["rota"] for a in analises)), unsafe_allow_html=True)

    if alertas:
        with st.container(border=True):
            st.subheader("Membros que precisam de apoio")
            st.caption("Não viram conteúdo. Vão para o time de comunidade decidir o contato.")
            colunas = st.columns(min(len(alertas), 2))
            for i, a in enumerate(alertas):
                with colunas[i % len(colunas)].container(border=True):
                    st.markdown(f'**{esc(a["autor"])}** <span class="cl-mono" style="font-size:13px;color:#555D6B">{esc(a["canal"])}</span>',
                                unsafe_allow_html=True)
                    st.markdown(f'<div class="cl-alerta">“{esc(a["texto"])}”</div>', unsafe_allow_html=True)
                    feito = ss["alertas"].get(a["autor"])
                    if feito:
                        st.markdown(selo(feito, "#E8EEFB", AZUL_ESCURO), unsafe_allow_html=True)
                    else:
                        b1, b2 = st.columns(2)
                        acao = ACOES_ALERTA.get(a["tipo"], "Oferecer mentoria")
                        if b1.button(acao, key=f"al_{i}_acao", width="stretch"):
                            ss["alertas"][a["autor"]] = "Encaminhado" if a["tipo"] == "reclamacao" else "Mentoria oferecida"
                            st.rerun()
                        if b2.button("Marcar como resolvido", key=f"al_{i}_ok", width="stretch"):
                            ss["alertas"][a["autor"]] = "Resolvido"
                            st.rerun()

    with st.container(border=True):
        cab, filtro_col = st.columns([2, 3], vertical_alignment="bottom")
        cab.subheader("Interações analisadas")
        opcoes = ["Todas"] + [ROTAS[k]["nome"] for k in ROTAS]
        filtro = filtro_col.container(key="filtro").radio("Filtrar por rota", opcoes, horizontal=True, key="filtro_rota")
        nome_para_rota = {v["nome"]: k for k, v in ROTAS.items()}
        linhas = [a for a in analises if filtro == "Todas" or a["rota"] == nome_para_rota[filtro]]
        linhas.sort(key=lambda a: a["relevancia"], reverse=True)
        tabela = pd.DataFrame([{
            "Autor": a["autor"], "Canal": a["canal"], "Mensagem": a["texto"], "Sentimento": a["sentimento"],
            "Relevância": a["relevancia"], "Rota": ROTAS[a["rota"]]["nome"],
        } for a in linhas])
        if tabela.empty:
            st.caption("Nenhuma mensagem nesta rota.")
        else:
            st.dataframe(tabela, hide_index=True, width="stretch", column_config={
                "Mensagem": st.column_config.TextColumn(width="large"),
                "Relevância": st.column_config.ProgressColumn(min_value=0, max_value=10, format="%d/10"),
            })


# ---------------------------------------------------------------------------
# Tela 3 — Curadoria
# ---------------------------------------------------------------------------
def botoes_decisao(id_ativo: str, rotulo_aprovar: str, bloqueado: bool = False):
    decisao = ss["decisoes"].get(id_ativo, cur.PENDENTE)
    _, area = st.columns([2, 3])
    if decisao == cur.PENDENTE:
        d, a = area.columns(2)
        if d.button("Descartar", key=f"dec_{id_ativo}_d", width="stretch"):
            ss["decisoes"][id_ativo] = cur.DESCARTADO
            st.rerun()
        if a.button(rotulo_aprovar, key=f"dec_{id_ativo}_a", type="primary", disabled=bloqueado, width="stretch"):
            ss["decisoes"][id_ativo] = cur.APROVADO
            st.rerun()
    else:
        s, u = area.columns(2, vertical_alignment="center")
        texto = "Aprovado" if decisao == cur.APROVADO else "Descartado"
        cores = ("#E8EEFB", AZUL_ESCURO) if decisao == cur.APROVADO else ("#EEF1F6", "#555D6B")
        s.markdown(f'<div style="text-align:right">{selo(texto, *cores)}</div>', unsafe_allow_html=True)
        if u.button("Desfazer", key=f"dec_{id_ativo}_u", width="stretch"):
            ss["decisoes"][id_ativo] = cur.PENDENTE
            st.rerun()


def inicial(chave: str, texto: str):
    """Valor padrão do campo; None quando o texto já está no estado (ex.: lote reaberto do histórico)."""
    return None if chave in ss else texto


def textos_editados() -> dict:
    return {k.removeprefix("txt_"): v for k, v in ss.items() if str(k).startswith("txt_")}


def tela_curadoria():
    r = ss["resultado"]
    if not r:
        st.title("Curadoria")
        sem_lote()
        return
    ativos = r["ativos_distribuicao_gerados"]
    principal, lateral = st.columns([7, 3], gap="large")

    with principal:
        st.title("Curadoria")
        st.markdown('<p class="cl-sub">Rascunhos gerados pela IA a partir das mensagens da semana. '
                    'Nada é publicado sem a sua aprovação.</p>', unsafe_allow_html=True)

        post = ativos.get("post_linkedin")
        if post:
            membro = cur.membro_do_post(r)
            with st.container(border=True):
                st.markdown(f'{selo("Post · LinkedIn oficial", "#E8EEFB", AZUL_ESCURO)} '
                            f'<span style="float:right;font-size:13px;color:#555D6B">Engajamento previsto: '
                            f'<b>{esc(post["potencial_engajamento"]).lower()}</b></span>', unsafe_allow_html=True)
                st.subheader(post["titulo"])
                t, o = st.columns([3, 2], gap="medium")
                t.text_area("Texto do post (editável)", value=inicial("txt_post_copy", post["copy"]), key="txt_post_copy", height=280)
                if membro:
                    o.markdown('<div class="cl-rotulo">Mensagem original</div>', unsafe_allow_html=True)
                    o.markdown(f'<div class="cl-citacao">“{esc(membro["texto"])}”</div>', unsafe_allow_html=True)
                    o.caption(f'{membro["autor"]} · {membro["canal"]} · relevância {membro["relevancia"]}/10')
                    outros = cur.outros_cases(r)
                    if outros:
                        o.caption("Outros candidatos a case: " + ", ".join(f'{a["autor"]} ({a["relevancia"]}/10)' for a in outros))
                nome = membro["autor"].split()[0] if membro else "O membro"
                autorizado = st.checkbox(f"{nome} autorizou o uso do nome e do depoimento", key="autorizado")
                if not autorizado and ss["decisoes"].get("post") == cur.APROVADO:
                    ss["decisoes"]["post"] = cur.PENDENTE  # sem autorização, o post volta para pendente
                botoes_decisao("post", "Aprovar post", bloqueado=not autorizado)
                if not autorizado and ss["decisoes"].get("post") == cur.PENDENTE:
                    st.caption("Marque a autorização para liberar a aprovação.")

        news = ativos.get("destaque_newsletter_semanal")
        if news:
            with st.container(border=True):
                st.markdown(selo("Newsletter semanal", "#EEF1F6", "#33373F"), unsafe_allow_html=True)
                st.subheader(news["secao"])
                st.text_input("Chamada", value=inicial("txt_news_chamada", news["chamada"]), key="txt_news_chamada")
                st.text_area("Resumo", value=inicial("txt_news_resumo", news["resumo"]), key="txt_news_resumo", height=110)
                botoes_decisao("newsletter", "Aprovar destaque")

        faqs = ativos.get("sugestao_conteudo_faq") or []
        if faqs:
            st.subheader("Dicas rápidas para a mentoria")
            st.caption(f"{len(faqs)} dúvidas viraram rascunhos de FAQ.")
            for i, faq in enumerate(faqs):
                with st.container(border=True):
                    st.markdown(f"**{esc(faq['tema'])}**")
                    st.text_area("Conteúdo", value=inicial(f"txt_faq_{i}_conteudo", faq["conteudo"]), key=f"txt_faq_{i}_conteudo", height=110,
                                 label_visibility="collapsed")
                    duvida = cur.duvida_da_faq(r, i)
                    if duvida:
                        st.caption(f'Dúvida original de {duvida["autor"]} em {duvida["canal"]}: “{duvida["texto"]}”')
                    botoes_decisao(f"faq_{i}", "Enviar à mentoria")

    with lateral:
        res = cur.resumo(ss["decisoes"])
        with st.container(border=True):
            st.subheader("Revisão da semana")
            fracao = res["revisados"] / res["total"] if res["total"] else 0
            st.progress(fracao, text=f'{res["revisados"]} de {res["total"]} revisados')
            a, d, p = st.columns(3)
            a.metric("Aprovados", res["aprovados"])
            d.metric("Descartados", res["descartados"])
            p.metric("Pendentes", res["pendentes"])
            if st.button("Exportar aprovados", type="primary", disabled=res["aprovados"] == 0, width="stretch"):
                pacote = cur.montar_aprovados(r, ss["decisoes"], textos_editados(), ss["lote_origem"], ss["lote_periodo"],
                                              autorizado=bool(ss.get("autorizado")))
                destino = cur.salvar_aprovados(pacote)
                ss["exportado"] = (str(destino), json.dumps(pacote, ensure_ascii=False, indent=2))
            if ss["exportado"]:
                caminho, conteudo = ss["exportado"]
                st.success(f"Salvo em `{caminho}`")
                st.download_button("Baixar aprovados.json", conteudo, file_name="aprovados.json",
                                   mime="application/json", width="stretch")
        with st.container(border=True):
            st.markdown("**Antes de aprovar**")
            st.markdown("Confira se o texto não afirma nada que a mensagem original não diz.\n\n"
                        "Posts com nome de membro só saem com a autorização marcada.")


# ---------------------------------------------------------------------------
iniciar_estado()
cabecalho()
{"Importar": tela_importar, "Visão geral": tela_visao_geral, "Curadoria": tela_curadoria}[ss["pagina"]]()
