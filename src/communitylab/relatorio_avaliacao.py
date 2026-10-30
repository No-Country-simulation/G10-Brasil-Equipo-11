"""Relatório de avaliação portátil, com evidências e sem serviços externos."""

from html import escape
import json
from typing import Any


_ROTULOS = {
    "tipo": "Tipo de interação",
    "sentimento": "Sentimento",
    "rota": "Rota de negócio",
    "depoimento": "Depoimento",
    "pergunta_tecnica": "Pergunta técnica",
    "feedback": "Feedback",
    "reclamacao": "Reclamação",
    "projeto": "Projeto",
    "outro": "Outro",
    "case_sucesso": "Case de sucesso",
    "faq": "FAQ",
    "alerta": "Alerta",
    "nenhuma": "Nenhuma",
    "mock": "Mock · simulação por regras",
    "gemini": "Gemini · execução via provedor",
    "arquivo": "Arquivo · previsões importadas",
    "avaliacao_local": "Classificador fornecido",
    "tipo_oculto": "Tipo oculto · sem rótulo de entrada",
    "tipo_informado": "Tipo informado · avaliação assistida",
    "proposta_pendente_revisao_humana": "Proposta · revisão humana pendente",
    "revisada_individualmente": "Referências revisadas individualmente",
}

_ESTILOS = """
:root{color-scheme:light;--paper:#f5f5ef;--card:#fff;--ink:#182b37;
--muted:#526570;--line:#d8e1df;--teal:#006c65;--teal-soft:#e5f2ed;
--blue:#536f95;--red:#9d3934;--red-soft:#fbece8;--amber:#82560a;
--amber-soft:#faf0d7;--radius:14px}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:1.5rem}
body{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,
-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:15px;line-height:1.6}
a{color:var(--teal);text-underline-offset:3px}a:hover{text-decoration-thickness:2px}
:focus-visible{outline:3px solid var(--teal);outline-offset:4px}
.skip{position:absolute;left:1rem;top:-10rem;background:white;padding:1rem;z-index:2}
.skip:focus{top:1rem}.shell{max-width:1240px;margin:auto;padding:42px 32px 30px}
.brand{display:flex;justify-content:space-between;gap:1rem;align-items:center;
padding-bottom:23px;border-bottom:1px solid var(--line)}
.wordmark{font-weight:780;font-size:24px;letter-spacing:-1px}.wordmark span{color:var(--teal)}
.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:11px;font-weight:750}
.muted,.helper{color:var(--muted)}.helper{font-size:13px;margin:.4rem 0 1rem}
.hero{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:48px;padding:38px 0 25px;align-items:start}
.hero>*,.grid-two>*,.grid-three>*,.section-head>*{min-width:0}
h1{font-size:clamp(30px,4vw,46px);line-height:1.12;letter-spacing:-1.7px;
margin:13px 0 18px;max-width:660px}h2{font-size:25px;line-height:1.25;letter-spacing:-.6px;
margin:0 0 9px}h3{font-size:18px;line-height:1.35;margin:0 0 12px}
h4{font-size:14px;margin:22px 0 9px}p{margin:0 0 14px}.lead{color:var(--muted);max-width:650px}
.snapshot{background:var(--ink);color:white;padding:24px;border-radius:var(--radius)}
.snapshot dl{margin:15px 0 0}.snapshot .meta-row{border-color:#405460}
.snapshot .meta-row dt{color:#c7d5da}.snapshot dd{font-weight:650}
.badge{display:inline-flex;align-items:center;border:1px solid transparent;border-radius:5px;
padding:4px 9px;font-size:11px;font-weight:750;line-height:1.4;letter-spacing:.025em}
.badge-neutral{background:#edf0f0;color:#425863}.badge-good{background:var(--teal-soft);color:#005d52}
.badge-warning{background:var(--amber-soft);color:var(--amber)}
.badge-critical{background:var(--red-soft);color:var(--red)}
.notice{border-left:4px solid var(--teal);background:var(--teal-soft);padding:17px 20px;
border-radius:0 9px 9px 0;font-size:14px}.notice p:last-child{margin-bottom:0}
nav{display:flex;flex-wrap:wrap;gap:10px 24px;padding:22px 0;border-bottom:1px solid var(--line)}
nav a{font-size:13px;font-weight:650;text-decoration:none}
main>section{margin-top:38px}.section-head{display:flex;justify-content:space-between;
align-items:start;gap:1rem;margin-bottom:20px}.section-number{font-size:12px;color:var(--teal);
font-weight:750;letter-spacing:.08em;margin-bottom:8px}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.card,.panel{min-width:0;background:var(--card);border:1px solid var(--line);border-radius:var(--radius)}
.card{padding:23px 21px;position:relative;overflow:hidden}.card:before{content:"";
position:absolute;left:0;top:0;width:100%;height:3px;background:var(--teal)}
.card.warning:before{background:var(--red)}.card-label{font-size:12px;font-weight:700;color:var(--muted)}
.card-value{font-size:34px;line-height:1.2;font-weight:760;letter-spacing:-1px;margin:10px 0}
.card-foot{font-size:12px;color:var(--muted)}.panel{padding:24px}.grid-two{display:grid;
grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.grid-three{display:grid;
grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.space-top{margin-top:18px}
.table-wrap{min-width:0;max-width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:9px}
table{border-collapse:collapse;width:100%;font-size:13px;background:white}
caption{caption-side:top;text-align:left;font-size:13px;font-weight:700;padding:13px 14px;
background:#f8faf8;border-bottom:1px solid var(--line)}
th,td{text-align:left;padding:11px 13px;border-bottom:1px solid var(--line);vertical-align:top}
thead th{font-size:11px;letter-spacing:.025em;color:#435a65;background:#f4f7f5}
tbody th{font-weight:600}tbody tr:last-child>*{border-bottom:0}
td.number,th.number{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.matrix td{text-align:center;vertical-align:middle;font-variant-numeric:tabular-nums}
.matrix th{min-width:85px;vertical-align:middle;max-width:170px}
.matrix .diagonal{background:var(--teal-soft);font-weight:750;color:#005d52}
.matrix .off-diagonal{background:var(--red-soft);font-weight:650;color:var(--red)}
.matrix .zero{color:#60727c}.matrix .failure{border-left:2px solid var(--line)}
.metric-summary{display:flex;gap:20px;flex-wrap:wrap;margin:18px 0 22px}
.metric-summary div{flex:1;min-width:130px}.metric-summary dt{font-size:12px;color:var(--muted)}
.metric-summary dd{font-size:25px;font-weight:720;margin:3px 0 0;font-variant-numeric:tabular-nums}
.legend{display:flex;flex-wrap:wrap;gap:10px 22px;font-size:12px;color:var(--muted);margin:12px 0}
.legend span:before{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;
background:var(--teal);margin-right:7px}.legend .predicted:before{background:var(--blue)}
.bar-group{margin-top:19px}.bar-label{font-size:13px;font-weight:650;margin-bottom:6px;
overflow-wrap:anywhere}.bar-line{display:grid;grid-template-columns:70px minmax(50px,1fr) 95px;
gap:9px;align-items:center;margin:5px 0}.bar-kind,.bar-value{font-size:11px;color:var(--muted)}
.bar-value{text-align:right;font-variant-numeric:tabular-nums}.bar-track{height:9px;
background:#eef2f0;overflow:hidden;border-radius:3px}.bar-fill{height:100%;
width:var(--bar-width);background:var(--teal);border-radius:3px}.bar-fill.predicted{background:var(--blue)}
.compact-list{margin:0;padding-left:19px}.compact-list li{padding:4px 0}
.review-link{font-weight:750;white-space:nowrap}.reason{min-width:230px}
.case{background:white;border:1px solid var(--line);border-radius:10px;margin-top:10px;
overflow:hidden}.case summary{cursor:pointer;padding:17px 20px;font-size:14px}
.case summary:hover{background:#f6f9f6}.case-title{font-weight:750;margin-right:10px}
.case-tags{display:inline-flex;flex-wrap:wrap;gap:6px;vertical-align:middle;margin:4px 0}
.case-body{border-top:1px solid var(--line);padding:21px}.case-meta{display:flex;flex-wrap:wrap;
gap:8px 22px;color:var(--muted);font-size:12px;margin-bottom:15px}
blockquote{margin:0 0 18px;padding:16px 18px;background:#f4f7f5;border-left:3px solid #a5c4b9;
border-radius:0 6px 6px 0;white-space:pre-wrap;overflow-wrap:anywhere}
.evidence{margin-top:18px}.evidence p{font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere}
.evidence strong{display:block;font-size:12px;margin-bottom:4px;color:var(--muted)}
.error{padding:12px 15px;background:var(--red-soft);color:var(--red);border-radius:6px;
white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}
.tag{font-size:11px;background:#f0f4f2;padding:3px 7px;border-radius:4px;color:var(--muted)}
.meta-row{display:grid;grid-template-columns:minmax(100px,.8fr) minmax(0,1.4fr);gap:14px;
border-bottom:1px solid var(--line);padding:9px 0;font-size:13px}
.meta-row>*{min-width:0;overflow-wrap:anywhere}
.meta-row:last-child{border:0}.meta-row dt{color:var(--muted)}.meta-row dd{margin:0;
overflow-wrap:anywhere}.trace{margin:0}.trace code{font-size:12px;word-break:break-all}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.6;background:#f4f7f5;
padding:16px;border-radius:8px;max-width:100%;overflow:auto}
.disclosure summary{font-size:13px;font-weight:700;cursor:pointer;padding:12px 0}
.empty{color:var(--muted);font-size:13px;padding:15px 0}
.slice-heading{font-size:14px;margin:16px 0 8px;overflow-wrap:anywhere}
.slice-data dl{margin:0}.slice-data .meta-row{grid-template-columns:repeat(2,minmax(0,1fr))}
footer{display:flex;justify-content:space-between;gap:20px;border-top:1px solid var(--line);
margin-top:40px;padding-top:20px;color:var(--muted);font-size:12px}
@media(max-width:900px){.hero{grid-template-columns:minmax(0,1fr);gap:20px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}
.grid-two,.grid-three{grid-template-columns:minmax(0,1fr)}.hero h1{max-width:700px}}
@media(max-width:540px){.shell{padding:24px 16px}.brand{align-items:start;flex-direction:column;gap:4px}
.hero{padding-top:25px}.cards{gap:10px}.card{padding:16px 13px}.card-value{font-size:28px}
.panel{padding:17px}.section-head{display:block}.case summary{padding:14px}.case-body{padding:15px}
.bar-line{grid-template-columns:58px minmax(35px,1fr) 88px;gap:5px}
.meta-row,.slice-data .meta-row{grid-template-columns:minmax(0,1fr)}
footer{display:block}nav{gap:10px 17px}h1{letter-spacing:-1px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{@page{size:A4;margin:14mm}html{scroll-behavior:auto}body{background:white;font-size:10pt}
.shell{max-width:none;margin:0;padding:0}nav,.skip{display:none}.brand{padding-bottom:10px}
.hero{padding:18px 0;gap:20px;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr)}h1{font-size:27pt;letter-spacing:-1px}
h2{font-size:17pt}h3{font-size:13pt}.lead,.notice{font-size:10pt}.snapshot{padding:15px;
background:white;color:var(--ink);border:1px solid var(--line)}.snapshot .meta-row dt{color:var(--muted)}
.snapshot .meta-row{border-color:var(--line)}.cards{grid-template-columns:repeat(4,minmax(0,1fr))}
.card{padding:14px}.card-value{font-size:22pt}.panel{padding:15px}.grid-two{grid-template-columns:minmax(0,1fr)}
main>section{margin-top:24px}.section-head{break-after:avoid}.table-wrap{overflow:visible}
table{font-size:8pt}th,td{padding:7px}thead{display:table-header-group}tr{break-inside:avoid}
.matrix{table-layout:fixed}.matrix th{min-width:0;max-width:none;overflow-wrap:anywhere}
.case{break-inside:avoid}.case summary{padding:11px}.case-body{padding:13px}
details::details-content{content-visibility:visible!important;display:block!important}
details:not([open])>*:not(summary){display:block!important}.bar-fill,.badge,.matrix td{
print-color-adjust:exact;-webkit-print-color-adjust:exact}.notice,.card{break-inside:avoid}
.metric-summary{margin:12px 0}.metric-summary dd{font-size:19pt}a{text-decoration:none;color:inherit}
footer{font-size:8pt}.grid-three{grid-template-columns:repeat(3,minmax(0,1fr))}}
"""


