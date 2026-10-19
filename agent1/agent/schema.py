from typing import Literal, get_args

from pydantic import BaseModel, Field

Categoria = Literal[
    "Alimentação",
    "Transporte",
    "Moradia",
    "Saúde",
    "Educação",
    "Lazer",
    "Compras",
    "Serviços/Assinaturas",
    "Não identificado",
]
CATEGORIAS: tuple[str, ...] = get_args(Categoria)

SituacaoNoGuia = Literal["dentro do recomendado", "fora do recomendado", "sem referência no guia"]


class ResultadoImportacao(BaseModel):
    inseridas: int
    ignoradas: int


class Transacao(BaseModel):
    id: int
    data: str
    descricao: str
    valor: float
    tipo: str
    categoria: str | None


class TransacaoParaClassificar(BaseModel):
    id: int
    descricao: str
    valor: float


class TotalMes(BaseModel):
    mes: str
    total_gasto: float
    quantidade_transacoes: int
    renda: float
    saldo: float
    percentual_renda_gasto: float | None


class GastoCategoria(BaseModel):
    categoria: str
    valor_total: float
    quantidade_transacoes: int
    percentual_do_total: float | None
    percentual_da_renda: float | None


class ComparacaoMensal(BaseModel):
    categoria: str
    valor_atual: float
    valor_anterior: float
    diferenca: float
    variacao_percentual: float | None


class TransacaoAtipica(BaseModel):
    data: str
    descricao: str
    valor: float
    categoria: str
    media_categoria: float
    razao: float


class TrechoRecuperado(BaseModel):
    origem: str
    texto: str
    similaridade: float


class LevantamentoMensal(BaseModel):
    total: TotalMes
    categorias: list[GastoCategoria]
    mes_anterior: str | None
    comparacao: list[ComparacaoMensal]
    atipicas: list[TransacaoAtipica]


class ClassificacaoTransacao(BaseModel):
    id: int
    justificativa: str
    categoria: Categoria


class ClassificacaoLote(BaseModel):
    classificacoes: list[ClassificacaoTransacao]


class ValorCitado(BaseModel):
    descricao: str
    valor: float
    ferramenta: str


class RespostaFinanceira(BaseModel):
    resposta: str
    valores_citados: list[ValorCitado] = Field(default_factory=list)
    fontes_conhecimento: list[str] = Field(default_factory=list)


class PontoDeAtencao(BaseModel):
    assunto: str
    dados: str
    motivo: str


class PontosDeAtencao(BaseModel):
    pontos: list[PontoDeAtencao]


class AvaliacaoPonto(BaseModel):
    assunto: str
    situacao: SituacaoNoGuia
    trecho_guia: str
    explicacao: str


class AvaliacaoGuia(BaseModel):
    avaliacoes: list[AvaliacaoPonto]


class Recomendacao(BaseModel):
    prioridade: int = Field(ge=1)
    acao: str
    justificativa: str


class DiagnosticoMensal(BaseModel):
    mes: str
    resumo: str
    avaliacoes: list[AvaliacaoPonto]
    recomendacoes: list[Recomendacao]


class TransacaoClassificada(BaseModel):
    data: str
    descricao: str
    valor: float
    categoria: str


class ResumoCategoria(BaseModel):
    categoria: str
    valor_total: float
    quantidade_transacoes: int


class GastoAnomalo(BaseModel):
    transacao: str
    motivo_anomalia: str


class ComparacaoCategoria(BaseModel):
    categoria: str
    valor_atual: float
    valor_anterior: float
    variacao: str


class AnaliseFinanceira(BaseModel):
    transacoes: list[TransacaoClassificada] = Field(default_factory=list)
    periodo_analisado: str
    total_gasto: float
    resumo_por_categoria: list[ResumoCategoria] = Field(default_factory=list)
    gastos_anomalos: list[GastoAnomalo] = Field(default_factory=list)
    comparacao_mes_anterior: list[ComparacaoCategoria] = Field(default_factory=list)
