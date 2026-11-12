"""Rotas REST complementares para a interface Web Vanilla e integração frontend.

Isoladas em APIRouter para evitar conflitos de merge e garantir arquitetura limpa.

Com COMMUNITYLAB_DB_MODE=oracle, curadoria, alertas e Insights leem e gravam no
Oracle por `app.repository`. Sem Oracle, valem o histórico antigo (Supabase, se
DATABASE_URL existir) e o modo demonstração.
"""
import hashlib
import json
import logging
import os
import re
import secrets
import unicodedata
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

RAIZ = Path(__file__).resolve().parent.parent

router = APIRouter(tags=["web"])

logger = logging.getLogger("communitylab.web")

_SESSOES_ATIVAS: set[str] = set()


def exigir_admin(request: Request):
    """Dependência FastAPI que garante que a sessão está autenticada quando o login de admin estiver configurado."""
    from ui import login
    if not login.configurado():
        return  # Em desenvolvimento aberto (sem ADMIN_USUARIO/SENHA), não restringe
    token = request.cookies.get("sender_session") or request.headers.get("X-Sender-Token")
    if not token or token not in _SESSOES_ATIVAS:
        raise HTTPException(status_code=401, detail="Acesso restrito. Faça login administrativo para continuar.")


class LoginRequisicao(BaseModel):
    usuario: str = ""
    senha: str = ""


class ExportarCuradoriaRequisicao(BaseModel):
    lote_id: Optional[int | str] = None
    origem_comunidade: str = "Discord_Grupo_ONE_G10"
    periodo_referencia: str
    aprovado_em: Optional[str] = None
    resultado: Optional[dict] = None
    decisoes: dict[str, str] = {}
    textos: dict[str, str] = {}
    autorizado: bool = False
    post_linkedin: Optional[dict] = None
    destaque_newsletter_semanal: Optional[dict] = None
    sugestao_conteudo_faq: list[dict] = []
    descartados: list[str] = []


class DecisaoRequisicao(BaseModel):
    lote_id: Optional[int | str] = None
    chave: str
    decisao: str
    textos: dict[str, str] = {}
    autorizacao: bool = False


class VerificarLoteRequisicao(BaseModel):
    interacoes: list[dict] = []


class AlertaTratarRequisicao(BaseModel):
    lote_id: Optional[int | str] = None
    ordem: int
    status: str


# ---------------------------------------------------------------------------
# Ponte entre o painel web e o Oracle (app.repository)
# ---------------------------------------------------------------------------
_STATUS_CURADORIA = {"p": "PENDENTE", "a": "APROVADO", "d": "DESCARTADO"}

# Status do painel -> (estado de triagem no Oracle, ação registrada no histórico)
_STATUS_ALERTA = {
    "aberto": ("PENDENTE", "Reaberto"),
    "encaminhado": ("ENCAMINHADO", "Encaminhado"),
    "mentoria_oferecida": ("ENCAMINHADO", "Mentoria oferecida"),
    "resolvido": ("RESOLVIDO", "Resolvido"),
}


def em_utc(iso: str | None) -> str | None:
    """O Oracle devolve as datas em UTC, mas sem fuso. Marca o fuso para o navegador
    mostrar no horário local (sem isso, 22:07 aparecia como 01:07)."""
    if not iso or iso.endswith("Z") or re.search(r"[+-]\d\d:\d\d$", iso):
        return iso
    return f"{iso}+00:00"


def oracle_ativo() -> bool:
    from app import database
    return database.database_mode() == "oracle"


def _responsavel() -> str:
    """Quem assina as alterações feitas pelo painel (o login é de um único admin)."""
    return (os.getenv("ADMIN_USUARIO") or "").strip() or "painel-web"


