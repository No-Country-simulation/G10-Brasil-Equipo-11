@echo off
chcp 65001 >nul
title Sender AI - Interface Vanilla Web (Porta 8000)
echo ==========================================================
echo   Iniciando Sender AI - Interface Vanilla Web + API
echo   URL: http://127.0.0.1:8000
echo ==========================================================

cd /d "%~dp0"

REM 1. Encerra qualquer processo anterior na porta 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

REM 2. Detecta o executavel Python (.venv ou global)
if exist ".venv\Scripts\python.exe" (
  set "PY_EXEC=.venv\Scripts\python.exe"
) else (
  set "PY_EXEC=python"
)

REM 3. Abre o navegador SOMENTE quando o servidor estiver respondendo na porta 8000
start "" powershell -NoProfile -Command "$tentativas=0; while ($tentativas -lt 30) { try { $tcp = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8000); if ($tcp.Connected) { $tcp.Close(); break } } catch {}; Start-Sleep -Milliseconds 400; $tentativas++ }; Start-Process 'http://127.0.0.1:8000'"

REM 4. Inicia o servidor FastAPI (estavel, sem descartar conexoes de estaticos)
%PY_EXEC% -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
