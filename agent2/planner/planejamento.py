from pathlib import Path

from planner.agente import construir_planejador
from planner.config import Settings
from planner.execution_log import Secao, salvar_registro
from planner.prompts import INSTRUCTIONS_PLANEJADOR
from planner.rastreio import chamadas_de_tool, formatar_chamadas
from planner.runner import executar
from planner.schema import Corte, CortePlanejado, PedidoPlano, PlanoDeMeta, PropostaDePlano, ValorCitado
from planner.simulacao import calcular_necessidade, simular_plano
from planner.tools import ContextoPlanejamento

MAXIMO_TURNOS_PLANEJADOR = 12
ENTRADA_DO_AGENTE = "Monte o plano para a meta informada. Os dados da meta e dos gastos estão disponíveis nas tools."


def montar_plano(pedido: PedidoPlano, proposta: PropostaDePlano) -> PlanoDeMeta:
    necessidade = calcular_necessidade(pedido)
    simulacao = simular_plano(
        pedido, [Corte(categoria=corte.categoria, valor_mensal=corte.valor_mensal) for corte in proposta.cortes]
    )
    gasto_por_categoria = {gasto.categoria: gasto.valor_total for gasto in pedido.gastos_por_categoria}
    acumulado_final = simulacao.projecao[-1].acumulado
    return PlanoDeMeta(
        meta=pedido.meta,
        mes_referencia=pedido.mes_referencia,
        meses_disponiveis=necessidade.meses_disponiveis,
        economia_mensal_necessaria=necessidade.economia_mensal_necessaria,
        sobra_atual=necessidade.sobra_atual,
        valor_a_cobrir_com_cortes=necessidade.valor_a_cobrir_com_cortes,
        viavel=simulacao.atinge_meta,
        cortes=[
            CortePlanejado(
                categoria=corte.categoria,
                gasto_atual=gasto_por_categoria[corte.categoria],
                corte_mensal=corte.valor_mensal,
                justificativa=corte.justificativa,
            )
            for corte in proposta.cortes
        ],
        economia_mensal_planejada=simulacao.economia_mensal_planejada,
        projecao=simulacao.projecao,
        diferenca_para_meta=simulacao.diferenca_para_meta,
        resumo=proposta.resumo,
        valores_citados=[
            ValorCitado(descricao="Economia mensal necessária", valor=necessidade.economia_mensal_necessaria,
                        ferramenta="calcular_necessidade_da_meta"),
            ValorCitado(descricao="Sobra atual do mês de referência", valor=necessidade.sobra_atual,
                        ferramenta="calcular_necessidade_da_meta"),
            ValorCitado(descricao="Valor a cobrir com cortes", valor=necessidade.valor_a_cobrir_com_cortes,
                        ferramenta="calcular_necessidade_da_meta"),
            ValorCitado(descricao="Economia mensal planejada", valor=simulacao.economia_mensal_planejada,
                        ferramenta="simular_cortes"),
            ValorCitado(descricao="Acumulado no prazo", valor=acumulado_final, ferramenta="simular_cortes"),
            ValorCitado(descricao="Diferença para a meta", valor=simulacao.diferenca_para_meta,
                        ferramenta="simular_cortes"),
        ],
    )


async def planejar(pedido: PedidoPlano, settings: Settings) -> tuple[PlanoDeMeta, Path]:
    execucao = await executar(
        construir_planejador,
        ENTRADA_DO_AGENTE,
        settings,
        context=ContextoPlanejamento(pedido),
        max_turns=MAXIMO_TURNOS_PLANEJADOR,
    )
    proposta: PropostaDePlano = execucao.resultado.final_output
    plano = montar_plano(pedido, proposta)
    log = salvar_registro(
        f"planejar_{pedido.meta.prazo}",
        "Execução — planejar meta",
        {"Modelo": execucao.modelo, "Meta": f"{pedido.meta.valor:.2f} até {pedido.meta.prazo}"},
        [
            Secao("Pedido", pedido.model_dump_json(indent=2), "json"),
            Secao("Instructions", INSTRUCTIONS_PLANEJADOR, "markdown"),
            Secao("Chamadas de tool (argumentos e retorno)", formatar_chamadas(chamadas_de_tool(execucao.resultado.new_items))),
            Secao("Proposta do LLM (PropostaDePlano)", proposta.model_dump_json(indent=2), "json"),
            Secao("Plano final (números da simulação determinística)", plano.model_dump_json(indent=2), "json"),
        ],
    )
    return plano, log
