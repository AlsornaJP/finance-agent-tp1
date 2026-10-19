from planner.schema import Corte, Necessidade, PedidoPlano, ProjecaoMes, Simulacao

TOLERANCIA_CENTAVOS = 0.005


def _proximo_mes(mes: str) -> str:
    ano, numero = map(int, mes.split("-"))
    return f"{ano + 1}-01" if numero == 12 else f"{ano}-{numero + 1:02d}"


def meses_do_plano(mes_referencia: str, prazo: str) -> list[str]:
    meses = []
    mes = _proximo_mes(mes_referencia)
    while mes <= prazo:
        meses.append(mes)
        mes = _proximo_mes(mes)
    return meses


def calcular_necessidade(pedido: PedidoPlano) -> Necessidade:
    meses = len(meses_do_plano(pedido.mes_referencia, pedido.meta.prazo))
    necessaria = round(pedido.meta.valor / meses, 2)
    sobra_atual = round(pedido.total_mes.saldo, 2)
    return Necessidade(
        meses_disponiveis=meses,
        economia_mensal_necessaria=necessaria,
        sobra_atual=sobra_atual,
        valor_a_cobrir_com_cortes=round(max(0.0, necessaria - sobra_atual), 2),
    )


def _validar_cortes(pedido: PedidoPlano, cortes: list[Corte]) -> None:
    gasto_por_categoria = {gasto.categoria: gasto.valor_total for gasto in pedido.gastos_por_categoria}
    vistas: set[str] = set()
    for corte in cortes:
        if corte.categoria not in gasto_por_categoria:
            raise ValueError(f"Não há gasto de {corte.categoria} no mês de referência para cortar.")
        if corte.categoria in vistas:
            raise ValueError(f"A categoria {corte.categoria} aparece em mais de um corte.")
        if corte.valor_mensal > gasto_por_categoria[corte.categoria]:
            raise ValueError(
                f"O corte de {corte.categoria} ({corte.valor_mensal:.2f}) excede o gasto da categoria "
                f"({gasto_por_categoria[corte.categoria]:.2f})."
            )
        vistas.add(corte.categoria)


def simular_plano(pedido: PedidoPlano, cortes: list[Corte]) -> Simulacao:
    _validar_cortes(pedido, cortes)
    economia_mensal = round(pedido.total_mes.saldo + sum(corte.valor_mensal for corte in cortes), 2)
    meses = meses_do_plano(pedido.mes_referencia, pedido.meta.prazo)
    projecao = [
        ProjecaoMes(mes=mes, acumulado=round(economia_mensal * posicao, 2))
        for posicao, mes in enumerate(meses, start=1)
    ]
    acumulado_final = projecao[-1].acumulado
    return Simulacao(
        economia_mensal_planejada=economia_mensal,
        projecao=projecao,
        atinge_meta=acumulado_final >= pedido.meta.valor - TOLERANCIA_CENTAVOS,
        diferenca_para_meta=round(acumulado_final - pedido.meta.valor, 2),
    )
