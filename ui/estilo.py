"""Visual do painel, com a paleta da identidade Sender AI, em tema claro e escuro.

Ciano para positivo, laranja e rosa para negativo e alertas: dá para distinguir também por
quem não enxerga bem vermelho e verde. O lima fica para ações e aprovações, nunca para sentimento.
Fonte: IBM Plex Sans e IBM Plex Mono.

O tema pode mudar com a página aberta, sem o Python rodar de novo (st.context.theme fica defasado):
- HTML e CSS usam css(), que devolve light-dark(): o navegador troca sozinho.
- Gráficos não entendem light-dark(), então os dados têm uma paleta só, legível nos dois fundos (DADO_*).

IMPORTANTE: todo texto que vem das mensagens da comunidade passa por esc() antes de
entrar em HTML. Uma mensagem com <script> não pode virar código na tela.
"""
from base64 import b64encode
from html import escape
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO = ASSETS / "logo_sender_ai.png"
ICONE = ASSETS / "icone_sender_ai.png"

# nome: (tema claro, tema escuro)
CORES = {
    "fundo": ("#F5F7F8", "#050A0E"),
    "superficie": ("#FFFFFF", "#0C1926"),
    "superficie_2": ("#EEF2F5", "#122436"),
    "linha": ("#DDE3E8", "#1B3347"),
    "texto": ("#0B1520", "#F0F6FC"),
    "cinza": ("#5A6B7C", "#7D93A8"),
    "apagado": ("#A9B4BF", "#566B80"),
    "neutro_texto": ("#3F4C59", "#B6C4D2"),
    "lima": ("#4D7C0F", "#C9F36A"),
    "lima_fundo": ("#B5E847", "#C9F36A"),
    "lima_tinta": ("#0D1705", "#071204"),
    "ciano": ("#00708C", "#00E5FF"),
    "laranja": ("#B45309", "#FFB84D"),
    "rosa": ("#C81E47", "#FF5C7C"),
    "lima_suave": ("rgba(181, 232, 71, 0.3)", "rgba(201, 243, 106, 0.12)"),
    "ciano_suave": ("rgba(0, 136, 170, 0.12)", "rgba(0, 229, 255, 0.12)"),
    "laranja_suave": ("rgba(224, 138, 30, 0.16)", "rgba(255, 184, 77, 0.14)"),
    "neutro_suave": ("rgba(90, 107, 124, 0.14)", "rgba(125, 147, 168, 0.16)"),
}


def css(nome: str) -> str:
    claro, escuro = CORES[nome]
    return f"light-dark({claro}, {escuro})"


SUPERFICIE = css("superficie")
SUPERFICIE_2 = css("superficie_2")
LINHA = css("linha")
TEXTO = css("texto")
CINZA = css("cinza")
APAGADO = css("apagado")
LIMA = css("lima")
LIMA_FUNDO = css("lima_fundo")
LIMA_TINTA = css("lima_tinta")
LIMA_SUAVE = css("lima_suave")
CIANO = css("ciano")
LARANJA = css("laranja")

# (fundo, texto) dos selos
SELO_INFO = (css("ciano_suave"), CIANO)
SELO_SUCESSO = (LIMA_SUAVE, LIMA)
SELO_AVISO = (css("laranja_suave"), LARANJA)
SELO_NEUTRO = (css("neutro_suave"), css("neutro_texto"))

DADO_CIANO = "#0097B8"
DADO_POSITIVO = "#5B9FB3"
DADO_NEUTRO = "#7D8FA1"
DADO_LARANJA = "#D9822B"
DADO_ROSA = "#E0456B"
DADO_LIMA = "#6FA012"
DADO_DESCARTADO = "#566B80"
DADO_TEXTO = "#6B7F93"  # números dentro dos gráficos: sem cor definida, sairiam pretos no tema escuro

SENTIMENTOS = [
    ("Altamente Positivo", DADO_CIANO),
    ("Positivo", DADO_POSITIVO),
    ("Neutro", DADO_NEUTRO),
    ("Negativo", DADO_LARANJA),
    ("Altamente Negativo", DADO_ROSA),
]
COR_SENTIMENTO = dict(SENTIMENTOS)

ROTAS = {
    "faq": {"nome": "FAQ", "barra": DADO_CIANO, "fundo": SELO_INFO[0], "texto": CIANO},
    "case_sucesso": {"nome": "Case de sucesso", "barra": DADO_LIMA, "fundo": SELO_SUCESSO[0], "texto": LIMA},
    "alerta": {"nome": "Alerta", "barra": DADO_LARANJA, "fundo": SELO_AVISO[0], "texto": LARANJA},
    "nenhuma": {"nome": "Sem ação", "barra": DADO_NEUTRO, "fundo": "transparent", "texto": CINZA},
}
ORDEM_ROTAS = ["faq", "case_sucesso", "alerta", "nenhuma"]


def esc(texto) -> str:
    return escape(str(texto), quote=True)


