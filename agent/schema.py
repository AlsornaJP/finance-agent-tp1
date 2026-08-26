from pydantic import BaseModel, Field


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
