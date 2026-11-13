"""Gera, na pasta deploy-easypanel/ (ignorada pelo git e pelo Docker), os textos para colar
no Easypanel a partir do seu .env e do ~/.oci/config. Veja docs/deploy-easypanel.md.

    python scripts/preparar_easypanel.py

Não imprime nenhum valor secreto: só nomes de variáveis e caminhos. Apague a pasta
deploy-easypanel/ depois de configurar o Easypanel."""
import re
import sys
from pathlib import Path

repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
saida = repo / "deploy-easypanel"
saida.mkdir(exist_ok=True)

# Caminhos de dentro do container e ajustes para o servidor
SOBRESCREVER = {
    "COMMUNITYLAB_DB_MODE": "oracle",
    "COMMUNITYLAB_DB_CONFIG_DIR": "/app/wallet",
    "COMMUNITYLAB_DB_WALLET_LOCATION": "/app/wallet",
    "OCI_CONFIG_FILE": "/app/oci/config",
    "OCI_STORAGE_MODE": "oci",
    "DATABASE_URL": "",
    "APP_ENV": "development",
}

linhas, vistos = [], set()
for bruta in (repo / ".env").read_text(encoding="utf-8-sig").splitlines():
    m = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", bruta.strip())
    if not m:
        continue
    chave, valor = m[1], m[2].strip()
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        valor = valor[1:-1]  # o Easypanel guarda o valor literal: sem aspas
    if chave in vistos:  # mantém a última ocorrência, como o python-dotenv
        linhas = [l for l in linhas if not l.startswith(chave + "=")]
    vistos.add(chave)
    linhas.append(f"{chave}={SOBRESCREVER.get(chave, valor)}")
for chave, valor in SOBRESCREVER.items():
    if chave not in vistos:
        linhas.append(f"{chave}={valor}")

(saida / "1-variaveis-de-ambiente.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")

cfg = (Path.home() / ".oci" / "config").read_text(encoding="utf-8-sig")
pem = Path(re.search(r"(?m)^key_file\s*=\s*(.+)$", cfg)[1].strip())
(saida / "3-oci-config.txt").write_text(
    re.sub(r"(?m)^key_file\s*=.*$", "key_file=/app/oci/chave.pem", cfg), encoding="utf-8", newline="\n")

senha_fraca = any(l == "ADMIN_SENHA=admin123" for l in linhas)
print("variáveis geradas:", ", ".join(l.split("=", 1)[0] for l in linhas))
print("ADMIN_SENHA ainda é a de demonstração:", senha_fraca)
print("chave da OCI a colar em /app/oci/chave.pem:", pem)
