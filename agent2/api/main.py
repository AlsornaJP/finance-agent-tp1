from collections.abc import Awaitable, Callable

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from pydantic import BaseModel

from api.tarefas import RegistroDeTarefas, StatusTarefa, Tarefa
from planner.config import load_settings
from planner.planejamento import planejar
from planner.schema import PedidoPlano

ExecutorDePedido = Callable[[PedidoPlano], Awaitable[dict]]


class RespostaRun(BaseModel):
    task_id: str
    status: StatusTarefa


async def executar_pedido(pedido: PedidoPlano) -> dict:
    plano, log = await planejar(pedido, load_settings())
    return {"plano": plano.model_dump(), "log": str(log)}


def criar_app(executar: ExecutorDePedido = executar_pedido) -> FastAPI:
    app = FastAPI(title="Agente 2 — Planejador de Metas")
    registro = RegistroDeTarefas()

    @app.post("/run", status_code=status.HTTP_202_ACCEPTED, response_model=RespostaRun)
    async def run(pedido: PedidoPlano, background_tasks: BackgroundTasks) -> RespostaRun:
        tarefa = registro.criar()
        background_tasks.add_task(registro.executar, tarefa.task_id, lambda: executar(pedido))
        return RespostaRun(task_id=tarefa.task_id, status=tarefa.status)

    @app.get("/status/{task_id}", response_model=Tarefa)
    async def consultar_status(task_id: str) -> Tarefa:
        tarefa = registro.obter(task_id)
        if tarefa is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
        return tarefa

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "agente": "agent2-planejador"}

    return app


app = criar_app()
