"""Persistência dos pacotes de ativos no OCI Object Storage. Dono: pessoa 4.

Sem as variáveis OCI configuradas, salva em ./saida_local/ para não travar o desenvolvimento.
Configuração do SDK: https://docs.oracle.com/iaas/Content/API/Concepts/sdkconfig.htm
"""
import json
import os
from datetime import date
from pathlib import Path

BUCKET = os.getenv("OCI_BUCKET", "communitylab-ativos-marketing")


def caminho_objeto(periodo: str) -> str:
    semana = periodo.lower().replace("_", "-")
    return f"ativos/{date.today().year}-{semana}/pacote-distribuicao.json"


def oci_configurado() -> bool:
    return bool(os.getenv("OCI_NAMESPACE")) and Path(os.path.expanduser(os.getenv("OCI_CONFIG_FILE", "~/.oci/config"))).exists()


def salvar_pacote(pacote: dict, periodo: str) -> dict:
    caminho = caminho_objeto(periodo)
    conteudo = json.dumps(pacote, ensure_ascii=False, indent=2).encode("utf-8")

    if not oci_configurado():
        destino = Path("saida_local") / caminho
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
        return {"bucket": "local", "caminho_objeto": str(destino), "status": "salvo_localmente"}

    try:
        import oci

        config = oci.config.from_file(os.getenv("OCI_CONFIG_FILE", "~/.oci/config"))
        cliente = oci.object_storage.ObjectStorageClient(config)
        cliente.put_object(
            namespace_name=os.environ["OCI_NAMESPACE"],
            bucket_name=BUCKET,
            object_name=caminho,
            put_object_body=conteudo,
            content_type="application/json",
        )
        return {"bucket": BUCKET, "caminho_objeto": caminho, "status": "salvo_com_sucesso"}
    except Exception as e:
        print(f"[OCI] falha no upload: {e}")
        return {"bucket": BUCKET, "caminho_objeto": caminho, "status": "erro"}
