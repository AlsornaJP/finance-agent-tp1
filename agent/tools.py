from dataclasses import dataclass
from pathlib import Path

from agents import RunContextWrapper, function_tool
from pydantic_core import to_json

from agent import database, rag
from agent.config import Settings


@dataclass(frozen=True)
class ContextoFinanceiro:
    banco: Path
    settings: Settings


def _json(dados: object) -> str:
    return to_json(dados).decode("utf-8")


def aviso_mes_sem_dados(banco: Path, mes: str) -> str | None:
    database.validar_mes(mes)
    disponiveis = database.meses_disponiveis(banco)
    if mes in disponiveis:
        return None
    return f"Não há transações para {mes}. Meses disponíveis: {', '.join(disponiveis) or 'nenhum'}."


@function_tool
def gasto_total_mes(ctx: RunContextWrapper[ContextoFinanceiro], mes: str) -> str:
    """Retorna o total gasto, a quantidade de despesas, a renda do mês e o percentual da renda que foi gasto.

    Args:
        mes: Mês no formato AAAA-MM, por exemplo 2024-04.
    """
    banco = ctx.context.banco
    return aviso_mes_sem_dados(banco, mes) or _json(database.gasto_total_mes(banco, mes))


@function_tool
def gastos_por_categoria(ctx: RunContextWrapper[ContextoFinanceiro], mes: str) -> str:
    """Retorna, para cada categoria, o valor gasto, a quantidade de transações e os percentuais do total e da renda.

    Args:
        mes: Mês no formato AAAA-MM, por exemplo 2024-04.
    """
    banco = ctx.context.banco
    return aviso_mes_sem_dados(banco, mes) or _json(database.gastos_por_categoria(banco, mes))


@function_tool
def comparar_meses(ctx: RunContextWrapper[ContextoFinanceiro], mes_atual: str, mes_anterior: str) -> str:
    """Compara os gastos por categoria entre dois meses: valores, diferença em reais e variação percentual.

    Args:
        mes_atual: Mês mais recente, no formato AAAA-MM.
        mes_anterior: Mês de referência, no formato AAAA-MM.
    """
    banco = ctx.context.banco
    aviso = aviso_mes_sem_dados(banco, mes_atual) or aviso_mes_sem_dados(banco, mes_anterior)
    return aviso or _json(database.comparar_meses(banco, mes_atual, mes_anterior))


@function_tool
def transacoes_atipicas(ctx: RunContextWrapper[ContextoFinanceiro], mes: str) -> str:
    """Retorna as transações do mês com valor mais de 10 vezes acima da média das demais da mesma categoria.

    Args:
        mes: Mês no formato AAAA-MM, por exemplo 2024-04.
    """
    banco = ctx.context.banco
    return aviso_mes_sem_dados(banco, mes) or _json(database.transacoes_atipicas(banco, mes))


@function_tool
def listar_transacoes(
    ctx: RunContextWrapper[ContextoFinanceiro], mes: str, categoria: str | None = None
) -> str:
    """Lista as transações de um mês, opcionalmente filtradas por categoria.

    Args:
        mes: Mês no formato AAAA-MM, por exemplo 2024-04.
        categoria: Uma das categorias fixas; omita para listar todas.
    """
    banco = ctx.context.banco
    return aviso_mes_sem_dados(banco, mes) or _json(database.listar_transacoes(banco, mes, categoria))


@function_tool
async def buscar_conhecimento(ctx: RunContextWrapper[ContextoFinanceiro], consulta: str) -> str:
    """Busca por similaridade no guia de orçamento pessoal e nas memórias de conversas anteriores do usuário.

    Args:
        consulta: O que se quer saber, em linguagem natural, por exemplo "limite recomendado para alimentação".
    """
    trechos = await rag.buscar(ctx.context.banco, consulta, ctx.context.settings)
    return _json(trechos)


FERRAMENTAS = [
    gasto_total_mes,
    gastos_por_categoria,
    comparar_meses,
    transacoes_atipicas,
    listar_transacoes,
    buscar_conhecimento,
]
