import pytest
from pydantic import ValidationError

from tests.conftest import montar_pedido


def test_prazo_igual_ao_mes_de_referencia_e_rejeitado():
    with pytest.raises(ValidationError, match="prazo"):
        montar_pedido(meta={"valor": 1000.0, "prazo": "2024-04"})


def test_categoria_repetida_e_rejeitada():
    gastos = [{"categoria": "Lazer", "valor_total": 100.0}, {"categoria": "Lazer", "valor_total": 50.0}]
    with pytest.raises(ValidationError, match="repetida"):
        montar_pedido(gastos_por_categoria=gastos)


def test_categoria_fora_do_dominio_e_rejeitada():
    with pytest.raises(ValidationError):
        montar_pedido(gastos_por_categoria=[{"categoria": "Viagem", "valor_total": 100.0}])


def test_mes_em_formato_invalido_e_rejeitado():
    with pytest.raises(ValidationError):
        montar_pedido(mes_referencia="2024-4")


def test_aceita_campos_extras_vindos_do_agente_1():
    pedido = montar_pedido(
        total_mes={"mes": "2024-04", "renda": 6000.0, "total_gasto": 5500.0, "saldo": 500.0,
                   "quantidade_transacoes": 16, "percentual_renda_gasto": 91.67},
        gastos_por_categoria=[{"categoria": "Lazer", "valor_total": 800.0, "quantidade_transacoes": 3,
                               "percentual_do_total": 14.5, "percentual_da_renda": 13.3}],
    )
    assert pedido.gastos_por_categoria[0].valor_total == 800.0
