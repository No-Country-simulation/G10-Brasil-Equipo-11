"""Visual do painel, seguindo a prévia aprovada pela equipe.

Paleta: azul para positivo e ações, laranja para negativo e alertas (dá para distinguir
também por quem não enxerga bem vermelho e verde). Fonte: IBM Plex Sans e IBM Plex Mono.

IMPORTANTE: todo texto que vem das mensagens da comunidade passa por esc() antes de
entrar em HTML. Uma mensagem com <script> não pode virar código na tela.
"""
from html import escape

import streamlit as st

AZUL = "#2B59C3"
AZUL_ESCURO = "#1E3F8F"
LARANJA = "#D9762F"
LARANJA_ESCURO = "#8A3209"
TINTA = "#15171C"
CINZA = "#555D6B"

SENTIMENTOS = [
    ("Altamente Positivo", "#1E3F8F"),
    ("Positivo", "#6C8FE0"),
    ("Neutro", "#C3C8D1"),
    ("Negativo", "#D9762F"),
    ("Altamente Negativo", "#8A3209"),
]
COR_SENTIMENTO = dict(SENTIMENTOS)

ROTAS = {
    "faq": {"nome": "FAQ", "barra": CINZA, "fundo": "#EEF1F6", "texto": "#33373F"},
    "case_sucesso": {"nome": "Case de sucesso", "barra": AZUL, "fundo": "#E8EEFB", "texto": AZUL_ESCURO},
    "alerta": {"nome": "Alerta", "barra": LARANJA, "fundo": "#FCEBDF", "texto": LARANJA_ESCURO},
    "nenhuma": {"nome": "Sem ação", "barra": "#C3C8D1", "fundo": "#FFFFFF", "texto": CINZA},
}
ORDEM_ROTAS = ["faq", "case_sucesso", "alerta", "nenhuma"]


