"""Repositório Oracle do CommunityLab: transações, idempotência e auditoria."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any

from . import database


class RecordNotFound(LookupError):
    pass


class IdempotencyConflict(ValueError):
    pass


class ProcessingInProgress(RuntimeError):
    pass


class AttemptSuperseded(ProcessingInProgress):
    """Uma execução expirou e outra tentativa assumiu o mesmo lote."""


class VersionConflict(RuntimeError):
    pass


class InvalidCuration(ValueError):
    pass


def json_dumps(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def json_loads(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "read"):
        value = value.read()
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(value) if isinstance(value, str) else value


def _text_value(value: Any) -> str | None:
    """Lê um CLOB sem depender da configuração fetch_lobs do driver."""
    if value is None:
        return None
    if hasattr(value, "read"):
        value = value.read()
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return value if isinstance(value, str) else str(value)


def fingerprint_request(payload: dict) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _set_clobs(cursor, *names: str) -> None:
    import oracledb

    cursor.setinputsizes(
        **{name: oracledb.DB_TYPE_CLOB for name in names}
    )

def _normalizar_data_interacao(valor: Any) -> date:
    """
    Converte a data recebida.
    Quando não houver data original, utiliza a data da importação
    no fuso horário de São Paulo.
    """

    if valor is None or valor == "":
        return datetime.now(
            ZoneInfo("America/Sao_Paulo")
        ).date()

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    return date.fromisoformat(str(valor).strip()[:10])

def _existing_by_key(
    cursor,
    key: str,
    *,
    for_update: bool = False,
):
    sql = """
        SELECT ID, REQUEST_SHA256, STATUS, RESULTADO_JSON,
               OCI_STATUS, OCI_BUCKET, OCI_OBJECT_NAME,
               OCI_ETAG, TOTAL_INTERACOES
        FROM CL_PROCESSAMENTOS
        WHERE IDEMPOTENCY_KEY = :key
    """
    if for_update:
        sql += " FOR UPDATE"

    cursor.execute(sql, {"key": key})
    return cursor.fetchone()


def iniciar_processamento(
    lote: dict,
    idempotency_key: str | None,
) -> dict:
    """Cria um lote PROCESSANDO ou recupera uma tentativa idempotente."""
    process_id = str(uuid.uuid4())
    attempt_token = str(uuid.uuid4())
    request_hash = fingerprint_request(lote)
    payload_json = json_dumps(lote)

    with database.connection() as conn:
        with conn.cursor() as cursor:
            if idempotency_key:
                existing = _existing_by_key(
                    cursor,
                    idempotency_key,
                    for_update=True,
                )

                if existing:
                    (
                        old_id,
                        old_hash,
                        status,
                        result_json,
                        oci_status,
                        bucket,
                        object_name,
                        etag,
                        total,
                    ) = existing

                    if old_hash != request_hash:
                        raise IdempotencyConflict(
                            "A chave de idempotência já foi usada "
                            "com outro conteúdo. Use uma chave nova."
                        )

                    if status == "PROCESSANDO":
                        cursor.execute(
                            """
                            SELECT INICIADO_EM
                            FROM CL_PROCESSAMENTOS
                            WHERE ID = :id
                            """,
                            {"id": old_id},
                        )
                        start_row = cursor.fetchone()
                        started_at = start_row[0] if start_row else None

                        stale_seconds = max(
                            300,
                            int(
                                os.getenv(
                                    "COMMUNITYLAB_PROCESSING_STALE_SECONDS",
                                    "3600",
                                )
                            ),
                        )

                        age = (
                            (
                                datetime.now(timezone.utc)
                                - started_at.astimezone(timezone.utc)
                            ).total_seconds()
                            if started_at
                            else stale_seconds + 1
                        )

                        if age > stale_seconds:
                            cursor.execute(
                                """
                                UPDATE CL_PROCESSAMENTOS
                                SET STATUS = 'PROCESSANDO',
                                    ATTEMPT_TOKEN = :attempt,
                                    ERRO_CODIGO = NULL,
                                    ERRO_DETALHE = NULL,
                                    INICIADO_EM = SYSTIMESTAMP,
                                    FINALIZADO_EM = NULL,
                                    ATUALIZADO_EM = SYSTIMESTAMP
                                WHERE ID = :id
                                """,
                                {
                                    "attempt": attempt_token,
                                    "id": old_id,
                                },
                            )

                            cursor.execute(
                                """
                                SELECT ID
                                FROM CL_INTERACOES
                                WHERE PROCESSAMENTO_ID = :id
                                ORDER BY POSICAO
                                """,
                                {"id": old_id},
                            )
                            interaction_ids = [
                                row[0] for row in cursor.fetchall()
                            ]

                            conn.commit()

                            return {
                                "existing": False,
                                "retry": True,
                                "id": old_id,
                                "attempt_token": attempt_token,
                                "interaction_ids": interaction_ids,
                                "request_hash": request_hash,
                            }

                        raise ProcessingInProgress(
                            "Esta requisição já está sendo processada."
                        )

                    if status == "SUCESSO" and result_json:
                        conn.rollback()
                        return {
                            "existing": True,
                            "id": old_id,
                            "response": json_loads(result_json),
                            "oci_status": oci_status,
                            "bucket": bucket,
                            "object_name": object_name,
                            "etag": etag,
                            "total": total,
                        }

                    if status == "ERRO":
                        cursor.execute(
                            """
                            UPDATE CL_PROCESSAMENTOS
                            SET STATUS = 'PROCESSANDO',
                                ATTEMPT_TOKEN = :attempt,
                                ERRO_CODIGO = NULL,
                                ERRO_DETALHE = NULL,
                                INICIADO_EM = SYSTIMESTAMP,
                                FINALIZADO_EM = NULL,
                                ATUALIZADO_EM = SYSTIMESTAMP
                            WHERE ID = :id
                            """,
                            {
                                "attempt": attempt_token,
                                "id": old_id,
                            },
                        )

                        cursor.execute(
                            """
                            SELECT ID
                            FROM CL_INTERACOES
                            WHERE PROCESSAMENTO_ID = :id
                            ORDER BY POSICAO
                            """,
                            {"id": old_id},
                        )
                        interaction_ids = [
                            row[0] for row in cursor.fetchall()
                        ]

                        conn.commit()

                        return {
                            "existing": False,
                            "retry": True,
                            "id": old_id,
                            "attempt_token": attempt_token,
                            "interaction_ids": interaction_ids,
                            "request_hash": request_hash,
                        }

            try:
                _set_clobs(cursor, "payload")

                cursor.execute(
                    """
                    INSERT INTO CL_PROCESSAMENTOS (
                        ID, IDEMPOTENCY_KEY, REQUEST_SHA256,
                        ATTEMPT_TOKEN, ORIGEM_COMUNIDADE,
                        PERIODO_REFERENCIA, STATUS, MODO_IA,
                        TOTAL_INTERACOES, ENTRADA_JSON,
                        OCI_STATUS, INICIADO_EM, CRIADO_EM
                    )
                    VALUES (
                        :id, :ikey, :request_hash, :attempt,
                        :origin, :period, 'PROCESSANDO',
                        :llm_mode, :total, :payload,
                        'PENDENTE', SYSTIMESTAMP, SYSTIMESTAMP
                    )
                    """,
                    {
                        "id": process_id,
                        "ikey": idempotency_key,
                        "request_hash": request_hash,
                        "attempt": attempt_token,
                        "origin": lote["origem_comunidade"],
                        "period": lote["periodo_referencia"],
                        "llm_mode": (
                            "mock"
                            if __import__(
                                "app.llm",
                                fromlist=["modo_mock"],
                            ).modo_mock()
                            else "gemini"
                        ),
                        "total": len(lote["interacoes"]),
                        "payload": payload_json,
                    },
                )

            except Exception as exc:
                conn.rollback()

                # Recupera o registro vencedor se houve concorrência
                # pela mesma chave única de idempotência.
                if idempotency_key:
                    with conn.cursor() as retry_cursor:
                        found = _existing_by_key(
                            retry_cursor,
                            idempotency_key,
                        )

                        if found:
                            if found[1] != request_hash:
                                raise IdempotencyConflict(
                                    "A chave de idempotência foi "
                                    "usada com outro conteúdo."
                                ) from exc

                            if found[2] == "PROCESSANDO":
                                raise ProcessingInProgress(
                                    "Esta requisição já está sendo processada."
                                ) from exc

                            if found[2] == "SUCESSO" and found[3]:
                                return {
                                    "existing": True,
                                    "id": found[0],
                                    "response": json_loads(found[3]),
                                    "oci_status": found[4],
                                    "bucket": found[5],
                                    "object_name": found[6],
                                    "etag": found[7],
                                    "total": found[8],
                                }

                raise

            interaction_ids: list[str] = []
            rows = []

            for index, item in enumerate(
                lote["interacoes"],
                start=1,
            ):
                interaction_id = str(uuid.uuid4())
                interaction_ids.append(interaction_id)

                rows.append(
                    {
                        "id": interaction_id,
                        "process_id": process_id,
                        "position": index,
                        "message_date": _normalizar_data_interacao(
                            item.get("data")
                        ),
                        "author": item["autor"],
                        "channel": item["canal"],
                        "kind": item["tipo"],
                        "text": item["texto"],
                    }
                )

            if rows:
                _set_clobs(cursor, "text")

                cursor.executemany(
                    """
                    INSERT INTO CL_INTERACOES (
                        ID,
                        PROCESSAMENTO_ID,
                        POSICAO,
                        DATA_INTERACAO,
                        AUTOR,
                        CANAL,
                        TIPO,
                        TEXTO,
                        CRIADO_EM
                    )
                    VALUES (
                        :id,
                        :process_id,
                        :position,
                        :message_date,
                        :author,
                        :channel,
                        :kind,
                        :text,
                        SYSTIMESTAMP
                    )
                    """,
                    rows,
                )

            conn.commit()

            return {
                "existing": False,
                "retry": False,
                "id": process_id,
                "attempt_token": attempt_token,
                "interaction_ids": interaction_ids,
                "request_hash": request_hash,
            }


def _asset_records(
    response: dict,
    processing_id: str,
    interaction_ids: list[str],
) -> tuple[list[dict], dict[str, str]]:
    """Prepara ativos publicáveis com fontes de origem explícitas."""
    assets = response.get("ativos_distribuicao_gerados") or {}
    source_map = response.get("fontes_ativos") or {}

    if not isinstance(assets, dict) or not isinstance(source_map, dict):
        raise ValueError(
            "O pipeline precisa retornar ativos e fontes_ativos como objetos JSON."
        )

    records: list[dict] = []
    ids: dict[str, str] = {}
    allowed_source_ids = set(interaction_ids)

    def sources_for(key: str) -> list[str]:
        refs = source_map.get(key, [])

        if not isinstance(refs, list):
            raise ValueError(
                f"fontes_ativos['{key}'] precisa ser uma lista de IDs de interação."
            )

        unique = list(dict.fromkeys(refs))
        invalid = [
            source_id
            for source_id in unique
            if source_id not in allowed_source_ids
        ]

        if invalid:
            raise ValueError(
                f"O ativo '{key}' referencia interações "
                "que não pertencem ao lote atual."
            )

        if not unique:
            raise ValueError(
                f"O ativo '{key}' não possui fonte de origem "
                "rastreável; a persistência foi recusada."
            )

        return unique

    def add(key: str, kind: str, payload: dict):
        if not isinstance(payload, dict):
            raise ValueError(
                f"O payload do ativo '{key}' deve ser um objeto JSON."
            )

        asset_id = str(uuid.uuid4())
        ids[key] = asset_id

        records.append(
            {
                "id": asset_id,
                "process_id": processing_id,
                "key": key,
                "kind": kind,
                "title": (
                    payload.get("titulo")
                    or payload.get("tema")
                    or payload.get("chamada")
                    or payload.get("secao")
                    or kind
                ),
                "payload": payload,
                "sources": sources_for(key),
            }
        )

    if assets.get("post_linkedin"):
        add("post", "POST_LINKEDIN", assets["post_linkedin"])

    if assets.get("destaque_newsletter_semanal"):
        add(
            "newsletter",
            "NEWSLETTER",
            assets["destaque_newsletter_semanal"],
        )

    for index, faq in enumerate(
        assets.get("sugestao_conteudo_faq") or []
    ):
        add(f"faq_{index}", "FAQ", faq)

    return records, ids
def finalizar_processamento(
    
    process_id: str,
    response: dict,
    interaction_ids: list[str],
    attempt_token: str,
    object_name: str,
) -> dict:
    """Grava análises, ativos, fontes e alertas atomicamente."""
    response = dict(response)
    raw_analyses = response.get("analises") or []

    if len(raw_analyses) != len(interaction_ids):
        raise ValueError(
            "O número de análises difere do número de interações persistidas."
        )

    response["analises"] = [
        dict(analysis, interacao_id=interaction_ids[index])
        for index, analysis in enumerate(raw_analyses)
    ]

    analyses = response["analises"]
    records, asset_ids = _asset_records(
        response,
        process_id,
        interaction_ids,
    )

    response["processamento_id"] = process_id
    response["ids_ativos"] = asset_ids
    response["persistencia"] = "oracle"
    response.setdefault("armazenamento_oci", {})

    storage_mode = os.getenv(
        "OCI_STORAGE_MODE", "local"
    ).strip().lower()
    from . import storage
    storage_bucket = (
        storage.bucket_name()
        if storage_mode in {"oci", "required"}
        else "local"
    )

    response["armazenamento_oci"].update({
        "status": "pendente",
        "bucket": storage_bucket or "",
        "caminho_objeto": object_name,
        "sha256": None,
        "etag": None,
        "detalhe": None,
    })

    result_json = json_dumps(response)

    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT STATUS, ATTEMPT_TOKEN
                FROM CL_PROCESSAMENTOS
                WHERE ID = :id
                FOR UPDATE
                """,
                {"id": process_id},
            )
            row = cursor.fetchone()

            if not row:
                raise RecordNotFound(
                    "Lote de processamento não encontrado."
                )

            if row[0] != "PROCESSANDO" or row[1] != attempt_token:
                raise AttemptSuperseded(
                    "Esta tentativa foi substituída por uma execução mais recente."
                )

            cursor.execute(
                """
                SELECT ID, AUTOR, CANAL, TEXTO
                FROM CL_INTERACOES
                WHERE PROCESSAMENTO_ID = :id
                ORDER BY POSICAO
                FOR UPDATE
                """,
                {"id": process_id},
            )
            source_rows = cursor.fetchall()

            if [item[0] for item in source_rows] != interaction_ids:
                raise ValueError(
                    "As interações foram alteradas ou reordenadas."
                )

            for source_row, analysis in zip(
                source_rows,
                analyses,
                strict=True,
            ):
                if (
                    analysis.get("autor") != source_row[1]
                    or analysis.get("canal") != source_row[2]
                    or analysis.get("texto") != _text_value(source_row[3])
                ):
                    raise ValueError(
                        "Uma análise não corresponde exatamente "
                        "à interação de origem persistida."
                    )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM CL_ATIVOS
                WHERE PROCESSAMENTO_ID = :id
                """,
                {"id": process_id},
            )
            if int(cursor.fetchone()[0]) > 0:
                raise RuntimeError(
                    "O processamento já possui ativos persistidos; "
                    "a gravação duplicada foi recusada."
                )

            import oracledb

            cursor.setinputsizes(
                analysis_json=oracledb.DB_TYPE_CLOB
            )

            for index, interaction_id in enumerate(interaction_ids):
                cursor.execute(
                    """
                    UPDATE CL_INTERACOES
                    SET ANALISE_JSON = :analysis_json
                    WHERE ID = :id
                      AND PROCESSAMENTO_ID = :process_id
                    """,
                    {
                        "analysis_json": json_dumps(analyses[index]),
                        "id": interaction_id,
                        "process_id": process_id,
                    },
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "Interação de origem não localizada "
                        "durante a persistência."
                    )

            cursor.setinputsizes(
                result_json=oracledb.DB_TYPE_CLOB
            )
            cursor.execute(
                """
                UPDATE CL_PROCESSAMENTOS
                SET STATUS = 'SUCESSO',
                    RESULTADO_JSON = :result_json,
                    OCI_STATUS = 'PENDENTE',
                    OCI_BUCKET = :bucket,
                    OCI_OBJECT_NAME = :object_name,
                    OCI_ETAG = NULL,
                    OCI_ERRO = NULL,
                    ERRO_CODIGO = NULL,
                    ERRO_DETALHE = NULL,
                    ATTEMPT_TOKEN = NULL,
                    FINALIZADO_EM = SYSTIMESTAMP,
                    ATUALIZADO_EM = SYSTIMESTAMP
                WHERE ID = :id
                  AND STATUS = 'PROCESSANDO'
                  AND ATTEMPT_TOKEN = :attempt
                """,
                {
                    "result_json": result_json,
                    "bucket": storage_bucket,
                    "object_name": object_name,
                    "id": process_id,
                    "attempt": attempt_token,
                },
            )

            if cursor.rowcount != 1:
                raise AttemptSuperseded(
                    "A execução perdeu a posse do processamento antes do commit."
                )

            cursor.setinputsizes(
                payload_json=oracledb.DB_TYPE_CLOB,
                new_payload=oracledb.DB_TYPE_CLOB,
            )

            for record in records:
                payload_json = json_dumps(record["payload"])

                cursor.execute(
                    """
                    INSERT INTO CL_ATIVOS (
                        ID, PROCESSAMENTO_ID, CHAVE_ATIVO,
                        TIPO_ATIVO, TITULO, PAYLOAD_JSON,
                        STATUS_CURADORIA, VERSAO,
                        CONSENTIMENTO_STATUS,
                        CRIADO_EM, ATUALIZADO_EM
                    )
                    VALUES (
                        :id, :process_id, :asset_key,
                        :kind, :title, :payload_json,
                        'PENDENTE', 1, 'NAO_APLICAVEL',
                        SYSTIMESTAMP, SYSTIMESTAMP
                    )
                    """,
                    {
                        "id": record["id"],
                        "process_id": process_id,
                        "asset_key": record["key"],
                        "kind": record["kind"],
                        "title": str(record["title"])[:500],
                        "payload_json": payload_json,
                    },
                )

                for source_id in record["sources"]:
                    cursor.execute(
                        """
                        INSERT INTO CL_ATIVO_INTERACOES (
                            ATIVO_ID, PROCESSAMENTO_ID,
                            INTERACAO_ID, METODO_ORIGEM
                        )
                        VALUES (
                            :asset_id, :process_id,
                            :interaction_id, :method
                        )
                        """,
                        {
                            "asset_id": record["id"],
                            "process_id": process_id,
                            "interaction_id": source_id,
                            "method": (
                                "FONTES_DO_GRAFO"
                                if record["key"] != "newsletter"
                                else "LOTE_COMPLETO"
                            ),
                        },
                    )

                cursor.execute(
                    """
                    INSERT INTO CL_HISTORICO_CURADORIA (
                        ID, ATIVO_ID, PROCESSAMENTO_ID, ACAO,
                        ESTADO_ANTERIOR, NOVO_ESTADO,
                        CONTEUDO_ANTERIOR, CONTEUDO_NOVO,
                        AUTOR, JUSTIFICATIVA, CRIADO_EM,
                        CONSENTIMENTO_ANTERIOR,
                        CONSENTIMENTO_NOVO,
                        REFERENCIA_CONSENTIMENTO
                    )
                    VALUES (
                        :id, :asset_id, :process_id, 'CRIADO',
                        NULL, 'PENDENTE', NULL, :new_payload,
                        'sistema', 'Ativo gerado pelo pipeline.',
                        SYSTIMESTAMP, NULL, 'NAO_APLICAVEL', NULL
                    )
                    """,
                    {
                        "id": str(uuid.uuid4()),
                        "asset_id": record["id"],
                        "process_id": process_id,
                        "new_payload": payload_json,
                    },
                )

            # Alertas de apoio são registros separados dos ativos de marketing.
            for index, analysis in enumerate(analyses):
                if analysis.get("rota") != "alerta":
                    continue

                alert_id = str(uuid.uuid4())
                interaction_id = interaction_ids[index]
                motivo = (
                    f"{analysis.get('sentimento', 'Sentimento não informado')} "
                    f"em {analysis.get('canal', 'canal não informado')}: "
                    f"{analysis.get('texto', '')[:100]}"
                )

                cursor.execute(
                    """
                    INSERT INTO CL_ALERTAS (
                        ID, PROCESSAMENTO_ID, INTERACAO_ID,
                        MOTIVO, STATUS_TRIAGEM, VERSAO,
                        CRIADO_EM, ATUALIZADO_EM
                    )
                    VALUES (
                        :id, :process_id, :interaction_id,
                        :motivo, 'PENDENTE', 1,
                        SYSTIMESTAMP, SYSTIMESTAMP
                    )
                    """,
                    {
                        "id": alert_id,
                        "process_id": process_id,
                        "interaction_id": interaction_id,
                        "motivo": motivo[:1000],
                    },
                )

                cursor.execute(
                    """
                    INSERT INTO CL_HISTORICO_ALERTAS (
                        ID, ALERTA_ID, PROCESSAMENTO_ID, ACAO,
                        ESTADO_ANTERIOR, NOVO_ESTADO,
                        AUTOR, JUSTIFICATIVA, CRIADO_EM
                    )
                    VALUES (
                        :id, :alert_id, :process_id, 'CRIADO',
                        NULL, 'PENDENTE', 'sistema',
                        :justification, SYSTIMESTAMP
                    )
                    """,
                    {
                        "id": str(uuid.uuid4()),
                        "alert_id": alert_id,
                        "process_id": process_id,
                        "justification": motivo[:1000],
                    },
                )

        conn.commit()

    return response


def marcar_erro(
    process_id: str,
    attempt_token: str,
    error_code: str,
    safe_detail: str,
) -> None:
    """Marca falha somente se a tentativa ainda for a proprietária do lote."""
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE CL_PROCESSAMENTOS
                SET STATUS = 'ERRO',
                    ERRO_CODIGO = :code,
                    ERRO_DETALHE = :detail,
                    ATTEMPT_TOKEN = NULL,
                    FINALIZADO_EM = SYSTIMESTAMP,
                    ATUALIZADO_EM = SYSTIMESTAMP
                WHERE ID = :id
                  AND STATUS = 'PROCESSANDO'
                  AND ATTEMPT_TOKEN = :attempt
                """,
                {
                    "code": error_code[:100],
                    "detail": safe_detail[:1000],
                    "id": process_id,
                    "attempt": attempt_token,
                },
            )
        conn.commit()


