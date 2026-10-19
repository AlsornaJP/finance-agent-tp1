from typing import Annotated, Literal

from pydantic import BaseModel, Field

from api.tarefas import StatusTarefa

PADRAO_MES = r"^\d{4}-(0[1-9]|1[0-2])$"


class PedidoImportar(BaseModel):
    acao: Literal["importar"]
    csv: str = Field(min_length=1)


class PedidoPerguntar(BaseModel):
    acao: Literal["perguntar"]
    pergunta: str = Field(min_length=1)
    sessao_id: str = "api"


class PedidoDiagnosticar(BaseModel):
    acao: Literal["diagnosticar"]
    mes: str = Field(pattern=PADRAO_MES)


PedidoRun = Annotated[PedidoImportar | PedidoPerguntar | PedidoDiagnosticar, Field(discriminator="acao")]


class RespostaRun(BaseModel):
    task_id: str
    status: StatusTarefa
