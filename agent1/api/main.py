from collections.abc import Awaitable, Callable

from fastapi import BackgroundTasks, FastAPI, HTTPException, status

from api.fluxos import executar_pedido
from api.schemas import PedidoRun, RespostaRun
from api.tarefas import RegistroDeTarefas, Tarefa

ExecutorDePedido = Callable[[PedidoRun], Awaitable[dict]]


def criar_app(executar: ExecutorDePedido = executar_pedido) -> FastAPI:
    app = FastAPI(title="Agente 1 — Finanças Pessoais")
    registro = RegistroDeTarefas()

    @app.post("/run", status_code=status.HTTP_202_ACCEPTED, response_model=RespostaRun)
    async def run(pedido: PedidoRun, background_tasks: BackgroundTasks) -> RespostaRun:
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
        return {"status": "ok", "agente": "agent1-financas"}

    return app


app = criar_app()