def atualizar_status_upload(
    process_id: str,
    upload: dict,
) -> None:
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT RESULTADO_JSON
                FROM CL_PROCESSAMENTOS
                WHERE ID = :id
                FOR UPDATE
                """,
                {"id": process_id},
            )
            row = cursor.fetchone()

            if not row:
                raise RecordNotFound(
                    "Lote de processamento não encontrado."
                )

            result = json_loads(row[0]) or {}
            result["armazenamento_oci"] = upload
            _set_clobs(cursor, "result_json")

            cursor.execute(
                """
                UPDATE CL_PROCESSAMENTOS
                SET RESULTADO_JSON = :result_json,
                    OCI_STATUS = :status,
                    OCI_BUCKET = :bucket,
                    OCI_OBJECT_NAME = :object_name,
                    OCI_ETAG = :etag,
                    OCI_ERRO = :error,
                    ATUALIZADO_EM = SYSTIMESTAMP
                WHERE ID = :id
                """,
                {
                    "result_json": json_dumps(result),
                    "status": upload.get("status", "erro").upper(),
                    "bucket": upload.get("bucket") or None,
                    "object_name": upload.get("caminho_objeto") or None,
                    "etag": upload.get("etag"),
                    "error": upload.get("detalhe") or None,
                    "id": process_id,
                },
            )
        conn.commit()


def obter_processamento(
    process_id: str,
) -> dict | None:
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ID, ORIGEM_COMUNIDADE, PERIODO_REFERENCIA,
                       STATUS, MODO_IA, TOTAL_INTERACOES,
                       RESULTADO_JSON, OCI_STATUS, OCI_BUCKET,
                       OCI_OBJECT_NAME, OCI_ETAG, ERRO_CODIGO,
                       ERRO_DETALHE, CRIADO_EM, FINALIZADO_EM
                FROM CL_PROCESSAMENTOS
                WHERE ID = :id
                """,
                {"id": process_id},
            )
            row = cursor.fetchone()

            if not row:
                return None

            result = {
                "id": row[0],
                "origem_comunidade": row[1],
                "periodo_referencia": row[2],
                "status": row[3],
                "modo_ia": row[4],
                "total_interacoes": row[5],
                "resultado": json_loads(row[6]),
                "oci_status": row[7],
                "oci_bucket": row[8],
                "oci_object_name": row[9],
                "oci_etag": row[10],
                "erro_codigo": row[11],
                "erro_detalhe": row[12],
                "criado_em": row[13].isoformat() if row[13] else None,
                "finalizado_em": row[14].isoformat() if row[14] else None,
            }

            cursor.execute(
                """
                SELECT ID, CHAVE_ATIVO, TIPO_ATIVO, TITULO,
                       PAYLOAD_JSON, STATUS_CURADORIA, VERSAO,
                       CONSENTIMENTO_STATUS, CONSENTIMENTO_AUTOR,
                       CONSENTIMENTO_EM, CONSENTIMENTO_REFERENCIA
                FROM CL_ATIVOS
                WHERE PROCESSAMENTO_ID = :id
                ORDER BY CRIADO_EM, CHAVE_ATIVO
                """,
                {"id": process_id},
            )

            result["ativos"] = [
                {
                    "id": asset[0],
                    "chave": asset[1],
                    "tipo": asset[2],
                    "titulo": asset[3],
                    "payload": json_loads(asset[4]),
                    "status_curadoria": asset[5],
                    "versao": asset[6],
                    "consentimento_status": asset[7],
                    "consentimento_autor": asset[8],
                    "consentimento_em": (
                        asset[9].isoformat() if asset[9] else None
                    ),
                    "consentimento_referencia": asset[10],
                }
                for asset in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT a.ID, a.INTERACAO_ID, i.AUTOR, i.CANAL,
                       i.TEXTO, a.MOTIVO, a.STATUS_TRIAGEM,
                       a.VERSAO, a.ACAO, a.RESPONSAVEL,
                       a.JUSTIFICATIVA
                FROM CL_ALERTAS a
                JOIN CL_INTERACOES i ON i.ID = a.INTERACAO_ID
                WHERE a.PROCESSAMENTO_ID = :id
                ORDER BY i.POSICAO
                """,
                {"id": process_id},
            )

            result["alertas"] = [
                {
                    "id": item[0],
                    "interacao_id": item[1],
                    "autor": item[2],
                    "canal": item[3],
                    "texto": _text_value(item[4]),
                    "motivo": item[5],
                    "status": item[6],
                    "versao": int(item[7]),
                    "acao": item[8],
                    "responsavel": item[9],
                    "justificativa": item[10],
                }
                for item in cursor.fetchall()
            ]

            return result



def listar_processamentos(
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ID, ORIGEM_COMUNIDADE, PERIODO_REFERENCIA,
                       STATUS, MODO_IA, TOTAL_INTERACOES,
                       OCI_STATUS, CRIADO_EM, FINALIZADO_EM
                FROM CL_PROCESSAMENTOS
                ORDER BY CRIADO_EM DESC
                OFFSET :offset ROWS FETCH NEXT :lim ROWS ONLY
                """,
                {"offset": offset, "lim": limit},
            )

            return [
                {
                    "id": item[0],
                    "origem_comunidade": item[1],
                    "periodo_referencia": item[2],
                    "status": item[3],
                    "modo_ia": item[4],
                    "total_interacoes": item[5],
                    "oci_status": item[6],
                    "criado_em": (
                        item[7].isoformat() if item[7] else None
                    ),
                    "finalizado_em": (
                        item[8].isoformat() if item[8] else None
                    ),
                }
                for item in cursor.fetchall()
            ]


