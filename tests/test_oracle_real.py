import os
import uuid

import pytest

pytestmark = pytest.mark.real


def test_oracle_real_conexao_e_schema():
    from app import database

    if (
        os.getenv(
            "COMMUNITYLAB_DB_MODE", "disabled"
        ).strip().lower() != "oracle"
        or not database.oracle_configured()
    ):
        pytest.skip(
            "Oracle não configurado para este teste."
        )

    try:
        assert database.ping() is True
        database.validate_schema()
    finally:
        database.close_pool()


def test_oracle_real_dml_e_rollback():
    from app import database

    if (
        os.getenv(
            "COMMUNITYLAB_DB_MODE", "disabled"
        ).strip().lower() != "oracle"
        or not database.oracle_configured()
    ):
        pytest.skip(
            "Oracle não configurado para este teste."
        )

    try:
        import oracledb
    except ImportError:
        pytest.skip(
            "Instale o driver com pip install -r requirements.txt."
        )

    process_id = str(uuid.uuid4())

    try:
        with database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.setinputsizes(
                    payload=oracledb.DB_TYPE_CLOB
                )

                cursor.execute(
                    """
                    INSERT INTO CL_PROCESSAMENTOS (
                        ID, REQUEST_SHA256,
                        ORIGEM_COMUNIDADE,
                        PERIODO_REFERENCIA,
                        STATUS, MODO_IA,
                        TOTAL_INTERACOES,
                        ENTRADA_JSON, OCI_STATUS,
                        CRIADO_EM
                    )
                    VALUES (
                        :id, :hash,
                        'SMOKE_TEST',
                        'TESTE_ROLLBACK',
                        'ERRO', 'mock',
                        0, :payload,
                        'PENDENTE',
                        SYSTIMESTAMP
                    )
                    """,
                    {
                        "id": process_id,
                        "hash": "0" * 64,
                        "payload": '{"smoke_test":true}',
                    },
                )

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM CL_PROCESSAMENTOS
                    WHERE ID = :id
                    """,
                    {"id": process_id},
                )

                assert cursor.fetchone()[0] == 1

                conn.rollback()

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM CL_PROCESSAMENTOS
                    WHERE ID = :id
                    """,
                    {"id": process_id},
                )

                assert cursor.fetchone()[0] == 0

    finally:
        database.close_pool()