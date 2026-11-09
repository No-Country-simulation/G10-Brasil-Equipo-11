"""Rotas REST complementares para a interface Web Vanilla e integração frontend.

Isoladas em APIRouter para evitar conflitos de merge e garantir arquitetura limpa.
"""
import json
import re
import secrets
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

RAIZ = Path(__file__).resolve().parent.parent

router = APIRouter(tags=["web"])

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
    lote_id: Optional[int] = None
    chave: str
    decisao: str
    textos: dict[str, str] = {}
    autorizacao: bool = False


class AlertaTratarRequisicao(BaseModel):
    lote_id: Optional[int] = None
    ordem: int
    status: str


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
# Curadoria Editorial e Exportação Segura
# ---------------------------------------------------------------------------
@router.post("/api/curadoria/exportar", dependencies=[Depends(exigir_admin)])
def exportar_aprovados(dados: ExportarCuradoriaRequisicao):
    periodo = dados.periodo_referencia.strip()
    if not re.fullmatch(r"^[a-zA-Z0-9_\-]+$", periodo):
        raise HTTPException(400, f"Período de referência inválido: '{periodo}'. Caracteres inválidos detectados.")

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

    salvo = False
    if repositorio.banco_configurado() and req.lote_id:
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

    salvo = False
    if repositorio.banco_configurado() and req.lote_id:
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

    banco_ok = repositorio.banco_configurado()
    if not banco_ok and not demo:
        return {
            "banco_configurado": False,
            "mensagem": "O histórico precisa do banco Supabase configurado via DATABASE_URL no .env.",
        }

    modo_busca = modo or repositorio.modo_atual()

    if banco_ok and not demo:
        from datetime import date, timedelta
        hoje = repositorio.hoje()
        d_inicio = date.fromisoformat(inicio) if inicio else (hoje - timedelta(weeks=8))
        d_fim = date.fromisoformat(fim) if fim else hoje
        comunidades = [comunidade] if comunidade else None
        canais = [canal] if canal else None

        df = repositorio.consultar_interacoes(d_inicio, d_fim, modo_busca, comunidades=comunidades, canais=canais)
        ativos = repositorio.consultar_ativos(d_inicio, d_fim, modo_busca, comunidades=comunidades, canais=canais)
        opcoes = repositorio.opcoes_filtros(modo_busca)
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
        if canal:
            df = df[df["canal"] == canal]
        if comunidade:
            df = df[df["comunidade"] == comunidade]
        if inicio:
            df = df[pd.to_datetime(df["data"]) >= pd.to_datetime(inicio)]
        if fim:
            df = df[pd.to_datetime(df["data"]) <= pd.to_datetime(fim)]

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
    }