# Campos permitidos para edição de cada tipo de ativo.
_ALLOWED_FIELDS = {
    "POST_LINKEDIN": {"titulo", "copy"},
    "NEWSLETTER": {"secao", "chamada", "resumo"},
    "FAQ": {"tema", "conteudo", "origem"},
}



def atualizar_curadoria(
    asset_id: str,
    status: str,
    patch: dict | None,
    actor: str,
    versao_esperada: int,
    consentimento: bool | None = None,
    justificativa: str | None = None,
    referencia_consentimento: str | None = None,
) -> dict:
    allowed_status = {"PENDENTE", "APROVADO", "DESCARTADO"}

    if status not in allowed_status:
        raise InvalidCuration("Estado de curadoria inválido.")

    patch = patch or {}
    actor = (actor or "usuario-local").strip()[:255]

    if any(ord(char) < 32 or ord(char) == 127 for char in actor):
        raise InvalidCuration(
            "A identificação do responsável contém caracteres de controle inválidos."
        )

    justification = (justificativa or "").strip()[:2000] or None

    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ID, PROCESSAMENTO_ID, CHAVE_ATIVO,
                       TIPO_ATIVO, PAYLOAD_JSON,
                       STATUS_CURADORIA, VERSAO,
                       CONSENTIMENTO_STATUS,
                       CONSENTIMENTO_REFERENCIA
                FROM CL_ATIVOS
                WHERE ID = :id
                FOR UPDATE
                """,
                {"id": asset_id},
            )
            row = cursor.fetchone()

            if not row:
                raise RecordNotFound("Ativo não encontrado.")

            (
                _id,
                process_id,
                key,
                kind,
                old_payload_raw,
                old_status,
                version,
                old_consent,
                old_ref,
            ) = row

            if kind not in _ALLOWED_FIELDS:
                raise InvalidCuration(
                    "Este tipo de ativo não pode ser curado por este endpoint."
                )

            invalid = set(patch) - _ALLOWED_FIELDS[kind]
            if invalid:
                raise InvalidCuration(
                    "Campos não permitidos para este tipo de ativo: "
                    + ", ".join(sorted(invalid))
                )

            old_payload = json_loads(old_payload_raw) or {}
            new_payload = dict(old_payload)

            for field, value in patch.items():
                if not isinstance(value, str) or not value.strip():
                    raise InvalidCuration(
                        f"O campo '{field}' não pode ficar vazio."
                    )

                max_length = (
                    20000
                    if field in {"copy", "conteudo", "resumo"}
                    else 500
                )
                if len(value) > max_length:
                    raise InvalidCuration(
                        f"O campo '{field}' excede {max_length} caracteres."
                    )

                new_payload[field] = value.strip()

            consent_status = old_consent
            consent_reference = old_ref

            if kind == "POST_LINKEDIN" and consentimento is True:
                candidate_ref = (
                    referencia_consentimento or old_ref or ""
                ).strip()

                if not candidate_ref:
                    raise InvalidCuration(
                        "Informe a referência do registro de autorização "
                        "do membro antes de confirmar o consentimento."
                    )

                if len(candidate_ref) > 500:
                    raise InvalidCuration(
                        "A referência de autorização não pode exceder 500 caracteres."
                    )

                consent_status = "CONFIRMADO"
                consent_reference = candidate_ref

            elif kind == "POST_LINKEDIN" and consentimento is False:
                consent_status = "REVOGADO"
                consent_reference = None

            if (
                kind == "POST_LINKEDIN"
                and status == "APROVADO"
                and (
                    consent_status != "CONFIRMADO"
                    or not consent_reference
                )
            ):
                raise InvalidCuration(
                    "A aprovação do post exige autorização documentada "
                    "com uma referência registrada."
                )

            unchanged = (
                old_status == status
                and old_payload == new_payload
                and old_consent == consent_status
                and old_ref == consent_reference
            )

            if int(version) != int(versao_esperada) and not unchanged:
                raise VersionConflict(
                    "O ativo foi alterado por outra operação. "
                    "Atualize a tela e tente novamente."
                )

            if unchanged:
                return {
                    "id": asset_id,
                    "chave": key,
                    "status_curadoria": old_status,
                    "payload": old_payload,
                    "versao": int(version),
                    "consentimento_status": old_consent,
                    "consentimento_referencia": old_ref,
                }

            new_version = int(version) + 1
            new_json = json_dumps(new_payload)

            import oracledb

            
def finalizar_processamento(
    process_id: str,
    response: dict,
    interaction_ids: list[str],
    attempt_token: str,
    object_name: str,
) -> dict:
    """Grava análises, ativos, fontes e alertas atomicamente."""
    response = dict(response)
    raw_analyses = response.get("analises") or []

    if len(raw_analyses) != len(interaction_ids):
        raise ValueError(
            "O número de análises difere do número de interações persistidas."
        )

    response["analises"] = [
        dict(analysis, interacao_id=interaction_ids[index])
        for index, analysis in enumerate(raw_analyses)
    ]

    analyses = response["analises"]

    records, asset_ids = _asset_records(
        response,
        process_id,
        interaction_ids,
    )

    response["processamento_id"] = process_id
    response["ids_ativos"] = asset_ids
    response["persistencia"] = "oracle"
    response.setdefault("armazenamento_oci", {})

    storage_mode = os.getenv(
        "OCI_STORAGE_MODE", "local"
    ).strip().lower()

    # Importação explícita para permitir a utilização do OCI Storage.
    from . import storage

    storage_bucket = (
        storage.bucket_name()
        if storage_mode in {"oci", "required"}
        else "local"
    )

    response["armazenamento_oci"].update({
        "status": "pendente",
        "bucket": storage_bucket or "",
        "caminho_objeto": object_name,
        "sha256": None,
        "etag": None,
        "detalhe": None,
    })

    result_json = json_dumps(response)

    with database.connection() as conn:
        with conn.cursor() as cursor:

            # 1. Confirma que esta tentativa ainda é proprietária do lote.
            cursor.execute(
                """
                SELECT STATUS, ATTEMPT_TOKEN
                FROM CL_PROCESSAMENTOS
                WHERE ID = :id
                FOR UPDATE
                """,
                {"id": process_id},
            )

            row = cursor.fetchone()

            if not row:
                raise RecordNotFound(
                    "Lote de processamento não encontrado."
                )

            if row[0] != "PROCESSANDO" or row[1] != attempt_token:
                raise AttemptSuperseded(
                    "Esta tentativa foi substituída por uma execução mais recente."
                )

            # 2. Recupera e bloqueia as interações de origem.
            cursor.execute(
                """
                SELECT ID, AUTOR, CANAL, TEXTO
                FROM CL_INTERACOES
                WHERE PROCESSAMENTO_ID = :id
                ORDER BY POSICAO
                FOR UPDATE
                """,
                {"id": process_id},
            )

            source_rows = cursor.fetchall()

            if [item[0] for item in source_rows] != interaction_ids:
                raise ValueError(
                    "As interações foram alteradas ou reordenadas."
                )

            # 3. Valida a correspondência entre análises e fontes.
            for source_row, analysis in zip(
                source_rows,
                analyses,
                strict=True,
            ):
                if (
                    analysis.get("autor") != source_row[1]
                    or analysis.get("canal") != source_row[2]
                    or analysis.get("texto") != _text_value(source_row[3])
                ):
                    raise ValueError(
                        "Uma análise não corresponde exatamente "
                        "à interação de origem persistida."
                    )

            # 4. Impede a duplicação de ativos.
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM CL_ATIVOS
                WHERE PROCESSAMENTO_ID = :id
                """,
                {"id": process_id},
            )

            if int(cursor.fetchone()[0]) > 0:
                raise RuntimeError(
                    "O processamento já possui ativos persistidos; "
                    "a gravação duplicada foi recusada."
                )

            import oracledb

            # 5. Persiste as análises usando cursor exclusivo.
            # O cursor não será reutilizado para outros CLOBs.
            with conn.cursor() as analysis_cursor:
                analysis_cursor.setinputsizes(
                    analysis_json=oracledb.DB_TYPE_CLOB
                )

                for index, interaction_id in enumerate(interaction_ids):
                    analysis_cursor.execute(
                        """
                        UPDATE CL_INTERACOES
                        SET ANALISE_JSON = :analysis_json
                        WHERE ID = :id
                          AND PROCESSAMENTO_ID = :process_id
                        """,
                        {
                            "analysis_json": json_dumps(analyses[index]),
                            "id": interaction_id,
                            "process_id": process_id,
                        },
                    )

                    if analysis_cursor.rowcount != 1:
                        raise RuntimeError(
                            "Interação de origem não localizada "
                            "durante a persistência."
                        )

            # 6. Atualiza o processamento usando outro cursor exclusivo.
            with conn.cursor() as result_cursor:
                result_cursor.setinputsizes(
                    result_json=oracledb.DB_TYPE_CLOB
                )

                result_cursor.execute(
                    """
                    UPDATE CL_PROCESSAMENTOS
                    SET STATUS = 'SUCESSO',
                        RESULTADO_JSON = :result_json,
                        OCI_STATUS = 'PENDENTE',
                        OCI_BUCKET = :bucket,
                        OCI_OBJECT_NAME = :object_name,
                        OCI_ETAG = NULL,
                        OCI_ERRO = NULL,
                        ERRO_CODIGO = NULL,
                        ERRO_DETALHE = NULL,
                        ATTEMPT_TOKEN = NULL,
                        FINALIZADO_EM = SYSTIMESTAMP,
                        ATUALIZADO_EM = SYSTIMESTAMP
                    WHERE ID = :id
                      AND STATUS = 'PROCESSANDO'
                      AND ATTEMPT_TOKEN = :attempt
                    """,
                    {
                        "result_json": result_json,
                        "bucket": storage_bucket,
                        "object_name": object_name,
                        "id": process_id,
                        "attempt": attempt_token,
                    },
                )

                if result_cursor.rowcount != 1:
                    raise AttemptSuperseded(
                        "A execução perdeu a posse do processamento "
                        "antes do commit."
                    )

            # 7. Persiste os ativos e seus relacionamentos.
            # Um cursor exclusivo recebe somente o bind payload_json.
            with conn.cursor() as asset_cursor:
                asset_cursor.setinputsizes(
                    payload_json=oracledb.DB_TYPE_CLOB
                )

                # Outro cursor exclusivo recebe somente new_payload.
                with conn.cursor() as history_cursor:
                    history_cursor.setinputsizes(
                        new_payload=oracledb.DB_TYPE_CLOB
                    )

                    for record in records:
                        payload_json = json_dumps(record["payload"])

                        # 7.1. Insere o ativo.
                        asset_cursor.execute(
                            """
                            INSERT INTO CL_ATIVOS (
                                ID, PROCESSAMENTO_ID, CHAVE_ATIVO,
                                TIPO_ATIVO, TITULO, PAYLOAD_JSON,
                                STATUS_CURADORIA, VERSAO,
                                CONSENTIMENTO_STATUS,
                                CRIADO_EM, ATUALIZADO_EM
                            )
                            VALUES (
                                :id, :process_id, :asset_key,
                                :kind, :title, :payload_json,
                                'PENDENTE', 1, 'NAO_APLICAVEL',
                                SYSTIMESTAMP, SYSTIMESTAMP
                            )
                            """,
                            {
                                "id": record["id"],
                                "process_id": process_id,
                                "asset_key": record["key"],
                                "kind": record["kind"],
                                "title": str(record["title"])[:500],
                                "payload_json": payload_json,
                            },
                        )

                        # 7.2. Registra as fontes de cada ativo.
                        for source_id in record["sources"]:
                            cursor.execute(
                                """
                                INSERT INTO CL_ATIVO_INTERACOES (
                                    ATIVO_ID, PROCESSAMENTO_ID,
                                    INTERACAO_ID, METODO_ORIGEM
                                )
                                VALUES (
                                    :asset_id, :process_id,
                                    :interaction_id, :method
                                )
                                """,
                                {
                                    "asset_id": record["id"],
                                    "process_id": process_id,
                                    "interaction_id": source_id,
                                    "method": (
                                        "FONTES_DO_GRAFO"
                                        if record["key"] != "newsletter"
                                        else "LOTE_COMPLETO"
                                    ),
                                },
                            )

                        # 7.3. Cria o histórico inicial de curadoria.
                        history_cursor.execute(
                            """
                            INSERT INTO CL_HISTORICO_CURADORIA (
                                ID, ATIVO_ID, PROCESSAMENTO_ID, ACAO,
                                ESTADO_ANTERIOR, NOVO_ESTADO,
                                CONTEUDO_ANTERIOR, CONTEUDO_NOVO,
                                AUTOR, JUSTIFICATIVA, CRIADO_EM,
                                CONSENTIMENTO_ANTERIOR,
                                CONSENTIMENTO_NOVO,
                                REFERENCIA_CONSENTIMENTO
                            )
                            VALUES (
                                :id, :asset_id, :process_id, 'CRIADO',
                                NULL, 'PENDENTE', NULL, :new_payload,
                                'sistema',
                                'Ativo gerado pelo pipeline.',
                                SYSTIMESTAMP, NULL,
                                'NAO_APLICAVEL', NULL
                            )
                            """,
                            {
                                "id": str(uuid.uuid4()),
                                "asset_id": record["id"],
                                "process_id": process_id,
                                "new_payload": payload_json,
                            },
                        )

            # 8. Registra os alertas encontrados nas análises.
            # Estes comandos não utilizam binds CLOB.
            for index, analysis in enumerate(analyses):
                if analysis.get("rota") != "alerta":
                    continue

                alert_id = str(uuid.uuid4())
                interaction_id = interaction_ids[index]

                motivo = (
                    f"{analysis.get('sentimento', 'Sentimento não informado')} "
                    f"em {analysis.get('canal', 'canal não informado')}: "
                    f"{analysis.get('texto', '')[:100]}"
                )

                cursor.execute(
                    """
                    INSERT INTO CL_ALERTAS (
                        ID, PROCESSAMENTO_ID, INTERACAO_ID,
                        MOTIVO, STATUS_TRIAGEM, VERSAO,
                        CRIADO_EM, ATUALIZADO_EM
                    )
                    VALUES (
                        :id, :process_id, :interaction_id,
                        :motivo, 'PENDENTE', 1,
                        SYSTIMESTAMP, SYSTIMESTAMP
                    )
                    """,
                    {
                        "id": alert_id,
                        "process_id": process_id,
                        "interaction_id": interaction_id,
                        "motivo": motivo[:1000],
                    },
                )

                cursor.execute(
                    """
                    INSERT INTO CL_HISTORICO_ALERTAS (
                        ID, ALERTA_ID, PROCESSAMENTO_ID, ACAO,
                        ESTADO_ANTERIOR, NOVO_ESTADO,
                        AUTOR, JUSTIFICATIVA, CRIADO_EM
                    )
                    VALUES (
                        :id, :alert_id, :process_id, 'CRIADO',
                        NULL, 'PENDENTE', 'sistema',
                        :justification, SYSTIMESTAMP
                    )
                    """,
                    {
                        "id": str(uuid.uuid4()),
                        "alert_id": alert_id,
                        "process_id": process_id,
                        "justification": motivo[:1000],
                    },
                )

        # 9. Confirma todas as gravações em uma única transação.
        conn.commit()

    return response



