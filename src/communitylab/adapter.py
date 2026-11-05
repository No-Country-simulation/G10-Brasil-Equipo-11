import csv
import io
import json
from pathlib import Path
from typing import Any

from app.schemas import Interacao, LoteEntrada


ALIASES = {
    "text": "texto",
    "channel": "canal",
    "type": "tipo",
    "author": "autor",
}

CAMPOS_OBRIGATORIOS_PT = ("texto", "canal", "tipo")


def _decodificar_bytes(conteudo: bytes) -> str:
    """Decodifica bytes suportando UTF-8 (com ou sem BOM) e Windows-1252 (cp1252)."""
    for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return conteudo.decode(codificacao)
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível decodificar o arquivo. Utilize UTF-8 ou Windows-1252.")


def _detectar_delimitador(texto: str) -> str:
    """Detecta automaticamente o separador do CSV (vírgula, ponto e vírgula ou tabulação)."""
    linhas = [linha for linha in texto.splitlines() if linha.strip()]
    if not linhas:
        return ","

    cabecalho = linhas[0]
    contagens = {
        ";": cabecalho.count(";"),
        ",": cabecalho.count(","),
        "\t": cabecalho.count("\t"),
    }
    melhor_delimitador, maior_contagem = max(contagens.items(), key=lambda item: item[1])
    if maior_contagem > 0:
        return melhor_delimitador

    try:
        dialeto = csv.Sniffer().sniff(cabecalho, delimiters=",;\t")
        return dialeto.delimiter
    except csv.Error:
        return ","


def _ler_registros_csv(texto: str) -> list[dict[str, Any]]:
    """Interpreta conteúdo CSV normalizando delimitador e cabeçalhos em PT/EN."""
    delimitador = _detectar_delimitador(texto)
    try:
        leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
        if not leitor.fieldnames:
            raise ValueError("O CSV está vazio ou não possui cabeçalho.")

        cabecalhos_normalizados = {
            ALIASES.get(campo.strip().lower(), campo.strip().lower())
            for campo in leitor.fieldnames
            if campo is not None
        }

        faltantes = [
            campo
            for campo in CAMPOS_OBRIGATORIOS_PT
            if campo not in cabecalhos_normalizados
        ]
        if faltantes:
            raise ValueError(
                "O CSV não possui as colunas obrigatórias: "
                + ", ".join(faltantes)
            )

        return [
            {
                str(chave).strip(): valor
                for chave, valor in linha.items()
                if chave is not None
            }
            for linha in leitor
        ]
    except csv.Error as exc:
        raise ValueError(f"Não foi possível interpretar o CSV: {exc}") from exc


def _normalizar_interacao(
    registro: dict[str, Any],
    indice: int,
) -> Interacao:
    """Converte uma interação para o contrato oficial do pipeline."""

    dados = {
        ALIASES.get(str(chave).strip().lower(), str(chave).strip().lower()): valor
        for chave, valor in registro.items()
    }

    texto = dados.get("texto")
    canal = dados.get("canal")
    tipo = dados.get("tipo") or "outro"
    autor = dados.get("autor")

    if not isinstance(texto, str) or not texto.strip():
        raise ValueError(
            f"A interação {indice} não possui um texto válido."
        )

    if not isinstance(canal, str) or not canal.strip():
        raise ValueError(
            f"A interação {indice} não possui um canal válido."
        )

    if not isinstance(tipo, str) or not tipo.strip():
        tipo = "outro"

    if not isinstance(autor, str) or not autor.strip():
        autor = f"anônimo_{indice:03d}"

    return Interacao(
        autor=autor.strip(),
        canal=canal.strip(),
        tipo=tipo.strip(),
        texto=texto.strip(),
    )


def carregar_lote_bytes(
    conteudo: bytes,
    nome_arquivo: str = "lote.csv",
    origem_comunidade: str | None = None,
    periodo_referencia: str | None = None,
) -> LoteEntrada:
    """Carrega bytes de um arquivo CSV ou JSON e converte para LoteEntrada."""
    sufixo = Path(nome_arquivo).suffix.lower()
    texto = _decodificar_bytes(conteudo)

    origem_arquivo = None
    periodo_arquivo = None

    if sufixo == ".json":
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido: {exc}") from exc

        if isinstance(dados, dict):
            origem_arquivo = dados.get("origem_comunidade")
            periodo_arquivo = dados.get("periodo_referencia")

            if "interacoes" in dados:
                registros = dados["interacoes"]
            elif "interactions" in dados:
                registros = dados["interactions"]
            else:
                raise ValueError(
                    "O JSON deve conter 'interacoes' ou 'interactions'."
                )
        elif isinstance(dados, list):
            registros = dados
        else:
            raise ValueError(
                "O JSON deve conter uma lista ou um objeto com interações."
            )

        if not isinstance(registros, list):
            raise ValueError("A coleção de interações deve ser uma lista.")

    elif sufixo == ".csv":
        registros = _ler_registros_csv(texto)
    else:
        raise ValueError(
            "Formato não suportado. Utilize um arquivo CSV ou JSON."
        )

    if not registros:
        raise ValueError("O arquivo não contém interações.")

    interacoes = [
        _normalizar_interacao(registro, indice)
        for indice, registro in enumerate(registros, start=1)
    ]

    origem = origem_comunidade or origem_arquivo or "comunidade_importada"
    periodo = (
        periodo_referencia
        or periodo_arquivo
        or "periodo_nao_informado"
    )

    return LoteEntrada(
        origem_comunidade=origem,
        periodo_referencia=periodo,
        interacoes=interacoes,
    )


def carregar_lote(
    caminho: str | Path,
    origem_comunidade: str | None = None,
    periodo_referencia: str | None = None,
) -> LoteEntrada:
    """
    Carrega CSV ou JSON e converte os registros para LoteEntrada.

    Aceita os campos em português e inglês, separadores ',' ou ';'
    e codificações UTF-8, UTF-8-SIG (BOM) e Windows-1252 (cp1252).
    """

    path = Path(caminho)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    if not path.is_file():
        raise ValueError(f"O caminho não é um arquivo: {path}")

    return carregar_lote_bytes(
        conteudo=path.read_bytes(),
        nome_arquivo=path.name,
        origem_comunidade=origem_comunidade,
        periodo_referencia=periodo_referencia,
    )
