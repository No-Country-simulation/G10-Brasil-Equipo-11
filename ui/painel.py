"""Painel Streamlit do CommunityLab.

Telas: Importar -> Visão geral -> Curadoria.

Execução, a partir da raiz:
    python -m streamlit run ui/painel.py

Modo integrado:
    COMMUNITYLAB_UI_BACKEND=api

Modo local para desenvolvimento:
    COMMUNITYLAB_UI_BACKEND=local
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from ui.tela_insights import tela_insights

RAIZ = Path(__file__).resolve().parent.parent

for caminho in (RAIZ, RAIZ / "src"):
    if str(caminho) not in sys.path:
        sys.path.insert(0, str(caminho))

from dotenv import load_dotenv

load_dotenv(RAIZ / ".env")

import pandas as pd
import streamlit as st

from app.api_client import (
    APIClientError,
    modo_api,
    request as api_request,
)
from app.grafo import processar
from app.llm import modo_mock
from ui import curadoria as cur
from ui.estilo import (
    AZUL,
    AZUL_ESCURO,
    LARANJA_ESCURO,
    MARCA_SVG,
    ROTAS,
    aplicar_estilo,
    barra_sentimento,
    barras_rotas,
    esc,
    selo,
)
from ui.importacao import ler_arquivo


TELAS = [
    "Importar",
    "Visão geral",
    "Insights",
    "Curadoria",
]
EXEMPLO = RAIZ / "data" / "interacoes_exemplo.json"

st.set_page_config(
    page_title="CommunityLab",
    page_icon="📣",
    layout="wide",
)

aplicar_estilo()
ss = st.session_state


def iniciar_estado() -> None:
    padrao = {
        "pagina": "Importar",
        "leitura": None,
        "arquivo_id": None,
        "resultado": None,
        "processado_em": None,
        "decisoes": {},
        "alertas": {},
        "exportado": None,
        "origem": "",
        "periodo": "",
        "lote_origem": "",
        "lote_periodo": "",
        "processamento_id": None,
        "ids_ativos": {},
        "versoes_ativos": {},
        "idempotency_key": None,
        "lotes_salvos": [],
        "exportacao_id": None,
        "export_status": None,
        "export_idempotency_key": None,
        "autorizado": False,
        "consentimento_api": False,
        "consentimento_referencia": "",
        "_carregamento_automatico_feito": False,
        "_erro_carregamento_automatico": None,
    }

    for chave, valor in padrao.items():
        ss.setdefault(chave, valor)

    if "_ir_para" in ss:
        ss["pagina"] = ss.pop("_ir_para")


def ir_para(tela: str) -> None:
    if tela not in TELAS:
        raise ValueError(f"Tela inexistente: {tela}")

    ss["_ir_para"] = tela
    st.rerun()


def limpar_widgets_ativos() -> None:
    """Evita que campos de um lote anterior contaminem o próximo."""
    prefixos = ("txt_", "dec_", "al_")

    for chave in list(ss.keys()):
        if str(chave).startswith(prefixos):
            del ss[chave]


def pendentes() -> int:
    if not ss["decisoes"]:
        return 0

    return cur.resumo(ss["decisoes"])["pendentes"]


def cabecalho() -> None:
    c1, c2, c3 = st.columns(
        [2, 4, 3],
        vertical_alignment="center",
    )

    c1.markdown(
        f'<div class="cl-marca">{MARCA_SVG}CommunityLab</div>',
        unsafe_allow_html=True,
    )

    c2.container(key="nav").radio(
        "Seção",
        TELAS,
        key="pagina",
        horizontal=True,
        label_visibility="collapsed",
    )

    if modo_api():
        modo = selo(
            "API / backend",
            "#E8EEFB",
            AZUL_ESCURO,
            "#C6D3F3",
        )
    else:
        modo = selo(
            "Modo local",
            "#FFF6EC",
            "#8A3A0B",
            "#D8B48A",
        )

    contexto = ""

    if ss["resultado"]:
        contexto = (
            f'<span class="cl-mono">'
            f'{esc(ss["lote_origem"])} · '
            f'{esc(ss["lote_periodo"])}'
            f'</span>'
        )

        if pendentes():
            contexto += selo(
                f"{pendentes()} pendentes",
                AZUL,
                "#FFFFFF",
            )

    c3.markdown(
        f'<div class="cl-contexto">{contexto}{modo}</div>',
        unsafe_allow_html=True,
    )

    st.divider()


def sem_lote() -> None:
    st.info(
        "Nenhum lote carregado. Comece importando as "
        "interações da comunidade."
    )

    if st.button("Ir para Importar", type="primary"):
        ir_para("Importar")


def _data_processamento(detalhe: dict) -> datetime:
    valor = detalhe.get("finalizado_em") or detalhe.get("criado_em")

    if valor:
        try:
            return datetime.fromisoformat(
                str(valor).replace("Z", "+00:00")
            )
        except ValueError:
            pass

    return datetime.now()


def mostrar_leitura(leitura) -> None:
    with st.container(border=True):
        a, b = st.columns(
            [4, 2],
            vertical_alignment="center",
        )

        a.markdown(
            f'<div class="cl-mono" style="font-weight:600">'
            f'{esc(leitura.nome)}</div>'
            f'<div style="font-size:13px;color:#555D6B">'
            f'{esc(leitura.detalhe)}</div>',
            unsafe_allow_html=True,
        )

        if leitura.ok:
            b.markdown(
                f'<div style="text-align:right">'
                f'{selo("Pronto para processar", "#E8EEFB", AZUL_ESCURO)}'
                f'</div>',
                unsafe_allow_html=True,
            )

            m1, m2, m3 = st.columns(3)
            m1.metric("Linhas lidas", leitura.total)
            m2.metric("Com erro", 0)
            m3.metric("Sem autor (anônimas)", leitura.anonimas)

            previa = pd.DataFrame(
                [
                    item.model_dump()
                    for item in leitura.lote.interacoes[:5]
                ]
            )

            if not previa.empty:
                st.dataframe(
                    previa[["data", "autor", "canal", "tipo", "texto"]],
                    hide_index=True,
                    width="stretch",
                )

            st.caption(
                f"Mostrando {min(5, leitura.total)} "
                f"de {leitura.total} linhas."
            )

        else:
            b.markdown(
                f'<div style="text-align:right">'
                f'{selo("Precisa de ajuste", "#FCEBDF", LARANJA_ESCURO)}'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="cl-alerta">'
                f'<b style="color:{LARANJA_ESCURO}">'
                f'{esc(leitura.titulo_erro)}</b>'
                f'<p style="margin:6px 0 0">'
                f'{esc(leitura.explicacao)}</p></div>',
                unsafe_allow_html=True,
            )

            if leitura.passos:
                st.markdown(
                    "**Como resolver**\n\n"
                    + "\n".join(
                        f"{n}. {passo}"
                        for n, passo in enumerate(
                            leitura.passos,
                            start=1,
                        )
                    )
                )

            if leitura.evidencia:
                st.code(leitura.evidencia, language=None)


def _aplicar_estado_persistido(detalhe: dict) -> None:
    """Reconstrói a sessão a partir do processamento gravado no Oracle."""
    limpar_widgets_ativos()

    resultado = detalhe.get("resultado") or {}

    if not resultado:
        raise APIClientError(
            "O processamento não possui resultado persistido."
        )

    resultado.setdefault(
        "ativos_distribuicao_gerados",
        {},
    )

    ativos_gerados = resultado["ativos_distribuicao_gerados"]

    ativos_por_chave = {
        item["chave"]: item
        for item in detalhe.get("ativos", [])
    }

    estados = {
        "PENDENTE": cur.PENDENTE,
        "APROVADO": cur.APROVADO,
        "DESCARTADO": cur.DESCARTADO,
    }

    decisoes = {}
    ids_ativos = {}
    versoes = {}

    faqs = list(
        ativos_gerados.get("sugestao_conteudo_faq") or []
    )

    for chave, item in ativos_por_chave.items():
        ids_ativos[chave] = item["id"]
        versoes[chave] = int(item.get("versao") or 1)

        if chave == "post" or chave == "newsletter" or chave.startswith("faq_"):
            decisoes[chave] = estados.get(
                item.get("status_curadoria"),
                cur.PENDENTE,
            )

        payload = item.get("payload") or {}

        if chave == "post":
            ativos_gerados["post_linkedin"] = payload

        elif chave == "newsletter":
            ativos_gerados[
                "destaque_newsletter_semanal"
            ] = payload

        elif chave.startswith("faq_"):
            try:
                indice = int(chave.split("_", 1)[1])
            except (ValueError, IndexError):
                continue

            while len(faqs) <= indice:
                faqs.append({})

            faqs[indice] = payload

    if ativos_por_chave:
        ativos_gerados["sugestao_conteudo_faq"] = faqs

    # Inclui todas as chaves de ativo mesmo que não tenham sido
    # retornadas por uma implementação antiga do backend.
    for chave in cur.ids_dos_ativos(resultado):
        decisoes.setdefault(chave, cur.PENDENTE)

    alertas = {
        item["interacao_id"]: dict(item)
        for item in detalhe.get("alertas", [])
        if item.get("interacao_id")
    }

    post = ativos_por_chave.get("post", {})
    consentimento_confirmado = (
        post.get("consentimento_status") == "CONFIRMADO"
    )

    ss.update({
        "resultado": resultado,
        "processamento_id": detalhe.get("id"),
        "ids_ativos": ids_ativos,
        "versoes_ativos": versoes,
        "decisoes": decisoes,
        "alertas": alertas,
        "exportado": None,
        "exportacao_id": None,
        "export_status": None,
        "export_idempotency_key": None,
        "lote_origem": detalhe.get("origem_comunidade", ""),
        "lote_periodo": detalhe.get("periodo_referencia", ""),
        "processado_em": _data_processamento(detalhe),
        "autorizado": consentimento_confirmado,
        "consentimento_api": consentimento_confirmado,
        "consentimento_referencia": (
            post.get("consentimento_referencia") or ""
        ),
    })


def processar_lote(lote) -> None:
    """Processa localmente ou através da API, conforme a configuração."""
    lote = lote.model_copy(
        update={
            "origem_comunidade": (
                ss["origem"].strip()
                or lote.origem_comunidade
            ),
            "periodo_referencia": (
                ss["periodo"].strip()
                or lote.periodo_referencia
            ),
        }
    )

    if (
        os.getenv("APP_ENV", "development").lower() == "production"
        and not modo_api()
    ):
        st.error(
            "O modo local está bloqueado em produção. "
            "Configure COMMUNITYLAB_UI_BACKEND=api."
        )
        return

    with st.spinner(
        "Analisando as interações e gerando os conteúdos..."
    ):
        if modo_api():
            try:
                # Conservar a chave quando houver timeout facilita
                # uma repetição segura da mesma requisição.
                ss["idempotency_key"] = (
                    ss.get("idempotency_key")
                    or str(uuid.uuid4())
                )

                resposta = api_request(
                    "POST",
                    "/processar",
                    payload=lote.model_dump(mode="json"),
                    idempotency_key=ss["idempotency_key"],
                )

                process_id = resposta.get("processamento_id")

                if (
                    not process_id
                    or resposta.get("persistencia") != "oracle"
                ):
                    raise APIClientError(
                        "A API não confirmou a persistência Oracle."
                    )

                detalhe = api_request(
                    "GET",
                    f"/processamentos/{process_id}",
                )

                _aplicar_estado_persistido(detalhe)
                ss["idempotency_key"] = None

            except APIClientError as exc:
                st.error(
                    "Não foi possível concluir o processamento. "
                    f"Confira a API e o banco Oracle: {exc}"
                )
                return

        else:
            try:
                resultado = processar(lote)
            except Exception as exc:
                st.error(
                    "Falha no processamento local: "
                    f"{type(exc).__name__}: {exc}"
                )
                return

            limpar_widgets_ativos()

            ss.update({
                "resultado": resultado,
                "processamento_id": None,
                "ids_ativos": {},
                "versoes_ativos": {},
                "processado_em": datetime.now(),
                "autorizado": False,
                "consentimento_api": False,
                "consentimento_referencia": "",
                "decisoes": {
                    item: cur.PENDENTE
                    for item in cur.ids_dos_ativos(resultado)
                },
                "alertas": {},
                "exportado": None,
                "exportacao_id": None,
                "export_status": None,
                "export_idempotency_key": None,
                "lote_origem": lote.origem_comunidade,
                "lote_periodo": lote.periodo_referencia,
            })

    ir_para("Visão geral")


def tela_importar() -> None:
    st.title("Importar interações")
    st.markdown(
        '<p class="cl-sub">Envie as mensagens da semana. '
        'O pipeline classifica cada uma e gera conteúdos para revisão.</p>',
        unsafe_allow_html=True,
    )

    esquerda, direita = st.columns([3, 2], gap="large")

    with esquerda:
        arquivo = st.file_uploader(
            "Arquivo JSON ou CSV "
            "(colunas autor, canal, tipo e texto)",
            type=["json", "csv"],
        )

        if st.button("Usar lote de exemplo"):
            if not EXEMPLO.is_file():
                st.error(
                    f"Arquivo de exemplo não encontrado: {EXEMPLO}"
                )
            else:
                conteudo = EXEMPLO.read_bytes()
                ss["leitura"] = ler_arquivo(
                    EXEMPLO.name,
                    conteudo,
                )
                ss["arquivo_id"] = "exemplo"

                if ss["leitura"].ok:
                    ss["origem"] = (
                        ss["leitura"].lote.origem_comunidade
                    )
                    ss["periodo"] = (
                        ss["leitura"].lote.periodo_referencia
                    )

        elif arquivo is not None:
            conteudo = arquivo.getvalue()
            fingerprint = hashlib.sha256(
                arquivo.name.encode("utf-8") + conteudo
            ).hexdigest()

            if fingerprint != ss["arquivo_id"]:
                ss["leitura"] = ler_arquivo(
                    arquivo.name,
                    conteudo,
                )
                ss["arquivo_id"] = fingerprint

                if ss["leitura"].ok:
                    ss["origem"] = (
                        ss["leitura"].lote.origem_comunidade
                    )
                    ss["periodo"] = (
                        ss["leitura"].lote.periodo_referencia
                    )

        if ss["leitura"]:
            mostrar_leitura(ss["leitura"])

    with direita:
        leitura = ss["leitura"]

        with st.container(border=True):
            st.subheader("Dados do lote")

            st.text_input(
                "Comunidade de origem",
                key="origem",
                placeholder="Ex.: Discord_Grupo_ONE_G10",
            )

            st.text_input(
                "Período de referência",
                key="periodo",
                placeholder="Ex.: Semana_04",
            )

            if ss["periodo"].strip():
                st.caption(
                    "O pacote será organizado por período e "
                    "identificador de processamento."
                )

            pronto = bool(leitura and leitura.ok)

            rotulo = (
                f"Processar {leitura.total} interações"
                if pronto
                else "Envie um arquivo válido para processar"
            )

            if st.button(
                rotulo,
                type="primary",
                disabled=not pronto,
                width="stretch",
            ):
                processar_lote(leitura.lote)

        with st.container(border=True):
            st.markdown("**Antes de enviar**")
            st.markdown(
                "Confira se o arquivo contém apenas dados que "
                "podem ser utilizados no projeto.\n\n"
                "Nomes reais e depoimentos destinados à publicação "
                "exigem autorização documentada."
            )

    if modo_api():
        tela_retomar_lote()
# ---------------------------------------------------------------------------
# Recuperação e histórico persistido
# ---------------------------------------------------------------------------
def tela_retomar_lote() -> None:
    """Consulta o histórico salvo no Oracle e permite retomar um lote."""
    with st.container(border=True):
        st.subheader("Retomar lote salvo")
        st.caption(
            "Recupere processamentos anteriores sem depender "
            "da sessão atual do painel."
        )

        col1, col2 = st.columns([2, 1])

        with col1:
            atualizar = st.button(
                "Atualizar lista",
                key="atualizar_lotes_salvos",
                width="stretch",
            )

        with col2:
            carregar = st.button(
                "Carregar selecionado",
                key="retomar_lote_salvo",
                type="primary",
                width="stretch",
            )

        if atualizar or not ss["lotes_salvos"]:
            try:
                resposta = api_request(
                    "GET",
                    "/processamentos?limit=100&offset=0",
                )
                ss["lotes_salvos"] = resposta.get("items", [])

            except APIClientError as exc:
                st.error(
                    f"Não foi possível consultar o histórico: {exc}"
                )

        itens = [
            item
            for item in ss["lotes_salvos"]
            if item.get("status") == "SUCESSO"
        ]

        if not itens:
            st.caption(
                "Nenhum processamento concluído disponível "
                "na primeira página do histórico."
            )
            return

        opcoes = {
            (
                f"{item.get('origem_comunidade', 'Comunidade')} · "
                f"{item.get('periodo_referencia', 'Período')} · "
                f"{item['id'][:8]}"
            ): item["id"]
            for item in itens
        }

        selecionado = st.selectbox(
            "Processamento",
            options=list(opcoes.keys()),
            key="lote_salvo_selecionado",
        )

        if carregar:
            process_id = opcoes[selecionado]

            try:
                detalhe = api_request(
                    "GET",
                    f"/processamentos/{process_id}",
                )
                _aplicar_estado_persistido(detalhe)
                ir_para("Visão geral")

            except APIClientError as exc:
                st.error(
                    f"Não foi possível recuperar o lote: {exc}"
                )

def carregar_ultimo_processamento() -> None:
    """Recupera automaticamente o último processamento salvo no Oracle."""
    if not modo_api() or ss["_carregamento_automatico_feito"]:
        return

    ss["_carregamento_automatico_feito"] = True

    # Não sobrescreve dados já carregados ou um lote recém-processado.
    if ss.get("resultado") or ss.get("processamento_id"):
        return

    try:
        resposta = api_request(
            "GET",
            "/processamentos?limit=100&offset=0",
        )

        itens = resposta.get("items") or []
        ss["lotes_salvos"] = itens

        concluidos = [
            item for item in itens
            if item.get("status") == "SUCESSO" and item.get("id")
        ]

        if not concluidos:
            return

        def data_ordem(item):
            valor = (
                item.get("criado_em")
                or item.get("created_at")
                or item.get("processado_em")
            )

            try:
                return datetime.fromisoformat(
                    str(valor).replace("Z", "+00:00")
                ).timestamp()
            except (TypeError, ValueError, OSError):
                return 0

        ultimo = max(concluidos, key=data_ordem)

        detalhe = api_request(
            "GET",
            f"/processamentos/{ultimo['id']}",
        )

        _aplicar_estado_persistido(detalhe)

    except APIClientError as exc:
        ss["_erro_carregamento_automatico"] = str(exc)
# ---------------------------------------------------------------------------
# Tela 2 — Visão geral
# ---------------------------------------------------------------------------
ACOES_ALERTA = {
    "reclamacao": "Encaminhar ao time de conteúdo",
}


def _chave_alerta(analise: dict) -> str:
    return str(
        analise.get("interacao_id")
        or analise.get("autor", "")
    )


def _texto_estado_alerta(analise: dict) -> str | None:
    registro = ss["alertas"].get(_chave_alerta(analise))

    if not registro:
        return None

    if isinstance(registro, dict):
        status = registro.get("status", "PENDENTE")

        return {
            "PENDENTE": "Pendente",
            "ENCAMINHADO": "Encaminhado",
            "RESOLVIDO": "Resolvido",
        }.get(status, status)

    return str(registro)


def _salvar_triagem_alerta(
    analise: dict,
    status: str,
    acao: str,
) -> bool:
    chave = _chave_alerta(analise)

    if not modo_api():
        ss["alertas"][chave] = (
            "Encaminhado"
            if status == "ENCAMINHADO"
            else "Resolvido"
            if status == "RESOLVIDO"
            else "Pendente"
        )
        return True

    registro = ss["alertas"].get(chave)

    if not isinstance(registro, dict) or not registro.get("id"):
        st.error(
            "O identificador persistido deste alerta não foi "
            "encontrado. Recarregue o lote salvo no Oracle."
        )
        return False

    try:
        resposta = api_request(
            "PATCH",
            f"/alertas/{registro['id']}",
            payload={
                "status": status,
                "versao_esperada": int(
                    registro.get("versao", 1)
                ),
                "acao": acao,
                "justificativa": None,
            },
        )

        ss["alertas"][chave] = {
            **registro,
            **resposta,
        }

        return True

    except APIClientError as exc:
        st.error(
            f"A decisão sobre o alerta não foi salva: {exc}"
        )
        return False


def tela_visao_geral() -> None:
    resultado = ss["resultado"]

    if not resultado:
        st.title("Saúde da comunidade")
        sem_lote()
        return

    analises = resultado.get("analises") or []
    ativos = resultado.get("ativos_distribuicao_gerados") or {}
    armaz = resultado.get("armazenamento_oci") or {}

    alertas = [
        analise
        for analise in analises
        if analise.get("rota") == "alerta"
    ]

    abertos = [
        analise
        for analise in alertas
        if _texto_estado_alerta(analise)
        not in {"Encaminhado", "Resolvido"}
    ]

    n_faq = len(
        ativos.get("sugestao_conteudo_faq") or []
    )

    partes = (
        ["1 post"] if ativos.get("post_linkedin") else []
    ) + (
        ["1 newsletter"]
        if ativos.get("destaque_newsletter_semanal")
        else []
    ) + (
        [f"{n_faq} FAQ"] if n_faq else []
    )

    status_pacote = {
        "pendente": "Pendente de envio",
        "salvo_localmente": "Salvo localmente",
        "salvo_com_sucesso": "Salvo na OCI",
        "erro": "Erro ao salvar na OCI",
    }

    topo, botao = st.columns(
        [4, 1],
        vertical_alignment="bottom",
    )

    with topo:
        st.title("Saúde da comunidade")

        quando = (
            ss["processado_em"].strftime("%d/%m/%Y às %H:%M")
            if ss["processado_em"]
            else "Horário não disponível"
        )

        st.markdown(
            f'<p class="cl-sub">{len(analises)} interações '
            f'processadas em {esc(quando)}</p>',
            unsafe_allow_html=True,
        )

    if pendentes() and botao.button(
        f"Revisar {pendentes()} ativos",
        type="primary",
        width="stretch",
    ):
        ir_para("Curadoria")

    k1, k2, k3, k4 = st.columns(4)

    with k1.container(border=True):
        st.metric(
            "Interações processadas",
            len(analises),
        )
        st.caption(
            f"de {len({a.get('autor') for a in analises})} pessoas · "
            f"{len({a.get('canal') for a in analises})} canais"
        )

    with k2.container(border=True):
        st.metric("Ativos para revisar", pendentes())
        st.caption(" · ".join(partes) or "Nenhum ativo gerado")

    with k3.container(border=True):
        st.metric(
            "Alertas aguardando triagem",
            len(abertos),
        )
        st.caption(
            f"{len(alertas) - len(abertos)} já tratados"
            if len(abertos) < len(alertas)
            else "Aguardando avaliação humana"
        )

    with k4.container(border=True):
        pacote_status = armaz.get("status", "pendente")
        cor = (
            LARANJA_ESCURO
            if pacote_status == "erro"
            else AZUL_ESCURO
        )

        st.markdown(
            '<div class="cl-kpi-rotulo">Pacote de distribuição</div>'
            f'<div class="cl-kpi-valor" style="color:{cor}">'
            f'{esc(status_pacote.get(pacote_status, pacote_status))}'
            "</div>",
            unsafe_allow_html=True,
        )

        caminho = armaz.get("caminho_objeto") or "Ainda não definido"
        st.caption(f"`{caminho}`")

    if armaz.get("detalhe"):
        st.warning(
            "Falha ou pendência no armazenamento: "
            + str(armaz["detalhe"])
        )

    if (
        modo_api()
        and ss.get("exportacao_id")
        and ss.get("export_status") == "erro"
    ):
        if st.button(
            "Tentar novamente o upload da exportação",
            key="repetir_upload_exportacao_visao",
        ):
            _repetir_upload_exportacao()

    s1, s2 = st.columns(2)

    with s1.container(border=True):
        st.subheader("Sentimento")

        sentimento = (
            resultado.get("resumo_comunidade") or {}
        ).get("sentimento_predominante", "Não disponível")

        st.caption(
            f"Predominante: {str(sentimento).lower()}."
        )

        st.markdown(
            barra_sentimento(
                Counter(
                    a.get("sentimento", "Neutro")
                    for a in analises
                )
            ),
            unsafe_allow_html=True,
        )

    with s2.container(border=True):
        st.subheader("Destino das interações")
        st.caption("Rota decidida pelo pipeline.")

        st.markdown(
            barras_rotas(
                Counter(
                    a.get("rota", "nenhuma")
                    for a in analises
                )
            ),
            unsafe_allow_html=True,
        )

    if alertas:
        with st.container(border=True):
            st.subheader("Interações que merecem atenção")
            st.caption(
                "Os alertas são indicações para avaliação humana, "
                "não diagnósticos nem conclusões sobre uma pessoa."
            )

            colunas = st.columns(min(len(alertas), 2))

            for index, analise in enumerate(alertas):
                with colunas[index % len(colunas)].container(border=True):
                    autor = analise.get("autor") or "Autor anônimo"
                    canal = analise.get("canal") or "Canal não informado"
                    texto = analise.get("texto") or ""

                    st.markdown(
                        f'**{esc(autor)}** '
                        f'<span class="cl-mono" '
                        f'style="font-size:13px;color:#555D6B">'
                        f'{esc(canal)}</span>',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f'<div class="cl-alerta">“{esc(texto)}”</div>',
                        unsafe_allow_html=True,
                    )

                    feito = _texto_estado_alerta(analise)

                    if feito:
                        st.markdown(
                            selo(
                                feito,
                                "#E8EEFB",
                                AZUL_ESCURO,
                            ),
                            unsafe_allow_html=True,
                        )

                    b1, b2 = st.columns(2)

                    acao = ACOES_ALERTA.get(
                        analise.get("tipo"),
                        "Oferecer mentoria",
                    )

                    if b1.button(
                        acao,
                        key=f"al_{index}_acao",
                        width="stretch",
                    ):
                        if _salvar_triagem_alerta(
                            analise,
                            "ENCAMINHADO",
                            acao,
                        ):
                            st.rerun()

                    if b2.button(
                        "Marcar como resolvido",
                        key=f"al_{index}_ok",
                        width="stretch",
                    ):
                        if _salvar_triagem_alerta(
                            analise,
                            "RESOLVIDO",
                            "Resolvido",
                        ):
                            st.rerun()

    with st.container(border=True):
        cab, filtro_col = st.columns(
            [2, 3],
            vertical_alignment="bottom",
        )

        cab.subheader("Interações analisadas")

        opcoes = ["Todas"] + [
            ROTAS[chave]["nome"]
            for chave in ROTAS
        ]

        filtro = filtro_col.container(
            key="filtro"
        ).radio(
            "Filtrar por rota",
            opcoes,
            horizontal=True,
            key="filtro_rota",
        )

        nome_para_rota = {
            valor["nome"]: chave
            for chave, valor in ROTAS.items()
        }

        linhas = [
            analise
            for analise in analises
            if (
                filtro == "Todas"
                or analise.get("rota", "nenhuma")
                == nome_para_rota[filtro]
            )
        ]

        linhas.sort(
            key=lambda item: item.get("relevancia", 0),
            reverse=True,
        )

        tabela = pd.DataFrame([
            {
                "Autor": analise.get("autor", ""),
                "Canal": analise.get("canal", ""),
                "Mensagem": analise.get("texto", ""),
                "Sentimento": analise.get("sentimento", ""),
                "Relevância": analise.get("relevancia", 0),
                "Rota": ROTAS.get(
                    analise.get("rota", "nenhuma"),
                    ROTAS["nenhuma"],
                )["nome"],
            }
            for analise in linhas
        ])

        if tabela.empty:
            st.caption("Nenhuma mensagem encontrada para esta rota.")
        else:
            st.dataframe(
                tabela,
                hide_index=True,
                width="stretch",
                column_config={
                    "Mensagem": st.column_config.TextColumn(
                        width="large"
                    ),
                    "Relevância": st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=10,
                        format="%d/10",
                    ),
                },
            )
# ---------------------------------------------------------------------------
# Tela 3 — Curadoria
# ---------------------------------------------------------------------------
def _patch_ativo_ui(id_ativo: str) -> dict:
    """Obtém os campos editados na interface para salvar no backend."""
    resultado = ss.get("resultado") or {}
    ativos = resultado.get(
        "ativos_distribuicao_gerados", {}
    )

    if id_ativo == "post":
        post = ativos.get("post_linkedin") or {}

        return {
            "titulo": ss.get(
                "txt_post_titulo",
                post.get("titulo", ""),
            ),
            "copy": ss.get(
                "txt_post_copy",
                post.get("copy", ""),
            ),
        }

    if id_ativo == "newsletter":
        news = (
            ativos.get("destaque_newsletter_semanal") or {}
        )

        return {
            "secao": ss.get(
                "txt_news_secao",
                news.get("secao", ""),
            ),
            "chamada": ss.get(
                "txt_news_chamada",
                news.get("chamada", ""),
            ),
            "resumo": ss.get(
                "txt_news_resumo",
                news.get("resumo", ""),
            ),
        }

    if id_ativo.startswith("faq_"):
        try:
            indice = int(id_ativo.split("_", 1)[1])
            faq = (
                ativos.get("sugestao_conteudo_faq") or []
            )[indice]
        except (ValueError, IndexError):
            return {}

        return {
            "tema": ss.get(
                f"txt_{id_ativo}_tema",
                faq.get("tema", ""),
            ),
            "conteudo": ss.get(
                f"txt_{id_ativo}_conteudo",
                faq.get("conteudo", ""),
            ),
            "origem": faq.get("origem", ""),
        }

    return {}


def _atualizar_payload_local(
    id_ativo: str,
    patch: dict,
) -> None:
    """Aplica as edições à sessão no modo local de desenvolvimento."""
    ativos = ss["resultado"]["ativos_distribuicao_gerados"]

    if id_ativo == "post":
        ativos["post_linkedin"].update(patch)

    elif id_ativo == "newsletter":
        ativos["destaque_newsletter_semanal"].update(patch)

    elif id_ativo.startswith("faq_"):
        indice = int(id_ativo.split("_", 1)[1])
        faqs = ativos.get("sugestao_conteudo_faq") or []

        if 0 <= indice < len(faqs):
            faqs[indice].update(patch)
            ativos["sugestao_conteudo_faq"] = faqs


def _salvar_decisao(
    id_ativo: str,
    novo_status: str,
) -> bool:
    """Salva conteúdo e decisão; em modo API, usa transação Oracle."""
    status_validos = {
        cur.PENDENTE: "PENDENTE",
        cur.APROVADO: "APROVADO",
        cur.DESCARTADO: "DESCARTADO",
    }

    if novo_status not in status_validos:
        st.error("Estado de curadoria inválido.")
        return False

    patch = _patch_ativo_ui(id_ativo)

    # Toda aprovação de post que identifica um membro exige
    # autorização confirmada e referência documental.
    consentimento = None
    referencia = None
    status_api = status_validos[novo_status]

    if id_ativo == "post":
        autorizado = bool(ss.get("autorizado"))
        referencia_informada = (
            ss.get("consentimento_referencia") or ""
        ).strip()

        if (
            status_api == "APROVADO"
            and (not autorizado or not referencia_informada)
        ):
            if (
                not autorizado
                and ss.get("consentimento_api")
            ):
                # A autorização previamente registrada foi desmarcada.
                # Não permitimos manter a aprovação.
                status_api = "PENDENTE"
                novo_status = cur.PENDENTE
                consentimento = False
            else:
                st.error(
                    "Antes de aprovar o post, confirme a autorização "
                    "e informe a referência documental correspondente."
                )
                return False

        elif autorizado and referencia_informada:
            consentimento = True
            referencia = referencia_informada

        elif (
            not autorizado
            and ss.get("consentimento_api")
        ):
            consentimento = False

            if status_api == "APROVADO":
                status_api = "PENDENTE"
                novo_status = cur.PENDENTE

    if not modo_api():
        try:
            _atualizar_payload_local(id_ativo, patch)
        except (KeyError, IndexError, ValueError) as exc:
            st.error(f"Não foi possível atualizar o ativo: {exc}")
            return False

        ss["decisoes"][id_ativo] = novo_status

        # Mantém a simulação local coerente com o comportamento da API.
        # A referência documental já está armazenada pelo próprio widget.
        if id_ativo == "post":
            ss["consentimento_api"] = bool(consentimento)

        return True

    asset_id = ss.get("ids_ativos", {}).get(id_ativo)

    if not asset_id or not ss.get("processamento_id"):
        st.error(
            "Não foi encontrado o ID persistido deste ativo. "
            "Carregue novamente o lote salvo no Oracle."
        )
        return False

    try:
        resposta = api_request(
            "PATCH",
            f"/ativos/{asset_id}/curadoria",
            payload={
                "status": status_api,
                "versao_esperada": int(
                    ss.get("versoes_ativos", {}).get(
                        id_ativo,
                        1,
                    )
                ),
                "patch": patch,
                "consentimento": consentimento,
                "referencia_consentimento": referencia,
                "justificativa": None,
            },
        )

        ss["versoes_ativos"][id_ativo] = int(
            resposta.get("versao", 1)
        )

        mapa_estados = {
            "PENDENTE": cur.PENDENTE,
            "APROVADO": cur.APROVADO,
            "DESCARTADO": cur.DESCARTADO,
        }

        status_salvo = resposta.get(
            "status_curadoria",
            status_api,
        )

        ss["decisoes"][id_ativo] = mapa_estados.get(
            status_salvo,
            cur.PENDENTE,
        )

        _atualizar_payload_local(
            id_ativo,
            resposta.get("payload") or patch,
        )

        if id_ativo == "post":
            ss["consentimento_api"] = (
                resposta.get("consentimento_status")
                == "CONFIRMADO"
            )

            ss["consentimento_referencia"] = (
                resposta.get("consentimento_referencia") or ""
            )

            if not ss["consentimento_api"]:
                ss["autorizado"] = False

        return True

    except APIClientError as exc:
        st.error(
            "Não foi possível salvar a alteração no Oracle. "
            "Se ocorreu conflito de versão, recarregue o lote. "
            f"Detalhes: {exc}"
        )
        return False


def botoes_decisao(
    id_ativo: str,
    rotulo_aprovar: str,
    bloqueado: bool = False,
) -> None:
    decisao = ss["decisoes"].get(
        id_ativo,
        cur.PENDENTE,
    )

    d, a, s = st.columns([1, 1, 1])

    if decisao == cur.PENDENTE:
        with d:
            if st.button(
                "Descartar",
                key=f"dec_{id_ativo}_d",
                width="stretch",
            ):
                if _salvar_decisao(
                    id_ativo,
                    cur.DESCARTADO,
                ):
                    st.rerun()

        with a:
            if st.button(
                rotulo_aprovar,
                key=f"dec_{id_ativo}_a",
                type="primary",
                disabled=bloqueado,
                width="stretch",
            ):
                if _salvar_decisao(
                    id_ativo,
                    cur.APROVADO,
                ):
                    st.rerun()

    else:
        texto = (
            "Aprovado"
            if decisao == cur.APROVADO
            else "Descartado"
        )

        fundo, cor = (
            ("#E8EEFB", AZUL_ESCURO)
            if decisao == cur.APROVADO
            else ("#EEF1F6", "#555D6B")
        )

        with d:
            st.markdown(
                f'<div style="padding-top:8px">'
                f'{selo(texto, fundo, cor)}</div>',
                unsafe_allow_html=True,
            )

        with a:
            if st.button(
                "Desfazer decisão",
                key=f"dec_{id_ativo}_u",
                width="stretch",
            ):
                if _salvar_decisao(
                    id_ativo,
                    cur.PENDENTE,
                ):
                    st.rerun()

    with s:
        if st.button(
            "Salvar edições",
            key=f"dec_{id_ativo}_s",
            width="stretch",
        ):
            if _salvar_decisao(
                id_ativo,
                decisao,
            ):
                st.success("Alterações registradas.")
                st.rerun()


def textos_editados() -> dict:
    """Nomes compatíveis com ui.curadoria.montar_aprovados."""
    return {
        chave.removeprefix("txt_"): valor
        for chave, valor in ss.items()
        if str(chave).startswith("txt_")
    }


def tela_curadoria() -> None:
    resultado = ss["resultado"]

    if not resultado:
        st.title("Curadoria")
        sem_lote()
        return

    ativos = resultado.get(
        "ativos_distribuicao_gerados", {}
    )

    principal, lateral = st.columns(
        [7, 3],
        gap="large",
    )

    with principal:
        st.title("Curadoria")

        st.markdown(
            '<p class="cl-sub">Revise os rascunhos gerados '
            'pela IA. Nada é publicado automaticamente.</p>',
            unsafe_allow_html=True,
        )

        post = ativos.get("post_linkedin")

        if post:
            membro = cur.membro_do_post(resultado)

            with st.container(border=True):
                st.markdown(
                    f'{selo("Post · LinkedIn oficial", "#E8EEFB", AZUL_ESCURO)} '
                    f'<span style="float:right;font-size:13px;color:#555D6B">'
                    f'Engajamento previsto: '
                    f'<b>{esc(post.get("potencial_engajamento", "Não estimado"))}</b>'
                    f'</span>',
                    unsafe_allow_html=True,
                )

                st.text_input(
                    "Título",
                    value=post.get("titulo", ""),
                    key="txt_post_titulo",
                )

                col_texto, col_origem = st.columns(
                    [3, 2],
                    gap="medium",
                )

                with col_texto:
                    st.text_area(
                        "Texto do post",
                        value=post.get("copy", ""),
                        key="txt_post_copy",
                        height=280,
                    )

                with col_origem:
                    if membro:
                        st.markdown(
                            '<div class="cl-rotulo">Interação de origem</div>',
                            unsafe_allow_html=True,
                        )

                        st.markdown(
                            f'<div class="cl-citacao">'
                            f'“{esc(membro.get("texto", ""))}”</div>',
                            unsafe_allow_html=True,
                        )

                        st.caption(
                            f'{membro.get("autor", "Anônimo")} · '
                            f'{membro.get("canal", "Canal desconhecido")} · '
                            f'relevância {membro.get("relevancia", 0)}/10'
                        )

                        outros = cur.outros_cases(resultado)

                        if outros:
                            st.caption(
                                "Outros candidatos: "
                                + ", ".join(
                                    f'{item.get("autor", "Anônimo")} '
                                    f'({item.get("relevancia", 0)}/10)'
                                    for item in outros
                                )
                            )

                nome = (
                    membro["autor"].split()[0]
                    if membro and membro.get("autor")
                    else "O membro"
                )

                st.checkbox(
                    f"{nome} autorizou o uso do nome e do depoimento",
                    key="autorizado",
                )

                st.text_input(
                    "Referência documental da autorização",
                    key="consentimento_referencia",
                    placeholder="Ex.: protocolo interno ou referência do termo",
                    help=(
                        "Informe o identificador do registro que comprova "
                        "a autorização. O painel não valida esse documento."
                    ),
                )

                autorizado = bool(ss.get("autorizado"))
                referencia = (
                    ss.get("consentimento_referencia") or ""
                ).strip()

                bloqueado = not (autorizado and bool(referencia))

                if bloqueado:
                    st.caption(
                        "A aprovação do post exige autorização confirmada "
                        "e uma referência documental."
                    )

                if (
                    not autorizado
                    and ss.get("consentimento_api")
                ):
                    st.warning(
                        "Há uma autorização anteriormente registrada. "
                        "Salve a edição com a autorização desmarcada para "
                        "revogá-la e devolver o post para pendente."
                    )

                botoes_decisao(
                    "post",
                    "Aprovar post",
                    bloqueado=bloqueado,
                )

        news = ativos.get("destaque_newsletter_semanal")

        if news:
            with st.container(border=True):
                st.markdown(
                    selo(
                        "Newsletter semanal",
                        "#EEF1F6",
                        "#33373F",
                    ),
                    unsafe_allow_html=True,
                )

                st.text_input(
                    "Seção",
                    value=news.get("secao", ""),
                    key="txt_news_secao",
                )

                st.text_input(
                    "Chamada",
                    value=news.get("chamada", ""),
                    key="txt_news_chamada",
                )

                st.text_area(
                    "Resumo",
                    value=news.get("resumo", ""),
                    key="txt_news_resumo",
                    height=120,
                )

                botoes_decisao(
                    "newsletter",
                    "Aprovar destaque",
                )

        faqs = ativos.get("sugestao_conteudo_faq") or []

        if faqs:
            st.subheader("Dicas rápidas para a mentoria")
            st.caption(
                f"{len(faqs)} sugestões de FAQ para revisão."
            )

            for index, faq in enumerate(faqs):
                chave = f"faq_{index}"

                with st.container(border=True):
                    st.text_input(
                        "Tema",
                        value=faq.get("tema", ""),
                        key=f"txt_{chave}_tema",
                    )

                    st.text_area(
                        "Conteúdo",
                        value=faq.get("conteudo", ""),
                        key=f"txt_{chave}_conteudo",
                        height=120,
                    )

                    duvida = cur.duvida_da_faq(
                        resultado,
                        index,
                    )

                    if duvida:
                        st.caption(
                            f'Dúvida de {duvida.get("autor", "Anônimo")} '
                            f'em {duvida.get("canal", "canal desconhecido")}: '
                            f'“{duvida.get("texto", "")}”'
                        )

                    botoes_decisao(
                        chave,
                        "Enviar à mentoria",
                    )

    with lateral:
        resumo = cur.resumo(ss["decisoes"])

        with st.container(border=True):
            st.subheader("Revisão da semana")

            fracao = (
                resumo["revisados"] / resumo["total"]
                if resumo["total"]
                else 0
            )

            st.progress(
                fracao,
                text=(
                    f'{resumo["revisados"]} de '
                    f'{resumo["total"]} revisados'
                ),
            )

            aprovados, descartados, pendentes_col = st.columns(3)

            aprovados.metric(
                "Aprovados",
                resumo["aprovados"],
            )
            descartados.metric(
                "Descartados",
                resumo["descartados"],
            )
            pendentes_col.metric(
                "Pendentes",
                resumo["pendentes"],
            )

            if st.button(
                "Exportar aprovados",
                type="primary",
                disabled=resumo["aprovados"] == 0,
                width="stretch",
            ):
                _exportar_aprovados()

            if ss.get("exportado"):
                caminho, conteudo = ss["exportado"]

                status = ss.get("export_status")

                if status == "salvo_com_sucesso":
                    st.success(
                        f"Pacote enviado à OCI: `{caminho}`"
                    )
                elif status == "salvo_localmente":
                    st.warning(
                        f"Pacote salvo apenas localmente: `{caminho}`"
                    )
                elif status == "erro":
                    st.error(
                        "A exportação foi registrada, mas o upload "
                        "para OCI não foi confirmado."
                    )
                else:
                    st.info(
                        f"Exportação registrada: `{caminho}`"
                    )

                st.download_button(
                    "Baixar aprovados.json",
                    data=conteudo,
                    file_name="aprovados.json",
                    mime="application/json",
                    width="stretch",
                )

                if (
                    modo_api()
                    and ss.get("exportacao_id")
                    and ss.get("export_status") == "erro"
                ):
                    if st.button(
                        "Tentar novamente o upload",
                        key="repetir_upload_exportacao",
                        width="stretch",
                    ):
                        _repetir_upload_exportacao()

        with st.container(border=True):
            st.markdown("**Antes de aprovar**")
            st.markdown(
                "Confira se o texto não afirma nada além do que "
                "as interações de origem sustentam.\n\n"
                "A aprovação é uma decisão humana e precisa ser "
                "registrada no backend."
            )
# ---------------------------------------------------------------------------
# Exportação e retentativas de armazenamento
# ---------------------------------------------------------------------------
def _exportar_aprovados() -> None:
    resultado = ss.get("resultado")

    if not resultado:
        st.error("Não existe processamento para exportar.")
        return

    if modo_api():
        process_id = ss.get("processamento_id")

        if not process_id:
            st.error(
                "Este lote não possui um ID Oracle. "
                "Carregue o processamento persistido antes de exportar."
            )
            return

        try:
            ss["export_idempotency_key"] = (
                ss.get("export_idempotency_key")
                or str(uuid.uuid4())
            )

            resposta = api_request(
                "POST",
                f"/processamentos/{process_id}/exportar",
                idempotency_key=ss["export_idempotency_key"],
            )

            export_id = resposta.get("exportacao_id")
            pacote = resposta.get("pacote") or {}
            armazenamento = resposta.get("armazenamento_oci") or {}

            if not export_id:
                raise APIClientError(
                    "A API não retornou o identificador da exportação."
                )

            ss["exportacao_id"] = export_id
            ss["export_status"] = armazenamento.get(
                "status",
                "erro",
            )

            conteudo = json.dumps(
                pacote,
                ensure_ascii=False,
                indent=2,
            )

            ss["exportado"] = (
                armazenamento.get("caminho_objeto")
                or export_id,
                conteudo,
            )

            # A exportação foi registrada. Se o upload falhou,
            # a retentativa utiliza o export_id, não cria outro pacote.
            ss["export_idempotency_key"] = None

            if ss["export_status"] == "salvo_com_sucesso":
                st.success(
                    "Pacote aprovado e enviado ao Object Storage da OCI."
                )
            elif ss["export_status"] == "salvo_localmente":
                st.warning(
                    "O pacote foi salvo localmente, não no bucket OCI. "
                    "Confira OCI_STORAGE_MODE."
                )
            else:
                st.error(
                    "A exportação foi registrada, mas o upload à OCI "
                    "precisa ser verificado ou repetido."
                )

        except APIClientError as exc:
            st.error(
                "Não foi possível concluir a exportação pela API: "
                f"{exc}"
            )

        return

    # Desenvolvimento local: não representa uma exportação Oracle/OCI.
    try:
        pacote = cur.montar_aprovados(
            resultado,
            ss["decisoes"],
            textos_editados(),
            ss["lote_origem"],
            ss["lote_periodo"],
            autorizado=bool(ss.get("autorizado")),
        )

        if pacote.get("post_linkedin"):
            referencia = (
                ss.get("consentimento_referencia") or ""
            ).strip()

            if not referencia:
                st.error(
                    "Para exportar o post local, informe a referência "
                    "documental da autorização."
                )
                return

            pacote["post_linkedin"]["referencia_autorizacao"] = (
                referencia
            )

        destino = cur.salvar_aprovados(pacote)

        conteudo = json.dumps(
            pacote,
            ensure_ascii=False,
            indent=2,
        )

        ss["exportado"] = (
            str(destino),
            conteudo,
        )
        ss["export_status"] = "salvo_localmente"

        st.warning(
            "Exportação de desenvolvimento: o arquivo foi salvo "
            "localmente, sem confirmação de upload à OCI."
        )

    except (ValueError, KeyError, OSError) as exc:
        st.error(
            f"Não foi possível gerar a exportação local: {exc}"
        )


def _repetir_upload_exportacao() -> None:
    export_id = ss.get("exportacao_id")

    if not export_id:
        st.error(
            "Não existe um identificador de exportação para repetir."
        )
        return

    try:
        resposta = api_request(
            "POST",
            f"/exportacoes/{export_id}/repetir-upload",
        )

        armazenamento = resposta.get("armazenamento_oci") or {}

        ss["export_status"] = armazenamento.get(
            "status",
            "erro",
        )

        if ss.get("exportado"):
            _, conteudo = ss["exportado"]
            ss["exportado"] = (
                armazenamento.get("caminho_objeto")
                or export_id,
                conteudo,
            )

        if ss["export_status"] == "salvo_com_sucesso":
            st.success(
                "Upload confirmado no Object Storage da OCI."
            )
        else:
            st.error(
                "O upload ainda não foi confirmado. "
                "Confira as permissões do bucket e os logs da API."
            )

        st.rerun()

    except APIClientError as exc:
        st.error(
            f"Falha ao repetir o upload da exportação: {exc}"
        )


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------
iniciar_estado()
carregar_ultimo_processamento()
cabecalho()

if ss.get("_erro_carregamento_automatico"):
    st.warning(
        "Não foi possível recuperar o último processamento "
        f"do Oracle: {ss.pop('_erro_carregamento_automatico')}"
    )

telas = {
    "Importar": tela_importar,
    "Visão geral": tela_visao_geral,
    "Insights": tela_insights,
    "Curadoria": tela_curadoria,
}

telas[ss["pagina"]]()