def esc(texto) -> str:
    return escape(str(texto), quote=True)


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stButton button, .stTextInput input, .stTextArea textarea {{
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
}}
.block-container {{ max-width: 1280px; padding-top: 3.2rem; }}
/* Menu de telas e filtro de rota: rádios desenhados como abas */
.st-key-nav [data-testid="stRadioGroup"], .st-key-filtro [data-testid="stRadioGroup"] {{ gap: 4px; flex-wrap: wrap; }}
.st-key-nav [data-testid="stRadioOption"], .st-key-filtro [data-testid="stRadioOption"] {{
  padding: 8px 14px; margin: 0; border-radius: 8px; cursor: pointer; min-height: 40px; align-items: center;
}}
.st-key-nav [data-testid="stRadioOption"] > div > div:first-child,
.st-key-filtro [data-testid="stRadioOption"] > div > div:first-child {{ display: none; }}
.st-key-nav [data-testid="stRadioOption"] p {{ font-weight: 500; color: {CINZA}; font-size: 15px; }}
.st-key-nav [data-testid="stRadioOption"][data-selected="true"] {{ background: #E4E9F2; }}
.st-key-nav [data-testid="stRadioOption"][data-selected="true"] p {{ color: {TINTA}; }}
.st-key-filtro [data-testid="stRadioOption"] {{ border: 1px solid #D5DAE1; background: #FFFFFF; }}
.st-key-filtro [data-testid="stRadioOption"][data-selected="true"] {{ border-color: {AZUL}; background: #F3F6FD; }}
.st-key-nav [data-testid="stRadioOption"]:has(input:focus-visible),
.st-key-filtro [data-testid="stRadioOption"]:has(input:focus-visible) {{ outline: 2px solid {AZUL}; outline-offset: 2px; }}
.cl-kpi-rotulo {{ font-size: 14px; color: {TINTA}; }}
.cl-kpi-valor {{ display: flex; align-items: center; gap: 8px; font-size: 20px; font-weight: 600; margin: 12px 0 6px; }}
h1 {{ font-weight: 700 !important; letter-spacing: -0.02em; }}
.cl-marca {{ display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 20px; color: {TINTA}; }}
.cl-contexto {{ display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 10px; font-size: 13px; color: {CINZA}; }}
.cl-mono {{ font-family: 'IBM Plex Mono', monospace; }}
.cl-selo {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; }}
.cl-modo-mock {{ border: 1px solid #D8B48A; background: #FFF6EC; color: #8A3A0B; }}
.cl-modo-real {{ border: 1px solid #C6D3F3; background: #E8EEFB; color: {AZUL_ESCURO}; }}
.cl-sub {{ color: {CINZA}; margin-top: -0.6rem; }}
.cl-rotulo {{ font-size: 12px; font-weight: 600; color: {CINZA}; text-transform: uppercase; letter-spacing: 0.04em; }}
.cl-citacao {{ background: #F7F8FA; border-radius: 10px; padding: 12px 14px; color: #33373F; font-size: 14px; }}
.cl-alerta {{ background: #FFF6EC; border-radius: 10px; padding: 14px 16px; }}
.cl-barra-sent {{ display: flex; height: 28px; border-radius: 6px; overflow: hidden; gap: 2px; margin: 4px 0 12px; }}
.cl-legenda {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 6px 14px; font-size: 14px; }}
.cl-legenda div {{ display: flex; align-items: center; gap: 8px; }}
.cl-legenda b {{ margin-left: auto; }}
.cl-quad {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; flex: none; }}
.cl-rota {{ display: grid; grid-template-columns: 140px minmax(0, 1fr) 28px; align-items: center; gap: 12px; margin: 8px 0; font-size: 14px; }}
.cl-trilho {{ height: 14px; background: #EEF1F6; border-radius: 4px; overflow: hidden; }}
.cl-trilho span {{ display: block; height: 100%; border-radius: 4px; }}
div[data-testid="stMetricValue"] {{ font-weight: 700; }}
</style>
"""


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def selo(texto: str, fundo: str, cor: str, borda: str | None = None) -> str:
    borda_css = f"border: 1px solid {borda};" if borda else ""
    return f'<span class="cl-selo" style="background:{fundo};color:{cor};{borda_css}">{esc(texto)}</span>'


def selo_rota(rota: str) -> str:
    r = ROTAS[rota]
    return selo(r["nome"], r["fundo"], r["texto"], "#D5DAE1" if rota == "nenhuma" else None)


def barra_sentimento(contagem: dict[str, int]) -> str:
    total = sum(contagem.values()) or 1
    partes = "".join(
        f'<div style="flex:{contagem.get(nome, 0)};background:{cor}"></div>'
        for nome, cor in SENTIMENTOS if contagem.get(nome, 0)
    )
    rotulo = ", ".join(f"{contagem.get(n, 0)} {n.lower()}" for n, _ in SENTIMENTOS if contagem.get(n, 0))
    legenda = "".join(
        f'<div><span class="cl-quad" style="background:{cor}"></span>{esc(nome)}<b>{contagem.get(nome, 0)}</b></div>'
        for nome, cor in SENTIMENTOS
    )
    return (f'<div class="cl-barra-sent" role="img" aria-label="Sentimento: {esc(rotulo)} de {total}">{partes}</div>'
            f'<div class="cl-legenda">{legenda}</div>')


def barras_rotas(contagem: dict[str, int]) -> str:
    total = sum(contagem.values()) or 1
    linhas = []
    for rota in ORDEM_ROTAS:
        n = contagem.get(rota, 0)
        r = ROTAS[rota]
        linhas.append(
            f'<div class="cl-rota"><span>{r["nome"]}</span>'
            f'<span class="cl-trilho"><span style="width:{round(100 * n / total)}%;background:{r["barra"]}"></span></span>'
            f'<b style="text-align:right">{n}</b></div>'
        )
    return "".join(linhas)


MARCA_SVG = (
    '<svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">'
    f'<rect x="1" y="1" width="24" height="24" rx="7" stroke="{AZUL}" stroke-width="2"></rect>'
    f'<path d="M8 15.5c1.4 1.6 3.1 2.4 5 2.4s3.6-.8 5-2.4M9 10h.01M17 10h.01" stroke="{AZUL}" '
    'stroke-width="2.2" stroke-linecap="round"></path></svg>'
)
