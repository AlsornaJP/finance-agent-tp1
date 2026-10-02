import pytest

from agent import agents, prompts, tools
from agent.schema import ClassificacaoLote, RespostaFinanceira


def test_aviso_mes_sem_dados_lista_meses_disponiveis(banco_classificado):
    aviso = tools.aviso_mes_sem_dados(banco_classificado, "2024-07")
    assert "2024-07" in aviso and "2024-03, 2024-04" in aviso
    assert tools.aviso_mes_sem_dados(banco_classificado, "2024-04") is None


def test_aviso_mes_sem_dados_propaga_formato_invalido(banco_classificado):
    with pytest.raises(ValueError, match="AAAA-MM"):
        tools.aviso_mes_sem_dados(banco_classificado, "abril")


def test_ferramentas_registradas():
    assert [ferramenta.name for ferramenta in tools.FERRAMENTAS] == [
        "gasto_total_mes",
        "gastos_por_categoria",
        "comparar_meses",
        "transacoes_atipicas",
        "listar_transacoes",
        "buscar_conhecimento",
    ]


def test_schema_das_tools_nao_expoe_contexto():
    gasto_total = tools.FERRAMENTAS[0]
    assert list(gasto_total.params_json_schema["properties"]) == ["mes"]


def test_agentes_combinam_tools_e_output_type():
    assistente = agents.construir_assistente("modelo-qualquer")
    assert assistente.output_type.output_type is RespostaFinanceira
    assert len(assistente.tools) == 6
    classificador = agents.construir_classificador("modelo-qualquer")
    assert classificador.output_type.output_type is ClassificacaoLote and classificador.tools == []


def test_instructions_seguem_anatomia_de_4_componentes():
    for instructions in (
        prompts.INSTRUCTIONS_CLASSIFICADOR,
        prompts.INSTRUCTIONS_ASSISTENTE,
        prompts.INSTRUCTIONS_PONTOS_DE_ATENCAO,
        prompts.INSTRUCTIONS_CONFRONTO_GUIA,
        prompts.INSTRUCTIONS_RECOMENDACOES,
    ):
        for secao in ("# INSTRUÇÃO", "# CONTEXTO", "# EXEMPLOS", "# FORMATO DE SAÍDA"):
            assert secao in instructions
