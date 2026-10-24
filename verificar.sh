#!/usr/bin/env bash
# CommunityLab — verificação completa no Linux/Mac. Responsável: Renato.
#
# Uso, na pasta raiz do projeto:
#   bash verificar.sh          # modo simulado
#   bash verificar.sh --real   # Gemini e OCI do .env
set -euo pipefail
cd "$(dirname "$0")"

falhar() { echo "[FALHOU] $1"; echo "Veja a seção 'Problemas comuns' em docs/EXECUCAO.md"; exit 1; }

echo ""
echo "CommunityLab — preparando o ambiente"

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then PY="$c"; break; fi
done
[ -n "$PY" ] || falhar "Python 3.10 ou mais novo não encontrado."
echo "[ OK ] $($PY --version)"

if [ ! -x .venv/bin/python ]; then
  echo "       Criando o ambiente virtual .venv (só na primeira vez)..."
  "$PY" -m venv .venv || falhar "Não foi possível criar o .venv (no Ubuntu: sudo apt install python3-venv)"
fi
echo "[ OK ] Ambiente virtual .venv"

echo "       Instalando dependências (a primeira vez leva alguns minutos)..."
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt || falhar "pip install -r requirements.txt falhou"
.venv/bin/python -m pip install --quiet --disable-pip-version-check -e . || falhar "pip install -e . falhou"
echo "[ OK ] Dependências instaladas"

exec .venv/bin/python verificar.py "$@"
