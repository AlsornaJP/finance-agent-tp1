import pytest

from planner.schema import PedidoPlano


def montar_pedido(saldo: float = 500.0, **alteracoes) -> PedidoPlano:
    dados = {
        "meta": {"valor": 4000.0, "prazo": "2024-12"},
        "mes_referencia": "2024-04",
        "total_mes": {"renda": 6000.0, "total_gasto": 5500.0, "saldo": saldo},
        "gastos_por_categoria": [
            {"categoria": "Lazer", "valor_total": 800.0},
            {"categoria": "Moradia", "valor_total": 2000.0},
            {"categoria": "Alimentação", "valor_total": 1200.0},
        ],
    }
    return PedidoPlano.model_validate(dados | alteracoes)


@pytest.fixture
def pedido_base() -> PedidoPlano:
    return montar_pedido()
