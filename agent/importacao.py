import json
from dataclasses import dataclass
from pathlib import Path

from agent import database
from agent.agents import construir_classificador
from agent.config import Settings
from agent.execution_log import Secao, salvar_registro
from agent.prompts import INSTRUCTIONS_CLASSIFICADOR
from agent.runner import Execucao, executar
from agent.schema import ClassificacaoTransacao, TransacaoParaClassificar

TENTATIVAS_CLASSIFICACAO = 2
JUSTIFICATIVA_NAO_RETORNADA = "O classificador não retornou esta transação após novas tentativas."


@dataclass(frozen=True)
class RelatorioClassificacao:
    classificadas: list[ClassificacaoTransacao]
    nao_retornadas: list[int]
    execucoes: list[Execucao]


def incorporar_classificacoes(
    pendentes: list[TransacaoParaClassificar], recebidas: list[ClassificacaoTransacao]
) -> tuple[list[ClassificacaoTransacao], list[TransacaoParaClassificar]]:
    ids_pendentes = {transacao.id for transacao in pendentes}
    aceitas: dict[int, ClassificacaoTransacao] = {}
    for classificacao in recebidas:
        if classificacao.id in ids_pendentes:
            aceitas.setdefault(classificacao.id, classificacao)
    restantes = [transacao for transacao in pendentes if transacao.id not in aceitas]
    return list(aceitas.values()), restantes


def _entrada_classificador(pendentes: list[TransacaoParaClassificar]) -> str:
    return json.dumps([transacao.model_dump() for transacao in pendentes], ensure_ascii=False, indent=2)


async def classificar_pendentes(banco: Path, settings: Settings) -> RelatorioClassificacao:
    restantes = database.transacoes_sem_categoria(banco)
    classificadas: list[ClassificacaoTransacao] = []
    execucoes: list[Execucao] = []
    for _ in range(TENTATIVAS_CLASSIFICACAO):
        if not restantes:
            break
        execucao = await executar(construir_classificador, _entrada_classificador(restantes), settings)
        execucoes.append(execucao)
        aceitas, restantes = incorporar_classificacoes(restantes, execucao.resultado.final_output.classificacoes)
        classificadas += aceitas

    nao_retornadas = [transacao.id for transacao in restantes]
    database.gravar_categorias(
        banco,
        classificadas
        + [
            ClassificacaoTransacao(id=id_, justificativa=JUSTIFICATIVA_NAO_RETORNADA, categoria="Não identificado")
            for id_ in nao_retornadas
        ],
    )
    return RelatorioClassificacao(classificadas, nao_retornadas, execucoes)


async def importar(banco: Path, caminho_csv: Path, settings: Settings) -> Path:
    importacao = database.importar_csv(banco, caminho_csv)
    print(f"[importar] {importacao.inseridas} transações novas, {importacao.ignoradas} já existentes")
    relatorio = await classificar_pendentes(banco, settings)

    secoes = [Secao("Instructions do classificador", INSTRUCTIONS_CLASSIFICADOR)]
    for numero, execucao in enumerate(relatorio.execucoes, start=1):
        secoes += [
            Secao(f"Chamada {numero} — input", str(execucao.resultado.input), "json"),
            Secao(
                f"Chamada {numero} — output ({execucao.provedor} | {execucao.modelo})",
                execucao.resultado.final_output.model_dump_json(indent=2),
                "json",
            ),
        ]
    secoes.append(Secao("Transações não retornadas pelo classificador", str(relatorio.nao_retornadas)))

    return salvar_registro(
        f"importar_{caminho_csv.stem}",
        "Execução — importar",
        {
            "CSV": str(caminho_csv),
            "Banco": str(banco),
            "Transações inseridas": str(importacao.inseridas),
            "Transações já existentes": str(importacao.ignoradas),
            "Classificadas pelo LLM": str(len(relatorio.classificadas)),
        },
        secoes,
    )
