from dataclasses import dataclass
from pathlib import Path

from agents import SQLiteSession

from agent import rag
from agent.agents import construir_assistente
from agent.config import Settings
from agent.execution_log import DIRETORIO_LOGS, Secao, salvar_registro
from agent.prompts import INSTRUCTIONS_ASSISTENTE
from agent.rastreio import ChamadaTool, chamadas_de_tool, formatar_chamadas
from agent.runner import Execucao, executar
from agent.schema import RespostaFinanceira
from agent.tools import ContextoFinanceiro

MAXIMO_TURNOS_ASSISTENTE = 15


@dataclass(frozen=True)
class ResultadoPergunta:
    resposta: RespostaFinanceira
    chamadas: list[ChamadaTool]
    execucao: Execucao
    log: Path


def texto_memoria(pergunta: str, resposta: str) -> str:
    return f"Pergunta do usuário: {pergunta}\nResposta do assistente: {resposta}"


async def perguntar(
    banco: Path,
    sessao_id: str,
    pergunta: str,
    settings: Settings,
    instructions: str = INSTRUCTIONS_ASSISTENTE,
    diretorio_log: Path = DIRETORIO_LOGS,
) -> ResultadoPergunta:
    await rag.indexar_guia(banco, settings)
    sessao = SQLiteSession(sessao_id, banco)
    try:
        itens_anteriores = len(await sessao.get_items())
        execucao = await executar(
            lambda modelo: construir_assistente(modelo, instructions),
            pergunta,
            settings,
            com_tools=True,
            session=sessao,
            context=ContextoFinanceiro(banco, settings),
            max_turns=MAXIMO_TURNOS_ASSISTENTE,
        )
    finally:
        sessao.close()

    resposta: RespostaFinanceira = execucao.resultado.final_output
    await rag.gravar_memoria(banco, sessao_id, texto_memoria(pergunta, resposta.resposta), settings)
    chamadas = chamadas_de_tool(execucao.resultado.new_items)

    log = salvar_registro(
        f"perguntar_{sessao_id}",
        "Execução — perguntar",
        {
            "Sessão": sessao_id,
            "Itens no histórico da sessão antes da pergunta": str(itens_anteriores),
            "Provedor": execucao.provedor,
            "Modelo": execucao.modelo,
        },
        [
            Secao("Instructions", instructions),
            Secao("Pergunta", pergunta),
            Secao("Chamadas de tool (argumentos e retorno)", formatar_chamadas(chamadas)),
            Secao("Saída validada (RespostaFinanceira)", resposta.model_dump_json(indent=2), "json"),
        ],
        diretorio=diretorio_log,
    )
    return ResultadoPergunta(resposta, chamadas, execucao, log)
