"""Gera os arquivos que a pessoa curadora baixa na tela de Curadoria: PDF, CSV ou JSON.

Recebe o pacote de aprovados (o mesmo de ui.curadoria.montar_aprovados) e devolve os bytes
do arquivo. Nada é gravado em disco aqui: o download vai direto para o navegador.
"""
from __future__ import annotations

import csv
import io
import json
import re
from xml.sax.saxutils import escape

FORMATOS = {
    "pdf": "application/pdf",
    "csv": "text/csv; charset=utf-8",
    "json": "application/json; charset=utf-8",
}

COLUNAS_CSV = ["tipo", "titulo", "conteudo", "membro", "autorizacao_do_membro", "potencial_engajamento", "origem"]


def nome_do_arquivo(pacote: dict, formato: str) -> str:
    periodo = re.sub(r"[^A-Za-z0-9_-]+", "-", str(pacote.get("periodo_referencia") or "")).strip("-") or "periodo"
    return f"aprovados_{periodo}.{formato}"


def total_de_ativos(pacote: dict) -> int:
    return (
        int(bool(pacote.get("post_linkedin")))
        + int(bool(pacote.get("destaque_newsletter_semanal")))
        + len(pacote.get("sugestao_conteudo_faq") or [])
    )


def gerar(pacote: dict, formato: str) -> bytes:
    if formato == "pdf":
        return gerar_pdf(pacote)
    if formato == "csv":
        return gerar_csv(pacote)
    if formato == "json":
        return json.dumps(pacote, ensure_ascii=False, indent=2).encode("utf-8")
    raise ValueError(f"Formato não suportado: {formato}. Use pdf, csv ou json.")


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def _celula(valor) -> str:
    """Texto seguro para planilha: uma célula que começa com = + - @ seria lida como fórmula."""
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def linhas_csv(pacote: dict) -> list[dict]:
    linhas = []
    post = pacote.get("post_linkedin")
    if post:
        linhas.append({
            "tipo": "Post LinkedIn",
            "titulo": post.get("titulo"),
            "conteudo": post.get("copy"),
            "membro": post.get("membro"),
            "autorizacao_do_membro": "sim" if post.get("autorizacao_membro") else "não",
            "potencial_engajamento": post.get("potencial_engajamento"),
        })
    news = pacote.get("destaque_newsletter_semanal")
    if news:
        linhas.append({
            "tipo": "Newsletter",
            "titulo": news.get("chamada"),
            "conteudo": news.get("resumo"),
            "origem": news.get("secao"),
        })
    for faq in pacote.get("sugestao_conteudo_faq") or []:
        linhas.append({
            "tipo": "FAQ",
            "titulo": faq.get("tema"),
            "conteudo": faq.get("conteudo"),
            "origem": faq.get("origem"),
        })
    return linhas


def gerar_csv(pacote: dict) -> bytes:
    """Ponto e vírgula e UTF-8 com BOM: é o que o Excel em português abre com os acentos certos."""
    saida = io.StringIO(newline="")
    escritor = csv.DictWriter(saida, fieldnames=COLUNAS_CSV, delimiter=";", lineterminator="\r\n")
    escritor.writeheader()
    for linha in linhas_csv(pacote):
        escritor.writerow({coluna: _celula(linha.get(coluna)) for coluna in COLUNAS_CSV})
    return saida.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
_TROCAS = {"→": "->", "•": "·", "✓": "ok", " ": " ", "​": "", "️": ""}


def _texto_pdf(valor) -> str:
    """As fontes padrão do PDF cobrem o português (cp1252). O que estiver fora, como emoji, sai do texto."""
    texto = "" if valor is None else str(valor)
    for de, para in _TROCAS.items():
        texto = texto.replace(de, para)
    texto = texto.encode("cp1252", "ignore").decode("cp1252")
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    return escape(texto).replace("\n", "<br/>")


def gerar_pdf(pacote: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    tinta, cinza, verde = colors.HexColor("#15171C"), colors.HexColor("#5A6270"), colors.HexColor("#3F6B12")
    titulo = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=tinta)
    meta = ParagraphStyle("meta", fontName="Helvetica", fontSize=9.5, leading=13, textColor=cinza)
    rotulo = ParagraphStyle("rotulo", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=verde,
                            spaceBefore=14, spaceAfter=3)
    subtitulo = ParagraphStyle("subtitulo", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=tinta,
                               spaceAfter=4)
    corpo = ParagraphStyle("corpo", fontName="Helvetica", fontSize=10.5, leading=15, textColor=tinta,
                           alignment=TA_LEFT, spaceAfter=4)

    def bloco(tipo, cabecalho, texto, detalhes=()):
        partes = [Paragraph(_texto_pdf(tipo).upper(), rotulo)]
        if cabecalho:
            partes.append(Paragraph(_texto_pdf(cabecalho), subtitulo))
        partes.append(Paragraph(_texto_pdf(texto), corpo))
        linha = " · ".join(f"{nome}: {valor}" for nome, valor in detalhes if valor)
        if linha:
            partes.append(Paragraph(_texto_pdf(linha), meta))
        return partes

    historia = [
        Paragraph("Sender AI · Conteúdos aprovados", titulo),
        Spacer(1, 3 * mm),
        Paragraph(_texto_pdf(
            f"Comunidade: {pacote.get('origem_comunidade') or '-'}   |   "
            f"Período: {pacote.get('periodo_referencia') or '-'}   |   "
            f"Aprovado em: {str(pacote.get('aprovado_em') or '-')[:16].replace('T', ' ')}   |   "
            f"{total_de_ativos(pacote)} conteúdo(s)"
        ), meta),
        Spacer(1, 3 * mm),
        HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#D5D9E0")),
    ]

    post = pacote.get("post_linkedin")
    if post:
        historia += bloco("Post para o LinkedIn", post.get("titulo"), post.get("copy"), [
            ("Membro", post.get("membro")),
            ("Autorização do membro", "sim" if post.get("autorizacao_membro") else "não"),
            ("Potencial de engajamento", post.get("potencial_engajamento")),
        ])
    news = pacote.get("destaque_newsletter_semanal")
    if news:
        historia += bloco("Destaque da newsletter", news.get("chamada"), news.get("resumo"), [("Seção", news.get("secao"))])
    for numero, faq in enumerate(pacote.get("sugestao_conteudo_faq") or [], 1):
        historia += bloco(f"FAQ {numero}", faq.get("tema"), faq.get("conteudo"), [("Origem", faq.get("origem"))])

    if total_de_ativos(pacote) == 0:
        historia.append(Paragraph("Nenhum conteúdo aprovado neste lote.", corpo))

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(cinza)
        canvas.drawString(20 * mm, 12 * mm, "Gerado pelo Sender AI. Revise antes de publicar.")
        canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Página {doc.page}")
        canvas.restoreState()

    saida = io.BytesIO()
    documento = SimpleDocTemplate(
        saida, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
        title="Sender AI - Conteúdos aprovados", author="Sender AI",
    )
    documento.build(historia, onFirstPage=rodape, onLaterPages=rodape)
    return saida.getvalue()