def atualizar_alerta(
    alert_id: str,
    status: str,
    actor: str,
    versao_esperada: int,
    acao: str | None = None,
    justificativa: str | None = None,
) -> dict:
    allowed = {"PENDENTE", "ENCAMINHADO", "RESOLVIDO"}

    if status not in allowed:
        raise InvalidCuration("Estado de triagem do alerta inválido.")

    actor = (actor or "usuario-local").strip()[:255]
    if any(ord(char) < 32 or ord(char) == 127 for char in actor):
        raise InvalidCuration(
            "A identificação do responsável contém caracteres de controle inválidos."
        )

    acao = (acao or status.title()).strip()[:300]
    justificativa = (justificativa or "").strip()[:2000] or None

    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ID, PROCESSAMENTO_ID, STATUS_TRIAGEM,
                       VERSAO, ACAO, RESPONSAVEL, JUSTIFICATIVA
                FROM CL_ALERTAS
                WHERE ID = :id
                FOR UPDATE
                """,
                {"id": alert_id},
            )
            row = cursor.fetchone()

            if not row:
                raise RecordNotFound("Alerta não encontrado.")

            (
                _id,
                process_id,
                old_status,
                version,
                old_action,
                old_actor,
                old_justification,
            ) = row

            unchanged = (
                old_status == status
                and old_action == acao
                and old_justification == justificativa
                and old_actor == actor
            )

            if int(version) != int(versao_esperada) and not unchanged:
                raise VersionConflict(
                    "O alerta foi alterado por outra operação. "
                    "Atualize a tela e tente novamente."
                )

            if unchanged:
                return {
                    "id": alert_id,
                    "status": old_status,
                    "versao": int(version),
                    "acao": old_action,
                }

            new_version = int(version) + 1

            cursor.execute(
                """
                UPDATE CL_ALERTAS
                SET STATUS_TRIAGEM = :status,
                    VERSAO = :version,
                    ACAO = :action,
                    RESPONSAVEL = :actor,
                    JUSTIFICATIVA = :justification,
                    ATUALIZADO_EM = SYSTIMESTAMP
                WHERE ID = :id
                """,
                {
                    "status": status,
                    "version": new_version,
                    "action": acao,
                    "actor": actor,
                    "justification": justificativa,
                    "id": alert_id,
                },
            )

            cursor.execute(
                """
                INSERT INTO CL_HISTORICO_ALERTAS (
                    ID, ALERTA_ID, PROCESSAMENTO_ID, ACAO,
                    ESTADO_ANTERIOR, NOVO_ESTADO,
                    AUTOR, JUSTIFICATIVA, CRIADO_EM
                )
                VALUES (
                    :id, :alert_id, :process_id, :action,
                    :old_status, :new_status,
                    :actor, :justification, SYSTIMESTAMP
                )
                """,
                {
                    "id": str(uuid.uuid4()),
                    "alert_id": alert_id,
                    "process_id": process_id,
                    "action": acao,
                    "old_status": old_status,
                    "new_status": status,
                    "actor": actor,
                    "justification": justificativa,
                },
            )

        conn.commit()

    return {
        "id": alert_id,
        "status": status,
        "versao": new_version,
        "acao": acao,
    }


def historico_alerta(
    alert_id: str,
) -> list[dict] | None:
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM CL_ALERTAS WHERE ID = :id",
                {"id": alert_id},
            )
            if not cursor.fetchone():
                return None

            cursor.execute(
                """
                SELECT ACAO, ESTADO_ANTERIOR, NOVO_ESTADO,
                       AUTOR, JUSTIFICATIVA, CRIADO_EM
                FROM CL_HISTORICO_ALERTAS
                WHERE ALERTA_ID = :id
                ORDER BY CRIADO_EM, ID
                """,
                {"id": alert_id},
            )

            return [
                {
                    "acao": row[0],
                    "estado_anterior": row[1],
                    "novo_estado": row[2],
                    "autor": row[3],
                    "justificativa": row[4],
                    "criado_em": row[5].isoformat() if row[5] else None,
                }
                for row in cursor.fetchall()
            ]


def definir_objeto_exportacao(
    export_id: str,
    object_name: str,
    bucket: str | None,
) -> str:
    """Fixe o destino da exportação para não alternar bucket em retentativas."""
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT STATUS, OCI_OBJECT_NAME, OCI_BUCKET
                FROM CL_EXPORTACOES
                WHERE ID = :id
                FOR UPDATE
                """,
                {"id": export_id},
            )
            row = cursor.fetchone()

            if not row:
                raise RecordNotFound("Exportação não encontrada.")

            status, saved_name, saved_bucket = row

            if status == "ENVIADO":
                return saved_name or object_name

            if (
                saved_name
                and saved_bucket
                and bucket
                and saved_bucket != bucket
            ):
                raise InvalidCuration(
                    "O destino OCI desta exportação mudou desde "
                    "a primeira tentativa. Restaure o bucket original "
                    "ou crie uma nova exportação; nenhum upload foi feito."
                )

            stable_name = saved_name or object_name
            stable_bucket = saved_bucket or bucket

            cursor.execute(
                """
                UPDATE CL_EXPORTACOES
                SET OCI_OBJECT_NAME = :object_name,
                    OCI_BUCKET = :bucket,
                    ATUALIZADO_EM = SYSTIMESTAMP
                WHERE ID = :id
                """,
                {
                    "object_name": stable_name,
                    "bucket": stable_bucket,
                    "id": export_id,
                },
            )

        conn.commit()

    return stable_name


