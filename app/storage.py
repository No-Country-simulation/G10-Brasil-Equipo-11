"""Persistência de pacotes no OCI Object Storage."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_BUCKET = "communitylab-ativos-marketing"


def bucket_name() -> str:
    return os.getenv("OCI_BUCKET") or DEFAULT_BUCKET


class StorageConfigurationError(RuntimeError):
    pass


class StorageUploadError(RuntimeError):
    pass


def _modo() -> str:
    return os.getenv(
        "OCI_STORAGE_MODE", "local"
    ).strip().lower()


def _safe_period(period: str) -> str:
    normalized = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "-",
        str(period).strip().lower(),
    ).strip("-_")

    return (normalized or "periodo-nao-informado")[:100]


def caminho_objeto(
    periodo: str,
    processamento_id: str | None = None,
    nome_arquivo: str = "pacote-distribuicao.json",
) -> str:
    prefix = (
        f"ativos/{date.today().year}-"
        f"{_safe_period(periodo)}"
    )

    if processamento_id:
        return (
            f"{prefix}/processamentos/"
            f"{processamento_id}/{nome_arquivo}"
        )

    return f"{prefix}/{nome_arquivo}"


def oci_configurado() -> bool:
    auth_mode = os.getenv(
        "OCI_AUTH_MODE", "config_file"
    ).strip().lower()

    if not os.getenv("OCI_NAMESPACE") or not bucket_name():
        return False

    if auth_mode == "resource_principal":
        return True

    if auth_mode != "config_file":
        return False

    config_path = Path(
        os.path.expanduser(
            os.getenv("OCI_CONFIG_FILE", "~/.oci/config")
        )
    )

    return config_path.is_file()


@lru_cache(maxsize=2)
def _oci_client(
    auth_mode: str,
    config_path: str,
    profile: str,
):
    try:
        import oci
    except ImportError as exc:
        raise StorageConfigurationError(
            "O SDK oracle-oci não está instalado."
        ) from exc

    if auth_mode == "resource_principal":
        signer = (
            oci.auth.signers
            .get_resource_principals_signer()
        )

        return oci.object_storage.ObjectStorageClient(
            config={},
            signer=signer,
        )

    config = oci.config.from_file(config_path, profile)

    return oci.object_storage.ObjectStorageClient(config)


def _client():
    auth_mode = os.getenv(
        "OCI_AUTH_MODE", "config_file"
    ).strip().lower()

    if auth_mode not in {
        "config_file",
        "resource_principal",
    }:
        raise StorageConfigurationError(
            "OCI_AUTH_MODE deve ser config_file "
            "ou resource_principal."
        )

    config_path = os.path.expanduser(
        os.getenv("OCI_CONFIG_FILE", "~/.oci/config")
    )
    profile = os.getenv(
        "OCI_CONFIG_PROFILE", "DEFAULT"
    )

    return _oci_client(
        auth_mode,
        config_path,
        profile,
    )


def verificar_bucket() -> dict[str, Any]:
    """Verifica conectividade real e acesso ao bucket."""
    if not oci_configurado():
        return {
            "ok": False,
            "motivo": "OCI não configurada",
        }

    try:
        client = _client()
        bucket = bucket_name()

        client.get_bucket(
            namespace_name=os.environ["OCI_NAMESPACE"],
            bucket_name=bucket,
            timeout=(10, 30),
        )

        return {
            "ok": True,
            "bucket": bucket,
        }

    except Exception as exc:
        return {
            "ok": False,
            "motivo": type(exc).__name__,
        }


def salvar_pacote(
    pacote: dict,
    periodo: str,
    processamento_id: str | None = None,
    nome_arquivo: str = "pacote-distribuicao.json",
    object_name: str | None = None,
) -> dict:
    """Salva em disco local ou no Object Storage.

    Em modo obrigatório, uma falha de OCI gera exceção,
    sem fallback silencioso para o disco local.
    """
    modo = _modo()

    object_key = object_name or caminho_objeto(
        periodo,
        processamento_id,
        nome_arquivo,
    )

    conteudo = json.dumps(
        pacote,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    sha256 = hashlib.sha256(conteudo).hexdigest()

    if modo == "local":
        destino = Path("saida_local") / object_key
        destino.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        destino.write_bytes(conteudo)

        return {
            "bucket": "local",
            "caminho_objeto": object_key,
            "status": "salvo_localmente",
            "sha256": sha256,
            "etag": None,
        }

    if modo not in {"oci", "required"}:
        raise StorageConfigurationError(
            "OCI_STORAGE_MODE deve ser local, oci ou required."
        )

    if not oci_configurado():
        raise StorageConfigurationError(
            "Object Storage não configurado; "
            "não foi realizado fallback local."
        )

    try:
        import oci

        client = _client()
        bucket = bucket_name()

        response = client.put_object(
            namespace_name=os.environ["OCI_NAMESPACE"],
            bucket_name=bucket,
            object_name=object_key,
            put_object_body=conteudo,
            content_type="application/json",
            content_language="pt-BR",
            opc_meta={
                "sha256": sha256,
                "application": "communitylab",
            },
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
            timeout=(10, 60),
        )

        etag = getattr(
            response,
            "headers",
            {},
        ).get("etag")

        # Confere se o objeto realmente existe após o upload.
        head = client.head_object(
            namespace_name=os.environ["OCI_NAMESPACE"],
            bucket_name=bucket,
            object_name=object_key,
            timeout=(10, 30),
        )

        headers = getattr(head, "headers", {}) or {}
        remote_length = headers.get("content-length")
        remote_sha = headers.get("opc-meta-sha256")

        if (
            remote_length is None
            or int(remote_length) != len(conteudo)
        ):
            raise StorageUploadError(
                "O tamanho confirmado no Object Storage "
                "não corresponde ao arquivo enviado."
            )

        if remote_sha != sha256:
            raise StorageUploadError(
                "O SHA-256 não foi confirmado "
                "pelo Object Storage."
            )

        return {
            "bucket": bucket,
            "caminho_objeto": object_key,
            "status": "salvo_com_sucesso",
            "sha256": sha256,
            "etag": etag or headers.get("etag"),
        }

    except StorageConfigurationError:
        raise

    except Exception as exc:
        raise StorageUploadError(
            "Falha no Object Storage "
            f"({type(exc).__name__})."
        ) from exc