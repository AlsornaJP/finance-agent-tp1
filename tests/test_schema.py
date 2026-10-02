import pytest
from pydantic import ValidationError

from agent.schema import CATEGORIAS, ClassificacaoTransacao, Recomendacao, RespostaFinanceira


def test_categorias_fixas_na_ordem_do_dominio():
    assert CATEGORIAS == (
        "Alimentação",
        "Transporte",
        "Moradia",
        "Saúde",
        "Educação",
        "Lazer",
        "Compras",
        "Serviços/Assinaturas",
        "Não identificado",
    )


def test_classificacao_rejeita_categoria_fora_da_lista():
    with pytest.raises(ValidationError):
        ClassificacaoTransacao(id=1, justificativa="x", categoria="Habitação")


def test_justificativa_precede_categoria_no_schema():
    campos = list(ClassificacaoTransacao.model_json_schema()["properties"])
    assert campos.index("justificativa") < campos.index("categoria")


def test_recomendacao_exige_prioridade_positiva():
    with pytest.raises(ValidationError):
        Recomendacao(prioridade=0, acao="a", justificativa="b")


def test_resposta_financeira_listas_opcionais():
    resposta = RespostaFinanceira(resposta="ok")
    assert resposta.valores_citados == [] and resposta.fontes_conhecimento == []
