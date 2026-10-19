import pytest
from fastapi.testclient import TestClient

from api.main import criar_app


def pedido_valido(**alteracoes) -> dict:
    corpo = {
        "meta": {"valor": 4000.0, "prazo": "2024-12"},
        "mes_referencia": "2024-04",
        "total_mes": {"renda": 6000.0, "total_gasto": 5500.0, "saldo": 500.0},
        "gastos_por_categoria": [{"categoria": "Lazer", "valor_total": 800.0}],
    }
    return corpo | alteracoes


@pytest.fixture
def pedidos_recebidos() -> list:
    return []


@pytest.fixture
def cliente(pedidos_recebidos: list) -> TestClient:
    async def executar_falso(pedido) -> dict:
        pedidos_recebidos.append(pedido)
        return {"fake": True}

    return TestClient(criar_app(executar_falso))


def test_run_responde_202_e_status_fica_done(cliente, pedidos_recebidos):
    resposta = cliente.post("/run", json=pedido_valido())
    assert resposta.status_code == 202
    assert resposta.json()["status"] == "pending"
    status = cliente.get(f"/status/{resposta.json()['task_id']}").json()
    assert status["status"] == "done"
    assert status["resultado"] == {"fake": True}
    assert pedidos_recebidos[0].meta.prazo == "2024-12"


def test_run_rejeita_prazo_anterior_ao_mes_de_referencia(cliente, pedidos_recebidos):
    corpo = pedido_valido(mes_referencia="2024-12", meta={"valor": 1000.0, "prazo": "2024-06"})
    assert cliente.post("/run", json=corpo).status_code == 422
    assert pedidos_recebidos == []


def test_run_aceita_a_saida_do_agente_1_sem_transformacao(cliente):
    corpo = pedido_valido(
        total_mes={"mes": "2024-04", "total_gasto": 5573.35, "quantidade_transacoes": 16, "renda": 4500.0,
                   "saldo": -1073.35, "percentual_renda_gasto": 123.85},
        gastos_por_categoria=[{"categoria": "Lazer", "valor_total": 800.0, "quantidade_transacoes": 3,
                               "percentual_do_total": 14.5, "percentual_da_renda": 13.3}],
    )
    assert cliente.post("/run", json=corpo).status_code == 202


def test_status_de_tarefa_inexistente_da_404(cliente):
    resposta = cliente.get("/status/nao-existe")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Tarefa não encontrada"}


def test_fluxo_que_falha_vira_error():
    async def executar_com_falha(pedido) -> dict:
        raise ValueError("O corte de Lazer excede o gasto da categoria.")

    cliente = TestClient(criar_app(executar_com_falha))
    task_id = cliente.post("/run", json=pedido_valido()).json()["task_id"]
    status = cliente.get(f"/status/{task_id}").json()
    assert status["status"] == "error"
    assert status["erro"] == "ValueError: O corte de Lazer excede o gasto da categoria."


def test_health(cliente):
    assert cliente.get("/health").json() == {"status": "ok", "agente": "agent2-planejador"}
