from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
PADRAO_MES = r"^\d{4}-(0[1-9]|1[0-2])$"


class Meta(BaseModel):
    valor: float = Field(gt=0)
    prazo: str = Field(pattern=PADRAO_MES)


class TotalMes(BaseModel):
    model_config = ConfigDict(extra="ignore")
    renda: float = Field(ge=0)
    total_gasto: float = Field(ge=0)
    saldo: float


class GastoCategoria(BaseModel):
    model_config = ConfigDict(extra="ignore")
    categoria: Categoria
    valor_total: float = Field(ge=0)


class PedidoPlano(BaseModel):
    meta: Meta
    mes_referencia: str = Field(pattern=PADRAO_MES)
    total_mes: TotalMes
    gastos_por_categoria: list[GastoCategoria] = Field(min_length=1)

    @model_validator(mode="after")
    def validar_consistencia(self) -> "PedidoPlano":
        if self.meta.prazo <= self.mes_referencia:
            raise ValueError("O prazo da meta deve ser posterior ao mes_referencia.")
        categorias = [gasto.categoria for gasto in self.gastos_por_categoria]
        repetidas = sorted({categoria for categoria in categorias if categorias.count(categoria) > 1})
        if repetidas:
            raise ValueError(f"Categoria repetida em gastos_por_categoria: {', '.join(repetidas)}.")
        return self


class Corte(BaseModel):
    categoria: Categoria
    valor_mensal: float = Field(gt=0)


class Necessidade(BaseModel):
    meses_disponiveis: int
    economia_mensal_necessaria: float
    sobra_atual: float
    valor_a_cobrir_com_cortes: float


class ProjecaoMes(BaseModel):
    mes: str
    acumulado: float


class Simulacao(BaseModel):
    economia_mensal_planejada: float
    projecao: list[ProjecaoMes]
    atinge_meta: bool
    diferenca_para_meta: float


class CorteJustificado(BaseModel):
    categoria: Categoria
    valor_mensal: float = Field(gt=0)
    justificativa: str


class PropostaDePlano(BaseModel):
    cortes: list[CorteJustificado]
    resumo: str


class CortePlanejado(BaseModel):
    categoria: Categoria
    gasto_atual: float
    corte_mensal: float
    justificativa: str


class ValorCitado(BaseModel):
    descricao: str
    valor: float
    ferramenta: str


class PlanoDeMeta(BaseModel):
    meta: Meta
    mes_referencia: str
    meses_disponiveis: int
    economia_mensal_necessaria: float
    sobra_atual: float
    valor_a_cobrir_com_cortes: float
    viavel: bool
    cortes: list[CortePlanejado]
    economia_mensal_planejada: float
    projecao: list[ProjecaoMes]
    diferenca_para_meta: float
    resumo: str
    valores_citados: list[ValorCitado]
