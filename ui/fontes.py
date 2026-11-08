"""Fontes dos dados e canais do lote. Os canais são fictícios, só para demonstração."""
from datetime import date

CANAIS: dict[str, list[str]] = {
    "Discord": ["Grupo ONE G10", "Dev Brasil"],
    "Telegram": ["Comunidade Python BR", "Vagas Tech"],
    "WhatsApp": ["Mentoria G10", "Alunos ONE"],
    "Arquivo manual": ["Pesquisa de satisfação", "Formulário de eventos"],
}

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def comunidade(fonte: str, canal: str) -> str:
    """Nome salvo no lote e no histórico, ex.: "Discord · Grupo ONE G10"."""
    return f"{fonte} · {canal}"


def periodo(ano: int, mes: int) -> str:
    """Mês de referência no formato AAAA-MM, que também vira a pasta do pacote."""
    return f"{ano}-{mes:02d}"


def nome_do_mes(mes: int) -> str:
    return MESES[mes - 1]


def anos_disponiveis() -> list[int]:
    atual = date.today().year
    return [atual - 2, atual - 1, atual]
