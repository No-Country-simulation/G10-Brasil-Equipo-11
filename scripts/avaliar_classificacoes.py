"""Execute na raiz: python scripts/avaliar_classificacoes.py --help."""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))

from app import ia, llm  # noqa: E402
from communitylab.avaliacao import (  # noqa: E402
    CENARIOS, avaliar, carregar_base, ler_json, salvar_resultados, validar_previsoes,
)


@contextmanager
def configurar_modo(modo):
    anterior = os.environ.get("LLM_MODO")
    if modo == "gemini" and not os.environ.get("GEMINI_API_KEY", "").strip():
        raise ValueError("Gemini exige GEMINI_API_KEY. Nenhuma chamada foi realizada; use --modo mock para simulação.")
    os.environ["LLM_MODO"] = modo
    try:
        yield
    finally:
        if anterior is None:
            os.environ.pop("LLM_MODO", None)
        else:
            os.environ["LLM_MODO"] = anterior


def main(argv=None):
    parser = argparse.ArgumentParser(description="Avaliação de classificações do CommunityLab. Padrão: mock local, sem credenciais.")
    parser.add_argument("--base", type=Path, default=RAIZ / "data/avaliacao_classificacoes.json")
    parser.add_argument("--cenario", choices=CENARIOS, default="tipo_oculto")
    parser.add_argument("--modo", choices=("mock", "gemini", "arquivo"), default="mock", help="gemini envia os textos ao provedor e usa a cota configurada; arquivo avalia previsões existentes")
    parser.add_argument("--previsoes", type=Path, help="JSON identificado por IDs; obrigatório em modo arquivo")
    parser.add_argument("--saida", type=Path, default=RAIZ / "data/output/avaliacao", help="Pasta base; cria subpasta com modo e cenário")
    parser.add_argument("--exigir-metas", action="store_true", help="Retorna código 1 se alguma meta não for atendida; consulte o status de revisão dos critérios; não aprova produção")
    args = parser.parse_args(argv)
    if (args.modo == "arquivo") != (args.previsoes is not None):
        parser.error("Use --previsoes somente e obrigatoriamente com --modo arquivo.")
    try:
        base = carregar_base(args.base)
        try:
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, check=True, capture_output=True, text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            commit = "indisponivel"
        metadados = {"modo": args.modo, "commit_base": commit,
                     "dependencias": {"pydantic": version("pydantic")},
                     "modelo": "regras_mock" if args.modo == "mock" else llm.modelo(),
                     "arquivos_sha256": {p: hashlib.sha256((RAIZ / p).read_bytes()).hexdigest() for p in (
                         "app/ia.py", "app/llm.py", "app/prompts.py", "app/schemas.py",
                         "src/communitylab/avaliacao.py", "src/communitylab/relatorio_avaliacao.py",
                         "scripts/avaliar_classificacoes.py",
                     )}}
        if args.modo == "gemini":
            metadados["inicio_execucao_utc"] = datetime.now(timezone.utc).isoformat()
        elif args.modo == "arquivo":
            metadados["importado_em_utc"] = datetime.now(timezone.utc).isoformat()
        if args.modo == "arquivo":
            previsoes = validar_previsoes(args.previsoes, base, args.cenario)
            metadados["modelo"] = ler_json(args.previsoes)["modelo"]
            metadados["origem_modelo"] = "declarado_no_arquivo_nao_verificado"
            metadados["previsoes_sha256"] = hashlib.sha256(args.previsoes.read_bytes()).hexdigest()
            # A identidade vem do ID da base, nunca da posição da previsão no JSON.
            por_entrada = {(c["entrada"]["autor"], c["entrada"]["canal"], c["entrada"]["texto"]): c["id"] for c in base["casos"]}
            def classificador(entrada):
                return previsoes[por_entrada[(entrada.autor, entrada.canal, entrada.texto)]]
            resultado = avaliar(base, classificador, cenario=args.cenario, metadados=metadados)
        else:
            with configurar_modo(args.modo):
                resultado = avaliar(base, ia.classificar, cenario=args.cenario, metadados=metadados)
        destino = args.saida / f"{args.modo}_{args.cenario}"
        # Não permitir que uma pasta de saída substitua a própria base/previsões.
        entradas = {args.base.resolve(), *( [args.previsoes.resolve()] if args.previsoes else [])}
        nomes = ["resultado.json", "relatorio.html", "revisao_classificacoes.csv", "metricas_por_categoria.csv", "matriz_confusao_tipo.csv", "matriz_confusao_sentimento.csv", "matriz_confusao_rota.csv"]
        if any((destino / nome).resolve() in entradas for nome in nomes):
            raise ValueError("A saída não pode sobrescrever um arquivo de entrada.")
        salvar_resultados(resultado, destino)
        cobertura = resultado["cobertura"]
        print(f"Modo: {args.modo}; cenário: {args.cenario}; válidos: {cobertura['validos']}/{cobertura['total']}.")
        print(f"Relatório: {destino / 'relatorio.html'}")
        revisao = resultado["metadados"]["revisao_anotacao"]
        if revisao:
            print(f"Base sintética. Referências e critérios revisados individualmente por {revisao['revisor']} em {revisao['data']}.")
            print("Essa revisão não aprova as previsões nem o uso em produção.")
        else:
            print("Base sintética. Referências e metas pendentes de revisão humana.")
        if cobertura["falhas"]:
            return 1
        return int(args.exigir_metas and not all(c["atendido"] is True for c in resultado["criterios"]))
    except (ValueError, OSError) as exc:
        print(f"Não foi possível avaliar: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
