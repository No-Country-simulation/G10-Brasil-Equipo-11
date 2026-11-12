"""Contrato JSON de entrada e saída do Sender AI.

Este arquivo é a referência para toda a equipe: IA, backend, interface e cloud
trabalham em cima destes modelos. Mudou o contrato? Combine com todos antes.
"""
from __future__ import annotations

import warnings
from datetime import date
from typing import Literal

# O enunciado usa o campo "copy", que coincide com um método antigo do Pydantic. É inofensivo.
warnings.filterwarnings("ignore", message='Field name "copy"')

from pydantic import BaseModel, Field  # noqa: E402

TipoInteracao = Literal[
    "depoimento",
    "pergunta_tecnica",
    "feedback",
    "reclamacao",
    "projeto",
    "outro",
]

Sentimento = Literal[
    "Altamente Positivo",
    "Positivo",
    "Neutro",
    "Negativo",
    "Altamente Negativo",
]


# ---------- Entrada ----------
# Os limites de tamanho acompanham as colunas do Oracle. O texto é guardado como veio
# (sem cortar espaços): a avaliação e o radar comparam trechos literais da mensagem.
class Interacao(BaseModel):
    autor: str = Field(max_length=300)
    canal: str = Field(max_length=300)
    tipo: TipoInteracao = "outro"
    texto: str = Field(max_length=20000)
    data: date | None = None  # dia em que a mensagem foi escrita; sem ela, vale o dia da importação


class LoteEntrada(BaseModel):
    origem_comunidade: str = Field(max_length=200)
    periodo_referencia: str = Field(max_length=100)
    interacoes: list[Interacao] = Field(max_length=1000)


# ---------- Análise intermediária (saída do classificador) ----------
class Analise(BaseModel):
    autor: str
    canal: str
    texto: str
    tipo: TipoInteracao
    sentimento: Sentimento
    topico: str
    relevancia: int = Field(ge=0, le=10, description="0 = ruído, 10 = imperdível")
    rota: Literal["case_sucesso", "faq", "alerta", "nenhuma"]


class AnaliseResposta(Analise):
    """Análise devolvida pela API: com Oracle, traz o ID da interação gravada."""
    interacao_id: str | None = None


# ---------- Saída ----------
class ResumoComunidade(BaseModel):
    total_interacoes_processadas: int
    sentimento_predominante: Sentimento
    topicos_principais: list[str] = Field(
        default_factory=list
    )


class PostLinkedin(BaseModel):
    titulo: str
    copy: str
    canal_recomendado: str = "LinkedIn Oficial"
    potencial_engajamento: Literal[
        "Alto",
        "Médio",
        "Baixo",
    ]


class DestaqueNewsletter(BaseModel):
    secao: str
    chamada: str
    resumo: str


class SugestaoFaq(BaseModel):
    tema: str
    origem: str
    conteudo: str
    status: str = "encaminhado_para_mentoria"


class Alerta(BaseModel):
    autor: str
    motivo: str


class AtivosDistribuicao(BaseModel):
    post_linkedin: PostLinkedin | None = None
    destaque_newsletter_semanal: DestaqueNewsletter | None = None
    sugestao_conteudo_faq: list[SugestaoFaq] = Field(
        default_factory=list
    )
    alertas_comunidade: list[Alerta] = Field(
        default_factory=list
    )


class ArmazenamentoOci(BaseModel):
    bucket: str = ""
    caminho_objeto: str = ""
    status: Literal[
        "salvo_com_sucesso",
        "salvo_localmente",
        "erro",
        "pendente",
    ]
    sha256: str | None = None
    etag: str | None = None
    detalhe: str | None = None


class RespostaProcessamento(BaseModel):
    status: Literal["sucesso", "erro"]
    resumo_comunidade: ResumoComunidade
    analises: list[AnaliseResposta]
    ativos_distribuicao_gerados: AtivosDistribuicao
    armazenamento_oci: ArmazenamentoOci
    # Identificador do lote para o painel web. Com Oracle é o mesmo valor de
    # processamento_id (texto); no histórico antigo do Supabase era um inteiro.
    lote_id: int | str | None = None
    processamento_id: str | None = None
    ids_ativos: dict[str, str] = Field(default_factory=dict)
    fontes_ativos: dict[str, list[str]] = Field(
        default_factory=dict
    )
    persistencia: Literal["oracle", "desativada"] | None = None