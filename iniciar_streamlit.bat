@echo off
chcp 65001 >nul
title Sender AI - Painel Streamlit (Porta 8501)
echo ==========================================================
echo   Iniciando Sender AI - Painel Streamlit
echo   URL: http://localhost:8501
echo ==========================================================

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY_EXEC=.venv\Scripts\python.exe"
) else (
  set "PY_EXEC=python"
)

%PY_EXEC% -m streamlit run ui/painel.py --server.port 8501
pause
