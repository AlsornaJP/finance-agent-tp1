import pytest

from planner.planejamento import montar_plano
from planner.schema import CorteJustificado, CortePlanejado, PropostaDePlano
from tests.conftest import montar_pedido


def _proposta(*cortes: tuple[str, float], resumo: str = "resumo") -> PropostaDePlano:
    return PropostaDePlano(
        cortes=[CorteJustificado(categoria=categoria, valor_mensal=valor, justificativa="discricionário")
                for categoria, valor in cortes],
        resumo=resumo,
    )


def test_montar_plano_usa_apenas_numeros_da_simulacao():
    plano = montar_plano(montar_pedido(saldo=200.0), _proposta(("Lazer", 300.0)))
    assert plano.viavel
    assert plano.economia_mensal_planejada == 500.0
    assert plano.valor_a_cobrir_com_cortes == 300.0
    assert plano.cortes == [
        CortePlanejado(categoria="Lazer", gasto_atual=800.0, corte_mensal=300.0, justificativa="discricionário")
    ]
    assert plano.projecao[-1].acumulado == 4000.0
    assert {valor.ferramenta for valor in plano.valores_citados} == {"calcular_necessidade_da_meta", "simular_cortes"}


def test_montar_plano_rejeita_proposta_invalida_do_llm(pedido_base):
    with pytest.raises(ValueError, match="Lazer"):
        montar_plano(pedido_base, _proposta(("Lazer", 5000.0)))


def test_montar_plano_sem_cortes_quando_a_sobra_basta(pedido_base):
    plano = montar_plano(pedido_base, _proposta(resumo="a sobra basta"))
    assert plano.viavel
    assert plano.cortes == []
    assert plano.resumo == "a sobra basta"


def test_montar_plano_inviavel_marca_viavel_falso():
    plano = montar_plano(montar_pedido(saldo=0.0), _proposta(("Lazer", 100.0)))
    assert not plano.viavel
    assert plano.diferenca_para_meta == -3200.0