def _patch_do_ativo(chave: str, textos: dict[str, str]) -> dict[str, str]:
    """Converte os textos do painel ("post_copy", "news_resumo", "faq_0_conteudo") nos campos do ativo."""
    from ui import curadoria as cur

    prefixo = {"post": "post_", "newsletter": "news_"}.get(chave, f"{chave}_")
    return {
        campo.removeprefix(prefixo): valor
        for campo, valor in cur.textos_do_ativo(chave, textos).items()
        if isinstance(valor, str) and valor.strip()
    }


def _salvar_decisao_oracle(req: "DecisaoRequisicao") -> None:
    from app import repository

    status = _STATUS_CURADORIA.get(req.decisao)
    if status is None:
        raise repository.InvalidCuration("Decisão de curadoria inválida.")

    item = repository.obter_processamento(str(req.lote_id))
    ativo = next((a for a in (item or {}).get("ativos", []) if a["chave"] == req.chave), None)
    if ativo is None:
        raise repository.RecordNotFound("Ativo não encontrado neste lote.")

    responsavel = _responsavel()
    autorizou = req.chave == "post" and req.autorizacao

    repository.atualizar_curadoria(
        asset_id=ativo["id"],
        status=status,
        patch=_patch_do_ativo(req.chave, req.textos),
        actor=responsavel,
        versao_esperada=ativo["versao"],
        consentimento=True if autorizou else None,
        referencia_consentimento=(
            f"Autorização do membro confirmada no painel por {responsavel}" if autorizou else None
        ),
    )


def _alerta_da_ordem(item: dict, ordem: int) -> dict | None:
    """Acha o alerta do Oracle a partir da posição da mensagem no lote (o que o painel conhece)."""
    resultado = item.get("resultado") or {}
    ordens = [i for i, a in enumerate(resultado.get("analises") or []) if a.get("rota") == "alerta"]
    if ordem not in ordens:
        return None

    numero = ordens.index(ordem)
    alertas = item.get("alertas") or []
    fontes = (resultado.get("fontes_ativos") or {}).get(f"alerta_{numero}") or []
    if fontes:
        achado = next((a for a in alertas if a["interacao_id"] == fontes[0]), None)
        if achado:
            return achado
    return alertas[numero] if numero < len(alertas) else None


def _tratar_alerta_oracle(req: "AlertaTratarRequisicao") -> None:
    from app import repository

    if req.status not in _STATUS_ALERTA:
        raise repository.InvalidCuration("Estado de alerta inválido.")
    status, acao = _STATUS_ALERTA[req.status]

    item = repository.obter_processamento(str(req.lote_id))
    alerta = _alerta_da_ordem(item, req.ordem) if item else None
    if alerta is None:
        raise repository.RecordNotFound("Alerta não encontrado neste lote.")

    repository.atualizar_alerta(
        alert_id=alerta["id"],
        status=status,
        actor=_responsavel(),
        versao_esperada=alerta["versao"],
        acao=acao,
    )


def _exportar_oracle(dados: "ExportarCuradoriaRequisicao") -> dict:
    """Exporta os aprovados do lote: registra em CL_EXPORTACOES e sobe o pacote para o Object Storage.

    Antes de exportar, grava as decisões e os textos que estão na tela. O painel salva cada
    decisão em segundo plano, então a última pode ainda não ter chegado ao banco.
    """
    from app import main as api, repository

    lote_id = str(dados.lote_id)
    try:
        for chave, decisao in dados.decisoes.items():
            _salvar_decisao_oracle(DecisaoRequisicao(
                lote_id=lote_id, chave=chave, decisao=decisao, textos=dados.textos,
                autorizacao=dados.autorizado,
            ))
        exportacao = repository.criar_exportacao(lote_id, _responsavel())
        envio = api._upload_export(exportacao["id"])
    except repository.RecordNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except (repository.InvalidCuration, repository.VersionConflict) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha ao exportar o lote %s (%s)", lote_id, type(exc).__name__)
        raise HTTPException(503, "Não foi possível gerar a exportação.") from exc

    if envio.get("status") == "erro":
        # A exportação fica registrada como pendente; POST /exportacoes/{id}/repetir-upload reenvia.
        raise HTTPException(502, (
            "A exportação foi registrada, mas o envio ao Object Storage falhou. "
            f"{envio.get('detalhe') or ''} Exportação: {exportacao['id']}"
        ).strip())

    na_nuvem = envio.get("status") == "salvo_com_sucesso"
    objeto = envio.get("caminho_objeto") or ""
    return {
        "status": "ok",
        # Mesmo conteúdo aprovado já exportado antes: nada foi enviado de novo.
        "ja_exportado": bool(exportacao.get("existing")),
        "exportado_em": em_utc(exportacao.get("criado_em")),
        "caminho": f"oci://{envio.get('bucket')}/{objeto}" if na_nuvem else str(Path("saida_local") / objeto),
        "exportacao_id": exportacao["id"],
        "armazenamento_oci": envio,
    }


