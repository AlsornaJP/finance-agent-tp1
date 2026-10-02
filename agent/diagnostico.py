import json
from pathlib import Path

from agent import database, rag
from agent.agents import construir_confronto_guia, construir_pontos_de_atencao, construir_recomendacoes
from agent.config import Settings
from agent.execution_log import Secao, salvar_registro
from agent.prompts import INSTRUCTIONS_CONFRONTO_GUIA, INSTRUCTIONS_PONTOS_DE_ATENCAO, INSTRUCTIONS_RECOMENDACOES
from agent.runner import Execucao, executar
from agent.schema import AvaliacaoGuia, DiagnosticoMensal, LevantamentoMensal, PontosDeAtencao

TRECHOS_POR_PONTO = 2


def levantar_mes(banco: Path, mes: str) -> LevantamentoMensal:
    disponiveis = database.meses_disponiveis(banco)
    if database.validar_mes(mes) not in disponiveis:
        raise ValueError(f"Não há transações para {mes}. Meses disponíveis: {', '.join(disponiveis) or 'nenhum'}.")
    anterior = database.mes_anterior(mes)
    tem_anterior = anterior in disponiveis
    return LevantamentoMensal(
        total=database.gasto_total_mes(banco, mes),
        categorias=database.gastos_por_categoria(banco, mes),
        mes_anterior=anterior if tem_anterior else None,
        comparacao=database.comparar_meses(banco, mes, anterior) if tem_anterior else [],
        atipicas=database.transacoes_atipicas(banco, mes),
    )


def _json(dados: object) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2)


def _secoes_da_etapa(titulo: str, instructions: str, execucao: Execucao) -> list[Secao]:
    return [
        Secao(f"{titulo} — instructions", instructions),
        Secao(f"{titulo} — input", str(execucao.resultado.input), "json"),
        Secao(
            f"{titulo} — output ({execucao.provedor} | {execucao.modelo})",
            execucao.resultado.final_output.model_dump_json(indent=2),
            "json",
        ),
    ]


async def diagnosticar(banco: Path, mes: str, settings: Settings) -> tuple[DiagnosticoMensal, Path]:
    levantamento = levantar_mes(banco, mes)
    await rag.indexar_guia(banco, settings)

    execucao_pontos = await executar(construir_pontos_de_atencao, levantamento.model_dump_json(indent=2), settings)
    pontos: PontosDeAtencao = execucao_pontos.resultado.final_output

    trechos_por_assunto = {
        ponto.assunto: [
            trecho.model_dump()
            for trecho in await rag.buscar(
                banco, f"{ponto.assunto}: {ponto.motivo}", settings, incluir_memorias=False, limite=TRECHOS_POR_PONTO
            )
        ]
        for ponto in pontos.pontos
    }
    entrada_confronto = _json({"pontos": pontos.model_dump()["pontos"], "trechos_guia": trechos_por_assunto})
    execucao_confronto = await executar(construir_confronto_guia, entrada_confronto, settings)
    avaliacao: AvaliacaoGuia = execucao_confronto.resultado.final_output

    entrada_recomendacoes = _json(
        {"mes": mes, "levantamento": levantamento.model_dump(), "avaliacoes": avaliacao.model_dump()["avaliacoes"]}
    )
    execucao_recomendacoes = await executar(construir_recomendacoes, entrada_recomendacoes, settings)
    diagnostico: DiagnosticoMensal = execucao_recomendacoes.resultado.final_output

    log = salvar_registro(
        f"diagnosticar_{mes}",
        f"Execução — diagnosticar {mes} (prompt chaining least-to-most)",
        {"Banco": str(banco), "Mês": mes},
        [
            Secao("Etapa 1 — Levantamento (Python, sem LLM)", levantamento.model_dump_json(indent=2), "json"),
            *_secoes_da_etapa("Etapa 2 — Pontos de atenção", INSTRUCTIONS_PONTOS_DE_ATENCAO, execucao_pontos),
            Secao("Etapa 3 — Trechos do guia recuperados por ponto (RAG)", _json(trechos_por_assunto), "json"),
            *_secoes_da_etapa("Etapa 3 — Confronto com o guia", INSTRUCTIONS_CONFRONTO_GUIA, execucao_confronto),
            *_secoes_da_etapa("Etapa 4 — Recomendações", INSTRUCTIONS_RECOMENDACOES, execucao_recomendacoes),
        ],
    )
    return diagnostico, log
