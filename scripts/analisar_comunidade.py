"""Gera o radar analítico a partir de lotes classificados ou de demonstração mock."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))

from app.ia import classificar  # noqa: E402
from app.schemas import Interacao  # noqa: E402
from communitylab.avaliacao import _escrever_csv, carregar_base, ler_json  # noqa: E402
from communitylab.radar import construir_radar, renderizar_radar  # noqa: E402


def _demonstracao():
    base = carregar_base(RAIZ / "data/avaliacao_classificacoes.json")
    modo_anterior = os.environ.get("LLM_MODO")
    os.environ["LLM_MODO"] = "mock"
    try:
        lotes = []
        for paridade, periodo in ((0, "lote_sintetico_A"), (1, "lote_sintetico_B")):
            # Divisão intercalada: cinco casos de cada tipo em cada lote.
            analises = [classificar(Interacao(**{**c["entrada"], "tipo": "outro"})).model_dump() for c in base["casos"][paridade::2]]
            lotes.append({"origem_comunidade": "CommunityLab_demonstracao", "periodo_referencia": periodo,
                          "natureza_dados": "sintetica", "modo_classificacao": "mock", "analises": analises})
        return lotes[1], lotes[0]
    finally:
        if modo_anterior is None:
            os.environ.pop("LLM_MODO", None)
        else:
            os.environ["LLM_MODO"] = modo_anterior


def main(argv=None):
    parser = argparse.ArgumentParser(description="Radar descritivo: somente análise local, sem chamadas a serviços externos.")
    fonte = parser.add_mutually_exclusive_group(required=True)
    fonte.add_argument("--atual", type=Path, help="Lote analítico com metadados explícitos e analises")
    fonte.add_argument("--demonstracao", action="store_true", help="Dois lotes sintéticos classificados em mock com tipo oculto")
    parser.add_argument("--anterior", type=Path, help="Lote anterior comparável, opcional")
    parser.add_argument("--saida", type=Path, default=RAIZ / "data/output/radar")
    args = parser.parse_args(argv)
    if args.demonstracao and args.anterior:
        parser.error("--demonstracao já define os dois lotes; não use --anterior.")
    try:
        if args.demonstracao:
            atual, anterior = _demonstracao()
        else:
            atual = ler_json(args.atual)
            anterior = ler_json(args.anterior) if args.anterior else None
        resultado = construir_radar(atual, anterior)
        if args.demonstracao:
            resultado["nota_demonstracao"] = "Dois recortes intercalados da base sintética de avaliação. Os nomes A/B não são períodos observados de uma comunidade real."
        entradas = {p.resolve() for p in (args.atual, args.anterior) if p}
        nomes = ["radar.json", "radar.html", "distribuicoes.csv", "comparacao_categorias.csv", "lote_atual.json", "lote_anterior.json"]
        if any((args.saida / nome).resolve() in entradas for nome in nomes):
            raise ValueError("A saída não pode sobrescrever arquivos de entrada.")
        args.saida.mkdir(parents=True, exist_ok=True)
        (args.saida / "radar.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (args.saida / "radar.html").write_text(renderizar_radar(resultado), encoding="utf-8")
        campos = ["categoria", "quantidade", "proporcao"]
        _escrever_csv(args.saida / "distribuicoes.csv", ["dimensao", *campos], ([d, *(linha[c] for c in campos)] for d, linhas in resultado["atual"]["distribuicoes"].items() for linha in linhas))
        campos_comparacao = ["dimensao", "categoria", "quantidade_anterior", "quantidade_atual", "proporcao_anterior", "proporcao_atual", "variacao_pontos_percentuais"]
        linhas = (resultado["comparacao"] or {}).get("categorias", [])
        _escrever_csv(args.saida / "comparacao_categorias.csv", campos_comparacao, ([linha[c] for c in campos_comparacao] for linha in linhas))
        if args.demonstracao:
            for nome, lote in (("lote_atual.json", atual), ("lote_anterior.json", anterior)):
                (args.saida / nome).write_text(json.dumps(lote, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Radar: {args.saida / 'radar.html'}")
        print("Comparação descritiva; indicadores dependem da qualidade das classificações.")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Não foi possível analisar: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
