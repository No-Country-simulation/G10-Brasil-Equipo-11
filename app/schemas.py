"""Contrato JSON de entrada e saída do CommunityLab.

Este arquivo é a referência para toda a equipe: IA, backend, interface e cloud
trabalham em cima destes modelos. Mudou o contrato? Combine com todos antes.
"""
import warnings
from typing import Literal, Optional

# O enunciado usa o campo "copy", que coincide com um método antigo do Pydantic. É inofensivo.
warnings.filterwarnings("ignore", message='Field name "copy"')

from pydantic import BaseModel, Field

TipoInteracao = Literal[
    "depoimento", "pergunta_tecnica", "feedback", "reclamacao", "projeto", "outro"
]
Sentimento = Literal[
    "Altamente Positivo", "Positivo", "Neutro", "Negativo", "Altamente Negativo"
]


# ---------- Entrada ----------
class Interacao(BaseModel):
    autor: str
    canal: str
    tipo: TipoInteracao = "outro"
    texto: str


class LoteEntrada(BaseModel):
    origem_comunidade: str
    periodo_referencia: str
    interacoes: list[Interacao]


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


# ---------- Saída ----------
class ResumoComunidade(BaseModel):
    total_interacoes_processadas: int
    sentimento_predominante: Sentimento
    topicos_principais: list[str]


class PostLinkedin(BaseModel):
    titulo: str
    copy: str
    canal_recomendado: str = "LinkedIn Oficial"
    potencial_engajamento: Literal["Alto", "Médio", "Baixo"]


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
    post_linkedin: Optional[PostLinkedin] = None
    destaque_newsletter_semanal: Optional[DestaqueNewsletter] = None
    sugestao_conteudo_faq: list[SugestaoFaq] = []
    alertas_comunidade: list[Alerta] = []


class ArmazenamentoOci(BaseModel):
    bucket: str
    caminho_objeto: str
    status: Literal["salvo_com_sucesso", "salvo_localmente", "erro"]


class RespostaProcessamento(BaseModel):
    status: Literal["sucesso", "erro"]
    resumo_comunidade: ResumoComunidade
    analises: list[Analise]
    ativos_distribuicao_gerados: AtivosDistribuicao
    armazenamento_oci: ArmazenamentoOci