def _texto(valor: Any) -> str:
    """Único ponto de inserção de conteúdo externo em texto ou atributos HTML."""
    return escape("não definido" if valor is None else str(valor), quote=True)


def _rotulo(valor: Any) -> str:
    return _texto(_ROTULOS.get(str(valor), valor))


def _numero(valor: Any, casas: int = 2) -> str:
    if valor is None:
        return _texto(None)
    formatado = f"{valor:,.{casas}f}".rstrip("0").rstrip(".") if casas else f"{valor:,d}"
    return _texto(formatado.replace(",", "_").replace(".", ",").replace("_", "."))


def _percentual(valor: float | None) -> str:
    return _texto(None) if valor is None else _numero(valor * 100, 1) + "%"


def _badge(texto: Any, estilo: str = "neutral") -> str:
    # Classes vêm apenas de constantes internas, nunca do resultado avaliado.
    return f'<span class="badge badge-{_texto(estilo)}">{_texto(texto)}</span>'


def _cabecalho(numero: str, titulo: str, descricao: str) -> str:
    return (
        '<div class="section-head"><div>'
        f'<div class="section-number">{_texto(numero)}</div>'
        f'<h2>{_texto(titulo)}</h2><p class="helper">{_texto(descricao)}</p>'
        '</div></div>'
    )