def historico_ativo(
    asset_id: str,
) -> list[dict] | None:
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM CL_ATIVOS WHERE ID = :id",
                {"id": asset_id},
            )
            if not cursor.fetchone():
                return None

            cursor.execute(
                """
                SELECT ACAO, ESTADO_ANTERIOR, NOVO_ESTADO,
                       CONTEUDO_ANTERIOR, CONTEUDO_NOVO,
                       AUTOR, JUSTIFICATIVA, CRIADO_EM,
                       CONSENTIMENTO_ANTERIOR,
                       CONSENTIMENTO_NOVO,
                       REFERENCIA_CONSENTIMENTO
                FROM CL_HISTORICO_CURADORIA
                WHERE ATIVO_ID = :id
                ORDER BY CRIADO_EM, ID
                """,
                {"id": asset_id},
            )

            return [
                {
                    "acao": row[0],
                    "estado_anterior": row[1],
                    "novo_estado": row[2],
                    "conteudo_anterior": json_loads(row[3]),
                    "conteudo_novo": json_loads(row[4]),
                    "autor": row[5],
                    "justificativa": row[6],
                    "criado_em": row[7].isoformat() if row[7] else None,
                    "consentimento_anterior": row[8],
                    "consentimento_novo": row[9],
                    "referencia_consentimento": row[10],
                }
                for row in cursor.fetchall()
            ]
