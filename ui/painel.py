"""Painel de curadoria do Sender AI.

Tela de login (um admin, do .env) e quatro telas: Importar → Visão geral → Curadoria, mais Insights (histórico).

Rode da raiz do projeto com:  python -m streamlit run ui/painel.py
"""
import json
import sys
from collections import Counter
from datetime import date, datetime
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
from app.llm import modo_mock  # noqa: E402
from ui import curadoria as cur  # noqa: E402
from ui import fontes, login  # noqa: E402
from ui.estilo import (  # noqa: E402
    CIANO, CINZA, ICONE, LARANJA, LIMA_FUNDO, LIMA_TINTA, ROTAS, SELO_AVISO, SELO_INFO, SELO_NEUTRO, SELO_SUCESSO,
    aplicar_estilo, barra_sentimento, barras_rotas, esc, logo_html, selo,
)
from ui.importacao import ler_arquivo  # noqa: E402
from ui.tela_insights import tela_insights  # noqa: E402

TELAS = ["Importar", "Visão geral", "Curadoria", "Insights"]
EXEMPLO = RAIZ / "data" / "interacoes_exemplo.json"

st.set_page_config(page_title="Sender AI", page_icon=str(ICONE), layout="wide")
aplicar_estilo()
ss = st.session_state


# ---------------------------------------------------------------------------
# Estado e navegação
# ---------------------------------------------------------------------------
def iniciar_estado():
    padrao = {
        "pagina": "Importar", "leitura": None, "arquivo_id": None, "resultado": None,
        "processado_em": None, "decisoes": {}, "alertas": {}, "exportado": None,
        "fonte": None, "canal": None, "mes": date.today().month, "ano": date.today().year,
        "lote_origem": "", "lote_periodo": "", "logado": False,
        "lote_id": None, "aviso_banco": None, "duplicado": None, "item_ativo": None,
    }
    for chave, valor in padrao.items():
        ss.setdefault(chave, valor)
    if "_ir_para" in ss:  # trocar de tela por código precisa acontecer antes do seletor existir
        ss["pagina"] = ss.pop("_ir_para")
    if ss["pagina"] != "Importar":  # fora da tela, o Streamlit apagaria o que foi escolhido nos campos do lote
        for chave in CAMPOS_DO_LOTE:
            ss[chave] = ss[chave]
    if ss["resultado"]:
        ids = cur.ids_dos_ativos(ss["resultado"])
        if ss["item_ativo"] not in ids:
            ss["item_ativo"] = cur.proximo_pendente(ids, ss["decisoes"]) or (ids[0] if ids else None)
    # A fila mostra um item por vez. Fora da tela, o Streamlit apagaria os textos editados e a autorização
    # dos outros itens, e a exportação voltaria em silêncio ao texto gerado.
    na_tela = cur.campos_do_ativo(ss["item_ativo"]) if ss["pagina"] == "Curadoria" else ()
    for chave in [k for k in ss.keys() if str(k).startswith("txt_") or k == "autorizado"]:
        if chave not in na_tela:
            ss[chave] = ss[chave]


CAMPOS_DO_LOTE = ("fonte", "canal", "mes", "ano")


def ir_para(tela: str):
    ss["_ir_para"] = tela
    st.rerun()


def pendentes() -> int:
    return cur.resumo(ss["decisoes"])["pendentes"] if ss["decisoes"] else 0


def sair():
    ss.clear()  # volta para o login com o painel zerado, como numa sessão nova


def cabecalho():
    c1, c2, c3, c4 = st.columns([2, 4, 3, 1], vertical_alignment="center")
    c1.markdown(logo_html(), unsafe_allow_html=True)
    c2.container(key="nav").radio("Seção", TELAS, key="pagina", horizontal=True, label_visibility="collapsed")
    modo = selo("Modo simulado", *SELO_AVISO) if modo_mock() else selo("Gemini", *SELO_INFO)
    contexto = ""
    if ss["resultado"]:
        origem_amigavel = esc(ss["lote_origem"]).replace("_", " ")
        contexto = f'<span class="cl-origem-badge">📡 {origem_amigavel} · {esc(ss["lote_periodo"])}</span>'
        if pendentes():
            contexto += selo(f"{pendentes()} pendentes", LIMA_FUNDO, LIMA_TINTA)
    c3.markdown(f'<div class="cl-contexto">{contexto}{modo}</div>', unsafe_allow_html=True)
    c4.button("Sair", icon=":material/logout:", on_click=sair, width="stretch")
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
    ss["item_ativo"] = None


