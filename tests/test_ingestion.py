import json

import pytest

from communitylab.ingestion import load_interactions


def test_load_valid_json(tmp_path):
    """Deve carregar um JSON válido."""

    file_path = tmp_path / "interactions.json"

    data = {
        "community": "Comunidade de Tecnologia",
        "reference_period": "2026-10",
        "interactions": [
            {
                "channel": "forum",
                "type": "question",
                "text": "Como estudar Python?",
            }
        ],
    }

    file_path.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )

    result = load_interactions(file_path)

    assert len(result) == 1
    assert result[0]["channel"] == "forum"
    assert result[0]["text"] == "Como estudar Python?"


def test_load_valid_csv(tmp_path):
    """Deve carregar um CSV válido."""

    file_path = tmp_path / "interactions.csv"

    file_path.write_text(
        "channel,type,text\n"
        'forum,question,"Como estudar Python?"\n',
        encoding="utf-8",
    )

    result = load_interactions(file_path)

    assert len(result) == 1
    assert result[0]["type"] == "question"


def test_reject_interaction_without_text(tmp_path):
    """Deve rejeitar uma interação sem texto."""

    file_path = tmp_path / "invalid.json"

    data = {
        "interactions": [
            {
                "channel": "forum",
                "type": "question",
                "text": "   ",
            }
        ]
    }

    file_path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="text"):
        load_interactions(file_path)


def test_reject_unsupported_format(tmp_path):
    """Deve rejeitar formatos não suportados."""

    file_path = tmp_path / "interactions.txt"
    file_path.write_text("conteúdo", encoding="utf-8")

    with pytest.raises(ValueError, match="não suportado"):
        load_interactions(file_path)


def test_reject_missing_file(tmp_path):
    """Deve informar quando o arquivo não existe."""

    file_path = tmp_path / "inexistente.json"

    with pytest.raises(FileNotFoundError):
        load_interactions(file_path)