def _card(titulo: str, valor_html: str, descricao: str, alerta: bool = False) -> str:
    classe = "card warning" if alerta else "card"
    return (
        f'<article class="{classe}"><div class="card-label">{_texto(titulo)}</div>'
        f'<div class="card-value">{valor_html}</div>'
        f'<div class="card-foot">{_texto(descricao)}</div></article>'
    )


def _matriz(metrica: dict, titulo: str) -> str:
    rotulos = metrica["rotulos"]
    colunas = "".join(f'<th scope="col">{_rotulo(r)}</th>' for r in rotulos)
    linhas = []
    for indice, (rotulo, valores) in enumerate(zip(rotulos, metrica["matriz_confusao"])):
        celulas = []
        for coluna, quantidade in enumerate(valores):
            classe = "diagonal" if indice == coluna else "off-diagonal" if quantidade else "zero"
            if coluna == len(rotulos):
                classe += " failure"
            celulas.append(f'<td class="{classe}">{_numero(quantidade, 0)}</td>')
        linhas.append(f'<tr><th scope="row">{_rotulo(rotulo)}</th>{"".join(celulas)}</tr>')
    return (
        '<div class="table-wrap" role="region" tabindex="0" '
        f'aria-label="Matriz de confusão: {_texto(titulo)}"><table class="matrix">'
        f'<caption>Matriz de confusão · {_texto(titulo)}</caption><thead><tr>'
        '<th scope="col">Referência ↓ / Previsão →</th>'
        f'{colunas}<th scope="col" class="failure">Falha</th></tr></thead>'
        f'<tbody>{"".join(linhas)}</tbody></table></div>'
        '<p class="helper">Diagonal: acertos. Demais células: divergências. '
        'A última coluna registra casos sem previsão válida.</p>'
    )