def hash_das_mensagens(interacoes: list[dict]) -> str:
    """Impressão digital só das mensagens: ignora ordem, espaços nas pontas, forma Unicode,
    comunidade e período. O mesmo arquivo importado com outra fonte ou outro mês dá o mesmo valor."""
    def norm(valor) -> str:
        return unicodedata.normalize("NFC", str(valor or "")).strip()

    itens = sorted(
        [norm(i.get("autor")), norm(i.get("canal")), norm(i.get("tipo") or "outro"), norm(i.get("texto")),
         norm(i.get("data"))]
        for i in interacoes if isinstance(i, dict)
    )
    bruto = json.dumps(itens, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _modo_atual() -> str:
    from app.llm import modo_mock
    return "mock" if modo_mock() else "gemini"


def _estado_do_lote(item: dict) -> dict:
    """Monta o que o painel precisa para reabrir um lote: resultado com os textos já editados,
    decisões, autorização do post e alertas tratados."""
    resultado = dict(item.get("resultado") or {})
    ativos = dict(resultado.get("ativos_distribuicao_gerados") or {})
    faqs = [dict(f) for f in (ativos.get("sugestao_conteudo_faq") or [])]
    decisoes, autorizado = {}, False
    letra = {"PENDENTE": "p", "APROVADO": "a", "DESCARTADO": "d"}

    for ativo in item.get("ativos") or []:
        chave, payload = ativo["chave"], ativo.get("payload") or {}
        decisoes[chave] = letra.get(ativo.get("status_curadoria"), "p")
        if chave == "post":
            ativos["post_linkedin"] = payload
            autorizado = ativo.get("consentimento_status") == "CONFIRMADO"
        elif chave == "newsletter":
            ativos["destaque_newsletter_semanal"] = payload
        elif chave.startswith("faq_") and chave[4:].isdigit() and int(chave[4:]) < len(faqs):
            faqs[int(chave[4:])] = payload
    if faqs:
        ativos["sugestao_conteudo_faq"] = faqs
    resultado["ativos_distribuicao_gerados"] = ativos
    resultado["lote_id"] = item["id"]

    ordens = [i for i, a in enumerate(resultado.get("analises") or []) if a.get("rota") == "alerta"]
    fontes = resultado.get("fontes_ativos") or {}
    por_interacao = {a["interacao_id"]: a for a in item.get("alertas") or []}
    alertas = {}
    for numero, ordem in enumerate(ordens):
        origem = (fontes.get(f"alerta_{numero}") or [None])[0]
        alerta = por_interacao.get(origem)
        if alerta is None or alerta["status"] == "PENDENTE":
            continue
        if alerta["status"] == "RESOLVIDO":
            alertas[str(ordem)] = "resolvido"
        else:
            alertas[str(ordem)] = "mentoria_oferecida" if alerta.get("acao") == "Mentoria oferecida" else "encaminhado"

    return {
        "lote_id": item["id"],
        "resultado": resultado,
        "decisoes": decisoes,
        "autorizado": autorizado,
        "alertas": alertas,
        "origem": item.get("origem_comunidade"),
        "periodo": item.get("periodo_referencia"),
        "processado_em": em_utc(item.get("finalizado_em") or item.get("criado_em")),
    }


def _gravar_no_oracle(operacao, req) -> dict:
    """Executa a gravação e devolve o contrato do painel: nunca derruba a tela, mas diz se salvou."""
    from app import repository

    try:
        operacao(req)
        return {"status": "ok", "salvo_no_banco": True}
    except (repository.RecordNotFound, repository.InvalidCuration, repository.VersionConflict) as exc:
        return {"status": "ok", "salvo_no_banco": False, "detalhe": str(exc)}
    except Exception as exc:
        logger.exception("Falha ao gravar no Oracle (%s)", type(exc).__name__)
        return {"status": "ok", "salvo_no_banco": False, "detalhe": "Banco indisponível no momento."}


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
@router.get("/api/auth/status")
def status_autenticacao(request: Request):
    from ui import login
    configurado = login.configurado()
    token = request.cookies.get("sender_session") or request.headers.get("X-Sender-Token")
    logado = bool(token and token in _SESSOES_ATIVAS)
    return {
        "configurado": configurado,
        "logado": logado,
    }


@router.post("/api/auth/login")
def realizar_login(dados: LoginRequisicao, response: Response):
    from ui import login
    if not login.configurado():
        raise HTTPException(400, "Login não configurado: defina ADMIN_USUARIO e ADMIN_SENHA no .env e reinicie o app.")
    if not login.confere(dados.usuario, dados.senha):
        raise HTTPException(401, "Usuário ou senha inválidos.")
    token = secrets.token_hex(24)
    _SESSOES_ATIVAS.add(token)
    response.set_cookie(key="sender_session", value=token, httponly=True, samesite="lax")
    return {"status": "ok", "token": token, "usuario": dados.usuario.strip()}


@router.post("/api/auth/logout")
def realizar_logout(request: Request, response: Response):
    token = request.cookies.get("sender_session") or request.headers.get("X-Sender-Token")
    if token and token in _SESSOES_ATIVAS:
        _SESSOES_ATIVAS.discard(token)
    response.delete_cookie(key="sender_session")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Dados de Apoio e Seletores
# ---------------------------------------------------------------------------
@router.get("/api/exemplo")
def obter_exemplo(tipo: str = "padrao"):
    if tipo in ("demo", "30out", "novembro"):
        caminho = RAIZ / "data" / "interacoes_30out_02nov_2026.json"
    else:
        caminho = RAIZ / "data" / "interacoes_exemplo.json"
    if not caminho.exists():
        raise HTTPException(404, "Arquivo de exemplo não encontrado.")
    return json.loads(caminho.read_text(encoding="utf-8"))


@router.get("/api/fontes")
def obter_fontes():
    from ui import fontes
    return {
        "canais": fontes.CANAIS,
        "meses": fontes.MESES,
        "anos": fontes.anos_disponiveis(),
    }


# ---------------------------------------------------------------------------
# Lotes já processados (aviso de duplicado e reabertura)
# ---------------------------------------------------------------------------
@router.post("/api/lotes/verificar", dependencies=[Depends(exigir_admin)])
def verificar_lote_ja_processado(dados: VerificarLoteRequisicao):
    """Diz se estas mensagens já foram processadas no modo de IA atual (com Oracle ligado)."""
    if not oracle_ativo() or not dados.interacoes:
        return {"existente": None}

    from app import repository

    procurado = hash_das_mensagens(dados.interacoes)
    try:
        candidatos = repository.listar_entradas_concluidas(_modo_atual(), len(dados.interacoes))
    except Exception as exc:
        logger.exception("Falha ao procurar lote já processado (%s)", type(exc).__name__)
        return {"existente": None}

    for candidato in candidatos:
        entrada = candidato.get("entrada") or {}
        if hash_das_mensagens(entrada.get("interacoes") or []) == procurado:
            return {"existente": {
                "lote_id": candidato["id"],
                "processado_em": em_utc(candidato["finalizado_em"]),
                "origem": candidato["origem_comunidade"],
                "periodo": candidato["periodo_referencia"],
                "total": len(dados.interacoes),
            }}
    return {"existente": None}


@router.get("/api/lotes/{lote_id}", dependencies=[Depends(exigir_admin)])
def abrir_lote(lote_id: str):
    """Devolve um lote já processado no formato que o painel usa para reabrir a curadoria."""
    if not oracle_ativo():
        raise HTTPException(503, "O histórico precisa do banco Oracle configurado.")

    from app import repository

    try:
        item = repository.obter_processamento(lote_id)
    except Exception as exc:
        logger.exception("Falha ao abrir o lote %s (%s)", lote_id, type(exc).__name__)
        raise HTTPException(503, "Não foi possível consultar o lote.") from exc

    if not item or item.get("status") != "SUCESSO" or not item.get("resultado"):
        raise HTTPException(404, "Lote não encontrado ou ainda sem resultado.")
    return _estado_do_lote(item)


# ---------------------------------------------------------------------------
# Curadoria Editorial e Exportação Segura
# ---------------------------------------------------------------------------
@router.post("/api/curadoria/exportar", dependencies=[Depends(exigir_admin)])
def exportar_aprovados(dados: ExportarCuradoriaRequisicao):
    periodo = dados.periodo_referencia.strip()
    if not re.fullmatch(r"^[a-zA-Z0-9_\-]+$", periodo):
        raise HTTPException(400, f"Período de referência inválido: '{periodo}'. Caracteres inválidos detectados.")

    if oracle_ativo() and dados.lote_id:
        return _exportar_oracle(dados)

    from ui import curadoria as cur

    if dados.resultado:
        try:
            pacote = cur.montar_aprovados(
                resultado=dados.resultado,
                decisoes=dados.decisoes,
                textos=dados.textos,
                origem=dados.origem_comunidade,
                periodo=periodo,
                autorizado=dados.autorizado,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    else:
        pacote = dados.model_dump()
        pacote["periodo_referencia"] = periodo
        if pacote.get("post_linkedin") and not dados.autorizado and not pacote["post_linkedin"].get("autorizacao_membro"):
            raise HTTPException(422, "O post só pode ser exportado com a autorização do membro.")

    try:
        destino = cur.salvar_aprovados(pacote, raiz=RAIZ)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    return {"status": "ok", "caminho": str(destino)}


@router.post("/api/curadoria/decidir", dependencies=[Depends(exigir_admin)])
def salvar_decisao_curadoria(req: DecisaoRequisicao):
    from app import repositorio
    from ui import curadoria as cur

    if oracle_ativo():
        if not req.lote_id:
            return {"status": "ok", "salvo_no_banco": False}
        return _gravar_no_oracle(_salvar_decisao_oracle, req)

    salvo = False
    if repositorio.banco_configurado() and isinstance(req.lote_id, int):
        try:
            textos = cur.textos_do_ativo(req.chave, req.textos)
            repositorio.salvar_decisao(
                lote_id=req.lote_id,
                chave=req.chave,
                decisao=req.decisao,
                conteudo_editado=textos,
                autorizacao=req.autorizacao,
            )
            salvo = True
        except Exception as e:
            print(f"[Supabase] Erro ao salvar decisão: {e}")
    return {"status": "ok", "salvo_no_banco": salvo}


@router.post("/api/alertas/tratar", dependencies=[Depends(exigir_admin)])
def tratar_alerta_comunidade(req: AlertaTratarRequisicao):
    from app import repositorio

    if oracle_ativo():
        if not req.lote_id:
            return {"status": "ok", "salvo_no_banco": False}
        return _gravar_no_oracle(_tratar_alerta_oracle, req)

    salvo = False
    if repositorio.banco_configurado() and isinstance(req.lote_id, int):
        try:
            repositorio.atualizar_alerta(
                lote_id=req.lote_id,
                ordem=req.ordem,
                status=req.status,
            )
            salvo = True
        except Exception as e:
            print(f"[Supabase] Erro ao atualizar alerta: {e}")
    return {"status": "ok", "salvo_no_banco": salvo}


# ---------------------------------------------------------------------------
# Histórico e Insights
# ---------------------------------------------------------------------------
@router.get("/api/insights", dependencies=[Depends(exigir_admin)])
def obter_insights(
    inicio: str | None = None,
    fim: str | None = None,
    modo: str | None = None,
    comunidade: str | None = None,
    canal: str | None = None,
    demo: bool = False,
):
    import pandas as pd
    from app import repositorio
    from ui import insights as ins

    oracle = oracle_ativo()
    banco_ok = oracle or repositorio.banco_configurado()
    if not banco_ok and not demo:
        return {
            "banco_configurado": False,
            "mensagem": "O histórico precisa do banco Oracle configurado (COMMUNITYLAB_DB_MODE=oracle no .env).",
        }

    modo_busca = modo or repositorio.modo_atual()

    if oracle and not demo:
        from datetime import date, timedelta
        from app import repository

        hoje = repositorio.hoje()
        try:
            d_inicio = date.fromisoformat(inicio) if inicio else (hoje - timedelta(weeks=8))
            d_fim = date.fromisoformat(fim) if fim else hoje
        except ValueError as exc:
            raise HTTPException(422, "Datas devem estar no formato AAAA-MM-DD.") from exc
        comunidades = [comunidade] if comunidade else None
        canais = [canal] if canal else None

        try:
            interacoes = repository.consultar_interacoes_insights(d_inicio, d_fim, modo_busca, comunidades, canais)
            lista_ativos = repository.consultar_ativos_insights(d_inicio, d_fim, modo_busca, comunidades, canais)
            opcoes = repository.opcoes_filtros_insights(modo_busca)
            alertas = repository.consultar_alertas_insights(d_inicio, d_fim, modo_busca, comunidades, canais)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:
            logger.exception("Falha ao consultar Insights no Oracle (%s)", type(exc).__name__)
            raise HTTPException(503, "Não foi possível consultar o histórico no Oracle.") from exc

        df = pd.DataFrame(interacoes, columns=["lote_id", "data", "comunidade", "canal", "sentimento", "topico", "rota",
                                               "autor", "tipo"])
        if not df.empty:
            df["data"] = pd.to_datetime(df["data"]).dt.date
        ativos = pd.DataFrame(lista_ativos, columns=["lote_id", "chave", "tipo", "status"])
    elif banco_ok and not demo:
        from datetime import date, timedelta
        hoje = repositorio.hoje()
        d_inicio = date.fromisoformat(inicio) if inicio else (hoje - timedelta(weeks=8))
        d_fim = date.fromisoformat(fim) if fim else hoje
        comunidades = [comunidade] if comunidade else None
        canais = [canal] if canal else None

        df = repositorio.consultar_interacoes(d_inicio, d_fim, modo_busca, comunidades=comunidades, canais=canais)
        ativos = repositorio.consultar_ativos(d_inicio, d_fim, modo_busca, comunidades=comunidades, canais=canais)
        opcoes = repositorio.opcoes_filtros(modo_busca)
        alertas = []  # o histórico antigo (Supabase) não guarda a triagem para esta tela
    else:
        caminho_demo = RAIZ / "data" / "interacoes_30out_02nov_2026.json"
        if not caminho_demo.exists():
            caminho_demo = RAIZ / "data" / "interacoes_exemplo.json"
        lote_json = json.loads(caminho_demo.read_text(encoding="utf-8"))
        from app.schemas import LoteEntrada
        lote = LoteEntrada(**lote_json)
        from app.grafo import processar
        from app.repositorio import linhas_do_lote
        resp = processar(lote)
        linhas = linhas_do_lote(lote, resp)
        df = pd.DataFrame(linhas["interacoes"])
        df["comunidade"] = lote.origem_comunidade
        df["lote_id"] = "demo"
        por_ordem = df.set_index("ordem")
        alertas = [{"lote_id": "demo", "ordem": al["ordem"], "data": por_ordem.at[al["ordem"], "data"],
                    "canal": por_ordem.at[al["ordem"], "canal"], "autor": al["autor"], "motivo": al["motivo"],
                    "status": "PENDENTE", "criado_em": None} for al in linhas["alertas"]]
        if canal:
            df = df[df["canal"] == canal]
        if comunidade:
            df = df[df["comunidade"] == comunidade]
        if inicio:
            df = df[pd.to_datetime(df["data"]) >= pd.to_datetime(inicio)]
        if fim:
            df = df[pd.to_datetime(df["data"]) <= pd.to_datetime(fim)]
        ordens = set(df["ordem"])
        alertas = [a for a in alertas if a["ordem"] in ordens]
        d_inicio = pd.to_datetime(df["data"]).min().date() if not df.empty else None
        d_fim = pd.to_datetime(df["data"]).max().date() if not df.empty else None

        ativos = pd.DataFrame(linhas["ativos"])
        if "status" not in ativos.columns:
            status_map = {"post": "aprovado", "newsletter": "pendente"}
            ativos["status"] = [
                status_map.get(k, "aprovado" if i % 2 == 0 else "pendente")
                for i, k in enumerate(ativos.get("chave", []))
            ]
        opcoes = {
            "comunidades": sorted(list(set(df["comunidade"].dropna()))),
            "canais": sorted(list(set(df["canal"].dropna()))),
        }

    numeros = ins.numeros_periodo(df)
    numeros = {k: float(v) if isinstance(v, (float, int)) else v for k, v in numeros.items()}

    s_dia = ins.sentimento_por_dia(df)
    v_canal = ins.volume_por_canal(df)
    s_div = ins.sentimento_divergente(df)
    topicos = ins.topicos_mais_falados(df, n=10)
    rotas = ins.rotas_geradas(df)
    aproveitamento = ins.aproveitamento_ativos(ativos)

    def df_to_list(d: pd.DataFrame):
        if d.empty:
            return []
        c = d.copy()
        if "data" in c.columns:
            c["data"] = c["data"].astype(str)
        return json.loads(c.to_json(orient="records"))

    return {
        "banco_configurado": banco_ok,
        "modo_demo": demo or not banco_ok,
        "modo": modo_busca,
        "opcoes": opcoes,
        "numeros": numeros,
        "sentimento_por_dia": df_to_list(s_dia),
        "volume_por_canal": df_to_list(v_canal),
        "sentimento_divergente": df_to_list(s_div),
        "topicos": df_to_list(topicos),
        "rotas": df_to_list(rotas),
        "aproveitamento": aproveitamento,
        # Painel web (tela Insights redesenhada)
        "periodo": {"inicio": str(d_inicio) if d_inicio else None, "fim": str(d_fim) if d_fim else None},
        "resumo": ins.resumo(df, ativos, alertas),
        "sentimento_no_tempo": ins.sentimento_no_tempo(df),
        "canais_sentimento": ins.canais_sentimento(df),
        "topicos_tom": ins.topicos_tom(df),
        "atividade_canal_tempo": ins.atividade_canal_tempo(df),
        "aproveitamento_por_tipo": ins.aproveitamento_por_tipo(ativos),
        "alertas_triagem": ins.alertas_triagem(alertas),
        "membros": ins.membros_engajados(df),
    }