# O logo é uma máscara sobre a cor do texto: branco no tema escuro, preto no claro, com um arquivo só.
MASCARA_LOGO = f'url("data:image/png;base64,{b64encode(LOGO.read_bytes()).decode()}") center / contain no-repeat'

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
.st-key-nav [data-testid="stRadioOption"][data-selected="true"] {{ background: {LIMA_SUAVE}; }}
.st-key-nav [data-testid="stRadioOption"][data-selected="true"] p {{ color: {LIMA}; }}
.st-key-filtro [data-testid="stRadioOption"] {{ border: 1px solid {LINHA}; background: {SUPERFICIE}; }}
.st-key-filtro [data-testid="stRadioOption"][data-selected="true"] {{ border-color: {LIMA}; background: {LIMA_SUAVE}; }}
.st-key-nav [data-testid="stRadioOption"]:has(input:focus-visible),
.st-key-filtro [data-testid="stRadioOption"]:has(input:focus-visible) {{ outline: 2px solid {LIMA}; outline-offset: 2px; }}
.cl-kpi-rotulo {{ font-size: 14px; color: {TEXTO}; }}
.cl-kpi-valor {{ display: flex; align-items: center; gap: 8px; font-size: 20px; font-weight: 600; margin: 12px 0 6px; }}
h1 {{ font-weight: 700 !important; letter-spacing: -0.02em; }}
.cl-logo {{ width: 79px; height: 76px; background: {TEXTO}; -webkit-mask: {MASCARA_LOGO}; mask: {MASCARA_LOGO}; }}
.stButton button[kind="primary"]:not(:disabled), .stDownloadButton button[kind="primary"]:not(:disabled),
.stFormSubmitButton button[kind="primaryFormSubmit"]:not(:disabled) {{ color: {LIMA_TINTA}; }}
.stButton button[kind="primary"]:not(:disabled) p, .stDownloadButton button[kind="primary"]:not(:disabled) p,
.stFormSubmitButton button[kind="primaryFormSubmit"]:not(:disabled) p {{ color: {LIMA_TINTA}; font-weight: 600; }}
.cl-contexto {{ display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 10px; font-size: 13px; color: {CINZA}; }}
.cl-mono {{ font-family: 'IBM Plex Mono', monospace; }}
.cl-selo {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; }}
.cl-sub {{ color: {CINZA}; margin-top: -0.6rem; }}
.cl-origem {{ margin-top: 14px; font-size: 14px; color: {CINZA}; }}
.cl-origem b {{ color: {TEXTO}; }}
.cl-mensagem {{ max-width: 68ch; margin: 6px 0 18px; padding: 14px 18px; background: {SUPERFICIE_2};
  border-radius: 4px 16px 16px 16px; color: {TEXTO}; font-size: 20px; line-height: 1.45; }}
div.st-key-fila {{ gap: 2px; }}
div.st-key-fila button, div.st-key-fila button:not(:disabled) {{ justify-content: flex-start; min-height: 38px; padding: 6px 10px;
  background: transparent; border-color: transparent; }}
div.st-key-fila button:hover {{ background: {SUPERFICIE_2}; border-color: transparent; }}
div.st-key-fila button > div {{ justify-content: flex-start; width: 100%; min-width: 0; }}
div.st-key-fila button > div > span {{ justify-content: flex-start; min-width: 0; }}
div.st-key-fila button [data-testid="stMarkdownContainer"] {{ min-width: 0; }}
div.st-key-fila button p {{ overflow: hidden; color: {CINZA}; font-size: 14px; font-weight: 400; text-align: left;
  text-overflow: ellipsis; white-space: nowrap; }}
div.st-key-fila button[kind="primary"]:not(:disabled) {{ background: {LIMA_SUAVE}; }}
div.st-key-fila button[kind="primary"]:not(:disabled) p {{ color: {LIMA}; font-weight: 600; }}
div.st-key-fila button[kind="primary"]:not(:disabled) span {{ color: {LIMA}; }}
.cl-alerta {{ background: {SELO_AVISO[0]}; border-radius: 10px; padding: 14px 16px; }}
.cl-barra-sent {{ display: flex; height: 28px; border-radius: 6px; overflow: hidden; gap: 2px; margin: 4px 0 12px; }}
.cl-legenda {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 6px 14px; font-size: 14px; }}
.cl-legenda div {{ display: flex; align-items: center; gap: 8px; }}
.cl-legenda b {{ margin-left: auto; }}
.cl-quad {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; flex: none; }}
.cl-rota {{ display: grid; grid-template-columns: 140px minmax(0, 1fr) 28px; align-items: center; gap: 12px; margin: 8px 0; font-size: 14px; }}
.cl-trilho {{ height: 14px; background: {SUPERFICIE_2}; border-radius: 4px; overflow: hidden; }}
.cl-trilho span {{ display: block; height: 100%; border-radius: 4px; }}
div[data-testid="stMetricValue"], .cl-kpi-valor, .cl-legenda b, .cl-rota b {{
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}}
/* Feedback tátil e micro-interações (Emil Kowalski) */
.stButton button, .stDownloadButton button {{
  transition: transform 0.15s cubic-bezier(0.23, 1, 0.32, 1), background-color 0.15s ease, border-color 0.15s ease !important;
}}
.stButton button:active:not(:disabled), .stDownloadButton button:active:not(:disabled) {{
  transform: scale(0.97) !important;
}}
/* Selo de comunidade no cabeçalho operacional */
.cl-origem-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  background: {SUPERFICIE_2};
  color: {TEXTO};
  border: 1px solid {LINHA};
}}
/* Acessibilidade de foco e preferência de movimento reduzido */
*:focus-visible {{
  outline: 2px solid {LIMA} !important;
  outline-offset: 2px !important;
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }}
}}
</style>
"""


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def selo(texto: str, fundo: str, cor: str, borda: str | None = None) -> str:
    borda_css = f"border: 1px solid {borda};" if borda else ""
    return f'<span class="cl-selo" style="background:{fundo};color:{cor};{borda_css}">{esc(texto)}</span>'


def selo_rota(rota: str) -> str:
    r = ROTAS[rota]
    return selo(r["nome"], r["fundo"], r["texto"], LINHA if rota == "nenhuma" else None)


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


def logo_html() -> str:
    return '<div class="cl-logo" role="img" aria-label="Sender AI"></div>'
