from agents import Agent, AgentOutputSchema, Model

from agent.prompts import (
    INSTRUCTIONS_ASSISTENTE,
    INSTRUCTIONS_CLASSIFICADOR,
    INSTRUCTIONS_CONFRONTO_GUIA,
    INSTRUCTIONS_PARTE_5,
    INSTRUCTIONS_PONTOS_DE_ATENCAO,
    INSTRUCTIONS_RECOMENDACOES,
)
from agent.schema import (
    AnaliseFinanceira,
    AvaliacaoGuia,
    ClassificacaoLote,
    DiagnosticoMensal,
    PontosDeAtencao,
    RespostaFinanceira,
)
from agent.tools import FERRAMENTAS, ContextoFinanceiro


def _saida(tipo: type) -> AgentOutputSchema:
    return AgentOutputSchema(tipo, strict_json_schema=False)


def construir_classificador(modelo: Model | str) -> Agent:
    return Agent(
        name="Classificador de Transações",
        instructions=INSTRUCTIONS_CLASSIFICADOR,
        model=modelo,
        output_type=_saida(ClassificacaoLote),
    )


def construir_assistente(
    modelo: Model | str, instructions: str = INSTRUCTIONS_ASSISTENTE
) -> Agent[ContextoFinanceiro]:
    return Agent[ContextoFinanceiro](
        name="Assistente Financeiro",
        instructions=instructions,
        model=modelo,
        tools=FERRAMENTAS,
        output_type=_saida(RespostaFinanceira),
    )


def construir_pontos_de_atencao(modelo: Model | str) -> Agent:
    return Agent(
        name="Diagnóstico — Pontos de Atenção",
        instructions=INSTRUCTIONS_PONTOS_DE_ATENCAO,
        model=modelo,
        output_type=_saida(PontosDeAtencao),
    )


def construir_confronto_guia(modelo: Model | str) -> Agent:
    return Agent(
        name="Diagnóstico — Confronto com o Guia",
        instructions=INSTRUCTIONS_CONFRONTO_GUIA,
        model=modelo,
        output_type=_saida(AvaliacaoGuia),
    )


def construir_recomendacoes(modelo: Model | str) -> Agent:
    return Agent(
        name="Diagnóstico — Recomendações",
        instructions=INSTRUCTIONS_RECOMENDACOES,
        model=modelo,
        output_type=_saida(DiagnosticoMensal),
    )


def construir_variante_sem_tools(modelo: Model | str) -> Agent:
    return Agent(
        name="Analista de Finanças Pessoais (TP1, Parte 5)",
        instructions=INSTRUCTIONS_PARTE_5,
        model=modelo,
        output_type=_saida(AnaliseFinanceira),
    )