def _metricas(metrica: dict, chave: str) -> str:
    titulo = _ROTULOS[chave]
    linhas = []
    for classe in metrica["por_classe"]:
        valores = [
            _numero(classe["suporte"], 0),
            _numero(classe["preditos"], 0),
            _numero(classe["verdadeiros_positivos"], 0),
            _percentual(classe["precisao"]),
            _percentual(classe["recall"]),
            _percentual(classe["f1"]),
        ]
        linhas.append(
            f'<tr><th scope="row">{_rotulo(classe["rotulo"])}</th>'
            + "".join(f'<td class="number">{valor}</td>' for valor in valores)
            + '</tr>'
        )
    return (
        '<article class="panel space-top">'
        f'<h3>{_texto(titulo)}</h3><dl class="metric-summary">'
        f'<div><dt>Acurácia</dt><dd>{_percentual(metrica["acuracia"])}</dd></div>'
        f'<div><dt>F1 macro</dt><dd>{_percentual(metrica["macro_f1"])}</dd></div>'
        f'<div><dt>F1 ponderado</dt><dd>{_percentual(metrica["ponderado_f1"])}</dd></div>'
        f'<div><dt>Previsões válidas / total</dt><dd>{_numero(metrica["validos"], 0)}'
        f' / {_numero(metrica["total"], 0)}</dd></div></dl>'
        '<div class="table-wrap" role="region" tabindex="0" '
        f'aria-label="Métricas por classe: {_texto(titulo)}"><table>'
        '<caption>Desempenho por classe</caption><thead><tr><th scope="col">Classe</th>'
        '<th scope="col" class="number">Suporte</th><th scope="col" class="number">Previstos</th>'
        '<th scope="col" class="number">Acertos</th><th scope="col" class="number">Precisão</th>'
        '<th scope="col" class="number">Recall</th><th scope="col" class="number">F1</th>'
        f'</tr></thead><tbody>{"".join(linhas)}</tbody></table></div>'
        '<p class="helper">Suporte = casos da referência. Precisão = acertos entre previsões '
        'da classe. Recall = acertos entre casos de referência da classe. '
        'F1 combina precisão e recall. “não definido” indica denominador ausente.</p>'
        + _matriz(metrica, titulo)
        + '</article>'
    )


def _barra(quantidade: int, total: int, tipo: str, prevista: bool = False) -> str:
    proporcao = quantidade / total if total else None
    largura = max(0.0, min(100.0, (proporcao or 0) * 100))
    classe = "bar-fill predicted" if prevista else "bar-fill"
    return (
        f'<div class="bar-line"><span class="bar-kind">{_texto(tipo)}</span>'
        '<div class="bar-track" aria-hidden="true">'
        f'<div class="{classe}" style="--bar-width:{_texto(f"{largura:.3f}")}%"></div></div>'
        f'<span class="bar-value">{_numero(quantidade, 0)} · {_percentual(proporcao)}</span></div>'
    )


def _distribuicao(titulo: str, previstos: dict, referencia: dict | None = None) -> str:
    referencia = referencia if referencia is not None else {}
    rotulos = list(dict.fromkeys([*referencia, *previstos]))
    grupos = []
    for rotulo in rotulos:
        barras = ''
        if referencia:
            barras += _barra(referencia.get(rotulo, 0), sum(referencia.values()), "Referência")
        barras += _barra(previstos.get(rotulo, 0), sum(previstos.values()), "Previsão", True)
        grupos.append(f'<div class="bar-group"><div class="bar-label">{_rotulo(rotulo)}</div>{barras}</div>')
    conteudo = "".join(grupos) or '<p class="empty">Sem registros para esta distribuição.</p>'
    return (
        f'<article class="panel"><h3>{_texto(titulo)}</h3>{conteudo}'
        '<p class="helper space-top">Percentuais calculados sobre o total de cada série. '
        'Falhas de execução não entram na série de previsões.</p></article>'
    )


def _prioridade(caso: dict) -> str:
    prioridade = caso["prioridade"]
    rotulo, estilo = {
        "alta": ("Alta", "critical"),
        "media": ("Média", "warning"),
        "baixa": ("Baixa", "neutral"),
    }.get(prioridade, (prioridade, "neutral"))
    return _badge(rotulo, estilo)


