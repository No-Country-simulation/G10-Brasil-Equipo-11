"""Leitura do arquivo enviado no painel, com diagnóstico amigável.

A conversão para o contrato é do adaptador da equipe (communitylab.adapter.carregar_lote).
Este módulo só faz duas coisas antes e depois dele:
  1. reconhece os problemas mais comuns de arquivos do Excel e explica como resolver;
  2. devolve um resumo para a tela de importação mostrar antes de processar.
"""
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas import LoteEntrada
from communitylab.adapter import carregar_lote

PREFIXO_ANONIMO = "anônimo_"


@dataclass
class Leitura:
    ok: bool
    nome: str
    detalhe: str = ""                       # linha curta abaixo do nome do arquivo
    lote: LoteEntrada | None = None
    titulo_erro: str = ""
    explicacao: str = ""
    passos: list[str] = field(default_factory=list)
    evidencia: str = ""                     # trecho do arquivo que mostra o problema

    @property
    def total(self) -> int:
        return len(self.lote.interacoes) if self.lote else 0

    @property
    def anonimas(self) -> int:
        if not self.lote:
            return 0
        return sum(1 for i in self.lote.interacoes if i.autor.startswith(PREFIXO_ANONIMO))


PASSOS_EXCEL = [
    "No Excel, abra o arquivo e vá em **Arquivo › Salvar como**.",
    "Escolha **CSV UTF-8 (delimitado por vírgulas)**.",
    "Envie o arquivo novo aqui.",
]


def _tamanho(n: int) -> str:
    return f"{n / 1024:.0f} KB" if n >= 1024 else f"{n} bytes"


def _diagnosticar_csv(nome: str, conteudo: bytes) -> Leitura | None:
    """Problemas de CSV que o adaptador não explica bem. None = nada de errado detectado."""
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        return Leitura(
            ok=False, nome=nome, detalhe=f"{_tamanho(len(conteudo))} · codificação antiga",
            titulo_erro="Este CSV não está em UTF-8",
            explicacao="Ele foi salvo numa codificação antiga do Windows. Se fosse lido assim, "
                       "os acentos chegariam corrompidos.",
            passos=PASSOS_EXCEL,
        )

    cabecalho = texto.splitlines()[0] if texto.strip() else ""
    if ";" in cabecalho and "," not in cabecalho:
        return Leitura(
            ok=False, nome=nome, detalhe=f"{_tamanho(len(conteudo))} · separador ponto e vírgula",
            titulo_erro="Este CSV usa ponto e vírgula como separador",
            explicacao="É o padrão do Excel em português. As colunas autor, canal, tipo e texto "
                       "não foram encontradas porque o cabeçalho chegou inteiro numa coluna só.",
            passos=PASSOS_EXCEL,
            evidencia=f"Cabeçalho recebido: {cabecalho[:120]}",
        )
    return None


def ler_arquivo(nome: str, conteudo: bytes, origem: str | None = None, periodo: str | None = None) -> Leitura:
    """Lê um JSON ou CSV enviado e devolve o lote pronto ou um erro explicado."""
    sufixo = Path(nome).suffix.lower()
    if sufixo not in (".json", ".csv"):
        return Leitura(ok=False, nome=nome, titulo_erro="Formato não suportado",
                       explicacao="Envie um arquivo .json ou .csv.")

    if sufixo == ".csv":
        problema = _diagnosticar_csv(nome, conteudo)
        if problema:
            return problema

    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / f"lote{sufixo}"
        caminho.write_bytes(conteudo)
        try:
            lote = carregar_lote(caminho, origem_comunidade=origem or None, periodo_referencia=periodo or None)
        except UnicodeDecodeError:
            return Leitura(ok=False, nome=nome, titulo_erro="O arquivo não está em UTF-8",
                           explicacao="Salve o arquivo de novo com a codificação UTF-8.", passos=PASSOS_EXCEL)
        except Exception as erro:  # ValueError do adaptador, ou erro de validação do contrato
            return Leitura(ok=False, nome=nome, detalhe=_tamanho(len(conteudo)),
                           titulo_erro="Não foi possível ler as interações", explicacao=str(erro))

    tipo = "CSV UTF-8" if sufixo == ".csv" else "JSON"
    return Leitura(ok=True, nome=nome, detalhe=f"{_tamanho(len(conteudo))} · {tipo}", lote=lote)
