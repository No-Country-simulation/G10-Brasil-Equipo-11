"""Indicadores descritivos de lotes classificados, sem inferências sobre pessoas."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from html import escape

from app.schemas import Analise
from app.ia import decidir_rota
from communitylab.avaliacao import ROTAS, SENTIMENTOS, TIPOS


def _texto(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"Informe {campo} como texto não vazio.")
    return valor.strip()


def _distribuir(analises, campo, categorias):
    contagens = Counter(a[campo] for a in analises)
    return [{"categoria": c, "quantidade": contagens[c], "proporcao": contagens[c] / len(analises)} for c in categorias]


def resumir_lote(lote: dict) -> dict:
    """Recebe metadados explícitos e analises no contrato oficial do pipeline.

    A unidade é o registro/mensagem. Tópicos repetidos são igualdade textual
    após NFC, caixa e espaços; não são similaridade semântica de perguntas.
    """
    campos = {"origem_comunidade", "periodo_referencia", "natureza_dados", "modo_classificacao", "analises"}
    if not isinstance(lote, dict) or set(lote) != campos:
        raise ValueError("O lote analítico exige origem_comunidade, periodo_referencia, natureza_dados, modo_classificacao e analises.")
    comunidade = _texto(lote["origem_comunidade"], "origem_comunidade")
    periodo = _texto(lote["periodo_referencia"], "periodo_referencia")
    if lote["natureza_dados"] not in ("sintetica", "real", "nao_informada"):
        raise ValueError("natureza_dados deve ser sintetica, real ou nao_informada.")
    if lote["modo_classificacao"] not in ("mock", "gemini", "importado", "nao_informado"):
        raise ValueError("modo_classificacao inválido.")
    if not isinstance(lote["analises"], list) or not lote["analises"]:
        raise ValueError("O lote precisa conter pelo menos uma análise.")
    analises = []
    for i, item in enumerate(lote["analises"], 1):
        if not isinstance(item, dict) or set(item) != set(Analise.model_fields):
            raise ValueError(f"Análise {i}: campos incompatíveis com Analise.")
        analise = Analise.model_validate(item, strict=True).model_dump()
        for campo in ("autor", "canal", "texto", "topico"):
            _texto(analise[campo], f"{campo} na análise {i}")
        analises.append(analise)
    total = len(analises)
    perguntas = defaultdict(list)
    nomes = {}
    for i, a in enumerate(analises, 1):
        if a["tipo"] == "pergunta_tecnica":
            topico = " ".join(unicodedata.normalize("NFC", a["topico"]).casefold().split())
            perguntas[topico].append(i)
            nomes.setdefault(topico, a["topico"].strip())
    topicos = [{"topico": nomes[t], "quantidade": len(indices), "indices_origem": indices,
                "recorrente": len(indices) >= 2} for t, indices in sorted(perguntas.items(), key=lambda x: (-len(x[1]), x[0]))]
    identidades = [(a["autor"], a["canal"], a["texto"]) for a in analises]
    duplicadas = total - len(set(identidades))
    negativos = sum(a["sentimento"] in ("Negativo", "Altamente Negativo") for a in analises)
    alertas = sum(a["rota"] == "alerta" for a in analises)
    numero_perguntas = sum(a["tipo"] == "pergunta_tecnica" for a in analises)
    inconsistencias = sum(a["rota"] != decidir_rota(a["tipo"], a["sentimento"], a["relevancia"]) for a in analises)
    sugestoes = []
    if alertas:
        sugestoes.append(f"Revisar mensagens encaminhadas a alerta ({alertas}) e conferir o contexto antes de qualquer ação.")
    if any(t["recorrente"] for t in topicos):
        sugestoes.append("Examinar as perguntas dos tópicos repetidos e confirmar se tratam da mesma dúvida antes de propor uma FAQ.")
    if not numero_perguntas:
        sugestoes.append("Nenhuma pergunta técnica foi classificada neste lote; conferir possíveis erros do classificador antes de concluir ausência de dúvidas.")
    if duplicadas:
        sugestoes.append(f"Conferir {duplicadas} registros com autor, canal e texto repetidos; podem inflar a contagem de recorrência.")
    if inconsistencias:
        sugestoes.append(f"Conferir {inconsistencias} rotas incompatíveis com a regra do pipeline; as previsões originais foram preservadas nas contagens.")
    if any(a["rota"] == "case_sucesso" for a in analises):
        sugestoes.append("Conferir evidências e autorização dos relatos candidatos a conteúdo antes de reutilização externa.")
    if not sugestoes:
        sugestoes.append("Revisar uma amostra das classificações antes de interpretar a distribuição como retrato da comunidade.")
    return {
        "origem_comunidade": comunidade, "periodo_referencia": periodo,
        "natureza_dados": lote["natureza_dados"], "modo_classificacao": lote["modo_classificacao"],
        "total_interacoes": total,
        "distribuicoes": {c: _distribuir(analises, c, vocabulario) for c, vocabulario in (("tipo", TIPOS), ("sentimento", SENTIMENTOS), ("rota", ROTAS))},
        "indicadores": {
            "mensagens_negativas": negativos, "proporcao_mensagens_negativas": negativos / total,
            "mensagens_em_alerta": alertas, "proporcao_mensagens_em_alerta": alertas / total,
            "perguntas_tecnicas": numero_perguntas,
            "perguntas_em_alerta": sum(a["tipo"] == "pergunta_tecnica" and a["rota"] == "alerta" for a in analises),
            "topicos_com_perguntas_repetidas": sum(t["recorrente"] for t in topicos),
            "registros_possivelmente_duplicados": duplicadas,
            "inconsistencias_rota": inconsistencias,
        },
        "perguntas_por_topico": topicos,
        "recomendacoes_para_revisao": sugestoes,
        "limitacoes": [
            "Indicadores descrevem mensagens do lote, não pessoas únicas, satisfação, retenção ou saúde comprovada da comunidade.",
            "A classificação pode estar incorreta. As recomendações são propostas para revisão humana, sem ações automáticas.",
            "Tópicos iguais não garantem dúvidas iguais; tópicos diferentes podem descrever a mesma dúvida. Não há agrupamento semântico nesta versão.",
            "Sem datas individuais, exposição ou método de amostragem, não é possível calcular taxas diárias nem inferir tendência ou causalidade.",
            "O relatório omite autores e textos, mas tópicos livres ainda podem conter dados pessoais. Agregação não equivale a anonimização ou controle de acesso.",
            "Natureza dos dados, comunidade, período e modo são declarados na entrada. Este relatório não comprova execução de um provedor externo.",
        ],
    }


def comparar_lotes(atual: dict, anterior: dict) -> dict:
    """Compara proporções com denominadores próprios, sempre em pontos percentuais."""
    for campo in ("origem_comunidade", "natureza_dados", "modo_classificacao"):
        if atual[campo] != anterior[campo]:
            raise ValueError(f"Lotes não comparáveis: {campo} difere.")
    if atual["periodo_referencia"] == anterior["periodo_referencia"]:
        raise ValueError("Identifique períodos distintos para a comparação.")
    linhas = []
    for dimensao, distribuicao in atual["distribuicoes"].items():
        anteriores = {c["categoria"]: c for c in anterior["distribuicoes"][dimensao]}
        for corrente in distribuicao:
            passada = anteriores[corrente["categoria"]]
            linhas.append({"dimensao": dimensao, "categoria": corrente["categoria"],
                           "quantidade_anterior": passada["quantidade"], "quantidade_atual": corrente["quantidade"],
                           "proporcao_anterior": passada["proporcao"], "proporcao_atual": corrente["proporcao"],
                           "variacao_pontos_percentuais": 100 * (corrente["proporcao"] - passada["proporcao"])})
    return {
        "periodo_anterior": anterior["periodo_referencia"], "periodo_atual": atual["periodo_referencia"],
        "total_anterior": anterior["total_interacoes"], "total_atual": atual["total_interacoes"],
        "variacao_total": atual["total_interacoes"] - anterior["total_interacoes"],
        "categorias": linhas,
        "interpretacao": "Comparação descritiva de lotes declarados. Diferenças de coleta, duração e composição podem explicar a variação; não demonstram tendência ou impacto.",
    }


def construir_radar(atual: dict, anterior: dict | None = None) -> dict:
    resumo = resumir_lote(atual)
    passado = resumir_lote(anterior) if anterior is not None else None
    return {"atual": resumo, "anterior": passado,
            "comparacao": comparar_lotes(resumo, passado) if passado is not None else None,
            "rastreabilidade": {"lote_atual_sha256": hashlib.sha256(json.dumps(atual, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                                "lote_anterior_sha256": hashlib.sha256(json.dumps(anterior, ensure_ascii=False, sort_keys=True).encode()).hexdigest() if anterior is not None else None,
                                "metodo_hash": "SHA256 da serialização JSON canônica por chaves; índices de origem são posições 1-based no lote"}}


def renderizar_radar(resultado: dict) -> str:
    def e(valor):
        return escape(str(valor), quote=True)

    def rotulo(valor):
        nomes = {"tipo": "Tipo de interação", "sentimento": "Sentimento", "rota": "Rota",
                 "depoimento": "Depoimento", "pergunta_tecnica": "Pergunta técnica",
                 "feedback": "Feedback", "reclamacao": "Reclamação", "projeto": "Projeto", "outro": "Outro",
                 "case_sucesso": "Case de sucesso", "faq": "FAQ", "alerta": "Alerta", "nenhuma": "Nenhuma"}
        return e(nomes.get(valor, valor))

    def percentual(valor):
        return f"{100 * valor:.1f}%".replace(".", ",")

    def variacao(valor):
        return f"{valor:+.1f} p.p.".replace(".", ",", 1)

    atual = resultado["atual"]
    tabelas = []
    for dimensao, linhas in atual["distribuicoes"].items():
        corpo = "".join(f'<tr><th scope="row">{rotulo(l["categoria"])}</th><td>{l["quantidade"]}</td><td><meter min="0" max="1" value="{l["proporcao"]}" aria-label="Proporção de {rotulo(l["categoria"])}"></meter> {percentual(l["proporcao"])}</td></tr>' for l in linhas)
        tabelas.append(f'<section class="panel"><h2>{rotulo(dimensao)}</h2><table><caption>Distribuição por {e(dimensao)} • {atual["total_interacoes"]} mensagens</caption><thead><tr><th scope="col">Categoria</th><th scope="col">Mensagens</th><th scope="col">Proporção</th></tr></thead><tbody>{corpo}</tbody></table></section>')
    topicos = "".join(f'<tr><th scope="row">{e(t["topico"])}</th><td>{t["quantidade"]}</td><td>{e(", ".join(map(str, t["indices_origem"])))}</td><td>{"Conferir recorrência" if t["recorrente"] else "Ocorrência única"}</td></tr>' for t in atual["perguntas_por_topico"])
    comparacao = resultado["comparacao"]
    comparacao_html = '<p>Sem lote anterior: a comparação não foi calculada.</p>'
    if comparacao:
        linhas = "".join(f'<tr><th scope="row">{rotulo(l["dimensao"])} / {rotulo(l["categoria"])}</th><td>{l["quantidade_anterior"]} ({percentual(l["proporcao_anterior"])})</td><td>{l["quantidade_atual"]} ({percentual(l["proporcao_atual"])})</td><td>{variacao(l["variacao_pontos_percentuais"])}</td></tr>' for l in comparacao["categorias"])
        comparacao_html = f'<p>{e(comparacao["periodo_anterior"])} ({comparacao["total_anterior"]} mensagens) → {e(comparacao["periodo_atual"])} ({comparacao["total_atual"]} mensagens).</p><p>{e(comparacao["interpretacao"])}</p><div class="scroll"><table><caption>Variação da participação de cada categoria</caption><thead><tr><th scope="col">Categoria</th><th scope="col">Anterior</th><th scope="col">Atual</th><th scope="col">Variação</th></tr></thead><tbody>{linhas}</tbody></table></div>'
    natureza = "Demonstração sintética" if atual["natureza_dados"] == "sintetica" else "Análise descritiva de mensagens"
    indicadores = atual["indicadores"]
    cards = [(atual["total_interacoes"], "Mensagens no lote"), (indicadores["perguntas_tecnicas"], "Perguntas técnicas"),
             (indicadores["mensagens_em_alerta"], "Mensagens em alerta"), (indicadores["topicos_com_perguntas_repetidas"], "Tópicos repetidos nas perguntas")]
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>CommunityLab | Radar da comunidade</title>
<style>
:root{{color-scheme:light;--ink:#16303c;--muted:#4b626b;--line:#d5e1e1;--teal:#086b64}}
*{{box-sizing:border-box}}body{{margin:0;background:#f2f6f5;color:var(--ink);font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:44px 26px}}header{{border-top:5px solid var(--teal);padding-top:26px;margin-bottom:28px}}h1{{font-size:clamp(2rem,4vw,3.5rem);line-height:1.1;letter-spacing:-.04em;margin:15px 0}}h2{{font-size:1.35rem;margin-top:0}}p{{max-width:90ch}}.eyebrow{{font-weight:700;letter-spacing:.12em;font-size:.8rem;text-transform:uppercase;color:var(--teal)}}.meta{{color:var(--muted)}}.notice{{background:#fff4d9;border-left:4px solid #ab7523;padding:15px 18px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:26px 0}}.card,.panel{{border:1px solid var(--line);border-radius:12px;padding:22px;background:white}}.card strong{{display:block;font-size:2.7rem;line-height:1.2}}.card span{{color:var(--muted);font-size:.9rem}}.panel{{margin:20px 0}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}caption{{text-align:left;color:var(--muted);margin:0 0 14px}}th,td{{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}thead th{{background:#eaf3f1;font-size:.8rem}}tbody th{{font-weight:500}}meter{{width:110px;height:13px;accent-color:var(--teal)}}.scroll{{overflow-x:auto}}.scroll table{{min-width:580px}}li{{margin:8px 0}}code{{overflow-wrap:anywhere;font-size:.8rem}}summary{{cursor:pointer;font-weight:600}}footer{{font-size:.85rem;color:var(--muted);margin-top:30px}}
@media(max-width:700px){{main{{padding:24px 16px}}.cards{{grid-template-columns:repeat(2,1fr)}}.panel{{padding:16px}}meter{{display:none}}th,td{{padding:9px 5px}}}}
@media print{{body{{background:white;font-size:10pt}}main{{max-width:none;padding:0}}.panel,.card{{break-inside:avoid}}.scroll{{overflow:visible}}details>*{{display:block}}}}
</style></head><body><main>
<header><div class="eyebrow">CommunityLab / Análise de Dados</div><h1>Radar da comunidade</h1><p>Distribuição das interações, perguntas por tópico e comparação entre lotes para apoiar a revisão da equipe.</p><p class="meta">{e(atual["origem_comunidade"])} · {e(atual["periodo_referencia"])} · Modo declarado: {e(atual["modo_classificacao"])}</p></header>
<div class="notice"><strong>{e(natureza)}</strong>. As contagens descrevem mensagens classificadas. Não representam pessoas únicas nem um índice validado de saúde. {e(resultado.get("nota_demonstracao", ""))}</div>
<div class="cards">{"".join(f'<div class="card"><strong>{n}</strong><span>{e(rotulo)}</span></div>' for n, rotulo in cards)}</div>
<section class="panel"><h2>Leitura do lote</h2><p>{percentual(indicadores["proporcao_mensagens_negativas"])} das mensagens foram classificadas com sentimento negativo; {percentual(indicadores["proporcao_mensagens_em_alerta"])} receberam rota de alerta. Essas dimensões não são equivalentes: reclamações também podem ser encaminhadas como alerta.</p><p>{indicadores["perguntas_em_alerta"]} perguntas técnicas receberam alerta e continuam incluídas na análise de dúvidas. Registros possivelmente duplicados: {indicadores["registros_possivelmente_duplicados"]}.</p><ul>{"".join(f'<li>{e(r)}</li>' for r in atual["recomendacoes_para_revisao"])}</ul></section>
{"".join(tabelas)}
<section class="panel"><h2>Perguntas por tópico</h2><p>Agrupamento por texto do tópico, normalizando caixa e espaços. Repetição exige pelo menos duas mensagens; a equivalência das dúvidas depende de revisão.</p><div class="scroll"><table><caption>Rastreabilidade pelas posições no lote atual, começando em 1</caption><thead><tr><th scope="col">Tópico</th><th scope="col">Mensagens</th><th scope="col">Índices de origem</th><th scope="col">Leitura</th></tr></thead><tbody>{topicos or '<tr><td colspan="4">Nenhuma pergunta técnica classificada.</td></tr>'}</tbody></table></div></section>
<section class="panel"><h2>Comparação entre períodos</h2>{comparacao_html}</section>
<section class="panel"><h2>Limites de interpretação</h2><ul>{"".join(f'<li>{e(l)}</li>' for l in atual["limitacoes"])}</ul></section>
<details class="panel"><summary>Rastreabilidade</summary><p>Hash canônico do lote atual: <code>{e(resultado["rastreabilidade"]["lote_atual_sha256"])}</code></p><p>Hash canônico do lote anterior: <code>{e(resultado["rastreabilidade"]["lote_anterior_sha256"])}</code></p><p>{e(resultado["rastreabilidade"]["metodo_hash"])}</p></details>
<footer>CommunityLab · Indicadores descritivos sujeitos a revisão humana.</footer>
</main></body></html>'''