def _fila_revisao(casos: list[dict]) -> str:
    linhas = []
    for indice, caso in enumerate(casos, start=1):
        previsto = caso["previsto"] or {}
        motivo = caso["motivo_revisao"] or (
            "Falha de execução" if caso["erro"] else "; ".join(caso["divergencias"])
        ) or "Revisão da anotação de referência"
        linhas.append(
            f'<tr><th scope="row"><a class="review-link" href="#caso-{_texto(indice)}">'
            f'{_texto(caso["id"])}</a></th><td>{_prioridade(caso)}</td>'
            f'<td>{_rotulo(caso["referencia"]["rota"])}</td><td>{_rotulo(previsto.get("rota"))}</td>'
            f'<td class="reason">{_texto(motivo)}</td></tr>'
        )
    if not linhas:
        return '<div class="panel"><p class="empty">Nenhum caso sinalizado para revisão nesta execução.</p></div>'
    return (
        '<div class="table-wrap" role="region" tabindex="0" aria-label="Fila priorizada de revisão">'
        '<table><caption>Casos sinalizados para revisão · ordem de prioridade do avaliador</caption>'
        '<thead><tr><th scope="col">Caso</th><th scope="col">Prioridade</th>'
        '<th scope="col">Rota de referência</th><th scope="col">Rota prevista</th>'
        '<th scope="col">Motivo da revisão</th></tr></thead>'
        f'<tbody>{"".join(linhas)}</tbody></table></div>'
    )


def _caso(caso: dict, indice: int) -> str:
    entrada, referencia = caso["entrada"], caso["referencia"]
    previsto = caso["previsto"] or {}
    if caso["erro"]:
        estado = _badge("Falha de execução", "critical")
    elif caso["divergencias"]:
        estado = _badge("Divergência com a referência", "warning")
    else:
        estado = _badge("Concordância com a referência", "good")
    linhas = []
    for campo in ("tipo", "sentimento", "rota"):
        linhas.append(
            f'<tr><th scope="row">{_texto(_ROTULOS[campo])}</th>'
            f'<td>{_rotulo(referencia[campo])}</td><td>{_rotulo(previsto.get(campo))}</td></tr>'
        )
    linhas.append(
        '<tr><th scope="row">Relevância (0–10)</th>'
        f'<td>{_numero(referencia["relevancia_min"])} a {_numero(referencia["relevancia_max"])}</td>'
        f'<td>{_numero(previsto.get("relevancia"))}</td></tr>'
    )
    evidencias = (
        '<div class="evidence"><strong>Justificativa da referência</strong>'
        f'<p>{_texto(caso["justificativa"])}</p><strong>Evidência da anotação</strong>'
        f'<p>{_texto(caso["evidencia"])}</p></div>'
    )
    if caso["divergencias"]:
        evidencias += '<h4>Divergências identificadas</h4><ul class="compact-list">' + "".join(
            f'<li>{_texto(item)}</li>' for item in caso["divergencias"]
        ) + '</ul>'
    if caso["motivo_revisao"]:
        evidencias += f'<div class="evidence"><strong>Motivo da revisão</strong><p>{_texto(caso["motivo_revisao"])}</p></div>'
    if caso["erro"]:
        evidencias += f'<div class="error"><strong>Erro registrado:</strong> {_texto(caso["erro"])}</div>'
    marcadores = " ".join(f'<span class="tag">{_texto(marcador)}</span>' for marcador in caso["marcadores"])
    adicional = (
        '<details class="disclosure"><summary>Previsão completa registrada</summary>'
        f'<pre>{_texto(json.dumps(caso["previsto"], ensure_ascii=False, indent=2, default=str))}</pre></details>'
        if caso["previsto"] is not None else ''
    )
    return (
        f'<details class="case" id="caso-{_texto(indice)}"><summary>'
        f'<span class="case-title">{_texto(caso["id"])}</span>'
        f'<span class="case-tags">{_prioridade(caso)} {estado}</span>'
        f' <span class="muted">{_texto(caso["grupo"])}</span></summary><div class="case-body">'
        f'<div class="case-meta"><span>Autor: {_texto(entrada["autor"])}</span>'
        f'<span>Canal: {_texto(entrada["canal"])}</span><span>Tipo enviado: {_rotulo(entrada["tipo"])}</span>'
        f'<span>Sinalizado para revisão na base: {_texto("sim" if caso["revisao_humana"] else "não")}</span>'
        f'<span>Anotação: {_rotulo(caso.get("status_anotacao", "proposta_pendente_revisao_humana"))}</span></div>'
        f'<blockquote>{_texto(entrada["texto"])}</blockquote>'
        '<div class="table-wrap" role="region" tabindex="0" aria-label="Comparação do caso">'
        '<table><thead><tr><th scope="col">Dimensão</th><th scope="col">Referência esperada</th>'
        f'<th scope="col">Previsão registrada</th></tr></thead><tbody>{"".join(linhas)}</tbody></table></div>'
        f'{evidencias}<div class="case-tags">{marcadores}</div>{adicional}</div></details>'
    )


def _criterios(criterios: list[dict]) -> str:
    linhas = []
    for criterio in criterios:
        atendido = criterio["atendido"]
        estado = (
            _badge("Atingido nesta execução", "good") if atendido is True
            else _badge("Não atingido", "warning") if atendido is False
            else _badge("não definido")
        )
        linhas.append(
            f'<tr><th scope="row">{_texto(criterio["descricao"])}'
            f'<div class="helper">{_texto(criterio["id"])}</div></th>'
            f'<td class="number">{_percentual(criterio["valor"])}</td>'
            f'<td class="number">≥ {_percentual(criterio["limiar"])}</td><td>{estado}</td></tr>'
        )
    return (
        '<div class="table-wrap" role="region" tabindex="0" aria-label="Metas da avaliação">'
        '<table><caption>Critérios de acompanhamento da avaliação</caption><thead><tr>'
        '<th scope="col">Critério</th><th scope="col" class="number">Valor observado</th>'
        '<th scope="col" class="number">Limiar da avaliação</th><th scope="col">Situação</th>'
        f'</tr></thead><tbody>{"".join(linhas)}</tbody></table></div>'
        '<p class="helper">Todos os critérios usam limites mínimos de acompanhamento. '
        'Atingir um limiar nesta base sintética não constitui aprovação para produção.</p>'
    )


