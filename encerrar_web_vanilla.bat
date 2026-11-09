@echo off
chcp 65001 >nul
title Encerrar Sender AI - Interface Vanilla Web (Porta 8000)
echo ==========================================================
echo   Encerrando servidor Vanilla Web / FastAPI (Porta 8000)...
echo ==========================================================
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue; Write-Host 'Processo encerrado (PID:' $_ ')' }"
echo Concluido! Porta 8000 liberada.
timeout /t 2 >nul
