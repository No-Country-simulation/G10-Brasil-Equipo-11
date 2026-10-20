import csv
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("text", "channel", "type")


def _validate_interactions(
    interactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Valida e normaliza uma lista de interações."""

    if not interactions:
        raise ValueError("O arquivo não contém interações.")

    normalized_interactions = []

    for index, interaction in enumerate(interactions, start=1):
        if not isinstance(interaction, dict):
            raise ValueError(
                f"A interação {index} deve ser um objeto."
            )

        normalized = {
            str(key).strip(): (
                value.strip() if isinstance(value, str) else value
            )
            for key, value in interaction.items()
        }

        for field in REQUIRED_FIELDS:
            value = normalized.get(field)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"A interação {index} possui o campo "
                    f"obrigatório '{field}' ausente ou inválido."
                )

        normalized_interactions.append(normalized)

    return normalized_interactions


def load_interactions(file_path: str | Path) -> list[dict[str, Any]]:
    """
    Carrega interações de um arquivo CSV ou JSON.

    O JSON pode conter uma lista de interações diretamente
    ou um objeto com a chave 'interactions'.

    Retorna uma lista de dicionários validados.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"O caminho informado não é um arquivo: {path}"
        )

    extension = path.suffix.lower()

    if extension == ".json":
        try:
            with path.open("r", encoding="utf-8-sig") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"O arquivo JSON é inválido: {exc}"
            ) from exc

        if isinstance(data, dict):
            interactions = data.get("interactions")
        else:
            interactions = data

        if not isinstance(interactions, list):
            raise ValueError(
                "O JSON deve conter uma lista de interações "
                "ou um objeto com a chave 'interactions'."
            )

    elif extension == ".csv":
        try:
            with path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:
                reader = csv.DictReader(file)

                if not reader.fieldnames:
                    raise ValueError(
                        "O CSV está vazio ou não possui cabeçalho."
                    )

                headers = {
                    header.strip()
                    for header in reader.fieldnames
                    if header is not None
                }

                missing_fields = [
                    field
                    for field in REQUIRED_FIELDS
                    if field not in headers
                ]

                if missing_fields:
                    raise ValueError(
                        "O CSV não possui as colunas obrigatórias: "
                        + ", ".join(missing_fields)
                    )

                interactions = [
                    {
                        key.strip(): value
                        for key, value in row.items()
                        if key is not None
                    }
                    for row in reader
                ]

        except csv.Error as exc:
            raise ValueError(
                f"Não foi possível interpretar o CSV: {exc}"
            ) from exc

    else:
        raise ValueError(
            "Formato não suportado. Utilize um arquivo CSV ou JSON."
        )

    return _validate_interactions(interactions)