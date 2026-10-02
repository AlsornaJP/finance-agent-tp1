import pytest

from agent.diagnostico import levantar_mes


def test_levantamento_de_abril_compara_com_marco(banco_classificado):
    levantamento = levantar_mes(banco_classificado, "2024-04")
    assert levantamento.total.total_gasto == 5573.35
    assert levantamento.mes_anterior == "2024-03"
    assert any(c.categoria == "Transporte" and c.diferenca == 96.0 for c in levantamento.comparacao)
    assert [a.descricao for a in levantamento.atipicas] == ["RESTAURANTE OUTBACK"]


def test_levantamento_do_primeiro_mes_nao_tem_comparacao(banco_classificado):
    levantamento = levantar_mes(banco_classificado, "2024-03")
    assert levantamento.mes_anterior is None and levantamento.comparacao == []


def test_levantamento_de_mes_sem_dados_falha(banco_classificado):
    with pytest.raises(ValueError, match="2024-03, 2024-04"):
        levantar_mes(banco_classificado, "2024-09")
