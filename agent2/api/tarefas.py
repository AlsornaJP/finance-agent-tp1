import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

StatusTarefa = Literal["pending", "done", "error"]


class Tarefa(BaseModel):
    task_id: str
    status: StatusTarefa
    resultado: dict | None = None
    erro: str | None = None


class RegistroDeTarefas:
    def __init__(self) -> None:
        self._tarefas: dict[str, Tarefa] = {}
        self._execucao_unica = asyncio.Lock()

    def criar(self) -> Tarefa:
        tarefa = Tarefa(task_id=str(uuid4()), status="pending")
        self._tarefas[tarefa.task_id] = tarefa
        return tarefa

    def obter(self, task_id: str) -> Tarefa | None:
        return self._tarefas.get(task_id)

    async def executar(self, task_id: str, trabalho: Callable[[], Awaitable[dict]]) -> None:
        async with self._execucao_unica:
            try:
                resultado = await trabalho()
            except Exception as erro:
                self._tarefas[task_id] = Tarefa(
                    task_id=task_id, status="error", erro=f"{type(erro).__name__}: {erro}"
                )
                return
            self._tarefas[task_id] = Tarefa(task_id=task_id, status="done", resultado=resultado)
