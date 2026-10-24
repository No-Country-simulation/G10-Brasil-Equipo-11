"""Verificação completa do CommunityLab. Responsável: Renato.

Roda as etapas na ordem e mostra OK ou FALHOU em cada uma.
Normalmente é chamado por verificar.ps1 (Windows) ou verificar.sh (Linux/Mac),
que antes criam o ambiente virtual e instalam as dependências.

    python verificar.py           # tudo em modo simulado (não gasta cota, não sobe nada para a nuvem)
    python verificar.py --real    # usa o Gemini e o OCI configurados no .env

O relatório também é salvo em saida_local/relatorio_verificacao.txt.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
REAL = "--real" in sys.argv
RESULTADOS: list[tuple[str, str, str]] = []

# Saída em UTF-8 também no terminal do Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def registrar(etapa: str, status: str, detalhe: str = ""):
    RESULTADOS.append((etapa, status, detalhe))
    marca = {"OK": "[ OK ]", "FALHOU": "[FALHOU]", "AVISO": "[AVISO]"}[status]
    print(f"{marca} {etapa}" + (f" — {detalhe}" if detalhe else ""), flush=True)


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def ambiente_servidor() -> dict:
    """Sem --real, força modo simulado e desliga o OCI. O load_dotenv do app não sobrescreve isso."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    if not REAL:
        env["LLM_MODO"] = "mock"
        env["OCI_NAMESPACE"] = ""
    return env


def esperar(url: str, segundos: int = 40) -> str | None:
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                return r.read().decode("utf-8")
        except Exception:
            time.sleep(0.5)
    return None


def iniciar(cmd: list[str], log: Path) -> subprocess.Popen:
    log.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(cmd, cwd=RAIZ, env=ambiente_servidor(),
                            stdout=log.open("w", encoding="utf-8"), stderr=subprocess.STDOUT)


def parar(proc: subprocess.Popen):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def ultimas_linhas(log: Path, n: int = 5) -> str:
    try:
        return " | ".join(log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-n:])
    except FileNotFoundError:
        return ""


# ---------------------------------------------------------------------------
def etapa_python():
    v = sys.version_info
    if v >= (3, 10):
        registrar("Versão do Python", "OK", f"{v.major}.{v.minor}.{v.micro}")
    else:
        registrar("Versão do Python", "FALHOU", f"{v.major}.{v.minor} encontrada; é preciso 3.10 ou mais novo")


def etapa_dependencias():
    faltando = []
    for modulo in ("fastapi", "uvicorn", "langgraph", "pydantic", "streamlit", "pandas", "dotenv", "pytest"):
        try:
            __import__(modulo)
        except ImportError:
            faltando.append(modulo)
    try:
        import communitylab  # noqa: F401
    except ImportError:
        faltando.append("communitylab (rode: python -m pip install -e .)")
    if faltando:
        registrar("Dependências instaladas", "FALHOU", "faltando: " + ", ".join(faltando))
    else:
        registrar("Dependências instaladas", "OK")


def etapa_env():
    env, exemplo = RAIZ / ".env", RAIZ / ".env.example"
    if not env.exists():
        shutil.copy(exemplo, env)
        registrar("Arquivo .env", "OK", "criado a partir do .env.example")
    else:
        registrar("Arquivo .env", "OK", "já existia")

    from dotenv import dotenv_values
    cfg = dotenv_values(env)
    tem_chave = bool(cfg.get("GEMINI_API_KEY"))
    mock_no_env = (cfg.get("LLM_MODO") or "").lower() == "mock"
    if not REAL:
        registrar("Modo desta verificação", "OK", "simulado (use --real para Gemini e OCI)")
    elif not tem_chave:
        registrar("Modo desta verificação", "FALHOU", "--real pedido, mas GEMINI_API_KEY está vazia no .env")
    elif mock_no_env:
        registrar("Modo desta verificação", "FALHOU", "--real pedido, mas o .env tem LLM_MODO=mock; apague essa linha")
    else:
        registrar("Modo desta verificação", "OK", "real: Gemini" + (" + OCI" if cfg.get("OCI_NAMESPACE") else ", OCI não configurado"))


def etapa_testes():
    filtro = "real" if REAL else "not real"
    cmd = [sys.executable, "-m", "pytest", "-q", "-m", filtro, "-p", "no:cacheprovider"]
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ambiente_servidor())
    linhas = [l for l in r.stdout.strip().splitlines() if l.strip()]
    resumo = linhas[-1].strip("= ") if linhas else "sem saída"
    nome = "Testes com serviços reais" if REAL else "Testes automatizados"
    if r.returncode in (0, 5):  # 5 = nenhum teste selecionado
        registrar(nome, "OK", resumo)
    else:
        falhas = [l for l in linhas if l.startswith(("FAILED", "ERROR"))][:5]
        registrar(nome, "FALHOU", resumo + (" | " + " | ".join(falhas) if falhas else ""))