def criar_exportacao(
    process_id: str,
    actor: str,
    idempotency_key: str | None = None,
) -> dict:
    """Gera um pacote versionado com os ativos aprovados."""
    export_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ORIGEM_COMUNIDADE,
                       PERIODO_REFERENCIA, STATUS
                FROM CL_PROCESSAMENTOS
                WHERE ID = :id
                """,
                {"id": process_id},
            )
            proc = cursor.fetchone()

            if not proc:
                raise RecordNotFound(
                    "Lote de processamento não encontrado."
                )

            if proc[2] != "SUCESSO":
                raise InvalidCuration(
                    "Só é possível exportar um processamento concluído com sucesso."
                )

            origin, period = proc[0], proc[1]

            cursor.execute(
                """
                SELECT ID, CHAVE_ATIVO, TIPO_ATIVO,
                       PAYLOAD_JSON, STATUS_CURADORIA,
                       CONSENTIMENTO_STATUS, VERSAO,
                       CONSENTIMENTO_REFERENCIA,
                       CONSENTIMENTO_AUTOR
                FROM CL_ATIVOS
                WHERE PROCESSAMENTO_ID = :id
                ORDER BY CHAVE_ATIVO
                FOR UPDATE
                """,
                {"id": process_id},
            )
            rows = cursor.fetchall()

            package = {
                "origem_comunidade": origin,
                "periodo_referencia": period,
                "aprovado_em": now,
                "processamento_id": process_id,
                "post_linkedin": None,
                "destaque_newsletter_semanal": None,
                "sugestao_conteudo_faq": [],
                "descartados": [],
            }

            for (
                asset_id,
                key,
                kind,
                payload_raw,
                state,
                consent,
                version,
                consent_ref,
                consent_actor,
            ) in rows:
                if state == "DESCARTADO":
                    package["descartados"].append(key)
                    continue

                if state != "APROVADO":
                    continue

                payload = json_loads(payload_raw) or {}

                if kind == "POST_LINKEDIN":
                    if consent != "CONFIRMADO" or not consent_ref:
                        raise InvalidCuration(
                            "O post aprovado não possui autorização "
                            "documentada com referência."
                        )

                    cursor.execute(
                        """
                        SELECT i.AUTOR
                        FROM CL_ATIVO_INTERACOES ai
                        JOIN CL_INTERACOES i
                          ON i.ID = ai.INTERACAO_ID
                        WHERE ai.ATIVO_ID = :asset_id
                        ORDER BY i.POSICAO
                        FETCH FIRST 1 ROWS ONLY
                        """,
                        {"asset_id": asset_id},
                    )
                    source = cursor.fetchone()

                    payload["membro"] = (
                        source[0] if source else None
                    )
                    payload["autorizacao_membro"] = True
                    payload["referencia_autorizacao"] = consent_ref
                    payload["autorizacao_registrada_por"] = consent_actor

                    package["post_linkedin"] = payload

                elif kind == "NEWSLETTER":
                    package[
                        "destaque_newsletter_semanal"
                    ] = payload

                elif kind == "FAQ":
                    package[
                        "sugestao_conteudo_faq"
                    ].append(payload)

            # A data de exportação não deve alterar o hash idempotente.
            hash_payload = dict(package)
            hash_payload.pop("aprovado_em", None)
            request_hash = fingerprint_request(hash_payload)

            if idempotency_key:
                cursor.execute(
                    """
                    SELECT ID, PROCESSAMENTO_ID,
                           REQUEST_SHA256, STATUS, PAYLOAD_JSON
                    FROM CL_EXPORTACOES
                    WHERE IDEMPOTENCY_KEY = :key
                    """,
                    {"key": idempotency_key},
                )
                existing = cursor.fetchone()

                if existing:
                    if (
                        existing[1] != process_id
                        or existing[2] != request_hash
                    ):
                        raise IdempotencyConflict(
                            "A chave de idempotência da exportação "
                            "foi usada com conteúdo diferente."
                        )

                    return {
                        "id": existing[0],
                        "processamento_id": existing[1],
                        "pacote": json_loads(existing[4]),
                        "status": existing[3].lower(),
                        "actor": actor,
                        "existing": True,
                    }

            package_json = json_dumps(package)
            _set_clobs(cursor, "payload_json")

            try:
                cursor.execute(
                    """
                    INSERT INTO CL_EXPORTACOES (
                        ID, PROCESSAMENTO_ID, IDEMPOTENCY_KEY,
                        REQUEST_SHA256, STATUS, PAYLOAD_JSON,
                        CRIADO_POR, CRIADO_EM
                    )
                    VALUES (
                        :id, :process_id, :ikey, :request_hash,
                        'PENDENTE', :payload_json,
                        :actor, SYSTIMESTAMP
                    )
                    """,
                    {
                        "id": export_id,
                        "process_id": process_id,
                        "ikey": idempotency_key,
                        "request_hash": request_hash,
                        "payload_json": package_json,
                        "actor": actor[:255],
                    },
                )

            except Exception as exc:
                conn.rollback()

                # Recupera uma exportação criada em paralelo com a mesma chave.
                if idempotency_key:
                    with conn.cursor() as retry_cursor:
                        retry_cursor.execute(
                            """
                            SELECT ID, PROCESSAMENTO_ID,
                                   REQUEST_SHA256, STATUS, PAYLOAD_JSON
                            FROM CL_EXPORTACOES
                            WHERE IDEMPOTENCY_KEY = :key
                            """,
                            {"key": idempotency_key},
                        )
                        existing = retry_cursor.fetchone()

                        if existing:
                            if (
                                existing[1] != process_id
                                or existing[2] != request_hash
                            ):
                                raise IdempotencyConflict(
                                    "A chave de idempotência da exportação "
                                    "foi usada com conteúdo diferente."
                                ) from exc

                            return {
                                "id": existing[0],
                                "processamento_id": existing[1],
                                "pacote": json_loads(existing[4]),
                                "status": existing[3].lower(),
                                "actor": actor,
                                "existing": True,
                            }

                raise

        conn.commit()

    return {
        "id": export_id,
        "processamento_id": process_id,
        "pacote": package,
        "status": "pendente",
        "actor": actor,
        "existing": False,
    }


def obter_exportacao(
    export_id: str,
) -> dict | None:
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ID, PROCESSAMENTO_ID, STATUS,
                       PAYLOAD_JSON, OCI_BUCKET,
                       OCI_OBJECT_NAME, OCI_ETAG,
                       OCI_ERRO, CRIADO_EM, CRIADO_POR
                FROM CL_EXPORTACOES
                WHERE ID = :id
                """,
                {"id": export_id},
            )
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "processamento_id": row[1],
                "status": row[2],
                "pacote": json_loads(row[3]),
                "bucket": row[4],
                "caminho_objeto": row[5],
                "etag": row[6],
                "erro": row[7],
                "criado_em": row[8].isoformat() if row[8] else None,
                "criado_por": row[9],
            }


