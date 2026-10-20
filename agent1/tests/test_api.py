import asyncio

import pytest
from fastapi.testclient import TestClient

from api.fluxos import executar_pedido
from api.main import criar_app
from api.schemas import PedidoDiagnosticar


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
    resposta = cliente.post("/run", json={"acao": "diagnosticar", "mes": "2024-04"})
    assert resposta.status_code == 202
    assert resposta.json()["status"] == "pending"
    status = cliente.get(f"/status/{resposta.json()['task_id']}").json()
    assert status["status"] == "done"
    assert status["resultado"] == {"fake": True}
    assert pedidos_recebidos[0].acao == "diagnosticar"


def test_run_aceita_importar_e_perguntar(cliente, pedidos_recebidos):
    assert cliente.post("/run", json={"acao": "importar", "csv": "data,descricao,valor\n"}).status_code == 202
    assert cliente.post("/run", json={"acao": "perguntar", "pergunta": "Quanto gastei?"}).status_code == 202
    assert [pedido.acao for pedido in pedidos_recebidos] == ["importar", "perguntar"]
    assert pedidos_recebidos[1].sessao_id == "api"


def test_run_rejeita_acao_desconhecida_e_mes_invalido(cliente):
    assert cliente.post("/run", json={"acao": "apagar"}).status_code == 422
    assert cliente.post("/run", json={"acao": "diagnosticar", "mes": "2024-13"}).status_code == 422
    assert cliente.post("/run", json={"acao": "importar", "csv": ""}).status_code == 422


def test_status_de_tarefa_inexistente_da_404(cliente):
    resposta = cliente.get("/status/nao-existe")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Tarefa não encontrada"}


def test_fluxo_que_falha_vira_error():
    async def executar_com_falha(pedido) -> dict:
        raise RuntimeError("x")

    cliente = TestClient(criar_app(executar_com_falha))
    task_id = cliente.post("/run", json={"acao": "diagnosticar", "mes": "2024-04"}).json()["task_id"]
    status = cliente.get(f"/status/{task_id}").json()
    assert status["status"] == "error"
    assert status["erro"] == "RuntimeError: x"


def test_health(cliente):
    assert cliente.get("/health").json() == {"status": "ok", "agente": "agent1-financas"}


def test_diagnosticar_mes_sem_dados_falha_antes_do_llm(banco_classificado):
    with pytest.raises(ValueError, match="Não há transações para 2023-01"):
        asyncio.run(executar_pedido(PedidoDiagnosticar(acao="diagnosticar", mes="2023-01"), banco_classificado))


def test_fluxos_da_api_usam_configuracao_nao_interativa(monkeypatch, banco_classificado):
    from dataclasses import replace

    from api import fluxos
    from tests.test_runner import _settings

    monkeypatch.setattr(fluxos, "load_settings", lambda: replace(_settings(), interativo=True))
    recebidas = []

    async def diagnosticar_falso(banco, mes, settings):
        recebidas.append(settings)
        raise RuntimeError("parar aqui")

    monkeypatch.setattr(fluxos, "diagnosticar", diagnosticar_falso)
    with pytest.raises(RuntimeError, match="parar aqui"):
        asyncio.run(executar_pedido(PedidoDiagnosticar(acao="diagnosticar", mes="2024-04"), banco_classificado))
    assert recebidas[0].interativo is False


def test_csvs_recebidos_no_mesmo_segundo_nao_se_sobrescrevem(tmp_path):
    from api.fluxos import _salvar_csv_recebido

    banco = tmp_path / "financas.db"
    primeiro = _salvar_csv_recebido(banco, "primeiro")
    segundo = _salvar_csv_recebido(banco, "segundo")
    assert primeiro != segundo
    assert primeiro.read_text(encoding="utf-8") == "primeiro"
    assert segundo.read_text(encoding="utf-8") == "segundo"
