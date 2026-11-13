from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Iterator

_pool = None
_pool_lock = threading.Lock()


class DatabaseNotConfigured(RuntimeError):
    """Indica que o Oracle não está configurado para esta execução."""


def database_mode() -> str:
    mode = os.getenv("COMMUNITYLAB_DB_MODE", "disabled").strip().lower()
    if mode not in {"disabled", "oracle"}:
        raise ValueError("COMMUNITYLAB_DB_MODE deve ser 'disabled' ou 'oracle'.")
    return mode


def oracle_configured() -> bool:
    return all(
        os.getenv(key)
        for key in (
            "COMMUNITYLAB_DB_USER",
            "COMMUNITYLAB_DB_PASSWORD",
            "COMMUNITYLAB_DB_DSN",
        )
    )


def initialize_pool():
    """Inicializa o pool Oracle, sendo seguro chamar mais de uma vez."""
    global _pool

    if database_mode() != "oracle":
        return None

    if not oracle_configured():
        raise DatabaseNotConfigured(
            "COMMUNITYLAB_DB_MODE=oracle exige "
            "COMMUNITYLAB_DB_USER, COMMUNITYLAB_DB_PASSWORD "
            "e COMMUNITYLAB_DB_DSN."
        )

    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        try:
            import oracledb
        except ImportError as exc:
            raise RuntimeError(
                "O driver python-oracledb não está instalado. "
                "Execute pip install -r requirements.txt."
            ) from exc

        kwargs = {
            "user": os.environ["COMMUNITYLAB_DB_USER"],
            "password": os.environ["COMMUNITYLAB_DB_PASSWORD"],
            "dsn": os.environ["COMMUNITYLAB_DB_DSN"],
            "min": int(os.getenv("COMMUNITYLAB_DB_POOL_MIN", "1")),
            "max": int(os.getenv("COMMUNITYLAB_DB_POOL_MAX", "4")),
            "increment": int(
                os.getenv("COMMUNITYLAB_DB_POOL_INCREMENT", "1")
            ),
            "timeout": int(
                os.getenv("COMMUNITYLAB_DB_POOL_TIMEOUT", "60")
            ),
            "wait_timeout": int(
                os.getenv("COMMUNITYLAB_DB_WAIT_TIMEOUT_MS", "10000")
            ),
            "ping_interval": int(
                os.getenv("COMMUNITYLAB_DB_PING_INTERVAL", "60")
            ),
        }

        if (
            kwargs["min"] < 1
            or kwargs["max"] < kwargs["min"]
            or kwargs["increment"] < 1
        ):
            raise ValueError(
                "Configuração inválida do pool Oracle: "
                "verifique min/max/increment."
            )

        config_dir = (
            os.getenv("COMMUNITYLAB_DB_CONFIG_DIR")
            or os.getenv("TNS_ADMIN")
        )
        wallet_location = os.getenv(
            "COMMUNITYLAB_DB_WALLET_LOCATION"
        )
        wallet_password = os.getenv(
            "COMMUNITYLAB_DB_WALLET_PASSWORD"
        )

        if config_dir:
            kwargs["config_dir"] = os.path.expanduser(config_dir)

        if wallet_location:
            kwargs["wallet_location"] = os.path.expanduser(
                wallet_location
            )

        if wallet_password:
            kwargs["wallet_password"] = wallet_password

        _pool = oracledb.create_pool(**kwargs)
        return _pool


def close_pool() -> None:
    """Encerra o pool ao desligar a aplicação."""
    global _pool

    with _pool_lock:
        pool, _pool = _pool, None

    if pool is not None:
        pool.close(force=True)


def get_pool():
    if database_mode() != "oracle":
        raise DatabaseNotConfigured(
            "A persistência Oracle está desativada nesta execução."
        )

    return _pool or initialize_pool()


@contextmanager
def connection() -> Iterator:
    """Obtém conexão do pool e evita devolver transação pendente."""
    pool = get_pool()
    conn = pool.acquire()

    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()


def ping() -> bool:
    """Executa uma consulta real para verificar a conectividade."""
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM DUAL")
            return cursor.fetchone()[0] == 1


