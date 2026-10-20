from dataclasses import replace
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from agent import database
from agent.config import Settings, load_settings
from agent.consulta import perguntar
from agent.database import CAMINHO_BANCO_PADRAO
from agent.diagnostico import diagnosticar, levantar_mes
from agent.importacao import importar
from api.schemas import PedidoDiagnosticar, PedidoImportar, PedidoPerguntar, PedidoRun


def _configuracao_da_api() -> Settings:
    return replace(load_settings(), interativo=False)


def _salvar_csv_recebido(banco: Path, conteudo: str) -> Path:
    diretorio = banco.parent / "importacoes"
    diretorio.mkdir(parents=True, exist_ok=True)
    destino = diretorio / f"api_{datetime.now():%Y%m%d-%H%M%S}_{uuid4().hex[:8]}.csv"
    destino.write_text(conteudo, encoding="utf-8")
    return destino


async def _importar(pedido: PedidoImportar, banco: Path) -> dict:
    caminho_csv = _salvar_csv_recebido(banco, pedido.csv)
    log = await importar(banco, caminho_csv, _configuracao_da_api())
    return {"log": str(log), "meses_disponiveis": database.meses_disponiveis(banco)}


async def _perguntar(pedido: PedidoPerguntar, banco: Path) -> dict:
    resultado = await perguntar(banco, pedido.sessao_id, pedido.pergunta, _configuracao_da_api())
    return {"resposta": resultado.resposta.model_dump(), "log": str(resultado.log)}


async def _diagnosticar(pedido: PedidoDiagnosticar, banco: Path) -> dict:
    levantamento = levantar_mes(banco, pedido.mes)
    diagnostico, log = await diagnosticar(banco, pedido.mes, _configuracao_da_api())
    return {
        "diagnostico": diagnostico.model_dump(),
        "total_mes": levantamento.total.model_dump(),
        "gastos_por_categoria": [categoria.model_dump() for categoria in levantamento.categorias],
        "log": str(log),
    }


async def executar_pedido(pedido: PedidoRun, banco: Path = CAMINHO_BANCO_PADRAO) -> dict:
    match pedido:
        case PedidoImportar():
            return await _importar(pedido, banco)
        case PedidoPerguntar():
            return await _perguntar(pedido, banco)
        case PedidoDiagnosticar():
            return await _diagnosticar(pedido, banco)
