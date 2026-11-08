"""API do Sender AI. Rode com: uvicorn app.main:app --reload"""
import json
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response  # noqa: E402
from pydantic import BaseModel, ValidationError  # noqa: E402

from communitylab.adapter import carregar_lote_bytes  # noqa: E402
from .grafo import processar  # noqa: E402
from .llm import modo_mock  # noqa: E402
from .schemas import LoteEntrada, RespostaProcessamento  # noqa: E402

app = FastAPI(title="Sender AI", version="0.1.0")


@app.get("/saude")
def saude():
    return {"status": "ok", "modo_llm": "mock" if modo_mock() else "gemini"}


@app.post("/processar", response_model=RespostaProcessamento)
async def processar_lote(request: Request):
    """Processa um lote de interações enviado como JSON (LoteEntrada) ou upload multipart (campo 'arquivo')."""
    content_type = (request.headers.get("content-type") or "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("arquivo") or form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(422, "Arquivo ausente. Envie o campo 'arquivo' via multipart/form-data.")

        conteudo = await upload.read()
        nome_arquivo = getattr(upload, "filename", None) or "lote.csv"
        origem = form.get("origem_comunidade")
        periodo = form.get("periodo_referencia")

        try:
            lote = carregar_lote_bytes(
                conteudo=conteudo,
                nome_arquivo=str(nome_arquivo),
                origem_comunidade=str(origem) if isinstance(origem, str) and origem.strip() else None,
                periodo_referencia=str(periodo) if isinstance(periodo, str) and periodo.strip() else None,
            )
        except (ValueError, ValidationError) as exc:
            raise HTTPException(422, str(exc)) from exc
    else:
        try:
            dados = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(422, "O corpo da requisição não é um JSON válido.") from exc

        try:
            lote = LoteEntrada.model_validate(dados)
        except ValidationError as exc:
            raise HTTPException(422, detail=json.loads(exc.json())) from exc

    if not lote.interacoes:
        raise HTTPException(400, "O lote não tem interações.")

    return processar(lote)


# ---------------------------------------------------------------------------
# Endpoints complementares para a interface Web Vanilla
# ---------------------------------------------------------------------------
from pathlib import Path
from fastapi.staticfiles import StaticFiles

RAIZ = Path(__file__).resolve().parent.parent


@app.get("/api/exemplo")
def obter_exemplo(tipo: str = "padrao"):
    if tipo in ("demo", "30out", "novembro"):
        caminho = RAIZ / "data" / "interacoes_30out_02nov_2026.json"
    else:
        caminho = RAIZ / "data" / "interacoes_exemplo.json"
    if not caminho.exists():
        raise HTTPException(404, "Arquivo de exemplo não encontrado.")
    return json.loads(caminho.read_text(encoding="utf-8"))


@app.get("/api/fontes")
def obter_fontes():
    from ui import fontes
    return {
        "canais": fontes.CANAIS,
        "meses": fontes.MESES,
        "anos": fontes.anos_disponiveis(),
    }


@app.post("/api/curadoria/exportar")
async def exportar_aprovados(request: Request):
    dados = await request.json()
    from ui import curadoria as cur
    destino = cur.salvar_aprovados(dados, raiz=RAIZ)
    return {"status": "ok", "caminho": str(destino)}


# ---------------------------------------------------------------------------
# Autenticação de Administrador e Histórico / Insights
# ---------------------------------------------------------------------------
_SESSOES_ATIVAS: set[str] = set()


class LoginRequisicao(BaseModel):
    usuario: str = ""
    senha: str = ""


@app.get("/api/auth/status")
def status_autenticacao(request: Request):
    from ui import login
    configurado = login.configurado()
    token = request.cookies.get("sender_session") or request.headers.get("X-Sender-Token")
    logado = bool(token and token in _SESSOES_ATIVAS)
    return {
        "configurado": configurado,
        "logado": logado,
    }


@app.post("/api/auth/login")
def realizar_login(dados: LoginRequisicao, response: Response):
    import secrets
    from ui import login
    if not login.configurado():
        raise HTTPException(400, "Login não configurado: defina ADMIN_USUARIO e ADMIN_SENHA no .env e reinicie o app.")
    if not login.confere(dados.usuario, dados.senha):
        raise HTTPException(401, "Usuário ou senha inválidos.")
    token = secrets.token_hex(24)
    _SESSOES_ATIVAS.add(token)
    response.set_cookie(key="sender_session", value=token, httponly=True, samesite="lax")
    return {"status": "ok", "token": token, "usuario": dados.usuario.strip()}


@app.post("/api/auth/logout")
def realizar_logout(request: Request, response: Response):
    token = request.cookies.get("sender_session") or request.headers.get("X-Sender-Token")
    if token and token in _SESSOES_ATIVAS:
        _SESSOES_ATIVAS.discard(token)
    response.delete_cookie(key="sender_session")
    return {"status": "ok"}


@app.get("/api/insights")
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


PASTA_WEB = RAIZ / "web"
if PASTA_WEB.exists():
    app.mount("/", StaticFiles(directory=str(PASTA_WEB), html=True), name="web")