def _valor_rastreavel(valor: Any) -> str:
    if isinstance(valor, (dict, list)):
        return f'<pre>{_texto(json.dumps(valor, ensure_ascii=False, indent=2, default=str))}</pre>'
    if isinstance(valor, bool):
        return _texto("sim" if valor else "não")
    return _texto(valor)


def _recortes(recortes: dict) -> str:
    if not recortes:
        return '<p class="empty">Nenhum recorte disponível nesta execução.</p>'
    paineis = []
    for nome, valores in recortes.items():
        if isinstance(valores, dict) and {"cobertura", "metricas", "relevancia"} <= valores.keys():
            cobertura = valores["cobertura"]
            linhas = []
            for dimensao, metrica in valores["metricas"].items():
                com_suporte = sum(classe["suporte"] > 0 for classe in metrica["por_classe"])
                linhas.append(
                    f'<tr><th scope="row">{_rotulo(dimensao)}</th>'
                    f'<td class="number">{_percentual(metrica["acuracia"])}</td>'
                    f'<td class="number">{_percentual(metrica["macro_f1"])}</td>'
                    f'<td class="number">{_numero(com_suporte, 0)} / {_numero(len(metrica["por_classe"]), 0)}</td></tr>'
                )
            alerta = next(
                (classe["recall"] for classe in valores["metricas"].get("rota", {}).get("por_classe", [])
                 if classe["rotulo"] == "alerta"), None
            )
            conteudo = (
                '<dl class="metric-summary">'
                f'<div><dt>Casos</dt><dd>{_numero(cobertura["total"], 0)}</dd></div>'
                f'<div><dt>Cobertura</dt><dd>{_percentual(cobertura["taxa"])}</dd></div>'
                f'<div><dt>Falhas</dt><dd>{_numero(cobertura["falhas"], 0)}</dd></div></dl>'
                '<div class="table-wrap" role="region" tabindex="0" aria-label="Desempenho do recorte">'
                '<table><thead><tr><th scope="col">Dimensão</th><th scope="col" class="number">Acurácia</th>'
                '<th scope="col" class="number">F1 macro</th>'
                '<th scope="col" class="number">Classes com suporte</th></tr></thead>'
                f'<tbody>{"".join(linhas)}</tbody></table></div><dl class="metric-summary">'
                f'<div><dt>Recall de alerta</dt><dd>{_percentual(alerta)}</dd></div>'
                '<div><dt>Relevância dentro da faixa</dt>'
                f'<dd>{_percentual(valores["relevancia"]["proporcao_dentro_faixa"])}</dd></div></dl>'
                '<p class="helper">Classes sem suporte não entram no F1 macro. '
                'Um recorte pequeno ou sem alguma classe não demonstra qualidade nessa classe.</p>'
            )
        elif isinstance(valores, dict):
            linhas = []
            for chave, valor in valores.items():
                if isinstance(valor, dict) and all(not isinstance(v, (dict, list)) for v in valor.values()):
                    conteudo = '<dl>' + ''.join(
                        f'<div class="meta-row"><dt>{_texto(k)}</dt><dd>{_valor_rastreavel(v)}</dd></div>'
                        for k, v in valor.items()
                    ) + '</dl>'
                else:
                    conteudo = _valor_rastreavel(valor)
                linhas.append(f'<h4 class="slice-heading">{_texto(chave)}</h4>{conteudo}')
            conteudo = ''.join(linhas)
        else:
            conteudo = _valor_rastreavel(valores)
        titulo = {"referencia": "Referência · base principal", "desafio": "Desafio · casos de estresse"}.get(nome, nome)
        paineis.append(f'<article class="panel slice-data"><h3>{_texto(titulo)}</h3>{conteudo}</article>')
    return '<div class="grid-two">' + ''.join(paineis) + '</div>'


