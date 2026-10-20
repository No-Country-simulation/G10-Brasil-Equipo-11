import csv
import json
from pathlib import Path
from typing import Any

from app.schemas import Interacao, LoteEntrada
from communitylab.ingestion import load_interactions


ALIASES = {
    "text": "texto",
    "channel": "canal",
    "type": "tipo",
    "author": "autor",
}


def _normalizar_interacao(
    registro: dict[str, Any],
    indice: int,
) -> Interacao:
    """Converte uma interação para o contrato oficial do pipeline."""

    dados = {
        ALIASES.get(str(chave).strip(), str(chave).strip()): valor
        for chave, valor in registro.items()
    }

    texto = dados.get("texto")
    canal = dados.get("canal")
    tipo = dados.get("tipo") or "outro"
    autor = dados.get("autor")

    if not isinstance(texto, str) or not texto.strip():
        raise ValueError(
            f"A interação {indice} não possui um texto válido."
        )

    if not isinstance(canal, str) or not canal.strip():
        raise ValueError(
            f"A interação {indice} não possui um canal válido."
        )

    if not isinstance(tipo, str) or not tipo.strip():
        tipo = "outro"

    if not isinstance(autor, str) or not autor.strip():
        autor = f"anônimo_{indice:03d}"

    return Interacao(
        autor=autor.strip(),
        canal=canal.strip(),
        tipo=tipo.strip(),
        texto=texto.strip(),
    )


def carregar_lote(
    caminho: str | Path,
    origem_comunidade: str | None = None,
    periodo_referencia: str | None = None,
) -> LoteEntrada:
    """
    Carrega CSV ou JSON e converte os registros para LoteEntrada.

    Aceita os campos em português e inglês. Para JSON no formato
    do pipeline, preserva origem_comunidade e periodo_referencia.
    """

    path = Path(caminho)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    if not path.is_file():
        raise ValueError(f"O caminho não é um arquivo: {path}")

    origem_arquivo = None
    periodo_arquivo = None

    if path.suffix.lower() == ".json":
        try:
            with path.open("r", encoding="utf-8-sig") as arquivo:
                conteudo = json.load(arquivo)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido: {exc}") from exc

        if isinstance(conteudo, dict):
            origem_arquivo = conteudo.get("origem_comunidade")
            periodo_arquivo = conteudo.get("periodo_referencia")

            if "interacoes" in conteudo:
                registros = conteudo["interacoes"]
            elif "interactions" in conteudo:
                registros = conteudo["interactions"]
            else:
                raise ValueError(
                    "O JSON deve conter 'interacoes' ou 'interactions'."
                )
        elif isinstance(conteudo, list):
            registros = conteudo
        else:
            raise ValueError(
                "O JSON deve conter uma lista ou um objeto com interações."
            )

        if not isinstance(registros, list):
            raise ValueError("A coleção de interações deve ser uma lista.")

    elif path.suffix.lower() == ".csv":
        # Preserva a validação já existente para CSV no formato original.
        try:
            registros = load_interactions(path)
        except ValueError as erro_original:
            # Tenta o contrato em português sem alterar ingestion.py.
            with path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as arquivo:
                leitor = csv.DictReader(arquivo)

                if not leitor.fieldnames:
                    raise erro_original

                cabecalhos = {
                    campo.strip()
                    for campo in leitor.fieldnames
                    if campo is not None
                }

                obrigatorios_pt = {"texto", "canal", "tipo"}
                if not obrigatorios_pt.issubset(cabecalhos):
                    raise erro_original

                registros = [
                    {
                        str(chave).strip(): valor
                        for chave, valor in linha.items()
                        if chave is not None
                    }
                    for linha in leitor
                ]
    else:
        raise ValueError(
            "Formato não suportado. Utilize um arquivo CSV ou JSON."
        )

    if not registros:
        raise ValueError("O arquivo não contém interações.")

    interacoes = [
        _normalizar_interacao(registro, indice)
        for indice, registro in enumerate(registros, start=1)
    ]

    origem = origem_comunidade or origem_arquivo or "comunidade_importada"
    periodo = (
        periodo_referencia
        or periodo_arquivo
        or "periodo_nao_informado"
    )

    return LoteEntrada(
        origem_comunidade=origem,
        periodo_referencia=periodo,
        interacoes=interacoes,
    )
