@echo off
chcp 65001 >nul
title Encerrar Sender AI - Painel Streamlit (Porta 8501)
echo ==========================================================
echo   Encerrando Painel Streamlit (Porta 8501)...
echo ==========================================================
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue; Write-Host 'Processo encerrado (PID:' $_ ')' }"
echo Concluido! Porta 8501 liberada.
timeout /t 2 >nul