def renderizar_html(resultado: dict) -> str:
    """Renderiza um resultado de avaliação sem rede, scripts ou efeitos colaterais.

    O relatório conserva os indicadores calculados pelo avaliador, inclusive
    valores indefinidos. O estado da revisão vem dos metadados da base;
    revisão individual e métricas sintéticas não comprovam qualidade em produção.
    """
    metadados = resultado["metadados"]
    cobertura = resultado["cobertura"]
    indicadores = resultado["indicadores"]
    relevancia = resultado["relevancia"]
    casos = resultado["casos"]
    metricas = resultado["metricas"]
    revisao = metadados.get("revisao_anotacao")
    contexto_revisao = (
        f'Referências e critérios conferidos individualmente por {revisao["revisor"]} '
        f'em {revisao["data"]}, com concordância sem alterações em '
        f'{len(revisao["casos_revisados"])} casos. Método: conferência de propostas. '
        'Não houve dupla anotação independente; a revisão não aprova as previsões do classificador.'
        if revisao else 'As referências e as metas aguardam revisão humana documentada.'
    )
    registro_revisor = (
        f'<div class="meta-row"><dt>Revisor</dt><dd>{_texto(revisao["revisor"])} · {_texto(revisao["data"])}</dd></div>'
        if revisao else ''
    )
    total_referencia = resultado["recortes"].get("referencia", {}).get("cobertura", {}).get("total")
    contexto_modo = {
        "mock": "Modo mock: o classificador usa regras locais. Estes resultados não medem a qualidade do Gemini.",
        "arquivo": "Previsões importadas: a identificação do modelo é declarada no arquivo de origem e não é verificada por este relatório.",
    }.get(metadados["modo"], "")
    if metadados["cenario"] == "tipo_informado":
        contexto_modo += " Neste cenário assistido, o tipo de referência é fornecido na entrada e reutilizado pelo mock."
    cards = ''.join([
        _card("Casos da base", _numero(cobertura["total"], 0), "Mensagens sintéticas com referência de avaliação"),
        _card("Cobertura de execução", _percentual(cobertura["taxa"]),
              f'{cobertura["validos"]} previsões válidas · {cobertura["falhas"]} falhas'),
        _card("F1 macro · rotas", _percentual(metricas["rota"]["macro_f1"]),
              "Média por classe com suporte na referência"),
        _card("Alertas não detectados", _numero(indicadores["alertas_nao_detectados"], 0),
              "Referência alerta sem rota alerta na previsão", bool(indicadores["alertas_nao_detectados"])),
    ])
    rotas_referencia = {classe["rotulo"]: classe["suporte"] for classe in metricas["rota"]["por_classe"]}
    sentimentos_referencia = {classe["rotulo"]: classe["suporte"] for classe in metricas["sentimento"]["por_classe"]}
    distribuicoes = (
        _distribuicao("Tipos de interação", indicadores["tipos_previstos"], indicadores["tipos_referencia"])
        + _distribuicao("Rotas de negócio", indicadores["rotas_previstas"], rotas_referencia)
        + _distribuicao("Sentimentos", indicadores["sentimentos_previstos"], sentimentos_referencia)
        + '<article class="panel"><h3>Tópicos previstos</h3><p class="helper">Agrupamento literal '
        'dos tópicos retornados. Não representa validação semântica ou tendência da comunidade.</p>'
        + ('<ul class="compact-list">' + ''.join(
            f'<li>{_texto(item["topico"])} <span class="muted">· {_numero(item["quantidade"], 0)} registros</span></li>'
            for item in indicadores["topicos"]
        ) + '</ul>' if indicadores["topicos"] else '<p class="empty">Nenhum tópico previsto.</p>')
        + '</article>'
    )
    limitacoes = ''.join(f'<li>{_texto(item)}</li>' for item in resultado["limitacoes"])
    rastreabilidade = ''.join(
        f'<div class="meta-row"><dt>{_texto(chave)}</dt><dd>{_valor_rastreavel(valor)}</dd></div>'
        for chave, valor in metadados.items()
    )
    html = [
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<meta name="color-scheme" content="light">',
        '<title>CommunityLab · Avaliação sintética do pipeline</title>',
        f'<style>{_ESTILOS}</style></head><body>',
        '<a class="skip" href="#conteudo">Ir para o conteúdo</a><div class="shell">',
        '<header><div class="brand"><div class="wordmark">Community<span>Lab</span></div>',
        '<div class="eyebrow muted">Observatório de qualidade</div></div>',
        '<div class="hero"><div>',
        _badge("Avaliação sintética", "warning"),
        '<h1>Qualidade do pipeline,<br>caso a caso.</h1>',
        '<p class="lead">Classificação, relevância e roteamento comparados com uma base '
        'de referência. Resultados verificáveis para orientar a evolução do CommunityLab.</p></div>',
        '<aside class="snapshot" aria-label="Contexto da execução"><div class="eyebrow">Esta execução</div><dl>',
        f'<div class="meta-row"><dt>Modo</dt><dd>{_rotulo(metadados["modo"])}</dd></div>',
        f'<div class="meta-row"><dt>Cenário</dt><dd>{_rotulo(metadados["cenario"])}</dd></div>',
        f'<div class="meta-row"><dt>Versão da base</dt><dd>{_texto(metadados["versao_base"])}</dd></div>',
        f'<div class="meta-row"><dt>Anotação</dt><dd>{_rotulo(metadados["status_anotacao"])}</dd></div>',
        registro_revisor,
        '</dl></aside></div><div class="notice"><p><strong>Escopo da evidência.</strong> '
        'Esta avaliação usa mensagens sintéticas e referências de trabalho. '
        'As métricas descrevem apenas esta base, este modo e este cenário. '
        'Concordância com a referência não significa aprovação do conteúdo gerado, impacto comprovado '
        'ou desempenho esperado em comunidades reais.</p>',
        f'<p><strong>{_texto(contexto_modo)}</strong></p>' if contexto_modo else '',
        f'<p>{_texto(contexto_revisao)}</p>',
        '</div></header>',
        '<nav aria-label="Seções do relatório"><a href="#resumo">Resumo</a><a href="#metas">Metas da avaliação</a>',
        '<a href="#distribuicao">Distribuições</a><a href="#desempenho">Desempenho</a>',
        '<a href="#revisao">Fila de revisão</a><a href="#casos">Casos</a>',
        '<a href="#rastreabilidade">Rastreabilidade</a></nav><main id="conteudo">',
        '<section id="resumo" aria-labelledby="titulo-resumo"><h2 id="titulo-resumo">Visão da execução</h2>',
        f'<p class="helper">Resumo de toda a base: {_numero(cobertura["total"], 0)} casos, '
        'incluindo os recortes de referência e desafio.</p>',
        f'<div class="cards">{cards}</div></section><section id="metas">',
        _cabecalho("01 / CRITÉRIOS", "Metas da avaliação, evidência observada", "Limiares de trabalho para acompanhamento da qualidade; o estado de revisão consta no contexto da execução."),
        '<p class="helper"><strong>Escopo das metas:</strong> classificação, recall de alerta, '
        f'relevância e cobertura de classes usam o recorte referência ({_numero(total_referencia, 0)} casos). '
        f'Cobertura de execução e consistência de rota usam toda a base ({_numero(cobertura["total"], 0)} casos). '
        'O resumo e a seção Desempenho apresentam os resultados de toda a base.</p>',
        _criterios(resultado["criterios"]),
        '</section><section id="distribuicao">',
        _cabecalho("02 / PERFIL", "Como os casos se distribuem", "Compare o perfil da referência com as previsões válidas antes de interpretar métricas agregadas."),
        '<div class="legend"><span>Referência</span><span class="predicted">Previsão</span></div>',
        f'<div class="grid-two">{distribuicoes}</div></section><section id="desempenho">',
        _cabecalho("03 / DESEMPENHO", "Do resultado agregado à classe", "Resultado de toda a base, incluindo desafios. Falhas permanecem no denominador da avaliação. F1 macro considera as classes com suporte na referência."),
        ''.join(_metricas(metricas[chave], chave) for chave in ("tipo", "sentimento", "rota")),
        '<article class="panel space-top"><h3>Relevância · concordância com a faixa esperada</h3>',
        '<p class="helper">A referência define um intervalo aceitável de 0 a 10, em vez de exigir uma pontuação única.</p>',
        '<dl class="metric-summary">',
        f'<div><dt>Avaliados / total</dt><dd>{_numero(relevancia["avaliados"], 0)} / {_numero(relevancia["total"], 0)}</dd></div>',
        f'<div><dt>Casos dentro da faixa</dt><dd>{_numero(relevancia["dentro_faixa"], 0)}</dd></div>',
        f'<div><dt>Proporção dentro da faixa</dt><dd>{_percentual(relevancia["proporcao_dentro_faixa"])}</dd></div>',
        f'<div><dt>Distância média à faixa</dt><dd>{_numero(relevancia["distancia_media_faixa"])}</dd></div></dl>',
        '<p class="helper">A distância é zero dentro do intervalo e mede, fora dele, os pontos '
        'até o limite mais próximo. Uma distância menor indica maior concordância.</p></article>',
        '</section><section id="recortes">',
        _cabecalho("04 / DIAGNÓSTICO", "Recortes da avaliação", "Leitura segmentada para localizar dificuldades que a média geral pode ocultar."),
        _recortes(resultado["recortes"]),
        '</section><section id="revisao">',
        _cabecalho("05 / REVISÃO", "Uma fila de revisão com contexto", "Prioridade e motivo acompanham cada caso. Abra o identificador para consultar sua evidência."),
        f'<p><strong>{_numero(indicadores["casos_revisao"], 0)} casos sinalizados pelo avaliador.</strong> ',
        '<span class="muted">A fila permite analisar as previsões e os casos sensíveis, inclusive quando a referência já foi revisada.</span></p>',
        _fila_revisao(casos),
        '</section><section id="casos">',
        _cabecalho("06 / EVIDÊNCIAS", "Cada decisão pode ser examinada", "Expanda um caso para comparar entrada, referência, previsão, justificativa e marcadores de diagnóstico."),
        ''.join(_caso(caso, indice) for indice, caso in enumerate(casos, start=1))
        or '<p class="empty">Nenhum caso disponível nesta execução.</p>',
        '</section><section id="rastreabilidade">',
        _cabecalho("07 / CONTEXTO TÉCNICO", "Limitações e rastreabilidade", "Identificação da base e da execução para permitir conferência e reprodução dos resultados."),
        '<div class="panel"><h3>Limitações de interpretação</h3>',
        f'<ul class="compact-list">{limitacoes}</ul>' if limitacoes else '<p class="empty">Nenhuma limitação adicional registrada.</p>',
        f'<p class="helper space-top">{_texto(contexto_revisao)}</p>',
        '</div><div class="panel space-top"><h3>Identificação da execução</h3>',
        f'<dl class="trace">{rastreabilidade}</dl></div></section></main>',
        '<footer><span>CommunityLab · avaliação sintética do pipeline</span>',
        '<span>Relatório autossuficiente · leitura local e impressão</span></footer></div></body></html>',
    ]
    return ''.join(html)
