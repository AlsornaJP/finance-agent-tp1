from dataclasses import dataclass

from agents import RunContextWrapper, function_tool

from planner import simulacao
from planner.schema import Corte, PedidoPlano


@dataclass(frozen=True)
class ContextoPlanejamento:
    pedido: PedidoPlano


@function_tool
def calcular_necessidade_da_meta(ctx: RunContextWrapper[ContextoPlanejamento]) -> str:
    """Calcula os meses disponíveis até o prazo, a economia mensal necessária para a meta, a sobra atual do
    mês de referência e quanto falta cobrir com cortes."""
    return simulacao.calcular_necessidade(ctx.context.pedido).model_dump_json()


@function_tool
def simular_cortes(ctx: RunContextWrapper[ContextoPlanejamento], cortes: list[Corte]) -> str:
    """Simula um conjunto de cortes mensais por categoria e devolve a economia mensal planejada, a projeção
    acumulada mês a mês, se a meta é atingida no prazo e a diferença para a meta.

    Args:
        cortes: Cortes mensais propostos, no máximo um por categoria, cada um menor ou igual ao gasto atual dela.
    """
    try:
        return simulacao.simular_plano(ctx.context.pedido, cortes).model_dump_json()
    except ValueError as erro:
        return f"Cortes inválidos: {erro}"


FERRAMENTAS = [calcular_necessidade_da_meta, simular_cortes]