def validate_schema() -> None:
    """Falha cedo se o schema estiver incompleto ou desatualizado."""
    required_columns = {
        "CL_SCHEMA_VERSION": {
            "VERSION_NO", "DESCRIPTION", "APPLIED_AT"
        },
        "CL_PROCESSAMENTOS": {
            "ID", "IDEMPOTENCY_KEY", "REQUEST_SHA256",
            "ATTEMPT_TOKEN", "STATUS", "ENTRADA_JSON",
            "RESULTADO_JSON", "OCI_STATUS", "OCI_BUCKET",
            "OCI_OBJECT_NAME",
        },
        "CL_INTERACOES": {
        "ID",
        "PROCESSAMENTO_ID",
        "POSICAO",
        "AUTOR",
        "CANAL",
        "TIPO",
        "TEXTO",
        "ANALISE_JSON",
        "DATA_INTERACAO",
    },
        "CL_ATIVOS": {
            "ID", "PROCESSAMENTO_ID", "CHAVE_ATIVO",
            "TIPO_ATIVO", "PAYLOAD_JSON", "STATUS_CURADORIA",
            "VERSAO", "CONSENTIMENTO_STATUS",
            "CONSENTIMENTO_REFERENCIA",
        },
        "CL_ATIVO_INTERACOES": {
            "ATIVO_ID", "PROCESSAMENTO_ID",
            "INTERACAO_ID", "METODO_ORIGEM",
        },
        "CL_HISTORICO_CURADORIA": {
            "ATIVO_ID", "PROCESSAMENTO_ID", "ACAO",
            "CONTEUDO_ANTERIOR", "CONTEUDO_NOVO", "AUTOR",
            "CONSENTIMENTO_ANTERIOR", "CONSENTIMENTO_NOVO",
            "REFERENCIA_CONSENTIMENTO",
        },
        "CL_EXPORTACOES": {
            "ID", "PROCESSAMENTO_ID", "IDEMPOTENCY_KEY",
            "STATUS", "PAYLOAD_JSON", "OCI_BUCKET",
            "OCI_OBJECT_NAME",
        },
        "CL_ALERTAS": {
            "ID", "PROCESSAMENTO_ID", "INTERACAO_ID",
            "STATUS_TRIAGEM", "VERSAO",
        },
        "CL_HISTORICO_ALERTAS": {
            "ID", "ALERTA_ID", "PROCESSAMENTO_ID",
            "NOVO_ESTADO", "AUTOR",
        },
    }

    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
            existing_tables = {
                row[0] for row in cursor.fetchall()
            }

            missing_tables = sorted(
                set(required_columns) - existing_tables
            )

            if missing_tables:
                raise RuntimeError(
                    "Schema Oracle incompleto. Execute "
                    "sql/001_oracle_schema.sql e depois "
                    "sql/002_robustez.sql. Tabelas ausentes: "
                    + ", ".join(missing_tables)
                )

            cursor.execute(
                "SELECT TABLE_NAME, COLUMN_NAME FROM USER_TAB_COLUMNS"
            )

            actual_columns: dict[str, set[str]] = {}
            for table_name, column_name in cursor.fetchall():
                actual_columns.setdefault(
                    table_name, set()
                ).add(column_name)

            missing_columns = [
                f"{table}.{column}"
                for table, columns in required_columns.items()
                for column in sorted(
                    columns - actual_columns.get(table, set())
                )
            ]

            if missing_columns:
                raise RuntimeError(
                    "Schema Oracle desatualizado ou parcialmente "
                    "aplicado. Confira as migrações 001/002. "
                    "Colunas ausentes: "
                    + ", ".join(missing_columns)
                )

            required_constraints = {
                "CK_CL_PROC_STATUS",
                "CK_CL_PROC_OCI",
                "CK_CL_PROC_TOKEN",
                "UQ_CL_PROC_IDEMP",
                "FK_CL_INT_PROC",
                "UQ_CL_INT_POS",
                "UQ_CL_INT_PROC_ID",
                "FK_CL_ATI_PROC",
                "UQ_CL_ATI_CHAVE",
                "UQ_CL_ATI_PROC_ID",
                "CK_CL_ATI_STATUS",
                "CK_CL_ATI_CONSENT",
                "CK_CL_ATI_VERSAO",
                "FK_CL_AI_ATIVO",
                "FK_CL_AI_INTER",
                "FK_CL_HIST_ATIVO",
                "FK_CL_EXP_PROC",
                "UQ_CL_EXP_IDEMP",
                "CK_CL_EXP_STATUS",
                "FK_CL_ALERTA_INTERACAO",
                "UQ_CL_ALERTA_PROC_ID",
                "UQ_CL_ALERTA_INTERACAO",
                "CK_CL_ALERTA_STATUS",
                "CK_CL_ALERTA_VERSAO",
                "FK_CL_HIST_ALERTA",
                "CK_CL_HIST_ALERTA_STATUS",
            }

            cursor.execute(
                """
                SELECT CONSTRAINT_NAME
                FROM USER_CONSTRAINTS
                WHERE STATUS = 'ENABLED'
                """
            )

            enabled_constraints = {
                row[0] for row in cursor.fetchall()
            }
            missing_constraints = sorted(
                required_constraints - enabled_constraints
            )

            if missing_constraints:
                raise RuntimeError(
                    "Schema Oracle sem restrições de integridade "
                    "críticas habilitadas: "
                    + ", ".join(missing_constraints)
                )

            cursor.execute(
                "SELECT MAX(VERSION_NO) FROM CL_SCHEMA_VERSION"
            )
            row = cursor.fetchone()

            if not row or row[0] is None:
                raise RuntimeError(
                    "CL_SCHEMA_VERSION não registra uma versão válida."
                )

            version = int(row[0])

            if version != 3:
                raise RuntimeError(
                    f"Versão do schema Oracle não suportada: {version}. "
                    "A aplicação requer a versão 3; execute as "
                    "migrações 001, 002 e 003."
                )