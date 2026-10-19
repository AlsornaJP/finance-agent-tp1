import asyncio

from api.tarefas import RegistroDeTarefas


def _retorna(resultado: dict):
    async def trabalho() -> dict:
        return resultado

    return trabalho


def _levanta(erro: Exception):
    async def trabalho() -> dict:
        raise erro

    return trabalho


def test_criar_gera_tarefa_pendente_com_id_unico():
    registro = RegistroDeTarefas()
    primeira, segunda = registro.criar(), registro.criar()
    assert primeira.status == "pending"
    assert primeira.task_id != segunda.task_id
    assert registro.obter(primeira.task_id) == primeira


def test_obter_id_desconhecido_retorna_none():
    assert RegistroDeTarefas().obter("inexistente") is None


def test_executar_grava_resultado_em_done():
    registro = RegistroDeTarefas()
    tarefa = registro.criar()
    asyncio.run(registro.executar(tarefa.task_id, _retorna({"ok": 1})))
    assert registro.obter(tarefa.task_id).model_dump() == {
        "task_id": tarefa.task_id,
        "status": "done",
        "resultado": {"ok": 1},
        "erro": None,
    }


def test_executar_grava_erro_e_segue_executando_as_proximas():
    registro = RegistroDeTarefas()
    falha, seguinte = registro.criar(), registro.criar()
    asyncio.run(registro.executar(falha.task_id, _levanta(ValueError("mês inválido"))))
    asyncio.run(registro.executar(seguinte.task_id, _retorna({"ok": 2})))
    assert registro.obter(falha.task_id).status == "error"
    assert registro.obter(falha.task_id).erro == "ValueError: mês inválido"
    assert registro.obter(seguinte.task_id).status == "done"