def processar_lote(lote, substituir: bool = False):
    lote = lote.model_copy(update={
        "origem_comunidade": fontes.comunidade(ss["fonte"], ss["canal"]),
        "periodo_referencia": fontes.periodo(ss["ano"], ss["mes"]),
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
        from app.grafo import processar_com_registro  # o LangGraph leva segundos para importar: só quando processar
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
    try:
        salvo = repositorio.carregar_lote(lote_id)
    except Exception as e:
        st.warning(f"Não foi possível abrir o resultado salvo: {e}")
        return
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
                   f'<div style="font-size:13px;color:{CINZA}">{esc(leitura.detalhe)}</div>', unsafe_allow_html=True)
        if leitura.ok:
            b.markdown(f'<div style="text-align:right">{selo("Pronto para processar", *SELO_SUCESSO)}</div>', unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Linhas lidas", leitura.total)
            m2.metric("Com erro", 0)
            m3.metric("Sem autor (anônimas)", leitura.anonimas)
            previa = pd.DataFrame([i.model_dump() for i in leitura.lote.interacoes[:5]])
            st.dataframe(previa[["autor", "canal", "tipo", "texto"]], hide_index=True, width="stretch")
            st.caption(f"Mostrando {min(5, leitura.total)} de {leitura.total} linhas.")
        else:
            b.markdown(f'<div style="text-align:right">{selo("Precisa de ajuste", *SELO_AVISO)}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="cl-alerta"><b style="color:{LARANJA}">{esc(leitura.titulo_erro)}</b>'
                f'<p style="margin:6px 0 0">{esc(leitura.explicacao)}</p></div>', unsafe_allow_html=True)
            if leitura.passos:
                st.markdown("**Como resolver**\n\n" + "\n".join(f"{n}. {p}" for n, p in enumerate(leitura.passos, 1)))
            if leitura.evidencia:
                st.code(leitura.evidencia, language=None)


def descartar_duplicado():  # fonte, canal e mês mudam o lote, então o aviso de duplicado deixa de valer
    ss["duplicado"] = None


def trocar_fonte():
    ss["canal"] = None  # os canais são de cada fonte
    descartar_duplicado()


def campos_do_lote():
    st.selectbox("Fonte dos dados", list(fontes.CANAIS), key="fonte", index=None,
                 placeholder="Escolha a fonte", on_change=trocar_fonte)
    if ss["fonte"]:
        st.selectbox("Canal", fontes.CANAIS[ss["fonte"]], key="canal", index=None,
                     placeholder="Escolha o canal", on_change=descartar_duplicado)
    mes, ano = st.columns(2)
    mes.selectbox("Mês de referência", list(range(1, 13)), key="mes", format_func=fontes.nome_do_mes,
                  on_change=descartar_duplicado)
    ano.selectbox("Ano", fontes.anos_disponiveis(), key="ano", on_change=descartar_duplicado)
    st.caption(f"O pacote será salvo em `ativos/{fontes.periodo(ss['ano'], ss['mes'])}/`")


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
        elif arquivo is not None and arquivo.file_id != ss["arquivo_id"]:
            ss["leitura"] = ler_arquivo(arquivo.name, arquivo.getvalue())
            ss["arquivo_id"], ss["duplicado"] = arquivo.file_id, None
        if ss["leitura"]:
            mostrar_leitura(ss["leitura"])

    with direita:
        leitura = ss["leitura"]
        with st.container(border=True):
            st.subheader("Dados do lote")
            campos_do_lote()
            pronto = bool(leitura and leitura.ok and ss["fonte"] and ss.get("canal"))
            if not (leitura and leitura.ok):
                rotulo = "Envie um arquivo válido para processar"
            elif not pronto:
                rotulo = "Escolha a fonte e o canal para processar"
            else:
                rotulo = f"Processar {leitura.total} interações"
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


def tratar_alerta(ordem: int, status: str):
    ss["alertas"][ordem] = status
    if ss["lote_id"]:
        try:
            repositorio.atualizar_alerta(ss["lote_id"], ordem, status)
            ss["aviso_banco"] = None
        except Exception as e:
            ss["aviso_banco"] = f"O status do alerta não foi salvo no histórico: {e}"
            if isinstance(e, LookupError):
                ss["lote_id"] = None
    st.rerun()


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

    alertas = [(ordem, a) for ordem, a in enumerate(analises) if a["rota"] == "alerta"]
    abertos = [a for ordem, a in alertas if ordem not in ss["alertas"]]
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
        cor = LARANJA if armaz["status"] == "erro" else CIANO
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
            for i, (ordem, a) in enumerate(alertas):
                with colunas[i % len(colunas)].container(border=True):
                    st.markdown(f'**{esc(a["autor"])}** <span class="cl-mono" style="font-size:13px;color:{CINZA}">{esc(a["canal"])}</span>',
                                unsafe_allow_html=True)
                    st.markdown(f'<div class="cl-alerta">“{esc(a["texto"])}”</div>', unsafe_allow_html=True)
                    feito = ss["alertas"].get(ordem)
                    if feito:
                        st.markdown(selo(cur.STATUS_ALERTA.get(feito, feito), *SELO_INFO), unsafe_allow_html=True)
                    else:
                        b1, b2 = st.columns(2)
                        acao = ACOES_ALERTA.get(a["tipo"], "Oferecer mentoria")
                        if b1.button(acao, key=f"al_{i}_acao", width="stretch"):
                            tratar_alerta(ordem, "encaminhado" if a["tipo"] == "reclamacao" else "mentoria_oferecida")
                        if b2.button("Marcar como resolvido", key=f"al_{i}_ok", width="stretch"):
                            tratar_alerta(ordem, "resolvido")

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
def decidir(id_ativo: str, decisao: str):
    """Guarda a decisão no estado e, se o lote está no histórico, no banco (com os textos editados do ativo)."""
    ss["decisoes"][id_ativo] = decisao
    if ss["lote_id"]:
        try:
            repositorio.salvar_decisao(ss["lote_id"], id_ativo, decisao, cur.textos_do_ativo(id_ativo, textos_editados()),
                                       autorizacao=bool(ss.get("autorizado")))
            ss["aviso_banco"] = None
        except Exception as e:
            ss["aviso_banco"] = f"A decisão não foi salva no histórico: {e}"
            if isinstance(e, LookupError):
                ss["lote_id"] = None


def botoes_decisao(id_ativo: str, rotulo_aprovar: str, bloqueado: bool = False):
    decisao = ss["decisoes"].get(id_ativo, cur.PENDENTE)
    _, area = st.columns([2, 3])
    if decisao == cur.PENDENTE:
        d, a = area.columns(2)
        escolha = None
        if d.button("Descartar", key=f"dec_{id_ativo}_d", width="stretch"):
            escolha = cur.DESCARTADO
        if a.button(rotulo_aprovar, key=f"dec_{id_ativo}_a", type="primary", disabled=bloqueado, width="stretch"):
            escolha = cur.APROVADO
        if escolha:
            decidir(id_ativo, escolha)
            ids = cur.ids_dos_ativos(ss["resultado"])
            ss["item_ativo"] = cur.proximo_pendente(ids, ss["decisoes"], id_ativo) or id_ativo
            st.rerun()
    else:
        s, u = area.columns(2, vertical_alignment="center")
        texto = "Aprovado" if decisao == cur.APROVADO else "Descartado"
        cores = SELO_SUCESSO if decisao == cur.APROVADO else SELO_NEUTRO
        s.markdown(f'<div style="text-align:right">{selo(texto, *cores)}</div>', unsafe_allow_html=True)
        if u.button("Desfazer", key=f"dec_{id_ativo}_u", width="stretch"):
            decidir(id_ativo, cur.PENDENTE)
            st.rerun()


def inicial(chave: str, texto: str):
    """Valor padrão do campo: o texto do estado, se houver (editado ou de lote reaberto), ou o gerado.

    Ao voltar para a tela, o navegador recria o campo só com esse padrão. Com None, ele abre vazio
    e devolve o vazio ao servidor, apagando o texto na aprovação seguinte.
    """
    return ss.get(chave, texto)


def textos_editados() -> dict:
    return {k.removeprefix("txt_"): v for k, v in ss.items() if str(k).startswith("txt_")}


ICONE_DECISAO = {cur.PENDENTE: ":material/radio_button_unchecked:", cur.APROVADO: ":material/check_circle:",
                 cur.DESCARTADO: ":material/cancel:"}


def abrir_item(id_ativo: str):
    ss["item_ativo"] = id_ativo


def mensagem_original(analise: dict):
    st.markdown(f'<div class="cl-origem"><b>{esc(analise["autor"])}</b> em {esc(analise["canal"])}</div>'
                f'<div class="cl-mensagem">{esc(analise["texto"])}</div>', unsafe_allow_html=True)


def item_post(r: dict, post: dict):
    membro = cur.membro_do_post(r)
    st.markdown(f'{selo("Post do LinkedIn", *SELO_INFO)} '
                f'<span style="float:right;font-size:13px;color:{CINZA}">Engajamento previsto: '
                f'<b>{esc(post["potencial_engajamento"]).lower()}</b></span>', unsafe_allow_html=True)
    if membro:
        mensagem_original(membro)
    st.subheader(post["titulo"])
    st.text_area("Texto do post (editável)", value=inicial("txt_post_copy", post["copy"]), key="txt_post_copy", height=260)
    outros = cur.outros_cases(r)
    if outros:
        with st.popover(f"Outros candidatos a case ({len(outros)})"):
            for a in sorted(outros, key=lambda a: a["relevancia"], reverse=True):
                st.markdown(f'**{esc(a["autor"])}**, relevância {a["relevancia"]}/10')
                st.caption(a["texto"])
    nome = membro["autor"].split()[0] if membro else "O membro"
    autorizado = st.checkbox(f"{nome} autorizou o uso do nome e do depoimento", value=inicial("autorizado", False), key="autorizado")
    if not autorizado and ss["decisoes"].get("post") == cur.APROVADO:
        decidir("post", cur.PENDENTE)  # sem autorização, o post volta para pendente
    botoes_decisao("post", "Aprovar post", bloqueado=not autorizado)
    if not autorizado and ss["decisoes"].get("post") == cur.PENDENTE:
        st.caption("Marque a autorização para liberar a aprovação.")


def item_newsletter(news: dict):
    st.markdown(selo("Newsletter", *SELO_NEUTRO), unsafe_allow_html=True)
    st.subheader(news["secao"])
    st.text_input("Chamada", value=inicial("txt_news_chamada", news["chamada"]), key="txt_news_chamada")
    st.text_area("Resumo", value=inicial("txt_news_resumo", news["resumo"]), key="txt_news_resumo", height=160)
    botoes_decisao("newsletter", "Aprovar destaque")


def item_faq(r: dict, i: int, faq: dict):
    st.markdown(selo("Dica para a mentoria", *SELO_NEUTRO), unsafe_allow_html=True)
    duvida = cur.duvida_da_faq(r, i)
    if duvida:
        mensagem_original(duvida)
    st.subheader(cur.titulo_na_fila(r, f"faq_{i}"))
    st.text_area("Resposta sugerida (editável)", value=inicial(f"txt_faq_{i}_conteudo", faq["conteudo"]),
                 key=f"txt_faq_{i}_conteudo", height=220)
    botoes_decisao(f"faq_{i}", "Enviar à mentoria")


def fila(r: dict, ids: list[str]):
    res = cur.resumo(ss["decisoes"])
    fracao = res["revisados"] / res["total"] if res["total"] else 0
    st.progress(fracao, text=f'{res["revisados"]} de {res["total"]} revisados')
    a, d, p = st.columns(3)
    a.metric("Aprovados", res["aprovados"])
    d.metric("Descartados", res["descartados"])
    p.metric("Pendentes", res["pendentes"])
    with st.container(key="fila", height=420, border=False):
        for id_ativo in ids:
            st.button(cur.titulo_na_fila(r, id_ativo), key=f"fila_{id_ativo}", on_click=abrir_item, args=(id_ativo,),
                      icon=ICONE_DECISAO[ss["decisoes"].get(id_ativo, cur.PENDENTE)], width="stretch",
                      type="primary" if id_ativo == ss["item_ativo"] else "secondary")
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


def tela_curadoria():
    if ss["aviso_banco"]:
        st.warning(ss["aviso_banco"])
    st.title("Curadoria")
    r = ss["resultado"]
    if not r:
        sem_lote()
        return
    st.markdown('<p class="cl-sub">Rascunhos gerados pela IA. Confira se o texto não afirma nada que a mensagem '
                'original não diz. Nada é publicado sem a sua aprovação.</p>', unsafe_allow_html=True)
    ids = cur.ids_dos_ativos(r)
    if not ids:
        st.info("Este lote não gerou conteúdos para revisar.")
        return
    ativos = r["ativos_distribuicao_gerados"]
    esquerda, direita = st.columns([3, 7], gap="large")
    with esquerda:
        fila(r, ids)
    with direita:
        item = ss["item_ativo"]
        if item == "post":
            item_post(r, ativos["post_linkedin"])
        elif item == "newsletter":
            item_newsletter(ativos["destaque_newsletter_semanal"])
        else:
            i = int(item.removeprefix("faq_"))
            item_faq(r, i, ativos["sugestao_conteudo_faq"][i])


# ---------------------------------------------------------------------------
def tela_login():
    _, meio, _ = st.columns([1, 1.2, 1])
    with meio:
        st.markdown(logo_html(), unsafe_allow_html=True)
        st.title("Entrar")
        configurado = login.configurado()
        if not configurado:
            st.warning("Login não configurado: defina ADMIN_USUARIO e ADMIN_SENHA no .env e reinicie o app.")
        with st.form("login", border=True):
            usuario = st.text_input("Usuário", key="login_usuario")
            senha = st.text_input("Senha", key="login_senha", type="password")
            if st.form_submit_button("Entrar", type="primary", disabled=not configurado, width="stretch"):
                if login.confere(usuario, senha):
                    ss["logado"] = True
                    st.rerun()
                st.error("Usuário ou senha inválidos.")


iniciar_estado()
if not ss["logado"]:
    tela_login()
    st.stop()
cabecalho()
{"Importar": tela_importar, "Visão geral": tela_visao_geral, "Curadoria": tela_curadoria,
 "Insights": tela_insights}[ss["pagina"]]()