def atualizar_exportacao_upload(
    export_id: str,
    upload: dict,
) -> None:
    """Registra o resultado do upload sem ocultar falhas."""
    if upload.get("status") == "salvo_com_sucesso":
        status = "ENVIADO"
    elif upload.get("status") == "salvo_localmente":
        status = "LOCAL"
    else:
        status = "FALHOU"

    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE CL_EXPORTACOES
                SET STATUS = :status,
                    OCI_BUCKET = :bucket,
                    OCI_OBJECT_NAME = :object_name,
                    OCI_ETAG = :etag,
                    OCI_ERRO = :error,
                    ATUALIZADO_EM = SYSTIMESTAMP
                WHERE ID = :id
                """,
                {
                    "status": status,
                    "bucket": upload.get("bucket") or None,
                    "object_name": (
                        upload.get("caminho_objeto") or None
                    ),
                    "etag": upload.get("etag"),
                    "error": upload.get("detalhe") or None,
                    "id": export_id,
                },
            )

            if cursor.rowcount != 1:
                raise RecordNotFound(
                    "Exportação não encontrada para atualização."
                )

        conn.commit()
# ---------------------------------------------------------------------------
# Insights: consultas históricas no Oracle
# ---------------------------------------------------------------------------

def _filtro_lista_sql(
    coluna: str,
    valores: list[str] | None,
    prefixo: str,
    params: dict,
) -> str:
    """Gera filtro IN com binds individuais, sem interpolar valores no SQL."""
    valores_unicos = list(dict.fromkeys(
        str(valor).strip()
        for valor in (valores or [])
        if str(valor).strip()
    ))

    if not valores_unicos:
        return ""

    placeholders = []

    for indice, valor in enumerate(valores_unicos):
        nome = f"{prefixo}_{indice}"
        placeholders.append(f":{nome}")
        params[nome] = valor

    return f"{coluna} IN ({', '.join(placeholders)})"


def _contexto_filtros_insights(
    modo: str,
    comunidades: list[str] | None,
    canais: list[str] | None,
    params: dict,
) -> list[str]:
    """Monta os filtros comuns de modo, comunidade e canal."""
    if modo not in {"mock", "gemini"}:
        raise ValueError("Modo de IA inválido.")

    condicoes = [
        "p.STATUS = 'SUCESSO'",
        "p.MODO_IA = :modo",
    ]

    params["modo"] = modo

    comunidade_sql = _filtro_lista_sql(
        "p.ORIGEM_COMUNIDADE",
        comunidades,
        "comunidade",
        params,
    )

    if comunidade_sql:
        condicoes.append(comunidade_sql)

    canal_sql = _filtro_lista_sql(
        "i.CANAL",
        canais,
        "canal",
        params,
    )

    if canal_sql:
        condicoes.append(canal_sql)

    return condicoes


def opcoes_filtros_insights(modo: str) -> dict:
    """Retorna comunidades e canais disponíveis para o modo selecionado."""
    if modo not in {"mock", "gemini"}:
        raise ValueError("Modo de IA inválido.")

    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT ORIGEM_COMUNIDADE
                FROM CL_PROCESSAMENTOS
                WHERE STATUS = 'SUCESSO'
                  AND MODO_IA = :modo
                ORDER BY ORIGEM_COMUNIDADE
                """,
                {"modo": modo},
            )

            comunidades = [
                row[0] for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT DISTINCT i.CANAL
                FROM CL_INTERACOES i
                JOIN CL_PROCESSAMENTOS p
                  ON p.ID = i.PROCESSAMENTO_ID
                WHERE p.STATUS = 'SUCESSO'
                  AND p.MODO_IA = :modo
                  AND i.DATA_INTERACAO IS NOT NULL
                  AND i.ANALISE_JSON IS NOT NULL
                ORDER BY i.CANAL
                """,
                {"modo": modo},
            )

            canais = [
                row[0] for row in cursor.fetchall()
            ]

    return {
        "comunidades": comunidades,
        "canais": canais,
    }


def consultar_interacoes_insights(
    inicio: date,
    fim: date,
    modo: str,
    comunidades: list[str] | None = None,
    canais: list[str] | None = None,
) -> list[dict]:
    """
    Consulta interações analisadas pela data original da mensagem.

    O intervalo é inclusivo: início até fim, inclusive.
    A análise é extraída do JSON persistido em ANALISE_JSON.
    """
    if inicio > fim:
        raise ValueError("A data inicial não pode ser posterior à final.")

    params = {
        "inicio": inicio,
        "fim_exclusivo": fim + timedelta(days=1),
    }

    condicoes = _contexto_filtros_insights(
        modo,
        comunidades,
        canais,
        params,
    )

    condicoes.extend([
        "i.DATA_INTERACAO >= :inicio",
        "i.DATA_INTERACAO < :fim_exclusivo",
        "i.ANALISE_JSON IS NOT NULL",
    ])

    sql = f"""
        SELECT
            p.ID AS LOTE_ID,
            i.DATA_INTERACAO AS DATA,
            p.ORIGEM_COMUNIDADE AS COMUNIDADE,
            i.CANAL AS CANAL,
            JSON_VALUE(
                i.ANALISE_JSON,
                '$.sentimento'
                RETURNING VARCHAR2(80)
                NULL ON ERROR
            ) AS SENTIMENTO,
            JSON_VALUE(
                i.ANALISE_JSON,
                '$.topico'
                RETURNING VARCHAR2(300)
                NULL ON ERROR
            ) AS TOPICO,
            JSON_VALUE(
                i.ANALISE_JSON,
                '$.rota'
                RETURNING VARCHAR2(80)
                NULL ON ERROR
            ) AS ROTA
        FROM CL_INTERACOES i
        JOIN CL_PROCESSAMENTOS p
          ON p.ID = i.PROCESSAMENTO_ID
        WHERE {' AND '.join(condicoes)}
        ORDER BY
            i.DATA_INTERACAO,
            p.ID,
            i.POSICAO
    """

    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)

            return [
                {
                    "lote_id": row[0],
                    "data": row[1],
                    "comunidade": row[2],
                    "canal": row[3],
                    "sentimento": row[4],
                    "topico": row[5],
                    "rota": row[6],
                }
                for row in cursor.fetchall()
            ]


def consultar_ativos_insights(
    inicio: date,
    fim: date,
    modo: str,
    comunidades: list[str] | None = None,
    canais: list[str] | None = None,
) -> list[dict]:
    """
    Consulta ativos vinculados às interações do período.

    EXISTS evita contar várias vezes um mesmo ativo que tenha
    mais de uma interação de origem, como uma newsletter.
    """
    if inicio > fim:
        raise ValueError("A data inicial não pode ser posterior à final.")

    params = {
        "inicio": inicio,
        "fim_exclusivo": fim + timedelta(days=1),
    }

    condicoes = _contexto_filtros_insights(
        modo,
        comunidades,
        None,
        params,
    )

    fontes = [
        "ai.ATIVO_ID = a.ID",
        "i.ID = ai.INTERACAO_ID",
        "i.DATA_INTERACAO >= :inicio",
        "i.DATA_INTERACAO < :fim_exclusivo",
    ]

    canal_sql = _filtro_lista_sql(
        "i.CANAL",
        canais,
        "canal",
        params,
    )

    if canal_sql:
        fontes.append(canal_sql)

    condicoes.append(
        """
        EXISTS (
            SELECT 1
            FROM CL_ATIVO_INTERACOES ai
            JOIN CL_INTERACOES i
              ON i.ID = ai.INTERACAO_ID
            WHERE """ + " AND ".join(fontes) + """
        )
        """
    )

    sql = f"""
        SELECT
            a.PROCESSAMENTO_ID,
            a.CHAVE_ATIVO,
            a.TIPO_ATIVO,
            LOWER(a.STATUS_CURADORIA) AS STATUS
        FROM CL_ATIVOS a
        JOIN CL_PROCESSAMENTOS p
          ON p.ID = a.PROCESSAMENTO_ID
        WHERE {' AND '.join(condicoes)}
        ORDER BY
            a.PROCESSAMENTO_ID,
            a.CHAVE_ATIVO
    """

    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)

            return [
                {
                    "lote_id": row[0],
                    "chave": row[1],
                    "tipo": row[2],
                    "status": row[3],
                }
                for row in cursor.fetchall()
            ]