def etapa_api():
    porta = porta_livre()
    base = f"http://127.0.0.1:{porta}"
    log = RAIZ / "saida_local" / "log_api.txt"
    proc = iniciar([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(porta)], log)
    try:
        saude = esperar(f"{base}/saude")
        if saude is None:
            registrar("API sobe e responde /saude", "FALHOU", ultimas_linhas(log) or "não respondeu em 40 s")
            return
        modo = json.loads(saude).get("modo_llm")
        registrar("API sobe e responde /saude", "OK", f"porta {porta}, modo_llm={modo}")

        lote = json.loads((RAIZ / "data" / "interacoes_exemplo.json").read_text(encoding="utf-8"))
        pedido = urllib.request.Request(
            f"{base}/processar", data=json.dumps(lote).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        inicio = time.time()
        try:
            with urllib.request.urlopen(pedido, timeout=300) as r:
                corpo = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            registrar("Processar lote de exemplo", "FALHOU", f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}")
            return
        segundos = time.time() - inicio

        total = corpo["resumo_comunidade"]["total_interacoes_processadas"]
        esperado = len(lote["interacoes"])
        rotas = {}
        for a in corpo["analises"]:
            rotas[a["rota"]] = rotas.get(a["rota"], 0) + 1
        if corpo.get("status") == "sucesso" and total == esperado:
            registrar("Processar lote de exemplo", "OK",
                      f"{total} interações em {segundos:.1f} s; rotas: " + ", ".join(f"{k}={v}" for k, v in sorted(rotas.items())))
        else:
            registrar("Processar lote de exemplo", "FALHOU", f"status={corpo.get('status')}, {total} de {esperado} interações")

        armaz = corpo["armazenamento_oci"]
        if armaz["status"] == "salvo_localmente":
            arquivo = RAIZ / armaz["caminho_objeto"]
            if arquivo.exists():
                registrar("Pacote salvo", "OK", f"local: {armaz['caminho_objeto']}")
            else:
                registrar("Pacote salvo", "FALHOU", f"arquivo não encontrado: {arquivo}")
        elif armaz["status"] == "salvo_com_sucesso":
            registrar("Pacote salvo", "OK", f"OCI: {armaz['bucket']}/{armaz['caminho_objeto']}")
        else:
            registrar("Pacote salvo", "FALHOU", f"status={armaz['status']}; veja saida_local/log_api.txt")
    finally:
        parar(proc)


def etapa_painel():
    porta = porta_livre()
    log = RAIZ / "saida_local" / "log_painel.txt"
    proc = iniciar([sys.executable, "-m", "streamlit", "run", "ui/painel.py", "--server.headless", "true",
                    "--server.port", str(porta), "--browser.gatherUsageStats", "false"], log)
    try:
        saude = esperar(f"http://127.0.0.1:{porta}/_stcore/health", segundos=60)
        if saude and saude.strip() == "ok":
            registrar("Painel Streamlit inicia", "OK", f"porta {porta}")
        else:
            registrar("Painel Streamlit inicia", "FALHOU", ultimas_linhas(log) or "não respondeu em 60 s")
    finally:
        parar(proc)


def salvar_relatorio():
    destino = RAIZ / "saida_local" / "relatorio_verificacao.txt"
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = [
        f"CommunityLab — relatório de verificação ({'real' if REAL else 'simulado'})",
        f"Data: {datetime.now():%Y-%m-%d %H:%M}",
        f"Python: {sys.version.split()[0]} em {sys.platform}",
        "",
    ] + [f"{s:7} {e}" + (f" — {d}" if d else "") for e, s, d in RESULTADOS]
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino


def main():
    print(f"\nCommunityLab — verificação {'com serviços reais' if REAL else 'em modo simulado'}\n")
    etapa_python()
    etapa_dependencias()
    if RESULTADOS[-1][1] == "FALHOU":
        print("\nInstale as dependências antes de continuar (veja docs/EXECUCAO.md).")
        return 1
    etapa_env()
    etapa_testes()
    etapa_api()
    etapa_painel()

    falhas = [r for r in RESULTADOS if r[1] == "FALHOU"]
    relatorio = salvar_relatorio()
    print("\n" + ("TUDO OK" if not falhas else f"{len(falhas)} ETAPA(S) FALHARAM") +
          f" — relatório em {relatorio.relative_to(RAIZ)}\n")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
