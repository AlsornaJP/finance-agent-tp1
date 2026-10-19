import pytest

from planner.schema import Corte, Necessidade, ProjecaoMes
from planner.simulacao import calcular_necessidade, meses_do_plano, simular_plano
from tests.conftest import montar_pedido


def test_meses_do_plano_comeca_no_mes_seguinte_e_inclui_o_prazo():
    assert meses_do_plano("2024-04", "2024-12") == [f"2024-{mes:02d}" for mes in range(5, 13)]
    assert meses_do_plano("2024-11", "2025-02") == ["2024-12", "2025-01", "2025-02"]


def test_necessidade_desconta_a_sobra_atual(pedido_base):
    assert calcular_necessidade(pedido_base) == Necessidade(
        meses_disponiveis=8, economia_mensal_necessaria=500.0, sobra_atual=500.0, valor_a_cobrir_com_cortes=0.0
    )


def test_saldo_negativo_soma_o_deficit_ao_que_os_cortes_cobrem():
    assert calcular_necessidade(montar_pedido(saldo=-300.0)).valor_a_cobrir_com_cortes == 800.0


def test_simular_plano_projeta_acumulado_e_atinge_meta():
    simulacao = simular_plano(montar_pedido(saldo=200.0), [Corte(categoria="Lazer", valor_mensal=300.0)])
    assert simulacao.economia_mensal_planejada == 500.0
    assert simulacao.projecao[0] == ProjecaoMes(mes="2024-05", acumulado=500.0)
    assert simulacao.projecao[-1] == ProjecaoMes(mes="2024-12", acumulado=4000.0)
    assert simulacao.atinge_meta
    assert simulacao.diferenca_para_meta == 0.0


def test_simular_plano_inviavel_informa_quanto_falta():
    simulacao = simular_plano(montar_pedido(saldo=0.0), [Corte(categoria="Lazer", valor_mensal=100.0)])
    assert not simulacao.atinge_meta
    assert simulacao.diferenca_para_meta == -3200.0


def test_simular_plano_rejeita_corte_maior_que_o_gasto(pedido_base):
    with pytest.raises(ValueError, match="Lazer"):
        simular_plano(pedido_base, [Corte(categoria="Lazer", valor_mensal=900.0)])


def test_simular_plano_rejeita_categoria_ausente_da_entrada(pedido_base):
    with pytest.raises(ValueError, match="Saúde"):
        simular_plano(pedido_base, [Corte(categoria="Saúde", valor_mensal=10.0)])


def test_simular_plano_rejeita_categoria_cortada_duas_vezes(pedido_base):
    with pytest.raises(ValueError, match="Lazer"):
        simular_plano(pedido_base, [Corte(categoria="Lazer", valor_mensal=10.0), Corte(categoria="Lazer", valor_mensal=20.0)])


def test_cortar_exatamente_o_valor_a_cobrir_atinge_a_meta_mesmo_com_divisao_inexata():
    pedido = montar_pedido(saldo=0.0, meta={"valor": 1000.0, "prazo": "2024-07"})
    necessidade = calcular_necessidade(pedido)
    assert necessidade.economia_mensal_necessaria == 333.34
    simulacao = simular_plano(pedido, [Corte(categoria="Alimentação", valor_mensal=necessidade.valor_a_cobrir_com_cortes)])
    assert simulacao.atinge_meta
