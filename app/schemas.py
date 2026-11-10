"""Contratos JSON da API CommunityLab."""
from __future__ import annotations
from datetime import date
from datetime import date
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

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


class ContratoEntrada(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class Interacao(ContratoEntrada):
    autor: str = Field(min_length=1, max_length=300)
    canal: str = Field(min_length=1, max_length=300)
    tipo: TipoInteracao = "outro"
    texto: str = Field(min_length=1, max_length=20000)

    # Data em que a interação foi publicada.
    # Opcional para manter compatibilidade com arquivos antigos.
    data: date | None = None

    @field_validator("autor", "canal", "texto")
    @classmethod
    def nao_vazio(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "O campo não pode conter apenas espaços."
            )

        return value


class LoteEntrada(ContratoEntrada):
    origem_comunidade: str = Field(
        min_length=1,
        max_length=200,
    )
    periodo_referencia: str = Field(
        min_length=1,
        max_length=100,
    )
    interacoes: list[Interacao] = Field(max_length=1000)

    @field_validator(
        "origem_comunidade",
        "periodo_referencia",
    )
    @classmethod
    def identificadores_nao_vazios(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "O identificador não pode ser vazio."
            )

        return value


class Analise(BaseModel):
    interacao_id: str | None = None
    autor: str
    canal: str
    texto: str
    tipo: TipoInteracao
    sentimento: Sentimento
    topico: str = Field(min_length=1, max_length=300)
    relevancia: int = Field(
        ge=0,
        le=10,
        description="0 = ruído, 10 = imperdível",
    )
    rota: Literal[
        "case_sucesso",
        "faq",
        "alerta",
        "nenhuma",
    ]


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
    analises: list[Analise]
    ativos_distribuicao_gerados: AtivosDistribuicao
    armazenamento_oci: ArmazenamentoOci
    processamento_id: str | None = None
    ids_ativos: dict[str, str] = Field(default_factory=dict)
    fontes_ativos: dict[str, list[str]] = Field(
        default_factory=dict
    )
    persistencia: Literal["oracle", "desativada"] | None = None